# AI Workflow - Docker環境
# Linux環境でClaude Agent SDKを実行

# Python 3.11ベースイメージを使用
FROM python:3.11-slim-bullseye

# 作業ディレクトリ
WORKDIR /workspace

# システムパッケージとNode.jsのインストール
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Claude Code CLIのインストール
RUN npm install -g @anthropic-ai/claude-code

# 作業ディレクトリにコピー
COPY requirements.txt ./

# Python依存パッケージのインストール
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY . .

# Claudeコマンドが使えることを確認
RUN claude --version

# デフォルトコマンド
CMD ["/bin/bash"]
