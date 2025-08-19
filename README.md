# Jenkins CI/CD インフラストラクチャ構築

このリポジトリは、AWSクラウド上にJenkinsベースのCI/CD環境をAnsibleとPulumiを組み合わせて段階的に構築するためのコードを管理します。ブルーグリーンデプロイに対応したJenkinsコントローラー環境を実現し、効率的なCI/CDパイプラインを提供します。

## 前提条件

- AWSアカウント
- 有効なEC2キーペア
- CloudFormationスタックをデプロイする権限
- Pulumiアカウント（アクセストークンが必要）

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

基本的なツールをインストールしたEC2踏み台サーバーをCloudFormationで構築します。

1. AWSコンソールのCloudFormationから以下のテンプレートをアップロード：
    - `bootstrap/cfn-bootstrap-template.yaml`

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

ブートストラップインスタンスは、コスト削減のため毎日日本時間午前1時（UTC 16:00）に自動停止されます。この機能はSSM Maintenance Windowを使用して実装されています。

- **自動停止時刻**: 毎日 1:00 AM JST
- **手動起動方法**: CloudFormation出力の`ManualStartCommand`に表示されるコマンドを使用
  ```bash
  aws ec2 start-instances --instance-ids <instance-id> --region ap-northeast-1
  ```
- **自動停止の無効化**: 必要に応じてCloudFormationスタックを更新して、Maintenance Windowを無効化できます

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
   
   以下のメッセージが表示されていれば、セットアップが完了しています：
   ```
   Bootstrap setup complete!
   ```
   
   ※ `Ctrl+C`でリアルタイム表示を終了し、`q`でlessを終了します

3. セットアップが完了していたら、以下のコマンドでブートストラップセットアップを実行します：

   ```bash
   # ブートストラップセットアップスクリプトを実行
   ./infrastructure-as-code/bootstrap/setup-bootstrap.sh
   ```

   このスクリプトは以下の処理を自動的に行います：
   - GitHubアクセス用のSSHキー設定（SSMパラメータストアと連携）
   - OpenAI APIキーの設定（対話形式またはSSMから復元）
   - GitHub App認証の設定（対話形式、秘密鍵は手動設定必要）
   - Pulumiバックエンドの設定（S3バックエンド、パスフレーズ管理）
   - Node.js 20 LTS, Java 21, AWS CLI v2, Pulumi, Docker, Ansibleなどのインストール
   - AWS認証情報の設定
   - systemdサービスによるEC2パブリックIP自動更新の設定

#### 手動設定が必要な項目

##### 1. GitHub SSHキーの登録

`setup-bootstrap.sh`は、GitHub SSHキーをSSMパラメータストアで管理します：

- **初回実行時**: 
  - SSHキーを自動生成
  - メールアドレスの入力は初回のみ必要
  - SSMパラメータストアに自動保存（秘密鍵は暗号化）
  - **手動作業**: 生成された公開鍵をGitHubに登録
    ```bash
    # 公開鍵を表示
    cat ~/.ssh/id_rsa.pub
    # GitHubの Settings > SSH and GPG keys > New SSH key で登録
    ```
  
- **2回目以降（新しいインスタンス）**:
  - SSMから自動的にキーを復元
  - ユーザー入力不要で処理を継続
  
- **保存されるパラメータ**:
  - `/bootstrap/github/email` - GitHubメールアドレス
  - `/bootstrap/github/ssh-private-key` - 秘密鍵（SecureString）
  - `/bootstrap/github/ssh-public-key` - 公開鍵

##### 2. OpenAI APIキーの設定

OpenAI APIキーの管理（オプション）：

- **初回実行時**:
  - 対話形式でAPIキーの入力を求められる
  - スキップ可能（後から設定も可能）
  - SSMパラメータストアに暗号化して保存
  
- **保存先**:
  - `/bootstrap/openai/api-key` - APIキー（SecureString）

