# Qwen-Image 集成 + v2 增量（联网 + sp_data 监控）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 Qwen-Image-2512 图片生成、DuckDuckGo 联网搜索、sheet→tool 强约束、工具调用计数监控集成到现有 SP Agent（双流程：Excel + PPT），升级 theme 到 Midnight Executive 配色，接入 pptx skill 的 QA 工具链。

**Architecture:** 保持现有 pptxgenjs 渲染路径不动，新增 4 个 Python 模块（image_client / image_pipeline / websearch / qa），通过 DI 注入到 agent.py。slide_spec_schema.json 加 image + tool_hints 字段（单一真相源）。theme.json 重写为 Midnight Executive 配色 + 9 宫格 zone 坐标表。

**Tech Stack:** Python 3.10+, openpyxl, requests, streamlit, duckduckgo-search, pptxgenjs (Node.js)，继承现有 OpenAI-compatible LLM 客户端。

**Spec 引用:** `docs/superpowers/specs/2026-07-13-qwen-image-ppt-design.md`

---

## 执行范围（2026-07-13 用户更新）

**已确认可做（不依赖 PPT 模板）**：
- Task 1: 基础环境与配置（pip install + .env + requirements.txt）
- Task 2: 重写 theme.json（Midnight Executive 配色；9 宫格 zone 坐标作为**通用**模型保留）
- Task 3: 更新 slide_spec_schema.json（image + tool_hints + 36 sheet 预设）
- Task 4: websearch.py（DuckDuckGoClient + LLM 工具）
- Task 5: image_client.py（QwenImageClient）
- Task 6: image_pipeline.py（augment_slide_spec）
- Task 7: prompts.py（slide-spec image 规则 + XLSX_DATA 3 条 sp_data 硬规则）
- Task 8: agent.py（DI + tool_call_stats 计数 wrapper + image_client 注入）
- Task 11: app.py **仅 Tab 1 部分**（tool_call_stats UI）；**Tab 2（PPT 流程） 等模板**
- Task 12: STATUS.md 更新（v3 增量章节）

**⏸ BLOCKED — 等待 PPT 模板**：
- Task 9: render.js applyImageZone（需要根据模板的 layout 结构调整 zone 适配）
- Task 10: qa.py（QA 检查项依赖模板的 layout 与字号范围）
- Task 11 Tab 2（图片生成/QA checkbox + QA 展示）——等模板一起做

**为什么这样切**：用户原话给后面留下一些写代码的机会。PPT 视觉细节（字体/排版/zone 适配）依赖具体模板，模板没到时做的早晚会推倒。先把独立模块（image_client / websearch / image_pipeline）和数据层（prompts / agent / schema / theme 配色）做扎实，模板到了再补 render.js / qa / Tab 2。

---

## Global Constraints

- **项目根目录:** `D:\memory`
- **Python 解释器:** 系统中已有的 `python`（已装 openpyxl, requests, streamlit, python-dotenv）
- **LLM:** Qwen3.5_122B_A10B at `http://10.8.0.54:6003/v1`（OpenAI 兼容，function-calling）
- **iDSTE MCP:** `http://123.188.239.53:9090`，5 个只读工具
- **Qwen-Image:** `http://10.8.0.26:6005/v1/images/generations`，model `Qwen-Image-2512`
- **DuckDuckGo:** pip 包 `duckduckgo-search`，无需 key
- **xlsx 模板:** `D:\下载\【中海润】战略规划智能体输出格式.xlsx`（36 张数据 sheet）
- **代码风格:** 易扩展可迭代——DI、配置化、schema 驱动、单一真相源；中文输出；每文件 < 300 行
- **测试方式:** 每个新模块带 `__main__` 段做轻量验证；不写正式 pytest
- **凭据:** 全部在 `.env`（已 gitignore）
- **不使用 git**（项目当前非 git 仓库；commit 步骤可选）

---

## 文件结构总览

| 文件 | 操作 | 职责 |
|---|---|---|
| `.env` | 改 | 加 QWEN_IMAGE_* + WEBSEARCH_* 配置 |
| `.env.example` | 改 | 同上（脱敏模板）|
| `requirements.txt` | 改 | 加 duckduckgo-search |
| `theme.json` | 改 | Midnight Executive 配色 + 9 宫格 zone 坐标 |
| `slide_spec_schema.json` | 改 | 加 image + tool_hints 字段 + 36 sheet 预设表 |
| `image_client.py` | 新 | QwenImageClient |
| `image_pipeline.py` | 新 | augment_slide_spec |
| `websearch.py` | 新 | DuckDuckGoClient |
| `qa.py` | 新 | thumbnail + soffice QA 工具链 |
| `prompts.py` | 改 | slide-spec prompt 加 image 规则 + XLSX_DATA 加 3 条 sp_data 硬规则 |
| `agent.py` | 改 | DI 加 image_client/image_pipeline/qa；tool_call_stats 计数 |
| `render.js` | 改 | 新增 applyImageZone 函数 |
| `app.py` | 改 | 加图片生成/QA checkbox + tool_call_stats UI |
| `STATUS.md` | 改 | 更新到 v3 架构 |

---

## Task 1: 基础环境与配置

**Files:**
- Modify: `D:\memory\requirements.txt`
- Modify: `D:\memory\.env`
- Modify: `D:\memory\.env.example`

**Interfaces:**
- Consumes: 无
- Produces: 环境准备好（pip 装好 duckduckgo-search，.env 含 QWEN_IMAGE_* 和 WEBSEARCH_*）

- [ ] **Step 1: 安装 duckduckgo-search**

```bash
pip install duckduckgo-search
```

- [ ] **Step 2: 验证安装成功**

```bash
python -c "from duckduckgo_search import DDGS; print(DDGS)"
```

预期：输出 `<class 'duckduckgo_search.DDGS'>` 类对象。

- [ ] **Step 3: 更新 requirements.txt**

在 `D:\memory\requirements.txt` 末尾追加：

```
duckduckgo-search>=4.0
```

- [ ] **Step 4: 在 .env 末尾追加 Qwen-Image 配置**

读取 `.env` 末尾，追加：

```bash
# Qwen-Image 图片生成（新增）
QWEN_IMAGE_URL=http://10.8.0.26:6005
QWEN_IMAGE_MODEL=Qwen-Image-2512
QWEN_IMAGE_TOKEN=<your-token>
IMAGE_CACHE_DIR=cache/images
IMAGE_CACHE_MAX_MB=500

# 联网搜索（新增）
WEBSEARCH_ENABLED=true
WEBSEARCH_PROVIDER=duckduckgo
WEBSEARCH_MAX_RESULTS=5
WEBSEARCH_TIMEOUT=30
```

- [ ] **Step 5: 在 .env.example 同步追加（脱敏）**

在 `.env.example` 末尾追加：

```bash
# Qwen-Image 图片生成
QWEN_IMAGE_URL=http://<your-qwen-image-host>:<port>
QWEN_IMAGE_MODEL=Qwen-Image-2512
QWEN_IMAGE_TOKEN=<your-xsrf-token>
IMAGE_CACHE_DIR=cache/images
IMAGE_CACHE_MAX_MB=500

# 联网搜索
WEBSEARCH_ENABLED=true
WEBSEARCH_PROVIDER=duckduckgo
WEBSEARCH_MAX_RESULTS=5
WEBSEARCH_TIMEOUT=30
```

- [ ] **Step 6: 验证 .env 加载正常**

```bash
python -c "from envutil import env; print('QWEN_IMAGE_URL =', env('QWEN_IMAGE_URL')); print('WEBSEARCH_PROVIDER =', env('WEBSEARCH_PROVIDER'))"
```

预期：
```
QWEN_IMAGE_URL = http://10.8.0.26:6005
WEBSEARCH_PROVIDER = duckduckgo
```

---

## Task 2: 重写 theme.json（Midnight Executive + 9 宫格 zone）

**Files:**
- Modify: `D:\memory\theme.json`

**Interfaces:**
- Consumes: 无
- Produces: 新的 theme.json，render.js 和 prompts.py 都从这里读配色/字体/zone 坐标

- [ ] **Step 1: 备份当前 theme.json**

