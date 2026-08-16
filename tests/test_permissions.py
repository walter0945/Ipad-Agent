# tests/test_permissions.py
import unittest
from pathlib import Path
from permissions import PermissionGate

class TestGate(unittest.TestCase):
    def _gate(self, confirm=lambda m: True, strong=lambda m: True):
        return PermissionGate(Path("workspace"), ("ls", "python3"), confirm, strong)

    def test_read_within_root_no_confirm(self):
        g = self._gate(confirm=lambda m: (_ for _ in ()).throw(AssertionError()))
        self.assertTrue(g.read(Path("workspace/a.txt")))

    def test_read_outside_root_denied(self):
        g = self._gate()
        self.assertFalse(g.read(Path("C:/etc/passwd")))

    def test_write_requires_confirm(self):
        called = []
        g = self._gate(confirm=lambda m: called.append(m) or True)
        self.assertTrue(g.write(Path("workspace/b.txt")))
        self.assertTrue(called)

    def test_delete_requires_strong_confirm(self):
        seen = {}
        g = self._gate(strong=lambda m: seen.setdefault("strong", True) and False)
        self.assertFalse(g.delete(Path("workspace/b.txt")))
        self.assertIn("strong", seen)

    def test_shell_allowlist_and_confirm(self):
        g = self._gate()
        self.assertTrue(g.shell("ls -l"))
        self.assertFalse(g.shell("rm -rf /"))

    def test_secret_files_unreadable(self):
        g = self._gate()
        for name in ("workspace/.env", "workspace/keys/id_rsa", "workspace/secret.pem",
                     "workspace/cert.p12", "workspace/credentials.json", "workspace/server.key"):
            self.assertFalse(g.read(Path(name)), name)
            self.assertFalse(g.write(Path(name)), name)
            self.assertFalse(g.delete(Path(name)), name)

    def test_overwrite_requires_strong_confirm(self):
        seen = {}
        g = self._gate(strong=lambda m: seen.setdefault("strong", True) and True)
        self.assertTrue(g.overwrite(Path("workspace/b.txt")))
        self.assertIn("strong", seen)

    def test_overwrite_denied_without_strong_confirm(self):
        g = self._gate(strong=lambda m: False)
        self.assertFalse(g.overwrite(Path("workspace/b.txt")))

    def test_overwrite_secret_denied(self):
        g = self._gate()
        self.assertFalse(g.overwrite(Path("workspace/.env")))

if __name__ == "__main__":
    unittest.main()
