# Phase 3: 快速参考指南

## 🚀 快速启动

### 启动完整系统

```bash
docker-compose up -d

# 等待所有服务就绪 (约 30-60 秒)
docker-compose ps

# 检查健康状态
curl http://localhost:8000/health
```

### 验证所有 Worker

```bash
# 检查 Celery Worker 连接
celery -A app.celery_config celery_app inspect active

# 预期看到两个 Worker:
# - celery@ai-review-celery-worker-high
# - celery@ai-review-celery-worker-low
```

---

## 📋 常用命令

### 队列 PR 分析

```bash
curl -X POST http://localhost:8000/api/v1/analysis/projects/project-1/analyze?pr_id=pr-1 \
  -H "Authorization: Bearer <token>"

# 响应: { "task_id": "abc123...", "status": "PENDING" }
```

### 检查任务状态

```bash
curl http://localhost:8000/api/v1/analysis/abc123/status \
  -H "Authorization: Bearer <token>"

# 循环检查直到完成:
# "status": "PENDING" → "PROGRESS" → "SUCCESS"
```

### 手动触发架构检测

```bash
# 循环依赖检测
celery -A app.celery_config celery_app call \
  app.tasks.architectural_drift.detect_cyclic_dependencies \
  --args='["project-id"]' --queue=low_priority

# 层违规检测
celery -A app.celery_config celery_app call \
  app.tasks.architectural_drift.detect_layer_violations \
  --args='["project-id"]' --queue=low_priority

# 完整漂移报告
celery -A app.celery_config celery_app call \
  app.tasks.architectural_drift.detect_architectural_drift \
  --args='["project-id"]' --queue=low_priority
```

### 查看任务结果

```bash
# 列出所有活跃任务
celery -A app.celery_config celery_app inspect active

# 查看特定任务结果
celery -A app.celery_config celery_app inspect result <task_id>

# 查看队列长度
celery -A app.celery_config celery_app inspect active_queues
```

---

## 📊 Cypher 查询速查表

### 循环依赖

```cypher
# 查找所有循环依赖
MATCH (p:Project {projectId: "project-id"})-[:CONTAINS]->(m1:Module)
MATCH path = (m1)-[:DEPENDS_ON*]->(m1)
WHERE length(path) > 1
RETURN m1.name, [n IN nodes(path) | n.name] AS cycle

# 只查找直接循环 (最严重)
MATCH (m1:Module)-[:DEPENDS_ON]->(m2:Module)-[:DEPENDS_ON]->(m1)
RETURN m1.name, m2.name
```

### 层违规

```cypher
# 检查 Controller 直接依赖 Repository
MATCH (c:Module)-[:DEPENDS_ON*1..3]->(r:Module)
WHERE toLower(c.name) CONTAINS 'controller'
  AND toLower(r.name) CONTAINS 'repository'
  AND NOT EXISTS {
    MATCH (c)-[:DEPENDS_ON]->(s:Module)
    WHERE toLower(s.name) CONTAINS 'service'
    AND (s)-[:DEPENDS_ON]->(r)
  }
RETURN c.name, r.name
```

### 耦合指标

```cypher
# 计算每个模块的不稳定性指数
MATCH (m:Module)
OPTIONAL MATCH (m)-[:DEPENDS_ON]->(dep)
WITH m, count(DISTINCT dep) AS EC
OPTIONAL MATCH (dependent)-[:DEPENDS_ON]->(m)
WITH m, EC, count(DISTINCT dependent) AS AC
RETURN m.name, EC, AC,
       ROUND(toFloat(EC) / (EC + AC), 3) AS instability
ORDER BY instability DESC
```

---

## 🐛 快速故障排除

### 任务卡住了?

```bash
# 检查 Worker 状态
docker-compose logs celery-worker-high -f

# 如果卡住，重启 Worker
docker-compose restart celery-worker-high

# 清除所有待处理任务 (谨慎!)
redis-cli -a <PASSWORD> FLUSHDB
```

### Redis 连接错误?

```bash
# 测试 Redis 连接
redis-cli -h localhost -p 6379 -a <PASSWORD> ping
# 预期: PONG

# 如果不行，重启 Redis
docker-compose restart redis

# 检查密码
echo $REDIS_PASSWORD
```

### Neo4j 查询缓慢?

```cypher
# 添加索引加快查询
CREATE INDEX project_id IF NOT EXISTS ON :Project(projectId);
CREATE INDEX module_id IF NOT EXISTS ON :Module(moduleId);

# 检查查询计划
EXPLAIN MATCH (m:Module)-[:DEPENDS_ON*]->(m) RETURN m
```

### 内存不足?

```bash
# 检查 Worker 内存使用
docker stats celery-worker-high

# 如果过高，减少并发或增加内存
# docker-compose.yml:
celery-worker-high:
  environment:
    - CELERYD_CONCURRENCY=1  # 从 2 减少到 1
```

