"""
AutoBuySettingsDialogV2 - 자동매수 설정 다이얼로그 (V4 + Expert 라디오 버튼 통합)

V4 전략과 Expert 전략을 라디오 버튼으로 선택
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
    QPushButton, QRadioButton, QStackedWidget, QLabel, QMessageBox,
    QScrollArea, QSpinBox
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

    V4 전략과 Expert 전략을 라디오 버튼으로 선택
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
        self.setMinimumHeight(600)
        self.setMaximumHeight(650)

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
        """UI 초기화 - 라디오 버튼 + 스택 위젯 구조"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)

        # === 1. 전략 선택 영역 (라디오 버튼) ===
        strategy_group = QGroupBox("📊 자동매수 전략 선택")
        strategy_group.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        strategy_layout = QVBoxLayout()

        # V4 라디오 버튼
        self.v4_radio = QRadioButton("📊 V4 전략 (3개 지표 - RSI, MACD, Volume)")
        self.v4_radio.setFont(QFont("맑은 고딕", 10))
        self.v4_radio.setStyleSheet("""
            QRadioButton {
                padding: 8px;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
            }
        """)
        strategy_layout.addWidget(self.v4_radio)

        # V4 설명
        v4_desc = QLabel("   ↳ 프리셋 기반 전략 (Conservative / Balanced / Aggressive)")
        v4_desc.setFont(QFont("맑은 고딕", 9))
        v4_desc.setStyleSheet("color: #666; padding-left: 30px;")
        strategy_layout.addWidget(v4_desc)

        strategy_layout.addSpacing(10)

        # Expert 라디오 버튼
        self.expert_radio = QRadioButton("🎯 Expert 전략 (5개 지표 - 종합 스코어링)")
        self.expert_radio.setFont(QFont("맑은 고딕", 10))
        self.expert_radio.setStyleSheet("""
            QRadioButton {
                padding: 8px;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
            }
        """)
        strategy_layout.addWidget(self.expert_radio)

        # Expert 설명
        expert_desc = QLabel("   ↳ 10개 전문가 프로필 + Custom 가중치 설정")
        expert_desc.setFont(QFont("맑은 고딕", 9))
        expert_desc.setStyleSheet("color: #666; padding-left: 30px;")
        strategy_layout.addWidget(expert_desc)

        strategy_group.setLayout(strategy_layout)
        main_layout.addWidget(strategy_group)

        # 라디오 버튼 이벤트 연결
        self.v4_radio.toggled.connect(self._on_strategy_changed)
        self.expert_radio.toggled.connect(self._on_strategy_changed)

        # === 2. 매수 금액 설정 (공통) ===
        buy_amount_group = self._create_buy_amount_group()
        main_layout.addWidget(buy_amount_group)

        # === 3. 설정 폼 영역 (스택 위젯 + 스크롤) ===
        self.stack_widget = QStackedWidget()

        # V4 위젯 (index 0)
        self.v4_widget = self._create_v4_widget()
        self.stack_widget.addWidget(self.v4_widget)

        # Expert 위젯 (index 1)
        self.expert_widget = self._create_expert_widget()
        self.stack_widget.addWidget(self.expert_widget)

        # 스크롤 영역으로 감싸기
        scroll_area = QScrollArea()
        scroll_area.setWidget(self.stack_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QScrollArea.NoFrame)  # 테두리 제거

        main_layout.addWidget(scroll_area, 1)  # stretch factor = 1

        # === 4. 버튼 영역 ===
        button_layout = self._create_button_layout()
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

    def _create_buy_amount_group(self) -> QGroupBox:
        """
        매수 금액 설정 그룹 생성 (공통)

        Returns:
            매수 금액 설정 QGroupBox
        """
        group = QGroupBox("💰 1회 매수 금액")
        group.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        layout = QFormLayout()

        self.buy_amount_spin = QSpinBox()
        self.buy_amount_spin.setRange(5000, 10000000)
        self.buy_amount_spin.setSingleStep(5000)
        self.buy_amount_spin.setSuffix(" 원")
        self.buy_amount_spin.setFont(QFont("맑은 고딕", 10))
        layout.addRow("매수 금액:", self.buy_amount_spin)

        buy_amount_info = QLabel(
            "자동매수 신호 발생 시 1회 매수할 금액입니다 (V4/Expert 전략 공통 적용)"
        )
        buy_amount_info.setStyleSheet("color: #666; font-size: 9px;")
        buy_amount_info.setWordWrap(True)
        layout.addRow("", buy_amount_info)

        group.setLayout(layout)
        return group

    def _create_v4_widget(self):
        """V4 설정 위젯 생성"""
        v4_config = self.config if self.config.get("strategy") in [None, "v4_auto_buy"] else None
        v4_dialog = AutoBuySettingsDialog(v4_config, self)

        # 다이얼로그를 위젯처럼 사용
        v4_dialog.setWindowFlags(Qt.Widget)

        # 내부 버튼 및 매수금액 그룹 숨기기
        main_layout = v4_dialog.layout()
        if main_layout and main_layout.count() > 0:
            # 마지막 아이템 (버튼 레이아웃) 숨기기
            last_item = main_layout.itemAt(main_layout.count() - 1)
            if last_item and last_item.layout():
                button_layout = last_item.layout()
                for i in range(button_layout.count()):
                    widget = button_layout.itemAt(i).widget()
                    if widget:
                        widget.setVisible(False)

            # 마지막에서 두 번째 아이템 (매수금액 그룹) 숨기기
            if main_layout.count() > 1:
                buy_amount_item = main_layout.itemAt(main_layout.count() - 2)
                if buy_amount_item and buy_amount_item.widget():
                    buy_amount_item.widget().setVisible(False)

        return v4_dialog

    def _create_expert_widget(self):
        """Expert 설정 위젯 생성"""
        expert_config = self.config if self.config.get("strategy") == "expert" else None
        expert_widget = ExpertStrategyWidget(expert_config, self)
        return expert_widget

    def _on_strategy_changed(self):
        """전략 선택 변경 시 호출"""
        if self.v4_radio.isChecked():
            self.stack_widget.setCurrentIndex(0)
            logger.info("✅ V4 전략 선택됨")
        else:
            self.stack_widget.setCurrentIndex(1)
            logger.info("✅ Expert 전략 선택됨")

    def _create_button_layout(self) -> QHBoxLayout:
        """버튼 레이아웃 생성 (임베드 모드에서는 숨김 처리됨)"""
        layout = QHBoxLayout()
        layout.addStretch()

        # 취소 버튼
        cancel_btn = QPushButton("❌ 취소")
        cancel_btn.setFont(QFont("맑은 고딕", 10))
        cancel_btn.setFixedWidth(120)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)

        # 저장 버튼 (독립 실행 시에만 사용, 임베드 시 숨김)
        save_btn = QPushButton("💾 저장")
        save_btn.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        save_btn.setFixedWidth(120)
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
        save_btn.clicked.connect(self.accept)
        layout.addWidget(save_btn)

        return layout

    def _load_config(self):
        """설정 로드 및 라디오 버튼 선택"""
        try:
            strategy = self.config.get("strategy", "v4_auto_buy")

            if strategy == "expert":
                # Expert 라디오 버튼 선택
                self.expert_radio.setChecked(True)
                self.stack_widget.setCurrentIndex(1)
                logger.info("📊 Expert 전략 로드")
            else:
                # V4 라디오 버튼 선택 (기본값)
                self.v4_radio.setChecked(True)
                self.stack_widget.setCurrentIndex(0)
                logger.info("📊 V4 전략 로드")

            # 매수 금액 로드 (공통)
            buy_amount = self.config.get("buy_amount_krw", 50000)
            self.buy_amount_spin.setValue(buy_amount)

        except Exception as e:
            logger.error(f"❌ 설정 로드 실패: {e}")
            # 기본값: V4 선택
            self.v4_radio.setChecked(True)
            self.stack_widget.setCurrentIndex(0)
            self.buy_amount_spin.setValue(50000)

    def get_config(self) -> dict:
        """
        현재 선택된 전략의 설정을 실시간으로 반환

        Returns:
            현재 선택된 전략의 설정 딕셔너리
        """
        try:
            # 공통 매수 금액 (상단 필드에서 가져오기)
            buy_amount = self.buy_amount_spin.value()

            if self.v4_radio.isChecked():
                # V4 전략 선택됨
                v4_config = self.v4_widget.get_config()

                result = {
                    "enabled": v4_config.get("enabled", True),
                    "strategy": "v4_auto_buy",
                    "investment_style": v4_config.get("investment_style"),
                    "candle_unit": v4_config.get("candle_unit"),
                    "indicators": v4_config.get("indicators"),
                    "buy_amount_krw": buy_amount  # 공통 필드 사용
                }

                logger.info(f"📊 V4 설정 반환: {result.get('investment_style')}, 매수금액: {buy_amount:,}원")
                return result

            else:
                # Expert 전략 선택됨
                expert_config = self.expert_widget.get_config()

                result = {
                    "enabled": True,
                    "strategy": "expert",
                    "expert_profile": expert_config.get("expert_profile"),
                    "candle_unit": expert_config.get("candle_unit"),
                    "buy_amount_krw": buy_amount  # 공통 필드 사용
                }

                # Custom 프로필인 경우 가중치 추가
                if expert_config.get("expert_profile") == "custom":
                    result["custom_weights"] = expert_config.get("custom_weights")
                    result["custom_threshold"] = expert_config.get("custom_threshold")

                logger.info(f"🎯 Expert 설정 반환: {result.get('expert_profile')}, 매수금액: {buy_amount:,}원")
                return result

        except Exception as e:
            logger.error(f"❌ get_config() 실패: {e}", exc_info=True)
            # 기본값 반환
            return self._get_default_config()


if __name__ == "__main__":
    """독립 실행 테스트"""
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # 테스트용 config
    test_config = {
        "strategy": "v4_auto_buy",
        "investment_style": "balanced",
        "candle_unit": "60",
        "indicators": {
            "rsi": {"enabled": True, "period": 14, "oversold": 30, "overbought": 70},
            "macd": {"enabled": True, "fast": 12, "slow": 26, "signal": 9},
            "volume": {"enabled": True, "period": 20, "threshold": 2.0}
        },
        "buy_amount_krw": 50000
    }

    dialog = AutoBuySettingsDialogV2(test_config)

    if dialog.exec():
        final_config = dialog.get_config()
        print("\n=== 최종 설정 ===")
        print(f"전략: {final_config.get('strategy')}")
        if final_config.get('strategy') == 'expert':
            print(f"프로필: {final_config.get('expert_profile')}")
        else:
            print(f"스타일: {final_config.get('investment_style')}")

    sys.exit(app.exec())
