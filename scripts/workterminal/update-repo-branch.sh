#!/bin/bash

# インフラリポジトリのブランチ更新とJenkins設定更新スクリプト
#
# 使用方法:
#   ./update-repo-branch.sh [ブランチ名] [--ci]
#   
# 例:
#   ./update-repo-branch.sh          # 現在のブランチで最新化
#   ./update-repo-branch.sh main     # mainブランチに切り替え
#   ./update-repo-branch.sh fix-2025-08-19
#   ./update-repo-branch.sh main --ci  # CI環境での非対話実行

set -e  # エラーが発生したら即座に終了

# 色付き出力用の設定
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ヘルプメッセージ
show_help() {
    echo "使用方法: $0 [ブランチ名] [--ci]"
    echo ""
    echo "インフラストラクチャリポジトリを指定したブランチに更新し、"
    echo "Jenkins設定ファイルのブランチ指定も同時に更新します。"
    echo ""
    echo "引数を指定しない場合は、現在のブランチで最新の状態に更新します。"
    echo ""
    echo "オプション:"
    echo "  --ci    CI環境での非対話実行（確認プロンプトをスキップ）"
    echo ""
    echo "例:"
    echo "  $0                     # 現在のブランチで最新化"
    echo "  $0 main                # mainブランチに切り替え"
    echo "  $0 feature/new-feature # featureブランチに切り替え"
    echo "  $0 fix-2025-08-19      # 特定のfixブランチに切り替え"
    echo "  $0 main --ci           # CI環境でmainブランチに切り替え"
    exit 0
}

# エラーメッセージ表示関数
error_exit() {
    echo -e "${RED}エラー: $1${NC}" >&2
    exit 1
}

# 成功メッセージ表示関数
success_msg() {
    echo -e "${GREEN}✓ $1${NC}"
}

# 情報メッセージ表示関数
info_msg() {
    echo -e "${BLUE}→ $1${NC}"
}

# 警告メッセージ表示関数
warn_msg() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# CIモードフラグ
CI_MODE=false

# 引数の解析
BRANCH_NAME=""
for arg in "$@"; do
    case "$arg" in
        -h|--help)
            show_help
            ;;
        --ci)
            CI_MODE=true
            ;;
        *)
            if [ -z "$BRANCH_NAME" ]; then
                BRANCH_NAME="$arg"
            fi
            ;;
    esac
done

REPO_PATH="$HOME/infrastructure-as-code"
CONFIG_FILE="$REPO_PATH/ansible/inventory/group_vars/all.yml"

# リポジトリディレクトリの存在確認
if [ ! -d "$REPO_PATH" ]; then
    error_exit "リポジトリディレクトリが見つかりません: $REPO_PATH"
fi

if [ ! -d "$REPO_PATH/.git" ]; then
    error_exit "$REPO_PATH はGitリポジトリではありません"
fi

echo "=========================================="
echo " インフラストラクチャリポジトリ更新"
echo "=========================================="
echo ""

# 現在のディレクトリを保存
ORIGINAL_DIR=$(pwd)

# リポジトリディレクトリに移動
cd "$REPO_PATH" || error_exit "ディレクトリ移動に失敗: $REPO_PATH"

# 現在のブランチを取得
CURRENT_BRANCH=$(git branch --show-current)

# ブランチ名の決定（引数がなければ現在のブランチを使用）
if [ -z "$BRANCH_NAME" ]; then
    BRANCH_NAME="$CURRENT_BRANCH"
    info_msg "現在のブランチ '$BRANCH_NAME' で最新化します"
else
    if [ "$BRANCH_NAME" = "$CURRENT_BRANCH" ]; then
        info_msg "指定されたブランチは現在のブランチと同じです: $BRANCH_NAME"
    else
        info_msg "現在のブランチ: $CURRENT_BRANCH → 目標ブランチ: $BRANCH_NAME"
    fi
fi

