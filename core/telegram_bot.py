"""
Telegram Bot
텔레그램 봇 클라이언트

실시간 알림 및 명령어:
- 신호 발생 알림 (매수/매도)
- 주문 체결 알림
- 리스크 관리 이벤트
- 일일 성과 요약
- 명령어: /status, /balance, /stop, /start

Example:
    >>> bot = TelegramBot(token, chat_id)
    >>> await bot.send_signal_alert('buy', 'KRW-BTC', 100000000)
    >>> await bot.send_order_result(order_result)
"""

import asyncio
import logging
from typing import Optional, Dict
from datetime import datetime
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes

logger = logging.getLogger(__name__)


class TelegramBot:
    """
    텔레그램 봇 클라이언트
    
    실시간 알림 및 트레이딩 제어를 위한 봇
    """
    
    def __init__(self, token: str, chat_id: str):
        """
        텔레그램 봇 초기화
        
        Args:
            token: 텔레그램 봇 토큰
            chat_id: 알림을 받을 채팅 ID
        """
        self.token = token
        self.chat_id = chat_id
        self.bot = Bot(token=token)
        self.application = None
        
        # 봇 상태
        self.is_running = False
        self.trading_enabled = True
        
        logger.info("✅ 텔레그램 봇 초기화 완료")
    
    async def start_bot(self):
        """봇 시작 (명령어 핸들러 등록)"""
        if self.is_running:
            logger.warning("⚠️ 봇이 이미 실행 중입니다")
            return
        
        # Application 생성
        self.application = Application.builder().token(self.token).build()
        
        # 명령어 핸들러 등록
        self.application.add_handler(CommandHandler("status", self.cmd_status))
        self.application.add_handler(CommandHandler("balance", self.cmd_balance))
        self.application.add_handler(CommandHandler("stop", self.cmd_stop))
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("help", self.cmd_help))
        
        # 봇 시작
        await self.application.initialize()
        await self.application.start()
        
        self.is_running = True
        logger.info("✅ 텔레그램 봇 시작 완료")
    
    async def stop_bot(self):
        """봇 종료"""
        if not self.is_running:
            return
        
        if self.application:
            await self.application.stop()
            await self.application.shutdown()
        
        self.is_running = False
        logger.info("⏹️ 텔레그램 봇 종료")
    
    async def send_message(self, text: str, parse_mode: str = "Markdown"):
        """
        메시지 전송

        Args:
            text: 메시지 내용
            parse_mode: 파싱 모드 (Markdown, HTML)
        """
        try:
            # 이벤트 루프 체크 및 재생성
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # 이벤트 루프가 없거나 닫혔으면 새로 생성
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                logger.info("🔄 텔레그램 봇: 새로운 이벤트 루프 생성")

            await self.bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode=parse_mode
            )
            logger.info(f"📤 메시지 전송 완료: {text[:50]}...")
        except Exception as e:
            logger.error(f"❌ 메시지 전송 실패: {e}")
    
    async def send_signal_alert(self, signal: str, symbol: str, price: float):
        """
        신호 발생 알림
        
        Args:
            signal: 신호 ('buy' or 'sell')
            symbol: 마켓 코드
            price: 현재 가격
        """
        emoji = "🛒" if signal == "buy" else "💵"
        signal_kr = "매수" if signal == "buy" else "매도"
        
        message = f"""
{emoji} *{signal_kr} 신호 발생!*

📊 마켓: `{symbol}`
💰 가격: `{price:,.0f}원`
⏰ 시각: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`

전략: Bollinger Bands (20, 2.5)
"""
        await self.send_message(message)
    
    async def send_order_result(self, result: Dict):
        """
        주문 체결 알림
        
        Args:
            result: 주문 결과 딕셔너리
        """
        if not result['success']:
            # 실패 알림
            message = f"""
❌ *주문 실패*

마켓: `{result['symbol']}`
타입: `{result['side']}`
에러: `{result.get('error', 'Unknown')}`
시각: `{result['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}`
"""
        else:
            # 성공 알림
            if result['side'] == 'buy':
                message = f"""
✅ *매수 체결 완료!*

📊 마켓: `{result['symbol']}`
💰 금액: `{result['amount']:,.0f}원`
📦 수량: `{result['executed_volume']:.8f}개`
💵 평균가: `{result['executed_price']:,.0f}원`
⏰ 시각: `{result['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}`
"""
            else:
                message = f"""
✅ *매도 체결 완료!*

📊 마켓: `{result['symbol']}`
📦 수량: `{result['volume']:.8f}개`
💰 금액: `{result['executed_funds']:,.0f}원`
💵 평균가: `{result['executed_price']:,.0f}원`
⏰ 시각: `{result['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}`
"""
        
        await self.send_message(message)
    
    async def send_risk_event(self, event_type: str, details: Dict):
        """
        리스크 관리 이벤트 알림
        
        Args:
            event_type: 이벤트 타입 ('stop_loss', 'take_profit', 'daily_loss_limit')
            details: 이벤트 상세 정보
        """
        if event_type == 'stop_loss':
            emoji = "🚨"
            title = "스톱로스 발동"
        elif event_type == 'take_profit':
            emoji = "🎯"
            title = "타겟 프라이스 달성"
        elif event_type == 'daily_loss_limit':
            emoji = "⛔"
            title = "일일 손실 한도 도달"
        elif event_type == 'trailing_stop':
            emoji = "📉"
            title = "트레일링 스톱 발동"
        else:
            emoji = "⚠️"
            title = "리스크 이벤트"
        
        message = f"""
{emoji} *{title}*

📊 마켓: `{details.get('symbol', 'N/A')}`
💰 현재가: `{details.get('price', 0):,.0f}원`
📈 손익률: `{details.get('pnl_pct', 0):+.2f}%`
⏰ 시각: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`

포지션이 자동으로 청산되었습니다.
"""
        await self.send_message(message)
    
    async def send_daily_summary(self, summary: Dict):
        """
        일일 성과 요약
        
        Args:
            summary: 성과 요약 정보
        """
        message = f"""
📊 *일일 성과 요약*

날짜: `{summary.get('date', datetime.now().strftime('%Y-%m-%d'))}`

💰 시작 자본: `{summary.get('start_capital', 0):,.0f}원`
💵 현재 자본: `{summary.get('current_capital', 0):,.0f}원`
📈 수익률: `{summary.get('return_pct', 0):+.2f}%`

📊 거래 통계:
- 총 거래: `{summary.get('total_trades', 0)}회`
- 성공: `{summary.get('winning_trades', 0)}회`
- 실패: `{summary.get('losing_trades', 0)}회`
- 승률: `{summary.get('win_rate', 0):.1f}%`

💸 손익 정보:
- 총 수익: `{summary.get('total_profit', 0):+,.0f}원`
- 총 손실: `{summary.get('total_loss', 0):,.0f}원`
- 순손익: `{summary.get('net_profit', 0):+,.0f}원`
"""
        await self.send_message(message)
    
    # ==================== 명령어 핸들러 ====================
    
    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /status - 현재 상태 조회
        """
        # TODO: Trading Engine에서 실제 상태 가져오기
        message = f"""
