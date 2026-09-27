import hashlib
import json
import tempfile
import unittest
import zlib
from pathlib import Path

import tsr_test_fixtures  # noqa: F401
from tsr_forensics.custody import CustodyLog, read_records, verify_chain
from tsr_forensics.hashing import entropy_of_bytes, hash_and_entropy, hash_file, hash_file_range
from tsr_forensics.config import parse_size


class HashingTests(unittest.TestCase):
    def test_hashes_match_stdlib(self):
        data = bytes(range(256)) * 5000  # > 1 chunk
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.bin"
            path.write_bytes(data)
            result = hash_file(path)
            self.assertEqual(result["size"], len(data))
            self.assertEqual(result["crc32"], f"{zlib.crc32(data) & 0xFFFFFFFF:08x}")
            self.assertEqual(result["md5"], hashlib.md5(data).hexdigest())
            self.assertEqual(result["sha1"], hashlib.sha1(data).hexdigest())
            self.assertEqual(result["sha256"], hashlib.sha256(data).hexdigest())
            part = hash_file_range(path, 100, 1000)
            self.assertEqual(part["sha1"], hashlib.sha1(data[100:1100]).hexdigest())

    def test_entropy_full_and_sampled(self):
        self.assertEqual(entropy_of_bytes(b"\x00" * 100), 0.0)
        self.assertAlmostEqual(entropy_of_bytes(bytes(range(256)) * 4), 8.0, places=3)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.bin"
            path.write_bytes(bytes(range(256)) * 4096)
            _, full = hash_and_entropy(path, full_max_bytes=10 * 1024 * 1024)
            self.assertEqual(full["metodo"], "completo")
            _, sampled = hash_and_entropy(path, full_max_bytes=1024)
            self.assertEqual(sampled["metodo"], "amostra")
            self.assertAlmostEqual(sampled["valor"], 8.0, places=2)
            empty = Path(tmp) / "vazio"
            empty.write_bytes(b"")
            self.assertEqual(hash_and_entropy(empty, 1024)[1]["metodo"], "vazio")

    def test_parse_size(self):
        self.assertEqual(parse_size("4096"), 4096)
        self.assertEqual(parse_size("16G"), 16 * 1024 ** 3)
        self.assertEqual(parse_size("500M"), 500 * 1024 ** 2)
        self.assertEqual(parse_size("1.5GiB"), int(1.5 * 1024 ** 3))
        with self.assertRaises(ValueError):
            parse_size("muito")


class CustodyTests(unittest.TestCase):
    def test_chain_append_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "custody_log.jsonl"
            log = CustodyLog(path, ["python", "-m", "tsr_forensics", "intake"])
            log.record("a", "ok", x=1)
            log.record("b", "aviso", y="ç")
            CustodyLog(path, ["outro"]).record("c", "erro")
            records = read_records(path)
            self.assertEqual([r["step"] for r in records], ["a", "b", "c"])
            for record in records:
                self.assertTrue(record["timestamp_utc"].endswith("Z"))
                env = record["environment"]
                for key in ("kit_version", "python", "py7zr", "pycdlib"):
                    self.assertIn(key, env)
            self.assertTrue(verify_chain(path)["ok"])
            # CRLF (ex.: checkout no Windows com autocrlf) não quebra a cadeia
            crlf = Path(tmp) / "crlf.jsonl"
            crlf.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
            self.assertTrue(verify_chain(crlf)["ok"])
            # alteração de uma linha antiga é detectada
            lines = path.read_text(encoding="utf-8").splitlines()
            first = json.loads(lines[0])
            first["details"]["x"] = 2
            lines[0] = json.dumps(first, ensure_ascii=False, sort_keys=True)
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            result = verify_chain(path)
            self.assertFalse(result["ok"])
            self.assertEqual(result["quebra_na_linha"], 2)


if __name__ == "__main__":
    unittest.main()
