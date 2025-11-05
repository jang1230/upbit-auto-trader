# V4 구현 계획 (Implementation Plan)

**작성일**: 2025-01-24
**브랜치**: `claude/gui-detailed-design-prep-011CUkVEaFjkinwpHyAKpEy5`
**목표**: V3 → V4 전환 (그룹 기반 시스템 + 자동매수 로직)

---

## 📊 전체 개요

### 주요 변경사항
1. ✅ **그룹 시스템 도입** - 2가지 모드 → 무제한 그룹
2. ✅ **통합 설정 파일** - 여러 JSON → `trading_config.json` 단일화
3. ✅ **자동매수 로직 개선** - Preset 타임프레임 시스템
4. ✅ **GUI 재설계** - 3탭 구조 + 새 다이얼로그들
5. ✅ **포지션 파일 분리** - Dry-run vs Live 별도 관리

### 구현 전략
- **하향식 접근** (Top-down): 설정 → 백엔드 → GUI → 통합
- **단계별 테스트**: 각 Phase마다 독립 테스트
- **V3 호환성 유지**: Phase 5 전까지 기존 기능 보존

---

## 🎯 Phase 1: 핵심 데이터 구조 및 설정 (Foundation)

**목표**: V4의 기반이 되는 설정 파일 및 데이터 스키마 구축

### 1.1 통합 설정 파일 생성

**생성 파일**:
- `config/trading_config.json` (신규)

**스키마 구조**:
```json
{
  "version": "4.0.0",
  "global_settings": {
    "observation_mode": false,
    "min_krw_balance": {
      "enabled": true,
      "amount": 50000
    },
    "daily_loss_limit": {
      "enabled": false,
      "loss_pct": 10.0,
      "calculation_method": "daily_only",
      "action": "alert"
    },
    "telegram": {
      "enabled": true,
      "token": "",
      "chat_id": ""
    },
    "dry_run": false
  },
  "groups": [
    {
      "id": "group_1737700000000",
      "name": "대형코인",
      "coins": ["KRW-BTC", "KRW-ETH"],
      "buy_settings": {
        "mode": "auto",
        "auto_config": {
          "enabled": true,
          "investment_style": "balanced",
          "candle_unit": "60",
          "indicators": {
            "rsi": {
              "enabled": true,
              "period": 14,
              "oversold": 30,
              "overbought": 70
            },
            "macd": {
              "enabled": true,
              "fast": 12,
              "slow": 26,
              "signal": 9
            },
            "volume": {
              "enabled": true,
              "period": 20,
              "threshold": 2.0
            }
          },
          "buy_amount_krw": 50000
        }
      },
      "dca_settings": {
        "mode": "auto",
        "levels": [
          {"drop_pct": -3.0, "buy_ratio": 1.5},
          {"drop_pct": -7.0, "buy_ratio": 2.0},
          {"drop_pct": -12.0, "buy_ratio": 3.0}
        ]
      },
      "profit_settings": {
        "mode": "auto",
        "target_pct": 5.0
      },
      "loss_settings": {
        "mode": "auto",
        "stop_loss_pct": -15.0
      }
    }
  ]
}
```

**구현 작업**:
- [ ] `config/schemas/trading_config_schema.json` 생성 (유효성 검증용)
- [ ] `core/config_manager.py` 신규 작성
  - `load_config()` - 설정 로드 및 스키마 검증
  - `save_config()` - 설정 저장
  - `validate_config()` - JSON 스키마 검증
  - `migrate_from_v3()` - V3 설정 → V4 자동 변환
- [ ] 기본 템플릿 생성 함수 `create_default_config()`

**테스트 항목**:
- ✅ 기본 설정 생성 테스트
- ✅ 잘못된 스키마 감지 테스트
- ✅ V3 마이그레이션 테스트

---

### 1.2 포지션 파일 분리

**생성 파일**:
- `data/positions_live.json` (실거래)
- `data/positions_dryrun.json` (모의거래)
- `data/virtual_balances.json` (Dry-run 잔고)

**positions_live.json 구조**:
```json
{
  "KRW-BTC": {
    "group_id": "group_1737700000000",
    "symbol": "KRW-BTC",
    "status": "active",
    "entry_price": 95000000,
    "entry_amount": 0.001,
    "current_price": 96000000,
    "profit_pct": 1.05,
    "dca_count": 0,
    "dca_history": [],
    "created_at": "2025-01-24T10:00:00"
  }
}
```

**구현 작업**:
- [ ] `core/position_manager.py` 신규 작성
  - `load_positions(mode)` - live/dryrun 선택적 로드
  - `save_position(symbol, data, mode)`
  - `update_position(symbol, updates, mode)`
  - `delete_position(symbol, mode)`
  - `get_all_positions(mode)`
  - `get_positions_by_group(group_id, mode)`
- [ ] Dry-run 전용 잔고 관리
  - `init_virtual_balance(krw_amount)`
  - `update_virtual_balance(krw_delta, coin_delta)`

**테스트 항목**:
- ✅ Live/Dry-run 파일 독립성 테스트
- ✅ 포지션 CRUD 동작 테스트
- ✅ 가상 잔고 계산 정확성 테스트

---

### 1.3 거래 내역 파일 구조

**생성 파일**:
- `data/trade_history.json`

**구조**:
```json
{
  "trades": [
    {
      "id": "trade_1737700123456",
      "group_id": "group_1737700000000",
      "group_name": "대형코인",
      "symbol": "KRW-BTC",
      "action": "buy",
      "type": "initial",
      "price": 95000000,
      "amount": 0.001,
      "total_krw": 95000,
      "timestamp": "2025-01-24T10:00:00",
      "dry_run": false,
      "strategy_signal": "RSI+MACD+Volume",
      "notes": "1시간봉 골든크로스"
    }
  ]
}
```

**구현 작업**:
- [ ] `core/trade_history_manager.py` 신규 작성
  - `add_trade(trade_data)`
  - `get_trades_by_group(group_id)`
  - `get_trades_by_symbol(symbol)`
  - `get_trades_by_date_range(start, end)`
  - `calculate_statistics(group_id=None)`

**테스트 항목**:
- ✅ 거래 기록 저장/조회
- ✅ 통계 계산 정확성

---

## 🎯 Phase 2: 백엔드 핵심 컴포넌트

**목표**: 그룹 관리 및 새로운 전략 시스템 구현

### 2.1 GroupManager 클래스

**생성 파일**:
- `core/group_manager.py` (신규)

**주요 메서드**:
```python
class GroupManager:
    """
    V4 그룹 관리 핵심 클래스

    역할:
    - 그룹 생성/수정/삭제
    - 코인 할당/이동
    - 그룹별 설정 적용
    - 그룹 단위 통계
    """

    def __init__(self, config_path: str):
        """설정 로드 및 초기화"""
        pass

    def create_group(self, name: str, coins: list) -> str:
        """새 그룹 생성 → group_id 반환"""
        pass

    def delete_group(self, group_id: str) -> bool:
        """그룹 삭제 (코인 포지션 확인 필수)"""
        pass

    def update_group_settings(self, group_id: str, settings: dict):
        """그룹 설정 업데이트"""
        pass

    def add_coin_to_group(self, group_id: str, symbol: str):
        """그룹에 코인 추가"""
        pass

    def remove_coin_from_group(self, group_id: str, symbol: str):
        """그룹에서 코인 제거"""
        pass

    def move_coin(self, symbol: str, from_group: str, to_group: str):
        """코인 그룹 이동"""
        pass

    def get_group_by_symbol(self, symbol: str) -> dict:
        """코인이 속한 그룹 조회"""
        pass

    def get_all_groups(self) -> list:
        """모든 그룹 목록"""
        pass

    def validate_group_constraints(self, group_id: str) -> bool:
        """그룹 제약사항 검증 (최대 코인 수 등)"""
        pass
```