```bash
cp D:\memory\theme.json D:\memory\theme.json.bak.v2
```

- [ ] **Step 2: 读取当前 theme.json 内容**

```bash
cat D:\memory\theme.json
```

记录现有的字段名（避免覆盖任何已有结构），如果需要保留 `LAYOUT`/`FONT` 等其他段。

- [ ] **Step 3: 完整重写 theme.json**

`D:\memory\theme.json` 全量替换为以下内容（保留 step 2 中未在下面的任何额外字段，加在末尾）：

```json
{
  "palette": "Midnight Executive",
  "color": {
    "primary":   "1E2761",
    "secondary": "CADCFC",
    "accent":    "FFFFFF",
    "text_dark": "0A0F2C",
    "text_muted":"5A6A8A",
    "bg_dark":   "0E1A40",
    "bg_light":  "F5F7FB",
    "border":    "8DA3C7",
    "warn":      "F96167",
    "ok":        "97BC62"
  },
  "font": {
    "family_header": "Microsoft YaHei",
    "family_body":   "Microsoft YaHei",
    "family_data":   "Consolas",
    "hero":   60,
    "cover":  44,
    "title":  32,
    "subtitle": 20,
    "body":   18,
    "caption": 12,
    "big_stat": 72
  },
  "layout": {
    "slideW": 13.33,
    "slideH": 7.5,
    "margin": 0.5,
    "gutter": 0.3
  },
  "image_zone": {
    "1": { "x": 0.5, "y": 4.5, "w": 4.0, "h": 2.5 },
    "2": { "x": 4.5, "y": 4.5, "w": 4.0, "h": 2.5 },
    "3": { "x": 8.5, "y": 4.5, "w": 4.0, "h": 2.5 },
    "4": { "x": 0.5, "y": 2.0, "w": 4.0, "h": 2.5 },
    "5": { "x": 4.5, "y": 2.0, "w": 4.0, "h": 2.5 },
    "6": { "x": 8.5, "y": 2.0, "w": 4.0, "h": 2.5 },
    "7": { "x": 0.5, "y": 0.5, "w": 4.0, "h": 1.5 },
    "8": { "x": 4.5, "y": 0.5, "w": 4.0, "h": 1.5 },
    "9": { "x": 8.5, "y": 0.5, "w": 4.0, "h": 1.5 }
  }
}
```

- [ ] **Step 4: 验证 JSON 解析 + 关键字段**

```bash
python -c "import json; t = json.load(open('D:/memory/theme.json', encoding='utf-8')); print('palette:', t['palette']); print('primary:', t['color']['primary']); print('zone[5]:', t['image_zone']['5'])"
```

预期：
```
palette: Midnight Executive
primary: 1E2761
zone[5]: {'x': 4.5, 'y': 2.0, 'w': 4.0, 'h': 2.5}
```

---

## Task 3: 更新 slide_spec_schema.json（image 字段 + tool_hints 字段）

**Files:**
- Modify: `D:\memory\slide_spec_schema.json`

**Interfaces:**
- Consumes: 现有 8 个 layout 定义
- Produces: schema 含 image 字段定义 + tool_hints 字段 + 36 sheet 预设

- [ ] **Step 1: 备份当前 schema**

```bash
cp D:\memory\slide_spec_schema.json D:\memory\slide_spec_schema.json.bak.v2
```

- [ ] **Step 2: 读取当前 schema 顶层结构**

```bash
python -c "import json; s = json.load(open('D:/memory/slide_spec_schema.json', encoding='utf-8')); print(list(s.keys()))"
```

记录已有顶层 key。

- [ ] **Step 3: 追加 image 字段定义**

在 `slide_spec_schema.json` 顶层新增 `image_field` 对象（如果文件末尾无逗号先加逗号）：

```json
,
"image_field": {
  "description": "可选字段。AI 生成的配图配置，Qwen-Image 集成使用。",
  "fields": {
    "prompt":    { "type": "string", "required": true, "desc": "喂给 Qwen-Image 的 prompt" },
    "zone":      { "type": "int",    "required": true, "enum": [1,2,3,4,5,6,7,8,9], "desc": "9 宫格位置（numpad 布局）" },
    "aspect":    { "type": "string", "required": true, "enum": ["16:9", "4:3", "1:1", "3:4"] },
    "style":     { "type": "string", "required": true, "enum": ["minimal", "photographic", "illustration", "diagram"] },
    "required":  { "type": "bool",   "required": true, "desc": "true=失败 raise，false=失败跳过" }
  }
}
```

- [ ] **Step 4: 追加 tool_hints 字段定义**

紧接 `image_field` 之后追加 `tool_hints_field`：

```json
,
"tool_hints_field": {
  "description": "可选字段。给 LLM 提示该 sheet 必须先调哪些 sp_data 表或 web_search 关键词。",
  "fields": {
    "tool_hints":         { "type": "array<string>", "required": false },
    "required_tool_calls":{ "type": "int",           "required": false, "default": 1 }
  }
}
```

- [ ] **Step 5: 追加 36 sheet 预设表**

在 schema 末尾追加 `sheet_presets` 数组：

```json
,
"sheet_presets": {
  "1.1 业绩差距分析":      { "tool_hints": ["业绩差距", "责任人"],            "required_tool_calls": 2 },
  "1.2 机会差距分析":      { "tool_hints": ["机会差距", "战略机会"],          "required_tool_calls": 2 },
  "2.1 宏观环境分析":      { "tool_hints": ["PESTEL", "宏观", "web_search"],  "required_tool_calls": 4 },
  "2.2 行业趋势分析":      { "tool_hints": ["行业趋势", "web_search"],        "required_tool_calls": 3 },
  "2.3 市场容量分析":      { "tool_hints": ["市场容量", "TAM", "web_search"], "required_tool_calls": 3 },
  "2.4 客户购买行为":      { "tool_hints": ["客户行为", "细分市场"],          "required_tool_calls": 2 },
  "2.5 业务划分分析":      { "tool_hints": ["业务划分", "BU/PL"],            "required_tool_calls": 2 },
  "2.6 整体对手分析":      { "tool_hints": ["对手分析", "市场份额", "web_search"], "required_tool_calls": 6 },
  "2.7 主要对手分析":      { "tool_hints": ["主要对手", "对比", "web_search"],     "required_tool_calls": 5 },
  "2.8 雷达图分析":        { "tool_hints": ["雷达图", "能力评估"],           "required_tool_calls": 1 },
  "2.9 自身分析":          { "tool_hints": ["自身能力"],                     "required_tool_calls": 1 },
  "2.10 五看分析":         { "tool_hints": ["五看", "行业"],                  "required_tool_calls": 1 },
  "2.11 SWOT分析":         { "tool_hints": ["SWOT"],                          "required_tool_calls": 1 },
  "2.12 TOPN 行业":        { "tool_hints": ["TOPN", "行业排名"],              "required_tool_calls": 1 },
  "2.13 行业占有率":       { "tool_hints": ["占有率", "市场份额", "web_search"], "required_tool_calls": 2 },
  "3.1 使命愿景":          { "tool_hints": ["使命愿景"],                     "required_tool_calls": 1 },
  "3.2 战略地图":          { "tool_hints": ["战略地图"],                     "required_tool_calls": 1 },
  "3.3 KPI":               { "tool_hints": ["KPI"],                          "required_tool_calls": 1 },
  "4.1 H123":              { "tool_hints": ["H123", "热点"],                  "required_tool_calls": 1 },
  "4.2 创新重点":          { "tool_hints": ["创新重点"],                     "required_tool_calls": 1 },
  "4.3 战略专题":          { "tool_hints": ["战略专题", "关键问题"],          "required_tool_calls": 1 },
  "4.4 新兴机会":          { "tool_hints": ["新兴机会", "web_search"],        "required_tool_calls": 2 },
  "5.1 竞争战略":          { "tool_hints": ["竞争战略"],                     "required_tool_calls": 1 },
  "5.2 中央平台":          { "tool_hints": ["中央平台"],                     "required_tool_calls": 1 },
  "5.3 业务设计":          { "tool_hints": ["业务设计"],                     "required_tool_calls": 1 },
  "5.4 主要风险":          { "tool_hints": ["风险", "web_search"],           "required_tool_calls": 2 },
  "6.1 战略举措":          { "tool_hints": ["战略举措"],                     "required_tool_calls": 1 },
  "6.2 年度目标":          { "tool_hints": ["年度目标"],                     "required_tool_calls": 1 },
  "6.3 重点项目":          { "tool_hints": ["重点项目"],                     "required_tool_calls": 1 },
  "7.1 组织架构":          { "tool_hints": ["组织架构"],                     "required_tool_calls": 1 },
  "7.2 流程变革":          { "tool_hints": ["流程变革"],                     "required_tool_calls": 1 },
  "8.1 人才盘点":          { "tool_hints": ["人才盘点"],                     "required_tool_calls": 1 },
  "8.2 人才规划":          { "tool_hints": ["人才规划"],                     "required_tool_calls": 1 },
  "9.1 企业文化":          { "tool_hints": ["企业文化"],                     "required_tool_calls": 1 },
  "9.2 其他资源":          { "tool_hints": ["其他资源"],                     "required_tool_calls": 1 },
  "10.1 财务预测":         { "tool_hints": ["财务预测"],                     "required_tool_calls": 1 }
}
```

