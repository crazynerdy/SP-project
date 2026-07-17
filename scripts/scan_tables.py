# -*- coding: utf-8 -*-
"""扫描公司维度下所有 SP 表，分类哪些通过 MCP 返回真实数据、哪些是 redirect（二类表）。

用法: python scan_tables.py
"""
import json
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from models.idste import sp_data_menu, sp_data


def main():
    menu = sp_data_menu("c")
    menus = (menu or {}).get("data", {}).get("menus", []) if isinstance(menu, dict) else []
    tables = []
    for m in menus:
        if not isinstance(m, dict):
            continue
        for t in m.get("tables", []) or []:
            if not isinstance(t, dict):
                continue
            tables.append((
                t.get("table_key"),
                m.get("menu_title", ""),
                t.get("table_title", ""),
            ))

    print(f"共 {len(tables)} 张表，逐一探测...\n")
    data_tables = []
    for tk, mtitle, title in tables:
        try:
            d = sp_data("c", tk, "2025")
            data = d.get("data", d)
            ttype = data.get("table_type", "?")
            status = data.get("status", "")
            if status == "redirect" or ttype == "type2":
                print(f"[REDIRECT] {tk:14} [{mtitle}] {title}")
            else:
                keys = list(data.keys())[:10] if isinstance(data, dict) else []
                print(f"[DATA    ] type={ttype:8} {tk:14} [{mtitle}] {title}  keys={keys}")
                data_tables.append((tk, mtitle, title, data))
        except Exception as e:
            print(f"[ERR     ] {tk:14} [{mtitle}] {title}  {e}")

    print(f"\n可分析(有数据)的表: {len(data_tables)} / {len(tables)}")

    # 抽样打印第一张有数据的表的完整结构，供 prompt 设计参考
    if data_tables:
        tk, mtitle, title, data = data_tables[0]
        print(f"\n=== 样本: [{mtitle}] {title} ({tk}) 完整结构 ===")
        print(json.dumps(data, ensure_ascii=False, indent=2)[:3000])


if __name__ == "__main__":
    main()
