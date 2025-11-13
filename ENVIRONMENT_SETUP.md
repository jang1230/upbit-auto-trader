# Environment Setup Guide

Complete guide for configuring your Upbit DCA Trader environment.

---

## Table of Contents

1. [Configuration Files](#configuration-files)
2. [Upbit API Keys](#upbit-api-keys)
3. [Telegram Bot Setup](#telegram-bot-setup)
4. [Trading Configuration](#trading-configuration)
5. [Development Environment](#development-environment)
6. [Production Deployment](#production-deployment)

---

## Configuration Files

### File Structure (V4)

```
upbit_dca_trader/
├── .env                           # Environment variables (optional)
├── config/
│   ├── trading_config.json        # V4 unified configuration
│   ├── trading_config_template.json  # Template
│   ├── schemas/
│   │   └── trading_config_schema.json  # JSON Schema
│   └── api_keys.json              # Encrypted API keys (GUI-generated)
├── data/
│   ├── positions_live.json        # Live mode positions
│   ├── positions_dryrun.json      # Dry-run mode positions
│   ├── trade_history.json         # Trade records
│   ├── virtual_balances.json      # Dry-run balances
│   ├── daily_snapshot.json        # Daily loss tracking
│   └── historical/                # Downloaded market data
└── logs/                          # Application logs
```

**V4 Key Changes**:
- `trading_config.json` replaces V3's `settings.json` + `auto_trading_config.json`
- Separate position files for live and dry-run modes
- Centralized trade history and statistics

### .env File (Optional)

Create `.env` file in project root for advanced configuration:

```bash
# Upbit API (Optional - can also configure via GUI)
UPBIT_ACCESS_KEY=your_access_key_here
UPBIT_SECRET_KEY=your_secret_key_here

# Telegram Bot (Optional - can also configure via GUI)
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/trading.log

# Trading
DEFAULT_MARKET=KRW-BTC
MIN_ORDER_AMOUNT=5000

# WebSocket
WS_RECONNECT_DELAY=5
WS_MAX_RETRIES=10
```

**⚠️ IMPORTANT**: Never commit `.env` to git! Already in `.gitignore`.

---

## Upbit API Keys

### Paper Trading (Dry Run)
**No API keys needed!** You can test the bot without real money or API keys.

### Real Trading
API keys required only for live trading.

### Step 1: Create Upbit Account

1. Visit: https://upbit.com
2. Sign up and complete KYC verification
3. Enable 2FA for security

### Step 2: Generate API Keys

1. Login to Upbit
2. Go to **My Page** → **Open API Management**
3. Click **Create API Key**

**Required Permissions** (중요!):
```
✅ 자산 조회 (View Balance)
✅ 주문 조회 (View Orders)
✅ 주문 등록/취소 (Create/Cancel Orders)
❌ 출금 (Withdraw) - DO NOT ENABLE!
```

**Security Settings**:
```
IP 제한: Recommended (add your server IP)
유효기간: Set expiration date
알림: Enable email/SMS notifications
```

### Step 3: Save API Keys Securely

**Method 1: GUI Configuration** (Recommended)
1. Open bot: `python main.py`
2. Click **⚙️ 설정 (Settings)**
3. Go to **🔑 API 키** tab
4. Enter Access Key and Secret Key
5. Click **저장 (Save)**

Keys are encrypted and stored in `config/api_keys.json`

**Method 2: .env File** (Advanced)
```bash
# Edit .env file
UPBIT_ACCESS_KEY=AbCdEfGh1234567890...
UPBIT_SECRET_KEY=XyZaBcDe0987654321...
```

### Security Best Practices

```
✅ Enable IP whitelist
✅ Set API key expiration (3-6 months)
✅ Enable email/SMS alerts
✅ Use separate keys for testing
✅ Rotate keys regularly
✅ Never share keys publicly
✅ Backup keys in password manager
❌ Don't commit to git
❌ Don't enable withdrawal permission
❌ Don't share with others
```

---

## Telegram Bot Setup

Telegram notifications are **strongly recommended** for monitoring 24/7 trading.

### Quick Start

1. **Install Telegram** on your phone or desktop
2. **Create Bot** with BotFather
3. **Get Bot Token**
4. **Get Your Chat ID**
5. **Configure in GUI**

### Detailed Steps

#### Step 1: Create Telegram Bot

1. Open Telegram app
2. Search for: `@BotFather`
3. Start conversation
4. Send command: `/newbot`
5. Follow prompts:
   ```
   BotFather: Alright, a new bot. How are we going to call it?
   You: Upbit DCA Trader Bot

   BotFather: Good. Now let's choose a username for your bot.
   You: upbit_dca_trader_bot

   BotFather: Done! Your token is:
   123456789:ABCdefGHIjklMNOpqrsTUVwxyz
   ```

6. **Save the token**! This is your Bot Token.

#### Step 2: Get Chat ID

1. Send any message to your new bot
2. Open browser and visit:
   ```
   https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
   ```
   Replace `<YOUR_BOT_TOKEN>` with actual token

3. Look for `"chat":{"id":123456789}`
4. The number (123456789) is your Chat ID

**Example Response**:
```json
{
  "ok": true,
  "result": [
    {
      "update_id": 123456,
      "message": {
        "chat": {
          "id": 987654321,  ← This is your Chat ID
          "first_name": "Your Name"
        }
      }
    }
  ]
}
```

#### Step 3: Configure in Bot

**Method 1: GUI** (Recommended)
1. Open bot: `python main.py`
2. Click **⚙️ 설정**
3. Go to **📱 텔레그램** tab
4. Enter:
   - Bot Token: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`
   - Chat ID: `987654321`
5. Click **저장**
6. Click **테스트 메시지 전송** to verify

**Method 2: .env File**
```bash
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=987654321
```

### Test Telegram Integration

```bash
# Start bot in dry-run mode
python main.py

# You should receive Telegram message:
"🤖 Upbit DCA Trader 시작
모드: Dry Run
전략: Filtered Bollinger Bands
..."
```

### Telegram Commands

Once configured, you can control bot via Telegram:

```
/status   - 현재 포지션 및 수익률
/balance  - 잔고 조회
/stop     - 트레이딩 중지
/start    - 트레이딩 시작
/help     - 도움말
```

### Troubleshooting Telegram

**Issue: No messages received**
- Check bot token and chat ID are correct
- Send message to bot first before getting updates
- Verify bot is not blocked
- Check internet connection

**Issue: getUpdates returns empty**
- Send any message to your bot
- Refresh the getUpdates URL
- Try incognito/private browser window

See detailed guide: [docs/TELEGRAM_설정_가이드.md](docs/TELEGRAM_설정_가이드.md)

---

## Trading Configuration (V4)

### First Time Setup

Launch GUI to begin V4 configuration:

```bash
python main.py
```

On first run, V4 will:
1. Create `config/trading_config.json` from template
2. Create empty position files
3. Show group management dialog

### Step 1: Create Your First Group

1. **Click "📁 그룹 관리"** (top of GUI)
2. **Click "그룹 추가"**
3. **Enter group name** (e.g., "Bitcoin Trading")
4. **Click "코인 선택"**
   - Select coins (e.g., KRW-BTC, KRW-ETH)
   - Save

### Step 2: Configure Buy Settings

1. **Click "⚙️ 그룹 설정"**
2. **Select buy mode**:
   - 🤖 **자동매수** (Auto-buy) - Recommended for beginners
   - 👤 **수동매수** (Manual-buy) - You buy on Upbit, bot manages DCA/profit/loss
   - 👁️ **관찰 모드** (Observation) - Track only, no trading

3. **If Auto-buy, click "⚙️ 자동매수 설정..."**:
   - **Preset**:
     - 🐢 **Conservative** (4-hour candles) - Stable, long-term
     - ⚖️ **Balanced** (1-hour candles) - Recommended
     - 🚀 **Aggressive** (15-minute candles) - Fast entry, high-risk
   - **Buy amount**: 50,000 KRW (recommended)
   - Save

### Step 3: Configure DCA/Profit/Loss Levels

1. **Click "⚙️ 레벨 상세 설정"**

2. **DCA Tab** (Dollar Cost Averaging):
   ```
   Level 1: -3% drop → Buy 100%
   Level 2: -5% drop → Buy 100%
   Level 3: -7% drop → Buy 100%
   ```

3. **Profit Tab** (Take Profit):
   ```
   Level 1: +5% gain → Sell 50%
   Level 2: +10% gain → Sell 50%
   ```

4. **Loss Tab** (Stop Loss):
   ```
   Level 1: -15% loss → Sell 100%
   ```

5. Save all settings

### Step 4: Set Daily Loss Limit

1. **Edit `config/trading_config.json`**:
```json
{
  "daily_loss_limit": {
    "enabled": true,
    "loss_pct": 10.0,
    "action": "alert",
    "calculation_method": "daily_only"
  }
}
```

**Options**:
- `action`: "alert" (notify only) or "liquidate" (sell all)
- `calculation_method`: "daily_only" (09:00 reset) or "total_account" (cumulative)

### Step 5: Set Mode (Dry-run or Live)

**For testing (recommended)**:
```json
{
  "mode": "dryrun"
}
```

**For live trading** (only after 1 week dry-run):
```json
{
  "mode": "live"
}
```

### Example V4 Configuration

**config/trading_config.json**:
```json
{
  "version": "4.0",
  "mode": "dryrun",
  "groups": {
    "group_1": {
      "name": "Bitcoin Trading",
      "coins": ["KRW-BTC", "KRW-ETH"],
      "buy_settings": {
        "mode": "auto",
        "auto_config": {
          "enabled": true,
          "investment_style": "balanced",
          "candle_unit": "60",
          "buy_amount_krw": 50000
        }
      },
      "dca_settings": {
        "mode": "auto",
        "levels": [
          {"price_ratio": -3.0, "quantity_ratio": 100},
          {"price_ratio": -5.0, "quantity_ratio": 100},
          {"price_ratio": -7.0, "quantity_ratio": 100}
        ]
      },
      "profit_settings": {
        "mode": "auto",
        "levels": [
          {"price_ratio": 5.0, "quantity_ratio": 50},
          {"price_ratio": 10.0, "quantity_ratio": 50}
        ]
      },
      "loss_settings": {
        "mode": "auto",
        "levels": [
          {"price_ratio": -15.0, "quantity_ratio": 100}
        ]
      }
    }
  },
  "daily_loss_limit": {
    "enabled": true,
    "loss_pct": 10.0,
    "action": "alert",
    "calculation_method": "daily_only"
  }
}
```

### Multiple Groups Example

You can create unlimited groups with different strategies:

```json
{
  "groups": {
    "scalping": {
      "name": "Scalping BTC/ETH",
      "coins": ["KRW-BTC", "KRW-ETH"],
      "buy_settings": {
        "mode": "auto",
        "auto_config": {
          "investment_style": "aggressive"
        }
      }
    },
    "long_term": {
      "name": "Long-term Altcoins",
      "coins": ["KRW-XRP", "KRW-ADA"],
      "buy_settings": {
        "mode": "auto",
        "auto_config": {
          "investment_style": "conservative"
        }
      }
    },
    "observation": {
      "name": "Observation Only",
      "coins": ["KRW-DOGE"],
      "buy_settings": {
        "mode": "observation"
      }
    }
  }
}
```

---

## Development Environment

### IDE Setup

#### VS Code (Recommended)

1. **Install Extensions**:
   - Python
   - Pylance
   - Python Docstring Generator
   - GitLens

2. **Workspace Settings** (`.vscode/settings.json`):
```json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "[python]": {
    "editor.rulers": [88]
  }
}
```

3. **Launch Configuration** (`.vscode/launch.json`):
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Main",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/main.py",
      "console": "integratedTerminal"
    },
    {
      "name": "Python: Backtest",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/backtest/run_dca_backtest.py",
      "console": "integratedTerminal"
    }
  ]
}
```

#### PyCharm

1. **Open Project**: File → Open → Select `upbit_dca_trader`
2. **Configure Interpreter**:
   - Settings → Project → Python Interpreter
   - Add → Existing Environment → Select `venv/bin/python`
3. **Run Configuration**:
   - Script path: `main.py`
   - Working directory: Project root

### Debugging

**Enable Debug Logging**:

Edit `.env`:
```bash
LOG_LEVEL=DEBUG
```

Or in code:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Test Individual Components**:

```bash
# Test Upbit API connection
python -c "from core.upbit_api import UpbitAPI; api = UpbitAPI(); print(api.get_ticker('KRW-BTC'))"

# Test strategy
python -c "from core.strategies import FilteredBBStrategy; s = FilteredBBStrategy('KRW-BTC'); print('Strategy OK')"

# Test WebSocket
python tests/test_websocket.py
```

### Git Configuration

```bash
# Set up git (if not already)
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# Check status
git status

# Create branch for development
git checkout -b feature/my-feature
```

---

## Production Deployment

### Cloud Deployment (Recommended)

**Why Cloud?**
- 24/7 uptime
- No local computer needed
- Reliable internet
- Professional infrastructure

#### AWS EC2

1. **Launch Instance**:
   - Ubuntu 22.04 LTS
   - t3.small (2GB RAM)
   - 20GB SSD

2. **Setup**:
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python
sudo apt install python3.10 python3.10-venv python3-pip git -y

# Clone project
git clone https://github.com/jang1230/upbit-auto-trader.git
cd upbit-auto-trader/upbit_dca_trader

# Setup environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure via .env file (headless server)
nano .env
```

3. **Run in background**:
```bash
# Using screen
screen -S trading
python main.py
# Press Ctrl+A then D to detach

# Resume: screen -r trading
```

#### Uptime Monitoring

```bash
# Using systemd service
sudo nano /etc/systemd/system/upbit-trader.service
```

```ini
[Unit]
Description=Upbit DCA Trader
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/upbit-auto-trader/upbit_dca_trader
Environment="PATH=/home/ubuntu/upbit-auto-trader/upbit_dca_trader/venv/bin"
ExecStart=/home/ubuntu/upbit-auto-trader/upbit_dca_trader/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl enable upbit-trader
sudo systemctl start upbit-trader

# Check status
sudo systemctl status upbit-trader
```

### Local 24/7 Running

**Requirements**:
- Dedicated computer
- UPS (Uninterruptible Power Supply) recommended
- Stable internet
- Cooling/ventilation

**Setup**:

```bash
# Keep computer awake (macOS)
caffeinate -d python main.py

# Keep computer awake (Windows)
powercfg /change monitor-timeout-ac 0
powercfg /change standby-timeout-ac 0
```

**Auto-start on boot** (Windows):
1. Create batch file `start_trader.bat`:
```batch
cd C:\path\to\upbit_dca_trader
venv\Scripts\activate
python main.py
```
2. Add to Startup folder:
   - Win+R → `shell:startup`
   - Copy `start_trader.bat` here

---

## Verification Checklist

Before running in production:

```
✅ Python 3.8+ installed
✅ All dependencies installed
✅ Virtual environment activated
✅ API keys configured (for live trading)
✅ Telegram bot configured
✅ Strategy selected
✅ DCA settings configured
✅ Risk settings configured
✅ Dry run mode tested (minimum 1 week)
✅ Telegram notifications working
✅ Logs directory exists
✅ Stable internet connection
✅ Backup of configuration files
```

---

## Next Steps

1. **Test in Dry Run**: [README.md](README.md#2단계-페이퍼-트레이딩-최소-1주일-권장)
2. **Monitor Performance**: Check Telegram notifications
3. **Review Logs**: `logs/trading.log`
4. **Gradual Deployment**: Start with minimum capital

---

## Support

- **Installation Issues**: [INSTALLATION.md](INSTALLATION.md)
- **Runtime Errors**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Telegram Setup**: [docs/TELEGRAM_설정_가이드.md](docs/TELEGRAM_설정_가이드.md)
- **GitHub Issues**: https://github.com/jang1230/upbit-auto-trader/issues

---

**Environment ready! Time to trade! 🚀**
