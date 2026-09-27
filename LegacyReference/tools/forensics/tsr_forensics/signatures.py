"""Detecção de formato de contêiner pelos *magic bytes* (nunca pela extensão).

Fontes das assinaturas (citadas também em cada regra):

* 7z: especificação 7-Zip (7zFormat.txt) — ``'7z' BC AF 27 1C``.
* ZIP: PKWARE APPNOTE.TXT — ``PK 03 04`` (cabeçalho local), ``PK 05 06``
  (fim de diretório central; ZIP vazio), ``PK 07 08`` (marcador de spanning).
* RAR: RARLAB technote — ``Rar! 1A 07 00`` (RAR 1.5–4.x) e ``Rar! 1A 07 01 00`` (RAR 5).
* gzip: RFC 1952 — ``1F 8B``.  bzip2: ``BZh`` + dígito do tamanho de bloco.
* xz: The .xz File Format — ``FD '7zXZ' 00``.  Zstandard: RFC 8878 — ``28 B5 2F FD``.
* tar: POSIX ustar — ``ustar`` no deslocamento 257.
* psx-spx (https://psx-spx.consoledev.net/, seções "CDROM Disk Format",
  "CDROM ISO Volume Descriptors" e "CDROM Disk Images ..."):
  sync de setor bruto ``00 FF*10 00``; ``CD001`` no descritor de volume
  (setor 16); ECM ``'ECM' 00``; CHD ``MComprHD``; PBP ``00 'PBP'``;
  SBI ``'SBI' 00``; MDS ``MEDIA DESCRIPTOR``; CCD ``[CloneCD]``; CUE (texto
  com comandos FILE/TRACK).
"""

from __future__ import annotations

import re
from typing import Dict, Optional

from .fsutil import PathLike, open_readonly

SYNC = b"\x00" + b"\xff" * 10 + b"\x00"
HEAD_BYTES = 64 * 1024

# Formatos que o kit sabe listar e extrair.
EXTRACTABLE = {"7z", "zip", "tar", "gzip", "bzip2", "xz"}
# Imagens de disco que o kit sabe ler.
DISC_IMAGES = {"iso9660", "cd_raw_2352", "cd_raw_2336"}

_CUE_FILE_RE = re.compile(r"^\s*FILE\s+.+\s+(BINARY|MOTOROLA|AIFF|WAVE|MP3)\s*$", re.I | re.M)
_CUE_TRACK_RE = re.compile(r"^\s*TRACK\s+\d{1,2}\s+\S+\s*$", re.I | re.M)

SOURCE_PSXSPX_FORMAT = "psx-spx: CDROM Disk Format / Sector Encoding"
SOURCE_PSXSPX_ISO = "psx-spx: CDROM ISO Volume Descriptors"
SOURCE_PSXSPX_IMAGES = "psx-spx: CDROM File Formats - Disk Images"


def _result(fmt: Optional[str], evidence: str, source: str, **extra) -> Dict[str, object]:
    data: Dict[str, object] = {"format": fmt, "evidence": evidence, "source": source}
    data.update(extra)
    return data


