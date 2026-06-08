import os
import re
from datetime import date
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "fruits_data"
OUTPUT_PATH = DATA_DIR / "garak_apple_prices.csv"

GARAKPRICE_URL = "https://www.garakprice.com/pum_detail.php"
DEFAULT_PUM_CD = os.getenv("GARAKPRICE_APPLE_PUM_CD", "41130")
DEFAULT_YEAR = int(os.getenv("GARAKPRICE_YEAR", str(date.today().year)))
DEFAULT_END_MONTH = int(os.getenv("GARAKPRICE_END_MONTH", str(date.today().month)))


def parse_int(value: str) -> int | None:
    digits = re.sub(r"[^0-9]", "", value or "")
    return int(digits) if digits else None


def parse_date(value: str, fallback_year: int) -> pd.Timestamp | None:
    text = value.strip()
    match = re.search(r"(\d{2,4})[./-](\d{1,2})[./-](\d{1,2})", text)
    if not match:
        return None

    year, month, day = match.groups()
    full_year = int(year)
    if full_year < 100:
        full_year += 2000
    if full_year < 2000:
        full_year = fallback_year

    try:
        return pd.Timestamp(year=full_year, month=int(month), day=int(day))
    except ValueError:
        return None


def extract_kg_unit(unit: str) -> float | None:
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:키로|kg)", unit, flags=re.IGNORECASE)
    if not match:
        return None
    return float(match.group(1))


def fetch_month(year: int, month: int, pum_cd: str = DEFAULT_PUM_CD) -> str:
    response = requests.get(
        GARAKPRICE_URL,
        params={"year": year, "month": month, "pum_cd": pum_cd},
        timeout=30,
        headers={"User-Agent": "Mozilla/5.0 fruits-local-llm-price-refresh"},
    )
    response.raise_for_status()
    response.encoding = response.apparent_encoding or response.encoding
    return response.text


def parse_price_rows(html: str, fallback_year: int) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    rows: list[dict] = []

    for table in soup.find_all("table"):
        table_rows = table.find_all("tr")
        if not table_rows:
            continue

        headers: list[str] = []
        for tr in table_rows:
            cells = [cell.get_text(" ", strip=True) for cell in tr.find_all(["th", "td"])]
            if not cells:
                continue

            joined = " ".join(cells)
            if any(label in joined for label in ("일자", "날짜")) and "등급" in joined:
                headers = cells
                continue
            if not headers or len(cells) < len(headers):
                continue

            row = {header: cells[index] for index, header in enumerate(headers)}
            date_text = row.get("일자") or row.get("날짜") or cells[0]
            grade = row.get("등급") or ""
            unit = row.get("단위") or ""
            price_text = row.get("평균가") or row.get("평균") or row.get("가격") or cells[-1]
            market = row.get("시장") or "가락시장"
            item = row.get("품목") or "사과"

            parsed_date = parse_date(date_text, fallback_year)
            price = parse_int(price_text)
            kg_unit = extract_kg_unit(unit)
            if parsed_date is None or price is None or not grade:
                continue

            rows.append(
                {
                    "date": parsed_date.strftime("%Y-%m-%d"),
                    "market": market,
                    "item": item,
                    "grade": grade,
                    "unit": unit,
                    "price": price,
                    "kg_unit": kg_unit,
                    "price_per_kg": round(price / kg_unit) if kg_unit else None,
                    "source": GARAKPRICE_URL,
                }
            )

    if rows:
        return rows

    text_lines = [line.strip() for line in soup.get_text("\n", strip=True).splitlines() if line.strip()]
    try:
        start = text_lines.index("평균가(시세)") + 1
    except ValueError:
        return rows

    index = start
    while index + 3 < len(text_lines):
        date_text, unit, grade, price_text = text_lines[index : index + 4]
        parsed_date = parse_date(date_text, fallback_year)
        price = parse_int(price_text)
        if parsed_date is None:
            index += 1
            continue
        if price is None or grade not in {"특", "상", "중", "하", "보통"}:
            break

        kg_unit = extract_kg_unit(unit)
        rows.append(
            {
                "date": parsed_date.strftime("%Y-%m-%d"),
                "market": "가락시장",
                "item": "사과 미시마",
                "grade": grade,
                "unit": unit,
                "price": price,
                "kg_unit": kg_unit,
                "price_per_kg": round(price / kg_unit) if kg_unit else None,
                "source": GARAKPRICE_URL,
            }
        )
        index += 4

    return rows


def crawl_garak_apple_prices(
    year: int = DEFAULT_YEAR,
    start_month: int = 1,
    end_month: int = DEFAULT_END_MONTH,
    pum_cd: str = DEFAULT_PUM_CD,
) -> pd.DataFrame:
    all_rows: list[dict] = []
    for month in range(start_month, end_month + 1):
        html = fetch_month(year, month, pum_cd)
        all_rows.extend(parse_price_rows(html, year))

    if not all_rows:
        raise ValueError("No apple price rows were parsed from garakprice.com")

    frame = pd.DataFrame(all_rows)
    frame = frame.drop_duplicates(["date", "market", "item", "grade", "unit"])
    frame = frame.sort_values(["date", "grade", "unit"]).reset_index(drop=True)
    return frame


def save_latest_prices(frame: pd.DataFrame, output_path: Path = OUTPUT_PATH) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False, encoding="utf-8-sig")
    return output_path


def crawl_and_save_latest_prices() -> Path:
    frame = crawl_garak_apple_prices()
    return save_latest_prices(frame)
