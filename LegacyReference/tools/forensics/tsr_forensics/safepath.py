"""Proteção contra path traversal ("zip-slip") e nomes problemáticos.

Regras para nomes vindos de arquivos compactados, de CUE sheets e do ISO9660:

* rejeita byte nulo, caminho absoluto (``/x``, ``\\x``), UNC, letra de unidade
  (``C:``) e qualquer componente ``..``;
* links simbólicos/junções são rejeitados por quem chama (o nome sozinho não
  revela isso);
* cada componente é saneado para ser válido no Windows, Linux e macOS
  (caracteres ``<>:"|?*`` e de controle viram ``_``; pontos/espaços finais
  são removidos; nomes reservados do Windows como ``CON``, ``NUL .txt``,
  ``CONIN$`` ou ``COM¹`` recebem prefixo);
* o destino final é conferido com ``realpath``: precisa ficar dentro do
  diretório base, nenhum componente intermediário pode ser link simbólico e
  nenhum componente existente pode ser um "apelido" de outro nome (ex.: nome
  curto 8.3 do Windows);
* ``NameAllocator`` evita colisões de destino: maiúsculas/minúsculas,
  normalização Unicode (NFC/NFD, relevante no macOS), arquivo versus
  diretório com o mesmo nome e nomes reservados (ex.: a pasta
  ``<arquivo>.extracted`` de um compactado aninhado).

Nomes não-ASCII e com espaços são preservados.
"""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .fsutil import fs, name_key as _name_key, strip_long_prefix

_DRIVE_RE = re.compile(r"^[A-Za-z]:")
_INVALID_CHARS_RE = re.compile(r'[<>:"|?*\x00-\x1f]')
# Nomes de dispositivo do Windows. Fonte: CPython 3.13, ``ntpath.isreserved``
# (CON, PRN, AUX, NUL, CONIN$, CONOUT$, COM1-9, LPT1-9 e COM/LPT com os
# dígitos sobrescritos ¹ ² ³). COM0/LPT0 entram por precaução: o único efeito
# é acrescentar um prefixo ao nome (o ajuste é registrado no manifesto).
_DEVICE_DIGITS = "0123456789\u00b9\u00b2\u00b3"
_WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$",
    *(f"COM{d}" for d in _DEVICE_DIGITS),
    *(f"LPT{d}" for d in _DEVICE_DIGITS),
}
_MAX_COMPONENT = 200


class UnsafePath(Exception):
    """Nome de entrada recusado por risco de escrita fora do destino."""

    def __init__(self, name: str, reason: str):
        super().__init__(f"{reason}: {name!r}")
        self.name = name
        self.reason = reason


def check_member_name(name: str) -> List[str]:
    """Valida o nome de uma entrada e devolve seus componentes (ainda não saneados).

    Levanta ``UnsafePath`` se o nome puder escapar do diretório de destino.
    """
    if not isinstance(name, str):
        raise UnsafePath(repr(name), "nome não textual")
    if "\x00" in name:
        raise UnsafePath(name, "nome contém byte nulo")
    normalized = name.replace("\\", "/")
    if normalized.startswith("/"):
        raise UnsafePath(name, "caminho absoluto")
    if _DRIVE_RE.match(normalized):
        raise UnsafePath(name, "letra de unidade (caminho absoluto do Windows)")
    parts = [part for part in normalized.split("/") if part not in ("", ".")]
    if any(part == ".." for part in parts):
        raise UnsafePath(name, "componente '..' (path traversal)")
    if not parts:
        raise UnsafePath(name, "nome vazio")
    for part in parts:
        if _DRIVE_RE.match(part):
            raise UnsafePath(name, "letra de unidade em componente intermediário")
    return parts


def sanitize_component(part: str) -> Tuple[str, bool]:
    """Devolve ``(componente_saneado, alterado?)``."""
    original = part
    cleaned = _INVALID_CHARS_RE.sub("_", part)
    cleaned = cleaned.rstrip(" .")
    if not cleaned:
        cleaned = "_"
    # Como em ``ntpath.isreserved``: o Windows ignora espaços antes da extensão
    # ("NUL .txt" também é o dispositivo NUL).
    stem = cleaned.partition(".")[0].rstrip(" ").upper()
    if stem in _WINDOWS_RESERVED:
        cleaned = "_" + cleaned
    if len(cleaned) > _MAX_COMPONENT:
        digest = hashlib.sha256(cleaned.encode("utf-8", "surrogatepass")).hexdigest()[:10]
        root, ext = os.path.splitext(cleaned)
        ext = ext[:20]
        cleaned = root[: _MAX_COMPONENT - len(ext) - 12] + "~" + digest + ext
    return cleaned, cleaned != original


def sanitize_parts(parts: List[str]) -> Tuple[List[str], bool]:
    changed = False
    result = []
    for part in parts:
        clean, was_changed = sanitize_component(part)
        result.append(clean)
        changed = changed or was_changed
    return result, changed


def _real(path: Path) -> str:
    """``realpath`` com o prefixo de caminho longo do Windows (e sem ele no resultado)."""
    return strip_long_prefix(os.path.realpath(fs(path)))


