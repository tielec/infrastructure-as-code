# テストシナリオ: Issue #528

## ファイルサイズの削減: pr_comment_generator.py

---

## 1. テスト戦略サマリー

### 1.1 選択されたテスト戦略

**テスト戦略**: UNIT_INTEGRATION（Unit + Integration）

**判断根拠**（設計書より）:
- **Unitテスト必要**: 新規分離モジュール（`openai_client.py`, `generator.py`, `cli.py`, `chunk_analyzer.py`）に対するユニットテストが必須
- **Integrationテスト必要**: 既存の統合テスト（`test_compatibility_layer.py`, `test_module_integration.py`）の維持・拡張が必要
- **BDDテスト不要**: 既存の`test_bdd_pr_comment_generation.py`でエンドツーエンドのシナリオが十分カバーされている
- OpenAI APIとの連携部分はモック化してユニットテストを実施

### 1.2 テスト対象の範囲

| モジュール | ファイル | 責務 | テスト種別 |
|----------|---------|------|-----------|
| OpenAIClient | `openai_client.py` | OpenAI API連携（リトライ、トークン管理） | Unit |
| PRCommentGenerator | `generator.py` | PRコメント生成コアロジック | Unit |
| ChunkAnalyzer | `chunk_analyzer.py` | チャンク分割・分析調整 | Unit |
| CLI | `cli.py` | CLIエントリポイント | Unit |
| モジュール間連携 | 複数 | OpenAIClient + ChunkAnalyzer + Generator連携 | Integration |
| 互換性レイヤー | `__init__.py` | 後方互換性維持 | Integration |

### 1.3 テストの目的

1. **信頼性の確保**: 各モジュールが仕様通りに動作することを保証
2. **回帰防止**: 既存機能が破壊されていないことを確認
3. **互換性維持**: 外部インターフェース（CLI、JSON出力）の後方互換性を検証
4. **カバレッジ目標**: 各新規モジュールで80%以上のコードカバレッジ達成

### 1.4 テストコード戦略

**BOTH_TEST**: 新規テスト作成 + 既存テスト拡張

| 種別 | アクション | 対象ファイル |
|------|-----------|-------------|
| CREATE_TEST | 新規作成 | `test_openai_client.py`, `test_generator.py`, `test_cli.py`, `test_chunk_analyzer.py` |
| EXTEND_TEST | 拡張 | `test_compatibility_layer.py`, `test_module_integration.py` |

---

## 2. Unitテストシナリオ

### 2.1 OpenAIClient テスト（test_openai_client.py）

#### 2.1.1 初期化テスト

**テストケース名**: `test_init_正常系_有効なAPIキー`

- **目的**: 有効なAPIキーでOpenAIClientが正常に初期化されることを検証
- **前提条件**: 環境変数`OPENAI_API_KEY`が設定されている
- **入力**:
  - `prompt_manager`: PromptTemplateManagerインスタンス
  - `retry_config`: None（デフォルト）
  - `log_level`: logging.INFO
- **期待結果**:
  - OpenAIClientインスタンスが作成される
  - デフォルトのリトライ設定（max_retries=5, initial_backoff=1, max_backoff=60）が適用される
- **テストデータ**:
  ```python
  os.environ['OPENAI_API_KEY'] = 'test-api-key-12345'
  prompt_manager = PromptTemplateManager()
  ```

---

**テストケース名**: `test_init_異常系_APIキー未設定`

- **目的**: APIキーが未設定の場合にエラーが発生することを検証
- **前提条件**: 環境変数`OPENAI_API_KEY`が設定されていない
- **入力**:
  - `prompt_manager`: PromptTemplateManagerインスタンス
- **期待結果**:
  - `ValueError`または適切な例外がスローされる
  - エラーメッセージに「OPENAI_API_KEY」が含まれる
- **テストデータ**:
  ```python
  del os.environ['OPENAI_API_KEY']  # またはモック
  ```

---

**テストケース名**: `test_init_正常系_カスタムリトライ設定`

- **目的**: カスタムリトライ設定が正しく適用されることを検証
- **前提条件**: 環境変数`OPENAI_API_KEY`が設定されている
- **入力**:
  - `retry_config`: `{'max_retries': 3, 'initial_backoff': 2, 'max_backoff': 30}`
- **期待結果**:
  - 指定されたリトライ設定が適用される
- **テストデータ**: 上記の設定辞書

---

#### 2.1.2 API呼び出しテスト

**テストケース名**: `test_call_api_正常系_成功`

- **目的**: API呼び出しが正常に成功することを検証
- **前提条件**:
  - OpenAIClientが初期化されている
  - OpenAI APIがモック化されている
- **入力**:
  - `messages`: `[{"role": "user", "content": "テストメッセージ"}]`
  - `max_tokens`: 2000
- **期待結果**:
  - APIレスポンスの文字列が返される
  - トークン使用量が記録される
- **テストデータ**:
  ```python
  mock_response = {
      "choices": [{"message": {"content": "テスト応答"}}],
      "usage": {"prompt_tokens": 10, "completion_tokens": 20}
  }
  ```

---

**テストケース名**: `test_call_api_正常系_リトライ成功`

- **目的**: 一時的なエラー後にリトライが成功することを検証
- **前提条件**:
  - OpenAIClientが初期化されている
  - 最初の2回の呼び出しは失敗、3回目で成功するようモック
- **入力**:
  - `messages`: `[{"role": "user", "content": "リトライテスト"}]`
