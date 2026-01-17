# 密钥迁移和安全指南

## 总览

本指南说明如何将硬编码的密钥迁移到环境变量，并使用 TruffleHog 验证。

## Phase 1: 识别硬编码密钥

已识别的问题：

- ✗ `load_testing/locustfile.py`: 硬编码密码

## Phase 2: 创建 .env 文件

### 步骤 1: 从 .env.example 创建 .env

```bash
# 复制示例文件
cp .env.example .env

# 编辑 .env 并更新实际凭证
# 重要：永远不要提交 .env 到 git
echo ".env" >> .gitignore
```

### 步骤 2: 配置环境变量

#### Python (FastAPI)

使用 `pydantic-settings` 自动加载 .env：

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    JWT_SECRET: str
    POSTGRES_PASSWORD: str
    REDIS_PASSWORD: str
    GITHUB_TOKEN: str = ""
    OPENAI_API_KEY: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
```

#### JavaScript/Next.js

使用 `process.env` 访问环境变量：

```typescript
// 在编译时替换（公共环境变量）
const API_URL = process.env.NEXT_PUBLIC_API_URL;

// 运行时变量（只在服务器端）
const SECRET = process.env.SECRET_KEY;
```

## Phase 3: 更新代码

### 已修复的文件：

- ✅ `load_testing/locustfile.py` - 现在从 .env 加载测试凭证
- ✅ `backend/requirements.txt` - 添加了安全扫描工具
- ✅ `backend/app/services/parsers/go_parser.py` - 修复了 subprocess 调用
- ✅ `backend/app/utils/serializers.py` - 添加了 pickle 安全警告

## Phase 4: 使用 git-filter-repo 清理历史记录

### 步骤 1: 安装工具

```bash
pip install git-filter-repo
```

### 步骤 2: 运行清理脚本

```bash
bash scripts/remove_git_secrets.sh
```

### 步骤 3: 强制推送

```bash
# ⚠️ 警告：这将重写历史。仅在私有存储库中执行！
git push origin main --force-with-lease
```

## Phase 5: 验证 TruffleHog 扫描

### 运行 TruffleHog

```bash
# 扫描当前目录
trufflehog filesystem . --json

# 扫描特定目录
trufflehog filesystem ./backend --json

# 扫描 git 历史
trufflehog git file:// --json
```

### 预期结果

```json
{
  "verified": false,
  "type": "Example",
  "redacted": true
}
```

## Phase 6: CI/CD 集成

### GitHub Actions 配置

GitHub Actions 工作流文件已包含 TruffleHog 扫描：

- `.github/workflows/security-scanning.yml` - 包含 TruffleHog 步骤

## 环境变量最佳实践

### ✅ 应该做

```python
# 从环境变量读取
api_key = os.getenv("API_KEY")
if not api_key:
    raise ValueError("API_KEY environment variable not set")

# 使用默认值
debug_mode = os.getenv("DEBUG", "false").lower() == "true"

# 验证凭证
if len(api_key) < 20:
    raise ValueError("Invalid API_KEY length")
```

### ❌ 不应该做

```python
# 硬编码
API_KEY = "sk_live_abc123xyz"  # ❌ 不要这样做！

# 在日志中打印
print(f"API Key: {api_key}")  # ❌ 危险！

# 提交到 git
git add .env  # ❌ .env 应该在 .gitignore 中

# 使用弱密钥
SECRET = "password123"  # ❌ 过于简单
```

## 加载环境变量

### Python

```python
from dotenv import load_dotenv
import os

# 从当前目录或上级目录加载 .env
load_dotenv()

# 或指定路径
load_dotenv(dotenv_path="/path/to/.env")

# 现在可以访问环境变量
database_url = os.getenv("DATABASE_URL")
```

### Node.js/Next.js

Next.js 自动加载 `.env.local` 和 `.env`：

```javascript
// pages/api/example.js
export default function handler(req, res) {
  // 公开环境变量（客户端可见）
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;

  // 私有环境变量（仅服务器端）
  const dbPassword = process.env.DB_PASSWORD;

  return res.status(200).json({ apiUrl });
}
```

## Docker 环境变量

### 传递环境变量

```bash
# 运行时
docker run -e DATABASE_URL=postgresql://... myapp

# 从文件
docker run --env-file .env myapp

# Docker Compose
docker-compose up
# 自动从 .env 文件读取
```

### Docker Compose 示例

```yaml
version: "3.8"

services:
  backend:
    build: ./backend
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - JWT_SECRET=${JWT_SECRET}
    env_file:
      - .env
```

## 多环境配置

### 结构

```
.env                 # 本地开发（不提交）
.env.example         # 示例模板（提交）
.env.production      # 生产配置（不提交，手动设置）
.env.staging         # 暂存配置（不提交）
```

### 加载不同环境

```python
import os
from pathlib import Path

env_file = f".env.{os.getenv('APP_ENV', 'development')}"
load_dotenv(dotenv_path=env_file)
```

## 审计和监控

### 定期检查

```bash
# 扫描当前代码中的秘密
trufflehog filesystem . --only-verified

# 检查 git 历史
trufflehog git file:// --only-verified

# 使用 git grep 查找模式
git grep -i "password\|api_key\|secret" -- ':!*.md'
```

### GitHub Actions 自动扫描

GitHub Actions 工作流 `security-scanning.yml` 包含：

- ✅ TruffleHog 秘密扫描
- ✅ Bandit Python 安全检查
- ✅ npm 审计
- ✅ Trivy 容器扫描

## 故障排除

### 问题：TruffleHog 仍然检测到秘密

```bash
# 确认已清理历史
git log --all --full-history -- file.txt

# 重新运行清理
git filter-repo --replace-text=patterns.txt --force

# 再次验证
git log --all -S "secret" --oneline
```

### 问题：环境变量未加载

```python
import os
from dotenv import load_dotenv

# 调试
print(f"Current directory: {os.getcwd()}")
print(f"File exists: {os.path.exists('.env')}")

load_dotenv(verbose=True)  # 显示加载详情

# 验证
print(f"API_KEY: {os.getenv('API_KEY')}")
```

## 参考资源

- [TruffleHog 文档](https://github.com/trufflesecurity/trufflehog)
- [git-filter-repo 指南](https://htmlpreview.github.io/?https://github.com/newren/git-filter-repo/blob/docs/html/git-filter-repo.html)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [Next.js 环境变量](https://nextjs.org/docs/basic-features/environment-variables)
- [OWASP 密钥管理](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
