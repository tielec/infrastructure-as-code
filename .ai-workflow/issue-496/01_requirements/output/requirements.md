# 要件定義書: Issue #496

## EC2 Image BuilderでECS Fargate Agent Dockerイメージの自動ビルド

**作成日**: 2025-01-14
**Issue URL**: https://github.com/tielec/infrastructure-as-code/issues/496
**対応するPlanning Document**: `.ai-workflow/issue-496/00_planning/output/planning.md`

---

## 0. Planning Documentの確認

### 0.1 開発計画の全体像

Planning Documentでは、以下の戦略が策定されています：

- **実装戦略**: CREATE（新規Pulumiスタック `jenkins-agent-ecs-image/` を完全に新規作成）
- **テスト戦略**: INTEGRATION_ONLY（Pulumiリソースの統合テストが中心）
- **テストコード戦略**: CREATE_TEST（`tests/integration/ecs-image/` に新規テストを作成）
- **複雑度**: 中程度
- **見積もり工数**: 12〜16時間

### 0.2 主要リスク

1. EC2 Image Builder ContainerRecipeの機能制限（multi-stage build非対応の可能性）
2. entrypoint.shの取り扱い（Component YAMLでの対応が必要）
3. イメージビルド時間の長さ（30分〜1時間）によるデバッグサイクルの遅延

### 0.3 Planning Documentとの整合性

本要件定義書は、Planning Documentで策定された「CREATE」実装戦略に基づき、新規Pulumiスタックの詳細な機能要件と受け入れ基準を定義します。

---

## 1. 概要

### 1.1 背景

現在、Jenkins CI/CDインフラストラクチャでは、EC2ベースのJenkins AgentとECS Fargateベースのエージェントの2種類が利用可能です。EC2ベースのエージェント用カスタムAMIは、既存の`jenkins-agent-ami`スタックでEC2 Image Builderを使用して自動ビルドされています。

一方、ECS Fargateエージェント用のDockerイメージ（`docker/jenkins-agent-ecs/Dockerfile`）は、手作業でビルドしECRへプッシュしている状態です。これにより以下の問題が発生しています：

- ビルドプロセスが属人化し、チーム間での一貫性が失われている
- 手作業によるヒューマンエラーのリスク
- バージョン管理やビルド履歴の追跡が困難
- 監査ログの欠如

### 1.2 目的

EC2 Image BuilderのContainer Image機能を活用し、ECS Fargate Agent用Dockerイメージのビルドを自動化します。これにより、AMIビルドと統一されたプロセスでコンテナイメージを管理できるようになります。

### 1.3 ビジネス価値

| 項目 | 価値 |
|------|------|
| プロセス統一 | AMIとコンテナイメージで統一されたビルドプロセスを実現 |
| バージョン管理 | 自動バージョニングとタグ付けによる追跡性向上 |
| 品質向上 | 手作業によるミス削減、再現性のあるビルド |
| 監査対応 | ビルド履歴・ログの自動記録によるコンプライアンス強化 |
| 運用効率 | 手動作業の削減によるDevOpsチームの負荷軽減 |

### 1.4 技術的価値

- 既存の`jenkins-agent-ami`スタックのパターンを踏襲し、コード資産を再利用
- Infrastructure as Codeによるビルドプロセスの宣言的管理
- SSMパラメータストアを活用した設定の一元管理

---

## 2. 機能要件

### 2.1 Pulumiスタックの作成

| ID | 要件 | 優先度 | 詳細 |
|----|------|--------|------|
| FR-01 | 新規Pulumiスタック `jenkins-agent-ecs-image` の作成 | 高 | `pulumi/jenkins-agent-ecs-image/` ディレクトリを作成し、Pulumiプロジェクト（`Pulumi.yaml`, `package.json`, `tsconfig.json`, `index.ts`）を構成する |
| FR-02 | 既存の`jenkins-agent-ami`スタックのパターン踏襲 | 高 | IAMロール、バージョン管理、SSMパラメータ出力のパターンを踏襲する |

### 2.2 EC2 Image Builder Componentの作成

