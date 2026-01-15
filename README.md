# Amul Bot VPS Setup Guide

This guide helps you install all required system and Python dependencies and run the bot services easily.

---

## System Requirements
- Ubuntu 22.04+ VPS
- Python 3.10+
- Root or sudo access

---

## Quick Installation

### Step 1: Clone the project

```bash
git clone https://github.com/krrpatel/amul-bot
cd amul-bot
```

---

### Step 2: Run auto setup script

```bash
chmod +x setup_amul_bot.sh
./setup_amul_bot.sh
```

This will:
- Install system packages
- Setup Python virtual environment
- Install Python dependencies
- Install screen

---

## Run Services in Background

### Start Main Bot

```bash
screen -S amul_app
source .venv/bin/activate
python bot.py
```

Detach using:
CTRL + A + D

---

### Start Notification Service

```bash
screen -S amul_notifier
source .venv/bin/activate
python notification_checker.py
```

Detach using:
CTRL + A + D

---

## Manage Screens

Resume:
```bash
screen -r amul_app
screen -r amul_notifier
```

Stop:
```bash
screen -XS amul_app quit
screen -XS amul_notifier quit
```

---

## Environment Variables

Create .env file:
```bash
nano .env
```

Add:
```
BOT_TOKEN=your_token
API_KEY=your_key
```

---

## Done!

Your bot is now running in background.
