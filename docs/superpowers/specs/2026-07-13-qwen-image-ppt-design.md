# Qwen-Image-2512 集成到 SP Agent PPT 流程 — 设计文档

> 日期：2026-07-13
> 状态：✅ 设计完成，待用户 review
> 项目：SP 战略规划智能体（D:\memory）

---

## 一、目标

把 Qwen-Image-2512 图片生成模型（`http://10.8.0.26:6005/v1/images/generations`）集成到现有 PPT 生成流程，让演示文稿有 AI 生成的配图（cover、section divider、conclusion 必出，其他页可选），同时升级 theme 配色与 QA 工具链。

**v2 增量**：在 Excel 流程中加入 (a) DuckDuckGo 联网搜索补全行业/宏观/对手/份额数据，以 sp_data 为主；(b) sheet→tool hints 强制 LLM 必须先调 sp_data；(c) 工具调用计数（方案 A）监控每张 sheet 是否真的取了数。

---

## 二、范围

**包括**：
- Qwen-Image 客户端 + 图片生成 pipeline
- slide-spec 新增 `image` 字段（zone 9 宫格 + aspect + style + required）
- theme.json 升级到 Midnight Executive 配色
- 接入 `pptx` skill 的 thumbnail.py + soffice.py 做 QA
- 缓存、错误降级、UI 集成
- **v2 增量**：
  - DuckDuckGo 联网搜索（DuckDuckGoClient）作为 sp_data 的补充
  - slide-spec sheet→tool hints 字段（强制 LLM 必须先调 sp_data）
  - 工具调用计数（方案 A）+ UI 状态标签
  - agent.py / prompts.py 增量

**不包括**：
- 重构 render.js 的整体架构（保持现有 pptxgenjs 模式）
- i18n（保留中文）
- 性能压测
- 跨平台（仅 Windows + Python 3 + Node）

---

## 三、架构

```
┌─────────────────────────────────────────────────────────┐
│ Streamlit (app.py) — Tab 2 PPT 流程                     │
└──────────┬──────────────────────────────────────────────┘
           │ 自然语言 + xlsx
           ▼
┌─────────────────────────────────────────────────────────┐
│ agent.generate_pptx_from_xlsx()                        │
│   ├─ xlsx_reader.read_template() → xlsx_data           │
│   ├─ prompts.build_slide_spec_from_xlsx_prompt()        │
│   ├─ llm.chat() → slide_spec (含 image 字段)           │
│   ├─ 【新】image_pipeline.augment_slide_spec()          │
│   │     ├─ 遍历每页，若需图则调 Qwen-Image              │
│   │     ├─ 重试 2 次，失败则跳过                       │
│   │     └─ 写本地缓存 cache/images/                    │
│   ├─ pptx_builder.build_pptx() → 调 render.js          │
│   │     (render.js 按 zone/aspect 贴图)                │
│   └─ (可选) qa.run() → thumbnail + PDF + 视觉检查     │
└──────────┬──────────────────────────────────────────────┘
           ▼
       output/<ts>_<intent>_slides.pptx
       output/qa/grid.jpg, output/qa/slide-XX.jpg (可选)
```

---

## 四、组件清单

