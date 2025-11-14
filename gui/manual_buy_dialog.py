"""
ManualBuyDialog - 수동 매수 다이얼로그

Manual 모드 그룹에서 사용하는 간단한 매수 다이얼로그
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLabel, QSpinBox, QComboBox, QMessageBox,
    QGroupBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class ManualBuyDialog(QDialog):
    """
    수동 매수 다이얼로그

    Manual 모드 그룹에서 코인을 선택하고 매수 금액을 입력하여 주문
    """

    def __init__(
        self,
        group_name: str,
        coins: List[str],
        default_amount: int,
        upbit_api=None,
        dry_run: bool = False,
        parent=None
    ):
        """
        Args:
            group_name: 그룹 이름
            coins: 그룹의 코인 목록 (예: ["KRW-BTC", "KRW-ETH"])
            default_amount: 기본 매수 금액
            upbit_api: Upbit API 인스턴스
            dry_run: Dry-run 모드 여부
            parent: 부모 위젯
        """
        super().__init__(parent)

        self.group_name = group_name
        self.coins = coins
        self.default_amount = default_amount
        self.upbit_api = upbit_api
        self.dry_run = dry_run

        # 현재가 캐시
        self.current_prices = {}

        self.setWindowTitle(f"💰 수동 매수: {group_name}")
        self.setMinimumWidth(500)
        self.setMinimumHeight(350)

        self._init_ui()
        self._load_initial_prices()

        # 가격 자동 업데이트 (10초마다)
        self.price_update_timer = QTimer(self)
        self.price_update_timer.timeout.connect(self._update_current_price)
        self.price_update_timer.start(10000)  # 10초

    def _init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # === 1. 그룹 정보 ===
        info_label = QLabel(f"📊 그룹: <b>{self.group_name}</b> (Manual 모드)")
        info_label.setFont(QFont("맑은 고딕", 10))
        layout.addWidget(info_label)

        if self.dry_run:
            dry_run_label = QLabel("⚠️ <b>Dry-run 모드</b> - 실제 주문이 실행되지 않습니다")
            dry_run_label.setStyleSheet("color: #FF9800; font-size: 10px;")
            layout.addWidget(dry_run_label)

        # === 2. 코인 선택 그룹 ===
        coin_group = self._create_coin_selection_group()
        layout.addWidget(coin_group)

        # === 3. 매수 금액 그룹 ===
        amount_group = self._create_amount_group()
        layout.addWidget(amount_group)

        # === 4. 예상 수량 표시 ===
        self.estimated_quantity_label = QLabel("예상 수량: -")
        self.estimated_quantity_label.setFont(QFont("맑은 고딕", 10))
        self.estimated_quantity_label.setStyleSheet("color: #2196F3; padding: 10px;")
        layout.addWidget(self.estimated_quantity_label)

        # Spacer
        layout.addStretch()

        # === 5. 버튼 ===
        button_layout = self._create_button_layout()
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def _create_coin_selection_group(self) -> QGroupBox:
        """
        코인 선택 그룹 생성

        Returns:
            코인 선택 QGroupBox
        """
        group = QGroupBox("🪙 매수할 코인 선택")
        group.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        layout = QFormLayout()

        # 코인 선택 ComboBox
        self.coin_combo = QComboBox()
        self.coin_combo.setFont(QFont("맑은 고딕", 10))
        self.coin_combo.addItems(self.coins)
        self.coin_combo.currentTextChanged.connect(self._on_coin_changed)
        layout.addRow("코인:", self.coin_combo)

        # 현재가 표시
        self.current_price_label = QLabel("조회 중...")
        self.current_price_label.setFont(QFont("맑은 고딕", 11, QFont.Bold))
        self.current_price_label.setStyleSheet("color: #2196F3;")
        layout.addRow("현재가:", self.current_price_label)

        group.setLayout(layout)
        return group

    def _create_amount_group(self) -> QGroupBox:
        """
        매수 금액 그룹 생성

        Returns:
            매수 금액 QGroupBox
        """
        group = QGroupBox("💰 매수 금액")
        group.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        layout = QFormLayout()

        # 매수 금액 입력
        self.amount_spin = QSpinBox()
        self.amount_spin.setRange(5000, 100000000)
        self.amount_spin.setSingleStep(5000)
        self.amount_spin.setSuffix(" 원")
        self.amount_spin.setValue(self.default_amount)
        self.amount_spin.setFont(QFont("맑은 고딕", 10))
        self.amount_spin.valueChanged.connect(self._update_estimated_quantity)
        layout.addRow("매수 금액:", self.amount_spin)

        # 안내 문구
        info_label = QLabel(
            "최소 5,000원 이상 입력해주세요.\n"
            "실제 매수 가능 여부는 계좌 잔고에 따라 달라집니다."
        )
        info_label.setStyleSheet("color: #666; font-size: 9px;")
        info_label.setWordWrap(True)
        layout.addRow("", info_label)

        group.setLayout(layout)
        return group

    def _create_button_layout(self) -> QHBoxLayout:
        """버튼 레이아웃 생성"""
        layout = QHBoxLayout()
        layout.addStretch()

        # 취소 버튼
        cancel_btn = QPushButton("❌ 취소")
        cancel_btn.setFont(QFont("맑은 고딕", 10))
        cancel_btn.setFixedWidth(120)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)

        # 매수 버튼
        self.buy_btn = QPushButton("💰 매수 실행")
        self.buy_btn.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        self.buy_btn.setFixedWidth(120)
        self.buy_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
            }
        """)
        self.buy_btn.clicked.connect(self._execute_buy)
        layout.addWidget(self.buy_btn)

        return layout

    def _load_initial_prices(self):
        """초기 가격 로드"""
        if not self.coins:
            return

        # 첫 번째 코인의 가격 로드
        selected_coin = self.coin_combo.currentText()
        if selected_coin:
            self._update_current_price()

    def _on_coin_changed(self, coin: str):
        """코인 선택 변경 시 호출"""
        if coin:
            self._update_current_price()

    def _update_current_price(self):
        """현재가 업데이트"""
        selected_coin = self.coin_combo.currentText()
        if not selected_coin:
            return

        try:
            if self.upbit_api is None:
                self.current_price_label.setText("API 없음")
                return

            # Upbit API로 현재가 조회
            ticker = self.upbit_api.get_ticker(selected_coin)
            if ticker and 'trade_price' in ticker:
                current_price = ticker['trade_price']
                self.current_prices[selected_coin] = current_price

                # 가격 포맷팅
                if current_price >= 1000:
                    price_str = f"{current_price:,.0f} 원"
                elif current_price >= 1:
                    price_str = f"{current_price:,.2f} 원"
                else:
                    price_str = f"{current_price:.4f} 원"

                self.current_price_label.setText(price_str)
                self._update_estimated_quantity()
            else:
                self.current_price_label.setText("조회 실패")
                logger.warning(f"현재가 조회 실패: {selected_coin}")

        except Exception as e:
            logger.error(f"현재가 업데이트 실패: {e}")
            self.current_price_label.setText("오류")

    def _update_estimated_quantity(self):
        """예상 수량 업데이트"""
        selected_coin = self.coin_combo.currentText()
        buy_amount = self.amount_spin.value()

        if selected_coin not in self.current_prices:
            self.estimated_quantity_label.setText("예상 수량: -")
            return

        current_price = self.current_prices[selected_coin]
        if current_price <= 0:
            self.estimated_quantity_label.setText("예상 수량: -")
            return

        # 수수료 0.05% 고려
        fee_rate = 0.0005
        estimated_quantity = (buy_amount * (1 - fee_rate)) / current_price

        self.estimated_quantity_label.setText(f"예상 수량: <b>{estimated_quantity:.8f}</b> (수수료 제외)")

    def _execute_buy(self):
        """매수 실행"""
        selected_coin = self.coin_combo.currentText()
        buy_amount = self.amount_spin.value()

        if not selected_coin:
            QMessageBox.warning(self, "입력 오류", "코인을 선택해주세요.")
            return

        if buy_amount < 5000:
            QMessageBox.warning(self, "입력 오류", "매수 금액은 최소 5,000원 이상이어야 합니다.")
            return

        if selected_coin not in self.current_prices:
            QMessageBox.warning(self, "가격 오류", "현재가를 조회할 수 없습니다. 잠시 후 다시 시도해주세요.")
            return

        # 확인 메시지
        current_price = self.current_prices[selected_coin]
        estimated_quantity = (buy_amount * 0.9995) / current_price

        msg = (
            f"<b>{selected_coin}</b>을(를) 매수하시겠습니까?\n\n"
            f"• 매수 금액: {buy_amount:,} 원\n"
            f"• 현재가: {current_price:,.4f} 원\n"
            f"• 예상 수량: {estimated_quantity:.8f}\n\n"
        )

        if self.dry_run:
            msg += "⚠️ <b>Dry-run 모드</b>이므로 실제 주문이 실행되지 않습니다."
        else:
            msg += "⚠️ <b>실제 주문이 실행됩니다!</b>"

        reply = QMessageBox.question(
            self,
            "매수 확인",
            msg,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        # 매수 실행
        try:
            if self.dry_run:
                # Dry-run 모드: 가상 주문만 기록
                logger.info(f"[Dry-run] 수동 매수: {selected_coin}, {buy_amount:,}원")
                QMessageBox.information(
                    self,
                    "매수 완료 (Dry-run)",
                    f"Dry-run 모드에서 매수가 기록되었습니다.\n\n"
                    f"• 코인: {selected_coin}\n"
                    f"• 금액: {buy_amount:,} 원"
                )
            else:
                # 실제 주문 실행
                if self.upbit_api is None:
                    raise ValueError("Upbit API가 설정되지 않았습니다.")

                result = self.upbit_api.buy_market_order(selected_coin, buy_amount)

                if result and 'uuid' in result:
                    logger.info(f"✅ 수동 매수 성공: {selected_coin}, {buy_amount:,}원, UUID: {result['uuid']}")
                    QMessageBox.information(
                        self,
                        "매수 완료",
                        f"매수 주문이 성공적으로 실행되었습니다.\n\n"
                        f"• 코인: {selected_coin}\n"
                        f"• 금액: {buy_amount:,} 원\n"
                        f"• 주문 UUID: {result['uuid']}"
                    )
                else:
                    raise ValueError("주문 결과에 UUID가 없습니다.")

            # 성공 시 다이얼로그 닫기
            self.accept()

        except Exception as e:
            logger.error(f"❌ 수동 매수 실패: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "매수 실패",
                f"매수 중 오류가 발생했습니다:\n\n{str(e)}"
            )

    def closeEvent(self, event):
        """다이얼로그 닫을 때 타이머 정리"""
        if hasattr(self, 'price_update_timer'):
            self.price_update_timer.stop()
        super().closeEvent(event)


if __name__ == "__main__":
    """독립 실행 테스트"""
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # 테스트용 다이얼로그
    test_coins = ["KRW-BTC", "KRW-ETH", "KRW-XRP"]
    dialog = ManualBuyDialog(
        group_name="테스트 그룹",
        coins=test_coins,
        default_amount=50000,
        upbit_api=None,  # 실제로는 UpbitAPI 인스턴스 전달
        dry_run=True
    )

    if dialog.exec():
        print("매수 실행됨")
    else:
        print("매수 취소됨")

    sys.exit(app.exec())
