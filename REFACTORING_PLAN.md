# 项目架构重构计划

## 当前架构问题分析

### 后端问题
1. **services目录职责混乱** - 60+个服务文件堆积，没有清晰分组
2. **缺少领域抽象层** - 业务逻辑直接暴露在API层
3. **依赖关系混乱** - 服务之间直接依赖，耦合度高
4. **缺少依赖注入** - 硬编码依赖导致难以测试

### 前端问题
1. **components目录过大** - 缺少按功能模块的分组
2. **lib和services职责重叠** - 需要明确分层

## 重构目标架构

```
backend/
├── app/
│   ├── api/                    # API层 - 负责请求/响应处理
│   │   └── v1/
│   │       ├── endpoints/     # API端点（控制器）
│   │       ├── dependencies/  # 依赖注入
│   │       └── router.py      # 路由组装
│   │
│   ├── domain/                # 领域层 - 核心业务逻辑（框架无关）
│   │   ├── entities/          # 实体定义
│   │   ├── repositories/      # 仓储接口（抽象）
│   │   ├── services/          # 领域服务（业务规则）
│   │   └── events/            # 领域事件
│   │
│   ├── application/           # 应用层 - 用例编排
│   │   ├── commands/          # 命令（写操作）
│   │   ├── queries/           # 查询（读操作）
│   │   └── handlers/          # 处理器
│   │
│   ├── infrastructure/        # 基础设施层 - 具体实现
│   │   ├── persistence/       # 数据库实现
│   │   │   ├── repositories/  # 仓储实现
│   │   │   └── migrations/    # 迁移脚本
│   │   ├── external/           # 外部服务
│   │   │   ├── github/        # GitHub API
│   │   │   ├── llm/           # LLM服务
│   │   │   └── cache/         # 缓存服务
│   │   └── messaging/         # 消息队列
│   │
│   ├── shared/                # 共享模块
│   │   ├── constants/         # 常量
│   │   ├── exceptions/        # 异常定义
│   │   └── utils/            # 工具函数
│   │
│   ├── config/               # 配置管理
│   │
│   └── main.py              # 应用入口
│
frontend/
├── src/
│   ├── app/                  # Next.js App Router
│   │
│   ├── features/             # 按功能模块组织
│   │   ├── auth/            # 认证功能
│   │   ├── projects/        # 项目功能
│   │   ├── reviews/          # 评审功能
│   │   └── architecture/     # 架构分析
│   │
│   ├── components/          # 通用组件
│   │   ├── ui/              # 基础UI组件
│   │   └── shared/          # 共享组件
│   │
│   ├── hooks/               # 自定义Hooks
│   │
│   ├── services/            # API客户端（对接后端API）
│   │
│   ├── lib/                 # 核心库
│   │   ├── api/            # API客户端
│   │   ├── auth/           # 认证逻辑
│   │   └── utils/         # 工具函数
│   │
│   ├── types/               # TypeScript类型
│   │
│   └── store/               # 状态管理
```

## 重构原则

### 1. 依赖倒置 (DIP)
- 高层模块不依赖低层模块
- 依赖抽象接口，不依赖具体实现
- 示例：Service不直接依赖GitHubClient，而是依赖IGitHubService接口

### 2. 单一职责 (SRP)
- 每个模块只负责一件事
- 职责边界清晰

### 3. 开闭原则 (OCP)
- 对扩展开放
- 对修改关闭

### 4. 依赖注入 (DI)
- 通过构造函数注入依赖
- 便于单元测试Mock

## 实施步骤

### Phase 1: 创建新的目录结构
1. 创建domain/application/infrastructure分层
2. 提取领域实体和接口

### Phase 2: 迁移核心服务
1. 迁移认证服务
2. 迁移项目服务
3. 迁移代码审查服务

### Phase 3: 创建抽象接口
1. 定义Repository接口
2. 定义外部服务接口
3. 实施依赖注入

### Phase 4: 前端重构
1. 按功能模块组织代码
2. 提取共享类型和hooks

## 预期收益

1. **可维护性提升** - 新开发者可快速定位代码
2. **可测试性增强** - 通过Mock轻松测试业务逻辑
3. **可扩展性改善** - 添加新功能不影响现有代码
4. **框架独立性** - 核心业务逻辑不依赖具体框架