| 组件 | 路径 | 状态 | 行数估算 | 职责 |
|---|---|---|---|---|
| `image_client.py` | 新 | TODO | ~80 | `QwenImageClient` 类：封装 `/v1/images/generations` HTTP 调用 + 鉴权 |
| `websearch.py` | 新 | TODO | ~50 | `DuckDuckGoClient` 类：封装 duckduckgo-search 包，作为 sp_data 的补充 |
| `image_pipeline.py` | 新 | TODO | ~120 | `augment_slide_spec()`：遍历 slides、cache 命中检查、调图、重试、required/fallback 决策 |
| `theme.json` | 改 | TODO | +30% | 增 9 宫格 zone 坐标表 + Midnight Executive 配色 + 中文字体 |
| `slide_spec_schema.json` | 改 | TODO | +30 行 | 加 `image` 字段定义（zone 1-9 enum, aspect enum, style enum, required bool）|
| `render.js` | 改 | TODO | +60 行 | 新增 `applyImageZone(slide, imgMeta, theme)`：按 zone/aspect 贴图 |
| `qa.py` | 新 | TODO | ~60 | `run(pptx_path, output_dir)`：调 skill 的 thumbnail.py + soffice.py |
| `agent.py` | 改 | TODO | +20 行 | `generate_pptx_from_xlsx` 加 `image_client=None`、`enable_qa=False` 参数 |
| `prompts.py` | 改 | TODO | +50 行 | slide-spec prompt 增 "image 字段规则" 段 |
| `app.py` | 改 | TODO | +30 行 | Tab 2 加 "启用图片生成" / "生成后做 QA" checkbox + QA 展示区 |
| `.env` / `.env.example` | 改 | TODO | +5 行 | 加 `QWEN_IMAGE_URL`、`QWEN_IMAGE_MODEL`、`QWEN_IMAGE_TOKEN`、`IMAGE_CACHE_DIR` |

---

## 五、数据模型

### slide-spec image 字段 schema
```json
{
  "layout": "section",
  "title": "市场洞察",
  "image": {
    "prompt": "modern city skyline at dawn, deep blue, navy, ice blue accent",
    "zone": 9,
    "aspect": "16:9",
    "style": "minimal",
    "required": true
  }
}
```

| 字段 | 类型 | 必填 | 含义 |
|---|---|---|---|
| `prompt` | string | ✅ | 喂给 Qwen-Image 的英文/中文 prompt，描述要生成的图 |
| `zone` | int 1-9 | ✅ | 9 宫格位置（numpad 布局：1=左下，5=中，9=右上）|
| `aspect` | enum | ✅ | `16:9` / `4:3` / `1:1` / `3:4`，决定 image 与 zone 的适配方式 |
| `style` | enum | ✅ | `minimal`（极简）/`photographic`（实景）/`illustration`（插画）/`diagram`（结构图）|
| `required` | bool | ✅ | `true` = 重试 2 次还失败就 raise 中断；`false` = 失败丢弃该图，slide 改纯文字 |

### sheet→tool hints（v2 新增）
slide-spec 的每个 sheet 对象可以加一个可选的 `tool_hints` 字段，给 LLM 提示"这张 sheet 必须先调哪些 sp_data 表"：

```json
{
  "layout": "bullets",
  "title": "2.6 整体对手分析",
  "tool_hints": ["对手分析", "市场份额"],
  "required_tool_calls": 6
}
```

| 字段 | 类型 | 含义 |
|---|---|---|
| `tool_hints` | list[string] | 提示 LLM 该 sheet 涉及的工具调用关键词（sp_data 内的表 key 或 DuckDuckGo 搜索关键词）|
| `required_tool_calls` | int | 期望的最少工具调用次数，agent 用作 warn 阈值（默认 1）|

