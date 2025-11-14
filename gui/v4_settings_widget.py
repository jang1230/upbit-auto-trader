"""
V4SettingsWidget - V4 자동매수 설정 위젯 (순수 QWidget)

AutoBuySettingsDialog에서 UI 부분만 추출하여 QWidget으로 재작성
QDialog 스타일 충돌 문제 해결을 위해 작성됨
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLabel, QSpinBox, QDoubleSpinBox,
    QGroupBox, QCheckBox, QRadioButton, QButtonGroup
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
import logging

from gui.v4_custom_settings_dialog import V4CustomSettingsDialog

logger = logging.getLogger(__name__)


class V4SettingsWidget(QWidget):
    """V4 자동매수 설정 위젯 (순수 QWidget)"""

    def __init__(self, config: dict = None, parent=None):
        """
        Args:
            config: 자동매수 설정 딕셔너리
            parent: 부모 위젯
        """
        super().__init__(parent)

        self.config = config or self._get_default_config()

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
        layout.setContentsMargins(0, 0, 0, 0)  # 부모 레이아웃에 맞춤

        # 1. 투자 스타일 선택 그룹
        style_group = self._create_investment_style_group()
        layout.addWidget(style_group)

        # 2. 지표 설정 그룹
        indicators_group = self._create_indicators_group()
        layout.addWidget(indicators_group)

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
            "   • 지표 상세 설정은 고급 설정 버튼을 눌러주세요"
        )
        custom_desc.setFont(QFont("맑은 고딕", 8))
        custom_desc.setStyleSheet("color: #666; margin-left: 20px;")
        layout.addWidget(custom_desc)

        # 고급 설정 버튼 (Custom 선택 시에만 표시)
        custom_button_container = QHBoxLayout()
        custom_button_container.addSpacing(30)  # 들여쓰기

        self.custom_advanced_button = QPushButton("🔧 고급 설정")
        self.custom_advanced_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 5px 15px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.custom_advanced_button.clicked.connect(self._open_custom_settings_dialog)
        self.custom_advanced_button.setVisible(False)  # 처음엔 숨김

        custom_button_container.addWidget(self.custom_advanced_button)
        custom_button_container.addStretch()
        layout.addLayout(custom_button_container)

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
        style_id = self.style_button_group.id(button)
        logger.info(f"투자 스타일 변경: {style_id} (0=보수적, 1=균형형, 2=적극적, 3=커스텀)")

        # 프리셋 정의 (v4_auto_buy_strategy.py의 PRESETS와 동일)
        presets = {
            0: {  # Conservative
                "rsi": {"enabled": True, "period": 14, "oversold": 30, "overbought": 70},
                "macd": {"enabled": True, "fast": 12, "slow": 26, "signal": 9},
                "volume": {"enabled": True, "period": 20, "threshold": 2.0}
            },
            1: {  # Balanced
                "rsi": {"enabled": True, "period": 14, "oversold": 30, "overbought": 70},
                "macd": {"enabled": True, "fast": 12, "slow": 26, "signal": 9},
                "volume": {"enabled": True, "period": 20, "threshold": 2.0}
            },
            2: {  # Aggressive
                "rsi": {"enabled": True, "period": 14, "oversold": 30, "overbought": 70},
                "macd": {"enabled": True, "fast": 10, "slow": 20, "signal": 7},
                "volume": {"enabled": True, "period": 20, "threshold": 3.0}
            }
        }

        if style_id == 3:  # Custom
            # 커스텀 모드: 고급 설정 버튼 표시, 지표 입력 비활성화
            self.custom_advanced_button.setVisible(True)
            self._set_indicators_enabled(False)  # Custom은 다이얼로그에서 설정
        else:
            # 프리셋 모드: 고급 설정 버튼 숨김, 지표 값 적용 후 비활성화
            self.custom_advanced_button.setVisible(False)
            preset = presets[style_id]
            self._apply_preset(preset)
            self._set_indicators_enabled(False)

    def _open_custom_settings_dialog(self):
        """
        V4 Custom 고급 설정 다이얼로그 열기

        현재 indicators 설정을 전달하고, 사용자가 수정한 값을 받아옴
        """
        try:
            # 현재 indicators 설정 가져오기
            current_indicators = self.config.get("indicators", {})

            # V4CustomSettingsDialog 열기
            from PySide6.QtWidgets import QDialog
            dialog = V4CustomSettingsDialog(
                config={"indicators": current_indicators},
                parent=self
            )

            if dialog.exec() == QDialog.Accepted:
                # 사용자가 확인 버튼 클릭 시 설정 업데이트
                updated_config = dialog.get_config()
                self.config["indicators"] = updated_config["indicators"]

                # UI에도 반영 (미리보기 목적)
                self._apply_preset(updated_config["indicators"])

                logger.info("✅ V4 Custom 설정 업데이트 완료")
            else:
                logger.info("❌ V4 Custom 설정 취소")

        except Exception as e:
            logger.error(f"❌ V4 Custom 설정 다이얼로그 오류: {e}")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "오류",
                f"고급 설정 다이얼로그를 여는 중 오류가 발생했습니다:\n{e}"
            )

    def _apply_preset(self, preset: dict):
        """
        프리셋 값을 UI에 적용

        Args:
            preset: 프리셋 딕셔너리 (rsi, macd, volume)
        """
        # RSI 설정 적용
        rsi = preset.get("rsi", {})
        self.rsi_enabled.setChecked(rsi.get("enabled", True))
        self.rsi_period_spin.setValue(rsi.get("period", 14))
        self.rsi_oversold_spin.setValue(rsi.get("oversold", 30))
        self.rsi_overbought_spin.setValue(rsi.get("overbought", 70))

        # MACD 설정 적용
        macd = preset.get("macd", {})
        self.macd_enabled.setChecked(macd.get("enabled", True))
        self.macd_fast_spin.setValue(macd.get("fast", 12))
        self.macd_slow_spin.setValue(macd.get("slow", 26))
        self.macd_signal_spin.setValue(macd.get("signal", 9))

        # Volume 설정 적용
        volume = preset.get("volume", {})
        self.volume_enabled.setChecked(volume.get("enabled", True))
        self.volume_period_spin.setValue(volume.get("period", 20))
        self.volume_threshold_spin.setValue(volume.get("threshold", 2.0))

    def _set_indicators_enabled(self, enabled: bool):
        """
        지표 입력 필드 활성화/비활성화

        Args:
            enabled: True면 활성화, False면 비활성화
        """
        # RSI
        self.rsi_enabled.setEnabled(enabled)
        self.rsi_period_spin.setEnabled(enabled and self.rsi_enabled.isChecked())
        self.rsi_oversold_spin.setEnabled(enabled and self.rsi_enabled.isChecked())
        self.rsi_overbought_spin.setEnabled(enabled and self.rsi_enabled.isChecked())

        # MACD
        self.macd_enabled.setEnabled(enabled)
        self.macd_fast_spin.setEnabled(enabled and self.macd_enabled.isChecked())
        self.macd_slow_spin.setEnabled(enabled and self.macd_enabled.isChecked())
        self.macd_signal_spin.setEnabled(enabled and self.macd_enabled.isChecked())

        # Volume
        self.volume_enabled.setEnabled(enabled)
        self.volume_period_spin.setEnabled(enabled and self.volume_enabled.isChecked())
        self.volume_threshold_spin.setEnabled(enabled and self.volume_enabled.isChecked())

    def _create_indicators_group(self) -> QGroupBox:
        """
        지표 설정 그룹 생성

        Returns:
            지표 설정 QGroupBox
        """
        group = QGroupBox("📈 지표 설정 (커스텀 모드에서만 수정 가능)")
        group.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        layout = QVBoxLayout()
        layout.setSpacing(15)  # 지표 그룹 간 간격
        layout.setContentsMargins(10, 10, 10, 10)

        # ========================================
        # RSI 지표 설정
        # ========================================
        rsi_group = QGroupBox("📊 RSI (Relative Strength Index)")
        rsi_group.setFont(QFont("맑은 고딕", 9, QFont.Bold))
        rsi_group.setStyleSheet("""
            QGroupBox {
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 15px;
                padding: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                padding: 0 5px;
            }
        """)
        rsi_layout = QVBoxLayout()
        rsi_layout.setContentsMargins(10, 10, 10, 10)
        rsi_layout.setSpacing(10)

        # RSI 활성화 체크박스
        self.rsi_enabled = QCheckBox("RSI 지표 사용")
        self.rsi_enabled.toggled.connect(self._on_rsi_toggled)
        rsi_layout.addWidget(self.rsi_enabled)

        # RSI 파라미터
        rsi_form = QFormLayout()
        rsi_form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        rsi_form.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        rsi_form.setHorizontalSpacing(20)
        rsi_form.setVerticalSpacing(10)

        self.rsi_period_spin = QSpinBox()
        self.rsi_period_spin.setRange(5, 50)
        self.rsi_period_spin.setSuffix(" 기간")
        self.rsi_period_spin.setMinimumWidth(150)
        self.rsi_period_spin.setFont(QFont("맑은 고딕", 10))
        rsi_form.addRow("기간:", self.rsi_period_spin)

        self.rsi_oversold_spin = QSpinBox()
        self.rsi_oversold_spin.setRange(10, 40)
        self.rsi_oversold_spin.setMinimumWidth(150)
        self.rsi_oversold_spin.setFont(QFont("맑은 고딕", 10))
        rsi_form.addRow("과매도 기준:", self.rsi_oversold_spin)

        self.rsi_overbought_spin = QSpinBox()
        self.rsi_overbought_spin.setRange(60, 90)
        self.rsi_overbought_spin.setMinimumWidth(150)
        self.rsi_overbought_spin.setFont(QFont("맑은 고딕", 10))
        rsi_form.addRow("과매수 기준:", self.rsi_overbought_spin)

        rsi_layout.addLayout(rsi_form)

        rsi_info = QLabel("RSI ≤ 과매도 시 매수 신호 발생")
        rsi_info.setStyleSheet("color: #666; font-size: 10px;")
        rsi_layout.addWidget(rsi_info)

        rsi_group.setLayout(rsi_layout)
        layout.addWidget(rsi_group)

        # ========================================
        # MACD 지표 설정
        # ========================================
        macd_group = QGroupBox("📈 MACD (Moving Average Convergence Divergence)")
        macd_group.setFont(QFont("맑은 고딕", 9, QFont.Bold))
        macd_group.setStyleSheet("""
            QGroupBox {
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 15px;
                padding: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                padding: 0 5px;
            }
        """)
        macd_layout = QVBoxLayout()
        macd_layout.setContentsMargins(10, 10, 10, 10)
        macd_layout.setSpacing(10)

        # MACD 활성화 체크박스
        self.macd_enabled = QCheckBox("MACD 지표 사용")
        self.macd_enabled.toggled.connect(self._on_macd_toggled)
        macd_layout.addWidget(self.macd_enabled)

        # MACD 파라미터
        macd_form = QFormLayout()
        macd_form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        macd_form.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        macd_form.setHorizontalSpacing(20)
        macd_form.setVerticalSpacing(10)

        self.macd_fast_spin = QSpinBox()
        self.macd_fast_spin.setRange(5, 30)
        self.macd_fast_spin.setSuffix(" 기간")
        self.macd_fast_spin.setMinimumWidth(150)
        self.macd_fast_spin.setFont(QFont("맑은 고딕", 10))
        macd_form.addRow("Fast 기간:", self.macd_fast_spin)

        self.macd_slow_spin = QSpinBox()
        self.macd_slow_spin.setRange(10, 50)
        self.macd_slow_spin.setSuffix(" 기간")
        self.macd_slow_spin.setMinimumWidth(150)
        self.macd_slow_spin.setFont(QFont("맑은 고딕", 10))
        macd_form.addRow("Slow 기간:", self.macd_slow_spin)

        self.macd_signal_spin = QSpinBox()
        self.macd_signal_spin.setRange(5, 20)
        self.macd_signal_spin.setSuffix(" 기간")
        self.macd_signal_spin.setMinimumWidth(150)
        self.macd_signal_spin.setFont(QFont("맑은 고딕", 10))
        macd_form.addRow("Signal 기간:", self.macd_signal_spin)

        macd_layout.addLayout(macd_form)

        macd_info = QLabel("MACD 골든크로스 시 매수 신호 발생")
        macd_info.setStyleSheet("color: #666; font-size: 10px;")
        macd_layout.addWidget(macd_info)

        macd_group.setLayout(macd_layout)
        layout.addWidget(macd_group)

        # ========================================
        # Volume 지표 설정
        # ========================================
        volume_group = QGroupBox("📊 Volume (거래량)")
        volume_group.setFont(QFont("맑은 고딕", 9, QFont.Bold))
        volume_group.setStyleSheet("""
            QGroupBox {
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 15px;
                padding: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                padding: 0 5px;
            }
        """)
        volume_layout = QVBoxLayout()
        volume_layout.setContentsMargins(10, 10, 10, 10)
        volume_layout.setSpacing(10)

        # Volume 활성화 체크박스
        self.volume_enabled = QCheckBox("거래량 지표 사용")
        self.volume_enabled.toggled.connect(self._on_volume_toggled)
        volume_layout.addWidget(self.volume_enabled)

        # Volume 파라미터
        volume_form = QFormLayout()
        volume_form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        volume_form.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        volume_form.setHorizontalSpacing(20)
        volume_form.setVerticalSpacing(10)

        self.volume_period_spin = QSpinBox()
        self.volume_period_spin.setRange(10, 50)
        self.volume_period_spin.setSuffix(" 기간")
        self.volume_period_spin.setMinimumWidth(150)
        self.volume_period_spin.setFont(QFont("맑은 고딕", 10))
        volume_form.addRow("평균 기간:", self.volume_period_spin)

        self.volume_threshold_spin = QDoubleSpinBox()
        self.volume_threshold_spin.setRange(1.0, 5.0)
        self.volume_threshold_spin.setSingleStep(0.1)
        self.volume_threshold_spin.setSuffix("배")
        self.volume_threshold_spin.setMinimumWidth(150)
        self.volume_threshold_spin.setFont(QFont("맑은 고딕", 10))
        volume_form.addRow("급증 기준:", self.volume_threshold_spin)

        volume_layout.addLayout(volume_form)

        volume_info = QLabel("현재 거래량 ≥ 평균 × 급증기준 시 매수 신호 발생")
        volume_info.setStyleSheet("color: #666; font-size: 10px;")
        volume_layout.addWidget(volume_info)

        volume_group.setLayout(volume_layout)
        layout.addWidget(volume_group)

        group.setLayout(layout)
        return group

    def _on_rsi_toggled(self, checked: bool):
        """RSI 지표 활성화/비활성화"""
        self.rsi_period_spin.setEnabled(checked)
        self.rsi_oversold_spin.setEnabled(checked)
        self.rsi_overbought_spin.setEnabled(checked)

    def _on_macd_toggled(self, checked: bool):
        """MACD 지표 활성화/비활성화"""
        self.macd_fast_spin.setEnabled(checked)
        self.macd_slow_spin.setEnabled(checked)
        self.macd_signal_spin.setEnabled(checked)

    def _on_volume_toggled(self, checked: bool):
        """Volume 지표 활성화/비활성화"""
        self.volume_period_spin.setEnabled(checked)
        self.volume_threshold_spin.setEnabled(checked)

    def _load_config(self):
        """설정 로드 (UI에 반영)"""
        try:
            # 투자 스타일 로드
            style = self.config.get("investment_style", "balanced")
            style_map = {
                "conservative": self.conservative_radio,
                "balanced": self.balanced_radio,
                "aggressive": self.aggressive_radio,
                "custom": self.custom_radio
            }
            if style in style_map:
                style_map[style].setChecked(True)
            else:
                self.balanced_radio.setChecked(True)

            # 지표 설정 로드
            indicators = self.config.get("indicators", {})

            # RSI
            rsi = indicators.get("rsi", {})
            self.rsi_enabled.setChecked(rsi.get("enabled", True))
            self.rsi_period_spin.setValue(rsi.get("period", 14))
            self.rsi_oversold_spin.setValue(rsi.get("oversold", 30))
            self.rsi_overbought_spin.setValue(rsi.get("overbought", 70))

            # MACD
            macd = indicators.get("macd", {})
            self.macd_enabled.setChecked(macd.get("enabled", True))
            self.macd_fast_spin.setValue(macd.get("fast", 12))
            self.macd_slow_spin.setValue(macd.get("slow", 26))
            self.macd_signal_spin.setValue(macd.get("signal", 9))

            # Volume
            volume = indicators.get("volume", {})
            self.volume_enabled.setChecked(volume.get("enabled", True))
            self.volume_period_spin.setValue(volume.get("period", 20))
            self.volume_threshold_spin.setValue(volume.get("threshold", 2.0))

        except Exception as e:
            logger.error(f"설정 로드 오류: {e}")
            # 로드 실패 시 기본값 사용 (이미 _get_default_config()에서 설정됨)

    def get_config(self) -> dict:
        """
        현재 설정 반환

        Returns:
            자동매수 설정 딕셔너리
        """
        # 투자 스타일 추출
        style_id = self.style_button_group.checkedId()
        style_map = {0: "conservative", 1: "balanced", 2: "aggressive", 3: "custom"}
        investment_style = style_map.get(style_id, "balanced")

        # 지표 설정 추출
        indicators = {
            "rsi": {
                "enabled": self.rsi_enabled.isChecked(),
                "period": self.rsi_period_spin.value(),
                "oversold": self.rsi_oversold_spin.value(),
                "overbought": self.rsi_overbought_spin.value()
            },
            "macd": {
                "enabled": self.macd_enabled.isChecked(),
                "fast": self.macd_fast_spin.value(),
                "slow": self.macd_slow_spin.value(),
                "signal": self.macd_signal_spin.value()
            },
            "volume": {
                "enabled": self.volume_enabled.isChecked(),
                "period": self.volume_period_spin.value(),
                "threshold": self.volume_threshold_spin.value()
            }
        }

        return {
            "enabled": True,
            "strategy": "v4_auto_buy",
            "investment_style": investment_style,
            "candle_unit": "60",
            "indicators": indicators,
            "buy_amount_krw": self.config.get("buy_amount_krw", 50000)
        }
