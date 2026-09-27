"""Identificação de formato por arquivo (sniff) — somente por conteúdo.

Regra do projeto: formato sem evidência = ``"desconhecido"``. Nenhum formato é
"chutado" pela extensão. Quando um cabeçalho parece com um formato mas a
estrutura não confere, o arquivo continua ``"desconhecido"`` e o fato é
registrado em ``indicios`` (factual, sem conclusão).

Fontes (psx-spx = https://psx-spx.consoledev.net/ , espelho do texto em
https://github.com/psx-spx/psx-spx.github.io):

* PS-X EXE — psx-spx "CDROM File Playstation EXE and SYSTEM.CNF":
  ``000h-007h ASCII ID "PS-X EXE"``, cabeçalho de 800h bytes,
  ``01Ch Filesize (must be N*800h) (excluding 800h-byte header)``.
* CPE — psx-spx "CDROM File PsyQ .CPE Files": ``File ID (01455043h aka "CPE",01h)``.
* TIM — psx-spx "CDROM File Video Texture Image TIM/PXL/CLT (Sony)":
  ``000h File ID (always 10h)``, ``001h Version (always 00h)``,
  ``002h Reserved (always 0000h)``, ``004h Flags (bit0-2=Type, bit3=HasCLUT,
  bit4-31=Reserved/zero)``; tipos 0..4 (e 5, citado como variante); seções
  ``Size (Xsiz*2*Ysiz+0Ch)``, ``Destination Coord``, ``Width+Height``.
* VAG — psx-spx "CDROM File Audio Single Samples VAG (Sony)":
  ``File ID (usually "VAGp")``; campos big-endian.
* VAB/VH — psx-spx "CDROM File Audio Sample Sets VAB and VH/VB (Sony)":
  ``File ID ("pBAV")`` (o mesmo cabeçalho existe em .VAB e .VH; .VB não tem
  cabeçalho e portanto não é detectável).
* SEQ/SEP — psx-spx "CDROM File Audio Sequences SEQ/SEP (Sony)": ambos usam
  ``File ID "pQES"`` ("same ID as in .SEQ files (!)"); SEQ tem versão 1 em
  32 bits, SEP tem versão 0 em 16 bits.
* STR — psx-spx "CDROM File Video Streaming STR (Sony)": setores com
  ``000h StStatus (0160h)`` e ``002h StType (... 8001h=MDEC)``.
* XA-ADPCM — identificado apenas pelo subheader dos setores do disco (submode
  Audio + Form2; psx-spx "CDROM XA Subheader"), não pelo arquivo extraído.
* RIFF/CDXA — psx-spx "RIFF Headers (on PCs)".
* Genéricos: PNG (RFC 2083), JPEG (JFIF/ITU T.81 SOI ``FF D8 FF``), GIF
  (GIF87a/GIF89a), BMP (``BM`` + tamanho declarado igual ao real), RIFF,
  PE (``MZ`` + ``PE\\0\\0`` em e_lfanew), texto ASCII/UTF-8, contêineres
  (ver ``signatures.py``).
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from . import signatures
from .fsutil import PathLike, open_readonly

PSXSPX = "psx-spx"

CATEGORY_BY_FORMAT = {
    "PS-X EXE": "executavel",
    "CPE (PsyQ)": "executavel",
    "PE (Windows)": "executavel",
    "TIM": "textura_imagem",
    "PNG": "textura_imagem",
    "JPEG": "textura_imagem",
    "GIF": "textura_imagem",
    "BMP": "textura_imagem",
    "VAG": "audio",
    "VAB/VH (pBAV)": "audio",
    "RIFF/WAVE": "audio",
    "RIFF/CDXA": "audio_video_xa",
    "XA-ADPCM (setores Mode2 Form2/Audio)": "audio",
    "SEQ/SEP (pQES)": "sequencia_musical",
    "STR (setores 0160h)": "video",
    "STR/XA intercalado (setores)": "video",
    "RIFF/AVI": "video",
    "texto ASCII": "texto",
    "texto UTF-8": "texto",
    "vazio": "vazio",
    "desconhecido": "desconhecido",
}

CONTAINER_NAMES = {
    "7z": ("7z", "compactado"),
    "zip": ("ZIP", "compactado"),
    "rar4": ("RAR 4", "compactado"),
    "rar5": ("RAR 5", "compactado"),
    "gzip": ("gzip", "compactado"),
    "bzip2": ("bzip2", "compactado"),
    "xz": ("xz", "compactado"),
    "zstd": ("Zstandard", "compactado"),
    "tar": ("tar", "compactado"),
    "ecm": ("ECM", "imagem_de_disco"),
    "chd": ("CHD", "imagem_de_disco"),
    "pbp": ("PBP", "imagem_de_disco"),
    "mds": ("MDS (Alcohol 120%)", "imagem_de_disco"),
    "ccd": ("CCD (CloneCD)", "imagem_de_disco"),
    "cue": ("CUE sheet", "imagem_de_disco"),
    "iso9660": ("ISO9660 (setores de 2048)", "imagem_de_disco"),
    "cd_raw_2352": ("CD bruto 2352", "imagem_de_disco"),
    "cd_raw_2336": ("CD bruto 2336", "imagem_de_disco"),
    "sbi": ("SBI (subcanal)", "subcanal_protecao"),
}


@dataclass
class SniffResult:
    format: str
    category: str
    source: str = ""
    details: Dict[str, object] = field(default_factory=dict)
    hints: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "formato": self.format,
            "categoria": self.category,
            "fonte_assinatura": self.source,
            "detalhes_formato": self.details,
            "indicios": self.hints,
        }


def _make(fmt: str, source: str = "", details=None, hints=None, category: Optional[str] = None) -> SniffResult:
    return SniffResult(
        format=fmt,
        category=category or CATEGORY_BY_FORMAT.get(fmt, "desconhecido"),
        source=source,
        details=details or {},
        hints=hints or [],
    )


def _u16le(data: bytes, off: int) -> int:
    return struct.unpack_from("<H", data, off)[0]


def _u32le(data: bytes, off: int) -> int:
    return struct.unpack_from("<I", data, off)[0]


def _u32be(data: bytes, off: int) -> int:
    return struct.unpack_from(">I", data, off)[0]


def _printable(raw: bytes) -> str:
    raw = raw.split(b"\x00", 1)[0]
    return "".join(chr(b) if 0x20 <= b < 0x7F else "?" for b in raw)


# ---------------------------------------------------------------- PS1 formats

TIM_TYPES = {0: "4bpp", 1: "8bpp", 2: "16bpp", 3: "24bpp", 4: "misto", 5: "tipo 5 (variante citada em psx-spx)"}


def tim_header_matches(head: bytes) -> bool:
    """Checa apenas os 8 primeiros bytes (ID, versão, reservado, flags)."""
    if len(head) < 8 or head[:4] != b"\x10\x00\x00\x00":
        return False
    flags = _u32le(head, 4)
    return (flags >> 4) == 0 and (flags & 7) in TIM_TYPES


def validate_tim(size: int, read_at: Callable[[int, int], bytes]) -> Dict[str, object]:
    """Valida a estrutura de seções de um TIM. Retorna detalhes + ``valido``."""
    head = read_at(0, 8)
    flags = _u32le(head, 4)
    has_clut = bool(flags & 8)
    details: Dict[str, object] = {
        "tipo": TIM_TYPES.get(flags & 7),
        "tem_clut": has_clut,
    }
    position = 8
    problems: List[str] = []

    def section(label: str) -> None:
        nonlocal position
        raw = read_at(position, 12)
        if len(raw) < 12:
            problems.append(f"seção {label} truncada")
            return
        length = _u32le(raw, 0)
        x, y, w, h = struct.unpack_from("<HHHH", raw, 4)
        expected = w * 2 * h + 12
        acceptable = {expected, (expected + 3) & ~3}
        details[label] = {"x": x, "y": y, "largura_halfwords": w, "altura": h, "tamanho_secao": length}
        if length < 12:
            problems.append(f"seção {label}: tamanho < 12")
        elif length not in acceptable:
            problems.append(f"seção {label}: tamanho {length} != {expected} (largura*2*altura+12)")
        if position + length > size:
            problems.append(f"seção {label} ultrapassa o fim do arquivo")
        position += max(length, 12)

    if has_clut:
        section("clut")
    if not problems:
        section("imagem")
    details["bytes_excedentes"] = max(size - position, 0) if not problems else None
    details["valido"] = not problems
    details["problemas"] = problems
    return details


def _sniff_psx_exe(head: bytes, size: int) -> SniffResult:
    details: Dict[str, object] = {}
    if len(head) >= 0x38:
        t_size = _u32le(head, 0x1C)
        details = {
            "pc_inicial": f"0x{_u32le(head, 0x10):08x}",
            "gp_inicial": f"0x{_u32le(head, 0x14):08x}",
            "endereco_destino": f"0x{_u32le(head, 0x18):08x}",
            "tamanho_declarado": t_size,
            "tamanho_multiplo_800h": t_size % 0x800 == 0,
            "tamanho_confere": size == 0x800 + t_size,
            "sp_base": f"0x{_u32le(head, 0x30):08x}",
        }
    if len(head) >= 0x4C + 1:
        marker = _printable(head[0x4C:0x4C + 60])
        if marker:
            details["marcador_ascii"] = marker
    return _make("PS-X EXE", PSXSPX + ": CDROM File Playstation EXE (ID 'PS-X EXE')", details)


def _sniff_vag(head: bytes) -> SniffResult:
    details: Dict[str, object] = {"id": head[:4].decode("ascii")}
    if len(head) >= 0x30:
        details.update(
            {
                "versao_be": f"0x{_u32be(head, 4):08x}",
                "tamanho_canal_be": _u32be(head, 0x0C),
                "taxa_amostragem_hz_be": _u32be(head, 0x10),
                "nome": _printable(head[0x20:0x30]),
            }
        )
    return _make("VAG", PSXSPX + ": CDROM File Audio Single Samples VAG (ID 'VAGp')", details)


def _sniff_vab(head: bytes, size: int) -> SniffResult:
    details: Dict[str, object] = {}
    if len(head) >= 0x20:
        declared = _u32le(head, 0x0C)
        details = {
            "versao_u32_le": _u32le(head, 4),
            "tamanho_total_declarado_u32_le": declared,
            "tamanho_real": size,
            "observacao": (
                "tamanho real igual ao declarado (compatível com .VAB completo)"
                if declared == size
                else "tamanho real difere do declarado (psx-spx: em .VH o campo soma .VH+.VB)"
            ),
        }
    return _make("VAB/VH (pBAV)", PSXSPX + ": CDROM File Audio Sample Sets VAB and VH/VB (ID 'pBAV')", details)


def _sniff_pqes(head: bytes) -> SniffResult:
    details: Dict[str, object] = {"bytes_04_07_hex": head[4:8].hex(" ")}
    if head[4:8] == b"\x00\x00\x00\x01":
        details["leitura"] = "campo de versão 32 bits = 1 (psx-spx descreve SEQ com versão 1)"
    elif head[4:6] == b"\x00\x00":
        details["leitura"] = "campo de versão 16 bits = 0 (psx-spx descreve SEP com versão 0)"
    else:
        details["leitura"] = "campo de versão não corresponde aos valores descritos em psx-spx"
    return _make(
        "SEQ/SEP (pQES)",
        PSXSPX + ": CDROM File Audio Sequences SEQ/SEP (ID 'pQES', compartilhado por SEQ e SEP)",
        details,
    )


def _sniff_str(size: int, read_at: Callable[[int, int], bytes]) -> Optional[SniffResult]:
    """STR: exige >= 2 blocos de 2048 bytes (dentre os 16 primeiros) com cabeçalho 0160h coerente."""
    chunks = min(size // 2048, 16)
    if chunks < 2:
        return None
    matches = 0
    types = set()
    for index in range(chunks):
        raw = read_at(index * 2048, 8)
        if len(raw) < 8:
            break
        if _u16le(raw, 0) != 0x0160:
            continue
        sector_offset, sector_count = _u16le(raw, 4), _u16le(raw, 6)
        if sector_count == 0 or sector_offset >= sector_count:
            continue
        matches += 1
        types.add(f"0x{_u16le(raw, 2):04x}")
    if matches < 2:
        return None
    return _make(
        "STR (setores 0160h)",
        PSXSPX + ": CDROM File Video Streaming STR (StStatus 0160h)",
        {"blocos_analisados": chunks, "blocos_com_cabecalho_str": matches, "sttype_encontrados": sorted(types)},
    )


# ---------------------------------------------------------------- generic


def _sniff_riff(head: bytes, size: int) -> Optional[SniffResult]:
    if len(head) < 12 or head[:4] != b"RIFF":
        return None
    form = head[8:12]
    declared = _u32le(head, 4) + 8
    details = {"tipo_riff": _printable(form), "tamanho_declarado": declared, "tamanho_confere": declared == size}
    if form == b"WAVE":
        return _make("RIFF/WAVE", "RIFF (Microsoft) forma 'WAVE'", details)
    if form == b"AVI ":
        return _make("RIFF/AVI", "RIFF (Microsoft) forma 'AVI '", details)
    if form == b"CDXA":
        return _make("RIFF/CDXA", PSXSPX + ": RIFF Headers (on PCs) ('CDXA')", details)
    return _make(f"RIFF/{_printable(form)}", "RIFF (Microsoft)", details, category="desconhecido")


def _sniff_bmp(head: bytes, size: int) -> Optional[SniffResult]:
    if len(head) < 26 or head[:2] != b"BM":
        return None
    declared = _u32le(head, 2)
    if declared != size:
        return None
    return _make("BMP", "BMP ('BM' + tamanho declarado == tamanho real)", {"tamanho_declarado": declared})


def _sniff_pe(head: bytes, size: int, read_at: Callable[[int, int], bytes]) -> Optional[SniffResult]:
    if len(head) < 0x40 or head[:2] != b"MZ":
        return None
    lfanew = _u32le(head, 0x3C)
    if lfanew + 4 > size:
        return None
    if read_at(lfanew, 4) != b"PE\x00\x00":
        return None
    return _make("PE (Windows)", "Microsoft PE/COFF ('MZ' + 'PE\\0\\0' em e_lfanew)", {"e_lfanew": lfanew})


def _text_kind(sample: bytes) -> Optional[str]:
    if not sample or b"\x00" in sample:
        return None
    allowed_controls = {0x09, 0x0A, 0x0C, 0x0D, 0x1A}
    if all((0x20 <= b < 0x7F) or b in allowed_controls for b in sample):
        return "texto ASCII"
    try:
        text = sample.decode("utf-8")
    except UnicodeDecodeError:
        # pode ter cortado um caractere multibyte no fim da amostra
        try:
            text = sample[:-4].decode("utf-8")
        except UnicodeDecodeError:
            return None
    if any((ord(ch) < 0x20 and ord(ch) not in allowed_controls) or ord(ch) == 0x7F for ch in text):
        return None
    return "texto UTF-8"


# ---------------------------------------------------------------- entry points

TEXT_SAMPLE = 1 << 20


def sniff(head: bytes, size: int, read_at: Callable[[int, int], bytes]) -> SniffResult:
    """Identifica o formato a partir do cabeçalho e de leituras pontuais."""
    if size == 0:
        return _make("vazio", "tamanho zero")
    if head[:8] == b"PS-X EXE":
        return _sniff_psx_exe(head, size)
    if head[:4] == b"CPE\x01":
        return _make("CPE (PsyQ)", PSXSPX + ": CDROM File PsyQ .CPE Files (ID 'CPE',01h)")
    if tim_header_matches(head):
        details = validate_tim(size, read_at)
        if details["valido"]:
            return _make("TIM", PSXSPX + ": CDROM File Video Texture Image TIM (ID 10h)", details)
        unknown = _make("desconhecido")
        unknown.hints.append(
            "8 primeiros bytes compatíveis com cabeçalho TIM (psx-spx), mas as seções não conferem: "
            + "; ".join(details["problemas"])
        )
        return unknown
    if head[:4] == b"VAGp":
        return _sniff_vag(head)
    if head[:4] == b"pBAV":
        return _sniff_vab(head, size)
    if head[:4] == b"pQES":
        return _sniff_pqes(head)
    container = signatures.detect_from_head(head, size)
    fmt = container.get("format")
    if fmt in CONTAINER_NAMES:
        name, category = CONTAINER_NAMES[fmt]
        extra = {k: v for k, v in container.items() if k not in ("format", "evidence", "source")}
        extra["evidencia"] = container.get("evidence")
        return _make(name, str(container.get("source", "")), extra, category=category)
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return _make("PNG", "PNG (RFC 2083): 89 50 4E 47 0D 0A 1A 0A")
    if head.startswith(b"\xff\xd8\xff"):
        return _make("JPEG", "JPEG (ITU T.81): SOI FF D8 FF")
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return _make("GIF", "GIF87a/GIF89a")
    riff = _sniff_riff(head, size)
    if riff is not None:
        return riff
    bmp = _sniff_bmp(head, size)
    if bmp is not None:
        return bmp
    pe = _sniff_pe(head, size, read_at)
    if pe is not None:
        return pe
    str_result = _sniff_str(size, read_at)
    if str_result is not None:
        return str_result
    kind = _text_kind(head)
    sample = head
    if kind is not None and size > len(head):
        sample = read_at(0, min(size, TEXT_SAMPLE))
        kind = _text_kind(sample)
    if kind is not None:
        details = {}
        if size > len(sample):
            details["observacao"] = f"classificação baseada nos primeiros {len(sample)} bytes"
        return _make(kind, "heurística de texto (bytes imprimíveis, sem NUL)", details)
    result = _make("desconhecido")
    if head[:2] == b"MZ":
        result.hints.append("começa com 'MZ' (cabeçalho DOS), sem cabeçalho PE válido")
    return result


def sniff_file(path: PathLike) -> SniffResult:
    with open_readonly(path) as handle:
        handle.seek(0, 2)
        size = handle.tell()
        handle.seek(0)
        head = handle.read(signatures.HEAD_BYTES)

        def read_at(offset: int, count: int) -> bytes:
            if offset < 0 or offset >= size:
                return b""
            if offset + count <= len(head):
                return head[offset:offset + count]
            handle.seek(offset)
            return handle.read(count)

        return sniff(head, size, read_at)


def sniff_bytes(data: bytes) -> SniffResult:
    def read_at(offset: int, count: int) -> bytes:
        return data[offset:offset + count]

    return sniff(data[: signatures.HEAD_BYTES], len(data), read_at)


def category_for(fmt: str) -> str:
    return CATEGORY_BY_FORMAT.get(fmt, "desconhecido")
