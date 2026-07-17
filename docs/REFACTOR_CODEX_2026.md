# REFACTOR_CODEX_2026

> 触发：Codex 2026-07-17 复审提出 7 类问题。
> 执行人：Claude (claude-sonnet-5)。
> 截止目标：每个 PR 完成后 `python -c "import controllers.ppt_controller; from core.workflow_engine import WorkflowEngine; print('OK')"` 这种 import 探烟必须过。

## Problem Statement

Codex 2026-07-17 复审发现 7 类缺陷：

1. **仓库污染** — `.superpowers/sdd/review-*.diff`（13 个 ~200KB）漏在 `.gitignore` 外；`__pycache__/` 散落 30+ 个 `.pyc`；`output/` 混入 `debug_xlsx_text.txt` / `test_fill_*.xlsx` / `regression_test.xlsx`；`agent_run.log` / `ppt_run.log` / `streamlit_*.txt` 漏忽略。
2. **零自动化测试** — DAG 拓扑、CJK 模糊匹配、JSON 解析容错这种纯函数没有任何 pytest 覆盖；`STATUS.md` 写"验证"全靠 `python -c "import..."` 和端到端跑一次。
3. **代码路径多入口未收敛** — 旧 `controllers/agent.py`（4 函数流）已从工作树删除但 `controllers/ppt_controller.py:10` 仍 `from controllers.agent import generate_pptx_from_xlsx` → **当前 ImportError**；DAG `WorkflowEngine`（`core/workflow_engine.py`）、`controllers/sp_change_2026_controller.py`（已删但 README/STATUS 仍引用）、`api/`（已消失）—— 文档、CLI、docstring 都还指向已不存在的路径。
4. **错误处理两套策略混用** — `core/strategic_context.py` 第 70-72/85-86/91-92/108-109 行全是 `try/except: pass` 静默吞错；`WorkflowEngine._execute_sheet` 反而把每条失败收 `self.errors` 列表；排查时无统一日志格式。
5. **硬编码部署耦合** — `models/pptx_builder.py:55` 错误信息里写死 `D:\memory`；`.env` / `STATUS.md` 含 `IDSTE_PASSWORD=<iDSTE_PASSWORD>` 和内网 IP；模板默认 `D:\下载\【中海润】...xlsx`。
6. **`.superpowers/` 整目录**（含 skills、sdd、多个 diff）从开发工具内部状态泄漏到工程根目录。
7. **300 行 guideline 违规** — `views/ui_theme.py` 612 行、`models/prompts.py` 443 行、`core/workflow_engine.py` 396 行。

## Solution

按 Fowler 原则分 6 个 PR 推进，每 PR 一个垂直切片。期间 `import` 探烟 + 新增 `pytest` 探烟必须过。

**已确认的好消息**：`git log --all -- .env` 0 命中 — `.env` 从未入过 git 历史（`.gitignore` 早拦截），无需 `git filter-repo`，直接 `rm` 即可。

## Commits

### PR 1 — 仓库清理 + 凭据隔离（半天）

- `chore(gitignore): add .superpowers/, review-*.diff, *.bak, .streamlit/secrets.toml`
- `chore(repo): untrack .superpowers/ and root-level *.log via git rm -r --cached`
- `chore(output): rm output/debug_*.txt, output/test_fill_*.xlsx, output/regression_test.xlsx from tracking`
- `chore(clean): add scripts/clean_repo.sh that nukes __pycache__/ + .pyc + output/debug*`
- `chore(env): rm .env from working tree (never tracked; user is switching MCP connection method — see Notes)`
- `docs(status): remove plaintext <iDSTE_PASSWORD> from STATUS.md and 建议用A+.md`
- `chore(hooks): pre-commit detect .env / *.log / __pycache__`

**验收**：`git ls-files .env` 0 命中；`scripts/clean_repo.sh` 跑完无残留；`grep -rn <iDSTE_PASSWORD> .` 在 docs/STATUS/建议用A+ 中 0 命中（仅 `.env.example` 注释保留占位说明）。

### PR 2 — 修复坏引用 + 路径收敛（Bug fix，1 天）

