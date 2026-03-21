# AI Code Review Platform

AI驱动的代码审查平台，提供智能代码分析、架构审查和合规性检查。

---

## 📋 Table of Contents

### 1. Quick Start (快速开始)

| Document | Description |
| -------- | ----------- |
| [QUICK_START.md](./QUICK_START.md) | 完整快速开始指南 (1012行) |
| [QUICK_START_DOCKER.md](./QUICK_START_DOCKER.md) | Docker 安装 (303行) |
| [QUICK_START_PRODUCTION.md](./QUICK_START_PRODUCTION.md) | 生产环境快速开始 (326行) |

### 2. Development (开发)

| Document | Description |
| -------- | ----------- |
| [CODING_STANDARDS.md](./CODING_STANDARDS.md) | 编码规范 (556行) |
| [TROUBLESHOOTING_GUIDE.md](./TROUBLESHOOTING_GUIDE.md) | 故障排查指南 (968行) |
| [TECHNICAL_DEBT_TRACKER.md](./TECHNICAL_DEBT_TRACKER.md) | 技术债追踪 (198行) |

### 3. Deployment (部署)

| Document | Description |
| -------- | ----------- |
| [DEPLOYMENT.md](./DEPLOYMENT.md) | 部署指南 (497行) |
| [QUICK_START_PRODUCTION_MIGRATION.md](./QUICK_START_PRODUCTION_MIGRATION.md) | 迁移指南 (425行) |
| [PRODUCTION_MIGRATION_EXECUTION_PLAN.md](./PRODUCTION_MIGRATION_EXECUTION_PLAN.md) | 迁移执行计划 (767行) |

### 4. Project Reports (项目报告)

| Document | Description |
| -------- | ----------- |
| [ARCHITECTURE_REFACTORING_SUMMARY.md](./ARCHITECTURE_REFACTORING_SUMMARY.md) | 架构重构总结 |
| [REFACTORING_PLAN.md](./REFACTORING_PLAN.md) | 重构计划 |
| [REFACTORING_SLIMMING_PLAN.md](./REFACTORING_SLIMMING_PLAN.md) | 代码精简计划 (664行) |

---

## 🚀 Quick Links (快速链接)

| 需求 | 前往 |
| ---- | ---- |
| 新开发者入门 | [QUICK_START.md](./QUICK_START.md) |
| 生产部署 | [DEPLOYMENT.md](./DEPLOYMENT.md) |
| 编码规范 | [CODING_STANDARDS.md](./CODING_STANDARDS.md) |
| 故障排查 | [TROUBLESHOOTING_GUIDE.md](./TROUBLESHOOTING_GUIDE.md) |

---

## ⚡ Quick Start (30秒快速开始)

### 方式1: Docker (推荐)

```bash
# 克隆项目
git clone <repository-url>
cd AI-Based-Quality-Check-On-Project-Code-And-Architecture

# 启动所有服务
docker-compose up -d

# 访问应用
# 前端: http://localhost:6066
# 后端: http://localhost:8000
# API文档: http://localhost:8000/docs
```

### 方式2: 手动安装

```bash
# 1. 克隆项目
git clone <repository-url>
cd AI-Based-Quality-Check-On-Project-Code-And-Architecture

# 2. 后端设置
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# .\venv\Scripts\Activate.ps1  # Windows
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head

# 3. 前端设置
cd ../frontend
npm install
npm run dev

# 4. 访问
# 前端: http://localhost:6066
# 后端: http://localhost:8000
```

---

## 📁 Documentation Structure (文档结构)

```
├── Root (当前目录)
│   ├── QUICK_START.md          # 完整快速开始 (1012行)
│   ├── QUICK_START_DOCKER.md   # Docker 快速开始 (303行)
│   ├── DEPLOYMENT.md           # 生产部署指南 (497行)
│   ├── CODING_STANDARDS.md    # 编码规范 (556行)
│   ├── TROUBLESHOOTING_GUIDE.md # 故障排查 (968行)
│   ├── README.md               # 本文件
│   └── ...
│
├── docs/                       # 详细文档
│   ├── ARCHITECTURE.md         # 系统架构
│   ├── SECURITY_PROCEDURES.md  # 安全指南
│   ├── OPERATIONS_RUNBOOK.md   # 运维手册
│   ├── api/                    # API 文档
│   └── ...
│
└── backend/                    # 后端源码
```

---

## 📊 Stats (统计)

| 指标 | 数量 |
| ---- | ---- |
| 根目录 Markdown 文件 | 24 |
| docs 目录文件 | 94+ |
| 总文档数 | 118+ |

---

## 🖥️ System Requirements (系统要求)

- **Python**: 3.11+ (推荐 3.13)
- **Node.js**: 18.0.0+ (推荐 LTS)
- **PostgreSQL**: 14+
- **Neo4j**: 5.0+
- **Redis**: 7.0+
- **Docker**: 20.10+ (可选)

---

## 🔧 Common Commands (常用命令)

### 后端

