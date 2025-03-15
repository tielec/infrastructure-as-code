# Jenkins CI/CD インフラストラクチャ構築

このリポジトリは、AWSクラウド上にJenkinsベースのCI/CD環境をPulumiを使って構築するためのコードを管理します。ブルーグリーンデプロイに対応したJenkinsコントローラー環境を実現し、効率的なCI/CDパイプラインを提供します。

## 前提条件

- AWSアカウント
- 有効なEC2キーペア
- CloudFormationスタックをデプロイする権限

## セットアップ手順

### 1. EC2キーペアの作成

踏み台サーバーにSSH接続するためのEC2キーペアを作成します。

1. AWSコンソールにログイン
2. EC2ダッシュボードに移動
3. 左側のメニューから「キーペア」を選択
4. 「キーペアの作成」ボタンをクリック
5. 以下の情報を入力：
    - 名前（例：`bootstrap-environment-key`）
    - キーペアタイプ：RSA
    - プライベートキー形式：.pem（OpenSSH）
6. 「キーペアの作成」ボタンをクリック
7. プライベートキー（.pemファイル）が自動的にダウンロードされます
8. ダウンロードしたキーファイルを安全に保管し、適切な権限を設定：
   ```bash
   chmod 400 bootstrap-environment-key.pem
   ```

**重要**: このプライベートキーはダウンロード時にのみ取得できます。安全に保管してください。

### 2. ブートストラップ環境の構築

次に、Pulumiを実行するための踏み台サーバーをCloudFormationで構築します。

1. AWSコンソールのCloudFormationから以下のテンプレートをアップロード：
    - `bootstrap/cfn-bootstrap-template.yaml`

2. スタック作成時に以下のスタック名とパラメータを指定：
    - スタック名: bootstrap-environment
    - パラメータ
        - `KeyName`: 先ほど作成したEC2キーペア名（例：`bootstrap-environment-key`）
        - `InstanceType`: インスタンスタイプ（デフォルト: t3.medium）
        - `AllowedIP`: SSHアクセスを許可するIPアドレス範囲（セキュリティのため自分のIPアドレスに制限することを推奨）

3. スタックが作成完了したら、出力タブから以下の情報を確認：
    - `BootstrapPublicIP`: 踏み台サーバーのパブリックIPアドレス
    - `VPCID`: 作成されたVPC ID
    - `PublicSubnetID`: パブリックサブネットID

### 3. 踏み台サーバーへの接続

1. AWSコンソールにログイン
2. EC2ダッシュボードに移動
3. インスタンスを選択
4. 「接続」ボタンをクリック
5. 「EC2 Instance Connectを使用して接続する」を選択
6. 「接続」ボタンをクリック

これにより、ブラウザベースのターミナルが開き、インスタンスに直接接続できます。

### 4. インフラストラクチャコードのセットアップ

踏み台サーバーではPulumiが正しくインストールされていないため、新たにインストールする必要があります。

```bash
# rootユーザーに切り替え
sudo su -

# Pulumiのインストール
curl -fsSL https://get.pulumi.com | sh

# パスを設定
echo 'export PATH=$PATH:$HOME/.pulumi/bin' >> ~/.bashrc
source ~/.bashrc

# Pulumiのバージョン確認
pulumi version
```

### 5. Pulumiアカウントへのログイン

Pulumiを使用するには、アカウント認証が必要です：

```bash
# Pulumiアカウントにログイン
pulumi login
```

以下のようなプロンプトが表示されます：
```
Manage your Pulumi stacks by logging in.
Run `pulumi login --help` for alternative login options.
Enter your access token from https://app.pulumi.com/account/tokens
    or hit <ENTER> to log in using your browser
```

アクセストークンを入力する場合：
1. ブラウザで https://app.pulumi.com/account/tokens にアクセス
2. 「NEW ACCESS TOKEN」をクリックしてトークンを作成
3. トークン名を入力（例：「Bootstrap Environment」）
4. 作成されたトークンをコピーして、プロンプトに貼り付け

ログインに成功すると、以下のようなメッセージが表示されます：
```
Welcome to Pulumi!
...
Logged in to pulumi.com as username (https://app.pulumi.com/username)
```

### 6. GitHubリポジトリのセットアップ

```bash
# SSHキーを作成（rootユーザーとして）
ssh-keygen -t ed25519 -C "your_email@example.com"

# 公開キーの表示（この内容をGitHubに登録）
cat ~/.ssh/id_ed25519.pub
```

表示された公開キー全体をGitHubアカウントに追加します：
1. GitHubにログイン
2. 右上のプロフィールアイコン → Settings
3. 左側メニューの「SSH and GPG keys」→「New SSH key」
4. タイトルを入力（例: EC2 Bootstrap Instance Root）
5. キータイプは「Authentication Key」を選択
6. 表示された公開キー（`ssh-ed25519`で始まる行全体）を貼り付け
7. 「Add SSH key」をクリック

