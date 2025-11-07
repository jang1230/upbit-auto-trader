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
    QMessageBox, QSplitter, QGroupBox, QFormLayout,
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QTabWidget
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
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)  # 초기 크기 설정

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

        # === 우측: 탭 위젯 ===
        tab_widget = QTabWidget()

        # ============ 탭 1: 기본 설정 ============
        tab1 = QWidget()
        tab1_layout = QVBoxLayout()

        # 그룹명
        group_name_layout = QHBoxLayout()
        group_name_layout.addWidget(QLabel("그룹명:"))
        self.group_name_input = QLineEdit()
        self.group_name_input.setPlaceholderText("그룹 이름 입력")
        group_name_layout.addWidget(self.group_name_input)
        tab1_layout.addLayout(group_name_layout)

        # 관찰 전용 모드
        self.observation_checkbox = QCheckBox("관찰 전용 모드")
        self.observation_checkbox.setStyleSheet("color: #FF9800;")
        tab1_layout.addWidget(self.observation_checkbox)

        # 포함 코인
        coins_label = QLabel("포함 코인:")
        coins_label.setFont(QFont("맑은 고딕", 9, QFont.Bold))
        tab1_layout.addWidget(coins_label)

        # 코인 체크박스 스크롤 영역
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(250)

        self.coins_widget = QWidget()
        self.coins_layout = QVBoxLayout()
        self.coins_widget.setLayout(self.coins_layout)
        scroll_area.setWidget(self.coins_widget)

        tab1_layout.addWidget(scroll_area)

        # 매수 설정
        buy_group = QGroupBox("매수 설정")
        buy_form_layout = QFormLayout()

        # 매수 방식 (자동/수동)
        buy_mode_layout = QHBoxLayout()
        self.buy_button_group = QButtonGroup()
        self.auto_buy_radio = QRadioButton("자동")
        self.manual_buy_radio = QRadioButton("수동")
        self.buy_button_group.addButton(self.auto_buy_radio, 0)
        self.buy_button_group.addButton(self.manual_buy_radio, 1)
        buy_mode_layout.addWidget(self.auto_buy_radio)
        buy_mode_layout.addWidget(self.manual_buy_radio)
        buy_mode_layout.addStretch()
        buy_form_layout.addRow("매수 방식:", buy_mode_layout)

        # 투자 성향 (자동 매수 시)
        self.investment_style_combo = QComboBox()
        self.investment_style_combo.addItems([
            "Conservative (보수적)",
            "Balanced (균형적)",
            "Aggressive (공격적)"
        ])
        self.investment_style_combo.setEnabled(False)  # 기본적으로 비활성화
        buy_form_layout.addRow("투자 성향:", self.investment_style_combo)

        # 매수 금액 (KRW)
        self.buy_amount_input = QLineEdit()
        self.buy_amount_input.setPlaceholderText("예: 50000")
        buy_form_layout.addRow("매수 금액 (KRW):", self.buy_amount_input)

        buy_group.setLayout(buy_form_layout)
        tab1_layout.addWidget(buy_group)

        tab1_layout.addStretch()
        tab1.setLayout(tab1_layout)

        # 자동/수동 전환 시 투자 성향 활성화/비활성화
        self.auto_buy_radio.toggled.connect(self._on_buy_mode_changed)

        # ============ 탭 2: 레벨 설정 ============
        tab2 = QWidget()
        tab2_layout = QVBoxLayout()

        # DCA 레벨 설정
        dca_group = QGroupBox("DCA 레벨 설정")
        dca_layout = QVBoxLayout()

        # DCA 활성화 체크박스
        self.dca_enabled_checkbox = QCheckBox("DCA 활성화")
        self.dca_enabled_checkbox.toggled.connect(self._on_dca_enabled_changed)
        dca_layout.addWidget(self.dca_enabled_checkbox)

        # DCA 레벨 테이블
        self.dca_table = QTableWidget()
        self.dca_table.setColumnCount(2)
        self.dca_table.setHorizontalHeaderLabels(["가격 하락 (%)", "매수 금액 (KRW)"])
        self.dca_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.dca_table.setMinimumHeight(150)
        self.dca_table.setEnabled(False)  # 기본적으로 비활성화
        dca_layout.addWidget(self.dca_table)

        # DCA 레벨 버튼들
        dca_button_layout = QHBoxLayout()
        self.dca_add_btn = QPushButton("➕ 추가")
        self.dca_remove_btn = QPushButton("➖ 삭제")
        self.dca_edit_btn = QPushButton("✏️ 수정")
        self.dca_add_btn.clicked.connect(self._add_dca_level)
        self.dca_remove_btn.clicked.connect(self._remove_dca_level)
        self.dca_edit_btn.clicked.connect(self._edit_dca_level)
        self.dca_add_btn.setEnabled(False)
        self.dca_remove_btn.setEnabled(False)
        self.dca_edit_btn.setEnabled(False)
        dca_button_layout.addWidget(self.dca_add_btn)
        dca_button_layout.addWidget(self.dca_remove_btn)
        dca_button_layout.addWidget(self.dca_edit_btn)
        dca_button_layout.addStretch()
        dca_layout.addLayout(dca_button_layout)

        dca_group.setLayout(dca_layout)
        tab2_layout.addWidget(dca_group)

        # 익절 레벨 설정
        profit_group = QGroupBox("익절 레벨 설정")
        profit_layout = QVBoxLayout()

        # 익절 레벨 테이블
        self.profit_table = QTableWidget()
        self.profit_table.setColumnCount(2)
        self.profit_table.setHorizontalHeaderLabels(["익절 비율", "판매 수량 (%)"])
        self.profit_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.profit_table.setMinimumHeight(150)
        profit_layout.addWidget(self.profit_table)

        # 익절 레벨 버튼들
        profit_button_layout = QHBoxLayout()
        self.profit_add_btn = QPushButton("➕ 추가")
        self.profit_remove_btn = QPushButton("➖ 삭제")
        self.profit_edit_btn = QPushButton("✏️ 수정")
        self.profit_add_btn.clicked.connect(self._add_profit_level)
        self.profit_remove_btn.clicked.connect(self._remove_profit_level)
        self.profit_edit_btn.clicked.connect(self._edit_profit_level)
        profit_button_layout.addWidget(self.profit_add_btn)
        profit_button_layout.addWidget(self.profit_remove_btn)
        profit_button_layout.addWidget(self.profit_edit_btn)
        profit_button_layout.addStretch()
        profit_layout.addLayout(profit_button_layout)

        profit_group.setLayout(profit_layout)
        tab2_layout.addWidget(profit_group)

        # 손절 레벨 설정
        loss_group = QGroupBox("손절 레벨 설정")
        loss_layout = QVBoxLayout()

        # 손절 레벨 테이블
        self.loss_table = QTableWidget()
        self.loss_table.setColumnCount(2)
        self.loss_table.setHorizontalHeaderLabels(["손절 퍼센트 (%)", "판매 수량 (%)"])
        self.loss_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.loss_table.setMinimumHeight(150)
        loss_layout.addWidget(self.loss_table)

        # 손절 레벨 버튼들
        loss_button_layout = QHBoxLayout()
        self.loss_add_btn = QPushButton("➕ 추가")
        self.loss_remove_btn = QPushButton("➖ 삭제")
        self.loss_edit_btn = QPushButton("✏️ 수정")
        self.loss_add_btn.clicked.connect(self._add_loss_level)
        self.loss_remove_btn.clicked.connect(self._remove_loss_level)
        self.loss_edit_btn.clicked.connect(self._edit_loss_level)
        loss_button_layout.addWidget(self.loss_add_btn)
        loss_button_layout.addWidget(self.loss_remove_btn)
        loss_button_layout.addWidget(self.loss_edit_btn)
        loss_button_layout.addStretch()
        loss_layout.addLayout(loss_button_layout)

        loss_group.setLayout(loss_layout)
        tab2_layout.addWidget(loss_group)

        tab2_layout.addStretch()
        tab2.setLayout(tab2_layout)

        # 탭 추가
        tab_widget.addTab(tab1, "기본 설정")
        tab_widget.addTab(tab2, "레벨 설정")

        # 스플리터에 추가
        splitter.addWidget(left_widget)
        splitter.addWidget(tab_widget)
        splitter.setSizes([200, 1000])

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

    def _on_buy_mode_changed(self, checked):
        """매수 방식 변경 시 투자 성향 활성화/비활성화"""
        # auto_buy_radio가 체크되면 투자 성향 활성화
        self.investment_style_combo.setEnabled(self.auto_buy_radio.isChecked())

    def _on_dca_enabled_changed(self, checked):
        """DCA 활성화/비활성화 시 테이블 및 버튼 활성화"""
        self.dca_table.setEnabled(checked)
        self.dca_add_btn.setEnabled(checked)
        self.dca_remove_btn.setEnabled(checked)
        self.dca_edit_btn.setEnabled(checked)

    def _add_dca_level(self):
        """DCA 레벨 추가"""
        from PySide6.QtWidgets import QInputDialog

        # 가격 하락 % 입력
        price_drop, ok1 = QInputDialog.getDouble(
            self, "DCA 레벨 추가", "가격 하락 (%):",
            -3.0, -50.0, 0.0, 1
        )
        if not ok1:
            return

        # 매수 금액 입력
        buy_amount, ok2 = QInputDialog.getInt(
            self, "DCA 레벨 추가", "매수 금액 (KRW):",
            50000, 10000, 10000000, 10000
        )
        if not ok2:
            return

        # 테이블에 추가
        row_count = self.dca_table.rowCount()
        self.dca_table.insertRow(row_count)
        self.dca_table.setItem(row_count, 0, QTableWidgetItem(str(price_drop)))
        self.dca_table.setItem(row_count, 1, QTableWidgetItem(str(buy_amount)))

    def _remove_dca_level(self):
        """DCA 레벨 삭제"""
        current_row = self.dca_table.currentRow()
        if current_row >= 0:
            self.dca_table.removeRow(current_row)
        else:
            QMessageBox.warning(self, "경고", "삭제할 레벨을 선택하세요.")

    def _edit_dca_level(self):
        """DCA 레벨 수정"""
        from PySide6.QtWidgets import QInputDialog

        current_row = self.dca_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "경고", "수정할 레벨을 선택하세요.")
            return

        # 현재 값 가져오기
        current_price_drop = float(self.dca_table.item(current_row, 0).text())
        current_buy_amount = int(self.dca_table.item(current_row, 1).text())

        # 가격 하락 % 입력
        price_drop, ok1 = QInputDialog.getDouble(
            self, "DCA 레벨 수정", "가격 하락 (%):",
            current_price_drop, -50.0, 0.0, 1
        )
        if not ok1:
            return

        # 매수 금액 입력
        buy_amount, ok2 = QInputDialog.getInt(
            self, "DCA 레벨 수정", "매수 금액 (KRW):",
            current_buy_amount, 10000, 10000000, 10000
        )
        if not ok2:
            return

        # 테이블 업데이트
        self.dca_table.setItem(current_row, 0, QTableWidgetItem(str(price_drop)))
        self.dca_table.setItem(current_row, 1, QTableWidgetItem(str(buy_amount)))

    def _add_profit_level(self):
        """익절 레벨 추가"""
        from PySide6.QtWidgets import QInputDialog

        # 가격 비율 입력 (1.05 = 5% 익절)
        price_ratio, ok1 = QInputDialog.getDouble(
            self, "익절 레벨 추가", "가격 비율 (예: 1.05 = 5% 익절):",
            1.05, 1.0, 2.0, 2
        )
        if not ok1:
            return

        # 판매 수량 비율 입력 (50 = 50% 판매)
        quantity_ratio, ok2 = QInputDialog.getInt(
            self, "익절 레벨 추가", "판매 수량 비율 (예: 50 = 50% 판매):",
            50, 1, 100, 1
        )
        if not ok2:
            return

        # 테이블에 추가
        row_count = self.profit_table.rowCount()
        self.profit_table.insertRow(row_count)
        self.profit_table.setItem(row_count, 0, QTableWidgetItem(str(price_ratio)))
        self.profit_table.setItem(row_count, 1, QTableWidgetItem(str(quantity_ratio)))

    def _remove_profit_level(self):
        """익절 레벨 삭제"""
        current_row = self.profit_table.currentRow()
        if current_row >= 0:
            self.profit_table.removeRow(current_row)
        else:
            QMessageBox.warning(self, "경고", "삭제할 레벨을 선택하세요.")

    def _edit_profit_level(self):
        """익절 레벨 수정"""
        from PySide6.QtWidgets import QInputDialog

        current_row = self.profit_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "경고", "수정할 레벨을 선택하세요.")
            return

        # 현재 값 가져오기
        current_price_ratio = float(self.profit_table.item(current_row, 0).text())
        current_quantity_ratio = int(float(self.profit_table.item(current_row, 1).text()))

        # 가격 비율 입력
        price_ratio, ok1 = QInputDialog.getDouble(
            self, "익절 레벨 수정", "가격 비율 (예: 1.05 = 5% 익절):",
            current_price_ratio, 1.0, 2.0, 2
        )
        if not ok1:
            return

        # 판매 수량 비율 입력
        quantity_ratio, ok2 = QInputDialog.getInt(
            self, "익절 레벨 수정", "판매 수량 비율 (예: 50 = 50% 판매):",
            current_quantity_ratio, 1, 100, 1
        )
        if not ok2:
            return

        # 테이블 업데이트
        self.profit_table.setItem(current_row, 0, QTableWidgetItem(str(price_ratio)))
        self.profit_table.setItem(current_row, 1, QTableWidgetItem(str(quantity_ratio)))

    def _add_loss_level(self):
        """손절 레벨 추가"""
        from PySide6.QtWidgets import QInputDialog

        # 손절 퍼센트 입력 (5 = -5% 손절)
        loss_percent, ok1 = QInputDialog.getInt(
            self, "손절 레벨 추가", "손절 퍼센트 (예: 5 = -5% 손절):",
            5, 1, 50, 1
        )
        if not ok1:
            return

        # 판매 수량 비율 입력 (100 = 100% 판매)
        quantity_ratio, ok2 = QInputDialog.getInt(
            self, "손절 레벨 추가", "판매 수량 비율 (예: 100 = 100% 판매):",
            100, 1, 100, 1
        )
        if not ok2:
            return

        # 테이블에 추가 (양수로 표시하지만, 저장 시 음수로 변환)
        row_count = self.loss_table.rowCount()
        self.loss_table.insertRow(row_count)
        self.loss_table.setItem(row_count, 0, QTableWidgetItem(str(loss_percent)))
        self.loss_table.setItem(row_count, 1, QTableWidgetItem(str(quantity_ratio)))

    def _remove_loss_level(self):
        """손절 레벨 삭제"""
        current_row = self.loss_table.currentRow()
        if current_row >= 0:
            self.loss_table.removeRow(current_row)
        else:
            QMessageBox.warning(self, "경고", "삭제할 레벨을 선택하세요.")

    def _edit_loss_level(self):
        """손절 레벨 수정"""
        from PySide6.QtWidgets import QInputDialog

        current_row = self.loss_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "경고", "수정할 레벨을 선택하세요.")
            return

        # 현재 값 가져오기 (테이블에는 양수로 저장됨)
        current_loss_percent = int(float(self.loss_table.item(current_row, 0).text()))
        current_quantity_ratio = int(float(self.loss_table.item(current_row, 1).text()))

        # 손절 퍼센트 입력
        loss_percent, ok1 = QInputDialog.getInt(
            self, "손절 레벨 수정", "손절 퍼센트 (예: 5 = -5% 손절):",
            current_loss_percent, 1, 50, 1
        )
        if not ok1:
            return

        # 판매 수량 비율 입력
        quantity_ratio, ok2 = QInputDialog.getInt(
            self, "손절 레벨 수정", "판매 수량 비율 (예: 100 = 100% 판매):",
            current_quantity_ratio, 1, 100, 1
        )
        if not ok2:
            return

        # 테이블 업데이트
        self.loss_table.setItem(current_row, 0, QTableWidgetItem(str(loss_percent)))
        self.loss_table.setItem(current_row, 1, QTableWidgetItem(str(quantity_ratio)))

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

            # 매수 설정
            buy_settings = group_data.get("buy_settings", {})

            # 투자 성향
            investment_style = buy_settings.get("investment_style", "balanced")
            style_index = {"conservative": 0, "balanced": 1, "aggressive": 2}.get(investment_style, 1)
            self.investment_style_combo.setCurrentIndex(style_index)

            # 매수 금액
            buy_amount = buy_settings.get("buy_amount_krw", 50000)
            self.buy_amount_input.setText(str(buy_amount))

            # DCA 설정
            dca_settings = group_data.get("dca_settings", {})
            dca_enabled = dca_settings.get("enabled", False)
            self.dca_enabled_checkbox.setChecked(dca_enabled)

            # DCA 레벨 로드
            self.dca_table.setRowCount(0)  # 기존 데이터 삭제
            dca_levels = dca_settings.get("levels", [])
            for level in dca_levels:
                row_count = self.dca_table.rowCount()
                self.dca_table.insertRow(row_count)
                self.dca_table.setItem(row_count, 0, QTableWidgetItem(str(level.get("price_drop_pct", -3.0))))
                self.dca_table.setItem(row_count, 1, QTableWidgetItem(str(level.get("buy_amount_krw", 50000))))

            # 익절 설정
            profit_settings = group_data.get("profit_settings", {})
            self.profit_table.setRowCount(0)  # 기존 데이터 삭제
            profit_targets = profit_settings.get("levels", [])
            for level in profit_targets:
                row_count = self.profit_table.rowCount()
                self.profit_table.insertRow(row_count)
                self.profit_table.setItem(row_count, 0, QTableWidgetItem(str(level.get("price_ratio", 1.05))))
                # quantity_ratio를 정수로 표시
                quantity_ratio = int(level.get("quantity_ratio", 50))
                self.profit_table.setItem(row_count, 1, QTableWidgetItem(str(quantity_ratio)))

            # 손절 설정
            loss_settings = group_data.get("loss_settings", {})
            self.loss_table.setRowCount(0)  # 기존 데이터 삭제
            loss_targets = loss_settings.get("levels", [])
            for level in loss_targets:
                row_count = self.loss_table.rowCount()
                self.loss_table.insertRow(row_count)
                # config의 음수 값(-5.0)을 양수(5)로 변환하여 표시
                price_ratio = level.get("price_ratio", -5.0)
                loss_percent = abs(price_ratio)  # 음수를 양수로 변환
                self.loss_table.setItem(row_count, 0, QTableWidgetItem(str(int(loss_percent))))
                # quantity_ratio를 정수로 표시
                quantity_ratio = int(level.get("quantity_ratio", 100))
                self.loss_table.setItem(row_count, 1, QTableWidgetItem(str(quantity_ratio)))

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

            # 매수 설정
            if "buy_settings" not in group_data:
                group_data["buy_settings"] = {}

            # 매수 모드 (스키마 필수 필드)
            group_data["buy_settings"]["mode"] = "auto" if self.auto_buy_radio.isChecked() else "manual"

            # 투자 성향
            style_map = {0: "conservative", 1: "balanced", 2: "aggressive"}
            group_data["buy_settings"]["investment_style"] = style_map[self.investment_style_combo.currentIndex()]

            # 매수 금액
            try:
                buy_amount = int(self.buy_amount_input.text().strip())
                group_data["buy_settings"]["buy_amount_krw"] = buy_amount
            except ValueError:
                # 잘못된 입력 시 기본값 사용
                group_data["buy_settings"]["buy_amount_krw"] = 50000

            # DCA 설정
            if "dca_settings" not in group_data:
                group_data["dca_settings"] = {}

            # DCA 모드 (스키마 필수 필드)
            group_data["dca_settings"]["mode"] = "auto" if self.dca_enabled_checkbox.isChecked() else "disabled"
            group_data["dca_settings"]["enabled"] = self.dca_enabled_checkbox.isChecked()

            # DCA 레벨 수집
            dca_levels = []
            for row in range(self.dca_table.rowCount()):
                price_drop_item = self.dca_table.item(row, 0)
                buy_amount_item = self.dca_table.item(row, 1)
                if price_drop_item and buy_amount_item:
                    # 스키마에 맞게 price_ratio, quantity_ratio 사용
                    # quantity_ratio는 초기 매수 대비 비율 (100 = 100%, 즉 같은 금액)
                    # TODO: 나중에 GUI를 quantity_ratio 입력으로 개선 필요
                    dca_levels.append({
                        "price_ratio": float(price_drop_item.text()),
                        "quantity_ratio": 100  # 임시로 100% 고정
                    })
            group_data["dca_settings"]["levels"] = dca_levels

            # 익절 설정
            if "profit_settings" not in group_data:
                group_data["profit_settings"] = {}

            # 익절 레벨 수집
            profit_levels = []
            for row in range(self.profit_table.rowCount()):
                price_ratio_item = self.profit_table.item(row, 0)
                quantity_ratio_item = self.profit_table.item(row, 1)
                if price_ratio_item and quantity_ratio_item:
                    profit_levels.append({
                        "price_ratio": float(price_ratio_item.text()),
                        "quantity_ratio": int(quantity_ratio_item.text())
                    })
            group_data["profit_settings"]["levels"] = profit_levels

            # 익절 모드 (스키마 필수 필드)
            group_data["profit_settings"]["mode"] = "auto" if profit_levels else "disabled"

            # 손절 설정
            if "loss_settings" not in group_data:
                group_data["loss_settings"] = {}

            # 손절 레벨 수집
            loss_levels = []
            for row in range(self.loss_table.rowCount()):
                price_ratio_item = self.loss_table.item(row, 0)
                quantity_ratio_item = self.loss_table.item(row, 1)
                if price_ratio_item and quantity_ratio_item:
                    # 테이블에는 양수(5)로 저장되어 있지만, config에는 음수(-5.0)로 저장
                    loss_percent = float(price_ratio_item.text())
                    loss_levels.append({
                        "price_ratio": -loss_percent,  # 음수로 변환!
                        "quantity_ratio": int(quantity_ratio_item.text())
                    })
            group_data["loss_settings"]["levels"] = loss_levels

            # 손절 모드 (스키마 필수 필드)
            group_data["loss_settings"]["mode"] = "auto" if loss_levels else "disabled"

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
