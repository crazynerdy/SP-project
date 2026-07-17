# -*- coding: utf-8 -*-
"""core/engine — WorkflowEngine 辅助函数子包 (PR6)。

topological_sort 和 master_template_sheet 从此处提取，
WorkflowEngine 类仍保留在 core.workflow_engine 中。
"""
from core.engine.topology import topological_sort, CycleError
from core.engine.sheet_matcher import master_template_sheet

__all__ = ["topological_sort", "CycleError", "master_template_sheet"]
