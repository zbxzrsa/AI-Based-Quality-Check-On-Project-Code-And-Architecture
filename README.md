# 馃 AI Code Review Platform

AI 椹卞姩鐨勪唬鐮佸鏌ヤ笌鏋舵瀯鍒嗘瀽骞冲彴锛屾彁渚涙櫤鑳戒唬鐮佸鏌ャ€佹灦鏋勫彲瑙嗗寲鍜屽悎瑙勬€ф鏌ャ€?

## 鉁?鏍稿績鍔熻兘

| 鍔熻兘 | 鎻忚堪 |
|---|---|
| 馃攼 **鐢ㄦ埛璁よ瘉** | 娉ㄥ唽/鐧诲綍銆丣WT 浠ょ墝銆丷BAC 澶氳鑹叉潈闄愭帶鍒?|
| 馃攳 **PR 浠ｇ爜瀹℃煡** | 鍩轰簬 DeepSeek AI 鐨?Pull Request 鑷姩瀹℃煡銆佸畨鍏ㄨ瘎鍒嗐€佸悎瑙勬鏌?|
| 馃彈锔?**鏋舵瀯鍥剧敓鎴?* | 浠庝唬鐮佸鏌ョ粨鏋滆嚜鍔ㄧ敓鎴愭灦鏋勫彲瑙嗗寲鍥俱€佷緷璧栧叧绯诲浘 |
| 馃悪 **GitHub 闆嗘垚** | 浠撳簱绠＄悊銆丳R 鍚屾銆乄ebhook 鑷姩瑙﹀彂瀹℃煡 |
| 馃搳 **搴﹂噺鐩戞帶** | 浠ｇ爜璐ㄩ噺璇勫垎銆佸畨鍏ㄨ瘎鍒嗐€佹灦鏋勫仴搴峰害銆丳rometheus 鎸囨爣 |
| 馃敀 **浼佷笟绾у畨鍏?* | 鏁版嵁鍔犲瘑銆丆ORS 淇濇姢銆侀€熺巼闄愬埗銆佸璁℃棩蹇?|

## 馃洜锔?鎶€鏈爤

```
鍚庣: Python 3.11 + FastAPI + SQLAlchemy + PostgreSQL
鍥炬暟鎹簱: Neo4j 5+ (鏋舵瀯鍏崇郴鍒嗘瀽)
缂撳瓨: Redis 7+ (浼氳瘽/缂撳瓨/閫熺巼闄愬埗)
AI 瀹℃煡: DeepSeek API + 鍐呯疆瑙勫垯寮曟搸
鍓嶇: Next.js 14 + TypeScript + Tailwind CSS
璁よ瘉: JWT (PyJWT) + bcrypt + RBAC
杩愯鐜: conda lxq
```

## 馃搧 椤圭洰缁撴瀯

