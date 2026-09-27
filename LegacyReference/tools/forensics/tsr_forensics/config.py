"""Configuração: limites de segurança e localização padrão de diretórios."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path

KIB = 1024
MIB = 1024 * KIB
GIB = 1024 * MIB

PACKAGE_DIR = Path(__file__).resolve().parent
FORENSICS_DIR = PACKAGE_DIR.parent


def find_repo_root(start: Path = PACKAGE_DIR) -> Path:
    """Detecta a raiz do repositório a partir da localização do pacote.

    O pacote vive em ``<repo>/LegacyReference/tools/forensics/tsr_forensics``;
    a raiz é o diretório pai de ``LegacyReference``. Se a estrutura não for
    encontrada (pacote copiado para outro lugar), procura um ``.git``; por
    fim, usa o diretório de trabalho atual.
    """
    for candidate in [start, *start.parents]:
        if candidate.name == "LegacyReference":
            return candidate.parent
    for candidate in [start, *start.parents]:
        if (candidate / ".git").exists():
            return candidate
    return Path.cwd()


def default_workdir(repo_root: Path) -> Path:
    return repo_root / "LegacyReference" / "_work"


def default_outdir(repo_root: Path) -> Path:
    return repo_root / "LegacyReference" / "inventory"


@dataclass
class Limits:
    """Limites anti-bomba e de recursão. Todos configuráveis pela CLI."""

    # Total de bytes que um intake pode escrever extraindo arquivos compactados.
    max_total_bytes: int = 16 * GIB
    # Tamanho máximo de UMA entrada extraída.
    max_entry_bytes: int = 8 * GIB
    # Razão máxima (descompactado / compactado) aceita...
    max_ratio: float = 200.0
    # ...aplicada apenas quando o descompactado é >= este tamanho (arquivos
    # pequenos muito compressíveis não representam risco).
    ratio_min_bytes: int = 64 * MIB
    # Número máximo de entradas por arquivo compactado.
    max_entries: int = 100_000
    # Profundidade máxima de arquivos compactados aninhados.
    max_depth: int = 4
    # Limites do leitor ISO9660.
    max_iso_entries: int = 200_000
    max_iso_dir_depth: int = 32
    # Bytes lidos de UM diretório ISO9660 (limite de segurança contra registros
    # com tamanho absurdo, ex.: 0xFFFFFFFF; o excesso é ignorado com aviso).
    max_iso_dir_bytes: int = 1 * MIB
    # Verificação cruzada com pycdlib: roda num processo separado com tempo e
    # memória limitados (o pycdlib não tem proteção própria contra laços).
    pycdlib_timeout_s: float = 120.0
    pycdlib_max_memory: int = 1 * GIB
    # Entropia exata até este tamanho; acima disso, por amostragem declarada.
    entropy_full_max_bytes: int = 64 * MIB

    def to_dict(self) -> dict:
        return asdict(self)


_SIZE_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*([kmgt]?)(i?b?)\s*$", re.IGNORECASE)
_SIZE_MULT = {"": 1, "k": KIB, "m": MIB, "g": GIB, "t": 1024 * GIB}


def parse_size(text: str) -> int:
    """Converte '16G', '500M', '4096', '1.5GiB' em bytes (base 1024)."""
    match = _SIZE_RE.match(str(text))
    if not match:
        raise ValueError(f"tamanho inválido: {text!r} (use ex.: 4096, 500M, 16G)")
    number, unit, _ = match.groups()
    value = float(number) * _SIZE_MULT[unit.lower()]
    if value < 0:
        raise ValueError(f"tamanho negativo: {text!r}")
    return int(value)