#### 按 sheet 类别的 tool_hints 预设
| sheet 名 | tool_hints | required_tool_calls | 备注 |
|---|---|---|---|
| 1.1 业绩差距分析 | ["业绩差距", "责任人"] | 2 | 业绩数字 + 责任人 |
| 1.2 机会差距分析 | ["机会差距", "战略机会"] | 2 | 数字 + 战略机会 |
| 2.1 宏观环境分析 | ["PESTEL", "宏观", "web_search"] | 4 | PESTEL 主 + 联网补政策新闻 |
| 2.2 行业趋势分析 | ["行业趋势", "web_search"] | 3 | iDSTE 数据 + 联网补行业动态 |
| 2.3 市场容量分析 | ["市场容量", "TAM", "web_search"] | 3 | 主 + 联网补最新市场报告 |
| 2.4 客户购买行为 | ["客户行为", "细分市场"] | 2 | 客户数据 |
| 2.5 业务划分分析 | ["业务划分", "BU/PL"] | 2 | 业务单位 |
| 2.6 整体对手分析 | ["对手分析", "市场份额", "web_search"] | 6 | 6 个对手 + 联网补最新动态 |
| 2.7 主要对手分析 | ["主要对手", "对比", "web_search"] | 5 | 对手对比 |
| 2.8 雷达图分析 | ["雷达图", "能力评估"] | 1 | type2 redirect |
| 2.9 自身分析 | ["自身能力"] | 1 | type2 |
| 2.10 五看分析 | ["五看", "行业"] | 1 | type2 |
| 2.11 SWOT分析 | ["SWOT"] | 1 | type2 |
| 2.12 TOPN 行业 | ["TOPN", "行业排名"] | 1 | type2 |
| 2.13 行业占有率 | ["占有率", "市场份额", "web_search"] | 2 | type2 + 联网 |
| 3.1 使命愿景 | ["使命愿景"] | 1 | 战略意图 |
| 3.2 战略地图 | ["战略地图"] | 1 | type2 |
| 3.3 KPI | ["KPI"] | 1 | 业绩指标 |
| 4.1 H123 | ["H123", "热点热难点热点机会"] | 1 | 创新焦点 |
| 4.2 创新重点 | ["创新重点"] | 1 | |
| 4.3 战略专题 | ["战略专题", "关键问题"] | 1 | |
| 4.4 新兴机会 | ["新兴机会", "web_search"] | 2 | iDSTE + 联网补新兴行业 |
| 5.1 竞争战略 | ["竞争战略"] | 1 | |
| 5.2 中央平台 | ["中央平台"] | 1 | |
| 5.3 业务设计 | ["业务设计"] | 1 | |
| 5.4 主要风险 | ["风险", "web_search"] | 2 | 风险 + 联网补政策风险 |
| 6.1 战略举措 | ["战略举措"] | 1 | |
| 6.2 年度目标 | ["年度目标"] | 1 | |
| 6.3 重点项目 | ["重点项目"] | 1 | |
| 7.1 组织架构 | ["组织架构"] | 1 | |
| 7.2 流程变革 | ["流程变革"] | 1 | |
| 8.1 人才盘点 | ["人才盘点"] | 1 | |
| 8.2 人才规划 | ["人才规划"] | 1 | |
| 9.1 企业文化 | ["企业文化"] | 1 | |
| 9.2 其他资源 | ["其他资源"] | 1 | |
| 10.1 财务预测 | ["财务预测"] | 1 | |

> LLM 看到 tool_hints 时**必须**先调对应工具才能填表。LLM 可以调多次（一张 sheet 多行就多次调）。

### Qwen-Image API 请求/响应
```
POST {QWEN_IMAGE_URL}/v1/images/generations
Headers:
  XSRF-TOKEN: {QWEN_IMAGE_TOKEN}
  Content-Type: application/json
Body:
  {
    "model": "Qwen-Image-2512",
    "prompt": "...",
    "n": 1,
    "size": "1024x1024"  // 或 1280x720
  }
Response:
  { "data": [{ "url": "http://...png" }] }
```
→ 客户端下载 url 返回的 PNG bytes。

### 缓存目录结构
```
cache/images/
  ├── {key}.png      # PNG bytes
  └── {key}.json     # {prompt, style, created_at, latency_ms, from_url}
```
`key = sha256(f"{prompt}|{style}|{size}").hexdigest()[:16]`

---

## 六、数据流

