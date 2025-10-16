# Implementation Plan: 볼린저 밴드 스퀴즈 전략 개선 - 보조 지표 추가

**Branch**: `002-spec-md` | **Date**: 2025-10-15 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-spec-md/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

현재 볼린저 밴드 스퀴즈 전략의 낮은 수익률(-2%~0%)을 개선하기 위해 보조 기술 지표(거래량, RSI, MACD)를 추가하고 신호 신뢰도 평가 시스템을 구축합니다. Phase 1(거래량+RSI)부터 Phase 4(ATR 동적 손절)까지 단계적으로 구현하여 최종적으로 승률 75~80%, 연간 수익률 +15~20%를 달성합니다.

## Technical Context

**Language/Version**: Python 3.11 (기존 프로젝트 표준)
**Primary Dependencies**:
- pandas ^2.0.0 (데이터 처리)
- numpy ^1.24.0 (수치 계산)
- pydantic ^2.0.0 (데이터 검증)
- yfinance ^0.2.66 (시장 데이터)
- openpyxl ^3.1.5 (결과 출력)

**Storage**:
- SQLite (백테스트 로그: data/logs/backtest.db)
- Excel (결과 보고서: results/*.xlsx)
- YAML (설정 파일: config/*.yaml)

**Testing**: pytest ^8.0.0 with:
- pytest-benchmark (성능 테스트)
- hypothesis (속성 기반 테스트)
- pytest-cov (커버리지)

**Target Platform**: macOS/Linux desktop (Python 3.11+ 환경)

**Project Type**: Single project (기존 구조 확장)

**Performance Goals**:
- 지표 계산: 단일 종목 1년 데이터 < 100ms
- 백테스트: KOSPI 100 종목 1년 < 5분
- 신호 생성: 실시간 데이터 처리 < 100ms

**Constraints**:
- 백테스트 실행 시간 기존 대비 2배 이상 증가 불가
- 메모리 사용량 500MB 이하 (constitution 요구사항)
- 기존 볼린저 밴드 전략 코드와의 호환성 유지

**Scale/Scope**:
- 3개 새로운 지표 모듈 (RSI, MACD, ATR)
- 24개 기능 요구사항
- 4개 Phase로 구성된 점진적 출시
- 기존 8개 유닛 테스트 → 20+ 유닛 테스트로 확장

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Data Integrity First ✅

**Status**: PASS
**Compliance**:
- FR-006: 거래량 데이터 없는 경우 필터 건너뛰고 로그 기록
- FR-007, FR-011: RSI/MACD 계산 위한 충분한 과거 데이터 없으면 필터 비활성화
- Edge case: 백테스트 중 모든 지표 계산 불가능 시 해당 기간 건너뛰고 경고 표시
- 기존 데이터 파이프라인 검증 로직 재사용

### II. Risk Management by Design ✅

**Status**: PASS
**Compliance**:
- 기존 손절매 시스템 유지 (5% 고정 손절)
- FR-017~019: ATR 기반 동적 손절매 추가 (Phase 4)
- FR-013: 신뢰도 점수 임계값(기본 60점) 기반 진입 제어
- Edge case: 자금 부족 시 신뢰도 점수 높은 순서대로 우선순위 배정
- 기존 포트폴리오 노출 한도 설정 유지

### III. Test-First Development (NON-NEGOTIABLE) ✅

**Status**: PASS
**Compliance**:
- 각 지표(RSI, MACD, ATR) 계산에 대한 유닛 테스트 우선 작성
- Given-When-Then 형식의 수락 시나리오를 테스트 케이스로 변환
- 기존 TDD 워크플로우 준수 (tests/unit/, tests/integration/)
- hypothesis를 활용한 속성 기반 테스트로 엣지 케이스 검증

### IV. Backtesting Integrity ✅

**Status**: PASS
**Compliance**:
- 모든 지표 계산은 시점(t)의 과거 데이터만 사용 (lookahead bias 방지)
- FR-001~003: 20일 평균 거래량, 14일 RSI, MACD(12/26/9) 등 과거 데이터만 참조
- 거래 비용(slippage, 수수료) 기존 백테스트 엔진에서 이미 포함
- 신규 지표도 기존 시간 경계 엄격히 준수

### V. Transparency & Auditability ✅

**Status**: PASS
**Compliance**:
- FR-014: 각 거래 내역에 신호 신뢰도 점수 기록
- FR-023: 백테스트 결과에 각 필터 적용 여부 포함
- 기존 구조화된 로깅(JSON) 유지
- EnhancedSignal 엔티티에 각 필터 통과 여부(거래량, RSI, MACD) 포함

### VI. Configuration Over Code ✅

**Status**: PASS
**Compliance**:
- FR-015, FR-021~022: 신뢰도 임계값, 거래량 배수, RSI 임계값을 설정 파일에서 조정 가능
- FR-018: 동적 손절매 활성화/비활성화 설정 옵션
- FR-020: 각 필터(거래량, RSI, MACD) 개별 활성화/비활성화
- 기존 YAML 설정 구조 확장

### VII. Defensive Validation ✅

**Status**: PASS
**Compliance**:
- 모든 임계값(거래량 배수 1.5, RSI 70, 신뢰도 60점) 양수 검증
- pydantic 모델로 설정 파일 스키마 검증
- 지표 계산 전 데이터 충분성 검증 (FR-007, FR-011)
- 잘못된 설정 시 명확한 오류 메시지와 함께 실행 중단

### Post-Design Re-check

*To be completed after Phase 1 (data-model.md, contracts/ complete)*

## Project Structure

### Documentation (this feature)

```
specs/002-spec-md/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── config-schema.yaml  # 설정 파일 스키마
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```
src/
├── indicators/
│   ├── __init__.py
│   ├── bollinger.py     # 기존
│   ├── squeeze.py       # 기존
│   ├── momentum.py      # 신규: RSI, MACD, ATR 계산
│   └── volume.py        # 신규: 거래량 필터
├── signals/
│   ├── __init__.py
│   ├── generator.py     # 수정: 보조 지표 통합, 신뢰도 평가
│   └── confidence.py    # 신규: 신호 신뢰도 평가 시스템
├── models/
│   ├── __init__.py
│   ├── config.py        # 수정: 새로운 설정 옵션 추가
│   ├── portfolio.py     # 기존
│   ├── stock_data.py    # 기존
│   └── trade.py         # 수정: 신뢰도 점수 필드 추가
├── backtest/
│   ├── __init__.py
│   ├── engine.py        # 수정: 개선된 신호 생성기 통합
│   └── metrics.py       # 기존
├── risk/
│   ├── __init__.py
│   └── controls.py      # 수정: ATR 기반 동적 손절매 추가
├── data/
│   ├── __init__.py
│   └── storage.py       # 기존
├── utils/
│   ├── __init__.py
│   ├── logging.py       # 기존
│   └── validation.py    # 수정: 새로운 설정 검증 규칙
└── cli/
    ├── __init__.py
    └── main.py          # 기존

tests/
├── unit/
│   ├── test_bollinger.py         # 기존
│   ├── test_squeeze.py           # 기존
│   ├── test_momentum.py          # 신규: RSI, MACD, ATR 테스트
│   ├── test_volume_filter.py    # 신규: 거래량 필터 테스트
│   ├── test_confidence.py        # 신규: 신뢰도 평가 테스트
│   ├── test_signals_enhanced.py  # 신규: 통합 신호 생성 테스트
│   ├── test_risk.py              # 수정: 동적 손절매 테스트 추가
│   └── test_config.py            # 수정: 새 설정 옵션 검증 테스트
├── integration/
│   ├── test_backtest_e2e.py      # 수정: Phase별 백테스트 시나리오
│   └── test_indicator_pipeline.py # 신규: 지표 계산 파이프라인 테스트
└── contract/
    └── test_config_schema.py     # 수정: 확장된 설정 스키마 검증

config/
├── default.yaml         # 수정: 신규 설정 옵션 추가
└── examples/
    ├── phase1_volume_rsi.yaml    # 신규: Phase 1 설정 예제
    ├── phase2_with_macd.yaml     # 신규: Phase 2 설정 예제
    └── phase3_confidence.yaml    # 신규: Phase 3 설정 예제
```

**Structure Decision**: Single project 구조 유지. 기존 src/ 아래 모듈 확장 방식으로 진행하여 코드 중복 최소화 및 기존 인프라(백테스트 엔진, CLI, 테스트 프레임워크) 재사용. 새로운 지표 모듈(momentum.py, volume.py)과 신뢰도 평가 시스템(confidence.py)을 추가하고, 기존 signals/generator.py를 점진적으로 개선.

## Complexity Tracking

*No Constitution violations requiring justification*

모든 개선 사항이 기존 아키텍처 내에서 구현 가능하며, Constitution의 7대 원칙을 모두 준수합니다. 새로운 외부 의존성이나 복잡한 패턴 도입 없이 표준 수학 라이브러리(pandas, numpy)만으로 지표 계산이 가능합니다.
