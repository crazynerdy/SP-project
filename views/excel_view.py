# -*- coding: utf-8 -*-
"""Excel Tab 的 View 层：表单渲染 + 结果渲染。只渲染，不调 agent。"""
import os
import html as _html
import streamlit as st

from views import ui_theme


def render_excel_form(idste_healthy):
    """渲染 Excel 表单，返回 {request, clicked, retry}。

    iDSTE 不可达时：显示不可达提示 + 禁用生成按钮 + 重试按钮（clicked=False）。
    iDSTE 可达时：显示生成按钮（不显示重试，已连上无需重试）。
    """
    with st.container(border=True):
        ui_theme.section_title("Excel", "自然语言到 Excel 分析报告")

        req = st.text_area(
            "分析需求",
            value=st.session_state.get("excel_input", ""),
            placeholder="例：分析2025年公司SP战略规划完成度，重点关注业绩差距和主要风险",
            height=140,
            key="excel_input_box",
        )
        st.caption("示例：梳理2025年公司关键战略问题与战略专题清单 · 只做业绩差距分析 · 主要风险的前4项")

        if not idste_healthy:
            st.error("⚠️ iDSTE 服务器不可达，无法生成 Excel。请检查网络连接或 .env 中的 IDSTE_BASE 配置。")
            st.button("生成 Excel", type="primary", use_container_width=True, disabled=True, key="btn_excel_disabled")
            retry = st.button("重试连接 iDSTE", key="retry_idste")
            return {"request": req, "clicked": False, "retry": retry}

        clicked = st.button("生成 Excel", type="primary", use_container_width=True, key="btn_excel")

    return {"request": req, "clicked": clicked, "retry": False}


def render_excel_results(tool_call_stats, xlsx_path):
    """渲染工具调用统计 + 下载区。"""
    if tool_call_stats:
        with st.container(border=True):
            ui_theme.section_title("运行明细", "工具调用统计")
            for sn, calls in tool_call_stats.items():
                sp_n = calls.get("sp_data", 0)
                ws_n = calls.get("web_search", 0)
                status = "✅" if sp_n > 0 else "❌"
                _sn = _html.escape(sn)
                st.markdown(f"<div style='display:flex;justify-content:space-between;align-items:baseline;padding:.3rem 0;font-size:.85rem;border-bottom:1px dashed var(--sp-border-light);'><span style='color:var(--sp-text-muted);'>{status} <b>{_sn}</b></span><span style='color:var(--sp-text);font-family:var(--sp-font-mono);font-size:.8rem;'>sp_data × {sp_n} · web_search × {ws_n}</span></div>", unsafe_allow_html=True)

    if xlsx_path:
        with st.container(border=True):
            ui_theme.section_title("下载", "Excel 已就绪")
            if os.path.exists(xlsx_path):
                with open(xlsx_path, "rb") as f:
                    st.download_button(
                        os.path.basename(xlsx_path),
                        f,
                        file_name=os.path.basename(xlsx_path),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        type="primary",
                        key="dl_excel",
                    )
                st.caption(f"{os.path.getsize(xlsx_path) / 1024:.1f} KB · XLSX")
            else:
                st.warning(f"文件不存在: {xlsx_path}")


def render_excel_tab_with_sp2026(template_path, idste_healthy):
    """Tab 1 整体渲染 (自然语言 + 智能体自动填写两个区块)。

    委托 excel_controller.run 渲染现有 Excel 自然语言区块 (表单 + 处理 + 重试 + 结果,
    零行为改动), 然后追加 SP 2026 智能体自动填写子区块。
    """
    from controllers import excel_controller as ec
    ec.run(template_path, idste_healthy)
    from views import sp_change_2026_view
    sp_change_2026_view.render_sp_change_2026_form(template_path)
