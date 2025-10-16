#!/usr/bin/env python3
"""
KOSPI 100 백테스트 - Yahoo Finance 실제 데이터 사용
Phase 3 Confidence Scoring 시스템으로 실제 시장 데이터 백테스트
"""

import pandas as pd
import numpy as np
from datetime import datetime
import pytz
import yaml
import sys
from pathlib import Path
import yfinance as yf
from typing import Optional

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.config import BacktestConfiguration
from src.backtest.engine import BacktestEngine
from scripts.analyze_trades import export_trades_to_excel


def load_stock_codes(filename: str = "data/kospi_top100.txt") -> list:
    """
    텍스트 파일에서 종목 코드 로드

    Args:
        filename: 종목 코드 파일 경로 (기본: data/kospi_top100.txt)

    Returns:
        종목 코드 리스트

    파일 형식:
        # 주석
        005930  # 삼성전자
        000660  # SK하이닉스
    """
    stock_codes = []
    file_path = project_root / filename

    if not file_path.exists():
        print(f"⚠️  종목 파일을 찾을 수 없습니다: {file_path}")
        print(f"   기본 종목 사용")
        return ["005930", "000660", "005380"]  # 기본 3개

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                # 주석 제거 및 공백 제거
                line = line.split('#')[0].strip()

                # 빈 줄 건너뛰기
                if not line:
                    continue

                # 6자리 숫자인지 확인
                if line.isdigit() and len(line) == 6:
                    stock_codes.append(line)
                else:
                    print(f"⚠️  잘못된 종목 코드 건너뜀: {line}")

        print(f"✅ {len(stock_codes)}개 종목 코드 로드 완료: {file_path}")
        return stock_codes

    except Exception as e:
        print(f"❌ 종목 파일 읽기 오류: {e}")
        return ["005930", "000660", "005380"]  # 기본 3개