- **期待結果**:
  - 最終的にAPIレスポンスが返される
  - リトライカウントが2として記録される
- **テストデータ**:
  ```python
  # 2回失敗後、成功するモック設定
  side_effects = [
      RateLimitError("Rate limit exceeded"),
      RateLimitError("Rate limit exceeded"),
      mock_success_response
  ]
  ```

---

**テストケース名**: `test_call_api_異常系_レート制限エラー`

- **目的**: レート制限エラーが適切に処理されることを検証
- **前提条件**:
  - OpenAIClientが初期化されている
  - 常にレート制限エラーを返すモック
- **入力**:
  - `messages`: `[{"role": "user", "content": "レート制限テスト"}]`
- **期待結果**:
  - 指数バックオフでリトライが実行される
  - 最大リトライ回数（5回）後に`APIMaxRetriesError`がスローされる
- **テストデータ**: モック化されたレート制限レスポンス

---

**テストケース名**: `test_call_api_異常系_最大リトライ超過`

- **目的**: 最大リトライ回数を超えた場合のエラー処理を検証
- **前提条件**:
  - `max_retries=3`で初期化されている
  - 常に失敗するモック
- **入力**:
  - `messages`: 任意のメッセージ
- **期待結果**:
  - 3回のリトライ後に`APIMaxRetriesError`がスローされる
  - エラーメッセージに試行回数が含まれる
- **テストデータ**: 常に失敗するモック

---

**テストケース名**: `test_call_api_境界値_空メッセージ`

- **目的**: 空のメッセージリストの処理を検証
- **前提条件**: OpenAIClientが初期化されている
- **入力**:
  - `messages`: `[]`
- **期待結果**:
  - 適切なエラーまたは空のレスポンスが返される
- **テストデータ**: 空のリスト

---

#### 2.1.3 入力準備テスト

**テストケース名**: `test_prepare_input_json_正常系`

- **目的**: PR情報とファイル変更からJSON入力が正しく作成されることを検証
- **前提条件**: OpenAIClientが初期化されている
- **入力**:
  - `pr_info`: PRInfoインスタンス
  - `changes`: FileChangeのリスト（3ファイル）
- **期待結果**:
  - JSON形式の文字列が返される
  - PR情報とファイル変更が含まれる
- **テストデータ**:
  ```python
  pr_info = PRInfo(
      title="テストPR",
      number=123,
      body="テスト説明",
      author="developer",
      base_branch="main",
      head_branch="feature/test",
      base_sha="abc123",
      head_sha="def456"
  )
  changes = [FileChange(...), FileChange(...), FileChange(...)]
  ```

---

**テストケース名**: `test_manage_input_size_正常系_制限内`

- **目的**: トークン制限内の入力がそのまま返されることを検証
- **前提条件**: OpenAIClientが初期化されている
- **入力**:
  - `input_json`: 短いJSON文字列（100トークン程度）
  - `max_tokens`: 1000
- **期待結果**:
  - 入力がそのまま返される（切り詰めなし）
- **テストデータ**: 短いJSON文字列

---

**テストケース名**: `test_manage_input_size_正常系_切り詰め`

- **目的**: トークン制限を超える入力が適切に切り詰められることを検証
- **前提条件**: OpenAIClientが初期化されている
- **入力**:
  - `input_json`: 長いJSON文字列（5000トークン程度）
  - `max_tokens`: 1000
- **期待結果**:
  - 入力が切り詰められる
  - 結果のトークン数が`max_tokens`以下
- **テストデータ**: 長いJSON文字列

---

#### 2.1.4 分析メソッドテスト

**テストケース名**: `test_analyze_chunk_正常系`

- **目的**: 単一チャンクの分析が正常に動作することを検証
- **前提条件**:
  - OpenAIClientが初期化されている
  - OpenAI APIがモック化されている
- **入力**:
  - `pr_info`: PRInfoインスタンス
  - `chunk`: FileChangeのリスト（2ファイル）
  - `chunk_index`: 0
- **期待結果**:
  - 分析結果の文字列が返される
  - プロンプトが正しく構築される
- **テストデータ**: サンプルPR情報とファイル変更

---

**テストケース名**: `test_analyze_chunk_異常系_APIエラー`

- **目的**: チャンク分析中のAPIエラー処理を検証
- **前提条件**:
  - OpenAIClientが初期化されている
  - APIが常にエラーを返すモック
- **入力**:
  - `pr_info`: PRInfoインスタンス
  - `chunk`: FileChangeのリスト
  - `chunk_index`: 0
- **期待結果**:
  - エラーメッセージを含む文字列が返される
  - または適切な例外がスローされる
- **テストデータ**: エラーモック

---

**テストケース名**: `test_generate_final_summary_正常系`

- **目的**: チャンク分析結果から最終サマリーが生成されることを検証
- **前提条件**: OpenAIClientが初期化されている
- **入力**:
  - `pr_info`: PRInfoインスタンス
  - `chunk_analyses`: `["チャンク1の分析結果", "チャンク2の分析結果"]`
  - `skipped_files`: `["large_file.bin"]`
- **期待結果**:
  - 最終サマリー文字列が返される
  - スキップされたファイルの情報が含まれる
- **テストデータ**: 複数のチャンク分析結果

---

**テストケース名**: `test_generate_final_summary_境界値_単一チャンク`

- **目的**: 単一チャンクの場合のサマリー生成を検証
- **前提条件**: OpenAIClientが初期化されている
- **入力**:
  - `pr_info`: PRInfoインスタンス
  - `chunk_analyses`: `["唯一のチャンク分析結果"]`
  - `skipped_files`: `[]`
