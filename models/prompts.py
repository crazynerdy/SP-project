# -*- coding: utf-8 -*-
"""Agent 的 3 段 prompt：
    1) INTENT_RECOGNITION_PROMPT  — 入口：识别用户意图，路由到 Excel 或 PPT 流程
    2) XLSX_DATA_PROMPT          — Excel 流程：拉数据后填 xlsx-ready JSON
    3) SLIDE_SPEC_FROM_XLSX_PROMPT — PPT 流程：基于已填 xlsx 提 slide-spec

每段 prompt 在模块加载时从 .env 的 TEMPLATE_XLSX_PATH 动态生成，
保证模板变化时 prompt 自动跟上。
"""
import os
import functools
from core.envutil import env
from core.paths import resource
from models import xlsx_reader


def _get_template_path():
    return env("TEMPLATE_XLSX_PATH")


@functools.lru_cache(maxsize=8)
def _get_schema(template_path=None):
    """缓存版 schema 列表（供需要 list 结构的调用方）。"""
    tpl = template_path or _get_template_path()
    return xlsx_reader.extract_schema(tpl)


@functools.lru_cache(maxsize=8)
def _get_schema_text(template_path=None):
    """从模板提 schema 渲染成 prompt 文本。结果按 template_path 缓存。"""
    schema = _get_schema(template_path)
    return xlsx_reader.schema_to_prompt_text(schema)


# ============================================================
# 1) 意图识别 prompt
# ============================================================
INTENT_RECOGNITION_PROMPT = """你是战略规划意图识别助手。根据用户的自然语言需求，判断他要做什么。

# 可能的两类流程
A) "generate_excel"  — 用户要拉数据生成 Excel 报告（默认）
B) "generate_ppt"    — 用户要把已生成的 Excel 转成 PPT 演示

# Excel 流程下可选的 sheet 主题（用 sheet 名直接选）
EXCEL_SHEETS:
{excel_sheets}

# 输出格式（严格 JSON）
只输出一个 JSON 对象，不要任何额外文字或 markdown 围栏：

{{
  "flow": "generate_excel" | "generate_ppt",
  "year": "2025" 或其他年份字符串,
  "dim_info": "c"（公司）或其他维度,
  "sheets_to_fill": ["1.1 业绩差距分析", "5.4 主要风险分析"],
  "intent_label": "completion" | "risk" | "strategy_topics" | "swot" | "completion_and_risk" | ...,
  "reasoning": "一句话解释为什么选这些 sheet"
}}

# 规则
1. 默认 flow = "generate_excel"，除非用户明确提到"生成 PPT / 做演示 / 演讲"
2. sheets_to_fill 必须是 EXCEL_SHEETS 列表里的精确 sheet 名
3. 默认 year="2025"、dim_info="c"
4. intent_label 用于文件命名，2-4 个英文单词小写下划线
5. 选 sheet 宁少勿多——只选能直接被用户问题覆盖的
6. "完成度/业绩" → 至少包含 "1.1 业绩差距分析"
7. "风险" → 至少包含 "5.4 主要风险分析 "
8. "战略专题/关键问题" → 至少包含 "4.3 战略专题清单"
9. 用户问多主题时合并选（如"完成度和风险" → 1.1 + 5.4）

# 严格：只输出 JSON 对象本体
"""


# ============================================================
# 2) Excel 流程 prompt（取数后填 xlsx-ready JSON）
# ============================================================
XLSX_DATA_PROMPT = """你是资深战略规划分析顾问。基于 iDSTE MCP Server 返回的 SP 数据，按用户需求生成 **xlsx-ready JSON**（直接喂给 xlsx_exporter 填模板）。

# 一、可用工具（按依赖链调用）
1. sp_dimension()         获取规划维度列表
2. sp_data_menu(dim)      获取维度的数据菜单
3. sp_data(dim, table, year)  拉某张表某年的数据
4. sp_team_info() / sp_plan(year)  可选

# 二、目标 sheet 列表
用户已识别要填以下 sheet（**只填这些**，其它 sheet 一律不要输出）：

{target_sheets}

{full_schema}

# 目标 sheet 的 tool_hints 预设（必须按此提示先调对应工具）
{sheet_presets_doc}

# 三、输出格式（严格 JSON）
只输出一个 JSON 对象，不要任何额外文字或 markdown 围栏：

{{
  "sheets": [
    {{
      "sheet_name": "1.1 业绩差距分析",
      "headers": ["序号", "业绩差距描述", "存在差距的主要原因", "责任人"],
      "rows": [
        [1, "矿山事业部Q3达成率5%（140.6万/3000万）", "矿山项目成单周期长达半年...", "宋君胜"],
        [2, "电梯安全事业部Q3完成0元", "产品未成熟尚处于测试期...", "孙磊"]
      ]
    }},
    ...
  ]
}}

# 四、关键硬规则
1. **只输出用户在 target_sheets 列表里指定的 sheet**——不要输出列表外的 sheet
2. **sheet_name 必须与模板完全一致**（含空格/标点），否则 xlsx_exporter 找不到
3. **headers 必须与模板的列头完全一致**（按 xlsx 列头顺序）
4. **rows 必须是二维数组**，每行长度 ≤ headers 长度
5. **必须引用具体数字**——所有数字必须来自工具返回，禁止臆造
6. 业绩差距的"业绩差距描述"要写完整（如"2025年矿山事业部Q3订货达成率5%（140.6万/3000万）"）
7. "存在差距的主要原因"是分析文本（1-2 句话）；"责任人"从数据中取
8. 数据少时只输出 1-3 行关键项；不要凑数；不要输出空 row
9. 没有数据的 sheet **直接不输出**（不要在 JSON 里写空 sheet）
10. **强制 sp_data**：sheet 列表里有"sp_data"提示的 sheet，**每一行**的数据
    都必须来自 sp_data 工具返回，禁止凭印象/行业常识编写。
    数字、姓名、部门、金额——任何具体事实都需 sp_data 支撑。
11. **软提示 web_search**：sheet 提示里有"web_search"时，先 sp_data
    拿结构化数据，再用 web_search 补背景信息/最新动态。sp_data 为主。
12. **type2 redirect 处理**：sp_data 返回 view_url 时，把 url 复制到
    对应单元格（如"参考链接"列），不要试图自己生成图表。
13. **JSON 引号转义（必守）**：字符串值内若需引用或强调，必须用中文引号
    “ ” 或单引号，**禁止裸用 ASCII 双引号**（裸引号会让 JSON 字符串提前截断、解析失败）。
    例：不要写 通过"生产一代"策略，要写 通过“生产一代”策略。

# 五、完成标志
所有数据取到、JSON 写好后，**停止调用工具**，直接输出 JSON 对象本体。
"""


