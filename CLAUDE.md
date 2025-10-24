# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Upbit DCA Trader** is an automated cryptocurrency trading bot for the Upbit exchange featuring:
- Multiple trading strategies (Bollinger Bands, RSI, MACD, Hybrid strategies)
- DCA (Dollar Cost Averaging) with risk management
- Real-time trading via WebSocket + REST API
- Telegram notifications
- Comprehensive backtesting framework
- GUI for configuration and monitoring

**Language**: Python 3.8+
**Primary Use**: Korean cryptocurrency market (KRW trading pairs)

---

## Key Commands

### Running the Application

```bash
# Launch GUI (main application)
python main.py

# Run backtesting
python backtest/run_backtest.py
python backtest/run_dca_backtest.py

# Run DCA parameter optimization
python backtest/optimize_dca_parameters.py
python backtest/optimize_dca_hybrid_strategies.py

# Collect historical data
python backtest/safe_data_collector.py
python backtest/collect_historical_sequential.py

# Analyze backtest results
python backtest/analyze_hybrid_results.py
python backtest/visualize_hybrid_results.py
```

### Testing

```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_strategies.py

# Run with coverage
python -m pytest --cov=core --cov=api tests/
```

### Building (Windows .exe)

```bash
# Install PyInstaller
pip install pyinstaller

# Build directory-based executable (recommended)
pyinstaller build_exe.spec

# Output: dist/UpbitDCATrader/UpbitDCATrader.exe
```

See `BUILD_GUIDE.md` for detailed build options.

---

## Architecture Overview

### High-Level Data Flow

```
WebSocket → Data Buffer → Strategy → Risk Manager → Order Manager → Telegram Bot
    ↓           ↓            ↓            ↓              ↓              ↓
Real-time   Candle      Signal      Risk Check    Upbit API       Notifications
 Price      Buffer     Generation   (Stop-loss)   Order Execute
```

### Core Components

**1. Trading Engine (`core/trading_engine.py`)**
- Main orchestrator integrating all components
- Manages trading loop and state
- Coordinates between WebSocket, strategies, risk, and orders
- Entry point: `TradingEngine.start()`

**2. Strategy System (`core/strategies/`)**

Base class: `BaseStrategy` (`core/strategies/base.py`)

Available strategies:

**Currently in Production:**
- `ScalpingStrategy` - MACD + Volume surge (auto-trading, 10 coins)
  - Monitors top 10 marketcap coins automatically
  - 20-30 buy signals per day (all coins combined)
  - Used in `AutoTradingManager` for fully automated trading

**Backtesting (Future Use):**
- `FilteredBBStrategy` - Bollinger Bands with ATR/MA240/Time filters
  - Coin-specific optimized parameters (BTC/ETH/XRP)
  - For mid-long term investment strategy
  - 1-year backtest: +29.13% portfolio return

**Other Strategies (Experimental):**
- `ProximityBBStrategy` - Bollinger Bands proximity detection
- `BinanceMultiSignalStrategy` - Multi-indicator signal system
- `HybridConservativeStrategy`, `HybridBalancedStrategy`, `HybridAggressiveStrategy`, `HybridSmartStrategy`
- `BBStrategy`, `RSIStrategy`, `MACDStrategy`

**Strategy Selection Pattern**:
```python
# Production: ScalpingStrategy (auto-trading)
from core.strategies import ScalpingStrategy

# Top 10 marketcap coins (hardcoded in auto_trading_manager.py)
MARKETCAP_TOP_10 = [
    'KRW-BTC', 'KRW-ETH', 'KRW-USDT', 'KRW-SOL', 'KRW-LINK',
    'KRW-USDC', 'KRW-DOGE', 'KRW-ADA', 'KRW-TRX', 'KRW-XRP'
]

strategy = ScalpingStrategy(
    symbol='KRW-BTC',
    macd_fast=12, macd_slow=26, macd_signal=9,
    volume_threshold=2.0  # 2x average volume
)

# Backtesting: FilteredBBStrategy (mid-long term)
from core.strategies import FilteredBBStrategy

strategy = FilteredBBStrategy(symbol='KRW-BTC')  # BTC params auto-applied
strategy = FilteredBBStrategy(symbol='KRW-ETH')  # ETH params auto-applied
strategy = FilteredBBStrategy(symbol='KRW-XRP')  # XRP params auto-applied
```

