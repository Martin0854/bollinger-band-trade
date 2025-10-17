# 암호화폐 백테스트 지원을 위한 마이그레이션 가이드

## 개요

본 문서는 현재 **한국 주식 시장(KOSPI/KOSDAQ)** 전용으로 구현된 백테스트 시스템을 **암호화폐 시장**에서도 사용할 수 있도록 확장하기 위해 필요한 코드 변경사항을 정리합니다.

### 현재 상태
- **타겟 시장**: 한국 주식 (KOSPI/KOSDAQ)
- **데이터 소스**: Yahoo Finance (`yfinance`)
- **자산 식별**: 6자리 숫자 종목코드 (예: `005930`)
- **거래 시간**: 주식 시장 거래 시간 (평일 09:00-15:30 KST)

### 목표 상태
- **타겟 시장**: 주식 + 암호화폐 (Bitcoin, Ethereum 등)
- **데이터 소스**: 주식(yfinance) + 암호화폐(Binance API, CoinGecko 등)
- **자산 식별**: 유연한 티커 시스템 (예: `BTC-USD`, `ETH-USD`)
- **거래 시간**: 24/7 거래 지원

---

## 1. 데이터 레이어 (Data Layer)

### 1.1 데이터 소스 추상화

**현재 문제점**:
- `examples/` 디렉토리의 모든 스크립트가 `yfinance`에 직접 의존
- 한국 주식 전용 티커 형식 하드코딩 (`.KS`, `.KQ` 접미사)

**위치**:
- `examples/phase1_mvp_kospi100.py:14-44`
- `examples/phase1_yearly_comparison.py`
- 기타 모든 `examples/` 및 `runs/scripts/` 파일

**필요한 변경**:

#### 1.1.1 데이터 제공자 인터페이스 생성

```python
# src/data/providers/base.py (신규)
from abc import ABC, abstractmethod
from datetime import date
from typing import Optional
import pandas as pd

class MarketDataProvider(ABC):
    """시장 데이터 제공자 추상 인터페이스"""

    @abstractmethod
    def fetch_ohlcv(
        self,
        symbol: str,
        start_date: date,
        end_date: date
    ) -> Optional[pd.DataFrame]:
        """
        OHLCV 데이터 가져오기

        Returns:
            DataFrame with columns: Open, High, Low, Close, Volume
            Index: datetime (timezone-aware if 24/7 market)
        """
        pass

    @abstractmethod
    def validate_symbol(self, symbol: str) -> bool:
        """심볼 형식 검증"""
        pass

    @abstractmethod
    def get_market_type(self) -> str:
        """시장 타입 반환 ('stock', 'crypto')"""
        pass
```

#### 1.1.2 구체적 구현체

```python
# src/data/providers/stock_provider.py (신규)
class YahooFinanceStockProvider(MarketDataProvider):
    """한국 주식 데이터 제공자 (yfinance)"""

    def fetch_ohlcv(self, symbol: str, start_date: date, end_date: date) -> Optional[pd.DataFrame]:
        # 기존 fetch_stock_data() 로직 이전
        ticker = f"{symbol}.KS"  # KOSPI
        # ... yfinance 호출

    def validate_symbol(self, symbol: str) -> bool:
        # 6자리 숫자 검증
        return symbol.isdigit() and len(symbol) == 6

    def get_market_type(self) -> str:
        return "stock"
```

```python
# src/data/providers/crypto_provider.py (신규)
class BinanceCryptoProvider(MarketDataProvider):
    """암호화폐 데이터 제공자 (Binance API)"""

    def __init__(self, testnet: bool = False):
        # Binance API 클라이언트 초기화
        # 주의: API 키 불필요 (공개 OHLCV 데이터만 사용)
        pass

    def fetch_ohlcv(self, symbol: str, start_date: date, end_date: date) -> Optional[pd.DataFrame]:
        """
        Binance에서 OHLCV 가져오기

        Args:
            symbol: "BTCUSDT", "ETHUSDT" 등

        Returns:
            DataFrame with timezone-aware index (UTC)
        """
        # Binance Klines API 호출
        # 1. 날짜를 timestamp로 변환
        # 2. Klines 엔드포인트 호출 (/api/v3/klines)
        # 3. 결과를 OHLCV DataFrame으로 변환
        # 4. timezone을 UTC로 설정
        pass

    def validate_symbol(self, symbol: str) -> bool:
        # Binance 페어 형식 검증 (예: BTCUSDT, ETHUSDT)
        return symbol.endswith("USDT") and len(symbol) >= 6

    def get_market_type(self) -> str:
        return "crypto"
```