- [ ] **Step 6: 验证 JSON 解析**

```bash
python -c "import json; s = json.load(open('D:/memory/slide_spec_schema.json', encoding='utf-8')); print('image_field:', 'image_field' in s); print('tool_hints_field:', 'tool_hints_field' in s); print('sheet_presets count:', len(s['sheet_presets']))"
```

预期：
```
image_field: True
tool_hints_field: True
sheet_presets count: 36
```

---

## Task 4: 写 websearch.py（DuckDuckGoClient）

**Files:**
- Create: `D:\memory\websearch.py`

**Interfaces:**
- Consumes: `envutil.env()`, `duckduckgo_search.DDGS`
- Produces: `DuckDuckGoClient` 类，暴露 `search(query) -> list[dict]` 和 `TOOL_MAP` 注册为 LLM 工具

- [ ] **Step 1: 创建文件并写类**

新建 `D:\memory\websearch.py`：

```python
# -*- coding: utf-8 -*-
"""联网搜索客户端（DuckDuckGo）。作为 sp_data 的补充。

LLM 通过 TOOL_MAP 注册 web_search 工具调用；agent.py 把它和 iDSTE 工具一起注入。
"""
import logging
from envutil import env

log = logging.getLogger(__name__)


class DuckDuckGoClient:
    """封装 duckduckgo-search 包。失败抛异常，由调用方兜底。"""

    def __init__(self, max_results: int = 5, timeout: int = 30):
        from duckduckgo_search import DDGS
        self.ddgs = DDGS()
        self.max_results = max_results
        self.timeout = timeout

    def search(self, query: str) -> list[dict]:
        # 返回 [{title, href, body}, ...]
        results = list(self.ddgs.text(
            query,
            max_results=self.max_results,
            timeout=self.timeout,
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


def get_client():
    """工厂方法：从 env 读取配置，返回 client。"""
    if env("WEBSEARCH_ENABLED", "true").lower() != "true":
        raise ValueError("WEBSEARCH_ENABLED=false，禁用了联网搜索")
    return DuckDuckGoClient(
        max_results=int(env("WEBSEARCH_MAX_RESULTS", "5")),
        timeout=int(env("WEBSEARCH_TIMEOUT", "30")),
    )


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
```

- [ ] **Step 2: 运行 __main__ 测试**

```bash
cd D:\memory && python websearch.py "中国 矿山 安全 行业 报告 2025"
```

预期：打印 ≥3 条搜索结果（每条带 title/snippet/url），最后打印"共 N 条结果"。

如果网络不可达 → 打印 `FAIL: ...` 退出码 1，这是预期的（公司内网可能屏蔽外网），不算错误，标记任务为"代码就绪，待网络测试"。

- [ ] **Step 3: 验证 LLM tool schema**

```bash
python -c "import websearch; print(websearch.WEB_SEARCH_TOOL_SCHEMA['function']['name'])"
```

预期：`web_search`

---

## Task 5: 写 image_client.py（QwenImageClient）

**Files:**
- Create: `D:\memory\image_client.py`

**Interfaces:**
- Consumes: `envutil.env()` 读 QWEN_IMAGE_URL/MODEL/TOKEN
- Produces: `QwenImageClient` 类，暴露 `generate(prompt, style, size) -> bytes` (PNG)

- [ ] **Step 1: 创建文件**

新建 `D:\memory\image_client.py`：

```python
# -*- coding: utf-8 -*-
"""Qwen-Image-2512 图片生成客户端。

POST {QWEN_IMAGE_URL}/v1/images/generations
Headers: XSRF-TOKEN, Content-Type
Body: {"model": "Qwen-Image-2512", "prompt": ..., "n": 1, "size": ...}
Response: {"data": [{"url": "..."}]}
→ 客户端下载 url 的 PNG bytes 返回
"""
import os
import time
import logging
import requests
from envutil import env

log = logging.getLogger(__name__)


class QwenImageError(Exception):
    pass


class QwenImageClient:
    def __init__(self, base_url: str = None, model: str = None,
                 token: str = None, timeout: int = 60, size: str = "1024x1024"):
        self.base_url = (base_url or env("QWEN_IMAGE_URL")).rstrip("/")
        self.model = model or env("QWEN_IMAGE_MODEL")
        self.token = token or env("QWEN_IMAGE_TOKEN")
        self.timeout = timeout
        self.size = size

    def _headers(self):
        return {
            "XSRF-TOKEN": self.token,
            "Content-Type": "application/json",
        }

    def generate(self, prompt: str, style: str = "minimal", size: str = None) -> bytes:
        """调 Qwen-Image API，返回 PNG bytes。失败 raise QwenImageError。"""
        size = size or self.size
        url = f"{self.base_url}/v1/images/generations"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "n": 1,
            "size": size,
        }
        # style 仅作为 prompt 后缀附加，不发到 API（API 字段未确认）
        full_prompt = f"{prompt}, style: {style}" if style else prompt
        payload["prompt"] = full_prompt

        log.info(f"[qwen-image] POST {url} prompt={full_prompt[:60]}...")
        t0 = time.time()
        try:
            r = requests.post(url, json=payload, headers=self._headers(), timeout=self.timeout)
        except requests.Timeout as e:
            raise QwenImageError(f"timeout after {self.timeout}s") from e
        except requests.ConnectionError as e:
            raise QwenImageError(f"connection error: {e}") from e

        latency = time.time() - t0

        if r.status_code >= 500:
            raise QwenImageError(f"server error {r.status_code}: {r.text[:200]}")
        if r.status_code >= 400:
            raise QwenImageError(f"client error {r.status_code}: {r.text[:200]}")

        try:
            data = r.json()
        except Exception as e:
            raise QwenImageError(f"invalid json: {e}; body: {r.text[:200]}") from e

        items = data.get("data", [])
        if not items or "url" not in items[0]:
            raise QwenImageError(f"no url in response: {data}")

        img_url = items[0]["url"]
        log.info(f"[qwen-image] got url in {latency:.1f}s, downloading...")
        try:
            img_r = requests.get(img_url, timeout=self.timeout)
            img_r.raise_for_status()
            return img_r.content
        except Exception as e:
            raise QwenImageError(f"download failed: {e}") from e

    def save(self, png_bytes: bytes, path: str):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "wb") as f:
            f.write(png_bytes)


if __name__ == "__main__":
    import sys
    prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "minimalist blue gradient, navy and ice blue, professional"
    try:
        client = QwenImageClient()
        png = client.generate(prompt, style="minimal")
        out_path = "output/test_qwen_image.png"
        client.save(png, out_path)
        print(f"OK: {len(png)} bytes saved to {out_path}")
    except Exception as e:
        print(f"FAIL: {type(e).__name__}: {e}")
        sys.exit(1)
```

- [ ] **Step 2: 运行 __main__ 测试**

```bash
cd D:\memory && python image_client.py
```