```bash
cd backend

# 激活虚拟环境
source venv/bin/activate

# 运行服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 运行测试
pytest

# 代码检查
ruff check app/
ruff format app/
black --check app/
mypy app/
```

### 前端

```bash
cd frontend

# 安装依赖
npm install

# 开发模式
npm run dev

# 构建生产版本
npm run build

# 代码检查
npm run lint
```

### Docker

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 重建服务
docker-compose up -d --build
```

---

## 🗂️ 缓存管理

### 缓存类型说明

| 缓存类型 | 目录 | 作用 | 大小 | 是否保留 |
|---------|------|------|------|----------|
| MyPy 类型检查 | `.mypy_cache/` | 存储类型检查结果 | ~45MB | ✅ 保留 |
| Ruff 代码检查 | `.ruff_cache/` | 缓存 linter 分析结果 | ~8MB | ✅ 保留 |
| Python 字节码 | `__pycache__/` | 编译后的字节码 | 小 | ✅ 保留 |
| Pytest 测试 | `.pytest_cache/` | 测试运行状态和结果 | 小 | ✅ 保留 |

### 清理缓存

```bash
# 手动清理
rm -rf .mypy_cache backend/.mypy_cache
rm -rf .ruff_cache backend/.ruff_cache
rm -rf __pycache__ backend/__pycache__
```

### 何时清理缓存

- 💾 **磁盘空间不足时**
- 🔧 **工具行为异常时** - 缓存可能损坏
- 🐍 **切换 Python 版本后** - 字节码不兼容
- 🔄 **大规模重构后** - 避免过时的缓存信息

> **注意:** 这些缓存文件会在下次运行相应工具时自动重新生成。

---

## 🔍 Troubleshooting (常见问题)

### 后端无法启动

1. 检查 Python 版本: `python --version` (需要 3.11+)
2. 检查依赖安装: `pip list | grep -E "fastapi|uvicorn|pydantic"`
3. 检查环境变量: 确保 `.env` 文件存在且配置正确
4. 检查端口占用: `lsof -i :8000` 或 `netstat -ano | findstr :8000`

### 前端无法启动

1. 检查 Node 版本: `node --version` (需要 18+)
2. 检查 npm 安装: `npm install`
3. 清除缓存: `rm -rf node_modules/.cache`
4. 重新安装: `rm -rf node_modules && npm install`

### 数据库连接失败

1. 检查 PostgreSQL 运行状态: `docker-compose ps postgres`
2. 检查连接字符串: 确保 `.env` 中 `DATABASE_URL` 正确
3. 检查防火墙: 确保端口 5432 可访问
4. 查看日志: `docker-compose logs postgres`

### API 返回 500 错误

1. 查看后端日志获取详细错误信息
2. 检查数据库连接和迁移状态: `alembic current`
3. 验证环境变量配置
4. 运行测试检查: `pytest tests/`

### 更多故障排查

详见 [TROUBLESHOOTING_GUIDE.md](./TROUBLESHOOTING_GUIDE.md) (968行详细指南)

---

## 📚 Additional Documentation (其他文档)

### 核心指南

- [CODING_STANDARDS.md](./CODING_STANDARDS.md) - 编码规范和最佳实践
- [DEPLOYMENT.md](./DEPLOYMENT.md) - 生产环境部署指南
- [ARCHITECTURE_REFACTORING_SUMMARY.md](./ARCHITECTURE_REFACTORING_SUMMARY.md) - 架构重构总结

### 运维文档

- [TROUBLESHOOTING_GUIDE.md](./TROUBLESHOOTING_GUIDE.md) - 故障排查指南
- [PRODUCTION_MIGRATION_EXECUTION_PLAN.md](./PRODUCTION_MIGRATION_EXECUTION_PLAN.md) - 迁移执行计划
- [MEMORY_OPTIMIZATION_PLAN.md](./MEMORY_OPTIMIZATION_PLAN.md) - 内存优化计划

### 参考文档

- [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) - 系统架构详情
- [docs/API.md](./docs/API.md) - API 参考文档
- [docs/SECURITY_PROCEDURES.md](./docs/SECURITY_PROCEDURES.md) - 安全操作指南

---

## 📈 Project Optimization (项目优化)

本项目已进行以下优化:

- ✅ 统一代码风格 (ruff, black)
- ✅ 消除重复代码 (metrics 模块, CircuitBreaker)
- ✅ 清理遗留文件 (refactored_* 文件)
- ✅ 修复语法错误 (测试文件)
- ✅ 统一枚举定义 (common/shared/enums)

详见 [REFACTORING_SLIMMING_PLAN.md](./REFACTORING_SLIMMING_PLAN.md)

---

## 🤝 Contributing (贡献指南)

1. 遵循 [CODING_STANDARDS.md](./CODING_STANDARDS.md) 中的编码规范
2. 运行 `ruff check` 和 `ruff format` 格式化代码
3. 确保所有测试通过: `pytest`
4. 提交前进行类型检查: `mypy app/`

---

## 📄 License (许可证)

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

---

> 💡 **提示:** 详细文档请查看各独立 Markdown 文件。快速参考请查看本文件的常用命令部分。
