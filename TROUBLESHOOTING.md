# Troubleshooting Guide

Common issues and solutions for Upbit DCA Trader.

---

## Table of Contents

1. [Installation Issues](#installation-issues)
2. [API and Connection Issues](#api-and-connection-issues)
3. [GUI Issues](#gui-issues)
4. [Trading Issues](#trading-issues)
5. [WebSocket Issues](#websocket-issues)
6. [Telegram Issues](#telegram-issues)
7. [Performance Issues](#performance-issues)
8. [Data and File Issues](#data-and-file-issues)

---

## Installation Issues

### ImportError: No module named 'XXX'

**Symptom**:
```
ModuleNotFoundError: No module named 'pyupbit'
ModuleNotFoundError: No module named 'PySide6'
```

**Solution**:
```bash
# 1. Check if virtual environment is activated
# Should see (venv) in prompt

# 2. If not activated:
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# 3. Install missing package
pip install pyupbit
pip install PySide6

# 4. Or reinstall all
pip install -r requirements.txt
```

---

### Python version too old

**Symptom**:
```
ERROR: Package 'PySide6' requires Python 3.8 or later
```

**Solution**:
```bash
# Check Python version
python --version

# If < 3.8, install Python 3.10:
# - Windows: https://www.python.org/downloads/
# - macOS: brew install python@3.10
# - Linux: sudo apt install python3.10
```

---

### pip install fails with SSL error

**Symptom**:
```
SSL: CERTIFICATE_VERIFY_FAILED
```

**Solution**:
```bash
# 1. Upgrade pip
python -m pip install --upgrade pip

# 2. Try with trusted host
pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt

# 3. Or upgrade certificates (macOS)
/Applications/Python\ 3.10/Install\ Certificates.command
```

---

## API and Connection Issues

### Invalid API Key Error

**Symptom**:
```
ERROR: Invalid API key
401 Unauthorized
```

**Possible Causes & Solutions**:

1. **Wrong API Keys**:
   ```bash
   # Check keys in GUI settings
   # ⚙️ 설정 → 🔑 API 키
   # Verify Access Key and Secret Key
   ```

2. **IP Restriction**:
   - Upbit console → API Management
   - Check if your IP is whitelisted
   - Add current IP or disable restriction

3. **Expired Keys**:
   - Check key expiration date in Upbit
   - Generate new keys if expired

4. **Incorrect Permissions**:
   Required permissions:
   ```
   ✅ 자산 조회 (View Balance)
   ✅ 주문 조회 (View Orders)
   ✅ 주문 등록/취소 (Create/Cancel Orders)
   ```

---

### Connection Timeout

**Symptom**:
```
requests.exceptions.ConnectionError: Connection timed out
```

**Solution**:
```bash
# 1. Check internet connection
ping 8.8.8.8

# 2. Check Upbit API status
# Visit: https://status.upbit.com

# 3. Try with longer timeout
# Edit core/upbit_api.py:
# requests.get(..., timeout=30)

# 4. Check firewall settings
# Allow Python through firewall
```

---

### Rate Limit Exceeded

**Symptom**:
```
ERROR: 429 Too Many Requests
API call limit exceeded
```

**Solution**:
- Upbit limits: 30 requests/second, 900 requests/minute
- Bot automatically handles rate limiting
- If still occurring:
  ```python
  # Check scan_interval in settings
  # Increase if too frequent:
  # ⚙️ 설정 → scan_interval: 10초 → 30초
  ```

---

## GUI Issues

### GUI Window Won't Open

**Symptom**:
```
QXcbConnection: Could not connect to display
```

**Solution (Linux)**:
```bash
# 1. Install display dependencies
sudo apt install libxcb-xinerama0 libxcb-cursor0

# 2. Or use headless mode
# Edit main.py to run without GUI
# Use .env configuration instead
```

**Solution (macOS)**:
```bash
# Update XQuartz
brew install --cask xquartz
```

**Solution (Windows)**:
```cmd
# Install Visual C++ Redistributable
# Download: https://aka.ms/vs/17/release/vc_redist.x64.exe
```

---

### GUI Freezes or Crashes

**Symptom**:
- GUI becomes unresponsive
- Application crashes without error

**Solution**:
```bash
# 1. Check logs
cat logs/trading.log

# 2. Run with verbose logging
LOG_LEVEL=DEBUG python main.py

# 3. Check system resources
# Task Manager (Windows)
# Activity Monitor (macOS)
# htop (Linux)

# 4. Increase system resources
# Close other applications
# Add more RAM if possible
```

---

### Settings Not Saving

**Symptom**:
- Settings reset after restart
- Configuration changes don't persist

**Solution**:
```bash
# 1. Check file permissions
ls -l config/

# 2. Ensure config directory exists
mkdir -p config

# 3. Check if config/settings.json is writable
chmod 644 config/settings.json

# 4. Run as regular user (not root/admin)
```

---

## Trading Issues

### Orders Not Executing

**Symptom**:
- Buy/sell signals generated
- But no orders placed

**Checklist**:

1. **Dry Run Mode**:
   ```
   ⚙️ GUI → Check if "🧪 Dry Run" is enabled
   If enabled: Orders are simulated, not real
   ```

2. **Insufficient Balance**:
   ```bash
   # Check KRW balance in GUI
   # Ensure balance > minimum order (5,000 KRW)
   ```

3. **API Keys**:
   ```
   # Verify keys configured
   # ⚙️ 설정 → 🔑 API 키
   ```

4. **Market Hours**:
   ```
   # Upbit trades 24/7
   # But check for maintenance
   # https://status.upbit.com
   ```

---

### Unexpected Sell/Liquidation

**Symptom**:
- Position sold unexpectedly
- Not at target or stop loss

**Possible Causes**:

1. **Multi-level TP/SL**:
   ```
   # Check DCA settings
   # ⚙️ 설정 → 💰 고급 DCA
   # Multiple levels may be triggered
   ```

2. **Risk Management**:
   ```
   # Daily loss limit reached
   # Check: ⚙️ 설정 → 🛡️ 리스크
   ```

3. **Manual Override**:
   ```
   # Did you sell manually in Upbit app?
   # Bot detects and adjusts
   ```

---

### DCA Not Working

**Symptom**:
- Price drops but no DCA buy
- Expected additional purchase didn't happen

**Check**:

1. **DCA Configuration**:
   ```
   ⚙️ 설정 → 💰 고급 DCA
   ✅ Enable DCA levels
   ✅ Set trigger percentages (-3%, -6%, etc.)
   ✅ Set buy amounts
   ```

2. **Sufficient Balance**:
   ```
   # Need enough KRW for DCA buys
   # Check balance in GUI
   ```

3. **Max Buys Reached**:
   ```
   # Check if max_buys limit reached
   # Default: 6 buys
   ```

4. **Logs**:
   ```bash
   grep "DCA" logs/trading.log
   # Check for DCA trigger messages
   ```

---

## WebSocket Issues

### Real-time Price Not Updating

**Symptom**:
- Prices frozen
- "1초 전" (1 second ago) not changing

**Solution**:

1. **Check WebSocket Connection**:
   ```bash
   # Look for in logs:
   grep "WebSocket" logs/trading.log

   # Should see:
   # "WebSocket connected"
   # "Ticker update: KRW-BTC"
   ```

2. **Manual Reconnect**:
   ```
   # Stop and restart trading
   # 🛑 트레이딩 중지
   # 🚀 트레이딩 시작
   ```

3. **Check Internet**:
   ```bash
   # Test connection
   ping api.upbit.com
   ```

4. **Firewall**:
   ```
   # Allow WebSocket connections
   # Port: 443 (HTTPS/WSS)
   ```

---

### WebSocket Keeps Disconnecting

**Symptom**:
```
WebSocket disconnected
Reconnecting... (attempt 1/10)
```

**Solution**:

1. **Increase Reconnect Delay**:
   ```python
   # Edit .env
   WS_RECONNECT_DELAY=10  # Increase from 5 to 10 seconds
   ```

2. **Check Network Stability**:
   ```bash
   # Test sustained connection
   ping -t api.upbit.com  # Windows
   ping api.upbit.com     # macOS/Linux
   ```

3. **Use Wired Connection**:
   - WiFi can be unstable
   - Use Ethernet cable if possible

---

## Telegram Issues

### No Telegram Notifications

**Symptom**:
- Trading active
- But no messages in Telegram

**Checklist**:

1. **Telegram Configured**:
   ```
   ⚙️ 설정 → 📱 텔레그램
   ✅ Bot Token entered
   ✅ Chat ID entered
   ✅ Test message sent successfully
   ```

2. **Bot Not Blocked**:
   - Check if you blocked the bot
   - Search for bot in Telegram
   - Send `/start` command

3. **Correct Chat ID**:
   ```bash
   # Verify Chat ID
   # Visit: https://api.telegram.org/bot<TOKEN>/getUpdates
   # Check "chat":{"id": ...}
   ```

4. **Internet Connection**:
   ```bash
   # Test Telegram API
   curl https://api.telegram.org/bot<TOKEN>/getMe
   ```

---

### Telegram Commands Not Working

**Symptom**:
- Send `/status` but no response
- Bot doesn't reply to commands

**Solution**:

1. **Check Bot Running**:
   ```
   # Ensure trading is started
   # GUI shows: "🔄 트레이딩 중"
   ```

2. **Correct Chat**:
   - Send commands to YOUR bot
   - Not to @BotFather

3. **Command Format**:
   ```
   # Use exactly:
   /status
   /balance
   /stop
   /start
   /help

   # Not:
   /Status
   /BALANCE
   status
   ```

---

## Performance Issues

### High CPU Usage

**Symptom**:
- CPU usage > 50%
- Computer slows down

**Solution**:

1. **Reduce Scan Frequency**:
   ```
   ⚙️ 설정 → scan_interval
   Increase from 10s to 30s or 60s
   ```

2. **Limit Coins**:
   ```
   # Trade fewer coins simultaneously
   # ⚙️ 설정 → 📊 코인 선택
   # Select 1-2 coins instead of many
   ```

3. **Close Other Apps**:
   ```
   # Close browser tabs
   # Close unnecessary applications
   ```

---

### High Memory Usage

**Symptom**:
- RAM usage > 2GB
- System swapping

**Solution**:

1. **Limit Data Buffer**:
   ```python
   # Edit core/data_buffer.py
   # Reduce MAX_CANDLES from 200 to 100
   ```

2. **Clear Logs**:
   ```bash
   # Old logs take memory
   rm logs/*.log.old
   ```

3. **Restart Periodically**:
   ```
   # Restart bot daily
   # Clears memory leaks
   ```

---

## Data and File Issues

### Missing Historical Data

**Symptom**:
```
ERROR: Historical data file not found
data/historical/KRW-BTC_minute1.csv
```

**Solution**:

```bash
# Download historical data
python backtest/safe_data_collector.py

# Follow prompts:
# Symbol: KRW-BTC
# Days: 365
```

---

### Permission Denied Errors

**Symptom**:
```
PermissionError: [Errno 13] Permission denied: 'config/settings.json'
```

**Solution**:

```bash
# Fix permissions
chmod 755 config/
chmod 644 config/*.json

# Or run as current user (not sudo/admin)
```

---

### Corrupt Configuration File

**Symptom**:
```
json.decoder.JSONDecodeError: Expecting value
```

**Solution**:

```bash
# 1. Backup corrupt file
cp config/settings.json config/settings.json.backup

# 2. Delete corrupt file
rm config/settings.json

# 3. Restart GUI
python main.py

# 4. Reconfigure in GUI
```

---

## Emergency Procedures

### Bot is Making Bad Trades

1. **STOP IMMEDIATELY**:
   ```
   # Method 1: Telegram
   /stop

   # Method 2: GUI
   Click "🛑 트레이딩 중지"

   # Method 3: Kill Process
   Ctrl + C in terminal
   ```

2. **Disable API Keys**:
   - Upbit → API Management
   - Delete or disable keys

3. **Check Logs**:
   ```bash
   tail -100 logs/trading.log
   ```

4. **Manual Cleanup**:
   - Upbit app/web
   - Manually close positions
   - Check balance

---

### Lost Configuration

1. **Check Backups**:
   ```bash
   ls -la config/
   # Look for .backup files
   ```

2. **Recreate Configuration**:
   ```bash
   # Delete all config
   rm -rf config/*

   # Restart GUI
   python main.py

   # Reconfigure everything
   ```

---

## Getting Help

If issue not resolved:

1. **Check Logs**:
   ```bash
   # Recent errors
   tail -50 logs/trading.log

   # Search specific error
   grep -i "error" logs/trading.log
   ```

2. **Enable Debug Logging**:
   ```bash
   # Edit .env
   LOG_LEVEL=DEBUG

   # Restart bot
   python main.py
   ```

3. **Create GitHub Issue**:
   - Visit: https://github.com/jang1230/upbit-auto-trader/issues
   - Click "New Issue"
   - Include:
     - Python version: `python --version`
     - OS: Windows/macOS/Linux
     - Error message (full text)
     - Log excerpt (remove sensitive info!)
     - Steps to reproduce

4. **Community Support**:
   - Check existing issues
   - Search README.md
   - Review documentation

---

## Diagnostic Commands

```bash
# System info
python --version
pip --version
pip list | grep -i "pyupbit\|pyside\|websocket"

# Test imports
python -c "import pyupbit; print('OK')"
python -c "import PySide6; print('OK')"
python -c "import websockets; print('OK')"

# Check API connection
python -c "from core.upbit_api import UpbitAPI; api = UpbitAPI(); print(api.get_ticker('KRW-BTC'))"

# Check file permissions
ls -la config/
ls -la logs/

# Check disk space
df -h

# Check memory
free -h  # Linux
vm_stat  # macOS
```

---

## Prevention Tips

✅ **Regular Backups**:
```bash
# Backup config weekly
cp -r config/ config.backup.$(date +%Y%m%d)
```

✅ **Monitor Logs**:
```bash
# Check logs daily
tail -50 logs/trading.log
```

✅ **Test in Dry Run**:
```
# Always test changes in Dry Run first
# Minimum 1 week before live trading
```

✅ **Keep Updated**:
```bash
# Update dependencies monthly
pip install --upgrade -r requirements.txt
```

✅ **Monitor System Resources**:
```
# Check CPU/RAM usage
# Ensure system is healthy
```

---

**Stay calm and trade safe! 🚀**