| ID | 要件 | 優先度 | 詳細 |
|----|------|--------|------|
| FR-03 | Component YAML（`component.yml`）の作成 | 高 | 既存Dockerfile（`docker/jenkins-agent-ecs/Dockerfile`）の内容をImage Builder Component形式に変換する |
| FR-04 | ツールインストールの実装 | 高 | Git, Java 21, Node.js 20, AWS CLI, Pulumi, Ansible, Docker CLIのインストールをComponentで実装する |
| FR-05 | Jenkins remotingエージェントJARの配置 | 高 | Jenkins remoting JAR（agent.jar）をダウンロードし適切な場所に配置する |
| FR-06 | entrypoint.shの配置と権限設定 | 高 | `docker/jenkins-agent-ecs/entrypoint.sh` をコンテナイメージ内にコピーし、実行権限を設定する |
| FR-07 | jenkinsユーザーの作成 | 高 | UID/GID 1000でjenkinsユーザーを作成し、必要なディレクトリを設定する |
| FR-08 | validateフェーズの実装 | 中 | 必要なツール（java, git, node, npm, python3, aws, pulumi, ansible）の存在とバージョンを検証する |

### 2.3 ContainerRecipeの定義

| ID | 要件 | 優先度 | 詳細 |
|----|------|--------|------|
| FR-09 | ContainerRecipeリソースの作成 | 高 | ベースイメージ `amazoncorretto:21-al2023` を使用し、Componentを適用するContainerRecipeを定義する |
| FR-10 | Dockerfileテンプレートの構成 | 高 | ENTRYPOINTとWorkingDirectoryを適切に設定するDockerfileテンプレートを定義する |
| FR-11 | バージョン管理 | 高 | `1.YYMMDD.secondsOfDay` 形式のセマンティックバージョニングを実装する |

### 2.4 InfrastructureConfigurationの定義

| ID | 要件 | 優先度 | 詳細 |
|----|------|--------|------|
| FR-12 | InfrastructureConfigurationの作成 | 高 | ビルド用EC2インスタンスの設定（インスタンスタイプ、サブネット、セキュリティグループ）を定義する |
| FR-13 | IAMロールとインスタンスプロファイルの作成 | 高 | Image Builder実行用のIAMロールとインスタンスプロファイルを作成する |

### 2.5 DistributionConfigurationの定義

| ID | 要件 | 優先度 | 詳細 |
|----|------|--------|------|
| FR-14 | DistributionConfigurationの作成 | 高 | 既存ECRリポジトリ（`jenkins-infra-agent-ecs-{env}`）への配布設定を定義する |
| FR-15 | イメージタグの設定 | 高 | `latest` および `{{imagebuilder:buildDate}}` タグを設定する |

### 2.6 ImagePipelineの作成

| ID | 要件 | 優先度 | 詳細 |
|----|------|--------|------|
| FR-16 | ImagePipelineリソースの作成 | 高 | 手動トリガーまたはスケジュール実行可能なパイプラインを作成する |
| FR-17 | テスト設定 | 中 | イメージテスト（起動テスト、ツール存在確認）の設定を行う |

### 2.7 SSMパラメータ出力

| ID | 要件 | 優先度 | 詳細 |
|----|------|--------|------|
| FR-18 | パイプラインARNの保存 | 高 | `/jenkins-infra/{env}/agent-ecs-image/pipeline-arn` にパイプラインARNを保存する |
| FR-19 | コンポーネントバージョンの保存 | 中 | `/jenkins-infra/{env}/agent-ecs-image/component-version` にバージョンを保存する |
| FR-20 | レシピバージョンの保存 | 中 | `/jenkins-infra/{env}/agent-ecs-image/recipe-version` にバージョンを保存する |

### 2.8 Ansibleプレイブック・ロールの作成