GitHub認証設定後：

```bash
# リポジトリをクローン（rootユーザーとして）
git clone git@github.com:tielec/infrastructure-as-code.git
cd infrastructure-as-code

# Pulumiの初期化
pulumi stack init dev

# 依存関係のインストール
npm install

# TypeScriptをコンパイル
npx tsc
```

### 7. AWS認証情報の設定

PulumiがAWS APIにアクセスするために必要な認証情報を設定します：

```bash
# スクリプトを実行して認証情報を環境変数に設定
source scripts/aws-credentials.sh
```

### 8. Jenkinsインフラのデプロイ

```bash
cd pulumi
# プレビュー
pulumi preview

# デプロイ実行
pulumi up
```

## インフラストラクチャの構成

このリポジトリは以下のAWSリソースを設定します：

- VPC、サブネット、ルートテーブル、セキュリティグループなどのネットワークリソース
- Jenkinsコントローラー用のEC2インスタンス（ブルー/グリーン環境）
- Jenkinsエージェント用のEC2 SpotFleet（自動スケーリング対応）
- Jenkinsデータ永続化のためのEFSファイルシステム
- ブルーグリーンデプロイ用のALB（Application Load Balancer）
- Jenkins関連リソースのIAMロールとポリシー

### ディレクトリ構造

```
infrastructure-as-code/
├─bootstrap/                  # 初期セットアップ用スクリプト
│      cfn-bootstrap-template.yaml
│
├─pulumi/                     # Pulumiプロジェクト
│  │  package.json
│  │  Pulumi.yaml
│  │  tsconfig.json
│  │
│  ├─config/                  # Pulumi設定ファイル
│  └─src/                     # Pulumiソースコード
│      ├─common/              # 共通モジュール
│      │      dependency-utils.ts
│      │      network.ts
│      │
│      ├─environments/        # 環境固有のエントリーポイント
│      │  └─dev/
│      │          index.ts
│      │
│      └─services/            # サービス固有のモジュール
│          └─jenkins/
│                  jenkins-agent.ts
│                  jenkins-controller.ts
│                  load-balancer.ts
│                  security.ts
│
└─scripts/                    # 設定スクリプト
    │  aws-credentials.sh
    │
    └─jenkins/
        ├─groovy/             # Jenkins初期化用Groovyスクリプト
        │      basic-settings.groovy
        │      disable-cli.groovy
        │      install-plugins.groovy
        │      recovery-mode.groovy
        │
        └─shell/              # EC2インスタンス設定用シェルスクリプト
               agent-setup.sh
               agent-template.sh
               controller-configure.sh
               controller-install.sh
               controller-mount-efs.sh
               controller-startup.sh
               controller-update.sh
               controller-user-data.sh
```

### 主な機能

- **ブルー/グリーンデプロイメント**: Jenkinsの更新を無停止で行えるデュアル環境
- **自動スケーリングエージェント**: EC2 SpotFleetによるコスト効率の高いJenkinsエージェント
- **リカバリーモード**: 管理者アカウントロックアウト時などの緊急アクセス用モード
- **データ永続性**: EFSによるJenkinsデータの永続化と高可用性の確保
- **モジュール化された設計**: サービスと環境を分離した再利用しやすい構造
- **最新版Jenkins対応**: 常に最新バージョンのJenkinsを使用可能

### アーキテクチャの特徴

- **共通モジュール**: ネットワークなど複数のサービスで共有するインフラリソース
- **サービス固有モジュール**: Jenkins専用のリソース定義（コントローラー、エージェント、ロードバランサーなど）
- **環境分離**: 開発、ステージング、本番などの環境を簡単に追加できる構造

## トラブルシューティング

- **Pulumiデプロイエラー**: `pulumi logs`でエラー詳細を確認
- **AWS認証エラー**: `source scripts/aws-credentials.sh`を実行して認証情報を更新
- **Jenkinsへのアクセス問題**: セキュリティグループの設定を確認
- **EFSマウント問題**: マウントターゲットの可用性を確認

## 注意事項

- 本番環境では適切なセキュリティ設定を行ってください
- AdministratorAccess権限は開発段階のみに使用し、本番環境では最小権限原則に従ってください
- バックアップ戦略の実装を忘れずに行ってください
- AWS認証情報は定期的に更新が必要です。セッションが切れた場合は`source scripts/aws-credentials.sh`を実行してください

## 拡張方法

リポジトリ構造は以下のように拡張可能です：

1. 新しいサービスの追加:
```
services/
  ├─jenkins/
  ├─database/
  └─api-service/
```

2. 新しい環境の追加:
```
environments/
  ├─dev/
  ├─staging/
  └─production/
```