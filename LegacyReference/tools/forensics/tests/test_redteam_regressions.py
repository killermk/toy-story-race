"""Testes de regressão dos achados do Red Team no kit forense.

Cada classe/teste cita o achado que cobre. Todas as fixtures são SINTÉTICAS e
geradas em diretório temporário (nada do jogo real, nenhum binário versionado).
"""

import contextlib
import io
import json
import os
import re
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import time
import unittest
import zipfile
from pathlib import Path
from unittest import mock

import tsr_test_fixtures as fx
from test_intake_e2e import load_inventory, run_cli
from tsr_forensics import safepath
from tsr_forensics.archives import Budget, extract_archive, list_archive, plan_extraction
from tsr_forensics.config import MIB, Limits
from tsr_forensics.cue import compute_layout, parse_cue_text
from tsr_forensics.custody import CustodyLog, read_records
from tsr_forensics.disc import DataTrackStream, layout_for_single_track, scan_track
from tsr_forensics.fsutil import PathRedactor, strip_long_prefix
from tsr_forensics.guard import hook_script, run_guard
from tsr_forensics.hashing import hash_file
from tsr_forensics.iso9660 import parse_iso, pycdlib_crosscheck
from tsr_forensics.safepath import NameAllocator, UnsafePath, safe_join, sanitize_component

GIT = shutil.which("git")
REPORTS = ("forensic_inventory.json", "forensic_inventory.csv", "FORENSIC_INVENTORY.generated.md", "custody_log.jsonl")


def _unlock(root: Path) -> None:
    for path in root.rglob("*"):
        try:
            os.chmod(path, stat.S_IWUSR | stat.S_IRUSR | stat.S_IXUSR)
        except OSError:
            pass


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def _report_texts(out: Path):
    """Todos os textos dos relatórios (JSON/JSONL decodificados, CSV/MD crus)."""
    for name in REPORTS:
        path = out / name
        if not path.is_file():
            continue
        raw = path.read_text(encoding="utf-8-sig")
        if name.endswith(".json"):
            yield from _strings(json.loads(raw))
        elif name.endswith(".jsonl"):
            for line in raw.splitlines():
                if line.strip():
                    yield from _strings(json.loads(line))
        else:
            yield raw


def _loop_iso(huge_dir_size: bool = False) -> bytes:
    """ISO sintético cujo registro do diretório DATA aponta para a própria raiz (laço)
    ou (``huge_dir_size``) declara tamanho 0xFFFFFFFF."""
    iso, _ = fx.make_iso()
    data = bytearray(iso)
    root_lba = struct.unpack_from("<I", data, 16 * 2048 + 0x9C + 2)[0]
    base = root_lba * 2048
    offset = 0
    while data[base + offset]:
        length = data[base + offset]
        name_len = data[base + offset + 32]
        if bytes(data[base + offset + 33:base + offset + 33 + name_len]) == b"DATA":
            if huge_dir_size:
                struct.pack_into("<I", data, base + offset + 10, 0xFFFFFFFF)
                struct.pack_into(">I", data, base + offset + 14, 0xFFFFFFFF)
            else:
                struct.pack_into("<I", data, base + offset + 2, root_lba)
                struct.pack_into(">I", data, base + offset + 6, root_lba)
            return bytes(data)
        offset += length
    raise AssertionError("registro DATA não encontrado")


def _zip_with_method(path: Path, name: str, payload: bytes, method: int) -> Path:
    """ZIP com a entrada gravada 'stored' e o código de método trocado (ex.: 9 = Deflate64)."""
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr(name, payload)
    data = bytearray(path.read_bytes())
    for signature, offset in ((b"PK\x03\x04", 8), (b"PK\x01\x02", 10)):
        position = data.find(signature)
        assert position >= 0
        struct.pack_into("<H", data, position + offset, method)
    path.write_bytes(bytes(data))
    return path


class _TmpCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.originals = self.tmp / "originais"
        self.originals.mkdir()

    def tearDown(self):
        _unlock(self.tmp)
        self._tmp.cleanup()

    def intake(self, original, *extra, work=None, out=None):
        work = work or self.tmp / "work"
        out = out or self.tmp / "out"
        code, stdout, stderr = run_cli("intake", "--original", original, "--workdir", work, "--out", out, *extra)
        return code, stdout + stderr

    def assert_no_local_paths(self, out: Path):
        needles = {str(self.tmp)}
        for text in _report_texts(out):
            for needle in needles:
                self.assertNotIn(needle, text)


