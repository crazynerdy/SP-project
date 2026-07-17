# -*- coding: utf-8 -*-
"""StrategyAgent — 深度战略设计类 Sheet Agent。

适用: 3.2 战略地图, 3.3 公司KPI, 5.1 竞争战略, 5.2 职能平台战略,
      5.3 业务设计, 6.1 战略举措, 6.2 年度目标, 6.3 年度项目
逻辑: 获取前置依赖 + MCP 业务数据 → 启用 Chain of Thought 深度推理 →
      输出结构化战略规划 JSON。
"""
from __future__ import annotations

from core.json_utils import parse_json
from core.strategic_context import StrategicContext
from agents.base_agent import BaseAgent


class StrategyAgent(BaseAgent):
    """战略设计 Agent — CoT 深度推理，thinking 模式全程开启。"""

    def _build_role_section(self, agent_type: str = "strategy") -> str:
        return (
            "## 角色\n\n"
            "你是高级企业战略规划顾问，专长是企业战略设计与决策。"
            "你具备以下能力:\n"
            "- 在复杂业务约束下进行深度推理（Chain of Thought）\n"
            "- 从多个前置分析中提取关键洞察并转化为可执行的战略方案\n"
            "- 平衡战略的雄心与可行性，确保方案可落地\n\n"
            "在生成最终答案前，请先在 notes 中展示你的推理链路（CoT），"
            "然后再生成 cells 数据。"
        )

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
            f"请基于前置依赖的分析结果，进行深度战略推理，生成【{sheet_name}】的内容。\n"
            f"思考步骤:\n"
            f"1. 先梳理前置分析中的关键发现\n"
            f"2. 识别战略约束条件和机会空间\n"
            f"3. 制定具体方案，确保每项 ≥80 字\n"
            f"最终输出必须严格按 JSON Schema 格式。"
        )

        if verbose:
            print(f"[StrategyAgent] {sheet_id}: prompt={len(system_prompt)}字")

        final_text = self._call_llm(
            system_prompt, user_msg,
            verbose=verbose,
        )
        result = parse_json(final_text)
        if not result:
            result = {"cells": {}, "notes": "LLM 输出解析失败"}
        return result