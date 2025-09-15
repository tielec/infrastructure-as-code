#!/bin/bash
# setup-bootstrap.sh - Jenkins CI/CD インフラストラクチャのブートストラップ環境セットアップスクリプト
# Amazon Linux 2023対応版

set -eo pipefail

# スクリプトディレクトリとリポジトリルートの設定
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
LIB_DIR="$SCRIPT_DIR/lib"

# 共通ライブラリの読み込み
source "$LIB_DIR/common.sh"
source "$LIB_DIR/script-permissions.sh"
source "$LIB_DIR/ssh-manager.sh"
source "$LIB_DIR/pulumi-config.sh"
source "$LIB_DIR/systemd-service.sh"
source "$LIB_DIR/openai-config.sh"
source "$LIB_DIR/github-app-config.sh"
source "$LIB_DIR/aws-account-config.sh"

# Ansibleプレイブックの格納場所
readonly ANSIBLE_DIR="$REPO_ROOT/ansible"
readonly PLAYBOOK_PATH="$ANSIBLE_DIR/playbooks/bootstrap-setup.yml"

# OS情報を表示
show_os_info() {
    log_info "OS情報:"
    cat /etc/os-release | grep -E "^(NAME|VERSION)" | sed 's/^/  /'
    echo
}

# Python環境の確認
check_python_environment() {
    log_info "Python環境の確認:"
    python3 --version || error_exit "Python3が見つかりません"
    pip3 --version || error_exit "pip3が見つかりません"
    echo
}

# Ansibleのインストール確認
ensure_ansible_installed() {
    log_info "Ansibleのインストール状況を確認しています..."
    
    if ! check_command "ansible-playbook"; then
        log_warn "Ansibleがインストールされていません。インストールします..."
        sudo python3 -m pip install ansible || error_exit "Ansibleのインストールに失敗しました"
    else
        log_info "✓ Ansibleは既にインストールされています"
    fi
}

# Ansible環境の準備
prepare_ansible_environment() {
    # 環境変数を設定
    export PATH="$HOME/.local/bin:$PATH"
    export ANSIBLE_COLLECTIONS_PATH="/usr/share/ansible/collections"
    
    # bashrcから環境変数を読み込み（エラーを無視）
    if [ -f ~/.bashrc ]; then
        source ~/.bashrc 2>/dev/null || true
    fi
    
    # 既存のcollectionsをクリーンアップ（ユーザー空間の重複を防ぐ）
    local user_collections="$HOME/.local/lib/python3.9/site-packages/ansible_collections"
    if [ -d "$user_collections" ]; then
        log_warn "ユーザー空間の既存のAnsible collectionsを検出しました"
        log_warn "システム全体のcollectionsを使用するため、ユーザー空間のcollectionsを削除します"
        rm -rf "$user_collections"
        log_info "✓ ユーザー空間のcollectionsをクリーンアップしました"
    fi
    
    # ansible-playbookのパスを確認
    local ansible_playbook_path=$(which ansible-playbook)
    if [ -z "$ansible_playbook_path" ]; then
        error_exit "ansible-playbook コマンドが見つかりません"
    fi
    
    log_info "ansible-playbook の場所: $ansible_playbook_path"
    log_info "ANSIBLE_COLLECTIONS_PATH: $ANSIBLE_COLLECTIONS_PATH"
}

# Ansibleプレイブックを実行
run_ansible_playbook() {
    log_section "Ansibleプレイブック実行"
    log_info "Ansibleプレイブックを実行して環境をセットアップします..."
    
    # プレイブックの存在確認
    if ! ensure_file "$PLAYBOOK_PATH"; then
        error_exit "ブートストラップセットアッププレイブックが見つかりません: $PLAYBOOK_PATH"
    fi
    
    # ansible-playbookを実行
    local ansible_cmd=$(which ansible-playbook)
    $ansible_cmd "$PLAYBOOK_PATH" -i "$ANSIBLE_DIR/inventory/hosts" -v || {
        log_error "Ansibleプレイブックの実行に失敗しました"
        return 1
    }
    
    return 0
}

# AWS認証情報の確認
check_aws_credentials() {
    log_section "AWS認証情報"
    log_info "AWS認証情報を確認しています..."
    
    if aws sts get-caller-identity &> /dev/null; then
        log_info "✓ AWS認証情報は正しく設定されています"
        aws sts get-caller-identity --output table
    else
        log_warn "AWS認証情報が設定されていません"
        
        local setup_script="$REPO_ROOT/scripts/aws/setup-aws-credentials.sh"
        if [ -f "$setup_script" ]; then
            log_info "認証情報設定スクリプトを実行します..."
            source "$setup_script"
        else
            log_warn "EC2インスタンスのIAMロールを使用している場合は、追加設定は不要です"
        fi
    fi
}

