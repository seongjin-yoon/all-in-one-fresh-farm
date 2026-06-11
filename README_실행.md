# 실행 절차

이 문서는 Codex 없이 직접 무료 버전과 프로 버전을 실행하는 방법을 정리한 문서입니다.

## 1. 무료 버전 실행

무료 버전은 로컬 Python, 로컬 MariaDB, Ollama를 사용합니다.

### 1-1. MariaDB 실행

PowerShell에서 아래 명령을 실행합니다.

```powershell
Start-Process -FilePath "C:\Program Files\MariaDB 12.3\bin\mariadbd.exe" -ArgumentList @("--defaults-file=C:\Program Files\MariaDB 12.3\data\my.ini") -WorkingDirectory "C:\Program Files\MariaDB 12.3\data" -WindowStyle Hidden
```

### 1-2. 프로젝트 폴더로 이동

```powershell
cd C:\Users\kccistc1\Documents\fruits_local_LLM
```

### 1-3. 무료 FastAPI 서버 실행

PowerShell 창 하나를 열고 아래 명령을 실행합니다.

```powershell
$env:APP_ENV_FILE=".env"
$env:CHAT_API_URL="http://localhost:8001/chat"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

### 1-4. 무료 관리자 페이지 실행

새 PowerShell 창을 열고 아래 명령을 실행합니다.

```powershell
cd C:\Users\kccistc1\Documents\fruits_local_LLM
$env:APP_ENV_FILE=".env"
$env:APP_EDITION="free"
$env:CHAT_API_URL="http://localhost:8001/chat"
python -m streamlit run app/ui/streamlit_app.py --server.address 127.0.0.1 --server.port 8501
```

### 1-5. 무료 쇼핑몰 페이지 실행

새 PowerShell 창을 열고 아래 명령을 실행합니다.

```powershell
cd C:\Users\kccistc1\Documents\fruits_local_LLM
$env:APP_ENV_FILE=".env"
$env:SHOP_EDITION="free"
$env:CHAT_API_URL="http://localhost:8001/chat"
python -m streamlit run app/ui/shop_app.py --server.address 127.0.0.1 --server.port 8502
```

### 1-6. 접속 주소

- 무료 관리자: http://127.0.0.1:8501
- 무료 쇼핑몰: http://127.0.0.1:8502
- 무료 API 상태 확인: http://127.0.0.1:8001/health

## 2. 프로 버전 실행

프로 버전은 Docker Desktop, Docker 내부 MariaDB, OpenAI API를 사용합니다.

### 2-1. Docker Desktop 실행

Windows에서 Docker Desktop을 먼저 실행합니다.

Docker 명령이 권한 문제로 실패하면 Docker Desktop을 관리자 권한으로 실행하거나, Windows 계정이 `docker-users` 그룹에 포함되어 있는지 확인합니다.

### 2-2. 프로젝트 폴더로 이동

```powershell
cd C:\Users\kccistc1\Documents\fruits_local_LLM
```

### 2-3. 프로 컨테이너 실행

```powershell
docker compose --env-file editions/pro/.env.pro -f editions/pro/docker-compose.pro.yml up -d --build
```

### 2-4. 접속 주소

- 프로 관리자: http://127.0.0.1:8601
- 프로 쇼핑몰: http://127.0.0.1:8602
- 프로 API 상태 확인: http://127.0.0.1:8000/health

## 3. 재고 더미데이터 초기화

재고를 새 FIFO 구조의 사과 1개 단위 더미데이터로 다시 채우고 싶을 때만 실행합니다.

주의: 아래 명령은 판매등록, 주문, 수확 이벤트, 사과 원장 데이터를 초기화합니다.

### 3-1. 무료 DB 재고 초기화

```powershell
cd C:\Users\kccistc1\Documents\fruits_local_LLM
$env:APP_ENV_FILE=".env"
python -c "from app.db.sales import reset_demo_inventory_data; print(reset_demo_inventory_data())"
```

### 3-2. 프로 DB 재고 초기화

```powershell
cd C:\Users\kccistc1\Documents\fruits_local_LLM
docker compose --env-file editions/pro/.env.pro -f editions/pro/docker-compose.pro.yml exec -T api python -c "from app.db.sales import reset_demo_inventory_data; print(reset_demo_inventory_data())"
```

정상 실행되면 아래와 비슷한 결과가 출력됩니다.

```text
{'inventory_rows': 6, 'item_count': 12905, 'total_weight_kg': 3509.68}
```

## 4. 서버 종료

### 4-1. 무료 버전 종료

무료 버전은 실행 중인 PowerShell 창에서 `Ctrl + C`를 누르면 종료됩니다.

백그라운드로 실행한 경우 아래 포트의 프로세스를 종료합니다.

```powershell
$ports = @(8001, 8501, 8502)
foreach ($port in $ports) {
    $conn = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($conn) {
        Stop-Process -Id $conn.OwningProcess -Force
    }
}
```

### 4-2. 프로 버전 종료

```powershell
cd C:\Users\kccistc1\Documents\fruits_local_LLM
docker compose --env-file editions/pro/.env.pro -f editions/pro/docker-compose.pro.yml down
```

## 5. 무료와 프로의 DB 구조

무료와 프로는 같은 DB를 공유하지 않습니다.

### 무료 버전 DB

- 로컬 MariaDB 사용
- 설정 파일: `.env`
- 기본 DB 이름: `fruits_rag`
- 기본 접속 위치: `localhost:3306`
- LLM: Ollama Qwen
- Embedding: Ollama bge-m3

### 프로 버전 DB

- Docker Compose 내부 MariaDB 컨테이너 사용
- 설정 파일: `editions/pro/.env.pro`
- 기본 DB 이름: `fruits_rag_pro`
- 컨테이너 내부 접속 위치: `mariadb:3306`
- LLM: OpenAI GPT
- Embedding: OpenAI embedding

현재 구조에서는 무료와 프로의 `user_id`, `listing_id`, `order_id`, `apple_items.id`가 서로 독립적으로 생성됩니다.

즉, 두 버전은 ID 기준으로 같은 DB에서 통합 관리되는 구조가 아니라, 각각 분리된 DB에서 따로 관리되는 구조입니다.

