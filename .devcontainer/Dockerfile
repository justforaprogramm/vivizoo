FROM mcr.microsoft.com/devcontainers/python:3.14

RUN apt-get update && apt-get install -y --no-install-recommends \
    sshpass \
    fastfetch \
    curl \
    meld \
    && rm -rf /var/lib/apt/lists/*

# Fix permissions on SSH directory before bind mount
RUN mkdir -p /home/vscode/.ssh && chown -R vscode:vscode /home/vscode/.ssh

# Create venv outside workspace mount so host files don't override it
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install packages into /opt/venv during image build
RUN pip install --no-cache-dir pandas sqlalchemy