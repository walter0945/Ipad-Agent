from dataclasses import dataclass
from typing import Callable

@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    func: Callable[[dict], str]

class Registry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def schemas(self) -> list[dict]:
        return [{"type": "function", "function": {"name": t.name, "description": t.description,
                                                  "parameters": t.parameters}}
                for t in self._tools.values()]

    def run(self, name: str, arguments: dict) -> str:
        if name not in self._tools:
            raise KeyError(f"未知工具: {name}")
        return self._tools[name].func(arguments)
