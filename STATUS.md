# SP Analysis Report Agent — 项目状态快照

> 最后更新：2026-07-13（v2 重构）
> 用途：上下文压缩后恢复项目状态；记录已确认/未确认事项、待办、关键决策。

---

## 一、目标（v2）

公司内部工具：让同事通过 web 输入自然语言需求 → **意图识别** → 自动拉取 iDSTE SP 数据 → 按【中海润】战略规划智能体输出格式模板（37 张 sheet）填出 **Excel 报告**；用户填好后再用同一 agent 把 Excel 数据 + 自然语言 → **PPT 演示**。

## 二、架构（v2）

```
Streamlit (app.py)
   ├─ Tab 1: 生成 Excel
   │    自然语言 → intent_recognize() → 选 sheet
   │           → generate_xlsx_data()  (LLM + iDSTE 工具) → xlsx-ready JSON
   │           → xlsx_exporter.fill_template() → output/<ts>_<intent>_data.xlsx
   │
   └─ Tab 2: 生成 PPT (基于 Excel)
        选历史/上传 xlsx + 自然语言
           → xlsx_reader.read_template() → xlsx JSON
           → generate_pptx_from_xlsx() (LLM) → slide-spec JSON
           → pptx_builder → node render.js → output/<ts>_<intent>_slides.pptx
```

## 三、文件结构

| 文件 | 状态 | 用途 |
|---|---|---|
| `.env` | ✅ | 凭据 + `TEMPLATE_XLSX_PATH` 模板路径 |
| `.env.example` | ✅ | 模板 |
| `.gitignore` | ✅ | 忽略 .env / output / node_modules |
| `envutil.py` | ✅ | .env 加载器（`env()` / `require()`） |
| `idste.py` | ✅ | 5 个只读 SP 工具 + `build_tools_schema()` + `TOOL_MAP` |
| `llm.py` | ✅ | OpenAI 客户端 + 工具调用循环 + deprecation 垫片 |
| `prompts.py` | ✅ | 3 段 prompt（intent / xlsx_data / slide_spec_from_xlsx），从 xlsx 模板动态生成 |
| `agent.py` | ✅ | 4 主函数（intent / generate_xlsx_data / generate_pptx_from_xlsx / run_excel_flow）|
| `xlsx_reader.py` | ✅ | 提取 schema + 读已填 xlsx |
| `xlsx_exporter.py` | ✅ | 填模板 |
| `pptx_builder.py` | ✅ | Python → Node 桥接 |
| `render.js` | ✅ | pptxgenjs 渲染（8 layout），加载 theme.json + slide_spec_schema.json |
| `theme.json` | ✅ | 调色板 + 字体 + 布局尺寸 |
| `slide_spec_schema.json` | ✅ | 8 layout 单一真相源 |
| `package.json` | ✅ | pptxgenjs 依赖 |
| `requirements.txt` | ✅ | requests, streamlit, openpyxl, python-dotenv |
| `app.py` | ✅ | Streamlit 双 Tab UI |
| `STATUS.md` | ✅ | 本文件 |

## 四、关键事实（必须记住）

### iDSTE / SP 数据
- **30 张表，22 张 type1（可分析），8 张 type2（redirect）**
- type1 返回 `{sheets: [{sheet_name, headers, rows}]}`，取数按需求挑 5-6 张即可
- type2 redirect 例：`战略KPI情况表`、`市场格局Mekko图`（含 `view_url`）
- 工具依赖链：`sp_dimension() → sp_data_menu(dim) → sp_data(dim, table_key, year)`
- **当前账号 `杨金威` 权限非 101 角色**，只能看 3 个维度（公司 c + 部分 BUPL），公司部署前**建议改用服务账号**（延后）

