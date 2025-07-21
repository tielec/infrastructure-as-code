# SSM Parameter Store Ansible Role

AWS Systems Manager Parameter Storeと連携して、セキュアな設定管理を実現するAnsibleロールです。

## 概要

このロールは、AWS SSM Parameter Storeからパラメータを取得し、Ansibleの変数や環境変数として利用できるようにします。セキュアな値の自動検出とマスキング、キャッシュ機能、バッチ処理など、本番環境での利用を想定した機能を提供します。

## 主な機能

- **パラメータの取得**: 単一、複数、パス指定での一括取得
- **セキュリティ**: 自動的なセキュアパラメータの検出とマスキング
- **キャッシュ**: プレイブック実行中のインメモリキャッシュ
- **環境変数**: 取得したパラメータの環境変数へのエクスポート
- **バリデーション**: 必須パラメータの確認と型チェック
- **エラーハンドリング**: リトライとフォールバック機能

## 要件

- Ansible 2.9以上
- Python 3.6以上
- boto3 ライブラリ
- AWS認証情報の設定（IAMロール、環境変数、またはAWS CLIプロファイル）

### 必要なIAM権限

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ssm:GetParameter",
        "ssm:GetParameters",
        "ssm:GetParametersByPath",
        "ssm:DescribeParameters",
        "ssm:PutParameter",
        "ssm:DeleteParameter"
      ],
      "Resource": "arn:aws:ssm:*:*:parameter/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "kms:Decrypt",
        "kms:Encrypt"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "kms:ViaService": [
            "ssm.*.amazonaws.com"
          ]
        }
      }
    }
  ]
}
```

## ロール変数

### デフォルト設定（defaults/main.yml）

| 変数名 | デフォルト値 | 説明 |
|--------|--------------|------|
| `ssm_parameter_store_region` | `ap-northeast-1` | AWS リージョン |
| `ssm_parameter_store_cache.enabled` | `true` | キャッシュの有効/無効 |
| `ssm_parameter_store_cache.ttl` | `300` | キャッシュの有効期限（秒） |
| `ssm_parameter_store_cache.scope` | `playbook` | キャッシュのスコープ |
| `ssm_parameter_store_auto_secure` | `true` | セキュアパラメータの自動検出 |
| `ssm_parameter_store_mask_value` | `***SECURE***` | マスク表示文字列 |
| `ssm_parameter_store_mask_partial` | `true` | 部分マスク（先頭3文字表示） |
| `ssm_parameter_store_batch_size` | `10` | バッチ処理のサイズ |
| `ssm_parameter_store_fail_on_missing` | `true` | パラメータ未検出時の挙動 |
| `ssm_parameter_store_retry_count` | `3` | リトライ回数 |
| `ssm_parameter_store_retry_delay` | `5` | リトライ間隔（秒） |

### セキュアキーワード

以下のキーワードを含むパラメータは自動的にセキュアとして扱われます：

- password, secret, key, token, credential, private
- cert, certificate, auth, api_key, api_secret
- access_key, secret_key, private_key, oauth, jwt

## 使用方法

### 1. 単一パラメータの取得

```yaml
- name: Get database password
  ansible.builtin.include_role:
    name: ssm_parameter_store
    tasks_from: get_parameter
  vars:
    parameter_name: "/myapp/dev/database/password"
    decrypt: true  # SecureStringの復号化（デフォルト: true）
    store_as: "db_password"  # 変数名として保存（オプション）
```

取得後の利用：
```yaml
- name: Use retrieved parameter
  ansible.builtin.debug:
    msg: "Database password is stored in variable: {{ db_password }}"
```

### 2. デフォルト値付きパラメータ取得

```yaml
- name: Get parameter with fallback
  ansible.builtin.include_role:
    name: ssm_parameter_store
    tasks_from: get_parameter
  vars:
    parameter_name: "/myapp/{{ environment }}/api/timeout"
    default_value: "30"  # パラメータが存在しない場合のデフォルト値
    ssm_parameter_store_fail_on_missing: false
```

### 3. 複数パラメータの一括取得

```yaml
- name: Get multiple parameters
  ansible.builtin.include_role:
    name: ssm_parameter_store
    tasks_from: get_parameters
  vars:
    parameter_names:
      - "/myapp/{{ environment }}/api/key"
      - "/myapp/{{ environment }}/database/host"
      - "/myapp/{{ environment }}/cache/endpoint"