```
鈹溾攢鈹€ backend/                    # Python FastAPI 鍚庣
鈹?  鈹溾攢鈹€ app/
鈹?  鈹?  鈹溾攢鈹€ api/v1/endpoints/   # API 绔偣 (25涓?
鈹?  鈹?  鈹?  鈹溾攢鈹€ auth.py         # 璁よ瘉: 娉ㄥ唽/鐧诲綍/鍒锋柊
鈹?  鈹?  鈹?  鈹溾攢鈹€ pull_request.py # PR 鍒嗘瀽瑙﹀彂
鈹?  鈹?  鈹?  鈹溾攢鈹€ architecture.py # 鏋舵瀯鍥炬暟鎹?
鈹?  鈹?  鈹?  鈹溾攢鈹€ code_review.py  # 浠ｇ爜瀹℃煡
鈹?  鈹?  鈹?  鈹溾攢鈹€ github.py       # GitHub 闆嗘垚
鈹?  鈹?  鈹?  鈹溾攢鈹€ analyze.py      # 鏋舵瀯鍒嗘瀽
鈹?  鈹?  鈹?  鈹溾攢鈹€ rbac_*.py       # 瑙掕壊鏉冮檺绠＄悊
鈹?  鈹?  鈹?  鈹斺攢鈹€ ...             # 鍋ュ悍妫€鏌?瀹¤/鐩戞帶绛?
鈹?  鈹?  鈹溾攢鈹€ auth/               # 璁よ瘉妯″潡 (RBAC)
鈹?  鈹?  鈹?  鈹溾攢鈹€ models/         # User, Session, Project 妯″瀷
鈹?  鈹?  鈹?  鈹溾攢鈹€ services/       # RBAC 鏈嶅姟
鈹?  鈹?  鈹?  鈹斺攢鈹€ middleware/     # 璁よ瘉涓棿浠?
鈹?  鈹?  鈹溾攢鈹€ core/               # 鏍稿績閰嶇疆
鈹?  鈹?  鈹?  鈹溾攢鈹€ config.py       # 搴旂敤閰嶇疆 (Pydantic Settings)
鈹?  鈹?  鈹?  鈹斺攢鈹€ ...             # 鏃ュ織/鎸囨爣/瀹夊叏
鈹?  鈹?  鈹溾攢鈹€ database/           # 鏁版嵁搴撹繛鎺?
鈹?  鈹?  鈹?  鈹溾攢鈹€ postgresql.py   # PostgreSQL (async)
鈹?  鈹?  鈹?  鈹溾攢鈹€ neo4j_db.py     # Neo4j 鍥炬暟鎹簱
鈹?  鈹?  鈹?  鈹斺攢鈹€ redis_db.py     # Redis 缂撳瓨
鈹?  鈹?  鈹溾攢鈹€ models/             # 鏁版嵁妯″瀷
鈹?  鈹?  鈹溾攢鈹€ schemas/            # Pydantic Schema
鈹?  鈹?  鈹溾攢鈹€ services/           # 涓氬姟鏈嶅姟 (50涓?
鈹?  鈹?  鈹?  鈹溾攢鈹€ deepseek_service.py        # DeepSeek AI 璋冪敤
鈹?  鈹?  鈹?  鈹溾攢鈹€ ai_pr_reviewer.py          # AI PR 瀹℃煡
鈹?  鈹?  鈹?  鈹溾攢鈹€ code_reviewer.py           # 浠ｇ爜瀹℃煡寮曟搸
鈹?  鈹?  鈹?  鈹溾攢鈹€ github_client.py           # GitHub API 瀹㈡埛绔?
鈹?  鈹?  鈹?  鈹溾攢鈹€ architecture_analyzer/     # 鏋舵瀯鍒嗘瀽鍣?
鈹?  鈹?  鈹?  鈹溾攢鈹€ architecture_diagram_service.py  # 鏋舵瀯鍥剧敓鎴?
鈹?  鈹?  鈹?  鈹斺攢鈹€ ...                        # 瀹夊叏/鍔犲瘑/缂撳瓨绛?
鈹?  鈹?  鈹溾攢鈹€ middleware/         # 涓棿浠?(瀹夊叏澶?閫熺巼闄愬埗/Prometheus)
鈹?  鈹?  鈹溾攢鈹€ tasks/              # 寮傛浠诲姟 (Celery)
鈹?  鈹?  鈹斺攢鈹€ utils/              # 宸ュ叿鍑芥暟
鈹?  鈹溾攢鈹€ alembic/                # 鏁版嵁搴撹縼绉?
鈹?  鈹溾攢鈹€ requirements.txt        # Python 渚濊禆
鈹?  鈹斺攢鈹€ requirements.in         # 渚濊禆婧愭竻鍗?
鈹?
鈹溾攢鈹€ frontend/                   # Next.js 鍓嶇
鈹?  鈹溾攢鈹€ src/
鈹?  鈹?  鈹溾攢鈹€ app/                # 椤甸潰璺敱 (16涓?
鈹?  鈹?  鈹?  鈹溾攢鈹€ login/          # 鐧诲綍椤?
鈹?  鈹?  鈹?  鈹溾攢鈹€ register/       # 娉ㄥ唽椤?
鈹?  鈹?  鈹?  鈹溾攢鈹€ dashboard/      # 浠〃鏉?
鈹?  鈹?  鈹?  鈹溾攢鈹€ reviews/        # PR 瀹℃煡鍒楄〃/璇︽儏
鈹?  鈹?  鈹?  鈹溾攢鈹€ architecture/   # 鏋舵瀯鍥惧彲瑙嗗寲
鈹?  鈹?  鈹?  鈹溾攢鈹€ projects/       # 椤圭洰绠＄悊
鈹?  鈹?  鈹?  鈹溾攢鈹€ settings/       # 鐢ㄦ埛璁剧疆 (GitHub Token)
鈹?  鈹?  鈹?  鈹溾攢鈹€ admin/          # 绠＄悊鍚庡彴
鈹?  鈹?  鈹?  鈹溾攢鈹€ profile/        # 鐢ㄦ埛璧勬枡
鈹?  鈹?  鈹?  鈹斺攢鈹€ metrics/        # 搴﹂噺闈㈡澘
鈹?  鈹?  鈹溾攢鈹€ components/         # React 缁勪欢 (17缁?
鈹?  鈹?  鈹?  鈹溾攢鈹€ auth/           # 璁よ瘉缁勪欢 (RBAC 瀹堝崼)
鈹?  鈹?  鈹?  鈹溾攢鈹€ architecture/   # 鏋舵瀯鍥剧粍浠?
鈹?  鈹?  鈹?  鈹溾攢鈹€ review/         # 浠ｇ爜瀹℃煡缁勪欢
鈹?  鈹?  鈹?  鈹溾攢鈹€ dashboard/      # 浠〃鏉跨粍浠?
鈹?  鈹?  鈹?  鈹斺攢鈹€ ...             # 閫氱敤/甯冨眬/鍥捐〃绛?
鈹?  鈹?  鈹溾攢鈹€ contexts/           # React Context (璁よ瘉/涓婚)
鈹?  鈹?  鈹溾攢鈹€ services/           # API 璋冪敤鏈嶅姟
鈹?  鈹?  鈹溾攢鈹€ hooks/              # 鑷畾涔?Hooks
鈹?  鈹?  鈹溾攢鈹€ lib/                # 宸ュ叿搴?
鈹?  鈹?  鈹斺攢鈹€ types/              # TypeScript 绫诲瀷
鈹?  鈹斺攢鈹€ package.json
鈹?
鈹溾攢鈹€ docs/                       # 椤圭洰鏂囨。
鈹溾攢鈹€ scripts/                    # 宸ュ叿鑴氭湰
鈹溾攢鈹€ common/                     # 鍏变韩閰嶇疆
鈹溾攢鈹€ shared/                     # 鍏变韩绫诲瀷
鈹溾攢鈹€ docker-compose.yml          # Docker 缂栨帓 (寮€鍙戠幆澧?
鈹溾攢鈹€ docker-compose.prod.yml     # Docker 缂栨帓 (鐢熶骇鐜锛屽惈 Nginx)
鈹溾攢鈹€ nginx/
鈹?  鈹斺攢鈹€ nginx.conf              # Nginx 鍙嶅悜浠ｇ悊閰嶇疆
鈹溾攢鈹€ start_all.py                # 涓€閿惎鍔ㄨ剼鏈?(鏈湴寮€鍙?
鈹斺攢鈹€ .env                        # 鐜鍙橀噺閰嶇疆
```