### LLM (Qwen3.5_122B_A10B)
- Base：`http://10.8.0.54:6003/v1`（**内网 VPN，不是 221.202.84.100:7092**）
- Key：见 .env 的 LLM_API_KEY（不在此明文）
- **支持 OpenAI 风格 native function-calling**（已实测）
- **是 reasoning 模型**：`message.reasoning` 字段含思考链，消耗大量 completion token（极简问题 ~440 tokens）。小 max_tokens 下 content 易被截断为空（`finish_reason=length`）。所有"最终回答"型 chat 调用走 `chat_with_fallback`（小 max_tokens 先试，空/length 则大 max_tokens 重试）；`run_agent_loop` 用 `final_max_tokens` 兜底。
- **thinking 开关**：`chat`/`chat_with_fallback`/`run_agent_loop` 均支持 `enable_thinking`（via `chat_template_kwargs`，**必须走此嵌套字段**，顶层 `enable_thinking` 实测无效）。`run_agent_loop` 分 `enable_thinking`（工具轮）与 `final_enable_thinking`（最终轮）。关思考省 reasoning token + 大幅提速（工具轮 25s->0.6s），按任务难度配置（见下）。
- **多模态未确认**（保守路径，不依赖）
- **VPN 偶尔断**：LLM 不可达时回 ConnectTimeout 120s
- **max_tokens + thinking 配置**（reasoning 占大头需留余量；thinking 开关按任务难度）：
  - intent 识别：`max_tokens=2000`/fallback `4096`，`enable_thinking=False`（简单分类，关思考）
  - xlsx data：`run_agent_loop(max_tokens=2000, final_max_tokens=12288, enable_thinking=False, final_enable_thinking=True)`（工具轮关思考+max_tokens=2000 够生成 tool_calls 含参数变长余量；最终轮开 thinking 保质量；探测最终轮 content 若超长被截断则丢弃，反正开 thinking 重试）
  - slide-spec：`max_tokens=12000`/fallback `16000`，`enable_thinking=True`（设计需推理）
  - 实测：Excel 端到端 170s->约 40s（max_tokens=512 时实测 38.5s；调 2000 更稳但探测稍慢）

### xlsx 模板
- 路径：`.env` 里的 `TEMPLATE_XLSX_PATH`（默认 `D:\下载\【中海润】战略规划智能体输出格式.xlsx`）
- 37 张 sheet（DSTE 4 阶段 + BLM 6 模块）：
  - **D 拆解**：1.1 业绩差距 / 1.2 机会差距
  - **D 市场洞察**：2.1-2.13 (PESTEL/行业/容量/客户/业务划分/对手/雷达/自身/五看/SWOT/TOPN/MEKKO/BCG)
  - **D 战略意图**：3.1 使命愿景 / 3.2 战略地图 / 3.3 KPI
  - **S 创新焦点**：4.1 H123 / 4.2 创新重点 / 4.3 战略专题 / 4.4 新兴机会
  - **S 业务设计**：5.1 竞争战略 / 5.2 中央平台 / 5.3 业务设计 / 5.4 主要风险
  - **T 关键任务**：6.1 战略举措 / 6.2 年度目标 / 6.3 重点项目
  - **E 正式组织**：7.1 组织架构 / 7.2 流程变革
  - **E 人才**：8.1 人才盘点 / 8.2 人才规划
  - **E 氛围文化**：9.1 企业文化 / 9.2 其他资源
  - **E 财务表现**：10.1 财务预测
- 每张 sheet 格式：Row1 标题 / Row2 说明 / Row3 列头 / Row4+ 数据
- 部分表预填样例（3.1 使命愿景：极弱磁信号智能感知探索者 / 6.1 战略举措：三大业务板块市场渗透计划 / 3.3 KPI：智能检测签约31亿元）

### Slide-spec 8 种 layout（来自 slide_spec_schema.json）
`title` / `section` / `bullets` / `two_col` / `table` / `chart` / `big_stat` / `conclusion`
**硬规则**：8-15 页，首页 title，末页 conclusion，section 间隔，纯 bullets 不得连续超 2 页

### 关键设计原则
- **3 段 prompt 全部从 .env 的 `TEMPLATE_XLSX_PATH` 动态生成**：模板变 → prompt 自动跟上
- **DI 注入**：`generate_xlsx_data(llm_client=None, tool_map=None, prompts_module=None, ...)` 方便 A/B 测试 / 多模型 / per-user 凭据
- **`build_tools_schema` 移到 `idste.py`**（schema 描述的是 iDSTE 工具，跟实现放一起更合理；`llm.build_sp_tools_schema` 留 deprecation 垫片）
- **render.js 双道校验**：未知 layout 先查 schema 再查 HANDLERS，warn 双重提示

