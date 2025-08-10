#!/bin/bash
# setup-bootstrap.sh - Jenkins CI/CD インフラストラクチャのブートストラップ環境セットアップスクリプト
# Amazon Linux 2023対応版
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=============================================${NC}"
echo -e "${BLUE}   Jenkins インフラストラクチャ ブートストラップセットアップ   ${NC}"
echo -e "${BLUE}   Amazon Linux 2023 Edition                 ${NC}"
echo -e "${BLUE}=============================================${NC}"
echo 

# OSバージョンの確認
echo -e "${GREEN}OS情報:${NC}"
cat /etc/os-release | grep -E "^(NAME|VERSION)" | sed 's/^/  /'
echo

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# リポジトリルートディレクトリに移動
cd "$REPO_ROOT"

# Python環境の確認
echo -e "${GREEN}Python環境の確認:${NC}"
python3 --version
pip3 --version
echo

# スクリプトの実行権限確認と修正
echo -e "${YELLOW}スクリプトファイルの実行権限を確認しています...${NC}"
SCRIPT_COUNT=0
FIXED_COUNT=0

check_script_permissions() {
  local dir=$1
  local pattern=$2
  
  if [ ! -d "$dir" ]; then
    echo -e "${RED}ディレクトリが見つかりません: $dir${NC}"
    return
  fi
  
  for script in $(find "$dir" -type f -name "$pattern"); do
    SCRIPT_COUNT=$((SCRIPT_COUNT+1))
    
    if [ ! -x "$script" ]; then
      echo -e "実行権限を付与: $script"
      chmod +x "$script"
      FIXED_COUNT=$((FIXED_COUNT+1))
    fi
  done
}

# スクリプトディレクトリ内のすべてのshファイルをチェック
check_script_permissions "$REPO_ROOT/scripts" "*.sh"

# Ansibleディレクトリ内のスクリプトをチェック
if [ -d "$REPO_ROOT/ansible/scripts" ]; then
  check_script_permissions "$REPO_ROOT/ansible/scripts" "*.sh"
fi

echo -e "${GREEN}スクリプトファイル実行権限の確認が完了しました。${NC}"
echo -e "${GREEN}検査したスクリプト数: $SCRIPT_COUNT${NC}"
if [ $FIXED_COUNT -gt 0 ]; then
  echo -e "${YELLOW}実行権限を付与したファイル数: $FIXED_COUNT${NC}"
else
  echo -e "${GREEN}すべてのスクリプトファイルに実行権限が付与されています。${NC}"
fi

# Ansibleプレイブックの格納場所
ANSIBLE_DIR="$REPO_ROOT/ansible"
PLAYBOOK_PATH="$ANSIBLE_DIR/playbooks/bootstrap-setup.yml"

# プレイブックの存在確認
if [ ! -f "$PLAYBOOK_PATH" ]; then
  echo -e "${YELLOW}エラー: ブートストラップセットアッププレイブックが見つかりません:${NC}"
  echo -e "${YELLOW}  $PLAYBOOK_PATH${NC}"
  echo -e "${YELLOW}リポジトリが正しくクローンされているか確認してください。${NC}"
  exit 1
fi

# SSHキー生成用の関数
generate_ssh_key() {
  echo -e "${YELLOW}GitHubリポジトリアクセス用のSSHキーを生成します。${NC}"
  echo -e "${YELLOW}すでにキーが存在する場合はスキップします。${NC}"
  
  if [ ! -f ~/.ssh/id_ed25519 ]; then
    read -p "GitHub用のメールアドレスを入力してください: " git_email
    ssh-keygen -t ed25519 -C "$git_email" -f ~/.ssh/id_ed25519 -N ""
    
    echo -e "\n${GREEN}SSHキーが生成されました。以下の公開キーをGitHubに登録してください:${NC}"
    echo -e "${BLUE}----------------------------------------${NC}"
    cat ~/.ssh/id_ed25519.pub
    echo -e "${BLUE}----------------------------------------${NC}"
    
    echo -e "\n${YELLOW}SSHキーをGitHubアカウントに追加するには:${NC}"
    echo -e "1. GitHubにログイン"
    echo -e "2. 右上のプロフィールアイコン → Settings"
    echo -e "3. 左側メニューの「SSH and GPG keys」→「New SSH key」"
    echo -e "4. タイトルを入力（例: EC2 Bootstrap Instance AL2023）"
    echo -e "5. 上記の公開キーを貼り付け"
    echo -e "6. 「Add SSH key」をクリック"
    
    read -p "GitHubにキーを追加したら Enter キーを押してください..."
  else
    echo -e "${GREEN}既存のSSHキーが見つかりました。新規生成をスキップします。${NC}"
  fi
}

