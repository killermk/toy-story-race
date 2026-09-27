"""Leitura de setores brutos de imagens de CD (somente leitura).

Referências (psx-spx, "CDROM Sector Encoding" e "CDROM XA Subheader"):

* Sync: ``00h,FFh×10,00h`` (12 bytes) + header ``Minute,Second,Sector,Mode``
  em BCD; endereço absoluto = LBA + 150 (00:02:00).
* Mode1: dados em 010h (800h bytes).
* Mode2/Form1: subheader em 010h (4 bytes) + cópia em 014h; dados em 018h (800h).
* Mode2/Form2: submode com bit 5 (20h) ligado; dados em 018h (914h bytes).
* Submode: bit0 EOR, bit1 Video, bit2 Audio, bit3 Data, bit4 Trigger,
  bit5 Form2, bit6 Real Time, bit7 EOF.
* Imagens 2336: começam no subheader (dados em 008h).

Setores STR (psx-spx "CDROM File Video Streaming STR (Sony)"): cabeçalho no
início dos dados do usuário com ``STR ID`` = 0160h e ``STR Type``; 8001h é o
valor mais comum (MDEC padrão), mas o psx-spx lista outros valores em uso
(ex.: 0004h = vídeo MDEC em setores MODE2/FORM2 no Final Fantasy 9; 0000h,
0001h, 0008h etc. com usos variados). O kit conta os setores com 0160h/8001h
separadamente dos setores com 0160h e outro StType, em Form1 E Form2. Um
casamento de só 2 bytes (0160h) é evidência fraca: os demais StType ficam
como indício, com natureza NÃO CONFIRMADA.

O fluxo lógico de 2048 bytes/setor (``DataTrackStream``) é o que um leitor
ISO9660 enxerga. ATENÇÃO: para setores Mode2/Form2 (XA-ADPCM, STR
intercalado) esse fluxo contém apenas os primeiros 2048 dos 2324 bytes de
cada setor — o conteúdo Form2 NÃO é preservado por essa visão.
"""

from __future__ import annotations

import io
import os
from typing import Dict, List, Optional

from .cue import FRAMES_PER_SECOND, TrackLayout, frames_to_msf
from .fsutil import PathLike, open_readonly
from .hashing import MultiHasher
from .signatures import SYNC

# Bits do mapa de setores (um byte por setor da faixa de dados)
F_FORM2 = 0x01
F_AUDIO = 0x02
F_VIDEO = 0x04
F_DATA = 0x08
F_STR = 0x10
F_NOSYNC = 0x20
F_STR_OTHER = 0x40  # STR ID 0160h com StType diferente de 8001h
F_MODE2 = 0x80

STR_ID = b"\x60\x01"  # STR ID 0160h (little-endian)
STR_MDEC_MAGIC = b"\x60\x01\x01\x80"  # STR ID 0160h + StType 8001h (little-endian)
_MAX_STTYPE_KEYS = 16
_SECTORS_PER_READ = 512
_ZERO_2352 = bytes(2352)


def _bcd(value: int) -> Optional[int]:
    high, low = value >> 4, value & 0x0F
    if high > 9 or low > 9:
        return None
    return high * 10 + low


def header_lba(header: bytes) -> Optional[int]:
    minute, second, frame = (_bcd(b) for b in header[:3])
    if minute is None or second is None or frame is None or second >= 60 or frame >= FRAMES_PER_SECOND:
        return None
    return (minute * 60 + second) * FRAMES_PER_SECOND + frame - 150


