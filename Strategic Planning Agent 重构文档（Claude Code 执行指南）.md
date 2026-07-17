## 一、项目背景与终极目标

你正在重构一个企业战略规划智能体项目。  
**当前状态**：项目代码本质上是一个“自动写报告”工具，通过 MCP 获取数据后直接让单个 LLM 填写 Excel。  
**终极目标**：将其重构为一个支持严格业务推理顺序的**多 Agent DAG（有向无环图）工作流系统**。系统需根据《战略规划SP变更需求》Excel 中的 37 个 Sheet 依赖关系，自动调用不同类型的 Agent，结合 MCP 获取的 2025 年结构化数据和 Web Search 外部数据，逐步推理生成 2026 年战略规划，最终输出校验后的 Excel 和 PPT。

## 二、核心设计原则与禁止事项

**必须遵守：**

1. **配置驱动 DAG**：所有 Sheet 的依赖关系、数据来源必须定义在 `config/strategy_tasks.yaml` 中。
2. **Strategic Context**：使用一个全局内存对象在 Agent 之间传递前置 Sheet 的生成结果。
3. **3 类基础 Agent**：系统仅包含 `WebSearchAgent`、`SynthesisAgent`、`StrategyAgent`。
4. **Structured Output & Validation**：所有 Agent 输出必须为 JSON，且必须经过 Pydantic Schema 校验后才能写入 Excel。

**禁止事项：**

1. **禁止使用 RAG / VectorDB / 知识库**（MCP 提供的已全是结构化数据）。
2. **禁止使用 Few-shot 进行业务推理**（仅允许用于示范输出格式）。
3. **禁止在 Prompt 中直接拼接整个 2025 Excel 或全量上下文**，必须根据当前 Sheet 的依赖关系按需提取。
4. **禁止让一个 Agent 处理所有 Sheet**。

## 三、系统架构蓝图

最终项目的目录结构必须如下：

text

复制

```
strategic_planning_agent/
├── config/
│   └── strategy_tasks.yaml          # 核心配置：37个Sheet的DAG依赖和Agent类型
├── core/
│   ├── strategic_context.py         # 全局上下文对象（管理MCP数据和Sheet结果）
│   └── workflow_engine.py           # 工作流引擎（拓扑排序、按序调度Agent）
├── agents/
│   ├── base_agent.py                # Agent基类（处理Prompt构建和LLM调用）
│   ├── web_search_agent.py          # 联网搜索类Sheet
│   ├── synthesis_agent.py           # 纯内部综合推理类Sheet
│   └── strategy_agent.py            # 深度战略设计类Sheet
├── schemas/
│   └── sheet_schemas.py             # 所有需要智能体生成的Sheet的Pydantic模型
├── prompts/                         # Prompt 模板目录
├── mcp/                             # 【保留现有代码】MCP 接入层
├── exporters/                       
│   ├── xlsx_exporter.py             # 【保留现有代码】Excel 模板解析和写入
│   └── ppt_generator.py             # 【保留现有代码】PPT 生成链路
└── app.py                           # 项目入口
```

## 四、详细开发任务（请按顺序执行）

### Step 1: 提取配置与目录初始化

1. 按照上述目录结构创建文件夹。
2. 读取提供的《战略规划SP变更需求-6.5 版》Excel。
3. **创建 `config/strategy_tasks.yaml`**：  
   将 Excel 中“数据来源/变更需求”和“业务期望分析过程”两列转化为 YAML 配置。对于每一个需要“智能体自动填写”的 Sheet，定义其：
   - `name`: Sheet名称
   - `agent_type`: 可选值为 `web_search`, `synthesis`, `strategy`
   - `depends_on`: 它依赖的前置 Sheet 序号列表（如 [“1.1”, “2.1”]）
   - `mcp_fields`: 需要从 MCP 获取的业务字段（如 [“competitor_list”, “business_lines”]）
   - `schema_class`: 对应的 Pydantic 模型名称  
     *(注意：对于“中海润公司填写”的 Sheet，不需在此配置 agent，由 MCP 直接获取数据填入)*

