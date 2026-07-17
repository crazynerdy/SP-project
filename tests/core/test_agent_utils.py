# -*- coding: utf-8 -*-
"""agent_utils 测试。"""
from core.agent_utils import make_counting_wrapper, build_full_tool_map


class TestMakeCountingWrapper:
    def test_counts_calls(self):
        stats = {"__all__": {}}

        def add(a=0, b=0):
            return a + b

        wrapped = make_counting_wrapper("add", add, stats)
        wrapped(a=1, b=2)
        wrapped(a=3, b=4)

        assert stats["__all__"]["add"] == 2

    def test_preserves_result(self):
        stats = {"__all__": {}}

        def greet(name=""):
            return f"hi {name}"

        wrapped = make_counting_wrapper("greet", greet, stats)
        assert wrapped(name="world") == "hi world"


class TestBuildFullToolMap:
    def test_combines_maps(self):
        stats = {"__all__": {}}
        idste = {"sp_data": lambda: 1}
        web = {"web_search": lambda: 2}

        full = build_full_tool_map(idste, web, stats)
        assert set(full.keys()) == {"sp_data", "web_search"}

    def test_wrapped_functions_count(self):
        stats = {"__all__": {}}
        idste = {"sp_data": lambda: 1}

        full = build_full_tool_map(idste, {}, stats)
        full["sp_data"]()
        assert stats["__all__"]["sp_data"] == 1