- **期待結果**:
  - サマリーが正常に生成される
- **テストデータ**: 単一の分析結果

---

**テストケース名**: `test_generate_title_正常系`

- **目的**: サマリーからタイトルが生成されることを検証
- **前提条件**: OpenAIClientが初期化されている
- **入力**:
  - `summary`: "この PR は認証機能を追加します。JWT トークンとセッション管理を実装しています。"
- **期待結果**:
  - 簡潔なタイトル文字列が返される（50文字以下）
- **テストデータ**: 上記のサマリー

---

#### 2.1.5 ユーティリティテスト

**テストケース名**: `test_get_usage_stats_正常系`

- **目的**: トークン使用量統計が正しく取得されることを検証
- **前提条件**:
  - OpenAIClientが初期化されている
  - 複数のAPI呼び出しが実行済み
- **入力**: なし（メソッド呼び出し）
- **期待結果**:
  - `prompt_tokens`, `completion_tokens`, `retries`, `skipped_files`を含む辞書が返される
- **テストデータ**: 事前にAPI呼び出しを実行

---

**テストケース名**: `test_save_prompt_and_result_正常系_有効`

- **目的**: プロンプト保存が有効な場合にファイルが作成されることを検証
- **前提条件**:
  - 環境変数`SAVE_PROMPTS=true`
  - 環境変数`PROMPT_OUTPUT_DIR`が設定されている
- **入力**:
  - `prompt`: "テストプロンプト"
  - `result`: "テスト結果"
  - `chunk_index`: 1
  - `phase`: "chunk"
- **期待結果**:
  - 指定されたディレクトリにファイルが作成される
  - ファイル名にchunk_indexとphaseが含まれる
- **テストデータ**: 一時ディレクトリを使用

---

**テストケース名**: `test_save_prompt_and_result_正常系_無効`

- **目的**: プロンプト保存が無効な場合にファイルが作成されないことを検証
- **前提条件**: 環境変数`SAVE_PROMPTS`が未設定または`false`
- **入力**:
  - `prompt`: "テストプロンプト"
  - `result`: "テスト結果"
- **期待結果**:
  - ファイルが作成されない
  - エラーも発生しない
- **テストデータ**: 通常の入力

---

### 2.2 ChunkAnalyzer テスト（test_chunk_analyzer.py）

#### 2.2.1 初期化テスト

**テストケース名**: `test_init_正常系`

- **目的**: ChunkAnalyzerが正常に初期化されることを検証
- **前提条件**: 依存コンポーネントが利用可能
- **入力**:
  - `openai_client`: OpenAIClientインスタンス（モック）
  - `statistics`: PRCommentStatisticsインスタンス
  - `log_level`: logging.INFO
- **期待結果**:
  - ChunkAnalyzerインスタンスが作成される
- **テストデータ**: モック化された依存コンポーネント

---

#### 2.2.2 チャンクサイズ計算テスト

**テストケース名**: `test_calculate_optimal_chunk_size_正常系_小規模PR`

- **目的**: 小規模PRに対して適切なチャンクサイズが計算されることを検証
- **前提条件**: ChunkAnalyzerが初期化されている
- **入力**:
  - `changes`: 3ファイル、各100行変更
- **期待結果**:
  - チャンクサイズ >= 2（小規模なので複数ファイルをまとめられる）
- **テストデータ**:
  ```python
  changes = [
      FileChange(filename="file1.py", additions=50, deletions=50, ...),
      FileChange(filename="file2.py", additions=50, deletions=50, ...),
      FileChange(filename="file3.py", additions=50, deletions=50, ...)
  ]
  ```

---

**テストケース名**: `test_calculate_optimal_chunk_size_正常系_大規模PR`

- **目的**: 大規模PRに対して適切なチャンクサイズが計算されることを検証
- **前提条件**: ChunkAnalyzerが初期化されている
- **入力**:
  - `changes`: 20ファイル、各500行変更
- **期待結果**:
  - チャンクサイズ = 1〜2（大規模なので分割が必要）
- **テストデータ**: 大規模なファイル変更リスト

---

**テストケース名**: `test_calculate_optimal_chunk_size_境界値_空リスト`

- **目的**: 空のファイルリストに対するチャンクサイズ計算を検証
- **前提条件**: ChunkAnalyzerが初期化されている
- **入力**:
  - `changes`: `[]`
- **期待結果**:
  - デフォルト値（例: 1）が返される
  - エラーが発生しない
- **テストデータ**: 空のリスト

---

**テストケース名**: `test_calculate_optimal_chunk_size_境界値_単一ファイル`

- **目的**: 単一ファイルに対するチャンクサイズ計算を検証
- **前提条件**: ChunkAnalyzerが初期化されている
- **入力**:
  - `changes`: 1ファイルのみ
- **期待結果**:
  - チャンクサイズ = 1が返される
- **テストデータ**: 単一ファイルのリスト

---

#### 2.2.3 チャンク分割テスト

**テストケース名**: `test_split_into_chunks_正常系`

- **目的**: ファイルリストが正しくチャンクに分割されることを検証
- **前提条件**: ChunkAnalyzerが初期化されている
- **入力**:
  - `changes`: 10ファイル
  - `chunk_size`: 3
- **期待結果**:
  - 4つのチャンクが作成される（[3, 3, 3, 1]）
  - すべてのファイルがいずれかのチャンクに含まれる
