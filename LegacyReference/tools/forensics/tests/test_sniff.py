import io
import tempfile
import unittest
import zipfile
from pathlib import Path

import tsr_test_fixtures as fx
from tsr_forensics.signatures import detect_container, detect_from_head
from tsr_forensics.sniff import sniff_bytes
from tsr_forensics.systemcnf import parse_system_cnf


class SniffTests(unittest.TestCase):
    def test_ps1_formats(self):
        exe = sniff_bytes(fx.fake_psx_exe())
        self.assertEqual(exe.format, "PS-X EXE")
        self.assertEqual(exe.category, "executavel")
        self.assertTrue(exe.details["tamanho_confere"])
        self.assertIn("psx-spx", exe.source)

        tim = sniff_bytes(fx.fake_tim())
        self.assertEqual(tim.format, "TIM")
        self.assertTrue(tim.details["valido"])
        self.assertTrue(tim.details["tem_clut"])
        self.assertEqual(tim.details["tipo"], "4bpp")

        self.assertEqual(sniff_bytes(fx.fake_vag()).format, "VAG")
        self.assertEqual(sniff_bytes(fx.fake_vag()).details["taxa_amostragem_hz_be"], 22050)
        self.assertEqual(sniff_bytes(fx.fake_vab()).format, "VAB/VH (pBAV)")
        seq = sniff_bytes(fx.fake_seq())
        self.assertEqual(seq.format, "SEQ/SEP (pQES)")
        self.assertIn("SEQ", seq.details["leitura"])
        self.assertEqual(sniff_bytes(fx.fake_str()).format, "STR (setores 0160h)")

    def test_tim_with_bad_sections_is_unknown_with_hint(self):
        result = sniff_bytes(fx.broken_tim())
        self.assertEqual(result.format, "desconhecido")
        self.assertTrue(any("TIM" in hint for hint in result.hints))

    def test_generic_and_unknown(self):
        self.assertEqual(sniff_bytes(b"").format, "vazio")
        self.assertEqual(sniff_bytes(b"BOOT = cdrom:\\X;1\r\n").format, "texto ASCII")
        self.assertEqual(sniff_bytes("ção\n".encode("utf-8")).format, "texto UTF-8")
        self.assertEqual(sniff_bytes(b"\x89PNG\r\n\x1a\n" + bytes(20)).format, "PNG")
        wav = b"RIFF" + (36).to_bytes(4, "little") + b"WAVEfmt " + bytes(28)
        self.assertEqual(sniff_bytes(wav).format, "RIFF/WAVE")
        bmp = bytearray(b"BM" + bytes(60))
        bmp[2:6] = (62).to_bytes(4, "little")
        self.assertEqual(sniff_bytes(bytes(bmp)).format, "BMP")
        self.assertEqual(sniff_bytes(fx.random_blob(4000)).format, "desconhecido")
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("a.txt", b"a")
        self.assertEqual(sniff_bytes(buffer.getvalue()).category, "compactado")

    def test_container_detection_by_magic_not_extension(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            payload = tmp / "a.txt"
            payload.write_bytes(b"conteudo")
            fake_zip = tmp / "na_verdade_7z.zip"
            fx.make_7z(fake_zip, {"a.txt": payload})
            self.assertEqual(detect_container(fake_zip)["format"], "7z")
            iso, _ = fx.make_iso({"/A.TXT;1": b"a"})
            fake_txt = tmp / "imagem.txt"
            fake_txt.write_bytes(iso)
            self.assertEqual(detect_container(fake_txt)["format"], "iso9660")
            raw = tmp / "sem_extensao"
            raw.write_bytes(fx.iso_to_mode2_raw(iso))
            result = detect_container(raw)
            self.assertEqual(result["format"], "cd_raw_2352")
            self.assertEqual(result["mode"], 2)
            self.assertTrue(result["iso9660"])
        self.assertEqual(detect_from_head(b'FILE "x.bin" BINARY\n  TRACK 01 MODE2/2352\n', 40)["format"], "cue")
        self.assertIsNone(detect_from_head(b"texto qualquer", 14)["format"])


class SystemCnfTests(unittest.TestCase):
    def test_parse_fake_serial(self):
        parsed = parse_system_cnf(fx.SYSTEM_CNF)
        self.assertEqual(parsed["BOOT"], "cdrom:\\TEST_000.00;1")
        self.assertEqual(parsed["boot_executavel"], "TEST_000.00")
        self.assertEqual(parsed["boot_versao"], "1")
        self.assertEqual(parsed["codigo_produto_derivado"], "TEST-00000")
        self.assertIn("NÃO CONFIRMADO", parsed["codigo_produto_observacao"])
        self.assertEqual(parsed["TCB"], "4")
        self.assertEqual(parsed["EVENT_hex_valor"], 16)
        self.assertEqual(parsed["STACK_hex_valor"], 0x801FFFF0)

    def test_nonstandard_name_and_unknown_keys(self):
        parsed = parse_system_cnf(b"BOOT=cdrom:\\EXE\\MAIN.EXE;1 arg\nFOO = 1\n")
        self.assertEqual(parsed["boot_executavel"], "MAIN.EXE")
        self.assertEqual(parsed["boot_argumentos"], "arg")
        self.assertIsNone(parsed["codigo_produto_derivado"])
        self.assertEqual(parsed["chaves_desconhecidas"], ["FOO"])


if __name__ == "__main__":
    unittest.main()
