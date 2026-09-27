"""Listagem e extração segura de arquivos compactados (zip, 7z, tar, gz, bz2, xz).

Proteções:

* nomes validados por ``safepath`` (zip-slip: ``..``, absolutos, letras de
  unidade, byte nulo) e destino conferido com ``realpath``;
* links simbólicos, junções, dispositivos e entradas criptografadas são
  recusados (registrados, nunca extraídos);
* anti-bomba: limite de número de entradas, de tamanho por entrada, de total
  extraído (orçamento compartilhado pelo intake inteiro) e de razão de
  compressão — por entrada (ZIP) e TOTAL do compactado (todos os formatos:
  soma dos tamanhos declarados / tamanho do compactado); os limites são
  conferidos ANTES (tamanhos declarados) e DURANTE a extração (bytes
  realmente descompactados, somados por compactado), de modo que dividir o
  conteúdo em muitas entradas pequenas ou declarar tamanhos falsos não
  contorna a proteção;
* métodos de compressão que a biblioteca padrão não lê (ex.: ZIP Deflate64)
  e entradas criptografadas são recusados com motivo explícito e contam como
  ERRO (conteúdo não inventariado);
* escrita atômica (arquivo temporário + ``os.replace``) e idempotência:
  uma entrada já presente com mesmo tamanho e CRC32 é mantida.

A extração do 7z usa ``py7zr`` com uma *WriterFactory* própria: o py7zr nunca
escolhe caminhos no disco; ele só entrega bytes para destinos já validados.
Se o py7zr pedir saída para um nome fora do plano (ex.: nome duplicado, que o
py7zr renomeia para ``nome_0``), os bytes vão para um destino descartável que
só calcula tamanho e hashes (registrados), sem interromper as demais entradas.
"""

from __future__ import annotations

import bz2
import datetime as _dt
import gzip
import lzma
import os
import posixpath
import stat
import tarfile
import threading
import zipfile
import zlib
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Dict, List, Optional

from .config import Limits
from .fsutil import ensure_dir, fs, is_alias, open_readonly, remove_quietly
from .hashing import MultiHasher
from .safepath import NameAllocator, UnsafePath, check_member_name, safe_join, sanitize_parts

CHUNK = 1 << 20
TMP_SUFFIX = ".tsrpart"
ZIP_METHODS = {
    0: "stored",
    8: "deflate",
    9: "deflate64",
    12: "bzip2",
    14: "lzma",
    93: "zstd",
    95: "xz",
    98: "ppmd",
    99: "aes (criptografado)",
}
# Métodos que o ``zipfile`` da biblioteca padrão consegue descompactar.
ZIP_SUPPORTED_METHODS = {0, 8, 12, 14} | ({93} if hasattr(zipfile, "ZIP_ZSTANDARD") else set())
# Sufixo da pasta onde um compactado aninhado é extraído (reservado no plano).
NESTED_SUFFIX = ".extracted"
SINGLE_STREAM = {
    "gzip": (gzip.open, {".tgz": ".tar", ".gz": ""}),
    "bzip2": (bz2.open, {".tbz2": ".tar", ".tbz": ".tar", ".bz2": ""}),
    "xz": (lzma.open, {".txz": ".tar", ".xz": ""}),
}


class ArchiveError(Exception):
    pass


class LimitExceeded(ArchiveError):
    pass


class Budget:
    """Orçamento de bytes extraídos compartilhado (thread-safe)."""

    def __init__(self, total: int):
        self.total = total
        self.used = 0
        self._lock = threading.Lock()

    @property
    def remaining(self) -> int:
        return self.total - self.used

    def consume(self, amount: int) -> None:
        with self._lock:
            if self.used + amount > self.total:
                raise LimitExceeded(
                    f"limite total de extração excedido ({self.total} bytes); use --max-total-bytes para ajustar"
                )
            self.used += amount


# ---------------------------------------------------------------- listing


def _entry(name: str, **kw) -> dict:
    data = {
        "nome": name,
        "diretorio": False,
        "link": False,
        "especial": False,
        "tamanho": None,
        "tamanho_compactado": None,
        "crc32": None,
        "data": None,
        "metodo": None,
        "criptografado": False,
    }
    data.update(kw)
    return data


