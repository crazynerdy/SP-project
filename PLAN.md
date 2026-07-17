# SP 分析报告 Agent — 实现计划

> ⚠️ **本文已过时**:这是早期设计稿(v1: Markdown 报告 + python-pptx),部分已被 v2 实现取代(xlsx + pptxgenjs/Node + 图片生成 + 联网搜索)。**以代码和 `STATUS.md` 为准**,最新总览见 `README.md`。

## 1. 目标

做一个**独立 Python Web Agent**：同事在网页上用自然语言提需求（如"分析 2025 年公司 SP 战略规划完成度"），Agent 自动：

1. 调用 iDSTE MCP Server 的 **SP 管理**工具拉数据（REST API v2）；
2. 用公司内网大模型（Qwen3.5_122B_A10B）+ 提示词生成**高质量分析报告**（Markdown）；
3. 用 `python-pptx` + 模板把报告自动生成**高质量 PPT**；
4. 网页上展示报告、提供报告(.md)和 PPT(.pptx) 下载。

面向不会用 Claude Code 的同事，一键出结果。

---

## 2. 架构总览

```
[Streamlit 网页 app.py]
        │  自然语言需求
        ▼
[agent.py 核心] ── 工具调用循环 ──► [llm.py] ──► Qwen3.5 (OpenAI 兼容 API)
        │                              ▲
        │  调 SP 工具(REST)             │ 注入分析/幻灯片 prompt (prompts.py)
        ▼                              │
[idste.py] ──HTTP──► iDSTE /mcp/api/v2/{tool}  (Key 从 .env 读)
        │
        ▼
   SP 原始数据 ──► [llm 分析] ──► 报告.md
                                   │
                                   ▼
                        [prompts: 幻灯片规格] ──► slide-spec JSON
                                   │
                                   ▼
                        [pptx_builder.py] ──► 报告.pptx (模板+设计规范)
```

凭据全部走现有 `envutil.py` / `.env` 体系（iDSTE + LLM 统一管理，不进代码）。

---

## 3. 技术栈与依赖

| 用途 | 包 | 说明 |
|------|----|----|
| Web UI | `streamlit` | 一个文件出网页 |
| LLM 调用 | `openai` | OpenAI 兼容，base_url 指向内网 |
| iDSTE REST | `requests` | 已装 |
| PPT 生成 | `python-pptx` | 模板填充 + 图表 |
| 图表(可选) | `matplotlib` | 复杂图表先出图再插入 |
| .env | 现有 `envutil.py` | 无需 python-dotenv |

安装：`pip install streamlit openai python-pptx matplotlib`

---

## 4. 文件结构

```
D:\memory\
├─ envutil.py              # 已有，扩展 LLM 配置项
├─ .env                    # 已有，追加 LLM_BASE_URL / LLM_MODEL / LLM_API_KEY
├─ .env.example            # 追加 LLM 占位
├─ idste.py                # 新：SP 工具 REST 封装
├─ llm.py                  # 新：LLM 客户端 + 工具调用循环
├─ agent.py                # 新：Agent 核心（需求→取数→报告→PPT）
├─ prompts.py              # 新：分析报告 prompt + 幻灯片规格 prompt
├─ pptx_builder.py         # 新：slide-spec → .pptx
├─ templates/
│   └─ sp_template.pptx    # 新：设计好的 PPT 母版模板
├─ app.py                  # 新：Streamlit 网页
└─ output/                 # 生成的报告/PPT 存放
```

---

## 5. 核心模块设计

### 5.1 `.env` 扩展（追加）
```
LLM_BASE_URL=http://221.202.84.100:7092/v1
LLM_MODEL=Qwen3.5_122B_A10B
LLM_API_KEY=sk-xxxxxxxx
```
（iDSTE 的三项已有，保持不变。）

