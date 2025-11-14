"""
V4CustomSettingsDialog - V4 Custom 투자 스타일 고급 설정 다이얼로그

V4 전략 Custom 선택 시 표시되는 상세 설정:
- RSI 설정 (기간, 과매도, 과매수)
- MACD 설정 (Fast, Slow, Signal)
- Volume 설정 (기간, 임계값)
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QSpinBox, QDoubleSpinBox, QPushButton, QGroupBox,
    QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
import logging

logger = logging.getLogger(__name__)


class V4CustomSettingsDialog(QDialog):
    """V4 Custom 투자 스타일 고급 설정 다이얼로그"""

    def __init__(self, config: dict = None, parent=None):
        """
        Args:
            config: V4 auto_config 딕셔너리
                {
                    "indicators": {
                        "rsi": {...},
                        "macd": {...},
                        "volume": {...}
                    }
                }
            parent: 부모 위젯
        """
        super().__init__(parent)

        self.config = config or self._get_default_config()

        self.setWindowTitle("🔧 V4 Custom 전략 고급 설정")
        self.setMinimumWidth(500)
        self.setMinimumHeight(550)

        self._init_ui()
        self._load_config()

    def _get_default_config(self) -> dict:
        """기본 설정 반환"""
        return {
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
            }
        }

    def _init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # 안내 문구
        info_label = QLabel(
            "ℹ️ Custom 투자 스타일의 지표 상세 설정을 조정합니다.\n"
            "   각 지표의 파라미터를 변경하여 자신만의 전략을 만드세요."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("""
            QLabel {
                padding: 10px;
                background-color: #E3F2FD;
                border-radius: 5px;
                font-size: 10pt;
            }
        """)
        layout.addWidget(info_label)

        # 1. RSI 설정
        rsi_group = self._create_rsi_section()
        layout.addWidget(rsi_group)

        # 2. MACD 설정
        macd_group = self._create_macd_section()
        layout.addWidget(macd_group)

        # 3. Volume 설정
        volume_group = self._create_volume_section()
        layout.addWidget(volume_group)

        layout.addStretch()

        # 버튼
        button_layout = self._create_button_layout()
        layout.addLayout(button_layout)

    def _create_rsi_section(self) -> QGroupBox:
        """RSI 설정 섹션"""
        group = QGroupBox("📊 RSI (상대강도지수)")
        group.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        layout = QFormLayout()

        # 기간
        self.rsi_period_spin = QSpinBox()
        self.rsi_period_spin.setRange(5, 30)
        self.rsi_period_spin.setValue(14)
        self.rsi_period_spin.setSuffix(" 기간")
        layout.addRow("📈 기간:", self.rsi_period_spin)

        # 과매도
        self.rsi_oversold_spin = QSpinBox()
        self.rsi_oversold_spin.setRange(10, 40)
        self.rsi_oversold_spin.setValue(30)
        layout.addRow("📉 과매도 기준:", self.rsi_oversold_spin)

        # 과매수
        self.rsi_overbought_spin = QSpinBox()
        self.rsi_overbought_spin.setRange(60, 90)
        self.rsi_overbought_spin.setValue(70)
        layout.addRow("📈 과매수 기준:", self.rsi_overbought_spin)

        # 설명
        desc = QLabel("💡 RSI가 과매도 기준 아래로 떨어지면 매수 신호")
        desc.setStyleSheet("color: #666; font-size: 9pt;")
        layout.addRow("", desc)

        group.setLayout(layout)
        return group

    def _create_macd_section(self) -> QGroupBox:
        """MACD 설정 섹션"""
        group = QGroupBox("📈 MACD (이동평균 수렴/확산)")
        group.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        layout = QFormLayout()

        # Fast
        self.macd_fast_spin = QSpinBox()
        self.macd_fast_spin.setRange(5, 20)
        self.macd_fast_spin.setValue(12)
        self.macd_fast_spin.setSuffix(" 기간")
        layout.addRow("⚡ Fast (빠른 이평):", self.macd_fast_spin)

        # Slow
        self.macd_slow_spin = QSpinBox()
        self.macd_slow_spin.setRange(15, 40)
        self.macd_slow_spin.setValue(26)
        self.macd_slow_spin.setSuffix(" 기간")
        layout.addRow("🐢 Slow (느린 이평):", self.macd_slow_spin)

        # Signal
        self.macd_signal_spin = QSpinBox()
        self.macd_signal_spin.setRange(5, 15)
        self.macd_signal_spin.setValue(9)
        self.macd_signal_spin.setSuffix(" 기간")
        layout.addRow("📡 Signal:", self.macd_signal_spin)

        # 설명
        desc = QLabel("💡 MACD 골든크로스(상승 교차) 시 매수 신호")
        desc.setStyleSheet("color: #666; font-size: 9pt;")
        layout.addRow("", desc)

        group.setLayout(layout)
        return group

    def _create_volume_section(self) -> QGroupBox:
        """Volume 설정 섹션"""
        group = QGroupBox("📊 Volume (거래량)")
        group.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        layout = QFormLayout()

        # 기간
        self.volume_period_spin = QSpinBox()
        self.volume_period_spin.setRange(10, 50)
        self.volume_period_spin.setValue(20)
        self.volume_period_spin.setSuffix(" 기간")
        layout.addRow("📈 평균 기간:", self.volume_period_spin)

        # 임계값
        self.volume_threshold_spin = QDoubleSpinBox()
        self.volume_threshold_spin.setRange(1.0, 5.0)
        self.volume_threshold_spin.setSingleStep(0.1)
        self.volume_threshold_spin.setDecimals(1)
        self.volume_threshold_spin.setValue(2.0)
        self.volume_threshold_spin.setSuffix(" 배")
        layout.addRow("🔥 급증 임계값:", self.volume_threshold_spin)

        # 설명
        desc = QLabel("💡 평균 거래량의 N배 이상일 때 급증으로 판단")
        desc.setStyleSheet("color: #666; font-size: 9pt;")
        layout.addRow("", desc)

        group.setLayout(layout)
        return group

    def _create_button_layout(self) -> QHBoxLayout:
        """버튼 레이아웃"""
        layout = QHBoxLayout()

        # 기본값 복원 버튼
        reset_btn = QPushButton("🔄 기본값 복원")
        reset_btn.clicked.connect(self._reset_to_defaults)
        layout.addWidget(reset_btn)

        layout.addStretch()

        # 취소 버튼
        cancel_btn = QPushButton("취소")
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)

        # 확인 버튼
        ok_btn = QPushButton("확인")
        ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        ok_btn.clicked.connect(self._on_ok_clicked)
        layout.addWidget(ok_btn)

        return layout

    def _load_config(self):
        """설정 로드"""
        indicators = self.config.get("indicators", {})

        # RSI
        rsi = indicators.get("rsi", {})
        self.rsi_period_spin.setValue(rsi.get("period", 14))
        self.rsi_oversold_spin.setValue(rsi.get("oversold", 30))
        self.rsi_overbought_spin.setValue(rsi.get("overbought", 70))

        # MACD
        macd = indicators.get("macd", {})
        self.macd_fast_spin.setValue(macd.get("fast", 12))
        self.macd_slow_spin.setValue(macd.get("slow", 26))
        self.macd_signal_spin.setValue(macd.get("signal", 9))

        # Volume
        volume = indicators.get("volume", {})
        self.volume_period_spin.setValue(volume.get("period", 20))
        self.volume_threshold_spin.setValue(volume.get("threshold", 2.0))

    def _reset_to_defaults(self):
        """기본값으로 복원"""
        reply = QMessageBox.question(
            self,
            "기본값 복원",
            "모든 설정을 기본값으로 복원하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # 기본값 설정
            self.rsi_period_spin.setValue(14)
            self.rsi_oversold_spin.setValue(30)
            self.rsi_overbought_spin.setValue(70)

            self.macd_fast_spin.setValue(12)
            self.macd_slow_spin.setValue(26)
            self.macd_signal_spin.setValue(9)

            self.volume_period_spin.setValue(20)
            self.volume_threshold_spin.setValue(2.0)

            QMessageBox.information(self, "완료", "기본값으로 복원되었습니다.")

    def _on_ok_clicked(self):
        """확인 버튼 클릭"""
        # 검증
        if not self._validate_inputs():
            return

        self.accept()

    def _validate_inputs(self) -> bool:
        """입력 검증"""
        # RSI 검증
        if self.rsi_oversold_spin.value() >= self.rsi_overbought_spin.value():
            QMessageBox.warning(
                self,
                "입력 오류",
                "RSI 과매도 기준은 과매수 기준보다 낮아야 합니다."
            )
            return False

        # MACD 검증
        if self.macd_fast_spin.value() >= self.macd_slow_spin.value():
            QMessageBox.warning(
                self,
                "입력 오류",
                "MACD Fast는 Slow보다 작아야 합니다."
            )
            return False

        return True

    def get_config(self) -> dict:
        """현재 설정 반환"""
        return {
            "indicators": {
                "rsi": {
                    "enabled": True,
                    "period": self.rsi_period_spin.value(),
                    "oversold": self.rsi_oversold_spin.value(),
                    "overbought": self.rsi_overbought_spin.value()
                },
                "macd": {
                    "enabled": True,
                    "fast": self.macd_fast_spin.value(),
                    "slow": self.macd_slow_spin.value(),
                    "signal": self.macd_signal_spin.value()
                },
                "volume": {
                    "enabled": True,
                    "period": self.volume_period_spin.value(),
                    "threshold": self.volume_threshold_spin.value()
                }
            }
        }
