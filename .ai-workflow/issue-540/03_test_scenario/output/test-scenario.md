# テストシナリオ書: Issue #540 - ドキュメントの追加: infrastructure.md

## 0. テスト戦略サマリー

### 選択されたテスト戦略（Phase 2から引用）
**テスト戦略: INTEGRATION_ONLY**

**判断根拠**:
- **ドキュメント更新のため自動テストコードは不要**
- **実装との整合性確認が最も重要**な検証ポイント
- SSMパラメータ出力名とドキュメント記載内容の一致確認が必要
- pulumi/jenkins-agent/index.tsの実装内容とdocの記載内容の整合性検証が中心
- BDDやユニットテストは該当せず、統合的な検証（実装コードとドキュメントの照合）のみが必要

### テスト対象の範囲
- `docs/architecture/infrastructure.md` と `pulumi/jenkins-agent/index.ts` の整合性
- SSMパラメータ出力名の正確性
- `docker/jenkins-agent-ecs` ディレクトリの役割説明の妥当性
- ドキュメント内リンクと参照整合性

### テストの目的
更新されたドキュメントが実装と完全に一致し、運用時に誤認や作業ミスを引き起こさない正確性を確保すること

## 1. Integrationテストシナリオ

### シナリオ1: ECS Fargateリソース定義の整合性確認

**シナリオ名**: infrastructure.md × pulumi/jenkins-agent/index.ts（ECS Fargate部分）

**目的**: ドキュメントに記載されるECS Fargateリソースが実装と一致することを検証

**前提条件**:
- pulumi/jenkins-agent/index.tsのECS Fargate関連リソース定義（739行目以降）が存在
- infrastructure.mdにECS Fargateセクションが追加済み

**テスト手順**:
1. pulumi/jenkins-agent/index.tsの739行目以降からECS Fargate関連リソースを抽出
2. 以下のリソース定義を特定:
   - ECS Cluster作成部分
   - ECR Repository作成部分
   - Task Definition作成部分
   - IAM Role作成部分
   - CloudWatch Logs Group作成部分
3. infrastructure.mdの「ECS Fargateエージェント詳細」セクションと照合
4. 各リソースの設定内容（名前、設定値、依存関係）が一致するか確認

**期待結果**:
- ECS Clusterの名前と設定がドキュメントと実装で一致
- ECR Repositoryの名前とポリシーが一致
- Task Definitionの設定項目（CPU、メモリ、実行ロール等）が一致
- IAM Roleの権限設定とポリシーが一致
- CloudWatch Logs Groupの設定が一致

**確認項目**:
- [ ] ECS Cluster名がpulumiコードとドキュメントで同一
- [ ] ECR Repository名とURIパターンが一致
- [ ] Task DefinitionのCPU/メモリ設定値が一致
- [ ] ECS Execution RoleのポリシーAttachmentが正確
- [ ] ECS Task RoleのAdministratorAccessが記載
- [ ] CloudWatch Logs Groupの名前とリテンション設定が一致

### シナリオ2: SSMパラメータ出力名の完全一致確認

**シナリオ名**: infrastructure.md × pulumi/jenkins-agent/index.ts（SSMパラメータ部分）

**目的**: ドキュメントに記載されるSSMパラメータ名が実装の出力と完全に一致することを検証

**前提条件**:
- pulumi/jenkins-agent/index.tsの943行目以降にECS関連SSMパラメータ出力が存在
- infrastructure.mdの「SSMパラメータ一覧」セクションが作成済み

**テスト手順**:
1. pulumi/jenkins-agent/index.tsの943行目以降からSSMパラメータ出力を抽出
2. 以下のパラメータを特定:
   - ECS Cluster ARN出力
   - ECS Cluster Name出力
   - ECS Task Definition ARN出力
   - ECR Repository URL出力
   - ECS Execution Role ARN出力
   - ECS Task Role ARN出力
   - ECS Log Group Name出力
3. infrastructure.mdの「SSMパラメータ一覧」テーブルと照合
4. パラメータ名のパス（`/jenkins-infra/{environment}/agent/...`）が完全一致するか確認

**期待結果**:
- 実装で出力される全てのECS関連SSMパラメータがドキュメントに記載されている
- パラメータ名のパスが実装とドキュメントで文字列として完全一致
- パラメータの説明と用途が実装の意図と合致

