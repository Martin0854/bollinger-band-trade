"""
현재 보유 중인 포지션 분석 (미실현 손익 포함)
2025년 1월 백테스트에서 매수 후 아직 매도되지 않은 종목들
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

# 기존 함수들 재사용
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
            'Volume': df['Volume'],
            'Adj Close': df['Adj Close']
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


def analyze_open_positions(data: pd.DataFrame) -> Tuple[List[Dict], Dict]:
    """보유 포지션 및 미실현 손익 분석"""
    # 기술지표 계산
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

    # 신호 생성 및 포지션 추적
    signals = []
    positions = []
    current_position = 0
    open_positions = []  # 열린 포지션들
    closed_trades = []   # 완료된 거래들
    current_buy_price = None
    current_buy_date = None

    for i in range(len(data)):
        signal = 'HOLD'

        if i < 30:
            signals.append(signal)
            positions.append(current_position)
            continue

        # 매수 신호 조건
        if (current_position == 0 and
            data.iloc[i]['Close'] > data.iloc[i]['BB_Upper'] and
            data.iloc[i]['Volume_Filter'] and
            30 <= data.iloc[i]['RSI'] <= 70 and
            data.iloc[i]['MACD'] > data.iloc[i]['MACD_Signal']):

            signal = 'BUY'
            current_position = 1
            current_buy_price = data.iloc[i]['Close']
            current_buy_date = data.index[i]

        # 매도 신호 조건
        elif (current_position == 1 and
              (data.iloc[i]['Close'] < data.iloc[i]['BB_Lower'] or
               data.iloc[i]['Close'] < current_buy_price * 0.95)):

            signal = 'SELL'
            sell_price = data.iloc[i]['Close']
            sell_date = data.index[i]

            # 완료된 거래 기록
            return_pct = (sell_price - current_buy_price) / current_buy_price * 100
            closed_trades.append({
                'buy_date': current_buy_date,
                'sell_date': sell_date,
                'buy_price': current_buy_price,
                'sell_price': sell_price,
                'return_pct': return_pct
            })

            current_position = 0
            current_buy_price = None
            current_buy_date = None

        signals.append(signal)
        positions.append(current_position)

    # 마지막에 여전히 보유 중인 포지션 확인
    if current_position == 1 and current_buy_price is not None:
        latest_price = data['Close'].iloc[-1]
        latest_date = data.index[-1]
        unrealized_return = (latest_price - current_buy_price) / current_buy_price * 100

        open_positions.append({
            'buy_date': current_buy_date,
            'buy_price': current_buy_price,
            'current_price': latest_price,
            'current_date': latest_date,
            'unrealized_return_pct': unrealized_return,
            'days_held': (latest_date - current_buy_date).days if hasattr((latest_date - current_buy_date), 'days') else 0
        })

    # 성과 요약
    performance_summary = {
        'closed_trades': len(closed_trades),
        'open_positions': len(open_positions),
        'closed_total_return': sum([t['return_pct'] for t in closed_trades]) if closed_trades else 0,
        'unrealized_total_return': sum([p['unrealized_return_pct'] for p in open_positions]) if open_positions else 0,
        'combined_total_return': 0
    }

    if closed_trades or open_positions:
        all_returns = [t['return_pct'] for t in closed_trades] + [p['unrealized_return_pct'] for p in open_positions]
        performance_summary['combined_total_return'] = sum(all_returns)
        performance_summary['avg_return_per_position'] = np.mean(all_returns)

    return open_positions, performance_summary


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
        '282330': 'BGF리테일', '138930': 'BNK금융지주', '003230': '삼양식품', '011780': '금호석유',
        '298050': '효성첨단소재', '298020': '효성티앤씨', '090430': '아모레퍼시픽', '010950': 'S-Oil',
        '241560': '두산밥캣', '267270': 'HD현대마린엔진', '006360': 'GS건설', '005940': 'NH투자증권',
        '000150': '두산', '047040': '대우건설', '008770': '호텔신라', '000120': 'CJ대한통운',
        '001430': '세아제강지주', '005850': '에스엘', '018880': '한온시스템', '011790': 'SKC'
    }
    return stock_names.get(stock_code, stock_code)


def analyze_all_open_positions():
    """모든 종목의 보유 포지션 분석"""
    print("="*80)
    print("🔍 2025년 보유 중인 포지션 분석 (미실현 손익 포함)")
    print("="*80)

    # 설정
    start_date = "2025-01-01"
    end_date = date.today().strftime('%Y-%m-%d')

    print(f"\n📅 분석 기간: {start_date} ~ {end_date}")

    # KOSPI Top 100 로드
    kospi_stocks = load_kospi_top100()
    print(f"📋 분석 대상: KOSPI Top 100 ({len(kospi_stocks)}개 종목)")

    all_open_positions = []
    all_performance = []

    print(f"\n[1] 종목별 포지션 분석 중...")

    for i, stock_code in enumerate(kospi_stocks):
        print(f"진행: {i+1}/{len(kospi_stocks)} ({stock_code})", end=" ")

        # 데이터 가져오기
        data = fetch_stock_data(stock_code, start_date, end_date)

        if data is not None and len(data) >= 15:
            # 포지션 분석
            open_positions, performance = analyze_open_positions(data)

            if open_positions or performance['closed_trades'] > 0:
                # 보유 포지션이 있는 종목들
                for pos in open_positions:
                    pos['stock_code'] = stock_code
                    pos['stock_name'] = get_stock_name(stock_code)
                    all_open_positions.append(pos)

                # 성과 정보 저장
                performance['stock_code'] = stock_code
                performance['stock_name'] = get_stock_name(stock_code)
                all_performance.append(performance)
                print("✓")
            else:
                print("○")
        else:
            print("✗")

    # 결과 분석
    print(f"\n[2] 결과 요약...")

    # 현재 보유 중인 포지션만 필터
    current_holdings = [pos for pos in all_open_positions if pos.get('unrealized_return_pct') is not None]

    if not current_holdings:
        print("⚠️ 현재 보유 중인 포지션이 없습니다.")
        return

    print(f"\n✅ 현재 보유 중인 포지션: {len(current_holdings)}개")

    # 포지션별 상세 정보
    print("\n" + "="*80)
    print("📊 현재 보유 포지션 상세 분석")
    print("="*80)

    # 수익률 기준 정렬
    current_holdings.sort(key=lambda x: x['unrealized_return_pct'], reverse=True)

    # 상위 보유 종목 표시
    print(f"\n🏆 보유 포지션 수익률 순위:")
    print("┌──────────┬────────────────┬──────────┬──────────┬──────────┬──────────┐")
    print("│ 종목코드 │    종목명      │ 매수가격 │ 현재가격 │ 미실현수익│ 보유일수 │")
    print("├──────────┼────────────────┼──────────┼──────────┼──────────┼──────────┤")

    total_unrealized = 0
    profitable_positions = 0

    for i, pos in enumerate(current_holdings[:20]):  # 상위 20개만 표시
        status_emoji = "🟢" if pos['unrealized_return_pct'] > 0 else "🔴"

        if pos['unrealized_return_pct'] > 0:
            profitable_positions += 1
        total_unrealized += pos['unrealized_return_pct']

        print(f"│ {pos['stock_code']:8s} │ {pos['stock_name'][:14]:14s} │ {pos['buy_price']:8.0f} │ {pos['current_price']:8.0f} │ {status_emoji}{pos['unrealized_return_pct']:7.2f}% │ {pos['days_held']:6d}일 │")

    print("└──────────┴────────────────┴──────────┴──────────┴──────────┴──────────┘")

    # 통계 요약
    print(f"\n📈 보유 포지션 통계:")
    avg_unrealized = total_unrealized / len(current_holdings) if current_holdings else 0
    unrealized_win_rate = (profitable_positions / len(current_holdings) * 100) if current_holdings else 0

    print(f"  총 보유 포지션:       {len(current_holdings)}개")
    print(f"  수익 포지션:          {profitable_positions}개")
    print(f"  손실 포지션:          {len(current_holdings) - profitable_positions}개")
    print(f"  미실현 승률:          {unrealized_win_rate:.1f}%")
    print(f"  평균 미실현 수익률:   {avg_unrealized:+.2f}%")
    print(f"  총 미실현 수익률:     {total_unrealized:+.2f}%")

    if current_holdings:
        best_position = max(current_holdings, key=lambda x: x['unrealized_return_pct'])
        worst_position = min(current_holdings, key=lambda x: x['unrealized_return_pct'])

        print(f"\n🌟 최고 수익 포지션:")
        print(f"  {best_position['stock_name']} ({best_position['stock_code']})")
        print(f"  미실현 수익률: {best_position['unrealized_return_pct']:+.2f}%")
        print(f"  매수가: {best_position['buy_price']:,.0f}원")
        print(f"  현재가: {best_position['current_price']:,.0f}원")

        print(f"\n📉 최악 손실 포지션:")
        print(f"  {worst_position['stock_name']} ({worst_position['stock_code']})")
        print(f"  미실현 손실: {worst_position['unrealized_return_pct']:+.2f}%")
        print(f"  매수가: {worst_position['buy_price']:,.0f}원")
        print(f"  현재가: {worst_position['current_price']:,.0f}원")

    # 전체 성과에 미치는 영향
    total_closed_return = sum([perf['closed_total_return'] for perf in all_performance if perf.get('closed_total_return')])
    total_unrealized_return = sum([perf['unrealized_total_return'] for perf in all_performance if perf.get('unrealized_total_return')])
    combined_return = total_closed_return + total_unrealized_return

    print(f"\n💰 전체 성과 비교 (미실현 손익 포함):")
    print(f"  완료된 거래 수익률:   {total_closed_return:+.2f}%")
    print(f"  미실현 수익률:        {total_unrealized_return:+.2f}%")
    print(f"  전체 수익률:          {combined_return:+.2f}%")
    print(f"  미실현 기여도:        {(total_unrealized_return/combined_return*100) if combined_return != 0 else 0:.1f}%")

    improvement = combined_return - total_closed_return
    print(f"\n📊 미실현 손익 영향:")
    if improvement > 0:
        print(f"  ✅ 추가 수익: +{improvement:.2f}%p")
        print(f"  💡 실제 성과가 보고된 성과보다 우수함")
    else:
        print(f"  ⚠️ 추가 손실: {improvement:.2f}%p")
        print(f"  💡 보유 포지션에서 손실 발생 중")


if __name__ == "__main__":
    analyze_all_open_positions()
    print(f"\n" + "="*80)
    print("✅ 보유 포지션 분석 완료")
    print("="*80)