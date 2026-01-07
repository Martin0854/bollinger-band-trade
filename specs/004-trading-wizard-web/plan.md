# Implementation Plan: Trading Wizard Web

**Branch**: `004-trading-wizard-web` | **Date**: 2026-01-05 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-trading-wizard-web/spec.md`

## Summary

사용자 계정별 거래 데이터 입력, 이력 관리, 백테스트, 시각화 기능을 제공하는 웹 애플리케이션 구축. PEM 키 기반 인증(ECDSA P-256)으로 개인정보 없이 사용자를 식별하며, 기존 `trading_wizard_bundle/`의 볼린저 밴드 스퀴즈 전략 로직을 코어 엔진으로 재사용한다.

## Technical Context

**Language/Version**: Python 3.11+ (Backend), TypeScript 5.x (Frontend)
**Primary Dependencies**:
- Backend: FastAPI, SQLAlchemy, cryptography, yfinance, pandas, numpy
- Frontend: React 18, Vite, TailwindCSS, Web Crypto API
**Storage**: SQLite (file-based, 단일 파일 배포)
**Testing**: pytest (backend), Vitest (frontend)
**Target Platform**: Linux/macOS server, Modern browsers (Chrome, Firefox, Safari, Edge)
**Project Type**: Web application (frontend + backend)
**Performance Goals**: 대시보드 로딩 <3초, 거래이력 조회 <2초, 백테스트 <3분
**Constraints**: 동시접속 100명, 15분 지연 시세 데이터 (Yahoo Finance)
**Scale/Scope**: 개인 투자자 대상, Kubernetes 단일 Pod 배포
**Deployment**: Kubernetes + Istio (Gateway/VirtualService), Docker 컨테이너

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Verification |
|-----------|--------|--------------|
| I. Data-Driven Strategy | ✅ PASS | 백테스트 기능으로 전략 검증 가능, 기존 3개년 백테스트 로직 재사용 |
| II. Simplicity Over Complexity | ✅ PASS | Phase 3 (MACD + Confidence) 기본 전략 유지, SQLite 단일 파일 배포 |
| III. Risk Management First | ✅ PASS | 손절선 -5% 필수, 최대 포지션 15개, 종목당 10% 비중 제한 강제 |
| IV. Reproducibility | ✅ PASS | SQLite에 모든 거래 이력 저장, 백테스트 결과 JSON 저장 |
| V. User Transparency | ✅ PASS | 신뢰도 점수 및 산출 근거 표시, 대시보드 시각화 제공 |

**Technical Standards Compliance:**
- 종목코드: 6자리 숫자 형식 유지 (기존 코드 재사용)
- 가격 데이터: KRW 단위, 소수점 반올림
- 날짜 형식: YYYY-MM-DD (ISO 8601)

## Project Structure

### Documentation (this feature)

```text
specs/004-trading-wizard-web/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (OpenAPI spec)
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
trading_wizard_web/
├── backend/
│   ├── src/
│   │   ├── main.py              # FastAPI app entry
│   │   ├── auth/                # PEM authentication
│   │   │   ├── crypto.py        # ECDSA P-256 operations
│   │   │   └── middleware.py    # Auth middleware
│   │   ├── models/              # SQLAlchemy models
│   │   │   ├── user.py
│   │   │   ├── portfolio.py
│   │   │   ├── trade.py
│   │   │   └── backtest.py
│   │   ├── api/                 # API routes
│   │   │   ├── auth.py
│   │   │   ├── portfolio.py
│   │   │   ├── trades.py
│   │   │   ├── backtest.py
│   │   │   └── settings.py
│   │   ├── services/            # Business logic
│   │   │   ├── portfolio_service.py
│   │   │   ├── trade_service.py
│   │   │   └── backtest_service.py
│   │   └── core/                # Core trading logic (from trading_wizard_bundle)
│   │       ├── signal_scanner.py    # Copy from bundle
│   │       ├── recommendation.py    # Copy from bundle
│   │       └── indicators.py        # Extracted indicator calculations
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── contract/
│   ├── requirements.txt
│   └── alembic/                 # DB migrations
│
├── frontend/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── common/          # Shared UI components
│   │   │   ├── dashboard/       # Dashboard widgets
│   │   │   ├── trade/           # Trade input forms
│   │   │   ├── backtest/        # Backtest UI
│   │   │   └── settings/        # Settings forms
│   │   ├── pages/
│   │   │   ├── LoginPage.tsx
│   │   │   ├── DashboardPage.tsx
│   │   │   ├── TradePage.tsx
│   │   │   ├── HistoryPage.tsx
│   │   │   ├── BacktestPage.tsx
│   │   │   └── SettingsPage.tsx
│   │   ├── services/
│   │   │   ├── api.ts           # API client
│   │   │   └── auth.ts          # Web Crypto operations
│   │   ├── hooks/
│   │   └── types/
│   ├── tests/
│   ├── index.html
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── package.json
│
├── data/
│   ├── trading_wizard.db       # SQLite database
│   └── stock_names_kr.json     # Korean stock name mapping (from bundle)
│
├── k8s/                        # Kubernetes manifests
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secret.yaml
│   ├── pvc.yaml
│   ├── backend.yaml
│   ├── frontend.yaml
│   ├── istio-gateway.yaml
│   ├── istio-virtualservice.yaml
│   ├── istio-destinationrule.yaml
│   └── certificate.yaml
│
└── mockup/                     # Existing mockups (reference)
    ├── common.css
    ├── dashboard.html
    ├── backtest.html
    ├── trade.html
    └── settings.html