**確認項目**:
- [ ] `/jenkins-infra/{environment}/agent/ecs-cluster-arn` の記載
- [ ] `/jenkins-infra/{environment}/agent/ecs-cluster-name` の記載
- [ ] `/jenkins-infra/{environment}/agent/ecs-task-definition-arn` の記載
- [ ] `/jenkins-infra/{environment}/agent/ecr-repository-url` の記載
- [ ] `/jenkins-infra/{environment}/agent/ecs-execution-role-arn` の記載
- [ ] `/jenkins-infra/{environment}/agent/ecs-task-role-arn` の記載
- [ ] `/jenkins-infra/{environment}/agent/ecs-log-group-name` の記載
- [ ] パラメータ名のtypoや相違がない
- [ ] 説明文が実装の用途と合致

### シナリオ3: docker/jenkins-agent-ecsディレクトリの役割説明妥当性確認

**シナリオ名**: infrastructure.md × docker/jenkins-agent-ecs ディレクトリ構成

**目的**: ドキュメントに記載されるdocker/jenkins-agent-ecsの役割説明が実際のディレクトリ構成と一致することを検証

**前提条件**:
- docker/jenkins-agent-ecsディレクトリが存在
- infrastructure.mdにディレクトリ構造説明が追加済み

**テスト手順**:
1. docker/jenkins-agent-ecsディレクトリの実際の構成を確認
2. 以下のファイルの存在と内容を確認:
   - Dockerfile（ECS Fargate用イメージ定義）
   - entrypoint.sh（amazon-ecsプラグイン互換スクリプト）
3. infrastructure.mdの「docker/jenkins-agent-ecs設計」セクションと照合
4. ディレクトリ構成図とファイルの役割説明が実態と一致するか確認

**期待結果**:
- ディレクトリ構成図が実際のファイル構造と一致
- Dockerfileの役割説明が実装内容と合致
- entrypoint.shの機能説明が実装内容と合致

**確認項目**:
- [ ] ディレクトリ内のファイル一覧がドキュメントと一致
- [ ] Dockerfileの説明（Multi-stage build、含有ツール等）が実態と合致
- [ ] entrypoint.shの説明（amazon-ecsプラグイン互換性等）が実態と合致
- [ ] ファイルの役割と利用手順が具体的で実行可能

### シナリオ4: SpotFleetとECS Fargateの併存関係の技術的妥当性確認

**シナリオ名**: infrastructure.md × 実装全体（SpotFleet + ECS Fargate併存構成）

**目的**: ドキュメントに記載されるSpotFleetとECS Fargateの併存関係が実装の構成と合致することを検証

**前提条件**:
- pulumi/jenkins-agent/index.tsでSpotFleetとECS Fargate両方のリソースが定義済み
- infrastructure.mdに「Jenkins エージェント構成比較」セクションが追加済み

**テスト手順**:
1. pulumi/jenkins-agent/index.tsでSpotFleetリソース定義部分を確認
2. ECS Fargateリソース定義部分を確認
3. 両者の共存関係（同一Jenkins Controllerからの管理等）を確認
4. infrastructure.mdの比較表と使い分け指針を照合
5. 技術的な制約や前提条件が実装と一致するか確認

**期待結果**:
- SpotFleetとECS Fargateが同一Jenkins環境で併存可能な構成として記載
- 使い分け指針（コスト、起動速度、スケーラビリティ等）が技術的に正確
- 両エージェント種別のSSM参照パターンが実装と合致

**確認項目**:
- [ ] SpotFleetリソースがpulumiコードに存在し、ドキュメントの説明と一致
- [ ] ECS Fargateリソースがpulumiコードに存在し、ドキュメントの説明と一致
- [ ] 比較表の技術特性（コスト、起動速度等）が実装ベースで妥当
- [ ] 使い分け指針が運用観点で実行可能
- [ ] 両エージェント種別のJenkins Controller接続方法が正確

### シナリオ5: ドキュメント内リンクと参照整合性の確認

**シナリオ名**: infrastructure.md × README.md × 関連ドキュメント

**目的**: 更新されたinfrastructure.mdへのリンクや参照が他のドキュメントで正常に機能することを検証

**前提条件**:
- infrastructure.mdが更新済み
- README.mdにクイックナビゲーションが存在

**テスト手順**:
1. README.mdからinfrastructure.mdへのリンクを確認
2. infrastructure.md内の他ドキュメントへのリンクを確認
3. 新規追加されたセクション（ECS Fargateエージェント詳細等）への内部リンクを確認
4. アーキテクチャ図や表の参照整合性を確認

**期待結果**:
- 全てのリンクが正常に機能する
- 内部参照（セクション間リンク）が正確
- クイックナビゲーションが更新内容を適切に案内

**確認項目**:
- [ ] README.mdのクイックナビゲーションリンクが有効
- [ ] infrastructure.md内の内部リンク（#アンカー）が有効
- [ ] 他ドキュメントへの外部リンクが有効
- [ ] アーキテクチャ図の参照が正確
- [ ] 表や一覧への参照が正確

