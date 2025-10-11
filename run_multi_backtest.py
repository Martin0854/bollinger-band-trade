"""
다중 종목 백테스트 실행
코스피 상위 100종목에 대해 백테스트를 실행하고 결과를 집계합니다.
"""

import yfinance as yf
import pandas as pd
from datetime import date
from decimal import Decimal
from typing import List, Dict, Tuple
import time
from src.models.config import BacktestConfiguration
from src.backtest.engine import BacktestEngine


# 종목 코드 -> 한글 이름 매핑
STOCK_NAMES = {
    "005930": "삼성전자", "000660": "SK하이닉스", "373220": "LG에너지솔루션",
    "207940": "삼성바이오로직스", "005490": "POSCO홀딩스", "005380": "현대차",
    "006400": "삼성SDI", "051910": "LG화학", "035420": "NAVER",
    "000270": "기아", "068270": "셀트리온", "105560": "KB금융",
    "055550": "신한지주", "035720": "카카오", "012330": "현대모비스",
    "028260": "삼성물산", "066570": "LG전자", "003670": "포스코퓨처엠",
    "323410": "카카오뱅크", "086790": "하나금융지주", "096770": "SK이노베이션",
    "009150": "삼성전기", "017670": "SK텔레콤", "033780": "KT&G",
    "015760": "한국전력", "034730": "SK", "000810": "삼성화재",
    "032830": "삼성생명", "018260": "삼성에스디에스", "003550": "LG",
    "030200": "KT", "010950": "S-Oil", "011070": "LG이노텍",
    "086280": "현대글로비스", "009540": "한국조선해양", "028050": "삼성엔지니어링",
    "047810": "한국항공우주", "271560": "오리온", "024110": "기업은행",
    "161390": "한국타이어앤테크놀로지", "010130": "고려아연", "036570": "엔씨소프트",
    "009830": "한화솔루션", "051900": "LG생활건강", "011170": "롯데케미칼",
    "267250": "HD현대중공업", "042660": "한화오션", "004020": "현대제철",
    "003490": "대한항공", "047050": "포스코인터내셔널", "097950": "CJ제일제당",
    "326030": "SK바이오팜", "352820": "하이브", "036460": "한국가스공사",
    "010140": "삼성중공업", "004170": "신세계", "078930": "GS",
    "051915": "LG화학우", "000720": "현대건설", "011200": "현대상사",
    "010620": "현대미포조선", "001450": "현대해상", "000100": "유한양행",
    "006800": "미래에셋증권", "016360": "삼성증권", "000080": "하이트진로",
    "004990": "롯데지주", "139480": "이마트", "030000": "제일기획",
    "064350": "현대로템", "111770": "영원무역", "004370": "농심",
    "088350": "한화생명", "006260": "LS", "001040": "CJ",
    "012450": "한화에어로스페이스", "069960": "현대백화점", "007070": "GS리테일",
    "001740": "SK네트웍스", "282330": "BGF리테일", "138930": "BNK금융지주",
    "003230": "삼양식품", "011780": "금호석유", "298050": "효성첨단소재",
    "298020": "효성티앤씨", "090430": "아모레퍼시픽", "241560": "두산밥캣",
    "267270": "HD현대건설기계", "006360": "GS건설", "005940": "NH투자증권",
    "000150": "두산", "047040": "대우건설", "008770": "호텔신라",
    "000120": "CJ대한통운", "001430": "세아베스틸", "005850": "에스엘",
    "018880": "한온시스템", "011790": "SKC", "001120": "LX인터내셔널",
}


def get_stock_name(stock_code: str) -> str:
    """종목 코드로 한글 이름 조회"""
    return STOCK_NAMES.get(stock_code, "")


def load_stock_list(filename: str = "kospi_top100.txt") -> List[str]:
    """파일에서 종목 리스트 로드"""
    try:
        with open(filename, 'r') as f:
            stocks = [line.strip() for line in f if line.strip()]
        return stocks
    except FileNotFoundError:
        print(f"⚠️  {filename} 파일이 없습니다.")
        print("   먼저 fetch_kospi_top100.py를 실행하세요.")
        return []


