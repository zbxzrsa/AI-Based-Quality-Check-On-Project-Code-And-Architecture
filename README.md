# 🤖 AI Code Review Platform

AI 驱动的代码审查与架构分析平台，提供智能代码审查、架构可视化和合规性检查。

## ✨ 核心功能

| 功能 | 描述 |
|---|---|
| 🔐 **用户认证** | 注册/登录、JWT 令牌、RBAC 多角色权限控制 |
| 🔍 **PR 代码审查** | 基于 DeepSeek AI 的 Pull Request 自动审查、安全评分、合规检查 |
| 🏗️ **架构图生成** | 从代码审查结果自动生成架构可视化图、依赖关系图 |
| 🐙 **GitHub 集成** | 仓库管理、PR 同步、Webhook 自动触发审查 |
| 📊 **度量监控** | 代码质量评分、安全评分、架构健康度、Prometheus 指标 |
| 🔒 **企业级安全** | 数据加密、CORS 保护、速率限制、审计日志 |

## 🛠️ 技术栈

```
后端: Python 3.11 + FastAPI + SQLAlchemy + PostgreSQL
图数据库: Neo4j 5+ (架构关系分析)
缓存: Redis 7+ (会话/缓存/速率限制)
AI 审查: DeepSeek API + 内置规则引擎
前端: Next.js 14 + TypeScript + Tailwind CSS
认证: JWT (PyJWT) + bcrypt + RBAC
运行环境: conda lxq
```

## 📁 项目结构

```
├── backend/                    # Python FastAPI 后端
│   ├── app/
│   │   ├── api/v1/endpoints/   # API 端点 (25个)
│   │   │   ├── auth.py         # 认证: 注册/登录/刷新
│   │   │   ├── pull_request.py # PR 分析触发
│   │   │   ├── architecture.py # 架构图数据
│   │   │   ├── code_review.py  # 代码审查
│   │   │   ├── github.py       # GitHub 集成
│   │   │   ├── analyze.py      # 架构分析
│   │   │   ├── rbac_*.py       # 角色权限管理
│   │   │   └── ...             # 健康检查/审计/监控等
│   │   ├── auth/               # 认证模块 (RBAC)
│   │   │   ├── models/         # User, Session, Project 模型
│   │   │   ├── services/       # RBAC 服务
│   │   │   └── middleware/     # 认证中间件
│   │   ├── core/               # 核心配置
│   │   │   ├── config.py       # 应用配置 (Pydantic Settings)
│   │   │   └── ...             # 日志/指标/安全
│   │   ├── database/           # 数据库连接
│   │   │   ├── postgresql.py   # PostgreSQL (async)
│   │   │   ├── neo4j_db.py     # Neo4j 图数据库
│   │   │   └── redis_db.py     # Redis 缓存
│   │   ├── models/             # 数据模型
│   │   ├── schemas/            # Pydantic Schema
│   │   ├── services/           # 业务服务 (50个)
│   │   │   ├── deepseek_service.py        # DeepSeek AI 调用
│   │   │   ├── ai_pr_reviewer.py          # AI PR 审查
│   │   │   ├── code_reviewer.py           # 代码审查引擎
│   │   │   ├── github_client.py           # GitHub API 客户端
│   │   │   ├── architecture_analyzer/     # 架构分析器
│   │   │   ├── architecture_diagram_service.py  # 架构图生成
│   │   │   └── ...                        # 安全/加密/缓存等
│   │   ├── middleware/         # 中间件 (安全头/速率限制/Prometheus)
│   │   ├── tasks/              # 异步任务 (Celery)
│   │   └── utils/              # 工具函数
│   ├── alembic/                # 数据库迁移
│   ├── requirements.txt        # Python 依赖
│   └── requirements.in         # 依赖源清单
│
├── frontend/                   # Next.js 前端
│   ├── src/
│   │   ├── app/                # 页面路由 (16个)
│   │   │   ├── login/          # 登录页
│   │   │   ├── register/       # 注册页
│   │   │   ├── dashboard/      # 仪表板
│   │   │   ├── reviews/        # PR 审查列表/详情
│   │   │   ├── architecture/   # 架构图可视化
│   │   │   ├── projects/       # 项目管理
│   │   │   ├── settings/       # 用户设置 (GitHub Token)
│   │   │   ├── admin/          # 管理后台
│   │   │   ├── profile/        # 用户资料
│   │   │   └── metrics/        # 度量面板
│   │   ├── components/         # React 组件 (17组)
│   │   │   ├── auth/           # 认证组件 (RBAC 守卫)
│   │   │   ├── architecture/   # 架构图组件
│   │   │   ├── review/         # 代码审查组件
│   │   │   ├── dashboard/      # 仪表板组件
│   │   │   └── ...             # 通用/布局/图表等
│   │   ├── contexts/           # React Context (认证/主题)
│   │   ├── services/           # API 调用服务
│   │   ├── hooks/              # 自定义 Hooks
│   │   ├── lib/                # 工具库
│   │   └── types/              # TypeScript 类型
│   └── package.json
│
├── docs/                       # 项目文档
├── scripts/                    # 工具脚本
├── common/                     # 共享配置
├── shared/                     # 共享类型
├── docker-compose.yml          # Docker 编排 (开发环境)
├── docker-compose.prod.yml     # Docker 编排 (生产环境，含 Nginx)
├── nginx/
│   └── nginx.conf              # Nginx 反向代理配置
├── start_all.py                # 一键启动脚本 (本地开发)
└── .env                        # 环境变量配置
```

