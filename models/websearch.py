# -*- coding: utf-8 -*-
"""联网搜索客户端（DuckDuckGo）。作为 sp_data 的补充。

LLM 通过 TOOL_MAP 注册 web_search 工具调用；agent.py 把它和 iDSTE 工具一起注入。
"""
import logging
from core.envutil import env

log = logging.getLogger(__name__)


class DuckDuckGoClient:
    """封装 duckduckgo-search 包。失败抛异常，由调用方兜底。"""

    def __init__(self, max_results: int = 5, timeout: int = 30):
        from duckduckgo_search import DDGS
        self.ddgs = DDGS(timeout=timeout)
        self.max_results = max_results
        self.timeout = timeout

    def search(self, query: str) -> list[dict]:
        # 返回 [{title, href, body}, ...]
        results = list(self.ddgs.text(
            query,
            max_results=self.max_results,
        ))
        # 统一字段名为 title/snippet/url（与 spec 一致）
        return [
            {"title": r.get("title", ""), "snippet": r.get("body", ""), "url": r.get("href", "")}
            for r in results
        ]


# ============================================================
# LLM 工具注册
# ============================================================
WEB_SEARCH_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "在公网搜索行业、宏观、竞争对手、市场份额、政策等实时信息。结果质量次于 sp_data，仅在 sp_data 不足时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词，建议中文"}
            },
            "required": ["query"]
        }
    }
}


_CLIENT = None


def get_client():
    """工厂方法：从 env 读取配置，返回单例 client（避免每次搜索新建 DDGS）。"""
    global _CLIENT
    if env("WEBSEARCH_ENABLED", "true").lower() != "true":
        raise ValueError("WEBSEARCH_ENABLED=false，禁用了联网搜索")
    if _CLIENT is None:
        _CLIENT = DuckDuckGoClient(
            max_results=int(env("WEBSEARCH_MAX_RESULTS", "5")),
            timeout=int(env("WEBSEARCH_TIMEOUT", "30")),
        )
    return _CLIENT


def web_search_tool(query: str) -> str:
    """LLM 工具函数。返回格式化的搜索结果字符串。"""
    try:
        client = get_client()
        results = client.search(query)
        if not results:
            return "（无搜索结果）"
        lines = [f"[{i+1}] {r['title']}\n    {r['snippet']}\n    URL: {r['url']}"
                 for i, r in enumerate(results)]
        return "\n\n".join(lines)
    except Exception as e:
        log.warning(f"web_search 失败: {e}")
        return f"（搜索失败：{type(e).__name__}: {e}）"


TOOL_MAP = {
    "web_search": web_search_tool,
}


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "中国 智能制造 行业 趋势 2025"
    print(f"Query: {q}\n")
    try:
        results = get_client().search(q)
        for i, r in enumerate(results, 1):
            print(f"[{i}] {r['title']}")
            print(f"    {r['snippet']}")
            print(f"    URL: {r['url']}\n")
        print(f"共 {len(results)} 条结果")
    except Exception as e:
        print(f"FAIL: {type(e).__name__}: {e}")
        sys.exit(1)