def scan_track(path: PathLike, layout: TrackLayout, keep_map: bool = False) -> dict:
    """Lê a faixa inteira: hashes, estatísticas por setor e (opcional) mapa de setores."""
    result: Dict[str, object] = {"hashes": None, "estatisticas": None}
    if layout.begin_byte is None or layout.sectors is None or layout.sector_size is None:
        result["erro"] = "faixa sem posição/tamanho calculado"
        return result
    size = layout.sector_size
    total = layout.sectors
    hasher = MultiHasher()
    sector_map = bytearray(total) if keep_map else None
    stats: Dict[str, object] = {}
    is_raw_data = layout.kind in ("data", "cdi") and size == 2352
    is_2336 = layout.kind in ("data", "cdi") and size == 2336
    counters = {
        "setores_lidos": 0,
        "setores_com_sync": 0,
        "setores_sem_sync": 0,
        "modo_0": 0,
        "modo_1": 0,
        "modo_2": 0,
        "modo_outro": 0,
        "form1": 0,
        "form2": 0,
        "submode_audio": 0,
        "submode_video": 0,
        "submode_data": 0,
        "submode_eof": 0,
        "submode_eor": 0,
        "submode_tempo_real": 0,
        "submode_trigger": 0,
        "xa_audio_form2": 0,
        "str_mdec_0160_8001": 0,
        "str_0160_outro_sttype": 0,
        "str_0160_em_form2": 0,
        "subheader_copia_divergente": 0,
        "msf_cabecalho_divergente": 0,
        "msf_cabecalho_invalido": 0,
        "setores_zerados": 0,
    }
    first_msf_mismatch = None
    first_nosync = None
    sttypes: Dict[str, int] = {}
    base_lba = layout.abs_lba_begin  # None = LBA absoluto desconhecido (MSF não conferido)

    def str_flags(user: bytes, form2: bool) -> int:
        if user[:2] != STR_ID:
            return 0
        if form2:
            counters["str_0160_em_form2"] += 1
        if user[2:4] == STR_MDEC_MAGIC[2:4]:
            counters["str_mdec_0160_8001"] += 1
            return F_STR
        counters["str_0160_outro_sttype"] += 1
        key = f"{user[3]:02x}{user[2]:02x}"
        if key in sttypes or len(sttypes) < _MAX_STTYPE_KEYS:
            sttypes[key] = sttypes.get(key, 0) + 1
        return F_STR_OTHER

    with open_readonly(path) as handle:
        handle.seek(layout.begin_byte)
        index = 0
        while index < total:
            count = min(_SECTORS_PER_READ, total - index)
            block = handle.read(count * size)
            if not block:
                break
            hasher.update(block)
            got = len(block) // size
            view = memoryview(block)
            for k in range(got):
                sector = view[k * size:(k + 1) * size]
                number = index + k
                if size == 2352 and sector == _ZERO_2352:
                    counters["setores_zerados"] += 1
                if is_raw_data:
                    flags = 0
                    if sector[:12] != SYNC:
                        counters["setores_sem_sync"] += 1
                        flags |= F_NOSYNC
                        if first_nosync is None:
                            first_nosync = number
                        if sector_map is not None:
                            sector_map[number] = flags
                        continue
                    counters["setores_com_sync"] += 1
                    lba = header_lba(bytes(sector[12:15]))
                    if lba is None:
                        counters["msf_cabecalho_invalido"] += 1
                    elif base_lba is not None and lba != base_lba + number:
                        counters["msf_cabecalho_divergente"] += 1
                        if first_msf_mismatch is None:
                            first_msf_mismatch = {"setor": number, "lba_esperado": base_lba + number, "lba_no_cabecalho": lba}
                    mode = sector[15]
                    if mode == 2:
                        counters["modo_2"] += 1
                        flags |= F_MODE2
                        sub = sector[16:20]
                        if sub != sector[20:24]:
                            counters["subheader_copia_divergente"] += 1
                        flags |= _count_submode(counters, sub[2])
                        flags |= str_flags(bytes(sector[24:28]), bool(flags & F_FORM2))
                    elif mode == 1:
                        counters["modo_1"] += 1
                        flags |= str_flags(bytes(sector[16:20]), False)
                    elif mode == 0:
                        counters["modo_0"] += 1
                    else:
                        counters["modo_outro"] += 1
                    if sector_map is not None:
                        sector_map[number] = flags
                elif is_2336:
                    counters["modo_2"] += 1
                    sub = sector[0:4]
                    if sub != sector[4:8]:
                        counters["subheader_copia_divergente"] += 1
                    flags = F_MODE2 | _count_submode(counters, sub[2])
                    flags |= str_flags(bytes(sector[8:12]), bool(flags & F_FORM2))
                    if sector_map is not None:
                        sector_map[number] = flags
                elif layout.kind == "audio":
                    if sector[:12] == SYNC:
                        counters["setores_com_sync"] += 1
                elif size == 2048:
                    flags = str_flags(bytes(sector[:4]), False)
                    if flags and sector_map is not None:
                        sector_map[number] = flags
            counters["setores_lidos"] += got
            index += got
            if got < count:
                break
    for key in list(counters):
        if counters[key] == 0 and key not in ("setores_lidos",):
            del counters[key]
    stats.update(counters)
    if first_msf_mismatch is not None:
        stats["primeira_divergencia_msf"] = first_msf_mismatch
    if first_nosync is not None:
        stats["primeiro_setor_sem_sync"] = first_nosync
    if sttypes:
        stats["str_0160_sttype_valores"] = dict(sorted(sttypes.items()))
        stats["str_0160_observacao"] = (
            "setores com STR ID 0160h e StType diferente de 8001h: o psx-spx lista usos variados "
            "(vídeo MDEC, áudio SPU-ADPCM, legendas, dados); casamento de 2 bytes = indício fraco; natureza NÃO CONFIRMADA"
        )
    if is_raw_data and base_lba is None:
        stats["msf_nao_conferido"] = "LBA absoluto da faixa desconhecido (CUE incompleto): cabeçalhos MSF não conferidos"
    if counters.get("setores_lidos", 0) < total:
        stats["aviso"] = f"arquivo terminou antes do esperado: {counters.get('setores_lidos', 0)} de {total} setores"
    if layout.kind == "audio" and counters.get("setores_com_sync"):
        stats["aviso_audio"] = "faixa declarada AUDIO contém setores com padrão de sync de dados"
    result["hashes"] = hasher.result()
    result["estatisticas"] = stats
    result["mapa_setores"] = sector_map
    return result


