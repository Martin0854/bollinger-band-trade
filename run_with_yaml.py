"""
YAML 설정 파일을 사용한 백테스트
"""

import pandas as pd
from src.models.config import BacktestConfiguration
from src.backtest.engine import BacktestEngine

# YAML 파일에서 설정 로드
config = BacktestConfiguration.from_yaml("my_strategy.yaml")

print(f"✅ 설정 로드 완료:")
print(f"  - 초기 자본: ₩{config.seed_money:,}")
print(f"  - 종목: {', '.join(config.stocks)}")
print(f"  - 기간: {config.date_range[0]} ~ {config.date_range[1]}")
print(f"  - 볼린저 기간: {config.bollinger_period}일")
print(f"  - 손절매: {config.stop_loss_percent}%")

# 백테스트 엔진 생성
engine = BacktestEngine(config=config)

# 각 종목에 대한 데이터 로드
for stock_code in config.stocks:
    # 실전에서는 실제 주가 데이터를 가져와야 합니다
    dates = pd.date_range(str(config.date_range[0]), str(config.date_range[1]), freq='D')

    # 종목별 기본 가격 설정
    base_prices = {
        "005930": 60000,  # 삼성전자
        "035720": 50000,  # 카카오
    }
    base_price = base_prices.get(stock_code, 50000)

    # 간단한 가격 데이터 생성
    close_prices = [base_price + i * 100 for i in range(len(dates))]

    price_data = pd.DataFrame({
        'Open': close_prices,
        'High': [p * 1.02 for p in close_prices],
        'Low': [p * 0.98 for p in close_prices],
        'Close': close_prices,
        'Volume': [1_000_000] * len(dates)
    }, index=dates)

    engine.load_mock_data(stock_code, price_data)
    print(f"  - {stock_code} 데이터 로드: {len(price_data)}일")

# 백테스트 실행
print("\n백테스트 실행 중...\n")
report = engine.run()

# 결과 출력
print("=" * 70)
print("📊 백테스트 결과")
print("=" * 70)
print(f"총 수익률:           {report.total_return_pct:.2f}%")
print(f"승률:               {report.win_rate_pct:.2f}%")
print(f"총 거래:            {report.num_trades}회")
print("=" * 70)
