"""Leitor ISO9660 próprio, tolerante, com verificação cruzada via pycdlib.

Decisão (documentada no README): o inventário usa um parser próprio mínimo
(descritores de volume + registros de diretório) porque ele

* registra problemas como AVISOS em vez de abortar (discos de PS1 podem ter
  campos atípicos; pycdlib é estrito e pode recusar a imagem inteira);
* lê o campo de sistema CD-XA (14 bytes) de cada registro (atributos
  Form1/Form2/intercalado/CD-DA — psx-spx "CDROM ISO File and Directory
  Descriptors");
* protege contra laços de diretório, limita profundidade/quantidade e o
  tamanho lido de cada diretório (``max_iso_dir_bytes``), lendo setor a setor
  só o que existe na faixa; cada problema estrutural vira uma ANOMALIA
  registrada (``anomalias``).

Em seguida, a mesma visão lógica é aberta com pycdlib (``open_fp``) e as
listas (caminho, LBA, tamanho) são comparadas; divergências viram avisos. O
pycdlib NÃO tem proteção contra laços: ele roda num PROCESSO SEPARADO com
tempo e memória limitados (``pycdlib_worker``) e nem é executado quando o
parser próprio já encontrou laço, diretório gigante ou profundidade excessiva.

Layouts (psx-spx "CDROM ISO Volume Descriptors"): descritores a partir do
setor 16; PVD com ``CD001``, identificadores, tamanho do volume (2x32 bits),
tamanho de bloco (2x16), registro do diretório raiz em 09Ch (34 bytes), datas
de 17 bytes e assinatura ``CD-XA001`` em 400h.
"""

from __future__ import annotations

import json
import struct
import subprocess
import sys
from typing import Dict, List, Optional, Set

from .config import FORENSICS_DIR, Limits

SECTOR = 2048
# Anomalias que impedem executar o pycdlib com segurança (ele entraria em laço
# ou alocaria memória sem limite).
UNSAFE_FOR_PYCDLIB = {"laco_de_diretorio", "diretorio_grande", "profundidade_maxima"}
VD_TYPES = {0: "boot record", 1: "primário", 2: "suplementar", 3: "partição", 255: "terminador"}
XA_BITS = [
    (11, "mode2"),
    (12, "mode2_form2"),
    (13, "intercalado"),
    (14, "cdda"),
    (15, "diretorio"),
]
FILE_FLAG_BITS = [
    (0, "oculto"),
    (1, "diretorio"),
    (2, "associado"),
    (3, "record"),
    (4, "protecao"),
    (7, "multi_extensao"),
]


class Iso9660Error(Exception):
    pass


def _both32(data: bytes, off: int):
    return struct.unpack_from("<I", data, off)[0], struct.unpack_from(">I", data, off + 4)[0]


def _both16(data: bytes, off: int):
    return struct.unpack_from("<H", data, off)[0], struct.unpack_from(">H", data, off + 2)[0]


def _text(raw: bytes) -> str:
    return raw.decode("latin-1").rstrip(" \x00")


def _vd_date(raw: bytes) -> Optional[str]:
    digits = raw[:16]
    if digits in (b"0" * 16, b"\x00" * 16, b" " * 16):
        return None
    try:
        text = digits.decode("ascii")
    except UnicodeDecodeError:
        return "inválida:" + raw.hex()
    if not text.isdigit():
        return "inválida:" + raw.hex()
    tz = struct.unpack_from("b", raw, 16)[0]
    return (
        f"{text[0:4]}-{text[4:6]}-{text[6:8]} {text[8:10]}:{text[10:12]}:{text[12:14]}.{text[14:16]}"
        f" (GMT{_tz_text(tz)})"
    )


def _tz_text(quarter_hours: int) -> str:
    minutes = quarter_hours * 15
    sign = "+" if minutes >= 0 else "-"
    minutes = abs(minutes)
    return f"{sign}{minutes // 60:02d}:{minutes % 60:02d}"


