"""跨 App 桥接工具：经 iOS Shortcuts / URL scheme 触发其它 App 的动作。

iOS 沙盒禁止直接操纵其它 App，但允许经系统的公开通道「请求」它们：
- run_shortcut：调用「捷径」App 里的一个捷径，捷径内部可驱动大量 App（App Intents / 内置动作 / 对方 URL scheme）。
- open_url：用系统 `open` 打开任意 URL 或 app scheme（shortcuts://、mailto:、某 App 的自定义 scheme…）。

两者都是「发起请求」，不是「控制进程」——沙盒完好，能力经正规接口取得。
`open` 命令由 a-Shell 提供；非 iOS/a-Shell 环境（如 Windows 开发机）会优雅报错。
"""

import subprocess
import urllib.parse
from tools import Tool


def _open(url: str, cwd=None) -> str | None:
    """调用系统 open；成功返回 None，失败返回错误说明。"""
    try:
        subprocess.run(["open", url], timeout=15, cwd=cwd)
        return None
    except (FileNotFoundError, OSError) as e:
        return f"无法调用 open（本机可能不是 iOS/a-Shell）：{e}"


def make_shortcuts_tools(gate) -> list[Tool]:
    def run_shortcut(args):
        name = args["name"]
        if not gate.confirm(f"确认触发捷径「{name}」（可能驱动其它 App）？"):
            return "拒绝：未确认"
        params = {"name": name}
        if args.get("input"):
            params["input"] = "text"
            params["text"] = args["input"]
        url = "shortcuts://run-shortcut?" + urllib.parse.urlencode(params)
        err = _open(url, cwd=str(gate.sandbox_root))
        return err or f"已触发捷径「{name}」"

    def open_url(args):
        url = args["url"]
        if not gate.confirm(f"确认打开 URL：{url}？"):
            return "拒绝：未确认"
        err = _open(url)
        return err or f"已打开 {url}"

    return [
        Tool("run_shortcut",
             "调用一个 iOS 捷径（Shortcuts）以驱动其它 App。name=捷径名；input=可选文本输入。"
             "适合发消息、存相册、记事项、触发第三方 App 已暴露的动作。",
             {"type": "object", "properties": {
                 "name": {"type": "string"},
                 "input": {"type": "string"}},
              "required": ["name"]},
             run_shortcut),
        Tool("open_url",
             "用系统 open 打开一个 URL 或 App scheme（如 shortcuts://、mailto:、某 App 的自定义 scheme）。",
             {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
             open_url),
    ]
