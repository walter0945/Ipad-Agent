"""混合路由：判断一条用户输入是否应走 reasoner（推理）模型。

v1.1 用保守的关键词启发式：命中推理类词汇才切 reasoner，否则走默认 chat。
- 中文命中用子串（中文无词边界）。
- 英文命中用词边界，避免 "plan" 命中 "airplane"、"reason" 命中 "seasoning"。
后续可换成轻量 LLM 分类器，接口保持不变。
"""

import re

CJK_HINTS = (
    "为什么", "分析", "对比", "推理", "规划", "方案", "评估",
    "权衡", "论证", "推导", "证明", "利弊", "根源", "成因",
)
EN_HINTS = (
    "why", "analyze", "analyse", "compare", "explain", "reason",
    "plan", "design", "trade", "prove",
)
_EN_RE = re.compile(r"\b(?:" + "|".join(EN_HINTS) + r")\b")


def should_use_reasoner(text: str) -> bool:
    t = (text or "").lower()
    if any(h in t for h in CJK_HINTS):
        return True
    return bool(_EN_RE.search(t))
