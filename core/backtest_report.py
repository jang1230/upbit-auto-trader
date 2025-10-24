"""
Backtest Report Generator
백테스팅 결과 리포트 생성

주요 기능:
- 성과 지표 표시
- 거래 내역 분석
- 결과 저장 (JSON, CSV)
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional
import pandas as pd
from core.backtester import BacktestResult

logger = logging.getLogger(__name__)


class BacktestReportGenerator:
    """
    백테스팅 결과 리포트 생성기

    결과를 보기 좋게 포맷팅하고 파일로 저장합니다.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        """
        초기화

        Args:
            output_dir: 출력 디렉토리 (None이면 프로젝트 루트/reports)
        """
        if output_dir is None:
            project_root = Path(__file__).parent.parent
            output_dir = project_root / 'reports'

        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Backtest Report Generator 초기화")
        logger.info(f"  출력 디렉토리: {self.output_dir}")

    def generate_report(
        self,
        result: BacktestResult,
        save_to_file: bool = True
    ) -> str:
        """
        백테스팅 결과 리포트 생성

        Args:
            result: 백테스팅 결과
            save_to_file: 파일 저장 여부

        Returns:
            str: 리포트 텍스트
        """
        logger.info(f"📊 백테스팅 리포트 생성")

        # 리포트 텍스트 생성
        report_lines = []

        # 헤더
        report_lines.append("=" * 80)
        report_lines.append("백테스팅 결과 리포트")
        report_lines.append("=" * 80)
        report_lines.append("")

        # 기본 정보
        report_lines.append("## 📋 기본 정보")
        report_lines.append(f"전략: {result.strategy_name}")
        report_lines.append(f"심볼: {result.symbol}")
        report_lines.append(f"기간: {result.start_date} ~ {result.end_date}")
        report_lines.append(f"실행 ID: {result.run_id}")
        report_lines.append("")

        # 자금 정보
        report_lines.append("## 💰 자금 정보")
        report_lines.append(f"초기 자산: {result.initial_capital:,.0f}원")
        report_lines.append(f"최종 자산: {result.final_capital:,.0f}원")
        report_lines.append(f"손익: {result.final_capital - result.initial_capital:+,.0f}원")
        report_lines.append(f"수익률: {result.total_return:+.2f}%")
        report_lines.append("")

        # 성과 지표
        report_lines.append("## 📊 성과 지표")
        report_lines.append(f"MDD (최대 낙폭): {result.max_drawdown:.2f}%")
        report_lines.append(f"샤프 비율: {result.sharpe_ratio:.2f}")
        report_lines.append(f"승률: {result.win_rate:.1f}%")
        report_lines.append("")

        # 거래 통계
        report_lines.append("## 📈 거래 통계")
        report_lines.append(f"총 거래 수: {result.total_trades}회")
        report_lines.append(f"승리 거래: {result.winning_trades}회")
        report_lines.append(f"손실 거래: {result.losing_trades}회")
        report_lines.append(f"평균 수익: {result.avg_profit:+,.0f}원")
        report_lines.append(f"평균 손실: {-result.avg_loss:+,.0f}원")

        if result.winning_trades > 0 and result.losing_trades > 0:
            profit_loss_ratio = result.avg_profit / result.avg_loss
            report_lines.append(f"손익비: {profit_loss_ratio:.2f}")

        report_lines.append("")

        # 거래 내역 요약
        if result.trades:
            report_lines.append("## 📝 거래 내역 요약 (최근 10건)")
            report_lines.append("")

            for i, trade in enumerate(result.trades[-10:], 1):
                timestamp = trade['timestamp']
                side = trade['side']
                price = trade['price']
                amount = trade['amount']
                reason = trade.get('reason', '')

                side_emoji = "🔴" if side == 'buy' else "🔵"
                side_text = "매수" if side == 'buy' else "매도"

                report_lines.append(
                    f"{i}. {side_emoji} {side_text}: {timestamp} | "
                    f"{price:,.0f}원 × {amount:.8f} | {reason}"
                )

            report_lines.append("")

        # 평가
        report_lines.append("## 💡 종합 평가")

        if result.total_return > 0:
            report_lines.append("✅ 수익 발생 전략")
        else:
            report_lines.append("❌ 손실 발생 전략")

        if result.max_drawdown < 10:
            report_lines.append("✅ 낮은 MDD (안정적)")
        elif result.max_drawdown < 20:
            report_lines.append("⚠️ 중간 MDD (보통)")
        else:
            report_lines.append("❌ 높은 MDD (위험)")

        if result.sharpe_ratio > 1.0:
            report_lines.append("✅ 높은 샤프 비율 (우수)")
        elif result.sharpe_ratio > 0.5:
            report_lines.append("⚠️ 보통 샤프 비율")
        else:
            report_lines.append("❌ 낮은 샤프 비율")

        if result.win_rate > 50:
            report_lines.append("✅ 높은 승률")
        else:
            report_lines.append("⚠️ 낮은 승률 (손익비 확인 필요)")

        report_lines.append("")

        # 푸터
        report_lines.append("=" * 80)
        report_lines.append(f"리포트 생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("=" * 80)

        # 리포트 텍스트 생성
        report_text = "\n".join(report_lines)

        # 파일 저장
        if save_to_file:
            self.save_report(result, report_text)

        return report_text

    def save_report(self, result: BacktestResult, report_text: str):
        """
        리포트 파일 저장

        Args:
            result: 백테스팅 결과
            report_text: 리포트 텍스트
        """
        # 파일명 생성
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"backtest_{result.symbol}_{timestamp}"

        # 1. 텍스트 리포트 저장
        txt_path = self.output_dir / f"{filename}.txt"
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(report_text)
        logger.info(f"  💾 텍스트 리포트 저장: {txt_path.name}")

        # 2. JSON 저장 (전체 데이터)
        json_data = {
            'run_id': result.run_id,
            'symbol': result.symbol,
            'strategy_name': result.strategy_name,
            'start_date': result.start_date.strftime('%Y-%m-%d %H:%M:%S'),
            'end_date': result.end_date.strftime('%Y-%m-%d %H:%M:%S'),
            'initial_capital': result.initial_capital,
            'final_capital': result.final_capital,
            'total_return': result.total_return,
            'max_drawdown': result.max_drawdown,
            'sharpe_ratio': result.sharpe_ratio,
            'win_rate': result.win_rate,
            'total_trades': result.total_trades,
            'winning_trades': result.winning_trades,
            'losing_trades': result.losing_trades,
            'avg_profit': result.avg_profit,
            'avg_loss': result.avg_loss,
            'trades': [
                {
                    'timestamp': trade['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                    'side': trade['side'],
                    'price': trade['price'],
                    'amount': trade['amount'],
                    'fee': trade['fee'],
                    'balance': trade['balance'],
                    'position': trade['position'],
                    'reason': trade.get('reason', '')
                }
                for trade in result.trades
            ]
        }

        json_path = self.output_dir / f"{filename}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        logger.info(f"  💾 JSON 저장: {json_path.name}")

        # 3. CSV 저장 (거래 내역)
        if result.trades:
            trades_df = pd.DataFrame(result.trades)
            csv_path = self.output_dir / f"{filename}_trades.csv"
            trades_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            logger.info(f"  💾 CSV 저장: {csv_path.name}")

        # 4. Equity Curve CSV
        equity_df = pd.DataFrame({
            'equity': result.equity_curve
        })
        equity_csv_path = self.output_dir / f"{filename}_equity.csv"
        equity_df.to_csv(equity_csv_path, index=False, encoding='utf-8-sig')
        logger.info(f"  💾 Equity Curve CSV 저장: {equity_csv_path.name}")

    def print_report(self, result: BacktestResult):
        """
        콘솔에 리포트 출력

        Args:
            result: 백테스팅 결과
        """
        report = self.generate_report(result, save_to_file=False)
        print(report)


# 테스트 코드
if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("=" * 80)
    print("Backtest Report Generator 테스트")
    print("=" * 80)

    # 더미 결과 생성
    from core.backtester import BacktestResult

    dummy_result = BacktestResult(
        run_id="test-123",
        symbol="KRW-BTC",
        strategy_name="Bollinger Bands",
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 31),
        initial_capital=1000000,
        final_capital=1150000,
        total_return=15.0,
        max_drawdown=8.5,
        sharpe_ratio=1.5,
        win_rate=65.0,
        total_trades=20,
        winning_trades=13,
        losing_trades=7,
        avg_profit=25000,
        avg_loss=15000,
        equity_curve=[1000000, 1020000, 1050000, 1100000, 1150000],
        trades=[
            {
                'timestamp': datetime(2024, 1, 1, 10, 0),
                'side': 'buy',
                'price': 85000000,
                'amount': 0.01,
                'fee': 425,
                'balance': 150000,
                'position': 0.01,
                'reason': '초기 진입'
            }
        ]
    )

    # 리포트 생성
    generator = BacktestReportGenerator()
    generator.print_report(dummy_result)

    print("\n" + "=" * 80)
