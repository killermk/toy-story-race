"""Hashes (CRC32, MD5, SHA-1, SHA-256) em streaming e entropia de Shannon."""

from __future__ import annotations

import collections
import hashlib
import math
import zlib
from typing import BinaryIO, Callable, Dict, Optional, Tuple

from .fsutil import PathLike, open_readonly

CHUNK = 1 << 20  # 1 MiB
HASH_KEYS = ("crc32", "md5", "sha1", "sha256")

# Amostragem de entropia para arquivos grandes: blocos igualmente espaçados.
_SAMPLE_BLOCKS = 256
_SAMPLE_BLOCK_SIZE = 128 * 1024


def _md5():
    try:
        return hashlib.new("md5", usedforsecurity=False)  # type: ignore[call-arg]
    except TypeError:  # pragma: no cover - Pythons antigos
        return hashlib.md5()


def _sha1():
    try:
        return hashlib.new("sha1", usedforsecurity=False)  # type: ignore[call-arg]
    except TypeError:  # pragma: no cover
        return hashlib.sha1()


class MultiHasher:
    """Calcula tamanho, CRC32, MD5, SHA-1 e SHA-256 de uma só vez."""

    __slots__ = ("size", "_crc", "_md5", "_sha1", "_sha256")

    def __init__(self) -> None:
        self.size = 0
        self._crc = 0
        self._md5 = _md5()
        self._sha1 = _sha1()
        self._sha256 = hashlib.sha256()

    def update(self, data) -> None:
        self.size += len(data)
        self._crc = zlib.crc32(data, self._crc)
        self._md5.update(data)
        self._sha1.update(data)
        self._sha256.update(data)

    def result(self) -> Dict[str, object]:
        return {
            "size": self.size,
            "crc32": f"{self._crc & 0xFFFFFFFF:08x}",
            "md5": self._md5.hexdigest(),
            "sha1": self._sha1.hexdigest(),
            "sha256": self._sha256.hexdigest(),
        }


class ByteHistogram:
    """Histograma de bytes para entropia de Shannon (bits por byte, 0..8)."""

    def __init__(self) -> None:
        self.counts: collections.Counter = collections.Counter()
        self.total = 0

    def update(self, data) -> None:
        self.counts.update(bytes(data))
        self.total += len(data)

    def entropy(self) -> Optional[float]:
        if self.total == 0:
            return None
        total = float(self.total)
        value = 0.0
        for count in self.counts.values():
            p = count / total
            value -= p * math.log2(p)
        return round(value + 0.0, 4)


def hash_stream(
    stream: BinaryIO,
    length: Optional[int] = None,
    on_chunk: Optional[Callable[[bytes], None]] = None,
) -> Dict[str, object]:
    """Hash de ``length`` bytes (ou até EOF) a partir da posição atual."""
    hasher = MultiHasher()
    remaining = length
    while remaining is None or remaining > 0:
        want = CHUNK if remaining is None else min(CHUNK, remaining)
        data = stream.read(want)
        if not data:
            break
        hasher.update(data)
        if on_chunk is not None:
            on_chunk(data)
        if remaining is not None:
            remaining -= len(data)
    return hasher.result()


def hash_file(path: PathLike) -> Dict[str, object]:
    with open_readonly(path) as handle:
        return hash_stream(handle)


def hash_file_range(path: PathLike, offset: int, length: int) -> Dict[str, object]:
    with open_readonly(path) as handle:
        handle.seek(offset)
        result = hash_stream(handle, length)
    return result


def hash_and_entropy(path: PathLike, full_max_bytes: int) -> Tuple[Dict[str, object], dict]:
    """Calcula hashes e entropia de um arquivo em uma única leitura quando possível.

    Retorna ``(hashes, entropia)`` onde ``entropia`` é
    ``{"valor": float|None, "metodo": "completo"|"amostra"|"vazio", "bytes_analisados": int}``.
    Acima de ``full_max_bytes`` a entropia é calculada sobre uma amostra
    determinística (blocos igualmente espaçados) e isso fica declarado.
    """
    with open_readonly(path) as handle:
        handle.seek(0, 2)
        size = handle.tell()
        handle.seek(0)
        if size <= full_max_bytes:
            histogram = ByteHistogram()
            hashes = hash_stream(handle, on_chunk=histogram.update)
            if histogram.total == 0:
                return hashes, {"valor": None, "metodo": "vazio", "bytes_analisados": 0}
            return hashes, {
                "valor": histogram.entropy(),
                "metodo": "completo",
                "bytes_analisados": histogram.total,
            }
        hashes = hash_stream(handle)
        histogram = ByteHistogram()
        step = max(size // _SAMPLE_BLOCKS, _SAMPLE_BLOCK_SIZE)
        position = 0
        while position < size:
            handle.seek(position)
            data = handle.read(_SAMPLE_BLOCK_SIZE)
            if not data:
                break
            histogram.update(data)
            position += step
        return hashes, {
            "valor": histogram.entropy(),
            "metodo": "amostra",
            "bytes_analisados": histogram.total,
        }


def entropy_of_bytes(data: bytes) -> Optional[float]:
    histogram = ByteHistogram()
    histogram.update(data)
    return histogram.entropy()


def hashes_equal(a: Dict[str, object], b: Dict[str, object]) -> bool:
    """Compara tamanho e todos os hashes presentes em ambos."""
    if a.get("size") != b.get("size"):
        return False
    compared = 0
    for key in HASH_KEYS:
        if a.get(key) is not None and b.get(key) is not None:
            compared += 1
            if str(a[key]).lower() != str(b[key]).lower():
                return False
    return compared > 0
