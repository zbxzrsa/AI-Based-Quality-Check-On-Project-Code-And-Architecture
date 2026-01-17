# Phase 3: 系统优化与运维 - 完整运作指南

## 目录

1. [异步任务队列 (Redis + Celery)](#异步任务队列)
2. [架构漂移检测查询](#架构漂移检测)
3. [Docker Compose 配置](#docker-compose-配置)
4. [运行与部署](#运行与部署)
5. [监控与调试](#监控与调试)
6. [故障排除](#故障排除)

---

## 异步任务队列

### 架构概述

```
GitHub Webhook
     ↓
FastAPI Endpoint (立即响应)
     ↓
Celery Task Queue (Redis)
     ↓
分为两个 Worker:
  - High Priority: PR 分析 (并发: 2)
  - Low Priority: 架构漂移检测 (并发: 1)
     ↓
存储结果 (PostgreSQL)
```

### 关键特性

✅ **非阻塞 API**: 端点立即返回 task_id，无需等待分析完成
✅ **优先级队列**: PR 分析优先级高，漂移检测优先级低
✅ **自动重试**: 失败自动重试，最多 3 次
✅ **任务追踪**: 通过 task_id 轮询任务状态
✅ **定时调度**: 使用 Celery Beat 实现周期性任务

### API 端点

#### 1. 队列 PR 分析

```bash
POST /api/v1/analysis/projects/{project_id}/analyze?pr_id={pr_id}

Response (立即返回):
{
  "task_id": "abc123xyz789",
  "status": "PENDING",
  "pr_id": "pr-1",
  "message": "PR analysis queued and will begin shortly"
}

响应时间: < 50ms ✓
```

#### 2. 检查任务状态

```bash
GET /api/v1/analysis/{task_id}/status

Response (PENDING):
{
  "task_id": "abc123xyz789",
  "status": "PENDING",
  "result": null,
  "error": null
}

Response (SUCCESS):
{
  "task_id": "abc123xyz789",
  "status": "SUCCESS",
  "result": {
    "pr_id": "pr-1",
    "status": "completed",
    "issues_found": 5,
    "risk_score": 45.5,
    "confidence_score": 0.92
  },
  "error": null
}

Response (FAILURE):
{
  "task_id": "abc123xyz789",
  "status": "FAILURE",
  "result": null,
  "error": "Connection timeout"
}
```

#### 3. 重新分析 PR

```bash
POST /api/v1/analysis/projects/{project_id}/pull-requests/{pr_id}/reanalyze

Response:
{
  "message": "PR re-analysis queued",
  "task_id": "new_task_id",
  "status": "PENDING",
  "pr_id": "pr-1"
}
```

### Celery 任务定义

#### analyze_pull_request (高优先级)

```python
@celery_app.task(
    bind=True,
    name='app.tasks.analyze_pull_request',
    max_retries=3,
    queue='high_priority'
)
def analyze_pull_request(self, pr_id: str, project_id: str):
    """
    执行步骤:
    1. 从 GitHub 获取 PR 文件和差异
    2. 使用 AST 解析器解析变更文件
    3. 在 Neo4j 中构建依赖图
    4. 运行 AI 推理引擎进行分析
    5. 存储结果到 PostgreSQL
    6. 更新 GitHub PR 检查状态
    """
```

#### detect_architectural_drift (低优先级)

```python
@celery_app.task(
    name='app.tasks.detect_architectural_drift',
    max_retries=2,
    queue='low_priority'
)
def detect_architectural_drift(project_id: str, baseline_version: str = "latest"):
    """
    执行步骤:
    1. 检测循环依赖
    2. 检测层违规
    3. 计算耦合指标
    4. 生成漂移报告
    5. 存储到数据库
    """
```

---

## 架构漂移检测

### Cypher 查询集合

#### 1. 检测循环依赖

**查询** (见 cypher_queries.py):

```cypher
CYCLIC_DEPENDENCY_QUERY

找到的模式:
Module A -> Module B -> ... -> Module A

严重程度:
- 2-hop 循环 (A->B->A): CRITICAL ⚠️
- 3+ hop 循环: HIGH ⚠️
```

**用法**:

```python
from app.tasks.architectural_drift import detect_cyclic_dependencies

# 异步任务
task_result = detect_cyclic_dependencies.apply_async(
    args=['project-id'],
    queue='low_priority'
)

# 轮询结果
from celery.result import AsyncResult
result = AsyncResult(task_result.id)
while result.status != 'SUCCESS':
    print(f"Status: {result.status}")
    # 等待...

print(result.result)
```

**示例结果**:

```python
{
    'cycles_found': 2,
    'cycles': [
        {
            'module': 'UserService',
            'cycle_path': ['UserService', 'AuthService', 'UserService'],
            'cycle_length': 2,
            'severity': 'CRITICAL',
            'description': '循环依赖: UserService -> AuthService -> UserService'
        },
        {
            'module': 'OrderService',
            'cycle_path': ['OrderService', 'PaymentService', 'InventoryService', 'OrderService'],
            'cycle_length': 3,
            'severity': 'HIGH',
            'description': '循环依赖: OrderService -> PaymentService -> InventoryService -> OrderService'
        }
    ]
}
```

#### 2. 检测层违规

**查询** (见 cypher_queries.py):

```cypher
LAYER_VIOLATION_QUERY

检测架构层违规:
Controller → Service → Repository (正确的流程)
Controller → Repository (违规! 跳过了 Service 层)

标准层:
- Controller 层: 处理 HTTP 请求
- Service 层: 业务逻辑
- Repository 层: 数据访问
- Database: 数据库
```

**用法**:

```python
from app.tasks.architectural_drift import detect_layer_violations

# 异步任务
task_result = detect_layer_violations.apply_async(
    args=['project-id'],
    queue='low_priority'
)

result = AsyncResult(task_result.id)
print(result.result)
```

**示例结果**:

```python
{
    'violations_found': 3,
    'violations': [
        {
            'source_module': 'UserController',
            'source_type': 'Controller',
            'target_module': 'UserRepository',
            'target_type': 'Repository',
            'violation_path': ['UserController', 'SomeHelper', 'UserRepository'],
            'violation_type': 'layer_skip',
            'severity': 'HIGH',
            'description': 'Layer violation: UserController (Controller) bypasses Service layer and directly depends on UserRepository (Repository)',
            'recommendation': 'Add intermediate Service layer to maintain proper architecture layers'
        }
    ]
}
```

#### 3. 耦合指标

**查询**:

```cypher
EFFERENT_COUPLING_QUERY: 出向耦合度 (模块依赖多少个其他模块)
AFFERENT_COUPLING_QUERY: 入向耦合度 (多少个其他模块依赖该模块)
INSTABILITY_INDEX_QUERY: 不稳定性指数 (EC / (EC + AC))

不稳定性指数解释:
- 0.0-0.3: STABLE (稳定核心 - 许多模块依赖它)
- 0.3-0.7: BALANCED (平衡模块)
- 0.7-1.0: UNSTABLE (不稳定叶子 - 依赖很多其他模块)
```

### 定时调度配置

在 `celery_config.py` 中:

```python
beat_schedule={
    # 每周一上午 2 点 (UTC)
    'detect-drift-weekly': {
        'task': 'app.tasks.architectural_drift.detect_architectural_drift',
        'schedule': crontab(day_of_week='monday', hour=2, minute=0),
    },

    # 每天上午 3 点 (UTC)
    'detect-cycles-daily': {
        'task': 'app.tasks.architectural_drift.detect_cyclic_dependencies',
        'schedule': crontab(hour=3, minute=0),
    },

    # 周一和周四上午 4 点 (UTC)
    'detect-violations-twice-weekly': {
        'task': 'app.tasks.architectural_drift.detect_layer_violations',
        'schedule': crontab(day_of_week='monday,thursday', hour=4, minute=0),
    }
}
```

### 使用 Cron 命令行

如果不使用 Celery Beat，可以用系统 cron:

```bash
# 编辑 crontab
crontab -e

# 添加以下行:
# 每周一上午 2 点运行漂移检测
0 2 * * 1 cd /app && celery -A app.celery_config celery_app call app.tasks.detect_architectural_drift --args='["project-id"]' --queue=low_priority

# 每天上午 3 点运行循环检测
0 3 * * * cd /app && celery -A app.celery_config celery_app call app.tasks.detect_cyclic_dependencies --args='["project-id"]' --queue=low_priority

# 每周一和周四上午 4 点运行层违规检测
0 4 * * 1,4 cd /app && celery -A app.celery_config celery_app call app.tasks.detect_layer_violations --args='["project-id"]' --queue=low_priority
```

---

## Docker Compose 配置

### 已更新的服务

```yaml
services:
  # 现有服务 (backend, postgres, neo4j, redis)

  # NEW: High Priority Celery Worker
  celery-worker-high:
    - 处理 PR 分析任务
    - 并发数: 2 (可根据需要调整)
    - 队列: high_priority
    - 命令: celery -A app.celery_config celery_app worker --queues=high_priority

  # NEW: Low Priority Celery Worker
  celery-worker-low:
    - 处理架构漂移检测
    - 并发数: 1
    - 队列: low_priority,default
    - 命令: celery -A app.celery_config celery_app worker --queues=low_priority,default

  # NEW: Celery Beat Scheduler
  celery-beat:
    - 触发定时任务
    - 调度周期任务
    - 命令: celery -A app.celery_config celery_app beat --scheduler django_celery_beat.schedulers:DatabaseScheduler

volumes:
  celery_beat_schedule: # Celery Beat 的持久化存储
```

---

## 运行与部署

### 本地开发

#### 启动所有服务

```bash
docker-compose up -d

# 验证服务
docker-compose ps

# 查看日志
docker-compose logs -f backend
docker-compose logs -f celery-worker-high
docker-compose logs -f celery-worker-low
docker-compose logs -f celery-beat
```

#### 检查服务健康

```bash
# 后端健康检查
curl http://localhost:8000/health

# Redis
redis-cli -h localhost -p 6379 -a <REDIS_PASSWORD> ping
# 预期: PONG

# 检查 Celery 连接
celery -A app.celery_config celery_app inspect active
```

### 生产部署

#### 使用 Kubernetes

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: celery-worker-high
spec:
  replicas: 3 # 3 个副本处理 PR 分析
  template:
    spec:
      containers:
        - name: celery-worker
          image: your-registry/backend:latest
          command:
            [
              "celery",
              "-A",
              "app.celery_config",
              "celery_app",
              "worker",
              "--queues=high_priority",
              "--concurrency=2",
            ]
          resources:
            requests:
              memory: "512Mi"
              cpu: "500m"
            limits:
              memory: "1Gi"
              cpu: "1000m"

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: celery-beat
spec:
  replicas: 1 # 只需要一个 Beat 实例
  template:
    spec:
      containers:
        - name: celery-beat
          image: your-registry/backend:latest
          command: ["celery", "-A", "app.celery_config", "celery_app", "beat"]
          resources:
            requests:
              memory: "256Mi"
              cpu: "100m"
```

#### 使用 Docker Swarm

```bash
docker stack deploy -c docker-compose.yml ai-review
docker service ls
docker service logs ai-review_celery-worker-high
```

---

## 监控与调试

### Celery 监控

#### 使用 Flower (Celery 监控工具)

```bash
# 安装
pip install flower

# 启动 Flower
celery -A app.celery_config celery_app flower

# 访问
http://localhost:5555

# 可以看到:
- 所有正在运行的任务
- 任务历史
- Worker 状态
- 实时统计
```

#### 命令行检查

```bash
# 查看活动任务
celery -A app.celery_config celery_app inspect active

# 查看 Worker 统计
celery -A app.celery_config celery_app inspect stats

# 查看任务结果
celery -A app.celery_config celery_app inspect result <task_id>

# 查看已注册的任务
celery -A app.celery_config celery_app inspect registered

# 查看队列
celery -A app.celery_config celery_app inspect active_queues
```

### 日志分析

```bash
# 查看特定 Worker 的日志
docker-compose logs celery-worker-high -f --tail=100

# 查看特定任务的日志
docker-compose exec celery-worker-high celery -A app.celery_config celery_app events --dump

# 筛选错误日志
docker-compose logs celery-worker-high | grep ERROR
```

### 性能监测

```python
# 在应用中添加度量指标
from app.core.metrics import metrics

@celery_app.task(bind=True)
def analyze_pull_request(self, pr_id: str, project_id: str):
    start_time = time.time()

    try:
        # ... 任务逻辑 ...

        elapsed = time.time() - start_time
        metrics.histogram(
            'task.analyze_pr.duration_seconds',
            elapsed,
            tags=['pr_id', pr_id, 'status', 'success']
        )
    except Exception as e:
        elapsed = time.time() - start_time
        metrics.histogram(
            'task.analyze_pr.duration_seconds',
            elapsed,
            tags=['pr_id', pr_id, 'status', 'failure']
        )
        raise
```

---

## 故障排除

### 常见问题

#### 问题 1: 任务卡在 PENDING

**症状**: 任务长时间停留在 PENDING 状态

**可能原因**:

1. Worker 未启动或崩溃
2. Redis 连接问题
3. 任务没有正确路由到队列

**解决方案**:

```bash
# 检查 Worker 状态
celery -A app.celery_config celery_app inspect active

# 重启 Worker
docker-compose restart celery-worker-high

# 检查 Redis 连接
redis-cli -h localhost -p 6379 -a <PASSWORD> ping

# 查看任务在哪个队列
docker-compose exec redis redis-cli -a <PASSWORD> KEYS "celery*"
```

#### 问题 2: Worker 频繁重启

**症状**: Worker 容器一直重启

**可能原因**:

1. 内存不足
2. 任务导致分段错误
3. 依赖问题

**解决方案**:

```bash
# 查看日志
docker-compose logs celery-worker-high --tail=50

# 增加内存限制 (docker-compose.yml)
celery-worker-high:
  deploy:
    resources:
      limits:
        memory: 2G

# 重启
docker-compose restart celery-worker-high
```

#### 问题 3: 任务超时

**症状**: 任务在完成前超时

**可能原因**:

1. 任务执行时间过长
2. Neo4j 查询效率低
3. 网络延迟

**解决方案**:

```python
# 在 celery_config.py 中增加超时
celery_app.conf.update(
    task_soft_time_limit=600,  # 10 分钟软限制
    task_time_limit=900,       # 15 分钟硬限制
)

# 或针对特定任务
@celery_app.task(
    time_limit=600,
    soft_time_limit=500
)
def analyze_pull_request(self, pr_id: str, project_id: str):
    pass
```

#### 问题 4: Redis 连接拒绝

**症状**: `ConnectionRefusedError: Error connecting to Redis`

**可能原因**:

1. Redis 容器未运行
2. 密码不正确
3. 端口被占用

**解决方案**:

```bash
# 检查 Redis 状态
docker-compose ps redis

# 检查端口
lsof -i :6379

# 重启 Redis
docker-compose restart redis

# 验证连接
docker-compose exec redis redis-cli -a <PASSWORD> ping
```

### 调试模式

```python
# 启用调试日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 启用 Celery 调试
celery -A app.celery_config celery_app worker --loglevel=DEBUG

# 在代码中添加调试
@celery_app.task(bind=True)
def analyze_pull_request(self, pr_id: str, project_id: str):
    print(f"DEBUG: Starting task {self.request.id}")
    print(f"DEBUG: PR ID: {pr_id}, Project ID: {project_id}")
    # ...
```

---

## 性能优化建议

### 1. 调整 Worker 并发数

```bash
# PR 分析 Worker: 处理 I/O 密集任务，可以增加并发
celery worker --queues=high_priority --concurrency=4 --pool=prefork

# 架构检测 Worker: 处理计算密集任务，保持较低并发
celery worker --queues=low_priority --concurrency=1
```

### 2. 优化 Cypher 查询

```cypher
// 添加索引加快查询
CREATE INDEX project_id ON :Project(projectId);
CREATE INDEX module_id ON :Module(moduleId);
CREATE INDEX depends_on ON :DEPENDS_ON(source, target);

// 使用 EXPLAIN 分析查询计划
EXPLAIN MATCH (m:Module)-[:DEPENDS_ON*]->(m) RETURN m
```

### 3. 实现结果缓存

```python
# 在 analyze_pull_request 中
@celery_app.task
def analyze_pull_request(self, pr_id: str, project_id: str):
    # 检查缓存
    cache_key = f"pr_analysis:{pr_id}"
    cached_result = await cache.get(cache_key)
    if cached_result:
        return cached_result

    # ... 执行分析 ...

    # 缓存结果 1 小时
    await cache.set(cache_key, result, expires=3600)
    return result
```

### 4. 批量处理任务

```python
# 不要这样做 - 太多小任务
for pr_id in pr_list:
    analyze_pull_request.apply_async([pr_id, project_id])

# 这样做 - 批处理
from celery import group
job = group(
    analyze_pull_request.s(pr_id, project_id)
    for pr_id in pr_list
)
result = job.apply_async()
```

---

## 总结

本指南涵盖了:
✅ 异步任务队列设置与使用
✅ 架构漂移检测查询
✅ Docker Compose 配置
✅ 运行与部署指南
✅ 监控与调试工具
✅ 故障排除与性能优化

完整的实现包括:

- 6 个 Celery 任务文件
- 8+ Cypher 查询模板
- 完整的测试套件
- Docker Compose 配置
- API 端点
- 定时调度配置

所有代码已准备好生产部署! 🚀