#### 1.1.3 팩토리 패턴

```python
# src/data/providers/factory.py (신규)
from typing import Optional
from .base import MarketDataProvider
from .stock_provider import YahooFinanceStockProvider
from .crypto_provider import BinanceCryptoProvider

class DataProviderFactory:
    """데이터 제공자 팩토리"""

    @staticmethod
    def create_provider(market_type: str, **kwargs) -> MarketDataProvider:
        if market_type == "stock":
            return YahooFinanceStockProvider()
        elif market_type == "crypto":
            return BinanceCryptoProvider(**kwargs)
        else:
            raise ValueError(f"Unsupported market type: {market_type}")
```

### 1.2 캐싱 레이어 수정

**위치**: `src/data/storage.py:135-189`

**현재 문제점**:
- Parquet 파일명이 `{stock_code}_{start_date}_{end_date}.parquet` 형식으로 고정
- 암호화폐 심볼(예: `BTC-USD`)에는 적합하지 않음

**필요한 변경**:

```python
# src/data/storage.py 수정
def save_to_parquet(
    df: pd.DataFrame,
    symbol: str,  # stock_code -> symbol로 이름 변경
    start_date: date,
    end_date: date,
    market_type: str = "stock",  # 신규 파라미터
    cache_dir: str = "data/cache"
) -> str:
    """
    Save DataFrame to Parquet file with compression.

    Args:
        symbol: Asset symbol (stock code or crypto pair)
        market_type: "stock" or "crypto"
    """
    Path(cache_dir).mkdir(parents=True, exist_ok=True)

    # 심볼에서 특수문자 제거 (파일명 안전성)
    safe_symbol = symbol.replace("-", "").replace("/", "")
    filename = f"{market_type}_{safe_symbol}_{start_date}_{end_date}.parquet"
    filepath = Path(cache_dir) / filename

    df.to_parquet(filepath, engine='pyarrow', compression='snappy')
    return str(filepath)
```

---

## 2. 설정 모델 (Configuration)

### 2.1 심볼 검증 로직 확장

**위치**: `src/models/config.py:212-222`

**현재 문제점**:
```python
@field_validator('stocks')
@classmethod
def validate_stock_codes(cls, v: List[str]) -> List[str]:
    """6자리 숫자만 허용"""
    for code in v:
        if not (code.isdigit() and len(code) == 6):
            raise ValueError(f"Invalid stock code: '{code}'")
    return v
```

**필요한 변경**:

#### 2.1.1 시장 타입 필드 추가

```python
# src/models/config.py 수정
class BacktestConfiguration(BaseModel):
    # 기존 필드들...

    # 신규 필드 추가
    market_type: str = Field(
        default="stock",
        description="Market type: 'stock' or 'crypto'"
    )

    # 기존 stocks 필드 이름 변경
    symbols: List[str] = Field(  # stocks -> symbols
        min_length=1,
        description="Asset symbols (stock codes or crypto pairs)"
    )

    @field_validator('market_type')
    @classmethod
    def validate_market_type(cls, v: str) -> str:
        if v not in ["stock", "crypto"]:
            raise ValueError(f"market_type must be 'stock' or 'crypto', got '{v}'")
        return v

    @field_validator('symbols')
    @classmethod
    def validate_symbols(cls, v: List[str], info) -> List[str]:
        """시장 타입에 따라 심볼 검증"""
        market_type = info.data.get('market_type', 'stock')

        if market_type == "stock":
            # 한국 주식: 6자리 숫자
            for symbol in v:
                if not (symbol.isdigit() and len(symbol) == 6):
                    raise ValueError(
                        f"Invalid stock code: '{symbol}'. "
                        f"Korean stock codes must be exactly 6 digits"
                    )
        elif market_type == "crypto":
            # 암호화폐: 기본 형식 검증 (예: BTCUSDT, BTC-USD)
            for symbol in v:
                if not symbol or len(symbol) < 3:
                    raise ValueError(
                        f"Invalid crypto symbol: '{symbol}'. "
                        f"Must be at least 3 characters"
                    )

        return v
```

#### 2.1.2 암호화폐 전용 설정 추가

