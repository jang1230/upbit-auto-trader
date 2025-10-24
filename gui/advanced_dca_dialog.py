"""
Advanced DCA Settings Dialog
고급 DCA 전략 설정 다이얼로그

5단계 DCA 레벨별 설정:
- 하락률, 매수 비중, 주문 금액 개별 설정
- 실시간 평균 단가/익절가/손절가 계산
- JSON 파일로 설정 저장/로드
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QSpinBox, QDoubleSpinBox, QPushButton,
    QTableWidget, QTableWidgetItem, QGroupBox,
    QHeaderView, QMessageBox, QCheckBox, QTabWidget
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from gui.dca_config import (
    DcaConfigManager, AdvancedDcaConfig, DcaLevelConfig,
    TakeProfitLevel, StopLossLevel
)


class AdvancedDcaDialog(QDialog):
    """
    고급 DCA 설정 다이얼로그
    
    5단계 DCA 레벨별 설정 + 익절/손절 설정
    """
    
    # 설정 변경 시그널
    config_changed = Signal(AdvancedDcaConfig)
    
    def __init__(self, parent=None, current_price: float = 100000000):
        super().__init__(parent)
        
        self.current_price = current_price  # 현재가
        self.config_manager = DcaConfigManager()
        self.config = self.config_manager.load()
        
        self.setWindowTitle("⚙️ 고급 DCA 전략 설정")
        self.setMinimumSize(900, 700)
        
        self._init_ui()
        self._load_config_to_ui()
        self._update_simulation()
    
    def _init_ui(self):
        """UI 초기화"""
        main_layout = QVBoxLayout(self)

        # 상단: 현재가 표시
        header_layout = QHBoxLayout()

        current_price_label = QLabel(f"📈 현재가: {self.current_price:,.0f}원")
        current_price_label.setFont(QFont("Consolas", 12, QFont.Bold))
        header_layout.addWidget(current_price_label)

        header_layout.addStretch()

        # DCA 활성화 체크박스
        self.enabled_checkbox = QCheckBox("DCA 전략 활성화")
        self.enabled_checkbox.setChecked(self.config.enabled)
        self.enabled_checkbox.stateChanged.connect(self._on_enabled_changed)
        header_layout.addWidget(self.enabled_checkbox)

        main_layout.addLayout(header_layout)

        # 탭 위젯 생성
        tab_widget = QTabWidget()

        # 📊 매수 전략 탭
        buy_tab = self._create_buy_strategy_tab()
        tab_widget.addTab(buy_tab, "📊 매수 전략")

        # 💰 매도 전략 탭
        sell_tab = self._create_sell_strategy_tab()
        tab_widget.addTab(sell_tab, "💰 매도 전략")

        main_layout.addWidget(tab_widget)

        # 하단: 시뮬레이션 결과
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
        reset_btn.clicked.connect(self._reset_to_default)
        button_layout.addWidget(reset_btn)
        
        button_layout.addStretch()
        
        cancel_btn = QPushButton("❌ 취소")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("💾 저장")
        save_btn.clicked.connect(self._save_config)
        button_layout.addWidget(save_btn)
        
        main_layout.addLayout(button_layout)

    def _create_buy_strategy_tab(self):
        """📊 매수 전략 탭 생성"""
        tab = QGroupBox()
        layout = QVBoxLayout()

        # 총 자산 + 레벨 개수 입력
        capital_layout = QHBoxLayout()

        # 총 자산
        capital_label = QLabel("💰 총 투자 가능 자산:")
        capital_label.setFont(QFont("Arial", 11, QFont.Bold))
        capital_layout.addWidget(capital_label)

        self.total_capital_spin = QSpinBox()
        self.total_capital_spin.setRange(5000, 1000000000)  # 5천원 ~ 10억원 (Upbit 최소 주문 금액)
        self.total_capital_spin.setValue(self.config.total_capital)
        self.total_capital_spin.setSuffix(" 원")
        self.total_capital_spin.setSingleStep(5000)
        self.total_capital_spin.setFont(QFont("Consolas", 11))
        self.total_capital_spin.setToolTip("비중(%) ↔ 금액(원) 계산 기준")
        self.total_capital_spin.valueChanged.connect(self._on_total_capital_changed)
        capital_layout.addWidget(self.total_capital_spin)

        capital_layout.addStretch()

        # 레벨 개수 선택
        level_count_label = QLabel("📊 DCA 레벨 개수:")
        level_count_label.setFont(QFont("Arial", 11, QFont.Bold))
        capital_layout.addWidget(level_count_label)

        self.level_count_spin = QSpinBox()
        self.level_count_spin.setRange(1, 10)  # 1~10단계
        self.level_count_spin.setValue(len(self.config.levels))
        self.level_count_spin.setSuffix(" 단계")
        self.level_count_spin.setFont(QFont("Consolas", 11))
        self.level_count_spin.setToolTip("DCA 분할 매수 단계 개수 (1~10)")
        self.level_count_spin.valueChanged.connect(self._on_level_count_changed)
        capital_layout.addWidget(self.level_count_spin)

        capital_layout.addStretch()

        info_label = QLabel("ℹ️ 비중과 금액은 자동으로 연동됩니다")
        info_label.setStyleSheet("color: #666; font-size: 10px;")
        capital_layout.addWidget(info_label)

        layout.addLayout(capital_layout)

        # DCA 레벨 테이블
        self.table_group = QGroupBox(f"📊 DCA 레벨 설정 ({len(self.config.levels)}단계)")
        table_layout = QVBoxLayout()

        self.dca_table = QTableWidget()
        self.dca_table.setRowCount(len(self.config.levels))
        self.dca_table.setColumnCount(6)
        self.dca_table.setHorizontalHeaderLabels([
            "레벨", "하락률 (%)", "매수 비중 (%)", "주문 금액 (원)", "진입가 (원)", "예상 수량"
        ])

        # 컬럼 크기 조정
        header = self.dca_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)

        self.dca_table.setFont(QFont("Consolas", 10))
        self.dca_table.cellChanged.connect(self._on_table_changed)

        table_layout.addWidget(self.dca_table)

        # 테이블 하단: 프리셋 버튼
        preset_layout = QHBoxLayout()

        aggressive_btn = QPushButton("🔥 공격형")
        aggressive_btn.setToolTip("하락률 크고, 후반 비중 높음")
        aggressive_btn.clicked.connect(lambda: self._apply_preset("aggressive"))
        preset_layout.addWidget(aggressive_btn)

        balanced_btn = QPushButton("⚖️ 균형형")
        balanced_btn.setToolTip("중간 하락률, 균등 비중")
        balanced_btn.clicked.connect(lambda: self._apply_preset("balanced"))
        preset_layout.addWidget(balanced_btn)

        conservative_btn = QPushButton("🛡️ 안정형")
        conservative_btn.setToolTip("작은 하락률, 초반 비중 높음")
        conservative_btn.clicked.connect(lambda: self._apply_preset("conservative"))
        preset_layout.addWidget(conservative_btn)

        table_layout.addLayout(preset_layout)

        self.table_group.setLayout(table_layout)
        layout.addWidget(self.table_group)

        tab.setLayout(layout)
        return tab

    def _create_sell_strategy_tab(self):
        """💰 매도 전략 탭 생성"""
        tab = QGroupBox()
        layout = QVBoxLayout()

        # 익절/손절 설정 (다단계 테이블)
        tp_sl_layout = QHBoxLayout()

        # 📈 다단계 익절 설정
        tp_group = QGroupBox("📈 다단계 익절 설정")
        tp_layout = QVBoxLayout()

        # 익절 테이블
        self.tp_table = QTableWidget()
        self.tp_table.setRowCount(len(self.config.take_profit_levels) if self.config.is_multi_level_tp_enabled() else 1)
        self.tp_table.setColumnCount(3)
        self.tp_table.setHorizontalHeaderLabels(["레벨", "수익률 (%)", "매도비율 (%, 남은 수량 기준)"])
        self.tp_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tp_table.setFont(QFont("Consolas", 10))
        self.tp_table.setToolTip("각 레벨에서 현재 남은 보유량의 N%를 매도합니다.\n예: 1 BTC 보유 → L1(30%) → 0.7 BTC 남음 → L2(50%) → 0.35 BTC 남음")
        self.tp_table.cellChanged.connect(self._on_tp_table_changed)
        tp_layout.addWidget(self.tp_table)

        # 익절 버튼
        tp_btn_layout = QHBoxLayout()
        tp_add_btn = QPushButton("➕ 레벨 추가")
        tp_add_btn.clicked.connect(self._add_tp_level)
        tp_btn_layout.addWidget(tp_add_btn)

        tp_remove_btn = QPushButton("➖ 레벨 삭제")
        tp_remove_btn.clicked.connect(self._remove_tp_level)
        tp_btn_layout.addWidget(tp_remove_btn)

        tp_single_btn = QPushButton("🔄 단일/다단계")
        tp_single_btn.setToolTip("단일 모드 ↔ 다단계 모드 전환")
        tp_single_btn.clicked.connect(self._toggle_tp_single_mode)
        tp_btn_layout.addWidget(tp_single_btn)

        tp_layout.addLayout(tp_btn_layout)
        tp_group.setLayout(tp_layout)
        tp_sl_layout.addWidget(tp_group)

        # 📉 다단계 손절 설정
        sl_group = QGroupBox("📉 다단계 손절 설정")
        sl_layout = QVBoxLayout()

        # 손절 테이블
        self.sl_table = QTableWidget()
        self.sl_table.setRowCount(len(self.config.stop_loss_levels) if self.config.is_multi_level_sl_enabled() else 1)
        self.sl_table.setColumnCount(3)
        self.sl_table.setHorizontalHeaderLabels(["레벨", "손실률 (%)", "매도비율 (%, 남은 수량 기준)"])
        self.sl_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.sl_table.setFont(QFont("Consolas", 10))
        self.sl_table.setToolTip("각 레벨에서 현재 남은 보유량의 N%를 매도합니다.\n예: 1 BTC 보유 → L1(50%) → 0.5 BTC 남음 → L2(100%) → 전량 청산")
        self.sl_table.cellChanged.connect(self._on_sl_table_changed)
        sl_layout.addWidget(self.sl_table)

        # 손절 버튼
        sl_btn_layout = QHBoxLayout()
        sl_add_btn = QPushButton("➕ 레벨 추가")
        sl_add_btn.clicked.connect(self._add_sl_level)
        sl_btn_layout.addWidget(sl_add_btn)

        sl_remove_btn = QPushButton("➖ 레벨 삭제")
        sl_remove_btn.clicked.connect(self._remove_sl_level)
        sl_btn_layout.addWidget(sl_remove_btn)

        sl_single_btn = QPushButton("🔄 단일/다단계")
        sl_single_btn.setToolTip("단일 모드 ↔ 다단계 모드 전환")
        sl_single_btn.clicked.connect(self._toggle_sl_single_mode)
        sl_btn_layout.addWidget(sl_single_btn)

        sl_layout.addLayout(sl_btn_layout)
        sl_group.setLayout(sl_layout)
        tp_sl_layout.addWidget(sl_group)

        layout.addLayout(tp_sl_layout)

        tab.setLayout(layout)
        return tab

    def _load_config_to_ui(self):
        """설정을 UI에 로드"""
        # DCA 테이블 업데이트 방지
        self.dca_table.blockSignals(True)

        for i, level_config in enumerate(self.config.levels):
            # 레벨 (읽기 전용)
            level_item = QTableWidgetItem(f"{level_config.level}")
            level_item.setFlags(level_item.flags() & ~Qt.ItemIsEditable)
            level_item.setTextAlignment(Qt.AlignCenter)
            self.dca_table.setItem(i, 0, level_item)

            # 하락률
            drop_item = QTableWidgetItem(f"{level_config.drop_pct:.1f}")
            drop_item.setTextAlignment(Qt.AlignCenter)
            self.dca_table.setItem(i, 1, drop_item)

            # 매수 비중
            weight_item = QTableWidgetItem(f"{level_config.weight_pct:.1f}")
            weight_item.setTextAlignment(Qt.AlignCenter)
            self.dca_table.setItem(i, 2, weight_item)

            # 주문 금액
            amount_item = QTableWidgetItem(f"{level_config.order_amount}")
            amount_item.setTextAlignment(Qt.AlignCenter)
            self.dca_table.setItem(i, 3, amount_item)

            # 진입가 (계산, 읽기 전용)
            entry_price = self.current_price * (1 - level_config.drop_pct / 100)
            entry_item = QTableWidgetItem(f"{entry_price:,.0f}")
            entry_item.setFlags(entry_item.flags() & ~Qt.ItemIsEditable)
            entry_item.setTextAlignment(Qt.AlignCenter)
            entry_item.setForeground(QColor(0, 100, 200))
            self.dca_table.setItem(i, 4, entry_item)

            # 예상 수량 (계산, 읽기 전용)
            quantity = level_config.order_amount / entry_price
            quantity_item = QTableWidgetItem(f"{quantity:.8f}")
            quantity_item.setFlags(quantity_item.flags() & ~Qt.ItemIsEditable)
            quantity_item.setTextAlignment(Qt.AlignCenter)
            quantity_item.setForeground(QColor(0, 150, 0))
            self.dca_table.setItem(i, 5, quantity_item)

        self.dca_table.blockSignals(False)

        # 익절 테이블 로드
        self._load_tp_table()

        # 손절 테이블 로드
        self._load_sl_table()
    
    def _on_table_changed(self, row: int, col: int):
        """테이블 셀 변경 시"""
        # 편집 가능한 컬럼만 처리 (하락률, 비중, 금액)
        if col not in [1, 2, 3]:
            return

        try:
            # 시그널 블록 (무한 루프 방지)
            self.dca_table.blockSignals(True)

            item = self.dca_table.item(row, col)
            value = float(item.text().replace(',', ''))

            level_config = self.config.levels[row]

            if col == 1:  # 하락률
                level_config.drop_pct = value

            elif col == 2:  # 매수 비중 변경 → 금액 자동 계산
                level_config.weight_pct = value

                # 🔧 비중 → 금액 계산
                calculated_amount = self.config.calculate_amount_from_weight(value)
                level_config.order_amount = calculated_amount

                # 금액 컬럼 업데이트
                amount_item = self.dca_table.item(row, 3)
                amount_item.setText(f"{calculated_amount:,}")

            elif col == 3:  # 주문 금액 변경 → 비중 자동 계산
                order_amount = int(value)
                level_config.order_amount = order_amount

                # 🔧 금액 → 비중 계산
                calculated_weight = self.config.calculate_weight_from_amount(order_amount)
                level_config.weight_pct = calculated_weight

                # 비중 컬럼 업데이트
                weight_item = self.dca_table.item(row, 2)
                weight_item.setText(f"{calculated_weight:.1f}")

            # 진입가/수량 재계산
            self._update_calculated_columns(row)
            self._update_simulation()

            # 시그널 재활성화
            self.dca_table.blockSignals(False)

        except ValueError:
            self.dca_table.blockSignals(False)
            pass
    
    def _update_calculated_columns(self, row: int):
        """진입가/수량 컬럼 재계산"""
        level_config = self.config.levels[row]
        
        # 진입가
        entry_price = self.current_price * (1 - level_config.drop_pct / 100)
        entry_item = self.dca_table.item(row, 4)
        entry_item.setText(f"{entry_price:,.0f}")
        
        # 수량
        quantity = level_config.order_amount / entry_price
        quantity_item = self.dca_table.item(row, 5)
        quantity_item.setText(f"{quantity:.8f}")
    
    def _update_simulation(self):
        """시뮬레이션 결과 업데이트"""
        # 목표가 계산
        targets = self.config.calculate_targets(self.current_price)

        # 총 비중 합계 계산
        total_weight = sum(level.weight_pct for level in self.config.levels)

        # 결과 표시
        result_text = f"""
