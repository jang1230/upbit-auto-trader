#!/usr/bin/env python3
"""
Upbit DCA Auto-Trading Program
메인 진입점 - GUI 모드 및 헤드리스 모드 지원

PyInstaller 호환성:
- sys.frozen 체크로 패키징 환경 감지
- 상대 경로 처리
- 멀티프로세싱 지원
"""

import sys
import argparse
import logging
from pathlib import Path
from typing import Optional

# PyInstaller 멀티프로세싱 지원
if sys.platform.startswith('win'):
    import multiprocessing
    multiprocessing.freeze_support()


def setup_logging(log_level: str = 'INFO', log_file: Optional[Path] = None):
    """
    로깅 설정

    Args:
        log_level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR)
        log_file: 로그 파일 경로 (None이면 콘솔만)
    """
    # PyInstaller 환경에서 기본 경로 설정
    if getattr(sys, 'frozen', False):
        base_path = Path(sys.executable).parent
    else:
        base_path = Path(__file__).parent

    # 로그 디렉토리
    log_dir = base_path / 'logs'
    log_dir.mkdir(exist_ok=True)

    # 로그 파일 경로
    if log_file is None:
        log_file = log_dir / 'upbit_dca.log'

    # 로거 설정
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))

    # 포매터
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 파일 핸들러
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logging.info("=" * 60)
    logging.info("Upbit DCA Auto-Trading Program")
    logging.info("=" * 60)


def run_gui_mode():
    """
    GUI 모드 실행
    """
    logging.info("🖥️ GUI 모드 시작")

    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt
        from gui.main_window import MainWindow

        # Qt 애플리케이션 생성
        app = QApplication(sys.argv)
        app.setApplicationName("Upbit DCA Trader")
        app.setOrganizationName("UpbitDCA")

        # High DPI 지원
        app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        # 메인 윈도우 생성
        window = MainWindow()
        window.show()

        logging.info("✅ GUI 애플리케이션 시작")
        return app.exec()

    except ImportError as e:
        logging.error(f"❌ GUI 모듈 import 실패: {e}")
        logging.error("PySide6가 설치되지 않았습니다. pip install PySide6")
        return 1
    except Exception as e:
        logging.error(f"❌ GUI 실행 실패: {e}", exc_info=True)
        return 1


def run_headless_mode(args: argparse.Namespace):
    """
    헤드리스 모드 실행 (백그라운드 자동매매)

    Args:
        args: 커맨드 라인 인자
    """
    logging.info("⚙️ 헤드리스 모드 시작")
    logging.info(f"   - 전략: {args.strategy}")
    logging.info(f"   - 심볼: {args.symbol}")
    logging.info(f"   - 드라이런: {args.dry_run}")

    try:
        # TODO: Phase 4 구현 후 활성화
        # from core.trader import AutoTrader
        # from core.strategy import get_strategy

        # # 전략 로드
        # strategy = get_strategy(args.strategy)
        #
        # # 트레이더 초기화
        # trader = AutoTrader(
        #     symbol=args.symbol,
        #     strategy=strategy,
        #     dry_run=args.dry_run
        # )
        #
        # # 자동매매 시작
        # trader.start()

        logging.info("⚠️ 헤드리스 모드는 Phase 4에서 구현됩니다.")
        logging.info("현재는 API 테스트만 가능합니다.")

        # API 테스트
        from api.upbit_api import UpbitAPI
        from utils.security import SecurityManager

        # API 키 로드
        sm = SecurityManager()
        credentials = sm.load_credentials()

        if credentials is None:
            logging.error("❌ 저장된 API 키가 없습니다.")
            logging.info("다음 명령으로 API 키를 저장하세요:")
            logging.info("  python main.py --save-keys")
            return 1

        # API 연결 테스트
        api = UpbitAPI(
            credentials['access_key'],
            credentials['secret_key']
        )

        if api.test_connection():
            logging.info("✅ API 연결 성공")

            # 계좌 정보 조회
            accounts = api.get_accounts()
            logging.info(f"📊 계좌 정보: {len(accounts)}개 자산")

            for account in accounts[:5]:  # 처음 5개만
                currency = account['currency']
                balance = float(account['balance'])
                if balance > 0:
                    logging.info(f"   - {currency}: {balance:,.2f}")
        else:
            logging.error("❌ API 연결 실패")
            return 1

        api.close()
        return 0

    except Exception as e:
        logging.error(f"❌ 헤드리스 모드 실행 실패: {e}", exc_info=True)
        return 1


