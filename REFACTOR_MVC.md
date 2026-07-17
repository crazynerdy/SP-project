# MVC（分层）重构方案

## 0. 目标与约束

**目标**：把当前 20+ 个平铺在根目录的 `.py` 按 MVC 变体（分层架构）归层，并把 361 行的 `app.py` 拆成 瘦入口 + View + Controller，实现真正的职责分离。

**硬约束（不可破）**：
- **不改任何业务逻辑**。`agent.py` 的 4 个函数、DI 签名、`llm/idste/prompts/...` 的实现一行不动；只是搬位置 + 修 import + 修资源路径定位。
- **PPT 模板待定**（`ppt-template-pending`）：`render.js` 的渲染逻辑、`qa.py`、PPT Tab 的业务流程代码内容不动。只允许搬文件位置和改路径常量。
- **单一真相源 / 可扩展**（`code-must-be-extensible`）：资源文件（`.env`/`theme.json`/`slide_spec_schema.json`/`render.js`）集中用 `PROJECT_ROOT` 锚点定位，不再各模块 `dirname(__file__)` 各找各的。

---

## 1. 为什么是"分层"而不是经典 MVC

Streamlit 是脚本式执行、无路由器，控件渲染（View）和回调（Controller）在同一个 rerun 流里天然耦合。硬拆 `models/ views/ controllers/` 三件套已在实践中证明可行，但 View/Controller 边界要这样定：

| 层 | 职责边界 | 禁止做 |
|---|---|---|
| **View** (`views/`) | 渲染 Streamlit 控件、布局、CSS；返回用户输入/点击事件 | 不调 agent、不写 session_state（只读显示） |
| **Controller** (`controllers/`) | 调 agent 编排业务、读写 session_state、用 `st.success/error/warning` 反馈 | 不布局控件、不写 CSS |
| **Model** (`models/`) | 外部服务封装 + 数据访问（取数/填表/渲染/图片/QA） | 不碰 `streamlit` |
| **基础设施** (`core/`) | env、路径锚点 | 不碰业务 |
| **脚本** (`scripts/`) | 一次性探针，不进主结构 | 不被正式模块 import |

---

## 2. 目标目录结构

```
D:\memory\
├─ app.py                     # 瘦入口（~80 行）：page config + 主题 + sidebar + hero + 路由
│
├─ core/                      # 基础设施
│   ├─ __init__.py
│   ├─ paths.py               # 【新】PROJECT_ROOT 锚点 + resource()
│   └─ envutil.py             # 改：.env 从 PROJECT_ROOT 读
│
├─ models/                    # Model 层（外部服务 + 数据访问）
│   ├─ __init__.py
│   ├─ llm.py
│   ├─ idste.py
│   ├─ websearch.py
│   ├─ prompts.py             # 改：schema 路径 + import
│   ├─ image_client.py
│   ├─ image_pipeline.py
│   ├─ qa.py
│   ├─ xlsx_reader.py         # 改：函数内 import
│   ├─ xlsx_exporter.py       # 改：函数内 import
│   └─ pptx_builder.py        # 改：render.js 路径
│
├─ controllers/               # Controller 层（业务编排）
│   ├─ __init__.py
│   ├─ agent.py               # 改 import；4 函数 + DI 不变
│   ├─ excel_controller.py    # 【新】从 app.py 抽出 Excel Tab 编排
│   └─ ppt_controller.py      # 【新】从 app.py 抽出 PPT Tab 编排
│
├─ views/                     # View 层（纯 UI 渲染）
│   ├─ __init__.py
│   ├─ ui_theme.py            # 改：theme.json 路径
│   ├─ layout.py              # 【新】sidebar + hero + 概览卡片（从 app.py 抽）
│   ├─ excel_view.py          # 【新】Excel Tab 控件渲染
│   └─ ppt_view.py            # 【新】PPT Tab 控件渲染
│
├─ scripts/                   # 一次性探针（不进 MVC）
│   ├─ login_mcp.py
│   ├─ discover.py
│   ├─ parse_discover.py
│   ├─ scan_tables.py
│   └─ probe_llm.py
│
├─ render.js                  # 留根（与 theme.json/schema 绑定，见 §4）
├─ theme.json                 # 留根
├─ slide_spec_schema.json     # 留根
├─ .env / .env.example / .gitignore
├─ .streamlit/config.toml
├─ package.json / requirements.txt / skills-lock.json
├─ README.md / PLAN.md / STATUS.md
└─ output/                    # 产物（gitignored）
```

