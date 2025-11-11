"""
Coin Selection Dialog - 코인 선택 다이얼로그
거래할 코인을 체크박스로 선택하는 다이얼로그
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QCheckBox,
    QPushButton, QLabel, QGroupBox, QScrollArea, QWidget, QMessageBox, QLineEdit
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class CoinSelectionDialog(QDialog):
    """
    코인 선택 다이얼로그

    여러 코인 중에서 거래할 코인을 체크박스로 선택합니다.
    선택된 코인만 MultiCoinTrader에서 감시하고 전략을 적용합니다.
    """

    # 시그널 정의
    coins_changed = Signal(list)  # 코인 선택이 변경되면 발생 (선택된 코인 리스트 전달)

    # 상장폐지 또는 제외할 코인 블랙리스트
    BLACKLIST = [
        'KRW-MATIC',  # 상장폐지
        # 추가 제외 코인이 있으면 여기에 추가
    ]

    def __init__(self, parent=None, selected_coins: List[str] = None, upbit_api=None):
        """
        코인 선택 다이얼로그 초기화

        Args:
            parent: 부모 위젯
            selected_coins: 현재 선택된 코인 리스트 (예: ['KRW-BTC', 'KRW-ETH'])
            upbit_api: UpbitAPI 인스턴스 (마켓 목록 조회용)
        """
        super().__init__(parent)

        # 기본값 설정 (아무것도 선택 안 됨)
        if selected_coins is None:
            selected_coins = []

        self.selected_coins = selected_coins.copy()  # 복사본 생성
        self.checkboxes = {}  # {심볼: QCheckBox}
        self.upbit_api = upbit_api

        # 동적으로 코인 목록 로드
        self.all_coins = []  # 사용 가능한 모든 KRW 마켓
        self.coin_names = {}  # {심볼: 한글명}
        self._load_market_list()

        self.setWindowTitle("🎯 거래할 코인 선택")
        self.setMinimumSize(500, 400)
        self.setModal(True)  # 모달 다이얼로그 (다른 창 조작 불가)

        self._init_ui()

    def _load_market_list(self):
        """
        Upbit API에서 마켓 목록을 동적으로 로드

        KRW 마켓만 필터링하고, 블랙리스트 코인 제외
        """
        if self.upbit_api is None:
            logger.warning("⚠️ UpbitAPI 인스턴스가 없어서 기본 코인 목록 사용")
            # Fallback: 기본 코인 목록
            self.all_coins = [
                'KRW-BTC', 'KRW-ETH', 'KRW-XRP', 'KRW-SOL',
                'KRW-DOGE', 'KRW-USDT', 'KRW-ADA', 'KRW-AVAX'
            ]
            self.coin_names = {
                'KRW-BTC': 'Bitcoin (비트코인)',
                'KRW-ETH': 'Ethereum (이더리움)',
                'KRW-XRP': 'Ripple (리플)',
                'KRW-SOL': 'Solana (솔라나)',
                'KRW-DOGE': 'Dogecoin (도지코인)',
                'KRW-USDT': 'Tether (테더)',
                'KRW-ADA': 'Cardano (에이다)',
                'KRW-AVAX': 'Avalanche (아발란체)',
            }
            return

        try:
            # Upbit API로 전체 마켓 목록 조회
            markets = self.upbit_api.get_market_all(is_details=True)

            if not markets:
                logger.warning("⚠️ 마켓 목록 조회 실패, 기본 목록 사용")
                self._load_market_list()  # Fallback 호출
                return

            # KRW 마켓만 필터링 (블랙리스트 제외)
            for market in markets:
                symbol = market.get('market', '')
                korean_name = market.get('korean_name', '')
                english_name = market.get('english_name', '')
                market_warning = market.get('market_warning', 'NONE')

                # KRW 마켓만
                if not symbol.startswith('KRW-'):
                    continue

                # 블랙리스트 제외
                if symbol in self.BLACKLIST:
                    logger.info(f"⛔ {symbol}: 스킵 리스트에 추가 (상장폐지)")
                    continue

                # 유의종목 제외 (선택사항)
                # if market_warning == "CAUTION":
                #     logger.info(f"⚠️ {symbol}: 유의종목 제외")
                #     continue

                # 추가
                self.all_coins.append(symbol)
                self.coin_names[symbol] = f"{english_name} ({korean_name})"

            # 심볼 기준 정렬 (BTC, ETH, ... 순서)
            self.all_coins.sort()

            logger.info(f"✅ KRW 마켓 {len(self.all_coins)}개 로드 완료")

        except Exception as e:
            logger.error(f"❌ 마켓 목록 로드 실패: {e}")
            # Fallback 재귀 호출 방지를 위해 직접 설정
            self.upbit_api = None
            self._load_market_list()

    def _init_ui(self):
        """UI 초기화"""
        main_layout = QVBoxLayout(self)

        # 상단: 안내 메시지
        header_label = QLabel(
            "<h2>🎯 거래할 코인을 선택하세요</h2>"
            "<p>체크된 코인만 감시하고 전략을 적용합니다.</p>"
            f"<p style='color: #666;'>전체 {len(self.all_coins)}개 KRW 마켓 중 선택 가능</p>"
        )
        header_label.setWordWrap(True)
        main_layout.addWidget(header_label)

        # 검색창
        search_layout = QHBoxLayout()
        search_label = QLabel("🔍 검색:")
        search_label.setFont(QFont("맑은 고딕", 9))
        search_layout.addWidget(search_label)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("코인 심볼 또는 이름으로 검색... (예: BTC, 비트코인)")
        self.search_edit.setFont(QFont("맑은 고딕", 9))
        self.search_edit.textChanged.connect(self._filter_coins)
        search_layout.addWidget(self.search_edit)

        main_layout.addLayout(search_layout)

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
        for symbol in self.all_coins:
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
        coin_name = self.coin_names.get(symbol, symbol)
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

    def _filter_coins(self):
        """검색어에 따라 코인 필터링"""
        search_text = self.search_edit.text().strip().upper()

        # 검색어가 비어있으면 모두 표시
        if not search_text:
            for checkbox in self.checkboxes.values():
                checkbox.setVisible(True)
            return

        # 검색어와 일치하는 항목만 표시
        for symbol, checkbox in self.checkboxes.items():
            # 심볼명 검색 (예: "BTC" 입력 시 "KRW-BTC" 매칭)
            symbol_match = search_text in symbol.upper()

            # 한글명/영문명 검색 (예: "비트" 입력 시 "비트코인" 매칭)
            coin_name = self.coin_names.get(symbol, "").upper()
            name_match = search_text in coin_name

            # 둘 중 하나라도 매칭되면 표시
            checkbox.setVisible(symbol_match or name_match)

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

        # 확인 메시지
        coins_str = ", ".join([symbol.replace('KRW-', '') for symbol in self.selected_coins[:10]])
        if len(self.selected_coins) > 10:
            coins_str += f", ... 외 {len(self.selected_coins) - 10}개"

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

    # 테스트: 기본 선택값 전달 (upbit_api=None이면 fallback 리스트 사용)
    dialog = CoinSelectionDialog(
        selected_coins=['KRW-BTC', 'KRW-ETH', 'KRW-XRP'],
        upbit_api=None  # 실제 사용 시에는 UpbitAPI 인스턴스 전달
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