| ID | 要件 | 優先度 | 詳細 |
|----|------|--------|------|
| FR-21 | `jenkins_agent_ecs_image` ロールの作成 | 高 | `ansible/roles/jenkins_agent_ecs_image/` にロールを作成する |
| FR-22 | デプロイ用プレイブックの作成 | 高 | `ansible/playbooks/jenkins/deploy/deploy_jenkins_agent_ecs_image.yml` を作成する |
| FR-23 | 削除用プレイブックの作成 | 中 | `ansible/playbooks/jenkins/remove/remove_jenkins_agent_ecs_image.yml` を作成する |
| FR-24 | meta/main.yml依存関係の定義 | 高 | `aws_setup`, `aws_cli_helper`, `pulumi_helper`, `ssm_parameter_store` への依存を定義する |

---

## 3. 非機能要件

### 3.1 パフォーマンス要件

| ID | 要件 | 基準 |
|----|------|------|
| NFR-01 | イメージビルド時間 | 60分以内にビルドが完了すること |
| NFR-02 | Pulumi preview実行時間 | 30秒以内にプレビューが完了すること |
| NFR-03 | Pulumi up実行時間 | 5分以内にデプロイが完了すること（初回デプロイ時を除く） |

### 3.2 セキュリティ要件

| ID | 要件 | 基準 |
|----|------|------|
| NFR-04 | IAM最小権限 | Image Builder実行に必要な最小限の権限のみを付与すること |
| NFR-05 | ECRアクセス制御 | 既存のECRリポジトリのプッシュ権限のみを付与すること |
| NFR-06 | ビルドインスタンスのネットワーク | パブリックサブネット内で実行し、ビルド完了後に自動削除されること |
| NFR-07 | 秘密情報の管理 | ハードコーディングされた秘密情報を含まないこと |

### 3.3 可用性・信頼性要件

| ID | 要件 | 基準 |
|----|------|------|
| NFR-08 | 冪等性 | 複数回のPulumi up実行で同じ結果が得られること |
| NFR-09 | エラー時の自動リカバリ | ビルド失敗時にインスタンスが自動終了されること（terminateInstanceOnFailure: true） |
| NFR-10 | 既存リソースとの独立性 | 既存の`jenkins-agent`スタックに影響を与えないこと |

### 3.4 保守性・拡張性要件

| ID | 要件 | 基準 |
|----|------|------|
| NFR-11 | コード規約 | `pulumi/CONTRIBUTION.md` のコーディング規約に準拠すること |
| NFR-12 | ドキュメント | `pulumi/README.md` に新スタックの説明を追加すること |
| NFR-13 | 既存パターンの踏襲 | `jenkins-agent-ami`スタックのコード構造・命名規則を踏襲すること |
| NFR-14 | Dockerfileとの同期 | 既存Dockerfileの機能を可能な限り維持すること |

---

## 4. 制約事項

### 4.1 技術的制約

| ID | 制約 | 詳細 |
|----|------|------|
| TC-01 | Multi-stage build非対応 | EC2 Image Builder ContainerRecipeはDockerfileのmulti-stage buildをサポートしない可能性がある。単一ステージでのビルドを検討する |
| TC-02 | ベースイメージの制限 | Image Builder親イメージとして使用できるイメージに制限がある可能性がある |
| TC-03 | ARG命令の制限 | Dockerfile内のARG命令がComponent YAMLで直接サポートされない可能性がある |
| TC-04 | 既存ECRリポジトリの使用 | 新規ECRリポジトリは作成せず、`jenkins-agent`スタックで作成済みのリポジトリを使用する |

### 4.2 リソース制約

| ID | 制約 | 詳細 |
|----|------|------|
| RC-01 | ビルド時間 | イメージビルドに30分〜1時間かかるため、デバッグサイクルが長くなる |
| RC-02 | AWSコスト | ビルド用EC2インスタンスの使用料が発生する（ビルド時のみ） |

### 4.3 ポリシー制約

| ID | 制約 | 詳細 |
|----|------|------|
| PC-01 | SSM Single Source of Truth | すべての設定値はSSMパラメータストアから取得する（Pulumi ConfigやStackReference使用禁止） |
| PC-02 | コーディング規約 | `CONTRIBUTION.md` および `pulumi/CONTRIBUTION.md` に従う |
| PC-03 | コメント言語 | ソースコード内のコメントは日本語で記述する |