```python
# src/models/config.py 추가
class CryptoSpecificConfig(BaseModel):
    """암호화폐 시장 전용 설정"""

    trading_fee_percent: float = Field(
        default=0.1,  # Binance 기본 수수료 0.1%
        description="Trading fee (maker/taker average)"
    )

    min_order_value_usdt: float = Field(
        default=10.0,
        description="Minimum order value in USDT"
    )

    quote_currency: str = Field(
        default="USDT",
        description="Quote currency (USDT, BTC, etc.)"
    )

class BacktestConfiguration(BaseModel):
    # ... 기존 필드들

    # 암호화폐 설정 (옵셔널)
    crypto_config: Optional[CryptoSpecificConfig] = Field(
        default=None,
        description="Crypto-specific settings (only for market_type='crypto')"
    )
```

### 2.2 YAML 설정 파일 예시

```yaml
# config/examples/crypto_btc_eth.yaml (신규)
market_type: crypto
seed_money: 10000  # 10,000 USDT
symbols:
  - BTCUSDT
  - ETHUSDT
  - BNBUSDT

date_range:
  start: "2023-01-01"
  end: "2024-01-01"

# Bollinger Band 설정 (동일)
bollinger_period: 20
bollinger_std_dev: 2.0

# 리스크 관리
stop_loss_percent: 5.0
max_position_percent: 30.0
max_positions: 3

# 암호화폐 전용 설정
crypto_config:
  trading_fee_percent: 0.1
  min_order_value_usdt: 10.0
  quote_currency: USDT

# Enhanced Strategy (동일하게 사용 가능)
enhanced_strategy:
  volume_filter:
    enabled: true
    window_days: 20
    multiplier: 1.5

  rsi:
    enabled: true
    period: 14
    overbought: 70
    oversold: 30
```

---

## 3. 백테스트 엔진 (Backtest Engine)

**현재 상태**: `src/backtest/engine.py`는 **이미 시장 중립적으로 설계**되어 있음
- OHLCV DataFrame만 받으면 동작
- 특정 시장에 종속적인 로직 없음

**필요한 변경**: ✅ **최소 변경 필요**

### 3.1 데이터 로딩 메서드 수정

**위치**: `src/backtest/engine.py:111-119`

```python
# 현재 (변경 없음, 그대로 사용 가능)
def load_mock_data(self, stock_code: str, df: pd.DataFrame) -> None:
    """Load mock OHLCV data for testing."""
    self.mock_data[stock_code] = df

# 선택사항: 메서드명 일반화
def load_market_data(self, symbol: str, df: pd.DataFrame) -> None:
    """Load OHLCV data (stock or crypto)."""
    self.mock_data[symbol] = df
```

### 3.2 거래 수수료 적용

**위치**: `src/backtest/engine.py:354-524` (매수/매도 메서드)

**현재 문제점**:
- `transaction_cost_percent` 설정은 있지만 암호화폐 거래소 수수료 구조와 다를 수 있음
- 암호화폐는 maker/taker 수수료 차이 존재

**권장 변경**:

```python
# src/backtest/engine.py 수정
def _execute_buy(self, ...):
    # 기존 로직...

    # 거래 비용 계산
    if self.config.market_type == "crypto" and self.config.crypto_config:
        fee_percent = self.config.crypto_config.trading_fee_percent
    else:
        fee_percent = self.config.transaction_cost_percent

    transaction_cost = trade_value * Decimal(str(fee_percent / 100))
    total_cost = trade_value + transaction_cost

    # ... 나머지 로직
```

---

## 4. 리스크 관리 (Risk Management)

**위치**: `src/risk/controls.py`

**현재 상태**: ✅ **시장 독립적 설계**
- `calculate_trade_value()`, `check_stop_loss()` 등 모두 범용 함수
- 특정 시장에 종속적인 로직 없음

**필요한 변경**: ✅ **변경 불필요**

### 4.1 암호화폐 특화 고려사항 (선택사항)

암호화폐 시장의 특성을 반영하려면:

```python
# src/risk/crypto_controls.py (신규, 선택사항)
def calculate_crypto_position_size(
    cash_balance: Decimal,
    max_position_percent: float,
    current_price: Decimal,
    min_order_value: float = 10.0  # USDT
) -> int:
    """
    암호화폐 포지션 크기 계산

    차이점:
    - 최소 주문 금액 검증 (거래소 정책)
    - 소수점 수량 가능 (주식은 정수만 가능)
    """
    max_value = cash_balance * Decimal(str(max_position_percent / 100))

    # 최소 주문 금액 체크
    if max_value < Decimal(str(min_order_value)):
        return 0

    # 암호화폐는 소수점 수량 허용
    quantity = max_value / current_price

    # 거래소별 LOT SIZE 규칙 적용 필요
    # (예: Binance BTC는 0.00001 BTC 단위)
    return quantity
```

