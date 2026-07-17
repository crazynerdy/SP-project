# -*- coding: utf-8 -*-
"""拓扑排序 — 从 WorkflowEngine 提取的纯函数。"""
from __future__ import annotations


class CycleError(Exception):
    """拓扑排序检测到环。"""
    pass


def topological_sort(tasks: list[dict]) -> list[dict]:
    """Kahn 算法拓扑排序，返回合法执行顺序。

    Args:
        tasks: 任务列表（仅 enabled + agent_type 不为 null 的）

    Returns:
        list[dict]: 排序后的任务列表

    Raises:
        CycleError: 检测到环
    """
    enabled = [t for t in tasks if t.get("enabled", False)]
    agent_tasks = [t for t in enabled if t.get("agent_type") is not None]

    in_degree: dict[str, int] = {}
    adj: dict[str, list[str]] = {}
    id_to_task: dict[str, dict] = {}

    for t in agent_tasks:
        sid = t["sheet_id"]
        in_degree[sid] = 0
        adj[sid] = []
        id_to_task[sid] = t

    for t in agent_tasks:
        sid = t["sheet_id"]
        for dep in t.get("depends_on", []):
            if dep in id_to_task:
                in_degree[sid] += 1
                adj[dep].append(sid)

    queue = [sid for sid, deg in in_degree.items() if deg == 0]
    sorted_ids = []

    while queue:
        u = queue.pop(0)
        sorted_ids.append(u)
        for v in adj.get(u, []):
            in_degree[v] -= 1
            if in_degree[v] == 0:
                queue.append(v)

    if len(sorted_ids) != len(agent_tasks):
        remaining = set(id_to_task.keys()) - set(sorted_ids)
        raise CycleError(
            f"拓扑排序检测到环，涉及 sheet: {sorted(remaining)}"
        )

    return [id_to_task[sid] for sid in sorted_ids]
