"""
Upbit API 직접 호출 테스트
XRP가 정말 API에서 반환되는지 확인
"""

from core.upbit_api import UpbitAPI
from gui.config_manager import ConfigManager
import json

# API 키 로드
config_mgr = ConfigManager()
access_key = config_mgr.get_upbit_access_key()
secret_key = config_mgr.get_upbit_secret_key()

# UpbitAPI 호출
api = UpbitAPI(access_key, secret_key)
accounts = api.get_accounts()

print("=" * 80)
print("📊 Upbit API 계좌 조회 결과")
print("=" * 80)
print(f"총 자산 개수: {len(accounts)}개\n")

for account in accounts:
    currency = account['currency']
    balance = float(account['balance'])
    locked = float(account['locked'])
    avg_buy_price = float(account['avg_buy_price'])

    print(f"🔹 {currency}")
    print(f"   - 보유량 (balance): {balance}")
    print(f"   - 주문 중 (locked): {locked}")
    print(f"   - 평균 매수가: {avg_buy_price:,.0f}")
    print(f"   - 원본 데이터: {account}")
    print()

print("=" * 80)
print("🔍 XRP 관련 자산 검색")
print("=" * 80)

xrp_found = False
for account in accounts:
    if 'XRP' in account['currency']:
        xrp_found = True
        print(f"✅ XRP 발견!")
        print(json.dumps(account, indent=2, ensure_ascii=False))

if not xrp_found:
    print("❌ XRP 자산이 없습니다. (정상)")

print("=" * 80)