- `fix(controllers/ppt_controller): replace broken 'from controllers.agent import' with new engine entry`
- `refactor(cli): add sp_agent/__main__.py as the only CLI; deprecate python -m controllers.*`
- `refactor(app): drop stale '业务编排见 controllers/agent.py' docstring in app.py:4`
- `docs(refactor_mvc): mark 旧 agent.py 章节为 [DEPRECATED] 或归档到 docs/archive/`
- `docs(readme): replace 'python -m controllers.agent' with 'python -m sp_agent' + 入口示例`
- `docs(status): drop 'controllers.agent 5 个导出函数可用' 那行；新增 '入口已统一' 段落`
- `docs(建议用A+): delete or rewrite to current module list`
- `docs(superpowers): 旧 plans/specs 引用 'controllers/sp_change_2026_controller.py' 的段落统一指向 sp_agent.cli 或打 deprecated 标记`

**验收**：`grep -r "controllers.agent" .` 在源码（不含 docs/archive）0 命中；`python -c "import controllers.ppt_controller; import controllers.excel_controller; from core.workflow_engine import WorkflowEngine"` 0 异常。

### PR 3 — 测试基线（pytest，2 天）

- `chore(test): scaffold tests/ + pytest.ini + tests/conftest.py with mcp_idste fixture`
- `chore(test): tests/_factories.py 提供 make_task / make_context / fake_llm_client 工厂`
- `test(core/workflow_engine): topological_sort — 线性/钻石/环/单点/缺依赖 5 case`
- `test(core/workflow_engine): _master_template_sheet — 精确/前缀/CJK chunk/不匹配回退 4 case`
- `test(core/json_utils): parse_json — bare/代码围栏/markdown 段/前后言/中英文混 6 case`
- `test(core/strategic_context): build — 全部 target_tables / 子集 / 空集 / MCP 异常 各 1 case`
- `test(models/prompts): build_intent_recognition_prompt / build_xlsx_data_prompt / build_slide_spec_from_xlsx_prompt / build_sp_2026_data_prompt / build_agent_prompt — 长度/字段占位 5 case`
- `test(core/agent_utils): make_counting_wrapper / build_full_tool_map 2 case`
- `chore(test): scripts/run_tests.sh 本地跑 pytest（不接 CI；用户已通内网可本地调真 LLM）`

**验收**：`pytest -q` 100% 通过；`pytest --cov=core --cov=models --cov=agents` 核心模块 ≥ 70%。

### PR 4 — 错误处理统一（一致性，1 天）

- `refactor(core): add core/errors.py — EngineError(severity, sheet_id, stage, cause) + ErrorCollector + logger setup`
- `refactor(core/strategic_context): replace 4 处 'except Exception: pass' 为 'logger.warning("MCP 调用失败: %s", stage, exc_info=True)'`
- `refactor(workflow_engine): 用 ErrorCollector 替代裸 list；critical 错误（全失败）才 raise RuntimeError；warning 级别（MCP 单点）只记日志不计入 errors`
- `refactor(agents): base_agent 失败时抛 EngineError 而非返回 None，让上层决策`
- `chore(logging): config/logging.yaml 统一日志格式和级别（INFO/DEBUG 开关）`

**验收**：人工注入 1 个 MCP 失败，跑端到端：日志含 `MCP 调用失败: sp_data_menu`，xlsx 仍正常产出；注入 1 个 schema 校验失败，errors 列表含 1 条，全部失败时 raise。

### PR 5 — 硬编码路径清理（可移植性，半天）

- `refactor(core/paths): 集中所有路径解析；新增 paths.project_root() 替代裸 os.path.dirname(__file__) 四次`
- `refactor(models/pptx_builder): 错误信息走 paths.project_root()，不再写死 'D:\memory'`
- `refactor(envutil): env() 启动时校验 TEMPLATE_XLSX_PATH 存在，否则给清晰报错（带示例）`
- `docs(readme): 增加"换机部署清单"小节：改 .env / 改 TEMPLATE_XLSX_PATH / 跑 pytest 三步`

**验收**：`grep -rn "D:\\\\" core/ models/ agents/ controllers/ views/` 0 命中（除 .env.example 注释里给路径示例的位置）。

### PR 6 — 文件拆分（重构债，2 天）

- `refactor(prompts): split models/prompts.py → prompts/{intent,xlsx_data,slide_spec,sp_2026,agent_template}.py 五个子模块 + prompts/__init__.py 聚合 build_* 函数`
- `refactor(views): split views/ui_theme.py → views/ui_theme/{tokens,components,injector}.py 三个子模块，公开 API 保持不变`
- `refactor(core): split workflow_engine.py → core/engine/{runner,topology,sheet_writer,pptx_step}.py + core/engine/__init__.py 导出 WorkflowEngine`
- `refactor(doc): 每个新模块顶部加 'moved from X' 注释，git blame 仍可追`

