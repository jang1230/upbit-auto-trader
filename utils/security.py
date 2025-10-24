"""
보안 관련 유틸리티 모듈
API 키 암호화/복호화, 안전한 저장 및 관리

PyInstaller 호환성:
- 시스템 keyring 사용하지 않음 (크로스 플랫폼 이슈)
- 파일 기반 암호화 저장 방식 사용
- 하드코딩된 경로 없음, 실행 파일 기준 상대 경로 사용
"""

import os
import sys
import json
import base64
import hashlib
from pathlib import Path
from typing import Optional, Dict
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend


class SecurityManager:
    """
    API 키 암호화 및 안전한 저장 관리

    PyInstaller 패키징 고려사항:
    - 실행 파일의 위치를 기준으로 설정 파일 경로 결정
    - sys._MEIPASS 처리 (임시 압축 해제 경로)
    """

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Args:
            config_dir: 설정 파일 저장 디렉토리 (None이면 자동 감지)
        """
        # PyInstaller 실행 환경 감지
        if getattr(sys, 'frozen', False):
            # PyInstaller로 패키징된 실행 파일
            # sys._MEIPASS: 임시 압축 해제 디렉토리
            # sys.executable: 실행 파일 경로
            self.base_path = Path(sys.executable).parent
        else:
            # 일반 Python 스크립트 실행
            self.base_path = Path(__file__).parent.parent

        # 설정 디렉토리 설정
        if config_dir is None:
            self.config_dir = self.base_path / 'data' / 'config'
        else:
            self.config_dir = config_dir

        # 디렉토리 생성
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # 암호화된 키 저장 파일
        self.encrypted_file = self.config_dir / '.credentials.enc'

        # 마스터 키 파일 (첫 실행 시 생성)
        self.master_key_file = self.config_dir / '.master.key'

        # 마스터 키 초기화
        self._master_key = self._load_or_create_master_key()

    def _load_or_create_master_key(self) -> bytes:
        """
        마스터 암호화 키 로드 또는 생성

        Returns:
            bytes: 마스터 키
        """
        if self.master_key_file.exists():
            # 기존 마스터 키 로드
            with open(self.master_key_file, 'rb') as f:
                return f.read()
        else:
            # 새 마스터 키 생성
            master_key = Fernet.generate_key()

            # 파일로 저장
            with open(self.master_key_file, 'wb') as f:
                f.write(master_key)

            # 파일 권한 설정 (읽기 전용)
            try:
                os.chmod(self.master_key_file, 0o600)
            except Exception:
                pass  # Windows에서는 권한 설정 실패할 수 있음

            return master_key

    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """
        패스워드로부터 암호화 키 유도 (PBKDF2-HMAC)

        Args:
            password: 사용자 패스워드
            salt: Salt 값

        Returns:
            bytes: 유도된 키
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,  # OWASP 권장값 (2023)
            backend=default_backend()
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))

    def save_credentials(self, access_key: str, secret_key: str,
                        password: Optional[str] = None) -> bool:
        """
        API 키를 암호화하여 저장

        Args:
            access_key: Upbit Access Key
            secret_key: Upbit Secret Key
            password: 추가 패스워드 (옵션)

        Returns:
            bool: 저장 성공 여부
        """
        try:
            # 암호화 키 생성
            if password:
                # 패스워드 기반 암호화
                salt = os.urandom(16)
                key = self._derive_key(password, salt)
                fernet = Fernet(key)

                # Salt 저장을 위해 데이터에 포함
                data = {
                    'access_key': access_key,
                    'secret_key': secret_key,
                    'salt': base64.b64encode(salt).decode()
                }
            else:
                # 마스터 키 기반 암호화
                fernet = Fernet(self._master_key)
                data = {
                    'access_key': access_key,
                    'secret_key': secret_key
                }

            # JSON → 암호화
            json_data = json.dumps(data)
            encrypted_data = fernet.encrypt(json_data.encode())

            # 파일 저장
            with open(self.encrypted_file, 'wb') as f:
                f.write(encrypted_data)

            # 파일 권한 설정
            try:
                os.chmod(self.encrypted_file, 0o600)
            except Exception:
                pass

            return True

        except Exception as e:
            print(f"❌ 키 저장 실패: {e}")
            return False

    def load_credentials(self, password: Optional[str] = None) -> Optional[Dict[str, str]]:
        """
        암호화된 API 키 로드

        Args:
            password: 복호화 패스워드 (저장 시 사용한 경우)

        Returns:
            Dict[str, str] | None: {'access_key': ..., 'secret_key': ...} 또는 None
        """
        try:
            if not self.encrypted_file.exists():
                return None

            # 암호화된 데이터 읽기
            with open(self.encrypted_file, 'rb') as f:
                encrypted_data = f.read()

            # 복호화
            if password:
                # 먼저 Salt 추출을 위해 마스터 키로 복호화 시도
                # (Salt가 암호화된 데이터 안에 있음)
                temp_fernet = Fernet(self._master_key)
                try:
                    json_data = temp_fernet.decrypt(encrypted_data).decode()
                    data = json.loads(json_data)

                    if 'salt' in data:
                        # 패스워드 기반 암호화된 데이터
                        salt = base64.b64decode(data['salt'])
                        key = self._derive_key(password, salt)
                        fernet = Fernet(key)

                        # 다시 복호화
                        json_data = fernet.decrypt(encrypted_data).decode()
                        data = json.loads(json_data)

                except Exception:
                    # 마스터 키로 복호화 실패 → 패스워드 기반
                    # Salt 없이는 복호화 불가
                    return None
            else:
                # 마스터 키 기반 복호화
                fernet = Fernet(self._master_key)
                json_data = fernet.decrypt(encrypted_data).decode()
                data = json.loads(json_data)

            return {
                'access_key': data['access_key'],
                'secret_key': data['secret_key']
            }

        except Exception as e:
            print(f"❌ 키 로드 실패: {e}")
            return None

    def delete_credentials(self) -> bool:
        """
        저장된 API 키 삭제

        Returns:
            bool: 삭제 성공 여부
        """
        try:
            if self.encrypted_file.exists():
                self.encrypted_file.unlink()
                return True
            return False
        except Exception as e:
            print(f"❌ 키 삭제 실패: {e}")
            return False

    def credentials_exist(self) -> bool:
        """
        저장된 API 키가 존재하는지 확인

        Returns:
            bool: 존재 여부
        """
        return self.encrypted_file.exists()

    @staticmethod
    def validate_api_keys(access_key: str, secret_key: str) -> bool:
        """
        API 키 형식 검증

        Args:
            access_key: Access Key
            secret_key: Secret Key

        Returns:
            bool: 유효한 형식인지 여부
        """
        # Upbit API 키 형식
        # Access Key: 영문 대문자 + 숫자, 길이 약 20자
        # Secret Key: 영문 대소문자 + 숫자 + 특수문자, 길이 약 40자

        if not access_key or not secret_key:
            return False

        if len(access_key) < 15 or len(secret_key) < 30:
            return False

        # 기본 문자 검증
        if not all(c.isalnum() or c == '-' for c in access_key):
            return False

        return True

    def reset_master_key(self) -> bool:
        """
        마스터 키 재생성 (기존 저장된 키 모두 삭제됨)

        Returns:
            bool: 재생성 성공 여부
        """
        try:
            # 기존 파일 삭제
            if self.master_key_file.exists():
                self.master_key_file.unlink()
            if self.encrypted_file.exists():
                self.encrypted_file.unlink()

            # 새 마스터 키 생성
            self._master_key = self._load_or_create_master_key()

            return True
        except Exception as e:
            print(f"❌ 마스터 키 재생성 실패: {e}")
            return False


