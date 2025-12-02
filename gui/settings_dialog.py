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
    # 설정 로드/저장
    # ========================================

    def _load_settings(self):
        """현재 설정 로드"""
        # Upbit API
        self.access_key_edit.setText(self.config_manager.get_upbit_access_key())
        self.secret_key_edit.setText(self.config_manager.get_upbit_secret_key())

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

            # 성공 메시지
            QMessageBox.information(
                self,
                "저장 완료",
                "✅ Upbit API 설정이 저장되었습니다."
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


# 테스트 코드
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    dialog = SettingsDialog()
    dialog.show()

    sys.exit(app.exec())