# Dockerの状態確認
check_docker_status() {
    log_section "Docker状態"
    
    if check_command "docker"; then
        log_info "✓ Dockerがインストールされています"
        docker --version
        
        if docker ps &> /dev/null; then
            log_info "✓ Dockerデーモンが実行中です"
        else
            log_warn "Dockerデーモンが実行されていません。再ログインが必要かもしれません"
        fi
    else
        log_warn "Dockerはインストールされていません"
    fi
}

# セットアップ完了メッセージ
show_completion_message() {
    log_header "✅ ブートストラップ環境のセットアップが完了しました！"
    
    echo -e "\n${BLUE}インストールされたツール:${NC}"
    echo -e "  - AWS CLI v2 (最新版)"
    echo -e "  - Node.js 20 LTS"
    echo -e "  - Java 21 (Amazon Corretto)"
    echo -e "  - Python 3.9+"
    echo -e "  - Ansible with AWS collections (7.0+)"
    echo -e "  - Pulumi (最新版)"
    echo -e "  - Docker"
    
    echo -e "\n${YELLOW}次のステップ:${NC}"
    echo -e "1. インストール確認:"
    echo -e "   ${GREEN}./verify-installation.sh${NC}"
    echo -e ""
    echo -e "2. Jenkinsインフラのデプロイ:"
    echo -e "   ${GREEN}cd ansible/playbooks/${NC}"
    echo -e "   ${GREEN}ansible-playbook jenkins_setup_pipeline.yml -e \"env=dev\" --check${NC}"
    echo -e ""
    echo -e "3. 本番デプロイ:"
    echo -e "   ${GREEN}ansible-playbook jenkins_setup_pipeline.yml -e \"env=dev\"${NC}"
    
    echo -e "\n${BLUE}詳細な情報は ~/README.txt を参照してください。${NC}"
}

# メイン処理
main() {
    # デフォルトリージョンの取得
    local DEFAULT_REGION

    # IMDSv2を使用してEC2インスタンスメタデータからリージョンを取得
    local TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600" 2>/dev/null || echo "")
    if [ -n "$TOKEN" ]; then
        DEFAULT_REGION=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/dynamic/instance-identity/document | grep region | cut -d'"' -f4 || echo "")
    fi

    # 取得できない場合はエラー
    if [ -z "$DEFAULT_REGION" ]; then
        log_error "EC2インスタンスメタデータからリージョンを取得できませんでした"
        log_error "EC2インスタンス上で実行されていることを確認してください"
        exit 1
    fi

    # リージョンの設定（引数があれば優先、なければデフォルト使用）
    local REGION
    if [ $# -ge 1 ]; then
        REGION="$1"
        log_info "指定されたリージョンを使用: $REGION"
    else
        REGION="$DEFAULT_REGION"
        log_info "現在のAWS設定からリージョンを自動検出: $REGION"
    fi

    export AWS_REGION="$REGION"

    # ヘッダー表示
    log_header "Jenkins インフラストラクチャ ブートストラップセットアップ\n   Amazon Linux 2023 Edition\n   Region: $REGION"
    
    # リポジトリルートディレクトリに移動
    cd "$REPO_ROOT"
    
    # === 軽量な前提条件チェック ===
    # OS情報表示（軽量）
    show_os_info
    
    # Python環境の確認（軽量）
    check_python_environment
    
    # スクリプトの実行権限を修正（軽量・ローカル処理）
    fix_all_script_permissions "$REPO_ROOT"
    
    # Docker状態確認（軽量・状態確認のみ）
    check_docker_status
    
    # === AWS関連の設定（ネットワーク処理を含む） ===
    # AWS認証情報の確認（早期に実行して後続処理でAWSリソースにアクセスできることを確認）
    check_aws_credentials
    
    # AWSアカウントIDの設定（SSMパラメータストア）
    setup_aws_account_ids "$REGION"
    
    # SSH鍵の設定（SSMアクセスを含むが対話的処理が含まれる可能性）
    setup_ssh_keys "$REGION"
    
    # OpenAI APIキーの設定（SSMアクセスを含む）
    setup_openai_api_key "$REGION"
    
    # GitHub App設定（SSMアクセスを含む）
    setup_github_app "$REGION"
    
    # Pulumi設定（AWS認証後に実行、SSMアクセスを含む）
    setup_pulumi_config "$REGION"
    
    # === 重い処理（インストールと実行） ===
    # Ansibleのインストール（パッケージインストールを含む可能性）
    ensure_ansible_installed
    
    # Ansible環境の準備（ディレクトリクリーンアップを含む）
    prepare_ansible_environment
    
    # Ansibleプレイブック実行（最も重い処理）
    run_ansible_playbook
    
    # systemdサービスの設定（システム設定変更）
    setup_public_ip_service "$REPO_ROOT"
    
    # 完了メッセージ
    show_completion_message
}

# エラーハンドリング
trap 'log_error "エラーが発生しました (行: $LINENO, コマンド: $BASH_COMMAND)"' ERR

# メイン処理を実行
main "$@"

# 正常終了
exit 0