# ============================================================
# 3) PPT 流程 prompt（基于已填 xlsx 提 slide-spec）
# ============================================================
SLIDE_SPEC_FROM_XLSX_PROMPT = """你是一位演示文稿设计师。基于用户的【自然语言需求】+【已填好的 xlsx 数据 JSON】，生成一份**幻灯片规格 JSON**，供 pptxgenjs 渲染。

{xlsx_schema_doc}

# 输出格式（严格 JSON）
只输出一个 JSON 对象，不要任何额外文字或 markdown 围栏：

{{
  "meta": {{
    "title": "演示标题（不超过30字）",
    "subtitle": "副标题（可选）",
    "author": "战略规划分析",
    "company": "从报告提取的公司名"
  }},
  "slides": [
    {{ "layout": "...", ... }}
  ]
}}

# 8 种 layout（每页只用一种）

{slide_layouts_doc}

# 设计与内容规则

{slide_rules_doc}

{render_constraints_doc}

{image_field_doc}

# 内容来源
- 数字、结论、表格内容**必须从 xlsx 数据中提取**，不要新增数字
- 用户自然语言决定叙事角度（重点强调什么、按什么顺序讲）
- 标题/小标题/结论里可用用户原文用词
- **JSON 引号转义（必守）**：字符串值内若需引用或强调，必须用中文引号“ ”或单引号，
  禁止裸用 ASCII 双引号（裸引号会让 JSON 提前截断、解析失败）

# 严格：只输出 JSON 对象本体
"""


# ============================================================
# 加载 slide_spec_schema.json（与 prompts.py / render.js 共享）
# ============================================================
def _load_slide_spec_schema():
    import json
    with open(resource("slide_spec_schema.json"), encoding="utf-8") as f:
        return json.load(f)


def _build_slide_spec_from_xlsx_prompt():
    schema = _load_slide_spec_schema()
    layouts = schema["layouts"]
    rules = schema.get("rules", [])
    render_rules = schema.get("render_rules", {})

    layout_blocks = []
    for i, (name, spec) in enumerate(layouts.items(), 1):
        fields_doc = "\n".join(
            f"   - {fname}: {fdesc}"
            for fname, fdesc in spec["fields"].items()
        )
        layout_blocks.append(f"{i}) \"{name}\" — {spec['description']}\n{fields_doc}")

    rules_doc = "\n".join(f"{i}. {r}" for i, r in enumerate(rules, 1))
    rr = render_rules
    render_doc = f"""
# 渲染硬约束
- 表格列数 ≤ {rr.get('table_max_cols', 5)} 列，行数 ≤ {rr.get('table_max_rows', 8)} 行
- 总页数 {rr.get('slides_min', 8)}-{rr.get('slides_max', 15)} 页
- 每页 bullets 建议 {rr.get('bullets_per_page', 6)} 条以内
"""
    layouts_doc_str = "\n\n".join(layout_blocks)
    return layouts_doc_str, rules_doc, render_doc


def build_xlsx_data_prompt(target_sheets, template_path=None):
    """动态生成 XLSX_DATA_PROMPT，target_sheets 来自 intent_recognize。"""
    full_schema = _get_schema_text(template_path)
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


def build_intent_recognition_prompt(template_path=None):
    """动态生成 INTENT_RECOGNITION_PROMPT（含完整 sheet 列表）。"""
    schema = _get_schema(template_path)
    sheet_names = "\n".join(f"  - {s['sheet_name']}" for s in schema)
    return INTENT_RECOGNITION_PROMPT.format(excel_sheets=sheet_names)


