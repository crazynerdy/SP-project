# -*- coding: utf-8 -*-
"""SP 2026 智能体自动填写 Prompt。"""


SP_2026_DATA_PROMPT_TEMPLATE = """你是【中海润】公司战略规划分析专家。任务:基于 2025 实际数据
(few-shot), 分析并预测 {year} 年【{template_name}】的 {n_dims} 个维度的内容。

## 一、目标表格信息
- 主模板 sheet 名: {template_name}
- 主模板 A 列 (要看的内容): {row_labels_json}
- 目标列: {target_col} (结果列)
- 目标年份: {year}

## 二、2025 实际数据 (few-shot, 来自 iDSTE MCP sp_data)
{baseline_2025_json}

## 三、业务期望过程 (来自驱动文件 F 列)
{process_hint}

## 四、可用工具
- web_search: 搜索 {year} 年最新行业事件、政策、技术 (DuckDuckGo)
  工具质量次于 sp_data; 本场景主要用来查 {year} 新增趋势

## 五、输出严格 JSON (无 markdown 包装, 无前后言)
{{
{cell_keys_example}
}}

## 六、硬规则
- 每个 cell 内容 ≥80 字, 包含 1-2 个具体数据/事件引用
- 不臆造; 引用来自 baseline_2025 或 web_search; {year} 预测必须明确标注"预测"
- 结论先行; 中文; 字符串内不用 ASCII 双引号 (用「」或 "")
- {n_dims} 个 cell 风格、深度对齐
- 仅返 JSON, 不要任何解释
"""


def build_sp_2026_data_prompt(
    template_name: str,
    row_labels: list[str],
    baseline_2025_json: str,
    process_hint: str,
    year: int,
    target_col: str = "B",
    start_row: int = 4,
) -> str:
    """动态拼装 SP 2026 prompt。"""
    n_dims = len(row_labels)
    cell_keys_example = ",\n".join(
        f'  "{target_col}{start_row + i}": "..."' for i in range(n_dims)
    )
    row_labels_json = " | ".join(row_labels) if row_labels else "(无维度标签)"
    return SP_2026_DATA_PROMPT_TEMPLATE.format(
        template_name=template_name,
        n_dims=n_dims,
        row_labels_json=row_labels_json,
        target_col=target_col,
        baseline_2025_json=baseline_2025_json,
        process_hint=process_hint or "（无额外业务期望）",
        year=year,
    )