def record_date(raw: bytes) -> Optional[str]:
    """Data de gravação de 7 bytes (ano-1900, mês, dia, h, min, s, fuso em 15 min)."""
    if raw == b"\x00" * 7:
        return None
    year, month, day, hour, minute, second = raw[:6]
    tz = struct.unpack_from("b", raw, 6)[0]
    if not (1 <= month <= 12 and 1 <= day <= 31 and hour < 24 and minute < 60 and second < 61):
        return "inválida:" + raw.hex()
    return f"{1900 + year:04d}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:{second:02d}{_tz_text(tz)}"


def _bits(value: int, table) -> List[str]:
    return [name for bit, name in table if value & (1 << bit)]


class IsoReader:
    def __init__(self, stream, limits: Optional[Limits] = None):
        self.stream = stream
        self.limits = limits or Limits()
        stream.seek(0, 2)
        self.length = stream.tell()
        self.total_sectors = self.length // SECTOR
        self.warnings: List[str] = []
        self.anomalies: List[dict] = []

    def anomaly(self, kind: str, message: str) -> None:
        self.warnings.append(message)
        self.anomalies.append({"tipo": kind, "detalhe": message})

    def read(self, lba: int, count: int = 1) -> bytes:
        """Lê setores existentes, um por vez (nunca aloca além do que a faixa tem)."""
        if lba < 0 or count <= 0:
            return b""
        count = max(0, min(count, self.total_sectors - lba))
        out = bytearray()
        self.stream.seek(lba * SECTOR)
        for _ in range(count):
            data = self.stream.read(SECTOR)
            if not data:
                break
            out += data
        return bytes(out)

    def read_bytes(self, offset: int, size: int) -> bytes:
        self.stream.seek(offset)
        return self.stream.read(size)

    # ------------------------------------------------------------ descriptors
    def volume_descriptors(self) -> List[dict]:
        descriptors = []
        for lba in range(16, 16 + 64):
            raw = self.read(lba)
            if len(raw) < SECTOR:
                self.warnings.append(f"setor {lba} ausente ao ler descritores de volume")
                break
            if raw[1:6] != b"CD001":
                if lba == 16:
                    raise Iso9660Error("setor 16 não contém 'CD001' (não é ISO9660)")
                self.warnings.append(f"setor {lba}: descritor sem 'CD001'; leitura dos descritores interrompida")
                break
            vd_type = raw[0]
            descriptors.append({"lba": lba, "tipo": vd_type, "descricao": VD_TYPES.get(vd_type, "reservado"), "versao": raw[6]})
            if vd_type == 255:
                break
        else:
            self.warnings.append("nenhum terminador de descritores nos 64 setores após o 16")
        return descriptors

    def primary_descriptor(self, descriptors: List[dict]) -> dict:
        pvd_entry = next((d for d in descriptors if d["tipo"] == 1), None)
        if pvd_entry is None:
            raise Iso9660Error("descritor de volume primário não encontrado")
        raw = self.read(pvd_entry["lba"])
        space_le, space_be = _both32(raw, 0x50)
        block_le, block_be = _both16(raw, 0x80)
        set_le, set_be = _both16(raw, 0x78)
        seq_le, seq_be = _both16(raw, 0x7C)
        pt_le, pt_be = _both32(raw, 0x84)
        for label, a, b in (
            ("tamanho do volume", space_le, space_be),
            ("tamanho de bloco", block_le, block_be),
            ("tamanho do conjunto", set_le, set_be),
            ("número de sequência", seq_le, seq_be),
            ("tamanho da tabela de caminhos", pt_le, pt_be),
        ):
            if a != b:
                self.warnings.append(f"PVD: {label} diverge entre little-endian ({a}) e big-endian ({b})")
        if block_le != SECTOR:
            self.warnings.append(f"PVD: tamanho de bloco lógico {block_le} (esperado 2048)")
        pvd = {
            "lba": pvd_entry["lba"],
            "versao": raw[6],
            "identificador_sistema": _text(raw[0x08:0x28]),
            "identificador_volume": _text(raw[0x28:0x48]),
            "tamanho_volume_blocos": space_le,
            "tamanho_conjunto_volumes": set_le,
            "numero_sequencia_volume": seq_le,
            "tamanho_bloco_logico": block_le,
            "tamanho_tabela_caminhos": pt_le,
            "tabela_caminhos_l": struct.unpack_from("<I", raw, 0x8C)[0],
            "tabela_caminhos_l_opcional": struct.unpack_from("<I", raw, 0x90)[0],
            "tabela_caminhos_m": struct.unpack_from(">I", raw, 0x94)[0],
            "tabela_caminhos_m_opcional": struct.unpack_from(">I", raw, 0x98)[0],
            "identificador_conjunto_volumes": _text(raw[0xBE:0x13E]),
            "identificador_editor": _text(raw[0x13E:0x1BE]),
            "identificador_preparador": _text(raw[0x1BE:0x23E]),
            "identificador_aplicacao": _text(raw[0x23E:0x2BE]),
            "arquivo_copyright": _text(raw[0x2BE:0x2E3]),
            "arquivo_resumo": _text(raw[0x2E3:0x308]),
            "arquivo_bibliografico": _text(raw[0x308:0x32D]),
            "data_criacao": _vd_date(raw[0x32D:0x33E]),
            "data_modificacao": _vd_date(raw[0x33E:0x34F]),
            "data_expiracao": _vd_date(raw[0x34F:0x360]),
            "data_efetiva": _vd_date(raw[0x360:0x371]),
            "versao_estrutura_arquivos": raw[0x371],
            "assinatura_cd_xa": _text(raw[0x400:0x408]) or None,
            "fonte": "psx-spx: CDROM ISO Volume Descriptors",
        }
        if space_le > self.total_sectors:
            self.warnings.append(
                f"PVD declara {space_le} blocos, mas a faixa de dados tem {self.total_sectors} setores"
            )
        root = self._parse_record(raw, 0x9C, context="registro raiz do PVD")
        if root is None:
            raise Iso9660Error("registro do diretório raiz inválido no PVD")
        pvd["_root"] = root
        return pvd

    # ------------------------------------------------------------ records
    def _parse_record(self, buf: bytes, off: int, context: str) -> Optional[dict]:
        length = buf[off]
        if length == 0:
            return None
        if length < 34 or off + length > len(buf):
            self.warnings.append(f"{context}: registro de diretório com tamanho inválido ({length})")
            return None
        rec = buf[off:off + length]
        lba_le, lba_be = _both32(rec, 2)
        size_le, size_be = _both32(rec, 10)
        if lba_le != lba_be:
            self.warnings.append(f"{context}: LBA diverge LE/BE ({lba_le}/{lba_be})")
        if size_le != size_be:
            self.warnings.append(f"{context}: tamanho diverge LE/BE ({size_le}/{size_be})")
        name_len = rec[32]
        if 33 + name_len > length:
            self.warnings.append(f"{context}: nome ultrapassa o registro")
            return None
        name_raw = rec[33:33 + name_len]
        pad = 1 if name_len % 2 == 0 else 0
        system_use = rec[33 + name_len + pad:]
        flags = rec[25]
        entry = {
            "name_raw": name_raw,
            "lba": lba_le,
            "size": size_le,
            "date": record_date(rec[18:25]),
            "flags": flags,
            "is_dir": bool(flags & 0x02),
            "ext_attr_len": rec[1],
            "file_unit_size": rec[26],
            "interleave_gap": rec[27],
            "xa": None,
        }
        if len(system_use) >= 14 and system_use[6:8] == b"XA":
            attributes = struct.unpack_from(">H", system_use, 4)[0]
            entry["xa"] = {
                "atributos": f"0x{attributes:04x}",
                "bits": _bits(attributes, XA_BITS),
                "numero_arquivo": system_use[8],
                "grupo": struct.unpack_from(">H", system_use, 0)[0],
                "usuario": struct.unpack_from(">H", system_use, 2)[0],
            }
        elif system_use:
            entry["system_use_bytes"] = len(system_use)
        return entry

    def walk(self, root: dict) -> List[dict]:
        entries: List[dict] = [
            {
                "path": "/",
                "name": "",
                "is_dir": True,
                "lba": root["lba"],
                "size": root["size"],
                "date": root["date"],
                "flags": root["flags"],
                "xa": root["xa"],
                "depth": 0,
            }
        ]
        visited: Set[int] = set()
        stack = [("/", root, 0)]
        while stack:
            path, record, depth = stack.pop()
            if record["lba"] in visited:
                self.anomaly("laco_de_diretorio", f"diretório {path} aponta para LBA já visitado ({record['lba']}); laço ignorado")
                continue
            visited.add(record["lba"])
            if depth > self.limits.max_iso_dir_depth:
                self.anomaly("profundidade_maxima", f"profundidade máxima de diretórios atingida em {path}")
                continue
            size = record["size"]
            if size > self.limits.max_iso_dir_bytes:
                self.anomaly(
                    "diretorio_grande",
                    f"diretório {path} declara {size} bytes (acima do limite de segurança de "
                    f"{self.limits.max_iso_dir_bytes}); lidos apenas os primeiros {self.limits.max_iso_dir_bytes}",
                )
                size = self.limits.max_iso_dir_bytes
            sectors = (size + SECTOR - 1) // SECTOR
            if record["lba"] + sectors > self.total_sectors:
                self.anomaly("diretorio_alem_do_fim", f"diretório {path} ultrapassa o fim da faixa de dados")
            data = self.read(record["lba"], sectors)
            sectors = len(data) // SECTOR
            children = []
            for sector_index in range(sectors):
                base = sector_index * SECTOR
                off = 0
                while off < SECTOR:
                    absolute = base + off
                    if absolute >= len(data):
                        break
                    length = data[absolute]
                    if length == 0:
                        break  # resto do setor é preenchimento
                    child = self._parse_record(data[base:base + SECTOR], off, context=f"diretório {path}")
                    if child is None:
                        break
                    off += length
                    if child["name_raw"] in (b"\x00", b"\x01"):
                        continue
                    children.append(child)
            for child in children:
                raw = child["name_raw"]
                try:
                    name = raw.decode("ascii")
                except UnicodeDecodeError:
                    name = raw.decode("latin-1")
                    self.warnings.append(f"nome não-ASCII em {path}: {raw.hex()}")
                child_path = (path.rstrip("/") + "/" + name) if path != "/" else "/" + name
                item = {
                    "path": child_path,
                    "name": name,
                    "is_dir": child["is_dir"],
                    "lba": child["lba"],
                    "size": child["size"],
                    "date": child["date"],
                    "flags": child["flags"],
                    "flags_desc": _bits(child["flags"], FILE_FLAG_BITS),
                    "xa": child["xa"],
                    "depth": depth + 1,
                }
                if child["ext_attr_len"]:
                    item["ext_attr_len"] = child["ext_attr_len"]
                if child["file_unit_size"] or child["interleave_gap"]:
                    item["intercalacao_iso"] = {"unidade": child["file_unit_size"], "lacuna": child["interleave_gap"]}
                if child["flags"] & 0x80:
                    self.warnings.append(f"{child_path}: arquivo multi-extensão (apenas a extensão listada é lida)")
                entries.append(item)
                if len(entries) > self.limits.max_iso_entries:
                    raise Iso9660Error("limite de entradas ISO9660 excedido")
                if child["is_dir"]:
                    stack.append((child_path, child, depth + 1))
        return entries


