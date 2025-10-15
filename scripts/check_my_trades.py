"""
내 거래 내역 간단히 확인하기
"""

import yfinance as yf
from datetime import date
from src.models.config import BacktestConfiguration
from src.backtest.engine import BacktestEngine
from analyze_trades import (
    analyze_trades_detail,
    create_trade_timeline,
    create_trade_summary,
    export_trades_to_excel
)


def quick_check_trades(stock_code, start_date, end_date, seed_money=10_000_000):
    """
    빠르게 거래 내역 확인

    사용법:
        quick_check_trades("005930", "2024-01-01", "2024-12-31")
    """
    print(f"🔍 {stock_code} 거래 내역 분석")
    print(f"   기간: {start_date} ~ {end_date}")
    print(f"   초기 자본: ₩{seed_money:,}")
    print()

    # 1. 설정
    config = BacktestConfiguration(
        seed_money=seed_money,
        stocks=[stock_code],
        date_range=(
            date.fromisoformat(start_date) if isinstance(start_date, str) else start_date,
            date.fromisoformat(end_date) if isinstance(end_date, str) else end_date
        ),
        squeeze_threshold_percent=25  # 조금 낮춰서 거래 기회 증가
    )

    # 2. 데이터 다운로드
    print("📥 데이터 다운로드 중...", end=" ")
    ticker = f"{stock_code}.KS"
    try:
        data = yf.download(ticker, start=start_date, end=end_date, progress=False)
        if data.empty:
            ticker = f"{stock_code}.KQ"
            data = yf.download(ticker, start=start_date, end=end_date, progress=False)

        data.columns = data.columns.get_level_values(0)
        price_data = data[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
        print(f"✅ {len(price_data)}일")

    except Exception as e:
        print(f"❌ 실패: {e}")
        return

    # 3. 백테스트 실행
    print("⏳ 백테스트 실행 중...", end=" ")
    engine = BacktestEngine(config)
    engine.load_mock_data(stock_code, price_data)
    report = engine.run()
    print(f"✅ 완료")

    # 4. 결과 요약
    print("\n" + "=" * 70)
    print("📊 백테스트 요약")
    print("=" * 70)
    print(f"총 거래:       {report.num_trades}회")
    print(f"총 수익률:     {report.total_return_pct:.2f}%")
    print(f"승률:         {report.win_rate_pct:.2f}%")
    print("=" * 70)

    if report.num_trades == 0:
        print("\n⚠️  거래가 발생하지 않았습니다.")
        print("   • 스퀴즈 조건이 충족되지 않았을 수 있습니다")
        print("   • 더 긴 기간으로 시도해보세요")
        print("   • squeeze_threshold_percent를 낮춰보세요 (20%)")
        return None

    # 5. 거래 내역 분석
    stock_data_dict = {stock_code: price_data}

    # 타임라인 (간단)
    create_trade_timeline(engine)

    # 상세 분석 (선택)
    print("\n\n💡 상세 분석을 보시겠습니까? (엔터를 누르면 표시, 's'를 입력하면 건너뛰기): ", end="")
    # user_input = input().strip().lower()
    user_input = ""  # 자동으로 표시

    if user_input != 's':
        analyze_trades_detail(engine, stock_data_dict)
        create_trade_summary(engine)

    # 6. 엑셀 저장 (선택)
    filename = f"{stock_code}_거래내역_{start_date}_{end_date}.xlsx"
    print(f"\n💾 엑셀 파일로 저장하시겠습니까? '{filename}' (y/n): ", end="")
    # save_input = input().strip().lower()
    save_input = "y"  # 자동으로 저장

    if save_input == 'y':
        export_trades_to_excel(engine, filename)

    return engine, report


# ============================================================
# 사용 예제
# ============================================================

if __name__ == "__main__":
    print("\n" + "🔹" * 35)
    print("매수/매도 시점 확인 도구")
    print("🔹" * 35 + "\n")

    # 예제 1: 삼성전자 2024년
    engine, report = quick_check_trades(
        stock_code="005930",
        start_date="2024-01-01",
        end_date="2024-12-31",
        seed_money=10_000_000
    )

    print("\n\n" + "=" * 70)
    print("✅ 분석 완료!")
    print("=" * 70)

    if engine and len(engine.trades) > 0:
        print("\n📋 매수/매도 시점 요약:")
        print()

        buy_count = 0
        sell_count = 0

        for i, trade in enumerate(engine.trades, 1):
            action = "🔴 매수" if trade.action.value == "buy" else "🔵 매도"
            date_str = trade.execution_timestamp.strftime('%Y-%m-%d')

            if trade.action.value == "buy":
                buy_count += 1
                reason = "스퀴즈 돌파" if "squeeze" in (trade.entry_reason or "").lower() else trade.entry_reason
                print(f"{i}. {date_str} {action} @ ₩{trade.execution_price:>8,.0f}  사유: {reason}")
            else:
                sell_count += 1
                reason = {
                    'stop_loss': '손절매',
                    'middle_band_cross': '중간선 돌파',
                }.get(trade.exit_reason, trade.exit_reason or "진입")

                print(f"{i}. {date_str} {action} @ ₩{trade.execution_price:>8,.0f}  사유: {reason}", end="")

                if trade.realized_pnl:
                    pnl_sign = "+" if trade.realized_pnl > 0 else ""
                    pnl_emoji = "✅" if trade.realized_pnl > 0 else "❌"
                    print(f"  {pnl_emoji} {pnl_sign}₩{trade.realized_pnl:>10,.0f}")
                else:
                    print()

        print()
        print(f"총 매수: {buy_count}회, 총 매도: {sell_count}회")

    print("\n💡 팁:")
    print("   • 엑셀 파일을 열어서 더 자세한 정보를 확인하세요")
    print("   • 각 거래의 볼린저 밴드 위치도 확인할 수 있습니다")
    print("   • analyze_trades.py를 실행하면 더 상세한 분석을 볼 수 있습니다")
