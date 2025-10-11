"""
거래 내역 상세 분석 도구
언제, 왜 매수/매도가 발생했는지 자세히 확인
"""

import pandas as pd
import yfinance as yf
from datetime import date
from src.models.config import BacktestConfiguration
from src.backtest.engine import BacktestEngine


def analyze_trades_detail(engine, stock_data_dict):
    """
    거래 내역을 상세하게 분석하고 출력

    Args:
        engine: BacktestEngine 인스턴스 (백테스트 실행 후)
        stock_data_dict: {종목코드: DataFrame} 가격 데이터
    """
    if len(engine.trades) == 0:
        print("❌ 거래 내역이 없습니다.")
        return

    print("\n" + "=" * 80)
    print("📊 거래 내역 상세 분석")
    print("=" * 80)

    # 매수/매도 분리
    buy_trades = [t for t in engine.trades if t.action.value == "buy"]
    sell_trades = [t for t in engine.trades if t.action.value == "sell"]

    print(f"\n총 거래: {len(engine.trades)}회")
    print(f"  - 매수: {len(buy_trades)}회")
    print(f"  - 매도: {len(sell_trades)}회")

    # 각 거래 상세 분석
    for i, trade in enumerate(engine.trades, 1):
        print("\n" + "-" * 80)
        print(f"거래 #{i}")
        print("-" * 80)

        # 기본 정보
        action_ko = "🔴 매수" if trade.action.value == "buy" else "🔵 매도"
        print(f"{action_ko}")
        print(f"종목:         {trade.stock_code}")
        print(f"날짜:         {trade.execution_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"가격:         ₩{trade.execution_price:,.0f}")
        print(f"수량:         {trade.quantity}주")
        print(f"거래금액:     ₩{trade.execution_price * trade.quantity:,.0f}")

        # 매수/매도 사유
        if trade.entry_reason:
            reason_ko = {
                'squeeze_breakout_buy': '스퀴즈 돌파 (상단 밴드 돌파)',
                'squeeze_expansion_buy': '스퀴즈 확장',
                'breakout': '돌파 신호'
            }.get(trade.entry_reason, trade.entry_reason)
            print(f"진입 사유:    {reason_ko}")

        if trade.exit_reason:
            reason_ko = {
                'stop_loss': '손절매 (5% 손실)',
                'middle_band_cross': '중간선 하향 돌파',
                'band_upper_exit': '상단 밴드 도달 (익절)',
                'trailing_stop': '추적 손절'
            }.get(trade.exit_reason, trade.exit_reason)
            print(f"청산 사유:    {reason_ko}")

        # 볼린저 밴드 정보
        print(f"\n볼린저 밴드 (거래 시점):")
        print(f"  상단 밴드:  ₩{trade.bollinger_values['upper']:,.0f}")
        print(f"  중간선:     ₩{trade.bollinger_values['middle']:,.0f}")
        print(f"  하단 밴드:  ₩{trade.bollinger_values['lower']:,.0f}")
        print(f"  대역폭:     {trade.band_width_at_entry * 100:.2f}%")

        # 포트폴리오 상태
        print(f"\n포트폴리오 상태:")
        print(f"  거래 전:    ₩{trade.portfolio_value_before:,.0f}")
        print(f"  거래 후:    ₩{trade.portfolio_value_after:,.0f}")
        print(f"  현금:       ₩{trade.cash_after:,.0f}")

        # 손익 (매도인 경우)
        if trade.realized_pnl is not None:
            pnl_sign = "+" if trade.realized_pnl > 0 else ""
            pnl_color = "✅" if trade.realized_pnl > 0 else "❌"
            print(f"\n{pnl_color} 실현 손익:  {pnl_sign}₩{trade.realized_pnl:,.0f}")

            # 수익률 계산
            if len(buy_trades) > 0:
                # 이전 매수 찾기
                matching_buy = None
                for buy in reversed(buy_trades):
                    if buy.stock_code == trade.stock_code and buy.execution_timestamp < trade.execution_timestamp:
                        matching_buy = buy
                        break

                if matching_buy:
                    holding_days = (trade.execution_timestamp - matching_buy.execution_timestamp).days
                    pnl_pct = (trade.realized_pnl / (matching_buy.execution_price * matching_buy.quantity)) * 100

                    print(f"보유 기간:    {holding_days}일")
                    print(f"수익률:       {pnl_pct:+.2f}%")
                    print(f"매수가:       ₩{matching_buy.execution_price:,.0f}")
                    print(f"매도가:       ₩{trade.execution_price:,.0f}")

        # 해당 날짜의 시장 상황
        if trade.stock_code in stock_data_dict:
            stock_data = stock_data_dict[trade.stock_code]
            trade_date = trade.execution_timestamp.date()

            if trade_date in stock_data.index.date:
                day_data = stock_data[stock_data.index.date == trade_date].iloc[0]

                print(f"\n📈 시장 상황 (당일):")
                print(f"  시가:       ₩{day_data['Open']:,.0f}")
                print(f"  고가:       ₩{day_data['High']:,.0f}")
                print(f"  저가:       ₩{day_data['Low']:,.0f}")
                print(f"  종가:       ₩{day_data['Close']:,.0f}")
                print(f"  거래량:     {day_data['Volume']:,.0f}주")

                # 변동성
                day_volatility = ((day_data['High'] - day_data['Low']) / day_data['Close']) * 100
                print(f"  일일 변동성: {day_volatility:.2f}%")

    print("\n" + "=" * 80)


def create_trade_timeline(engine):
    """거래 타임라인 생성"""
    if len(engine.trades) == 0:
        return

    print("\n" + "=" * 80)
    print("📅 거래 타임라인")
    print("=" * 80)

    # 날짜순으로 정렬
    sorted_trades = sorted(engine.trades, key=lambda t: t.execution_timestamp)

    for trade in sorted_trades:
        date_str = trade.execution_timestamp.strftime('%Y-%m-%d')
        action = "매수" if trade.action.value == "buy" else "매도"
        action_symbol = "🔴" if action == "매수" else "🔵"

        print(f"{date_str} {action_symbol} {action:4s} [{trade.stock_code}] "
              f"{trade.quantity:3d}주 @ ₩{trade.execution_price:>8,.0f}", end="")

        if trade.realized_pnl:
            pnl_sign = "+" if trade.realized_pnl > 0 else ""
            print(f"  손익: {pnl_sign}₩{trade.realized_pnl:,.0f}")
        else:
            reason = trade.entry_reason or ""
            if "squeeze" in reason.lower():
                print(f"  (스퀴즈 돌파)")
            else:
                print()


def create_trade_summary(engine):
    """거래 요약 통계"""
    if len(engine.trades) == 0:
        return

    print("\n" + "=" * 80)
    print("📊 거래 요약 통계")
    print("=" * 80)

    # 종목별 통계
    stock_trades = {}
    for trade in engine.trades:
        if trade.stock_code not in stock_trades:
            stock_trades[trade.stock_code] = []
        stock_trades[trade.stock_code].append(trade)

    print(f"\n종목별 거래 횟수:")
    for stock_code, trades in stock_trades.items():
        buy_count = sum(1 for t in trades if t.action.value == "buy")
        sell_count = sum(1 for t in trades if t.action.value == "sell")
        print(f"  {stock_code}: 매수 {buy_count}회, 매도 {sell_count}회")

    # 시간대별 통계
    print(f"\n시간대별 거래:")
    hour_counts = {}
    for trade in engine.trades:
        hour = trade.execution_timestamp.hour
        hour_counts[hour] = hour_counts.get(hour, 0) + 1

    for hour in sorted(hour_counts.keys()):
        print(f"  {hour:02d}:00 ~ {hour:02d}:59: {hour_counts[hour]}회")

    # 요일별 통계
    print(f"\n요일별 거래:")
    weekday_names = ['월', '화', '수', '목', '금', '토', '일']
    weekday_counts = {day: 0 for day in weekday_names}

    for trade in engine.trades:
        weekday = weekday_names[trade.execution_timestamp.weekday()]
        weekday_counts[weekday] += 1

    for day, count in weekday_counts.items():
        if count > 0:
            print(f"  {day}요일: {count}회")

    # 손익 거래 분석
    profitable_trades = [t for t in engine.trades if t.realized_pnl and t.realized_pnl > 0]
    losing_trades = [t for t in engine.trades if t.realized_pnl and t.realized_pnl < 0]

    if profitable_trades or losing_trades:
        print(f"\n손익 거래 분석:")
        print(f"  수익 거래: {len(profitable_trades)}회 (평균: ₩{sum(t.realized_pnl for t in profitable_trades) / len(profitable_trades) if profitable_trades else 0:,.0f})")
        print(f"  손실 거래: {len(losing_trades)}회 (평균: ₩{sum(t.realized_pnl for t in losing_trades) / len(losing_trades) if losing_trades else 0:,.0f})")

    print("=" * 80)


def export_trades_to_excel(engine, filename="거래내역.xlsx"):
    """거래 내역을 엑셀로 저장"""
    if len(engine.trades) == 0:
        print("❌ 거래 내역이 없어 엑셀 파일을 생성할 수 없습니다.")
        return

    # DataFrame 생성
    trades_data = []
    for trade in engine.trades:
        trades_data.append({
            '날짜': trade.execution_timestamp.strftime('%Y-%m-%d'),
            '시간': trade.execution_timestamp.strftime('%H:%M:%S'),
            '종목코드': trade.stock_code,
            '매매구분': '매수' if trade.action.value == "buy" else '매도',
            '가격': int(trade.execution_price),
            '수량': trade.quantity,
            '거래금액': int(trade.execution_price * trade.quantity),
            '진입사유': trade.entry_reason or '',
            '청산사유': trade.exit_reason or '',
            '실현손익': int(trade.realized_pnl) if trade.realized_pnl else 0,
            '상단밴드': int(trade.bollinger_values['upper']),
            '중간선': int(trade.bollinger_values['middle']),
            '하단밴드': int(trade.bollinger_values['lower']),
            '대역폭': float(trade.band_width_at_entry),
            '포트폴리오(전)': int(trade.portfolio_value_before),
            '포트폴리오(후)': int(trade.portfolio_value_after),
            '현금잔고': int(trade.cash_after)
        })

    df = pd.DataFrame(trades_data)
    df.to_excel(filename, index=False, engine='openpyxl')
    print(f"\n✅ 거래 내역이 '{filename}' 파일로 저장되었습니다.")


# ============================================================
# 예제 실행
# ============================================================

if __name__ == "__main__":
    print("🚀 거래 내역 상세 분석 예제")
    print("=" * 80)

    # 1. 백테스트 실행
    config = BacktestConfiguration(
        seed_money=10_000_000,
        stocks=["005930"],
        date_range=(date(2024, 1, 1), date(2024, 12, 31)),
        bollinger_period=20,
        squeeze_threshold_percent=25,  # 낮춰서 더 많은 거래 생성
        stop_loss_percent=5.0
    )

    # 실제 데이터 다운로드
    print("\n📥 데이터 다운로드 중...")
    ticker = "005930.KS"
    stock_data = yf.download(ticker, start="2024-01-01", end="2024-12-31", progress=False)

    stock_data.columns = stock_data.columns.get_level_values(0)
    price_data = pd.DataFrame({
        'Open': stock_data['Open'],
        'High': stock_data['High'],
        'Low': stock_data['Low'],
        'Close': stock_data['Close'],
        'Volume': stock_data['Volume']
    }).dropna()

    print(f"✅ {len(price_data)}일 데이터 다운로드 완료")

    # 백테스트 실행
    print("\n⏳ 백테스트 실행 중...")
    engine = BacktestEngine(config=config)
    engine.load_mock_data("005930", price_data)
    report = engine.run()

    print(f"\n✅ 백테스트 완료: {report.num_trades}회 거래 실행")

    # 2. 거래 내역 상세 분석
    if report.num_trades > 0:
        stock_data_dict = {"005930": price_data}

        # 상세 분석
        analyze_trades_detail(engine, stock_data_dict)

        # 타임라인
        create_trade_timeline(engine)

        # 요약 통계
        create_trade_summary(engine)

        # 엑셀 저장
        try:
            export_trades_to_excel(engine, "삼성전자_거래내역_2024.xlsx")
        except ImportError:
            print("\n⚠️  openpyxl이 설치되지 않아 엑셀 저장을 건너뜁니다.")
            print("   설치: poetry add openpyxl")
    else:
        print("\n⚠️  거래가 발생하지 않았습니다.")
        print("   팁: squeeze_threshold_percent를 더 낮춰보세요 (예: 20%)")
