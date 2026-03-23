"""
AI Code Review Platform — 一键启动脚本
支持两种部署模式：
  1. Docker 模式 (推荐): 自动启动所有容器
  2. 本地模式: 在本机运行后端和前端

用法:
    python start_all.py                  # 自动检测 (优先 Docker)
    python start_all.py --mode docker    # 强制 Docker
    python start_all.py --mode local     # 强制本地
    python start_all.py --check          # 仅检查环境
    python start_all.py --stop           # 停止所有 Docker 服务
    python start_all.py --logs           # 查看 Docker 日志
    python start_all.py --status         # 查看服务状态
    python start_all.py --clean          # 清理并重新开始
    python start_all.py --help           # 查看帮助

兼容性: Python 3.7+
"""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import Dict, List, Optional

# ──────────────────────── 路径 ────────────────────────
ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"
ENV_FILE = ROOT / ".env"

# ──────────────────────── 端口 ────────────────────────
BACKEND_PORT = int(os.environ.get("BACKEND_PORT", "8000"))
FRONTEND_PORT = int(os.environ.get("FRONTEND_PORT", "3000"))

# ──────────────────────── 颜色 ────────────────────────
class C:
    """ANSI color codes (auto-disabled on non-TTY)."""
    _enabled = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
    GREEN  = "\033[92m" if _enabled else ""
    YELLOW = "\033[93m" if _enabled else ""
    RED    = "\033[91m" if _enabled else ""
    CYAN   = "\033[96m" if _enabled else ""
    BOLD   = "\033[1m"  if _enabled else ""
    RESET  = "\033[0m"  if _enabled else ""

# ──────────────────────── .env 模板 ────────────────────
ENV_TEMPLATE = """\
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
JWT_SECRET=dev-secret-key-change-in-production-32chars
ENVIRONMENT=development

# === AI 审查 (DeepSeek) ===
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# === GitHub OAuth (项目导入功能需要) ===
NEXT_PUBLIC_GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
GITHUB_TOKEN=

# === 后端 URL (Docker 内部通信) ===
BACKEND_URL=http://backend:8000
"""


# ========================= 工具函数 =========================

def print_banner() -> None:
    print(f"""{C.CYAN}{C.BOLD}
╔═══════════════════════════════════════════════╗
║       🤖 AI Code Review Platform              ║
║       一键启动脚本 v2.1                       ║
╚═══════════════════════════════════════════════╝{C.RESET}
  项目目录: {ROOT}
""")


def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def cmd_exists(name: str) -> bool:
    return shutil.which(name) is not None


def load_env_file() -> Dict[str, str]:
    """Parse .env file into a dict (simple key=value parser)."""
    env_vars: Dict[str, str] = {}
    if not ENV_FILE.exists():
        return env_vars
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            env_vars[k.strip()] = v.strip()
    return env_vars


def ensure_env_file() -> None:
    """Create .env from template if it doesn't exist."""
    if ENV_FILE.exists():
        print(f"{C.GREEN}✅ .env 文件已存在{C.RESET}")
        return
    ENV_FILE.write_text(ENV_TEMPLATE, encoding="utf-8")
    print(f"{C.YELLOW}📝 已创建 .env 文件，请根据需要修改配置（特别是 DEEPSEEK_API_KEY）{C.RESET}")


def stream_output(proc: subprocess.Popen, name: str) -> None:
    """Stream child stdout with a prefix."""
    assert proc.stdout is not None
    for line in proc.stdout:
        sys.stdout.write(f"[{name}] {line}")
    proc.stdout.close()


def stop_process(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    try:
        if os.name == "nt":
            proc.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            proc.terminate()
        proc.wait(timeout=10)
    except Exception:
        proc.kill()


def kill_process_on_port(port: int) -> bool:
    """Kill the process occupying a port (Windows & Linux)."""
    if os.name == "nt":
        try:
            r = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, timeout=10)
            pids = set()
            for line in r.stdout.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.split()
                    if len(parts) >= 5:
                        try:
                            pid = int(parts[-1])
                            if pid > 0:
                                pids.add(pid)
                        except ValueError:
                            pass
            for pid in pids:
                subprocess.run(["taskkill", "/F", "/PID", str(pid)],
                               capture_output=True, timeout=10)
            if pids:
                time.sleep(1)
            return bool(pids)
        except Exception:
            return False
    else:
        try:
            r = subprocess.run(["lsof", "-ti", f":{port}"],
                               capture_output=True, text=True, timeout=10)
            if r.returncode == 0 and r.stdout.strip():
                for pid in r.stdout.strip().split("\n"):
                    subprocess.run(["kill", "-9", pid], timeout=5)
                return True
        except Exception:
            pass
        return False