**验收**：所有 `from models.prompts import X` 改为 `from prompts import X`（或保留 `models.prompts` 兼容 shim 一版再删）；`wc -l` 检查无文件 > 300 行（`views/ui_theme/__init__.py` 聚合文件除外）。

## Decision Document

- **单一入口**：新增 `sp_agent/__main__.py`，统一 CLI；`controllers/*.py` 不再做 `__main__` 段。
- **统一错误模型**：`core/errors.EngineError(severity=info|warning|critical, stage=阶段名, sheet_id=...)` + `ErrorCollector`。`strategic_context` 走 `warning`（MCP 单点）；`workflow_engine._execute_sheet` 走 `critical`（每 sheet 一票，全失败才 raise）。
- **测试范围**：只覆盖纯函数 + DI 注入点；不测 LLM 真调用（mock），不测 Streamlit UI（成本太高，留手动）。用户已通内网可本地调真 LLM 做手动冒烟。
- **凭据策略**：用户决定切换 MCP 连接方式 → `.env` 整体删，不轮换。GitLab 凭据由用户管理，不入仓不入 memory。
- **架构原则**：保留 DAG + WorkflowEngine 主路径，不再引入新代码路径；旧的 4 函数流彻底退出（包括 docstring）。
- **路径 API**：`core/paths.py` 是唯一路径出口，错误信息里的"项目根目录"必须走 `paths.project_root()`。
- **prompts 拆分边界**：按"输入参数 + 输出字段"切，不按"业务场景"切（避免后续每加 1 个新流程就开新文件）。

## Testing Decisions

- 框架：pytest + pytest-cov。
- 覆盖策略：纯函数（topological_sort、_master_template_sheet、json_utils.parse_json、build_*_prompt）测输入→输出；带 MCP 的（StrategicContextBuilder.build）用 monkeypatch 替换 `idste.sp_data/sp_data_menu/sp_dimension` 三个函数。
- 不测的：LLM 真调用（成本+不确定性，留手动冒烟）、Streamlit UI（session_state 复杂）、PptxBuilder 渲染结果（视觉）。
- "好测试"标准：测外部行为（输入→输出/异常），不耦合到内部实现细节。
- 参考：`STATUS.md` 列的 import 探烟，照搬成 `tests/smoke/test_imports.py`。

## Out of Scope

- 新功能 / 新 sheet / 新数据源接入。
- 切换 LLM provider（`models/llm.py` 重写）。
- 异步化（`docs/superpowers/specs/...` 提到，本轮不做）。
- 升级 openpyxl / python-pptx / streamlit 主版本。
- 重做 PPT 主题（用户说"等 PPT 模板"）。
- 把 iDSTE MCP 替换为自家服务。
- 国际化（界面仍中文）。
- 把 `prompts/*.py` 改成独立 .md/.txt 模板文件（暂保留 inline）。
- GitLab push — 本计划只覆盖本地代码整理；推送另议。

## Further Notes

- **执行顺序**：PR1 → PR2 → PR3 → PR4 → PR5 → PR6。每个 PR 独立可 merge。
- **安全警告**：iDSTE 与 GitLab 共用弱密码 `<iDSTE_PASSWORD>`（虽本计划不存此值）。建议 PR 全部落地后用户立即在两个平台轮换。
- **GitLab 推送**：本计划不覆盖。计划完成后会单独问用户 GitLab repo URL（之前给的 `http://192.168.1.15:8090/pages/viewpage.action?pageId=7503913` 是 Confluence 页面，不是 git remote URL，需要用户提供 `http(s)://.../group/project.git` 形式）。
- **`views/ui_theme.py` 612 行** 是最大债务，拆分最容易引入 CSS 渲染 regression → 放 PR6 末尾，做完跑一次手工截图核对。
- **`controllers/ppt_controller.py:10` 坏 import** 是当前唯一会阻断 import 的真 bug，**PR2 第一提交修**，优先级最高。
- **`.env` 从未入历史**：用户切换 MCP 连接方式时可直接 `rm .env`，无需 `git filter-repo`。`.env.example` 保留作模板。
- **本计划文档本身**：`docs/REFACTOR_CODEX_2026.md`，跟 `PLAN.md` / `STATUS.md` 同级。