📊 *트레이딩 봇 상태*

🤖 봇 상태: `{'실행 중' if self.is_running else '중단'}`
📈 트레이딩: `{'활성화' if self.trading_enabled else '비활성화'}`

💰 현재 포지션: `없음`
📊 전략: `Bollinger Bands (20, 2.5)`
⏰ 업데이트: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`
"""
        await update.message.reply_text(message, parse_mode="Markdown")
    
    async def cmd_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /balance - 계좌 잔고 조회
        """
        # TODO: Upbit API에서 실제 잔고 가져오기
        message = f"""
💰 *계좌 잔고*

KRW: `1,000,000원`
BTC: `0.00000000개`

📊 총 자산: `1,000,000원`
⏰ 조회 시각: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`
"""
        await update.message.reply_text(message, parse_mode="Markdown")
    
    async def cmd_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /stop - 트레이딩 중단
        """
        self.trading_enabled = False
        logger.info("⏸️ 트레이딩 중단 (사용자 명령)")
        
        message = "⏸️ *트레이딩 중단*\n\n자동 매매가 중단되었습니다.\n재개하려면 /start 명령을 사용하세요."
        await update.message.reply_text(message, parse_mode="Markdown")
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /start - 트레이딩 재개
        """
        self.trading_enabled = True
        logger.info("▶️ 트레이딩 재개 (사용자 명령)")
        
        message = "▶️ *트레이딩 재개*\n\n자동 매매가 재개되었습니다."
        await update.message.reply_text(message, parse_mode="Markdown")
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /help - 도움말
        """
        message = """
📖 *사용 가능한 명령어*

/status - 현재 트레이딩 봇 상태 조회
/balance - 계좌 잔고 조회
/stop - 트레이딩 중단 (포지션 유지)
/start - 트레이딩 재개
/help - 이 도움말 표시

📊 *알림 종류*
- 신호 발생 (매수/매도)
- 주문 체결 (성공/실패)
- 리스크 관리 (스톱로스, 타겟 등)
- 일일 성과 요약
"""
        await update.message.reply_text(message, parse_mode="Markdown")