def list_archive(path: Path, fmt: str) -> dict:
    """Lista as entradas SEM extrair. Nunca escreve no disco."""
    if fmt == "zip":
        return _list_zip(path)
    if fmt == "7z":
        return _list_7z(path)
    if fmt == "tar":
        return _list_tar(path)
    if fmt in SINGLE_STREAM:
        return _list_single(path, fmt)
    raise ArchiveError(f"formato {fmt} reconhecido, mas listagem/extração não suportada por este kit")


def _list_zip(path: Path) -> dict:
    entries = []
    with open_readonly(path) as handle, zipfile.ZipFile(handle) as archive:
        for info in archive.infolist():
            mode = (info.external_attr >> 16) & 0xFFFF
            file_type = stat.S_IFMT(mode)
            # Só interpreta o tipo quando o compactador gravou bits de tipo Unix.
            is_link = info.create_system == 3 and file_type == stat.S_IFLNK
            special = info.create_system == 3 and file_type not in (0, stat.S_IFREG, stat.S_IFDIR, stat.S_IFLNK)
            try:
                date = _dt.datetime(*info.date_time).isoformat()
            except ValueError:
                date = None
            entries.append(
                _entry(
                    info.filename,
                    diretorio=info.is_dir(),
                    link=is_link,
                    especial=special,
                    tamanho=info.file_size,
                    tamanho_compactado=info.compress_size,
                    crc32=f"{info.CRC:08x}",
                    data=date,
                    data_observacao="horário local do compactador (formato DOS, sem fuso)" if date else None,
                    metodo=ZIP_METHODS.get(info.compress_type, f"método {info.compress_type}"),
                    metodo_codigo=info.compress_type,
                    criptografado=bool(info.flag_bits & 0x1),
                    nome_utf8=bool(info.flag_bits & 0x800),
                )
            )
        comment = archive.comment
    return {"formato": "zip", "entradas": entries, "info": {"comentario_bytes": len(comment)}}


def _list_7z(path: Path) -> dict:
    import py7zr
    from py7zr.helpers import ArchiveTimestamp  # type: ignore

    entries = []
    with py7zr.SevenZipFile(fs(path), mode="r") as archive:
        try:
            info = archive.archiveinfo()
            method_names = list(getattr(info, "method_names", []) or [])
            solid = bool(getattr(info, "solid", False))
            blocks = getattr(info, "blocks", None)
        except Exception:  # arquivo vazio ou cabeçalho atípico
            method_names, solid, blocks = [], None, None
        methods = ", ".join(method_names)
        # py7zr.needs_password() indica apenas se uma senha foi FORNECIDA;
        # a criptografia é detectada pelo método (7zAES) das pastas.
        encrypted = any("aes" in m.lower() for m in method_names)
        items = list(archive.files)
        # 7z sólido: vários arquivos compartilham um bloco ("folder"); o py7zr
        # devolve o tamanho empacotado do BLOCO no 1º arquivo e None nos demais.
        # Nesse caso não existe tamanho compactado por arquivo: fica null e o
        # tamanho do bloco é registrado à parte.
        folder_of = {id(item): getattr(item, "folder", None) for item in items}
        per_folder = Counter(id(f) for f in folder_of.values() if f is not None)
        folder_index: Dict[int, int] = {}
        for item in items:
            folder = folder_of[id(item)]
            if folder is not None and id(folder) not in folder_index:
                folder_index[id(folder)] = len(folder_index)
        for item in items:
            date = None
            stamp = item.lastwritetime
            if stamp is not None:
                try:
                    date = _dt.datetime.fromtimestamp(ArchiveTimestamp(stamp).totimestamp(), _dt.timezone.utc).isoformat()
                except (OverflowError, OSError, ValueError):
                    date = None
            folder = folder_of[id(item)]
            shared = folder is not None and per_folder[id(folder)] > 1
            extra = {}
            if folder is not None:
                extra["bloco"] = folder_index[id(folder)]
            if shared:
                extra["tamanho_compactado_observacao"] = (
                    f"7z sólido: bloco {folder_index[id(folder)]} compartilhado por {per_folder[id(folder)]} arquivos; "
                    "não existe tamanho compactado por arquivo"
                )
                if item.compressed is not None:
                    extra["tamanho_compactado_bloco"] = item.compressed
            entries.append(
                _entry(
                    item.filename,
                    diretorio=bool(item.is_directory),
                    link=bool(item.is_symlink or item.is_junction),
                    especial=bool(item.is_socket),
                    tamanho=0 if item.emptystream else item.uncompressed,
                    tamanho_compactado=None if shared else item.compressed,
                    crc32=None if item.crc32 is None else f"{item.crc32 & 0xFFFFFFFF:08x}",
                    data=date,
                    metodo=methods or None,
                    criptografado=encrypted and not item.emptystream,
                    **extra,
                )
            )
        archive_info = {
            "solido": solid,
            "blocos": blocks,
            "metodos": methods or None,
            "criptografado": encrypted,
        }
    return {"formato": "7z", "entradas": entries, "info": archive_info}


