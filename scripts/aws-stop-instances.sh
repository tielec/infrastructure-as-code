#!/bin/bash

# エラー時は即座に終了
set -e

# INSTANCE_NAMEが設定されているか確認
if [ -z "$INSTANCE_NAME" ]; then
  echo "エラー: INSTANCE_NAME環境変数が設定されていません"
  exit 1
fi

# jqがインストールされているか確認
if ! command -v jq &> /dev/null; then
  echo "エラー: jqコマンドが見つかりません"
  exit 1
fi

# パターンを配列に分割（カンマ区切り）
IFS="," read -ra PATTERNS <<< "$INSTANCE_NAME"

echo "=== 検索パターン ==="
for i in "${!PATTERNS[@]}"; do
  # 前後の空白を削除
  PATTERNS[$i]=$(echo "${PATTERNS[$i]}" | xargs)
  echo "$((i+1)). '${PATTERNS[$i]}'"
done
echo ""

# すべての実行中のインスタンスを取得
ALL_INSTANCES=$(aws ec2 describe-instances \
  --filters "Name=instance-state-name,Values=running" \
  --query "Reservations[*].Instances[*].{ID:InstanceId,Name:Tags[?Key=='Name'].Value|[0],State:State.Name}" \
  --output json)

# マッチしたインスタンスを格納する配列
declare -A MATCHED_INSTANCES

# 各パターンでインスタンスを検索
for PATTERN in "${PATTERNS[@]}"; do
  if [[ "$PATTERN" == *"*"* ]]; then
    # ワイルドカードが含まれている場合
    REGEX_PATTERN=$(echo "$PATTERN" | sed 's/\*/\.\*/g')
    MATCHES=$(echo "$ALL_INSTANCES" | jq -r ".[][] | select(.Name != null and (.Name | test(\"^${REGEX_PATTERN}$\"))) | \"\(.ID) \(.Name)\"")
  else
    # 完全一致
    MATCHES=$(echo "$ALL_INSTANCES" | jq -r ".[][] | select(.Name == \"${PATTERN}\") | \"\(.ID) \(.Name)\"")
  fi
  
  # マッチしたインスタンスを配列に追加
  if [ -n "$MATCHES" ]; then
    while IFS= read -r line; do
      INSTANCE_ID=$(echo "$line" | awk '{print $1}')
      INSTANCE_NAME=$(echo "$line" | awk '{$1=""; print $0}' | xargs)
      MATCHED_INSTANCES[$INSTANCE_ID]="$INSTANCE_NAME"
    done <<< "$MATCHES"
  fi
done

# マッチしたインスタンスがあるかチェック
if [ ${#MATCHED_INSTANCES[@]} -eq 0 ]; then
  echo "エラー: 指定されたパターンにマッチする実行中のインスタンスが見つかりません"
  exit 1
fi

# 停止対象のインスタンス一覧を表示
echo "=== 停止対象のインスタンス ==="
for INSTANCE_ID in "${!MATCHED_INSTANCES[@]}"; do
  echo "  $INSTANCE_ID (${MATCHED_INSTANCES[$INSTANCE_ID]})"
done
echo "合計: ${#MATCHED_INSTANCES[@]} 個"
echo ""

# インスタンスIDのリストを作成（配列として保持）
INSTANCE_ID_ARRAY=( "${!MATCHED_INSTANCES[@]}" )

# 10秒後にすべてのインスタンスを停止
echo "10秒後にインスタンスを停止します..."

# ログファイル名を決定
LOG_FILE="/tmp/ec2-stop-$$.log"

# バックグラウンドで遅延実行
{
  # エラーハンドリングを無効化（バックグラウンドプロセス内）
  set +e
  
  sleep 10
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] 停止処理を開始します" >> "$LOG_FILE"
  
  # デバッグ情報を追加
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] 停止対象インスタンス数: ${#INSTANCE_ID_ARRAY[@]}" >> "$LOG_FILE"
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] インスタンスID: ${INSTANCE_ID_ARRAY[*]}" >> "$LOG_FILE"
  
  # aws ec2 stop-instancesコマンドを実行
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] aws ec2 stop-instances コマンドを実行中..." >> "$LOG_FILE"
  
  # コマンドの実行と結果の取得
  STOP_OUTPUT=$(aws ec2 stop-instances --instance-ids ${INSTANCE_ID_ARRAY[@]} 2>&1)
  STOP_RESULT=$?
  
  if [ $STOP_RESULT -eq 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 停止コマンドが正常に実行されました" >> "$LOG_FILE"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] コマンド出力:" >> "$LOG_FILE"
    echo "$STOP_OUTPUT" >> "$LOG_FILE"
    
    # 停止状態の確認（バックグラウンドで継続）
    for i in {1..6}; do
      sleep 10
      echo "" >> "$LOG_FILE"
      echo "[$(date '+%Y-%m-%d %H:%M:%S')] 状態確認 ($i/6):" >> "$LOG_FILE"
      
      # 各インスタンスの状態を確認
      for instance_id in "${INSTANCE_ID_ARRAY[@]}"; do
        STATE=$(aws ec2 describe-instances \
          --instance-ids "$instance_id" \
          --query 'Reservations[0].Instances[0].State.Name' \
          --output text 2>&1)
        if [ $? -eq 0 ]; then
          echo "  $instance_id: $STATE" >> "$LOG_FILE"
        else
          echo "  $instance_id: 状態取得エラー - $STATE" >> "$LOG_FILE"
        fi
      done
      
      # すべてのインスタンスが停止したかチェック
      ALL_STOPPED=true
      for instance_id in "${INSTANCE_ID_ARRAY[@]}"; do
        STATE=$(aws ec2 describe-instances \
          --instance-ids "$instance_id" \
          --query 'Reservations[0].Instances[0].State.Name' \
          --output text 2>/dev/null)
        if [ "$STATE" != "stopped" ] && [ "$STATE" != "stopping" ]; then
          ALL_STOPPED=false
        fi
      done
      
      if [ "$ALL_STOPPED" = true ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] すべてのインスタンスが停止しました" >> "$LOG_FILE"
        break
      fi
    done
  else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] エラー: 停止コマンドの実行に失敗しました (終了コード: $STOP_RESULT)" >> "$LOG_FILE"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] エラー出力:" >> "$LOG_FILE"
    echo "$STOP_OUTPUT" >> "$LOG_FILE"
  fi
  
  # ログファイルの最終出力
  echo "" >> "$LOG_FILE"
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] 処理完了" >> "$LOG_FILE"
} &

# バックグラウンドプロセスのPIDを記録
BG_PID=$!
echo "バックグラウンドプロセスID: $BG_PID"
echo "ログファイル: $LOG_FILE"
echo ""
echo "Jenkinsジョブは正常に完了します。"
echo "インスタンスは10秒後に停止を開始します。"
echo ""
echo "停止処理の状況は以下のコマンドで確認できます:"
echo "  tail -f $LOG_FILE"

# Jenkinsジョブとしては正常終了
exit 0
