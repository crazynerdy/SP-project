# -*- coding: utf-8 -*-
"""统一错误模型 — EngineError + ErrorCollector。

PR4 of docs/REFACTOR_CODEX_2026.md
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Literal

logger = logging.getLogger("sp_agent")

Severity = Literal["info", "warning", "critical"]


@dataclass
class EngineError(Exception):
    """引擎层统一异常。

    Args:
        message: 错误描述
        severity: 严重程度
        sheet_id: 关联 sheet（可选）
        stage: 发生阶段（如 "mcp", "llm", "validate", "write"）
    """
    message: str
    severity: Severity = "warning"
    sheet_id: str | None = None
    stage: str = "unknown"

    def __str__(self) -> str:
        parts = [f"[{self.severity.upper()}]"]
        if self.sheet_id:
            parts.append(f"sheet={self.sheet_id}")
        parts.append(f"stage={self.stage}: {self.message}")
        return " ".join(parts)


@dataclass
class ErrorCollector:
    """收集错误，按 severity 分级处理。"""
    errors: list[EngineError] = field(default_factory=list)

    def add(self, error: EngineError) -> None:
        self.errors.append(error)
        if error.severity == "critical":
            logger.error(str(error))
        elif error.severity == "warning":
            logger.warning(str(error))
        else:
            logger.info(str(error))

    def has_critical(self) -> bool:
        return any(e.severity == "critical" for e in self.errors)

    def get_by_sheet(self, sheet_id: str) -> list[EngineError]:
        return [e for e in self.errors if e.sheet_id == sheet_id]

    def raise_if_critical(self) -> None:
        """存在 critical 错误时抛 RuntimeError（聚合）。"""
        criticals = [e for e in self.errors if e.severity == "critical"]
        if criticals:
            msg = "; ".join(str(e) for e in criticals)
            raise RuntimeError(msg)

    def __len__(self) -> int:
        return len(self.errors)
