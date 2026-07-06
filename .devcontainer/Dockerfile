FROM mcr.microsoft.com/devcontainers/python:3.14

RUN mkdir -p /home/vscode/.ssh && chown -R vscode:vscode /home/vscode/.ssh

RUN pip install --no-cache-dir pandas

RUN apt-get update && apt-get install -y --no-install-recommends \
    sshpass \
    fastfetch \
    curl \
    meld \
    && rm -rf /var/lib/apt/lists/*