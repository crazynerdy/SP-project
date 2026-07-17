# -*- coding: utf-8 -*-
"""Workflow Engine — 拓扑排序 + 按序调度 Agent + 校验 + 写入 xlsx + 生成 PPT。

核心类 WorkflowEngine:
    engine = WorkflowEngine(tasks, context, llm_client, prompts_module,
                            agents, xlsx_exporter, template_path, output_dir)
    result = engine.run(sheet_ids=["2.2 行业趋势分析表"])
    # 或全量执行: engine.run()
"""
from __future__ import annotations

import os
import json
from datetime import datetime
from uuid import uuid4
from typing import Any

from openpyxl import load_workbook

from config import load_tasks, get_enabled_tasks
from core.agent_utils import make_counting_wrapper, build_full_tool_map
from core.strategic_context import StrategicContext, get_dependencies
from core.errors import EngineError, ErrorCollector
from core.engine.topology import topological_sort, CycleError
from core.engine.sheet_matcher import master_template_sheet
from schemas import get_schema_for_sheet


class WorkflowEngine:
    """DAG 工作流引擎。

    按 YAML 配置的 depends_on 拓扑排序，逐 sheet 执行 agent → 校验 → 写 xlsx。

    Usage:
        engine = WorkflowEngine(
            tasks=load_tasks(),
            context=strategic_context,
            llm_client=llm,
            prompts_module=prompts,
            agents=AGENT_REGISTRY,
            xlsx_exporter_module=xlsx_exporter,
            template_path=template_path,
            output_dir="output",
        )
        result = engine.run()
    """

    def __init__(
        self,
        tasks: list[dict],
        context: StrategicContext,
        llm_client=None,
        prompts_module=None,
        agents: dict | None = None,
        xlsx_exporter_module=None,
        template_path: str | None = None,
        output_dir: str = "output",
        enable_web_search: bool = True,
        verbose: bool = True,
    ):
        self.tasks = tasks
        self.context = context
        self.llm_client = llm_client
        self.prompts_module = prompts_module
        self.agents = agents or {}
        self.xlsx_exporter = xlsx_exporter_module
        self.template_path = template_path
        self.output_dir = output_dir
        self.enable_web_search = enable_web_search
        self.verbose = verbose

        # 运行时状态
        self.tool_call_stats: dict = {"__all__": {}}
        self.error_collector = ErrorCollector()
        self.filled_sheets: list[str] = []
        self.out_xlsx_path: str | None = None

        # 延迟导入默认模块
        if self.llm_client is None:
            from models import llm as _llm
            self.llm_client = _llm
        if self.prompts_module is None:
            from models import prompts as _prompts
            self.prompts_module = _prompts
        if self.xlsx_exporter is None:
            from models import xlsx_exporter as _xlsx_exporter
            self.xlsx_exporter = _xlsx_exporter
        if self.template_path is None:
            from core.envutil import env
            self.template_path = env("TEMPLATE_XLSX_PATH")

    # ---- 拓扑排序 ----
    def topological_sort(self) -> list[dict]:
        """Kahn 算法拓扑排序，返回合法执行顺序。"""
        return topological_sort(self.tasks)

    # ---- 主入口 ----
    def run(self, sheet_ids: list[str] | None = None) -> dict:
        """执行完整工作流。

        Args:
            sheet_ids: 限定只执行这些 sheet（None = 全部 enabled）

        Returns:
            {
                "output_xlsx_path": str | None,
                "tool_call_stats": {"__all__": {name: count}},
                "filled_sheets": [...],
                "errors": [...],
                "context": StrategicContext,
            }
        """
        sorted_tasks = self.topological_sort()

        # 过滤
        if sheet_ids:
            id_set = set()
            for s in sheet_ids:
                s = s.strip().rstrip("表")
                id_set.add(s)
            sorted_tasks = [
                t for t in sorted_tasks
                if t["sheet_id"].strip().rstrip("表") in id_set
                or t["sheet_name"].strip().rstrip("表") in id_set
            ]
            if not sorted_tasks:
                raise ValueError(f"过滤后无任务: sheet_ids={sheet_ids}")

        if self.verbose:
            order = [t["sheet_id"] for t in sorted_tasks]
            print(f"[engine] 执行顺序: {order}")

        # 预加载 master template sheet names
        _tpl_wb = load_workbook(self.template_path, read_only=True)
        _tpl_sheet_names = list(_tpl_wb.sheetnames)
        _tpl_wb.close()

        os.makedirs(self.output_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.out_xlsx_path = os.path.join(
            self.output_dir, f"{ts}_sp_dag_{uuid4().hex[:8]}_data.xlsx"
        )

        for task in sorted_tasks:
            self._execute_sheet(task, _tpl_sheet_names)

        # 全部失败 -> raise critical
        if not self.filled_sheets and self.error_collector:
            raise RuntimeError(
                f"所有 {len(sorted_tasks)} 个 sheet 都失败: "
                + "; ".join(str(e) for e in self.error_collector.errors)
            )

        # 生成 PPT
        pptx_path = None
        if self.filled_sheets:
            try:
                pptx_path = self._generate_pptx()
            except Exception as e:
                if self.verbose:
                    print(f"[engine] PPT 生成失败: {e}")

        return {
            "output_xlsx_path": self.out_xlsx_path if self.filled_sheets else None,
            "pptx_path": pptx_path,
            "tool_call_stats": self.tool_call_stats,
            "filled_sheets": self.filled_sheets,
            "errors": self.error_collector.errors,
            "context": self.context,
        }

    # ---- 单 sheet 执行 ----
    def _execute_sheet(self, task: dict, tpl_sheet_names: list[str]):
        """执行单个 sheet: agent -> validate -> retry -> write xlsx。"""
        sheet_id = task["sheet_id"]
        sheet_name = task["sheet_name"]
        agent_type = task["agent_type"]

        try:
            # 1) 创建 agent 实例
            agent_cls = self.agents.get(agent_type)
            if agent_cls is None:
                raise ValueError(f"未知 agent_type: {agent_type!r}")

            agent = agent_cls(
                llm_client=self.llm_client,
                prompts_module=self.prompts_module,
            )

            # 2) 执行 agent（含重试逻辑）
            # 引擎层统一用 CellMapOutput 校验（agent 输出 格式）
            # 结构化 schema（PESTELOutput 等）后续增强时使用
            from schemas.cell_map import CellMapOutput
            schema_cls = CellMapOutput
            max_retries = 2
            last_error = None

            for attempt in range(max_retries + 1):
                if self.verbose and attempt > 0:
                    print(f"[engine] {sheet_id} 校验失败，重试 {attempt}/{max_retries}")

                output = agent.execute(
                    sheet_id=sheet_id,
                    task=task,
                    context=self.context,
                    tool_call_stats=self.tool_call_stats,
                    enable_web_search=self.enable_web_search,
                    verbose=self.verbose,
                )

                # 校验
                try:
                    validated = schema_cls.model_validate(output)
                    break
                except Exception as ve:
                    last_error = ve
                    if attempt < max_retries:
                        # 把校验错误信息传给 agent 重试
                        task["_validation_error"] = str(ve)
                    continue
            else:
                # 3 次全失败 → 用原始输出做 fallback
                if self.verbose:
                    print(f"[engine] {sheet_id} 校验 {max_retries+1} 次全失败，用原始输出 fallback: {last_error}")
                validated = schema_cls.model_validate(output) if output else None

            # 3) 提取 cells
            if validated is not None:
                if hasattr(validated, "cells"):
                    cells = validated.cells
                elif hasattr(validated, "model_dump"):
                    # 结构化输出 → 序列化为 cells
                    dumped = validated.model_dump()
                    cells = {}
                    for key, val in dumped.items():
                        if key == "notes":
                            continue
                        if isinstance(val, list):
                            for i, item in enumerate(val):
                                if isinstance(item, dict):
                                    for k, v in item.items():
                                        row = 4 + i
                                        col = chr(ord("B") + list(item.keys()).index(k))
                                        cells[f"{col}{row}"] = str(v)
                        else:
                            cells[f"B{4 + len(cells)}"] = str(val)
                else:
                    cells = {}

                # 存 notes 到 sheet_results
                notes = getattr(validated, "notes", "") if hasattr(validated, "notes") else ""
                self.context.sheet_results[sheet_id] = {
                    "cells": cells,
                    "notes": notes,
                    "agent_type": agent_type,
                    "sheet_name": sheet_name,
                }
            else:
                cells = output.get("cells", {}) if isinstance(output, dict) else {}
                self.context.sheet_results[sheet_id] = {
                    "cells": cells,
                    "notes": "",
                    "agent_type": agent_type,
                    "sheet_name": sheet_name,
                }

            # 4) 写入 xlsx
            mt_sheet = self._master_template_sheet(sheet_name, tpl_sheet_names)

            if not os.path.exists(self.out_xlsx_path):
                self.xlsx_exporter.fill_cells(
                    self.template_path, mt_sheet, cells,
                    mode="overwrite", out_path=self.out_xlsx_path,
                )
            else:
                wb = load_workbook(self.out_xlsx_path)
                available = {name.strip(): name for name in wb.sheetnames}
                sname_norm = mt_sheet.strip()
                if sname_norm in available:
                    ws = wb[available[sname_norm]]
                    for coord, val in cells.items():
                        ws[coord] = val
                    wb.save(self.out_xlsx_path)
                else:
                    raise KeyError(f"主模板里没有 sheet {mt_sheet!r}")

            self.filled_sheets.append(mt_sheet)
            if self.verbose:
                print(f"[engine] OK: {sheet_id} ({sheet_name}) -> {len(cells)} cells")

        except Exception as e:
            error = EngineError(
                message=f"{type(e).__name__}: {e}",
                severity="warning",
                sheet_id=sheet_id,
                stage="execute",
            )
            self.error_collector.add(error)
            if self.verbose:
                print(f"[engine] FAIL: {sheet_id} - {error.message}")

    # ---- 工具方法 ----
    def _master_template_sheet(self, output_template: str,
                               available_sheets: list[str]) -> str:
        """模糊匹配 D 列模板名 → 主模板实际 sheet 名。"""
        return master_template_sheet(output_template, available_sheets)

    def _generate_pptx(self) -> str | None:
        """生成 PPT（后置步骤）。"""
        if not self.out_xlsx_path or not os.path.exists(self.out_xlsx_path):
            return None
        try:
            from models import pptx_builder, xlsx_reader
            xlsx_data = xlsx_reader.read_template(self.out_xlsx_path)
            if not xlsx_data.get("sheets"):
                return None
            return pptx_builder.build_pptx(
                {"slides": []},  # 简化：先不做 slide-spec 生成
                output_dir=self.output_dir,
                verbose=self.verbose,
            )
        except Exception:
            return None