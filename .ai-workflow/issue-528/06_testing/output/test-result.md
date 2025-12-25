# テスト実行結果

## テスト結果サマリー
- 総テスト数: 104件
- 成功: 103件
- 失敗: 1件
- 成功率: 99%

### `jenkins/jobs/pipeline/docs-generator/pull-request-comment-builder/tests/bdd/test_bdd_pr_comment_generation.py`
- **エラー**: SyntaxError: expected '('（テスト名に半角スペースが含まれており関数名として無効）
- **スタックトレース**:
  ```
  File "jenkins/jobs/pipeline/docs-generator/pull-request-comment-builder/tests/bdd/test_bdd_pr_comment_generation.py", line 245
    def test_scenario_互換性レイヤーを使用したPR コメント生成(self, logger, temp_template_dir):
                                       ^^^^^^
  SyntaxError: expected '('
  ```
