# -*- coding: utf-8 -*-
"""SynthesisAgent — 纯内部综合推理类 Sheet Agent。

适用: 2.9 五看总结, 2.10 SWOT, 2.11 TOPN, 2.12 MEKKO, 2.13 BCG,
      4.4 创新机会, 5.4 风险分析, 7.1 组织架构, 7.2 流程, 10.1 财务预算
逻辑: 无 Web Search。仅获取 depends_on 的前置 Sheet 结果 → 组合成大 Prompt →
      让 LLM 做归纳总结推理。
"""
from __future__ import annotations

from core.json_utils import parse_json
from core.strategic_context import StrategicContext
from agents.base_agent import BaseAgent


class SynthesisAgent(BaseAgent):
    """合成推理 Agent — 纯内部综合，不联网。"""

    def execute(
        self,
        sheet_id: str,
        task: dict,
        context: StrategicContext,
        tool_call_stats: dict | None = None,
        enable_web_search: bool = True,
        verbose: bool = True,
    ) -> dict:
        sheet_name = task["sheet_name"]
        system_prompt = self.build_prompt(task, context)
        user_msg = (
            f"请基于前置依赖的分析结果，综合推理生成【{sheet_name}】的内容。\n"
            f"你不需要联网搜索，仅需基于提供的上下文数据做归纳总结。"
            f"最终输出必须严格按 JSON Schema 格式，每 cell ≥80 字。"
        )

        if verbose:
            print(f"[SynthesisAgent] {sheet_id}: prompt={len(system_prompt)}字")

        final_text = self._call_llm(
            system_prompt, user_msg,
            verbose=verbose,
        )
        result = parse_json(final_text)
        if not result:
            result = {"cells": {}, "notes": "LLM 输出解析失败"}
        return result