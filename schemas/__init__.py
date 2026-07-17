# -*- coding: utf-8 -*-
"""Schema 层入口 — 根据 sheet_id 返回对应的 Pydantic 模型。"""
from __future__ import annotations

from pydantic import BaseModel

from schemas.cell_map import CellMapOutput
from schemas.sheet_schemas import (
    SCHEMA_REGISTRY,
    PESTELOutput,
    PESTELRow,
    IndustryTrendOutput,
    IndustryTrendRow,
    SWOTOutput,
    SWOTQuadrant,
)


def get_schema_for_sheet(sheet_id: str) -> type[BaseModel]:
    """根据 sheet_id 返回对应的 Pydantic 模型。

    先在 SCHEMA_REGISTRY 中查，miss 则返回 CellMapOutput（通用兜底）。
    """
    return SCHEMA_REGISTRY.get(sheet_id, CellMapOutput)


__all__ = [
    "CellMapOutput",
    "PESTELOutput",
    "PESTELRow",
    "IndustryTrendOutput",
    "IndustryTrendRow",
    "SWOTOutput",
    "SWOTQuadrant",
    "get_schema_for_sheet",
    "SCHEMA_REGISTRY",
]