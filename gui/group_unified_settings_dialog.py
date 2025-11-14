"""
GroupUnifiedSettingsDialog - 그룹 통합 설정 다이얼로그

자동매수, DCA, 익절/손절 설정을 탭으로 통합
"""

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

    def __init__(self, group_id: str, parent=None):
        """
        Args:
            group_id: 그룹 ID
            parent: 부모 위젯
        """
        super().__init__(parent)

        self.group_id = group_id
        self.config_manager = ConfigManager()

        # 설정 로드
        self.group_config = self._load_group_config()

        self.setWindowTitle(f"⚙️ 그룹 설정: {self.group_config.get('name', group_id)}")
        self.setMinimumWidth(800)
        self.setMinimumHeight(700)

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
        # 자동매수 설정 추출
        buy_settings = self.group_config.get('buy_settings', {})
        auto_config = buy_settings.get('auto_config', {})

        # AutoBuySettingsDialogV2를 위젯으로 사용
        autobuy_dialog = AutoBuySettingsDialogV2(config=auto_config.copy(), parent=self)

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

            # 자동매수 설정 업데이트
            # autobuy_config는 이미 전체 buy_settings 구조 (mode, buy_amount_krw, auto_config)를 포함
            group["buy_settings"] = autobuy_config

            # DCA 설정 업데이트
            if "dca_settings" not in group:
                group["dca_settings"] = {"mode": "auto"}
            group["dca_settings"]["levels"] = dca_levels

            # 익절 설정 업데이트
            if "profit_settings" not in group:
                group["profit_settings"] = {"mode": "auto"}
            group["profit_settings"]["levels"] = profit_levels

            # 손절 설정 업데이트
            if "loss_settings" not in group:
                group["loss_settings"] = {"mode": "auto"}
            group["loss_settings"]["levels"] = loss_levels

            # 저장
            self.config_manager.save_config(config)

            logger.info(f"✅ 그룹 {self.group_id} 통합 설정 저장 완료")

            # 전략 정보 표시 개선
            strategy = autobuy_config.get("strategy")
            if strategy == "expert":
                strategy_info = f"Expert 전략 - {autobuy_config.get('expert_profile', 'N/A')}"
            else:
                strategy_info = f"V4 전략 - {autobuy_config.get('investment_style', 'N/A')}"

            QMessageBox.information(
                self,
                "저장 완료",
                f"그룹 '{self.group_config.get('name')}' 설정이 저장되었습니다.\n\n"
                f"📊 자동매수: {strategy_info}\n"
                f"📈 DCA: {len(dca_levels)}개 레벨\n"
                f"💰 익절: {len(profit_levels)}개 레벨\n"
                f"🛑 손절: {len(loss_levels)}개 레벨"
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


if __name__ == "__main__":
    """테스트 코드"""
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # 테스트용 다이얼로그
    dialog = GroupUnifiedSettingsDialog(group_id="group_1")
    dialog.exec()

    sys.exit(app.exec())
