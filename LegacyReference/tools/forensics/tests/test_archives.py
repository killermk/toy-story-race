import stat
import tempfile
import unittest
import zipfile
from pathlib import Path

import tsr_test_fixtures as fx
from tsr_forensics.archives import Budget, extract_archive, list_archive, plan_extraction
from tsr_forensics.config import MIB, Limits


def _evil_zip(path: Path) -> Path:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("ok/bom.txt", b"arquivo legitimo")
        archive.writestr(zipfile.ZipInfo("../evil.txt"), b"fora do destino")
        archive.writestr(zipfile.ZipInfo("/abs/evil2.txt"), b"absoluto")
        archive.writestr(zipfile.ZipInfo("C:/drive.txt"), b"unidade")
        archive.writestr(zipfile.ZipInfo("a\\..\\..\\b.txt"), b"barra invertida")
        link = zipfile.ZipInfo("link_para_fora")
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(link, "../../etc/passwd")
    with zipfile.ZipFile(path) as archive:  # garante que os nomes maliciosos foram gravados
        names = archive.namelist()
    assert "../evil.txt" in names and "/abs/evil2.txt" in names, names
    return path


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _run(self, path, fmt, limits=None, budget=None):
        limits = limits or Limits()
        budget = budget or Budget(limits.max_total_bytes)
        listing = list_archive(path, fmt)
        dest = self.tmp / "dest" / "x"
        plan = plan_extraction(listing, path.stat().st_size, dest, limits, budget)
        if plan["erro_fatal"]:
            return listing, plan, None, dest
        result = extract_archive(path, listing, plan["plano"], limits, budget)
        return listing, plan, result, dest

    def test_zip_slip_and_symlink_rejected(self):
        path = _evil_zip(self.tmp / "evil.zip")
        listing, plan, result, dest = self._run(path, "zip")
        rejected = {r["nome"]: r["motivo"] for r in plan["recusadas"]}
        self.assertIn("componente '..'", rejected["../evil.txt"])
        self.assertIn("caminho absoluto", rejected["/abs/evil2.txt"])
        self.assertIn("letra de unidade", rejected["C:/drive.txt"])
        self.assertIn("componente '..'", rejected["a\\..\\..\\b.txt"])
        self.assertIn("link simbólico", rejected["link_para_fora"])
        self.assertEqual([i["relativo"] for i in result["extraidas"]], ["ok/bom.txt"])
        self.assertEqual((dest / "ok" / "bom.txt").read_bytes(), b"arquivo legitimo")
        self.assertFalse((self.tmp / "dest" / "evil.txt").exists())
        self.assertFalse((self.tmp / "evil.txt").exists())
        self.assertFalse(Path("/abs/evil2.txt").exists())
        created = sorted(p.relative_to(self.tmp).as_posix() for p in self.tmp.rglob("*") if p.is_file())
        self.assertEqual(created, ["dest/x/ok/bom.txt", "evil.zip"])

    def test_bomb_ratio_and_total_limits(self):
        path = self.tmp / "bomba.zip"
        fx.make_zip(path, {"zeros.bin": bytes(20 * MIB)})
        limits = Limits(max_ratio=10, ratio_min_bytes=MIB)
        _, plan, result, dest = self._run(path, "zip", limits)
        self.assertIsNone(result)
        self.assertIn("razão de compressão", plan["erro_fatal"])
        self.assertFalse(dest.exists())
        limits = Limits(max_total_bytes=1000)
        _, plan, result, _ = self._run(path, "zip", limits)
        self.assertIn("orçamento", plan["erro_fatal"])

    def test_declared_size_lie_is_caught_while_streaming(self):
        path = self.tmp / "mentira.zip"
        fx.make_zip(path, {"a.bin": bytes(5000)})
        limits = Limits(max_entry_bytes=1000)
        listing = list_archive(path, "zip")
        listing["entradas"][0]["tamanho"] = 10  # simula cabeçalho que declara menos
        budget = Budget(limits.max_total_bytes)
        plan = plan_extraction(listing, path.stat().st_size, self.tmp / "d", limits, budget)
        result = extract_archive(path, listing, plan["plano"], limits, budget)
        self.assertTrue(result["erros"])
        self.assertFalse((self.tmp / "d" / "a.bin").exists())
        self.assertFalse(any(p.name.endswith(".tsrpart") for p in self.tmp.rglob("*")))

    def test_7z_extraction_names_and_idempotency(self):
        src = self.tmp / "src"
        src.mkdir()
        (src / "Leia-me ção.txt").write_bytes("olá".encode("utf-8"))
        (src / "vazio.dat").write_bytes(b"")
        (src / "com espaço (1).bin").write_bytes(bytes(range(256)) * 10)
        archive = self.tmp / "Disney_Pixar Test Racer.zip.7z"
        fx.make_7z(
            archive,
            {
                "Leia-me ção.txt": src / "Leia-me ção.txt",
                "pasta/vazio.dat": src / "vazio.dat",
                "pasta/com espaço (1).bin": src / "com espaço (1).bin",
            },
        )
        listing, plan, result, dest = self._run(archive, "7z")
        self.assertFalse(result["erros"], result["erros"])
        self.assertEqual((dest / "Leia-me ção.txt").read_bytes(), "olá".encode("utf-8"))
        self.assertEqual((dest / "pasta" / "vazio.dat").read_bytes(), b"")
        self.assertEqual((dest / "pasta" / "com espaço (1).bin").stat().st_size, 2560)
        before = sorted(p.relative_to(dest).as_posix() for p in dest.rglob("*"))
        listing, plan, result, dest = self._run(archive, "7z")
        statuses = {i["entrada"]["nome"]: i["entrada"]["status"] for i in result["extraidas"]}
        self.assertEqual(statuses["pasta/com espaço (1).bin"], "ja_existente_verificado")
        after = sorted(p.relative_to(dest).as_posix() for p in dest.rglob("*"))
        self.assertEqual(before, after)

    def test_single_stream_ratio_guard(self):
        import gzip

        path = self.tmp / "bomba.bin.gz"
        with gzip.open(path, "wb") as handle:
            handle.write(bytes(6 * MIB))
        limits = Limits(max_ratio=10, ratio_min_bytes=MIB)
        listing, plan, result, dest = self._run(path, "gzip", limits)
        self.assertTrue(any("razão de compressão" in e for e in result["erros"]), result["erros"])
        self.assertFalse((dest / "bomba.bin").exists())
        self.assertFalse(any(p.name.endswith(".tsrpart") for p in self.tmp.rglob("*")))

    def test_single_stream_gzip(self):
        import gzip

        path = self.tmp / "dados.bin.gz"
        with gzip.open(path, "wb") as handle:
            handle.write(b"abc" * 100)
        listing, plan, result, dest = self._run(path, "gzip")
        self.assertEqual(result["extraidas"][0]["relativo"], "dados.bin")
        self.assertEqual((dest / "dados.bin").read_bytes(), b"abc" * 100)


if __name__ == "__main__":
    unittest.main()