# Ansibleの存在確認
echo -e "${YELLOW}Ansibleのインストール状況を確認しています...${NC}"
if ! command -v ansible-playbook &> /dev/null; then
    echo -e "${YELLOW}Ansibleがインストールされていません。インストールします...${NC}"
    sudo python3 -m pip install ansible
fi

# Ansibleプレイブックを実行
echo -e "${YELLOW}ブートストラップ環境をセットアップします...${NC}"
echo -e "${YELLOW}sudo権限が必要なため、パスワードの入力を求められる場合があります。${NC}"

# GitHubリポジトリ用のSSHキーがあるか確認
if [ ! -f ~/.ssh/id_ed25519 ]; then
  echo -e "\n${YELLOW}GitHubアクセス用のSSHキーが必要ですか？${NC}"
  read -p "SSHキーを生成しますか？ (y/N): " generate_key
  if [[ $generate_key =~ ^[Yy]$ ]]; then
    generate_ssh_key
  fi
fi

# Ansibleプレイブックを実行
echo -e "\n${YELLOW}Ansibleプレイブックを実行して環境をセットアップします...${NC}"

# 環境変数を設定
export PATH="$HOME/.local/bin:$PATH"
source ~/.bashrc

# ansible-playbookのパスを取得
ANSIBLE_PLAYBOOK_PATH=$(which ansible-playbook)
if [ -z "$ANSIBLE_PLAYBOOK_PATH" ]; then
  echo -e "${RED}ERROR: ansible-playbook コマンドが見つかりません。${NC}"
  exit 1
fi

echo -e "${GREEN}ansible-playbook の場所: $ANSIBLE_PLAYBOOK_PATH${NC}"

# 絶対パスで ansible-playbook を実行（Amazon Linux 2023では通常sudoは不要）
$ANSIBLE_PLAYBOOK_PATH "$PLAYBOOK_PATH" -v

# Pulumi初期設定の案内
echo -e "\n${BLUE}=== Pulumi設定 ===${NC}"

# CloudFormationスタックからPulumi S3バケット名を取得
echo -e "${YELLOW}Pulumi用S3バケットを確認しています...${NC}"
PULUMI_BUCKET=$(aws cloudformation describe-stacks --stack-name bootstrap-environment --query "Stacks[0].Outputs[?OutputKey=='PulumiStateBucketName'].OutputValue" --output text 2>/dev/null || echo "")

