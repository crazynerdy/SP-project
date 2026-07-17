# -*- coding: utf-8 -*-
"""SP Agent CLI — 统一命令行入口。

用法:
    python -m sp_agent [sheet_id ...]

示例:
    python -m sp_agent "2.2 行业趋势分析表"
    python -m sp_agent  # 跑全部 enabled sheet
"""
from __future__ import annotations

import sys


def main(argv=None):
    argv = argv or sys.argv[1:]
    if not argv:
        print("用法: python -m sp_agent <sheet_id> ...")
        print("       python -m sp_agent  # 跑全部 enabled sheet")
        print("示例: python -m sp_agent '2.2 行业趋势分析表'")
        sys.exit(0)

    # TODO: PR3+ 接入完整 WorkflowEngine 调度
    print(f"[sp_agent] 待调度 sheet: {argv}")
    print("[sp_agent] 完整 CLI 实现见后续 PR（当前为占位）")


if __name__ == "__main__":
    main()
