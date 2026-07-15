# -*- coding: utf-8 -*-
"""Streamlit Web UI 入口（瘦）：page config + 主题 + 骨架 + 路由。

View 层在 views/，Controller 层在 controllers/，业务编排见 controllers/agent.py。
视觉层由 views/ui_theme.py 负责；本文件只做页面骨架与 Tab 路由。
"""
import os
import sys
import streamlit as st

from views import ui_theme, layout
# 开发期热重载 ui_theme.py（生产关掉，避免每次 rerun 重载开销）
if os.environ.get("DEV", "false").lower() == "true" and "views.ui_theme" in sys.modules:
    import importlib
    importlib.reload(sys.modules["views.ui_theme"])

from core.envutil import env
from models import idste, xlsx_reader
from controllers import excel_controller, ppt_controller


# ---------- 页面配置 ----------
st.set_page_config(
    page_title="SP 战略规划智能体",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 注入 iDSTE 仪表盘主题
ui_theme.inject()


# ---------- 模板加载 ----------
TEMPLATE_PATH = env("TEMPLATE_XLSX_PATH")
SHEET_NAMES = []
try:
    SHEET_NAMES = [s["sheet_name"] for s in xlsx_reader.extract_schema(TEMPLATE_PATH)]
except Exception as e:
    st.error(f"模板加载失败: {TEMPLATE_PATH}\n{e}")


# ---------- 骨架：sidebar + hero ----------
layout.render_sidebar()
layout.render_hero()


# ---------- session_state 初始化 ----------
if "history" not in st.session_state:
    st.session_state["history"] = []
if "last_intent" not in st.session_state:
    st.session_state["last_intent"] = None
if "last_xlsx_path" not in st.session_state:
    st.session_state["last_xlsx_path"] = None
if "last_pptx_path" not in st.session_state:
    st.session_state["last_pptx_path"] = None
if "last_slide_spec" not in st.session_state:
    st.session_state["last_slide_spec"] = None
if "last_qa" not in st.session_state:
    st.session_state["last_qa"] = None
if "last_tool_call_stats" not in st.session_state:
    st.session_state["last_tool_call_stats"] = None
if "active_tab" not in st.session_state:
    st.session_state["active_tab"] = "excel"
if "idste_healthy" not in st.session_state:
    st.session_state["idste_healthy"] = idste.health_check()


# ---------- 系统概览 ----------
active_tab = st.session_state.get("active_tab", "excel")
layout.render_overview(SHEET_NAMES, len(st.session_state["history"]), TEMPLATE_PATH, active_tab)


# ---------- 路由 ----------
if active_tab == "excel":
    from views import excel_view
    excel_view.render_excel_tab_with_sp2026(TEMPLATE_PATH, st.session_state["idste_healthy"])
elif active_tab == "ppt":
    ppt_controller.run(st.session_state["history"])