# 未コミットの変更がないか確認
if ! git diff --quiet || ! git diff --cached --quiet; then
    warn_msg "未コミットの変更があります:"
    git status --short
    
    if [ "$CI_MODE" = true ]; then
        # CIモードでは自動的にstashして続行
        info_msg "CIモード: 変更を自動的に一時退避します..."
        git stash push -m "Auto-stash before branch update $(date +%Y%m%d_%H%M%S)" -- . ':!**/node_modules' || {
            warn_msg "node_modulesを除外したstashに失敗しました。通常のstashを試みます..."
            git stash push -m "Auto-stash before branch update $(date +%Y%m%d_%H%M%S)"
        }
        success_msg "変更を一時退避しました"
        STASHED=true
    else
        echo ""
        echo "どのように処理しますか？"
        echo "  1) 変更を破棄して続行"
        echo "  2) 変更を一時退避(stash)して続行"
        echo "  3) 操作をキャンセル"
        echo ""
        read -p "選択してください (1/2/3) [デフォルト: 3]: " -n 1 -r
        echo ""
        
        case "$REPLY" in
        1)
            read -p "本当に変更を破棄しますか？ (y/N): " -n 1 -r
            echo ""
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                info_msg "変更を破棄します..."
                
                # まずgitで管理されているファイルをリセット
                git reset --hard HEAD
                
                # node_modulesディレクトリの処理
                if find . -type d -name "node_modules" 2>/dev/null | grep -q .; then
                    warn_msg "node_modulesディレクトリが検出されました"
                    echo "node_modulesディレクトリをどう処理しますか？"
                    echo "  1) 削除する（sudoを使用）"
                    echo "  2) そのまま残す"
                    read -p "選択してください (1/2) [デフォルト: 2]: " -n 1 -r
                    echo ""
                    
                    if [[ $REPLY == "1" ]]; then
                        info_msg "node_modulesディレクトリを削除します..."
                        find . -type d -name "node_modules" -exec sudo rm -rf {} + 2>/dev/null || \
                            warn_msg "一部のnode_modulesディレクトリを削除できませんでした"
                    fi
                fi
                
                # 未追跡ファイルのクリーンアップ（node_modules以外）
                git clean -fd -e node_modules || {
                    warn_msg "一部のファイルを削除できませんでした。権限の問題がある可能性があります。"
                    echo "強制的に削除を試みますか？（sudoを使用）"
                    read -p "(y/N): " -n 1 -r
                    echo ""
                    if [[ $REPLY =~ ^[Yy]$ ]]; then
                        sudo git clean -fd -e node_modules
                    fi
                }
                
                success_msg "変更を破棄しました"
            else
                error_exit "操作をキャンセルしました"
            fi
            ;;
        2)
            info_msg "変更を一時退避します..."
            # node_modulesを除外してstash
            git stash push -m "Auto-stash before branch update $(date +%Y%m%d_%H%M%S)" -- . ':!**/node_modules' || {
                warn_msg "node_modulesを除外したstashに失敗しました。通常のstashを試みます..."
                git stash push -m "Auto-stash before branch update $(date +%Y%m%d_%H%M%S)"
            }
            success_msg "変更を一時退避しました"
            STASHED=true
            ;;
        *)
            error_exit "操作をキャンセルしました"
            ;;
        esac
    fi
fi

# リモートの最新情報を取得
info_msg "リモートリポジトリから最新情報を取得中..."
git fetch origin || error_exit "fetchに失敗しました"
success_msg "最新情報を取得しました"

# ブランチの切り替えまたは更新
if [ "$BRANCH_NAME" = "$CURRENT_BRANCH" ]; then
    # 同じブランチの場合は更新のみ
    if git show-ref --verify --quiet "refs/remotes/origin/$BRANCH_NAME"; then
        info_msg "リモートから最新の変更を取得中..."
        git pull origin "$BRANCH_NAME" || error_exit "pullに失敗しました"
        success_msg "ブランチを最新状態に更新しました"
    else
        warn_msg "リモートブランチ 'origin/$BRANCH_NAME' が存在しません（ローカルのみのブランチ）"
    fi
else
    # 異なるブランチへの切り替え
    if git show-ref --verify --quiet "refs/heads/$BRANCH_NAME"; then
        # ローカルブランチが存在する場合
        info_msg "ローカルブランチ '$BRANCH_NAME' に切り替えます..."
        git checkout "$BRANCH_NAME" || error_exit "ブランチ切り替えに失敗: $BRANCH_NAME"
        
        # リモートブランチが存在する場合はpull
        if git show-ref --verify --quiet "refs/remotes/origin/$BRANCH_NAME"; then
            info_msg "リモートから最新の変更を取得中..."
            git pull origin "$BRANCH_NAME" || error_exit "pullに失敗しました"
            success_msg "ブランチを最新状態に更新しました"
        else
            warn_msg "リモートブランチ 'origin/$BRANCH_NAME' が存在しません"
        fi
    elif git show-ref --verify --quiet "refs/remotes/origin/$BRANCH_NAME"; then
        # リモートブランチのみ存在する場合
        info_msg "リモートブランチ 'origin/$BRANCH_NAME' からローカルブランチを作成します..."
        git checkout -b "$BRANCH_NAME" "origin/$BRANCH_NAME" || error_exit "ブランチ作成に失敗: $BRANCH_NAME"
        success_msg "ブランチ '$BRANCH_NAME' を作成し、切り替えました"
    else
        error_exit "ブランチ '$BRANCH_NAME' がローカルにもリモートにも存在しません"
    fi
