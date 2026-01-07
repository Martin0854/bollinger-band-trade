# Data Model: Trading Wizard Web

**Feature**: 004-trading-wizard-web
**Date**: 2026-01-05
**Status**: Complete

## Entity Relationship Diagram

```
┌─────────────┐     1:1      ┌─────────────────┐
│    User     │──────────────│    Portfolio    │
└─────────────┘              └─────────────────┘
      │                              │
      │ 1:N                          │ 1:N
      ▼                              ▼
┌─────────────────┐          ┌─────────────────┐
│  UserSettings   │          │    Position     │
└─────────────────┘          └─────────────────┘
      │
      │ 1:N
      ▼
┌─────────────────┐          ┌─────────────────┐
│ BacktestResult  │          │     Trade       │
└─────────────────┘          └─────────────────┘
                                     ▲
                                     │ N:1
                                     │
                             ┌───────┴───────┐
                             │   Portfolio   │
                             └───────────────┘
```

## Entities

### 1. User

사용자 계정. PEM 키 기반 인증으로 개인정보 미수집.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | 고유 식별자 |
| public_key | TEXT | NOT NULL, UNIQUE | ECDSA P-256 공개키 (PEM 형식) |
| fingerprint | VARCHAR(64) | NOT NULL, UNIQUE, INDEX | 공개키 SHA-256 핑거프린트 (사용자 ID로 사용) |
| nickname | VARCHAR(50) | NULLABLE | 표시용 닉네임 (선택) |
| created_at | DATETIME | NOT NULL, DEFAULT NOW | 가입일 |
| last_login_at | DATETIME | NULLABLE | 마지막 로그인 |

**Validation Rules**:
- `public_key`: 유효한 ECDSA P-256 PEM 형식
- `fingerprint`: 64자 hex string (SHA-256)
- `nickname`: 최대 50자, 특수문자 제한

**Index**:
- `idx_user_fingerprint` ON (fingerprint)

---

### 2. Portfolio

사용자의 포트폴리오. User와 1:1 관계.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | 고유 식별자 |
| user_id | UUID | FK(User.id), UNIQUE | 소유자 |
| initial_capital | DECIMAL(15,2) | NOT NULL, DEFAULT 1000000 | 초기자본 (KRW) |
| cash_balance | DECIMAL(15,2) | NOT NULL | 현금잔고 (KRW) |
| created_at | DATETIME | NOT NULL, DEFAULT NOW | 생성일 |
| updated_at | DATETIME | NOT NULL | 마지막 수정일 |

**Validation Rules**:
- `initial_capital`: >= 0
- `cash_balance`: >= 0

**Business Rules**:
- 사용자당 1개의 포트폴리오만 존재
- 초기자본 설정 시 cash_balance도 동일하게 설정

---

### 3. Position

보유 종목. Portfolio와 N:1 관계.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | 고유 식별자 |
| portfolio_id | UUID | FK(Portfolio.id) | 소속 포트폴리오 |
| stock_code | VARCHAR(6) | NOT NULL | 종목코드 (6자리) |
| stock_name | VARCHAR(100) | NOT NULL | 종목명 |
| quantity | INTEGER | NOT NULL | 보유수량 |
| avg_entry_price | DECIMAL(12,2) | NOT NULL | 평균매수가 (KRW) |
| first_entry_date | DATE | NOT NULL | 최초 매수일 |
| entry_reason | VARCHAR(50) | NULLABLE | 매수 사유 (예: squeeze_breakout_buy) |
| confidence_score | INTEGER | NULLABLE | 신뢰도 점수 (0-100) |
| created_at | DATETIME | NOT NULL, DEFAULT NOW | 생성일 |
| updated_at | DATETIME | NOT NULL | 마지막 수정일 |

**Validation Rules**:
- `stock_code`: 정규식 `^[0-9]{6}$`
- `quantity`: > 0
- `avg_entry_price`: > 0
- `confidence_score`: 0-100 (NULLABLE)

**Unique Constraint**:
- `uq_position_portfolio_stock` ON (portfolio_id, stock_code)