### 图片生成流程
```
slide_spec (chat LLM 输出, 13 页)
   │
   ▼
image_pipeline.augment_slide_spec(slide_spec, client, cache_dir, verbose)
   │
   │ for each slide:
   │   1. if slide.image is None → skip
   │   2. if layout ∈ {cover, section, conclusion} and image is None:
   │        自动注入 image = {prompt: "professional minimal illustration for a presentation section titled <title>, Midnight Executive palette, no text", zone: 5, aspect: 16:9, style: minimal, required: true}
   │   3. if layout ∈ {cover, section, conclusion} and image.required is missing:
   │        强制 required = true
   │   4. cache_key = sha256(prompt|style|size).hexdigest()[:16]
   │   5. if cache_key in cache_dir:
   │        copy to slide.image.local_path = "cache/images/{key}.png"
   │   6. else:
   │        for attempt in [1, 2, 3]:
   │          try: client.generate(prompt, style, size) → PNG bytes
   │          except (Timeout, HTTP5xx): sleep(2^attempt); continue
   │        on success: save to cache_dir/{key}.png + .json, set slide.image.local_path
   │        on failure:
   │          if image.required → raise
   │          else → log warn, delete slide.image
   │
   ▼
augmented slide_spec (含 local_path)
   │
   ▼
pptx_builder.build_pptx() → 调 node render.js
   │ for each slide:
   │   if slide.image.local_path: applyImageZone(slide, theme)
   ▼
output.pptx
```

### 关键设计原则
- **决策层和生成层分离**：chat LLM 不知道 cache/重试细节，专注给 zone/aspect/style
- **layout 兜底 required**：cover/section/conclusion 强制 required=true，LLM 漏给图也能保证视觉完整
- **cache key 与 deck 解耦**：key 不含 xlsx/user_request，跨 deck 复用图
- **DI 一致**：image_client / image_pipeline / qa 都走参数注入

---

## 七、错误处理

| 错误源 | 触发条件 | 行为 | 用户感知 |
|---|---|---|---|
| `QWEN_IMAGE_URL` 未配置 | 启动时检测 | raise `ValueError` | 启动直接报错 |
| Qwen-Image 超时 | `requests.Timeout` | 重试 2 次（间隔 1s/3s 指数退避）| UI 进度条更新，日志 warn |
| Qwen-Image 5xx | 500/502/503 | 重试 2 次同上 | 同上 |
| Qwen-Image 4xx | 400/401/403/404 | 不重试，raise | 鉴权/参数错误，立刻发现 |
| `required=true` 重试用尽 | 上述任何错误 | raise → 中断 PPT 生成 | UI 弹错，按钮可重试 |
| `required=false` 重试用尽 | 上述任何错误 | 丢弃该页 image，slide 纯文字 | 日志 warn，PPT 仍生成 |
| 缓存目录不可写 | 写 PNG 失败 | 跳过缓存，继续生成 | 日志 warn，不阻断 |
| `prompt` 含敏感词 | Qwen-Image 返回 400 | 不重试，跳过 | 日志 warn，丢弃该图 |
| render.js 加载本地图片失败 | 文件不存在/损坏 | 跳过该图，slide 纯文字 | 日志 warn，PPT 仍生成 |

### 重试实现（tenacity 风格）
```python
@retry(stop=stop_after_attempt(3),
       wait=wait_exponential(multiplier=1, min=1, max=10),
       retry=retry_if_exception_type((Timeout, HTTP5xx)))
def _call_qwen_image(self, prompt: str, style: str, size: str) -> bytes:
    return requests.post(self.url, json=..., headers=..., timeout=60).content
```

---

## 八、theme.json 升级（Midnight Executive）

### 配色
| 角色 | 十六进制 | 用途 |
|---|---|---|
| `primary` | `1E2761` | 海军蓝，主标题/强调 |
| `secondary` | `CADCFC` | 冰蓝，副标题/次要元素 |
| `accent` | `FFFFFF` | 白，高亮文字/图标 |
| `text_dark` | `0A0F2C` | 深海军（正文） |
| `text_muted` | `5A6A8A` | 灰蓝（说明/脚注） |
| `bg_dark` | `0E1A40` | cover/section 背景 |
| `bg_light` | `F5F7FB` | content 页背景 |
| `border` | `8DA3C7` | 卡片/分割线 |
| `warn` | `F96167` | 风险/差距警示 |
| `ok` | `97BC62` | 完成/正面 |

