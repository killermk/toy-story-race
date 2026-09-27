"""Teste ponta a ponta do intake com fixture sintética ("Disney_Pixar Test Racer.zip.7z")."""

import contextlib
import csv
import io
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path

import tsr_test_fixtures as fx
from tsr_forensics.cli import main
from tsr_forensics.custody import read_records, verify_chain
from tsr_forensics.hashing import hash_file

VOLATILE = {"gerado_em_utc", "sessao"}


def run_cli(*args):
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = main([str(a) for a in args])
    return code, stdout.getvalue(), stderr.getvalue()


def load_inventory(out: Path) -> dict:
    with open(out / "forensic_inventory.json", encoding="utf-8") as handle:
        return json.load(handle)


def stable(inventory: dict) -> dict:
    data = {k: v for k, v in inventory.items() if k not in VOLATILE}
    data["original"] = dict(data["original"])
    data["original"]["copia"] = {k: v for k, v in data["original"]["copia"].items() if k != "situacao"}
    for container in data["conteineres"]:
        for entry in container.get("entradas", []):
            entry.pop("status", None)
    return data


class IntakeEndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.tmp = Path(cls._tmp.name)
        cls.fixture = fx.build_original(cls.tmp)
        cls.original = cls.fixture["original"]
        cls.work = cls.tmp / "work"
        cls.out = cls.tmp / "out"
        cls.stat_before = os.stat(cls.original)
        cls.hash_before = hash_file(cls.original)
        cls.code1, cls.stdout1, cls.stderr1 = run_cli("intake", "--original", cls.original, "--workdir", cls.work, "--out", cls.out)
        cls.inv1 = load_inventory(cls.out)
        cls.files_after_1 = sorted(p.relative_to(cls.work).as_posix() for p in cls.work.rglob("*"))
        cls.code2, _, _ = run_cli("intake", "--original", cls.original, "--workdir", cls.work, "--out", cls.out)
        cls.inv2 = load_inventory(cls.out)
        cls.files_after_2 = sorted(p.relative_to(cls.work).as_posix() for p in cls.work.rglob("*"))

    @classmethod
    def tearDownClass(cls):
        for path in cls.work.rglob("*"):
            try:
                os.chmod(path, stat.S_IWUSR | stat.S_IRUSR | stat.S_IXUSR)
            except OSError:
                pass
        cls._tmp.cleanup()

    def test_exit_codes(self):
        self.assertEqual(self.code1, 0, self.stderr1 + json.dumps(self.inv1.get("erros"), ensure_ascii=False))
        self.assertEqual(self.code2, 0)
        self.assertEqual(self.inv1["erros"], [])

    def test_original_untouched(self):
        after = os.stat(self.original)
        self.assertEqual(after.st_size, self.stat_before.st_size)
        self.assertEqual(after.st_mtime_ns, self.stat_before.st_mtime_ns)
        self.assertEqual(hash_file(self.original), self.hash_before)
        original = self.inv1["original"]
        self.assertTrue(original["inalterado"])
        self.assertEqual(original["hashes"]["sha256"], self.hash_before["sha256"])
        self.assertEqual(original["hashes"]["crc32"], self.hash_before["crc32"])
        self.assertEqual(original["formato_detectado"], "7z")
        self.assertEqual(original["tamanho"], self.stat_before.st_size)
        self.assertEqual(sorted(p.name for p in self.original.parent.iterdir()), [self.original.name])

    def test_copy_is_verified_and_readonly(self):
        copy = self.work / "original_copy" / self.original.name
        self.assertTrue(copy.is_file())
        self.assertEqual(hash_file(copy), self.hash_before)
        self.assertEqual(stat.S_IMODE(os.stat(copy).st_mode) & 0o222, 0, "cópia deveria ser somente leitura")
        info = self.inv1["original"]["copia"]
        self.assertTrue(info["hashes_conferem"])
        self.assertTrue(info["somente_leitura"])
        self.assertEqual(info["situacao"], "copiada")
        self.assertEqual(self.inv2["original"]["copia"]["situacao"], "ja_existia_verificada")
        self.assertEqual(os.stat(copy).st_mtime_ns, self.stat_before.st_mtime_ns)

    def test_manifests(self):
        seven, inner = self.inv1["conteineres"][:2]
        self.assertEqual(seven["formato"], "7z")
        self.assertEqual([e["nome"] for e in seven["entradas"]], ["Disney_Pixar Test Racer.zip"])
        self.assertIsNotNone(seven["entradas"][0]["crc32"])
        self.assertEqual(inner["formato"], "zip")
        names = sorted(e["nome"] for e in inner["entradas"])
        self.assertEqual(
            names,
            sorted(["Test Racer.cue", "Test Racer (Track 1).bin", "Test Racer (Track 2).bin", "Test Racer.sbi", "Leia-me ção.txt"]),
        )
        for entry in inner["entradas"]:
            self.assertEqual(entry["metodo"], "deflate")
            self.assertIsNotNone(entry["tamanho_compactado"])
        extracted = self.work / "extracted" / self.original.name / "Disney_Pixar Test Racer.zip.extracted"
        self.assertTrue((extracted / "Leia-me ção.txt").is_file())

    def test_disc_tree_and_formats(self):
        self.assertEqual(len(self.inv1["discos"]), 1)
        disc = self.inv1["discos"][0]
        self.assertEqual(disc["layout"], "cue")
        tree = {n["caminho"]: n for n in disc["arvore"]}
        for path, (lba, size) in self.fixture["locations"].items():
            self.assertIn(path, tree)
            self.assertEqual(tree[path]["lba"], lba)
            self.assertEqual(tree[path]["tamanho"], size)
            self.assertIsNotNone(tree[path]["data"])
        for directory in ("/", "/DATA", "/DATA/SUB", "/SND", "/MOVIE", "/MUSIC"):
            self.assertTrue(tree[directory]["diretorio"], directory)
        expected = {
            "/TEST_000.00;1": "PS-X EXE",
            "/DATA/TEX.TIM;1": "TIM",
            "/DATA/SND.VAG;1": "VAG",
            "/SND/BANK.VAB;1": "VAB/VH (pBAV)",
            "/SND/SONG.SEQ;1": "SEQ/SEP (pQES)",
            "/MOVIE/INTRO.STR;1": "STR (setores 0160h)",
            "/MUSIC/VOICE.XA;1": "XA-ADPCM (setores Mode2 Form2/Audio)",
            "/SYSTEM.CNF;1": "texto ASCII",
            "/DATA/SUB/BLOB.DAT;1": "desconhecido",
        }
        for path, fmt in expected.items():
            self.assertEqual(tree[path]["formato"], fmt, path)
        self.assertEqual(disc["iso9660"]["verificacao_pycdlib"]["status"], "ok")
        self.assertEqual(disc["iso9660"]["pvd"]["identificador_sistema"], "PLAYSTATION")
        disc_dir = self.work / "disc_files" / "Test Racer"
        self.assertEqual((disc_dir / "SYSTEM.CNF").read_bytes(), fx.SYSTEM_CNF)
        self.assertEqual((disc_dir / "DATA" / "TEX.TIM").read_bytes(), fx.fake_tim())
        rows = {r["caminho_logico"].split("#iso9660:")[-1]: r for r in self.inv1["arquivos"] if r["tipo"] == "arquivo_de_disco"}
        self.assertEqual(len(rows), len(self.fixture["locations"]))
        self.assertEqual(rows["/MUSIC/VOICE.XA;1"]["setores_form2"], 4)
        self.assertEqual(rows["/DATA/SUB/BLOB.DAT;1"]["primeiros_16_bytes_hex"], fx.random_blob(5000)[:16].hex())
        self.assertGreater(rows["/DATA/SUB/BLOB.DAT;1"]["entropia"], 7.5)

    def test_system_cnf_serial(self):
        cnf = self.inv1["discos"][0]["system_cnf"]
        self.assertEqual(cnf["BOOT"], "cdrom:\\TEST_000.00;1")
        self.assertEqual(cnf["boot_executavel"], "TEST_000.00")
        self.assertTrue(cnf["boot_executavel_presente"])
        self.assertEqual(cnf["boot_executavel_formato"], "PS-X EXE")
        self.assertEqual((cnf["TCB"], cnf["EVENT"], cnf["STACK"]), ("4", "10", "801FFFF0"))

    def test_tracks_audio_and_subchannel(self):
        disc = self.inv1["discos"][0]
        self.assertEqual(disc["resumo_faixas"], {"total": 2, "dados": 1, "audio": 1, "outras": 0})
        audio = disc["faixas_audio"][0]
        self.assertEqual(audio["numero"], 2)
        self.assertEqual(audio["setores"], 300)
        self.assertEqual(audio["duracao_segundos"], 4.0)
        self.assertEqual(audio["duracao_a_partir_index01_segundos"], 2.0)
        self.assertEqual(audio["sha1"], hash_file(self.fixture["track2"])["sha1"])
        track1 = disc["faixas"][0]
        self.assertEqual(track1["estatisticas"]["form2"], 4)
        self.assertEqual(track1["hashes"]["sha1"], hash_file(self.fixture["track1"])["sha1"])
        self.assertEqual(disc["faixas"][1]["lba_index01"], self.fixture["data_sectors"] + 150)
        sub = disc["arquivos_subcanal"]
        self.assertEqual([s["nome"] for s in sub], ["Test Racer.sbi"])
        self.assertTrue(sub[0]["assinatura_sbi"])
        self.assertIn("não", sub[0]["observacao"].lower())

    def test_reports_generated_and_metadata_only(self):
        for name in ("forensic_inventory.json", "forensic_inventory.csv", "FORENSIC_INVENTORY.generated.md", "custody_log.jsonl"):
            self.assertTrue((self.out / name).is_file(), name)
        with open(self.out / "forensic_inventory.csv", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), len(self.inv1["arquivos"]))
        self.assertIn("sha256", rows[0])
        md = (self.out / "FORENSIC_INVENTORY.generated.md").read_text(encoding="utf-8")
        for needle in ("Identificação do original", self.hash_before["sha256"], "TEST_000.00", "Árvore do disco", "NÃO CONFIRMADO"):
            self.assertIn(needle, md)
        blob = fx.random_blob(5000)
        for name in ("forensic_inventory.json", "forensic_inventory.csv", "FORENSIC_INVENTORY.generated.md", "custody_log.jsonl"):
            text = (self.out / name).read_text(encoding="utf-8-sig")
            self.assertNotIn(blob[16:64].hex(), text)  # conteúdo além dos 16 bytes iniciais nunca aparece
            self.assertNotIn(str(self.tmp), text, f"caminho absoluto vazou em {name}")
        self.assertNotIn("_path", json.dumps(self.inv1))

    def test_report_content_statement_evidence_and_registry(self):
        md = (self.out / "FORENSIC_INVENTORY.generated.md").read_text(encoding="utf-8")
        self.assertNotIn("Nenhum conteúdo do jogo", md)
        self.assertIn("16 primeiros bytes", md)
        self.assertIn("Integridade da imagem", md)
        notes = " ".join(self.inv1["nota_evidencia"])
        self.assertIn("E1", notes)
        self.assertIn("E3", notes)
        self.assertIn("https://psx-spx.consoledev.net/", notes)
        self.assertEqual(self.inv1["integridade"]["situacao"], "nenhum problema de integridade detectado")
        registry = (self.work / "protected_sha256.txt").read_text(encoding="utf-8")
        self.assertIn(self.hash_before["sha256"], registry)
        self.assertIn(hash_file(self.fixture["track1"])["sha256"], registry)
        self.assertEqual(len(set(registry.split())), len(registry.split()), "registro sem duplicatas")
        cross = self.inv1["discos"][0]["iso9660"]["verificacao_pycdlib"]
        self.assertTrue(cross["processo_isolado"])

    def test_custody_log(self):
        records = read_records(self.out / "custody_log.jsonl")
        steps = [r["step"] for r in records]
        for step in ("intake.inicio", "original.hash", "copia.verificada", "manifesto", "extracao", "disco.iso9660",
                     "disco.system_cnf", "original.reverificado", "relatorios.gerados"):
            self.assertIn(step, steps)
        self.assertEqual(steps.count("intake.inicio"), 2)
        self.assertTrue(verify_chain(self.out / "custody_log.jsonl")["ok"])
        env = records[0]["environment"]
        self.assertEqual(env["kit"], "tsr-forensics")
        self.assertIsNotNone(env["py7zr"])
        self.assertIsNotNone(env["pycdlib"])
        self.assertTrue(all("<externo>" in " ".join(r["command"]) for r in records if r["step"] == "intake.inicio"))

    def test_idempotent(self):
        self.assertEqual(self.files_after_1, self.files_after_2)
        self.assertFalse([f for f in self.files_after_2 if f.endswith(".tsrpart")])
        self.assertEqual(stable(self.inv1), stable(self.inv2))

    def test_verify_command(self):
        code, out, _ = run_cli("verify", "--original", self.original, "--workdir", self.work, "--out", self.out)
        self.assertEqual(code, 0, out)
        self.assertIn("CONFERE", out)
        tampered_dir = self.tmp / "adulterado"
        tampered_dir.mkdir(exist_ok=True)
        tampered = tampered_dir / self.original.name
        tampered.write_bytes(self.original.read_bytes() + b"x")
        code, out, _ = run_cli("verify", "--original", tampered, "--workdir", self.work, "--out", self.out)
        self.assertEqual(code, 1)
        self.assertIn("ALTERADO", out)

    def test_redump_dat_comparison(self):
        t1 = hash_file(self.fixture["track1"])
        dat = self.tmp / "teste.dat"
        dat.write_text(
            '<?xml version="1.0"?>\n<!DOCTYPE datafile PUBLIC "-//Logiqx//DTD ROM Management Datafile//EN" '
            '"http://www.logiqx.com/Dats/datafile.dtd">\n<datafile><header><name>Teste sintetico</name>'
            "<version>0</version></header>"
            f'<game name="Test Racer (Sintetico)"><rom name="Test Racer (Track 1).bin" size="{t1["size"]}" '
            f'crc="{t1["crc32"]}" md5="{t1["md5"]}" sha1="{t1["sha1"]}"/>'
            '<rom name="Test Racer (Track 2).bin" size="1" crc="00000000" md5="0" sha1="0"/></game></datafile>\n',
            encoding="utf-8",
        )
        out = self.tmp / "out_redump"
        code, _, err = run_cli("intake", "--original", self.original, "--workdir", self.work, "--out", out, "--redump-dat", dat)
        self.assertEqual(code, 0, err)
        redump = load_inventory(out)["redump"]
        total = [m for m in redump["correspondencias"] if m["correspondencia_total"]]
        self.assertTrue(any(m["rom_dat"] == "Test Racer (Track 1).bin" for m in total))
        self.assertFalse(any(m["rom_dat"] == "Test Racer (Track 2).bin" for m in total))
        # QA: toda tabela do MD precisa de linha em branco antes (senão, colada a um item
        # de lista, vira continuação do parágrafo no CommonMark/GFM e não é renderizada).
        lines = (out / "FORENSIC_INVENTORY.generated.md").read_text(encoding="utf-8").split("\n")
        for index, line in enumerate(lines[1:], start=1):
            if line.startswith("| ") and not lines[index - 1].startswith("|"):
                self.assertEqual(lines[index - 1], "", f"tabela sem linha em branco antes (linha {index + 1})")
        evil = self.tmp / "evil.dat"
        evil.write_text('<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "b">]><datafile/>', encoding="utf-8")
        code, _, _ = run_cli("intake", "--original", self.original, "--workdir", self.work, "--out", self.tmp / "o3", "--redump-dat", evil)
        self.assertEqual(code, 1)
        self.assertIn("ENTITY", json.dumps(load_inventory(self.tmp / "o3")["erros"]))


class DirectImageTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.iso, self.locations = fx.make_iso()
        self.originals = self.tmp / "originais"
        self.originals.mkdir()

    def tearDown(self):
        for path in self.tmp.rglob("*"):
            try:
                os.chmod(path, stat.S_IWUSR | stat.S_IRUSR | stat.S_IXUSR)
            except OSError:
                pass
        self._tmp.cleanup()

    def _intake(self, original: Path):
        out = self.tmp / ("out_" + original.stem)
        code, _, err = run_cli("intake", "--original", original, "--workdir", self.tmp / "work", "--out", out)
        return code, err, load_inventory(out)

    def test_plain_iso_2048(self):
        original = self.originals / "jogo teste.iso"
        original.write_bytes(self.iso)
        code, err, inv = self._intake(original)
        self.assertEqual(code, 0, err + str(inv["erros"]))
        disc = inv["discos"][0]
        self.assertEqual(disc["layout"], "iso_2048")
        self.assertEqual(disc["faixas"][0]["tipo"], "MODE1/2048")
        tree = {n["caminho"]: n for n in disc["arvore"]}
        self.assertEqual(tree["/DATA/TEX.TIM;1"]["formato"], "TIM")
        self.assertEqual(disc["system_cnf"]["boot_executavel"], "TEST_000.00")

    def test_bin_without_cue(self):
        original = self.originals / "jogo teste.bin"
        original.write_bytes(fx.iso_to_mode2_raw(self.iso) + fx.audio_sectors(20))
        code, err, inv = self._intake(original)
        self.assertEqual(code, 0, err + str(inv["erros"]))
        disc = inv["discos"][0]
        self.assertEqual(disc["layout"], "bin_sem_cue")
        self.assertEqual(disc["deteccao"]["tipo_faixa"], "MODE2/2352")
        self.assertEqual(disc["iso9660"]["verificacao_pycdlib"]["status"], "ok")
        tree = {n["caminho"]: n for n in disc["arvore"]}
        self.assertEqual(tree["/TEST_000.00;1"]["formato"], "PS-X EXE")
        self.assertEqual(disc["faixas"][0]["estatisticas"]["setores_sem_sync"], 20)
        self.assertTrue(any("NÃO CONFIRMADA" in n for n in disc["observacoes"]))

    def test_truncated_bin_reports_missing_extents(self):
        raw = fx.iso_to_mode2_raw(self.iso)
        blob_lba, _ = self.locations["/DATA/SUB/BLOB.DAT;1"]
        original = self.originals / "truncado.bin"
        original.write_bytes(raw[: (blob_lba + 1) * 2352])
        code, err, inv = self._intake(original)
        # imagem incompleta = ERRO de integridade (código 1), não "concluído sem erros"
        self.assertEqual(code, 1, err + str(inv["erros"]))
        self.assertTrue(inv["integridade"]["situacao"].startswith("ALERTA"))
        warnings = " ".join(inv["avisos"])
        self.assertIn("PVD declara", warnings)
        self.assertIn("BLOB.DAT", " ".join(inv["erros"]))
        rows = {r["caminho_logico"].split("#iso9660:")[-1]: r for r in inv["arquivos"] if r["tipo"] == "arquivo_de_disco"}
        self.assertEqual(len(rows), len(self.locations))
        self.assertIsNone(rows["/DATA/SUB/BLOB.DAT;1"]["sha256"])
        self.assertIn("ultrapassa", rows["/DATA/SUB/BLOB.DAT;1"]["observacoes"][0])
        self.assertEqual(rows["/TEST_000.00;1"]["formato"], "PS-X EXE")

    def test_zip_slip_through_intake(self):
        from test_archives import _evil_zip

        original = _evil_zip(self.originals / "malicioso.zip")
        code, err, inv = self._intake(original)
        self.assertEqual(code, 0, err)
        warnings = " ".join(inv["avisos"])
        self.assertIn("../evil.txt", warnings)
        self.assertIn("/abs/evil2.txt", warnings)
        work_files = sorted(p.relative_to(self.tmp).as_posix() for p in self.tmp.rglob("*") if p.is_file())
        self.assertFalse([f for f in work_files if f.endswith("evil.txt") or f.endswith("evil2.txt")], work_files)

    def test_bomb_refused_through_intake(self):
        original = self.originals / "bomba.zip"
        fx.make_zip(original, {"zeros.bin": bytes(8 * 1024 * 1024)})
        out = self.tmp / "out_bomba"
        code, _, _ = run_cli(
            "intake", "--original", original, "--workdir", self.tmp / "work", "--out", out,
            "--max-ratio", "5", "--ratio-min-bytes", "1M",
        )
        self.assertEqual(code, 1)
        inv = load_inventory(out)
        self.assertIn("razão de compressão", " ".join(inv["erros"]))
        self.assertFalse(list((self.tmp / "work" / "extracted").rglob("zeros.bin")))

    def test_max_depth_stops_recursion(self):
        fixture = fx.build_original(self.tmp / "profundidade")
        out = self.tmp / "out_depth"
        code, _, err = run_cli("intake", "--original", fixture["original"], "--workdir", self.tmp / "work_depth",
                               "--out", out, "--max-depth", "1")
        self.assertEqual(code, 0, err)
        inv = load_inventory(out)
        self.assertEqual(len(inv["conteineres"]), 2)
        self.assertIn("profundidade", inv["conteineres"][1]["situacao"])
        self.assertEqual(inv["discos"], [])
        self.assertTrue(any("profundidade máxima" in w for w in inv["avisos"]))

    def test_refuses_original_inside_workdir(self):
        work = self.tmp / "work"
        inner = work / "extracted" / "x"
        inner.mkdir(parents=True)
        original = inner / "a.iso"
        original.write_bytes(self.iso)
        code, _, err = run_cli("intake", "--original", original, "--workdir", work, "--out", self.tmp / "o")
        self.assertEqual(code, 2)
        self.assertIn("área de trabalho", err)


if __name__ == "__main__":
    unittest.main()
