"""
V4 일일 손실 추적 시스템

역할:
- 매일 09:00 기준 스냅샷 생성
- 실시간 손실률 계산
- 한도 도달 시 알림/청산
"""

import json
import os
from datetime import datetime, time as dt_time
from typing import Dict, Any, Optional, Callable
from pathlib import Path


class DailyLossTracker:
    """일일 손실 한도 추적"""

    SNAPSHOT_PATH = "data/daily_snapshot.json"

    def __init__(
        self,
        config: Dict[str, Any],
        get_valuation_fn: Callable[[], float],
        get_krw_balance_fn: Callable[[], float],
        send_alert_fn: Optional[Callable[[str], None]] = None,
        liquidate_fn: Optional[Callable[[str], None]] = None
    ):
        """
        Args:
            config: daily_loss_limit 설정
                {
                    "enabled": True,
                    "loss_pct": 10.0,
                    "calculation_method": "daily_only",
                    "action": "alert"
                }
            get_valuation_fn: 현재 총 평가액 조회 함수
            get_krw_balance_fn: 현재 KRW 잔고 조회 함수
            send_alert_fn: 알림 전송 함수 (optional)
            liquidate_fn: 전체 청산 함수 (optional)
        """
        self.config = config
        self.get_valuation_fn = get_valuation_fn
        self.get_krw_balance_fn = get_krw_balance_fn
        self.send_alert_fn = send_alert_fn
        self.liquidate_fn = liquidate_fn

        # 상태
        self.daily_snapshot: Optional[Dict[str, Any]] = None
        self.limit_reached = False

        # 설정
        self.reset_hour = 9  # 09:00 리셋

        # 스냅샷 로드
        self._load_snapshot()

    def _load_snapshot(self) -> None:
        """저장된 스냅샷 로드"""
        if not os.path.exists(self.SNAPSHOT_PATH):
            return

        try:
            with open(self.SNAPSHOT_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.daily_snapshot = data.get('snapshot')
                self.limit_reached = data.get('limit_reached', False)

            # 날짜 확인 (다른 날짜면 무효화)
            if self.daily_snapshot:
                snapshot_date = datetime.fromisoformat(self.daily_snapshot['timestamp']).date()
                today = datetime.now().date()

                if snapshot_date != today:
                    self.daily_snapshot = None
                    self.limit_reached = False

        except (json.JSONDecodeError, KeyError):
            print("⚠️ 스냅샷 파일 파싱 오류")
            self.daily_snapshot = None

    def _save_snapshot(self) -> None:
        """스냅샷 저장"""
        os.makedirs(os.path.dirname(self.SNAPSHOT_PATH), exist_ok=True)

        data = {
            'snapshot': self.daily_snapshot,
            'limit_reached': self.limit_reached,
            'last_updated': datetime.now().isoformat()
        }

        with open(self.SNAPSHOT_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def check_and_reset(self) -> None:
        """
        매일 09:00에 자동 리셋 확인

        사용법: TradingEngine 메인 루프에서 주기적으로 호출
        """
        if not self.config.get('enabled', False):
            return

        current_time = datetime.now().time()
        reset_time = dt_time(hour=self.reset_hour, minute=0, second=0)

        # 09:00 이후이고 스냅샷이 없으면 생성
        if current_time >= reset_time and self.daily_snapshot is None:
            self._create_snapshot()

        # 자정 넘어가면 무효화 (다음 09:00까지 대기)
        if self.daily_snapshot:
            snapshot_date = datetime.fromisoformat(self.daily_snapshot['timestamp']).date()
            today = datetime.now().date()

            if snapshot_date != today:
                print("📅 날짜 변경 - 스냅샷 초기화")
                self.daily_snapshot = None
                self.limit_reached = False
                self._save_snapshot()

    def _create_snapshot(self) -> None:
        """당일 시작 스냅샷 생성"""
        # 현재 평가액
        total_valuation = self.get_valuation_fn()
        krw_balance = self.get_krw_balance_fn()

        self.daily_snapshot = {
            'start_valuation': total_valuation,
            'start_krw': krw_balance,
            'start_total': total_valuation + krw_balance,
            'timestamp': datetime.now().isoformat()
        }

        self.limit_reached = False
        self._save_snapshot()

        print(f"📸 일일 스냅샷 생성 ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
        print(f"   - 시작 평가액: {total_valuation:,.0f}원")
        print(f"   - 시작 KRW: {krw_balance:,.0f}원")
        print(f"   - 총 자산: {self.daily_snapshot['start_total']:,.0f}원")

    def calculate_daily_loss(self) -> Optional[float]:
        """
        당일 손실률 계산

        Returns:
            손실률 (%) 또는 None (스냅샷 없음)
        """
        if not self.config.get('enabled', False):
            return None

        if not self.daily_snapshot:
            return None

        # 현재 평가액
        current_valuation = self.get_valuation_fn()
        current_krw = self.get_krw_balance_fn()
        current_total = current_valuation + current_krw

        # 손실률 계산
        start_total = self.daily_snapshot['start_total']

        if start_total == 0:
            return 0.0

        calculation_method = self.config.get('calculation_method', 'daily_only')

        if calculation_method == 'daily_only':
            # 방법 1: 당일 변화만 (09:00 기준)
            loss_pct = ((current_total - start_total) / start_total) * 100
        elif calculation_method == 'total_account':
            # 방법 2: 전체 계좌 기준 (누적 손실 포함)
            # 이 경우 시작 자산은 최초 입금액을 기준으로 해야 함
            # 현재는 daily_only와 동일하게 구현 (추후 확장 가능)
            loss_pct = ((current_total - start_total) / start_total) * 100
        else:
            loss_pct = 0.0

        return loss_pct

    def is_limit_reached(self) -> bool:
        """
        한도 도달 여부 확인

        Returns:
            한도 도달 시 True
        """
        if not self.config.get('enabled', False):
            return False

        # 이미 한도 도달
        if self.limit_reached:
            return True

        # 스냅샷 없으면 확인 불가
        if not self.daily_snapshot:
            return False

        # 현재 손실률 계산
        current_loss = self.calculate_daily_loss()

        if current_loss is None:
            return False

        # 한도 확인 (손실은 음수이므로 <= 비교)
        loss_limit = -abs(self.config.get('loss_pct', 10.0))

        if current_loss <= loss_limit:
            self.limit_reached = True
            self._save_snapshot()
            self._handle_limit_reached(current_loss)
            return True

        return False

    def _handle_limit_reached(self, loss_pct: float) -> None:
        """
        한도 도달 시 처리

        Args:
            loss_pct: 손실률 (%)
        """
        action = self.config.get('action', 'alert')

        message = (
            f"⚠️ 일일 손실 한도 도달!\n"
            f"   - 손실률: {loss_pct:.2f}%\n"
            f"   - 한도: {self.config.get('loss_pct', 10.0)}%\n"
            f"   - 액션: {action}"
        )

        print(message)

        if action == "alert":
            # 알림만
            if self.send_alert_fn:
                self.send_alert_fn(message)

        elif action == "liquidate":
            # 전체 청산
            print("🚨 전체 청산 시작...")

            if self.liquidate_fn:
                self.liquidate_fn(f"일일 손실 한도 도달 ({loss_pct:.2f}%)")
            else:
                print("⚠️ liquidate_fn이 설정되지 않았습니다.")

            if self.send_alert_fn:
                self.send_alert_fn(f"🚨 전체 청산 완료\n손실률: {loss_pct:.2f}%")

    def reset_manually(self) -> None:
        """수동 리셋 (테스트용)"""
        self.daily_snapshot = None
        self.limit_reached = False
        self._save_snapshot()
        print("✅ 일일 손실 추적 수동 리셋 완료")

    def get_status(self) -> Dict[str, Any]:
        """
        현재 상태 조회

        Returns:
            상태 딕셔너리
        """
        if not self.config.get('enabled', False):
            return {
                'enabled': False,
                'status': 'disabled'
            }

        if not self.daily_snapshot:
            return {
                'enabled': True,
                'status': 'no_snapshot',
                'message': f'09:00 이후 스냅샷 생성 예정'
            }

        current_loss = self.calculate_daily_loss()

        return {
            'enabled': True,
            'status': 'active',
            'snapshot_time': self.daily_snapshot['timestamp'],
            'start_total': self.daily_snapshot['start_total'],
            'current_loss_pct': current_loss,
            'loss_limit': self.config.get('loss_pct', 10.0),
            'limit_reached': self.limit_reached,
            'action': self.config.get('action', 'alert')
        }


if __name__ == "__main__":
    # 테스트 코드
    print("=== DailyLossTracker 테스트 ===\n")

    # Mock 함수들
    def get_valuation():
        return 500000.0  # 현재 포지션 평가액

    def get_krw():
        return 300000.0  # KRW 잔고

    def send_alert(message):
        print(f"[텔레그램 알림]\n{message}")

    def liquidate(reason):
        print(f"[청산 실행] {reason}")

    # 설정
    config = {
        'enabled': True,
        'loss_pct': 10.0,
        'calculation_method': 'daily_only',
        'action': 'alert'
    }

    # 생성
    tracker = DailyLossTracker(
        config=config,
        get_valuation_fn=get_valuation,
        get_krw_balance_fn=get_krw,
        send_alert_fn=send_alert,
        liquidate_fn=liquidate
    )

    # 1. 스냅샷 생성
    print("1. 스냅샷 강제 생성")
    tracker._create_snapshot()
    print()

    # 2. 상태 조회
    print("2. 상태 조회")
    status = tracker.get_status()
    print(f"   - 활성화: {status['enabled']}")
    print(f"   - 상태: {status['status']}")
    print(f"   - 시작 자산: {status.get('start_total', 0):,.0f}원")
    print(f"   - 현재 손실률: {status.get('current_loss_pct', 0):.2f}%")
    print()

    # 3. 손실 시뮬레이션
    print("3. 손실 시뮬레이션 (평가액 -15% 하락)")

    # 평가액을 425,000원으로 변경 (500,000 * 0.85)
    def get_valuation_loss():
        return 425000.0

    tracker.get_valuation_fn = get_valuation_loss

    loss_pct = tracker.calculate_daily_loss()
    print(f"   - 계산된 손실률: {loss_pct:.2f}%")
    print()

    # 4. 한도 확인
    print("4. 한도 확인")
    is_reached = tracker.is_limit_reached()
    print(f"   - 한도 도달: {is_reached}")
    print()

    # 5. 수동 리셋
    print("5. 수동 리셋")
    tracker.reset_manually()
    print()

    print("✅ 테스트 완료!")
