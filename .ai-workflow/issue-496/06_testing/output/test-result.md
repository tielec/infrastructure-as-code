# テスト実行結果

## テスト結果サマリー
- 総テスト数: 12件
- 成功: 0件
- 失敗: 12件
- 成功率: 0%

## 条件分岐
**失敗時（失敗数が1件以上）**:
以下の形式で失敗したテストの詳細のみを記載してください：

### `tests/integration/ecs-image/test_component_yaml.sh::INT-ECS-IMG-015`
- **エラー**: yamllint が環境に存在せず構文チェックを開始できず
- **スタックトレース**:
  ```
  [ERROR] Required command 'yamllint' not found in PATH
  ```

### `tests/integration/ecs-image/test_component_yaml.sh::INT-ECS-IMG-016`
- **エラー**: yamllint 不在のためインストール手順検証を実行不可
- **スタックトレース**:
  ```
  [ERROR] Required command 'yamllint' not found in PATH
  ```

### `tests/integration/ecs-image/test_ansible_playbooks.sh::INT-ECS-IMG-011`
- **エラー**: ansible-playbook が未インストールでプレイブック構文検証を開始できず
- **スタックトレース**:
  ```
  [ERROR] Required command 'ansible-playbook' not found in PATH
  ```

### `tests/integration/ecs-image/test_ansible_playbooks.sh::INT-ECS-IMG-012`
- **エラー**: ansible-playbook が未インストールのため confirm ガード検証が未実施
- **スタックトレース**:
  ```
  [ERROR] Required command 'ansible-playbook' not found in PATH
  ```

### `tests/integration/ecs-image/test_pulumi_stack.sh::INT-ECS-IMG-013`
- **エラー**: PULUMI_ACCESS_TOKEN 未設定によりスタック選択で失敗し preview を実行できず
- **スタックトレース**:
  ```
  [INFO] Selecting Pulumi stack dev
  error: PULUMI_ACCESS_TOKEN must be set for login during non-interactive CLI sessions
  [ERROR] Pulumi stack selection failed for dev
  ```

### `tests/integration/ecs-image/test_pulumi_stack.sh::INT-ECS-IMG-014`
- **エラー**: スタック選択段階で失敗したため冪等性確認まで到達せず
- **スタックトレース**:
  ```
  [INFO] Selecting Pulumi stack dev
  error: PULUMI_ACCESS_TOKEN must be set for login during non-interactive CLI sessions
  [ERROR] Pulumi stack selection failed for dev
  ```

### `tests/integration/ecs-image/test_ecs_image_pipeline.sh::INT-ECS-IMG-001`
- **エラー**: SSM パラメータ `/jenkins-infra/dev/agent-ecs-image/*` が取得できず
- **スタックトレース**:
  ```
  [ERROR] SSM parameter missing for pipeline ARN: /jenkins-infra/dev/agent-ecs-image/pipeline-arn
  [ERROR] SSM parameter missing for component version: /jenkins-infra/dev/agent-ecs-image/component-version
  [ERROR] SSM parameter missing for recipe version: /jenkins-infra/dev/agent-ecs-image/recipe-version
  ```

### `tests/integration/ecs-image/test_ecs_image_pipeline.sh::INT-ECS-IMG-002`
- **エラー**: パイプライン ARN が空のため Image Builder パイプラインを取得できず
- **スタックトレース**:
  ```
  [ERROR] Image pipeline not found for ARN: 
  ```

### `tests/integration/ecs-image/test_ecs_image_pipeline.sh::INT-ECS-IMG-003`
- **エラー**: コンテナレシピ ARN が空でレシピ取得に失敗
- **スタックトレース**:
  ```
  [ERROR] Container recipe not found: 
  ```

### `tests/integration/ecs-image/test_ecs_image_pipeline.sh::INT-ECS-IMG-004`
- **エラー**: 配布設定 ARN が空のため DistributionConfiguration を取得できず
- **スタックトレース**:
  ```
  [ERROR] Distribution configuration not found: 
  ```

### `tests/integration/ecs-image/test_ecs_image_pipeline.sh::INT-ECS-IMG-005`
- **エラー**: InfrastructureConfiguration ARN が空で構成取得に失敗
- **スタックトレース**:
  ```
  [ERROR] Infrastructure configuration not found: 
  ```

### `tests/integration/ecs-image/test_ecs_image_pipeline.sh::INT-ECS-IMG-007`
- **エラー**: コンポーネント ARN 不明のまま get-component を実行し失敗
- **スタックトレース**:
  ```
  [ERROR] Component not found: 
  ```
