# -*- coding: utf-8 -*-
"""Streamlit 前端主题层（SP 战略规划智能体）。

视觉方向：iDSTE SaaS 仪表盘风（与 iDSTE MCP Server 管理后台统一）。
- 主色从 theme.json 的 ui 字段读取，确保与 iDSTE 品牌一致——单一真相源。
- 侧边栏深蓝青、主区浅灰白卡片、紫色强调、绿色成功。
- 字体优先 Noto / 思源系列，内网回退 Windows 系统字体。

只负责视觉层：token、CSS 注入、hero / stat_card / eyebrow 等 helper。
"""
import json
import os
import streamlit as st

from core.paths import resource

_THEME_JSON = resource("theme.json")


def _load_theme(path: str = _THEME_JSON) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _hex(val: str) -> str:
    return "#" + str(val).lstrip("#")


def _build_theme() -> dict:
    """每次调用都重新读取 theme.json，确保运行时修改能生效。"""
    tj = _load_theme()
    ui = tj.get("ui", {})
    c = {
        "sidebar_bg":     _hex(ui.get("sidebar_bg",     "1E3A8A")),
        "sidebar_text":   _hex(ui.get("sidebar_text",   "FFFFFF")),
        "sidebar_hover":  _hex(ui.get("sidebar_hover",  "172554")),
        "sidebar_active": _hex(ui.get("sidebar_active", "DBEAFE")),
        "sidebar_icon":   _hex(ui.get("sidebar_icon",   "93C5FD")),
        "accent":         _hex(ui.get("accent",         "7C3AED")),
        "accent_hover":   _hex(ui.get("accent_hover",  "6D28D9")),
        "accent_soft":    _hex(ui.get("accent_soft",    "EDE9FE")),
        "success":        _hex(ui.get("success",        "22C55E")),
        "success_soft":   _hex(ui.get("success_soft",   "DCFCE7")),
        "bg":             _hex(ui.get("bg",             "F8FAFC")),
        "card":           _hex(ui.get("card",           "FFFFFF")),
        "text":           _hex(ui.get("text",           "111827")),
        "text_muted":     _hex(ui.get("text_muted",     "6B7280")),
        "text_soft":      _hex(ui.get("text_soft",      "9CA3AF")),
        "border":         _hex(ui.get("border",         "E5E7EB")),
        "border_light":   _hex(ui.get("border_light",   "F3F4F6")),
    }
    f = {
        "display": '"Noto Sans SC", "Source Han Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif',
        "body":    '"Noto Sans SC", "Source Han Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif',
        "mono":    '"JetBrains Mono", "Cascadia Code", Consolas, "Courier New", monospace',
    }
    r = {"sm": "6px", "md": "10px", "lg": "12px", "xl": "16px"}
    s = {
        "card":   "0 1px 3px rgba(0,0,0,.06), 0 1px 2px rgba(0,0,0,.04)",
        "card_h": "0 4px 6px rgba(0,0,0,.08), 0 2px 4px rgba(0,0,0,.04)",
        "dropdown":"0 10px 15px rgba(0,0,0,.08), 0 4px 6px rgba(0,0,0,.04)",
    }
    return {"color": c, "font": f, "radius": r, "shadow": s}


def _root_vars(theme: dict) -> str:
    c, f, r, s = theme["color"], theme["font"], theme["radius"], theme["shadow"]
    return f"""
:root {{
  --sp-sidebar-bg: {c['sidebar_bg']};
  --sp-sidebar-text: {c['sidebar_text']};
  --sp-sidebar-hover: {c['sidebar_hover']};
  --sp-sidebar-active: {c['sidebar_active']};
  --sp-sidebar-icon: {c['sidebar_icon']};
  --sp-accent: {c['accent']};
  --sp-accent-hover: {c['accent_hover']};
  --sp-accent-soft: {c['accent_soft']};
  --sp-success: {c['success']};
  --sp-success-soft: {c['success_soft']};
  --sp-bg: {c['bg']};
  --sp-card: {c['card']};
  --sp-text: {c['text']};
  --sp-text-muted: {c['text_muted']};
  --sp-text-soft: {c['text_soft']};
  --sp-border: {c['border']};
  --sp-border-light: {c['border_light']};
  --sp-font-display: {f['display']};
  --sp-font-body: {f['body']};
  --sp-font-mono: {f['mono']};
  --sp-r-sm: {r['sm']};
  --sp-r-md: {r['md']};
  --sp-r-lg: {r['lg']};
  --sp-r-xl: {r['xl']};
  --sp-sh-card: {s['card']};
  --sp-sh-card-h: {s['card_h']};
  --sp-sh-dropdown: {s['dropdown']};
}}
"""


