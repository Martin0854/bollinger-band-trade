"""
yfinance를 사용해서 실제 한국 주식 데이터 가져오기
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, date

def fetch_korean_stock_data(stock_code, start_date, end_date):
    """
    Yahoo Finance에서 한국 주식 데이터 가져오기

    Args:
        stock_code: 6자리 종목 코드 (예: "005930")
        start_date: 시작일 (datetime.date 또는 str)
        end_date: 종료일 (datetime.date 또는 str)

    Returns:
        pandas.DataFrame: OHLCV 데이터
    """
    # 한국 주식은 .KS (KOSPI) 또는 .KQ (KOSDAQ) 접미사 필요
    # 대부분의 대형주는 KOSPI이므로 .KS 사용
    ticker = f"{stock_code}.KS"

    print(f"📥 {stock_code} 데이터 다운로드 중...")
    print(f"   기간: {start_date} ~ {end_date}")

    try:
        # Yahoo Finance에서 데이터 다운로드
        df = yf.download(
            ticker,
            start=start_date,
            end=end_date,
            progress=False  # 진행바 숨기기
        )

        if df.empty:
            # KOSPI에 없으면 KOSDAQ 시도
            ticker = f"{stock_code}.KQ"
            print(f"   KOSPI에 없음. KOSDAQ 시도: {ticker}")
            df = yf.download(
                ticker,
                start=start_date,
                end=end_date,
                progress=False
            )

        if df.empty:
            raise ValueError(f"종목 {stock_code}의 데이터를 찾을 수 없습니다.")

        # 컬럼명을 영어로 정리
        df.columns = df.columns.get_level_values(0)  # MultiIndex 제거

        # 필요한 컬럼만 선택
        result = pd.DataFrame({
            'Open': df['Open'],
            'High': df['High'],
            'Low': df['Low'],
            'Close': df['Close'],
            'Volume': df['Volume']
        })

        # 결측치 제거
        result = result.dropna()

        print(f"   ✅ {len(result)}일 데이터 다운로드 완료")
        print(f"   기간: {result.index[0].strftime('%Y-%m-%d')} ~ {result.index[-1].strftime('%Y-%m-%d')}")
        print(f"   평균 종가: ₩{result['Close'].mean():,.0f}")

        return result

    except Exception as e:
        print(f"   ❌ 오류 발생: {str(e)}")
        raise


def get_stock_info(stock_code):
    """종목 정보 가져오기"""
    ticker = f"{stock_code}.KS"
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        print(f"\n📊 종목 정보: {stock_code}")
        print(f"   이름: {info.get('longName', 'N/A')}")
        print(f"   업종: {info.get('sector', 'N/A')}")
        print(f"   시가총액: {info.get('marketCap', 0):,}")
        print(f"   현재가: ₩{info.get('currentPrice', 0):,}")

    except Exception as e:
        print(f"종목 정보를 가져올 수 없습니다: {e}")


# 예제 사용법
if __name__ == "__main__":
    # 1. 삼성전자 데이터 가져오기
    samsung_data = fetch_korean_stock_data(
        stock_code="005930",  # 삼성전자
        start_date="2024-01-01",
        end_date="2024-12-31"
    )

    print("\n" + "="*70)
    print("📈 데이터 미리보기 (최근 5일)")
    print("="*70)
    print(samsung_data.tail())

    # 2. 종목 정보 확인
    get_stock_info("005930")

    # 3. 여러 종목 한번에 가져오기
    print("\n" + "="*70)
    print("📦 여러 종목 데이터 가져오기")
    print("="*70)

    stocks = {
        "005930": "삼성전자",
        "035720": "카카오",
        "000660": "SK하이닉스"
    }

    all_data = {}
    for code, name in stocks.items():
        try:
            data = fetch_korean_stock_data(code, "2024-01-01", "2024-12-31")
            all_data[code] = data
            print(f"✅ {name} ({code}): {len(data)}일")
        except Exception as e:
            print(f"❌ {name} ({code}): {str(e)}")

    print(f"\n총 {len(all_data)}개 종목 데이터 준비 완료!")
