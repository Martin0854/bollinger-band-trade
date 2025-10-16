"""
두산(000150) 거래 검증 스크립트
3천만원 수익이 실제로 맞는지 확인
"""

import yfinance as yf
import pandas as pd
from datetime import datetime
from decimal import Decimal

# 두산 데이터 가져오기
print("=" * 80)
print("두산(000150) 거래 검증")
print("=" * 80)

stock_code = "000150"
ticker = f"{stock_code}.KS"

print(f"\n[1] 2025년 1월~9월 두산 주가 데이터 다운로드...")
df = yf.download(ticker, start="2025-01-01", end="2025-09-30", progress=False)

if df.empty:
    print("❌ 데이터를 가져올 수 없습니다.")
    exit(1)

# 컬럼 정리
if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)

print(f"✓ {len(df)}일치 데이터 확인")

# 기본 통계
print(f"\n[2] 두산 주가 요약:")
print(f"  기간: 2025-01-01 ~ 2025-09-30")
print(f"  시작가: ₩{df['Close'].iloc[0]:,.0f}")
print(f"  종가: ₩{df['Close'].iloc[-1]:,.0f}")
print(f"  최저가: ₩{df['Close'].min():,.0f}")
print(f"  최고가: ₩{df['Close'].max():,.0f}")
print(f"  상승률: {(df['Close'].iloc[-1] / df['Close'].iloc[0] - 1) * 100:.2f}%")

# 볼린저 밴드 계산
from src.indicators.bollinger import calculate_bollinger_bands

bands = calculate_bollinger_bands(
    close_prices=df['Close'],
    period=20,
    std_multiplier=2.0
)

# Squeeze 탐지
from src.indicators.squeeze import detect_squeeze

squeeze_signals = detect_squeeze(
    band_width=bands['bandwidth'],
    lookback_days=10,
    threshold_percent=30.0
)

print(f"\n[3] Squeeze 이벤트:")
squeeze_dates = squeeze_signals[squeeze_signals == True].index
print(f"  총 {len(squeeze_dates)}회 Squeeze 발생")
if len(squeeze_dates) > 0:
    for i, date in enumerate(squeeze_dates[:5], 1):
        print(f"    {i}. {date.strftime('%Y-%m-%d')}")
    if len(squeeze_dates) > 5:
        print(f"    ... 외 {len(squeeze_dates) - 5}회")

# 매수 신호 찾기 (Squeeze 후 상단 밴드 돌파)
print(f"\n[4] 매수 신호 분석:")
in_squeeze = False
min_bandwidth = None

potential_entries = []

for current_date in df.index:
    if pd.isna(bands.loc[current_date, 'upper']):
        continue

    current_price = df.loc[current_date, 'Close']
    upper_band = bands.loc[current_date, 'upper']
    band_width = bands.loc[current_date, 'bandwidth']

    # Track minimum bandwidth
    if min_bandwidth is None or band_width < min_bandwidth:
        min_bandwidth = band_width

    # Squeeze detection
    if current_date in squeeze_dates:
        in_squeeze = True
    elif in_squeeze and band_width <= min_bandwidth * 1.2:
        in_squeeze = True

    # Entry signal: price breaks above upper band after squeeze
    if in_squeeze and current_price > upper_band:
        bandwidth_expanding = band_width >= min_bandwidth * 1.1
        if bandwidth_expanding:
            potential_entries.append({
                'date': current_date,
                'price': current_price,
                'upper_band': upper_band,
                'bandwidth': band_width,
                'volume': df.loc[current_date, 'Volume']
            })
            in_squeeze = False

print(f"  찾은 매수 신호: {len(potential_entries)}개")

# 실제 백테스트 엔진으로 확인
from src.models.config import BacktestConfiguration
from src.backtest.engine import BacktestEngine

print(f"\n[5] 백테스트 엔진으로 실제 거래 확인:")
config = BacktestConfiguration.from_yaml("config/examples/phase1_volume_rsi.yaml")
config.stocks = ["000150"]  # 두산만
config.seed_money = 100_000_000

engine = BacktestEngine(config=config)
engine.load_mock_data("000150", df)

report = engine.run()

print(f"\n[6] 두산 거래 결과:")
print(f"  총 거래: {len(engine.trades)}회")

duosan_trades = [t for t in engine.trades if t.stock_code == "000150"]

if len(duosan_trades) == 0:
    print("  ⚠️  거래가 없습니다!")
    print("\n  필터 조건 확인:")
    print(f"    - Volume Filter: {engine.volume_filter is not None}")
    print(f"    - RSI Filter: {engine.rsi_indicator is not None}")