**Business Rules**:
- 동일 종목 매수 시 평균매수가 재계산
- 전량 매도 시 Position 삭제

---

### 4. Trade

개별 거래 기록. Portfolio와 N:1 관계.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | 고유 식별자 |
| portfolio_id | UUID | FK(Portfolio.id), INDEX | 소속 포트폴리오 |
| trade_date | DATE | NOT NULL, INDEX | 거래일 |
| stock_code | VARCHAR(6) | NOT NULL, INDEX | 종목코드 |
| stock_name | VARCHAR(100) | NOT NULL | 종목명 |
| action | VARCHAR(4) | NOT NULL | 거래유형: 'BUY' or 'SELL' |
| quantity | INTEGER | NOT NULL | 거래수량 |
| price | DECIMAL(12,2) | NOT NULL | 거래단가 (KRW) |
| total_amount | DECIMAL(15,2) | NOT NULL | 거래금액 (quantity * price) |
| realized_pnl | DECIMAL(15,2) | NULLABLE | 실현손익 (SELL 시) |
| reason | VARCHAR(100) | NULLABLE | 거래사유 |
| created_at | DATETIME | NOT NULL, DEFAULT NOW | 입력일시 |

**Validation Rules**:
- `stock_code`: 정규식 `^[0-9]{6}$`
- `action`: ENUM('BUY', 'SELL')
- `quantity`: > 0
- `price`: > 0
- `total_amount`: = quantity * price

**Index**:
- `idx_trade_portfolio_date` ON (portfolio_id, trade_date DESC)
- `idx_trade_stock` ON (stock_code)

**Business Rules**:
- BUY: cash_balance 차감, Position 생성/업데이트
- SELL: Position 수량 감소, realized_pnl 계산, cash_balance 증가
- 매도 시 보유수량 초과 불가

---

### 5. BacktestResult

백테스트 결과. User와 N:1 관계.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | 고유 식별자 |
| user_id | UUID | FK(User.id), INDEX | 실행자 |
| name | VARCHAR(100) | NULLABLE | 결과 이름 (선택) |
| start_date | DATE | NOT NULL | 백테스트 시작일 |
| end_date | DATE | NOT NULL | 백테스트 종료일 |
| stock_list_name | VARCHAR(50) | NOT NULL | 종목리스트명 (예: kospi_top100_2025jan) |
| initial_capital | DECIMAL(15,2) | NOT NULL | 초기자본 |
| final_value | DECIMAL(15,2) | NOT NULL | 최종평가액 |
| total_return_pct | DECIMAL(8,4) | NOT NULL | 총 수익률 (%) |
| max_drawdown_pct | DECIMAL(8,4) | NOT NULL | 최대낙폭 (%) |
| total_trades | INTEGER | NOT NULL | 총 거래수 |
| winning_trades | INTEGER | NOT NULL | 승리 거래수 |
| win_rate_pct | DECIMAL(6,2) | NOT NULL | 승률 (%) |
| result_json | JSON | NOT NULL | 상세 결과 (trades, daily_values 등) |
| executed_at | DATETIME | NOT NULL, DEFAULT NOW | 실행일시 |

**Validation Rules**:
- `start_date` < `end_date`
- `win_rate_pct`: 0-100

**Index**:
- `idx_backtest_user_date` ON (user_id, executed_at DESC)

---

### 6. UserSettings

사용자 전략 설정. User와 1:1 관계.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | 고유 식별자 |
| user_id | UUID | FK(User.id), UNIQUE | 소유자 |
| max_positions | INTEGER | NOT NULL, DEFAULT 15 | 최대 포지션 수 |
| max_position_pct | DECIMAL(5,2) | NOT NULL, DEFAULT 10.00 | 종목당 최대 비중 (%) |
| stop_loss_pct | DECIMAL(5,2) | NOT NULL, DEFAULT 5.00 | 손절선 (%) |
| confidence_threshold | INTEGER | NOT NULL, DEFAULT 60 | 신뢰도 임계값 |
| created_at | DATETIME | NOT NULL, DEFAULT NOW | 생성일 |
| updated_at | DATETIME | NOT NULL | 마지막 수정일 |

