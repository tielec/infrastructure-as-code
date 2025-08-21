#!/bin/bash
#
# run-ansible-in-tmux.sh
# 
# 説明: Ansibleプレイブックをtmuxセッション内で実行し、完了を監視する
# 
# 使用方法:
#   ./run-ansible-in-tmux.sh <session_name> <window_name> <timeout_minutes> <ansible_command>
#
# パラメータ:
#   $1: tmuxセッション名
#   $2: tmuxウィンドウ名
#   $3: タイムアウト時間（分）
#   $4: 実行するAnsibleコマンド
#
# 戻り値:
#   0: 正常完了
#   1: エラー
#   2: タイムアウト
#

set -euo pipefail

# パラメータ取得
TMUX_SESSION="${1:?tmuxセッション名が必要です}"
WINDOW_NAME="${2:?ウィンドウ名が必要です}"
TIMEOUT_MINUTES="${3:?タイムアウト時間が必要です}"
ANSIBLE_CMD="${4:?Ansibleコマンドが必要です}"

# 設定
TIMEOUT_SECONDS=$((TIMEOUT_MINUTES * 60))
ELAPSED=0
INTERVAL=10
LOG_FILE="/tmp/${TMUX_SESSION}_${WINDOW_NAME}.log"

# 関数: tmuxウィンドウの作成
create_tmux_window() {
    if ! tmux has-session -t "${TMUX_SESSION}" 2>/dev/null; then
        tmux new-session -d -s "${TMUX_SESSION}" -n "${WINDOW_NAME}"
    else
        tmux new-window -t "${TMUX_SESSION}" -n "${WINDOW_NAME}"
    fi
}

# 関数: コマンドの実行
execute_command() {
    tmux send-keys -t "${TMUX_SESSION}:${WINDOW_NAME}" "cd ~/infrastructure-as-code/ansible" C-m
    tmux send-keys -t "${TMUX_SESSION}:${WINDOW_NAME}" "${ANSIBLE_CMD}" C-m
}

# 関数: 実行完了のチェック
check_completion() {
    local last_output
    # 最後の50行を取得
    last_output=$(tmux capture-pane -t "${TMUX_SESSION}:${WINDOW_NAME}" -p -S -50 2>/dev/null || echo "")
    
    # PLAY RECAPの存在確認
    if echo "${last_output}" | grep -q "PLAY RECAP"; then
        return 0
    fi
    
    # シェルプロンプトの確認
    if echo "${last_output}" | grep -qE '\[.+@.+\]\$|bash-.*\$'; then
        # ansible-playbookプロセスの確認
        if ! pgrep -f "ansible-playbook" > /dev/null 2>&1; then
            return 0
        fi
    fi
    
    return 1
}

# 関数: エラーチェック
check_errors() {
    local last_output
    last_output=$(tmux capture-pane -t "${TMUX_SESSION}:${WINDOW_NAME}" -p -S -100 2>/dev/null || echo "")
    
    # failed taskのチェック
    if echo "${last_output}" | grep -E "failed=[1-9]" > /dev/null; then
        echo "エラー: Ansibleの実行が失敗しました（failed taskあり）"
        return 1
    fi
    
    # unreachableのチェック
    if echo "${last_output}" | grep -E "unreachable=[1-9]" > /dev/null; then
        echo "エラー: 到達不可能なホストがあります"
        return 1
    fi
    
    return 0
}

# 関数: 進捗表示
show_progress() {
    if [ $((ELAPSED % 30)) -eq 0 ] && [ ${ELAPSED} -gt 0 ]; then
        echo "実行中... (${ELAPSED}秒経過)"
        # 最新の5行を表示
        echo "--- 最新の出力 ---"
        tmux capture-pane -t "${TMUX_SESSION}:${WINDOW_NAME}" -p -S -5 2>/dev/null | sed 's/^/  > /' || true
    fi
}

# メイン処理
main() {
    echo "========================================="
    echo " tmuxセッション内でAnsibleを実行"
    echo "========================================="
    echo "セッション: ${TMUX_SESSION}"
    echo "ウィンドウ: ${WINDOW_NAME}"
    echo "タイムアウト: ${TIMEOUT_MINUTES}分"
    echo "コマンド: ${ANSIBLE_CMD}"
    echo ""
    
    # tmuxウィンドウ作成
    create_tmux_window
    
    # コマンド実行
    execute_command
    
    # 起動待機
    echo "Ansibleプロセスの起動を待機中..."
    sleep 3
    
    echo "プロセスの完了を待機中（最大${TIMEOUT_MINUTES}分）..."
    echo "リアルタイムログ確認: tmux attach -t ${TMUX_SESSION}"
    echo ""
    
    # 監視ループ
    while [ ${ELAPSED} -lt ${TIMEOUT_SECONDS} ]; do
        # ウィンドウの存在確認
        if ! tmux list-windows -t "${TMUX_SESSION}" -F '#{window_name}' 2>/dev/null | grep -q "^${WINDOW_NAME}$"; then
            echo "エラー: tmuxウィンドウが見つかりません"
            exit 1
        fi
        
        # 完了チェック
        if check_completion; then
            echo "Ansible実行が完了しました"
            
            # ログを保存
            echo "=== 実行結果（最後の100行） ==="
            tmux capture-pane -t "${TMUX_SESSION}:${WINDOW_NAME}" -p -S -100 | tail -100
            
            # 全ログを保存
            tmux capture-pane -t "${TMUX_SESSION}:${WINDOW_NAME}" -p -S - > "${LOG_FILE}"
            echo ""
            echo "完全なログは ${LOG_FILE} に保存されました"
            
            # エラーチェック
            if ! check_errors; then
                exit 1
            fi
            
            echo "Ansibleが正常に完了しました"
            exit 0
        fi
        
        # 進捗表示
        show_progress
        
        sleep ${INTERVAL}
        ELAPSED=$((ELAPSED + INTERVAL))
    done
    
    # タイムアウト処理
    echo "タイムアウト: ${TIMEOUT_MINUTES}分を超えました"
    
    # プロセスを終了
    tmux send-keys -t "${TMUX_SESSION}:${WINDOW_NAME}" C-c 2>/dev/null || true
    sleep 2
    tmux kill-window -t "${TMUX_SESSION}:${WINDOW_NAME}" 2>/dev/null || true
    
    echo "Ansibleプロセスを強制終了しました"
    
    # タイムアウト時のログ保存
    echo "=== タイムアウト時のログ（最後の100行） ==="
    tmux capture-pane -t "${TMUX_SESSION}:${WINDOW_NAME}" -p -S -100 2>/dev/null > "${LOG_FILE}" || true
    tail -100 "${LOG_FILE}" 2>/dev/null || true
    
    # タイムアウトフラグファイル作成
    touch "${LOG_FILE}.timeout"
    
    exit 2
}

# 実行
main