# テストシナリオ書 - Issue #536

## 概要

pr_comment_generator.pyでTokenEstimatorクラスの使用方法が間違っているため、`TokenEstimator.estimate_tokens() missing 1 required positional argument: 'text'`エラーが発生している問題を修正するためのテストシナリオです。

## 1. テスト戦略サマリー

### 選択されたテスト戦略: UNIT_INTEGRATION

**Phase 2で決定された戦略**:
- **UNITテスト**: TokenEstimatorクラスの個別動作確認（既存のテストが存在し、正しい使用パターンを示している）
- **INTEGRATIONテスト**: openai_client.pyがTokenEstimatorを正しく使用できているかの統合確認

### テスト対象の範囲
- **主要修正対象ファイル**: `openai_client.py` (11箇所の修正)
- **テスト拡張対象**: `test_token_estimator.py` (エッジケース追加)
- **統合確認対象**: openai_clientとTokenEstimatorの連携動作

### テストの目的
1. TokenEstimatorクラスのインスタンスベース使用が正しく動作することの確認
2. openai_client.py内の修正が正常に機能することの確認
3. エラー「`TokenEstimator.estimate_tokens() missing 1 required positional argument`」の解消確認
4. 既存機能の保持確認

## 2. Unitテストシナリオ

### 2.1 TokenEstimator基本機能テスト

#### テストケース名: TokenEstimator_初期化_正常系
- **目的**: TokenEstimatorが正常にインスタンス化できることを検証
- **前提条件**: ログオブジェクトが存在する
- **入力**: `logger = logging.getLogger("test")`
- **期待結果**: TokenEstimatorインスタンスが正常に作成される
- **テストデータ**: 標準的なLoggerインスタンス

#### テストケース名: estimate_tokens_正常系_非ASCII文字
- **目的**: 絵文字や特殊文字を含むテキストのトークン推定が正常動作することを検証
- **前提条件**: TokenEstimatorインスタンスが存在する
- **入力**: `text = "Hello 👋 World 🌍 Test 🧪"`
- **期待結果**: 正の整数値が返される
- **テストデータ**: 絵文字を含む文字列

#### テストケース名: estimate_tokens_異常系_None値
- **目的**: None値が与えられた場合のエラーハンドリングを検証
- **前提条件**: TokenEstimatorインスタンスが存在する
- **入力**: `text = None`
- **期待結果**: TypeError或いは適切なエラーが発生する
- **テストデータ**: None値

#### テストケース名: estimate_tokens_境界値_超大テキスト
- **目的**: 非常に大きなテキスト（100KB以上）のトークン推定を検証
- **前提条件**: TokenEstimatorインスタンスが存在する
- **入力**: `text = "A" * 100000`
- **期待結果**: 適切なトークン数が推定される（メモリエラーなし）
- **テストデータ**: 10万文字の文字列

#### テストケース名: truncate_text_正常系_UTF8文字
- **目的**: UTF-8文字（絵文字、特殊文字）を含むテキストの切り詰めを検証
- **前提条件**: TokenEstimatorインスタンスが存在する
- **入力**:
  - `text = "Hello 👋 World 🌍 " * 50`
  - `max_tokens = 10`
- **期待結果**:
  - 切り詰められたテキストのトークン数が10以下
  - UTF-8文字が正しく保たれている
- **テストデータ**: 絵文字を含む長い文字列

#### テストケース名: truncate_text_異常系_負のトークン数
- **目的**: 負のmax_tokensが与えられた場合のエラーハンドリングを検証
- **前提条件**: TokenEstimatorインスタンスが存在する
- **入力**:
  - `text = "Test text"`
  - `max_tokens = -1`
- **期待結果**: ValueError或いは適切なエラーが発生する
- **テストデータ**: 負の整数

#### テストケース名: truncate_text_境界値_ゼロトークン
- **目的**: max_tokens=0の場合の動作を検証
- **前提条件**: TokenEstimatorインスタンスが存在する
- **入力**:
  - `text = "Test text"`
  - `max_tokens = 0`
- **期待結果**: 空文字列が返される
- **テストデータ**: 0値とテキスト

### 2.2 OpenAIClient修正機能テスト

#### テストケース名: OpenAIClient_初期化_TokenEstimator作成
- **目的**: OpenAIClientの初期化時にTokenEstimatorインスタンスが正常に作成されることを検証
- **前提条件**: prompt_managerが存在する
- **入力**: `OpenAIClient(prompt_manager)`
- **期待結果**:
  - `self.token_estimator`が存在する
  - TokenEstimatorのインスタンスである
- **テストデータ**: モックのprompt_manager

#### テストケース名: OpenAIClient_TokenEstimator_初期化エラー
- **目的**: TokenEstimatorの初期化に失敗した場合のエラーハンドリングを検証
- **前提条件**: TokenEstimatorのコンストラクタがエラーを発生するモック
- **入力**: `OpenAIClient(prompt_manager)` (TokenEstimatorがエラー)
- **期待結果**:
  - ValueErrorが発生する
  - エラーメッセージに"TokenEstimator initialization failed"が含まれる