- **手動取得が必要**:
  - [OpenAI Platform](https://platform.openai.com/api-keys)でAPIキーを生成
  - `sk-`で始まる形式のキーを取得

##### 3. GitHub App認証の設定

GitHub App認証の設定（オプション）：

- **対話形式の設定**:
  - App IDの入力
  - 組織名/ユーザー名の入力（オプション）
  
- **手動作業が必要**:
  1. [GitHub Apps](https://github.com/settings/apps)でAppを作成
  2. App IDをメモ
  3. Private Keyを生成してダウンロード
  4. PKCS#8形式に変換:
     ```bash
     openssl pkcs8 -topk8 -inform PEM -outform PEM -nocrypt \
       -in github-app-key.pem \
       -out github-app-key-pkcs8.pem
     ```
  5. SSMに手動登録:
     ```bash
     aws ssm put-parameter \
       --name "/bootstrap/github/app-private-key" \
       --value file://github-app-key-pkcs8.pem \
       --type SecureString \
       --overwrite \
       --region ap-northeast-1
     ```

- **保存されるパラメータ**:
  - `/bootstrap/github/app-id` - App ID
  - `/bootstrap/github/app-private-key` - 秘密鍵（要手動設定）
  - `/bootstrap/github/app-owner` - 組織名（オプション）

##### 4. Pulumiパスフレーズの管理

Pulumiのパスフレーズは自動生成されますが、以下の点に注意：

- **初回設定時**:
  - 自動生成または手動入力を選択
  - SSMパラメータストアに暗号化保存
  - **重要**: 一度設定したパスフレーズは変更しないこと（既存スタックにアクセスできなくなる）

- **バックアップ推奨**:
  ```bash
  # パスフレーズの確認（安全な場所に保存）
  aws ssm get-parameter \
    --name "/bootstrap/pulumi/config-passphrase" \
    --with-decryption \
    --query 'Parameter.Value' \
    --output text
  ```

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

# S3バケット名を設定（オプション - 通常は自動検出）
export PULUMI_STATE_BUCKET_NAME=$(aws cloudformation describe-stacks \
  --stack-name bootstrap-environment \
  --query "Stacks[0].Outputs[?OutputKey=='PulumiStateBucketName'].OutputValue" \
  --output text)
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

#### Pulumi Cloudバックエンドの使用（代替）

Pulumi Cloudを使用する場合：

1. [Pulumi Console](https://app.pulumi.com/account/tokens)からアクセストークンを取得
2. 環境変数を設定：
   ```bash
   export PULUMI_ACCESS_TOKEN="pul-YOUR_ACCESS_TOKEN"
   ```
3. Ansible実行時にバックエンドタイプを指定：
   ```bash
   ansible-playbook playbooks/jenkins/jenkins_setup_pipeline.yml \
     -e "env=dev pulumi_backend_type=cloud"
   ```

### 5. Jenkinsインフラの段階的デプロイ

環境準備ができたら、以下のコマンドでインフラをデプロイします：

```bash
# infrastructure-as-codeディレクトリに移動
cd ~/infrastructure-as-code

# 全体のデプロイパイプラインを実行（初期構築）
cd ansible
ansible-playbook playbooks/jenkins/jenkins_setup_pipeline.yml -e "env=dev"

# 特定のコンポーネントだけをデプロイする場合
ansible-playbook playbooks/jenkins/jenkins_setup_pipeline.yml -e "env=dev run_network=true run_security=false run_storage=false"
```

各コンポーネントを個別にデプロイすることも可能です：

```bash
# ネットワークコンポーネントのみをデプロイ
ansible-playbook playbooks/jenkins/deploy/deploy_jenkins_network.yml -e "env=dev"

# セキュリティグループのみをデプロイ
ansible-playbook playbooks/jenkins/deploy/deploy_jenkins_security.yml -e "env=dev"

# Jenkins Agent AMIビルダーをデプロイ（デフォルトでImage Builderパイプライン自動実行）
ansible-playbook playbooks/jenkins/deploy/deploy_jenkins_agent_ami.yml -e "env=dev"

# Jenkins Agent AMIビルダーをデプロイ（パイプライン実行を抑制）
ansible-playbook playbooks/jenkins/deploy/deploy_jenkins_agent_ami.yml -e "env=dev trigger_ami_build=false"

# その他のコンポーネントも同様に個別デプロイ可能
```

#### バックグラウンドデプロイメント（tmux使用）

長時間かかるデプロイメントをバックグラウンドで実行・管理する方法：

##### 基本的な使い方

```bash
# tmuxセッション作成
tmux new-session -d -s jenkins-deploy

# コマンド実行
tmux send-keys -t jenkins-deploy "cd ~/infrastructure-as-code/ansible" C-m
tmux send-keys -t jenkins-deploy "ansible-playbook playbooks/jenkins/jenkins_setup_pipeline.yml -e 'env=dev'" C-m

# セッションにアタッチして進捗確認
tmux attach -t jenkins-deploy

# 操作方法
# デタッチ（バックグラウンドに戻す）: Ctrl+b, d
# 再アタッチ: tmux attach -t jenkins-deploy
# セッション一覧: tmux ls
# セッション削除: tmux kill-session -t jenkins-deploy
```

##### 複数コンポーネントの並行デプロイ

```bash
# 複数ウィンドウでの管理
tmux new-session -d -s jenkins
tmux new-window -t jenkins:1 -n network
tmux new-window -t jenkins:2 -n controller
tmux new-window -t jenkins:3 -n agent-ami
tmux new-window -t jenkins:4 -n agent

# 各ウィンドウでコマンド実行
cd ~/infrastructure-as-code/ansible
tmux send-keys -t jenkins:1 "ansible-playbook playbooks/jenkins/deploy/deploy_jenkins_network.yml -e 'env=dev'" C-m
tmux send-keys -t jenkins:2 "ansible-playbook playbooks/jenkins/deploy/deploy_jenkins_controller.yml -e 'env=dev'" C-m
tmux send-keys -t jenkins:3 "ansible-playbook playbooks/jenkins/deploy/deploy_jenkins_agent_ami.yml -e 'env=dev'" C-m
tmux send-keys -t jenkins:4 "ansible-playbook playbooks/jenkins/deploy/deploy_jenkins_agent.yml -e 'env=dev'" C-m

# 特定のウィンドウを確認
tmux attach -t jenkins:2

# ウィンドウ間の移動
# 次のウィンドウ: Ctrl+b, n
# 前のウィンドウ: Ctrl+b, p
# ウィンドウ一覧: Ctrl+b, w
```

##### ログ出力の保存

```bash
# tmux内でログを保存しながら実行
tmux new-session -d -s jenkins-deploy
tmux send-keys -t jenkins-deploy "cd ~/infrastructure-as-code/ansible" C-m
tmux send-keys -t jenkins-deploy "ansible-playbook playbooks/jenkins/jenkins_setup_pipeline.yml -e 'env=dev' | tee ~/jenkins-deploy-$(date +%Y%m%d-%H%M%S).log" C-m

# ログをキャプチャ（セッション全体の出力を保存）
tmux pipe-pane -t jenkins-deploy -o "cat >> ~/jenkins-deploy.log"
```

**tmuxの利点**:
- SSHセッションが切れても処理が継続
- 実行中のプロセスに後から再接続可能
- リアルタイムで進捗確認
- 複数のデプロイを並行管理
- エラー時の対話的な対処が可能

**実行時間の目安**:
- 全体デプロイ: 約30-45分
- Agent AMI作成（Image Builder）: 追加で最大1時間

### 6. Jenkins環境構築後の設定管理

Jenkins環境が構築された後、アプリケーションレベルの設定を管理できます：

```bash
# Jenkinsのバージョン更新、プラグインインストール、CLIユーザー作成、シードジョブ作成、再起動を実行
ansible-playbook playbooks/jenkins/deploy/deploy_jenkins_application.yml -e "env=dev"

# Jenkinsバージョンのみ更新（プラグインインストールはスキップ）
ansible-playbook playbooks/jenkins/deploy/deploy_jenkins_application.yml -e "env=dev version=2.426.1 plugins=false"

# プラグインのみインストール（Gitリポジトリ更新はスキップ）
ansible-playbook playbooks/jenkins/deploy/deploy_jenkins_application.yml -e "env=dev update_git=false plugins=true restart=false"

# シードジョブのみ作成（他の設定はスキップ）
ansible-playbook playbooks/jenkins/deploy/deploy_jenkins_application.yml -e "env=dev jenkins_version=latest install_plugins=false setup_cli_user=false restart_jenkins=false"
```

#### シードジョブのカスタマイズ

シードジョブは、Gitリポジトリ内のJenkinsfileを実行して他のすべてのJenkinsジョブを管理します。以下の変数でカスタマイズ可能です：

```bash
# カスタムGitリポジトリとブランチを指定してシードジョブを作成
ansible-playbook playbooks/jenkins/deploy/deploy_jenkins_application.yml \
  -e "env=dev" \
  -e "jenkins_jobs_repo=https://github.com/myorg/jenkins-jobs.git" \
  -e "jenkins_jobs_branch=develop" \
  -e "jenkins_jobs_jenkinsfile=pipelines/seed-job/Jenkinsfile"
```

## ブートストラップ環境の管理

### インスタンスの再作成

ブートストラップインスタンスを再作成する場合、CloudFormationスタックの`InstanceVersion`パラメータを更新します：

```bash
# CloudFormation出力の RecreateInstanceCommand を使用
aws cloudformation update-stack --stack-name bootstrap-iac-environment \
  --use-previous-template \
  --parameters ParameterKey=InstanceVersion,ParameterValue=$(date +%s) \
  --capabilities CAPABILITY_NAMED_IAM
```

再作成後も以下の情報は保持されます：
- Pulumi S3バケットとその内容
- SSMパラメータストア内の設定（GitHub SSHキー、Pulumiパスフレーズなど）
- VPCやセキュリティグループなどのネットワーク設定

### ブートストラップ環境の完全削除

ブートストラップ環境を完全に削除する場合：

```bash
# CloudFormationスタックの削除
aws cloudformation delete-stack --stack-name bootstrap-iac-environment

# 注意: これにより以下が削除されます：
# - EC2インスタンス
# - VPCとネットワーク関連リソース
# - Pulumi S3バケット（データも含む）
# - SSMパラメータ
# - IAMロールとポリシー
```

## インフラストラクチャの削除

構築したJenkinsインフラストラクチャを削除する場合は、以下のコマンドを使用します：

### 全体の削除

```bash
# 削除の確認（ドライラン）
ansible-playbook playbooks/jenkins/jenkins_teardown_pipeline.yml -e "env=dev"

# 実際に削除を実行
ansible-playbook playbooks/jenkins/jenkins_teardown_pipeline.yml -e "env=dev confirm=true"

# Pulumiスタックも含めて完全に削除
ansible-playbook playbooks/jenkins/jenkins_teardown_pipeline.yml -e "env=dev confirm=true remove_stacks=true"
```

### 特定コンポーネントの削除

```bash
# ネットワークとセキュリティグループを残して他を削除
ansible-playbook playbooks/jenkins/jenkins_teardown_pipeline.yml \
  -e "env=dev confirm=true destroy_network=false destroy_security=false"

# エージェントとコントローラーのみ削除
ansible-playbook playbooks/jenkins/jenkins_teardown_pipeline.yml \
  -e "env=dev confirm=true destroy_config=false destroy_loadbalancer=false destroy_storage=false destroy_security=false destroy_network=false"
```

**注意**: 削除操作は破壊的な操作です。以下の点に注意してください：
- 必ず `confirm=true` の指定が必要です
- 環境名 (`env`) を正しく指定してください
- EFSに保存されているJenkinsデータも削除されます
- 削除前に重要なデータのバックアップを取ることを推奨します

## インフラストラクチャの構成

このリポジトリは以下のAWSリソースを設定します：

- VPC、サブネット、ルートテーブル、セキュリティグループなどのネットワークリソース
- Jenkinsコントローラー用のEC2インスタンス（ブルー/グリーン環境）
- Jenkinsエージェント用のEC2 SpotFleet（自動スケーリング対応）
- Jenkinsデータ永続化のためのEFSファイルシステム
- ブルーグリーンデプロイ用のALB（Application Load Balancer）
- Jenkins関連リソースのIAMロールとポリシー
- アプリケーション設定管理用のSSMドキュメントとパラメータ

### ディレクトリ構造

```
infrastructure-as-code/
├─ ansible/                    # Ansible設定とプレイブック
│  ├─ inventory/              # インベントリと変数定義
│  ├─ playbooks/              # 各種プレイブック
│  │  ├─ jenkins/             # Jenkins関連プレイブック
│  │  │  ├─ deploy/          # デプロイ用
│  │  │  ├─ remove/          # 削除用
│  │  │  ├─ misc/            # その他（更新等）
│  │  │  ├─ jenkins_setup_pipeline.yml    # セットアップパイプライン
│  │  │  └─ jenkins_teardown_pipeline.yml # 削除パイプライン
│  │  └─ lambda/              # Lambda関連プレイブック
│  └─ roles/                  # Ansibleロール
│      ├─ aws_setup/          # AWS環境設定
│      ├─ pulumi_helper/      # Pulumi操作ヘルパー
│      ├─ jenkins_*/          # Jenkins関連（network, controller, agent等）
│      └─ lambda_*/           # Lambda関連（IP管理、API Gateway等）
│
├─ bootstrap/                  # ブートストラップ環境構築
│  ├─ cfn-bootstrap-template.yaml  # CloudFormationテンプレート
│  └─ setup-bootstrap.sh           # セットアップスクリプト
│
├─ jenkins/                    # Jenkins設定とジョブ定義
│  └─ jobs/                    # Jenkinsジョブ定義
│      ├─ dsl/                 # Job DSL定義（フォルダ構造等）
│      ├─ pipeline/            # パイプラインジョブ（Jenkinsfile）
│      └─ shared/              # 共有ライブラリ
│
├─ pulumi/                     # Pulumiインフラコード
│  ├─ jenkins-*/               # Jenkinsインフラスタック
│  └─ lambda-*/                # Lambdaインフラスタック
│
├─ scripts/                    # ユーティリティスクリプト
│  ├─ aws/                     # AWS操作スクリプト
│  └─ jenkins/                 # Jenkins設定スクリプト
│      ├─ casc/                # Configuration as Code設定
│      ├─ groovy/              # Groovy初期化スクリプト
│      ├─ jobs/                # ジョブXML定義
│      └─ shell/               # シェルスクリプト
│
└─ docs/                       # ドキュメント
```

### 主要ディレクトリの説明

- **ansible/**: Ansibleによる自動化設定。プレイブックでインフラの構築・削除・設定を管理
- **bootstrap/**: EC2踏み台サーバーの初期構築用CloudFormationとセットアップスクリプト
- **jenkins/**: Jenkinsジョブ定義とパイプライン。Job DSLとJenkinsfileによるジョブ管理
- **pulumi/**: インフラストラクチャのコード。各コンポーネントを独立したスタックとして管理
- **scripts/**: 各種ユーティリティスクリプト。AWS操作、Jenkins設定、初期化処理など

### 主な機能

- **段階的デプロイ**: Ansibleを使用して各コンポーネントを順番にデプロイ
- **段階的削除**: 依存関係を考慮した安全な削除処理
- **モジュール分割**: 各インフラコンポーネントを独立したPulumiスタックとして管理
- **ブルー/グリーンデプロイメント**: Jenkinsの更新を無停止で行えるデュアル環境
- **自動スケーリングエージェント**: EC2 SpotFleetによるコスト効率の高いJenkinsエージェント
- **リカバリーモード**: 管理者アカウントロックアウト時などの緊急アクセス用モード
- **データ永続性**: EFSによるJenkinsデータの永続化と高可用性の確保
- **アプリケーション設定管理**: Jenkinsバージョン更新、プラグイン管理、再起動処理の自動化
- **Jenkins CLIユーザー管理**: APIトークンを使用したCLIアクセスの自動設定
- **シードジョブによるジョブ管理**: Infrastructure as Codeによるジョブの自動作成・更新・削除

### Jenkins環境構築後の管理機能

`deploy_jenkins_application.yml` プレイブックを使用して、以下の管理タスクを実行できます：

1. **Jenkinsバージョン更新**
   - 最新バージョンまたは特定バージョンへの安全なアップグレード
   - 自動バックアップとロールバック機能

2. **プラグイン管理**
   - `install-plugins.groovy`スクリプトによる一括インストール・更新
   - プラグイン依存関係の自動解決

3. **CLIユーザーとクレデンシャル管理**
   - `cli-user`の自動作成
   - APIトークンの生成とJenkinsクレデンシャルストアへの保存
   - クレデンシャルID: `cli-user-token`として利用可能

4. **シードジョブ管理**
   - Gitリポジトリからジョブ定義を取得するパイプラインジョブの作成
   - Job DSLを使用したジョブのライフサイクル管理
   - ジョブ定義の変更を検知して自動的に反映

5. **サービス管理**
   - Jenkinsの安全な再起動
   - 起動確認とヘルスチェック

## トラブルシューティング

- **EC2インスタンス起動後の初期化エラー**: 
  - `sudo less +F /var/log/cloud-init-output.log`でuser data実行ログを確認
  - `Bootstrap setup complete!`が表示されていない場合は、エラー内容を確認
  - よくあるエラー：インターネット接続不可、IAMロール権限不足
- **Pulumiデプロイエラー**: `pulumi logs`でエラー詳細を確認
- **Ansibleエラー**: `-vvv`オプションを追加して詳細なログを確認（例: `ansible-playbook -vvv playbooks/jenkins_setup_pipeline.yml`）
- **AWS認証エラー**: `source scripts/aws/setup-aws-credentials.sh`を実行して認証情報を更新
- **Pulumiバックエンドエラー**: 
  - S3バックエンド使用時: 環境変数`PULUMI_CONFIG_PASSPHRASE`が設定されているか確認
    ```bash
    # パスフレーズが設定されているか確認
    echo $PULUMI_CONFIG_PASSPHRASE
    
    # 再設定が必要な場合
    export PULUMI_CONFIG_PASSPHRASE="your-secure-passphrase"
    
    # S3バケットの存在確認
    aws s3 ls | grep pulumi-state
    ```
  - Pulumi Cloud使用時: 環境変数`PULUMI_ACCESS_TOKEN`が正しく設定されているか確認
    ```bash
    # トークンが設定されているか確認
    echo $PULUMI_ACCESS_TOKEN
    
    # 再設定が必要な場合
    export PULUMI_ACCESS_TOKEN="pul-YOUR_ACCESS_TOKEN"
    ```
- **Jenkinsへのアクセス問題**: セキュリティグループの設定を確認
- **EFSマウント問題**: マウントターゲットの可用性を確認
- **削除時のリソース依存関係エラー**: 削除順序が正しいか確認（ネットワークは最後に削除）
- **Jenkinsバージョン更新失敗**: `/var/log/jenkins-update-version.log`を確認
- **プラグインインストール失敗**: Jenkins管理画面のシステムログを確認
- **CLIユーザー作成失敗**: `/var/log/jenkins/jenkins.log`でGroovyスクリプトの実行ログを確認
- **シードジョブ作成失敗**: 
  - Pipeline pluginがインストールされているか確認
  - `/var/log/jenkins/jenkins.log`でエラーを確認
  - Gitリポジトリへのアクセス権限を確認

## 共有パラメータの確認と修正

共有パラメータファイル（`all.yml`）が適切に設定されていることを確認してください。パラメータを変更する場合は以下の手順で行います：

```bash
# パラメータファイルを編集
vi ansible/inventory/group_vars/all.yml

# エディタで必要な変更を行った後、構文をチェック
ansible-playbook playbooks/jenkins/jenkins_setup_pipeline.yml -e "env=dev" --syntax-check

# 変更を適用（コミットする前にチェックモードで実行）
ansible-playbook playbooks/jenkins/jenkins_setup_pipeline.yml -e "env=dev" --check
```

## 注意事項

- 本番環境では適切なセキュリティ設定を行ってください
- AdministratorAccess権限は開発段階のみに使用し、本番環境では最小権限原則に従ってください
- バックアップ戦略の実装を忘れずに行ってください
- AWS認証情報は定期的に更新が必要です。セッションが切れた場合は`source scripts/aws/setup-aws-credentials.sh`を実行してください
- Pulumiアクセストークンは安全に管理してください。環境変数として設定する場合は、他のユーザーに見えないように注意してください
- **削除操作は取り消せません**。本番環境での削除操作は特に注意して実行してください
- Jenkinsバージョン更新前には必ずバックアップを取得してください
- シードジョブで管理されるジョブは、手動で変更しても次回シードジョブ実行時に上書きされます

## 拡張方法

リポジトリ構造は以下のように拡張可能です：

1. 新しいコンポーネントの追加:
```
pulumi/
  ├─jenkins-network/          # 既存のネットワークスタック
  ├─jenkins-security/         # 既存のセキュリティスタック
  ├─jenkins-application/      # 既存のアプリケーション設定スタック
  ├─monitoring/               # 新しいモニタリングスタック
  └─database/                 # 新しいデータベーススタック
```

2. 新しいAnsibleプレイブックの追加:
```
ansible/playbooks/jenkins/
  ├─jenkins_setup_pipeline.yml      # 既存のメインパイプライン
  ├─jenkins_teardown_pipeline.yml   # 既存の削除パイプライン
  ├─deploy/
  │  ├─deploy_jenkins_network.yml      # 既存のネットワークデプロイ
  │  ├─deploy_jenkins_application.yml  # 既存のアプリケーション設定
  │  └─deploy_monitoring.yml           # 新しいモニタリングデプロイ
  └─remove/
     ├─remove_jenkins_network.yml      # ネットワーク削除
     └─remove_monitoring.yml           # モニタリング削除
```

3. 新しいロールの追加時は、必ず`deploy.yml`と`destroy.yml`の両方を実装してください
