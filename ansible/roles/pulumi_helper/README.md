# Pulumi Helper Ansible Role

このロールは、Ansible PlaybookからPulumiプロジェクトを操作するための共通ヘルパータスクを提供します。Pulumi CloudとS3バックエンドの両方に対応し、TypeScriptベースのPulumiプロジェクトの管理を自動化します。

## 概要

`pulumi_helper`ロールは、Pulumiの一般的な操作（スタックの初期化、デプロイ、削除など）をAnsibleタスクとして実行できるようにします。このロールを使用することで、インフラストラクチャのプロビジョニングワークフローをAnsibleで一元管理できます。

## 機能

- **認証管理**: Pulumi CloudとS3バックエンドの両方に対応した認証処理
- **スタック管理**: スタックの初期化、選択、削除
- **デプロイ操作**: プレビュー、デプロイ、リフレッシュ、削除
- **設定管理**: スタック設定値の管理（シークレット対応）
- **出力取得**: スタック出力値の取得と参照
- **ビルド**: TypeScriptプロジェクトのビルドとチェック

## 依存関係

- `aws_setup`ロール（AWS認証情報の設定に必要）

## 必要な環境変数

### Pulumi Cloudバックエンドの場合
```bash
export PULUMI_ACCESS_TOKEN="pul-YOUR_ACCESS_TOKEN"
```

### S3バックエンドの場合
```bash
export PULUMI_CONFIG_PASSPHRASE="your-secure-passphrase"
# AWS認証情報も必要（aws_setupロールで設定）
```

## デフォルト変数

```yaml
# Pulumiプロジェクトのベースパス
pulumi_base_path: "{{ playbook_dir }}/../../pulumi"

# バックエンドタイプ（"cloud" または "s3"）
pulumi_backend_type: "cloud"

# Pulumi Cloud設定
pulumi_cloud_url: "https://api.pulumi.com"

# S3バックエンド設定
pulumi_s3_bucket: "pulumi-state-bucket"
pulumi_s3_region: "ap-northeast-1"

# ログ出力制御
pulumi_helper_verbose: "{{ ansible_verbosity > 0 }}"
pulumi_helper_debug: "{{ ansible_verbosity > 1 }}"

# タイムアウト設定
pulumi_operation_timeout: 600  # 10分
pulumi_operation_poll: 10      # 10秒ごとにポーリング
```

## 使用方法

### 基本的な使い方

```yaml
- name: Pulumiプロジェクトをデプロイ
  hosts: localhost
  tasks:
    - name: Pulumiヘルパーロールの初期化
      ansible.builtin.include_role:
        name: pulumi_helper

    - name: スタックの初期化
      ansible.builtin.include_role:
        name: pulumi_helper
        tasks_from: init_stack
      vars:
        pulumi_project_path: "{{ pulumi_base_path }}/my-project"
        stack_name: "dev"

    - name: デプロイ実行
      ansible.builtin.include_role:
        name: pulumi_helper
        tasks_from: deploy
      vars:
        pulumi_project_path: "{{ pulumi_base_path }}/my-project"
```

### 各タスクの詳細

#### 1. スタックの初期化（init_stack）

新しいスタックを作成または既存のスタックを選択します。

```yaml
- name: スタックを初期化
  ansible.builtin.include_role:
    name: pulumi_helper
    tasks_from: init_stack
  vars:
    pulumi_project_path: "/path/to/pulumi/project"
    stack_name: "dev"
```

#### 2. TypeScriptプロジェクトのビルド（build）

TypeScriptコードをコンパイルし、構文チェックを実行します。

```yaml
- name: TypeScriptをビルド
  ansible.builtin.include_role:
    name: pulumi_helper
    tasks_from: build
  vars:
    pulumi_project_path: "/path/to/pulumi/project"
```

#### 3. デプロイプレビュー（preview）

変更内容をプレビューします（実際の変更は行いません）。

```yaml
- name: 変更をプレビュー
  ansible.builtin.include_role:
    name: pulumi_helper
    tasks_from: preview
  vars:
    pulumi_project_path: "/path/to/pulumi/project"
```

#### 4. デプロイ実行（deploy）

インフラストラクチャをデプロイします。

```yaml
- name: デプロイ実行
  ansible.builtin.include_role:
    name: pulumi_helper
    tasks_from: deploy
  vars:
    pulumi_project_path: "/path/to/pulumi/project"
```

#### 5. スタック削除（destroy）

リソースを削除します。

