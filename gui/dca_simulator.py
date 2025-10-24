"""
DCA Simulator - DCA 전략 시뮬레이터
사용자가 파라미터를 조정하며 DCA 결과를 미리 계산
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QSpinBox, QDoubleSpinBox, QPushButton,
    QTextEdit, QGroupBox, QTableWidget, QTableWidgetItem,
    QHeaderView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class DcaSimulatorDialog(QDialog):
    """
    DCA 시뮬레이터 다이얼로그

    현재가와 하락률을 입력하면 DCA 레벨별 매수 계산
    """

    def __init__(self, parent=None, initial_price=100000000, order_amount=10000):
        super().__init__(parent)

        self.initial_price = initial_price  # 현재가 (기본값: 1억원)
        self.order_amount = order_amount    # 주문 금액 (기본값: 10,000원)

        self.setWindowTitle("💰 DCA 전략 시뮬레이터")
        self.setMinimumSize(700, 600)

        self._init_ui()
        self._calculate_dca()  # 초기 계산

    def _init_ui(self):
        """UI 초기화"""
        main_layout = QVBoxLayout(self)

        # 상단: 입력 파라미터
        input_group = QGroupBox("📊 DCA 파라미터 설정")
        input_layout = QFormLayout()

        # 현재가 입력
        self.price_spin = QSpinBox()
        self.price_spin.setRange(1000, 1000000000)
        self.price_spin.setValue(self.initial_price)
        self.price_spin.setSuffix(" 원")
        self.price_spin.setSingleStep(100000)
        self.price_spin.valueChanged.connect(self._calculate_dca)
        input_layout.addRow("📈 현재가:", self.price_spin)

        # 주문 금액
        self.amount_spin = QSpinBox()
        self.amount_spin.setRange(5000, 1000000)
        self.amount_spin.setValue(self.order_amount)
        self.amount_spin.setSuffix(" 원")
        self.amount_spin.setSingleStep(1000)
        self.amount_spin.valueChanged.connect(self._calculate_dca)
        input_layout.addRow("💰 주문 금액:", self.amount_spin)

        # DCA 레벨 수
        self.levels_spin = QSpinBox()
        self.levels_spin.setRange(1, 10)
        self.levels_spin.setValue(5)
        self.levels_spin.valueChanged.connect(self._calculate_dca)
        input_layout.addRow("🔢 DCA 레벨 수:", self.levels_spin)

        # 하락 간격 %
        self.drop_interval_spin = QDoubleSpinBox()
        self.drop_interval_spin.setRange(1.0, 20.0)
        self.drop_interval_spin.setValue(5.0)
        self.drop_interval_spin.setSuffix(" %")
        self.drop_interval_spin.setDecimals(1)
        self.drop_interval_spin.setSingleStep(0.5)
        self.drop_interval_spin.valueChanged.connect(self._calculate_dca)
        input_layout.addRow("📉 하락 간격:", self.drop_interval_spin)

        # DCA 배수
        self.multiplier_spin = QDoubleSpinBox()
        self.multiplier_spin.setRange(1.0, 5.0)
        self.multiplier_spin.setValue(2.0)
        self.multiplier_spin.setDecimals(1)
        self.multiplier_spin.setSingleStep(0.1)
        self.multiplier_spin.valueChanged.connect(self._calculate_dca)
        input_layout.addRow("⚡ DCA 배수:", self.multiplier_spin)

        # 익절 목표 %
        self.target_spin = QDoubleSpinBox()
        self.target_spin.setRange(1.0, 50.0)
        self.target_spin.setValue(10.0)
        self.target_spin.setSuffix(" %")
        self.target_spin.setDecimals(1)
        self.target_spin.setSingleStep(0.5)
        self.target_spin.valueChanged.connect(self._calculate_dca)
        input_layout.addRow("🎯 익절 목표:", self.target_spin)

        input_group.setLayout(input_layout)
        main_layout.addWidget(input_group)

        # 중단: DCA 테이블
        table_group = QGroupBox("📋 DCA 레벨별 상세")
        table_layout = QVBoxLayout()

        self.dca_table = QTableWidget()
        self.dca_table.setColumnCount(5)
        self.dca_table.setHorizontalHeaderLabels([
            "레벨", "하락률", "진입가", "매수금액", "누적투자"
        ])

        # 컬럼 크기 자동 조정
        header = self.dca_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)

        self.dca_table.setFont(QFont("Consolas", 10))
        table_layout.addWidget(self.dca_table)

        table_group.setLayout(table_layout)
        main_layout.addWidget(table_group)

        # 하단: 결과 요약
        result_group = QGroupBox("📊 시뮬레이션 결과")
        result_layout = QVBoxLayout()

        self.result_label = QLabel()
        self.result_label.setFont(QFont("Consolas", 11))
        self.result_label.setWordWrap(True)
        self.result_label.setStyleSheet("""
            background-color: #f0f0f0;
            padding: 15px;
            border-radius: 5px;
            border: 1px solid #ccc;
        """)
        result_layout.addWidget(self.result_label)

        result_group.setLayout(result_layout)
        main_layout.addWidget(result_group)

        # 버튼
        button_layout = QHBoxLayout()

        reset_btn = QPushButton("🔄 기본값 복원")
        reset_btn.clicked.connect(self._reset_defaults)
        button_layout.addWidget(reset_btn)

        close_btn = QPushButton("✅ 닫기")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)

        main_layout.addLayout(button_layout)

    def _calculate_dca(self):
        """DCA 계산"""
        current_price = self.price_spin.value()
        amount = self.amount_spin.value()
        levels = self.levels_spin.value()
        drop_interval = self.drop_interval_spin.value()
        multiplier = self.multiplier_spin.value()
        target_pct = self.target_spin.value()

        # 테이블 초기화
        self.dca_table.setRowCount(levels)

        total_invested = 0
        total_quantity = 0

        dca_data = []

        for i in range(levels):
            # 레벨 (1부터 시작)
            level = i + 1

            # 하락률 계산
            drop_pct = drop_interval * i

            # 진입가 계산
            entry_price = current_price * (1 - drop_pct / 100)

            # 매수 금액 계산 (배수 적용)
            if i == 0:
                buy_amount = amount
            else:
                buy_amount = amount * (multiplier ** i)

            # 매수 수량 계산
            buy_quantity = buy_amount / entry_price

            # 누적
            total_invested += buy_amount
            total_quantity += buy_quantity

            dca_data.append({
                'level': level,
                'drop_pct': drop_pct,
                'entry_price': entry_price,
                'buy_amount': buy_amount,
                'total_invested': total_invested
            })

            # 테이블에 추가
            self.dca_table.setItem(i, 0, QTableWidgetItem(f"{level}"))
            self.dca_table.setItem(i, 1, QTableWidgetItem(f"-{drop_pct:.1f}%"))
            self.dca_table.setItem(i, 2, QTableWidgetItem(f"{entry_price:,.0f}원"))
            self.dca_table.setItem(i, 3, QTableWidgetItem(f"{buy_amount:,.0f}원"))
            self.dca_table.setItem(i, 4, QTableWidgetItem(f"{total_invested:,.0f}원"))

            # 가운데 정렬
            for col in range(5):
                self.dca_table.item(i, col).setTextAlignment(Qt.AlignCenter)

        # 평균 단가 계산
        avg_price = total_invested / total_quantity if total_quantity > 0 else 0

        # 익절 목표가 계산
        target_price = avg_price * (1 + target_pct / 100)

        # 익절 시 수익
        profit = (target_price - avg_price) * total_quantity
        profit_pct = (profit / total_invested) * 100 if total_invested > 0 else 0

        # 결과 표시
        result_text = f"""
📊 DCA 시뮬레이션 결과

💰 총 투자금:     {total_invested:,.0f}원
📈 총 매수 수량:   {total_quantity:.8f} BTC
💵 평균 단가:      {avg_price:,.0f}원

🎯 익절 목표:      {target_pct}% (+{target_pct}%)
💹 익절가:         {target_price:,.0f}원
✅ 익절 시 수익:   {profit:,.0f}원 (+{profit_pct:.2f}%)

📉 최대 하락:      -{drop_interval * (levels - 1):.1f}%
        """.strip()

        self.result_label.setText(result_text)

    def _reset_defaults(self):
        """기본값 복원"""
        self.price_spin.setValue(100000000)  # 1억원
        self.amount_spin.setValue(10000)     # 1만원
        self.levels_spin.setValue(5)         # 5레벨
        self.drop_interval_spin.setValue(5.0)  # 5% 간격
        self.multiplier_spin.setValue(2.0)   # 2배수
        self.target_spin.setValue(10.0)      # 10% 익절


# 테스트 코드
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    dialog = DcaSimulatorDialog()
    dialog.exec()

    sys.exit(app.exec())