**주의**: 현재 `Trade` 모델의 `quantity`는 `int` 타입입니다.
암호화폐 지원을 위해 `Decimal`로 변경 필요:

```python
# src/models/trade.py 수정 필요
@dataclass
class Trade:
    quantity: Decimal  # int -> Decimal로 변경
```

---

## 5. 모델 레이어 (Models)

### 5.1 StockData → MarketData 리네이밍

**위치**: `src/models/stock_data.py:15-186`

**필요한 변경**:

```python
# src/models/market_data.py (stock_data.py 이름 변경)
@dataclass
class MarketData:  # StockData -> MarketData
    """
    시장 데이터 래퍼 (주식/암호화폐 공통)

    Attributes:
        symbol: 자산 심볼 (주식 코드 또는 암호화폐 페어)
        market_type: "stock" or "crypto"
        ohlcv: DataFrame with Open, High, Low, Close, Volume
        ...
    """
    symbol: str  # stock_code -> symbol
    market_type: str  # 신규 필드
    ohlcv: pd.DataFrame
    start_date: date
    end_date: date
    bollinger_bands: Optional[pd.DataFrame] = None
    squeeze_events: list = field(default_factory=list)

    def __post_init__(self):
        """검증"""
        # 시장별 심볼 검증은 config 레벨에서 이미 완료되었다고 가정
        validate_ohlcv_dataframe(self.ohlcv, self.symbol)
        # ...
```

### 5.2 Trade 모델 수정

**위치**: `src/models/trade.py`

```python
# src/models/trade.py 수정
@dataclass
class Trade:
    trade_id: str
    execution_timestamp: datetime
    symbol: str  # stock_code -> symbol로 이름 변경
    action: TradeAction
    quantity: Decimal  # int -> Decimal (암호화폐 소수점 지원)
    execution_price: Decimal

    # 메타데이터
    market_type: str = "stock"  # 신규 필드

    # ... 기타 필드
```

---

## 6. 데이터베이스 스키마 (Logging)

**위치**: `src/data/storage.py:37-132`

**필요한 변경**:

```sql
-- trade_log 테이블 수정
CREATE TABLE IF NOT EXISTS trade_log (
    trade_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    symbol TEXT NOT NULL,          -- stock_code -> symbol
    market_type TEXT NOT NULL,      -- 신규 컬럼: "stock" or "crypto"
    action TEXT NOT NULL,
    quantity REAL NOT NULL,         -- INTEGER -> REAL (소수점 지원)
    price REAL NOT NULL,
    -- ... 기타 컬럼
);

-- squeeze_events 테이블도 동일하게 수정
CREATE TABLE IF NOT EXISTS squeeze_events (
    event_id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,           -- stock_code -> symbol
    market_type TEXT NOT NULL,      -- 신규 컬럼
    detection_date TEXT NOT NULL,
    -- ...
);
```

---

## 7. 인디케이터 레이어 (Indicators)

**위치**: `src/indicators/`

**현재 상태**: ✅ **시장 독립적 설계**
- Bollinger Bands, RSI, MACD, ATR 모두 OHLCV만 필요
- 특정 시장 로직 없음

**필요한 변경**: ✅ **변경 불필요**

---

## 8. 예제 스크립트 (Examples)

### 8.1 암호화폐 백테스트 예제 생성

```python
# examples/crypto_btc_eth_backtest.py (신규)
"""
암호화폐 백테스트 예제 - BTC, ETH, BNB
"""
from src.data.providers.factory import DataProviderFactory
from src.models.config import BacktestConfiguration
from src.backtest.engine import BacktestEngine

# Step 1: 설정 로드
config = BacktestConfiguration.from_yaml("config/examples/crypto_btc_eth.yaml")
print(f"Market Type: {config.market_type}")
print(f"Symbols: {config.symbols}")
print(f"Fee: {config.crypto_config.trading_fee_percent}%")

# Step 2: 데이터 제공자 생성
provider = DataProviderFactory.create_provider(
    market_type=config.market_type
)

# Step 3: 데이터 다운로드
engine = BacktestEngine(config=config)

for symbol in config.symbols:
    print(f"Fetching {symbol}...", end=" ")

    df = provider.fetch_ohlcv(
        symbol=symbol,
        start_date=config.date_range[0],
        end_date=config.date_range[1]
    )

    if df is not None:
        engine.load_market_data(symbol, df)
        print(f"✅ {len(df)} candles")
    else:
        print("❌ Failed")

# Step 4: 백테스트 실행
report = engine.run()

# Step 5: 결과 출력
print("\n" + "=" * 80)
print(f"Crypto Backtest Results")
print("=" * 80)
print(f"Total Return: {report.total_return_pct:.2f}%")
print(f"Win Rate: {report.win_rate_pct:.2f}%")
print(f"Max Drawdown: {report.max_drawdown_pct:.2f}%")
print(f"Sharpe Ratio: {report.sharpe_ratio:.2f}")
```

