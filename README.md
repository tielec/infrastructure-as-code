# Jenkins CI/CD インフラストラクチャ構築

このリポジトリは、AWSクラウド上にJenkinsベースのCI/CD環境をAnsibleとPulumiを組み合わせて段階的に構築するためのコードを管理します。ブルーグリーンデプロイに対応したJenkinsコントローラー環境を実現し、効率的なCI/CDパイプラインを提供します。

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

次に、Pulumiを実行するための踏み台サーバーをCloudFormationで構築します。このテンプレートはAnsible、Pulumi、その他必要なツールを自動的にインストールします。

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

1. 以下のコマンドで踏み台サーバーにSSH接続します：
   ```bash
   ssh -i bootstrap-environment-key.pem ec2-user@<BootstrapPublicIP>
   ```

   または

2. AWSコンソールからEC2インスタンスに接続する方法：
   - AWSコンソールにログイン
   - EC2ダッシュボードに移動
   - インスタンスを選択
   - 「接続」ボタンをクリック
   - 「EC2 Instance Connectを使用して接続する」を選択
   - 「接続」ボタンをクリック

接続すると、自動的にインストールされたツールの概要と次のステップを示すREADMEが表示されます。

### 4. インストール検証と初期設定

踏み台サーバーには以下のツールが自動的にインストールされています：
- AWS CLI v2
- Node.js 16.x
- Python 3 と pip3
- Ansible
- Pulumi
- Git

最初にインストールが正常に完了したことを確認します：

```bash
# インストールされたツールを確認
./verify-installation.sh
```

検証が完了したら、Pulumiアカウントにログインします：

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

### 5. GitHubリポジトリのセットアップ

```bash
# SSHキーを作成
ssh-keygen -t ed25519 -C "your_email@example.com"

# 公開キーの表示（この内容をGitHubに登録）
cat ~/.ssh/id_ed25519.pub
```

表示された公開キー全体をGitHubアカウントに追加します：
1. GitHubにログイン
2. 右上のプロフィールアイコン → Settings
3. 左側メニューの「SSH and GPG keys」→「New SSH key」
4. タイトルを入力（例: EC2 Bootstrap Instance）
5. キータイプは「Authentication Key」を選択
6. 表示された公開キー（`ssh-ed25519`で始まる行全体）を貼り付け
7. 「Add SSH key」をクリック

GitHub認証設定後：

```bash
# リポジトリをクローン
git clone git@github.com:tielec/infrastructure-as-code.git
cd infrastructure-as-code
```

### 6. AWS認証情報の設定

PulumiがAWS APIにアクセスするために必要な認証情報を設定します：

```bash
# スクリプトを実行して認証情報を環境変数に設定
source scripts/aws-credentials.sh
```

### 7. Ansibleの設定確認とパラメータの更新

Ansible設定とパラメータを確認する手順です：

```bash
# リポジトリのディレクトリに移動
cd infrastructure-as-code

# ansible.cfg の設定を確認
cat ansible/ansible.cfg

# 共有パラメータファイルを確認
cat ansible/inventory/group_vars/all.yml

# 設定ファイルとパラメータに問題がないことを確認するための実行
cd ansible
ansible-playbook playbooks/jenkins_setup_pipeline.yml -e "env=dev" --check
```

`--check`オプションを使うと、実際のデプロイを行わずにプレイブックの実行可能性を確認できます。

### 8. Jenkinsインフラの段階的デプロイ

確認ができたら、実際のデプロイを行います：

```bash
# 全体のデプロイパイプラインを実行（初期構築）
cd ansible
ansible-playbook playbooks/jenkins_setup_pipeline.yml -e "env=dev"

# 特定のコンポーネントだけをデプロイする場合
ansible-playbook playbooks/jenkins_setup_pipeline.yml -e "env=dev run_network=true run_security=false run_storage=false"
```

各コンポーネントを個別にデプロイすることも可能です：

