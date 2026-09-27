"""Comparação opcional com um DAT XML do Redump FORNECIDO PELO USUÁRIO.

O kit não baixa nada da internet. O DAT (formato Logiqx: ``<datafile>``,
``<game>``, ``<rom name size crc md5 sha1>``) é lido localmente e os hashes
dos arquivos/faixas do inventário são comparados com as entradas ``<rom>``.

Segurança: DATs com declarações ``<!ENTITY`` são recusados (evita expansão de
entidades) e o arquivo é limitado a 256 MiB. Nenhum DTD externo é buscado.

Uma correspondência significa apenas "hashes iguais aos do DAT fornecido";
ela é registrada como tal e não substitui a verificação humana da origem do
DAT.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional

from .fsutil import open_readonly

MAX_DAT_BYTES = 256 * 1024 * 1024


class RedumpError(Exception):
    pass


def load_dat(path: Path) -> dict:
    with open_readonly(path) as handle:
        raw = handle.read(MAX_DAT_BYTES + 1)
    if len(raw) > MAX_DAT_BYTES:
        raise RedumpError("DAT maior que 256 MiB; recusado")
    if b"<!ENTITY" in raw.upper():
        raise RedumpError("DAT contém declarações <!ENTITY; recusado por segurança")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise RedumpError(f"XML inválido: {exc}") from exc
    header = {}
    head = root.find("header")
    if head is not None:
        for field in ("name", "description", "version", "date", "author", "homepage", "url"):
            node = head.find(field)
            if node is not None and node.text:
                header[field] = node.text.strip()
    roms: List[dict] = []
    for game in root.iter("game"):
        game_name = game.get("name", "")
        for rom in game.iter("rom"):
            size = rom.get("size")
            roms.append(
                {
                    "jogo": game_name,
                    "rom": rom.get("name", ""),
                    "size": int(size) if size and size.isdigit() else None,
                    "crc32": (rom.get("crc") or "").lower() or None,
                    "md5": (rom.get("md5") or "").lower() or None,
                    "sha1": (rom.get("sha1") or "").lower() or None,
                }
            )
    return {"cabecalho": header, "roms": roms}


def match_items(items: List[dict], dat: dict) -> dict:
    """``items``: dicts com ``caminho_logico``, ``tamanho``, ``crc32``, ``md5``, ``sha1``."""
    by_sha1: Dict[str, List[dict]] = {}
    by_md5: Dict[str, List[dict]] = {}
    by_crc_size: Dict[tuple, List[dict]] = {}
    for rom in dat["roms"]:
        if rom["sha1"]:
            by_sha1.setdefault(rom["sha1"], []).append(rom)
        if rom["md5"]:
            by_md5.setdefault(rom["md5"], []).append(rom)
        if rom["crc32"] and rom["size"] is not None:
            by_crc_size.setdefault((rom["crc32"], rom["size"]), []).append(rom)
    matches = []
    matched_roms = set()
    for item in items:
        candidates: List[dict] = []
        for rom in by_sha1.get(str(item.get("sha1") or "").lower(), []):
            candidates.append(rom)
        for rom in by_md5.get(str(item.get("md5") or "").lower(), []):
            if rom not in candidates:
                candidates.append(rom)
        for rom in by_crc_size.get((str(item.get("crc32") or "").lower(), item.get("tamanho")), []):
            if rom not in candidates:
                candidates.append(rom)
        for rom in candidates:
            agree = {
                "tamanho": rom["size"] == item.get("tamanho") if rom["size"] is not None else None,
                "crc32": rom["crc32"] == str(item.get("crc32") or "").lower() if rom["crc32"] else None,
                "md5": rom["md5"] == str(item.get("md5") or "").lower() if rom["md5"] else None,
                "sha1": rom["sha1"] == str(item.get("sha1") or "").lower() if rom["sha1"] else None,
            }
            complete = all(v is not False for v in agree.values()) and any(v for v in agree.values())
            matches.append(
                {
                    "item": item.get("caminho_logico"),
                    "jogo_dat": rom["jogo"],
                    "rom_dat": rom["rom"],
                    "campos": agree,
                    "correspondencia_total": complete,
                }
            )
            if complete:
                matched_roms.add((rom["jogo"], rom["rom"]))
    games: Dict[str, dict] = {}
    for rom in dat["roms"]:
        info = games.setdefault(rom["jogo"], {"roms": 0, "roms_correspondentes": 0})
        info["roms"] += 1
        if (rom["jogo"], rom["rom"]) in matched_roms:
            info["roms_correspondentes"] += 1
    relevant = {name: info for name, info in games.items() if info["roms_correspondentes"]}
    return {
        "correspondencias": matches,
        "jogos_com_correspondencia": relevant,
        "observacao": (
            "Correspondência = hashes iguais aos do DAT fornecido pelo usuário. "
            "Arquivos .cue costumam diferir (nomes/terminações de linha) sem indicar alteração do disco."
        ),
    }


def item_from_row(row: dict) -> Optional[dict]:
    if row.get("sha1") is None and row.get("md5") is None:
        return None
    return {
        "caminho_logico": row.get("caminho_logico"),
        "tamanho": row.get("tamanho"),
        "crc32": row.get("crc32"),
        "md5": row.get("md5"),
        "sha1": row.get("sha1"),
    }
