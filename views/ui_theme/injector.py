# -*- coding: utf-8 -*-
"""CSS 注入器。"""
import os
import streamlit as st

from views.ui_theme.tokens import _build_theme, _root_vars

_CSS_PATH = os.path.join(os.path.dirname(__file__), "styles.css")


def _load_rules() -> str:
    try:
        with open(_CSS_PATH, encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def _build_css() -> str:
    theme = _build_theme()
    return _root_vars(theme) + "\n" + _load_rules()


def inject():
    st.markdown(f"<style>{_build_css()}</style>", unsafe_allow_html=True)