```yaml
- name: リソースを削除
  ansible.builtin.include_role:
    name: pulumi_helper
    tasks_from: destroy
  vars:
    pulumi_project_path: "/path/to/pulumi/project"
```

#### 6. スタックリフレッシュ（refresh）

実際のリソース状態とPulumiの状態を同期します。

```yaml
- name: スタックをリフレッシュ
  ansible.builtin.include_role:
    name: pulumi_helper
    tasks_from: refresh
  vars:
    pulumi_project_path: "/path/to/pulumi/project"
```

#### 7. 設定値の管理（set_config）

スタック設定値を設定します。

```yaml
- name: 設定値をセット
  ansible.builtin.include_role:
    name: pulumi_helper
    tasks_from: set_config
  vars:
    pulumi_project_path: "/path/to/pulumi/project"
    config_key: "aws:region"
    config_value: "ap-northeast-1"
    config_secret: false  # シークレットとして保存する場合はtrue
```

#### 8. 出力値の取得（get_outputs）

スタックの出力値を取得します。

```yaml
- name: 出力値を取得
  ansible.builtin.include_role:
    name: pulumi_helper
    tasks_from: get_outputs
  vars:
    pulumi_project_path: "/path/to/pulumi/project"
    output_name: "vpc_id"  # 特定の出力のみ取得
    # output_nameを省略すると全ての出力を取得

- name: 取得した値を使用
  ansible.builtin.debug:
    msg: "VPC ID: {{ pulumi_output_value }}"
```

#### 9. スタックの完全削除（remove_stack）

スタック自体を削除します（リソース削除後に実行）。

```yaml
- name: スタックを削除
  ansible.builtin.include_role:
    name: pulumi_helper
    tasks_from: remove_stack
  vars:
    pulumi_project_path: "/path/to/pulumi/project"
    stack_name: "dev"
```

### 実践的な使用例

完全なデプロイワークフローの例：

```yaml
- name: Pulumiプロジェクトの完全なデプロイ
  hosts: localhost
  vars:
    project_path: "{{ pulumi_base_path }}/my-infrastructure"
    stack: "production"
  tasks:
    # ロールの初期化（一度だけ実行）
    - name: Initialize Pulumi helper role
      ansible.builtin.include_role:
        name: pulumi_helper

    # スタックの初期化
    - name: Initialize stack
      ansible.builtin.include_role:
        name: pulumi_helper
        tasks_from: init_stack
      vars:
        pulumi_project_path: "{{ project_path }}"
        stack_name: "{{ stack }}"

    # 設定値の設定
    - name: Configure AWS region
      ansible.builtin.include_role:
        name: pulumi_helper
        tasks_from: set_config
      vars:
        pulumi_project_path: "{{ project_path }}"
        config_key: "aws:region"
        config_value: "ap-northeast-1"

    - name: Configure project name
      ansible.builtin.include_role:
        name: pulumi_helper
        tasks_from: set_config
      vars:
        pulumi_project_path: "{{ project_path }}"
        config_key: "projectName"
        config_value: "my-awesome-project"

    # TypeScriptのビルド
    - name: Build TypeScript project
      ansible.builtin.include_role:
        name: pulumi_helper
        tasks_from: build
      vars:
        pulumi_project_path: "{{ project_path }}"

    # 変更のプレビュー
    - name: Preview changes
      ansible.builtin.include_role:
        name: pulumi_helper
        tasks_from: preview
      vars:
        pulumi_project_path: "{{ project_path }}"

    # デプロイ実行
    - name: Deploy infrastructure
      ansible.builtin.include_role:
        name: pulumi_helper
        tasks_from: deploy
      vars:
        pulumi_project_path: "{{ project_path }}"

    # 出力値の取得
    - name: Get deployed resource outputs
      ansible.builtin.include_role:
        name: pulumi_helper
        tasks_from: get_outputs
      vars:
        pulumi_project_path: "{{ project_path }}"

    - name: Display outputs
      ansible.builtin.debug:
        msg: "Deployment outputs: {{ pulumi_output_value }}"
```

## S3バックエンドの使用

### 基本的な設定方法

S3バックエンドを使用する場合、バケット名とリージョンをAnsible変数として設定します：

```yaml
- name: S3バックエンドでPulumiを使用
  hosts: localhost
  vars:
    # S3バックエンドの設定
    pulumi_backend_type: "s3"
    pulumi_s3_bucket: "my-pulumi-state-bucket"
    pulumi_s3_region: "ap-northeast-1"
```

### 環境変数を使用した設定（推奨）

環境に応じて設定を変更できるよう、環境変数から値を取得する方法：