预期：打印 `OK: NNNNN bytes saved to output/test_qwen_image.png`，生成的文件能用图片查看器打开。

如果网络/VPN 不可达 → `FAIL: ...` 退出码 1。任务视为"代码就绪，待网络测试"。

- [ ] **Step 3: 验证异常路径**

```bash
cd D:\memory && python -c "
from image_client import QwenImageClient, QwenImageError
c = QwenImageClient(base_url='http://127.0.0.1:1', timeout=2)
try:
    c.generate('test', style='minimal')
    print('FAIL: should have raised')
except QwenImageError as e:
    print(f'OK raised: {e}')
except Exception as e:
    print(f'OK raised (other): {type(e).__name__}: {e}')
"
```

预期：打印 `OK raised: ...`（不抛 `FAIL: should have raised`）。

---

## Task 6: 写 image_pipeline.py（augment_slide_spec）

**Files:**
- Create: `D:\memory\image_pipeline.py`

**Interfaces:**
- Consumes: `QwenImageClient` 实例、slide_spec dict、cache 目录
- Produces: 修改后的 slide_spec（每个有图的 slide 都有 `image.local_path`）

- [ ] **Step 1: 创建文件**

新建 `D:\memory\image_pipeline.py`：

```python
# -*- coding: utf-8 -*-
"""图片生成 pipeline：把 slide_spec 里需要图的 slide 调 Qwen-Image，
按 cache 命中 / 强制 vs 可选 / 重试 决策，写入本地 cache 并补 local_path。
"""
import os
import time
import json
import hashlib
import logging
from typing import Optional
from envutil import env

log = logging.getLogger(__name__)


# 必须有图的关键 layout
KEY_LAYOUTS = {"cover", "section", "conclusion"}


def _cache_key(prompt: str, style: str, size: str) -> str:
    raw = f"{prompt}|{style}|{size}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def _default_image_for(slide: dict, palette: str = "Midnight Executive") -> dict:
    """为缺失 image 字段的 key layout 生成兜底 image 配置。"""
    title = slide.get("title", "section")
    return {
        "prompt": (
            f"professional minimal illustration for a presentation section "
            f'titled "{title}", {palette} palette, no text, abstract'
        ),
        "zone": 5,
        "aspect": "16:9",
        "style": "minimal",
        "required": True,
    }


def _normalize(slide_spec: dict) -> None:
    """in-place：cover/section/conclusion 缺 image 自动注入；required 强制 True。"""
    for slide in slide_spec.get("slides", []):
        layout = slide.get("layout", "")
        if layout in KEY_LAYOUTS and not slide.get("image"):
            slide["image"] = _default_image_for(slide)
        if layout in KEY_LAYOUTS and slide.get("image") is not None:
            slide["image"].setdefault("required", True)


def augment_slide_spec(
    slide_spec: dict,
    client,                       # QwenImageClient 实例
    cache_dir: Optional[str] = None,
    on_progress=None,             # callable(slide_idx, success, cached, latency_ms) -> None
    verbose: bool = True,
) -> dict:
    """遍历 slides，缺图调 Qwen-Image。in-place 修改 slide_spec，返回它。"""
    cache_dir = cache_dir or env("IMAGE_CACHE_DIR", "cache/images")
    os.makedirs(cache_dir, exist_ok=True)
    size = client.size

    _normalize(slide_spec)

    for idx, slide in enumerate(slide_spec.get("slides", [])):
        img = slide.get("image")
        if not img:
            continue
        prompt = img.get("prompt", "")
        style = img.get("style", "minimal")
        required = img.get("required", True)

        key = _cache_key(prompt, style, size)
        png_path = os.path.join(cache_dir, f"{key}.png")
        meta_path = os.path.join(cache_dir, f"{key}.json")

        # 命中 cache
        if os.path.exists(png_path) and os.path.getsize(png_path) > 0:
            if verbose:
                log.info(f"[image] slide {idx} cache hit: {key}")
            slide["image"]["local_path"] = png_path
            if on_progress:
                on_progress(idx, True, True, 0)
            continue

        # 调 Qwen-Image（重试 2 次共 3 次）
        png_bytes = None
        last_err = None
        for attempt in (1, 2, 3):
            try:
                t0 = time.time()
                png_bytes = client.generate(prompt, style=style, size=size)
                latency_ms = int((time.time() - t0) * 1000)
                last_err = None
                break
            except Exception as e:
                last_err = e
                if verbose:
                    log.warning(f"[image] slide {idx} attempt {attempt} failed: {e}")
                if attempt < 3:
                    time.sleep(2 ** attempt)

        if png_bytes is None:
            if required:
                raise RuntimeError(
                    f"slide {idx} ({slide.get('title', '')}): required image failed after 3 attempts: {last_err}"
                ) from last_err
            if verbose:
                log.warning(f"[image] slide {idx} optional image skipped: {last_err}")
            del slide["image"]  # 丢掉，避免 render 报空
            if on_progress:
                on_progress(idx, False, False, 0)
            continue

        # 写 cache
        try:
            with open(png_path, "wb") as f:
                f.write(png_bytes)
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump({
                    "prompt": prompt, "style": style, "size": size,
                    "created_at": time.time(), "latency_ms": latency_ms,
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            if verbose:
                log.warning(f"[image] cache write failed (continuing): {e}")

        slide["image"]["local_path"] = png_path
        if on_progress:
            on_progress(idx, True, False, latency_ms)

    return slide_spec


if __name__ == "__main__":
    from image_client import QwenImageClient
    fake = {
        "slides": [
            {"layout": "cover", "title": "Test Cover"},
            {"layout": "bullets", "title": "P1"},
            {"layout": "section", "title": "Test Section"},
            {"layout": "bullets", "title": "P2"},
            {"layout": "conclusion", "title": "End"},
        ]
    }
    print("Before:", json.dumps(fake, ensure_ascii=False, indent=2))
    try:
        client = QwenImageClient()
        result = augment_slide_spec(fake, client, verbose=True)
        print("After:", json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"FAIL: {type(e).__name__}: {e}")
```

- [ ] **Step 2: 验证 import + 函数签名**

```bash
python -c "from image_pipeline import augment_slide_spec, _normalize, _default_image_for, KEY_LAYOUTS; print('KEY_LAYOUTS =', KEY_LAYOUTS); print('_normalize ok')"
```

预期：
```
KEY_LAYOUTS = {'cover', 'section', 'conclusion'}
_normalize ok
```

- [ ] **Step 3: 验证 _normalize 行为（不调 API）**

```bash
python -c "
import image_pipeline
spec = {'slides': [
    {'layout': 'cover', 'title': 'T'},      # 应注入 image
    {'layout': 'bullets', 'title': 'B'},    # 不动
    {'layout': 'section', 'title': 'S', 'image': {'prompt': 'p', 'zone': 5, 'aspect': '16:9', 'style': 'minimal'}},  # 缺 required
    {'layout': 'section', 'title': 'S2', 'image': {'prompt': 'p', 'zone': 5, 'aspect': '16:9', 'style': 'minimal', 'required': False}},  # 在 key layout
]}
image_pipeline._normalize(spec)
import json
print(json.dumps(spec, ensure_ascii=False, indent=2))
"
```

预期：
- cover slide 多了 `image` 字段，`required: True`
- bullets 不变
- section slide 1 补了 `required: True`
- section slide 2 `required` 从 False 变 True（因为是 key layout）

- [ ] **Step 4: 运行 __main__（需网络）**

```bash
cd D:\memory && python image_pipeline.py
```

预期：3 张图生成（cover / section / conclusion），写入 `cache/images/`，slide_spec 多了 `image.local_path`。如果网络失败 → `FAIL: ...`，标记任务为"代码就绪，待网络测试"。

---

## Task 7: 更新 prompts.py（image 规则 + 3 条 sp_data 硬规则）

**Files:**
- Modify: `D:\memory\prompts.py`

**Interfaces:**
- Consumes: 现有 3 个 prompt builder
- Produces: SLIDE_SPEC_FROM_XLSX_PROMPT 含 image 字段规则；XLSX_DATA_PROMPT 含 3 条 sp_data 硬规则 + sheet_presets 注入

