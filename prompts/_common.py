# -*- coding: utf-8 -*-
"""Prompt 共享辅助函数。"""
import functools

from core.envutil import env
from core.paths import resource
from models import xlsx_reader


def _get_template_path():
    return env("TEMPLATE_XLSX_PATH")


@functools.lru_cache(maxsize=8)
def _get_schema(template_path=None):
    """缓存版 schema 列表。"""
    tpl = template_path or _get_template_path()
    return xlsx_reader.extract_schema(tpl)


@functools.lru_cache(maxsize=8)
def _get_schema_text(template_path=None):
    """从模板提 schema 渲染成 prompt 文本。"""
    schema = _get_schema(template_path)
    return xlsx_reader.schema_to_prompt_text(schema)


def _load_slide_spec_schema():
    """加载 slide_spec_schema.json。"""
    import json
    with open(resource("slide_spec_schema.json"), encoding="utf-8") as f:
        return json.load(f)
