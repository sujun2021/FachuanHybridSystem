# CLAUDE.md — FachuanHybridSystem (法穿 AI Copilot)

## 项目概述

法穿 (Fachuan) 是一套面向中国律师/律所的开源 AI 法律实务管理系统，由一线执业律师 (Lawyer-ray) 主导开发。核心理念："数据录入一次，自动流转全系统"——消除律师在内部 OA、法院平台之间的重复数据录入。

当前版本: **v26.52.3** | 主仓库: `github.com/Lawyer-ray/FachuanHybridSystem`

---

## 技术栈

| 层 | 技术 |
|---|---|
| **前端** | React 19 + TypeScript 5.9 + Vite 7 + Tailwind CSS 4 + shadcn/ui (Radix) + TanStack React Query + Zustand + React Router 7 + Framer Motion |
| **后端** | Python 3.12 + Django 6.0 + Django Ninja (REST API) + Django Q2 (异步任务) + Django Channels (WebSocket) + Uvicorn |
| **数据库** | PostgreSQL 16 + Valkey 8 (Redis 兼容) |
| **工作流引擎** | Temporal.io (持久化编排, 信号/等待/重试) |
| **AI/LLM** | OpenAI 兼容 API + Ollama 本地模型 + Pydantic AI + MCP 协议 |
| **Java 服务** | Spring Boot 3.5 + Java 25 + Apache POI 5.5 / poi-tl 1.12 (Word 文书生成) |
| **浏览器自动化** | CloakBrowser (C++ 级反检测引擎) + Playwright (页面操控) |
| **OCR/文档处理** | RapidOCR + ddddocr + python-docx + docxtpl + ReportLab + pdfplumber + PyMuPDF |
| **部署** | Docker Compose (Postgres + Valkey + Web + QCluster) |
| **CI** | GitHub Actions + Ruff + Black + MyPy + Pytest (1954+ tests) |

---

## 仓库结构

```
FachuanHybridSystem/
├── backend/                     # Django 单体 + MCP Server
│   ├── apiSystem/apiSystem/     # Django 项目根 (settings, urls, asgi/wsgi)
│   ├── apps/                    # ~33 个 Django App (见下方详解)
│   ├── mcp_server/              # MCP 协议服务器 (200+ 工具)
│   ├── plugins/                 # Git 子模块 (FachuanPlugins)
│   ├── pyproject.toml           # uv 管理的 Python 依赖
│   └── Dockerfile
├── frontend/                    # React SPA
│   ├── src/
│   │   ├── api/                 # API 客户端层
│   │   ├── components/          # 共享 UI (shadcn/ui + 业务组件)
│   │   ├── features/            # 功能模块 (auth, workflow, workbench, cases...)
│   │   ├── pages/               # 路由页面组件
│   │   ├── stores/              # Zustand 状态
│   │   ├── routes/              # React Router 配置
│   │   └── lib/                 # 工具库 (api.ts, token.ts, utils.ts)
│   └── package.json             # pnpm 管理
├── java-services/               # Spring Boot 微服务
│   ├── poi-service/             # Word 文书生成微服务
│   └── shared/                  # 公共模型和工具
├── changelog/                   # 版本变更日志
├── scripts/                     # 运维脚本
└── CLAUDE.md                    # 本文件
```

---

## 后端 App 架构 (backend/apps/)

### 核心业务 App

| App | 职责 |
|---|---|
| `core` | 基础设施: LLM 服务、浏览器公共服务、系统配置、任务调度 |
| `cases` | 案件管理: Case, CaseParty, CaseNumber, CaseMaterial, CaseLog, Grant |
| `contracts` | 合同管理: Contract, Payment, SupplementaryAgreement, 归档 |
| `client` | 当事人管理: Client, IdentityDoc, PropertyClue |
| `contacts` | 联系人管理 |
| `organization` | 组织架构: Lawfirm, Lawyer, Team, Credential |
| `documents` | 文书生成: 模板系统, 替换词, 起诉状/答辩状/授权委托书 |
| `evidence` | 证据管理: EvidenceList, EvidenceItem, 证据排列 |
| `finance` | 财务: LPR 利率, 利息计算 |
| `reminders` | 提醒系统 |

### 自动化 App

| App | 职责 |
|---|---|
| `automation` | 法院短信处理, GSXT 企业查询, 文件命名器, 文档处理器 |
| `oa_filing` | OA 立案: JTN 等律所 OA 系统自动填报 (Playwright) |
| `express_query` | 快递查询 (浏览器自动化) |
| `legal_research` | 类案检索: 威科先行 (Weike) 等法律数据库对接 |
| `enterprise_data` | 企业数据: 天眼查/企查查 API 集成 |

