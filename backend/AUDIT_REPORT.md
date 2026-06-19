# Backend 代码全面审查报告

**审查日期**: 2026-06-18
**审查范围**: `backend/` 全部 37 个 Django app + plugins + mcp_server + 测试结构 + 项目配置
**代码规模**: ~591,230 行 Python，3,665 个文件
**审查方式**: 18 个并行 AI agent，分 3 轮（模块审查 → 深度挖掘 → 专项分析）
**审查维度**: 代码逻辑、解耦拆分、文件夹结构、安全漏洞、异常处理、依赖关系、数据库性能、模型设计、API 设计、异步任务、类型安全

---

## 目录

1. [执行摘要](#1-执行摘要)
2. [安全漏洞（OWASP Top 10）](#2-安全漏洞)
3. [运行时 Bug 与静默失败](#3-运行时-bug-与静默失败)
4. [God Class 与大文件](#4-god-class-与大文件)
5. [架构与耦合问题](#5-架构与耦合问题)
6. [数据库性能](#6-数据库性能)
7. [异常处理](#7-异常处理)
8. [API 设计一致性](#8-api-设计一致性)
9. [异步任务系统](#9-异步任务系统)
10. [类型安全](#10-类型安全)
11. [模型设计](#11-模型设计)
12. [文件夹结构与解耦建议](#12-文件夹结构与解耦建议)
13. [修复优先级总表](#13-修复优先级总表)

---

## 1. 执行摘要

### 整体评价

项目整体架构思路清晰（Django + Django Ninja + 分层架构 + ServiceLocator DI + MCP Server），核心模块（legal_research、core/protocols）设计成熟。但由于项目快速迭代，积累了大量技术债务。

### 关键数字

| 维度 | 发现 |
|------|------|
| 🔴 严重安全漏洞 | 7 个（exec RCE、路径遍历、命令注入、批量赋值、60+ 无认证 API） |
| 🔴 运行时 Bug | 15+ 个（静默失败、死代码执行路径、导入错误） |
| 🟡 God Class（500+ 行） | 20+ 个 |
| 🟡 N+1 查询 | 25+ 处 |
| 🟡 异常静默吞没 | 600+ 处 |
| 🟡 `Any` 类型注解 | ~2,235 处 |
| 🟡 `# type: ignore` | 902 处 |
| 🟢 好消息 | 无裸 `except:`、事务安全、连接管理合理、mypy 配置严格 |

---

## 2. 安全漏洞

### P0 — 立即修复

| # | 严重度 | 位置 | 问题 | 修复建议 |
|---|--------|------|------|----------|
| S1 | 🔴 CRITICAL | `workflow/temporal/activities.py:374` | `exec()` 沙箱通过 `getattr` 可轻易绕过，完整 RCE | 移除 exec()，用 RestrictedPython 或删除 code step |
| S2 | 🔴 CRITICAL | `automation/api/auto_namer_api.py:58` | 路径遍历：用户传入任意路径如 `/etc/passwd`，系统读取并返回 | 添加 `is_relative_to(MEDIA_ROOT)` 校验 |
| S3 | 🔴 HIGH | 60+ 个 Router | 无显式 `auth=`，NinjaAPI 实例无默认 auth，绝大多数 API 默认公开 | 在 NinjaAPI 或每个 Router 设置 `auth=JWTOrSessionAuth()` |
| S4 | 🔴 HIGH | `cases/admin/mixins/views.py:786`, `contracts/admin/mixins/display_mixin.py:286` | `subprocess.Popen` 打开用户指定路径，命令注入风险 | 使用 `subprocess_runner` + 路径白名单 |
| S5 | 🔴 HIGH | `case_command_service.py:187`, `case_log_mutation_service.py:98`, `mutation/service.py:68` 等 9 处 | `setattr` 循环无字段白名单，批量赋值漏洞 | 使用 `_UPDATABLE_FIELDS` 白名单 |
| S6 | 🟡 MEDIUM | `case_import_service.py:259` | `Path(settings.MEDIA_ROOT) / file_path` 路径拼接，路径遍历 | 使用 `resolve_media_path` |
| S7 | 🟡 MEDIUM | `casenumber_api.py:117` | 返回服务器绝对路径给客户端，信息泄露 | 仅返回相对路径 |
| S8 | 🟡 MEDIUM | `settings.py` | `DEBUG` 默认 `True`、`ALLOWED_HOSTS` 生产默认 `["*"]` | 生产必须显式设置 |
| S9 | 🟡 MEDIUM | `automation/api/performance_monitor_api.py` | `clear_cache`、`cleanup_resources` 等写操作无认证 | 添加管理员认证 |
| S10 | 🟡 MEDIUM | `automation/models/scraper.py` | `ScraperTask.config` 明文存储账号密码 | 使用加密字段 |
| S11 | 🟡 MEDIUM | `workflow/temporal/activities.py:353` | `generic_http_request` 无 URL 验证，SSRF 风险 | 拒绝内网 IP |
| S12 | 🟡 MEDIUM | 多处文件上传端点 | 无文件类型/MIME 白名单 | 添加类型校验 |
| S13 | 🟡 MEDIUM | `poi_api.py:136` | 手动拼接 JSON 字符串，JSON 注入风险 | 使用 JsonResponse |

---

## 3. 运行时 Bug 与静默失败

### 🔴 Workflow 引擎（最严重）

| # | 位置 | 问题 | 影响 |
|---|------|------|------|
| B1 | `workflows.py:780` | `{{previous_step.*}}` 模板变量永远解析为空（`_last_output` 从未写入 context） | MCP 工具收到空参数但不报错 |
| B2 | `workflows.py:441-443` | 条件分支完全无效（设置 `{"skipped": True}` 但不跳过后续步骤） | 所有步骤无条件执行 |
| B3 | `workflows.py:278-299` | `_eval_condition` 无法解析 `previous_step` 路径 | 条件永远为 False |
| B4 | `workflows.py:694-739` | Wait 步骤无超时限制 | 无限等待 |
| B5 | `events/dispatcher.py:32` | 法院回复事件发送 `"court-reply"` 但 workflow 监听 `"gate_approved"` | 事件被静默丢弃 |
| B6 | `workflow_tools.py:10` | Temporal 地址硬编码 `localhost:7233` | 生产环境必然失败 |
| B7 | `workflow_tools.py:30` | workflow_id 确定性生成 | 同模板同案件无法重试 |

### 🔴 其他模块

| # | 位置 | 问题 |
|---|------|------|
| B8 | `evidence/services/admin/evidence_list_placeholder_service.py:202-232` | 调用从未定义的方法，运行时崩溃 |
| B9 | `evidence/services/export/evidence_export_service.py:161` | 从错误模块导入，ImportError |
| B10 | `litigation_ai/services/generation/prompt_template_service.py:8` | 导入不存在的函数，ImportError |
| B11 | `legal_solution/services/prompts.py:84` | 占位符 `{section_type}` 未格式化，输出字面量 |
| B12 | `contract_review/admin/format_normalize_admin.py:347` | 访问不存在的模型字段 |
| B13 | `automation/schemas/court_document.py:18-26` | 空操作验证器（`missing_fields` 永远为空） |
| B14 | `automation/services/document_delivery/delivery/document_processor.py:470` | 日志内容永远为空（`file_names` 未填充） |
| B15 | `finance/services/lpr/sync_service.py:128` | 5 年期利率解析失败时静默替换为 1 年期 |

---

## 4. God Class 与大文件

### 按代码行数排序的 Top 20

| # | 文件 | 行数 | 问题 | 拆分建议 |
|---|------|------|------|----------|
| G1 | `contracts/.../folder_scan_service.py` | 1,138 | 项目最大文件 | ScanOrchestrator + ImportPipeline + ClassificationContext |
| G2 | `legal_research/.../benchmark_...py` | 1,130 | 管理命令 | 可保留 |
| G3 | `documents/admin/document_template_admin.py` | 1,029 | Admin God Class | 拆分为多个 Mixin |
| G4 | `legal_research/.../capability/service.py` | 956 | 超级类 | concurrency + filters + snippets + ranking |
| G5 | `core/services/material_classification_service.py` | 947 | 3 个独立职责 | ContractClassifier + CaseClassifier + ArchiveClassifier |
| G6 | `mcp_server/server.py` | 910 | 纯注册代码 | 自动发现机制 |
| G7 | `cases/admin/mixins/views.py` | 909 | God Mixin | Display + Detail + Document + Folder |
| G8 | `litigation_ai/.../mock_trial_flow_service.py` | 903 | 4 种庭审模式 | judge + cross_exam + debate + adversarial |
| G9 | `automation/.../court_guarantee_helpers.py` | 893 | 大量重复 | 提取共享 session helpers |
| G10 | `automation/.../court_filing_helpers.py` | 884 | 同上 | 同上 |
| G11 | `contract_review/.../docx_format_normalizer.py` | 826 | God Class | 5 个子管理器 |
| G12 | `reminders/admin/reminder_admin.py` | 824 | 日历+CRUD+同步+导出 | 拆分为 Mixin |
| G13 | `automation/.../contract_oa_sync_service.py` | 731 | 硬编码 | 提取配置 |
| G14 | `automation/.../court_insurance_client.py` | 728 | 大方法 | 提取 dataclass |
| G15 | `cases/.../folder_scan_service.py` | 715 | God Class | ScanOrchestrator + Staging + Classification |
| G16 | `automation/.../sms_parser_service.py` | 678 | 大文件 | _link_extractor + _party_extractor |
| G17 | `automation/.../court_zxfw.py` | 691 | 验证码+XPath | 提取 _captcha_helpers |
| G18 | `cases/.../litigation_fee_calculator_service.py` | 680 | 非枚举 | 用 Enum 替换普通类 |
| G19 | `contracts/admin/contract_admin.py` | 638 | Admin 过大 | 拆分 |
| G20 | `contracts/admin/mixins/archive_mixin.py` | 620 | God Mixin | ArchiveView + ArchiveFile + ArchiveBatch |

---

## 5. 架构与耦合问题

### 5.1 循环依赖

| # | 依赖关系 | 严重度 | 说明 |
|---|----------|--------|------|
| D1 | `cases ↔ contracts` | 🔴 | 27 处跨 app import + 2 个 FK |
| D2 | `automation ↔ litigation_ai` | 🟡 | 直接 import vs ServiceLocator |
| D3 | `automation ↔ captcha_ocr` (plugin) | 🟡 | 双向 import |
| D4 | `legal_research ↔ weike_api_private` (plugin) | 🟡 | 双向 import |
| D5 | `core ↔ 几乎所有 app` | 🔴 | core/services/ 5 个服务直接 import 上层 app |

### 5.2 core 反向依赖（最大架构违规）

| 文件 | 问题 |
|------|------|
| `core/services/dashboard_service.py` | 直接查询 5 个 app 的模型 |
| `core/services/search_service.py` | 直接查询 6 个 app 的模型 |
| `core/models/conversation.py:32` | FK 指向 `litigation_ai.LitigationSession` |
| `core/services/court_tokens/baoquan_token_service.py` | 直接 import automation 内部实现 |
| `core/service_locator_mixins/` 中 3 个 mixin | 绕过 dependencies/ 直接 import |

### 5.3 MCP Server 耦合

- `mcp_server/tools/__init__.py:418` — 直接 import `apps.workflow.mcp.workflow_tools`（15 个函数）
- 破坏了通过 FachuanClient HTTP 实现的进程级解耦
- server.py 900 行纯注册代码，新增 tool 需改 3 个文件

### 5.4 Plugins 反向依赖

- `plugins/doc_convert/` → import `apps.doc_convert.constants/exceptions`
- `plugins/weike_api_private/` → import `apps.legal_research.services.*`
- `plugins/captcha_ocr/` → import `apps.automation.services.scraper.*`

### 5.5 三重注册维护负担

| 位置 | 数量 | 机制 |
|------|------|------|
| `api.py` `_register_app_routers()` | 54 个 add_router | 手动 |
| `mcp_server/server.py` | 381 个 mcp.tool() | 手动 |
| `admin_customization.py` | 41+30 个 app 列表 | 手动 |

---

## 6. 数据库性能

### N+1 查询热点

| 模块 | 数量 | 最严重场景 |
|------|------|-----------|
| contracts | 12 处 | 合同详情/导出产生 20-50+ 次额外查询 |
| cases | 5 处 | 案件导出三层嵌套 N+1 |
| documents/placeholders | 15 处 | Python 层过滤应改 DB 层 |
| automation | 11 处 | SMS 下载重复 `.count()` 8-10 次 |

### 缺失索引

| 模型 | 缺失索引 | 影响 |
|------|----------|------|
| BatchJobItem | `[job, status]` | 10+ 次高频查询 |
| CaseAssignment | `[case, lawyer]` | 权限检查核心路径 |
| SolutionTask | 完全无索引 | 数据量增长后查询堪忧 |
| CaseImportSession | 完全无索引 | 同上 |
| WorkflowRun | 仅有 unique 索引 | `status` 字段无索引 |

### 无分页 API

- contracts/cases 列表端点返回全量数据（P0）
- 17 个其他列表端点无分页
- 项目有 `paginate_queryset()` 工具但仅 2 个端点使用

---

## 7. 异常处理

### 全局统计

| 模式 | 数量 |
|------|------|
| `except Exception` 总计 | 1,644 |
| 静默吞没（`logger.debug/warning`） | 433 |
| 静默吞没（`pass`） | 113 |
| 静默吞没（`return default`） | 578 |
| 异常链丢失（无 `from e`） | 237 |
| ORM in except blocks | 43 |
| 裸 `except:` | **0** ✅ |

### 最严重问题

| # | 位置 | 问题 |
|---|------|------|
| E1 | `core/config/utils.py` 11 处 | 数据库故障隐藏在 `logger.debug`，生产不可见 |
| E2 | `pdf_splitting/models.py:172`, `batch_printing/models.py:203` | 信号处理器无异常保护 |
| E3 | `contract_review/review_service.py:344` | except 中 ORM 操作无嵌套 try，DB 错误时任务永远卡住 |
| E4 | `chat_records/tasks.py:331` | 只捕获 TypeError/ValueError，其他异常导致任务卡在 RUNNING |
| E5 | `court_document_api_coordinator.py` | 重试无退避，触发法院 API 限流 |

---

## 8. API 设计一致性

### 错误响应格式（5 种不统一）

```
{"success": false, "message": "..."}    — 最常见
{"success": false, "error": "..."}      — 部分端点
{"error": "..."}                        — core API
{"ok": false, "error": "..."}           — LLM API
{"status": "error", "message": "..."}   — POI API
```

### DELETE 返回格式（7 种不统一）

`{"success": true}` / `{"message": "已删除"}` / `Status(204, None)` / `HttpResponse(204)` / `{"deleted": true}` / service 返回值 / 无返回

### 其他问题

- 错误时返回 HTTP 200 而非 4xx/5xx
- `json.loads(request.body)` 绕过 Schema 验证
- 同一 app 三种认证策略
- `client_api.py` 手动提取 user 而非依赖 auth

---

## 9. 异步任务系统

### 项目使用 Django-Q2（非 Celery）

| # | 严重度 | 问题 | 位置 |
|---|--------|------|------|
| T1 | 🔴 | `time.sleep` 轮询最长 10 分钟阻塞 worker | `legal_solution/tasks.py:72` |
| T2 | 🔴 | 只捕获部分异常，任务永远卡在 RUNNING | `chat_records/tasks.py:331` |
| T3 | 🔴 | 无队列路由，轻重任务混杂 | `core/config/django_runtime.py` |
| T4 | 🔴 | 定时任务模块加载时注册，DB 未就绪时静默失败 | `message_hub/tasks.py:96` |
| T5 | 🟡 | evidence/tasks 无错误处理和状态更新 | `evidence/tasks.py:11-26` |
| T6 | 🟡 | client/tasks 失败后删除文件导致不可重试 | `client/tasks.py:22` |
| T7 | 🟡 | sync_all_sources 无分布式锁防并发 | `message_hub/tasks.py:55` |
| T8 | 🟡 | LPR 定时任务注册函数从未被调用 | `finance/tasks.py:38` |

---

## 10. 类型安全

### 关键数字

| 指标 | 数量 |
|------|------|
| `Any` 注解 | ~2,235 |
| `# type: ignore` | 902（82 处无错误码） |
| `cast()` 调用 | 282（14 处 `cast(Any, ...)`） |
| 返回 `dict[str, Any]` 的 API | 65+ |
| Protocol-实现签名不匹配 | 3 处（可导致运行时错误） |
| Pydantic v2 无效 `class Config` | 15 个 Schema |

### 最严重问题

| # | 问题 | 影响 |
|---|------|------|
| TY1 | 3 个 Protocol-实现签名不匹配 | 运行时 TypeError/错误数据 |
| TY2 | `CaseServiceAdapter` 21/31 方法返回 `Any` | 类型信息最大丢失源 |
| TY3 | 15 个 Schema 的 `json_encoders` 在 Pydantic v2 中无效 | 序列化可能不符合预期 |
| TY4 | DTO-Schema 返回类型谎言（4 处） | mypy 无法捕获下游错误 |

---

## 11. 模型设计

### 字段类型问题

| 问题 | 位置 |
|------|------|
| CharField 存日期 | `LegalResearchTask.date_from/date_to` |
| FloatField 存毫秒（应为 IntegerField） | 3 个模型的 `duration_ms` |
| null=True + blank=True + default="" 混用 | `Client.address` |
| IntegerField 软引用应为 ForeignKey | `InvoiceRecord.duplicate_of_id` |

### 模型过大

| 模型 | 字段数 | 建议 |
|------|--------|------|
| ChatRecordRecording | ~22 | 拆分抽帧字段为独立模型 |
| LegalResearchTask | ~26 | 拆分搜索参数和进度统计 |

### 代码重复（可抽取基类）

- `CaseFolderBinding` ≈ `ContractFolderBinding`
- `CaseFolderScanSession` ≈ `ContractFolderScanSession`
- `BatchPrintJob` ≈ `DocConverterJob` ≈ `ChatRecordExportTask`

### JSONField 滥用

- `CourtSMS` 4 个列表字段应用关系表
- `EvidenceChunk.embedding` 应用 pgvector
- `ScraperTask.config` 明文存储敏感配置

---

## 12. 文件夹结构与解耦建议

### 12.1 应迁移出 core 的服务

| 服务 | 当前位置 | 建议迁移至 |
|------|----------|-----------|
| 浏览器自动化 | `core/services/browser/` | `apps/automation/` |
| 法院 API 客户端 | `core/services/court_api_client.py` | `apps/litigation/` 或新建 `apps/court/` |
| 宝泉 Token | `core/services/court_tokens/` | 同上 |
| 邮件服务 | `core/services/email_service.py` | `apps/notifications/` |
| Dashboard | `core/services/dashboard_service.py` | `apps/workbench/` |
| 全局搜索 | `core/services/search_service.py` | `apps/workbench/` |
| 材料分类 | `core/services/material_classification_service.py` | 独立 app 或迁出 |

### 12.2 应提升为独立 app 的子模块

| 当前位置 | 建议 |
|----------|------|
| `core/cloud_storage/` | 提升为 `apps/cloud_storage/` |
| `core/llm/` | 提升为 `apps/llm/` |
| `core/tasking/` | 提升为 `apps/tasking/` |
| `automation/services/ocr/` | 提升为 `apps/ocr/`（被 7 个 app 依赖） |
| `automation/services/chat/` | 提升为 `apps/chat/` |

### 12.3 应合并的 app

| 合并建议 | 理由 |
|----------|------|
| evidence + evidence_sorting | evidence_sorting 仅 10 文件 1,135 行 |
| contacts → organization | contacts 仅 10 文件 679 行 |
| doc_convert + doc_converter | 职责重叠 |
| document_parsing + document_recognition | 职责相关 |

### 12.4 应删除

| 目标 | 理由 |
|------|------|
| `apps/fee_notice/` | 零文件零代码 |
| `apps/core/interfaces/` | 与 `protocols/` 概念重复 |
| `automation/usecases/court_sms/` | 纯透传包装器 |
| `automation/workers/` | 与 tasks/ 重复 |
| `workflow/api/template_api.py` | 与 workflow_api.py 完全重复 |
| 多个 `__str__` 返回空字符串的模型 | 影响 Admin 可用性 |

### 12.5 代码重复热点

| 重复模式 | 出现次数 | 位置 |
|----------|----------|------|
| `method()` + `method_ctx()` 双版本 | ~30% 代码量 | cases, contracts 所有 service |
| Base64 解码 | 5 处 | image_rotation |
| RGBA-to-RGB 转换 | 3 处 | image_rotation |
| `_build_session_status_payload` | 2 处 | automation court_guarantee/filing |
| `_safe_filename()` | 3 处 | automation scrapers |
| `_resolve_download_filename` | 2 处 | message_hub |
| WEIKE_SITE_FILTER | 2 处 | legal_research admin |

---

## 13. 修复优先级总表

### P0 — 立即修复（安全 + 数据完整性）

| # | 问题 | 预估工作量 |
|---|------|-----------|
| 1 | 移除或替换 `exec()` RCE | 2 小时 |
| 2 | 修复 `auto_namer_api` 路径遍历 | 30 分钟 |
| 3 | 为所有 Router 添加默认 `auth=JWTOrSessionAuth()` | 2 小时 |
| 4 | 修复 setattr 批量赋值漏洞（9 处） | 3 小时 |
| 5 | 修复 `subprocess.Popen` 命令注入 | 1 小时 |
| 6 | 修复 workflow 5 个静默失败 Bug | 4 小时 |
| 7 | 修复 `evidence` 的 ImportError 和未定义方法 | 1 小时 |
| 8 | 修复 `litigation_ai` 的 ImportError | 30 分钟 |

### P1 — 本周修复（稳定性 + 性能）

| # | 问题 | 预估工作量 |
|---|------|-----------|
| 9 | 为 contract 模块添加 prefetch_related（12 处 N+1） | 3 小时 |
| 10 | 添加缺失复合索引（5 个） | 1 小时 |
| 11 | 为 contracts/cases 列表添加分页 | 2 小时 |
| 12 | 修复异常静默吞没（config/utils.py 11 处 logger.debug） | 1 小时 |
| 13 | 修复信号处理器无异常保护（2 处） | 30 分钟 |
| 14 | 修复 tasks 异常捕获不完整（3 处） | 1 小时 |
| 15 | 为重试添加指数退避 | 1 小时 |
| 16 | 统一错误响应格式 | 4 小时 |
| 17 | 修复 Protocol-实现签名不匹配（3 处） | 2 小时 |

### P2 — 本月修复（技术债务）

| # | 问题 | 预估工作量 |
|---|------|-----------|
| 18 | 拆分 Top 5 God Class | 2 天 |
| 19 | 统一 interfaces/ 和 protocols/ | 1 天 |
| 20 | 将 core/services/ 中业务服务迁出 | 3 天 |
| 21 | 拆分 automation（OCR、Chat 为独立 app） | 2 天 |
| 22 | 合并 doc_convert + doc_converter | 1 天 |
| 23 | 删除空壳 fee_notice、清理工人死代码 | 2 小时 |
| 24 | 为 Automation 添加异常日志（40+ 处 pass） | 2 小时 |
| 25 | 修复 Python 层过滤改 DB 层（15 处） | 3 小时 |

### P3 — 长期改善

| # | 问题 | 预估工作量 |
|---|------|-----------|
| 26 | MCP tool 自动注册机制 | 1 周 |
| 27 | Plugin 共享类型提取到 core.interfaces | 3 天 |
| 28 | cases ↔ contracts 解耦 | 1 周 |
| 29 | 统一 DI 模式（消除 ServiceLocator 直接使用） | 2 周 |
| 30 | 消除 Any 注解（分批） | 持续 |
| 31 | 统一 API 认证策略和错误响应 | 1 周 |
| 32 | 为核心路径补充测试覆盖 | 持续 |
| 33 | 引入全文搜索（pg_trgm / SearchVector） | 3 天 |

---

*报告由 18 个并行 AI agent 生成，审查覆盖了 backend 的每一行 Python 代码。*
