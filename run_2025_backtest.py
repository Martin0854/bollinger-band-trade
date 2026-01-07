"""
2025 KOSPI Top 100 Bollinger Band Strategy Backtest
Based on Phase 3: Volume + RSI + MACD + Confidence Scoring
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import yfinance as yf
import pandas as pd
from datetime import datetime, date
from typing import Dict, Optional
from src.models.config import BacktestConfiguration
from src.backtest.engine import BacktestEngine


def fetch_stock_data(stock_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
    """Yahoo Finance에서 한국 주식 데이터 가져오기"""
    ticker = f"{stock_code}.KS"

    try:
        df = yf.download(ticker, start=start_date, end=end_date, progress=False)

        if df.empty:
            ticker = f"{stock_code}.KQ"
            df = yf.download(ticker, start=start_date, end=end_date, progress=False)

        if df.empty:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        result = pd.DataFrame({
            'Open': df['Open'],
            'High': df['High'],
            'Low': df['Low'],
            'Close': df['Close'],
            'Volume': df['Volume']
        }).dropna()

        return result if len(result) >= 50 else None  # At least 50 days of data

    except Exception as e:
        print(f"Error fetching {stock_code}: {e}")
        return None


def load_kospi_top100(filepath: str = "kospi_top100.txt") -> list:
    """KOSPI Top 100 종목 리스트 로드"""
    with open(filepath, 'r') as f:
        stocks = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return [s for s in stocks if s][:100]  # Remove empty lines and limit to 100


def run_2025_backtest(kospi_stocks: list, period: str = "2025") -> dict:
    """2025년 백테스트 실행"""
    print(f"\n{'='*80}")
    print(f"📅 {period} KOSPI Top 100 백테스트 (Phase 3: MACD + Confidence Scoring)")
    print(f"{'='*80}")

    # 2025년 기간 설정 - 현재 사용 가능한 데이터까지
    current_date = date.today().strftime('%Y-%m-%d')
    if period == "2025":
        start_date = "2025-01-01"
        end_date = min(current_date, "2025-12-31")
    else:
        start_date = f"{period}-01-01"
        end_date = f"{period}-12-31"

    print(f"📊 백테스트 기간: {start_date} ~ {end_date}")

    # 설정 로드 및 수정
    config = BacktestConfiguration.from_yaml("runs/configs/phases/phase3_confidence.yaml")
    config.stocks = kospi_stocks
    config.seed_money = 100_000_000  # 1억원
    config.max_positions = 15
    config.date_range = (start_date, end_date)

    # 데이터 다운로드
    print(f"\n📈 데이터 다운로드 중... ", end="", flush=True)
    engine = BacktestEngine(config=config)
    loaded_count = 0
    failed_stocks = []

    for i, stock_code in enumerate(kospi_stocks):
        if i % 20 == 0:
            print(f"\n진행률: {i}/{len(kospi_stocks)} ({i/len(kospi_stocks)*100:.1f}%) ", end="", flush=True)

        data = fetch_stock_data(stock_code, start_date, end_date)
        if data is not None and len(data) > 0:
            engine.load_mock_data(stock_code, data)
            loaded_count += 1
            print("✓", end="", flush=True)
        else:
            failed_stocks.append(stock_code)
            print("✗", end="", flush=True)

    print(f"\n✅ 성공: {loaded_count}개 종목 로드")
    if failed_stocks:
        print(f"❌ 실패: {len(failed_stocks)}개 종목 ({failed_stocks[:10]}{'...' if len(failed_stocks) > 10 else ''})")

    if loaded_count == 0:
        print("⚠️ 로드된 데이터가 없습니다.")
        return None

    # 백테스트 실행
    print(f"🚀 백테스트 실행 중... ", end="", flush=True)
    try:
        report = engine.run()
        print("✅ 완료")
    except Exception as e:
        print(f"❌ 실행 실패: {e}")
        return None

    # 결과 요약
    completed_trades = report.num_trades // 2 if report.num_trades > 0 else 0

    return {
        'period': period,
        'start_date': start_date,
        'end_date': end_date,
        'stocks_loaded': loaded_count,
        'stocks_failed': len(failed_stocks),
        'total_return': report.total_return_pct,
        'cagr': report.cagr_pct,
        'win_rate': report.win_rate_pct,
        'sharpe': report.sharpe_ratio,
        'mdd': report.max_drawdown_pct,
        'trades': completed_trades,
        'win_trades': report.num_winning_trades,
        'loss_trades': report.num_losing_trades,
        'avg_win': report.avg_win,
        'avg_loss': report.avg_loss,
        'win_loss_ratio': report.win_loss_ratio if report.win_loss_ratio else 0,
        'profit_factor': report.profit_factor if report.profit_factor else 0,
        'final_balance': report.final_portfolio_value,
        'initial_balance': config.seed_money,
        'failed_stocks': failed_stocks[:10],  # Show first 10 failed stocks
    }


def print_detailed_results(result: dict):
    """상세 결과 출력"""
    if not result:
        return

    print("\n" + "="*80)
    print(f"📊 {result['period']} 백테스트 결과 상세 분석")
    print("="*80)

    # 기본 정보
    print(f"\n📋 기본 정보:")
    print(f"  백테스트 기간:        {result['start_date']} ~ {result['end_date']}")
    print(f"  분석 종목:            KOSPI Top 100")
    print(f"  성공 로드:            {result['stocks_loaded']}개 종목")
    print(f"  실패 종목:            {result['stocks_failed']}개 종목")
    print(f"  전략:                Phase 3 (Volume + RSI + MACD + Confidence)")

    # 수익성 지표
    print(f"\n💰 수익성 지표:")
    status_emoji = "🟢" if result['total_return'] > 0 else "🔴"
    print(f"  총 수익률:            {status_emoji} {result['total_return']:+.2f}%")
    print(f"  연평균 수익률(CAGR):  {result['cagr']:+.2f}%")
    print(f"  초기 자본:            ₩{result['initial_balance']:,}")
    print(f"  최종 자본:            ₩{result['final_balance']:,.0f}")

    profit_amount = result['final_balance'] - result['initial_balance']
    print(f"  손익 금액:            {status_emoji} ₩{profit_amount:+,.0f}")

    # 거래 통계
    print(f"\n📈 거래 통계:")
    print(f"  총 거래 수:           {result['trades']}건")
    print(f"  승률:                 {result['win_rate']:.1f}%")
    print(f"  수익 거래:            {result['win_trades']}건")
    print(f"  손실 거래:            {result['loss_trades']}건")

    if result['avg_win'] and result['avg_loss']:
        print(f"  평균 수익:            ₩{result['avg_win']:,.0f}")
        print(f"  평균 손실:            ₩{result['avg_loss']:,.0f}")
        print(f"  손익비:               {result['win_loss_ratio']:.2f}")

    # 리스크 지표
    print(f"\n⚠️ 리스크 지표:")
    print(f"  최대 낙폭(MDD):       {result['mdd']:.2f}%")
    print(f"  샤프 비율:            {result['sharpe']:.2f}")
    print(f"  수익 팩터:            {result['profit_factor']:.2f}")

    # 실패한 종목들
    if result['failed_stocks']:
        print(f"\n❌ 데이터 로드 실패 종목 (일부):")
        print(f"  {', '.join(result['failed_stocks'])}")

    # 성과 평가
    print(f"\n🎯 성과 평가:")
    if result['total_return'] > 10:
        evaluation = "🌟 우수 (>10%)"
    elif result['total_return'] > 5:
        evaluation = "✅ 양호 (5-10%)"
    elif result['total_return'] > 0:
        evaluation = "⚡ 보통 (0-5%)"
    elif result['total_return'] > -5:
        evaluation = "⚠️ 부진 (0~-5%)"
    else:
        evaluation = "🔥 손실 (<-5%)"

    print(f"  종합 평가:            {evaluation}")

    if result['sharpe'] > 1.5:
        risk_eval = "🛡️ 우수한 리스크 대비 수익"
    elif result['sharpe'] > 1.0:
        risk_eval = "✅ 양호한 리스크 대비 수익"
    elif result['sharpe'] > 0.5:
        risk_eval = "⚡ 보통의 리스크 대비 수익"
    else:
        risk_eval = "⚠️ 낮은 리스크 대비 수익"

    print(f"  리스크 평가:          {risk_eval}")


if __name__ == "__main__":
    print("="*80)
    print("🎯 2025 KOSPI Top 100 Bollinger Band Strategy Backtest")
    print("Strategy: Phase 3 (Volume + RSI + MACD + Confidence Scoring)")
    print("="*80)

    # KOSPI Top 100 로드
    print("\n[1] KOSPI 상위 100종목 로드...")
    kospi_stocks = load_kospi_top100()
    print(f"✓ {len(kospi_stocks)}개 종목 로드 완료")
    print(f"   샘플: {kospi_stocks[:10]}")

    # 2025년 백테스트 실행
    print("\n[2] 2025년 백테스트 실행...")
    result = run_2025_backtest(kospi_stocks, "2025")

    if result:
        print_detailed_results(result)
    else:
        print("❌ 백테스트 실행에 실패했습니다.")

    print("\n" + "="*80)
    print("✅ 2025 KOSPI Top 100 백테스트 완료")
    print("="*80)