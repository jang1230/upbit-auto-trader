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

        # TODO: Step 2에서 추가할 내용
        # 1. 투자 스타일 선택 그룹
        # 2. 지표 설정 그룹
        # 3. 매수 금액 그룹
        # 4. 버튼

        # 임시 라벨 (다음 단계에서 제거)
        temp_label = QLabel("Step 1 완료: 기본 구조 생성됨\n다음 단계에서 UI 추가 예정")
        temp_label.setFont(QFont("맑은 고딕", 12))
        temp_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(temp_label)

        self.setLayout(layout)

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
