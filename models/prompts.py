# -*- coding: utf-8 -*-
"""Prompts 兼容 Shim — 内容已拆分到 prompts/ 包。

moved from models/prompts.py (443 lines) → prompts/ 包 (PR6 of docs/REFACTOR_CODEX_2026.md)
保留本文件以确保旧的 `from models import prompts` 用法继续工作。
"""
from prompts import (
    INTENT_RECOGNITION_PROMPT,
    XLSX_DATA_PROMPT,
    SLIDE_SPEC_FROM_XLSX_PROMPT,
    SP_2026_DATA_PROMPT_TEMPLATE,
    AGENT_PROMPT_TEMPLATE,
    build_intent_recognition_prompt,
    build_xlsx_data_prompt,
    build_slide_spec_from_xlsx_prompt,
    build_sp_2026_data_prompt,
    build_agent_prompt,
)

__all__ = [
    "INTENT_RECOGNITION_PROMPT",
    "XLSX_DATA_PROMPT",
    "SLIDE_SPEC_FROM_XLSX_PROMPT",
    "SP_2026_DATA_PROMPT_TEMPLATE",
    "AGENT_PROMPT_TEMPLATE",
    "build_intent_recognition_prompt",
    "build_xlsx_data_prompt",
    "build_slide_spec_from_xlsx_prompt",
    "build_sp_2026_data_prompt",
    "build_agent_prompt",
]


if __name__ == "__main__":
    print("=" * 60)
    print("[1] INTENT_RECOGNITION_PROMPT 长度:", len(build_intent_recognition_prompt()), "字")
    print("=" * 60)
    print("[2] XLSX_DATA_PROMPT 长度（target=1.1+1.2+5.4+4.3）:",
          len(build_xlsx_data_prompt(["1.1 业绩差距分析", "1.2 机会差距分析",
                                       "5.4 主要风险分析 ", "4.3 战略专题清单"])), "字")
    print("=" * 60)
    fake_xlsx = {"sheets": [{"sheet_name": "1.1 业绩差距分析", "headers": ["序号", "描述"], "rows": [[1, "test"]]}]}
    print("[3] SLIDE_SPEC_FROM_XLSX_PROMPT 长度:",
          len(build_slide_spec_from_xlsx_prompt(fake_xlsx, "分析完成度")), "字")
    print("=" * 60)
    print("[4] SP_2026_DATA_PROMPT 长度（2.2 试跑 6 维度）:",
          len(build_sp_2026_data_prompt(
              template_name="2.2 行业趋势分析",
              row_labels=["变化中的客户偏好", "行业间的界限模糊",
                          "全球化/新进入市场的全球化竞争者", "突破性的新技术",
                          "政策、法规变化", "新的或变化中的利润模式"],
              baseline_2025_json='{"示例": "2025 实际数据..."}',
              process_hint="要根据差距分析，然后作为输入，进行生成",
              year=2026,
          )),
          "字")