### AI & 工作流 App

| App | 职责 |
|---|---|
| `workflow` | **Temporal 工作流引擎**: 模板管理, 动态编排, MCP 工具调度 |
| `workbench` | AI 对话工作台: 多会话, 流式输出, 工具审批 |
| `litigation_ai` | 诉讼 AI 辅助 |
| `legal_solution` | 法律方案 |

### 文档处理 App

| App | 职责 |
|---|---|
| `doc_convert` | 要素式文档格式转换 (40+ 法院格式) |
| `doc_converter` | 通用文档格式转换 |
| `document_recognition` | 文档识别 |
| `document_parsing` | 文档解析 |
| `pdf_splitting` | PDF 智能拆分 (OCR 页面分类) |
| `image_rotation` | 图片方向检测与旋转 |
| `invoice_recognition` | 发票识别 |
| `chat_records` | 聊天记录取证 (屏幕录制帧提取 + OCR) |
| `contract_review` | 合同审查 |

### 其他 App

| App | 职责 |
|---|---|
| `message_hub` | 消息中心: IMAP 收件箱聚合, 消息源管理 |
| `social_auth` | 社交登录 |
| `batch_printing` | 批量打印 |
| `evidence_sorting` | 证据排序 |
| `story_viz` | 故事可视化 |

---

## 核心设计模式

### 1. MCP 协议架构 (Model Context Protocol)

系统通过 MCP 协议暴露 **200+ 个工具函数**，使任何 AI Agent 可以通过自然语言调用系统功能。

```
backend/mcp_server/tools/
├── __init__.py          # 统一导出所有工具 (200+ 函数)
├── automation/          # 自动化工具 (法院短信, 立案, 保全, 文件命名...)
├── cases/               # 案件工具 (CRUD, 材料绑定, 诉讼费计算...)
├── clients/             # 当事人工具
├── contacts/            # 联系人工具
├── contracts/           # 合同工具 (含归档系统)
├── documents/           # 文书工具 (生成, 下载, 模板管理)
├── enterprise_data/     # 企业查询工具
├── finance/             # 财务工具 (LPR 利率)
├── legal_research/      # 法律检索工具
├── organization/        # 组织架构工具
├── reminders/           # 提醒工具
├── core/                # 核心工具 (LLM, 配置, 任务队列)
└── ...
```

每个 MCP 工具都是一个同步/异步 Python 函数，通过 `mcp_server/tools/__init__.py` 统一注册到 `__all__` 导出列表。

### 2. Temporal 工作流引擎

**架构层次:**

```
WorkflowTemplate (模板, DB)
    └── steps_schema: JSON 数组 (步骤定义)
         └── 每个步骤: {id, name, type, mcp_tool, config, timeout, retry_max, on_fail}

WorkflowRun (运行实例, DB)
    ├── 关联 Template + Case
    ├── temporal_workflow_id / temporal_run_id (Temporal 侧)
    └── StepExecution (步骤执行记录, DB)

Temporal Workflow (编排层)
    ├── SalesContractDisputeWorkflow (示例: 买卖合同纠纷)
    └── DynamicWorkflow (通用动态引擎 — 核心)
         └── 8 种步骤类型: activity, gate, wait, condition, delay, llm, http, code

Temporal Activity (执行层)
    ├── 内部 Activity (collect_case_facts, generate_complaint, ...)
    ├── MCP 工具调度 (execute_mcp_tool → 路由到对应 MCP 函数)
    └── 通用 Activity (generic_llm_call, generic_http_request, generic_code_exec, generic_delay)
```

**DynamicWorkflow 核心流程:**
1. 读取 Template 的 `steps_schema`
2. 逐步执行, 维护 `context` (包含所有步骤输出)
3. 每个步骤先判断类型:
   - `activity`: 优先走 MCP 工具 (`mcp_tool` 字段), 否则走内部 Activity
   - `gate`: 暂停等待人工审批信号 (`gate_approved`)
   - `wait`: 暂停等待外部事件 (复用 gate 信号机制)
   - `condition`: 求值条件表达式, 决定是否跳过后续步骤
   - `delay`: 延时等待
   - `llm`: 调用 LLM (system_prompt + user_prompt 模板, 支持 `{{变量}}` 插值)
   - `http`: 发送 HTTP 请求
   - `code`: 受限 Python 代码执行 (沙盒环境, 只暴露安全内置函数)
4. 失败处理: `on_fail` 支持 `abort` (终止) 或 `skip` (跳过继续)
5. 运行状态实时写回 Django DB (StepExecution + WorkflowRun)