```yaml
- name: S3バックエンドでPulumiを使用
  hosts: localhost
  vars:
    # S3バックエンド設定（環境変数から取得、デフォルト値付き）
    pulumi_backend_type: "s3"
    pulumi_s3_bucket: "{{ lookup('env', 'PULUMI_S3_BUCKET') | default('pulumi-state-bucket') }}"
    pulumi_s3_region: "{{ lookup('env', 'PULUMI_S3_REGION') | default('ap-northeast-1') }}"
    
    # プロジェクト設定
    project_path: "{{ playbook_dir }}/../../pulumi/my-project"
  tasks:
    - name: Pulumiヘルパーの準備
      ansible.builtin.include_role:
        name: pulumi_helper

    - name: スタックの初期化
      ansible.builtin.include_role:
        name: pulumi_helper
        tasks_from: init_stack
      vars:
        pulumi_project_path: "{{ project_path }}"
        stack_name: "prod"
```

### S3バックエンド使用時の環境変数

```bash
# 必須：暗号化パスフレーズ
export PULUMI_CONFIG_PASSPHRASE="your-secure-passphrase"

# オプション：S3バケット設定（Ansible変数のデフォルト値を上書き）
export PULUMI_S3_BUCKET="my-custom-pulumi-bucket"
export PULUMI_S3_REGION="us-east-1"

# AWS認証情報（aws_setupロールで設定される）
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
```

### 完全な使用例

```yaml
- name: S3バックエンドを使用したPulumiデプロイ
  hosts: localhost
  vars:
    # 環境変数から設定を取得
    pulumi_backend_type: "s3"
    pulumi_s3_bucket: "{{ lookup('env', 'PULUMI_S3_BUCKET') | default('pulumi-state-bucket') }}"
    pulumi_s3_region: "{{ lookup('env', 'PULUMI_S3_REGION') | default('ap-northeast-1') }}"
    
    # プロジェクト設定
    project_path: "{{ playbook_dir }}/../../pulumi/infrastructure"
    stack: "{{ lookup('env', 'DEPLOY_ENV') | default('dev') }}"
  
  tasks:
    - name: Initialize Pulumi helper
      ansible.builtin.include_role:
        name: pulumi_helper

    - name: Initialize stack
      ansible.builtin.include_role:
        name: pulumi_helper
        tasks_from: init_stack
      vars:
        pulumi_project_path: "{{ project_path }}"
        stack_name: "{{ stack }}"

    - name: Deploy infrastructure
      ansible.builtin.include_role:
        name: pulumi_helper
        tasks_from: deploy
      vars:
        pulumi_project_path: "{{ project_path }}"
```

このアプローチにより、同じPlaybookを異なる環境（開発、ステージング、本番）で使い回すことができます。

## エラーハンドリング

このロールは各操作でエラーが発生した場合、わかりやすいエラーメッセージを表示します。詳細なデバッグ情報が必要な場合は、`-v`または`-vv`オプションを使用してください：

```bash
# 通常の実行
ansible-playbook deploy.yml

# 詳細なログ出力
ansible-playbook deploy.yml -v

# より詳細なデバッグ情報
ansible-playbook deploy.yml -vv
```

## チェックモード

すべてのタスクはAnsibleのチェックモード（`--check`）に対応しています：

```bash
ansible-playbook deploy.yml --check
```

## 注意事項

1. **Pulumiのインストール**: このロールはPulumiがインストール済みであることを前提としています（通常は`/root/.pulumi/bin/pulumi`）
2. **TypeScriptプロジェクト**: TypeScriptベースのPulumiプロジェクトを想定しています
3. **AWS認証**: AWS関連のリソースを扱う場合、`aws_setup`ロールによるAWS認証設定が必要です
4. **環境変数**: 必要な環境変数（`PULUMI_ACCESS_TOKEN`など）は実行前に設定してください

## トラブルシューティング

### 認証エラーが発生する場合

```bash
# Pulumi Cloudの場合
export PULUMI_ACCESS_TOKEN="pul-YOUR_TOKEN"

# S3バックエンドの場合
export PULUMI_CONFIG_PASSPHRASE="your-passphrase"
```

### TypeScriptビルドエラーが発生する場合

```yaml
# ビルドタスクを個別に実行してエラーを確認
- name: TypeScriptビルドのデバッグ
  ansible.builtin.include_role:
    name: pulumi_helper
    tasks_from: build
  vars:
    pulumi_project_path: "/path/to/project"
```

### スタックが見つからない場合

スタック名の解決に失敗している可能性があります。`-vv`でデバッグ情報を確認してください。