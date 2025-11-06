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
        desc_label = QLabel("💡 DCA (Dollar Cost Averaging): 가격이 하락할 때 추가 매수하여 평균 단가를 낮춥니다.")
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
        self.dca_table.setHorizontalHeaderLabels(["No", "하락률 (%)", "매수 금액 (KRW)"])
        self.dca_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.dca_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.dca_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.dca_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.dca_table)

        return tab

    def _create_profit_tab(self) -> QWidget:
        """익절 레벨 탭 생성"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 설명
        desc_label = QLabel("💡 익절 (Take Profit): 목표 수익률 도달 시 자동으로 매도합니다.")
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
        self.profit_table.setHorizontalHeaderLabels(["No", "가격 비율", "수량 비율"])
        self.profit_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.profit_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.profit_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.profit_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.profit_table)

        return tab

    def _create_loss_tab(self) -> QWidget:
        """손절 레벨 탭 생성"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 설명
        desc_label = QLabel("💡 손절 (Stop Loss): 손실이 일정 수준 이상 발생 시 자동으로 매도합니다.")
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
        self.loss_table.setHorizontalHeaderLabels(["No", "가격 비율", "수량 비율"])
        self.loss_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.loss_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.loss_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.loss_table.setSelectionBehavior(QTableWidget.SelectRows)
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
            profit_loss_settings = group.get("profit_loss_settings", {})
            profit_targets = profit_loss_settings.get("profit_targets", [])
            self._populate_profit_table(profit_targets)

            # 손절 레벨 로드
            stop_losses = profit_loss_settings.get("stop_losses", [])
            self._populate_loss_table(stop_losses)

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
            drop_item = QTableWidgetItem(str(level.get("price_drop_pct", -3.0)))
            drop_item.setTextAlignment(Qt.AlignCenter)
            self.dca_table.setItem(i, 1, drop_item)

            # 매수 금액 (KRW)
            amount_item = QTableWidgetItem(str(level.get("buy_amount_krw", 50000)))
            amount_item.setTextAlignment(Qt.AlignCenter)
            self.dca_table.setItem(i, 2, amount_item)

    def _populate_profit_table(self, targets: List[Dict[str, Any]]):
        """익절 테이블 채우기"""
        self.profit_table.setRowCount(len(targets))

        for i, target in enumerate(targets):
            # No
            no_item = QTableWidgetItem(str(i + 1))
            no_item.setTextAlignment(Qt.AlignCenter)
            no_item.setFlags(no_item.flags() & ~Qt.ItemIsEditable)
            self.profit_table.setItem(i, 0, no_item)

            # 가격 비율
            price_item = QTableWidgetItem(str(target.get("price_ratio", 1.05)))
            price_item.setTextAlignment(Qt.AlignCenter)
            self.profit_table.setItem(i, 1, price_item)

            # 수량 비율
            qty_item = QTableWidgetItem(str(target.get("quantity_ratio", 0.5)))
            qty_item.setTextAlignment(Qt.AlignCenter)
            self.profit_table.setItem(i, 2, qty_item)

    def _populate_loss_table(self, losses: List[Dict[str, Any]]):
        """손절 테이블 채우기"""
        self.loss_table.setRowCount(len(losses))

        for i, loss in enumerate(losses):
            # No
            no_item = QTableWidgetItem(str(i + 1))
            no_item.setTextAlignment(Qt.AlignCenter)
            no_item.setFlags(no_item.flags() & ~Qt.ItemIsEditable)
            self.loss_table.setItem(i, 0, no_item)

            # 가격 비율
            price_item = QTableWidgetItem(str(loss.get("price_ratio", 0.95)))
            price_item.setTextAlignment(Qt.AlignCenter)
            self.loss_table.setItem(i, 1, price_item)

            # 수량 비율
            qty_item = QTableWidgetItem(str(loss.get("quantity_ratio", 1.0)))
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
        drop_item = QTableWidgetItem("-3.0")
        drop_item.setTextAlignment(Qt.AlignCenter)
        self.dca_table.setItem(row_count, 1, drop_item)

        amount_item = QTableWidgetItem("50000")
        amount_item.setTextAlignment(Qt.AlignCenter)
        self.dca_table.setItem(row_count, 2, amount_item)

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
        price_item = QTableWidgetItem("1.05")
        price_item.setTextAlignment(Qt.AlignCenter)
        self.profit_table.setItem(row_count, 1, price_item)

        qty_item = QTableWidgetItem("0.5")
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
        price_item = QTableWidgetItem("0.95")
        price_item.setTextAlignment(Qt.AlignCenter)
        self.loss_table.setItem(row_count, 1, price_item)

        qty_item = QTableWidgetItem("1.0")
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
            profit_targets = self._get_profit_targets()
            stop_losses = self._get_stop_losses()

            if not self._validate_levels(dca_levels, profit_targets, stop_losses):
                return

            # 설정 업데이트
            config = self.config_manager.load_config()
            groups = config.get("groups", {})

            if self.group_id not in groups:
                raise ValueError(f"그룹을 찾을 수 없습니다: {self.group_id}")

            group = groups[self.group_id]

            # DCA 설정 업데이트
            if "dca_settings" not in group:
                group["dca_settings"] = {"enabled": True}
            group["dca_settings"]["levels"] = dca_levels

            # 익절/손절 설정 업데이트
            if "profit_loss_settings" not in group:
                group["profit_loss_settings"] = {}
            group["profit_loss_settings"]["profit_targets"] = profit_targets
            group["profit_loss_settings"]["stop_losses"] = stop_losses

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
            drop_item = self.dca_table.item(i, 1)
            amount_item = self.dca_table.item(i, 2)

            if drop_item and amount_item:
                levels.append({
                    "price_drop_pct": float(drop_item.text()),
                    "buy_amount_krw": int(amount_item.text())
                })
        return levels

    def _get_profit_targets(self) -> List[Dict[str, Any]]:
        """익절 테이블에서 레벨 읽기"""
        targets = []
        for i in range(self.profit_table.rowCount()):
            price_item = self.profit_table.item(i, 1)
            qty_item = self.profit_table.item(i, 2)

            if price_item and qty_item:
                targets.append({
                    "price_ratio": float(price_item.text()),
                    "quantity_ratio": float(qty_item.text())
                })
        return targets

    def _get_stop_losses(self) -> List[Dict[str, Any]]:
        """손절 테이블에서 레벨 읽기"""
        losses = []
        for i in range(self.loss_table.rowCount()):
            price_item = self.loss_table.item(i, 1)
            qty_item = self.loss_table.item(i, 2)

            if price_item and qty_item:
                losses.append({
                    "price_ratio": float(price_item.text()),
                    "quantity_ratio": float(qty_item.text())
                })
        return losses

    def _validate_levels(self, dca_levels: List[Dict[str, Any]],
                        profit_targets: List[Dict[str, Any]],
                        stop_losses: List[Dict[str, Any]]) -> bool:
        """레벨 검증"""
        try:
            # DCA 검증: 하락률은 음수이고 순서대로 감소
            for i, level in enumerate(dca_levels):
                price_drop = level["price_drop_pct"]
                buy_amount = level["buy_amount_krw"]

                if price_drop >= 0:
                    QMessageBox.warning(
                        self,
                        "검증 오류",
                        f"DCA 레벨 {i+1}: 하락률은 음수여야 합니다. (현재: {price_drop}%)"
                    )
                    return False

                if buy_amount <= 0:
                    QMessageBox.warning(
                        self,
                        "검증 오류",
                        f"DCA 레벨 {i+1}: 매수 금액은 양수여야 합니다. (현재: {buy_amount}원)"
                    )
                    return False

                if i > 0 and price_drop >= dca_levels[i-1]["price_drop_pct"]:
                    QMessageBox.warning(
                        self,
                        "검증 오류",
                        f"DCA 레벨 {i+1}: 하락률이 이전 레벨보다 작아야 합니다.\n"
                        f"이전: {dca_levels[i-1]['price_drop_pct']}%, 현재: {price_drop}%"
                    )
                    return False

            # 익절 검증: 가격 비율 > 1.0, 순서대로 증가
            for i, target in enumerate(profit_targets):
                price_ratio = target["price_ratio"]
                qty_ratio = target["quantity_ratio"]

                if price_ratio <= 1.0:
                    QMessageBox.warning(
                        self,
                        "검증 오류",
                        f"익절 레벨 {i+1}: 가격 비율은 1.0보다 커야 합니다. (현재: {price_ratio})"
                    )
                    return False

                if qty_ratio <= 0 or qty_ratio > 1.0:
                    QMessageBox.warning(
                        self,
                        "검증 오류",
                        f"익절 레벨 {i+1}: 수량 비율은 0 < ratio <= 1.0 범위여야 합니다. (현재: {qty_ratio})"
                    )
                    return False

                if i > 0 and price_ratio <= profit_targets[i-1]["price_ratio"]:
                    QMessageBox.warning(
                        self,
                        "검증 오류",
                        f"익절 레벨 {i+1}: 가격 비율이 이전 레벨보다 커야 합니다.\n"
                        f"이전: {profit_targets[i-1]['price_ratio']}, 현재: {price_ratio}"
                    )
                    return False

            # 손절 검증: 가격 비율 < 1.0
            for i, loss in enumerate(stop_losses):
                price_ratio = loss["price_ratio"]
                qty_ratio = loss["quantity_ratio"]

                if price_ratio >= 1.0:
                    QMessageBox.warning(
                        self,
                        "검증 오류",
                        f"손절 레벨 {i+1}: 가격 비율은 1.0보다 작아야 합니다. (현재: {price_ratio})"
                    )
                    return False

                if qty_ratio <= 0 or qty_ratio > 1.0:
                    QMessageBox.warning(
                        self,
                        "검증 오류",
                        f"손절 레벨 {i+1}: 수량 비율은 0 < ratio <= 1.0 범위여야 합니다. (현재: {qty_ratio})"
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
