# -*- coding: utf-8 -*-
"""Sheet 级别的 Pydantic 输出模型。

设计原则:
- 默认: 所有 sheet 用 CellMapOutput（通用 cells dict）
- 按需细化: 核心 sheet 有结构化 model（PESTEL, 行业趋势, SWOT）
- 每个 sheet 的 schema_class 名在 YAML 中引用，通过 get_schema_for_sheet() 解析
"""
from pydantic import BaseModel, Field
from schemas.cell_map import CellMapOutput


# ============================================================
# 2.1 宏观环境分析 (PESTEL) — 结构化
# ============================================================
class PESTELRow(BaseModel):
    """PESTEL 单行维度"""
    维度: str = Field(description="PESTEL 维度名: 政治/经济/社会/技术/环境/法律")
    变化与趋势: str = Field(description="该维度在 2026 年的主要变化与趋势, ≥80 字")
    机会: str = Field(description="该维度带来的机会, ≥50 字")
    威胁: str = Field(description="该维度带来的威胁, ≥50 字")


class PESTELOutput(BaseModel):
    """2.1 宏观环境分析 (PESTEL 分析) 输出"""
    rows: list[PESTELRow] = Field(description="6 个 PESTEL 维度的分析结果")
    notes: str = Field(default="", description="PESTEL 分析总结摘要")


# ============================================================
# 2.2 行业趋势分析 — 结构化
# ============================================================
class IndustryTrendRow(BaseModel):
    """行业趋势单行"""
    趋势维度: str = Field(description="趋势维度名称")
    趋势描述: str = Field(description="该趋势的详细描述, ≥80 字")
    对行业影响: str = Field(description="该趋势对行业的影响分析, ≥50 字")
    对公司影响: str = Field(description="该趋势对公司的影响分析, ≥50 字")


class IndustryTrendOutput(BaseModel):
    """2.2 行业趋势分析 输出"""
    rows: list[IndustryTrendRow] = Field(description="行业趋势分析的各维度结果")
    notes: str = Field(default="", description="行业趋势分析总结摘要")


# ============================================================
# 2.10 SWOT 分析 — 结构化
# ============================================================
class SWOTQuadrant(BaseModel):
    """SWOT 象限"""
    条目: str = Field(description="SWOT 条目描述")
    重要性: str = Field(default="中", description="高/中/低")
    应对策略: str = Field(default="", description="针对该条目的应对策略建议, ≥40 字")


class SWOTOutput(BaseModel):
    """2.10 SWOT 分析 输出"""
    优势: list[SWOTQuadrant] = Field(description="内部优势列表")
    劣势: list[SWOTQuadrant] = Field(description="内部劣势列表")
    机会: list[SWOTQuadrant] = Field(description="外部机会列表")
    威胁: list[SWOTQuadrant] = Field(description="外部威胁列表")
    notes: str = Field(default="", description="SWOT 分析总结摘要")


# ============================================================
# Schema 注册表 — sheet_id -> Pydantic Model
# ============================================================
SCHEMA_REGISTRY: dict[str, type[BaseModel]] = {
    # 结构化 schemas
    "2.1": PESTELOutput,
    "2.2": IndustryTrendOutput,
    "2.10": SWOTOutput,
    # 其余 sheet 默认用 CellMapOutput
    # (在 get_schema_for_sheet 中兜底处理)
}