# スクリプト開発ガイド

スクリプトの開発者向けガイドです。

## 📋 目次

- [開発環境](#開発環境)
- [コーディング規約](#コーディング規約)
- [スクリプト作成ガイドライン](#スクリプト作成ガイドライン)
- [ディレクトリ構造と責任分担](#ディレクトリ構造と責任分担)
- [テスト](#テスト)
- [ベストプラクティス](#ベストプラクティス)
- [トラブルシューティング](#トラブルシューティング)

## 開発環境

### 必要なツール

```bash
# Bash (4.0以上推奨)
bash --version

# ShellCheck (静的解析ツール)
shellcheck --version

# AWS CLI
aws --version

# jq (JSON処理)
jq --version

# yq (YAML処理)
yq --version
```

### 開発環境のセットアップ

```bash
# macOS
brew install shellcheck jq yq awscli

# Ubuntu/Debian
apt-get update
apt-get install shellcheck jq
# yqは別途インストール
wget https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64 -O /usr/bin/yq
chmod +x /usr/bin/yq

# AWS CLI
pip install awscli --upgrade
```

### IDE設定

推奨エディタ/IDE:
- **VS Code**: Bash IDE、ShellCheck拡張機能
- **IntelliJ IDEA**: Shell Script プラグイン
- **Vim**: ALE (Asynchronous Lint Engine) with ShellCheck

```json
// VS Code settings.json
{
  "shellcheck.enable": true,
  "shellcheck.run": "onSave",
  "shellcheck.exclude": [],
  "shellcheck.customArgs": [],
  "files.eol": "\n",
  "files.trimTrailingWhitespace": true
}
```

## コーディング規約

### ファイル命名規則

```bash
# 一般的なスクリプト
{action}-{target}.sh
例: setup-aws-credentials.sh, test-s3-access.sh

# 環境設定スクリプト
{system}-env.sh
例: aws-env.sh, jenkins-env.sh

# アプリケーション固有
{application}-{action}-{target}.sh
例: jenkins-install-plugins.sh, controller-mount-efs.sh
```

### Shebangとヘッダー

```bash
#!/bin/bash
#
# スクリプト名: script-name.sh
# 
# 説明:
#   このスクリプトの目的と機能の説明
#
# 使用方法:
#   ./script-name.sh [options] <arguments>
#
# オプション:
#   -h, --help      ヘルプを表示
#   -v, --verbose   詳細出力
#   -d, --debug     デバッグモード
#
# 引数:
#   argument1       説明（必須/オプション）
#   argument2       説明（デフォルト: value）
#
# 環境変数:
#   VAR_NAME        説明（必須）
#   OPTIONAL_VAR    説明（オプション、デフォルト: value）
#
# 終了コード:
#   0   成功
#   1   一般的なエラー
#   2   引数エラー
#   3   環境エラー
#
# 例:
#   ./script-name.sh --verbose argument1
#   VAR_NAME=value ./script-name.sh argument1 argument2
#
```

### 基本設定

```bash
# エラーハンドリングの設定（必須）
set -euo pipefail

# -e: コマンドがエラー（0以外の終了コード）で即座に終了
# -u: 未定義変数の参照でエラー
# -o pipefail: パイプライン内のエラーを検出

# デバッグモード（オプション）
[[ "${DEBUG:-false}" == "true" ]] && set -x

# IFS設定（文字列分割の制御）
IFS=$'\n\t'
```

### 変数定義

```bash
# グローバル定数（大文字）
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_NAME="$(basename "${BASH_SOURCE[0]}")"
readonly TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

# 設定可能な変数（大文字、デフォルト値付き）
AWS_REGION="${AWS_REGION:-ap-northeast-1}"
LOG_LEVEL="${LOG_LEVEL:-INFO}"
TIMEOUT="${TIMEOUT:-300}"

# 必須環境変数のチェック
: "${REQUIRED_VAR:?Error: REQUIRED_VAR is not set}"

# ローカル変数（小文字、関数内で使用）
local file_path="/tmp/example.txt"
local counter=0
```

### 関数定義

```bash
# 関数名は動詞_名詞の形式
# 戻り値: 0=成功、1以上=エラー

#######################################
# 関数の説明
# Globals:
#   AWS_REGION - 使用するAWSリージョン
# Arguments:
#   $1 - 引数1の説明
#   $2 - 引数2の説明（オプション）
# Returns:
#   0 - 成功
#   1 - エラー
# Outputs:
#   処理結果を標準出力に出力
#######################################
function process_data() {
    local input_file="${1:?Error: input file is required}"
    local output_file="${2:-/tmp/output.txt}"
    
    # 引数チェック
    if [[ ! -f "$input_file" ]]; then
        log_error "Input file not found: $input_file"
        return 1
    fi
    
    # メイン処理
    log_info "Processing $input_file"
    # 処理内容...
    
    return 0
}
```

### ログ出力

```bash
# ログレベル関数
function log_debug() {
    [[ "$LOG_LEVEL" == "DEBUG" ]] && echo "[DEBUG] $(date '+%Y-%m-%d %H:%M:%S') - $*" >&2
}

function log_info() {
    echo "[INFO] $(date '+%Y-%m-%d %H:%M:%S') - $*" >&2
}

function log_warn() {
    echo "[WARN] $(date '+%Y-%m-%d %H:%M:%S') - $*" >&2
}

function log_error() {
    echo "[ERROR] $(date '+%Y-%m-%d %H:%M:%S') - $*" >&2
}

# 使用例
log_info "Starting process..."
log_debug "Variable value: $var"
log_error "Failed to connect to database"
```

### エラーハンドリング

```bash
# エラートラップ
trap 'error_handler $? $LINENO' ERR

function error_handler() {
    local exit_code=$1
    local line_number=$2
    log_error "Error occurred in $SCRIPT_NAME at line $line_number with exit code $exit_code"
    cleanup
    exit "$exit_code"
}

# クリーンアップ関数
function cleanup() {
    log_info "Cleaning up..."
    # 一時ファイルの削除
    [[ -f "$temp_file" ]] && rm -f "$temp_file"
    # プロセスの停止
    [[ -n "${pid:-}" ]] && kill "$pid" 2>/dev/null || true
}

# 正常終了時のクリーンアップ
trap cleanup EXIT
```

## スクリプト作成ガイドライン

### 1. 冪等性の確保

```bash
# ファイル作成前にチェック
if [[ ! -f "$config_file" ]]; then
    create_config_file "$config_file"
else
    log_info "Config file already exists: $config_file"
fi

# ディレクトリ作成（-pオプションで冪等性確保）
mkdir -p "$target_dir"

# サービス起動（既に起動している場合も成功とする）
systemctl start jenkins || systemctl is-active jenkins
```

### 2. 入力検証

```bash
# 引数の数をチェック
if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <argument>" >&2
    exit 2
fi

# ファイルの存在チェック
if [[ ! -f "$input_file" ]]; then
    log_error "File not found: $input_file"
    exit 1
fi

# 数値チェック
if ! [[ "$port" =~ ^[0-9]+$ ]]; then
    log_error "Port must be a number: $port"
    exit 2
fi

# 範囲チェック
if (( port < 1 || port > 65535 )); then
    log_error "Port out of range: $port"
    exit 2
fi
```

### 3. セキュリティ考慮事項

```bash
# 機密情報のマスキング
function mask_sensitive_data() {
    local data="$1"
    echo "${data:0:4}****${data: -4}"
}

# 一時ファイルの安全な作成
temp_file="$(mktemp)"
chmod 600 "$temp_file"
trap 'rm -f "$temp_file"' EXIT

# コマンドインジェクション対策
# NG: eval "command $user_input"
# OK: 
safe_input="$(printf '%q' "$user_input")"
command "$safe_input"

# パスワードの安全な読み取り
read -s -p "Password: " password
echo
```

## ディレクトリ構造と責任分担

### aws/ - AWS操作スクリプト

```bash
aws/
├── aws-env.sh              # AWS環境変数設定
├── setup-aws-credentials.sh # 認証情報設定
├── get-pulumi-bucket.sh    # Pulumiバケット情報取得
├── test-s3-access.sh       # S3アクセステスト
└── aws-stop-instances.sh   # EC2インスタンス管理
```

**開発規約:**
- AWS CLIコマンドはエラーハンドリングを含める
- リージョンは環境変数で設定可能にする
- 出力はJSONフォーマットで統一
- jqを使用してJSON処理

### jenkins/ - Jenkins関連スクリプト

```bash
jenkins/
├── casc/                   # Configuration as Code
│   └── jenkins.yaml.template
├── groovy/                 # Groovyスクリプト
│   ├── basic-settings.groovy
│   └── install-plugins.groovy
├── jobs/                   # ジョブ定義
│   └── seed-job.xml
└── shell/                  # シェルスクリプト
    ├── controller-*.sh     # コントローラー関連
    ├── agent-*.sh         # エージェント関連
    └── application-*.sh   # アプリケーション設定
```

**開発規約:**
- Jenkinsスクリプトは`jenkins-cli.jar`または REST APIを使用
- Groovyスクリプトは Script Console での実行を想定
- 設定変更後は必ず検証スクリプトを実行

### workterminal/ - 作業端末用スクリプト

```bash
workterminal/
└── update-repo-branch.sh   # リポジトリ管理
```

**開発規約:**
- 開発者の作業効率化を目的とする
- Git操作は安全性を重視（force pushの制限など）

## テスト

### ShellCheckによる静的解析

```bash
# 単一ファイルのチェック
shellcheck scripts/aws/aws-env.sh

# ディレクトリ全体のチェック
find scripts -name "*.sh" -exec shellcheck {} \;

# 特定の警告を無視
# shellcheck disable=SC2086
command $args  # 意図的にクォートなし
```

### 単体テスト

```bash
#!/bin/bash
# test_aws_env.sh

source scripts/aws/aws-env.sh

# テスト関数
function test_aws_region_setting() {
    AWS_REGION="us-west-2"
    source scripts/aws/aws-env.sh
    
    if [[ "$AWS_REGION" != "us-west-2" ]]; then
        echo "FAIL: AWS_REGION not set correctly"
        return 1
    fi
    echo "PASS: AWS_REGION setting"
    return 0
}

# テスト実行
test_aws_region_setting
```

### 統合テスト

```bash
#!/bin/bash
# integration_test.sh

# 環境セットアップ
./scripts/aws/setup-aws-credentials.sh

# S3アクセステスト
./scripts/aws/test-s3-access.sh

# 結果確認
if [[ $? -eq 0 ]]; then
    echo "Integration test passed"
else
    echo "Integration test failed"
    exit 1
fi
```

## ベストプラクティス

### 1. パフォーマンス最適化

```bash
# 不要なサブシェルを避ける
# NG: 
result=$(cat file.txt | grep pattern | wc -l)
# OK:
result=$(grep -c pattern file.txt)

# ループ内でのコマンド実行を最小化
# NG:
for file in *.txt; do
    cat "$file" >> output.txt
done
# OK:
cat *.txt > output.txt

# 並列処理の活用
export -f process_file
find . -name "*.log" | parallel process_file
```

### 2. 可読性の向上

```bash
# 意味のある変数名
# NG: 
d="/var/lib/jenkins"
# OK:
jenkins_home_dir="/var/lib/jenkins"

# 複雑な条件の関数化
function is_jenkins_running() {
    systemctl is-active jenkins >/dev/null 2>&1
}

if is_jenkins_running; then
    log_info "Jenkins is running"
fi

# 長いコマンドの分割
aws ec2 describe-instances \
    --filters "Name=tag:Environment,Values=dev" \
    --query 'Reservations[*].Instances[*].[InstanceId,State.Name]' \
    --output table
```

### 3. デバッグ支援

```bash
# デバッグ関数
function debug_vars() {
    [[ "${DEBUG:-false}" != "true" ]] && return
    
    echo "=== Debug Information ===" >&2
    echo "Script: $SCRIPT_NAME" >&2
    echo "PID: $$" >&2
    echo "PWD: $PWD" >&2
    echo "Arguments: $*" >&2
    echo "Environment:" >&2
    env | grep -E '^(AWS_|JENKINS_)' | sort >&2
    echo "======================" >&2
}

# 実行時間の計測
function measure_time() {
    local start_time=$(date +%s)
    "$@"
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    log_info "Execution time: ${duration}s"
}

# 使用例
measure_time long_running_command
```

## トラブルシューティング

### よくあるエラーと対処法

#### 1. Syntax Error

```bash
# エラー: syntax error near unexpected token
# 原因: 構文エラー
# 対処:
bash -n script.sh  # 構文チェック
shellcheck script.sh  # 詳細な解析
```

#### 2. Command Not Found

```bash
# エラー: command not found
# 原因: コマンドがPATHにない
# 対処:
which command_name  # コマンドの場所確認
export PATH="$PATH:/usr/local/bin"  # PATH追加
```

#### 3. Permission Denied

```bash
# エラー: permission denied
# 原因: 実行権限がない
# 対処:
chmod +x script.sh  # 実行権限付与
ls -l script.sh  # 権限確認
```

#### 4. Variable Unbound

```bash
# エラー: unbound variable
# 原因: set -u で未定義変数を参照
# 対処:
# デフォルト値を設定
VAR="${VAR:-default}"
# または必須チェック
: "${VAR:?Error: VAR is required}"
```

### デバッグテクニック

```bash
# 1. トレースモード
set -x  # 実行するコマンドを表示
# または
bash -x script.sh

# 2. エラー時のスタックトレース
set -E
trap 'echo "Error at line $LINENO"' ERR

# 3. 変数の内容確認
declare -p variable_name

# 4. ステップ実行
trap 'read -p "Next? "' DEBUG

# 5. ログファイルへの出力
exec 1> >(tee -a output.log)
exec 2> >(tee -a error.log >&2)
```

## コントリビューション

### コミット規約

```
[scripts] action: 詳細な説明

action: add|update|fix|remove|refactor

例:
[scripts] add: Pulumiステートバケット取得スクリプトを追加
[scripts] fix: AWS認証エラーの処理を修正
[scripts] update: Jenkins設定スクリプトのタイムアウト値を変更
```

### プルリクエスト

1. featureブランチを作成
2. ShellCheckでエラーがないことを確認
3. テストスクリプトを追加・更新
4. README.mdのドキュメントを更新
5. PRを作成

### レビューチェックリスト

- [ ] ShellCheckエラーなし
- [ ] ヘッダーコメント記載
- [ ] エラーハンドリング実装
- [ ] 冪等性の確保
- [ ] セキュリティ考慮
- [ ] ログ出力適切
- [ ] テスト追加/更新
- [ ] ドキュメント更新

## 関連ドキュメント

- [scripts/README.md](README.md) - 使用方法
- [メインCLAUDE.md](../CLAUDE.md) - 開発ガイドライン
- [Jenkins CONTRIBUTION.md](../jenkins/CONTRIBUTION.md) - Jenkins開発規約
- [Ansible CONTRIBUTION.md](../ansible/CONTRIBUTION.md) - Ansible開発規約