---

## 3. PROJECT_ROOT 锚点（`core/paths.py`，新增）

```python
# -*- coding: utf-8 -*-
"""项目根锚点：所有资源文件统一从这里定位，模块怎么移动都不影响资源查找。"""
from pathlib import Path

# core/paths.py -> 向上一级 = 项目根
PROJECT_ROOT = Path(__file__).resolve().parent.parent

def resource(name: str) -> str:
    """返回项目根下某资源文件的绝对路径字符串。"""
    return str(PROJECT_ROOT / name)
```

**依赖方向**：`paths` 只用 `pathlib`，不依赖任何业务模块 → `envutil`/`prompts`/`ui_theme`/`pptx_builder` 单向依赖 `paths`，无循环。

---

## 4. 资源路径改动清单

> 关键约束：`render.js:15` 用 `__dirname` 找 `theme.json` + `slide_spec_schema.json`；`pptx_builder.py:17` 用 `dirname(__file__)` 找 `render.js`。所以 **render.js + theme.json + slide_spec_schema.json 必须同目录，且都留在根目录**。只有移动了的 Python 模块改路径常量。

| 文件 | 现状 | 改为 |
|---|---|---|
| `core/envutil.py:10-11` | `_HERE=dirname(__file__)`; `_ENV_PATH=_HERE/.env` | `from core.paths import resource`; `_ENV_PATH = resource(".env")` |
| `models/prompts.py:16,191` | `_HERE=dirname(__file__)`; 读 `_HERE/slide_spec_schema.json` | `from core.paths import resource`; 用 `resource("slide_spec_schema.json")` |
| `models/pptx_builder.py:17` | `RENDER_JS=dirname(__file__)/render.js` | `from core.paths import resource`; `RENDER_JS = resource("render.js")` |
| `views/ui_theme.py:15` | `_THEME_JSON=dirname(__file__)/theme.json` | `from core.paths import resource`; `_THEME_JSON = resource("theme.json")` |
| `render.js` | `__dirname` 找 theme/schema | **不动**（它们都在根目录，自洽） |

---

## 5. import 改动清单（逐文件，旧 → 新）

### `app.py`
```
import ui_theme                              → from views import ui_theme
import agent / from agent import (...)       → from controllers import agent
                                             （from controllers.agent import intent_recognize, save_xlsx, ...）
from agent import generate_xlsx_data（L166） → from controllers.agent import generate_xlsx_data
from envutil import env, run_with_timeout    → from core.envutil import env, run_with_timeout
import idste                                 → from models import idste
import xlsx_reader                           → from models import xlsx_reader
# DEV 热重载：importlib.reload(ui_theme) → reload(views.ui_theme 对应模块)
```

### `controllers/agent.py`
```
import idste                          → from models import idste
import llm                            → from models import llm
import prompts                        → from models import prompts
import xlsx_exporter                  → from models import xlsx_exporter
import xlsx_reader                    → from models import xlsx_reader
import pptx_builder                   → from models import pptx_builder
import image_client as image_client_mod         → from models import image_client as image_client_mod
import image_pipeline as image_pipeline_mod     → from models import image_pipeline as image_pipeline_mod
import websearch as websearch_mod               → from models import websearch as websearch_mod
import qa as qa_mod                             → from models import qa as qa_mod
from envutil import env               → from core.envutil import env
# __main__ 命令行入口：python agent.py "..." → python -m controllers.agent "..."（同步改 README）
```

### `models/` 内（每个文件的 envutil import）
```
idste.py:        from envutil import env, require    → from core.envutil import env, require
llm.py:          from envutil import require          → from core.envutil import require
websearch.py:    from envutil import env              → from core.envutil import env
image_client.py: from envutil import env              → from core.envutil import env
image_pipeline.py: from envutil import env            → from core.envutil import env
prompts.py:      from envutil import env              → from core.envutil import env
                 import xlsx_reader                   → from models import xlsx_reader
xlsx_reader.py:153（函数内） from envutil import env  → from core.envutil import env
xlsx_exporter.py:122（函数内）from envutil import env → from core.envutil import env
```

