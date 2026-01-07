"""
2025 KOSPI Top 100 포트폴리오 기반 백테스트
시드 머니: 1,000만원 기준 실제 포트폴리오 관리
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')


class PortfolioBacktest:
    def __init__(self, initial_capital: float = 10_000_000, max_positions: int = 15, position_size_pct: float = 0.1):
        """
        포트폴리오 백테스트 초기화

        Args:
            initial_capital: 초기 자본 (기본: 1,000만원)
            max_positions: 최대 동시 보유 종목 수
            position_size_pct: 종목당 최대 투자 비중 (기본: 10%)
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.max_positions = max_positions
        self.position_size_pct = position_size_pct

        self.positions = {}  # 현재 보유 포지션 {stock_code: {'shares': int, 'buy_price': float, 'buy_date': date}}
        self.cash = initial_capital  # 현재 현금
        self.portfolio_history = []  # 포트폴리오 가치 히스토리
        self.trade_history = []  # 거래 히스토리
        self.daily_values = {}  # 일별 포트폴리오 가치


def load_kospi_top100(filepath: str = "kospi_top100.txt") -> List[str]:
    """KOSPI Top 100 종목 리스트 로드"""
    with open(filepath, 'r') as f:
        stocks = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return [s for s in stocks if s][:100]


def fetch_stock_data(stock_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
    """Yahoo Finance에서 한국 주식 데이터 가져오기"""
    ticker = f"{stock_code}.KS"

    try:
        df = yf.download(ticker, start=start_date, end=end_date, progress=False, auto_adjust=False)

        if df.empty:
            ticker = f"{stock_code}.KQ"
            df = yf.download(ticker, start=start_date, end=end_date, progress=False, auto_adjust=False)

        if df.empty:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        result = pd.DataFrame({
            'Open': df['Open'],
            'High': df['High'],
            'Low': df['Low'],
            'Close': df['Close'],
            'Volume': df['Volume']
        }).dropna()

        return result if len(result) >= 10 else None

    except Exception:
        return None


def calculate_bollinger_bands(prices: pd.Series, window: int = 20, std_dev: float = 2.0) -> pd.DataFrame:
    """볼린저 밴드 계산"""
    sma = prices.rolling(window=window).mean()
    std = prices.rolling(window=window).std()

    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)

    return pd.DataFrame({
        'SMA': sma,
        'Upper': upper,
        'Lower': lower,
        'BandWidth': (upper - lower) / sma * 100
    })


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """RSI 계산"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """MACD 계산"""
    exp1 = prices.ewm(span=fast).mean()
    exp2 = prices.ewm(span=slow).mean()
    macd_line = exp1 - exp2
    signal_line = macd_line.ewm(span=signal).mean()
    histogram = macd_line - signal_line

    return pd.DataFrame({
        'MACD': macd_line,
        'Signal': signal_line,
        'Histogram': histogram
    })


def calculate_volume_filter(volume: pd.Series, window: int = 20, multiplier: float = 1.5) -> pd.Series:
    """거래량 필터 계산"""
    avg_volume = volume.rolling(window=window).mean()
    return volume >= (avg_volume * multiplier)


def prepare_stock_data(data: pd.DataFrame) -> pd.DataFrame:
    """주식 데이터에 기술지표 추가"""
    # 기술지표 계산
    bb = calculate_bollinger_bands(data['Close'])
    data['RSI'] = calculate_rsi(data['Close'])
    macd_data = calculate_macd(data['Close'])
    data['MACD'] = macd_data['MACD']
    data['MACD_Signal'] = macd_data['Signal']
    data['Volume_Filter'] = calculate_volume_filter(data['Volume'])

    # 볼린저 밴드 추가
    data['BB_Upper'] = bb['Upper']
    data['BB_Lower'] = bb['Lower']
    data['BB_SMA'] = bb['SMA']
    data['BandWidth'] = bb['BandWidth']

    # Squeeze 감지
    data['BandWidth_MA'] = data['BandWidth'].rolling(window=10).mean()
    data['Squeeze'] = data['BandWidth'] < (data['BandWidth_MA'] * 0.7)

    return data


def check_buy_signal(data: pd.DataFrame, index: int) -> bool:
    """매수 신호 확인"""
    if index < 30:  # 충분한 데이터 필요
        return False

    row = data.iloc[index]

    return (
        row['Close'] > row['BB_Upper'] and  # 상단 밴드 돌파
        row['Volume_Filter'] and  # 거래량 급증
        30 <= row['RSI'] <= 70 and  # RSI 중립구간
        row['MACD'] > row['MACD_Signal']  # MACD 골든크로스
    )


def check_sell_signal(data: pd.DataFrame, index: int, buy_price: float) -> bool:
    """매도 신호 확인"""
    row = data.iloc[index]

    return (
        row['Close'] < row['BB_Lower'] or  # 하단 밴드 터치
        row['Close'] < buy_price * 0.95  # 5% 손절
    )


def run_portfolio_backtest(kospi_stocks: List[str], start_date: str, end_date: str) -> Dict:
    """포트폴리오 백테스트 실행"""
    portfolio = PortfolioBacktest(
        initial_capital=10_000_000,  # 1,000만원
        max_positions=15,
        position_size_pct=0.15  # 종목당 최대 15% 투자
    )

    # 모든 종목 데이터 수집
    print("📈 데이터 수집 중...")
    stock_data = {}
    successful_stocks = []

    for i, stock_code in enumerate(kospi_stocks):
        print(f"진행: {i+1}/{len(kospi_stocks)} ({stock_code})", end=" ")

        data = fetch_stock_data(stock_code, start_date, end_date)
        if data is not None and len(data) >= 15:
            prepared_data = prepare_stock_data(data)
            stock_data[stock_code] = prepared_data
            successful_stocks.append(stock_code)
            print("✓")
        else:
            print("✗")

    if not stock_data:
        return {}

    print(f"\n✅ {len(successful_stocks)}개 종목 데이터 준비 완료")

    # 모든 거래일 수집 (교집합)
    all_dates = set(stock_data[list(stock_data.keys())[0]].index)
    for data in stock_data.values():
        all_dates = all_dates.intersection(set(data.index))

    trading_dates = sorted(list(all_dates))
    print(f"📅 거래일: {len(trading_dates)}일")

    # 일별 백테스트 실행
    print("\n🚀 포트폴리오 백테스트 실행 중...")

    for date_idx, current_date in enumerate(trading_dates):
        if date_idx % 5 == 0:
            print(f"진행: {date_idx+1}/{len(trading_dates)} ({current_date.date()})", end="\r")

        # 현재 포트폴리오 가치 계산
        portfolio_value = portfolio.cash
        current_positions_value = 0

        # 보유 주식 가치 계산
        for stock_code, position in portfolio.positions.items():
            if stock_code in stock_data and current_date in stock_data[stock_code].index:
                current_price = stock_data[stock_code].loc[current_date, 'Close']
                position_value = position['shares'] * current_price
                current_positions_value += position_value

        portfolio_value += current_positions_value
        portfolio.daily_values[current_date] = portfolio_value

        # 매도 신호 확인 (보유 종목들)
        stocks_to_sell = []
        for stock_code, position in portfolio.positions.items():
            if stock_code in stock_data and current_date in stock_data[stock_code].index:
                date_idx_in_stock = stock_data[stock_code].index.get_loc(current_date)

                if check_sell_signal(stock_data[stock_code], date_idx_in_stock, position['buy_price']):
                    stocks_to_sell.append(stock_code)

        # 매도 실행
        for stock_code in stocks_to_sell:
            position = portfolio.positions[stock_code]
            current_price = stock_data[stock_code].loc[current_date, 'Close']

            # 매도 금액 계산
            sell_value = position['shares'] * current_price
            portfolio.cash += sell_value

            # 수익률 계산
            return_pct = (current_price - position['buy_price']) / position['buy_price'] * 100

            # 거래 기록
            portfolio.trade_history.append({
                'type': 'SELL',
                'stock_code': stock_code,
                'date': current_date,
                'price': current_price,
                'shares': position['shares'],
                'value': sell_value,
                'buy_date': position['buy_date'],
                'buy_price': position['buy_price'],
                'return_pct': return_pct,
                'days_held': (current_date - position['buy_date']).days
            })

            # 포지션 제거
            del portfolio.positions[stock_code]

        # 매수 신호 확인 (새로운 종목들)
        if len(portfolio.positions) < portfolio.max_positions:
            for stock_code in successful_stocks:
                if (stock_code not in portfolio.positions and
                    stock_code in stock_data and
                    current_date in stock_data[stock_code].index):

                    date_idx_in_stock = stock_data[stock_code].index.get_loc(current_date)

                    if check_buy_signal(stock_data[stock_code], date_idx_in_stock):
                        # 매수 실행
                        current_price = stock_data[stock_code].loc[current_date, 'Close']
                        max_investment = portfolio_value * portfolio.position_size_pct

                        if portfolio.cash >= max_investment and max_investment >= current_price:
                            shares = int(max_investment / current_price)
                            actual_investment = shares * current_price

                            if shares > 0 and portfolio.cash >= actual_investment:
                                portfolio.cash -= actual_investment

                                portfolio.positions[stock_code] = {
                                    'shares': shares,
                                    'buy_price': current_price,
                                    'buy_date': current_date
                                }

                                # 거래 기록
                                portfolio.trade_history.append({
                                    'type': 'BUY',
                                    'stock_code': stock_code,
                                    'date': current_date,
                                    'price': current_price,
                                    'shares': shares,
                                    'value': actual_investment
                                })

                                if len(portfolio.positions) >= portfolio.max_positions:
                                    break

    print(f"\n✅ 백테스트 완료")

    # 최종 결과 계산
    final_portfolio_value = list(portfolio.daily_values.values())[-1] if portfolio.daily_values else portfolio.initial_capital
    total_return_pct = (final_portfolio_value - portfolio.initial_capital) / portfolio.initial_capital * 100

    # 거래 분석
    completed_trades = [t for t in portfolio.trade_history if t['type'] == 'SELL']
    total_trades = len(completed_trades)
    winning_trades = len([t for t in completed_trades if t['return_pct'] > 0])
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

    avg_return_per_trade = np.mean([t['return_pct'] for t in completed_trades]) if completed_trades else 0

    return {
        'initial_capital': portfolio.initial_capital,
        'final_portfolio_value': final_portfolio_value,
        'total_return_pct': total_return_pct,
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': total_trades - winning_trades,
        'win_rate': win_rate,
        'avg_return_per_trade': avg_return_per_trade,
        'current_positions': len(portfolio.positions),
        'current_cash': portfolio.cash,
        'trade_history': portfolio.trade_history,
        'daily_values': portfolio.daily_values,
        'positions': portfolio.positions,
        'portfolio': portfolio
    }


def get_stock_name(stock_code: str) -> str:
    """종목 코드를 종목명으로 변환"""
    stock_names = {
        '005930': '삼성전자', '000660': 'SK하이닉스', '373220': 'LG에너지솔루션', '207940': '삼성바이오로직스',
        '005490': 'POSCO홀딩스', '005380': '현대차', '006400': '삼성SDI', '051910': 'LG화학',
        '035420': 'NAVER', '000270': '기아', '068270': '셀트리온', '105560': 'KB금융',
        '055550': '신한지주', '035720': '카카오', '012330': '현대모비스', '028260': '삼성물산',
        '066570': 'LG전자', '003670': '포스코퓨처엠', '323410': '카카오뱅크', '086790': '하나금융지주',
        '096770': 'SK이노베이션', '009150': '삼성전기', '017670': 'SK텔레콤', '033780': 'KT&G',
        '015760': '한국전력', '034730': 'SK', '000810': '삼성화재', '032830': '삼성생명',
        '018260': '삼성에스디에스', '003550': 'LG', '030200': 'KT', '010950': 'S-Oil',
        '011070': 'LG이노텍', '086280': '현대글로비스', '009540': 'HD현대중공업', '028050': '삼성엔지니어링',
        '047810': '한국항공우주', '271560': '오리온', '024110': '기업은행', '161390': '한국타이어앤테크놀로지',
        '010130': '고려아연', '036570': '엔씨소프트', '009830': '한화솔루션', '051900': 'LG생활건강',
        '011170': '롯데케미칼', '267250': 'HD현대', '042660': '한화오션', '004020': '현대제철',
        '003490': '대한항공', '047050': '포스코인터내셔널', '097950': 'CJ제일제당', '326030': 'SK바이오팜',
        '352820': 'HD현대에너지솔루션', '036460': '한국가스공사', '010140': '삼성중공업', '004170': '신세계',
        '078930': 'GS', '051915': 'LG화학우', '000720': '현대건설', '003550': 'LG',
        '011200': 'HMM', '010620': '현대미포조선', '001450': '현대해상', '000100': '유한양행',
        '006800': '미래에셋증권', '016360': 'HL만도', '000080': '하이트진로', '004990': '롯데지주',
        '139480': '이마트', '030000': '제일기획', '064350': '현대로템', '111770': '영원무역',
        '004370': '농심', '088350': '한화생명', '006260': 'LS', '001040': 'CJ',
        '012450': '한화에어로스페이스', '069960': '현대백화점', '007070': 'GS리테일', '001740': 'SK네트웍스',
        '282330': 'BGF리테일', '138930': 'BNK금융지주', '003230': '삼양식품', '011780': '금고석유',
        '298050': '효성첨단소재', '298020': '효성티앤씨', '090430': '아모레퍼시픽', '010950': 'S-Oil',
        '241560': '두산밥캣', '267270': 'HD현대마린엔진', '006360': 'GS건설', '005940': 'NH투자증권',
        '000150': '두산', '047040': '대우건설', '008770': '호텔신라', '000120': 'CJ대한통운',
        '001430': '세��제강지주', '005850': '에스엘', '018880': '한온시스템', '011790': 'SKC'
    }
    return stock_names.get(stock_code, stock_code)


def main():
    print("="*80)
    print("💰 2025 KOSPI Top 100 포트폴리오 백테스트")
    print("시드 머니: 1,000만원 기준")
    print("="*80)

    # 설정
    start_date = "2025-01-01"
    end_date = date.today().strftime('%Y-%m-%d')

    print(f"\n📅 분석 기간: {start_date} ~ {end_date}")

    # KOSPI Top 100 로드
    kospi_stocks = load_kospi_top100()
    print(f"📋 분석 대상: KOSPI Top 100 ({len(kospi_stocks)}개 종목)")
    print(f"💰 시드 머니: 10,000,000원")
    print(f"📊 최대 동시 보유: 15종목")
    print(f"📈 종목당 최대 투자: 15%")

    # 백테스트 실행
    results = run_portfolio_backtest(kospi_stocks, start_date, end_date)

    if not results:
        print("❌ 백테스트 실행 실패")
        return

    # 결과 출력
    print("\n" + "="*80)
    print("📊 포트폴리오 백테스트 결과")
    print("="*80)

    print(f"\n💰 자본 현황:")
    print(f"  초기 자본:            ₩{results['initial_capital']:,}")
    print(f"  최종 포트폴리오 가치: ₩{results['final_portfolio_value']:,.0f}")
    print(f"  현재 현금:            ₩{results['current_cash']:,.0f}")

    profit_loss = results['final_portfolio_value'] - results['initial_capital']
    status_emoji = "🟢" if profit_loss > 0 else "🔴"

    print(f"\n📈 수익성 지표:")
    print(f"  총 손익:              {status_emoji} ₩{profit_loss:+,.0f}")
    print(f"  총 수익률:            {status_emoji} {results['total_return_pct']:+.2f}%")

    print(f"\n📊 거래 통계:")
    print(f"  총 거래 수:           {results['total_trades']}건")
    print(f"  수익 거래:            {results['winning_trades']}건")
    print(f"  손실 거래:            {results['losing_trades']}건")
    print(f"  승률:                 {results['win_rate']:.1f}%")
    print(f"  거래당 평균 수익률:   {results['avg_return_per_trade']:+.2f}%")
    print(f"  현재 보유 포지션:     {results['current_positions']}개")

    # 현재 보유 포지션 표시
    if results['positions']:
        print(f"\n🏆 현재 보유 포지션:")
        print("┌──────────┬────────────────┬──────────┬──────────┬──────────┬──────────┐")
        print("│ 종목코드 │    종목명      │  보유주수│ 매수가격 │ 현재가치 │ 보유일수 │")
        print("├──────────┼────────────────┼──────────┼──────────┼──────────┼──────────┤")

        # 현재 가격 정보 필요 시 다시 조회 (간단히 매수가로 대체)
        for stock_code, position in results['positions'].items():
            stock_name = get_stock_name(stock_code)
            current_value = position['shares'] * position['buy_price']  # 간단 계산
            days_held = (date.today() - position['buy_date'].date()).days

            print(f"│ {stock_code:8s} │ {stock_name[:14]:14s} │ {position['shares']:8,}주 │ {position['buy_price']:8,.0f} │ {current_value:8,.0f} │ {days_held:6d}일 │")

        print("└──────────┴────────────────┴──────────┴──────────┴──────────┴──────────┘")

    # 상위 거래 표시
    completed_trades = [t for t in results['trade_history'] if t['type'] == 'SELL']
    if completed_trades:
        # 수익률 기준 상위 10개 거래
        top_trades = sorted(completed_trades, key=lambda x: x['return_pct'], reverse=True)[:10]

        print(f"\n🌟 상위 10개 거래:")
        print("┌──────────┬────────────────┬──────────┬──────────┬──────────┬──────────┐")
        print("│ 종목코드 │    종목명      │ 매수가격 │ 매도가격 │  수익률  │ 보유일수 │")
        print("├──────────┼────────────────┼──────────┼──────────┼──────────┼──────────┤")

        for trade in top_trades:
            stock_name = get_stock_name(trade['stock_code'])
            status_emoji = "🟢" if trade['return_pct'] > 0 else "🔴"

            print(f"│ {trade['stock_code']:8s} │ {stock_name[:14]:14s} │ {trade['buy_price']:8,.0f} │ {trade['price']:8,.0f} │ {status_emoji}{trade['return_pct']:7.2f}% │ {trade['days_held']:6d}일 │")

        print("└──────────┴────────────────┴──────────┴──────────┴──────────┴──────────┘")

    # 성과 평가
    print(f"\n🎯 성과 평가:")
    if results['total_return_pct'] > 20:
        evaluation = "🌟 탁월 (>20%)"
    elif results['total_return_pct'] > 10:
        evaluation = "✅ 우수 (10-20%)"
    elif results['total_return_pct'] > 5:
        evaluation = "⚡ 양호 (5-10%)"
    elif results['total_return_pct'] > 0:
        evaluation = "📈 보통 (0-5%)"
    else:
        evaluation = "📉 부진 (<0%)"

    print(f"  포트폴리오 성과:      {evaluation}")

    if results['win_rate'] > 60:
        consistency = "🛡️ 높은 일관성 (>60% 승률)"
    elif results['win_rate'] > 50:
        consistency = "✅ 보통 일관성 (50-60% 승률)"
    else:
        consistency = "⚠️ 낮은 일관성 (<50% 승률)"

    print(f"  거래 일관성:          {consistency}")


if __name__ == "__main__":
    main()
    print(f"\n" + "="*80)
    print("✅ 포트폴리오 백테스트 완료")
    print("="*80)