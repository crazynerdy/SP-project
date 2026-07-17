# -*- coding: utf-8 -*-
"""页面骨架 View：sidebar + hero + 概览卡片。

只负责渲染，不调 agent、不写业务 session_state（导航 active_tab 除外）。
"""
import os
import streamlit as st

from views import ui_theme


def render_sidebar():
    """iDSTE 品牌区 + 功能导航 + 提示 + 底部状态。导航结果写 active_tab。"""
    with st.sidebar:
        # 品牌标识
        st.markdown("""
        <div style="margin-bottom:1.4rem;">
          <div style="font-size:1.85rem;font-weight:700;color:#fff;letter-spacing:.04em;">iDSTE</div>
          <div style="font-size:1.05rem;color:rgba(255,255,255,.75);margin-top:.25rem;">战略规划智能体</div>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        # 功能导航（radio，CSS 覆盖为列表样式）
        nav_options = ["📊 Excel表格生成", "🎯 PPT生成"]
        nav_idx = 0 if st.session_state.get("active_tab", "excel") == "excel" else 1
        nav = st.radio("功能", options=nav_options, index=nav_idx, key="nav_radio")
        st.session_state["active_tab"] = "excel" if nav == "📊 Excel表格生成" else "ppt"

        st.divider()

        st.markdown("<div style='font-size:.72rem;color:rgba(255,255,255,.5);letter-spacing:.12em;text-transform:uppercase;margin-bottom:.5rem;'>提示</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:.8rem;color:rgba(255,255,255,.55);line-height:1.55;'>历史记录仅在当前会话内存中保留，关闭页面即清空。</div>", unsafe_allow_html=True)

        # 弹性 spacer：把底部状态推到 sidebar 底部，但避免滚动条
        st.markdown("""
        <div style="height: calc(100vh - 600px); min-height: 20px;"></div>
        """, unsafe_allow_html=True)

        # 底部状态
        st.markdown("""
        <div class="sp-sidebar-bottom">
          <div style="display:flex;align-items:center;gap:.5rem;font-size:.95rem;color:rgba(255,255,255,.7);">
            <span style="width:8px;height:8px;border-radius:50%;background:#22C55E;display:inline-block;"></span>
            服务运行中
          </div>
          <div style="font-size:.85rem;color:rgba(255,255,255,.45);margin-top:.2rem;">v1.0.0</div>
        </div>
        """, unsafe_allow_html=True)


def render_hero():
    """深蓝渐变 hero 条带。"""
    ui_theme.hero(
        title="中海润战略规划智能体",
        subtitle="自然语言驱动 · iDSTE 数据取数 · Excel / PPT 输出",
        eyebrow="AI-POWERED STRATEGIC PLANNING",
        pills=["多维度全方位AI赋能数据分析", "iDSTE 数据直连", "Excel 报告导出", "PPT 演示生成"],
    )


def render_overview(sheet_names, history_count, template_path, active_tab):
    """3 个统计卡片（模板 sheet 数 / 历史报告数 / 当前模板）。"""
    stat_cols = st.columns(3)
    with stat_cols[0]:
        ui_theme.stat_card("📄", str(len(sheet_names)), "模板 Sheet 数", "blue")
    with stat_cols[1]:
        ui_theme.stat_card("📊", str(history_count), "历史报告数", "accent")
    with stat_cols[2]:
        tpl_name = os.path.basename(template_path)
        display_name = tpl_name.replace("【中海润】战略规划智能体", "")
        ext = ".pptx" if active_tab == "ppt" else ".xlsx"
        display_name = display_name.rsplit(".", 1)[0] + ext
        ui_theme.stat_card("📁", display_name, "当前模板", "orange")