## 馃殌 蹇€熷紑濮?

### 鍓嶇疆瑕佹眰

- **Python 3.11+** (Anaconda / Miniconda)
- **Node.js 18+**
- **PostgreSQL 14+**
- **Redis 7+**
- **Neo4j 5+** (鍙€夛紝鐢ㄤ簬鏋舵瀯鍥惧垎鏋?

### 瀹夎姝ラ

#### 1. 鍏嬮殕椤圭洰

```bash
git clone https://github.com/zbxzrsa/AI-Based-Quality-Check-On-Project-Code-And-Architecture.git
cd AI-Based-Quality-Check-On-Project-Code-And-Architecture
```

#### 2. 閰嶇疆鐜鍙橀噺

鍦ㄩ」鐩牴鐩綍鍒涘缓 `.env` 鏂囦欢锛?

```env
# === 鏁版嵁搴?===
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=ai_code_review
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres123

# === Redis ===
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# === Neo4j (鍙€? ===
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=neo4j123

# === 瀹夊叏 ===
JWT_SECRET=your-secret-key-at-least-32-characters-long
ENVIRONMENT=development

# === AI 瀹℃煡 (DeepSeek) ===
DEEPSEEK_API_KEY=your-deepseek-api-key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# === GitHub (鍙€? ===
GITHUB_TOKEN=ghp_your_github_token
```

#### 3. 鍚姩鍚庣

```bash
# 婵€娲?conda 鐜
conda activate lxq

# 瀹夎渚濊禆
cd backend
pip install -r requirements.txt

# 鍚姩鏈嶅姟
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 4. 鍚姩鍓嶇

```bash
# 鏂扮粓绔?
cd frontend
npm install
npm run dev
```

#### 5. 涓€閿惎鍔?(鍙€?

```bash
python start_all.py
```

### 璁块棶鍦板潃

| 鏈嶅姟 | 鍦板潃 |
|---|---|
| 鍓嶇鐣岄潰 | http://localhost:3000 |
| 鍚庣 API | http://localhost:8000 |
| API 鏂囨。 (Swagger) | http://localhost:8000/docs |
| API 鏂囨。 (ReDoc) | http://localhost:8000/redoc |

### 榛樿娴嬭瘯璐︽埛

```
閭: admin@example.com
瀵嗙爜: Admin123!
瑙掕壊: ADMIN
```

## 馃摉 API 姒傝

### 璁よ瘉 (`/api/v1/auth`)

| 鏂规硶 | 璺緞 | 鎻忚堪 |
|---|---|---|
| POST | `/register` | 鐢ㄦ埛娉ㄥ唽 |
| POST | `/login` | 鐢ㄦ埛鐧诲綍锛岃繑鍥?JWT |
| POST | `/refresh` | 鍒锋柊 Access Token |
| POST | `/logout` | 鐢ㄦ埛鐧诲嚭 |
| GET | `/me` | 鑾峰彇褰撳墠鐢ㄦ埛淇℃伅 |
| PUT | `/change-password` | 淇敼瀵嗙爜 |

### PR 鍒嗘瀽 (`/api/v1/analysis`)

| 鏂规硶 | 璺緞 | 鎻忚堪 |
|---|---|---|
| POST | `/projects/{id}/analyze` | 瑙﹀彂 PR 鍒嗘瀽 |
| GET | `/analysis/{task_id}/status` | 鏌ヨ鍒嗘瀽浠诲姟鐘舵€?|
| POST | `/projects/{id}/pull-requests/{pr_id}/reanalyze` | 閲嶆柊鍒嗘瀽 |
| POST | `/projects/{id}/circular-dependencies` | 寰幆渚濊禆妫€娴?|

### 鏋舵瀯鍙鍖?(`/api/v1/architecture`)

| 鏂规硶 | 璺緞 | 鎻忚堪 |
|---|---|---|
| GET | `/{project_id}/branches` | 鑾峰彇椤圭洰鍒嗘敮鍒楄〃 |
| GET | `/{project_id}/branches/{branch_id}/architecture` | 鍒嗘敮鏋舵瀯鍥炬暟鎹?|
| GET | `/dependencies/{project_id}` | 渚濊禆鍏崇郴鍥?|
| GET | `/architecture/{analysis_id}` | 鏋舵瀯鍒嗘瀽缁撴灉 |
| POST | `/diagram/generate` | 鍩轰簬瀹℃煡鐢熸垚鏋舵瀯鍥?|

### 浠ｇ爜瀹℃煡 (`/api/v1/code-review`)

| 鏂规硶 | 璺緞 | 鎻忚堪 |
|---|---|---|
| POST | `/webhook` | GitHub Webhook 鎺ユ敹 |
| GET | `/reviews` | 瀹℃煡璁板綍鍒楄〃 |
| GET | `/reviews/{id}` | 瀹℃煡璇︽儏 |

### GitHub 闆嗘垚 (`/api/v1/github`)

| 鏂规硶 | 璺緞 | 鎻忚堪 |
|---|---|---|
| GET | `/repos` | 鑾峰彇鐢ㄦ埛浠撳簱鍒楄〃 |
| GET | `/repos/{owner}/{repo}/pulls` | 鑾峰彇 PR 鍒楄〃 |
| GET | `/repos/{owner}/{repo}/pulls/{number}/diff` | 鑾峰彇 PR Diff |

### 鍏朵粬绔偣

- **RBAC** (`/rbac/users`, `/rbac/projects`, `/rbac/audit`) 鈥?瑙掕壊鏉冮檺绠＄悊
- **鍋ュ悍妫€鏌?* (`/health`, `/health/ready`, `/health/live`) 鈥?鏈嶅姟鐘舵€?
- **鐢ㄦ埛璁剧疆** (`/user/settings`) 鈥?GitHub Token 绛夐厤缃?
- **瀹¤鏃ュ織** (`/audit-logs`) 鈥?鎿嶄綔璁板綍鏌ヨ
- **鐩戞帶鎸囨爣** (`/metrics`) 鈥?Prometheus 鎸囨爣
- **鐢ㄦ埛鏁版嵁** (`/users`) 鈥?GDPR 鏁版嵁瀵煎嚭/鍒犻櫎

## 馃攼 璁よ瘉璇存槑

鎵€鏈夐渶瑕佽璇佺殑 API 绔偣闇€瑕佸湪 Header 涓惡甯?JWT Token锛?

```
Authorization: Bearer <your_jwt_token>
```

### 鐢ㄦ埛瑙掕壊

| 瑙掕壊 | 鏉冮檺 |
|---|---|
| `ADMIN` | 鍏ㄩ儴鏉冮檺锛岀敤鎴风鐞嗭紝瑙掕壊鍒嗛厤 |
| `DEVELOPER` | 椤圭洰璁块棶锛屼唬鐮佸鏌ワ紝鏋舵瀯鏌ョ湅 |
| `VIEWER` | 鍙璁块棶 |
| `VISITOR` | 娉ㄥ唽鍚庨粯璁よ鑹诧紝鍙楅檺璁块棶 |

## 馃敡 閰嶇疆璇存槑

鎵€鏈夐厤缃€氳繃鐜鍙橀噺绠＄悊 (`.env` 鏂囦欢)锛屽叧閿厤缃」锛?

| 鍙橀噺 | 蹇呴渶 | 榛樿鍊?| 鎻忚堪 |
|---|---|---|---|
| `JWT_SECRET` | 鉁?| dev-secret... | JWT 绛惧悕瀵嗛挜 (鈮?2瀛楃) |
| `POSTGRES_*` | 鉁?| localhost | PostgreSQL 杩炴帴淇℃伅 |
| `REDIS_*` | 鈿狅笍 | localhost | Redis 杩炴帴淇℃伅 (缂撳瓨鍙檷绾? |
| `NEO4J_*` | 鈿狅笍 | localhost | Neo4j 杩炴帴淇℃伅 (鍥惧垎鏋愬彲闄嶇骇) |
| `DEEPSEEK_API_KEY` | 鈿狅笍 | - | DeepSeek AI API Key |
| `GITHUB_TOKEN` | 鈿狅笍 | - | GitHub Personal Access Token |
| `ENVIRONMENT` | - | development | 杩愯鐜 |

> 鈿狅笍 = 鍙€夛紝缂哄け鏃跺搴斿姛鑳介檷绾т絾涓嶅奖鍝嶅惎鍔?

## 馃惓 Docker 閮ㄧ讲

### 鏁翠綋鏋舵瀯

```
鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
鈹?                   Docker Network (ai_review_network)        鈹?
鈹?                                                             鈹?
鈹? 鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹? 鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹? 鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹? 鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?   鈹?
鈹? 鈹侾ostgreSQL鈹? 鈹? Redis   鈹? 鈹? Neo4j   鈹? 鈹? Nginx   鈹?   鈹?
鈹? 鈹? :5432   鈹? 鈹? :6379   鈹? 鈹? :7687   鈹? 鈹? :80/443 鈹傗梽鈹€鈹€鈹€鈹€鈹€ 鐢ㄦ埛璁块棶
鈹? 鈹斺攢鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹? 鈹斺攢鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹? 鈹斺攢鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹? 鈹斺攢鈹€鈹攢鈹€鈹€鈹攢鈹€鈹€鈹?   鈹?
鈹?      鈹?             鈹?            鈹?          鈹?  鈹?        鈹?
鈹?      鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹尖攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?          鈹?  鈹?        鈹?
鈹?                     鈹?                        鈹?  鈹?        鈹?
鈹?             鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹粹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?               鈹?  鈹?        鈹?
鈹?             鈹?  Backend      鈹傗梽鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?  鈹?        鈹?
鈹?             鈹? (FastAPI)     鈹?                    鈹?        鈹?
鈹?             鈹?  :8000        鈹?                    鈹?        鈹?
鈹?             鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?                    鈹?        鈹?
鈹?             鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?                    鈹?        鈹?
鈹?             鈹?  Frontend     鈹傗梽鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?        鈹?
鈹?             鈹? (Next.js)     鈹?                              鈹?
鈹?             鈹?  :3000        鈹?                              鈹?
鈹?             鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?                              鈹?
鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
```

### 鍓嶇疆瑕佹眰

- **Docker Engine 24+** & **Docker Compose V2** ([瀹夎鎸囧崡](https://docs.docker.com/engine/install/))
- 鑷冲皯 **4 GB** 绌洪棽鍐呭瓨锛圢eo4j 闇€瑕佽緝澶氬唴瀛橈級
- 閰嶇疆濂?`.env` 鏂囦欢锛堝弬鑰冧笂鏂?[閰嶇疆鐜鍙橀噺](#2-閰嶇疆鐜鍙橀噺) 绔犺妭锛?

---

### 鏂瑰紡涓€锛氬紑鍙戠幆澧冮儴缃?

寮€鍙戠幆澧冩敮鎸?**鐑噸杞?*锛屼唬鐮佷慨鏀瑰悗鑷姩鐢熸晥锛岄€傚悎鏃ュ父寮€鍙戣皟璇曘€?

#### 1. 涓€閿惎鍔ㄦ墍鏈夋湇鍔?

```bash
# 鍦ㄩ」鐩牴鐩綍鎵ц
docker-compose up -d
```

#### 2. 鏌ョ湅鍚姩鐘舵€?

```bash
docker-compose ps
```

姝ｅ父杈撳嚭绀轰緥锛?

```
NAME                   STATUS                   PORTS
ai_based_quality_check_on_project_code_and_architecture_postgres     Up (healthy)             0.0.0.0:5432->5432/tcp
ai_based_quality_check_on_project_code_and_architecture_redis        Up (healthy)             0.0.0.0:6379->6379/tcp
ai_based_quality_check_on_project_code_and_architecture_neo4j        Up (healthy)             0.0.0.0:7474->7474/tcp, 0.0.0.0:7687->7687/tcp
ai_based_quality_check_on_project_code_and_architecture_backend      Up (healthy)             0.0.0.0:8000->8000/tcp
ai_based_quality_check_on_project_code_and_architecture_frontend     Up                       0.0.0.0:3000->3000/tcp
```

#### 3. 鍒濆鍖栨暟鎹簱 (棣栨閮ㄧ讲)

```bash
# 杩涘叆鍚庣瀹瑰櫒鎵ц鏁版嵁搴撹縼绉?
docker exec -it ai_based_quality_check_on_project_code_and_architecture_backend alembic upgrade head
```

#### 4. 璁块棶鏈嶅姟

| 鏈嶅姟 | 鍦板潃 | 璇存槑 |
|---|---|---|
| 鍓嶇鐣岄潰 | http://localhost:3000 | Next.js 寮€鍙戞湇鍔″櫒 |
| 鍚庣 API | http://localhost:8000 | FastAPI  |
| Swagger 鏂囨。 | http://localhost:8000/docs | 浜や簰寮?API 鏂囨。 |
| Neo4j Browser | http://localhost:7474 | 鍥炬暟鎹簱鍙鍖?|

#### 5. 鏌ョ湅鏃ュ織

```bash
# 鏌ョ湅鎵€鏈夋湇鍔℃棩蹇?
docker-compose logs -f

# 鍙湅鍚庣鏃ュ織
docker-compose logs -f backend

# 鍙湅鍓嶇鏃ュ織
docker-compose logs -f frontend
```

#### 6. 鍋滄 / 閿€姣?

```bash
# 鍋滄鏈嶅姟 (淇濈暀鏁版嵁鍗?
docker-compose down

# 鍋滄骞跺垹闄ゆ暟鎹嵎 (瀹屽叏閲嶇疆)
docker-compose down -v
```

---

### 鏂瑰紡浜岋細鐢熶骇鐜閮ㄧ讲

鐢熶骇鐜浣跨敤 **Nginx 鍙嶅悜浠ｇ悊**銆?*澶氶樁娈垫瀯寤洪暅鍍?*锛屾暟鎹簱绔彛涓嶆毚闇插埌瀹夸富鏈恒€?

#### 1. 鍑嗗鐢熶骇閰嶇疆

纭繚 `.env` 涓缃簡瀹夊叏鐨勫瘑鐮佸拰瀵嗛挜锛?

```env
# .env (鐢熶骇鐜 鈥?蹇呴』淇敼浠ヤ笅鍊?
POSTGRES_PASSWORD=<寮哄瘑鐮?
REDIS_PASSWORD=<寮哄瘑鐮?
NEO4J_PASSWORD=<寮哄瘑鐮?
JWT_SECRET=<鑷冲皯32瀛楃鐨勯殢鏈哄瘑閽?
ENVIRONMENT=production
DEEPSEEK_API_KEY=<浣犵殑API Key>
```

#### 2. 鍒涘缓 SSL 璇佷功鐩綍 (鍙€夛紝HTTPS)

```bash
mkdir -p nginx/ssl
# 灏嗕綘鐨勮瘉涔︽枃浠舵斁鍏?
#   nginx/ssl/cert.pem
#   nginx/ssl/key.pem
```

#### 3. 鏋勫缓骞跺惎鍔?

```bash
docker-compose -f docker-compose.prod.yml up -d --build
```

#### 4. 鍒濆鍖栨暟鎹簱

```bash
docker exec -it ai_based_quality_check_on_project_code_and_architecture_backend alembic upgrade head
```

#### 5. 璁块棶

| 鏈嶅姟 | 鍦板潃 | 璇存槑 |
|---|---|---|
| 缁熶竴鍏ュ彛 | http://localhost (鎴?https://your-domain.com) | Nginx 鍙嶅悜浠ｇ悊 |
| API | http://localhost/api/ | 鐢?Nginx 杞彂鍒板悗绔?|
| API 鏂囨。 | http://localhost/docs | Swagger UI |

---

### 鍚勬湇鍔¤瑙?

#### 馃悩 PostgreSQL (涓绘暟鎹簱)

| 椤圭洰 | 鍊?|
|---|---|
| 闀滃儚 | `postgres:16-alpine` |
| 瀹瑰櫒鍚?| `ai_based_quality_check_on_project_code_and_architecture_postgres` |
| 鍐呴儴绔彛 | `5432` |
| 鏁版嵁鍗?| `postgres_data` |
| 鍋ュ悍妫€鏌?| `pg_isready` |

瀛樺偍鎵€鏈変笟鍔℃暟鎹細鐢ㄦ埛銆侀」鐩€佸鏌ヨ褰曘€丷BAC 鏉冮檺绛夈€?

```bash
# 鎵嬪姩杩炴帴鏁版嵁搴?
docker exec -it ai_based_quality_check_on_project_code_and_architecture_postgres psql -U postgres -d ai_code_review

# 澶囦唤鏁版嵁搴?
docker exec ai_based_quality_check_on_project_code_and_architecture_postgres pg_dump -U postgres ai_code_review > backup.sql

# 鎭㈠鏁版嵁搴?
docker exec -i ai_based_quality_check_on_project_code_and_architecture_postgres psql -U postgres ai_code_review < backup.sql
```

#### 馃敶 Redis (缂撳瓨 & 閫熺巼闄愬埗)

| 椤圭洰 | 鍊?|
|---|---|
| 闀滃儚 | `redis:7-alpine` |
| 瀹瑰櫒鍚?| `ai_based_quality_check_on_project_code_and_architecture_redis` |
| 鍐呴儴绔彛 | `6379` |
| 鏁版嵁鍗?| `redis_data` |
| 鍐呭瓨闄愬埗 | 寮€鍙?256MB / 鐢熶骇 512MB |

鐢ㄤ簬 JWT Session 缂撳瓨銆丄PI 閫熺巼闄愬埗璁℃暟鍣ㄣ€丏eepSeek API 璋冪敤缂撳瓨銆?

```bash
# 杩炴帴 Redis CLI
docker exec -it ai_based_quality_check_on_project_code_and_architecture_redis redis-cli

# 鏌ョ湅缂撳瓨鐘舵€?
docker exec -it ai_based_quality_check_on_project_code_and_architecture_redis redis-cli info memory
```

#### 馃數 Neo4j (鍥炬暟鎹簱)

| 椤圭洰 | 鍊?|
|---|---|
| 闀滃儚 | `neo4j:5-community` |
| 瀹瑰櫒鍚?| `ai_based_quality_check_on_project_code_and_architecture_neo4j` |
| Bolt 绔彛 | `7687` |
| Browser 绔彛 | `7474` (浠呭紑鍙戠幆澧冩毚闇? |
| 鎻掍欢 | APOC |

瀛樺偍浠ｇ爜鏋舵瀯鍏崇郴锛氭ā鍧椾緷璧栧浘銆佺被缁ф壙鍏崇郴銆佸惊鐜緷璧栨娴嬬粨鏋溿€?

```bash
# 閫氳繃 cypher-shell 鎵ц鏌ヨ
docker exec -it ai_based_quality_check_on_project_code_and_architecture_neo4j cypher-shell -u neo4j -p neo4j123

# 娓呯┖鎵€鏈夊浘鏁版嵁
docker exec -it ai_based_quality_check_on_project_code_and_architecture_neo4j cypher-shell -u neo4j -p neo4j123 "MATCH (n) DETACH DELETE n"
```

#### 鈿?Backend 鈥?FastAPI

| 椤圭洰 | 鍊?|
|---|---|
| 鏋勫缓鏂囦欢 | 寮€鍙? `backend/Dockerfile.dev`锛岀敓浜? `backend/Dockerfile` |
| 瀹瑰櫒鍚?| `ai_based_quality_check_on_project_code_and_architecture_backend` |
| 鍐呴儴绔彛 | `8000` |
| 鍋ュ悍妫€鏌?| `GET /health` |

**Docker 鍐呮湇鍔″彂鐜?(鍏抽敭)**锛氬湪 `docker-compose.yml` 涓紝鐜鍙橀噺浼?**瑕嗙洊** `.env` 涓殑 `localhost` 涓?Docker 鏈嶅姟鍚嶏細

```yaml
environment:
  POSTGRES_HOST: postgres      # 鈫?涓嶆槸 localhost锛屾槸 Docker 鏈嶅姟鍚?
  REDIS_HOST: redis            # 鈫?鍚屼笂
  NEO4J_URI: bolt://neo4j:7687 # 鈫?鍚屼笂
```

杩欐槸瀹瑰櫒闂撮€氫俊鐨勬牳蹇冩満鍒?鈥?Docker Compose 浼氳嚜鍔ㄥ皢鏈嶅姟鍚嶈В鏋愪负瀵瑰簲瀹瑰櫒鐨?IP銆?

```bash
# 杩涘叆鍚庣瀹瑰櫒 Shell
docker exec -it ai_based_quality_check_on_project_code_and_architecture_backend bash

# 杩愯鏁版嵁搴撹縼绉?
docker exec -it ai_based_quality_check_on_project_code_and_architecture_backend alembic upgrade head

# 鏌ョ湅鍚庣鏃ュ織
docker logs -f ai_based_quality_check_on_project_code_and_architecture_backend
```

#### 馃帹 Frontend 鈥?Next.js

| 椤圭洰 | 鍊?|
|---|---|
| 鏋勫缓鏂囦欢 | 寮€鍙? `frontend/Dockerfile.dev`锛岀敓浜? `frontend/Dockerfile.prod` |
| 瀹瑰櫒鍚?| `ai_based_quality_check_on_project_code_and_architecture_frontend` |
| 鍐呴儴绔彛 | `3000` |

**鍓嶇濡備綍璋冪敤鍚庣 API**锛?

- **娴忚鍣ㄧ (瀹㈡埛绔覆鏌?**锛氶€氳繃 `NEXT_PUBLIC_API_URL` 璁块棶鍚庣
  - 寮€鍙戠幆澧冿細`http://localhost:8000` (鐩存帴璁块棶鍚庣绔彛)
  - 鐢熶骇鐜锛歚/api` (閫氳繃 Nginx 鍙嶄唬)
- **鏈嶅姟绔覆鏌?(SSR)**锛氶€氳繃 `NEXT_PUBLIC_BACKEND_URL` 鍦?Docker 鍐呴儴缃戠粶鐩磋繛鍚庣
  - 鍊间负 `http://backend:8000` (Docker 鏈嶅姟鍚?

```bash
# 鏌ョ湅鍓嶇鏃ュ織
docker logs -f ai_based_quality_check_on_project_code_and_architecture_frontend

# 閲嶆柊鏋勫缓鍓嶇闀滃儚
docker-compose build frontend
```

#### 馃寪 Nginx (浠呯敓浜х幆澧?

| 椤圭洰 | 鍊?|
|---|---|
| 闀滃儚 | `nginx:alpine` |
| 鏆撮湶绔彛 | `80`, `443` |
| 閰嶇疆鏂囦欢 | `nginx/nginx.conf` |

璺敱瑙勫垯锛?

| 璺緞 | 浠ｇ悊鍒?| 璇存槑 |
|---|---|---|
| `/api/*` | `backend:8000` | 鍚庣 API |
| `/docs`, `/redoc` | `backend:8000` | API 鏂囨。 |
| `/health`, `/metrics` | `backend:8000` | 鐩戞帶绔偣 |
| `/ws` | `backend:8000` | WebSocket |
| `/*` (鍏朵粬) | `frontend:3000` | 鍓嶇椤甸潰 |

---

### Docker 鏂囦欢娓呭崟

```
鈹溾攢鈹€ docker-compose.yml          # 寮€鍙戠幆澧冪紪鎺?(5涓湇鍔?
鈹溾攢鈹€ docker-compose.prod.yml     # 鐢熶骇鐜缂栨帓 (6涓湇鍔★紝鍚?Nginx)
鈹溾攢鈹€ nginx/
鈹?  鈹斺攢鈹€ nginx.conf              # Nginx 鍙嶅悜浠ｇ悊閰嶇疆
鈹溾攢鈹€ backend/
鈹?  鈹溾攢鈹€ Dockerfile              # 鍚庣鐢熶骇闀滃儚 (澶氶樁娈垫瀯寤?
鈹?  鈹溾攢鈹€ Dockerfile.dev          # 鍚庣寮€鍙戦暅鍍?(鐑噸杞?
鈹?  鈹斺攢鈹€ .dockerignore           # 鏋勫缓鎺掗櫎鍒楄〃
鈹溾攢鈹€ frontend/
鈹?  鈹溾攢鈹€ Dockerfile              # 鍓嶇鐢熶骇闀滃儚
鈹?  鈹溾攢鈹€ Dockerfile.dev          # 鍓嶇寮€鍙戦暅鍍?(鐑噸杞?
鈹?  鈹斺攢鈹€ Dockerfile.prod         # 鍓嶇鐢熶骇浼樺寲闀滃儚
鈹斺攢鈹€ backend/security/
    鈹斺攢鈹€ docker-compose.zap.yml  # OWASP ZAP 瀹夊叏鎵弿 (鎸夐渶鍚姩)
```

---

### 甯哥敤杩愮淮鍛戒护

```bash
# 閲嶆柊鏋勫缓鎵€鏈夐暅鍍?
docker-compose build --no-cache

# 鍙噸鍚悗绔?
docker-compose restart backend

# 鏌ョ湅璧勬簮鍗犵敤
docker stats

# 娓呯悊鏈娇鐢ㄧ殑闀滃儚/缃戠粶/鍗?
docker system prune -a

# 鏌ョ湅 Docker 缃戠粶涓殑瀹瑰櫒杩炴帴
docker network inspect ai-based-quality-check-on-project-code-and-architecture_ai_review_network
```

### 甯歌闂

**Q: 鍚庣鎶?`Connection refused` 杩炰笉涓婃暟鎹簱锛?*
> 纭繚 `docker-compose.yml` 涓?`POSTGRES_HOST` 璁剧疆涓?`postgres` 鑰屼笉鏄?`localhost`銆傚鍣ㄩ棿閫氫俊浣跨敤 Docker 鏈嶅姟鍚嶃€?

**Q: 鍓嶇椤甸潰鍔犺浇浜嗕絾 API 璋冪敤澶辫触锛?*
> 寮€鍙戠幆澧冩鏌?`NEXT_PUBLIC_API_URL` 鏄惁涓?`http://localhost:8000`锛涚敓浜х幆澧冩鏌?Nginx 閰嶇疆鏄惁姝ｇ‘浠ｇ悊浜?`/api/` 璺緞銆?

**Q: Neo4j 鍚姩寰堟參锛?*
> Neo4j 棣栨鍚姩闇€瑕佸垵濮嬪寲鏁版嵁搴擄紝寤鸿鑷冲皯绛夊緟 30 绉掋€傚彲閫氳繃 `docker logs -f ai_based_quality_check_on_project_code_and_architecture_neo4j` 鏌ョ湅鍚姩杩涘害銆?

**Q: 濡備綍鍦ㄤ笉褰卞搷鏁版嵁鐨勬儏鍐典笅鏇存柊浠ｇ爜锛?*
> ```bash
> git pull
> docker-compose up -d --build   # 鍙噸寤烘湁鍙樻洿鐨勯暅鍍?
> ```

## 馃搫 License

MIT License