- **テストデータ**: エラーを発生するTokenEstimatorモック

## 3. Integrationテストシナリオ

### 3.1 openai_client.py と TokenEstimator統合テスト

#### シナリオ名: openai_client_TokenEstimator_estimate_tokens統合
- **目的**: openai_client.py内でTokenEstimatorのestimate_tokensが正常に呼び出されることを検証
- **前提条件**:
  - OpenAIClientインスタンスが初期化済み
  - TokenEstimatorインスタンスが正常に作成済み
- **テスト手順**:
  1. OpenAIClientを初期化する
  2. テスト用テキストを準備する
  3. 修正対象の行（806, 815, 825, 832, 1000, 1018, 1134行相当）の処理を実行する
  4. self.token_estimator.estimate_tokens()が呼び出されることを確認
- **期待結果**:
  - TokenEstimator.estimate_tokens()エラーが発生しない
  - self.token_estimator.estimate_tokens()が正常実行される
  - 適切なトークン数が返される
- **確認項目**:
  - [ ] クラスメソッド呼び出しエラーが発生しない
  - [ ] インスタンスメソッド呼び出しが成功する
  - [ ] 戻り値が正の整数である

#### シナリオ名: openai_client_TokenEstimator_truncate_text統合
- **目的**: openai_client.py内でTokenEstimatorのtruncate_text（旧truncate_to_token_limit）が正常に呼び出されることを検証
- **前提条件**:
  - OpenAIClientインスタンスが初期化済み
  - TokenEstimatorインスタンスが正常に作成済み
- **テスト手順**:
  1. OpenAIClientを初期化する
  2. 長いテスト用テキストと最大トークン数を準備する
  3. 修正対象の行（607, 613, 618, 1157行相当）の処理を実行する
  4. self.token_estimator.truncate_text()が呼び出されることを確認
- **期待結果**:
  - truncate_to_token_limitメソッド名エラーが発生しない
  - self.token_estimator.truncate_text()が正常実行される
  - 切り詰められたテキストが返される
- **確認項目**:
  - [ ] 旧メソッド名によるAttributeErrorが発生しない
  - [ ] 新メソッド名での呼び出しが成功する
  - [ ] 切り詰め処理が正常に動作する

#### シナリオ名: pr_comment_generator_全体統合テスト
- **目的**: pr_comment_generator.py全体での修正が正常に動作することを検証
- **前提条件**:
  - 修正済みのopenai_client.pyが存在する
  - テスト用のPRデータファイルが存在する
- **テスト手順**:
  1. テスト用のPRデータ（pr_diff.json, pr_info.json）を準備する
  2. pr_comment_generator.pyを実行する
  3. 処理が完了まで実行されることを確認
  4. 出力ファイルが正常に作成されることを確認
- **期待結果**:
  - "TokenEstimator.estimate_tokens() missing 1 required positional argument"エラーが発生しない
  - 処理が正常に完了する
  - PRコメント生成結果が出力される
- **確認項目**:
  - [ ] エラーログに対象エラーメッセージが出現しない
  - [ ] analysis_result.jsonが正常に作成される
  - [ ] 処理が途中で停止しない

### 3.2 エラー回避確認統合テスト

#### シナリオ名: 実際のエラーケース再現テスト
- **目的**: Issue #536で報告された実際のエラーケースが修正されていることを検証
- **前提条件**:
  - Issue #536のエラーログと同じ条件を再現する環境
  - 修正済みのコードが適用済み
- **テスト手順**:
  1. Issue #536で使用されたのと同じPRデータを準備
  2. 同じコマンドラインオプションでpr_comment_generatorを実行
  3. ログ出力を監視
  4. 処理完了まで実行する
- **期待結果**:
  - "TokenEstimator.estimate_tokens() missing 1 required positional argument: 'text'"エラーが発生しない
  - "Error analyzing chunk"メッセージが発生しない
  - コメント生成が正常に完了する
- **確認項目**:
  - [ ] 対象エラーメッセージがログに出現しない
  - [ ] chunk analyzerでエラーが発生しない
  - [ ] "Comment generation completed successfully!"が表示される

## 4. テストデータ

### 4.1 Unitテスト用テストデータ

```python
# トークン推定用テキストサンプル
test_texts = {
    "empty": "",
    "short_english": "Hello world",
    "short_japanese": "こんにちは世界",
    "mixed_language": "Hello こんにちは 🌍",
    "with_emojis": "Test 👋 🌍 🧪 📝 ✅",
    "special_chars": "@user #123 https://example.com",
    "large_text": "A" * 100000,
    "unicode_text": "Test 中文 العربية עברית",
}

# トークン数テストケース
token_limits = [0, 1, 5, 10, 50, 100, 1000]

# エラーケーステストデータ
error_cases = {
    "none_text": None,
    "negative_tokens": -1,
    "float_tokens": 10.5,
    "string_tokens": "10",
}
```

### 4.2 Integrationテスト用テストデータ