---

## 9. 테스트 (Tests)

### 9.1 암호화폐 데이터 제공자 테스트

```python
# tests/unit/test_crypto_provider.py (신규)
import pytest
from datetime import date
from src.data.providers.crypto_provider import BinanceCryptoProvider

def test_fetch_btc_ohlcv():
    provider = BinanceCryptoProvider()

    df = provider.fetch_ohlcv(
        symbol="BTCUSDT",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31)
    )

    assert df is not None
    assert len(df) > 0
    assert all(col in df.columns for col in ['Open', 'High', 'Low', 'Close', 'Volume'])
    assert df.index.tz is not None  # Timezone-aware

def test_validate_crypto_symbol():
    provider = BinanceCryptoProvider()

    assert provider.validate_symbol("BTCUSDT") == True
    assert provider.validate_symbol("ETHUSDT") == True
    assert provider.validate_symbol("INVALID") == False
```

### 9.2 설정 검증 테스트

```python
# tests/unit/test_crypto_config.py (신규)
from src.models.config import BacktestConfiguration

def test_crypto_config_validation():
    config = BacktestConfiguration(
        market_type="crypto",
        symbols=["BTCUSDT", "ETHUSDT"],
        seed_money=10000,
        date_range=(date(2023, 1, 1), date(2024, 1, 1))
    )

    assert config.market_type == "crypto"
    assert len(config.symbols) == 2

def test_invalid_crypto_symbol():
    with pytest.raises(ValueError):
        BacktestConfiguration(
            market_type="crypto",
            symbols=["BTC"],  # 너무 짧음
            seed_money=10000,
            date_range=(date(2023, 1, 1), date(2024, 1, 1))
        )
```

---

## 10. 구현 우선순위 및 단계

### Phase 1: 기본 인프라 (1-2주)
1. ✅ `MarketDataProvider` 인터페이스 생성
2. ✅ `BinanceCryptoProvider` 구현
3. ✅ `DataProviderFactory` 구현
4. ✅ 설정 모델에 `market_type` 추가
5. ✅ 심볼 검증 로직 확장

### Phase 2: 모델 및 스토리지 (1주)
6. ✅ `StockData` → `MarketData` 리네이밍
7. ✅ `Trade.quantity`를 `Decimal`로 변경
8. ✅ 데이터베이스 스키마 마이그레이션
9. ✅ Parquet 캐싱 수정

### Phase 3: 백테스트 엔진 통합 (1주)
10. ✅ 백테스트 엔진에 데이터 제공자 통합
11. ✅ 암호화폐 수수료 로직 추가
12. ✅ 예제 스크립트 작성 (`examples/crypto_*.py`)

### Phase 4: 테스트 및 검증 (1주)
13. ✅ 단위 테스트 작성 (암호화폐 제공자)
14. ✅ 통합 테스트 (BTC/ETH 백테스트)
15. ✅ 성능 테스트 (24/7 데이터 처리)

### Phase 5: 문서화 및 배포 (3일)
16. ✅ README 업데이트
17. ✅ 암호화폐 백테스트 가이드 작성
18. ✅ 설정 파일 예제 추가

---

## 11. 암호화폐 특화 고려사항

### 11.1 24/7 거래 시간
- **주식**: 평일만 거래 (주말/공휴일 제외)
- **암호화폐**: 24시간 365일 거래

**영향**:
- Bollinger Band 계산 시 주말 제외 로직 불필요
- Squeeze lookback days 설정 시 연속 7일 고려 가능

### 11.2 높은 변동성
- 암호화폐는 주식 대비 변동성이 훨씬 높음
- **권장 파라미터 조정**:
  ```yaml
  bollinger_std_dev: 2.5  # 주식: 2.0 → 암호화폐: 2.5
  stop_loss_percent: 8.0  # 주식: 5.0 → 암호화폐: 8.0
  squeeze_threshold_percent: 40.0  # 주식: 30.0 → 암호화폐: 40.0
  ```