- **テストデータ**: 10ファイルのリスト

---

**テストケース名**: `test_split_into_chunks_正常系_均等分割`

- **目的**: ファイル数がチャンクサイズで割り切れる場合の分割を検証
- **前提条件**: ChunkAnalyzerが初期化されている
- **入力**:
  - `changes`: 9ファイル
  - `chunk_size`: 3
- **期待結果**:
  - 3つの均等なチャンクが作成される（各3ファイル）
- **テストデータ**: 9ファイルのリスト

---

**テストケース名**: `test_split_into_chunks_境界値_チャンクサイズより少ないファイル`

- **目的**: ファイル数がチャンクサイズより少ない場合の処理を検証
- **前提条件**: ChunkAnalyzerが初期化されている
- **入力**:
  - `changes`: 2ファイル
  - `chunk_size`: 5
- **期待結果**:
  - 1つのチャンクに全ファイルが含まれる
- **テストデータ**: 2ファイルのリスト

---

#### 2.2.4 チャンク分析テスト

**テストケース名**: `test_analyze_all_chunks_正常系`

- **目的**: すべてのチャンクが正常に分析されることを検証
- **前提条件**:
  - ChunkAnalyzerが初期化されている
  - OpenAIClientがモック化されている
- **入力**:
  - `pr_info`: PRInfoインスタンス
  - `chunks`: 3つのチャンク
- **期待結果**:
  - 3つの分析結果が返される
  - 各分析結果が空でない
- **テストデータ**: 3つのチャンクに分割されたファイルリスト

---

**テストケース名**: `test_analyze_all_chunks_異常系_部分的失敗`

- **目的**: 一部のチャンク分析が失敗した場合の処理を検証
- **前提条件**:
  - ChunkAnalyzerが初期化されている
  - 2番目のチャンクでエラーが発生するモック
- **入力**:
  - `pr_info`: PRInfoインスタンス
  - `chunks`: 3つのチャンク
- **期待結果**:
  - 3つの結果が返される（2番目はエラーメッセージ）
  - 処理が継続される
- **テストデータ**: エラーを返すモック設定

---

**テストケース名**: `test_analyze_single_chunk_正常系`

- **目的**: 単一チャンクの分析が正常に動作することを検証
- **前提条件**:
  - ChunkAnalyzerが初期化されている
  - OpenAIClientがモック化されている
- **入力**:
  - `pr_info`: PRInfoインスタンス
  - `chunk`: FileChangeのリスト
  - `chunk_index`: 0
- **期待結果**:
  - 分析結果の文字列が返される
- **テストデータ**: サンプルチャンク

---

### 2.3 PRCommentGenerator テスト（test_generator.py）

#### 2.3.1 初期化テスト

**テストケース名**: `test_init_正常系`

- **目的**: PRCommentGeneratorが正常に初期化されることを検証
- **前提条件**: 依存環境変数が設定されている
- **入力**:
  - `log_level`: logging.INFO
- **期待結果**:
  - PRCommentGeneratorインスタンスが作成される
  - 依存コンポーネント（OpenAIClient, ChunkAnalyzer）が初期化される
- **テストデータ**: 環境変数の設定

---

#### 2.3.2 データ読み込みテスト

**テストケース名**: `test_load_pr_data_正常系`

- **目的**: PR情報とDiffが正しく読み込まれることを検証
- **前提条件**:
  - PRCommentGeneratorが初期化されている
  - 有効なJSONファイルが存在する
- **入力**:
  - `pr_info_path`: "tests/fixtures/sample_pr_info.json"
  - `pr_diff_path`: "tests/fixtures/sample_diff.json"
- **期待結果**:
  - PRInfoインスタンスが返される
  - FileChangeのリストが返される
  - スキップファイルリストが返される（空の場合もあり）
- **テストデータ**: 既存のfixtureファイル

---

**テストケース名**: `test_load_pr_data_異常系_ファイル不存在`

- **目的**: PR情報ファイルが存在しない場合のエラー処理を検証
- **前提条件**: PRCommentGeneratorが初期化されている
- **入力**:
  - `pr_info_path`: "non_existent_file.json"
  - `pr_diff_path`: "tests/fixtures/sample_diff.json"
- **期待結果**:
  - `PRDataLoadError`がスローされる
  - エラーメッセージにファイルパスが含まれる
- **テストデータ**: 存在しないファイルパス

---

**テストケース名**: `test_load_pr_data_異常系_無効なJSON`

- **目的**: 無効なJSONファイルの処理を検証
- **前提条件**: PRCommentGeneratorが初期化されている
- **入力**:
  - `pr_info_path`: 無効なJSONを含むファイル
- **期待結果**:
  - `PRDataLoadError`がスローされる
  - エラーメッセージにJSON解析エラーの情報が含まれる
- **テストデータ**: 無効なJSON文字列を含む一時ファイル

---

#### 2.3.3 ファイルフィルタリングテスト

**テストケース名**: `test_filter_large_files_正常系`

- **目的**: 大きなファイルが正しくフィルタリングされることを検証
- **前提条件**: PRCommentGeneratorが初期化されている
- **入力**:
  - `changes`: 大きなファイル（10000行）と小さなファイル（100行）の混合リスト
- **期待結果**:
  - 処理対象ファイルと除外ファイルの2つのリストが返される
  - 大きなファイルが除外リストに含まれる
