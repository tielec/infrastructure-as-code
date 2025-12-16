# テストシナリオ: Issue #496

## EC2 Image BuilderでECS Fargate Agent Dockerイメージの自動ビルド

**作成日**: 2025-01-14
**Issue URL**: https://github.com/tielec/infrastructure-as-code/issues/496
**対応する設計書**: `.ai-workflow/issue-496/02_design/output/design.md`

---

## 1. テスト戦略サマリー

### 1.1 選択されたテスト戦略

**テスト戦略**: INTEGRATION_ONLY

**判断根拠**（設計書Phase 2より）:
- Pulumiスタックは主にAWSリソースのプロビジョニングを行う
- ユニットテストの対象となる複雑なビジネスロジックは存在しない
- 実際のAWSリソース（ECR、Image Builder）との統合確認が主なテスト対象
- BDDはエンドユーザー向け機能ではないため不要
- 既存の`tests/integration/ecs-fargate/`パターンに従う

### 1.2 テスト対象の範囲

| カテゴリ | テスト対象 |
|---------|-----------|
| Pulumiリソース | Component, ContainerRecipe, InfrastructureConfiguration, DistributionConfiguration, ImagePipeline |
| IAMリソース | Image Builder用IAMロール、インスタンスプロファイル |
| SSMパラメータ | pipeline-arn, component-version, recipe-version |
| 既存リソース統合 | ECRリポジトリ（jenkins-agentスタック所有）との連携 |
| Ansibleプレイブック | デプロイ/削除プレイブックの実行 |

### 1.3 テストの目的

1. **インフラ整合性**: Pulumiスタックが正常にデプロイされ、必要なAWSリソースが作成されることを検証
2. **リソース連携**: 既存のネットワーク/セキュリティ/ECRリソースとの統合が正常に機能することを検証
3. **設定の正確性**: SSMパラメータが正しい値で保存されることを検証
4. **運用可能性**: Ansibleプレイブックによるデプロイ/削除が正常に機能することを検証

---

## 2. 統合テストシナリオ

### 2.1 Pulumiリソース検証テスト

#### INT-ECS-IMG-001: SSMパラメータの存在確認

**目的**: jenkins-agent-ecs-imageスタックがデプロイされた後、必要なSSMパラメータが作成されていることを検証

**前提条件**:
- jenkins-agent-ecs-imageスタックがデプロイ済み
- AWS CLIが設定済み
- jqがインストール済み

**テスト手順**:
1. 以下のSSMパラメータの存在を確認
   - `/jenkins-infra/{env}/agent-ecs-image/pipeline-arn`
   - `/jenkins-infra/{env}/agent-ecs-image/component-version`
   - `/jenkins-infra/{env}/agent-ecs-image/recipe-version`
2. 各パラメータの値が空でないことを確認
3. パラメータの形式を検証
   - pipeline-arn: `arn:aws:imagebuilder:` で始まる
   - component-version: `1.YYMMDD.SSSSS` 形式
   - recipe-version: `1.YYMMDD.SSSSS` 形式

**期待結果**:
- すべてのパラメータが存在する
- 各パラメータの値が期待される形式である

**確認項目**:
- [ ] pipeline-arnパラメータが存在し、ARN形式である
- [ ] component-versionパラメータが存在し、バージョン形式である
- [ ] recipe-versionパラメータが存在し、バージョン形式である

---

#### INT-ECS-IMG-002: Image Builderパイプラインのステータス確認

**目的**: Image Builderパイプラインが正常に作成され、ENABLED状態であることを検証

**前提条件**:
- INT-ECS-IMG-001が成功
- pipeline-arnがSSMパラメータから取得可能

**テスト手順**:
1. SSMパラメータからpipeline-arnを取得
2. `aws imagebuilder get-image-pipeline`でパイプライン情報を取得
3. パイプラインのステータスを確認

**期待結果**:
- パイプラインが存在する
- ステータスが`ENABLED`である

**確認項目**:
- [ ] パイプラインが取得可能
- [ ] status = "ENABLED"

---

