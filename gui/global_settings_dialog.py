"""
전역 설정 다이얼로그
- 거래 제한 (최대 포지션, 최소 잔고, 거래일 리셋)
- 일일 손실 한도
- 텔레그램 알림
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QSpinBox, QDoubleSpinBox, QCheckBox, QLineEdit,
    QComboBox, QPushButton, QGroupBox, QFormLayout, QMessageBox
)
from PySide6.QtCore import Qt
from gui.config_manager import ConfigManager
import logging

logger = logging.getLogger(__name__)


class GlobalSettingsDialog(QDialog):
    """전역 설정 다이얼로그"""

    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager  # V4 config (config.json)
        self.env_config_manager = ConfigManager()  # .env config (Upbit API)
        self.config = config_manager.load_config()

        self.setWindowTitle("전역 설정")
        self.setMinimumSize(600, 550)

        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout()

        # 탭 위젯
        self.tab_widget = QTabWidget()

        # Tab 1: Upbit API (새로 추가)
        self.upbit_api_tab = self._create_upbit_api_tab()
        self.tab_widget.addTab(self.upbit_api_tab, "📡 Upbit API")

        # Tab 2: 거래 제한
        self.trading_limits_tab = self._create_trading_limits_tab()
        self.tab_widget.addTab(self.trading_limits_tab, "거래 제한")

        # Tab 2: 손실 한도 (일일 손실 한도 + 포지션 손실 한도)
        self.loss_limit_tab = self._create_loss_limit_tab()
        self.tab_widget.addTab(self.loss_limit_tab, "손실 한도")

        # Tab 3: 텔레그램 알림
        self.telegram_tab = self._create_telegram_tab()
        self.tab_widget.addTab(self.telegram_tab, "텔레그램 알림")

        layout.addWidget(self.tab_widget)

        # 하단 버튼
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.save_button = QPushButton("저장")
        self.save_button.clicked.connect(self._save_settings)
        button_layout.addWidget(self.save_button)

        self.cancel_button = QPushButton("취소")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def _create_upbit_api_tab(self) -> QWidget:
        """Upbit API 탭 생성"""
        widget = QWidget()
        layout = QVBoxLayout()

        # API 키 그룹
        api_group = QGroupBox("API Keys")
        api_layout = QFormLayout()

        # Access Key
        self.access_key_edit = QLineEdit()
        self.access_key_edit.setEchoMode(QLineEdit.Password)
        self.access_key_edit.setPlaceholderText("Access Key를 입력하세요")
        api_layout.addRow("Access Key:", self.access_key_edit)

        # Access Key 표시 버튼
        self.access_key_show_btn = QPushButton("👁️ 표시")
        self.access_key_show_btn.setCheckable(True)
        self.access_key_show_btn.setMaximumWidth(80)
        self.access_key_show_btn.clicked.connect(
            lambda checked: self.access_key_edit.setEchoMode(
                QLineEdit.Normal if checked else QLineEdit.Password
            )
        )
        api_layout.addRow("", self.access_key_show_btn)

        # Secret Key
        self.secret_key_edit = QLineEdit()
        self.secret_key_edit.setEchoMode(QLineEdit.Password)
        self.secret_key_edit.setPlaceholderText("Secret Key를 입력하세요")
        api_layout.addRow("Secret Key:", self.secret_key_edit)

        # Secret Key 표시 버튼
        self.secret_key_show_btn = QPushButton("👁️ 표시")
        self.secret_key_show_btn.setCheckable(True)
        self.secret_key_show_btn.setMaximumWidth(80)
        self.secret_key_show_btn.clicked.connect(
            lambda checked: self.secret_key_edit.setEchoMode(
                QLineEdit.Normal if checked else QLineEdit.Password
            )
        )
        api_layout.addRow("", self.secret_key_show_btn)

        api_group.setLayout(api_layout)
        layout.addWidget(api_group)

        # 테스트 버튼
        self.upbit_test_btn = QPushButton("🔍 연결 테스트")
        self.upbit_test_btn.clicked.connect(self._test_upbit)
        layout.addWidget(self.upbit_test_btn)

        # 안내 메시지
        info_label = QLabel(
            "<b>💡 API 키 발급 방법:</b><br>"
            "1. Upbit 웹사이트 접속<br>"
            "2. 마이페이지 > Open API 관리<br>"
            "3. API 키 생성 (자산 조회, 주문 조회, 주문하기 권한)<br>"
            "4. Access Key와 Secret Key 복사<br><br>"
            "🔗 <a href='https://upbit.com/mypage/open_api_management'>Upbit API 관리 페이지</a>"
        )
        info_label.setOpenExternalLinks(True)
        info_label.setWordWrap(True)
        info_label.setStyleSheet("background-color: #f0f0f0; padding: 10px; border-radius: 5px;")
        layout.addWidget(info_label)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _create_trading_limits_tab(self) -> QWidget:
        """거래 제한 탭 생성"""
        widget = QWidget()
        layout = QVBoxLayout()

        # 1. 거래일 리셋 시간
        reset_group = QGroupBox("거래일 리셋 시간")
        reset_layout = QFormLayout()

        self.reset_hour_spin = QSpinBox()
        self.reset_hour_spin.setRange(0, 23)
        self.reset_hour_spin.setSuffix("시")
        reset_layout.addRow("리셋 시간:", self.reset_hour_spin)

        reset_info = QLabel("매일 이 시간에 일일 손실 한도가 초기화됩니다.")
        reset_info.setStyleSheet("color: gray; font-size: 11px;")
        reset_layout.addRow("", reset_info)

        reset_group.setLayout(reset_layout)
        layout.addWidget(reset_group)

        # 2. 최대 포지션 수
        max_pos_group = QGroupBox("최대 포지션 수 제한")
        max_pos_layout = QVBoxLayout()

        self.max_positions_enabled = QCheckBox("최대 포지션 수 제한 활성화")
        self.max_positions_enabled.toggled.connect(self._on_max_positions_toggled)
        max_pos_layout.addWidget(self.max_positions_enabled)

        max_pos_form = QFormLayout()
        self.max_positions_spin = QSpinBox()
        self.max_positions_spin.setRange(1, 50)
        self.max_positions_spin.setSuffix("개")
        max_pos_form.addRow("최대 포지션:", self.max_positions_spin)

        max_pos_info = QLabel("동시에 보유할 수 있는 최대 포지션 수를 제한합니다.")
        max_pos_info.setStyleSheet("color: gray; font-size: 11px;")
        max_pos_form.addRow("", max_pos_info)

        max_pos_layout.addLayout(max_pos_form)
        max_pos_group.setLayout(max_pos_layout)
        layout.addWidget(max_pos_group)

        # 3. 최소 KRW 잔고
        min_balance_group = QGroupBox("최소 KRW 잔고 유지")
        min_balance_layout = QVBoxLayout()

        self.min_balance_enabled = QCheckBox("최소 KRW 잔고 유지 활성화")
        self.min_balance_enabled.toggled.connect(self._on_min_balance_toggled)
        min_balance_layout.addWidget(self.min_balance_enabled)

        min_balance_form = QFormLayout()
        self.min_balance_spin = QSpinBox()
        self.min_balance_spin.setRange(0, 10000000)
        self.min_balance_spin.setSingleStep(10000)
        self.min_balance_spin.setSuffix("원")
        min_balance_form.addRow("최소 잔고:", self.min_balance_spin)

        min_balance_info = QLabel("KRW 잔고가 이 금액 이하일 경우 매수를 중단합니다.")
        min_balance_info.setStyleSheet("color: gray; font-size: 11px;")
        min_balance_form.addRow("", min_balance_info)

        min_balance_layout.addLayout(min_balance_form)
        min_balance_group.setLayout(min_balance_layout)
        layout.addWidget(min_balance_group)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _create_loss_limit_tab(self) -> QWidget:
        """손실 한도 탭 생성 (일일 손실 한도 + 포지션 손실 한도)"""
        widget = QWidget()
        layout = QVBoxLayout()

        # ========== 1. 일일 손실 한도 ==========
        daily_loss_group = QGroupBox("일일 손실 한도 설정")
        daily_loss_layout = QVBoxLayout()

        # 활성화 체크박스
        self.daily_loss_enabled = QCheckBox("일일 손실 한도 활성화")
        self.daily_loss_enabled.toggled.connect(self._on_daily_loss_toggled)
        daily_loss_layout.addWidget(self.daily_loss_enabled)

        # 손실 퍼센트
        loss_pct_layout = QFormLayout()
        self.daily_loss_pct_spin = QDoubleSpinBox()
        self.daily_loss_pct_spin.setRange(1.0, 50.0)
        self.daily_loss_pct_spin.setSingleStep(1.0)
        self.daily_loss_pct_spin.setSuffix("%")
        loss_pct_layout.addRow("손실 한도:", self.daily_loss_pct_spin)

        daily_loss_layout.addLayout(loss_pct_layout)

        # 계산 방식
        calc_method_layout = QFormLayout()
        self.calc_method_combo = QComboBox()
        self.calc_method_combo.addItem("09시 기준 (daily_only)", "daily_only")
        self.calc_method_combo.addItem("초기 자본금 기준 (total_account)", "total_account")
        calc_method_layout.addRow("계산 방식:", self.calc_method_combo)

        calc_method_info = QLabel(
            "• 09시 기준: 매일 09시 스냅샷 대비 손실 계산\n"
            "• 초기 자본금 기준: 시작 시점 대비 누적 손실 계산"
        )
        calc_method_info.setStyleSheet("color: gray; font-size: 11px;")
        calc_method_layout.addRow("", calc_method_info)

        daily_loss_layout.addLayout(calc_method_layout)

        # 조치 방식
        action_layout = QFormLayout()
        self.action_combo = QComboBox()
        self.action_combo.addItem("알림만 (alert)", "alert")
        self.action_combo.addItem("전체 청산 (liquidate)", "liquidate")
        action_layout.addRow("조치:", self.action_combo)

        action_info = QLabel(
            "• 알림만: 텔레그램 알림만 전송\n"
            "• 전체 청산: 모든 포지션을 시장가로 매도"
        )
        action_info.setStyleSheet("color: gray; font-size: 11px;")
        action_layout.addRow("", action_info)

        daily_loss_layout.addLayout(action_layout)

        daily_loss_group.setLayout(daily_loss_layout)
        layout.addWidget(daily_loss_group)

        # ========== 2. 포지션 손실 한도 (새로 추가) ==========
        position_loss_group = QGroupBox("포지션 손실 한도 설정")
        position_loss_layout = QVBoxLayout()

        # 활성화 체크박스
        self.position_loss_enabled = QCheckBox("포지션 손실 한도 활성화")
        self.position_loss_enabled.toggled.connect(self._on_position_loss_toggled)
        position_loss_layout.addWidget(self.position_loss_enabled)

        # 손실 퍼센트
        pos_loss_pct_layout = QFormLayout()
        self.position_loss_pct_spin = QDoubleSpinBox()
        self.position_loss_pct_spin.setRange(-50.0, 0.0)
        self.position_loss_pct_spin.setSingleStep(1.0)
        self.position_loss_pct_spin.setSuffix("%")
        self.position_loss_pct_spin.setValue(-10.0)
        pos_loss_pct_layout.addRow("손실 한도:", self.position_loss_pct_spin)

        pos_loss_info = QLabel(
            "거래 그룹의 합산 손익률이 이 값 이하가 되면 조치를 취합니다.\n"
            "(예: -10% → 총 투자금 대비 -10% 손실 시 발동)"
        )
        pos_loss_info.setStyleSheet("color: gray; font-size: 11px;")
        pos_loss_pct_layout.addRow("", pos_loss_info)

        position_loss_layout.addLayout(pos_loss_pct_layout)

        # 관찰 그룹 제외
        self.exclude_observation_groups = QCheckBox("관찰 전용 그룹 제외")
        self.exclude_observation_groups.setChecked(True)
        position_loss_layout.addWidget(self.exclude_observation_groups)

        exclude_info = QLabel(
            "체크 시: 관찰 전용 그룹의 포지션은 손실 계산에서 제외됩니다."
        )
        exclude_info.setStyleSheet("color: gray; font-size: 11px;")
        position_loss_layout.addWidget(exclude_info)

        # 조치 방식
        pos_action_layout = QFormLayout()
        self.position_action_combo = QComboBox()
        self.position_action_combo.addItem("알림만 (alert)", "alert")
        self.position_action_combo.addItem("전체 청산 (liquidate)", "liquidate")
        pos_action_layout.addRow("조치:", self.position_action_combo)

        pos_action_info = QLabel(
            "• 알림만: 텔레그램 알림 + 매수 중단 (재시작 필요)\n"
            "• 전체 청산: 거래 그룹 포지션 전량 매도 + 매수 중단"
        )
        pos_action_info.setStyleSheet("color: gray; font-size: 11px;")
        pos_action_layout.addRow("", pos_action_info)

        position_loss_layout.addLayout(pos_action_layout)

        position_loss_group.setLayout(position_loss_layout)
        layout.addWidget(position_loss_group)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _create_telegram_tab(self) -> QWidget:
        """텔레그램 알림 탭 생성"""
        widget = QWidget()
        layout = QVBoxLayout()

        telegram_group = QGroupBox("텔레그램 알림 설정")
        telegram_layout = QVBoxLayout()

        # 활성화 체크박스
        self.telegram_enabled = QCheckBox("텔레그램 알림 활성화")
        self.telegram_enabled.toggled.connect(self._on_telegram_toggled)
        telegram_layout.addWidget(self.telegram_enabled)

        # Bot Token
        token_layout = QFormLayout()
        self.telegram_token_input = QLineEdit()
        self.telegram_token_input.setPlaceholderText("1234567890:ABCdefGHIjklMNOpqrsTUVwxyz")
        token_layout.addRow("Bot Token:", self.telegram_token_input)

        # Chat ID
        self.telegram_chat_id_input = QLineEdit()
        self.telegram_chat_id_input.setPlaceholderText("123456789")
        token_layout.addRow("Chat ID:", self.telegram_chat_id_input)

        telegram_layout.addLayout(token_layout)

        # 안내 정보
        info_label = QLabel(
            "<b>설정 방법:</b><br>"
            "1. BotFather에서 봇 생성 후 Token 발급<br>"
            "2. 봇과 대화 시작<br>"
            "3. getUpdates API로 Chat ID 확인<br><br>"
            "자세한 내용은 docs/TELEGRAM_설정_가이드.md 참조"
        )
        info_label.setStyleSheet("color: gray; font-size: 11px;")
        info_label.setWordWrap(True)
        telegram_layout.addWidget(info_label)

        # 테스트 버튼
        self.telegram_test_btn = QPushButton("📱 알림 테스트 전송")
        self.telegram_test_btn.clicked.connect(self._test_telegram)
        telegram_layout.addWidget(self.telegram_test_btn)

        telegram_group.setLayout(telegram_layout)
        layout.addWidget(telegram_group)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _load_settings(self):
        """설정 로드"""
        # Upbit API (.env에서 로드)
        self.access_key_edit.setText(self.env_config_manager.get_upbit_access_key())
        self.secret_key_edit.setText(self.env_config_manager.get_upbit_secret_key())

        global_settings = self.config.get("global_settings", {})

        # 거래일 리셋 시간
        self.reset_hour_spin.setValue(global_settings.get("trading_day_reset_hour", 9))

        # 최대 포지션 수
        max_pos = global_settings.get("max_positions", {})
        self.max_positions_enabled.setChecked(max_pos.get("enabled", False))
        self.max_positions_spin.setValue(max_pos.get("limit", 3))
        self._on_max_positions_toggled(max_pos.get("enabled", False))

        # 최소 KRW 잔고
        min_balance = global_settings.get("min_krw_balance", {})
        self.min_balance_enabled.setChecked(min_balance.get("enabled", True))
        self.min_balance_spin.setValue(min_balance.get("amount", 50000))
        self._on_min_balance_toggled(min_balance.get("enabled", True))

        # 일일 손실 한도
        daily_loss = global_settings.get("daily_loss_limit", {})
        self.daily_loss_enabled.setChecked(daily_loss.get("enabled", False))
        self.daily_loss_pct_spin.setValue(daily_loss.get("loss_pct", 10.0))

        calc_method = daily_loss.get("calculation_method", "daily_only")
        index = self.calc_method_combo.findData(calc_method)
        if index >= 0:
            self.calc_method_combo.setCurrentIndex(index)

        action = daily_loss.get("action", "alert")
        index = self.action_combo.findData(action)
        if index >= 0:
            self.action_combo.setCurrentIndex(index)

        self._on_daily_loss_toggled(daily_loss.get("enabled", False))

        # 포지션 손실 한도
        position_loss = global_settings.get("position_loss_limit", {})
        self.position_loss_enabled.setChecked(position_loss.get("enabled", False))
        self.position_loss_pct_spin.setValue(position_loss.get("limit_pct", -10.0))
        self.exclude_observation_groups.setChecked(position_loss.get("exclude_observation_groups", True))

        pos_action = position_loss.get("action", "alert")
        index = self.position_action_combo.findData(pos_action)
        if index >= 0:
            self.position_action_combo.setCurrentIndex(index)

        self._on_position_loss_toggled(position_loss.get("enabled", False))

        # 텔레그램
        telegram = global_settings.get("telegram", {})
        self.telegram_enabled.setChecked(telegram.get("enabled", False))
        self.telegram_token_input.setText(telegram.get("token", ""))
        self.telegram_chat_id_input.setText(telegram.get("chat_id", ""))
        self._on_telegram_toggled(telegram.get("enabled", False))

    def _on_max_positions_toggled(self, checked: bool):
        """최대 포지션 수 토글"""
        self.max_positions_spin.setEnabled(checked)

    def _on_min_balance_toggled(self, checked: bool):
        """최소 잔고 토글"""
        self.min_balance_spin.setEnabled(checked)

    def _on_daily_loss_toggled(self, checked: bool):
        """일일 손실 한도 토글"""
        self.daily_loss_pct_spin.setEnabled(checked)
        self.calc_method_combo.setEnabled(checked)
        self.action_combo.setEnabled(checked)

    def _on_position_loss_toggled(self, checked: bool):
        """포지션 손실 한도 토글"""
        self.position_loss_pct_spin.setEnabled(checked)
        self.exclude_observation_groups.setEnabled(checked)
        self.position_action_combo.setEnabled(checked)

    def _on_telegram_toggled(self, checked: bool):
        """텔레그램 토글"""
        self.telegram_token_input.setEnabled(checked)
        self.telegram_chat_id_input.setEnabled(checked)
        self.telegram_test_btn.setEnabled(checked)

    def _test_telegram(self):
        """텔레그램 알림 테스트"""
        bot_token = self.telegram_token_input.text().strip()
        chat_id = self.telegram_chat_id_input.text().strip()

        if not bot_token or not chat_id:
            QMessageBox.warning(self, "입력 오류", "Bot Token과 Chat ID를 입력하세요.")
            return

        # 형식 검증
        if ':' not in bot_token:
            QMessageBox.warning(
                self,
                "형식 오류",
                "Bot Token 형식이 올바르지 않습니다.\n"
                "형식: 숫자:영문숫자 (예: 123456789:ABC-DEF1234)"
            )
            return

        # 실제 Telegram 테스트
        try:
            import requests

            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {
                "chat_id": chat_id,
                "text": "🧪 **테스트 메시지**\n\n"
                        "Upbit DCA Trader에서 전송한 테스트 알림입니다.\n"
                        "이 메시지가 보이면 설정이 올바릅니다! ✅",
                "parse_mode": "Markdown"
            }

            response = requests.post(url, data=data, timeout=10)

            if response.status_code == 200:
                QMessageBox.information(
                    self,
                    "전송 성공",
                    "✅ Telegram 테스트 메시지 전송 성공!\n\n"
                    "Telegram 앱에서 메시지를 확인하세요."
                )
            else:
                error_msg = response.json().get('description', '알 수 없는 오류')
                QMessageBox.critical(
                    self,
                    "전송 실패",
                    f"❌ Telegram 메시지 전송 실패:\n{error_msg}\n\n"
                    "Bot Token과 Chat ID를 확인하세요."
                )

        except Exception as e:
            QMessageBox.critical(
                self,
                "전송 실패",
                f"❌ Telegram 메시지 전송 실패:\n{str(e)}\n\n"
                "네트워크 연결과 설정을 확인하세요."
            )

    def _test_upbit(self):
        """Upbit API 연결 테스트"""
        access_key = self.access_key_edit.text().strip()
        secret_key = self.secret_key_edit.text().strip()

        if not access_key or not secret_key:
            QMessageBox.warning(self, "입력 오류", "Access Key와 Secret Key를 입력하세요.")
            return

        # 간단한 형식 검증
        if len(access_key) < 20 or len(secret_key) < 20:
            QMessageBox.warning(
                self,
                "형식 오류",
                "API 키 형식이 올바르지 않습니다.\n"
                "Upbit에서 발급받은 키를 정확히 입력하세요."
            )
            return

        # 실제 API 테스트
        try:
            from core.upbit_api import UpbitAPI

            api = UpbitAPI(access_key, secret_key)
            accounts = api.get_accounts()

            if accounts:
                QMessageBox.information(
                    self,
                    "연결 성공",
                    f"✅ Upbit API 연결 성공!\n\n"
                    f"계좌 정보: {len(accounts)}개 자산 조회됨"
                )
            else:
                QMessageBox.warning(
                    self,
                    "연결 실패",
                    "❌ API 키는 유효하지만 계좌 정보를 가져올 수 없습니다."
                )

        except Exception as e:
            QMessageBox.critical(
                self,
                "연결 실패",
                f"❌ Upbit API 연결 실패:\n{str(e)}\n\n"
                f"API 키를 확인하세요."
            )

    def _save_settings(self):
        """설정 저장"""
        try:
            # Upbit API 저장 (.env 파일)
            upbit_success = self.env_config_manager.set_upbit_keys(
                self.access_key_edit.text().strip(),
                self.secret_key_edit.text().strip()
            )
            if not upbit_success:
                QMessageBox.warning(self, "저장 실패", "Upbit API 키 저장에 실패했습니다.")
                return

            # global_settings 업데이트
            if "global_settings" not in self.config:
                self.config["global_settings"] = {}

            global_settings = self.config["global_settings"]

            # 거래일 리셋 시간
            global_settings["trading_day_reset_hour"] = self.reset_hour_spin.value()

            # 최대 포지션 수
            global_settings["max_positions"] = {
                "enabled": self.max_positions_enabled.isChecked(),
                "limit": self.max_positions_spin.value()
            }

            # 최소 KRW 잔고
            global_settings["min_krw_balance"] = {
                "enabled": self.min_balance_enabled.isChecked(),
                "amount": self.min_balance_spin.value()
            }

            # 일일 손실 한도
            global_settings["daily_loss_limit"] = {
                "enabled": self.daily_loss_enabled.isChecked(),
                "loss_pct": self.daily_loss_pct_spin.value(),
                "calculation_method": self.calc_method_combo.currentData(),
                "action": self.action_combo.currentData()
            }

            # 포지션 손실 한도
            global_settings["position_loss_limit"] = {
                "enabled": self.position_loss_enabled.isChecked(),
                "limit_pct": self.position_loss_pct_spin.value(),
                "action": self.position_action_combo.currentData(),
                "exclude_observation_groups": self.exclude_observation_groups.isChecked()
            }

            # 텔레그램
            global_settings["telegram"] = {
                "enabled": self.telegram_enabled.isChecked(),
                "token": self.telegram_token_input.text().strip(),
                "chat_id": self.telegram_chat_id_input.text().strip()
            }

            # 설정 저장
            self.config_manager.save_config(self.config)

            logger.info("✅ 전역 설정 저장 완료")
            QMessageBox.information(self, "저장 완료", "전역 설정이 저장되었습니다.")
            self.accept()

        except Exception as e:
            logger.error(f"❌ 전역 설정 저장 실패: {e}")
            QMessageBox.critical(self, "저장 실패", f"설정 저장 중 오류가 발생했습니다:\n{e}")