- **テストデータ**:
  ```python
  changes = [
      FileChange(filename="small.py", additions=50, deletions=50, ...),
      FileChange(filename="large.py", additions=5000, deletions=5000, ...),
  ]
  ```

---

**テストケース名**: `test_filter_large_files_境界値_全て小さい`

- **目的**: すべてのファイルが小さい場合の処理を検証
- **前提条件**: PRCommentGeneratorが初期化されている
- **入力**:
  - `changes`: 小さなファイルのみ（各100行以下）
- **期待結果**:
  - 全ファイルが処理対象リストに含まれる
  - 除外リストが空
- **テストデータ**: 小さなファイルのリスト

---

**テストケース名**: `test_is_binary_file_正常系_バイナリ`

- **目的**: バイナリファイルが正しく識別されることを検証
- **前提条件**: PRCommentGeneratorが初期化されている
- **入力**:
  - `filename`: "image.png", "archive.zip", "document.pdf"
- **期待結果**:
  - `True`が返される
- **テストデータ**: 各種バイナリファイル拡張子

---

**テストケース名**: `test_is_binary_file_正常系_テキスト`

- **目的**: テキストファイルがバイナリとして識別されないことを検証
- **前提条件**: PRCommentGeneratorが初期化されている
- **入力**:
  - `filename`: "script.py", "config.json", "README.md"
- **期待結果**:
  - `False`が返される
- **テストデータ**: 各種テキストファイル拡張子

---

#### 2.3.4 コメント生成テスト

**テストケース名**: `test_generate_comment_正常系`

- **目的**: PRコメントが正常に生成されることを検証
- **前提条件**:
  - PRCommentGeneratorが初期化されている
  - OpenAI APIがモック化されている
- **入力**:
  - `pr_info_path`: 有効なPR情報ファイル
  - `pr_diff_path`: 有効なDiffファイル
- **期待結果**:
  - `comment`, `suggested_title`, `usage`を含む辞書が返される
  - コメントがMarkdown形式
- **テストデータ**: fixtureファイル

---

**テストケース名**: `test_generate_comment_正常系_スキップファイルあり`

- **目的**: スキップされたファイルがある場合のコメント生成を検証
- **前提条件**:
  - PRCommentGeneratorが初期化されている
  - 大きなファイルを含むDiff
- **入力**:
  - 大きなファイルを含むDiffファイル
- **期待結果**:
  - コメントにスキップファイル情報が含まれる
  - `skipped_files`リストが正しく設定される
- **テストデータ**: 大きなファイルを含むサンプル

---

**テストケース名**: `test_generate_comment_境界値_ファイルなし`

- **目的**: 変更ファイルがない場合の処理を検証
- **前提条件**: PRCommentGeneratorが初期化されている
- **入力**:
  - 空のDiffファイル
- **期待結果**:
  - 適切なメッセージを含む結果が返される
  - エラーが発生しない
- **テストデータ**: 空の配列を含むJSONファイル

---

#### 2.3.5 ファイルパス正規化テスト

**テストケース名**: `test_rebuild_file_section_正常系`

- **目的**: ファイルセクションの重複が正しく排除されることを検証
- **前提条件**: PRCommentGeneratorが初期化されている
- **入力**:
  - `comment`: 重複ファイル参照を含むコメント
  - `original_file_paths`: 元のファイルパスリスト
- **期待結果**:
  - 重複が排除されたコメントが返される
  - ファイルパスが正規化される
- **テストデータ**:
  ```python
  comment = """
  ## 変更ファイル
  - src/auth/login.py
  - src/auth/login.py  # 重複
  - auth/login.py      # 別表記
  """
  original_file_paths = ["src/auth/login.py", "src/auth/session.py"]
  ```

---

### 2.4 CLI テスト（test_cli.py）

#### 2.4.1 引数パーサーテスト

**テストケース名**: `test_create_argument_parser_正常系`

- **目的**: 引数パーサーが正しく作成されることを検証
- **前提条件**: なし
- **入力**: なし
- **期待結果**:
  - ArgumentParserインスタンスが返される
  - 必須引数（--pr-diff, --pr-info, --output）が定義されている
- **テストデータ**: なし

---

**テストケース名**: `test_parse_args_正常系_必須引数のみ`

- **目的**: 必須引数のみでパースが成功することを検証
- **前提条件**: 引数パーサーが作成されている
- **入力**:
  - `args`: `["--pr-diff", "diff.json", "--pr-info", "info.json", "--output", "out.json"]`
- **期待結果**:
  - Namespaceオブジェクトが返される
  - 各引数値が正しく設定される
- **テストデータ**: 上記の引数リスト

---

**テストケース名**: `test_parse_args_正常系_全オプション`

- **目的**: すべてのオプション引数でパースが成功することを検証
- **前提条件**: 引数パーサーが作成されている
- **入力**:
  ```python
  args = [
      "--pr-diff", "diff.json",
      "--pr-info", "info.json",
      "--output", "out.json",
      "--save-prompts",
      "--parallel",
      "--log-level", "DEBUG"
  ]
  ```
- **期待結果**:
  - すべてのオプションが正しく設定される
- **テストデータ**: 上記の引数リスト

---

**テストケース名**: `test_parse_args_異常系_必須引数不足`

- **目的**: 必須引数が不足している場合のエラー処理を検証
- **前提条件**: 引数パーサーが作成されている
- **入力**:
  - `args`: `["--pr-diff", "diff.json"]`  # --pr-info, --output が不足
- **期待結果**:
  - SystemExitが発生する
  - エラーメッセージに不足している引数名が含まれる
