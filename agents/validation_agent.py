# -*- coding: utf-8 -*-
"""Validation Agent - 校验 Agent 输出是否符合预期。

纯函数，无外部依赖，可离线单测。
"""
import json
import re


def validate(output: dict, schema: dict | None = None) -> dict:
    """校验 Agent 输出。

    Args:
        output: 任意 Agent 的 JSON 输出
        schema: 可选的 JSON Schema dict（暂未实现完整 JSON Schema 校验，
                M6 引入 Pydantic 后补全；当前做基本结构检查）

    Returns:
        {
            "valid": True | False,
            "errors": [{"field": "...", "message": "..."}],
            "warnings": [...],
        }
    """
    errors = []
    warnings = []

    # 基本类型检查
    if not isinstance(output, dict):
        return {
            "valid": False,
            "errors": [{"field": "__root__", "message": f"期望 dict，收到 {type(output).__name__}"}],
            "warnings": [],
        }

    # 检查是否为空
    if not output:
        warnings.append("输出为空 dict")

    # 检查是否有嵌套的错误信息
    for key, val in output.items():
        if isinstance(val, str) and len(val) == 0:
            warnings.append(f"字段 '{key}' 为空字符串")

    # schema 基本校验（若提供）
    if schema and isinstance(schema, dict):
        required_fields = schema.get("required", [])
        for field in required_fields:
            if field not in output:
                errors.append({
                    "field": field,
                    "message": f"缺少必填字段 '{field}'",
                })

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


if __name__ == "__main__":
    # 离线单测
    assert validate({}) == {
        "valid": True, "errors": [],
        "warnings": ["输出为空 dict"],
    }
    assert validate("not a dict")["valid"] is False
    assert validate({"key": ""})["warnings"] == ["字段 'key' 为空字符串"]
    assert validate({"a": 1}, {"required": ["b"]}) == {
        "valid": False,
        "errors": [{"field": "b", "message": "缺少必填字段 'b'"}],
        "warnings": [],
    }
    print("Validation Agent: all tests PASS")
