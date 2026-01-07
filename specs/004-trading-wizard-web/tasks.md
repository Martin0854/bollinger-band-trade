# Tasks: Trading Wizard Web

**Input**: Design documents from `/specs/004-trading-wizard-web/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/openapi.yaml ✅

**Tests**: Tests are OPTIONAL - only included if explicitly requested.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `trading_wizard_web/backend/src/`, `trading_wizard_web/frontend/src/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create project directory structure per plan.md (`trading_wizard_web/backend/`, `trading_wizard_web/frontend/`, `trading_wizard_web/k8s/`, `trading_wizard_web/data/`)
- [x] T002 [P] Initialize Python backend with FastAPI dependencies in `trading_wizard_web/backend/requirements.txt`
- [x] T003 [P] Initialize React frontend with Vite and TailwindCSS in `trading_wizard_web/frontend/package.json`
- [x] T004 [P] Configure linting and formatting (ruff for Python, eslint for TypeScript) in respective config files
- [x] T005 Copy `data/stock_names_kr.json` from `trading_wizard_bundle` to `trading_wizard_web/data/`
- [x] T006 [P] Create backend Dockerfile in `trading_wizard_web/backend/Dockerfile`
- [x] T007 [P] Create frontend Dockerfile and nginx.conf in `trading_wizard_web/frontend/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T008 Create SQLAlchemy base configuration and database setup in `trading_wizard_web/backend/src/db/database.py`
- [x] T009 Create base SQLAlchemy model with UUID and timestamp mixins in `trading_wizard_web/backend/src/models/base.py`
- [x] T010 Setup Alembic for database migrations in `trading_wizard_web/backend/alembic/`
- [x] T011 Create environment configuration management in `trading_wizard_web/backend/src/core/config.py`
- [x] T012 [P] Create error handling and exception classes in `trading_wizard_web/backend/src/core/exceptions.py`
- [x] T013 [P] Setup logging infrastructure in `trading_wizard_web/backend/src/core/logging.py`
- [x] T014 Create FastAPI app entry point with CORS, middleware in `trading_wizard_web/backend/src/main.py`
- [x] T015 Create API router structure in `trading_wizard_web/backend/src/api/__init__.py`
- [x] T016 Create health check endpoint in `trading_wizard_web/backend/src/api/health.py`
- [x] T017 [P] Create frontend API client base in `trading_wizard_web/frontend/src/services/api.ts`
- [x] T018 [P] Create frontend type definitions in `trading_wizard_web/frontend/src/types/index.ts`
- [x] T019 Create React app entry point and router in `trading_wizard_web/frontend/src/main.tsx` and `App.tsx`
- [x] T020 [P] Create common UI components (Button, Input, Card, Table) in `trading_wizard_web/frontend/src/components/common/`

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - PEM 키 기반 인증 (Priority: P1) 🎯 MVP

**Goal**: 개인 투자자가 PEM 개인키 파일로 인증하여 개인정보 없이 계정 식별

**Independent Test**: 키 생성 → PEM 파일로 로그인 → 대시보드 접근까지 완료 확인

### Backend Models for User Story 1

- [x] T021 [P] [US1] Create User model with ECDSA public key storage in `trading_wizard_web/backend/src/models/user.py`
- [x] T022 [P] [US1] Create UserSettings model in `trading_wizard_web/backend/src/models/user_settings.py`
- [x] T023 [P] [US1] Create Portfolio model (User 1:1) in `trading_wizard_web/backend/src/models/portfolio.py`

### Backend Auth Infrastructure for User Story 1

- [x] T024 [US1] Implement ECDSA P-256 crypto operations (key validation, fingerprint, signature verify) in `trading_wizard_web/backend/src/auth/crypto.py`
- [x] T025 [US1] Implement JWT token creation and validation in `trading_wizard_web/backend/src/auth/jwt.py`
- [x] T026 [US1] Create auth middleware for protected routes in `trading_wizard_web/backend/src/auth/middleware.py`
- [x] T027 [US1] Create challenge store (in-memory with TTL) in `trading_wizard_web/backend/src/auth/challenge_store.py`

### Backend API for User Story 1

- [x] T028 [US1] Implement POST /api/auth/register endpoint in `trading_wizard_web/backend/src/api/auth.py`
- [x] T029 [US1] Implement POST /api/auth/challenge endpoint in `trading_wizard_web/backend/src/api/auth.py`
- [x] T030 [US1] Implement POST /api/auth/verify endpoint in `trading_wizard_web/backend/src/api/auth.py`
- [x] T031 [US1] Implement POST /api/auth/logout endpoint in `trading_wizard_web/backend/src/api/auth.py`
- [x] T032 [US1] Create Alembic migration for User, UserSettings, Portfolio tables

### Frontend Auth for User Story 1

- [x] T033 [P] [US1] Implement Web Crypto API ECDSA P-256 key generation and signing in `trading_wizard_web/frontend/src/services/auth.ts`
- [x] T034 [P] [US1] Implement PEM file export/import utilities in `trading_wizard_web/frontend/src/services/pem.ts`
- [x] T035 [US1] Create auth context and state management in `trading_wizard_web/frontend/src/contexts/AuthContext.tsx`
- [x] T036 [US1] Create LoginPage with key generation, PEM upload, login flow in `trading_wizard_web/frontend/src/pages/LoginPage.tsx`
- [x] T037 [US1] Create protected route wrapper in `trading_wizard_web/frontend/src/components/common/ProtectedRoute.tsx`
- [x] T038 [US1] Create basic DashboardPage placeholder (로그인 후 리다이렉트 대상) in `trading_wizard_web/frontend/src/pages/DashboardPage.tsx`

**Checkpoint**: User Story 1 complete - 키 생성, PEM 다운로드, 로그인, 로그아웃 기능 동작 확인

---

## Phase 4: User Story 2 - 거래 데이터 입력 (Priority: P1)

**Goal**: 투자자가 매수/매도 거래를 입력하고 포트폴리오에 반영

**Independent Test**: 거래 입력 후 포트폴리오에 해당 종목이 반영되는지 확인

### Backend Models for User Story 2

- [x] T039 [P] [US2] Create Position model with entry_reason (VARCHAR(50)), confidence_score (INTEGER) fields in `trading_wizard_web/backend/src/models/position.py`
- [x] T040 [P] [US2] Create Trade model with TradeAction enum in `trading_wizard_web/backend/src/models/trade.py`

### Backend Services for User Story 2

- [x] T041 [US2] Create stock name lookup service using stock_names_kr.json in `trading_wizard_web/backend/src/services/stock_service.py`
- [x] T042 [US2] Implement trade processing service (BUY/SELL logic, position update, cash balance) in `trading_wizard_web/backend/src/services/trade_service.py`
- [x] T043 [US2] Implement portfolio service (get summary, update initial capital) in `trading_wizard_web/backend/src/services/portfolio_service.py`

### Backend API for User Story 2

- [x] T044 [US2] Implement POST /api/trades endpoint with validation in `trading_wizard_web/backend/src/api/trades.py`
- [x] T045 [US2] Implement GET /api/stocks/search endpoint in `trading_wizard_web/backend/src/api/stocks.py`
- [x] T046 [US2] Implement GET /api/stocks/{code} endpoint in `trading_wizard_web/backend/src/api/stocks.py`
- [x] T047 [US2] Create Alembic migration for Position, Trade tables

### Frontend for User Story 2

- [x] T048 [P] [US2] Create trade input form component in `trading_wizard_web/frontend/src/components/trade/TradeInputForm.tsx`
- [x] T049 [P] [US2] Create stock search autocomplete component in `trading_wizard_web/frontend/src/components/trade/StockSearchInput.tsx`
- [x] T050 [US2] Create TradePage with trade input form in `trading_wizard_web/frontend/src/pages/TradePage.tsx`
- [x] T051 [US2] Add trade API calls to frontend API client in `trading_wizard_web/frontend/src/services/api.ts`

**Checkpoint**: User Story 2 complete - 매수/매도 거래 입력 및 포트폴리오 반영 확인

---

## Phase 5: User Story 3 - 포트폴리오 대시보드 시각화 (Priority: P2)

**Goal**: 현재 보유 종목, 평가손익, 총 자산을 한 화면에서 확인

**Independent Test**: 보유 종목과 손익 정보가 대시보드에 올바르게 표시되는지 확인

### Backend for User Story 3

- [x] T052 [US3] Implement yfinance price fetching service in `trading_wizard_web/backend/src/services/price_service.py`
- [x] T053 [US3] Extend portfolio service to include positions value, unrealized PnL in `trading_wizard_web/backend/src/services/portfolio_service.py`
- [x] T054 [US3] Implement GET /api/portfolio endpoint (summary with current values) in `trading_wizard_web/backend/src/api/portfolio.py`
- [x] T055 [US3] Implement GET /api/positions endpoint (with current prices) in `trading_wizard_web/backend/src/api/positions.py`

### Frontend for User Story 3

- [x] T056 [P] [US3] Create portfolio summary card component in `trading_wizard_web/frontend/src/components/dashboard/PortfolioSummaryCard.tsx`
- [x] T057 [P] [US3] Create positions table component in `trading_wizard_web/frontend/src/components/dashboard/PositionsTable.tsx`
- [x] T058 [P] [US3] Create PnL summary component in `trading_wizard_web/frontend/src/components/dashboard/PnLSummary.tsx`
- [x] T059 [US3] Integrate dashboard components in `trading_wizard_web/frontend/src/pages/DashboardPage.tsx`
- [x] T060 [US3] Add portfolio and positions API calls to frontend API client in `trading_wizard_web/frontend/src/services/api.ts`

**Checkpoint**: User Story 3 complete - 대시보드에 포트폴리오 요약, 보유종목, 손익현황 표시 확인

---

## Phase 6: User Story 4 - 거래 이력 관리 (Priority: P2)

**Goal**: 과거 거래 내역 조회, 필터링, 삭제 기능

**Independent Test**: 거래 이력 페이지에서 과거 입력한 모든 거래가 표시되는지 확인

### Backend for User Story 4

- [x] T061 [US4] Implement trade rollback logic (delete trade, reverse position/cash) in `trading_wizard_web/backend/src/services/trade_service.py`
- [x] T062 [US4] Implement GET /api/trades endpoint with filters (stock_code, action, date range, pagination) in `trading_wizard_web/backend/src/api/trades.py`
- [x] T063 [US4] Implement DELETE /api/trades/{id} endpoint in `trading_wizard_web/backend/src/api/trades.py`
- [x] T064 [US4] Implement GET /api/trades/export CSV endpoint in `trading_wizard_web/backend/src/api/trades.py`

### Frontend for User Story 4

- [x] T065 [P] [US4] Create trade history table component with pagination in `trading_wizard_web/frontend/src/components/trade/TradeHistoryTable.tsx`
- [x] T066 [P] [US4] Create trade filter component (date range, stock, action) in `trading_wizard_web/frontend/src/components/trade/TradeFilter.tsx`
- [x] T067 [US4] Create HistoryPage with filters and table in `trading_wizard_web/frontend/src/pages/HistoryPage.tsx`
- [x] T068 [US4] Add trade history API calls and CSV export to frontend in `trading_wizard_web/frontend/src/services/api.ts`

**Checkpoint**: User Story 4 complete - 거래 이력 조회, 필터링, 삭제, CSV 내보내기 확인

---

## Phase 7: User Story 5 - 백테스트 실행 및 결과 조회 (Priority: P3)

**Goal**: 볼린저 밴드 스퀴즈 전략 백테스트 실행 및 결과 확인

**Independent Test**: 백테스트 파라미터 입력 후 결과가 생성되고 조회 가능한지 확인

### Backend Core Logic for User Story 5

- [x] T069 [US5] Copy and adapt signal_scanner.py from trading_wizard_bundle to `trading_wizard_web/backend/src/core/signal_scanner.py`
- [x] T070 [US5] Copy and adapt recommendation.py from trading_wizard_bundle to `trading_wizard_web/backend/src/core/recommendation.py`
- [x] T071 [US5] Extract indicator calculations to `trading_wizard_web/backend/src/core/indicators.py`

### Backend Models and Services for User Story 5

- [x] T072 [US5] Create BacktestResult model in `trading_wizard_web/backend/src/models/backtest.py`
- [x] T073 [US5] Implement backtest service (run, analyze, save results) in `trading_wizard_web/backend/src/services/backtest_service.py` - MUST read max_positions, stop_loss_pct, confidence_threshold, max_position_pct from UserSettings
- [x] T074 [US5] Create Alembic migration for BacktestResult table

### Backend API for User Story 5

- [x] T075 [US5] Implement POST /api/backtest/run endpoint (async execution) in `trading_wizard_web/backend/src/api/backtest.py`
- [x] T076 [US5] Implement GET /api/backtest/results endpoint in `trading_wizard_web/backend/src/api/backtest.py`
- [x] T077 [US5] Implement GET /api/backtest/{id} endpoint in `trading_wizard_web/backend/src/api/backtest.py`

### Frontend for User Story 5

- [x] T078 [P] [US5] Create backtest input form component in `trading_wizard_web/frontend/src/components/backtest/BacktestForm.tsx`
- [x] T079 [P] [US5] Create backtest result summary component in `trading_wizard_web/frontend/src/components/backtest/BacktestResultCard.tsx`
- [x] T080 [P] [US5] Create backtest detail view (monthly returns, trades, chart) in `trading_wizard_web/frontend/src/components/backtest/BacktestDetail.tsx`
- [x] T081 [US5] Create BacktestPage with form and results list in `trading_wizard_web/frontend/src/pages/BacktestPage.tsx`
- [x] T082 [US5] Add backtest API calls to frontend in `trading_wizard_web/frontend/src/services/api.ts`

**Checkpoint**: User Story 5 complete - 백테스트 실행, 진행상태 표시, 결과 조회 확인

---

## Phase 8: User Story 6 - 전략 설정 관리 (Priority: P3)

**Goal**: 투자 전략 파라미터 (최대 포지션 수, 손절선 등) 설정 및 저장

**Independent Test**: 설정 변경 후 저장되고, 다음 로그인 시에도 유지되는지 확인

### Backend for User Story 6

- [x] T083 [US6] Implement settings service in `trading_wizard_web/backend/src/services/settings_service.py`
- [x] T084 [US6] Implement GET /api/settings endpoint in `trading_wizard_web/backend/src/api/settings.py`
- [x] T085 [US6] Implement PUT /api/settings endpoint with validation in `trading_wizard_web/backend/src/api/settings.py` - show Constitution III warning if stop_loss_pct < 5% or max_position_pct > 10%

### Frontend for User Story 6

- [x] T086 [P] [US6] Create settings form component in `trading_wizard_web/frontend/src/components/settings/SettingsForm.tsx` - display Constitution III warning when stop_loss_pct < 5% or max_position_pct > 10%
- [x] T087 [US6] Create SettingsPage in `trading_wizard_web/frontend/src/pages/SettingsPage.tsx`
- [x] T088 [US6] Add settings API calls to frontend in `trading_wizard_web/frontend/src/services/api.ts`

**Checkpoint**: User Story 6 complete - 설정 조회, 변경, 저장, 유지 확인

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T089 [P] Add navigation component with logout button in `trading_wizard_web/frontend/src/components/common/Navigation.tsx`
- [x] T090 [P] Implement session timeout (30분 미활동 시 자동 로그아웃) in `trading_wizard_web/frontend/src/contexts/AuthContext.tsx`
- [x] T091 [P] Add loading states and error handling to all pages
- [x] T092 [P] Create responsive mobile layout for dashboard and trade pages
- [x] T093 Create Kubernetes manifests in `trading_wizard_web/k8s/` (namespace, configmap, secret, pvc, backend, frontend)
- [x] T094 Create Istio Gateway and VirtualService in `trading_wizard_web/k8s/` (istio-gateway.yaml, istio-virtualservice.yaml, istio-destinationrule.yaml)
- [x] T095 Run quickstart.md validation - verify development environment setup
- [x] T096 Create docker-compose.yml for local development

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-8)**: All depend on Foundational phase completion
  - US1 (Auth) and US2 (Trade) are both P1 - can be done in parallel or US1 first
  - US3 (Dashboard) and US4 (History) are P2 - depend on US2 for data
  - US5 (Backtest) and US6 (Settings) are P3 - can start after Foundational
- **Polish (Phase 9)**: Depends on core user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational - Needs US1 auth for protected endpoints
- **User Story 3 (P2)**: Depends on US1 (auth) and US2 (positions/trades exist)
- **User Story 4 (P2)**: Depends on US1 (auth) and US2 (trades exist)
- **User Story 5 (P3)**: Depends on US1 (auth) only - Core logic is independent
- **User Story 6 (P3)**: Depends on US1 (auth) only - Settings model created in US1

### Within Each User Story

- Models before services
- Services before API endpoints
- Backend before frontend (for API dependencies)
- Core implementation before integration

### Parallel Opportunities

**Phase 1 (Setup)**:
```bash
Task: T002 (backend init) | T003 (frontend init) | T004 (linting) | T006 (backend Dockerfile) | T007 (frontend Dockerfile)
```

**Phase 2 (Foundational)**:
```bash
Task: T012 (exceptions) | T013 (logging) | T017 (frontend api) | T018 (frontend types) | T020 (common components)
```

**Phase 3 (User Story 1)**:
```bash
# Models in parallel:
Task: T021 (User) | T022 (UserSettings) | T023 (Portfolio)
# Frontend in parallel:
Task: T033 (Web Crypto) | T034 (PEM utils)
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (Authentication)
4. Complete Phase 4: User Story 2 (Trade Input)
5. **STOP and VALIDATE**: Test login + trade input flow
6. Deploy/demo if ready (users can register, login, input trades)

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Auth works
3. Add User Story 2 → Test independently → Trade input works (MVP!)
4. Add User Story 3 → Dashboard visualizes portfolio
5. Add User Story 4 → Trade history management
6. Add User Story 5 → Backtest functionality
7. Add User Story 6 → Settings management
8. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (Auth) → User Story 5 (Backtest)
   - Developer B: User Story 2 (Trade) → User Story 3 (Dashboard) → User Story 4 (History)
   - Developer C: User Story 6 (Settings) → Polish tasks
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies within the phase
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- trading_wizard_bundle core logic reuse: ~70% (signal_scanner, recommendation)