**구현 작업**:
- [ ] 기본 CRUD 메서드 구현
- [ ] 그룹 제약사항 검증 로직
  - 한 코인은 하나의 그룹에만 소속
  - 포지션 보유 중인 코인 그룹 변경 금지
  - 그룹 삭제 시 포지션 확인
- [ ] 에러 처리 (GroupNotFoundError, CoinAlreadyAssignedError 등)

**테스트 항목**:
- ✅ 그룹 생성/수정/삭제
- ✅ 코인 할당 및 이동
- ✅ 제약사항 검증

---

### 2.2 V4AutoBuyStrategy 전략 클래스

**생성 파일**:
- `core/strategies/v4_auto_buy_strategy.py` (신규)

**구조**:
```python
class V4AutoBuyStrategy(BaseStrategy):
    """
    V4 자동매수 전략

    특징:
    - Preset 타임프레임 시스템 (4H/1H/15min)
    - TradingView 표준 지표 (RSI, MACD, Volume)
    - 선택적 지표 활성화
    """

    def __init__(
        self,
        symbol: str,
        investment_style: str = "balanced",  # conservative/balanced/aggressive/custom
        candle_unit: str = "60",  # 240/60/15/1
        indicators_config: dict = None,
        **kwargs
    ):
        """
        Args:
            investment_style: 투자 스타일 preset
            candle_unit: 캔들 단위 (분)
            indicators_config: 지표 설정
                {
                    "rsi": {"enabled": True, "period": 14, ...},
                    "macd": {"enabled": True, "fast": 12, ...},
                    "volume": {"enabled": True, "threshold": 2.0, ...}
                }
        """
        super().__init__(symbol)

        # Preset 적용
        if investment_style != "custom":
            self._apply_preset(investment_style)
        else:
            self.candle_unit = candle_unit
            self.indicators_config = indicators_config

        self.name = f"V4 Auto-buy ({investment_style})"

    def _apply_preset(self, style: str):
        """Preset 설정 적용"""
        presets = {
            "conservative": {
                "candle_unit": "240",  # 4시간
                "indicators": {
                    "rsi": {"enabled": True, "period": 14, "oversold": 30, "overbought": 70},
                    "macd": {"enabled": True, "fast": 12, "slow": 26, "signal": 9},
                    "volume": {"enabled": True, "period": 20, "threshold": 2.0}
                }
            },
            "balanced": {
                "candle_unit": "60",  # 1시간
                "indicators": {
                    "rsi": {"enabled": True, "period": 14, "oversold": 30, "overbought": 70},
                    "macd": {"enabled": True, "fast": 12, "slow": 26, "signal": 9},
                    "volume": {"enabled": True, "period": 20, "threshold": 2.0}
                }
            },
            "aggressive": {
                "candle_unit": "15",  # 15분
                "indicators": {
                    "rsi": {"enabled": True, "period": 14, "oversold": 30, "overbought": 70},
                    "macd": {"enabled": True, "fast": 10, "slow": 20, "signal": 7},  # 조정됨
                    "volume": {"enabled": True, "period": 20, "threshold": 3.0}  # 더 높은 기준
                }
            }
        }

        preset = presets[style]
        self.candle_unit = preset["candle_unit"]
        self.indicators_config = preset["indicators"]

    def should_buy(self, candles: pd.DataFrame) -> bool:
        """
        매수 신호 판단

        ⚠️ 중요: 미래 데이터 사용 금지!
        백테스트 시 candles.iloc[:i+1]만 전달됨
        """
        # 1. RSI 체크
        if self.indicators_config["rsi"]["enabled"]:
            rsi = self._calculate_rsi(candles)
            if rsi.iloc[-1] >= self.indicators_config["rsi"]["oversold"]:
                return False  # 과매수 구간 → 매수 금지

        # 2. MACD 골든크로스 체크
        if self.indicators_config["macd"]["enabled"]:
            if not self._check_macd_golden_cross(candles):
                return False

        # 3. Volume surge 체크
        if self.indicators_config["volume"]["enabled"]:
            if not self._check_volume_surge(candles):
                return False

        # 모든 활성화된 조건 만족
        return True

    def should_sell(self, candles: pd.DataFrame) -> bool:
        """
        매도 신호 판단

        주의: DCA 모드에서는 사용 안 됨
        익절/손절은 GroupManager가 처리
        """
        # V4에서는 매도 신호를 전략이 결정하지 않음
        return False

    def _calculate_rsi(self, candles: pd.DataFrame) -> pd.Series:
        """RSI 계산"""
        period = self.indicators_config["rsi"]["period"]
        close = candles['close']

        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def _check_macd_golden_cross(self, candles: pd.DataFrame) -> bool:
        """MACD 골든크로스 확인"""
        config = self.indicators_config["macd"]
        close = candles['close']

        # EMA 계산
        exp1 = close.ewm(span=config["fast"], adjust=False).mean()
        exp2 = close.ewm(span=config["slow"], adjust=False).mean()

        macd = exp1 - exp2
        signal = macd.ewm(span=config["signal"], adjust=False).mean()

        # 골든크로스: 이전에는 아래, 현재는 위
        if len(candles) < 2:
            return False

        prev_macd = macd.iloc[-2]
        prev_signal = signal.iloc[-2]
        curr_macd = macd.iloc[-1]
        curr_signal = signal.iloc[-1]

        return (prev_macd <= prev_signal) and (curr_macd > curr_signal)

    def _check_volume_surge(self, candles: pd.DataFrame) -> bool:
        """거래량 급증 확인"""
        config = self.indicators_config["volume"]
        volume = candles['volume']

        avg_volume = volume.rolling(window=config["period"]).mean()
        current_volume = volume.iloc[-1]
        avg_current = avg_volume.iloc[-1]

        return current_volume >= (avg_current * config["threshold"])

    def get_indicator_values(self, candles: pd.DataFrame) -> dict:
        """현재 지표 값 반환 (모니터링용)"""
        return {
            'rsi': self._calculate_rsi(candles).iloc[-1] if self.indicators_config["rsi"]["enabled"] else None,
            'macd_cross': self._check_macd_golden_cross(candles) if self.indicators_config["macd"]["enabled"] else None,
            'volume_surge': self._check_volume_surge(candles) if self.indicators_config["volume"]["enabled"] else None
        }
```

**구현 작업**:
- [ ] Preset 시스템 구현
- [ ] RSI, MACD, Volume 지표 계산
- [ ] 백테스트 호환성 확인 (미래 데이터 사용 금지)
- [ ] 전략 파라미터 검증

**테스트 항목**:
- ✅ Preset 적용 테스트
- ✅ 각 지표 계산 정확성
- ✅ 매수 신호 생성 테스트
- ✅ 백테스트 엔진과 통합 테스트

---

### 2.3 V4TradingEngine 업데이트

**수정 파일**:
- `core/trading_engine.py` (기존 파일 수정)