# ========================= 环境检查 =========================

def check_docker() -> bool:
    """Check Docker & Docker Compose availability."""
    if not cmd_exists("docker"):
        return False
    try:
        r = subprocess.run(["docker", "info"], capture_output=True, timeout=10)
        if r.returncode != 0:
            return False
        r2 = subprocess.run(["docker", "compose", "version"],
                            capture_output=True, timeout=10)
        return r2.returncode == 0
    except Exception:
        return False


def auto_start_docker_desktop() -> bool:
    """Try to auto-start Docker Desktop (Windows/Mac)."""
    if cmd_exists("docker"):
        # Check if Docker daemon is already running
        try:
            r = subprocess.run(["docker", "info"], capture_output=True, timeout=10)
            if r.returncode == 0:
                return True
        except Exception:
            pass
    else:
        print(f"{C.RED}❌ Docker 未安装，请先安装 Docker Desktop{C.RESET}")
        print(f"   下载: https://docs.docker.com/desktop/install/windows-install/")
        return False

    print(f"\n{C.YELLOW}🐳 Docker Desktop 未运行，正在尝试自动启动...{C.RESET}")

    # Try to start Docker Desktop
    started = False
    if os.name == "nt":  # Windows
        docker_paths = [
            os.path.expandvars(r"%ProgramFiles%\Docker\Docker\Docker Desktop.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Docker\Docker\Docker Desktop.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Docker\Docker Desktop.exe"),
        ]
        for path in docker_paths:
            if os.path.exists(path):
                try:
                    subprocess.Popen([path], creationflags=subprocess.DETACHED_PROCESS)
                    started = True
                    break
                except Exception:
                    pass
        if not started:
            # Try via start command
            try:
                subprocess.Popen("start /B \"Docker Desktop\" \"Docker Desktop\"",
                                shell=True, creationflags=subprocess.DETACHED_PROCESS)
                started = True
            except Exception:
                pass
    else:  # macOS / Linux
        try:
            subprocess.Popen(["open", "-a", "Docker"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            started = True
        except Exception:
            pass

    if not started:
        print(f"{C.RED}❌ 无法自动启动 Docker Desktop，请手动启动后重试{C.RESET}")
        return False

    # Wait for Docker daemon to be ready (up to 60 seconds)
    print(f"  等待 Docker 引擎就绪 (最多 60 秒)...", end="", flush=True)
    for i in range(60):
        try:
            r = subprocess.run(["docker", "info"], capture_output=True, timeout=5)
            if r.returncode == 0:
                print(f"\n  {C.GREEN}✅{C.RESET} Docker Desktop 已就绪")
                return True
        except Exception:
            pass
        print(".", end="", flush=True)
        time.sleep(1)

    print(f"\n{C.RED}❌ Docker Desktop 启动超时，请手动启动后重试{C.RESET}")
    return False


def init_database_for_docker() -> None:
    """Initialize database after Docker containers are healthy.
    
    Ensures uuid-ossp extension and proper alembic_version table exist.
    The actual tables are created by the backend app on startup via
    Base.metadata.create_all in init_postgres().
    """
    env_vars = load_env_file()
    db_name = env_vars.get("POSTGRES_DB", "ai_code_review")
    db_user = env_vars.get("POSTGRES_USER", "postgres")

    print(f"\n{C.CYAN}🗃️  初始化数据库...{C.RESET}")

    # 1. Ensure uuid-ossp extension
    try:
        result = subprocess.run(
            ["docker", "exec", "ai_review_postgres", "psql",
             "-U", db_user, "-d", db_name, "-c",
             'CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            print(f"  {C.GREEN}✅{C.RESET} uuid-ossp 扩展已启用")
        else:
            print(f"  {C.YELLOW}⚠️{C.RESET}  uuid-ossp 扩展设置跳过: {result.stderr.strip()[:100]}")
    except Exception as e:
        print(f"  {C.YELLOW}⚠️{C.RESET}  uuid-ossp 扩展设置跳过: {e}")

    # 2. Ensure alembic_version table with VARCHAR(255)
    try:
        result = subprocess.run(
            ["docker", "exec", "ai_review_postgres", "psql",
             "-U", db_user, "-d", db_name, "-c",
             "CREATE TABLE IF NOT EXISTS alembic_version "
             "(version_num VARCHAR(255) NOT NULL, "
             "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num));"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            print(f"  {C.GREEN}✅{C.RESET} 数据库版本表已就绪")
        else:
            print(f"  {C.YELLOW}⚠️{C.RESET}  版本表设置跳过: {result.stderr.strip()[:100]}")
    except Exception as e:
        print(f"  {C.YELLOW}⚠️{C.RESET}  版本表设置跳过: {e}")


def check_python() -> Dict[str, any]:
    """Check Python environment."""
    version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    conda_env = os.environ.get("CONDA_DEFAULT_ENV", None)
    venv = os.environ.get("VIRTUAL_ENV", None)

    info = {"version": version, "ok": sys.version_info >= (3, 7)}
    if conda_env:
        info["env_type"] = "conda"
        info["env_name"] = conda_env
    elif venv:
        info["env_type"] = "venv"
        info["env_name"] = Path(venv).name
    else:
        info["env_type"] = "system"
        info["env_name"] = "system"
    return info


def check_node() -> Optional[str]:
    """Return Node.js version string if available."""
    try:
        r = subprocess.run(["node", "--version"], capture_output=True,
                           text=True, timeout=5)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def check_service(host: str, port: int, name: str) -> bool:
    """Check if a TCP service is reachable."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            s.connect((host, port))
            return True
    except Exception:
        return False


def run_env_check(verbose: bool = True) -> Dict[str, bool]:
    """Run all environment checks, return results dict."""
    results: Dict[str, bool] = {}
    env_vars = load_env_file()

    # Python
    py = check_python()
    results["python"] = py["ok"]
    if verbose:
        env_label = f" ({py['env_type']}: {py['env_name']})" if py["env_type"] != "system" else ""
        status = f"{C.GREEN}✅{C.RESET}" if py["ok"] else f"{C.RED}❌{C.RESET}"
        print(f"  {status} Python {py['version']}{env_label}")

    # Node.js
    node_ver = check_node()
    results["node"] = node_ver is not None
    if verbose:
        if node_ver:
            print(f"  {C.GREEN}✅{C.RESET} Node.js {node_ver}")
        else:
            print(f"  {C.RED}❌{C.RESET} Node.js 未安装")

    # Docker
    docker_ok = check_docker()
    results["docker"] = docker_ok
    if verbose:
        if docker_ok:
            print(f"  {C.GREEN}✅{C.RESET} Docker & Docker Compose 可用")
        else:
            print(f"  {C.YELLOW}⚠️{C.RESET}  Docker 不可用 (仅支持本地模式)")

    # PostgreSQL
    pg_host = env_vars.get("POSTGRES_HOST", "localhost")
    pg_port = int(env_vars.get("POSTGRES_PORT", "5432"))
    pg_ok = check_service(pg_host, pg_port, "PostgreSQL")
    results["postgres"] = pg_ok
    if verbose:
        if pg_ok:
            print(f"  {C.GREEN}✅{C.RESET} PostgreSQL ({pg_host}:{pg_port})")
        else:
            print(f"  {C.YELLOW}⚠️{C.RESET}  PostgreSQL 不可达 ({pg_host}:{pg_port})")

    # Redis
    redis_host = env_vars.get("REDIS_HOST", "localhost")
    redis_port = int(env_vars.get("REDIS_PORT", "6379"))
    redis_ok = check_service(redis_host, redis_port, "Redis")
    results["redis"] = redis_ok
    if verbose:
        if redis_ok:
            print(f"  {C.GREEN}✅{C.RESET} Redis ({redis_host}:{redis_port})")
        else:
            print(f"  {C.YELLOW}⚠️{C.RESET}  Redis 不可达 — 缓存功能将降级")

    # Neo4j
    neo4j_uri = env_vars.get("NEO4J_URI", "bolt://localhost:7687")
    neo4j_host = neo4j_uri.split("://")[-1].split(":")[0] if "://" in neo4j_uri else "localhost"
    neo4j_port = int(neo4j_uri.split(":")[-1]) if neo4j_uri.count(":") >= 2 else 7687
    neo4j_ok = check_service(neo4j_host, neo4j_port, "Neo4j")
    results["neo4j"] = neo4j_ok
    if verbose:
        if neo4j_ok:
            print(f"  {C.GREEN}✅{C.RESET} Neo4j ({neo4j_host}:{neo4j_port})")
        else:
            print(f"  {C.YELLOW}⚠️{C.RESET}  Neo4j 不可达 — 架构图分析将降级")

    # DeepSeek API Key
    api_key = env_vars.get("DEEPSEEK_API_KEY", "")
    results["deepseek"] = bool(api_key)
    if verbose:
        if api_key:
            print(f"  {C.GREEN}✅{C.RESET} DeepSeek API Key 已配置")
        else:
            print(f"  {C.YELLOW}⚠️{C.RESET}  DeepSeek API Key 未配置 — AI 审查功能不可用")

    return results


# ========================= Docker 模式 =========================

def cleanup_stale_containers() -> None:
    """Remove stale/conflicting containers before starting."""
    container_names = [
        "ai_review_frontend", "ai_review_backend",
        "ai_review_postgres", "ai_review_redis", "ai_review_neo4j"
    ]
    for name in container_names:
        try:
            r = subprocess.run(
                ["docker", "inspect", name],
                capture_output=True, timeout=5
            )
            if r.returncode == 0:
                subprocess.run(
                    ["docker", "rm", "-f", name],
                    capture_output=True, timeout=10
                )
        except Exception:
            pass


def show_container_status() -> None:
    """Show status of all project containers."""
    print(f"\n{C.CYAN}📋 容器状态:{C.RESET}\n")
    try:
        result = subprocess.run(
            ["docker", "compose", "ps", "--format",
             "table {{.Name}}\t{{.Status}}\t{{.Ports}}"],
            cwd=str(ROOT), capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            print(result.stdout)
        else:
            print(f"  {C.YELLOW}⚠️{C.RESET}  没有运行中的容器")
    except Exception:
        print(f"  {C.RED}❌{C.RESET} 无法获取容器状态")

    services = [
        ("PostgreSQL", "localhost", 5432),
        ("Redis",      "localhost", 6379),
        ("Neo4j",      "localhost", 7687),
        ("Backend",    "localhost", BACKEND_PORT),
        ("Frontend",   "localhost", FRONTEND_PORT),
    ]
    print(f"\n{C.CYAN}🔌 端口连通性:{C.RESET}\n")
    for name, host, port in services:
        ok = check_service(host, port, name)
        status = f"{C.GREEN}✅ 可达{C.RESET}" if ok else f"{C.RED}❌ 不可达{C.RESET}"
        print(f"  {status}  {name} (:{port})")
    print()


def stop_docker() -> None:
    """Stop all Docker Compose services."""
    print(f"\n{C.CYAN}⏹️  停止所有 Docker 服务...{C.RESET}\n")
    result = subprocess.run(
        ["docker", "compose", "down"],
        cwd=str(ROOT)
    )
    if result.returncode == 0:
        print(f"\n{C.GREEN}✅ 所有服务已停止{C.RESET}")
    else:
        print(f"\n{C.RED}❌ 停止服务失败{C.RESET}")


def clean_docker() -> None:
    """Stop services and remove all Docker volumes (fresh start)."""
    print(f"\n{C.RED}{C.BOLD}⚠️  警告: 此操作将删除所有数据（数据库、缓存等）！{C.RESET}")
    answer = input(f"  确认清理? (y/N): ").strip().lower()
    if answer != 'y':
        print(f"  已取消")
        return
    print(f"\n{C.CYAN}🧹 清理所有 Docker 资源...{C.RESET}\n")
    subprocess.run(
        ["docker", "compose", "down", "-v", "--remove-orphans"],
        cwd=str(ROOT)
    )
    print(f"\n{C.GREEN}✅ 清理完成，可使用 python start_all.py 重新启动{C.RESET}")


def view_docker_logs(follow: bool = True) -> None:
    """View Docker Compose logs."""
    cmd = ["docker", "compose", "logs"]
    if follow:
        cmd.append("-f")
    cmd.extend(["--tail", "100"])
    try:
        subprocess.run(cmd, cwd=str(ROOT))
    except KeyboardInterrupt:
        pass


def start_docker(prod: bool = False, open_browser: bool = False) -> None:
    """Start all services via Docker Compose."""
    compose_file = "docker-compose.prod.yml" if prod else "docker-compose.yml"
    compose_path = ROOT / compose_file

    if not compose_path.exists():
        print(f"{C.RED}❌ {compose_file} 不存在{C.RESET}")
        sys.exit(1)

    # Clean up stale containers to avoid "name already in use" errors
    print(f"\n{C.CYAN}🧹 清理旧容器...{C.RESET}")
    cleanup_stale_containers()

    # Check & resolve port conflicts before starting
    for port, name in [(BACKEND_PORT, "后端"), (FRONTEND_PORT, "前端")]:
        if is_port_in_use(port):
            print(f"\n{C.YELLOW}⚠️  {name}端口 {port} 被占用，尝试释放...{C.RESET}")
            if kill_process_on_port(port) and not is_port_in_use(port):
                print(f"  {C.GREEN}✅{C.RESET} 端口 {port} 已释放")
            else:
                print(f"  {C.YELLOW}⚠️{C.RESET}  端口 {port} 仍被占用，Docker 可能会启动失败")
                print(f"     请手动关闭占用进程或修改端口配置")

    print(f"\n{C.CYAN}🐳 使用 Docker Compose 启动 ({compose_file})...{C.RESET}\n")

    cmd = ["docker", "compose", "-f", str(compose_path), "up", "-d", "--build"]
    result = subprocess.run(cmd, cwd=str(ROOT))
    if result.returncode != 0:
        print(f"\n{C.RED}❌ Docker Compose 启动失败{C.RESET}")
        print(f"   请检查 Docker 日志: docker compose logs")
        print(f"\n{C.YELLOW}💡 常见问题:{C.RESET}")
        print(f"   1. 端口被占用: 运行 python start_all.py --stop 后重试")
        print(f"   2. 镜像拉取失败: 检查网络连接")
        print(f"   3. 容器名冲突: 运行 python start_all.py --clean 后重试")
        sys.exit(1)

    print(f"\n{C.GREEN}✅ Docker 容器已启动！{C.RESET}")
    print(f"\n  等待服务就绪...\n")

    # Wait for services to be healthy
    services = [
        ("PostgreSQL", "localhost", 5432),
        ("Redis",      "localhost", 6379),
        ("Backend",    "localhost", BACKEND_PORT),
        ("Frontend",   "localhost", FRONTEND_PORT),
    ]

    all_ready = True
    for name, host, port in services:
        timeout = 120 if name == "Frontend" else 90
        for i in range(timeout):
            if check_service(host, port, name):
                print(f"  {C.GREEN}✅{C.RESET} {name} 就绪 (:{port})")
                break
            time.sleep(1)
        else:
            print(f"  {C.YELLOW}⏳{C.RESET} {name} 尚未就绪 (:{port})，请稍后检查")
            all_ready = False

    # Initialize database after PostgreSQL is ready
    if check_service("localhost", 5432, "PostgreSQL"):
        init_database_for_docker()

    # Auto-open browser
    if open_browser and all_ready:
        try:
            webbrowser.open(f"http://localhost:{FRONTEND_PORT}")
            print(f"  {C.GREEN}🌐{C.RESET} 已在浏览器中打开前端界面")
        except Exception:
            pass

    print(f"""
{C.GREEN}{C.BOLD}
╔═══════════════════════════════════════════════╗
║   ✅ 所有 Docker 服务已启动！                 ║
╚═══════════════════════════════════════════════╝{C.RESET}
{C.CYAN}  📊 前端界面:  http://localhost:{FRONTEND_PORT}
  📡 后端 API:   http://localhost:{BACKEND_PORT}
  📖 API 文档:   http://localhost:{BACKEND_PORT}/docs{C.RESET}

{C.GREEN}  🔑 默认登录账号:{C.RESET}
{C.CYAN}     邮箱: admin@example.com
     密码: Admin123!{C.RESET}

{C.YELLOW}  常用命令:
  停止服务:     python start_all.py --stop
  查看日志:     python start_all.py --logs
  服务状态:     python start_all.py --status
  清理重建:     python start_all.py --clean{C.RESET}
""")


# ========================= 本地模式 =========================

def install_backend_deps() -> bool:
    """Install Python backend dependencies."""
    req_file = BACKEND_DIR / "requirements.txt"
    if not req_file.exists():
        print(f"{C.RED}❌ requirements.txt 不存在{C.RESET}")
        return False

    print(f"\n{C.CYAN}📦 检查后端依赖...{C.RESET}")
    try:
        # Quick check if key packages are importable
        result = subprocess.run(
            [sys.executable, "-c", "import fastapi; import sqlalchemy"],
            capture_output=True, timeout=10
        )
        if result.returncode == 0:
            print(f"  {C.GREEN}✅{C.RESET} 后端核心依赖已安装")
            return True
    except Exception:
        pass

    print(f"  正在安装后端依赖...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(req_file), "-q"],
        cwd=str(BACKEND_DIR),
        timeout=600
    )
    if result.returncode == 0:
        print(f"  {C.GREEN}✅{C.RESET} 后端依赖安装完成")
        return True
    else:
        print(f"  {C.RED}❌{C.RESET} 后端依赖安装失败")
        return False


def install_frontend_deps() -> bool:
    """Install frontend dependencies via npm."""
    node_modules = FRONTEND_DIR / "node_modules"
    if node_modules.exists() and any(node_modules.iterdir()):
        print(f"  {C.GREEN}✅{C.RESET} 前端依赖已安装")
        return True

    print(f"\n{C.CYAN}📦 安装前端依赖 (npm install)...{C.RESET}")
    try:
        result = subprocess.run(
            ["npm", "install"],
            cwd=str(FRONTEND_DIR),
            shell=(os.name == "nt"),
            timeout=300
        )
        if result.returncode == 0:
            print(f"  {C.GREEN}✅{C.RESET} 前端依赖安装完成")
            return True
        else:
            print(f"  {C.RED}❌{C.RESET} npm install 失败")
            return False
    except subprocess.TimeoutExpired:
        print(f"  {C.RED}❌{C.RESET} npm install 超时 (5分钟)")
        return False
    except FileNotFoundError:
        print(f"  {C.RED}❌{C.RESET} npm 命令未找到")
        return False


def run_db_migration() -> bool:
    """Run Alembic database migration."""
    print(f"\n{C.CYAN}🗃️  执行数据库迁移...{C.RESET}")
    try:
        env = os.environ.copy()
        env["PYTHONPATH"] = f"{BACKEND_DIR}{os.pathsep}{ROOT}"
        # Load .env into migration environment
        for k, v in load_env_file().items():
            if k not in env:
                env[k] = v
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=str(BACKEND_DIR),
            env=env,
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            print(f"  {C.GREEN}✅{C.RESET} 数据库迁移完成")
            return True
        else:
            stderr = result.stderr[:300] if result.stderr else ""
            print(f"  {C.YELLOW}⚠️{C.RESET}  数据库迁移跳过 ({stderr.strip() or '可能已是最新'})")
            return True  # Non-fatal
    except Exception as e:
        print(f"  {C.YELLOW}⚠️{C.RESET}  数据库迁移跳过: {e}")
        return True  # Non-fatal


def start_local(args: argparse.Namespace) -> None:
    """Start backend and frontend locally."""
    # Check prerequisites
    py = check_python()
    if not py["ok"]:
        print(f"{C.RED}❌ Python 3.7+ 是必需的 (当前: {py['version']}){C.RESET}")
        sys.exit(1)

    if not check_node():
        print(f"{C.RED}❌ Node.js 未安装，前端无法启动{C.RESET}")
        print(f"   请安装 Node.js 18+: https://nodejs.org/")
        sys.exit(1)

    if not BACKEND_DIR.exists():
        print(f"{C.RED}❌ 后端目录不存在: {BACKEND_DIR}{C.RESET}")
        sys.exit(1)
    if not FRONTEND_DIR.exists():
        print(f"{C.RED}❌ 前端目录不存在: {FRONTEND_DIR}{C.RESET}")
        sys.exit(1)

    # Install dependencies (skip with --skip-deps)
    if not args.skip_deps:
        if not install_backend_deps():
            sys.exit(1)
        if not install_frontend_deps():
            sys.exit(1)
    else:
        print(f"\n{C.YELLOW}⏭️  跳过依赖安装 (--skip-deps){C.RESET}")

    # Check & auto-resolve port conflicts
    for port, name in [(BACKEND_PORT, "后端"), (FRONTEND_PORT, "前端")]:
        if is_port_in_use(port):
            print(f"\n{C.YELLOW}⚠️  {name}端口 {port} 被占用，尝试释放...{C.RESET}")
            if kill_process_on_port(port) and not is_port_in_use(port):
                print(f"  {C.GREEN}✅{C.RESET} 端口 {port} 已释放")
            else:
                print(f"  {C.RED}❌{C.RESET} 无法释放端口 {port}，请手动关闭占用进程")
                sys.exit(1)

    # Optional: database migration
    env_vars = load_env_file()
    pg_host = env_vars.get("POSTGRES_HOST", "localhost")
    pg_port = int(env_vars.get("POSTGRES_PORT", "5432"))
    if check_service(pg_host, pg_port, "PostgreSQL"):
        run_db_migration()
    else:
        print(f"\n{C.YELLOW}⚠️  PostgreSQL 不可达，跳过数据库迁移{C.RESET}")
        print(f"   后端启动后可能因数据库连接失败报错")

    # Start backend
    print(f"\n{C.CYAN}🚀 启动后端 (FastAPI)...{C.RESET}")
    backend_env = os.environ.copy()
    backend_env["PYTHONPATH"] = f"{BACKEND_DIR}{os.pathsep}{ROOT}"
    # Load .env into subprocess environment so config.py picks up credentials
    for k, v in env_vars.items():
        if k not in backend_env:
            backend_env[k] = v

    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app",
         "--host", "0.0.0.0", "--port", str(BACKEND_PORT), "--reload"],
        cwd=str(BACKEND_DIR),
        env=backend_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
        bufsize=1,
        creationflags=creationflags,
    )
    threading.Thread(target=stream_output, args=(backend_proc, "backend"), daemon=True).start()

    # Wait for backend
    print(f"  等待后端就绪 (端口 {BACKEND_PORT})...")
    for i in range(60):
        if backend_proc.poll() is not None:
            print(f"\n{C.RED}❌ 后端启动失败 (exit code: {backend_proc.returncode}){C.RESET}")
            print("   请检查上方日志输出")
            sys.exit(1)
        if is_port_in_use(BACKEND_PORT):
            break
        time.sleep(1)
    else:
        print(f"\n{C.RED}❌ 后端未在 60 秒内启动{C.RESET}")
        stop_process(backend_proc)
        sys.exit(1)
    print(f"  {C.GREEN}✅{C.RESET} 后端已就绪")

    # Start frontend
    print(f"\n{C.CYAN}🚀 启动前端 (Next.js)...{C.RESET}")
    frontend_proc = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=str(FRONTEND_DIR),
        shell=(os.name == "nt"),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
        bufsize=1,
    )
    threading.Thread(target=stream_output, args=(frontend_proc, "frontend"), daemon=True).start()

    time.sleep(3)
    if frontend_proc.poll() is not None:
        print(f"\n{C.RED}❌ 前端启动失败{C.RESET}")
        stop_process(backend_proc)
        sys.exit(1)

    procs = {"backend": backend_proc, "frontend": frontend_proc}

    print(f"""
{C.GREEN}{C.BOLD}
╔═══════════════════════════════════════════════╗
║   ✅ 所有服务已启动！                         ║
╚═══════════════════════════════════════════════╝{C.RESET}
{C.CYAN}  📊 前端界面:  http://localhost:{FRONTEND_PORT}
  📡 后端 API:   http://localhost:{BACKEND_PORT}
  📖 API 文档:   http://localhost:{BACKEND_PORT}/docs
  📕 ReDoc:      http://localhost:{BACKEND_PORT}/redoc{C.RESET}

{C.YELLOW}  按 Ctrl+C 停止所有服务{C.RESET}
""")

    # Monitor
    try:
        while True:
            for name, proc in list(procs.items()):
                code = proc.poll()
                if code is not None:
                    print(f"\n{name} 已退出 (code {code})，正在停止其他服务...")
                    for other_proc in procs.values():
                        if other_proc is not proc:
                            stop_process(other_proc)
                    return
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n\n{C.YELLOW}⏹️  正在停止所有服务...{C.RESET}")
        for proc in procs.values():
            stop_process(proc)
        print(f"{C.GREEN}✅ 所有服务已停止{C.RESET}")


# ========================= 入口 =========================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AI Code Review Platform — 一键启动脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
部署模式:
  docker   使用 Docker Compose 启动所有服务 (推荐)
  local    在本机直接运行后端和前端

环境变量 (通过 .env 文件配置):
  POSTGRES_HOST / POSTGRES_PORT / POSTGRES_PASSWORD
  REDIS_HOST / REDIS_PORT / REDIS_PASSWORD
  NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD
  JWT_SECRET / DEEPSEEK_API_KEY / GITHUB_TOKEN

示例:
  python start_all.py                # 自动检测模式
  python start_all.py --mode docker  # Docker 部署
  python start_all.py --mode local   # 本地开发
  python start_all.py --check        # 仅检查环境
"""
    )
    parser.add_argument(
        "--mode", choices=["docker", "local", "auto"], default="auto",
        help="部署模式: docker / local / auto (默认: auto)"
    )
    parser.add_argument(
        "--prod", action="store_true",
        help="使用生产环境配置 (仅 Docker 模式)"
    )
    parser.add_argument(
        "--check", action="store_true",
        help="仅检查环境配置，不启动服务"
    )
    parser.add_argument(
        "--stop", action="store_true",
        help="停止所有 Docker 服务"
    )
    parser.add_argument(
        "--logs", action="store_true",
        help="查看 Docker 服务日志 (实时跟踪)"
    )
    parser.add_argument(
        "--status", action="store_true",
        help="查看服务运行状态"
    )
    parser.add_argument(
        "--clean", action="store_true",
        help="清理所有 Docker 资源 (含数据卷)，从零开始"
    )
    parser.add_argument(
        "--open", action="store_true",
        help="启动完成后自动打开浏览器"
    )
    parser.add_argument(
        "--skip-deps", action="store_true",
        help="跳过依赖安装 (本地模式)"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print_banner()

    # Handle quick-action flags that don't need full env check
    if args.stop:
        stop_docker()
        return

    if args.logs:
        view_docker_logs(follow=True)
        return

    if args.status:
        show_container_status()
        return

    if args.clean:
        clean_docker()
        return

    # Ensure .env exists
    ensure_env_file()

    # Environment check
    print(f"\n{C.CYAN}🔍 环境检测:{C.RESET}\n")
    results = run_env_check(verbose=True)

    if args.check:
        print(f"\n{'=' * 50}")
        if results.get("docker"):
            print(f"  ✅ 支持 Docker 部署")
        if results.get("python") and results.get("node"):
            print(f"  ✅ 支持本地开发")
        if not results.get("postgres"):
            print(f"  ⚠️  PostgreSQL 不可达 — 建议使用 Docker 模式")
        env_vars = load_env_file()
        if not env_vars.get("NEXT_PUBLIC_GITHUB_CLIENT_ID", ""):
            print(f"  ⚠️  GitHub OAuth 未配置 — 项目导入功能需要")
        print(f"{'=' * 50}")
        return

    # Determine mode
    mode = args.mode
    if mode == "auto":
        if results.get("docker"):
            mode = "docker"
            print(f"\n{C.GREEN}🐳 检测到 Docker，自动选择 Docker 模式{C.RESET}")
        elif results.get("python") and results.get("node"):
            mode = "local"
            print(f"\n{C.GREEN}💻 使用本地模式{C.RESET}")
        else:
            print(f"\n{C.RED}❌ 无法确定部署模式:{C.RESET}")
            if not results.get("docker"):
                print(f"   - Docker 不可用")
            if not results.get("python"):
                print(f"   - Python 不可用")
            if not results.get("node"):
                print(f"   - Node.js 不可用")
            print(f"\n   请安装 Docker 或 Python + Node.js")
            sys.exit(1)

    if mode == "docker":
        if not results.get("docker"):
            # Try to auto-start Docker Desktop
            if not auto_start_docker_desktop():
                print(f"{C.RED}❌ Docker 不可用，请安装并启动 Docker Desktop{C.RESET}")
                print(f"   下载: https://docs.docker.com/desktop/install/windows-install/")
                sys.exit(1)
        start_docker(prod=args.prod, open_browser=args.open)
    else:
        start_local(args)


if __name__ == "__main__":
    main()
