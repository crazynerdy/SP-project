# -*- coding: utf-8 -*-
"""Theme token 加载与构建。"""
import json
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
        "border":         _hex(ui.get("border",         "E2E8F0")),
        "border_light":   _hex(ui.get("border_light",   "F1F5F9")),
    }
    f = {
        "display": ui.get("font_display", "'Noto Sans SC', 'Microsoft YaHei', sans-serif"),
        "body":    ui.get("font_body",    "'Noto Sans SC', 'Microsoft YaHei', sans-serif"),
        "mono":    ui.get("font_mono",    "'SF Mono', 'Fira Code', 'Consolas', monospace"),
    }
    r = {
        "sm": ui.get("radius_sm", "6px"),
        "md": ui.get("radius_md", "10px"),
        "lg": ui.get("radius_lg", "14px"),
        "xl": ui.get("radius_xl", "18px"),
    }
    s = {
        "card":      ui.get("shadow_card",      "0 1px 3px rgba(0,0,0,.06)"),
        "card_h":    ui.get("shadow_card_h",    "0 4px 12px rgba(0,0,0,.08)"),
        "dropdown":  ui.get("shadow_dropdown",  "0 8px 24px rgba(0,0,0,.10)"),
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