#### INT-ECS-IMG-003: ContainerRecipeの存在確認

**目的**: Image BuilderのContainerRecipeが正しく作成されていることを検証

**前提条件**:
- INT-ECS-IMG-002が成功
- パイプラインARNが取得済み

**テスト手順**:
1. パイプラインからcontainerRecipeArnを取得
2. `aws imagebuilder get-container-recipe`でレシピ情報を取得
3. レシピの設定内容を確認
   - containerType: "DOCKER"
   - targetRepository設定の存在

**期待結果**:
- ContainerRecipeが存在する
- containerTypeが"DOCKER"である
- targetRepository設定が存在する

**確認項目**:
- [ ] containerRecipeArnが取得可能
- [ ] containerType = "DOCKER"
- [ ] targetRepository設定が存在

---

#### INT-ECS-IMG-004: ECRリポジトリ配布設定の確認

**目的**: 既存のECRリポジトリへの配布設定が正しく構成されていることを検証

**前提条件**:
- INT-ECS-IMG-003が成功
- jenkins-agentスタックでECRリポジトリがデプロイ済み

**テスト手順**:
1. SSMパラメータ`/jenkins-infra/{env}/agent/ecr-repository-url`を取得
2. パイプラインのdistributionConfigurationArnを取得
3. DistributionConfigurationの設定を確認
4. ターゲットリポジトリがECR URLと一致することを確認

**期待結果**:
- ECRリポジトリURLが取得可能
- DistributionConfigurationが存在する
- ターゲットリポジトリが既存ECRを指している

**確認項目**:
- [ ] ECRリポジトリURLがSSMから取得可能
- [ ] distributionConfigurationArnが存在
- [ ] ターゲットリポジトリが正しいECRを指している

---

#### INT-ECS-IMG-005: IAMロールの権限確認

**目的**: Image Builder用のIAMロールが正しい権限を持っていることを検証

**前提条件**:
- jenkins-agent-ecs-imageスタックがデプロイ済み

**テスト手順**:
1. IAMロール`jenkins-infra-imagebuilder-role-{env}`の存在を確認
2. アタッチされたポリシーを一覧取得
3. 必要なポリシーがアタッチされていることを確認
   - EC2InstanceProfileForImageBuilder
   - AmazonSSMManagedInstanceCore
   - EC2InstanceProfileForImageBuilderECRContainerBuilds
4. インスタンスプロファイルの存在を確認

**期待結果**:
- IAMロールが存在する
- 必要なポリシーがアタッチされている
- インスタンスプロファイルが存在する

**確認項目**:
- [ ] IAMロールが存在
- [ ] EC2InstanceProfileForImageBuilderポリシーがアタッチ
- [ ] AmazonSSMManagedInstanceCoreポリシーがアタッチ
- [ ] EC2InstanceProfileForImageBuilderECRContainerBuildsポリシーがアタッチ
- [ ] インスタンスプロファイルが存在

---

#### INT-ECS-IMG-006: InfrastructureConfigurationの検証

**目的**: ビルド用EC2インスタンスの設定が正しいことを検証

**前提条件**:
- INT-ECS-IMG-002が成功
- パイプラインARNが取得済み

**テスト手順**:
1. パイプラインからinfrastructureConfigurationArnを取得
2. `aws imagebuilder get-infrastructure-configuration`で設定を取得
3. 以下の設定を確認
   - instanceProfileName
   - instanceTypes
   - subnetId（publicサブネット）
   - securityGroupIds
   - terminateInstanceOnFailure

**期待結果**:
- InfrastructureConfigurationが存在する
- 適切なインスタンスタイプが設定されている
- パブリックサブネットが設定されている
- セキュリティグループが設定されている
- 失敗時の自動終了が有効

**確認項目**:
- [ ] infrastructureConfigurationArnが取得可能
- [ ] instanceProfileNameが設定済み
- [ ] subnetIdがパブリックサブネットを指している
- [ ] securityGroupIdsが設定済み
- [ ] terminateInstanceOnFailure = true

---

#### INT-ECS-IMG-007: Image Builderコンポーネントの検証

