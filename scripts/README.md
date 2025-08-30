# スクリプト集

プロジェクトの自動化・管理用スクリプト集です。AWS、Jenkins、Ansibleなどの各種操作を効率化します。

## 📋 目次

- [概要](#概要)
- [ディレクトリ構造](#ディレクトリ構造)
- [スクリプト一覧](#スクリプト一覧)
- [使用方法](#使用方法)
- [環境変数](#環境変数)
- [セキュリティ](#セキュリティ)
- [トラブルシューティング](#トラブルシューティング)

## 概要

このディレクトリには、インフラストラクチャの構築・管理を支援する各種スクリプトが含まれています：

- **AWS操作**: 認証設定、リソース管理、状態確認
- **Jenkins設定**: インストール、構成、プラグイン管理
- **ユーティリティ**: IPホワイトリスト管理、環境設定

## ディレクトリ構造

```
scripts/
├── aws/                    # AWS関連スクリプト
│   ├── aws-env.sh         # AWS環境変数設定
│   ├── aws-stop-instances.sh  # EC2インスタンス停止
│   ├── get-pulumi-bucket.sh    # Pulumiバケット情報取得
│   ├── setup-aws-credentials.sh # AWS認証設定
│   ├── test-s3-access.sh      # S3アクセステスト
│   └── userdata/          # EC2 UserDataスクリプト
│       └── nat-instance-setup.sh # NATインスタンス設定
├── jenkins/               # Jenkins関連スクリプト
│   ├── casc/             # Configuration as Code
│   ├── groovy/           # Groovyスクリプト
│   ├── jobs/             # ジョブ定義
│   └── shell/            # シェルスクリプト
├── lambda/               # Lambda関連スクリプト
│   ├── cleanup-ssm-params.sh  # SSMパラメータクリーンアップ
│   └── verify-deployment.sh   # Lambda環境動作確認
└── workterminal/         # 作業端末用スクリプト
    ├── check-ansible-tmux.sh  # Ansible tmuxセッション確認
    ├── run-ansible-in-tmux.sh # tmux内でAnsible実行
    └── update-repo-branch.sh  # リポジトリブランチ更新
```

## スクリプト一覧

### AWS関連スクリプト

#### aws/aws-env.sh
AWS環境変数を設定します。

```bash
# 使用方法
source scripts/aws/aws-env.sh

# 設定される環境変数
# - AWS_REGION
# - AWS_DEFAULT_REGION
# - AWS_PROFILE (指定時)
```

#### aws/setup-aws-credentials.sh
AWS認証情報を対話的に設定します。

```bash
# 実行
./scripts/aws/setup-aws-credentials.sh

# プロンプトに従って以下を入力：
# - AWS Access Key ID
# - AWS Secret Access Key
# - Default region (ap-northeast-1)
# - Output format (json)
```

#### aws/get-pulumi-bucket.sh
Pulumiステート管理用S3バケット名を取得します。

```bash
# 実行
./scripts/aws/get-pulumi-bucket.sh

# 出力例
# pulumi-state-bucket-123456789012
```

#### aws/test-s3-access.sh
S3バケットへのアクセス権限をテストします。

```bash
# 使用方法
./scripts/aws/test-s3-access.sh [bucket-name]

# バケット名を自動検出する場合
./scripts/aws/test-s3-access.sh
```

#### aws/aws-stop-instances.sh
指定したタグを持つEC2インスタンスを停止します。

```bash
# 使用方法
./scripts/aws/aws-stop-instances.sh

# 環境変数で制御
export TAG_KEY="Environment"
export TAG_VALUE="dev"
./scripts/aws/aws-stop-instances.sh
```

### Jenkins関連スクリプト

#### Jenkins設定スクリプト (jenkins/shell/)

| スクリプト | 説明 | 使用場所 |
|-----------|------|----------|
| `controller-install.sh` | Jenkinsコントローラーインストール | EC2 UserData |
| `controller-configure.sh` | Jenkinsコントローラー設定 | 初期セットアップ |
| `controller-mount-efs.sh` | EFSマウント設定 | コントローラー起動時 |
| `controller-startup.sh` | Jenkinsサービス起動 | systemd |
| `controller-update.sh` | Jenkinsバージョン更新 | メンテナンス |
| `controller-user-data.sh` | UserDataスクリプト | EC2起動時 |
| `jenkins-restart.sh` | Jenkinsサービス再起動 | メンテナンス |

#### アプリケーション設定スクリプト

| スクリプト | 説明 | 実行タイミング |
|-----------|------|--------------|
| `application-install-plugins.sh` | プラグインインストール | 初期設定 |
| `application-setup-users.sh` | ユーザー設定 | 初期設定 |
| `application-setup-credentials.sh` | 認証情報設定 | 初期設定 |
| `application-configure-with-casc.sh` | JCasC適用 | 設定変更時 |
| `application-create-seed-job.sh` | Seedジョブ作成 | ジョブ設定 |
| `application-verify-all.sh` | 全設定検証 | デプロイ後 |
| `application-verify-plugins.sh` | プラグイン検証 | プラグイン更新後 |
| `application-verify-security.sh` | セキュリティ検証 | セキュリティ設定後 |
| `application-update-version.sh` | Jenkinsバージョン更新 | アップグレード時 |
| `application-cleanup-groovy.sh` | Groovyスクリプトクリーンアップ | メンテナンス |

#### Jenkins Configuration as Code (jenkins/casc/)

```yaml
# jenkins.yaml.template
# JCasC設定テンプレート
# 環境変数で動的に値を設定
jenkins:
  systemMessage: "${JENKINS_SYSTEM_MESSAGE:-Welcome to Jenkins}"
  numExecutors: ${JENKINS_NUM_EXECUTORS:-2}
  mode: ${JENKINS_MODE:-NORMAL}
```

#### Groovyスクリプト (jenkins/groovy/)

| スクリプト | 説明 | 実行方法 |
|-----------|------|----------|
| `basic-settings.groovy` | 基本設定 | Script Console |
| `install-plugins.groovy` | プラグイン管理 | Init Hook |
| `setup-users.groovy` | ユーザー管理 | Init Hook |
| `setup-credentials.groovy` | 認証情報管理 | Script Console |
| `create-seed-job.groovy` | Seedジョブ作成 | Script Console |
| `recovery-mode.groovy` | リカバリーモード | 緊急時 |

### Lambda関連スクリプト

#### lambda/verify-deployment.sh
Lambda API環境の包括的な動作確認を実行します。

```bash
# 使用方法
./scripts/lambda/verify-deployment.sh [env]

# デフォルト（dev環境）
./scripts/lambda/verify-deployment.sh

# 詳細出力モード
VERBOSE=1 ./scripts/lambda/verify-deployment.sh dev

# 確認項目：
# - SSMパラメータ（API Gateway設定、APIキー）
# - Lambda関数の状態と実行テスト
# - API Gatewayのリソースとエンドポイント
# - CloudWatchログ
# - VPC/ネットワーク設定
# - Dead Letter Queue設定
```

#### lambda/cleanup-ssm-params.sh
Lambda環境のSSMパラメータをクリーンアップします。

```bash
# 使用方法
./scripts/lambda/cleanup-ssm-params.sh [env]

# dev環境のパラメータ削除
./scripts/lambda/cleanup-ssm-params.sh dev

# 実行内容：
# 1. /lambda-api/{env}/ 以下のパラメータをリスト
# 2. 削除確認プロンプト
# 3. パラメータ削除
# 4. 削除結果の検証
```

### AWS UserDataスクリプト

#### aws/userdata/nat-instance-setup.sh
NATインスタンスの初期設定を行います。

```bash
# EC2 UserDataで自動実行
# 実行内容：
# 1. IPフォワーディング有効化
# 2. iptables設定
# 3. ソース/デスティネーションチェック無効化
```

### 作業端末用スクリプト

#### workterminal/check-ansible-tmux.sh
Ansible実行用のtmuxセッションを確認します。

```bash
# 使用方法
./scripts/workterminal/check-ansible-tmux.sh

# 実行内容：
# 1. tmuxセッションの存在確認
# 2. Ansibleプロセスの状態確認
# 3. セッション情報の表示
```

#### workterminal/run-ansible-in-tmux.sh
tmuxセッション内でAnsibleプレイブックを実行します。

```bash
# 使用方法
./scripts/workterminal/run-ansible-in-tmux.sh playbook.yml

# バックグラウンド実行
# tmuxセッションへのアタッチ
tmux attach-session -t ansible
```

#### workterminal/update-repo-branch.sh
Gitリポジトリのブランチを更新します。

```bash
# 使用方法
./scripts/workterminal/update-repo-branch.sh [branch-name]

# デフォルトブランチ（main）に切り替え
./scripts/workterminal/update-repo-branch.sh

# 特定のブランチに切り替え
./scripts/workterminal/update-repo-branch.sh feature/new-feature
```

## 使用方法

### 基本的な実行方法

```bash
# 実行権限の付与
chmod +x scripts/path/to/script.sh

# 直接実行
./scripts/path/to/script.sh

# sourceで実行（環境変数設定スクリプト）
source scripts/aws/aws-env.sh
```

### スクリプトの連携例

```bash
# 1. AWS環境設定
source scripts/aws/aws-env.sh

# 2. 認証情報設定
./scripts/aws/setup-aws-credentials.sh

# 3. S3アクセス確認
./scripts/aws/test-s3-access.sh

# 4. Jenkinsデプロイ（Ansible経由）
cd ansible
ansible-playbook playbooks/jenkins/jenkins_setup_pipeline.yml -e "env=dev"

# Lambda環境のデプロイと確認
ansible-playbook playbooks/lambda_setup_pipeline.yml -e "env=dev"
./scripts/lambda/verify-deployment.sh dev
```

## 環境変数

### 共通環境変数

| 変数名 | 説明 | デフォルト値 |
|--------|------|-------------|
| `AWS_REGION` | AWSリージョン | ap-northeast-1 |
| `AWS_PROFILE` | AWSプロファイル | default |
| `DEBUG` | デバッグモード | false |

### Jenkins関連環境変数

| 変数名 | 説明 | デフォルト値 |
|--------|------|-------------|
| `JENKINS_HOME` | Jenkinsホームディレクトリ | /var/lib/jenkins |
| `JENKINS_VERSION` | Jenkinsバージョン | 2.426.1 |
| `JENKINS_PORT` | Jenkinsポート | 8080 |
| `JENKINS_ADMIN_USER` | 管理者ユーザー | admin |

### Lambda関連環境変数

| 変数名 | 説明 | デフォルト値 |
|--------|------|-------------|
| `ENV_NAME` | 環境名 | dev |
| `VERBOSE` | 詳細出力モード | 0 |
| `LOG_LEVEL` | ログレベル | INFO |

### スクリプト固有環境変数

各スクリプトのヘッダーコメントに記載されている環境変数を確認してください。

```bash
# スクリプトヘッダーの例
#!/bin/bash
# 
# 環境変数:
#   BUCKET_NAME - S3バケット名（必須）
#   REGION - AWSリージョン（オプション、デフォルト: ap-northeast-1）
```

## セキュリティ

### 認証情報の管理

- **ハードコーディング禁止**: 認証情報をスクリプトに直接記述しない
- **環境変数使用**: AWS認証はIAMロールまたは環境変数経由
- **SSMパラメータ**: 機密情報はSSM Parameter Store（SecureString）で管理

### スクリプトの権限

```bash
# 適切な権限設定
chmod 750 scripts/sensitive-script.sh  # 所有者とグループのみ実行可能
chmod 755 scripts/public-script.sh     # 全員実行可能（読み取り専用）
```

### ログ出力

```bash
# 機密情報のマスキング例
echo "Connecting to database..." 
# パスワードは出力しない
# NG: echo "Password: $DB_PASSWORD"
# OK: echo "Password: ****"
```

## トラブルシューティング

### よくある問題と解決方法

#### 1. 権限エラー

```bash
# エラー: Permission denied
# 解決方法:
chmod +x scripts/script.sh
# またはsudoで実行
sudo ./scripts/script.sh
```

#### 2. AWS認証エラー

```bash
# エラー: Unable to locate credentials
# 解決方法:
aws configure
# または
export AWS_PROFILE=your-profile
```

#### 3. スクリプトが見つからない

```bash
# エラー: No such file or directory
# 解決方法: プロジェクトルートから実行
cd /path/to/infrastructure-as-code
./scripts/aws/script.sh
```

#### 4. 環境変数が設定されていない

```bash
# エラー: Required environment variable X not set
# 解決方法:
export X=value
# または.envファイルを使用
source .env
```

### デバッグ方法

```bash
# デバッグモードで実行
bash -x scripts/script.sh

# または環境変数で制御
DEBUG=true ./scripts/script.sh

# ログファイルに出力
./scripts/script.sh 2>&1 | tee debug.log
```

## 開発者向け情報

スクリプトの開発方法については[CONTRIBUTION.md](CONTRIBUTION.md)を参照してください。

## 関連ドキュメント

### プロジェクトドキュメント
- [メインREADME](../README.md) - プロジェクト全体の概要
- [Ansible README](../ansible/README.md) - Ansibleプレイブックとの連携
- [Pulumi README](../pulumi/README.md) - Pulumiスタックとの連携
- [Jenkins README](../jenkins/README.md) - Jenkins設定の詳細
- [CONTRIBUTION.md](CONTRIBUTION.md) - スクリプト開発規約

## サポート

問題が発生した場合は、以下を確認してください：

1. このREADMEのトラブルシューティングセクション
2. 各スクリプトのヘッダーコメント
3. 関連するシステムのREADME
4. プロジェクトのissueトラッカー