- [ ] **Step 1: 在 SLIDE_SPEC_FROM_XLSX_PROMPT 加 image 字段说明**

读取 `prompts.py` 第 125-160 行（SLIDE_SPEC_FROM_XLSX_PROMPT 段），在 "# 8 种 layout（每页只用一种）" 之后插入新段：

```python
# 图片字段规则（v2 新增）
{image_field_doc}
```

- [ ] **Step 2: 在 XLSX_DATA_PROMPT 加 3 条硬规则**

读取 `prompts.py` 第 71-119 行（XLSX_DATA_PROMPT 段），在 "# 四、关键硬规则" 列表末尾追加：

```
10. **强制 sp_data**：sheet 列表里有"sp_data"提示的 sheet，**每一行**的数据
    都必须来自 sp_data 工具返回，禁止凭印象/行业常识编写。
    数字、姓名、部门、金额——任何具体事实都需 sp_data 支撑。
11. **软提示 web_search**：sheet 提示里有"web_search"时，先 sp_data
    拿结构化数据，再用 web_search 补背景信息/最新动态。sp_data 为主。
12. **type2 redirect 处理**：sp_data 返回 view_url 时，把 url 复制到
    对应单元格（如"参考链接"列），不要试图自己生成图表。
```

- [ ] **Step 3: 修 XLSX_DATA_PROMPT 让其支持 sheet_presets 注入**

把现有 `XLSX_DATA_PROMPT` 模板里的 `# 完整模板 schema（所有 sheet 的列结构参考，只在选中的 sheet 范围内输出数据）：\n\n{full_schema}` 替换为：

```python
{full_schema}

# 目标 sheet 的 tool_hints 预设（必须按此提示先调对应工具）
{sheet_presets_doc}
```

- [ ] **Step 4: 改 build_xlsx_data_prompt 函数注入 sheet_presets**

找到 `build_xlsx_data_prompt(target_sheets)` 函数（在文件底部），替换为：

```python
def build_xlsx_data_prompt(target_sheets):
    """动态生成 XLSX_DATA_PROMPT，target_sheets 来自 intent_recognize。"""
    full_schema = _get_schema_text()
    target_list = "\n".join(f"- {s}" for s in target_sheets)
    # 加载 sheet_presets
    try:
        schema = _load_slide_spec_schema()
        presets = schema.get("sheet_presets", {})
        preset_lines = []
        for s in target_sheets:
            p = presets.get(s)
            if p:
                preset_lines.append(
                    f"- **{s}**: tool_hints={p.get('tool_hints', [])}, "
                    f"required_tool_calls={p.get('required_tool_calls', 1)}"
                )
            else:
                preset_lines.append(f"- **{s}**: (无预设)")
        sheet_presets_doc = "\n".join(preset_lines) if preset_lines else "（无预设）"
    except Exception:
        sheet_presets_doc = "（加载预设失败，按需调工具即可）"
    return XLSX_DATA_PROMPT.format(
        target_sheets=target_list,
        full_schema=full_schema,
        sheet_presets_doc=sheet_presets_doc,
    )
```

- [ ] **Step 5: 改 build_slide_spec_from_xlsx_prompt 注入 image 字段说明**

找到 `build_slide_spec_from_xlsx_prompt(xlsx_data, user_request)` 函数，替换为：

```python
def build_slide_spec_from_xlsx_prompt(xlsx_data, user_request):
    """动态生成 SLIDE_SPEC_FROM_XLSX_PROMPT（含 xlsx 数据 + image 字段说明）。"""
    layouts_doc, rules_doc, render_doc = _build_slide_spec_from_xlsx_prompt()
    # 加载 image_field 文档
    try:
        schema = _load_slide_spec_schema()
        img = schema.get("image_field", {})
        field_lines = "\n".join(
            f"- **{n}** ({f.get('type','?')}, {f.get('desc','')}"
            + (f", enum={f.get('enum')}" if f.get('enum') else "")
            + f", required={f.get('required', False)})"
            for n, f in img.get("fields", {}).items()
        )
        image_field_doc = (
            f"# 图片字段（v2 新增，可选）\n{img.get('description','')}\n\n{field_lines}\n\n"
            f"**重要**：cover / section / conclusion 三类 layout 必须填 image 字段。"
        )
    except Exception as e:
        image_field_doc = f"# 图片字段（加载失败：{e}）"
    import json
    xlsx_json_str = json.dumps(xlsx_data, ensure_ascii=False, indent=2)
    xlsx_schema_doc = f"""# xlsx 数据（用户已填好的内容）

```json
{xlsx_json_str}
```

# 用户原始需求
{user_request}
"""
    return SLIDE_SPEC_FROM_XLSX_PROMPT.format(
        xlsx_schema_doc=xlsx_schema_doc,
        slide_layouts_doc=layouts_doc,
        slide_rules_doc=rules_doc,
        render_constraints_doc=render_doc,
        image_field_doc=image_field_doc,
    )
```

- [ ] **Step 6: 验证 prompts.py 导入和长度**

```bash
cd D:\memory && python -c "
import prompts
p1 = prompts.build_intent_recognition_prompt()
p2 = prompts.build_xlsx_data_prompt(['1.1 业绩差距分析', '2.1 宏观环境分析', '2.6 整体对手分析'])
print('intent prompt 长度:', len(p1))
print('xlsx data prompt 长度:', len(p2))
print('xlsx prompt 含 sheet_presets:', 'sheet_presets' in p2 or 'tool_hints' in p2)
"
```

预期：
```
intent prompt 长度: <与之前相近>
xlsx data prompt 长度: <与之前相近>
xlsx prompt 含 sheet_presets: True
```

- [ ] **Step 7: 验证 slide-spec prompt 含 image 字段**

```bash
cd D:\memory && python -c "
import prompts
fake = {'sheets': [{'sheet_name': '1.1 业绩差距', 'headers': ['A'], 'rows': [['x']]}]}
p = prompts.build_slide_spec_from_xlsx_prompt(fake, 'test')
print('slide-spec prompt 长度:', len(p))
print('含 image_field_doc:', '图片字段' in p or 'image_field' in p)
print('含 zone/aspect/style:', all(k in p for k in ['zone', 'aspect', 'style']))
"
```

预期：长度与之前接近（多 200-400 字 image 文档），含 image 相关关键词。

---

## Task 8: 更新 agent.py（DI + tool_call_stats + image_client 注入）

**Files:**
- Modify: `D:\memory\agent.py`

**Interfaces:**
- Consumes: image_client / image_pipeline / websearch 模块
- Produces: `generate_pptx_from_xlsx` 接 `image_client=None` 参数；`generate_xlsx_data` 返回 `tool_call_stats`

- [ ] **Step 1: 在文件顶部加 import**

在 `agent.py` 顶部 import 段（约第 12-22 行）添加：

```python
import image_client as image_client_mod
import image_pipeline as image_pipeline_mod
import websearch as websearch_mod
import qa as qa_mod
```

- [ ] **Step 2: 加 tool_call_stats 累计器到 generate_xlsx_data**

找到 `generate_xlsx_data` 函数（约 100-159 行），把调用 `llm_client.run_agent_loop` 那段改为：

```python
    # 合并 web_search tool map，并包一层计数
    tool_call_stats = {"__all__": {}}  # {sheet_name: {tool_name: count}}；sheet 难识别，暂累计到 __all__

    def _make_counting_wrapper(name, fn):
        def wrapper(**kwargs):
            tool_call_stats["__all__"].setdefault(name, 0)
            tool_call_stats["__all__"][name] += 1
            return fn(**kwargs)
        wrapper.__name__ = f"counted_{name}"
        return wrapper

    full_tool_map = {}
    for name, fn in dict(tool_map).items():
        full_tool_map[name] = _make_counting_wrapper(name, fn)
    for name, fn in websearch_mod.TOOL_MAP.items():
        full_tool_map[name] = _make_counting_wrapper(name, fn)

    final_text = llm_client.run_agent_loop(
        system_prompt,
        user_input,
        full_tool_map,
        tools_schema,
        max_turns=max_turns,
        verbose=verbose,
    )
    xlsx_data = _parse_json(final_text)

    # 兜底：只保留 intent.sheets_to_fill 里的 sheet
    xlsx_data["sheets"] = [
        s for s in xlsx_data.get("sheets", [])
        if s.get("sheet_name", "").strip() in sheets
    ]
    # 加 tool_call_stats
    xlsx_data["tool_call_stats"] = tool_call_stats
    return intent, xlsx_data
```

