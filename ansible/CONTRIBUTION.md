# Ansible開発ガイド

Ansibleプレイブック・ロールの開発者向けガイドです。

## 📋 目次

- [開発環境](#開発環境)
- [コーディング規約](#コーディング規約)
- [プレイブック開発](#プレイブック開発)
- [ロール開発](#ロール開発)
- [テスト](#テスト)
- [ベストプラクティス](#ベストプラクティス)
- [トラブルシューティング](#トラブルシューティング)

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

```yaml
---
# 複数のプレイブックを連携させるパイプライン
- name: Setup Pipeline
  hosts: localhost
  gather_facts: no
  
  vars:
    pipeline_steps:
      - name: "SSMパラメータ初期化"
        playbook: "deploy_jenkins_ssm_init.yml"
      - name: "ネットワーク構築"
        playbook: "deploy_jenkins_network.yml"
      - name: "セキュリティ設定"
        playbook: "deploy_jenkins_security.yml"
        
  tasks:
    - name: パイプライン実行
      include_tasks: "{{ item.playbook }}"
      loop: "{{ pipeline_steps }}"
      loop_control:
        label: "{{ item.name }}"
```

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

## ヘルパーロールの活用

### 重要：ヘルパーロールの積極的利用

このプロジェクトでは、一般的な操作を標準化し、コードの重複を避けるために以下のヘルパーロールを提供しています。**新しいロールやプレイブックを作成する際は、必ずこれらのヘルパーロールの利用を検討してください。**

**⚠️ 注意：ロールからヘルパーロールを使用する場合は、必ず`meta/main.yml`の`dependencies`セクションに依存関係を定義してください。プレイブックから直接使用する場合は、`include_role`で呼び出せます。**

### 利用可能なヘルパーロール

#### 1. pulumi_helper - Pulumiスタック操作

Pulumiスタックの操作を標準化するロール。直接Pulumiコマンドを実行する代わりに、このロールを使用してください。

```yaml
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

### ヘルパーロールの依存関係設定（重要）

**⚠️ 重要：ヘルパーロールを使用するには、必ずロールの`meta/main.yml`に依存関係を定義する必要があります。**

```yaml
# roles/your_role/meta/main.yml
---
dependencies:
  - role: pulumi_helper
    when: use_pulumi | default(false)
  
  - role: ssm_parameter_store
    when: use_ssm | default(false)
  
  - role: aws_cli_helper
    when: use_aws_cli | default(false)
  
  - role: aws_setup
    when: validate_aws_env | default(true)
```

または、常に依存する場合：

```yaml
# roles/jenkins_controller/meta/main.yml
---
dependencies:
  - pulumi_helper  # Pulumiスタック操作に必須
  - ssm_parameter_store  # パラメータ管理に必須
  - aws_cli_helper  # AWS操作に必須
```

### カスタムヘルパーロールの作成

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
    │   ├── main.yml       # メインタスク
    │   ├── deploy.yml     # デプロイタスク
    │   ├── destroy.yml    # 削除タスク
    │   └── validate.yml   # 検証タスク
    ├── handlers/
    │   └── main.yml       # ハンドラー
    ├── templates/
    │   └── config.j2      # テンプレート
    ├── files/
    │   └── script.sh      # 静的ファイル
    └── meta/
        └── main.yml       # ⚠️ 重要：依存関係の定義（ヘルパーロール等）
```

#### meta/main.ymlの例

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

# ヘルパーロールへの依存関係を定義
dependencies:
  - role: aws_setup
    vars:
      validate_credentials: true
      
  - role: pulumi_helper
    vars:
      pulumi_backend: s3
      
  - role: ssm_parameter_store
    vars:
      ssm_path_prefix: "/{{ project_name }}/{{ env }}"
      
  - role: aws_cli_helper
    vars:
      aws_region: "{{ aws_region | default('ap-northeast-1') }}"
```

### タスク分割パターン

```yaml
# tasks/main.yml
---
- name: アクションの選択
  include_tasks: "{{ action }}.yml"
  when: action is defined
  
# tasks/deploy.yml
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
    
# tasks/destroy.yml
---
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