### 字体
- `family_header` = `Microsoft YaHei`（中文标题）
- `family_body` = `Microsoft YaHei`（中文正文）
- `family_data` = `Consolas`（数字）

### 字号
| 元素 | pt |
|---|---|
| hero | 60 |
| cover | 44 |
| title | 32 |
| subtitle | 20 |
| body | 18 |
| caption | 12 |
| big_stat | 72 |

### 9 宫格 zone 坐标（slideW=13.33, slideH=7.5, margin=0.5, gutter=0.3）
| zone | x | y | w | h |
|---|---|---|---|---|
| 1 (左下) | 0.5 | 4.5 | 4.0 | 2.5 |
| 2 (中下) | 4.5 | 4.5 | 4.0 | 2.5 |
| 3 (右下) | 8.5 | 4.5 | 4.0 | 2.5 |
| 4 (左中) | 0.5 | 2.0 | 4.0 | 2.5 |
| 5 (居中) | 4.5 | 2.0 | 4.0 | 2.5 |
| 6 (右中) | 8.5 | 2.0 | 4.0 | 2.5 |
| 7 (左上) | 0.5 | 0.5 | 4.0 | 1.5 |
| 8 (中上) | 4.5 | 0.5 | 4.0 | 1.5 |
| 9 (右上) | 8.5 | 0.5 | 4.0 | 1.5 |

### aspect → fit 映射
| aspect | 缩放规则 |
|---|---|
| `16:9` | 横向铺满 zone，垂直居中 |
| `4:3` | 横向填 zone，垂直按 4:3 算 |
| `1:1` | zone 内取方形最大居中 |
| `3:4` | 纵向填 zone，水平按 3:4 算 |

---

## 九、QA 工具链

### 触发
`agent.generate_pptx_from_xlsx(..., enable_qa=False)` —— 默认关闭。
UI Tab 2 加 checkbox "生成后做视觉 QA" —— 勾上才跑。

### 流程
```
qa.run(pptx_path, output_dir, verbose)
   ├─ 1) subprocess: python C:\...\skills\pptx\scripts\thumbnail.py <pptx>
   │     → output_dir/qa_thumbs/grid.jpg
   ├─ 2) subprocess: python C:\...\skills\pptx\scripts\office\soffice.py --headless --convert-to pdf <pptx>
   │     → output_dir/qa_pdf/output.pdf
   │     → subprocess: pdftoppm -jpeg -r 100 output.pdf slide
   │     → output_dir/qa_pdf/slide-XX.jpg
   ├─ 3) (可选) subagent 读 jpg，套 SKILL.md checklist 检图
   │     → issues: [{slide, type, desc}]
   └─ 4) 返回 {thumbs_path, pdf_path, slide_images, issues, ok}
```

### 失败兜底
- LibreOffice 没装 → 跳 PDF，单页 jpg 也跳过
- pdftoppm 没装 → 跳单页图
- subagent 视觉检查失败 → 跳过，issues 为空

### UI 展示
- grid.jpg 用 `st.image` 嵌在 Tab 2 下方
- 单页 jpg 列出文件名，可逐张查看
- issues 列表用 `st.json` 展示
- "下载 QA 报告" 按钮打包 json + pdf + jpg

---

## 十、配置（.env 新增项）

```bash
# Qwen-Image 图片生成（新增）
QWEN_IMAGE_URL=http://10.8.0.26:6005
QWEN_IMAGE_MODEL=Qwen-Image-2512
QWEN_IMAGE_TOKEN=<your-token>
IMAGE_CACHE_DIR=cache/images
IMAGE_CACHE_MAX_MB=500
```

---

## 十一、易扩展性设计

- **DI 友好**：`generate_pptx_from_xlsx(image_client=None, image_pipeline=None, qa_runner=None, ...)` 全部走参数注入，方便 mock / A/B 测试
- **配置化**：所有可调参数（URL、token、cache 目录、size、retry 数）走 .env
- **Schema 驱动**：slide-spec 字段定义在 `slide_spec_schema.json`，render.js 和 prompts.py 都从 schema 读
- **单一真相源**：
  - 颜色/字体/坐标 → `theme.json`（render.js + theme 引用方共享）
  - slide-spec 字段 → `slide_spec_schema.json`（render + prompt 共享）
  - xlsx 列结构 → `xlsx_reader.extract_schema()`（prompts 动态生成）