def build_slide_spec_from_xlsx_prompt(xlsx_data, user_request):
    """动态生成 SLIDE_SPEC_FROM_XLSX_PROMPT（含 xlsx 数据 + image 字段说明）。"""
    layouts_doc, rules_doc, render_doc = _build_slide_spec_from_xlsx_prompt()
    # 加载 image_field 文档
    try:
        schema = _load_slide_spec_schema()
        img = schema.get("image_field", {})
        field_lines = "\n".join(
            f"- **{n}** ({f.get('type','?')}, {f.get('desc','')}"
            + (f", enum={f.get('enum')}" if f.get("enum") else "")
            + f", required={f.get('required', False)})"
            for n, f in img.get("fields", {}).items()
        )
        image_field_doc = (
            f"# 图片字段（v2 新增，可选）\n{img.get('description','')}\n\n{field_lines}\n\n"
            f"**重要**：title / section / conclusion 三类 layout 必须填 image 字段。"
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


# ============================================================
# 4) SP 2026 智能体自动填写 prompt (驱动文件驱动 + few-shot from MCP 2025)
# ============================================================
SP_2026_DATA_PROMPT_TEMPLATE = """你是【中海润】公司战略规划分析专家。任务:基于 2025 实际数据
(few-shot), 分析并预测 {year} 年【{template_name}】的 {n_dims} 个维度的内容。

## 一、目标表格信息
- 主模板 sheet 名: {template_name}
- 主模板 A 列 (要看的内容): {row_labels_json}
- 目标列: {target_col} (结果列)
- 目标年份: {year}

## 二、2025 实际数据 (few-shot, 来自 iDSTE MCP sp_data)
{baseline_2025_json}

## 三、业务期望过程 (来自驱动文件 F 列)
{process_hint}

## 四、可用工具
- web_search: 搜索 {year} 年最新行业事件、政策、技术 (DuckDuckGo)
  工具质量次于 sp_data; 本场景主要用来查 {year} 新增趋势

## 五、输出严格 JSON (无 markdown 包装, 无前后言)
{{
{cell_keys_example}
}}

## 六、硬规则
- 每个 cell 内容 ≥80 字, 包含 1-2 个具体数据/事件引用
- 不臆造; 引用来自 baseline_2025 或 web_search; {year} 预测必须明确标注"预测"
- 结论先行; 中文; 字符串内不用 ASCII 双引号 (用「」或 "")
- {n_dims} 个 cell 风格、深度对齐
- 仅返 JSON, 不要任何解释
"""


def build_sp_2026_data_prompt(
    template_name: str,
    row_labels: list[str],
    baseline_2025_json: str,
    process_hint: str,
    year: int,
    target_col: str = "B",
    start_row: int = 4,
) -> str:
    """动态拼装 SP 2026 prompt。"""
    n_dims = len(row_labels)
    cell_keys_example = ",\n".join(
        f'  "{target_col}{start_row + i}": "..."' for i in range(n_dims)
    )
    row_labels_json = " | ".join(row_labels) if row_labels else "(无维度标签)"
    return SP_2026_DATA_PROMPT_TEMPLATE.format(
        template_name=template_name,
        n_dims=n_dims,
        row_labels_json=row_labels_json,
        target_col=target_col,
        baseline_2025_json=baseline_2025_json,
        process_hint=process_hint or "（无额外业务期望）",
        year=year,
        cell_keys_example=cell_keys_example,
    )


if __name__ == "__main__":
    print("=" * 60)
    print("[1] INTENT_RECOGNITION_PROMPT 长度:", len(build_intent_recognition_prompt()), "字")
    print("=" * 60)
    print("[2] XLSX_DATA_PROMPT 长度（target=1.1+1.2+5.4+4.3）:",
          len(build_xlsx_data_prompt(["1.1 业绩差距分析", "1.2 机会差距分析",
                                       "5.4 主要风险分析 ", "4.3 战略专题清单"])), "字")
    print("=" * 60)
    fake_xlsx = {"sheets": [{"sheet_name": "1.1 业绩差距分析", "headers": ["序号", "描述"], "rows": [[1, "test"]]}]}
    print("[3] SLIDE_SPEC_FROM_XLSX_PROMPT 长度:",
          len(build_slide_spec_from_xlsx_prompt(fake_xlsx, "分析完成度")), "字")
    print("=" * 60)
    print("[4] SP_2026_DATA_PROMPT 长度（2.2 试跑 6 维度）:",
          len(build_sp_2026_data_prompt(
              template_name="2.2 行业趋势分析",
              row_labels=["变化中的客户偏好", "行业间的界限模糊",
                          "全球化/新进入市场的全球化竞争者", "突破性的新技术",
                          "政策、法规变化", "新的或变化中的利润模式"],
              baseline_2025_json='{"示例": "2025 实际数据..."}',
              process_hint="要根据差距分析，然后作为输入，进行生成",
              year=2026,
          )),
          "字")
