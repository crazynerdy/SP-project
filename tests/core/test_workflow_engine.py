# -*- coding: utf-8 -*-
"""WorkflowEngine 纯函数测试。"""
import pytest

from core.workflow_engine import WorkflowEngine, CycleError
from tests._factories import make_task, make_context


class TestTopologicalSort:
    def test_linear(self):
        tasks = [
            make_task("A", "Sheet A", depends_on=[]),
            make_task("B", "Sheet B", depends_on=["A"]),
            make_task("C", "Sheet C", depends_on=["B"]),
        ]
        engine = WorkflowEngine(tasks, make_context())
        order = [t["sheet_id"] for t in engine.topological_sort()]
        assert order == ["A", "B", "C"]

    def test_diamond(self):
        tasks = [
            make_task("A", "Sheet A", depends_on=[]),
            make_task("B", "Sheet B", depends_on=["A"]),
            make_task("C", "Sheet C", depends_on=["A"]),
            make_task("D", "Sheet D", depends_on=["B", "C"]),
        ]
        engine = WorkflowEngine(tasks, make_context())
        order = [t["sheet_id"] for t in engine.topological_sort()]
        assert order.index("A") < order.index("B")
        assert order.index("A") < order.index("C")
        assert order.index("B") < order.index("D")
        assert order.index("C") < order.index("D")

    def test_cycle_raises(self):
        tasks = [
            make_task("A", "Sheet A", depends_on=["B"]),
            make_task("B", "Sheet B", depends_on=["A"]),
        ]
        engine = WorkflowEngine(tasks, make_context())
        with pytest.raises(CycleError):
            engine.topological_sort()

    def test_single_node(self):
        tasks = [make_task("A", "Sheet A", depends_on=[])]
        engine = WorkflowEngine(tasks, make_context())
        order = [t["sheet_id"] for t in engine.topological_sort()]
        assert order == ["A"]

    def test_disabled_skipped(self):
        tasks = [
            make_task("A", "Sheet A", enabled=True),
            make_task("B", "Sheet B", enabled=False),
        ]
        engine = WorkflowEngine(tasks, make_context())
        order = [t["sheet_id"] for t in engine.topological_sort()]
        assert order == ["A"]


class TestMasterTemplateSheet:
    def test_exact_match(self):
        engine = WorkflowEngine([], make_context())
        result = engine._master_template_sheet("业绩差距分析", ["业绩差距分析", "机会差距分析"])
        assert result == "业绩差距分析"

    def test_prefix_match(self):
        engine = WorkflowEngine([], make_context())
        result = engine._master_template_sheet("业绩差距分析表", ["业绩差距分析", "机会差距分析"])
        assert result == "业绩差距分析"

    def test_cjk_chunk_match(self):
        engine = WorkflowEngine([], make_context())
        result = engine._master_template_sheet("主要风险分析表", ["主要风险分析", "业绩差距分析"])
        assert result == "主要风险分析"

    def test_no_match_fallback(self):
        engine = WorkflowEngine([], make_context())
        result = engine._master_template_sheet("不存在的表", ["业绩差距分析"])
        # _master_template_sheet 会 strip "表" suffix，所以 fallback 也是 strip 后的
        assert result == "不存在的"
