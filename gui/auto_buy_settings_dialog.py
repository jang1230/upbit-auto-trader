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

from gui.v4_custom_settings_dialog import V4CustomSettingsDialog

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

        # 2. 지표 설정 그룹
        indicators_group = self._create_indicators_group()
        layout.addWidget(indicators_group)

        # 3. 매수 금액 그룹
        buy_amount_group = self._create_buy_amount_group()
        layout.addWidget(buy_amount_group)

        # 4. 버튼
        button_layout = self._create_button_layout()
        layout.addLayout(button_layout)

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
        rsi_config = preset["rsi"]
        self.rsi_enabled.setChecked(rsi_config["enabled"])
        self.rsi_period_spin.setValue(rsi_config["period"])
        self.rsi_oversold_spin.setValue(rsi_config["oversold"])
        self.rsi_overbought_spin.setValue(rsi_config["overbought"])

        # MACD 설정 적용
        macd_config = preset["macd"]
        self.macd_enabled.setChecked(macd_config["enabled"])
        self.macd_fast_spin.setValue(macd_config["fast"])
        self.macd_slow_spin.setValue(macd_config["slow"])
        self.macd_signal_spin.setValue(macd_config["signal"])

        # Volume 설정 적용
        volume_config = preset["volume"]
        self.volume_enabled.setChecked(volume_config["enabled"])
        self.volume_period_spin.setValue(volume_config["period"])
        self.volume_threshold_spin.setValue(volume_config["threshold"])

    def _set_indicators_enabled(self, enabled: bool):
        """
        지표 입력 필드 활성화/비활성화

        Args:
            enabled: True면 활성화 (커스텀 모드), False면 비활성화 (프리셋 모드)
        """
        # RSI 체크박스와 입력 필드
        self.rsi_enabled.setEnabled(enabled)
        # 체크박스가 체크되어 있을 때만 입력 필드 활성화 (커스텀 모드일 때)
        if enabled:
            self.rsi_period_spin.setEnabled(self.rsi_enabled.isChecked())
            self.rsi_oversold_spin.setEnabled(self.rsi_enabled.isChecked())
            self.rsi_overbought_spin.setEnabled(self.rsi_enabled.isChecked())
        else:
            # 프리셋 모드: 모두 비활성화
            self.rsi_period_spin.setEnabled(False)
            self.rsi_oversold_spin.setEnabled(False)
            self.rsi_overbought_spin.setEnabled(False)

        # MACD 체크박스와 입력 필드
        self.macd_enabled.setEnabled(enabled)
        if enabled:
            self.macd_fast_spin.setEnabled(self.macd_enabled.isChecked())
            self.macd_slow_spin.setEnabled(self.macd_enabled.isChecked())
            self.macd_signal_spin.setEnabled(self.macd_enabled.isChecked())
        else:
            self.macd_fast_spin.setEnabled(False)
            self.macd_slow_spin.setEnabled(False)
            self.macd_signal_spin.setEnabled(False)

        # Volume 체크박스와 입력 필드
        self.volume_enabled.setEnabled(enabled)
        if enabled:
            self.volume_period_spin.setEnabled(self.volume_enabled.isChecked())
            self.volume_threshold_spin.setEnabled(self.volume_enabled.isChecked())
        else:
            self.volume_period_spin.setEnabled(False)
            self.volume_threshold_spin.setEnabled(False)

    def _create_indicators_group(self) -> QGroupBox:
        """
        지표 설정 그룹 생성

        Returns:
            지표 설정 QGroupBox
        """
        group = QGroupBox("📈 지표 설정 (커스텀 모드에서만 수정 가능)")
        group.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        layout = QVBoxLayout()

        # ========================================
        # RSI 지표 설정
        # ========================================
        rsi_group = QGroupBox("RSI (Relative Strength Index)")
        rsi_group.setFont(QFont("맑은 고딕", 9))
        rsi_layout = QVBoxLayout()

        # RSI 활성화 체크박스
        self.rsi_enabled = QCheckBox("RSI 지표 사용")
        self.rsi_enabled.toggled.connect(self._on_rsi_toggled)
        rsi_layout.addWidget(self.rsi_enabled)

        # RSI 파라미터
        rsi_form = QFormLayout()

        self.rsi_period_spin = QSpinBox()
        self.rsi_period_spin.setRange(5, 50)
        self.rsi_period_spin.setSuffix(" 기간")
        rsi_form.addRow("기간:", self.rsi_period_spin)

        self.rsi_oversold_spin = QSpinBox()
        self.rsi_oversold_spin.setRange(10, 40)
        rsi_form.addRow("과매도 기준:", self.rsi_oversold_spin)

        self.rsi_overbought_spin = QSpinBox()
        self.rsi_overbought_spin.setRange(60, 90)
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
        macd_group = QGroupBox("MACD (Moving Average Convergence Divergence)")
        macd_group.setFont(QFont("맑은 고딕", 9))
        macd_layout = QVBoxLayout()

        # MACD 활성화 체크박스
        self.macd_enabled = QCheckBox("MACD 지표 사용")
        self.macd_enabled.toggled.connect(self._on_macd_toggled)
        macd_layout.addWidget(self.macd_enabled)

        # MACD 파라미터
        macd_form = QFormLayout()

        self.macd_fast_spin = QSpinBox()
        self.macd_fast_spin.setRange(5, 30)
        self.macd_fast_spin.setSuffix(" 기간")
        macd_form.addRow("Fast 기간:", self.macd_fast_spin)

        self.macd_slow_spin = QSpinBox()
        self.macd_slow_spin.setRange(10, 50)
        self.macd_slow_spin.setSuffix(" 기간")
        macd_form.addRow("Slow 기간:", self.macd_slow_spin)

        self.macd_signal_spin = QSpinBox()
        self.macd_signal_spin.setRange(5, 20)
        self.macd_signal_spin.setSuffix(" 기간")
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
        volume_group = QGroupBox("Volume (거래량)")
        volume_group.setFont(QFont("맑은 고딕", 9))
        volume_layout = QVBoxLayout()

        # Volume 활성화 체크박스
        self.volume_enabled = QCheckBox("거래량 지표 사용")
        self.volume_enabled.toggled.connect(self._on_volume_toggled)
        volume_layout.addWidget(self.volume_enabled)

        # Volume 파라미터
        volume_form = QFormLayout()

        self.volume_period_spin = QSpinBox()
        self.volume_period_spin.setRange(10, 50)
        self.volume_period_spin.setSuffix(" 기간")
        volume_form.addRow("평균 기간:", self.volume_period_spin)

        self.volume_threshold_spin = QDoubleSpinBox()
        self.volume_threshold_spin.setRange(1.0, 5.0)
        self.volume_threshold_spin.setSingleStep(0.1)
        self.volume_threshold_spin.setSuffix("배")
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

    def _create_buy_amount_group(self) -> QGroupBox:
        """
        매수 금액 설정 그룹 생성

        Returns:
            매수 금액 설정 QGroupBox
        """
        group = QGroupBox("💰 매수 금액")
        group.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        layout = QFormLayout()

        self.buy_amount_spin = QSpinBox()
        self.buy_amount_spin.setRange(5000, 10000000)
        self.buy_amount_spin.setSingleStep(5000)
        self.buy_amount_spin.setSuffix(" 원")
        layout.addRow("1회 매수 금액:", self.buy_amount_spin)

        buy_amount_info = QLabel(
            "자동매수 신호 발생 시 1회 매수할 금액입니다.\n"
            "예: 50,000원 설정 시 매수 신호마다 50,000원씩 매수"
        )
        buy_amount_info.setStyleSheet("color: #666; font-size: 10px;")
        buy_amount_info.setWordWrap(True)
        layout.addRow("", buy_amount_info)

        group.setLayout(layout)
        return group

    def _create_button_layout(self) -> QHBoxLayout:
        """
        하단 버튼 레이아웃 생성

        Returns:
            버튼 레이아웃
        """
        layout = QHBoxLayout()
        layout.addStretch()

        # 취소 버튼
        self.cancel_button = QPushButton("취소")
        self.cancel_button.clicked.connect(self.reject)
        layout.addWidget(self.cancel_button)

        # 저장 버튼 (녹색 강조)
        self.save_button = QPushButton("💾 저장")
        self.save_button.setStyleSheet(
            "background-color: #4CAF50; color: white; "
            "padding: 8px 16px; font-weight: bold;"
        )
        self.save_button.clicked.connect(self._save_settings)
        layout.addWidget(self.save_button)

        return layout

    def _save_settings(self):
        """
        설정 저장

        현재 UI의 모든 설정값을 self.config에 저장하고 다이얼로그 닫기
        """
        try:
            # 1. 투자 스타일 및 candle_unit 저장
            style_id = self.style_button_group.checkedId()
            style_map = {
                0: ("conservative", "240"),  # 4시간
                1: ("balanced", "60"),       # 1시간
                2: ("aggressive", "15"),     # 15분
                3: ("custom", self.config.get("candle_unit", "60"))  # 커스텀: 기존 값 유지
            }

            investment_style, candle_unit = style_map[style_id]
            self.config["investment_style"] = investment_style
            self.config["candle_unit"] = candle_unit

            # 2. 지표 설정 저장
            self.config["indicators"] = {
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

            # 3. 매수 금액 저장
            self.config["buy_amount_krw"] = self.buy_amount_spin.value()

            # 4. enabled 플래그 (항상 True)
            self.config["enabled"] = True

            logger.info(f"✅ 자동매수 설정 저장 완료: {investment_style}, {candle_unit}분봉")
            self.accept()

        except Exception as e:
            logger.error(f"❌ 자동매수 설정 저장 실패: {e}")
            QMessageBox.critical(
                self,
                "저장 실패",
                f"설정 저장 중 오류가 발생했습니다:\n{e}"
            )

    def _load_config(self):
        """
        설정 로드

        self.config에서 값을 읽어 UI에 반영
        """
        try:
            # 1. 투자 스타일 로드 및 라디오 버튼 설정
            investment_style = self.config.get("investment_style", "balanced")
            style_id_map = {
                "conservative": 0,
                "balanced": 1,
                "aggressive": 2,
                "custom": 3
            }
            style_id = style_id_map.get(investment_style, 1)  # 기본값 Balanced

            # 라디오 버튼 선택
            if style_id == 0:
                self.conservative_radio.setChecked(True)
            elif style_id == 1:
                self.balanced_radio.setChecked(True)
            elif style_id == 2:
                self.aggressive_radio.setChecked(True)
            else:
                self.custom_radio.setChecked(True)

            # 2. 지표 설정 로드
            indicators = self.config.get("indicators", {})

            # RSI
            rsi_config = indicators.get("rsi", {})
            self.rsi_enabled.setChecked(rsi_config.get("enabled", True))
            self.rsi_period_spin.setValue(rsi_config.get("period", 14))
            self.rsi_oversold_spin.setValue(rsi_config.get("oversold", 30))
            self.rsi_overbought_spin.setValue(rsi_config.get("overbought", 70))

            # MACD
            macd_config = indicators.get("macd", {})
            self.macd_enabled.setChecked(macd_config.get("enabled", True))
            self.macd_fast_spin.setValue(macd_config.get("fast", 12))
            self.macd_slow_spin.setValue(macd_config.get("slow", 26))
            self.macd_signal_spin.setValue(macd_config.get("signal", 9))

            # Volume
            volume_config = indicators.get("volume", {})
            self.volume_enabled.setChecked(volume_config.get("enabled", True))
            self.volume_period_spin.setValue(volume_config.get("period", 20))
            self.volume_threshold_spin.setValue(volume_config.get("threshold", 2.0))

            # 3. 매수 금액 로드
            buy_amount = self.config.get("buy_amount_krw", 50000)
            self.buy_amount_spin.setValue(buy_amount)

            # 4. 프리셋 모드면 지표 필드 비활성화, Custom이면 고급 설정 버튼 표시
            if style_id != 3:  # Custom이 아니면
                self._set_indicators_enabled(False)
                self.custom_advanced_button.setVisible(False)
            else:  # Custom
                self._set_indicators_enabled(False)  # Custom은 다이얼로그에서 설정
                self.custom_advanced_button.setVisible(True)

            logger.info(f"✅ 자동매수 설정 로드 완료: {investment_style}")

        except Exception as e:
            logger.error(f"❌ 자동매수 설정 로드 실패: {e}")
            # 로드 실패 시 기본값 사용 (이미 _get_default_config()에서 설정됨)

    def get_config(self) -> dict:
        """
        현재 설정 반환

        Returns:
            자동매수 설정 딕셔너리
        """
        return self.config
