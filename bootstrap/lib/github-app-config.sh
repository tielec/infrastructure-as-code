#!/bin/bash
# github-app-config.sh - GitHub App設定管理ライブラリ

# GitHub App設定をセットアップ
setup_github_app() {
    # 引数チェック
    if [ $# -ne 1 ]; then
        log_error "使用方法: setup_github_app <REGION>"
        return 1
    fi

    local REGION="$1"

    log_section "GitHub App設定"
    
    # 既存のGitHub App設定を確認
    local APP_ID_PARAM="/bootstrap/github/app-id"
    local APP_KEY_PARAM="/bootstrap/github/app-private-key"
    local APP_OWNER_PARAM="/bootstrap/github/app-owner"
    
    # App IDの確認
    if aws ssm get-parameter --name "$APP_ID_PARAM" --region "$REGION" &>/dev/null; then
        log_info "✓ GitHub App IDは既に設定されています"
        
        # 秘密鍵の確認
        if aws ssm get-parameter --name "$APP_KEY_PARAM" --region "$REGION" &>/dev/null; then
            log_info "✓ GitHub App秘密鍵も設定されています"
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
    
    # 秘密鍵用のプレースホルダーパラメータを作成
    log_info "秘密鍵用のSSMパラメータを準備しています..."
    
    # プレースホルダーとして仮の秘密鍵形式の値でパラメータを作成（後で手動で更新）
    local placeholder_key="-----BEGIN PRIVATE KEY-----
PLACEHOLDER_PRIVATE_KEY
This is a placeholder. Please replace with your actual GitHub App private key.
-----END PRIVATE KEY-----"
    
    if aws ssm put-parameter \
        --name "$APP_KEY_PARAM" \
        --value "$placeholder_key" \
        --type "SecureString" \
        --description "GitHub App Private Key - Please update this manually" \
        --overwrite \
        --region "$REGION" &>/dev/null; then
        log_info "✓ 秘密鍵用のパラメータを作成しました"
    else
        log_warn "秘密鍵パラメータの作成に失敗しました（既に存在する可能性があります）"
    fi
    
    # 手動設定の指示を表示
    echo
    log_warn "================================================================"
    log_warn "重要: GitHub App秘密鍵を手動で設定してください"
    log_warn "================================================================"
    echo
    echo "GitHub Appの秘密鍵取得と変換手順："
    echo
    echo "1. GitHubでPrivate Keyをダウンロード:"
    echo "   - GitHub App設定ページ → Private keys → Generate a private key"
    echo "   - .pemファイルがダウンロードされます"
    echo
    echo "2. PKCS#1からPKCS#8形式に変換（Jenkinsで必要）:"
    echo -e "${GREEN}openssl pkcs8 -topk8 -inform PEM -outform PEM -nocrypt \\\\${NC}"
    echo -e "${GREEN}  -in github-app-key.pem \\\\${NC}"
    echo -e "${GREEN}  -out github-app-key-pkcs8.pem${NC}"
    echo
    echo "3. 変換した秘密鍵をSSMに登録:"
    echo -e "${GREEN}aws ssm put-parameter \\\\${NC}"
    echo -e "${GREEN}  --name \"$APP_KEY_PARAM\" \\\\${NC}"
    echo -e "${GREEN}  --value file://github-app-key-pkcs8.pem \\\\${NC}"
    echo -e "${GREEN}  --type SecureString \\\\${NC}"
    echo -e "${GREEN}  --overwrite \\\\${NC}"
    echo -e "${GREEN}  --region $REGION${NC}"
    echo
    echo "または、AWS Management Consoleから直接設定:"
    echo "  1. Systems Manager → Parameter Store を開く"
    echo "  2. パラメータ名: $APP_KEY_PARAM"
    echo "  3. 値: 変換後の秘密鍵の内容（PKCS#8形式）"
    echo
    echo "注意: GitHubからダウンロードした秘密鍵は通常PKCS#1形式（BEGIN RSA PRIVATE KEY）ですが、"
    echo "      JenkinsではPKCS#8形式（BEGIN PRIVATE KEY）が必要です。"
    echo
    
    # 秘密鍵が設定されるまで待機
    log_info "秘密鍵を設定したら、Enterキーを押して続行してください..."
    read -p ""
    
    # 秘密鍵が正しく設定されたか確認
    log_info "秘密鍵の設定を確認しています..."
    local stored_key=$(aws ssm get-parameter \
        --name "$APP_KEY_PARAM" \
        --with-decryption \
        --region "$REGION" \
        --query 'Parameter.Value' \
        --output text 2>/dev/null)
    
    if echo "$stored_key" | grep -q "PLACEHOLDER_PRIVATE_KEY"; then
        log_warn "秘密鍵がまだプレースホルダーのままです"
        
        if confirm_action "秘密鍵の設定をスキップして続行しますか？"; then
            log_warn "秘密鍵の設定をスキップしました。後で手動で設定してください。"
        else
            log_info "秘密鍵を設定してから、このスクリプトを再実行してください。"
            return 1
        fi
    elif echo "$stored_key" | grep -q "BEGIN PRIVATE KEY"; then
        log_info "✓ 秘密鍵が正しく設定されました（PKCS#8形式）"
    elif echo "$stored_key" | grep -q "BEGIN RSA PRIVATE KEY"; then
        log_warn "秘密鍵がPKCS#1形式です。PKCS#8形式への変換が必要です。"
        echo
        echo "変換コマンド:"
        echo -e "${GREEN}openssl pkcs8 -topk8 -inform PEM -outform PEM -nocrypt -in key.pem -out key-pkcs8.pem${NC}"
        echo
        if ! confirm_action "このまま続行しますか？"; then
            return 1
        fi
    else
        log_warn "秘密鍵の形式が認識できません"
        if ! confirm_action "このまま続行しますか？"; then
            return 1
        fi
    fi
    
    log_info "✅ GitHub App設定が完了しました"
    echo
    echo "設定されたGitHub App情報："
    echo "  - App ID: $app_id"
    if [ -n "$owner" ]; then
        echo "  - Owner: $owner"
    fi
    echo "  - 秘密鍵パラメータ: $APP_KEY_PARAM"
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