---

## 5. 前提条件

### 5.1 システム環境

| ID | 前提条件 | 詳細 |
|----|---------|------|
| PR-01 | AWS環境 | ap-northeast-1リージョンでのデプロイを想定 |
| PR-02 | Pulumi環境 | Pulumi CLI 3.0以上がインストールされていること |
| PR-03 | Node.js環境 | Node.js 18以上がインストールされていること |
| PR-04 | S3バックエンド | Pulumiの状態管理にS3バックエンドを使用していること |

### 5.2 依存コンポーネント（デプロイ順序で必須）

| ID | 依存スタック | 取得するSSMパラメータ |
|----|-------------|----------------------|
| PR-05 | `jenkins-ssm-init` | `/jenkins-infra/{env}/config/project-name` |
| PR-06 | `jenkins-network` | `/jenkins-infra/{env}/network/vpc-id`, `/jenkins-infra/{env}/network/public-subnet-a-id` |
| PR-07 | `jenkins-security` | `/jenkins-infra/{env}/security/jenkins-agent-sg-id` |
| PR-08 | `jenkins-agent` | `/jenkins-infra/{env}/agent/ecr-repository-url`（既存ECRリポジトリ） |

### 5.3 既存リソースの活用

| ID | リソース | 詳細 |
|----|---------|------|
| PR-09 | ECRリポジトリ | `jenkins-agent`スタックで作成された `jenkins-infra-agent-ecs-{env}` を使用 |
| PR-10 | 参考実装 | `pulumi/jenkins-agent-ami/index.ts` を参考実装として使用 |
| PR-11 | 既存Dockerfile | `docker/jenkins-agent-ecs/Dockerfile` の機能をComponent YAMLに変換 |
| PR-12 | 既存entrypoint | `docker/jenkins-agent-ecs/entrypoint.sh` をそのまま使用 |

---

## 6. 受け入れ基準

### 6.1 Pulumiスタック作成（FR-01, FR-02）

**AC-01: Pulumiスタックの基本構造**
```gherkin
Given Pulumiスタック "jenkins-agent-ecs-image" が作成されている
When "cd pulumi/jenkins-agent-ecs-image && npm install && pulumi preview" を実行する
Then プレビューがエラーなく完了する
And 以下のリソースがプレビューに含まれる：
  | リソースタイプ | 個数 |
  | aws:imagebuilder:Component | 1 |
  | aws:imagebuilder:ContainerRecipe | 1 |
  | aws:imagebuilder:InfrastructureConfiguration | 1 |
  | aws:imagebuilder:DistributionConfiguration | 1 |
  | aws:imagebuilder:ImagePipeline | 1 |
  | aws:iam:Role | 1 |
  | aws:iam:InstanceProfile | 1 |
  | aws:ssm:Parameter | 3以上 |
```

### 6.2 Component YAML変換（FR-03〜FR-08）

**AC-02: ツールインストールの検証**
```gherkin
Given Component YAMLが適用されたコンテナイメージがビルドされている
When コンテナ内でツールのバージョン確認コマンドを実行する
Then 以下のコマンドがすべて成功する：
  | コマンド | 期待結果 |
  | java -version | Java 21が出力される |
  | git --version | Git 2.x以上 |
  | node --version | Node.js 20.x |
  | npm --version | npm 10.x以上 |
  | python3 --version | Python 3.x |
  | aws --version | AWS CLI v2.x |
  | pulumi version | Pulumi 3.x |
  | ansible --version | Ansible 2.x以上 |
```

**AC-03: entrypoint.shの配置**
```gherkin
Given Component YAMLが適用されたコンテナイメージがビルドされている
When コンテナ内で "/entrypoint.sh" を確認する
Then ファイルが存在する
And 実行権限（chmod +x）が設定されている
And jenkinsユーザーが所有者である
```