def safe_join(base: Path, parts: List[str]) -> Path:
    """Junta ``parts`` (já saneados) a ``base`` garantindo que o resultado fique dentro de ``base``.

    Levanta ``UnsafePath`` se o destino escapar da base, passar por link
    simbólico/junção ou se algum componente existente for um apelido de outro
    nome (ex.: nome curto 8.3 do Windows, que faria a escrita cair em outro
    arquivo). Erros de sistema (``OSError``) ao inspecionar o destino também
    viram ``UnsafePath``, para que quem chama recuse só esta entrada.
    """
    base_abs = Path(os.path.abspath(os.fspath(base)))
    target = base_abs.joinpath(*parts)
    try:
        # Nenhum componente existente abaixo de base pode ser link simbólico
        # (ou junção no Windows): isso poderia redirecionar a escrita.
        current = base_abs
        for part in parts:
            current = current / part
            if os.path.islink(fs(current)) or _is_junction(current):
                raise UnsafePath("/".join(parts), "componente do destino é link simbólico/junção")
        real_base_raw = _real(base_abs)
        real_target_raw = _real(target)
    except OSError as exc:
        raise UnsafePath("/".join(parts), f"falha ao validar o destino ({type(exc).__name__})") from exc
    real_base = os.path.normcase(real_base_raw)
    real_target = os.path.normcase(real_target_raw)
    try:
        inside = os.path.commonpath([real_base, real_target]) == real_base
    except ValueError:
        inside = False
    if not inside or real_target == real_base:
        raise UnsafePath("/".join(parts), "destino resolve para fora do diretório de extração")
    # No Windows, ``realpath`` devolve o nome longo real de cada componente
    # existente; se ele diferir do planejado (além de maiúsculas/NFC), o nome
    # planejado é apelido de outro arquivo/pasta (ex.: "LONGNA~1.TXT").
    relative = os.path.relpath(real_target_raw, real_base_raw)
    if os.altsep:
        relative = relative.replace(os.altsep, os.sep)
    relative = relative.split(os.sep)
    if len(relative) != len(parts) or any(_name_key(a) != _name_key(b) for a, b in zip(relative, parts)):
        raise UnsafePath("/".join(parts), "destino é apelido de outro nome existente (ex.: nome curto 8.3)")
    return target


def _is_junction(path: Path) -> bool:
    checker = getattr(os.path, "isjunction", None)  # Python 3.12+
    if checker is None:
        return False
    try:
        return bool(checker(path))
    except OSError:
        return False


class NameAllocator:
    """Evita colisões de destino dentro de uma mesma árvore de extração.

    Trata como iguais nomes que diferem só por maiúsculas/minúsculas ou pela
    normalização Unicode (NFC/NFD), como no Windows e no macOS. Também evita:

    * arquivo e diretório com o mesmo caminho (ex.: entradas ``file`` e
      ``file/child.txt``): o componente que chega depois é renomeado com
      ``~N`` e o mapeamento é mantido para as entradas seguintes do mesmo
      diretório;
    * nomes reservados: com ``reserve_suffix`` (ex.: ``".extracted"``), o
      caminho ``<arquivo><sufixo>`` fica reservado para uso do kit (pasta de
      extração de um compactado aninhado) e nenhuma entrada pode ocupá-lo.
    """

    def __init__(self) -> None:
        self._kinds: Dict[str, str] = {}  # chave normalizada -> "file" | "dir" | "reserved"
        self._dirs: Dict[str, List[str]] = {}  # diretório de origem (chave) -> componentes alocados

    @staticmethod
    def _key(parts: List[str]) -> str:
        return "/".join(_name_key(p) for p in parts)

    def allocate(self, parts: List[str], source_name: str, reserve_suffix: Optional[str] = None) -> Tuple[List[str], bool]:
        """Devolve ``(parts_finais, renomeado?)``."""
        out: List[str] = []
        for depth in range(len(parts) - 1):
            source_key = self._key(parts[: depth + 1])
            mapped = self._dirs.get(source_key)
            if mapped is not None:
                out = list(mapped)
                continue
            component = parts[depth]
            candidate, counter = component, 2
            while self._kinds.get(self._key(out + [candidate]), "dir") != "dir":
                candidate = f"{component}~{counter}"
                counter += 1
            out = out + [candidate]
            self._kinds[self._key(out)] = "dir"
            self._dirs[source_key] = list(out)
        name = parts[-1]
        root, ext = os.path.splitext(name)
        candidate, counter = name, 2
        while True:
            taken = self._key(out + [candidate]) in self._kinds
            if not taken and reserve_suffix:
                taken = self._key(out + [candidate + reserve_suffix]) in self._kinds
            if not taken:
                break
            candidate = f"{root}~{counter}{ext}"
            counter += 1
        final = out + [candidate]
        self._kinds[self._key(final)] = "file"
        if reserve_suffix:
            self._kinds[self._key(out + [candidate + reserve_suffix])] = "reserved"
        return final, final != list(parts)
