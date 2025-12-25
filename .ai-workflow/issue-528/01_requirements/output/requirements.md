# 要件定義書: Issue #528

## ファイルサイズの削減: pr_comment_generator.py

---

## 0. Planning Documentの確認

本要件定義書は、Planning Phase（`.ai-workflow/issue-528/00_planning/output/planning.md`）で策定された開発計画に基づいています。

### Planning Documentの要点

| 項目 | 決定事項 |
|------|----------|
| **複雑度** | 複雑（1985行の大規模単一ファイル） |
| **見積もり工数** | 32〜48時間 |
| **リスク評価** | 高（既存パイプライン使用中、外部API連携複雑） |
| **実装戦略** | REFACTOR（既存コードの構造改善） |
| **テスト戦略** | UNIT_INTEGRATION（新規ユニットテスト＋既存統合テスト拡張） |
| **テストコード戦略** | BOTH_TEST（新規作成＋既存拡張） |

### 既存モジュール化状況

Planning Documentの分析により、以下のモジュールは既に分離済みであることが確認されています：

| モジュール | 行数 | 責務 | 状態 |
|----------|------|------|------|
| `models.py` | 80行 | データモデル（PRInfo, FileChange） | 分離済み |
| `token_estimator.py` | 87行 | トークン推定 | 分離済み |
| `prompt_manager.py` | 122行 | プロンプトテンプレート管理 | 分離済み |
| `statistics.py` | 149行 | 統計処理 | 分離済み |
| `formatter.py` | 254行 | フォーマット処理 | 分離済み |
| `__init__.py` | 50行 | 互換性レイヤー | 分離済み |

### 新規分離対象

| モジュール | 責務 | 対象行範囲（メインファイル） |
|----------|------|---------------------------|
| `openai_client.py` | OpenAI API連携（リトライ、トークン管理） | 174〜1424行 |
| `generator.py` | PRコメント生成コアロジック | 1426〜1907行 |
| `cli.py` | CLIエントリポイント | 1909〜1985行 |
| `chunk_analyzer.py` | チャンク分析ロジック | OpenAIClient内から抽出 |

---

## 1. 概要

### 1.1 背景

`pr_comment_generator.py`は、Pull Requestの差分を分析してAIによるコメントを自動生成するPythonスクリプトです。現在、このファイルは1985行の単一ファイルとして実装されており、以下の5つの責務が混在しています：

1. **解析ロジック**: PR差分の解析、チャンク分割
2. **データモデル生成**: PRInfo、FileChangeなどのデータ構造
3. **OpenAI API連携**: API呼び出し、リトライ、トークン管理
4. **プロンプト構築**: テンプレート管理、プロンプト生成
5. **CLIエントリポイント**: コマンドライン引数解析、出力処理

### 1.2 目的

本リファクタリングの目的は以下の通りです：

- **保守性の向上**: 責務の明確な分離により、変更影響範囲の特定を容易にする
- **テスト容易性の向上**: 単一責務のモジュールにより、ユニットテストを容易にする
- **開発速度の回復**: 並行開発が可能なモジュール構造を実現する
- **信頼性の向上**: 各モジュールの独立したテストにより、回帰リスクを低減する

### 1.3 ビジネス価値・技術的価値

| 観点 | 価値 |
|------|------|
| **開発効率** | モジュール単位での修正・拡張が可能になり、開発サイクルが短縮 |
| **品質向上** | テストカバレッジ向上により、本番障害リスクが低減 |
| **チーム生産性** | 責務分離により、複数開発者の並行作業が可能 |
| **将来拡張性** | OpenAIクライアントの差し替え、新規CLI機能の追加が容易 |

---

## 2. 機能要件

### 2.1 モジュール分割要件

#### FR-001: OpenAIClientの分離（優先度: 高）

**説明**: OpenAI API連携ロジックを独立したモジュール`openai_client.py`に分離する。

