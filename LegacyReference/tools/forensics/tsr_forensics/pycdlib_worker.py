"""Processo isolado da verificação cruzada com pycdlib.

Executado por ``iso9660.pycdlib_crosscheck`` como subprocesso, para que um
laço ou um consumo de memória descontrolado dentro do pycdlib (ex.: ISO com
diretório que aponta para si mesmo) não trave o intake nem a máquina.

Entrada (stdin, JSON UTF-8): parâmetros da visão lógica de 2048 bytes/setor
(``path``, ``begin_byte``, ``sector_size``, ``user_offset``, ``first_lba``,
``sectors``) e ``max_memory`` (bytes). Saída (stdout, JSON UTF-8):
``{"status": "ok", "arquivos": {CAMINHO: [lba, tamanho]}}`` ou
``{"status": "erro", "erro": "..."}``.

Limite de memória: um vigia (thread) mede a memória do próprio processo a
cada 0,1 s e encerra com o código ``MEMORY_EXIT`` ao passar do limite
(Linux: ``/proc/self/statm``; macOS: ``getrusage``; Windows:
``GetProcessMemoryInfo`` via ``ctypes``). No Linux também é aplicado
``RLIMIT_AS`` como barreira adicional. O tempo máximo é imposto pelo processo
pai (``subprocess.run(timeout=...)``).
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from typing import Callable, Optional

MEMORY_EXIT = 86


def _linux_rss() -> Optional[int]:
    try:
        with open("/proc/self/statm", "rb") as handle:
            fields = handle.read().split()
        return int(fields[1]) * os.sysconf("SC_PAGE_SIZE")
    except (OSError, ValueError, IndexError):
        return None


def _macos_peak_rss() -> Optional[int]:
    try:
        import resource

        return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)  # bytes no macOS
    except Exception:
        return None


def _windows_memory() -> Optional[int]:
    try:
        import ctypes
        from ctypes import wintypes

        class _Counters(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        query = getattr(kernel32, "K32GetProcessMemoryInfo", None)
        if query is None:
            query = ctypes.WinDLL("psapi").GetProcessMemoryInfo
        query.argtypes = [wintypes.HANDLE, ctypes.POINTER(_Counters), wintypes.DWORD]
        query.restype = wintypes.BOOL
        counters = _Counters()
        counters.cb = ctypes.sizeof(_Counters)
        if not query(kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            return None
        return max(int(counters.PagefileUsage), int(counters.WorkingSetSize))
    except Exception:
        return None


def memory_probe() -> Optional[Callable[[], Optional[int]]]:
    if sys.platform.startswith("linux"):
        return _linux_rss
    if sys.platform == "darwin":
        return _macos_peak_rss
    if os.name == "nt":
        return _windows_memory
    return None


def _start_watchdog(limit: int) -> None:
    probe = memory_probe()
    if probe is None or probe() is None:
        return

    def watch() -> None:
        while True:
            used = probe()
            if used is not None and used > limit:
                try:
                    sys.stderr.write(f"limite de memória excedido ({used} > {limit} bytes)\n")
                    sys.stderr.flush()
                finally:
                    os._exit(MEMORY_EXIT)
            time.sleep(0.1)

    threading.Thread(target=watch, name="tsr-memory-watchdog", daemon=True).start()


def _apply_address_space_limit(limit: int) -> None:
    if not sys.platform.startswith("linux"):
        return
    try:
        import resource

        ceiling = max(2 * limit, limit + (1 << 30))
        soft, hard = resource.getrlimit(resource.RLIMIT_AS)
        if hard != resource.RLIM_INFINITY:
            ceiling = min(ceiling, hard)
        resource.setrlimit(resource.RLIMIT_AS, (ceiling, hard))
    except Exception:
        pass


def _walk(stream) -> dict:
    import pycdlib

    iso = pycdlib.PyCdlib()
    try:
        iso.open_fp(stream)
    except Exception as exc:  # pycdlib pode recusar imagens atípicas
        return {"status": "erro", "erro": f"{type(exc).__name__}: {exc}"}
    files = {}
    try:
        for dirpath, _dirs, names in iso.walk(iso_path="/"):
            for name in names:
                full = (dirpath.rstrip("/") + "/" + name) if dirpath != "/" else "/" + name
                record = iso.get_record(iso_path=full)
                files[full.upper()] = [record.extent_location(), record.get_data_length()]
    except Exception as exc:
        return {"status": "erro", "erro": f"{type(exc).__name__}: {exc}"}
    finally:
        try:
            iso.close()
        except Exception:
            pass
    return {"status": "ok", "arquivos": files}


def main() -> int:
    params = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    limit = int(params.get("max_memory") or 0)
    if limit > 0:
        _apply_address_space_limit(limit)
        _start_watchdog(limit)
    from .disc import DataTrackStream

    try:
        stream = DataTrackStream(
            params["path"],
            params["begin_byte"],
            params["sector_size"],
            params["user_offset"],
            params["first_lba"],
            params["sectors"],
        )
    except OSError as exc:
        result = {"status": "erro", "erro": f"{type(exc).__name__}: {exc}"}
    else:
        try:
            result = _walk(stream)
        except MemoryError:
            result = {"status": "memoria_excedida", "erro": "MemoryError no pycdlib"}
        finally:
            stream.close()
    sys.stdout.buffer.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))
    sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