# --------------------------------------------------------------------------- achado ALTO
class RebaselineTests(_TmpCase):
    """Alto: rodar o intake de novo com o original alterado NÃO troca a referência nem apaga a cópia."""

    def setUp(self):
        super().setUp()
        self.original = fx.make_zip(self.originals / "Disney_Pixar Test Racer.zip", {"leia.txt": b"conteudo sintetico\n"})
        self.work, self.out = self.tmp / "work", self.tmp / "out"
        self.copy = self.work / "original_copy" / self.original.name

    def verify(self, out=None):
        code, stdout, _ = run_cli("verify", "--original", self.original, "--workdir", self.work, "--out", out or self.out)
        return code, stdout

    def test_changed_original_blocks_and_rebaseline_preserves_old_copy(self):
        code, output = self.intake(self.original)
        self.assertEqual(code, 0, output)
        first_hash = hash_file(self.original)
        inventory_before = (self.out / "forensic_inventory.json").read_bytes()
        with open(self.original, "ab") as handle:
            handle.write(b"X")
        self.assertEqual(self.verify()[0], 1)

        code, output = self.intake(self.original)
        self.assertEqual(code, 3, output)
        self.assertIn("NÃO CONFERE COM O REGISTRO", output)
        self.assertEqual(hash_file(self.copy), first_hash, "a cópia íntegra não pode ser substituída")
        self.assertEqual((self.out / "forensic_inventory.json").read_bytes(), inventory_before)
        steps = [r["step"] for r in read_records(self.out / "custody_log.jsonl")]
        self.assertIn("original.divergente", steps)
        code, stdout = self.verify()
        self.assertEqual(code, 1, stdout)
        self.assertIn("ALTERADO", stdout)

        code, output = self.intake(self.original, "--rebaseline")
        self.assertEqual(code, 0, output)
        kept = list((self.work / "original_copy" / "substituidas").iterdir())
        self.assertEqual(len(kept), 1)
        self.assertEqual(hash_file(kept[0]), first_hash)
        self.assertEqual(hash_file(self.copy), hash_file(self.original))
        records = read_records(self.out / "custody_log.jsonl")
        self.assertIn("original.rebaseline", [r["step"] for r in records])
        code, stdout = self.verify()
        self.assertEqual(code, 0, stdout)
        self.assertIn("redefinida 1 vez", stdout)

    def test_verify_flags_divergent_ok_records(self):
        """Logs antigos (ou editados) com dois 'ok' diferentes sem rebaseline: verify acusa."""
        self.out.mkdir()
        log = CustodyLog(self.out / "custody_log.jsonl", ["teste"])
        current = hash_file(self.original)
        other = dict(current, sha256="0" * 64, md5="0" * 32, sha1="0" * 40, crc32="00000000")
        log.record("original.hash", "ok", arquivo=self.original.name, hashes=other)
        log.record("original.hash", "ok", arquivo=self.original.name, hashes=current)
        code, stdout = self.verify()
        self.assertEqual(code, 1, stdout)
        self.assertIn("REGISTROS DIVERGENTES", stdout)

    def test_corrupted_copy_is_preserved_and_reported(self):
        self.assertEqual(self.intake(self.original)[0], 0)
        os.chmod(self.copy, stat.S_IWUSR | stat.S_IRUSR)
        with open(self.copy, "ab") as handle:
            handle.write(b"corrompido")
        corrupted = hash_file(self.copy)
        code, output = self.intake(self.original)
        self.assertEqual(code, 1, output)
        inventory = load_inventory(self.out)
        self.assertTrue(any("cópia de trabalho estava ALTERADA" in e for e in inventory["erros"]))
        kept = list((self.work / "original_copy" / "substituidas").iterdir())
        self.assertEqual([hash_file(k)["sha256"] for k in kept], [corrupted["sha256"]])
        self.assertEqual(hash_file(self.copy), hash_file(self.original))

    def test_divergent_copy_without_registry_blocks(self):
        self.assertEqual(self.intake(self.original)[0], 0)
        os.chmod(self.copy, stat.S_IWUSR | stat.S_IRUSR)
        with open(self.copy, "ab") as handle:
            handle.write(b"?")
        code, output = self.intake(self.original, out=self.tmp / "out_novo")
        self.assertEqual(code, 3, output)
        self.assertIn("não é possível saber", output)