def _count_submode(counters: Dict[str, int], submode: int) -> int:
    flags = 0
    if submode & 0x20:
        counters["form2"] += 1
        flags |= F_FORM2
    else:
        counters["form1"] += 1
    if submode & 0x04:
        counters["submode_audio"] += 1
        flags |= F_AUDIO
        if submode & 0x20:
            counters["xa_audio_form2"] += 1
    if submode & 0x02:
        counters["submode_video"] += 1
        flags |= F_VIDEO
    if submode & 0x08:
        counters["submode_data"] += 1
        flags |= F_DATA
    if submode & 0x80:
        counters["submode_eof"] += 1
    if submode & 0x01:
        counters["submode_eor"] += 1
    if submode & 0x40:
        counters["submode_tempo_real"] += 1
    if submode & 0x10:
        counters["submode_trigger"] += 1
    return flags


def summarize_sector_range(sector_map: Optional[bytearray], start: int, count: int) -> Optional[dict]:
    """Contagens do mapa de setores num intervalo (ex.: extensão de um arquivo)."""
    if sector_map is None or count <= 0 or start < 0 or start >= len(sector_map):
        return None
    chunk = sector_map[start:start + count]
    result = {
        "setores": len(chunk),
        "form2": 0,
        "xa_audio_form2": 0,
        "video": 0,
        "str_mdec": 0,
        "str_outro_sttype": 0,
        "sem_sync": 0,
    }
    for flags in chunk:
        if flags & F_FORM2:
            result["form2"] += 1
            if flags & F_AUDIO:
                result["xa_audio_form2"] += 1
        if flags & F_VIDEO:
            result["video"] += 1
        if flags & F_STR:
            result["str_mdec"] += 1
        if flags & F_STR_OTHER:
            result["str_outro_sttype"] += 1
        if flags & F_NOSYNC:
            result["sem_sync"] += 1
    if len(chunk) < count:
        result["fora_da_faixa"] = count - len(chunk)
    return result


