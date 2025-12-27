# インフラストラクチャの構成

> 📖 **親ドキュメント**: [README.md](../../README.md)

## 概要

Jenkins基盤で利用するAWSリソース、リポジトリのディレクトリ構造、主要機能と管理ポイントをまとめています。

このリポジトリは以下のAWSリソースを設定します：

- VPC、サブネット、ルートテーブル、セキュリティグループなどのネットワークリソース
- Jenkinsコントローラー用のEC2インスタンス（ブルー/グリーン環境）
- Jenkinsエージェント用のEC2 SpotFleet（自動スケーリング対応）
- Jenkinsエージェント用のECS Fargateクラスタ、ECRリポジトリ、Task Definition、CloudWatch Logs
- Jenkinsエージェント用のカスタムAMI（EC2 Image Builder）
- Jenkinsデータ永続化のためのEFSファイルシステム
- ブルーグリーンデプロイ用のALB（Application Load Balancer）
- Jenkins関連リソースのIAMロールとポリシー
- アプリケーション設定管理用のSSMドキュメントとパラメータ

## ディレクトリ構造

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
│  │  ├─ jenkins-agent/        # Jenkins Agent SpotFleet
│  │  └─ jenkins-agent-ami/    # Jenkins Agent AMI Builder
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
├─ docker/                      # Jenkinsエージェントコンテナ定義
│  └─ jenkins-agent-ecs/       # ECS Fargateエージェントイメージ
│      ├─ Dockerfile           # ECS専用Jenkinsエージェントイメージ
│      └─ entrypoint.sh        # amazon-ecsプラグイン互換のエントリーポイント

