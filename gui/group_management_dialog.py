"""
그룹 관리 다이얼로그

V4 그룹 시스템의 마스터-디테일 패턴 UI
- 좌측: 그룹 목록
- 우측: 그룹 상세 (코인 선택, 설정)
"""

import logging
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QListWidget, QCheckBox,
    QScrollArea, QWidget, QRadioButton, QButtonGroup,
    QMessageBox, QSplitter, QGroupBox, QFormLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from core.group_manager import GroupManager

logger = logging.getLogger(__name__)


class GroupManagementDialog(QDialog):
    """
    V4 그룹 관리 다이얼로그

    마스터-디테일 패턴:
    - 좌측: 그룹 목록 (QListWidget)
    - 우측: 그룹 상세 (코인 체크박스, 설정)
    """

    def __init__(self, group_manager: GroupManager, parent=None):
        super().__init__(parent)
        self.group_manager = group_manager
        self.current_group_id = None

        # 코인 체크박스 딕셔너리 {symbol: QCheckBox}
        self.coin_checkboxes = {}

        self._init_ui()
        self._load_groups()

    def _init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("그룹 관리")
        self.setMinimumSize(700, 600)

        # 메인 레이아웃
        main_layout = QVBoxLayout()

        # 스플리터 (좌우 분할)
        splitter = QSplitter(Qt.Horizontal)

        # === 좌측: 그룹 목록 ===
        left_widget = QWidget()
        left_layout = QVBoxLayout()

        # 그룹 목록
        list_label = QLabel("그룹 목록")
        list_label.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        left_layout.addWidget(list_label)

        self.group_list = QListWidget()
        self.group_list.currentItemChanged.connect(self._on_group_selected)
        left_layout.addWidget(self.group_list)

        # 새 그룹 버튼
        self.new_group_btn = QPushButton("+ 새 그룹")
        self.new_group_btn.clicked.connect(self._create_new_group)
        left_layout.addWidget(self.new_group_btn)

        left_widget.setLayout(left_layout)

        # === 우측: 그룹 상세 ===
        right_widget = QWidget()
        right_layout = QVBoxLayout()

        # 그룹 상세 타이틀
        detail_label = QLabel("그룹 상세")
        detail_label.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        right_layout.addWidget(detail_label)

        # 그룹명
        group_name_layout = QHBoxLayout()
        group_name_layout.addWidget(QLabel("그룹명:"))
        self.group_name_input = QLineEdit()
        self.group_name_input.setPlaceholderText("그룹 이름 입력")
        group_name_layout.addWidget(self.group_name_input)
        right_layout.addLayout(group_name_layout)

        # 관찰 전용 모드
        self.observation_checkbox = QCheckBox("관찰 전용 모드")
        self.observation_checkbox.setStyleSheet("color: #FF9800;")
        right_layout.addWidget(self.observation_checkbox)

        # 포함 코인
        coins_label = QLabel("포함 코인:")
        coins_label.setFont(QFont("맑은 고딕", 9, QFont.Bold))
        right_layout.addWidget(coins_label)

        # 코인 체크박스 스크롤 영역
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(200)

        self.coins_widget = QWidget()
        self.coins_layout = QVBoxLayout()
        self.coins_widget.setLayout(self.coins_layout)
        scroll_area.setWidget(self.coins_widget)

        right_layout.addWidget(scroll_area)

        # 매수 방식
        buy_group = QGroupBox("매수 방식")
        buy_layout = QVBoxLayout()

        self.buy_button_group = QButtonGroup()
        self.auto_buy_radio = QRadioButton("자동")
        self.manual_buy_radio = QRadioButton("수동")
        self.buy_button_group.addButton(self.auto_buy_radio, 0)
        self.buy_button_group.addButton(self.manual_buy_radio, 1)

        buy_layout.addWidget(self.auto_buy_radio)
        buy_layout.addWidget(self.manual_buy_radio)

        buy_group.setLayout(buy_layout)
        right_layout.addWidget(buy_group)

        # 레벨 설정 버튼 (나중에 구현)
        self.level_settings_btn = QPushButton("⚙️ 레벨 상세 설정")
        self.level_settings_btn.setEnabled(False)  # 임시로 비활성화
        right_layout.addWidget(self.level_settings_btn)

        right_layout.addStretch()
        right_widget.setLayout(right_layout)

        # 스플리터에 추가
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([150, 500])

        main_layout.addWidget(splitter)

        # === 하단 버튼 ===
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.save_btn = QPushButton("💾 저장")
        self.save_btn.clicked.connect(self._save_group)
        button_layout.addWidget(self.save_btn)

        self.delete_btn = QPushButton("🗑️ 그룹 삭제")
        self.delete_btn.clicked.connect(self._delete_group)
        button_layout.addWidget(self.delete_btn)

        self.cancel_btn = QPushButton("취소")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

    def _load_groups(self):
        """그룹 목록 로드"""
        try:
            self.group_list.clear()
            groups = self.group_manager.get_all_groups()

            for group_id, group_data in groups.items():
                group_name = group_data.get("name", group_id)
                self.group_list.addItem(f"{group_name} ({group_id})")

            # 첫 번째 그룹 선택
            if self.group_list.count() > 0:
                self.group_list.setCurrentRow(0)

        except Exception as e:
            logger.error(f"그룹 목록 로드 실패: {e}")
            QMessageBox.critical(self, "오류", f"그룹 목록을 불러올 수 없습니다:\n{str(e)}")

    def _on_group_selected(self, current, previous):
        """그룹 선택 시 상세 정보 표시"""
        if not current:
            return

        # 그룹 ID 추출 (괄호 안의 내용)
        text = current.text()
        group_id = text.split("(")[-1].rstrip(")")
        self.current_group_id = group_id

        try:
            # V4: get_all_groups()로 가져온 후 group_id로 필터링
            all_groups = self.group_manager.get_all_groups()
            if group_id not in all_groups:
                raise KeyError(f"그룹을 찾을 수 없습니다: {group_id}")

            group_data = all_groups[group_id]

            # 그룹명
            self.group_name_input.setText(group_data.get("name", ""))

            # 관찰 전용
            observation = group_data.get("observation_only", False)
            self.observation_checkbox.setChecked(observation)

            # 매수 방식
            buy_strategy = group_data.get("buy_strategy", {})
            if buy_strategy.get("enabled", False):
                self.auto_buy_radio.setChecked(True)
            else:
                self.manual_buy_radio.setChecked(True)

            # 코인 체크박스 업데이트
            self._update_coin_checkboxes(group_data.get("coins", []))

        except Exception as e:
            logger.error(f"그룹 정보 로드 실패: {e}")
            QMessageBox.critical(self, "오류", f"그룹 정보를 불러올 수 없습니다:\n{str(e)}")

    def _update_coin_checkboxes(self, selected_coins):
        """코인 체크박스 업데이트"""
        # 기존 체크박스 제거
        for i in reversed(range(self.coins_layout.count())):
            widget = self.coins_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        self.coin_checkboxes.clear()

        # 업비트 KRW 마켓 코인 목록 가져오기
        all_coins = self._get_krw_market_coins()

        # 다른 그룹에 속한 코인 확인
        all_groups = self.group_manager.get_all_groups()
        coins_in_other_groups = set()

        for gid, gdata in all_groups.items():
            if gid != self.current_group_id:
                coins_in_other_groups.update(gdata.get("coins", []))

        # 체크박스 생성
        for coin in all_coins:
            checkbox = QCheckBox(coin)

            # 선택 상태
            if coin in selected_coins:
                checkbox.setChecked(True)

            # 다른 그룹에 있으면 비활성화
            if coin in coins_in_other_groups:
                checkbox.setEnabled(False)
                checkbox.setToolTip(f"이미 다른 그룹에 포함됨")

            self.coin_checkboxes[coin] = checkbox
            self.coins_layout.addWidget(checkbox)

    def _create_new_group(self):
        """새 그룹 생성"""
        try:
            # 고유한 그룹 ID 생성
            import time
            group_id = f"group_{int(time.time())}"

            # 새 그룹 생성
            self.group_manager.create_group(
                group_id=group_id,
                name="새 그룹",
                coins=[]
            )

            # 목록 새로고침
            self._load_groups()

            # 새 그룹 선택
            for i in range(self.group_list.count()):
                if group_id in self.group_list.item(i).text():
                    self.group_list.setCurrentRow(i)
                    break

        except Exception as e:
            logger.error(f"그룹 생성 실패: {e}")
            QMessageBox.critical(self, "오류", f"그룹을 생성할 수 없습니다:\n{str(e)}")

    def _save_group(self):
        """그룹 저장"""
        if not self.current_group_id:
            QMessageBox.warning(self, "경고", "선택된 그룹이 없습니다.")
            return

        try:
            # 선택된 코인 수집
            selected_coins = [
                coin for coin, checkbox in self.coin_checkboxes.items()
                if checkbox.isChecked()
            ]

            # V4: get_all_groups()로 가져온 후 group_id로 필터링
            all_groups = self.group_manager.get_all_groups()
            if self.current_group_id not in all_groups:
                raise KeyError(f"그룹을 찾을 수 없습니다: {self.current_group_id}")

            group_data = all_groups[self.current_group_id]

            group_data["name"] = self.group_name_input.text().strip() or "새 그룹"
            group_data["observation_only"] = self.observation_checkbox.isChecked()
            group_data["coins"] = selected_coins

            # 매수 방식
            if "buy_strategy" not in group_data:
                group_data["buy_strategy"] = {}

            group_data["buy_strategy"]["enabled"] = self.auto_buy_radio.isChecked()

            # 저장
            self.group_manager.update_group_settings(self.current_group_id, group_data)

            QMessageBox.information(self, "성공", "그룹이 저장되었습니다.")

            # 목록 새로고침
            self._load_groups()

        except Exception as e:
            logger.error(f"그룹 저장 실패: {e}")
            QMessageBox.critical(self, "오류", f"그룹을 저장할 수 없습니다:\n{str(e)}")

    def _delete_group(self):
        """그룹 삭제"""
        if not self.current_group_id:
            QMessageBox.warning(self, "경고", "선택된 그룹이 없습니다.")
            return

        # 확인 대화상자
        reply = QMessageBox.question(
            self,
            "그룹 삭제",
            f"'{self.group_name_input.text()}' 그룹을 삭제하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                self.group_manager.delete_group(self.current_group_id)

                QMessageBox.information(self, "성공", "그룹이 삭제되었습니다.")

                # 목록 새로고침
                self._load_groups()

            except Exception as e:
                logger.error(f"그룹 삭제 실패: {e}")
                QMessageBox.critical(self, "오류", f"그룹을 삭제할 수 없습니다:\n{str(e)}")

    def _get_krw_market_coins(self):
        """
        Upbit API에서 KRW 마켓 코인 목록 가져오기

        Returns:
            list: KRW 마켓 코인 심볼 리스트 (예: ["KRW-BTC", "KRW-ETH", ...])
        """
        try:
            import requests

            # Upbit API: 마켓 코드 조회
            url = "https://api.upbit.com/v1/market/all"
            params = {"isDetails": "false"}

            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()

            markets = response.json()

            # KRW 마켓만 필터링
            krw_markets = [
                market['market']
                for market in markets
                if market['market'].startswith('KRW-')
            ]

            # 시가총액 상위 순으로 정렬 (대략적인 순서)
            # BTC, ETH, USDT, SOL 등을 앞에 배치
            priority_coins = ['KRW-BTC', 'KRW-ETH', 'KRW-USDT', 'KRW-SOL', 'KRW-XRP',
                             'KRW-DOGE', 'KRW-ADA', 'KRW-AVAX', 'KRW-DOT', 'KRW-LINK']

            # 우선순위 코인을 앞에, 나머지는 알파벳 순
            sorted_coins = []
            for coin in priority_coins:
                if coin in krw_markets:
                    sorted_coins.append(coin)

            remaining = sorted([c for c in krw_markets if c not in priority_coins])
            sorted_coins.extend(remaining)

            return sorted_coins if sorted_coins else ["KRW-BTC", "KRW-ETH", "KRW-XRP"]

        except Exception as e:
            logger.warning(f"Upbit API 코인 목록 조회 실패: {e}, 기본 목록 사용")
            # 폴백: 하드코딩된 기본 목록
            return [
                "KRW-BTC", "KRW-ETH", "KRW-XRP", "KRW-DOGE",
                "KRW-SOL", "KRW-ADA", "KRW-AVAX", "KRW-DOT",
                "KRW-LINK", "KRW-MATIC", "KRW-ATOM", "KRW-NEAR"
            ]


if __name__ == "__main__":
    """테스트 코드"""
    import sys
    from PySide6.QtWidgets import QApplication
    from core.config_manager import ConfigManager

    app = QApplication(sys.argv)

    # GroupManager 생성
    config_path = "config/trading_config.json"
    config_manager = ConfigManager(config_path)
    group_manager = GroupManager(config_path)

    # 다이얼로그 표시
    dialog = GroupManagementDialog(group_manager)
    dialog.exec()

    sys.exit(0)
