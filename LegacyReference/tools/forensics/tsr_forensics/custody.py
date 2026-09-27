"""Log de cadeia de custódia (JSON Lines, somente acréscimo, encadeado por hash).

Cada linha é um objeto JSON com:

* ``timestamp_utc`` — instante UTC (ISO 8601, sufixo Z);
* ``session_id`` — identificador da execução;
* ``environment`` — versão do kit, do Python, do py7zr, do pycdlib e do SO;
* ``command`` — comando executado (com caminhos redigidos);
* ``step`` / ``result`` / ``details`` — etapa, resultado (ok/aviso/erro) e dados;
* ``prev_sha256`` — SHA-256 da linha anterior (bytes UTF-8, sem o fim de linha).

O encadeamento torna detectável qualquer edição ou remoção de linhas antigas
(``verify`` checa a cadeia). O arquivo só é aberto em modo de acréscimo.

Referência de hashes do original (``original_history``): o PRIMEIRO registro
``original.hash`` (resultado ``ok``) de um nome de arquivo é a referência; ela
só muda com um registro explícito ``original.rebaseline`` (opção
``--rebaseline`` do ``intake``). Registros ``ok`` posteriores com hashes
diferentes, sem rebaseline, são sinalizados como divergentes.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import platform
import uuid
from pathlib import Path
from typing import Callable, Dict, List, Optional

from . import KIT_NAME, __version__
from .fsutil import ensure_dir, fs
from .hashing import hashes_equal

GENESIS = "0" * 64


def utc_now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _dist_version(name: str) -> Optional[str]:
    try:
        from importlib import metadata
    except ImportError:  # pragma: no cover
        return None
    try:
        return metadata.version(name)
    except Exception:
        return None


def environment_info() -> Dict[str, Optional[str]]:
    return {
        "kit": KIT_NAME,
        "kit_version": __version__,
        "python": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "py7zr": _dist_version("py7zr"),
        "pycdlib": _dist_version("pycdlib"),
        "os": f"{platform.system()} {platform.release()}".strip(),
    }


def _line_hash(line: bytes) -> str:
    return hashlib.sha256(line.rstrip(b"\r\n")).hexdigest()


def _last_line(path: Path) -> Optional[bytes]:
    """Lê a última linha não vazia do arquivo, sem carregar o arquivo inteiro."""
    try:
        handle = open(fs(path), "rb")
    except FileNotFoundError:
        return None
    with handle:
        handle.seek(0, 2)
        end = handle.tell()
        if end == 0:
            return None
        block = 64 * 1024
        buffer = b""
        position = end
        while position > 0:
            step = min(block, position)
            position -= step
            handle.seek(position)
            buffer = handle.read(step) + buffer
            stripped = buffer.rstrip(b"\r\n")
            if b"\n" in stripped:
                return stripped.rsplit(b"\n", 1)[1]
        stripped = buffer.rstrip(b"\r\n")
        return stripped if stripped else None


class CustodyLog:
    """Log de custódia. ``scrub`` (opcional) limpa caminhos locais de todas as
    strings dos detalhes antes de gravar (o log vai para o repositório público)."""

    def __init__(self, path: Path, command: List[str], session_id: Optional[str] = None,
                 scrub: Optional[Callable[[object], object]] = None):
        self.path = Path(path)
        self.command = list(command)
        self.session_id = session_id or uuid.uuid4().hex
        self.environment = environment_info()
        self.scrub = scrub
        ensure_dir(self.path.parent)

    def record(self, step: str, result: str, **details) -> dict:
        if result not in ("ok", "aviso", "erro"):
            raise ValueError(f"resultado inválido: {result}")
        if self.scrub is not None:
            details = self.scrub(details)  # type: ignore[assignment]
        last = _last_line(self.path)
        prev = GENESIS if last is None else _line_hash(last)
        entry = {
            "timestamp_utc": utc_now_iso(),
            "session_id": self.session_id,
            "environment": self.environment,
            "command": self.command,
            "step": step,
            "result": result,
            "details": details,
            "prev_sha256": prev,
        }
        line = json.dumps(entry, ensure_ascii=False, sort_keys=True, default=str)
        with open(fs(self.path), "a", encoding="utf-8", newline="\n") as handle:
            handle.write(line + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return entry


def read_records(path: Path) -> List[dict]:
    records: List[dict] = []
    try:
        with open(fs(path), "rb") as handle:
            for raw in handle:
                raw = raw.rstrip(b"\r\n")
                if not raw:
                    continue
                try:
                    records.append(json.loads(raw.decode("utf-8")))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    records.append({"_invalid_line": True})
    except FileNotFoundError:
        pass
    return records


def verify_chain(path: Path) -> dict:
    """Confere o encadeamento de hashes do log.

    Retorna ``{"ok": bool, "registros": int, "quebra_na_linha": int|None, "detalhe": str}``.
    """
    try:
        handle = open(fs(path), "rb")
    except FileNotFoundError:
        return {"ok": False, "registros": 0, "quebra_na_linha": None, "detalhe": "log inexistente"}
    prev = GENESIS
    count = 0
    with handle:
        for number, raw in enumerate(handle, start=1):
            line = raw.rstrip(b"\r\n")
            if not line:
                continue
            try:
                entry = json.loads(line.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return {
                    "ok": False,
                    "registros": count,
                    "quebra_na_linha": number,
                    "detalhe": "linha não é JSON válido",
                }
            if entry.get("prev_sha256") != prev:
                return {
                    "ok": False,
                    "registros": count,
                    "quebra_na_linha": number,
                    "detalhe": "prev_sha256 não confere com a linha anterior (log alterado)",
                }
            prev = _line_hash(line)
            count += 1
    return {"ok": True, "registros": count, "quebra_na_linha": None, "detalhe": "cadeia íntegra"}


def _same_hashes(a: dict, b: dict) -> bool:
    return hashes_equal(a, b) and str(a.get("sha256", "")).lower() == str(b.get("sha256", "")).lower()


def original_history(path: Path, name: str) -> dict:
    """Referência de hashes registrada para o original ``name`` no log.

    Retorna ``{"referencia": {...}|None, "divergentes": [...], "rebaselines": int}``;
    ``referencia`` = ``{"timestamp_utc", "hashes", "fonte"}``.
    """
    reference: Optional[dict] = None
    divergent: List[dict] = []
    rebaselines = 0
    for record in read_records(path):
        details = record.get("details") or {}
        if details.get("arquivo") != name:
            continue
        step = record.get("step")
        if step == "original.rebaseline" and details.get("hashes_novos"):
            rebaselines += 1
            reference = {
                "timestamp_utc": record.get("timestamp_utc"),
                "hashes": details["hashes_novos"],
                "fonte": "custody_log.jsonl (original.rebaseline)",
            }
            divergent = []
            continue
        if step != "original.hash" or record.get("result") != "ok" or not details.get("hashes"):
            continue
        hashes = details["hashes"]
        if reference is None:
            reference = {"timestamp_utc": record.get("timestamp_utc"), "hashes": hashes, "fonte": "custody_log.jsonl"}
        elif not _same_hashes(hashes, reference["hashes"]):
            divergent.append({"timestamp_utc": record.get("timestamp_utc"), "sha256": hashes.get("sha256"), "size": hashes.get("size")})
    return {"referencia": reference, "divergentes": divergent, "rebaselines": rebaselines}
