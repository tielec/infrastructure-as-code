#!/bin/bash
# script-permissions.sh - スクリプト実行権限管理

# 依存関係
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

# スクリプト実行権限のチェックと修正
check_script_permissions() {
    local dir="$1"
    local pattern="${2:-*.sh}"
    local fixed_count=0
    local script_count=0
    
    if [ ! -d "$dir" ]; then
        echo "0:0"
        return 1
    fi
    
    while IFS= read -r -d '' script; do
        script_count=$((script_count + 1))
        
        if [ ! -x "$script" ]; then
            chmod +x "$script" 2>/dev/null && fixed_count=$((fixed_count + 1))
        fi
    done < <(find "$dir" -type f -name "$pattern" -print0 2>/dev/null)
    
    echo "$script_count:$fixed_count"
}

# 複数ディレクトリのスクリプト権限を修正
fix_all_script_permissions() {
    local repo_root="$1"
    local total_scripts=0
    local total_fixed=0
    local fixed_files=()
    
    log_section "スクリプトファイルの実行権限確認"
    
    # チェックするディレクトリのリスト
    local directories=(
        "$repo_root/scripts"
        "$repo_root/bootstrap"
        "$repo_root/bootstrap/scripts"
        "$repo_root/ansible/scripts"
    )
    
    for dir in "${directories[@]}"; do
        if [ -d "$dir" ]; then
            # ディレクトリ内のスクリプトを個別にチェック
            while IFS= read -r -d '' script; do
                total_scripts=$((total_scripts + 1))
                
                if [ ! -x "$script" ]; then
                    if chmod +x "$script" 2>/dev/null; then
                        total_fixed=$((total_fixed + 1))
                        fixed_files+=("$script")
                    fi
                fi
            done < <(find "$dir" -type f -name "*.sh" -print0 2>/dev/null)
        fi
    done
    
    log_info "✓ スクリプトファイル実行権限の確認が完了しました"
    log_info "  検査したスクリプト数: $total_scripts"
    
    if [ $total_fixed -gt 0 ]; then
        log_warn "  実行権限を付与したファイル数: $total_fixed"
        for file in "${fixed_files[@]}"; do
            log_info "    - $(basename "$file")"
        done
    else
        log_info "  すべてのスクリプトファイルに実行権限が付与されています"
    fi
    
    return 0
}