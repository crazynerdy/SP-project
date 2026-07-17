# -*- coding: utf-8 -*-
"""SP 2026 智能体自动填写 - Tab 1 末尾子区块 View 层。

表单 (年份 + sheet 过滤) -> 初始化 WorkflowEngine -> 端到端 DAG 编排 ->
结果展示 (成功提示 + 工具调用统计 + 错误 expander + 下载按钮)。

结果存 session_state["sp2026_result"], 与现有 Excel 自然语言流程隔离。
"""
import os
import streamlit as st

from views import ui_theme
from core.strategic_context import StrategyContextBuilder
from core.workflow_engine import WorkflowEngine
from config import load_tasks
from agents import AGENT_REGISTRY


_YEAR_OPTIONS = list(range(2026, 2032))


def render_sp_change_2026_form(template_path: str):
    """渲染 SP 智能体自动填写区块: 表单 + 结果 + 下载。

    Args:
        template_path: 主模板 xlsx 路径 (app.py 的 TEMPLATE_PATH)
    """
    with st.container(border=True):
        year = st.selectbox("年份", options=_YEAR_OPTIONS, index=0, key="sp2026_year")
        ui_theme.section_title("智能体自动填写", f"SP {year}年 DAG 工作流")
        st.caption("YAML 驱动 DAG → 拓扑排序 → 3 类 Agent → Pydantic 校验 → 写主模板 → 生成 PPT")

        sheet_filter = st.text_input(
            "限定 sheet 名 (可选, 逗号分隔)", value="2.2 行业趋势分析表", key="sp2026_sheet_filter",
        )
        clicked = st.button(f"生成 {year} 报告", type="primary", use_container_width=True, key="btn_sp2026")

    if clicked:
        _run_with_spinner(template_path, year, sheet_filter)

    _render_result()


def _run_with_spinner(template_path, year, sheet_filter):
    """初始化 WorkflowEngine 并执行。"""
    target_sheets = None
    raw = sheet_filter.strip()
    if raw:
        target_sheets = [s.strip() for s in raw.split(",") if s.strip()]

    try:
        with st.spinner("正在初始化 MCP 上下文..."):
            builder = StrategyContextBuilder(dim_info="c", year=str(year - 1))
            context = builder.build(target_tables=[])

        with st.spinner(f"正在运行 DAG 工作流, 预计 30-120s..."):
            engine = WorkflowEngine(
                tasks=load_tasks(),
                context=context,
                agents=AGENT_REGISTRY,
                template_path=template_path,
                output_dir="output",
                verbose=False,
            )
            result = engine.run(sheet_ids=target_sheets)

        st.session_state["sp2026_result"] = result
    except Exception as e:
        st.session_state["sp2026_result"] = {"error": f"{type(e).__name__}: {e}"}
        with st.expander("异常详情"):
            st.exception(e)


def _render_result():
    """从 session_state 读结果, 渲染成功提示 / 工具统计 / 错误 / 下载按钮。"""
    result = st.session_state.get("sp2026_result")
    if not result:
        return

    if result.get("error"):
        st.error(f"生成失败: {result['error']}")
        return

    out_path = result.get("output_xlsx_path")
    pptx_path = result.get("pptx_path")
    filled = result.get("filled_sheets", [])
    errors = result.get("errors", [])
    stats = result.get("tool_call_stats", {}).get("__all__", {})

    if out_path:
        st.success(f"报告生成完毕: {os.path.basename(out_path)} (填 {len(filled)} 个 sheet)")
    else:
        st.warning("未生成任何 sheet")

    if stats:
        with st.container(border=True):
            ui_theme.section_title("运行明细", "工具调用统计")
            for name, n in stats.items():
                st.markdown(f"- **{name}** x {n}")

    if errors:
        with st.expander(f"失败 sheet ({len(errors)})"):
            for e in errors:
                st.markdown(f"- **{e.get('sheet_id', e.get('sheet', ''))}**: {e['error']}")

    if out_path and os.path.exists(out_path):
        with open(out_path, "rb") as f:
            st.download_button(
                "下载 报告",
                f,
                file_name=os.path.basename(out_path),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                type="primary",
                key="dl_sp2026",
            )
        st.caption(f"{os.path.getsize(out_path) / 1024:.1f} KB - XLSX")

    if pptx_path and os.path.exists(pptx_path):
        with open(pptx_path, "rb") as f:
            st.download_button(
                "下载 PPT",
                f,
                file_name=os.path.basename(pptx_path),
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                use_container_width=True,
                key="dl_sp2026_pptx",
            )