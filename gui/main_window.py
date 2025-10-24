"""
Main Window - 메인 화면
Upbit DCA Trader GUI 메인 윈도우
"""

import sys
import os

# 🔧 프로젝트 루트를 Python 경로에 추가 (gui 폴더에서도 실행 가능)
if __name__ == "__main__":
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QGroupBox,
    QMenuBar, QMenu, QMessageBox, QStatusBar,
    QSpinBox, QDoubleSpinBox, QFormLayout,
    QTableWidget, QTableWidgetItem, QHeaderView,  # 포지션 테이블용
    QScrollArea, QSizePolicy, QSplitter, QTabWidget,  # Step 2: 사이드바 레이아웃 + 탭
    QRadioButton, QButtonGroup  # 트레이딩 모드 선택용
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QAction, QFont
from gui.settings_dialog import SettingsDialog
from gui.config_manager import ConfigManager
from gui.trading_worker import TradingEngineWorker
from gui.multi_coin_worker import MultiCoinTradingWorker  # 🔧 다중 코인 워커 추가
from gui.auto_trading_worker import AutoTradingWorker  # 🔧 완전 자동 워커 추가
from gui.semi_auto_worker import SemiAutoWorker  # 🔧 반자동 워커 추가 (수동매수 + 자동관리)
from gui.dca_simulator import DcaSimulatorDialog
from gui.advanced_dca_dialog import AdvancedDcaDialog
from gui.dca_config import DcaConfigManager
from gui.coin_selection_dialog import CoinSelectionDialog  # 🔧 코인 선택 다이얼로그
from gui.auto_trading_config import AutoTradingConfig  # 🔧 완전 자동 모드 설정


