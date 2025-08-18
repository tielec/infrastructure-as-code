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

# SSMパラメータストアからSSHキーを復元する関数
restore_ssh_key_from_ssm() {
  echo -e "${YELLOW}SSMパラメータストアからSSHキーを復元しています...${NC}"
  
  # SSMから秘密鍵を取得
  PRIVATE_KEY=$(aws ssm get-parameter --name "/bootstrap/github/ssh-private-key" --with-decryption --query 'Parameter.Value' --output text 2>/dev/null || echo "")
  PUBLIC_KEY=$(aws ssm get-parameter --name "/bootstrap/github/ssh-public-key" --query 'Parameter.Value' --output text 2>/dev/null || echo "")
  
  if [ -n "$PRIVATE_KEY" ] && [ -n "$PUBLIC_KEY" ]; then
    # .sshディレクトリを作成
    mkdir -p ~/.ssh
    chmod 700 ~/.ssh
    
    # キーを復元
    echo "$PRIVATE_KEY" > ~/.ssh/id_ed25519
    echo "$PUBLIC_KEY" > ~/.ssh/id_ed25519.pub
    chmod 600 ~/.ssh/id_ed25519
    chmod 644 ~/.ssh/id_ed25519.pub
    
    echo -e "${GREEN}✓ SSHキーが正常に復元されました${NC}"
    return 0
  else
    return 1
  fi
}

# SSHキー生成用の関数
generate_ssh_key() {
  echo -e "${YELLOW}GitHubリポジトリアクセス用のSSHキーを設定します。${NC}"
  
  # まずSSMパラメータストアを確認
  echo -e "${YELLOW}SSMパラメータストアを確認しています...${NC}"
  
  # SSMから既存のキー情報を取得
  GIT_EMAIL=$(aws ssm get-parameter --name "/bootstrap/github/email" --query 'Parameter.Value' --output text 2>/dev/null || echo "")
  
  if [ -n "$GIT_EMAIL" ]; then
    echo -e "${GREEN}✓ 既存のGitHub設定が見つかりました (Email: $GIT_EMAIL)${NC}"
    
    # SSMからキーを復元
    if restore_ssh_key_from_ssm; then
      echo -e "${GREEN}✓ SSHキーの復元が完了しました${NC}"
      
      # 公開鍵を表示
      echo -e "\n${BLUE}=== GitHub公開鍵 ===${NC}"
      echo -e "${YELLOW}以下の公開鍵がGitHubに登録されていることを確認してください:${NC}"
      echo -e "${BLUE}----------------------------------------${NC}"
      cat ~/.ssh/id_ed25519.pub
      echo -e "${BLUE}----------------------------------------${NC}"
      return 0
    fi
  fi
  
  # 既存のローカルキーをチェック
  if [ -f ~/.ssh/id_ed25519 ]; then
    echo -e "${GREEN}ローカルに既存のSSHキーが見つかりました。${NC}"
    
    # SSMに保存されていない場合は保存するか確認
    if [ -z "$GIT_EMAIL" ]; then
      echo -e "${YELLOW}このキーをSSMパラメータストアに保存しますか？${NC}"
      echo -e "${YELLOW}（今後、新しいインスタンスでも同じキーを使用できます）${NC}"
      read -p "保存しますか？ (Y/n): " save_to_ssm
      
      if [[ ! $save_to_ssm =~ ^[Nn]$ ]]; then
        # メールアドレスを取得
        read -p "GitHub用のメールアドレスを入力してください: " git_email
        
        # SSMに保存
        save_ssh_key_to_ssm "$git_email"
      fi
    fi
    return 0
  fi
  
  # 新規キー生成
  echo -e "${YELLOW}新しいSSHキーを生成します。${NC}"
  
  # メールアドレスを取得（SSMから取得できなかった場合は入力を求める）
  if [ -z "$GIT_EMAIL" ]; then
    read -p "GitHub用のメールアドレスを入力してください: " git_email
  else
    git_email="$GIT_EMAIL"
    echo -e "${GREEN}メールアドレス: $git_email${NC}"
  fi
  
  # SSHキーを生成
  ssh-keygen -t ed25519 -C "$git_email" -f ~/.ssh/id_ed25519 -N ""
  
  # SSMに保存
  save_ssh_key_to_ssm "$git_email"
  
  # 公開鍵を表示
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
}

