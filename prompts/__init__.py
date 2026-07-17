# -*- coding: utf-8 -*-
"""Prompts 包 — 从 models/prompts.py 拆分而来 (PR6 of docs/REFACTOR_CODEX_2026.md)。

所有 build_* 函数在此重新导出，兼容旧的 `from models import prompts` 用法。
"""
from prompts._common import _get_template_path, _get_schema, _get_schema_text, _load_slide_spec_schema
from prompts.intent import INTENT_RECOGNITION_PROMPT, build_intent_recognition_prompt
from prompts.xlsx_data import XLSX_DATA_PROMPT, build_xlsx_data_prompt
from prompts.slide_spec import SLIDE_SPEC_FROM_XLSX_PROMPT, build_slide_spec_from_xlsx_prompt
from prompts.sp_2026 import SP_2026_DATA_PROMPT_TEMPLATE, build_sp_2026_data_prompt
from prompts.agent_template import AGENT_PROMPT_TEMPLATE, build_agent_prompt

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
    "_get_template_path",
    "_get_schema",
    "_get_schema_text",
    "_load_slide_spec_schema",
]