```bash
# ネットワークコンポーネントのみをデプロイ
ansible-playbook playbooks/deploy_jenkins_network.yml -e "env=dev"

# セキュリティグループのみをデプロイ
ansible-playbook playbooks/deploy_jenkins_security.yml -e "env=dev"

# その他のコンポーネントも同様に個別デプロイ可能
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
├─ansible/                     # Ansible設定ファイル
│  ├─ansible.cfg               # Ansible設定
│  ├─inventory/
│  │  ├─hosts
│  │  └─group_vars/
│  │      └─all.yml            # 共通変数定義ファイル
│  ├─playbooks/                # 各種プレイブック
│  │  ├─jenkins_setup_pipeline.yml  # メインパイプライン
│  │  ├─deploy_jenkins_network.yml
│  │  ├─deploy_jenkins_security.yml
│  │  ├─deploy_jenkins_storage.yml
│  │  ├─deploy_jenkins_loadbalancer.yml
│  │  ├─deploy_jenkins_controller.yml
│  │  ├─deploy_jenkins_agent.yml
│  │  └─deploy_jenkins_application.yml
│  └─roles/                    # 共通ロール
│      ├─aws_setup/           # AWS環境設定ロール
│      │  ├─defaults/
│      │  ├─tasks/
│      │  └─vars/
│      └─pulumi_helper/       # Pulumiヘルパーロール
│          ├─defaults/
│          └─tasks/
│
├─bootstrap/                  # 初期セットアップ用スクリプト
│   └─cfn-bootstrap-template.yaml
│
├─pulumi/                     # Pulumiプロジェクト
│  ├─package.json             # ルートパッケージ設定
│  ├─Pulumi.yaml              # ルートプロジェクト設定
│  ├─tsconfig.json            # TypeScript設定
│  ├─config/                  # 設定ディレクトリ
│  ├─network/                 # ネットワークスタック
│  │  ├─index.ts
│  │  ├─Pulumi.yaml
│  │  └─package.json
│  ├─security/                # セキュリティスタック
│  │  ├─index.ts
│  │  ├─Pulumi.yaml
│  │  ├─package.json
│  │  └─tsconfig.json
│  └─src/                     # ソースコード
│      ├─common/              # 共通ユーティリティ
│      │  └─dependency-utils.ts
│      └─services/            # サービス別モジュール
│          └─jenkins/         # Jenkins関連モジュール
│              ├─index.ts
│              ├─jenkins-agent.ts
│              ├─jenkins-controller.ts
│              ├─load-balancer.ts
│              ├─network.ts
│              └─security.ts
│
└─scripts/                    # 設定スクリプト
    │  aws-credentials.sh
    │
    └─jenkins/
        ├─groovy/             # Jenkins初期化用Groovyスクリプト
        │  ├─basic-settings.groovy
        │  ├─disable-cli.groovy
        │  ├─install-plugins.groovy
        │  └─recovery-mode.groovy
        │
        └─shell/              # EC2インスタンス設定用シェルスクリプト
           ├─agent-setup.sh
           ├─agent-template.sh
           ├─controller-configure.sh
           ├─controller-install.sh
           ├─controller-mount-efs.sh
           ├─controller-startup.sh
           ├─controller-update.sh
           └─controller-user-data.sh
```

### 主な機能

- **段階的デプロイ**: Ansibleを使用して各コンポーネントを順番にデプロイ
- **モジュール分割**: 各インフラコンポーネントを独立したPulumiスタックとして管理
- **ブルー/グリーンデプロイメント**: Jenkinsの更新を無停止で行えるデュアル環境
- **自動スケーリングエージェント**: EC2 SpotFleetによるコスト効率の高いJenkinsエージェント
- **リカバリーモード**: 管理者アカウントロックアウト時などの緊急アクセス用モード
- **データ永続性**: EFSによるJenkinsデータの永続化と高可用性の確保

### アーキテクチャの特徴

- **レイヤー分離**: ネットワーク、セキュリティ、ストレージなどのレイヤーを分離
- **Ansible + Pulumi連携**: Ansibleでオーケストレーション、Pulumiでインフラ構築
- **依存関係管理**: 各スタック間の依存関係を明示的に制御

## トラブルシューティング

- **Pulumiデプロイエラー**: `pulumi logs`でエラー詳細を確認
- **Ansibleエラー**: `-vvv`オプションを追加して詳細なログを確認（例: `ansible-playbook -vvv playbooks/jenkins_setup_pipeline.yml`）
- **AWS認証エラー**: `source scripts/aws-credentials.sh`を実行して認証情報を更新
- **Jenkinsへのアクセス問題**: セキュリティグループの設定を確認
- **EFSマウント問題**: マウントターゲットの可用性を確認

## 共有パラメータの確認と修正

共有パラメータファイル（`all.yml`）が適切に設定されていることを確認してください。パラメータを変更する場合は以下の手順で行います：

```bash
# パラメータファイルを編集
vi ansible/inventory/group_vars/all.yml

# エディタで必要な変更を行った後、構文をチェック
ansible-playbook playbooks/jenkins_setup_pipeline.yml -e "env=dev" --syntax-check

# 変更を適用（コミットする前にチェックモードで実行）
ansible-playbook playbooks/jenkins_setup_pipeline.yml -e "env=dev" --check
```

## 注意事項

- 本番環境では適切なセキュリティ設定を行ってください
- AdministratorAccess権限は開発段階のみに使用し、本番環境では最小権限原則に従ってください
- バックアップ戦略の実装を忘れずに行ってください
- AWS認証情報は定期的に更新が必要です。セッションが切れた場合は`source scripts/aws-credentials.sh`を実行してください

## 拡張方法

リポジトリ構造は以下のように拡張可能です：

1. 新しいコンポーネントの追加:
```
pulumi/
  ├─network/          # 既存のネットワークスタック
  ├─security/         # 既存のセキュリティスタック
  ├─monitoring/       # 新しいモニタリングスタック
  └─database/         # 新しいデータベーススタック
```

2. 新しいAnsibleプレイブックの追加:
```
ansible/playbooks/
  ├─jenkins_setup_pipeline.yml      # 既存のメインパイプライン
  ├─deploy_jenkins_network.yml      # 既存のネットワークデプロイ
  └─deploy_monitoring.yml           # 新しいモニタリングデプロイ
```