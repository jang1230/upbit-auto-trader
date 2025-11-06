"""
그룹 설정 다이얼로그
V4 그룹별 매수/DCA/익절/손절 설정 UI
"""

import logging
from typing import Optional, Dict

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget,
    QPushButton, QLabel, QLineEdit, QCheckBox,
    QRadioButton, QButtonGroup, QGroupBox,
    QMessageBox, QFormLayout, QSpinBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

logger = logging.getLogger(__name__)


class GroupSettingsDialog(QDialog):
    """
    그룹 설정 다이얼로그

    3가지 거래 방식 프리셋 제공:
    1. 자동매수 + 자동매도
    2. 자동매수 + 수동매도
    3. 수동매수 + 자동매도
    """

    # 시그널: 설정 저장 완료
    settings_saved = Signal()

    def __init__(self, config_manager, group_id: str, group_name: str, parent=None):
        """
        Args:
            config_manager: ConfigManager 인스턴스
            group_id: 그룹 ID
            group_name: 그룹 이름 (표시용)
            parent: 부모 위젯
        """
        super().__init__(parent)

        self.config_manager = config_manager
        self.group_id = group_id
        self.group_name = group_name

        # UI 컴포넌트
        self.preset_buttons = []
        self.auto_buy_radio = None
        self.manual_buy_radio = None
        self.buy_amount_input = None
        self.dca_checkbox = None
        self.profit_checkbox = None
        self.loss_checkbox = None
        self.level_detail_btn = None

        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        """UI 초기화"""
        self.setWindowTitle(f"그룹 설정 - \"{self.group_name}\"")
        self.resize(650, 550)

        # 메인 레이아웃
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # ========================================
        # 프리셋 선택 영역
        # ========================================
        preset_group = QGroupBox("📋 빠른 설정")
        preset_group.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        preset_layout = QHBoxLayout(preset_group)
        preset_layout.setSpacing(10)

        # 3가지 프리셋 버튼
        presets = [
            ("자동매수 + 자동매도", "auto_auto"),
            ("자동매수 + 수동매도", "auto_manual"),
            ("수동매수 + 자동매도", "manual_auto"),
        ]

        for label, preset_id in presets:
            btn = QPushButton(label)
            btn.setFont(QFont("맑은 고딕", 9))
            btn.setStyleSheet(
                "QPushButton {"
                "  background-color: #E0E0E0;"
                "  color: #333;"
                "  padding: 12px;"
                "  border: 2px solid #BDBDBD;"
                "  border-radius: 5px;"
                "}"
                "QPushButton:hover {"
                "  background-color: #BDBDBD;"
                "}"
                "QPushButton:pressed {"
                "  background-color: #2196F3;"
                "  color: white;"
                "}"
            )
            btn.clicked.connect(lambda checked, pid=preset_id: self._apply_preset(pid))
            preset_layout.addWidget(btn)
            self.preset_buttons.append(btn)

        main_layout.addWidget(preset_group)

        # 구분선
        separator = QLabel("─" * 80)
        separator.setStyleSheet("color: #BDBDBD;")
        separator.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(separator)

        # ========================================
        # 매수 설정
        # ========================================
        buy_group = QGroupBox("🛒 매수 설정")
        buy_group.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        buy_layout = QVBoxLayout(buy_group)
        buy_layout.setSpacing(10)

        # 매수 방식 라디오 버튼
        buy_mode_layout = QHBoxLayout()
        buy_mode_label = QLabel("매수 방식:")
        buy_mode_label.setFont(QFont("맑은 고딕", 9))
        buy_mode_label.setMinimumWidth(100)
        buy_mode_layout.addWidget(buy_mode_label)

        self.auto_buy_radio = QRadioButton("자동")
        self.auto_buy_radio.setFont(QFont("맑은 고딕", 9))
        self.auto_buy_radio.toggled.connect(self._on_buy_mode_changed)
        buy_mode_layout.addWidget(self.auto_buy_radio)

        self.manual_buy_radio = QRadioButton("수동 (Upbit 앱에서 직접 매수)")
        self.manual_buy_radio.setFont(QFont("맑은 고딕", 9))
        buy_mode_layout.addWidget(self.manual_buy_radio)

        buy_mode_layout.addStretch()
        buy_layout.addLayout(buy_mode_layout)

        # 매수 금액 (자동 매수일 때만)
        buy_amount_layout = QHBoxLayout()
        buy_amount_label = QLabel("매수 금액:")
        buy_amount_label.setFont(QFont("맑은 고딕", 9))
        buy_amount_label.setMinimumWidth(100)
        buy_amount_layout.addWidget(buy_amount_label)

        self.buy_amount_input = QSpinBox()
        self.buy_amount_input.setFont(QFont("맑은 고딕", 9))
        self.buy_amount_input.setMinimum(5000)
        self.buy_amount_input.setMaximum(10000000)
        self.buy_amount_input.setSingleStep(10000)
        self.buy_amount_input.setValue(50000)
        self.buy_amount_input.setSuffix(" 원")
        buy_amount_layout.addWidget(self.buy_amount_input)

        buy_amount_layout.addStretch()
        buy_layout.addLayout(buy_amount_layout)

        main_layout.addWidget(buy_group)

        # ========================================
        # DCA/익절/손절 설정
        # ========================================
        strategy_group = QGroupBox("📊 거래 전략")
        strategy_group.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        strategy_layout = QVBoxLayout(strategy_group)
        strategy_layout.setSpacing(12)

        # DCA 체크박스
        self.dca_checkbox = QCheckBox("📊 DCA (추가매수) 사용")
        self.dca_checkbox.setFont(QFont("맑은 고딕", 9, QFont.Bold))
        self.dca_checkbox.setStyleSheet("color: #2196F3;")
        strategy_layout.addWidget(self.dca_checkbox)

        dca_desc = QLabel("   💡 가격 하락 시 추가 매수하여 평균 단가를 낮춤")
        dca_desc.setFont(QFont("맑은 고딕", 8))
        dca_desc.setStyleSheet("color: #666;")
        strategy_layout.addWidget(dca_desc)

        # 익절 체크박스
        self.profit_checkbox = QCheckBox("💰 익절 (수익 실현) 사용")
        self.profit_checkbox.setFont(QFont("맑은 고딕", 9, QFont.Bold))
        self.profit_checkbox.setStyleSheet("color: #4CAF50;")
        strategy_layout.addWidget(self.profit_checkbox)

        profit_desc = QLabel("   💡 목표 수익률 도달 시 자동 매도")
        profit_desc.setFont(QFont("맑은 고딕", 8))
        profit_desc.setStyleSheet("color: #666;")
        strategy_layout.addWidget(profit_desc)

        # 손절 체크박스
        self.loss_checkbox = QCheckBox("🛡️ 손절 (손실 차단) 사용")
        self.loss_checkbox.setFont(QFont("맑은 고딕", 9, QFont.Bold))
        self.loss_checkbox.setStyleSheet("color: #F44336;")
        strategy_layout.addWidget(self.loss_checkbox)

        loss_desc = QLabel("   💡 손실률 초과 시 자동 매도하여 추가 손실 방지")
        loss_desc.setFont(QFont("맑은 고딕", 8))
        loss_desc.setStyleSheet("color: #666;")
        strategy_layout.addWidget(loss_desc)

        main_layout.addWidget(strategy_group)

        # ========================================
        # 레벨 상세 설정 버튼
        # ========================================
        self.level_detail_btn = QPushButton("⚙️ 레벨 상세 설정")
        self.level_detail_btn.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        self.level_detail_btn.setStyleSheet(
            "background-color: #9C27B0; color: white; padding: 15px; border-radius: 5px;"
        )
        self.level_detail_btn.clicked.connect(self._open_level_detail)
        main_layout.addWidget(self.level_detail_btn)

        # 안내 메시지
        info_label = QLabel(
            "💡 레벨 상세 설정에서 DCA/익절/손절의 세부 레벨을 조정할 수 있습니다."
        )
        info_label.setFont(QFont("맑은 고딕", 8))
        info_label.setStyleSheet("color: #666; padding: 5px;")
        info_label.setWordWrap(True)
        main_layout.addWidget(info_label)

        main_layout.addStretch()

        # ========================================
        # 하단 버튼
        # ========================================
        button_layout = QHBoxLayout()

        save_btn = QPushButton("💾 저장")
        save_btn.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        save_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 12px; min-width: 100px;")
        save_btn.clicked.connect(self._save_settings)
        button_layout.addWidget(save_btn)

        cancel_btn = QPushButton("취소")
        cancel_btn.setFont(QFont("맑은 고딕", 10))
        cancel_btn.setStyleSheet("padding: 12px; min-width: 100px;")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        main_layout.addLayout(button_layout)

        # 기본값: 자동매수 선택
        self.auto_buy_radio.setChecked(True)

    def _apply_preset(self, preset_id: str):
        """프리셋 적용"""
        logger.info(f"📋 프리셋 적용: {preset_id}")

        if preset_id == "auto_auto":
            # 자동매수 + 자동매도
            self.auto_buy_radio.setChecked(True)
            self.dca_checkbox.setChecked(True)
            self.profit_checkbox.setChecked(True)
            self.loss_checkbox.setChecked(True)

        elif preset_id == "auto_manual":
            # 자동매수 + 수동매도
            self.auto_buy_radio.setChecked(True)
            self.dca_checkbox.setChecked(True)
            self.profit_checkbox.setChecked(False)
            self.loss_checkbox.setChecked(False)

        elif preset_id == "manual_auto":
            # 수동매수 + 자동매도
            self.manual_buy_radio.setChecked(True)
            self.dca_checkbox.setChecked(True)
            self.profit_checkbox.setChecked(True)
            self.loss_checkbox.setChecked(True)

    def _on_buy_mode_changed(self):
        """매수 방식 변경 시"""
        is_auto = self.auto_buy_radio.isChecked()
        self.buy_amount_input.setEnabled(is_auto)

    def _load_settings(self):
        """설정 로드"""
        try:
            config = self.config_manager.load_config()
            groups = config.get("groups", {})

            if self.group_id not in groups:
                logger.warning(f"⚠️ 그룹 없음: {self.group_id}")
                return

            group = groups[self.group_id]

            # 매수 설정
            buy_settings = group.get("buy_settings", {})
            buy_amount = buy_settings.get("buy_amount_krw", 50000)
            investment_style = buy_settings.get("investment_style", "balanced")

            # 매수 방식 판단 (investment_style이 "manual"이면 수동)
            if investment_style == "manual":
                self.manual_buy_radio.setChecked(True)
            else:
                self.auto_buy_radio.setChecked(True)

            self.buy_amount_input.setValue(buy_amount)

            # DCA 설정
            dca_settings = group.get("dca_settings", {})
            dca_enabled = dca_settings.get("enabled", True)
            self.dca_checkbox.setChecked(dca_enabled)

            # 익절/손절 설정
            profit_loss_settings = group.get("profit_loss_settings", {})
            profit_targets = profit_loss_settings.get("profit_targets", [])
            stop_losses = profit_loss_settings.get("stop_losses", [])

            self.profit_checkbox.setChecked(len(profit_targets) > 0)
            self.loss_checkbox.setChecked(len(stop_losses) > 0)

            logger.info(f"✅ 그룹 설정 로드: {self.group_id}")

        except Exception as e:
            logger.error(f"❌ 설정 로드 실패: {e}")
            QMessageBox.warning(
                self,
                "경고",
                f"설정을 불러올 수 없습니다.\n기본값을 사용합니다.\n\n{e}"
            )

    def _save_settings(self):
        """설정 저장"""
        try:
            config = self.config_manager.load_config()
            groups = config.get("groups", {})

            if self.group_id not in groups:
                raise ValueError(f"그룹을 찾을 수 없습니다: {self.group_id}")

            group = groups[self.group_id]

            # 매수 설정
            is_auto_buy = self.auto_buy_radio.isChecked()
            buy_amount = self.buy_amount_input.value()

            if is_auto_buy:
                # 자동매수 모드: auto_config 필요
                group["buy_settings"] = {
                    "mode": "auto",
                    "auto_config": {
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
                        "buy_amount_krw": buy_amount
                    }
                }
            else:
                # 수동매수 모드: mode만 필요
                group["buy_settings"] = {
                    "mode": "manual"
                }

            # DCA 설정
            dca_enabled = self.dca_checkbox.isChecked()
            if "dca_settings" not in group:
                group["dca_settings"] = {
                    "enabled": dca_enabled,
                    "levels": [
                        {"price_drop_pct": -3.0, "buy_amount_krw": 50000},
                        {"price_drop_pct": -6.0, "buy_amount_krw": 50000},
                        {"price_drop_pct": -10.0, "buy_amount_krw": 100000}
                    ]
                }
            else:
                group["dca_settings"]["enabled"] = dca_enabled

            # 익절/손절 설정
            profit_enabled = self.profit_checkbox.isChecked()
            loss_enabled = self.loss_checkbox.isChecked()

            if "profit_loss_settings" not in group:
                group["profit_loss_settings"] = {
                    "profit_targets": [],
                    "stop_losses": []
                }

            # 익절 기본값 (사용 안 함 → 사용으로 전환 시)
            if profit_enabled and len(group["profit_loss_settings"].get("profit_targets", [])) == 0:
                group["profit_loss_settings"]["profit_targets"] = [
                    {"price_ratio": 1.05, "quantity_ratio": 0.5},
                    {"price_ratio": 1.10, "quantity_ratio": 1.0}
                ]
            elif not profit_enabled:
                group["profit_loss_settings"]["profit_targets"] = []

            # 손절 기본값 (사용 안 함 → 사용으로 전환 시)
            if loss_enabled and len(group["profit_loss_settings"].get("stop_losses", [])) == 0:
                group["profit_loss_settings"]["stop_losses"] = [
                    {"price_ratio": 0.95, "quantity_ratio": 1.0}
                ]
            elif not loss_enabled:
                group["profit_loss_settings"]["stop_losses"] = []

            # 저장
            self.config_manager.save_config(config)

            logger.info(f"✅ 그룹 설정 저장: {self.group_id}")

            QMessageBox.information(
                self,
                "저장 완료",
                f"그룹 \"{self.group_name}\"의 설정이 저장되었습니다."
            )

            # 시그널 발생
            self.settings_saved.emit()

            self.accept()

        except Exception as e:
            logger.error(f"❌ 설정 저장 실패: {e}")
            QMessageBox.critical(
                self,
                "오류",
                f"설정을 저장할 수 없습니다.\n{e}"
            )

    def _open_level_detail(self):
        """레벨 상세 설정 다이얼로그 열기"""
        # TODO: Phase 3 Step 4에서 LevelSettingsDialog 구현
        QMessageBox.information(
            self,
            "레벨 상세 설정",
            f"레벨 상세 설정 다이얼로그는 Phase 3 Step 4에서 구현 예정입니다.\n\n"
            f"현재 그룹: {self.group_name}\n\n"
            "설정 항목:\n"
            "- DCA 레벨 (하락률, 주문금액)\n"
            "- 익절 레벨 (수익률, 매도비율)\n"
            "- 손절 레벨 (손실률, 매도비율)",
            QMessageBox.Ok
        )


# 테스트 코드
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    from core.config_manager import ConfigManager

    app = QApplication(sys.argv)

    # 테스트용 매니저 생성
    config_mgr = ConfigManager()

    dialog = GroupSettingsDialog(config_mgr, "group_1", "테스트 그룹")
    dialog.exec()

    sys.exit(app.exec())