**目的**: ツールインストール用コンポーネントが正しく定義されていることを検証

**前提条件**:
- INT-ECS-IMG-003が成功
- ContainerRecipeが取得済み

**テスト手順**:
1. ContainerRecipeからcomponentArnを取得
2. `aws imagebuilder get-component`でコンポーネント情報を取得
3. コンポーネントのプラットフォームとバージョンを確認
4. コンポーネントのデータ（YAML）にbuildとvalidateフェーズが含まれることを確認

**期待結果**:
- コンポーネントが存在する
- platform = "Linux"
- buildフェーズが定義されている
- validateフェーズが定義されている

**確認項目**:
- [ ] コンポーネントが取得可能
- [ ] platform = "Linux"
- [ ] buildフェーズの存在
- [ ] validateフェーズの存在

---

### 2.2 依存リソース連携テスト

#### INT-ECS-IMG-008: ネットワークリソースの参照確認

**目的**: 既存のネットワークスタック（jenkins-network）のリソースが正しく参照されていることを検証

**前提条件**:
- jenkins-networkスタックがデプロイ済み
- jenkins-agent-ecs-imageスタックがデプロイ済み

**テスト手順**:
1. SSMパラメータから以下を取得
   - `/jenkins-infra/{env}/network/vpc-id`
   - `/jenkins-infra/{env}/network/public-subnet-a-id`
2. InfrastructureConfigurationのsubnetIdと比較
3. サブネットが指定されたVPCに属することを確認

**期待結果**:
- VPC IDが取得可能
- サブネットIDが取得可能
- InfrastructureConfigurationのsubnetIdがpublic-subnet-a-idと一致

**確認項目**:
- [ ] VPC IDがSSMから取得可能
- [ ] サブネットIDがSSMから取得可能
- [ ] InfrastructureConfigurationのsubnetIdが一致

---

#### INT-ECS-IMG-009: セキュリティグループの参照確認

**目的**: 既存のセキュリティスタック（jenkins-security）のセキュリティグループが正しく参照されていることを検証

**前提条件**:
- jenkins-securityスタックがデプロイ済み
- jenkins-agent-ecs-imageスタックがデプロイ済み

**テスト手順**:
1. SSMパラメータから`/jenkins-infra/{env}/security/jenkins-agent-sg-id`を取得
2. InfrastructureConfigurationのsecurityGroupIdsと比較

**期待結果**:
- セキュリティグループIDが取得可能
- InfrastructureConfigurationのsecurityGroupIdsに含まれている

**確認項目**:
- [ ] セキュリティグループIDがSSMから取得可能
- [ ] InfrastructureConfigurationのsecurityGroupIdsに含まれている

---

#### INT-ECS-IMG-010: 既存ECRリポジトリとの統合確認

**目的**: jenkins-agentスタックで作成されたECRリポジトリが配布先として正しく設定されていることを検証

**前提条件**:
- jenkins-agentスタックがデプロイ済み（ECRリポジトリ作成済み）
- jenkins-agent-ecs-imageスタックがデプロイ済み

**テスト手順**:
1. SSMパラメータから`/jenkins-infra/{env}/agent/ecr-repository-url`を取得
2. ECRリポジトリURLからリポジトリ名を抽出
3. DistributionConfigurationまたはContainerRecipeのtargetRepository設定を確認
4. リポジトリ名が一致することを確認

**期待結果**:
- ECRリポジトリURLが取得可能
- ターゲットリポジトリ名が一致

**確認項目**:
- [ ] ECRリポジトリURLが取得可能
- [ ] リポジトリ名がtargetRepository設定と一致

---

### 2.3 Ansibleプレイブック検証テスト

#### INT-ECS-IMG-011: デプロイプレイブックの構文検証

**目的**: デプロイ用Ansibleプレイブックが構文的に正しいことを検証

**前提条件**:
- Ansibleがインストール済み
- プレイブックファイルが存在