**詳細要件**:
- [ ] APIリクエスト処理の分離
- [ ] 指数バックオフリトライロジックの分離
- [ ] トークン使用量管理の分離
- [ ] プロンプト保存機能の分離
- [ ] チャンク分析メソッド（`_analyze_chunk`、`_generate_final_summary`など）の分離
- [ ] 型ヒントの完全な付与

**受け入れ基準**:
```
Given: pr_comment_generator.pyからOpenAI関連コードを抽出済み
When: openai_client.pyモジュールとして独立させる
Then:
  - OpenAIClient クラスが openai_client.py で定義されている
  - すべての公開メソッドに型ヒントが付与されている
  - 既存の統合テストがパスする
  - 新規ユニットテストでカバレッジ80%以上
```

#### FR-002: PRCommentGeneratorの分離（優先度: 高）

**説明**: PRコメント生成のコアロジックを独立したモジュール`generator.py`に分離する。

**詳細要件**:
- [ ] `PRCommentGenerator`クラスの抽出
- [ ] PR データ読み込みロジック（`load_pr_data`）の分離
- [ ] ファイルフィルタリングロジック（`_filter_large_files`、`_is_binary_file`）の分離
- [ ] ファイルパス正規化ロジック（`_normalize_file_paths`、`_rebuild_file_section`）の分離
- [ ] コメント生成メインロジック（`generate_comment`）の分離
- [ ] OpenAIClient への依存を注入可能にする

**受け入れ基準**:
```
Given: pr_comment_generator.pyからPRCommentGeneratorクラスを抽出済み
When: generator.pyモジュールとして独立させる
Then:
  - PRCommentGenerator クラスが generator.py で定義されている
  - OpenAIClient を依存注入できる設計になっている
  - 既存の統合テスト・BDDテストがパスする
  - 新規ユニットテストでカバレッジ80%以上
```

#### FR-003: CLIエントリポイントの分離（優先度: 中）

**説明**: コマンドライン処理を独立したモジュール`cli.py`に分離する。

**詳細要件**:
- [ ] `main()`関数の抽出
- [ ] 引数パーサー（`argparse`）設定の分離
- [ ] 環境変数オーバーライドロジックの分離
- [ ] エラーハンドリングとJSON出力処理の分離
- [ ] 新しいエントリポイントスクリプトの作成

**受け入れ基準**:
```
Given: pr_comment_generator.pyからmain関数を抽出済み
When: cli.pyモジュールとして独立させる
Then:
  - main() 関数が cli.py で定義されている
  - 既存のCLIインターフェースが維持されている
  - コマンドライン引数の動作が変更されていない
  - 新規ユニットテストでカバレッジ80%以上
```

#### FR-004: ChunkAnalyzerの分離（優先度: 中）

**説明**: チャンク分析ロジックを独立したモジュール`chunk_analyzer.py`に分離する。

**詳細要件**:
- [ ] チャンク分割ロジック（`_split_changes_into_chunks`）の抽出
- [ ] 最適チャンクサイズ計算（`_calculate_optimal_chunk_size`）の抽出
- [ ] 入力サイズ管理ロジックの抽出
- [ ] 型ヒントの完全な付与

**受け入れ基準**:
```
Given: OpenAIClientからチャンク関連メソッドを抽出済み
When: chunk_analyzer.pyモジュールとして独立させる
Then:
  - ChunkAnalyzer クラスが chunk_analyzer.py で定義されている
  - OpenAIClient から呼び出し可能な設計になっている
  - 新規ユニットテストでカバレッジ80%以上
```

### 2.2 互換性維持要件

#### FR-005: 後方互換性の維持（優先度: 高）

**説明**: 既存のインポートパスと外部インターフェースを維持する。

**詳細要件**:
- [ ] `from pr_comment_generator import *`形式のインポートが引き続き機能する
- [ ] 非推奨警告を適切に表示する
- [ ] CLIインターフェース（引数、出力形式）を変更しない
- [ ] 出力JSONの形式を維持する

