#!/bin/bash
# pulumi-config.sh - Pulumi設定管理関数

# 依存関係
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

# Pulumi関連の定数
readonly PULUMI_PASSPHRASE_PARAM="/bootstrap/pulumi/config-passphrase"

# Pulumiバケット名を取得
get_pulumi_bucket() {
    # 引数チェック
    if [ $# -ne 1 ]; then
        log_error "使用方法: get_pulumi_bucket <REGION>"
        return 1
    fi

    local REGION="$1"
    local STACK_NAME=""
    local RESULT=""

    # まず bootstrap-iac-environment を探す
    RESULT=$(aws cloudformation describe-stacks \
        --stack-name "bootstrap-iac-environment" \
        --region "$REGION" \
        --query "Stacks[0].Outputs[?OutputKey=='PulumiStateBucketName'].OutputValue" \
        --output text 2>/dev/null || echo "")

    if [ -n "$RESULT" ]; then
        echo "$RESULT"
        return 0
    fi

    # 見つからない場合は bootstrap-iac-environment-[region] を探す
    RESULT=$(aws cloudformation describe-stacks \
        --stack-name "bootstrap-iac-environment-${REGION}" \
        --region "$REGION" \
        --query "Stacks[0].Outputs[?OutputKey=='PulumiStateBucketName'].OutputValue" \
        --output text 2>/dev/null || echo "")

    echo "$RESULT"
}

# Pulumiパスフレーズを取得
get_pulumi_passphrase() {
    # 引数チェック
    if [ $# -ne 1 ]; then
        log_error "使用方法: get_pulumi_passphrase <REGION>"
        return 1
    fi

    local REGION="$1"

    aws ssm get-parameter \
        --name "$PULUMI_PASSPHRASE_PARAM" \
        --region "$REGION" \
        --with-decryption \
        --query 'Parameter.Value' \
        --output text 2>/dev/null || echo ""
}

# パスフレーズを生成
generate_passphrase() {
    openssl rand -base64 32 | tr -d '\n'
}

# パスフレーズをSSMに保存
save_passphrase_to_ssm() {
    # 引数チェック
    if [ $# -ne 2 ]; then
        log_error "使用方法: save_passphrase_to_ssm <passphrase> <region>"
        return 1
    fi

    local passphrase="$1"
    local region="$2"
    
    log_info "パスフレーズをSSMパラメータストアに保存しています..."
    log_info "  リージョン: $region"
    log_info "  パラメータ名: $PULUMI_PASSPHRASE_PARAM"

    # 既存のパラメータが存在するか確認
    local existing_param
    existing_param=$(aws ssm get-parameter \
        --name "$PULUMI_PASSPHRASE_PARAM" \
        --region "$region" \
        --query 'Parameter.Value' \
        --output text 2>/dev/null || echo "")

    local error_output
    if [ -n "$existing_param" ]; then
        # 既存のパラメータを上書き（タグなし）
        log_info "既存のパラメータを更新しています..."
        error_output=$(aws ssm put-parameter \
            --name "$PULUMI_PASSPHRASE_PARAM" \
            --value "$passphrase" \
            --type "SecureString" \
            --description "Pulumi configuration passphrase for S3 backend encryption" \
            --region "$region" \
            --overwrite 2>&1)
    else
        # 新規作成（タグ付き）
        log_info "新規パラメータを作成しています..."
        error_output=$(aws ssm put-parameter \
            --name "$PULUMI_PASSPHRASE_PARAM" \
            --value "$passphrase" \
            --type "SecureString" \
            --description "Pulumi configuration passphrase for S3 backend encryption" \
            --tags "Key=Name,Value=Pulumi-Config-Passphrase" "Key=Purpose,Value=Pulumi-Backend" \
            --region "$region" 2>&1)
    fi

    if [ $? -eq 0 ]; then
        log_info "✓ パスフレーズがSSMパラメータストアに安全に保存されました"
        return 0
    else
        log_error "パスフレーズの保存に失敗しました"
        log_error "エラー詳細: $error_output"
        return 1
    fi
}

# 対話的にパスフレーズを設定
setup_passphrase_interactive() {
    echo >&2
    log_info "パスフレーズの設定方法を選択してください:" >&2
    echo "  1) 自動生成（推奨）" >&2
    echo "  2) 手動入力" >&2
    echo >&2
    local passphrase_choice
    while true; do
        echo -n "選択 (1/2): " >&2
        read passphrase_choice
        if [[ "$passphrase_choice" =~ ^[12]$ ]]; then
            break
        fi
        log_warn "有効な選択肢を入力してください (1 または 2)" >&2
    done
    
    local passphrase=""
    
    if [ "$passphrase_choice" = "2" ]; then
        # 手動入力
        while true; do
            echo >&2
            echo -n "パスフレーズを入力してください（16文字以上推奨）: " >&2
            read -s passphrase1
            echo >&2
            echo -n "確認のためもう一度入力してください: " >&2
            read -s passphrase2
            echo >&2

            if [ "$passphrase1" != "$passphrase2" ]; then
                log_error "パスフレーズが一致しません。もう一度お試しください。" >&2
            elif [ ${#passphrase1} -lt 16 ]; then
                log_error "パスフレーズは16文字以上にしてください。" >&2
            else
                passphrase="$passphrase1"
                break
            fi
        done
    else
        # 自動生成
        log_info "セキュアなパスフレーズを自動生成しています..." >&2
        passphrase=$(generate_passphrase)
        log_info "✓ パスフレーズが生成されました" >&2
    fi

    # パスフレーズが空の場合はエラー
    if [ -z "$passphrase" ]; then
        log_error "パスフレーズの生成に失敗しました" >&2
        return 1
    fi

    echo "$passphrase"
}

# Pulumi使用方法を表示
show_pulumi_usage() {
    local bucket="$1"
    
    log_section "Pulumi使用方法"
    
    log_warn "S3バックエンドを使用する場合（推奨）:"
    echo -e "${GREEN}# SSMから自動的にパスフレーズを取得${NC}"
    echo -e "${GREEN}export PULUMI_CONFIG_PASSPHRASE=\$(aws ssm get-parameter --name \"$PULUMI_PASSPHRASE_PARAM\" --with-decryption --query 'Parameter.Value' --output text)${NC}"
    echo -e "${GREEN}export PULUMI_STATE_BUCKET_NAME=\"${bucket}\"${NC}"
    echo
    
    log_warn "パスフレーズの確認:"
    echo -e "${GREEN}aws ssm get-parameter --name \"$PULUMI_PASSPHRASE_PARAM\" --with-decryption --query 'Parameter.Value' --output text${NC}"
    echo
    
    log_warn "代替オプション: Pulumi Cloudを使用する場合:"
    echo -e "${GREEN}export PULUMI_ACCESS_TOKEN=\"pul-YOUR_ACCESS_TOKEN\"${NC}"
    echo -e "${GREEN}# all.ymlでbackend_typeを'cloud'に変更するか、実行時に指定:${NC}"
    echo -e "${GREEN}ansible-playbook jenkins_setup_pipeline.yml -e \"env=dev pulumi_backend_type=cloud\"${NC}"
}

# Pulumi設定のメイン処理
setup_pulumi_config() {
    # 引数チェック
    if [ $# -ne 1 ]; then
        log_error "使用方法: setup_pulumi_config <REGION>"
        return 1
    fi

    local REGION="$1"

    log_section "Pulumi設定"
    
    # CloudFormationスタックからPulumi S3バケット名を取得
    log_info "Pulumi用S3バケットを確認しています..."
    local pulumi_bucket=$(get_pulumi_bucket "$REGION")

    if [ -z "$pulumi_bucket" ]; then
        log_warn "Pulumi S3バケットが見つかりません"
        log_warn "以下のCloudFormationスタックが存在することを確認してください:"
        log_warn "  - bootstrap-iac-environment"
        log_warn "  - bootstrap-iac-environment-${REGION}"
        return 1
    fi
    
    log_info "✓ Pulumi S3バケットが見つかりました: $pulumi_bucket"
    
    # SSMパラメータストアからパスフレーズを確認
    log_info "Pulumi設定パスフレーズを確認しています..."
    local existing_passphrase=$(get_pulumi_passphrase "$REGION")
    
    if [ -n "$existing_passphrase" ]; then
        log_info "✓ Pulumi設定パスフレーズが既に設定されています"
        log_info "既存のパスフレーズを使用します"
    else
        log_warn "Pulumi設定パスフレーズがまだ設定されていません"
        log_warn "S3バックエンドのセキュリティのため、パスフレーズの設定が必要です"
        echo
        
        if confirm_action "Pulumi設定パスフレーズを設定しますか？" "y"; then
            local passphrase
            passphrase=$(setup_passphrase_interactive)
            
            if [ -n "$passphrase" ] && save_passphrase_to_ssm "$passphrase" "$REGION"; then
                log_info "✓ パスフレーズの設定が完了しました"
            else
                log_error "パスフレーズの保存に失敗しました"
                log_warn "手動で以下のコマンドを実行してください:"
                echo -e "${GREEN}aws ssm put-parameter --name \"$PULUMI_PASSPHRASE_PARAM\" --value \"YOUR_PASSPHRASE\" --type \"SecureString\"${NC}"
            fi
        fi
    fi
    
    # 使用方法を表示
    show_pulumi_usage "$pulumi_bucket"
    
    return 0
}