- **handler dict**：`render.js` 的 layout handler / 9 宫格 zone 坐标都用 dict 映射，新加 layout/zone 加表项即可
- **新需求扩展点**：
  - 加新 layout → 改 `slide_spec_schema.json` + `render.js` 的 HANDLERS + `prompts.py` 文档
  - 加新配色 → 改 `theme.json` 即可，render 不动
  - 换图片模型 → 实现新 `ImageClient`（如 `StableDiffusionClient`），注入 `image_client` 参数

---

## 十二、测试策略

### 验证层次
| 层 | 工具 | 范围 | 通过条件 |
|---|---|---|---|
| L1 单元 | 临时 `assert` + `__main__` 段 | image_client 的请求/响应/重试逻辑；image_pipeline 的 cache 命中、required/fallback 行为 | 调一次 print 结果对 |
| L2 集成（mock） | mock Qwen-Image 返回固定 PNG bytes | image_pipeline 全流程：cache 命中/未命中/重试用尽/必需失败/可选失败 | 5 个 case 路径都通 |
| L3 端到端（真） | 跑 `python agent.py "分析2025年公司SP战略规划完成度"`，再调 PPT | 完整：xlsx → slide-spec → Qwen-Image 3-5 张 → 渲染 → QA | ① xlsx 内容正确 ② pptx 能开 ③ grid.jpg 无错位 ④ 关键页有图 |
| L4 视觉 QA | subagent 套 SKILL.md checklist 检图 | 重叠/溢出/对比度/留白 | issues ≤ 3 minor，无 major |

### 验证清单（手工）
1. `python image_client.py` —— 调 1 次 Qwen-Image，存图
2. `python image_pipeline.py` —— 用 mock slide-spec 跑 5 个 case
3. `python agent.py "分析2025年公司SP战略规划完成度"` —— 端到端
4. 打开 grid.jpg：检查 13 页布局
5. 打开 1-2 张关键页 jpg：检查图片位置
6. 故意停掉网络 / 改 .env 错 token：验证 required=true 时报错路径
7. 删 `cache/images/` 重跑：验证 LRU 限制

### v2 新增验证点
- LLM 在 tool_hints 提示下，**是否真的**调了 sp_data？ 跑 3 个 case：
  - 必调 sheet（1.1 业绩差距）→ 期望 sp_data ≥ 2
  - 必调+联网 sheet（2.1 宏观）→ 期望 sp_data ≥ 2 + web_search ≥ 1
  - 触发 warn case：故意改成"直接写"的需求 → 期望 LLM 仍调工具
- 联网失败场景：拔网 / 关 VPN → 期望 web_search 跳过、sp_data 正常

### 不做的
- ❌ 写正式 pytest（`__main__` 段够用）
- ❌ 性能压测（一次 1-2 个 deck，不构成瓶颈）
- ❌ 跨平台测试

---

## 十三、风险与预案

| 风险 | 预案 |
|---|---|
| Qwen-Image 返回图分辨率太小 | 客户端固定 `size: "1024x1024"` 或 `1280x720` |
| Qwen-Image 生成内容跑题 | slide-spec prompt 强调"色调与 {palette} 一致，中国战略规划场景" |
| render.js 加载本地图片失败 | 兜底：图片缺失时只渲染文字 |
| cache 目录跨用户冲突 | 路径用 `cache/images/{session_id}/...`，session_id 取 user_input 的 hash |
| 9 宫格 zone 与现有 layout 冲突 | `applyImageZone` 后置调用，若 zone 已被 title/bullet 占据，自动缩小图（缩小到 0.8x 居中）|

---

## 十四、交付物（实现完成后）