**주요 변경사항**:
```python
class V4TradingEngine:
    """
    V4 거래 엔진

    변경사항:
    - GroupManager 통합
    - 그룹별 독립 WebSocket 관리
    - 전역 설정 적용 (관찰 모드, 최소 잔고, 일일 손실 한도)
    """

    def __init__(self, config_path: str = "config/trading_config.json"):
        # 설정 로드
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.load_config()

        # 그룹 관리
        self.group_manager = GroupManager(config_path)

        # 전역 설정
        self.global_settings = self.config["global_settings"]
        self.observation_mode = self.global_settings["observation_mode"]
        self.dry_run = self.global_settings["dry_run"]

        # 포지션 관리
        mode = "dryrun" if self.dry_run else "live"
        self.position_manager = PositionManager(mode)

        # 거래 내역
        self.trade_history = TradeHistoryManager()

        # WebSocket 관리 (그룹별)
        self.websocket_managers = {}

        # 일일 손실 추적
        self.daily_loss_tracker = DailyLossTracker()

    def start(self):
        """거래 시작"""
        if self.observation_mode:
            print("⚠️ 관찰 전용 모드 - 실제 거래 없음")

        # 모든 그룹의 코인에 대해 WebSocket 시작
        for group in self.group_manager.get_all_groups():
            for symbol in group["coins"]:
                self._start_websocket_for_symbol(symbol, group)

    def _start_websocket_for_symbol(self, symbol: str, group: dict):
        """코인별 WebSocket 시작"""
        # WebSocket 생성
        ws = UpbitWebSocket(symbol, candle_unit=group["buy_settings"]["auto_config"]["candle_unit"])

        # 콜백 설정
        ws.on_candle = lambda candle: self._on_candle_update(symbol, group, candle)

        # 시작
        ws.start()

        self.websocket_managers[symbol] = ws

    def _on_candle_update(self, symbol: str, group: dict, candle: dict):
        """캔들 업데이트 콜백"""
        # 1. 전역 제약 확인
        if not self._check_global_constraints():
            return

        # 2. 전략 신호 확인
        if group["buy_settings"]["mode"] == "auto":
            strategy = self._create_strategy_for_group(group, symbol)

            # 최근 200개 캔들 가져오기
            candles = self._get_recent_candles(symbol, group["buy_settings"]["auto_config"]["candle_unit"])

            if strategy.should_buy(candles):
                self._execute_buy(symbol, group)

        # 3. 포지션 관리 (DCA, 익절, 손절)
        self._manage_positions(symbol, group)

    def _check_global_constraints(self) -> bool:
        """전역 제약 확인"""
        # 관찰 모드 체크
        if self.observation_mode:
            return False

        # 최소 잔고 체크
        if self.global_settings["min_krw_balance"]["enabled"]:
            current_balance = self._get_krw_balance()
            min_balance = self.global_settings["min_krw_balance"]["amount"]

            if current_balance < min_balance:
                print(f"⚠️ 최소 잔고 미달: {current_balance:,}원 < {min_balance:,}원")
                return False

        # 일일 손실 한도 체크
        if self.global_settings["daily_loss_limit"]["enabled"]:
            if self.daily_loss_tracker.is_limit_reached():
                print("⚠️ 일일 손실 한도 도달")
                return False

        return True

    def _create_strategy_for_group(self, group: dict, symbol: str):
        """그룹 설정으로 전략 생성"""
        auto_config = group["buy_settings"]["auto_config"]

        return V4AutoBuyStrategy(
            symbol=symbol,
            investment_style=auto_config["investment_style"],
            candle_unit=auto_config["candle_unit"],
            indicators_config=auto_config["indicators"]
        )

    def _execute_buy(self, symbol: str, group: dict):
        """매수 실행"""
        if self.observation_mode:
            print(f"[관찰] {symbol} 매수 신호 (실행 안 함)")
            return

        buy_amount = group["buy_settings"]["auto_config"]["buy_amount_krw"]

        # 주문 실행
        order_result = self._place_buy_order(symbol, buy_amount)

        # 거래 기록
        self.trade_history.add_trade({
            "group_id": group["id"],
            "group_name": group["name"],
            "symbol": symbol,
            "action": "buy",
            "type": "initial",
            "total_krw": buy_amount,
            "dry_run": self.dry_run
        })

    def _manage_positions(self, symbol: str, group: dict):
        """포지션 관리 (DCA, 익절, 손절)"""
        position = self.position_manager.get_position(symbol)

        if not position:
            return

        current_price = self._get_current_price(symbol)
        profit_pct = ((current_price - position["entry_price"]) / position["entry_price"]) * 100

        # DCA 체크
        if group["dca_settings"]["mode"] == "auto":
            for level in group["dca_settings"]["levels"]:
                if profit_pct <= level["drop_pct"] and position["dca_count"] < len(group["dca_settings"]["levels"]):
                    self._execute_dca(symbol, group, level)
                    break

        # 익절 체크
        if group["profit_settings"]["mode"] == "auto":
            if profit_pct >= group["profit_settings"]["target_pct"]:
                self._execute_sell(symbol, group, "profit")

        # 손절 체크
        if group["loss_settings"]["mode"] == "auto":
            if profit_pct <= group["loss_settings"]["stop_loss_pct"]:
                self._execute_sell(symbol, group, "loss")
```

**구현 작업**:
- [ ] GroupManager 통합
- [ ] 전역 제약 로직 구현
- [ ] 그룹별 WebSocket 관리
- [ ] 일일 손실 추적 (`core/daily_loss_tracker.py` 신규)
- [ ] 포지션 관리 로직 업데이트

**테스트 항목**:
- ✅ 그룹별 독립 거래 동작
- ✅ 전역 제약 적용 테스트
- ✅ 관찰 모드 동작 확인

---

### 2.4 일일 손실 추적 시스템

**생성 파일**:
- `core/daily_loss_tracker.py` (신규)

**구조**:
```python
class DailyLossTracker:
    """
    일일 손실 한도 추적

    기능:
    - 09:00 기준 스냅샷 생성
    - 실시간 손실률 계산
    - 한도 도달 시 알림/청산
    """

    def __init__(self, config: dict):
        self.config = config
        self.daily_snapshot = None
        self.limit_reached = False
        self.reset_time = "09:00:00"

    def check_and_reset(self):
        """매일 09:00에 리셋"""
        current_time = datetime.now().time()
        reset_time = datetime.strptime(self.reset_time, "%H:%M:%S").time()

        if current_time >= reset_time and self.daily_snapshot is None:
            self._create_snapshot()
            self.limit_reached = False

    def _create_snapshot(self):
        """당일 시작 스냅샷 생성"""
        # 현재 보유 코인 평가액 + KRW 잔고
        self.daily_snapshot = {
            "start_valuation": self._get_total_valuation(),
            "start_krw": self._get_krw_balance(),
            "timestamp": datetime.now()
        }

    def calculate_daily_loss(self) -> float:
        """당일 손실률 계산"""
        if not self.daily_snapshot:
            return 0.0

        current_valuation = self._get_total_valuation()
        start_valuation = self.daily_snapshot["start_valuation"]

        loss_pct = ((current_valuation - start_valuation) / start_valuation) * 100

        return loss_pct

    def is_limit_reached(self) -> bool:
        """한도 도달 여부"""
        if not self.config["enabled"]:
            return False

        if self.limit_reached:
            return True

        current_loss = self.calculate_daily_loss()

        if current_loss <= -self.config["loss_pct"]:
            self.limit_reached = True
            self._handle_limit_reached(current_loss)
            return True

        return False

    def _handle_limit_reached(self, loss_pct: float):
        """한도 도달 시 처리"""
        action = self.config["action"]

        if action == "alert":
            # 텔레그램 알림만
            self._send_alert(loss_pct)
        elif action == "liquidate":
            # 전체 청산
            self._liquidate_all_positions(loss_pct)
```

**구현 작업**:
- [ ] 일일 스냅샷 로직
- [ ] 손실률 계산
- [ ] 알림/청산 처리
- [ ] 09:00 자동 리셋

