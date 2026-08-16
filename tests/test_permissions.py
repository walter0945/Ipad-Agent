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

    def test_shell_blocks_secret_and_escape_in_args(self):
        # 命令头在白名单，但参数试图读密钥/越界/绝对路径 —— 必须挡住
        g = self._gate()
        self.assertFalse(g.shell("ls ../.env"))          # 密钥 token
        self.assertFalse(g.shell("ls .."))               # 路径穿越
        self.assertFalse(g.shell("ls /etc/passwd"))      # 绝对路径
        self.assertTrue(g.shell("ls -l data"))           # 正常相对路径放行

    def test_python_shows_code_in_prompt(self):
        seen = []
        g = self._gate(strong=lambda m: seen.append(m) or True)
        self.assertTrue(g.python("print('hi')"))
        self.assertTrue(seen and "print('hi')" in seen[0])   # 代码出现在确认提示里

    def test_python_blocks_secret_and_escape(self):
        g = self._gate()
        self.assertFalse(g.python("open('../.env').read()"))
        self.assertFalse(g.python("open('/etc/passwd')"))

    def test_python_requires_allowlist(self):
        g = PermissionGate(Path("workspace"), ("ls",), lambda m: True, lambda m: True)
        self.assertFalse(g.python("print(1)"))           # python3 不在白名单

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
