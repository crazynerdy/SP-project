# -*- coding: utf-8 -*-
"""json_utils.parse_json 测试。"""
from core.json_utils import parse_json, _repair_unescaped_quotes


class TestParseJson:
    def test_bare_json(self):
        assert parse_json('{"a": 1}') == {"a": 1}

    def test_json_with_fences(self):
        text = '```json\n{"a": 1}\n```'
        assert parse_json(text) == {"a": 1}

    def test_with_preamble(self):
        text = '这是结果：\n{"a": 1}\n结束。'
        assert parse_json(text) == {"a": 1}

    def test_empty_returns_empty_dict(self):
        assert parse_json("") == {}

    def test_invalid_returns_empty_dict(self):
        assert parse_json("not json") == {}

    def test_chinese_quotes_in_value(self):
        text = '{"desc": "通过"生产一代"策略"}'
        result = parse_json(text)
        assert result == {"desc": '通过"生产一代"策略'}


class TestRepairUnescapedQuotes:
    def test_simple(self):
        text = '{"k": "v"with"quotes"}'
        repaired = _repair_unescaped_quotes(text)
        assert '"with"' not in repaired
        assert '"with\\"' in repaired
