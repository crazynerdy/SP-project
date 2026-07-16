# agents/router_agent.py
# -*- coding: utf-8 -*-
"""Router Agent - 意图识别 + Sheet 分发 + Agent 调度计划。

替代 controllers/agent.py 的 intent_recognize() 的 LLM 调用逻辑。
"""
from context.strategy_context_builder import StrategyContext


def route(user_input: str, context: StrategyContext, llm_client=None,
          prompts_module=None) -> dict:
    """识别用户意图，返回工作流计划。

    Args:
        user_input: 自然语言需求
        context: StrategyContext（含 available_tables）
        llm_client: DI 注入（None 时用默认）
        prompts_module: DI 注入（None 时用默认）

    Returns:
        {
            "flow": "generate_excel" | "generate_ppt",
            "year": "2025",
            "dim_info": "c",
            "sheets_to_fill": [...],
            "intent_label": "...",
            "reasoning": "...",
            "agent_plan": [{"sheet": "...", "agents": [...]}],
        }
    """
    from models import llm as _llm
    from models import prompts as _prompts
    from workflow.sheet_dispatcher import dispatch as _dispatch

    llm_client = llm_client or _llm
    prompts_module = prompts_module or _prompts

    # 1) 调 LLM 做意图识别（与现有 intent_recognize 逻辑一致）
    system_prompt = prompts_module.build_intent_recognition_prompt()
    resp = llm_client.chat_with_fallback(
        [{"role": "system", "content": system_prompt},
         {"role": "user", "content": user_input}],
        max_tokens=2000, final_max_tokens=4096, verbose=False,
        enable_thinking=False,
    )
    text = resp["choices"][0]["message"].get("content") or ""

    # 2) 解析 JSON（复用 agent.py 的 _parse_json）
    from controllers.agent import _parse_json
    intent = _parse_json(text)

    # 兜底
    intent.setdefault("flow", "generate_excel")
    intent.setdefault( "year", context.year)
    intent.setdefault("dim_info", context.dim_info)
    intent.setdefault("sheets_to_fill", [])
    intent.setdefault("reasoning", "")
    if not intent.get("intent_label"):
        from datetime import datetime
        base = "analysis"
        s = user_input.lower()
        if "风险" in s:
            base = "risk"
        elif "完成度" in s or "业绩" in s:
            base = "completion"
        ts = datetime.now().strftime("%H%M%S")
        intent["intent_label"] = f"{base}_{ts}"

    # 3) 生成 agent_plan（新增：为 Workflow 提供调度依据）
    agent_plan = []
    for sheet in intent.get("sheets_to_fill", []):
        agents = _dispatch(sheet)
        agent_plan.append({"sheet": sheet, "agents": agents})
    intent["agent_plan"] = agent_plan

    return intent