**테스트 항목**:
- ✅ 손실률 계산 정확성
- ✅ 한도 도달 시 동작
- ✅ 리셋 동작 확인

---

## 🎯 Phase 3: GUI 컴포넌트

**목표**: V4 GUI 구현 (그룹 관리, 설정 다이얼로그)

### 3.1 Main Window 재설계

**수정 파일**:
- `gui/main_window.py` (기존 파일 대폭 수정)

**주요 변경사항**:
```python
class V4MainWindow(QMainWindow):
    """
    V4 메인 윈도우

    변경사항:
    - 3탭 구조 (Active Positions, Trade History, Statistics)
    - 모드 선택 라디오 버튼 삭제
    - 그룹 관리 UI 추가
    - 전역 설정 UI 추가
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Upbit Auto Trader V4")
        self.setGeometry(100, 100, 1600, 850)

        # 중앙 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 레이아웃
        main_layout = QVBoxLayout(central_widget)

        # 상단 컨트롤 패널
        self._create_top_panel(main_layout)

        # 탭 위젯
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # 3개 탭 생성
        self._create_positions_tab()
        self._create_history_tab()
        self._create_statistics_tab()

        # 하단 상태바
        self._create_status_bar()

    def _create_top_panel(self, layout):
        """상단 컨트롤 패널"""
        panel = QHBoxLayout()

        # 그룹 관리 버튼
        btn_group_manage = QPushButton("그룹 관리")
        btn_group_manage.clicked.connect(self.open_group_management_dialog)
        panel.addWidget(btn_group_manage)

        # 전역 설정 버튼
        btn_global_settings = QPushButton("전역 설정")
        btn_global_settings.clicked.connect(self.open_global_settings_dialog)
        panel.addWidget(btn_global_settings)

        # 관찰 모드 토글
        self.chk_observation = QCheckBox("관찰 전용 모드")
        self.chk_observation.stateChanged.connect(self.toggle_observation_mode)
        panel.addWidget(self.chk_observation)

        # Dry-run 토글
        self.chk_dryrun = QCheckBox("Dry Run (모의거래)")
        self.chk_dryrun.stateChanged.connect(self.toggle_dry_run)
        panel.addWidget(self.chk_dryrun)

        # 시작/중지 버튼
        self.btn_start = QPushButton("거래 시작")
        self.btn_start.clicked.connect(self.start_trading)
        panel.addWidget(self.btn_start)

        self.btn_stop = QPushButton("거래 중지")
        self.btn_stop.clicked.connect(self.stop_trading)
        self.btn_stop.setEnabled(False)
        panel.addWidget(self.btn_stop)

        panel.addStretch()

        layout.addLayout(panel)

    def _create_positions_tab(self):
        """Tab 1: 활성 포지션"""
        positions_widget = QWidget()
        layout = QVBoxLayout(positions_widget)

        # 그룹 필터
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("그룹 필터:"))

        self.combo_group_filter = QComboBox()
        self.combo_group_filter.addItem("전체")
        self.combo_group_filter.currentTextChanged.connect(self.filter_positions_by_group)
        filter_layout.addWidget(self.combo_group_filter)

        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # 포지션 테이블
        self.positions_table = QTableWidget()
        self.positions_table.setColumnCount(10)
        self.positions_table.setHorizontalHeaderLabels([
            "그룹", "코인", "진입가", "현재가", "수익률(%)",
            "DCA 횟수", "목표 익절", "손절선", "상태", "액션"
        ])
        layout.addWidget(self.positions_table)

        self.tab_widget.addTab(positions_widget, "활성 포지션")

    def _create_history_tab(self):
        """Tab 2: 거래 내역"""
        history_widget = QWidget()
        layout = QVBoxLayout(history_widget)

        # 필터
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("기간:"))

        self.date_start = QDateEdit()
        self.date_end = QDateEdit()
        filter_layout.addWidget(self.date_start)
        filter_layout.addWidget(QLabel("~"))
        filter_layout.addWidget(self.date_end)

        btn_filter = QPushButton("조회")
        btn_filter.clicked.connect(self.load_trade_history)
        filter_layout.addWidget(btn_filter)

        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # 거래 내역 테이블
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(9)
        self.history_table.setHorizontalHeaderLabels([
            "시간", "그룹", "코인", "액션", "타입", "가격", "수량", "총액", "비고"
        ])
        layout.addWidget(self.history_table)

        self.tab_widget.addTab(history_widget, "거래 내역")

    def _create_statistics_tab(self):
        """Tab 3: 통계"""
        stats_widget = QWidget()
        layout = QVBoxLayout(stats_widget)

        # 전체 통계
        overall_group = QGroupBox("전체 통계")
        overall_layout = QGridLayout()

        self.lbl_total_profit = QLabel("총 수익: 0원 (0%)")
        overall_layout.addWidget(self.lbl_total_profit, 0, 0)

        self.lbl_win_rate = QLabel("승률: 0%")
        overall_layout.addWidget(self.lbl_win_rate, 0, 1)

        self.lbl_total_trades = QLabel("총 거래: 0회")
        overall_layout.addWidget(self.lbl_total_trades, 1, 0)

        overall_group.setLayout(overall_layout)
        layout.addWidget(overall_group)

        # 그룹별 통계
        group_stats_group = QGroupBox("그룹별 통계")
        group_stats_layout = QVBoxLayout()

        self.group_stats_table = QTableWidget()
        self.group_stats_table.setColumnCount(6)
        self.group_stats_table.setHorizontalHeaderLabels([
            "그룹명", "코인 수", "총 수익", "승률", "거래 횟수", "평균 보유 시간"
        ])
        group_stats_layout.addWidget(self.group_stats_table)

        group_stats_group.setLayout(group_stats_layout)
        layout.addWidget(group_stats_group)

        self.tab_widget.addTab(stats_widget, "통계")
```

**구현 작업**:
- [ ] 3탭 구조 구현
- [ ] 상단 컨트롤 패널
- [ ] 포지션 테이블 실시간 업데이트
- [ ] 그룹 필터 기능
- [ ] 통계 계산 및 표시

**테스트 항목**:
- ✅ UI 레이아웃 확인
- ✅ 실시간 업데이트 동작
- ✅ 필터 기능 테스트

---

### 3.2 그룹 관리 다이얼로그

**생성 파일**:
- `gui/group_management_dialog.py` (신규)

**구조**:
```python
class GroupManagementDialog(QDialog):
    """
    그룹 관리 다이얼로그

    기능:
    - 그룹 목록 표시
    - 그룹 생성/수정/삭제
    - 코인 할당/이동
    """

    def __init__(self, group_manager: GroupManager, parent=None):
        super().__init__(parent)
        self.group_manager = group_manager

        self.setWindowTitle("그룹 관리")
        self.setModal(True)
        self.resize(800, 600)

        self._setup_ui()
        self._load_groups()

    def _setup_ui(self):
        """UI 구성"""
        layout = QVBoxLayout(self)

        # 상단 버튼
        btn_layout = QHBoxLayout()

        btn_new_group = QPushButton("새 그룹 생성")
        btn_new_group.clicked.connect(self.create_new_group)
        btn_layout.addWidget(btn_new_group)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # 그룹 목록
        self.group_list = QTableWidget()
        self.group_list.setColumnCount(5)
        self.group_list.setHorizontalHeaderLabels([
            "그룹명", "코인 수", "활성 포지션", "설정", "액션"
        ])
        layout.addWidget(self.group_list)

    def create_new_group(self):
        """새 그룹 생성"""
        dialog = GroupSettingsDialog(None, self.group_manager)
        if dialog.exec_() == QDialog.Accepted:
            self._load_groups()

    def edit_group(self, group_id: str):
        """그룹 수정"""
        group = self.group_manager.get_group_by_id(group_id)
        dialog = GroupSettingsDialog(group, self.group_manager)
        if dialog.exec_() == QDialog.Accepted:
            self._load_groups()

    def delete_group(self, group_id: str):
        """그룹 삭제"""
        # 포지션 확인
        positions = self.group_manager.get_active_positions_in_group(group_id)

        if positions:
            QMessageBox.warning(
                self,
                "삭제 불가",
                f"해당 그룹에 {len(positions)}개의 활성 포지션이 있습니다.\n"
                "모든 포지션을 정리한 후 삭제해주세요."
            )
            return

        # 확인
        reply = QMessageBox.question(
            self,
            "그룹 삭제",
            "정말 이 그룹을 삭제하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.group_manager.delete_group(group_id)
            self._load_groups()
```

