import re
import os
from pathlib import Path

os.environ.setdefault("USE_TF", "0")

import pandas as pd
import torch
from bs4 import BeautifulSoup
from chronos import ChronosPipeline

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "fruits_data"
CRAWLED_PRICE_PATH = DATA_DIR / "garak_apple_prices.csv"
OUTPUT_PATH = PROJECT_ROOT / "rag_docs" / "apple_price_forecast_chronos_mini.md"

MODEL_NAME = "amazon/chronos-t5-mini"
PREDICTION_LENGTH = 30
NUM_SAMPLES = 100
FORECAST_GRADE = os.getenv("PRICE_FORECAST_GRADE", "상")


def parse_price(value: str) -> int | None:
    digits = re.sub(r"[^0-9]", "", value)
    return int(digits) if digits else None


def parse_date(value: str) -> pd.Timestamp | None:
    match = re.search(r"(\d{2})\.(\d{2})\.(\d{2})", value)
    if not match:
        return None

    year, month, day = match.groups()
    return pd.Timestamp(year=2000 + int(year), month=int(month), day=int(day))


def load_apple_price_series() -> pd.DataFrame:
    if CRAWLED_PRICE_PATH.exists():
        frame = pd.read_csv(CRAWLED_PRICE_PATH)
        frame["date"] = pd.to_datetime(frame["date"])
        if "price_per_kg" not in frame.columns:
            raise ValueError(f"{CRAWLED_PRICE_PATH} must contain price_per_kg")

        filtered = frame[
            (frame["grade"] == FORECAST_GRADE)
            & frame["price_per_kg"].notna()
        ].copy()
        if filtered.empty:
            raise ValueError(f"No {FORECAST_GRADE} grade price rows found in {CRAWLED_PRICE_PATH}")

        filtered["price"] = filtered["price_per_kg"].round().astype(int)
        filtered["source"] = CRAWLED_PRICE_PATH.name
        return (
            filtered[["date", "price", "source"]]
            .groupby("date", as_index=False)
            .agg({"price": "mean", "source": "first"})
            .assign(price=lambda data: data["price"].round().astype(int))
            .sort_values("date")
            .reset_index(drop=True)
        )

    rows: list[dict] = []
    for path in sorted(DATA_DIR.glob("*.xls")):
        soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="ignore"), "html.parser")
        tables = soup.find_all("table")
        if not tables:
            continue

        for tr in tables[-1].find_all("tr"):
            cells = [cell.get_text(" ", strip=True) for cell in tr.find_all(["th", "td"])]
            if len(cells) < 2 or cells[0] == "날짜":
                continue

            date = parse_date(cells[0])
            price = parse_price(cells[1])
            if date is None or price is None:
                continue

            rows.append({"date": date, "price": price, "source": path.name})

    if not rows:
        raise ValueError(f"No apple price rows found in {DATA_DIR}")

    frame = pd.DataFrame(rows)
    return frame.drop_duplicates("date").sort_values("date").reset_index(drop=True)


def forecast_prices(series: pd.Series) -> pd.DataFrame:
    pipeline = ChronosPipeline.from_pretrained(
        MODEL_NAME,
        device_map="cpu",
        dtype=torch.float32,
    )
    context = torch.tensor(series.to_numpy(dtype="float32"))
    forecast = pipeline.predict(
        context,
        prediction_length=PREDICTION_LENGTH,
        num_samples=NUM_SAMPLES,
    )
    samples = forecast[0]
    quantiles = torch.quantile(samples, torch.tensor([0.1, 0.5, 0.9]), dim=0)

    return pd.DataFrame(
        {
            "forecast_step": range(1, PREDICTION_LENGTH + 1),
            "p10": quantiles[0].round().to(torch.int64).tolist(),
            "median": quantiles[1].round().to(torch.int64).tolist(),
            "p90": quantiles[2].round().to(torch.int64).tolist(),
        }
    )


def business_days_after(last_date: pd.Timestamp, periods: int) -> pd.DatetimeIndex:
    return pd.bdate_range(last_date + pd.Timedelta(days=1), periods=periods)


