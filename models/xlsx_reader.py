# -*- coding: utf-8 -*-
"""xlsx 读写：提取模板 schema + 读已填 xlsx 转 JSON。

两个核心函数：
    extract_schema(template_path)  ->  每张 sheet 的 {sheet_name, title, description, headers}
    read_template(xlsx_path, sheets=None)  ->  已填 xlsx 转 JSON（给 PPT 流程用）
"""
import os
import json
from openpyxl import load_workbook


def extract_schema(template_path):
    """从模板 xlsx 提取所有 sheet 的列结构。

    每张 sheet 假设结构：
        Row 1: 标题
        Row 2: 说明 (description)
        Row 3: 列头 (headers)
        Row 4+: 空白数据行

    Returns:
        list of dict:
            [
                {"sheet_name": "战略规划SP总览", "title": "...", "description": "...", "headers": [...]},
                {"sheet_name": "1.1 业绩差距分析", "title": "双差分析-业绩差距", "description": "说明...", "headers": ["序号", "业绩差距描述", ...]},
                ...
            ]
    """
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"模板不存在: {template_path}")

    wb = load_workbook(template_path, data_only=True)
    schema = []
    for sn in wb.sheetnames:
        ws = wb[sn]
        row1 = _row_values(ws, 1)
        row2 = _row_values(ws, 2)
        row3 = _row_values(ws, 3)

        title = row1[0] if row1 else ""
        description = row2[0] if row2 else ""
        # headers: row 3 的所有非空单元格
        headers = [c for c in row3 if c]

        # 跳过"战略规划SP总览"——它是 TOC，不是数据 sheet
        if sn == "战略规划SP总览":
            continue

        schema.append({
            "sheet_name": sn,
            "title": str(title).strip() if title else "",
            "description": str(description).strip()[:200] if description else "",  # 截断避免 prompt 过长
            "headers": [str(h).strip() for h in headers],
        })
    return schema


def schema_to_prompt_text(schema):
    """把 schema 渲染成 LLM prompt 友好的文本。

    格式:
        [1.1 业绩差距分析]
        标题: 双差分析-业绩差距
        说明: 对照公司整体业绩目标...
        列: 序号 | 业绩差距描述 | 存在差距的主要原因 | 责任人

        [1.2 机会差距分析]
        ...
    """
    blocks = []
    for s in schema:
        blocks.append(
            f"[{s['sheet_name']}]\n"
            f"标题: {s['title']}\n"
            f"说明: {s['description']}\n"
            f"列: {' | '.join(s['headers'])}"
        )
    return "\n\n".join(blocks)


def read_template(xlsx_path, sheets=None):
    """读已填 xlsx，转 JSON 供 PPT 流程使用。

    Args:
        xlsx_path: xlsx 文件路径
        sheets: 可选，sheet 名列表（None = 全部）

    Returns:
        dict:
            {
                "sheets": [
                    {
                        "sheet_name": "1.1 业绩差距分析",
                        "title": "...",
                        "headers": [...],
                        "rows": [[1, "...", "...", "..."], ...]
                    }
                ]
            }
    """
    if not os.path.exists(xlsx_path):
        raise FileNotFoundError(f"xlsx 不存在: {xlsx_path}")
    wb = load_workbook(xlsx_path, data_only=True)

    result_sheets = []
    # 与 fill_template 对齐：建 strip 后名字集合，容错模板/入参尾空格
    want = {s.strip() for s in sheets} if sheets else None
    for sn in wb.sheetnames:
        if want is not None and sn.strip() not in want:
            continue
        if sn == "战略规划SP总览":
            continue

        ws = wb[sn]
        row1 = _row_values(ws, 1)
        row3 = _row_values(ws, 3)

        title = row1[0] if row1 else ""
        headers = [str(h).strip() for h in row3 if h]

        # 数据从 row 4 开始，跳过空白行
        rows = []
        for r_idx in range(4, ws.max_row + 1):
            row = _row_values(ws, r_idx)
            if any(c is not None and str(c).strip() != "" for c in row[:len(headers)]):
                rows.append([c if c is not None else "" for c in row[:len(headers)]])

        if not headers and not rows:
            continue  # 跳过完全空的 sheet

        result_sheets.append({
            "sheet_name": sn,
            "title": str(title).strip() if title else "",
            "headers": headers,
            "rows": rows,
        })

    return {"sheets": result_sheets}


def list_sheet_names(template_path):
    """返回模板里所有数据 sheet 名（不含 SP总览）。"""
    return [s["sheet_name"] for s in extract_schema(template_path)]


def _row_values(ws, row_idx):
    """读一行的所有列值，转成字符串列表。"""
    return [c.value for c in ws[row_idx]]


if __name__ == "__main__":
    from core.envutil import env
    tpl = env("TEMPLATE_XLSX_PATH")
    print(f"Template: {tpl}")
    print("=" * 60)
    schema = extract_schema(tpl)
    print(f"共 {len(schema)} 张数据 sheet")
    for s in schema[:3]:
        print(f"\n[{s['sheet_name']}]")
        print(f"  标题: {s['title']}")
        print(f"  说明: {s['description'][:60]}...")
        print(f"  列: {s['headers']}")
    print("\n--- 读刚才生成的 xlsx（如果有） ---")
    import os
    out = "output"
    if os.path.isdir(out):
        xlsx_files = [f for f in os.listdir(out) if f.endswith("_data.xlsx")]
        if xlsx_files:
            latest = sorted(xlsx_files)[-1]
            xlsx_path = os.path.join(out, latest)
            data = read_template(xlsx_path)
            print(f"读 {xlsx_path}：共 {len(data['sheets'])} 张 sheet 有数据")
            for s in data["sheets"][:2]:
                print(f"  [{s['sheet_name']}] {len(s['rows'])} 行")
        else:
            print("(暂无已填的 xlsx)")
