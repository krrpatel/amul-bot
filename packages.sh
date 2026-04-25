#!/bin/bash

set -e

echo "Updating system..."
sudo apt update

echo "Installing packages..."
sudo apt install -y \
build-essential \
chromium-browser \
chromium-chromedriver \
chromium-codecs-ffmpeg \
docker-buildx-plugin \
docker-ce \
docker-ce-cli \
docker-ce-rootless-extras \
docker-compose-plugin \
docker-model-plugin \
git \
nodejs \
python3 \
python3-dev \
python3-pip \
python3-venv \
xvfb \
yarn \
wget \
gnupg

# -------------------------------
# Install Google Chrome (your way)
# -------------------------------
echo "Installing Google Chrome..."

wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt install -y ./google-chrome-stable_current_amd64.deb

# -------------------------------
# Verify installation
# -------------------------------
echo "Checking Chrome path..."

CHROME_PATH=$(which google-chrome || true)

if [ "$CHROME_PATH" = "/usr/bin/google-chrome" ]; then
    echo "Chrome installed correctly at $CHROME_PATH ✅"
else
    echo "Chrome not found at expected path ❌"
    echo "Found at: $CHROME_PATH"
fi

echo "Installation complete ✅"