### `scripts/*`（探针，低优先级）
```
from envutil import require   → from core.envutil import require
from idste import ...         → from models.idste import ...
# scripts/ 子目录跑时根不在 sys.path：每个脚本顶部加
#   import sys, os
#   sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# 或统一用 python -m scripts.xxx 运行
```

### 每个 `__init__.py`（`core/ models/ controllers/ views/`）
新建空 `__init__.py`（标记为 Python 包）。

---

## 6. app.py 拆分设计（方案 B 核心）

### 现状
`app.py` 361 行同时做：页面配置 / 主题 / sidebar / hero / session_state 初始化 / 概览卡片 / Excel Tab（渲染+编排+健康检查+下载）/ PPT Tab（渲染+编排+下载+QA）。

### 拆分后职责

**`app.py`（瘦入口，~80 行）** — 只做骨架：
- `st.set_page_config` + `ui_theme.inject()`
- `views/layout.render_sidebar()` + `render_hero()` + `render_overview()`
- `session_state` 初始化（`history`/`last_*`/`active_tab`/`idste_healthy`）
- 路由：`if active_tab=="excel": excel_controller.run()` / `elif "ppt": ppt_controller.run()`

**`views/layout.py`（新）** — 从 app.py 抽：
- `render_sidebar()` — 品牌 + 导航 radio（写 `active_tab`）+ 提示 + 底部状态
- `render_hero()` — 调 `ui_theme.hero(...)`
- `render_overview(sheet_names, history, template_path, active_tab)` — 3 个 stat_card

**`views/excel_view.py`（新）** — 纯渲染，返回输入/事件：
```python
def render_excel_form(template_path, idste_healthy) -> dict | None:
    """渲染需求输入框 + 生成/重试按钮，返回 {request, clicked, retry}；iDSTE 不可达时 st.stop()。"""

def render_excel_results(tool_call_stats, xlsx_path) -> None:
    """渲染工具调用统计 + 下载区（只读 session_state）。"""
```

**`views/ppt_view.py`（新）** — 纯渲染：
```python
def render_ppt_form(history) -> dict | None:
    """渲染数据源选择 + 演示重点 + 图片/QA checkbox，返回 {xlsx_path, request, enable_images, enable_qa, clicked}。"""

def render_ppt_results(pptx_path, slide_spec, qa_res) -> None:
    """渲染下载 + QA 报告。"""
```

**`controllers/excel_controller.py`（新）** — 编排：
```python
def run(template_path, sheet_names, idste_healthy) -> None:
    """Excel Tab 完整控制器：调 view 渲染表单 -> 若点击则调 agent 编排 -> 写 session_state -> 调 view 渲染结果。"""
    ev = excel_view.render_excel_form(template_path, idste_healthy)
    if ev and ev["retry"]:
        st.session_state["idste_healthy"] = idste.health_check(); st.rerun(); return
    if ev and ev["clicked"] and ev["request"].strip():
        try:
            with st.spinner("正在生成 Excel..."):
                intent = intent_recognize(ev["request"], verbose=False)
                ... (原 app.py L159-179 的编排，调 generate_xlsx_data + save_xlsx，包在 run_with_timeout 里)
            st.session_state["history"].insert(0, {...})
            st.session_state["last_xlsx_path"] = ...
            st.session_state["last_tool_call_stats"] = ...
            st.success(...)
        except Exception as e: ...
    excel_view.render_excel_results(...)
```

**`controllers/ppt_controller.py`（新）** — 同理封装 PPT Tab 编排（调 `xlsx_reader.read_template` + `generate_pptx_from_xlsx`，写 `last_pptx_path/last_slide_spec/last_qa`）。**PPT 业务流程代码内容照搬，不改动**。

### Streamlit 注意点
- **session_state 读写**：由 controller 持有（rerun 后状态需保持，跨函数传参不如 session_state 自然）。view 只读显示。
- **`st.stop()`/`st.rerun()`**：保留在原语义位置（view 的表单不可达时 stop；controller 的重试 rerun）。
- **DEV 热重载**：`importlib.reload` 改为 reload `views.ui_theme` 模块对象。

