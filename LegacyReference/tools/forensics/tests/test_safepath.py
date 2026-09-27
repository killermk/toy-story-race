import os
import tempfile
import unittest
from pathlib import Path

import tsr_test_fixtures  # noqa: F401  (ajusta sys.path)
from tsr_forensics.safepath import NameAllocator, UnsafePath, check_member_name, safe_join, sanitize_component


class CheckMemberNameTests(unittest.TestCase):
    def test_accepts_normal_names_with_spaces_and_non_ascii(self):
        self.assertEqual(check_member_name("Test Racer (Track 1).bin"), ["Test Racer (Track 1).bin"])
        self.assertEqual(check_member_name("pasta/Leia-me ção.txt"), ["pasta", "Leia-me ção.txt"])
        self.assertEqual(check_member_name("./a//b/./c"), ["a", "b", "c"])

    def test_rejects_traversal_absolute_drive_and_nul(self):
        cases = {
            "../evil.txt": "componente '..'",
            "a/../../evil.txt": "componente '..'",
            "a\\..\\..\\evil.txt": "componente '..'",
            "/abs/evil.txt": "caminho absoluto",
            "\\abs\\evil.txt": "caminho absoluto",
            "//server/share/x": "caminho absoluto",
            "C:/Windows/evil.txt": "letra de unidade",
            "C:evil.txt": "letra de unidade",
            "a\x00b": "byte nulo",
            "": "nome vazio",
            "./": "nome vazio",
        }
        for name, reason in cases.items():
            with self.subTest(name=name):
                with self.assertRaises(UnsafePath) as ctx:
                    check_member_name(name)
                self.assertIn(reason, ctx.exception.reason)


class SanitizeTests(unittest.TestCase):
    def test_windows_invalid_chars_reserved_and_trailing(self):
        self.assertEqual(sanitize_component('a<b>c:d"e|f?g*h')[0], "a_b_c_d_e_f_g_h")
        self.assertEqual(sanitize_component("CON")[0], "_CON")
        self.assertEqual(sanitize_component("nul.txt")[0], "_nul.txt")
        self.assertEqual(sanitize_component("README. ")[0], "README")
        self.assertEqual(sanitize_component("...")[0], "_")
        clean, changed = sanitize_component("Leia-me ção.txt")
        self.assertEqual(clean, "Leia-me ção.txt")
        self.assertFalse(changed)

    def test_long_component_is_truncated_with_hash(self):
        clean, changed = sanitize_component("x" * 400 + ".bin")
        self.assertTrue(changed)
        self.assertLessEqual(len(clean), 200)
        self.assertTrue(clean.endswith(".bin"))

    def test_allocator_handles_case_collisions(self):
        allocator = NameAllocator()
        self.assertEqual(allocator.allocate(["A.BIN"], "A.BIN")[0], ["A.BIN"])
        final, renamed = allocator.allocate(["a.bin"], "a.bin")
        self.assertTrue(renamed)
        self.assertEqual(final, ["a~2.bin"])


class SafeJoinTests(unittest.TestCase):
    def test_inside_and_symlink_component_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "dest"
            base.mkdir()
            self.assertEqual(safe_join(base, ["a", "b.txt"]), base / "a" / "b.txt")
            outside = Path(tmp) / "outside"
            outside.mkdir()
            try:
                os.symlink(outside, base / "link", target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("sistema sem suporte a links simbólicos")
            with self.assertRaises(UnsafePath):
                safe_join(base, ["link", "evil.txt"])


if __name__ == "__main__":
    unittest.main()
