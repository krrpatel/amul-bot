#!/bin/bash

# Amul Bot Start Script

set -e

echo "🥛 Starting Amul Product Tracker Bot..."
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please create .env file from .env.example"
    echo ""
    echo "  cp .env.example .env"
    echo "  nano .env  # Add your TELEGRAM_BOT_TOKEN"
    echo ""
    exit 1
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Validate required environment variables
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "❌ Error: TELEGRAM_BOT_TOKEN not set in .env file"
    exit 1
fi

echo "✅ Configuration loaded"
echo ""

# Check if Docker is available
if command -v docker-compose &> /dev/null; then
    echo "🐳 Docker Compose detected"
    echo ""
    echo "Choose deployment method:"
    echo "  1) Docker Compose (recommended)"
    echo "  2) Manual Python"
    echo ""
    read -p "Enter choice (1 or 2): " choice
    
    case $choice in
        1)
            echo ""
            echo "🚀 Starting with Docker Compose..."
            docker-compose up -d
            echo ""
            echo "✅ Services started!"
            echo ""
            echo "View logs with: docker-compose logs -f"
            echo "Stop with: docker-compose down"
            ;;
        2)
            echo ""
            echo "🚀 Starting manually..."
            
            # Check Redis
            if ! command -v redis-cli &> /dev/null || ! redis-cli ping &> /dev/null; then
                echo "⚠️  Warning: Redis not running. Starting Redis..."
                if command -v redis-server &> /dev/null; then
                    redis-server --daemonize yes
                    sleep 2
                else
                    echo "❌ Redis not installed. Please install Redis first."
                    exit 1
                fi
            fi
            
            echo "Starting bot in background..."
            nohup python bot.py > logs/bot.log 2>&1 &
            BOT_PID=$!
            
            echo "Starting checker in background..."
            nohup python notification_checker.py > logs/checker.log 2>&1 &
            CHECKER_PID=$!
            
            echo ""
            echo "✅ Services started!"
            echo "  Bot PID: $BOT_PID"
            echo "  Checker PID: $CHECKER_PID"
            echo ""
            echo "View logs:"
            echo "  tail -f logs/bot.log"
            echo "  tail -f logs/checker.log"
            echo ""
            echo "Stop services:"
            echo "  kill $BOT_PID $CHECKER_PID"
            ;;
        *)
            echo "Invalid choice"
            exit 1
            ;;
    esac
else
    echo "🐍 Running with Python..."
    
    # Check Redis
    if ! command -v redis-cli &> /dev/null || ! redis-cli ping &> /dev/null; then
        echo "❌ Redis not running. Please start Redis first."
        echo ""
        echo "  redis-server"
        echo ""
        exit 1
    fi
    
    echo "Starting bot in background..."
    mkdir -p logs
    nohup python bot.py > logs/bot.log 2>&1 &
    BOT_PID=$!
    
    echo "Starting checker in background..."
    nohup python notification_checker.py > logs/checker.log 2>&1 &
    CHECKER_PID=$!
    
    echo ""
    echo "✅ Services started!"
    echo "  Bot PID: $BOT_PID"
    echo "  Checker PID: $CHECKER_PID"
    echo ""
    echo "View logs:"
    echo "  tail -f logs/bot.log"
    echo "  tail -f logs/checker.log"
fi

echo ""
echo "🎉 Bot is ready! Open Telegram and send /start to your bot"
echo ""
