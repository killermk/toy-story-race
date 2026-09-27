"""Comando ``intake``: registro, cópia, inventário e extração do original.

Fluxo (cada etapa gera registro no log de cadeia de custódia):

a. abre o original SOMENTE para leitura; tamanho, CRC32, MD5, SHA-1, SHA-256;
   formato pelos magic bytes; ``os.stat`` antes/depois;
b. copia para ``<workdir>/original_copy/``, confere o hash da cópia, preserva
   o mtime do original na cópia e marca a cópia como somente leitura;
c. lista as entradas dos compactados SEM extrair (manifesto);
d. extrai a cópia para ``<workdir>/extracted/`` com proteções (zip-slip,
   links, bombas), de forma idempotente;
e. recursão em compactados aninhados até ``--max-depth``;
f. imagens de disco: CUE/BIN (várias faixas/arquivos), ISO 2048, BIN sem CUE;
   setores brutos, faixa de dados → fluxo lógico de 2048 → ISO9660;
   SYSTEM.CNF; faixas de áudio; setores Form2; arquivos .sbi/.sub (apenas
   registro);
g. extrai os arquivos do ISO9660 para ``<workdir>/disc_files/`` e hasheia;
h. identifica o formato de cada arquivo (sniff), entropia e 16 bytes iniciais;
i. escreve os relatórios em ``<out>``;
j. opcional: compara com DAT Redump fornecido pelo usuário.

Ao final, o original é re-hasheado e comparado com a medição inicial.

Referência de hashes: antes de copiar, o original é comparado com a
referência registrada no log de custódia (``custody.original_history``) e com
a cópia de trabalho existente. Se divergir, o intake PARA (código 3) sem tocar
na cópia; só prossegue com ``--rebaseline`` (decisão explícita), e mesmo assim
a cópia anterior é preservada em ``original_copy/substituidas/``.

Integridade da imagem: arquivo de faixa ausente, setor final incompleto,
arquivo menor que o declarado, diretório ou arquivo ISO9660 além do fim da
faixa são ERROS de integridade (código 1) com destaque no relatório.

Qualquer falha (inclusive inesperada, ao copiar ou ao gravar os relatórios) é
registrada no log de custódia (``intake.abortado``) e o original é
reverificado antes de o erro subir para a linha de comando.
"""

from __future__ import annotations

import datetime as _dt
import os
import re
import stat
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from . import report
from .archives import NESTED_SUFFIX, Budget, extract_archive, list_archive, plan_extraction
from .config import Limits, find_repo_root
from .cue import CueError, compute_layout, parse_cue_file
from .custody import CustodyLog, environment_info, original_history, utc_now_iso, verify_chain
from .disc import DataTrackStream, layout_for_single_track, probe_raw_image, scan_track, summarize_sector_range
from .fsutil import (
    PathRedactor,
    ensure_dir,
    fs,
    is_alias,
    is_readonly,
    is_within,
    make_readonly,
    make_writable,
    open_readonly,
    remove_quietly,
    same_file,
)
from .hashing import CHUNK, MultiHasher, hash_and_entropy, hash_file, hashes_equal
from .iso9660 import UNSAFE_FOR_PYCDLIB, Iso9660Error, parse_iso, pycdlib_crosscheck, read_extent
from .redump import RedumpError, item_from_row, load_dat, match_items
from .safepath import NameAllocator, UnsafePath, check_member_name, safe_join, sanitize_component, sanitize_parts
from .signatures import DISC_IMAGES, EXTRACTABLE, detect_container
from .sniff import sniff_file
from .systemcnf import parse_system_cnf

UNSUPPORTED_CONTAINERS = {"rar4", "rar5", "zstd", "ecm", "chd", "pbp", "mds", "ccd"}
SUBCHANNEL_EXTENSIONS = {".sbi", ".sub"}
LIBCRYPT_NOTE = (
    "Arquivo de subcanal: presença registrada; conteúdo NÃO processado. Pode conter dados usados por "
    "proteções como LibCrypt (psx-spx: 'CDROM Protection - LibCrypt'). O kit não altera nem contorna proteções."
)


PROTECTED_HASHES_NAME = "protected_sha256.txt"
PSXSPX_URL = "https://psx-spx.consoledev.net/"


class IntakeError(Exception):
    """Erro fatal: o intake não pode prosseguir com segurança."""


class OriginalDivergentError(IntakeError):
    """O original difere da referência registrada (ou da cópia existente)."""


@dataclass
class IntakeOptions:
    original: Path
    workdir: Path
    out: Path
    limits: Limits = field(default_factory=Limits)
    redump_dat: Optional[Path] = None
    record_full_paths: bool = False
    command: List[str] = field(default_factory=list)
    rebaseline: bool = False


def _same(a: dict, b: dict) -> bool:
    return hashes_equal(a, b) and str(a.get("sha256", "")).lower() == str(b.get("sha256", "")).lower()


def _mtime_utc(ns: int) -> str:
    return _dt.datetime.fromtimestamp(ns / 1e9, _dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _stat_dict(st: os.stat_result) -> dict:
    return {"tamanho": st.st_size, "mtime_ns": st.st_mtime_ns, "mtime_utc": _mtime_utc(st.st_mtime_ns)}


def _norm_key(path: Path) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(path)))


def _strip_version(name: str) -> str:
    return re.sub(r";\d+$", "", name)


