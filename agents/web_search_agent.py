# -*- coding: utf-8 -*-
"""WebSearchAgent — 联网搜索类 Sheet Agent。

适用: 2.1 PESTEL, 2.2 行业趋势, 2.3 市场容量, 2.4 客户需求, 2.6 竞品分析
逻辑: 提取 Context 和 MCP 字段 → 构建搜索 Query → 执行 Web Search →
      对搜索结果做摘要 → 结合前置依赖交给 LLM 生成 JSON。
"""
from __future__ import annotations

from core.json_utils import parse_json
from core.agent_utils import make_counting_wrapper
from core.strategic_context import StrategicContext
from agents.base_agent import BaseAgent


class WebSearchAgent(BaseAgent):
    """联网搜索 Agent — 可调用 web_search 工具获取最新数据。"""

    def execute(
        self,
        sheet_id: str,
        task: dict,
        context: StrategicContext,
        tool_call_stats: dict | None = None,
        enable_web_search: bool = True,
        verbose: bool = True,
    ) -> dict:
        from models import websearch

        sheet_name = task["sheet_name"]
        system_prompt = self.build_prompt(task, context)
        user_msg = (
            f"请生成【{sheet_name}】的内容。\n"
            f"你可以使用 web_search 工具搜索与 '{sheet_name}' 相关的最新数据、报告和政策。"
            f"每次搜索后评估信息是否充分，不足则继续搜索。"
            f"最终输出必须严格按 JSON Schema 格式，每 cell ≥80 字。"
        )

        # 构建工具
        if enable_web_search:
            tool_map = {}
            stats = tool_call_stats or {}
            for name, fn in websearch.TOOL_MAP.items():
                tool_map[name] = make_counting_wrapper(name, fn, stats)
            tools_schema = [websearch.WEB_SEARCH_TOOL_SCHEMA["function"]]
            max_turns = 12
        else:
            tool_map = {}
            tools_schema = []
            max_turns = 2

        if verbose:
            print(f"[WebSearchAgent] {sheet_id}: prompt={len(system_prompt)}字, "
                  f"web_search={'on' if enable_web_search else 'off'}")

        final_text = self._call_llm(
            system_prompt, user_msg,
            tools_schema=tools_schema,
            tool_map=tool_map,
            max_turns=max_turns,
            verbose=verbose,
        )
        result = parse_json(final_text)
        if not result:
            result = {"cells": {}, "notes": "LLM 输出解析失败"}
        return result