**テスト手順**:
1. `ansible-playbook --syntax-check`でプレイブックの構文チェック
2. 必要なロールの存在を確認
   - jenkins_agent_ecs_image
   - 依存ロール（aws_setup, aws_cli_helper, pulumi_helper, ssm_parameter_store）

**期待結果**:
- 構文エラーがない
- 依存ロールが存在する

**確認項目**:
- [ ] ansible-playbook --syntax-checkが成功
- [ ] jenkins_agent_ecs_imageロールが存在
- [ ] 依存ロールがすべて存在

---

#### INT-ECS-IMG-012: 削除プレイブックの構文検証

**目的**: 削除用Ansibleプレイブックが構文的に正しいことを検証

**前提条件**:
- Ansibleがインストール済み
- プレイブックファイルが存在

**テスト手順**:
1. `ansible-playbook --syntax-check`でプレイブックの構文チェック
2. confirm変数なしでの実行が拒否されることを確認

**期待結果**:
- 構文エラーがない
- confirm変数なしでは実行が拒否される

**確認項目**:
- [ ] ansible-playbook --syntax-checkが成功
- [ ] confirm=falseの場合にエラーとなる

---

### 2.4 Pulumiスタック検証テスト

#### INT-ECS-IMG-013: Pulumiプレビュー実行

**目的**: Pulumiスタックがプレビュー実行でエラーなく動作することを検証

**前提条件**:
- 依存スタック（jenkins-ssm-init, jenkins-network, jenkins-security, jenkins-agent）がデプロイ済み
- Node.js、npm、Pulumiがインストール済み

**テスト手順**:
1. `pulumi/jenkins-agent-ecs-image/`ディレクトリに移動
2. `npm install`で依存パッケージをインストール
3. `pulumi stack select {env}`でスタックを選択
4. `pulumi preview`を実行
5. 作成予定のリソースを確認

**期待結果**:
- プレビューがエラーなく完了
- 以下のリソースが作成予定として表示される
  - aws:imagebuilder:Component
  - aws:imagebuilder:ContainerRecipe
  - aws:imagebuilder:InfrastructureConfiguration
  - aws:imagebuilder:DistributionConfiguration
  - aws:imagebuilder:ImagePipeline
  - aws:iam:Role
  - aws:iam:InstanceProfile
  - aws:ssm:Parameter（3つ以上）

**確認項目**:
- [ ] npm installが成功
- [ ] pulumi previewがエラーなく完了
- [ ] 期待されるリソースが表示される

---

#### INT-ECS-IMG-014: Pulumiスタックの冪等性確認

**目的**: Pulumiスタックが冪等に動作することを検証（複数回のデプロイで同じ結果）

**前提条件**:
- INT-ECS-IMG-013が成功
- スタックが一度デプロイ済み

**テスト手順**:
1. `pulumi up --yes`で初回デプロイ
2. 再度`pulumi up --yes`を実行
3. 変更なし（no changes）であることを確認

**期待結果**:
- 2回目のデプロイで"no changes"と表示される
- リソースが変更されない

**確認項目**:
- [ ] 初回デプロイが成功
- [ ] 2回目のデプロイで変更なし

---

### 2.5 Component YAML検証テスト

#### INT-ECS-IMG-015: Component YAMLの構文検証

**目的**: Image Builder Component YAMLが正しい構文であることを検証

**前提条件**:
- component.ymlファイルが存在
- yamllintまたは同等のツールがインストール済み

**テスト手順**:
1. `yamllint component.yml`で構文チェック
2. 必須フィールドの存在を確認
   - name
   - description
   - schemaVersion
   - phases（buildとvalidate）
3. buildフェーズの各ステップを確認

**期待結果**:
- YAML構文が正しい
- 必須フィールドがすべて存在
- buildフェーズとvalidateフェーズが定義されている

**確認項目**:
- [ ] YAML構文が正しい
- [ ] name, description, schemaVersionが存在
- [ ] buildフェーズが存在
- [ ] validateフェーズが存在

---

#### INT-ECS-IMG-016: Component YAMLのツールインストール検証

**目的**: Component YAMLに必要なすべてのツールのインストールステップが含まれていることを検証