def parse_iso(stream, limits: Optional[Limits] = None) -> dict:
    reader = IsoReader(stream, limits)
    descriptors = reader.volume_descriptors()
    pvd = reader.primary_descriptor(descriptors)
    root = pvd.pop("_root")
    entries = reader.walk(root)
    for entry in entries:
        entry["sectors"] = (entry["size"] + SECTOR - 1) // SECTOR
        if not entry["is_dir"] and entry["size"] and entry["lba"] + entry["sectors"] > reader.total_sectors:
            reader.warnings.append(f"{entry['path']}: extensão ultrapassa o fim da faixa de dados")
            entry["alem_do_fim"] = True
    return {
        "descritores": descriptors,
        "pvd": pvd,
        "entries": entries,
        "warnings": reader.warnings,
        "anomalias": reader.anomalies,
        "setores_na_faixa": reader.total_sectors,
    }


def read_extent(stream, lba: int, size: int, chunk: int = 1 << 20):
    """Gera os bytes de um arquivo a partir do fluxo lógico (2048 bytes/setor)."""
    stream.seek(lba * SECTOR)
    remaining = size
    while remaining > 0:
        data = stream.read(min(chunk, remaining))
        if not data:
            break
        remaining -= len(data)
        yield data


def pycdlib_crosscheck(source, entries: List[dict], limits: Optional[Limits] = None) -> Dict[str, object]:
    """Abre a mesma visão lógica com pycdlib, em processo isolado, e compara caminho/LBA/tamanho.

    ``source``: um ``DataTrackStream`` (ou o dict de ``worker_params()``).
    Status possíveis: ``ok``, ``divergente``, ``erro``, ``tempo_esgotado``,
    ``memoria_excedida``, ``indisponivel``.
    """
    limits = limits or Limits()
    params = dict(source.worker_params() if hasattr(source, "worker_params") else source)
    params["max_memory"] = int(limits.pycdlib_max_memory)
    if not sys.executable:
        return {"status": "indisponivel", "erro": "interpretador Python não identificado para o processo isolado"}
    command = [
        sys.executable,
        "-c",
        "import sys; sys.path.insert(0, sys.argv[1]); from tsr_forensics.pycdlib_worker import main; sys.exit(main())",
        str(FORENSICS_DIR),
    ]
    try:
        proc = subprocess.run(
            command,
            input=json.dumps(params, ensure_ascii=False).encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=limits.pycdlib_timeout_s,
        )
    except subprocess.TimeoutExpired:
        return {
            "status": "tempo_esgotado",
            "erro": f"pycdlib não terminou em {limits.pycdlib_timeout_s:g} s (processo encerrado); possível laço na imagem",
        }
    except OSError as exc:
        return {"status": "indisponivel", "erro": f"{type(exc).__name__}: {exc}"}
    from .pycdlib_worker import MEMORY_EXIT

    if proc.returncode == MEMORY_EXIT:
        return {
            "status": "memoria_excedida",
            "erro": f"pycdlib passou de {limits.pycdlib_max_memory} bytes de memória (processo encerrado); possível laço na imagem",
        }
    try:
        theirs_result = json.loads(proc.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        tail = proc.stderr.decode("utf-8", "replace").strip().splitlines()[-1:] or [""]
        return {"status": "erro", "erro": f"processo isolado terminou com código {proc.returncode}: {tail[0][:300]}"}
    if theirs_result.get("status") != "ok":
        return {"status": theirs_result.get("status", "erro"), "erro": theirs_result.get("erro")}
    theirs = {k: tuple(v) for k, v in theirs_result["arquivos"].items()}
    ours = {e["path"].upper(): (e["lba"], e["size"]) for e in entries if not e["is_dir"]}
    only_ours = sorted(set(ours) - set(theirs))
    only_theirs = sorted(set(theirs) - set(ours))
    different = sorted(k for k in set(ours) & set(theirs) if ours[k] != theirs[k])
    status = "ok" if not (only_ours or only_theirs or different) else "divergente"
    return {
        "status": status,
        "processo_isolado": True,
        "arquivos_comparados": len(set(ours) & set(theirs)),
        "somente_parser_proprio": only_ours[:50],
        "somente_pycdlib": only_theirs[:50],
        "lba_ou_tamanho_diferente": [
            {"caminho": k, "proprio": ours[k], "pycdlib": theirs[k]} for k in different[:50]
        ],
    }
