"""Leitura do SYSTEM.CNF de discos PlayStation.

Referência: psx-spx, "CDROM File Playstation EXE and SYSTEM.CNF":

    BOOT = cdrom:\\abcd_123.45;1 arg ;boot exe (drive:\\path\\name.ext;version)
    TCB = 4                         ;HEX (=4 decimal)   ;max number of threads
    EVENT = 10                      ;HEX (=16 decimal)  ;max number of events
    STACK = 801FFF00                ;HEX (=memtop-256)

psx-spx também descreve a convenção de nome ``XXXX_NNN.NN`` para o executável
de boot ("taken from the game code ... with the minus replaced by an
underscore") e observa que ela "seems to apply for all official licensed PSX
games". Por isso o código de produto derivado do nome é registrado como
DERIVADO e NÃO CONFIRMADO até ser comparado com a mídia/caixa.
"""

from __future__ import annotations

import re
from typing import Dict, Optional

_BOOT_RE = re.compile(
    r"^(?P<device>[A-Za-z0-9]+):(?P<path>[^\s;]*)(?:;(?P<version>\d+))?(?:\s+(?P<args>.*))?$"
)
_SERIAL_RE = re.compile(r"^(?P<prefix>[A-Z]{4})[_-](?P<a>\d{3})\.(?P<b>\d{2})$")
_KNOWN_KEYS = ("BOOT", "TCB", "EVENT", "STACK")


def _hex_value(text: Optional[str]) -> Optional[int]:
    if text is None:
        return None
    token = text.strip().split()[0] if text.strip() else ""
    try:
        return int(token, 16)
    except ValueError:
        return None


def parse_system_cnf(data: bytes) -> Dict[str, object]:
    text = data.decode("ascii", errors="replace")
    entries: Dict[str, str] = {}
    order = []
    ignored = []
    for raw_line in re.split(r"\r\n|\r|\n", text):
        line = raw_line.strip().rstrip("\x00").strip()
        if not line:
            continue
        if "=" not in line:
            ignored.append(line[:80])
            continue
        key, value = line.split("=", 1)
        key = key.strip().upper()
        value = value.strip()
        if key in entries:
            ignored.append(f"chave repetida: {key}")
            continue
        entries[key] = value
        order.append(key)

    result: Dict[str, object] = {
        "chaves": entries,
        "ordem": order,
        "linhas_ignoradas": ignored,
        "chaves_desconhecidas": [k for k in order if k not in _KNOWN_KEYS],
        "fonte": "psx-spx: CDROM File Playstation EXE and SYSTEM.CNF",
    }
    boot = entries.get("BOOT")
    result["BOOT"] = boot
    if boot is not None:
        match = _BOOT_RE.match(boot)
        if match:
            path = match.group("path")
            executable = re.split(r"[\\/]", path)[-1] if path else ""
            result.update(
                {
                    "boot_dispositivo": match.group("device"),
                    "boot_caminho": path,
                    "boot_versao": match.group("version"),
                    "boot_argumentos": match.group("args"),
                    "boot_executavel": executable,
                }
            )
            serial = _SERIAL_RE.match(executable.upper())
            if serial:
                result["codigo_produto_derivado"] = f"{serial.group('prefix')}-{serial.group('a')}{serial.group('b')}"
                result["codigo_produto_observacao"] = (
                    "Derivado do nome do executável de boot pela convenção XXXX_NNN.NN descrita em "
                    "psx-spx. NÃO CONFIRMADO como código oficial até comparação com a mídia/caixa."
                )
            else:
                result["codigo_produto_derivado"] = None
                result["codigo_produto_observacao"] = "nome do executável não segue o padrão XXXX_NNN.NN"
        else:
            result["boot_erro"] = "linha BOOT não segue o formato dispositivo:\\caminho;versão"
    for key in ("TCB", "EVENT", "STACK"):
        raw = entries.get(key)
        result[key] = raw
        result[f"{key}_hex_valor"] = _hex_value(raw)
    return result
