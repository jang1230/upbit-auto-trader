# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Upbit DCA Trader V4** - Group-based automated cryptocurrency trading bot

**Language**: Python 3.8+
**Primary Use**: Korean cryptocurrency market (KRW trading pairs)
**Architecture**: V4 (Group-based multi-strategy system)

**V4 Key Features**:
- **Group-based configuration** - Unlimited independent trading groups
- **Separate Live/Dry-run** position files
- **Preset-based auto-buy** strategies (Conservative/Balanced/Aggressive)
- **Position loss limit** - 포지션 손실 한도 (24시간 암호화폐 시장에 적합)
- **Multi-level DCA/Profit/Loss** - Independent settings per group
- **Real-time trading** - WebSocket + REST API
- **Telegram notifications**
- **PySide6 GUI** for configuration and monitoring

**V4 Changes from V3**:
- Trading modes: 2 modes (V3) → Unlimited groups (V4)
- Configuration: 2 files (V3) → 1 unified file (V4)
- Coin management: Global (V3) → Group-level (V4)
- Position tracking: 1 file (V3) → 2 files live/dryrun (V4)

---

## Key Commands

### Running the Application

```bash
# Launch V4 GUI (main application)
python main.py

# Check V4 configuration
cat config/trading_config.json

# Check V4 positions
cat data/positions_live.json      # Live mode
cat data/positions_dryrun.json    # Dry-run mode

# Check trade history
cat data/trade_history.json

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

## V4 Architecture

### Overview

V4 introduces a group-based trading system, replacing V3's 2-mode limitation (semi-auto/full-auto) with unlimited independent trading groups.

**Status**: ✅ Phase 1-2 Complete (100%)

### Key Architectural Changes

**V3 → V4 Transition**:
- **Configuration**: Split files → Single unified `trading_config.json`
- **Trading Modes**: 2 modes → Unlimited groups
- **Coin Management**: Global settings → Group-level independence
- **Position Tracking**: Single file → Separate live/dry-run files
- **DCA Management**: Single level → Multi-level profit/loss

### V4 Core Components

**Phase 1: Data Structures (100% Complete)**

1. **ConfigManager** (`core/config_manager.py`, 512 lines)
   - Manages `config/trading_config.json` with dictionary-based groups
   - JSON Schema validation via `config/schemas/trading_config_schema.json`
   - V3→V4 automatic migration support
   - Interface:
     ```python
     config_mgr = ConfigManager()
     config = config_mgr.load_config(auto_migrate=True)
     config_mgr.validate_config(config)
     config_mgr.save_config(config)
     ```

2. **PositionManager** (`core/position_manager.py`, 656 lines)
   - Separate position files for live/dry-run modes
   - CRUD operations: `create_position()`, `update_position()`, `close_position()`
   - DCA management: `add_dca()`, multiple buy levels per position
   - Upbit synchronization: `sync_with_upbit()` for initial balance sync
   - Interface:
     ```python
     pos_mgr = PositionManager(mode="live", upbit_api=api)
     pos_mgr.sync_with_upbit()  # Initial sync
     position = pos_mgr.create_position(group_id, symbol, buy_price, amount)
     pos_mgr.add_dca(position_id, dca_price, dca_amount)
     ```

3. **TradeHistoryManager** (`core/trade_history_manager.py`, 479 lines)
   - Records all trades to `data/trade_history.json`
   - Group-level statistics calculation
   - Interface:
     ```python
     history_mgr = TradeHistoryManager()
     history_mgr.add_trade(group_id, symbol, trade_type, price, amount, profit_loss)
     stats = history_mgr.calculate_statistics(group_id)
     ```

**Phase 2: Backend Core Components (100% Complete)**

4. **GroupManager** (`core/group_manager.py`, 578 lines)
   - Group lifecycle: `create_group()`, `delete_group()`, `update_group_settings()`
   - Coin management: `add_coin_to_group()`, `remove_coin_from_group()`, `move_coin()`
   - Cross-group validation: prevents coin duplication
   - Interface:
     ```python
     group_mgr = GroupManager(config_mgr, pos_mgr)
     group_mgr.create_group("scalping_group", "Scalping BTC/ETH",
                           coins=["KRW-BTC", "KRW-ETH"])
     group_mgr.add_coin_to_group("scalping_group", "KRW-XRP")
     ```

5. **V4AutoBuyStrategy** (`core/strategies/v4_auto_buy_strategy.py`, 456 lines)
   - Preset-based auto-buy strategy: Conservative (4H), Balanced (1H), Aggressive (15min)
   - Technical indicators: RSI (oversold detection), MACD (golden cross), Volume (surge detection)
   - Group-level strategy assignment
   - Interface:
     ```python
     strategy = V4AutoBuyStrategy(
         symbol="KRW-BTC",
         investment_style="balanced"  # or "conservative", "aggressive", "custom"
     )
     if strategy.should_buy(candles):
         # Execute buy
     indicators = strategy.get_indicator_values(candles)
     ```

6. **V4TradingEngine** (`core/v4_trading_engine.py`, 930 lines)
   - Integrates all V4 components
   - Group-level trading loops
   - Position monitoring (60-second polling)
   - Auto-buy strategy execution
   - DCA/Profit/Loss trigger logic
   - Position loss limit enforcement
   - Interface:
     ```python
     engine = V4TradingEngine(config, upbit_api, telegram_bot)
     engine.start()  # Start trading
     engine.stop()   # Stop trading
     ```

### V4 Data Flow

```
ConfigManager → GroupManager → V4TradingEngine
                      ↓              ↓
               PositionManager ← WebSocket
                      ↓              ↓
               TradeHistory     V4AutoBuyStrategy
                                     ↓
                              Risk Check → Order Execution
