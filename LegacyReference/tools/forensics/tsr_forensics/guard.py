"""Comandos ``guard`` e ``install-hook``: impedem versionar material original.

``guard`` examina arquivos do índice do git (``--staged``: somente os
adicionados/modificados no commit; padrão: todos os rastreados) ou de um
diretório (``--dir``) e acusa:

1. extensões de imagem de disco, arquivos compactados, subcanal e formatos
   PS1 (lista em ``FORBIDDEN_EXTENSIONS``);
2. assinaturas de conteúdo PS1/disco/compactado nos primeiros bytes
   (PS-X EXE, CPE, TIM, VAGp, pBAV, pQES, STR 0160h/8001h, sync de setor
   bruto, CD001 de ISO9660, RIFF/CDXA, 7z/zip/rar/gzip/bzip2/xz/zstd/ECM/CHD/
   PBP/SBI/MDS) — fontes em ``sniff.py`` e ``signatures.py``;
3. arquivos binários maiores que o limite (``--max-binary-size``) e arquivos
   de texto maiores que ``--max-text-size``;
4. conteúdo binário CODIFICADO em texto: se o início do arquivo é base64 ou
   hexadecimal, os bytes decodificados passam pelas mesmas assinaturas da
   regra 2; texto grande (>= 1 MiB) quase só com caracteres base64/hex e sem
   espaços também é acusado;
5. qualquer arquivo cujo SHA-256 conste de material original já inventariado:
   ``forensic_inventory.json``, os registros ``original.hash``/cópias do
   ``custody_log.jsonl`` ao lado dele e o registro LOCAL cumulativo
   ``LegacyReference/_work/protected_sha256.txt`` (gravado por cada intake;
   continua protegendo intakes anteriores mesmo que o inventário seja
   sobrescrito) e ``--hash-list``. Esta regra NUNCA é liberada por lista de
   permissões.

O conteúdo é lido do ÍNDICE do git (o que de fato seria commitado), via
``git cat-file --batch``. Sai com código 1 se encontrar algo, 0 se limpo e
2 em erro de uso/ambiente.
"""

from __future__ import annotations

import base64
import binascii
import fnmatch
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Set, Tuple

from . import report, sniff
from .config import FORENSICS_DIR, MIB
from .signatures import SYNC, detect_from_head

