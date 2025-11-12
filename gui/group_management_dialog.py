"""
그룹 관리 다이얼로그
V4 그룹 시스템의 그룹 생성/삭제/수정 UI
"""

import logging
from typing import Optional, Dict, List

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget,
    QPushButton, QLabel, QLineEdit, QCheckBox,
    QListWidget, QListWidgetItem, QGroupBox,
    QMessageBox, QScrollArea, QSplitter
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

logger = logging.getLogger(__name__)


class GroupManagementDialog(QDialog):
    """
    그룹 관리 다이얼로그

    마스터-디테일 패턴:
    - 왼쪽: 그룹 목록
    - 오른쪽: 선택된 그룹 상세 정보
    """

    # 시그널: 그룹 변경 완료 (메인 윈도우에서 새로고침용)
    groups_changed = Signal()

    def __init__(self, config_manager, group_manager, parent=None, is_trading_running=False, upbit_api=None):
        """
        Args:
            config_manager: ConfigManager 인스턴스
            group_manager: GroupManager 인스턴스
            parent: 부모 위젯
            is_trading_running: 거래 실행 중 여부
            upbit_api: UpbitAPI 인스턴스 (마켓 목록 조회용)
        """
        super().__init__(parent)

        self.config_manager = config_manager
        self.group_manager = group_manager
        self.is_trading_running = is_trading_running  # 거래 실행 상태
        self.upbit_api = upbit_api

        # 현재 선택된 그룹 ID
        self.selected_group_id: Optional[str] = None

        # UI 컴포넌트
        self.group_list_widget = None
        self.group_name_edit = None
        self.observation_checkbox = None
        self.coin_checkboxes: Dict[str, QCheckBox] = {}
        self.settings_btn = None
        self.save_btn = None
        self.delete_btn = None

        self._init_ui()
        self._load_groups()

    def _init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("그룹 관리")
        self.resize(900, 650)  # 700x600보다 약간 크게 (여유 공간)

        # 메인 레이아웃
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # 스플리터 생성 (좌우 분할)
        splitter = QSplitter(Qt.Horizontal)

        # ========================================
        # 왼쪽 패널: 그룹 목록
        # ========================================
        left_panel = self._create_group_list_panel()
        splitter.addWidget(left_panel)

        # ========================================
        # 오른쪽 패널: 그룹 상세
        # ========================================
        right_panel = self._create_group_detail_panel()
        splitter.addWidget(right_panel)

        # 스플리터 비율 설정 (왼쪽:오른쪽 = 1:3)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        main_layout.addWidget(splitter)

    def _create_group_list_panel(self) -> QWidget:
        """그룹 목록 패널 생성"""
        panel = QWidget()
        panel.setMaximumWidth(220)
        panel.setMinimumWidth(180)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        # 타이틀
        title_label = QLabel("그룹 목록")
        title_label.setFont(QFont("맑은 고딕", 11, QFont.Bold))
        layout.addWidget(title_label)

        # 그룹 목록 위젯
        self.group_list_widget = QListWidget()
        self.group_list_widget.setFont(QFont("맑은 고딕", 10))
        self.group_list_widget.currentItemChanged.connect(self._on_group_selected)
        layout.addWidget(self.group_list_widget)

        # 새 그룹 버튼
        new_group_btn = QPushButton("+ 새 그룹")
        new_group_btn.setFont(QFont("맑은 고딕", 9, QFont.Bold))
        new_group_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px;")
        new_group_btn.clicked.connect(self._create_new_group)
        layout.addWidget(new_group_btn)

        return panel

    def _create_group_detail_panel(self) -> QWidget:
        """그룹 상세 패널 생성"""
        panel = QWidget()

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 5, 5, 5)
        layout.setSpacing(15)

        # 타이틀
        title_label = QLabel("그룹 상세")
        title_label.setFont(QFont("맑은 고딕", 11, QFont.Bold))
        layout.addWidget(title_label)

        # ========================================
        # 그룹명 입력
        # ========================================
        name_layout = QHBoxLayout()
        name_label = QLabel("그룹명:")
        name_label.setFont(QFont("맑은 고딕", 10))
        name_label.setMinimumWidth(80)
        name_layout.addWidget(name_label)

        self.group_name_edit = QLineEdit()
        self.group_name_edit.setFont(QFont("맑은 고딕", 10))
        self.group_name_edit.setPlaceholderText("그룹 이름을 입력하세요")
        name_layout.addWidget(self.group_name_edit)

        layout.addLayout(name_layout)

        # ========================================
        # 관찰 전용 모드
        # ========================================
        self.observation_checkbox = QCheckBox("관찰 전용 모드 (자동 매수/매도 비활성화)")
        self.observation_checkbox.setFont(QFont("맑은 고딕", 9))
        self.observation_checkbox.setStyleSheet("color: #F44336;")
        layout.addWidget(self.observation_checkbox)

        # ========================================
        # 포함 코인 선택
        # ========================================
        coin_group = QGroupBox("포함 코인")
        coin_group.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        coin_layout = QVBoxLayout(coin_group)
        coin_layout.setSpacing(5)

        # 코인 개수 라벨
        self.coin_count_label = QLabel("0개 선택됨")
        self.coin_count_label.setFont(QFont("맑은 고딕", 9))
        self.coin_count_label.setStyleSheet("color: #666;")
        coin_layout.addWidget(self.coin_count_label)

        # 검색창
        coin_search_layout = QHBoxLayout()
        coin_search_label = QLabel("🔍")
        coin_search_label.setFont(QFont("맑은 고딕", 9))
        coin_search_layout.addWidget(coin_search_label)

        self.coin_search_edit = QLineEdit()
        self.coin_search_edit.setPlaceholderText("검색... (예: BTC, 비트)")
        self.coin_search_edit.setFont(QFont("맑은 고딕", 9))
        self.coin_search_edit.textChanged.connect(self._filter_coins)
        coin_search_layout.addWidget(self.coin_search_edit)

        coin_layout.addLayout(coin_search_layout)

        # 스크롤 가능한 코인 리스트
        coin_scroll = QScrollArea()
        coin_scroll.setWidgetResizable(True)
        coin_scroll.setMaximumHeight(300)

        coin_widget = QWidget()
        self.coin_checkbox_layout = QVBoxLayout(coin_widget)
        self.coin_checkbox_layout.setSpacing(5)
        self.coin_checkbox_layout.setContentsMargins(5, 5, 5, 5)

        # 코인 체크박스는 _load_available_coins()에서 동적 생성

        coin_scroll.setWidget(coin_widget)
        coin_layout.addWidget(coin_scroll)

        layout.addWidget(coin_group)

        # ========================================
        # 하단 버튼들
        # ========================================
        button_layout = QHBoxLayout()

        # 설정 버튼 (그룹 설정 다이얼로그 열기)
        self.settings_btn = QPushButton("⚙️ 레벨 상세 설정")
        self.settings_btn.setFont(QFont("맑은 고딕", 9, QFont.Bold))
        self.settings_btn.setStyleSheet("background-color: #9C27B0; color: white; padding: 10px;")
        self.settings_btn.clicked.connect(self._open_group_settings)
        self.settings_btn.setEnabled(False)  # 그룹 선택 시 활성화
        button_layout.addWidget(self.settings_btn)

        button_layout.addStretch()

        # 저장 버튼
        self.save_btn = QPushButton("💾 저장")
        self.save_btn.setFont(QFont("맑은 고딕", 9, QFont.Bold))
        self.save_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 10px;")
        self.save_btn.clicked.connect(self._save_group)
        self.save_btn.setEnabled(False)
        button_layout.addWidget(self.save_btn)

        # 삭제 버튼
        self.delete_btn = QPushButton("🗑️ 삭제")
        self.delete_btn.setFont(QFont("맑은 고딕", 9, QFont.Bold))
        self.delete_btn.setStyleSheet("background-color: #F44336; color: white; padding: 10px;")
        self.delete_btn.clicked.connect(self._delete_group)
        self.delete_btn.setEnabled(False)
        button_layout.addWidget(self.delete_btn)

        # 취소 버튼
        cancel_btn = QPushButton("취소")
        cancel_btn.setFont(QFont("맑은 고딕", 9))
        cancel_btn.setStyleSheet("padding: 10px;")
        cancel_btn.clicked.connect(self.close)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

        # 초기 상태: 안내 메시지
        self.empty_state_label = QLabel(
            "👈 왼쪽에서 그룹을 선택하거나\n"
            "\"+ 새 그룹\" 버튼을 클릭하세요"
        )
        self.empty_state_label.setFont(QFont("맑은 고딕", 11))
        self.empty_state_label.setStyleSheet("color: #999; padding: 50px;")
        self.empty_state_label.setAlignment(Qt.AlignCenter)
        layout.insertWidget(1, self.empty_state_label)  # 타이틀 다음에 삽입

        # 상세 패널은 처음에 숨김
        self._set_detail_panel_visible(False)

        return panel

    def _set_detail_panel_visible(self, visible: bool):
        """상세 패널 표시/숨김"""
        self.empty_state_label.setVisible(not visible)
        self.group_name_edit.setVisible(visible)
        self.observation_checkbox.setVisible(visible)
        self.coin_count_label.parent().setVisible(visible)  # coin_group

    def _load_groups(self):
        """설정 파일에서 그룹 목록 로드"""
        try:
            config = self.config_manager.load_config()
            groups = config.get("groups", {})

            self.group_list_widget.clear()

            for group_id, group_data in groups.items():
                group_name = group_data.get("name", group_id)

                # 그룹명만 표시 (코인 목록은 상세 패널에서 확인)
                item = QListWidgetItem(group_name)
                item.setData(Qt.UserRole, group_id)  # group_id 저장
                self.group_list_widget.addItem(item)

            logger.info(f"✅ {len(groups)}개 그룹 로드됨")

        except Exception as e:
            logger.error(f"❌ 그룹 로드 실패: {e}")
            QMessageBox.critical(
                self,
                "오류",
                f"그룹 목록을 불러올 수 없습니다.\n{e}"
            )

    def _fetch_available_coins(self) -> List[tuple]:
        """
        Upbit API에서 사용 가능한 코인 목록 조회

        Returns:
            List[tuple]: (symbol, name) 튜플 리스트
                예: [("KRW-BTC", "Bitcoin (비트코인)"), ...]
        """
        if self.upbit_api is None:
            logger.warning("⚠️ UpbitAPI 인스턴스가 없어서 기본 코인 목록 사용")
            # Fallback: 기본 코인 목록
            return [
                ("KRW-BTC", "Bitcoin (비트코인)"),
                ("KRW-ETH", "Ethereum (이더리움)"),
                ("KRW-XRP", "Ripple (리플)"),
                ("KRW-SOL", "Solana (솔라나)"),
                ("KRW-DOGE", "Dogecoin (도지코인)"),
                ("KRW-USDT", "Tether (테더)"),
                ("KRW-ADA", "Cardano (에이다)"),
                ("KRW-AVAX", "Avalanche (아발란체)"),
            ]

        try:
            # Upbit API로 전체 마켓 목록 조회
            markets = self.upbit_api.get_market_all(is_details=True)

            if not markets:
                logger.warning("⚠️ 마켓 목록 조회 실패, 기본 목록 사용")
                return self._fetch_available_coins()  # Fallback 재귀 호출

            # KRW 마켓만 필터링
            available_coins = []
            for market in markets:
                symbol = market.get('market', '')
                korean_name = market.get('korean_name', '')
                english_name = market.get('english_name', '')

                # KRW 마켓만
                if not symbol.startswith('KRW-'):
                    continue

                # 추가
                name = f"{english_name} ({korean_name})"
                available_coins.append((symbol, name))

            # 심볼 기준 정렬
            available_coins.sort(key=lambda x: x[0])

            logger.info(f"✅ KRW 마켓 {len(available_coins)}개 로드 완료")
            return available_coins

        except Exception as e:
            logger.error(f"❌ 마켓 목록 로드 실패: {e}")
            # Fallback 재귀 호출 방지
            self.upbit_api = None
            return self._fetch_available_coins()

    def _load_available_coins(self):
        """사용 가능한 코인 목록 로드 및 체크박스 생성"""
        # 기존 체크박스 제거
        for checkbox in self.coin_checkboxes.values():
            self.coin_checkbox_layout.removeWidget(checkbox)
            checkbox.deleteLater()
        self.coin_checkboxes.clear()

        # Upbit API에서 동적으로 마켓 목록 로드
        available_coins = self._fetch_available_coins()

        # 상장폐지 코인 블랙리스트 (CoinSelectionDialog와 동일)
        blacklist = ['KRW-MATIC']

        # 현재 설정에서 이미 다른 그룹에 할당된 코인 확인
        try:
            config = self.config_manager.load_config()
            groups = config.get("groups", {})

            assigned_coins = {}  # {symbol: group_name}
            for gid, gdata in groups.items():
                if gid == self.selected_group_id:
                    continue  # 현재 그룹은 제외

                for coin in gdata.get("coins", []):
                    assigned_coins[coin] = gdata.get("name", gid)
        except Exception as e:
            logger.warning(f"⚠️ 할당된 코인 확인 실패: {e}")
            assigned_coins = {}

        # 체크박스 생성
        for symbol, name in available_coins:
            # 블랙리스트 코인 제외
            if symbol in blacklist:
                logger.info(f"⛔ {symbol}: 스킵 리스트에 추가 (상장폐지)")
                continue

            checkbox = QCheckBox(f"{symbol} - {name}")
            checkbox.setFont(QFont("맑은 고딕", 9))

            # 다른 그룹에 이미 있는 코인은 비활성화
            if symbol in assigned_coins:
                checkbox.setEnabled(False)
                checkbox.setStyleSheet("color: #999;")
                checkbox.setToolTip(f"이미 \"{assigned_coins[symbol]}\" 그룹에 포함됨")
            else:
                checkbox.stateChanged.connect(self._on_coin_selection_changed)

            self.coin_checkboxes[symbol] = checkbox
            self.coin_checkbox_layout.addWidget(checkbox)

        # 하단 여백
        self.coin_checkbox_layout.addStretch()

    def _create_new_group(self):
        """새 그룹 생성"""
        # 거래 실행 중 체크
        if self.is_trading_running:
            QMessageBox.warning(
                self,
                "생성 불가",
                "거래가 실행 중일 때는 그룹을 생성할 수 없습니다.\n\n"
                "먼저 '거래 중지' 버튼을 눌러 거래를 중지한 후\n"
                "그룹을 생성하세요."
            )
            return

        try:
            # 새 그룹 ID 생성 (group_1, group_2, ...)
            config = self.config_manager.load_config()
            existing_groups = config.get("groups", {})

            default_name = f"새 그룹 {len(existing_groups) + 1}"

            # 그룹명 입력 다이얼로그
            from PySide6.QtWidgets import QInputDialog

            group_name, ok = QInputDialog.getText(
                self,
                "새 그룹 생성",
                "그룹명을 입력하세요:",
                text=default_name
            )

            # 사용자가 취소 누르면 생성 안 함
            if not ok:
                logger.info("❌ 그룹 생성 취소됨")
                return

            # 그룹명 검증
            group_name = group_name.strip()
            if not group_name:
                QMessageBox.warning(self, "입력 오류", "그룹명을 입력하세요.")
                return

            new_id = f"group_{len(existing_groups) + 1}"

            # GroupManager를 통해 그룹 생성
            self.group_manager.create_group(
                group_id=new_id,
                name=group_name,
                coins=[]
            )

            logger.info(f"✅ 새 그룹 생성: {new_id} ({group_name})")

            # UI 업데이트
            self._load_groups()

            # 새로 생성된 그룹 선택
            for i in range(self.group_list_widget.count()):
                item = self.group_list_widget.item(i)
                if item.data(Qt.UserRole) == new_id:
                    self.group_list_widget.setCurrentItem(item)
                    break

        except Exception as e:
            logger.error(f"❌ 그룹 생성 실패: {e}")
            QMessageBox.critical(
                self,
                "오류",
                f"그룹을 생성할 수 없습니다.\n{e}"
            )

    def _on_group_selected(self, current: QListWidgetItem, previous: QListWidgetItem):
        """그룹 선택 이벤트"""
        if not current:
            self.selected_group_id = None
            self._set_detail_panel_visible(False)
            return

        group_id = current.data(Qt.UserRole)
        self.selected_group_id = group_id

        # 상세 패널 표시
        self._set_detail_panel_visible(True)

        # 버튼 활성화
        self.settings_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)

        # 그룹 데이터 로드
        self._load_group_detail(group_id)

    def _load_group_detail(self, group_id: str):
        """선택된 그룹의 상세 정보 로드"""
        try:
            config = self.config_manager.load_config()
            groups = config.get("groups", {})

            if group_id not in groups:
                logger.warning(f"⚠️ 그룹 없음: {group_id}")
                return

            group = groups[group_id]

            # 그룹명
            self.group_name_edit.setText(group.get("name", ""))

            # 관찰 전용 모드
            observation_mode = group.get("observation_only", False)
            self.observation_checkbox.setChecked(observation_mode)

            # 코인 체크박스 로드
            self._load_available_coins()

            # 현재 그룹의 코인 체크
            group_coins = group.get("coins", [])
            for symbol, checkbox in self.coin_checkboxes.items():
                checkbox.setChecked(symbol in group_coins)

            # 코인 개수 업데이트
            self._update_coin_count()

            logger.info(f"✅ 그룹 상세 로드: {group_id}")

        except Exception as e:
            logger.error(f"❌ 그룹 상세 로드 실패: {e}")
            QMessageBox.critical(
                self,
                "오류",
                f"그룹 정보를 불러올 수 없습니다.\n{e}"
            )

    def _on_coin_selection_changed(self):
        """코인 선택 변경 시"""
        self._update_coin_count()

    def _update_coin_count(self):
        """선택된 코인 개수 및 목록 업데이트"""
        # 선택된 코인 추출
        selected_coins = [
            symbol for symbol, cb in self.coin_checkboxes.items()
            if cb.isChecked()
        ]
        checked_count = len(selected_coins)

        # 표시 텍스트 생성
        if checked_count == 0:
            display_text = "선택된 코인 없음"
        else:
            # 최대 3개까지만 표시
            coin_symbols = [coin.replace('KRW-', '') for coin in selected_coins[:3]]
            coin_str = ", ".join(coin_symbols)

            if checked_count > 3:
                coin_str += f", ... 외 {checked_count - 3}개"

            display_text = f"{checked_count}개 선택됨: {coin_str}"

        self.coin_count_label.setText(display_text)

    def _filter_coins(self):
        """검색어에 따라 코인 필터링"""
        search_text = self.coin_search_edit.text().strip().upper()

        # 검색어가 비어있으면 모두 표시
        if not search_text:
            for checkbox in self.coin_checkboxes.values():
                checkbox.setVisible(True)
            return

        # 검색어와 일치하는 항목만 표시
        for symbol, checkbox in self.coin_checkboxes.items():
            # 심볼명 또는 표시 텍스트에서 검색
            checkbox_text = checkbox.text().upper()
            checkbox.setVisible(search_text in checkbox_text)

    def _save_group(self):
        """그룹 저장"""
        if not self.selected_group_id:
            return

        # 거래 실행 중 체크
        if self.is_trading_running:
            QMessageBox.warning(
                self,
                "변경 불가",
                "거래가 실행 중일 때는 그룹 설정을 변경할 수 없습니다.\n\n"
                "먼저 '거래 중지' 버튼을 눌러 거래를 중지한 후\n"
                "그룹 설정을 변경하세요."
            )
            return

        try:
            # 그룹명 검증
            new_name = self.group_name_edit.text().strip()
            if not new_name:
                QMessageBox.warning(
                    self,
                    "입력 오류",
                    "그룹명을 입력하세요."
                )
                return

            # 선택된 코인 목록
            selected_coins = [
                symbol for symbol, checkbox in self.coin_checkboxes.items()
                if checkbox.isChecked()
            ]

            # 관찰 전용 모드
            observation_mode = self.observation_checkbox.isChecked()

            # GroupManager를 통해 업데이트 (딕셔너리로 전달)
            self.group_manager.update_group_settings(
                group_id=self.selected_group_id,
                updates={
                    'name': new_name,
                    'observation_only': observation_mode
                }
            )

            # 코인 업데이트 (기존 코인 제거 후 새로 추가)
            config = self.config_manager.load_config()
            old_coins = config.get("groups", {}).get(self.selected_group_id, {}).get("coins", [])

            # 제거할 코인
            for coin in old_coins:
                if coin not in selected_coins:
                    self.group_manager.remove_coin_from_group(self.selected_group_id, coin)

            # 추가할 코인
            for coin in selected_coins:
                if coin not in old_coins:
                    self.group_manager.add_coin_to_group(self.selected_group_id, coin)

            logger.info(f"✅ 그룹 저장 완료: {self.selected_group_id}")

            QMessageBox.information(
                self,
                "저장 완료",
                f"그룹 \"{new_name}\"이(가) 저장되었습니다."
            )

            # UI 업데이트
            self._load_groups()

            # 변경 시그널 발생
            self.groups_changed.emit()

        except Exception as e:
            logger.error(f"❌ 그룹 저장 실패: {e}")
            QMessageBox.critical(
                self,
                "오류",
                f"그룹을 저장할 수 없습니다.\n{e}"
            )

    def _delete_group(self):
        """그룹 삭제"""
        if not self.selected_group_id:
            return

        # 거래 실행 중 체크
        if self.is_trading_running:
            QMessageBox.warning(
                self,
                "삭제 불가",
                "거래가 실행 중일 때는 그룹을 삭제할 수 없습니다.\n\n"
                "먼저 '거래 중지' 버튼을 눌러 거래를 중지한 후\n"
                "그룹을 삭제하세요."
            )
            return

        try:
            # 포지션 확인
            # TODO: PositionManager를 통해 활성 포지션 확인
            # 현재는 간단한 확인만 수행

            reply = QMessageBox.question(
                self,
                "삭제 확인",
                f"그룹 \"{self.group_name_edit.text()}\"을(를) 삭제하시겠습니까?\n"
                "이 작업은 되돌릴 수 없습니다.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

            # GroupManager를 통해 삭제
            self.group_manager.delete_group(self.selected_group_id)

            logger.info(f"✅ 그룹 삭제 완료: {self.selected_group_id}")

            QMessageBox.information(
                self,
                "삭제 완료",
                "그룹이 삭제되었습니다."
            )

            # UI 업데이트
            self.selected_group_id = None
            self._load_groups()
            self._set_detail_panel_visible(False)

            # 변경 시그널 발생
            self.groups_changed.emit()

        except Exception as e:
            logger.error(f"❌ 그룹 삭제 실패: {e}")
            QMessageBox.critical(
                self,
                "오류",
                f"그룹을 삭제할 수 없습니다.\n{e}"
            )

    def _open_group_settings(self):
        """그룹 설정 다이얼로그 열기"""
        if not self.selected_group_id:
            return

        try:
            from gui.group_settings_dialog import GroupSettingsDialog

            group_name = self.group_name_edit.text()

            dialog = GroupSettingsDialog(
                self.config_manager,
                self.selected_group_id,
                group_name,
                parent=self
            )

            # 설정 저장 시그널 연결
            dialog.settings_saved.connect(self._on_settings_saved)

            dialog.exec()

        except Exception as e:
            logger.error(f"❌ 그룹 설정 다이얼로그 오류: {e}")
            QMessageBox.critical(
                self,
                "오류",
                f"그룹 설정 다이얼로그를 열 수 없습니다.\n{e}"
            )

    def _on_settings_saved(self):
        """그룹 설정 저장 완료 시"""
        logger.info("✅ 그룹 설정 저장 완료")
        # 그룹 리스트 다시 로드 (코인 목록 변경사항 반영)
        self._load_groups()
        # 그룹 변경 시그널 전파 (메인 윈도우 업데이트)
        self.groups_changed.emit()


# 테스트 코드
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    from core.config_manager import ConfigManager
    from core.group_manager import GroupManager

    app = QApplication(sys.argv)

    # 테스트용 매니저 생성
    config_mgr = ConfigManager()
    group_mgr = GroupManager(config_mgr, position_manager=None)

    dialog = GroupManagementDialog(config_mgr, group_mgr)
    dialog.exec()

    sys.exit(app.exec())