**구현 작업**:
- [ ] 그룹 목록 표시
- [ ] CRUD 기능 구현
- [ ] 포지션 확인 및 경고

**테스트 항목**:
- ✅ 그룹 생성/수정/삭제
- ✅ 제약사항 검증

---

### 3.3 그룹 설정 다이얼로그

**생성 파일**:
- `gui/group_settings_dialog.py` (신규)

**구조**:
```python
class GroupSettingsDialog(QDialog):
    """
    그룹 설정 다이얼로그

    기능:
    - 그룹명 설정
    - 코인 선택
    - 매수/DCA/익절/손절 설정
    """

    def __init__(self, group: dict = None, group_manager: GroupManager = None, parent=None):
        super().__init__(parent)
        self.group = group
        self.group_manager = group_manager
        self.is_edit_mode = group is not None

        self.setWindowTitle("그룹 설정" if self.is_edit_mode else "새 그룹 생성")
        self.setModal(True)
        self.resize(900, 700)

        self._setup_ui()

        if self.is_edit_mode:
            self._load_group_data()

    def _setup_ui(self):
        """UI 구성"""
        layout = QVBoxLayout(self)

        # 그룹명
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("그룹명:"))
        self.txt_group_name = QLineEdit()
        name_layout.addWidget(self.txt_group_name)
        layout.addLayout(name_layout)

        # 코인 선택
        coins_group = QGroupBox("코인 선택")
        coins_layout = QVBoxLayout()

        self.coin_list = QListWidget()
        self.coin_list.setSelectionMode(QListWidget.MultiSelection)
        coins_layout.addWidget(self.coin_list)

        coins_group.setLayout(coins_layout)
        layout.addWidget(coins_group)

        # 매수 설정
        buy_group = QGroupBox("매수 설정")
        buy_layout = QVBoxLayout()

        self.radio_buy_manual = QRadioButton("수동 (Upbit에서 직접)")
        self.radio_buy_auto = QRadioButton("자동")
        self.radio_buy_disabled = QRadioButton("사용 안 함")

        buy_layout.addWidget(self.radio_buy_manual)
        buy_layout.addWidget(self.radio_buy_auto)
        buy_layout.addWidget(self.radio_buy_disabled)

        # 자동매수 상세 설정 버튼
        self.btn_auto_buy_settings = QPushButton("자동매수 설정...")
        self.btn_auto_buy_settings.clicked.connect(self.open_auto_buy_settings)
        self.btn_auto_buy_settings.setEnabled(False)
        buy_layout.addWidget(self.btn_auto_buy_settings)

        self.radio_buy_auto.toggled.connect(
            lambda checked: self.btn_auto_buy_settings.setEnabled(checked)
        )

        buy_group.setLayout(buy_layout)
        layout.addWidget(buy_group)

        # DCA 설정
        dca_group = QGroupBox("DCA 설정")
        dca_layout = QVBoxLayout()

        # ... (DCA UI 구성)

        dca_group.setLayout(dca_layout)
        layout.addWidget(dca_group)

        # 익절 설정
        # ... (익절 UI 구성)

        # 손절 설정
        # ... (손절 UI 구성)

        # 저장 버튼
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("저장")
        btn_save.clicked.connect(self.save_group)
        btn_layout.addWidget(btn_save)

        btn_cancel = QPushButton("취소")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        layout.addLayout(btn_layout)

    def open_auto_buy_settings(self):
        """자동매수 설정 다이얼로그 열기"""
        dialog = AutoBuySettingsDialog(self.auto_buy_config, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.auto_buy_config = dialog.get_config()

    def save_group(self):
        """그룹 저장"""
        # 유효성 검증
        if not self.txt_group_name.text():
            QMessageBox.warning(self, "오류", "그룹명을 입력해주세요.")
            return

        # 그룹 데이터 생성
        group_data = {
            "name": self.txt_group_name.text(),
            "coins": self._get_selected_coins(),
            "buy_settings": self._get_buy_settings(),
            "dca_settings": self._get_dca_settings(),
            "profit_settings": self._get_profit_settings(),
            "loss_settings": self._get_loss_settings()
        }

        # 저장
        if self.is_edit_mode:
            self.group_manager.update_group(self.group["id"], group_data)
        else:
            self.group_manager.create_group(group_data)

        self.accept()
```

**구현 작업**:
- [ ] 폼 UI 구성
- [ ] 4가지 설정 섹션 (매수/DCA/익절/손절)
- [ ] 유효성 검증
- [ ] 데이터 저장

**테스트 항목**:
- ✅ 설정 저장/로드
- ✅ 유효성 검증

---

### 3.4 자동매수 설정 다이얼로그

**생성 파일**:
- `gui/auto_buy_settings_dialog.py` (신규)

