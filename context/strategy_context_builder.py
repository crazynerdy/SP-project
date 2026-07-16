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

        target_tables: 只拉指定表名（None = 拉全部可用表）。
        结果缓存，重复调用不重复拉 MCP。
        """
        raise NotImplementedError("Phase 1 will implement")

    def get_sheet_context(self, sheet_name: str) -> dict:
        """单 sheet 上下文。从缓存或按需拉取。"""
        raise NotImplementedError("Phase 1 will implement")

    def get_historical_summary(self) -> dict:
        """轻量历史战略摘要。只做结构化提取，不做 LLM 推理。"""
        raise NotImplementedError("Phase 1 will implement")