# SSHキーをSSMパラメータストアに保存する関数
save_ssh_key_to_ssm() {
  local git_email="$1"
  
  echo -e "${YELLOW}SSHキーをSSMパラメータストアに保存しています...${NC}"
  
  # メールアドレスを保存
  aws ssm put-parameter \
    --name "/bootstrap/github/email" \
    --value "$git_email" \
    --type "String" \
    --description "GitHub email address for SSH key" \
    --overwrite \
    2>/dev/null || echo -e "${YELLOW}メールアドレスの保存をスキップ${NC}"
  
  # 秘密鍵を保存（SecureString）
  aws ssm put-parameter \
    --name "/bootstrap/github/ssh-private-key" \
    --value "$(cat ~/.ssh/id_ed25519)" \
    --type "SecureString" \
    --description "GitHub SSH private key" \
    --overwrite \
    2>/dev/null || echo -e "${RED}秘密鍵の保存に失敗しました${NC}"
  
  # 公開鍵を保存
  aws ssm put-parameter \
    --name "/bootstrap/github/ssh-public-key" \
    --value "$(cat ~/.ssh/id_ed25519.pub)" \
    --type "String" \
    --description "GitHub SSH public key" \
    --overwrite \
    2>/dev/null || echo -e "${RED}公開鍵の保存に失敗しました${NC}"
  
  echo -e "${GREEN}✓ SSHキーがSSMパラメータストアに安全に保存されました${NC}"
  echo -e "${GREEN}  パラメータ:${NC}"
  echo -e "${GREEN}    - /bootstrap/github/email${NC}"
  echo -e "${GREEN}    - /bootstrap/github/ssh-private-key (暗号化)${NC}"
  echo -e "${GREEN}    - /bootstrap/github/ssh-public-key${NC}"
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

# GitHubリポジトリ用のSSHキーを設定
echo -e "\n${YELLOW}GitHub SSH キーの設定を確認しています...${NC}"

# SSMパラメータストアから既存のキーを確認
GIT_EMAIL_CHECK=$(aws ssm get-parameter --name "/bootstrap/github/email" --query 'Parameter.Value' --output text 2>/dev/null || echo "")

if [ -n "$GIT_EMAIL_CHECK" ]; then
  # SSMに設定が存在する場合は自動的に復元
  echo -e "${GREEN}✓ SSMパラメータストアにGitHub設定が見つかりました${NC}"
  
  if [ ! -f ~/.ssh/id_ed25519 ]; then
    # ローカルにキーがない場合は復元
    restore_ssh_key_from_ssm
  else
    echo -e "${GREEN}✓ ローカルにSSHキーが既に存在します${NC}"
  fi
else
  # SSMに設定がない場合
  if [ ! -f ~/.ssh/id_ed25519 ]; then
    echo -e "\n${YELLOW}GitHubアクセス用のSSHキーが設定されていません。${NC}"
    echo -e "${YELLOW}SSHキーを生成して、SSMパラメータストアに保存します。${NC}"
    generate_ssh_key
  else
    # ローカルにキーはあるがSSMにない場合
    echo -e "${GREEN}ローカルにSSHキーが見つかりました。${NC}"
    echo -e "${YELLOW}このキーをSSMパラメータストアに保存しますか？${NC}"
    read -p "保存しますか？ (Y/n): " save_existing
    
    if [[ ! $save_existing =~ ^[Nn]$ ]]; then
      read -p "GitHub用のメールアドレスを入力してください: " git_email
      save_ssh_key_to_ssm "$git_email"
    fi
  fi
fi

# Ansibleプレイブックを実行
echo -e "\n${YELLOW}Ansibleプレイブックを実行して環境をセットアップします...${NC}"

# 環境変数を設定
export PATH="$HOME/.local/bin:$PATH"
export ANSIBLE_COLLECTIONS_PATH="/usr/share/ansible/collections"
source ~/.bashrc

# 既存のcollectionsをクリーンアップ（ユーザー空間の重複を防ぐ）
if [ -d "$HOME/.local/lib/python3.9/site-packages/ansible_collections" ]; then
  echo -e "${YELLOW}ユーザー空間の既存のAnsible collectionsを検出しました。${NC}"
  echo -e "${YELLOW}システム全体のcollectionsを使用するため、ユーザー空間のcollectionsを削除します。${NC}"
  rm -rf "$HOME/.local/lib/python3.9/site-packages/ansible_collections"
  echo -e "${GREEN}✓ ユーザー空間のcollectionsをクリーンアップしました${NC}"
fi

# ansible-playbookのパスを取得
ANSIBLE_PLAYBOOK_PATH=$(which ansible-playbook)
if [ -z "$ANSIBLE_PLAYBOOK_PATH" ]; then
  echo -e "${RED}ERROR: ansible-playbook コマンドが見つかりません。${NC}"
  exit 1
fi

echo -e "${GREEN}ansible-playbook の場所: $ANSIBLE_PLAYBOOK_PATH${NC}"
echo -e "${GREEN}ANSIBLE_COLLECTIONS_PATH: $ANSIBLE_COLLECTIONS_PATH${NC}"

# 絶対パスで ansible-playbook を実行（Amazon Linux 2023では通常sudoは不要）
# インベントリファイルを明示的に指定
$ANSIBLE_PLAYBOOK_PATH "$PLAYBOOK_PATH" -i "$ANSIBLE_DIR/inventory/hosts" -v

# Pulumi初期設定の案内
echo -e "\n${BLUE}=== Pulumi設定 ===${NC}"

# CloudFormationスタックからPulumi S3バケット名を取得
echo -e "${YELLOW}Pulumi用S3バケットを確認しています...${NC}"
PULUMI_BUCKET=$(aws cloudformation describe-stacks --stack-name bootstrap-iac-environment --query "Stacks[0].Outputs[?OutputKey=='PulumiStateBucketName'].OutputValue" --output text 2>/dev/null || echo "")

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

# systemdサービスの設定（EC2起動時のPublic IP自動更新）
echo -e "\n${BLUE}=== Public IP自動更新サービスの設定 ===${NC}"
echo -e "${YELLOW}EC2起動時にPublic IPをSSMパラメータに自動更新するサービスを設定しています...${NC}"

# スクリプトファイルの存在確認
if [ -f "$REPO_ROOT/bootstrap/scripts/update-public-ip.sh" ]; then
    # スクリプトを/opt/bootstrapディレクトリにコピー
    sudo mkdir -p /opt/bootstrap
    sudo cp "$REPO_ROOT/bootstrap/scripts/update-public-ip.sh" /opt/bootstrap/
    sudo chmod +x /opt/bootstrap/update-public-ip.sh
    echo -e "${GREEN}✓ update-public-ip.shをコピーしました${NC}"
else
    echo -e "${RED}エラー: update-public-ip.shが見つかりません${NC}"
    echo -e "${YELLOW}  期待される場所: $REPO_ROOT/bootstrap/scripts/update-public-ip.sh${NC}"
fi

# systemdサービスファイルの存在確認とコピー
if [ -f "$REPO_ROOT/bootstrap/scripts/update-public-ip.service" ]; then
    sudo cp "$REPO_ROOT/bootstrap/scripts/update-public-ip.service" /etc/systemd/system/
    echo -e "${GREEN}✓ update-public-ip.serviceをコピーしました${NC}"
    
    # サービスを有効化
    sudo systemctl daemon-reload
    sudo systemctl enable update-public-ip.service
    
    # 現在のPublic IPを即座に更新
    if sudo systemctl start update-public-ip.service; then
        echo -e "${GREEN}✓ Public IP自動更新サービスが正常に設定されました${NC}"
        echo -e "${GREEN}  サービス名: update-public-ip.service${NC}"
        echo -e "${GREEN}  スクリプト: /opt/bootstrap/update-public-ip.sh${NC}"
        echo -e "${GREEN}  ログファイル: /var/log/update-public-ip.log${NC}"
        
        # 現在のPublic IPを表示
        CURRENT_IP=$(aws ssm get-parameter --name /bootstrap/workterminal/public-ip --query 'Parameter.Value' --output text 2>/dev/null || echo "取得失敗")
        echo -e "${GREEN}  現在のPublic IP: $CURRENT_IP${NC}"
    else
        echo -e "${YELLOW}⚠ Public IP更新サービスの初回実行に失敗しました${NC}"
        echo -e "${YELLOW}  手動で確認してください: sudo systemctl status update-public-ip.service${NC}"
    fi
else
    echo -e "${RED}エラー: update-public-ip.serviceが見つかりません${NC}"
    echo -e "${YELLOW}  期待される場所: $REPO_ROOT/bootstrap/scripts/update-public-ip.service${NC}"
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
