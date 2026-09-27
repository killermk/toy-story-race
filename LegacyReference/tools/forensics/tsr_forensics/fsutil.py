"""Utilitários de sistema de arquivos multiplataforma (Windows/Linux/macOS)."""

from __future__ import annotations

import os
import re
import stat
import unicodedata
from pathlib import Path
from typing import Iterable, List, Optional, Tuple, Union

PathLike = Union[str, "os.PathLike[str]"]

IS_WINDOWS = os.name == "nt"
_LONG_PATH_THRESHOLD = 240


def fs(path: PathLike) -> str:
    """Converte um caminho em string para chamadas ao SO.

    No Windows, caminhos absolutos longos (>= 240 caracteres) recebem o
    prefixo ``\\\\?\\`` para contornar o limite MAX_PATH de 260 caracteres.
    Nos demais sistemas o caminho é devolvido sem alteração.
    """
    text = os.fspath(path)
    if IS_WINDOWS:
        text = os.path.abspath(text)
        if len(text) >= _LONG_PATH_THRESHOLD and not text.startswith("\\\\?\\"):
            if text.startswith("\\\\"):
                text = "\\\\?\\UNC\\" + text[2:]
            else:
                text = "\\\\?\\" + text
    return text


def strip_long_prefix(text: str) -> str:
    """Remove o prefixo de caminho longo do Windows (``\\\\?\\`` / ``\\\\?\\UNC\\``)."""
    if text.startswith("\\\\?\\UNC\\"):
        return "\\\\" + text[8:]
    if text.startswith("\\\\?\\"):
        return text[4:]
    return text


def name_key(name: str) -> str:
    """Chave de comparação de nomes: NFC + casefold (Windows/macOS não diferenciam)."""
    return unicodedata.normalize("NFC", name).casefold()


def is_alias(path: PathLike) -> bool:
    """True se ``path`` existe mas resolve para OUTRO nome de arquivo.

    Ex.: no Windows, ``LONGNA~1.TXT`` pode ser o nome curto 8.3 de
    ``LongName.txt``; gravar/apagar pelo nome curto atingiria o outro arquivo.
    Também vale para um link simbólico (resolve para o alvo). Comparação sem
    diferenciar maiúsculas nem normalização Unicode.
    """
    try:
        if not os.path.lexists(fs(path)):
            return False
        real = strip_long_prefix(os.path.realpath(fs(path)))
    except OSError:
        return False
    return name_key(os.path.basename(real)) != name_key(os.path.basename(os.fspath(path)))


def open_readonly(path: PathLike):
    """Abre um arquivo SOMENTE para leitura binária.

    No Linux tenta ``O_NOATIME`` (não atualiza o horário de acesso); se o
    sistema recusar (arquivo de outro usuário), abre normalmente.
    """
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    noatime = getattr(os, "O_NOATIME", 0)
    if noatime:
        try:
            fd = os.open(fs(path), flags | noatime)
        except OSError:
            pass
        else:
            return os.fdopen(fd, "rb")
    return open(fs(path), "rb")


def ensure_dir(path: PathLike) -> None:
    os.makedirs(fs(path), exist_ok=True)


def make_readonly(path: PathLike) -> None:
    mode = stat.S_IMODE(os.stat(fs(path)).st_mode)
    os.chmod(fs(path), mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))


def make_writable(path: PathLike) -> None:
    mode = stat.S_IMODE(os.stat(fs(path)).st_mode)
    os.chmod(fs(path), mode | stat.S_IWUSR)


def is_readonly(path: PathLike) -> bool:
    mode = os.stat(fs(path)).st_mode
    return not (mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))


def remove_quietly(path: PathLike) -> None:
    try:
        if os.path.lexists(fs(path)):
            try:
                os.remove(fs(path))
            except PermissionError:
                make_writable(path)
                os.remove(fs(path))
    except OSError:
        pass


def is_within(path: PathLike, base: PathLike) -> bool:
    """True se ``path`` está dentro de ``base`` (ou é igual), sem resolver links."""
    try:
        p = os.path.normcase(os.path.abspath(os.fspath(path)))
        b = os.path.normcase(os.path.abspath(os.fspath(base)))
        return os.path.commonpath([p, b]) == b
    except ValueError:  # unidades diferentes no Windows
        return False


def same_file(a: PathLike, b: PathLike) -> bool:
    """True se os dois caminhos designam o mesmo arquivo existente (ou o mesmo caminho real)."""
    try:
        return os.path.samefile(fs(a), fs(b))
    except OSError:
        ra = os.path.normcase(os.path.realpath(os.fspath(a)))
        rb = os.path.normcase(os.path.realpath(os.fspath(b)))
        return ra == rb


