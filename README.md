# Jenkins CI/CD インフラストラクチャ構築

このリポジトリは、AWSクラウド上にJenkinsベースのCI/CD環境をPulumiとAnsibleを使って構築するためのコードを管理します。ブルーグリーンデプロイに対応したJenkinsコントローラー環境を実現し、効率的なCI/CDパイプラインを提供します。

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

次に、PulumiとAnsibleを実行するための踏み台サーバーをCloudFormationで構築します。

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

### 4. 必要なツールのインストール

踏み台サーバーにAnsibleとPulumiをインストールします：

```bash
# rootユーザーに切り替え
sudo su -

# 必要なパッケージをインストール
yum update -y
yum install -y git python3 python3-pip nodejs npm

# Ansibleのインストール
pip3 install ansible

# Pulumiのインストール
curl -fsSL https://get.pulumi.com | sh

# パスを設定
echo 'export PATH=$PATH:$HOME/.pulumi/bin' >> ~/.bashrc
source ~/.bashrc

# バージョン確認
ansible --version
pulumi version
```

### 5. GitHubリポジトリのクローン

```bash
# SSHキーを作成（rootユーザーとして）
ssh-keygen -t ed25519 -C "your_email@example.com"

# 公開キーの表示（この内容をGitHubに登録）
cat ~/.ssh/id_ed25519.pub

# リポジトリをクローン
git clone git@github.com:yourusername/jenkins-infra.git
cd jenkins-infra
```

### 6. AWS認証情報の設定

PulumiとAnsibleがAWS APIにアクセスするために必要な認証情報を設定します：

```bash
# AWS CLIのインストール（まだ入っていない場合）
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# 認証情報の設定
aws configure
```

プロンプトで以下の情報を入力します：
- AWS Access Key ID
- AWS Secret Access Key
- Default region name（例：ap-northeast-1）
- Default output format（例：json）

### 7. Pulumiのセットアップ

```bash
# Pulumiにログイン
pulumi login

# AWS認証情報の確認
aws sts get-caller-identity
```

### 8. Jenkinsインフラのデプロイ

AnsibleプレイブックによるJenkinsインフラの段階的デプロイを実行します：

```bash
cd ansible

# 環境変数の設定（必要に応じて）
export AWS_REGION=ap-northeast-1
export ENVIRONMENT=dev
export PROJECT_NAME=jenkins-infra

# ネットワークのみをデプロイしてテスト
ansible-playbook playbooks/jenkins-setup-pipeline.yml \
  -e "env=dev run_network=true"
```

デプロイが成功したら、段階的に他のコンポーネントも有効化できます：

```bash
# セキュリティグループの追加
ansible-playbook playbooks/jenkins-setup-pipeline.yml \
  -e "env=dev run_network=true run_security=true"

# ストレージの追加
ansible-playbook playbooks/jenkins-setup-pipeline.yml \
  -e "env=dev run_network=true run_security=true run_storage=true"

# 以下同様に他のコンポーネントも追加
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
jenkins-infra/
├─ansible/                    # Ansible関連ファイル
│  ├─inventory/               # インベントリファイル
│  │  └─group_vars/           # グループ変数
│  ├─playbooks/               # プレイブック
│  │    jenkins-setup-pipeline.yml    # メインプレイブック
│  │    deploy_jenkins_network.yml    # ネットワークデプロイ
│  │    deploy_jenkins_security.yml   # セキュリティグループデプロイ
│  │    deploy_jenkins_storage.yml    # ストレージデプロイ
│  │    deploy_jenkins_loadbalancer.yml  # ロードバランサーデプロイ
│  │    deploy_jenkins_controller.yml    # コントローラーデプロイ
│  │    deploy_jenkins_agent.yml      # エージェントデプロイ
│  │    deploy_jenkins_application.yml   # アプリケーション設定デプロイ
│  └─roles/                   # Ansibleロール
│
├─bootstrap/                  # 初期セットアップ用スクリプト
│      cfn-bootstrap-template.yaml
│
├─pulumi/                     # Pulumiプロジェクト
│  ├─common/                  # 共通モジュール
│  │    dependency-utils.ts
│  │
│  ├─network/                 # ネットワークスタック
│  │    index.ts
│  │    Pulumi.yaml
│  │    package.json
│  │
│  ├─security/                # セキュリティスタック
│  ├─storage/                 # ストレージスタック
│  ├─loadbalancer/            # ロードバランサースタック
│  └─jenkins/                 # Jenkinsスタック
│
└─scripts/                    # 設定スクリプト
    └─jenkins/
        ├─groovy/             # Jenkins初期化用Groovyスクリプト
        │      basic-settings.groovy
        │      disable-cli.groovy
        │      recovery-mode.groovy
        │
        └─shell/              # EC2インスタンス設定用シェルスクリプト
               agent-setup.sh
               controller-configure.sh
               controller-install.sh
               controller-mount-efs.sh
               controller-startup.sh
               controller-update.sh
               controller-user-data.sh
```

### アーキテクチャの特徴

- **Ansible + Pulumi**: AnsibleによるオーケストレーションとPulumiによるインフラストラクチャ定義
- **段階的デプロイ**: 各コンポーネントを段階的に構築
- **モジュール化されたスタック**: 各コンポーネントが独立したPulumiスタックとして管理
- **ブルー/グリーンデプロイメント**: Jenkinsの更新を無停止で行えるデュアル環境
- **自動スケーリングエージェント**: EC2 SpotFleetによるコスト効率の高いJenkinsエージェント
- **データ永続性**: EFSによるJenkinsデータの永続化と高可用性の確保

## トラブルシューティング

### Ansibleの問題
- **プレイブック実行エラー**: `ansible-playbook playbooks/jenkins-setup-pipeline.yml -vvv` で詳細なデバッグ情報を確認
- **変数の問題**: `ansible-playbook --syntax-check playbooks/jenkins-setup-pipeline.yml` で文法チェック

### Pulumiの問題
- **デプロイエラー**: `pulumi logs`でエラー詳細を確認
- **スタックの状態確認**: `pulumi stack` で現在のスタック状態を確認
- **リソースの一覧表示**: `pulumi stack --show-resources` でデプロイされたリソースを確認

### AWS認証の問題
- **認証情報の更新**: `aws configure` を再実行
- **認証情報の検証**: `aws sts get-caller-identity` で現在のIAMユーザー/ロールを確認
- **アクセス権限の確認**: IAMコンソールでポリシーが正しく設定されているか確認

## 拡張方法

### 新しいスタックの追加
1. `pulumi/` ディレクトリに新しいコンポーネント用のディレクトリを作成
2. 必要なPulumiファイル（index.ts, Pulumi.yaml, package.json）を作成
3. `ansible/playbooks/` に対応するデプロイプレイブックを作成
4. メインのパイプラインプレイブックに新しいステップを追加

### 既存スタックの修正
1. 対応するPulumiディレクトリのコードを更新
2. `pulumi preview` で変更内容を確認
3. Ansibleプレイブックを実行して変更をデプロイ

### 複数環境のサポート
環境ごとに異なる設定を適用する場合:
1. 環境ごとのPulumi設定ファイル（例：Pulumi.prod.yaml）を作成
2. ansible-playbookコマンドの `-e "env=prod"` パラメータで環境を指定