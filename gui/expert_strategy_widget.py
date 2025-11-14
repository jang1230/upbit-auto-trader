"""
ExpertStrategyWidget - Expert 전략 설정 위젯

10개 전문가 프로필 선택 + 커스텀 가중치 설정
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QComboBox, QSlider, QSpinBox, QDoubleSpinBox, QGroupBox,
    QTextEdit
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
import logging

logger = logging.getLogger(__name__)


class ExpertStrategyWidget(QWidget):
    """Expert 전략 설정 위젯"""

    # 10개 전문가 프로필 정의 (ExpertStrategy.EXPERT_PROFILES와 동일)
    EXPERT_PROFILES = {
        "rsi_specialist": {
            "name": "RSI 전문가",
            "description": "과매도 구간 포착에 특화\nRSI 가중치가 높아 과매도 반등 시점을 잘 포착합니다.",
            "weights": {"rsi": 0.70, "macd": 0.65, "bollinger": 0.50, "volume": 0.60, "trend": 0.40},
            "confidence_threshold": 50
        },
        "momentum_expert": {
            "name": "모멘텀 전문가",
            "description": "MACD 골든크로스 중심 전략\n빠른 모멘텀 전환을 포착하는 데 유리합니다.",
            "weights": {"macd": 0.75, "volume": 0.70, "rsi": 0.50, "trend": 0.60, "bollinger": 0.40},
            "confidence_threshold": 50
        },
        "volatility_expert": {
            "name": "볼린저 전문가",
            "description": "변동성 확장 포착\n볼린저 밴드 하단 터치 시 진입을 선호합니다.",
            "weights": {"bollinger": 0.85, "volume": 0.65, "rsi": 0.55, "macd": 0.60, "trend": 0.40},
            "confidence_threshold": 50
        },
        "volume_expert": {
            "name": "거래량 전문가",
            "description": "거래량 급증 기반\n큰 손의 매수 움직임을 따라갑니다.",
            "weights": {"volume": 0.85, "macd": 0.65, "bollinger": 0.50, "rsi": 0.50, "trend": 0.45},
            "confidence_threshold": 50
        },
        "balanced_expert": {
            "name": "균형형 전문가 ⭐",
            "description": "모든 지표 균등 분석\n가장 안정적이고 범용적인 전략입니다.",
            "weights": {"rsi": 0.65, "macd": 0.65, "bollinger": 0.65, "volume": 0.65, "trend": 0.60},
            "confidence_threshold": 45
        },
        "conservative_expert": {
            "name": "보수적 전문가",
            "description": "안전한 진입 우선\n높은 신뢰도 기준(55%)으로 보수적 진입합니다.",
            "weights": {"rsi": 0.75, "trend": 0.70, "bollinger": 0.60, "macd": 0.50, "volume": 0.55},
            "confidence_threshold": 55
        },
        "aggressive_expert": {
            "name": "공격적 전문가",
            "description": "빠른 진입\n낮은 신뢰도 기준(45%)으로 적극적 진입합니다.",
            "weights": {"macd": 0.80, "volume": 0.75, "rsi": 0.45, "bollinger": 0.55, "trend": 0.50},
            "confidence_threshold": 45
        },
        "trend_follower": {
            "name": "추세 추종가",
            "description": "강한 상승 추세 포착\n추세와 모멘텀을 중시합니다.",
            "weights": {"trend": 0.80, "macd": 0.70, "volume": 0.65, "rsi": 0.45, "bollinger": 0.50},
            "confidence_threshold": 50
        },
        "reversal_hunter": {
            "name": "반전 사냥꾼",
            "description": "과매도 반등 노림\nRSI와 볼린저 밴드를 활용한 반전 매매입니다.",
            "weights": {"rsi": 0.80, "bollinger": 0.70, "macd": 0.55, "trend": 0.40, "volume": 0.60},
            "confidence_threshold": 50
        },
        "smart_money": {
            "name": "스마트머니",
            "description": "거래량+추세 종합\n거래량과 추세를 함께 분석합니다.",
            "weights": {"volume": 0.80, "trend": 0.75, "macd": 0.65, "bollinger": 0.55, "rsi": 0.50},
            "confidence_threshold": 50
        }
    }

    def __init__(self, config: dict = None, parent=None):
        """
        Args:
            config: Expert 전략 설정 딕셔너리
            parent: 부모 위젯
        """
        super().__init__(parent)

        self.config = config or self._get_default_config()

        self._init_ui()
        self._load_config()

    def _get_default_config(self) -> dict:
        """기본 설정 반환"""
        return {
            "strategy": "expert",
            "expert_profile": "balanced_expert",
            "candle_unit": "10",
            "custom_weights": {
                "rsi": 0.65,
                "macd": 0.65,
                "bollinger": 0.65,
                "volume": 0.65,
                "trend": 0.60
            },
            "custom_threshold": 50,
            "buy_amount_krw": 50000
        }

    def _init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # 1. 전문가 프로필 선택
        profile_group = self._create_profile_selection_group()
        layout.addWidget(profile_group)

        # 2. 캔들 타임프레임 선택
        candle_group = self._create_candle_selection_group()
        layout.addWidget(candle_group)

        # 3. 커스텀 가중치 설정 (custom 선택 시만 표시)
        self.custom_weights_group = self._create_custom_weights_group()
        layout.addWidget(self.custom_weights_group)

        # 4. 프로필 정보 표시
        info_group = self._create_profile_info_group()
        layout.addWidget(info_group)

        self.setLayout(layout)

    def _create_profile_selection_group(self) -> QGroupBox:
        """전문가 프로필 선택 그룹"""
        group = QGroupBox("🎯 전문가 프로필")
        group.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        group.setStyleSheet("""
            QGroupBox {
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 15px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                padding: 0 5px;
            }
        """)
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        # 프로필 선택 콤보박스
        self.profile_combo = QComboBox()
        self.profile_combo.setFont(QFont("맑은 고딕", 10))

        # 프로필 목록 추가
        for profile_key, profile_data in self.EXPERT_PROFILES.items():
            self.profile_combo.addItem(profile_data["name"], profile_key)

        # 커스텀 프로필 추가
        self.profile_combo.addItem("🔧 커스텀 (가중치 직접 설정)", "custom")

        self.profile_combo.currentIndexChanged.connect(self._on_profile_changed)
        layout.addWidget(self.profile_combo)

        group.setLayout(layout)
        return group

    def _create_candle_selection_group(self) -> QGroupBox:
        """캔들 타임프레임 선택 그룹"""
        group = QGroupBox("⏱️ 캔들 타임프레임")
        group.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        group.setStyleSheet("""
            QGroupBox {
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 15px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                padding: 0 5px;
            }
        """)
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        self.candle_combo = QComboBox()
        self.candle_combo.setFont(QFont("맑은 고딕", 10))

        candles = [
            ("10", "10분봉 (스캘핑)"),
            ("15", "15분봉"),
            ("60", "1시간봉"),
            ("240", "4시간봉 (장기)")
        ]

        for value, label in candles:
            self.candle_combo.addItem(label, value)

        layout.addWidget(self.candle_combo)

        group.setLayout(layout)
        return group

    def _create_custom_weights_group(self) -> QGroupBox:
        """커스텀 가중치 설정 그룹"""
        group = QGroupBox("🔧 커스텀 가중치 설정")
        group.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        group.setStyleSheet("""
            QGroupBox {
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 15px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                padding: 0 5px;
            }
        """)
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        # 5개 지표 슬라이더 + SpinBox
        form = QFormLayout()

        # RSI 가중치
        rsi_container, self.rsi_slider, self.rsi_spinbox = self._create_weight_slider("RSI")
        form.addRow("📊 RSI:", rsi_container)

        # MACD 가중치
        macd_container, self.macd_slider, self.macd_spinbox = self._create_weight_slider("MACD")
        form.addRow("📈 MACD:", macd_container)

        # Bollinger 가중치
        bollinger_container, self.bollinger_slider, self.bollinger_spinbox = self._create_weight_slider("Bollinger")
        form.addRow("📉 Bollinger:", bollinger_container)

        # Volume 가중치
        volume_container, self.volume_slider, self.volume_spinbox = self._create_weight_slider("Volume")
        form.addRow("📊 Volume:", volume_container)

        # Trend 가중치
        trend_container, self.trend_slider, self.trend_spinbox = self._create_weight_slider("Trend")
        form.addRow("📈 Trend:", trend_container)

        layout.addLayout(form)

        # 신뢰도 기준
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("🎯 신뢰도 기준:"))

        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(0, 100)
        self.threshold_spin.setSuffix(" %")
        self.threshold_spin.setValue(50)
        self.threshold_spin.setFont(QFont("맑은 고딕", 10))
        threshold_layout.addWidget(self.threshold_spin)

        threshold_layout.addStretch()
        layout.addLayout(threshold_layout)

        group.setLayout(layout)
        group.setVisible(False)  # 기본적으로 숨김
        return group

    def _create_weight_slider(self, name: str):
        """가중치 슬라이더 + SpinBox 생성 (0.0 ~ 1.0)

        Args:
            name: 지표 이름 (예: "RSI")

        Returns:
            tuple: (container, slider, spinbox)
        """
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        # 슬라이더 (0~100 정수)
        slider = QSlider(Qt.Horizontal)
        slider.setRange(0, 100)  # 0.00 ~ 1.00을 0~100으로 표현
        slider.setValue(65)  # 기본값 0.65
        slider.setSingleStep(5)  # 5% 단위
        slider.setPageStep(10)  # 10% 단위
        slider.setTickPosition(QSlider.TicksBelow)
        slider.setTickInterval(10)

        # DoubleSpinBox (0.0~1.0, 0.01 단위)
        spinbox = QDoubleSpinBox()
        spinbox.setRange(0.0, 1.0)
        spinbox.setSingleStep(0.01)  # 0.01 단위로 정밀 조정
        spinbox.setDecimals(2)  # 소수점 2자리
        spinbox.setValue(0.65)  # 기본값
        spinbox.setMinimumWidth(80)
        spinbox.setMaximumWidth(100)
        spinbox.setAlignment(Qt.AlignCenter)
        spinbox.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        spinbox.setStyleSheet("""
            QDoubleSpinBox {
                padding: 5px;
            }
        """)

        # 양방향 동기화: 슬라이더 → SpinBox
        def slider_to_spinbox(value):
            spinbox.blockSignals(True)
            spinbox.setValue(value / 100.0)
            spinbox.blockSignals(False)

        slider.valueChanged.connect(slider_to_spinbox)

        # 양방향 동기화: SpinBox → 슬라이더
        def spinbox_to_slider(value):
            slider.blockSignals(True)
            slider.setValue(int(value * 100))
            slider.blockSignals(False)

        spinbox.valueChanged.connect(spinbox_to_slider)

        layout.addWidget(slider, 3)
        layout.addWidget(spinbox, 1)

        return (container, slider, spinbox)

    def _create_profile_info_group(self) -> QGroupBox:
        """프로필 정보 표시 그룹"""
        group = QGroupBox("📊 프로필 정보")
        group.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        group.setStyleSheet("""
            QGroupBox {
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 15px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                padding: 0 5px;
            }
        """)
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        self.profile_info_text = QTextEdit()
        self.profile_info_text.setReadOnly(True)
        self.profile_info_text.setMaximumHeight(150)
        self.profile_info_text.setFont(QFont("맑은 고딕", 9))

        layout.addWidget(self.profile_info_text)

        group.setLayout(layout)
        return group

    def _on_profile_changed(self, index):
        """프로필 변경 시 처리"""
        profile_key = self.profile_combo.currentData()

        if profile_key == "custom":
            # 커스텀 모드: 가중치 설정 그룹 표시
            self.custom_weights_group.setVisible(True)
            self._update_profile_info_custom()
        else:
            # 프리셋 모드: 가중치 설정 숨기고 프로필 정보 표시
            self.custom_weights_group.setVisible(False)
            profile = self.EXPERT_PROFILES[profile_key]
            self._update_profile_info(profile)

    def _update_profile_info(self, profile: dict):
        """프로필 정보 업데이트"""
        info = f"<b>{profile['name']}</b><br><br>"
        info += f"<b>설명:</b><br>{profile['description']}<br><br>"
        info += f"<b>지표 가중치:</b><br>"
        info += f"  • RSI: {profile['weights']['rsi']}<br>"
        info += f"  • MACD: {profile['weights']['macd']}<br>"
        info += f"  • Bollinger: {profile['weights']['bollinger']}<br>"
        info += f"  • Volume: {profile['weights']['volume']}<br>"
        info += f"  • Trend: {profile['weights']['trend']}<br><br>"
        info += f"<b>신뢰도 기준:</b> {profile['confidence_threshold']}%"

        self.profile_info_text.setHtml(info)

    def _update_profile_info_custom(self):
        """커스텀 프로필 정보 업데이트"""
        info = "<b>🔧 커스텀 전문가</b><br><br>"
        info += "<b>설명:</b><br>"
        info += "사용자가 직접 지표별 가중치를 설정합니다.<br>"
        info += "각 지표의 중요도를 조절하여 자신만의 전략을 만들 수 있습니다.<br><br>"
        info += "위의 슬라이더를 조정하여 가중치를 변경하세요."

        self.profile_info_text.setHtml(info)

    def _load_config(self):
        """설정 로드"""
        # 프로필 선택
        profile_key = self.config.get("expert_profile", "balanced_expert")
        index = self.profile_combo.findData(profile_key)
        if index >= 0:
            self.profile_combo.setCurrentIndex(index)

        # 캔들 선택
        candle_unit = self.config.get("candle_unit", "10")
        index = self.candle_combo.findData(candle_unit)
        if index >= 0:
            self.candle_combo.setCurrentIndex(index)

        # 커스텀 가중치
        if profile_key == "custom":
            custom_weights = self.config.get("custom_weights", {})
            # SpinBox에 값 설정 (슬라이더는 자동 동기화됨)
            self.rsi_spinbox.setValue(custom_weights.get("rsi", 0.65))
            self.macd_spinbox.setValue(custom_weights.get("macd", 0.65))
            self.bollinger_spinbox.setValue(custom_weights.get("bollinger", 0.65))
            self.volume_spinbox.setValue(custom_weights.get("volume", 0.65))
            self.trend_spinbox.setValue(custom_weights.get("trend", 0.60))

            custom_threshold = self.config.get("custom_threshold", 50)
            self.threshold_spin.setValue(custom_threshold)

    def get_config(self) -> dict:
        """현재 설정 반환"""
        profile_key = self.profile_combo.currentData()
        candle_unit = self.candle_combo.currentData()

        config = {
            "strategy": "expert",
            "expert_profile": profile_key,
            "candle_unit": candle_unit
        }

        if profile_key == "custom":
            # SpinBox 값 사용 (정확한 값)
            config["custom_weights"] = {
                "rsi": self.rsi_spinbox.value(),
                "macd": self.macd_spinbox.value(),
                "bollinger": self.bollinger_spinbox.value(),
                "volume": self.volume_spinbox.value(),
                "trend": self.trend_spinbox.value()
            }
            config["custom_threshold"] = self.threshold_spin.value()

        return config