**前提条件**:
- INT-ECS-IMG-015が成功

**テスト手順**:
1. component.ymlの内容を解析
2. 以下のツールのインストールステップが含まれていることを確認
   - Java 21
   - Node.js 20
   - AWS CLI v2
   - Pulumi
   - Ansible
   - Git
   - Python3
3. jenkinsユーザー作成ステップの存在を確認
4. entrypoint.sh配置ステップの存在を確認

**期待結果**:
- すべての必要ツールのインストールステップが存在
- jenkinsユーザー作成ステップが存在
- entrypoint.sh配置ステップが存在

**確認項目**:
- [ ] Java 21インストールステップ
- [ ] Node.js 20インストールステップ
- [ ] AWS CLI v2インストールステップ
- [ ] Pulumiインストールステップ
- [ ] Ansibleインストールステップ
- [ ] Gitインストールステップ
- [ ] Python3インストールステップ
- [ ] jenkinsユーザー作成ステップ
- [ ] entrypoint.sh配置ステップ

---

### 2.6 手動検証シナリオ

以下のテストシナリオは、実際のAWSリソースを使用した手動検証が必要です。

#### INT-ECS-IMG-MAN-001: パイプライン実行テスト

**目的**: Image Builderパイプラインを手動実行し、イメージビルドが成功することを検証

**前提条件**:
- jenkins-agent-ecs-imageスタックがデプロイ済み
- パイプラインがENABLED状態

**テスト手順**:
1. SSMパラメータからpipeline-arnを取得
2. `aws imagebuilder start-image-pipeline-execution`でパイプラインを実行
3. パイプライン実行のステータスを監視（30〜60分）
4. ビルド完了を確認

**期待結果**:
- パイプラインが正常に開始される
- ビルドが60分以内に完了する
- ビルドステータスが`AVAILABLE`となる

**確認項目**:
- [ ] パイプライン実行が開始される
- [ ] ビルドが60分以内に完了
- [ ] 最終ステータスが`AVAILABLE`

**注意**: このテストはAWSコストが発生し、30〜60分かかります。

---

#### INT-ECS-IMG-MAN-002: ECRイメージプッシュ確認

**目的**: ビルド完了後、ECRリポジトリにイメージがプッシュされることを検証

**前提条件**:
- INT-ECS-IMG-MAN-001が成功
- イメージビルドが完了

**テスト手順**:
1. SSMパラメータからECRリポジトリURLを取得
2. `aws ecr list-images`でリポジトリ内のイメージを一覧取得
3. 以下のタグが存在することを確認
   - `latest`
   - ビルド日付形式のタグ

**期待結果**:
- ECRリポジトリにイメージが存在
- `latest`タグが存在
- ビルド日付タグが存在

**確認項目**:
- [ ] イメージがECRに存在
- [ ] latestタグが存在
- [ ] 日付タグが存在

---

#### INT-ECS-IMG-MAN-003: コンテナイメージのツール検証

**目的**: ビルドされたコンテナイメージに必要なツールがすべてインストールされていることを検証

**前提条件**:
- INT-ECS-IMG-MAN-002が成功
- ECRにイメージが存在

**テスト手順**:
1. ECRからイメージをプル
2. コンテナを起動し、以下のコマンドを実行
   - `java -version`
   - `git --version`
   - `node --version`
   - `npm --version`
   - `python3 --version`
   - `aws --version`
   - `pulumi version`
   - `ansible --version`
3. 各ツールのバージョンを確認

**期待結果**:
- すべてのコマンドが成功
- Java 21がインストール済み
- Node.js 20.xがインストール済み
- その他のツールが最新バージョンでインストール済み

**確認項目**:
- [ ] java -version: Java 21
- [ ] git --version: 2.x以上
- [ ] node --version: 20.x
- [ ] npm --version: 10.x以上
- [ ] python3 --version: 3.x
- [ ] aws --version: v2.x
- [ ] pulumi version: 3.x
- [ ] ansible --version: 2.x以上

---

#### INT-ECS-IMG-MAN-004: entrypoint.shの検証

