import re
from pathlib import Path
from index import build_index
from tools import Tool

def _resolve(gate, p: str) -> Path:
    return gate.sandbox_root.joinpath(p).resolve()

def make_files_tools(gate) -> list[Tool]:
    MAX_READ_BYTES = 200 * 1024

    def read_file(args):
        p = _resolve(gate, args["path"])
        if not gate.read(p):
            return "拒绝：路径越界"
        if p.is_dir():
            return "是目录，请用 list_dir"
        if p.stat().st_size > MAX_READ_BYTES:
            return "文件过大"
        start = max(args.get("start", 1), 1)
        end = args.get("end")
        lines = p.read_text(encoding="utf-8").splitlines()
        seg = lines[start - 1:end] if end else lines[start - 1:]
        return "\n".join(seg)

    def write_file(args):
        p = _resolve(gate, args["path"])
        if p.exists():
            if not gate.overwrite(p):
                return "拒绝：未确认覆盖或路径越界"
        elif not gate.write(p):
            return "拒绝：未确认写入或路径越界"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(args["content"], encoding="utf-8")
        return f"已写入 {p.name}"

    def edit_file(args):
        p = _resolve(gate, args["path"])
        if not gate.write(p):
            return "拒绝"
        text = p.read_text(encoding="utf-8")
        if args["old"] not in text:
            return "未找到要替换的文本"
        p.write_text(text.replace(args["old"], args["new"], 1), encoding="utf-8")
        return "已替换"

    def list_dir(args):
        p = _resolve(gate, args.get("path", "."))
        if not gate.read(p):
            return "拒绝"
        return "\n".join(sorted(str(x.relative_to(gate.sandbox_root)) for x in p.iterdir()
                                if not gate._is_secret(x)))

    def grep(args):
        p = _resolve(gate, args.get("path", "."))
        if not gate.read(p):
            return "拒绝"
        pat = re.compile(args["pattern"])
        hits = []
        for f in p.rglob("*") if p.is_dir() else [p]:
            if f.is_file() and not gate._is_secret(f):
                for i, line in enumerate(f.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                    if pat.search(line):
                        hits.append(f"{f.name}:{i}: {line.strip()}")
        return "\n".join(hits[:50])

    def glob(args):
        p = _resolve(gate, ".")
        if not gate.read(p):
            return "拒绝"
        matches = sorted(str(x.relative_to(p)) for x in p.glob(args["pattern"])
                         if not gate._is_secret(x))
        return "\n".join(matches[:100])

    def file_index(args):
        return build_index(gate.sandbox_root)

    return [
        Tool("read_file", "读文件（支持 start/end 行区间）",
             {"type": "object", "properties": {"path": {"type": "string"}, "start": {"type": "integer"}, "end": {"type": "integer"}}, "required": ["path"]}, read_file),
        Tool("write_file", "创建或覆盖文件",
             {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}, write_file),
        Tool("edit_file", "精确查找替换",
             {"type": "object", "properties": {"path": {"type": "string"}, "old": {"type": "string"}, "new": {"type": "string"}}, "required": ["path", "old", "new"]}, edit_file),
        Tool("list_dir", "列出目录", {"type": "object", "properties": {"path": {"type": "string"}}, "required": []}, list_dir),
        Tool("grep", "正则搜索文件内容", {"type": "object", "properties": {"pattern": {"type": "string"}, "path": {"type": "string"}}, "required": ["pattern"]}, grep),
        Tool("glob", "按模式找文件", {"type": "object", "properties": {"pattern": {"type": "string"}}, "required": ["pattern"]}, glob),
        Tool("file_index", "列出沙盒内所有文件（排除隐藏与密钥文件）", {"type": "object", "properties": {}, "required": []}, file_index),
    ]
