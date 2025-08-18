#!/bin/bash
# systemd-service.sh - systemdサービス管理

# 依存関係
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

# Public IP更新サービスの設定
setup_public_ip_service() {
    local repo_root="$1"
    local service_name="update-public-ip"
    
    log_section "Public IP自動更新サービスの設定"
    log_info "EC2起動時にPublic IPをSSMパラメータに自動更新するサービスを設定しています..."
    
    # スクリプトファイルの存在確認
    local script_source="$repo_root/bootstrap/scripts/${service_name}.sh"
    local script_dest="/opt/bootstrap/${service_name}.sh"
    
    if ! ensure_file "$script_source"; then
        log_error "${service_name}.shが見つかりません"
        log_warn "  期待される場所: $script_source"
        return 1
    fi
    
    # スクリプトを/opt/bootstrapディレクトリにコピー
    sudo mkdir -p /opt/bootstrap
    sudo cp "$script_source" "$script_dest"
    sudo chmod +x "$script_dest"
    log_info "✓ ${service_name}.shをコピーしました"
    
    # systemdサービスファイルの存在確認とコピー
    local service_source="$repo_root/bootstrap/scripts/${service_name}.service"
    local service_dest="/etc/systemd/system/${service_name}.service"
    
    if ! ensure_file "$service_source"; then
        log_error "${service_name}.serviceが見つかりません"
        log_warn "  期待される場所: $service_source"
        return 1
    fi
    
    sudo cp "$service_source" "$service_dest"
    log_info "✓ ${service_name}.serviceをコピーしました"
    
    # サービスを有効化
    sudo systemctl daemon-reload
    sudo systemctl enable "${service_name}.service"
    
    # 現在のPublic IPを即座に更新
    if sudo systemctl start "${service_name}.service"; then
        log_info "✓ Public IP自動更新サービスが正常に設定されました"
        log_info "  サービス名: ${service_name}.service"
        log_info "  スクリプト: $script_dest"
        log_info "  ログファイル: /var/log/${service_name}.log"
        
        # 現在のPublic IPを表示
        local current_ip=$(aws ssm get-parameter \
            --name /bootstrap/workterminal/public-ip \
            --query 'Parameter.Value' \
            --output text 2>/dev/null || echo "取得失敗")
        log_info "  現在のPublic IP: $current_ip"
    else
        log_warn "⚠ Public IP更新サービスの初回実行に失敗しました"
        log_warn "  手動で確認してください: sudo systemctl status ${service_name}.service"
        return 1
    fi
    
    return 0
}