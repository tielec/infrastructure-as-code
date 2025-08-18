#!/bin/bash
# setup-bootstrap.sh - Jenkins CI/CD インフラストラクチャのブートストラップ環境セットアップスクリプト
# Amazon Linux 2023対応版 (Refactored for readability)
set -e

# --- Globals ---
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# --- Function Definitions ---

# ウェルカムメッセージを表示
display_welcome_message() {
  echo -e "${BLUE}=============================================${NC}"
  echo -e "${BLUE}   Jenkins インフラストラクチャ ブートストラップセットアップ   ${NC}"
  echo -e "${BLUE}   Amazon Linux 2023 Edition                 ${NC}"
  echo -e "${BLUE}=============================================${NC}"
  echo 
}

# OSバージョンを確認
check_os_version() {
  echo -e "${GREEN}OS情報:${NC}"
  cat /etc/os-release | grep -E \"^(NAME|VERSION)\" | sed 's/^/  /'
  echo
}

# スクリプトの実行権限を修正
fix_script_permissions() {
  echo -e "${YELLOW}スクリプトファイルの実行権限を確認しています...${NC}"
  local script_count=0
  local fixed_count=0

  _check_and_fix() {
    local dir=$1
    local pattern=$2
    if [ ! -d "$dir" ]; then return; fi
    for script in $(find "$dir" -type f -name "$pattern"); do
      script_count=$((script_count+1))
      if [ ! -x "$script" ]; then
        echo -e "実行権限を付与: $script"
        chmod +x "$script"
        fixed_count=$((fixed_count+1))
      fi
    done
  }

  _check_and_fix "$REPO_ROOT/scripts" "*.sh"
  _check_and_fix "$REPO_ROOT/ansible/scripts" "*.sh"

  echo -e "${GREEN}スクリプトファイル実行権限の確認が完了しました。${NC}"
  echo -e "${GREEN}検査したスクリプト数: $script_count${NC}"
  if [ $fixed_count -gt 0 ]; then
    echo -e "${YELLOW}実行権限を付与したファイル数: $fixed_count${NC}"
  else
    echo -e "${GREEN}すべてのスクリプトファイルに実行権限が付与されています。${NC}"
  fi
}

# Ansibleプレイブックの存在を確認
verify_ansible_playbook_exists() {
  local playbook_path="$REPO_ROOT/ansible/playbooks/bootstrap-setup.yml"
  if [ ! -f "$playbook_path" ]; then
    echo -e "${RED}エラー: ブートストラップセットアッププレイブックが見つかりません: $playbook_path${NC}"
    exit 1
  fi
}

# --- SSH Key Functions ---
restore_ssh_key_from_ssm() {
  echo -e "${YELLOW}SSMパラメータストアからSSHキーを復元しています...${NC}"
  local private_key=$(aws ssm get-parameter --name "/bootstrap/github/ssh-private-key" --with-decryption --query 'Parameter.Value' --output text 2>/dev/null || echo "")
  local public_key=$(aws ssm get-parameter --name "/bootstrap/github/ssh-public-key" --query 'Parameter.Value' --output text 2>/dev/null || echo "")
  
  if [ -n "$private_key" ] && [ -n "$public_key" ]; then
    mkdir -p ~/.ssh && chmod 700 ~/.ssh
    echo "$private_key" > ~/.ssh/id_ed25519 && chmod 600 ~/.ssh/id_ed25519
    echo "$public_key" > ~/.ssh/id_ed25519.pub && chmod 644 ~/.ssh/id_ed25519.pub
    echo -e "${GREEN}✓ SSHキーが正常に復元されました${NC}"
    return 0
  fi
  return 1
}

save_ssh_key_to_ssm() {
  local git_email="$1"
  echo -e "${YELLOW}SSHキーをSSMパラメータストアに保存しています...${NC}"
  aws ssm put-parameter --name "/bootstrap/github/email" --value "$git_email" --type "String" --overwrite &>/dev/null
  aws ssm put-parameter --name "/bootstrap/github/ssh-private-key" --value "$(cat ~/.ssh/id_ed25519)" --type "SecureString" --overwrite &>/dev/null
  aws ssm put-parameter --name "/bootstrap/github/ssh-public-key" --value "$(cat ~/.ssh/id_ed25519.pub)" --type "String" --overwrite &>/dev/null
  echo -e "${GREEN}✓ SSHキーがSSMパラメータストアに安全に保存されました${NC}"
}

