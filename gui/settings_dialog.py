"""
Settings Dialog - 설정 화면
.env 파일을 GUI로 편집
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QLineEdit, QPushButton, QSpinBox, QCheckBox,
    QGroupBox, QFormLayout, QMessageBox, QWidget, QComboBox,
    QTextEdit
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from gui.config_manager import ConfigManager


class SettingsDialog(QDialog):
    """
    설정 다이얼로그

    .env 파일의 설정을 GUI로 편집 가능
    """

    # 설정 변경 시그널
    settings_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.config_manager = ConfigManager()

        self.setWindowTitle("설정")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)

        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)

        # 탭 위젯
        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_upbit_tab(), "📡 Upbit API")
        self.tabs.addTab(self._create_telegram_tab(), "📱 Telegram")
        self.tabs.addTab(self._create_trading_tab(), "💱 거래 설정")
        self.tabs.addTab(self._create_strategy_tab(), "🎯 전략 설정")

        layout.addWidget(self.tabs)

        # 버튼
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.test_btn = QPushButton("🔍 연결 테스트")
        self.test_btn.clicked.connect(self._test_connection)
        button_layout.addWidget(self.test_btn)

        self.save_btn = QPushButton("💾 저장")
        self.save_btn.clicked.connect(self._save_settings)
        button_layout.addWidget(self.save_btn)

        self.cancel_btn = QPushButton("취소")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

    # ========================================
    # Upbit API 탭
    # ========================================

    def _create_upbit_tab(self) -> QWidget:
        """Upbit API 탭 생성"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # API 키 그룹
        api_group = QGroupBox("API Keys")
        api_layout = QFormLayout()

        self.access_key_edit = QLineEdit()
        self.access_key_edit.setEchoMode(QLineEdit.Password)
        self.access_key_edit.setPlaceholderText("Access Key를 입력하세요")
        api_layout.addRow("Access Key:", self.access_key_edit)

        # Access Key 표시 버튼
        access_key_show_btn = QPushButton("👁️ 표시")
        access_key_show_btn.setCheckable(True)
        access_key_show_btn.clicked.connect(
            lambda checked: self.access_key_edit.setEchoMode(
                QLineEdit.Normal if checked else QLineEdit.Password
            )
        )
        api_layout.addRow("", access_key_show_btn)

        self.secret_key_edit = QLineEdit()
        self.secret_key_edit.setEchoMode(QLineEdit.Password)
        self.secret_key_edit.setPlaceholderText("Secret Key를 입력하세요")
        api_layout.addRow("Secret Key:", self.secret_key_edit)

        # Secret Key 표시 버튼
        secret_key_show_btn = QPushButton("👁️ 표시")
        secret_key_show_btn.setCheckable(True)
        secret_key_show_btn.clicked.connect(
            lambda checked: self.secret_key_edit.setEchoMode(
                QLineEdit.Normal if checked else QLineEdit.Password
            )
        )
        api_layout.addRow("", secret_key_show_btn)

        api_group.setLayout(api_layout)
        layout.addWidget(api_group)

        # 안내 메시지
        info_label = QLabel(
            "💡 <b>API 키 발급 방법:</b><br>"
            "1. Upbit 웹사이트 접속<br>"
            "2. 마이페이지 > Open API 관리<br>"
            "3. API 키 생성 (자산 조회, 주문 조회, 주문하기 권한)<br>"
            "4. Access Key와 Secret Key 복사<br><br>"
            "🔗 <a href='https://upbit.com/mypage/open_api_management'>Upbit API 관리 페이지</a>"
        )
        info_label.setOpenExternalLinks(True)
        info_label.setWordWrap(True)
        info_label.setStyleSheet("background-color: #f0f0f0; padding: 10px; border-radius: 5px;")
        layout.addWidget(info_label)

        layout.addStretch()
        return widget

    # ========================================
    # Telegram 탭
    # ========================================

    def _create_telegram_tab(self) -> QWidget:
        """Telegram 탭 생성"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Telegram 설정 그룹
        telegram_group = QGroupBox("Bot 설정")
        telegram_layout = QFormLayout()

        self.bot_token_edit = QLineEdit()
        self.bot_token_edit.setEchoMode(QLineEdit.Password)
        self.bot_token_edit.setPlaceholderText("Bot Token을 입력하세요")
        telegram_layout.addRow("Bot Token:", self.bot_token_edit)

        # Bot Token 표시 버튼
        bot_token_show_btn = QPushButton("👁️ 표시")
        bot_token_show_btn.setCheckable(True)
        bot_token_show_btn.clicked.connect(
            lambda checked: self.bot_token_edit.setEchoMode(
                QLineEdit.Normal if checked else QLineEdit.Password
            )
        )
        telegram_layout.addRow("", bot_token_show_btn)

        self.chat_id_edit = QLineEdit()
        self.chat_id_edit.setPlaceholderText("Chat ID를 입력하세요")
        telegram_layout.addRow("Chat ID:", self.chat_id_edit)

        telegram_group.setLayout(telegram_layout)
        layout.addWidget(telegram_group)

        # 안내 메시지
        info_label = QLabel(
            "💡 <b>Telegram 봇 설정 방법:</b><br>"
            "1. Telegram 앱에서 @BotFather 검색<br>"
            "2. /newbot 명령어로 봇 생성<br>"
            "3. Bot Token 복사<br>"
            "4. @userinfobot에게 메시지 전송하여 Chat ID 확인<br><br>"
            "📖 <a href='https://github.com/your-repo/docs/TELEGRAM_설정_가이드.md'>상세 가이드 보기</a>"
        )
        info_label.setOpenExternalLinks(True)
        info_label.setWordWrap(True)
        info_label.setStyleSheet("background-color: #f0f0f0; padding: 10px; border-radius: 5px;")
        layout.addWidget(info_label)

        # 테스트 버튼
        test_telegram_btn = QPushButton("📱 알림 테스트 전송")
        test_telegram_btn.clicked.connect(self._test_telegram)
        layout.addWidget(test_telegram_btn)

        layout.addStretch()
        return widget

    # ========================================
    # 거래 설정 탭
    # ========================================

    def _create_trading_tab(self) -> QWidget:
        """거래 설정 탭 생성"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 거래 설정 그룹
        trading_group = QGroupBox("기본 설정")
        trading_layout = QFormLayout()

        self.min_order_amount_spin = QSpinBox()
        self.min_order_amount_spin.setRange(5000, 10000000)
        self.min_order_amount_spin.setSingleStep(1000)
        self.min_order_amount_spin.setSuffix(" 원")
        trading_layout.addRow("최소 주문 금액:", self.min_order_amount_spin)

        self.order_timeout_spin = QSpinBox()
        self.order_timeout_spin.setRange(10, 300)
        self.order_timeout_spin.setSingleStep(5)
        self.order_timeout_spin.setSuffix(" 초")
        trading_layout.addRow("주문 타임아웃:", self.order_timeout_spin)

        trading_group.setLayout(trading_layout)
        layout.addWidget(trading_group)

        # 안내 메시지
        info_label = QLabel(
            "💡 <b>거래 설정 안내:</b><br>"
            "• <b>최소 주문 금액</b>: 한 번에 주문할 최소 금액 (기본: 5,000원)<br>"
            "• <b>주문 타임아웃</b>: 주문 체결 대기 시간 (기본: 30초)<br>"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("background-color: #f0f0f0; padding: 10px; border-radius: 5px;")
        layout.addWidget(info_label)

        layout.addStretch()
        return widget

    # ========================================
    # 전략 설정 탭
    # ========================================

    def _create_strategy_tab(self) -> QWidget:
        """전략 설정 탭 생성"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 전략 선택 그룹
        strategy_group = QGroupBox("🎯 매매 전략 선택")
        strategy_layout = QVBoxLayout()

        # 전략 선택 콤보박스
        strategy_select_layout = QHBoxLayout()
        strategy_label = QLabel("전략:")
        strategy_label.setFont(QFont("Arial", 11, QFont.Bold))
        strategy_select_layout.addWidget(strategy_label)

        self.strategy_combo = QComboBox()
        self.strategy_combo.addItem("🏆 필터링된 볼린저 밴드 (권장)", "filtered_bb")
        self.strategy_combo.addItem("📊 기본 볼린저 밴드", "bb")
        self.strategy_combo.addItem("📈 RSI 전략", "rsi")
        self.strategy_combo.addItem("📉 MACD 전략", "macd")
        self.strategy_combo.setFont(QFont("Arial", 10))
        self.strategy_combo.currentIndexChanged.connect(self._on_strategy_changed)
        strategy_select_layout.addWidget(self.strategy_combo, 1)

        strategy_layout.addLayout(strategy_select_layout)

        strategy_group.setLayout(strategy_layout)
        layout.addWidget(strategy_group)

        # 전략 설명 그룹
        description_group = QGroupBox("📝 전략 설명")
        description_layout = QVBoxLayout()

        self.strategy_description = QTextEdit()
        self.strategy_description.setReadOnly(True)
        self.strategy_description.setMaximumHeight(250)
        self.strategy_description.setFont(QFont("Consolas", 9))
        description_layout.addWidget(self.strategy_description)

        description_group.setLayout(description_layout)
        layout.addWidget(description_group)

        # 백테스팅 결과 그룹
        backtest_group = QGroupBox("📊 백테스팅 결과 (2024-2025, 1년)")
        backtest_layout = QVBoxLayout()

        self.backtest_results = QTextEdit()
        self.backtest_results.setReadOnly(True)
        self.backtest_results.setMaximumHeight(200)
        self.backtest_results.setFont(QFont("Consolas", 9))
        backtest_layout.addWidget(self.backtest_results)

        backtest_group.setLayout(backtest_layout)
        layout.addWidget(backtest_group)

        layout.addStretch()
        return widget

    def _on_strategy_changed(self, index: int):
        """전략 선택 변경 시"""
        strategy_type = self.strategy_combo.itemData(index)
        
        descriptions = {
            'filtered_bb': """
🏆 필터링된 볼린저 밴드 전략 (최적화 완료)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 전략 개요
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"무릎에서 사기" 위한 통계적 매수 타이밍 전략입니다.
볼린저 밴드 + 다중 필터로 매수 신호를 생성합니다.

📍 매수 타이밍 (전략이 결정):
  1️⃣ 가격 < 볼린저 밴드 하단 (과매도 구간)
  2️⃣ 가격 < MA240 (하락 추세 확인)
  3️⃣ ATR >= 최소 변동성 기준 (거래량 충분)
  4️⃣ 마지막 거래 후 최소 대기 시간 경과

💰 추가 매수 (DCA):
  → 고급 DCA 설정에서 조정 가능
  → 기본: 5단계 분할 매수

💵 매도 타이밍 (DCA 익절/손절):
  ⚠️ 전략의 매도 신호는 사용하지 않습니다!
  → 고급 DCA 설정의 익절/손절로만 매도됩니다
  → 기본: 익절 +10%, 손절 -10% (변경 가능)
  → "어깨에서 팔기" 위한 목표가 관리

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✨ 코인별 최적 파라미터 (자동 적용)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BTC: std=2.0, wait=6h, atr=0.3
ETH: std=2.5, wait=10h, atr=0.4
XRP: std=2.0, wait=6h, atr=0.3

코인을 선택하면 해당 코인에 최적화된 파라미터가 자동으로 적용됩니다.
""",
            'bb': """
📊 기본 볼린저 밴드 전략

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 전략 개요
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
가격이 볼린저 밴드를 돌파할 때 매매하는 기본 전략입니다.

매수 조건:
  • 가격 < 볼린저 밴드 하단

매도 조건:
  • 가격 > 볼린저 밴드 상단

파라미터:
  • 기간: 20
  • 표준편차: 2.0

⚠️ 필터가 없어 거래 빈도가 높고 수수료 부담이 클 수 있습니다.
필터링된 볼린저 밴드 전략을 권장합니다.
""",
            'rsi': """
📈 RSI 전략

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 전략 개요
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RSI 지표를 이용한 과매수/과매도 매매 전략입니다.

매수 조건:
  • RSI < 30 (과매도)

매도 조건:
  • RSI > 70 (과매수)

파라미터:
  • 기간: 14
  • 과매도: 30
  • 과매수: 70

💡 횡보장에서 효과적이지만 강한 추세장에서는 손실 가능합니다.
""",
            'macd': """
📉 MACD 전략

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 전략 개요
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MACD와 시그널선의 교차를 이용한 추세 추종 전략입니다.

매수 조건:
  • MACD > 시그널 (골든크로스)

매도 조건:
  • MACD < 시그널 (데드크로스)

파라미터:
  • 빠른 기간: 12
  • 느린 기간: 26
  • 시그널 기간: 9

💡 추세장에서 효과적이지만 횡보장에서는 잦은 손절이 발생할 수 있습니다.
"""
        }
        
        backtest_results = {
            'filtered_bb': """
🏆 필터링된 볼린저 밴드 - 백테스팅 결과

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 개별 코인 성과
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BTC: +8.05%  (24회 거래, 승률 58.3%)
ETH: +64.92% (26회 거래, 승률 38.5%) 🔥
XRP: +14.42% (84회 거래, 승률 52.4%)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 포트폴리오 전체 (6,000,000원 투자)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
최종 자산: 7,747,838원
포트폴리오 수익률: +29.13% ✅
총 거래: 134회
월 평균 거래: 11회

현실적 기대 수익률: 약 14.57% (백테스팅의 50%)
""",
            'bb': """
📊 기본 볼린저 밴드 - 백테스팅 미실시

⚠️ 이 전략은 백테스팅이 완료되지 않았습니다.
필터가 없어 과도한 거래가 발생할 수 있습니다.

권장: 필터링된 볼린저 밴드 전략 사용
""",
            'rsi': """
📈 RSI 전략 - 백테스팅 미실시

⚠️ 이 전략은 백테스팅이 완료되지 않았습니다.

사용 전 백테스팅을 통한 성과 검증이 필요합니다.
""",
            'macd': """
📉 MACD 전략 - 백테스팅 미실시

⚠️ 이 전략은 백테스팅이 완료되지 않았습니다.

사용 전 백테스팅을 통한 성과 검증이 필요합니다.
"""
        }
        
        self.strategy_description.setPlainText(descriptions.get(strategy_type, ""))
        self.backtest_results.setPlainText(backtest_results.get(strategy_type, ""))

    # ========================================
    # 설정 로드/저장
    # ========================================

    def _load_settings(self):
        """현재 설정 로드"""
        # Upbit API
        self.access_key_edit.setText(self.config_manager.get_upbit_access_key())
        self.secret_key_edit.setText(self.config_manager.get_upbit_secret_key())

        # Telegram
        self.bot_token_edit.setText(self.config_manager.get_telegram_bot_token())
        self.chat_id_edit.setText(self.config_manager.get_telegram_chat_id())

        # Trading
        self.min_order_amount_spin.setValue(self.config_manager.get_min_order_amount())
        self.order_timeout_spin.setValue(self.config_manager.get_order_timeout())

        # Strategy
        strategy_type = self.config_manager.get_strategy_type()
        # 콤보박스에서 해당 전략 선택
        for i in range(self.strategy_combo.count()):
            if self.strategy_combo.itemData(i) == strategy_type:
                self.strategy_combo.setCurrentIndex(i)
                break
        
        # 전략 설명 업데이트
        self._on_strategy_changed(self.strategy_combo.currentIndex())

    def _save_settings(self):
        """설정 저장"""
        try:
            # Upbit API 저장
            success = self.config_manager.set_upbit_keys(
                self.access_key_edit.text().strip(),
                self.secret_key_edit.text().strip()
            )

            if not success:
                QMessageBox.warning(self, "저장 실패", "Upbit API 키 저장에 실패했습니다.")
                return

            # Telegram 저장
            success = self.config_manager.set_telegram_config(
                self.bot_token_edit.text().strip(),
                self.chat_id_edit.text().strip()
            )

            if not success:
                QMessageBox.warning(self, "저장 실패", "Telegram 설정 저장에 실패했습니다.")
                return

            # Trading 설정 저장
            success = self.config_manager.set_trading_config(
                self.min_order_amount_spin.value(),
                self.order_timeout_spin.value()
            )

            if not success:
                QMessageBox.warning(self, "저장 실패", "거래 설정 저장에 실패했습니다.")
                return

            # Strategy 설정 저장
            strategy_type = self.strategy_combo.currentData()
            success = self.config_manager.set_strategy_type(strategy_type)

            if not success:
                QMessageBox.warning(self, "저장 실패", "전략 설정 저장에 실패했습니다.")
                return

            # 성공 메시지
            strategy_name = self.strategy_combo.currentText()
            QMessageBox.information(
                self,
                "저장 완료",
                f"✅ 모든 설정이 저장되었습니다.\n\n"
                f"전략: {strategy_name}\n"
                f"설정이 .env 파일에 저장되었습니다."
            )

            # 설정 변경 시그널 발생
            self.settings_changed.emit()

            # 다이얼로그 닫기
            self.accept()

        except Exception as e:
            QMessageBox.critical(
                self,
                "오류",
                f"설정 저장 중 오류가 발생했습니다:\n{str(e)}"
            )

    # ========================================
    # 테스트 기능
    # ========================================

    def _test_connection(self):
        """연결 테스트"""
        current_tab = self.tabs.currentIndex()

        if current_tab == 0:  # Upbit API
            self._test_upbit()
        elif current_tab == 1:  # Telegram
            self._test_telegram()
        else:
            QMessageBox.information(self, "안내", "해당 탭에는 테스트 기능이 없습니다.")

    def _test_upbit(self):
        """Upbit API 연결 테스트"""
        access_key = self.access_key_edit.text().strip()
        secret_key = self.secret_key_edit.text().strip()

        if not access_key or not secret_key:
            QMessageBox.warning(self, "입력 오류", "Access Key와 Secret Key를 입력하세요.")
            return

        # 간단한 형식 검증
        if len(access_key) < 20 or len(secret_key) < 20:
            QMessageBox.warning(
                self,
                "형식 오류",
                "API 키 형식이 올바르지 않습니다.\n"
                "Upbit에서 발급받은 키를 정확히 입력하세요."
            )
            return

        # 실제 API 테스트 (core/upbit_api.py 사용)
        try:
            from core.upbit_api import UpbitAPI

            api = UpbitAPI(access_key, secret_key)
            accounts = api.get_accounts()

            if accounts:
                QMessageBox.information(
                    self,
                    "연결 성공",
                    f"✅ Upbit API 연결 성공!\n\n"
                    f"계좌 정보: {len(accounts)}개 자산 조회됨"
                )
            else:
                QMessageBox.warning(
                    self,
                    "연결 실패",
                    "❌ API 키는 유효하지만 계좌 정보를 가져올 수 없습니다."
                )

        except Exception as e:
            QMessageBox.critical(
                self,
                "연결 실패",
                f"❌ Upbit API 연결 실패:\n{str(e)}\n\n"
                f"API 키를 확인하세요."
            )

    def _test_telegram(self):
        """Telegram 알림 테스트"""
        bot_token = self.bot_token_edit.text().strip()
        chat_id = self.chat_id_edit.text().strip()

        if not bot_token or not chat_id:
            QMessageBox.warning(self, "입력 오류", "Bot Token과 Chat ID를 입력하세요.")
            return

        # 형식 검증
        if ':' not in bot_token:
            QMessageBox.warning(
                self,
                "형식 오류",
                "Bot Token 형식이 올바르지 않습니다.\n"
                "형식: 숫자:영문숫자 (예: 123456789:ABC-DEF1234)"
            )
            return

        # 실제 Telegram 테스트
        try:
            import asyncio
            from core.telegram_bot import TelegramBot

            async def send_test_message():
                bot = TelegramBot(bot_token, chat_id)
                await bot.send_message(
                    "🧪 **테스트 메시지**\n\n"
                    "Upbit DCA Trader GUI에서 전송한 테스트 알림입니다.\n"
                    "이 메시지가 보이면 설정이 올바릅니다! ✅"
                )

            asyncio.run(send_test_message())

            QMessageBox.information(
                self,
                "전송 성공",
                "✅ Telegram 테스트 메시지 전송 성공!\n\n"
                "Telegram 앱에서 메시지를 확인하세요."
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "전송 실패",
                f"❌ Telegram 메시지 전송 실패:\n{str(e)}\n\n"
                "Bot Token과 Chat ID를 확인하세요."
            )


# 테스트 코드
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    dialog = SettingsDialog()
    dialog.show()

    sys.exit(app.exec())
