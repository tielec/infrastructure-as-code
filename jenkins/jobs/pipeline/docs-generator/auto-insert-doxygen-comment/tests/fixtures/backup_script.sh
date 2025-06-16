#!/bin/bash

# システム定数の設定
BACKUP_DIR="/var/backups/app_data"
LOG_FILE="/var/log/backup_script.log"
MAX_BACKUPS=7

# 引数チェック
if [ $# -lt 1 ]; then
  echo "使用法: $0 <ソースディレクトリ> [バックアップ名]"
  exit 1
fi

SOURCE_DIR=$1
BACKUP_NAME=${2:-"backup-$(date +%Y%m%d-%H%M%S)"}

# ログ出力関数
log_message() {
  local message=$1
  local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
  echo "[$timestamp] $message" >> "$LOG_FILE"
  echo "[$timestamp] $message"
}

# ディレクトリ存在確認
check_directories() {
  if [ ! -d "$SOURCE_DIR" ]; then
    log_message "エラー: ソースディレクトリが存在しません: $SOURCE_DIR"
    return 1
  fi

  if [ ! -d "$BACKUP_DIR" ]; then
    log_message "バックアップディレクトリが存在しないため作成します: $BACKUP_DIR"
    mkdir -p "$BACKUP_DIR"
    if [ $? -ne 0 ]; then
      log_message "エラー: バックアップディレクトリを作成できませんでした"
      return 1
    fi
  fi

  return 0
}

# 古いバックアップを削除
cleanup_old_backups() {
  if [ "$MAX_BACKUPS" -gt 0 ]; then
    local backup_count=$(ls -1 "$BACKUP_DIR" | grep -c "\.tar\.gz$")
    
    if [ "$backup_count" -gt "$MAX_BACKUPS" ]; then
      log_message "古いバックアップをクリーンアップします..."
      
      ls -t "$BACKUP_DIR/"*.tar.gz | tail -n +$(($MAX_BACKUPS + 1)) | xargs rm -f
      
      if [ $? -eq 0 ]; then
        log_message "古いバックアップの削除に成功しました"
      else
        log_message "警告: 一部の古いバックアップを削除できませんでした"
      fi
    fi
  fi
}

# バックアップを実行
perform_backup() {
  local backup_file="$BACKUP_DIR/$BACKUP_NAME.tar.gz"
  
  log_message "バックアップを開始: $SOURCE_DIR -> $backup_file"
  
  tar -czf "$backup_file" -C "$(dirname "$SOURCE_DIR")" "$(basename "$SOURCE_DIR")" 2>> "$LOG_FILE"
  
  if [ $? -eq 0 ]; then
    log_message "バックアップ成功: $(du -h "$backup_file" | cut -f1) のデータをバックアップしました"
    return 0
  else
    log_message "エラー: バックアップに失敗しました"
    return 1
  fi
}

# メイン処理
main() {
  log_message "バックアップスクリプトを開始します..."
  
  # ディレクトリチェック
  check_directories
  if [ $? -ne 0 ]; then
    exit 1
  fi
  
  # バックアップ実行
  perform_backup
  if [ $? -ne 0 ]; then
    exit 1
  fi
  
  # 古いバックアップクリーンアップ
  cleanup_old_backups
  
  log_message "バックアップスクリプトが正常に完了しました"
  exit 0
}

# スクリプト実行
main
