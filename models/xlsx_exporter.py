# -*- coding: utf-8 -*-
"""xlsx 导出：LLM 输出的 JSON + 模板 → 填好的 .xlsx。

LLM 输出结构（agent.generate_xlsx_data 返回）:
    {
        "sheets": [
            {
                "sheet_name": "1.1 业绩差距分析",
                "headers": ["序号", "业绩差距描述", "存在差距的主要原因", "责任人"],
                "rows": [
                    [1, "矿山事业部Q3达成率5%（140.6万/3000万）", "...", "宋君胜"],
                    ...
                ]
            },
            ...
        ]
    }

模板假设结构：
    Row 1: 标题
    Row 2: 说明
    Row 3: 列头
    Row 4+: 空白数据行
"""
import os
import re
import shutil
from openpyxl import load_workbook


def fill_template(json_data, template_path, output_path=None):
    """把 LLM 输出写入模板副本。

    Args:
        json_data: LLM 输出的 xlsx-ready dict
        template_path: 模板 xlsx 路径
        output_path: 输出 .xlsx 路径；为 None 时返回 bytes（内存模式，不写盘）

    Returns:
        dict: {filled: 写成功的 sheet 数, missing: 没匹配的 sheet 名, output_path}
              output_path 在内存模式下为 None, 额外含 "xlsx_bytes" 字段
    """
    import io
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"模板不存在: {template_path}")
    if "sheets" not in json_data or not json_data["sheets"]:
        raise ValueError("json_data.sheets 为空，没法填表")

    memory_mode = output_path is None
    if not memory_mode:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    buf = io.BytesIO()
    with open(template_path, "rb") as f:
        buf.write(f.read())
    buf.seek(0)

    wb = load_workbook(buf)
    # 建 strip 后名字 -> 原始 sheet 名映射，容错模板里的尾空格/不规则空格
    # （如模板 "5.4 主要风险分析 " 带尾空格，LLM 输出 "5.4 主要风险分析" 无尾空格）
    available = {name.strip(): name for name in wb.sheetnames}

    filled = []
    missing = []
    for sheet_data in json_data["sheets"]:
        sn = sheet_data.get("sheet_name", "").strip()
        if sn not in available:
            missing.append(sn)
            continue

        ws = wb[available[sn]]  # 用原始 sheet 名取 worksheet
        # 清空 row 3 (headers) 及以下，保留 row 1-2
        _clear_data_rows(ws)

        # 写 headers 到 row 3
        headers = sheet_data.get("headers", [])
        if not headers and sheet_data.get("rows"):
            import warnings
            warnings.warn(
                f"sheet '{sn}' 有 rows 但 headers 为空，已跳过（无法定位列）"
            )
            missing.append(sn)
            continue
        for col_idx, h in enumerate(headers, 1):
            ws.cell(row=3, column=col_idx, value=h)

        # 写 rows 从 row 4
        for row_idx, row in enumerate(sheet_data.get("rows", []), start=4):
            for col_idx, val in enumerate(row, 1):
                if col_idx > len(headers):
                    break
                ws.cell(row=row_idx, column=col_idx, value=val)

        filled.append(sn)

    try:
        if memory_mode:
            buf.seek(0)
            wb.save(buf)
            xlsx_bytes = buf.getvalue()
        else:
            wb.save(output_path)
    except PermissionError as e:
        raise PermissionError(
            f"xlsx 保存失败（文件可能被 Excel 占用）: {output_path} - {e}"
        ) from e
    except Exception as e:
        path_info = output_path or "<memory>"
        raise RuntimeError(f"xlsx 保存失败: {path_info} - {e}") from e
    finally:
        buf.close()

    if missing:
        import warnings
        warnings.warn(f"以下 sheet 名在模板里找不到（可能拼写有误）: {missing}")

    result = {
        "filled": filled,
        "missing": missing,
        "output_path": output_path,
        "filled_count": len(filled),
    }
    if memory_mode:
        result["xlsx_bytes"] = xlsx_bytes
    return result


def _clear_data_rows(ws):
    """清空 row 3 及以下的单元格值（保留行高/列宽/样式，不删行）。

    用 cell.value=None 替代 delete_rows：delete_rows 会销毁模板预设的
    边框/填充/数字格式，且大表时性能差；清值保留样式更稳。
    """
    if ws.max_row < 3:
        return
    for r in range(3, ws.max_row + 1):
        for c in range(1, ws.max_column + 1):
            ws.cell(row=r, column=c).value = None