```json
// test_pr_diff.json
{
  "files": [
    {
      "path": "test_file.py",
      "status": "modified",
      "changes": 5,
      "patch": "@@ -1,3 +1,5 @@\n+# New comment\n def test():\n+    # Additional line\n     pass"
    }
  ]
}

// test_pr_info.json
{
  "number": 123,
  "title": "Test PR for TokenEstimator fix",
  "description": "Test description",
  "branch": "feature/test"
}
```

### 4.3 エラー再現用テストデータ

```python
# Issue #536の実際のエラーケース再現用データ
jenkins_test_data = {
    "pr_diff_path": "/tmp/test/pr_diff.json",
    "pr_info_path": "/tmp/test/pr_info.json",
    "output_path": "/tmp/test/analysis_result.json",
    "prompt_output_dir": "/tmp/test/prompts"
}

# 大きなファイルでのテストケース
large_file_data = {
    "file_content": "function test() {\n" + "  // comment\n" * 1000 + "}",
    "expected_chunks": 2,
    "max_tokens_per_chunk": 1000
}
```

## 5. テスト環境要件

### 5.1 必要なテスト環境

#### ローカル開発環境
- **Python**: 3.8以上
- **必要なパッケージ**: pytest, logging, openai
- **テストフレームワーク**: pytest
- **モックライブラリ**: unittest.mock（標準ライブラリ）

#### CI/CD環境
- **Jenkins**: 統合テスト用の環境変数設定
- **OpenAI APIキー**: テスト用の制限付きキー
- **ファイルシステム**: 一時ファイル作成可能な環境

### 5.2 必要な外部サービス・データベース

#### OpenAI API (Integrationテストのみ)
- **用途**: 実際のAPI呼び出しを含む統合テスト
- **制限**: テストではモック使用を優先、実際のAPI呼び出しは最小限
- **エラー処理**: APIレート制限時のフォールバック

#### ファイルシステム
- **一時ディレクトリ**: テスト用ファイル作成・削除
- **権限**: 読み書き権限が必要

### 5.3 モック/スタブの必要性

#### Unitテスト用モック
```python
# TokenEstimator初期化エラー用モック
@patch('pr_comment_generator.token_estimator.TokenEstimator')
def mock_token_estimator_error():
    raise ValueError("Mock initialization error")

# Logger用モック
@patch('logging.getLogger')
def mock_logger():
    return MagicMock()
```

#### Integrationテスト用モック
```python
# OpenAI API用モック（レート制限回避）
@patch('openai.ChatCompletion.create')
def mock_openai_api():
    return {"choices": [{"message": {"content": "mock response"}}]}

# ファイルI/O用モック（大きなファイルテスト）
@patch('builtins.open')
def mock_file_operations():
    return MagicMock()
```

## 6. 品質ゲート（Phase 3）確認

### Phase 2の戦略に沿ったテストシナリオ確認
- ✅ **UNIT_INTEGRATION戦略準拠**: Unitテスト（7ケース）とIntegrationテスト（3シナリオ）を定義
- ✅ **TokenEstimatorクラスの個別動作確認**: 基本機能、エラーケース、境界値テストを包含
- ✅ **openai_clientとTokenEstimator統合確認**: メソッド呼び出し統合、エラー再現テストを包含

### 主要な正常系カバレッジ確認
- ✅ **TokenEstimator初期化**: 正常なインスタンス作成テスト
- ✅ **estimate_tokensメソッド**: 各種テキストでのトークン推定テスト
- ✅ **truncate_textメソッド**: テキスト切り詰め機能テスト
- ✅ **OpenAIClient統合**: 修正後のメソッド呼び出しテスト
- ✅ **pr_comment_generator全体**: エンドツーエンド動作テスト

### 主要な異常系カバレッジ確認
- ✅ **None値エラー**: 不正な入力値でのエラーハンドリング
- ✅ **初期化エラー**: TokenEstimator作成失敗時のエラー処理
- ✅ **負の値エラー**: 不正なトークン数でのエラー処理
- ✅ **実際のエラー再現**: Issue #536の元のエラーケース確認

### 期待結果の明確性確認
- ✅ **具体的な検証項目**: 各テストケースで明確な期待結果を記載
- ✅ **定量的な基準**: トークン数の範囲、エラーメッセージの内容を具体化
- ✅ **確認チェックリスト**: 統合テストで検証すべき項目をリスト化
- ✅ **成功/失敗判定**: 各テストでpass/failの判定基準を明記

## まとめ

このテストシナリオは、Phase 2で決定されたUNIT_INTEGRATION戦略に基づき、TokenEstimatorクラスの正しいインスタンスベース使用への修正を包括的に検証します。

**主要な検証ポイント:**
1. **エラー解消**: `TokenEstimator.estimate_tokens() missing 1 required positional argument`エラーの解消
2. **機能保持**: 既存のトークン推定・テキスト切り詰め機能の保持
3. **統合動作**: openai_client.pyでのTokenEstimator使用が正常動作
4. **品質維持**: 修正による既存機能への悪影響がないことの確認

テストは段階的実行（Unit → Integration → 全体）により、修正の影響範囲を限定し、安全で効率的な検証を実現します。