## 🚀 快速开始

### 前置要求

- **Python 3.11+** (Anaconda / Miniconda)
- **Node.js 18+**
- **PostgreSQL 14+**
- **Redis 7+**
- **Neo4j 5+** (可选，用于架构图分析)

### 安装步骤

#### 1. 克隆项目

```bash
git clone https://github.com/zbxzrsa/AI-Based-Quality-Check-On-Project-Code-And-Architecture.git
cd AI-Based-Quality-Check-On-Project-Code-And-Architecture
```

#### 2. 配置环境变量

在项目根目录创建 `.env` 文件：

```env
# === 数据库 ===
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=ai_code_review
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres123

# === Redis ===
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# === Neo4j (可选) ===
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=neo4j123

# === 安全 ===
JWT_SECRET=your-secret-key-at-least-32-characters-long
ENVIRONMENT=development

# === AI 审查 (DeepSeek) ===
DEEPSEEK_API_KEY=your-deepseek-api-key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# === GitHub (可选) ===
GITHUB_TOKEN=ghp_your_github_token
```

#### 3. 启动后端

```bash
# 激活 conda 环境
conda activate lxq

# 安装依赖
cd backend
pip install -r requirements.txt

# 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 4. 启动前端

```bash
# 新终端
cd frontend
npm install
npm run dev
```

#### 5. 一键启动 (可选)

```bash
python start_all.py
```

### 访问地址

| 服务 | 地址 |
|---|---|
| 前端界面 | http://localhost:3000 |
| 后端 API | http://localhost:8000 |
| API 文档 (Swagger) | http://localhost:8000/docs |
| API 文档 (ReDoc) | http://localhost:8000/redoc |

### 默认测试账户

```
邮箱: admin@example.com
密码: Admin123!
角色: ADMIN
```

## 📖 API 概览

### 认证 (`/api/v1/auth`)

| 方法 | 路径 | 描述 |
|---|---|---|
| POST | `/register` | 用户注册 |
| POST | `/login` | 用户登录，返回 JWT |
| POST | `/refresh` | 刷新 Access Token |
| POST | `/logout` | 用户登出 |
| GET | `/me` | 获取当前用户信息 |
| PUT | `/change-password` | 修改密码 |

### PR 分析 (`/api/v1/analysis`)

| 方法 | 路径 | 描述 |
|---|---|---|
| POST | `/projects/{id}/analyze` | 触发 PR 分析 |
| GET | `/analysis/{task_id}/status` | 查询分析任务状态 |
| POST | `/projects/{id}/pull-requests/{pr_id}/reanalyze` | 重新分析 |
| POST | `/projects/{id}/circular-dependencies` | 循环依赖检测 |

### 架构可视化 (`/api/v1/architecture`)

| 方法 | 路径 | 描述 |
|---|---|---|
| GET | `/{project_id}/branches` | 获取项目分支列表 |
| GET | `/{project_id}/branches/{branch_id}/architecture` | 分支架构图数据 |
| GET | `/dependencies/{project_id}` | 依赖关系图 |
| GET | `/architecture/{analysis_id}` | 架构分析结果 |
| POST | `/diagram/generate` | 基于审查生成架构图 |

### 代码审查 (`/api/v1/code-review`)

| 方法 | 路径 | 描述 |
|---|---|---|
| POST | `/webhook` | GitHub Webhook 接收 |
| GET | `/reviews` | 审查记录列表 |
| GET | `/reviews/{id}` | 审查详情 |

### GitHub 集成 (`/api/v1/github`)

| 方法 | 路径 | 描述 |
|---|---|---|
| GET | `/repos` | 获取用户仓库列表 |
| GET | `/repos/{owner}/{repo}/pulls` | 获取 PR 列表 |
| GET | `/repos/{owner}/{repo}/pulls/{number}/diff` | 获取 PR Diff |

### 其他端点

- **RBAC** (`/rbac/users`, `/rbac/projects`, `/rbac/audit`) — 角色权限管理
- **健康检查** (`/health`, `/health/ready`, `/health/live`) — 服务状态
- **用户设置** (`/user/settings`) — GitHub Token 等配置
- **审计日志** (`/audit-logs`) — 操作记录查询
- **监控指标** (`/metrics`) — Prometheus 指标
- **用户数据** (`/users`) — GDPR 数据导出/删除

## 🔐 认证说明

所有需要认证的 API 端点需要在 Header 中携带 JWT Token：

```
Authorization: Bearer <your_jwt_token>
```

### 用户角色

| 角色 | 权限 |
|---|---|
| `ADMIN` | 全部权限，用户管理，角色分配 |
| `DEVELOPER` | 项目访问，代码审查，架构查看 |
| `VIEWER` | 只读访问 |
| `VISITOR` | 注册后默认角色，受限访问 |

## 🔧 配置说明

所有配置通过环境变量管理 (`.env` 文件)，关键配置项：

| 变量 | 必需 | 默认值 | 描述 |
|---|---|---|---|
| `JWT_SECRET` | ✅ | dev-secret... | JWT 签名密钥 (≥32字符) |
| `POSTGRES_*` | ✅ | localhost | PostgreSQL 连接信息 |
| `REDIS_*` | ⚠️ | localhost | Redis 连接信息 (缓存可降级) |
| `NEO4J_*` | ⚠️ | localhost | Neo4j 连接信息 (图分析可降级) |
| `DEEPSEEK_API_KEY` | ⚠️ | - | DeepSeek AI API Key |
| `GITHUB_TOKEN` | ⚠️ | - | GitHub Personal Access Token |
| `ENVIRONMENT` | - | development | 运行环境 |

> ⚠️ = 可选，缺失时对应功能降级但不影响启动

## 🐳 Docker 部署

### 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Network (ai_review_network)        │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │PostgreSQL│  │  Redis   │  │  Neo4j   │  │  Nginx   │    │
│  │  :5432   │  │  :6379   │  │  :7687   │  │  :80/443 │◄───── 用户访问
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──┬───┬───┘    │
│       │              │             │           │   │         │
│       └──────────────┼─────────────┘           │   │         │
│                      │                         │   │         │
│              ┌───────┴────────┐                │   │         │
│              │   Backend      │◄───────────────┘   │         │
│              │  (FastAPI)     │                     │         │
│              │   :8000        │                     │         │
│              └────────────────┘                     │         │
│              ┌────────────────┐                     │         │
│              │   Frontend     │◄────────────────────┘         │
│              │  (Next.js)     │                               │
│              │   :3000        │                               │
│              └────────────────┘                               │
└─────────────────────────────────────────────────────────────┘
```

