# AWS Setup Ansible Role

このロールは、AWS認証情報のセットアップと検証を行い、PulumiやAWS CLIなどのツールがAWSリソースを操作できるように環境を準備します。

## 概要

`aws_setup`ロールは、AWS CLI認証情報の設定状態を確認し、必要に応じて認証情報をセットアップします。主にPulumiでのインフラ管理をサポートするために使用されます。

## 機能

- **認証情報の確認**: 既存のAWS認証情報の有効性をチェック
- **自動セットアップ**: 認証情報が未設定の場合、自動的に設定スクリプトを実行
- **権限管理**: 必要なスクリプトファイルの実行権限を自動設定
- **環境変数の準備**: PulumiなどのAWS操作を行うツール用の環境変数テンプレートを生成

## デフォルト変数

```yaml
# AWS認証情報セットアップスクリプトのパス
aws_credentials_script_path: "/root/infrastructure-as-code/scripts/aws/setup-aws-credentials.sh"

# デフォルトのAWSリージョン
aws_region: "ap-northeast-1"
```

## 使用方法

### 依存関係として使用（推奨）

このロールは通常、他のロールの依存関係として定義されます：

```yaml
# roles/pulumi_helper/meta/main.yml の例
---
dependencies:
  - role: aws_setup
```

### 直接使用する場合

```yaml
- name: AWS環境のセットアップ
  hosts: localhost
  tasks:
    - name: AWS認証情報をセットアップ
      ansible.builtin.include_role:
        name: aws_setup
```

## 必要なスクリプト

このロールは以下のスクリプトファイルが存在することを前提としています：

1. **aws-env.sh**: AWS環境変数を設定するスクリプト
   - パス: `{{ playbook_dir }}/../../scripts/aws/aws-env.sh`
   
2. **setup-aws-credentials.sh**: AWS認証情報をセットアップするスクリプト
   - パス: `{{ playbook_dir }}/../../scripts/aws/setup-aws-credentials.sh`
   - デフォルト値は変数で上書き可能

## 動作の詳細

1. **スクリプトの権限確認と設定**
   - 必要なスクリプトファイルの存在確認
   - 実行権限がない場合は自動的に付与（755）

2. **認証情報の確認**
   - `aws sts get-caller-identity`コマンドで現在の認証状態を確認
   - 成功した場合は既存の設定を使用

3. **認証情報の設定**
   - 認証情報が無効または未設定の場合、setup-aws-credentials.shを実行
   - 設定後、再度認証情報の有効性を確認

4. **環境変数テンプレートの作成**
   - Pulumiなどのツール用に環境変数のテンプレートを生成
   - `aws_env_vars`変数として他のタスクから参照可能

## 出力変数

- **aws_env_vars**: PulumiやAWS CLIで使用する環境変数のテンプレート文字列

## トラブルシューティング

### 認証情報の設定に失敗する場合

1. setup-aws-credentials.shスクリプトが正しく配置されているか確認：
   ```bash
   ls -la /root/infrastructure-as-code/scripts/aws/setup-aws-credentials.sh
   ```

2. スクリプトの内容が正しいか確認（AWS認証情報の設定ロジックが含まれているか）

3. 手動でAWS認証情報を設定：
   ```bash
   aws configure
   ```

### 権限エラーが発生する場合

スクリプトファイルの権限を手動で設定：
```bash
chmod +x /root/infrastructure-as-code/scripts/aws/*.sh
```

### デバッグ情報を表示する

詳細なデバッグ情報を表示するには、`-v`オプションを使用：
```bash
ansible-playbook your-playbook.yml -v
```

## 注意事項

1. **セキュリティ**: AWS認証情報を含む出力は自動的に非表示（no_log: true）に設定されています
2. **前提条件**: AWS CLIがインストールされている必要があります
3. **実行環境**: rootユーザーでの実行を想定しています（パスが/root/で始まる）