**구조**:
```python
class AutoBuySettingsDialog(QDialog):
    """
    자동매수 설정 다이얼로그

    기능:
    - 투자 스타일 선택 (Preset)
    - 기술적 지표 선택 및 파라미터 설정
    - 매수 금액 설정
    """

    def __init__(self, config: dict = None, parent=None):
        super().__init__(parent)
        self.config = config or self._get_default_config()

        self.setWindowTitle("자동매수 설정")
        self.setModal(True)
        self.resize(700, 600)

        self._setup_ui()
        self._load_config()

    def _setup_ui(self):
        """UI 구성"""
        layout = QVBoxLayout(self)

        # 투자 스타일 (Preset)
        style_group = QGroupBox("투자 스타일")
        style_layout = QVBoxLayout()

        self.radio_conservative = QRadioButton("보수적 (4시간봉) - 하루 1~5번")
        self.radio_balanced = QRadioButton("균형형 (1시간봉) - 하루 5~15번 ⭐ 추천")
        self.radio_aggressive = QRadioButton("적극적 (15분봉) - 하루 15~30번")
        self.radio_custom = QRadioButton("커스텀 (고급 사용자)")

        self.radio_balanced.setChecked(True)

        style_layout.addWidget(self.radio_conservative)
        style_layout.addWidget(self.radio_balanced)
        style_layout.addWidget(self.radio_aggressive)
        style_layout.addWidget(self.radio_custom)

        # 커스텀 타임프레임 선택
        custom_layout = QHBoxLayout()
        custom_layout.addWidget(QLabel("타임프레임:"))
        self.combo_timeframe = QComboBox()
        self.combo_timeframe.addItems(["1분", "3분", "5분", "15분", "30분", "1시간", "4시간"])
        self.combo_timeframe.setEnabled(False)
        custom_layout.addWidget(self.combo_timeframe)
        custom_layout.addStretch()
        style_layout.addLayout(custom_layout)

        self.radio_custom.toggled.connect(
            lambda checked: self.combo_timeframe.setEnabled(checked)
        )

        style_group.setLayout(style_layout)
        layout.addWidget(style_group)

        # 기술적 지표
        indicators_group = QGroupBox("기술적 지표 (체크된 조건을 모두 만족해야 매수)")
        indicators_layout = QVBoxLayout()

        # RSI
        self.chk_rsi = QCheckBox("RSI (상대강도지수)")
        self.chk_rsi.setChecked(True)
        indicators_layout.addWidget(self.chk_rsi)

        rsi_params = QHBoxLayout()
        rsi_params.addSpacing(20)
        rsi_params.addWidget(QLabel("기간:"))
        self.spin_rsi_period = QSpinBox()
        self.spin_rsi_period.setRange(5, 50)
        self.spin_rsi_period.setValue(14)
        rsi_params.addWidget(self.spin_rsi_period)

        rsi_params.addWidget(QLabel("과매도:"))
        self.spin_rsi_oversold = QSpinBox()
        self.spin_rsi_oversold.setRange(10, 40)
        self.spin_rsi_oversold.setValue(30)
        rsi_params.addWidget(self.spin_rsi_oversold)

        rsi_params.addWidget(QLabel("과매수:"))
        self.spin_rsi_overbought = QSpinBox()
        self.spin_rsi_overbought.setRange(60, 90)
        self.spin_rsi_overbought.setValue(70)
        rsi_params.addWidget(self.spin_rsi_overbought)

        rsi_params.addStretch()
        indicators_layout.addLayout(rsi_params)

        # MACD
        self.chk_macd = QCheckBox("MACD (추세 전환)")
        self.chk_macd.setChecked(True)
        indicators_layout.addWidget(self.chk_macd)

        macd_params = QHBoxLayout()
        macd_params.addSpacing(20)
        macd_params.addWidget(QLabel("Fast:"))
        self.spin_macd_fast = QSpinBox()
        self.spin_macd_fast.setRange(5, 30)
        self.spin_macd_fast.setValue(12)
        macd_params.addWidget(self.spin_macd_fast)

        macd_params.addWidget(QLabel("Slow:"))
        self.spin_macd_slow = QSpinBox()
        self.spin_macd_slow.setRange(10, 50)
        self.spin_macd_slow.setValue(26)
        macd_params.addWidget(self.spin_macd_slow)

        macd_params.addWidget(QLabel("Signal:"))
        self.spin_macd_signal = QSpinBox()
        self.spin_macd_signal.setRange(5, 20)
        self.spin_macd_signal.setValue(9)
        macd_params.addWidget(self.spin_macd_signal)

        macd_params.addStretch()
        indicators_layout.addLayout(macd_params)

        # Volume
        self.chk_volume = QCheckBox("거래량 급증")
        self.chk_volume.setChecked(True)
        indicators_layout.addWidget(self.chk_volume)

        volume_params = QHBoxLayout()
        volume_params.addSpacing(20)
        volume_params.addWidget(QLabel("평균 기간:"))
        self.spin_volume_period = QSpinBox()
        self.spin_volume_period.setRange(10, 50)
        self.spin_volume_period.setValue(20)
        volume_params.addWidget(self.spin_volume_period)

        volume_params.addWidget(QLabel("급증 기준:"))
        self.spin_volume_threshold = QDoubleSpinBox()
        self.spin_volume_threshold.setRange(1.0, 5.0)
        self.spin_volume_threshold.setSingleStep(0.1)
        self.spin_volume_threshold.setValue(2.0)
        self.spin_volume_threshold.setSuffix("배")
        volume_params.addWidget(self.spin_volume_threshold)

        volume_params.addStretch()
        indicators_layout.addLayout(volume_params)

        indicators_group.setLayout(indicators_layout)
        layout.addWidget(indicators_group)

        # 매수 금액
        amount_group = QGroupBox("매수 금액")
        amount_layout = QHBoxLayout()

        amount_layout.addWidget(QLabel("1회 매수 금액:"))
        self.spin_buy_amount = QSpinBox()
        self.spin_buy_amount.setRange(5000, 10000000)
        self.spin_buy_amount.setSingleStep(10000)
        self.spin_buy_amount.setValue(50000)
        self.spin_buy_amount.setSuffix(" 원")
        amount_layout.addWidget(self.spin_buy_amount)

        amount_layout.addStretch()
        amount_group.setLayout(amount_layout)
        layout.addWidget(amount_group)

        # 저장 버튼
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("저장")
        btn_save.clicked.connect(self.accept)
        btn_layout.addWidget(btn_save)

        btn_cancel = QPushButton("취소")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        layout.addLayout(btn_layout)

    def get_config(self) -> dict:
        """현재 설정 반환"""
        # 투자 스타일 결정
        if self.radio_conservative.isChecked():
            investment_style = "conservative"
            candle_unit = "240"
        elif self.radio_balanced.isChecked():
            investment_style = "balanced"
            candle_unit = "60"
        elif self.radio_aggressive.isChecked():
            investment_style = "aggressive"
            candle_unit = "15"
        else:
            investment_style = "custom"
            timeframe_map = {"1분": "1", "3분": "3", "5분": "5", "15분": "15",
                           "30분": "30", "1시간": "60", "4시간": "240"}
            candle_unit = timeframe_map[self.combo_timeframe.currentText()]

        return {
            "enabled": True,
            "investment_style": investment_style,
            "candle_unit": candle_unit,
            "indicators": {
                "rsi": {
                    "enabled": self.chk_rsi.isChecked(),
                    "period": self.spin_rsi_period.value(),
                    "oversold": self.spin_rsi_oversold.value(),
                    "overbought": self.spin_rsi_overbought.value()
                },
                "macd": {
                    "enabled": self.chk_macd.isChecked(),
                    "fast": self.spin_macd_fast.value(),
                    "slow": self.spin_macd_slow.value(),
                    "signal": self.spin_macd_signal.value()
                },
                "volume": {
                    "enabled": self.chk_volume.isChecked(),
                    "period": self.spin_volume_period.value(),
                    "threshold": self.spin_volume_threshold.value()
                }
            },
            "buy_amount_krw": self.spin_buy_amount.value()
        }
```

**구현 작업**:
- [ ] Preset 선택 UI
- [ ] 지표별 파라미터 입력 UI
- [ ] 설정 저장/로드
- [ ] 커스텀 모드 지원

**테스트 항목**:
- ✅ Preset 적용 확인
- ✅ 커스텀 설정 저장/로드
- ✅ 파라미터 유효성 검증

---

### 3.5 전역 설정 다이얼로그

**생성 파일**:
- `gui/global_settings_dialog.py` (신규)