- **テストデータ**: 不完全な引数リスト

---

#### 2.4.2 環境変数設定テスト

**テストケース名**: `test_setup_environment_from_args_正常系`

- **目的**: 引数から環境変数が正しく設定されることを検証
- **前提条件**: なし
- **入力**:
  - `args.save_prompts`: True
  - `args.parallel`: True
  - `args.log_level`: "DEBUG"
- **期待結果**:
  - `SAVE_PROMPTS`環境変数が"true"に設定される
  - `PARALLEL_FETCH`環境変数が"true"に設定される
- **テストデータ**: Namespaceオブジェクト

---

**テストケース名**: `test_setup_environment_from_args_正常系_デフォルト`

- **目的**: デフォルト値の場合に環境変数が設定されないことを検証
- **前提条件**: なし
- **入力**:
  - `args.save_prompts`: False
  - `args.parallel`: False
- **期待結果**:
  - `SAVE_PROMPTS`環境変数が設定されない（または"false"）
- **テストデータ**: デフォルト値のNamespaceオブジェクト

---

#### 2.4.3 main関数テスト

**テストケース名**: `test_main_正常系`

- **目的**: main関数が正常に実行されることを検証
- **前提条件**:
  - 有効な入力ファイルが存在する
  - PRCommentGeneratorがモック化されている
- **入力**:
  - コマンドライン引数（sys.argvをモック）
- **期待結果**:
  - 出力ファイルが作成される
  - 終了コード0で終了
- **テストデータ**: fixtureファイルと一時出力ディレクトリ

---

**テストケース名**: `test_main_異常系_入力ファイル不存在`

- **目的**: 入力ファイルが存在しない場合のエラー処理を検証
- **前提条件**: 入力ファイルが存在しない
- **入力**:
  - 存在しないファイルパスを含む引数
- **期待結果**:
  - エラー情報を含むJSONが出力される
  - 適切なエラーメッセージが表示される
- **テストデータ**: 存在しないパス

---

**テストケース名**: `test_main_正常系_JSON出力形式`

- **目的**: 出力JSONの形式が正しいことを検証
- **前提条件**: main関数が正常に完了している
- **入力**: 出力されたJSONファイル
- **期待結果**:
  - 必須フィールド（comment, suggested_title, usage, pr_number）が含まれる
  - JSON形式が有効
- **テストデータ**: main関数の出力ファイル

---

**テストケース名**: `test_main_異常系_エラー出力形式`

- **目的**: エラー時の出力JSONの形式が正しいことを検証
- **前提条件**: main関数がエラーで終了
- **入力**: エラー時の出力ファイル
- **期待結果**:
  - `error`フィールドが含まれる
  - `traceback`フィールドが含まれる（オプション）
- **テストデータ**: エラーケースの出力

---

## 3. Integrationテストシナリオ

### 3.1 モジュール間連携テスト（test_module_integration.py 拡張）

#### 3.1.1 OpenAIClient + ChunkAnalyzer 連携

**シナリオ名**: `test_OpenAIClientとChunkAnalyzerの連携`

- **目的**: OpenAIClientとChunkAnalyzerが正しく連携してチャンク分析を行うことを検証
- **前提条件**:
  - 両モジュールがインポート可能
  - OpenAI APIがモック化されている
- **テスト手順**:
  1. PRCommentStatisticsを初期化
  2. OpenAIClient（モック）を初期化
  3. ChunkAnalyzerをOpenAIClientと共に初期化
  4. サンプルファイル変更リスト（10ファイル）を用意
  5. `calculate_optimal_chunk_size`を呼び出し
  6. `split_into_chunks`を呼び出し
  7. `analyze_all_chunks`を呼び出し
- **期待結果**:
  - チャンクサイズが適切に計算される
  - ファイルが正しく分割される
  - 各チャンクの分析結果が取得される
- **確認項目**:
  - [ ] チャンク数が期待通り
  - [ ] 分析結果の数がチャンク数と一致
  - [ ] OpenAIClient.analyze_chunkが正しい回数呼び出される

---

#### 3.1.2 Generator + OpenAIClient + ChunkAnalyzer 連携

**シナリオ名**: `test_Generator完全ワークフロー`

- **目的**: PRCommentGeneratorが依存モジュールと正しく連携してコメントを生成することを検証
- **前提条件**:
  - 全モジュールがインポート可能
  - 外部APIがモック化されている
  - fixtureファイルが存在
- **テスト手順**:
  1. PRCommentGenerator（モック依存）を初期化
  2. `load_pr_data`でPR情報を読み込み
  3. `generate_comment`を呼び出し
  4. 結果の構造を検証
- **期待結果**:
  - 完全な結果辞書が返される
  - コメントがMarkdown形式
  - 使用統計が含まれる
- **確認項目**:
  - [ ] `comment`フィールドが存在し空でない
  - [ ] `suggested_title`フィールドが存在
  - [ ] `usage`辞書に`prompt_tokens`, `completion_tokens`が含まれる
  - [ ] `pr_number`が正しい値
  - [ ] `file_count`と`processed_file_count`の整合性

---

#### 3.1.3 CLI → Generator 連携

**シナリオ名**: `test_CLIからGeneratorへの連携`

- **目的**: CLIモジュールがGeneratorを正しく呼び出し、結果を出力することを検証
- **前提条件**:
  - CLIモジュールとGeneratorがインポート可能
  - 入力ファイルが存在
  - 一時出力ディレクトリが利用可能