def download_stock_data(stock_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
    """
    Yahoo Finance에서 한국 주식 데이터 다운로드

    Args:
        stock_code: 6자리 종목 코드 (예: "005930")
        start_date: 시작일 (YYYY-MM-DD)
        end_date: 종료일 (YYYY-MM-DD)

    Returns:
        OHLCV 데이터프레임 (Asia/Seoul 시간대) 또는 None
    """
    try:
        # Yahoo Finance 티커 형식: 종목코드.KS
        ticker = f"{stock_code}.KS"

        print(f"   다운로드 중: {stock_code} ({ticker})...", end=" ")

        # 데이터 다운로드
        stock = yf.Ticker(ticker)
        df = stock.history(start=start_date, end=end_date)

        if df.empty:
            print(f"❌ 데이터 없음")
            return None

        # 컬럼명 표준화
        df = df.rename(columns={
            'Open': 'Open',
            'High': 'High',
            'Low': 'Low',
            'Close': 'Close',
            'Volume': 'Volume'
        })

        # 필요한 컬럼만 선택
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']]

        # 시간대 설정 (Asia/Seoul)
        if df.index.tz is None:
            df.index = df.index.tz_localize('UTC').tz_convert('Asia/Seoul')
        else:
            df.index = df.index.tz_convert('Asia/Seoul')

        print(f"✓ {len(df)}일")
        return df

    except Exception as e:
        print(f"❌ 오류: {str(e)}")
        return None


def main():
    """메인 실행 함수"""
    print("=" * 80)
    print("KOSPI 100 백테스트 - Yahoo Finance 실제 데이터")
    print("=" * 80)

    # 종목 코드 로드
    print(f"\n📁 종목 코드 로드 중...")
    kospi_stocks = load_stock_codes("data/kospi_top100.txt")

    if not kospi_stocks:
        print("❌ 종목 코드를 로드할 수 없습니다. 종료합니다.")
        return

    # 설정 로드
    config_path = project_root / "config/examples/phase3_confidence.yaml"
    print(f"📁 설정 파일 로드: {config_path}")

    with open(config_path, 'r') as f:
        config_dict = yaml.safe_load(f)

    # 로드된 종목으로 교체 (처음 50개만 사용)
    config_dict['stocks'] = kospi_stocks[:100]
    config_dict['max_positions'] = 20

    # date_range 변환
    if 'date_range' in config_dict and isinstance(config_dict['date_range'], dict):
        start_date = config_dict['date_range']['start']
        end_date = config_dict['date_range']['end']
        config_dict['date_range'] = (start_date, end_date)
    else:
        start_date, end_date = config_dict['date_range']

    config = BacktestConfiguration(**config_dict)

    print(f"\n✅ 백테스트 설정:")
    print(f"   초기 자본:        ₩{config.seed_money:,}")
    print(f"   종목 수:          {len(config.stocks)}개")
    print(f"   최대 보유:        {config.max_positions}개")
    print(f"   기간:            {start_date} ~ {end_date}")
    print(f"   Volume Filter:   {config.enhanced_strategy.volume_filter.enabled}")
    print(f"   RSI Filter:      {config.enhanced_strategy.rsi.enabled}")
    print(f"   MACD Filter:     {config.enhanced_strategy.macd.enabled}")
    print(f"   Confidence:      {config.enhanced_strategy.confidence.threshold}/100")

    # 엔진 초기화
    engine = BacktestEngine(config=config)

    # Yahoo Finance에서 실제 데이터 다운로드
    print(f"\n📊 Yahoo Finance에서 데이터 다운로드 중...")
    print(f"   기간: {start_date} ~ {end_date}")
    print(f"   종목: {len(config.stocks)}개")
    print()

    downloaded_count = 0
    failed_stocks = []

    for idx, stock_code in enumerate(config.stocks):
        # 데이터 다운로드
        df = download_stock_data(stock_code, start_date, end_date)

        if df is not None and len(df) > 0:
            # 엔진에 데이터 로드
            engine.load_mock_data(stock_code, df)
            downloaded_count += 1
        else:
            failed_stocks.append(stock_code)

        # 진행 상황 표시
        if (idx + 1) % 10 == 0:
            print(f"\n   진행: {idx + 1}/{len(config.stocks)} 종목 처리 완료")

    print(f"\n{'=' * 80}")
    print(f"✅ 데이터 다운로드 완료:")
    print(f"   성공: {downloaded_count}개")
    print(f"   실패: {len(failed_stocks)}개")

    if failed_stocks:
        print(f"\n   실패 종목: {', '.join(failed_stocks[:10])}")
        if len(failed_stocks) > 10:
            print(f"   ... 외 {len(failed_stocks) - 10}개")

    if downloaded_count == 0:
        print("\n❌ 다운로드된 데이터가 없습니다. 종료합니다.")
        return

    # 백테스트 실행
    print(f"\n{'=' * 80}")
    print(f"⚙️  백테스트 실행 중...")
    print(f"   {downloaded_count}개 종목 분석 중...")
    print(f"   이 작업은 수 분 소요될 수 있습니다...")

    report = engine.run()

    # 결과 출력
    print("\n" + "=" * 80)
    print("📊 백테스트 결과")
    print("=" * 80)
    print(f"총 수익률:                {report.total_return_pct:>12.2f}%")
    print(f"승률:                    {report.win_rate_pct:>12.2f}%")
    print(f"총 거래:                 {report.num_trades:>12}회")

    if hasattr(report, 'num_winning_trades'):
        print(f"승리 거래:               {report.num_winning_trades:>12}회")
        print(f"패배 거래:               {report.num_losing_trades:>12}회")

    print("=" * 80)

    # 거래 분석
    if len(engine.trades) > 0:
        print(f"\n📈 거래 분석:")
        print("-" * 80)

        # 종목별 통계
        stock_trades = {}
        for trade in engine.trades:
            if trade.stock_code not in stock_trades:
                stock_trades[trade.stock_code] = []
            stock_trades[trade.stock_code].append(trade)

        print(f"\n거래 발생 종목: {len(stock_trades)}개")
        print(f"거래가 없는 종목: {downloaded_count - len(stock_trades)}개")

        print(f"\n종목별 거래 수 (Top 10):")
        for stock, trades in sorted(stock_trades.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
            print(f"  {stock}: {len(trades):2}건")

        # 신뢰도 점수 분석
        buy_trades = [t for t in engine.trades if t.action.value == "buy"]
        if buy_trades:
            confidence_scores = [t.confidence_score for t in buy_trades if t.confidence_score is not None]
            if confidence_scores:
                print(f"\n신뢰도 점수 통계:")
                print(f"  평균: {np.mean(confidence_scores):.1f}/100")
                print(f"  최대: {np.max(confidence_scores)}/100")
                print(f"  최소: {np.min(confidence_scores)}/100")

        # Excel 내보내기
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        excel_filename = f"backtest_real_data_{start_date}_{end_date}_{timestamp}.xlsx"
        excel_path = project_root / "results" / excel_filename

        print(f"\n💾 결과 저장 중...")
        export_trades_to_excel(engine, filename=str(excel_path))
        print(f"   ✓ Excel 파일 저장: {excel_path}")

        # 상세 거래 내역 (최근 20건)
        print(f"\n📝 거래 상세 (최근 20건):")
        print("-" * 80)

        for i, trade in enumerate(engine.trades[:20], 1):
            print(f"\n[{i}] {trade.action.value.upper()} - {trade.stock_code}")
            print(f"    날짜: {trade.execution_timestamp.strftime('%Y-%m-%d %H:%M')}")
            print(f"    가격: ₩{int(trade.execution_price):,}")
            print(f"    수량: {trade.quantity:,}주")

            if trade.confidence_score is not None:
                print(f"    신뢰도: {trade.confidence_score}/100 점")
                filters = []
                if trade.volume_pass: filters.append("거래량")
                if trade.rsi_pass: filters.append("RSI")
                if trade.macd_pass: filters.append("MACD")
                print(f"    통과 필터: {', '.join(filters) if filters else '기본만'}")

            if trade.realized_pnl:
                color = "🟢" if trade.realized_pnl > 0 else "🔴"
                print(f"    {color} 실현손익: ₩{int(trade.realized_pnl):+,}")

        if len(engine.trades) > 20:
            print(f"\n... 외 {len(engine.trades) - 20}건 (Excel 파일 참조)")

    else:
        print("\n⚠️  거래가 발생하지 않았습니다.")
        print("   필터 조건이 매우 엄격하거나 백테스트 기간에 조건을 만족하는 신호가 없습니다.")
        print("   다음을 시도해보세요:")
        print("   - config 파일에서 confidence.threshold를 낮추기 (60 → 50)")
        print("   - 백테스트 기간을 늘리기 (1년 → 2-3년)")
        print("   - 일부 필터 비활성화 (MACD enabled: false)")

    print("\n" + "=" * 80)
    print("✅ Yahoo Finance 실제 데이터 백테스트 완료")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
