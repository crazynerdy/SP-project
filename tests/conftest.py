# -*- coding: utf-8 -*-
"""pytest 共享 fixtures。"""
import pytest


@pytest.fixture
def fake_llm_client():
    """返回一个伪 LLM client，永远返回固定字符串。"""
    class FakeLLM:
        def chat(self, messages, **kwargs):
            return {"content": '{"sheets": []}'}
    return FakeLLM()


@pytest.fixture
def empty_tool_stats():
    return {"__all__": {}}