### Step 2: 实现全局上下文与 Schema

1. **实现 `core/strategic_context.py`**：
   - 包含一个 `mcp_data` 字典（系统启动时一次性载入所有 MCP 数据）。
   - 包含一个 `sheet_results` 字典（记录每个 Sheet 生成的 JSON 结果）。
   - 提供 `get_dependencies(sheet_id)` 方法：根据 YAML 配置，返回该 Sheet 所依赖的前置 Sheet 结果。**注意：如果依赖的 Sheet 过多，需对前置结果做简单的文本摘要，防止上下文超限。**
2. **实现 `schemas/sheet_schemas.py`**：
   - 根据《输出格式》Excel，使用 Pydantic 为每个需要智能体生成的 Sheet 定义数据结构模型。
   - 例如 `2.1 宏观环境分析`：

python

复制

```
     class PESTELRow(BaseModel):
         维度: str
         变化与趋势: str
         机会: str
         威胁: str
     class Sheet2_1Output(BaseModel):
         rows: List[PESTELRow]
```

![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACgAAAAoCAYAAACM/rhtAAAACXBIWXMAABYlAAAWJQFJUiTwAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAPLSURBVHgBzZi/UxNBFMffW35EIZGkQLlIQQpsQfwDiDXqYAcMhRboUCEz0gL5A5RQMQIzYiNY0UjHDNgLgy0UxBmGY0KRSE4U8Hbdd5BALpdkE0KST5Pc7dvZ773dffv2IRSJfpgICuCdwLEbQHQCohcEeK1GhLgQIoKAEQHiB2NsXWv2rEMRYCHGu7vCe8ttjMjB36TEqBMRCOvMrAtp2u2IaiclgSTM1WhMAAkrAVLogqrQvAIPosYIBz5ZhMfyEeEIoda7dxZyGeUUuB9NTJXKa1lhGPY3e0azNTsKPJ/SxLL0WhDKgNxIW6fH/HEg4Ivb25hTh/oGY61c4gi52ztdjTXLTm0ZAmlakcJGuZEO2T+US8pG2hTvRY9eMAEfoZIIMepvaQonH1MCdf1Pm2Bna/JvG1SW+MmxGUiux8sprjmbgMqLI7wud+1E8sHy4IX3dqGKkF70kRdrrSfynlDvvLG5AYtLX2B7exv2dd16t7a6Ch6PJ8M2kUhI2yXZZxO2d3as56c9PTAxPp5zjPoGRvF30hIoCggp76amrAHtGAkjQyAJejs2lvqIQpChZ4QEMl1PBEFx7c3OzTmKc0KXoooVd4GXMqZazngQFXIGmpqvKysZ7x91dYFf08Dtcae9/y6n1C6OPPxETm+wuxtUECbvrJXiOlSMNxwGfNDeDh9mZhzt7Z6mjyBbTf6qIrdFUIYZbFMxpg1hJ5cn7PYkrBBxBCJ2MEDRpmKsO6ylbAPScigRXnadPO99OAwDg4PW5rmKYRgZtrREnvX2wuvhYcePzS7wGpCnKJTMzs8reY3WMAn9vLgIqjC64EAJoDiobGso28Zpiksi8EZAEaEp3oIqRXD4KT0ovkG1grDFULCq9SBd+JmmyRu/wkZxO2Qq6e2XR53b7c5tm6f9HBGhaoQVZoQppvOZD/T1WceVHTpfXw0NpWUyyXdO0PE40N8PeeUhrtOvlSXsxmJe12lNDKoI5GZA03zWLoaAzxfnIr8XywWVRkgc/U+dJGcuWd7AaoiJMvaZZij5lBJIXoR/IgQVhnMMJb1HpJ3Ffn9TuJJTTWO3aunFJMdUej96VNbSB0H1mfv3mh7a3ztmMyd15nPZpXwBXBY2qXjk3JSDvYNfYYbW7erGsKa1pSlriS9nPkgdkcNL2llQalDEqQ6TSxyRN2HV5KJFTu4Xn6BEkNdOfvPA1SJRNgoqout6TJZI2KT826162bocScSFCdOnf3nYqVCZtRsUCV34L+7U8toqL14oL/8CvUkx54kwblE6RxmTlZQUwX9+F568K5L+eAAAAABJRU5ErkJggg==)

