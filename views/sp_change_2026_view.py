# -*- coding: utf-8 -*-
"""SP 2026 智能体自动填写 - Tab 1 末尾子区块 View 层。

表单 (驱动文件路径 + 目标年份 + sheet 过滤) -> 调 controller 端到端编排 ->
结果展示 (成功提示 + 工具调用统计 + 错误 expander + 下载按钮)。

只渲染 + 调 controller, 不直接碰 MCP / LLM。结果存 session_state["sp2026_result"],
与现有 Excel 自然语言流程 (last_xlsx_path / last_tool_call_stats) 隔离, 互不污染。
"""
import os
import streamlit as st

from views import ui_theme
from core.envutil import env
from controllers import sp_change_2026_controller as sp2026_ctrl


# 驱动文件默认路径: 优先读 .env 的 GG_XLSX_PATH, 否则用桌面 gg/ 子目录
DEFAULT_GG_PATH = env("GG_XLSX_PATH") or r"D:\Desktop\gg\战略规划SP变更需求-6.5 版（产品需求沟通确认 2.0）.xlsx"


def render_sp_change_2026_form(template_path: str):
    """渲染 SP 2026 智能体自动填写区块: 表单 + 结果 + 下载。

    Args:
        template_path: 主模板 xlsx 路径 (app.py 的 TEMPLATE_PATH)
    """
    with st.container(border=True):
        ui_theme.section_title("智能体自动填写", "SP 2026 端到端生成")
        st.caption("驱动文件 (gg/战略规划SP变更需求-*.xlsx) -> MCP 拉 2025 基线 -> LLM + web_search -> 写主模板副本")

        gg_path = st.text_input("驱动文件路径", value=DEFAULT_GG_PATH, key="sp2026_gg_path")
        year = st.number_input(
            "目标年份", min_value=2024, max_value=2030, value=2026, step=1, key="sp2026_year",
        )
        sheet_filter = st.text_input(
            "限定 sheet 名 (可选, 逗号分隔)", value="2.2 行业趋势分析表", key="sp2026_sheet_filter",
        )
        clicked = st.button("生成 2026 报告", type="primary", use_container_width=True, key="btn_sp2026")

    if clicked:
        _run_with_spinner(gg_path, template_path, int(year), sheet_filter)

    _render_result()


def _run_with_spinner(gg_path, template_path, year, sheet_filter):
    """调 controller 跑端到端编排, 结果 (或异常) 写 session_state["sp2026_result"]。"""
    target_sheets = None
    raw = sheet_filter.strip()
    if raw:
        target_sheets = [s.strip() for s in raw.split(",") if s.strip()]

    try:
        with st.spinner("正在生成 2026 报告, 预计 30-60s..."):
            result = sp2026_ctrl.run_sp_change_2026(
                gg_xlsx_path=gg_path,
                template_xlsx_path=template_path,
                year=year,
                target_sheet_names=target_sheets,
                verbose=False,
            )
        st.session_state["sp2026_result"] = result
    except Exception as e:
        st.session_state["sp2026_result"] = {"error": f"{type(e).__name__}: {e}"}
        with st.expander("异常详情"):
            st.exception(e)


def _render_result():
    """从 session_state 读结果, 渲染成功提示 / 工具统计 / 错误 / 下载按钮。无结果时静默返回。"""
    result = st.session_state.get("sp2026_result")
    if not result:
        return

    # 异常分支
    if result.get("error"):
        st.error(f"生成失败: {result['error']}")
        return

    out_path = result.get("output_xlsx_path")
    filled = result.get("filled_sheets", [])
    errors = result.get("errors", [])
    stats = result.get("tool_call_stats", {}).get("__all__", {})

    # 成功提示
    if out_path:
        st.success(f"2026 报告生成完毕: {os.path.basename(out_path)} (填 {len(filled)} sheet)")
    else:
        st.warning("未生成任何 sheet")

    # 工具调用统计
    if stats:
        with st.container(border=True):
            ui_theme.section_title("运行明细", "工具调用统计")
            for name, n in stats.items():
                st.markdown(f"- **{name}** x {n}")

    # 失败 sheet expander
    if errors:
        with st.expander(f"失败 sheet ({len(errors)})"):
            for e in errors:
                st.markdown(f"- **{e['sheet']}**: {e['error']}")

    # 下载按钮
    if out_path and os.path.exists(out_path):
        with open(out_path, "rb") as f:
            st.download_button(
                "下载 2026 报告",
                f,
                file_name=os.path.basename(out_path),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                type="primary",
                key="dl_sp2026",
            )
        st.caption(f"{os.path.getsize(out_path) / 1024:.1f} KB - XLSX")
    elif out_path:
        st.warning(f"文件不存在: {out_path}")