_RULES = """
/* ===== 全局基底 ===== */
html, body, [class*="css"] { font-family: var(--sp-font-body); }
.stApp, [data-testid="stAppViewContainer"], [data-testid="stAppViewBlockContainer"] {
  background: var(--sp-bg);
  color: var(--sp-text);
}
#root, .stApp > div { background: transparent; }
p { color: var(--sp-text); line-height: 1.6; }

/* 主内容区顶部增加呼吸感 */
[data-testid="stAppViewBlockContainer"] {
  padding-top: 0 !important;
}

/* 隐藏默认顶栏菜单 / 页脚。
   注意：不能藏 sidebar 折叠按钮（stBaseButton-headerNoPadding），
   否则侧边栏一旦收起（窄屏自动收起 / 浏览器记住状态）就再也展开不了。 */
header[data-testid="stHeader"] { background: transparent; }
#MainMenu, footer[data-testid="stFooter"], [data-testid="stToolbar"],
.stDeployButton, [data-testid="stLogo"] { display: none !important; }

a { color: var(--sp-accent); text-decoration: none; }
a:hover { text-decoration: underline; text-underline-offset: 2px; }

/* ===== 排版 ===== */
h1, h2, h3, h4 { font-family: var(--sp-font-display); color: var(--sp-text); letter-spacing: -.01em; }
[data-testid="stHeading"] h1 { font-size: 1.5rem; font-weight: 700; }
[data-testid="stHeading"] h2 { font-size: 1.2rem; font-weight: 600; }
[data-testid="stHeading"] h3 { font-size: 1.05rem; font-weight: 600; }

[data-testid="stCaptionContainer"], .stCaption {
  color: var(--sp-text-muted);
  font-size: .82rem;
  line-height: 1.55;
}
code, pre { font-family: var(--sp-font-mono); }

hr, [data-testid="stDivider"] {
  border: none !important;
  border-top: 1px solid var(--sp-border) !important;
  margin: 1rem 0 !important;
}

/* ===== Hero 条带（深蓝渐变） ===== */
.sp-hero {
  background: linear-gradient(135deg, #1E3A8A 0%, #2563EB 50%, #3B82F6 100%);
  border-radius: var(--sp-r-xl);
  padding: 1.8rem 2.4rem 1.8rem;
  margin-bottom: 0.5rem;
  box-shadow: 0 4px 20px rgba(30,58,138,.25);
  position: relative; overflow: hidden;
}
/* hero 装饰性网格背景 + 右侧大字 */
.sp-hero::before {
  content: "";
  position: absolute; inset: 0;
  background-image:
    linear-gradient(rgba(255,255,255,.06) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,.06) 1px, transparent 1px);
  background-size: 24px 24px;
  pointer-events: none;
}
.sp-hero::after {
  content: "SP";
  position: absolute; right: 1.5rem; top: 50%;
  transform: translateY(-50%);
  font-family: var(--sp-font-mono);
  font-size: 6rem; font-weight: 800;
  color: rgba(255,255,255,.06);
  letter-spacing: -.05em;
  pointer-events: none; user-select: none;
}
.sp-hero__eyebrow {
  font-family: var(--sp-font-mono);
  font-size: .72rem; font-weight: 500;
  color: rgba(255,255,255,.6);
  letter-spacing: .2em; text-transform: uppercase;
  margin-bottom: .45rem;
}
.sp-hero__title {
  font-family: var(--sp-font-display);
  font-size: 2.1rem; font-weight: 700; color: #fff;
  letter-spacing: -.01em; line-height: 1.15;
  margin-bottom: .45rem;
}
.sp-hero__sub {
  font-size: .95rem; color: rgba(255,255,255,.75);
  line-height: 1.5; margin-bottom: 0.7rem;
}
.sp-hero__pills {
  display: flex; flex-wrap: wrap; gap: .5rem;
}
.sp-hero__pill {
  display: inline-flex; align-items: center; gap: .4rem;
  padding: .35rem .9rem;
  border-radius: 999px;
  background: rgba(255,255,255,.15);
  border: 1px solid rgba(255,255,255,.18);
  font-size: .78rem; color: rgba(255,255,255,.9);
  font-weight: 500;
  backdrop-filter: blur(4px);
}
.sp-hero__pill::before {
  content: "";
  width: 5px; height: 5px; border-radius: 50%;
  background: rgba(255,255,255,.7);
  display: inline-block;
}

/* ===== eyebrow / section 标题 ===== */
.sp-eyebrow {
  font-family: var(--sp-font-mono);
  font-size: .68rem; font-weight: 500;
  color: var(--sp-accent);
  letter-spacing: .14em; text-transform: uppercase;
  margin-bottom: .4rem;
}
.sp-sec-title {
  font-family: var(--sp-font-display);
  font-size: 1.1rem; font-weight: 600; color: var(--sp-text);
  margin: 0 0 .9rem;
}

/* ===== 统计卡片 ===== */
.sp-stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 0.5rem; }
.sp-stat-card {
  background: var(--sp-card);
  border: 1px solid var(--sp-border-light);
  border-radius: var(--sp-r-lg);
  padding: 1rem 1.1rem;
  box-shadow: var(--sp-sh-card);
  display: flex; align-items: center; gap: .9rem;
  transition: box-shadow .15s ease;
}
.sp-stat-card:hover { box-shadow: var(--sp-sh-card-h); }
.sp-stat-card__icon {
  width: 40px; height: 40px; border-radius: var(--sp-r-md);
  display: flex; align-items: center; justify-content: center;
  font-size: 1.1rem; flex: none;
}
.sp-stat-card__icon--accent { background: var(--sp-accent-soft); color: var(--sp-accent); }
.sp-stat-card__icon--success { background: var(--sp-success-soft); color: var(--sp-success); }
.sp-stat-card__icon--blue { background: #DBEAFE; color: #2563EB; }
.sp-stat-card__icon--orange { background: #FEF3C7; color: #D97706; }
.sp-stat-card__num {
  font-family: var(--sp-font-mono);
  font-size: 1.35rem; font-weight: 700; color: var(--sp-text);
  line-height: 1.1;
}
.sp-stat-card__label {
  font-size: .78rem; color: var(--sp-text-muted);
  margin-top: .15rem;
}

/* ===== 工作卡片（border container 覆盖） ===== */
[data-testid="stVerticalBlockBorderWrapper"] {
  border: 1px solid var(--sp-border) !important;
  border-radius: var(--sp-r-lg) !important;
  background: var(--sp-card) !important;
  box-shadow: var(--sp-sh-card) !important;
  padding: 1.4rem 1.5rem !important;
}

/* ===== Tab ===== */
[data-testid="stTabs"] [role="tablist"] {
  gap: .1rem;
  border-bottom: 1px solid var(--sp-border);
}
[data-testid="stTabs"] button[data-baseweb="tab"] {
  font-family: var(--sp-font-body);
  font-size: .88rem; font-weight: 500;
  color: var(--sp-text-muted);
  background: transparent;
  border: none;
  border-radius: 0;
  padding: .5rem .9rem;
  border-bottom: 2px solid transparent;
}
[data-testid="stTabs"] button[data-baseweb="tab"]:hover {
  color: var(--sp-text);
  background: var(--sp-accent-soft);
}
[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {
  color: var(--sp-accent);
  font-weight: 600;
  border-bottom: 2px solid var(--sp-accent);
}
[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
  background-color: var(--sp-accent) !important; height: 2px !important;
}
[data-testid="stTabs"] [data-baseweb="tab-border"] { display: none !important; }

/* ===== 按钮 ===== */
section[data-testid="stButton"] button,
.stButton > button {
  font-family: var(--sp-font-body);
  font-size: .88rem; font-weight: 500;
  border-radius: var(--sp-r-md) !important;
  padding: .48rem 1.1rem !important;
  transition: all .12s ease;
  border: 1px solid var(--sp-border) !important;
  background: var(--sp-card) !important;
  color: var(--sp-text) !important;
}
section[data-testid="stButton"] button:hover,
.stButton > button:hover {
  background: var(--sp-bg) !important;
  border-color: var(--sp-accent) !important;
}
/* primary = 紫底白字 */
section[data-testid="stButton"] button[kind="primary"],
.stButton > button[kind="primary"] {
  background: var(--sp-accent) !important;
  color: #fff !important;
  border: 1px solid var(--sp-accent) !important;
  font-weight: 600;
}
section[data-testid="stButton"] button[kind="primary"]:hover,
.stButton > button[kind="primary"]:hover {
  background: var(--sp-accent-hover) !important;
  border-color: var(--sp-accent-hover) !important;
  box-shadow: 0 2px 8px rgba(124,58,237,.25) !important;
}

/* ===== 输入 ===== */
[data-testid="stTextArea"] textarea,
[data-testid="stTextInput"] input {
  font-family: var(--sp-font-body) !important;
  font-size: .9rem !important;
  color: var(--sp-text) !important;
  background: var(--sp-card) !important;
  border: 1px solid var(--sp-border) !important;
  border-radius: var(--sp-r-md) !important;
}
[data-testid="stTextArea"] textarea:focus,
[data-testid="stTextInput"] input:focus {
  border-color: var(--sp-accent) !important;
  box-shadow: 0 0 0 3px rgba(124,58,237,.1) !important;
}
[data-baseweb="select"] > div,
[data-baseweb="select"] [class*="input"] {
  border-radius: var(--sp-r-md) !important;
  background: var(--sp-card) !important;
}
[data-baseweb="select"] [class*="input"] input {
  background: transparent !important;
}

/* radio / checkbox 已随 config.toml primaryColor 自动变色 */

/* ===== 进度条 ===== */
[data-testid="stProgress"] div[role="progressbar"] {
  background: var(--sp-border-light) !important;
  border-radius: 999px !important;
  height: 6px !important;
}
[data-testid="stProgress"] div[role="progressbar"] > div {
  background: linear-gradient(90deg, var(--sp-accent), #A78BFA) !important;
  border-radius: 999px !important;
}

/* ===== expander ===== */
[data-testid="stExpander"] {
  border: 1px solid var(--sp-border) !important;
  border-radius: var(--sp-r-lg) !important;
  background: var(--sp-card) !important;
  overflow: hidden;
}
[data-testid="stExpander"] summary span,
[data-testid="stExpander"] details > summary {
  font-family: var(--sp-font-body) !important;
  font-weight: 600 !important;
  color: var(--sp-text) !important;
}

/* ===== file uploader ===== */
[data-testid="stFileUploaderDropzone"] {
  border: 1px dashed var(--sp-border) !important;
  border-radius: var(--sp-r-lg) !important;
  background: var(--sp-card) !important;
}
[data-testid="stFileUploaderDropzone"]:hover {
  border-color: var(--sp-accent) !important;
  background: var(--sp-accent-soft) !important;
}

/* ===== alert ===== */
[data-testid="stAlert"], .stAlert {
  border-radius: var(--sp-r-md) !important;
  border-left-width: 3px !important;
}

/* ===== json ===== */
[data-testid="stJson"] {
  border: 1px solid var(--sp-border) !important;
  border-radius: var(--sp-r-md) !important;
  font-family: var(--sp-font-mono) !important;
  font-size: .78rem !important;
}

/* ===== 强制 sidebar 永久展开（不可折叠） ===== */
section[data-testid="stSidebar"] {
  position: fixed !important;
  left: 0 !important; top: 0 !important;
  width: 300px !important;
  min-width: 300px !important;
  max-width: 300px !important;
  height: 100vh !important;
  transform: none !important;
  margin-left: 0 !important;
  display: block !important;
  visibility: visible !important;
  opacity: 1 !important;
  overflow-y: auto !important;
  background: var(--sp-sidebar-bg) !important;
}
/* 主内容区给 sidebar 让出固定空间 */
[data-testid="stAppViewContainer"] {
  margin-left: 300px !important;
}
/* 彻底隐藏所有折叠/展开按钮（防止任何途径触发收起） */
[data-testid="stBaseButton-headerNoPadding"],
[data-testid="stSidebarCollapseButton"],
button[kind="header"],
header[data-testid="stHeader"] button {
  display: none !important;
}

/* ===== sidebar radio 导航 ===== */
section[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] {
  display: flex; flex-direction: column; gap: .3rem;
}
section[data-testid="stSidebar"] [data-testid="stRadio"] label {
  display: flex; align-items: center;
  padding: .6rem .8rem; border-radius: 6px;
  font-size: 1rem; color: rgba(255,255,255,.75);
  cursor: pointer; margin: 0; line-height: 1.4;
  transition: background .12s ease;
}
section[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
  background: rgba(255,255,255,.08); color: #fff;
}
/* 隐藏 radio circle */
section[data-testid="stSidebar"] [data-testid="stRadio"] input[type="radio"] {
  display: none !important;
}
/* 选中态 */
section[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
  background: rgba(255,255,255,.15); color: #fff; font-weight: 500;
}
/* radio 标题 */
section[data-testid="stSidebar"] [data-testid="stRadio"] > div > div:first-child {
  font-size: .85rem; color: rgba(255,255,255,.5);
  letter-spacing: .12em; text-transform: uppercase;
  margin-bottom: .5rem;
}

/* ===== sidebar（深蓝色） ===== */
section[data-testid="stSidebar"],
[data-testid="stSidebarViewport"] {
  background: var(--sp-sidebar-bg) !important;
}
section[data-testid="stSidebar"] {
  border-right: none !important;
}
.sp-sidebar-bottom {
  padding-top: 1.2rem !important;
  border-top: 1px solid rgba(255,255,255,.12) !important;
}
/* sidebar 文字变白（只对已知安全的元素，避免影响未来组件） */
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] h4,
section[data-testid="stSidebar"] .stCaption,
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
  color: var(--sp-sidebar-text) !important;
}
/* sidebar 分割线变淡 */
section[data-testid="stSidebar"] hr,
section[data-testid="stSidebar"] [data-testid="stDivider"] {
  border-top-color: rgba(255,255,255,.15) !important;
}
/* sidebar 按钮 */
section[data-testid="stSidebar"] section[data-testid="stButton"] button,
section[data-testid="stSidebar"] .stButton > button {
  background: rgba(255,255,255,.1) !important;
  color: var(--sp-sidebar-text) !important;
  border-color: rgba(255,255,255,.2) !important;
}
section[data-testid="stSidebar"] section[data-testid="stButton"] button:hover,
section[data-testid="stSidebar"] .stButton > button:hover {
  background: rgba(255,255,255,.18) !important;
}

/* ===== 可访问性 ===== */
*:focus-visible {
  outline: 2px solid var(--sp-accent) !important;
  outline-offset: 2px !important;
}
@media (prefers-reduced-motion: reduce) {
  * { transition: none !important; animation: none !important; }
}

/* ===== 空状态卡片 ===== */
.sp-empty-state {
  text-align: center;
  padding: 2.2rem 1.5rem 1.8rem;
  background: linear-gradient(135deg, var(--sp-accent-soft) 0%, var(--sp-card) 60%);
  border-radius: var(--sp-r-lg);
  border: 1px solid var(--sp-border);
}
.sp-empty-state__icon {
  display: inline-flex; align-items: center; justify-content: center;
  width: 56px; height: 56px;
  border-radius: 50%;
  background: var(--sp-card);
  border: 1.5px solid var(--sp-accent);
  margin-bottom: 1rem;
}
.sp-empty-state__icon svg { width: 26px; height: 26px; }
.sp-empty-state__title {
  font-family: var(--sp-font-display);
  font-size: 1.1rem; font-weight: 600;
  color: var(--sp-text);
  margin-bottom: .45rem;
  line-height: 1.35;
}
.sp-empty-state__sub {
  font-size: .88rem; color: var(--sp-text-muted);
  line-height: 1.55;
  max-width: 320px; margin: 0 auto;
}

/* ===== 响应式 ===== */
@media (max-width: 720px) {
  .sp-stat-grid { grid-template-columns: 1fr 1fr; }
  .sp-topbar { flex-direction: column; align-items: flex-start; gap: .4rem; }
}
"""


def _build_css() -> str:
    theme = _build_theme()
    return _root_vars(theme) + "\n" + _RULES


def inject():
    st.markdown(f"<style>{_build_css()}</style>", unsafe_allow_html=True)


def hero(title: str = "中海润战略规划智能体",
         subtitle: str = "自然语言驱动 · iDSTE 数据取数 · Excel / PPT 输出",
         eyebrow: str = "AI-POWERED STRATEGIC PLANNING",
         pills=None):
    """深蓝渐变 hero 条带（参考模板风格）。"""
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
    """统计卡片（模板图中的 KPI 卡片）。tone: accent/success/blue/orange。"""
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
    """空状态卡片：居中图标 + 主副文案。按钮由调用方渲染。"""
    # 文档轮廓 SVG 图标（accent 色描边）
    svg = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>"""
    st.markdown(f"""
<div class="sp-empty-state">
  <div class="sp-empty-state__icon">{svg}</div>
  <div class="sp-empty-state__title">{title}</div>
  <div class="sp-empty-state__sub">{subtitle}</div>
</div>
""", unsafe_allow_html=True)
