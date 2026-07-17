# -*- coding: utf-8 -*-
"""Sheet 名称模糊匹配 — 从 WorkflowEngine 提取的纯函数。"""
import re


def master_template_sheet(output_template: str, available_sheets: list[str]) -> str:
    """模糊匹配 D 列模板名 → 主模板实际 sheet 名。

    匹配策略（按优先级）：
    1. 精确匹配（strip 后）
    2. 前缀匹配
    3. CJK 连续字符 chunk 最长匹配
    4. 回退：返回 strip 后的原始名
    """
    raw = output_template.strip()
    s = raw
    for suffix in ("表", "图"):
        if s.endswith(suffix):
            s = s[:-len(suffix)].strip()
            break

    # 精确
    for name in available_sheets:
        if name.strip() == s:
            return name

    # 前缀
    for name in available_sheets:
        n = name.strip()
        if n and s.startswith(n):
            return name

    # CJK chunk
    chunks = sorted(set(re.findall(r"[一-鿿]{2,}", s)), key=len, reverse=True)
    best = None
    best_len = 0
    for name in available_sheets:
        n = name.strip()
        for chunk in chunks:
            if chunk in n and len(chunk) > best_len:
                best = name
                best_len = len(chunk)
                break
    return best if best is not None else s
