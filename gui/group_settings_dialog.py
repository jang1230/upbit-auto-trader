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
            buy_mode = buy_settings.get("mode", "manual")

            # 매수 금액 로드
            if buy_mode == "auto":
                # 자동 모드: auto_config에서 로드
                auto_config = buy_settings.get("auto_config", {})
                buy_amount = auto_config.get("buy_amount_krw", 50000)
                self.auto_buy_radio.setChecked(True)
            else:
                # 수동 모드: buy_settings에서 직접 로드
                buy_amount = buy_settings.get("buy_amount_krw", 50000)
                self.manual_buy_radio.setChecked(True)

            self.buy_amount_input.setValue(buy_amount)

            # DCA 설정
            dca_settings = group.get("dca_settings", {})
            dca_mode = dca_settings.get("mode", "disabled")
            self.dca_checkbox.setChecked(dca_mode == "auto")

            # 익절 설정
            profit_settings = group.get("profit_settings", {})
            profit_mode = profit_settings.get("mode", "disabled")
            self.profit_checkbox.setChecked(profit_mode in ["auto", "alert"])

            # 손절 설정
            loss_settings = group.get("loss_settings", {})
            loss_mode = loss_settings.get("mode", "disabled")
            self.loss_checkbox.setChecked(loss_mode in ["auto", "alert"])

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
                # 수동매수 모드: mode + 매수금액 저장
                group["buy_settings"] = {
                    "mode": "manual",
                    "buy_amount_krw": buy_amount
                }

            # DCA 설정
            dca_enabled = self.dca_checkbox.isChecked()
            if "dca_settings" not in group:
                group["dca_settings"] = {"mode": "disabled"}

            if dca_enabled:
                group["dca_settings"]["mode"] = "auto"
                # 기본 레벨이 없으면 생성
                if "levels" not in group["dca_settings"] or len(group["dca_settings"]["levels"]) == 0:
                    group["dca_settings"]["levels"] = [
                        {"price_ratio": -3.0, "quantity_ratio": 100},
                        {"price_ratio": -5.0, "quantity_ratio": 100},
                        {"price_ratio": -7.0, "quantity_ratio": 100}
                    ]
            else:
                group["dca_settings"]["mode"] = "disabled"

            # 익절/손절 설정
            profit_enabled = self.profit_checkbox.isChecked()
            loss_enabled = self.loss_checkbox.isChecked()

            # 익절 설정
            if "profit_settings" not in group:
                group["profit_settings"] = {"mode": "disabled"}

            if profit_enabled:
                group["profit_settings"]["mode"] = "auto"
                # 기본 레벨이 없으면 생성
                if "levels" not in group["profit_settings"] or len(group["profit_settings"]["levels"]) == 0:
                    group["profit_settings"]["levels"] = [
                        {"price_ratio": 5.0, "quantity_ratio": 50},
                        {"price_ratio": 10.0, "quantity_ratio": 50}
                    ]
            else:
                group["profit_settings"]["mode"] = "disabled"

            # 손절 설정
            if "loss_settings" not in group:
                group["loss_settings"] = {"mode": "disabled"}

            if loss_enabled:
                group["loss_settings"]["mode"] = "auto"
                # 기본 레벨이 없으면 생성
                if "levels" not in group["loss_settings"] or len(group["loss_settings"]["levels"]) == 0:
                    group["loss_settings"]["levels"] = [
                        {"price_ratio": -15.0, "quantity_ratio": 100}
                    ]
            else:
                group["loss_settings"]["mode"] = "disabled"

            # V3 호환성: 옛날 필드 삭제
            group.pop("observation_mode", None)
            group.pop("profit_loss_settings", None)
            if "dca_settings" in group:
                group["dca_settings"].pop("enabled", None)

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
        try:
            from gui.level_settings_dialog import LevelSettingsDialog

            dialog = LevelSettingsDialog(
                self.config_manager,
                self.group_id,
                self.group_name,
                parent=self
            )
            dialog.settings_saved.connect(self._on_level_settings_saved)
            dialog.exec()

        except Exception as e:
            logger.error(f"❌ 레벨 상세 설정 다이얼로그 오류: {e}")
            QMessageBox.critical(
                self,
                "오류",
                f"레벨 상세 설정 다이얼로그를 열 수 없습니다.\n{e}"
            )

    def _on_level_settings_saved(self):
        """레벨 설정 저장 완료 시"""
        logger.info("✅ 레벨 설정 저장 완료")
        # 설정 파일이 변경되었으므로 상위 다이얼로그에 알림
        self.settings_saved.emit()


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
