# -*- coding: utf-8 -*-
"""PPT 视觉 QA 工具链（stub — 等模板到位后填充）。"""
import os
import logging

log = logging.getLogger(__name__)


def run(pptx_path: str, output_dir: str = "output/qa", verbose: bool = True) -> dict:
    """跑完整 QA 流程，返回报告 dict。（当前为 stub）"""
    os.makedirs(output_dir, exist_ok=True)
    return {
        "thumbs_path": None,
        "pdf_path": None,
        "slide_images": [],
        "issues": ["QA 尚未实现（等待 PPT 模板）"],
        "ok": True,
    }
