# -*- coding: utf-8 -*-
"""Strategic Context — 全局上下文对象，管理 MCP 数据和 Sheet 生成结果。

Agent 不允许直接调 MCP，必须通过本模块获取数据。
每个 Sheet 的生成结果也存入 sheet_results，供后续依赖 sheet 的 prompt 构建。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class StrategicContext:
    """结构化战略上下文 — Agent 的单一数据来源。

    mcp_data: 系统启动时一次性载入的所有 MCP 数据（原 strategy_2025）
    sheet_results: 每个 Sheet 生成后存入的 JSON 结果（新）
    其余字段由 StrategyContextBuilder.build() 填充。

    Agent 只读，不修改。
    """
    mcp_data: dict[str, Any] = field(default_factory=dict)
    sheet_results: dict[str, Any] = field(default_factory=dict)
    company_profile: dict = field(default_factory=dict)
    financial_summary: dict = field(default_factory=dict)
    project_summary: dict = field(default_factory=dict)
    kpi_summary: dict = field(default_factory=dict)
    historical_summary: dict = field(default_factory=dict)
    dim_info: str = "c"
    year: str = "2025"
    available_tables: list = field(default_factory=list)


class StrategyContextBuilder:
    """统一 MCP 数据入口 + 依赖提取。

    Usage:
        builder = StrategyContextBuilder(dim_info="c", year="2025")
        ctx = builder.build()
        # 或只拉指定表
        ctx = builder.build(target_tables=["2.2 行业趋势分析", "2.10 SWOT分析"])
        # 提取依赖
        deps = ctx.get_dependencies("2.9", task_config)
    """

    def __init__(self, dim_info: str = "c", year: str = "2025"):
        self.dim_info = dim_info
        self.year = year
        self._cache: dict = {}
        self._built = False

    def build(self, target_tables: list[str] | None = None) -> StrategicContext:
        """完整构建：dimension -> menu -> 拉表 -> 结构化 -> 返回 Context。

        调用链：
            sp_dimension() -> sp_data_menu(dim) -> 对每个 target_table 调 sp_data()
            结果缓存到 self._cache，避免重复拉取。

        Args:
            target_tables: 只拉指定表名（None = 拉全部可用表）。
        """
        if self._built and self._cache.get("_context"):
            return self._cache["_context"]

        from models import idste

        ctx = StrategicContext(dim_info=self.dim_info, year=self.year)

        # 1) 团队信息
        try:
            ctx.company_profile = idste.sp_team_info() or {}
        except Exception:
            ctx.company_profile = {}

        # 2) dimension + menu
        try:
            dim_resp = idste.sp_dimension()
            if isinstance(dim_resp, str):
                ctx.dim_info = dim_resp
            elif isinstance(dim_resp, list) and dim_resp:
                first = dim_resp[0]
                ctx.dim_info = first if isinstance(first, str) else (
                    first.get("dim_info") or first.get("id") or "c"
                )
        except Exception:
            pass

        try:
            menu = idste.sp_data_menu(ctx.dim_info)
            ctx.available_tables = idste._find_table_keys(menu)
        except Exception:
            ctx.available_tables = []

        # 3) 拉数据表 → mcp_data
        for tbl_info in ctx.available_tables:
            tk = tbl_info["table_key"]
            name = tbl_info.get("name", tk)
            if target_tables is not None and name not in target_tables:
                matched = any(
                    name.strip().rstrip("表") == t.strip().rstrip("表")
                    for t in target_tables
                )
                if not matched:
                    continue
            try:
                data = idste.sp_data(ctx.dim_info, tk, self.year)
                ctx.mcp_data[name] = data
            except Exception:
                ctx.mcp_data[name] = {"error": f"sp_data 拉取失败: {tk}"}

        # 4) 结构化提取
        ctx.financial_summary = self._extract_financial(ctx)
        ctx.project_summary = self._extract_projects(ctx)
        ctx.kpi_summary = self._extract_kpi(ctx)

        self._cache["_context"] = ctx
        self._built = True
        ctx.historical_summary = self._get_historical_summary()
        return ctx

    # ---- 内部提取 ----
    def _extract_financial(self, ctx: StrategicContext) -> dict:
        result = {}
        for name, data in ctx.mcp_data.items():
            if isinstance(data, dict) and not data.get("error"):
                if any(kw in name for kw in ("财务", "营收", "利润", "收入", "成本")):
                    result[name] = data
        return result

    def _extract_projects(self, ctx: StrategicContext) -> dict:
        result = {}
        for name, data in ctx.mcp_data.items():
            if isinstance(data, dict) and not data.get("error"):
                if any(kw in name for kw in ("项目", "举措", "重点", "计划")):
                    result[name] = data
        return result

    def _extract_kpi(self, ctx: StrategicContext) -> dict:
        result = {}
        for name, data in ctx.mcp_data.items():
            if isinstance(data, dict) and not data.get("error"):
                if any(kw in name for kw in ("KPI", "指标", "目标", "达成")):
                    result[name] = data
        return result

    def _get_historical_summary(self) -> dict:
        if not self._built:
            self.build()
        ctx = self._cache.get("_context")
        if ctx is None:
            return {}
        summary = {
            "kpi_highlights": [],
            "project_status": [],
            "financial_highlights": [],
        }
        for name, data in ctx.kpi_summary.items():
            if isinstance(data, dict):
                summary["kpi_highlights"].append({"source": name, "summary": str(data)[:500]})
        for name, data in ctx.project_summary.items():
            if isinstance(data, dict):
                summary["project_status"].append({"source": name, "summary": str(data)[:500]})
        for name, data in ctx.financial_summary.items():
            if isinstance(data, dict):
                summary["financial_highlights"].append({"source": name, "summary": str(data)[:500]})
        return summary

    # ---- 单 sheet 上下文 ----
    def get_sheet_context(self, sheet_name: str) -> dict:
        """单 sheet 的 MCP 数据，从缓存或按需拉取。"""
        if not self._built:
            self.build()
        ctx = self._cache.get("_context")
        if ctx is None:
            return {}
        for name, data in ctx.mcp_data.items():
            if name.strip().rstrip("表") == sheet_name.strip().rstrip("表"):
                return data
            if sheet_name.strip().rstrip("表") in name or name in sheet_name:
                return data
        return {}


def get_dependencies(ctx: StrategicContext, sheet_id: str,
                     task_config: dict | None = None) -> dict:
    """根据 YAML 配置，返回该 Sheet 所需的前置 Sheet 结果。

    对每个前置 sheet_id:
    - 如果已生成，取 sheet_results[sheet_id]
    - 未生成时跳过（标记为 pending）

    如果依赖的 sheet 过多（>8 个），对每个前置结果做简单摘要：
    - 提取 notes 字段
    - cells 截断到前 200 字

    Args:
        ctx: 全局上下文
        sheet_id: 当前 sheet 的 ID
        task_config: 当前 sheet 的 YAML 任务配置（含 depends_on 列表）

    Returns:
        {
            "predecessors": {
                "2.1": {"notes": "...", "cells_summary": "B4: ... B5: ..."},
                ...
            },
            "summary_text": "前置结果摘要文本（给 LLM prompt 用）",
            "pending": ["3.1"]  # 未生成的前置 sheet
        }
    """
    depends_on = task_config.get("depends_on", []) if task_config else []
    if not depends_on:
        return {"predecessors": {}, "summary_text": "", "pending": []}

    predecessors = {}
    pending = []
    for dep_id in depends_on:
        if dep_id in ctx.sheet_results:
            result = ctx.sheet_results[dep_id]
            # 摘要
            summary = {
                "notes": str(result.get("notes", ""))[:300],
            }
            if "cells" in result:
                cells = result["cells"]
                cells_str = "; ".join(
                    f"{k}: {str(v)[:80]}" for k, v in list(cells.items())[:8]
                )
                summary["cells_summary"] = cells_str[:500]
            elif "rows" in result:
                # 结构化输出（如 PESTELOutput）
                rows = result.get("rows", [])
                summary["rows_count"] = len(rows)
                summary["rows_preview"] = str(rows[:3])[:300]
            predecessors[dep_id] = summary
        else:
            pending.append(dep_id)

    # 构建摘要文本
    parts = []
    for dep_id, summary in predecessors.items():
        dep_name = dep_id
        if task_config:
            # 尝试从 YAML 找依赖 sheet 的名称
            pass
        entry = f"【{dep_id}】"
        if summary.get("notes"):
            entry += f"\n  推理摘要: {summary['notes']}"
        if summary.get("cells_summary"):
            entry += f"\n  数据: {summary['cells_summary']}"
        if summary.get("rows_count"):
            entry += f"\n  行数: {summary['rows_count']}, 预览: {summary.get('rows_preview', '')}"
        parts.append(entry)

    summary_text = "\n\n".join(parts) if parts else ""

    return {
        "predecessors": predecessors,
        "summary_text": summary_text,
        "pending": pending,
    }