└─ docs/                       # ドキュメント
```

## 主要ディレクトリの説明

- **ansible/**: Ansibleによる自動化設定。プレイブックでインフラの構築・削除・設定を管理
- **bootstrap/**: EC2踏み台サーバーの初期構築用CloudFormationとセットアップスクリプト
- **jenkins/**: Jenkinsジョブ定義とパイプライン。Job DSLとJenkinsfileによるジョブ管理
- **pulumi/**: インフラストラクチャのコード。各コンポーネントを独立したスタックとして管理
- **scripts/**: 各種ユーティリティスクリプト。AWS操作、Jenkins設定、初期化処理など
- **docker/**: ECS Fargateエージェントイメージの定義。`docker/jenkins-agent-ecs/`でDockerfile・entrypoint.shを管理

## 主な機能

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

## Jenkinsエージェント構成

本番環境では、Jenkins コントローラーから接続するエージェントを SpotFleet（EC2）と ECS Fargate の双方で運用しています。SpotFleet は既存のバッチ/長時間ジョブに対して安定したキャパシティを提供し、ECS Fargate は短時間かつ高い並列性が求められるジョブを高速に処理します。どちらの構成も `pulumi/jenkins-agent/index.ts` 内で定義されたリソース群と SSM パラメータを通じて Jenkins に公開されます。

### SpotFleet vs ECS Fargate 比較

| 観点 | SpotFleet | ECS Fargate |
|------|-----------|-------------|
| コスト | スポットインスタンスによる低コスト | オンデマンド課金のためやや高価だが必要な分だけ課金 |
| 起動速度 | EC2 の起動を伴うため中程度 | コンテナ起動のため高速 |
| スケーラビリティ | 数百台まで拡張可能 | 数千タスクの並行実行が可能 |
| 管理負荷 | AMI と Launch Template の管理が必要 | コンテナ定義のみで運用 |
| リソース効率 | 固定サイズのインスタンス | 必要なリソースに応じたスケール |
| 適用場面 | 長時間バッチ処理やツールチェーン依存 | 短時間・並列処理、CI ファーストパーティタスク |

#### 使い分けの指針

- 長時間実行を前提にした大容量やレガシーツールチェーンは SpotFleet を維持
- 短時間かつスケールが必要なタスク、たとえば並列ビルド/テストは ECS Fargate エージェントへ切り替え
- Jenkins からは両方のエージェントを amazon-ecs プラグインと SpotFleet プラグインで個別に管理し、SSM パラメータ経由で接続情報を取得

## ECS Fargateエージェント詳細

`pulumi/jenkins-agent/index.ts` の 739 行以降では、ECS Fargate エージェント用の Cluster、ECR、Task Definition、IAM Role、CloudWatch Logs が定義され、各リソースは SSM パラメータとして Jenkins に提供されます。

### ECS Cluster

専用の ECS Cluster を作成し、Fargate タスクの実行環境を分離しています。クラスタ名・ARN は SSM パラメータ `/jenkins-infra/{environment}/agent/ecs-cluster-*` で公開され、amazon-ecs プラグインのクラスタ設定にそのまま流し込めるようにしています。

### ECR Repository

`docker/jenkins-agent-ecs` でビルドした Jenkins エージェントイメージは専用の ECR リポジトリに格納され、Fargate タスクはこのリポジトリからイメージを取得します。リポジトリ URL も SSM パラメータとして公開し、タスク定義の `image` フィールドへ埋め込みます。

### Task Definition

タスク定義では利用するコンテナの CPU/Mem、実行ロール（`ecs-task-role`）、実行時ロール（`ecs-execution-role`）、ログドライバ（CloudWatch Logs）、必要な環境変数・ボリュームなどを包括的に定義しています。定義の ARN は SSM パラメータ `/jenkins-infra/{environment}/agent/ecs-task-definition-arn` で管理され、Jenkins から amazon-ecs プラグイン経由で参照します。

### IAM Roles

Fargate タスクには Execution Role（ECR へのプル、CloudWatch へのログ送信）と Task Role（Jenkins 内での操作権限）の 2 つの IAM Role を割り当てています。Task Role は AdministratorAccess ポリシーを継承し、SpotFleet とは異なる最小権限の境界を維持しつつも必要なリソースへアクセスできるようにしています。

### CloudWatch Logs

タスクのコンテナログは CloudWatch Logs に送信し、Log Group 名も SSM パラメータ `/jenkins-infra/{environment}/agent/ecs-log-group-name` で管理しています。S3 やログフィルタは必要に応じて追加できますが、基本は Pulumi 定義内でリテンションとストリームポリシーを維持しています。

## docker/jenkins-agent-ecs

`docker/jenkins-agent-ecs` 以下には、ECS Fargate で動作する Jenkins エージェントコンテナの定義が集約されています。主なファイルは次の通りです：

- `Dockerfile`: Multi-stage build を採用し、OpenJDK、AWS CLI、Pulumi、Ansible、Jenkins Remoting など必要なツールを含む軽量イメージを構築します。ビルド後は不要ファイルを削ぎ落とし、最終ステージでは実行に必要なファイルのみを残します。
- `entrypoint.sh`: amazon-ecs プラグイン互換のエントリーポイントで、引数の変換や環境変数の整備、動作ログの出力を行います。古い形式の引数をサポートしつつ新しい ECS タスクからの実行も可能なように調整されています。

## ECSエージェント用SSMパラメータ

ECS エージェントに必要な接続情報は全て SSM Parameter Store で管理され、`/jenkins-infra/{environment}/agent/` プレフィックスに集約されています。SpotFleet で利用しているパラメータと同様に Pulumi の `pulumi/jenkins-agent/index.ts` から出力され、Jenkins の amazon-ecs プラグインや運用手順でそのまま参照されます。

| パラメータ名 | 説明 | 用途 |
|-------------|------|------|
| `/jenkins-infra/{environment}/agent/ecs-cluster-arn` | ECS Cluster ARN | amazon-ecs プラグインのクラスタ指定 |
| `/jenkins-infra/{environment}/agent/ecs-cluster-name` | ECS Cluster 名 | 管理者がクラスタを識別するため |
| `/jenkins-infra/{environment}/agent/ecs-task-definition-arn` | Task Definition ARN | Task Definition のリビジョンを Jenkins から指定 |
| `/jenkins-infra/{environment}/agent/ecr-repository-url` | ECR リポジトリ URL | ECS タスクの `image` フィールドに設定 |
| `/jenkins-infra/{environment}/agent/ecs-execution-role-arn` | ECS Execution Role ARN | ECR へのアクセスやログ送信権限 |
| `/jenkins-infra/{environment}/agent/ecs-task-role-arn` | ECS Task Role ARN | Jenkins 内処理用ロール（AdministratorAccess） |
| `/jenkins-infra/{environment}/agent/ecs-log-group-name` | CloudWatch Logs Group 名 | タスクログの送信先 |

## Jenkins環境構築後の管理機能

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

## 関連ドキュメント

- [Jenkinsインフラデプロイ](../operations/jenkins-deploy.md)
- [Jenkins環境運用管理](../operations/jenkins-management.md)
- [README.md](../../README.md)
