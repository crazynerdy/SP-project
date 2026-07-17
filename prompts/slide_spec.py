# -*- coding: utf-8 -*-
"""Slide Spec Prompt（基于已填 xlsx 生成 PPT 规格）。"""
from prompts._common import _load_slide_spec_schema


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
- **JSON 引号转义（必守）**：字符串值内若需引用或强调，必须用中文引号""或单引号，
  禁止裸用 ASCII 双引号（裸引号会让 JSON 提前截断、解析失败）

# 严格：只输出 JSON 对象本体
"""


def _build_slide_spec_from_xlsx_prompt():
    """构建 slide-spec 的 layout/rules/render 文档段落。"""
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
        layout_blocks.append(f'{i}) "{name}" — {spec["description"]}\n{fields_doc}')

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


def build_slide_spec_from_xlsx_prompt(xlsx_data, user_request):
    """动态生成 SLIDE_SPEC_FROM_XLSX_PROMPT（含 xlsx 数据 + image 字段说明）。"""
    layouts_doc, rules_doc, render_doc = _build_slide_spec_from_xlsx_prompt()
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
