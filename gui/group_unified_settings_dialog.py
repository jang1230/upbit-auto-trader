"""
GroupUnifiedSettingsDialog - 그룹 통합 설정 다이얼로그

자동매수, DCA, 익절/손절 설정을 탭으로 통합
"""

from typing import Optional, TYPE_CHECKING

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QPushButton, QWidget, QLabel, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
import logging

from core.config_manager import ConfigManager
from gui.auto_buy_settings_dialog_v2 import AutoBuySettingsDialogV2
from gui.level_settings_dialog import LevelSettingsDialog

if TYPE_CHECKING:
    from core.position_manager import PositionManager

logger = logging.getLogger(__name__)


class GroupUnifiedSettingsDialog(QDialog):
    """
    그룹 통합 설정 다이얼로그

    3개 탭으로 구성:
    - 탭1: 자동매수 전략 (V4/Expert)
    - 탭2: DCA 레벨 설정
    - 탭3: 익절/손절 설정

    저장 버튼 1번으로 모든 설정 반영
    """

    settings_saved = Signal()

    def __init__(
        self,
        group_id: str,
        position_manager: Optional["PositionManager"] = None,
        is_trading_running: bool = False,
        parent=None
    ):
        """
        Args:
            group_id: 그룹 ID
            position_manager: 포지션 매니저 (레벨 리셋용)
            is_trading_running: 거래 실행 중 여부
            parent: 부모 위젯
        """
        super().__init__(parent)

        self.group_id = group_id
        self.position_manager = position_manager
        self.is_trading_running = is_trading_running
        self.config_manager = ConfigManager()

        # 설정 로드
        self.group_config = self._load_group_config()

        self.setWindowTitle(f"⚙️ 그룹 설정: {self.group_config.get('name', group_id)}")
        self.setMinimumWidth(800)  # 너비 800px (원래대로)
        self.setMinimumHeight(400)  # 높이 400px (500 → 400 축소)
        self.resize(800, 400)  # 초기 크기 설정

        self._init_ui()

    def _load_group_config(self) -> dict:
        """그룹 설정 로드"""
        try:
            config = self.config_manager.load_config()
            groups = config.get('groups', {})

            if self.group_id not in groups:
                raise ValueError(f"그룹을 찾을 수 없습니다: {self.group_id}")

            return groups[self.group_id]

        except Exception as e:
            logger.error(f"❌ 그룹 설정 로드 실패: {e}")
            # 기본 설정 반환
            return {
                'name': self.group_id,
                'coins': [],
                'buy_settings': {'mode': 'manual'},
                'dca_settings': {'mode': 'disabled'},
                'profit_settings': {'mode': 'disabled'},
                'loss_settings': {'mode': 'disabled'}
            }

    def _init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # 탭 위젯 생성
        self.tab_widget = QTabWidget()
        self.tab_widget.setFont(QFont("맑은 고딕", 10))

        # 탭1: 자동매수 전략
        self.tab1_widget = self._create_tab1_autobuy()
        self.tab_widget.addTab(self.tab1_widget, "📊 자동매수 전략")

        # 탭2: DCA/익절/손절 (LevelSettingsDialog 임베딩)
        self.tab2_widget = self._create_tab2_levels()
        self.tab_widget.addTab(self.tab2_widget, "📈 DCA / 익절 / 손절")

        layout.addWidget(self.tab_widget)

        # 하단 버튼
        button_layout = self._create_button_layout()
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def _create_tab1_autobuy(self) -> QWidget:
        """탭1: 자동매수 전략 (AutoBuySettingsDialogV2 임베딩)"""
        # 자동매수 설정 추출 (buy_settings 전체를 전달해야 mode 정보 포함됨)
        buy_settings = self.group_config.get('buy_settings', {})

        # AutoBuySettingsDialogV2를 위젯으로 사용
        # buy_settings 전체를 전달 (mode="manual"이면 manual 모드로 로드됨)
        # embedded=True로 설정하여 사이즈 제약 스킵 (부모 다이얼로그 크기 우선)
        autobuy_dialog = AutoBuySettingsDialogV2(config=buy_settings.copy(), parent=self, embedded=True)

        # 다이얼로그를 위젯처럼 사용하기 위해 윈도우 플래그 제거
        autobuy_dialog.setWindowFlags(Qt.Widget)

        # 내부 버튼 레이아웃 숨기기 (상위 다이얼로그 버튼 사용)
        main_layout = autobuy_dialog.layout()
        if main_layout and main_layout.count() > 0:
            last_item = main_layout.itemAt(main_layout.count() - 1)
            if last_item and last_item.layout():
                # 버튼 레이아웃 숨김
                button_layout = last_item.layout()
                for i in range(button_layout.count()):
                    widget = button_layout.itemAt(i).widget()
                    if widget:
                        widget.setVisible(False)

        # 참조 저장 (나중에 get_config() 호출용)
        self.autobuy_widget = autobuy_dialog

        return autobuy_dialog

    def _create_tab2_levels(self) -> QWidget:
        """탭2: DCA/익절/손절 레벨 (LevelSettingsDialog 임베딩)"""
        # LevelSettingsDialog를 위젯으로 사용
        level_dialog = LevelSettingsDialog(
            config_manager=self.config_manager,
            group_id=self.group_id,
            group_name=self.group_config.get('name', self.group_id),
            position_manager=self.position_manager,
            is_trading_running=self.is_trading_running,
            parent=self
        )

        # 다이얼로그를 위젯처럼 사용하기 위해 윈도우 플래그 제거
        level_dialog.setWindowFlags(Qt.Widget)

        # 내부 버튼 레이아웃 숨기기
        main_layout = level_dialog.layout()
        if main_layout and main_layout.count() > 0:
            # 마지막 아이템이 버튼 레이아웃
            last_item = main_layout.itemAt(main_layout.count() - 1)
            if last_item and last_item.layout():
                button_layout = last_item.layout()
                for i in range(button_layout.count()):
                    widget = button_layout.itemAt(i).widget()
                    if widget:
                        widget.setVisible(False)

        # 참조 저장 (나중에 get_config() 호출용)
        self.level_widget = level_dialog

        return level_dialog

    def _create_button_layout(self) -> QHBoxLayout:
        """하단 버튼 레이아웃"""
        layout = QHBoxLayout()
        layout.addStretch()

        # 취소 버튼
        cancel_btn = QPushButton("취소")
        cancel_btn.setFont(QFont("맑은 고딕", 10))
        cancel_btn.setFixedWidth(100)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)

        # 저장 버튼
        save_btn = QPushButton("💾 저장")
        save_btn.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        save_btn.setFixedWidth(100)
        save_btn.setStyleSheet(
            "QPushButton {"
            "  background-color: #4CAF50;"
            "  color: white;"
            "  padding: 8px;"
            "  border-radius: 4px;"
            "}"
            "QPushButton:hover {"
            "  background-color: #45a049;"
            "}"
        )
        save_btn.clicked.connect(self._on_save_clicked)
        layout.addWidget(save_btn)

        return layout

    def _on_save_clicked(self):
        """저장 버튼 클릭 처리"""
        try:
            # 1. 거래 실행 중이면 저장 불가
            if self.is_trading_running:
                QMessageBox.warning(
                    self,
                    "저장 불가",
                    "거래가 실행 중입니다.\n정지 후 설정을 변경해주세요."
                )
                return

            logger.info(f"💾 그룹 {self.group_id} 통합 설정 저장 시작...")

            # 탭1: 자동매수 설정 수집
            autobuy_config = self.autobuy_widget.get_config()
            logger.info(f"  📊 자동매수 설정: {autobuy_config.get('strategy')}")

            # 탭2: DCA/익절/손절 설정 수집
            dca_levels = self.level_widget._get_dca_levels()
            profit_levels = self.level_widget._get_profit_levels()
            loss_levels = self.level_widget._get_loss_levels()
            logger.info(f"  📈 DCA 레벨: {len(dca_levels)}개")
            logger.info(f"  💰 익절 레벨: {len(profit_levels)}개")
            logger.info(f"  🛑 손절 레벨: {len(loss_levels)}개")

            # 레벨 검증
            if not self.level_widget._validate_levels(dca_levels, profit_levels, loss_levels):
                logger.warning("레벨 검증 실패")
                return

            # ConfigManager로 설정 저장
            config = self.config_manager.load_config()
            groups = config.get("groups", {})

            if self.group_id not in groups:
                raise ValueError(f"그룹을 찾을 수 없습니다: {self.group_id}")

            group = groups[self.group_id]

            # 2. 기존 설정 가져오기 (변경 감지용)
            old_dca_levels = group.get("dca_settings", {}).get("levels", [])
            old_profit_levels = group.get("profit_settings", {}).get("levels", [])
            old_loss_levels = group.get("loss_settings", {}).get("levels", [])

            # 3. 변경 감지
            dca_changed = old_dca_levels != dca_levels
            profit_changed = old_profit_levels != profit_levels
            loss_changed = old_loss_levels != loss_levels

            changed_items = []
            if dca_changed:
                changed_items.append("DCA")
            if profit_changed:
                changed_items.append("익절")
            if loss_changed:
                changed_items.append("손절")

            # 4. 변경된 항목이 있으면 확인 다이얼로그
            if changed_items:
                if not self.position_manager:
                    result = QMessageBox.warning(
                        self,
                        "경고",
                        f"변경된 항목: {', '.join(changed_items)}\n\n"
                        "position_manager가 없어 레벨 실행 기록을 리셋할 수 없습니다.\n"
                        "설정만 변경하시겠습니까?",
                        QMessageBox.Yes | QMessageBox.No
                    )
                    if result == QMessageBox.No:
                        return
                else:
                    result = QMessageBox.question(
                        self,
                        "설정 변경 확인",
                        f"변경된 항목: {', '.join(changed_items)}\n\n"
                        f"해당 그룹의 모든 포지션에서 {', '.join(changed_items)} 실행 기록이 리셋됩니다.\n"
                        "조건 충족 시 다시 실행될 수 있습니다.\n\n"
                        "계속하시겠습니까?",
                        QMessageBox.Yes | QMessageBox.No
                    )
                    if result == QMessageBox.No:
                        return

            # 5. 레벨 리셋 (변경된 항목만)
            reset_backup = {}
            if self.position_manager and changed_items:
                try:
                    if dca_changed:
                        reset_backup["dca"] = self._reset_group_levels("dca")
                    if profit_changed:
                        reset_backup["profit"] = self._reset_group_levels("profit")
                    if loss_changed:
                        reset_backup["loss"] = self._reset_group_levels("loss")
                except Exception as e:
                    self._rollback_reset(reset_backup)
                    raise ValueError(f"레벨 리셋 실패: {e}")

            # 자동매수 설정 업데이트
            # autobuy_config는 이미 전체 buy_settings 구조 (mode, buy_amount_krw, auto_config)를 포함
            group["buy_settings"] = autobuy_config

            # DCA 설정 업데이트 (레벨 개수에 따라 mode 자동 설정)
            if "dca_settings" not in group:
                group["dca_settings"] = {"mode": "auto"}
            group["dca_settings"]["levels"] = dca_levels
            group["dca_settings"]["mode"] = "auto" if len(dca_levels) > 0 else "disabled"

            # 익절 설정 업데이트 (레벨 개수에 따라 mode 자동 설정)
            if "profit_settings" not in group:
                group["profit_settings"] = {"mode": "auto"}
            group["profit_settings"]["levels"] = profit_levels
            group["profit_settings"]["mode"] = "auto" if len(profit_levels) > 0 else "disabled"

            # 손절 설정 업데이트 (레벨 개수에 따라 mode 자동 설정)
            if "loss_settings" not in group:
                group["loss_settings"] = {"mode": "auto"}
            group["loss_settings"]["levels"] = loss_levels
            group["loss_settings"]["mode"] = "auto" if len(loss_levels) > 0 else "disabled"

            # 저장
            try:
                self.config_manager.save_config(config)
            except Exception as e:
                self._rollback_reset(reset_backup)
                raise ValueError(f"설정 저장 실패: {e}")

            logger.info(f"✅ 그룹 {self.group_id} 통합 설정 저장 완료")
            if changed_items:
                logger.info(f"🔄 리셋된 항목: {', '.join(changed_items)}")

            # 전략 정보 표시 개선
            mode = autobuy_config.get("mode", "auto")
            if mode == "manual":
                strategy_info = "수동 매수 (Upbit에서 직접 매수)"
            else:
                # Auto 모드일 때 전략 확인
                auto_config = autobuy_config.get("auto_config", {})
                strategy = auto_config.get("strategy", "v4_auto_buy")
                if strategy == "expert":
                    strategy_info = f"Expert 전략 - {auto_config.get('expert_profile', 'N/A')}"
                else:
                    strategy_info = f"V4 전략 - {auto_config.get('investment_style', 'N/A')}"

            # 리셋 정보 추가
            reset_info = ""
            if changed_items:
                reset_info = f"\n\n🔄 리셋된 실행 기록: {', '.join(changed_items)}"

            QMessageBox.information(
                self,
                "저장 완료",
                f"그룹 '{self.group_config.get('name')}' 설정이 저장되었습니다.\n\n"
                f"📊 자동매수: {strategy_info}\n"
                f"📈 DCA: {len(dca_levels)}개 레벨\n"
                f"💰 익절: {len(profit_levels)}개 레벨\n"
                f"🛑 손절: {len(loss_levels)}개 레벨"
                f"{reset_info}"
            )

            # 설정 저장 시그널 발생
            self.settings_saved.emit()

            self.accept()

        except Exception as e:
            logger.error(f"❌ 설정 저장 실패: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "저장 실패",
                f"설정 저장 중 오류가 발생했습니다:\n{e}"
            )

    def _reset_group_levels(self, level_type: str) -> dict:
        """
        해당 그룹의 모든 포지션에서 레벨 실행 기록 리셋

        Args:
            level_type: "dca", "profit", "loss"

        Returns:
            롤백용 백업 데이터 {symbol: {field: value, ...}}
        """
        field_name = f"{level_type}_levels_executed"
        backup = {}

        positions = self.position_manager.get_active_positions()

        for symbol, position in positions.items():
            if position.get("group_id") == self.group_id:
                # 백업
                backup[symbol] = {
                    field_name: position.get(field_name, []).copy()
                }

                # 리셋할 필드
                reset_fields = {field_name: []}

                # DCA의 경우 dca_count도 함께 리셋
                if level_type == "dca":
                    backup[symbol]["dca_count"] = position.get("dca_count", 0)
                    reset_fields["dca_count"] = 0

                # 리셋
                self.position_manager.update_position(symbol, reset_fields)

        logger.info(f"🔄 그룹 {self.group_id}의 {level_type} 레벨 실행 기록 리셋 ({len(backup)}개 포지션)")
        return backup

    def _rollback_reset(self, reset_backup: dict):
        """
        리셋 롤백 (실패 시 원복)

        Args:
            reset_backup: {level_type: {symbol: {field: value, ...}}}
        """
        if not self.position_manager:
            return

        for level_type, positions_backup in reset_backup.items():
            for symbol, fields_backup in positions_backup.items():
                try:
                    # 백업된 모든 필드 복원
                    self.position_manager.update_position(symbol, fields_backup)
                except Exception as e:
                    logger.error(f"❌ 롤백 실패 {symbol}: {e}")


if __name__ == "__main__":
    """테스트 코드"""
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # 테스트용 다이얼로그
    dialog = GroupUnifiedSettingsDialog(group_id="group_1")
    dialog.exec()

    sys.exit(app.exec())
