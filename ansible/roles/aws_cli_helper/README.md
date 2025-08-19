# AWS CLI Helper Role

AWS CLIコマンドの実行を標準化し、エラーハンドリング、リトライ、JSONパースなどの共通機能を提供するAnsibleロールです。

## 機能

- **標準化されたAWS CLI実行**: リージョン設定、タイムアウト、環境変数の統一管理
- **自動リトライ**: スロットリングエラーなどの一時的なエラーに対する自動リトライ
- **エラー解析**: AWS APIエラーの自動分類と詳細情報の抽出
- **JSONパース**: AWS CLI出力の自動パース
- **セキュアログ**: 機密情報のマスキング

## 要件

- Ansible 2.9以上
- AWS CLI（システムにインストール済み）
- boto3（オプション）

## 使用方法

### 基本的な使用

```yaml
- name: Execute simple AWS command
  ansible.builtin.include_role:
    name: aws_cli_helper
    tasks_from: execute
  vars:
    aws_command: "aws s3 ls"
    operation_name: "list_s3_buckets"
```

### 重要な制約事項

**aws_commandは1行で記述する必要があります**

```yaml
# ✅ 正しい例：1行で記述
- name: Execute AWS command correctly
  ansible.builtin.include_role:
    name: aws_cli_helper
    tasks_from: execute
  vars:
    aws_command: "aws imagebuilder list-image-pipeline-images --image-pipeline-arn {{ arn }} --query 'imageSummaryList[0].image' --output text"
    operation_name: "get_ami"

# ❌ 間違った例：複数行で記述（エラーになります）
- name: This will fail
  ansible.builtin.include_role:
    name: aws_cli_helper
    tasks_from: execute
  vars:
    aws_command: |
      aws imagebuilder list-image-pipeline-images 
      --image-pipeline-arn {{ arn }} 
      --query 'imageSummaryList[0].image' 
      --output text
    operation_name: "get_ami"
```

複数行に分割すると、bashが各行を別のコマンドとして解釈してエラーになります。長いコマンドでも必ず1行で記述してください。

### リトライ付き実行

```yaml
- name: Execute with retry
  ansible.builtin.include_role:
    name: aws_cli_helper
    tasks_from: execute_with_retry
  vars:
    aws_command: "aws ec2 describe-instances"
    operation_name: "describe_instances"
    max_retries: 5
    retry_delay: 10
```

### セキュアな値を含むコマンド

```yaml
- name: Execute command with secrets
  ansible.builtin.include_role:
    name: aws_cli_helper
    tasks_from: execute
  vars:
    aws_command: "aws ssm put-parameter --name /app/password --value '{{ secret_value }}'"
    operation_name: "set_password"
    no_log_output: true  # 出力をマスク
```

## 変数

### 必須変数

| 変数名 | 説明 | 例 |
|--------|------|-----|
| `aws_command` | 実行するAWS CLIコマンド | `aws s3 ls` |
| `operation_name` | 操作の識別名（ログ用） | `list_buckets` |

### オプション変数

| 変数名 | デフォルト値 | 説明 |
|--------|--------------|------|
| `no_log_output` | `false` | 出力をマスクするか |
| `parse_output` | `true` | JSON出力をパースするか |
| `timeout` | `30` | コマンドのタイムアウト（秒） |
| `max_retries` | `3` | 最大リトライ回数 |
| `retry_delay` | `5` | リトライ間隔（秒） |
| `use_backoff` | `true` | 指数バックオフを使用するか |

### 戻り値

| 変数名 | 説明 |
|--------|------|
| `aws_cli_success` | コマンドが成功したか |
| `aws_cli_data` | パース済みのJSONデータ |
| `aws_cli_error_type` | エラーの種類（失敗時） |
| `aws_cli_error_message` | エラーメッセージ（失敗時） |
| `aws_cli_retry_attempts` | リトライ回数（リトライ使用時） |

## リトライ可能なエラー

以下のエラーは自動的にリトライされます：

- `ThrottlingException`
- `RequestLimitExceeded`
- `ServiceUnavailable`
- `RequestTimeout`
- `TooManyRequestsException`

## 他のロールからの使用

### meta/main.yml で依存関係を定義

```yaml
dependencies:
  - role: aws_cli_helper
```

### タスクから使用

```yaml
- name: Get SSM parameter using AWS CLI helper
  ansible.builtin.include_role:
    name: aws_cli_helper
    tasks_from: execute_with_retry
  vars:
    aws_command: "aws ssm get-parameter --name {{ param_name }} --with-decryption"
    operation_name: "get_ssm_parameter"
    no_log_output: true
```