else:
    print(f"\n[7] 두산 거래 상세:")
    for i, trade in enumerate(duosan_trades, 1):
        action = "🟢 매수" if trade.action.value == "buy" else "🔴 매도"
        print(f"\n  {i}. {action}")
        print(f"     날짜: {trade.execution_timestamp.strftime('%Y-%m-%d')}")
        print(f"     가격: ₩{float(trade.execution_price):,.0f}")
        print(f"     수량: {trade.quantity}주")
        print(f"     금액: ₩{float(trade.execution_price * trade.quantity):,.0f}")

        if trade.realized_pnl:
            print(f"     손익: {'+' if trade.realized_pnl > 0 else ''}₩{float(trade.realized_pnl):,.0f}")

            # 수익률 계산
            if i > 1:
                buy_trade = duosan_trades[i-2]
                buy_price = float(buy_trade.execution_price)
                sell_price = float(trade.execution_price)
                pnl_pct = (sell_price / buy_price - 1) * 100
                holding_days = (trade.execution_timestamp - buy_trade.execution_timestamp).days

                print(f"     수익률: {pnl_pct:+.2f}%")
                print(f"     보유기간: {holding_days}일")

# 검증
print(f"\n" + "=" * 80)
print("🔍 검증 결과")
print("=" * 80)

if len(duosan_trades) >= 2:
    buy_trade = duosan_trades[0]
    sell_trade = duosan_trades[1]

    buy_price = float(buy_trade.execution_price)
    sell_price = float(sell_trade.execution_price)
    quantity = buy_trade.quantity

    expected_pnl = (sell_price - buy_price) * quantity
    actual_pnl = float(sell_trade.realized_pnl) if sell_trade.realized_pnl else 0

    print(f"\n매수: {buy_trade.execution_timestamp.strftime('%Y-%m-%d')}")
    print(f"  - 가격: ₩{buy_price:,.0f}")
    print(f"  - 수량: {quantity}주")
    print(f"  - 총액: ₩{buy_price * quantity:,.0f}")

    print(f"\n매도: {sell_trade.execution_timestamp.strftime('%Y-%m-%d')}")
    print(f"  - 가격: ₩{sell_price:,.0f}")
    print(f"  - 수량: {quantity}주")
    print(f"  - 총액: ₩{sell_price * quantity:,.0f}")

    print(f"\n손익 계산:")
    print(f"  - 예상 손익: ₩{expected_pnl:,.0f}")
    print(f"  - 실제 손익: ₩{actual_pnl:,.0f}")
    print(f"  - 차이: ₩{abs(expected_pnl - actual_pnl):,.0f}")

    print(f"\n수익률:")
    print(f"  - {(sell_price / buy_price - 1) * 100:+.2f}%")

    print(f"\n보유기간:")
    print(f"  - {(sell_trade.execution_timestamp - buy_trade.execution_timestamp).days}일")

    if abs(expected_pnl - actual_pnl) < 1:
        print(f"\n✅ 검증 성공: 손익 계산이 정확합니다.")
    else:
        print(f"\n⚠️  검증 실패: 손익 계산에 오차가 있습니다.")

    # 실제 주가 데이터와 비교
    print(f"\n실제 주가 확인:")
    buy_date_str = buy_trade.execution_timestamp.strftime('%Y-%m-%d')
    sell_date_str = sell_trade.execution_timestamp.strftime('%Y-%m-%d')

    if buy_date_str in df.index.strftime('%Y-%m-%d'):
        buy_idx = df.index[df.index.strftime('%Y-%m-%d') == buy_date_str][0]
        actual_buy_price = df.loc[buy_idx, 'Close']
        print(f"  - 매수일({buy_date_str}) 실제 종가: ₩{actual_buy_price:,.0f}")
        print(f"  - 백테스트 매수가: ₩{buy_price:,.0f}")
        print(f"  - 차이: ₩{abs(actual_buy_price - buy_price):,.0f}")

    if sell_date_str in df.index.strftime('%Y-%m-%d'):
        sell_idx = df.index[df.index.strftime('%Y-%m-%d') == sell_date_str][0]
        actual_sell_price = df.loc[sell_idx, 'Close']
        print(f"  - 매도일({sell_date_str}) 실제 종가: ₩{actual_sell_price:,.0f}")
        print(f"  - 백테스트 매도가: ₩{sell_price:,.0f}")
        print(f"  - 차이: ₩{abs(actual_sell_price - sell_price):,.0f}")

    # 포지션 크기 확인
    print(f"\n포지션 크기 확인:")
    position_value = buy_price * quantity
    position_pct = (position_value / config.seed_money) * 100
    print(f"  - 포지션 가치: ₩{position_value:,.0f}")
    print(f"  - 전체 자본 대비: {position_pct:.2f}%")
    print(f"  - 설정된 최대 포지션: {config.max_position_percent}%")

    if position_pct <= config.max_position_percent * 1.01:  # 1% 오차 허용
        print(f"  ✅ 포지션 크기가 적절합니다.")
    else:
        print(f"  ⚠️  포지션 크기가 제한을 초과합니다!")

else:
    print("\n⚠️  매매 거래가 충분하지 않아 검증할 수 없습니다.")

print("\n" + "=" * 80)