fi

# Jenkins設定ファイルの更新
echo ""
info_msg "Jenkins設定ファイルを更新中..."

if [ ! -f "$CONFIG_FILE" ]; then
    error_exit "設定ファイルが見つかりません: $CONFIG_FILE"
fi

# 現在の設定値を確認
CURRENT_CONFIG_BRANCH=$(grep -E "^\s*branch:" "$CONFIG_FILE" | sed 's/.*branch:[[:space:]]*"\(.*\)".*/\1/')

if [ "$CURRENT_CONFIG_BRANCH" = "$BRANCH_NAME" ]; then
    info_msg "Jenkins設定のブランチは既に '$BRANCH_NAME' です（変更不要）"
else
    # YAMLファイルのブランチ設定を更新
    # sedコマンドでjenkins.git.branchの値を更新
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s|^\([[:space:]]*\)branch:[[:space:]]*\".*\"|\\1branch: \"$BRANCH_NAME\"|" "$CONFIG_FILE"
    else
        # Linux
        sed -i "s|^\([[:space:]]*\)branch:[[:space:]]*\".*\"|\\1branch: \"$BRANCH_NAME\"|" "$CONFIG_FILE"
    fi

    # 変更が正しく適用されたか確認
    if grep -q "branch: \"$BRANCH_NAME\"" "$CONFIG_FILE"; then
        success_msg "Jenkins設定のブランチを '$CURRENT_CONFIG_BRANCH' → '$BRANCH_NAME' に更新しました"
        CONFIG_UPDATED=true
        
        # 変更内容を表示
        echo ""
        info_msg "設定ファイルの変更内容:"
        grep -A1 -B1 "branch:" "$CONFIG_FILE" | grep -E "(git:|branch:)" || true
    else
        error_exit "設定ファイルの更新に失敗しました"
    fi
fi

# 設定ファイルの変更をコミット（変更がある場合のみ）
if [ "$CONFIG_UPDATED" = true ]; then
    if [ "$CI_MODE" = true ]; then
        # CIモードでは自動的にコミット
        info_msg "CIモード: 設定ファイルの変更を自動的にコミットします"
        git add "$CONFIG_FILE"
        git commit -m "[config] Update Jenkins branch to $BRANCH_NAME" || warn_msg "コミットに失敗しました（変更がない可能性があります）"
        success_msg "変更をコミットしました"
    else
        echo ""
        read -p "設定ファイルの変更をコミットしますか？ (y/N): " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            git add "$CONFIG_FILE"
            git commit -m "[config] Update Jenkins branch to $BRANCH_NAME" || warn_msg "コミットに失敗しました（変更がない可能性があります）"
            success_msg "変更をコミットしました"
        fi
    fi
fi

# 元のディレクトリに戻る
cd "$ORIGINAL_DIR" || warn_msg "元のディレクトリに戻れませんでした: $ORIGINAL_DIR"

# 完了メッセージ
echo ""
echo "=========================================="
echo -e "${GREEN}✓ 更新完了${NC}"
echo "=========================================="
echo ""
echo "現在のブランチ: $BRANCH_NAME"
echo "設定ファイル: $CONFIG_FILE"

if [ "$STASHED" = true ]; then
    echo ""
    warn_msg "一時退避した変更があります。必要に応じて以下のコマンドで復元してください:"
    echo "  cd $REPO_PATH && git stash pop"
fi

if [ "$CONFIG_UPDATED" = true ]; then
    echo ""
    info_msg "Jenkins設定を反映するには、Jenkinsの設定デプロイを実行してください:"
    echo "  cd $REPO_PATH/ansible"
    echo "  ansible-playbook playbooks/jenkins/deploy/deploy_jenkins_config.yml -e env=dev"
fi