# -*- coding: utf-8 -*-
"""JSON 解析工具 — 从 controllers/agent.py 提取，解除循环引用。

提供:
    - _repair_unescaped_quotes(text) -> str  — 修复 JSON 字符串值内未转义的双引号
    - parse_json(text) -> dict               — 容错解析 LLM 返回的 JSON
"""
import json


def _repair_unescaped_quotes(t: str) -> str:
    """修复 JSON 字符串值内未转义的双引号。

    reasoning 模型常在中文字符串里用 ``"..."`` 强调，导致 JSON 字符串提前结束。
    扫描时维护 in_string 状态；字符串内的裸 ``"`` 若后面（跳过空白）不跟
    ``,}]:`` 则判定为值内引号，转义为 ``\\"``。
    """
    out = []
    i, n = 0, len(t)
    in_str = False
    while i < n:
        c = t[i]
        if not in_str:
            out.append(c)
            if c == '"':
                in_str = True
            i += 1
            continue
        # 字符串内
        if c == '\\':  # 转义符，原样保留下一字符
            out.append(c)
            if i + 1 < n:
                out.append(t[i + 1])
                i += 2
            else:
                i += 1
            continue
        if c == '"':
            j = i + 1
            while j < n and t[j] in ' \t\r\n':
                j += 1
            if j >= n or t[j] in ',}]:':
                out.append(c)      # 字符串结束
                in_str = False
            else:
                out.append('\\"')  # 值内裸引号，转义
            i += 1
            continue
        out.append(c)
        i += 1
    return ''.join(out)


def parse_json(text: str) -> dict:
    """容错解析 LLM 返回的 JSON。

    处理:
    1. ```json ... ``` 围栏
    2. 前后言包裹
    3. 字符串值内未转义的双引号（reasoning 模型常见问题）

    失败或非 dict 时返回 {}，绝不抛异常。
    """
    t = text.strip()
    # 去 markdown 围栏
    if t.startswith("```"):
        lines = t.split("\n")
        kept = [ln for ln in lines if ln.strip().lower() not in ("```json", "```", "``")]
        t = "\n".join(kept).strip()
    # 提取第一个 {...}
    if not t.startswith("{"):
        i = t.find("{")
        j = t.rfind("}")
        if i != -1 and j != -1:
            t = t[i:j + 1]
    try:
        obj = json.loads(t)
    except json.JSONDecodeError:
        # fallback: 修复字符串值内未转义的双引号
        try:
            obj = json.loads(_repair_unescaped_quotes(t))
        except Exception:
            return {}
    return obj if isinstance(obj, dict) else {}