# -*- coding: utf-8 -*-
"""PPTX 生成器 — 从 xlsx 数据生成 slide-spec 并调用 Node 渲染。

替代已删除的 controllers/agent.py::generate_pptx_from_xlsx，
作为 models/ 层的纯函数，不依赖 Streamlit session_state。
"""
from __future__ import annotations

from models import xlsx_reader, pptx_builder, qa


def generate_pptx_from_xlsx(
    request: str,
    xlsx_path: str,
    enable_images: bool = False,
    enable_qa: bool = False,
    verbose: bool = False,
) -> dict:
    """从已填好的 xlsx 生成 PPT。

    Returns:
        {
            "pptx_path": str,
            "slide_spec": dict,
            "qa": dict | None,
        }
    """
    xlsx_data = xlsx_reader.read_template(xlsx_path)

    slide_spec = _build_slide_spec(xlsx_data, request)

    pptx_path = pptx_builder.build_pptx(
        slide_spec, output_dir="output", verbose=verbose,
    )

    result = {
        "pptx_path": pptx_path,
        "slide_spec": slide_spec,
        "qa": None,
    }

    if enable_qa:
        result["qa"] = qa.run(pptx_path, verbose=verbose)

    return result


def _build_slide_spec(xlsx_data: dict, request: str) -> dict:
    """把 xlsx 数据转成 slide-spec dict（简化版，后续 PR 补 LLM 润色）。"""
    slides = []
    for sheet in xlsx_data.get("sheets", []):
        sheet_name = sheet.get("sheet_name", "未命名")
        headers = sheet.get("headers", [])
        rows = sheet.get("rows", [])

        # 标题页
        slides.append({
            "layout": "title_content",
            "title": sheet_name,
            "content": f"共 {len(rows)} 条记录" + ("，含图片字段" if headers else ""),
        })

        # 数据页（表格，最多 8 行避免溢出）
        if rows:
            slides.append({
                "layout": "table",
                "title": sheet_name,
                "headers": headers,
                "rows": rows[:8],
            })

    if not slides:
        slides.append({
            "layout": "title_content",
            "title": request or "战略规划分析报告",
            "content": "暂无数据",
        })

    return {
        "meta": {
            "title": request or "战略规划分析报告",
            "subtitle": "",
            "author": "SP Agent",
        },
        "slides": slides,
    }
