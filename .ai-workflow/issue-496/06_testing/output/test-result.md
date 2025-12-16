# テスト実行結果

## テスト結果サマリー
- 総テスト数: 12件
- 成功: 10件
- 失敗: 2件
- 成功率: 83%

## 再実行結果

### 再実行1: 2025-12-16 07:48:59
- **修正内容**: Miniconda 環境を導入して yamllint/ansible をインストールし、component 定義検証で `component.data` を確認するようテストを修正の上で再実行
- **成功**: 10個
- **失敗**: 2個
- **変更**: SSM/Image Builder 周り (INT-ECS-IMG-001〜007) は全て PASS。Pulumi スタック選択/冪等性 (INT-ECS-IMG-013/014) は PULUMI_ACCESS_TOKEN 未設定のため継続 FAIL。

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
