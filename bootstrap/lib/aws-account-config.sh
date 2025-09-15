#!/bin/bash
# aws-account-config.sh - AWSアカウントID設定（SSMパラメータストア）

# 依存関係
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

# SSMパラメータストアにAWSアカウントIDを対話的に設定
setup_aws_account_ids() {
    # 引数チェック
    if [ $# -ne 1 ]; then
        log_error "使用方法: setup_aws_account_ids <REGION>"
        return 1
    fi

    local REGION="$1"

    log_section "AWSアカウントID設定（SSMパラメータストア）"
    
    # SSMパラメータ名（他のライブラリと同じ命名規則）
    local PROD_ACCOUNT_PARAM="/bootstrap/aws/prod-account-ids"
    local DEV_ACCOUNT_PARAM="/bootstrap/aws/dev-account-ids"
    
    # 既存のパラメータをチェック
    local existing_prod=$(aws ssm get-parameter --name "$PROD_ACCOUNT_PARAM" --region "$REGION" --query 'Parameter.Value' --output text 2>/dev/null)
    local existing_dev=$(aws ssm get-parameter --name "$DEV_ACCOUNT_PARAM" --region "$REGION" --query 'Parameter.Value' --output text 2>/dev/null)
    
    # 両方とも設定済みの場合はスキップ
    if [ -n "$existing_prod" ] && [ -n "$existing_dev" ]; then
        log_info "✓ AWSアカウントIDは既に設定されています"
        log_info "  本番環境: $existing_prod"
        log_info "  開発環境: $existing_dev"
        log_info "既存の設定を使用します"
        return 0
    fi
    
    log_info "AWSアカウントIDを設定します"
    echo
    echo "環境ごとに許可するAWSアカウントIDを設定することで、"
    echo "誤った環境へのデプロイを防ぐことができます。"
    echo
    
    # 本番環境アカウントIDの入力
    echo -e "${BLUE}本番環境のAWSアカウントIDを設定します${NC}"
    echo "複数のアカウントIDを設定する場合は、カンマ区切りで入力してください"
    echo "例: 987654321098,987654321099"
    
    if [ -n "$existing_prod" ]; then
        echo -e "${YELLOW}現在の値: $existing_prod${NC}"
        echo "変更しない場合はEnterキーを押してください"
    fi
    
    echo -e "${GREEN}本番環境アカウントID:${NC} \c"
    read -r prod_account_ids
    
    if [ -z "$prod_account_ids" ] && [ -n "$existing_prod" ]; then
        prod_account_ids="$existing_prod"
        log_info "既存の値を使用します"
    fi
    
    # 開発環境アカウントIDの入力
    echo -e "\n${BLUE}開発環境のAWSアカウントIDを設定します${NC}"
    echo "複数のアカウントIDを設定する場合は、カンマ区切りで入力してください"
    echo "例: 123456789012,123456789013"
    
    if [ -n "$existing_dev" ]; then
        echo -e "${YELLOW}現在の値: $existing_dev${NC}"
        echo "変更しない場合はEnterキーを押してください"
    fi
    
    echo -e "${GREEN}開発環境アカウントID:${NC} \c"
    read -r dev_account_ids
    
    if [ -z "$dev_account_ids" ] && [ -n "$existing_dev" ]; then
        dev_account_ids="$existing_dev"
        log_info "既存の値を使用します"
    fi
    
    # 少なくとも一つは設定が必要
    if [ -z "$prod_account_ids" ] && [ -z "$dev_account_ids" ]; then
        log_warn "アカウントIDが設定されませんでした"
        log_warn "後で手動で設定してください"
        return 0
    fi
    
    # 入力確認
    echo -e "\n${BLUE}以下の内容で設定します:${NC}"
    [ -n "$prod_account_ids" ] && echo -e "  本番環境: ${GREEN}$prod_account_ids${NC}"
    [ -n "$dev_account_ids" ] && echo -e "  開発環境: ${GREEN}$dev_account_ids${NC}"
    
    echo -e "\n${YELLOW}この内容で設定しますか？ (y/N):${NC} \c"
    read -r confirm
    
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        log_warn "設定をキャンセルしました"
        return 1
    fi
    
    # SSMパラメータに保存
    log_info "SSMパラメータストアに保存中..."
    
    # 本番環境アカウントID（StringList型）
    if [ -n "$prod_account_ids" ]; then
        aws ssm put-parameter \
            --name "$PROD_ACCOUNT_PARAM" \
            --value "$prod_account_ids" \
            --type "StringList" \
            --description "Production AWS Account IDs (comma-separated)" \
            --region "$REGION" \
            --overwrite \
            && log_info "✓ 本番環境アカウントIDを設定しました" \
            || log_error "本番環境アカウントIDの設定に失敗しました"
    fi
    
    # 開発環境アカウントID（StringList型）
    if [ -n "$dev_account_ids" ]; then
        aws ssm put-parameter \
            --name "$DEV_ACCOUNT_PARAM" \
            --value "$dev_account_ids" \
            --type "StringList" \
            --description "Development AWS Account IDs (comma-separated)" \
            --region "$REGION" \
            --overwrite \
            && log_info "✓ 開発環境アカウントIDを設定しました" \
            || log_error "開発環境アカウントIDの設定に失敗しました"
    fi
    
    # 設定確認
    echo
    log_info "設定完了:"
    local stored_prod=$(aws ssm get-parameter --name "$PROD_ACCOUNT_PARAM" --region "$REGION" --query 'Parameter.Value' --output text 2>/dev/null)
    local stored_dev=$(aws ssm get-parameter --name "$DEV_ACCOUNT_PARAM" --region "$REGION" --query 'Parameter.Value' --output text 2>/dev/null)
    
    [ -n "$stored_prod" ] && log_info "✓ 本番環境: $stored_prod"
    [ -n "$stored_dev" ] && log_info "✓ 開発環境: $stored_dev"
    
    echo
    log_info "設定したアカウントIDは、Jenkinsパイプラインで自動的に検証されます"
    
    return 0
}