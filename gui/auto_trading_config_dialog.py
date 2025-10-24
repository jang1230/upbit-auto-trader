"""
AutoTradingConfigDialog - 완전 자동 트레이딩 설정 다이얼로그
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLabel, QSpinBox, QDoubleSpinBox,
    QGroupBox, QCheckBox, QRadioButton, QButtonGroup,
    QListWidget, QLineEdit, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from gui.auto_trading_config import AutoTradingConfig


class AutoTradingConfigDialog(QDialog):
    """완전 자동 트레이딩 설정 다이얼로그"""
    
    def __init__(self, config: AutoTradingConfig, parent=None):
        super().__init__(parent)
        
        self.config = config.copy() if hasattr(config, 'copy') else config
        
        self.setWindowTitle("🤖 완전 자동 트레이딩 설정")
        self.setMinimumWidth(600)
        self.setMinimumHeight(700)
        
        self._init_ui()
        self._load_config()
    
    def _init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # 1. 기본 설정
        basic_group = QGroupBox("📊 기본 설정")
        basic_layout = QFormLayout()
        
        # 매수 금액
        self.buy_amount_spin = QSpinBox()
        self.buy_amount_spin.setRange(5000, 10000000)
        self.buy_amount_spin.setSingleStep(1000)
        self.buy_amount_spin.setSuffix(" 원")
        basic_layout.addRow("💰 매수 금액:", self.buy_amount_spin)
        
        # 스캔 주기
        self.scan_interval_spin = QSpinBox()
        self.scan_interval_spin.setRange(10, 300)
        self.scan_interval_spin.setSingleStep(10)
        self.scan_interval_spin.setSuffix(" 초")
        basic_layout.addRow("⏱️ 스캔 주기:", self.scan_interval_spin)
        
        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)
        
        # 2. 모니터링 설정
        monitoring_group = QGroupBox("🎯 모니터링 설정")
        monitoring_layout = QVBoxLayout()
        
        # 모드 선택
        mode_layout = QHBoxLayout()
        self.top_marketcap_radio = QRadioButton("시가총액 상위")
        self.custom_list_radio = QRadioButton("커스텀 리스트")
        
        self.mode_button_group = QButtonGroup()
        self.mode_button_group.addButton(self.top_marketcap_radio, 0)
        self.mode_button_group.addButton(self.custom_list_radio, 1)
        
        mode_layout.addWidget(self.top_marketcap_radio)
        mode_layout.addWidget(self.custom_list_radio)
        mode_layout.addStretch()
        
        monitoring_layout.addLayout(mode_layout)
        
        # 상위 N개 설정
        topn_layout = QHBoxLayout()
        topn_layout.addWidget(QLabel("상위"))
        self.top_n_spin = QSpinBox()
        self.top_n_spin.setRange(5, 20)
        topn_layout.addWidget(self.top_n_spin)
        topn_layout.addWidget(QLabel("개 코인"))
        topn_layout.addStretch()
        monitoring_layout.addLayout(topn_layout)
        
        monitoring_group.setLayout(monitoring_layout)
        layout.addWidget(monitoring_group)
        
        # 3. 리스크 관리
        risk_group = QGroupBox("🛡️ 리스크 관리")
        risk_layout = QVBoxLayout()
        
        # 최대 포지션 수
        max_pos_layout = QHBoxLayout()
        self.max_positions_check = QCheckBox("최대 포지션 수 제한")
        max_pos_layout.addWidget(self.max_positions_check)
        self.max_positions_spin = QSpinBox()
        self.max_positions_spin.setRange(1, 20)
        max_pos_layout.addWidget(self.max_positions_spin)
        max_pos_layout.addWidget(QLabel("개"))
        max_pos_layout.addStretch()
        risk_layout.addLayout(max_pos_layout)
        
        # 일일 거래 횟수
        daily_trades_layout = QHBoxLayout()
        self.daily_trades_check = QCheckBox("일일 거래 횟수 제한")
        daily_trades_layout.addWidget(self.daily_trades_check)
        self.daily_trades_spin = QSpinBox()
        self.daily_trades_spin.setRange(1, 50)
        daily_trades_layout.addWidget(self.daily_trades_spin)
        daily_trades_layout.addWidget(QLabel("회"))
        daily_trades_layout.addStretch()
        risk_layout.addLayout(daily_trades_layout)
        
        # 최소 잔고 유지
        min_balance_layout = QHBoxLayout()
        self.min_krw_balance_check = QCheckBox("최소 KRW 잔고 유지")
        min_balance_layout.addWidget(self.min_krw_balance_check)
        self.min_krw_balance_spin = QSpinBox()
        self.min_krw_balance_spin.setRange(10000, 10000000)
        self.min_krw_balance_spin.setSingleStep(10000)
        self.min_krw_balance_spin.setSuffix(" 원")
        min_balance_layout.addWidget(self.min_krw_balance_spin)
        min_balance_layout.addStretch()
        risk_layout.addLayout(min_balance_layout)
        
        # 일일 손실 한도
        stop_loss_layout = QHBoxLayout()
        self.stop_on_loss_check = QCheckBox("일일 손실 한도")
        stop_loss_layout.addWidget(self.stop_on_loss_check)
        self.stop_on_loss_spin = QDoubleSpinBox()
        self.stop_on_loss_spin.setRange(1.0, 50.0)
        self.stop_on_loss_spin.setSingleStep(1.0)
        self.stop_on_loss_spin.setSuffix(" %")
        stop_loss_layout.addWidget(self.stop_on_loss_spin)
        stop_loss_layout.addStretch()
        risk_layout.addLayout(stop_loss_layout)
        
        risk_group.setLayout(risk_layout)
        layout.addWidget(risk_group)
        
        # 4. 버튼
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("취소")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("💾 저장")
        save_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px; font-weight: bold;")
        save_btn.clicked.connect(self._save_config)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
    
    def _load_config(self):
        """설정 로드"""
        # 기본 설정
        self.buy_amount_spin.setValue(int(self.config.buy_amount))
        self.scan_interval_spin.setValue(self.config.scan_interval)
        
        # 모니터링 설정
        if self.config.monitoring_mode == "top_marketcap":
            self.top_marketcap_radio.setChecked(True)
        else:
            self.custom_list_radio.setChecked(True)
        
        self.top_n_spin.setValue(self.config.top_n)
        
        # 리스크 관리
        self.max_positions_check.setChecked(self.config.max_positions_enabled)
        self.max_positions_spin.setValue(self.config.max_positions_limit)
        
        self.daily_trades_check.setChecked(self.config.daily_trades_enabled)
        self.daily_trades_spin.setValue(self.config.daily_trades_limit)
        
        self.min_krw_balance_check.setChecked(self.config.min_krw_balance_enabled)
        self.min_krw_balance_spin.setValue(int(self.config.min_krw_balance_amount))
        
        self.stop_on_loss_check.setChecked(self.config.stop_on_loss_enabled)
        self.stop_on_loss_spin.setValue(self.config.stop_on_loss_daily_pct)
    
    def _save_config(self):
        """설정 저장"""
        # 기본 설정
        self.config.buy_amount = float(self.buy_amount_spin.value())
        self.config.scan_interval = self.scan_interval_spin.value()
        
        # 모니터링 설정
        if self.top_marketcap_radio.isChecked():
            self.config.monitoring_mode = "top_marketcap"
        else:
            self.config.monitoring_mode = "custom_list"
        
        self.config.top_n = self.top_n_spin.value()
        
        # 리스크 관리
        self.config.max_positions_enabled = self.max_positions_check.isChecked()
        self.config.max_positions_limit = self.max_positions_spin.value()
        
        self.config.daily_trades_enabled = self.daily_trades_check.isChecked()
        self.config.daily_trades_limit = self.daily_trades_spin.value()
        
        self.config.min_krw_balance_enabled = self.min_krw_balance_check.isChecked()
        self.config.min_krw_balance_amount = float(self.min_krw_balance_spin.value())
        
        self.config.stop_on_loss_enabled = self.stop_on_loss_check.isChecked()
        self.config.stop_on_loss_daily_pct = self.stop_on_loss_spin.value()
        
        # 유효성 검증
        is_valid, error_msg = self.config.validate()
        if not is_valid:
            QMessageBox.warning(self, "설정 오류", error_msg)
            return
        
        self.accept()
    
    def get_config(self) -> AutoTradingConfig:
        """설정 반환"""
        return self.config
