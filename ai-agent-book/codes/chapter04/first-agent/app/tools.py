from datetime import date
from typing import Any, Callable

from pydantic import BaseModel, ConfigDict, Field


class AddArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    a: int = Field(description="第一个整数")
    b: int = Field(description="第二个整数")


class DateArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")


def add(a: int, b: int) -> int:
    return a + b


def get_current_date() -> str:
    return date.today().isoformat()


class Tool:
    def __init__(
        self,
        name: str,
        description: str,
        args_model: type[BaseModel],
        function: Callable[..., Any],
    ):
        self.name = name
        self.description = description
        self.args_model = args_model
        self.function = function

    def execute(self, arguments: dict[str, Any]) -> Any:
        # 在执行前验证参数
        args = self.args_model.model_validate(arguments)

        # 只调用经过注册的函数
        return self.function(**args.model_dump())


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool):
        if tool.name in self._tools:
            raise ValueError(f"工具重复注册: {tool.name}")

        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise ValueError(f"未知工具: {name}")

        return self._tools[name]

    def definitions(self) -> list[dict]:
        result = []

        for tool in self._tools.values():
            schema = tool.args_model.model_json_schema()

            result.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": schema,
                },
            })

        return result


def build_registry() -> ToolRegistry:
    registry = ToolRegistry()

    registry.register(
        Tool(
            name="add",
            description="计算两个整数的和",
            args_model=AddArgs,
            function=add,
        )
    )

    registry.register(
        Tool(
            name="get_current_date",
            description="获取运行环境当前日期",
            args_model=DateArgs,
            function=get_current_date,
        )
    )

    return registry