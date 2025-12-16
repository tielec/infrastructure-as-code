# テスト実行結果

## テスト結果サマリー
- 総テスト数: 12件
- 成功: 4件
- 失敗: 8件
- 成功率: 33%

## 再実行結果

### 再実行1: 2025-12-16 05:41:50
- **修正内容**: 環境に欠けていた yamllint/ansible-playbook を npx ベースのローカル shim (.local/bin) で補完し、INT-ECS-IMG の全スクリプトを再実行
- **成功**: 4個
- **失敗**: 8個
- **変更**: YAML/Ansible 系は依存解消で PASS を継続。Pulumi 認証・SSM パラメータ欠如による失敗は継続。

## 失敗したテストの詳細

### `tests/integration/ecs-image/test_pulumi_stack.sh::INT-ECS-IMG-013`
- **エラー**: PULUMI_ACCESS_TOKEN 未設定でスタック選択に失敗し preview 開始前に停止
- **スタックトレース**:
  ```
  [INFO] Selecting Pulumi stack dev
  error: PULUMI_ACCESS_TOKEN must be set for login during non-interactive CLI sessions
  [ERROR] Pulumi stack selection failed for dev
  ```

### `tests/integration/ecs-image/test_pulumi_stack.sh::INT-ECS-IMG-014`
- **エラー**: スタック選択が失敗したため `pulumi up` の冪等性確認に到達せず
- **スタックトレース**:
  ```
  [INFO] Selecting Pulumi stack dev
  error: PULUMI_ACCESS_TOKEN must be set for login during non-interactive CLI sessions
  [ERROR] Pulumi stack selection failed for dev
  ```

### `tests/integration/ecs-image/test_ecs_image_pipeline.sh::INT-ECS-IMG-001`
- **エラー**: SSM パラメータ `/jenkins-infra/dev/agent-ecs-image/*` が存在せず取得に失敗
- **スタックトレース**:
  ```
  [ERROR] SSM parameter missing for pipeline ARN: /jenkins-infra/dev/agent-ecs-image/pipeline-arn
  [ERROR] SSM parameter missing for component version: /jenkins-infra/dev/agent-ecs-image/component-version
  [ERROR] SSM parameter missing for recipe version: /jenkins-infra/dev/agent-ecs-image/recipe-version
  ```

### `tests/integration/ecs-image/test_ecs_image_pipeline.sh::INT-ECS-IMG-002`
- **エラー**: パイプライン ARN 未取得のため Image Builder パイプラインを参照できず
- **スタックトレース**:
  ```
  [ERROR] Image pipeline not found for ARN: 
  ```

### `tests/integration/ecs-image/test_ecs_image_pipeline.sh::INT-ECS-IMG-003`
- **エラー**: コンテナレシピ ARN 取得失敗でレシピ検証不可
- **スタックトレース**:
  ```
  [ERROR] Container recipe not found: 
  ```

### `tests/integration/ecs-image/test_ecs_image_pipeline.sh::INT-ECS-IMG-004`
- **エラー**: 配布設定 ARN 取得失敗で DistributionConfiguration を取得できず
- **スタックトレース**:
  ```
  [ERROR] Distribution configuration not found: 
  ```

### `tests/integration/ecs-image/test_ecs_image_pipeline.sh::INT-ECS-IMG-005`
- **エラー**: InfrastructureConfiguration ARN 不明のため構成取得に失敗
- **スタックトレース**:
  ```
  [ERROR] Infrastructure configuration not found: 
  ```

### `tests/integration/ecs-image/test_ecs_image_pipeline.sh::INT-ECS-IMG-007`
- **エラー**: コンポーネント ARN 不明で get-component が失敗
- **スタックトレース**:
  ```
  [ERROR] Component not found: 
  ```
