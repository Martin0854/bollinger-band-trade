"""
Phase 1 MVP 백테스트 - KOSPI 상위 100종목
Volume Filter + RSI Filter with KOSPI Top 100 Stocks
"""

import yfinance as yf
import pandas as pd
from datetime import datetime
from typing import Dict, Optional
from src.models.config import BacktestConfiguration
from src.backtest.engine import BacktestEngine


def fetch_stock_data(stock_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
    """Yahoo Finance에서 한국 주식 데이터 가져오기"""
    ticker = f"{stock_code}.KS"

    try:
        df = yf.download(ticker, start=start_date, end=end_date, progress=False)

        if df.empty:
            # KOSPI에 없으면 KOSDAQ 시도
            ticker = f"{stock_code}.KQ"
            df = yf.download(ticker, start=start_date, end=end_date, progress=False)

        if df.empty:
            return None

        # 컬럼 정리
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        result = pd.DataFrame({
            'Open': df['Open'],
            'High': df['High'],
            'Low': df['Low'],
            'Close': df['Close'],
            'Volume': df['Volume']
        }).dropna()

        return result if len(result) >= 100 else None  # 최소 100일 데이터 필요

    except Exception:
        return None


def load_kospi_top100(filepath: str = "scripts/kospi_top100.txt") -> list:
    """KOSPI Top 100 종목 리스트 로드"""
    with open(filepath, 'r') as f:
        stocks = [line.strip() for line in f if line.strip()]
    return stocks[:100]  # 정확히 100개만


print("=" * 80)
print("Phase 1 MVP 백테스트 - KOSPI 상위 100종목 (표준 파라미터)")
print("Volume Filter + RSI Filter")
print("=" * 80)

# Step 1: Load KOSPI Top 100
print("\n[1] KOSPI 상위 100종목 로드...")
kospi_stocks = load_kospi_top100()
print(f"✓ {len(kospi_stocks)}개 종목 로드 완료")

# Step 2: Load standard configuration
print("\n[2] Phase 1 MVP 설정 로드 (표준 파라미터)...")
config = BacktestConfiguration.from_yaml("config/examples/phase1_volume_rsi.yaml")

# Override with KOSPI 100 stocks and adjusted capital
config.stocks = kospi_stocks
config.seed_money = 100_000_000  # 1억원 (100 stocks)
config.max_positions = 15  # 최대 15개 종목 동시 보유

print(f"✓ 설정 완료:")
print(f"  - 초기 자본: ₩{config.seed_money:,}")
print(f"  - 종목 수: {len(config.stocks)}개")
print(f"  - 기간: {config.date_range[0]} ~ {config.date_range[1]}")
print(f"  - 최대 동시 보유: {config.max_positions}종목")
print(f"  - Squeeze 임계값: {config.squeeze_threshold_percent}%")
print(f"  - Volume 배수: {config.enhanced_strategy.volume_filter.multiplier}x")
print(f"  - RSI 과매수: {config.enhanced_strategy.rsi.overbought}")
print(f"  - 신뢰도 임계값: {config.enhanced_strategy.confidence.threshold}점")

# Step 3: Download data with progress tracking
print(f"\n[3] 실제 주가 데이터 다운로드 (100개 종목):")
print("   (이 작업은 약 5-10분 정도 소요됩니다...)")
print()

engine = BacktestEngine(config=config)
loaded_stocks = []
failed_stocks = []
stock_data_info = {}

for i, stock_code in enumerate(kospi_stocks, 1):
    print(f"   [{i:3d}/100] {stock_code} ", end="", flush=True)

    data = fetch_stock_data(stock_code, config.date_range[0], config.date_range[1])

    if data is not None and len(data) > 0:
        engine.load_mock_data(stock_code, data)
        loaded_stocks.append(stock_code)
        stock_data_info[stock_code] = len(data)
        print(f"✅ {len(data):3d}일")
    else:
        failed_stocks.append(stock_code)
        print("❌ 실패")

print()
print(f"  ✓ 성공: {len(loaded_stocks)}개 종목 ({len(loaded_stocks)/len(kospi_stocks)*100:.1f}%)")
print(f"  ✗ 실패: {len(failed_stocks)}개 종목")

if len(loaded_stocks) == 0:
    print("\n❌ 데이터를 가져올 수 없어 백테스트를 실행할 수 없습니다.")
    exit(1)

if len(loaded_stocks) < 50:
    print(f"\n⚠️  경고: 로드된 종목이 {len(loaded_stocks)}개로 적습니다.")
    print("   결과의 신뢰도가 낮을 수 있습니다.")

# Step 4: Display filter configuration
print(f"\n[4] 필터 설정 (표준):")
print(f"  ✓ Volume Filter: {engine.volume_filter.window_days}일 평균, {engine.volume_filter.multiplier}x 이상")
print(f"  ✓ RSI Indicator: {engine.rsi_indicator.period}일, 과매수={engine.rsi_indicator.overbought}")
print(f"  ✓ 신뢰도 임계값: {engine.signal_generator.confidence_threshold}점")

# Step 5: Run backtest
print(f"\n[5] 백테스트 실행 중...")
print("   (100개 종목 처리 중... 약 2-3분 소요)")
start_time = datetime.now()
report = engine.run()
elapsed_time = (datetime.now() - start_time).total_seconds()
print(f"  ✓ 백테스트 완료! (소요 시간: {elapsed_time:.1f}초)")

# Step 6: Display comprehensive results
print("\n" + "=" * 80)
print("📈 PHASE 1 MVP 백테스트 결과 (KOSPI 100, 실제 데이터, 표준 파라미터)")
print("=" * 80)

print("\n💰 수익성 지표:")
print(f"  초기 자본:             ₩{config.seed_money:,}")
print(f"  최종 자본:             ₩{config.seed_money * (1 + report.total_return_pct/100):,.0f}")
print(f"  총 수익률:             {report.total_return_pct:.2f}%")
print(f"  연평균 수익률(CAGR):   {report.cagr_pct:.2f}%")

print(f"\n📊 리스크 지표:")
print(f"  승률:                  {report.win_rate_pct:.2f}%")
print(f"  최대 낙폭(MDD):        {report.max_drawdown_pct:.2f}%")
print(f"  샤프 비율:             {report.sharpe_ratio:.2f}")

print(f"\n📈 거래 통계:")
print(f"  총 거래:               {report.num_trades}회 (매수+매도 합계)")
print(f"  완료된 거래:           {report.num_trades // 2}회")
print(f"    - 수익 거래:         {report.num_winning_trades}회")
print(f"    - 손실 거래:         {report.num_losing_trades}회")

if report.avg_win > 0:
    print(f"  평균 수익:             ₩{report.avg_win:,.0f}")
if report.avg_loss != 0:
    print(f"  평균 손실:             ₩{report.avg_loss:,.0f}")
if report.win_loss_ratio:
    print(f"  손익비:                {report.win_loss_ratio:.2f}")
if report.profit_factor:
    print(f"  수익 팩터:             {report.profit_factor:.2f}")

# Step 7: Trade details by stock
print(f"\n📋 종목별 거래 통계:")
print("-" * 80)

# Group trades by stock
stock_trades = {}
for trade in engine.trades:
    if trade.stock_code not in stock_trades:
        stock_trades[trade.stock_code] = []
    stock_trades[trade.stock_code].append(trade)

# Calculate per-stock statistics
stock_stats = []
for stock_code, trades in stock_trades.items():
    completed_trades = len([t for t in trades if t.action.value == "sell"])
    total_pnl = sum([t.realized_pnl for t in trades if t.realized_pnl])
    wins = len([t for t in trades if t.realized_pnl and t.realized_pnl > 0])

    stock_stats.append({
        'code': stock_code,
        'trades': completed_trades,
        'pnl': total_pnl,
        'wins': wins,
        'win_rate': wins / completed_trades * 100 if completed_trades > 0 else 0
    })

# Sort by PnL
stock_stats.sort(key=lambda x: x['pnl'], reverse=True)

# Top 10 profitable stocks
print("\n🌟 수익 상위 10종목:")
for i, stat in enumerate(stock_stats[:10], 1):
    win_rate_str = f"{stat['win_rate']:.0f}%" if stat['trades'] > 0 else "N/A"
    print(f"  {i:2d}. {stat['code']}: {stat['trades']:2d}건 | "
          f"손익: {stat['pnl']:+,.0f}원 | 승률: {win_rate_str}")

# Bottom 10 stocks (if any losses)
loss_stocks = [s for s in stock_stats if s['pnl'] < 0]
if len(loss_stocks) > 0:
    print("\n📉 손실 상위 10종목:")
    for i, stat in enumerate(loss_stocks[-10:], 1):
        win_rate_str = f"{stat['win_rate']:.0f}%" if stat['trades'] > 0 else "N/A"
        print(f"  {i:2d}. {stat['code']}: {stat['trades']:2d}건 | "
              f"손익: {stat['pnl']:+,.0f}원 | 승률: {win_rate_str}")

# Stocks with most trades
print("\n📊 거래 빈도 상위 10종목:")
stock_stats_by_trades = sorted(stock_stats, key=lambda x: x['trades'], reverse=True)
for i, stat in enumerate(stock_stats_by_trades[:10], 1):
    print(f"  {i:2d}. {stat['code']}: {stat['trades']:2d}건 | "
          f"손익: {stat['pnl']:+,.0f}원")

# Sample trades
if len(engine.trades) > 0:
    print(f"\n📋 거래 샘플 (최근 20건):")
    print("-" * 80)

    for i, trade in enumerate(engine.trades[:20], 1):
        action_ko = "🟢 매수" if trade.action.value == "buy" else "🔴 매도"
        print(f"{i}. [{trade.stock_code}] {action_ko}: {trade.quantity}주 @ ₩{trade.execution_price:,.0f}")
        print(f"   날짜: {trade.execution_timestamp.strftime('%Y-%m-%d')}", end="")

        if trade.realized_pnl:
            pnl_sign = "+" if trade.realized_pnl > 0 else ""
            pnl_emoji = "🟢" if trade.realized_pnl > 0 else "🔴"
            print(f" | 손익: {pnl_emoji} {pnl_sign}₩{trade.realized_pnl:,.0f}")
        else:
            print()

    if len(engine.trades) > 20:
        print(f"\n   ... 외 {len(engine.trades) - 20}건")
else:
    print(f"\n⚠️  거래가 실행되지 않았습니다.")

# Step 8: Phase 1 MVP Goal Assessment
print("\n" + "=" * 80)
print("🎯 PHASE 1 MVP 목표 달성도 평가")
print("=" * 80)

goals = [
    ("승률 (Win Rate)", report.win_rate_pct, 55, 60, "%"),
    ("연간 수익률 (CAGR)", report.cagr_pct, 5, 8, "%"),
]

print("\n목표 vs 실제:")
all_goals_met = True
for goal_name, actual, target_min, target_max, unit in goals:
    if target_min <= actual <= target_max:
        status = "✅ 달성"
        color = "🟢"
    elif actual > target_max:
        status = "✨ 초과달성"
        color = "🌟"
    else:
        status = "❌ 미달성"
        color = "🔴"
        all_goals_met = False

    print(f"{color} {goal_name:30s} 목표: {target_min:5.1f}-{target_max:5.1f}{unit}  |  실제: {actual:6.2f}{unit}  ({status})")

print(f"\n📊 필터 효과성:")
print(f"  데이터 로드 성공:      {len(loaded_stocks)}/100 종목 ({len(loaded_stocks)/100*100:.0f}%)")
print(f"  Squeeze 임계값:        {config.squeeze_threshold_percent}%")
print(f"  Volume 배수:           {config.enhanced_strategy.volume_filter.multiplier}x")
print(f"  RSI 과매수:            {config.enhanced_strategy.rsi.overbought}")
print(f"  신뢰도 임계값:         {config.enhanced_strategy.confidence.threshold}점")
print(f"  신호 생성 수:          {len(engine.trades) // 2}회")
print(f"  거래 종목 수:          {len(stock_trades)}개")
print(f"  평균 종목당 거래:      {len(stock_trades) / len(loaded_stocks) * 100:.1f}%가 1회 이상 거래")

# Statistical significance assessment
completed_trades = report.num_trades // 2
print(f"\n📈 통계적 유의성:")
if completed_trades >= 30:
    print(f"  ✅ 충분한 샘플: {completed_trades}건 (30건 이상)")
    print(f"     결과를 신뢰할 수 있습니다.")
elif completed_trades >= 10:
    print(f"  ⚠️  보통 샘플: {completed_trades}건 (10-30건)")
    print(f"     참고용으로 사용 가능합니다.")
else:
    print(f"  ❌ 부족한 샘플: {completed_trades}건 (10건 미만)")
    print(f"     샘플 크기가 작아 결과의 신뢰도가 낮습니다.")

print("\n" + "=" * 80)
if all_goals_met:
    print("🎉 Phase 1 MVP 목표 달성! (KOSPI 100)")
    print("=" * 80)
    print(f"\n✅ {len(loaded_stocks)}개 종목으로 {completed_trades}건의 거래를 완료했습니다.")
    print(f"   Volume Filter와 RSI Filter가 효과적으로 작동했습니다.")
    print("\n🚀 다음 단계:")
    print("   - Phase 2: MACD 필터 추가 (승률 70-75% 목표)")
    print("   - Phase 3: 다단계 신뢰도 평가 시스템 구현")
    print("   - Phase 4: ATR 기반 동적 손절매 (수익률 +15-20% 목표)")
elif completed_trades >= 10:
    print("📊 Phase 1 MVP 백테스트 완료 (일부 목표 미달성)")
    print("=" * 80)
    print(f"\n✅ 성과:")
    print(f"   - {len(loaded_stocks)}개 종목에서 {completed_trades}건 거래 발생")
    print(f"   - 통계적으로 의미있는 샘플 확보")

    print(f"\n💡 개선 제안:")
    if report.win_rate_pct < 55:
        print(f"   📊 승률 개선 (현재 {report.win_rate_pct:.1f}%):")
        print(f"      - RSI overbought를 70으로 낮춰 더 보수적 진입")
        print(f"      - 신뢰도 임계값을 55-60으로 높여 고품질 신호만 선택")

    if report.cagr_pct < 5:
        print(f"   💰 수익률 개선 (현재 {report.cagr_pct:.1f}%):")
        print(f"      - max_position_percent를 35-40%로 증가")
        print(f"      - 수익 종목의 패턴 분석하여 파라미터 최적화")
else:
    print("⚠️  표준 파라미터로 거래 부족")
    print("=" * 80)
    print(f"\n   - 거래 발생: {completed_trades}건 (목표: 10건 이상)")
    print("\n💡 추가 조치 필요:")
    print("   - squeeze_threshold_percent를 25%로 낮춤")
    print("   - volume_filter.multiplier를 1.2x로 낮춤")
    print("   - confidence.threshold를 50-55로 낮춤")
    print("   - 더 긴 백테스트 기간 사용 (2022-2024 2년)")

print("\n" + "=" * 80)
print(f"✅ Phase 1 MVP 백테스트 완료 (KOSPI 100)")
print("=" * 80)
print(f"\n📊 요약:")
print(f"   - 종목 수: {len(loaded_stocks)}개")
print(f"   - 기간: {config.date_range[0]} ~ {config.date_range[1]}")
print(f"   - 거래: {completed_trades}건")
print(f"   - 승률: {report.win_rate_pct:.1f}%")
print(f"   - CAGR: {report.cagr_pct:.1f}%")
print(f"   - 샤프: {report.sharpe_ratio:.2f}")
print("\n" + "=" * 80)
