"""
AutoBuySettingsDialogV2 - 자동매수 설정 다이얼로그 (V4 + Expert 탭 통합)

V4 전략과 Expert 전략을 탭으로 선택할 수 있는 통합 다이얼로그
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QPushButton, QTabWidget, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
import logging

# 기존 V4 다이얼로그와 Expert 위젯 임포트
from gui.auto_buy_settings_dialog import AutoBuySettingsDialog
from gui.expert_strategy_widget import ExpertStrategyWidget

logger = logging.getLogger(__name__)


class AutoBuySettingsDialogV2(QDialog):
    """
    자동매수 설정 다이얼로그 V2

    V4 전략과 Expert 전략을 탭으로 선택
    """

    def __init__(self, config: dict = None, parent=None):
        """
        Args:
            config: 자동매수 설정 딕셔너리
            parent: 부모 위젯
        """
        super().__init__(parent)

        self.config = config or self._get_default_config()

        self.setWindowTitle("⚙️ 자동매수 전략 설정")
        self.setMinimumWidth(750)
        self.setMinimumHeight(700)

        self._init_ui()
        self._load_config()

    def _get_default_config(self) -> dict:
        """기본 설정 반환 (V4 balanced)"""
        return {
            "enabled": True,
            "strategy": "v4_auto_buy",  # 기본값: V4 전략
            "investment_style": "balanced",
            "candle_unit": "60",
            "indicators": {
                "rsi": {
                    "enabled": True,
                    "period": 14,
                    "oversold": 30,
                    "overbought": 70
                },
                "macd": {
                    "enabled": True,
                    "fast": 12,
                    "slow": 26,
                    "signal": 9
                },
                "volume": {
                    "enabled": True,
                    "period": 20,
                    "threshold": 2.0
                }
            },
            "buy_amount_krw": 50000
        }

    def _init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # 탭 위젯 생성
        self.tab_widget = QTabWidget()
        self.tab_widget.setFont(QFont("맑은 고딕", 10))

        # Tab 1: V4 전략 (기존 AutoBuySettingsDialog의 내용 활용)
        self.v4_widget = self._create_v4_tab()
        self.tab_widget.addTab(self.v4_widget, "📊 V4 전략 (3개 지표)")

        # Tab 2: Expert 전략
        expert_config = self.config if self.config.get("strategy") == "expert" else None
        self.expert_widget = ExpertStrategyWidget(expert_config, self)
        self.tab_widget.addTab(self.expert_widget, "🎯 Expert 전략 (5개 지표)")

        layout.addWidget(self.tab_widget)

        # 버튼
        button_layout = self._create_button_layout()
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def _create_v4_tab(self):
        """V4 탭 생성 (기존 AutoBuySettingsDialog 재사용)"""
        # 기존 AutoBuySettingsDialog를 위젯으로 사용
        # 단, 부모 다이얼로그의 버튼을 사용하므로 내부 버튼은 숨김
        v4_config = self.config if self.config.get("strategy") in [None, "v4_auto_buy"] else None
        v4_dialog = AutoBuySettingsDialog(v4_config, self)

        # 다이얼로그를 위젯처럼 사용하기 위해 윈도우 플래그 제거
        v4_dialog.setWindowFlags(Qt.Widget)

        # 내부 버튼 레이아웃 숨기기 (상위 다이얼로그 버튼 사용)
        # 버튼은 마지막 레이아웃이므로 숨김 처리
        main_layout = v4_dialog.layout()
        if main_layout and main_layout.count() > 0:
            last_item = main_layout.itemAt(main_layout.count() - 1)
            if last_item and last_item.layout():
                # 버튼 레이아웃 숨김
                button_layout = last_item.layout()
                for i in range(button_layout.count()):
                    widget = button_layout.itemAt(i).widget()
                    if widget:
                        widget.setVisible(False)

        return v4_dialog

    def _create_button_layout(self) -> QHBoxLayout:
        """버튼 레이아웃 생성"""
        layout = QHBoxLayout()
        layout.addStretch()

        # 취소 버튼
        cancel_btn = QPushButton("취소")
        cancel_btn.setFont(QFont("맑은 고딕", 10))
        cancel_btn.setFixedWidth(100)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)

        # 저장 버튼
        save_btn = QPushButton("저장")
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
            # 현재 선택된 탭에 따라 설정 저장
            current_index = self.tab_widget.currentIndex()

            if current_index == 0:
                # V4 탭: V4 전용 필드만 추출
                v4_config = self.v4_widget.get_config()

                # V4 전용 필드만 명시적으로 구성 (Expert 필드 제거)
                self.config = {
                    "enabled": v4_config.get("enabled", True),
                    "strategy": "v4_auto_buy",
                    "investment_style": v4_config.get("investment_style"),
                    "candle_unit": v4_config.get("candle_unit"),
                    "indicators": v4_config.get("indicators"),
                    "buy_amount_krw": v4_config.get("buy_amount_krw")
                }

                logger.info(f"✅ V4 전략 설정 저장: {self.config.get('investment_style')}")

            else:
                # Expert 탭: Expert 전용 필드만 추출
                expert_config = self.expert_widget.get_config()

                # Expert 전용 필드만 명시적으로 구성 (V4 필드 제거)
                self.config = {
                    "enabled": True,
                    "strategy": "expert",
                    "expert_profile": expert_config.get("expert_profile"),
                    "candle_unit": expert_config.get("candle_unit"),
                    "buy_amount_krw": self.config.get("buy_amount_krw", 50000)
                }

                # custom 프로필인 경우 가중치 정보 추가
                if expert_config.get("expert_profile") == "custom":
                    self.config["custom_weights"] = expert_config.get("custom_weights")
                    self.config["custom_threshold"] = expert_config.get("custom_threshold")

                profile = expert_config.get("expert_profile")
                logger.info(f"✅ Expert 전략 설정 저장: {profile}")

            self.accept()

        except Exception as e:
            logger.error(f"❌ 설정 저장 실패: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "저장 실패",
                f"설정 저장 중 오류가 발생했습니다:\n{e}"
            )

    def _load_config(self):
        """설정 로드 및 탭 선택"""
        try:
            strategy = self.config.get("strategy", "v4_auto_buy")

            if strategy == "expert":
                # Expert 탭으로 전환
                self.tab_widget.setCurrentIndex(1)
                logger.info("Expert 전략 탭으로 전환")
            else:
                # V4 탭으로 전환 (기본값)
                self.tab_widget.setCurrentIndex(0)
                logger.info("V4 전략 탭으로 전환")

        except Exception as e:
            logger.error(f"설정 로드 중 오류: {e}")
            # 기본값으로 V4 탭 선택
            self.tab_widget.setCurrentIndex(0)

    def get_config(self) -> dict:
        """
        현재 설정 반환

        Returns:
            현재 선택된 탭의 설정 딕셔너리
        """
        return self.config
