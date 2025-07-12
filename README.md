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
    - スタック名: bootstrap-environment
    - パラメータ
        - `KeyName`: 先ほど作成したEC2キーペア名（例：`bootstrap-environment-key`）
        - `InstanceType`: インスタンスタイプ（デフォルト: t4g.small）
        - `AllowedIP`: SSHアクセスを許可するIPアドレス範囲（セキュリティのため自分のIPアドレスに制限することを推奨）

3. スタックが作成完了したら、出力タブから以下の情報を確認：
    - `BootstrapPublicIP`: 踏み台サーバーのパブリックIPアドレス
    - `PulumiStateBucketName`: Pulumiのステート管理用S3バケット名

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
   - GitHubアクセス用のSSHキー生成（必要な場合）
   - Node.js, AWS CLI, Pulumi, Dockerなどの必要なツールのインストール
   - AWS認証情報の設定

### 4. Pulumiアクセストークンの設定

Jenkinsインフラのデプロイ前に、Pulumiのアクセストークンを設定する必要があります：

1. [Pulumi Console](https://app.pulumi.com/account/tokens)からアクセストークンを取得
2. 以下のコマンドで環境変数を設定：

   ```bash
   export PULUMI_ACCESS_TOKEN="pul-YOUR_ACCESS_TOKEN"
   ```

   Ansible実行時にこの環境変数を使って自動的にPulumiログインが行われます。

### 5. Jenkinsインフラの段階的デプロイ

環境準備ができたら、以下のコマンドでインフラをデプロイします：

```bash
# infrastructure-as-codeディレクトリに移動
cd ~/infrastructure-as-code

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

### 6. Jenkins環境構築後の設定管理

Jenkins環境が構築された後、アプリケーションレベルの設定を管理できます：

```bash
# Jenkinsのバージョン更新、プラグインインストール、CLIユーザー作成、シードジョブ作成、再起動を実行
ansible-playbook playbooks/deploy_jenkins_application.yml -e "env=dev"

# Jenkinsバージョンのみ更新（プラグインインストールはスキップ）
ansible-playbook playbooks/deploy_jenkins_application.yml -e "env=dev version=2.426.1 plugins=false"

# プラグインのみインストール（Gitリポジトリ更新はスキップ）
ansible-playbook playbooks/deploy_jenkins_application.yml -e "env=dev update_git=false plugins=true restart=false"

# シードジョブのみ作成（他の設定はスキップ）
ansible-playbook playbooks/deploy_jenkins_application.yml -e "env=dev jenkins_version=latest install_plugins=false setup_cli_user=false restart_jenkins=false"
```

#### シードジョブのカスタマイズ

シードジョブは、Gitリポジトリ内のJenkinsfileを実行して他のすべてのJenkinsジョブを管理します。以下の変数でカスタマイズ可能です：

```bash
# カスタムGitリポジトリとブランチを指定してシードジョブを作成
ansible-playbook playbooks/deploy_jenkins_application.yml \
  -e "env=dev" \
  -e "jenkins_jobs_repo=https://github.com/myorg/jenkins-jobs.git" \
  -e "jenkins_jobs_branch=develop" \
  -e "jenkins_jobs_jenkinsfile=pipelines/seed-job/Jenkinsfile"
```

## インフラストラクチャの削除

構築したJenkinsインフラストラクチャを削除する場合は、以下のコマンドを使用します：

### 全体の削除

```bash
# 削除の確認（ドライラン）
ansible-playbook playbooks/jenkins_teardown_pipeline.yml -e "env=dev"

# 実際に削除を実行
ansible-playbook playbooks/jenkins_teardown_pipeline.yml -e "env=dev confirm=true"

# Pulumiスタックも含めて完全に削除
ansible-playbook playbooks/jenkins_teardown_pipeline.yml -e "env=dev confirm=true remove_stacks=true"
```

### 特定コンポーネントの削除

```bash
# ネットワークとセキュリティグループを残して他を削除
ansible-playbook playbooks/jenkins_teardown_pipeline.yml \
  -e "env=dev confirm=true tear_network=false tear_security=false"

# エージェントとコントローラーのみ削除
ansible-playbook playbooks/jenkins_teardown_pipeline.yml \
  -e "env=dev confirm=true tear_config=false tear_loadbalancer=false tear_storage=false tear_security=false tear_network=false"
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
│  ├─ playbooks/              # 各種プレイブック（構築・削除・設定）
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
- **Pulumiログインエラー**: 環境変数`PULUMI_ACCESS_TOKEN`が正しく設定されているか確認
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
ansible-playbook playbooks/jenkins_setup_pipeline.yml -e "env=dev" --syntax-check

# 変更を適用（コミットする前にチェックモードで実行）
ansible-playbook playbooks/jenkins_setup_pipeline.yml -e "env=dev" --check
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
ansible/playbooks/
  ├─jenkins_setup_pipeline.yml      # 既存のメインパイプライン
  ├─jenkins_teardown_pipeline.yml   # 既存の削除パイプライン
  ├─deploy_jenkins_network.yml      # 既存のネットワークデプロイ
  ├─deploy_jenkins_application.yml  # 既存のアプリケーション設定
  └─deploy_monitoring.yml           # 新しいモニタリングデプロイ
```

3. 新しいロールの追加時は、必ず`deploy.yml`と`destroy.yml`の両方を実装してください
