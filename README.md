# All-in-One Fresh Farm

AI 기반 과일 수확, 선별, 재고, 시세 예측, 판매 등록, 쇼핑몰 주문 관리를 통합한 농장 운영 MVP 프로젝트입니다.

농장 운영자가 대시보드에서 재고와 주문을 확인하고, AI 도우미를 통해 판매 등록과 운영 질문을 처리할 수 있도록 구성했습니다. 고객은 별도 Fresh Farm Market 페이지에서 등록된 과일 상품을 확인하고 주문할 수 있습니다.

## 주요 기능

- FastAPI 기반 백엔드 API
- MariaDB 운영 DB
- MariaDB Vector 기반 RAG 검색
- `rag_docs/` Markdown 문서 기반 RAG
- 문서 chunking, embedding 생성, MariaDB 저장
- 사용자 질문 embedding 후 관련 문서 검색
- 검색 문서와 질문을 조합한 프롬프트 생성
- 무료 버전: Ollama 로컬 Qwen 모델 사용
- Pro 버전: OpenAI GPT API 사용
- Streamlit 관리자 대시보드
- Streamlit Apple Market 쇼핑몰 페이지
- 재고, 판매상품, 주문, 구매이력, 알림 관리
- 가격 정보 업데이트, 뉴스 업데이트
- Chronos mini 기반 사과 시세 예측 문서 생성

## 프로젝트 구조

```text
app/                  # 무료/Pro 공용 애플리케이션 코드
  api/                # FastAPI 라우터
  db/                 # DB 연결, 스키마, 판매/인증/메모리 관리
  llm/                # Ollama/OpenAI 호출
  news/               # 과일 뉴스 수집/요약
  prices/             # 가격 데이터 수집
  rag/                # 문서 ingest, embedding, 검색, 프롬프트
  ui/                 # Streamlit 관리자/마켓 UI

rag_docs/             # 무료/Pro 공용 RAG 문서
fruits_data/          # 사과 시세 원본 데이터
reviews/              # 코드 리뷰용 문서

editions/
  free/               # 무료 로컬 버전 설정
    .env.example
    README_FREE.md

  pro/                # Pro 서버/Docker 버전 설정
    .env.pro.example
    Dockerfile
    docker-compose.pro.yml
    requirements-pro.txt
    README_PRO.md

requirements.txt      # 무료 로컬 버전 패키지
README.md             # 전체 프로젝트 설명
```

## 무료 버전과 Pro 버전 차이

무료 버전은 PC 또는 엣지 장비에서 로컬로 실행하는 구조입니다.

```text
Streamlit UI
-> FastAPI
-> MariaDB
-> Ollama Qwen
-> Ollama embedding 모델
```

Pro 버전은 서버나 클라우드 배포를 고려한 구조입니다.

```text
Streamlit UI 컨테이너
-> FastAPI 컨테이너
-> MariaDB 컨테이너
-> OpenAI GPT API
-> OpenAI embedding API
```

현재 Pro 버전도 `rag_docs/`와 `fruits_data/`를 공용으로 사용합니다. Docker 빌드 시 해당 폴더를 컨테이너 안으로 복사하고, API 컨테이너가 시작될 때 `rag_docs/` 문서를 OpenAI embedding으로 MariaDB에 다시 적재합니다.

즉, 문서 소스는 공용이고 AI 처리 방식이 다릅니다.

```text
무료: rag_docs -> Ollama embedding -> MariaDB -> Ollama Qwen 답변
Pro:  rag_docs -> OpenAI embedding -> Docker MariaDB -> GPT API 답변
```

## 무료 로컬 버전 실행

프로젝트 루트에서 실행합니다.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item editions\free\.env.example .env
```

`.env`에서 MariaDB, Ollama, 모델명을 설정합니다.

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

DB 스키마와 RAG 문서를 준비합니다.

```powershell
python -m app.db.init_schema
python -m app.rag.ingest_docs
```

서버와 화면을 실행합니다.

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
python -m streamlit run app/ui/streamlit_app.py --server.port 8501
python -m streamlit run app/ui/shop_app.py --server.port 8502
```

접속 주소:

```text
관리자 대시보드: http://localhost:8501
Apple Market:    http://localhost:8502
FastAPI:         http://localhost:8000/health
```

기본 계정:

```text
관리자: admin / admin1234
고객:   customer / customer1234
```

## Pro Docker 버전 실행