### 11.3 최소 주문 금액
- Binance: 최소 10 USDT
- Upbit: 최소 5,000 KRW

**대응**:
```python
# src/risk/controls.py 수정
def validate_minimum_order_value(
    quantity: Decimal,
    price: Decimal,
    min_value: Decimal
) -> bool:
    """최소 주문 금액 검증"""
    return (quantity * price) >= min_value
```

### 11.4 거래 수수료 구조
| 거래소 | Maker Fee | Taker Fee |
|--------|-----------|-----------|
| Binance | 0.10% | 0.10% |
| Upbit | 0.05% | 0.05% |
| Coinbase | 0.40% | 0.60% |

**권장**: 평균값(0.1%) 사용 또는 거래소별 설정 추가

### 11.5 정밀도 (Precision)
- BTC: 8자리 (0.00000001 BTC)
- ETH: 18자리 (0.000000000000000001 ETH)

**대응**:
```python
from decimal import Decimal, getcontext

# 높은 정밀도 설정
getcontext().prec = 28
```

---

## 12. 체크리스트

### 필수 변경사항
- [ ] `MarketDataProvider` 인터페이스 구현
- [ ] `BinanceCryptoProvider` 구현
- [ ] `BacktestConfiguration`에 `market_type` 필드 추가
- [ ] 심볼 검증 로직 확장 (`validate_symbols`)
- [ ] `Trade.quantity`를 `int` → `Decimal`로 변경
- [ ] `stock_code` → `symbol` 전역 리네이밍
- [ ] 데이터베이스 스키마 마이그레이션
- [ ] Parquet 캐싱에 `market_type` 추가

### 선택 변경사항
- [ ] `StockData` → `MarketData` 리네이밍
- [ ] 암호화폐 전용 `CryptoSpecificConfig` 추가
- [ ] Maker/Taker 수수료 분리
- [ ] 최소 주문 금액 검증 추가
- [ ] 소수점 수량 LOT SIZE 규칙 구현

### 테스트
- [ ] `BinanceCryptoProvider` 단위 테스트
- [ ] 암호화폐 설정 검증 테스트
- [ ] BTC/ETH 통합 백테스트
- [ ] 24/7 데이터 처리 성능 테스트

### 문서
- [ ] README에 암호화폐 섹션 추가
- [ ] 암호화폐 백테스트 예제 작성
- [ ] 설정 파일 예제 (`config/examples/crypto_*.yaml`)

---

## 13. 참고 자료

### Binance API
- **Docs**: https://binance-docs.github.io/apidocs/spot/en/
- **Klines Endpoint**: `/api/v3/klines` (OHLCV 데이터)
- **Python SDK**: `python-binance` (pip install python-binance)

### 대체 데이터 소스
- **CCXT**: 통합 암호화폐 거래소 라이브러리 (100+ 거래소 지원)
  - `pip install ccxt`
  - 장점: 단일 인터페이스로 여러 거래소 지원
  - 단점: yfinance보다 느림

- **CoinGecko API**: 무료, API 키 불필요
  - 장점: 무료, 간단함
  - 단점: Rate limit 낮음 (50 req/min)

### 권장 라이브러리
```toml
# pyproject.toml 추가 의존성
[tool.poetry.dependencies]
python-binance = "^1.0.17"  # Binance API
ccxt = "^4.1.0"  # 통합 거래소 API (선택)
```

---

## 14. 마이그레이션 예상 시간

| 단계 | 작업 | 예상 시간 |
|------|------|-----------|
| Phase 1 | 데이터 제공자 인프라 | 1-2주 |
| Phase 2 | 모델 및 스토리지 | 1주 |
| Phase 3 | 백테스트 엔진 통합 | 1주 |
| Phase 4 | 테스트 및 검증 | 1주 |
| Phase 5 | 문서화 | 3일 |
| **총계** | | **4-5주** |

---

## 15. 질문 및 피드백

구현 중 추가 질문이나 피드백이 있다면:
1. 설계 리뷰 요청: 각 Phase 완료 후
2. 성능 테스트: Phase 3 완료 후 실제 데이터로 검증
3. 사용자 피드백: Phase 4에서 베타 테스터 모집

---

**작성일**: 2025-10-17
**버전**: 1.0
**작성자**: Claude Code (Automated Analysis)
