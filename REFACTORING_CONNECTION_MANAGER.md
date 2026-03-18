# Connection Manager 重构计划

## 当前问题

`connection_manager.py` 有 **1427 行**，存在以下问题：

### 1. 代码重复
`PoolMonitor` 类和 `ConnectionManager` 类中存在重复方法：
- `_pool_health_monitor` 
- `_pool_cleanup_monitor`
- `_check_and_recover_pools`
- `_recover_postgresql_pool`
- `_recover_neo4j_driver`
- `_validate_pool_health`

### 2. 职责不清晰
`ConnectionManager` 同时负责：
- 连接池管理
- 健康监控
- 统计收集
- 报告生成
- 全局单例

## 重构方案

### 阶段 1：提取监控逻辑到 PoolMonitor（高风险）
将 `ConnectionManager` 中的监控方法委托给 `PoolMonitor`，删除重复代码。

### 阶段 2：拆分统计和报告模块（中风险）
提取 `connection_reporting.py`：
- `get_pool_statistics()`
- `get_health_status()`
- `get_detailed_pool_report()`
- `_get_enhanced_pool_metrics()`
- `_get_system_health_metrics()`
- `_calculate_health_score()`

### 阶段 3：提取验证逻辑（中风险）
提取 `connection_verification.py`：
- `verify_postgres()`
- `verify_neo4j()`
- `verify_redis()`
- `verify_all()`

### 阶段 4：清理主类（低风险）
`connection_manager.py` 最终应该只保留：
- `__init__()` - 初始化
- `initialize_pools()` - 入口点
- `get_postgresql_connection()` - 核心 API
- `get_neo4j_session()` - 核心 API
- `close_all_connections()` - 清理

## 预估工作量

| 阶段 | 风险 | 工作量 | 测试覆盖 |
|------|------|--------|----------|
| 1 | 高 | 2-3 小时 | 需要更新测试 |
| 2 | 中 | 1-2 小时 | 相对独立 |
| 3 | 中 | 1-2 小时 | 需要模拟 |
| 4 | 低 | 30 分钟 | 回归测试 |

## 当前测试覆盖

- `test_connection_manager.py` - 522 行
- `test_connection_manager_pool_properties.py` - 526 行
- `test_connection_manager_pool_health_properties.py` - 609 行

总计：**1657 行测试代码**，确保重构有充分覆盖。

## 建议执行时间

建议在有完整 CI 环境时执行，并确保：
1. 所有测试通过
2. 有完整的回归测试
3. 准备回滚方案