# 테스트 코드
if __name__ == "__main__":
    """테스트: 텔레그램 봇 메시지 전송"""
    import os
    from dotenv import load_dotenv
    
    print("=== Telegram Bot 테스트 ===\n")
    
    # .env 파일에서 토큰 로드
    load_dotenv()
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not token or not chat_id:
        print("❌ 텔레그램 설정이 없습니다.")
        print("   .env 파일에 TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID를 설정하세요.")
        print("\n설정 방법:")
        print("1. @BotFather에게 /newbot 명령으로 봇 생성")
        print("2. 받은 토큰을 TELEGRAM_BOT_TOKEN에 설정")
        print("3. 봇과 대화 시작 후 chat_id 확인 (https://api.telegram.org/bot<TOKEN>/getUpdates)")
        exit(1)
    
    async def test_telegram_bot():
        bot = TelegramBot(token, chat_id)
        
        # 1. 시작 메시지
        print("1. 시작 메시지 전송")
        await bot.send_message("🤖 *Upbit DCA Trader 테스트*\n\n텔레그램 봇 연동 테스트입니다.")
        print("   ✅ 전송 완료\n")
        
        await asyncio.sleep(1)
        
        # 2. 신호 알림 테스트
        print("2. 매수 신호 알림 테스트")
        await bot.send_signal_alert('buy', 'KRW-BTC', 100000000)
        print("   ✅ 전송 완료\n")
        
        await asyncio.sleep(1)
        
        # 3. 주문 체결 알림 테스트
        print("3. 주문 체결 알림 테스트")
        order_result = {
            'success': True,
            'order_id': 'test_order_123',
            'symbol': 'KRW-BTC',
            'side': 'buy',
            'amount': 10000,
            'executed_volume': 0.0001,
            'executed_price': 100000000,
            'timestamp': datetime.now()
        }
        await bot.send_order_result(order_result)
        print("   ✅ 전송 완료\n")
        
        await asyncio.sleep(1)
        
        # 4. 리스크 이벤트 알림 테스트
        print("4. 스톱로스 알림 테스트")
        risk_event = {
            'symbol': 'KRW-BTC',
            'price': 95000000,
            'pnl_pct': -5.0
        }
        await bot.send_risk_event('stop_loss', risk_event)
        print("   ✅ 전송 완료\n")
        
        await asyncio.sleep(1)
        
        # 5. 일일 요약 테스트
        print("5. 일일 성과 요약 테스트")
        summary = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'start_capital': 1000000,
            'current_capital': 1050000,
            'return_pct': 5.0,
            'total_trades': 10,
            'winning_trades': 7,
            'losing_trades': 3,
            'win_rate': 70.0,
            'total_profit': 80000,
            'total_loss': -30000,
            'net_profit': 50000
        }
        await bot.send_daily_summary(summary)
        print("   ✅ 전송 완료\n")
        
        print("✅ 모든 테스트 완료")
        print("\n📱 텔레그램 앱에서 메시지를 확인하세요!")
    
    # 비동기 테스트 실행
    asyncio.run(test_telegram_bot())
