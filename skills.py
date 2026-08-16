import re
from dataclasses import dataclass
from pathlib import Path

@dataclass
class Skill:
    name: str
    description: str
    body: str

_FRONT = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.S)

def load_skills(skills_dir: Path) -> list[Skill]:
    out = []
    if not skills_dir.exists():
        return out
    for md in sorted(skills_dir.glob("*/SKILL.md")):
        text = md.read_text(encoding="utf-8")
        m = _FRONT.match(text)
        if not m:
            continue
        meta = dict(re.findall(r"([\w-]+):\s*(.+)", m.group(1)))
        out.append(Skill(meta.get("name", md.parent.name), meta.get("description", ""), m.group(2).strip()))
    return out
