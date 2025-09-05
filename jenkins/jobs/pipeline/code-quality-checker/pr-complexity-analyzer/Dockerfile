# rust:1.76-slimをベースにGitを含むイメージを作成
FROM rust:1.76-slim

# rootユーザーとして実行
USER root

# ホームディレクトリを設定
ENV HOME=/root

# 必要なパッケージをインストール
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    pkg-config \
    libssl-dev \
    openssh-client \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

# rootのホームディレクトリを作成し、権限を設定
RUN mkdir -p /root && chmod 755 /root

# Git safe.directoryをグローバルに設定
RUN git config --global --add safe.directory '*' \
    && git config --global --add safe.directory /workspace \
    && git config --global --add safe.directory /tmp \
    && git config --global user.name "Jenkins" \
    && git config --global user.email "jenkins@localhost"

# 作業ディレクトリを設定
WORKDIR /workspace

# Gitバージョンと設定を表示（デバッグ用）
RUN git --version && git config --global --list