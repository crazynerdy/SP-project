# -*- coding: utf-8 -*-
"""测试数据工厂。"""


def make_task(sheet_id, sheet_name, agent_type="strategy", depends_on=None, enabled=True):
    return {
        "sheet_id": sheet_id,
        "sheet_name": sheet_name,
        "agent_type": agent_type,
        "depends_on": depends_on or [],
        "enabled": enabled,
    }


def make_context(mcp_data=None, sheet_results=None):
    from core.strategic_context import StrategicContext
    return StrategicContext(
        mcp_data=mcp_data or {},
        sheet_results=sheet_results or {},
    )