def write_text_atomic(path: PathLike, text: str, encoding: str = "utf-8") -> None:
    """Escreve texto com terminação LF (idêntica em todos os SOs) de forma atômica."""
    target = Path(path)
    ensure_dir(target.parent)
    tmp = target.with_name(target.name + ".tmp-tsr")
    try:
        with open(fs(tmp), "w", encoding=encoding, newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(fs(tmp), fs(target))
    finally:
        remove_quietly(tmp)


# Pastas de usuário em textos livres (mensagens de exceção). Forma Windows
# (com letra de unidade, também com barras duplicadas de ``repr``) e formas
# POSIX (sensíveis a maiúsculas: nomes ISO9660 são maiúsculos e não casam).
_USER_DIR_PATTERNS = [
    re.compile(r"(?i)\b[A-Z]:[\\/]+(?:Users|Documents and Settings)[\\/]+[^\\/'\"\s:*?<>|]+"),
    re.compile(r"(?<![\w.~])/(?:home|Users)/[^/'\"\s]+"),
]


def _is_root(path: str) -> bool:
    return os.path.dirname(path) == path


class PathRedactor:
    """Converte caminhos locais em rótulos que não expõem o computador do usuário.

    Os relatórios vão para um repositório PÚBLICO; por padrão, caminhos
    absolutos (que costumam conter o nome de usuário) são substituídos por
    âncoras como ``<workdir>/...``, ``<repo>/...`` ou ``<externo>/nome``.
    Com ``full=True`` (opção ``--record-full-paths``) grava o caminho completo.

    ``scrub(texto)`` faz o mesmo em TEXTO LIVRE (ex.: mensagens de exceção do
    sistema operacional, que trazem o caminho completo): substitui as âncoras
    conhecidas (inclusive nas formas ``\\\\?\\`` e com barras duplicadas de
    ``repr``), a pasta do usuário (``<home>``) e qualquer trecho com cara de
    pasta de usuário (``C:\\Users\\nome``, ``/home/nome``, ``/Users/nome``).
    """

    def __init__(self, anchors: Iterable[tuple], full: bool = False):
        pairs = []
        for label, base in anchors:
            if base is None:
                continue
            pairs.append((label, os.path.abspath(os.fspath(base))))
        # âncoras mais específicas (caminhos mais longos) primeiro
        self._anchors = sorted(pairs, key=lambda item: len(item[1]), reverse=True)
        self.full = full
        self._text_anchors: List[Tuple[str, str]] = [a for a in self._anchors if not _is_root(a[1])]
        home = os.path.expanduser("~")
        if home and home != "~":
            self.add_text_anchor("<home>", home)

    def add_text_anchor(self, label: str, base: Optional[PathLike]) -> None:
        """Âncora usada só na limpeza de texto livre (ex.: pasta do original)."""
        if base is None:
            return
        absolute = os.path.abspath(os.fspath(base))
        if _is_root(absolute):
            return
        self._text_anchors.append((label, absolute))
        self._text_anchors.sort(key=lambda item: len(item[1]), reverse=True)

    def __call__(self, path: Optional[PathLike]) -> Optional[str]:
        if path is None:
            return None
        absolute = os.path.abspath(os.fspath(path))
        if self.full:
            return absolute
        for label, base in self._anchors:
            if is_within(absolute, base):
                rel = os.path.relpath(absolute, base)
                if rel == ".":
                    return label
                return label + "/" + rel.replace(os.sep, "/")
        return "<externo>/" + os.path.basename(absolute)

    @staticmethod
    def _variants(base: str) -> List[str]:
        forms = {base}
        if "\\" in base:
            forms.add(base.replace("\\", "/"))
            forms.add(base.replace("\\", "\\\\"))  # repr() de caminho Windows
            forms.add("\\\\?\\" + base)
            forms.add(("\\\\?\\" + base).replace("\\", "\\\\"))
        return sorted(forms, key=len, reverse=True)

    def scrub(self, text, patterns: bool = True):
        """Remove caminhos locais de um texto livre (sem efeito com ``full=True``)."""
        if self.full or not isinstance(text, str) or not text:
            return text
        flags = re.IGNORECASE if os.name == "nt" else 0
        for label, base in self._text_anchors:
            for variant in self._variants(base):
                if flags or variant in text:
                    # Só casa o caminho inteiro (ex.: âncora "/a" não casa em "/abs/x").
                    pattern = r"(?<![\w.~-])" + re.escape(variant) + r"(?=$|[\\/'\"\s,;:)\]}])"
                    text = re.sub(pattern, lambda _m, lab=label: lab, text, flags=flags)
        if patterns:
            for pattern in _USER_DIR_PATTERNS:
                text = pattern.sub("<home>", text)
        return text

    def scrub_obj(self, value, patterns: bool = True):
        """Aplica ``scrub`` recursivamente a todas as strings de dicts/listas."""
        if self.full:
            return value
        if isinstance(value, str):
            return self.scrub(value, patterns)
        if isinstance(value, dict):
            return {key: self.scrub_obj(item, patterns) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [self.scrub_obj(item, patterns) for item in value]
        return value
