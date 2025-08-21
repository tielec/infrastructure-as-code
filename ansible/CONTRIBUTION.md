# Ansible開発ガイド

Ansibleプレイブック・ロールの開発者向けガイドです。

## 📋 目次

- [開発環境](#開発環境)
- [コーディング規約](#コーディング規約)
- [プレイブック開発](#プレイブック開発)
- [ロール開発](#ロール開発)
  - [ロール構造](#ロール構造)
  - [ヘルパーロールの活用](#ヘルパーロールの活用)
  - [タスク分割パターン](#タスク分割パターン重要)
- [テスト](#テスト)
- [ベストプラクティス](#ベストプラクティス)
- [グループ変数](#グループ変数)
- [トラブルシューティング](#トラブルシューティング)
- [コントリビューション](#コントリビューション)

## 開発環境

### 必要ツール

```bash
# Python仮想環境のセットアップ
python3 -m venv venv
source venv/bin/activate

# 開発用パッケージのインストール
pip install -r requirements-dev.txt
```

### requirements-dev.txt

```
ansible>=2.9
ansible-lint>=5.0
yamllint>=1.26
boto3>=1.20
botocore>=1.23
pytest>=7.0
pytest-ansible>=3.0
```

### 開発用設定

```bash
# ansible.cfg (開発用)
[defaults]
stdout_callback = debug
verbosity = 2
gathering = explicit
host_key_checking = False
retry_files_enabled = True
deprecation_warnings = True
```

## コーディング規約

### YAML記述ルール

```yaml
---
# 1. ファイルは必ず「---」で開始
# 2. インデントはスペース2文字
# 3. リスト項目は「-」とスペース1文字
# 4. コロンの後にはスペース1文字
# 5. 行末の空白は禁止
# 6. ファイル末尾に空行を1つ

- name: タスク名は日本語で記述
  module_name:
    parameter1: value1
    parameter2: value2
  when: condition
  register: result
  tags:
    - deploy
    - config
```

### 命名規則

#### ファイル名

```
# プレイブック
{action}_{component}_{target}.yml
例: deploy_jenkins_network.yml

# ロール
{component}_{function}
例: jenkins_controller, lambda_functions

# 変数ファイル
{environment}.yml または {component}_vars.yml
例: dev.yml, jenkins_vars.yml
```

#### 変数名

```yaml
# Snake_caseを使用
jenkins_version: "2.426.1"
aws_region: "ap-northeast-1"

# 環境固有変数にはプレフィックス
dev_instance_type: "t3.small"
prod_instance_type: "t3.large"

# プライベート変数にはアンダースコア
_temp_password: "temporary"
```

### タスク記述規約

```yaml
# 良い例
- name: Jenkinsコントローラーをデプロイ
  include_role:
    name: jenkins_controller
    tasks_from: deploy
  vars:
    instance_type: "{{ jenkins_instance_type }}"
  when: jenkins_deploy_controller | default(true) | bool
  tags:
    - jenkins
    - controller
    - deploy

# 悪い例
- include_role:  # nameがない
    name: jenkins_controller
    tasks_from: deploy
```

## プレイブック開発

### プレイブック構造

```yaml
---
# プレイブックの説明
#
# 実行例
# ======
#
# 基本実行:
#   ansible-playbook playbooks/example.yml -e "env=dev"
#
# デバッグモード:
#   ansible-playbook playbooks/example.yml -e "env=dev" -vvv
#

- name: プレイブック名
  hosts: localhost
  gather_facts: no
  
  vars:
    # プレイブックレベル変数
    default_env: dev
    
  pre_tasks:
    # 事前チェック
    - name: 必須パラメータの確認
      assert:
        that:
          - env is defined
        fail_msg: "env パラメータが必要です"
        
  tasks:
    # メイン処理
    - name: メインタスク
      include_role:
        name: role_name
        
  post_tasks:
    # 後処理
    - name: 実行結果のサマリー表示
      debug:
        msg: "処理が完了しました"
        
  handlers:
    # ハンドラー定義
    - name: restart service
      service:
        name: service_name
        state: restarted
```

### パイプラインプレイブック

パイプラインプレイブックは、複数のプレイブックを連携させて実行するための仕組みです。

```yaml
---
# 基本的なパイプライン構造
- name: Lambda Setup Pipeline
  hosts: localhost
  gather_facts: no
  
  vars:
    env: "{{ env | default('dev') }}"
    
# 各プレイブックを条件付きでインポート
- import_playbook: lambda/lambda_ssm_init.yml
  vars:
    env: "{{ env }}"
  when: run_ssm_init | default(true) | bool
  tags:
    - ssm-init

- import_playbook: lambda/lambda_network.yml
  vars:
    env: "{{ env }}"
  when: run_network | default(true) | bool
  tags:
    - network

- import_playbook: lambda/lambda_security.yml
  vars:
    env: "{{ env }}"
  when: run_security | default(true) | bool
  tags:
    - security
```

**注意事項:**
- `import_playbook` を使用（`ansible.builtin.import_playbook` ではない）
- `vars` と `when` パラメータがサポートされている
- 変数の循環参照に注意（詳細は[トラブルシューティング](#変数の循環参照エラー)を参照）
- import_playbookのエラー対処法は[トラブルシューティング](#import_playbookでエラーが発生する問題)を参照

### テストプレイブック記述規約

```yaml
---
# テストプレイブックの説明
#
# 実行例
# ======
#
# 基本実行:
#   ansible-playbook playbooks/test/test-example.yml
#
# パラメータ指定:
#   ansible-playbook playbooks/test/test-example.yml -e param=value
#
# デバッグモード:
#   ansible-playbook playbooks/test/test-example.yml -vvv
#
- name: テストプレイブック名
  hosts: localhost
  gather_facts: no
  
  tasks:
    - name: テスト実行
      # テスト実装
```

## ロール開発

### ロール構造

```
roles/
└── role_name/
    ├── README.md           # ロールの説明
    ├── defaults/
    │   └── main.yml       # デフォルト変数
    ├── vars/
    │   └── main.yml       # ロール変数
    ├── tasks/
    │   ├── main.yml       # ⚠️ 必須：エントリーポイント（deploy/destroy の振り分け）
    │   ├── deploy.yml     # ⚠️ 必須：デプロイタスク
    │   ├── destroy.yml    # ⚠️ 必須：削除タスク
    │   └── validate.yml   # オプション：検証タスク
    ├── handlers/
    │   └── main.yml       # ハンドラー
    ├── templates/
    │   └── config.j2      # テンプレート
    ├── files/
    │   └── script.sh      # 静的ファイル
    └── meta/
        └── main.yml       # ⚠️ 重要：依存関係の定義（ヘルパーロール等）
```

**注意事項:**
- `tasks/main.yml`、`tasks/deploy.yml`、`tasks/destroy.yml` の3ファイルは必須
- main.yml は operation 変数に基づいて deploy/destroy を振り分ける役割のみ
- 実際の処理は deploy.yml と destroy.yml に実装する

### ヘルパーロールの活用

このプロジェクトでは、一般的な操作を標準化し、コードの重複を避けるために以下のヘルパーロールを提供しています。**新しいロールやプレイブックを作成する際は、必ずこれらのヘルパーロールの利用を検討してください。**

**⚠️ 注意：ロールからヘルパーロールを使用する場合は、必ず`meta/main.yml`の`dependencies`セクションに依存関係を定義してください。プレイブックから直接使用する場合は、`include_role`で呼び出せます。**

#### 1. pulumi_helper - Pulumiスタック操作

Pulumiスタックの操作を標準化するロール。直接Pulumiコマンドを実行する代わりに、このロールを使用してください。

**⚠️ 重要な実装パターン：**
- **必ず `tasks_from` パラメータを使用**して特定のタスクファイルを呼び出す
- `pulumi_action` 変数によるアクション制御は使用しない（エラーの原因となる）
- スタック初期化には `tasks_from: init_stack` を使用する
- 実行されない場合のトラブルシューティングは[こちら](#pulumiヘルパーロールが実行されない問題)を参照

```yaml
# ✅ 正しい実装例：tasks_from を使用
- name: Pulumiスタックを初期化
  ansible.builtin.include_role:
    name: pulumi_helper
    tasks_from: init_stack  # 特定のタスクファイルを直接指定
  vars:
    pulumi_project_path: "{{ playbook_dir }}/../../pulumi/lambda-ssm-init"
    stack_name: "{{ env_name }}"

# ❌ 間違った実装例：pulumi_action を使用
- name: Pulumiスタックを初期化（動作しない）
  ansible.builtin.include_role:
    name: pulumi_helper
  vars:
    pulumi_action: "init"  # これは動作しない
    pulumi_project_path: "{{ playbook_dir }}/../../pulumi/lambda-ssm-init"
    stack_name: "{{ env_name }}"

# デプロイ
- name: Pulumiスタックをデプロイ
  ansible.builtin.include_role:
    name: pulumi_helper
    tasks_from: deploy
  vars:
    stack_name: "jenkins-network"
    stack_path: "{{ playbook_dir }}/../../pulumi/jenkins-network"
    pulumi_env: "{{ env }}"

# プレビュー
- name: 変更をプレビュー
  ansible.builtin.include_role:
    name: pulumi_helper
    tasks_from: preview
  vars:
    stack_name: "jenkins-network"
    stack_path: "{{ playbook_dir }}/../../pulumi/jenkins-network"

# 削除
- name: スタックを削除
  ansible.builtin.include_role:
    name: pulumi_helper
    tasks_from: destroy
  vars:
    stack_name: "jenkins-network"
    stack_path: "{{ playbook_dir }}/../../pulumi/jenkins-network"
    force_destroy: true  # 確認なしで削除

# リフレッシュ
- name: スタック状態をリフレッシュ
  ansible.builtin.include_role:
    name: pulumi_helper
    tasks_from: refresh
  vars:
    stack_name: "jenkins-network"
    stack_path: "{{ playbook_dir }}/../../pulumi/jenkins-network"
```

#### 2. ssm_parameter_store - SSMパラメータ管理

AWS Systems Manager Parameter Storeの操作を抽象化。パラメータの取得・設定・削除を簡単に実行できます。

```yaml
# パラメータ取得
- name: データベースパスワードを取得
  ansible.builtin.include_role:
    name: ssm_parameter_store
    tasks_from: get_parameter
  vars:
    parameter_name: "/jenkins-infra/{{ env }}/database/password"
    decrypt: true  # SecureStringの復号化
    store_as: "db_password"  # 結果を保存する変数名

# 取得した値の使用
- name: 取得した値を使用
  debug:
    msg: "Database password: {{ ssm_parameter_value }}"

# パラメータ設定
- name: アプリケーションバージョンを設定
  ansible.builtin.include_role:
    name: ssm_parameter_store
    tasks_from: set_parameter
  vars:
    parameter_name: "/jenkins-infra/{{ env }}/app/version"
    parameter_value: "{{ app_version }}"
    parameter_type: "String"  # String, StringList, SecureString
    description: "Application version"
    overwrite: true

# パラメータ削除
- name: 不要なパラメータを削除
  ansible.builtin.include_role:
    name: ssm_parameter_store
    tasks_from: delete_parameter
  vars:
    parameter_name: "/jenkins-infra/{{ env }}/temp/value"

# バルク取得（パスプレフィックスで複数取得）
- name: 環境のすべてのパラメータを取得
  ansible.builtin.include_role:
    name: ssm_parameter_store
    tasks_from: get_parameters_by_path
  vars:
    parameter_path: "/jenkins-infra/{{ env }}"
    recursive: true
    decrypt: true
```

#### 3. aws_cli_helper - AWS CLIコマンド実行

AWS CLIコマンドの実行を標準化し、エラーハンドリングとリトライを提供します。

```yaml
# 基本的な実行
- name: EC2インスタンスを一覧表示
  ansible.builtin.include_role:
    name: aws_cli_helper
    tasks_from: execute
  vars:
    aws_command: "ec2 describe-instances --filters Name=tag:Environment,Values={{ env }}"
    operation_name: "List EC2 instances"
    parse_output: true  # JSON出力を自動パース

# 結果の使用
- name: 結果を表示
  debug:
    var: aws_cli_result

# リトライ付き実行（一時的な失敗に対応）
- name: S3バケット作成（リトライ付き）
  ansible.builtin.include_role:
    name: aws_cli_helper
    tasks_from: execute_with_retry
  vars:
    aws_command: "s3api create-bucket --bucket {{ bucket_name }} --region {{ aws_region }}"
    operation_name: "Create S3 bucket"
    max_retries: 5
    retry_delay: 10

# 複雑なクエリの実行
- name: 特定のタグを持つリソースを検索
  ansible.builtin.include_role:
    name: aws_cli_helper
    tasks_from: execute
  vars:
    aws_command: |
      resourcegroupstaggingapi get-resources \
        --tag-filters Key=Environment,Values={{ env }} \
        --resource-type-filters ec2:instance \
        --query 'ResourceTagMappingList[].ResourceARN'
    operation_name: "Find tagged resources"
    parse_output: true

# エラーハンドリング付き実行
- name: リソースの存在チェック
  ansible.builtin.include_role:
    name: aws_cli_helper
    tasks_from: execute
  vars:
    aws_command: "ec2 describe-instances --instance-ids {{ instance_id }}"
    operation_name: "Check instance existence"
    ignore_errors: true  # エラーを無視して続行
```

#### 4. aws_setup - AWS環境セットアップ

AWS環境の基本的な検証と設定を行います。プレイブックの最初に実行することを推奨。

```yaml
# AWS環境の検証
- name: AWS環境をセットアップ
  ansible.builtin.include_role:
    name: aws_setup
  vars:
    required_aws_region: "{{ aws_region | default('ap-northeast-1') }}"
    validate_credentials: true
    check_required_services:
      - ec2
      - s3
      - ssm
      - cloudformation
```

### ヘルパーロール利用のベストプラクティス

#### 1. 直接コマンド実行を避ける

```yaml
# ❌ 悪い例：直接コマンド実行
- name: Pulumiデプロイ
  shell: |
    cd {{ stack_path }}
    pulumi up -y --stack {{ stack_name }}
  environment:
    PULUMI_CONFIG_PASSPHRASE: "{{ pulumi_passphrase }}"

# ✅ 良い例：ヘルパーロール使用
- name: Pulumiデプロイ
  ansible.builtin.include_role:
    name: pulumi_helper
    tasks_from: deploy
  vars:
    stack_name: "{{ stack_name }}"
    stack_path: "{{ stack_path }}"
```

#### 2. エラーハンドリングの活用

```yaml
# ヘルパーロールは適切なエラーハンドリングを提供
- name: 重要なパラメータを取得
  ansible.builtin.include_role:
    name: ssm_parameter_store
    tasks_from: get_parameter
  vars:
    parameter_name: "/critical/parameter"
    required: true  # 存在しない場合はエラー
    decrypt: true
```

#### 3. 結果の再利用

```yaml
# ヘルパーロールの結果を後続タスクで使用
- name: VPC情報を取得
  ansible.builtin.include_role:
    name: aws_cli_helper
    tasks_from: execute
  vars:
    aws_command: "ec2 describe-vpcs --filters Name=tag:Name,Values={{ vpc_name }}"
    parse_output: true

- name: VPC IDを使用
  debug:
    msg: "VPC ID: {{ aws_cli_result.Vpcs[0].VpcId }}"
```

#### 5. カスタムヘルパーロールの作成

新しいヘルパーロールを作成する際のガイドライン：

```yaml
# roles/custom_helper/meta/main.yml
---
dependencies: []  # ヘルパーロール自体は通常依存関係を持たない

# roles/custom_helper/tasks/main.yml
---
- name: パラメータ検証
  assert:
    that:
      - required_param is defined
    fail_msg: "required_param is required"

- name: デフォルト値の設定
  set_fact:
    optional_param: "{{ optional_param | default('default_value') }}"

- name: メイン処理
  # 実装

- name: 結果を返す
  set_fact:
    helper_result: "{{ result }}"
```

### meta/main.ymlの例（依存関係の定義）

**⚠️ 重要：ヘルパーロールを使用するには、必ずロールの`meta/main.yml`に依存関係を定義する必要があります。**

```yaml
# roles/jenkins_controller/meta/main.yml
---
galaxy_info:
  author: DevOps Team
  description: Jenkins Controller deployment role
  min_ansible_version: 2.9
  platforms:
    - name: Ubuntu
      versions:
        - focal
        - jammy

# ヘルパーロールへの依存関係を定義（条件付き）
dependencies:
  - role: aws_setup
    vars:
      validate_credentials: true
    when: validate_aws_env | default(true)
      
  - role: pulumi_helper
    vars:
      pulumi_backend: s3
    when: use_pulumi | default(false)
      
  - role: ssm_parameter_store
    vars:
      ssm_path_prefix: "/{{ project_name }}/{{ env }}"
    when: use_ssm | default(false)
      
  - role: aws_cli_helper
    vars:
      aws_region: "{{ aws_region | default('ap-northeast-1') }}"
    when: use_aws_cli | default(false)
```

または、常に依存する場合：

```yaml
# roles/lambda_functions/meta/main.yml
---
dependencies:
  - pulumi_helper  # Pulumiスタック操作に必須
  - ssm_parameter_store  # パラメータ管理に必須
  - aws_cli_helper  # AWS操作に必須
```

### タスク分割パターン（重要）

**⚠️ 基本運用ルール: すべてのロールは必ず `deploy.yml` と `destroy.yml` に分割して実装してください。**

このリポジトリでは、インフラストラクチャの作成と削除を明確に分離するため、すべてのAnsibleロールで以下の構造を採用しています：

```yaml
# tasks/main.yml - 必須：エントリーポイント
---
- name: Include deploy tasks
  ansible.builtin.include_tasks: deploy.yml
  when: operation | default('deploy') == 'deploy'

- name: Include destroy tasks
  ansible.builtin.include_tasks: destroy.yml
  when: operation | default('deploy') == 'destroy'

# tasks/deploy.yml - 必須：デプロイメント処理
---
- name: 事前検証
  include_tasks: validate.yml

# ✅ ヘルパーロールを使用してPulumiスタックをデプロイ
- name: リソースのデプロイ
  include_role:
    name: pulumi_helper
    tasks_from: deploy
  vars:
    stack_name: "{{ component_name }}-{{ env }}"
    stack_path: "{{ pulumi_stack_path }}"
    pulumi_env: "{{ env }}"

# ✅ SSMパラメータストアに結果を保存
- name: デプロイ結果をSSMに保存
  include_role:
    name: ssm_parameter_store
    tasks_from: set_parameter
  vars:
    parameter_name: "/{{ project_name }}/{{ env }}/{{ component_name }}/deployed_at"
    parameter_value: "{{ ansible_date_time.iso8601 }}"
    parameter_type: "String"
    
# tasks/destroy.yml - 必須：削除処理
---
- name: 削除前の確認
  ansible.builtin.pause:
    prompt: "Press ENTER to confirm deletion, or Ctrl+C to cancel"
  when: 
    - force_destroy is not defined or not force_destroy
    - not preview_only | default(false)

# ✅ AWS CLIヘルパーでリソースの存在確認
- name: リソースの存在確認
  include_role:
    name: aws_cli_helper
    tasks_from: execute
  vars:
    aws_command: "cloudformation describe-stacks --stack-name {{ stack_name }}"
    operation_name: "Check stack existence"
    ignore_errors: true

# ✅ ヘルパーロールを使用してリソースを削除
- name: リソースの削除
  include_role:
    name: pulumi_helper
    tasks_from: destroy
  vars:
    stack_name: "{{ component_name }}-{{ env }}"
    stack_path: "{{ pulumi_stack_path }}"
    force_destroy: "{{ force | default(false) }}"
  when: aws_cli_result is defined

# ✅ SSMパラメータも削除
- name: 関連するSSMパラメータを削除
  include_role:
    name: ssm_parameter_store
    tasks_from: delete_parameter
  vars:
    parameter_name: "/{{ project_name }}/{{ env }}/{{ component_name }}/deployed_at"
```

#### deploy/destroy 分割の利点

1. **明確な責任分離**: 作成と削除のロジックが混在しない
2. **安全性の向上**: 誤った削除を防ぐための確認処理を標準化
3. **保守性の向上**: 各ファイルが単一の目的を持つ
4. **再利用性**: deploy/destroy を個別に呼び出し可能

#### 実装ガイドライン

```yaml
# 呼び出し例（プレイブックから）
- name: デプロイ実行
  include_role:
    name: jenkins_controller
  vars:
    operation: deploy  # デフォルト値なので省略可能

- name: 削除実行
  include_role:
    name: jenkins_controller
  vars:
    operation: destroy
    force_destroy: true  # 確認プロンプトをスキップ
```

#### 必須変数と推奨変数

**deploy.yml で使用する変数:**
- `preview_only`: プレビューのみ実行（デフォルト: false）
- `env_name` または `env`: 環境名（dev/prod）
- `project_name`: プロジェクト名

**destroy.yml で使用する変数:**
- `force_destroy`: 確認なしで削除（デフォルト: false）
- `preview_only`: 削除のプレビューのみ（デフォルト: false）
- `remove_stack`: Pulumiスタック自体も削除（デフォルト: true）
- `force_manual_cleanup`: 手動削除を強制（デフォルト: false）

### 変数管理

```yaml
# defaults/main.yml - オーバーライド可能
---
component_version: "1.0.0"
component_enabled: true

# vars/main.yml - 固定値
---
component_home: "/opt/component"
component_user: "component"
```

## テスト

### ユニットテスト

```python
# tests/test_role.py
import pytest
from ansible.playbook import Playbook

def test_role_syntax():
    """ロールの構文チェック"""
    pb = Playbook.load('playbooks/test_role.yml')
    assert pb is not None
    
def test_role_variables():
    """変数の妥当性チェック"""
    # 実装
```

### 統合テスト

```yaml
# playbooks/test/test-integration.yml
---
- name: 統合テスト
  hosts: localhost
  
  tasks:
    - name: コンポーネントAのデプロイ
      include_role:
        name: component_a
        tasks_from: deploy
        
    - name: デプロイ結果の検証
      assert:
        that:
          - deploy_result.changed
          - deploy_result.resources_created > 0
```

### Lintチェック

```bash
# ansible-lint実行
ansible-lint playbooks/*.yml

# yamllint実行
yamllint -c .yamllint .

# カスタムルール (.yamllint)
---
extends: default
rules:
  line-length:
    max: 120
  indentation:
    spaces: 2
```

## ベストプラクティス

### 1. 冪等性の確保

```yaml
# changed_whenで状態管理
- name: リソースをデプロイ
  command: pulumi up -y
  register: result
  changed_when: result.stdout is search('Resources:.*created|updated|deleted')
  
# check_modeサポート
- name: ファイル作成
  file:
    path: /tmp/test
    state: touch
  check_mode: yes
```

### 2. エラーハンドリング

```yaml
# block/rescue/always
- block:
    - name: リスクのある処理
      command: risky_command
      
  rescue:
    - name: エラー時の処理
      debug:
        msg: "エラー発生: {{ ansible_failed_result.msg }}"
        
  always:
    - name: クリーンアップ
      command: cleanup_command
```

### 3. パフォーマンス最適化

```yaml
# 並列実行
- name: 複数リソースの並列デプロイ
  include_role:
    name: "{{ item }}"
  loop:
    - component_a
    - component_b
  vars:
    ansible_async: 600
    ansible_poll: 0
    
# fact収集の最適化
- hosts: all
  gather_facts: no  # 不要な場合は無効化
```

### 4. デバッグ支援

```yaml
# デバッグ出力
- name: 変数の確認
  debug:
    var: item
    verbosity: 2  # -vv以上で表示
  loop: "{{ debug_vars }}"
  tags:
    - never
    - debug
```

### 5. Vault使用

```yaml
# 機密情報の暗号化
ansible-vault create group_vars/prod/secrets.yml

# 実行時
ansible-playbook playbook.yml --vault-password-file ~/.vault_pass
```

## グループ変数

### 変数定義例

```yaml
# inventory/group_vars/all.yml
---
# プロジェクト共通設定
aws_region: ap-northeast-1

# Pulumi設定
pulumi_org: "{{ lookup('env', 'PULUMI_ORG', default='organization') }}"
pulumi_backend_type: s3

# システム別設定 - Jenkins
jenkins_project_name: jenkins-infra
jenkins_version: "{{ lookup('env', 'JENKINS_VERSION', default='2.426.1') }}"
jenkins_home: /var/lib/jenkins

# システム別設定 - Lambda
lambda_project_name: lambda-functions
lambda_runtime: python3.9

# タグ設定
default_tags:
  ManagedBy: ansible
  Environment: "{{ env | default('dev') }}"
```

### 環境別変数

```yaml
# inventory/group_vars/dev.yml
---
instance_type: t3.small
min_size: 1
max_size: 3

# inventory/group_vars/prod.yml
---
instance_type: t3.large
min_size: 2
max_size: 10
```

## トラブルシューティング

### デバッグテクニック

```bash
# 詳細ログ
ANSIBLE_DEBUG=1 ansible-playbook playbook.yml -vvvv

# 特定タスクのみ実行
ansible-playbook playbook.yml --start-at-task="タスク名"

# ステップ実行
ansible-playbook playbook.yml --step

# Dry run
ansible-playbook playbook.yml --check --diff
```

### よくある問題

#### 変数未定義エラー

```yaml
# 解決方法: デフォルト値を設定
- name: 変数使用
  debug:
    msg: "{{ my_var | default('default_value') }}"
```

#### タスクのスキップ

```yaml
# 解決方法: when条件の確認
- name: デバッグ用when条件確認
  debug:
    msg: "条件: {{ my_condition }}"
  when: my_condition is defined
```

#### パフォーマンス問題

```yaml
# 解決方法: fact収集の最適化
- hosts: all
  gather_facts: no
  tasks:
    - name: 必要な時のみfact収集
      setup:
        gather_subset:
          - min
```

#### Pulumiヘルパーロールが実行されない問題

**症状：** `pulumi_helper` ロールを呼び出してもPulumiコマンドが実行されない

```yaml
# 問題の原因: pulumi_action変数を使用している
- name: Initialize stack (動作しない)
  ansible.builtin.include_role:
    name: pulumi_helper
  vars:
    pulumi_action: "init"  # これは動作しない

# 解決方法: tasks_fromを使用して特定のタスクファイルを指定
- name: Initialize stack (正しい)
  ansible.builtin.include_role:
    name: pulumi_helper
    tasks_from: init_stack  # 直接タスクファイルを指定
  vars:
    pulumi_project_path: "{{ stack_path }}"
    stack_name: "{{ env_name }}"
```

#### import_playbookでエラーが発生する問題

**症状：** `ansible.builtin.import_playbook` を使用すると "has extra params" エラーが発生

```yaml
# 問題の原因: ansible.builtin.import_playbook を使用
- ansible.builtin.import_playbook: playbook.yml  # エラー
  vars:
    env: "{{ env }}"
  when: condition

# 解決方法: import_playbook を使用（ansible.builtin. プレフィックスなし）
- import_playbook: playbook.yml  # 正しい
  vars:
    env: "{{ env }}"
  when: condition
```

#### 変数の循環参照エラー

**症状：** "An unhandled exception occurred while templating" エラーが発生

```yaml
# 問題の原因: 変数が自己参照している
- name: Execute role
  ansible.builtin.include_role:
    name: my_role
  vars:
    operation: "{{ operation | default('deploy') }}"  # 循環参照

# 解決方法: 中間変数を使用
- name: Set operation variable
  ansible.builtin.set_fact:
    role_operation: "{{ operation | default('deploy') }}"
    
- name: Execute role
  ansible.builtin.include_role:
    name: my_role
  vars:
    operation: "{{ role_operation }}"  # 中間変数を使用
```

#### SSMパラメータが初期化されない問題

**症状：** SSM初期化ロールを実行してもパラメータが作成されない

**原因の調査方法:**

1. **ロールの構造を確認**
   - `tasks/main.yml`が正しくタスクを振り分けているか
   - `deploy.yml`が実際のPulumiコマンドを呼び出しているか

2. **pulumi_helperの呼び出し方を確認**
   - `tasks_from`パラメータが正しく設定されているか
   - `pulumi_action`を使用していないか（これは動作しない）

3. **デバッグ方法**
   ```yaml
   - name: Debug role execution
     ansible.builtin.include_role:
       name: ssm_init
     vars:
       ansible_verbosity: 3  # デバッグログを有効化
   ```

4. **正しい実装パターンの確認**
   - 動作しているJenkinsの実装と比較
   - `tasks_from: init_stack`が使用されているか確認

## コントリビューション

### コミット規約

```
[ansible] action: 詳細な説明

action: add|update|fix|remove|refactor

例:
[ansible] add: Jenkins用の新しいデプロイロールを追加
[ansible] fix: jenkins_controllerロールのエラー処理を修正
[ansible] update: Lambda関数のタイムアウト値を30秒に変更
```

### プルリクエスト

1. featureブランチを作成
2. Lintチェックをパス
3. テストを追加・更新
4. ドキュメントを更新
5. PRを作成

## 関連ドキュメント

- [Ansible README](README.md) - 使用方法
- [メインCLAUDE.md](../CLAUDE.md) - 開発ガイドライン
- [Pulumi CONTRIBUTION](../pulumi/CONTRIBUTION.md) - Pulumi開発規約