**受け入れ基準**:
```
Given: リファクタリング後のモジュール構造
When: 既存のインポートパスを使用する
Then:
  - 非推奨警告が表示される
  - クラス・関数が正常に利用可能
  - 既存の test_compatibility_layer.py のテストがすべてパスする
```

#### FR-006: __init__.pyの更新（優先度: 高）

**説明**: パッケージの`__init__.py`を更新して新モジュールをエクスポートする。

**詳細要件**:
- [ ] 新モジュール（`openai_client.py`、`generator.py`、`cli.py`、`chunk_analyzer.py`）のエクスポート追加
- [ ] `__all__`リストの更新
- [ ] 非推奨警告の更新
- [ ] バージョン情報の更新

**受け入れ基準**:
```
Given: 新モジュールが作成されている
When: __init__.py を更新する
Then:
  - 新しいクラス（OpenAIClient, PRCommentGenerator, ChunkAnalyzer）がエクスポートされる
  - 旧インポートパスでも新クラスにアクセス可能
  - バージョンが適切に更新されている
```

---

## 3. 非機能要件

### 3.1 パフォーマンス要件

#### NFR-001: 実行時間の維持

**要件**: リファクタリング後も、PR分析の実行時間が現状と同等以下であること。

**測定基準**:
- 既存の実行時間をベースラインとして測定
- リファクタリング後の実行時間がベースラインの110%以内

#### NFR-002: メモリ使用量の維持

**要件**: リファクタリング後も、メモリ使用量が現状と同等以下であること。

**測定基準**:
- モジュール分割によるインポートオーバーヘッドを最小化
- 大規模PRの処理時にメモリリークが発生しない

### 3.2 信頼性要件

#### NFR-003: エラーハンドリングの維持

**要件**: 既存のエラーハンドリング動作を維持する。

**詳細**:
- OpenAI API障害時のリトライロジックが正常に機能する
- GitHub API障害時の部分継続処理が正常に機能する
- 出力JSONにエラー情報が適切に含まれる

#### NFR-004: ロギングの維持

**要件**: 既存のロギング出力形式・レベルを維持する。

**詳細**:
- 各モジュールで独立したロガーを使用
- ログフォーマットを統一（`%(asctime)s - %(name)s - %(levelname)s - %(message)s`）

### 3.3 保守性要件

#### NFR-005: コードカバレッジ

**要件**: 新規作成モジュールのテストカバレッジを80%以上とする。

**詳細**:
- `openai_client.py`: 80%以上
- `generator.py`: 80%以上
- `cli.py`: 80%以上
- `chunk_analyzer.py`: 80%以上

#### NFR-006: ドキュメント

**要件**: 各モジュールに適切なdocstringを付与する。

**詳細**:
- モジュールdocstring: モジュールの目的と責務を説明
- クラスdocstring: クラスの役割と使用方法を説明
- メソッドdocstring: パラメータ、戻り値、例外を説明

### 3.4 拡張性要件

#### NFR-007: 依存逆転の原則

**要件**: モジュール間の依存関係を適切に管理し、将来の拡張を容易にする。

**詳細**:
- OpenAIClientを抽象化し、将来的な別AIプロバイダー対応を可能にする
- PRCommentGeneratorがOpenAIClientを依存注入として受け取る設計

---

## 4. 制約事項

### 4.1 技術的制約

| 制約 | 詳細 |
|------|------|
| **Python バージョン** | Python 3.8以上で動作すること |
| **依存ライブラリ** | 新規依存を追加しない（既存: openai, dataclasses） |
| **ファイル構造** | `src/pr_comment_generator/`パッケージ内に配置 |
| **外部API** | OpenAI API、GitHub APIとの連携を維持 |

### 4.2 既存システムとの整合性

