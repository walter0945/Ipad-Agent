"""从 GitHub 安装 skill（指令型 SKILL.md 文件）。

支持两种 URL：
- raw 文件链接：https://raw.githubusercontent.com/user/repo/main/SKILL.md
- GitHub 仓库链接：https://github.com/user/repo  （会找根目录的 SKILL.md）
"""

import re
from pathlib import Path
import requests

GITHUB_REPO_RE = re.compile(r"^https?://github\.com/([^/\s]+)/([^/\s]+?)(?:\.git)?/?$")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.S)


def parse_frontmatter(text: str) -> tuple[dict, str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text.strip()
    meta = dict(re.findall(r"(\w+):\s*(.+)", m.group(1)))
    return meta, m.group(2).strip()


def _slugify(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_-]+", "-", text).strip("-").lower()
    return s or "skill"


def fetch_skill_text(url: str) -> str:
    url = url.strip()
    if "raw.githubusercontent.com" in url or url.endswith(".md"):
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        return r.text
    m = GITHUB_REPO_RE.match(url.rstrip("/"))
    if not m:
        raise ValueError(f"无法识别的 URL：{url}")
    repo = f"{m.group(1)}/{m.group(2)}"
    for path in ("SKILL.md", "skill.md"):
        raw = f"https://raw.githubusercontent.com/{repo}/HEAD/{path}"
        try:
            r = requests.get(raw, timeout=30)
            if r.status_code == 200:
                return r.text
        except requests.RequestException:
            continue
    raise ValueError("该仓库根目录没有 SKILL.md（可能不是 skill 仓库，而是普通代码项目）")


def install_skill(url: str, skills_dir: Path) -> str:
    text = fetch_skill_text(url)
    meta, _ = parse_frontmatter(text)
    name = meta.get("name") or _slugify(url.rstrip("/").split("/")[-1].replace(".md", ""))
    target = skills_dir / name
    target.mkdir(parents=True, exist_ok=True)
    (target / "SKILL.md").write_text(text, encoding="utf-8")
    desc = meta.get("description", "")
    return f"已安装 skill：{name}" + (f"（{desc}）" if desc else "")
