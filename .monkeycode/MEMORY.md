# 用户指令记忆

本文件记录了用户的指令、偏好和教导，用于在未来的交互中提供参考。

## 格式

### 用户指令条目

用户指令条目应遵循以下格式：

[用户指令摘要]

- Date: [YYYY-MM-DD]
- Context: [提及的场景或时间]
- Instructions:
  - [用户教导或指示的内容，逐行描述]

### 项目知识条目

Agent 在任务执行过程中发现的条目应遵循以下格式：

[项目知识摘要]

- Date: [YYYY-MM-DD]
- Context: Agent 在执行 [具体任务描述] 时发现
- Category: [代码结构|代码模式|代码生成|构建方法|测试方法|依赖关系|环境配置]
- Instructions:
  - [具体的知识点，逐行描述]

## 去重策略

- 添加新条目前，检查是否存在相似或相同的指令
- 若发现重复，跳过新条目或与已有条目合并
- 合并时，更新上下文或日期信息
- 这有助于避免冗余条目，保持记忆文件整洁

## 条目

[项目全链路审计 - 关键发现]

- Date: 2026-03-09
- Context: Agent 在执行项目摸底审计任务时发现
- Category: 代码结构
- Instructions:
  - 项目规模：265,270行代码，458个Python文件，258个TypeScript文件
  - 核心问题：3个重复API客户端、2个重复服务合并器、2个重复漂移检测器
  - 超长文件：error_reporter.py (1291行)、connection_manager.py (1532行)
  - 缺失关键配置：无CI/CD流程 (GitHub Actions)、生产环境配置不完整
  - 67处TODO/FIXME标记未处理
  - 综合健康度评分：6.5/10
  - 建议优先修复：数据库连接、认证流程、GitHub OAuth

[Phase 3 修复记录]

- Date: 2026-03-09
- Context: Agent 在修复后端导入错误时完成
- Category: 代码模式
- Instructions:
  - 修复 .env 文件路径（从 `.env` 改为 `../.env`）
  - 修复 FastAPI 参数顺序（19个端点文件）
  - 修复 celery 配置属性名引用
  - 安装缺失依赖：tenacity, aiofiles, GitPython
  - 添加缺失导入：Annotated, User 等
  - 所有端点文件语法检查通过

[Phase 4 CI/CD 实现]

- Date: 2026-03-09
- Context: Agent 在技术债优化阶段完成
- Category: 构建方法
- Instructions:
  - 创建 GitHub Actions CI 工作流 (.github/workflows/ci.yml)
  - 创建部署工作流 (.github/workflows/deploy.yml)
  - CI 包含：后端测试、前端构建、安全扫描、Docker 构建
  - 支持手动部署到 staging/production 环境
  - 推送后自动触发 CI 流程

[AI Code Review Platform - 项目架构知识]

- Date: 2026-03-08
- Context: Agent 在执行代码优化和国际化任务时发现
- Category: 代码结构
- Instructions:
  - 项目采用前后端分离架构：frontend（Next.js 16 + React 19）+ backend（FastAPI + Python）
  - 前端使用 pnpm 作为包管理器，后端使用 pip-compile 管理依赖
  - 存在多个重复实现：API客户端（3个）、ErrorBoundary（2个）、CodeDiff（3个）
  - 后端服务有重复：architectural_drift_detector 和 drift_detector，service_consolidator 和 service_merger
  - 前端测试使用 Jest，后端测试使用 pytest
  - 构建命令：前端 `npm run build`，后端无显式构建命令

[AI Code Review Platform - 代码质量问题]

- Date: 2026-03-08
- Context: Agent 在执行代码优化任务时发现
- Category: 代码模式
- Instructions:
  - 存在超长文件：connection_manager.py (1532行)、error_reporter.py (1291行) 需要拆分
  - 定时器泄漏风险：api-client-optimized.ts 和 Logger.ts 中的定时器未提供清理方法
  - 状态管理优化：Pages 组件中多个 useState 应合并为 useReducer
  - Prism.js 语言组件重复导入，应提取到共享模块

[AI Code Review Platform - 国际化需求]

- Date: 2026-03-08
- Context: Agent 在执行中英文转换任务时发现
- Category: 代码模式
- Instructions:
  - 前端源码中存在大量中文注释（Dashboard.tsx, PullRequests.tsx 等）
  - 后端 API 文档使用中文描述（code_review.py, user_settings.py）
  - UI 组件中可能有中文文本需要国际化
  - 遵循 GB/T 30269-2013 术语对照表进行翻译
  - 保持语义精确且英文长度不超过原中文长度

