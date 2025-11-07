"""
전역 설정 다이얼로그 테스트
"""

import sys
from PySide6.QtWidgets import QApplication
from gui.global_settings_dialog import GlobalSettingsDialog

if __name__ == "__main__":
    app = QApplication(sys.argv)

    dialog = GlobalSettingsDialog()
    dialog.show()

    sys.exit(app.exec())
