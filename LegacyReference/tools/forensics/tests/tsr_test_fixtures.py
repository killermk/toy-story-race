"""Fixtures SINTÉTICAS para os testes (geradas em diretório temporário).

Nada aqui vem do jogo real: cabeçalhos PS1 falsos construídos a partir da
documentação (psx-spx), serial FALSO "TEST_000.00", áudio sintético.
Nenhum binário de fixture é versionado.
"""

from __future__ import annotations

import io
import os
import random
import struct
import sys
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
KIT_DIR = HERE.parent
if str(KIT_DIR) not in sys.path:
    sys.path.insert(0, str(KIT_DIR))

SYNC = b"\x00" + b"\xff" * 10 + b"\x00"

SYSTEM_CNF = b"BOOT = cdrom:\\TEST_000.00;1\r\nTCB = 4\r\nEVENT = 10\r\nSTACK = 801FFFF0\r\n"


def fake_psx_exe(code_size: int = 0x800) -> bytes:
    header = bytearray(0x800)
    header[0:8] = b"PS-X EXE"
    struct.pack_into("<IIII", header, 0x10, 0x80010000, 0, 0x80010000, code_size)
    struct.pack_into("<I", header, 0x30, 0x801FFFF0)
    header[0x4C:0x4C + 20] = b"FAKE TEST MARKER ONLY"[:20]
    body = bytes((i * 7) & 0xFF for i in range(code_size))
    return bytes(header) + body


def fake_tim(width_px: int = 16, height: int = 16) -> bytes:
    """TIM 4bpp com CLUT de 16 cores (psx-spx: seções com tamanho w*2*h+12)."""
    data = bytearray(b"\x10\x00\x00\x00")
    data += struct.pack("<I", 0x08 | 0x00)  # HasCLUT + 4bpp
    clut_w, clut_h = 16, 1
    data += struct.pack("<IHHHH", clut_w * 2 * clut_h + 12, 0, 480, clut_w, clut_h)
    data += bytes(range(32))
    w_half = width_px // 4  # 4bpp: 4 pixels por halfword
    data += struct.pack("<IHHHH", w_half * 2 * height + 12, 320, 0, w_half, height)
    data += bytes((i * 3) & 0xFF for i in range(w_half * 2 * height))
    return bytes(data)


def broken_tim() -> bytes:
    data = bytearray(fake_tim())
    struct.pack_into("<I", data, 8, 9999)  # tamanho de seção incoerente
    return bytes(data)


def fake_vag(samples: int = 64) -> bytes:
    header = bytearray(0x30)
    header[0:4] = b"VAGp"
    struct.pack_into(">IIII", header, 4, 0x20, 0, samples * 16, 22050)
    header[0x20:0x28] = b"TESTSND\x00"
    return bytes(header) + bytes(samples * 16)


def fake_vab() -> bytes:
    header = bytearray(0x20)
    header[0:4] = b"pBAV"
    struct.pack_into("<III", header, 4, 7, 0, 0x20 + 64)
    return bytes(header) + bytes(64)


def fake_seq() -> bytes:
    return b"pQES" + b"\x00\x00\x00\x01" + b"\x01\x80" + b"\x07\x27\x0e" + b"\x04\x02" + b"\xff\x2f\x00"


