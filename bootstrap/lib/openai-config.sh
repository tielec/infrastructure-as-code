#!/bin/bash
# openai-config.sh - OpenAI API キー管理

# 依存関係
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

# OpenAI APIキー関連の定数
readonly OPENAI_API_KEY_PARAM="/bootstrap/openai/api-key"

# OpenAI APIキーを取得
get_openai_api_key() {
    # 引数チェック
    if [ $# -ne 1 ]; then
        log_error "使用方法: get_openai_api_key <REGION>"
        return 1
    fi

    local REGION="$1"

    aws ssm get-parameter \
        --name "$OPENAI_API_KEY_PARAM" \
        --region "$REGION" \
        --with-decryption \
        --query 'Parameter.Value' \
        --output text 2>/dev/null || echo ""
}

# APIキーの形式を検証
validate_api_key() {
    local api_key="$1"
    
    if [[ -z "$api_key" ]]; then
        log_error "APIキーが入力されていません"
        return 1
    elif [[ ! "$api_key" =~ ^sk- ]]; then
        log_error "無効な形式です。APIキーは 'sk-' で始まる必要があります"
        return 1
    fi
    
    return 0
}

# APIキーをSSMに保存
save_api_key_to_ssm() {
    # 引数チェック
    if [ $# -ne 2 ]; then
        log_error "使用方法: save_api_key_to_ssm <api_key> <REGION>"
        return 1
    fi

    local api_key="$1"
    local REGION="$2"

    log_info "APIキーをSSMパラメータストアに保存しています..."

    if aws ssm put-parameter \
        --name "$OPENAI_API_KEY_PARAM" \
        --value "$api_key" \
        --type "SecureString" \
        --description "OpenAI API Key for various services" \
        --region "$REGION" \
        --overwrite 2>/dev/null; then
        log_info "✓ OpenAI APIキーがSSMパラメータストアに安全に保存されました"
        log_info "  パラメータ名: $OPENAI_API_KEY_PARAM"
        return 0
    else
        log_error "APIキーの保存に失敗しました"
        log_warn "手動で設定してください"
        return 1
    fi
}

# 対話的にAPIキーを入力
input_api_key_interactive() {
    local api_key
    
    while true; do
        read -s -p "OpenAI APIキーを入力してください (sk-...) : " api_key
        echo
        
        if validate_api_key "$api_key"; then
            echo "$api_key"
            return 0
        fi
    done
}

# OpenAI APIキー設定のメイン処理
setup_openai_api_key() {
    # 引数チェック
    if [ $# -ne 1 ]; then
        log_error "使用方法: setup_openai_api_key <REGION>"
        return 1
    fi

    local REGION="$1"

    log_section "OpenAI APIキー設定"

    log_info "OpenAI APIキーをSSMパラメータストアで確認しています..."

    # 既存のキーを確認
    local existing_key=$(get_openai_api_key "$REGION")
    
    if [ -n "$existing_key" ]; then
        log_info "✓ OpenAI APIキーは既にSSMパラメータストアに設定されています"
        return 0
    fi
    
    # キーが設定されていない場合
    log_warn "OpenAI APIキーが設定されていません"
    
    if ! confirm_action "今すぐ設定しますか？" "y"; then
        log_warn "設定をスキップしました"
        return 1
    fi
    
    # キーの入力と保存
    local api_key=$(input_api_key_interactive)
    
    if [ -n "$api_key" ]; then
        save_api_key_to_ssm "$api_key" "$REGION"
        return $?
    fi
    
    return 1
}

# APIキーの取得と環境変数への設定
export_openai_api_key() {
    local api_key=$(get_openai_api_key "$REGION")
    
    if [ -n "$api_key" ]; then
        export OPENAI_API_KEY="$api_key"
        log_info "✓ OpenAI APIキーが環境変数に設定されました"
        return 0
    else
        log_warn "OpenAI APIキーが設定されていません"
        return 1
    fi
}