def save_api_keys_interactive():
    """
    대화형 API 키 저장
    """
    logging.info("🔐 API 키 저장")

    from utils.security import SecurityManager

    print("\n" + "=" * 60)
    print("Upbit API 키 저장")
    print("=" * 60)
    print("API 키는 Upbit 웹사이트에서 발급받을 수 있습니다:")
    print("https://upbit.com/mypage/open_api_management")
    print("=" * 60 + "\n")

    # Access Key 입력
    access_key = input("Access Key: ").strip()
    if not access_key:
        print("❌ Access Key가 입력되지 않았습니다.")
        return 1

    # Secret Key 입력
    from getpass import getpass
    secret_key = getpass("Secret Key (입력 내용 숨김): ").strip()
    if not secret_key:
        print("❌ Secret Key가 입력되지 않았습니다.")
        return 1

    # 형식 검증
    if not SecurityManager.validate_api_keys(access_key, secret_key):
        print("⚠️ 경고: API 키 형식이 올바르지 않을 수 있습니다.")
        confirm = input("계속하시겠습니까? (y/N): ").strip().lower()
        if confirm != 'y':
            print("취소되었습니다.")
            return 0

    # 추가 패스워드 설정 (옵션)
    use_password = input("\n추가 패스워드를 설정하시겠습니까? (y/N): ").strip().lower()
    password = None
    if use_password == 'y':
        password = getpass("패스워드: ").strip()
        password_confirm = getpass("패스워드 확인: ").strip()

        if password != password_confirm:
            print("❌ 패스워드가 일치하지 않습니다.")
            return 1

    # 저장
    sm = SecurityManager()
    if sm.save_credentials(access_key, secret_key, password):
        print("\n✅ API 키가 안전하게 저장되었습니다.")
        print(f"📁 저장 위치: {sm.encrypted_file}")
        return 0
    else:
        print("\n❌ API 키 저장에 실패했습니다.")
        return 1


def delete_api_keys():
    """
    저장된 API 키 삭제
    """
    from utils.security import SecurityManager

    sm = SecurityManager()

    if not sm.credentials_exist():
        print("❌ 저장된 API 키가 없습니다.")
        return 1

    confirm = input("저장된 API 키를 삭제하시겠습니까? (y/N): ").strip().lower()
    if confirm != 'y':
        print("취소되었습니다.")
        return 0

    if sm.delete_credentials():
        print("✅ API 키가 삭제되었습니다.")
        return 0
    else:
        print("❌ API 키 삭제에 실패했습니다.")
        return 1


def run_backtest_mode(args: argparse.Namespace):
    """
    백테스팅 모드 실행

    Args:
        args: 커맨드 라인 인자
    """
    from datetime import datetime, timedelta
    from core.database import CandleDatabase
    from core.data_loader import UpbitDataLoader
    from core.backtester import Backtester
    from core.analyzer import PerformanceAnalyzer
    from api.upbit_api import UpbitAPI

    logging.info("📊 백테스팅 모드 시작")
    logging.info(f"   - 심볼: {args.symbol}")
    logging.info(f"   - 기간: {args.start_date} ~ {args.end_date}")
    logging.info(f"   - 봉 간격: {args.interval}")
    logging.info(f"   - 초기 자금: {args.capital:,.0f}원")

    try:
        # 1. 데이터베이스 및 API 초기화
        db = CandleDatabase()
        api = UpbitAPI('', '')  # 공개 API (키 불필요)
        loader = UpbitDataLoader(api, db)

        # 2. 날짜 파싱
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
        end_date = datetime.strptime(args.end_date, '%Y-%m-%d')

        # 3. 데이터 다운로드 (필요 시)
        logging.info("📥 데이터 확인 중...")
        stored_candles = db.get_candles(args.symbol, args.interval, start_date, end_date)

        if stored_candles.empty or args.force_download:
            logging.info("📥 과거 데이터 다운로드 중...")
            downloaded = loader.batch_download(
                market=args.symbol,
                interval=args.interval,
                start_date=start_date,
                end_date=end_date,
                show_progress=True
            )
            logging.info(f"✅ {downloaded:,}개 캔들 다운로드 완료")

            # 다시 조회
            stored_candles = db.get_candles(args.symbol, args.interval, start_date, end_date)
        else:
            logging.info(f"✅ 저장된 데이터 사용: {len(stored_candles):,}개 캔들")

        if stored_candles.empty:
            logging.error("❌ 데이터가 없습니다.")
            return 1

        # 4. 백테스팅 실행
        # TODO: Phase 2에서 실제 전략 구현 후 수정
        # 현재는 Buy & Hold 더미 전략 사용
        class SimpleStrategy:
            name = f"Buy & Hold ({args.symbol})"

            def __init__(self):
                self.bought = False

            def generate_signal(self, candles):
                # 첫 캔들에서 매수
                if len(candles) == 1 and not self.bought:
                    self.bought = True
                    return 'buy'
                # 마지막 캔들에서 매도
                elif len(candles) == len(stored_candles):
                    return 'sell'
                return None

        strategy = SimpleStrategy()

        logging.info("🔄 백테스팅 실행 중...")
        backtester = Backtester(
            strategy=strategy,
            initial_capital=args.capital,
            fee_rate=0.0005,  # 0.05%
            slippage=0.001     # 0.1%
        )

        result = backtester.run(stored_candles, args.symbol)

        # 5. 성과 분석
        logging.info("📊 성과 분석 중...")
        analyzer = PerformanceAnalyzer(risk_free_rate=0.02)
        report = analyzer.analyze(result)

        # 6. 결과 출력
        analyzer.print_report(report)

        # 7. 정리
        api.close()
        db.close()

        logging.info("✅ 백테스팅 완료")
        return 0

    except Exception as e:
        logging.error(f"❌ 백테스팅 실패: {e}", exc_info=True)
        return 1