def fake_str(chunks: int = 4) -> bytes:
    out = bytearray()
    for index in range(chunks):
        sector = bytearray(2048)
        struct.pack_into("<HHHHII", sector, 0, 0x0160, 0x8001, index % 2, 2, 1 + index // 2, 1000)
        struct.pack_into("<HH", sector, 0x10, 320, 240)
        out += sector
    return bytes(out)


def random_blob(size: int, seed: int = 1234) -> bytes:
    rng = random.Random(seed)
    data = bytes(rng.getrandbits(8) for _ in range(size))
    if data[:1] == b"\x10":
        data = b"\x11" + data[1:]
    return data


ISO_FILES: Dict[str, bytes] = {}


def iso_contents() -> Dict[str, bytes]:
    return {
        "/SYSTEM.CNF;1": SYSTEM_CNF,
        "/TEST_000.00;1": fake_psx_exe(),
        "/DATA/TEX.TIM;1": fake_tim(),
        "/DATA/SND.VAG;1": fake_vag(),
        "/DATA/SUB/BLOB.DAT;1": random_blob(5000),
        "/DATA/SUB/NOTE.TXT;1": b"Arquivo de texto sintetico para teste.\r\n",
        "/SND/BANK.VAB;1": fake_vab(),
        "/SND/SONG.SEQ;1": fake_seq(),
        "/MOVIE/INTRO.STR;1": fake_str(),
        "/MUSIC/VOICE.XA;1": bytes(2048 * 4),
    }


def make_iso(contents: Optional[Dict[str, bytes]] = None, volume_id: str = "TESTDISC") -> Tuple[bytes, Dict[str, Tuple[int, int]]]:
    """Cria ISO9660 (2048) com pycdlib. Retorna (bytes, {caminho: (lba, tamanho)})."""
    import pycdlib

    contents = contents or iso_contents()
    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=1, sys_ident="PLAYSTATION", vol_ident=volume_id, xa=True)
    directories = set()
    for path in contents:
        parts = path.strip("/").split("/")[:-1]
        for depth in range(1, len(parts) + 1):
            directories.add("/" + "/".join(parts[:depth]))
    for directory in sorted(directories, key=lambda d: d.count("/")):
        iso.add_directory(directory)
    for path, data in contents.items():
        iso.add_fp(io.BytesIO(data), len(data), path)
    out = io.BytesIO()
    iso.write_fp(out)
    iso.close()
    raw = out.getvalue()
    check = pycdlib.PyCdlib()
    check.open_fp(io.BytesIO(raw))
    locations = {}
    for path in contents:
        record = check.get_record(iso_path=path)
        locations[path] = (record.extent_location(), record.get_data_length())
    check.close()
    return raw, locations


