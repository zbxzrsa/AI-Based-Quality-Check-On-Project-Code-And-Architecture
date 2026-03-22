# 🚀 AI Code Review Platform - 操作手册

**完整的安装、配置和运行指南**

---

## 📋 目录

1. [系统要求](#系统要求)
2. [快速启动](#快速启�?
3. [详细安装步骤](#详细安装步骤)
4. [环境配置](#环境配置)
5. [数据库设置](#数据库设�?
6. [启动服务](#启动服务)
7. [登录系统](#登录系统)
8. [GitHub OAuth 配置](#github-oauth-配置)
9. [验证安装](#验证安装)
10. [故障排查](#故障排查)
11. [常用操作](#常用操作)

---

## 系统要求

### 必需软件

- **Python**: 3.11+ (推荐 3.13)
- **Node.js**: 18.0.0+ (推荐 LTS 版本)
- **npm**: 9.0.0+
- **PostgreSQL**: 14+
- **Neo4j**: 5.0+
- **Redis**: 7.0+

### 可选工�?

- **Docker Desktop**: 用于容器化部�?
- **Git**: 版本控制

### 系统资源

- 至少 4GB 可用内存
- 至少 10GB 可用磁盘空间

---

## 快速启�?

### 方式 1: 手动启动（推荐用于开发）

#### 1. 克隆项目

```bash
git clone <repository-url>
cd AI-Based-Quality-Check-On-Project-Code-And-Architecture
```

#### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.template .env
cp frontend/.env.example frontend/.env.local

# 编辑配置文件
# Windows: notepad .env
# Linux/Mac: nano .env
```

#### 3. 启动后端

```bash
cd backend

# 创建虚拟环境
python -m venv venv

# 激活虚拟环�?
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install --upgrade pip
pip install -r requirements.txt

# 运行数据库迁�?
alembic upgrade head

# 启动后端服务�?
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 4. 启动前端（新终端窗口�?

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

#### 5. 访问应用

- 前端: http://localhost:6066
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs

### 方式 2: Docker 启动

```bash
# 启动所有服�?
docker-compose up -d

# 查看服务状�?
docker-compose ps

# 查看日志
docker-compose logs -f
```

---

## 详细安装步骤

### 后端安装

#### 步骤 1: 进入后端目录

```bash
cd backend
```

#### 步骤 2: 创建 Python 虚拟环境

```bash
python -m venv venv
```

#### 步骤 3: 激活虚拟环�?

**Windows PowerShell:**
```powershell
.\venv\Scripts\Activate.ps1
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

#### 步骤 4: 升级 pip

```bash
pip install --upgrade pip
```

#### 步骤 5: 安装依赖

```bash
# 安装生产依赖
pip install -r requirements.txt

# 安装测试依赖（可选）
pip install -r requirements-test.txt

# 安装开发工具（可选）
pip install black isort ruff mypy pytest
```

#### 步骤 6: 配置环境变量

```bash
# 复制模板
cp .env.example .env

# 编辑配置
# Windows: notepad .env
# Linux/Mac: nano .env
```

#### 步骤 7: 运行数据库迁�?

```bash
alembic upgrade head
```

#### 步骤 8: 验证后端安装

```bash
# 运行测试
pytest

# 检查代码格�?
black --check app/
isort --check app/

# 运行 linting
ruff check app/
```

### 前端安装

#### 步骤 1: 进入前端目录

```bash
cd frontend
```

#### 步骤 2: 检�?Node.js 版本

```bash
node --version  # 应该�?18.0.0+
npm --version   # 应该�?9.0.0+
```

#### 步骤 3: 安装依赖

```bash
npm install
```

#### 步骤 4: 配置环境变量

```bash
# 复制模板
cp .env.example .env.local

# 编辑配置
# Windows: notepad .env.local
# Linux/Mac: nano .env.local
```

#### 步骤 5: 验证前端安装

```bash
# 运行 linting
npm run lint

# 运行类型检�?
npm run type-check

# 运行测试（可选）
npm test
```

---

## 环境配置

### 后端环境变量 (.env)

```bash
# 数据库配�?
POSTGRES_DB=ai_code_review
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Neo4j 配置
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password
NEO4J_URI=bolt://localhost:7687
NEO4J_DATABASE=neo4j

# Redis 配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# 安全密钥（使�?openssl rand -hex 32 生成�?
JWT_SECRET=your_jwt_secret_min_32_chars
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
SECRET_KEY=your_app_secret_min_32_chars
SESSION_SECRET=your_session_secret_min_32_chars

# 应用配置
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
PROJECT_NAME="AI Code Review Platform"
API_V1_STR=/api/v1

# GitHub OAuth（可选）
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
GITHUB_TOKEN=
GITHUB_WEBHOOK_SECRET=

# LLM API Keys（可选）
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
```

### 前端环境变量 (.env.local)

```bash
# API 配置
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000

# NextAuth 配置
NEXTAUTH_URL=http://localhost:6066
NEXTAUTH_SECRET=your_nextauth_secret_min_32_chars

# GitHub OAuth（可选）
NEXT_PUBLIC_GITHUB_CLIENT_ID=
```

---

## 数据库设�?

### PostgreSQL 设置

#### 1. 安装 PostgreSQL

**Windows:**
- 下载: https://www.postgresql.org/download/windows/
- 运行安装程序，记住设置的密码

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
```

**macOS:**
```bash
brew install postgresql
brew services start postgresql
```

#### 2. 创建数据�?

```bash
# 连接�?PostgreSQL
psql -U postgres

# 创建数据�?
CREATE DATABASE ai_code_review;

# 创建用户（如果需要）
CREATE USER your_user WITH PASSWORD 'your_password';

# 授予权限
GRANT ALL PRIVILEGES ON DATABASE ai_code_review TO your_user;

# 退�?
\q
```

#### 3. 更新 .env 文件

```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=ai_code_review
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
```

### Neo4j 设置

#### 1. 安装 Neo4j

**Windows/Mac:**
- 下载 Neo4j Desktop: https://neo4j.com/download/
- 创建新数据库，设置密�?

**Linux:**
```bash
# 添加 Neo4j 仓库
wget -O - https://debian.neo4j.com/neotechnology.gpg.key | sudo apt-key add -
echo 'deb https://debian.neo4j.com stable latest' | sudo tee /etc/apt/sources.list.d/neo4j.list

# 安装
sudo apt update
sudo apt install neo4j

# 启动服务
sudo systemctl start neo4j
```

#### 2. 配置 Neo4j

```bash
# 访问 Neo4j Browser
http://localhost:7474

# 首次登录
用户�? neo4j
密码: neo4j
# 系统会要求修改密�?
```

#### 3. 更新 .env 文件

```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_new_password
NEO4J_DATABASE=neo4j
```

### Redis 设置

#### 1. 安装 Redis

**Windows:**
- 下载: https://github.com/microsoftarchive/redis/releases
- 或使�?WSL2 安装 Linux 版本

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis-server
```

**macOS:**
```bash
brew install redis
brew services start redis
```

#### 2. 验证 Redis

```bash
redis-cli ping
# 应该返回: PONG
```

#### 3. 更新 .env 文件

```bash
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=  # 本地开发通常为空
REDIS_DB=0
```

---

## 启动服务

### 启动后端服务�?

```bash
cd backend

# 激活虚拟环�?
# Windows:
.\venv\Scripts\Activate.ps1
# Linux/Mac:
source venv/bin/activate

# 启动服务�?
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**预期输出:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**访问:**
- API: http://localhost:8000
- 文档: http://localhost:8000/docs
- 健康检�? http://localhost:8000/health

### 启动前端服务�?

```bash
cd frontend

# 启动开发服务器
npm run dev
```

**预期输出:**
```
> frontend@0.1.0 dev
> next dev

   �?Next.js 14.x.x
   - Local:        http://localhost:6066
   - Network:      http://192.168.x.x:3000

 �?Ready in 2.5s
```

**访问:**
- 应用: http://localhost:6066
- 登录: http://localhost:6066/login
- 注册: http://localhost:6066/register

---

## 登录系统

### 创建管理员账�?

首次使用需要创建管理员账号�?

```bash
cd backend

# 激活虚拟环�?
# Windows:
.\venv\Scripts\Activate.ps1
# Linux/Mac:
source venv/bin/activate

# 创建默认管理�?
python scripts/create_admin_user.py

# 或创建自定义管理�?
python scripts/create_admin_user.py \
  --email your-admin@example.com \
  --password YourSecurePass123! \
  --name "Your Name"
```

### 默认管理员凭�?

**Email:** `admin@example.com`  
**密码:** `change-me-strong-password`

### 登录步骤

1. 访问 http://localhost:6066/login
2. 输入 Email 和密�?
3. 点击 "Sign in" 按钮
4. 登录成功后跳转到 Dashboard

### 注册新用�?

1. 访问 http://localhost:6066/register
2. 填写信息�?
   - Full Name（全名）
   - Email（邮箱）
   - Password（密码，至少8字符，包含大小写字母和数字）
   - Confirm Password（确认密码）
3. 勾选同意条�?
4. 点击 "Create account"

### 密码要求

- 至少 8 个字�?
- 至少 1 个大写字�?
- 至少 1 个小写字�?
- 至少 1 个数�?
- 至少 1 个特殊字�?(!@#$%^&*()_+-=[]{}|;:,.<>?)

---

## GitHub OAuth 配置

### 步骤 1: 创建 GitHub OAuth 应用

1. 访问 GitHub Settings: https://github.com/settings/developers
2. 点击 "OAuth Apps" �?"New OAuth App"
3. 填写信息:
   - **Application name**: AI Code Review Platform
   - **Homepage URL**: `http://localhost:6066`
   - **Authorization callback URL**: `http://localhost:6066/api/github/callback`
4. 点击 "Register application"
5. 记录 **Client ID** 和生�?**Client Secret**

### 步骤 2: 配置后端

编辑 `.env` 文件:

```bash
GITHUB_CLIENT_ID=你的_GitHub_Client_ID
GITHUB_CLIENT_SECRET=你的_GitHub_Client_Secret
```

### 步骤 3: 配置前端

编辑 `frontend/.env.local` 文件:

```bash
NEXT_PUBLIC_GITHUB_CLIENT_ID=你的_GitHub_Client_ID
```

### 步骤 4: 重启服务

```bash
# 重启后端（Ctrl+C 停止，然后重新运行）
cd backend
uvicorn app.main:app --reload

# 重启前端（Ctrl+C 停止，然后重新运行）
cd frontend
npm run dev
```

### 步骤 5: 测试 GitHub 集成

1. 访问 http://localhost:6066/projects
2. 点击 "Add Project"
3. 点击 "Connect with GitHub"
4. 应该跳转�?GitHub 授权页面
5. 授权后返回应�?

---

## 验证安装

### 检查后�?

```bash
# 检查健康状�?
curl http://localhost:8000/health

# 或使用浏览器访问
http://localhost:8000/health

# 预期响应:
{"status":"healthy"}
```

### 检查前�?

```bash
# 访问前端
http://localhost:6066

# 应该看到登录页面�?Dashboard
```

### 检查数据库连接

```bash
# PostgreSQL
psql -U postgres -d ai_code_review -c "SELECT 1;"

# Neo4j
# 访问 http://localhost:7474
# 运行查询: RETURN 1

# Redis
redis-cli ping
# 应该返回: PONG
```

### 运行测试

```bash
# 后端测试
cd backend
pytest

# 前端测试
cd frontend
npm test
```

---

## 故障排查

### 后端无法启动

#### 问题: 端口 8000 被占�?

```bash
# Windows: 查找占用端口的进�?
netstat -ano | findstr :8000

# Linux/Mac:
lsof -i :8000

# 停止进程或更改端�?
uvicorn app.main:app --reload --port 8001
```

#### 问题: 数据库连接失�?

```bash
# 检�?PostgreSQL 是否运行
# Windows:
Get-Service postgresql*

# Linux:
sudo systemctl status postgresql

# 检查连接字符串
# 确保 .env 中的数据库配置正�?
```

#### 问题: 模块导入错误

```bash
# 重新安装依赖
pip install -r requirements.txt --force-reinstall

# 检查虚拟环境是否激�?
which python  # Linux/Mac
where python  # Windows
```

### 前端无法启动

#### 问题: 端口 3000 被占�?

```bash
# Windows:
netstat -ano | findstr :3000

# Linux/Mac:
lsof -i :3000

# 或更改端�?
npm run dev -- -p 3001
```

#### 问题: 模块未找�?

```bash
# 删除 node_modules �?package-lock.json
rm -rf node_modules package-lock.json

# 重新安装
npm install
```

#### 问题: 构建错误

```bash
# 清理缓存
rm -rf .next

# 重新构建
npm run build
```

### 数据库问�?

#### PostgreSQL 连接超时

```bash
# 检�?PostgreSQL 是否运行
sudo systemctl status postgresql

# 重启 PostgreSQL
sudo systemctl restart postgresql

# 检查防火墙
sudo ufw allow 5432/tcp
```

#### Neo4j 无法连接

```bash
# 检�?Neo4j 是否运行
sudo systemctl status neo4j

# 重启 Neo4j
sudo systemctl restart neo4j

# 检查配�?
cat /etc/neo4j/neo4j.conf
```

#### Redis 连接失败

```bash
# 检�?Redis 是否运行
sudo systemctl status redis

# 重启 Redis
sudo systemctl restart redis

# 测试连接
redis-cli ping
```

### GitHub OAuth 问题

#### 错误: "redirect_uri is not associated with this application"

**解决方案:**
1. 检�?GitHub OAuth 应用的回�?URL
2. 必须完全匹配: `http://localhost:6066/api/github/callback`
3. 确保没有多余的斜杠或空格
4. 重启前端服务�?

#### 错误: "Configuration Error: GitHub Client ID is not configured"

**解决方案:**
1. 检�?`frontend/.env.local` 文件是否存在
2. 确认 `NEXT_PUBLIC_GITHUB_CLIENT_ID` 已设�?
3. 重启前端服务�?

---

## 常用操作

### 停止服务

```bash
# 停止后端: 在后端终端按 Ctrl+C
# 停止前端: 在前端终端按 Ctrl+C
```

### 重启服务

```bash
# 重启后端
cd backend
# �?Ctrl+C 停止
uvicorn app.main:app --reload

# 重启前端
cd frontend
# �?Ctrl+C 停止
npm run dev
```

### 查看日志

```bash
# 后端日志在终端直接显�?

# 前端日志在终端直接显�?

# 查看数据库日�?
# PostgreSQL:
sudo tail -f /var/log/postgresql/postgresql-14-main.log

# Neo4j:
sudo tail -f /var/log/neo4j/neo4j.log
```

### 清理缓存

```bash
# 清理前端缓存
cd frontend
rm -rf .next .swc
npm run dev

# 清理后端缓存
cd backend
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
```

### 更新依赖

```bash
# 更新后端依赖
cd backend
pip install --upgrade -r requirements.txt

# 更新前端依赖
cd frontend
npm update
```

### 运行数据库迁�?

```bash
cd backend

# 查看当前版本
alembic current

# 升级到最新版�?
alembic upgrade head

# 降级一个版�?
alembic downgrade -1

# 创建新迁�?
alembic revision --autogenerate -m "描述"
```

### 创建新用�?

```bash
# 通过脚本创建
cd backend
python scripts/create_admin_user.py \
  --email user@example.com \
  --password SecurePass123! \
  --name "User Name"

# 或通过 API
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!",
    "full_name": "User Name"
  }'
```

### 备份数据�?

```bash
# 备份 PostgreSQL
pg_dump -U postgres ai_code_review > backup_$(date +%Y%m%d).sql

# 恢复 PostgreSQL
psql -U postgres ai_code_review < backup_20240101.sql

# 备份 Neo4j
neo4j-admin database dump neo4j --to-path=/backups/

# 恢复 Neo4j
neo4j-admin database load neo4j --from=/backups/neo4j.dump
```

---

## Docker 部署（可选）

### 使用 Docker Compose

```bash
# 启动所有服�?
docker-compose up -d

# 查看服务状�?
docker-compose ps

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 停止并删除数�?
docker-compose down -v
```

### Docker 服务端点

| 服务 | 端口 | URL |
|------|------|-----|
| 前端 | 6066 | http://localhost:6066 |
| 后端 | 8000 | http://localhost:8000 |
| PostgreSQL | 5432 | - |
| Neo4j | 7474 | http://localhost:7474 |
| Redis | 6379 | - |

---

## 生产环境部署

### 安全检查清�?

- [ ] 修改所有默认密�?
- [ ] 使用强密码（至少 16 字符�?
- [ ] 启用 HTTPS
- [ ] 配置防火�?
- [ ] 启用数据库备�?
- [ ] 配置日志轮转
- [ ] 设置监控告警
- [ ] 限制数据库访�?
- [ ] 启用 CORS 白名�?
- [ ] 配置 Rate Limiting

### 环境变量

```bash
# 生产环境设置
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING

# 使用强密�?
JWT_SECRET=$(openssl rand -hex 32)
SECRET_KEY=$(openssl rand -hex 32)
SESSION_SECRET=$(openssl rand -hex 32)
```

---

## 获取帮助

### 文档

- [架构文档](docs/ARCHITECTURE.md)
- [用户指南](docs/USER_GUIDE.md)
- [部署指南](docs/DEPLOYMENT_GUIDE.md)
- [API 文档](http://localhost:8000/docs)

### 常见问题

1. 检查本文档的故障排查部�?
2. 查看后端日志
3. 查看前端控制�?
4. 检查数据库连接

---

**🎉 安装完成！现在可以开始使�?AI Code Review Platform�?*