def _list_tar(path: Path) -> dict:
    entries = []
    with open_readonly(path) as handle, tarfile.open(fileobj=handle, mode="r:*") as archive:
        for member in archive:
            entries.append(
                _entry(
                    member.name,
                    diretorio=member.isdir(),
                    link=member.issym() or member.islnk(),
                    especial=not (member.isreg() or member.isdir() or member.issym() or member.islnk()),
                    tamanho=member.size if member.isreg() else 0,
                    data=_dt.datetime.fromtimestamp(member.mtime, _dt.timezone.utc).isoformat() if member.mtime else None,
                    metodo="tar",
                )
            )
    return {"formato": "tar", "entradas": entries, "info": {}}


def _single_output_name(path: Path, fmt: str) -> str:
    lower = path.name.lower()
    for suffix, replacement in SINGLE_STREAM[fmt][1].items():
        if lower.endswith(suffix):
            return (path.name[: -len(suffix)] + replacement) or "conteudo"
    return path.name + ".descompactado"


def _list_single(path: Path, fmt: str) -> dict:
    name = _single_output_name(path, fmt)
    return {
        "formato": fmt,
        "entradas": [_entry(name, tamanho=None, metodo=fmt, observacao="fluxo único; tamanho conhecido só após descompactar")],
        "info": {"nome_saida_derivado_do_nome_do_arquivo": True},
    }


# ---------------------------------------------------------------- planning


