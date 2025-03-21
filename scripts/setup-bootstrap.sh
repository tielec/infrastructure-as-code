#!/bin/bash
# setup-bootstrap.sh - Jenkins CI/CD インフラストラクチャのブートストラップ環境セットアップスクリプト
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=============================================${NC}"
echo -e "${BLUE}   Jenkins インフラストラクチャ ブートストラップセットアップ   ${NC}"
echo -e "${BLUE}=============================================${NC}"
echo 

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# リポジトリルートディレクトリに移動
cd "$REPO_ROOT"

# Ansibleプレイブックの格納場所
ANSIBLE_DIR="$REPO_ROOT/ansible"
PLAYBOOK_PATH="$ANSIBLE_DIR/bootstrap-setup.yml"

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
    echo -e "4. タイトルを入力（例: EC2 Bootstrap Instance）"
    echo -e "5. 上記の公開キーを貼り付け"
    echo -e "6. 「Add SSH key」をクリック"
    
    read -p "GitHubにキーを追加したら Enter キーを押してください..."
  else
    echo -e "${GREEN}既存のSSHキーが見つかりました。新規生成をスキップします。${NC}"
  fi
}

# Ansibleプレイブックを実行
echo -e "${YELLOW}ブートストラップ環境をセットアップします...${NC}"
echo -e "${YELLOW}sudo権限が必要なため、パスワードの入力を求められる場合があります。${NC}"

# GitHubリポジトリ用のSSHキーがあるか確認
# これは必要に応じてコメントアウト可能
if [ ! -f ~/.ssh/id_ed25519 ]; then
  generate_ssh_key
fi

# Ansibleプレイブックを実行
echo -e "\n${YELLOW}Ansibleプレイブックを実行して環境をセットアップします...${NC}"
sudo ansible-playbook "$PLAYBOOK_PATH" -v

# Pulumi初期設定の案内
echo -e "\n${YELLOW}Pulumiの初期設定を行います...${NC}"
echo -e "Pulumiアカウントへのログインが必要です。以下のいずれかを選択してください:"
echo -e "1. Pulumiクラウドアカウントにログイン（推奨）"
echo -e "2. ローカルバックエンドを使用"

read -p "選択してください [1/2]: " pulumi_choice

if [ "$pulumi_choice" = "1" ]; then
  echo -e "\n${YELLOW}Pulumiクラウドアカウントにログインします...${NC}"
  echo -e "ブラウザでPulumiアカウントにログインし、アクセストークンを取得するよう求められます。"
  pulumi login
elif [ "$pulumi_choice" = "2" ]; then
  echo -e "\n${YELLOW}Pulumiローカルバックエンドを設定します...${NC}"
  pulumi login --local
else
  echo -e "\n${YELLOW}選択が不正です。Pulumiのセットアップをスキップします。${NC}"
  echo -e "後で 'pulumi login' コマンドを実行して手動でセットアップしてください。"
fi

# AWS認証情報の設定
echo -e "\n${YELLOW}AWS認証情報を設定します...${NC}"
if [ -f "$REPO_ROOT/scripts/aws-credentials.sh" ]; then
  echo -e "${GREEN}scripts/aws-credentials.sh スクリプトが見つかりました。${NC}"
  source "$REPO_ROOT/scripts/aws-credentials.sh"
else
  echo -e "${YELLOW}AWS認証情報スクリプトが見つかりません。${NC}"
  echo -e "EC2インスタンスのIAMロールを使用するため、設定は不要かもしれません。"
  echo -e "必要に応じて、手動でAWS認証情報を設定してください。"
fi

# セットアップ完了メッセージ
echo -e "\n${GREEN}ブートストラップ環境のセットアップが完了しました！${NC}"
echo -e "\n${YELLOW}インストールされたツールを確認するには:${NC}"
echo -e "  ./verify-installation.sh"

echo -e "\n${YELLOW}次のステップ:${NC}"
echo -e "1. AWS認証情報が正しく設定されていることを確認:"
echo -e "   aws sts get-caller-identity"
echo -e "2. JenkinsインフラストラクチャのAnsibleプレイブックを実行:"
echo -e "   cd ansible/playbooks/"
echo -e "   ansible-playbook jenkins_setup_pipeline.yml -e \"env=dev\" --check"
echo -e "3. 問題がなければ、実際にデプロイを実行:"
echo -e "   ansible-playbook jenkins_setup_pipeline.yml -e \"env=dev\""

echo -e "\n${BLUE}=============================================${NC}"
echo -e "${BLUE}   セットアップ完了   ${NC}"
echo -e "${BLUE}=============================================${NC}"
