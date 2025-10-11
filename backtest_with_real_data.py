"""
실제 주가 데이터로 백테스트 실행하기
yfinance를 사용해서 데이터를 다운로드하고 백테스트 실행
"""

import yfinance as yf
import pandas as pd
from datetime import date
from src.models.config import BacktestConfiguration
from src.backtest.engine import BacktestEngine


def fetch_stock_data(stock_code, start_date, end_date):
    """Yahoo Finance에서 한국 주식 데이터 가져오기"""
    # .KS = KOSPI, .KQ = KOSDAQ
    ticker = f"{stock_code}.KS"

    print(f"📥 {stock_code} 데이터 다운로드 중...", end=" ")

    try:
        df = yf.download(ticker, start=start_date, end=end_date, progress=False)

        if df.empty:
            # KOSPI에 없으면 KOSDAQ 시도
            ticker = f"{stock_code}.KQ"
            df = yf.download(ticker, start=start_date, end=end_date, progress=False)

        if df.empty:
            raise ValueError(f"데이터를 찾을 수 없습니다.")

        # 컬럼 정리
        df.columns = df.columns.get_level_values(0)

        result = pd.DataFrame({
            'Open': df['Open'],
            'High': df['High'],
            'Low': df['Low'],
            'Close': df['Close'],
            'Volume': df['Volume']
        }).dropna()

        print(f"✅ {len(result)}일")
        return result

    except Exception as e:
        print(f"❌ 실패: {str(e)}")
        return None


def run_backtest_with_real_data(
    stocks,
    start_date,
    end_date,
    seed_money=10_000_000,
    **strategy_params
):
    """
    실제 주가 데이터로 백테스트 실행

    Args:
        stocks: 종목 코드 리스트 (예: ["005930", "035720"])
        start_date: 시작일 (str 또는 date)
        end_date: 종료일 (str 또는 date)
        seed_money: 초기 자본 (기본: 1000만원)
        **strategy_params: 전략 파라미터 (선택사항)
    """
    print("=" * 70)
    print("🚀 실제 데이터 백테스트 시작")
    print("=" * 70)

    # 1. 설정 생성
    if isinstance(start_date, str):
        start_date = pd.to_datetime(start_date).date()
    if isinstance(end_date, str):
        end_date = pd.to_datetime(end_date).date()

    config = BacktestConfiguration(
        seed_money=seed_money,
        stocks=stocks,
        date_range=(start_date, end_date),
        **strategy_params
    )

    print(f"\n⚙️  설정:")
    print(f"   초기 자본: ₩{config.seed_money:,}")
    print(f"   종목: {', '.join(config.stocks)}")
    print(f"   기간: {config.date_range[0]} ~ {config.date_range[1]}")
    print(f"   볼린저 기간: {config.bollinger_period}일")
    print(f"   스퀴즈 임계값: {config.squeeze_threshold_percent}%")
    print(f"   손절매: {config.stop_loss_percent}%")

    # 2. 백테스트 엔진 생성
    engine = BacktestEngine(config=config)

    # 3. 각 종목의 데이터 다운로드
    print(f"\n📊 데이터 다운로드:")
    loaded_count = 0

    for stock_code in config.stocks:
        data = fetch_stock_data(stock_code, start_date, end_date)
        if data is not None and len(data) > 0:
            engine.load_mock_data(stock_code, data)
            loaded_count += 1

    if loaded_count == 0:
        print("\n❌ 데이터를 가져올 수 없어 백테스트를 실행할 수 없습니다.")
        return None

    print(f"   총 {loaded_count}개 종목 데이터 로드 완료")

    # 4. 백테스트 실행
    print(f"\n⏳ 백테스트 실행 중...\n")
    report = engine.run()

    # 5. 결과 출력
    print("=" * 70)
    print("📈 백테스트 결과")
    print("=" * 70)
    print(f"초기 자본:           ₩{config.seed_money:,}")
    print(f"총 수익률:           {report.total_return_pct:.2f}%")
    print(f"연평균 수익률(CAGR): {report.cagr_pct:.2f}%")
    print(f"\n승률:               {report.win_rate_pct:.2f}%")
    print(f"최대 낙폭(MDD):      {report.max_drawdown_pct:.2f}%")
    print(f"샤프 비율:           {report.sharpe_ratio:.2f}")

    print(f"\n총 거래:            {report.num_trades}회")
    print(f"  - 수익 거래:       {report.num_winning_trades}회")
    print(f"  - 손실 거래:       {report.num_losing_trades}회")

    if report.avg_win > 0:
        print(f"\n평균 수익:           ₩{report.avg_win:,.0f}")
    if report.avg_loss != 0:
        print(f"평균 손실:           ₩{report.avg_loss:,.0f}")
    if report.win_loss_ratio:
        print(f"손익비:             {report.win_loss_ratio:.2f}")
    if report.profit_factor:
        print(f"수익 팩터:           {report.profit_factor:.2f}")

    print("=" * 70)

    # 6. 거래 내역
    if len(engine.trades) > 0:
        print(f"\n📋 거래 내역 (총 {len(engine.trades)}건):")
        for i, trade in enumerate(engine.trades[:10], 1):  # 최근 10건만 표시
            action_ko = "매수" if trade.action.value == "buy" else "매도"
            print(f"\n{i}. [{trade.stock_code}] {action_ko}: {trade.quantity}주 @ ₩{trade.execution_price:,.0f}")
            print(f"   날짜: {trade.execution_timestamp.strftime('%Y-%m-%d')}")
            if trade.realized_pnl:
                pnl_sign = "+" if trade.realized_pnl > 0 else ""
                print(f"   손익: {pnl_sign}₩{trade.realized_pnl:,.0f}")

        if len(engine.trades) > 10:
            print(f"\n   ... 외 {len(engine.trades) - 10}건")
    else:
        print("\n⚠️  거래가 실행되지 않았습니다.")
        print("   팁: squeeze_threshold_percent를 낮춰보세요 (예: 20-25%)")

    return report, engine


# ============================================================
# 예제 실행
# ============================================================

if __name__ == "__main__":
    # 예제 1: 삼성전자 단일 종목
    print("\n" + "🔹" * 35)
    print("예제 1: 삼성전자 (005930) - 2024년")
    print("🔹" * 35)

    report1, engine1 = run_backtest_with_real_data(
        stocks=["005930"],
        start_date="2024-01-01",
        end_date="2024-12-31",
        seed_money=10_000_000,
        bollinger_period=20,
        squeeze_threshold_percent=30,
        stop_loss_percent=5.0
    )

    # 예제 2: 3종목 포트폴리오
    print("\n\n" + "🔹" * 35)
    print("예제 2: 3종목 포트폴리오 - 2024년")
    print("🔹" * 35)

    report2, engine2 = run_backtest_with_real_data(
        stocks=["005930", "035720", "000660"],  # 삼성전자, 카카오, SK하이닉스
        start_date="2024-01-01",
        end_date="2024-12-31",
        seed_money=30_000_000,  # 3종목이므로 자본 증액
        bollinger_period=20,
        squeeze_threshold_percent=25,  # 약간 낮춤
        stop_loss_percent=5.0,
        max_positions=3
    )

    print("\n\n✅ 모든 백테스트 완료!")
    print("\n💡 팁:")
    print("   - 거래가 없다면 squeeze_threshold_percent를 20-25%로 낮춰보세요")
    print("   - 더 긴 기간으로 테스트하려면 start_date를 '2023-01-01'로 변경하세요")
    print("   - 데이터는 data/logs/backtest.db 에 저장됩니다")