def plan_extraction(listing: dict, archive_size: int, dest_dir: Path, limits: Limits, budget: Budget) -> dict:
    """Valida nomes e limites. Retorna ``{"plano": [...], "recusadas": [...], "erro_fatal": str|None}``."""
    entries = listing["entradas"]
    rejected: List[dict] = []
    plan: List[dict] = []
    if len(entries) > limits.max_entries:
        return {"plano": [], "recusadas": [], "erro_fatal": f"{len(entries)} entradas excede o limite de {limits.max_entries}"}
    declared = sum(e["tamanho"] or 0 for e in entries if not e["diretorio"])
    if declared > budget.remaining:
        return {
            "plano": [],
            "recusadas": [],
            "erro_fatal": f"tamanho declarado ({declared} bytes) excede o orçamento restante de extração ({budget.remaining} bytes)",
        }
    fmt = listing["formato"]
    if fmt == "zip":
        for e in entries:
            size, packed = e["tamanho"] or 0, e["tamanho_compactado"] or 0
            if size >= limits.ratio_min_bytes and packed > 0 and size / packed > limits.max_ratio:
                return {
                    "plano": [],
                    "recusadas": [],
                    "erro_fatal": (
                        f"entrada {e['nome']!r}: razão de compressão {size / packed:.1f} > {limits.max_ratio} "
                        "(possível bomba de descompressão; ajuste --max-ratio se for legítimo)"
                    ),
                }
    # Razão TOTAL (todos os formatos, inclusive ZIP): impede contornar o limite
    # dividindo o conteúdo em várias entradas menores que --ratio-min-bytes.
    if archive_size > 0 and declared >= limits.ratio_min_bytes and declared / archive_size > limits.max_ratio:
        return {
            "plano": [],
            "recusadas": [],
            "erro_fatal": (
                f"razão de compressão total {declared / archive_size:.1f} > {limits.max_ratio} "
                "(possível bomba de descompressão; ajuste --max-ratio se for legítimo)"
            ),
        }
    allocator = NameAllocator()
    seen_names: Dict[str, int] = {}
    for index, e in enumerate(entries):
        name = e["nome"]
        if e["diretorio"]:
            continue
        reason = None
        # grave=True: o conteúdo existe mas o kit não consegue lê-lo (inventário
        # incompleto) — o intake registra como ERRO, não como aviso.
        grave = False
        if e["link"]:
            reason = "link simbólico/junção (não extraído por segurança)"
        elif e["especial"]:
            reason = "entrada especial (dispositivo/socket/fifo)"
        elif e["criptografado"]:
            reason = "entrada criptografada (sem senha; não extraída; conteúdo NÃO inventariado)"
            grave = True
        elif fmt == "zip" and e.get("metodo_codigo") is not None and e["metodo_codigo"] not in ZIP_SUPPORTED_METHODS:
            reason = (
                f"método de compressão ZIP {e.get('metodo')} (código {e['metodo_codigo']}) não suportado pela "
                "biblioteca padrão do Python; conteúdo NÃO inventariado (recompacte com outro método ou extraia "
                "com outra ferramenta e rode o intake no resultado)"
            )
            grave = True
        elif e["tamanho"] is not None and e["tamanho"] > limits.max_entry_bytes:
            reason = f"tamanho declarado {e['tamanho']} excede --max-entry-bytes ({limits.max_entry_bytes})"
            grave = True
        parts: List[str] = []
        if reason is None:
            try:
                parts = check_member_name(name)
            except UnsafePath as exc:
                reason = exc.reason
        if reason is None and fmt == "7z":
            key = name.replace("\\", "/")
            if key in seen_names:
                reason = "nome duplicado no 7z (apenas a primeira ocorrência é extraída)"
            seen_names[key] = index
        if reason is not None:
            rejected.append({"indice": index, "nome": name, "motivo": reason, "grave": grave})
            e["status"] = "recusada"
            e["motivo_recusa"] = reason
            continue
        clean, changed = sanitize_parts(parts)
        # "<nome>.extracted" fica reservado para a extração de um compactado aninhado.
        final, renamed = allocator.allocate(clean, name, reserve_suffix=NESTED_SUFFIX)
        try:
            dest = safe_join(dest_dir, final)
        except UnsafePath as exc:
            rejected.append({"indice": index, "nome": name, "motivo": exc.reason, "grave": exc.reason.startswith("falha ao validar")})
            e["status"] = "recusada"
            e["motivo_recusa"] = exc.reason
            continue
        item = {"indice": index, "entrada": e, "destino": dest, "relativo": "/".join(final)}
        if changed or renamed:
            item["nome_ajustado"] = True
            e["nome_no_disco"] = "/".join(final)
        plan.append(item)
    return {"plano": plan, "recusadas": rejected, "erro_fatal": None}


def _crc32_of(path: Path) -> str:
    value = 0
    with open_readonly(path) as handle:
        while True:
            data = handle.read(CHUNK)
            if not data:
                break
            value = zlib.crc32(data, value)
    return f"{value & 0xFFFFFFFF:08x}"


def already_extracted(dest: Path, size: Optional[int], crc: Optional[str]) -> bool:
    """Idempotência: destino existente, regular, com mesmo tamanho e CRC32."""
    if size is None or crc is None:
        return False
    try:
        st = os.lstat(fs(dest))
        if not stat.S_ISREG(st.st_mode) or st.st_size != size:
            return False
        return _crc32_of(dest) == crc.lower()
    except OSError:
        # Inexistente, nome longo demais (ENAMETOOLONG), componente que não é
        # pasta, sem permissão...: não é reaproveitável. A extração dessa
        # entrada registra o erro dela sem abortar a análise inteira.
        return False


# ---------------------------------------------------------------- extraction


class _RatioGuard:
    """Razão de compressão acumulada de UM compactado, conferida durante a extração.

    Soma os bytes descompactados de todas as entradas (inclusive as já
    presentes de execuções anteriores e dados descartados) e compara com o
    tamanho do compactado.
    """

    def __init__(self, archive_size: int, limits: Limits, start: int = 0):
        self.size = max(int(archive_size), 1)
        self.limits = limits
        self.total = start
        self._lock = threading.Lock()

    def add(self, amount: int) -> None:
        with self._lock:
            self.total += amount
            total = self.total
        if total >= self.limits.ratio_min_bytes and total / self.size > self.limits.max_ratio:
            raise LimitExceeded(
                f"razão de compressão {total / self.size:.1f} > {self.limits.max_ratio} durante a "
                "descompactação (soma das entradas deste compactado; possível bomba; ajuste --max-ratio se for legítimo)"
            )


