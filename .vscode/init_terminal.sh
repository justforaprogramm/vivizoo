#!/bin/bash
# Lade die normalen lokalen Bash-Einstellungen
if [ -f ~/.bashrc ]; then
    source ~/.bashrc
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