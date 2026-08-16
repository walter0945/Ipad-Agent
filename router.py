"""混合路由：判断一条用户输入是否应走 reasoner（推理）模型。

v1.1 用保守的关键词启发式：命中推理类词汇才切 reasoner，否则走默认 chat。
后续可换成轻量 LLM 分类器，接口保持不变。
"""

REASONING_HINTS = (
    "为什么", "分析", "对比", "推理", "规划", "方案", "评估",
    "权衡", "论证", "推导", "证明", "利弊", "根源", "成因",
    "why", "analyze", "analyse", "compare", "explain", "reason",
    "plan", "design", "trade", "prove",
)


def should_use_reasoner(text: str) -> bool:
    t = (text or "").lower()
    return any(h in t for h in REASONING_HINTS)
