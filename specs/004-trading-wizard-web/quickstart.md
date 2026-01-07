# Quick Start Guide: Trading Wizard Web

**Feature**: 004-trading-wizard-web
**Date**: 2026-01-05

## Prerequisites

- Python 3.11+
- Node.js 18+
- Git

## 1. Project Setup

```bash
# Clone and navigate
cd trading_wizard_web

# Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Frontend setup
cd ../frontend
npm install
```

## 2. Database Initialization

```bash
cd backend

# Create database schema
alembic upgrade head

# Copy stock names data
cp ../trading_wizard_bundle/data/stock_names_kr.json ../data/
```

## 3. Running Development Servers

### Backend (FastAPI)

```bash
cd backend
source venv/bin/activate
uvicorn src.main:app --reload --port 8000

# API available at http://localhost:8000
# OpenAPI docs at http://localhost:8000/docs
```

### Frontend (Vite)

```bash
cd frontend
npm run dev

# App available at http://localhost:5173
```

## 4. First-time User Flow

### 4.1 Generate Key Pair

브라우저에서 로그인 페이지 접속 → "새 키 생성" 클릭:

```javascript
// Frontend에서 Web Crypto API 사용
const keyPair = await crypto.subtle.generateKey(
  { name: 'ECDSA', namedCurve: 'P-256' },
  true,
  ['sign', 'verify']
);

// PEM 형식으로 내보내기
const privateKey = await crypto.subtle.exportKey('pkcs8', keyPair.privateKey);
const publicKey = await crypto.subtle.exportKey('spki', keyPair.publicKey);
```

### 4.2 Register

```bash
# POST /api/auth/register
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "public_key": "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----",
    "nickname": "MyWizard"
  }'
```

### 4.3 Login Flow

```bash
# 1. Request challenge
curl -X POST http://localhost:8000/api/auth/challenge \
  -H "Content-Type: application/json" \
  -d '{"fingerprint": "abc123..."}'

# 2. Sign challenge with private key (browser)
# 3. Verify signature
curl -X POST http://localhost:8000/api/auth/verify \
  -H "Content-Type: application/json" \
  -d '{
    "fingerprint": "abc123...",
    "challenge": "base64...",
    "signature": "base64..."
  }'
# Returns: { "access_token": "jwt...", "token_type": "bearer" }
```

## 5. Basic API Usage

### Portfolio

```bash
# Get portfolio summary
curl http://localhost:8000/api/portfolio \
  -H "Authorization: Bearer <token>"

# Set initial capital
curl -X PUT http://localhost:8000/api/portfolio \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"initial_capital": 1000000}'
```

### Trade Input

```bash
# Buy trade
curl -X POST http://localhost:8000/api/trades \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "trade_date": "2026-01-05",
    "stock_code": "005930",
    "action": "BUY",
    "quantity": 10,
    "price": 71200
  }'

# Sell trade
curl -X POST http://localhost:8000/api/trades \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "trade_date": "2026-01-10",
    "stock_code": "005930",
    "action": "SELL",
    "quantity": 5,
    "price": 73000,
    "reason": "profit_taking"
  }'
```

### Backtest

```bash
# Run backtest
curl -X POST http://localhost:8000/api/backtest/run \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2025-01-02",
    "end_date": "2025-12-31",
    "stock_list": "kospi_top100_2025jan",
    "initial_capital": 1000000,
    "name": "2025년 백테스트"
  }'

# Get results
curl http://localhost:8000/api/backtest/results \
  -H "Authorization: Bearer <token>"
```

## 6. Environment Variables

### Backend (.env)

```bash
# Database
DATABASE_URL=sqlite:///./data/trading_wizard.db

# JWT
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30

# CORS
CORS_ORIGINS=http://localhost:5173
```

### Frontend (.env)

```bash
VITE_API_URL=http://localhost:8000/api
```

## 7. Testing

### Backend

```bash
cd backend
pytest tests/ -v

# With coverage
pytest tests/ --cov=src --cov-report=html
```

### Frontend

```bash
cd frontend
npm run test

# E2E tests
npm run test:e2e
```

## 8. Production Build

### Backend

```bash
cd backend
pip install gunicorn
gunicorn src.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Frontend

```bash
cd frontend
npm run build
# Static files in dist/
```

### Docker Compose

```bash
docker-compose up -d

# Services:
# - backend: http://localhost:8000
# - frontend: http://localhost:3000
```

## 9. Migrating from trading_wizard_bundle

기존 `portfolio_state.json`을 웹 앱으로 이전:

```bash
cd backend
python scripts/migrate_portfolio.py \
  --input ../trading_wizard_bundle/portfolio_state.json \
  --fingerprint <your-fingerprint>
```

## Common Issues

### CORS Error

Frontend와 Backend 포트가 다를 때 발생. Backend `.env`에서 CORS_ORIGINS 확인.

### PEM File Invalid

- ECDSA P-256 형식인지 확인
- PEM 헤더/푸터 포함 여부 확인
- 줄바꿈 문자 (\\n vs 실제 개행) 확인

### yfinance Rate Limit

Yahoo Finance API 요청 과다 시 발생. 요청 간 100ms 간격 유지 권장.

---

## Next Steps

1. [data-model.md](./data-model.md) - 데이터 모델 상세
2. [contracts/openapi.yaml](./contracts/openapi.yaml) - API 스펙
3. [research.md](./research.md) - 기술 결정 근거