- **テスト手順**:
  1. sys.argvを必要な引数でモック
  2. main()関数を呼び出し
  3. 出力ファイルを読み込み
  4. JSON内容を検証
- **期待結果**:
  - 出力ファイルが作成される
  - JSON形式が有効
  - 必須フィールドが含まれる
- **確認項目**:
  - [ ] 出力ファイルが存在
  - [ ] JSONとしてパース可能
  - [ ] `comment`, `suggested_title`, `usage`が存在
  - [ ] エラーフィールドがない（正常終了時）

---

### 3.2 互換性レイヤーテスト（test_compatibility_layer.py 拡張）

#### 3.2.1 新モジュールのインポート確認

**シナリオ名**: `test_新モジュールのインポート確認`

- **目的**: 新規作成モジュールがパッケージから正しくインポートできることを検証
- **前提条件**: リファクタリングが完了している
- **テスト手順**:
  1. `from pr_comment_generator.openai_client import OpenAIClient`を実行
  2. `from pr_comment_generator.generator import PRCommentGenerator`を実行
  3. `from pr_comment_generator.chunk_analyzer import ChunkAnalyzer`を実行
  4. `from pr_comment_generator.cli import main`を実行
  5. 各クラス/関数が正しい型であることを確認
- **期待結果**:
  - すべてのインポートが成功
  - 型エラーなし
- **確認項目**:
  - [ ] OpenAIClientがクラス
  - [ ] PRCommentGeneratorがクラス
  - [ ] ChunkAnalyzerがクラス
  - [ ] mainが関数

---

#### 3.2.2 OpenAIClientの後方互換性

**シナリオ名**: `test_OpenAIClient後方互換性`

- **目的**: 既存コードでOpenAIClientが使用されている場合の互換性を検証
- **前提条件**:
  - 新旧両方のモジュール構造が利用可能
  - APIキーがモック設定されている
- **テスト手順**:
  1. 旧パス（`pr_comment_generator.OpenAIClient`）でインポート試行
  2. 新パス（`pr_comment_generator.openai_client.OpenAIClient`）でインポート
  3. 両方のクラスが同一であることを確認
  4. 基本的なメソッド呼び出しが動作することを確認
- **期待結果**:
  - 旧パスでは非推奨警告が表示される（またはエイリアスとして動作）
  - 新パスでは警告なし
  - 両方で同じ機能が利用可能
- **確認項目**:
  - [ ] 非推奨警告の適切な表示
  - [ ] メソッドの動作一致
  - [ ] インスタンス化成功

---

#### 3.2.3 Generatorの後方互換性

**シナリオ名**: `test_Generator後方互換性`

- **目的**: 既存コードでPRCommentGeneratorが使用されている場合の互換性を検証
- **前提条件**: 新旧両方のモジュール構造が利用可能
- **テスト手順**:
  1. 旧パスでインポート試行
  2. 新パスでインポート
  3. 同一機能の検証
- **期待結果**:
  - 互換性が維持される
  - 非推奨警告が適切に表示される
- **確認項目**:
  - [ ] クラス定義の一致
  - [ ] メソッドシグネチャの一致
  - [ ] 出力形式の一致

---

#### 3.2.4 CLIインターフェースの互換性

**シナリオ名**: `test_CLI引数の後方互換性`

- **目的**: 既存のCLI引数がリファクタリング後も動作することを検証
- **前提条件**: CLI が実行可能
- **テスト手順**:
  1. 既存の引数形式でCLIを呼び出し
     ```
     --pr-diff diff.json --pr-info info.json --output out.json
     ```
  2. 出力を検証
  3. オプション引数を追加して再度実行
     ```
     --save-prompts --parallel --log-level DEBUG
     ```
- **期待結果**:
  - すべての既存引数が認識される
  - 出力形式が維持される
- **確認項目**:
  - [ ] 必須引数が動作
  - [ ] オプション引数が動作
  - [ ] 出力JSONフィールドが一致

---

### 3.3 エラーハンドリング統合テスト

**シナリオ名**: `test_エラーハンドリングと復旧`

- **目的**: モジュール間でエラーが適切に伝播・処理されることを検証
- **前提条件**: 全モジュールが連携可能
- **テスト手順**:
  1. OpenAIClientでAPI エラーをシミュレート
  2. ChunkAnalyzerのエラー処理を確認
  3. Generatorでの最終エラーハンドリングを確認
  4. CLIでのエラー出力形式を確認
- **期待結果**:
  - エラーが適切にログ出力される
  - 部分的な成功が可能な場合は継続処理
  - 最終出力にエラー情報が含まれる
- **確認項目**:
  - [ ] スタックトレースがログに出力
  - [ ] エラーJSON形式が正しい
  - [ ] リトライが適切に実行される

---

## 4. テストデータ

### 4.1 既存フィクスチャ（再利用）

| ファイル | 内容 | 用途 |
|---------|------|------|
| `tests/fixtures/sample_pr_info.json` | サンプルPR情報 | PR読み込みテスト |
| `tests/fixtures/sample_diff.json` | サンプルDiff（5ファイル） | Diff読み込みテスト |

### 4.2 新規テストデータ

#### 4.2.1 大規模PR用テストデータ

```json
// tests/fixtures/large_pr_diff.json
[
  {
    "filename": "src/module1.py",
    "status": "modified",
    "additions": 500,
    "deletions": 200,
    "changes": 700,
    "patch": "...(大量のパッチ内容)..."
  },
  // ... 50ファイル分
]
```

