# Pulumiバックエンド設定

> 📖 **親ドキュメント**: [README.md](../../README.md)

## 概要

CloudFormationで用意したS3バックエンドとSSM Parameter Storeを使ってPulumiの状態管理とパスフレーズを設定する手順です。

### 4. Pulumiバックエンドの設定

本プロジェクトはデフォルトでS3バックエンドを使用してPulumiの状態を管理します。

#### S3バックエンドの設定（推奨）

S3バックエンドはCloudFormationブートストラップで作成されたS3バケットを使用します。パスフレーズは`setup-bootstrap.sh`実行時に対話形式で設定され、SSM Parameter Storeに安全に保存されます。

##### 初回セットアップ

`setup-bootstrap.sh`を実行すると、以下の処理が自動的に行われます：

1. **S3バケットの確認**: CloudFormationで作成されたバケットを自動検出
2. **パスフレーズの設定**: 対話形式で設定（自動生成または手動入力を選択可能）
3. **SSM Parameter Storeへの保存**: SecureStringタイプで暗号化して保存

##### Ansible実行時の自動設定

**重要**: Ansibleは自動的にSSM Parameter Storeからパスフレーズを取得するため、通常は環境変数の設定は不要です。

```bash
# Ansibleを実行（パスフレーズは自動的にSSMから取得）
cd ansible
ansible-playbook playbooks/jenkins/jenkins_setup_pipeline.yml -e "env=dev"
```

##### 手動での環境変数設定（オプション）

環境変数を優先したい場合や、SSMへのアクセスを避けたい場合：

```bash
# SSMからパスフレーズを取得して環境変数に設定
export PULUMI_CONFIG_PASSPHRASE=$(aws ssm get-parameter \
  --name "/bootstrap/pulumi/config-passphrase" \
  --with-decryption \
  --query 'Parameter.Value' \
  --output text)

# S3バケット名はSSMパラメータストアから自動取得されるため、手動設定は不要
```

**パスフレーズの優先順位**:
1. 環境変数 `PULUMI_CONFIG_PASSPHRASE`（設定されている場合）
2. SSM Parameter Store `/bootstrap/pulumi/config-passphrase`（自動取得）
3. エラー（どちらも利用できない場合）

##### パスフレーズの管理

- **確認**: `aws ssm get-parameter --name "/bootstrap/pulumi/config-passphrase" --with-decryption --query 'Parameter.Value' --output text`
- **変更**: SSMコンソールまたはCLIで直接更新（既存のPulumiスタックがある場合は注意）
- **セキュリティ**: SSM Parameter StoreでKMS暗号化されているため安全

**重要**: パスフレーズは一度設定したら変更しないでください。変更すると既存のPulumiスタックにアクセスできなくなります。

## 関連ドキュメント

- [ブートストラップ構築](bootstrap.md)
- [前提条件](prerequisites.md)
- [README.md](../../README.md)