**目的**: entrypoint.shが正しく配置され、実行可能であることを検証

**前提条件**:
- INT-ECS-IMG-MAN-002が成功

**テスト手順**:
1. ECRからイメージをプル
2. コンテナを起動し、以下を確認
   - `/entrypoint.sh`の存在
   - 実行権限（chmod +x）
   - jenkinsユーザーの所有
3. agent.jarの存在を確認
   - `/home/jenkins/agent.jar`

**期待結果**:
- entrypoint.shが存在し、実行可能
- agent.jarが存在
- jenkinsユーザーが所有者

**確認項目**:
- [ ] /entrypoint.shが存在
- [ ] 実行権限が設定済み
- [ ] jenkinsユーザーが所有者
- [ ] /home/jenkins/agent.jarが存在

---

## 3. テストデータ

### 3.1 環境変数

| 変数名 | 値 | 説明 |
|--------|-----|------|
| ENV | dev / staging / prod | テスト対象環境 |
| SSM_PREFIX | /jenkins-infra/${ENV} | SSMパラメータのプレフィックス |
| AWS_REGION | ap-northeast-1 | AWSリージョン |

### 3.2 SSMパラメータ（入力）

| パラメータ名 | 値の例 | 説明 |
|-------------|--------|------|
| /jenkins-infra/{env}/config/project-name | jenkins-infra | プロジェクト名 |
| /jenkins-infra/{env}/network/vpc-id | vpc-xxxxxxxx | VPC ID |
| /jenkins-infra/{env}/network/public-subnet-a-id | subnet-xxxxxxxx | パブリックサブネットID |
| /jenkins-infra/{env}/security/jenkins-agent-sg-id | sg-xxxxxxxx | セキュリティグループID |
| /jenkins-infra/{env}/agent/ecr-repository-url | xxxx.dkr.ecr.ap-northeast-1.amazonaws.com/jenkins-infra-agent-ecs-dev | ECRリポジトリURL |

### 3.3 SSMパラメータ（出力）

| パラメータ名 | 値の形式 | 説明 |
|-------------|---------|------|
| /jenkins-infra/{env}/agent-ecs-image/pipeline-arn | arn:aws:imagebuilder:ap-northeast-1:xxxx:image-pipeline/xxxx | パイプラインARN |
| /jenkins-infra/{env}/agent-ecs-image/component-version | 1.250114.12345 | コンポーネントバージョン |
| /jenkins-infra/{env}/agent-ecs-image/recipe-version | 1.250114.12345 | レシピバージョン |

### 3.4 IAMロール名

| ロール名 | 説明 |
|---------|------|
| jenkins-infra-imagebuilder-role-{env} | Image Builder実行用IAMロール |

---

## 4. テスト環境要件

### 4.1 必要なツール

| ツール | バージョン | 用途 |
|--------|-----------|------|
| AWS CLI | v2.x | AWS API操作 |
| jq | 1.6+ | JSON処理 |
| shellcheck | 0.8+ | シェルスクリプト構文チェック |
| yamllint | 1.x | YAML構文チェック |
| Node.js | 18+ | Pulumiスタック実行 |
| Pulumi | 3.x | インフラデプロイ |
| Ansible | 2.x | プレイブック実行 |
| Docker | 20+ | コンテナイメージ検証（手動テスト用） |

### 4.2 AWS権限

テスト実行には以下のAWS権限が必要：

- `ssm:GetParameter`, `ssm:PutParameter` - SSMパラメータの読み書き
- `imagebuilder:Get*`, `imagebuilder:List*` - Image Builderリソースの参照
- `imagebuilder:StartImagePipelineExecution` - パイプライン実行（手動テスト）
- `ecr:GetAuthorizationToken`, `ecr:DescribeImages`, `ecr:ListImages` - ECRイメージの参照
- `iam:GetRole`, `iam:ListAttachedRolePolicies` - IAMロールの参照

### 4.3 前提スタック

テスト実行前に以下のスタックがデプロイ済みである必要があります：

