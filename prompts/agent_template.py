# -*- coding: utf-8 -*-
"""5 段式 Agent Prompt 模板（DAG 工作流用）。"""


AGENT_PROMPT_TEMPLATE = """## 角色

{role}

## 任务

{task_description}

## 上下文数据

### 前置分析结果

{predecessor_context}

### MCP 基线数据

```json
{mcp_context}
```

## 输出格式

{output_format}

## 输出 Schema

```json
{output_schema}
```"""


def build_agent_prompt(
    role: str,
    task_description: str,
    predecessor_context: str,
    mcp_context: str,
    output_format: str,
    output_schema: str,
) -> str:
    """构建 5 段式 Agent Prompt。

    Args:
        role: 角色描述
        task_description: 任务描述
        predecessor_context: 前置依赖 sheet 的摘要文本
        mcp_context: MCP 基线数据 JSON 字符串
        output_format: 输出格式说明
        output_schema: 输出 JSON Schema

    Returns:
        完整的 5 段式 prompt 字符串
    """
    return AGENT_PROMPT_TEMPLATE.format(
        role=role,
        task_description=task_description,
        predecessor_context=predecessor_context or "（无前置依赖）",
        mcp_context=mcp_context or "（无 MCP 基线数据）",
        output_format=output_format,
        output_schema=output_schema,
    )
