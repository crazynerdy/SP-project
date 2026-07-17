# -*- coding: utf-8 -*-
"""探测内网 LLM：1) 基本连通 2) function-calling 支持 3) 多模态支持。

用法: python probe_llm.py
结果决定 llm.py 的工具调用模式（native vs prompt）和 PPT 视觉 QA 是否可加。
"""
import json
import requests
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from core.envutil import require

BASE = require("LLM_BASE_URL").rstrip("/")
KEY = require("LLM_API_KEY")
MODEL = require("LLM_MODEL")
H = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}


def post(body, timeout=60):
    return requests.post(f"{BASE}/chat/completions", headers=H, json=body, timeout=timeout)


def main():
    print("=" * 60)
    print(f"模型: {MODEL}  端点: {BASE}")
    print("=" * 60)

    # 1) 基本连通
    print("\n[1] 基本连通")
    r = post({"model": MODEL, "messages": [{"role": "user", "content": "用一句话说你是谁"}], "temperature": 0})
    print("status:", r.status_code)
    try:
        j = r.json()
        print("回复:", j["choices"][0]["message"]["content"][:200])
    except Exception as e:
        print("解析失败:", e, "| 原始:", r.text[:300])

    # 2) function-calling
    print("\n[2] function-calling 支持")
    tools = [{"type": "function", "function": {
        "name": "get_weather",
        "description": "查询某城市天气",
        "parameters": {"type": "object", "properties": {"city": {"type": "string", "description": "城市名"}}, "required": ["city"]}
    }}]
    r = post({"model": MODEL, "messages": [{"role": "user", "content": "北京今天天气怎么样？"}], "tools": tools, "temperature": 0})
    print("status:", r.status_code)
    try:
        j = r.json()
        msg = j["choices"][0]["message"]
        tcs = msg.get("tool_calls")
        print("tool_calls:", json.dumps(tcs, ensure_ascii=False) if tcs else "无")
        print("content:", (msg.get("content") or "")[:200])
        print("=> 支持 native function-calling" if tcs else "=> 不支持 native，需用 prompt 模式")
    except Exception as e:
        print("解析失败:", e, "| 原始:", r.text[:300])

    # 3) 多模态
    print("\n[3] 多模态（图片理解）")
    # 1x1 红色 PNG
    img_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8z8BQDwADhQGAWjR9awAAAABJRU5ErkJggg=="
    content = [{"type": "text", "text": "这张图主要是什么颜色？只回答颜色。"},
               {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}}]
    r = post({"model": MODEL, "messages": [{"role": "user", "content": content}], "temperature": 0})
    print("status:", r.status_code)
    try:
        j = r.json()
        ans = j["choices"][0]["message"]["content"][:200]
        print("回复:", ans)
        print("=> 支持多模态（可加 PPT 视觉 QA）" if "红" in ans or "red" in ans.lower() else "=> 回复未识别红色，多模态可能不支持或未正确处理图片")
    except Exception as e:
        print("解析失败/不支持:", e, "| 原始:", r.text[:300])


if __name__ == "__main__":
    main()