Pro 버전은 Docker Compose로 실행합니다.

```powershell
Copy-Item editions\pro\.env.pro.example editions\pro\.env.pro
```

`editions/pro/.env.pro`에 OpenAI API 키와 DB 비밀번호를 설정합니다.

```env
OPENAI_API_KEY=...
OPENAI_CHAT_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

MARIADB_USER=pro_rag_user
MARIADB_PASSWORD=change-this-password
MARIADB_DATABASE=fruits_rag_pro
MARIADB_ROOT_PASSWORD=change-this-root-password
```

Docker Compose 실행:

```powershell
docker compose --env-file editions/pro/.env.pro -f editions/pro/docker-compose.pro.yml up -d --build
```

상태 확인:

```powershell
docker compose --env-file editions/pro/.env.pro -f editions/pro/docker-compose.pro.yml ps
docker compose --env-file editions/pro/.env.pro -f editions/pro/docker-compose.pro.yml logs -f api
```

접속 주소:

```text
관리자 Pro: http://localhost:8601
Apple Market Pro: http://localhost:8602
FastAPI: http://localhost:8000/health
```

기본 계정:

```text
관리자 Pro: adminpro / adminpro1234
고객 Pro:   customerpro / customerpro1234
```

Docker 종료:

```powershell
docker compose --env-file editions/pro/.env.pro -f editions/pro/docker-compose.pro.yml down
```

## 외부 접속과 배포

현재 PC에서 Docker Desktop으로 실행하면 기본적으로 내 PC가 서버 역할을 합니다.

같은 내부망에서 접속하려면 PC의 내부 IP와 포트를 사용합니다.

```text
http://PC_IP:8601
http://PC_IP:8602
```

학교나 기관망에서는 방화벽 정책 때문에 외부 기기 접속이 막힐 수 있습니다. 이 경우 Cloudflare Tunnel, ngrok, Oracle Cloud 같은 서버 배포 방식이 필요합니다.

클라우드 서버에 올릴 때는 Pro Docker 구성을 그대로 사용할 수 있습니다. 서버 방화벽에서 `8000`, `8601`, `8602` 포트를 열고, 실제 운영에서는 HTTPS와 도메인을 붙이는 것이 좋습니다.

## RAG 문서 관리

RAG 문서는 `rag_docs/` 폴더의 Markdown 파일을 사용합니다.

문서를 추가하거나 수정한 뒤 다시 적재합니다.

```powershell
python -m app.rag.ingest_docs
```

Pro Docker에서는 컨테이너 시작 시 자동으로 문서를 적재합니다.

주의할 점:

- 무료 버전과 Pro 버전은 같은 `rag_docs/`를 사용합니다.
- 무료 버전은 Ollama embedding 차원을 사용합니다.
- Pro 버전은 OpenAI embedding 차원인 `1536`을 사용합니다.
- embedding 차원이 바뀌면 `rag_documents` 테이블을 재생성해야 합니다.

## 가격 정보와 뉴스 업데이트

가격 정보 업데이트와 뉴스 업데이트는 FastAPI와 관리자 화면에서 사용할 수 있도록 구성했습니다.

관련 코드:

```text
app/prices/
app/news/
app/api/prices.py
app/api/news.py
```

뉴스는 원문을 그대로 RAG에 넣기보다 요약해서 `rag_docs/fruit_news_2026.md`에 반영하는 방향으로 구성했습니다.

## 로봇 연동 방향

터틀봇이나 로봇팔이 수확/선별 결과를 FastAPI로 전달하면 DB 재고에 반영할 수 있습니다.

예상 입력 데이터:

```text
수확 시간
사과 크기: 대과 / 중과
품질 등급: 상 / 중 / 하
수확 개수
추정 중량
결함 여부
장비 ID
```

현재는 더미 재고와 판매 흐름을 기반으로 MVP를 구성했고, 이후 로봇팔 코드에서 수확 결과를 API로 보내는 방식으로 확장할 수 있습니다.

## 정리

이 프로젝트는 현재 두 가지 방식으로 설명할 수 있습니다.

무료 버전:

```text
농장 PC 또는 엣지 장비에서 로컬 LLM과 로컬 DB로 작동하는 오프라인 지향 시스템
```

Pro 버전:

```text
Docker와 GPT API를 사용해 서버 또는 클라우드에 배포 가능한 농산물 재고/판매 관리 시스템
```
