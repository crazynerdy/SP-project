# -*- coding: utf-8 -*-
"""LLM 客户端（OpenAI 兼容）+ 工具调用 Agent 循环。

使用环境变量 LLM_BASE_URL / LLM_API_KEY / LLM_MODEL。
已探测 Qwen3.5 支持 native function-calling（标准 OpenAI tool_calls 格式）。

注意：build_sp_tools_schema 已迁移到 idste.py（schema 描述的是 iDSTE 工具），
这里仅保留一个 deprecation 兼容垫片。
"""
import json
import warnings
import requests
from core.envutil import require

_CFG = None  # 懒加载配置缓存


def _get_config():
    """懒加载 LLM 配置。首次从 env 读，之后缓存；可被 configure() 覆盖。"""
    global _CFG
    if _CFG is None:
        _CFG = {
            "base_url": require("LLM_BASE_URL").rstrip("/"),
            "api_key": require("LLM_API_KEY"),
            "model": require("LLM_MODEL"),
            "timeout": 120,
        }
    return _CFG


def configure(base_url=None, api_key=None, model=None, timeout=None):
    """依赖注入入口：显式覆盖配置（多模型/测试用）。"""
    global _CFG
    _CFG = {
        "base_url": (base_url or require("LLM_BASE_URL")).rstrip("/"),
        "api_key": api_key or require("LLM_API_KEY"),
        "model": model or require("LLM_MODEL"),
        "timeout": timeout or 120,
    }


