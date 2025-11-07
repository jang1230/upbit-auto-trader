"""
Main Window - 메인 화면
Upbit DCA Trader GUI 메인 윈도우
"""

import sys
import os
import time
import logging

# 🔧 로거 초기화
logger = logging.getLogger(__name__)

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
from gui.dca_simulator import DcaSimulatorDialog
from gui.advanced_dca_dialog import AdvancedDcaDialog
from gui.coin_selection_dialog import CoinSelectionDialog  # 🔧 코인 선택 다이얼로그
from core.utils import format_price  # 🔧 가격 포맷팅 유틸리티

# V4 Backend Components
from core.config_manager import ConfigManager  # V4 버전
from core.group_manager import GroupManager
from core.upbit_api import UpbitAPI

# ============================================================
# V4 Imports
# ============================================================
from gui.v4_worker import V4Worker  # V4 메인 워커

# ============================================================
# V3 Legacy Imports (최소한 보존 - API 키 검증에 필요)
# ============================================================
from gui.config_manager import ConfigManager as V3ConfigManager  # V3 버전 (검증 메서드용)

# V3 DEPRECATED - 아래는 모두 사용 중지됨
# from gui.trading_worker import TradingEngineWorker
# from gui.multi_coin_worker import MultiCoinTradingWorker
# from gui.auto_trading_worker import AutoTradingWorker
# from gui.semi_auto_worker import SemiAutoWorker
# from gui.dca_config import DcaConfigManager
# from gui.auto_trading_config import AutoTradingConfig


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


class MyAssetPreparationWorker(QThread):
    """
    MyAsset WebSocket 구독 준비 워커

    프로그램 시작 시 백그라운드에서 MyAsset 구독을 수행하여
    사용자가 시작 버튼을 누를 때 즉시 실시간 감지가 가능하도록 준비
    """

    # 시그널 정의
    preparation_complete = Signal()  # 구독 준비 완료
    preparation_failed = Signal(str)  # 구독 실패 (에러 메시지)
    status_update = Signal(str)  # 상태 업데이트 메시지

    def __init__(self, access_key: str, secret_key: str):
        super().__init__()
        self.access_key = access_key
        self.secret_key = secret_key

    def run(self):
        """백그라운드에서 MyAsset 구독 실행"""
        import asyncio

        try:
            self.status_update.emit("🔄 실시간 감지 준비 중...")

            # asyncio 이벤트 루프 생성
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # MyAsset WebSocket 연결 및 구독
            from core.upbit_websocket import MyAssetWebSocket

            myasset_ws = MyAssetWebSocket(self.access_key, self.secret_key)

            # 연결
            connected = loop.run_until_complete(myasset_ws.connect())
            if not connected:
                self.preparation_failed.emit("MyAsset WebSocket 연결 실패")
                return

            # 구독 (연결 유지, start_trading에서 재사용)
            loop.run_until_complete(myasset_ws.subscribe_myasset())

            # 🔧 disconnect() 제거! (23초 블로킹 문제 해결)
            # - 연결은 유지됨 (Worker 종료 시 자동 정리)
            # - 구독 가능 여부만 확인하면 됨

            # 성공
            self.preparation_complete.emit()
            self.status_update.emit("✅ 실시간 감지 준비 완료!")

            # 이벤트 루프 정리 (연결은 유지하되 루프는 종료)
            loop.close()

        except Exception as e:
            self.preparation_failed.emit(f"준비 실패: {str(e)}")
            self.status_update.emit("⚠️ 실시간 감지 사용 불가 (Fallback 모드)")


