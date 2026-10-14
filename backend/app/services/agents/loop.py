"""
Agent Loop —— ReAct 主循环（Reasoning + Acting）

核心控制流：
  1. 把当前消息（含历史工具观察）发给绑定了工具的 LLM；
  2. 若模型返回 tool_calls，则逐个执行并把观察作为 ToolMessage 追加回消息；
  3. 重复，直到模型不再调用工具（给出最终答案）或达到最大迭代/步数上限。

这是把「固定流水线」升级为「自主 Agent」的关键：模型自己决定
何时、调用哪些工具、调用几次，直到信息充分。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

from langchain_core.messages import ToolMessage

from app.services.agents.harness import AgentHarness

logger = logging.getLogger(__name__)


class AgentLoop:
    def __init__(
        self,
        harness: AgentHarness,
        llm_client: Any,
        max_iterations: int = 8,
        max_tool_steps: int = 16,
    ) -> None:
        self.harness = harness
        self.llm_client = llm_client
        self.max_iterations = max_iterations
        self.max_tool_steps = max_tool_steps

    async def run(self, messages: List[Any]) -> Tuple[List[Any], List[Dict[str, Any]]]:
        """执行 ReAct 循环。返回 (最终消息列表, 步骤轨迹)。"""
        tools = self.harness.registry.langchain_tools()
        steps: List[Dict[str, Any]] = []
        tool_steps_used = 0

        for iteration in range(1, self.max_iterations + 1):
            response = await self.llm_client.invoke_with_tools(messages, tools)
            messages.append(response)

            tool_calls = getattr(response, "tool_calls", None) or []
            if not tool_calls:
                logger.info("循环于第 %d 轮收敛（模型给出最终答案）", iteration)
                break

            for tool_call in tool_calls:
                if tool_steps_used >= self.max_tool_steps:
                    logger.warning("达到最大工具步数上限 %d，强制结束循环", self.max_tool_steps)
                    messages.append(ToolMessage(
                        content="达到最大工具调用步数，请在已有信息基础上直接给出最终结论。",
                        tool_call_id=tool_call.get("id", ""),
                    ))
                    return messages, steps

                name = tool_call.get("name", "")
                arguments = tool_call.get("args", {}) or {}
                observation = await self.harness.execute(name, arguments)
                messages.append(ToolMessage(
                    content=observation,
                    tool_call_id=tool_call.get("id", ""),
                ))
                steps.append({"tool": name, "arguments": arguments})
                tool_steps_used += 1

        return messages, steps