# SP 战略规划 — 智能体自动填写（2026）设计文档

> 日期：2026-07-15
> 状态：✅ 设计完成，待用户 review
> 项目：SP 战略规划智能体（D:\memory）

---

## 一、目标

为【中海润】战略规划智能体新增一条**驱动文件（driving file）驱动的自动填写流程**：让用户上传/指定 `战略规划SP变更需求-X.X 版.xlsx` 这类需求追踪表，智能体自动识别 E 列标为「智能体自动搜索填写 / 智能体自动分析总结」的行，从 iDSTE MCP 拉对应 sheet 的 2025 年实际数据作为 few-shot，再用 LLM + 联网搜索生成 **2026 年**内容，覆盖写回主模板（37-sheet 标准模板）的指定单元格，最终输出 1 份 `<ts>_sp_2026_data.xlsx`。

**试点范围**：本次仅做 **2.2 行业趋势分析表** 一张，跑通端到端；架构要支持未来扩展到全部 22 张「智能体自动...」行（不改 prompt 主体）。

**业务诉求**（来自驱动文件 A1 单元格原文）：
> 1. 期望智能体学习 iDSTE 里面 SP 管理（基于 BLM&MM 的 SP 七步法）的全部内容
> 2. 只针对做战略规划...
> 3. 智能化生成战略规划报告

---

## 二、范围

**包括**：
- 解析驱动文件 gg Excel（`D:\Desktop\gg\战略规划SP变更需求-6.5 版（产品需求沟通确认 2.0）.xlsx`）
- 过滤 E ∈ `{"智能体自动搜索填写", "智能体自动分析总结"}` 的行
- iDSTE MCP 拉 2025 行业趋势数据（few-shot）
- LLM (Qwen3.5_122B_A10B) + DuckDuckGo 联网搜索生成 2026 内容
- 覆盖写入主模板对应 sheet 的指定单元格（B4-B9 试点）
- 输出 `D:\memory\output\<ts>_sp_2026_data.xlsx`（主模板副本，不动原件）
- Streamlit Tab 1 加 "智能体自动填写模式" 表单入口
- 工具调用统计（沿用现有 tool_call_stats 机制）

**不包括**：
- 不动 iDSTE MCP 客户端（`models/idste.py`）
- 不动联网搜索（`models/websearch.py`）
- 不动 LLM 客户端（`models/llm.py`）
- 不动 render.js / theme.json / slide_spec_schema.json
- 不动现有 Tab 1「自然语言→intent」流程 / Tab 2 PPT 流程
- 不重写 37-sheet 主模板
- 不做 i18n
- 不动驱动文件 gg Excel（只读）

---

## 三、架构

```
┌──────────────────────────────────────────────────────────────────────┐
│ Streamlit (app.py) — Tab 1 末尾新增 "智能体自动填写模式" 子区块            │
└──────────┬───────────────────────────────────────────────────────────┘
           │ 用户提交: gg_xlsx_path + year=2026 + sheets=["2.2 行业趋势分析表"]
           ▼
┌──────────────────────────────────────────────────────────────────────┐
│ controllers/sp_change_2026_controller.run_sp_change_2026(...)         │
│                                                                       │
│   ┌─ models/sp_change_2026.parse_requirement_xlsx(gg_xlsx)            │
│   │    → 解析 A-H 列 → 过滤 E ∈ {自动搜索, 自动总结} → 6 字段元组     │
│   │                                                                   │
│   ├─ sp_dimension() → 'c' (调 MCP, loop 外只一次)
│   ├─ sp_data_menu('c') → menu (调 MCP, loop 外缓存一次)

│   ├─ for each target (row, template_name, f_process_hint):
│   │   ├─ resolve_table_key(template_name, menu)                        │
│   │   │    → 按"主模板 sheet 名去'表'字后，含目标关键字"匹配第一条     │
│   │   ├─ sp_data('c', table_key, '2025') → baseline_2025 (iDSTE MCP)  │
│   │   ├─ 读主模板对应 sheet 的 A4-A9 (6 维度标签)                       │
│   │   ├─ run_agent_loop(SP_2026_DATA_PROMPT, user_msg,                │
│   │   │                  tool_map={**TOOL_MAP, "web_search": ...})    │
│   │   │    → 2026_cells = {"B4": "...", ..., "B9": "..."}             │
│   │   └─ xlsx_exporter.fill_cells(                                    │
│   │         template_path=TEMPLATE_XLSX_PATH,                         │
│   │         sheet_name="2.2 行业趋势分析",                              │
│   │         cells=2026_cells,                                          │
│   │         mode="overwrite",                                          │
│   │         out_path=D:/memory/output/<ts>_sp_2026_data.xlsx           │
│   │      )    ← 同一 out_xlsx 累计写多张 sheet                          │
│   │                                                                   │
│   └─ return (intent_meta, out_xlsx_path, tool_call_stats)              │
└──────────┬───────────────────────────────────────────────────────────┘
           ▼
       [output/<ts>_sp_2026_data.xlsx]   ← Streamlit 提供下载按钮
```