def _bcd(value: int) -> int:
    return ((value // 10) << 4) | (value % 10)


def raw_sector_mode2(lba: int, user: bytes, submode: int = 0x08, file_no: int = 0, channel: int = 0, coding: int = 0) -> bytes:
    msf = lba + 150
    minute, rest = divmod(msf, 75 * 60)
    second, frame = divmod(rest, 75)
    header = bytes([_bcd(minute), _bcd(second), _bcd(frame), 2])
    sub = bytes([file_no, channel, submode, coding]) * 2
    if submode & 0x20:
        payload = user.ljust(2324, b"\x00")[:2324] + b"\x00" * 4
    else:
        payload = user.ljust(2048, b"\x00")[:2048] + b"\x00" * 4 + b"\x00" * 276
    sector = SYNC + header + sub + payload
    assert len(sector) == 2352
    return sector


def iso_to_mode2_raw(iso: bytes, form2_ranges: List[Tuple[int, int, int]] = ()) -> bytes:
    """Converte ISO 2048 em MODE2/2352 (EDC/ECC zerados).

    ``form2_ranges``: (lba_inicial, quantidade, submode) marcados como Form2.
    """
    sectors = len(iso) // 2048
    special = {}
    for start, count, submode in form2_ranges:
        for lba in range(start, start + count):
            special[lba] = submode
    out = bytearray()
    for lba in range(sectors):
        user = iso[lba * 2048:(lba + 1) * 2048]
        submode = special.get(lba, 0x89 if lba == sectors - 1 else 0x08)
        out += raw_sector_mode2(lba, user, submode=submode, file_no=1 if lba in special else 0)
    return bytes(out)


def iso_to_mode1_raw(iso: bytes) -> bytes:
    out = bytearray()
    for lba in range(len(iso) // 2048):
        msf = lba + 150
        minute, rest = divmod(msf, 75 * 60)
        second, frame = divmod(rest, 75)
        out += SYNC + bytes([_bcd(minute), _bcd(second), _bcd(frame), 1]) + iso[lba * 2048:(lba + 1) * 2048] + bytes(288)
    return bytes(out)


def audio_sectors(count: int, seed: int = 7) -> bytes:
    rng = random.Random(seed)
    out = bytearray()
    for _ in range(count):
        sample = rng.getrandbits(16)
        out += struct.pack("<hh", (sample & 0x7FFF) - 0x4000, 0x1000) * (2352 // 4)
    return bytes(out)


def build_disc(workdir: Path, stem: str = "Test Racer") -> dict:
    """Cria CUE + 2 BINs (Redump-like): faixa 1 MODE2/2352, faixa 2 AUDIO com pregap de 2 s."""
    workdir.mkdir(parents=True, exist_ok=True)
    iso, locations = make_iso()
    xa_lba, xa_size = locations["/MUSIC/VOICE.XA;1"]
    xa_sectors = (xa_size + 2047) // 2048
    raw = iso_to_mode2_raw(iso, [(xa_lba, xa_sectors, 0x64)])  # Form2 + Audio + Real-time
    track1 = workdir / f"{stem} (Track 1).bin"
    track2 = workdir / f"{stem} (Track 2).bin"
    cue = workdir / f"{stem}.cue"
    track1.write_bytes(raw)
    audio = audio_sectors(300)
    track2.write_bytes(audio)
    cue.write_text(
        f'FILE "{track1.name}" BINARY\r\n'
        "  TRACK 01 MODE2/2352\r\n"
        "    INDEX 01 00:00:00\r\n"
        f'FILE "{track2.name}" BINARY\r\n'
        "  TRACK 02 AUDIO\r\n"
        "    INDEX 00 00:00:00\r\n"
        "    INDEX 01 00:02:00\r\n",
        encoding="ascii",
        newline="",
    )
    return {
        "iso": iso,
        "locations": locations,
        "raw": raw,
        "cue": cue,
        "track1": track1,
        "track2": track2,
        "audio": audio,
        "data_sectors": len(iso) // 2048,
        "xa": (xa_lba, xa_sectors),
    }


def make_zip(path: Path, members: Dict[str, bytes]) -> Path:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in members.items():
            archive.writestr(name, data)
    return path


def make_7z(path: Path, members: Dict[str, Path]) -> Path:
    import py7zr

    with py7zr.SevenZipFile(path, "w") as archive:
        for arcname, source in members.items():
            archive.write(source, arcname)
    return path


def build_original(tmp: Path) -> dict:
    """Monta 'Disney_Pixar Test Racer.zip.7z' contendo um .zip com CUE/BINs."""
    staging = tmp / "staging"
    disc = build_disc(staging)
    sbi = b"SBI\x00" + bytes(16)  # arquivo de subcanal FALSO (somente para testar o registro)
    zip_path = staging / "Disney_Pixar Test Racer.zip"
    make_zip(
        zip_path,
        {
            disc["cue"].name: disc["cue"].read_bytes(),
            disc["track1"].name: disc["track1"].read_bytes(),
            disc["track2"].name: disc["track2"].read_bytes(),
            "Test Racer.sbi": sbi,
            "Leia-me ção.txt": "Arquivo sintético de teste — não é do jogo.\n".encode("utf-8"),
        },
    )
    originals = tmp / "originais"
    originals.mkdir(parents=True, exist_ok=True)
    seven = originals / "Disney_Pixar Test Racer.zip.7z"
    make_7z(seven, {zip_path.name: zip_path})
    disc["zip"] = zip_path
    disc["original"] = seven
    return disc


def git_env(home: Path) -> Dict[str, str]:
    """Ambiente git isolado (sem configurações globais/sistema do usuário)."""
    env = dict(os.environ)
    home.mkdir(parents=True, exist_ok=True)
    empty = home / "gitconfig-vazio"
    empty.write_text("", encoding="utf-8")
    env.update(
        {
            "HOME": str(home),
            "GIT_CONFIG_GLOBAL": str(empty),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_AUTHOR_NAME": "Teste",
            "GIT_AUTHOR_EMAIL": "teste@example.invalid",
            "GIT_COMMITTER_NAME": "Teste",
            "GIT_COMMITTER_EMAIL": "teste@example.invalid",
        }
    )
    return env
