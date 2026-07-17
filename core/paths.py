# -*- coding: utf-8 -*-
"""项目根锚点：所有资源文件统一从这里定位，模块怎么移动都不影响资源查找。

被 core/envutil.py（.env）、models/prompts.py（slide_spec_schema.json）、
models/pptx_builder.py（render.js）、views/ui_theme.py（theme.json）共用。
"""
from pathlib import Path

# core/paths.py -> 向上一级 = 项目根
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def resource(name: str) -> str:
    """返回项目根下某资源文件的绝对路径字符串。"""
    return str(PROJECT_ROOT / name)