**AC-04: jenkinsユーザーの設定**
```gherkin
Given Component YAMLが適用されたコンテナイメージがビルドされている
When コンテナ内でjenkinsユーザー情報を確認する
Then UID=1000, GID=1000でjenkinsユーザーが存在する
And /home/jenkins ディレクトリが存在し、jenkinsユーザーが所有している
And /home/jenkins/.jenkins ディレクトリが存在する
```

### 6.3 ECR配布設定（FR-14, FR-15）

**AC-05: ECRイメージプッシュ**
```gherkin
Given ImagePipelineが実行されビルドが成功している
When ECRリポジトリの内容を確認する
Then 以下のタグを持つイメージが存在する：
  | タグ |
  | latest |
  | ビルド日付形式（例: 2025-01-14-12-30-00） |
And イメージサイズが1GB〜3GB程度である
```

### 6.4 SSMパラメータ出力（FR-18〜FR-20）

**AC-06: SSMパラメータの作成**
```gherkin
Given Pulumiスタックがデプロイされている
When SSMパラメータを確認する
Then 以下のパラメータが存在する：
  | パラメータ名 | 値の形式 |
  | /jenkins-infra/{env}/agent-ecs-image/pipeline-arn | arn:aws:imagebuilder:... |
  | /jenkins-infra/{env}/agent-ecs-image/component-version | 1.YYMMDD.SSSSS |
  | /jenkins-infra/{env}/agent-ecs-image/recipe-version | 1.YYMMDD.SSSSS |
```

### 6.5 Ansibleプレイブック（FR-21〜FR-24）

**AC-07: デプロイプレイブック実行**
```gherkin
Given 依存スタック（jenkins-network, jenkins-security, jenkins-agent）がデプロイ済みである
When "ansible-playbook playbooks/jenkins/deploy/deploy_jenkins_agent_ecs_image.yml -e 'env=dev'" を実行する
Then プレイブックがエラーなく完了する
And Pulumiスタックがデプロイされている
And SSMパラメータが作成されている
```

**AC-08: 削除プレイブック実行**
```gherkin
Given jenkins-agent-ecs-imageスタックがデプロイ済みである
When "ansible-playbook playbooks/jenkins/remove/remove_jenkins_agent_ecs_image.yml -e 'env=dev confirm=true'" を実行する
Then プレイブックがエラーなく完了する
And Pulumiリソースが削除されている
And SSMパラメータが削除されている
```

### 6.6 既存システムとの整合性

**AC-09: 既存スタックへの影響なし**
```gherkin
Given jenkins-agent-ecs-imageスタックをデプロイする
When jenkins-agentスタックのリソースを確認する
Then ECRリポジトリが変更されていない
And ECS Cluster、Task Definitionが変更されていない
And 既存のSSMパラメータが上書きされていない
```

**AC-10: Dockerfileとの機能一致**
```gherkin
Given Component YAMLから生成されたコンテナイメージがある
And 既存Dockerfileから生成されたコンテナイメージがある
When 両イメージのツールバージョンを比較する
Then 同一のツールが同一バージョンでインストールされている
  | ツール | バージョン |
  | Java | 21 |
  | Node.js | 20.x |
  | Pulumi | 最新 |
  | Ansible | 最新 |
  | AWS CLI | v2 |
```

---

## 7. スコープ外

### 7.1 明確にスコープ外とする事項

| ID | 事項 | 理由 |
|----|------|------|
| OOS-01 | ARM64アーキテクチャ対応 | 初期リリースではx86_64のみ。将来的に追加検討 |
| OOS-02 | 新規ECRリポジトリの作成 | 既存の`jenkins-agent`スタックで作成済みのECRを使用 |
| OOS-03 | ECS Task Definitionの更新 | イメージのビルドのみが対象。Task定義の更新は別Issue |
| OOS-04 | CI/CDパイプラインとの統合（自動トリガー） | 初期リリースでは手動トリガーのみ |
| OOS-05 | スケジュール実行の設定 | 必要に応じて後で追加 |
| OOS-06 | 既存Dockerfileの削除 | 参照用およびローカルテスト用として維持 |
| OOS-07 | マルチステージビルドの完全再現 | Image Builderの制限により単一ステージで実装 |

### 7.2 将来的な拡張候補