**3. Risk Management (`core/risk_manager.py`)**
- Stop-loss enforcement
- Take-profit targets
- Daily loss limits
- Trailing stop (optional)
- Position size management

**4. Order Execution (`core/order_manager.py`)**
- Upbit REST API integration
- Order validation and retry logic
- Dry-run mode support (paper trading)
- Order state tracking

**5. Data Management**
- `core/data_buffer.py` - Real-time candle buffering (max 200 candles)
- `core/data_loader.py` - Historical data loading for backtesting
- `core/historical_data.py` - Historical data management utilities

**6. WebSocket (`core/upbit_websocket.py`)**
- Real-time price/candle streaming from Upbit
- Auto-reconnection with exponential backoff
- 1-minute candle polling

**7. Telegram Integration (`core/telegram_bot.py`)**
- Buy/sell signal notifications
- Order execution results
- Risk event alerts
- Commands: `/status`, `/balance`, `/stop`, `/start`, `/help`

**8. Multi-Coin Trading (`core/multi_coin_trader.py`)**
- Manages multiple coins simultaneously
- Independent position tracking per coin
- Portfolio-level risk management

### Backtesting System

**Architecture**:
```
Data Loader → Backtester → Strategy → Results → Report Generator
     ↓            ↓           ↓          ↓            ↓
Historical   Simulate     Signal    Trade Log    Performance
  Candles    Market     Generation  Tracking      Metrics
```

**Key Files**:
- `backtest/dca_backtest_engine.py` - DCA backtesting engine
- `backtest/backtest_engine.py` - Standard backtesting engine
- `core/dca_backtester.py` - Core DCA backtesting logic
- `core/backtester.py` - Core standard backtesting logic

**Backtest Workflow**:
```python
from backtest.dca_backtest_engine import DCABacktestEngine
from core.strategies import HybridBalancedStrategy

# Load historical data
candles = pd.read_csv('data/historical/KRW-BTC_minute1.csv')

# Create strategy
strategy = HybridBalancedStrategy(symbol='KRW-BTC')

# Run backtest
engine = DCABacktestEngine(
    strategy=strategy,
    initial_capital=1000000,
    profit_target_pct=5.0,
    stop_loss_pct=-7.0,
    max_buys=6,
    buy_interval_pct=10.0
)

result = engine.run(candles)
print(f"Return: {result.total_return}%")
print(f"Win Rate: {result.win_rate}%")
```

---

## Critical Design Patterns

### 1. Strategy Pattern

All strategies inherit from `BaseStrategy` and implement:
```python
class CustomStrategy(BaseStrategy):
    def should_buy(self, candles: pd.DataFrame) -> bool:
        """Return True if buy signal detected"""
        pass

    def should_sell(self, candles: pd.DataFrame) -> bool:
        """Return True if sell signal detected"""
        pass
```

**Important**: In DCA mode, `should_sell()` is NOT used. Selling is controlled by:
- DCA profit target (익절)
- DCA stop loss (손절)
- Risk manager settings

### 2. DCA System Architecture

DCA operates independently from strategy sell signals:

```
Entry: Strategy.should_buy() → Initial Position
  ↓
DCA Levels: Price drops trigger additional buys
  ↓
Exit: Only via profit_target or stop_loss (NOT strategy.should_sell())
```

**DCA Parameters**:
- `profit_target_pct`: Exit when profit reaches this % (e.g., +10%)
- `stop_loss_pct`: Exit when loss exceeds this % (e.g., -10%)
- `buy_interval_pct`: Price drop % to trigger next DCA buy (e.g., -10%)
- `max_buys`: Maximum number of DCA purchases (e.g., 6)

### 3. Hybrid Strategy Pattern

Hybrid strategies combine two base strategies:
```python
class HybridBalancedStrategy(BaseStrategy):
    def __init__(self, symbol, **kwargs):
        # Combine ProximityBB + BinanceMultiSignal
        self.proximity_bb = ProximityBBStrategy(symbol, **kwargs)
        self.binance_signal = BinanceMultiSignalStrategy(symbol, **kwargs)

    def should_buy(self, candles):
        # Require BOTH strategies to agree
        return (self.proximity_bb.should_buy(candles) and
                self.binance_signal.should_buy(candles))
```