**复用模块**（一行不动）：
- `models/idste.py` — `sp_dimension / sp_data_menu / sp_data / _find_table_keys`
- `models/websearch.py` — `web_search_tool / TOOL_MAP`
- `models/llm.py` — `chat / chat_with_fallback / run_agent_loop`
- `models/xlsx_reader.py` — 读主模板 A4-A9 维度标签
- `core/envutil.py` / `core/paths.py` — env / 路径

---

## 四、新增/改动文件

### 4.1 新增 3 个文件

| 文件 | 职责 | 估行数 |
|---|---|---|
| `models/sp_change_2026.py` | 业务核心：parse_requirement_xlsx / resolve_table_key / fetch_2025_baseline / generate_2026_content | ~180 |
| `controllers/sp_change_2026_controller.py` | 编排 run_sp_change_2026，session_state 持有 | ~120 |
| `views/sp_change_2026_view.py` | Streamlit Tab 1 子区块 UI | ~80 |

### 4.2 改动 4 个文件

| 文件 | 改动 |
|---|---|
| `models/xlsx_exporter.py` | 加 `fill_cells(template_path, sheet_name, cells: dict, mode="overwrite", out_path=None) -> out_path`（在 `fill_template` 旁加，不动原函数） |
| `models/prompts.py` | 加 `build_sp_2026_data_prompt(template_name, row_labels, baseline_2025, f_process_hint, year) -> str` |
| `views/excel_view.py` | Tab 1 末尾加子区块："智能体自动填写模式" |
| `views/app.py` | 把 sp_change_2026_view 接入 Tab 1（仅拼接，不动其他 Tab） |

### 4.3 配置（`.env` 不改）

无新增 env。如果 `resolve_table_key` 命中 0 条，未来可在 `.env` 加 `SP_2026_TABLE_KEY_MAP=2.2 行业趋势分析表:xxx_key,2.1 宏观环境分析:yyy_key`（本次**不实现**，仅留扩展点；试点单一关键字匹配足够）。

---

## 五、关键数据结构

### 5.1 驱动文件解析结果

```python
@dataclass
class RequirementRow:
    row: int                # 1-indexed
    blm_module: str         # A 列 (e.g., "市场洞察")
    stage_step: str         # B 列 (e.g., "行业趋势分析")
    research_content: str   # C 列
    output_template: str    # D 列 (e.g., "2.2 行业趋势分析表")
    data_source: str        # E 列 (e.g., "智能体自动搜索填写")
    process_hint: str       # F 列 (业务期望过程)
    idste_module: str       # G 列
    note: str               # H 列

def parse_requirement_xlsx(path: str) -> list[RequirementRow]:
    """读 A1-H38，过滤 data_source ∈ {智能体自动搜索填写, 智能体自动分析总结}"""
```

### 5.2 单元格映射结果

```python
# 2.2 试跑
type SheetCells = dict[str, str]   # {"B4": "...", "B5": "...", ..., "B9": "..."}
# 未来扩 6.1/6.2 (Y1/Y2/Y3 多年型) 时: {"D2": "2026 营收目标", "E2": "2027 营收目标", ...}  # 单独 spec
```

### 5.3 单次 run 输出

