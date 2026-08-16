"""从 GitHub 安装 skill（指令型 SKILL.md 文件）。

支持的 URL：
- raw 直链：https://raw.githubusercontent.com/user/repo/HEAD/path/SKILL.md
- blob 页面：https://github.com/user/repo/blob/ref/path/SKILL.md   （自动转 raw）
- 仓库根：  https://github.com/user/repo                          （找根目录 SKILL.md）

注意：只下载单个 SKILL.md 文本，不下载配套文件、不执行任何远程代码。
若正文引用了同目录的其它文件（REFERENCE.md、脚本等），安装后会给出缺失提示。
"""

import re
from pathlib import Path
import requests

GITHUB_REPO_RE = re.compile(r"^https?://github\.com/([^/\s]+)/([^/\s]+?)(?:\.git)?/?$")
GITHUB_BLOB_RE = re.compile(r"^https?://github\.com/([^/\s]+)/([^/\s]+)/blob/(.+)$")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.S)
# 键允许连字符（when-to-use 等），值取到行尾
META_LINE_RE = re.compile(r"([\w-]+):\s*(.+)")
# 正文里引用的同目录配套文件
COMPANION_RE = re.compile(r"[\w./-]+\.(?:md|py|js|sh|json|txt|csv|yaml|yml)")

# 内置 skill 不允许被下载覆盖（否则等于远程改写本地行为）
BUILTIN_SKILLS = {"spreadsheet", "video"}


def parse_frontmatter(text: str) -> tuple[dict, str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text.strip()
    meta = dict(META_LINE_RE.findall(m.group(1)))
    return meta, m.group(2).strip()


def _slugify(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_-]+", "-", text).strip("-").lower()
    return s or "skill"


def _to_raw_url(url: str) -> str:
    """github.com/.../blob/ref/path -> raw.githubusercontent.com/.../ref/path"""
    m = GITHUB_BLOB_RE.match(url.strip())
    if m:
        return f"https://raw.githubusercontent.com/{m.group(1)}/{m.group(2)}/{m.group(3)}"
    return url.strip()


def _get_text(url: str) -> str:
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    text = r.text
    if text.lstrip()[:200].lower().startswith(("<!doctype", "<html")):
        raise ValueError("取回的是 HTML 页面而非 SKILL.md。请用 raw.githubusercontent.com 直链，"
                         "或 github.com/用户/仓库 形式。")
    return text


def fetch_skill_text(url: str) -> str:
    url = _to_raw_url(url)
    if "raw.githubusercontent.com" in url or url.endswith(".md"):
        return _get_text(url)
    m = GITHUB_REPO_RE.match(url.rstrip("/"))
    if not m:
        raise ValueError(f"无法识别的 URL：{url}")
    repo = f"{m.group(1)}/{m.group(2)}"
    for path in ("SKILL.md", "skill.md"):
        raw = f"https://raw.githubusercontent.com/{repo}/HEAD/{path}"
        try:
            r = requests.get(raw, timeout=30)
            if r.status_code == 200:
                return _get_text(raw)
        except requests.RequestException:
            continue
    raise ValueError("该仓库根目录没有 SKILL.md。集合型仓库请直接给某个 skill 的 "
                     "raw/blob 链接（如 .../blob/main/skills/pdf/SKILL.md）。")


def _missing_companions(body: str) -> list[str]:
    refs = {r for r in COMPANION_RE.findall(body) if Path(r).name.lower() != "skill.md"}
    return sorted(refs)


def install_skill(url: str, skills_dir: Path, force: bool = False) -> str:
    text = fetch_skill_text(url)
    meta, body = parse_frontmatter(text)
    name = _slugify(meta.get("name") or url.rstrip("/").split("/")[-1].replace(".md", ""))

    if name in BUILTIN_SKILLS:
        return f"拒绝：{name} 是内置 skill，不允许被远程安装覆盖。"

    skills_dir = skills_dir.resolve()
    target = (skills_dir / name).resolve()
    # 纵深防御：slugify 之后 target 仍必须落在 skills_dir 内
    if target != skills_dir and skills_dir not in target.parents:
        raise ValueError(f"非法 skill 名，路径逃逸：{name}")

    if target.exists() and not force:
        return f"skill「{name}」已存在。确认要覆盖请加 --force。"

    target.mkdir(parents=True, exist_ok=True)
    (target / "SKILL.md").write_text(text, encoding="utf-8")

    desc = meta.get("description", "")
    msg = f"已安装 skill：{name}" + (f"（{desc[:60]}）" if desc else "")
    missing = _missing_companions(body)
    if missing:
        msg += ("\n⚠️ 正文引用了这些配套文件，但本工具只下载 SKILL.md，未包含它们，"
                "该 skill 可能无法完整工作：\n  " + "、".join(missing))
    return msg
