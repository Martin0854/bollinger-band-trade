"""
나의 첫 번째 백테스트
"""

import pandas as pd
from datetime import date
from src.models.config import BacktestConfiguration
from src.backtest.engine import BacktestEngine

# 1단계: 설정 만들기
config = BacktestConfiguration(
    seed_money=10_000_000,      # 초기 자본: 1000만원
    stocks=["005930"],          # 삼성전자
    date_range=(date(2024, 1, 1), date(2024, 12, 31)),  # 백테스트 기간
    bollinger_period=20,        # 볼린저 밴드 기간 (20일)
    bollinger_std_dev=2.0,      # 표준편차 배수 (2배)
    squeeze_threshold_percent=30.0,  # 스퀴즈 감지 임계값 (30%)
    squeeze_lookback_days=10,   # 비교 기간 (10일)
    stop_loss_percent=5.0,      # 손절매 (5%)
    max_position_percent=30.0,  # 종목당 최대 비중 (30%)
    max_positions=5             # 최대 동시 보유 종목 수
)

# 2단계: 가격 데이터 준비
# 실전에서는 실제 주가 데이터를 가져와야 합니다
dates = pd.date_range('2024-01-01', '2024-12-31', freq='D')

# 간단한 가격 데이터 생성 (실전에서는 실제 데이터 사용)
close_prices = []
for i in range(len(dates)):
    if i < 100:
        # 횡보 구간 (스퀴즈 형성)
        price = 60000 + (i % 5) * 200
    elif i < 120:
        # 저변동성 구간 (스퀴즈)
        price = 60000 + (i % 3) * 50
    else:
        # 돌파 및 상승
        price = 60000 + (i - 120) * 300
    close_prices.append(price)

# DataFrame 형식으로 변환
price_data = pd.DataFrame({
    'Open': close_prices,
    'High': [p * 1.02 for p in close_prices],   # 고가 = 종가 + 2%
    'Low': [p * 0.98 for p in close_prices],    # 저가 = 종가 - 2%
    'Close': close_prices,
    'Volume': [1_000_000] * len(dates)          # 거래량
}, index=dates)

# 3단계: 백테스트 엔진 생성 및 데이터 로드
engine = BacktestEngine(config=config)
engine.load_mock_data("005930", price_data)

# 4단계: 백테스트 실행
print("백테스트 실행 중...")
report = engine.run()

# 5단계: 결과 확인
print("\n" + "=" * 70)
print("📊 백테스트 결과")
print("=" * 70)
print(f"초기 자본:           ₩{config.seed_money:,}")
print(f"총 수익률:           {report.total_return_pct:.2f}%")
print(f"승률:               {report.win_rate_pct:.2f}%")
print(f"최대 낙폭(MDD):      {report.max_drawdown_pct:.2f}%")
print(f"샤프 비율:           {report.sharpe_ratio:.2f}")
print(f"\n총 거래 횟수:        {report.num_trades}회")
print(f"  - 수익 거래:       {report.num_winning_trades}회")
print(f"  - 손실 거래:       {report.num_losing_trades}회")

if report.avg_win > 0:
    print(f"\n평균 수익:           ₩{report.avg_win:,.0f}")
if report.avg_loss != 0:
    print(f"평균 손실:           ₩{report.avg_loss:,.0f}")
if report.win_loss_ratio:
    print(f"손익비:             {report.win_loss_ratio:.2f}")

print("=" * 70)

# 6단계: 거래 내역 확인
print(f"\n📋 거래 내역 ({len(engine.trades)}건):")
for i, trade in enumerate(engine.trades, 1):
    action_ko = "매수" if trade.action.value == "buy" else "매도"
    print(f"\n{i}. {action_ko}: {trade.quantity}주 @ ₩{trade.execution_price:,}")
    print(f"   날짜: {trade.execution_timestamp.strftime('%Y-%m-%d')}")
    if trade.entry_reason:
        print(f"   진입 사유: {trade.entry_reason}")
    if trade.exit_reason:
        print(f"   청산 사유: {trade.exit_reason}")
    if trade.realized_pnl:
        pnl_sign = "+" if trade.realized_pnl > 0 else ""
        print(f"   실현손익: {pnl_sign}₩{trade.realized_pnl:,}")

print("\n✅ 백테스트 완료!")