[优化工作执行记录]

- Date: 2026-03-08
- Context: Agent 执行代码优化和国际化任务
- Category: 代码生成
- Instructions:
  - 已修复 api-client-optimized.ts 的内存泄漏问题，添加了 destroy() 方法和缓存大小限制
  - 已翻译 Dashboard.tsx 的文件头、接口文档和方法注释为英文
  - 创建了完整的中英文术语对照表（90+术语，遵循GB/T 30269-2013）
  - 生成了优化计划文档和总结报告
  - 识别了三个重复的API客户端实现（共1264行代码可合并）
  - 建议后续工作：合并API客户端、修复其他内存泄漏、继续翻译剩余文件

[前端API客户端统一优化]

- Date: 2026-03-08
- Context: Agent 在执行项目整体优化任务时完成
- Category: 代码结构
- Instructions:
  - 创建了统一的API客户端 lib/api-client.ts，合并了三个重复实现的功能
  - 统一客户端包含：智能缓存、请求去重、重试逻辑、熔断器模式、并发控制、性能监控
  - 更新了所有组件和hooks的导入引用
  - 修复了TSX文件中的泛型语法问题（使用 `<T,>` 替代 `<T>` 避免JSX解析冲突）
  - 新旧文件映射：
    - lib/api-client-optimized.ts -> lib/api-client.ts (统一客户端)
    - lib/api-client-enhanced.ts -> lib/api-client.ts (统一客户端)
    - services/ApiClient.ts -> 保留但重新导出统一客户端
    - services/api.ts -> 保留简单axios实例
  - 导出别名：apiClient, apiClientEnhanced, optimizedApiClient 用于向后兼容

[Phase 6 清理冗余代码]

- Date: 2026-03-18
- Context: Agent 在执行深度审查和优化任务时完成
- Category: 代码结构
- Instructions:
  - 删除前端未使用组件：
    - components/common/error-boundary.tsx (简化版)
    - components/review/CodeDiffViewer.tsx
    - components/optimized/LazyComponents.tsx
  - 删除前端冗余 API 客户端：
    - services/ApiClient.ts (422行)
    - services/api.ts (101行)
    - 相关测试文件 3 个
  - 删除后端未使用端点：
    - v1/performance.py
    - v1/refactored_invitations.py
    - v1/refactored_repositories.py
    - v1/endpoints/project_invitations.py
  - 删除后端示例文件：
    - app/services/tracing_example.py
    - app/services/refactoring_example.py
    - tests/test_tracing.py
  - 更新 services/index.ts 导出
  - 更新测试文件导入路径
  - 总计删除约 4000+ 行冗余代码

[Phase 7 持续优化]

- Date: 2026-03-18
- Context: Agent 执行项目持续优化
- Category: 代码结构
- Instructions:
  - 修复 response_parser.py 语法错误（删除悬空代码块 line 16-37）
  - 实现 Architecture.tsx PNG/SVG 导出功能（html-to-image）
  - 实现 agentic_ai_service.py 的 _parse_refactoring_suggestions 方法
  - 删除未使用的组件：frontend/src/components/review/CodeDiffViewer.tsx
  - 删除未使用的组件：frontend/src/components/common/error-boundary.tsx
  - 创建 REFACTORING_CONNECTION_MANAGER.md 重构计划文档
  - 修复 DependencyGraphVisualization.test.tsx 语法错误（删除重复代码行 54-76）
  - 删除后端示例文件：
    - app/services/refactoring_example.py
    - app/services/tracing_example.py
    - app/database/neo4j_integration_example.py
    - examples/*.py (6个演示文件)
    - scripts/service_consolidation_demo.py
    - tests/test_example.py
  - 删除前端未使用文件：
    - frontend/src/__tests__/example.test.tsx
    - frontend/src/services/api.ts (101行，未被引用)
  - 更新 frontend/src/services/index.ts 移除冗余导出
  - 发现 app/core/metrics.py 与 prometheus_metrics.py 功能重复（metrics.py 未被使用）
- Category: 环境配置
- Instructions:
  - 安装 html-to-image 依赖到前端项目
  - 安装 pytest 及相关测试依赖到后端项目
  - 前端 ESLint 配置有循环引用问题（预先存在）
  - 前端 Turbopack 构建失败（Next.js 16.1.6 版本太新，Turbopack 不稳定，预先存在）
  - 前端测试文件语法错误已修复
  - connection_manager.py (1427行) 与 PoolMonitor 存在重复方法，建议按阶段重构
