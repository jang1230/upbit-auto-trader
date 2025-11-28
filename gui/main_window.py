"""
Main Window - 메인 화면
Upbit DCA Trader GUI 메인 윈도우
"""

import sys
import os
import time
import logging
import threading
import uuid
from datetime import datetime

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
    QRadioButton, QButtonGroup,  # 트레이딩 모드 선택용
    QDialog  # Step 6: Global Settings Dialog용
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QAction, QFont, QColor, QTextCursor
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
from gui.group_management_dialog import GroupManagementDialog  # 🔧 V4 그룹 관리 다이얼로그
from gui.logging_handler import GuiLogHandler  # 🔧 백엔드 로그 필터링 핸들러
from core.utils import format_price  # 🔧 가격 포맷팅 유틸리티

# 🔧 V4 매니저 import
try:
    from core.config_manager import ConfigManager as V4ConfigManager
    from core.group_manager import GroupManager
    from core.position_manager import PositionManager
    from core.v4_trading_engine import V4TradingEngine
    V4_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ V4 모듈을 불러올 수 없습니다. V4 기능이 비활성화됩니다.")
    V4_AVAILABLE = False


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

            # 성공 시그널 발생 (accounts 데이터 포함하여 Step 2에서 재사용)
            self.finished.emit({
                'success': True,
                'krw': krw_balance,
                'btc': btc_balance,
                'accounts': accounts  # Step 2에서 재사용할 데이터
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

    # 🔧 스레드 안전한 GUI 업데이트용 Signal
    position_refresh_signal = Signal(str)  # 포지션 새로고침 (symbol)

    def __init__(self):
        super().__init__()

        self.config_manager = ConfigManager()
        self.dca_config_manager = DcaConfigManager()  # 고급 DCA 설정 관리자
        self.dca_config = self.dca_config_manager.load()  # DCA 설정 로드

        # 🔧 Upbit API 초기화 (나중에 Step 1에서 설정)
        self.upbit_api = None
        self.initial_accounts = None  # Step 1에서 받은 accounts 데이터 (Step 2에서 재사용)

        # 🔧 V4 매니저 초기화 (config 기반 모드 결정)
        if V4_AVAILABLE:
            # V4 설정 로드하여 모드 확인
            from core.config_manager import ConfigManager as V4ConfigManager
            v4_config_mgr = V4ConfigManager("config/trading_config.json")
            try:
                v4_config = v4_config_mgr.load_config()
                mode = "dryrun" if v4_config.get("global_settings", {}).get("dry_run", True) else "live"
            except:
                mode = "dryrun"  # 설정 로드 실패 시 기본값

            # GroupManager가 내부에서 ConfigManager와 PositionManager를 생성
            self.v4_group_manager = GroupManager(
                config_path="config/trading_config.json",
                mode=mode
            )
            # GroupManager 내부의 매니저 참조
            self.v4_config_manager = self.v4_group_manager.config_manager
            self.v4_position_manager = self.v4_group_manager.position_manager
        else:
            self.v4_config_manager = None
            self.v4_position_manager = None
            self.v4_group_manager = None

        # 🔧 트레이딩 모드 및 완전 자동 설정
        self.trading_mode = "semi_auto"  # "semi_auto" | "full_auto"
        self.auto_trading_config = AutoTradingConfig.from_file('auto_trading_config.json')  # 완전 자동 설정
        self.scan_interval = 60  # 🔧 반자동 모드 fallback 스캔 주기 (초, MyAsset WebSocket 보조용)
        
        self.is_running = False
        self.balance_worker = None  # 잔고 조회 워커 스레드
        self.trading_worker = None  # Trading Engine 워커 스레드
        self.preparation_worker = None  # MyAsset 구독 준비 워커
        self.price_websocket_worker = None  # 🔧 V4: 가격 WebSocket 워커
        self.myasset_websocket_worker = None  # 🔧 V4: MyAsset WebSocket 워커 (잔고 실시간 감지)
        self.myasset_ready = False  # MyAsset 구독 준비 완료 여부
        self.api_keys_validated = False  # 🔧 API 키 검증 완료 플래그 (Step 1 성공 시 True)
        self._shutdown_timer = None  # 비동기 종료 타이머
        self._shutdown_elapsed = 0  # 종료 대기 시간

        # 🔧 V4: Trading Engine 인스턴스
        self.v4_engine = None  # V4TradingEngine 인스턴스

        # 🔧 V4: 실시간 가격 업데이트 타이머 (V4 WebSocket에서 읽어옴)
        self.price_update_timer = None

        # 🔧 GUI 업데이트 throttling
        self.last_summary_update = 0  # 포지션 요약 마지막 업데이트 시간

        # 🔧 세션 거래 내역 저장 (프로그램 재시작 시 리셋됨, 파일 저장 안 함)
        self.session_trades = []  # Trade 객체 리스트 (세션 한정)

        # 🔧 자동 매도 중복 알림 방지 (즉시매도 + 익절 + 손절)
        self.recent_immediate_sells = {}  # {symbol: timestamp} - 봇이 자동으로 매도한 코인 추적 (10초간 수동매도 알림 차단)

        # 리스크 관리 파라미터 (고급 DCA 설정에서 관리)
        # 🔧 모든 DCA 관련 설정은 self.dca_config에서 가져옴
        self.stop_loss_pct = self.dca_config.stop_loss_pct
        self.take_profit_pct = self.dca_config.take_profit_pct
        self.max_daily_loss_pct = 10.0  # 일일 최대 손실은 별도 관리

        self.setWindowTitle("Upbit DCA Trader V4")
        self.setMinimumSize(1600, 850)  # V4: 그룹 시스템으로 화면 확대

        # 🔧 스레드 안전한 Signal 연결 (백그라운드 → GUI)
        self.position_refresh_signal.connect(self._on_position_refresh_requested)

        self._init_ui()
        self._init_menu()
        self._init_statusbar()
        self._update_status()

        # 🔧 V4: 포지션은 Step 2에서 로드됨 (중복 방지)

        # 🔧 백엔드 로그 필터링 핸들러 초기화
        self._setup_backend_logging()

        # 🔧 순차적 초기화 시작 (500ms 후)
        QTimer.singleShot(500, self._start_sequential_initialization)

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

        # 🔧 V4: 트레이딩 모드 선택 삭제 (그룹 시스템으로 대체)

        # 🔧 1. 상태 패널 (사이드바 상단)
        status_group = QGroupBox("📊 상태")
        status_layout = QVBoxLayout()

        self.status_label = QLabel("● 중지됨")
        self.status_label.setFont(QFont("맑은 고딕", 11, QFont.Bold))
        status_layout.addWidget(self.status_label)

        # V4: Mode 표시 (Live/Dry-run | 준비 상태)
        self.mode_label = QLabel("Mode: Live | 준비 완료")
        self.mode_label.setFont(QFont("맑은 고딕", 9))
        status_layout.addWidget(self.mode_label)

        status_group.setLayout(status_layout)
        sidebar_layout.addWidget(status_group)

        # 🔧 2. 계좌 정보 패널 (사이드바)
        account_group = QGroupBox("💰 계좌 정보")
        account_layout = QFormLayout()

        self.krw_balance_label = QLabel("로딩 중...")
        self.krw_balance_label.setFont(QFont("Consolas", 9, QFont.Bold))
        self.krw_balance_label.setStyleSheet("color: #2196F3;")
        account_layout.addRow("보유 KRW:", self.krw_balance_label)

        self.total_buy_label = QLabel("로딩 중...")
        self.total_buy_label.setFont(QFont("Consolas", 9))
        account_layout.addRow("총 매수:", self.total_buy_label)

        # 🔧 기존 코드 호환성 유지 (화면에 표시 안 함)
        self.total_asset_label = QLabel("총 자산: 로딩 중...")
        self.profit_label = QLabel("수익률: 0.00%")
        self.mdd_label = QLabel("최대 낙폭: 0.00%")

        account_group.setLayout(account_layout)
        sidebar_layout.addWidget(account_group)

        # 🔧 3. 그룹 현황 패널 (V4 신규)
        group_info_group = QGroupBox("📁 그룹 현황")
        group_info_layout = QVBoxLayout()

        self.active_groups_label = QLabel("활성 그룹: 0개")
        self.active_groups_label.setFont(QFont("맑은 고딕", 9, QFont.Bold))
        group_info_layout.addWidget(self.active_groups_label)

        self.total_positions_label = QLabel("총 포지션: 0개")
        self.total_positions_label.setFont(QFont("맑은 고딕", 9))
        group_info_layout.addWidget(self.total_positions_label)

        # 그룹별 포지션 수 표시 영역
        self.group_details_label = QLabel("")
        self.group_details_label.setFont(QFont("Consolas", 8))
        self.group_details_label.setStyleSheet("color: #666; padding-left: 10px;")
        group_info_layout.addWidget(self.group_details_label)

        group_info_group.setLayout(group_info_layout)
        sidebar_layout.addWidget(group_info_group)

        # 🔧 4. 오늘의 거래 패널 (V4 신규)
        trade_summary_group = QGroupBox("📈 오늘의 거래")
        trade_summary_layout = QFormLayout()

        self.today_buy_count_label = QLabel("0건")
        self.today_buy_count_label.setFont(QFont("Consolas", 9))
        self.today_buy_count_label.setStyleSheet("color: #F44336;")
        trade_summary_layout.addRow("매수:", self.today_buy_count_label)

        self.today_sell_count_label = QLabel("0건")
        self.today_sell_count_label.setFont(QFont("Consolas", 9))
        self.today_sell_count_label.setStyleSheet("color: #2196F3;")
        trade_summary_layout.addRow("매도:", self.today_sell_count_label)

        self.today_realized_pnl_label = QLabel("0원")
        self.today_realized_pnl_label.setFont(QFont("Consolas", 9, QFont.Bold))
        trade_summary_layout.addRow("실현 손익:", self.today_realized_pnl_label)

        trade_summary_group.setLayout(trade_summary_layout)
        sidebar_layout.addWidget(trade_summary_group)

        # 🔧 4. 실행 버튼들 (사이드바 하단)
        button_group = QGroupBox("⚙️ 제어")
        button_layout = QVBoxLayout()

        # 🔧 V4: 그룹 관리 버튼 추가
        group_management_btn = QPushButton("📁 그룹 관리")
        group_management_btn.setStyleSheet("background-color: #FF9800; color: white; padding: 8px; font-weight: bold;")
        group_management_btn.clicked.connect(self._open_group_management)
        button_layout.addWidget(group_management_btn)

        # 🔧 V4: 전역 설정 버튼 추가
        global_settings_btn = QPushButton("⚙️ 전역 설정")
        global_settings_btn.setStyleSheet("background-color: #9C27B0; color: white; padding: 8px; font-weight: bold;")
        global_settings_btn.clicked.connect(self._open_global_settings)
        button_layout.addWidget(global_settings_btn)

        # 🔧 MyAsset 구독 상태 라벨
        self.myasset_status_label = QLabel("🔄 실시간 감지 준비 중...")
        self.myasset_status_label.setFont(QFont("맑은 고딕", 9))
        self.myasset_status_label.setStyleSheet(
            "padding: 8px; background-color: #FFF9C4; color: #F57F17; "
            "border-radius: 3px; border: 1px solid #FBC02D;"
        )
        self.myasset_status_label.setWordWrap(True)
        button_layout.addWidget(self.myasset_status_label)

        # 시작 버튼
        self.start_btn = QPushButton("▶ 전체 DCA 시작")
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px; font-size: 13px; font-weight: bold;")
        self.start_btn.setEnabled(False)  # 🔧 초기에 비활성화 (MyAsset 준비 완료까지)
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

        # 🔧 V4: 포지션 테이블 생성 (12개 컬럼 - 즉시매도 버튼 추가)
        self.position_table = QTableWidget()
        self.position_table.setColumnCount(12)
        self.position_table.setHorizontalHeaderLabels([
            "그룹", "심볼", "매수", "DCA", "익절", "손절", "평균가", "현재가", "수량", "평가손익", "수익률(%)", "즉시매도"
        ])

        # 테이블 스타일 설정
        self.position_table.setFont(QFont("Consolas", 10))
        self.position_table.setAlternatingRowColors(False)  # 그룹별 배경색 사용으로 비활성화
        self.position_table.setEditTriggers(QTableWidget.NoEditTriggers)  # 읽기 전용
        self.position_table.setSelectionBehavior(QTableWidget.SelectItems)  # 개별 셀 선택

        # 컬럼 너비 자동 조정
        header = self.position_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)

        # 🔧 테이블 정렬 비활성화 (컬럼 헤더 클릭 시 정렬 방지)
        self.position_table.setSortingEnabled(False)

        position_layout.addWidget(self.position_table)
        
        # === 탭 2: 거래 내역 ===
        trade_history_widget = QWidget()
        trade_history_layout = QVBoxLayout(trade_history_widget)
        trade_history_layout.setContentsMargins(5, 5, 5, 5)

        # 🔧 거래 내역 상단: 요약 라벨 + 내보내기 버튼 (수평 레이아웃)
        trade_header_layout = QHBoxLayout()

        # 거래 내역 요약 정보
        self.trade_summary_label = QLabel("총 0건 | 매수: 0건, 매도: 0건 | 누적 손익: 0원 (0.00%)")
        self.trade_summary_label.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        self.trade_summary_label.setStyleSheet("color: #666; padding: 5px; background-color: #f5f5f5; border-radius: 3px;")
        trade_header_layout.addWidget(self.trade_summary_label, stretch=1)

        # 🆕 내보내기 버튼
        self.export_trades_btn = QPushButton("📥 내보내기")
        self.export_trades_btn.setFixedWidth(100)
        self.export_trades_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)
        self.export_trades_btn.clicked.connect(self._export_session_trades)
        trade_header_layout.addWidget(self.export_trades_btn)

        trade_history_layout.addLayout(trade_header_layout)

        # 거래 내역 테이블 생성 (9개 컬럼 - 그룹 추가)
        self.session_trades_table = QTableWidget()
        self.session_trades_table.setColumnCount(9)
        self.session_trades_table.setHorizontalHeaderLabels([
            "시각", "그룹", "심볼", "유형", "가격", "수량", "금액", "손익", "사유"
        ])

        # 테이블 스타일 설정
        self.session_trades_table.setFont(QFont("Consolas", 9))
        self.session_trades_table.setAlternatingRowColors(True)
        self.session_trades_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.session_trades_table.setSelectionBehavior(QTableWidget.SelectRows)

        # 컬럼 너비 설정 (9개) - 고정 너비로 균등하게 배치
        trade_header = self.session_trades_table.horizontalHeader()
        self.session_trades_table.setColumnWidth(0, 70)   # 시각 (HH:MM:SS)
        self.session_trades_table.setColumnWidth(1, 90)   # 그룹
        self.session_trades_table.setColumnWidth(2, 60)   # 심볼 (BTC, ETH)
        self.session_trades_table.setColumnWidth(3, 80)   # 유형 (자동매수, DCA L1)
        self.session_trades_table.setColumnWidth(4, 100)  # 가격
        self.session_trades_table.setColumnWidth(5, 110)  # 수량 (소수점 8자리)
        self.session_trades_table.setColumnWidth(6, 100)  # 금액
        self.session_trades_table.setColumnWidth(7, 100)  # 손익
        trade_header.setSectionResizeMode(8, QHeaderView.Stretch)  # 사유 (나머지 공간)

        # 정렬 활성화
        self.session_trades_table.setSortingEnabled(True)

        trade_history_layout.addWidget(self.session_trades_table)
        
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

        # 구분선
        settings_menu.addSeparator()

        # 모드 전환 (Step 7)
        self.mode_toggle_action = QAction(self._get_mode_toggle_text(), self)
        self.mode_toggle_action.triggered.connect(self._toggle_mode)
        settings_menu.addAction(self.mode_toggle_action)

        # 도움말 메뉴
        help_menu = menubar.addMenu("도움말")

        about_action = QAction("ℹ️ 정보", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _init_statusbar(self):
        """상태바 초기화"""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self._update_mode_display()  # 모드 표시 초기화

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

        # 코인 선택 다이얼로그 열기 (upbit_api 전달하여 동적 코인 목록 로드)
        dialog = CoinSelectionDialog(self, selected_coins=selected_coins, upbit_api=self.upbit_api)

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

            # 🔧 V4: 사이드바 그룹 현황 업데이트 (나중에 _update_sidebar_group_info()로 대체)

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
        # DCA Simulator 다이얼로그 열기 (첫 번째 레벨 금액 사용)
        first_level_amount = self.dca_config.levels[0].order_amount if self.dca_config.levels else 10000

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
        """트레이딩 시작 (V4)"""
        # 이미 실행 중이면 무시
        if self.is_running:
            self._add_log("⚠️ 이미 실행 중입니다")
            return

        # V4 사용 불가능 시
        if not V4_AVAILABLE:
            QMessageBox.critical(
                self,
                "V4 엔진 없음",
                "V4 Trading Engine을 불러올 수 없습니다.\n"
                "core 모듈이 올바르게 설치되었는지 확인하세요."
            )
            return

        # API 키 검증
        if not self.api_keys_validated and self.upbit_api is None:
            QMessageBox.warning(
                self,
                "API 키 필요",
                "Upbit API 키가 설정되지 않았습니다.\n"
                "먼저 초기화 단계(Step 1)를 완료해주세요."
            )
            return

        # 그룹 설정 확인
        try:
            config = self.v4_config_manager.load_config()
            groups = config.get("groups", {})

            if not groups:
                reply = QMessageBox.question(
                    self,
                    "그룹 없음",
                    "설정된 거래 그룹이 없습니다.\n\n"
                    "그룹 관리 메뉴에서 그룹을 생성하시겠습니까?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    self._open_group_management()
                return

            # 활성화된 그룹 확인
            active_groups = {gid: g for gid, g in groups.items() if not g.get("observation_mode", False)}
            if not active_groups:
                QMessageBox.information(
                    self,
                    "활성 그룹 없음",
                    "모든 그룹이 관찰 모드입니다.\n"
                    "실제 거래를 하려면 최소 1개 그룹의 관찰 모드를 해제하세요."
                )

        except Exception as e:
            logger.error(f"❌ 설정 로드 실패: {e}")
            QMessageBox.critical(
                self,
                "설정 오류",
                f"거래 설정을 불러올 수 없습니다:\n{e}"
            )
            return

        # 실거래 모드 확인
        global_settings = config.get("global_settings", {})
        dry_run = global_settings.get("dry_run", True)

        if not dry_run:
            reply = QMessageBox.question(
                self,
                "🚨 실거래 모드 시작 확인",
                "⚠️⚠️⚠️ <b>실제 거래 모드입니다!</b> ⚠️⚠️⚠️<br><br>"
                "<b style='color: red;'>실제 돈으로 주문이 실행됩니다!</b><br><br>"
                "확인 사항:<br>"
                "✅ Upbit API 키에 '주문하기' 권한 있음<br>"
                "✅ 충분한 KRW 잔고 확인<br>"
                "✅ 그룹 설정 확인 완료<br>"
                "✅ 텔레그램 알림 동작 확인<br><br>"
                "<b>정말로 시작하시겠습니까?</b>",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

        # V4 Trading Engine 시작
        try:
            self._add_log("=" * 50)
            self._add_log("🚀 V4 Trading Engine 시작")
            self._add_log("=" * 50)

            # 🔧 1단계: GUI WebSocket 중지 (V4 WebSocket으로 전환)
            if self.price_websocket_worker and self.price_websocket_worker.isRunning():
                logger.info("🔄 GUI WebSocket → V4 WebSocket 전환")
                self._add_log("🔄 실시간 가격: GUI WebSocket → V4 WebSocket 전환")
                self.price_websocket_worker.stop()
                self.price_websocket_worker.wait(3000)  # 최대 3초 대기
                self.price_websocket_worker = None

            # 🔧 2단계: V4TradingEngine 인스턴스 생성 (PositionManager 공유)
            self.v4_engine = V4TradingEngine(
                config_path="config/trading_config.json",
                upbit_api=self.upbit_api,
                position_manager=self.v4_position_manager  # recent_bot_sells 공유
            )

            # 🔧 2-1단계: 자동 매도 콜백 등록 (중복 알림 방지)
            self.v4_engine.on_auto_sell_callback = self._on_auto_sell_executed
            logger.info("✅ 자동 매도 콜백 등록 완료")

            # 🔧 2-2단계: 포지션 생성 콜백 등록 (GUI 새로고침용)
            self.v4_engine.on_position_created_callback = self._on_position_created
            logger.info("✅ 포지션 생성 콜백 등록 완료")

            # 🆕 2-3단계: 거래 내역 콜백 등록 (세션 거래 기록용)
            self.v4_engine.on_trade_callback = self._on_trade_event
            logger.info("✅ 거래 내역 콜백 등록 완료")

            # 엔진을 백그라운드 스레드에서 시작 (GUI 블로킹 방지)
            def run_engine():
                try:
                    self.v4_engine.start()
                except Exception as e:
                    logger.error(f"❌ V4 엔진 실행 오류: {e}", exc_info=True)
                    # GUI 스레드에서 처리할 수 있도록 시그널 필요 시 추가

            self.engine_thread = threading.Thread(target=run_engine, daemon=True)
            self.engine_thread.start()

            # 🔧 3단계: 상태 업데이트
            self.is_running = True
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.statusbar.showMessage("실행 중")

            # 🔧 4단계: V4 WebSocket 데이터를 GUI로 전달하는 타이머 시작
            self.price_update_timer = QTimer(self)
            self.price_update_timer.timeout.connect(self._update_from_v4)
            self.price_update_timer.start(100)  # 0.1초마다 (실시간)
            logger.info("✅ V4 → GUI 실시간 가격 업데이트 타이머 시작 (0.1초 간격)")

            mode_str = "🧪 Dry-run" if dry_run else "💰 Live"
            self._add_log(f"✅ V4 엔진 시작 완료 ({mode_str})")
            self._add_log(f"📊 활성 그룹: {len(groups)}개")

            # V4 엔진 시작 완료 - 여기서 종료
            return

        except Exception as e:
            logger.error(f"❌ V4 엔진 시작 실패: {e}", exc_info=True)
            self.is_running = False
            QMessageBox.critical(
                self,
                "시작 실패",
                f"V4 Trading Engine 시작에 실패했습니다:\n\n{e}"
            )
            return

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

        # 🔧 V4: 아래 코드는 Phase 2 early return으로 인해 실행되지 않음
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
            # 🔧 V4: Phase 2 early return으로 인해 실행되지 않음
            self._add_log("=" * 50)
            self._add_log("🚀 트레이딩 시작")
            self._add_log("=" * 50)

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
                
                # 🔧 V4: dry_run 설정은 V4 config에서 관리 (하드코딩 제거)
                'dry_run': None,  # Phase 2 early return으로 실행되지 않음
                
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
                self.trading_worker.trade_signal.connect(self._on_trade_executed)  # 🔧 거래 내역 기록
                
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
        """트레이딩 중지 (V4)"""
        # 이미 중지 중이면 무시
        if not self.is_running:
            return

        reply = QMessageBox.question(
            self,
            "트레이딩 중지",
            "V4 Trading Engine을 중지하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self._add_log("")
            self._add_log("=" * 50)
            self._add_log("🛑 V4 Trading Engine 중지")
            self._add_log("=" * 50)

            # 즉시 버튼 비활성화 (중복 클릭 방지)
            self.stop_btn.setEnabled(False)

            # 🔧 1단계: V4 → GUI 가격 업데이트 타이머 중지
            if self.price_update_timer:
                logger.info("🛑 V4 → GUI 가격 업데이트 타이머 중지")
                self.price_update_timer.stop()
                self.price_update_timer = None

            # 🔧 2단계: V4 엔진 중지
            if self.v4_engine:
                try:
                    self._add_log("⏳ V4 엔진 중지 중...")
                    self.v4_engine.stop()
                    self._add_log("✅ V4 엔진 정상 종료")
                except Exception as e:
                    logger.error(f"❌ V4 엔진 중지 실패: {e}")
                    self._add_log(f"❌ 엔진 중지 중 오류: {e}")
                finally:
                    self.v4_engine = None

            # 🔧 3단계: 상태 업데이트
            self.is_running = False
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.statusbar.showMessage("중지됨")
            self._add_log("✅ 트레이딩 중지 완료")

            # 🔧 4단계: GUI WebSocket 재시작 (활성 포지션이 있으면)
            try:
                positions = self.v4_position_manager.get_active_positions()
                if positions:
                    symbols = [p['symbol'] for p in positions.values()]
                    logger.info(f"🔄 V4 WebSocket → GUI WebSocket 전환 ({len(symbols)}개 심볼)")
                    self._add_log(f"🔄 실시간 가격: V4 WebSocket → GUI WebSocket 전환")
                    self._start_price_websocket(symbols)
                else:
                    logger.info("⏭️ 포지션 없음: GUI WebSocket 시작 불필요")
            except Exception as e:
                logger.error(f"❌ GUI WebSocket 재시작 실패: {e}", exc_info=True)

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

        # 🔧 최초 1회만 조회
        # self._add_log("🔄 계좌 정보 조회 중...")

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
            self.session_trades.insert(0, trade)
            
            # 테이블 업데이트
            self._update_trade_history_table()
            
            # 로그 출력
            emoji = trade.get_type_emoji()
            trade_type = trade.get_type_text()
            symbol_short = trade.get_symbol_short()
            
            if trade.trade_type == 'buy':
                self._add_log(f"{emoji} {symbol_short} {trade_type}: {format_price(trade.price)} × {trade.quantity:.8f} = {trade.amount:,.0f}원")

                # 🔧 V4: 매수 발생 시 테이블 업데이트는 V4 엔진에서 처리
            else:
                self._add_log(f"{emoji} {symbol_short} {trade_type}: {format_price(trade.price)} × {trade.quantity:.8f} = {trade.amount:,.0f}원 | 손익: {trade.profit:+,.0f}원 ({trade.profit_pct:+.2f}%)")

                # 🔧 V4: 매도 발생 시 테이블 업데이트는 V4 엔진에서 처리

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

    # 🔧 V4: _on_coin_update() 함수 제거됨
    # V3 테이블 구조(8컬럼)와 V4 테이블 구조(11컬럼) 충돌로 인해 제거
    # V4 포지션 업데이트는 별도 구현 필요

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

                # 🆕 관리 중인 포지션 수 + 총평가손익 표시
                self._update_total_profit_label(managed)

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
            # 🔧 V4: 포지션 업데이트는 V4 엔진에서 처리
            # V3 _on_coin_update 제거됨

        except KeyboardInterrupt:
            # 프로그램 종료 시 발생하는 KeyboardInterrupt 무시
            pass
        except Exception as e:
            logger.error(f"❌ [GUI] 포지션 업데이트 오류 ({symbol}): {e}", exc_info=True)
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
        # 🔧 V4: 사이드바 전체 업데이트로 대체
        pass
    
    def _update_trade_history_table(self):
        """거래 내역 테이블 업데이트"""
        try:
            # 정렬 비활성화 (업데이트 중)
            self.session_trades_table.setSortingEnabled(False)
            
            # 테이블 초기화
            self.session_trades_table.setRowCount(len(self.session_trades))
            
            # 거래 내역 통계 계산
            total_trades = len(self.session_trades)
            buy_count = sum(1 for t in self.session_trades if t.trade_type == 'buy')
            sell_count = sum(1 for t in self.session_trades if t.trade_type == 'sell')
            total_profit = sum(t.profit for t in self.session_trades if t.trade_type == 'sell')
            
            # 누적 수익률 계산 (총 매수 금액 대비)
            total_buy_amount = sum(t.amount for t in self.session_trades if t.trade_type == 'buy')
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
            
            # 각 거래 내역 추가 (9개 컬럼)
            for row, trade in enumerate(self.session_trades):
                # 0: 시각
                time_item = QTableWidgetItem(trade.get_time_str())
                time_item.setTextAlignment(Qt.AlignCenter)
                self.session_trades_table.setItem(row, 0, time_item)

                # 1: 그룹 (🆕)
                group_item = QTableWidgetItem(trade.group)
                group_item.setTextAlignment(Qt.AlignCenter)
                self.session_trades_table.setItem(row, 1, group_item)

                # 2: 심볼
                symbol_item = QTableWidgetItem(trade.get_symbol_short())
                symbol_item.setFont(QFont("Consolas", 9, QFont.Bold))
                symbol_item.setTextAlignment(Qt.AlignCenter)
                self.session_trades_table.setItem(row, 2, symbol_item)

                # 3: 유형 (detail_type: 자동매수, DCA L1, 익절 L1 등)
                type_item = QTableWidgetItem(f"{trade.get_type_emoji()} {trade.get_type_text()}")
                type_item.setTextAlignment(Qt.AlignCenter)
                if trade.trade_type == 'buy':
                    type_item.setForeground(Qt.red)
                else:
                    type_item.setForeground(Qt.blue)
                self.session_trades_table.setItem(row, 3, type_item)

                # 4: 가격
                price_item = QTableWidgetItem(f"{trade.price:,.0f}")
                price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.session_trades_table.setItem(row, 4, price_item)

                # 5: 수량
                qty_item = QTableWidgetItem(f"{trade.quantity:.8f}")
                qty_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.session_trades_table.setItem(row, 5, qty_item)

                # 6: 금액
                amount_item = QTableWidgetItem(f"{trade.amount:,.0f}")
                amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.session_trades_table.setItem(row, 6, amount_item)

                # 7: 손익
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
                self.session_trades_table.setItem(row, 7, profit_item)

                # 8: 사유
                reason_item = QTableWidgetItem(trade.reason)
                reason_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                self.session_trades_table.setItem(row, 8, reason_item)
            
            # 정렬 다시 활성화
            self.session_trades_table.setSortingEnabled(True)
            
        except Exception as e:
            self._add_log(f"⚠️ 거래 내역 테이블 업데이트 오류: {e}")

    def _export_session_trades(self):
        """세션 거래 내역을 CSV 파일로 내보내기"""
        if not self.session_trades:
            QMessageBox.information(self, "내보내기", "내보낼 거래 내역이 없습니다.")
            return

        from datetime import datetime
        from PySide6.QtWidgets import QFileDialog
        import csv

        # 기본 파일명 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"거래내역_{timestamp}.csv"

        # 파일 저장 다이얼로그
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "거래 내역 내보내기",
            default_filename,
            "CSV 파일 (*.csv);;모든 파일 (*.*)"
        )

        if not file_path:
            return  # 사용자가 취소함

        try:
            # CSV 파일로 저장 (utf-8-sig: Excel에서 한글 깨짐 방지)
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)

                # 헤더 작성
                writer.writerow([
                    '시각', '그룹', '심볼', '유형', '가격',
                    '수량', '금액', '손익', '손익률(%)', '사유'
                ])

                # 데이터 작성
                for trade in self.session_trades:
                    writer.writerow([
                        trade.get_time_str() if hasattr(trade, 'get_time_str') else trade.timestamp.strftime("%H:%M:%S"),
                        trade.group,
                        trade.get_symbol_short() if hasattr(trade, 'get_symbol_short') else trade.symbol.replace('KRW-', ''),
                        trade.detail_type,
                        f"{trade.price:,.0f}",
                        f"{trade.quantity:.8f}",
                        f"{trade.amount:,.0f}",
                        f"{trade.profit:+,.0f}" if trade.profit != 0 else "",
                        f"{trade.profit_pct:+.2f}" if trade.profit_pct != 0 else "",
                        trade.reason
                    ])

            # 내보내기 요약 계산
            buy_count = sum(1 for t in self.session_trades if t.trade_type == 'buy')
            sell_count = sum(1 for t in self.session_trades if t.trade_type == 'sell')
            total_profit = sum(t.profit for t in self.session_trades)

            QMessageBox.information(
                self,
                "내보내기 완료",
                f"거래 내역을 저장했습니다.\n\n"
                f"📁 파일: {file_path}\n"
                f"📊 총 {len(self.session_trades)}건 (매수: {buy_count}, 매도: {sell_count})\n"
                f"💰 누적 손익: {total_profit:+,.0f}원"
            )

            logger.info(f"✅ 거래 내역 내보내기 완료: {file_path} ({len(self.session_trades)}건)")

        except Exception as e:
            logger.error(f"❌ 거래 내역 내보내기 오류: {e}")
            QMessageBox.critical(
                self,
                "내보내기 실패",
                f"거래 내역 내보내기에 실패했습니다.\n\n오류: {e}"
            )

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
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            for _ in range(100):
                cursor.select(QTextCursor.SelectionType.LineUnderCursor)
                cursor.removeSelectedText()
                cursor.deleteChar()  # 줄바꿈 문자 삭제

        # 자동 스크롤 (최신 로그로)
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _setup_backend_logging(self):
        """
        백엔드 로그 필터링 핸들러 설정

        백엔드(core 모듈)의 로그를 필터링하여 중요한 정보만 GUI에 표시
        """
        try:
            # GuiLogHandler 생성
            self.gui_log_handler = GuiLogHandler()

            # Signal 연결: 백엔드 로그 → GUI
            self.gui_log_handler.log_signal.connect(self._on_backend_log)

            # 백엔드 로거에 핸들러 등록
            backend_loggers = [
                "core.v4_trading_engine",
                "core.order_manager",
                "core.position_manager",
                "core.risk_manager",
                "core.daily_loss_tracker",
                "core.strategies",
                "core.upbit_api",
            ]

            for logger_name in backend_loggers:
                backend_logger = logging.getLogger(logger_name)
                backend_logger.addHandler(self.gui_log_handler)

            logger.info("✅ GUI 로그 핸들러 초기화 완료")

        except Exception as e:
            logger.error(f"❌ GUI 로그 핸들러 초기화 실패: {e}")

    def _on_auto_sell_executed(self, symbol: str, quantity: float):
        """
        자동 매도 실행 시 호출되는 콜백 (중복 알림 방지)

        V4TradingEngine에서 익절/손절 매도 실행 시 호출되어,
        MyAsset WebSocket의 "수동 매도" 알림을 방지합니다.

        Args:
            symbol: 매도한 코인 심볼 (예: KRW-BTC)
            quantity: 매도한 수량 (사용하지 않음, 로깅용)
        """
        import time
        self.recent_immediate_sells[symbol] = time.time()
        logger.info(f"🔖 자동 매도 추적 등록: {symbol} (수량: {quantity:.8f}) - 10초간 수동매도 알림 차단")

    def _on_position_created(self, symbol: str):
        """
        포지션 생성/변경 시 호출되는 콜백 (백그라운드 스레드에서 호출됨)

        V4TradingEngine에서 포지션이 생성/변경될 때 호출되어,
        Signal을 통해 GUI 스레드에 새로고침을 요청합니다.

        Args:
            symbol: 생성/변경된 포지션의 코인 심볼 (예: KRW-BTC)
        """
        logger.info(f"📊 포지션 변경 콜백 수신: {symbol}")
        try:
            # 🔧 Signal을 통해 GUI 스레드에서 안전하게 새로고침
            self.position_refresh_signal.emit(symbol)
        except Exception as e:
            logger.error(f"❌ GUI 새로고침 Signal emit 오류: {e}")

    def _on_position_refresh_requested(self, symbol: str):
        """
        포지션 새로고침 Signal 슬롯 (GUI 스레드에서 실행됨)

        백그라운드 스레드에서 position_refresh_signal이 emit되면
        이 슬롯이 GUI 스레드에서 호출됩니다.

        Args:
            symbol: 변경된 포지션의 심볼
        """
        logger.info(f"🔄 GUI 포지션 새로고침 요청: {symbol}")
        try:
            self._load_v4_positions()
        except Exception as e:
            logger.error(f"❌ GUI 포지션 새로고침 오류: {e}")

    def _on_trade_event(self, trade):
        """
        거래 이벤트 콜백 (백그라운드 스레드에서 호출됨)

        V4TradingEngine에서 거래가 완료될 때 호출되어,
        세션 거래 내역에 추가합니다.

        Args:
            trade: Trade 데이터 객체
        """
        try:
            # 세션 거래 내역에 추가
            self.session_trades.append(trade)

            # GUI 스레드에서 테이블 업데이트 (QTimer.singleShot 사용)
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, self._update_trade_history_table)

            logger.debug(f"📊 거래 내역 추가: {trade}")
        except Exception as e:
            logger.error(f"❌ 거래 이벤트 콜백 오류: {e}")

    def _on_backend_log(self, level: str, formatted_message: str):
        """
        백엔드 로그 수신 핸들러

        GuiLogHandler에서 필터링된 로그를 GUI에 표시
        (타임스탬프는 이미 포함되어 있음)

        Args:
            level: 로그 레벨 (INFO/WARNING/ERROR/CRITICAL)
            formatted_message: 이미 포맷팅된 메시지 (예: "[10:30:45] ℹ️ 매수 체결...")
        """
        # 타임스탬프가 이미 포함되어 있으므로 그대로 추가
        self.log_text.append(formatted_message)

        # 로그 자동 정리 (최대 1000줄)
        document = self.log_text.document()
        if document.lineCount() > 1000:
            cursor = self.log_text.textCursor()
            cursor.movePosition(cursor.Start)
            for _ in range(100):
                cursor.select(cursor.LineUnderCursor)
                cursor.removeSelectedText()
                cursor.deleteChar()

        # 자동 스크롤
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
        self._add_log("🔄 초기화 시작...")
        self.myasset_status_label.setText("🔄 초기화 중... (1/3) 예수금 조회")

        # 단계 1: 예수금 조회
        self._step1_load_balance()

    def _step1_load_balance(self):
        """단계 1: 예수금 조회"""
        import logging
        logger = logging.getLogger(__name__)

        logger.info("🔄 [Step 1] 예수금 조회 시작")

        # 🔧 Step 3와 동일한 방식으로 API 키 가져오기
        access_key = self.config_manager.get_upbit_access_key()
        secret_key = self.config_manager.get_upbit_secret_key()

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

            # 🔧 accounts 데이터 저장 (Step 2에서 재사용하여 중복 API 호출 방지)
            self.initial_accounts = result.get('accounts', None)
            if self.initial_accounts:
                logger.info(f"✅ [Step 1] accounts 데이터 저장 완료: {len(self.initial_accounts)}개 자산")

            # 🔧 API 키 검증 완료 플래그 설정
            self.api_keys_validated = True
            logger.info("✅ [Step 1] API 키 검증 완료 (플래그 설정)")

            # 🔧 UpbitAPI 인스턴스 생성 및 저장
            try:
                from core.upbit_api import UpbitAPI
                access_key = self.config_manager.get_upbit_access_key()
                secret_key = self.config_manager.get_upbit_secret_key()
                self.upbit_api = UpbitAPI(access_key, secret_key)
                logger.info("✅ [Step 1] UpbitAPI 인스턴스 생성 완료")

                # V4 PositionManager에 API 전달
                if V4_AVAILABLE and self.v4_position_manager:
                    self.v4_position_manager.upbit_api = self.upbit_api
                    logger.info("✅ [Step 1] PositionManager에 UpbitAPI 전달 완료")
            except Exception as e:
                logger.error(f"❌ [Step 1] UpbitAPI 초기화 실패: {e}")
                self.upbit_api = None

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
        self.myasset_status_label.setText("🔄 초기화 중... (2/3) 보유 종목 조회")
        self._add_log("🔄 보유 종목 조회 중...")

        # ========================================
        # 🔧 V4: dry_run 모드 체크
        # ========================================
        if V4_AVAILABLE and self.v4_config_manager:
            try:
                config = self.v4_config_manager.load_config()
                is_dry_run = config.get("global_settings", {}).get("dry_run", True)

                if is_dry_run:
                    # Dry-run 모드: V4 가상 포지션 로드
                    logger.info("🟢 [Step 2] Dry-run 모드: 가상 포지션 로드")
                    self._add_log("🟢 Dry-run 모드: 가상 포지션 로드")
                    self._load_v4_positions()
                    self._step3_prepare_myasset()
                    return
                else:
                    # Live 모드: Upbit 동기화 + 포지션 로드
                    logger.info("🔴 [Step 2] Live 모드: Upbit 동기화 시작")
                    self._add_log("🔴 Live 모드: Upbit 계좌 동기화 중...")

                    try:
                        # sync_with_upbit() 호출 (Step 1에서 받은 accounts 재사용)
                        if self.v4_position_manager and self.upbit_api:
                            sync_result = self.v4_position_manager.sync_with_upbit(config, accounts=self.initial_accounts)
                            logger.info(f"✅ [Step 2] Upbit 동기화 완료: {sync_result}")
                            self._add_log(f"✅ 동기화 완료: {len(sync_result['synced_positions'])}개 업데이트, "
                                        f"{len(sync_result['new_positions'])}개 신규, "
                                        f"{len(sync_result['removed_positions'])}개 삭제")

                            # 포지션 테이블 로드
                            self._load_v4_positions()

                            # 🔧 MyAsset WebSocket 시작 (실시간 잔고 감지)
                            self._start_myasset_websocket()
                        else:
                            logger.warning("⚠️ [Step 2] PositionManager 또는 UpbitAPI가 없음")
                            self._add_log("⚠️ 포지션 관리자 초기화 필요")

                    except Exception as e:
                        logger.error(f"❌ [Step 2] Upbit 동기화 실패: {e}")
                        self._add_log(f"⚠️ Upbit 동기화 실패: {e}")

                    # 단계 3으로 진행
                    self._step3_prepare_myasset()
                    return

            except Exception as e:
                logger.error(f"❌ [Step 2] V4 설정 로드 실패: {e}")
                # V4 설정 실패 시 Live 모드로 fallback

        # ========================================
        # V4 미지원 시 Fallback: 기존 방식
        # ========================================
        logger.info("🔄 [Step 2] V4 미지원 - 기존 방식으로 포지션 조회")
        access_key = self.config_manager.get_upbit_access_key()
        secret_key = self.config_manager.get_upbit_secret_key()

        if not access_key or not secret_key:
            logger.warning("⚠️ [Step 2] API 키 미설정 - 단계 3으로 진행")
            self._add_log("⚠️ API 키 미설정 - 단계 3으로 진행")
            self._step3_prepare_myasset()
            return

        try:
            from core.upbit_api import UpbitAPI

            logger.info("🔍 [Step 2] UpbitAPI 초기화 및 계좌 조회 중...")
            api = UpbitAPI(access_key, secret_key)
            accounts = api.get_accounts()
            logger.info(f"✅ [Step 2] 계좌 조회 완료: {len(accounts)}개 자산")

            # 포지션 수집
            positions_found = []
            for account in accounts:
                currency = account['currency']
                if currency != 'KRW':
                    balance = float(account['balance'])
                    if balance > 0:
                        symbol = f'KRW-{currency}'
                        logger.info(f"💰 [Step 2] 포지션 발견: {symbol}, 수량={balance}")
                        positions_found.append(currency)

            if positions_found:
                logger.info(f"✅ [Step 2] 보유 종목 {len(positions_found)}개 발견: {', '.join(positions_found)}")
                self._add_log(f"✅ 보유 종목 {len(positions_found)}개 발견")
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
        self.myasset_status_label.setText("🔄 초기화 중... (3/3) 실시간 감지 준비")
        self._add_log("🔄 실시간 감지 준비 중...")

        # 기존 _start_myasset_preparation() 로직 호출
        self._start_myasset_preparation()

    # ========================================
    # MyAsset 구독 준비
    # ========================================

    def _start_myasset_preparation(self):
        """MyAsset WebSocket 구독 준비 시작 (백그라운드)"""
        # API 키 확인
        access_key = self.config_manager.get_upbit_access_key()
        secret_key = self.config_manager.get_upbit_secret_key()

        if not access_key or not secret_key:
            # API 키 없으면 준비 실패
            self.myasset_status_label.setText("⚠️ API 키 미설정 (Fallback 모드)")
            self.myasset_status_label.setStyleSheet(
                "padding: 8px; background-color: #FFCDD2; color: #C62828; "
                "border-radius: 3px; border: 1px solid #E53935;"
            )
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

        # 상태 라벨 업데이트
        self.myasset_status_label.setText("✅ 실시간 감지 준비 완료!")
        self.myasset_status_label.setStyleSheet(
            "padding: 8px; background-color: #C8E6C9; color: #2E7D32; "
            "border-radius: 3px; border: 1px solid #4CAF50;"
        )

    def _on_myasset_preparation_failed(self, error_msg: str):
        """MyAsset 구독 준비 실패"""
        self.myasset_ready = False
        self.start_btn.setEnabled(True)  # 버튼은 활성화 (fallback 모드로 작동)
        self._add_log(f"⚠️ 실시간 감지 준비 실패: {error_msg}")
        self._add_log("   → Fallback polling 모드로 작동합니다 (60초마다 확인)")

    def _on_myasset_status_update(self, status_msg: str):
        """MyAsset 상태 업데이트"""
        self.myasset_status_label.setText(status_msg)

    # ========================================
    # V4 GUI 핸들러
    # ========================================

    def _toggle_trading_mode(self):
        """Dry Run ↔ 실거래 모드 전환 (임시 구현)"""
        # TODO: Phase 3에서 실제 모드 전환 로직 구현
        QMessageBox.information(
            self,
            "모드 전환",
            "모드 전환 기능은 Phase 3에서 구현 예정입니다.\n"
            "현재는 Dry Run 모드로 동작합니다.",
            QMessageBox.Ok
        )

    def _open_group_management(self):
        """그룹 관리 다이얼로그 열기"""
        if not V4_AVAILABLE:
            QMessageBox.warning(
                self,
                "V4 기능 없음",
                "V4 모듈을 불러올 수 없습니다.\n"
                "core/config_manager.py, core/group_manager.py 파일을 확인하세요."
            )
            return

        try:
            dialog = GroupManagementDialog(
                self.v4_config_manager,
                self.v4_group_manager,
                parent=self,
                is_trading_running=self.is_running,  # 거래 실행 상태 전달
                upbit_api=self.upbit_api,  # 동적 코인 목록 로드용
                position_manager=self.v4_position_manager  # 레벨 리셋용
            )

            # 그룹 변경 시그널 연결
            dialog.groups_changed.connect(self._on_groups_changed)

            dialog.exec()

        except Exception as e:
            logger.error(f"❌ 그룹 관리 다이얼로그 오류: {e}")
            QMessageBox.critical(
                self,
                "오류",
                f"그룹 관리 다이얼로그를 열 수 없습니다.\n{e}"
            )

    def _on_groups_changed(self):
        """그룹 변경 시 호출 (메인 윈도우 업데이트)"""
        logger.info("📊 그룹 변경됨, 메인 윈도우 업데이트")

        # 1. GUI 업데이트
        self._load_v4_positions()
        self._add_log("✅ 그룹 설정이 업데이트되었습니다.")

        # 2. V4TradingEngine 리로드 (Bug #5 수정: 거래 중인 경우)
        if hasattr(self, 'v4_engine') and self.v4_engine:
            try:
                self.v4_engine.reload_config_and_update_groups()
                logger.info("   ✅ V4TradingEngine config 리로드 완료")
                self._add_log("✅ 거래 엔진 설정이 즉시 반영되었습니다.")
            except Exception as e:
                logger.error(f"   ❌ V4TradingEngine config 리로드 실패: {e}")
                self._add_log(f"⚠️ 설정 적용 실패: {e}")
        else:
            logger.info("   ℹ️ V4TradingEngine 없음 (거래 중지 상태)")

    def _load_v4_positions(self):
        """V4: 포지션 데이터 로드 및 테이블 표시"""
        if not V4_AVAILABLE or not self.v4_position_manager:
            return

        try:
            # 🔧 JSON 파일에서 최신 데이터 강제 리로드 (Engine과 동기화)
            self.v4_position_manager.reload_positions()

            # 활성 포지션만 가져오기 (status='active')
            positions = self.v4_position_manager.get_active_positions()

            # 설정 로드 (그룹명 및 DCA/익절/손절 설정 확인용)
            config = self.v4_config_manager.load_config()
            groups = config.get("groups", {})

            # 테이블 초기화
            self.position_table.setRowCount(0)

            # 포지션이 없으면 종료
            if not positions:
                logger.info("📊 활성 포지션 없음")
                return

            # 포지션을 그룹별로 정렬 (그룹 ID → 심볼 순)
            sorted_positions = sorted(
                positions.items(),
                key=lambda x: (x[1].get("group_id", ""), x[0])  # (group_id, symbol)
            )

            # 그룹별 배경색 정의 (부드러운 파스텔 톤)
            group_colors = [
                "#E3F2FD",  # Light Blue
                "#F3E5F5",  # Light Purple
                "#E8F5E9",  # Light Green
                "#FFF3E0",  # Light Orange
                "#FCE4EC",  # Light Pink
                "#F1F8E9",  # Light Lime
                "#FFF9C4",  # Light Yellow
                "#E0F2F1",  # Light Teal
            ]

            # 그룹별 색상 매핑
            group_color_map = {}
            color_index = 0

            # 각 포지션을 테이블에 추가
            row_idx = 0
            managed_count = 0  # 🔧 관찰 모드 제외한 관리 중인 포지션 카운트
            total_profit_krw = 0  # 🆕 총평가손익
            total_invested_krw = 0  # 🆕 총투자금액
            for symbol, pos in sorted_positions:
                if pos.get("status") != "active":
                    continue  # 비활성 포지션은 스킵

                # 그룹 정보 가져오기
                group_id = pos.get("group_id", "")
                group = groups.get(group_id, {})
                group_name = group.get("name", group_id)

                # 🔧 관찰 모드가 아닌 포지션만 카운트 (최대 포지션 개수 계산용)
                if not group.get("observation_only", False):
                    managed_count += 1

                # 매수/DCA/익절/손절 설정
                buy_settings = group.get("buy_settings", {})
                buy_mode = buy_settings.get("mode", "manual")
                buy_text = "자동" if buy_mode == "auto" else "수동"

                dca_settings = group.get("dca_settings", {})
                dca_mode = dca_settings.get("mode", "disabled")
                dca_text = "ON" if dca_mode == "auto" else "OFF"

                profit_settings = group.get("profit_settings", {})
                profit_mode = profit_settings.get("mode", "disabled")
                profit_text = "ON" if profit_mode in ["auto", "alert"] else "OFF"

                loss_settings = group.get("loss_settings", {})
                loss_mode = loss_settings.get("mode", "disabled")
                loss_text = "ON" if loss_mode in ["auto", "alert"] else "OFF"

                # 포지션 데이터
                average_price = pos.get("avg_buy_price", 0)
                current_price = pos.get("current_price", average_price)
                total_amount = pos.get("total_amount", 0)
                profit_krw = pos.get("profit_krw", 0)
                profit_pct = pos.get("profit_pct", 0)

                # 🆕 총평가손익/총투자금액 누적 (관찰 모드 제외)
                if not group.get("observation_only", False):
                    total_profit_krw += profit_krw
                    total_invested_krw += average_price * total_amount

                # 테이블 행 추가
                self.position_table.insertRow(row_idx)

                # 컬럼 데이터 설정
                items = [
                    QTableWidgetItem(group_name),                        # 0: 그룹
                    QTableWidgetItem(symbol),                            # 1: 심볼
                    QTableWidgetItem(buy_text),                          # 2: 매수
                    QTableWidgetItem(dca_text),                          # 3: DCA
                    QTableWidgetItem(profit_text),                       # 4: 익절
                    QTableWidgetItem(loss_text),                         # 5: 손절
                    QTableWidgetItem(f"{average_price:,.2f}"),          # 6: 평균가 (소수점 2자리)
                    QTableWidgetItem(f"{current_price:,.2f}"),          # 7: 현재가 (소수점 2자리)
                    QTableWidgetItem(f"{total_amount:.8f}"),            # 8: 수량
                    QTableWidgetItem(f"{profit_krw:+,.0f}"),            # 9: 평가손익
                    QTableWidgetItem(f"{profit_pct:+.2f}%")             # 10: 수익률
                ]

                # 그룹별 배경색 할당
                if group_id not in group_color_map:
                    group_color_map[group_id] = group_colors[color_index % len(group_colors)]
                    color_index += 1

                bg_color = QColor(group_color_map[group_id])

                # 모든 셀 중앙 정렬 및 배경색 적용
                for col_idx, item in enumerate(items):
                    item.setTextAlignment(Qt.AlignCenter)
                    item.setBackground(bg_color)
                    self.position_table.setItem(row_idx, col_idx, item)

                # 그룹명 셀은 볼드체 적용
                items[0].setFont(QFont("Consolas", 10, QFont.Bold))

                # 수익/손실 색상 적용 (텍스트 색상)
                if profit_krw > 0:
                    # 수익: 빨간색
                    items[9].setForeground(QColor("red"))
                    items[10].setForeground(QColor("red"))
                elif profit_krw < 0:
                    # 손실: 파란색
                    items[9].setForeground(QColor("blue"))
                    items[10].setForeground(QColor("blue"))

                # 🔧 즉시매도 버튼 추가 (11번째 컬럼)
                # 중요: 시작/중지 상태와 무관하게 항상 활성화
                sell_btn = QPushButton("매도")
                sell_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #f44336;
                        color: white;
                        padding: 5px;
                        border-radius: 3px;
                        font-weight: bold;
                        font-size: 11px;
                    }
                    QPushButton:hover {
                        background-color: #d32f2f;
                    }
                """)
                # 람다로 symbol, group_id 전달
                sell_btn.clicked.connect(lambda checked, s=symbol, g=group_id: self._execute_immediate_sell(s, g))
                self.position_table.setCellWidget(row_idx, 11, sell_btn)

                row_idx += 1

            logger.debug(f"✅ V4 포지션 로드 완료: {row_idx}개 (관리 중: {managed_count}개)")

            # 🆕 총평가수익률 계산
            total_profit_pct = (total_profit_krw / total_invested_krw * 100) if total_invested_krw > 0 else 0

            # 🆕 관리 중인 포지션 개수 + 총평가손익 업데이트 (HTML로 색상 적용)
            if total_profit_krw >= 0:
                # 수익: 빨간색
                profit_color = "red"
                profit_icon = "📈"
            else:
                # 손실: 파란색
                profit_color = "blue"
                profit_icon = "📉"

            self.price_label.setText(
                f"관리 중: {managed_count}개 포지션 | "
                f"<span style='color:{profit_color}; font-weight:bold;'>"
                f"💰 총손익: {total_profit_krw:+,.0f}원 ({profit_icon} {total_profit_pct:+.2f}%)"
                f"</span>"
            )

            # 🔧 WebSocket 시작 (포지션이 있을 때만)
            if row_idx > 0:
                self._start_price_websocket(list(positions.keys()))

        except Exception as e:
            logger.error(f"❌ V4 포지션 로드 실패: {e}")
            self._add_log(f"⚠️ 포지션 로드 실패: {e}")

    def _update_total_profit_label(self, managed_count: int = None):
        """
        🆕 총평가손익 라벨 업데이트 (포지션 테이블 기반)

        Args:
            managed_count: 관리 중인 포지션 수 (None이면 테이블에서 계산)
        """
        try:
            # 포지션 테이블에서 총평가손익 계산
            total_profit_krw = 0
            total_invested_krw = 0
            row_count = self.position_table.rowCount() if managed_count is None else managed_count

            for row in range(self.position_table.rowCount()):
                # 평균가 (6번 컬럼), 현재가 (7번 컬럼), 수량 (8번 컬럼), 평가손익 (9번 컬럼)
                avg_price_item = self.position_table.item(row, 6)
                amount_item = self.position_table.item(row, 8)
                profit_item = self.position_table.item(row, 9)

                if avg_price_item and amount_item and profit_item:
                    try:
                        avg_price = float(avg_price_item.text().replace(',', ''))
                        amount = float(amount_item.text())
                        profit = float(profit_item.text().replace(',', '').replace('+', ''))

                        total_invested_krw += avg_price * amount
                        total_profit_krw += profit
                    except (ValueError, AttributeError):
                        continue

            # 총평가수익률 계산
            total_profit_pct = (total_profit_krw / total_invested_krw * 100) if total_invested_krw > 0 else 0

            # 색상 및 아이콘 결정
            if total_profit_krw >= 0:
                profit_color = "red"
                profit_icon = "📈"
            else:
                profit_color = "blue"
                profit_icon = "📉"

            # 관리 중 포지션 수 (없으면 테이블 행 수 사용)
            if managed_count is None:
                managed_count = self.position_table.rowCount()

            # 라벨 업데이트 (HTML 형식)
            self.price_label.setText(
                f"관리 중: {managed_count}개 포지션 | "
                f"<span style='color:{profit_color}; font-weight:bold;'>"
                f"💰 총손익: {total_profit_krw:+,.0f}원 ({profit_icon} {total_profit_pct:+.2f}%)"
                f"</span>"
            )

        except Exception as e:
            logger.error(f"❌ 총평가손익 라벨 업데이트 오류: {e}")
            # 오류 시 기본 라벨 표시
            if managed_count is not None:
                self.price_label.setText(f"관리 중: {managed_count}개 포지션")

    def _start_price_websocket(self, symbols: list):
        """
        가격 WebSocket 시작 또는 업데이트

        옵션 A (공식 Best Practice):
        - 워커가 실행 중이면 update_symbols() 호출 (연결 유지, 메시지만 재전송)
        - 워커가 없거나 중지 상태면 새로 시작

        Args:
            symbols: 구독할 심볼 리스트
        """
        try:
            # 🔧 시작 버튼 누른 상태면 V4 WebSocket 사용 (GUI WebSocket 사용 안 함)
            if self.is_running:
                logger.debug("⏭️ 시작 중: V4 WebSocket 사용, GUI WebSocket 스킵")
                return

            # 🔥 핵심: 워커가 실행 중이면 재구독만 수행 (연결 재시작 X)
            if self.price_websocket_worker and self.price_websocket_worker.isRunning():
                logger.info(f"🔄 Symbol 리스트 업데이트 시도: {len(symbols)}개")
                self.price_websocket_worker.update_symbols(symbols)
                return

            # 워커가 없거나 중지 상태 → 새로 시작
            logger.info(f"🚀 새 WebSocket 워커 시작: {len(symbols)}개 심볼")

            # 기존 워커가 중지 상태면 정리
            if self.price_websocket_worker:
                logger.info("🛑 기존 WebSocket 워커 정리")
                self.price_websocket_worker.stop()
                self.price_websocket_worker.wait(3000)  # 3초 대기

            # 새 워커 생성
            from gui.price_websocket_worker import PriceWebSocketWorker

            self.price_websocket_worker = PriceWebSocketWorker(
                self.v4_position_manager,
                parent=self
            )

            # 시그널 연결
            self.price_websocket_worker.price_updated.connect(self._on_price_updated)
            self.price_websocket_worker.connected.connect(self._on_websocket_connected)
            self.price_websocket_worker.disconnected.connect(self._on_websocket_disconnected)
            self.price_websocket_worker.error_occurred.connect(self._on_websocket_error)

            # 심볼 설정 및 시작
            self.price_websocket_worker.set_symbols(symbols)
            self.price_websocket_worker.start()

            logger.info(f"✅ 가격 WebSocket 시작 완료: {len(symbols)}개 심볼")
            self._add_log(f"🔌 실시간 가격 업데이트 시작 ({len(symbols)}개 코인)")

        except Exception as e:
            logger.error(f"❌ WebSocket 시작/업데이트 실패: {e}", exc_info=True)
            self._add_log(f"⚠️ 실시간 가격 업데이트 오류: {e}")

    def _start_myasset_websocket(self):
        """
        MyAsset WebSocket 시작 (실시간 잔고 감지)

        Live 모드에서만 실행되며, 잔고 변동을 실시간으로 감지합니다.
        """
        try:
            # API 키 확인
            access_key = self.config_manager.get_upbit_access_key()
            secret_key = self.config_manager.get_upbit_secret_key()

            if not access_key or not secret_key:
                logger.warning("⚠️ MyAsset WebSocket: API 키 미설정")
                return

            # V4 config 로드
            if not self.v4_config_manager:
                logger.warning("⚠️ MyAsset WebSocket: V4 config 없음")
                return

            config = self.v4_config_manager.load_config()

            # 기존 워커가 있으면 중지
            if self.myasset_websocket_worker and self.myasset_websocket_worker.isRunning():
                logger.info("🛑 기존 MyAsset WebSocket 워커 중지")
                self.myasset_websocket_worker.stop()
                self.myasset_websocket_worker.wait(3000)  # 3초 대기

            # 새 워커 생성
            from gui.myasset_websocket_worker import MyAssetWebSocketWorker

            # 🆕 V4 엔진의 pending_initial_buys 참조 가져오기 (봇 주문/외부 매수 구분용)
            pending_initial_buys = None
            if hasattr(self, 'v4_engine') and self.v4_engine:
                pending_initial_buys = self.v4_engine.pending_initial_buys

            self.myasset_websocket_worker = MyAssetWebSocketWorker(
                access_key,
                secret_key,
                self.v4_position_manager,
                config,
                pending_initial_buys=pending_initial_buys,  # 🆕 봇 주문 추적용
                parent=self
            )

            # 시그널 연결
            self.myasset_websocket_worker.balance_updated.connect(self._on_balance_updated)
            self.myasset_websocket_worker.connected.connect(self._on_myasset_connected)
            self.myasset_websocket_worker.disconnected.connect(self._on_myasset_disconnected)
            self.myasset_websocket_worker.error_occurred.connect(self._on_myasset_error)

            # 워커 시작
            self.myasset_websocket_worker.start()

            logger.info("🚀 MyAsset WebSocket 시작: 실시간 잔고 감지")
            self._add_log("💰 실시간 잔고 감지 시작 (자동 동기화 활성화)")

        except Exception as e:
            logger.error(f"❌ MyAsset WebSocket 시작 실패: {e}", exc_info=True)
            self._add_log(f"⚠️ 실시간 잔고 감지 시작 실패: {e}")

    def _on_price_updated(self, symbol: str, current_price: float):
        """
        가격 업데이트 시그널 핸들러

        Args:
            symbol: 심볼 (예: 'KRW-BTC')
            current_price: 현재가
        """
        try:
            if not self.v4_position_manager:
                return

            # PositionManager에서 가격 업데이트 (수익률 재계산)
            position = self.v4_position_manager.update_price(symbol, current_price)
            if not position:
                return

            # 테이블에서 해당 심볼 찾기
            for row in range(self.position_table.rowCount()):
                symbol_item = self.position_table.item(row, 1)
                if not symbol_item or symbol_item.text() != symbol:
                    continue

                # 그룹 배경색 가져오기 (그룹명 셀에서)
                group_item = self.position_table.item(row, 0)
                bg_color = group_item.background() if group_item else QColor("white")

                # 현재가 업데이트 (컬럼 7)
                price_item = QTableWidgetItem(f"{current_price:,.2f}")
                price_item.setTextAlignment(Qt.AlignCenter)
                price_item.setBackground(bg_color)
                self.position_table.setItem(row, 7, price_item)

                # 평가손익 업데이트 (컬럼 9)
                profit_krw = position.get('profit_krw', 0)
                profit_item = QTableWidgetItem(f"{profit_krw:+,.0f}")
                profit_item.setTextAlignment(Qt.AlignCenter)
                profit_item.setBackground(bg_color)

                if profit_krw > 0:
                    profit_item.setForeground(QColor("red"))
                elif profit_krw < 0:
                    profit_item.setForeground(QColor("blue"))

                self.position_table.setItem(row, 9, profit_item)

                # 수익률 업데이트 (컬럼 10)
                profit_pct = position.get('profit_pct', 0)
                pct_item = QTableWidgetItem(f"{profit_pct:+.2f}%")
                pct_item.setTextAlignment(Qt.AlignCenter)
                pct_item.setBackground(bg_color)

                if profit_pct > 0:
                    pct_item.setForeground(QColor("red"))
                elif profit_pct < 0:
                    pct_item.setForeground(QColor("blue"))

                self.position_table.setItem(row, 10, pct_item)

                break

            # 🆕 총평가손익 라벨 실시간 업데이트
            self._update_total_profit_label()

        except Exception as e:
            logger.error(f"❌ 가격 업데이트 처리 오류: {e}", exc_info=True)

    def _on_websocket_connected(self):
        """WebSocket 연결 성공 핸들러"""
        logger.info("✅ WebSocket 연결 성공")
        self._add_log("✅ 실시간 가격 업데이트 연결됨")

    def _on_websocket_disconnected(self):
        """WebSocket 연결 종료 핸들러"""
        logger.warning("⚠️ WebSocket 연결 종료")
        self._add_log("⚠️ 실시간 가격 업데이트 종료됨")

    def _on_websocket_error(self, error_msg: str):
        """WebSocket 에러 핸들러"""
        logger.error(f"❌ WebSocket 에러: {error_msg}")
        self._add_log(f"⚠️ 실시간 가격 업데이트 오류: {error_msg}")

    def _update_from_v4(self):
        """
        V4 WebSocket 데이터를 GUI로 전달 (0.1초마다 호출됨)

        V4TradingEngine의 WebSocketManager에서 실시간 현재가를 읽어서
        GUI 포지션 테이블을 업데이트합니다.
        """
        try:
            if not self.v4_engine or not self.v4_position_manager:
                return

            # WebSocketManager가 실행 중인지 확인
            if not self.v4_engine.websocket_manager or not self.v4_engine.websocket_manager.is_running:
                return

            # 활성 포지션의 심볼에 대해 현재가 가져오기
            positions = self.v4_position_manager.get_active_positions()
            for symbol, position in positions.items():
                # V4 WebSocketManager에서 실시간 현재가 가져오기
                current_price = self.v4_engine.websocket_manager.get_current_price(symbol)

                if current_price and current_price > 0:
                    # GUI 업데이트 (기존 _on_price_updated 메서드 재사용)
                    self._on_price_updated(symbol, current_price)

        except Exception as e:
            logger.error(f"❌ V4 → GUI 가격 업데이트 오류: {e}", exc_info=True)

    def _on_balance_updated(self, assets: list):
        """
        MyAsset 잔고 업데이트 시그널 핸들러

        Args:
            assets: MyAsset WebSocket에서 받은 자산 리스트
        """
        try:
            if not self.v4_position_manager or not self.v4_config_manager:
                return

            # PositionManager 동기화
            config = self.v4_config_manager.load_config()
            sync_result = self.v4_position_manager.sync_from_myasset(assets, config)

            # 로그 출력 (변경 사항이 있을 때만)
            has_changes = (sync_result['synced_positions'] or
                          sync_result['new_positions'] or
                          sync_result['removed_positions'])

            if has_changes:
                logger.info(f"💰 잔고 변동 감지: "
                           f"신규 {len(sync_result['new_positions'])}개, "
                           f"삭제 {len(sync_result['removed_positions'])}개, "
                           f"업데이트 {len(sync_result['synced_positions'])}개")

                # 포지션 테이블 리프레시 (업데이트도 포함!)
                self._load_v4_positions()

                # 수동매도 감지 시 GUI 로그만 표시 (텔레그램 알림 없음)
                # 🔧 MyOrder에서 이미 처리된 수동 매도는 중복 로그 스킵
                if sync_result['removed_positions']:
                    for removed_pos in sync_result['removed_positions']:
                        if isinstance(removed_pos, dict):
                            symbol = removed_pos['symbol']

                            # 🔧 MyOrder에서 최근 처리된 경우 스킵 (중복 로그 방지)
                            if hasattr(self, 'v4_engine') and self.v4_engine:
                                if self.v4_engine._was_recently_processed_by_myorder(symbol, window_seconds=10):
                                    logger.debug(f"   ⏭️ {symbol} MyOrder에서 이미 처리됨 → MyAsset 수동매도 로그 스킵")
                                    continue

                            profit_krw = removed_pos.get('profit_krw', 0)
                            profit_pct = removed_pos.get('profit_pct', 0)
                            self._add_log(f"[수동매도] {symbol} | {profit_krw:+,.0f}원 ({profit_pct:+.2f}%)")
                        else:
                            self._add_log(f"[수동매도] {removed_pos}")

                # 🔧 new_positions 로그 제거 - V4 엔진(MyOrder)에서 이미 처리함
                # MyAsset은 백업용이므로 GUI 로그 불필요

                if sync_result['synced_positions']:
                    # 🔧 봇 매도 시 수량 변동 로그 차단 (MyOrder에서 이미 처리됨)
                    if hasattr(self, 'v4_engine') and self.v4_engine:
                        filtered_positions = [
                            s for s in sync_result['synced_positions']
                            if not self.v4_engine._was_recently_processed_by_myorder(s, window_seconds=10)
                        ]
                    else:
                        filtered_positions = sync_result['synced_positions']

                    if filtered_positions:
                        synced_str = ', '.join(filtered_positions)
                        self._add_log(f"📊 수량 변동: {synced_str}")

        except Exception as e:
            logger.error(f"❌ 잔고 업데이트 처리 오류: {e}", exc_info=True)

    def _on_myasset_connected(self):
        """MyAsset WebSocket 연결 성공 핸들러"""
        logger.info("✅ MyAsset WebSocket 연결 성공")
        self._add_log("✅ 실시간 잔고 감지 연결됨")

    def _on_myasset_disconnected(self):
        """MyAsset WebSocket 연결 종료 핸들러"""
        logger.warning("⚠️ MyAsset WebSocket 연결 종료")
        self._add_log("⚠️ 실시간 잔고 감지 종료됨")

    def _on_myasset_error(self, error_msg: str):
        """MyAsset WebSocket 에러 핸들러"""
        logger.error(f"❌ MyAsset WebSocket 에러: {error_msg}")
        self._add_log(f"⚠️ 실시간 잔고 감지 오류: {error_msg}")

    def _execute_immediate_sell(self, symbol: str, group_id: str):
        """
        즉시매도 실행

        ⚠️ 중요: 시작/중지 상태와 무관하게 항상 실행 가능

        Args:
            symbol: 매도할 심볼 (예: 'KRW-BTC')
            group_id: 그룹 ID
        """
        try:
            # 1. API 키 확인
            if not self.upbit_api:
                QMessageBox.warning(
                    self,
                    "API 없음",
                    "Upbit API가 설정되지 않았습니다.\n"
                    "설정 메뉴에서 API 키를 등록해주세요."
                )
                return

            # 2. 설정 로드
            if not self.v4_config_manager or not self.v4_position_manager:
                QMessageBox.warning(
                    self,
                    "V4 미지원",
                    "V4 시스템이 로드되지 않았습니다."
                )
                return

            config = self.v4_config_manager.load_config()
            dry_run = config.get("global_settings", {}).get("dry_run", True)

            # 3. 포지션 정보 조회
            position = self.v4_position_manager.get_position(symbol)
            if not position:
                QMessageBox.warning(
                    self,
                    "포지션 없음",
                    f"{symbol} 포지션을 찾을 수 없습니다."
                )
                return

            total_amount = position.get("total_amount", 0)
            avg_buy_price = position.get("avg_buy_price", 0)
            current_price = position.get("current_price", avg_buy_price)
            profit_krw = position.get("profit_krw", 0)
            profit_pct = position.get("profit_pct", 0)

            if total_amount <= 0:
                QMessageBox.warning(
                    self,
                    "수량 없음",
                    f"{symbol}의 보유 수량이 0입니다."
                )
                return

            # 4. 확인 다이얼로그
            estimated_value = total_amount * current_price

            msg = (
                f"<b>{symbol}</b>을(를) 즉시 전량 매도하시겠습니까?<br><br>"
                f"• 보유 수량: {total_amount:.8f}<br>"
                f"• 평균 매수가: {avg_buy_price:,.2f} 원<br>"
                f"• 현재가: {current_price:,.2f} 원<br>"
                f"• 예상 매도 금액: {estimated_value:,.0f} 원<br>"
                f"• 예상 손익: {profit_krw:+,.0f} 원 ({profit_pct:+.2f}%)<br><br>"
            )

            if dry_run:
                msg += "⚠️ <b>Dry-run 모드</b>이므로 실제 주문이 실행되지 않습니다."
            else:
                msg += "⚠️ <b>실제 시장가 매도 주문이 실행됩니다!</b>"

            reply = QMessageBox.question(
                self,
                "즉시매도 확인",
                msg,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

            # 5. 매도 실행
            self._add_log("=" * 50)
            self._add_log(f"🔴 즉시매도 실행: {symbol}")

            if dry_run:
                # Dry-run 모드: 가상 매도
                logger.info(f"[Dry-run] 즉시매도: {symbol}, 수량: {total_amount}")
                sell_result = {
                    'uuid': 'DRYRUN-' + symbol,
                    'executed_volume': str(total_amount),
                    'price': str(current_price)
                }
                actual_sell_price = current_price
                actual_sell_amount = total_amount
            else:
                # 실제 매도 실행
                # 🆕 identifier 생성 (봇 즉시매도 구분용)
                currency = symbol.replace("KRW-", "")
                timestamp_str = datetime.now().strftime("%Y%m%d%H%M%S")
                short_uuid = uuid.uuid4().hex[:8]
                identifier = f"bot_immediate_{currency}_{timestamp_str}_{short_uuid}"
                logger.debug(f"🏷️ 즉시매도 identifier 생성: {identifier}")

                sell_result = self.upbit_api.sell_market_order(symbol, total_amount, identifier=identifier)

                if not sell_result or 'uuid' not in sell_result:
                    raise ValueError("매도 주문 실패: 결과에 UUID가 없습니다.")

                # 실제 체결 가격 조회
                import time
                time.sleep(0.5)  # 체결 완료 대기 (시장가는 보통 즉시 체결)

                order_detail = self.upbit_api.get_order(sell_result['uuid'])

                if order_detail.get('state') == 'done' and order_detail.get('trades'):
                    # trades 배열에서 가중 평균 체결 가격 계산
                    trades = order_detail['trades']
                    total_funds = sum(float(t['funds']) for t in trades)
                    total_volume = sum(float(t['volume']) for t in trades)

                    actual_sell_price = total_funds / total_volume if total_volume > 0 else current_price
                    actual_sell_amount = total_volume

                    logger.info(f"💰 실제 체결가: {actual_sell_price:,.2f} 원 (예상: {current_price:,.2f} 원, 차이: {actual_sell_price - current_price:+.2f} 원)")
                else:
                    # 체결이 완료되지 않았거나 정보가 없는 경우 WebSocket 현재가 사용 (fallback)
                    actual_sell_price = current_price
                    actual_sell_amount = total_amount
                    logger.warning(f"⚠️ 체결 정보 조회 실패, WebSocket 현재가 사용: {current_price:,.2f} 원")

            # 6. 성공 처리 (실제 체결 가격으로 재계산)
            actual_sell_value = actual_sell_amount * actual_sell_price
            actual_profit_krw = actual_sell_value - (avg_buy_price * actual_sell_amount)
            actual_profit_pct = (actual_profit_krw / (avg_buy_price * actual_sell_amount)) * 100 if avg_buy_price > 0 else 0

            logger.info(f"✅ 즉시매도 성공: {symbol} | {actual_sell_value:,.0f}원 | {actual_profit_krw:+,.0f}원 ({actual_profit_pct:+.2f}%)")
            self._add_log(f"✅ 즉시매도 성공: {symbol} | {actual_sell_value:,.0f}원 | {actual_profit_krw:+,.0f}원 ({actual_profit_pct:+.2f}%)")

            # 7. 포지션 제거 (실제 체결 가격으로)
            close_reason = "즉시매도"
            self.v4_position_manager.close_position(
                symbol=symbol,
                close_price=actual_sell_price,
                close_reason=close_reason
            )

            # 7-1. 즉시매도 기록 (중복 알림 방지용)
            import time
            self.recent_immediate_sells[symbol] = time.time()
            logger.info(f"📝 즉시매도 기록: {symbol} (10초간 수동매도 알림 억제)")

            # 8. 거래 내역 기록 (TradeHistoryManager가 있으면, 실제 체결 가격으로)
            if hasattr(self, 'v4_trade_history_manager'):
                try:
                    from core.trade_history_manager import TradeHistoryManager
                    history_mgr = TradeHistoryManager()
                    history_mgr.add_trade(
                        group_id=group_id,
                        symbol=symbol,
                        trade_type='sell',
                        price=actual_sell_price,
                        amount=actual_sell_amount,
                        profit_loss=actual_profit_krw,
                        reason=close_reason
                    )
                except Exception as e:
                    logger.warning(f"거래 내역 기록 실패: {e}")

            # 9. 포지션 테이블 새로고침
            self._load_v4_positions()

            # 10. 텔레그램 알림 (항상 전송, V4 엔진 무관, 실제 체결 가격으로)
            telegram_msg = (
                f"🔴 즉시매도 완료\n\n"
                f"심볼: {symbol}\n"
                f"수량: {actual_sell_amount:.8f}\n"
                f"체결가: {actual_sell_price:,.0f} 원\n"
                f"손익: {actual_profit_krw:+,.0f} 원 ({actual_profit_pct:+.2f}%)"
            )

            # 방법 1: V4 엔진이 실행 중이면 엔진의 메서드 사용
            if hasattr(self, 'v4_engine') and self.v4_engine:
                try:
                    self.v4_engine._send_telegram_alert(telegram_msg)
                except Exception as e:
                    logger.warning(f"V4 엔진 텔레그램 알림 실패: {e}")
            else:
                # 방법 2: V4 엔진이 없으면 직접 전송 (동기 방식)
                try:
                    telegram_token = self.config_manager.get_telegram_bot_token()
                    telegram_chat_id = self.config_manager.get_telegram_chat_id()

                    if telegram_token and telegram_chat_id:
                        def send_telegram_sync():
                            """텔레그램 동기 전송 (requests 사용, 별도 스레드)"""
                            try:
                                import requests
                                url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
                                payload = {
                                    "chat_id": telegram_chat_id,
                                    "text": telegram_msg
                                }
                                response = requests.post(url, json=payload, timeout=10)
                                response.raise_for_status()
                                logger.info(f"📤 텔레그램 메시지 전송 완료 (즉시매도)")
                            except Exception as e:
                                logger.error(f"❌ 텔레그램 전송 실패: {e}")

                        # 별도 스레드에서 전송 (GUI 블로킹 방지)
                        import threading
                        thread = threading.Thread(target=send_telegram_sync, daemon=True)
                        thread.start()
                    else:
                        logger.debug("텔레그램 설정 없음 (알림 스킵)")
                except Exception as e:
                    logger.warning(f"텔레그램 알림 실패: {e}")

            # 성공 메시지는 GUI 로그로만 출력 (결과창 제거 - 경고창만 유지)

        except Exception as e:
            logger.error(f"❌ 즉시매도 실패: {e}", exc_info=True)
            self._add_log(f"❌ 즉시매도 실패: {symbol} - {e}")
            QMessageBox.critical(
                self,
                "즉시매도 실패",
                f"{symbol} 즉시매도 중 오류가 발생했습니다:\n\n{str(e)}"
            )

    def _open_global_settings(self):
        """전역 설정 다이얼로그 열기"""
        if not V4_AVAILABLE or not self.v4_config_manager:
            QMessageBox.warning(
                self,
                "V4 미지원",
                "V4 설정 파일이 없습니다.\n"
                "그룹 관리에서 새 그룹을 생성하면 V4 설정이 자동 생성됩니다."
            )
            return

        from gui.global_settings_dialog import GlobalSettingsDialog

        dialog = GlobalSettingsDialog(self.v4_config_manager, parent=self)
        if dialog.exec() == QDialog.Accepted:
            logger.info("✅ 전역 설정 저장 완료")
            # 설정 변경 후 필요한 동작 (예: DailyLossTracker 재시작 등)
            # TODO: V4TradingEngine 연동 시 처리

    # ========================================
    # Step 7: 모드 전환 (Live ↔ Dry-run)
    # ========================================

    def _get_mode_toggle_text(self) -> str:
        """모드 전환 메뉴 텍스트 반환"""
        if not V4_AVAILABLE or not self.v4_config_manager:
            return "🔄 모드 전환"

        try:
            config = self.v4_config_manager.load_config()
            is_dry_run = config.get("global_settings", {}).get("dry_run", True)

            if is_dry_run:
                return "🔄 모드 전환 (현재: 🟢 Dry-run)"
            else:
                return "🔄 모드 전환 (현재: 🔴 Live)"
        except Exception as e:
            logger.error(f"❌ 모드 텍스트 로드 실패: {e}")
            return "🔄 모드 전환"

    def _toggle_mode(self):
        """모드 전환 (Live ↔ Dry-run)"""
        if not V4_AVAILABLE or not self.v4_config_manager:
            QMessageBox.warning(
                self,
                "V4 미지원",
                "V4 설정 파일이 없습니다.\n"
                "그룹 관리에서 새 그룹을 생성하면 V4 설정이 자동 생성됩니다."
            )
            return

        # ========================================
        # 1단계: 실행 중 체크
        # ========================================
        if self.is_running:
            QMessageBox.warning(
                self,
                "모드 전환 불가",
                "거래가 실행 중입니다.\n\n"
                "먼저 [중지] 버튼을 눌러\n"
                "거래를 중지한 후 모드를 전환하세요."
            )
            return

        # ========================================
        # 2단계: 현재 모드 확인
        # ========================================
        try:
            config = self.v4_config_manager.load_config()
            current_dry_run = config.get("global_settings", {}).get("dry_run", True)
        except Exception as e:
            logger.error(f"❌ 설정 로드 실패: {e}")
            QMessageBox.critical(self, "오류", f"설정을 불러올 수 없습니다:\n{e}")
            return

        # ========================================
        # 3단계: 전환 확인 다이얼로그
        # ========================================
        if not current_dry_run:  # Live → Dry-run
            reply = QMessageBox.question(
                self,
                "가상 거래 모드로 전환",
                "가상 거래 모드로 전환하시겠습니까?\n\n"
                "• 실제 거래가 중단됩니다\n"
                "• 테스트 목적으로만 사용됩니다",
                QMessageBox.Yes | QMessageBox.No
            )
        else:  # Dry-run → Live
            reply = QMessageBox.warning(
                self,
                "실거래 모드로 전환",
                "⚠️ 실거래 모드로 전환하시겠습니까?\n\n"
                "주의사항:\n"
                "• 실제 자금이 사용됩니다\n"
                "• 모든 거래는 되돌릴 수 없습니다\n"
                "• 충분히 테스트 후 전환하세요",
                QMessageBox.Yes | QMessageBox.No
            )

        if reply != QMessageBox.Yes:
            return

        # ========================================
        # 4단계: 모드 전환 처리
        # ========================================
        try:
            new_dry_run = not current_dry_run
            config["global_settings"]["dry_run"] = new_dry_run
            self.v4_config_manager.save_config(config)

            # PositionManager 재초기화
            mode_str = "dryrun" if new_dry_run else "live"

            # Upbit API 가져오기 (API 키가 있으면)
            upbit_api = None
            if hasattr(self, 'upbit_api') and self.upbit_api:
                upbit_api = self.upbit_api

            self.v4_position_manager = PositionManager(mode=mode_str, upbit_api=upbit_api)

            # 포지션 테이블 새로고침
            self._load_v4_positions()

            # UI 업데이트
            self._update_mode_display()

            # 완료 메시지
            mode_name = "🟢 가상 거래 (Dry-run)" if new_dry_run else "🔴 실거래 (Live)"
            QMessageBox.information(
                self,
                "모드 전환 완료",
                f"✅ {mode_name} 모드로 전환되었습니다.\n\n"
                f"포지션 테이블이 갱신되었습니다."
            )

            logger.info(f"✅ 모드 전환 완료: {'Dry-run' if new_dry_run else 'Live'}")

        except Exception as e:
            logger.error(f"❌ 모드 전환 실패: {e}")
            QMessageBox.critical(self, "모드 전환 실패", f"모드 전환 중 오류가 발생했습니다:\n{e}")

    def _update_mode_display(self):
        """모드 표시 업데이트 (메뉴 텍스트 + 상태바)"""
        if not V4_AVAILABLE or not self.v4_config_manager:
            self.statusbar.showMessage("준비")
            return

        try:
            config = self.v4_config_manager.load_config()
            is_dry_run = config.get("global_settings", {}).get("dry_run", True)

            # 메뉴 텍스트 업데이트
            if hasattr(self, 'mode_toggle_action'):
                self.mode_toggle_action.setText(self._get_mode_toggle_text())

            # 상태바 업데이트
            if is_dry_run:
                self.statusbar.showMessage("Mode: 🟢 Dry-run  |  준비 완료")
            else:
                self.statusbar.showMessage("Mode: 🔴 Live  |  준비 완료")

        except Exception as e:
            logger.error(f"❌ 모드 표시 업데이트 실패: {e}")
            self.statusbar.showMessage("준비")

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
                    # 반자동 모드: SemiAutoWorker
                    # SemiAutoWorker는 stop() 메서드 사용
                    self.trading_worker.stop()
                else:
                    # 완전 자동 모드: AutoTradingWorker
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

        # Price WebSocket Worker 정리
        if self.price_websocket_worker and self.price_websocket_worker.isRunning():
            logger.info("🛑 Price WebSocket Worker 종료 중...")
            self.price_websocket_worker.stop()
            if not self.price_websocket_worker.wait(3000):
                logger.warning("⚠️ Price WebSocket Worker 종료 시간 초과")
                self.price_websocket_worker.terminate()
                self.price_websocket_worker.wait(1000)
            self.price_websocket_worker = None

        # MyAsset WebSocket Worker 정리
        if self.myasset_websocket_worker and self.myasset_websocket_worker.isRunning():
            logger.info("🛑 MyAsset WebSocket Worker 종료 중...")
            self.myasset_websocket_worker.stop()
            if not self.myasset_websocket_worker.wait(3000):
                logger.warning("⚠️ MyAsset WebSocket Worker 종료 시간 초과")
                self.myasset_websocket_worker.terminate()
                self.myasset_websocket_worker.wait(1000)
            self.myasset_websocket_worker = None

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
