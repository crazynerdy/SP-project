# context/strategy_context_builder.py
# -*- coding: utf-8 -*-
"""Strategy Context Builder - 统一 MCP 数据入口。

Agent 不允许直接调 MCP，必须通过本模块获取数据。
"""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class StrategyContext:
    """结构化战略上下文 - Agent 的单一数据来源。

    所有字段由 StrategyContextBuilder.build() 填充；
    Agent 只读，不修改。
    """
    company_profile: dict = field(default_factory=dict)
    strategy_2025: dict = field(default_factory=dict)
    financial_summary: dict = field(default_factory=dict)
    project_summary: dict = field(default_factory=dict)
    kpi_summary: dict = field(default_factory=dict)
    historical_summary: dict = field(default_factory=dict)
    dim_info: str = "c"
    year: str = "2025"
    available_tables: list = field(default_factory=list)


class StrategyContextBuilder:
    """统一 MCP 数据入口。

    Usage:
        builder = StrategyContextBuilder(dim_info="c", year="2025")
        ctx = builder.build()
        # 或只拉指定表
        ctx = builder.build(target_tables=["2.2 行业趋势分析", "2.10 SWOT分析"])
    """

    def __init__(self, dim_info="c", year="2025"):
        self.dim_info = dim_info
        self.year = year
        self._cache: dict = {}
        self._built = False

    def build(self, target_tables: list[str] | None = None) -> StrategyContext:
        """完整构建：dimension -> menu -> 拉表 -> 结构化 -> 返回 Context。

        调用链：
            sp_dimension() -> sp_data_menu(dim) -> 对每个 target_table 调 sp_data()
            结果缓存到 self._cache，避免重复拉取。

        target_tables: 只拉指定表名（None = 拉全部可用表）。
        """
        if self._built and self._cache.get("_context"):
            return self._cache["_context"]

        from models import idste

        ctx = StrategyContext(dim_info=self.dim_info, year=self.year)

        # 1) 团队信息
        try:
            ctx.company_profile = idste.sp_team_info() or {}
        except Exception:
            ctx.company_profile = {}

        # 2) dimension + menu
        try:
            dim_resp = idste.sp_dimension()
            # 容错多种返回结构
            if isinstance(dim_resp, str):
                ctx.dim_info = dim_resp
            elif isinstance(dim_resp, list) and dim_resp:
                first = dim_resp[0]
                ctx.dim_info = first if isinstance(first, str) else (
                    first.get("dim_info") or first.get("id") or "c"
                )
        except Exception:
            pass  # 保持默认 "c"

        try:
            menu = idste.sp_data_menu(ctx.dim_info)
            ctx.available_tables = idste._find_table_keys(menu)
        except Exception:
            ctx.available_tables = []

        # 3) 拉数据表
        for tbl_info in ctx.available_tables:
            tk = tbl_info["table_key"]
            name = tbl_info.get("name", tk)
            if target_tables is not None and name not in target_tables:
                # 模糊匹配（容错空格/尾"表"字）
                matched = any(
                    name.strip().rstrip("表") == t.strip().rstrip("表")
                    for t in target_tables
                )
                if not matched:
                    continue
            try:
                data = idste.sp_data(ctx.dim_info, tk, self.year)
                ctx.strategy_2025[name] = data
            except Exception:
                ctx.strategy_2025[name] = {"error": f"sp_data 拉取失败: {tk}"}

        # 4) 结构化提取（轻量，非 LLM 推理）
        ctx.financial_summary = self._extract_financial(ctx)
        ctx.project_summary = self._extract_projects(ctx)
        ctx.kpi_summary = self._extract_kpi(ctx)

        # 先缓存并置 _built，再调 get_historical_summary()：
        # 后者会在 _built=False 时重新触发 build()，造成无限递归。
        self._cache["_context"] = ctx
        self._built = True
        ctx.historical_summary = self.get_historical_summary()
        return ctx

    def _extract_financial(self, ctx: StrategyContext) -> dict:
        """从 strategy_2025 中提取财务相关数据。"""
        result = {}
        for name, data in ctx.strategy_2025.items():
            if isinstance(data, dict) and not data.get("error"):
                # 查找含"财务"/"营收"/"利润"的表
                if any(kw in name for kw in ("财务", "营收", "利润", "收入", "成本")):
                    result[name] = data
        return result

    def _extract_projects(self, ctx: StrategyContext) -> dict:
        """从 strategy_2025 中提取项目/举措相关数据。"""
        result = {}
        for name, data in ctx.strategy_2025.items():
            if isinstance(data, dict) and not data.get("error"):
                if any(kw in name for kw in ("项目", "举措", "重点", "计划")):
                    result[name] = data
        return result

    def _extract_kpi(self, ctx: StrategyContext) -> dict:
        """从 strategy_2025 中提取 KPI 相关数据。"""
        result = {}
        for name, data in ctx.strategy_2025.items():
            if isinstance(data, dict) and not data.get("error"):
                if any(kw in name for kw in ("KPI", "指标", "目标", "达成")):
                    result[name] = data
        return result

    def get_sheet_context(self, sheet_name: str) -> dict:
        """单 sheet 上下文。从缓存或按需拉取。"""
        if not self._built:
            self.build()
        ctx = self._cache.get("_context")
        if ctx is None:
            return {}
        # 模糊匹配
        for name, data in ctx.strategy_2025.items():
            if name.strip().rstrip("表") == sheet_name.strip().rstrip("表"):
                return data
            if sheet_name.strip().rstrip("表") in name or name in sheet_name:
                return data
        return {}

    def get_historical_summary(self) -> dict:
        """轻量历史战略摘要。只做结构化提取，不做 LLM 推理。"""
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
        # 从 KPI 数据中提取关键指标
        for name, data in ctx.kpi_summary.items():
            if isinstance(data, dict):
                summary["kpi_highlights"].append({
                    "source": name,
                    "summary": str(data)[:500],
                })
        # 从项目数据中提取状态
        for name, data in ctx.project_summary.items():
            if isinstance(data, dict):
                summary["project_status"].append({
                    "source": name,
                    "summary": str(data)[:500],
                })
        # 从财务数据中提取
        for name, data in ctx.financial_summary.items():
            if isinstance(data, dict):
                summary["financial_highlights"].append({
                    "source": name,
                    "summary": str(data)[:500],
                })
        return summary
