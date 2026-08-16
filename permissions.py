from pathlib import Path
from typing import Callable

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

    def shell(self, command: str) -> bool:
        head = command.strip().split(" ", 1)[0]
        if head not in self.shell_allowlist:
            return False
        return self.confirm(f"确认执行命令：{command}？")
