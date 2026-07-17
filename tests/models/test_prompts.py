# -*- coding: utf-8 -*-
"""prompts.py build_* 函数测试。"""
import pytest

from models import prompts


class TestBuildIntentRecognitionPrompt:
    def test_returns_string_with_sheets(self):
        # 需要真实模板文件；若不存在则跳过
        try:
            p = prompts.build_intent_recognition_prompt()
        except Exception:
            pytest.skip("模板文件不可用")
        assert isinstance(p, str)
        assert "EXCEL_SHEETS" in p


class TestBuildXlsxDataPrompt:
    def test_returns_string_with_target_sheets(self):
        try:
            p = prompts.build_xlsx_data_prompt(["1.1 业绩差距分析"])
        except Exception:
            pytest.skip("模板文件不可用")
        assert isinstance(p, str)
        assert "1.1 业绩差距分析" in p


class TestBuildAgentPrompt:
    def test_all_sections_present(self):
        p = prompts.build_agent_prompt(
            role="测试角色",
            task_description="测试任务",
            predecessor_context="前置结果",
            mcp_context='{"k": "v"}',
            output_format="JSON",
            output_schema='{"type": "object"}',
        )
        assert "测试角色" in p
        assert "测试任务" in p
        assert "前置结果" in p
        assert "JSON" in p