def fetch_stock_data_safe(stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    안전하게 주가 데이터 다운로드 (에러 처리 포함)

    Args:
        stock_code: 종목 코드
        start_date: 시작일
        end_date: 종료일

    Returns:
        DataFrame 또는 None
    """
    ticker = f"{stock_code}.KS"

    try:
        df = yf.download(ticker, start=start_date, end=end_date, progress=False)

        if df.empty:
            # KOSPI에 없으면 KOSDAQ 시도
            ticker = f"{stock_code}.KQ"
            df = yf.download(ticker, start=start_date, end=end_date, progress=False)

        if df.empty:
            return None

        # 컬럼 정리
        df.columns = df.columns.get_level_values(0)

        result = pd.DataFrame({
            'Open': df['Open'],
            'High': df['High'],
            'Low': df['Low'],
            'Close': df['Close'],
            'Volume': df['Volume']
        }).dropna()

        # 최소 데이터 개수 확인 (볼린저 밴드 계산 위해 최소 50일)
        if len(result) < 50:
            return None

        return result

    except Exception as e:
        return None


def run_single_backtest(
    stock_code: str,
    stock_data: pd.DataFrame,
    config: BacktestConfiguration
) -> Tuple[bool, Dict]:
    """
    단일 종목 백테스트 실행

    Args:
        stock_code: 종목 코드
        stock_data: 가격 데이터
        config: 백테스트 설정

    Returns:
        (성공 여부, 결과 딕셔너리)
    """
    try:
        # 개별 종목용 설정 생성
        stock_config = BacktestConfiguration(
            seed_money=config.seed_money,
            stocks=[stock_code],
            date_range=config.date_range,
            bollinger_period=config.bollinger_period,
            bollinger_std_dev=config.bollinger_std_dev,
            squeeze_threshold_percent=config.squeeze_threshold_percent,
            squeeze_lookback_days=config.squeeze_lookback_days,
            stop_loss_percent=config.stop_loss_percent,
            max_position_percent=config.max_position_percent,
            max_positions=1  # 단일 종목이므로 1
        )

        # 백테스트 실행
        engine = BacktestEngine(config=stock_config)
        engine.load_mock_data(stock_code, stock_data)
        report = engine.run()

        # 결과 정리
        result = {
            'stock_code': stock_code,
            'num_trades': report.num_trades,
            'total_return_pct': float(report.total_return_pct),
            'win_rate_pct': float(report.win_rate_pct),
            'max_drawdown_pct': float(report.max_drawdown_pct),
            'sharpe_ratio': float(report.sharpe_ratio),
            'num_winning': report.num_winning_trades,
            'num_losing': report.num_losing_trades,
            'avg_win': float(report.avg_win) if report.avg_win else 0,
            'avg_loss': float(report.avg_loss) if report.avg_loss != 0 else 0,
            'profit_factor': float(report.profit_factor) if report.profit_factor else 0,
        }

        return True, result

    except Exception as e:
        return False, {'stock_code': stock_code, 'error': str(e)}


def run_multi_backtest(
    stock_codes: List[str],
    start_date: str,
    end_date: str,
    seed_money: int = 10_000_000,
    max_stocks: int = None,
    **strategy_params
):
    """
    다중 종목 백테스트 실행

    Args:
        stock_codes: 종목 코드 리스트
        start_date: 시작일
        end_date: 종료일
        seed_money: 초기 자본
        max_stocks: 최대 테스트 종목 수 (None이면 전체)
        **strategy_params: 전략 파라미터
    """
    print("=" * 80)
    print("🚀 다중 종목 백테스트 시작")
    print("=" * 80)

    # 최대 종목 수 제한
    if max_stocks:
        stock_codes = stock_codes[:max_stocks]

    print(f"\n📊 설정:")
    print(f"   종목 수: {len(stock_codes)}개")
    print(f"   기간: {start_date} ~ {end_date}")
    print(f"   초기 자본: ₩{seed_money:,}")
    print(f"   전략 파라미터: {strategy_params}")

    # 설정 생성
    config = BacktestConfiguration(
        seed_money=seed_money,
        stocks=stock_codes,
        date_range=(
            pd.to_datetime(start_date).date(),
            pd.to_datetime(end_date).date()
        ),
        **strategy_params
    )

    # 1단계: 데이터 다운로드
    print(f"\n📥 1단계: 데이터 다운로드 중...")
    print("-" * 80)

    stock_data_dict = {}
    download_success = 0
    download_fail = 0

    for i, stock_code in enumerate(stock_codes, 1):
        stock_name = get_stock_name(stock_code)
        display_name = f"{stock_code} ({stock_name})" if stock_name else stock_code
        print(f"[{i:3d}/{len(stock_codes)}] {display_name} ... ", end="", flush=True)

        data = fetch_stock_data_safe(stock_code, start_date, end_date)

        if data is not None:
            stock_data_dict[stock_code] = data
            download_success += 1
            print(f"✅ {len(data)}일")
        else:
            download_fail += 1
            print(f"❌ 실패")

        # API 제한 방지를 위한 딜레이 (100종목이면 조금 쉬어가기)
        if i % 10 == 0:
            time.sleep(1)

    print(f"\n다운로드 완료: 성공 {download_success}개, 실패 {download_fail}개")

    if download_success == 0:
        print("\n❌ 다운로드된 데이터가 없어 백테스트를 실행할 수 없습니다.")
        return

    # 2단계: 백테스트 실행
    print(f"\n⏳ 2단계: 백테스트 실행 중...")
    print("-" * 80)

    results = []
    backtest_success = 0
    backtest_fail = 0

    for i, (stock_code, stock_data) in enumerate(stock_data_dict.items(), 1):
        stock_name = get_stock_name(stock_code)
        display_name = f"{stock_code} ({stock_name})" if stock_name else stock_code
        print(f"[{i:3d}/{len(stock_data_dict)}] {display_name} 백테스트 ... ", end="", flush=True)

        success, result = run_single_backtest(stock_code, stock_data, config)

        if success:
            results.append(result)
            backtest_success += 1
            print(f"✅ 거래 {result['num_trades']}회, 수익률 {result['total_return_pct']:.2f}%")
        else:
            backtest_fail += 1
            print(f"❌ 실패")

    print(f"\n백테스트 완료: 성공 {backtest_success}개, 실패 {backtest_fail}개")

    # 3단계: 결과 분석 및 저장
    if len(results) == 0:
        print("\n❌ 백테스트 결과가 없습니다.")
        return

    print(f"\n📊 3단계: 결과 분석")
    print("=" * 80)

    # DataFrame으로 변환
    df_results = pd.DataFrame(results)

    # 통계 계산
    print(f"\n전체 통계 (총 {len(df_results)}개 종목):")
    print("-" * 80)
    # 최고/최저 종목 정보
    max_idx = df_results['total_return_pct'].idxmax()
    min_idx = df_results['total_return_pct'].idxmin()
    max_stock_code = df_results.loc[max_idx, 'stock_code']
    min_stock_code = df_results.loc[min_idx, 'stock_code']
    max_stock_name = get_stock_name(max_stock_code)
    min_stock_name = get_stock_name(min_stock_code)
    max_display = f"{max_stock_code} ({max_stock_name})" if max_stock_name else max_stock_code
    min_display = f"{min_stock_code} ({min_stock_name})" if min_stock_name else min_stock_code

    print(f"평균 수익률:          {df_results['total_return_pct'].mean():.2f}%")
    print(f"중간값 수익률:        {df_results['total_return_pct'].median():.2f}%")
    print(f"최고 수익률:          {df_results['total_return_pct'].max():.2f}% ({max_display})")
    print(f"최저 수익률:          {df_results['total_return_pct'].min():.2f}% ({min_display})")
    print(f"\n평균 승률:            {df_results['win_rate_pct'].mean():.2f}%")
    print(f"평균 MDD:             {df_results['max_drawdown_pct'].mean():.2f}%")
    print(f"평균 샤프 비율:       {df_results['sharpe_ratio'].mean():.2f}")
    print(f"\n평균 거래 횟수:       {df_results['num_trades'].mean():.1f}회")
    print(f"총 거래 횟수:         {df_results['num_trades'].sum()}회")

    # 수익 종목 vs 손실 종목
    profitable = df_results[df_results['total_return_pct'] > 0]
    unprofitable = df_results[df_results['total_return_pct'] <= 0]

    print(f"\n수익 종목:            {len(profitable)}개 ({len(profitable)/len(df_results)*100:.1f}%)")
    print(f"손실 종목:            {len(unprofitable)}개 ({len(unprofitable)/len(df_results)*100:.1f}%)")

    # Top 10 종목
    print(f"\n💰 수익률 상위 10개 종목:")
    print("-" * 80)
    top10 = df_results.nlargest(10, 'total_return_pct')
    for i, row in enumerate(top10.itertuples(), 1):
        stock_name = get_stock_name(row.stock_code)
        display = f"{row.stock_code} ({stock_name})" if stock_name else row.stock_code
        print(f"{i:2d}. {display:<25}  수익률: {row.total_return_pct:>7.2f}%  거래: {row.num_trades}회  승률: {row.win_rate_pct:.1f}%")

    # Bottom 10 종목
    print(f"\n📉 수익률 하위 10개 종목:")
    print("-" * 80)
    bottom10 = df_results.nsmallest(10, 'total_return_pct')
    for i, row in enumerate(bottom10.itertuples(), 1):
        stock_name = get_stock_name(row.stock_code)
        display = f"{row.stock_code} ({stock_name})" if stock_name else row.stock_code
        print(f"{i:2d}. {display:<25}  수익률: {row.total_return_pct:>7.2f}%  거래: {row.num_trades}회  승률: {row.win_rate_pct:.1f}%")

    # 4단계: 엑셀로 저장
    filename = f"backtest_results_{len(df_results)}stocks_{start_date}_{end_date}.xlsx"
    df_results_sorted = df_results.sort_values('total_return_pct', ascending=False)

    # 한글 종목명 컬럼 추가
    df_results_sorted.insert(1, 'stock_name', df_results_sorted['stock_code'].apply(get_stock_name))

    df_results_sorted.to_excel(filename, index=False, engine='openpyxl')

    print(f"\n💾 결과 저장: {filename}")
    print("=" * 80)

    return df_results


# ============================================================
# 실행 예제
# ============================================================

if __name__ == "__main__":
    # 방법 1: 파일에서 종목 리스트 로드
    stocks = load_stock_list("kospi_top100.txt")

    if len(stocks) == 0:
        print("\n⚠️  종목 리스트가 비어있습니다.")
        print("   fetch_kospi_top100.py를 먼저 실행하세요:")
        print("   poetry run python fetch_kospi_top100.py")
        exit(1)

    # 테스트용: 처음 10개 종목만 (빠른 테스트)
    # 전체 실행 시 주석 처리하세요
    print("\n⚠️  테스트 모드: 처음 10개 종목만 실행")
    print("   전체 100개 종목을 실행하려면 아래 줄의 주석을 해제하세요\n")

    results = run_multi_backtest(
        stock_codes=stocks,
        start_date="2023-01-01",  # ← 2022년으로 변경
        end_date="2023-12-31",    # ← 2022년으로 변경
        seed_money=10_000_000,
        #max_stocks=10,  # ← 이 줄을 삭제하거나 주석 처리하면 전체 실행
        bollinger_period=20,
        squeeze_threshold_percent=40,
        stop_loss_percent=5.0,
        max_position_percent=30.0
    )

    print("\n✅ 모든 백테스트 완료!")
    print("\n💡 다음 단계:")
    print("   1. 생성된 엑셀 파일 확인")
    print("   2. 수익률 상위 종목 분석")
    print("   3. 전략 파라미터 최적화")