class _Sink:
    """Escreve em arquivo temporário e publica atomicamente ao concluir."""

    def __init__(self, dest: Path, expected: Optional[int], budget: Budget, max_entry: int,
                 guard: Optional[_RatioGuard] = None):
        self.dest = dest
        self.tmp = dest.with_name(dest.name + TMP_SUFFIX)
        self.expected = expected
        self.budget = budget
        self.max_entry = max_entry
        self.guard = guard
        self.written = 0
        self.finished = False
        ensure_dir(dest.parent)
        remove_quietly(self.tmp)
        self._fh = open(fs(self.tmp), "wb")

    def write(self, data) -> int:
        length = len(data)
        self.written += length
        if self.expected is not None and self.written > self.expected:
            raise LimitExceeded(f"{self.dest.name}: dados excedem o tamanho declarado ({self.expected} bytes)")
        if self.written > self.max_entry:
            raise LimitExceeded(f"{self.dest.name}: excede --max-entry-bytes ({self.max_entry})")
        if self.guard is not None:
            self.guard.add(length)
        self.budget.consume(length)
        self._fh.write(data)
        return length

    def finish(self) -> None:
        if self.finished:
            return
        self._fh.flush()
        os.fsync(self._fh.fileno())
        self._fh.close()
        if self.expected is not None and self.written != self.expected:
            remove_quietly(self.tmp)
            raise ArchiveError(f"{self.dest.name}: {self.written} bytes escritos, {self.expected} declarados")
        if is_alias(self.dest):
            # Conferido de novo aqui porque o nome curto 8.3 de um arquivo só passa
            # a existir depois que ele é extraído (depois do planejamento).
            remove_quietly(self.tmp)
            raise ArchiveError(
                f"{self.dest.name}: o destino é apelido de outro arquivo (ex.: nome curto 8.3 ou link); não gravado"
            )
        if os.path.lexists(fs(self.dest)):
            remove_quietly(self.dest)
        os.replace(fs(self.tmp), fs(self.dest))
        self.finished = True

    def abort(self) -> None:
        try:
            self._fh.close()
        except Exception:
            pass
        remove_quietly(self.tmp)


def extract_archive(path: Path, listing: dict, plan: List[dict], limits: Limits, budget: Budget) -> dict:
    """Extrai as entradas planejadas.

    Retorna ``{"extraidas": [...], "erros": [...], "descartadas": [...]}``;
    ``descartadas`` lista dados que o extrator entregou para nomes fora do
    plano (somente tamanho e hashes; nada gravado).
    """
    fmt = listing["formato"]
    done: List[dict] = []
    errors: List[str] = []
    discarded: List[dict] = []
    pending: List[dict] = []
    reused = 0
    for item in plan:
        entry = item["entrada"]
        if already_extracted(item["destino"], entry["tamanho"], entry["crc32"]):
            budget.consume(entry["tamanho"] or 0)
            reused += entry["tamanho"] or 0
            entry["status"] = "ja_existente_verificado"
            done.append(item)
        else:
            pending.append(item)
    result = {"extraidas": done, "erros": errors, "descartadas": discarded}
    if not pending:
        return result
    guard = _RatioGuard(os.path.getsize(fs(path)), limits, start=reused)
    if fmt == "zip":
        _extract_zip(path, pending, limits, budget, done, errors, guard)
    elif fmt == "7z":
        _extract_7z(path, pending, limits, budget, done, errors, guard, discarded)
    elif fmt == "tar":
        _extract_tar(path, pending, limits, budget, done, errors, guard)
    elif fmt in SINGLE_STREAM:
        _extract_single(path, fmt, pending, limits, budget, done, errors, guard)
    else:
        errors.append(f"formato {fmt} sem extrator")
    return result


def _copy_stream(source, sink: _Sink) -> None:
    while True:
        data = source.read(CHUNK)
        if not data:
            break
        sink.write(data)