### 5.2 `idste.py` — SP 工具 REST 封装
封装 6 个**只读** SP 工具（写工具 `update_sp_data` 不用于分析，不封装）：
- `sp_team_info()` → GET get_sp_team_info
- `sp_activity_list()` → GET get_sp_activity_list（需 101 角色）
- `sp_plan(year)` → GET get_sp_plan
- `sp_dimension()` → GET get_sp_dimension（返回 dim_info 列表）
- `sp_data_menu(dim_info)` → GET get_sp_data_menu（返回 table_key 列表）
- `sp_data(dim_info, table_key, year)` → GET get_sp_data（返回 rendering_guide + data）

每个函数：读 `.env` 的 `IDSTE_BASE`/`IDSTE_API_KEY`，`requests.get(f"{BASE}/mcp/api/v2/{tool}", headers={"X-MCP-API-Key": KEY}, params=...)`，解析 `{"success":true,"data":...}` 返回 `data`。统一异常处理（401/404/403）。

### 5.3 `llm.py` — LLM 客户端 + 工具调用循环
- 用 `openai` 包，`base_url=require("LLM_BASE_URL")`，`api_key=require("LLM_API_KEY")`，`model=require("LLM_MODEL")`。
- **工具调用**：先按 Qwen 支持 OpenAI 风格 `tools`/`tool_calls` 实现；首次调用若模型不返回 tool_calls，自动切"prompt 模式"（系统提示约束模型输出 `<<TOOL_CALL>>{json}`，代码解析执行）。两种模式对上层接口一致。
- 暴露 `chat(messages, tools=None)` 和 `run_agent_loop(system_prompt, user_msg, tool_map, max_turns)` 两个核心方法。`run_agent_loop` 负责循环：LLM 出工具调用 → 执行 `tool_map` 里对应函数 → 把结果塞回 messages → 直到 LLM 给出最终文本。

### 5.4 `prompts.py` — 两段关键 prompt（"高质量"的核心）
**分析报告 prompt**（system）：定义报告框架与质量标准——
- 角色：资深战略规划分析顾问，精通 DSTE/BLM 框架；
- 输出结构：① 执行摘要 ② 规划全景（团队/维度/计划概览）③ 数据详析（按表逐项，用 rendering_guide 指导呈现）④ 关键发现（完成度、质量、差距、风险）⑤ 建议与下一步；
- 要求：数据支撑（引用具体数值）、结论先行、问题具体可执行、中文、Markdown；
- 工具使用规则：先 `sp_dimension`→`sp_data_menu`→`sp_data` 的依赖链；按需补 `sp_team_info`/`sp_plan`；不臆造数据。

**幻灯片规格 prompt**：把报告转成 slide-spec JSON——
```
{ "slides": [ {"layout": "title|section|bullets|two_col|table|chart|big_stat|conclusion",
               "title": "...", "bullets": [...], "table": {...}, "chart_type": "bar|pie", "chart_data": {...} } ] }
```
约束：8-15 页；每页一个布局；数据页用 table/chart；结论页用 big_stat；不产出纯文字页。

### 5.5 `agent.py` — Agent 核心
1. 接收 NL 需求；
2. `run_agent_loop` 用分析 prompt + 6 个 SP 工具，循环取数+分析，产出报告 Markdown；
3. 保存 `output/{timestamp}_report.md`；
4. 用幻灯片规格 prompt 把报告转成 slide-spec JSON；
5. 调 `pptx_builder.build(spec)` 生成 `output/{timestamp}_report.pptx`；
6. 返回报告文本 + 两个文件路径给 Streamlit。

### 5.6 `pptx_builder.py` — PPT 生成（模板法 + 设计规范）
- 加载 `templates/sp_template.pptx`，按 slide-spec 逐页填内容；
- 内置设计规范（移植自 pptx skill）：固定企业配色（主色 60-70% + 1 辅色 + 1 强调色）、字体搭配（标题/正文）、6-8 种版式、每页必有视觉元素（图表/表格/大数字/色块）、0.5" 边距、标题 36pt+/正文 14-16pt、不加标题下划线；
- 用 `python-pptx` 原生图表（柱/饼）画 SP 完成度/差距；表格用 `add_table`；
- **保守版式**规避溢出（因 Qwen 纯文本无视觉 QA）：固定文本框尺寸、不自动缩放、长文本截断并提示。