def get_security_manager() -> SecurityManager:
    """
    SecurityManager 싱글톤 인스턴스 반환

    Returns:
        SecurityManager: 보안 관리자 인스턴스
    """
    if not hasattr(get_security_manager, '_instance'):
        get_security_manager._instance = SecurityManager()
    return get_security_manager._instance


if __name__ == "__main__":
    """
    테스트 코드
    """
    print("=== Security Manager 테스트 ===\n")

    # SecurityManager 인스턴스 생성
    sm = SecurityManager()

    print(f"📁 설정 디렉토리: {sm.config_dir}")
    print(f"🔐 마스터 키 파일: {sm.master_key_file}")
    print(f"💾 암호화 파일: {sm.encrypted_file}\n")

    # 1. API 키 형식 검증 테스트
    print("1️⃣ API 키 형식 검증 테스트")
    valid = SecurityManager.validate_api_keys(
        "TEST1234567890ABCDEF",
        "secretkey1234567890abcdefghijklmnop"
    )
    print(f"   유효한 형식: {valid}\n")

    # 2. API 키 저장 테스트
    print("2️⃣ API 키 저장 테스트")
    test_access = "TEST_ACCESS_KEY_1234567890"
    test_secret = "TEST_SECRET_KEY_abcdefghijklmnopqrstuvwxyz1234567890"

    success = sm.save_credentials(test_access, test_secret)
    print(f"   저장 결과: {'✅ 성공' if success else '❌ 실패'}\n")

    # 3. API 키 로드 테스트
    print("3️⃣ API 키 로드 테스트")
    credentials = sm.load_credentials()
    if credentials:
        print(f"   ✅ 로드 성공")
        print(f"   Access Key: {credentials['access_key'][:10]}...")
        print(f"   Secret Key: {credentials['secret_key'][:10]}...\n")
    else:
        print(f"   ❌ 로드 실패\n")

    # 4. 패스워드 기반 암호화 테스트
    print("4️⃣ 패스워드 기반 암호화 테스트")
    test_password = "MySecurePassword123!"

    success = sm.save_credentials(test_access, test_secret, password=test_password)
    print(f"   저장 결과: {'✅ 성공' if success else '❌ 실패'}")

    credentials = sm.load_credentials(password=test_password)
    if credentials:
        print(f"   ✅ 로드 성공 (올바른 패스워드)")
    else:
        print(f"   ❌ 로드 실패")

    # 잘못된 패스워드로 시도
    credentials = sm.load_credentials(password="WrongPassword")
    if credentials:
        print(f"   ⚠️ 경고: 잘못된 패스워드로 로드됨")
    else:
        print(f"   ✅ 잘못된 패스워드로 로드 차단됨\n")

    # 5. 키 존재 확인 테스트
    print("5️⃣ 키 존재 확인 테스트")
    exists = sm.credentials_exist()
    print(f"   키 존재 여부: {exists}\n")

    # 6. 키 삭제 테스트
    print("6️⃣ 키 삭제 테스트")
    success = sm.delete_credentials()
    print(f"   삭제 결과: {'✅ 성공' if success else '❌ 실패'}")

    exists = sm.credentials_exist()
    print(f"   키 존재 여부: {exists}\n")

    print("=== 테스트 완료 ===")