## 2. テストデータ

### 検証対象の実装ファイル
- `pulumi/jenkins-agent/index.ts` (739行目以降のECS Fargate定義, 943行目以降のSSM出力)
- `docker/jenkins-agent-ecs/Dockerfile`
- `docker/jenkins-agent-ecs/entrypoint.sh`

### 検証対象のドキュメントファイル
- `docs/architecture/infrastructure.md` (更新後)
- `README.md` (クイックナビゲーション部分)

### 検証対象のSSMパラメータ名一覧
```
/jenkins-infra/{environment}/agent/ecs-cluster-arn
/jenkins-infra/{environment}/agent/ecs-cluster-name
/jenkins-infra/{environment}/agent/ecs-task-definition-arn
/jenkins-infra/{environment}/agent/ecr-repository-url
/jenkins-infra/{environment}/agent/ecs-execution-role-arn
/jenkins-infra/{environment}/agent/ecs-task-role-arn
/jenkins-infra/{environment}/agent/ecs-log-group-name
```

## 3. テスト環境要件

### 必要なテスト環境
- ローカル開発環境（ファイル読み込み・照合用）
- Git環境（差分確認用）

### 必要な外部サービス
- なし（静的ファイルの照合のみ）

### 検証ツール
- テキスト比較ツール（diff、grep等）
- Markdownリンク検証ツール（可能であれば）

## 4. テスト実行手順

### 事前準備
1. 実装コードとドキュメントの最新版を取得
2. 比較対象ファイルの存在確認

### 実行順序
1. **シナリオ2**（SSMパラメータ）を最初に実行（最も客観的な検証）
2. **シナリオ1**（ECS Fargateリソース）を実行
3. **シナリオ3**（docker/jenkins-agent-ecs）を実行
4. **シナリオ4**（併存関係）を実行
5. **シナリオ5**（リンク整合性）を最後に実行

### 不整合発見時の対応
1. 実装とドキュメントのどちらが正しいかを判断
2. 実装が正の場合はドキュメントを修正
3. ドキュメントが正の場合は実装チームに確認
4. 修正後、関連するシナリオを再実行

## 5. 品質ゲート（Phase 3）

テストシナリオは以下の品質ゲートを満たします：

- [x] **Phase 2の戦略（INTEGRATION_ONLY）に沿ったテストシナリオである**
  - 実装とドキュメントの統合的な整合性確認に特化
  - ユニットテストやBDDシナリオは含まない

- [x] **主要な正常系がカバーされている**
  - ECS Fargateリソース定義の正確な記載
  - SSMパラメータ出力名の完全一致
  - docker/jenkins-agent-ecsの役割説明妥当性

- [x] **主要な異常系がカバーされている**
  - 不整合発見時の対応手順を明記
  - リンク切れや参照エラーの検出

- [x] **期待結果が明確である**
  - 各シナリオで具体的な確認項目をチェックリスト形式で明記
  - 合格基準（完全一致、正常機能等）を明示

## 6. 成功判定基準

全ての統合テストシナリオが以下の条件を満たした場合に成功とみなします：

1. **ECS Fargateリソースの完全一致**: pulumiコードとドキュメントの記載内容に相違がない
2. **SSMパラメータの完全網羅**: 実装で出力される全パラメータがドキュメントに正確に記載
3. **docker/jenkins-agent-ecsの正確な説明**: 実際のディレクトリ構成とドキュメントの説明が一致
4. **併存関係の技術的妥当性**: SpotFleetとECS Fargateの使い分け指針が実装ベースで正確
5. **参照整合性の確保**: 全てのリンクと参照が正常に機能

## 7. リスクと軽減策

### リスク1: 実装の継続的変更による検証タイミングのズレ
- **影響度**: 中
- **軽減策**: テスト実行直前に実装ファイルの最新版を確認、変更があった場合は再テスト

### リスク2: 複雑なpulumiコードの解釈誤り
- **影響度**: 中
- **軽減策**: 不明な点は実装者に確認、段階的な照合で精度向上

### リスク3: ドキュメント更新の部分的実装
- **影響度**: 高
- **軽減策**: 全セクションの更新完了を前提条件として明記、未完了部分の特定

## 8. 継続的品質管理

### 定期的な整合性確認
- 実装変更時のドキュメント更新チェック
- 月次での整合性確認レビュー

### 自動化の検討
- SSMパラメータ名の自動照合スクリプト作成可能性の検討
- Markdownリンク検証の自動化

これらの統合テストシナリオにより、ドキュメントと実装の完全な整合性を確保し、運用時の誤認や作業ミスを防止します。