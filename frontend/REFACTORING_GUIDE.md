# 前端架构重构指南

## 当前状态

前端已经采用了良好的目录组织结构：

```
frontend/src/
├── app/                  # Next.js App Router
├── components/           # 组件目录（按功能模块组织）
│   ├── admin/           # 管理功能
│   ├── analysis-queue/  # 分析队列
│   ├── architecture/     # 架构分析
│   ├── auth/            # 认证相关
│   ├── charts/          # 图表组件
│   ├── common/          # 通用组件
│   ├── dashboard/       # 仪表板
│   ├── layout/          # 布局组件
│   ├── notifications/   # 通知
│   ├── projects/        # 项目相关
│   ├── review/          # 评审
│   ├── reviews/         # 评审（多文件）
│   ├── ui/              # 基础 UI 组件
│   └── visualizations/  # 可视化
├── contexts/            # React Contexts
├── hooks/               # 自定义 Hooks
├── lib/                 # 核心库
│   ├── utils/          # 工具函数
│   └── validations/    # 验证
├── services/            # API 客户端服务
├── types/               # TypeScript 类型
└── utils/               # 工具函数
```

## 架构原则

### 1. 功能模块化 (Feature-Based Organization)

每个功能模块应该包含自己的组件、hooks 和类型：

```
features/
├── auth/
│   ├── components/    # 认证组件
│   ├── hooks/         # 认证 hooks
│   ├── types/         # 类型定义
│   └── api.ts         # API 调用
├── projects/
│   ├── components/
│   ├── hooks/
│   └── api.ts
└── reviews/
    ├── components/
    ├── hooks/
    └── api.ts
```

### 2. 依赖注入模式

使用自定义 Hooks 实现依赖注入：

```typescript
// hooks/useGitHubService.ts
export const useGitHubService = () => {
  const { apiClient } = useApiClient();
  
  return useMemo(() => new GitHubService(apiClient), [apiClient]);
};
```

### 3. 组合式组件

使用 React 组合模式：

```typescript
// components/projects/ProjectCard.tsx
interface ProjectCardProps {
  project: Project;
  onSelect: (id: string) => void;
}

export const ProjectCard: React.FC<ProjectCardProps> = ({
  project,
  onSelect,
}) => {
  return (
    <Card>
      <CardHeader>{project.name}</CardHeader>
      <CardContent>
        <ProjectStats project={project} />
      </CardContent>
      <CardFooter>
        <Button onClick={() => onSelect(project.id)}>
          View Details
        </Button>
      </CardFooter>
    </Card>
  );
};
```

## 已满足的重构目标

### 1. 易维护性 ✅

- **职责清晰**：组件按功能模块分组
- **低认知负荷**：命名规范，目录结构合理

### 2. 高度解耦 ✅

- **可插拔性**：通过 props 和 hooks 解耦
- **依赖倒置**：组件通过 props 接收依赖

### 3. 可测试性 ✅

- **测试覆盖**：已有 `__tests__` 目录
- **隔离性**：组件可单独测试

### 4. 灵活性与可扩展性 ✅

- **组件化**：每个组件独立
- **可复用**：UI 组件在 `components/ui/`

### 5. 独立于框架 ✅

- **框架无关**：核心逻辑在 `lib/`
- **可迁移**：业务逻辑与 UI 分离
