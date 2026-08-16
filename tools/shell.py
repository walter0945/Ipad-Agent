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
        code = args.get("code", "")
        path = gate.sandbox_root / "agent_main.py"
        if code.strip():
            # 覆盖写入持久文件（记住上次代码，供后续增量编辑）
            path.write_text(code, encoding="utf-8")
        elif not path.exists():
            return "没有已保存的代码：请先传 code 写入 agent_main.py，或确认该文件存在"
        if not gate.python(path.read_text(encoding="utf-8")):
            return "拒绝：代码触碰密钥/越界，或未确认执行"
        r = subprocess.run([sys.executable, path.name], capture_output=True, text=True,
                           cwd=str(gate.sandbox_root), timeout=120)
        return ((r.stdout or "") + (r.stderr or "")).strip() or "（无输出）"

    return [Tool("run_shell", "执行 shell 命令（白名单 + 确认）",
                 {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}, run_shell),
            Tool("run_python", "执行 Python：传 code 覆盖保存到 agent_main.py 并运行；不传 code 则重跑已保存的 agent_main.py（配合 edit_file 增量改）",
                 {"type": "object", "properties": {"code": {"type": "string"}}, "required": []}, run_python)]
