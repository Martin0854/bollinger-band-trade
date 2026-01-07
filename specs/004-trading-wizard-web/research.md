# Research: Trading Wizard Web

**Feature**: 004-trading-wizard-web
**Date**: 2026-01-05
**Status**: Complete

## 1. Core Logic Reuse Analysis

### 1.1 trading_wizard_bundle 아키텍처 분석

**Decision**: `trading_wizard_bundle/src/wizard/` 모듈을 핵심 엔진으로 재사용

**Rationale**:
- 3개년(2023-2025) 백테스트 검증 완료 (+90.21% 누적 수익률)
- 볼린저 밴드 스퀴즈 전략 로직이 성숙함
- yfinance 기반 데이터 수집 코드 안정적
- Constitution 원칙 준수 (손절 -5%, 최대 15 포지션, 신뢰도 점수 등)

**Alternatives Considered**:
| Alternative | Rejected Because |
|-------------|------------------|
| 전략 로직 새로 작성 | 검증된 로직 재사용이 리스크 낮음, Constitution I 위반 가능 |
| trading_wizard_bundle 직접 import | CLI 의존성, JSON 파일 기반으로 웹 아키텍처와 맞지 않음 |
| 외부 라이브러리 (backtrader 등) | 학습 비용, 기존 전략 이식 필요, 불필요한 복잡도 |

### 1.2 재사용 대상 코드 상세

```text
trading_wizard_bundle/
├── src/wizard/
│   ├── portfolio_manager.py    # 297 lines - 재사용 (모델 변환 필요)
│   │   ├── WizardPosition       → Position 모델
│   │   ├── TradeRecord          → Trade 모델
│   │   ├── PendingOrder         → (웹에서 별도 처리)
│   │   └── WizardPortfolioState → Portfolio 모델
│   │
│   ├── signal_scanner.py       # 406 lines - 거의 그대로 복사
│   │   ├── fetch_stock_data()   → core/signal_scanner.py
│   │   ├── calculate_indicators() → core/indicators.py
│   │   ├── calculate_confidence_score() → core/signal_scanner.py
│   │   └── SignalScanner class  → core/signal_scanner.py
│   │
│   └── recommendation.py       # 323 lines - 거의 그대로 복사
│       ├── BuyRecommendation    → types/recommendation.py
│       ├── SellRecommendation   → types/recommendation.py
│       └── RecommendationEngine → services/recommendation_service.py
│
├── backtest_wizard.py          # 662 lines - 로직 추출
│   ├── run_backtest()           → services/backtest_service.py
│   ├── analyze_performance()    → services/backtest_service.py
│   └── save_to_json()           → (DB 저장으로 대체)
│
└── data/
    └── stock_names_kr.json     # 그대로 복사
```

## 2. Authentication Strategy

### 2.1 PEM 키 기반 인증 (ECDSA P-256)

**Decision**: 브라우저 Web Crypto API로 키 생성, 서버는 공개키만 저장

**Rationale**:
- 개인정보 미수집 요구사항 충족 (이메일/비밀번호 불필요)
- ECDSA P-256은 브라우저 Web Crypto API에서 기본 지원
- 키 크기가 작아 (256bit) PEM 파일 용량 최소화
- TLS 인증서에도 널리 사용되어 검증된 알고리즘

**Alternatives Considered**:
| Alternative | Rejected Because |
|-------------|------------------|
| RSA 2048/4096 | 키 크기 큼 (2048-4096bit), 서명/검증 느림 |
| Ed25519 | Web Crypto API 미지원 (Safari 등) |
| Passkey/WebAuthn | 하드웨어 의존성, 복잡도 높음 |
| Traditional JWT + Password | 개인정보 수집 필요, spec 위반 |

### 2.2 인증 플로우

```
[신규 사용자]
1. 브라우저에서 ECDSA P-256 키쌍 생성 (Web Crypto API)
2. 공개키를 서버로 전송 → 핑거프린트 계산 → User 생성
3. 개인키를 PEM 형식으로 다운로드 (사용자 보관)

[로그인]
1. PEM 파일 업로드 → 브라우저에서 개인키 파싱
2. 서버가 challenge (nonce) 전송
3. 브라우저가 개인키로 challenge 서명
4. 서버가 공개키로 서명 검증 → JWT 세션 토큰 발급

[세션 유지]
- JWT 토큰 30분 만료 (FR-003)
- 활동 시 자동 갱신
```

## 3. Data Storage Strategy

### 3.1 SQLite 선택

**Decision**: SQLite (단일 파일 데이터베이스)

**Rationale**:
- 배포 간단 (DB 서버 불필요, 파일 복사로 백업)
- 동시접속 100명 규모 충분 (WAL 모드)
- Python 표준 라이브러리 지원
- 개인 투자자 대상 소규모 서비스에 적합

