"""Comando ``verify``: recalcula os hashes do original e compara com o registro.

Registro consultado (nesta ordem):

1. a REFERÊNCIA do log de cadeia de custódia para o mesmo nome de arquivo: o
   primeiro registro ``original.hash`` (resultado ``ok``), ou o último
   ``original.rebaseline`` explícito (``custody.original_history``). Rodar o
   ``intake`` de novo NÃO troca a referência; registros ``ok`` posteriores com
   hashes diferentes, sem rebaseline, são acusados como divergentes;
2. a seção ``original`` de ``forensic_inventory.json`` (se o log não tiver
   registro).

Também confere a cópia de trabalho (``<workdir>/original_copy/<nome>``), se
existir, e a integridade do encadeamento do log de custódia.

Códigos de saída: 0 = confere; 1 = ALTERADO (ou cópia/log divergente);
2 = sem registro para comparar / arquivo inexistente.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Optional

from . import report
from .custody import CustodyLog, original_history, verify_chain
from .fsutil import PathRedactor, fs, is_readonly
from .hashing import HASH_KEYS, hash_file
from .safepath import sanitize_component


def _registered(out_dir: Path, name: str) -> Optional[dict]:
    history = original_history(out_dir / report.CUSTODY_NAME, name)
    if history["referencia"] is not None:
        result = dict(history["referencia"])
        result["divergentes"] = history["divergentes"]
        result["rebaselines"] = history["rebaselines"]
        return result
    inventory_path = out_dir / report.JSON_NAME
    try:
        with open(fs(inventory_path), "r", encoding="utf-8") as handle:
            inventory = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None
    original = inventory.get("original") or {}
    if not original.get("hashes"):
        return None
    hashes = dict(original["hashes"])
    hashes["size"] = original.get("tamanho")
    return {
        "fonte": report.JSON_NAME,
        "timestamp_utc": inventory.get("gerado_em_utc"),
        "hashes": hashes,
        "nome_registrado": original.get("nome_arquivo"),
    }


def _compare(current: dict, expected: dict) -> List[str]:
    diffs = []
    if expected.get("size") is not None and current["size"] != expected["size"]:
        diffs.append(f"tamanho: registrado {expected['size']}, atual {current['size']}")
    for key in HASH_KEYS:
        if expected.get(key) and str(expected[key]).lower() != str(current[key]).lower():
            diffs.append(f"{key}: registrado {expected[key]}, atual {current[key]}")
    return diffs


def run_verify(original: Path, out_dir: Path, workdir: Path, command: List[str], record_full_paths: bool = False,
               repo_root: Optional[Path] = None) -> int:
    original = Path(os.path.abspath(original))
    redact = PathRedactor([("<workdir>", workdir), ("<out>", out_dir), ("<repo>", repo_root)], full=record_full_paths)
    redact.add_text_anchor("<externo>", original.parent)
    custody = CustodyLog(Path(out_dir) / report.CUSTODY_NAME, command=command, scrub=redact.scrub_obj)
    chain = verify_chain(Path(out_dir) / report.CUSTODY_NAME)
    if not os.path.isfile(fs(original)):
        print(f"[verify] ERRO: arquivo não encontrado: {original}")
        custody.record("verify", "erro", original=redact(original), motivo="arquivo não encontrado")
        return 2
    registered = _registered(Path(out_dir), original.name)
    if registered is None:
        print("[verify] ERRO: nenhum registro de hash encontrado (rode 'intake' antes).")
        custody.record("verify", "erro", original=redact(original), motivo="sem registro")
        return 2
    current = hash_file(original)
    diffs = _compare(current, registered["hashes"])
    name_note = None
    if registered.get("nome_registrado") and registered["nome_registrado"] != original.name:
        name_note = f"nome registrado ({registered['nome_registrado']}) difere do informado ({original.name})"

    copy_status = None
    copy_path = Path(workdir) / "original_copy" / sanitize_component(original.name)[0]
    if os.path.isfile(fs(copy_path)):
        copy_hashes = hash_file(copy_path)
        copy_diffs = _compare(copy_hashes, registered["hashes"])
        copy_status = {
            "caminho": redact(copy_path),
            "confere": not copy_diffs,
            "somente_leitura": is_readonly(copy_path),
            "diferencas": copy_diffs,
        }

    divergent = registered.get("divergentes") or []
    ok = not diffs and not divergent and (copy_status is None or copy_status["confere"]) and chain["ok"]
    print(f"[verify] Arquivo: {original.name}")
    print(f"[verify] Registro de referência: {registered['fonte']} ({registered.get('timestamp_utc')})")
    if registered.get("rebaselines"):
        print(f"[verify] Observação: a referência foi redefinida {registered['rebaselines']} vez(es) com --rebaseline (ver log).")
    if divergent:
        print(
            f"[verify] REGISTROS DIVERGENTES: o log tem {len(divergent)} registro(s) 'ok' com hashes diferentes da "
            "referência, sem rebaseline explícito — a referência pode ter sido trocada. Investigue."
        )
        for item in divergent[:10]:
            print(f"[verify]   - {item.get('timestamp_utc')}: sha256 {item.get('sha256')}")
    for key in ("size",) + HASH_KEYS:
        print(f"[verify]   {key:7s} atual: {current[key]}")
    if name_note:
        print(f"[verify] Observação: {name_note}")
    if diffs:
        print("[verify] ALTERADO — diferenças em relação ao registro:")
        for line in diffs:
            print(f"[verify]   - {line}")
    else:
        print("[verify] Original CONFERE com o registro.")
    if copy_status is not None:
        print(
            f"[verify] Cópia de trabalho: {'confere' if copy_status['confere'] else 'DIVERGE'}; "
            f"somente leitura: {'sim' if copy_status['somente_leitura'] else 'NÃO'}"
        )
    print(f"[verify] Log de custódia: {chain['detalhe']} ({chain['registros']} registros)")
    custody.record(
        "verify",
        "ok" if ok else "erro",
        original=redact(original),
        confere=not diffs,
        diferencas=diffs,
        registro=registered["fonte"],
        registro_timestamp_utc=registered.get("timestamp_utc"),
        registros_divergentes=divergent,
        hashes_atuais=current,
        copia=copy_status,
        cadeia_custodia=chain,
        observacao=name_note,
    )
    return 0 if ok else 1