**구조**:
```python
class GlobalSettingsDialog(QDialog):
    """
    전역 설정 다이얼로그

    기능:
    - 관찰 모드
    - 최소 KRW 잔고
    - 일일 손실 한도
    - 텔레그램 설정
    - Dry-run 모드
    """

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.config = config

        self.setWindowTitle("전역 설정")
        self.setModal(True)
        self.resize(600, 500)

        self._setup_ui()
        self._load_config()

    def _setup_ui(self):
        """UI 구성"""
        layout = QVBoxLayout(self)

        # 최소 KRW 잔고
        balance_group = QGroupBox("최소 KRW 잔고")
        balance_layout = QVBoxLayout()

        self.chk_min_balance = QCheckBox("최소 잔고 유지")
        balance_layout.addWidget(self.chk_min_balance)

        balance_amount_layout = QHBoxLayout()
        balance_amount_layout.addSpacing(20)
        balance_amount_layout.addWidget(QLabel("금액:"))
        self.spin_min_balance = QSpinBox()
        self.spin_min_balance.setRange(0, 10000000)
        self.spin_min_balance.setSingleStep(10000)
        self.spin_min_balance.setValue(50000)
        self.spin_min_balance.setSuffix(" 원")
        balance_amount_layout.addWidget(self.spin_min_balance)
        balance_amount_layout.addStretch()
        balance_layout.addLayout(balance_amount_layout)

        balance_group.setLayout(balance_layout)
        layout.addWidget(balance_group)

        # 일일 손실 한도
        loss_group = QGroupBox("일일 손실 한도")
        loss_layout = QVBoxLayout()

        self.chk_daily_loss = QCheckBox("일일 손실 한도 사용")
        loss_layout.addWidget(self.chk_daily_loss)

        loss_pct_layout = QHBoxLayout()
        loss_pct_layout.addSpacing(20)
        loss_pct_layout.addWidget(QLabel("손실 한도:"))
        self.spin_loss_pct = QDoubleSpinBox()
        self.spin_loss_pct.setRange(1.0, 50.0)
        self.spin_loss_pct.setSingleStep(1.0)
        self.spin_loss_pct.setValue(10.0)
        self.spin_loss_pct.setSuffix(" %")
        loss_pct_layout.addWidget(self.spin_loss_pct)
        loss_pct_layout.addStretch()
        loss_layout.addLayout(loss_pct_layout)

        loss_action_layout = QHBoxLayout()
        loss_action_layout.addSpacing(20)
        loss_action_layout.addWidget(QLabel("도달 시 동작:"))
        self.combo_loss_action = QComboBox()
        self.combo_loss_action.addItems(["알림만", "전체 매도"])
        loss_action_layout.addWidget(self.combo_loss_action)
        loss_action_layout.addStretch()
        loss_layout.addLayout(loss_action_layout)

        loss_group.setLayout(loss_layout)
        layout.addWidget(loss_group)

        # 텔레그램
        telegram_group = QGroupBox("텔레그램 알림")
        telegram_layout = QVBoxLayout()

        self.chk_telegram = QCheckBox("텔레그램 사용")
        telegram_layout.addWidget(self.chk_telegram)

        telegram_token_layout = QHBoxLayout()
        telegram_token_layout.addSpacing(20)
        telegram_token_layout.addWidget(QLabel("Bot Token:"))
        self.txt_telegram_token = QLineEdit()
        telegram_token_layout.addWidget(self.txt_telegram_token)
        telegram_layout.addLayout(telegram_token_layout)

        telegram_chat_layout = QHBoxLayout()
        telegram_chat_layout.addSpacing(20)
        telegram_chat_layout.addWidget(QLabel("Chat ID:"))
        self.txt_telegram_chat_id = QLineEdit()
        telegram_chat_layout.addWidget(self.txt_telegram_chat_id)
        telegram_layout.addLayout(telegram_chat_layout)

        telegram_group.setLayout(telegram_layout)
        layout.addWidget(telegram_group)

        # 저장 버튼
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("저장")
        btn_save.clicked.connect(self.save_settings)
        btn_layout.addWidget(btn_save)

        btn_cancel = QPushButton("취소")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        layout.addLayout(btn_layout)
```

**구현 작업**:
- [ ] 전역 설정 UI
- [ ] 설정 저장/로드
- [ ] 유효성 검증

**테스트 항목**:
- ✅ 설정 적용 확인
- ✅ 제약 동작 테스트

---

## 🎯 Phase 4: 통합 및 테스트

**목표**: 백엔드-GUI 통합 및 전체 시스템 테스트

### 4.1 통합 작업

**작업 항목**:
- [ ] GUI → Backend 연결
  - GroupManagementDialog → GroupManager
  - GroupSettingsDialog → ConfigManager
  - MainWindow → V4TradingEngine
- [ ] Signal/Slot 연결
  - 실시간 포지션 업데이트
  - 거래 내역 업데이트
  - 통계 업데이트
- [ ] WebSocket 이벤트 처리
  - 캔들 업데이트 → 전략 신호 → GUI 반영
  - 500ms 업데이트 throttling

### 4.2 단위 테스트

**생성 파일**:
- `tests/test_group_manager.py`
- `tests/test_v4_auto_buy_strategy.py`
- `tests/test_config_manager.py`
- `tests/test_position_manager.py`
- `tests/test_daily_loss_tracker.py`

**테스트 커버리지 목표**: 80%+

### 4.3 통합 테스트

**시나리오**:
1. **그룹 생성 → 자동매수 → DCA → 익절**
   - 그룹 A 생성 (BTC, 균형형 전략)
   - 매수 신호 발생 확인
   - DCA 레벨 트리거 확인
   - 익절 도달 시 매도 확인

2. **다중 그룹 동시 운영**
   - 그룹 A (자동), 그룹 B (수동), 그룹 C (DCA 없음)
   - 각 그룹 독립 동작 확인
   - 전역 제약 적용 확인

3. **일일 손실 한도 테스트**
   - 손실 -10% 도달
   - 알림 발송 확인
   - 신규 매수 중지 확인

4. **관찰 모드 테스트**
   - 관찰 모드 활성화
   - 신호 감지는 하되 주문 없음 확인

### 4.4 Dry-run 테스트

**기간**: 최소 3일
**목표**:
- 가상 잔고 관리 정확성
- 전략 신호 발생 빈도
- GUI 실시간 업데이트
- 메모리 누수 확인

---

## 🎯 Phase 5: 마이그레이션 및 배포

**목표**: V3 → V4 전환 및 실거래 준비

### 5.1 V3 설정 마이그레이션

**생성 파일**:
- `tools/migrate_v3_to_v4.py` (마이그레이션 스크립트)

**마이그레이션 로직**:
```python
def migrate_v3_to_v4():
    """
    V3 설정을 V4 형식으로 변환

    변환 규칙:
    - dca_config.json → 그룹 "반자동 모드" 생성
    - auto_trading_config.json → 그룹 "자동 모드" 생성
    - positions.json → positions_live.json (group_id 추가)
    """
    # V3 설정 로드
    dca_config = load_json("config/dca_config.json")
    auto_config = load_json("config/auto_trading_config.json")

    # V4 통합 설정 생성
    v4_config = {
        "version": "4.0.0",
        "global_settings": {
            "observation_mode": False,
            "min_krw_balance": {"enabled": False, "amount": 50000},
            "daily_loss_limit": {"enabled": False, "loss_pct": 10.0},
            "telegram": auto_config.get("telegram", {}),
            "dry_run": False
        },
        "groups": []
    }

    # 그룹 1: 반자동 모드 (V3의 dca_config)
    semi_auto_group = {
        "id": f"group_{int(time.time() * 1000)}",
        "name": "반자동 모드 (V3 마이그레이션)",
        "coins": [],  # 사용자가 수동으로 추가
        "buy_settings": {"mode": "manual"},
        "dca_settings": {
            "mode": "auto",
            "levels": dca_config.get("dca_levels", [])
        },
        "profit_settings": {
            "mode": "auto",
            "target_pct": dca_config.get("profit_target_pct", 5.0)
        },
        "loss_settings": {
            "mode": "auto",
            "stop_loss_pct": dca_config.get("stop_loss_pct", -15.0)
        }
    }

    v4_config["groups"].append(semi_auto_group)

    # 그룹 2: 자동 모드 (V3의 auto_trading_config)
    auto_group = {
        "id": f"group_{int(time.time() * 1000) + 1}",
        "name": "자동 모드 (V3 마이그레이션)",
        "coins": auto_config.get("symbols", []),
        "buy_settings": {
            "mode": "auto",
            "auto_config": {
                "enabled": True,
                "investment_style": "balanced",  # 기본값
                "candle_unit": "60",
                "indicators": {
                    "rsi": {"enabled": True, "period": 14, "oversold": 30, "overbought": 70},
                    "macd": {"enabled": True, "fast": 12, "slow": 26, "signal": 9},
                    "volume": {"enabled": True, "period": 20, "threshold": 2.0}
                },
                "buy_amount_krw": auto_config.get("buy_amount_krw", 50000)
            }
        },
        "dca_settings": {
            "mode": "auto",
            "levels": auto_config.get("dca_levels", [])
        },
        "profit_settings": {
            "mode": "auto",
            "target_pct": auto_config.get("profit_target_pct", 5.0)
        },
        "loss_settings": {
            "mode": "auto",
            "stop_loss_pct": auto_config.get("stop_loss_pct", -15.0)
        }
    }

    v4_config["groups"].append(auto_group)

    # 저장
    save_json("config/trading_config.json", v4_config)

    # V3 파일 백업
    backup_v3_files()

    print("✅ V3 → V4 마이그레이션 완료!")
    print(f"   - 그룹 1: {semi_auto_group['name']}")
    print(f"   - 그룹 2: {auto_group['name']}")
```

