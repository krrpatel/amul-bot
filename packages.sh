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
google-chrome-stable \
nodejs \
python3 \
python3-dev \
python3-pip \
python3-venv \
xvfb \
yarn

echo "Installation complete ✅"
