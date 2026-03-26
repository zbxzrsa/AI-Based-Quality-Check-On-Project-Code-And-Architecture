# 馃惓 Docker 涓€閿儴缃叉寚鍗?

## 鐜瑕佹眰

| 杞欢 | 鏈€浣庣増鏈?| 璇存槑 |
|------|---------|------|
| **Docker Desktop** | 4.0+ | [涓嬭浇鍦板潃](https://docs.docker.com/desktop/) |
| **Docker Compose** | v2.0+ | Docker Desktop 鑷甫 |
| **Git** | 2.30+ | 鐢ㄤ簬鍏嬮殕浠撳簱 |

> 馃挕 Windows 鐢ㄦ埛璇风‘淇?Docker Desktop 宸插惎鍔ㄥ苟鏄剧ず "Engine running" 鐘舵€?

---

## 蹇€熼儴缃诧紙3 姝ュ畬鎴愶級

### 绗?1 姝ワ細鍏嬮殕浠撳簱

```bash
git clone https://github.com/lv-g-eng/ai--reviewer.git
cd ai--reviewer
```

### 绗?2 姝ワ細閰嶇疆鐜鍙橀噺

椤圭洰鏍圭洰褰曞凡鏈?`.env` 鏂囦欢锛屽寘鍚粯璁ら厤缃€傚闇€鑷畾涔夛紝鍙紪杈戜互涓嬪叧閿」锛?

```bash
# 鏌ョ湅骞舵寜闇€淇敼 .env
cat .env
```

**涓昏閰嶇疆椤硅鏄庯細**

| 鍙橀噺鍚?| 榛樿鍊?| 璇存槑 |
|--------|--------|------|
| `POSTGRES_PASSWORD` | `postgres123` | 鏁版嵁搴撳瘑鐮?|
| `JWT_SECRET` | `dev-secret-key...` | JWT 绛惧悕瀵嗛挜锛堢敓浜х幆澧冭淇敼锛?|
| `DEEPSEEK_API_KEY` | (绌? | DeepSeek AI API 瀵嗛挜锛堝彲閫夛紝AI瀹℃煡鍔熻兘闇€瑕侊級 |
| `GITHUB_TOKEN` | (绌? | GitHub Personal Access Token锛堝彲閫夛紝鍚屾浠撳簱PR闇€瑕侊級 |

### 绗?3 姝ワ細涓€閿惎鍔?

**鏂瑰紡涓€锛氫娇鐢ㄥ惎鍔ㄨ剼鏈紙鎺ㄨ崘锛?*
```bash
python start_all.py --mode docker
```

**鏂瑰紡浜岋細鐩存帴浣跨敤 Docker Compose**
```bash
docker compose up -d --build
```

绛夊緟鎵€鏈夊鍣ㄥ惎鍔紙绾?1-2 鍒嗛挓锛夛紝鐪嬪埌浠ヤ笅鐘舵€佽〃绀烘垚鍔燂細
```
鉁?Container ai_based_quality_check_on_project_code_and_architecture_postgres    Healthy
鉁?Container ai_based_quality_check_on_project_code_and_architecture_redis       Healthy
鉁?Container ai_based_quality_check_on_project_code_and_architecture_neo4j       Healthy
鉁?Container ai_based_quality_check_on_project_code_and_architecture_backend     Healthy
鉁?Container ai_based_quality_check_on_project_code_and_architecture_frontend    Created
```

---

## 璁块棶鏈嶅姟

| 鏈嶅姟 | 鍦板潃 | 璇存槑 |
|------|------|------|
| **馃寪 鍓嶇鐣岄潰** | http://localhost:3000 | 涓荤晫闈?|
| **馃摗 鍚庣 API** | http://localhost:8000 | REST API |
| **馃摉 API 鏂囨。** | http://localhost:8000/docs | Swagger UI |
| **馃梽锔?Neo4j 娴忚鍣?* | http://localhost:7474 | 鍥炬暟鎹簱绠＄悊 |

### 榛樿鐧诲綍璐﹀彿

```
閭: admin@example.com
瀵嗙爜: Admin123!
```

---

## 鏈嶅姟鏋舵瀯

```
鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?    鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
鈹?  Frontend  鈹傗攢鈹€鈹€鈹€鈻垛攤   Backend   鈹?
鈹? (Next.js)  鈹?    鈹? (FastAPI)  鈹?
鈹? :3000      鈹?    鈹? :8000      鈹?
鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?    鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹€鈹?
                           鈹?
              鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹尖攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
              鈻?           鈻?           鈻?
        鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
        鈹侾ostgreSQL鈹?鈹? Redis   鈹?鈹? Neo4j   鈹?
        鈹? :5432   鈹?鈹? :6379   鈹?鈹? :7687   鈹?
        鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
```

---

## 甯哥敤 Docker 鍛戒护

```bash
# 鏌ョ湅瀹瑰櫒鐘舵€?
docker compose ps

# 鏌ョ湅鏃ュ織锛堝疄鏃讹級
docker compose logs -f

# 鍙湅鍚庣鏃ュ織
docker compose logs -f backend

# 鍋滄鎵€鏈夋湇鍔?
docker compose down

# 鍋滄骞舵竻闄ゆ暟鎹紙鈿狅笍 浼氬垹闄ゆ暟鎹簱鏁版嵁锛?
docker compose down -v

# 閲嶆柊鏋勫缓骞跺惎鍔紙浠ｇ爜鏇存柊鍚庯級
docker compose up -d --build

# 杩涘叆鍚庣瀹瑰櫒璋冭瘯
docker exec -it ai_based_quality_check_on_project_code_and_architecture_backend bash

# 杩涘叆鏁版嵁搴?
docker exec -it ai_based_quality_check_on_project_code_and_architecture_postgres psql -U postgres -d ai_code_review
```

---

## 浣跨敤娴佺▼

1. **鐧诲綍** 鈫?浣跨敤榛樿璐﹀彿鐧诲綍绯荤粺
2. **娣诲姞椤圭洰** 鈫?鍦?Projects 椤甸潰娣诲姞 GitHub 浠撳簱锛堥渶瑕?GitHub Token锛?
3. **鍚屾 PR** 鈫?鐐瑰嚮椤圭洰鐨?"鍚屾" 鎸夐挳鎷夊彇 Pull Request 鍒楄〃
4. **寮€濮嬪鏌?* 鈫?鍦?Pull Requests 椤甸潰鐐瑰嚮 "寮€濮嬪鏌? 瑙﹀彂 AI 浠ｇ爜瀹℃煡
5. **鏌ョ湅鏋舵瀯** 鈫?鍦?Architecture 椤甸潰閫夋嫨椤圭洰鍜屽垎鏀煡鐪嬩唬鐮佹灦鏋勫浘

---

## 鏁呴殰鎺掓煡

### 瀹瑰櫒鍚姩澶辫触
```bash
# 鏌ョ湅璇︾粏閿欒鏃ュ織
docker compose logs backend

# 妫€鏌ョ鍙ｅ崰鐢?
netstat -ano | findstr :8000
netstat -ano | findstr :3000

# 鍋滄鍗犵敤绔彛鐨勮繘绋嬪悗閲嶈瘯
docker compose down
docker compose up -d --build
```

### 鏁版嵁搴撹繛鎺ュけ璐?
```bash
# 妫€鏌?PostgreSQL 瀹瑰櫒鐘舵€?
docker compose ps postgres

# 鎵嬪姩鍒濆鍖栨暟鎹簱鎵╁睍
docker exec ai_based_quality_check_on_project_code_and_architecture_postgres psql -U postgres -d ai_code_review -c 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'
```

### 閲嶇疆鎵€鏈夋暟鎹?
```bash
docker compose down -v
docker compose up -d --build
```

