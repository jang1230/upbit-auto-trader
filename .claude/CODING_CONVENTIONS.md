# 코딩 컨벤션

## 파일 헤더 규칙

`core/`, `gui/`, `utils/` 폴더의 모든 파일 상단에 필수:
```python
"""
[파일명] - [한줄 설명]

역할:
- [이 모듈이 하는 일 1]
- [이 모듈이 하는 일 2]

Dependencies (이 파일이 사용하는 모듈):
    - core/xxx.py: ClassName (용도)
    - core/yyy.py: ClassName (용도)

Used by (이 파일을 사용하는 모듈):
    - gui/xxx.py: 어떻게 사용하는지
    - core/yyy.py: 어떻게 사용하는지

Key Components:
    - method_name(): 설명
    - another_method(): 설명
"""
```

## 적용 규칙

| 상황 | 필수 작업 |
|------|----------|
| 새 파일 생성 | 위 형식으로 헤더 작성 |
| 메서드 추가 | Key Components 업데이트 |
| import 추가 | Dependencies 업데이트 |
| 다른 파일에서 import | Used by 업데이트 |

## 예시 (v4_trading_engine.py)
```python
"""
V4 거래 엔진 (핵심 오케스트레이터)

역할:
- 모든 V4 컴포넌트 통합
- 그룹별 독립 거래 루프

Dependencies (이 파일이 사용하는 모듈):
    - core/config_manager.py: ConfigManager (설정 로드)
    - core/group_manager.py: GroupManager (그룹 관리)
    - core/position_manager.py: PositionManager (포지션 관리)

Used by (이 파일을 사용하는 모듈):
    - gui/main_window.py: V4TradingEngine 인스턴스 생성/관리

Key Components:
    - start(): 엔진 시작
    - stop(): 엔진 중지
    - process_buy(): 매수 주문 처리
    - process_sell(): 매도 주문 처리
"""
```

## 코드 규칙

- `group_id`: `None` 대신 `"group_null"` 사용
- WebSocket: `threading.Lock` 필수
- 중복 방지: TTL 5초 dedup 패턴