**작업 항목**:
- [ ] 마이그레이션 스크립트 작성
- [ ] V3 백업 기능
- [ ] 마이그레이션 검증
- [ ] 문서화 (사용자 가이드)

### 5.2 V3 파일 백업 및 정리

**백업 대상**:
- `config/dca_config.json` → `config/backup_v3/`
- `config/auto_trading_config.json` → `config/backup_v3/`
- `data/positions.json` → `data/backup_v3/`

**작업 항목**:
- [ ] 백업 디렉토리 생성
- [ ] 파일 이동 (삭제 아님, 백업)
- [ ] V3 코드 보존 (브랜치 생성)

### 5.3 문서 업데이트

**업데이트 대상**:
- `README.md` - V4 기능 설명 추가
- `INSTALLATION.md` - V4 설치 가이드
- `docs/V4_USER_GUIDE.md` (신규) - V4 사용자 가이드
  - 그룹 관리 방법
  - 자동매수 설정 가이드
  - 전역 설정 설명
  - 마이그레이션 가이드

**작업 항목**:
- [ ] V4 사용자 가이드 작성
- [ ] README 업데이트
- [ ] 스크린샷 추가

### 5.4 배포 준비

**체크리스트**:
- [ ] Dry-run 최소 3일 테스트 완료
- [ ] 메모리 누수 없음 확인
- [ ] 모든 단위/통합 테스트 통과
- [ ] 문서 완성
- [ ] V3 백업 완료
- [ ] 실거래 최소 금액으로 1주일 테스트

---

## 📅 타임라인 및 우선순위

### 예상 작업 기간

| Phase | 내용 | 예상 시간 | 우선순위 |
|-------|------|-----------|---------|
| Phase 1 | 핵심 데이터 구조 | 4-6 시간 | 🔴 최우선 |
| Phase 2 | 백엔드 컴포넌트 | 8-10 시간 | 🔴 최우선 |
| Phase 3 | GUI 컴포넌트 | 10-12 시간 | 🟡 중요 |
| Phase 4 | 통합 및 테스트 | 6-8 시간 | 🟡 중요 |
| Phase 5 | 마이그레이션 및 배포 | 4-6 시간 | 🟢 보통 |
| **총계** | | **32-42 시간** | |

### 개발 순서 (권장)

1. **Week 1 (Phase 1-2)**
   - Day 1-2: Phase 1 (데이터 구조)
   - Day 3-5: Phase 2 (백엔드)
   - 목표: 백엔드 완성 및 테스트

2. **Week 2 (Phase 3)**
   - Day 1-3: GUI 다이얼로그
   - Day 4-5: Main Window 재설계
   - 목표: GUI 완성

3. **Week 3 (Phase 4-5)**
   - Day 1-2: 통합 및 단위 테스트
   - Day 3-4: Dry-run 테스트
   - Day 5: 마이그레이션 및 문서화

---

## ⚠️ 주의사항 및 리스크

### 1. 기존 포지션 처리
- **리스크**: V3 → V4 전환 시 기존 활성 포지션 손실 가능
- **대응**:
  - 모든 포지션 정리 후 전환 권장
  - 또는 마이그레이션 스크립트로 group_id 자동 할당

### 2. 설정 파일 백업
- **리스크**: 마이그레이션 실패 시 설정 손실
- **대응**:
  - V3 파일 자동 백업 (`config/backup_v3/`)
  - 수동 백업도 권장

### 3. WebSocket 부하
- **리스크**: 50개 코인 동시 감시 시 시스템 부하
- **대응**:
  - 초기에는 그룹당 5-10개 코인으로 제한
  - 성능 모니터링 후 점진적 확대

### 4. 일일 손실 한도 오작동
- **리스크**: 계산 오류로 잘못된 청산
- **대응**:
  - Dry-run 충분히 테스트
  - 초기에는 "알림만" 모드 사용

---

## 🔄 롤백 계획

V4에 문제 발생 시 V3로 즉시 복귀 가능하도록:

1. **V3 브랜치 보존**
   ```bash
   git branch v3-stable
   git tag v3.0.0
   ```

2. **V3 설정 백업 유지**
   - `config/backup_v3/` 삭제 금지
   - 최소 1개월 보관

3. **롤백 절차**
   ```bash
   git checkout v3-stable
   cp config/backup_v3/* config/
   python main.py
   ```

---

## 📊 체크리스트

### Phase 1 체크리스트
- [ ] `config/trading_config.json` 스키마 정의
- [ ] `core/config_manager.py` 구현
- [ ] `core/position_manager.py` 구현
- [ ] `core/trade_history_manager.py` 구현
- [ ] Phase 1 단위 테스트 작성 및 통과

### Phase 2 체크리스트
- [ ] `core/group_manager.py` 구현
- [ ] `core/strategies/v4_auto_buy_strategy.py` 구현
- [ ] `core/trading_engine.py` V4 업데이트
- [ ] `core/daily_loss_tracker.py` 구현
- [ ] Phase 2 단위 테스트 작성 및 통과

### Phase 3 체크리스트
- [ ] `gui/main_window.py` V4 재설계
- [ ] `gui/group_management_dialog.py` 구현
- [ ] `gui/group_settings_dialog.py` 구현
- [ ] `gui/auto_buy_settings_dialog.py` 구현
- [ ] `gui/global_settings_dialog.py` 구현
- [ ] GUI 통합 테스트

### Phase 4 체크리스트
- [ ] Backend-GUI 통합
- [ ] Signal/Slot 연결
- [ ] 통합 테스트 시나리오 작성 및 실행
- [ ] Dry-run 3일 테스트
- [ ] 메모리/성능 모니터링

### Phase 5 체크리스트
- [ ] 마이그레이션 스크립트 작성
- [ ] V3 백업 자동화
- [ ] V4 사용자 가이드 작성
- [ ] README 업데이트
- [ ] 실거래 최소 금액 테스트 (1주일)

---

## 🎉 완료 기준

V4 구현 완료 조건:

1. ✅ 모든 Phase 체크리스트 완료
2. ✅ 단위 테스트 커버리지 80%+
3. ✅ Dry-run 3일 안정성 확인
4. ✅ 실거래 1주일 테스트 성공
5. ✅ 사용자 문서 완성
6. ✅ V3 롤백 가능 상태 유지

---

**다음 단계**: Phase 1 시작 - `config/trading_config.json` 스키마 정의 및 `ConfigManager` 구현
