# -*- coding: utf-8 -*-
"""Agent 工具函数 — 从 controllers/agent.py 和 core/envutil.py 提取。"""
from core.envutil import run_with_timeout  # re-export


def make_counting_wrapper(name: str, fn, stats: dict):
    """包装一个工具函数，每次调用时在 stats 中计数。

    Args:
        name: 工具名
        fn: 原始工具函数
        stats: {"__all__": {name: count}} 格式的 dict

    Returns:
        wrapper: 与 fn 签名相同的函数
    """
    def wrapper(**kwargs):
        stats["__all__"].setdefault(name, 0)
        stats["__all__"][name] += 1
        return fn(**kwargs)
    wrapper.__name__ = f"counted_{name}"
    return wrapper


def build_full_tool_map(idste_tool_map: dict, websearch_tool_map: dict,
                        tool_call_stats: dict) -> dict:
    """构建带计数的完整 tool_map: idste + websearch 全包一层计数。

    Args:
        idste_tool_map: models.idste.TOOL_MAP
        websearch_tool_map: models.websearch.TOOL_MAP
        tool_call_stats: {"__all__": {}} 格式的 dict

    Returns:
        dict: {name: counted_fn}
    """
    full = {}
    for name, fn in dict(idste_tool_map).items():
        full[name] = make_counting_wrapper(name, fn, tool_call_stats)
    for name, fn in dict(websearch_tool_map).items():
        full[name] = make_counting_wrapper(name, fn, tool_call_stats)
    return full