```

### 4. パスベースの一括取得

```yaml
- name: Get all parameters for environment
  ansible.builtin.include_role:
    name: ssm_parameter_store
    tasks_from: get_parameters_by_path
  vars:
    parameter_path: "/myapp/{{ environment }}/"
    recursive: true  # サブパスも含める
```

### 5. 環境変数へのエクスポート

#### 自動マッピング

```yaml
- name: Export with auto-generated names
  ansible.builtin.include_role:
    name: ssm_parameter_store
    tasks_from: export_to_env
  vars:
    ssm_parameter_store_env_prefix: "MYAPP_"
    ssm_parameter_store_env_uppercase: true
```

結果例：
- `/myapp/dev/api-key` → `MYAPP_API_KEY`
- `/myapp/dev/database.host` → `MYAPP_DATABASE_HOST`

#### カスタムマッピング

```yaml
- name: Export with custom mappings
  ansible.builtin.include_role:
    name: ssm_parameter_store
    tasks_from: export_to_env
  vars:
    ssm_env_mappings:
      - ssm_path: "/myapp/{{ environment }}/database/host"
        env_name: "DB_HOST"
        required: true
      - ssm_path: "/myapp/{{ environment }}/database/password"
        env_name: "DB_PASSWORD"
        secure: true
        required: true
      - ssm_path: "/myapp/{{ environment }}/api/key"
        env_name: "API_KEY"
        secure: true
      - ssm_path: "/myapp/{{ environment }}/features"
        env_name: "FEATURE_FLAGS"
        parse_json: true
        transform: "base64"  # Base64エンコード
```

### 6. パラメータの設定/更新

```yaml
- name: Set application version
  ansible.builtin.include_role:
    name: ssm_parameter_store
    tasks_from: set_parameter
  vars:
    parameter_name: "/myapp/{{ environment }}/version"
    parameter_value: "{{ git_commit_sha }}"
    parameter_type: "String"  # String, StringList, SecureString
    description: "Deployed version"
    overwrite: true
    tags:
      Environment: "{{ environment }}"
      ManagedBy: "Ansible"
      DeployedAt: "{{ ansible_date_time.iso8601 }}"
```

### 7. セキュアパラメータの設定

```yaml
- name: Set secure parameter
  ansible.builtin.include_role:
    name: ssm_parameter_store
    tasks_from: set_parameter
  vars:
    parameter_name: "/myapp/{{ environment }}/database/password"
    parameter_value: "{{ lookup('password', '/dev/null length=32 chars=ascii_letters,digits') }}"
    parameter_type: "SecureString"
    kms_key_id: "alias/myapp-{{ environment }}"  # カスタムKMSキー
```

### 8. パラメータの削除

```yaml
- name: Delete parameter
  ansible.builtin.include_role:
    name: ssm_parameter_store
    tasks_from: delete_parameter
  vars:
    parameter_name: "/myapp/{{ environment }}/temp/value"
```

### 9. パラメータの一覧取得

```yaml
- name: List all parameters for environment
  ansible.builtin.include_role:
    name: ssm_parameter_store
    tasks_from: list_parameters
  vars:
    name_prefix: "/myapp/{{ environment }}/"
    parameter_type: "SecureString"  # フィルタリング（オプション）
    max_results: 100

- name: Display parameter list
  ansible.builtin.debug:
    var: ssm_parameter_info
```

### 10. パラメータのバリデーション

```yaml
- name: Validate required parameters
  ansible.builtin.include_role:
    name: ssm_parameter_store
    tasks_from: validate_parameters
  vars:
    required_parameters:
      - "/myapp/{{ environment }}/database/host"
      - "/myapp/{{ environment }}/database/password"
      - "/myapp/{{ environment }}/api/key"
    parameter_schemas:
      - name: "/myapp/{{ environment }}/database/port"
        pattern: "^[0-9]+$"
        type: "number"
      - name: "/myapp/{{ environment }}/api/config"
        type: "json"
    parameter_constraints:
      - name: "/myapp/{{ environment }}/api/timeout"
        type: "number"
        min: 1
        max: 300
      - name: "/myapp/{{ environment }}/api/key"
        type: "string"
        min_length: 32
        max_length: 64