- [ ] `image_client.py`、`image_pipeline.py`、`qa.py` 3 个新文件
- [ ] `theme.json`、`slide_spec_schema.json` 更新
- [ ] `render.js` 加 `applyImageZone` 函数
- [ ] `agent.py`、`prompts.py`、`app.py` 增量更新
- [ ] `.env` / `.env.example` 加 4 行
- [ ] 1 张端到端生成的 xlsx + 1 张 pptx + 1 张 grid.jpg 验证产出
- [ ] STATUS.md 更新 v3 架构
- [ ] **v2 增量交付物**：
  - `websearch.py` + DuckDuckGo 集成
  - slide-spec schema 加 `tool_hints` / `required_tool_calls` 字段 + 36 张 sheet 预设表
  - `agent.py` 加 tool_call_stats 计数 + UI 状态标签
  - `prompts.py` XLSX_DATA_PROMPT 加 3 条硬规则
  - .env 加 4 行 websearch 配置
  - requirements.txt 加 duckduckgo-search 包
  - 验证 1 张端到端 xlsx，确认 tool_call_stats 全绿

---

## 十五、v2 增量：联网搜索 + sp_data 强约束 + 工具调用监控

### 15.1 DuckDuckGo 联网搜索

#### 客户端（websearch.py）
```python
class DuckDuckGoClient:
    def __init__(self, max_results: int = 5, timeout: int = 30):
        from duckduckgo_search import DDGS
        self.ddgs = DDGS()
        self.max_results = max_results
        self.timeout = timeout

    def search(self, query: str) -> list[dict]:
        # 返回 [{title, snippet, url}, ...]
        return list(self.ddgs.text(query, max_results=self.max_results))
```

#### 注册为 LLM 工具
- 加到 `idste.TOOL_MAP` 或新 `websearch.TOOL_MAP`
- tool schema：
```json
{
  "type": "function",
  "function": {
    "name": "web_search",
    "description": "在公网搜索行业、宏观、竞争对手、市场份额、政策等实时信息。结果质量次于 sp_data，仅在 sp_data 不足时使用。",
    "parameters": {
      "type": "object",
      "properties": {
        "query": {"type": "string", "description": "搜索关键词，建议中文"}
      },
      "required": ["query"]
    }
  }
}
```

#### sp_data vs web_search 优先级规则
- **sp_data 为主**：涉及业绩/KPI/责任人/部门数据 → 只用 sp_data
- **web_search 补**：sp_data 没覆盖到的新兴行业、政策新闻、宏观趋势、竞品动态、市场份额
- **同 sheet 拼接**：1.1 业绩差距（sp_data）+ 该 sheet 行业背景（web_search）→ 跨源拼接

#### 网络失败兜底
- `requests.ConnectionError` / `duckduckgo.exceptions` → 跳过该次搜索，agent 继续跑
- 公司内网禁网 → agent 启动时检测一次 `web_search("test")`，失败就 warn 但不阻断（sp_data 仍可用）

### 15.2 sp_data 强约束（防 LLM 编数）

#### 触发 sheet（必须先调 sp_data，禁止直接写）
- 1.1 业绩差距 / 1.2 机会差距 / 3.3 KPI / 6.2 年度目标 / 10.1 财务预测（业绩数字必须真实）
- 2.6 整体对手 / 2.7 主要对手（对手名单必须真实）
- 5.4 主要风险（必须从 iDSTE 风险库取）

#### 软提示 sheet（sp_data 优先，不足可补 web_search）
- 2.1 宏观环境 / 2.2 行业趋势 / 2.3 市场容量（iDSTE 数据 + 联网补最新）
- 2.4 客户购买 / 2.5 业务划分（iDSTE 为主，联网补客户洞察）
- 4.4 新兴机会 / 5.4 主要风险（iDSTE + 联网补政策风险）

