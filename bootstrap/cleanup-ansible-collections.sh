#!/bin/bash
# cleanup-ansible-collections.sh - Ansible Collectionsの重複を解消し最新版に更新

set -e

# カラー定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Ansible Collections クリーンアップツール${NC}"
echo -e "${BLUE}========================================${NC}"
echo

# 1. 現在の状態を確認
echo -e "${YELLOW}=== 現在のCollections状態を確認 ===${NC}"
echo -e "${YELLOW}ユーザー空間:${NC}"
ansible-galaxy collection list -p ~/.local/lib/python3.9/site-packages/ansible_collections 2>/dev/null | grep -E "(amazon\.aws|community\.aws|community\.general|ansible\.posix|community\.docker)" || echo "なし"

echo -e "\n${YELLOW}システム全体:${NC}"
ansible-galaxy collection list -p /usr/share/ansible/collections 2>/dev/null | grep -E "(amazon\.aws|community\.aws|community\.general|ansible\.posix|community\.docker)" || echo "なし"

# 2. 確認プロンプト
echo -e "\n${YELLOW}以下の処理を実行します:${NC}"
echo "1. ユーザー空間のAnsible Collectionsを削除"
echo "2. システム全体のCollectionsを最新版に更新"
echo "3. 環境変数を適切に設定"
echo
read -p "続行しますか？ (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${RED}処理を中止しました${NC}"
    exit 1
fi

# 3. ユーザー空間のCollectionsをバックアップ（念のため）
echo -e "\n${YELLOW}=== バックアップ作成 ===${NC}"
if [ -d ~/.local/lib/python3.9/site-packages/ansible_collections ]; then
    backup_dir=~/ansible_collections_backup_$(date +%Y%m%d_%H%M%S)
    echo "バックアップ先: $backup_dir"
    cp -r ~/.local/lib/python3.9/site-packages/ansible_collections $backup_dir
    echo -e "${GREEN}✓ バックアップ完了${NC}"
fi

# 4. ユーザー空間のCollectionsを削除
echo -e "\n${YELLOW}=== ユーザー空間のCollections削除 ===${NC}"
if [ -d ~/.local/lib/python3.9/site-packages/ansible_collections ]; then
    rm -rf ~/.local/lib/python3.9/site-packages/ansible_collections
    echo -e "${GREEN}✓ ユーザー空間のCollections削除完了${NC}"
else
    echo "ユーザー空間にCollectionsが見つかりません"
fi

# 5. 環境変数の設定確認
echo -e "\n${YELLOW}=== 環境変数の設定 ===${NC}"
if ! grep -q "ANSIBLE_COLLECTIONS_PATH" ~/.bashrc; then
    echo 'export ANSIBLE_COLLECTIONS_PATH="/usr/share/ansible/collections"' >> ~/.bashrc
    echo -e "${GREEN}✓ ~/.bashrcに環境変数を追加${NC}"
else
    echo "環境変数は既に設定されています"
fi

# 6. システム全体のCollectionsを最新版に更新
echo -e "\n${YELLOW}=== システム全体のCollections更新 ===${NC}"
echo "必要なCollectionsのみを最新版に更新します..."

# 必要なコレクションのリスト
collections=(
    "amazon.aws"
    "community.aws"
    "community.general"
    "ansible.posix"
    "community.docker"
)

# 各コレクションを更新
for collection in "${collections[@]}"; do
    echo -e "\n${BLUE}更新中: $collection${NC}"
    sudo ansible-galaxy collection install $collection --force -p /usr/share/ansible/collections
done

# 7. 不要なコレクションの削除（オプション）
echo -e "\n${YELLOW}=== 不要なCollectionsの確認 ===${NC}"
echo "以下のコレクションは通常のJenkins/Lambda環境では不要です:"
echo "- cisco.* (Cisco機器管理用)"
echo "- vmware.* (VMware管理用)"
echo "- fortinet.* (Fortinet機器管理用)"
echo "- その他のベンダー固有コレクション"
echo
read -p "不要なコレクションを削除しますか？ (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # 保持するコレクションのパターン
    keep_patterns=(
        "amazon\.aws"
        "community\.aws"
        "community\.general"
        "ansible\.posix"
        "community\.docker"
        "ansible\.utils"
        "ansible\.netcommon"
    )
    
    # システムコレクションディレクトリに移動
    cd /usr/share/ansible/collections/ansible_collections
    
    # 不要なコレクションを削除
    for vendor_dir in */; do
        vendor=${vendor_dir%/}
        keep=false
        
        # 保持パターンに一致するか確認
        for pattern in "${keep_patterns[@]}"; do
            if [[ "$vendor" =~ ^${pattern%%\.*}$ ]]; then
                keep=true
                break
            fi
        done
        
        if [ "$keep" = false ]; then
            echo "削除: $vendor"
            sudo rm -rf "$vendor"
        fi
    done
    
    echo -e "${GREEN}✓ 不要なコレクションの削除完了${NC}"
fi

# 8. 最終確認
echo -e "\n${YELLOW}=== 最終確認 ===${NC}"
export ANSIBLE_COLLECTIONS_PATH="/usr/share/ansible/collections"
echo -e "${BLUE}インストール済みのコレクション:${NC}"
ansible-galaxy collection list | grep -E "(amazon\.aws|community\.aws|community\.general|ansible\.posix|community\.docker)"

# 9. 動作確認
echo -e "\n${YELLOW}=== 動作確認 ===${NC}"
echo "amazon.awsコレクションのテスト..."
if ansible-doc amazon.aws.ec2_instance >/dev/null 2>&1; then
    echo -e "${GREEN}✓ amazon.awsコレクションは正常に動作しています${NC}"
else
    echo -e "${RED}✗ amazon.awsコレクションの動作確認に失敗${NC}"
fi

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}クリーンアップが完了しました！${NC}"
echo -e "${GREEN}========================================${NC}"
echo
echo "次の手順:"
echo "1. 新しいターミナルを開くか、以下を実行:"
echo "   source ~/.bashrc"
echo "2. 動作確認:"
echo "   ansible-galaxy collection list"
echo
echo "バックアップは以下に保存されています:"
echo "  ~/ansible_collections_backup_*"
echo "問題がなければ削除してください。"