def fill_cells(template_path, sheet_name, cells, mode="overwrite", out_path=None):
    """把指定 cell 覆盖/追加写入主模板副本。

    与 fill_template 的区别:
    - fill_template 是 LLM 输出"全 sheet"结构 (headers + rows), 批量重写 row 3+
    - fill_cells 是 dict-based (B4 -> "..."), 点对点写具体 cell, **不动其他 cell**

    Raises:
        FileNotFoundError: 模板不存在
        KeyError: sheet_name 不在模板里
        ValueError: mode 未知 或 cells 为空
    """
    if mode not in ("overwrite", "append_row"):
        raise ValueError(f"未知 mode: {mode!r}（仅支持 overwrite / append_row）")
    if not cells:
        raise ValueError("cells 为空")

    if not os.path.exists(template_path):
        raise FileNotFoundError(f"模板不存在: {template_path}")

    if out_path is None:
        from datetime import datetime
        from uuid import uuid4
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = "output"
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f"{ts}_sp_2026_{uuid4().hex[:8]}_data.xlsx")
    else:
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    shutil.copyfile(template_path, out_path)
    wb = load_workbook(out_path)

    available = {name.strip(): name for name in wb.sheetnames}
    sname_norm = sheet_name.strip()
    if sname_norm not in available:
        raise KeyError(
            f"模板里没有 sheet {sheet_name!r}。已有: {list(wb.sheetnames)[:5]}..."
        )
    real_sname = available[sname_norm]
    ws = wb[real_sname]

    for coord, val in cells.items():
        if mode == "overwrite":
            ws[coord] = val
        elif mode == "append_row":
            if len(cells) != 1:
                raise ValueError("append_row 模式仅支持单 key cells")
            col_letter = re.match(r"^([A-Z]+)", coord).group(1)
            target_col_idx = ws[f"{col_letter}1"].column
            row = ws.max_row + 1
            while row > 1 and ws.cell(row=row - 1, column=target_col_idx).value not in (None, ""):
                row -= 1
            while row <= ws.max_row and ws.cell(row=row, column=target_col_idx).value not in (None, ""):
                row += 1
            ws.cell(row=row, column=target_col_idx, value=val)

    try:
        wb.save(out_path)
    except PermissionError as e:
        raise PermissionError(
            f"xlsx 保存失败（文件可能被 Excel 占用）: {out_path} - {e}"
        ) from e

    return out_path


if __name__ == "__main__":
    from core.envutil import env
    tpl = env("TEMPLATE_XLSX_PATH")

    # --- Test 1: 原 fill_template 不动 ---
    test_data = {
        "sheets": [
            {
                "sheet_name": "1.1 业绩差距分析",
                "headers": ["序号", "业绩差距描述", "存在差距的主要原因", "责任人"],
                "rows": [[1, "测试行 1", "测试原因", "测试人"]],
            }
        ]
    }
    out1 = "output/test_fill_template.xlsx"
    result = fill_template(test_data, tpl, out1)
    print(f"[fill_template] filled: {result['filled']} missing: {result['missing']}")

    # --- Test 2: 新 fill_cells overwrite ---
    test_cells = {"B4": "2026 客户偏好预测：消费者更注重健康环保..."}
    out2 = fill_cells(tpl, "2.2 行业趋势分析", test_cells, mode="overwrite")
    print(f"[fill_cells overwrite] out: {out2}")

    # --- Test 3: 读回验证 ---
    wb = load_workbook(out2)
    ws = wb["2.2 行业趋势分析"]
    print(f"[verify] B4 = {ws['B4'].value!r}")

    # --- Test 4: 多 cell overwrite ---
    test_cells_4 = {
        "B4": "2026 维度 1",
        "B5": "2026 维度 2",
        "B9": "2026 维度 6",
    }
    out3 = fill_cells(tpl, "2.2 行业趋势分析", test_cells_4)
    wb3 = load_workbook(out3)
    ws3 = wb3["2.2 行业趋势分析"]
    for coord, expected in test_cells_4.items():
        actual = ws3[coord].value
        ok = "OK" if actual == expected else "FAIL"
        print(f"[verify multi] {coord} = {actual!r}  {ok}")

    # --- Test 5: sheet 不存在应抛 KeyError ---
    try:
        fill_cells(tpl, "9.9 不存在的 sheet", {"A1": "x"})
        print("[error] 应抛 KeyError 但没抛 FAIL")
    except KeyError:
        print(f"[error path] KeyError 正确抛出 OK")