if [ -n "$PULUMI_BUCKET" ]; then
    echo -e "${GREEN}✓ Pulumi S3バケットが見つかりました: ${PULUMI_BUCKET}${NC}"
    
    # SSMパラメータストアからPULUMI_CONFIG_PASSPHRASEを確認
    PASSPHRASE_PARAM="/bootstrap/pulumi/config-passphrase"
    echo -e "${YELLOW}Pulumi設定パスフレーズを確認しています...${NC}"
    
    EXISTING_PASSPHRASE=$(aws ssm get-parameter --name "$PASSPHRASE_PARAM" --with-decryption --query 'Parameter.Value' --output text 2>/dev/null || echo "")
    
    if [ -n "$EXISTING_PASSPHRASE" ]; then
        echo -e "${GREEN}✓ Pulumi設定パスフレーズが既に設定されています${NC}"
        echo -e "${YELLOW}既存のパスフレーズを使用します${NC}"
    else
        echo -e "${YELLOW}Pulumi設定パスフレーズがまだ設定されていません${NC}"
        echo -e "${YELLOW}S3バックエンドのセキュリティのため、パスフレーズの設定が必要です${NC}"
        echo -e ""
        
        # 対話形式でパスフレーズ設定を確認
        read -p "Pulumi設定パスフレーズを設定しますか？ (Y/n): " setup_passphrase
        if [[ ! $setup_passphrase =~ ^[Nn]$ ]]; then
            echo -e "${YELLOW}パスフレーズの設定方法を選択してください:${NC}"
            echo -e "1) 自動生成（推奨）"
            echo -e "2) 手動入力"
            read -p "選択 (1/2): " passphrase_choice
            
            if [ "$passphrase_choice" = "2" ]; then
                # 手動入力
                while true; do
                    read -s -p "パスフレーズを入力してください（16文字以上推奨）: " passphrase1
                    echo
                    read -s -p "確認のためもう一度入力してください: " passphrase2
                    echo
                    
                    if [ "$passphrase1" != "$passphrase2" ]; then
                        echo -e "${RED}パスフレーズが一致しません。もう一度お試しください。${NC}"
                    elif [ ${#passphrase1} -lt 16 ]; then
                        echo -e "${RED}パスフレーズは16文字以上にしてください。${NC}"
                    else
                        PASSPHRASE="$passphrase1"
                        break
                    fi
                done
            else
                # 自動生成
                echo -e "${YELLOW}セキュアなパスフレーズを自動生成しています...${NC}"
                PASSPHRASE=$(openssl rand -base64 32 | tr -d '\n')
                echo -e "${GREEN}✓ パスフレーズが生成されました${NC}"
            fi
            
            # SSMパラメータストアに保存
            echo -e "${YELLOW}パスフレーズをSSMパラメータストアに保存しています...${NC}"
            if aws ssm put-parameter \
                --name "$PASSPHRASE_PARAM" \
                --value "$PASSPHRASE" \
                --type "SecureString" \
                --description "Pulumi configuration passphrase for S3 backend encryption" \
                --tags "Key=Name,Value=Pulumi-Config-Passphrase" "Key=Purpose,Value=Pulumi-Backend" \
                --region ${AWS::Region:-ap-northeast-1} 2>/dev/null; then
                echo -e "${GREEN}✓ パスフレーズがSSMパラメータストアに安全に保存されました${NC}"
                echo -e "${GREEN}  パラメータ名: $PASSPHRASE_PARAM${NC}"
            else
                echo -e "${RED}パスフレーズの保存に失敗しました${NC}"
                echo -e "${YELLOW}手動で以下のコマンドを実行してください:${NC}"
                echo -e "${GREEN}aws ssm put-parameter --name \"$PASSPHRASE_PARAM\" --value \"YOUR_PASSPHRASE\" --type \"SecureString\"${NC}"
            fi
        fi
    fi
    
    echo -e ""
    echo -e "${BLUE}=== Pulumi使用方法 ===${NC}"
    echo -e "${YELLOW}S3バックエンドを使用する場合（推奨）:${NC}"
    echo -e "${GREEN}# SSMから自動的にパスフレーズを取得${NC}"
    echo -e "${GREEN}export PULUMI_CONFIG_PASSPHRASE=\$(aws ssm get-parameter --name \"$PASSPHRASE_PARAM\" --with-decryption --query 'Parameter.Value' --output text)${NC}"
    echo -e "${GREEN}export PULUMI_STATE_BUCKET_NAME=\"${PULUMI_BUCKET}\"${NC}"
    echo -e ""
    echo -e "${YELLOW}パスフレーズの確認:${NC}"
    echo -e "${GREEN}aws ssm get-parameter --name \"$PASSPHRASE_PARAM\" --with-decryption --query 'Parameter.Value' --output text${NC}"
else
    echo -e "${YELLOW}Pulumi S3バケットが見つかりません。${NC}"
    echo -e "${YELLOW}CloudFormationスタック 'bootstrap-environment' が存在することを確認してください。${NC}"
fi

echo -e ""
echo -e "${YELLOW}代替オプション: Pulumi Cloudを使用する場合:${NC}"
echo -e "${GREEN}export PULUMI_ACCESS_TOKEN=\"pul-YOUR_ACCESS_TOKEN\"${NC}"
echo -e "${GREEN}# all.ymlでbackend_typeを'cloud'に変更するか、実行時に指定:${NC}"
echo -e "${GREEN}ansible-playbook jenkins_setup_pipeline.yml -e \"env=dev pulumi_backend_type=cloud\"${NC}"

# AWS認証情報の設定確認
echo -e "\n${BLUE}=== AWS認証情報 ===${NC}"
echo -e "${YELLOW}AWS認証情報を確認しています...${NC}"
if aws sts get-caller-identity &> /dev/null; then
    echo -e "${GREEN}✓ AWS認証情報は正しく設定されています${NC}"
    aws sts get-caller-identity --output table
else
    echo -e "${YELLOW}AWS認証情報が設定されていません。${NC}"
    if [ -f "$REPO_ROOT/scripts/aws/setup-aws-credentials.sh" ]; then
        echo -e "${GREEN}認証情報設定スクリプトを実行します...${NC}"
        source "$REPO_ROOT/scripts/aws/setup-aws-credentials.sh"
    else
        echo -e "${YELLOW}EC2インスタンスのIAMロールを使用している場合は、追加設定は不要です。${NC}"
    fi
fi

# Docker確認
echo -e "\n${BLUE}=== Docker状態 ===${NC}"
if command -v docker &> /dev/null; then
    echo -e "${GREEN}✓ Dockerがインストールされています${NC}"
    docker --version
    if docker ps &> /dev/null; then
        echo -e "${GREEN}✓ Dockerデーモンが実行中です${NC}"
    else
        echo -e "${YELLOW}Dockerデーモンが実行されていません。再ログインが必要かもしれません。${NC}"
    fi
else
    echo -e "${YELLOW}Dockerはインストールされていません${NC}"
fi

# セットアップ完了メッセージ
echo -e "\n${GREEN}=============================================${NC}"
echo -e "${GREEN}✅ ブートストラップ環境のセットアップが完了しました！${NC}"
echo -e "${GREEN}=============================================${NC}"

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