class MainWindow(QMainWindow):
    """
    메인 윈도우

    트레이딩 봇 실행/중지, 상태 모니터링
    """

    def __init__(self):
        super().__init__()

        # V4 Configuration & Managers
        self.config_path = "config/trading_config.json"
        self.config_manager = ConfigManager(self.config_path)
        self.config = self.config_manager.load_config()
        self.global_settings = self.config.get("global_settings", {})

        # V4 Group Manager
        self.group_manager = GroupManager(self.config_path)

        # ============================================================
        # V3 Legacy Configuration (최소한 보존)
        # ============================================================
        # V3 ConfigManager (API 키 검증에만 사용)
        self.v3_config_manager = V3ConfigManager()

        # V3 DEPRECATED - 아래는 모두 사용 중지됨
        # self.dca_config_manager = DcaConfigManager()
        # self.dca_config = self.dca_config_manager.load()
        # self.trading_mode = "semi_auto"
        # self.auto_trading_config = AutoTradingConfig.from_file('auto_trading_config.json')
        # self.scan_interval = 60
        
        self.is_running = False
        self.balance_worker = None  # 잔고 조회 워커 스레드
        self.trading_worker = None  # Trading Engine 워커 스레드
        self.preparation_worker = None  # MyAsset 구독 준비 워커
        self.myasset_ready = False  # MyAsset 구독 준비 완료 여부
        self.api_keys_validated = False  # 🔧 API 키 검증 완료 플래그 (Step 1 성공 시 True)
        self._shutdown_timer = None  # 비동기 종료 타이머
        self._shutdown_elapsed = 0  # 종료 대기 시간

        # 🔧 GUI 업데이트 throttling
        self.last_summary_update = 0  # 포지션 요약 마지막 업데이트 시간

        # 🔧 거래 내역 저장
        self.trade_history = []  # Trade 객체 리스트

        # V3 Legacy - 리스크 관리 파라미터 (V4에서는 그룹별/전역 설정으로 이동)
        # self.stop_loss_pct = self.dca_config.stop_loss_pct
        # self.take_profit_pct = self.dca_config.take_profit_pct
        # self.max_daily_loss_pct = 10.0

        self.setWindowTitle("Upbit DCA Trader V4")
        self.setMinimumSize(1600, 850)  # V4: 윈도우 크기 증가

        self._init_ui()
        self._init_menu()
        self._init_statusbar()
        self._update_status()

        # 🔧 순차적 초기화 시작 (500ms 후)
        QTimer.singleShot(500, self._start_sequential_initialization)

    def _get_all_coins_from_groups(self):
        """
        V4 그룹에서 모든 코인 리스트 가져오기 (V3 호환용)

        Returns:
            List[str]: 모든 그룹의 코인 리스트 (중복 제거)
        """
        try:
            all_groups = self.group_manager.get_all_groups()
            all_coins = []

            for group in all_groups.values():
                coins = group.get("coins", [])
                all_coins.extend(coins)

            # 중복 제거하고 정렬
            unique_coins = list(set(all_coins))
            unique_coins.sort()

            return unique_coins
        except Exception as e:
            logger.error(f"코인 리스트 가져오기 실패: {e}")
            return []

    def _init_ui(self):
        """UI 초기화 - V4: Dry Run 배너 + 좌측 사이드바 + 우측 메인 패널"""
        # 중앙 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # V4: 메인 레이아웃을 QVBoxLayout으로 변경 (배너 + 스플리터)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ===========================================
        # V4 Step 1: Dry Run 배너 (최상단 고정)
        # ===========================================
        self._create_dry_run_banner(main_layout)

        # 🔧 좌우 분할 스플리터
        main_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(main_splitter)

        # ========================================
        # 좌측 사이드바 (설정 영역) - V4 스펙
        # ========================================
        sidebar_widget = QWidget()
        sidebar_widget.setMaximumWidth(280)  # V4: 충분한 크기
        sidebar_widget.setMinimumWidth(250)
        sidebar_layout = QVBoxLayout(sidebar_widget)
        sidebar_layout.setContentsMargins(5, 8, 5, 8)
        sidebar_layout.setSpacing(10)

        # 사이드바를 스크롤 가능하게 (설정이 많을 경우 대비)
        sidebar_scroll = QScrollArea()
        sidebar_scroll.setWidget(sidebar_widget)
        sidebar_scroll.setWidgetResizable(True)
        sidebar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # ===========================================
        # V4 Step 5: 사이드바 정리
        # ===========================================

        # 1. 상태 패널
        status_group = QGroupBox("📊 상태")
        status_layout = QVBoxLayout()

        self.status_label = QLabel("● 중지됨")
        self.status_label.setFont(QFont("맑은 고딕", 11, QFont.Bold))
        status_layout.addWidget(self.status_label)

        # V4: 그룹 수와 코인 수 표시
        groups = self.group_manager.get_all_groups()
        selected_coin_count = len(self._get_all_coins_from_groups())
        self.symbol_label = QLabel(f"총 {selected_coin_count}개 코인\n({len(groups)}개 그룹)")
        self.symbol_label.setFont(QFont("맑은 고딕", 9))
        status_layout.addWidget(self.symbol_label)

        status_group.setLayout(status_layout)
        sidebar_layout.addWidget(status_group)

        # 2. 계좌 정보 패널
        account_group = QGroupBox("💰 계좌")
        account_layout = QVBoxLayout()

        self.total_asset_label = QLabel("총 자산: 로딩 중...")
        self.total_asset_label.setFont(QFont("맑은 고딕", 9))
        account_layout.addWidget(self.total_asset_label)

        self.profit_label = QLabel("수익률: +0.00%")
        self.profit_label.setFont(QFont("맑은 고딕", 9))
        account_layout.addWidget(self.profit_label)

        # 새로고침 버튼
        refresh_btn = QPushButton("🔄 새로고침")
        refresh_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 5px;")
        refresh_btn.clicked.connect(self._refresh_account_info)
        account_layout.addWidget(refresh_btn)

        account_group.setLayout(account_layout)
        sidebar_layout.addWidget(account_group)

        # 3. 제어 버튼
        button_group = QGroupBox("⚙️ 제어")
        button_layout = QVBoxLayout()

        # V4: 그룹 관리 버튼
        group_manage_btn = QPushButton("📁 그룹관리")
        group_manage_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 8px; font-weight: bold;")
        group_manage_btn.clicked.connect(self._open_group_management)
        button_layout.addWidget(group_manage_btn)

        # V4: 전역 설정 버튼
        global_settings_btn = QPushButton("⚙️ 전역설정")
        global_settings_btn.setStyleSheet("background-color: #673AB7; color: white; padding: 8px; font-weight: bold;")
        global_settings_btn.clicked.connect(self._open_global_settings)
        button_layout.addWidget(global_settings_btn)

        # 시작 버튼
        self.start_btn = QPushButton("▶ 시작")
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px; font-size: 13px; font-weight: bold;")
        self.start_btn.clicked.connect(self._start_trading)
        button_layout.addWidget(self.start_btn)

        # 중지 버튼
        self.stop_btn = QPushButton("■ 중지")
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

        # ===========================================
        # V4 Step 2: 포지션 요약 패널
        # ===========================================
        self._create_position_summary_panel(main_panel_layout)

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

        # ===========================================
        # V4 Step 4: 11개 컬럼 테이블
        # ===========================================
        self.position_table = QTableWidget()
        self.position_table.setColumnCount(11)  # V4: 11개 컬럼
        self.position_table.setHorizontalHeaderLabels([
            "그룹", "심볼", "매수", "DCA", "익절", "손절",
            "평균가", "현재가", "수량", "평가손익", "수익률(%)"
        ])

        # 테이블 스타일 설정
        self.position_table.setFont(QFont("맑은 고딕", 10))  # 한글 가독성 개선
        self.position_table.setAlternatingRowColors(True)
        self.position_table.setEditTriggers(QTableWidget.NoEditTriggers)  # 읽기 전용
        self.position_table.setSelectionBehavior(QTableWidget.SelectRows)  # 행 단위 선택

        # V4: 행 높이 설정 (가독성 개선)
        self.position_table.verticalHeader().setDefaultSectionSize(35)  # 기본 행 높이 35px
        self.position_table.verticalHeader().setMinimumSectionSize(30)  # 최소 행 높이 30px

        # V4 컬럼 너비 설정 (1320px 메인 패널에 맞춤)
        header = self.position_table.horizontalHeader()
        header.setDefaultSectionSize(100)  # 기본 컬럼 너비
        header.setMinimumSectionSize(60)  # 최소 컬럼 너비
        header.setSectionResizeMode(0, QHeaderView.Fixed)  # 그룹
        header.resizeSection(0, 100)
        header.setSectionResizeMode(1, QHeaderView.Fixed)  # 심볼
        header.resizeSection(1, 90)
        header.setSectionResizeMode(2, QHeaderView.Fixed)  # 매수
        header.resizeSection(2, 70)
        header.setSectionResizeMode(3, QHeaderView.Fixed)  # DCA
        header.resizeSection(3, 70)
        header.setSectionResizeMode(4, QHeaderView.Fixed)  # 익절
        header.resizeSection(4, 70)
        header.setSectionResizeMode(5, QHeaderView.Fixed)  # 손절
        header.resizeSection(5, 70)
        header.setSectionResizeMode(6, QHeaderView.Fixed)  # 평균가
        header.resizeSection(6, 150)
        header.setSectionResizeMode(7, QHeaderView.Fixed)  # 현재가
        header.resizeSection(7, 150)
        header.setSectionResizeMode(8, QHeaderView.Fixed)  # 수량
        header.resizeSection(8, 110)
        header.setSectionResizeMode(9, QHeaderView.Fixed)  # 평가손익
        header.resizeSection(9, 140)
        header.setSectionResizeMode(10, QHeaderView.Stretch)  # 수익률 - 남은 공간 채우기

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
        
        # 거래 내역 테이블 생성 (V4: 그룹 컬럼 추가)
        self.trade_history_table = QTableWidget()
        self.trade_history_table.setColumnCount(9)
        self.trade_history_table.setHorizontalHeaderLabels([
            "그룹", "시각", "심볼", "유형", "가격", "수량", "금액", "손익", "사유"
        ])
        
        # 테이블 스타일 설정
        self.trade_history_table.setFont(QFont("맑은 고딕", 10))  # 한글 가독성 개선
        self.trade_history_table.setAlternatingRowColors(True)
        self.trade_history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.trade_history_table.setSelectionBehavior(QTableWidget.SelectRows)

        # V4: 행 높이 설정 (가독성 개선)
        self.trade_history_table.verticalHeader().setDefaultSectionSize(32)  # 기본 행 높이 32px
        self.trade_history_table.verticalHeader().setMinimumSectionSize(28)  # 최소 행 높이 28px
        
        # 컬럼 너비 설정 (V4: 그룹 컬럼 추가, 고정 너비)
        trade_header = self.trade_history_table.horizontalHeader()
        trade_header.setDefaultSectionSize(100)  # 기본 컬럼 너비
        trade_header.setMinimumSectionSize(60)  # 최소 컬럼 너비
        trade_header.setSectionResizeMode(0, QHeaderView.Fixed)  # 그룹
        trade_header.resizeSection(0, 100)
        trade_header.setSectionResizeMode(1, QHeaderView.Fixed)  # 시각
        trade_header.resizeSection(1, 90)
        trade_header.setSectionResizeMode(2, QHeaderView.Fixed)  # 심볼
        trade_header.resizeSection(2, 80)
        trade_header.setSectionResizeMode(3, QHeaderView.Fixed)  # 유형
        trade_header.resizeSection(3, 130)
        trade_header.setSectionResizeMode(4, QHeaderView.Fixed)  # 가격
        trade_header.resizeSection(4, 120)
        trade_header.setSectionResizeMode(5, QHeaderView.Fixed)  # 수량
        trade_header.resizeSection(5, 110)
        trade_header.setSectionResizeMode(6, QHeaderView.Fixed)  # 금액
        trade_header.resizeSection(6, 110)
        trade_header.setSectionResizeMode(7, QHeaderView.Fixed)  # 손익
        trade_header.resizeSection(7, 130)
        trade_header.setSectionResizeMode(8, QHeaderView.Stretch)  # 사유 - 남은 공간 채우기
        
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

        # 스플리터 비율 설정 (좌측 280px : 우측 나머지)
        main_splitter.setStretchFactor(0, 0)  # 사이드바 고정
        main_splitter.setStretchFactor(1, 1)  # 메인 패널 확장
        main_splitter.setSizes([280, 1320])  # 초기 크기: 사이드바 280px, 메인 1320px (총 1600px)

        # 초기 로그 메시지
        self._add_log("🚀 Upbit DCA Trader V4 GUI 시작")
        self._add_log("📌 좌측 사이드바에서 설정을 확인하세요")
        self._add_log("ℹ️ 설정 메뉴(상단)에서 API 키와 Telegram을 설정하세요")

    def _create_dry_run_banner(self, parent_layout):
        """
        V4 Dry Run 배너 생성

        최상단에 고정되는 배너:
        - Dry Run 모드: 녹색 배경
        - 실거래 모드: 빨간색 배경
        """
        # 배너 프레임
        self.dry_run_banner = QWidget()
        self.dry_run_banner.setFixedHeight(45)
        banner_layout = QHBoxLayout(self.dry_run_banner)
        banner_layout.setContentsMargins(15, 5, 15, 5)

        # ConfigManager에서 dry_run 상태 읽기
        dry_run = self.config.get("dry_run", True)  # 기본값: True

        # 상태 텍스트
        self.dry_run_label = QLabel()
        self.dry_run_label.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        banner_layout.addWidget(self.dry_run_label)

        banner_layout.addStretch()

        # 전환 버튼
        self.dry_run_toggle_btn = QPushButton()
        self.dry_run_toggle_btn.setFont(QFont("맑은 고딕", 9))
        self.dry_run_toggle_btn.clicked.connect(self._toggle_dry_run_mode)
        banner_layout.addWidget(self.dry_run_toggle_btn)

        # 초기 표시 업데이트
        self._update_dry_run_banner()

        parent_layout.addWidget(self.dry_run_banner)

    def _update_dry_run_banner(self):
        """Dry Run 배너 상태 업데이트"""
        dry_run = self.config.get("dry_run", True)

        if dry_run:
            # Dry Run 모드 (녹색)
            self.dry_run_banner.setStyleSheet("background-color: #d4edda;")

            # 가상 잔고 표시
            virtual_balance = self.global_settings.get("virtual_initial_balance", 1000000)
            self.dry_run_label.setText(f"🟢 Dry Run 모드 (페이퍼 트레이딩) | 가상 초기 잔고: {virtual_balance:,}원")
            self.dry_run_label.setStyleSheet("color: #155724;")

            self.dry_run_toggle_btn.setText("⚠️ 실거래로 전환")
            self.dry_run_toggle_btn.setStyleSheet(
                "background-color: #ffc107; color: #000; "
                "padding: 5px 15px; border-radius: 3px; font-weight: bold;"
            )
        else:
            # 실거래 모드 (빨간색)
            self.dry_run_banner.setStyleSheet("background-color: #f8d7da;")

            # KRW 잔고 표시 (실제 잔고는 나중에 업데이트)
            self.dry_run_label.setText("🔴 실거래 모드 (실제 거래 실행 중) | KRW 잔고: 로딩 중...")
            self.dry_run_label.setStyleSheet("color: #721c24;")

            self.dry_run_toggle_btn.setText("ℹ️ Dry Run으로 전환")
            self.dry_run_toggle_btn.setStyleSheet(
                "background-color: #28a745; color: #fff; "
                "padding: 5px 15px; border-radius: 3px; font-weight: bold;"
            )

    def _toggle_dry_run_mode(self):
        """Dry Run 모드 전환"""
        current_dry_run = self.config.get("dry_run", True)

        if current_dry_run:
            # Dry Run → 실거래 전환 확인
            reply = QMessageBox.warning(
                self,
                "⚠️ 실거래 모드 전환",
                "실거래 모드로 전환하시겠습니까?\n\n"
                "실제 자금으로 거래가 실행됩니다!\n"
                "API 키와 설정을 다시 확인하세요.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                self.config["dry_run"] = False
                self.config_manager.save_config(self.config)
                self._update_dry_run_banner()
                self._add_log("🔴 실거래 모드로 전환되었습니다!")
        else:
            # 실거래 → Dry Run 전환 (안전하므로 바로 전환)
            self.config["dry_run"] = True
            self.config_manager.save_config(self.config)
            self._update_dry_run_banner()
            self._add_log("🟢 Dry Run 모드로 전환되었습니다.")

    def _create_position_summary_panel(self, parent_layout):
        """
        V4 포지션 요약 패널 생성

        형식: "포지션 요약: X개 그룹 | Y개 코인 | 평가손익: ±Z원"
        """
        # 포지션 요약 프레임
        self.position_summary_panel = QWidget()
        self.position_summary_panel.setFixedHeight(40)
        self.position_summary_panel.setStyleSheet("background-color: #f0f8ff; border-radius: 5px;")

        summary_layout = QHBoxLayout(self.position_summary_panel)
        summary_layout.setContentsMargins(15, 5, 15, 5)

        # 포지션 요약 라벨
        self.position_summary_label = QLabel("포지션 요약: 0개 그룹 | 0개 코인 | 평가손익: 0원")
        self.position_summary_label.setFont(QFont("맑은 고딕", 11, QFont.Bold))
        self.position_summary_label.setStyleSheet("color: #333;")
        summary_layout.addWidget(self.position_summary_label)

        summary_layout.addStretch()

        parent_layout.addWidget(self.position_summary_panel)

    def _update_position_summary_panel(self):
        """포지션 요약 패널 업데이트"""
        try:
            # V4 그룹 매니저에서 정보 가져오기
            all_groups = self.group_manager.get_all_groups()
            group_count = len(all_groups)

            # 모든 그룹의 코인 수집
            all_coins = set()
            for group_data in all_groups.values():
                all_coins.update(group_data.get("coins", []))

            coin_count = len(all_coins)

            # 평가손익 계산 (실제 포지션 데이터 필요 - 추후 구현)
            total_pnl = 0  # 임시값

            # 라벨 업데이트
            if total_pnl >= 0:
                pnl_text = f"+{total_pnl:,}원"
                pnl_color = "#d32f2f"  # 빨간색
            else:
                pnl_text = f"{total_pnl:,}원"
                pnl_color = "#1976d2"  # 파란색

            self.position_summary_label.setText(
                f"포지션 요약: {group_count}개 그룹 | {coin_count}개 코인 | 평가손익: {pnl_text}"
            )

            # 손익에 따라 라벨 색상 변경
            self.position_summary_label.setStyleSheet(f"color: {pnl_color}; font-weight: bold;")

        except Exception as e:
            logger.error(f"포지션 요약 패널 업데이트 실패: {e}")
            self.position_summary_label.setText("포지션 요약: 데이터 로드 실패")

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
            # V4: 그룹별 자동 매수 시스템
            self._add_log("💡 V4 그룹별 자동 매수 시스템 활성화")
        
        # 상태 업데이트
        self._update_status()
    
    def _open_auto_trading_config(self):
        """
        완전 자동 모드 설정 다이얼로그 열기

        DEPRECATED: V3 전용 메서드
        - V4에서는 그룹별 설정 사용으로 미사용
        - 대신 config/trading_config.json 직접 수정
        """
        self._add_log("⚠️ V4에서는 그룹별 설정을 사용합니다. config/trading_config.json을 직접 수정해주세요.")

        # from gui.auto_trading_config_dialog import AutoTradingConfigDialog
        #
        # dialog = AutoTradingConfigDialog(self.auto_trading_config, self)
        # if dialog.exec():
        #     # 설정이 변경되면 업데이트
        #     self.auto_trading_config = dialog.get_config()
        #     self.auto_trading_config.to_file('auto_trading_config.json')
        #     self._update_auto_config_display()
        #     self._add_log("✅ 완전 자동 설정이 업데이트되었습니다")

    def _open_group_management(self):
        """V4 그룹 관리 다이얼로그 열기"""
        from gui.group_management_dialog import GroupManagementDialog

        try:
            dialog = GroupManagementDialog(self.group_manager, self)
            if dialog.exec():
                # 그룹 변경 후 UI 업데이트
                self._add_log("✅ 그룹 설정이 업데이트되었습니다")

                # 사이드바 그룹 정보 업데이트
                selected_coin_count = len(self._get_all_coins_from_groups())
                groups = self.group_manager.get_all_groups()
                self.symbol_label.setText(f"총 {selected_coin_count}개 코인\n({len(groups)}개 그룹)")

                # 포지션 요약 패널 업데이트
                self._update_position_summary_panel()

        except Exception as e:
            self._add_log(f"❌ 그룹 관리 다이얼로그 오류: {e}")
            logger.error(f"그룹 관리 다이얼로그 오류: {e}", exc_info=True)

    def _refresh_account_info(self):
        """V4 계좌 정보 새로고침"""
        try:
            self._add_log("🔄 계좌 정보 새로고침 중...")

            # API 키 확인
            access_key = self.v3_config_manager.get_upbit_access_key()
            secret_key = self.v3_config_manager.get_upbit_secret_key()

            # API 키가 있으면 실제 잔고 조회
            if access_key and secret_key:
                # UpbitAPI 생성
                upbit_api = UpbitAPI(access_key, secret_key)

                # KRW 잔고 조회
                balances = upbit_api.get_balances()
                krw_balance = 0

                for balance in balances:
                    if balance['currency'] == 'KRW':
                        krw_balance = float(balance['balance'])
                        break

                # 총 자산 계산 (KRW + 코인 평가액)
                total_asset = krw_balance
                for balance in balances:
                    if balance['currency'] != 'KRW':
                        avg_buy_price = float(balance['avg_buy_price'])
                        amount = float(balance['balance'])
                        total_asset += avg_buy_price * amount

                # 초기 자산 대비 수익률 계산
                initial_balance = self.global_settings.get("virtual_initial_balance", 1000000)
                profit_rate = ((total_asset - initial_balance) / initial_balance) * 100

                # UI 업데이트
                self.total_asset_label.setText(f"총 자산: {total_asset:,.0f}원")

                if profit_rate >= 0:
                    self.profit_label.setText(f"수익률: +{profit_rate:.2f}%")
                    self.profit_label.setStyleSheet("color: #d32f2f; font-weight: bold;")
                else:
                    self.profit_label.setText(f"수익률: {profit_rate:.2f}%")
                    self.profit_label.setStyleSheet("color: #1976d2; font-weight: bold;")

                self._add_log(f"✅ 계좌 정보 새로고침 완료 (자산: {total_asset:,.0f}원, 수익률: {profit_rate:+.2f}%)")

            else:
                # API 키 미설정 또는 Dry Run 모드 - 가상 데이터 표시
                virtual_balance = self.global_settings.get("virtual_initial_balance", 1000000)
                self.total_asset_label.setText(f"총 자산: {virtual_balance:,.0f}원 (가상)")
                self.profit_label.setText("수익률: +0.00%")
                self._add_log("✅ API 키 미설정 또는 Dry Run 모드 - 가상 계좌 정보 표시")

        except Exception as e:
            self._add_log(f"❌ 계좌 정보 새로고침 실패: {e}")
            logger.error(f"계좌 정보 새로고침 실패: {e}", exc_info=True)
            QMessageBox.warning(self, "오류", f"계좌 정보를 새로고침할 수 없습니다:\n{str(e)}")

    def _open_global_settings(self):
        """V4 전역 설정 다이얼로그 열기"""
        # TODO: Phase 3-5에서 GlobalSettingsDialog 구현 예정

        try:
            self._add_log("⚙️ 전역 설정 다이얼로그 (구현 예정)")

            QMessageBox.information(
                self,
                "전역 설정",
                "전역 설정 다이얼로그는 Phase 3-5에서 구현 예정입니다.\n\n"
                "현재 설정:\n"
                f"- Dry Run: {self.config.get('dry_run', True)}\n"
                f"- 가상 초기 잔고: {self.global_settings.get('virtual_initial_balance', 1000000):,}원\n"
                f"- 일일 손실 제한: {self.global_settings.get('daily_loss', {}).get('enabled', False)}"
            )

        except Exception as e:
            self._add_log(f"❌ 전역 설정 오류: {e}")
            logger.error(f"전역 설정 오류: {e}", exc_info=True)

    def _update_auto_config_display(self):
        """완전 자동 설정 표시 업데이트"""
        # V3 전용 메서드 - V4에서는 그룹별 설정 사용으로 미사용
        pass

        # # 매수 금액
        # self.auto_buy_amount_label.setText(f"{self.auto_trading_config.buy_amount:,.0f}원")
        #
        # # 모니터링 코인
        # monitoring_text = f"상위 {self.auto_trading_config.top_n}개" if self.auto_trading_config.monitoring_mode == "top_marketcap" else f"{len(self.auto_trading_config.custom_symbols)}개"
        # self.auto_monitoring_label.setText(monitoring_text)
        #
        # # 스캔 주기
        # self.auto_scan_label.setText(f"{self.auto_trading_config.scan_interval}초")
        #
        # # 리스크 관리 요약
        # risk_items = []
        # if self.auto_trading_config.max_positions_enabled:
        #     risk_items.append(f"포지션 {self.auto_trading_config.max_positions_limit}개")
        # if self.auto_trading_config.daily_trades_enabled:
        #     risk_items.append(f"거래 {self.auto_trading_config.daily_trades_limit}회/일")
        # if self.auto_trading_config.min_krw_balance_enabled:
        #     risk_items.append(f"잔고 {self.auto_trading_config.min_krw_balance_amount:,.0f}원")
        # if self.auto_trading_config.stop_on_loss_enabled:
        #     risk_items.append(f"손실 {self.auto_trading_config.stop_on_loss_daily_pct}%")
        #
        # risk_text = ", ".join(risk_items) if risk_items else "없음"
        # self.auto_risk_label.setText(risk_text)

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
        # V4: 그룹에서 코인 리스트 가져오기
        selected_coins = self._get_all_coins_from_groups()

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
        # V4: 기본 금액 사용 (그룹별로 다를 수 있음)
        first_level_amount = 10000  # 기본값

        # 기본 시뮬레이션 가격: 1억원 (BTC 기준, 사용자가 시뮬레이터에서 변경 가능)
        default_price = 100000000

        dialog = DcaSimulatorDialog(
            self,
            initial_price=default_price,
            order_amount=first_level_amount
        )

        dialog.exec()
        self._add_log("💰 DCA 시뮬레이터 사용 완료")
    
    def _open_advanced_dca(self):
        """고급 DCA 설정 다이얼로그 열기"""
        # 고급 DCA 설정 다이얼로그 열기
        dialog = AdvancedDcaDialog(self)
        
        # 🔧 설정 변경 시그널 연결 (저장 버튼 누를 때마다 즉시 반영)
        dialog.config_changed.connect(self._on_dca_config_changed)
        
        # 다이얼로그 실행
        dialog.exec()
    
    def _on_dca_config_changed(self, config):
        """DCA 설정 변경 시그널 핸들러 (저장 시 자동 호출)"""
        # V3 전용 메서드 - V4에서는 그룹별 설정 사용으로 미사용
        pass

        # self._add_log("⚙️ 고급 DCA 설정이 저장되었습니다")
        #
        # # DCA 설정 업데이트
        # self.dca_config = config
        # self.stop_loss_pct = config.stop_loss_pct
        # self.take_profit_pct = config.take_profit_pct
        #
        # # 🔧 메인 화면의 읽기 전용 라벨들 자동 업데이트
        # # 익절 라벨 (다단계/단일 구분)
        # if config.is_multi_level_tp_enabled():
        #     tp_count = len(config.take_profit_levels)
        #     self.take_profit_label.setText(f"다단계 ({tp_count}레벨)")
        # else:
        #     self.take_profit_label.setText(f"+{config.take_profit_pct}%")
        #
        # # 손절 라벨 (다단계/단일 구분)
        # if config.is_multi_level_sl_enabled():
        #     sl_count = len(config.stop_loss_levels)
        #     self.stop_loss_label.setText(f"다단계 ({sl_count}레벨)")
        # else:
        #     self.stop_loss_label.setText(f"-{config.stop_loss_pct}%")
        #
        # # DCA 레벨 정보 업데이트
        # min_drop = min(level.drop_pct for level in config.levels)
        # max_drop = max(level.drop_pct for level in config.levels)
        # self.dca_levels_label.setText(f"{len(config.levels)}단계 ({min_drop}%~{max_drop}%)")
        #
        # # 총 투자금 업데이트
        # total_investment = sum(level.order_amount for level in config.levels)
        # self.total_investment_label.setText(f"{total_investment:,}원")
        #
        # # DCA 상태 업데이트
        # self.dca_status_label.setText("✅ 활성화" if config.enabled else "❌ 비활성화")
        # self.dca_status_label.setStyleSheet("color: #4CAF50;" if config.enabled else "color: #999;")
        #
        # # 로그 출력
        # self._add_log(f"  📊 DCA 레벨: {len(config.levels)}단계")
        #
        # # 익절 표시 (다단계/단일 구분)
        # if config.is_multi_level_tp_enabled():
        #     tp_count = len(config.take_profit_levels)
        #     self._add_log(f"  🎯 익절: 다단계 ({tp_count}레벨)")
        # else:
        #     self._add_log(f"  🎯 익절: +{config.take_profit_pct}%")
        #
        # # 손절 표시 (다단계/단일 구분)
        # if config.is_multi_level_sl_enabled():
        #     sl_count = len(config.stop_loss_levels)
        #     self._add_log(f"  🛑 손절: 다단계 ({sl_count}레벨)")
        # else:
        #     self._add_log(f"  🛑 손절: -{config.stop_loss_pct}%")
        #
        # self._add_log(f"  💰 총 투자금: {total_investment:,}원")
        #
        # # 레벨 정보 출력 (처음 3개)
        # for level_config in config.levels[:3]:
        #     self._add_log(f"     레벨 {level_config.level}: {level_config.drop_pct}% 하락 → {level_config.order_amount:,}원")
        # if len(config.levels) > 3:
        #     self._add_log(f"     ... 외 {len(config.levels) - 3}개 레벨")
        #
        # # 🔧 실행 중인 엔진에 DCA 설정 실시간 반영
        # if self.is_running and self.trading_worker:
        #     self._add_log("🔄 실행 중인 엔진에 DCA 설정 업데이트 전송...")
        #     self.trading_worker.update_dca_config(config)

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
        # V4: load_config()로 다시 로드
        self.config = self.config_manager.load_config()
        self.global_settings = self.config.get("global_settings", {})
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

        # 🔧 API 키 검증 (초기화 시 이미 검증되었으면 스킵)
        if self.api_keys_validated:
            self._add_log("✅ API 키 검증 완료 (초기화 시 확인됨)")
        else:
            self._add_log("🔑 API 키 검증 중...")
            self.statusbar.showMessage("API 키 검증 중...")

            if not self.v3_config_manager.validate_upbit_keys():
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
        if not self.v3_config_manager.validate_telegram_config():
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

            # ========================================
            # 🚀 V4 Trading Engine 시작
            # ========================================

            # V4 그룹 정보 로드
            groups = self.group_manager.get_all_groups()
            active_groups = [g for g in groups.values() if not g.get("observation_only", False)]

            self._add_log(f"📊 활성 그룹: {len(active_groups)}개 / 전체: {len(groups)}개")

            # 그룹별 코인 수 계산
            total_coins = sum(len(g.get("coins", [])) for g in active_groups)
            self._add_log(f"🎯 관리 코인: 총 {total_coins}개")

            # 전역 설정 표시
            if self.global_settings.get("observation_mode", False):
                self._add_log("⚠️ 관찰 전용 모드")

            if self.global_settings.get("dry_run", False):
                self._add_log("🧪 Dry-run 모드 (가상 거래)")
            else:
                self._add_log("💰 Live 모드 (실거래)")

            # Upbit API 인스턴스 생성
            upbit_api = UpbitAPI(
                access_key=self.v3_config_manager.get_upbit_access_key(),
                secret_key=self.v3_config_manager.get_upbit_secret_key()
            )

            # V4Worker 생성
            self._add_log("🔧 V4 거래 엔진 초기화 중...")
            self.trading_worker = V4Worker(
                config_path=self.config_path,
                upbit_api=upbit_api
            )

            # 시그널 연결 (V3 호환)
            self.trading_worker.started.connect(self._on_trading_started)
            self.trading_worker.finished.connect(self._on_trading_stopped)
            self.trading_worker.log_signal.connect(self._on_trading_log)
            self.trading_worker.error_signal.connect(self._on_trading_error)
            self.trading_worker.status_signal.connect(self._on_auto_trading_status)
            self.trading_worker.position_update_signal.connect(self._on_position_update)
            self.trading_worker.trade_signal.connect(self._on_trade_executed)

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
        if not self.v3_config_manager.validate_upbit_keys():
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

        # 🔧 최초 1회만 조회
        # self._add_log("🔄 계좌 정보 조회 중...")

        # 워커 스레드 생성 및 실행
        self.balance_worker = BalanceWorker(
            self.v3_config_manager.get_upbit_access_key(),
            self.v3_config_manager.get_upbit_secret_key()
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

        # UI 업데이트 (로그 출력 제거 - 잔고 갱신마다 반복되므로)
        self.total_asset_label.setText(f"총 자산: {krw_balance:,.0f}원")

    def _on_balance_error(self, error_msg: str):
        """잔고 조회 실패"""
        self._add_log(f"❌ 계좌 조회 실패: {error_msg}")
        QMessageBox.warning(
            self,
            "조회 실패",
            f"계좌 정보를 가져올 수 없습니다:\n{error_msg}"
        )

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
        거래 실행 시그널 처리 (V3/V4 호환)

        V3 Args:
            trade_data: 거래 정보 (단일 Trade 객체)
                - timestamp, symbol, trade_type, price, quantity, amount, profit, profit_pct, reason, order_id

        V4 Args:
            trade_data: 거래 내역 배치 (TradeHistoryManager 형식)
                - trades: 거래 리스트 (최신순)
                - total_count: 총 거래 수
                - timestamp: 업데이트 시각
        """
        try:
            # V4 데이터 형식 확인 (trades 키가 있으면 V4)
            if 'trades' in trade_data:
                # V4: 거래내역 전체를 교체
                self.trade_history = trade_data['trades']
                self._update_trade_history_table_v4()

                # 최신 거래만 로그 출력 (처음 1건)
                if self.trade_history:
                    latest_trade = self.trade_history[0]
                    self._log_v4_trade(latest_trade)
            else:
                # V3: 기존 로직 유지
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
                    self._add_log(f"{emoji} {symbol_short} {trade_type}: {format_price(trade.price)} × {trade.quantity:.8f} = {trade.amount:,.0f}원")

                    # 🔧 매수 발생 시 즉시 해당 코인 상태 조회하여 활성 포지션 테이블 업데이트
                    # (완전 자동 모드만 해당, 반자동 모드는 position_update_signal로 업데이트됨)
                    if self.trading_worker and hasattr(self.trading_worker, 'get_coin_status'):
                        coin_status = self.trading_worker.get_coin_status(trade.symbol)
                        if coin_status:
                            self._on_coin_update(trade.symbol, coin_status)
                else:
                    self._add_log(f"{emoji} {symbol_short} {trade_type}: {format_price(trade.price)} × {trade.quantity:.8f} = {trade.amount:,.0f}원 | 손익: {trade.profit:+,.0f}원 ({trade.profit_pct:+.2f}%)")

                    # 🔧 매도 발생 시에도 즉시 해당 코인 상태 조회하여 활성 포지션 테이블 업데이트
                    # (완전 자동 모드만 해당, 반자동 모드는 position_update_signal로 업데이트됨)
                    if self.trading_worker and hasattr(self.trading_worker, 'get_coin_status'):
                        coin_status = self.trading_worker.get_coin_status(trade.symbol)
                        if coin_status:
                            self._on_coin_update(trade.symbol, coin_status)

        except Exception as e:
            logger.error(f"거래 내역 업데이트 오류: {e}")
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
        개별 코인 상태 업데이트 처리 → 포지션 테이블 업데이트 (V3 레거시 - V4에서는 사용 안 함)

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
            # 🔧 V4 모드에서는 _on_position_update를 사용하므로 이 함수는 무시
            if hasattr(self, 'trading_worker') and self.trading_worker and hasattr(self.trading_worker, '__class__'):
                worker_class_name = self.trading_worker.__class__.__name__
                if worker_class_name == 'V4Worker':
                    # V4 모드에서는 _update_position_row_v4를 사용
                    return
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
                        # 🔧 매도 후 요약 정보 업데이트 (throttled - 500ms)
                        self._update_position_summary_throttled()
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
            entry_price_item = QTableWidgetItem(format_price(entry_price))
            entry_price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.position_table.setItem(row_index, 2, entry_price_item)

            # 현재가
            if current_price:
                current_price_item = QTableWidgetItem(format_price(current_price))
                current_price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.position_table.setItem(row_index, 3, current_price_item)
            else:
                self.position_table.setItem(row_index, 3, QTableWidgetItem("-"))

            # 수량
            qty_item = QTableWidgetItem(f"{position:.8f}")
            qty_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.position_table.setItem(row_index, 4, qty_item)

            # 매수금액 (진입가 × 수량)
            purchase_amount = entry_price * position
            purchase_amount_item = QTableWidgetItem(f"{purchase_amount:,.0f}원")
            purchase_amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            purchase_amount_item.setForeground(Qt.darkGray)  # 회색 (중립)
            self.position_table.setItem(row_index, 5, purchase_amount_item)

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
            self.position_table.setItem(row_index, 6, profit_loss_item)

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
            self.position_table.setItem(row_index, 7, return_pct_item)

            # 🔧 포지션 요약 정보 업데이트 (throttled - 500ms)
            self._update_position_summary_throttled()

        except Exception as e:
            self._add_log(f"⚠️ 코인 업데이트 오류 ({symbol}): {e}")

    def _update_position_summary_throttled(self):
        """
        포지션 요약 정보 업데이트 (throttled - 500ms)

        종목이 많을 때 GUI 응답없음을 방지하기 위해 500ms throttling 적용
        """
        now = time.time()

        # 500ms (0.5초) 이내에는 업데이트 건너뜀
        if now - self.last_summary_update < 0.5:
            return

        self.last_summary_update = now
        self._update_position_summary()

    def _update_position_summary(self):
        """
        포지션 요약 정보 업데이트

        테이블에 있는 모든 포지션의 평가손익과 수익률을 합산하여 표시
        """
        try:
            total_profit_loss = 0
            total_invested = 0  # 🔧 총 투자금액
            position_count = self.position_table.rowCount()

            # 테이블의 모든 행에서 평가손익 및 투자금액 합산
            for row in range(position_count):
                # 평가손익 추출
                profit_item = self.position_table.item(row, 6)  # 평가손익 컬럼 (5 → 6 매수금액 추가로 변경)
                if profit_item:
                    # "+1,500원" → 1500 변환
                    profit_text = profit_item.text().replace('원', '').replace(',', '').replace('+', '').replace(' ', '')
                    try:
                        profit_loss = float(profit_text)
                        total_profit_loss += profit_loss
                    except ValueError:
                        pass

                # 🔧 투자금액 계산 (진입가 × 수량)
                entry_price_item = self.position_table.item(row, 2)  # 진입가 컬럼
                quantity_item = self.position_table.item(row, 4)     # 수량 컬럼

                if entry_price_item and quantity_item:
                    try:
                        entry_price_text = entry_price_item.text().replace('원', '').replace(',', '').replace(' ', '')
                        quantity_text = quantity_item.text().replace(' ', '')

                        entry_price = float(entry_price_text)
                        quantity = float(quantity_text)
                        invested = entry_price * quantity
                        total_invested += invested
                    except ValueError:
                        pass

            # 🔧 수익률 계산
            return_pct = (total_profit_loss / total_invested * 100) if total_invested > 0 else 0

            # 요약 텍스트 생성
            if position_count > 0:
                # 🔧 수익률 추가 표시
                summary_text = f"총 {position_count}개 보유 중 | 전체 평가손익: {total_profit_loss:+,.0f}원 ({return_pct:+.2f}%)"

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
        트레이딩 상태 업데이트 처리 (반자동 + 완전 자동 모드 통합)

        Args:
            status: 트레이딩 상태

                [반자동 모드 - SemiAutoWorker]
                - total_value: 총 평가금액 (KRW)
                - total_return_pct: 총 수익률 (%)
                - managed_count: 관리 중인 포지션 수
                - positions: 포지션 리스트

                [완전 자동 모드 - AutoTradingWorker]
                - krw_balance: KRW 잔고
                - daily_pnl_pct: 오늘 손익률
                - monitoring_count: 모니터링 중인 코인 수
                - managed_positions: 관리 중인 포지션 수
                - daily_trades: 오늘 거래 횟수
        """
        try:
            # 🔧 반자동 모드 vs 완전 자동 모드 구분
            # 반자동: total_return_pct 존재
            # 완전 자동: daily_pnl_pct 존재

            if 'total_return_pct' in status:
                # ===== 반자동 모드 =====
                total_value = status.get('total_value', 0)
                return_pct = status.get('total_return_pct', 0)
                managed = status.get('managed_count', 0)

                # 총 자산 (평가금액) 표시
                self.total_asset_label.setText(f"포지션 평가액: {total_value:,.0f}원")

                # 수익률 표시
                if return_pct > 0:
                    self.profit_label.setText(f"수익률: +{return_pct:.2f}%")
                    self.profit_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
                elif return_pct < 0:
                    self.profit_label.setText(f"수익률: {return_pct:.2f}%")
                    self.profit_label.setStyleSheet("color: #f44336; font-weight: bold;")
                else:
                    self.profit_label.setText(f"수익률: {return_pct:.2f}%")
                    self.profit_label.setStyleSheet("color: gray;")

                # 최대 낙폭 (수익률이 마이너스면 표시)
                if return_pct < 0:
                    self.mdd_label.setText(f"최대 낙폭: {abs(return_pct):.2f}%")
                    self.mdd_label.setStyleSheet("color: #f44336;")
                else:
                    self.mdd_label.setText("최대 낙폭: 0.00%")
                    self.mdd_label.setStyleSheet("color: gray;")

                # 관리 중인 포지션 수 표시
                self.price_label.setText(f"관리 중: {managed}개 포지션")

            else:
                # ===== 완전 자동 모드 =====
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
            self._add_log(f"⚠️ 트레이딩 상태 업데이트 오류: {e}")

    def _on_position_update(self, position_data: dict):
        """
        V4 포지션 업데이트 처리 (V4Worker)

        Args:
            position_data: V4Worker가 보낸 포지션 정보
                - positions: Dict[symbol, position_dict] - 모든 포지션
                - total_count: int - 총 포지션 수
                - timestamp: float - 업데이트 시각
        """
        try:
            positions = position_data.get('positions', {})

            if not positions:
                # 포지션이 없으면 테이블 클리어
                self.position_table.setRowCount(0)
                return

            # 기존 테이블의 심볼 목록 수집
            existing_symbols = set()
            for row in range(self.position_table.rowCount()):
                symbol_item = self.position_table.item(row, 1)  # 컬럼 1: 심볼
                if symbol_item:
                    existing_symbols.add(symbol_item.text())

            # 각 포지션을 테이블에 업데이트
            for symbol, pos in positions.items():
                self._update_position_row_v4(symbol, pos, existing_symbols)

            # 더 이상 존재하지 않는 포지션 제거
            current_symbols = set(positions.keys())
            symbols_to_remove = existing_symbols - current_symbols

            for symbol in symbols_to_remove:
                for row in range(self.position_table.rowCount()):
                    symbol_item = self.position_table.item(row, 1)
                    if symbol_item and symbol_item.text() == symbol:
                        self.position_table.removeRow(row)
                        break

            # 포지션 요약 업데이트
            self._update_position_summary_v4(positions)

        except KeyboardInterrupt:
            pass
        except Exception as e:
            logger.error(f"❌ [GUI] V4 포지션 업데이트 오류: {e}", exc_info=True)
            self._add_log(f"⚠️ V4 포지션 업데이트 오류: {e}")

    def _update_position_row_v4(self, symbol: str, pos: dict, existing_symbols: set):
        """
        V4 포지션 한 행 업데이트

        Args:
            symbol: 심볼 (예: "KRW-BTC")
            pos: 포지션 데이터
            existing_symbols: 기존 테이블에 있는 심볼들
        """
        # 심볼 단축 표기 (KRW- 제거)
        symbol_short = symbol.replace("KRW-", "")

        # 기존 행 찾기
        row_index = -1
        for row in range(self.position_table.rowCount()):
            item = self.position_table.item(row, 1)  # 컬럼 1: 심볼
            if item and item.text() == symbol_short:
                row_index = row
                break

        # 행이 없으면 새로 추가
        if row_index == -1:
            row_index = self.position_table.rowCount()
            self.position_table.insertRow(row_index)

        # 데이터 추출
        group_id = pos.get('group_id', '-')
        average_price = pos.get('average_price', 0)
        current_price = pos.get('current_price', 0)
        total_amount = pos.get('total_amount', 0)
        profit_krw = pos.get('profit_krw', 0)
        profit_pct = pos.get('profit_pct', 0)
        dca_count = pos.get('dca_count', 0)

        # 가격 포맷 함수
        def format_price(price):
            if price >= 1000:
                return f"{price:,.0f}"
            elif price >= 1:
                return f"{price:,.2f}"
            else:
                return f"{price:.8f}"

        # 0: 그룹
        group_item = QTableWidgetItem(group_id)
        group_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        self.position_table.setItem(row_index, 0, group_item)

        # 1: 심볼
        symbol_item = QTableWidgetItem(symbol_short)
        symbol_item.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        symbol_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        self.position_table.setItem(row_index, 1, symbol_item)

        # 2: 매수 (초기 매수 상태 - 일단 "✓"로 표시)
        buy_item = QTableWidgetItem("✓")
        buy_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        buy_item.setForeground(Qt.darkGreen)
        self.position_table.setItem(row_index, 2, buy_item)

        # 3: DCA (DCA 횟수)
        dca_item = QTableWidgetItem(str(dca_count) if dca_count > 0 else "-")
        dca_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        if dca_count > 0:
            dca_item.setForeground(Qt.darkBlue)
        self.position_table.setItem(row_index, 3, dca_item)

        # 4: 익절 (레벨 정보 - 그룹 설정에서 가져오기)
        tp_display, tp_reached = self._get_profit_level_display(group_id, profit_pct)
        tp_item = QTableWidgetItem(tp_display)
        tp_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        if tp_reached > 0:
            tp_item.setForeground(Qt.darkGreen)
            tp_item.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        self.position_table.setItem(row_index, 4, tp_item)

        # 5: 손절 (레벨 정보 - 그룹 설정에서 가져오기)
        sl_display, sl_reached = self._get_loss_level_display(group_id, profit_pct)
        sl_item = QTableWidgetItem(sl_display)
        sl_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        if sl_reached > 0:
            sl_item.setForeground(Qt.red)
            sl_item.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        self.position_table.setItem(row_index, 5, sl_item)

        # 6: 평균가
        avg_price_item = QTableWidgetItem(format_price(average_price))
        avg_price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.position_table.setItem(row_index, 6, avg_price_item)

        # 7: 현재가
        curr_price_item = QTableWidgetItem(format_price(current_price))
        curr_price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.position_table.setItem(row_index, 7, curr_price_item)

        # 8: 수량
        amount_item = QTableWidgetItem(f"{total_amount:.8f}")
        amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.position_table.setItem(row_index, 8, amount_item)

        # 9: 평가손익
        profit_item = QTableWidgetItem(f"{profit_krw:+,.0f}원")
        profit_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        if profit_krw > 0:
            profit_item.setForeground(Qt.red)  # 빨강 (수익)
            profit_item.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        elif profit_krw < 0:
            profit_item.setForeground(Qt.blue)  # 파랑 (손실)
            profit_item.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        else:
            profit_item.setForeground(Qt.black)
        self.position_table.setItem(row_index, 9, profit_item)

        # 10: 수익률
        pct_item = QTableWidgetItem(f"{profit_pct:+.2f}%")
        pct_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        if profit_pct > 0:
            pct_item.setForeground(Qt.red)  # 빨강 (수익)
            pct_item.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        elif profit_pct < 0:
            pct_item.setForeground(Qt.blue)  # 파랑 (손실)
            pct_item.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        else:
            pct_item.setForeground(Qt.black)
        self.position_table.setItem(row_index, 10, pct_item)

    def _update_position_summary_v4(self, positions: dict):
        """
        V4 포지션 요약 정보 업데이트

        Args:
            positions: Dict[symbol, position_dict]
        """
        try:
            # 총 포지션 수
            total_positions = len(positions)

            # 총 투자금액, 총 평가금액, 총 손익 계산
            total_invested = sum(pos.get('total_invested_krw', 0) for pos in positions.values())
            total_value = sum(pos.get('current_value_krw', 0) for pos in positions.values())
            total_profit = sum(pos.get('profit_krw', 0) for pos in positions.values())

            # 총 수익률
            total_profit_pct = (total_profit / total_invested * 100) if total_invested > 0 else 0

            # 상단 배너 업데이트
            # 포지션 요약 레이블 (좌측에 있는 것)
            if hasattr(self, 'position_summary_label'):
                self.position_summary_label.setText(
                    f"보유 종목: {total_positions}개  |  "
                    f"총 투자금액: {total_invested:,.0f}원  |  "
                    f"총 평가금액: {total_value:,.0f}원  |  "
                    f"평가손익: {total_profit:+,.0f}원 ({total_profit_pct:+.2f}%)"
                )

                # 수익/손실에 따라 색상 변경
                if total_profit > 0:
                    self.position_summary_label.setStyleSheet(
                        "background-color: rgba(76, 175, 80, 0.1); "
                        "color: #2E7D32; "
                        "padding: 8px; "
                        "border-radius: 4px; "
                        "font-weight: bold;"
                    )
                elif total_profit < 0:
                    self.position_summary_label.setStyleSheet(
                        "background-color: rgba(244, 67, 54, 0.1); "
                        "color: #C62828; "
                        "padding: 8px; "
                        "border-radius: 4px; "
                        "font-weight: bold;"
                    )
                else:
                    self.position_summary_label.setStyleSheet(
                        "background-color: rgba(128, 128, 128, 0.1); "
                        "color: #555; "
                        "padding: 8px; "
                        "border-radius: 4px;"
                    )

        except Exception as e:
            logger.error(f"V4 포지션 요약 업데이트 오류: {e}")

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
        # V4: 그룹의 코인 개수로 업데이트
        selected_coin_count = len(self._get_all_coins_from_groups())
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

    def _update_trade_history_table_v4(self):
        """
        거래 내역 테이블 업데이트 (V4)

        TradeHistoryManager의 거래 데이터를 테이블에 표시
        - 9개 컬럼: 그룹, 시각, 심볼, 유형, 가격, 수량, 금액, 손익, 사유
        """
        try:
            # 정렬 비활성화 (업데이트 중)
            self.trade_history_table.setSortingEnabled(False)

            # 테이블 초기화
            self.trade_history_table.setRowCount(len(self.trade_history))

            # 거래 내역 통계 계산
            total_trades = len(self.trade_history)
            buy_count = sum(1 for t in self.trade_history if t.get('action') == 'buy')
            sell_count = sum(1 for t in self.trade_history if t.get('action') == 'sell')

            # 누적 손익 계산 (매도 거래의 손익 합계)
            # V4에서는 매도 시 total_krw가 실제 판매 금액이므로, 손익은 (판매금액 - 매수금액)으로 계산해야 함
            # 하지만 TradeHistoryManager에 손익 정보가 없으므로, 나중에 추가 필요
            # 임시로 0으로 설정
            total_profit = 0.0
            total_profit_pct = 0.0

            # 요약 정보 업데이트
            self.trade_summary_label.setText(
                f"총 {total_trades}건 | 매수: {buy_count}건, 매도: {sell_count}건 | "
                f"누적 손익: {total_profit:+,.0f}원 ({total_profit_pct:+.2f}%)"
            )

            # 색상 변경
            if total_profit > 0:
                self.trade_summary_label.setStyleSheet(
                    "color: #4CAF50; padding: 5px; background-color: #f5f5f5; border-radius: 3px; font-weight: bold;"
                )
            elif total_profit < 0:
                self.trade_summary_label.setStyleSheet(
                    "color: #f44336; padding: 5px; background-color: #f5f5f5; border-radius: 3px; font-weight: bold;"
                )
            else:
                self.trade_summary_label.setStyleSheet(
                    "color: #666; padding: 5px; background-color: #f5f5f5; border-radius: 3px;"
                )

            # 각 거래 내역 추가
            for row, trade in enumerate(self.trade_history):
                # 0: 그룹
                group_name = trade.get('group_name', trade.get('group_id', '-'))
                group_item = QTableWidgetItem(group_name)
                group_item.setTextAlignment(Qt.AlignCenter)
                self.trade_history_table.setItem(row, 0, group_item)

                # 1: 시각
                timestamp_str = trade.get('timestamp', '')
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(timestamp_str)
                    time_str = dt.strftime("%m-%d %H:%M")
                except:
                    time_str = timestamp_str[:16] if len(timestamp_str) >= 16 else timestamp_str
                time_item = QTableWidgetItem(time_str)
                time_item.setTextAlignment(Qt.AlignCenter)
                self.trade_history_table.setItem(row, 1, time_item)

                # 2: 심볼
                symbol = trade.get('symbol', '')
                symbol_short = symbol.replace('KRW-', '')
                symbol_item = QTableWidgetItem(symbol_short)
                symbol_item.setFont(QFont("Consolas", 9, QFont.Bold))
                symbol_item.setTextAlignment(Qt.AlignCenter)
                self.trade_history_table.setItem(row, 2, symbol_item)

                # 3: 유형 (매수/매도)
                action = trade.get('action', '')
                trade_type = trade.get('type', '')

                # 이모지 매핑
                emoji_map = {
                    'buy': '🔴',
                    'sell': '🔵'
                }
                type_text_map = {
                    'buy': '매수',
                    'sell': '매도'
                }
                emoji = emoji_map.get(action, '⚪')
                type_text = type_text_map.get(action, action)

                # 거래 타입 표시 (initial, dca, profit, loss, manual)
                type_detail_map = {
                    'initial': '첫매수',
                    'dca': '추가매수',
                    'profit': '익절',
                    'loss': '손절',
                    'manual': '수동'
                }
                type_detail = type_detail_map.get(trade_type, '')

                if type_detail:
                    type_display = f"{emoji} {type_text} ({type_detail})"
                else:
                    type_display = f"{emoji} {type_text}"

                type_item = QTableWidgetItem(type_display)
                type_item.setTextAlignment(Qt.AlignCenter)
                if action == 'buy':
                    type_item.setForeground(Qt.red)
                else:
                    type_item.setForeground(Qt.blue)
                self.trade_history_table.setItem(row, 3, type_item)

                # 4: 가격
                price = trade.get('price', 0)
                price_item = QTableWidgetItem(f"{price:,.0f}")
                price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.trade_history_table.setItem(row, 4, price_item)

                # 5: 수량
                amount = trade.get('amount', 0)
                qty_item = QTableWidgetItem(f"{amount:.8f}")
                qty_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.trade_history_table.setItem(row, 5, qty_item)

                # 6: 금액 (total_krw)
                total_krw = trade.get('total_krw', 0)
                amount_item = QTableWidgetItem(f"{total_krw:,.0f}")
                amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.trade_history_table.setItem(row, 6, amount_item)

                # 7: 손익 (매도 시만 표시, 향후 구현)
                # TODO: PositionManager에서 손익 정보를 TradeHistoryManager에 전달하도록 수정 필요
                profit_item = QTableWidgetItem("-")
                profit_item.setTextAlignment(Qt.AlignCenter)
                self.trade_history_table.setItem(row, 7, profit_item)

                # 8: 사유 (notes 필드)
                notes = trade.get('notes', trade.get('strategy_signal', '-'))
                reason_item = QTableWidgetItem(notes)
                reason_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                self.trade_history_table.setItem(row, 8, reason_item)

            # 정렬 다시 활성화
            self.trade_history_table.setSortingEnabled(True)

        except Exception as e:
            logger.error(f"V4 거래 내역 테이블 업데이트 오류: {e}")
            self._add_log(f"⚠️ V4 거래 내역 테이블 업데이트 오류: {e}")

    def _log_v4_trade(self, trade: dict):
        """
        V4 거래 로그 출력

        Args:
            trade: TradeHistoryManager의 거래 딕셔너리
        """
        try:
            action = trade.get('action', '')
            trade_type = trade.get('type', '')
            symbol = trade.get('symbol', '').replace('KRW-', '')
            price = trade.get('price', 0)
            amount = trade.get('amount', 0)
            total_krw = trade.get('total_krw', 0)

            # 이모지 및 텍스트
            emoji_map = {'buy': '🔴', 'sell': '🔵'}
            type_text_map = {'buy': '매수', 'sell': '매도'}
            type_detail_map = {
                'initial': '첫매수',
                'dca': '추가매수',
                'profit': '익절',
                'loss': '손절',
                'manual': '수동'
            }

            emoji = emoji_map.get(action, '⚪')
            type_text = type_text_map.get(action, action)
            type_detail = type_detail_map.get(trade_type, '')

            if type_detail:
                display_type = f"{type_text}({type_detail})"
            else:
                display_type = type_text

            # 로그 출력
            self._add_log(
                f"{emoji} {symbol} {display_type}: "
                f"{format_price(price)} × {amount:.8f} = {total_krw:,.0f}원"
            )

        except Exception as e:
            logger.error(f"V4 거래 로그 출력 오류: {e}")

    def _get_profit_level_display(self, group_id: str, current_profit_pct: float):
        """
        익절 레벨 표시 문자열 생성

        Args:
            group_id: 그룹 ID
            current_profit_pct: 현재 수익률 (%)

        Returns:
            tuple: (표시 문자열, 도달한 레벨 수)
                - 예: ("1/2", 1) - 2개 레벨 중 1개 도달
                - 예: ("0/3", 0) - 3개 레벨 중 0개 도달
                - 예: ("-", 0) - 레벨 없음
        """
        try:
            # V4Worker에서 config를 직접 로드
            from core.config_manager import ConfigManager

            config_mgr = ConfigManager()
            config = config_mgr.load_config()

            if 'groups' not in config or group_id not in config['groups']:
                return ("-", 0)

            group_data = config['groups'][group_id]
            profit_settings = group_data.get('profit_settings', {})
            levels = profit_settings.get('levels', [])

            if not levels:
                return ("-", 0)

            # 현재 수익률이 넘은 레벨 수 계산
            reached_count = 0
            for level in levels:
                if current_profit_pct >= level.get('price_ratio', 0):
                    reached_count += 1

            return (f"{reached_count}/{len(levels)}", reached_count)

        except Exception as e:
            logger.error(f"익절 레벨 표시 오류: {e}")
            return ("-", 0)

    def _get_loss_level_display(self, group_id: str, current_profit_pct: float):
        """
        손절 레벨 표시 문자열 생성

        Args:
            group_id: 그룹 ID
            current_profit_pct: 현재 수익률 (%)

        Returns:
            tuple: (표시 문자열, 도달한 레벨 수)
                - 예: ("0/1", 0) - 1개 레벨 중 0개 도달
                - 예: ("1/1", 1) - 1개 레벨 중 1개 도달 (손절 발동!)
                - 예: ("-", 0) - 레벨 없음
        """
        try:
            # V4Worker에서 config를 직접 로드
            from core.config_manager import ConfigManager

            config_mgr = ConfigManager()
            config = config_mgr.load_config()

            if 'groups' not in config or group_id not in config['groups']:
                return ("-", 0)

            group_data = config['groups'][group_id]
            loss_settings = group_data.get('loss_settings', {})
            levels = loss_settings.get('levels', [])

            if not levels:
                return ("-", 0)

            # 현재 수익률이 손절 기준 아래로 떨어진 레벨 수 계산
            reached_count = 0
            for level in levels:
                if current_profit_pct <= level.get('price_ratio', 0):
                    reached_count += 1

            return (f"{reached_count}/{len(levels)}", reached_count)

        except Exception as e:
            logger.error(f"손절 레벨 표시 오류: {e}")
            return ("-", 0)

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
    # 순차적 초기화 시스템
    # ========================================

    def _start_sequential_initialization(self):
        """순차적 초기화 시작 (단계별 진행)"""
        import logging
        logger = logging.getLogger(__name__)

        logger.info("🚀 [Init] 순차적 초기화 시작")
        self._add_log("🔄 초기화 시작... (1/3) 예수금 조회")

        # 단계 1: 예수금 조회
        self._step1_load_balance()

    def _step1_load_balance(self):
        """단계 1: 예수금 조회"""
        import logging
        logger = logging.getLogger(__name__)

        logger.info("🔄 [Step 1] 예수금 조회 시작")

        # 🔧 Step 3와 동일한 방식으로 API 키 가져오기
        access_key = self.v3_config_manager.get_upbit_access_key()
        secret_key = self.v3_config_manager.get_upbit_secret_key()

        if not access_key or not secret_key:
            logger.warning("⚠️ [Step 1] API 키 미설정 - 단계 2로 진행")
            self._add_log("⚠️ API 키 미설정 - 단계 2로 진행")
            self._step2_load_positions()
            return

        # BalanceWorker 시작
        logger.info("🔧 [Step 1] BalanceWorker 시작")
        self.balance_worker = BalanceWorker(access_key, secret_key)
        self.balance_worker.finished.connect(self._on_step1_complete)
        self.balance_worker.error.connect(self._on_step1_error)
        self.balance_worker.start()

    def _on_step1_complete(self, result: dict):
        """단계 1 완료: 예수금 표시 → 단계 2로"""
        import logging
        logger = logging.getLogger(__name__)

        if result['success']:
            krw = result['krw']
            logger.info(f"✅ [Step 1] 예수금 조회 완료: {krw:,.0f}원")
            self._add_log(f"✅ 예수금 조회 완료: {krw:,.0f}원")
            # balance_label은 GUI에 없으므로 로그로만 표시

            # 🔧 API 키 검증 완료 플래그 설정
            self.api_keys_validated = True
            logger.info("✅ [Step 1] API 키 검증 완료 (플래그 설정)")

        # 단계 2로 진행
        logger.info("🔄 [Step 1] 완료 → 단계 2로 진행")
        self._step2_load_positions()

    def _on_step1_error(self, error_msg: str):
        """단계 1 실패: 에러 표시 → 단계 2로 계속"""
        import logging
        logger = logging.getLogger(__name__)

        logger.error(f"❌ [Step 1] 예수금 조회 실패: {error_msg}")
        self._add_log(f"⚠️ 예수금 조회 실패: {error_msg}")
        self._step2_load_positions()

    def _step2_load_positions(self):
        """단계 2: 보유 종목 조회 + 화면 표시"""
        import logging
        logger = logging.getLogger(__name__)

        logger.info("🔄 [Step 2] 보유 종목 조회 시작")
        self._add_log("🔄 초기화 중... (2/3) 보유 종목 조회")

        # 🔧 Step 3와 동일한 방식으로 API 키 가져오기
        access_key = self.v3_config_manager.get_upbit_access_key()
        secret_key = self.v3_config_manager.get_upbit_secret_key()

        if not access_key or not secret_key:
            logger.warning("⚠️ [Step 2] API 키 미설정 - 단계 3으로 진행")
            self._add_log("⚠️ API 키 미설정 - 단계 3으로 진행")
            self._step3_prepare_myasset()
            return

        try:
            from core.upbit_api import UpbitAPI
            from datetime import datetime

            logger.info("🔍 [Step 2] UpbitAPI 초기화 및 계좌 조회 중...")
            api = UpbitAPI(access_key, secret_key)
            accounts = api.get_accounts()
            logger.info(f"✅ [Step 2] 계좌 조회 완료: {len(accounts)}개 자산")

            # 🔧 코인 포지션 수집 및 GUI 업데이트
            positions_found = []
            for account in accounts:
                currency = account['currency']
                if currency != 'KRW':
                    balance = float(account['balance'])
                    avg_buy_price = float(account['avg_buy_price'])

                    if balance > 0:
                        symbol = f'KRW-{currency}'
                        logger.info(f"💰 [Step 2] 포지션 발견: {symbol}, 수량={balance}, 평단가={avg_buy_price}")

                        # ✅ GUI 업데이트 (각 포지션마다 _on_coin_update 호출)
                        position_data = {
                            'symbol': symbol,
                            'position': balance,
                            'entry_price': avg_buy_price,
                            'avg_entry_price': avg_buy_price,
                            'current_price': avg_buy_price,  # 최초에는 진입가로 표시
                            'profit_loss': 0,
                            'return_pct': 0,
                            'entry_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }

                        # GUI 테이블 업데이트
                        logger.info(f"🔧 [Step 2] _on_coin_update 호출: {symbol}")
                        self._on_coin_update(symbol, position_data)
                        logger.info(f"✅ [Step 2] _on_coin_update 완료: {symbol}")
                        positions_found.append(currency)

            if positions_found:
                logger.info(f"✅ [Step 2] 보유 종목 {len(positions_found)}개 발견: {', '.join(positions_found)}")
                logger.info(f"✅ [Step 2] 활성 포지션 테이블에 표시 완료")
                self._add_log(f"✅ 보유 종목 {len(positions_found)}개 발견: {', '.join(positions_found)}")
                self._add_log(f"   → 활성 포지션 테이블에 표시 완료")
            else:
                logger.info("📭 [Step 2] 보유 종목 없음")
                self._add_log("📭 보유 종목 없음")

        except Exception as e:
            import traceback
            logger.error(f"❌ [Step 2] 보유 종목 조회 실패: {e}")
            logger.error(f"❌ [Step 2] Traceback:\n{traceback.format_exc()}")
            self._add_log(f"⚠️ 보유 종목 조회 실패: {e}")

        # 단계 3으로 진행
        logger.info("🔄 [Step 2] 완료 → 단계 3으로 진행")
        self._step3_prepare_myasset()

    def _step3_prepare_myasset(self):
        """단계 3: MyAsset WebSocket 구독 준비"""
        import logging
        logger = logging.getLogger(__name__)

        logger.info("🔄 [Step 3] 실시간 감지 준비 시작")
        self._add_log("🔄 초기화 중... (3/3) 실시간 감지 준비")

        # 기존 _start_myasset_preparation() 로직 호출
        self._start_myasset_preparation()

    # ========================================
    # MyAsset 구독 준비
    # ========================================

    def _start_myasset_preparation(self):
        """MyAsset WebSocket 구독 준비 시작 (백그라운드)"""
        # API 키 확인
        access_key = self.v3_config_manager.get_upbit_access_key()
        secret_key = self.v3_config_manager.get_upbit_secret_key()

        if not access_key or not secret_key:
            # API 키 없으면 준비 실패
            self._add_log("⚠️ API 키 미설정 (Fallback 모드)")
            self.start_btn.setEnabled(True)  # 버튼은 활성화 (fallback 모드로 작동)
            return

        # MyAsset 구독 준비 워커 시작
        self.preparation_worker = MyAssetPreparationWorker(access_key, secret_key)
        self.preparation_worker.preparation_complete.connect(self._on_myasset_preparation_complete)
        self.preparation_worker.preparation_failed.connect(self._on_myasset_preparation_failed)
        self.preparation_worker.status_update.connect(self._on_myasset_status_update)
        self.preparation_worker.start()

    def _on_myasset_preparation_complete(self):
        """MyAsset 구독 준비 완료"""
        self.myasset_ready = True
        self.start_btn.setEnabled(True)  # 시작 버튼 활성화
        self._add_log("✅ 실시간 감지 준비 완료! 이제 시작 버튼을 눌러주세요.")
        self._add_log("ℹ️  참고: 프로그램 시작 직후 첫 매수는 1-3분 지연될 수 있습니다 (Upbit 정책)")
        self._add_log("   이후 매수부터는 즉시 감지됩니다 (평균 15-30초 이내)")

    def _on_myasset_preparation_failed(self, error_msg: str):
        """MyAsset 구독 준비 실패"""
        self.myasset_ready = False
        self.start_btn.setEnabled(True)  # 버튼은 활성화 (fallback 모드로 작동)
        self._add_log(f"⚠️ 실시간 감지 준비 실패: {error_msg}")
        self._add_log("   → Fallback polling 모드로 작동합니다 (60초마다 확인)")

    def _on_myasset_status_update(self, status_msg: str):
        """MyAsset 상태 업데이트"""
        self._add_log(status_msg)

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

            # 🔧 V4 Trading Engine 중지
            if self.trading_worker:
                self._add_log("⏸️ V4 Trading Engine 중지 중...")
                self.trading_worker.stop()

                # 스레드 종료 대기 (최대 5초로 단축)
                if not self.trading_worker.wait(5000):
                    self._add_log("⚠️ 엔진 중지 시간 초과, 강제 종료")
                    if self.trading_worker:  # None 체크
                        self.trading_worker.terminate()
                        if self.trading_worker:  # terminate 후 다시 체크
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
