# 🐳 Docker 一键部署指南

## 环境要求

| 软件 | 最低版本 | 说明 |
|------|---------|------|
| **Docker Desktop** | 4.0+ | [下载地址](https://docs.docker.com/desktop/) |
| **Docker Compose** | v2.0+ | Docker Desktop 自带 |
| **Git** | 2.30+ | 用于克隆仓库 |

> 💡 Windows 用户请确保 Docker Desktop 已启动并显示 "Engine running" 状态

---

## 快速部署（3 步完成）

### 第 1 步：克隆仓库

```bash
git clone https://github.com/lv-g-eng/ai--reviewer.git
cd ai--reviewer
```

### 第 2 步：配置环境变量

项目根目录已有 `.env` 文件，包含默认配置。如需自定义，可编辑以下关键项：

```bash
# 查看并按需修改 .env
cat .env
```

**主要配置项说明：**

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `POSTGRES_PASSWORD` | `postgres123` | 数据库密码 |
| `JWT_SECRET` | `dev-secret-key...` | JWT 签名密钥（生产环境请修改） |
| `DEEPSEEK_API_KEY` | (空) | DeepSeek AI API 密钥（可选，AI审查功能需要） |
| `GITHUB_TOKEN` | (空) | GitHub Personal Access Token（可选，同步仓库PR需要） |

### 第 3 步：一键启动

**方式一：使用启动脚本（推荐）**
```bash
python start_all.py --mode docker
```

**方式二：直接使用 Docker Compose**
```bash
docker compose up -d --build
```

等待所有容器启动（约 1-2 分钟），看到以下状态表示成功：
```
✔ Container ai_review_postgres    Healthy
✔ Container ai_review_redis       Healthy
✔ Container ai_review_neo4j       Healthy
✔ Container ai_review_backend     Healthy
✔ Container ai_review_frontend    Created
```

---

## 访问服务

| 服务 | 地址 | 说明 |
|------|------|------|
| **🌐 前端界面** | http://localhost:3000 | 主界面 |
| **📡 后端 API** | http://localhost:8000 | REST API |
| **📖 API 文档** | http://localhost:8000/docs | Swagger UI |
| **🗄️ Neo4j 浏览器** | http://localhost:7474 | 图数据库管理 |

### 默认登录账号

```
邮箱: admin@example.com
密码: Admin123!
```

---

## 服务架构

```
┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   Backend   │
│  (Next.js)  │     │  (FastAPI)  │
│  :3000      │     │  :8000      │
└─────────────┘     └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │PostgreSQL│ │  Redis   │ │  Neo4j   │
        │  :5432   │ │  :6379   │ │  :7687   │
        └──────────┘ └──────────┘ └──────────┘
```

---

## 常用 Docker 命令

```bash
# 查看容器状态
docker compose ps

# 查看日志（实时）
docker compose logs -f

# 只看后端日志
docker compose logs -f backend

# 停止所有服务
docker compose down

# 停止并清除数据（⚠️ 会删除数据库数据）
docker compose down -v

# 重新构建并启动（代码更新后）
docker compose up -d --build

# 进入后端容器调试
docker exec -it ai_review_backend bash

# 进入数据库
docker exec -it ai_review_postgres psql -U postgres -d ai_code_review
```

---

## 使用流程

1. **登录** → 使用默认账号登录系统
2. **添加项目** → 在 Projects 页面添加 GitHub 仓库（需要 GitHub Token）
3. **同步 PR** → 点击项目的 "同步" 按钮拉取 Pull Request 列表
4. **开始审查** → 在 Pull Requests 页面点击 "开始审查" 触发 AI 代码审查
5. **查看架构** → 在 Architecture 页面选择项目和分支查看代码架构图

---

## 故障排查

### 容器启动失败
```bash
# 查看详细错误日志
docker compose logs backend

# 检查端口占用
netstat -ano | findstr :8000
netstat -ano | findstr :3000

# 停止占用端口的进程后重试
docker compose down
docker compose up -d --build
```

### 数据库连接失败
```bash
# 检查 PostgreSQL 容器状态
docker compose ps postgres

# 手动初始化数据库扩展
docker exec ai_review_postgres psql -U postgres -d ai_code_review -c 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'
```

### 重置所有数据
```bash
docker compose down -v
docker compose up -d --build
```