## 五、双流程入口参数

| 流程 | 函数 | 输入 | 输出 |
|---|---|---|---|
| 入口 | `agent.intent_recognize(user_input)` | 自然语言 | `{flow, year, dim_info, sheets_to_fill, intent_label, reasoning}` |
| Excel | `agent.run_excel_flow(user_input)` | 自然语言 | `(intent, xlsx_path)` |
| Excel 细 | `agent.generate_xlsx_data(user_input, intent=None)` | 自然语言 + intent | `(intent, xlsx_data_dict)` |
| PPT | `agent.generate_pptx_from_xlsx(user_input, xlsx_path)` | 自然语言 + xlsx | `{xlsx_data, slide_spec, pptx_path}` |

## 六、已验证 vs 未验证

| 模块 | 验证方式 | 结果 |
|---|---|---|
| `envutil.py` | `env()` / `require()` 调通 | ✅ |
| `idste.py` | 5 工具 schema + 之前端到端跑通过 | ✅ |
| `llm.py` | function-calling 之前跑通过 | ✅ |
| `xlsx_reader.py` | `python xlsx_reader.py` 36 张 schema 正确 | ✅ |
| `xlsx_exporter.py` | 测试填 1 张表 → reader 读回一致 | ✅ |
| `prompts.py` | 3 段 prompt 动态生成长度合理（intent 1442 / data 4132 / slide 1996 字）| ✅ |
| `agent.py` | 4 函数 DI 签名 | ✅ |
| `app.py` | 语法 OK | ✅ |
| `render.js` | 之前已能跑（13 slides 236KB）| ✅ |
| `pptx_builder.py` | 之前已能跑 | ✅ |
| **端到端（LLM 调用）** | 完整 intent → 取数 → 填表 → 读表 → slide → pptx | ✅ **跑通**（2026-07-14 VPN 通后跑通，修 5 个 bug，见 v3 验证小节）|

## 七、未决 / 风险

| 项 | 状态 | 应对 |
|---|---|---|
| LLM 持续不可达 | 当前现象 | 等 VPN 通后跑端到端 |
| iDSTE 弱密码 `Aa123456` | 已知 | 内部自用可接受；部署前换服务账号 |
| LLM 选 sheet 是否准 | 待验证 | 看实际 xlsx 输出 sheet 名是否符合预期 |
| 模板里预填的样例（3.1/6.1 等）会被覆盖 | 设计行为 | 用户可手动恢复（如果需要保留，在 agent 里加 merge 逻辑）|
| xlsx_exporter 用 `delete_rows` 删模板行 | 性能 | 模板数据少，OK；大数据会慢 |
| 模板路径硬编码 D:\下载 | .env 改了就行 | 多用户部署要换 |

## 八、Phase 完成度

- [x] 阶段 1：环境 + 凭据脱敏
- [x] 阶段 2：MCP REST 工具 + 表分类
- [x] 阶段 3：报告 + slide-spec 端到端（**v1 已完成，v2 已删除**）
- [x] 阶段 4：PPT 渲染（pptxgenjs + theme/schema）
- [x] 阶段 5：Streamlit Web 界面（**v2 双 Tab**）
- [x] 阶段 6：提示词与样式打磨（v1 完成的 3 项重构：theme/schema/DI）
- [x] **v2 新增**：xlsx_reader / xlsx_exporter / intent 识别 / 模板动态生成
- [ ] **延后**：iDSTE 服务账号、部署到公司服务器

## 九、待办（v2 之后）

| # | 任务 | 优先级 |
|---|---|---|
| 1 | VPN 通了后跑一次完整端到端，看 xlsx 内容是否符合预期 | P0 |
| 2 | LLM 选 sheet 准的话，再调 prompt 边界（如"只做 X"会不会误填） | P1 |
| 3 | LLM 选 sheet 不准的话：把 LLM 选错的样例加到 prompt 的"反例"段 | P1 |
| 4 | 加 `LANG=zh/en` 切换（i18n） | P3 |
| 5 | 按 req hash 缓存报告 + xlsx | P2 |
| 6 | iDSTE 服务账号 | P1（部署前必做）|

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
- `render.js`（applyImageZone 函数 — **BLOCKED 等模板**）
- `app.py`（图片生成/QA checkbox + tool_call_stats UI）
- `.env` / `.env.example`（QWEN_IMAGE_* + WEBSEARCH_* 共 9 行）
- `requirements.txt`（加 duckduckgo-search）

