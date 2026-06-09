# Manage Apple

AI 기반 사과 수확, 선별, 재고, 시세예측, 판매등록, 쇼핑몰 연동을 실험하기 위한 Local LLM + RAG MVP입니다.

관리자 페이지는 **Manage Apple**, 고객용 쇼핑몰은 **Apple Market**으로 구성되어 있습니다.

## 주요 기능

- FastAPI 기반 백엔드
- MariaDB 운영 DB + MariaDB Vector 기반 RAG 저장소
- `rag_docs/` Markdown 문서 chunking, embedding, vector 검색
- Ollama 로컬 Qwen 모델 기반 챗봇 답변 생성
- 최근 대화 요약 및 MariaDB 저장
- 재고 질문에 MariaDB 판매 재고 기반 직접 응답
- 챗봇 명령을 통한 쇼핑몰 판매 등록
- 판매 초안, 승인, 등록상품, 주문, 알림 관리
- Streamlit 관리자 대시보드
- Streamlit 고객용 Apple Market 페이지
- MariaDB 사용자 테이블 기반 로그인
- 가락시장 사과 시세 크롤링
- Chronos mini 기반 30영업일 사과 시세 예측 RAG 문서 갱신

## 기술 스택

- Python
- FastAPI
- MariaDB 11.8+ / MariaDB Vector
- Ollama
- Qwen2.5 7B 또는 Qwen3 8B
- bge-m3 또는 nomic-embed-text
- Streamlit
- Chronos Forecasting
- BeautifulSoup / pandas

## 프로젝트 구조

```text
app/
  main.py
  api/
    chat.py
    prices.py
    sales.py
  db/
    connection.py
    schema.sql
    sales.py
    vector_search.py
  llm/
    ollama_client.py
  prices/
    garak_crawler.py
    refresh.py
  rag/
    embedder.py
    generate_apple_forecast_doc.py
    ingest_docs.py
    prompt_builder.py
    retriever.py
  ui/
    streamlit_app.py
    shop_app.py
    assets/
rag_docs/
fruits_data/
requirements.txt
.env.example
```

## 설치

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

`.env`에서 MariaDB, Ollama, RAG 설정을 확인합니다.

```env
MARIADB_HOST=localhost
MARIADB_PORT=3306
MARIADB_USER=rag_user
MARIADB_PASSWORD=rag_password
MARIADB_DATABASE=fruits_rag

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_CHAT_MODEL=qwen2.5:7b
OLLAMA_EMBEDDING_MODEL=bge-m3

CHAT_API_URL=http://localhost:8000/chat

APP_ADMIN_USERNAME=admin
APP_ADMIN_PASSWORD=admin1234
APP_ADMIN_DISPLAY_NAME=관리자
APP_CUSTOMER_USERNAME=customer
APP_CUSTOMER_PASSWORD=customer1234
APP_CUSTOMER_DISPLAY_NAME=테스트 고객
```

## Ollama 모델

```powershell
ollama pull qwen2.5:7b
ollama pull bge-m3
```

Qwen3 8B를 사용하려면 `.env`의 `OLLAMA_CHAT_MODEL`을 변경합니다.

## MariaDB 설정

MariaDB 11.8 이상이 필요합니다. Vector 타입과 vector index를 사용합니다.

스키마 적용:

```powershell
mariadb --ssl=0 -urag_user -prag_password fruits_rag -e "SOURCE app/db/schema.sql"
```

Windows에서 MariaDB를 직접 실행하는 경우 예시:

```powershell
Start-Process -FilePath "C:\Program Files\MariaDB 12.3\bin\mariadbd.exe" `
  -ArgumentList @("--defaults-file=C:\Program Files\MariaDB 12.3\data\my.ini") `
  -WorkingDirectory "C:\Program Files\MariaDB 12.3\data" `
  -WindowStyle Hidden
