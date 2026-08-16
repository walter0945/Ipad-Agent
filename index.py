"""本地文件索引：扫描沙盒目录，生成紧凑文件清单，供注入 system prompt 或刷新查询。

跳过隐藏文件、__pycache__ 与密钥文件（.env/.pem/.key/.p12/id_rsa/credentials）。
"""

from pathlib import Path

SECRET_TOKENS = (".env", ".pem", ".key", ".p12", "id_rsa", "credentials")
MAX_ENTRIES = 200


def _is_secret(path: Path) -> bool:
    lowered = [p.lower() for p in path.parts]
    return any(t in lowered for t in SECRET_TOKENS)


def _is_ignored(name: str) -> bool:
    return name.startswith(".") or name == "__pycache__"


def build_index(root: Path) -> str:
    if not root.exists():
        return "（沙盒目录为空）"
    lines = []
    for p in sorted(root.rglob("*")):
        if _is_ignored(p.name) or _is_secret(p):
            continue
        if p.is_file():
            rel = p.relative_to(root).as_posix()
            try:
                size = p.stat().st_size
            except OSError:
                size = 0
            lines.append(f"{rel}  ({size} bytes)")
        if len(lines) >= MAX_ENTRIES:
            lines.append("…（更多文件已省略）")
            break
    return "\n".join(lines) if lines else "（沙盒目录为空）"
