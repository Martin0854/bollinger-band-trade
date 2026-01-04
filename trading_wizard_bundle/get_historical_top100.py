#!/usr/bin/env python
"""
2025년 1월 초 기준 KOSPI 시가총액 Top 100 목록 생성

yfinance를 사용하여 역사적 시가총액을 계산합니다.
"""

import json
import yfinance as yf
import pandas as pd
from datetime import datetime
from pathlib import Path

# 주요 KOSPI 종목 리스트 (150개 이상의 대형/중형주)
# 현재 Top 100 + 추가 후보군
KOSPI_CANDIDATES = [
    # 현재 Top 100 (2026-01-04 기준)
    "005930", "000660", "207940", "373220", "005380", "105560", "000270", "068270",
    "012450", "034020", "035420", "055550", "329180", "028260", "012330", "086790",
    "011200", "035720", "032830", "005490", "015760", "402340", "042660", "009540",
    "138040", "000810", "064350", "051910", "316140", "024110", "096770", "267260",
    "010130", "259960", "033780", "010140", "323410", "018260", "006400", "030200",
    "066570", "079550", "003550", "034730", "017670", "352820", "006800", "086280",
    "003670", "003230", "009150", "272210", "267250", "003490", "377300", "298040",
    "071050", "000150", "047050", "005830", "090430", "042700", "000100", "047810",
    "180640", "005940", "000720", "010120", "021240", "326030", "010950", "000880",
    "016360", "010620", "032640", "029780", "039490", "009830", "011070", "028050",
    "097950", "036570", "051900", "004020", "271560", "161390", "001450", "004170",
    "078930", "036460", "011780", "006260", "001040", "069960", "007070", "088350",
    "004370", "282330", "138930", "241560",
    # 추가 후보군 (2024년에 Top 100이었을 가능성이 있는 종목들)
    "035250",  # 강원랜드
    "009240",  # 한샘
    "000120",  # CJ대한통운
    "051600",  # 한전KPS
    "139480",  # 이마트
    "004990",  # 롯데지주
    "002790",  # 아모레G
    "011170",  # 롯데케미칼
    "018880",  # 한온시스템
    "092780",  # 동양생명
    "093050",  # LF
    "002380",  # KCC
    "034220",  # LG디스플레이
    "012630",  # HDC
    "023530",  # 롯데쇼핑
    "002270",  # 롯데삼강
    "001740",  # SK네트웍스
    "001430",  # 세아베스틸
    "006360",  # GS건설
    "000210",  # 대림산업(DL)
    "088980",  # 맥쿼리인프라
    "016380",  # KG동부제철
    "001800",  # 오리온홀딩스
    "005300",  # 롯데칠성
    "000080",  # 하이트진로
    "117930",  # 한진
    "003620",  # 쌍용C&E
    "000990",  # DB하이텍
    "001680",  # 대상
    "000240",  # 한국타이어&테크놀로지 (duplicate check)
    "192820",  # 코스맥스
    "383220",  # F&F
    "003410",  # 쌍용C&E
    "000670",  # 영풍
    "069620",  # 대웅제약
    "000640",  # 동아쏘시오홀딩스
    "004000",  # 롯데정밀화학
    "002710",  # TCC스틸
    "002350",  # 넥센타이어
    "008770",  # 호텔신라
    "003830",  # 대한화섬
    "008560",  # 메리츠종금증권
]

# 중복 제거
KOSPI_CANDIDATES = list(set(KOSPI_CANDIDATES))


def get_market_cap_on_date(stock_code: str, year: int) -> tuple:
    """
    특정 연도 1월 초의 시가총액을 계산합니다.

    Returns:
        tuple: (stock_code, market_cap, stock_name, close_price)
    """
    ticker_symbol = f"{stock_code}.KS"

    try:
        ticker = yf.Ticker(ticker_symbol)

        # 주식 정보 가져오기
        info = ticker.info
        shares_outstanding = info.get("sharesOutstanding", 0)
        stock_name = info.get("shortName", stock_code)

        if not shares_outstanding:
            return None

        # 해당 연도 1월 초의 종가 가져오기
        start_date = f"{year}-01-02"
        end_date = f"{year}-01-15"
        hist = ticker.history(start=start_date, end=end_date)
        if hist.empty:
            return None

        # 첫 번째 거래일 종가 사용
        close_price = hist["Close"].iloc[0]
        market_cap = close_price * shares_outstanding

        return (stock_code, market_cap, stock_name, close_price)

    except Exception as e:
        return None


def main(year: int = 2025):
    print("=" * 70)
    print(f"{year}년 1월 초 기준 KOSPI 시가총액 Top 100 계산")
    print("=" * 70)

    results = []
    total = len(KOSPI_CANDIDATES)

    print(f"\n총 {total}개 종목 분석 중...\n")

    for i, code in enumerate(KOSPI_CANDIDATES, 1):
        print(f"\r분석 중: {i}/{total} - {code}    ", end="")
        result = get_market_cap_on_date(code, year)
        if result:
            results.append(result)

    print(f"\n\n분석 완료: {len(results)}개 종목")

    # 시가총액 기준 정렬
    results.sort(key=lambda x: x[1], reverse=True)

    # Top 100 추출
    top100 = results[:100]

    print("\n" + "=" * 70)
    print(f"{year}년 1월 초 KOSPI 시가총액 Top 100")
    print("=" * 70)

    print(f"\n{'순위':>4} {'종목코드':<8} {'종목명':<20} {'시가총액(조)':>12}")
    print("-" * 50)

    for i, (code, mcap, name, price) in enumerate(top100[:30], 1):
        mcap_trillion = mcap / 1e12
        print(f"{i:>4} {code:<8} {name[:18]:<20} {mcap_trillion:>10.2f}조")

    print("...")
    print(f"\n... 총 {len(top100)}개 종목")

    # 파일로 저장
    output_file = f"kospi_top100_{year}jan.txt"
    with open(output_file, "w") as f:
        for code, mcap, name, price in top100:
            f.write(f"{code}\n")

    print(f"\n저장 완료: {output_file}")
    return output_file


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="연도별 KOSPI Top 100 생성")
    parser.add_argument("--year", type=int, default=2025, help="대상 연도")
    args = parser.parse_args()
    main(args.year)
