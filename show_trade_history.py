"""
포트폴리오 백테스트 거래 이력 상세 분석
모든 매수/매도 거래를 시간순으로 표시
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

# 이전 포트폴리오 백테스트 코드 재사용
class PortfolioBacktest:
    def __init__(self, initial_capital: float = 10_000_000, max_positions: int = 15, position_size_pct: float = 0.1):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.max_positions = max_positions
        self.position_size_pct = position_size_pct

        self.positions = {}
        self.cash = initial_capital
        self.portfolio_history = []
        self.trade_history = []
        self.daily_values = {}


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
    bb = calculate_bollinger_bands(data['Close'])
    data['RSI'] = calculate_rsi(data['Close'])
    macd_data = calculate_macd(data['Close'])
    data['MACD'] = macd_data['MACD']
    data['MACD_Signal'] = macd_data['Signal']
    data['Volume_Filter'] = calculate_volume_filter(data['Volume'])

    data['BB_Upper'] = bb['Upper']
    data['BB_Lower'] = bb['Lower']
    data['BB_SMA'] = bb['SMA']
    data['BandWidth'] = bb['BandWidth']

    data['BandWidth_MA'] = data['BandWidth'].rolling(window=10).mean()
    data['Squeeze'] = data['BandWidth'] < (data['BandWidth_MA'] * 0.7)

    return data


def check_buy_signal(data: pd.DataFrame, index: int) -> bool:
    """매수 신호 확인"""
    if index < 30:
        return False

    row = data.iloc[index]

    return (
        row['Close'] > row['BB_Upper'] and
        row['Volume_Filter'] and
        30 <= row['RSI'] <= 70 and
        row['MACD'] > row['MACD_Signal']
    )


def check_sell_signal(data: pd.DataFrame, index: int, buy_price: float) -> bool:
    """매도 신호 확인"""
    row = data.iloc[index]

    return (
        row['Close'] < row['BB_Lower'] or
        row['Close'] < buy_price * 0.95
    )


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
        '001430': '세아제강지주', '005850': '에스엘', '018880': '한온시스템', '011790': 'SKC'
    }
    return stock_names.get(stock_code, stock_code)


def run_detailed_backtest_with_history():
    """상세한 거래 이력을 포함한 백테스트 실행"""
    print("="*80)
    print("📈 포트폴리오 거래 이력 상세 분석")
    print("="*80)

    start_date = "2025-01-01"
    end_date = date.today().strftime('%Y-%m-%d')

    # KOSPI Top 100 로드
    kospi_stocks = load_kospi_top100()
    print(f"📋 분석 대상: KOSPI Top 100 ({len(kospi_stocks)}개 종목)")

    portfolio = PortfolioBacktest(
        initial_capital=10_000_000,
        max_positions=15,
        position_size_pct=0.15
    )

    # 데이터 수집 (간략히)
    stock_data = {}
    successful_stocks = []

    print("\n📈 데이터 수집 중... ", end="", flush=True)
    for stock_code in kospi_stocks:
        data = fetch_stock_data(stock_code, start_date, end_date)
        if data is not None and len(data) >= 15:
            prepared_data = prepare_stock_data(data)
            stock_data[stock_code] = prepared_data
            successful_stocks.append(stock_code)

    print(f"✓ {len(successful_stocks)}개 종목")

    # 공통 거래일 추출
    all_dates = set(stock_data[list(stock_data.keys())[0]].index)
    for data in stock_data.values():
        all_dates = all_dates.intersection(set(data.index))

    trading_dates = sorted(list(all_dates))

    print(f"📅 거래 기간: {trading_dates[0].date()} ~ {trading_dates[-1].date()} ({len(trading_dates)}일)")
    print(f"💰 초기 자본: ₩{portfolio.initial_capital:,}")

    # 백테스트 실행
    print(f"\n🚀 백테스트 실행 중... ", end="", flush=True)

    for date_idx, current_date in enumerate(trading_dates):
        # 포트폴리오 가치 계산
        portfolio_value = portfolio.cash
        current_positions_value = 0

        for stock_code, position in portfolio.positions.items():
            if stock_code in stock_data and current_date in stock_data[stock_code].index:
                current_price = stock_data[stock_code].loc[current_date, 'Close']
                position_value = position['shares'] * current_price
                current_positions_value += position_value

        portfolio_value += current_positions_value
        portfolio.daily_values[current_date] = portfolio_value

        # 매도 신호 확인
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

            sell_value = position['shares'] * current_price
            portfolio.cash += sell_value

            return_pct = (current_price - position['buy_price']) / position['buy_price'] * 100

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
                'days_held': (current_date - position['buy_date']).days,
                'portfolio_value_before': portfolio_value,
                'cash_after': portfolio.cash
            })

            del portfolio.positions[stock_code]

        # 매수 신호 확인
        if len(portfolio.positions) < portfolio.max_positions:
            for stock_code in successful_stocks:
                if (stock_code not in portfolio.positions and
                    stock_code in stock_data and
                    current_date in stock_data[stock_code].index):

                    date_idx_in_stock = stock_data[stock_code].index.get_loc(current_date)

                    if check_buy_signal(stock_data[stock_code], date_idx_in_stock):
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

                                portfolio.trade_history.append({
                                    'type': 'BUY',
                                    'stock_code': stock_code,
                                    'date': current_date,
                                    'price': current_price,
                                    'shares': shares,
                                    'value': actual_investment,
                                    'portfolio_value_before': portfolio_value,
                                    'cash_after': portfolio.cash
                                })

                                if len(portfolio.positions) >= portfolio.max_positions:
                                    break

    print("✅ 완료")

    # 거래 이력 분석
    print(f"\n" + "="*80)
    print(f"📊 거래 이력 상세 분석")
    print(f"="*80)

    all_trades = sorted(portfolio.trade_history, key=lambda x: x['date'])

    if not all_trades:
        print("⚠️ 거래 이력이 없습니다.")
        return

    print(f"\n📈 총 거래 수: {len(all_trades)}건")

    buy_trades = [t for t in all_trades if t['type'] == 'BUY']
    sell_trades = [t for t in all_trades if t['type'] == 'SELL']

    print(f"  매수 거래: {len(buy_trades)}건")
    print(f"  매도 거래: {len(sell_trades)}건")

    # 시간순 거래 이력
    print(f"\n🕒 시간순 거래 이력:")
    print("┌──────────┬────────┬────────────────┬──────────┬──────────┬────────────┬────────────┬──────────┐")
    print("│   날짜   │  구분  │    종목명      │  주수    │  가격    │   거래금액 │  포트폴리오│  수익률  │")
    print("├──────────┼────────┼────────────────┼──────────┼──────────┼────────────┼────────────┼──────────┤")

    for i, trade in enumerate(all_trades):
        trade_date = trade['date'].strftime('%m/%d')
        trade_type = "🟢 매수" if trade['type'] == 'BUY' else "🔴 매도"
        stock_name = get_stock_name(trade['stock_code'])[:14]
        shares = f"{trade['shares']:,}주"
        price = f"₩{trade['price']:,.0f}"
        value = f"₩{trade['value']:,.0f}"
        portfolio_val = f"₩{trade.get('portfolio_value_before', 0):,.0f}"

        # 수익률 (매도 거래만)
        if trade['type'] == 'SELL':
            return_str = f"{trade['return_pct']:+.1f}%"
        else:
            return_str = "-"

        print(f"│ {trade_date:8s} │ {trade_type:6s} │ {stock_name:14s} │ {shares:8s} │ {price:8s} │ {value:10s} │ {portfolio_val:10s} │ {return_str:8s} │")

        # 20개마다 구분선
        if (i + 1) % 20 == 0 and i < len(all_trades) - 1:
            print("├──────────┼────────┼────────────────┼──────────┼──────────┼────────────┼────────────┼──────────┤")

    print("└──────────┴────────┴────────────────┴──────────┴──────────┴────────────┴────────────┴──────────┘")

    # 월별 거래 요약
    print(f"\n📅 월별 거래 요약:")

    monthly_summary = {}
    for trade in all_trades:
        month_key = trade['date'].strftime('%Y-%m')
        if month_key not in monthly_summary:
            monthly_summary[month_key] = {'buy': 0, 'sell': 0, 'buy_value': 0, 'sell_value': 0}

        if trade['type'] == 'BUY':
            monthly_summary[month_key]['buy'] += 1
            monthly_summary[month_key]['buy_value'] += trade['value']
        else:
            monthly_summary[month_key]['sell'] += 1
            monthly_summary[month_key]['sell_value'] += trade['value']

    print("┌─────────┬──────────┬──────────┬────────────┬────────────┐")
    print("│  월     │ 매수건수 │ 매도건수 │  매수금액  │  매도금액  │")
    print("├─────────┼──────────┼──────────┼────────────┼────────────┤")

    for month, summary in sorted(monthly_summary.items()):
        buy_count = summary['buy']
        sell_count = summary['sell']
        buy_value = f"₩{summary['buy_value']:,.0f}" if summary['buy_value'] > 0 else "-"
        sell_value = f"₩{summary['sell_value']:,.0f}" if summary['sell_value'] > 0 else "-"

        print(f"│ {month:7s} │ {buy_count:8d} │ {sell_count:8d} │ {buy_value:10s} │ {sell_value:10s} │")

    print("└─────────┴──────────┴──────────┴────────────┴────────────┘")

    # 최종 결과
    final_value = list(portfolio.daily_values.values())[-1]
    total_return = (final_value - portfolio.initial_capital) / portfolio.initial_capital * 100

    print(f"\n💰 최종 결과:")
    print(f"  초기 자본:       ₩{portfolio.initial_capital:,}")
    print(f"  최종 포트폴리오: ₩{final_value:,.0f}")
    print(f"  총 손익:         ₩{final_value - portfolio.initial_capital:+,.0f}")
    print(f"  총 수익률:       {total_return:+.2f}%")

    winning_trades = [t for t in sell_trades if t['return_pct'] > 0]
    print(f"  수익 거래:       {len(winning_trades)}/{len(sell_trades)}건 ({len(winning_trades)/len(sell_trades)*100:.1f}% 승률)")

    return portfolio


if __name__ == "__main__":
    portfolio = run_detailed_backtest_with_history()
    print(f"\n" + "="*80)
    print("✅ 거래 이력 분석 완료")
    print("="*80)