HEAD = 64 * 1024
ENCODED_TEXT_MIN = 1 << 20  # texto >= 1 MiB com cara de base64/hex é acusado
_B64_RUN = re.compile(rb"[A-Za-z0-9+/]*")
_HEX_RUN = re.compile(rb"[0-9A-Fa-f]*")
_B64_ALPHABET = frozenset(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=")
HOOK_MARKER = "tsr-forensics-guard-hook"
ALLOWLIST_FILE = FORENSICS_DIR / "guard_allowlist.txt"

FORBIDDEN_EXTENSIONS = {
    # arquivos compactados
    ".7z", ".zip", ".rar", ".gz", ".tgz", ".bz2", ".tbz2", ".xz", ".txz", ".zst", ".tar",
    # imagens de disco e subcanal
    ".iso", ".bin", ".cue", ".img", ".ccd", ".sub", ".sbi", ".mds", ".mdf", ".chd", ".ecm",
    ".pbp", ".toc", ".cdi", ".nrg",
    # formatos PS1 (psx-spx: TIM, VAG, VAB/VH/VB, SEQ/SEP, STR, XA, TMD, CPE)
    ".tim", ".vag", ".vab", ".vh", ".vb", ".seq", ".sep", ".str", ".xa", ".tmd", ".cpe", ".psx",
    # memory card / saves
    ".mcr", ".mcd", ".gme", ".psv", ".vgs", ".srm",
    # sobra de extração interrompida do próprio kit (conteúdo parcial do jogo)
    ".tsrpart",
}

# Contêineres binários acusados por conteúdo (CUE/CCD textuais são tratados pela extensão,
# para não acusar documentação que cite comandos de CUE).
BLOCKED_CONTAINERS = {
    "7z", "zip", "rar4", "rar5", "gzip", "bzip2", "xz", "zstd", "tar", "ecm", "chd", "pbp", "sbi", "mds",
    "iso9660", "cd_raw_2352", "cd_raw_2336",
}


@dataclass
class Candidate:
    path: str  # relativo ao repositório (ou ao diretório), com '/'
    size: int = 0
    sha256: str = ""
    head: bytes = b""
    binary: bool = False
    reasons: List[str] = field(default_factory=list)


def content_reasons(head: bytes, size: int) -> List[str]:
    reasons: List[str] = []
    if head[:8] == b"PS-X EXE":
        reasons.append("assinatura PS-X EXE (psx-spx)")
    if head[:4] == b"CPE\x01":
        reasons.append("assinatura CPE (PsyQ, psx-spx)")
    if sniff.tim_header_matches(head):
        reasons.append("cabeçalho TIM 10h 00h 0000h + flags válidas (psx-spx)")
    if head[:4] == b"VAGp":
        reasons.append("assinatura VAGp (psx-spx)")
    if head[:4] == b"pBAV":
        reasons.append("assinatura pBAV (VAB/VH, psx-spx)")
    if head[:4] == b"pQES":
        reasons.append("assinatura pQES (SEQ/SEP, psx-spx)")
    if head[:4] == b"\x60\x01\x01\x80":
        reasons.append("cabeçalho de setor STR 0160h/8001h (psx-spx)")
    if head[:12] == SYNC:
        reasons.append("padrão de sync de setor bruto de CD (psx-spx)")
    if head[:4] == b"RIFF" and head[8:12] == b"CDXA":
        reasons.append("RIFF/CDXA (psx-spx)")
    detected = detect_from_head(head, size).get("format")
    if detected in BLOCKED_CONTAINERS:
        reasons.append(f"assinatura de contêiner/imagem: {detected}")
    return reasons


def _decoded_views(head: bytes) -> List[Tuple[str, bytes]]:
    """Decodifica o início de um texto que seja base64 (com ou sem ``data:...;base64,``) ou hexadecimal."""
    views: List[Tuple[str, bytes]] = []
    text = head.lstrip(b"\xef\xbb\xbf \t\r\n")
    marker = text.find(b"base64,", 0, 256)
    if marker >= 0:
        text = text[marker + 7:]
    # base64: quebras de linha são permitidas, espaços não (texto comum tem espaços)
    compact = re.sub(rb"[\r\n]+", b"", text)
    run = _B64_RUN.match(compact).group(0)
    if len(run) >= 64:
        run = run[: len(run) - len(run) % 4]
        try:
            views.append(("base64", base64.b64decode(run, validate=True)))
        except (binascii.Error, ValueError):
            pass
    compact = re.sub(rb"\s+", b"", re.sub(rb"0x", b"", text[:HEAD]))
    run = _HEX_RUN.match(compact).group(0)
    if len(run) >= 64:
        run = run[: len(run) - len(run) % 2]
        try:
            views.append(("hexadecimal", bytes.fromhex(run.decode("ascii"))))
        except ValueError:
            pass
    return views


def encoded_reasons(head: bytes, size: int) -> List[str]:
    """Assinaturas encontradas em conteúdo codificado em texto (base64/hex)."""
    reasons: List[str] = []
    for label, data in _decoded_views(head):
        for reason in content_reasons(data, len(data)):
            reasons.append(f"conteúdo {label} decodificado: {reason}")
    if size >= ENCODED_TEXT_MIN:
        sample = head.replace(b"\r", b"").replace(b"\n", b"")
        if sample:
            dense = sum(1 for b in sample if b in _B64_ALPHABET) / len(sample)
            spaces = sample.count(b" ") / len(sample)
            if dense >= 0.97 and spaces < 0.01:
                reasons.append(
                    f"texto grande ({size} bytes) com aparência de dados binários codificados (base64/hex)"
                )
    return reasons


def _custody_hashes(path: Path) -> Set[str]:
    """SHA-256 de originais e cópias registrados no log de custódia."""
    found: Set[str] = set()
    try:
        handle = open(path, "rb")
    except OSError:
        return found
    with handle:
        for raw in handle:
            try:
                record = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            details = record.get("details") or {}
            step = record.get("step")
            if step == "original.hash":
                sha = (details.get("hashes") or {}).get("sha256")
                if sha and (details.get("hashes") or {}).get("size"):
                    found.add(str(sha).lower())
            elif step in ("copia.verificada", "copia.preservada") and details.get("sha256"):
                found.add(str(details["sha256"]).lower())
            elif step == "original.divergente" and details.get("sha256_atual"):
                found.add(str(details["sha256_atual"]).lower())
    return found


def load_hash_lists(paths: Iterable[Path]) -> Tuple[Set[str], List[str]]:
    hashes: Set[str] = set()
    loaded: List[str] = []
    for path in paths:
        try:
            with open(path, "r", encoding="utf-8") as handle:
                for line in handle:
                    value = line.strip().split()[0].lower() if line.strip() else ""
                    if re.fullmatch(r"[0-9a-f]{64}", value):
                        hashes.add(value)
        except FileNotFoundError:
            continue
        except (OSError, UnicodeDecodeError) as exc:
            print(f"[guard] aviso: lista de hashes ilegível {path}: {exc}", file=sys.stderr)
            continue
        loaded.append(str(path))
    return hashes, loaded


def load_inventory_hashes(paths: Iterable[Path]) -> Tuple[Set[str], List[str]]:
    hashes: Set[str] = set()
    loaded: List[str] = []
    for path in paths:
        custody = Path(path).with_name(report.CUSTODY_NAME)
        if custody.is_file():
            hashes |= _custody_hashes(custody)
            loaded.append(str(custody))
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except FileNotFoundError:
            continue
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[guard] aviso: inventário ilegível {path}: {exc}", file=sys.stderr)
            continue
        loaded.append(str(path))
        original = data.get("original") or {}
        if (original.get("hashes") or {}).get("sha256") and original.get("tamanho"):
            hashes.add(original["hashes"]["sha256"].lower())
        for row in data.get("arquivos") or []:
            if row.get("sha256") and row.get("tamanho"):
                hashes.add(str(row["sha256"]).lower())
        for disc in data.get("discos") or []:
            for track in disc.get("faixas") or []:
                h = track.get("hashes") or {}
                if h.get("sha256") and h.get("size"):
                    hashes.add(str(h["sha256"]).lower())
    return hashes, loaded


def load_allowlist(extra: Iterable[str]) -> List[str]:
    patterns = [p for p in extra if p]
    try:
        with open(ALLOWLIST_FILE, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.append(line)
    except FileNotFoundError:
        pass
    return patterns


def _is_allowed(path: str, patterns: List[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


def _git(repo: Path, *args: str) -> bytes:
    result = subprocess.run(["git", "-C", str(repo), *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode("utf-8", "replace").strip() or f"git {' '.join(args)} falhou")
    return result.stdout


class _Consumer:
    def __init__(self) -> None:
        self.sha = hashlib.sha256()
        self.head = bytearray()
        self.size = 0
        self.nul = False
        self.utf8_ok = True
        self._probe = bytearray()

    def __call__(self, data: bytes) -> None:
        self.sha.update(data)
        self.size += len(data)
        if len(self.head) < HEAD:
            self.head += data[: HEAD - len(self.head)]
        if len(self._probe) < 8192:
            piece = data[: 8192 - len(self._probe)]
            self._probe += piece
            if b"\x00" in piece:
                self.nul = True

    def finish(self, candidate: Candidate) -> None:
        candidate.size = self.size
        candidate.sha256 = self.sha.hexdigest()
        candidate.head = bytes(self.head)
        probe = bytes(self._probe)
        binary = self.nul
        if not binary:
            try:
                probe.decode("utf-8")
            except UnicodeDecodeError as exc:
                binary = exc.start < len(probe) - 4  # tolera caractere cortado no fim da amostra
        candidate.binary = binary


class _CatFile:
    def __init__(self, repo: Path):
        self.proc = subprocess.Popen(
            ["git", "-C", str(repo), "cat-file", "--batch"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )

    def stream(self, sha: str, consumer: Callable[[bytes], None]) -> None:
        assert self.proc.stdin is not None and self.proc.stdout is not None
        self.proc.stdin.write(sha.encode("ascii") + b"\n")
        self.proc.stdin.flush()
        header = self.proc.stdout.readline().decode("ascii", "replace").split()
        if len(header) < 3 or header[1] == "missing":
            raise RuntimeError(f"objeto git ausente: {sha}")
        remaining = int(header[2])
        while remaining > 0:
            data = self.proc.stdout.read(min(1 << 20, remaining))
            if not data:
                raise RuntimeError("fim inesperado da saída do git cat-file")
            consumer(data)
            remaining -= len(data)
        self.proc.stdout.read(1)

    def close(self) -> None:
        try:
            if self.proc.stdin:
                self.proc.stdin.close()
            self.proc.wait(timeout=30)
        except Exception:
            self.proc.kill()


def _index_entries(repo: Path) -> Dict[str, Tuple[str, str]]:
    raw = _git(repo, "ls-files", "-s", "-z")
    entries: Dict[str, Tuple[str, str]] = {}
    for item in raw.split(b"\x00"):
        if not item:
            continue
        meta, _, path = item.partition(b"\t")
        mode, sha, _stage = meta.decode("ascii").split()
        entries[path.decode("utf-8", "surrogateescape")] = (mode, sha)
    return entries


def collect_git(repo: Path, staged: bool) -> List[Candidate]:
    entries = _index_entries(repo)
    if staged:
        raw = _git(repo, "diff", "--cached", "--name-only", "-z", "--diff-filter=ACMRT")
        wanted = [p.decode("utf-8", "surrogateescape") for p in raw.split(b"\x00") if p]
    else:
        wanted = sorted(entries)
    candidates: List[Candidate] = []
    reader = _CatFile(repo)
    try:
        for path in wanted:
            entry = entries.get(path)
            candidate = Candidate(path=path)
            if entry is None:
                continue
            mode, sha = entry
            if mode == "160000":  # submódulo
                continue
            if mode == "120000":  # link simbólico: só a regra de extensão se aplica
                candidates.append(candidate)
                continue
            consumer = _Consumer()
            reader.stream(sha, consumer)
            consumer.finish(candidate)
            candidates.append(candidate)
    finally:
        reader.close()
    return candidates


def collect_dir(directory: Path) -> List[Candidate]:
    candidates: List[Candidate] = []
    for root, dirs, files in os.walk(directory, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d != ".git")
        for name in sorted(files):
            full = Path(root) / name
            rel = full.relative_to(directory).as_posix()
            candidate = Candidate(path=rel)
            if full.is_symlink():
                candidates.append(candidate)
                continue
            consumer = _Consumer()
            try:
                with open(full, "rb") as handle:
                    while True:
                        data = handle.read(1 << 20)
                        if not data:
                            break
                        consumer(data)
            except OSError as exc:
                candidate.reasons.append(f"ilegível: {exc}")
                candidates.append(candidate)
                continue
            consumer.finish(candidate)
            candidates.append(candidate)
    return candidates


def evaluate(candidates: List[Candidate], inventory_hashes: Set[str], max_binary: int, allow: List[str],
             max_text: int = 20 * MIB) -> List[Candidate]:
    findings: List[Candidate] = []
    for candidate in candidates:
        reasons = list(candidate.reasons)
        if candidate.sha256 and candidate.size and candidate.sha256 in inventory_hashes:
            reasons.append("SHA-256 consta da lista de material original inventariado "
                           "(forensic_inventory.json, custody_log.jsonl, protected_sha256.txt ou --hash-list)")
        allowed = _is_allowed(candidate.path, allow)
        if not allowed:
            suffix = os.path.splitext(candidate.path)[1].lower()
            if suffix in FORBIDDEN_EXTENSIONS:
                reasons.append(f"extensão bloqueada ({suffix})")
            if candidate.head:
                reasons.extend(content_reasons(candidate.head, candidate.size))
                if not candidate.binary:
                    reasons.extend(encoded_reasons(candidate.head, candidate.size))
            if candidate.binary and candidate.size > max_binary:
                reasons.append(f"arquivo binário grande ({candidate.size} bytes > limite {max_binary})")
            if not candidate.binary and candidate.size > max_text:
                reasons.append(f"arquivo de texto grande ({candidate.size} bytes > limite {max_text})")
        if reasons:
            candidate.reasons = reasons
            findings.append(candidate)
    return findings


def default_inventory(repo: Path) -> Path:
    return repo / "LegacyReference" / "inventory" / report.JSON_NAME


def default_hash_list(repo: Path) -> Path:
    return repo / "LegacyReference" / "_work" / "protected_sha256.txt"


def run_guard(repo: Path, staged: bool = False, directory: Optional[Path] = None,
              inventories: Optional[List[Path]] = None, max_binary: int = 5 * MIB,
              allow: Optional[List[str]] = None, quiet: bool = False,
              hash_lists: Optional[List[Path]] = None, max_text: int = 20 * MIB) -> int:
    inventory_paths = list(inventories or [])
    if not inventory_paths:
        inventory_paths = [default_inventory(repo)]
    hashes, loaded = load_inventory_hashes(inventory_paths)
    extra, extra_loaded = load_hash_lists(list(hash_lists or []) + [default_hash_list(repo)])
    hashes |= extra
    loaded += extra_loaded
    patterns = load_allowlist(allow or [])
    try:
        if directory is not None:
            candidates = collect_dir(Path(directory))
            scope = f"diretório {directory}"
        else:
            candidates = collect_git(repo, staged)
            scope = "arquivos staged" if staged else "arquivos rastreados (índice)"
    except (RuntimeError, OSError) as exc:
        print(f"[guard] ERRO: {exc}", file=sys.stderr)
        return 2
    findings = evaluate(candidates, hashes, max_binary, patterns, max_text)
    if not quiet:
        print(
            f"[guard] {len(candidates)} arquivo(s) verificados ({scope}); "
            f"inventário: {', '.join(loaded) if loaded else 'nenhum encontrado'} ({len(hashes)} hashes)."
        )
    if findings:
        print(f"[guard] BLOQUEADO: {len(findings)} arquivo(s) suspeito(s) de conter material original:", file=sys.stderr)
        for item in findings:
            print(f"[guard]   - {item.path}: " + "; ".join(item.reasons), file=sys.stderr)
        print(
            "[guard] Este repositório é PÚBLICO: ROM/ISO/BIOS/assets do jogo não podem ser versionados. "
            "Remova do stage com: git restore --staged <arquivo>",
            file=sys.stderr,
        )
        return 1
    if not quiet:
        print("[guard] OK: nenhum material original detectado.")
    return 0


# ---------------------------------------------------------------- install-hook


def _sh_quote(text: str) -> str:
    return "'" + text.replace("'", "'\\''") + "'"


def _sh_path(path: Path) -> str:
    text = str(path)
    if os.name == "nt":
        text = text.replace("\\", "/")
    return text


def hook_script(python: str, kit_dir: Path) -> str:
    return f"""#!/bin/sh
# {HOOK_MARKER} v1 — gerado por "python -m tsr_forensics install-hook". Não editar à mão.
# Bloqueia commits que contenham material original do jogo (ROM/ISO/BIOS/assets).
TOP=$(git rev-parse --show-toplevel) || exit 1
KIT={_sh_quote(_sh_path(kit_dir))}
if [ ! -d "$KIT/tsr_forensics" ]; then
  KIT="$TOP/LegacyReference/tools/forensics"
fi
if [ ! -d "$KIT/tsr_forensics" ]; then
  echo "[guard] kit forense não encontrado; commit bloqueado por segurança." >&2
  exit 1
fi
CHECK="import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"
PY={_sh_quote(_sh_path(Path(python)))}
if ! "$PY" -c "$CHECK" >/dev/null 2>&1; then
  PY=""
  # Cada candidato precisa EXECUTAR (no Windows, "python3" pode ser só o
  # atalho da Microsoft Store, que existe no PATH mas não roda Python).
  for candidate in python3 python py; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c "$CHECK" >/dev/null 2>&1; then
      PY="$candidate"
      break
    fi
  done
fi
if [ -z "$PY" ]; then
  echo "[guard] Python 3.10+ não encontrado (testados: o Python registrado na instalação do hook, python3, python, py;" >&2
  echo "[guard] no Windows, 'python3'/'python' podem ser atalhos da Microsoft Store que não executam Python)." >&2
  echo "[guard] Commit bloqueado por segurança. Reinstale o hook com o Python do kit: python -m tsr_forensics install-hook --force" >&2
  exit 1
fi
cd "$KIT" || exit 1
exec "$PY" -m tsr_forensics guard --staged --repo "$TOP"
"""


def install_hook(repo: Path, force: bool = False, python: Optional[str] = None) -> int:
    try:
        top = Path(_git(repo, "rev-parse", "--show-toplevel").decode("utf-8").strip())
        hooks_rel = _git(repo, "rev-parse", "--git-path", "hooks").decode("utf-8").strip()
    except (RuntimeError, OSError) as exc:
        print(f"[install-hook] ERRO: {exc}", file=sys.stderr)
        return 2
    configured = subprocess.run(
        ["git", "-C", str(repo), "config", "--get", "core.hooksPath"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    ).stdout.decode("utf-8").strip()
    if configured and not force:
        print(
            f"[install-hook] core.hooksPath está configurado ({configured}); instalar ali afetaria outros "
            "repositórios. Use --force se tiver certeza.",
            file=sys.stderr,
        )
        return 2
    hooks_dir = Path(hooks_rel)
    if not hooks_dir.is_absolute():
        hooks_dir = Path(repo) / hooks_dir
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook = hooks_dir / "pre-commit"
    if hook.exists():
        current = hook.read_text(encoding="utf-8", errors="replace")
        if HOOK_MARKER not in current:
            if not force:
                print(
                    f"[install-hook] já existe um pre-commit hook que não é deste kit: {hook}. "
                    "Use --force para substituí-lo (uma cópia de segurança será criada).",
                    file=sys.stderr,
                )
                return 2
            import datetime as _dt

            stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            backup = hook.with_name(f"pre-commit.backup-{stamp}")
            hook.replace(backup)
            print(f"[install-hook] hook anterior salvo em {backup}")
    script = hook_script(python or sys.executable, FORENSICS_DIR)
    with open(hook, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(script)
    os.chmod(hook, 0o755)
    print(f"[install-hook] pre-commit instalado em {hook} (repositório {top}).")
    print("[install-hook] Teste: stage um arquivo e rode 'git commit'; o guard será executado antes do commit.")
    return 0


def describe_command(argv: List[str]) -> str:
    return " ".join(shlex.quote(a) for a in argv)
