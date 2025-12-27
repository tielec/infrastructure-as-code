# ブートストラップ構築

> 📖 **親ドキュメント**: [README.md](../../README.md)

## 概要

CloudFormationで踏み台サーバーを構築し、`setup-bootstrap.sh`で開発環境を初期化する手順をまとめています。

### 2. ブートストラップ環境の構築

基本的なツールをプリインストールしたEC2踏み台サーバーをCloudFormationで構築します。

1. AWSコンソールのCloudFormationから以下のテンプレートをアップロード：
    - `bootstrap/cfn-bootstrap-template.yaml`

   **このテンプレートが作成するリソース**:
   - EC2インスタンス（t4g.small、ARM64）
   - VPC、サブネット、セキュリティグループ
   - Pulumi用S3バケット（状態管理用）
   - SSMパラメータストア（設定保存用）
   - 自動停止用Maintenance Window（毎日0:00 AM JST）

2. スタック作成時に以下のスタック名とパラメータを指定：
    - スタック名: bootstrap-iac-environment
    - パラメータ
        - `KeyName`: 先ほど作成したEC2キーペア名（例：`bootstrap-environment-key`）
        - `InstanceType`: インスタンスタイプ（デフォルト: t4g.small）
        - `AllowedIP`: SSHアクセスを許可するIPアドレス範囲（セキュリティのため自分のIPアドレスに制限することを推奨）

3. スタックが作成完了したら、出力タブから以下の情報を確認：
    - `BootstrapPublicIP`: 踏み台サーバーのパブリックIPアドレス
    - `PulumiStateBucketName`: Pulumiのステート管理用S3バケット名
    - `ManualStartCommand`: インスタンス手動起動コマンド

#### インスタンスの自動停止機能

ブートストラップインスタンスは、コスト削減のため毎日日本時間午前0時（UTC 15:00）に自動停止されます。この機能はSSM Maintenance Windowを使用して実装されています。

- **自動停止時刻**: 毎日 0:00 AM JST
- **手動起動方法**: CloudFormation出力の`ManualStartCommand`に表示されるコマンドを使用
  ```bash
  aws ec2 start-instances --instance-ids <instance-id> --region ap-northeast-1
  ```
- **自動停止の無効化**: 必要に応じてCloudFormationスタックを更新して、Maintenance Windowを無効化できます

**注意**: dev環境の Jenkins インフラ自動停止機能は現在無効化されています。コスト管理のため、必要に応じて手動での環境停止を行ってください。

### 3. 踏み台サーバーへの接続とセットアップ

1. 以下のコマンドで踏み台サーバーにSSH接続します：
   ```bash
   ssh -i bootstrap-environment-key.pem ec2-user@<BootstrapPublicIP>
   ```

2. 接続後、まずuser dataの実行が完了していることを確認します：
   ```bash
   # ログをリアルタイムで確認
   sudo less +F /var/log/cloud-init-output.log
   ```
   
   以下のメッセージが表示されていれば、初期セットアップが完了しています：
   ```
   Bootstrap setup complete!
   ```
   
   ※ `Ctrl+C`でリアルタイム表示を終了し、`q`でlessを終了します

   **プリインストールされているツール**:
   - git、python3、python3-pip、jq、tmux
   - Ansible、boto3、botocore（userspace）
   - リポジトリは既にクローン済み: `~/infrastructure-as-code`

3. セットアップが完了していたら、以下のコマンドでブートストラップセットアップを実行します：

   ```bash
   # ブートストラップセットアップスクリプトを実行
   ./infrastructure-as-code/bootstrap/setup-bootstrap.sh
   ```

   このスクリプトは以下の順序で処理を実行します：
   
   ※ `setup-bootstrap.sh`はモジュラー設計により、`bootstrap/lib/`ディレクトリ内のライブラリ関数を使用します

   **前提条件チェック（軽量処理）**
   1. OS情報の表示（Amazon Linux 2023の確認）
   2. Python環境の確認（Python3とpip3の存在確認）
   3. スクリプト実行権限の修正（リポジトリ内の全.shファイル）
   4. Docker状態の確認（インストールとデーモン状態の確認）

   **AWS関連設定（ネットワーク処理）**
   5. AWS認証情報の確認（IAMロールまたは認証情報の設定）
   6. GitHub SSHキーの設定（SSMパラメータストアと連携）
   7. OpenAI APIキーの設定（対話形式またはSSMから復元）
   8. GitHub App認証の設定（App IDと組織名の入力、秘密鍵は手動設定）
   9. Pulumi設定（S3バックエンド、パスフレーズ管理）

   **重い処理（インストールと実行）**
   10. Ansibleのインストール確認と必要に応じたインストール
   11. Ansible環境の準備（collections パスの設定とクリーンアップ）
   12. Ansibleプレイブック実行（Node.js 20、Java 21、AWS CLI v2、Docker等のインストール）
   13. systemdサービスの設定（EC2パブリックIP自動更新）