**步骤注册表 (Step Registry):**
`backend/apps/workflow/api/step_registry.py` 定义了 9 个分类、40+ 可用步骤:
- 流程控制: gate, wait, condition, delay, llm, http, code
- 案件管理: collect_case_facts, list_case_materials, create_case_log
- 证据分析: analyze_single_evidence, summarize_evidence, suggest_arrangement
- 文书生成: generate_complaint, generate_defense, review_complaint_quality, download_litigation_document
- 诉讼流程: build_litigation_context, execute_court_filing, execute_guarantee, submit_court_sms
- 企业数据: search_companies, get_company_profile, get_company_risks
- 法律检索: create_research_task, check_law_references
- 通知提醒: create_reminder, send_message
- 自动化工具: auto_namer, process_document, convert_document, calculate_litigation_fee, calculate_interest

**MCP 工具路由表:**
`workflows.py` 中的 `MCP_TOOL_MAP` 将步骤 ID 映射到 MCP 工具名, `activities.py` 中的 `execute_mcp_tool` 通过路由表动态调用对应函数。

### 3. 浏览器自动化 (CloakBrowser + Playwright)

**架构:** `backend/apps/core/services/browser/`

```
create_browser() / create_browser_async()    ← 统一入口
    ├── BrowserProfile (配置档案)
    │   ├── default: CloakBrowser 原生启动
    │   ├── court_zxfw: 法院执行网 (反检测 + 慢速)
    │   ├── gsxt: 国家企业信用公示系统 (CDP 模式)
    │   └── express: 快递查询 (CDP 模式)
    ├── launcher.py (CloakBrowser launch 模式)
    ├── cdp_connector.py (CloakBrowser 异步启动模式)
    ├── anti_detection.py (指纹补丁)
    └── profiles.py (配置档案管理 + 环境变量覆盖)
```

**CloakBrowser 反检测体系:**
- **C++ 级反检测**: CloakBrowser 在 C++ 层处理 navigator.webdriver 隐藏、Canvas/WebGL 指纹伪装、WebRTC 泄漏防护等 (Linux 58 个补丁, macOS 26 个)
- **JS 层补充** (macOS): `anti_detection.py` 中的 `_MACOS_FINGERPRINT_JS` 补充 macOS 平台缺少的补丁:
  - `navigator.platform` → 'MacIntel'
  - `screen.width/height` → 1920x1080
  - Canvas 指纹随机化 (每次启动微小像素偏移)
  - `navigator.vendor`, `language`, `languages` 等属性
- **上下文配置**: viewport 1920x1080, locale zh-CN, timezone Asia/Shanghai, Accept-Language 头
- **登录态持久化**: `session_id` 参数启用 `user_data_dir` 持久化
- **环境变量覆盖**: `BROWSER_<NAME>_<KEY>` 格式 (如 `BROWSER_GSXT_CDP_URL`)

**GSXT 自动化流程 (gsxt_login_service.py):**
1. 优先尝试 HTTP 逆向登录 (`gsxt_reverse_login`, 需打码平台)
2. 回退到 CloakBrowser: 导航→填表→登录→等待验证码→搜索企业→点击详情→申请报告
3. 知道创宇 WAF 规避: 不能直接导航到详情页 URL, 必须在搜索页上 JS click 链接
4. 极验验证码: 轮询 `geetest_lock_success` 类名判断完成
5. 报告发送后启动邮件轮询定时任务

**OA 立案自动化 (oa_scripts/jtn/):**
- SSO 扫码登录 + Cookie 持久化 (`~/.fachuan/jtn_cookies.json`)
- 企业微信扫码 → 账号密码登录 → Cookie 缓存

**法律检索 (Weike):**
- 登录策略: Legacy 主页登录 → 检查认证状态 → 必要时 Modal 弹窗二次登录
- 用户协议自动勾选

### 4. 前端架构

**路由结构:**
- Auth 路由 (`/login`, `/register`): GuestGuard + AuthLayout
- Admin 路由 (`/admin/*`): AuthGuard + AdminLayout + 懒加载
- 工作流路由: `/admin/workflows` (运行列表), `/admin/workflows/templates` (模板管理), `/admin/workflows/templates/:id/edit` (可视化编辑器)

**API 层:**
- `lib/api.ts`: Ky HTTP 客户端, JWT 自动附加 + Token 刷新 + 401 重试
- `createFeatureApiClient(prefix)`: 功能模块级客户端工厂
- Vite dev proxy: `/api` → `http://127.0.0.1:8002`

