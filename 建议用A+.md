我建议选 **A，但是稍微升级一下（A+方案）**。

我仔细看了你现在的代码结构，其实 `controllers/agent.py` 已经承担了整个项目的对外入口，如果直接删掉（B方案），风险会比较大，而且后面如果还要接：

- Streamlit UI
- MCP Server
- API 服务
- CLI
- LangGraph（如果以后要接）
- Workflow Engine

你最后还是会需要一个统一的入口。

所以我的想法是：

```
                    UI                    |                    |                 API                    |                    |                 CLI                    |                    |            controllers/agent.py                    |                    |             Router Agent（统一入口）                    |    --------------------------------------------------    |            |             |             |Strategy       Market         SWOT         GoalReview         Analysis                    GenerationAgent          Agent          Agent         Agent                    |               Validation Agent                    |               Workflow Engine                    |                 Excel                    |                  PPT
```

也就是说：

> **不要把 `controllers/agent.py` 当成业务逻辑层，而是把它升级成 Facade（门面模式）或者 Orchestrator（编排入口）。**

---

### 为什么我不建议 B？

如果选 B：

```
excel_controller        |        |GoalAgentppt_controller        |        |MarketAgentsp_change_controller        |        |SWOTAgent
```

后面会出现一个问题：

- Controller 之间开始互相调用 Agent。
- Agent 的依赖关系越来越乱。
- Workflow 不好统一管理。

尤其你这个项目后面一定会变成：

```
Generate Sheet 2.1      |需要：- Strategy Context- Market Analysis- Historical Strategy- ValidationGenerate Sheet 6.1      |需要：- KPI Analysis- SWOT Result- Goal Generation- Validation
```

如果没有一个统一入口，调用链会非常复杂。

---

### 我更推荐的目录结构

建议改成：

```
controllers/agent.pyexcel_controller.pyppt_controller.pysp_change_2026_controller.pyagents/router_agent.pystrategy_review_agent.pymarket_analysis_agent.pyswot_agent.pygoal_generation_agent.pyvalidation_agent.pyworkflow/sp2026_workflow.pysheet_dispatcher.py
```

然后：

```
controllers/agent.py
```

不要删，而是变成：

```
generate_excel()

↓

RouterAgent.run()

------------------

generate_ppt()

↓

Workflow.run()

------------------

generate_sheet()

↓

SheetDispatcher.run()
```

它只负责：

1. 接收请求。
2. 调用 Workflow。
3. 返回结果。

---

### 我对 Claude Code 的要求

如果让 Claude Code 改，我会加下面这几条约束：

#### 必须保留

```
controllers/agent.py
```

#### 不允许

```
controllers/agent.py
```

做下面的事情：

- Prompt 拼接。
- MCP 调用。
- Web Search。
- LLM 推理。
- Excel 写入。
- PPT 写入。
- Strategic Memory 分析。
- Sheet 分发逻辑。

#### 允许做的事情

- Router。
- Workflow 调用。
- 参数检查。
- 向后兼容。
- CLI 入口。
- API 入口。

---

### 完成后的样子应该是

假设用户调用：

```
generate_2026_strategy()
```

流程应该是：

```
controllers/agent.py↓RouterAgent↓Workflow Engine↓Sheet Dispatcher↓Context Builder↓对应 Agent↓Prompt Builder↓LLM↓JSON↓Schema Validation↓Excel Writer↓PPT Generator↓Return Result
```

整个过程中：

```
controllers/agent.py
```

完全不知道：

- SWOT 怎么做。
- KPI 怎么分析。
- Prompt 长什么样。
- Web Search 怎么做。

它只是：

> “帮你把整个 Workflow 跑起来。”

---

### Definition of Done

我会这样要求 Claude Code：

```
1. 保留 controllers/agent.py。2. controllers/agent.py 不允许包含任何业务逻辑。3. controllers/agent.py 必须作为整个项目的统一入口和 Facade。4. 所有战略规划业务逻辑必须迁移到 Agents 和 Workflow 层。5. 现有 Streamlit UI、CLI 和 Controller 调用方式必须保持兼容。6. 重构完成后，不需要修改任何 UI 调用代码即可正常运行。
```

所以我的最终选择是：

> **A+（保留 `controllers/agent.py`，但将其彻底改造成 Facade / Router / Workflow 入口层），这是对现有代码侵入最小、扩展性最好、最适合后续战略规划智能体演进的方案。**