---

## 7. 不改动清单（确认边界）

- `render.js`（一行不改，留根目录）
- `theme.json` / `slide_spec_schema.json` / `.env` / `.streamlit/`（留根，不动）
- `agent.py` 的 4 个函数体 + DI 签名（只改 import，逻辑不动）
- `llm/idste/prompts/websearch/image_client/image_pipeline/qa/xlsx_reader/xlsx_exporter/pptx_builder` 的函数实现（只改 import + 路径常量）
- `requirements.txt` / `package.json`（无新依赖）

---

## 8. 实施步骤（建议顺序，每步可独立冒烟）

1. **建包骨架**：`mkdir core models controllers views scripts` + 4 个 `__init__.py`。
2. **加 `core/paths.py`** + 改 `core/envutil.py` 的 `.env` 定位（此时 envutil 还在根，先原地改路径用 `PROJECT_ROOT`，再移动）。
   - *稳妥起见*：先在根目录新建 `paths.py` 让所有路径常量切到 `PROJECT_ROOT`，**冒烟通过后**再把 `paths.py`+`envutil.py` 一起移进 `core/` 并修 import。避免一次动太多。
3. **移 Model 层**：`llm/idste/websearch/prompts/image_client/image_pipeline/qa/xlsx_reader/xlsx_exporter/pptx_builder` → `models/`，逐个改 import + 路径常量。
   - 冒烟：`python -c "from models import llm, idste, prompts, pptx_builder, xlsx_reader, xlsx_exporter, image_client, image_pipeline, websearch, qa"`
4. **移 Controller 层**：`agent.py` → `controllers/agent.py`，改 import。
   - 冒烟：`python -c "from controllers import agent; print(agent.intent_recognize)"`
5. **移 View 层**：`ui_theme.py` → `views/ui_theme.py`，改 theme.json 路径。
6. **移探针**：5 个脚本 → `scripts/`，加 sys.path 兜底。
7. **拆 app.py**：抽 `views/layout.py` + `views/excel_view.py` + `views/ppt_view.py` + `controllers/excel_controller.py` + `controllers/ppt_controller.py`，`app.py` 瘦身到 ~80 行。
8. **端到端冒烟**：
   - `streamlit run app.py` 能起、两个 Tab 渲染正常、sidebar 导航切换正常。
   - `python -m controllers.agent "分析2025年公司SP战略规划完成度"` 命令行入口可用（需 VPN/LLM 可达；不可达至少不报 ImportError）。
   - Excel 流程跑通（生成 xlsx + 下载）；PPT 流程跑通（生成 pptx + 下载）。
9. **更新文档**：`README.md` 启动命令（`python -m controllers.agent`）+ 架构图；`STATUS.md` 追加重构记录。

---

## 9. 风险与回滚

| 风险 | 应对 |
|---|---|
| import 漏改致 `ImportError` | 每移一层就 `python -c "import ..."` 冒烟，不积累 |
| `xlsx_reader/exporter` 函数内 import 漏改 | §5 已单列，实现时 grep 复查 `from envutil` 全清 |
| Streamlit 拆分后 `session_state`/`rerun` 语义错乱 | controller 持有 session_state，view 只读；保持原 `st.stop/rerun` 位置；拆完端到端跑两流程 |
| 资源路径断（theme/schema/render.js/.env 找不到） | 全部走 `PROJECT_ROOT`；render.js 四件套留根；冒烟时确认 `ui_theme.inject()` 能加载 |
| 探针脚本 sys.path 问题 | 加兜底 `sys.path.insert`；优先级低，最后处理 |

**回滚**：纯结构重构 + git。每步独立提交，任一步冒烟失败即可 `git revert` 该步，不影响业务代码（业务逻辑本就没动）。

---

## 10. 工作量预估

- 步骤 1-6（归层 + import + 路径）：~60% 工作量，机械但需细致。
- 步骤 7（拆 app.py）：~30%，需小心 Streamlit 语义。
- 步骤 8-9（冒烟 + 文档）：~10%。