- [ ] **Step 3: 在 generate_pptx_from_xlsx 加 image_client / enable_qa 参数**

找到 `generate_pptx_from_xlsx` 函数签名，替换为：

```python
def generate_pptx_from_xlsx(
    user_input,
    xlsx_path,
    llm_client=None,
    prompts_module=None,
    template_path=None,
    image_client=None,           # 【新】QwenImageClient 实例
    enable_images=True,            # 【新】
    enable_qa=False,               # 【新】默认关
    qa_runner=None,                # 【新】
    output_dir="output",
    verbose=True,
):
    """PPT 流程主体：读 xlsx + LLM 提 slide-spec → render.js → pptx。
    
    Args:
        user_input: 自然语言需求
        xlsx_path: 已填 xlsx 路径
        image_client: QwenImageClient（None 时默认新建）
        enable_images: 是否启用图片生成（False 跳过整个 pipeline）
        enable_qa: 是否跑完做 QA
        qa_runner: qa.run 函数（None 时默认 qa_mod.run）
    """
    llm_client = llm_client or llm
    prompts_module = prompts_module or prompts
    template_path = template_path or _default_template_path()

    # 1) 读 xlsx
    if verbose:
        print(f"[ppt] 读 xlsx: {xlsx_path}")
    xlsx_data = xlsx_reader.read_template(xlsx_path)
    if not xlsx_data["sheets"]:
        raise ValueError(f"xlsx 没有任何数据 sheet: {xlsx_path}")

    # 2) LLM 提 slide-spec
    system_prompt = prompts_module.build_slide_spec_from_xlsx_prompt(xlsx_data, user_input)
    if verbose:
        print(f"[ppt] system prompt 长度: {len(system_prompt)}")

    resp = llm_client.chat(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ],
        max_tokens=12000,
    )
    text = llm_client._msg_text(resp)
    if verbose:
        print(f"[ppt] slide-spec 长度: {len(text)}")
    slide_spec = _parse_json(text)

    # 3) 【新】图片生成 pipeline
    if enable_images:
        if image_client is None:
            try:
                image_client = image_client_mod.QwenImageClient()
            except Exception as e:
                if verbose:
                    print(f"[ppt] QwenImageClient 初始化失败，跳过图片: {e}")
                image_client = None
        if image_client is not None:
            try:
                image_pipeline_mod.augment_slide_spec(
                    slide_spec, image_client, verbose=verbose,
                )
            except Exception as e:
                if verbose:
                    print(f"[ppt] 图片 pipeline 失败: {e}")
                # required=true 时已经 raise，否则继续

    # 4) 渲染 PPT
    if verbose:
        print(f"[ppt] 渲染 PPT（{len(slide_spec.get('slides', []))} 页）...")
    pptx_path = pptx_builder.build_pptx(slide_spec, output_dir=output_dir, verbose=verbose)

    result = {
        "xlsx_data": xlsx_data,
        "slide_spec": slide_spec,
        "pptx_path": pptx_path,
    }

    # 5) 【新】QA（可选）
    if enable_qa:
        runner = qa_runner or qa_mod.run
        qa_result = runner(pptx_path, output_dir=os.path.join(output_dir, "qa"), verbose=verbose)
        result["qa"] = qa_result

    return result
```

- [ ] **Step 4: 验证 agent.py 导入**

```bash
cd D:\memory && python -c "
import agent
print('agent module loaded')
print('generate_pptx_from_xlsx signature:', agent.generate_pptx_from_xlsx.__code__.co_varnames[:8])
print('generate_xlsx_data signature:', agent.generate_xlsx_data.__code__.co_varnames[:8])
"
```

预期：两个函数都被 import；`generate_pptx_from_xlsx` 包含 `image_client, enable_images, enable_qa, qa_runner`。

- [ ] **Step 5: 验证 tool_call_stats 字段在返回里**

```bash
cd D:\memory && python -c "
import agent
import inspect
src = inspect.getsource(agent.generate_xlsx_data)
print('_make_counting_wrapper' in src, 'tool_call_stats' in src, 'websearch_mod' in src)
"
```

预期：`True True True`

---

## Task 9: 更新 render.js（applyImageZone 函数）— ⏸ BLOCKED: 等待 PPT 模板

> **状态：等待用户提供 PPT 模板。** 模板到位后用 pptx skill 的  +  分析结构再开始此任务。详见 [[ppt-template-pending]]。

**Files:**
- Modify: `D:\memory\render.js`

**Interfaces:**
- Consumes: theme.json 的 image_zone 坐标表
- Produces: `applyImageZone(slide, theme)` 函数，在每个 layout handler 末尾调用

- [ ] **Step 1: 读取 render.js 顶部**

```bash
head -50 D:\memory\render.js
```

确认 theme.json 加载逻辑（应该有 `const theme = require('./theme.json')` 之类）。

- [ ] **Step 2: 加 applyImageZone 函数**

在 `render.js` 中**最后一个 layout handler 之后**追加（如果文件末尾是导出/收尾，加在导出之前）：

```javascript
/**
 * 把 slide.image 贴到指定 9 宫格位置。
 * 按 aspect 适配 zone 尺寸。
 */
function applyImageZone(slide, theme) {
  if (!slide.image || !slide.image.local_path) return;
  const fs = require('fs');
  if (!fs.existsSync(slide.image.local_path)) {
    console.warn(`[image] file not found: ${slide.image.local_path}`);
    return;
  }

  const zone = theme.image_zone[String(slide.image.zone || 5)];
  if (!zone) {
    console.warn(`[image] invalid zone: ${slide.image.zone}`);
    return;
  }

  const { x, y, w, h } = zone;
  // 按 aspect 适配
  const aspect = slide.image.aspect || '16:9';
  const [aw, ah] = aspect.split(':').map(Number);
  let imgW = w, imgH = h;
  const zoneAspect = w / h;
  const targetAspect = aw / ah;
  if (targetAspect > zoneAspect) {
    // 图比 zone 宽 → 按高填充
    imgH = h;
    imgW = h * targetAspect;
  } else {
    imgW = w;
    imgH = w / targetAspect;
  }
  // 居中
  const offX = x + (w - imgW) / 2;
  const offY = y + (h - imgH) / 2;

  slide.shapes.image = {
    path: slide.image.local_path,
    x: offX,
    y: offY,
    w: imgW,
    h: imgH,
  };
}
```

- [ ] **Step 3: 在每个 layout handler 末尾调用 applyImageZone**

对 8 个 layout handler（title/section/bullets/two_col/table/chart/big_stat/conclusion），在它们构造好 `slide.shapes` 之后、返回之前，加一行：

```javascript
applyImageZone(slide, theme);
```

具体位置根据现有 render.js 结构决定——找到每个 handler 函数的 `return` 语句之前。

- [ ] **Step 4: 验证 JS 语法**

```bash
cd D:\memory && node -c render.js
```

预期：没有语法错误（node 静默退出，exit code 0）。

- [ ] **Step 5: 验证 zone 计算正确**

```bash
cd D:\memory && node -e "
const theme = require('./theme.json');
console.log('zone 5 (居中):', theme.image_zone['5']);
console.log('zone 9 (右上):', theme.image_zone['9']);
"
```

预期：
```
zone 5 (居中): { x: 4.5, y: 2.0, w: 4.0, h: 2.5 }
zone 9 (右上): { x: 8.5, y: 0.5, w: 4.0, h: 1.5 }
```

---

## Task 10: 写 qa.py（thumbnail + soffice QA 工具链）— ⏸ BLOCKED: 等待 PPT 模板

> **状态：依赖 PPT 模板。** QA 检查项（重叠/溢出/对比度）需要先确定模板的 layout 与字号范围。模板到位后用 pptx skill 跑 thumbnail 做基线再实现检查逻辑。

