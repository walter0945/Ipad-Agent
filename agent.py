import json
from pathlib import Path
from typing import Callable
from config import LLMConfig
from llm import LLMClient
from permissions import PermissionGate
from session import Session
from skills import Skill, load_skills
from tools import Registry
from tools.files import make_files_tools
from tools.spreadsheet import make_spreadsheet_tools
from tools.shell import make_shell_tools
from tools.search import make_search_tools

def build_system_prompt(skills: list[Skill]) -> str:
    lines = ["你是一个运行在 iPad 本地沙盒里的 AI agent，帮用户处理文件、表格与信息。",
             "规则：所有文件操作限沙盒目录；删除/覆盖/执行 shell 前会经用户确认；不确定就问。",
             "可用的 skills："]
    for s in skills:
        lines.append(f"- {s.name}: {s.description}")
    if skills:
        lines.append("\n各 skill 用法：")
        for s in skills:
            lines.append(f"[{s.name}]\n{s.body}")
    return "\n".join(lines)

class Agent:
    def __init__(self, config: LLMConfig, sandbox_root: Path,
                 confirm: Callable[[str], bool], strong_confirm: Callable[[str], bool]):
        sandbox_root.mkdir(parents=True, exist_ok=True)
        self.llm = LLMClient(config)
        self.gate = PermissionGate(sandbox_root, ("ls", "python3", "ffmpeg", "cat"), confirm, strong_confirm)
        self.registry = Registry()
        for t in (make_files_tools(self.gate) + make_spreadsheet_tools(self.gate)
                  + make_shell_tools(self.gate) + make_search_tools()):
            self.registry.register(t)
        self.skills = load_skills(Path("skills"))
        self.session_path = sandbox_root / ".session.jsonl"
        if self.session_path.exists():
            self.session = Session.load(self.session_path)
        else:
            self.session = Session(build_system_prompt(self.skills), self.session_path)

    def run(self, user_input: str) -> str:
        self.session.add("user", user_input)
        for _ in range(20):  # 最多 20 轮工具调用
            result = self.llm.chat(self.session.to_messages(), self.registry.schemas())
            if result.tool_calls:
                for tc in result.tool_calls:
                    try:
                        out = self.registry.run(tc.name, tc.arguments)
                    except Exception as e:  # noqa: BLE001
                        out = f"工具执行出错：{e}"
                    self.session.add("tool", f"[{tc.name}] {out}")
                continue
            if result.content:
                self.session.add("assistant", result.content)
                self.session.save()
                return result.content
            return "（无输出）"
        return "（达到最大工具轮数）"