| スタック | 提供するリソース |
|---------|-----------------|
| jenkins-ssm-init | project-name設定 |
| jenkins-network | VPC、サブネット |
| jenkins-security | セキュリティグループ |
| jenkins-agent | ECRリポジトリ |

---

## 5. テスト実行計画

### 5.1 テスト実行順序

```
Phase 1: 静的検証（CI/CDで自動実行可能）
├── INT-ECS-IMG-011: デプロイプレイブック構文検証
├── INT-ECS-IMG-012: 削除プレイブック構文検証
├── INT-ECS-IMG-015: Component YAML構文検証
└── INT-ECS-IMG-016: Component YAMLツールインストール検証

Phase 2: Pulumiプレビュー検証
└── INT-ECS-IMG-013: Pulumiプレビュー実行

Phase 3: デプロイ後検証（デプロイ済み環境で実行）
├── INT-ECS-IMG-001: SSMパラメータ存在確認
├── INT-ECS-IMG-002: パイプラインステータス確認
├── INT-ECS-IMG-003: ContainerRecipe存在確認
├── INT-ECS-IMG-004: ECRリポジトリ配布設定確認
├── INT-ECS-IMG-005: IAMロール権限確認
├── INT-ECS-IMG-006: InfrastructureConfiguration検証
├── INT-ECS-IMG-007: Image Builderコンポーネント検証
├── INT-ECS-IMG-008: ネットワークリソース参照確認
├── INT-ECS-IMG-009: セキュリティグループ参照確認
├── INT-ECS-IMG-010: 既存ECRリポジトリ統合確認
└── INT-ECS-IMG-014: Pulumiスタック冪等性確認

Phase 4: 手動検証（オプション、時間とコストがかかる）
├── INT-ECS-IMG-MAN-001: パイプライン実行テスト
├── INT-ECS-IMG-MAN-002: ECRイメージプッシュ確認
├── INT-ECS-IMG-MAN-003: コンテナイメージツール検証
└── INT-ECS-IMG-MAN-004: entrypoint.sh検証
```

### 5.2 テスト所要時間見積もり

| フェーズ | 見積もり時間 | 備考 |
|---------|-------------|------|
| Phase 1 | 5分 | 静的検証のみ |
| Phase 2 | 2分 | Pulumiプレビュー |
| Phase 3 | 5-10分 | デプロイ済み環境での検証 |
| Phase 4 | 45-90分 | イメージビルド時間を含む |

---

## 6. 品質ゲートチェックリスト（Phase 3）

### 必須要件

- [x] **Phase 2の戦略に沿ったテストシナリオである**
  - INTEGRATION_ONLY戦略に基づき、すべて統合テストシナリオとして作成
  - ユニットテスト、BDDシナリオは作成していない

- [x] **主要な正常系がカバーされている**
  - Pulumiリソース作成の検証（INT-ECS-IMG-001〜007）
  - 依存リソースとの連携検証（INT-ECS-IMG-008〜010）
  - プレイブック実行検証（INT-ECS-IMG-011〜014）
  - イメージビルド・プッシュ検証（INT-ECS-IMG-MAN-001〜004）

- [x] **主要な異常系がカバーされている**
  - SSMパラメータ欠落時の検出（INT-ECS-IMG-001）
  - パイプラインステータス異常の検出（INT-ECS-IMG-002）
  - IAM権限不足の検出（INT-ECS-IMG-005）
  - プレイブック構文エラーの検出（INT-ECS-IMG-011, 012）

- [x] **期待結果が明確である**
  - 各テストシナリオに具体的な期待結果を記載
  - 確認項目をチェックリスト形式で提示

---

## 7. 承認・レビュー

| 項目 | 状態 | 日付 | 担当者 |
|------|------|------|--------|
| テストシナリオ作成 | 完了 | 2025-01-14 | - |
| クリティカルシンキングレビュー | 未実施 | - | - |
| テストシナリオ承認 | 未実施 | - | - |

---

*このテストシナリオはIssue #496の統合テストを定義しています。Phase 4（実装）では、このシナリオに基づいてテストスクリプトを作成します。*
