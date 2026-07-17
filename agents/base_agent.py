# -*- coding: utf-8 -*-
"""Base Agent — 封装 LLM 调用逻辑和 5 段式 Prompt 构建。

Blueprint §四 Step 4.1: Prompt 必须包含 5 个部分:
    Role, Task Description, Context, Output Format, Output Schema
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

from core.json_utils import parse_json
from core.strategic_context import StrategicContext, get_dependencies
from schemas import get_schema_for_sheet, CellMapOutput


class BaseAgent(ABC):
    """Agent 基类 — 子类只需实现 execute()。

    Args:
        llm_client: LLM 模块（默认 models.llm）
        prompts_module: prompts 模块（默认 models.prompts）
    """

    def __init__(self, llm_client=None, prompts_module=None):
        if llm_client is None:
            from models import llm as _llm
            llm_client = _llm
        if prompts_module is None:
            from models import prompts as _prompts
            prompts_module = _prompts
        self.llm = llm_client
        self.prompts = prompts_module

    @abstractmethod
    def execute(
        self,
        sheet_id: str,
        task: dict,
        context: StrategicContext,
        tool_call_stats: dict | None = None,
        enable_web_search: bool = True,
        verbose: bool = True,
    ) -> dict:
        """执行 Agent 推理，返回 JSON dict。

        Returns:
            dict: 需符合 schema_class 格式（如 {"cells": {"B4": "...", ...}, "notes": "..."}）
        """
        ...

    # ---- 5 段式 Prompt 构建 ----
    def build_prompt(self, task: dict, context: StrategicContext) -> str:
        """构建 5 段式 Prompt。

        1. Role
        2. Task Description
        3. Context (前置依赖 + MCP slice)
        4. Output Format
        5. Output Schema
        """
        sheet_id = task["sheet_id"]
        sheet_name = task["sheet_name"]
        agent_type = task.get("agent_type", "synthesis")
        description = task.get("description", sheet_name)
        process_hint = task.get("process_hint", "")

        # 1) Role
        role = self._build_role_section(agent_type)

        # 2) Task
        task_section = self._build_task_section(sheet_name, description, process_hint)

        # 3) Context
        deps = get_dependencies(context, sheet_id, task)
        mcp_slice = self._build_mcp_slice(task, context)
        context_section = self._build_context_section(deps, mcp_slice)

        # 4) Output Format
        format_section = self._build_format_section(task)

        # 5) Output Schema
        schema_cls = get_schema_for_sheet(sheet_id)
        schema_json = schema_cls.model_json_schema()
        schema_section = self._build_schema_section(schema_json)

        return f"""{role}

{task_section}

{context_section}

{format_section}

