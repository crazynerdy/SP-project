# SP 分析报告 Agent

公司内部工具：自然语言需求 → 拉取 iDSTE SP 数据 → 生成 Excel 报告 → 一键生成 PPT 演示。

## 架构

```
Streamlit (app.py)
   ├─ Tab 1：生成 Excel
   │    自然语言 → intent_recognize() → 选 sheet
   │           → generate_xlsx_data() (LLM + iDSTE 工具) → xlsx-ready JSON
   │           → save_xlsx() → output/<ts>_<intent>_<uuid>_data.xlsx
   │
   └─ Tab 2：生成 PPT（基于 Excel）
        选历史 / 上传 xlsx + 自然语言
           → xlsx_reader.read_template() → xlsx JSON
           → generate_pptx_from_xlsx() (LLM) → slide-spec JSON
           → （可选）image_pipeline（Qwen-Image 生成 cover/section/conclusion 图）
           → pptx_builder → node render.js → output/<ts>_<intent>_slides.pptx
```

四个核心函数（`agent.py`，全部支持 DI 注入）：

| 函数 | 作用 |
|---|---|
| `intent_recognize(user_input)` | 入口意图分类，路由到 Excel / PPT 流程 |
| `generate_xlsx_data(user_input, intent)` | Excel 流程：取数 + LLM 整理 → xlsx-ready JSON |
| `generate_pptx_from_xlsx(user_input, xlsx_path)` | PPT 流程：读 xlsx + LLM → slide-spec → render.js → pptx |
| `save_xlsx(xlsx_data, template_path)` | 把 xlsx-ready JSON 写入模板副本，返回路径 |

## 项目结构（MVC 分层）

```
app.py                 # 瘦入口：page config + 主题 + 骨架 + Tab 路由
core/                  # 基础设施：envutil（.env）、paths（PROJECT_ROOT 锚点）
models/                # Model 层：llm/idste/prompts/websearch/image_*/qa/xlsx_*/pptx_builder
controllers/           # Controller 层：agent（流程编排）+ excel_controller/ppt_controller
views/                 # View 层：ui_theme（视觉）+ layout/excel_view/ppt_view（渲染）
scripts/               # 一次性探针脚本（login_mcp/discover/parse_discover/scan_tables/probe_llm）
render.js              # Node 渲染（与 theme.json/schema 同目录绑定）
theme.json / slide_spec_schema.json  # 运行时资源（留根，render.js 用 __dirname 定位）
```

资源文件（`.env` / `theme.json` / `slide_spec_schema.json` / `render.js`）统一由 `core.paths.resource()` 经 `PROJECT_ROOT` 定位，模块怎么移动都不影响查找。

## 产物

每次运行在 `output/` 目录生成：

| 流程 | 文件 | 用途 |
|---|---|---|
| Tab 1 | `*_<uuid>_data.xlsx` | 已填模板的 Excel 报告（37 张 sheet 按用户意图选填） |
| Tab 2 | `*_slides.pptx` | 8-15 页 PPT 演示（pptxgenjs 渲染） |
| Tab 2 可选 | `qa/thumbs_*.jpg` | 视觉 QA 缩略图（启用后） |

## 依赖

- **Python 3.10+**：`requests` / `streamlit` / `openpyxl` / `python-dotenv` / `duckduckgo-search` / `cryptography`（探针脚本用）
- **Node 18+**：`pptxgenjs`
- **运行时配置**：`theme.json`（调色板 + 布局尺寸）、`slide_spec_schema.json`（8 layout 单一真相源）

完整列表与版本约束见 `requirements.txt` 和 `package.json`。

## 安装

```bash
# 1. Python 依赖
pip install -r requirements.txt

# 2. Node 依赖
npm install

# 3. 凭据
cp .env.example .env
# 编辑 .env，填入 IDSTE_API_KEY / LLM_API_KEY / QWEN_IMAGE_TOKEN 等
# 模板路径：TEMPLATE_XLSX_PATH 指向 .xlsx 模板
```

## 启动

```bash
# 方式 1：Streamlit Web 界面（推荐给同事用）
streamlit run app.py
# 浏览器打开 http://localhost:8501

# 方式 2：命令行单次跑 Excel 流程
python -m controllers.agent "分析2025年公司SP战略规划完成度"

# 开发模式（ui_theme.py 热重载）
DEV=true streamlit run app.py
```

## 配置文件

| 文件 | 作用 |
|---|---|
| `.env` | 凭据 + 模板路径 + 各服务开关（gitignored，不入库） |
| `theme.json` | 调色板（Midnight Executive：深蓝+冰蓝）、字体、页面布局尺寸、9 宫格 image zone |
| `slide_spec_schema.json` | 8 种 slide layout 单一真相源（`prompts.py` / `render.js` 共享） |
| `.streamlit/config.toml` | Streamlit 原生控件颜色（与 theme.json 概念重复，作为兜底） |

## 阶段完成度

- [x] 阶段 1：环境 + 凭据脱敏
- [x] 阶段 2：MCP REST 工具 + 表分类
- [x] 阶段 3：报告 + slide-spec 端到端
- [x] 阶段 4：PPT 渲染（pptxgenjs）
- [x] 阶段 5：Streamlit Web 界面
- [x] 阶段 6：提示词与样式打磨
- [x] v2 重构：xlsx 流程（替代 v1 的 .md 报告）、37 张 sheet schema 动态生成 prompt
- [x] v3 增量：Qwen-Image 图片生成（cover/section/conclusion 必出）+ DuckDuckGo 联网搜索 + 工具调用统计
- [ ] 延后：iDSTE 服务账号替换、部署到公司服务器、PPT 视觉 QA 全量

详见 `STATUS.md`。

## 部署到公司服务器（待办）

1. 改用 iDSTE 服务账号（替换个人账号）
2. Streamlit：`streamlit run app.py --server.port 8501 --server.address 0.0.0.0`
3. Nginx 反代 + 内网域名
4. `.env` 改用 secrets 管理（不放文件）
