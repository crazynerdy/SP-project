# -*- coding: utf-8 -*-
"""UI 组件。"""
import streamlit as st


def hero(title: str = "中海润战略规划智能体",
         subtitle: str = "自然语言驱动 · iDSTE 数据取数 · Excel / PPT 输出",
         eyebrow: str = "AI-POWERED STRATEGIC PLANNING",
         pills=None):
    """深蓝渐变 hero 条带。"""
    pills = pills or []
    pill_html = "".join(
        f'<span class="sp-hero__pill">{p}</span>' for p in pills
    )
    st.markdown(f"""
<div class="sp-hero">
  <div class="sp-hero__eyebrow">{eyebrow}</div>
  <div class="sp-hero__title">{title}</div>
  <div class="sp-hero__sub">{subtitle}</div>
  <div class="sp-hero__pills">{pill_html}</div>
</div>
""", unsafe_allow_html=True)


def eyebrow(text: str):
    st.markdown(f'<div class="sp-eyebrow">{text}</div>', unsafe_allow_html=True)


def section_title(eyebrow_text: str, title: str):
    st.markdown(f"""
<div class="sp-eyebrow">{eyebrow_text}</div>
<div class="sp-sec-title">{title}</div>
""", unsafe_allow_html=True)


def stat_card(icon: str, num: str, label: str, tone: str = "accent"):
    """统计卡片。tone: accent/success/blue/orange。"""
    st.markdown(f"""
<div class="sp-stat-card">
  <div class="sp-stat-card__icon sp-stat-card__icon--{tone}">{icon}</div>
  <div>
    <div class="sp-stat-card__num">{num}</div>
    <div class="sp-stat-card__label">{label}</div>
  </div>
</div>
""", unsafe_allow_html=True)


def empty_state_card(title: str, subtitle: str):
    """空状态卡片。"""
    svg = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>"""
    st.markdown(f"""
<div class="sp-empty-state">
  <div class="sp-empty-state__icon">{svg}</div>
  <div class="sp-empty-state__title">{title}</div>
  <div class="sp-empty-state__sub">{subtitle}</div>
</div>
""", unsafe_allow_html=True)