---

## Data File Locations

### Configuration
- `config/settings.json` - Main settings (created by GUI)
- `config/api_keys.json` - Encrypted API keys (DO NOT commit)
- `.env` - Environment variables (DO NOT commit)

### Historical Data
- `data/historical/` - Downloaded candle data
  - Format: `{SYMBOL}_minute1_{START}_{END}.csv`
  - Example: `KRW-BTC_minute1_20240101_20241231.csv`

### Backtest Results
- `backtest_results/` - CSV files with backtest results
- `backtest_results/charts/` - Visualization PNG files
- `backtest_results/README_백테스트결과요약.md` - Results summary

### Logs
- `logs/` - Application logs
  - `historical_collection_*.log` - Data collection logs
  - `trading_*.log` - Trading session logs

### Reports
- `reports/` - Generated performance reports

---

## Common Development Workflows

### Adding a New Strategy

1. Create new file in `core/strategies/`:
```python
# core/strategies/my_strategy.py
from core.strategies.base import BaseStrategy
import pandas as pd

class MyStrategy(BaseStrategy):
    def __init__(self, symbol: str, param1: float = 20, param2: float = 2.0):
        super().__init__(symbol)
        self.param1 = param1
        self.param2 = param2

    def should_buy(self, candles: pd.DataFrame) -> bool:
        # Implement buy logic
        return False

    def should_sell(self, candles: pd.DataFrame) -> bool:
        # Implement sell logic (NOTE: Not used in DCA mode)
        return False
```

2. Register in `core/strategies/__init__.py`:
```python
from .my_strategy import MyStrategy

__all__ = [..., 'MyStrategy']
```

3. Add to GUI strategy list in `gui/settings_dialog.py`

4. Backtest before use:
```bash
python backtest/run_dca_backtest.py
```

### Running DCA Parameter Optimization

To find optimal DCA parameters for a strategy:

```bash
# Optimize for specific strategy
python backtest/optimize_dca_parameters.py

# Optimize hybrid strategies (4 strategies × 9 DCA configs × 3 coins = 108 tests)
python backtest/optimize_dca_hybrid_strategies.py
```

Results saved to `backtest_results/` with timestamp.

### Collecting New Historical Data

```bash
# Interactive collection with checkpoint support
python backtest/safe_data_collector.py

# Sequential collection for multiple coins
python backtest/collect_historical_sequential.py
```

**Important**: Data collection uses checkpoints to resume after interruption. Checkpoint files stored in `data/checkpoints/`.

---

## Important Constraints and Gotchas

### 1. Strategy Sell Signals vs DCA Exits

**Critical**: When using DCA mode, strategy `should_sell()` is IGNORED.

- ❌ Wrong: Expecting strategy to trigger profit-taking
- ✅ Correct: Configure DCA `profit_target_pct` and `stop_loss_pct`

### 2. Strategy-Specific Coin Handling

**ScalpingStrategy** (currently in production):
- **All coins use identical parameters**: MACD(12,26,9), volume threshold 2.0x
- **Monitored coins**: Top 10 marketcap (hardcoded in `auto_trading_manager.py:30-42`)
- No coin-specific optimization needed

**FilteredBBStrategy** (backtesting, mid-long term):
- **Coin-specific optimized parameters**:
  - BTC: `std=2.0, wait=6h, atr=0.3`
  - ETH: `std=2.5, wait=10h, atr=0.4`
  - XRP: `std=2.0, wait=6h, atr=0.3`
- Parameters auto-applied based on `symbol` parameter
- Do NOT manually override unless backtesting new parameters

### 3. Data Collection Rate Limiting

Upbit API has rate limits:
- Use 1-second delay between requests (implemented in collectors)
- Use checkpoint files to resume interrupted collections
- Sequential collection for multiple coins to avoid API bans

### 4. WebSocket Reconnection

WebSocket connections can drop. The system handles this with:
- Exponential backoff reconnection
- State preservation
- Automatic recovery

