"""
전역 설정 다이얼로그

V4 시스템의 global_settings를 관리하는 GUI
"""

import logging
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QCheckBox, QSpinBox, QDoubleSpinBox, QLineEdit,
    QComboBox, QPushButton, QMessageBox, QTabWidget, QWidget
)
from PySide6.QtCore import Qt

from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class GlobalSettingsDialog(QDialog):
    """
    전역 설정 다이얼로그

    Global settings 관리:
    - Daily Loss Limit
    - Telegram 알림
    - Min KRW Balance
    - Max Positions
    - Trading Day Reset Hour
    - Dry Run 모드
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("전역 설정")
        self.setMinimumSize(600, 500)
        self.resize(700, 600)

        self.config_manager = ConfigManager()
        self.config = None

        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout()

        # 탭 위젯 생성
        tab_widget = QTabWidget()

        # 탭 1: 리스크 관리
        risk_tab = self._create_risk_management_tab()
        tab_widget.addTab(risk_tab, "리스크 관리")

        # 탭 2: 알림 설정
        notification_tab = self._create_notification_tab()
        tab_widget.addTab(notification_tab, "알림 설정")

        # 탭 3: 기타 설정
        misc_tab = self._create_misc_tab()
        tab_widget.addTab(misc_tab, "기타 설정")

        layout.addWidget(tab_widget)

        # 하단 버튼
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        save_button = QPushButton("저장")
        save_button.clicked.connect(self._save_settings)
        button_layout.addWidget(save_button)

        cancel_button = QPushButton("취소")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def _create_risk_management_tab(self):
        """리스크 관리 탭 생성"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Daily Loss Limit 설정
        daily_loss_group = self._create_daily_loss_limit_group()
        layout.addWidget(daily_loss_group)

        # Min KRW Balance 설정
        min_balance_group = self._create_min_krw_balance_group()
        layout.addWidget(min_balance_group)

        # Max Positions 설정
        max_positions_group = self._create_max_positions_group()
        layout.addWidget(max_positions_group)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _create_daily_loss_limit_group(self):
        """Daily Loss Limit 설정 그룹"""
        group = QGroupBox("일일 손실 제한 (Daily Loss Limit)")
        layout = QVBoxLayout()

        # 활성화 체크박스
        self.daily_loss_enabled_checkbox = QCheckBox("일일 손실 제한 활성화")
        self.daily_loss_enabled_checkbox.toggled.connect(self._on_daily_loss_enabled_changed)
        layout.addWidget(self.daily_loss_enabled_checkbox)

        # 손실 퍼센트
        loss_pct_layout = QHBoxLayout()
        loss_pct_layout.addWidget(QLabel("손실 제한 (%):", self))
        self.loss_pct_spinbox = QDoubleSpinBox()
        self.loss_pct_spinbox.setRange(1.0, 50.0)
        self.loss_pct_spinbox.setValue(10.0)
        self.loss_pct_spinbox.setSingleStep(1.0)
        self.loss_pct_spinbox.setSuffix(" %")
        self.loss_pct_spinbox.setToolTip("일일 손실이 이 비율을 초과하면 액션 수행")
        loss_pct_layout.addWidget(self.loss_pct_spinbox)
        loss_pct_layout.addStretch()
        layout.addLayout(loss_pct_layout)

        # 계산 방법
        calc_method_layout = QHBoxLayout()
        calc_method_layout.addWidget(QLabel("계산 방법:", self))
        self.calc_method_combo = QComboBox()
        self.calc_method_combo.addItem("일일 기준 (09:00 시작)", "daily_only")
        self.calc_method_combo.addItem("전체 계좌 기준 (초기 자본)", "total_account")
        self.calc_method_combo.setToolTip(
            "daily_only: 매일 09:00 잔고 기준\n"
            "total_account: 프로그램 시작 시 초기 자본 기준"
        )
        calc_method_layout.addWidget(self.calc_method_combo)
        calc_method_layout.addStretch()
        layout.addLayout(calc_method_layout)

        # 액션 선택
        action_layout = QHBoxLayout()
        action_layout.addWidget(QLabel("액션:", self))
        self.action_combo = QComboBox()
        self.action_combo.addItem("알림만 (Alert)", "alert")
        self.action_combo.addItem("전체 청산 (Liquidate)", "liquidate")
        self.action_combo.setToolTip(
            "alert: 텔레그램 알림만 전송\n"
            "liquidate: 모든 포지션 강제 청산"
        )
        action_layout.addWidget(self.action_combo)
        action_layout.addStretch()
        layout.addLayout(action_layout)

        group.setLayout(layout)
        return group

    def _create_min_krw_balance_group(self):
        """Min KRW Balance 설정 그룹"""
        group = QGroupBox("최소 KRW 잔고 유지")
        layout = QVBoxLayout()

        # 활성화 체크박스
        self.min_balance_enabled_checkbox = QCheckBox("최소 KRW 잔고 유지 활성화")
        self.min_balance_enabled_checkbox.toggled.connect(self._on_min_balance_enabled_changed)
        layout.addWidget(self.min_balance_enabled_checkbox)

        # 최소 금액
        amount_layout = QHBoxLayout()
        amount_layout.addWidget(QLabel("최소 금액 (KRW):", self))
        self.min_balance_spinbox = QSpinBox()
        self.min_balance_spinbox.setRange(0, 100000000)
        self.min_balance_spinbox.setValue(50000)
        self.min_balance_spinbox.setSingleStep(10000)
        self.min_balance_spinbox.setSuffix(" 원")
        self.min_balance_spinbox.setToolTip("항상 유지할 최소 KRW 잔고")
        amount_layout.addWidget(self.min_balance_spinbox)
        amount_layout.addStretch()
        layout.addLayout(amount_layout)

        group.setLayout(layout)
        return group

    def _create_max_positions_group(self):
        """Max Positions 설정 그룹"""
        group = QGroupBox("최대 포지션 수 제한")
        layout = QVBoxLayout()

        # 활성화 체크박스
        self.max_positions_enabled_checkbox = QCheckBox("최대 포지션 수 제한 활성화")
        self.max_positions_enabled_checkbox.toggled.connect(self._on_max_positions_enabled_changed)
        layout.addWidget(self.max_positions_enabled_checkbox)

        # 최대 포지션 수
        limit_layout = QHBoxLayout()
        limit_layout.addWidget(QLabel("최대 포지션 수:", self))
        self.max_positions_spinbox = QSpinBox()
        self.max_positions_spinbox.setRange(1, 50)
        self.max_positions_spinbox.setValue(3)
        self.max_positions_spinbox.setSingleStep(1)
        self.max_positions_spinbox.setToolTip("동시에 보유 가능한 최대 포지션 수")
        limit_layout.addWidget(self.max_positions_spinbox)
        limit_layout.addStretch()
        layout.addLayout(limit_layout)

        group.setLayout(layout)
        return group

    def _create_notification_tab(self):
        """알림 설정 탭 생성"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Telegram 설정
        telegram_group = self._create_telegram_group()
        layout.addWidget(telegram_group)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _create_telegram_group(self):
        """Telegram 설정 그룹"""
        group = QGroupBox("텔레그램 알림")
        layout = QVBoxLayout()

        # 활성화 체크박스
        self.telegram_enabled_checkbox = QCheckBox("텔레그램 알림 활성화")
        self.telegram_enabled_checkbox.toggled.connect(self._on_telegram_enabled_changed)
        layout.addWidget(self.telegram_enabled_checkbox)

        # Bot Token
        token_layout = QHBoxLayout()
        token_layout.addWidget(QLabel("Bot Token:", self))
        self.telegram_token_input = QLineEdit()
        self.telegram_token_input.setPlaceholderText("123456:ABC-DEF...")
        self.telegram_token_input.setEchoMode(QLineEdit.Password)
        self.telegram_token_input.setToolTip("텔레그램 봇 토큰")
        token_layout.addWidget(self.telegram_token_input)
        layout.addLayout(token_layout)

        # Chat ID
        chat_id_layout = QHBoxLayout()
        chat_id_layout.addWidget(QLabel("Chat ID:", self))
        self.telegram_chat_id_input = QLineEdit()
        self.telegram_chat_id_input.setPlaceholderText("123456789")
        self.telegram_chat_id_input.setToolTip("텔레그램 채팅 ID")
        chat_id_layout.addWidget(self.telegram_chat_id_input)
        layout.addLayout(chat_id_layout)

        group.setLayout(layout)
        return group

    def _create_misc_tab(self):
        """기타 설정 탭 생성"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Trading Day Reset Hour
        reset_hour_group = self._create_reset_hour_group()
        layout.addWidget(reset_hour_group)

        # Dry Run 모드
        dry_run_group = self._create_dry_run_group()
        layout.addWidget(dry_run_group)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _create_reset_hour_group(self):
        """Trading Day Reset Hour 설정 그룹"""
        group = QGroupBox("일일 초기화 시간")
        layout = QVBoxLayout()

        hour_layout = QHBoxLayout()
        hour_layout.addWidget(QLabel("초기화 시간:", self))
        self.reset_hour_spinbox = QSpinBox()
        self.reset_hour_spinbox.setRange(0, 23)
        self.reset_hour_spinbox.setValue(9)
        self.reset_hour_spinbox.setSingleStep(1)
        self.reset_hour_spinbox.setSuffix(" 시")
        self.reset_hour_spinbox.setToolTip("매일 손실 제한 및 통계를 초기화할 시간")
        hour_layout.addWidget(self.reset_hour_spinbox)
        hour_layout.addStretch()
        layout.addLayout(hour_layout)

        group.setLayout(layout)
        return group

    def _create_dry_run_group(self):
        """Dry Run 모드 설정 그룹"""
        group = QGroupBox("거래 모드")
        layout = QVBoxLayout()

        self.dry_run_checkbox = QCheckBox("Dry Run 모드 (가상 거래)")
        self.dry_run_checkbox.setToolTip(
            "활성화: 실제 거래 없이 가상으로 테스트\n"
            "비활성화: 실제 거래 실행"
        )
        layout.addWidget(self.dry_run_checkbox)

        group.setLayout(layout)
        return group

    def _on_daily_loss_enabled_changed(self, checked):
        """Daily Loss Limit 활성화 상태 변경"""
        self.loss_pct_spinbox.setEnabled(checked)
        self.calc_method_combo.setEnabled(checked)
        self.action_combo.setEnabled(checked)

    def _on_min_balance_enabled_changed(self, checked):
        """Min Balance 활성화 상태 변경"""
        self.min_balance_spinbox.setEnabled(checked)

    def _on_max_positions_enabled_changed(self, checked):
        """Max Positions 활성화 상태 변경"""
        self.max_positions_spinbox.setEnabled(checked)

    def _on_telegram_enabled_changed(self, checked):
        """Telegram 활성화 상태 변경"""
        self.telegram_token_input.setEnabled(checked)
        self.telegram_chat_id_input.setEnabled(checked)

    def _load_settings(self):
        """설정 로드"""
        try:
            self.config = self.config_manager.load_config()
            global_settings = self.config.get("global_settings", {})

            # Daily Loss Limit
            daily_loss = global_settings.get("daily_loss_limit", {})
            self.daily_loss_enabled_checkbox.setChecked(daily_loss.get("enabled", False))
            self.loss_pct_spinbox.setValue(daily_loss.get("loss_pct", 10.0))

            calc_method = daily_loss.get("calculation_method", "daily_only")
            index = self.calc_method_combo.findData(calc_method)
            if index >= 0:
                self.calc_method_combo.setCurrentIndex(index)

            action = daily_loss.get("action", "alert")
            index = self.action_combo.findData(action)
            if index >= 0:
                self.action_combo.setCurrentIndex(index)

            # Min KRW Balance
            min_balance = global_settings.get("min_krw_balance", {})
            self.min_balance_enabled_checkbox.setChecked(min_balance.get("enabled", True))
            self.min_balance_spinbox.setValue(int(min_balance.get("amount", 50000)))

            # Max Positions
            max_positions = global_settings.get("max_positions", {})
            self.max_positions_enabled_checkbox.setChecked(max_positions.get("enabled", False))
            self.max_positions_spinbox.setValue(max_positions.get("limit", 3))

            # Telegram
            telegram = global_settings.get("telegram", {})
            self.telegram_enabled_checkbox.setChecked(telegram.get("enabled", False))
            self.telegram_token_input.setText(telegram.get("token", ""))
            self.telegram_chat_id_input.setText(telegram.get("chat_id", ""))

            # Trading Day Reset Hour
            self.reset_hour_spinbox.setValue(global_settings.get("trading_day_reset_hour", 9))

            # Dry Run
            self.dry_run_checkbox.setChecked(global_settings.get("dry_run", True))

            # 초기 활성화 상태 반영
            self._on_daily_loss_enabled_changed(self.daily_loss_enabled_checkbox.isChecked())
            self._on_min_balance_enabled_changed(self.min_balance_enabled_checkbox.isChecked())
            self._on_max_positions_enabled_changed(self.max_positions_enabled_checkbox.isChecked())
            self._on_telegram_enabled_changed(self.telegram_enabled_checkbox.isChecked())

        except Exception as e:
            logger.error(f"설정 로드 실패: {e}")
            QMessageBox.critical(self, "오류", f"설정을 불러올 수 없습니다:\n{str(e)}")

    def _save_settings(self):
        """설정 저장"""
        try:
            if not self.config:
                raise ValueError("설정이 로드되지 않았습니다")

            global_settings = self.config["global_settings"]

            # Daily Loss Limit
            global_settings["daily_loss_limit"] = {
                "enabled": self.daily_loss_enabled_checkbox.isChecked(),
                "loss_pct": self.loss_pct_spinbox.value(),
                "calculation_method": self.calc_method_combo.currentData(),
                "action": self.action_combo.currentData()
            }

            # Min KRW Balance
            global_settings["min_krw_balance"] = {
                "enabled": self.min_balance_enabled_checkbox.isChecked(),
                "amount": self.min_balance_spinbox.value()
            }

            # Max Positions
            global_settings["max_positions"] = {
                "enabled": self.max_positions_enabled_checkbox.isChecked(),
                "limit": self.max_positions_spinbox.value()
            }

            # Telegram
            global_settings["telegram"] = {
                "enabled": self.telegram_enabled_checkbox.isChecked(),
                "token": self.telegram_token_input.text().strip(),
                "chat_id": self.telegram_chat_id_input.text().strip()
            }

            # Trading Day Reset Hour
            global_settings["trading_day_reset_hour"] = self.reset_hour_spinbox.value()

            # Dry Run
            global_settings["dry_run"] = self.dry_run_checkbox.isChecked()

            # 저장
            self.config_manager.save_config(self.config)

            QMessageBox.information(self, "성공", "설정이 저장되었습니다.")
            self.accept()

        except Exception as e:
            logger.error(f"설정 저장 실패: {e}")
            QMessageBox.critical(self, "오류", f"설정을 저장할 수 없습니다:\n{str(e)}")
