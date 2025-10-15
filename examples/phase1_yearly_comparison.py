"""
Phase 1 MVP 연도별 백테스트 비교
KOSPI 100 종목으로 2020-2024년 각 연도별 성과 비교
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

        return result if len(result) >= 100 else None

    except Exception:
        return None


def load_kospi_top100(filepath: str = "scripts/kospi_top100.txt") -> list:
    """KOSPI Top 100 종목 리스트 로드"""
    with open(filepath, 'r') as f:
        stocks = [line.strip() for line in f if line.strip()]
    return stocks[:100]


def run_backtest_for_year(year: int, kospi_stocks: list, config_template: BacktestConfiguration) -> dict:
    """특정 연도의 백테스트 실행"""
    print(f"\n{'='*80}")
    print(f"📅 {year}년 백테스트")
    print(f"{'='*80}")

    # 연도 설정
    config = BacktestConfiguration.from_yaml("config/examples/phase1_volume_rsi.yaml")
    config.stocks = kospi_stocks
    config.seed_money = 100_000_000
    config.max_positions = 15
    config.date_range = (f"{year}-01-01", f"{year}-12-31")

    # 데이터 다운로드
    print(f"\n데이터 다운로드 중... ", end="", flush=True)
    engine = BacktestEngine(config=config)
    loaded_count = 0

    for stock_code in kospi_stocks:
        data = fetch_stock_data(stock_code, config.date_range[0], config.date_range[1])
        if data is not None and len(data) > 0:
            engine.load_mock_data(stock_code, data)
            loaded_count += 1

    print(f"✓ {loaded_count}개 종목")

    if loaded_count == 0:
        return None

    # 백테스트 실행
    print(f"백테스트 실행 중... ", end="", flush=True)
    report = engine.run()
    print("✓ 완료")

    # 결과 요약
    completed_trades = report.num_trades // 2

    return {
        'year': year,
        'stocks_loaded': loaded_count,
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
    }


print("=" * 80)
print("Phase 1 MVP 연도별 백테스트 비교 (KOSPI 100)")
print("2020-2024년 각 연도별 성과 분석")
print("=" * 80)

# KOSPI Top 100 로드
print("\n[1] KOSPI 상위 100종목 로드...")
kospi_stocks = load_kospi_top100()
print(f"✓ {len(kospi_stocks)}개 종목")

# 설정 템플릿 로드
config_template = BacktestConfiguration.from_yaml("config/examples/phase1_volume_rsi.yaml")

# 각 연도별 백테스트 실행
years = [2020, 2021, 2022, 2023, 2024]
results = []

for year in years:
    result = run_backtest_for_year(year, kospi_stocks, config_template)
    if result:
        results.append(result)

# 결과 출력
print("\n" + "=" * 80)
print("📊 연도별 백테스트 결과 종합")
print("=" * 80)

# 테이블 헤더
print("\n┌────────┬──────────┬──────────┬──────────┬──────────┬──────────┬──────────┐")
print("│  연도  │ 수익률   │   CAGR   │  승률    │  샤프    │   MDD    │  거래수  │")
print("├────────┼──────────┼──────────┼──────────┼──────────┼──────────┼──────────┤")

best_year = None
worst_year = None
best_return = -999999
worst_return = 999999

for r in results:
    status = "🟢" if r['total_return'] > 0 else "🔴"
    print(f"│ {r['year']} │ {status} {r['total_return']:6.2f}% │ {r['cagr']:7.2f}% │ {r['win_rate']:7.2f}% │ {r['sharpe']:7.2f} │ {r['mdd']:7.2f}% │ {r['trades']:5d}건 │")

    if r['total_return'] > best_return:
        best_return = r['total_return']
        best_year = r
    if r['total_return'] < worst_return:
        worst_return = r['total_return']
        worst_year = r

print("└────────┴──────────┴──────────┴──────────┴──────────┴──────────┴──────────┘")

# 통계 요약
print("\n📈 통계 요약:")
avg_return = sum([r['total_return'] for r in results]) / len(results)
avg_win_rate = sum([r['win_rate'] for r in results]) / len(results)
avg_sharpe = sum([r['sharpe'] for r in results]) / len(results)
total_trades = sum([r['trades'] for r in results])

print(f"  평균 수익률:           {avg_return:.2f}%")
print(f"  평균 승률:             {avg_win_rate:.2f}%")
print(f"  평균 샤프 비율:        {avg_sharpe:.2f}")
print(f"  총 거래 수:            {total_trades}건")
print(f"  수익 연도:             {len([r for r in results if r['total_return'] > 0])}/5년")

# 최고/최악의 해
print(f"\n🌟 최고의 해: {best_year['year']}년")
print(f"   수익률: {best_year['total_return']:.2f}%")
print(f"   승률: {best_year['win_rate']:.2f}%")
print(f"   샤프: {best_year['sharpe']:.2f}")
print(f"   거래: {best_year['trades']}건")

print(f"\n📉 최악의 해: {worst_year['year']}년")
print(f"   수익률: {worst_year['total_return']:.2f}%")
print(f"   승률: {worst_year['win_rate']:.2f}%")
print(f"   샤프: {worst_year['sharpe']:.2f}")
print(f"   거래: {worst_year['trades']}건")

# 상세 분석
print("\n" + "=" * 80)
print("🔍 상세 분석")
print("=" * 80)

for r in results:
    print(f"\n【 {r['year']}년 】")
    print(f"  수익률: {r['total_return']:+.2f}% | 승률: {r['win_rate']:.1f}% | 샤프: {r['sharpe']:.2f}")
    print(f"  거래: {r['trades']}건 (수익 {r['win_trades']}건, 손실 {r['loss_trades']}건)")
    print(f"  평균 수익: ₩{r['avg_win']:,.0f} | 평균 손실: ₩{r['avg_loss']:,.0f}")
    print(f"  손익비: {r['win_loss_ratio']:.2f} | 수익 팩터: {r['profit_factor']:.2f}")
    print(f"  MDD: {r['mdd']:.2f}%")

# 결론 및 인사이트
print("\n" + "=" * 80)
print("💡 인사이트 및 결론")
print("=" * 80)

profitable_years = [r for r in results if r['total_return'] > 0]
losing_years = [r for r in results if r['total_return'] < 0]

print(f"\n✅ 수익 연도: {len(profitable_years)}년 ({', '.join([str(r['year']) for r in profitable_years])})")
print(f"❌ 손실 연도: {len(losing_years)}년 ({', '.join([str(r['year']) for r in losing_years])})")

if avg_return < 0:
    print(f"\n⚠️  5년 평균 수익률이 음수({avg_return:.2f}%)입니다.")
    print("   전략이 시장 하락기에 취약합니다.")
    print("\n💡 개선 방향:")
    print("   1. 하락장 감지 로직 추가 (시장 추세 필터)")
    print("   2. 손절매 강화 (ATR 기반 동적 손절)")
    print("   3. 포지션 크기 조정 (변동성 기반)")
    print("   4. MACD 추가로 추세 확인 (Phase 2)")
else:
    print(f"\n✅ 5년 평균 수익률: {avg_return:.2f}% (긍정적)")
    if avg_win_rate < 45:
        print(f"   승률({avg_win_rate:.1f}%)은 개선 필요")
        print("   Phase 2(MACD)로 신호 품질 향상 권장")

print("\n" + "=" * 80)
print("✅ 연도별 백테스트 비교 완료")
print("=" * 80)