---

## 🔍 监控检查清单

### 每日检查

- [ ] 所有 Worker 都在运行: `docker-compose ps`
- [ ] 无错误的任务: `docker-compose logs | grep ERROR`
- [ ] Redis 健康: `redis-cli ping`
- [ ] Neo4j 可访问: `curl http://localhost:7474`

### 每周检查

- [ ] 漂移检测任务完成
- [ ] 循环依赖检测完成
- [ ] 层违规检测完成
- [ ] 处理任何架构问题

### 每月检查

- [ ] 数据库优化 (VACUUM, REINDEX)
- [ ] 日志轮转和清理
- [ ] 性能指标审查
- [ ] 更新依赖和安全补丁

---

## 📈 性能优化建议

### 优化 Worker 并发

```bash
# 高优先级 Worker (I/O 密集)
--concurrency=4 --pool=prefork

# 低优先级 Worker (CPU 密集)
--concurrency=1 --pool=prefork
```

### Cypher 查询优化

```cypher
# 添加 LIMIT 避免扫描整个数据库
MATCH (m:Module)
RETURN m LIMIT 1000

# 使用特定节点标签
MATCH (p:Project {projectId: "xyz"})-[:CONTAINS]->(m:Module)
INSTEAD OF
MATCH (p)-[:CONTAINS]->(m)

# 使用索引匹配
CREATE INDEX module_depends ON :Module(moduleId, type)
```

---

## 📚 关键文件位置

```
backend/
├── app/
│   ├── celery_config.py              ← Celery 配置 (调度, 重试等)
│   ├── tasks/
│   │   ├── pull_request_analysis.py  ← PR 分析任务
│   │   └── architectural_drift.py    ← 漂移检测任务
│   ├── services/
│   │   ├── cypher_queries.py         ← Cypher 查询库
│   │   └── neo4j_ast_service_extended.py ← Neo4j 服务
│   └── api/v1/endpoints/
│       └── pull_request.py           ← 分析端点
├── tests/
│   └── test_celery_async.py          ← 单元和集成测试
└── docker-compose.yml                ← 完整的 Docker 配置

docs/
└── PHASE_3_OPERATIONS_GUIDE.md       ← 完整的运维指南
```

---

## 🔗 API 端点速查

| 方法 | 端点                                                          | 功能         |
| ---- | ------------------------------------------------------------- | ------------ |
| POST | `/api/v1/analysis/projects/{id}/analyze?pr_id={pr}`           | 队列 PR 分析 |
| GET  | `/api/v1/analysis/{task_id}/status`                           | 检查任务状态 |
| POST | `/api/v1/analysis/projects/{id}/pull-requests/{pr}/reanalyze` | 重新分析 PR  |

---

## 🌐 监控工具

### Flower (Web UI)

```bash
pip install flower
celery -A app.celery_config celery_app flower

# 访问
http://localhost:5555
```

### Celery CLI

```bash
# 活跃任务
celery inspect active

# Worker 统计
celery inspect stats

# 注册的任务
celery inspect registered

# 队列
celery inspect active_queues
```

### Logs

```bash
# 实时日志
docker-compose logs -f celery-worker-high

# 查找错误
docker-compose logs celery-worker-high | grep ERROR

# 查找特定任务
docker-compose logs | grep "task_id"
```

---

## ⏰ 定时任务时间表

| 任务         | 频率   | 时间 (UTC)      | 队列         |
| ------------ | ------ | --------------- | ------------ |
| 完整漂移检测 | 每周   | 周一 2:00       | low_priority |
| 循环依赖检测 | 每天   | 3:00            | low_priority |
| 层违规检测   | 2次/周 | 周一、周四 4:00 | low_priority |
| 健康检查     | 每小时 | 整点            | default      |

---

## 🆘 获取帮助

### 查看完整文档

- [PHASE_3_OPERATIONS_GUIDE.md](./PHASE_3_OPERATIONS_GUIDE.md) - 完整运维指南
- [cypher_queries.py](./backend/app/services/cypher_queries.py) - Cypher 查询库与说明
- [test_celery_async.py](./backend/tests/test_celery_async.py) - 测试用例与示例

### 常见错误信息

```
❌ "Connection refused (Redis)"
→ 检查 Redis 容器: docker-compose restart redis

❌ "Task timed out"
→ 增加超时或优化查询性能

❌ "Worker not available"
→ 重启 Worker: docker-compose restart celery-worker-high

❌ "Cypher syntax error"
→ 检查查询拼写，使用 Neo4j Browser 测试
```

---

**最后更新**: 2024 年 1 月 17 日
**版本**: 3.0
**作者**: AI Code Review Team
