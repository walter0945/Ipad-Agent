import unittest
from pathlib import Path
from permissions import PermissionGate
from tools.shell import make_shell_tools, split_commands

class TestShell(unittest.TestCase):
    def test_split_commands(self):
        self.assertEqual(split_commands("echo a && echo b"), ["echo a", "echo b"])

    def test_block_pipe(self):
        gate = PermissionGate(Path("workspace"), ("echo",), lambda m: True, lambda m: True)
        tool = {t.name: t for t in make_shell_tools(gate)}["run_shell"]
        self.assertIn("拒绝", tool.func({"command": "echo a | grep b"}))

    def test_run_allowed(self):
        gate = PermissionGate(Path("workspace"), ("echo",), lambda m: True, lambda m: True)
        tool = {t.name: t for t in make_shell_tools(gate)}["run_shell"]
        self.assertIn("hi", tool.func({"command": "echo hi"}))

    def test_run_and_chain(self):
        gate = PermissionGate(Path("workspace"), ("echo",), lambda m: True, lambda m: True)
        tool = {t.name: t for t in make_shell_tools(gate)}["run_shell"]
        out = tool.func({"command": "echo a && echo b"})
        self.assertIn("a", out)
        self.assertIn("b", out)

    def test_run_python(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            gate = PermissionGate(Path(d), ("python3",), lambda m: True, lambda m: True)
            tool = {t.name: t for t in make_shell_tools(gate)}["run_python"]
            out = tool.func({"code": "print('hello from python')"})
            self.assertIn("hello from python", out)

    def test_run_python_persists_and_reruns(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            gate = PermissionGate(Path(d), ("python3",), lambda m: True, lambda m: True)
            tool = {t.name: t for t in make_shell_tools(gate)}["run_python"]
            tool.func({"code": "x = 42\nprint(x)"})
            self.assertTrue((Path(d) / "agent_main.py").exists())
            out = tool.func({})   # 不传 code，重跑已保存文件
            self.assertIn("42", out)

    def test_run_python_no_code_no_file(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            gate = PermissionGate(Path(d), ("python3",), lambda m: True, lambda m: True)
            tool = {t.name: t for t in make_shell_tools(gate)}["run_python"]
            out = tool.func({})
            self.assertIn("没有已保存的代码", out)

    def test_run_python_blocks_sandbox_escape(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "workspace"; root.mkdir()
            (Path(d) / ".env").write_text("LLM_API_KEY=sk-SECRET", encoding="utf-8")
            gate = PermissionGate(root, ("python3",), lambda m: True, lambda m: True)
            tool = {t.name: t for t in make_shell_tools(gate)}["run_python"]
            out = tool.func({"code": "print(open('../.env').read())"})
            self.assertIn("拒绝", out)
            self.assertNotIn("sk-SECRET", out)

    def test_run_shell_blocks_secret_via_cat(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "workspace"; root.mkdir()
            (Path(d) / ".env").write_text("LLM_API_KEY=sk-SECRET", encoding="utf-8")
            gate = PermissionGate(root, ("cat",), lambda m: True, lambda m: True)
            tool = {t.name: t for t in make_shell_tools(gate)}["run_shell"]
            out = tool.func({"command": "cat ../.env"})
            self.assertIn("拒绝", out)
            self.assertNotIn("sk-SECRET", out)

if __name__ == "__main__":
    unittest.main()