def detect_from_head(head: bytes, size: int) -> Dict[str, object]:
    """Identifica o contêiner a partir dos primeiros bytes (idealmente 64 KiB)."""
    if head.startswith(b"7z\xbc\xaf\x27\x1c"):
        return _result("7z", "assinatura 37 7A BC AF 27 1C", "7-Zip 7zFormat.txt")
    if head[:4] in (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"):
        return _result("zip", f"assinatura {head[:4].hex(' ')}", "PKWARE APPNOTE.TXT")
    if head.startswith(b"Rar!\x1a\x07\x01\x00"):
        return _result("rar5", "assinatura Rar! 1A 07 01 00", "RARLAB technote (RAR 5.0)")
    if head.startswith(b"Rar!\x1a\x07\x00"):
        return _result("rar4", "assinatura Rar! 1A 07 00", "RARLAB technote (RAR 1.5-4.x)")
    if head.startswith(b"\x1f\x8b"):
        return _result("gzip", "assinatura 1F 8B", "RFC 1952")
    if len(head) >= 4 and head.startswith(b"BZh") and 0x31 <= head[3] <= 0x39:
        return _result("bzip2", "assinatura 'BZh' + dígito", "formato bzip2")
    if head.startswith(b"\xfd7zXZ\x00"):
        return _result("xz", "assinatura FD 37 7A 58 5A 00", "The .xz File Format")
    if head.startswith(b"\x28\xb5\x2f\xfd"):
        return _result("zstd", "assinatura 28 B5 2F FD", "RFC 8878")
    if head.startswith(b"ECM\x00"):
        return _result("ecm", "assinatura 'ECM' 00", SOURCE_PSXSPX_IMAGES + " (ECM)")
    if head.startswith(b"MComprHD"):
        return _result("chd", "assinatura 'MComprHD'", SOURCE_PSXSPX_IMAGES + " (CHD)")
    if head.startswith(b"\x00PBP"):
        return _result("pbp", "assinatura 00 'PBP'", SOURCE_PSXSPX_IMAGES + " (PBP)")
    if head.startswith(b"SBI\x00"):
        return _result("sbi", "assinatura 'SBI' 00", SOURCE_PSXSPX_IMAGES + " (SBI)")
    if head.startswith(b"MEDIA DESCRIPTOR"):
        return _result("mds", "assinatura 'MEDIA DESCRIPTOR'", SOURCE_PSXSPX_IMAGES + " (MDS)")
    if head.startswith(SYNC):
        mode = head[15] if len(head) > 15 else None
        iso_at = 16 * 2352 + (24 if mode == 2 else 16) + 1
        has_iso = head[iso_at:iso_at + 5] == b"CD001"
        return _result(
            "cd_raw_2352",
            f"padrão de sync 00 FF*10 00 no deslocamento 0; byte de modo = {mode}"
            + ("; 'CD001' no setor 16" if has_iso else ""),
            SOURCE_PSXSPX_FORMAT,
            mode=mode,
            iso9660=has_iso,
        )
    if head[0x8001:0x8006] == b"CD001":
        return _result("iso9660", "'CD001' no deslocamento 0x8001 (setor 16 de 2048 bytes)", SOURCE_PSXSPX_ISO)
    iso_2336 = 16 * 2336 + 8 + 1
    if head[iso_2336:iso_2336 + 5] == b"CD001":
        return _result(
            "cd_raw_2336",
            "'CD001' no setor 16 com setores de 2336 bytes (subheader de 8 bytes)",
            SOURCE_PSXSPX_ISO,
        )
    if head[257:262] == b"ustar":
        return _result("tar", "'ustar' no deslocamento 257", "POSIX ustar")
    text = _as_text(head)
    if text is not None:
        if _CUE_FILE_RE.search(text) and _CUE_TRACK_RE.search(text):
            return _result("cue", "texto com comandos FILE e TRACK", SOURCE_PSXSPX_IMAGES + " (CUE/BIN)")
        if text.lstrip().upper().startswith("[CLONECD]"):
            return _result("ccd", "texto iniciando com [CloneCD]", SOURCE_PSXSPX_IMAGES + " (CCD)")
    return _result(None, "nenhuma assinatura de contêiner reconhecida", "")


def _as_text(head: bytes) -> Optional[str]:
    if not head or b"\x00" in head[:4096]:
        return None
    sample = head[:16384]
    for encoding in ("utf-8", "cp1252", "latin-1"):
        try:
            return sample.decode(encoding)
        except UnicodeDecodeError:
            continue
    return None  # pragma: no cover - latin-1 sempre decodifica


def read_head(path: PathLike, count: int = HEAD_BYTES) -> bytes:
    with open_readonly(path) as handle:
        return handle.read(count)


def detect_container(path: PathLike) -> Dict[str, object]:
    with open_readonly(path) as handle:
        head = handle.read(HEAD_BYTES)
        handle.seek(0, 2)
        size = handle.tell()
    result = detect_from_head(head, size)
    result["size"] = size
    return result