def _extract_zip(path, pending, limits, budget, done, errors, guard) -> None:
    with open_readonly(path) as handle, zipfile.ZipFile(handle) as archive:
        infos = archive.infolist()
        for item in pending:
            entry = item["entrada"]
            info = infos[item["indice"]]
            sink = None
            try:
                sink = _Sink(item["destino"], entry["tamanho"], budget, limits.max_entry_bytes, guard)
                with archive.open(info) as source:
                    _copy_stream(source, sink)
                sink.finish()
                entry["status"] = "extraida"
                done.append(item)
            except LimitExceeded as exc:
                if sink:
                    sink.abort()
                entry["status"] = "erro"
                errors.append(f"{entry['nome']}: {exc}")
                break  # limite global: interrompe o restante deste arquivo
            except Exception as exc:
                if sink:
                    sink.abort()
                entry["status"] = "erro"
                errors.append(f"{entry['nome']}: {type(exc).__name__}: {exc}")


def _extract_tar(path, pending, limits, budget, done, errors, guard) -> None:
    with open_readonly(path) as handle, tarfile.open(fileobj=handle, mode="r:*") as archive:
        members = archive.getmembers()
        for item in pending:
            entry = item["entrada"]
            member = members[item["indice"]]
            sink = None
            try:
                source = archive.extractfile(member)
                if source is None:
                    raise ArchiveError("membro não é arquivo regular")
                sink = _Sink(item["destino"], entry["tamanho"], budget, limits.max_entry_bytes, guard)
                with source:
                    _copy_stream(source, sink)
                sink.finish()
                entry["status"] = "extraida"
                done.append(item)
            except LimitExceeded as exc:
                if sink:
                    sink.abort()
                entry["status"] = "erro"
                errors.append(f"{entry['nome']}: {exc}")
                break
            except Exception as exc:
                if sink:
                    sink.abort()
                entry["status"] = "erro"
                errors.append(f"{entry['nome']}: {type(exc).__name__}: {exc}")


def _extract_single(path, fmt, pending, limits, budget, done, errors, guard) -> None:
    opener = SINGLE_STREAM[fmt][0]
    item = pending[0]
    entry = item["entrada"]
    sink = None
    try:
        # Fluxo único não declara o tamanho: a razão é conferida durante a descompactação (guard).
        sink = _Sink(item["destino"], None, budget, limits.max_entry_bytes, guard)
        with open_readonly(path) as raw, opener(raw, "rb") as source:
            while True:
                data = source.read(CHUNK)
                if not data:
                    break
                sink.write(data)
        sink.finish()
        entry["tamanho"] = sink.written
        entry["status"] = "extraida"
        done.append(item)
    except Exception as exc:
        if sink:
            sink.abort()
        entry["status"] = "erro"
        errors.append(f"{entry['nome']}: {type(exc).__name__}: {exc}")


def _7z_keys(name: str) -> List[str]:
    normalized = name.replace("\\", "/")
    keys = {name, normalized}
    stripped = normalized
    while stripped.startswith("./"):
        stripped = stripped[2:]
    keys.add(stripped)
    keys.add(PurePosixPath(stripped).as_posix())
    keys.add(posixpath.normpath(stripped))
    return [k for k in keys if k]