```

### V4 Configuration Structure

```json
{
  "version": "4.0",
  "mode": "live",
  "groups": {
    "group_1": {
      "name": "Scalping BTC/ETH",
      "coins": ["KRW-BTC", "KRW-ETH"],
      "buy_settings": {
        "investment_style": "aggressive",
        "buy_amount_krw": 50000
      },
      "dca_settings": {
        "enabled": true,
        "levels": [
          {"price_drop_pct": -3.0, "buy_amount_krw": 50000},
          {"price_drop_pct": -6.0, "buy_amount_krw": 100000}
        ]
      },
      "profit_loss_settings": {
        "profit_targets": [
          {"price_ratio": 1.05, "quantity_ratio": 0.5},
          {"price_ratio": 1.10, "quantity_ratio": 1.0}
        ],
        "stop_losses": [
          {"price_ratio": 0.95, "quantity_ratio": 1.0}
        ]
      }
    }
  },
  "position_loss_limit": {
    "enabled": true,
    "limit_pct": -10.0,
    "action": "alert",
    "exclude_observation_groups": true
  }
}
```

### V4 File Locations

**Configuration**:
- `config/trading_config.json` - Unified V4 configuration
- `config/trading_config_template.json` - Template for new configs
- `config/schemas/trading_config_schema.json` - JSON Schema validation

**Runtime Data**:
- `data/positions_live.json` - Live mode positions
- `data/positions_dryrun.json` - Dry-run mode positions
- `data/trade_history.json` - All trade records
- `data/virtual_balances.json` - Dry-run mode balances

**Ignored Files** (`.gitignore`):
- All runtime data files above
- User-specific positions and history

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

## Latest Updates

### V4 Phase 1-2 Complete (2025-01-25)

**Branch**: `claude/gui-detailed-design-prep-011CUpFANut7zsN2Ndg8Qxq9`

**Phase 1: Data Structures (100% Complete)**

Created 5 new files for V4 data management:

1. **core/config_manager.py** (512 lines)
   - Purpose: Unified configuration management for V4
   - Key features: Dictionary-based groups, JSON Schema validation, V3 migration
   - Usage: `ConfigManager().load_config(auto_migrate=True)`

2. **core/position_manager.py** (656 lines)
   - Purpose: Live/Dry-run position tracking with Upbit sync
   - Key features: CRUD operations, DCA management, `sync_with_upbit()`
   - Usage: `PositionManager(mode="live", upbit_api=api)`

3. **core/trade_history_manager.py** (479 lines)
   - Purpose: Trade recording and group-level statistics
   - Key features: Trade logging, performance metrics, JSON persistence
   - Usage: `TradeHistoryManager().add_trade(...)`

4. **config/schemas/trading_config_schema.json**
   - Purpose: JSON Schema for V4 configuration validation
   - Defines: Required fields, types, constraints, group structure

5. **config/trading_config_template.json**
   - Purpose: Template for new V4 configurations
   - Contains: Example group with all settings

**Phase 2: Backend Core (100% Complete)** ✅

Created 3 new files, extended 2 existing files, and completed V4TradingEngine:

6. **core/group_manager.py** (578 lines)
   - Purpose: Group lifecycle and coin management
   - Key features: Create/delete groups, add/remove/move coins, validation
   - Usage: `GroupManager(config_mgr, pos_mgr).create_group(...)`

7. **core/strategies/v4_auto_buy_strategy.py** (456 lines)
   - Purpose: Preset-based auto-buy strategy for groups
   - Key features: 3 presets (Conservative/Balanced/Aggressive), RSI+MACD+Volume
   - Usage: `V4AutoBuyStrategy(symbol, investment_style="balanced")`

8. **core/strategies/__init__.py** (extended)
   - Added: V4AutoBuyStrategy to module exports

**Phase 2: Core Engine (100% Complete)** ✅

9. **core/v4_trading_engine.py** (930 lines)
    - Status: ✅ Complete
    - Purpose: Main trading loop integrating all V4 components
    - Key Features:
      - Group-level trading loops
      - Position monitoring (60-second polling)
      - Auto-buy strategy execution
      - DCA trigger logic (price drop detection)
      - Profit/loss trigger logic
      - Position loss limit enforcement
    - API Integration:
      - ✅ pyupbit 제거 완료 (2025-01-26)
      - ✅ Official Upbit REST API 사용
      - ✅ Rate Limit 준수 (UpbitAPI 통합)

**Phase 2: API Best Practice 적용 (100% Complete)** ✅

10. **Rate Limit 버그 수정** (2025-01-26)
    - REST API 그룹명 불일치 수정
      - "trades" → "trade", "candles" → "candle"
      - `Remaining-Req` 헤더 동기화 정상화
    - WebSocket Rate Limiter 구현
      - 초당 5회, 분당 100회 제한
      - Window-based deque 알고리즘
    - File: core/upbit_api.py, core/upbit_websocket.py

11. **커뮤니티 라이브러리 제거** (2025-01-26)
    - 실거래 코어에서 pyupbit 완전 제거
      - core/v4_trading_engine.py
      - core/upbit_websocket.py (CandleWebSocket)
    - requirements.txt 정리
      - ta 라이브러리 제거 (미사용)
      - pyupbit 용도 명시 (백테스팅 전용)

**Total Work (Phase 1-2)**:
- **Lines of Code**: ~4,400 lines across 11 new files
- **API Integration**: 100% official Upbit REST API
- **Rate Limit**: REST + WebSocket 완벽 구현
- **Community Libraries**: 실거래 코어에서 0개 (완전 제거)
- **Documentation**: Comprehensive docstrings with type hints
- **Design Docs**: 172KB DESIGN_V4_COMPLETE.md with 18 sections

**Key Architectural Decisions**:
1. **Dictionary-based groups**: Flexible, unlimited groups without array constraints
2. **Separate files**: Live/dry-run positions stored separately for isolation
3. **Preset system**: V4AutoBuyStrategy uses presets for ease of use
4. **Upbit sync**: PositionManager can sync with Upbit API for initial state
5. **Official API only**: No community libraries in production core (pyupbit only for backtesting)
6. **Position loss limit**: 24시간 암호화폐 시장에 적합한 포지션 기반 손실 관리

**Optional Improvements (Not Blocking)**:
- ⏳ WebSocket 실시간 통합 (현재 60초 폴링 사용 중, 동작은 정상)
- ⏳ Unit Tests & Integration Testing (안정성 향상용)

**Next Steps**:
1. ✅ Phase 2 완료 (2025-01-26)
2. Phase 3: GUI redesign (3-tab structure, group management dialogs)
3. Phase 4: Integration testing
4. Phase 5: V3→V4 migration and deployment

---

## Upbit 공식 문서 참조

Upbit API 관련 질문 시 **웹사이트를 fetch하지 말고** 로컬 `upbit_docs/` 폴더의 문서를 참조하세요:

| 폴더 | 내용 |
|------|------|
| `upbit_docs/reference/` | API 레퍼런스 (주문, 잔고, 캔들, WebSocket 등) |
| `upbit_docs/docs/` | 가이드 문서 (개발환경, FAQ, 튜토리얼 등) |
| `upbit_docs/changelog/` | API 변경 이력 |

예시:
- 주문 API → `upbit_docs/reference/new-order.md`
- WebSocket 가이드 → `upbit_docs/reference/websocket-guide.md`
- Rate Limit → `upbit_docs/reference/rate-limits.md`

---

## 하네스 시스템 (세션별 진행 관리)

프로젝트 컨텍스트와 작업 기록은 `.claude/` 폴더에서 관리됩니다:

| 파일 | 용도 | 참조 시점 |
|------|------|----------|
| `.claude/PROJECT_CONTEXT.md` | **아키텍처, GUI 관계도, 설정 파일 구분** | 🔴 코드 분석/수정 전 필수 |
| `.claude/PROGRESS_LOG.md` | 세션별 작업 기록, 최근 커밋 | 이어서 작업 시 |
| `.claude/FEATURE_LIST.json` | 기능 상태 (done/planned), 해결된 이슈 | 기능 추가/버그 수정 시 |
| `.claude/SESSION_START.md` | 세션 시작 템플릿 | 새 세션 시작 시 |
| `.claude/HOW_IT_WORKS.md` | 하네스 시스템 사용 가이드 | 시스템 이해 필요 시 |

### PROJECT_CONTEXT.md 주요 내용
- **아키텍처 다이어그램**: V4TradingEngine 중심 구조
- **GUI 컴포넌트 관계도**: MainWindow → Dialog → Worker 관계
- **설정 파일 구분**: `.env` vs `config.json` 역할 분리
- **핵심 모듈 목록**: 파일별 역할 및 수정 횟수
- **알려진 이슈 패턴**: 해결된 버그와 해결책

### 최근 중요 변경 (2025-12 기준)

⚠️ **필수 규칙**:
- `group_id`는 `None` 대신 `"group_null"` 문자열 사용
- WebSocket 메시지 처리 시 `threading.Lock` 필수
- 커밋: `fix:`, `feat:`, `refactor:`, `docs:` 형식

📊 **현재 상태**: Phase 4 초입 (통합 테스트 + 안정화 단계)

---

## 세션 종료 규칙

사용자가 "작업 마무리", "세션 끝", "커밋해줘" 등을 말하면:

1. `.claude/PROGRESS_LOG.md` 맨 위에 아래 양식으로 기록 추가:

## YYYY-MM-DD 세션

### 작업 내용
1. **작업 제목** (`커밋해시`)
   - 상세 내용
   - 파일: 변경된 파일 경로

### 변경된 파일
- 파일 목록

### 다음 세션 권장 작업
1. 다음에 할 일

2. 커밋 메시지 형식: `fix:`, `feat:`, `refactor:`, `docs:`
```

---

## 그러면 이렇게 간단히 말해도 됨
```
작업 끝. 커밋해줘.
