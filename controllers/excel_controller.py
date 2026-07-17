# -*- coding: utf-8 -*-
"""Excel Tab 的 Controller：调 WorkflowEngine + 管 session_state + 反馈。

新增: 自然语言意图识别 → 匹配 sheet → DAG workflow engine。
保留: 旧 Excel 流程逻辑（backward compat）。
"""
import os
from datetime import datetime
import streamlit as st

from core.envutil import run_with_timeout
from models import idste, xlsx_exporter
from views import excel_view


def run(template_path, idste_healthy):
    """Excel Tab 完整控制器：渲染表单 -> 处理生成/重试 -> 渲染结果。"""
    ev = excel_view.render_excel_form(idste_healthy)

    if ev:
        if ev["clicked"]:
            req = ev["request"]
            if not req.strip():
                st.warning("先分析需求再生成")
                st.stop()

            try:
                with st.spinner("正在生成 Excel..."):
                    # 意图识别：调 LLM 识别用户想填哪些 sheet
                    from models import llm, prompts
                    sys_prompt = prompts.build_intent_recognition_prompt()
                    resp = llm.chat_with_fallback(
                        [
                            {"role": "system", "content": sys_prompt},
                            {"role": "user", "content": req},
                        ],
                        max_tokens=2000, final_max_tokens=4096,
                        enable_thinking=False,
                    )
                    text = resp["choices"][0]["message"].get("content") or ""
                    from core.json_utils import parse_json
                    intent = parse_json(text)
                    intent.setdefault("flow", "generate_excel")
                    intent.setdefault("sheets_to_fill", [])

                    if not intent.get("sheets_to_fill"):
                        st.warning(f"意图识别没选任何 sheet。理由: {intent.get('reasoning', '')}")
                        st.json(intent)
                        st.stop()

                    sheets = [s.strip() for s in intent["sheets_to_fill"]]

                    # 初始化 context + engine
                    from core.strategic_context import StrategyContextBuilder
                    from core.workflow_engine import WorkflowEngine
                    from config import load_tasks
                    from agents import AGENT_REGISTRY

                    builder = StrategyContextBuilder(dim_info="c", year="2025")
                    context = builder.build(target_tables=[])

                    engine = WorkflowEngine(
                        tasks=load_tasks(),
                        context=context,
                        agents=AGENT_REGISTRY,
                        template_path=template_path,
                        output_dir="output",
                        verbose=False,
                    )
                    result = engine.run(sheet_ids=sheets)

                    out_path = result.get("output_xlsx_path")
                    if not out_path or not os.path.exists(out_path):
                        st.error("没取到数据，换个说法重试，或调整需求范围")
                        st.stop()

                    with open(out_path, "rb") as f:
                        xlsx_bytes = f.read()

                st.success(f"Excel 生成完毕（{len(result.get('filled_sheets', []))} 张 sheet）")

                st.session_state["history"].insert(0, {
                    "xlsx_path": out_path,
                    "intent": intent,
                    "ts": os.path.basename(out_path).split("_")[0],
                    "request": req,
                })
                st.session_state["_intent"] = intent
                st.session_state["_xlsx_bytes"] = xlsx_bytes
                st.session_state["_request"] = req
                st.session_state["_tool_call_stats"] = result.get("tool_call_stats", {})

            except Exception as e:
                st.error(f"{type(e).__name__}: {e}")
                with st.expander("异常详情"):
                    st.exception(e)
                st.stop()

        if ev["retry"]:
            st.session_state["idste_healthy"] = idste.health_check()
            st.rerun()

    # 工具调用统计 + 下载
    excel_view.render_excel_results(
        st.session_state.get("_tool_call_stats"),
        st.session_state.get("_xlsx_bytes"),
    )