setup_github_ssh_keys() {
  echo -e "\n${YELLOW}GitHub SSH キーの設定を確認しています...${NC}"
  if [ -f ~/.ssh/id_ed25519 ]; then
    echo -e "${GREEN}✓ ローカルにSSHキーが既に存在します${NC}"
    return 0
  fi

  if restore_ssh_key_from_ssm; then
    echo -e "${GREEN}✓ SSMからのSSHキー復元に成功しました。${NC}"
  else
    echo -e "${YELLOW}新しいSSHキーを生成します。${NC}"
    read -p "GitHub用のメールアドレスを入力してください: " git_email
    ssh-keygen -t ed25519 -C "$git_email" -f ~/.ssh/id_ed25519 -N ""
    save_ssh_key_to_ssm "$git_email"
  fi

  echo -e "\n${BLUE}=== GitHub公開鍵 ===${NC}"
  echo -e "${YELLOW}以下の公開鍵がGitHubに登録されていることを確認してください:${NC}"
  cat ~/.ssh/id_ed25519.pub
  echo -e "${BLUE}----------------------------------------${NC}"
  read -p "GitHubにキーを追加したら Enter キーを押してください..."
}

# --- OpenAI API Key Function ---
setup_openai_api_key() {
  echo -e "\n${BLUE}=== OpenAI APIキー設定 ===${NC}"
  local param_name="/bootstrap/openai/api-key"
  echo -e "${YELLOW}OpenAI APIキーをSSMパラメータストアで確認しています...${NC}"
  
  if aws ssm get-parameter --name "$param_name" &>/dev/null; then
    echo -e "${GREEN}✓ OpenAI APIキーは既にSSMパラメータストアに設定されています。${NC}"
    return 0
  fi

  echo -e "${YELLOW}OpenAI APIキーが設定されていません。${NC}"
  read -p "今すぐ設定しますか？ (Y/n): " setup_now
  if [[ $setup_now =~ ^[Nn]$ ]]; then return 1; fi

  local api_key
  while true; do
    read -s -p "OpenAI APIキーを入力してください (sk-...) : " api_key; echo
    if [[ "$api_key" =~ ^sk- ]]; then break; fi
    echo -e "${RED}無効な形式です。APIキーは 'sk-' で始まる必要があります。${NC}"
  done

  echo -e "${YELLOW}APIキーをSSMパラメータストアに保存しています...${NC}"
  if aws ssm put-parameter --name "$param_name" --value "$api_key" --type \"SecureString\" --overwrite; then
    echo -e "${GREEN}✓ OpenAI APIキーがSSMパラメータストアに安全に保存されました${NC}"
  else
    echo -e "${RED}APIキーの保存に失敗しました${NC}"
  fi
}

# --- Core Setup Functions ---
ensure_ansible_installed() {
  echo -e "\n${YELLOW}Ansibleのインストール状況を確認しています...${NC}"
  if ! command -v ansible-playbook &> /dev/null; then
    echo -e "${YELLOW}Ansibleがインストールされていません。インストールします...${NC}"
    sudo python3 -m pip install ansible
  fi
  echo -e "${GREEN}✓ Ansibleはインストール済みです。${NC}"
}

run_bootstrap_playbook() {
  echo -e "\n${YELLOW}Ansibleプレイブックを実行して環境をセットアップします...${NC}"
  export PATH="$HOME/.local/bin:$PATH"
  ansible-playbook "$REPO_ROOT/ansible/playbooks/bootstrap-setup.yml" -v
}

