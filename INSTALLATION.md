# Installation Guide

Complete step-by-step installation guide for Upbit DCA Trader.

---

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Python Installation](#python-installation)
3. [Project Setup](#project-setup)
4. [Dependencies Installation](#dependencies-installation)
5. [Verification](#verification)
6. [Troubleshooting](#troubleshooting)

---

## System Requirements

### Minimum Requirements
- **Operating System**: Windows 10+, macOS 10.14+, or Linux (Ubuntu 18.04+)
- **Python**: 3.8 or higher
- **RAM**: 4GB minimum (8GB recommended)
- **Disk Space**: 500MB free space
- **Internet**: Stable broadband connection

### Recommended Setup
- **OS**: Windows 11 or macOS Ventura+ or Ubuntu 22.04+
- **Python**: 3.10 or 3.11
- **RAM**: 8GB or more
- **SSD**: For faster data processing
- **Network**: Wired connection or 5GHz WiFi

---

## Python Installation

### Windows

#### Method 1: Official Python Installer (Recommended)

1. **Download Python**:
   - Visit: https://www.python.org/downloads/
   - Download Python 3.10 or 3.11 (64-bit)

2. **Install Python**:
   ```
   ✅ Check "Add Python to PATH"
   ✅ Check "Install pip"
   Click "Install Now"
   ```

3. **Verify Installation**:
   ```cmd
   python --version
   pip --version
   ```

#### Method 2: Anaconda (Alternative)

1. Download from: https://www.anaconda.com/download
2. Install with default settings
3. Open "Anaconda Prompt"
4. Verify:
   ```cmd
   python --version
   conda --version
   ```

### macOS

#### Method 1: Homebrew (Recommended)

1. **Install Homebrew** (if not installed):
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

2. **Install Python**:
   ```bash
   brew install python@3.10
   ```

3. **Verify**:
   ```bash
   python3 --version
   pip3 --version
   ```

#### Method 2: Official Installer

1. Download from: https://www.python.org/downloads/
2. Install the .pkg file
3. Verify in Terminal:
   ```bash
   python3 --version
   ```

### Linux (Ubuntu/Debian)

```bash
# Update package list
sudo apt update

# Install Python 3.10
sudo apt install python3.10 python3.10-venv python3-pip

# Verify
python3 --version
pip3 --version
```

---

## Project Setup

### 1. Clone Repository

```bash
# Clone from GitHub
git clone https://github.com/jang1230/upbit-auto-trader.git

# Navigate to project directory
cd upbit-auto-trader/upbit_dca_trader
```

**Alternative (if git not installed)**:
1. Download ZIP: https://github.com/jang1230/upbit-auto-trader/archive/main.zip
2. Extract to desired location
3. Open terminal/command prompt in `upbit-auto-trader/upbit_dca_trader` folder

### 2. Create Virtual Environment (Recommended)

**Why use virtual environment?**
- Isolated Python packages
- Prevents conflicts with other projects
- Easy dependency management

#### Windows
```cmd
# Create virtual environment
python -m venv venv

# Activate
venv\Scripts\activate

# You should see (venv) in your prompt
```

#### macOS/Linux
```bash
# Create virtual environment
python3 -m venv venv

# Activate
source venv/bin/activate

# You should see (venv) in your prompt
```

**Deactivate** (when done):
```bash
deactivate
```

---

## Dependencies Installation

### Method 1: Using requirements.txt (Recommended)

```bash
# Make sure virtual environment is activated
# You should see (venv) in prompt

# Install all dependencies
pip install -r requirements.txt

# This will install:
# - PySide6 (GUI framework)
# - pyupbit (Upbit API client)
# - websockets (real-time communication)
# - pandas, numpy (data analysis)
# - ta (technical analysis)
# - python-telegram-bot (notifications)
# - and more...
```

**Installation Progress**:
```
Collecting PySide6>=6.6.0
  Downloading PySide6-6.6.1-...
Installing collected packages: ...
Successfully installed PySide6-6.6.1 pyupbit-0.2.30 ...
```

This may take 5-10 minutes depending on your internet speed.

### Method 2: Manual Installation

If `requirements.txt` fails, install manually:

```bash
# Core packages
pip install PySide6>=6.6.0
pip install pyupbit>=0.2.30
pip install websockets>=12.0
pip install pandas>=2.0.0
pip install numpy>=1.24.0

# Technical analysis
pip install ta>=0.11.0
pip install matplotlib>=3.8.0

# API and security
pip install requests>=2.31.0
pip install PyJWT>=2.8.0
pip install python-dotenv>=1.0.0
pip install cryptography>=41.0.0
pip install keyring>=24.0.0

# Telegram
pip install python-telegram-bot>=20.0

# Async
pip install aiohttp>=3.9.0

# Testing
pip install pytest>=7.4.0
pip install pytest-asyncio>=0.23.0
```

### Verify Installation

```bash
# List installed packages
pip list

# Check specific package
pip show pyupbit
pip show PySide6
```

---

## Verification

### 1. Test Python Environment

```bash
# Test Python
python --version

# Should output: Python 3.10.x or 3.11.x
```

### 2. Test Package Imports

```bash
python -c "import pyupbit; print('pyupbit:', pyupbit.__version__)"
python -c "import PySide6; print('PySide6 OK')"
python -c "import websockets; print('websockets OK')"
python -c "import pandas; print('pandas OK')"
python -c "import ta; print('ta OK')"
```

All should print "OK" or version number without errors.

### 3. Test GUI Launch

```bash
# Launch the application
python main.py
```

**Expected Result**:
- GUI window opens
- No error messages in terminal
- Main window shows Upbit DCA Trader interface

**If errors occur**: See [Troubleshooting](#troubleshooting) section

---

## Troubleshooting

### Issue: `python` command not found

**Solution (Windows)**:
```cmd
# Use py instead
py --version
py main.py
```

**Solution (macOS/Linux)**:
```bash
# Use python3
python3 --version
python3 main.py
```

### Issue: `pip` command not found

```bash
# Windows
python -m pip --version

# macOS/Linux
python3 -m pip --version
```

### Issue: Permission denied (Linux/macOS)

```bash
# Don't use sudo! Use virtual environment instead
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Issue: SSL Certificate Error

```bash
# Upgrade pip first
python -m pip install --upgrade pip

# Try installation again
pip install -r requirements.txt
```

### Issue: PySide6 installation fails

**Windows**: Install Visual C++ Redistributable
- Download: https://aka.ms/vs/17/release/vc_redist.x64.exe
- Install and restart

**macOS**: Update Xcode Command Line Tools
```bash
xcode-select --install
```

**Linux**: Install dependencies
```bash
sudo apt install build-essential libgl1-mesa-dev
```

### Issue: `No module named 'pyupbit'`

```bash
# Check if virtual environment is activated
# Should see (venv) in prompt

# If not activated:
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Install pyupbit
pip install pyupbit
```

### Issue: Import error on startup

```bash
# Reinstall all dependencies
pip uninstall -r requirements.txt -y
pip install -r requirements.txt --force-reinstall
```

### Issue: GUI doesn't open

1. **Check Python version**:
   ```bash
   python --version
   # Must be 3.8 or higher
   ```

2. **Check PySide6**:
   ```bash
   pip show PySide6
   # Should show version 6.6.0 or higher
   ```

3. **Try verbose mode**:
   ```bash
   python -v main.py
   # Shows detailed import information
   ```

---

## Next Steps

After successful installation:

1. **Configure Settings**: See [ENVIRONMENT_SETUP.md](ENVIRONMENT_SETUP.md)
2. **Set up Telegram**: See [docs/TELEGRAM_설정_가이드.md](docs/TELEGRAM_설정_가이드.md)
3. **Configure Strategy**: See README.md "사용 방법" section
4. **Start Paper Trading**: Test with Dry Run mode first!

---

## Additional Resources

- **Main README**: [README.md](README.md)
- **Environment Setup**: [ENVIRONMENT_SETUP.md](ENVIRONMENT_SETUP.md)
- **Troubleshooting**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Telegram Guide**: [docs/TELEGRAM_설정_가이드.md](docs/TELEGRAM_설정_가이드.md)
- **GitHub Issues**: https://github.com/jang1230/upbit-auto-trader/issues

---

## Support

If you encounter issues not covered here:

1. Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
2. Search existing issues: https://github.com/jang1230/upbit-auto-trader/issues
3. Create new issue with:
   - Python version
   - Operating system
   - Error message (full text)
   - Steps to reproduce

---

**Installation complete! Ready to trade! 🚀**
