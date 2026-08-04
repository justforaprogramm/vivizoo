#!/bin/bash
if [ -f ~/.bashrc ]; then
    source ~/.bashrc
fi

# 1. Install Dependencies if Missing
if ! command -v devpod &>/dev/null; then
  echo "devpod nicht gefunden. Prüfe Docker …"

  if ! command -v docker &>/dev/null; then
    echo "Installiere Docker …"
    curl -fsSL https://get.docker.com | sudo sh
    sudo usermod -aG docker "$USER"
    echo "⚠️ Bitte aus- und wieder einloggen (oder 'newgrp docker') für Docker-Rechte."
  fi

  echo "Installiere devpod …"
  curl -fsSL https://devpod.sh/install.sh | sh

  echo "Setze Docker als Default-Provider …"
  devpod provider use docker 2>/dev/null || devpod provider add docker
fi

# 2. Ensure DevPod Container is Running
echo "Prüfe vivizoo.devpod..."
if ! ssh -q -o ConnectTimeout=2 vivizoo.devpod exit; then
    echo "Starte DevPod..."
    devpod up .
fi

# 3. Connect Directly
echo "Verbinde mit vivizoo.devpod..."
ssh -t vivizoo.devpod