class DataTrackStream(io.RawIOBase):
    """Visão lógica de 2048 bytes/setor de uma faixa de dados (somente leitura).

    O setor lógico N corresponde ao LBA absoluto N. Setores antes do início
    da faixa no arquivo são lidos como zeros; o fluxo termina no último setor
    da faixa. Aceito pelo pycdlib (``open_fp``) e pelo leitor ISO9660 próprio.
    """

    def __init__(self, path: PathLike, begin_byte: int, sector_size: int, user_offset: int,
                 first_lba: int, sectors: int):
        super().__init__()
        self._path = os.fspath(path)
        self._fh = open_readonly(path)
        self._begin = begin_byte
        self._size = sector_size
        self._offset = user_offset
        self._first = first_lba
        self._sectors = sectors
        self._pos = 0
        self._length = (first_lba + sectors) * 2048

    def worker_params(self) -> dict:
        """Parâmetros para reabrir a mesma visão lógica em outro processo."""
        return {
            "path": self._path,
            "begin_byte": self._begin,
            "sector_size": self._size,
            "user_offset": self._offset,
            "first_lba": self._first,
            "sectors": self._sectors,
        }

    @property
    def mode(self) -> str:
        return "rb"

    @property
    def name(self) -> str:
        return "<faixa-de-dados>"

    @property
    def length(self) -> int:
        return self._length

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def writable(self) -> bool:
        return False

    def tell(self) -> int:
        return self._pos

    def seek(self, offset: int, whence: int = 0) -> int:
        if whence == 0:
            new = offset
        elif whence == 1:
            new = self._pos + offset
        elif whence == 2:
            new = self._length + offset
        else:
            raise ValueError("whence inválido")
        if new < 0:
            raise ValueError("posição negativa")
        self._pos = new
        return self._pos

    def _read_sectors(self, lba: int, count: int) -> bytes:
        """Lê ``count`` setores lógicos a partir de ``lba`` (2048 bytes cada)."""
        out = bytearray()
        if lba < self._first:
            zeros = min(count, self._first - lba)
            out += bytes(zeros * 2048)
            lba += zeros
            count -= zeros
        if count <= 0:
            return bytes(out)
        rel = lba - self._first
        count = min(count, self._sectors - rel)
        if count <= 0:
            return bytes(out)
        self._fh.seek(self._begin + rel * self._size)
        raw = self._fh.read(count * self._size)
        if self._size == 2048 and self._offset == 0:
            out += raw
            missing = count * 2048 - len(raw)
            if missing > 0:
                out += bytes(missing)
            return bytes(out)
        view = memoryview(raw)
        for k in range(count):
            start = k * self._size + self._offset
            piece = view[start:start + 2048]
            out += piece
            if len(piece) < 2048:
                out += bytes(2048 - len(piece))
        return bytes(out)

    def readinto(self, buffer) -> int:
        view = memoryview(buffer).cast("B")
        wanted = min(len(view), max(self._length - self._pos, 0))
        done = 0
        while done < wanted:
            lba, within = divmod(self._pos, 2048)
            need_sectors = min((within + (wanted - done) + 2047) // 2048, _SECTORS_PER_READ)
            data = self._read_sectors(lba, need_sectors)
            if not data:
                break
            piece = data[within:within + (wanted - done)]
            if not piece:
                break
            view[done:done + len(piece)] = piece
            done += len(piece)
            self._pos += len(piece)
        return done

    def close(self) -> None:
        try:
            self._fh.close()
        finally:
            super().close()


def probe_raw_image(path: PathLike, size: int, container: dict) -> dict:
    """Define o layout de uma imagem sem CUE a partir da assinatura detectada."""
    fmt = container.get("format")
    if fmt == "iso9660":
        track_type, sector_size = "MODE1/2048", 2048
    elif fmt == "cd_raw_2336":
        track_type, sector_size = "MODE2/2336", 2336
    elif fmt == "cd_raw_2352":
        mode = container.get("mode")
        track_type = "MODE2/2352" if mode == 2 else "MODE1/2352" if mode == 1 else None
        sector_size = 2352
        if track_type is None:
            return {"erro": f"byte de modo {mode} no primeiro setor não é 1 nem 2"}
    else:
        return {"erro": "formato não é imagem de disco reconhecida"}
    warnings: List[str] = []
    if size % sector_size:
        warnings.append(f"tamanho ({size}) não é múltiplo de {sector_size}; setor final incompleto ignorado")
    return {"tipo_faixa": track_type, "tamanho_setor": sector_size, "setores": size // sector_size, "avisos": warnings}


def layout_for_single_track(path, file_name: str, size: int, track_type: str) -> TrackLayout:
    from .cue import TRACK_TYPES

    info = TRACK_TYPES[track_type]
    layout = TrackLayout(
        number=1,
        type=track_type,
        kind=info["kind"],
        sector_size=info["sector_size"],
        user_offset=info["user_offset"],
        file_path=path,
        file_name=file_name,
        file_size=size,
        begin_byte=0,
        index01_byte=0,
        sectors=size // info["sector_size"],
        abs_lba_begin=0,
        abs_lba_index01=0,
    )
    return layout


def describe_duration(sectors: Optional[int]) -> Optional[str]:
    if sectors is None:
        return None
    return f"{frames_to_msf(sectors)} ({sectors / FRAMES_PER_SECOND:.3f} s)"
