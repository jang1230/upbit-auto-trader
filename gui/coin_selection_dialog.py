"""
Coin Selection Dialog - 코인 선택 다이얼로그
거래할 코인을 체크박스로 선택하는 다이얼로그
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QCheckBox,
    QPushButton, QLabel, QGroupBox, QScrollArea, QWidget, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from typing import List


class CoinSelectionDialog(QDialog):
    """
    코인 선택 다이얼로그

    여러 코인 중에서 거래할 코인을 체크박스로 선택합니다.
    선택된 코인만 MultiCoinTrader에서 감시하고 전략을 적용합니다.
    """

    # 시그널 정의
    coins_changed = Signal(list)  # 코인 선택이 변경되면 발생 (선택된 코인 리스트 전달)

    # 사용 가능한 모든 코인 리스트 (나중에 확장 가능)
    ALL_COINS = [
        'KRW-BTC',
        'KRW-ETH',
        'KRW-XRP',
        'KRW-SOL',
        'KRW-DOGE',
        'KRW-USDT',
        # 나중에 추가 가능
        # 'KRW-ADA',
        # 'KRW-AVAX',
        # 'KRW-MATIC',
        # 'KRW-DOT',
    ]

    # 코인 이름 매핑 (한글 표시용)
    COIN_NAMES = {
        'KRW-BTC': 'Bitcoin (비트코인)',
        'KRW-ETH': 'Ethereum (이더리움)',
        'KRW-XRP': 'Ripple (리플)',
        'KRW-SOL': 'Solana (솔라나)',
        'KRW-DOGE': 'Dogecoin (도지코인)',
        'KRW-USDT': 'Tether (테더)',
    }

    def __init__(self, parent=None, selected_coins: List[str] = None):
        """
        코인 선택 다이얼로그 초기화

        Args:
            parent: 부모 위젯
            selected_coins: 현재 선택된 코인 리스트 (예: ['KRW-BTC', 'KRW-ETH'])
        """
        super().__init__(parent)

        # 기본값 설정 (아무것도 선택 안 됨)
        if selected_coins is None:
            selected_coins = []

        self.selected_coins = selected_coins.copy()  # 복사본 생성
        self.checkboxes = {}  # {심볼: QCheckBox}

        self.setWindowTitle("🎯 거래할 코인 선택")
        self.setMinimumSize(500, 400)
        self.setModal(True)  # 모달 다이얼로그 (다른 창 조작 불가)

        self._init_ui()

    def _init_ui(self):
        """UI 초기화"""
        main_layout = QVBoxLayout(self)

        # 상단: 안내 메시지
        header_label = QLabel(
            "<h2>🎯 거래할 코인을 선택하세요</h2>"
            "<p>체크된 코인만 감시하고 전략을 적용합니다.</p>"
            "<p style='color: #666;'>최소 1개, 최대 6개까지 선택 가능합니다.</p>"
        )
        header_label.setWordWrap(True)
        main_layout.addWidget(header_label)

        # 중단: 코인 선택 체크박스 (스크롤 가능)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # 코인 그룹박스
        coins_group = QGroupBox("사용 가능한 코인")
        coins_layout = QVBoxLayout()

        # 각 코인에 대한 체크박스 생성
        for symbol in self.ALL_COINS:
            checkbox = QCheckBox(self._get_coin_display_name(symbol))
            checkbox.setFont(QFont("맑은 고딕", 10))

            # 현재 선택된 코인이면 체크
            if symbol in self.selected_coins:
                checkbox.setChecked(True)

            # 체크박스 상태 변경 시그널 연결
            checkbox.stateChanged.connect(self._on_checkbox_changed)

            # 저장
            self.checkboxes[symbol] = checkbox
            coins_layout.addWidget(checkbox)

        coins_group.setLayout(coins_layout)
        scroll_layout.addWidget(coins_group)
        scroll_layout.addStretch()

        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)

        # 하단: 선택 정보 및 버튼
        info_layout = QHBoxLayout()

        self.selection_info_label = QLabel(self._get_selection_info())
        self.selection_info_label.setFont(QFont("맑은 고딕", 9))
        self.selection_info_label.setStyleSheet("color: #666;")
        info_layout.addWidget(self.selection_info_label)
        info_layout.addStretch()

        main_layout.addLayout(info_layout)

        # 버튼 레이아웃
        button_layout = QHBoxLayout()

        # 전체 선택/해제 버튼
        select_all_btn = QPushButton("✅ 전체 선택")
        select_all_btn.clicked.connect(self._select_all)
        button_layout.addWidget(select_all_btn)

        deselect_all_btn = QPushButton("❌ 전체 해제")
        deselect_all_btn.clicked.connect(self._deselect_all)
        button_layout.addWidget(deselect_all_btn)

        button_layout.addStretch()

        # 저장/취소 버튼
        save_btn = QPushButton("💾 저장")
        save_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px; font-weight: bold;")
        save_btn.clicked.connect(self._save_and_close)
        button_layout.addWidget(save_btn)

        cancel_btn = QPushButton("🚫 취소")
        cancel_btn.setStyleSheet("background-color: #999; color: white; padding: 10px;")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        main_layout.addLayout(button_layout)

    def _get_coin_display_name(self, symbol: str) -> str:
        """
        코인 심볼을 표시용 이름으로 변환

        Args:
            symbol: 코인 심볼 (예: 'KRW-BTC')

        Returns:
            str: 표시용 이름 (예: 'KRW-BTC - Bitcoin (비트코인)')
        """
        coin_name = self.COIN_NAMES.get(symbol, symbol)
        return f"{symbol} - {coin_name}"

    def _get_selection_info(self) -> str:
        """선택 정보 텍스트 생성"""
        count = len(self.selected_coins)
        if count == 0:
            return "⚠️ 코인이 선택되지 않았습니다 (최소 1개 필요)"
        else:
            coins_str = ", ".join([symbol.replace('KRW-', '') for symbol in self.selected_coins])
            return f"✅ {count}개 선택됨: {coins_str}"

    def _on_checkbox_changed(self):
        """체크박스 상태 변경 시 호출"""
        # 현재 선택된 코인 리스트 업데이트
        self.selected_coins = [
            symbol for symbol, checkbox in self.checkboxes.items()
            if checkbox.isChecked()
        ]

        # 선택 정보 업데이트
        self.selection_info_label.setText(self._get_selection_info())

    def _select_all(self):
        """전체 선택"""
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(True)

    def _deselect_all(self):
        """전체 해제"""
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(False)

    def _save_and_close(self):
        """저장하고 닫기"""
        # 검증: 최소 1개 선택 필요
        if len(self.selected_coins) == 0:
            QMessageBox.warning(
                self,
                "선택 필요",
                "⚠️ 최소 1개 이상의 코인을 선택해야 합니다."
            )
            return

        # 검증: 최대 6개까지
        if len(self.selected_coins) > 6:
            QMessageBox.warning(
                self,
                "선택 초과",
                f"⚠️ 최대 6개까지만 선택할 수 있습니다.\n현재 {len(self.selected_coins)}개 선택됨"
            )
            return

        # 확인 메시지
        coins_str = ", ".join([symbol.replace('KRW-', '') for symbol in self.selected_coins])
        reply = QMessageBox.question(
            self,
            "코인 선택 저장",
            f"선택한 코인을 저장하시겠습니까?\n\n"
            f"선택된 코인 ({len(self.selected_coins)}개):\n{coins_str}\n\n"
            f"이 코인들만 감시하고 전략을 적용합니다.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )

        if reply == QMessageBox.Yes:
            # 시그널 발생 (MainWindow에서 받음)
            self.coins_changed.emit(self.selected_coins)

            # 다이얼로그 닫기 (성공)
            self.accept()

    def get_selected_coins(self) -> List[str]:
        """
        선택된 코인 리스트 반환

        Returns:
            List[str]: 선택된 코인 심볼 리스트
        """
        return self.selected_coins.copy()


# 테스트 코드
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # 테스트: 기본 선택값 전달
    dialog = CoinSelectionDialog(
        selected_coins=['KRW-BTC', 'KRW-ETH', 'KRW-XRP']
    )

    # 시그널 연결 (테스트)
    def on_coins_changed(coins):
        print(f"선택된 코인: {coins}")

    dialog.coins_changed.connect(on_coins_changed)

    # 다이얼로그 실행
    result = dialog.exec()

    if result == QDialog.Accepted:
        print(f"✅ 저장됨: {dialog.get_selected_coins()}")
    else:
        print("❌ 취소됨")

    sys.exit(0)