### 验证状态
- [x] L1 单元：所有新模块 __main__ 段可 import（受网络/VPN 限制的标记为"代码就绪"）
- [x] L2 集成：LLM 连通 + function-calling 可用（2026-07-14）
- [x] L3 端到端：Excel + PPT 流程跑通，修 5 个 bug（2026-07-14）
- [ ] L4 视觉 QA：等 PPT 模板（Task 10 BLOCKED）

### L2/L3 端到端验证（2026-07-14，VPN 通）

**验证结果**：Excel + PPT 双流程跑通。LLM 选 sheet 准（"业绩差距+主要风险" -> `1.1 业绩差距分析` + `5.4 主要风险分析`），数据真实有 sp_data 支撑（订货 3000 万/达成率 5%/责任人宋君胜等），`tool_call_stats` 正确累计 `{sp_dimension:1, sp_data_menu:1, sp_data:2}`，PPT 9 页硬规则满足（首页 title/末页 conclusion/8-15 页），Qwen-Image 9 张图生成成功（b64_json，1.2-1.7 MB/张）。

**发现并修复 5 个 bug**：
1. **reasoning 模型 max_tokens 截断**：Qwen3.5_A10B 思考链吃光小 max_tokens，content 为空（finish=length），`run_agent_loop` 误以为"空回答"返回。修：`llm.chat_with_fallback`（小→大重试）+ `run_agent_loop(final_max_tokens)` + intent/pptx 调用接入。
2. **JSON 未转义引号**：LLM 在字符串值内用裸 ASCII 双引号（如 `通过"生产一代"策略`）致 JSON 截断。修：`agent._repair_unescaped_quotes` 兜底（扫描字符串内裸引号转义）+ XLSX/SLIDE prompt 加硬规则（值内用中文引号）。
3. **xlsx sheet 名尾空格**：模板 `5.4 主要风险分析 ` 带尾空格，LLM 输出无尾空格，`fill_template` 匹配失败只填 1 张。修：建 strip→原名映射容错。
4. **Qwen-Image 返回 b64_json 非 url**：`image_client` 只认 url，崩在 `requests.get(None)`。修：优先 b64_json（base64 解码），url 次之。
5. **KEY_LAYOUTS 用 cover 不匹配 title**：schema 8 layout 无 cover，首页 title 不注入图。修：`KEY_LAYOUTS = {title, section, conclusion}` + prompts 文档对齐。

**仍待验证**：
- web_search 实际联网（DuckDuckGo 在公司内网可能被屏蔽；本次 LLM 未调 web_search，sp_data 已够）。代码就绪。
- 图片贴进 pptx：等 Task 9（render.js applyImageZone，BLOCKED 等模板）。
- L4 视觉 QA：等 Task 10（BLOCKED 等模板）。

## v4 增量（2026-07-15）：MVC 分层重构

### 动机
原 20+ 个 `.py` 平铺根目录，`app.py` 361 行身兼 View+Controller+直调 Model 三职。按 MVC 变体（分层架构）归层并拆 `app.py`，**业务逻辑零改动**。

### 结构变更
- `core/`（`envutil` + `paths.PROJECT_ROOT` 锚点）、`models/`（10 个服务/数据模块）、`controllers/`（`agent` + `excel_controller` + `ppt_controller`）、`views/`（`ui_theme` + `layout` + `excel_view` + `ppt_view`）、`scripts/`（5 个探针）
- 资源文件（`.env` / `theme.json` / `slide_spec_schema.json` / `render.js`）留根，统一由 `core.paths.resource()` 经 `PROJECT_ROOT` 定位
- render.js 四件套（render.js + theme.json + schema + pptx_builder）的 `__dirname`/`__file__` 绑定保持不变，`render.js` 一行未改

### app.py 拆分
- 361 行 -> ~85 行瘦入口（page config + 主题 + sidebar/hero/overview + session_state 初始化 + Tab 路由）
- View 只渲染不调 agent；Controller 编排 + 管 session_state；Model 不碰 streamlit
- session_state 由 controller 持有，view 只读

