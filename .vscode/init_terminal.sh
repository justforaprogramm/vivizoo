#!/bin/bash

# use bashrc
if [ -f ~/.bashrc ]; then
    source ~/.bashrc
fi

# docker on system?
if ! command -v docker &>/dev/null; then
  echo "Docker nicht gefunden! …"
  exit 1
fi

echo "Docker gefunden..."

#devpod on system
if ! command -v devpod &>/dev/null; then
  echo "Devpod nicht gefunden! …"
  echo "versuche vielleicht …"
  echo "devpod provider use docker 2>/dev/null || devpod provider add docker"
  exit 1
fi

echo "Devpod gefunden..."

# devpod running?
echo "ist vivizoo.devpod verbindbar..."
if ! ssh -q -o ConnectTimeout=2 vivizoo.devpod exit; then
    echo "Starte DevPod..."
    devpod up .
fi

# 3. Connect Directly
echo "Verbinde mit vivizoo.devpod..."
ssh -t vivizoo.devpod