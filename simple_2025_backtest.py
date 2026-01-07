"""
Simple 2025 KOSPI Top 100 Bollinger Band Strategy Analysis
Basic implementation without complex dependencies
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, date
from typing import Dict, List, Optional
import warnings
warnings.filterwarnings('ignore')


def load_kospi_top100(filepath: str = "kospi_top100.txt") -> List[str]:
    """KOSPI Top 100 종목 리스트 로드"""
    with open(filepath, 'r') as f:
        stocks = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return [s for s in stocks if s][:100]


def fetch_stock_data(stock_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
    """Yahoo Finance에서 한국 주식 데이터 가져오기"""
    ticker = f"{stock_code}.KS"

    try:
        df = yf.download(ticker, start=start_date, end=end_date, progress=False, auto_adjust=False)

        if df.empty:
            ticker = f"{stock_code}.KQ"
            df = yf.download(ticker, start=start_date, end=end_date, progress=False, auto_adjust=False)

        if df.empty:
            return None

        # Handle MultiIndex columns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        result = pd.DataFrame({
            'Open': df['Open'],
            'High': df['High'],
            'Low': df['Low'],
            'Close': df['Close'],
            'Volume': df['Volume'],
            'Adj Close': df['Adj Close']
        }).dropna()

        return result if len(result) >= 10 else None  # At least 10 days

    except Exception:
        return None


def calculate_bollinger_bands(prices: pd.Series, window: int = 20, std_dev: float = 2.0) -> pd.DataFrame:
    """볼린저 밴드 계산"""
    sma = prices.rolling(window=window).mean()
    std = prices.rolling(window=window).std()

    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)

    return pd.DataFrame({
        'SMA': sma,
        'Upper': upper,
        'Lower': lower,
        'BandWidth': (upper - lower) / sma * 100
    })


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """RSI 계산"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """MACD 계산"""
    exp1 = prices.ewm(span=fast).mean()
    exp2 = prices.ewm(span=slow).mean()
    macd_line = exp1 - exp2
    signal_line = macd_line.ewm(span=signal).mean()
    histogram = macd_line - signal_line

    return pd.DataFrame({
        'MACD': macd_line,
        'Signal': signal_line,
        'Histogram': histogram
    })


def calculate_volume_filter(volume: pd.Series, window: int = 20, multiplier: float = 1.5) -> pd.Series:
    """거래량 필터 계산"""
    avg_volume = volume.rolling(window=window).mean()
    return volume >= (avg_volume * multiplier)


def simple_bollinger_strategy(data: pd.DataFrame) -> pd.DataFrame:
    """간단한 볼린저 밴드 전략 구현"""
    # 기술지표 계산
    bb = calculate_bollinger_bands(data['Close'])
    data['RSI'] = calculate_rsi(data['Close'])
    macd_data = calculate_macd(data['Close'])
    data['MACD'] = macd_data['MACD']
    data['MACD_Signal'] = macd_data['Signal']
    data['Volume_Filter'] = calculate_volume_filter(data['Volume'])

    # 볼린저 밴드 추가
    data['BB_Upper'] = bb['Upper']
    data['BB_Lower'] = bb['Lower']
    data['BB_SMA'] = bb['SMA']
    data['BandWidth'] = bb['BandWidth']

    # Squeeze 감지 (간단히 밴드폭이 평균 대비 낮은 수준)
    data['BandWidth_MA'] = data['BandWidth'].rolling(window=10).mean()
    data['Squeeze'] = data['BandWidth'] < (data['BandWidth_MA'] * 0.7)

    # 신호 생성
    signals = []
    positions = []
    current_position = 0

    for i in range(len(data)):
        signal = 'HOLD'

        if i < 30:  # 충분한 데이터가 필요
            signals.append(signal)
            positions.append(current_position)
            continue

        # 매수 신호 조건
        if (current_position == 0 and
            data.iloc[i]['Close'] > data.iloc[i]['BB_Upper'] and  # 상단 밴드 돌파
            data.iloc[i]['Volume_Filter'] and  # 거래량 급증
            30 <= data.iloc[i]['RSI'] <= 70 and  # RSI 중립구간
            data.iloc[i]['MACD'] > data.iloc[i]['MACD_Signal']):  # MACD 골든크로스

            signal = 'BUY'
            current_position = 1

        # 매도 신호 조건
        elif (current_position == 1 and
              (data.iloc[i]['Close'] < data.iloc[i]['BB_Lower'] or  # 하단 밴드 터치
               data.iloc[i]['Close'] < data.iloc[i-1]['Close'] * 0.95)):  # 5% 손절

            signal = 'SELL'
            current_position = 0

        signals.append(signal)
        positions.append(current_position)

    data['Signal'] = signals
    data['Position'] = positions

    return data


def calculate_performance(data: pd.DataFrame) -> Dict:
    """성과 계산"""
    # 거래 신호 찾기
    buy_signals = data[data['Signal'] == 'BUY']
    sell_signals = data[data['Signal'] == 'SELL']

    if len(buy_signals) == 0:
        return {
            'trades': 0,
            'total_return': 0,
            'win_rate': 0,
            'avg_return_per_trade': 0,
            'max_drawdown': 0
        }

    # 매수/매도 페어 생성
    trades = []
    buy_prices = []
    buy_dates = []

    for _, buy_row in buy_signals.iterrows():
        buy_prices.append(buy_row['Close'])
        buy_dates.append(buy_row.name)

        # 해당 매수 이후 첫 매도 신호 찾기
        future_sells = sell_signals[sell_signals.index > buy_row.name]
        if len(future_sells) > 0:
            sell_row = future_sells.iloc[0]
            return_pct = (sell_row['Close'] - buy_row['Close']) / buy_row['Close'] * 100
            trades.append(return_pct)

    if not trades:
        return {
            'trades': 0,
            'total_return': 0,
            'win_rate': 0,
            'avg_return_per_trade': 0,
            'max_drawdown': 0
        }

    # 성과 지표 계산
    total_return = sum(trades)
    win_rate = len([t for t in trades if t > 0]) / len(trades) * 100
    avg_return = np.mean(trades)

    # 간단한 최대 낙폭 계산 (누적 수익률 기준)
    cumulative_returns = np.cumsum(trades)
    running_max = np.maximum.accumulate(cumulative_returns)
    drawdowns = cumulative_returns - running_max
    max_drawdown = abs(min(drawdowns)) if len(drawdowns) > 0 else 0

    return {
        'trades': len(trades),
        'total_return': total_return,
        'win_rate': win_rate,
        'avg_return_per_trade': avg_return,
        'max_drawdown': max_drawdown,
        'trade_returns': trades
    }


def run_2025_analysis():
    """2025년 KOSPI Top 100 분석 실행"""
    print("="*80)
    print("🎯 2025 KOSPI Top 100 Bollinger Band Strategy Analysis")
    print("="*80)

    # 설정
    start_date = "2025-01-01"
    end_date = date.today().strftime('%Y-%m-%d')

    print(f"\n📅 분석 기간: {start_date} ~ {end_date}")

    # KOSPI Top 100 로드
    print("\n[1] KOSPI Top 100 종목 로드...")
    kospi_stocks = load_kospi_top100()
    print(f"✓ {len(kospi_stocks)}개 종목")

    # 데이터 수집 및 분석
    print(f"\n[2] 데이터 수집 및 전략 적용...")
    results = []
    successful_stocks = []
    failed_stocks = []

    for i, stock_code in enumerate(kospi_stocks):
        print(f"진행: {i+1}/{len(kospi_stocks)} ({stock_code})", end=" ")

        # 데이터 가져오기
        data = fetch_stock_data(stock_code, start_date, end_date)

        if data is not None and len(data) >= 15:  # 최소 15일 필요
            # 전략 적용
            strategy_data = simple_bollinger_strategy(data)
            performance = calculate_performance(strategy_data)

            if performance['trades'] > 0:
                results.append({
                    'stock_code': stock_code,
                    'data_points': len(data),
                    **performance
                })
                successful_stocks.append(stock_code)
                print("✓")
            else:
                print("○ (no signals)")
        else:
            failed_stocks.append(stock_code)
            print("✗")

    print(f"\n✅ 분석 완료: {len(successful_stocks)}개 종목에서 거래 신호 발생")
    print(f"❌ 실패/신호없음: {len(failed_stocks)}개 종목")

    if not results:
        print("⚠️ 분석할 수 있는 거래가 없습니다.")
        return

    # 통합 결과 계산
    print(f"\n[3] 결과 분석...")

    total_trades = sum([r['trades'] for r in results])
    all_returns = []
    for r in results:
        all_returns.extend(r['trade_returns'])

    avg_total_return = np.mean([r['total_return'] for r in results])
    avg_win_rate = np.mean([r['win_rate'] for r in results])
    overall_win_rate = len([r for r in all_returns if r > 0]) / len(all_returns) * 100 if all_returns else 0

    # 결과 출력
    print("\n" + "="*80)
    print("📊 2025년 KOSPI Top 100 백테스트 결과")
    print("="*80)

    print(f"\n📋 기본 정보:")
    print(f"  분석 기간:            {start_date} ~ {end_date}")
    print(f"  분석 종목:            KOSPI Top 100 ({len(kospi_stocks)}개)")
    print(f"  성공 종목:            {len(successful_stocks)}개")
    print(f"  신호 발생 종목:       {len(results)}개")
    print(f"  전략:                Volume + RSI + MACD + Bollinger Bands")

    print(f"\n📈 거래 통계:")
    print(f"  총 거래 수:           {total_trades}건")
    print(f"  종목별 평균 거래:     {total_trades/len(results):.1f}건")
    print(f"  전체 승률:            {overall_win_rate:.1f}%")
    print(f"  종목별 평균 승률:     {avg_win_rate:.1f}%")

    print(f"\n💰 수익성 지표:")
    status = "🟢" if avg_total_return > 0 else "🔴"
    print(f"  평균 종목 수익률:     {status} {avg_total_return:+.2f}%")
    print(f"  거래당 평균 수익:     {np.mean(all_returns):+.2f}%")

    if all_returns:
        print(f"  최고 거래 수익:       {max(all_returns):+.2f}%")
        print(f"  최악 거래 수익:       {min(all_returns):+.2f}%")

    # 상위 성과 종목
    top_performers = sorted(results, key=lambda x: x['total_return'], reverse=True)[:10]

    print(f"\n🌟 상위 10개 종목:")
    print("┌──────────┬──────────┬──────────┬──────────┬──────────┐")
    print("│ 종목코드 │ 총수익률 │  거래수  │  승률    │ 거래수익 │")
    print("├──────────┼──────────┼──────────┼──────────┼──────────┤")

    for performer in top_performers:
        status_emoji = "🟢" if performer['total_return'] > 0 else "🔴"
        print(f"│ {performer['stock_code']:8s} │ {status_emoji}{performer['total_return']:7.2f}% │ {performer['trades']:6d}건 │ {performer['win_rate']:7.1f}% │ {performer['avg_return_per_trade']:7.2f}% │")

    print("└──────────┴──────────┴──────────┴──────────┴──────────┘")

    # 성과 평가
    print(f"\n🎯 전략 평가:")

    if avg_total_return > 5:
        evaluation = "🌟 우수 (>5%)"
    elif avg_total_return > 2:
        evaluation = "✅ 양호 (2-5%)"
    elif avg_total_return > 0:
        evaluation = "⚡ 보통 (0-2%)"
    elif avg_total_return > -2:
        evaluation = "⚠️ 부진 (0~-2%)"
    else:
        evaluation = "🔥 손실 (<-2%)"

    print(f"  종합 평가:            {evaluation}")

    if overall_win_rate > 60:
        consistency = "🛡️ 높은 일관성 (>60% 승률)"
    elif overall_win_rate > 50:
        consistency = "✅ 보통 일관성 (50-60% 승률)"
    else:
        consistency = "⚠️ 낮은 일관성 (<50% 승률)"

    print(f"  일관성 평가:          {consistency}")

    # 추가 인사이트
    print(f"\n💡 주요 인사이트:")
    profitable_stocks = len([r for r in results if r['total_return'] > 0])
    print(f"  수익 종목 비율:       {profitable_stocks}/{len(results)} ({profitable_stocks/len(results)*100:.1f}%)")

    high_trade_stocks = len([r for r in results if r['trades'] >= 3])
    print(f"  활발한 거래 종목:     {high_trade_stocks}개 (3건 이상)")

    if failed_stocks:
        print(f"  데이터 부족 종목:     {len(failed_stocks)}개")
        print(f"  (예시: {failed_stocks[:5]})")


if __name__ == "__main__":
    run_2025_analysis()

    print(f"\n" + "="*80)
    print("✅ 2025 KOSPI Top 100 분석 완료")
    print("="*80)