**Validation Rules**:
- `max_positions`: 1-50 (Constitution: ≤15 권장)
- `max_position_pct`: 1-100 (Constitution: ≤10% 권장)
- `stop_loss_pct`: 1-50 (Constitution: 5% 기본)
- `confidence_threshold`: 0-100

**Business Rules**:
- Constitution III 준수: max_positions ≤ 15, max_position_pct ≤ 10%
- 사용자 설정 시 경고 표시 (권장값 초과 시)

---

## State Transitions

### Position Lifecycle

```
[없음] ─── BUY ───▶ [보유중] ─── 추가매수 ───▶ [보유중] (수량증가, 평균가 재계산)
                       │
                       │─── 일부매도 ───▶ [보유중] (수량감소)
                       │
                       └─── 전량매도 ───▶ [없음] (Position 삭제)
```

### Trade Processing

```python
# BUY 처리
def process_buy(portfolio, trade):
    # 1. 잔고 확인
    if portfolio.cash_balance < trade.total_amount:
        raise InsufficientBalanceError()

    # 2. 잔고 차감
    portfolio.cash_balance -= trade.total_amount

    # 3. Position 업데이트
    position = get_or_create_position(portfolio, trade.stock_code)
    if position.exists:
        # 평균매수가 재계산
        total_cost = position.avg_entry_price * position.quantity + trade.total_amount
        position.quantity += trade.quantity
        position.avg_entry_price = total_cost / position.quantity
    else:
        position.quantity = trade.quantity
        position.avg_entry_price = trade.price
        position.first_entry_date = trade.trade_date

# SELL 처리
def process_sell(portfolio, trade):
    position = get_position(portfolio, trade.stock_code)

    # 1. 보유수량 확인
    if position.quantity < trade.quantity:
        raise InsufficientQuantityError()

    # 2. 실현손익 계산
    trade.realized_pnl = (trade.price - position.avg_entry_price) * trade.quantity

    # 3. Position 업데이트
    position.quantity -= trade.quantity
    if position.quantity == 0:
        delete_position(position)

    # 4. 잔고 증가
    portfolio.cash_balance += trade.total_amount
```

---

## SQLAlchemy Models Preview

