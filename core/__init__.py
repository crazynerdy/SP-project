# -*- coding: utf-8 -*-
"""Core 模块 — 配置、上下文、JSON 工具、Agent 工具、工作流引擎。"""
from core.envutil import env, require, run_with_timeout
from core.paths import PROJECT_ROOT, resource
from core.json_utils import parse_json, _repair_unescaped_quotes
from core.agent_utils import make_counting_wrapper, build_full_tool_map
from core.strategic_context import (
    StrategicContext,
    StrategyContextBuilder,
    get_dependencies,
)