setup_pulumi_backend() {
  echo -e "\n${BLUE}=== Pulumi設定 ===${NC}"
  echo -e "${YELLOW}Pulumi用S3バケットを確認しています...${NC}"
  local pulumi_bucket=$(aws cloudformation describe-stacks --stack-name bootstrap-iac-environment --query "Stacks[0].Outputs[?OutputKey=='PulumiStateBucketName'].OutputValue" --output text 2>/dev/null || echo "")
  if [ -z "$pulumi_bucket" ]; then
    echo -e "${RED}Pulumi S3バケットが見つかりません。CloudFormationスタックを確認してください。${NC}"
    return 1
  fi
  echo -e "${GREEN}✓ Pulumi S3バケット: ${pulumi_bucket}${NC}"

  local passphrase_param="/bootstrap/pulumi/config-passphrase"
  echo -e "${YELLOW}Pulumi設定パスフレーズを確認しています...${NC}"
  if aws ssm get-parameter --name "$passphrase_param" &>/dev/null; then
    echo -e "${GREEN}✓ Pulumi設定パスフレーズが既に設定されています${NC}"
    return 0
  fi

  echo -e "${YELLOW}Pulumi設定パスフレーズがまだ設定されていません${NC}"
  read -p "自動生成しますか？ (Y/n): " gen_passphrase
  if [[ $gen_passphrase =~ ^[Nn]$ ]]; then return 1; fi

  local passphrase=$(openssl rand -base64 32)
  echo -e "${YELLOW}パスフレーズをSSMパラメータストアに保存しています...${NC}"
  if aws ssm put-parameter --name "$passphrase_param" --value "$passphrase" --type \"SecureString\"
; then
    echo -e "${GREEN}✓ パスフレーズがSSMパラメータストアに安全に保存されました${NC}"
  else
    echo -e "${RED}パスフレーズの保存に失敗しました${NC}"
  fi
}

verify_aws_credentials() {
  echo -e "\n${BLUE}=== AWS認証情報 ===${NC}"
  echo -e "${YELLOW}AWS認証情報を確認しています...${NC}"
  if aws sts get-caller-identity &> /dev/null; then
    echo -e "${GREEN}✓ AWS認証情報は正しく設定されています${NC}"
    aws sts get-caller-identity --output table
  else
    echo -e "${RED}AWS認証情報が設定されていません。EC2インスタンスプロファイルを確認してください。${NC}"
    exit 1
  fi
}

check_docker_status() {
  echo -e "\n${BLUE}=== Docker状態 ===${NC}"
  if ! command -v docker &> /dev/null; then
    echo -e "${RED}Dockerはインストールされていません${NC}"
    return 1
  fi
  echo -e "${GREEN}✓ Dockerがインストールされています${NC}"
  if docker ps &> /dev/null; then
    echo -e "${GREEN}✓ Dockerデーモンが実行中です${NC}"
  else
    echo -e "${RED}Dockerデーモンが実行されていません。${NC}"
  fi
}

setup_auto_update_ip_service() {
  echo -e "\n${BLUE}=== Public IP自動更新サービスの設定 ===${NC}"
  local script_src="$REPO_ROOT/bootstrap/scripts/update-public-ip.sh"
  local service_src="$REPO_ROOT/bootstrap/scripts/update-public-ip.service"

  if [ ! -f "$script_src" ] || [ ! -f "$service_src" ]; then
    echo -e "${RED}エラー: IP自動更新用のスクリプトまたはサービスファイルが見つかりません。${NC}"
    return 1
  fi

  echo -e "${YELLOW}サービスをセットアップしています...${NC}"
  sudo mkdir -p /opt/bootstrap
  sudo cp "$script_src" /opt/bootstrap/
  sudo chmod +x /opt/bootstrap/update-public-ip.sh
  sudo cp "$service_src" /etc/systemd/system/
  sudo systemctl daemon-reload
  sudo systemctl enable --now update-public-ip.service
  echo -e "${GREEN}✓ Public IP自動更新サービスが正常に設定・起動されました${NC}"
}

# 完了メッセージを表示
display_summary() {
  echo -e "\n${GREEN}=============================================${NC}"
  echo -e "${GREEN}✅ ブートストラップ環境のセットアップが完了しました！${NC}"
  echo -e "=============================================${NC}"
  echo -e "\n${YELLOW}次のステップ:${NC}"
  echo -e "1. インストール確認: ${GREEN}./verify-installation.sh${NC}"
  echo -e "2. Jenkinsインフラのデプロイ: ${GREEN}cd ansible && ansible-playbook playbooks/jenkins_setup_pipeline.yml -e \"env=dev\"${NC}"
}

# --- Main Execution ---
main() {
  display_welcome_message
  check_os_version
  
  cd "$REPO_ROOT"
  
  fix_script_permissions
  verify_ansible_playbook_exists
  ensure_ansible_installed
  
  setup_github_ssh_keys
  run_bootstrap_playbook
  
  setup_pulumi_backend
  verify_aws_credentials
  setup_openai_api_key
  check_docker_status
  setup_auto_update_ip_service
  
  display_summary
}

# スクリプトの実行
main "$@"