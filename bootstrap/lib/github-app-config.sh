#!/bin/bash
# github-app-config.sh - GitHub App設定管理ライブラリ

# GitHub App設定をセットアップ
setup_github_app() {
    log_section "GitHub App設定"
    
    # リージョンとプロジェクト情報を取得
    local REGION="${AWS_REGION:-ap-northeast-1}"
    
    # 既存のGitHub App設定を確認
    local APP_ID_PARAM="/bootstrap/github/app-id"
    local APP_KEY_PARAM="/bootstrap/github/app-private-key"
    local APP_OWNER_PARAM="/bootstrap/github/app-owner"
    
    # App IDの確認
    if aws ssm get-parameter --name "$APP_ID_PARAM" --region "$REGION" &>/dev/null; then
        log_info "✓ GitHub App IDは既に設定されています"
        
        # 既存の設定を使用するか確認
        if confirm_action "既存のGitHub App設定を使用しますか？"; then
            log_info "既存の設定を使用します"
            return 0
        fi
    fi
    
    log_info "GitHub App設定を行います"
    echo
    echo "GitHub Appを使用することで、個人アクセストークンなしでリポジトリにアクセスできます。"
    echo "GitHub App設定には以下が必要です："
    echo "  1. GitHub App ID"
    echo "  2. GitHub App秘密鍵（PEM形式）"
    echo "  3. 組織名またはユーザー名（オプション）"
    echo
    
    # GitHub App設定の確認
    if ! confirm_action "GitHub Appを設定しますか？"; then
        log_info "GitHub App設定をスキップします"
        return 0
    fi
    
    # App IDの入力
    local app_id=""
    while [ -z "$app_id" ]; do
        read -p "GitHub App ID: " app_id
        if [ -z "$app_id" ]; then
            log_warn "App IDを入力してください"
        elif ! [[ "$app_id" =~ ^[0-9]+$ ]]; then
            log_warn "App IDは数値である必要があります"
            app_id=""
        fi
    done
    
    # 秘密鍵ファイルパスの入力
    local key_path=""
    local private_key=""
    while [ -z "$private_key" ]; do
        read -p "GitHub App秘密鍵ファイルのパス: " key_path
        
        if [ -z "$key_path" ]; then
            log_warn "秘密鍵ファイルのパスを入力してください"
            continue
        fi
        
        # ~を展開
        key_path="${key_path/#\~/$HOME}"
        
        if [ ! -f "$key_path" ]; then
            log_warn "ファイルが見つかりません: $key_path"
            continue
        fi
        
        # PEM形式の確認
        if ! grep -q "BEGIN RSA PRIVATE KEY" "$key_path" 2>/dev/null; then
            log_warn "指定されたファイルはPEM形式の秘密鍵ではないようです"
            if ! confirm_action "このファイルを使用しますか？"; then
                continue
            fi
        fi
        
        private_key=$(cat "$key_path")
        log_info "✓ 秘密鍵ファイルを読み込みました"
    done
    
    # 組織名/ユーザー名の入力（オプション）
    local owner=""
    read -p "組織名またはユーザー名（オプション、Enterでスキップ）: " owner
    
    # SSMパラメータストアに保存
    log_info "GitHub App設定をSSM Parameter Storeに保存しています..."
    
    # App IDを保存
    if aws ssm put-parameter \
        --name "$APP_ID_PARAM" \
        --value "$app_id" \
        --type "String" \
        --overwrite \
        --region "$REGION" &>/dev/null; then
        log_info "✓ App IDを保存しました"
    else
        log_error "App IDの保存に失敗しました"
        return 1
    fi
    
    # 秘密鍵を保存（SecureString）
    if aws ssm put-parameter \
        --name "$APP_KEY_PARAM" \
        --value "$private_key" \
        --type "SecureString" \
        --overwrite \
        --region "$REGION" &>/dev/null; then
        log_info "✓ 秘密鍵を保存しました"
    else
        log_error "秘密鍵の保存に失敗しました"
        return 1
    fi
    
    # 組織名/ユーザー名を保存（指定された場合）
    if [ -n "$owner" ]; then
        if aws ssm put-parameter \
            --name "$APP_OWNER_PARAM" \
            --value "$owner" \
            --type "String" \
            --overwrite \
            --region "$REGION" &>/dev/null; then
            log_info "✓ 組織名/ユーザー名を保存しました"
        else
            log_warn "組織名/ユーザー名の保存に失敗しました（続行します）"
        fi
    fi
    
    log_info "✅ GitHub App設定が完了しました"
    echo
    echo "設定されたGitHub App情報："
    echo "  - App ID: $app_id"
    if [ -n "$owner" ]; then
        echo "  - Owner: $owner"
    fi
    echo "  - 秘密鍵: SSMに安全に保存されました"
    echo
    echo "この設定はJenkinsの起動時に自動的に読み込まれ、"
    echo "GitHub Appクレデンシャル（ID: github-app-credentials）として登録されます。"
    
    return 0
}

# GitHub App設定の削除
remove_github_app_config() {
    log_section "GitHub App設定の削除"
    
    if ! confirm_action "GitHub App設定を削除しますか？"; then
        log_info "削除をキャンセルしました"
        return 0
    fi
    
    local REGION="${AWS_REGION:-ap-northeast-1}"
    local params=(
        "/bootstrap/github/app-id"
        "/bootstrap/github/app-private-key"
        "/bootstrap/github/app-owner"
    )
    
    for param in "${params[@]}"; do
        if aws ssm delete-parameter --name "$param" --region "$REGION" &>/dev/null; then
            log_info "✓ 削除: $param"
        else
            log_debug "パラメータが存在しないか削除済み: $param"
        fi
    done
    
    log_info "✅ GitHub App設定を削除しました"
    return 0
}

# GitHub App設定の表示（秘密鍵は表示しない）
show_github_app_config() {
    log_section "GitHub App設定の確認"
    
    local REGION="${AWS_REGION:-ap-northeast-1}"
    
    # App IDの確認
    local app_id=$(aws ssm get-parameter \
        --name "/bootstrap/github/app-id" \
        --region "$REGION" \
        --query 'Parameter.Value' \
        --output text 2>/dev/null)
    
    if [ -n "$app_id" ]; then
        echo "GitHub App設定:"
        echo "  - App ID: $app_id"
        
        # Ownerの確認
        local owner=$(aws ssm get-parameter \
            --name "/bootstrap/github/app-owner" \
            --region "$REGION" \
            --query 'Parameter.Value' \
            --output text 2>/dev/null)
        
        if [ -n "$owner" ]; then
            echo "  - Owner: $owner"
        fi
        
        # 秘密鍵の存在確認のみ
        if aws ssm get-parameter \
            --name "/bootstrap/github/app-private-key" \
            --region "$REGION" &>/dev/null; then
            echo "  - 秘密鍵: ✓ 設定済み"
        else
            echo "  - 秘密鍵: ✗ 未設定"
        fi
    else
        log_info "GitHub App設定が見つかりません"
    fi
    
    return 0
}