**Alternatives Considered**:
| Alternative | Rejected Because |
|-------------|------------------|
| PostgreSQL | 별도 서버 필요, 배포 복잡도 증가 |
| MySQL/MariaDB | 같은 이유 |
| JSON 파일 (기존 방식) | 동시성 문제, 쿼리 불가, 데이터 무결성 약함 |
| MongoDB | 관계형 데이터에 부적합, 오버스펙 |

### 3.2 SQLite 최적화 설정

```python
# WAL 모드 (동시 읽기 지원)
PRAGMA journal_mode = WAL;

# 외래키 강제
PRAGMA foreign_keys = ON;

# 캐시 크기 (10MB)
PRAGMA cache_size = -10000;
```

## 4. Frontend Framework Selection

### 4.1 React + Vite + TailwindCSS

**Decision**: React 18 + Vite 5 + TailwindCSS 3

**Rationale**:
- React: 컴포넌트 기반, 풍부한 생태계
- Vite: 빠른 HMR, 번들 최적화, TypeScript 기본 지원
- TailwindCSS: 유틸리티 퍼스트, mockup CSS와 유사한 스타일링

**Alternatives Considered**:
| Alternative | Rejected Because |
|-------------|------------------|
| Next.js | SSR 불필요, 과도한 복잡도 |
| Vue.js | 팀 경험 기준 React 선호 |
| Svelte | 생태계 작음, 학습 곡선 |
| Plain HTML/CSS | SPA 기능 구현 어려움, 상태관리 복잡 |

## 5. Backend Framework Selection

### 5.1 FastAPI

**Decision**: FastAPI + SQLAlchemy + Alembic

**Rationale**:
- FastAPI: 비동기 지원, 자동 OpenAPI 문서, 타입 힌트 기반
- trading_wizard_bundle이 Python이므로 언어 일관성
- SQLAlchemy: 성숙한 ORM, SQLite 완벽 지원
- Alembic: 스키마 마이그레이션 관리

**Alternatives Considered**:
| Alternative | Rejected Because |
|-------------|------------------|
| Django | 불필요한 기능 많음, 오버스펙 |
| Flask | 비동기 지원 약함, 타입 힌트 미흡 |
| Node.js/Express | Python 코어 로직 재작성 필요 |
| Go/Rust | 학습 곡선, Python 로직 이식 비용 |

## 6. API Design Patterns

### 6.1 RESTful API

**Decision**: RESTful API + JWT Bearer Token

**Endpoints 요약**:
```
POST   /api/auth/register     # 공개키 등록
POST   /api/auth/challenge    # 로그인 challenge 요청
POST   /api/auth/verify       # 서명 검증 & 토큰 발급
POST   /api/auth/logout       # 로그아웃

GET    /api/portfolio         # 포트폴리오 조회
PUT    /api/portfolio         # 초기자본 설정

GET    /api/positions         # 보유종목 조회
POST   /api/trades            # 거래 입력
GET    /api/trades            # 거래이력 조회
DELETE /api/trades/:id        # 거래 삭제
GET    /api/trades/export     # CSV 내보내기

POST   /api/backtest/run      # 백테스트 실행
GET    /api/backtest/results  # 결과 목록
GET    /api/backtest/:id      # 결과 상세

GET    /api/settings          # 설정 조회
PUT    /api/settings          # 설정 저장

GET    /api/stocks/search     # 종목 검색
GET    /api/stocks/:code      # 종목 정보 (현재가 포함)
```

## 7. Real-time Data Strategy

### 7.1 Yahoo Finance API (yfinance)

**Decision**: yfinance 라이브러리로 15분 지연 데이터 조회

**Rationale**:
- 기존 trading_wizard_bundle에서 검증된 사용
- 무료, API 키 불필요
- KOSPI/KOSDAQ 종목 지원 (.KS/.KQ suffix)
- 15분 지연은 spec 요구사항 충족 (FR-009)

**Rate Limiting 전략**:
```python
# 요청 속도 제한
- 종목당 최소 100ms 간격
- 대량 조회 시 batch 처리
```

## 8. Security Considerations

### 8.1 보안 요구사항

| Requirement | Implementation |
|-------------|----------------|
| PEM 개인키 보호 | 서버에 저장 안함, 브라우저에서만 사용 |
| 세션 탈취 방지 | JWT HttpOnly cookie, CSRF 토큰 |
| XSS 방지 | React 기본 이스케이프, CSP 헤더 |
| SQL Injection | SQLAlchemy ORM 사용 |
| 브루트포스 방지 | Rate limiting (IP당 10회/분) |

### 8.2 개인정보 최소화

- 수집 데이터: 공개키, 핑거프린트, 닉네임(선택)
- 미수집: 이메일, 비밀번호, 전화번호, IP 주소 (로그 제외)
- 데이터 보관: 사용자 요청 시 삭제 가능