**Files:**
- Create: `D:\memory\qa.py`

**Interfaces:**
- Consumes: pptx 路径，pptx skill 的 scripts（thumbnail.py, soffice.py）
- Produces: `{thumbs_path, pdf_path, slide_images, issues, ok}`

- [ ] **Step 1: 创建文件**

新建 `D:\memory\qa.py`：

```python
# -*- coding: utf-8 -*-
"""PPT 视觉 QA 工具链。

调 pptx skill 的 scripts：
- thumbnail.py  → 缩略图网格
- office/soffice.py → 转 PDF
- pdftoppm     → PDF 转单页 jpg
"""
import os
import sys
import shutil
import subprocess
import logging

log = logging.getLogger(__name__)

# pptx skill 路径
SKILL_DIR = r"C:\Users\92047\.claude\skills\pptx"
THUMBNAIL_SCRIPT = os.path.join(SKILL_DIR, "scripts", "thumbnail.py")
SOFFICE_SCRIPT = os.path.join(SKILL_DIR, "scripts", "office", "soffice.py")


def run(pptx_path: str, output_dir: str = "output/qa", verbose: bool = True) -> dict:
    """跑完整 QA 流程，返回报告 dict。"""
    os.makedirs(output_dir, exist_ok=True)
    thumbs_dir = os.path.join(output_dir, "qa_thumbs")
    pdf_dir = os.path.join(output_dir, "qa_pdf")
    os.makedirs(thumbs_dir, exist_ok=True)
    os.makedirs(pdf_dir, exist_ok=True)

    result = {
        "thumbs_path": None,
        "pdf_path": None,
        "slide_images": [],
        "issues": [],
        "ok": True,
    }

    # 1) 缩略图
    try:
        if os.path.exists(THUMBNAIL_SCRIPT):
            cmd = [sys.executable, THUMBNAIL_SCRIPT, pptx_path]
            if verbose:
                log.info(f"[qa] thumb: {' '.join(cmd)}")
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            grid = os.path.join(thumbs_dir, "grid.jpg")
            # thumbnail.py 通常会把 grid.jpg 输出到 pptx 所在目录；移动到 thumbs_dir
            pptx_dir = os.path.dirname(os.path.abspath(pptx_path))
            for cand in [os.path.join(pptx_dir, "grid.jpg"),
                         os.path.join(pptx_dir, "thumbnail.jpg"),
                         os.path.join(thumbs_dir, "grid.jpg")]:
                if os.path.exists(cand) and cand != grid:
                    shutil.copy(cand, grid)
                    break
            if os.path.exists(grid):
                result["thumbs_path"] = grid
        else:
            result["issues"].append(f"thumbnail.py 不存在: {THUMBNAIL_SCRIPT}")
    except Exception as e:
        result["issues"].append(f"thumbnail 失败: {e}")

    # 2) PDF 转换
    try:
        if os.path.exists(SOFFICE_SCRIPT):
            cmd = [sys.executable, SOFFICE_SCRIPT, "--headless", "--convert-to", "pdf",
                   "--outdir", pdf_dir, pptx_path]
            if verbose:
                log.info(f"[qa] pdf: {' '.join(cmd)}")
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            pdf_name = os.path.splitext(os.path.basename(pptx_path))[0] + ".pdf"
            pdf_path = os.path.join(pdf_dir, pdf_name)
            if os.path.exists(pdf_path):
                result["pdf_path"] = pdf_path
            else:
                result["issues"].append(f"PDF 未生成: stdout={r.stdout[:200]}")
        else:
            result["issues"].append(f"soffice.py 不存在: {SOFFICE_SCRIPT}")
    except Exception as e:
        result["issues"].append(f"PDF 转换失败: {e}")

    # 3) PDF → 单页 jpg
    if result["pdf_path"]:
        try:
            cmd = ["pdftoppm", "-jpeg", "-r", "100", result["pdf_path"],
                   os.path.join(pdf_dir, "slide")]
            if verbose:
                log.info(f"[qa] pdftoppm: {' '.join(cmd)}")
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            for fn in sorted(os.listdir(pdf_dir)):
                if fn.startswith("slide-") and fn.endswith(".jpg"):
                    result["slide_images"].append(os.path.join(pdf_dir, fn))
        except FileNotFoundError:
            result["issues"].append("pdftoppm 未安装（Poppler）")
        except Exception as e:
            result["issues"].append(f"pdftoppm 失败: {e}")

    result["ok"] = len(result["issues"]) == 0
    return result


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python qa.py <pptx_path>")
        sys.exit(1)
    pptx = sys.argv[1]
    r = run(pptx)
    print(f"thumbs: {r['thumbs_path']}")
    print(f"pdf:    {r['pdf_path']}")
    print(f"slides: {len(r['slide_images'])}")
    print(f"issues: {r['issues']}")
    print(f"ok:     {r['ok']}")
```

- [ ] **Step 2: 验证 import + 工具脚本存在**

```bash
python -c "import qa; import os; print('thumbnail exists:', os.path.exists(qa.THUMBNAIL_SCRIPT)); print('soffice exists:', os.path.exists(qa.SOFFICE_SCRIPT))"
```

预期：
```
thumbnail exists: True
soffice exists: True
```

- [ ] **Step 3: 用历史 pptx 跑一次 QA**

```bash
cd D:\memory && ls output/*.pptx 2>/dev/null | head -1
```

如果存在 pptx：

```bash
cd D:\memory && python qa.py output/<some>.pptx
```

预期：打印 thumbs/pdf/slides 路径，issues 可能为空（视 LibreOffice 是否安装而定）。

如果 LibreOffice 没装 → PDF 转换会失败，issues 会出现 "PDF 转换失败"。

---

## Task 11: 更新 app.py（图片生成/QA checkbox + tool_call_stats UI）

**Files:**
- Modify: `D:\memory\app.py`

**Interfaces:**
- Consumes: agent 模块的新参数；qa 模块
- Produces: Tab 1 加 tool_call_stats 展示；Tab 2 加图片生成/QA checkbox

- [ ] **Step 1: 在 Tab 1 加 tool_call_stats 展示**

找到 Tab 1 的下载按钮之前（约第 150 行），在 `st.divider()` 之前插入：

```python
    # 工具调用统计（v2 新增）
    if st.session_state.get("last_tool_call_stats"):
        st.divider()
        st.subheader("📊 工具调用统计")
        stats = st.session_state["last_tool_call_stats"]
        for sn, calls in stats.items():
            sp_n = calls.get("sp_data", 0)
            ws_n = calls.get("web_search", 0)
            icon = "✅" if sp_n > 0 else "❌"
            st.caption(f"{icon} **{sn}**: sp_data × {sp_n}, web_search × {ws_n}")
```

- [ ] **Step 2: 在 generate_xlsx_data 调完后存 stats**

找到 `Tab 1` 中 `intent, xlsx_data = generate_xlsx_data(...)` 那段（约第 113 行），在 `st.session_state["last_intent"] = intent` 之后加：

```python
            st.session_state["last_tool_call_stats"] = xlsx_data.get("tool_call_stats", {})
```

- [ ] **Step 3: 在 Tab 2 加图片生成 / QA checkbox**

找到 `Tab 2` 中 `st.button("🚀 生成 PPT", ...)` 之前，加：

```python
    col1, col2 = st.columns(2)
    with col1:
        enable_images = st.checkbox("🎨 启用图片生成（Qwen-Image）", value=True, key="ppt_enable_images")
    with col2:
        enable_qa = st.checkbox("🔍 生成后做视觉 QA", value=False, key="ppt_enable_qa")
```

- [ ] **Step 4: 改 generate_pptx_from_xlsx 调用传新参数**

找到 Tab 2 中 `result = _gen(req_ppt or "...", xlsx_path_for_ppt, verbose=False)` 段，替换为：

```python
            from agent import generate_pptx_from_xlsx as _gen
            result = _gen(
                req_ppt or "生成完整分析报告的演示文稿",
                xlsx_path_for_ppt,
                enable_images=enable_images,
                enable_qa=enable_qa,
                verbose=False,
            )
```

