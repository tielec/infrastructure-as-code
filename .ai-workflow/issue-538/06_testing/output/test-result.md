# テスト実行結果

## テスト結果サマリー
- 総テスト数: 7件
- 成功: 6件
- 失敗: 1件
- 成功率: 85.7%

## 条件分岐

### `tests/integration/test_documentation_links.py::test_external_links_are_reachable`
- **エラー**: https://platform.openai.com/api-keys should be reachable (HTTP < 400), got 403
- **スタックトレース**:
  ```
  Traceback (most recent call last):
    File "/tmp/ai-workflow-repos-7-77d6b70d/infrastructure-as-code/tests/integration/test_documentation_links.py", line 104, in test_external_links_are_reachable
      self.assertLess(
  AssertionError: 403 not less than 400 : https://platform.openai.com/api-keys should be reachable (HTTP < 400), got 403
  ```
