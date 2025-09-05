# rust:1.76-slimをベースにGitを含むイメージを作成
FROM rust:1.76-slim

# rootユーザーとして実行
USER root

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

# Git safe.directoryをグローバルに設定
RUN git config --global --add safe.directory '*' \
    && git config --global --add safe.directory /workspace \
    && git config --global --add safe.directory /tmp

# 作業ディレクトリを設定
WORKDIR /workspace

# Gitバージョンを表示（デバッグ用）
RUN git --version