```python
return {
    "intent_meta": {
        "year": 2026,
        "sheets_filled": ["2.2 行业趋势分析"],
        "rows_filled": 6,
    },
    "output_xlsx_path": "D:/memory/output/20260715_113022_sp_2026_data.xlsx",
    "tool_call_stats": {
        "sp_dimension": 1, "sp_data_menu": 1, "sp_data": 1, "web_search": 3,
    },
}
```

---

## 六、核心 prompt（`SP_2026_DATA_PROMPT`）

由 `models/prompts.py` 的 `build_sp_2026_data_prompt()` 动态拼装：

```
你是【中海润】公司战略规划分析专家。任务：基于 2025 行业趋势实际数据
(few-shot)，分析并预测 2026 行业趋势的 {len(row_labels)} 个维度变化。

## 输出表格信息
- 主模板 sheet 名: {template_name}
- 主模板 A 列 (要看的内容): {row_labels_json}      # 从主模板 A4-A9 现读
- 目标列: B 列 (看到的结果)
- 目标年份: {year}

## 2025 实际数据 (few-shot, 来自 iDSTE MCP sp_data)
{baseline_2025_json}

## 业务期望过程 (来自驱动文件 F 列)
{process_hint}

## 可用工具
- web_search: 搜索 2026 年最新行业事件、政策、技术 (DuckDuckGo)
  工具质量次于 sp_data；本场景主要用来查 2026 新增趋势

## 输出严格 JSON (无 markdown 包装, 无前后言)
{{
  {B4_key}: "...",
  {B5_key}: "...",
  ...
  {B9_key}: "..."
}}

## 硬规则
- 每个 cell 内容 ≥80 字，包含 1-2 个具体数据/事件引用
- 不臆造；引用来自 baseline_2025 或 web_search；2026 预测必须明确标注"预测"
- 结论先行；中文；字符串内不用 ASCII 双引号 (用「」或 "")
- {len(row_labels)} 个 cell 风格、深度对齐
- 仅返 JSON，不要任何解释
```

**设计要点**：
- 6 维度**从主模板现读**（不硬编码"客户偏好/行业界限/..."）
- `row_labels_json` + `B4_key...B9_key` 都动态生成 → 试跑 2.2 后扩到 2.1/2.3/.../10.1 共 22 张时**prompt 主体不动**
- 沿用现有 `run_agent_loop` 配置：`enable_thinking=False, final_enable_thinking=True, max_tokens=2000, final_max_tokens=12288`

---

## 七、错误处理

| 失败点 | 行为 |
|---|---|
| gg_xlsx 路径不存在 / 不是 xlsx | 抛 `FileNotFoundError` 或 `ValueError`；UI 显红 |
| E 列无"智能体自动..."行 | 抛 `ValueError("该驱动文件无自动填写项")` |
| `sp_dimension` / `sp_data_menu` / `sp_data` 超时或鉴权失败 | 抛 `RuntimeError`（沿用 idste.py 既有异常） |
| `resolve_table_key` 命中 0 条 | 抛 `ValueError("主模板 sheet 名 X 未在 MCP 菜单中找到")` |
| `resolve_table_key` 命中 ≥2 条 | 取**第一条含目标关键字**（如"行业"），日志记录所有候选 |
| `sp_data` 返回 `success=false` | 抛原始错误（沿用 idste.py） |
| LLM 返非 JSON / 空 content | 复用 `chat_with_fallback`（小→大 max_tokens 重试） + `_repair_unescaped_quotes` |
| LLM 返 JSON 但键名不匹配预期 (B4-B9) | 容错：补齐空字符串 + `log.warning` |
| `xlsx_exporter.fill_cells` 写入失败 (sheet 不存在等) | 抛 + UI 显红 |
| 同一 out_xlsx 多次 run 累加 | 每次新 run 用**新 `<ts>` 文件名**（不覆盖） |
| `WEBSEARCH_ENABLED=false` | 抛 `ValueError`（与 websearch.py 一致） |

---

## 八、测试