def _extract_7z(path, pending, limits, budget, done, errors, guard, discarded) -> None:
    import py7zr
    from py7zr.io import Py7zIO, WriterFactory  # type: ignore

    by_key: Dict[str, dict] = {}
    for item in pending:
        for key in _7z_keys(item["entrada"]["nome"]):
            by_key.setdefault(key, item)

    lock = threading.Lock()
    sinks: Dict[int, _Sink] = {}
    unexpected: List[str] = []
    claimed: set = set()
    failed: set = set()

    def _entry_failed(item: dict, exc: BaseException) -> None:
        entry = item["entrada"]
        entry["status"] = "erro"
        with lock:
            failed.add(id(item))
            errors.append(f"{entry['nome']}: {type(exc).__name__}: {exc}")

    class _Writer(Py7zIO):
        def __init__(self, item):
            self.item = item
            self.closed_once = False
            entry = item["entrada"]
            self.sink = _Sink(item["destino"], entry["tamanho"], budget, limits.max_entry_bytes, guard)
            with lock:
                sinks[id(self)] = self.sink

        def write(self, s) -> int:
            return self.sink.write(s)

        def read(self, size=None) -> bytes:
            return b""

        def seek(self, offset, whence=0) -> int:
            return self.sink.written

        def flush(self) -> None:
            pass

        def size(self) -> int:
            return self.sink.written

        def close(self) -> None:
            if self.closed_once:
                return
            self.closed_once = True
            try:
                self.sink.finish()
            except (ArchiveError, OSError) as exc:
                # Falha ao PUBLICAR só esta entrada (ex.: apelido 8.3, tamanho
                # divergente): registra o erro dela sem interromper as demais.
                self.sink.abort()
                _entry_failed(self.item, exc)
                return
            self.item["entrada"]["status"] = "extraida"

    class _Discard(Py7zIO):
        """Destino descartável: só mede tamanho e hashes (nada é gravado)."""

        def __init__(self, filename: str, record: bool = True):
            self.filename = filename
            self.record = record  # False: entrada planejada cujo destino falhou (erro já registrado)
            self.hasher = MultiHasher()
            self.closed_once = False

        def write(self, s) -> int:
            length = len(s)
            if self.hasher.size + length > limits.max_entry_bytes:
                raise LimitExceeded(f"{self.filename}: dados descartados excedem --max-entry-bytes ({limits.max_entry_bytes})")
            guard.add(length)
            self.hasher.update(s)
            return length

        def read(self, size=None) -> bytes:
            return b""

        def seek(self, offset, whence=0) -> int:
            return self.hasher.size

        def flush(self) -> None:
            pass

        def size(self) -> int:
            return self.hasher.size

        def close(self) -> None:
            if self.closed_once:
                return
            self.closed_once = True
            if not self.record:
                return
            info = self.hasher.result()
            with lock:
                discarded.append(
                    {
                        "nome_py7zr": self.filename,
                        "tamanho": info["size"],
                        "crc32": info["crc32"],
                        "sha256": info["sha256"],
                        "observacao": "entrada fora do plano (ex.: nome duplicado); dados descartados sem gravar",
                    }
                )

    class _Factory(WriterFactory):
        def create(self, filename: str):
            item = None
            for key in _7z_keys(filename):
                item = by_key.get(key)
                if item is not None:
                    break
            if item is None or id(item) in claimed:
                # Nome fora do plano (ex.: duplicata renomeada pelo py7zr para
                # "nome_0") ou já atendido: descarta e registra, sem abortar.
                with lock:
                    unexpected.append(filename)
                return _Discard(filename)
            claimed.add(id(item))
            try:
                return _Writer(item)
            except OSError as exc:
                # Destino inutilizável só para ESTA entrada (ex.: arquivo no lugar
                # de uma pasta, caminho longo demais): registra o erro e descarta
                # os dados dela, sem interromper as demais entradas.
                _entry_failed(item, exc)
                return _Discard(filename, record=False)

    targets = [item["entrada"]["nome"] for item in pending]
    try:
        with py7zr.SevenZipFile(fs(path), mode="r") as archive:
            archive.extract(targets=targets, factory=_Factory())
    except Exception as exc:
        errors.append(f"7z: {type(exc).__name__}: {exc}")
    finally:
        for sink in sinks.values():
            if not sink.finished:
                sink.abort()
    for item in pending:
        entry = item["entrada"]
        if id(item) in failed:
            continue  # erro desta entrada já registrado acima
        if entry.get("status") == "extraida":
            done.append(item)
        elif entry.get("tamanho") == 0 and not os.path.exists(fs(item["destino"])):
            # entradas vazias: garante o arquivo de 0 byte
            try:
                sink = _Sink(item["destino"], 0, budget, limits.max_entry_bytes, guard)
                sink.finish()
                entry["status"] = "extraida"
                done.append(item)
            except Exception as exc:
                entry["status"] = "erro"
                errors.append(f"{entry['nome']}: {type(exc).__name__}: {exc}")
        else:
            entry["status"] = "erro"
            errors.append(f"{entry['nome']}: não extraída (ver erro do 7z acima)")
    # Nomes fora do plano não são erro: os dados foram medidos e descartados
    # (ver "descartadas"); o intake registra como aviso.