class BalanceWorker(QThread):
    """
    잔고 조회 워커 스레드

    GUI 프리징을 방지하기 위한 백그라운드 작업 스레드
    """

    # 시그널 정의
    finished = Signal(dict)  # 성공 시: {'success': True, 'krw': float, 'btc': float}
    error = Signal(str)      # 실패 시: 에러 메시지

    def __init__(self, access_key: str, secret_key: str):
        super().__init__()
        self.access_key = access_key
        self.secret_key = secret_key

    def run(self):
        """백그라운드에서 API 호출 실행"""
        try:
            from core.upbit_api import UpbitAPI

            api = UpbitAPI(self.access_key, self.secret_key)
            accounts = api.get_accounts()

            # KRW 잔고 찾기
            krw_balance = 0
            for account in accounts:
                if account['currency'] == 'KRW':
                    krw_balance = float(account['balance'])
                    break

            # BTC 잔고 찾기
            btc_balance = 0
            for account in accounts:
                if account['currency'] == 'BTC':
                    btc_balance = float(account['balance'])
                    break

            # 성공 시그널 발생
            self.finished.emit({
                'success': True,
                'krw': krw_balance,
                'btc': btc_balance
            })

        except Exception as e:
            # 실패 시그널 발생
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    """
    메인 윈도우

    트레이딩 봇 실행/중지, 상태 모니터링
    """

    def __init__(self):
        super().__init__()

        self.config_manager = ConfigManager()
        self.dca_config_manager = DcaConfigManager()  # 고급 DCA 설정 관리자
        self.dca_config = self.dca_config_manager.load()  # DCA 설정 로드
        
        # 🔧 트레이딩 모드 및 완전 자동 설정
        self.trading_mode = "semi_auto"  # "semi_auto" | "full_auto"
        self.auto_trading_config = AutoTradingConfig.from_file('auto_trading_config.json')  # 완전 자동 설정
        self.scan_interval = 10  # 반자동 모드 포지션 스캔 주기 (초)
        
        self.is_running = False
        self.balance_worker = None  # 잔고 조회 워커 스레드
        self.trading_worker = None  # Trading Engine 워커 스레드
        self._shutdown_timer = None  # 비동기 종료 타이머
        self._shutdown_elapsed = 0  # 종료 대기 시간
        
        # 🔧 거래 내역 저장
        self.trade_history = []  # Trade 객체 리스트

        # 리스크 관리 파라미터 (고급 DCA 설정에서 관리)
        # 🔧 모든 DCA 관련 설정은 self.dca_config에서 가져옴
        self.stop_loss_pct = self.dca_config.stop_loss_pct
        self.take_profit_pct = self.dca_config.take_profit_pct
        self.max_daily_loss_pct = 10.0  # 일일 최대 손실은 별도 관리

        self.setWindowTitle("Upbit DCA Trader")
        self.setMinimumSize(1200, 750)  # Step 2: 사이드바 레이아웃으로 증가

        self._init_ui()
        self._init_menu()
        self._init_statusbar()
        self._update_status()

        # 🔧 GUI 시작 시 자동으로 잔고 조회 (500ms 후)
        QTimer.singleShot(500, self._refresh_balance)

        # 🔧 주기적 잔고 갱신 (60초마다 fallback)
        self.balance_refresh_timer = QTimer(self)
        self.balance_refresh_timer.timeout.connect(self._refresh_balance)
        self.balance_refresh_timer.start(60000)  # 60초

    def _init_ui(self):
        """UI 초기화 - Step 2: 좌측 사이드바 + 우측 메인 패널"""
        # 중앙 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 🔧 메인 레이아웃: 좌우 분할 (QSplitter 사용)
        main_splitter = QSplitter(Qt.Horizontal)
        main_layout = QHBoxLayout(central_widget)
        main_layout.addWidget(main_splitter)

        # ========================================
        # 좌측 사이드바 (설정 영역) - 3.png 기준으로 좁게 조정
        # ========================================
        sidebar_widget = QWidget()
        sidebar_widget.setMaximumWidth(200)  # 더 좁게 (3.png 참고)
        sidebar_widget.setMinimumWidth(180)
        sidebar_layout = QVBoxLayout(sidebar_widget)
        sidebar_layout.setContentsMargins(3, 5, 3, 5)
        sidebar_layout.setSpacing(8)

        # 사이드바를 스크롤 가능하게 (설정이 많을 경우 대비)
        sidebar_scroll = QScrollArea()
        sidebar_scroll.setWidget(sidebar_widget)
        sidebar_scroll.setWidgetResizable(True)
        sidebar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # 🔧 0. 트레이딩 모드 선택 (사이드바 최상단)
        mode_group = QGroupBox("🎯 트레이딩 모드")
        mode_layout = QVBoxLayout()
        mode_layout.setSpacing(5)
        
        # 모드 선택 라디오 버튼
        self.semi_auto_radio = QRadioButton("반자동 (Upbit 앱 수동매수 → 봇 자동관리)")
        self.full_auto_radio = QRadioButton("완전 자동 (봇 자동매수 + 자동관리)")
        
        # 버튼 그룹 생성
        self.mode_button_group = QButtonGroup()
        self.mode_button_group.addButton(self.semi_auto_radio, 0)
        self.mode_button_group.addButton(self.full_auto_radio, 1)
        
        # 기본값: 반자동
        self.semi_auto_radio.setChecked(True)
        
        # 폰트 설정
        self.semi_auto_radio.setFont(QFont("맑은 고딕", 9))
        self.full_auto_radio.setFont(QFont("맑은 고딕", 9))
        
        # 시그널 연결
        self.semi_auto_radio.toggled.connect(self._on_mode_changed)
        
        mode_layout.addWidget(self.semi_auto_radio)
        mode_layout.addWidget(self.full_auto_radio)
        
        # 모드 설명 추가
        mode_info = QLabel(
            "💡 반자동: Upbit 앱 수동매수 → 봇 감지 → DCA/익절/손절 자동실행\n"
            "💡 완전 자동: 봇이 상위코인 모니터링 → 시그널 감지 → 자동매수 → 자동관리"
        )
        mode_info.setFont(QFont("맑은 고딕", 8))
        mode_info.setStyleSheet("color: #666; padding: 3px;")
        mode_info.setWordWrap(True)
        mode_layout.addWidget(mode_info)
        
        mode_group.setLayout(mode_layout)
        sidebar_layout.addWidget(mode_group)

        # 🔧 1. 상태 패널 (사이드바 상단)
        status_group = QGroupBox("📊 상태")
        status_layout = QVBoxLayout()

        self.status_label = QLabel("● 중지됨")
        self.status_label.setFont(QFont("맑은 고딕", 11, QFont.Bold))
        status_layout.addWidget(self.status_label)

        # 선택된 코인 개수로 초기화
        selected_coin_count = len(self.config_manager.get_selected_coins())
        self.symbol_label = QLabel(f"다중 코인 ({selected_coin_count}개)")
        self.symbol_label.setFont(QFont("맑은 고딕", 9))
        status_layout.addWidget(self.symbol_label)

        status_group.setLayout(status_layout)
        sidebar_layout.addWidget(status_group)

        # 🔧 2. 계좌 정보 패널 (사이드바)
        account_group = QGroupBox("💰 계좌 정보")
        account_layout = QVBoxLayout()

        self.total_asset_label = QLabel("총 자산: 로딩 중...")
        self.total_asset_label.setFont(QFont("맑은 고딕", 9))
        account_layout.addWidget(self.total_asset_label)

        self.profit_label = QLabel("수익률: 0.00%")
        self.profit_label.setStyleSheet("color: gray;")
        self.profit_label.setFont(QFont("맑은 고딕", 9))
        account_layout.addWidget(self.profit_label)

        self.mdd_label = QLabel("최대 낙폭: 0.00%")
        self.mdd_label.setStyleSheet("color: gray;")
        self.mdd_label.setFont(QFont("맑은 고딕", 9))
        account_layout.addWidget(self.mdd_label)

        self.refresh_btn = QPushButton("🔄 새로고침")
        self.refresh_btn.clicked.connect(self._refresh_balance)
        account_layout.addWidget(self.refresh_btn)

        account_group.setLayout(account_layout)
        sidebar_layout.addWidget(account_group)

        # 🔧 3. DCA 전략 설정 (사이드바 - 읽기 전용 요약)
        settings_group = QGroupBox("📊 DCA 전략")
        settings_layout = QVBoxLayout()

        # DCA 설정 요약 정보
        summary_layout = QFormLayout()

        # 익절 목표 (읽기 전용)
        if self.dca_config.is_multi_level_tp_enabled():
            tp_count = len(self.dca_config.take_profit_levels)
            tp_text = f"다단계 ({tp_count}레벨)"
        else:
            tp_text = f"+{self.dca_config.take_profit_pct}%"

        self.take_profit_label = QLabel(tp_text)
        self.take_profit_label.setFont(QFont("Consolas", 9, QFont.Bold))
        self.take_profit_label.setStyleSheet("color: #4CAF50;")
        summary_layout.addRow("🎯 익절:", self.take_profit_label)

        # 손절 방어 (읽기 전용)
        if self.dca_config.is_multi_level_sl_enabled():
            sl_count = len(self.dca_config.stop_loss_levels)
            sl_text = f"다단계 ({sl_count}레벨)"
        else:
            sl_text = f"-{self.dca_config.stop_loss_pct}%"

        self.stop_loss_label = QLabel(sl_text)
        self.stop_loss_label.setFont(QFont("Consolas", 9, QFont.Bold))
        self.stop_loss_label.setStyleSheet("color: #F44336;")
        summary_layout.addRow("🛑 손절:", self.stop_loss_label)

        # DCA 레벨 정보 (읽기 전용)
        min_drop = min(level.drop_pct for level in self.dca_config.levels)
        max_drop = max(level.drop_pct for level in self.dca_config.levels)
        self.dca_levels_label = QLabel(f"{len(self.dca_config.levels)}단계 ({min_drop}%~{max_drop}%)")
        self.dca_levels_label.setFont(QFont("Consolas", 9))
        summary_layout.addRow("📊 레벨:", self.dca_levels_label)

        # 총 투자금 (읽기 전용)
        total_investment = sum(level.order_amount for level in self.dca_config.levels)
        self.total_investment_label = QLabel(f"{total_investment:,}원")
        self.total_investment_label.setFont(QFont("Consolas", 9, QFont.Bold))
        self.total_investment_label.setStyleSheet("color: #2196F3;")
        summary_layout.addRow("💰 투자금:", self.total_investment_label)

        # DCA 활성화 상태 (읽기 전용)
        self.dca_status_label = QLabel("✅ 활성화" if self.dca_config.enabled else "❌ 비활성화")
        self.dca_status_label.setFont(QFont("Consolas", 9, QFont.Bold))
        self.dca_status_label.setStyleSheet("color: #4CAF50;" if self.dca_config.enabled else "color: #999;")
        summary_layout.addRow("⚙️ 상태:", self.dca_status_label)

        settings_layout.addLayout(summary_layout)
        settings_group.setLayout(settings_layout)
        sidebar_layout.addWidget(settings_group)

        # 🔧 3.5. 완전 자동 모드 설정 (사이드바 - 완전 자동 선택 시만 표시)
        self.auto_settings_group = QGroupBox("🤖 완전 자동 설정")
        auto_settings_layout = QVBoxLayout()
        
        # 완전 자동 설정 요약
        auto_summary_layout = QFormLayout()
        
        # 매수 금액
        self.auto_buy_amount_label = QLabel(f"{self.auto_trading_config.buy_amount:,.0f}원")
        self.auto_buy_amount_label.setFont(QFont("Consolas", 9, QFont.Bold))
        self.auto_buy_amount_label.setStyleSheet("color: #2196F3;")
        auto_summary_layout.addRow("💰 매수금액:", self.auto_buy_amount_label)
        
        # 모니터링 코인
        monitoring_text = f"상위 {self.auto_trading_config.top_n}개" if self.auto_trading_config.monitoring_mode == "top_marketcap" else f"{len(self.auto_trading_config.custom_symbols)}개"
        self.auto_monitoring_label = QLabel(monitoring_text)
        self.auto_monitoring_label.setFont(QFont("Consolas", 9))
        auto_summary_layout.addRow("📊 모니터링:", self.auto_monitoring_label)
        
        # 스캔 주기
        self.auto_scan_label = QLabel(f"{self.auto_trading_config.scan_interval}초")
        self.auto_scan_label.setFont(QFont("Consolas", 9))
        auto_summary_layout.addRow("⏱️ 스캔주기:", self.auto_scan_label)
        
        # 리스크 관리 요약
        risk_items = []
        if self.auto_trading_config.max_positions_enabled:
            risk_items.append(f"포지션 {self.auto_trading_config.max_positions_limit}개")
        if self.auto_trading_config.daily_trades_enabled:
            risk_items.append(f"거래 {self.auto_trading_config.daily_trades_limit}회/일")
        if self.auto_trading_config.min_krw_balance_enabled:
            risk_items.append(f"잔고 {self.auto_trading_config.min_krw_balance_amount:,.0f}원")
        if self.auto_trading_config.stop_on_loss_enabled:
            risk_items.append(f"손실 {self.auto_trading_config.stop_on_loss_daily_pct}%")
        
        risk_text = ", ".join(risk_items) if risk_items else "없음"
        self.auto_risk_label = QLabel(risk_text)
        self.auto_risk_label.setFont(QFont("맑은 고딕", 8))
        self.auto_risk_label.setWordWrap(True)
        self.auto_risk_label.setStyleSheet("color: #F44336;")
        auto_summary_layout.addRow("🛡️ 리스크:", self.auto_risk_label)
        
        auto_settings_layout.addLayout(auto_summary_layout)
        
        # 설정 변경 버튼
        auto_config_btn = QPushButton("⚙️ 설정 변경")
        auto_config_btn.setStyleSheet("background-color: #673AB7; color: white; padding: 5px; font-weight: bold;")
        auto_config_btn.clicked.connect(self._open_auto_trading_config)
        auto_settings_layout.addWidget(auto_config_btn)
        
        self.auto_settings_group.setLayout(auto_settings_layout)
        sidebar_layout.addWidget(self.auto_settings_group)
        
        # 초기에는 숨김 (반자동 모드가 기본)
        self.auto_settings_group.setVisible(False)

        # 🔧 4. 실행 버튼들 (사이드바 하단)
        button_group = QGroupBox("⚙️ 제어")
        button_layout = QVBoxLayout()

        # 코인 선택 버튼 (반자동 모드에서만 표시)
        self.coin_selection_btn = QPushButton("🎯 코인 선택")
        self.coin_selection_btn.setStyleSheet("background-color: #FF9800; color: white; padding: 8px; font-weight: bold;")
        self.coin_selection_btn.clicked.connect(self._open_coin_selection)
        button_layout.addWidget(self.coin_selection_btn)

        # DCA 설정 변경 버튼
        advanced_dca_btn = QPushButton("⚙️ DCA 설정 변경")
        advanced_dca_btn.setStyleSheet("background-color: #9C27B0; color: white; padding: 8px; font-weight: bold;")
        advanced_dca_btn.clicked.connect(self._open_advanced_dca)
        button_layout.addWidget(advanced_dca_btn)

        # 시작 버튼
        self.start_btn = QPushButton("▶ 전체 DCA 시작")
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px; font-size: 13px; font-weight: bold;")
        self.start_btn.clicked.connect(self._start_trading)
        button_layout.addWidget(self.start_btn)

        # 중지 버튼
        self.stop_btn = QPushButton("■ 전체 DCA 중지")
        self.stop_btn.setStyleSheet("background-color: #f44336; color: white; padding: 10px; font-size: 13px; font-weight: bold;")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_trading)
        button_layout.addWidget(self.stop_btn)

        button_group.setLayout(button_layout)
        sidebar_layout.addWidget(button_group)

        # 사이드바 하단 여백 추가
        sidebar_layout.addStretch()

        # 사이드바를 스플리터에 추가
        main_splitter.addWidget(sidebar_scroll)

        # ========================================
        # 우측 메인 패널 (모니터링 영역)
        # ========================================
        main_panel_widget = QWidget()
        main_panel_layout = QVBoxLayout(main_panel_widget)
        main_panel_layout.setContentsMargins(5, 5, 5, 5)
        main_panel_layout.setSpacing(10)

        # 🔧 상단: 포지션 현황 (간결)
        top_layout = QHBoxLayout()

        self.price_label = QLabel("포지션: 없음")
        self.price_label.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        self.price_label.setStyleSheet("padding: 8px; background-color: #f5f5f5; border-radius: 3px;")
        top_layout.addWidget(self.price_label)

        main_panel_layout.addLayout(top_layout)

        # 🔧 중단: 탭 위젯 (활성 포지션 + 거래 내역)
        tab_widget = QTabWidget()
        
        # === 탭 1: 활성 포지션 ===
        position_widget = QWidget()
        position_layout = QVBoxLayout(position_widget)
        position_layout.setContentsMargins(5, 5, 5, 5)

        # 🔧 포지션 요약 정보 (상단)
        self.position_summary_label = QLabel("총 0개 보유 중 | 전체 평가손익: 0원 (0.00%)")
        self.position_summary_label.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        self.position_summary_label.setStyleSheet("color: #666; padding: 5px; background-color: #f5f5f5; border-radius: 3px;")
        position_layout.addWidget(self.position_summary_label)

        # 포지션 테이블 생성
        self.position_table = QTableWidget()
        self.position_table.setColumnCount(7)  # 🔧 진입시각 컬럼 제거 (8 → 7)
        self.position_table.setHorizontalHeaderLabels([
            "심볼", "상태", "진입가", "현재가", "수량", "평가손익", "손익률(%)"  # 🔧 "진입시각" 제거
        ])

        # 테이블 스타일 설정
        self.position_table.setFont(QFont("Consolas", 10))
        self.position_table.setAlternatingRowColors(True)
        self.position_table.setEditTriggers(QTableWidget.NoEditTriggers)  # 읽기 전용
        self.position_table.setSelectionBehavior(QTableWidget.SelectRows)  # 행 단위 선택

        # 컬럼 너비 자동 조정
        header = self.position_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)

        # 🔧 테이블 정렬 활성화 (컬럼 헤더 클릭 시 정렬)
        self.position_table.setSortingEnabled(True)

        position_layout.addWidget(self.position_table)
        
        # === 탭 2: 거래 내역 ===
        trade_history_widget = QWidget()
        trade_history_layout = QVBoxLayout(trade_history_widget)
        trade_history_layout.setContentsMargins(5, 5, 5, 5)
        
        # 거래 내역 요약 정보
        self.trade_summary_label = QLabel("총 0건 | 매수: 0건, 매도: 0건 | 누적 손익: 0원 (0.00%)")
        self.trade_summary_label.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        self.trade_summary_label.setStyleSheet("color: #666; padding: 5px; background-color: #f5f5f5; border-radius: 3px;")
        trade_history_layout.addWidget(self.trade_summary_label)
        
        # 거래 내역 테이블 생성
        self.trade_history_table = QTableWidget()
        self.trade_history_table.setColumnCount(8)
        self.trade_history_table.setHorizontalHeaderLabels([
            "시각", "심볼", "유형", "가격", "수량", "금액", "손익", "사유"
        ])
        
        # 테이블 스타일 설정
        self.trade_history_table.setFont(QFont("Consolas", 9))
        self.trade_history_table.setAlternatingRowColors(True)
        self.trade_history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.trade_history_table.setSelectionBehavior(QTableWidget.SelectRows)
        
        # 컬럼 너비 설정
        trade_header = self.trade_history_table.horizontalHeader()
        trade_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 시각
        trade_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # 심볼
        trade_header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 유형
        trade_header.setSectionResizeMode(3, QHeaderView.Stretch)  # 가격
        trade_header.setSectionResizeMode(4, QHeaderView.Stretch)  # 수량
        trade_header.setSectionResizeMode(5, QHeaderView.Stretch)  # 금액
        trade_header.setSectionResizeMode(6, QHeaderView.Stretch)  # 손익
        trade_header.setSectionResizeMode(7, QHeaderView.Stretch)  # 사유
        
        # 정렬 활성화
        self.trade_history_table.setSortingEnabled(True)
        
        trade_history_layout.addWidget(self.trade_history_table)
        
        # 탭에 위젯 추가
        tab_widget.addTab(position_widget, "📊 활성 포지션")
        tab_widget.addTab(trade_history_widget, "📋 거래 내역")
        
        # 탭 위젯을 메인 패널에 추가
        main_panel_layout.addWidget(tab_widget, stretch=1)

        # 🔧 하단: 실시간 로그 (높이 축소 - 200px)
        log_group = QGroupBox("📈 실시간 로그")
        log_layout = QVBoxLayout()

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setMaximumHeight(280)  # 3.png 참고하여 증가 (200 → 280)
        log_layout.addWidget(self.log_text)

        # 로그 클리어 버튼
        log_button_layout = QHBoxLayout()

        clear_log_btn = QPushButton("🗑️ 로그 지우기")
        clear_log_btn.clicked.connect(self.log_text.clear)
        log_button_layout.addWidget(clear_log_btn)

        # DCA 시뮬레이터 버튼 (로그 영역 하단)
        simulator_btn = QPushButton("💰 DCA 시뮬레이터")
        simulator_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 5px;")
        simulator_btn.setToolTip("DCA 전략을 미리 시뮬레이션해보기")
        simulator_btn.clicked.connect(self._open_dca_simulator)
        log_button_layout.addWidget(simulator_btn)

        log_layout.addLayout(log_button_layout)

        log_group.setLayout(log_layout)
        main_panel_layout.addWidget(log_group)

        # 메인 패널을 스플리터에 추가
        main_splitter.addWidget(main_panel_widget)

        # 스플리터 비율 설정 (좌측 350px : 우측 나머지)
        main_splitter.setStretchFactor(0, 0)  # 사이드바 고정
        main_splitter.setStretchFactor(1, 1)  # 메인 패널 확장

        # 초기 로그 메시지
        self._add_log("🚀 Upbit DCA Trader GUI 시작")
        self._add_log("📌 좌측 사이드바에서 설정을 확인하세요")
        self._add_log("ℹ️ 설정 메뉴(상단)에서 API 키와 Telegram을 설정하세요")

    def _init_menu(self):
        """메뉴 초기화"""
        menubar = self.menuBar()

        # 파일 메뉴
        file_menu = menubar.addMenu("파일")

        exit_action = QAction("종료", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 설정 메뉴
        settings_menu = menubar.addMenu("설정")

        config_action = QAction("⚙️ 환경 설정", self)
        config_action.triggered.connect(self._open_settings)
        settings_menu.addAction(config_action)

        # 도움말 메뉴
        help_menu = menubar.addMenu("도움말")

        about_action = QAction("ℹ️ 정보", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _init_statusbar(self):
        """상태바 초기화"""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("준비")

    # ========================================
    # 트레이딩 모드 관리
    # ========================================
    
    def _on_mode_changed(self, checked: bool):
        """트레이딩 모드 변경 핸들러"""
        if not checked:
            return
        
        # 실행 중이면 모드 변경 불가
        if self.is_running:
            QMessageBox.warning(
                self,
                "모드 변경 불가",
                "트레이딩이 실행 중입니다.\n먼저 중지한 후 모드를 변경하세요."
            )
            # 라디오 버튼 원래대로 되돌리기
            if self.trading_mode == "semi_auto":
                self.semi_auto_radio.setChecked(True)
            else:
                self.full_auto_radio.setChecked(True)
            return
        
        # 모드 변경
        if self.semi_auto_radio.isChecked():
            self.trading_mode = "semi_auto"
            self.auto_settings_group.setVisible(False)
            self.coin_selection_btn.setVisible(True)  # 🔧 코인 선택 버튼 표시
            self._add_log("🔄 반자동 모드로 변경")
            self._add_log("💡 Upbit에서 직접 매수하면 자동으로 DCA 관리됩니다")
        else:
            self.trading_mode = "full_auto"
            self.auto_settings_group.setVisible(True)
            self.coin_selection_btn.setVisible(False)  # 🔧 코인 선택 버튼 숨김
            self._add_log("🔄 완전 자동 모드로 변경")
            self._add_log(f"💡 시가총액 상위 {self.auto_trading_config.top_n}개 코인을 자동 모니터링합니다")
        
        # 상태 업데이트
        self._update_status()
    
    def _open_auto_trading_config(self):
        """완전 자동 모드 설정 다이얼로그 열기"""
        from gui.auto_trading_config_dialog import AutoTradingConfigDialog
        
        dialog = AutoTradingConfigDialog(self.auto_trading_config, self)
        if dialog.exec():
            # 설정이 변경되면 업데이트
            self.auto_trading_config = dialog.get_config()
            self.auto_trading_config.to_file('auto_trading_config.json')
            self._update_auto_config_display()
            self._add_log("✅ 완전 자동 설정이 업데이트되었습니다")
    
    def _update_auto_config_display(self):
        """완전 자동 설정 표시 업데이트"""
        # 매수 금액
        self.auto_buy_amount_label.setText(f"{self.auto_trading_config.buy_amount:,.0f}원")
        
        # 모니터링 코인
        monitoring_text = f"상위 {self.auto_trading_config.top_n}개" if self.auto_trading_config.monitoring_mode == "top_marketcap" else f"{len(self.auto_trading_config.custom_symbols)}개"
        self.auto_monitoring_label.setText(monitoring_text)
        
        # 스캔 주기
        self.auto_scan_label.setText(f"{self.auto_trading_config.scan_interval}초")
        
        # 리스크 관리 요약
        risk_items = []
        if self.auto_trading_config.max_positions_enabled:
            risk_items.append(f"포지션 {self.auto_trading_config.max_positions_limit}개")
        if self.auto_trading_config.daily_trades_enabled:
            risk_items.append(f"거래 {self.auto_trading_config.daily_trades_limit}회/일")
        if self.auto_trading_config.min_krw_balance_enabled:
            risk_items.append(f"잔고 {self.auto_trading_config.min_krw_balance_amount:,.0f}원")
        if self.auto_trading_config.stop_on_loss_enabled:
            risk_items.append(f"손실 {self.auto_trading_config.stop_on_loss_daily_pct}%")
        
        risk_text = ", ".join(risk_items) if risk_items else "없음"
        self.auto_risk_label.setText(risk_text)

    # ========================================
    # 리스크 관리 설정 핸들러
    # ========================================

    def _on_stop_loss_changed(self, value: float):
        """손절 % 변경"""
        self.stop_loss_pct = value
        self._add_log(f"⚙️ 손절: {value}%")

    def _on_take_profit_changed(self, value: float):
        """익절 % 변경"""
        self.take_profit_pct = value
        self._add_log(f"⚙️ 익절: {value}%")

    def _on_daily_loss_changed(self, value: float):
        """일일 최대 손실 % 변경"""
        self.max_daily_loss_pct = value
        self._add_log(f"⚙️ 일일 최대 손실: {value}%")

    def _on_order_amount_changed(self, value: int):
        """주문 금액 변경 - Deprecated: Use Advanced DCA Dialog"""
        # 🔧 이 메서드는 더 이상 사용되지 않음
        pass

    def _apply_settings(self):
        """설정 적용 - Deprecated: Use Advanced DCA Dialog"""
        # 🔧 이 메서드는 더 이상 사용되지 않음
        # 고급 DCA 설정 다이얼로그에서만 설정 변경 가능
        QMessageBox.information(
            self,
            "설정 변경",
            "DCA 설정을 변경하려면 '⚙️ DCA 전략 설정 변경' 버튼을 사용하세요."
        )

    def _reset_settings(self):
        """설정 초기화 (기본값으로) - Deprecated: Use Advanced DCA Dialog"""
        # 🔧 이 메서드는 더 이상 사용되지 않음
        # 고급 DCA 설정 다이얼로그에서만 설정 변경 가능
        QMessageBox.information(
            self,
            "설정 변경",
            "DCA 설정을 변경하려면 '⚙️ DCA 전략 설정 변경' 버튼을 사용하세요."
        )

    def _open_coin_selection(self):
        """코인 선택 다이얼로그 열기"""
        # 현재 선택된 코인 리스트 가져오기
        selected_coins = self.config_manager.get_selected_coins()

        # 코인 선택 다이얼로그 열기
        dialog = CoinSelectionDialog(self, selected_coins=selected_coins)

        # 코인 선택 변경 시그널 연결
        dialog.coins_changed.connect(self._on_coins_changed)

        # 다이얼로그 실행
        dialog.exec()

    def _on_coins_changed(self, coins):
        """코인 선택 변경 시그널 핸들러"""
        # ConfigManager에 저장
        if self.config_manager.set_selected_coins(coins):
            coins_str = ", ".join([coin.replace('KRW-', '') for coin in coins])
            self._add_log(f"🎯 거래 코인 선택: {coins_str} ({len(coins)}개)")

            # 🔧 사이드바 심볼 라벨 업데이트
            self.symbol_label.setText(f"다중 코인 ({len(coins)}개)")

            # 🔧 포지션 테이블 초기화 (매수 완료 시에만 행 추가)
            self.position_table.setRowCount(0)
            
            # 🔧 실행 중인 엔진에 코인 선택 실시간 반영
            if self.is_running and self.trading_worker:
                self._add_log("🔄 실행 중인 엔진에 코인 선택 업데이트 전송...")
                self.trading_worker.update_coins(coins)

        else:
            self._add_log("❌ 코인 선택 저장 실패")

    def _open_dca_simulator(self):
        """DCA 시뮬레이터 열기"""
        # 현재 DOGE 가격 가져오기 (가능하면)
        try:
            import pyupbit
            current_price = pyupbit.get_current_price("KRW-DOGE")
            if not current_price:
                current_price = 200  # 기본값: 200원 (DOGE 평균가)
        except:
            current_price = 200  # 기본값: 200원

        # DCA Simulator 다이얼로그 열기 (첫 번째 레벨 금액 사용)
        first_level_amount = self.dca_config.levels[0].order_amount if self.dca_config.levels else 10000

        dialog = DcaSimulatorDialog(
            self,
            initial_price=int(current_price),
            order_amount=first_level_amount
        )

        dialog.exec()
        self._add_log("💰 DCA 시뮬레이터 사용 완료")
    
    def _open_advanced_dca(self):
        """고급 DCA 설정 다이얼로그 열기"""
        # 현재 DOGE 가격 가져오기
        try:
            import pyupbit
            current_price = pyupbit.get_current_price("KRW-DOGE")
            if not current_price:
                current_price = 200  # 기본값: 200원 (DOGE 평균가)
        except:
            current_price = 200  # 기본값: 200원
        
        # 고급 DCA 설정 다이얼로그 열기
        dialog = AdvancedDcaDialog(self, current_price=int(current_price))
        
        # 🔧 설정 변경 시그널 연결 (저장 버튼 누를 때마다 즉시 반영)
        dialog.config_changed.connect(self._on_dca_config_changed)
        
        # 다이얼로그 실행
        dialog.exec()
    
    def _on_dca_config_changed(self, config):
        """DCA 설정 변경 시그널 핸들러 (저장 시 자동 호출)"""
        self._add_log("⚙️ 고급 DCA 설정이 저장되었습니다")
        
        # DCA 설정 업데이트
        self.dca_config = config
        self.stop_loss_pct = config.stop_loss_pct
        self.take_profit_pct = config.take_profit_pct
        
        # 🔧 메인 화면의 읽기 전용 라벨들 자동 업데이트
        # 익절 라벨 (다단계/단일 구분)
        if config.is_multi_level_tp_enabled():
            tp_count = len(config.take_profit_levels)
            self.take_profit_label.setText(f"다단계 ({tp_count}레벨)")
        else:
            self.take_profit_label.setText(f"+{config.take_profit_pct}%")
        
        # 손절 라벨 (다단계/단일 구분)
        if config.is_multi_level_sl_enabled():
            sl_count = len(config.stop_loss_levels)
            self.stop_loss_label.setText(f"다단계 ({sl_count}레벨)")
        else:
            self.stop_loss_label.setText(f"-{config.stop_loss_pct}%")
        
        # DCA 레벨 정보 업데이트
        min_drop = min(level.drop_pct for level in config.levels)
        max_drop = max(level.drop_pct for level in config.levels)
        self.dca_levels_label.setText(f"{len(config.levels)}단계 ({min_drop}%~{max_drop}%)")
        
        # 총 투자금 업데이트
        total_investment = sum(level.order_amount for level in config.levels)
        self.total_investment_label.setText(f"{total_investment:,}원")
        
        # DCA 상태 업데이트
        self.dca_status_label.setText("✅ 활성화" if config.enabled else "❌ 비활성화")
        self.dca_status_label.setStyleSheet("color: #4CAF50;" if config.enabled else "color: #999;")
        
        # 로그 출력
        self._add_log(f"  📊 DCA 레벨: {len(config.levels)}단계")
        
        # 익절 표시 (다단계/단일 구분)
        if config.is_multi_level_tp_enabled():
            tp_count = len(config.take_profit_levels)
            self._add_log(f"  🎯 익절: 다단계 ({tp_count}레벨)")
        else:
            self._add_log(f"  🎯 익절: +{config.take_profit_pct}%")
        
        # 손절 표시 (다단계/단일 구분)
        if config.is_multi_level_sl_enabled():
            sl_count = len(config.stop_loss_levels)
            self._add_log(f"  🛑 손절: 다단계 ({sl_count}레벨)")
        else:
            self._add_log(f"  🛑 손절: -{config.stop_loss_pct}%")
        
        self._add_log(f"  💰 총 투자금: {total_investment:,}원")
        
        # 레벨 정보 출력 (처음 3개)
        for level_config in config.levels[:3]:
            self._add_log(f"     레벨 {level_config.level}: {level_config.drop_pct}% 하락 → {level_config.order_amount:,}원")
        if len(config.levels) > 3:
            self._add_log(f"     ... 외 {len(config.levels) - 3}개 레벨")
        
        # 🔧 실행 중인 엔진에 DCA 설정 실시간 반영
        if self.is_running and self.trading_worker:
            self._add_log("🔄 실행 중인 엔진에 DCA 설정 업데이트 전송...")
            self.trading_worker.update_dca_config(config)

    # ========================================
    # 설정 및 다이얼로그
    # ========================================

    def _open_settings(self):
        """설정 다이얼로그 열기"""
        dialog = SettingsDialog(self)
        dialog.settings_changed.connect(self._on_settings_changed)

        if dialog.exec():
            self._add_log("✅ 설정이 저장되었습니다")

    def _on_settings_changed(self):
        """설정 변경 시"""
        self.config_manager.reload()
        self._add_log("📝 설정이 다시 로드되었습니다")
        self._update_status()

    def _show_about(self):
        """정보 다이얼로그"""
        QMessageBox.about(
            self,
            "Upbit DCA Trader",
            "<h2>Upbit DCA Trader</h2>"
            "<p>비트코인 자동 매매 트레이딩 봇</p>"
            "<p><b>버전:</b> 1.0.0 (Phase 3.7)</p>"
            "<p><b>전략:</b> 볼린저 밴드 (20, 2.5)</p>"
            "<p><b>리스크 관리:</b> 손절 -5%, 익절 +10%</p>"
            "<hr>"
            "<p><b>개발:</b> Claude Code AI Assistant</p>"
            "<p><b>라이선스:</b> MIT</p>"
        )

    # ========================================
    # 트레이딩 제어
    # ========================================

    def _start_trading(self):
        """트레이딩 시작"""
        # 디버그 로그
        self._add_log(f"🔍 시작 요청 - is_running: {self.is_running}, worker: {self.trading_worker is not None}")

        # 이미 실행 중이면 무시
        if self.is_running:
            self._add_log("⚠️ 이미 실행 중입니다")
            return

        # 이전 워커가 아직 살아있으면 대기
        if self.trading_worker and self.trading_worker.isRunning():
            self._add_log("⏳ 이전 엔진이 종료되는 중입니다. 잠시만 기다려주세요...")
            return

        # 🔧 API 키 검증 (실제 연결 테스트)
        self._add_log("🔑 API 키 검증 중...")
        self.statusbar.showMessage("API 키 검증 중...")

        if not self.config_manager.validate_upbit_keys():
            self._add_log("❌ API 키 검증 실패")
            QMessageBox.warning(
                self,
                "설정 오류",
                "Upbit API 키가 설정되지 않았거나 유효하지 않습니다.\n\n"
                "가능한 원인:\n"
                "• API 키가 잘못 입력되었습니다\n"
                "• API 키가 만료되었습니다\n"
                "• 네트워크 연결에 문제가 있습니다\n\n"
                "설정 메뉴에서 API 키를 다시 확인하세요."
            )
            self.statusbar.showMessage("준비")
            self._open_settings()
            return

        self._add_log("✅ API 키 검증 성공")
        self.statusbar.showMessage("준비")

        # Telegram 검증 (선택사항)
        if not self.config_manager.validate_telegram_config():
            reply = QMessageBox.question(
                self,
                "Telegram 미설정",
                "Telegram 봇이 설정되지 않았습니다.\n"
                "알림을 받을 수 없습니다.\n\n"
                "그래도 계속하시겠습니까?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.No:
                self._open_settings()
                return

        # ========================================
        # 🔄 모드 전환: 아래 주석을 바꾸면 페이퍼/실거래 전환
        # ========================================
        
        # # ✅ 페이퍼 트레이딩 모드 (테스트용 - 실제 주문 안함)
        # reply = QMessageBox.question(
        #     self,
        #     "트레이딩 시작",
        #     "⚠️ <b>트레이딩을 시작하시겠습니까?</b><br><br>"
        #     "페이퍼 트레이딩(Dry Run) 모드로 시작됩니다.<br>"
        #     "실제 주문은 실행되지 않습니다.<br><br>"
        #     "<b>실거래 모드로 전환하려면:</b><br>"
        #     "main_window.py 파일에서 주석을 변경하세요.",
        #     QMessageBox.Yes | QMessageBox.No,
        #     QMessageBox.No
        # )
        
        # 🚨 실거래 모드 (실제 주문 실행 - 돈 잃을 수 있음!)
        reply = QMessageBox.question(
            self,
            "🚨 실거래 모드 시작 확인",
            "⚠️⚠️⚠️ <b>실제 거래 모드입니다!</b> ⚠️⚠️⚠️<br><br>"
            "<b style='color: red;'>실제 돈으로 주문이 실행됩니다!</b><br><br>"
            "확인 사항:<br>"
            "✅ Upbit API 키에 '주문하기' 권한 있음<br>"
            "✅ 충분한 KRW 잔고 확인<br>"
            "✅ DCA 설정 소액으로 조정<br>"
            "✅ 텔레그램 알림 동작 확인<br><br>"
            "<b>정말로 시작하시겠습니까?</b>",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self._add_log("=" * 50)
            self._add_log("🚀 트레이딩 시작")
            self._add_log("=" * 50)
            
            # # ✅ 페이퍼 트레이딩 모드 로그
            # self._add_log("⚠️ 페이퍼 트레이딩 모드 (Dry Run)")
            
            # 🚨 실거래 모드 로그
            self._add_log("🚨🚨🚨 실거래 모드 - 실제 주문 실행 🚨🚨🚨")
            self._add_log("💰 실제 돈으로 거래가 진행됩니다!")
            
            self._add_log("")

            # 🔧 다중 코인 트레이딩 설정 생성
            # 사용자가 선택한 코인 리스트 가져오기
            selected_coins = self.config_manager.get_selected_coins()
            coin_count = len(selected_coins)

            # 선택된 코인 로그 출력
            coins_str = ", ".join([coin.replace('KRW-', '') for coin in selected_coins])
            self._add_log(f"🎯 선택된 코인: {coins_str} ({coin_count}개)")
            self._add_log(f"💰 총 투자 자본: {coin_count * 1000000:,}원 (코인당 1,000,000원)")
            self._add_log("")

            config = {
                # 사용자가 선택한 코인 심볼
                'symbols': selected_coins,
                # 총 투자 자본 (코인당 균등 배분)
                'total_capital': coin_count * 1000000,  # 코인당 100만원
                'strategy': {
                    'period': 20,
                    'std_dev': 2.5
                },
                'risk_management': {
                    'stop_loss_pct': self.dca_config.stop_loss_pct,
                    'take_profit_pct': self.dca_config.take_profit_pct,
                    'max_daily_loss_pct': self.max_daily_loss_pct
                },
                # 코인당 주문 금액
                'order_amount': self.dca_config.levels[0].order_amount if self.dca_config.levels else 100000,
                
                # ========================================
                # 🔄 모드 전환: 아래 주석을 바꾸면 페이퍼/실거래 전환
                # ========================================
                # 'dry_run': True,   # ✅ 페이퍼 트레이딩 모드 (안전)
                'dry_run': False,  # 🚨 실거래 모드 (실제 주문!)
                
                'access_key': self.config_manager.get_upbit_access_key(),
                'secret_key': self.config_manager.get_upbit_secret_key(),
                'telegram': {
                    'token': self.config_manager.get_telegram_bot_token(),
                    'chat_id': self.config_manager.get_telegram_chat_id()
                },
                # DCA 설정
                'dca_config': self.dca_config
            }

            # 리스크 설정 표시 (다단계/단일 구분)
            tp_info = f"다단계 ({len(self.dca_config.take_profit_levels)}레벨)" if self.dca_config.is_multi_level_tp_enabled() else f"{self.dca_config.take_profit_pct}%"
            sl_info = f"다단계 ({len(self.dca_config.stop_loss_levels)}레벨)" if self.dca_config.is_multi_level_sl_enabled() else f"{self.dca_config.stop_loss_pct}%"
            self._add_log(f"📊 리스크 설정: 손절 {sl_info}, 익절 {tp_info}")
            self._add_log(f"💰 DCA 레벨: {len(self.dca_config.levels)}단계 ({'활성화' if self.dca_config.enabled else '비활성화'})")
            
            if self.dca_config.enabled:
                # DCA 레벨 정보 출력
                for level_config in self.dca_config.levels[:3]:  # 처음 3개만 표시
                    self._add_log(f"   레벨 {level_config.level}: {level_config.drop_pct}% 하락 시 {level_config.order_amount:,}원 매수")
                if len(self.dca_config.levels) > 3:
                    self._add_log(f"   ... 외 {len(self.dca_config.levels) - 3}개 레벨")

            # 🔧 트레이딩 모드별 워커 생성
            if self.trading_mode == "semi_auto":
                # ===================================================================
                # 🔧 반자동 모드: SemiAutoWorker (수동매수 + 자동DCA/익절/손절)
                # ===================================================================
                self._add_log("🎯 모드: 반자동 (수동매수 + 자동관리)")
                self._add_log("   - Upbit 앱에서 수동 매수 시 자동 감지")
                self._add_log("   - DCA/익절/손절 자동 실행")
                self._add_log(f"   - 스캔 주기: {self.scan_interval}초")
                
                self.trading_worker = SemiAutoWorker(
                    access_key=self.config_manager.get_upbit_access_key(),
                    secret_key=self.config_manager.get_upbit_secret_key(),
                    dca_config=self.dca_config,
                    dry_run=config['dry_run'],
                    scan_interval=self.scan_interval,
                    balance_update_callback=self.balance_update_callback  # 🔧 잔고 갱신 콜백 전달
                )
                
                # 반자동 모드 시그널 연결
                self.trading_worker.started.connect(self._on_trading_started)
                self.trading_worker.finished.connect(self._on_trading_stopped)
                self.trading_worker.log_signal.connect(self._on_trading_log)
                self.trading_worker.error_signal.connect(self._on_trading_error)
                self.trading_worker.status_signal.connect(self._on_auto_trading_status)
                self.trading_worker.position_update_signal.connect(self._on_position_update)
                self.trading_worker.trade_signal.connect(self._on_auto_trade_executed)
                
                # ===================================================================
                # 📦 보존된 코드: MultiCoinTradingWorker (Bollinger Bands 전략)
                # 나중에 "모드 3" 등으로 활성화 가능
                # ===================================================================
                # self.trading_worker = MultiCoinTradingWorker(config)
                # self.trading_worker.started.connect(self._on_trading_started)
                # self.trading_worker.stopped.connect(self._on_trading_stopped)
                # self.trading_worker.log_message.connect(self._on_trading_log)
                # self.trading_worker.portfolio_update.connect(self._on_portfolio_update)
                # self.trading_worker.coin_update.connect(self._on_coin_update)
                # self.trading_worker.trade_executed.connect(self._on_trade_executed)
                # self.trading_worker.error_occurred.connect(self._on_trading_error)
                
            else:  # full_auto
                # 완전 자동 모드: AutoTradingWorker
                self._add_log("🤖 모드: 완전 자동 (자동매수 + 자동관리)")
                self._add_log(f"   매수 금액: {self.auto_trading_config.buy_amount:,.0f}원")
                self._add_log(f"   모니터링: 상위 {self.auto_trading_config.top_n}개")
                self._add_log(f"   스캔 주기: {self.auto_trading_config.scan_interval}초")
                
                self.trading_worker = AutoTradingWorker(
                    access_key=self.config_manager.get_upbit_access_key(),
                    secret_key=self.config_manager.get_upbit_secret_key(),
                    auto_config=self.auto_trading_config,
                    dca_config=self.dca_config,
                    dry_run=config['dry_run'],
                    balance_update_callback=self.balance_update_callback  # 🔧 잔고 갱신 콜백 전달
                )
                
                # 완전 자동 모드 시그널 연결
                # QThread 기본 시그널
                self.trading_worker.started.connect(self._on_trading_started)
                self.trading_worker.finished.connect(self._on_trading_stopped)
                
                # AutoTradingWorker 커스텀 시그널
                self.trading_worker.log_signal.connect(self._on_trading_log)
                self.trading_worker.error_signal.connect(self._on_trading_error)
                self.trading_worker.status_signal.connect(self._on_auto_trading_status)
                self.trading_worker.position_update_signal.connect(self._on_position_update)
                self.trading_worker.trade_signal.connect(self._on_auto_trade_executed)

            # UI 상태 업데이트
            self.is_running = True
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.status_label.setText("● 실행 중")
            self.status_label.setStyleSheet("color: green;")
            self.statusbar.showMessage("트레이딩 실행 중...")

            # 워커 스레드 시작
            self.trading_worker.start()

    def _stop_trading(self):
        """트레이딩 중지 (비동기)"""
        # 이미 중지 중이면 무시
        if not self.is_running:
            return

        reply = QMessageBox.question(
            self,
            "트레이딩 중지",
            "트레이딩을 중지하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self._add_log("")
            self._add_log("=" * 50)
            self._add_log("■ 트레이딩 중지")
            self._add_log("=" * 50)

            # 즉시 버튼 비활성화 (중복 클릭 방지)
            self.stop_btn.setEnabled(False)

            # 🔧 모드별 Trading Engine 중지
            if self.trading_worker:
                if self.trading_mode == "semi_auto":
                    # 반자동 모드: MultiCoinTradingWorker
                    self._add_log("🛑 반자동 모드 엔진 중지 중...")
                    if hasattr(self.trading_worker, 'stop_trader'):
                        self.trading_worker.stop_trader()
                    else:
                        self.trading_worker.stop_engine()
                else:
                    # 완전 자동 모드: AutoTradingWorker
                    self._add_log("🛑 완전 자동 모드 엔진 중지 중...")
                    self.trading_worker.stop()
                
                self._add_log("⏳ 엔진 종료 대기 중... (GUI 응답 유지)")

                # 🔧 비동기 종료 대기 (GUI 프리징 방지)
                self._shutdown_elapsed = 0
                self._shutdown_timer = QTimer()
                self._shutdown_timer.timeout.connect(self._check_worker_shutdown)
                self._shutdown_timer.start(500)  # 500ms마다 체크

    def _check_worker_shutdown(self):
        """Worker 종료 체크 (비동기, 500ms마다)"""
        if not self.trading_worker:
            # Worker 이미 정리됨
            if self._shutdown_timer:
                self._shutdown_timer.stop()
                self._shutdown_timer = None
            return

        # Worker 종료 확인
        if not self.trading_worker.isRunning():
            # ✅ 정상 종료
            self._add_log(f"✅ 엔진 정상 종료 ({self._shutdown_elapsed / 1000:.1f}초)")
            self._shutdown_timer.stop()
            self._shutdown_timer = None
            self._on_trading_stopped()
            return

        # 타임아웃 체크 (2초 - 빠른 종료)
        self._shutdown_elapsed += 500
        if self._shutdown_elapsed >= 2000:
            # ⚠️ 강제 종료
            self._add_log("⚠️ 엔진 중지 시간 초과, 강제 종료")
            self.trading_worker.terminate()
            self.trading_worker.wait(1000)
            self._shutdown_timer.stop()
            self._shutdown_timer = None
            self._on_trading_stopped()
            return

        # 진행 표시 (1초마다)
        if self._shutdown_elapsed % 1000 == 0:
            self._add_log(f"⏳ 대기 중... ({self._shutdown_elapsed / 1000:.0f}/2초)")

    def balance_update_callback(self):
        """
        🔧 잔고 갱신 콜백 (주문 완료 시 자동 호출)

        OrderManager와 SemiAutoManager에서 호출하는 콜백입니다.
        - 매수/매도 완료 시
        - 수동 매수 감지 시
        """
        # _refresh_balance 호출
        self._refresh_balance()

    def _refresh_balance(self):
        """잔고 새로고침 (비동기)"""
        if not self.config_manager.validate_upbit_keys():
            QMessageBox.warning(
                self,
                "설정 오류",
                "Upbit API 키가 설정되지 않았습니다.\n\n"
                "설정 메뉴에서 API 키를 먼저 설정하세요."
            )
            return

        # 이미 실행 중인 워커가 있다면 대기
        if self.balance_worker and self.balance_worker.isRunning():
            # 🔧 자동 콜백인 경우 로그 출력 안함 (너무 많이 출력됨)
            # self._add_log("⏳ 이미 계좌 정보를 조회 중입니다...")
            return

        # 🔧 자동 콜백인 경우 로그 출력 최소화
        # self._add_log("🔄 계좌 정보 조회 중...")
        self.refresh_btn.setEnabled(False)  # 버튼 비활성화

        # 워커 스레드 생성 및 실행
        self.balance_worker = BalanceWorker(
            self.config_manager.get_upbit_access_key(),
            self.config_manager.get_upbit_secret_key()
        )

        # 시그널 연결
        self.balance_worker.finished.connect(self._on_balance_success)
        self.balance_worker.error.connect(self._on_balance_error)

        # 스레드 시작
        self.balance_worker.start()

    def _on_balance_success(self, result: dict):
        """잔고 조회 성공"""
        krw_balance = result['krw']
        btc_balance = result['btc']

        # UI 업데이트
        self.total_asset_label.setText(f"총 자산: {krw_balance:,.0f}원")
        self._add_log(f"✅ 총 자산: {krw_balance:,.0f}원")

        if btc_balance > 0:
            self._add_log(f"   BTC: {btc_balance:.8f}")

        # 버튼 다시 활성화
        self.refresh_btn.setEnabled(True)

    def _on_balance_error(self, error_msg: str):
        """잔고 조회 실패"""
        self._add_log(f"❌ 계좌 조회 실패: {error_msg}")
        QMessageBox.warning(
            self,
            "조회 실패",
            f"계좌 정보를 가져올 수 없습니다:\n{error_msg}"
        )

        # 버튼 다시 활성화
        self.refresh_btn.setEnabled(True)

    # ========================================
    # Trading Engine 시그널 핸들러
    # ========================================

    def _on_trading_started(self):
        """Trading Engine 시작 시그널 처리"""
        # 로그는 trading_engine.py에서 이미 출력됨 (중복 방지)
        pass

    def _on_trading_stopped(self):
        """Trading Engine 중지 시그널 처리"""
        # 중복 실행 방지 (signal + 수동 호출 모두 대응)
        if not self.is_running:
            return

        self._add_log("✅ Trading Engine 중지 완료")

        self.is_running = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("● 중지됨")
        self.status_label.setStyleSheet("color: red;")
        self.statusbar.showMessage("트레이딩 중지됨")

        # Worker 정리 (재시작 준비)
        if self.trading_worker:
            self.trading_worker = None
            self._add_log("🔧 Worker 정리 완료 - 재시작 준비됨")

    def _on_trading_log(self, message: str):
        """Trading Engine 로그 메시지 처리"""
        self._add_log(message)
    
    def _on_trade_executed(self, trade_data: dict):
        """
        거래 실행 시그널 처리
        
        Args:
            trade_data: 거래 정보
                - timestamp: 거래 시각
                - symbol: 코인 심볼
                - trade_type: 'buy' or 'sell'
                - price: 거래 가격
                - quantity: 거래 수량
                - amount: 거래 금액
                - profit: 손익 (매도 시)
                - profit_pct: 손익률 (매도 시)
                - reason: 거래 사유
                - order_id: 주문 ID
        """
        try:
            from gui.trade_data import Trade
            
            # Trade 객체 생성
            trade = Trade.from_dict(trade_data)
            
            # 거래 내역에 추가 (최신 거래가 위에 오도록)
            self.trade_history.insert(0, trade)
            
            # 테이블 업데이트
            self._update_trade_history_table()
            
            # 로그 출력
            emoji = trade.get_type_emoji()
            trade_type = trade.get_type_text()
            symbol_short = trade.get_symbol_short()
            
            if trade.trade_type == 'buy':
                self._add_log(f"{emoji} {symbol_short} {trade_type}: {trade.price:,.0f}원 × {trade.quantity:.8f} = {trade.amount:,.0f}원")

                # 🔧 매수 발생 시 즉시 해당 코인 상태 조회하여 활성 포지션 테이블 업데이트
                if self.trading_worker:
                    coin_status = self.trading_worker.get_coin_status(trade.symbol)
                    if coin_status:
                        self._on_coin_update(trade.symbol, coin_status)
            else:
                self._add_log(f"{emoji} {symbol_short} {trade_type}: {trade.price:,.0f}원 × {trade.quantity:.8f} = {trade.amount:,.0f}원 | 손익: {trade.profit:+,.0f}원 ({trade.profit_pct:+.2f}%)")
                
                # 🔧 매도 발생 시에도 즉시 해당 코인 상태 조회하여 활성 포지션 테이블 업데이트
                if self.trading_worker:
                    coin_status = self.trading_worker.get_coin_status(trade.symbol)
                    if coin_status:
                        self._on_coin_update(trade.symbol, coin_status)

        except Exception as e:
            self._add_log(f"⚠️ 거래 내역 업데이트 오류: {e}")

    def _on_portfolio_update(self, portfolio_status: dict):
        """
        포트폴리오 전체 상태 업데이트 처리

        Args:
            portfolio_status: 포트폴리오 통합 상태
                - total_initial_capital: 총 시작 자본
                - total_current_asset: 총 현재 자산
                - total_return_pct: 전체 수익률
                - coins: 개별 코인 상태 딕셔너리
                - summary: 요약 정보
        """
        try:
            # 총 자산 및 수익률 업데이트
            total_asset = portfolio_status.get('total_current_asset', 0)
            return_pct = portfolio_status.get('total_return_pct', 0)

            # 총 자산 업데이트
            self.total_asset_label.setText(f"총 자산: {total_asset:,.0f}원")

            # 수익률 업데이트 (색상 변경)
            if return_pct > 0:
                self.profit_label.setText(f"수익률: +{return_pct:.2f}%")
                self.profit_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
            elif return_pct < 0:
                self.profit_label.setText(f"수익률: {return_pct:.2f}%")
                self.profit_label.setStyleSheet("color: #f44336; font-weight: bold;")
            else:
                self.profit_label.setText(f"수익률: {return_pct:.2f}%")
                self.profit_label.setStyleSheet("color: gray;")

            # MDD 업데이트
            if return_pct < 0:
                self.mdd_label.setText(f"최대 낙폭: {abs(return_pct):.2f}%")
            else:
                self.mdd_label.setText("최대 낙폭: 0.00%")

            # 포지션 보유 코인 수 표시
            summary = portfolio_status.get('summary', {})
            position_count = summary.get('position_count', 0)
            coin_count = summary.get('coin_count', 0)

            self.price_label.setText(f"포지션: {position_count}/{coin_count}개 코인 보유 중")

        except Exception as e:
            self._add_log(f"⚠️ 포트폴리오 업데이트 오류: {e}")

    def _on_coin_update(self, symbol: str, coin_status: dict):
        """
        개별 코인 상태 업데이트 처리 → 포지션 테이블 업데이트

        Args:
            symbol: 코인 심볼 (예: 'KRW-BTC')
            coin_status: 코인 상태
                - position: 보유 수량
                - entry_price: 진입가
                - current_price: 현재가
                - profit_loss: 평가손익 (원)
                - return_pct: 손익률 (%)
                - entry_time: 진입시각
        """
        try:
            # 심볼에서 'KRW-' 제거
            symbol_short = symbol.replace('KRW-', '')

            # 포지션 정보 추출
            position = coin_status.get('position', 0)
            entry_price = coin_status.get('entry_price')  # 최초 진입가 (테이블 표시용)
            avg_entry_price = coin_status.get('avg_entry_price')  # 🔧 DCA 평균 단가 (손익 계산용)
            current_price = coin_status.get('current_price') or coin_status.get('last_price')  # 🔧 SemiAuto는 current_price, MultiCoin은 last_price

            # 🔧 평가손익 계산 (DCA 평균 단가 기준)
            profit_loss = 0
            return_pct = 0
            if position > 0 and avg_entry_price and current_price:
                profit_loss = (current_price - avg_entry_price) * position
                return_pct = ((current_price - avg_entry_price) / avg_entry_price) * 100
            elif position > 0 and entry_price and current_price:
                # avg_entry_price가 없으면 entry_price 사용 (하위 호환)
                profit_loss = (current_price - entry_price) * position
                return_pct = ((current_price - entry_price) / entry_price) * 100

            # 🔧 포지션이 없으면 테이블에 표시하지 않음 (매수 완료 시에만 표시)
            if position <= 0 or not entry_price:
                # 기존에 테이블에 있었다면 제거 (매도 완료)
                for row in range(self.position_table.rowCount()):
                    item = self.position_table.item(row, 0)
                    if item and item.text() == symbol_short:
                        self.position_table.removeRow(row)
                        # 🔧 매도 후 요약 정보 업데이트
                        self._update_position_summary()
                        break
                return

            # ✅ 포지션 보유 중 - 테이블에서 해당 심볼 행 찾기
            row_index = -1
            for row in range(self.position_table.rowCount()):
                item = self.position_table.item(row, 0)
                if item and item.text() == symbol_short:
                    row_index = row
                    break

            # 행이 없으면 새로 추가 (첫 매수)
            if row_index == -1:
                row_index = self.position_table.rowCount()
                self.position_table.insertRow(row_index)

            # 심볼
            symbol_item = QTableWidgetItem(symbol_short)
            symbol_item.setFont(QFont("Consolas", 10, QFont.Bold))
            self.position_table.setItem(row_index, 0, symbol_item)

            # 상태 (검은색)
            status_item = QTableWidgetItem("보유중")
            status_item.setForeground(Qt.black)
            status_item.setFont(QFont("Consolas", 10, QFont.Bold))
            self.position_table.setItem(row_index, 1, status_item)

            # 진입가
            entry_price_item = QTableWidgetItem(f"{entry_price:,.0f}원")
            entry_price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.position_table.setItem(row_index, 2, entry_price_item)

            # 현재가
            if current_price:
                current_price_item = QTableWidgetItem(f"{current_price:,.0f}원")
                current_price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.position_table.setItem(row_index, 3, current_price_item)
            else:
                self.position_table.setItem(row_index, 3, QTableWidgetItem("-"))

            # 수량
            qty_item = QTableWidgetItem(f"{position:.8f}")
            qty_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.position_table.setItem(row_index, 4, qty_item)

            # 평가손익 (색상: 수익=빨강, 손실=파랑, 0=검은색)
            profit_loss_item = QTableWidgetItem(f"{profit_loss:+,.0f}원")
            profit_loss_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if profit_loss > 0:
                profit_loss_item.setForeground(Qt.red)  # 🔴 빨강 (수익)
                profit_loss_item.setFont(QFont("Consolas", 10, QFont.Bold))
            elif profit_loss < 0:
                profit_loss_item.setForeground(Qt.blue)  # 🔵 파랑 (손실)
                profit_loss_item.setFont(QFont("Consolas", 10, QFont.Bold))
            else:
                profit_loss_item.setForeground(Qt.black)  # ⚫ 검은색 (0)
            self.position_table.setItem(row_index, 5, profit_loss_item)

            # 손익률 (색상: 수익=빨강, 손실=파랑, 0=검은색)
            return_pct_item = QTableWidgetItem(f"{return_pct:+.2f}%")
            return_pct_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if return_pct > 0:
                return_pct_item.setForeground(Qt.red)  # 🔴 빨강 (수익)
                return_pct_item.setFont(QFont("Consolas", 10, QFont.Bold))
            elif return_pct < 0:
                return_pct_item.setForeground(Qt.blue)  # 🔵 파랑 (손실)
                return_pct_item.setFont(QFont("Consolas", 10, QFont.Bold))
            else:
                return_pct_item.setForeground(Qt.black)  # ⚫ 검은색 (0)
            self.position_table.setItem(row_index, 6, return_pct_item)

            # 🔧 포지션 요약 정보 업데이트
            self._update_position_summary()

        except Exception as e:
            self._add_log(f"⚠️ 코인 업데이트 오류 ({symbol}): {e}")

    def _update_position_summary(self):
        """
        포지션 요약 정보 업데이트

        테이블에 있는 모든 포지션의 평가손익을 합산하여 표시
        """
        try:
            total_profit_loss = 0
            position_count = self.position_table.rowCount()

            # 테이블의 모든 행에서 평가손익 합산
            for row in range(position_count):
                profit_item = self.position_table.item(row, 5)  # 평가손익 컬럼
                if profit_item:
                    # "+1,500원" → 1500 변환
                    profit_text = profit_item.text().replace('원', '').replace(',', '').replace('+', '').replace(' ', '')
                    try:
                        profit_loss = float(profit_text)
                        total_profit_loss += profit_loss
                    except ValueError:
                        pass

            # 요약 텍스트 생성
            if position_count > 0:
                summary_text = f"총 {position_count}개 보유 중 | 전체 평가손익: {total_profit_loss:+,.0f}원"

                # 색상 설정
                if total_profit_loss > 0:
                    self.position_summary_label.setStyleSheet(
                        "color: red; font-weight: bold; padding: 5px; background-color: #ffe5e5; border-radius: 3px;"
                    )
                elif total_profit_loss < 0:
                    self.position_summary_label.setStyleSheet(
                        "color: blue; font-weight: bold; padding: 5px; background-color: #e5e5ff; border-radius: 3px;"
                    )
                else:
                    self.position_summary_label.setStyleSheet(
                        "color: #666; padding: 5px; background-color: #f5f5f5; border-radius: 3px;"
                    )
            else:
                summary_text = "총 0개 보유 중 | 전체 평가손익: 0원 (0.00%)"
                self.position_summary_label.setStyleSheet(
                    "color: #666; padding: 5px; background-color: #f5f5f5; border-radius: 3px;"
                )

            self.position_summary_label.setText(summary_text)

        except Exception as e:
            self._add_log(f"⚠️ 포지션 요약 업데이트 오류: {e}")

    def _on_status_update(self, status: dict):
        """
        Trading Engine 상태 업데이트 처리

        Args:
            status: 엔진 상태 딕셔너리
                - symbol: 심볼
                - position: 현재 포지션 (BTC 수량)
                - entry_price: 진입 가격
                - entry_time: 진입 시각
                - initial_capital: 시작 자본
                - current_capital: 현재 KRW 잔액
                - btc_value: BTC 평가금액
                - total_asset: 총 자산 (KRW + BTC)
                - return_pct: 수익률 (%)
                - total_trades: 총 거래 횟수
                - winning_trades: 성공 거래
                - losing_trades: 손실 거래
                - win_rate: 승률 (%)
        """
        try:
            # 🔧 총 자산 = KRW 잔액 + BTC 평가금액
            total_asset = status.get('total_asset', 0)
            return_pct = status.get('return_pct', 0)

            # 총 자산 업데이트
            self.total_asset_label.setText(f"총 자산: {total_asset:,.0f}원")

            # 수익률 업데이트 (색상 변경)
            if return_pct > 0:
                self.profit_label.setText(f"수익률: +{return_pct:.2f}%")
                self.profit_label.setStyleSheet("color: #4CAF50; font-weight: bold;")  # 녹색
            elif return_pct < 0:
                self.profit_label.setText(f"수익률: {return_pct:.2f}%")
                self.profit_label.setStyleSheet("color: #f44336; font-weight: bold;")  # 빨강
            else:
                self.profit_label.setText(f"수익률: {return_pct:.2f}%")
                self.profit_label.setStyleSheet("color: gray;")

            # MDD 업데이트 (추후 추가 예정)
            # 현재는 간단히 수익률 기반으로 표시
            if return_pct < 0:
                self.mdd_label.setText(f"최대 낙폭: {abs(return_pct):.2f}%")
            else:
                self.mdd_label.setText("최대 낙폭: 0.00%")

            # 포지션 정보 업데이트
            position = status.get('position', 0)
            entry_price = status.get('entry_price')
            last_price = status.get('last_price')

            if position > 0 and entry_price:
                # 포지션 보유 중 - 현재가와 수익률 표시
                btc_value = status.get('btc_value', 0)
                if last_price:
                    profit_loss = btc_value - (position * entry_price)
                    profit_pct = (profit_loss / (position * entry_price)) * 100 if entry_price else 0
                    self.price_label.setText(
                        f"포지션: {position:.8f} BTC @ {entry_price:,.0f}원\n"
                        f"현재가: {last_price:,.0f}원 ({profit_pct:+.2f}%)"
                    )
                else:
                    self.price_label.setText(f"포지션: {position:.8f} BTC @ {entry_price:,.0f}원")
            else:
                # 포지션 없음
                self.price_label.setText("포지션: 없음")

        except Exception as e:
            self._add_log(f"⚠️ 상태 업데이트 오류: {e}")

    def _on_trading_error(self, error_msg: str):
        """Trading Engine 에러 처리 (팝업 + 로그)"""
        from datetime import datetime

        # 로그에 에러 기록
        self._add_log(f"❌ 에러: {error_msg}")

        # 🔧 에러 팝업 (더 명확한 메시지)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        QMessageBox.critical(
            self,
            "🚨 트레이딩 엔진 오류",
            f"<b>트레이딩 엔진에서 오류가 발생했습니다</b><br><br>"
            f"<b>시각:</b> {timestamp}<br>"
            f"<b>오류 내용:</b><br>"
            f"<code>{error_msg}</code><br><br>"
            f"<b>조치 방법:</b><br>"
            f"1. 로그를 확인하세요<br>"
            f"2. 트레이딩을 중지하고 재시작해보세요<br>"
            f"3. 문제가 지속되면 설정을 확인하세요"
        )

    # ========================================
    # 완전 자동 모드 시그널 핸들러
    # ========================================

    def _on_auto_trading_status(self, status: dict):
        """
        완전 자동 모드 상태 업데이트 처리 (AutoTradingWorker)
        
        Args:
            status: 자동 트레이딩 상태
                - monitoring_count: 모니터링 중인 코인 수
                - managed_positions: 관리 중인 포지션 수
                - daily_trades: 오늘 거래 횟수
                - daily_pnl_pct: 오늘 손익률
                - krw_balance: KRW 잔고
                - positions: 포지션 리스트
        """
        try:
            # 상단 통계 업데이트
            krw_balance = status.get('krw_balance', 0)
            daily_pnl = status.get('daily_pnl_pct', 0)
            
            self.total_asset_label.setText(f"KRW 잔고: {krw_balance:,.0f}원")
            
            # 일일 손익률 표시
            if daily_pnl > 0:
                self.profit_label.setText(f"오늘 손익: +{daily_pnl:.2f}%")
                self.profit_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
            elif daily_pnl < 0:
                self.profit_label.setText(f"오늘 손익: {daily_pnl:.2f}%")
                self.profit_label.setStyleSheet("color: #f44336; font-weight: bold;")
            else:
                self.profit_label.setText(f"오늘 손익: {daily_pnl:.2f}%")
                self.profit_label.setStyleSheet("color: gray;")
            
            # 모니터링/관리 정보 표시
            monitoring = status.get('monitoring_count', 0)
            managed = status.get('managed_positions', 0)
            daily_trades = status.get('daily_trades', 0)
            
            self.price_label.setText(
                f"모니터링: {monitoring}개 | 관리 중: {managed}개\n"
                f"오늘 거래: {daily_trades}회"
            )
            
        except Exception as e:
            self._add_log(f"⚠️ 자동 트레이딩 상태 업데이트 오류: {e}")

    def _on_position_update(self, position_data: dict):
        """
        완전 자동 모드 포지션 업데이트 처리 (AutoTradingWorker)
        
        Args:
            position_data: 포지션 정보
                - symbol: 심볼
                - position: 보유 수량
                - entry_price: 진입가
                - current_price: 현재가
                - profit_loss: 평가손익
                - return_pct: 손익률
                - entry_time: 진입 시각
        """
        try:
            symbol = position_data.get('symbol', '')
            # 기존 _on_coin_update와 동일한 로직 재사용
            self._on_coin_update(symbol, position_data)
            
        except Exception as e:
            self._add_log(f"⚠️ 포지션 업데이트 오류: {e}")

    def _on_auto_trade_executed(self, trade_data: dict):
        """
        완전 자동 모드 거래 실행 처리 (AutoTradingWorker)
        
        Args:
            trade_data: 거래 정보
                - symbol: 심볼
                - trade_type: 'buy' or 'sell'
                - price: 거래가
                - quantity: 수량
                - amount: 금액
                - profit: 손익 (매도 시)
                - profit_pct: 손익률 (매도 시)
                - reason: 사유
        """
        try:
            # 기존 _on_trade_executed와 동일한 로직 재사용
            self._on_trade_executed(trade_data)
            
        except Exception as e:
            self._add_log(f"⚠️ 자동 거래 내역 업데이트 오류: {e}")

    # ========================================
    # UI 업데이트
    # ========================================

    def _update_status(self):
        """상태 정보 업데이트"""
        # 🔧 사이드바 심볼 정보 (선택된 코인 개수로 업데이트)
        selected_coin_count = len(self.config_manager.get_selected_coins())
        self.symbol_label.setText(f"다중 코인 ({selected_coin_count}개)")
    
    def _update_trade_history_table(self):
        """거래 내역 테이블 업데이트"""
        try:
            # 정렬 비활성화 (업데이트 중)
            self.trade_history_table.setSortingEnabled(False)
            
            # 테이블 초기화
            self.trade_history_table.setRowCount(len(self.trade_history))
            
            # 거래 내역 통계 계산
            total_trades = len(self.trade_history)
            buy_count = sum(1 for t in self.trade_history if t.trade_type == 'buy')
            sell_count = sum(1 for t in self.trade_history if t.trade_type == 'sell')
            total_profit = sum(t.profit for t in self.trade_history if t.trade_type == 'sell')
            
            # 누적 수익률 계산 (총 매수 금액 대비)
            total_buy_amount = sum(t.amount for t in self.trade_history if t.trade_type == 'buy')
            total_profit_pct = (total_profit / total_buy_amount * 100) if total_buy_amount > 0 else 0.0
            
            # 요약 정보 업데이트
            self.trade_summary_label.setText(
                f"총 {total_trades}건 | 매수: {buy_count}건, 매도: {sell_count}건 | "
                f"누적 손익: {total_profit:+,.0f}원 ({total_profit_pct:+.2f}%)"
            )
            
            # 색상 변경
            if total_profit > 0:
                self.trade_summary_label.setStyleSheet("color: #4CAF50; padding: 5px; background-color: #f5f5f5; border-radius: 3px; font-weight: bold;")
            elif total_profit < 0:
                self.trade_summary_label.setStyleSheet("color: #f44336; padding: 5px; background-color: #f5f5f5; border-radius: 3px; font-weight: bold;")
            else:
                self.trade_summary_label.setStyleSheet("color: #666; padding: 5px; background-color: #f5f5f5; border-radius: 3px;")
            
            # 각 거래 내역 추가
            for row, trade in enumerate(self.trade_history):
                # 시각
                time_item = QTableWidgetItem(trade.get_time_str())
                time_item.setTextAlignment(Qt.AlignCenter)
                self.trade_history_table.setItem(row, 0, time_item)
                
                # 심볼
                symbol_item = QTableWidgetItem(trade.get_symbol_short())
                symbol_item.setFont(QFont("Consolas", 9, QFont.Bold))
                symbol_item.setTextAlignment(Qt.AlignCenter)
                self.trade_history_table.setItem(row, 1, symbol_item)
                
                # 유형 (매수/매도)
                type_item = QTableWidgetItem(f"{trade.get_type_emoji()} {trade.get_type_text()}")
                type_item.setTextAlignment(Qt.AlignCenter)
                if trade.trade_type == 'buy':
                    type_item.setForeground(Qt.red)
                else:
                    type_item.setForeground(Qt.blue)
                self.trade_history_table.setItem(row, 2, type_item)
                
                # 가격
                price_item = QTableWidgetItem(f"{trade.price:,.0f}")
                price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.trade_history_table.setItem(row, 3, price_item)
                
                # 수량
                qty_item = QTableWidgetItem(f"{trade.quantity:.8f}")
                qty_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.trade_history_table.setItem(row, 4, qty_item)
                
                # 금액
                amount_item = QTableWidgetItem(f"{trade.amount:,.0f}")
                amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.trade_history_table.setItem(row, 5, amount_item)
                
                # 손익
                if trade.trade_type == 'sell':
                    profit_text = f"{trade.profit:+,.0f} ({trade.profit_pct:+.2f}%)"
                    profit_item = QTableWidgetItem(profit_text)
                    profit_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    if trade.profit > 0:
                        profit_item.setForeground(Qt.red)
                        profit_item.setFont(QFont("Consolas", 9, QFont.Bold))
                    elif trade.profit < 0:
                        profit_item.setForeground(Qt.blue)
                        profit_item.setFont(QFont("Consolas", 9, QFont.Bold))
                else:
                    profit_item = QTableWidgetItem("-")
                    profit_item.setTextAlignment(Qt.AlignCenter)
                self.trade_history_table.setItem(row, 6, profit_item)
                
                # 사유
                reason_item = QTableWidgetItem(trade.reason)
                reason_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                self.trade_history_table.setItem(row, 7, reason_item)
            
            # 정렬 다시 활성화
            self.trade_history_table.setSortingEnabled(True)
            
        except Exception as e:
            self._add_log(f"⚠️ 거래 내역 테이블 업데이트 오류: {e}")

    def _add_log(self, message: str):
        """로그 추가 (최대 1000줄 유지)"""
        from datetime import datetime

        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")

        # 🔧 로그 자동 정리 (최대 1000줄)
        document = self.log_text.document()
        if document.lineCount() > 1000:
            # 처음 100줄 삭제 (한 번에 여러 줄 삭제로 성능 개선)
            cursor = self.log_text.textCursor()
            cursor.movePosition(cursor.Start)
            for _ in range(100):
                cursor.select(cursor.LineUnderCursor)
                cursor.removeSelectedText()
                cursor.deleteChar()  # 줄바꿈 문자 삭제

        # 자동 스크롤 (최신 로그로)
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    # ========================================
    # 종료 처리
    # ========================================

    def closeEvent(self, event):
        """윈도우 닫기 이벤트"""
        # 종료 타이머 정리
        if self._shutdown_timer:
            self._shutdown_timer.stop()
            self._shutdown_timer = None

        if self.is_running:
            reply = QMessageBox.question(
                self,
                "종료 확인",
                "트레이딩이 실행 중입니다.\n정말 종료하시겠습니까?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.No:
                event.ignore()
                return

            # 🔧 모드별 Trading Engine 중지
            if self.trading_worker:
                self._add_log("⏸️ Trading Engine 중지 중...")
                
                if self.trading_mode == "semi_auto":
                    # 반자동 모드: MultiCoinTradingWorker
                    if hasattr(self.trading_worker, 'stop_trader'):
                        self.trading_worker.stop_trader()
                    else:
                        self.trading_worker.stop_engine()
                else:
                    # 완전 자동 모드: AutoTradingWorker
                    self.trading_worker.stop()

                # 스레드 종료 대기 (최대 5초로 단축)
                if not self.trading_worker.wait(5000):
                    self._add_log("⚠️ 엔진 중지 시간 초과, 강제 종료")
                    self.trading_worker.terminate()
                    self.trading_worker.wait(1000)  # 강제 종료 후 1초 대기

                # Worker 정리
                self.trading_worker = None

        # Balance Worker도 정리
        if self.balance_worker and self.balance_worker.isRunning():
            self.balance_worker.wait(1000)
            self.balance_worker = None

        event.accept()


# 테스트 코드
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setApplicationName("Upbit DCA Trader")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
