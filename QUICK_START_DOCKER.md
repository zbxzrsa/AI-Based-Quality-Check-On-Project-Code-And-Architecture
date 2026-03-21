# AI代码审查平台 - Docker容器化部署快速启动指南

## 项目概述

本项目已将AI代码审查平台从本地数据库安装迁移到现代化的Docker容器化基础设施，提供完整的PostgreSQL、Neo4j、Redis、pgAdmin数据库管理和前端-后端分离架构。

## 快速开始

### 1. 环境准备

确保系统已安装：

- Docker 20.0+
- Docker Compose 2.0+
- Python 3.8+ (可选，用于脚本)

### 2. 配置环境

```bash
# 复制环境模板
cp .env.template .env

# 编辑环境变量（使用你喜欢的编辑器）
nano .env
# 或
vim .env
# 或
code .env
```

在 `.env` 文件中设置以下必要配置：

```bash
# 数据库密码（使用openssl rand -hex 16生成）
POSTGRES_PASSWORD=your_secure_password_here
NEO4J_PASSWORD=your_secure_password_here
REDIS_PASSWORD=your_secure_password_here

# 安全密钥（使用openssl rand -hex 32生成）
JWT_SECRET=your_32_character_jwt_secret
SECRET_KEY=your_32_character_secret
SESSION_SECRET=your_32_character_session_secret
```

### 3. 启动Docker服务

```bash
# 后台启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看服务日志
docker-compose logs -f
```

### 4. 验证部署

```bash
# 运行健康检查
./setup-check.sh

# 运行连接测试
python scripts/test_db_connections.py
```

等待所有服务状态变为 "healthy"（约1-2分钟）。

## 访问服务

| 服务          | URL                   | 端口 | 说明            |
| ------------- | --------------------- | ---- | --------------- |
| 🔧 前端应用   | http://localhost:6066 | 6066 | Next.js前端界面 |
| 🌐 后端API    | http://localhost:8000 | 8000 | FastAPI后端服务 |
| 📊 pgAdmin    | http://localhost:5050 | 5050 | 数据库管理界面  |
| 🐘 PostgreSQL | localhost:5432        | 5432 | 主要关系数据库  |
| 🔗 Neo4j      | http://localhost:7474 | 7474 | 图数据库浏览器  |
| 🔴 Redis      | localhost:6379        | 6379 | 缓存和消息队列  |

**pgAdmin登录信息：**

- 邮箱：admin@example.com
- 密码：与POSTGRES_PASSWORD相同

## 数据迁移

如果你有现有的本地数据库需要迁移：

### 创建数据导出脚本

```bash
# 创建迁移脚本（如果需要）
cat > scripts/database_migration.py << 'EOF'
#!/usr/bin/env python3
import psycopg2
import os

print("数据迁移脚本需要手动创建")
print("参考scripts/目录中的示例")
EOF

chmod +x scripts/database_migration.py
```

### 手动迁移步骤

1. **导出现有数据库：**

```bash
# PostgreSQL导出
pg_dump -h localhost -U postgres -d ai_code_review > backup.sql

# Neo4j导出（使用Neo4j Browser）
# 登录Neo4j Browser (http://localhost:7474)
# 执行：CALL apoc.export.cypher.all('backup.cypher')
```

2. **导入到Docker数据库：**

```bash
# PostgreSQL导入
docker exec -i ai_review_postgres psql -U postgres -d ai_code_review < backup.sql

# Neo4j导入
docker cp backup.cypher ai_review_neo4j:/var/lib/neo4j/import/
docker exec ai_review_neo4j cypher-shell -u neo4j -p your_password < /var/lib/neo4j/import/backup.cypher
```

## 服务管理

### 常用命令

```bash
# 查看服务状态
docker-compose ps

# 查看特定服务日志
docker-compose logs backend
docker-compose logs postgres

# 重启服务
docker-compose restart backend

# 停止服务
docker-compose down

# 停止并清理数据（警告：会删除数据库）
docker-compose down -v

# 重建特定服务
docker-compose build backend

# 更新并重建
docker-compose up -d --build
```

### 故障排除

1. **端口冲突：**

   ```bash
   # 检查端口占用
   netstat -tulpn | grep :8000

   # 修改docker-compose.yml中的端口映射
   ```

2. **服务启动失败：**

   ```bash
   # 查看详细错误
   docker logs ai_review_backend
   docker logs ai_review_postgres

   # 重启服务
   docker-compose restart
   ```

3. **数据库连接失败：**
   ```bash
   # 测试连接
   docker exec ai_review_postgres pg_isready -U postgres
   docker exec ai_review_redis redis-cli ping
   ```

## 性能优化

### Docker资源配置

编辑 `docker-compose.yml` 中的资源限制：

```yaml
services:
  postgres:
    deploy:
      resources:
        limits:
          memory: 2G # 增加内存限制
          cpus: '2' # 增加CPU核心
```

### 数据库性能设置

在 `.env` 文件中调整：

```bash
# PostgreSQL性能
POSTGRES_SHARED_BUFFERS=512MB
POSTGRES_EFFECTIVE_CACHE_SIZE=2GB

# Neo4j内存设置
NEO4J_dbms_memory_heap_max_size=4G
NEO4J_dbms_memory_pagecache_size=2G
```

## 安全设置

### 生产环境配置

1. **修改默认端口：**

   ```yaml
   # docker-compose.yml
   ports:
     - '18800:8000' # 修改外部端口
   ```

2. **启用HTTPS：**

   ```bash
   # 配置Nginx反向代理
   # 参考nginx/nginx.conf.example
   ```

3. **防火墙设置：**
   ```bash
   # 限制访问端口
   ufw allow 18800/tcp  # 只开放必要端口
   ufw enable
   ```

## 监控和维护

### 健康监控

```bash
# 定期健康检查
./setup-check.sh

# 查看系统资源使用
docker stats

# 查看容器资源使用
docker exec ai_review_postgres ps aux
```

### 备份策略

```bash
# PostgreSQL备份
docker exec ai_review_postgres pg_dumpall -U postgres > backup_$(date +%Y%m%d).sql

# Neo4j备份
docker exec ai_review_neo4j cypher-shell -u neo4j -p your_password \
  "CALL apoc.export.cypher.all('backup_$(date +%Y%m%d).cypher')"

# Redis备份（如果重要）
docker exec ai_review_redis redis-cli save
```

## 故障恢复

### 恢复数据库

```bash
# PostgreSQL恢复
docker exec -i ai_review_postgres psql -U postgres < backup_20250212.sql

# Neo4j恢复
docker cp backup_20250212.cypher ai_review_neo4j:/var/lib/neo4j/import/
docker exec ai_review_neo4j cypher-shell -u neo4j -p your_password \
  < /var/lib/neo4j/import/backup_20250212.cypher
```

## 支持与联系方式

如有问题请检查：

1. Docker和Docker Compose版本
2. 系统资源是否充足
3. 端口是否被占用
4. 防火墙设置

查看详细日志：

```bash
docker-compose logs
```

---

**注意：** 生产环境部署前请确保进行充分测试，并考虑网络安全和数据备份策略。
