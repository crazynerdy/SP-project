# -*- coding: utf-8 -*-
"""PPT Tab 的 Controller：调 agent 编排 + 管 session_state + 反馈。

业务流程与原 app.py 一致，仅做 View/Controller 分离，逻辑零改动。
"""
import os
import streamlit as st

from core.envutil import run_with_timeout
from controllers.agent import generate_pptx_from_xlsx
from models import xlsx_reader
from views import ppt_view


def run(history):
    """PPT Tab 完整控制器：渲染表单 -> 处理生成 -> 渲染结果。"""
    pv = ppt_view.render_ppt_form(history)

    if pv and pv["clicked"]:
        xlsx_path = pv["xlsx_path"]
        if not xlsx_path or not os.path.exists(xlsx_path):
            st.error("先选择一份历史 Excel，或上传一个 xlsx")
            st.stop()
            return

        try:
            with st.spinner("正在生成 PPT..."):
                xlsx_data = xlsx_reader.read_template(xlsx_path)
                if not xlsx_data["sheets"]:
                    st.error("这份 xlsx 没有任何数据 sheet")
                    st.stop()
                    return

                result = run_with_timeout(
                    lambda: generate_pptx_from_xlsx(
                        pv["request"] or "生成完整分析报告的演示文稿",
                        xlsx_path,
                        enable_images=pv["enable_images"],
                        enable_qa=pv["enable_qa"],
                        verbose=False,
                    ),
                    timeout_sec=120, label="PPT 生成",
                )

                pptx_path = result["pptx_path"]

            st.success(f"PPT 生成完毕: {os.path.basename(pptx_path)} ({len(result['slide_spec'].get('slides', []))} 页)")

            st.session_state["last_pptx_path"] = pptx_path
            st.session_state["last_slide_spec"] = result["slide_spec"]
            st.session_state["last_qa"] = result.get("qa")

        except Exception as e:
            st.error(f"{type(e).__name__}: {e}")
            with st.expander("异常详情"):
                st.exception(e)
            st.stop()
            return

    # 下载 + QA
    ppt_view.render_ppt_results(
        st.session_state.get("last_pptx_path"),
        st.session_state.get("last_slide_spec"),
        st.session_state.get("last_qa"),
    )
