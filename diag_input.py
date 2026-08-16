"""a-Shell 输入分诊：逐级加压，看键盘在第几步死掉。

用法（在 a-Shell 干净新窗口里）：
    python3 diag_input.py

每一步都要求你敲一个字符再回车。哪一步开始敲不进去，就是那一步的元凶。
"""
import sys

def step(n: int, what: str) -> None:
    sys.stdout.write(f"\n[{n}] {what}\n> ")
    sys.stdout.flush()
    got = input()
    print(f"    OK，收到: {got!r}", flush=True)


print("=== a-Shell 输入分诊 ===", flush=True)

step(1, "裸 input()（基线：这步就失败 = a-Shell #567，与本项目无关）")

try:
    sys.stdout.reconfigure(encoding="utf-8")
    print("    stdout.reconfigure 成功", flush=True)
except Exception as e:  # noqa: BLE001
    print(f"    stdout.reconfigure 失败: {e!r}", flush=True)
step(2, "stdout.reconfigure 之后")

try:
    sys.stdin.reconfigure(encoding="utf-8")
    print("    stdin.reconfigure 成功", flush=True)
except Exception as e:  # noqa: BLE001
    print(f"    stdin.reconfigure 失败: {e!r}", flush=True)
step(3, "stdin.reconfigure 之后（嫌疑 1：原 agent.py:88）")

try:
    from rich.console import Console
    c = Console()
    print("    rich Console 构造成功", flush=True)
    step(4, "rich Console() 构造之后（嫌疑 2）")
    c.print("[bold]rich 输出一行[/bold]")
    step(5, "rich console.print 之后")
except ImportError:
    print("\n[4-5] 跳过：rich 未安装（这正是我们想要的状态）", flush=True)

print("\n=== 全部通过，输入链路正常 ===", flush=True)
