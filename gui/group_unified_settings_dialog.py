"""
GroupUnifiedSettingsDialog - 그룹 통합 설정 다이얼로그

자동매수, DCA, 익절/손절 설정을 탭으로 통합
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QPushButton, QWidget, QLabel, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
import logging

from core.config_manager import ConfigManager

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

        # 탭2: DCA 레벨
        self.tab2_widget = self._create_tab2_dca()
        self.tab_widget.addTab(self.tab2_widget, "📈 DCA 레벨")

        # 탭3: 익절/손절
        self.tab3_widget = self._create_tab3_profit_loss()
        self.tab_widget.addTab(self.tab3_widget, "💰 익절/손절")

        layout.addWidget(self.tab_widget)

        # 하단 버튼
        button_layout = self._create_button_layout()
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def _create_tab1_autobuy(self) -> QWidget:
        """탭1: 자동매수 전략 (임시 빈 위젯)"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        label = QLabel("📊 자동매수 전략 설정")
        label.setFont(QFont("맑은 고딕", 12, QFont.Bold))
        label.setAlignment(Qt.AlignCenter)

        placeholder = QLabel("(Step 2에서 구현 예정)")
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setStyleSheet("color: gray;")

        layout.addStretch()
        layout.addWidget(label)
        layout.addSpacing(20)
        layout.addWidget(placeholder)
        layout.addStretch()

        return widget

    def _create_tab2_dca(self) -> QWidget:
        """탭2: DCA 레벨 (임시 빈 위젯)"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        label = QLabel("📈 DCA 레벨 설정")
        label.setFont(QFont("맑은 고딕", 12, QFont.Bold))
        label.setAlignment(Qt.AlignCenter)

        placeholder = QLabel("(Step 3에서 구현 예정)")
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setStyleSheet("color: gray;")

        layout.addStretch()
        layout.addWidget(label)
        layout.addSpacing(20)
        layout.addWidget(placeholder)
        layout.addStretch()

        return widget

    def _create_tab3_profit_loss(self) -> QWidget:
        """탭3: 익절/손절 (임시 빈 위젯)"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        label = QLabel("💰 익절/손절 설정")
        label.setFont(QFont("맑은 고딕", 12, QFont.Bold))
        label.setAlignment(Qt.AlignCenter)

        placeholder = QLabel("(Step 4에서 구현 예정)")
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setStyleSheet("color: gray;")

        layout.addStretch()
        layout.addWidget(label)
        layout.addSpacing(20)
        layout.addWidget(placeholder)
        layout.addStretch()

        return widget

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

            # TODO: Step 5에서 구현
            # - 탭1: 자동매수 설정 수집
            # - 탭2: DCA 설정 수집
            # - 탭3: 익절/손절 설정 수집
            # - ConfigManager.update_group() 호출

            QMessageBox.information(
                self,
                "저장 완료",
                f"그룹 '{self.group_config.get('name')}' 설정이 저장되었습니다.\n"
                f"(Step 5에서 실제 저장 로직 구현 예정)"
            )

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
