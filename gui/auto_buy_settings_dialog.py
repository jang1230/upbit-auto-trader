"""
AutoBuySettingsDialog - 자동매수 설정 다이얼로그
투자 스타일 선택 및 지표 파라미터 설정
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLabel, QSpinBox, QDoubleSpinBox,
    QGroupBox, QCheckBox, QRadioButton, QButtonGroup,
    QComboBox, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
import logging

logger = logging.getLogger(__name__)


class AutoBuySettingsDialog(QDialog):
    """자동매수 설정 다이얼로그"""

    def __init__(self, config: dict = None, parent=None):
        """
        Args:
            config: 자동매수 설정 딕셔너리
            parent: 부모 위젯
        """
        super().__init__(parent)

        self.config = config or self._get_default_config()

        self.setWindowTitle("⚙️ 자동매수 설정")
        self.setMinimumWidth(700)
        self.setMinimumHeight(600)

        self._init_ui()
        self._load_config()

    def _get_default_config(self) -> dict:
        """
        기본 설정 반환 (balanced 프리셋)

        Returns:
            기본 자동매수 설정 딕셔너리
        """
        return {
            "enabled": True,
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

        # 1. 투자 스타일 선택 그룹
        style_group = self._create_investment_style_group()
        layout.addWidget(style_group)

        # TODO: Step 3에서 추가
        # 2. 지표 설정 그룹

        # TODO: Step 4에서 추가
        # 3. 매수 금액 그룹
        # 4. 버튼

        self.setLayout(layout)

    def _create_investment_style_group(self) -> QGroupBox:
        """
        투자 스타일 선택 그룹 생성

        Returns:
            투자 스타일 선택 QGroupBox
        """
        group = QGroupBox("📊 투자 스타일")
        group.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        layout = QVBoxLayout()

        # 라디오 버튼 그룹
        self.style_button_group = QButtonGroup()

        # ========================================
        # Conservative 라디오 버튼
        # ========================================
        self.conservative_radio = QRadioButton(
            "🛡️ 보수적 (4시간봉) - 하루 1~5번 신호"
        )
        self.conservative_radio.setFont(QFont("맑은 고딕", 10))
        self.style_button_group.addButton(self.conservative_radio, 0)
        layout.addWidget(self.conservative_radio)

        conservative_desc = QLabel(
            "   • 장기 추세 확인, 낮은 변동성\n"
            "   • 안정적이지만 기회가 적음"
        )
        conservative_desc.setFont(QFont("맑은 고딕", 8))
        conservative_desc.setStyleSheet("color: #666; margin-left: 20px;")
        layout.addWidget(conservative_desc)

        # ========================================
        # Balanced 라디오 버튼 (기본 추천)
        # ========================================
        self.balanced_radio = QRadioButton(
            "⚖️ 균형형 (1시간봉) - 하루 5~15번 신호 ⭐ 추천"
        )
        self.balanced_radio.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        self.balanced_radio.setStyleSheet("color: #2196F3;")
        self.style_button_group.addButton(self.balanced_radio, 1)
        layout.addWidget(self.balanced_radio)

        balanced_desc = QLabel(
            "   • 중기 추세 + 단기 모멘텀\n"
            "   • 안정성과 수익성의 균형 ⭐ 대부분의 경우 권장"
        )
        balanced_desc.setFont(QFont("맑은 고딕", 8))
        balanced_desc.setStyleSheet("color: #666; margin-left: 20px;")
        layout.addWidget(balanced_desc)

        # ========================================
        # Aggressive 라디오 버튼
        # ========================================
        self.aggressive_radio = QRadioButton(
            "🔥 적극적 (15분봉) - 하루 15~30번 신호"
        )
        self.aggressive_radio.setFont(QFont("맑은 고딕", 10))
        self.style_button_group.addButton(self.aggressive_radio, 2)
        layout.addWidget(self.aggressive_radio)

        aggressive_desc = QLabel(
            "   • 단기 급등 포착, 높은 변동성\n"
            "   • 수익 기회 많지만 위험도 높음 ⚠️"
        )
        aggressive_desc.setFont(QFont("맑은 고딕", 8))
        aggressive_desc.setStyleSheet("color: #666; margin-left: 20px;")
        layout.addWidget(aggressive_desc)

        # ========================================
        # Custom 라디오 버튼
        # ========================================
        self.custom_radio = QRadioButton(
            "🔧 커스텀 (고급 사용자)"
        )
        self.custom_radio.setFont(QFont("맑은 고딕", 10))
        self.style_button_group.addButton(self.custom_radio, 3)
        layout.addWidget(self.custom_radio)

        custom_desc = QLabel(
            "   • 아래 지표를 직접 설정합니다"
        )
        custom_desc.setFont(QFont("맑은 고딕", 8))
        custom_desc.setStyleSheet("color: #666; margin-left: 20px;")
        layout.addWidget(custom_desc)

        # 라디오 버튼 변경 시 지표 활성화/비활성화
        self.style_button_group.buttonClicked.connect(self._on_style_changed)

        # 기본값: Balanced 선택
        self.balanced_radio.setChecked(True)

        group.setLayout(layout)
        return group

    def _on_style_changed(self, button):
        """
        투자 스타일 변경 시 처리

        Args:
            button: 클릭된 라디오 버튼
        """
        # TODO: Step 5에서 구현 (프리셋 적용 로직)
        style_id = self.style_button_group.id(button)
        logger.info(f"투자 스타일 변경: {style_id} (0=보수적, 1=균형형, 2=적극적, 3=커스텀)")

    def _load_config(self):
        """설정 로드"""
        # TODO: Step 6에서 구현
        logger.info("설정 로드 준비 완료 (Step 6에서 구현 예정)")

    def get_config(self) -> dict:
        """
        현재 설정 반환

        Returns:
            자동매수 설정 딕셔너리
        """
        return self.config