#### 手動設定が必要な項目

セットアップスクリプト（`setup-bootstrap.sh`）は対話形式で進行し、以下の設定を順番に行います。各項目はSSMパラメータストアで永続化され、インスタンス再作成時に自動復元されます。

##### 1. GitHub SSHキーの設定（手順6で実行）

**初回実行時**:
- SSHキーペアを自動生成
- GitHubメールアドレスの入力を求められる
- SSMパラメータストアに自動保存

**必要な手動作業**:
```bash
# 生成された公開鍵を表示
cat ~/.ssh/id_rsa.pub

# GitHubの Settings > SSH and GPG keys > New SSH key で上記の公開鍵を登録
```

**2回目以降の実行時**:
- SSMから自動復元（ユーザー入力不要）

**SSMパラメータ**:
- `/bootstrap/github/email` - メールアドレス
- `/bootstrap/github/ssh-private-key` - 秘密鍵（SecureString）
- `/bootstrap/github/ssh-public-key` - 公開鍵

##### 2. OpenAI APIキーの設定（手順7で実行・オプション）

**初回実行時**:
- APIキーの入力を求められる（スキップ可能）
- 入力した場合はSSMに暗号化保存

**事前準備**:
- [OpenAI Platform](https://platform.openai.com/api-keys)でAPIキーを生成
- `sk-`で始まる形式のキーを用意

**SSMパラメータ**:
- `/bootstrap/openai/api-key` - APIキー（SecureString）

##### 3. GitHub App認証の設定（手順8で実行・オプション）

**対話形式の入力**:
- App IDの入力（スキップ可能）
- 組織名/ユーザー名の入力（オプション）

**必要な手動作業**:
1. [GitHub Apps](https://github.com/settings/apps)でAppを作成
2. App IDをメモ
3. Private Keyを生成してダウンロード
4. 秘密鍵をPKCS#8形式に変換してSSMに手動登録:

```bash
# PKCS#8形式に変換（Jenkinsで必要）
# GitHubからダウンロードした鍵はPKCS#1形式（BEGIN RSA PRIVATE KEY）
# JenkinsにはPKCS#8形式（BEGIN PRIVATE KEY）が必要
openssl pkcs8 -topk8 -inform PEM -outform PEM -nocrypt \
  -in github-app-key.pem \
  -out github-app-key-pkcs8.pem

# SSMパラメータストアに登録
aws ssm put-parameter \
  --name "/bootstrap/github/app-private-key" \
  --value file://github-app-key-pkcs8.pem \
  --type SecureString \
  --overwrite \
  --region ap-northeast-1
```

**SSMパラメータ**:
- `/bootstrap/github/app-id` - App ID
- `/bootstrap/github/app-private-key` - 秘密鍵（要手動登録）
- `/bootstrap/github/app-owner` - 組織名（オプション）

##### 4. Pulumiパスフレーズの設定（手順9で実行）

**初回実行時**:
- 自動生成または手動入力を選択
- SSMパラメータストアに暗号化保存

**重要な注意事項**:
- **一度設定したパスフレーズは変更不可**（既存スタックへのアクセスが失われる）
- バックアップを強く推奨

**バックアップ方法**:
```bash
# パスフレーズを取得して安全な場所に保存
aws ssm get-parameter \
  --name "/bootstrap/pulumi/config-passphrase" \
  --with-decryption \
  --query 'Parameter.Value' \
  --output text
```

**SSMパラメータ**:
- `/bootstrap/pulumi/config-passphrase` - パスフレーズ（SecureString）

##### 設定値の永続性

すべての設定はSSMパラメータストアに保存されるため：
- EC2インスタンスを再作成しても設定が保持される
- 2回目以降の実行では自動的に復元される
- 手動作業が必要なのは初回のみ（GitHub公開鍵登録、GitHub App秘密鍵登録）

## 関連ドキュメント

- [前提条件](prerequisites.md)
- [Pulumiバックエンド設定](pulumi-backend.md)
- [README.md](../../README.md)
