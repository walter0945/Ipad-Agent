import re
from pathlib import Path
from typing import Callable

# 命令/代码里出现的绝对路径：unix /... 或 Windows 盘符 X:\ / X:/
# 前导可为行首/空白/引号/括号/逗号/等号（覆盖 shell 参数与代码字面量 open('/...') 两种形态）。
# 紧跟 / 的必须是路径字符（排除 " / "、URL 中的 "//"），避免误伤除法和 https://。
_ABS_PATH = re.compile(r"""(?:^|[\s'"(,=])(?:/[^\s'")/]|[A-Za-z]:[\\/])""")

class PermissionGate:
    def __init__(self, sandbox_root: Path, shell_allowlist: tuple[str, ...],
                 confirm: Callable[[str], bool], strong_confirm: Callable[[str], bool]):
        self.sandbox_root = sandbox_root.resolve()
        self.shell_allowlist = shell_allowlist
        self.confirm = confirm
        self.strong_confirm = strong_confirm

    def is_within_root(self, path: Path) -> bool:
        try:
            self.sandbox_root.joinpath(path).resolve().relative_to(self.sandbox_root)
            return True
        except ValueError:
            return False

    _SECRET_TOKENS = (".env", ".pem", ".key", ".p12", "id_rsa", "credentials")

    def _is_secret(self, path: Path) -> bool:
        parts = [str(seg).lower() for seg in path.parts]
        return any(any(tok in seg for tok in self._SECRET_TOKENS) for seg in parts)

    def read(self, path: Path) -> bool:
        if self._is_secret(path):
            return False
        return self.is_within_root(path)

    def write(self, path: Path) -> bool:
        if self._is_secret(path):
            return False
        return self.is_within_root(path) and self.confirm(f"确认写入 {path}？")

    def overwrite(self, path: Path) -> bool:
        return self.is_within_root(path) and not self._is_secret(path) \
            and self.strong_confirm(f"⚠️ 确认覆盖 {path}？此操作不可撤销")

    def delete(self, path: Path) -> bool:
        if self._is_secret(path):
            return False
        return self.is_within_root(path) and self.strong_confirm(f"⚠️ 确认删除 {path}？此操作不可撤销")

    def _touches_forbidden(self, text: str) -> bool:
        """命令行/代码里是否触碰密钥文件、路径穿越或绝对路径。

        注意：这是启发式的「防手滑 + 知情同意」层，不是硬隔离——
        动态拼接的路径仍可能绕过。真正的保护是把命令/代码展示给用户确认。
        """
        low = text.lower()
        if any(tok in low for tok in self._SECRET_TOKENS):
            return True
        if ".." in text:
            return True
        return bool(_ABS_PATH.search(text))

    def shell(self, command: str) -> bool:
        head = command.strip().split(" ", 1)[0]
        if head not in self.shell_allowlist:
            return False
        if self._touches_forbidden(command):
            return False
        return self.confirm(f"确认执行命令：{command}？")

    def python(self, code: str) -> bool:
        # 任意 Python 代码风险等同 shell：需在白名单、过密钥/越界扫描、并把代码原文交由强确认。
        if "python3" not in self.shell_allowlist:
            return False
        if self._touches_forbidden(code):
            return False
        preview = code if len(code) <= 300 else code[:300] + "…"
        return self.strong_confirm(f"⚠️ 确认执行以下 Python 代码？\n{preview}")
