# -*- coding: utf-8 -*-
"""通用 Cell Map Schema — 覆盖所有 sheet 的基础输出格式。

每个 sheet 的输出最终都是 cells 形式的 dict: {"B4": "内容...", "B5": "内容...", ...}
+ notes 字段记录推理过程，供 UI 和前置依赖摘要使用。
"""
from pydantic import BaseModel, Field


class CellMapOutput(BaseModel):
    """通用 Cell Map 输出 schema。

    LLM 必须输出这个格式（或子类化后的格式），
    engine 用 fill_cells(cells) 写入 xlsx。
    """
    cells: dict[str, str] = Field(
        default_factory=dict,
        description="Cell 坐标映射, e.g. {'B4': '内容', 'B5': '内容'}. 坐标格式: 列字母+行号."
    )
    notes: str = Field(
        default="",
        description="推理过程摘要，供前置依赖 sheet 的 prompt 引用（建议 200-500 字）"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "cells": {
                    "B4": "2026 年政策环境分析结论...",
                    "B5": "2026 年经济环境分析结论..."
                },
                "notes": "本次 PESTEL 分析侧重政策和经济维度，发现..."
            }
        }
    }