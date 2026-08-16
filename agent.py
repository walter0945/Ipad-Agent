import json
import sys
from pathlib import Path
from typing import Callable
from dotenv import load_dotenv
from config import LLMConfig, load_llm_config
from llm import LLMClient
from permissions import PermissionGate
from session import Session
from skills import Skill, load_skills
from index import build_index
from router import should_use_reasoner
from tools import Registry
from tools.files import make_files_tools
from tools.spreadsheet import make_spreadsheet_tools
from tools.shell import make_shell_tools
from tools.search import make_search_tools
from tools.video import make_video_tools

def build_system_prompt(skills: list[Skill], file_index: str = "") -> str:
    lines = ["你是一个运行在 iPad 本地沙盒里的 AI agent，帮用户处理文件、表格与信息。",
             "规则：所有文件操作限沙盒目录；删除/覆盖/执行 shell 前会经用户确认；不确定就问。",
             "可用的 skills："]
    for s in skills:
        lines.append(f"- {s.name}: {s.description}")
    if skills:
        lines.append("\n各 skill 用法：")
        for s in skills:
            lines.append(f"[{s.name}]\n{s.body}")
    if file_index:
        lines.append(f"\n当前沙盒文件索引：\n{file_index}")
    return "\n".join(lines)

class Agent:
    def __init__(self, config: LLMConfig, sandbox_root: Path,
                 confirm: Callable[[str], bool], strong_confirm: Callable[[str], bool],
                 persist: bool = True):
        sandbox_root.mkdir(parents=True, exist_ok=True)
        self.config = config
        self.llm = LLMClient(config)
        self.gate = PermissionGate(sandbox_root, ("ls", "python3", "ffmpeg", "cat"), confirm, strong_confirm)
        self.registry = Registry()
        for t in (make_files_tools(self.gate) + make_spreadsheet_tools(self.gate)
                  + make_shell_tools(self.gate) + make_search_tools()
                  + make_video_tools(self.gate)):
            self.registry.register(t)
        self.skills = load_skills(Path(__file__).resolve().parent / "skills")
        self.max_tokens = 8192
        self.session_path = sandbox_root / ".session.jsonl" if persist else None
        self.file_index = build_index(sandbox_root)
        if persist and self.session_path is not None and self.session_path.exists():
            self.session = Session.load(self.session_path)
        else:
            self.session = Session(build_system_prompt(self.skills, file_index=self.file_index), self.session_path)

    def clear(self):
        self.session = Session(build_system_prompt(self.skills, file_index=self.file_index), self.session_path)
        if self.session_path is not None:
            self.session.save()

    def _summarize(self, text: str) -> str:
        try:
            r = self.llm.chat([{"role": "system", "content": "把以下对话压缩成要点摘要，保留关键事实"},
                               {"role": "user", "content": text}])
            return r.content or ""
        except Exception:  # noqa: BLE001
            return ""

    def _route_model(self, user_input: str) -> str | None:
        # None 表示用默认 chat 模型；命中的话用 provider 的 reasoner 模型
        if should_use_reasoner(user_input) and self.config.reasoner_model:
            return self.config.reasoner_model
        return None

    def run(self, user_input: str) -> str:
        self.session.add("user", user_input)
        model = self._route_model(user_input)
        for _ in range(20):  # 最多 20 轮工具调用
            self.session.maybe_compress(self._summarize, max_tokens=self.max_tokens)
            result = self.llm.chat(self.session.to_messages(), self.registry.schemas(), model=model)
            if result.tool_calls:
                self.session.add("assistant", result.content or "",
                                 tool_calls=[{"id": tc.id, "type": "function",
                                              "function": {"name": tc.name,
                                                           "arguments": json.dumps(tc.arguments, ensure_ascii=False)}}
                                             for tc in result.tool_calls])
                for tc in result.tool_calls:
                    try:
                        out = self.registry.run(tc.name, tc.arguments)
                    except Exception as e:  # noqa: BLE001
                        out = f"工具执行出错：{e}"
                    self.session.add("tool", f"[{tc.name}] {out}", tool_call_id=tc.id)
                    self.session.save()
                continue
            if result.content:
                self.session.add("assistant", result.content)
                self.session.save()
                return result.content
            return "（无输出）"
        return "（达到最大工具轮数）"


def _prompt(text: str) -> str:
    """提示符与读取分开：a-Shell 不保证 input(prompt) 的提示会被 flush 出来。"""
    sys.stdout.write(text)
    sys.stdout.flush()
    return input()


def _ask(prompt: str) -> bool:
    return _prompt(prompt).strip().lower() in ("y", "yes", "是")


if __name__ == "__main__":
    # a-Shell 的 stdin 不是普通 fd（ios_system 经 WKWebView 桥接），reconfigure 会
    # 重建 TextIOWrapper 并切断输入管道，导致第一次 input() 就再也收不到按键。
    # 仅在编码确实不是 UTF-8 时才尝试（Windows 控制台），失败也不致命。
    for _stream in (sys.stdin, sys.stdout):
        try:
            if (getattr(_stream, "encoding", "") or "").lower().replace("-", "") != "utf8":
                _stream.reconfigure(encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass

    load_dotenv()
    cfg = load_llm_config()

    args = sys.argv[1:]
    auto_yes = "--yes" in args or "-y" in args
    args = [a for a in args if a not in ("--yes", "-y")]

    if auto_yes:
        confirm = strong_confirm = lambda m: True
    elif args:
        # 单次模式（未 --yes）：默认拒绝写/删/shell，只允许读，避免在无交互键盘的环境卡在 input()
        confirm = strong_confirm = lambda m: False
    else:
        confirm = strong_confirm = _ask

    agent = Agent(cfg, Path("workspace"), confirm=confirm, strong_confirm=strong_confirm,
                  persist=not bool(args))

    if args:
        print(agent.run(" ".join(args)), flush=True)
    else:
        print("输入 /quit 或 /exit 退出；/clear 清空会话。", flush=True)
        while True:
            try:
                u = _prompt("你 > ")
            except EOFError:
                break
            if u.strip().lower() in ("/quit", "/exit"):
                break
            if u.strip().lower() in ("/clear", "/reset"):
                agent.clear()
                print("会话已清空", flush=True)
                continue
            print(agent.run(u), flush=True)