- [ ] **Step 5: 在 Tab 2 加 QA 结果展示**

找到 Tab 2 的 `if st.session_state.get("last_pptx_path")` 块，在 download_button 之后加：

```python
            if result.get("qa"):
                qa_res = result["qa"]
                with st.expander("🔍 QA 报告", expanded=False):
                    if qa_res.get("thumbs_path"):
                        st.image(qa_res["thumbs_path"], caption="缩略图网格")
                    st.json({k: v for k, v in qa_res.items() if k != "slide_images"})
                    st.caption(f"共 {len(qa_res.get('slide_images', []))} 张单页 jpg")
```

- [ ] **Step 6: 验证 app.py 语法**

```bash
cd D:\memory && python -c "import app; print('app.py loads OK')"
```

预期：`app.py loads OK`（注意：import 会执行整个文件，如果 streamlit 配置有副作用，单独 run 可能问题；这里只测语法）。

如果 import 失败，定位报错行修复。

- [ ] **Step 7: 启动 streamlit 做 smoke test**

```bash
cd D:\memory && timeout 5 streamlit run app.py --server.headless true 2>&1 | head -10
```

预期：streamlit 启动信息（端口 8501），不报错立即崩。timeout 5 自动 kill。

---

## Task 12: 端到端验证 + STATUS.md 更新

**Files:**
- Modify: `D:\memory\STATUS.md`

**Interfaces:**
- Consumes: 所有前 11 任务的产出
- Produces: STATUS.md 反映 v3 架构

- [ ] **Step 1: 跑 xlsx 流程（不需要 LLM 真实调用也可以走 dry run）**

```bash
cd D:\memory && python -c "
import agent
# 只测 import 和签名
print('agent.generate_xlsx_data OK')
print('agent.generate_pptx_from_xlsx OK')
"
```

预期：无报错。

- [ ] **Step 2: 检查所有新模块导入**

```bash
cd D:\memory && python -c "
import image_client
import image_pipeline
import websearch
import qa
print('all new modules import OK')
"
```

预期：`all new modules import OK`

- [ ] **Step 3: 检查 theme 和 schema 关键字段**

```bash
cd D:\memory && python -c "
import json
t = json.load(open('theme.json', encoding='utf-8'))
s = json.load(open('slide_spec_schema.json', encoding='utf-8'))
print('theme.palette:', t['palette'])
print('theme.image_zone 数量:', len(t['image_zone']))
print('schema.image_field:', 'image_field' in s)
print('schema.tool_hints_field:', 'tool_hints_field' in s)
print('schema.sheet_presets 数量:', len(s['sheet_presets']))
"
```

预期：
```
theme.palette: Midnight Executive
theme.image_zone 数量: 9
schema.image_field: True
schema.tool_hints_field: True
schema.sheet_presets 数量: 36
```

- [ ] **Step 4: 检查 .env 关键项**

```bash
cd D:\memory && python -c "
from envutil import env
required = ['QWEN_IMAGE_URL', 'QWEN_IMAGE_MODEL', 'QWEN_IMAGE_TOKEN',
            'IMAGE_CACHE_DIR', 'WEBSEARCH_ENABLED', 'WEBSEARCH_PROVIDER']
for k in required:
    v = env(k)
    print(f'{k}: {v if v else \"(missing)\"}')
"
```

预期：所有 key 都有值（不是 missing）。

- [ ] **Step 5: 跑 __main__ smoke test（image_client）**

```bash
cd D:\memory && python image_client.py
```

预期：如果网络可达，打印 `OK: NNNNN bytes saved to output/test_qwen_image.png`；如果网络不可达，标记为"代码就绪"。

- [ ] **Step 6: 跑 __main__ smoke test（websearch）**

```bash
cd D:\memory && python websearch.py "中国 战略规划 行业 2025"
```

预期：同上。

- [ ] **Step 7: 更新 STATUS.md**

读 STATUS.md，在末尾追加 v3 章节：

```markdown
---

## v3 增量（2026-07-13）

### 新增能力
- Qwen-Image-2512 图片生成：cover/section/conclusion 必出，其他可选；9 宫格 zone 定位
- DuckDuckGo 联网搜索：sp_data 主 + web_search 补，XLSX_DATA_PROMPT 3 条硬规则
- 工具调用计数监控（方案 A）：每张 sheet 调几次 sp_data/web_search，UI 绿/黄/红
- sheet→tool hints 字段：36 张 sheet 预设表，LLM 看到 schema 就知道要调几次
- theme 升级：Midnight Executive 配色（深蓝+冰蓝）
- QA 工具链：thumbnail + soffice + pdftoppm（pptx skill 集成）

### 新增文件
- `image_client.py`、`image_pipeline.py`、`websearch.py`、`qa.py`
- `docs/superpowers/specs/2026-07-13-qwen-image-ppt-design.md`
- `docs/superpowers/plans/2026-07-13-qwen-image-ppt.md`

### 改动文件
- `theme.json`（Midnight Executive + image_zone）
- `slide_spec_schema.json`（image_field + tool_hints_field + sheet_presets）
- `prompts.py`（SLIDE_SPEC 加 image 规则 + XLSX_DATA 加 3 条 sp_data 硬规则）
- `agent.py`（DI 加 image_client / enable_qa / tool_call_stats）
- `render.js`（applyImageZone 函数）
- `app.py`（图片生成/QA checkbox + tool_call_stats UI）
- `.env` / `.env.example`（QWEN_IMAGE_* + WEBSEARCH_* 共 9 行）
- `requirements.txt`（加 duckduckgo-search）

### 验证状态
- [x] L1 单元：所有新模块 __main__ 段跑通（受网络/VPN 限制的标记为"代码就绪"）
- [ ] L2 集成：需要 LLM 真实跑（待 VPN 通）
- [ ] L3 端到端：需要 LLM 真实跑
- [ ] L4 视觉 QA：需要 LLM 真实跑出 pptx
```

- [ ] **Step 8: 最终验证 — 完整结构**

```bash
cd D:\memory && ls -la *.py theme.json slide_spec_schema.json .env requirements.txt | awk '{print $5, $9}'
```

预期：列出所有关键文件及大小。

---

## 交付物清单

完成所有 12 任务后，应该有：

- [ ] `image_client.py` — QwenImageClient + __main__
- [ ] `image_pipeline.py` — augment_slide_spec + __main__
- [ ] `websearch.py` — DuckDuckGoClient + TOOL_MAP + __main__
- [ ] `qa.py` — run() + __main__
- [ ] `theme.json` — Midnight Executive + 9 image_zone
- [ ] `slide_spec_schema.json` — image_field + tool_hints_field + 36 sheet_presets
- [ ] `prompts.py` — 3 个 prompt 都加新规则
- [ ] `agent.py` — DI 完整（image_client, enable_qa, tool_call_stats）
- [ ] `render.js` — applyImageZone + 8 handler 调用
- [ ] `app.py` — checkbox + stats UI
- [ ] `.env` / `.env.example` — 9 行新配置
- [ ] `requirements.txt` — duckduckgo-search
- [ ] `STATUS.md` — v3 增量章节
- [ ] 1 张端到端生成的 xlsx + pptx + grid.jpg（待 VPN 通后跑）

---

## 风险预案

| 风险 | 触发 | 应对 |
|---|---|---|
| Qwen-Image 网络不可达 | `ConnectTimeout` | image_client 抛 QwenImageError，pipeline 重试 3 次后按 required 决策 |
| DuckDuckGo 包不兼容 | `ImportError` | 提示 `pip install duckduckgo-search` |
| LibreOffice 未装 | soffice 失败 | qa.run 跳过 PDF，issues 标"soffice 缺失" |
| pdftoppm 未装 | 找不到命令 | qa.run 跳过单页 jpg，issues 标"Poppler 缺失" |
| 公司内网禁外网 | web_search 失败 | 跳过该次搜索，sp_data 仍可用 |
| LLM 仍不调 sp_data | 计数=0 | UI 红字提示，用户可手动加 |
| 36 sheet 预设名错 | intent 返回的 sheet 名匹配不到 preset | 预设不存在时回退到"无预设"+ 默认 required=1 |