| 级别 | 验证 |
|---|---|
| L1 单元 | `parse_requirement_xlsx(gg_path)` 返回 1 条 row=6；`resolve_table_key("2.2 行业趋势分析表", mock_menu)` 命中含"行业"那条；`fill_cells` 写后 `openpyxl` 读回 B4-B9 内容一致 |
| L2 集成 | MCP 拉 2025 真实数据 + LLM 返 6 维 JSON + xlsx_exporter 写盘后 `xlsx_reader.read_template()` 读回 B4-B9 一致 |
| L3 端到端 | Tab 1 表单提交 → 下载 `<ts>_sp_2026_data.xlsx` → 人工检查 6 个 cell 内容质量（结论性 / 引用 / 中文） |
| L4 视觉 QA | (可选) 跑 `qa.thumbnail()` 确认主模板其他 sheet 未被改坏 |

### 单测 / E2E 命令

```bash
# 单元
python -m models.sp_change_2026 --test parse "D:/Desktop/gg/战略规划SP变更需求-6.5 版（产品需求沟通确认 2.0）.xlsx"
python -m models.sp_change_2026 --test resolve "2.2 行业趋势分析表"

# 集成（需 VPN/LLM）
python -m controllers.sp_change_2026_controller \
    "D:/Desktop/gg/战略规划SP变更需求-6.5 版（产品需求沟通确认 2.0）.xlsx" \
    --year 2026 \
    --sheets "2.2 行业趋势分析表"

# UI
streamlit run app.py
# Tab 1 → 末尾 "智能体自动填写模式" 表单
```

---

## 九、风险与已知约束

| 项 | 状态 | 应对 |
|---|---|---|
| 当前账号 `杨金威` 权限非 101 | 已知 | 仅看 'c' 维度；2.2 在 'c' 维度下应该能拉到 |
| LLM 截断 (reasoning 模型) | 已知 | 复用 `chat_with_fallback` + `final_max_tokens=12288` |
| 主模板 2.2 sheet 名 `2.2 行业趋势分析` (无"表"字) 与 D 列 `2.2 行业趋势分析表` 差一字 | 已知 | `resolve_table_key` 先去 "表" 字再关键字匹配 |
| DuckDuckGo 在公司内网可能被屏蔽 | 待验证 | 试点时若 web_search 全失败，临时关 `enable_thinking` 加速 + 接受 2026 预测无联网补充 |
| 6 维度标签从主模板现读 | 设计 | 若主模板 2.2 行数变化（A 列行数从 6 变 5/7），代码自动适配 |
| 22 张扩展时的 sheet 结构差异 | 已知 | 试点 2.2 (单结果列型) 跑通后，6.1/6.2 (Y1/Y2/Y3 多年型) 单独 spec |

---

## 十、依赖

无新增 pip / npm 包，全部用现有依赖：
- `openpyxl` — 读写 xlsx
- `openai` (Qwen3.5 OpenAI 兼容) — LLM 调用
- `duckduckgo-search` — 联网搜索
- `streamlit` — UI
- `requests` — iDSTE MCP REST
- `python-dotenv` — `.env`

---

## 十一、里程碑

| 阶段 | 内容 | 验证 |
|---|---|---|
| M1 | `models/sp_change_2026.py` + L1 单元 | parse / resolve / fill_cells 单元通过 |
| M2 | `models/prompts.py` + `models/xlsx_exporter.py.fill_cells` 增量 | 单 sheet 覆盖写成功 |
| M3 | `controllers/sp_change_2026_controller.py` + 集成 | MCP 2025 + LLM + 写盘 端到端 |
| M4 | `views/sp_change_2026_view.py` + 接入 Tab 1 | Streamlit UI 可提交 + 下载 |
| M5 | L3 端到端 + 人工审核 2.2 内容 | 6 维度结论质量 OK |

---

## 十二、未来扩展点（不在本次范围）

- 全 22 张「智能体自动...」sheet 自动填写（仅需把 prompt 主体做 sheet 类型分支：单结果列型 / BSC 多列型 / Y1-Y3 多年型 / KPI 列表型）
- `.env` 加 `SP_2026_TABLE_KEY_MAP` 显式映射（替代关键字匹配）
- 多年型 sheet (6.1/6.2) 的 Y1/Y2/Y3 → 2025/2026/2027 重映射逻辑
- 驱动文件 gg Excel 直接放桌面常驻 + Tab 自动检测
- L4 视觉 QA 自动化（thumbnail + 异常 cell 高亮）