📊 DCA 전략 시뮬레이션

💰 총 자산:        {self.config.total_capital:,.0f}원
💸 총 투자금:      {targets['total_invested']:,.0f}원
📊 총 비중:        {total_weight:.1f}%"""

        # 비중 초과 경고
        if total_weight > 100:
            result_text += f" ⚠️ (초과!)"

        result_text += f"""

📈 총 매수 수량:   {targets['total_quantity']:.8f} BTC
💵 평균 단가:      {targets['avg_price']:,.0f}원

🎯 익절:           {"다단계" if self.config.is_multi_level_tp_enabled() else f"{self.config.take_profit_pct}%"}
🛑 손절:           {"다단계" if self.config.is_multi_level_sl_enabled() else f"{self.config.stop_loss_pct}%"}

📉 최대 하락:      -{self.config.levels[-1].drop_pct}%
        """.strip()

        self.result_label.setText(result_text)
    
    def _on_level_count_changed(self, count: int):
        """레벨 개수 변경 시"""
        current_count = len(self.config.levels)

        if count > current_count:
            # 레벨 추가
            for i in range(current_count, count):
                # 마지막 레벨 복사하거나 기본값 생성
                if current_count > 0:
                    last_level = self.config.levels[-1]
                    # 하락률 5%씩 증가, 비중은 10%로 기본 설정
                    new_level = DcaLevelConfig(
                        level=i + 1,
                        drop_pct=last_level.drop_pct + 5.0,
                        weight_pct=10.0,
                        order_amount=self.config.calculate_amount_from_weight(10.0)
                    )
                else:
                    # 첫 레벨 생성
                    new_level = DcaLevelConfig(
                        level=1,
                        drop_pct=0.0,
                        weight_pct=20.0,
                        order_amount=self.config.calculate_amount_from_weight(20.0)
                    )
                self.config.levels.append(new_level)

        elif count < current_count:
            # 레벨 제거
            self.config.levels = self.config.levels[:count]

        # 테이블 업데이트
        self.dca_table.setRowCount(count)
        self.table_group.setTitle(f"📊 DCA 레벨 설정 ({count}단계)")

        # UI 재로드
        self._load_config_to_ui()
        self._update_simulation()

    def _on_total_capital_changed(self, value: int):
        """총 자산 변경 시 모든 금액 재계산"""
        self.config.total_capital = value

        # 시그널 블록
        self.dca_table.blockSignals(True)

        # 각 레벨의 금액을 비중 기준으로 재계산
        for i, level_config in enumerate(self.config.levels):
            # 비중을 기준으로 금액 재계산
            calculated_amount = self.config.calculate_amount_from_weight(level_config.weight_pct)
            level_config.order_amount = calculated_amount

            # 테이블 업데이트
            amount_item = self.dca_table.item(i, 3)
            amount_item.setText(f"{calculated_amount:,}")

            # 진입가/수량도 재계산
            self._update_calculated_columns(i)

        # 시그널 재활성화
        self.dca_table.blockSignals(False)

        # 시뮬레이션 업데이트
        self._update_simulation()

    def _on_enabled_changed(self, state: int):
        """DCA 활성화 체크박스 변경"""
        self.config.enabled = (state == Qt.Checked)
    
    def _apply_preset(self, preset_type: str):
        """프리셋 적용 (현재 레벨 개수에 맞춰 동적 생성)"""
        level_count = self.level_count_spin.value()

        if preset_type == "aggressive":
            # 🔥 공격형: 큰 하락률, 후반 비중 높음
            levels = self._generate_aggressive_preset(level_count)

        elif preset_type == "balanced":
            # ⚖️ 균형형: 중간 하락률, 균등 비중
            levels = self._generate_balanced_preset(level_count)

        else:  # conservative
            # 🛡️ 안정형: 작은 하락률, 초반 비중 높음
            levels = self._generate_conservative_preset(level_count)

        self.config.levels = levels
        self._load_config_to_ui()
        self._update_simulation()

        # 총 비중 합계
        total_weight = sum(level.weight_pct for level in levels)

        QMessageBox.information(
            self,
            "프리셋 적용",
            f"✅ {preset_type.upper()} 프리셋이 적용되었습니다.\n\n"
            f"레벨: {level_count}단계\n"
            f"총 비중: {total_weight:.1f}%\n"
            f"총 자산: {self.config.total_capital:,}원"
        )

    def _generate_aggressive_preset(self, count: int) -> list:
        """공격형 프리셋 생성 (후반 집중)"""
        levels = []
        total_weight = 100.0
        accumulated_weight = 0.0

        for i in range(count):
            level = i + 1
            # 하락률: 0%, 5%, 10%, 20%, 30% ...
            drop_pct = 0.0 if i == 0 else (5.0 * i if i <= 2 else 10.0 * i)

            # 비중: 후반으로 갈수록 증가 (지수 분포)
            if i == count - 1:
                # 🔧 마지막 레벨: 나머지 비중 전부 할당 (100.0% 보장)
                weight_pct = round(total_weight - accumulated_weight, 1)
            else:
                weight_ratio = (i + 1) ** 2 / sum((j + 1) ** 2 for j in range(count))
                weight_pct = round(total_weight * weight_ratio, 1)
                accumulated_weight += weight_pct

            order_amount = self.config.calculate_amount_from_weight(weight_pct)
            levels.append(DcaLevelConfig(level, drop_pct, weight_pct, order_amount))

        return levels

    def _generate_balanced_preset(self, count: int) -> list:
        """균형형 프리셋 생성 (균등 분배)"""
        levels = []
        total_weight = 100.0
        weight_per_level = round(100.0 / count, 1)
        accumulated_weight = 0.0

        for i in range(count):
            level = i + 1
            # 하락률: 0%, 5%, 10%, 15%, 20% ...
            drop_pct = 5.0 * i

            # 🔧 마지막 레벨: 나머지 비중 전부 할당 (100.0% 보장)
            if i == count - 1:
                weight_pct = round(total_weight - accumulated_weight, 1)
            else:
                weight_pct = weight_per_level
                accumulated_weight += weight_pct

            order_amount = self.config.calculate_amount_from_weight(weight_pct)
            levels.append(DcaLevelConfig(level, drop_pct, weight_pct, order_amount))

        return levels

    def _generate_conservative_preset(self, count: int) -> list:
        """안정형 프리셋 생성 (초반 집중)"""
        levels = []
        total_weight = 100.0
        accumulated_weight = 0.0

        for i in range(count):
            level = i + 1
            # 하락률: 0%, 3%, 6%, 10%, 15% ...
            drop_pct = 0.0 if i == 0 else (3.0 * i if i <= 2 else 5.0 * (i - 1))

            # 비중: 초반으로 갈수록 증가 (역지수 분포)
            if i == count - 1:
                # 🔧 마지막 레벨: 나머지 비중 전부 할당 (100.0% 보장)
                weight_pct = round(total_weight - accumulated_weight, 1)
            else:
                weight_ratio = (count - i) ** 2 / sum((count - j) ** 2 for j in range(count))
                weight_pct = round(total_weight * weight_ratio, 1)
                accumulated_weight += weight_pct

            order_amount = self.config.calculate_amount_from_weight(weight_pct)
            levels.append(DcaLevelConfig(level, drop_pct, weight_pct, order_amount))

        return levels
    
    def _reset_to_default(self):
        """기본값 복원"""
        reply = QMessageBox.question(
            self,
            "기본값 복원",
            "기본 설정으로 복원하시겠습니까?\n\n현재 설정이 사라집니다.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.config = self.config_manager.create_default_config()
            self.enabled_checkbox.setChecked(self.config.enabled)
            self._load_config_to_ui()
            self._update_simulation()
    
    def _save_config(self):
        """설정 저장"""
        # 테이블에서 최신 값 읽기 (현재 레벨 개수만큼)
        level_count = len(self.config.levels)

        for i in range(level_count):
            try:
                drop_pct = float(self.dca_table.item(i, 1).text())
                weight_pct = float(self.dca_table.item(i, 2).text())
                order_amount = int(self.dca_table.item(i, 3).text().replace(',', ''))

                self.config.levels[i].drop_pct = drop_pct
                self.config.levels[i].weight_pct = weight_pct
                self.config.levels[i].order_amount = order_amount

            except ValueError:
                QMessageBox.warning(
                    self,
                    "입력 오류",
                    f"레벨 {i+1}의 입력값을 확인해주세요."
                )
                return

        # 총 자산
        self.config.total_capital = self.total_capital_spin.value()

        # DCA 활성화
        self.config.enabled = self.enabled_checkbox.isChecked()

        # 익절/손절 테이블 저장
        self._save_tp_table()
        self._save_sl_table()

        # 🔧 검증: 총 비중 합계 경고
        total_weight = sum(level.weight_pct for level in self.config.levels)
        if total_weight > 100:
            reply = QMessageBox.warning(
                self,
                "비중 초과 경고",
                f"⚠️ 총 비중이 {total_weight:.1f}%로 100%를 초과합니다.\n\n"
                f"이는 총 자산보다 많은 금액을 투자하게 됩니다.\n\n"
                f"계속 저장하시겠습니까?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        # 저장
        if self.config_manager.save(self.config):
            QMessageBox.information(
                self,
                "저장 완료",
                "DCA 설정이 저장되었습니다.\n\n다음 트레이딩부터 적용됩니다."
            )

            # 시그널 발송
            self.config_changed.emit(self.config)

            self.accept()
        else:
            QMessageBox.warning(
                self,
                "저장 실패",
                "설정 저장에 실패했습니다."
            )
    # ===== 익절 테이블 관련 메서드 =====

    def _load_tp_table(self):
        """익절 테이블 로드"""
        self.tp_table.blockSignals(True)

        if self.config.is_multi_level_tp_enabled():
            # 다단계 익절 모드
            for i, tp_level in enumerate(self.config.take_profit_levels):
                # 레벨 (읽기 전용)
                level_item = QTableWidgetItem(f"{tp_level.level}")
                level_item.setFlags(level_item.flags() & ~Qt.ItemIsEditable)
                level_item.setTextAlignment(Qt.AlignCenter)
                self.tp_table.setItem(i, 0, level_item)

                # 수익률
                profit_item = QTableWidgetItem(f"{tp_level.profit_pct:.1f}")
                profit_item.setTextAlignment(Qt.AlignCenter)
                self.tp_table.setItem(i, 1, profit_item)

                # 매도 비율
                ratio_item = QTableWidgetItem(f"{tp_level.sell_ratio:.1f}")
                ratio_item.setTextAlignment(Qt.AlignCenter)
                self.tp_table.setItem(i, 2, ratio_item)
        else:
            # 단일 익절 모드 (하위 호환)
            level_item = QTableWidgetItem("1")
            level_item.setFlags(level_item.flags() & ~Qt.ItemIsEditable)
            level_item.setTextAlignment(Qt.AlignCenter)
            self.tp_table.setItem(0, 0, level_item)

            profit_item = QTableWidgetItem(f"{self.config.take_profit_pct:.1f}")
            profit_item.setTextAlignment(Qt.AlignCenter)
            self.tp_table.setItem(0, 1, profit_item)

            ratio_item = QTableWidgetItem("100.0")
            ratio_item.setTextAlignment(Qt.AlignCenter)
            ratio_item.setFlags(ratio_item.flags() & ~Qt.ItemIsEditable)
            self.tp_table.setItem(0, 2, ratio_item)

        self.tp_table.blockSignals(False)

    def _load_sl_table(self):
        """손절 테이블 로드"""
        self.sl_table.blockSignals(True)

        if self.config.is_multi_level_sl_enabled():
            # 다단계 손절 모드
            for i, sl_level in enumerate(self.config.stop_loss_levels):
                # 레벨 (읽기 전용)
                level_item = QTableWidgetItem(f"{sl_level.level}")
                level_item.setFlags(level_item.flags() & ~Qt.ItemIsEditable)
                level_item.setTextAlignment(Qt.AlignCenter)
                self.sl_table.setItem(i, 0, level_item)

                # 손실률
                loss_item = QTableWidgetItem(f"{sl_level.loss_pct:.1f}")
                loss_item.setTextAlignment(Qt.AlignCenter)
                self.sl_table.setItem(i, 1, loss_item)

                # 매도 비율
                ratio_item = QTableWidgetItem(f"{sl_level.sell_ratio:.1f}")
                ratio_item.setTextAlignment(Qt.AlignCenter)
                self.sl_table.setItem(i, 2, ratio_item)
        else:
            # 단일 손절 모드 (하위 호환)
            level_item = QTableWidgetItem("1")
            level_item.setFlags(level_item.flags() & ~Qt.ItemIsEditable)
            level_item.setTextAlignment(Qt.AlignCenter)
            self.sl_table.setItem(0, 0, level_item)

            loss_item = QTableWidgetItem(f"{self.config.stop_loss_pct:.1f}")
            loss_item.setTextAlignment(Qt.AlignCenter)
            self.sl_table.setItem(0, 1, loss_item)

            ratio_item = QTableWidgetItem("100.0")
            ratio_item.setTextAlignment(Qt.AlignCenter)
            ratio_item.setFlags(ratio_item.flags() & ~Qt.ItemIsEditable)
            self.sl_table.setItem(0, 2, ratio_item)

        self.sl_table.blockSignals(False)

    def _save_tp_table(self):
        """익절 테이블 저장"""
        if self.tp_table.rowCount() == 1:
            # 단일 모드
            profit_pct = float(self.tp_table.item(0, 1).text())
            self.config.take_profit_pct = profit_pct
            self.config.take_profit_levels = []  # 빈 리스트 = 단일 모드
        else:
            # 다단계 모드
            tp_levels = []
            for i in range(self.tp_table.rowCount()):
                profit_pct = float(self.tp_table.item(i, 1).text())
                sell_ratio = float(self.tp_table.item(i, 2).text())
                tp_levels.append(TakeProfitLevel(level=i+1, profit_pct=profit_pct, sell_ratio=sell_ratio))
            self.config.take_profit_levels = tp_levels

    def _save_sl_table(self):
        """손절 테이블 저장"""
        if self.sl_table.rowCount() == 1:
            # 단일 모드
            loss_pct = float(self.sl_table.item(0, 1).text())
            self.config.stop_loss_pct = loss_pct
            self.config.stop_loss_levels = []  # 빈 리스트 = 단일 모드
        else:
            # 다단계 모드
            sl_levels = []
            for i in range(self.sl_table.rowCount()):
                loss_pct = float(self.sl_table.item(i, 1).text())
                sell_ratio = float(self.sl_table.item(i, 2).text())
                sl_levels.append(StopLossLevel(level=i+1, loss_pct=loss_pct, sell_ratio=sell_ratio))
            self.config.stop_loss_levels = sl_levels

    def _on_tp_table_changed(self, row: int, col: int):
        """익절 테이블 변경 시"""
        if col not in [1, 2]:  # 수익률, 매도비율만 편집 가능
            return
        self._update_simulation()

    def _on_sl_table_changed(self, row: int, col: int):
        """손절 테이블 변경 시"""
        if col not in [1, 2]:  # 손실률, 매도비율만 편집 가능
            return
        self._update_simulation()

    def _add_tp_level(self):
        """익절 레벨 추가"""
        row_count = self.tp_table.rowCount()
        self.tp_table.setRowCount(row_count + 1)

        # 레벨 (읽기 전용)
        level_item = QTableWidgetItem(f"{row_count + 1}")
        level_item.setFlags(level_item.flags() & ~Qt.ItemIsEditable)
        level_item.setTextAlignment(Qt.AlignCenter)
        self.tp_table.setItem(row_count, 0, level_item)

        # 기본값: 수익률 +5%, 매도비율 30%
        profit_item = QTableWidgetItem("5.0")
        profit_item.setTextAlignment(Qt.AlignCenter)
        self.tp_table.setItem(row_count, 1, profit_item)

        ratio_item = QTableWidgetItem("30.0")
        ratio_item.setTextAlignment(Qt.AlignCenter)
        self.tp_table.setItem(row_count, 2, ratio_item)

    def _remove_tp_level(self):
        """익절 레벨 삭제"""
        row_count = self.tp_table.rowCount()
        if row_count > 1:
            self.tp_table.setRowCount(row_count - 1)

    def _add_sl_level(self):
        """손절 레벨 추가"""
        row_count = self.sl_table.rowCount()
        self.sl_table.setRowCount(row_count + 1)

        # 레벨 (읽기 전용)
        level_item = QTableWidgetItem(f"{row_count + 1}")
        level_item.setFlags(level_item.flags() & ~Qt.ItemIsEditable)
        level_item.setTextAlignment(Qt.AlignCenter)
        self.sl_table.setItem(row_count, 0, level_item)

        # 기본값: 손실률 -10%, 매도비율 50%
        loss_item = QTableWidgetItem("10.0")
        loss_item.setTextAlignment(Qt.AlignCenter)
        self.sl_table.setItem(row_count, 1, loss_item)

        ratio_item = QTableWidgetItem("50.0")
        ratio_item.setTextAlignment(Qt.AlignCenter)
        self.sl_table.setItem(row_count, 2, ratio_item)

    def _remove_sl_level(self):
        """손절 레벨 삭제"""
        row_count = self.sl_table.rowCount()
        if row_count > 1:
            self.sl_table.setRowCount(row_count - 1)

    def _apply_tp_preset(self):
        """익절 프리셋 적용"""
        # 3단계 익절 프리셋: 5% (30%), 10% (50%), 15% (100% 전량 청산)
        self.tp_table.setRowCount(3)
        self.tp_table.blockSignals(True)

        presets = [
            (1, 5.0, 30.0),
            (2, 10.0, 50.0),
            (3, 15.0, 100.0)  # 마지막은 전량 청산
        ]

        for i, (level, profit_pct, sell_ratio) in enumerate(presets):
            level_item = QTableWidgetItem(f"{level}")
            level_item.setFlags(level_item.flags() & ~Qt.ItemIsEditable)
            level_item.setTextAlignment(Qt.AlignCenter)
            self.tp_table.setItem(i, 0, level_item)

            profit_item = QTableWidgetItem(f"{profit_pct:.1f}")
            profit_item.setTextAlignment(Qt.AlignCenter)
            self.tp_table.setItem(i, 1, profit_item)

            ratio_item = QTableWidgetItem(f"{sell_ratio:.1f}")
            ratio_item.setTextAlignment(Qt.AlignCenter)
            self.tp_table.setItem(i, 2, ratio_item)

        self.tp_table.blockSignals(False)
        self._update_simulation()

        QMessageBox.information(self, "프리셋 적용", "✅ 익절 프리셋이 적용되었습니다.\n\n레벨1: +5% (남은 수량의 30%)\n레벨2: +10% (남은 수량의 50%)\n레벨3: +15% (남은 수량의 100%, 전량 청산)")

    def _apply_sl_preset(self):
        """손절 프리셋 적용"""
        # 2단계 손절 프리셋: -10% (50%), -20% (50%)
        self.sl_table.setRowCount(2)
        self.sl_table.blockSignals(True)

        presets = [
            (1, 10.0, 50.0),
            (2, 20.0, 100.0)  # 마지막은 전량 청산
        ]

        for i, (level, loss_pct, sell_ratio) in enumerate(presets):
            level_item = QTableWidgetItem(f"{level}")
            level_item.setFlags(level_item.flags() & ~Qt.ItemIsEditable)
            level_item.setTextAlignment(Qt.AlignCenter)
            self.sl_table.setItem(i, 0, level_item)

            loss_item = QTableWidgetItem(f"{loss_pct:.1f}")
            loss_item.setTextAlignment(Qt.AlignCenter)
            self.sl_table.setItem(i, 1, loss_item)

            ratio_item = QTableWidgetItem(f"{sell_ratio:.1f}")
            ratio_item.setTextAlignment(Qt.AlignCenter)
            self.sl_table.setItem(i, 2, ratio_item)

        self.sl_table.blockSignals(False)
        self._update_simulation()

        QMessageBox.information(self, "프리셋 적용", "✅ 손절 프리셋이 적용되었습니다.\n\n레벨1: -10% (남은 수량의 50%)\n레벨2: -20% (남은 수량의 100%, 전량 청산)")

    def _toggle_tp_single_mode(self):
        """익절 단일/다단계 모드 전환"""
        if self.tp_table.rowCount() == 1:
            # 단일 → 다단계
            reply = QMessageBox.question(
                self,
                "다단계 모드 전환",
                "다단계 익절 모드로 전환하시겠습니까?\n\n프리셋이 자동 적용됩니다.",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self._apply_tp_preset()
        else:
            # 다단계 → 단일
            reply = QMessageBox.question(
                self,
                "단일 모드 전환",
                "단일 익절 모드로 전환하시겠습니까?\n\n현재 다단계 설정이 사라집니다.",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.tp_table.setRowCount(1)
                self.tp_table.blockSignals(True)

                level_item = QTableWidgetItem("1")
                level_item.setFlags(level_item.flags() & ~Qt.ItemIsEditable)
                level_item.setTextAlignment(Qt.AlignCenter)
                self.tp_table.setItem(0, 0, level_item)

                profit_item = QTableWidgetItem("10.0")
                profit_item.setTextAlignment(Qt.AlignCenter)
                self.tp_table.setItem(0, 1, profit_item)

                ratio_item = QTableWidgetItem("100.0")
                ratio_item.setTextAlignment(Qt.AlignCenter)
                ratio_item.setFlags(ratio_item.flags() & ~Qt.ItemIsEditable)
                self.tp_table.setItem(0, 2, ratio_item)

                self.tp_table.blockSignals(False)
                self._update_simulation()

    def _toggle_sl_single_mode(self):
        """손절 단일/다단계 모드 전환"""
        if self.sl_table.rowCount() == 1:
            # 단일 → 다단계
            reply = QMessageBox.question(
                self,
                "다단계 모드 전환",
                "다단계 손절 모드로 전환하시겠습니까?\n\n프리셋이 자동 적용됩니다.",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self._apply_sl_preset()
        else:
            # 다단계 → 단일
            reply = QMessageBox.question(
                self,
                "단일 모드 전환",
                "단일 손절 모드로 전환하시겠습니까?\n\n현재 다단계 설정이 사라집니다.",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.sl_table.setRowCount(1)
                self.sl_table.blockSignals(True)

                level_item = QTableWidgetItem("1")
                level_item.setFlags(level_item.flags() & ~Qt.ItemIsEditable)
                level_item.setTextAlignment(Qt.AlignCenter)
                self.sl_table.setItem(0, 0, level_item)

                loss_item = QTableWidgetItem("25.0")
                loss_item.setTextAlignment(Qt.AlignCenter)
                self.sl_table.setItem(0, 1, loss_item)

                ratio_item = QTableWidgetItem("100.0")
                ratio_item.setTextAlignment(Qt.AlignCenter)
                ratio_item.setFlags(ratio_item.flags() & ~Qt.ItemIsEditable)
                self.sl_table.setItem(0, 2, ratio_item)

                self.sl_table.blockSignals(False)
                self._update_simulation()


# 테스트 코드
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    dialog = AdvancedDcaDialog(current_price=100000000)
    dialog.exec()

    sys.exit(app.exec())