引用

### Step 3: 实现工作流引擎

1. **实现 `core/workflow_engine.py`**：
   - 编写拓扑排序算法，读取 `strategy_tasks.yaml`，计算出所有 Sheet 的合法执行顺序。
   - 按顺序遍历 Sheet。如果该 Sheet 不需要智能体（即公司填写），直接跳过（由 MCP 导入模块处理）。
   - 如果需要智能体，实例化对应的 Agent，调用 `agent.execute(sheet_id, context)`。
   - 拿到 Agent 返回的 JSON 后，用对应的 Pydantic Schema 进行校验。校验失败则要求 Agent 重试（最多 2 次）。
   - 校验通过后，将结果存入 `StrategicContext`，并调用 `exporters/xlsx_exporter.py` 写入当前 Sheet。
   - 所有 Sheet 完成后，调用 `ppt_generator.py` 生成 PPT。

### Step 4: 实现 3 类 Agent

1. **实现 `agents/base_agent.py`**：
   - 封装 LLM 调用逻辑和 Prompt 构建逻辑。
   - Prompt 必须包含 5 个部分：Role, Task Description, Context (来自 StrategicContext 的前置依赖和 MCP 数据), Output Format Requirement (Schema), Output Schema (Pydantic)。
2. **实现 `agents/web_search_agent.py`**：
   - 适用于 2.1(PESTEL), 2.2(行业趋势), 2.3(市场容量) 等。
   - 逻辑：提取 Context 和 MCP 字段 -> 构建搜索 Query -> 执行 Web Search -> 对搜索结果做摘要 -> 连同前置依赖一起交给 LLM 生成 JSON。
3. **实现 `agents/synthesis_agent.py`**：
   - 适用于 2.9(五看总结), 2.10(SWOT) 等。
   - 逻辑：无 Web Search。仅获取 `depends_on` 的前置 Sheet 结果 -> 组合成大 Prompt -> 让 LLM 做归纳总结推理。
4. **实现 `agents/strategy_agent.py`**：
   - 适用于 3.2(战略地图), 5.1(竞争战略), 6.1(战略举措) 等。
   - 逻辑：获取前置依赖 + MCP 业务数据 -> 启用 Chain of Thought 深度推理 -> 输出结构化战略规划 JSON。

## 五、关于 MCP 和现有代码的复用

- **保留**现有的 `mcp/`、`exporters/xlsx_exporter.py` 和 `exporters/ppt_generator.py` 模块。
- 系统入口 `app.py` 需负责：初始化 MCP 客户端 -> 拉取所有 2025 数据存入 `StrategicContext.mcp_data` -> 将公司填写的原始数据通过 `xlsx_exporter` 直接写入对应 Sheet -> 启动 `WorkflowEngine`。

## 六、项目完成标准

当你完成了以下所有条件，视为重构成功：

1. `strategy_tasks.yaml` 中准确包含了 37 个 Sheet 的配置，且依赖关系与业务需求 Excel 一致。
2. 运行 `app.py` 时，系统能自动执行 DAG 工作流，控制台打印每个 Sheet 的开始与结束日志，无报错中断。
3. 对于复杂的依赖 Sheet（如 5.1 依赖 22 个前置 Sheet），系统能够自动提取前置结果摘要并成功生成内容。
4. 生成的最终 Excel 文件中，所有标记为“智能体自动生成”的 Sheet 均有正确格式的数据，无空白或格式错乱。
5. 最终自动生成了对应的 PPT 文件。
6. 代码中没有出现 RAG、VectorDB 相关的代码引入。