{schema_section}"""

    def _build_role_section(self, agent_type: str) -> str:
        role_map = {
            "web_search": "你是专业的企业战略规划分析师，专长是外部环境扫描与行业趋势分析。"
                         "你能够基于 Web 搜索获取最新信息，结合结构化数据做出专业分析。",
            "synthesis": "你是专业的企业战略规划分析师，专长是综合推理与归纳总结。"
                        "你能够基于多个前置分析结果，提炼出关键洞察和战略方向。",
            "strategy": "你是高级企业战略规划顾问，专长是企业战略设计与决策。"
                      "你能够基于深度推理（Chain of Thought），在复杂业务约束下制定可执行的战略方案。",
        }
        body = role_map.get(agent_type, role_map["synthesis"])
        return f"## 角色\n\n{body}"

    def _build_task_section(self, sheet_name: str, description: str,
                            process_hint: str) -> str:
        lines = [
            "## 任务",
            "",
            f"你需要生成 **{sheet_name}** 的内容。",
            "",
            f"业务目标: {description}",
            "",
        ]
        if process_hint:
            lines.append(f"分析过程指引: {process_hint}")
            lines.append("")
        lines.append("请严格按照下面的「输出格式」和「输出 Schema」生成 JSON。"
                     "输出必须是纯 JSON，不要包含 markdown 代码围栏或其他文字。")
        return "\n".join(lines)

    def _build_context_section(self, deps: dict, mcp_slice: str) -> str:
        lines = ["## 上下文数据"]
        lines.append("")

        # 前置依赖摘要
        if deps.get("summary_text"):
            lines.append("### 前置 Sheet 分析结果")
            lines.append("")
            lines.append(deps["summary_text"])
            lines.append("")

        if deps.get("pending"):
            lines.append(f"### 注意: 以下前置 sheet 尚未生成：{', '.join(deps['pending'])}")
            lines.append("")

        # MCP 数据
        if mcp_slice:
            lines.append("### MCP 2025 基线数据")
            lines.append("")
            lines.append(f"```json\n{mcp_slice}\n```")
            lines.append("")

        return "\n".join(lines)

    def _build_format_section(self, task: dict) -> str:
        lines = [
            "## 输出格式",
            "",
            "请输出以下 JSON 格式:",
            "```json",
            "{",
            '  "cells": {',
            '    "B4": "内容...",',
            '    "B5": "内容...",',
            '    "B6": "内容..."',
            "  },",
            '  "notes": "推理过程摘要（200-500 字）"',
            "}",
            "```",
            "",
            "- cells 的 key 是 Excel 单元格坐标（列字母+行号），value 是对应内容",
            "- 每一行的内容必须 ≥80 字，使用中文",
            "- notes 记录本次推理的关键发现，供后续依赖 sheet 引用",
        ]
        return "\n".join(lines)

    def _build_schema_section(self, schema_json: dict) -> str:
        return (
            "## 输出 Schema\n\n"
            "你的输出必须符合以下 JSON Schema，否则会被拒绝:\n\n"
            "```json\n"
            f"{json.dumps(schema_json, ensure_ascii=False, indent=2)}\n"
            "```"
        )

    def _build_mcp_slice(self, task: dict, context: StrategicContext) -> str:
        """从 context.mcp_data 提取当前 sheet 相关的 MCP 字段。"""
        mcp_fields = task.get("mcp_fields", [])
        if not mcp_fields:
            return ""
        parts = []
        for field in mcp_fields:
            for name, data in context.mcp_data.items():
                if field.strip().rstrip("表") in name or name in field:
                    parts.append(f"// {name}\n{json.dumps(data, ensure_ascii=False, default=str)[:2000]}")
                    break
        return "\n".join(parts)

    # ---- LLM 调用 ----
    def _call_llm(self, system_prompt: str, user_msg: str,
                  tools_schema: list | None = None,
                  tool_map: dict | None = None,
                  max_turns: int = 2,
                  verbose: bool = True) -> str:
        """调 LLM agent loop（有工具时走 agent loop，无工具时直接 chat）。"""
        if tools_schema and tool_map:
            return self.llm.run_agent_loop(
                system_prompt, user_msg,
                tool_map, tools_schema,
                max_turns=max_turns, verbose=verbose,
                max_tokens=2000, final_max_tokens=12288,
                enable_thinking=False, final_enable_thinking=True,
            )
        else:
            resp = self.llm.chat_with_fallback(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                ],
                max_tokens=8000, final_max_tokens=12288,
                verbose=verbose, enable_thinking=True,
            )
            return resp["choices"][0]["message"].get("content") or ""

    # ---- 通用 execute 实现（子类可覆盖） ----
    def execute(
        self,
        sheet_id: str,
        task: dict,
        context: StrategicContext,
        tool_call_stats: dict | None = None,
        enable_web_search: bool = True,
        verbose: bool = True,
    ) -> dict:
        """默认 execute: 构建 prompt → 调 LLM → 解析 JSON。

        子类（WebSearchAgent 等）可覆盖以添加工具。
        """
        system_prompt = self.build_prompt(task, context)
        user_msg = f"请生成【{task['sheet_name']}】的内容。要求: 严格按 JSON Schema 输出，每 cell ≥80 字。"

        if verbose:
            print(f"[{self.__class__.__name__}] {sheet_id}: prompt={len(system_prompt)}字")

        final_text = self._call_llm(
            system_prompt, user_msg,
            verbose=verbose,
        )
        result = parse_json(final_text)

        if not result:
            result = {"cells": {}, "notes": "LLM 输出解析失败"}

        return result