Do NOT manually restart WebSocket - it's handled automatically.

### 5. Dry Run vs Live Trading

**Dry Run Mode** (Paper Trading):
- No real orders executed
- Uses real market data
- Simulates order fills
- Perfect for testing strategies

**Live Trading Mode**:
- Real money at risk
- Requires Upbit API keys
- Irreversible transactions

Always test in Dry Run for minimum 1 week before going live.

### 6. Telegram Bot Setup

Telegram bot is **required** for monitoring. Without it:
- No notifications of trades
- No remote control
- Difficult to monitor 24/7 operation

See `docs/TELEGRAM_설정_가이드.md` for setup.

### 7. Backtest Data Requirements

For accurate backtesting:
- Minimum 6 months of data recommended
- 1-minute candle resolution
- Complete data (no gaps)
- Multiple market conditions (bull, bear, sideways)

---

## Security Considerations

### API Keys
- Stored encrypted in `config/api_keys.json`
- NEVER commit API keys to git
- Use read-only keys for testing
- Rotate keys regularly

### File Exclusions
Already in `.gitignore`:
- `config/api_keys.json`
- `config/settings.json`
- `.env`
- `data/historical/*.csv`
- `logs/*.log`

### Telegram Bot Token
- Keep bot token secret
- Do not share Chat ID
- Bot can execute trades - secure access

---

## Performance Optimization

### Backtesting
- Use vectorized operations (pandas/numpy)
- Avoid loops where possible
- Cache indicator calculations
- Use checkpoint files for long-running optimizations

### Data Buffer
- Limited to 200 candles (configurable)
- Older candles automatically dropped
- Sufficient for most technical indicators

### WebSocket
- Single connection per coin
- Message batching for efficiency
- Background thread processing

---

## References

- **README.md** - Complete project documentation
- **BUILD_GUIDE.md** - Windows executable build instructions
- **PHASE_3_완료_보고서.md** - Phase 3 completion report (system architecture)
- **docs/TELEGRAM_설정_가이드.md** - Telegram setup guide
- **FAQ.md** - Frequently asked questions

---

## Development Notes

### Project Status
- Phase 3 Complete (Real-time trading system)
- Phase 3.8 Complete (Strategy optimization)
- Ready for paper trading and live deployment

### Next Steps
1. Paper trading validation (minimum 1 week)
2. Performance monitoring
3. Gradual live deployment with small capital
4. GitHub repository maintenance

### Known Limitations
- Supports KRW trading pairs only (Upbit Korea)
- 1-minute candle resolution only
- No support for futures/margin trading

## Latest Updates (2025-01-24)

### Phase 4 Complete: GitHub Repository Setup

**Project Cleanup**:
- ✅ Removed 151MB binance extracted folder
- ✅ Cleaned all Python cache files (105 files)
- ✅ Organized screenshots to `docs/screenshots/`
- ✅ Moved design documents to `docs/design/`
- ✅ Root directory completely cleaned

**Documentation Created**:
- ✅ `INSTALLATION.md` - Step-by-step installation guide
  - System requirements
  - Python installation for Windows/macOS/Linux
  - Virtual environment setup
  - Dependency installation
  - Verification steps
  - Troubleshooting

- ✅ `ENVIRONMENT_SETUP.md` - Complete configuration guide
  - Upbit API key setup
  - Telegram bot configuration
  - Trading configuration via GUI
  - Development environment setup
  - Production deployment (AWS/cloud)

- ✅ `TROUBLESHOOTING.md` - Common issues and solutions
  - Installation issues
  - API and connection problems
  - GUI issues
  - Trading problems
  - WebSocket issues
  - Telegram issues
  - Performance optimization
  - Emergency procedures

**README.md Updates**:
- ✅ Updated to Phase 4 status
- ✅ Added WebSocket real-time features
- ✅ Added semi-auto and full-auto modes
- ✅ Added auto-balance refresh feature
- ✅ Updated GitHub URLs to https://github.com/jang1230/upbit-auto-trader

**Ready for GitHub Push**:
- Clean project structure
- Comprehensive documentation
- Professional setup for contributors
- Clear installation and setup process