### 5.7 `app.py` — Streamlit 网页
- 标题 + 需求输入框 + "生成"按钮；
- 生成中显示步骤进度（取数中→分析中→生成 PPT 中）；
- 完成后：Markdown 渲染报告 + 两个下载按钮（.md / .pptx）；
- 侧边栏放示例需求（一键填入）。

---

## 6. 端到端流程（一次调用）

同事输入"分析 2025 年公司 SP 战略规划完成度" →
1. Agent 解析意图（year=2025，scope=公司维度 c，分析角度=完成度）；
2. `sp_dimension()` → 拿到 `dim_info='c'`；
3. `sp_data_menu('c')` → 拿到若干 `table_key`；
4. `sp_data('c', table_key, '2025')` 逐表取数（含 rendering_guide）；
5. （可选）`sp_team_info()`、`sp_plan('2025')` 补全景；
6. LLM 按分析 prompt 综合数据 → 报告.md；
7. LLM 按幻灯片 prompt → slide-spec JSON；
8. pptx_builder → 报告.pptx；
9. 网页展示 + 下载。

---

## 7. 关键设计决策与兜底

| 决策 | 选择 | 原因/兜底 |
|------|------|-----------|
| 形态 | 独立 Python + Streamlit | 同事一键用，不依赖 Claude Code |
| 数据接入 | REST helper | 已验证可行、复用 .env、零兼容风险 |
| LLM 工具调用 | 原生 function-calling，退回 prompt 模式 | Qwen 多半支持；不支持也能跑 |
| PPT 生成 | python-pptx 模板法 | 质量稳、可控；纯文本模型无视觉 QA，靠保守版式兜底 |
| 视觉 QA | 暂不做 | Qwen 非 VL；如后续有多模态模型再加（渲染成图+多模态挑错） |
| 凭据 | 全进 .env，envutil 统一读 | 与已做好的脱敏方案一致 |

---

## 8. 实施阶段（按顺序，每阶段可独立验证）

1. **环境与取数**：扩展 .env；写 `idste.py`；跑通一次 `sp_dimension→menu→data` 拿到真实表数据。（这步会顺便摸清 SP 实际有哪些表）
2. **LLM 客户端**：写 `llm.py`；验证 Qwen 连通 + 探测 function-calling 是否可用。
3. **Agent 核心 + 分析 prompt**：写 `agent.py`、`prompts.py` 的报告 prompt；端到端跑出一份报告.md 并人工评估质量。
4. **PPT 生成**：做 `templates/sp_template.pptx` 模板；写 `pptx_builder.py`；从报告生成 PPT 并检查版式。
5. **Streamlit 网页**：写 `app.py`；串通"输入→报告→PPT→下载"。
6. **打磨**：分析 prompt 调优、设计规范落实、异常处理、示例需求。

---

## 9. 风险与待验证项

- **iDSTE 权限**：当前 API Key 关联杨金威个人账号。若非 101 角色，SP 数据范围受限，报告覆盖不全。→ 全量报告建议换 101 权限的**服务账号**（与之前脱敏讨论一致）。
- **SP 表结构未知**：第一阶段的真实取数会摸清 `table_key` 和每张表的字段，prompt 据此微调。
- **Qwen function-calling**：第 2 阶段实测；不支持则走 prompt 模式（已设计兜底，不影响功能）。
- **数据量**：某张 SP 表可能很大；若超 LLM 上下文，agent.py 里加截断/分批/摘要。
- **PPT 模板**：需一次性设计好 `sp_template.pptx`（可在 PowerPoint 里做，或用 python-pptx 生成基础版后再美化）。这是 PPT 质量的关键投入。
- **服务器部署**：Streamlit 跑 `streamlit run app.py`；确保服务器能访问 iDSTE(123.188.239.53:9090) 和 LLM(221.202.84.100:7092) 两个内网地址。