# --------------------------------------------------------------------------- achados MÉDIOS
class PycdlibIsolationTests(_TmpCase):
    """Médio: laço de diretório não trava o pycdlib nem esgota a memória; diretório com tamanho 0xFFFFFFFF."""

    def test_intake_with_directory_loop_finishes(self):
        original = self.originals / "loop.iso"
        original.write_bytes(_loop_iso())
        kit = Path(fx.KIT_DIR)
        command = [sys.executable, "-m", "tsr_forensics", "intake", "--original", str(original),
                   "--workdir", str(self.tmp / "work"), "--out", str(self.tmp / "out")]
        started = time.monotonic()
        proc = subprocess.run(command, cwd=kit, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
        self.assertLess(time.monotonic() - started, 300)
        self.assertIn(proc.returncode, (0, 1), proc.stderr.decode("utf-8", "replace"))
        disc = load_inventory(self.tmp / "out")["discos"][0]
        self.assertEqual(disc["iso9660"]["verificacao_pycdlib"]["status"], "nao_executada")
        self.assertIn("laco_de_diretorio", [a["tipo"] for a in disc["iso9660"]["anomalias"]])

    def _loop_stream(self):
        path = self.tmp / "loop.iso"
        path.write_bytes(_loop_iso())
        stream = DataTrackStream(path, 0, 2048, 0, 0, path.stat().st_size // 2048)
        self.addCleanup(stream.close)
        return stream

    def test_isolated_pycdlib_is_killed_by_memory_or_time_limit(self):
        stream = self._loop_stream()
        entries = parse_iso(stream)["entries"]
        started = time.monotonic()
        result = pycdlib_crosscheck(stream, entries, Limits(pycdlib_timeout_s=60, pycdlib_max_memory=128 * MIB))
        self.assertIn(result["status"], ("memoria_excedida", "tempo_esgotado"), result)
        self.assertLess(time.monotonic() - started, 90)
        result = pycdlib_crosscheck(stream, entries, Limits(pycdlib_timeout_s=1, pycdlib_max_memory=64 * 1024 * MIB))
        self.assertEqual(result["status"], "tempo_esgotado", result)

    def test_huge_directory_size_is_bounded(self):
        path = self.tmp / "grande.iso"
        path.write_bytes(_loop_iso(huge_dir_size=True))
        stream = DataTrackStream(path, 0, 2048, 0, 0, path.stat().st_size // 2048)
        self.addCleanup(stream.close)
        sizes = []
        original_read = stream.read

        def spy(n=-1):
            sizes.append(n)
            return original_read(n)

        stream.read = spy
        parsed = parse_iso(stream)
        self.assertIn("diretorio_grande", [a["tipo"] for a in parsed["anomalias"]])
        self.assertLessEqual(max(sizes), 2048)


class PathLeakTests(_TmpCase):
    """Médio: caminhos absolutos locais não vazam para o log de custódia nem para os relatórios."""

    def test_missing_original_is_logged_without_local_path(self):
        missing = self.tmp / "ro" / "Disney_Pixar Test Racer.zip.7z"
        code, output = self.intake(missing)
        self.assertEqual(code, 2, output)
        records = read_records(self.tmp / "out" / "custody_log.jsonl")
        self.assertIn("intake.abortado", [r["step"] for r in records])
        self.assert_no_local_paths(self.tmp / "out")

    def test_os_error_text_is_scrubbed(self):
        original = fx.make_zip(self.originals / "leak.zip", {"ok/bom.txt": b"legitimo"})
        blocker = self.tmp / "work" / "extracted" / "leak.zip" / "ok"
        blocker.parent.mkdir(parents=True)
        blocker.write_bytes(b"arquivo no lugar de uma pasta")
        code, output = self.intake(original)
        self.assertEqual(code, 1, output)
        errors = " ".join(load_inventory(self.tmp / "out")["erros"])
        self.assertIn("<workdir>", errors)
        self.assert_no_local_paths(self.tmp / "out")

    def test_scrub_windows_forms(self):
        redactor = PathRedactor([("<workdir>", self.tmp / "work")])
        text = redactor.scrub("[WinError 5] Acesso negado: 'C:\\\\Users\\\\fulano\\\\x' e C:\\Users\\fulano\\y e /home/fulano/z")
        self.assertNotIn("fulano", text)
        self.assertEqual(redactor.scrub("/DATA/USERS/X;1 e /abs/evil2.txt"), "/DATA/USERS/X;1 e /abs/evil2.txt")


class ZipRatioTests(_TmpCase):
    """Médio: a razão de compressão total vale para ZIP; dividir em entradas pequenas não contorna."""

    def _split_bomb(self) -> Path:
        return fx.make_zip(self.originals / "bomb_split.zip", {f"z{i:02d}.bin": bytes(900 * 1024) for i in range(20)})

    def test_split_zip_bomb_refused(self):
        code, output = self.intake(self._split_bomb(), "--ratio-min-bytes", "1M", "--max-ratio", "50")
        self.assertEqual(code, 1, output)
        errors = " ".join(load_inventory(self.tmp / "out")["erros"])
        self.assertIn("razão de compressão total", errors)
        self.assertFalse(list((self.tmp / "work" / "extracted").rglob("z*.bin")))

    def test_ratio_checked_while_streaming_when_sizes_unknown(self):
        path = self._split_bomb()
        limits = Limits(max_ratio=50, ratio_min_bytes=MIB)
        budget = Budget(limits.max_total_bytes)
        listing = list_archive(path, "zip")
        for entry in listing["entradas"]:
            entry["tamanho"] = None  # cabeçalho que não declara/mente o tamanho
            entry["crc32"] = None
        plan = plan_extraction(listing, path.stat().st_size, self.tmp / "d", limits, budget)
        self.assertIsNone(plan["erro_fatal"])
        result = extract_archive(path, listing, plan["plano"], limits, budget)
        self.assertTrue(any("durante a descompactação" in e for e in result["erros"]), result["erros"])
        self.assertLess(len(result["extraidas"]), 20)


class SevenZipDuplicateTests(_TmpCase):
    """Médio: nomes duplicados num 7z não abortam a extração das entradas seguintes."""

    def test_duplicates_do_not_abort_following_entries(self):
        import py7zr

        original = self.originals / "dup.7z"
        with py7zr.SevenZipFile(original, "w") as archive:
            archive.writestr(b"one", "dup.txt")
            archive.writestr(b"two", "dup.txt")
            archive.writestr(b"real", "real.txt")
            archive.writestr("ç".encode("utf-8"), "Ünï code/ç ã.txt")
        code, output = self.intake(original)
        self.assertEqual(code, 0, output)
        dest = self.tmp / "work" / "extracted" / "dup.7z"
        self.assertEqual((dest / "real.txt").read_bytes(), b"real")
        self.assertEqual((dest / "Ünï code" / "ç ã.txt").read_bytes(), "ç".encode("utf-8"))
        self.assertEqual((dest / "dup.txt").read_bytes(), b"one")
        container = load_inventory(self.tmp / "out")["conteineres"][0]
        discarded = container["descartadas"]
        self.assertEqual(len(discarded), 1)
        self.assertEqual(discarded[0]["tamanho"], 3)
        self.assertEqual(discarded[0]["sha256"], __import__("hashlib").sha256(b"two").hexdigest())


class FailureLoggingTests(_TmpCase):
    """Médio: falhas fora do bloco de análise ficam no log; relatórios nunca ficam misturados."""

    def setUp(self):
        super().setUp()
        self.original = fx.make_zip(self.originals / "pequeno.zip", {"a.txt": b"texto sintetico\n"})

    def test_unexpected_copy_failure_is_logged_and_original_reverified(self):
        work = self.tmp / "work"
        work.mkdir()
        (work / "original_copy").write_bytes(b"arquivo no lugar da pasta")
        code, output = self.intake(self.original)
        self.assertEqual(code, 2, output)
        records = read_records(self.tmp / "out" / "custody_log.jsonl")
        steps = [r["step"] for r in records]
        self.assertIn("intake.abortado", steps)
        self.assertEqual(steps[-1], "original.reverificado")
        self.assertEqual(records[-1]["result"], "ok")
        self.assert_no_local_paths(self.tmp / "out")

    def test_workdir_that_is_a_file_is_refused_and_logged(self):
        not_dir = self.tmp / "um_arquivo"
        not_dir.write_bytes(b"x")
        code, output = self.intake(self.original, work=not_dir)
        self.assertEqual(code, 2, output)
        steps = [r["step"] for r in read_records(self.tmp / "out" / "custody_log.jsonl")]
        self.assertIn("intake.abortado", steps)

    def test_locked_csv_leaves_previous_reports_intact(self):
        out = self.tmp / "out"
        self.assertEqual(self.intake(self.original)[0], 0)
        before = {name: (out / name).read_bytes() for name in ("forensic_inventory.json", "FORENSIC_INVENTORY.generated.md")}
        (out / "forensic_inventory.csv").unlink()
        (out / "forensic_inventory.csv").mkdir()
        (out / "forensic_inventory.csv" / "trava.txt").write_text("simula arquivo travado", encoding="utf-8")
        code, output = self.intake(self.original)
        self.assertEqual(code, 2, output)
        for name, data in before.items():
            self.assertEqual((out / name).read_bytes(), data, f"{name} não deveria ter sido substituído")
        self.assertFalse([p.name for p in out.iterdir() if p.name.endswith(".tmp-tsr")])
        steps = [r["step"] for r in read_records(out / "custody_log.jsonl")]
        self.assertIn("relatorios.falha", steps)
        self.assertEqual(steps[-1], "intake.abortado")
        self.assertIn("original.reverificado", steps[-4:])


class IntegrityTests(_TmpCase):
    """Médio: imagem truncada/corrompida é ERRO (código 1) com destaque no relatório."""

    def test_truncated_cue_bin_is_an_integrity_error(self):
        disc = fx.build_disc(self.tmp / "disc")
        raw = disc["raw"]
        half = (len(raw) // 2352) // 2
        truncated = raw[: half * 2352 + 1000]
        cue = 'FILE "trunc.bin" BINARY\r\n  TRACK 01 MODE2/2352\r\n    INDEX 01 00:00:00\r\n'
        original = fx.make_zip(self.originals / "trunc.zip", {"trunc.cue": cue.encode("ascii"), "trunc.bin": truncated})
        code, output = self.intake(original)
        self.assertEqual(code, 1, output)
        inventory = load_inventory(self.tmp / "out")
        self.assertTrue(inventory["integridade"]["situacao"].startswith("ALERTA"))
        details = " ".join(p["detalhe"] for p in inventory["integridade"]["problemas"])
        self.assertIn("não é múltiplo", details)
        self.assertIn("ultrapassa o fim", details)
        md = (self.tmp / "out" / "FORENSIC_INVENTORY.generated.md").read_text(encoding="utf-8")
        self.assertIn("ALERTA DE INTEGRIDADE", md)


class CueMissingFileTests(_TmpCase):
    """Médio: faixas depois de um FILE ausente ficam com LBA null (NÃO CONFIRMADO), nunca deslocado."""

    CUE = (
        'FILE "t1.bin" BINARY\n  TRACK 01 MODE2/2352\n    INDEX 01 00:00:00\n'
        'FILE "t2.bin" BINARY\n  TRACK 02 AUDIO\n    INDEX 01 00:00:00\n'
        'FILE "t3.bin" BINARY\n  TRACK 03 AUDIO\n    INDEX 00 00:00:00\n    INDEX 01 00:02:00\n'
    )

    def test_compute_layout_unknown_after_missing_file(self):
        sheet = parse_cue_text(self.CUE)
        layouts = compute_layout(sheet, [Path("t1.bin"), None, Path("t3.bin")], [48 * 2352, None, 300 * 2352])
        self.assertEqual((layouts[0].abs_lba_begin, layouts[0].abs_lba_index01), (0, 0))
        self.assertIsNone(layouts[2].abs_lba_begin)
        self.assertIsNone(layouts[2].abs_lba_index01)
        self.assertTrue(any("NÃO CONFIRMADO" in w for w in layouts[2].warnings))
        full = compute_layout(sheet, [Path("t1.bin"), Path("t2.bin"), Path("t3.bin")], [48 * 2352, 450 * 2352, 300 * 2352])
        self.assertEqual((full[2].abs_lba_begin, full[2].abs_lba_index01), (498, 648))

    def test_intake_reports_null_lba(self):
        disc = fx.build_disc(self.tmp / "disc")
        original = fx.make_zip(
            self.originals / "mf.zip",
            {"mf.cue": self.CUE.encode("ascii"), "t1.bin": disc["raw"], "t3.bin": fx.audio_sectors(300)},
        )
        code, output = self.intake(original)
        self.assertEqual(code, 1, output)
        inventory = load_inventory(self.tmp / "out")
        tracks = inventory["discos"][0]["faixas"]
        self.assertEqual(tracks[0]["lba_inicio"], 0)
        self.assertIsNone(tracks[2]["lba_inicio"])
        self.assertIsNone(tracks[2]["lba_index01"])
        self.assertTrue(any("NÃO CONFIRMADO" in w for w in tracks[2]["avisos"]))
        self.assertTrue(any("t2.bin" in p["detalhe"] for p in inventory["integridade"]["problemas"]))
        rows = [r for r in inventory["arquivos"] if r["tipo"] == "faixa" and r["caminho_logico"].endswith("#faixa03")]
        self.assertIsNone(rows[0]["lba"])


# --------------------------------------------------------------------------- achados BAIXOS
class WindowsNamesTests(unittest.TestCase):
    """Baixo: nomes reservados do Windows (com espaço antes da extensão, CONIN$, COM¹...) e caminho longo."""

    def test_reserved_names(self):
        cases = {
            "nul .txt": "_nul .txt",
            "CONIN$": "_CONIN$",
            "conout$.log": "_conout$.log",
            "COM\u00b9.txt": "_COM\u00b9.txt",
            "LPT\u00b3": "_LPT\u00b3",
            "COM0": "_COM0",
            "console.txt": "console.txt",
        }
        for name, expected in cases.items():
            with self.subTest(name=name):
                self.assertEqual(sanitize_component(name)[0], expected)

    def test_long_prefix_helpers_and_long_paths(self):
        self.assertEqual(strip_long_prefix("\\\\?\\C:\\x\\y"), "C:\\x\\y")
        self.assertEqual(strip_long_prefix("\\\\?\\UNC\\srv\\share\\x"), "\\\\srv\\share\\x")
        self.assertEqual(strip_long_prefix("/tmp/x"), "/tmp/x")
        with tempfile.TemporaryDirectory() as tmp:
            parts = ["d" * 60] * 5 + ["arquivo.bin"]
            target = safe_join(Path(tmp), parts)
            self.assertGreater(len(str(target)), 260)

    def test_alias_detection(self):
        """Simula um nome curto 8.3: realpath devolve outro nome para o componente existente."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            real = safepath._real

            def fake_real(path):
                result = real(path)
                return result.replace("LONGNA~1.TXT", "LongName.txt")

            with mock.patch.object(safepath, "_real", side_effect=fake_real):
                with self.assertRaises(UnsafePath) as ctx:
                    safe_join(base, ["LONGNA~1.TXT"])
            self.assertIn("apelido", ctx.exception.reason)


class PublishAliasTests(_TmpCase):
    """Baixo: o apelido (8.3/link) que só aparece DEPOIS do planejamento é recusado na hora de gravar,
    sem apagar o arquivo real."""

    def test_alias_created_after_planning_is_not_overwritten(self):
        path = fx.make_zip(self.tmp / "a.zip", {"LONGNA~1.TXT": b"nome curto"})
        dest_dir = self.tmp / "dest"
        limits = Limits()
        budget = Budget(limits.max_total_bytes)
        listing = list_archive(path, "zip")
        plan = plan_extraction(listing, path.stat().st_size, dest_dir, limits, budget)
        self.assertEqual(len(plan["plano"]), 1)
        dest_dir.mkdir()
        real = dest_dir / "LongName.txt"
        real.write_bytes(b"arquivo real")
        try:
            os.symlink(real.name, dest_dir / "LONGNA~1.TXT")  # simula o nome curto gerado pelo Windows
        except (OSError, NotImplementedError):
            self.skipTest("sistema sem suporte a links simbólicos")
        result = extract_archive(path, listing, plan["plano"], limits, budget)
        self.assertTrue(any("apelido" in e for e in result["erros"]), result["erros"])
        self.assertEqual(real.read_bytes(), b"arquivo real")
        self.assertFalse(list(dest_dir.glob("*.tsrpart")))


class CollisionTests(_TmpCase):
    """Baixo: '<arquivo>.extracted', arquivo versus diretório e NFC/NFD."""

    def test_allocator(self):
        allocator = NameAllocator()
        self.assertEqual(allocator.allocate(["file"], "file")[0], ["file"])
        self.assertEqual(allocator.allocate(["file", "child.txt"], "file/child.txt")[0], ["file~2", "child.txt"])
        self.assertEqual(allocator.allocate(["file", "other.txt"], "file/other.txt")[0], ["file~2", "other.txt"])
        allocator = NameAllocator()
        self.assertEqual(allocator.allocate(["dir", "a.txt"], "dir/a.txt")[0], ["dir", "a.txt"])
        self.assertEqual(allocator.allocate(["dir"], "dir")[0], ["dir~2"])
        allocator = NameAllocator()
        allocator.allocate(["e\u0301.txt"], "nfd")
        final, renamed = allocator.allocate(["\u00e9.txt"], "nfc")
        self.assertTrue(renamed)
        allocator = NameAllocator()
        allocator.allocate(["X.zip"], "X.zip", reserve_suffix=".extracted")
        final, renamed = allocator.allocate(["X.zip.extracted", "foo.txt"], "X.zip.extracted/foo.txt", reserve_suffix=".extracted")
        self.assertEqual(final, ["X.zip.extracted~2", "foo.txt"])

    def test_nested_extracted_folder_and_file_dir_prefix(self):
        inner = io.BytesIO()
        with zipfile.ZipFile(inner, "w") as archive:
            archive.writestr("foo.txt", b"INNER")
        original = fx.make_zip(
            self.originals / "colisao.zip",
            {
                "X.zip": inner.getvalue(),
                "X.zip.extracted/foo.txt": b"OUTER",
                "file": b"arquivo",
                "file/child.txt": b"filho",
                "tiny.bin": b"12345678",
            },
        )
        code, output = self.intake(original)
        self.assertEqual(code, 0, output)
        inventory = load_inventory(self.tmp / "out")
        self.assertEqual(inventory["erros"], [])
        dest = self.tmp / "work" / "extracted" / "colisao.zip"
        self.assertEqual((dest / "X.zip.extracted" / "foo.txt").read_bytes(), b"INNER")
        self.assertEqual((dest / "X.zip.extracted~2" / "foo.txt").read_bytes(), b"OUTER")
        self.assertEqual((dest / "file").read_bytes(), b"arquivo")
        self.assertEqual((dest / "file~2" / "child.txt").read_bytes(), b"filho")
        tiny = [r for r in inventory["arquivos"] if r["caminho_logico"].endswith("tiny.bin")][0]
        self.assertTrue(tiny["primeiros_16_bytes_sao_o_arquivo_inteiro"])

    def test_disc_file_and_directory_with_same_name(self):
        import pycdlib

        iso = pycdlib.PyCdlib()
        iso.new(interchange_level=1, sys_ident="PLAYSTATION", vol_ident="T", xa=True)
        iso.add_directory("/FILE")
        iso.add_fp(io.BytesIO(b"conteudo"), 8, "/FILE.;1")
        iso.add_fp(io.BytesIO(b"filho"), 5, "/FILE/X.TXT;1")
        buffer = io.BytesIO()
        iso.write_fp(buffer)
        iso.close()
        original = self.originals / "colide.iso"
        original.write_bytes(buffer.getvalue())
        code, output = self.intake(original)
        inventory = load_inventory(self.tmp / "out")
        self.assertFalse([e for e in inventory["erros"] if "falha inesperada" in e], inventory["erros"])
        tree = {n["caminho"]: n for n in inventory["discos"][0]["arvore"]}
        self.assertTrue(tree["/FILE.;1"]["extraido"])
        self.assertTrue(tree["/FILE/X.TXT;1"]["extraido"])


class SolidSevenZipTests(_TmpCase):
    """Baixo: 7z sólido não atribui o tamanho do bloco inteiro ao 1º arquivo."""

    def test_solid_block_size_not_attributed_to_first_file(self):
        import py7zr

        path = self.tmp / "solido.7z"
        with py7zr.SevenZipFile(path, "w") as archive:
            for index in range(3):
                archive.writestr(bytes([index]) * 100000, f"f{index}.bin")
        entries = list_archive(path, "7z")["entradas"]
        self.assertEqual([e["tamanho_compactado"] for e in entries], [None, None, None])
        self.assertTrue(all("sólido" in e["tamanho_compactado_observacao"] for e in entries))
        self.assertIsNotNone(entries[0].get("tamanho_compactado_bloco"))


class StrCountingTests(_TmpCase):
    """Baixo: STR em setores Form2 e StType diferente de 8001h (psx-spx) são contados."""

    def test_form2_and_other_sttype(self):
        sectors = []
        mdec = struct.pack("<HH", 0x0160, 0x8001) + bytes(28)
        ff9_like = struct.pack("<HH", 0x0160, 0x0004) + bytes(28)
        for lba in range(3):
            sectors.append(fx.raw_sector_mode2(lba, mdec, submode=0x08))
        for lba in range(3, 8):
            sectors.append(fx.raw_sector_mode2(lba, ff9_like, submode=0x22))  # Form2 + Video
        path = self.tmp / "str.bin"
        path.write_bytes(b"".join(sectors))
        layout = layout_for_single_track(path, path.name, path.stat().st_size, "MODE2/2352")
        stats = scan_track(path, layout, keep_map=True)["estatisticas"]
        self.assertEqual(stats["str_mdec_0160_8001"], 3)
        self.assertEqual(stats["str_0160_outro_sttype"], 5)
        self.assertEqual(stats["str_0160_em_form2"], 5)
        self.assertEqual(stats["str_0160_sttype_valores"], {"0004": 5})


class ZipMethodTests(_TmpCase):
    """Baixo: ZIP Deflate64 (não suportado pela biblioteca padrão) vira ERRO explícito."""

    def test_deflate64_entry_is_an_error(self):
        original = _zip_with_method(self.originals / "d64.zip", "dados.txt", b"sintetico", 9)
        code, output = self.intake(original)
        self.assertEqual(code, 1, output)
        errors = " ".join(load_inventory(self.tmp / "out")["erros"])
        self.assertIn("deflate64", errors)
        self.assertIn("não suportado", errors)


class OneBadEntryTests(_TmpCase):
    """QA: um OSError ao conferir o destino de UMA entrada (ENOTDIR, nome longo demais...)
    não pode abortar a análise inteira ("falha inesperada ... relatório parcial")."""

    def test_blocked_destination_fails_only_that_entry(self):
        original = fx.make_zip(self.originals / "um_ruim.zip", {"ok/bom.txt": b"legitimo", "z_outro.txt": b"segue"})
        blocker = self.tmp / "work" / "extracted" / "um_ruim.zip" / "ok"
        blocker.parent.mkdir(parents=True)
        blocker.write_bytes(b"arquivo no lugar de uma pasta")
        code, output = self.intake(original)
        self.assertEqual(code, 1, output)
        inventory = load_inventory(self.tmp / "out")
        errors = " ".join(inventory["erros"])
        self.assertNotIn("falha inesperada", errors)
        status = {e["nome"]: e.get("status") for e in inventory["conteineres"][0]["entradas"]}
        self.assertEqual(status["ok/bom.txt"], "erro")
        self.assertEqual(status["z_outro.txt"], "extraida")
        self.assertEqual((self.tmp / "work" / "extracted" / "um_ruim.zip" / "z_outro.txt").read_bytes(), b"segue")
        self.assert_no_local_paths(self.tmp / "out")

    def _seven(self, name: str) -> Path:
        staging = self.tmp / "staging7z"
        staging.mkdir(exist_ok=True)
        members = {}
        for arcname, data in (("a_antes.txt", b"antes"), ("ok/bom.txt", b"legitimo"), ("z_outro.txt", b"segue")):
            source = staging / arcname.replace("/", "_")
            source.write_bytes(data)
            members[arcname] = source
        return fx.make_7z(self.originals / name, members)

    def test_7z_blocked_destination_fails_only_that_entry(self):
        original = self._seven("bloq.7z")
        blocker = self.tmp / "work" / "extracted" / "bloq.7z" / "ok"
        blocker.parent.mkdir(parents=True)
        blocker.write_bytes(b"arquivo no lugar de uma pasta")
        code, output = self.intake(original)
        self.assertEqual(code, 1, output)
        inventory = load_inventory(self.tmp / "out")
        status = {e["nome"]: e.get("status") for e in inventory["conteineres"][0]["entradas"]}
        self.assertEqual(status, {"a_antes.txt": "extraida", "ok/bom.txt": "erro", "z_outro.txt": "extraida"})
        self.assertEqual(len(inventory["erros"]), 1, inventory["erros"])
        self.assertIn("ok/bom.txt", inventory["erros"][0])
        self.assertEqual((self.tmp / "work" / "extracted" / "bloq.7z" / "z_outro.txt").read_bytes(), b"segue")
        self.assertFalse(inventory["conteineres"][0].get("descartadas"))  # não é "fora do plano"
        self.assert_no_local_paths(self.tmp / "out")

    def test_7z_publish_failure_fails_only_that_entry(self):
        original = self._seven("publica.7z")
        from tsr_forensics import archives

        real_is_alias = archives.is_alias

        def fake_is_alias(path):
            return os.path.basename(os.fspath(path)) == "bom.txt" or real_is_alias(path)

        with mock.patch("tsr_forensics.archives.is_alias", side_effect=fake_is_alias):
            code, output = self.intake(original)
        self.assertEqual(code, 1, output)
        inventory = load_inventory(self.tmp / "out")
        status = {e["nome"]: e.get("status") for e in inventory["conteineres"][0]["entradas"]}
        self.assertEqual(status, {"a_antes.txt": "extraida", "ok/bom.txt": "erro", "z_outro.txt": "extraida"})
        self.assertTrue(any("apelido" in e for e in inventory["erros"]), inventory["erros"])
        dest = self.tmp / "work" / "extracted" / "publica.7z"
        self.assertFalse((dest / "ok" / "bom.txt").exists())
        self.assertFalse(list(dest.rglob("*.tsrpart")))


class MarkdownControlCharsTests(_TmpCase):
    """QA: nomes corrompidos (ex.: dados de arquivo lidos como registros de diretório num ISO
    danificado) não podem levar CR/controle crus ao MD — CR sozinho é fim de linha no
    CommonMark e quebraria tabelas e listas."""

    def test_cell_and_code_are_single_line(self):
        from tsr_forensics import report

        for helper in (report.cell, report.code):
            rendered = helper("a\rb\r\nc\nd\x1de\x00f g")
            self.assertNotIn("\r", rendered)
            self.assertNotIn("\n", rendered)
            self.assertNotIn("\x1d", rendered)
            self.assertNotIn("\x00", rendered)
            self.assertNotIn(" ", rendered)
            self.assertIn("\\x1d", rendered)
        self.assertEqual(report.cell("tab\tok"), "tab\tok")

    def test_corrupted_iso_names_do_not_break_markdown(self):
        path = self.originals / "grande.iso"
        path.write_bytes(_loop_iso(huge_dir_size=True))
        code, output = self.intake(path)
        self.assertEqual(code, 1, output)  # diretórios além do fim da faixa = INTEGRIDADE
        md = (self.tmp / "out" / "FORENSIC_INVENTORY.generated.md").read_bytes()
        self.assertNotIn(b"\r", md)
        self.assertIsNone(re.search(rb"[\x00-\x08\x0b-\x1f\x7f]", md))


class LocationTests(_TmpCase):
    """Baixo (README): original em qualquer lugar da área de trabalho é recusado."""

    def test_original_in_workdir_root_refused(self):
        work = self.tmp / "work"
        work.mkdir()
        original = work / "a.zip"
        fx.make_zip(original, {"a.txt": b"x"})
        code, output = self.intake(original, work=work)
        self.assertEqual(code, 2, output)
        self.assertIn("área de trabalho", output)


@unittest.skipIf(GIT is None, "git não disponível")
class GitBasedTests(unittest.TestCase):
    """Baixo: guard (texto codificado, hashes de intakes anteriores, hook) e workdir não ignorado."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        self.env = fx.git_env(self.tmp / "home")
        self._old_env = dict(os.environ)
        os.environ.clear()
        os.environ.update(self.env)
        self.git("init", "-q")

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._old_env)
        _unlock(self.tmp)
        self._tmp.cleanup()

    def git(self, *args, check=True):
        return subprocess.run(["git", "-C", str(self.repo), *args], env=self.env, check=check,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def guard(self, **kwargs):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = run_guard(self.repo, **kwargs)
        return code, out.getvalue() + err.getvalue()

    def test_encoded_content_and_big_text(self):
        import base64

        (self.repo / "prosa.txt").write_text(("Texto comum com espaços e acentos: ação. " * 50000), encoding="utf-8")
        self.git("add", "prosa.txt")
        code, output = self.guard(staged=True)
        self.assertEqual(code, 0, output)
        (self.repo / "tim_b64.txt").write_text(base64.b64encode(fx.fake_tim()).decode("ascii"), encoding="ascii")
        (self.repo / "exe_hex.txt").write_text(fx.fake_psx_exe()[:256].hex(" "), encoding="ascii")
        (self.repo / "bigtext.txt").write_bytes(b"A" * (3 * MIB // 2))
        (self.repo / "sobra.bin.tsrpart").write_bytes(b"parcial")
        self.git("add", "tim_b64.txt", "exe_hex.txt", "bigtext.txt", "sobra.bin.tsrpart")
        code, output = self.guard(staged=True)
        self.assertEqual(code, 1, output)
        self.assertIn("tim_b64.txt: conteúdo base64 decodificado", output)
        self.assertIn("exe_hex.txt: conteúdo hexadecimal decodificado: assinatura PS-X EXE", output)
        self.assertIn("bigtext.txt: texto grande", output)
        self.assertIn("sobra.bin.tsrpart: extensão bloqueada", output)
        code, output = self.guard(staged=True, max_text=1000, allow=["tim_b64.txt", "exe_hex.txt", "bigtext.txt"])
        self.assertIn("prosa.txt: arquivo de texto grande", output)

    def test_hashes_from_custody_log_and_local_registry(self):
        import hashlib

        secret = self.repo / "copia.md"
        secret.write_text("conteúdo de um arquivo já inventariado\n", encoding="utf-8")
        other = self.repo / "outro.md"
        other.write_text("outro arquivo original de intake anterior\n", encoding="utf-8")
        self.git("add", "copia.md", "outro.md")
        inventory_dir = self.repo / "LegacyReference" / "inventory"
        inventory_dir.mkdir(parents=True)
        log = CustodyLog(inventory_dir / "custody_log.jsonl", ["teste"])
        data = secret.read_bytes()
        log.record("original.hash", "ok", arquivo="antigo.7z",
                   hashes={"size": len(data), "sha256": hashlib.sha256(data).hexdigest()})
        registry = self.repo / "LegacyReference" / "_work" / "protected_sha256.txt"
        registry.parent.mkdir(parents=True)
        registry.write_text("# comentario\n" + hashlib.sha256(other.read_bytes()).hexdigest() + "\n", encoding="utf-8")
        code, output = self.guard(staged=True)
        self.assertEqual(code, 1, output)
        self.assertIn("copia.md: SHA-256 consta", output)
        self.assertIn("outro.md: SHA-256 consta", output)

    def test_hook_checks_python_really_runs(self):
        script = hook_script(sys.executable, fx.KIT_DIR)
        self.assertIn("sys.version_info >= (3, 10)", script)
        self.assertIn("Microsoft Store", script)
        from tsr_forensics.guard import install_hook

        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(install_hook(self.repo, python=str(self.tmp / "nao-existe" / "python")), 0)
        fake_bin = self.tmp / "fakebin"
        fake_bin.mkdir()
        fake = fake_bin / "python3"
        fake.write_text("#!/bin/sh\nexit 9009\n", encoding="utf-8")
        fake.chmod(0o755)
        real_dir = str(Path(sys.executable).parent)
        env = dict(self.env)
        env["PATH"] = os.pathsep.join([str(fake_bin), real_dir, env.get("PATH", "")])
        if not (shutil.which("python", path=env["PATH"]) or shutil.which("py", path=env["PATH"])):
            self.skipTest("sem 'python' nem 'py' no PATH para o fallback")
        (self.repo / "leia.md").write_text("texto\n", encoding="utf-8")
        self.git("add", "leia.md")
        result = subprocess.run(["git", "-C", str(self.repo), "commit", "-q", "-m", "t"], env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", "replace"))

    def test_workdir_inside_repo_must_be_ignored(self):
        (self.repo / ".gitignore").write_text("_work/\n", encoding="utf-8")
        original = fx.make_zip(self.tmp / "pequeno.zip", {"a.txt": b"x"})
        with mock.patch("tsr_forensics.intake.find_repo_root", return_value=self.repo):
            code, stdout, stderr = run_cli("intake", "--original", original, "--workdir", self.repo / "visivel",
                                           "--out", self.tmp / "out1")
            self.assertEqual(code, 2, stdout + stderr)
            self.assertIn("NÃO é ignorada", stderr)
            self.assertFalse((self.repo / "visivel" / "original_copy").exists())
            code, stdout, stderr = run_cli("intake", "--original", original, "--workdir", self.repo / "_work",
                                           "--out", self.tmp / "out2")
            self.assertEqual(code, 0, stdout + stderr)


if __name__ == "__main__":
    unittest.main()
