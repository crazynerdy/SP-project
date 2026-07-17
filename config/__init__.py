# -*- coding: utf-8 -*-
"""Strategy Tasks 配置加载器。

读取 config/strategy_tasks.yaml，返回结构化任务列表。
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


# 默认配置路径
DEFAULT_CONFIG_PATH = Path(__file__).parent / "strategy_tasks.yaml"


def load_tasks(path: str | os.PathLike | None = None) -> list[dict[str, Any]]:
    """加载所有任务配置。

    Args:
        path: YAML 文件路径; None 时用默认 config/strategy_tasks.yaml

    Returns:
        list[dict]: 每个 dict 包含 sheet_id, sheet_name, agent_type, depends_on 等
    """
    path = Path(path) if path else DEFAULT_CONFIG_PATH
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict) or "tasks" not in data:
        raise ValueError(f"YAML 格式错误: 缺少顶层 'tasks' 键 in {path}")
    return data["tasks"]


def load_task(sheet_id: str, path: str | os.PathLike | None = None) -> dict[str, Any]:
    """按 sheet_id 加载单个任务配置。

    Raises:
        KeyError: sheet_id 不在配置中
    """
    tasks = load_tasks(path)
    for t in tasks:
        if t.get("sheet_id") == sheet_id:
            return t
    raise KeyError(f"sheet_id {sheet_id!r} 不在 YAML 配置中")


def get_enabled_tasks(tasks: list[dict] | None = None, path=None) -> list[dict]:
    """过滤 enabled=true 的任务。"""
    if tasks is None:
        tasks = load_tasks(path)
    return [t for t in tasks if t.get("enabled", False)]


def get_agent_tasks(tasks: list[dict] | None = None, path=None) -> list[dict]:
    """过滤需要 agent 执行的任务（agent_type 不为 null）。"""
    if tasks is None:
        tasks = load_tasks(path)
    return [t for t in tasks if t.get("agent_type") is not None]