#### 4.2.2 バイナリファイルを含むテストデータ

```json
// tests/fixtures/binary_files_diff.json
[
  {
    "filename": "assets/image.png",
    "status": "added",
    "additions": 0,
    "deletions": 0,
    "changes": 0,
    "patch": null
  },
  {
    "filename": "src/script.py",
    "status": "modified",
    "additions": 50,
    "deletions": 10,
    "changes": 60,
    "patch": "..."
  }
]
```

#### 4.2.3 エラーケース用テストデータ

```json
// tests/fixtures/invalid_pr_info.json
{
  "title": "Missing fields",
  // number フィールドなし
  // body フィールドなし
}
```

#### 4.2.4 空のPRテストデータ

```json
// tests/fixtures/empty_diff.json
[]
```

### 4.3 モックデータ

#### 4.3.1 OpenAI API成功レスポンス

```python
mock_success_response = {
    "id": "chatcmpl-123",
    "object": "chat.completion",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "## PRサマリー\n\nこのPRは認証機能を追加します。\n\n### 主な変更点\n- JWTトークン実装\n- セッション管理"
            },
            "finish_reason": "stop"
        }
    ],
    "usage": {
        "prompt_tokens": 150,
        "completion_tokens": 80,
        "total_tokens": 230
    }
}
```

#### 4.3.2 OpenAI API レート制限レスポンス

```python
mock_rate_limit_error = {
    "error": {
        "message": "Rate limit reached for requests. Please retry after 20 seconds.",
        "type": "rate_limit_error",
        "code": "rate_limit_exceeded"
    }
}
```

---

## 5. テスト環境要件

### 5.1 ローカル開発環境

| 要件 | 詳細 |
|------|------|
| **Python** | 3.8以上 |
| **pytest** | 7.0以上 |
| **pytest-cov** | カバレッジ測定用 |
| **pytest-mock** | モック用 |

### 5.2 CI/CD環境

| 要件 | 詳細 |
|------|------|
| **実行環境** | GitHub Actions または Jenkins |
| **Pythonバージョン** | 3.8, 3.9, 3.10 でマトリックステスト |
| **カバレッジレポート** | Codecov または同等のサービス |

### 5.3 外部サービス・データベース

| サービス | テスト時の対応 |
|---------|---------------|
| **OpenAI API** | unittest.mockまたはpytest-mockでモック化 |
| **GitHub API** | モック化（github_utils.pyのGitHubClient） |

### 5.4 モック/スタブの必要性

| コンポーネント | モック方法 | 理由 |
|--------------|-----------|------|
| OpenAI API | `unittest.mock.patch` | 外部依存の分離、コスト削減 |
| ファイルシステム | `tempfile`, `pytest-tmpdir` | テスト間の独立性確保 |
| 環境変数 | `monkeypatch` | テスト設定の分離 |
| ログ出力 | `caplog` fixture | ログ出力の検証 |

---

## 6. テスト実行コマンド

### 6.1 全テスト実行

```bash
# カレントディレクトリ: pull-request-comment-builder/
pytest tests/ -v --cov=src/pr_comment_generator --cov-report=html
```

### 6.2 Unitテストのみ

```bash
pytest tests/unit/ -v -m unit
```

### 6.3 Integrationテストのみ

```bash
pytest tests/integration/ -v -m integration
```

### 6.4 特定モジュールのテスト

```bash
# OpenAIClientのテスト
pytest tests/unit/test_openai_client.py -v

# Generatorのテスト
pytest tests/unit/test_generator.py -v
```

### 6.5 カバレッジ確認

```bash
pytest tests/unit/ --cov=src/pr_comment_generator --cov-report=term-missing --cov-fail-under=80
```

---

## 7. 品質ゲート確認

### 7.1 Phase 2の戦略準拠

- [x] **UNIT_INTEGRATION戦略に沿ったテストシナリオである**
  - Unitテスト: 4モジュール × 各10〜15ケース = 約50ケース
  - Integrationテスト: 7シナリオ
  - BDDテスト: 既存テストで十分（追加不要）

### 7.2 正常系カバレッジ

- [x] **主要な正常系がカバーされている**
  - 初期化: 全モジュールの正常初期化
  - 主要機能: API呼び出し、チャンク分割、コメント生成、CLI実行
  - データフロー: PR読み込み → 分析 → 出力

### 7.3 異常系カバレッジ

- [x] **主要な異常系がカバーされている**
  - 入力エラー: ファイル不存在、無効なJSON、必須引数不足
  - 外部エラー: APIエラー、レート制限、最大リトライ超過
  - 境界値: 空リスト、単一要素、大規模データ

### 7.4 期待結果の明確さ

- [x] **期待結果が明確である**
  - 各テストケースに具体的な期待結果を記載
  - 検証可能な条件（戻り値、例外、ログ出力）を明記
  - 確認項目をチェックリスト形式で提供

---

## 8. 変更履歴

| 日付 | バージョン | 変更内容 | 作成者 |
|------|-----------|----------|--------|
| 2025年 | 1.0.0 | 初版作成 | AI Workflow Test Scenario Agent |

---

## 9. 承認

本テストシナリオは、Issue #528 の実装に関する詳細なテスト計画を提供します。
実装フェーズでは、このシナリオに基づいてテストコードを作成してください。

**作成日**: 2025年
**作成者**: AI Workflow Test Scenario Agent
**関連Issue**: [#528](https://github.com/tielec/infrastructure-as-code/issues/528)
