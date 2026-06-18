<div align="center">
<img src="https://capsule-render.vercel.app/api?type=waving&color=0:2E7D32,100:8BC34A&height=200&section=header&text=All-in-One%20Fresh%20Farm&fontSize=46&fontColor=ffffff&animation=fadeIn&fontAlignY=38&desc=Harvest%20to%20Sale,%20Fully%20Automated&descAlignY=58&descSize=18" />

<p>
  <img src="https://img.shields.io/badge/version-MVP-2E7D32?style=for-the-badge" />
  <img src="https://img.shields.io/badge/license-MIT-8BC34A?style=for-the-badge" />
  <img src="https://img.shields.io/badge/status-active-success?style=for-the-badge" />
</p>

<p>
  <img src="https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/MariaDB-003545?style=flat-square&logo=mariadb&logoColor=white" />
  <img src="https://img.shields.io/badge/Streamlit-FF4B4B?style=flat-square&logo=streamlit&logoColor=white" />
  <img src="https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white" />
  <img src="https://img.shields.io/badge/Ollama-000000?style=flat-square&logo=ollama&logoColor=white" />
</p>

### 과일 수확부터 판매까지, AI 한 번에 처리합니다.
선별 · 재고 · 시세 예측 · 등록 · 주문 관리를 하나의 흐름으로 통합한 농장 운영 MVP

</div>

<br>

```
🤖 수확/선별 로봇 → FastAPI → MariaDB ⇄ RAG/LLM
                                  ├─ 📊 관리자 대시보드
                                  └─ 🛒 Fresh Farm Market (고객용)
```

운영자는 **대시보드**에서 재고·주문을 확인하고 AI 도우미로 판매 등록과 운영 질문을 처리합니다. 고객은 별도의 **Fresh Farm Market** 페이지에서 상품을 보고 주문합니다.

<br>

## Why this project?

- ⚡ **농장 PC 한 대로 완결** — 클라우드 없이 로컬 LLM + 로컬 DB로 완전히 작동
- 🔄 **무료 ↔ Pro 전환이 코드 변경 없이** — 같은 `rag_docs/`를 쓰고 AI 백엔드만 교체
- 🤖 **로봇 연동을 염두에 둔 설계** — 수확 로봇이 API만 호출하면 재고에 즉시 반영
- 📈 **시세 예측까지 자동화** — Chronos mini로 생성한 예측을 RAG 문서로 흡수

<br>

## 🆚 Free vs Pro

```diff
+ Free   rag_docs → Ollama embedding   → 로컬 MariaDB     → Qwen 답변   (오프라인 자립형)
! Pro    rag_docs → OpenAI embedding   → Docker MariaDB   → GPT 답변    (서버/클라우드 배포형)
```

| | Free | Pro |
|---|---|---|
| 실행 환경 | PC / 엣지 로컬 | Docker 서버·클라우드 |
| Embedding 차원 | Ollama 로컬 모델 | OpenAI `text-embedding-3-small` (1536) |

> 두 버전 모두 `rag_docs/`, `fruits_data/`를 공용으로 사용합니다 — **문서는 같고, AI 처리 방식만 다릅니다.**

<br>

## ✨ Features

```
📦 재고 · 판매상품 · 주문 · 구매이력 · 알림 관리
🔍 MariaDB Vector 기반 RAG 검색
📰 가격/뉴스 자동 수집 및 요약 반영
📊 Chronos mini 기반 사과 시세 예측
🛒 Streamlit 관리자 대시보드 + Apple Market 쇼핑몰
```

<br>

## 📁 프로젝트 구조

```text
app/                  # 무료/Pro 공용 애플리케이션 코드
├── api/              # FastAPI 라우터
├── db/                # DB 연결, 스키마, 판매/인증/메모리 관리
├── llm/               # Ollama / OpenAI 호출
├── news/              # 과일 뉴스 수집·요약
├── prices/            # 가격 데이터 수집
├── rag/                # 문서 ingest, embedding, 검색, 프롬프트
└── ui/                 # Streamlit 관리자/마켓 UI

rag_docs/             # 무료/Pro 공용 RAG 문서
fruits_data/           # 사과 시세 원본 데이터
reviews/                # 코드 리뷰용 문서

editions/
├── free/              # 무료 로컬 버전 설정
│   ├── .env.example
│   └── README_FREE.md
└── pro/                # Pro 서버/Docker 버전 설정
    ├── .env.pro.example
    ├── Dockerfile
    ├── docker-compose.pro.yml
    ├── requirements-pro.txt
    └── README_PRO.md

requirements.txt       # 무료 로컬 버전 패키지
README.md              # 전체 프로젝트 설명
```

<br>

## 🚀 무료 로컬 버전 실행

### 1. 환경 설정

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item editions\free\.env.example .env
```

`.env` 설정값:

```env
MARIADB_HOST=localhost
MARIADB_PORT=3306
MARIADB_USER=rag_user
MARIADB_PASSWORD=rag_password
MARIADB_DATABASE=fruits_rag

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_CHAT_MODEL=qwen2.5:7b
OLLAMA_EMBEDDING_MODEL=bge-m3

