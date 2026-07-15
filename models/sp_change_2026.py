# -*- coding: utf-8 -*-
"""SP 2026 智能体自动填写 - 业务核心。

解析驱动文件 (gg/战略规划SP变更需求-*.xlsx) -> 过滤"智能体自动..."行 ->
对每行调 MCP 拉 2025 实际数据 (few-shot) -> LLM + 联网生成 2026 单元格数据。
"""
from __future__ import annotations
import os
import re
from dataclasses import dataclass, asdict
from openpyxl import load_workbook
from models import idste


AUTO_FILL_MARKERS = {"智能体自动搜索填写", "智能体自动分析总结"}


@dataclass
class RequirementRow:
    """驱动文件里一行 (BLM 战略规划研究内容追踪表)。"""
    row: int
    blm_module: str
    stage_step: str
    research_content: str
    output_template: str
    data_source: str
    process_hint: str
    idste_module: str
    note: str

    def to_dict(self) -> dict:
        return asdict(self)


def parse_requirement_xlsx(path: str) -> list[RequirementRow]:
    """读驱动文件 Excel, 过滤 E in AUTO_FILL_MARKERS 的行。"""
    if not os.path.exists(path):
        raise FileNotFoundError(f"驱动文件不存在: {path}")
    if not path.lower().endswith((".xlsx", ".xlsm")):
        raise ValueError(f"驱动文件必须是 .xlsx: {path}")

    wb = load_workbook(path, data_only=True)
    ws = wb[wb.sheetnames[0]]

    rows: list[RequirementRow] = []
    for r_idx in range(3, ws.max_row + 1):
        a = ws.cell(row=r_idx, column=1).value
        e = ws.cell(row=r_idx, column=5).value
        if e is None:
            continue
        e_str = str(e).strip()
        if e_str not in AUTO_FILL_MARKERS:
            continue
        rows.append(RequirementRow(
            row=r_idx,
            blm_module=str(a or "").strip(),
            stage_step=str(ws.cell(row=r_idx, column=2).value or "").strip(),
            research_content=str(ws.cell(row=r_idx, column=3).value or "").strip(),
            output_template=str(ws.cell(row=r_idx, column=4).value or "").strip(),
            data_source=e_str,
            process_hint=str(ws.cell(row=r_idx, column=6).value or "").strip(),
            idste_module=str(ws.cell(row=r_idx, column=7).value or "").strip(),
            note=str(ws.cell(row=r_idx, column=8).value or "").strip(),
        ))
    return rows


def _normalize_template_name(name: str) -> str:
    """去"表"字 + 去空白, 方便与 menu 里 table.name 模糊匹配。"""
    return re.sub(r"\s+", "", name).rstrip("表")


def resolve_table_key(template_name: str, menu, keyword: str | None = None) -> str:
    """把 D 列里的"输出表格/图形模版"名解析为 MCP table_key。"""
    candidates = idste._find_table_keys(menu)
    if not candidates:
        raise ValueError(
            f"sp_data_menu 返回里未发现任何 table_key, 无法解析 {template_name!r}"
        )

    normalized = _normalize_template_name(template_name)
    if keyword is None:
        keyword = "".join(re.findall(r"[一-鿿]+", normalized))

    for c in candidates:
        cname = re.sub(r"\s+", "", c.get("name") or "")
        for chunk in re.findall(r"[一-鿿]{2,}", normalized):
            if chunk in cname:
                return c["table_key"]

    for c in candidates:
        cname = re.sub(r"\s+", "", c.get("name") or "")
        if keyword and keyword in cname:
            return c["table_key"]

    raise ValueError(
        f"主模板 sheet {template_name!r} (normalized={normalized!r}, "
        f"keyword={keyword!r}) 未在 MCP 菜单中找到。\n"
        f"MCP 菜单候选: {[c.get('name') for c in candidates[:8]]}"
    )


if __name__ == "__main__":
    import sys

    DRIVE_FILE = r"D:\Desktop\gg\战略规划SP变更需求-6.5 版（产品需求沟通确认 2.0）.xlsx"

    print("=" * 60)
    print("== [1] parse_requirement_xlsx 离线单元测试 ==")
    rows = parse_requirement_xlsx(DRIVE_FILE)
    print(f"驱动文件: {DRIVE_FILE}")
    print(f"发现 {len(rows)} 行「智能体自动...」:")
    for r in rows:
        print(f"  row={r.row} D={r.output_template!r} E={r.data_source!r}")

    print()
    print("=" * 60)
    print("== [2] resolve_table_key 在线测试 (需 VPN/iDSTE) ==")
    if len(sys.argv) > 1 and sys.argv[1] == "--online":
        menu = idste.sp_data_menu("c")
        for r in rows[:3]:
            try:
                tk = resolve_table_key(r.output_template, menu)
                print(f"  {r.output_template} -> {tk} OK")
            except ValueError as e:
                print(f"  {r.output_template} -> FAIL: {e}")
    else:
        print("  (跳过; 跑 `python -m models.sp_change_2026 --online` 启用)")