```

**Structure Decision**: Web application (Option 2) 선택. Frontend(React/Vite)와 Backend(FastAPI)를 분리하여 관심사 분리 및 독립 배포 가능. `trading_wizard_bundle/src/wizard/` 핵심 로직을 `backend/src/core/`로 복사하여 재사용.

## Core Logic Reuse Strategy

**trading_wizard_bundle → trading_wizard_web 매핑:**

| Bundle Module | Web Backend Target | Reuse Strategy |
|--------------|-------------------|----------------|
| `src/wizard/portfolio_manager.py` | `models/`, `services/portfolio_service.py` | 데이터클래스 → SQLAlchemy 모델 변환 |
| `src/wizard/signal_scanner.py` | `core/signal_scanner.py` | 거의 그대로 복사, yfinance 의존성 유지 |
| `src/wizard/recommendation.py` | `core/recommendation.py` | 거의 그대로 복사 |
| `backtest_wizard.py` | `services/backtest_service.py` | 로직 추출하여 서비스로 래핑 |
| `data/stock_names_kr.json` | `data/stock_names_kr.json` | 그대로 복사 |

**기존 코드 재사용 비율:** ~70% (핵심 전략 로직 전량 재사용)

## Complexity Tracking

> **No violations - complexity justified**

N/A - Constitution Check 모두 통과

---

## Post-Design Constitution Re-Check

*Re-evaluated after Phase 1 design completion*

| Principle | Status | Post-Design Verification |
|-----------|--------|--------------------------|
| I. Data-Driven Strategy | ✅ PASS | backtest_service.py가 기존 backtest_wizard.py 로직 재사용, 3개년+ 검증 유지 |
| II. Simplicity Over Complexity | ✅ PASS | 단일 SQLite 파일, trading_wizard_bundle 70% 코드 재사용, 불필요한 추상화 없음 |
| III. Risk Management First | ✅ PASS | UserSettings 모델에 max_positions(15), stop_loss_pct(5%), max_position_pct(10%) 기본값 강제 |
| IV. Reproducibility | ✅ PASS | Trade 엔티티에 모든 거래 기록, BacktestResult에 JSON 상세 결과 저장 |
| V. User Transparency | ✅ PASS | PortfolioSummary API에 신뢰도 점수, 산출 근거 포함, 대시보드 시각화 제공 |

**Technical Standards Post-Design:**
- 종목코드: `^[0-9]{6}$` 정규식 검증 (data-model.md Position, Trade)
- 가격 데이터: DECIMAL(12,2) KRW 단위 (data-model.md)
- 날짜 형식: DATE/DATETIME ISO 8601 (openapi.yaml)

---

## Generated Artifacts

| Phase | Artifact | Path | Description |
|-------|----------|------|-------------|
| 0 | research.md | `specs/004-trading-wizard-web/research.md` | 기술 결정 및 근거 |
| 1 | data-model.md | `specs/004-trading-wizard-web/data-model.md` | 엔티티 정의, SQLAlchemy 모델 |
| 1 | openapi.yaml | `specs/004-trading-wizard-web/contracts/openapi.yaml` | REST API 계약 |
| 1 | quickstart.md | `specs/004-trading-wizard-web/quickstart.md` | 개발 환경 설정 가이드 |

---

## Next Steps

1. **`/speckit.tasks`** 실행하여 구현 태스크 생성
2. P1 User Stories 우선 구현:
   - PEM 키 기반 인증 (User Story 1)
   - 거래 데이터 입력 (User Story 2)
3. trading_wizard_bundle 핵심 로직 복사 및 적응
