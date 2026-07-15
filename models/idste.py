# -*- coding: utf-8 -*-
"""iDSTE MCP Server SP 管理工具的 REST 封装（只读）。

通过 REST API v2 (GET /mcp/api/v2/{tool}) 调用，API Key 从 .env 读取。
只封装 5 个只读 SP 工具；写工具 update_sp_data 不用于分析，不封装。
"""
import json
import requests
from core.envutil import env, require

_CFG = None  # 懒加载配置缓存，允许测试 patch / 运行时注入


def _get_config():
    """懒加载 iDSTE 配置。首次调用从 env 读，之后缓存；可被 configure() 覆盖。"""
    global _CFG
    if _CFG is None:
        _CFG = {
            "base": require("IDSTE_BASE").rstrip("/"),
            "api_key": require("IDSTE_API_KEY"),
            "timeout": int(env("IDSTE_TIMEOUT", "30")),
        }
    return _CFG


def configure(base=None, api_key=None, timeout=None):
    """依赖注入入口：显式覆盖配置（多账号/测试用）。"""
    global _CFG
    _CFG = {
        "base": (base or require("IDSTE_BASE")).rstrip("/"),
        "api_key": api_key or require("IDSTE_API_KEY"),
        "timeout": timeout or 30,
    }


def _call(tool, **params):
    """调用一个只读 SP 工具，返回 data 部分。"""
    cfg = _get_config()
    url = f"{cfg['base']}/mcp/api/v2/{tool}"
    clean = {k: v for k, v in params.items() if v is not None and v != ""}
    last_err = None
    for _attempt in range(2):
        try:
            r = requests.get(
                url,
                headers={"X-MCP-API-Key": cfg["api_key"]},
                params=clean,
                timeout=cfg["timeout"],
            )
            if r.status_code < 500:
                break
            last_err = RuntimeError(f"[{tool}] server error {r.status_code}: {r.text[:200]}")
        except requests.RequestException as e:
            last_err = e
        if _attempt == 0:
            import time as _t
            _t.sleep(1)
    else:
        raise RuntimeError(f"[{tool}] 重试失败: {last_err}")
    if r.status_code == 401:
        raise RuntimeError(f"[{tool}] API Key 认证失败(401)")
    if r.status_code == 403:
        raise RuntimeError(f"[{tool}] 权限不足/守卫拒绝(403)")
    if r.status_code == 404:
        raise RuntimeError(f"[{tool}] 工具不存在(404)")
    try:
        j = r.json()
    except Exception:
        raise RuntimeError(f"[{tool}] 非 JSON 响应: {r.text[:300]}")
    if not j.get("success", False):
        err = j.get("error", {})
        raise RuntimeError(
            f"[{tool}] 调用失败: {err.get('code')} {err.get('message', r.text[:200])}"
        )
    return j.get("data")


# ---------- 6 个只读 SP 工具 ----------
def sp_team_info():
    """查询SP团队信息（无参）。101 角色返回全公司，否则仅本人团队。"""
    return _call("get_sp_team_info")


def sp_plan(year):
    """查询SP编制计划（WBS）。year: 字符串如 '2025'。"""
    return _call("get_sp_plan", year=str(year))


def sp_dimension():
    """查询SP规划维度，返回 dim_info 列表（'c'/'bupl_{id}'/'f_{id}'）。"""
    return _call("get_sp_dimension")


def sp_data_menu(dim_info):
    """查询指定维度的数据菜单，返回数据表清单（含 table_key）。"""
    return _call("get_sp_data_menu", dim_info=dim_info)


def sp_data(dim_info, table_key, year):
    """查询指定维度/数据表/年份的数据，含 rendering_guide + data。"""
    return _call("get_sp_data", dim_info=dim_info, table_key=table_key, year=str(year))


# ---------- OpenAI tools schema（给 LLM 看） ----------
# 之前在 llm.py，但 schema 描述的是 iDSTE 工具，跟实现放一起更合理。
def build_tools_schema():
    """生成 SP 工具的 OpenAI tools schema（与本模块函数一一对应）。"""
    return [
        {
            "name": "sp_team_info",
            "description": "查询SP团队信息（无参）。101角色返回全公司SP规划团队，否则仅本人所属。",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "sp_plan",
            "description": "查询SP编制计划（WBS计划表）。返回指定年度的树形任务数据。",
            "parameters": {
                "type": "object",
                "properties": {"year": {"type": "string", "description": "年份，如 '2025'"}},
                "required": ["year"],
            },
        },
        {
            "name": "sp_dimension",
            "description": "查询SP规划维度（公司/BUPL/功能领域）。返回 dim_info 列表，'c' 是公司维度。",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "sp_data_menu",
            "description": "查询指定维度的数据菜单（数据表清单）。dim_info 必须由 sp_dimension 返回。",
            "parameters": {
                "type": "object",
                "properties": {"dim_info": {"type": "string", "description": "维度标识，如 c、bupl_5、f_3"}},
                "required": ["dim_info"],
            },
        },
        {
            "name": "sp_data",
            "description": "查询指定维度/数据表/年份的SP数据（含表格行内容）。依赖链：先 sp_dimension -> sp_data_menu 拿 table_key。",
            "parameters": {
                "type": "object",
                "properties": {
                    "dim_info": {"type": "string", "description": "维度标识"},
                    "table_key": {"type": "string", "description": "数据表标识，由 sp_data_menu 返回"},
                    "year": {"type": "string", "description": "年份，如 '2025'"},
                },
                "required": ["dim_info", "table_key", "year"],
            },
        },
    ]


# 默认工具映射（外部可复制后修改做 A/B 测试或多账号）
TOOL_MAP = {
    "sp_team_info": sp_team_info,
    "sp_plan": sp_plan,
    "sp_dimension": sp_dimension,
    "sp_data_menu": sp_data_menu,
    "sp_data": sp_data,
}


def _find_table_keys(obj, found=None):
    """从菜单返回里递归找出所有 table_key（结构未知，容错提取）。"""
    if found is None:
        found = []
    if isinstance(obj, dict):
        for k in ("table_key", "table_id"):
            if k in obj and isinstance(obj[k], str) and obj[k]:
                # name 字段容错：MCP 实际返回 table_title（如"行业趋势分析"），
                # 兼容 name / table_name / table_title，都没有时回退到 table_key
                found.append({"table_key": obj[k], "name": obj.get("name") or obj.get("table_name") or obj.get("table_title") or obj[k]})
        for v in obj.values():
            _find_table_keys(v, found)
    elif isinstance(obj, list):
        for v in obj:
            _find_table_keys(v, found)
    return found


def health_check():
    """检查 iDSTE 服务器是否可达。返回 True/False。"""
    cfg = _get_config()
    try:
        r = requests.get(cfg["base"], timeout=5, allow_redirects=True)
        return True
    except requests.RequestException:
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("== 1. sp_dimension() ==")
    dim = sp_dimension()
    print(json.dumps(dim, ensure_ascii=False, indent=2)[:1500])

    print("\n" + "=" * 60)
    print("== 2. sp_data_menu('c') ==")
    menu = sp_data_menu("c")
    tables = _find_table_keys(menu)
    print(f"发现 {len(tables)} 个 table_key")

    if tables:
        tk = tables[0]["table_key"]
        print(f"\n== 3. sp_data('c', '{tk}', '2025') ==")
        data = sp_data("c", tk, "2025")
        print(json.dumps(data, ensure_ascii=False, indent=2)[:2500])