```

## RAG 문서

RAG 문서는 `rag_docs/` 폴더의 Markdown 파일을 사용합니다.

문서 임베딩:

```powershell
python -m app.rag.ingest_docs
```

처리 흐름:

```text
rag_docs/*.md
-> chunk 분할
-> Ollama embedding 생성
-> MariaDB rag_documents 테이블 저장
-> 질문 embedding 생성
-> MariaDB Vector 검색
-> 관련 chunk + 질문으로 prompt 구성
-> Ollama Qwen 답변 생성
```

## 사과 시세 예측

현재 가격 갱신 흐름은 다음과 같습니다.

```text
가락시장 가격 페이지
-> app/prices/garak_crawler.py
-> fruits_data/garak_apple_prices.csv
-> app/rag/generate_apple_forecast_doc.py
-> rag_docs/apple_price_forecast_chronos_mini.md
-> RAG 재임베딩
```

가락시장 크롤링 대상 URL:

```text
https://www.garakprice.com/pum_detail.php
```

현재 기본 품목 코드는 `41130`입니다.

가격 RAG 갱신 API:

```powershell
curl -X POST http://localhost:8000/prices/refresh
```

관리자 Streamlit의 `시세갱신` 메뉴에서도 실행할 수 있습니다.

## 실행

FastAPI:

```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

관리자 페이지:

```powershell
python -m streamlit run app/ui/streamlit_app.py --server.address 0.0.0.0 --server.port 8501
```

Apple Market:

```powershell
python -m streamlit run app/ui/shop_app.py --server.address 0.0.0.0 --server.port 8502
```

로컬 접속:

- 관리자 대시보드: http://127.0.0.1:8501
- Apple Market: http://127.0.0.1:8502
- FastAPI 상태: http://127.0.0.1:8000/health

같은 내부망에서 접속하려면 이 PC의 IPv4 주소를 사용합니다.

예시:

- 관리자 대시보드: `http://10.10.16.17:8501`
- Apple Market: `http://10.10.16.17:8502`
- FastAPI 상태: `http://10.10.16.17:8000/health`

외부 PC에서 접속이 안 되면 Windows 방화벽에서 `8000`, `8501`, `8502` 포트를 허용해야 합니다.

## 주요 API

### POST `/auth/login`

관리자 페이지와 Apple Market 로그인에 사용합니다.

기본 계정:

```text
관리자: admin / admin1234
고객: customer / customer1234
```

Request:

```json
{
  "username": "admin",
  "password": "admin1234"
}
```

Response:

```json
{
  "id": 1,
  "username": "admin",
  "display_name": "관리자",
  "role": "admin"
}
```

### POST `/chat`

챗봇 질문을 처리합니다. RAG 검색, 대화 기억, 판매 등록 명령, 재고 직접 응답을 포함합니다.

Request:

```json
{
  "question": "중과 하 재고 알려줘",
  "session_id": null
}
```

Response:

```json
{
  "session_id": 1,
  "answer": "...",
  "sources": [
    {
      "source_path": "rag_docs/sample.md",
      "chunk_index": 0,
      "content": "...",
      "distance": 0.12
    }
  ]
}
```

챗봇 판매 등록 예시:

```text
대과 상 50키로 쇼핑몰에 올려줘
중과 하 20kg 판매 등록해줘
```

### Sales API

```text
GET  /sales/products
GET  /sales/drafts
POST /sales/drafts
PUT  /sales/drafts/{draft_id}
POST /sales/drafts/{draft_id}/approve
POST /sales/drafts/{draft_id}/register
GET  /sales/listings
GET  /sales/orders
GET  /sales/orders/users/{customer_user_id}
POST /sales/listings/{listing_id}/orders
GET  /sales/notifications
POST /sales/notifications/{notification_id}/read
```

### Prices API

```text
GET  /prices/refresh
POST /prices/refresh
```

`POST /prices/refresh`는 가격 크롤링, Chronos 예측 문서 생성, RAG 재임베딩을 순서대로 실행합니다.

## 현재 더미 재고 기준

실제 로봇팔/분류 모델 연동 전까지 `app/db/sales.py`의 `SAMPLE_PRODUCTS`를 기준 재고로 사용합니다.

현재 분류 축:

- 크기: 대과, 중과
- 상품성: 상, 중, 하
- 추정 중량:
  - 대과: 0.32kg/개
  - 중과: 0.24kg/개

쇼핑몰 등록 수량은 기준 재고보다 많이 등록할 수 없도록 검증합니다. 주문이 들어오면 등록상품의 남은 판매 수량이 감소합니다.

## 로봇 연동 예정 방향

로봇팔/분류 모델이 실제로 연결되면 다음 데이터가 필요합니다.

- 수확 이벤트 시간
- 과일 종류
- 크기 분류: 대/중
- 상품성 분류: 상/중/하
- 결함 탐지 결과
- 추정 중량 또는 크기 기반 중량
- 장비 ID 또는 작업 구역

이 이벤트를 FastAPI로 받아 MariaDB 재고 테이블에 누적하면, 관리자 대시보드와 Apple Market 재고가 자동으로 연동될 수 있습니다.

## 주의사항

- 현재 인증/권한 기능은 없습니다. 내부망 데모용으로 사용하세요.
- MariaDB가 꺼져 있으면 `/sales/products` 등 판매 API가 500을 반환할 수 있습니다.
- 가격 크롤링은 외부 사이트 구조 변경에 영향을 받을 수 있습니다.
- Chronos 예측은 확정 가격이 아니라 의사결정 참고값입니다.
- 실제 운영 전에는 판매 승인, 주문 취소, 재고 보정, 인증, 로그 관리가 필요합니다.
