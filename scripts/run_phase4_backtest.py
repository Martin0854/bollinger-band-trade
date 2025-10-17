"""
Phase 4 백테스트: ATR 동적 손절매 검증
실제 yfinance 데이터를 사용하여 전체 전략(Volume + RSI + MACD + Confidence + ATR) 성능 평가
"""

import pandas as pd
import yfinance as yf
from datetime import datetime
from src.models.config import BacktestConfiguration
from src.backtest.engine import BacktestEngine
from scripts.analyze_trades import export_trades_to_excel, create_trade_timeline, create_trade_summary

def download_korean_stock_data(ticker_symbol: str, start: str, end: str) -> pd.DataFrame:
    """
    한국 주식 데이터를 yfinance에서 다운로드

    Args:
        ticker_symbol: 종목 코드 (예: "005930.KS")
        start: 시작일 (YYYY-MM-DD)
        end: 종료일 (YYYY-MM-DD)

    Returns:
        OHLCV DataFrame
    """
    print(f"  📥 {ticker_symbol} 데이터 다운로드 중...")
    data = yf.download(ticker_symbol, start=start, end=end, progress=False)

    if data.empty:
        raise ValueError(f"데이터를 다운로드할 수 없습니다: {ticker_symbol}")

    # MultiIndex columns 처리
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    # OHLCV 데이터 정리
    ohlcv = pd.DataFrame({
        'Open': data['Open'],
        'High': data['High'],
        'Low': data['Low'],
        'Close': data['Close'],
        'Volume': data['Volume']
    }).dropna()

    print(f"  ✅ {len(ohlcv)}일 데이터 다운로드 완료")
    return ohlcv