```

## 実践的な使用例

### Lambda関数の設定管理

```yaml
---
- name: Configure Lambda function with SSM parameters
  hosts: localhost
  vars:
    environment: "{{ env | default('dev') }}"
    function_name: "myapp-api-{{ environment }}"
    
  tasks:
    # すべての設定を取得
    - name: Get Lambda configuration from SSM
      ansible.builtin.include_role:
        name: ssm_parameter_store
        tasks_from: get_parameters_by_path
      vars:
        parameter_path: "/lambda/{{ function_name }}/"
        recursive: true

    # 環境変数として設定
    - name: Export as Lambda environment variables
      ansible.builtin.include_role:
        name: ssm_parameter_store
        tasks_from: export_to_env
      vars:
        ssm_env_mappings:
          - ssm_path: "/lambda/{{ function_name }}/database/connection_string"
            env_name: "DATABASE_URL"
            secure: true
          - ssm_path: "/lambda/{{ function_name }}/api/key"
            env_name: "API_KEY"
            secure: true
          - ssm_path: "/lambda/{{ function_name }}/features/config"
            env_name: "FEATURE_CONFIG"
            parse_json: true

    # Pulumiで使用
    - name: Configure Pulumi with SSM values
      ansible.builtin.include_role:
        name: pulumi_helper
        tasks_from: set_config
      vars:
        config_key: "lambda:environment"
        config_value: "{{ ssm_exported_vars | to_json }}"
        config_secret: true
```

### CI/CDパイプラインでの利用

```yaml
---
- name: Deploy application with SSM parameters
  hosts: localhost
  vars:
    app_name: "myapp"
    environment: "{{ env }}"
    
  tasks:
    # 必須パラメータの確認
    - name: Validate deployment parameters
      ansible.builtin.include_role:
        name: ssm_parameter_store
        tasks_from: validate_parameters
      vars:
        required_parameters:
          - "/{{ app_name }}/{{ environment }}/deployment/target_group_arn"
          - "/{{ app_name }}/{{ environment }}/deployment/ecr_repository"
          - "/{{ app_name }}/{{ environment }}/deployment/task_definition"

    # デプロイメント設定の取得
    - name: Get deployment configuration
      ansible.builtin.include_role:
        name: ssm_parameter_store
        tasks_from: get_parameters_by_path
      vars:
        parameter_path: "/{{ app_name }}/{{ environment }}/deployment/"

    # バージョン情報の更新
    - name: Update deployment version
      ansible.builtin.include_role:
        name: ssm_parameter_store
        tasks_from: set_parameter
      vars:
        parameter_name: "/{{ app_name }}/{{ environment }}/deployment/current_version"
        parameter_value: "{{ git_commit_sha }}"
        tags:
          DeployedBy: "{{ ansible_user_id }}"
          DeployedAt: "{{ ansible_date_time.iso8601 }}"
          GitBranch: "{{ git_branch }}"
```

## 出力変数

各タスクは以下の変数を設定します：

### get_parameter

- `ssm_parameter_value`: 取得した値
- `ssm_parameter_metadata`: パラメータのメタデータ（型、バージョン、最終更新日）
- `ssm_operation_success`: 操作の成功/失敗
- `ssm_operation_error`: エラーメッセージ（失敗時）

### get_parameters / get_parameters_by_path

- `ssm_parameters`: 取得したパラメータの辞書（キー: パラメータ名、値: パラメータ値）
- `ssm_parameter_metadata`: 各パラメータのメタデータ
- `ssm_parameter_count`: 取得したパラメータ数

### export_to_env

- `ssm_exported_vars`: エクスポートされた環境変数名のリスト
- `ssm_export_count`: エクスポートされた変数の数

### validate_parameters

- `ssm_validation_passed`: バリデーション結果
- `ssm_validation_summary`: バリデーションのサマリー情報

## トラブルシューティング

### パラメータが見つからない

```yaml
# デバッグモードで実行
- name: Debug parameter retrieval
  ansible.builtin.include_role:
    name: ssm_parameter_store
    tasks_from: get_parameter
  vars:
    parameter_name: "/myapp/dev/missing"
    ssm_parameter_store_verbose: true
    ssm_parameter_store_debug: true
    ssm_parameter_store_fail_on_missing: false
    default_value: "fallback-value"
```

### キャッシュのクリア

```yaml
# キャッシュを無効化
- name: Get fresh parameter value
  ansible.builtin.include_role:
    name: ssm_parameter_store
    tasks_from: get_parameter
  vars:
    parameter_name: "/myapp/dev/config"
    ssm_parameter_store_cache:
      enabled: false
```

### 権限エラー

IAMロールまたはポリシーに以下の権限があることを確認：

```bash
# 権限の確認
aws ssm get-parameter --name "/myapp/dev/test" --region ap-northeast-1

# KMS権限の確認（SecureString使用時）
aws kms describe-key --key-id alias/aws/ssm --region ap-northeast-1
```

## 依存関係

- aws_setup ロール（AWS認証設定）