class Intake:
    def __init__(self, options: IntakeOptions):
        self.opts = options
        self.limits = options.limits
        self.repo = find_repo_root()
        self.workdir = Path(os.path.abspath(options.workdir))
        self.out = Path(os.path.abspath(options.out))
        self.redact = PathRedactor(
            [("<workdir>", self.workdir), ("<out>", self.out), ("<repo>", self.repo)],
            full=options.record_full_paths,
        )
        # Pastas usadas só para limpar caminhos de mensagens livres (exceções).
        self.redact.add_text_anchor("<externo>", Path(os.path.abspath(options.original)).parent)
        if options.redump_dat:
            self.redact.add_text_anchor("<externo>", Path(os.path.abspath(options.redump_dat)).parent)
        self.custody = CustodyLog(self.out / report.CUSTODY_NAME, command=options.command, scrub=self.redact.scrub_obj)
        self.integrity: List[dict] = []
        self.hashes0: Optional[dict] = None
        self.st_before: Optional[os.stat_result] = None
        self.reverified = False
        self.rows: List[dict] = []
        self.containers: List[dict] = []
        self.discs: List[dict] = []
        self.warnings: List[str] = []
        self.errors: List[str] = []
        self.budget = Budget(self.limits.max_total_bytes)
        self.consumed: set = set()
        self.cue_roles: Dict[str, List[str]] = {}
        self.disc_names = NameAllocator()
        self.original_path: Optional[Path] = None

    # ------------------------------------------------------------ helpers
    def scrub(self, text):
        return self.redact.scrub(text)

    def warn(self, message: str) -> None:
        self.warnings.append(self.scrub(message))

    def error(self, message: str) -> None:
        self.errors.append(self.scrub(message))

    def integrity_problem(self, origin: str, message: str, level: str = "erro") -> None:
        """Problema de integridade da imagem: ``erro`` (conteúdo faltando) ou ``indicio``."""
        self.integrity.append({"nivel": level, "origem": self.scrub(origin), "detalhe": self.scrub(message)})
        if level == "erro":
            self.error(f"INTEGRIDADE: {origin}: {message}")
        else:
            self.warn(f"INTEGRIDADE (indício): {origin}: {message}")

    def _git_ignored(self, path: Path) -> Optional[bool]:
        """True/False se ``path`` (dentro do repositório) é ignorado pelo git; None se indeterminado."""
        if not is_within(path, self.repo) or not os.path.exists(fs(self.repo / ".git")):
            return None
        rel = os.path.relpath(os.path.abspath(path), self.repo).replace(os.sep, "/")
        try:
            result = subprocess.run(
                ["git", "-C", str(self.repo), "check-ignore", "-q", "--no-index", rel],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=60,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if result.returncode == 0:
            return True
        if result.returncode == 1:
            return False
        return None

    def _check_locations(self, original: Path) -> None:
        """Recusa combinações de caminhos que poderiam expor ou sobrescrever material do jogo."""
        if os.path.exists(fs(self.workdir)) and not os.path.isdir(fs(self.workdir)):
            raise IntakeError(f"--workdir existe e não é uma pasta: {self.redact(self.workdir)}")
        if os.path.exists(fs(self.out)) and not os.path.isdir(fs(self.out)):
            raise IntakeError(f"--out existe e não é uma pasta: {self.redact(self.out)}")
        if is_within(original, self.workdir):
            raise IntakeError(
                "o --original está dentro da área de trabalho do kit (--workdir); mova o arquivo original para "
                "uma pasta fora dela (o kit escreve e apaga arquivos ali)"
            )
        if is_within(original, self.out):
            raise IntakeError("o --original está dentro da pasta de relatórios (--out), que vai para o repositório público")
        if is_within(self.workdir, self.repo):
            probe = self.workdir / "extracted" / "__tsr_probe__" / "SYSTEM.CNF"
            ignored = self._git_ignored(probe)
            if ignored is False:
                raise IntakeError(
                    "a área de trabalho (--workdir) fica dentro do repositório PÚBLICO e NÃO é ignorada pelo "
                    ".gitignore: os arquivos do jogo extraídos ali poderiam ser commitados. Use o padrão "
                    "(LegacyReference/_work) ou uma pasta fora do repositório"
                )
            if ignored is None:
                self.warn(
                    "não foi possível confirmar com o git que a área de trabalho está ignorada pelo .gitignore; "
                    "confira antes de qualquer commit"
                )
        if is_within(original, self.repo):
            ignored = self._git_ignored(original)
            if ignored is False:
                raise IntakeError(
                    "o --original está dentro do repositório PÚBLICO e NÃO é ignorado pelo .gitignore; "
                    "mova-o para fora do repositório"
                )
            self.warn("o arquivo original está dentro da pasta do repositório; o recomendado é mantê-lo fora dela")

    def _assert_not_original(self, target: Path) -> None:
        if self.original_path is not None and os.path.exists(fs(target)) and same_file(target, self.original_path):
            raise IntakeError(f"tentativa de escrita sobre o arquivo original bloqueada: {self.redact(target)}")

    # ------------------------------------------------------------ main
    def run(self) -> int:
        original = Path(os.path.abspath(self.opts.original))
        if not os.path.exists(fs(original)):
            self.custody.record("intake.inicio", "erro", motivo="original não encontrado", original=self.redact(original))
            raise IntakeError(f"arquivo original não encontrado: {self.redact(original)}")
        st_before = os.stat(fs(original))
        if not stat.S_ISREG(st_before.st_mode):
            self.custody.record("intake.inicio", "erro", motivo="original não é arquivo regular", original=self.redact(original))
            raise IntakeError("o --original precisa ser um arquivo regular")
        self.original_path = original
        self.st_before = st_before
        try:
            self._check_locations(original)
        except IntakeError as exc:
            self.custody.record("intake.inicio", "erro", motivo=str(exc), original=self.redact(original))
            raise
        self.custody.record(
            "intake.inicio",
            "ok",
            original=self.redact(original),
            workdir=self.redact(self.workdir),
            out=self.redact(self.out),
            limites=self.limits.to_dict(),
            redump_dat=self.redact(self.opts.redump_dat) if self.opts.redump_dat else None,
        )

        chain = verify_chain(self.out / report.CUSTODY_NAME)
        if not chain["ok"] and chain["detalhe"] != "log inexistente":
            self.warn(
                f"log de custódia com cadeia quebrada ({chain['detalhe']}, linha {chain['quebra_na_linha']}); "
                "a referência de hashes registrada pode não ser confiável"
            )
            self.custody.record("custodia.cadeia", "aviso", **chain)

        # a. hash + formato do original (somente leitura)
        container = detect_container(original)
        hashes0 = hash_file(original)
        self.hashes0 = hashes0
        st_mid = os.stat(fs(original))
        stable = st_mid.st_size == st_before.st_size == hashes0["size"] and st_mid.st_mtime_ns == st_before.st_mtime_ns
        hash_details = dict(
            arquivo=original.name,
            hashes=hashes0,
            formato_detectado=container.get("format"),
            evidencia=container.get("evidence"),
            stat=_stat_dict(st_before),
        )
        if not stable:
            self.custody.record("original.hash", "erro", motivo="original instável durante a leitura", **hash_details)
            raise IntakeError("o original mudou durante a leitura (tamanho/mtime); intake abortado")

        # a2. comparação com a referência registrada e com a cópia existente
        copy_dest = self.workdir / "original_copy" / sanitize_component(original.name)[0]
        check = self._check_registry(original, hashes0, copy_dest)
        if check["problemas"]:
            if not self.opts.rebaseline:
                self.custody.record("original.hash", "erro", motivo="diverge do registro", **hash_details)
                self.custody.record(
                    "original.divergente",
                    "erro",
                    arquivo=original.name,
                    problemas=check["problemas"],
                    referencia=check["referencia"],
                    sha256_atual=hashes0["sha256"],
                    sha256_copia_existente=(check["copia"] or {}).get("sha256"),
                )
                raise OriginalDivergentError(
                    "O ORIGINAL NÃO CONFERE COM O REGISTRO: " + "; ".join(check["problemas"]) + ". Nada foi alterado "
                    "(cópia de trabalho e relatórios preservados). Investigue; se a troca do arquivo for intencional, "
                    "rode de novo com --rebaseline (a cópia anterior será preservada)."
                )
            self.warn("REBASELINE solicitado: " + "; ".join(check["problemas"]))
            self.custody.record(
                "original.rebaseline",
                "aviso",
                arquivo=original.name,
                problemas=check["problemas"],
                hashes_anteriores=(check["referencia"] or {}).get("hashes") or check["copia"],
                hashes_novos=hashes0,
            )
        self.custody.record("original.hash", "ok", **hash_details)

        # b. cópia de trabalho
        copy_info = self._copy_original(original, hashes0, st_before, copy_dest, check)
        copy_path: Path = copy_info.pop("_path")
        self.custody.record("copia.verificada", "ok", **copy_info)

        # c-h. análise da cópia
        top_logical = original.name
        original_row = self._file_row(copy_path, top_logical, "original", hashes=hashes0)
        original_row["caminho_local"] = self.redact(original)
        redump_result = None
        try:
            self._dispatch(copy_path, top_logical, depth=0, container=container)
            # j. Redump (opcional)
            if self.opts.redump_dat:
                redump_result = self._redump(Path(self.opts.redump_dat))
        except IntakeError:
            raise
        except Exception as exc:  # falha inesperada: registra e ainda verifica o original e gera relatórios parciais
            message = f"falha inesperada durante a análise ({type(exc).__name__}: {exc}); relatório parcial"
            self.error(message)
            self.custody.record("analise.falha", "erro", erro=message)

        # verificação final do original
        unchanged, st_after = self._reverify()
        if not unchanged:
            self.error("O ARQUIVO ORIGINAL MUDOU durante o intake (tamanho/mtime/hash). Investigue antes de prosseguir.")

        inventory = self._build_inventory(original, container, hashes0, st_before, st_after, unchanged, copy_info, redump_result)
        self._register_protected_hashes(inventory)
        try:
            paths = report.write_reports(inventory, self.out)
        except report.ReportWriteError as exc:
            message = f"falha ao gravar os relatórios: {exc}"
            self.custody.record("relatorios.falha", "erro", erro=message, substituidos=exc.replaced)
            raise IntakeError(self.scrub(message)) from exc
        self.custody.record(
            "relatorios.gerados",
            "erro" if self.errors else ("aviso" if self.warnings else "ok"),
            arquivos={k: self.redact(v) for k, v in paths.items()},
            total_linhas=len(self.rows),
            avisos=len(self.warnings),
            erros=len(self.errors),
            problemas_integridade=len(self.integrity),
        )
        self.inventory = inventory
        self.report_paths = paths
        if not unchanged:
            return 3
        return 1 if self.errors else 0

    def _reverify(self):
        """Re-hasheia o original e compara com a medição inicial (registrado no log)."""
        original, st_before, hashes0 = self.original_path, self.st_before, self.hashes0
        st_after = os.stat(fs(original))
        hashes_after = hash_file(original)
        unchanged = (
            st_after.st_size == st_before.st_size
            and st_after.st_mtime_ns == st_before.st_mtime_ns
            and _same(hashes_after, hashes0)
        )
        self.custody.record(
            "original.reverificado",
            "ok" if unchanged else "erro",
            inalterado=unchanged,
            stat_antes=_stat_dict(st_before),
            stat_depois=_stat_dict(st_after),
            sha256_antes=hashes0["sha256"],
            sha256_depois=hashes_after["sha256"],
        )
        self.reverified = True
        return unchanged, st_after

    def abort(self, reason: str, exc: BaseException) -> None:
        """Registra o aborto no log e, se possível, reverifica o original."""
        try:
            self.custody.record("intake.abortado", "erro", motivo=reason, tipo=type(exc).__name__)
        except Exception:
            pass
        if self.reverified or self.original_path is None or self.hashes0 is None or self.st_before is None:
            return
        try:
            self._reverify()
        except Exception as inner:  # registra, mas não mascara o erro original
            try:
                self.custody.record("original.reverificado", "erro", motivo=f"reverificação impossível ({type(inner).__name__}: {inner})")
            except Exception:
                pass

    # ------------------------------------------------------------ a2. registry
    def _check_registry(self, original: Path, hashes0: dict, copy_dest: Path) -> dict:
        """Compara o original com a referência do log de custódia e com a cópia existente."""
        history = original_history(self.out / report.CUSTODY_NAME, original.name)
        reference = history["referencia"]
        copy_hashes = None
        if os.path.isfile(fs(copy_dest)) and not os.path.islink(fs(copy_dest)) and not same_file(copy_dest, original):
            copy_hashes = hash_file(copy_dest)
        problems: List[str] = []
        if reference is not None and not _same(hashes0, reference["hashes"]):
            problems.append(
                f"o original difere da referência registrada em {reference.get('timestamp_utc')} "
                f"(SHA-256 registrado {reference['hashes'].get('sha256')}, atual {hashes0['sha256']})"
            )
        if history["divergentes"]:
            problems.append(
                f"o log de custódia contém {len(history['divergentes'])} registro(s) 'ok' com hashes diferentes da "
                "referência, sem rebaseline"
            )
        if reference is None and copy_hashes is not None and not _same(copy_hashes, hashes0):
            problems.append(
                "não há registro deste arquivo no log de custódia (--out) e a cópia de trabalho existente difere do "
                "original: não é possível saber qual dos dois está íntegro"
            )
        copy_corrupt = (
            not problems and reference is not None and copy_hashes is not None and not _same(copy_hashes, hashes0)
        )
        return {"problemas": problems, "referencia": reference, "copia": copy_hashes, "copia_alterada": copy_corrupt}

    # ------------------------------------------------------------ b. copy
    def _preserve_copy(self, dest: Path, existing: dict) -> Path:
        """Move uma cópia divergente para ``original_copy/substituidas/`` (nunca apaga)."""
        keep_dir = dest.parent / "substituidas"
        ensure_dir(keep_dir)
        stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        target = keep_dir / f"{dest.name}.{stamp}.sha256-{str(existing.get('sha256'))[:12]}"
        counter = 2
        while os.path.lexists(fs(target)):
            target = keep_dir / f"{dest.name}.{stamp}.sha256-{str(existing.get('sha256'))[:12]}~{counter}"
            counter += 1
        make_writable(dest)
        os.replace(fs(dest), fs(target))
        make_readonly(target)
        self.custody.record(
            "copia.preservada", "aviso", destino=self.redact(target), sha256=existing.get("sha256"), tamanho=existing.get("size")
        )
        return target

    def _copy_original(self, original: Path, hashes0: dict, st: os.stat_result, dest: Path, check: dict) -> dict:
        copy_dir = dest.parent
        ensure_dir(copy_dir)
        if os.path.exists(fs(dest)) and same_file(dest, original):
            raise IntakeError("o --original aponta para a própria cópia de trabalho; informe o arquivo original")
        situation = None
        preserved = None
        if os.path.lexists(fs(dest)):
            if os.path.islink(fs(dest)) or not os.path.isfile(fs(dest)):
                raise IntakeError(f"destino da cópia existe e não é arquivo regular: {self.redact(dest)}")
            existing = check.get("copia") or hash_file(dest)
            if _same(existing, hashes0):
                situation = "ja_existia_verificada"
            else:
                # Só chega aqui com --rebaseline ou com a cópia comprovadamente
                # alterada (o original confere com a referência): a cópia antiga
                # é PRESERVADA, nunca apagada.
                preserved = self._preserve_copy(dest, existing)
                situation = "substituida_anterior_preservada"
                if check.get("copia_alterada"):
                    self.error(
                        "a cópia de trabalho estava ALTERADA (não conferia com o original, que confere com o "
                        f"registro); ela foi preservada em {self.redact(preserved)} e uma nova cópia foi feita"
                    )
                else:
                    self.warn(f"cópia de trabalho anterior preservada em {self.redact(preserved)} (rebaseline)")
        if situation != "ja_existia_verificada":
            tmp = dest.with_name(dest.name + ".tsrpart")
            remove_quietly(tmp)
            with open_readonly(original) as source, open(fs(tmp), "wb") as target:
                while True:
                    data = source.read(CHUNK)
                    if not data:
                        break
                    target.write(data)
                target.flush()
                os.fsync(target.fileno())
            copied = hash_file(tmp)
            if not (hashes_equal(copied, hashes0) and copied["sha256"] == hashes0["sha256"]):
                remove_quietly(tmp)
                raise IntakeError("o hash da cópia difere do original (falha de leitura/escrita); nada foi substituído")
            if os.path.exists(fs(dest)):
                make_writable(dest)
            os.replace(fs(tmp), fs(dest))
            os.utime(fs(dest), ns=(st.st_atime_ns, st.st_mtime_ns))
            situation = situation or "copiada"
        make_readonly(dest)
        final = hash_file(dest)
        matches = hashes_equal(final, hashes0) and final["sha256"] == hashes0["sha256"]
        if not matches:
            raise IntakeError("a cópia de trabalho não confere com o original após a cópia")
        info = {
            "_path": dest,
            "caminho": self.redact(dest),
            "situacao": situation,
            "hashes_conferem": matches,
            "somente_leitura": is_readonly(dest),
            "sha256": final["sha256"],
        }
        if preserved is not None:
            info["copia_anterior_preservada"] = self.redact(preserved)
        return info

    # ------------------------------------------------------------ rows
    def _file_row(self, path: Path, logical: str, tipo: str, hashes: Optional[dict] = None, extra: Optional[dict] = None) -> dict:
        file_hashes, entropy = hash_and_entropy(path, self.limits.entropy_full_max_bytes)
        if hashes is not None and not (hashes_equal(file_hashes, hashes) and file_hashes["sha256"] == hashes["sha256"]):
            self.error(f"{logical}: hash do arquivo de trabalho difere do esperado")
        sniffed = sniff_file(path)
        with open_readonly(path) as handle:
            head16 = handle.read(16).hex()
        row = {
            "tipo": tipo,
            "caminho_logico": logical,
            "caminho_local": self.redact(path),
            "tamanho": file_hashes["size"],
            "crc32": file_hashes["crc32"],
            "md5": file_hashes["md5"],
            "sha1": file_hashes["sha1"],
            "sha256": file_hashes["sha256"],
            "formato": sniffed.format,
            "categoria": sniffed.category,
            "fonte_assinatura": sniffed.source,
            "detalhes_formato": sniffed.details,
            "indicios": list(sniffed.hints),
            "entropia": entropy["valor"],
            "entropia_metodo": entropy["metodo"],
            "primeiros_16_bytes_hex": head16,
            "primeiros_16_bytes_sao_o_arquivo_inteiro": 0 < file_hashes["size"] <= 16,
            "lba": None,
            "setores": None,
            "setores_form2": None,
            "data": None,
            "observacoes": [],
        }
        row["_path"] = path  # uso interno; removido antes de gerar os relatórios
        roles = self.cue_roles.get(_norm_key(path))
        if roles and tipo == "extraido":
            row["observacoes"].append("referenciado por CUE: " + "; ".join(roles))
            if row["formato"] == "desconhecido":
                row["indicios"].append(
                    "sem assinatura própria no conteúdo (faixas de áudio CD-DA são PCM sem cabeçalho); "
                    "papel definido pela declaração do CUE"
                )
                row["formato"] = "faixa de CD conforme CUE"
                row["categoria"] = "imagem_de_disco"
        if path.suffix.lower() in SUBCHANNEL_EXTENSIONS or sniffed.format.startswith("SBI"):
            row["observacoes"].append(LIBCRYPT_NOTE)
            row["subcanal"] = True
        if extra:
            row.update(extra)
        self.rows.append(row)
        return row

    # ------------------------------------------------------------ dispatch
    def _dispatch(self, path: Path, logical: str, depth: int, container: Optional[dict] = None) -> None:
        det = container or detect_container(path)
        fmt = det.get("format")
        if fmt in EXTRACTABLE:
            self._process_archive(path, logical, depth, det)
        elif fmt == "cue":
            self._process_cue(path, logical)
        elif fmt in DISC_IMAGES:
            if _norm_key(path) in self.consumed:
                return
            self._process_image_without_cue(path, logical, det)
        elif fmt in UNSUPPORTED_CONTAINERS:
            self.warn(
                f"{logical}: formato {fmt} reconhecido pelos magic bytes, mas não suportado por este kit "
                "(dependências limitadas a py7zr/pycdlib); conteúdo não inventariado"
            )
            self.custody.record("formato.nao_suportado", "aviso", arquivo=logical, formato=fmt)

    # ------------------------------------------------------------ archives
    def _extraction_dir(self, path: Path, depth: int) -> Path:
        if depth == 0:
            name, _ = sanitize_component(path.name)
            return self.workdir / "extracted" / name
        # O plano do compactado externo reservou "<nome>.extracted" (nenhuma
        # entrada externa pode ocupar esse caminho).
        return path.with_name(path.name + NESTED_SUFFIX)

    def _process_archive(self, path: Path, logical: str, depth: int, det: dict) -> None:
        fmt = det["format"]
        record: Dict[str, object] = {
            "caminho_logico": logical,
            "formato": fmt,
            "profundidade": depth,
            "evidencia_formato": det.get("evidence"),
        }
        self.containers.append(record)
        if depth >= self.limits.max_depth:
            record["situacao"] = "não extraído: profundidade máxima atingida"
            self.warn(f"{logical}: profundidade máxima de compactados ({self.limits.max_depth}) atingida; não extraído")
            self.custody.record("extracao", "aviso", arquivo=logical, motivo="profundidade máxima")
            return
        try:
            listing = list_archive(path, fmt)
        except Exception as exc:
            record["situacao"] = "erro na listagem"
            record["erro"] = self.scrub(f"{type(exc).__name__}: {exc}")
            self.error(f"{logical}: falha ao listar ({type(exc).__name__}: {exc})")
            self.custody.record("manifesto", "erro", arquivo=logical, erro=record["erro"])
            return
        record["entradas"] = listing["entradas"]
        record["info"] = listing.get("info")
        self.custody.record(
            "manifesto",
            "ok",
            arquivo=logical,
            formato=fmt,
            entradas=len(listing["entradas"]),
            tamanho_declarado_total=sum(e.get("tamanho") or 0 for e in listing["entradas"]),
        )
        dest = self._extraction_dir(path, depth)
        self._assert_not_original(dest)
        size = os.path.getsize(fs(path))
        plan = plan_extraction(listing, size, dest, self.limits, self.budget)
        if plan["erro_fatal"]:
            record["situacao"] = "recusado: " + plan["erro_fatal"]
            self.error(f"{logical}: extração recusada — {plan['erro_fatal']}")
            self.custody.record("extracao", "erro", arquivo=logical, motivo=plan["erro_fatal"])
            return
        for rejected in plan["recusadas"]:
            message = f"{logical}: entrada recusada {rejected['nome']!r} — {rejected['motivo']}"
            if rejected.get("grave"):
                self.error(message)
            else:
                self.warn(message)
        ensure_dir(dest)
        result = extract_archive(path, listing, plan["plano"], self.limits, self.budget)
        for err in result["erros"]:
            self.error(f"{logical}: {err}")
        if result.get("descartadas"):
            record["descartadas"] = result["descartadas"]
            for item in result["descartadas"]:
                self.warn(
                    f"{logical}: o extrator entregou dados para {item['nome_py7zr']!r}, fora do plano (ex.: nome "
                    f"duplicado); {item['tamanho']} bytes medidos (SHA-256 {item['sha256']}) e descartados sem gravar"
                )
        extracted = result["extraidas"]
        record["destino"] = self.redact(dest)
        record["situacao"] = (
            f"{len(extracted)} extraída(s), {len(plan['recusadas'])} recusada(s), {len(result['erros'])} erro(s)"
        )
        self.custody.record(
            "extracao",
            "erro" if result["erros"] else ("aviso" if plan["recusadas"] else "ok"),
            arquivo=logical,
            destino=self.redact(dest),
            extraidas=len(extracted),
            ja_existentes=sum(1 for i in extracted if i["entrada"].get("status") == "ja_existente_verificado"),
            recusadas=plan["recusadas"],
            erros=result["erros"],
            descartadas=result.get("descartadas") or [],
        )
        children = []
        for item in extracted:
            child = item["destino"]
            children.append((child, f"{logical}!/{item['entrada']['nome']}", detect_container(child), item["entrada"]))
        # CUEs primeiro: marcam os BINs referenciados como consumidos
        children.sort(key=lambda c: (0 if c[2].get("format") == "cue" else 1, c[1]))
        for child, child_logical, child_det, entry in children:
            extra = {"data": entry.get("data")}
            if entry.get("crc32") is not None:
                extra["crc32_manifesto_confere"] = None
            row = self._file_row(child, child_logical, "extraido", extra=extra)
            if entry.get("crc32") is not None:
                row["crc32_manifesto_confere"] = row["crc32"] == entry["crc32"]
                if not row["crc32_manifesto_confere"]:
                    self.error(f"{child_logical}: CRC32 extraído difere do manifesto")
            self._dispatch(child, child_logical, depth + 1, child_det)

    # ------------------------------------------------------------ discs
    def _new_disc(self, logical: str, layout_kind: str, stem: str) -> dict:
        name, _ = sanitize_component(stem or "disco")
        final, _ = self.disc_names.allocate([name], logical)
        disc = {
            "id": f"disco-{len(self.discs) + 1}",
            "origem": logical,
            "layout": layout_kind,
            "diretorio_arquivos": final[0],
            "observacoes": [],
        }
        self.discs.append(disc)
        return disc

    def _resolve_cue_reference(self, base_dir: Path, name: str) -> Optional[Path]:
        candidates: List[Path] = []
        try:
            parts = check_member_name(name)
            clean, _ = sanitize_parts(parts)
            candidates.append(base_dir.joinpath(*parts))
            candidates.append(base_dir.joinpath(*clean))
        except UnsafePath as exc:
            self.warn(f"referência insegura no CUE ({exc.reason}): {name!r}; buscando apenas pelo nome base")
        basename = re.split(r"[\\/]", name)[-1]
        candidates.append(base_dir / basename)
        candidates.append(base_dir / sanitize_component(basename)[0])
        for candidate in candidates:
            if is_within(candidate, base_dir) and os.path.isfile(fs(candidate)) and not os.path.islink(fs(candidate)):
                return candidate
        wanted = {basename.casefold(), sanitize_component(basename)[0].casefold()}
        try:
            for entry in sorted(os.listdir(fs(base_dir))):
                candidate = base_dir / entry
                if entry.casefold() in wanted and os.path.isfile(fs(candidate)) and not os.path.islink(fs(candidate)):
                    return candidate
        except OSError:
            pass
        return None

    def _process_cue(self, cue_path: Path, logical: str) -> None:
        try:
            sheet = parse_cue_file(cue_path)
        except (CueError, OSError) as exc:
            self.error(f"{logical}: CUE ilegível ({exc})")
            return
        resolved: List[Optional[Path]] = []
        sizes: List[Optional[int]] = []
        for cue_file in sheet.files:
            path = self._resolve_cue_reference(cue_path.parent, cue_file.name)
            resolved.append(path)
            sizes.append(os.path.getsize(fs(path)) if path else None)
            if path is None:
                self.integrity_problem(logical, f"arquivo de faixa referenciado pelo CUE não encontrado: {cue_file.name!r}")
            else:
                self.consumed.add(_norm_key(path))
                declared = ", ".join(f"faixa {sheet.tracks[i].number:02d} {sheet.tracks[i].type}" for i in cue_file.tracks)
                self.cue_roles.setdefault(_norm_key(path), []).append(f"{Path(logical).name} ({declared or 'sem faixas'})")
        layouts = compute_layout(sheet, resolved, sizes)
        disc = self._new_disc(logical, "cue", cue_path.stem)
        disc["cue"] = sheet.to_dict()
        disc["arquivos_imagem"] = [
            {
                "nome": f.name,
                "tipo": f.filetype,
                "encontrado": p is not None,
                "caminho_local": self.redact(p) if p else None,
                "tamanho": s,
            }
            for f, p, s in zip(sheet.files, resolved, sizes)
        ]
        for w in sheet.warnings:
            self.warn(f"{logical}: {w}")
        self.custody.record(
            "disco.cue",
            "aviso" if sheet.warnings else "ok",
            arquivo=logical,
            arquivos=len(sheet.files),
            faixas=len(sheet.tracks),
            avisos=sheet.warnings,
        )
        self._analyze_disc(disc, layouts, logical, cue_path.parent, [cue_path.stem] + [Path(f.name).stem for f in sheet.files])

    def _process_image_without_cue(self, path: Path, logical: str, det: dict) -> None:
        size = os.path.getsize(fs(path))
        probe = probe_raw_image(path, size, det)
        if "erro" in probe:
            self.error(f"{logical}: {probe['erro']}")
            return
        layout = layout_for_single_track(path, path.name, size, probe["tipo_faixa"])
        kind = "iso_2048" if det.get("format") == "iso9660" else "bin_sem_cue"
        disc = self._new_disc(logical, kind, path.stem)
        disc["deteccao"] = {
            "formato": det.get("format"),
            "evidencia": det.get("evidence"),
            "fonte": det.get("source"),
            "tipo_faixa": probe["tipo_faixa"],
            "tamanho_setor": probe["tamanho_setor"],
            "setores": probe["setores"],
            "avisos": probe["avisos"],
        }
        for w in probe["avisos"]:
            if "não é múltiplo" in w:
                self.integrity_problem(logical, f"{w} (possível arquivo truncado/incompleto)")
            else:
                self.warn(f"{logical}: {w}")
        if kind == "bin_sem_cue":
            disc["observacoes"].append(
                "Imagem sem .cue: tratada como uma única faixa de dados. Sem o .cue não é possível delimitar "
                "faixas de áudio; se houver setores sem sync após os dados, a natureza deles é NÃO CONFIRMADA."
            )
        self.custody.record("disco.sem_cue", "ok", arquivo=logical, deteccao=disc["deteccao"])
        self._analyze_disc(disc, [layout], logical, path.parent, [path.stem])

    def _analyze_disc(self, disc: dict, layouts, logical: str, image_dir: Path, stems: List[str]) -> None:
        tracks_out = []
        data_layout = None
        data_map = None
        for layout in layouts:
            entry = layout.to_dict()
            track_origin = f"{logical} faixa {layout.number:02d}"
            for w in layout.warnings:
                if "não é múltiplo" in w:
                    self.integrity_problem(track_origin, f"{w} (possível arquivo truncado/incompleto)")
            if layout.file_path is None or layout.sectors is None:
                entry["situacao"] = "não lida"
                tracks_out.append(entry)
                if layout.file_path is not None:
                    self.integrity_problem(track_origin, "posição/tamanho da faixa não pôde ser calculado; faixa não lida")
                continue
            first_data = data_layout is None and layout.kind == "data"
            scan = scan_track(layout.file_path, layout, keep_map=first_data and layout.sector_size in (2352, 2336))
            if first_data and layout.sector_size == 2048:
                disc["observacoes"].append(
                    "Faixa de dados com setores de 2048 bytes: a imagem não contém subheaders CD-XA, portanto "
                    "setores Form2 (XA/STR) não podem ser contados nesta imagem."
                )
            entry["hashes"] = scan.get("hashes")
            entry["estatisticas"] = scan.get("estatisticas")
            if scan.get("erro"):
                entry["erro"] = scan["erro"]
            if first_data:
                data_layout = layout
                data_map = scan.get("mapa_setores")
            tracks_out.append(entry)
            hashes = scan.get("hashes") or {}
            stats = scan.get("estatisticas") or {}
            track_row = {
                "tipo": "faixa",
                "caminho_logico": f"{logical}#faixa{layout.number:02d}",
                "caminho_local": self.redact(layout.file_path),
                "tamanho": hashes.get("size"),
                "crc32": hashes.get("crc32"),
                "md5": hashes.get("md5"),
                "sha1": hashes.get("sha1"),
                "sha256": hashes.get("sha256"),
                "formato": f"faixa {layout.type}",
                "categoria": "audio_cdda" if layout.kind == "audio" else "dados_de_disco",
                "fonte_assinatura": "CUE" if disc["layout"] == "cue" else "detecção por conteúdo",
                "detalhes_formato": {},
                "indicios": [],
                "entropia": None,
                "entropia_metodo": None,
                "primeiros_16_bytes_hex": None,
                "lba": layout.abs_lba_begin,
                "setores": layout.sectors,
                "setores_form2": stats.get("form2"),
                "data": None,
                "observacoes": [f"duração {entry.get('duracao_msf')} ({entry.get('duracao_segundos')} s)"],
            }
            self.rows.append(track_row)
            for w in layout.warnings:
                if "não é múltiplo" not in w:
                    self.warn(f"{logical} faixa {layout.number:02d}: {w}")
            if stats.get("aviso"):
                self.integrity_problem(track_origin, f"{stats['aviso']} (arquivo incompleto)")
            if stats.get("aviso_audio"):
                self.warn(f"{logical} faixa {layout.number:02d}: {stats['aviso_audio']}")
            if disc["layout"] == "bin_sem_cue" and stats.get("setores_sem_sync"):
                disc["observacoes"].append(
                    f"{stats['setores_sem_sync']} setor(es) sem padrão de sync a partir do setor "
                    f"{stats.get('primeiro_setor_sem_sync')}; natureza NÃO CONFIRMADA (sem .cue)."
                )
        disc["faixas"] = tracks_out
        disc["faixas_audio"] = [
            {
                "numero": t["numero"],
                "setores": t.get("setores"),
                "duracao_segundos": t.get("duracao_segundos"),
                "duracao_a_partir_index01_segundos": t.get("duracao_a_partir_index01_segundos"),
                "sha1": (t.get("hashes") or {}).get("sha1"),
                "crc32": (t.get("hashes") or {}).get("crc32"),
            }
            for t in tracks_out
            if t.get("natureza") == "audio"
        ]
        disc["resumo_faixas"] = {
            "total": len(tracks_out),
            "dados": sum(1 for t in tracks_out if t.get("natureza") == "data"),
            "audio": len(disc["faixas_audio"]),
            "outras": sum(1 for t in tracks_out if t.get("natureza") not in ("data", "audio")),
        }
        disc["arquivos_subcanal"] = self._find_subchannel(image_dir, stems)
        self.custody.record(
            "disco.faixas",
            "ok",
            disco=disc["id"],
            origem=logical,
            faixas=[
                {"numero": t["numero"], "tipo": t["tipo"], "setores": t.get("setores"), "sha1": (t.get("hashes") or {}).get("sha1")}
                for t in tracks_out
            ],
            arquivos_subcanal=[s["nome"] for s in disc["arquivos_subcanal"]],
        )
        if data_layout is None or data_layout.user_offset is None:
            disc["iso9660"] = None
            disc["system_cnf"] = None
            disc["system_cnf_observacao"] = "nenhuma faixa de dados legível como ISO9660"
            if data_layout is None:
                self.warn(f"{logical}: nenhuma faixa de dados encontrada")
            return
        if data_layout.abs_lba_begin is None:
            disc["iso9660"] = None
            disc["system_cnf"] = None
            disc["system_cnf_observacao"] = (
                "LBA absoluto da faixa de dados NÃO CONFIRMADO (arquivo anterior do CUE ausente ou indeterminado); "
                "ISO9660 não lido para não presumir o endereço"
            )
            self.integrity_problem(logical, disc["system_cnf_observacao"])
            return
        self._read_filesystem(disc, data_layout, data_map, logical)

    def _find_subchannel(self, image_dir: Path, stems: List[str]) -> List[dict]:
        found = []
        wanted = {s.casefold() for s in stems if s}
        try:
            names = sorted(os.listdir(fs(image_dir)))
        except OSError:
            return found
        for name in names:
            path = image_dir / name
            suffix = Path(name).suffix.lower()
            if suffix not in SUBCHANNEL_EXTENSIONS or not os.path.isfile(fs(path)):
                continue
            row = next((r for r in self.rows if r.get("caminho_local") == self.redact(path)), None)
            stem_match = Path(name).stem.casefold() in wanted
            with open_readonly(path) as handle:
                head = handle.read(4)
            found.append(
                {
                    "nome": name,
                    "tamanho": os.path.getsize(fs(path)),
                    "sha1": row.get("sha1") if row else hash_file(path)["sha1"],
                    "assinatura_sbi": head == b"SBI\x00",
                    "mesmo_nome_da_imagem": stem_match,
                    "observacao": LIBCRYPT_NOTE,
                }
            )
            self.custody.record("subcanal.registrado", "aviso", arquivo=name, observacao="apenas registrado; não processado")
        return found

    def _read_filesystem(self, disc: dict, layout, sector_map, logical: str) -> None:
        def open_stream():
            return DataTrackStream(
                layout.file_path,
                layout.begin_byte,
                layout.sector_size,
                layout.user_offset,
                layout.abs_lba_begin or 0,
                layout.sectors,
            )

        stream = open_stream()
        try:
            try:
                iso = parse_iso(stream, self.limits)
            except Iso9660Error as exc:
                disc["iso9660"] = {"erro": self.scrub(str(exc))}
                disc["system_cnf"] = None
                disc["system_cnf_observacao"] = "sistema de arquivos ISO9660 não lido"
                self.error(f"{logical}: ISO9660 não lido ({exc})")
                self.custody.record("disco.iso9660", "erro", disco=disc["id"], erro=str(exc))
                return
            unsafe = sorted({a["tipo"] for a in iso["anomalias"]} & UNSAFE_FOR_PYCDLIB)
            if unsafe:
                # O pycdlib não se protege contra laços/diretórios gigantes: nem é executado.
                cross = {
                    "status": "nao_executada",
                    "erro": "anomalias estruturais detectadas pelo parser próprio (" + ", ".join(unsafe) + "); "
                    "o pycdlib não tem proteção contra elas",
                }
            else:
                cross = pycdlib_crosscheck(stream.worker_params(), iso["entries"], self.limits)
                if cross.get("erro"):
                    cross["erro"] = self.scrub(cross["erro"])
            if cross.get("status") != "ok":
                self.warn(f"{logical}: verificação cruzada com pycdlib: {cross.get('status')} {cross.get('erro') or ''}".strip())
            integrity_messages = {a["detalhe"] for a in iso["anomalias"] if a["tipo"] == "diretorio_alem_do_fim"}
            for w in iso["warnings"]:
                # os que viram problema de integridade são registrados uma vez só, lá
                if w in integrity_messages or w.startswith("PVD declara") or "extensão ultrapassa o fim" in w:
                    continue
                self.warn(f"{logical}: ISO9660: {w}")
            for anomaly in iso["anomalias"]:
                if anomaly["tipo"] == "diretorio_alem_do_fim":
                    self.integrity_problem(logical, f"ISO9660: {anomaly['detalhe']} (dados do diretório ausentes na imagem)")
            declared = iso["pvd"].get("tamanho_volume_blocos")
            if isinstance(declared, int) and declared > iso["setores_na_faixa"]:
                self.integrity_problem(
                    logical,
                    f"PVD declara {declared} blocos, mas a faixa de dados tem {iso['setores_na_faixa']} setores "
                    "(compatível com imagem truncada; também pode ser um volume declarado maior que a faixa — NÃO CONFIRMADO)",
                    level="indicio",
                )
            entries = sorted(iso["entries"], key=lambda e: (e["path"] != "/", e["path"].upper()))
            disc_dir = self.workdir / "disc_files" / disc["diretorio_arquivos"]
            self._assert_not_original(disc_dir)
            ensure_dir(disc_dir)
            allocator = NameAllocator()
            tree = []
            file_rows: Dict[str, dict] = {}
            for e in entries:
                node = {
                    "caminho": e["path"],
                    "diretorio": e["is_dir"],
                    "lba": e["lba"],
                    "tamanho": e["size"],
                    "setores": e["sectors"],
                    "data": e["date"],
                    "flags": e.get("flags_desc"),
                    "xa": e.get("xa"),
                    "observacoes": [],
                }
                if not e["is_dir"]:
                    self._extract_disc_file(stream, e, node, disc_dir, allocator, sector_map, layout, logical, file_rows)
                tree.append(node)
            files = [n for n in tree if not n["diretorio"]]
            disc["iso9660"] = {
                "descritores": iso["descritores"],
                "pvd": iso["pvd"],
                "avisos": iso["warnings"],
                "anomalias": iso["anomalias"],
                "verificacao_pycdlib": cross,
                "total_arquivos": len(files),
                "total_diretorios": len(tree) - len(files),
                "destino_extracao": self.redact(disc_dir),
                "observacao_form2": (
                    "Arquivos extraídos pela visão lógica de 2048 bytes/setor. Setores Mode2 Form2 (XA/STR) têm "
                    "2324 bytes; o excedente não é preservado nessa visão (ver 'setores_form2')."
                ),
            }
            disc["arvore"] = tree
            self.custody.record(
                "disco.iso9660",
                "ok",
                disco=disc["id"],
                arquivos=len(files),
                diretorios=len(tree) - len(files),
                pycdlib=cross.get("status"),
                destino=self.redact(disc_dir),
            )
            self._system_cnf(disc, tree, file_rows, logical)
        finally:
            stream.close()

    def _extract_disc_file(self, stream, e, node, disc_dir, allocator, sector_map, layout, logical, file_rows) -> None:
        rel_start = e["lba"] - (layout.abs_lba_begin or 0)
        sectors_info = summarize_sector_range(sector_map, rel_start, e["sectors"]) if e["size"] else None
        node["setores_info"] = sectors_info
        xa_bits = (e.get("xa") or {}).get("bits") or []
        disc_logical = f"{logical}#iso9660:{e['path']}"
        if "cdda" in xa_bits:
            self._not_extracted(node, e, disc_logical, "entrada CD-DA (XA)",
                                "entrada marcada CD-DA no registro XA (aponta para áudio); não extraída")
            return
        if e.get("alem_do_fim"):
            self._not_extracted(node, e, disc_logical, "desconhecido",
                                "extensão ultrapassa o fim da faixa de dados; não extraída")
            self.integrity_problem(disc_logical, "extensão do arquivo ultrapassa o fim da faixa de dados (conteúdo ausente na imagem); não extraído")
            return
        raw_parts = [_strip_version(p) for p in e["path"].strip("/").split("/")]
        try:
            parts = check_member_name("/".join(raw_parts))
            clean, _ = sanitize_parts(parts)
            final, _ = allocator.allocate(clean, e["path"])
            dest = safe_join(disc_dir, final)
        except UnsafePath as exc:
            self._not_extracted(node, e, disc_logical, "desconhecido", f"nome recusado: {exc.reason}")
            self.warn(f"{disc_logical}: nome recusado ({exc.reason})")
            return
        self._assert_not_original(dest)
        tmp = dest.with_name(dest.name + ".tsrpart")
        hasher = MultiHasher()
        try:
            ensure_dir(dest.parent)
            remove_quietly(tmp)
            with open(fs(tmp), "wb") as target:
                for chunk in read_extent(stream, e["lba"], e["size"]):
                    hasher.update(chunk)
                    target.write(chunk)
            if hasher.size != e["size"]:
                self.warn(f"{disc_logical}: lidos {hasher.size} de {e['size']} bytes")
            if is_alias(dest):
                raise OSError("o destino é apelido de outro arquivo (ex.: nome curto 8.3 ou link); não gravado")
            if os.path.lexists(fs(dest)):
                remove_quietly(dest)
            os.replace(fs(tmp), fs(dest))
        except OSError as exc:
            remove_quietly(tmp)
            self._not_extracted(node, e, disc_logical, "desconhecido", self.scrub(f"falha ao extrair: {type(exc).__name__}: {exc}"))
            self.error(f"{disc_logical}: falha ao extrair ({type(exc).__name__}: {exc})")
            return
        row = self._file_row(dest, disc_logical, "arquivo_de_disco")
        row["lba"] = e["lba"]
        row["setores"] = e["sectors"]
        row["data"] = e["date"]
        if e.get("xa"):
            row["detalhes_formato"] = dict(row["detalhes_formato"], atributos_xa=e["xa"])
        if sectors_info:
            row["setores_form2"] = sectors_info["form2"]
            self._apply_sector_evidence(row, sectors_info)
        node["extraido"] = True
        node["destino"] = self.redact(dest)
        node["formato"] = row["formato"]
        node["categoria"] = row["categoria"]
        node["sha1"] = row["sha1"]
        node["observacoes"].extend(row["observacoes"])
        file_rows[e["path"].upper()] = row

    def _not_extracted(self, node: dict, e: dict, disc_logical: str, fmt: str, reason: str) -> None:
        """Arquivo do ISO9660 não extraído: ainda gera linha (sem hashes) no inventário."""
        node["extraido"] = False
        node["formato"] = fmt
        node["observacoes"].append(reason)
        self.rows.append(
            {
                "tipo": "arquivo_de_disco",
                "caminho_logico": disc_logical,
                "caminho_local": None,
                "tamanho": e["size"],
                "crc32": None,
                "md5": None,
                "sha1": None,
                "sha256": None,
                "formato": fmt,
                "categoria": "audio_cdda" if fmt == "entrada CD-DA (XA)" else "desconhecido",
                "fonte_assinatura": "registro de diretório ISO9660/CD-XA",
                "detalhes_formato": {"atributos_xa": e.get("xa")} if e.get("xa") else {},
                "indicios": [],
                "entropia": None,
                "entropia_metodo": None,
                "primeiros_16_bytes_hex": None,
                "lba": e["lba"],
                "setores": e["sectors"],
                "setores_form2": None,
                "data": e["date"],
                "observacoes": [reason],
            }
        )

    def _apply_sector_evidence(self, row: dict, info: dict) -> None:
        total = info["setores"]
        form2 = info["form2"]
        xa = info["xa_audio_form2"]
        str_count = info["str_mdec"]
        str_other = info.get("str_outro_sttype", 0)
        if form2:
            row["observacoes"].append(
                f"{form2} de {total} setor(es) Mode2 Form2: a extração em 2048 bytes/setor NÃO preserva o conteúdo Form2 (2324 bytes/setor)"
            )
        source = "psx-spx: CDROM XA Subheader (submode) e CDROM File Video Streaming STR"
        if total and xa == total:
            row["indicios"].append(f"formato por conteúdo do arquivo extraído: {row['formato']}")
            row["formato"] = "XA-ADPCM (setores Mode2 Form2/Audio)"
            row["categoria"] = "audio"
            row["fonte_assinatura"] = source
        elif xa and str_count:
            row["indicios"].append(f"formato por conteúdo do arquivo extraído: {row['formato']}")
            row["formato"] = "STR/XA intercalado (setores)"
            row["categoria"] = "video"
            row["fonte_assinatura"] = source
        elif xa:
            row["observacoes"].append(f"{xa} setor(es) XA-ADPCM (submode Audio + Form2)")
        if str_count and row["formato"] not in ("STR/XA intercalado (setores)",):
            row["observacoes"].append(f"{str_count} setor(es) com cabeçalho STR 0160h/8001h (MDEC)")
        if str_other:
            row["indicios"].append(
                f"{str_other} setor(es) com STR ID 0160h e StType diferente de 8001h (psx-spx lista usos variados; "
                "casamento de 2 bytes; natureza NÃO CONFIRMADA)"
            )

    def _system_cnf(self, disc: dict, tree: List[dict], file_rows: Dict[str, dict], logical: str) -> None:
        cnf_key = next((k for k in sorted(file_rows) if _strip_version(k) == "/SYSTEM.CNF"), None)
        if cnf_key is None:
            disc["system_cnf"] = None
            has_psx_exe = any(_strip_version(k) == "/PSX.EXE" for k in file_rows)
            disc["system_cnf_observacao"] = (
                "SYSTEM.CNF não encontrado na raiz. psx-spx: sem SYSTEM.CNF o BIOS usa PSX.EXE "
                f"(PSX.EXE presente: {'sim' if has_psx_exe else 'não'})."
            )
            self.warn(f"{logical}: SYSTEM.CNF não encontrado")
            return
        cnf_row = file_rows[cnf_key]
        with open_readonly(cnf_row["_path"]) as handle:
            data = handle.read(64 * 1024)
        parsed = parse_system_cnf(data)
        parsed["arquivo_no_disco"] = cnf_key
        boot_path = parsed.get("boot_caminho")
        if boot_path:
            wanted = "/" + boot_path.replace("\\", "/").strip("/").upper()
            match_key = next((k for k in sorted(file_rows) if _strip_version(k) == wanted), None)
            match = file_rows.get(match_key) if match_key else None
            parsed["boot_executavel_presente"] = match is not None
            parsed["boot_executavel_formato"] = match["formato"] if match else None
            if match is None:
                self.warn(f"{logical}: executável de BOOT {boot_path!r} não encontrado no ISO9660")
        disc["system_cnf"] = parsed
        self.custody.record(
            "disco.system_cnf",
            "ok",
            disco=disc["id"],
            boot=parsed.get("BOOT"),
            codigo_produto_derivado=parsed.get("codigo_produto_derivado"),
        )

    # ------------------------------------------------------------ redump
    def _redump(self, dat_path: Path) -> dict:
        try:
            dat = load_dat(dat_path)
        except (RedumpError, OSError) as exc:
            self.error(f"DAT Redump: {exc}")
            self.custody.record("redump", "erro", dat=self.redact(dat_path), erro=str(exc))
            return {"erro": self.scrub(str(exc))}
        items = [item_from_row(r) for r in self.rows if r.get("tipo") in ("original", "extraido", "faixa")]
        items = [i for i in items if i is not None]
        result = match_items(items, dat)
        result["cabecalho"] = dat["cabecalho"]
        result["roms_no_dat"] = len(dat["roms"])
        result["dat"] = self.redact(dat_path)
        self.custody.record(
            "redump",
            "ok",
            dat=self.redact(dat_path),
            correspondencias=len(result["correspondencias"]),
            totais=sum(1 for m in result["correspondencias"] if m["correspondencia_total"]),
        )
        return result

    # ------------------------------------------------------------ inventory
    def _build_inventory(self, original, container, hashes0, st_before, st_after, unchanged, copy_info, redump_result) -> dict:
        disc_rows = [r for r in self.rows if r["tipo"] == "arquivo_de_disco"]
        extracted_rows = [r for r in self.rows if r["tipo"] == "extraido"]
        unknown = [
            {
                "caminho_logico": r["caminho_logico"],
                "tamanho": r["tamanho"],
                "entropia": r["entropia"],
                "primeiros_16_bytes_hex": r["primeiros_16_bytes_hex"],
                "indicios": r["indicios"],
            }
            for r in self.rows
            if r["tipo"] in ("arquivo_de_disco", "extraido") and r["formato"] == "desconhecido"
        ]
        full_match = bool(redump_result and any(m.get("correspondencia_total") for m in redump_result.get("correspondencias", [])))
        evidence = [
            "E1 (evidência direta, sobre ESTE arquivo): tamanhos, hashes, estrutura dos compactados, setores, LBAs, "
            "árvore ISO9660 e valores do SYSTEM.CNF foram medidos diretamente no arquivo fornecido pelo proprietário.",
            "NÃO CONFIRMADO: que este arquivo corresponda à mídia comercial original do jogo"
            + (
                " — há correspondência de hash com o DAT Redump fornecido pelo usuário (Redump = base de dados, "
                "fonte secundária, E3; ver seção de comparação com Redump)."
                if full_match
                else " (nenhuma correspondência com DAT Redump foi verificada nesta execução)."
            ),
            "Identificação de formato: por assinaturas documentadas no psx-spx (" + PSXSPX_URL + "), documentação "
            "técnica de terceiros — fonte secundária (proposta: E3; classificação a confirmar pelo coordenador); o "
            "casamento da assinatura é medido (E1), a interpretação do formato depende dessa fonte. Fontes citadas por arquivo; \"desconhecido\" não é conclusão sobre o conteúdo.",
            "H/NÃO CONFIRMADO: código de produto derivado do SYSTEM.CNF (convenção descrita no psx-spx) até "
            "comparação com a mídia/caixa (E2).",
            "Trechos de conteúdo incluídos (pedidos pela especificação do inventário): os 16 primeiros bytes de cada "
            "arquivo em hexadecimal (em arquivos de até 16 bytes isso é o arquivo inteiro — campo "
            "'primeiros_16_bytes_sao_o_arquivo_inteiro'), campos de cabeçalho (ex.: marcador ASCII do PS-X EXE, nome "
            "do VAG), valores do SYSTEM.CNF e comandos REM/TITLE/PERFORMER do CUE. Nenhum outro conteúdo de arquivo.",
        ]
        for row in self.rows:
            row.pop("_path", None)
        integrity_errors = [p for p in self.integrity if p["nivel"] == "erro"]
        integrity = {
            "situacao": (
                "ALERTA: imagem incompleta ou corrompida"
                if integrity_errors
                else ("indícios a verificar" if self.integrity else "nenhum problema de integridade detectado")
            ),
            "problemas": self.integrity,
            "observacao": (
                "Verificações feitas: arquivos de faixa presentes, tamanho múltiplo do setor, arquivo com todos os "
                "setores declarados, diretórios e arquivos ISO9660 dentro da faixa, tamanho do volume do PVD. "
                "EDC/ECC dos setores NÃO são verificados: ausência de alertas não prova integridade; compare os "
                "hashes das faixas com um DAT Redump (--redump-dat)."
            ),
        }
        inventory = {
            "schema": "tsr-forensic-inventory/1",
            "gerado_em_utc": utc_now_iso(),
            "sessao": self.custody.session_id,
            "kit": environment_info(),
            "limites": self.limits.to_dict(),
            "nota_evidencia": evidence,
            "original": {
                "nome_arquivo": original.name,
                "caminho_registrado": self.redact(original),
                "tamanho": hashes0["size"],
                "hashes": {k: hashes0[k] for k in ("crc32", "md5", "sha1", "sha256")},
                "formato_detectado": container.get("format"),
                "evidencia_formato": container.get("evidence"),
                "fonte_assinatura": container.get("source"),
                "stat_antes": _stat_dict(st_before),
                "stat_depois": _stat_dict(st_after),
                "inalterado": unchanged,
                "copia": copy_info,
            },
            "conteineres": self.containers,
            "discos": self.discs,
            "arquivos": self.rows,
            "contagens": {
                "arquivos_de_disco": report.counts_for(self.rows, "arquivo_de_disco"),
                "extraidos": report.counts_for(self.rows, "extraido"),
                "faixas": report.counts_for(self.rows, "faixa"),
                "total_arquivos_de_disco": len(disc_rows),
                "total_extraidos": len(extracted_rows),
            },
            "desconhecidos": unknown,
            "integridade": integrity,
            "redump": redump_result,
            "avisos": self.warnings,
            "erros": self.errors,
        }
        # Última barreira: nenhum caminho absoluto local (âncoras conhecidas) nos relatórios.
        return self.redact.scrub_obj(inventory, patterns=False)

    # ------------------------------------------------------------ guard registry
    def _register_protected_hashes(self, inventory: dict) -> None:
        """Acrescenta os SHA-256 inventariados a ``<workdir>/protected_sha256.txt``.

        Registro LOCAL e cumulativo (a área de trabalho não vai para o git): o
        ``guard`` continua protegendo arquivos de intakes anteriores mesmo que
        ``forensic_inventory.json`` seja sobrescrito por outro intake.
        """
        wanted = set()
        original_hashes = (inventory.get("original") or {}).get("hashes") or {}
        if original_hashes.get("sha256"):
            wanted.add(str(original_hashes["sha256"]).lower())
        for row in inventory.get("arquivos") or []:
            if row.get("sha256") and row.get("tamanho"):
                wanted.add(str(row["sha256"]).lower())
        for disc in inventory.get("discos") or []:
            for track in disc.get("faixas") or []:
                sha = (track.get("hashes") or {}).get("sha256")
                if sha and (track.get("hashes") or {}).get("size"):
                    wanted.add(str(sha).lower())
        path = self.workdir / PROTECTED_HASHES_NAME
        try:
            existing = set()
            if os.path.isfile(fs(path)):
                with open(fs(path), "r", encoding="utf-8") as handle:
                    existing = {line.strip().lower() for line in handle if line.strip() and not line.startswith("#")}
            new = sorted(wanted - existing)
            ensure_dir(self.workdir)
            with open(fs(path), "a", encoding="utf-8", newline="\n") as handle:
                if not existing and os.path.getsize(fs(path)) == 0:
                    handle.write("# tsr-forensics: SHA-256 de material original inventariado (LOCAL; nunca commitar)\n")
                for sha in new:
                    handle.write(sha + "\n")
            self.custody.record("guard.registro_hashes", "ok", arquivo=self.redact(path), novos=len(new), total=len(existing | wanted))
        except OSError as exc:
            self.warn(f"não foi possível atualizar o registro local de hashes protegidos ({type(exc).__name__}: {exc})")


def run_intake(options: IntakeOptions) -> int:
    try:
        intake = Intake(options)
    except OSError as exc:
        raise IntakeError(
            f"não foi possível preparar a pasta de relatórios (--out) nem o log de custódia ({type(exc).__name__})"
        ) from exc
    try:
        return intake.run()
    except BaseException as exc:  # inclusive falhas inesperadas e Ctrl+C: tudo fica no log de custódia
        if isinstance(exc, KeyboardInterrupt):
            reason = "interrompido pelo usuário (Ctrl+C)"
        elif isinstance(exc, IntakeError):
            reason = str(exc)
        else:
            reason = f"falha inesperada ({type(exc).__name__}: {exc})"
        intake.abort(reason, exc)
        raise