| 制約 | 詳細 |
|------|------|
| **Jenkins パイプライン** | 既存のJenkinsジョブが変更なしで動作すること |
| **CLI インターフェース** | 引数、出力形式を変更しない |
| **出力JSON形式** | 既存のフィールド構成を維持 |
| **GitHub連携** | github_utils.pyとの連携を維持 |

### 4.3 コーディング規約

| 規約 | 詳細 |
|------|------|
| **コメント言語** | 日本語でコメントを記述 |
| **型ヒント** | すべての公開メソッドに型ヒントを付与 |
| **命名規則** | snake_case（変数・関数）、PascalCase（クラス） |
| **ファイルヘッダー** | 各ファイルにモジュールの目的を記述したdocstring |

---

## 5. 前提条件

### 5.1 システム環境

| 項目 | 条件 |
|------|------|
| **Python** | 3.8以上 |
| **OS** | Linux（Amazon Linux 2023推奨） |
| **実行環境** | Jenkins パイプライン内のDockerコンテナ |

### 5.2 依存コンポーネント

| コンポーネント | 役割 | 依存内容 |
|--------------|------|----------|
| `github_utils.py` | GitHub API連携 | GitHubClient クラスの使用 |
| `templates/` | プロンプトテンプレート | base_template.md, chunk_analysis_extension.md, summary_extension.md |
| OpenAI API | AI処理 | GPT-4モデルの呼び出し |

### 5.3 外部システム連携

| システム | 連携内容 |
|---------|----------|
| **OpenAI API** | PR分析のためのAI処理 |
| **GitHub API** | PRデータ、ファイル内容の取得 |
| **Jenkins** | パイプラインからの呼び出し、環境変数の提供 |

---

## 6. 受け入れ基準

### 6.1 機能要件の受け入れ基準

#### AC-001: OpenAIClient分離の受け入れ基準

```gherkin
Feature: OpenAIClientモジュールの分離

  Scenario: OpenAIClientが独立してインポート可能
    Given リファクタリングが完了している
    When "from pr_comment_generator.openai_client import OpenAIClient"を実行する
    Then OpenAIClientクラスがインポートされる
    And 型エラーが発生しない

  Scenario: APIリクエストが正常に動作する
    Given OpenAIClientインスタンスが作成されている
    And OPENAI_API_KEY環境変数が設定されている
    When _call_openai_apiメソッドを呼び出す
    Then OpenAI APIにリクエストが送信される
    And レスポンスが返却される

  Scenario: リトライロジックが正常に動作する
    Given OpenAIClientインスタンスが作成されている
    When API呼び出しがレート制限エラーを返す
    Then 指数バックオフでリトライが実行される
    And 最大リトライ回数後に例外がスローされる
```

#### AC-002: PRCommentGenerator分離の受け入れ基準

```gherkin
Feature: PRCommentGeneratorモジュールの分離

  Scenario: PRCommentGeneratorが独立してインポート可能
    Given リファクタリングが完了している
    When "from pr_comment_generator.generator import PRCommentGenerator"を実行する
    Then PRCommentGeneratorクラスがインポートされる

  Scenario: PRデータの読み込みが正常に動作する
    Given PRCommentGeneratorインスタンスが作成されている
    And 有効なPR情報とDiff情報のJSONファイルが存在する
    When load_pr_dataメソッドを呼び出す
    Then PRInfo、FileChangeのリスト、スキップファイルリストが返却される

  Scenario: コメント生成が正常に動作する
    Given PRCommentGeneratorインスタンスが作成されている
    And 有効なPRデータが読み込まれている
    When generate_commentメソッドを呼び出す
    Then コメント、タイトル、使用統計を含む辞書が返却される
```

#### AC-003: CLI分離の受け入れ基準

```gherkin
Feature: CLIモジュールの分離

  Scenario: CLIが既存の引数で動作する
    Given リファクタリングが完了している
    When "--pr-diff", "--pr-info", "--output"引数でCLIを実行する
    Then 正常に実行が完了する
    And 出力JSONファイルが生成される

  Scenario: 既存の環境変数オーバーライドが動作する
    Given "--save-prompts"フラグが指定されている
    When CLIを実行する
    Then SAVE_PROMPTS環境変数がtrueに設定される
    And プロンプトファイルが出力される
```