def trend_label(first_value: int, last_value: int) -> str:
    change_rate = (last_value - first_value) / first_value
    if change_rate >= 0.03:
        return "상승 가능성이 있는 흐름"
    if change_rate <= -0.03:
        return "하락 가능성이 있는 흐름"
    return "큰 방향성보다는 보합권 흐름"


def write_markdown(history: pd.DataFrame, forecast: pd.DataFrame) -> None:
    dates = business_days_after(history["date"].max(), len(forecast))
    forecast = forecast.copy()
    forecast["date"] = dates
    forecast["change_from_latest_percent"] = (
        (forecast["median"] - int(history["price"].iloc[-1]))
        / int(history["price"].iloc[-1])
        * 100
    ).round(2)

    latest_price = int(history["price"].iloc[-1])
    recent_20_mean = int(round(history["price"].tail(20).mean()))
    forecast_mean = int(round(forecast["median"].mean()))
    low_forecast = int(forecast["p10"].min())
    high_forecast = int(forecast["p90"].max())
    label = trend_label(int(forecast["median"].iloc[0]), int(forecast["median"].iloc[-1]))

    rows = "\n".join(
        "| {date} | {median:,} | {p10:,} | {p90:,} | {change:+.2f}% |".format(
            date=row.date.strftime("%Y-%m-%d"),
            median=int(row.median),
            p10=int(row.p10),
            p90=int(row.p90),
            change=float(row.change_from_latest_percent),
        )
        for row in forecast.itertuples(index=False)
    )

    content = f"""# 사과 시세 예측 RAG 문서

## 데이터 개요
- 품목: 사과
- 세부 기준: 가락시장 사과, {FORECAST_GRADE} 등급, kg당 환산 가격
- 원천 파일 위치: `fruits_data/garak_apple_prices.csv` 우선 사용, 없으면 `fruits_data/*.xls`
- 관측 기간: {history['date'].min().strftime('%Y-%m-%d')} ~ {history['date'].max().strftime('%Y-%m-%d')}
- 관측치 수: {len(history):,}개
- 최신 관측 가격: {latest_price:,}원/kg
- 최근 20개 관측 평균: {recent_20_mean:,}원/kg

## 예측 설정
- 예측 모델: Chronos mini (`{MODEL_NAME}`)
- 실행 방식: 로컬 CPU 추론
- 예측 범위: 최신 관측일 이후 30영업일
- 예측값 의미: 중앙값은 기본 예상 시세, p10은 낮은 경우, p90은 높은 경우의 참고 범위
- 주의: 이 예측은 과거 소매가격 흐름만 사용한 시계열 예측이며, 날씨, 작황, 명절 수요, 산지 출하량, 도매시장 수급, 재고 정보는 직접 반영하지 않았다.

## 예측 요약
- 30영업일 중앙값 평균: {forecast_mean:,}원/kg
- 예측 참고 범위: {low_forecast:,}원/kg ~ {high_forecast:,}원/kg
- 전체 흐름 판단: {label}
- 판매 판단에 사용할 때는 최신 실제 시세, 재고량, 납품처 주문량과 함께 확인하는 것이 좋다.

## 30영업일 예측표
| 예측일 | 중앙값 예상가(원/kg) | 낮은 경우 p10 | 높은 경우 p90 | 최신가 대비 |
|---|---:|---:|---:|---:|
{rows}

## 챗봇 답변 기준
- 사용자가 사과 시세 전망을 물으면 중앙값 예상가를 우선 안내한다.
- 사용자가 판매 시점을 물으면 예측 흐름뿐 아니라 재고 상태, 납품 일정, 품질 저하 가능성을 함께 고려해 답한다.
- 예측값은 확정 가격이 아니라 의사결정을 돕는 참고값으로 설명한다.
- kg당 가격 질문에는 이 문서의 kg당 환산 가격을 우선 사용한다.
"""
    OUTPUT_PATH.write_text(content, encoding="utf-8")


def main() -> None:
    history = load_apple_price_series()
    forecast = forecast_prices(history["price"])
    write_markdown(history, forecast)
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