**工作流前端:**
- **WorkflowDashboard**: 运行列表, 5 秒轮询活跃流程, 审批入口
- **TemplateEditorPage**: 三栏可视化编辑器
  - 左栏: 步骤面板 (按 registry 分类, 可搜索)
  - 中栏: 画布 (dnd-kit 拖拽排序, 连接线, 步骤卡片)
  - 右栏: 属性面板 (步骤配置, 超时/重试, gate/wait 特殊配置, JSON 高级配置)
- **StepNodeCard**: 8 种步骤类型各有独特配色 (activity=蓝, gate=琥珀, wait=紫, condition=绿, delay=灰, llm=粉紫, http=青, code=橙)

### 5. Java POI 服务

`java-services/poi-service/`: 独立 Spring Boot 微服务, 使用 Apache POI + poi-tl 模板引擎生成 Word 文书。前端/后端通过 HTTP 调用, 实现零手动编辑的合同和诉讼文书输出。

---

## 开发指南

### 环境准备

```bash
# 后端
cd backend && uv sync
python manage.py migrate
python manage.py runserver 0.0.0.0:8002

# 前端
cd frontend && pnpm install
pnpm dev

# Temporal Worker
python manage.py start_temporal_worker
```

### 关键约定

1. **Django Ninja** 做 REST API, 不用 DRF
2. **Django Q2** 做异步任务队列, 不用 Celery
3. **Pydantic Schema** (`ninja.Schema`) 做请求/响应验证
4. **MCP 工具函数** 是同步函数, 在 Temporal Activity 中用 `asyncio.to_thread()` 包装
5. **Temporal Workflow** 必须满足确定性约束: 不能调 `datetime.now()`, `random`, I/O, ORM; 所有"脏活"放 Activity
6. **CloakBrowser** 统一管理浏览器, 不直接用 Playwright launch; 通过 `create_browser()` / `create_browser_async()` 入口
7. **前端功能模块** 自包含: `features/<name>/` 包含 api.ts, types.ts, hooks/, components/
8. **React Query** 做数据缓存和轮询, Zustand 做客户端状态
9. **步骤注册表** 是前端编排器的数据源, 新增 MCP 工具后需同步更新 `step_registry.py`

### 测试

```bash
cd backend
pytest                           # 全量测试
pytest tests/ci/unit/            # 单元测试
pytest tests/ci/integration/     # 集成测试
pytest -k "workflow"             # 按关键词
```

### 代码规范

- **Python**: Ruff + Black + MyPy (strict)
- **前端**: ESLint + TypeScript strict
- **提交**: 使用中文 commit message, 格式 `feat/fix/refactor: 描述 (#PR号)`

---

## 扩展开发指南

### 新增 MCP 工具

1. 在 `mcp_server/tools/<module>/` 下创建函数
2. 在 `mcp_server/tools/__init__.py` 中导入并添加到 `__all__`
3. 如需在工作流中使用, 更新 `workflow/api/step_registry.py` 和 `workflow/temporal/workflows.py` 的 `MCP_TOOL_MAP`

### 新增工作流步骤类型

1. 在 `step_registry.py` 的 `STEP_CATEGORIES` 中添加步骤定义 (含 config_schema)
2. 在 `workflows.py` 的 `DynamicWorkflow._execute_step()` 中添加分支处理
3. 在 `activities.py` 中添加对应的 Temporal Activity
4. 前端 `StepNodeCard.tsx` 中添加新类型的配色方案

### 新增 Django App

1. `python manage.py startapp <name>` 在 `backend/apps/` 下
2. 在 `settings.py` 的 `INSTALLED_APPS` 中注册
3. 用 Django Ninja Router 创建 API
4. 在 `apiSystem/api.py` 中挂载路由
5. 创建对应的 MCP 工具 (如需 AI 调用)

### 新增前端功能模块

1. 在 `frontend/src/features/<name>/` 下创建: `api.ts`, `types.ts`, `hooks/`, `components/`
2. 在 `frontend/src/pages/dashboard/<name>/` 下创建页面组件
3. 在 `frontend/src/routes/index.tsx` 中添加懒加载路由
4. 在 `frontend/src/routes/paths.ts` 中添加路径常量

### 浏览器自动化开发

1. 使用 `create_browser(profile_name)` / `create_browser_async(profile_name)` 创建浏览器
2. 需要新 Profile 时在 `profiles.py` 的 `_PROFILES` 中注册
3. 验证码场景: 轮询 DOM 状态判断完成, 设置合理超时
4. WAF 规避: 通过 JS click 而非直接导航, 避免被拦截
5. 登录态持久化: 使用 `session_id` 参数
