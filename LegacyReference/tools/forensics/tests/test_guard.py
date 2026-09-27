import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import tsr_test_fixtures as fx
from tsr_forensics.guard import install_hook, run_guard

GIT = shutil.which("git")


@unittest.skipIf(GIT is None, "git não disponível")
class GuardTests(unittest.TestCase):
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
        self._tmp.cleanup()

    def git(self, *args, check=True):
        return subprocess.run(["git", "-C", str(self.repo), *args], env=self.env, check=check,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def guard(self, **kwargs):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = run_guard(self.repo, **kwargs)
        return code, out.getvalue() + err.getvalue()

    def test_staged_tim_and_exe_blocked_text_allowed(self):
        (self.repo / "README.md").write_text("# Projeto\nTexto comum.\n", encoding="utf-8")
        (self.repo / "notas.txt").write_text("BOOT = cdrom:\\X;1\nFILE \"a.bin\" BINARY\n  TRACK 01 MODE2/2352\n", encoding="utf-8")
        self.git("add", "README.md", "notas.txt")
        code, output = self.guard(staged=True)
        self.assertEqual(code, 0, output)

        (self.repo / "textura.dat").write_bytes(fx.fake_tim())  # extensão inocente, conteúdo TIM
        (self.repo / "boot.x").write_bytes(fx.fake_psx_exe())
        self.git("add", "textura.dat", "boot.x")
        code, output = self.guard(staged=True)
        self.assertEqual(code, 1)
        self.assertIn("textura.dat", output)
        self.assertIn("TIM", output)
        self.assertIn("boot.x", output)
        self.assertIn("PS-X EXE", output)
        self.assertNotIn("README.md:", output)

    def test_staged_content_is_read_from_index_not_worktree(self):
        target = self.repo / "arquivo.dat"
        target.write_bytes(fx.fake_vag())
        self.git("add", "arquivo.dat")
        target.write_text("agora é texto no disco, mas o índice tem VAG\n", encoding="utf-8")
        code, output = self.guard(staged=True)
        self.assertEqual(code, 1)
        self.assertIn("VAGp", output)

    def test_extension_size_and_inventory_hash(self):
        (self.repo / "jogo.cue").write_text('FILE "x.bin" BINARY\n', encoding="utf-8")
        (self.repo / "grande.dat").write_bytes(bytes(3000) + fx.random_blob(5000))
        secret = self.repo / "parece_texto.md"
        secret.write_text("conteúdo idêntico a um arquivo inventariado\n", encoding="utf-8")
        inventory = self.tmp / "inv.json"
        inventory.write_text(
            json.dumps({"arquivos": [{"sha256": __import__("hashlib").sha256(secret.read_bytes()).hexdigest(), "tamanho": 10}]}),
            encoding="utf-8",
        )
        self.git("add", ".")
        code, output = self.guard(staged=True, inventories=[inventory], max_binary=4096)
        self.assertEqual(code, 1)
        self.assertIn("jogo.cue: extensão bloqueada", output)
        self.assertIn("binário grande", output)
        self.assertIn("parece_texto.md: SHA-256 consta", output)
        # a lista de permissões não libera correspondência de hash
        code, output = self.guard(staged=True, inventories=[inventory], max_binary=4096, allow=["*"])
        self.assertEqual(code, 1)
        self.assertIn("parece_texto.md", output)
        self.assertNotIn("jogo.cue", output)

    def test_dir_mode(self):
        folder = self.tmp / "pasta"
        folder.mkdir()
        (folder / "ok.txt").write_text("ok", encoding="utf-8")
        code, output = self.guard(directory=folder)
        self.assertEqual(code, 0, output)
        (folder / "som.bin").write_bytes(fx.fake_vag())
        code, output = self.guard(directory=folder)
        self.assertEqual(code, 1)
        self.assertIn("som.bin", output)

    def test_install_hook_blocks_commit(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(install_hook(self.repo, python=sys.executable), 0)
            self.assertEqual(install_hook(self.repo, python=sys.executable), 0)  # reinstalação idempotente
        hook = self.repo / ".git" / "hooks" / "pre-commit"
        self.assertIn("tsr-forensics-guard-hook", hook.read_text(encoding="utf-8"))
        (self.repo / "leia.md").write_text("texto\n", encoding="utf-8")
        self.git("add", "leia.md")
        result = self.git("commit", "-q", "-m", "texto", check=False)
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", "replace"))
        (self.repo / "tex.tim").write_bytes(fx.fake_tim())
        self.git("add", "tex.tim")
        result = self.git("commit", "-q", "-m", "tim", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("BLOQUEADO", result.stderr.decode("utf-8", "replace"))
        log = self.git("log", "--oneline").stdout.decode()
        self.assertEqual(len(log.strip().splitlines()), 1)

    def test_install_hook_refuses_foreign_hook(self):
        hooks = self.repo / ".git" / "hooks"
        hooks.mkdir(parents=True, exist_ok=True)
        (hooks / "pre-commit").write_text("#!/bin/sh\necho outro\n", encoding="utf-8")
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(install_hook(self.repo), 2)
            self.assertEqual(install_hook(self.repo, force=True), 0)
        self.assertTrue(list(hooks.glob("pre-commit.backup-*")))


if __name__ == "__main__":
    unittest.main()