def run_phase4_backtest():
    """Phase 4 백테스트 실행"""
    print("=" * 80)
    print("🚀 Phase 4 백테스트: ATR 동적 손절매 검증")
    print("=" * 80)

    # 1. 설정 파일 로드
    print("\n📋 1단계: 설정 파일 로드")
    config = BacktestConfiguration.from_yaml("config/examples/phase4_dynamic_stop.yaml")

    print(f"\n✅ 설정 로드 완료:")
    print(f"  - 초기 자본: ₩{config.seed_money:,}")
    print(f"  - 종목: {', '.join(config.stocks)}")
    print(f"  - 기간: {config.date_range[0]} ~ {config.date_range[1]}")
    print(f"  - 볼린저 기간: {config.bollinger_period}일")
    print(f"  - 기본 손절매: {config.stop_loss_percent}%")

    # Enhanced Strategy 설정 출력
    if hasattr(config, 'enhanced_strategy') and config.enhanced_strategy:
        print(f"\n  📊 Enhanced Strategy 설정:")
        print(f"    - Volume Filter: {'ON' if config.enhanced_strategy.volume_filter.enabled else 'OFF'}")
        print(f"    - RSI Filter: {'ON' if config.enhanced_strategy.rsi.enabled else 'OFF'}")
        print(f"    - MACD Filter: {'ON' if config.enhanced_strategy.macd.enabled else 'OFF'}")
        print(f"    - ATR Dynamic Stop: {'ON' if config.enhanced_strategy.atr.enabled else 'OFF'}")
        if config.enhanced_strategy.atr.enabled:
            print(f"      → ATR Period: {config.enhanced_strategy.atr.period}일")
            print(f"      → ATR Multiplier: {config.enhanced_strategy.atr.multiplier}x")
        print(f"    - Confidence Threshold: {config.enhanced_strategy.confidence.threshold}점")

    # 2. 데이터 다운로드
    print(f"\n📥 2단계: 실제 주가 데이터 다운로드")

    # 종목 코드 매핑 (6자리 코드 → yfinance 티커)
    ticker_mapping = {
        "005930": "005930.KS",  # 삼성전자
        "000660": "000660.KS",  # SK하이닉스
        "035420": "035420.KS",  # NAVER
        "005380": "005380.KS",  # 현대차
        "051910": "051910.KS",  # LG화학
    }

    stock_data = {}
    for stock_code in config.stocks:
        ticker = ticker_mapping.get(stock_code)
        if not ticker:
            print(f"  ⚠️  종목 코드 {stock_code}의 티커를 찾을 수 없습니다. 건너뜁니다.")
            continue

        try:
            ohlcv = download_korean_stock_data(
                ticker_symbol=ticker,
                start=str(config.date_range[0]),
                end=str(config.date_range[1])
            )
            stock_data[stock_code] = ohlcv
        except Exception as e:
            print(f"  ❌ {stock_code} 데이터 다운로드 실패: {e}")

    if not stock_data:
        print("\n❌ 다운로드된 데이터가 없습니다. 종료합니다.")
        return

    # 3. 백테스트 엔진 초기화
    print(f"\n⚙️  3단계: 백테스트 엔진 초기화")
    engine = BacktestEngine(config=config)

    # 데이터 로드
    for stock_code, ohlcv in stock_data.items():
        engine.load_mock_data(stock_code, ohlcv)
        print(f"  ✅ {stock_code} 데이터 로드 완료")

    # 4. 백테스트 실행
    print(f"\n🏃 4단계: 백테스트 실행 중...")
    report = engine.run()

    # 5. 결과 출력
    print("\n" + "=" * 80)
    print("📊 백테스트 결과 요약")
    print("=" * 80)

    print(f"\n💰 수익 지표:")
    print(f"  - 총 수익률:        {report.total_return_pct:+.2f}%")
    print(f"  - 연환산 수익률:    {report.cagr_pct:+.2f}% (CAGR)")
    final_capital = config.seed_money * (1 + float(report.total_return_pct) / 100)
    print(f"  - 최종 자본:        ₩{final_capital:,.0f}")
    print(f"  - 최대 낙폭:        {report.max_drawdown_pct:.2f}%")

    print(f"\n📈 거래 지표:")
    print(f"  - 총 거래 횟수:     {report.num_trades}회")
    print(f"  - 승률:            {report.win_rate_pct:.2f}%")
    print(f"  - 수익 거래:        {report.num_winning_trades}회")
    print(f"  - 손실 거래:        {report.num_losing_trades}회")

    if report.num_trades > 0:
        print(f"\n💹 평균 수익:")
        print(f"  - 평균 수익 거래:   ₩{report.avg_win:+,.0f}")
        print(f"  - 평균 손실 거래:   ₩{report.avg_loss:+,.0f}")
        if report.win_loss_ratio:
            print(f"  - 손익비:          {report.win_loss_ratio:.2f}")
        if report.profit_factor:
            print(f"  - Profit Factor:   {report.profit_factor:.2f}")

    if report.sharpe_ratio:
        print(f"\n📊 리스크 조정 수익률:")
        print(f"  - Sharpe Ratio:    {report.sharpe_ratio:.2f}")

    print("\n" + "=" * 80)

    # 6. ATR 관련 통계 분석
    print("\n" + "=" * 80)
    print("🎯 ATR 동적 손절매 분석")
    print("=" * 80)

    atr_trades = [t for t in engine.trades if t.stop_loss_type == "ATR_DYNAMIC"]
    fixed_trades = [t for t in engine.trades if t.stop_loss_type == "FIXED"]

    print(f"\n손절 유형별 거래:")
    print(f"  - ATR 동적 손절:    {len(atr_trades)}회")
    print(f"  - 고정 손절:        {len(fixed_trades)}회")

    if atr_trades:
        atr_values = [t.atr_value for t in atr_trades if t.atr_value is not None]
        if atr_values:
            print(f"\nATR 값 통계:")
            print(f"  - 평균 ATR:        {sum(atr_values)/len(atr_values):,.2f}")
            print(f"  - 최소 ATR:        {min(atr_values):,.2f}")
            print(f"  - 최대 ATR:        {max(atr_values):,.2f}")

        # 손절 발동 분석
        atr_stop_losses = [t for t in atr_trades if t.exit_reason == "stop_loss"]
        print(f"\nATR 손절 발동:")
        print(f"  - ATR 손절 발동:   {len(atr_stop_losses)}회")
        if atr_trades:
            print(f"  - 손절 비율:        {len(atr_stop_losses)/len(atr_trades)*100:.1f}%")

    print("\n" + "=" * 80)

    # 7. 거래 내역 출력
    if report.num_trades > 0:
        print("\n📅 거래 타임라인:")
        create_trade_timeline(engine)

        print("\n📊 거래 요약 통계:")
        create_trade_summary(engine)

        # 8. Excel 저장
        print("\n💾 Excel 파일 저장 중...")
        filename = f"phase4_backtest_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        try:
            export_trades_to_excel(engine, filename)
            print(f"  ✅ 파일 저장 완료: {filename}")
            print(f"\n  📋 Excel 파일에는 다음 컬럼이 포함됩니다:")
            print(f"    - 기본 거래 정보 (날짜, 시간, 종목, 가격, 수량 등)")
            print(f"    - 볼린저 밴드 값 (상단, 중간, 하단, 대역폭)")
            print(f"    - 신뢰도 점수 및 필터 통과 여부 (거래량, RSI, MACD)")
            print(f"    - ATR 값, 동적손절가, 손절유형 ✨ NEW!")
        except Exception as e:
            print(f"  ❌ Excel 저장 실패: {e}")
    else:
        print("\n⚠️  거래가 발생하지 않았습니다.")
        print("\n💡 거래가 없는 이유:")
        print("  - 신뢰도 임계값이 너무 높을 수 있습니다 (현재: 60점)")
        print("  - 필터 조건이 너무 엄격할 수 있습니다")
        print("  - 백테스트 기간 동안 스퀴즈 신호가 없었을 수 있습니다")
        print("\n💡 해결 방법:")
        print("  - confidence.threshold를 50으로 낮춰보세요")
        print("  - squeeze_threshold_percent를 낮춰보세요 (예: 30)")
        print("  - 더 긴 백테스트 기간을 설정해보세요")

    print("\n" + "=" * 80)
    print("✅ 백테스트 완료!")
    print("=" * 80)


if __name__ == "__main__":
    try:
        run_phase4_backtest()
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
