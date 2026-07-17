# -*- coding: utf-8 -*-
"""PPT Tab 的 View 层：表单渲染 + 结果渲染。只渲染，不调 agent。"""
import os
from uuid import uuid4
import streamlit as st

from views import ui_theme


def render_ppt_form(history):
    """渲染 PPT 表单，返回 {xlsx_path, request, enable_images, enable_qa, clicked}。"""
    with st.container(border=True):
        ui_theme.section_title("PPT", "基于 Excel 生成 PPT 演示文稿")

        src = st.radio(
            "Excel 数据源",
            options=["从历史记录选择", "上传 xlsx"],
            horizontal=True,
            key="ppt_src",
        )

        xlsx_path = None
        if src == "从历史记录选择":
            if not history:
                ui_theme.empty_state_card(
                    title="暂无历史记录",
                    subtitle="请先在「Excel表格生成」中生成一份 Excel 报告",
                )
                if st.button("📊 前往 Excel 生成", type="primary", use_container_width=True, key="ppt_empty_cta"):
                    st.session_state["active_tab"] = "excel"
                    st.rerun()
            else:
                options = [f"{h['ts']} - {h['request'][:30]}{'...' if len(h['request'])>30 else ''}"
                           for h in history]
                idx = st.selectbox("选择一份历史 Excel", range(len(options)),
                                   format_func=lambda i: options[i], key="ppt_history_idx")
                xlsx_path = history[idx]["xlsx_path"]
                st.caption(f"已选: `{os.path.basename(xlsx_path)}`")
        else:
            uploaded = st.file_uploader("上传 xlsx", type=["xlsx"], key="ppt_upload")
            if uploaded:
                os.makedirs("output", exist_ok=True)
                # basename 清洗防路径穿越 + uuid 防撞名
                safe_name = os.path.basename(uploaded.name)
                tmp_path = os.path.join("output", f"uploaded_{uuid4().hex[:8]}_{safe_name}")
                with open(tmp_path, "wb") as f:
                    f.write(uploaded.getvalue())
                xlsx_path = tmp_path
                st.caption(f"已上传: `{os.path.basename(tmp_path)}`")

        req = st.text_area(
            "演示重点",
            value=st.session_state.get("ppt_input", ""),
            placeholder="例：突出关键业绩差距和TOP风险",
            height=80,
            key="ppt_input_box",
            help="比如：'突出业绩差距' / '面向董事会强调风险' / '按 DSTE 阶段顺序讲'",
        )

        col1, col2 = st.columns(2)
        with col1:
            enable_images = st.checkbox("启用图片生成（Qwen-Image）", value=True, key="ppt_enable_images")
        with col2:
            enable_qa = st.checkbox("生成后做视觉 QA", value=False, key="ppt_enable_qa")

        clicked = st.button("生成 PPT", type="primary", use_container_width=True, key="btn_ppt")

    return {"xlsx_path": xlsx_path, "request": req, "enable_images": enable_images, "enable_qa": enable_qa, "clicked": clicked}


def render_ppt_results(pptx_path, slide_spec, qa_res):
    """渲染下载 + QA 报告。"""
    if not pptx_path:
        return
    with st.container(border=True):
        ui_theme.section_title("下载", "PPT 已就绪")
        if os.path.exists(pptx_path):
            with open(pptx_path, "rb") as f:
                st.download_button(
                    os.path.basename(pptx_path),
                    f,
                    file_name=os.path.basename(pptx_path),
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    use_container_width=True,
                    type="primary",
                    key="dl_ppt",
                )
            meta = [f"{os.path.getsize(pptx_path) / 1024:.1f} KB"]
            if slide_spec:
                meta.append(f"{len(slide_spec.get('slides', []))} 页")
            st.caption("  ·  ".join(meta))

            if qa_res:
                with st.expander("QA 报告"):
                    if qa_res.get("thumbs_path"):
                        st.image(qa_res["thumbs_path"], caption="缩略图网格")
                    st.json({k: v for k, v in qa_res.items() if k != "slide_images"})
                    st.caption(f"共 {len(qa_res.get('slide_images', []))} 张单页 jpg")
        else:
            st.warning(f"文件不存在: {pptx_path}")
