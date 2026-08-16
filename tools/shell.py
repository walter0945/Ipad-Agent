import re
import subprocess
import sys
from tools import Tool

BLOCKED = re.compile(r"(?<![|])\|(?![|])|(?<![&])&(?![&])|\$\(|`")

def split_commands(command: str) -> list[str]:
    return [c.strip() for c in re.split(r"&&|\|\||;", command) if c.strip()]

def make_shell_tools(gate) -> list[Tool]:
    def run_shell(args):
        command = args["command"]
        if BLOCKED.search(command):
            return "拒绝：命令含被拦截的语法（管道/&/命令替换）"
        outputs = []
        for cmd in split_commands(command):
            if not gate.shell(cmd):
                return f"拒绝：命令不在白名单或未确认 ({cmd})"
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                               cwd=gate.sandbox_root, timeout=30)
            outputs.append((r.stdout or "") + (r.stderr or ""))
        return "\n".join(outputs).strip() or "（无输出）"

    def run_python(args):
        if not gate.shell("python3"):
            return "拒绝：执行 Python 需确认"
        tmp = gate.sandbox_root / ".agent_tmp.py"
        tmp.write_text(args["code"], encoding="utf-8")
        try:
            r = subprocess.run([sys.executable, tmp.name], capture_output=True, text=True,
                               cwd=str(gate.sandbox_root), timeout=60)
            return ((r.stdout or "") + (r.stderr or "")).strip() or "（无输出）"
        finally:
            tmp.unlink(missing_ok=True)

    return [Tool("run_shell", "执行 shell 命令（白名单 + 确认）",
                 {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}, run_shell),
            Tool("run_python", "执行一段 Python 代码（写临时文件运行，返回输出，适合写代码→跑→看结果）",
                 {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]}, run_python)]
