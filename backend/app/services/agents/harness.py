"""
Agent Harness —— 工具执行环境（Tool Execution Harness）

把模型可调用的「工具」统一抽象为 BaseTool，并通过 ToolRegistry 集中管理；
AgentHarness 负责：查找工具、执行、重试/回退、记录执行轨迹、缓存结构化结果。

设计原则：
  - 工具 = {name, description, args_schema, func|coroutine}
  - 同步工具（GPU 推理 / 网络调用）自动丢进 asyncio.to_thread，避免阻塞事件循环
  - 执行失败自动重试，最终仍失败则返回可读的 error 观察结果（绝不抛崩整个 loop）
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable, Dict, List, Optional, Type

from pydantic import BaseModel
from langchain_core.tools import StructuredTool

logger = logging.getLogger(__name__)


class BaseTool:
    """统一的工具抽象。func（同步）与 coroutine（异步）二选一。"""

    def __init__(
        self,
        name: str,
        description: str,
        args_schema: Type[BaseModel],
        func: Optional[Callable[..., Any]] = None,
        coroutine: Optional[Callable[..., Any]] = None,
    ) -> None:
        self.name = name
        self.description = description
        self.args_schema = args_schema
        self.func = func
        self.coroutine = coroutine

    async def run(self, args: Dict[str, Any]) -> Any:
        """统一入口：异步工具直接 await，同步工具丢线程池执行。"""
        if self.coroutine is not None:
            return await self.coroutine(**args)
        if self.func is not None:
            return await asyncio.to_thread(self.func, **args)
        raise NotImplementedError(f"工具 {self.name} 未绑定任何可执行函数")

    def to_langchain(self) -> StructuredTool:
        """转换为 LangChain StructuredTool，供 Gemini bind_tools 生成 function schema。"""
        kwargs: Dict[str, Any] = dict(
            name=self.name,
            description=self.description,
            args_schema=self.args_schema,
        )
        if self.coroutine is not None:
            kwargs["coroutine"] = self.coroutine
        else:
            kwargs["func"] = self.func
        return StructuredTool.from_function(**kwargs)


class ToolRegistry:
    """工具注册表：按 name 索引全部可调用工具。"""

    def __init__(self) -> None:
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> BaseTool:
        self._tools[tool.name] = tool
        return tool

    def get(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def all(self) -> List[BaseTool]:
        return list(self._tools.values())

    def langchain_tools(self) -> List[StructuredTool]:
        return [tool.to_langchain() for tool in self.all()]


class AgentHarness:
    """工具执行环境：执行 + 重试 + 轨迹 + 结构化结果缓存。"""

    def __init__(self, registry: ToolRegistry, max_retries: int = 1) -> None:
        self.registry = registry
        self.max_retries = max_retries
        # 对话 / 观察的记忆存储（供 loop 与下游报告读取）
        self.execution_log: List[Dict[str, Any]] = []
        self.observations: Dict[str, Any] = {}

    async def execute(self, name: str, arguments: Dict[str, Any]) -> str:
        """执行单个工具调用，返回可回传给模型的观察字符串（JSON）。"""
        tool = self.registry.get(name)
        if tool is None:
            return json.dumps({"error": f"Unknown tool: {name}"}, ensure_ascii=False)

        last_err: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                result = await tool.run(arguments)
                # 结构化结果先缓存，供后续组件（报告生成）直接复用。
                self.observations[name] = result
                self.execution_log.append(
                    {"tool": name, "arguments": arguments, "ok": True}
                )
                if isinstance(result, str):
                    return result
                return json.dumps(result, ensure_ascii=False, default=str)
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                logger.warning(
                    "工具 %s 执行失败（第 %d/%d 次）：%s",
                    name, attempt + 1, self.max_retries + 1, exc,
                )

        self.execution_log.append(
            {"tool": name, "arguments": arguments, "ok": False, "error": str(last_err)}
        )
        return json.dumps(
            {"error": f"Tool {name} failed after {self.max_retries + 1} attempts: {last_err}"},
            ensure_ascii=False,
        )