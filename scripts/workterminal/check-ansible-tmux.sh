#!/bin/bash
# ==============================================================================
# スクリプト名: check-ansible-tmux.sh
# 説明: Workterminalで実行中のJenkins Ansibleタスクを確認
# 使用方法: ./check-ansible-tmux.sh [options]
# オプション:
#   -a, --all       すべてのセッション詳細を表示
#   -l, --list      セッション一覧のみ表示
#   -s, --session   特定のセッションを確認（例: -s ansible_jenkins_deploy_1）
#   -k, --kill      古いセッションをクリーンアップ
# ==============================================================================

set -euo pipefail

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ヘルプ関数
show_help() {
    echo "使用方法: $0 [options]"
    echo ""
    echo "オプション:"
    echo "  -a, --all       すべてのセッション詳細を表示"
    echo "  -l, --list      セッション一覧のみ表示"
    echo "  -s, --session   特定のセッションを確認"
    echo "  -k, --kill      古いセッションをクリーンアップ"
    echo "  -h, --help      このヘルプを表示"
}

# セッション一覧表示
list_sessions() {
    echo -e "${BLUE}=== Jenkins Ansible TMUXセッション ===${NC}"
    if tmux ls 2>/dev/null | grep -E "^ansible_" > /dev/null; then
        tmux ls 2>/dev/null | grep -E "^ansible_" | while read -r line; do
            session_name=$(echo "$line" | cut -d: -f1)
            created=$(echo "$line" | sed 's/.*created //')
            echo -e "${GREEN}✓${NC} $session_name (作成: $created)"
            
            # ジョブ名とビルド番号を解析
            if [[ $session_name =~ ansible_(.+)_([0-9]+)$ ]]; then
                job_name="${BASH_REMATCH[1]}"
                build_num="${BASH_REMATCH[2]}"
                echo -e "  ジョブ: ${YELLOW}$job_name${NC}"
                echo -e "  ビルド: #$build_num"
            fi
        done
    else
        echo -e "${YELLOW}実行中のセッションはありません${NC}"
    fi
}

# セッション詳細表示
show_session_details() {
    local session=$1
    
    if ! tmux has-session -t "$session" 2>/dev/null; then
        echo -e "${RED}セッション '$session' が見つかりません${NC}"
        return 1
    fi
    
    echo -e "${BLUE}=== セッション: $session ===${NC}"
    
    # ウィンドウ一覧
    echo -e "${GREEN}ウィンドウ:${NC}"
    tmux list-windows -t "$session" -F '  #{window_index}: #{window_name} (#{pane_current_command})'
    
    # 各ウィンドウの最新ログ
    echo -e "${GREEN}最新ログ:${NC}"
    for window in $(tmux list-windows -t "$session" -F '#{window_index}'); do
        echo -e "  ${YELLOW}Window $window:${NC}"
        tmux capture-pane -t "${session}:${window}" -p -S -10 2>/dev/null | sed 's/^/    /' || echo "    (ログなし)"
        echo ""
    done
}

# すべてのセッション詳細表示
show_all_details() {
    if tmux ls 2>/dev/null | grep -E "^ansible_" > /dev/null; then
        for session in $(tmux ls 2>/dev/null | grep -E "^ansible_" | cut -d: -f1); do
            show_session_details "$session"
            echo ""
        done
    else
        echo -e "${YELLOW}実行中のセッションはありません${NC}"
    fi
}

# 古いセッションのクリーンアップ
cleanup_old_sessions() {
    echo -e "${BLUE}=== 古いセッションのクリーンアップ ===${NC}"
    
    # 24時間以上前のセッションを検出
    current_time=$(date +%s)
    cleaned=0
    
    if tmux ls 2>/dev/null | grep -E "^ansible_" > /dev/null; then
        while IFS= read -r line; do
            session_name=$(echo "$line" | cut -d: -f1)
            
            # セッションの作成時刻を取得（概算）
            if tmux show-environment -t "$session_name" 2>/dev/null | grep -q "TMUX_SESSION_CREATED"; then
                created_time=$(tmux show-environment -t "$session_name" | grep "TMUX_SESSION_CREATED" | cut -d= -f2)
                age=$((current_time - created_time))
                
                # 24時間（86400秒）以上古い場合
                if [ $age -gt 86400 ]; then
                    echo -e "${YELLOW}削除:${NC} $session_name ($(($age / 3600))時間前)"
                    tmux kill-session -t "$session_name"
                    cleaned=$((cleaned + 1))
                fi
            fi
        done < <(tmux ls 2>/dev/null | grep -E "^ansible_")
    fi
    
    if [ $cleaned -eq 0 ]; then
        echo -e "${GREEN}クリーンアップ対象のセッションはありません${NC}"
    else
        echo -e "${GREEN}$cleaned 個のセッションを削除しました${NC}"
    fi
    
    # 一時ファイルのクリーンアップ
    echo -e "${BLUE}一時ファイルのクリーンアップ...${NC}"
    find /tmp -name "ansible_*_*.log" -mtime +1 -delete 2>/dev/null || true
    find /tmp -name "ansible_*_*.timeout" -mtime +1 -delete 2>/dev/null || true
    echo -e "${GREEN}完了${NC}"
}

# プロセス状況表示
show_processes() {
    echo -e "${BLUE}=== Ansibleプロセス ===${NC}"
    if ps aux | grep -v grep | grep ansible-playbook > /dev/null; then
        ps aux | grep -v grep | grep ansible-playbook | while read -r line; do
            pid=$(echo "$line" | awk '{print $2}')
            cmd=$(echo "$line" | awk '{for(i=11;i<=NF;i++) printf "%s ", $i}')
            echo -e "${GREEN}✓${NC} PID: $pid"
            echo -e "  コマンド: ${cmd:0:100}..."
        done
    else
        echo -e "${YELLOW}実行中のAnsibleプロセスはありません${NC}"
    fi
}

# メイン処理
main() {
    case "${1:-}" in
        -a|--all)
            list_sessions
            echo ""
            show_all_details
            echo ""
            show_processes
            ;;
        -l|--list)
            list_sessions
            ;;
        -s|--session)
            if [ -z "${2:-}" ]; then
                echo -e "${RED}エラー: セッション名を指定してください${NC}"
                exit 1
            fi
            show_session_details "$2"
            ;;
        -k|--kill)
            cleanup_old_sessions
            ;;
        -h|--help)
            show_help
            ;;
        *)
            # デフォルト表示
            list_sessions
            echo ""
            show_processes
            echo ""
            echo -e "${BLUE}詳細を見るには -a オプションを使用してください${NC}"
            echo -e "${BLUE}特定のセッションにアタッチ: tmux attach -t [セッション名]${NC}"
            ;;
    esac
}

# スクリプト実行
main "$@"