### 验证
- [x] 各层 import 冒烟（models/controllers/views/core 全量）
- [x] `streamlit run app.py` 启动成功、无 traceback
- [x] `controllers.agent` 5 个导出函数可用
- [ ] 实际 Excel/PPT 端到端（依赖 VPN/LLM，环境就绪后跑）

### 命令行入口变更
`python agent.py "..."` -> `python -m controllers.agent "..."`


## v5 增量（2026-07-15）：SP 2026 智能体自动填写

### 动机
驱动文件（`D:\Desktop\gg\战略规划SP变更需求-*.xlsx`）的 E 列标了"智能体自动搜索填写" / "智能体自动分析总结" 的行，表示该 sheet 需要智能体基于 2025 实际数据生成 2026 内容。本次先做 2.2 行业趋势分析表试点。

### 新增能力
- 解析驱动文件 -> 识别"智能体自动..."行（24 行：4 搜索填写 + 20 分析总结，离线纯函数单测覆盖）
- iDSTE MCP 拉 2025 行业趋势（few-shot，7693 字）-> LLM (Qwen3.5) 生成 2026 6 维度内容
- 覆盖写入主模板 B4-B9 -> 输出 `output/<ts>_sp_2026_<uuid>_data.xlsx`
- Streamlit Tab 1 加 "智能体自动填写" 子区块（路径输入 + 年份 + sheet 过滤 + 下载）

### 新增文件
- `models/sp_change_2026.py` - 业务核心：parse_requirement_xlsx + resolve_table_key（纯函数，离线可单测；含 CJK 字符集重叠打分 fallback）
- `controllers/sp_change_2026_controller.py` - 端到端编排（DI 全开；enable_web_search 开关；--no-web CLI）
- `views/sp_change_2026_view.py` - Streamlit 子区块 UI

### 改动文件
- `models/idste.py` - `_find_table_keys` 加 `table_title` 字段提取（MCP 实际返回 table_title 而非 name）
- `models/xlsx_exporter.py` - 加 `fill_cells()`（不动原 `fill_template`，dict-based 点对点写）
- `models/prompts.py` - 加 `build_sp_2026_data_prompt()`（不硬编码 6 维度，从 row_labels 现读）
- `views/excel_view.py` - 加 `render_excel_tab_with_sp2026()` 包装
- `app.py` - Tab 1 改走新入口（保留旧 import 以备回滚）
- `.env.example` - 加 `GG_XLSX_PATH` 注释项

### 验证状态
- [x] L1 单元：parse / resolve / fill_cells 离线单测（Task 1/2/3 __main__ 段）
- [x] L2 集成：MCP 拉 2025 + LLM 返 6 维 JSON + xlsx 写盘
- [x] L3 端到端：`python -m controllers.sp_change_2026_controller "2.2 行业趋势分析表" --no-web` 跑通，6 cells 各 164-183 字，含"2026 预测"+ 具体数据引用
- [x] 回归：现有 fill_template + 3 个 prompt builder 仍工作
- [ ] web_search 端到端：当前环境网络封锁（DuckDuckGo/bing ConnectError），需联网环境验证

### 已知约束
- web_search 在公司内网被屏蔽；pilot 用 `--no-web` 跑通，2026 内容基于 2025 few-shot + LLM 知识生成（无联网补充）
- `resolve_table_key` 对 MCP 菜单中不存在的 sheet（如 2.4 客户购买行为）会抛 ValueError -- 这是正确行为，未来需在驱动文件层标注或补 MCP 数据
- `models/prompts.py` 378 行、`controllers/sp_change_2026_controller.py` 456 行，均超 300 行 guideline（拆分到 `prompts/` 包 / `controllers/sp_2026_helpers.py` 是未来重构点）

### 未来扩展点
- 全 24 张「智能体自动...」sheet 自动填写（沿用现有架构，单独 spec）
- 多年型 sheet (6.1/6.2) Y1/Y2/Y3 重映射
- `.env` 加 `SP_2026_TABLE_KEY_MAP` 显式映射（替代关键字+打分匹配）
- 驱动文件自动检测常驻
- web_search 走公司代理或换搜索源
