"""Parser de CUE sheets (CDRWIN) e cálculo do layout das faixas.

Referência: psx-spx, "CDROM Disk Images CUE/BIN/CDT (Cdrwin)":

* tipos de faixa e tamanho de setor::

    AUDIO 930h | MODE1/2048 800h | MODE1/2352 930h | MODE2/2336 920h
    MODE2/2352 930h | CDI/2336 920h | CDI/2352 930h | CDG ? (não confirmado)

* o .BIN começa em 00:02:00 (os 2 segundos iniciais não são gravados);
* ``PREGAP``/``POSTGAP`` NÃO estão no .BIN e deslocam os endereços seguintes;
* ``INDEX 00`` (quando existe) marca o início do pregap gravado no arquivo;
* existem CUEs "malformados" com número de faixa/índice de 1 dígito.

Deslocamentos de dados do usuário (psx-spx "CDROM Sector Encoding"):
Mode1/2352 → 010h; Mode2/2352 (Form1) → 018h; Mode2/2336 → 008h (a
imagem começa no subheader).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .fsutil import PathLike, open_readonly

TRACK_TYPES: Dict[str, dict] = {
    "AUDIO": {"sector_size": 2352, "kind": "audio", "user_offset": None},
    "MODE1/2048": {"sector_size": 2048, "kind": "data", "user_offset": 0},
    "MODE1/2352": {"sector_size": 2352, "kind": "data", "user_offset": 16},
    "MODE2/2352": {"sector_size": 2352, "kind": "data", "user_offset": 24},
    "MODE2/2336": {"sector_size": 2336, "kind": "data", "user_offset": 8},
    # CD-i: tamanho do setor documentado; leitura ISO9660 não se aplica.
    "CDI/2352": {"sector_size": 2352, "kind": "cdi", "user_offset": None},
    "CDI/2336": {"sector_size": 2336, "kind": "cdi", "user_offset": None},
}
FRAMES_PER_SECOND = 75
MAX_CUE_BYTES = 1 << 20


class CueError(Exception):
    pass


@dataclass
class CueTrack:
    number: int
    type: str
    file_index: int
    line: int
    indexes: Dict[int, int] = field(default_factory=dict)
    pregap: int = 0
    postgap: int = 0
    flags: List[str] = field(default_factory=list)
    isrc: Optional[str] = None
    title: Optional[str] = None
    performer: Optional[str] = None

    @property
    def known_type(self) -> bool:
        return self.type in TRACK_TYPES

    @property
    def sector_size(self) -> Optional[int]:
        info = TRACK_TYPES.get(self.type)
        return info["sector_size"] if info else None

    def first_index(self) -> Optional[int]:
        return min(self.indexes.values()) if self.indexes else None


@dataclass
class CueFile:
    name: str
    filetype: str
    line: int
    tracks: List[int] = field(default_factory=list)


@dataclass
class CueSheet:
    files: List[CueFile] = field(default_factory=list)
    tracks: List[CueTrack] = field(default_factory=list)
    catalog: Optional[str] = None
    title: Optional[str] = None
    performer: Optional[str] = None
    rems: List[str] = field(default_factory=list)
    cdtextfile: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    encoding: str = "utf-8"

    def to_dict(self) -> dict:
        return {
            "codificacao": self.encoding,
            "catalog": self.catalog,
            "title": self.title,
            "performer": self.performer,
            "rem": self.rems,
            "cdtextfile": self.cdtextfile,
            "arquivos": [
                {"nome": f.name, "tipo": f.filetype, "linha": f.line, "faixas": [self.tracks[i].number for i in f.tracks]}
                for f in self.files
            ],
            "faixas": [
                {
                    "numero": t.number,
                    "tipo": t.type,
                    "tipo_reconhecido": t.known_type,
                    "arquivo": self.files[t.file_index].name,
                    "indices": {f"{k:02d}": frames_to_msf(v) for k, v in sorted(t.indexes.items())},
                    "pregap": frames_to_msf(t.pregap) if t.pregap else None,
                    "postgap": frames_to_msf(t.postgap) if t.postgap else None,
                    "flags": t.flags,
                    "isrc": t.isrc,
                    "title": t.title,
                    "performer": t.performer,
                }
                for t in self.tracks
            ],
            "avisos": self.warnings,
        }


_MSF_RE = re.compile(r"^(\d{1,3}):(\d{1,2}):(\d{1,2})$")


def msf_to_frames(text: str) -> int:
    match = _MSF_RE.match(text.strip())
    if not match:
        raise CueError(f"tempo MM:SS:FF inválido: {text!r}")
    minutes, seconds, frames = (int(g) for g in match.groups())
    if seconds >= 60 or frames >= FRAMES_PER_SECOND:
        raise CueError(f"tempo MM:SS:FF fora do intervalo: {text!r}")
    return (minutes * 60 + seconds) * FRAMES_PER_SECOND + frames


def frames_to_msf(frames: int) -> str:
    minutes, rest = divmod(int(frames), 60 * FRAMES_PER_SECOND)
    seconds, frame = divmod(rest, FRAMES_PER_SECOND)
    return f"{minutes:02d}:{seconds:02d}:{frame:02d}"


def _unquote(text: str) -> str:
    text = text.strip()
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        return text[1:-1]
    return text


def _parse_file_args(rest: str):
    rest = rest.strip()
    if rest.startswith('"'):
        end = rest.find('"', 1)
        if end == -1:
            raise CueError("FILE com aspas não fechadas")
        return rest[1:end], rest[end + 1:].strip().upper()
    parts = rest.rsplit(None, 1)
    if len(parts) != 2:
        raise CueError("FILE sem tipo")
    return parts[0], parts[1].upper()


def decode_cue_bytes(raw: bytes):
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise CueError("codificação do CUE não reconhecida")  # pragma: no cover


def parse_cue_text(text: str) -> CueSheet:
    sheet = CueSheet()
    current_file: Optional[int] = None
    current_track: Optional[CueTrack] = None
    for number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        command, _, rest = line.partition(" ")
        command = command.upper()
        rest = rest.strip()
        try:
            if command == "REM":
                sheet.rems.append(rest)
            elif command == "CATALOG":
                sheet.catalog = rest
            elif command == "CDTEXTFILE":
                sheet.cdtextfile = _unquote(rest)
            elif command == "FILE":
                name, filetype = _parse_file_args(rest)
                sheet.files.append(CueFile(name=name, filetype=filetype, line=number))
                current_file = len(sheet.files) - 1
                current_track = None
                if filetype not in ("BINARY", "MOTOROLA"):
                    sheet.warnings.append(
                        f"linha {number}: FILE do tipo {filetype} não é imagem binária; faixas desse arquivo não serão lidas"
                    )
            elif command == "TRACK":
                if current_file is None:
                    raise CueError("TRACK antes de FILE")
                parts = rest.split()
                if len(parts) != 2:
                    raise CueError("TRACK deve ter número e tipo")
                track_no = int(parts[0])
                if len(parts[0]) == 1:
                    sheet.warnings.append(
                        f"linha {number}: número de faixa com 1 dígito (variante 'malformada' descrita em psx-spx)"
                    )
                track = CueTrack(number=track_no, type=parts[1].upper(), file_index=current_file, line=number)
                if not track.known_type:
                    sheet.warnings.append(
                        f"linha {number}: tipo de faixa {track.type} sem tamanho de setor confirmado; faixa apenas registrada"
                    )
                if sheet.tracks and track_no <= sheet.tracks[-1].number:
                    sheet.warnings.append(f"linha {number}: numeração de faixa não crescente ({track_no})")
                sheet.tracks.append(track)
                sheet.files[current_file].tracks.append(len(sheet.tracks) - 1)
                current_track = track
            elif command == "INDEX":
                if current_track is None:
                    raise CueError("INDEX fora de TRACK")
                parts = rest.split()
                if len(parts) != 2:
                    raise CueError("INDEX deve ter número e tempo")
                index_no = int(parts[0])
                if index_no in current_track.indexes:
                    raise CueError(f"INDEX {index_no:02d} repetido")
                current_track.indexes[index_no] = msf_to_frames(parts[1])
            elif command == "PREGAP":
                if current_track is None:
                    raise CueError("PREGAP fora de TRACK")
                current_track.pregap = msf_to_frames(rest)
            elif command == "POSTGAP":
                if current_track is None:
                    raise CueError("POSTGAP fora de TRACK")
                current_track.postgap = msf_to_frames(rest)
            elif command == "FLAGS":
                if current_track is None:
                    raise CueError("FLAGS fora de TRACK")
                current_track.flags = rest.upper().split()
            elif command == "ISRC":
                if current_track is None:
                    raise CueError("ISRC fora de TRACK")
                current_track.isrc = rest
            elif command in ("TITLE", "PERFORMER", "SONGWRITER"):
                value = _unquote(rest)
                if current_track is not None and command != "SONGWRITER":
                    setattr(current_track, command.lower(), value)
                elif command == "TITLE":
                    sheet.title = value
                elif command == "PERFORMER":
                    sheet.performer = value
            else:
                sheet.warnings.append(f"linha {number}: comando desconhecido {command!r} ignorado")
        except (CueError, ValueError) as exc:
            sheet.warnings.append(f"linha {number}: {exc}")
    for track in sheet.tracks:
        if 1 not in track.indexes:
            sheet.warnings.append(f"faixa {track.number:02d}: sem INDEX 01")
        indexes = sorted(track.indexes.items())
        values = [v for _, v in indexes]
        if values != sorted(values):
            sheet.warnings.append(f"faixa {track.number:02d}: índices fora de ordem")
    for cue_file in sheet.files:
        if cue_file.tracks:
            first = sheet.tracks[cue_file.tracks[0]]
            if first.first_index() not in (0, None):
                sheet.warnings.append(
                    f"arquivo {cue_file.name!r}: primeiro índice da faixa {first.number:02d} não é 00:00:00"
                )
    if not sheet.files:
        sheet.warnings.append("nenhum comando FILE encontrado")
    return sheet


def parse_cue_file(path: PathLike) -> CueSheet:
    with open_readonly(path) as handle:
        raw = handle.read(MAX_CUE_BYTES + 1)
    if len(raw) > MAX_CUE_BYTES:
        raise CueError("arquivo CUE maior que 1 MiB; recusado")
    text, encoding = decode_cue_bytes(raw)
    sheet = parse_cue_text(text)
    sheet.encoding = encoding
    return sheet


@dataclass
class TrackLayout:
    """Posição de uma faixa dentro do arquivo de imagem e no disco."""

    number: int
    type: str
    kind: str  # "audio" | "data" | "cdi" | "desconhecido"
    sector_size: Optional[int]
    user_offset: Optional[int]
    file_path: Optional[Path]
    file_name: str
    file_size: Optional[int]
    begin_byte: Optional[int] = None  # primeiro índice (00 se houver)
    index01_byte: Optional[int] = None
    sectors: Optional[int] = None  # do primeiro índice até o fim da faixa no arquivo
    pregap_in_file: int = 0  # INDEX 01 - INDEX 00
    pregap_not_in_file: int = 0  # comando PREGAP
    postgap_not_in_file: int = 0
    abs_lba_begin: Optional[int] = None
    abs_lba_index01: Optional[int] = None
    warnings: List[str] = field(default_factory=list)

    @property
    def sectors_from_index01(self) -> Optional[int]:
        if self.sectors is None:
            return None
        return self.sectors - self.pregap_in_file

    def to_dict(self) -> dict:
        from_index01 = self.sectors_from_index01
        return {
            "numero": self.number,
            "tipo": self.type,
            "natureza": self.kind,
            "tamanho_setor": self.sector_size,
            "arquivo": self.file_name,
            "byte_inicial": self.begin_byte,
            "byte_index01": self.index01_byte,
            "setores": self.sectors,
            "setores_pregap_no_arquivo": self.pregap_in_file,
            "setores_pregap_fora_do_arquivo": self.pregap_not_in_file,
            "setores_postgap_fora_do_arquivo": self.postgap_not_in_file,
            "setores_a_partir_index01": from_index01,
            "duracao_segundos": None if self.sectors is None else round(self.sectors / FRAMES_PER_SECOND, 3),
            "duracao_a_partir_index01_segundos": None if from_index01 is None else round(from_index01 / FRAMES_PER_SECOND, 3),
            "duracao_msf": None if self.sectors is None else frames_to_msf(self.sectors),
            "lba_inicio": self.abs_lba_begin,
            "lba_index01": self.abs_lba_index01,
            "msf_absoluto_index01": None if self.abs_lba_index01 is None else frames_to_msf(self.abs_lba_index01 + 150),
            "avisos": self.warnings,
        }


def compute_layout(sheet: CueSheet, resolved: List[Optional[Path]], sizes: List[Optional[int]]) -> List[TrackLayout]:
    """Calcula bytes e LBAs de cada faixa.

    ``resolved``/``sizes``: caminho e tamanho de cada FILE do CUE (None se ausente).
    Endereços absolutos seguem psx-spx: LBA 0 = MSF 00:02:00 (início do .BIN);
    PREGAP/POSTGAP deslocam todos os endereços seguintes.

    Num CUE com vários FILE, o LBA absoluto de um arquivo depende do número de
    setores de TODOS os arquivos anteriores. Se algum deles estiver ausente ou
    tiver tamanho/faixas indeterminados, os LBAs absolutos das faixas seguintes
    ficam ``None`` (NÃO CONFIRMADOS), com aviso — nunca um valor deslocado.
    """
    layouts: List[TrackLayout] = []
    file_base_lba = 0
    gap_shift = 0
    base_known = True
    unknown_reason = ""
    for file_index, cue_file in enumerate(sheet.files):
        path = resolved[file_index]
        size = sizes[file_index]
        track_ids = cue_file.tracks
        begin_bytes: List[Optional[int]] = []
        file_layouts: List[TrackLayout] = []
        running_byte = 0
        prev_start = None
        prev_size = None
        for position, track_id in enumerate(track_ids):
            track = sheet.tracks[track_id]
            info = TRACK_TYPES.get(track.type)
            layout = TrackLayout(
                number=track.number,
                type=track.type,
                kind=info["kind"] if info else "desconhecido",
                sector_size=info["sector_size"] if info else None,
                user_offset=info["user_offset"] if info else None,
                file_path=path,
                file_name=cue_file.name,
                file_size=size,
                pregap_not_in_file=track.pregap,
                postgap_not_in_file=track.postgap,
            )
            start = track.first_index()
            if start is None or layout.sector_size is None:
                layout.warnings.append("faixa sem índice ou com tipo sem tamanho de setor: posição não calculada")
                begin_bytes.append(None)
                file_layouts.append(layout)
                prev_start = None
                continue
            if position == 0:
                running_byte = start * layout.sector_size
            elif prev_start is not None and prev_size is not None:
                running_byte = running_byte + (start - prev_start) * prev_size
            else:
                layout.warnings.append("faixa anterior sem posição: posição desta faixa não calculada")
                begin_bytes.append(None)
                file_layouts.append(layout)
                prev_start = None
                continue
            layout.begin_byte = running_byte
            index01 = track.indexes.get(1, start)
            layout.pregap_in_file = index01 - start
            layout.index01_byte = running_byte + layout.pregap_in_file * layout.sector_size
            gap_shift += track.pregap
            if base_known:
                layout.abs_lba_begin = file_base_lba + start + gap_shift
                layout.abs_lba_index01 = file_base_lba + index01 + gap_shift
            else:
                layout.warnings.append(
                    f"LBA absoluto NÃO CONFIRMADO: {unknown_reason}; o número de setores anteriores é desconhecido"
                )
            gap_shift += track.postgap  # POSTGAP desloca apenas as faixas seguintes
            begin_bytes.append(running_byte)
            file_layouts.append(layout)
            prev_start = start
            prev_size = layout.sector_size
        # fim de cada faixa = início da próxima faixa do mesmo arquivo, ou fim do arquivo
        total_sectors = 0
        for position, layout in enumerate(file_layouts):
            if layout.begin_byte is None:
                continue
            next_begin = None
            for later in file_layouts[position + 1:]:
                if later.begin_byte is not None:
                    next_begin = later.begin_byte
                    break
            end = next_begin if next_begin is not None else size
            if end is None:
                layout.warnings.append("arquivo da faixa ausente: tamanho desconhecido")
                continue
            length = end - layout.begin_byte
            if length < 0:
                layout.warnings.append("faixa com tamanho negativo (índices incoerentes com o arquivo)")
                continue
            if length % layout.sector_size:
                layout.warnings.append(
                    f"tamanho da faixa ({length} bytes) não é múltiplo do setor ({layout.sector_size}); "
                    "setor final incompleto ignorado"
                )
            layout.sectors = length // layout.sector_size
            total_sectors += layout.sectors
        first = next((l for l in file_layouts if l.begin_byte is not None), None)
        leading = 0
        if first is not None and first.sector_size:
            leading = first.begin_byte // first.sector_size
        file_base_lba += total_sectors + leading
        if base_known:
            if size is None:
                base_known = False
                unknown_reason = f"arquivo anterior {cue_file.name!r} ausente"
            elif not file_layouts or any(l.sectors is None for l in file_layouts):
                base_known = False
                unknown_reason = f"faixas do arquivo anterior {cue_file.name!r} com tamanho indeterminado"
        layouts.extend(file_layouts)
    return layouts