LLM_PROVIDER=ollama
EMBEDDING_PROVIDER=ollama
CHAT_API_URL=http://localhost:8000/chat
```

### 2. DB 스키마 & RAG 문서 준비

```powershell
python -m app.db.init_schema
python -m app.rag.ingest_docs
```

### 3. 서버 & 화면 실행

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
python -m streamlit run app/ui/streamlit_app.py --server.port 8501
python -m streamlit run app/ui/shop_app.py --server.port 8502
```

```
관리자 대시보드   http://localhost:8501   (admin / admin1234)
Apple Market     http://localhost:8502   (customer / customer1234)
FastAPI          http://localhost:8000/health
```

<br>

## 🐳 Pro Docker 버전 실행

### 1. 환경 설정

```powershell
Copy-Item editions\pro\.env.pro.example editions\pro\.env.pro
```

`editions/pro/.env.pro` 설정값:

```env
OPENAI_API_KEY=...
OPENAI_CHAT_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

MARIADB_USER=pro_rag_user
MARIADB_PASSWORD=change-this-password
MARIADB_DATABASE=fruits_rag_pro
MARIADB_ROOT_PASSWORD=change-this-root-password
```

### 2. 실행

```powershell
docker compose --env-file editions/pro/.env.pro -f editions/pro/docker-compose.pro.yml up -d --build
```

### 3. 상태 확인

```powershell
docker compose --env-file editions/pro/.env.pro -f editions/pro/docker-compose.pro.yml ps
docker compose --env-file editions/pro/.env.pro -f editions/pro/docker-compose.pro.yml logs -f api
```

```
관리자 Pro        http://localhost:8601   (adminpro / adminpro1234)
Apple Market Pro  http://localhost:8602   (customerpro / customerpro1234)
FastAPI           http://localhost:8000/health
```

### 종료

```powershell
docker compose --env-file editions/pro/.env.pro -f editions/pro/docker-compose.pro.yml down
```

<br>

## 🌐 외부 접속과 배포

현재 PC에서 Docker Desktop으로 실행하면 기본적으로 **내 PC가 서버 역할**을 합니다.

같은 내부망에서 접속하려면 PC의 내부 IP와 포트를 사용합니다.

```text
http://PC_IP:8601
http://PC_IP:8602
```

> ⚠️ 학교나 기관망에서는 방화벽 정책 때문에 외부 기기 접속이 막힐 수 있습니다. 이 경우 **Cloudflare Tunnel**, **ngrok**, **Oracle Cloud** 같은 서버 배포 방식이 필요합니다.

클라우드 서버에 올릴 때는 Pro Docker 구성을 그대로 사용할 수 있습니다. 서버 방화벽에서 `8000`, `8601`, `8602` 포트를 열고, 실제 운영에서는 HTTPS와 도메인을 붙이는 것을 권장합니다.

<br>

## 📚 RAG 문서 관리

RAG 문서는 `rag_docs/` 폴더의 Markdown 파일을 사용합니다.

문서를 추가하거나 수정한 뒤 다시 적재합니다.

```powershell
python -m app.rag.ingest_docs
```

> Pro Docker에서는 컨테이너 시작 시 **자동으로 문서를 적재**합니다.

### ⚠️ 주의할 점

- 무료 버전과 Pro 버전은 같은 `rag_docs/`를 사용합니다.
- 무료 버전은 Ollama embedding 차원을 사용합니다.
- Pro 버전은 OpenAI embedding 차원인 **1536**을 사용합니다.
- embedding 차원이 바뀌면 `rag_documents` 테이블을 **재생성**해야 합니다.

<br>

## 📰 가격 정보와 뉴스 업데이트

가격 정보 업데이트와 뉴스 업데이트는 FastAPI와 관리자 화면에서 사용할 수 있도록 구성했습니다.

```text
app/prices/
app/news/
app/api/prices.py
app/api/news.py
```

뉴스는 원문을 그대로 RAG에 넣기보다 **요약해서** `rag_docs/fruit_news_2026.md`에 반영하는 방향으로 구성했습니다.

<br>

## 🤖 로봇 연동 방향

터틀봇이나 로봇팔이 수확/선별 결과를 FastAPI로 전달하면 DB 재고에 반영할 수 있습니다.

```json
{
  "harvested_at": "수확 시각",
  "size_class": "대과 | 중과",
  "quality_grade": "상 | 중 | 하",
  "harvest_count": "수확 개수",
  "estimated_weight_kg": "추정 중량",
  "has_defect": "결함 여부",
  "device_id": "장비 ID"
}
```

현재는 더미 재고와 판매 흐름을 기반으로 MVP를 구성했고, 이후 로봇팔 코드에서 수확 결과를 API로 보내는 방식으로 확장할 수 있습니다.

<br>

## 📌 한 줄 정리

```diff
+ Free   농장 PC/엣지에서 로컬 LLM·로컬 DB로 작동하는 오프라인 자립형 시스템
! Pro    Docker·GPT API로 서버/클라우드에 배포 가능한 재고·판매 관리 시스템
```

<br>

<div align="center">

<sub>🍎 Built for farmers who'd rather be in the orchard than in spreadsheets.</sub>

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:8BC34A,100:2E7D32&height=100&section=footer" />

</div>