### 6.2 互換性の受け入れ基準

#### AC-004: 後方互換性の受け入れ基準

```gherkin
Feature: 後方互換性の維持

  Scenario: 旧インポートパスが動作する
    Given リファクタリングが完了している
    When "from pr_comment_generator import PRInfo, FileChange"を実行する
    Then クラスが正常にインポートされる
    And 非推奨警告が表示される

  Scenario: 既存テストがすべてパスする
    Given リファクタリングが完了している
    When test_compatibility_layer.pyを実行する
    Then すべてのテストがパスする

  Scenario: 既存BDDテストがすべてパスする
    Given リファクタリングが完了している
    When test_bdd_pr_comment_generation.pyを実行する
    Then すべてのテストがパスする
```

### 6.3 品質の受け入れ基準

#### AC-005: テストカバレッジの受け入れ基準

```gherkin
Feature: テストカバレッジ目標

  Scenario: 新規モジュールのカバレッジ達成
    Given すべての新規モジュールにユニットテストが作成されている
    When pytestでカバレッジを測定する
    Then openai_client.pyのカバレッジが80%以上
    And generator.pyのカバレッジが80%以上
    And cli.pyのカバレッジが80%以上
    And chunk_analyzer.pyのカバレッジが80%以上
```

---

## 7. スコープ外

### 7.1 本リファクタリングのスコープ外

以下の項目は本リファクタリングのスコープ外とします：

| 項目 | 理由 |
|------|------|
| **機能追加** | 本Issueはリファクタリングのみを対象 |
| **OpenAI API以外のAIプロバイダー対応** | 将来の拡張として検討 |
| **新規CLI引数の追加** | 既存インターフェースの維持を優先 |
| **パフォーマンス最適化** | 別Issueで対応 |
| **github_utils.pyのリファクタリング** | 別モジュールのため対象外 |

### 7.2 将来的な拡張候補

以下は将来的な拡張候補として記録します：

1. **抽象AIクライアントインターフェース**: OpenAI以外のプロバイダー対応
2. **プラグインアーキテクチャ**: 分析ロジックの拡張性向上
3. **非同期処理**: API呼び出しの非同期化によるパフォーマンス向上
4. **設定ファイル対応**: YAML/TOML形式の設定ファイルサポート

---

## 8. 品質ゲート確認

本要件定義書は以下の品質ゲートを満たしています：

- [x] **機能要件が明確に記載されている**
  - 6つの機能要件（FR-001〜FR-006）が定義されている
  - 各要件に詳細な要件リストが含まれている

- [x] **受け入れ基準が定義されている**
  - 5つの受け入れ基準（AC-001〜AC-005）がGherkin形式で定義されている
  - 各シナリオにGiven-When-Then形式の検証ステップが含まれている

- [x] **スコープが明確である**
  - セクション7で明確にスコープ外事項が定義されている
  - 将来拡張候補も記載されている

- [x] **論理的な矛盾がない**
  - 機能要件と受け入れ基準が対応している
  - 非機能要件と制約事項に矛盾がない
  - Planning Documentと整合している

---

## 9. 変更履歴

| 日付 | バージョン | 変更内容 | 作成者 |
|------|-----------|----------|--------|
| 2025年 | 1.0.0 | 初版作成 | AI Workflow Requirements Agent |

---

## 10. 承認

本要件定義書は、Issue #528 の実装に関する詳細な要件を提供します。
設計フェーズ開始前に、ステークホルダーの承認を得てください。

**作成日**: 2025年
**作成者**: AI Workflow Requirements Agent
**関連Issue**: [#528](https://github.com/tielec/infrastructure-as-code/issues/528)
