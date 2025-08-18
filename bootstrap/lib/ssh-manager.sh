#!/bin/bash
# ssh-manager.sh - SSH鍵管理関数

# 依存関係
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

# SSHキー関連のSSMパラメータ
readonly SSH_EMAIL_PARAM="/bootstrap/github/email"
readonly SSH_PRIVATE_KEY_PARAM="/bootstrap/github/ssh-private-key"
readonly SSH_PUBLIC_KEY_PARAM="/bootstrap/github/ssh-public-key"
readonly SSH_KEY_PATH="$HOME/.ssh/id_ed25519"

# SSMからSSHキーを復元
restore_ssh_key_from_ssm() {
    log_info "SSMパラメータストアからSSHキーを復元しています..."
    
    local private_key=$(aws ssm get-parameter \
        --name "$SSH_PRIVATE_KEY_PARAM" \
        --with-decryption \
        --query 'Parameter.Value' \
        --output text 2>/dev/null || echo "")
    
    local public_key=$(aws ssm get-parameter \
        --name "$SSH_PUBLIC_KEY_PARAM" \
        --query 'Parameter.Value' \
        --output text 2>/dev/null || echo "")
    
    if [ -n "$private_key" ] && [ -n "$public_key" ]; then
        # .sshディレクトリを作成
        mkdir -p ~/.ssh
        chmod 700 ~/.ssh
        
        # キーを復元
        echo "$private_key" > "$SSH_KEY_PATH"
        echo "$public_key" > "${SSH_KEY_PATH}.pub"
        chmod 600 "$SSH_KEY_PATH"
        chmod 644 "${SSH_KEY_PATH}.pub"
        
        log_info "✓ SSHキーが正常に復元されました"
        return 0
    else
        return 1
    fi
}

# SSHキーをSSMに保存
save_ssh_key_to_ssm() {
    local git_email="$1"
    
    log_info "SSHキーをSSMパラメータストアに保存しています..."
    
    # メールアドレスを保存
    if aws ssm put-parameter \
        --name "$SSH_EMAIL_PARAM" \
        --value "$git_email" \
        --type "String" \
        --description "GitHub email address for SSH key" \
        --overwrite \
        2>/dev/null; then
        log_info "✓ メールアドレスを保存しました"
    else
        log_warn "メールアドレスの保存をスキップ"
    fi
    
    # 秘密鍵を保存（SecureString）
    if aws ssm put-parameter \
        --name "$SSH_PRIVATE_KEY_PARAM" \
        --value "$(cat "$SSH_KEY_PATH")" \
        --type "SecureString" \
        --description "GitHub SSH private key" \
        --overwrite \
        2>/dev/null; then
        log_info "✓ 秘密鍵を保存しました"
    else
        log_error "秘密鍵の保存に失敗しました"
        return 1
    fi
    
    # 公開鍵を保存
    if aws ssm put-parameter \
        --name "$SSH_PUBLIC_KEY_PARAM" \
        --value "$(cat "${SSH_KEY_PATH}.pub")" \
        --type "String" \
        --description "GitHub SSH public key" \
        --overwrite \
        2>/dev/null; then
        log_info "✓ 公開鍵を保存しました"
    else
        log_error "公開鍵の保存に失敗しました"
        return 1
    fi
    
    log_info "✓ SSHキーがSSMパラメータストアに安全に保存されました"
    log_info "  パラメータ:"
    log_info "    - $SSH_EMAIL_PARAM"
    log_info "    - $SSH_PRIVATE_KEY_PARAM (暗号化)"
    log_info "    - $SSH_PUBLIC_KEY_PARAM"
    
    return 0
}

# 公開鍵を表示
display_public_key() {
    log_section "GitHub公開鍵"
    log_warn "以下の公開鍵をGitHubに登録してください:"
    echo -e "${BLUE}----------------------------------------${NC}"
    cat "${SSH_KEY_PATH}.pub"
    echo -e "${BLUE}----------------------------------------${NC}"
}

# GitHub登録手順を表示
show_github_instructions() {
    echo -e "\n${YELLOW}SSHキーをGitHubアカウントに追加するには:${NC}"
    echo -e "1. GitHubにログイン"
    echo -e "2. 右上のプロフィールアイコン → Settings"
    echo -e "3. 左側メニューの「SSH and GPG keys」→「New SSH key」"
    echo -e "4. タイトルを入力（例: EC2 Bootstrap Instance AL2023）"
    echo -e "5. 上記の公開キーを貼り付け"
    echo -e "6. 「Add SSH key」をクリック"
}

# SSHキーを生成
generate_new_ssh_key() {
    local git_email="$1"
    
    log_info "新しいSSHキーを生成しています..."
    
    # SSHキーを生成
    ssh-keygen -t ed25519 -C "$git_email" -f "$SSH_KEY_PATH" -N ""
    
    if [ $? -eq 0 ]; then
        log_info "✓ SSHキーが生成されました"
        return 0
    else
        log_error "SSHキーの生成に失敗しました"
        return 1
    fi
}

# メールアドレスを取得
get_git_email() {
    local existing_email=$(aws ssm get-parameter \
        --name "$SSH_EMAIL_PARAM" \
        --query 'Parameter.Value' \
        --output text 2>/dev/null || echo "")
    
    if [ -n "$existing_email" ]; then
        echo "$existing_email"
    else
        read -p "GitHub用のメールアドレスを入力してください: " git_email
        echo "$git_email"
    fi
}

# SSHキーのセットアップメイン処理
setup_ssh_keys() {
    log_section "GitHub SSH キーの設定"
    
    # SSMから既存の設定を確認
    local git_email_check=$(aws ssm get-parameter \
        --name "$SSH_EMAIL_PARAM" \
        --query 'Parameter.Value' \
        --output text 2>/dev/null || echo "")
    
    if [ -n "$git_email_check" ]; then
        log_info "✓ SSMパラメータストアにGitHub設定が見つかりました"
        
        if [ ! -f "$SSH_KEY_PATH" ]; then
            # ローカルにキーがない場合は復元
            if restore_ssh_key_from_ssm; then
                display_public_key
                return 0
            fi
        else
            log_info "✓ ローカルにSSHキーが既に存在します"
            return 0
        fi
    fi
    
    # 既存のローカルキーをチェック
    if [ -f "$SSH_KEY_PATH" ]; then
        log_info "ローカルに既存のSSHキーが見つかりました"
        
        if [ -z "$git_email_check" ]; then
            if confirm_action "このキーをSSMパラメータストアに保存しますか？" "y"; then
                local git_email=$(get_git_email)
                save_ssh_key_to_ssm "$git_email"
            fi
        fi
        return 0
    fi
    
    # 新規キー生成
    log_warn "SSHキーが設定されていません"
    
    if confirm_action "新しいSSHキーを生成しますか？" "y"; then
        local git_email=$(get_git_email)
        
        if generate_new_ssh_key "$git_email"; then
            save_ssh_key_to_ssm "$git_email"
            display_public_key
            show_github_instructions
            
            read -p "GitHubにキーを追加したら Enter キーを押してください..."
        fi
    fi
    
    return 0
}