## 9. Deployment Strategy

### 9.1 Kubernetes + Istio 배포

**Decision**: Kubernetes Deployment + Istio Gateway/VirtualService

**Rationale**:
- 기존 Kubernetes 클러스터 활용
- Istio 서비스 메시로 트래픽 관리, mTLS, 관측성 확보
- 무중단 배포 (Rolling Update)
- SQLite는 PersistentVolume으로 데이터 영속성 보장

### 9.2 Dockerfile

**Backend (FastAPI)**

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Frontend (React/Vite)**

```dockerfile
# frontend/Dockerfile
FROM node:18-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

**Frontend nginx.conf**

```nginx
# frontend/nginx.conf
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    # SPA routing
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Health check
    location /health {
        return 200 'ok';
        add_header Content-Type text/plain;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### 9.3 Kubernetes Manifests

**Namespace & ConfigMap**

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: trading-wizard
  labels:
    istio-injection: enabled
---
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: trading-wizard-config
  namespace: trading-wizard
data:
  DATABASE_URL: "sqlite:///data/trading_wizard.db"
  JWT_ALGORITHM: "HS256"
  JWT_EXPIRE_MINUTES: "30"
  CORS_ORIGINS: "https://trading-wizard.example.com"
```

**Secret**

```yaml
# k8s/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: trading-wizard-secret
  namespace: trading-wizard
type: Opaque
stringData:
  JWT_SECRET_KEY: "<generate-secure-key>"
```

**PersistentVolumeClaim (SQLite 데이터)**

```yaml
# k8s/pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: trading-wizard-data
  namespace: trading-wizard
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
  storageClassName: standard  # 클러스터에 맞게 조정
```

**Backend Deployment & Service**

```yaml
# k8s/backend.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: trading-wizard-backend
  namespace: trading-wizard
spec:
  replicas: 1  # SQLite 사용으로 단일 인스턴스
  selector:
    matchLabels:
      app: trading-wizard-backend
  template:
    metadata:
      labels:
        app: trading-wizard-backend
        version: v1
    spec:
      containers:
        - name: backend
          image: trading-wizard-backend:latest
          ports:
            - containerPort: 8000
          envFrom:
            - configMapRef:
                name: trading-wizard-config
            - secretRef:
                name: trading-wizard-secret
          volumeMounts:
            - name: data
              mountPath: /app/data
          resources:
            requests:
              memory: "256Mi"
              cpu: "100m"
            limits:
              memory: "512Mi"
              cpu: "500m"
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 30
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 10
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: trading-wizard-data
---
apiVersion: v1
kind: Service
metadata:
  name: trading-wizard-backend
  namespace: trading-wizard
spec:
  selector:
    app: trading-wizard-backend
  ports:
    - port: 8000
      targetPort: 8000
      name: http
```

**Frontend Deployment & Service**

```yaml
# k8s/frontend.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: trading-wizard-frontend
  namespace: trading-wizard
spec:
  replicas: 2
  selector:
    matchLabels:
      app: trading-wizard-frontend
  template:
    metadata:
      labels:
        app: trading-wizard-frontend
        version: v1
    spec:
      containers:
        - name: frontend
          image: trading-wizard-frontend:latest
          ports:
            - containerPort: 80
          resources:
            requests:
              memory: "64Mi"
              cpu: "50m"
            limits:
              memory: "128Mi"
              cpu: "200m"
          livenessProbe:
            httpGet:
              path: /health
              port: 80
            periodSeconds: 30
          readinessProbe:
            httpGet:
              path: /health
              port: 80
            periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: trading-wizard-frontend
  namespace: trading-wizard
spec:
  selector:
    app: trading-wizard-frontend
  ports:
    - port: 80
      targetPort: 80
      name: http
```

### 9.4 Istio Gateway & VirtualService

**Gateway**

```yaml
# k8s/istio-gateway.yaml
apiVersion: networking.istio.io/v1beta1
kind: Gateway
metadata:
  name: trading-wizard-gateway
  namespace: trading-wizard
spec:
  selector:
    istio: ingressgateway  # Istio default ingress gateway
  servers:
    - port:
        number: 80
        name: http
        protocol: HTTP
      hosts:
        - "trading-wizard.example.com"
      tls:
        httpsRedirect: true
    - port:
        number: 443
        name: https
        protocol: HTTPS
      hosts:
        - "trading-wizard.example.com"
      tls:
        mode: SIMPLE
        credentialName: trading-wizard-tls  # TLS Secret
```

**VirtualService**

```yaml
# k8s/istio-virtualservice.yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: trading-wizard-vs
  namespace: trading-wizard
spec:
  hosts:
    - "trading-wizard.example.com"
  gateways:
    - trading-wizard-gateway
  http:
    # API 라우팅 (Backend)
    - match:
        - uri:
            prefix: /api
      route:
        - destination:
            host: trading-wizard-backend
            port:
              number: 8000
      timeout: 60s
      retries:
        attempts: 3
        perTryTimeout: 20s
        retryOn: connect-failure,refused-stream,unavailable,cancelled,resource-exhausted

    # 백테스트 API (긴 타임아웃)
    - match:
        - uri:
            prefix: /api/backtest/run
      route:
        - destination:
            host: trading-wizard-backend
            port:
              number: 8000
      timeout: 300s  # 5분 (백테스트용)

    # Frontend (기본 라우팅)
    - match:
        - uri:
            prefix: /
      route:
        - destination:
            host: trading-wizard-frontend
            port:
              number: 80
```

**DestinationRule (mTLS & Connection Pool)**

```yaml
# k8s/istio-destinationrule.yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: trading-wizard-backend-dr
  namespace: trading-wizard
spec:
  host: trading-wizard-backend
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        h2UpgradePolicy: UPGRADE
        http1MaxPendingRequests: 100
        http2MaxRequests: 1000
    tls:
      mode: ISTIO_MUTUAL
---
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: trading-wizard-frontend-dr
  namespace: trading-wizard
spec:
  host: trading-wizard-frontend
  trafficPolicy:
    tls:
      mode: ISTIO_MUTUAL
```

### 9.5 TLS Certificate (cert-manager)

```yaml
# k8s/certificate.yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: trading-wizard-tls
  namespace: istio-system  # Gateway가 참조하는 namespace
spec:
  secretName: trading-wizard-tls
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
    - trading-wizard.example.com
```

### 9.6 배포 순서

```bash
# 1. Namespace 생성 (Istio injection 활성화)
kubectl apply -f k8s/namespace.yaml

# 2. ConfigMap & Secret
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml

# 3. PVC (데이터 영속성)
kubectl apply -f k8s/pvc.yaml

# 4. Backend & Frontend Deployment
kubectl apply -f k8s/backend.yaml
kubectl apply -f k8s/frontend.yaml

# 5. TLS Certificate (cert-manager 사용 시)
kubectl apply -f k8s/certificate.yaml

# 6. Istio Gateway & VirtualService
kubectl apply -f k8s/istio-gateway.yaml
kubectl apply -f k8s/istio-virtualservice.yaml
kubectl apply -f k8s/istio-destinationrule.yaml

# 7. 배포 확인
kubectl get pods -n trading-wizard
kubectl get vs,gw -n trading-wizard
```

### 9.7 SQLite 제약사항 및 대안

**제약**: SQLite는 단일 writer만 지원하므로 Backend replica=1 필수

**확장 필요 시 대안**:
| 규모 | 권장 Storage | 변경사항 |
|------|-------------|----------|
| 현재 (100명 이하) | SQLite + PVC | 현재 설계 유지 |
| 중규모 (100-1000명) | PostgreSQL (CloudSQL/RDS) | DATABASE_URL 변경, SQLAlchemy 호환 |
| 대규모 (1000명+) | PostgreSQL + Read Replica | Connection pooling 추가 |

Constitution II (Simplicity) 원칙에 따라 현재 규모에서는 SQLite 유지.

## 10. Testing Strategy

### 10.1 테스트 범위

| Layer | Tool | Coverage Target |
|-------|------|-----------------|
| Backend Unit | pytest | 80%+ (core/, services/) |
| Backend Integration | pytest + TestClient | API endpoints |
| Backend Contract | pytest | OpenAPI schema 검증 |
| Frontend Unit | Vitest | 70%+ (services/, hooks/) |
| Frontend E2E | Playwright | Critical user flows |

### 10.2 Core Logic 테스트

```python
# trading_wizard_bundle에서 이미 검증된 로직
# 웹 버전에서는 입출력 변환 테스트에 집중

def test_signal_scanner_buy_signal():
    """기존 backtest 결과와 동일한 신호 생성 확인"""
    pass

def test_confidence_score_calculation():
    """신뢰도 점수 계산 로직 검증"""
    pass
```

## Summary

| Decision Area | Choice | Key Rationale |
|---------------|--------|---------------|
| Core Logic | trading_wizard_bundle 재사용 | 3년 검증, 70% 코드 재사용 |
| Authentication | ECDSA P-256 + PEM | 개인정보 미수집, 브라우저 호환 |
| Storage | SQLite (WAL) | 배포 간단, 소규모 적합 |
| Backend | FastAPI | Python 일관성, 비동기 |
| Frontend | React + Vite | 컴포넌트 기반, 빠른 개발 |
| Data Source | yfinance | 기존 검증, 무료 |
| Deployment | Kubernetes + Istio | 기존 클러스터 활용, mTLS, 관측성 |