def chat(messages, tools=None, temperature=0.3, max_tokens=4096, enable_thinking=None):
    """单次调用 /chat/completions，返回原始响应 JSON dict。

    enable_thinking: None=模型默认；True/False 通过 chat_template_kwargs 传给 vLLM。
        Qwen3.5_122B_A10B 是 reasoning 模型，关 thinking（False）可省 reasoning token、
        大幅提速（实测 24.7s->0.3s）；简单任务（意图识别、工具调用决策）关，复杂任务开。
    """
    cfg = _get_config()
    body = {
        "model": cfg["model"],
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if tools:
        body["tools"] = [{"type": "function", "function": t} for t in tools]
    if enable_thinking is not None:
        body["chat_template_kwargs"] = {"enable_thinking": enable_thinking}
    last_err = None
    for _attempt in range(2):  # 最多 2 次，第 2 次退避 1s
        try:
            r = requests.post(
                f"{cfg['base_url']}/chat/completions",
                headers={"Authorization": f"Bearer {cfg['api_key']}", "Content-Type": "application/json"},
                json=body,
                timeout=cfg["timeout"],
            )
            if r.status_code == 200:
                break
            if r.status_code >= 500 and _attempt == 0:
                import time as _t
                _t.sleep(1)
                continue
            raise RuntimeError(f"LLM 调用失败({r.status_code}): {r.text[:500]}")
        except requests.RequestException as e:
            last_err = e
            if _attempt == 0:
                import time as _t
                _t.sleep(1)
                continue
            raise RuntimeError(f"LLM 调用网络失败: {e}") from e
    else:
        raise RuntimeError(f"LLM 调用重试失败: {last_err}")
    j = r.json()
    if "choices" not in j:
        raise RuntimeError(f"LLM 响应无 choices: {j}")
    return j


def _msg_text(resp):
    return resp["choices"][0]["message"].get("content") or ""


def _msg_tool_calls(resp):
    return resp["choices"][0]["message"].get("tool_calls") or []


def _trim_tool_messages(messages, max_chars=60000):
    """总量上限：当 messages 字符总数超阈值，淘汰最早的 tool 结果。

    保留 system + user + assistant(含 tool_calls) 骨架，仅截断/丢弃最早
    的 tool 消息内容，避免长 agent 循环爆 context。最小可行：逐条淘汰直到达标。
    """
    def _total():
        return sum(len(m.get("content") or "") for m in messages)
    while _total() > max_chars and len(messages) > 3:
        for i, m in enumerate(messages):
            if m.get("role") == "tool":
                # 先尝试清空内容保留占位（维持 tool_call_id 配对）
                if len(m.get("content") or "") > 200:
                    m["content"] = "(已淘汰以节省上下文)"
                    break
                else:
                    # 内容已很短仍超限，直接删该 tool + 其前导 assistant
                    del messages[i]
                    if i > 0 and messages[i - 1].get("role") == "assistant":
                        del messages[i - 1]
                    break
        else:
            break  # 没有可淘汰的 tool 了


def chat_with_fallback(messages, max_tokens=4096, final_max_tokens=None,
                       temperature=0.3, tools=None, verbose=False, enable_thinking=None):
    """调 chat，若 content 空/finish_reason=length 且 final_max_tokens 更大则重试一次。

    reasoning 模型（Qwen3.5_122B_A10B）思考链常吃光小 max_tokens 导致 content 为空。
    用于"最终回答"型调用（intent 识别、slide-spec 生成等）。返回最终 resp。
    enable_thinking 透传给 chat（两档重试用同一开关）。
    """
    final_max_tokens = final_max_tokens or max_tokens
    resp = chat(messages, tools=tools, temperature=temperature, max_tokens=max_tokens, enable_thinking=enable_thinking)
    content = _msg_text(resp)
    finish = resp["choices"][0].get("finish_reason")
    if (not content or finish == "length") and final_max_tokens > max_tokens:
        if verbose:
            print(f"[llm] content空/finish={finish}，用 max_tokens={final_max_tokens} 重试")
        resp = chat(messages, tools=tools, temperature=temperature, max_tokens=final_max_tokens, enable_thinking=enable_thinking)
    return resp


def run_agent_loop(system_prompt, user_msg, tool_map, tools_schema,
                   max_turns=12, verbose=True, temperature=0.3, max_tokens=4096,
                   final_max_tokens=None, enable_thinking=None, final_enable_thinking=None):
    """Agent 工具调用循环（native function-calling）。

    Args:
        system_prompt: 系统提示。
        user_msg: 用户原始需求。
        tool_map: {tool_name: callable}，callable 接 **kwargs。
        tools_schema: OpenAI 风格 tools 列表（function 定义）。
        max_turns: 最大轮次。
        verbose: 打印过程。
        max_tokens: 每轮 chat 的 max_tokens（工具调用轮够用即可）。
        final_max_tokens: 最终回答轮（无 tool_calls）的 max_tokens；若 > max_tokens，
            且该轮 content 为空或 finish_reason=length（reasoning 模型常把 token
            吃光导致 content 截断），用此值重试一次给足空间。默认等于 max_tokens。
        enable_thinking: 工具调用轮的 thinking 开关（None=模型默认）。工具轮通常关
            （False）省 token 提速--决定调哪个工具不需深度推理。
        final_enable_thinking: 最终回答轮的 thinking 开关；默认等于 enable_thinking。
            复杂分析任务建议最终轮开（True）保证质量。

    Returns:
        最终 assistant 文本回答（通常为报告 markdown）。
    """
    # Qwen3.5_122B_A10B 是 reasoning 模型：思考链消耗大量 completion token，
    # 小 max_tokens 下 content 易被截断为空。最终回答轮用更大 max_tokens 兜底。
    final_max_tokens = final_max_tokens or max_tokens
    final_enable_thinking = final_enable_thinking if final_enable_thinking is not None else enable_thinking
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_msg},
    ]
    content = ""  # 防 max_turns=0 时未定义

    for turn in range(max_turns):
        resp = chat(messages, tools=tools_schema, temperature=temperature,
                    max_tokens=max_tokens, enable_thinking=enable_thinking)
        msg = resp["choices"][0]["message"]
        content = msg.get("content") or ""
        tool_calls = msg.get("tool_calls") or []
        finish = resp["choices"][0].get("finish_reason")

        if not tool_calls:
            # 最终回答轮。若 final 策略不同（如工具轮关 thinking、最终轮开）或
            # content 空/截断，用 final 配置（final_enable_thinking + final_max_tokens）重试。
            need_retry = (final_enable_thinking != enable_thinking) or \
                         ((not content or finish == "length") and final_max_tokens > max_tokens)
            if need_retry:
                if verbose:
                    print(f"[llm] turn {turn}: 最终轮重试 thinking={final_enable_thinking} "
                          f"max_tokens={final_max_tokens} (was len={len(content)} finish={finish})")
                resp = chat(messages, tools=tools_schema, temperature=temperature,
                            max_tokens=final_max_tokens, enable_thinking=final_enable_thinking)
                msg = resp["choices"][0]["message"]
                content = msg.get("content") or ""
                finish = resp["choices"][0].get("finish_reason")
            if verbose:
                print(f"[llm] turn {turn}: 最终回答 (len={len(content)}, finish={finish})")
            return content

        # 回传 assistant 消息（必须含 tool_calls）
        messages.append({
            "role": "assistant",
            "content": content,
            "tool_calls": tool_calls,
        })

        # 执行每个工具调用
        for tc in tool_calls:
            name = tc["function"]["name"]
            try:
                args = json.loads(tc["function"].get("arguments") or "{}")
            except Exception:
                args = {}
            fn = tool_map.get(name)
            if fn is None:
                result = f"错误：工具 {name} 不存在。可用：{list(tool_map.keys())}"
            else:
                try:
                    raw = fn(**args) if isinstance(args, dict) else fn()
                    result = json.dumps(raw, ensure_ascii=False, default=str)
                except Exception as e:
                    result = f"工具执行出错: {type(e).__name__}: {e}"
            # 截断过长结果，避免爆 context
            if len(result) > 12000:
                result = result[:12000] + "\n...(已截断)..."
            if verbose:
                args_s = str(args)[:80]
                print(f"[llm] turn {turn}: {name}({args_s}) -> {result[:140]}...")
            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result,
            })

        # 总量上限：超阈值淘汰最早的 tool 结果，保留 system+user+最近上下文
        _trim_tool_messages(messages, max_chars=60000)

    return content or "（达到最大轮次，模型未给出最终回答）"


# ---------- SP 工具 schema（已迁移到 idste.py，保留兼容垫片） ----------

def build_sp_tools_schema():
    """DEPRECATED：已迁移到 idste.build_tools_schema。

    保留此函数仅为向后兼容，新代码请直接 import idste.build_tools_schema。
    """
    warnings.warn(
        "llm.build_sp_tools_schema 已迁移到 idste.build_tools_schema，"
        "将在下个版本移除。",
        DeprecationWarning,
        stacklevel=2,
    )
    from models.idste import build_tools_schema
    return build_tools_schema()


if __name__ == "__main__":
    # 自检：连一次，问一个简单问题
    r = chat([{"role": "user", "content": "用一句话回答：1+1=？"}])
    print("连通自检:", _msg_text(r))
