#!/bin/bash
# Lade die normalen lokalen Bash-Einstellungen
if [ -f ~/.bashrc ]; then
    source ~/.bashrc
fi

if ! command -v devpod &>/dev/null; then
  echo "devpod nicht gefunden. Prüfe Docker …"

  if ! command -v docker &>/dev/null; then
    echo "Installiere Docker …"
    curl -fsSL https://get.docker.com | sudo sh
    sudo usermod -aG docker "$USER"
    echo "⚠️  Bitte aus- und wieder einloggen (oder 'newgrp docker') für Docker-Rechte."
  fi

  echo "Installiere devpod …"
  curl -fsSL https://devpod.sh/install.sh | sh

  echo "Setze Docker als Default-Provider …"
  devpod provider use docker 2>/dev/null || devpod provider add docker
fi

# DevPod Check
echo "Prüfe vivizoo.devpod..."
if ! ssh -q -o ConnectTimeout=2 vivizoo.devpod exit; then
    echo "Starte DevPod..."
    devpod up .
fi

echo "Verbinde mit vivizoo.devpod und aktiviere venv..."

# Verbindet per SSH, springt in den Container und startet dort eine interaktive 
# Bash-Shell, die direkt das venv im Container sourct.
ssh -t vivizoo.devpod "bash --init-file <(echo '
    if [ -f ~/.bashrc ]; then source ~/.bashrc; fi
    if [ -d .venv ]; then 
        source .venv/bin/activate
        echo \"[DevPod] .venv erfolgreich aktiviert!\"
    else
        python -m venv .venv --system-site-packages
        source .venv/bin/activate
    fi
')"