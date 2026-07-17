# -*- coding: utf-8 -*-
"""Import 探烟 — 确保核心模块无 ImportError。"""


def test_import_controllers():
    import controllers.ppt_controller
    import controllers.excel_controller


def test_import_core():
    from core.workflow_engine import WorkflowEngine
    from core.strategic_context import StrategicContext, StrategyContextBuilder
    from core.json_utils import parse_json
    from core.agent_utils import make_counting_wrapper, build_full_tool_map


def test_import_models():
    from models import prompts, xlsx_reader, xlsx_exporter, pptx_builder
    from models.pptx_generator import generate_pptx_from_xlsx


def test_import_agents():
    from agents.base_agent import BaseAgent
    from agents.strategy_agent import StrategyAgent


def test_import_sp_agent_cli():
    import sp_agent.__main__
