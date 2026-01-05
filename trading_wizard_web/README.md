# Trading Wizard Web

볼린저 밴드 기반 트레이딩 전략을 위한 웹 UI 애플리케이션

## 개요

`trading_wizard_bundle`의 핵심 로직을 활용하여 개인 투자자를 위한 웹 기반 인터페이스를 제공합니다.

## 주요 기능

- **데이터 입력**: 개인 포트폴리오 및 거래 데이터 입력
- **이력 관리**: 거래 이력 조회 및 관리
- **시각화**: 포트폴리오 성과 및 매매 신호 시각화

## 프로젝트 구조

```
trading_wizard_web/
├── README.md
├── src/           # 소스 코드
├── static/        # 정적 파일 (CSS, JS)
├── templates/     # HTML 템플릿
└── data/          # 사용자 데이터
```

## 기술 스택

- Backend: Python (Flask/FastAPI)
- Frontend: HTML, CSS, JavaScript
- 시각화: Chart.js / Plotly

## 참고

- 핵심 로직: `../trading_wizard_bundle/`
