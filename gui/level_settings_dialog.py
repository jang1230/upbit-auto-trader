"""
레벨 상세 설정 다이얼로그

DCA/익절/손절 레벨을 테이블로 상세 편집
"""

import logging
from typing import List, Dict, Any

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QPushButton, QTableWidget, QTableWidgetItem, QWidget,
    QMessageBox, QHeaderView, QLabel
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class LevelSettingsDialog(QDialog):
    """레벨 상세 설정 다이얼로그"""

    settings_saved = Signal()

    def __init__(self, config_manager: ConfigManager, group_id: str, group_name: str, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.group_id = group_id
        self.group_name = group_name

        self.setWindowTitle(f"레벨 상세 설정: {group_name}")
        self.setMinimumSize(700, 600)

        self._init_ui()
        self._load_levels()

    def _init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)

        # 탭 위젯
        self.tab_widget = QTabWidget()
        self.tab_widget.setFont(QFont("맑은 고딕", 9))

        # 3개 탭 생성
        self.dca_tab = self._create_dca_tab()
        self.profit_tab = self._create_profit_tab()
        self.loss_tab = self._create_loss_tab()

        self.tab_widget.addTab(self.dca_tab, "DCA 레벨")
        self.tab_widget.addTab(self.profit_tab, "익절 레벨")
        self.tab_widget.addTab(self.loss_tab, "손절 레벨")

        layout.addWidget(self.tab_widget)

        # 하단 버튼
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        save_btn = QPushButton("💾 저장")
        save_btn.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        save_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 12px 30px; border-radius: 5px;")
        save_btn.clicked.connect(self._save_levels)
        button_layout.addWidget(save_btn)

        cancel_btn = QPushButton("취소")
        cancel_btn.setFont(QFont("맑은 고딕", 9))
        cancel_btn.setStyleSheet("padding: 10px 20px;")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def _create_dca_tab(self) -> QWidget:
        """DCA 레벨 탭 생성"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 설명
        desc_label = QLabel("💡 DCA (Dollar Cost Averaging): 가격이 하락할 때 추가 매수하여 평균 단가를 낮춥니다.\n"
                           "• 하락률: 최초 매수가 대비 하락 퍼센트 (예: -3, -5, -7)\n"
                           "• 수량 비율: 최초 매수 금액 대비 비율 (100 = 같은 금액, 200 = 2배)")
        desc_label.setFont(QFont("맑은 고딕", 9))
        desc_label.setStyleSheet("background-color: #e3f2fd; padding: 10px; border-radius: 5px;")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        # 버튼
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("+ 추가")
        add_btn.setFont(QFont("맑은 고딕", 9))
        add_btn.clicked.connect(lambda: self._add_dca_level())
        btn_layout.addWidget(add_btn)

        delete_btn = QPushButton("- 삭제")
        delete_btn.setFont(QFont("맑은 고딕", 9))
        delete_btn.clicked.connect(lambda: self._delete_selected_row(self.dca_table))
        btn_layout.addWidget(delete_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # 테이블
        self.dca_table = QTableWidget()
        self.dca_table.setColumnCount(3)
        self.dca_table.setHorizontalHeaderLabels(["No", "하락률 (%)", "수량 비율 (%)"])
        self.dca_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.dca_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.dca_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.dca_table.setSelectionMode(QTableWidget.SingleSelection)  # 단일 셀 선택
        layout.addWidget(self.dca_table)

        return tab

    def _create_profit_tab(self) -> QWidget:
        """익절 레벨 탭 생성"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 설명
        desc_label = QLabel("💡 익절 (Take Profit): 목표 수익률 도달 시 자동으로 매도합니다.\n"
                           "• 수익률: 평균 매수가 대비 수익 퍼센트 (예: 2, 4, 6)\n"
                           "• 수량 비율: 현재 남은 수량 대비 매도 비율 (50 = 50% 매도, 100 = 전량 매도)")
        desc_label.setFont(QFont("맑은 고딕", 9))
        desc_label.setStyleSheet("background-color: #e8f5e9; padding: 10px; border-radius: 5px;")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        # 버튼
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("+ 추가")
        add_btn.setFont(QFont("맑은 고딕", 9))
        add_btn.clicked.connect(lambda: self._add_profit_level())
        btn_layout.addWidget(add_btn)

        delete_btn = QPushButton("- 삭제")
        delete_btn.setFont(QFont("맑은 고딕", 9))
        delete_btn.clicked.connect(lambda: self._delete_selected_row(self.profit_table))
        btn_layout.addWidget(delete_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # 테이블
        self.profit_table = QTableWidget()
        self.profit_table.setColumnCount(3)
        self.profit_table.setHorizontalHeaderLabels(["No", "수익률 (%)", "수량 비율 (%)"])
        self.profit_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.profit_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.profit_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.profit_table.setSelectionMode(QTableWidget.SingleSelection)  # 단일 셀 선택
        layout.addWidget(self.profit_table)

        return tab

    def _create_loss_tab(self) -> QWidget:
        """손절 레벨 탭 생성"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 설명
        desc_label = QLabel("💡 손절 (Stop Loss): 손실이 일정 수준 이상 발생 시 자동으로 매도합니다.\n"
                           "• 손실률: 평균 매수가 대비 손실 퍼센트 (예: -15, -20)\n"
                           "• 수량 비율: 현재 남은 수량 대비 매도 비율 (50 = 50% 매도, 100 = 전량 매도)")
        desc_label.setFont(QFont("맑은 고딕", 9))
        desc_label.setStyleSheet("background-color: #ffebee; padding: 10px; border-radius: 5px;")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        # 버튼
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("+ 추가")
        add_btn.setFont(QFont("맑은 고딕", 9))
        add_btn.clicked.connect(lambda: self._add_loss_level())
        btn_layout.addWidget(add_btn)

        delete_btn = QPushButton("- 삭제")
        delete_btn.setFont(QFont("맑은 고딕", 9))
        delete_btn.clicked.connect(lambda: self._delete_selected_row(self.loss_table))
        btn_layout.addWidget(delete_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # 테이블
        self.loss_table = QTableWidget()
        self.loss_table.setColumnCount(3)
        self.loss_table.setHorizontalHeaderLabels(["No", "손실률 (%)", "수량 비율 (%)"])
        self.loss_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.loss_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.loss_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.loss_table.setSelectionMode(QTableWidget.SingleSelection)  # 단일 셀 선택
        layout.addWidget(self.loss_table)

        return tab

    def _load_levels(self):
        """설정 파일에서 레벨 로드"""
        try:
            config = self.config_manager.load_config()
            groups = config.get("groups", {})

            if self.group_id not in groups:
                raise ValueError(f"그룹을 찾을 수 없습니다: {self.group_id}")

            group = groups[self.group_id]

            # DCA 레벨 로드
            dca_settings = group.get("dca_settings", {})
            dca_levels = dca_settings.get("levels", [])
            self._populate_dca_table(dca_levels)

            # 익절 레벨 로드
            profit_settings = group.get("profit_settings", {})
            profit_levels = profit_settings.get("levels", [])
            self._populate_profit_table(profit_levels)

            # 손절 레벨 로드
            loss_settings = group.get("loss_settings", {})
            loss_levels = loss_settings.get("levels", [])
            self._populate_loss_table(loss_levels)

            logger.info(f"✅ 레벨 로드 완료: {self.group_id}")

        except Exception as e:
            logger.error(f"❌ 레벨 로드 실패: {e}")
            QMessageBox.critical(self, "오류", f"레벨을 로드할 수 없습니다.\n{e}")

    def _populate_dca_table(self, levels: List[Dict[str, Any]]):
        """DCA 테이블 채우기"""
        self.dca_table.setRowCount(len(levels))

        for i, level in enumerate(levels):
            # No
            no_item = QTableWidgetItem(str(i + 1))
            no_item.setTextAlignment(Qt.AlignCenter)
            no_item.setFlags(no_item.flags() & ~Qt.ItemIsEditable)
            self.dca_table.setItem(i, 0, no_item)

            # 하락률 (%)
            price_ratio = level.get("price_ratio", -3.0)
            drop_item = QTableWidgetItem(f"{price_ratio:.1f}")
            drop_item.setTextAlignment(Qt.AlignCenter)
            self.dca_table.setItem(i, 1, drop_item)

            # 수량 비율 (%)
            quantity_ratio = level.get("quantity_ratio", 100)
            qty_item = QTableWidgetItem(str(int(quantity_ratio)))
            qty_item.setTextAlignment(Qt.AlignCenter)
            self.dca_table.setItem(i, 2, qty_item)

    def _populate_profit_table(self, levels: List[Dict[str, Any]]):
        """익절 테이블 채우기"""
        self.profit_table.setRowCount(len(levels))

        for i, level in enumerate(levels):
            # No
            no_item = QTableWidgetItem(str(i + 1))
            no_item.setTextAlignment(Qt.AlignCenter)
            no_item.setFlags(no_item.flags() & ~Qt.ItemIsEditable)
            self.profit_table.setItem(i, 0, no_item)

            # 수익률 (%)
            price_ratio = level.get("price_ratio", 5.0)
            price_item = QTableWidgetItem(f"{price_ratio:.1f}")
            price_item.setTextAlignment(Qt.AlignCenter)
            self.profit_table.setItem(i, 1, price_item)

            # 수량 비율 (%)
            quantity_ratio = level.get("quantity_ratio", 50)
            qty_item = QTableWidgetItem(str(int(quantity_ratio)))
            qty_item.setTextAlignment(Qt.AlignCenter)
            self.profit_table.setItem(i, 2, qty_item)

    def _populate_loss_table(self, levels: List[Dict[str, Any]]):
        """손절 테이블 채우기"""
        self.loss_table.setRowCount(len(levels))

        for i, level in enumerate(levels):
            # No
            no_item = QTableWidgetItem(str(i + 1))
            no_item.setTextAlignment(Qt.AlignCenter)
            no_item.setFlags(no_item.flags() & ~Qt.ItemIsEditable)
            self.loss_table.setItem(i, 0, no_item)

            # 손실률 (%)
            price_ratio = level.get("price_ratio", -15.0)
            price_item = QTableWidgetItem(f"{price_ratio:.1f}")
            price_item.setTextAlignment(Qt.AlignCenter)
            self.loss_table.setItem(i, 1, price_item)

            # 수량 비율 (%)
            quantity_ratio = level.get("quantity_ratio", 100)
            qty_item = QTableWidgetItem(str(int(quantity_ratio)))
            qty_item.setTextAlignment(Qt.AlignCenter)
            self.loss_table.setItem(i, 2, qty_item)

    def _add_dca_level(self):
        """DCA 레벨 추가"""
        row_count = self.dca_table.rowCount()
        self.dca_table.insertRow(row_count)

        # No
        no_item = QTableWidgetItem(str(row_count + 1))
        no_item.setTextAlignment(Qt.AlignCenter)
        no_item.setFlags(no_item.flags() & ~Qt.ItemIsEditable)
        self.dca_table.setItem(row_count, 0, no_item)

        # 기본값
        drop_item = QTableWidgetItem("-3")
        drop_item.setTextAlignment(Qt.AlignCenter)
        self.dca_table.setItem(row_count, 1, drop_item)

        qty_item = QTableWidgetItem("100")
        qty_item.setTextAlignment(Qt.AlignCenter)
        self.dca_table.setItem(row_count, 2, qty_item)

        self._update_row_numbers(self.dca_table)

    def _add_profit_level(self):
        """익절 레벨 추가"""
        row_count = self.profit_table.rowCount()
        self.profit_table.insertRow(row_count)

        # No
        no_item = QTableWidgetItem(str(row_count + 1))
        no_item.setTextAlignment(Qt.AlignCenter)
        no_item.setFlags(no_item.flags() & ~Qt.ItemIsEditable)
        self.profit_table.setItem(row_count, 0, no_item)

        # 기본값
        price_item = QTableWidgetItem("5")
        price_item.setTextAlignment(Qt.AlignCenter)
        self.profit_table.setItem(row_count, 1, price_item)

        qty_item = QTableWidgetItem("50")
        qty_item.setTextAlignment(Qt.AlignCenter)
        self.profit_table.setItem(row_count, 2, qty_item)

        self._update_row_numbers(self.profit_table)

    def _add_loss_level(self):
        """손절 레벨 추가"""
        row_count = self.loss_table.rowCount()
        self.loss_table.insertRow(row_count)

        # No
        no_item = QTableWidgetItem(str(row_count + 1))
        no_item.setTextAlignment(Qt.AlignCenter)
        no_item.setFlags(no_item.flags() & ~Qt.ItemIsEditable)
        self.loss_table.setItem(row_count, 0, no_item)

        # 기본값
        price_item = QTableWidgetItem("-15")
        price_item.setTextAlignment(Qt.AlignCenter)
        self.loss_table.setItem(row_count, 1, price_item)

        qty_item = QTableWidgetItem("100")
        qty_item.setTextAlignment(Qt.AlignCenter)
        self.loss_table.setItem(row_count, 2, qty_item)

        self._update_row_numbers(self.loss_table)

    def _delete_selected_row(self, table: QTableWidget):
        """선택된 행 삭제"""
        current_row = table.currentRow()
        if current_row >= 0:
            table.removeRow(current_row)
            self._update_row_numbers(table)
        else:
            QMessageBox.warning(self, "선택 오류", "삭제할 행을 선택하세요.")

    def _update_row_numbers(self, table: QTableWidget):
        """행 번호 업데이트"""
        for i in range(table.rowCount()):
            no_item = table.item(i, 0)
            if no_item:
                no_item.setText(str(i + 1))

    def _save_levels(self):
        """레벨 저장"""
        try:
            # 검증
            dca_levels = self._get_dca_levels()
            profit_levels = self._get_profit_levels()
            loss_levels = self._get_loss_levels()

            if not self._validate_levels(dca_levels, profit_levels, loss_levels):
                return

            # 설정 업데이트
            config = self.config_manager.load_config()
            groups = config.get("groups", {})

            if self.group_id not in groups:
                raise ValueError(f"그룹을 찾을 수 없습니다: {self.group_id}")

            group = groups[self.group_id]

            # DCA 설정 업데이트 (기존 mode 유지)
            if "dca_settings" not in group:
                group["dca_settings"] = {"mode": "auto", "levels": []}
            group["dca_settings"]["levels"] = dca_levels

            # 익절 설정 업데이트 (기존 mode 유지)
            if "profit_settings" not in group:
                group["profit_settings"] = {"mode": "auto", "levels": []}
            group["profit_settings"]["levels"] = profit_levels

            # 손절 설정 업데이트 (기존 mode 유지)
            if "loss_settings" not in group:
                group["loss_settings"] = {"mode": "auto", "levels": []}
            group["loss_settings"]["levels"] = loss_levels

            # 저장
            self.config_manager.save_config(config)

            logger.info(f"✅ 레벨 저장 완료: {self.group_id}")

            QMessageBox.information(
                self,
                "저장 완료",
                f"그룹 \"{self.group_name}\"의 레벨 설정이 저장되었습니다."
            )

            # 시그널 발생
            self.settings_saved.emit()

            self.accept()

        except Exception as e:
            logger.error(f"❌ 레벨 저장 실패: {e}")
            QMessageBox.critical(
                self,
                "오류",
                f"레벨을 저장할 수 없습니다.\n{e}"
            )

    def _get_dca_levels(self) -> List[Dict[str, Any]]:
        """DCA 테이블에서 레벨 읽기"""
        levels = []
        for i in range(self.dca_table.rowCount()):
            price_item = self.dca_table.item(i, 1)
            qty_item = self.dca_table.item(i, 2)

            if price_item and qty_item:
                levels.append({
                    "price_ratio": float(price_item.text()),
                    "quantity_ratio": int(qty_item.text())
                })
        return levels

    def _get_profit_levels(self) -> List[Dict[str, Any]]:
        """익절 테이블에서 레벨 읽기"""
        levels = []
        for i in range(self.profit_table.rowCount()):
            price_item = self.profit_table.item(i, 1)
            qty_item = self.profit_table.item(i, 2)

            if price_item and qty_item:
                levels.append({
                    "price_ratio": float(price_item.text()),
                    "quantity_ratio": int(qty_item.text())
                })
        return levels

    def _get_loss_levels(self) -> List[Dict[str, Any]]:
        """손절 테이블에서 레벨 읽기"""
        levels = []
        for i in range(self.loss_table.rowCount()):
            price_item = self.loss_table.item(i, 1)
            qty_item = self.loss_table.item(i, 2)

            if price_item and qty_item:
                levels.append({
                    "price_ratio": float(price_item.text()),
                    "quantity_ratio": int(qty_item.text())
                })
        return levels

    def _validate_levels(self, dca_levels: List[Dict[str, Any]],
                        profit_levels: List[Dict[str, Any]],
                        loss_levels: List[Dict[str, Any]]) -> bool:
        """레벨 검증"""
        try:
            # DCA 검증: 하락률은 음수이고 순서대로 감소
            for i, level in enumerate(dca_levels):
                price_ratio = level["price_ratio"]
                quantity_ratio = level["quantity_ratio"]

                if price_ratio >= 0:
                    QMessageBox.warning(
                        self,
                        "검증 오류",
                        f"DCA 레벨 {i+1}: 하락률은 음수여야 합니다. (현재: {price_ratio}%)"
                    )
                    return False

                if quantity_ratio <= 0:
                    QMessageBox.warning(
                        self,
                        "검증 오류",
                        f"DCA 레벨 {i+1}: 수량 비율은 양수여야 합니다. (현재: {quantity_ratio}%)"
                    )
                    return False

                if i > 0 and price_ratio >= dca_levels[i-1]["price_ratio"]:
                    QMessageBox.warning(
                        self,
                        "검증 오류",
                        f"DCA 레벨 {i+1}: 하락률이 이전 레벨보다 작아야 합니다.\n"
                        f"이전: {dca_levels[i-1]['price_ratio']}%, 현재: {price_ratio}%"
                    )
                    return False

            # 익절 검증: 수익률 > 0, 순서대로 증가
            for i, level in enumerate(profit_levels):
                price_ratio = level["price_ratio"]
                quantity_ratio = level["quantity_ratio"]

                if price_ratio <= 0:
                    QMessageBox.warning(
                        self,
                        "검증 오류",
                        f"익절 레벨 {i+1}: 수익률은 양수여야 합니다. (현재: {price_ratio}%)"
                    )
                    return False

                if quantity_ratio <= 0 or quantity_ratio > 100:
                    QMessageBox.warning(
                        self,
                        "검증 오류",
                        f"익절 레벨 {i+1}: 수량 비율은 1~100 범위여야 합니다. (현재: {quantity_ratio}%)"
                    )
                    return False

                if i > 0 and price_ratio <= profit_levels[i-1]["price_ratio"]:
                    QMessageBox.warning(
                        self,
                        "검증 오류",
                        f"익절 레벨 {i+1}: 수익률이 이전 레벨보다 커야 합니다.\n"
                        f"이전: {profit_levels[i-1]['price_ratio']}%, 현재: {price_ratio}%"
                    )
                    return False

            # 손절 검증: 손실률 < 0
            for i, level in enumerate(loss_levels):
                price_ratio = level["price_ratio"]
                quantity_ratio = level["quantity_ratio"]

                if price_ratio >= 0:
                    QMessageBox.warning(
                        self,
                        "검증 오류",
                        f"손절 레벨 {i+1}: 손실률은 음수여야 합니다. (현재: {price_ratio}%)"
                    )
                    return False

                if quantity_ratio <= 0 or quantity_ratio > 100:
                    QMessageBox.warning(
                        self,
                        "검증 오류",
                        f"손절 레벨 {i+1}: 수량 비율은 1~100 범위여야 합니다. (현재: {quantity_ratio}%)"
                    )
                    return False

            return True

        except ValueError as e:
            QMessageBox.warning(
                self,
                "입력 오류",
                f"올바른 숫자를 입력하세요.\n{e}"
            )
            return False