#### prompts.py 新增 3 条硬规则（写入 XLSX_DATA_PROMPT）
```
10. **强制 sp_data**：tool_hints 列表里有 "sp_data" 的 sheet，**每一行**的数据
    都必须来自 sp_data 工具返回，禁止凭印象/行业常识编写。
    数字、姓名、部门、金额——任何具体事实都需 sp_data 支撑。
11. **软提示 web_search**：tool_hints 里有 "web_search" 的 sheet，先 sp_data
    拿结构化数据，再用 web_search 补背景信息/最新动态。sp_data 为主。
12. **type2 redirect 处理**：sp_data 返回 view_url 时，把 url 复制到对应
    单元格（如"参考链接"列），不要试图自己生成图表。
```

### 15.3 工具调用计数（方案 A 监控）

#### 实现位置
- `agent.py.generate_xlsx_data()` 内部维护 `tool_call_stats: dict[sheet_name, dict[tool_name, count]]`
- 跑完返回元信息 `{intent, xlsx_data, tool_call_stats}`

#### 计数逻辑
```python
def _record_tool_call(stats, sheet_name, tool_name):
    stats.setdefault(sheet_name, {}).setdefault(tool_name, 0)
    stats[sheet_name][tool_name] += 1
```

在 `llm.run_agent_loop` 的工具调用回调里挂这个函数（需 llm.py 配合暴露回调或改 hook）。

#### 监控输出
```python
{
  "1.1 业绩差距分析": {"sp_data": 4, "web_search": 0},
  "2.1 宏观环境分析": {"sp_data": 2, "web_search": 2},
  "2.6 整体对手分析": {"sp_data": 6, "web_search": 1},
  "5.4 主要风险分析": {"sp_data": 1, "web_search": 0}  # <1 触发 warn
}
```

#### Warn 规则
- sp_data 数 = 0 且 sheet 属于"强制 sp_data"清单 → **ERROR 级 warn**（UI 红字）
- sp_data 数 < required_tool_calls → **WARN 级**（UI 黄字）
- sp_data 数 ≥ required_tool_calls → **OK**（UI 绿字）

#### UI 展示（app.py Tab 1）
每张 sheet 输出后，在 st.expander 里显示：
```
✅ 2.1 宏观环境分析: sp_data × 2, web_search × 2
⚠️ 5.4 主要风险分析: sp_data × 1（建议 ≥ 2）
❌ 1.1 业绩差距分析: sp_data × 0（必须取数）
```

### 15.4 数据流变化（v2）

```
                  ┌─────────────┐
                  │ sp_data()   │ ←  iDSTE MCP（公司内网）
                  │  + 其它 4 个│
                  └──────┬──────┘
                         │ 主要数据源
                         ▼
chat LLM  ◀────────  ┌──────────────┐
   │                 │ web_search() │ ← DuckDuckGo（公网，补 sp_data 不足）
   │ tool_calls      └──────────────┘
   ▼
JSON 输出
   │
   ▼
xlsx_exporter → 模板填充
   │
   ▼
UI 显示 tool_call_stats（绿/黄/红）
```

### 15.5 .env 新增项（v2）
```bash
# 联网搜索（新增）
WEBSEARCH_ENABLED=true
WEBSEARCH_PROVIDER=duckduckgo
WEBSEARCH_MAX_RESULTS=5
WEBSEARCH_TIMEOUT=30
```

### 15.6 易扩展性预留
- 新搜索源：实现 `TavilyClient` / `BingClient`，注册到 `websearch.TOOL_MAP` 即可
- 新监控维度：在 `tool_call_stats` 字典里加 key（如 `total_latency_ms`）
- 强制 sheet 清单：抽到 `xlsx_reader.REQUIRED_SP_DATA_SHEETS = {...}` 配置

---
## 十六、后续可能方向（不在本次范围）

- 视频封面图生成（每张 deck 一张缩略图）
- 多语言图片 prompt（i18n）
- A/B 测试不同 style 的视觉效果
- 图片版权水印（公司 logo 自动叠加）
- 离线图片库（可选用历史生成的图，标记收藏）