### 前置要求

- **Docker Engine 24+** & **Docker Compose V2** ([安装指南](https://docs.docker.com/engine/install/))
- 至少 **4 GB** 空闲内存（Neo4j 需要较多内存）
- 配置好 `.env` 文件（参考上方 [配置环境变量](#2-配置环境变量) 章节）

---

### 方式一：开发环境部署

开发环境支持 **热重载**，代码修改后自动生效，适合日常开发调试。

#### 1. 一键启动所有服务

```bash
# 在项目根目录执行
docker-compose up -d
```

#### 2. 查看启动状态

```bash
docker-compose ps
```

正常输出示例：

```
NAME                   STATUS                   PORTS
ai_review_postgres     Up (healthy)             0.0.0.0:5432->5432/tcp
ai_review_redis        Up (healthy)             0.0.0.0:6379->6379/tcp
ai_review_neo4j        Up (healthy)             0.0.0.0:7474->7474/tcp, 0.0.0.0:7687->7687/tcp
ai_review_backend      Up (healthy)             0.0.0.0:8000->8000/tcp
ai_review_frontend     Up                       0.0.0.0:3000->3000/tcp
```

#### 3. 初始化数据库 (首次部署)

```bash
# 进入后端容器执行数据库迁移
docker exec -it ai_review_backend alembic upgrade head
```

#### 4. 访问服务

| 服务 | 地址 | 说明 |
|---|---|---|
| 前端界面 | http://localhost:3000 | Next.js 开发服务器 |
| 后端 API | http://localhost:8000 | FastAPI  |
| Swagger 文档 | http://localhost:8000/docs | 交互式 API 文档 |
| Neo4j Browser | http://localhost:7474 | 图数据库可视化 |

#### 5. 查看日志

```bash
# 查看所有服务日志
docker-compose logs -f

# 只看后端日志
docker-compose logs -f backend

# 只看前端日志
docker-compose logs -f frontend
```

#### 6. 停止 / 销毁

```bash
# 停止服务 (保留数据卷)
docker-compose down

# 停止并删除数据卷 (完全重置)
docker-compose down -v
```

---

### 方式二：生产环境部署

生产环境使用 **Nginx 反向代理**、**多阶段构建镜像**，数据库端口不暴露到宿主机。

#### 1. 准备生产配置

确保 `.env` 中设置了安全的密码和密钥：

```env
# .env (生产环境 — 必须修改以下值)
POSTGRES_PASSWORD=<强密码>
REDIS_PASSWORD=<强密码>
NEO4J_PASSWORD=<强密码>
JWT_SECRET=<至少32字符的随机密钥>
ENVIRONMENT=production
DEEPSEEK_API_KEY=<你的API Key>
```

#### 2. 创建 SSL 证书目录 (可选，HTTPS)

```bash
mkdir -p nginx/ssl
# 将你的证书文件放入:
#   nginx/ssl/cert.pem
#   nginx/ssl/key.pem
```

#### 3. 构建并启动

```bash
docker-compose -f docker-compose.prod.yml up -d --build
```

#### 4. 初始化数据库

```bash
docker exec -it ai_review_backend alembic upgrade head
```

#### 5. 访问

| 服务 | 地址 | 说明 |
|---|---|---|
| 统一入口 | http://localhost (或 https://your-domain.com) | Nginx 反向代理 |
| API | http://localhost/api/ | 由 Nginx 转发到后端 |
| API 文档 | http://localhost/docs | Swagger UI |

---

### 各服务详解

#### 🐘 PostgreSQL (主数据库)

| 项目 | 值 |
|---|---|
| 镜像 | `postgres:16-alpine` |
| 容器名 | `ai_review_postgres` |
| 内部端口 | `5432` |
| 数据卷 | `postgres_data` |
| 健康检查 | `pg_isready` |

存储所有业务数据：用户、项目、审查记录、RBAC 权限等。

```bash
# 手动连接数据库
docker exec -it ai_review_postgres psql -U postgres -d ai_code_review

# 备份数据库
docker exec ai_review_postgres pg_dump -U postgres ai_code_review > backup.sql

# 恢复数据库
docker exec -i ai_review_postgres psql -U postgres ai_code_review < backup.sql
```

#### 🔴 Redis (缓存 & 速率限制)

| 项目 | 值 |
|---|---|
| 镜像 | `redis:7-alpine` |
| 容器名 | `ai_review_redis` |
| 内部端口 | `6379` |
| 数据卷 | `redis_data` |
| 内存限制 | 开发 256MB / 生产 512MB |

用于 JWT Session 缓存、API 速率限制计数器、DeepSeek API 调用缓存。

```bash
# 连接 Redis CLI
docker exec -it ai_review_redis redis-cli

# 查看缓存状态
docker exec -it ai_review_redis redis-cli info memory
```

#### 🔵 Neo4j (图数据库)

| 项目 | 值 |
|---|---|
| 镜像 | `neo4j:5-community` |
| 容器名 | `ai_review_neo4j` |
| Bolt 端口 | `7687` |
| Browser 端口 | `7474` (仅开发环境暴露) |
| 插件 | APOC |

存储代码架构关系：模块依赖图、类继承关系、循环依赖检测结果。

```bash
# 通过 cypher-shell 执行查询
docker exec -it ai_review_neo4j cypher-shell -u neo4j -p neo4j123

# 清空所有图数据
docker exec -it ai_review_neo4j cypher-shell -u neo4j -p neo4j123 "MATCH (n) DETACH DELETE n"
```

#### ⚡ Backend — FastAPI

| 项目 | 值 |
|---|---|
| 构建文件 | 开发: `backend/Dockerfile.dev`，生产: `backend/Dockerfile` |
| 容器名 | `ai_review_backend` |
| 内部端口 | `8000` |
| 健康检查 | `GET /health` |

**Docker 内服务发现 (关键)**：在 `docker-compose.yml` 中，环境变量会 **覆盖** `.env` 中的 `localhost` 为 Docker 服务名：

```yaml
environment:
  POSTGRES_HOST: postgres      # ← 不是 localhost，是 Docker 服务名
  REDIS_HOST: redis            # ← 同上
  NEO4J_URI: bolt://neo4j:7687 # ← 同上
```

这是容器间通信的核心机制 — Docker Compose 会自动将服务名解析为对应容器的 IP。

```bash
# 进入后端容器 Shell
docker exec -it ai_review_backend bash

# 运行数据库迁移
docker exec -it ai_review_backend alembic upgrade head

# 查看后端日志
docker logs -f ai_review_backend
```

#### 🎨 Frontend — Next.js

| 项目 | 值 |
|---|---|
| 构建文件 | 开发: `frontend/Dockerfile.dev`，生产: `frontend/Dockerfile.prod` |
| 容器名 | `ai_review_frontend` |
| 内部端口 | `3000` |

**前端如何调用后端 API**：

- **浏览器端 (客户端渲染)**：通过 `NEXT_PUBLIC_API_URL` 访问后端
  - 开发环境：`http://localhost:8000` (直接访问后端端口)
  - 生产环境：`/api` (通过 Nginx 反代)
- **服务端渲染 (SSR)**：通过 `NEXT_PUBLIC_BACKEND_URL` 在 Docker 内部网络直连后端
  - 值为 `http://backend:8000` (Docker 服务名)

```bash
# 查看前端日志
docker logs -f ai_review_frontend

# 重新构建前端镜像
docker-compose build frontend
```

#### 🌐 Nginx (仅生产环境)

| 项目 | 值 |
|---|---|
| 镜像 | `nginx:alpine` |
| 暴露端口 | `80`, `443` |
| 配置文件 | `nginx/nginx.conf` |

路由规则：

| 路径 | 代理到 | 说明 |
|---|---|---|
| `/api/*` | `backend:8000` | 后端 API |
| `/docs`, `/redoc` | `backend:8000` | API 文档 |
| `/health`, `/metrics` | `backend:8000` | 监控端点 |
| `/ws` | `backend:8000` | WebSocket |
| `/*` (其他) | `frontend:3000` | 前端页面 |

---

### Docker 文件清单

```
├── docker-compose.yml          # 开发环境编排 (5个服务)
├── docker-compose.prod.yml     # 生产环境编排 (6个服务，含 Nginx)
├── nginx/
│   └── nginx.conf              # Nginx 反向代理配置
├── backend/
│   ├── Dockerfile              # 后端生产镜像 (多阶段构建)
│   ├── Dockerfile.dev          # 后端开发镜像 (热重载)
│   └── .dockerignore           # 构建排除列表
├── frontend/
│   ├── Dockerfile              # 前端生产镜像
│   ├── Dockerfile.dev          # 前端开发镜像 (热重载)
│   └── Dockerfile.prod         # 前端生产优化镜像
└── backend/security/
    └── docker-compose.zap.yml  # OWASP ZAP 安全扫描 (按需启动)
```

---

### 常用运维命令

```bash
# 重新构建所有镜像
docker-compose build --no-cache

# 只重启后端
docker-compose restart backend

# 查看资源占用
docker stats

# 清理未使用的镜像/网络/卷
docker system prune -a

# 查看 Docker 网络中的容器连接
docker network inspect ai-based-quality-check-on-project-code-and-architecture_ai_review_network
```

### 常见问题

**Q: 后端报 `Connection refused` 连不上数据库？**
> 确保 `docker-compose.yml` 中 `POSTGRES_HOST` 设置为 `postgres` 而不是 `localhost`。容器间通信使用 Docker 服务名。

**Q: 前端页面加载了但 API 调用失败？**
> 开发环境检查 `NEXT_PUBLIC_API_URL` 是否为 `http://localhost:8000`；生产环境检查 Nginx 配置是否正确代理了 `/api/` 路径。

**Q: Neo4j 启动很慢？**
> Neo4j 首次启动需要初始化数据库，建议至少等待 30 秒。可通过 `docker logs -f ai_review_neo4j` 查看启动进度。

**Q: 如何在不影响数据的情况下更新代码？**
> ```bash
> git pull
> docker-compose up -d --build   # 只重建有变更的镜像
> ```

## 📄 License

MIT License
