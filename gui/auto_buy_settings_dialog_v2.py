"""
AutoBuySettingsDialogV2 - 자동매수 설정 다이얼로그 (V4 + Expert 라디오 버튼 통합)

V4 전략과 Expert 전략을 라디오 버튼으로 선택
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
    QPushButton, QRadioButton, QLabel, QMessageBox, QSpinBox,
    QScrollArea, QWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
import logging

# Expert 위젯 임포트 (V4는 _create_v4_widget()에서 임포트)
from gui.expert_strategy_widget import ExpertStrategyWidget

logger = logging.getLogger(__name__)


class AutoBuySettingsDialogV2(QDialog):
    """
    매수 설정 다이얼로그 V2 (Manual + Auto 통합)

    1. 매수 모드 선택: Manual (수동 매수) vs Auto (자동 매수)
    2. Auto 모드 시 전략 선택: V4 vs Expert
    """

    def __init__(self, config: dict = None, parent=None, embedded=False):
        """
        Args:
            config: buy_settings 딕셔너리 (mode + auto_config 또는 legacy auto_config)
            parent: 부모 위젯
            embedded: True면 다른 다이얼로그에 임베딩되는 모드 (사이즈 설정 스킵)
        """
        super().__init__(parent)

        self.config = config or self._get_default_config()
        self.embedded = embedded  # embedded 모드 저장

        self.setWindowTitle("⚙️ 자동매수 전략 설정")

        # Standalone 다이얼로그일 때만 사이즈 설정
        if not embedded:
            self.setMinimumWidth(800)
            self.setMinimumHeight(700)
            self.resize(820, 750)

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
        """UI 초기화 - 매수 모드 + 전략 선택"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # === 1. 매수 모드 선택 (Manual vs Auto) ===
        mode_group = self._create_buy_mode_group()
        main_layout.addWidget(mode_group)

        # === 2. 자동 매수 설정 컨테이너 (auto 모드에서만 표시) ===
        self.auto_settings_container = QGroupBox()
        self.auto_settings_container.setStyleSheet("QGroupBox { border: none; }")
        auto_layout = QVBoxLayout()
        auto_layout.setSpacing(12)
        auto_layout.setContentsMargins(0, 5, 0, 0)

        # === 2-1. 전략 선택 영역 (라디오 버튼) ===
        strategy_group = QGroupBox("📊 자동매수 전략 선택")
        strategy_group.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        strategy_group.setStyleSheet("""
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
        strategy_layout = QVBoxLayout()
        strategy_layout.setContentsMargins(10, 10, 10, 10)
        strategy_layout.setSpacing(8)

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
        auto_layout.addWidget(strategy_group)

        # 라디오 버튼 이벤트 연결
        self.v4_radio.toggled.connect(self._on_strategy_changed)
        self.expert_radio.toggled.connect(self._on_strategy_changed)

        # === 2-2. 매수 금액 설정 (공통) ===
        buy_amount_group = self._create_buy_amount_group()
        auto_layout.addWidget(buy_amount_group)

        # === 2-3. 설정 폼 영역 (Scrollable) ===
        # Container 위젯 생성 (V4 + Expert 위젯을 담을 컨테이너)
        widget_container = QWidget()
        widget_container.setObjectName("widgetContainer")
        # 중요: ID selector 사용하여 자식 위젯에 cascade되지 않도록 함
        widget_container.setStyleSheet("#widgetContainer { background-color: transparent; }")
        container_layout = QVBoxLayout(widget_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # V4 위젯
        self.v4_widget = self._create_v4_widget()
        container_layout.addWidget(self.v4_widget)

        # Expert 위젯
        self.expert_widget = self._create_expert_widget()
        container_layout.addWidget(self.expert_widget)

        # 기본값: V4 숨김, Expert 표시
        self.v4_widget.setVisible(False)
        self.expert_widget.setVisible(True)

        # 스크롤 영역으로 감싸기 (V4/Expert 위젯만 스크롤)
        scroll_area = QScrollArea()
        scroll_area.setObjectName("scrollArea")
        scroll_area.setWidget(widget_container)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        # 중요: ID selector 사용하여 자식 위젯에 cascade되지 않도록 함
        scroll_area.setStyleSheet("#scrollArea { background-color: transparent; border: none; }")

        # embedded 모드일 때는 더 작은 최소 높이 사용
        if self.embedded:
            scroll_area.setMinimumHeight(150)  # 임베딩 모드: 최소 150px
            scroll_area.setMaximumHeight(250)  # 임베딩 모드: 최대 250px
        else:
            scroll_area.setMinimumHeight(350)  # Standalone: 최소 350px
            scroll_area.setMaximumHeight(500)  # Standalone: 최대 500px

        auto_layout.addWidget(scroll_area, 1)  # stretch factor = 1

        # 자동 매수 컨테이너 레이아웃 설정
        self.auto_settings_container.setLayout(auto_layout)
        main_layout.addWidget(self.auto_settings_container)

        # === 3. 버튼 영역 ===
        button_layout = self._create_button_layout()
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

        # === 4. 이벤트 연결 (UI 생성 완료 후) ===
        # 매수 모드 변경 이벤트
        self.manual_mode_radio.toggled.connect(self._on_buy_mode_changed)
        self.auto_mode_radio.toggled.connect(self._on_buy_mode_changed)

    def _create_buy_mode_group(self) -> QGroupBox:
        """
        매수 모드 선택 그룹 생성 (Manual vs Auto)

        Returns:
            매수 모드 선택 QGroupBox
        """
        group = QGroupBox("🎯 매수 모드 선택")
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
        layout.setSpacing(8)

        # Manual 모드 라디오 버튼
        self.manual_mode_radio = QRadioButton("📱 수동 매수 (Upbit에서 직접 매수)")
        self.manual_mode_radio.setFont(QFont("맑은 고딕", 10))
        self.manual_mode_radio.setStyleSheet("""
            QRadioButton {
                padding: 8px;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
            }
        """)
        layout.addWidget(self.manual_mode_radio)

        # Manual 설명
        manual_desc = QLabel("   ↳ Upbit 거래소에서 직접 매수, DCA/익절/손절은 자동 실행")
        manual_desc.setFont(QFont("맑은 고딕", 9))
        manual_desc.setStyleSheet("color: #666; padding-left: 30px;")
        layout.addWidget(manual_desc)

        layout.addSpacing(10)

        # Auto 모드 라디오 버튼
        self.auto_mode_radio = QRadioButton("🤖 자동 매수 (전략 기반 자동 매수)")
        self.auto_mode_radio.setFont(QFont("맑은 고딕", 10))
        self.auto_mode_radio.setStyleSheet("""
            QRadioButton {
                padding: 8px;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
            }
        """)
        layout.addWidget(self.auto_mode_radio)

        # Auto 설명
        auto_desc = QLabel("   ↳ V4/Expert 전략으로 자동 매수, DCA/익절/손절도 자동 실행")
        auto_desc.setFont(QFont("맑은 고딕", 9))
        auto_desc.setStyleSheet("color: #666; padding-left: 30px;")
        layout.addWidget(auto_desc)

        # NOTE: 이벤트 연결은 _init_ui()에서 auto_settings_container 생성 후에 수행
        # 기본값: Auto 모드 선택 (이벤트 없이)
        self.auto_mode_radio.setChecked(True)

        group.setLayout(layout)
        return group

    def _on_buy_mode_changed(self):
        """매수 모드 변경 시 호출"""
        if self.manual_mode_radio.isChecked():
            # Manual 모드: 자동 설정 컨테이너 비활성화 (보이지만 편집 불가)
            self.auto_settings_container.setEnabled(False)
            logger.info("📱 수동 매수 모드 선택됨 (자동매수 설정 비활성화)")
        else:
            # Auto 모드: 자동 설정 컨테이너 활성화
            self.auto_settings_container.setEnabled(True)
            logger.info("🤖 자동 매수 모드 선택됨 (자동매수 설정 활성화)")

    def _create_buy_amount_group(self) -> QGroupBox:
        """
        매수 금액 설정 그룹 생성 (공통)

        Returns:
            매수 금액 설정 QGroupBox
        """
        group = QGroupBox("💰 1회 매수 금액")
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
        layout = QFormLayout()
        layout.setContentsMargins(10, 10, 10, 10)

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
        """V4 설정 위젯 생성 (순수 QWidget 사용)"""
        from gui.v4_settings_widget import V4SettingsWidget

        # auto_config 추출 (구조: buy_settings > auto_config)
        auto_config = self.config.get("auto_config", self.config)

        # V4 전략일 때만 config 전달
        if auto_config.get("strategy") in [None, "v4_auto_buy"]:
            v4_config = auto_config
        else:
            v4_config = None

        return V4SettingsWidget(v4_config, self)

    def _create_expert_widget(self):
        """Expert 설정 위젯 생성"""
        # auto_config 추출 (구조: buy_settings > auto_config)
        auto_config = self.config.get("auto_config", self.config)

        # Expert 전략일 때만 config 전달
        if auto_config.get("strategy") == "expert":
            expert_config = auto_config
        else:
            expert_config = None

        expert_widget = ExpertStrategyWidget(expert_config, self)
        return expert_widget

    def _on_strategy_changed(self):
        """전략 선택 변경 시 호출"""
        if self.v4_radio.isChecked():
            self.v4_widget.setVisible(True)
            self.expert_widget.setVisible(False)
            logger.info("✅ V4 전략 선택됨")
        else:
            self.v4_widget.setVisible(False)
            self.expert_widget.setVisible(True)
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
        """설정 로드 및 모드/전략 선택"""
        try:
            # 매수 금액 로드 (공통)
            buy_amount = self.config.get("buy_amount_krw", 50000)
            self.buy_amount_spin.setValue(buy_amount)

            # 모드 확인 (backward compatibility)
            mode = self.config.get("mode", None)

            if mode == "manual":
                # Manual 모드
                self.manual_mode_radio.setChecked(True)
                # NOTE: _on_buy_mode_changed()가 자동 호출되어 setEnabled(False) 실행됨
                logger.info("📱 Manual 모드 로드")

            elif mode == "auto" or mode is None:
                # Auto 모드 또는 구버전 (mode 필드 없음)
                self.auto_mode_radio.setChecked(True)
                # NOTE: _on_buy_mode_changed()가 자동 호출되어 setEnabled(True) 실행됨

                # auto_config에서 전략 정보 가져오기
                auto_config = self.config.get("auto_config", self.config)  # Fallback to self.config for backward compatibility
                strategy = auto_config.get("strategy", "v4_auto_buy")

                if strategy == "expert":
                    # Expert 라디오 버튼 선택
                    self.expert_radio.setChecked(True)
                    self.v4_widget.setVisible(False)
                    self.expert_widget.setVisible(True)
                    logger.info("📊 Auto Expert 전략 로드")
                else:
                    # V4 라디오 버튼 선택 (기본값)
                    self.v4_radio.setChecked(True)
                    self.v4_widget.setVisible(True)
                    self.expert_widget.setVisible(False)
                    logger.info("📊 Auto V4 전략 로드")

        except Exception as e:
            logger.error(f"❌ 설정 로드 실패: {e}")
            # 기본값: Auto V4 선택
            self.auto_mode_radio.setChecked(True)
            # NOTE: _on_buy_mode_changed()가 자동 호출되어 setEnabled(True) 실행됨
            self.v4_radio.setChecked(True)
            self.v4_widget.setVisible(True)
            self.expert_widget.setVisible(False)
            self.buy_amount_spin.setValue(50000)

    def get_config(self) -> dict:
        """
        현재 선택된 모드 및 전략의 설정을 반환

        Returns:
            buy_settings 구조의 설정 딕셔너리
        """
        try:
            # 공통 매수 금액
            buy_amount = self.buy_amount_spin.value()

            # Manual 모드 선택 시
            if self.manual_mode_radio.isChecked():
                result = {
                    "mode": "manual",
                    "buy_amount_krw": buy_amount
                }
                logger.info(f"📱 Manual 모드 설정 반환: 매수금액 {buy_amount:,}원")
                return result

            # Auto 모드 선택 시
            if self.v4_radio.isChecked():
                # V4 전략 선택됨
                v4_config = self.v4_widget.get_config()

                auto_config = {
                    "enabled": v4_config.get("enabled", True),
                    "strategy": "v4_auto_buy",
                    "investment_style": v4_config.get("investment_style"),
                    "candle_unit": v4_config.get("candle_unit"),
                    "signal_mode": v4_config.get("signal_mode", "all"),
                    "min_signals_required": v4_config.get("min_signals_required"),
                    "indicators": v4_config.get("indicators"),
                    "buy_amount_krw": buy_amount
                }

                result = {
                    "mode": "auto",
                    "buy_amount_krw": buy_amount,  # 공통 필드
                    "auto_config": auto_config
                }

                signal_info = f"신호모드: {auto_config.get('signal_mode')}"
                if auto_config.get('signal_mode') == "partial":
                    signal_info += f" (최소 {auto_config.get('min_signals_required')}개)"
                logger.info(f"📊 Auto V4 설정 반환: {auto_config.get('investment_style')}, {signal_info}, 매수금액: {buy_amount:,}원")
                return result

            else:
                # Expert 전략 선택됨
                expert_config = self.expert_widget.get_config()

                auto_config = {
                    "enabled": True,
                    "strategy": "expert",
                    "expert_profile": expert_config.get("expert_profile"),
                    "candle_unit": expert_config.get("candle_unit"),
                    "buy_amount_krw": buy_amount
                }

                # Custom 프로필인 경우 가중치 추가
                if expert_config.get("expert_profile") == "custom":
                    auto_config["custom_weights"] = expert_config.get("custom_weights")
                    auto_config["custom_threshold"] = expert_config.get("custom_threshold")

                result = {
                    "mode": "auto",
                    "buy_amount_krw": buy_amount,  # 공통 필드
                    "auto_config": auto_config
                }

                logger.info(f"🎯 Auto Expert 설정 반환: {auto_config.get('expert_profile')}, 매수금액: {buy_amount:,}원")
                return result

        except Exception as e:
            logger.error(f"❌ get_config() 실패: {e}", exc_info=True)
            # 기본값 반환 (auto 모드)
            return {
                "mode": "auto",
                "buy_amount_krw": 50000,
                "auto_config": self._get_default_config()
            }


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