| ID | 候補 | 優先度 | 説明 |
|----|------|--------|------|
| FE-01 | ARM64サポート | 中 | Gravitonインスタンス対応のため |
| FE-02 | スケジュール実行 | 低 | 定期的なイメージ更新のため |
| FE-03 | Git pushトリガー | 中 | Dockerfileの変更検知と自動ビルド |
| FE-04 | SNS通知 | 低 | ビルド完了/失敗時の通知 |
| FE-05 | jenkins_setup_pipeline.ymlへの統合 | 中 | 全体デプロイフローへの組み込み |

---

## 8. 技術詳細（参考情報）

### 8.1 既存Dockerfileの分析

**ファイル**: `docker/jenkins-agent-ecs/Dockerfile`

**特徴**:
- Multi-stage build（builder + runtime）
- ベースイメージ: `amazoncorretto:21-al2023`
- 主要ツール: Git, Java 21, Node.js 20, AWS CLI v2, Pulumi, Ansible, Docker CLI
- Jenkins remoting JAR: `remoting-3206.vb_15dcf73f6a_9.jar`
- jenkinsユーザー: UID/GID 1000

**Image Builder変換時の考慮点**:
- Multi-stageをシングルステージに変換
- COPY --from=builder をExecuteBashでのダウンロード/インストールに変換
- ARG命令を環境変数または固定値に変換

### 8.2 entrypoint.shの分析

**ファイル**: `docker/jenkins-agent-ecs/entrypoint.sh`

**機能**:
- amazon-ecsプラグインからの引数形式（`-url <url> <secret> <name>`）を処理
- 新形式（`-url`, `-secret`, `-name`, `-webSocket`）に変換
- Jenkins remoting エージェントJARの実行

**Image Builder変換時の考慮点**:
- スクリプトファイルをそのままコンテナにコピー
- 実行権限（chmod +x）の設定
- ENTRYPOINTディレクティブでの指定

### 8.3 SSMパラメータ設計

**新規作成パラメータ（jenkins-agent-ecs-imageスタック）**:
```
/jenkins-infra/{env}/agent-ecs-image/pipeline-arn
/jenkins-infra/{env}/agent-ecs-image/component-version
/jenkins-infra/{env}/agent-ecs-image/recipe-version
```

**参照するパラメータ（他スタックから）**:
```
/jenkins-infra/{env}/config/project-name          (jenkins-ssm-init)
/jenkins-infra/{env}/network/vpc-id               (jenkins-network)
/jenkins-infra/{env}/network/public-subnet-a-id   (jenkins-network)
/jenkins-infra/{env}/security/jenkins-agent-sg-id (jenkins-security)
/jenkins-infra/{env}/agent/ecr-repository-url     (jenkins-agent)
```

---

## 9. 品質ゲートチェックリスト（Phase 1）

### 必須要件

- [x] **機能要件が明確に記載されている**
  - FR-01〜FR-24の24項目の機能要件を定義
  - 各要件に優先度（高/中）を付与

- [x] **受け入れ基準が定義されている**
  - AC-01〜AC-10の10項目の受け入れ基準を定義
  - Given-When-Then形式で検証可能な形で記述

- [x] **スコープが明確である**
  - スコープ外事項を7項目定義（OOS-01〜OOS-07）
  - 将来的な拡張候補を5項目定義（FE-01〜FE-05）

- [x] **論理的な矛盾がない**
  - 依存関係が明確に定義されている（PR-05〜PR-08）
  - 制約事項が技術的実現可能性と整合している
  - Planning Documentの戦略と整合している

---

## 10. 承認・レビュー

| 項目 | 状態 | 日付 | 担当者 |
|------|------|------|--------|
| 要件定義書作成 | 完了 | 2025-01-14 | - |
| クリティカルシンキングレビュー | 未実施 | - | - |
| 要件承認 | 未実施 | - | - |

---

*この要件定義書はIssue #496の実装に向けた詳細要件を定義しています。Phase 2（設計）では、この要件に基づいて具体的な設計ドキュメントを作成します。*
