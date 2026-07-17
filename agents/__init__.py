# -*- coding: utf-8 -*-
"""Agent 注册表 — 3 类 Agent 的工厂入口。"""
from agents.base_agent import BaseAgent
from agents.web_search_agent import WebSearchAgent
from agents.synthesis_agent import SynthesisAgent
from agents.strategy_agent import StrategyAgent


# Agent 类型 → 类映射
AGENT_REGISTRY: dict[str, type[BaseAgent]] = {
    "web_search": WebSearchAgent,
    "synthesis": SynthesisAgent,
    "strategy": StrategyAgent,
}


def make_agent(agent_type: str, llm_client=None, prompts_module=None) -> BaseAgent:
    """工厂函数: 根据 agent_type 创建 Agent 实例。

    Args:
        agent_type: "web_search" | "synthesis" | "strategy"
        llm_client: 注入的 LLM 客户端
        prompts_module: 注入的 prompts 模块

    Returns:
        BaseAgent 子类实例

    Raises:
        ValueError: 未知的 agent_type
    """
    agent_cls = AGENT_REGISTRY.get(agent_type)
    if agent_cls is None:
        raise ValueError(f"未知 agent_type: {agent_type!r}, 可选: {list(AGENT_REGISTRY.keys())}")
    return agent_cls(llm_client=llm_client, prompts_module=prompts_module)


__all__ = [
    "BaseAgent",
    "WebSearchAgent",
    "SynthesisAgent",
    "StrategyAgent",
    "AGENT_REGISTRY",
    "make_agent",
]