```python
from sqlalchemy import Column, String, Integer, Numeric, DateTime, ForeignKey, JSON, Enum
from sqlalchemy.dialects.sqlite import UUID
from sqlalchemy.orm import relationship
import enum

class TradeAction(enum.Enum):
    BUY = "BUY"
    SELL = "SELL"

class User(Base):
    __tablename__ = "users"

    id = Column(UUID, primary_key=True)
    public_key = Column(String, nullable=False, unique=True)
    fingerprint = Column(String(64), nullable=False, unique=True, index=True)
    nickname = Column(String(50), nullable=True)
    created_at = Column(DateTime, nullable=False)
    last_login_at = Column(DateTime, nullable=True)

    portfolio = relationship("Portfolio", back_populates="user", uselist=False)
    settings = relationship("UserSettings", back_populates="user", uselist=False)
    backtest_results = relationship("BacktestResult", back_populates="user")

class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(UUID, primary_key=True)
    user_id = Column(UUID, ForeignKey("users.id"), unique=True)
    initial_capital = Column(Numeric(15, 2), nullable=False, default=1000000)
    cash_balance = Column(Numeric(15, 2), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    user = relationship("User", back_populates="portfolio")
    positions = relationship("Position", back_populates="portfolio")
    trades = relationship("Trade", back_populates="portfolio")

class Position(Base):
    __tablename__ = "positions"
    __table_args__ = (
        UniqueConstraint('portfolio_id', 'stock_code', name='uq_position_portfolio_stock'),
    )

    id = Column(UUID, primary_key=True)
    portfolio_id = Column(UUID, ForeignKey("portfolios.id"))
    stock_code = Column(String(6), nullable=False)
    stock_name = Column(String(100), nullable=False)
    quantity = Column(Integer, nullable=False)
    avg_entry_price = Column(Numeric(12, 2), nullable=False)
    first_entry_date = Column(Date, nullable=False)
    entry_reason = Column(String(50), nullable=True)  # From trading_wizard_bundle
    confidence_score = Column(Integer, nullable=True)  # 0-100, from trading_wizard_bundle
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    portfolio = relationship("Portfolio", back_populates="positions")

class Trade(Base):
    __tablename__ = "trades"
    __table_args__ = (
        Index('idx_trade_portfolio_date', 'portfolio_id', 'trade_date'),
        Index('idx_trade_stock', 'stock_code'),
    )

    id = Column(UUID, primary_key=True)
    portfolio_id = Column(UUID, ForeignKey("portfolios.id"))
    trade_date = Column(Date, nullable=False)
    stock_code = Column(String(6), nullable=False)
    stock_name = Column(String(100), nullable=False)
    action = Column(Enum(TradeAction), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Numeric(12, 2), nullable=False)
    total_amount = Column(Numeric(15, 2), nullable=False)
    realized_pnl = Column(Numeric(15, 2), nullable=True)
    reason = Column(String(100), nullable=True)
    created_at = Column(DateTime, nullable=False)

    portfolio = relationship("Portfolio", back_populates="trades")

class BacktestResult(Base):
    __tablename__ = "backtest_results"

    id = Column(UUID, primary_key=True)
    user_id = Column(UUID, ForeignKey("users.id"), index=True)
    name = Column(String(100), nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    stock_list_name = Column(String(50), nullable=False)
    initial_capital = Column(Numeric(15, 2), nullable=False)
    final_value = Column(Numeric(15, 2), nullable=False)
    total_return_pct = Column(Numeric(8, 4), nullable=False)
    max_drawdown_pct = Column(Numeric(8, 4), nullable=False)
    total_trades = Column(Integer, nullable=False)
    winning_trades = Column(Integer, nullable=False)
    win_rate_pct = Column(Numeric(6, 2), nullable=False)
    result_json = Column(JSON, nullable=False)
    executed_at = Column(DateTime, nullable=False)

    user = relationship("User", back_populates="backtest_results")

class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(UUID, primary_key=True)
    user_id = Column(UUID, ForeignKey("users.id"), unique=True)
    max_positions = Column(Integer, nullable=False, default=15)
    max_position_pct = Column(Numeric(5, 2), nullable=False, default=10.00)
    stop_loss_pct = Column(Numeric(5, 2), nullable=False, default=5.00)
    confidence_threshold = Column(Integer, nullable=False, default=60)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    user = relationship("User", back_populates="settings")
```

---

## Data Migration from trading_wizard_bundle

기존 `portfolio_state.json` 형식과의 호환성:

```python
# JSON → SQLite 마이그레이션
def migrate_portfolio_state(json_path: str, user_id: UUID):
    with open(json_path) as f:
        data = json.load(f)

    # Portfolio 생성
    portfolio = Portfolio(
        user_id=user_id,
        initial_capital=data["initial_capital"],
        cash_balance=data["cash_balance"],
    )

    # Positions 마이그레이션
    for pos in data.get("positions", []):
        Position(
            portfolio_id=portfolio.id,
            stock_code=pos["stock_code"],
            stock_name=get_stock_name(pos["stock_code"]),
            quantity=pos["quantity"],
            avg_entry_price=pos["entry_price"],
            first_entry_date=pos["entry_date"],
            entry_reason=pos.get("entry_reason"),  # From trading_wizard_bundle
            confidence_score=pos.get("confidence_score"),  # From trading_wizard_bundle
        )

    # Trades 마이그레이션
    for trade in data.get("trade_history", []):
        Trade(
            portfolio_id=portfolio.id,
            trade_date=trade["date"],
            stock_code=trade["stock_code"],
            action=trade["action"],
            quantity=trade["quantity"],
            price=trade["price"],
            realized_pnl=trade.get("realized_pnl"),
            reason=trade.get("reason"),
        )
```