def main():
    """
    메인 함수
    """
    parser = argparse.ArgumentParser(
        description='Upbit DCA Auto-Trading Program',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
  # GUI 모드 (기본)
  python main.py

  # 헤드리스 모드 (자동매매)
  python main.py --headless --symbol KRW-BTC --strategy dca_rsi

  # 드라이런 모드 (실제 주문 없이 테스트)
  python main.py --headless --dry-run

  # 백테스팅 모드
  python main.py --backtest --symbol KRW-BTC --start-date 2024-01-01 --end-date 2024-12-31

  # API 키 저장
  python main.py --save-keys

  # API 키 삭제
  python main.py --delete-keys
        """
    )

    # 모드 선택
    parser.add_argument(
        '--headless',
        action='store_true',
        help='헤드리스 모드 (GUI 없이 백그라운드 실행)'
    )

    parser.add_argument(
        '--backtest',
        action='store_true',
        help='백테스팅 모드 (과거 데이터로 전략 검증)'
    )

    # 자동매매 설정
    parser.add_argument(
        '--symbol',
        type=str,
        default='KRW-BTC',
        help='거래 심볼 (기본: KRW-BTC)'
    )

    parser.add_argument(
        '--strategy',
        type=str,
        default='dca_rsi',
        choices=['dca_rsi', 'dca_macd', 'dca_bb'],
        help='거래 전략 (기본: dca_rsi)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='드라이런 모드 (실제 주문 없이 테스트)'
    )

    # 백테스팅 설정
    parser.add_argument(
        '--start-date',
        type=str,
        default='2024-01-01',
        help='백테스팅 시작일 (YYYY-MM-DD, 기본: 2024-01-01)'
    )

    parser.add_argument(
        '--end-date',
        type=str,
        default='2024-12-31',
        help='백테스팅 종료일 (YYYY-MM-DD, 기본: 2024-12-31)'
    )

    parser.add_argument(
        '--interval',
        type=str,
        default='1d',
        choices=['1m', '3m', '5m', '10m', '15m', '30m', '1h', '4h', '1d', '1w'],
        help='캔들 봉 간격 (기본: 1d)'
    )

    parser.add_argument(
        '--capital',
        type=float,
        default=1000000,
        help='초기 자금 (원, 기본: 1,000,000)'
    )

    parser.add_argument(
        '--force-download',
        action='store_true',
        help='저장된 데이터 무시하고 재다운로드'
    )

    # API 키 관리
    parser.add_argument(
        '--save-keys',
        action='store_true',
        help='API 키 저장 (대화형)'
    )

    parser.add_argument(
        '--delete-keys',
        action='store_true',
        help='저장된 API 키 삭제'
    )

    # 로깅 설정
    parser.add_argument(
        '--log-level',
        type=str,
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='로그 레벨 (기본: INFO)'
    )

    args = parser.parse_args()

    # 로깅 초기화
    setup_logging(args.log_level)

    # API 키 관리 명령
    if args.save_keys:
        return save_api_keys_interactive()

    if args.delete_keys:
        return delete_api_keys()

    # 실행 모드 선택
    if args.backtest:
        return run_backtest_mode(args)
    elif args.headless:
        return run_headless_mode(args)
    else:
        return run_gui_mode()


if __name__ == "__main__":
    sys.exit(main())
