#!/bin/bash
# common.sh - 共通関数とカラー定義

# 厳密なエラーチェックは設定しない（呼び出し元で設定される）

# カラー定義
export GREEN='\033[0;32m'
export YELLOW='\033[1;33m'
export BLUE='\033[0;34m'
export RED='\033[0;31m'
export NC='\033[0m' # No Color

# ロギング関数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_section() {
    echo -e "\n${BLUE}=== $1 ===${NC}"
}

log_header() {
    echo -e "${BLUE}=============================================${NC}"
    echo -e "${BLUE}   $1${NC}"
    echo -e "${BLUE}=============================================${NC}"
    echo
}

# エラーハンドリング
error_exit() {
    log_error "$1"
    exit 1
}

# コマンド存在確認
check_command() {
    local cmd=$1
    if ! command -v "$cmd" &> /dev/null; then
        return 1
    fi
    return 0
}

# ディレクトリ確認
ensure_directory() {
    local dir=$1
    if [ ! -d "$dir" ]; then
        log_warn "ディレクトリが見つかりません: $dir"
        return 1
    fi
    return 0
}

# ファイル確認
ensure_file() {
    local file=$1
    if [ ! -f "$file" ]; then
        log_warn "ファイルが見つかりません: $file"
        return 1
    fi
    return 0
}

# 実行確認プロンプト
confirm_action() {
    local message=$1
    local default=${2:-n}
    
    if [ "$default" = "y" ]; then
        read -p "$message (Y/n): " response
        if [[ $response =~ ^[Nn]$ ]]; then
            return 1
        fi
    else
        read -p "$message (y/N): " response
        if [[ ! $response =~ ^[Yy]$ ]]; then
            return 1
        fi
    fi
    return 0
}

# プログレス表示
show_progress() {
    local current=$1
    local total=$2
    local message=$3
    echo -e "${GREEN}[$current/$total]${NC} $message"
}