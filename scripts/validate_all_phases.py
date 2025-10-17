"""
T074: 전체 quickstart.md 검증
모든 4개 Phase의 목표 메트릭 달성 여부 확인
"""

import pandas as pd
import yfinance as yf
from datetime import datetime
from src.models.config import BacktestConfiguration
from src.backtest.engine import BacktestEngine
from typing import Dict, Tuple

# 검증 기준
PHASE_TARGETS = {
    'Phase 1 (Volume+RSI)': {
        'config': 'config/examples/phase1_volume_rsi.yaml',
        'win_rate_min': 55.0,
        'win_rate_max': 60.0,
        'return_min': 5.0,
        'return_max': 8.0
    },
    'Phase 2 (MACD)': {
        'config': 'config/examples/phase2_with_macd.yaml',
        'win_rate_min': 70.0,
        'win_rate_max': 75.0,
        'return_min': 10.0,
        'return_max': 15.0
    },
    'Phase 3 (Confidence)': {
        'config': 'config/examples/phase3_confidence.yaml',
        'win_rate_min': 70.0,
        'win_rate_max': 75.0,
        'return_min': 10.0,
        'return_max': 15.0
    },
    'Phase 4 (ATR)': {
        'config': 'config/examples/phase4_test.yaml',  # 테스트용 완화 설정
        'win_rate_min': 70.0,
        'win_rate_max': 75.0,
        'return_min': 15.0,
        'return_max': 20.0
    }
}

# KOSPI Top 10
KOSPI_TOP10 = {
    '005930': '삼성전자',
    '000660': 'SK하이닉스',
    '005380': '현대차',
    '051910': 'LG화학',
    '035420': 'NAVER',
    '068270': '셀트리온',
    '035720': '카카오',
    '028260': '삼성물산',
    '105560': 'KB금융',
    '055550': '신한지주'
}


def download_data(stocks: list, start: str, end: str) -> Dict[str, pd.DataFrame]:
    """주식 데이터 다운로드"""
    stock_data = {}

    for code in stocks:
        try:
            ticker = f'{code}.KS'
            data = yf.download(ticker, start=start, end=end, progress=False)
            if not data.empty:
                if isinstance(data.columns, pd.MultiIndex):
                    data.columns = data.columns.get_level_values(0)
                ohlcv = pd.DataFrame({
                    'Open': data['Open'],
                    'High': data['High'],
                    'Low': data['Low'],
                    'Close': data['Close'],
                    'Volume': data['Volume']
                }).dropna()
                stock_data[code] = ohlcv
        except Exception as e:
            print(f'  ⚠️  {code}: {e}')

    return stock_data


def run_phase_backtest(phase_name: str, config_path: str, stock_data: Dict[str, pd.DataFrame]) -> Tuple[bool, dict]:
    """특정 Phase 백테스트 실행 및 검증"""
    print(f'\n{"="*80}')
    print(f'🔍 {phase_name} 검증')
    print(f'{"="*80}')

    try:
        # 설정 로드
        config = BacktestConfiguration.from_yaml(config_path)
        config.stocks = list(stock_data.keys())
        config.max_positions = 10

        # 백테스트 실행
        print(f'⏳ 백테스트 실행 중...')
        engine = BacktestEngine(config=config)
        for code, ohlcv in stock_data.items():
            engine.load_mock_data(code, ohlcv)

        report = engine.run()

        # 결과 출력
        print(f'\n📊 결과:')
        print(f'  총 거래:     {report.num_trades}회')
        print(f'  승률:       {report.win_rate_pct:.2f}%')
        print(f'  총 수익률:   {report.total_return_pct:+.2f}%')
        print(f'  CAGR:       {report.cagr_pct:+.2f}%')
        print(f'  Sharpe:     {report.sharpe_ratio:.2f}')

        # 목표 대비 검증
        targets = PHASE_TARGETS[phase_name]

        results = {
            'trades': report.num_trades,
            'win_rate': float(report.win_rate_pct),
            'total_return': float(report.total_return_pct),
            'cagr': float(report.cagr_pct),
            'sharpe': report.sharpe_ratio,
            'max_drawdown': float(report.max_drawdown_pct)
        }

        # 검증 (거래가 있을 때만)
        if report.num_trades == 0:
            print(f'\n⚠️  거래가 없어서 검증할 수 없습니다.')
            return False, results

        win_rate_ok = targets['win_rate_min'] <= results['win_rate'] <= targets['win_rate_max']
        return_ok = results['cagr'] >= targets['return_min']  # CAGR 기준

        print(f'\n✅ 검증 결과:')
        print(f'  승률 목표: {targets["win_rate_min"]:.0f}-{targets["win_rate_max"]:.0f}%')
        print(f'  승률 실제: {results["win_rate"]:.2f}% {"✓" if win_rate_ok else "✗"}')
        print(f'  수익 목표: {targets["return_min"]:.0f}%+')
        print(f'  수익 실제: {results["cagr"]:.2f}% {"✓" if return_ok else "✗"}')

        passed = win_rate_ok and return_ok

        if passed:
            print(f'\n🎉 {phase_name} 검증 통과!')
        else:
            print(f'\n⚠️  {phase_name} 목표 미달성')

        return passed, results

    except Exception as e:
        print(f'\n❌ 오류 발생: {e}')
        import traceback
        traceback.print_exc()
        return False, {}


def main():
    """전체 Phase 검증 실행"""
    print('='*80)
    print('🚀 전체 Phase 검증 (T074)')
    print('='*80)

    # 데이터 다운로드
    print(f'\n📥 KOSPI Top 10 데이터 다운로드 중 (2023년)...')
    stock_data = download_data(list(KOSPI_TOP10.keys()), '2023-01-01', '2023-12-31')
    print(f'✅ {len(stock_data)}개 종목 다운로드 완료')

    # 각 Phase 검증
    results = {}

    for phase_name, config_info in PHASE_TARGETS.items():
        passed, metrics = run_phase_backtest(phase_name, config_info['config'], stock_data)
        results[phase_name] = {
            'passed': passed,
            'metrics': metrics
        }

    # 전체 결과 요약
    print(f'\n{"="*80}')
    print(f'📊 전체 검증 결과 요약')
    print(f'{"="*80}')

    total_phases = len(PHASE_TARGETS)
    passed_phases = sum(1 for r in results.values() if r['passed'])

    for phase_name, result in results.items():
        status = '✅ PASS' if result['passed'] else '❌ FAIL'
        metrics = result['metrics']
        if metrics:
            print(f'\n{status} {phase_name}')
            print(f'  승률: {metrics.get("win_rate", 0):.2f}%, 수익률: {metrics.get("cagr", 0):.2f}%')
        else:
            print(f'\n❌ {phase_name} - 실행 실패')

    print(f'\n{"="*80}')
    print(f'최종 결과: {passed_phases}/{total_phases} Phase 통과')

    if passed_phases == total_phases:
        print(f'🎉 모든 Phase 검증 통과!')
    else:
        print(f'⚠️  일부 Phase 목표 미달성')

    print(f'{"="*80}')

    return passed_phases == total_phases


if __name__ == '__main__':
    import sys
    success = main()
    sys.exit(0 if success else 1)
