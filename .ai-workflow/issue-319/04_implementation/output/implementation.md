# 実装ログ - Issue #319

## 実装サマリー
- **実装戦略**: EXTEND
- **変更ファイル数**: 2個
- **新規作成ファイル数**: 1個
- **実装フェーズ**: Phase 4（実コードのみ、テストコードは Phase 5）

## 変更ファイル一覧

### 新規作成
- `scripts/ai-workflow/utils/dependency_validator.py`: フェーズ依存関係検証モジュール

### 修正
- `scripts/ai-workflow/main.py`: CLIオプション追加、個別フェーズ実行時の依存関係チェック統合
- `scripts/ai-workflow/phases/base_phase.py`: `run()` メソッドに依存関係チェックを統合

## 実装詳細

### ファイル1: scripts/ai-workflow/utils/dependency_validator.py（新規作成）

**変更内容**:
1. **PHASE_DEPENDENCIES 定数**: 全フェーズの依存関係を辞書形式で定義
   - `planning`: 依存なし
   - `requirements`: 依存なし
   - `design`: `['requirements']`
   - `test_scenario`: `['requirements', 'design']`
   - `implementation`: `['requirements', 'design', 'test_scenario']`
   - `test_implementation`: `['implementation']`
   - `testing`: `['implementation', 'test_implementation']`
   - `documentation`: `['implementation']`
   - `report`: `['requirements', 'design', 'implementation', 'testing', 'documentation']`
   - `evaluation`: `['report']`

2. **DependencyError クラス**: カスタム例外クラス
   - `phase_name`: 実行しようとしているフェーズ名
   - `missing_phases`: 未完了の依存フェーズリスト
   - `message`: 自動生成されるエラーメッセージ（単一/複数フェーズ対応）

3. **validate_phase_dependencies() 関数**: 依存関係検証ロジック
   - `skip_check`: 依存関係チェックをスキップ（--skip-dependency-check）
   - `ignore_violations`: 警告のみ表示して継続（--ignore-dependencies）
   - 依存フェーズのステータスを `metadata.get_phase_status()` で確認
   - 未完了フェーズが存在する場合、DependencyError を発生

4. **ユーティリティ関数**:
   - `get_phase_dependencies()`: 指定フェーズの依存関係リストを取得
   - `get_all_phase_dependencies()`: 全フェーズの依存関係定義を取得

**理由**:
- 設計書7.1節の「新規モジュール: utils/dependency_validator.py」に従って実装
- フェーズ依存関係を一箇所で管理し、保守性を向上
- エラーハンドリングとログ出力を適切に実装

**注意点**:
- `PHASE_DEPENDENCIES` は要件定義書の付録A（フェーズ依存関係図）に基づいて定義
- `metadata.get_phase_status()` は既存の `MetadataManager` クラスのメソッド（87-97行目）を使用
- 将来的に新しいフェーズを追加する場合、`PHASE_DEPENDENCIES` に1行追加するのみで対応可能

---

### ファイル2: scripts/ai-workflow/main.py（修正）

**変更内容**:

#### 2.1 CLIオプション追加（607-628行目）
`execute` コマンドに以下のオプションを追加：
- `--skip-dependency-check`: 依存関係チェックをスキップ
- `--ignore-dependencies`: 依存関係違反時も警告のみ表示して継続
- `--preset`: プリセット実行（requirements-only, design-phase, implementation-phase, full-workflow）

#### 2.2 オプション排他性チェック（630-638行目）
- `--preset` と `--phase` の同時指定をエラーとする
- `--skip-dependency-check` と `--ignore-dependencies` の同時指定をエラーとする
- エラーメッセージを表示して `sys.exit(1)` で終了

#### 2.3 プリセット処理（640-651行目）
プリセットに応じて `phase` を上書き：
- `requirements-only` → `requirements`
- `design-phase` → `design`
- `implementation-phase` → `implementation`
- `full-workflow` → `all`

#### 2.4 個別フェーズ実行時の依存関係チェック（853-876行目）
`phase != 'all'` の場合、依存関係チェックを実施：
- `validate_phase_dependencies()` を呼び出し
- DependencyError 発生時、エラーメッセージとヒントを表示して終了
- その他の例外も適切にハンドリング

**理由**:
- 設計書7.2節の「既存モジュール修正: main.py」に従って実装
- 既存の `execute` コマンドを拡張し、依存関係チェック機能を追加
- ユーザビリティを考慮し、エラーメッセージにヒントを含める

**注意点**:
- `phase == 'all'` の場合は依存関係チェックを実施しない（順次実行のため問題なし）
- プリセット実行時は、プリセットに応じたフェーズが自動選択される
- エラーハンドリングは既存コードのスタイルに合わせて実装

---

### ファイル3: scripts/ai-workflow/phases/base_phase.py（修正）

**変更内容**:

#### 3.1 run() メソッドに依存関係チェックを統合（643-670行目）
フェーズ実行前に依存関係チェックを実施：
- `validate_phase_dependencies()` を呼び出し
- メタデータから `skip_dependency_check` と `ignore_dependencies` フラグを取得（将来拡張用）
- DependencyError 発生時、フェーズステータスを `failed` に更新し、GitHub に進捗報告
- `return False` で終了

#### 3.2 防御的チェック
- main.py で CLI 実行前にチェック済みだが、`BasePhase.run()` が直接呼ばれる場合（テスト等）に備えて防御的にチェック
- メタデータから `skip_dependency_check` と `ignore_dependencies` フラグを取得（デフォルト: False）

**理由**:
- 設計書7.3節の「既存モジュール修正: phases/base_phase.py」に従って実装
- フェーズ実行前に依存関係チェックを自動的に実施
- 二重チェック防止のため、main.py で実施済みの場合はメタデータからフラグを取得

**注意点**:
- 依存関係チェック失敗時、GitHub に進捗報告を行う（既存の `post_progress()` メソッドを使用）
- フェーズステータスを `failed` に更新し、`return False` で終了
- 将来的にメタデータに `skip_dependency_check` フラグを記録する機能を追加する予定（現時点では未実装）

---

## 実装方針

### 1. 既存コードの尊重
- 既存のコーディングスタイルを維持（インデント、命名規則、コメント形式）
- 既存の `MetadataManager.get_phase_status()` メソッドを活用
- 既存のエラーハンドリングパターンに従う

### 2. 設計書への準拠
- 設計書7.1〜7.3節の実装方針に従って実装
- PHASE_DEPENDENCIES 定義は要件定義書の付録A に基づく
- CLIオプション名、プリセット名は設計書に記載されたものを使用

### 3. エラーハンドリング
- DependencyError はカスタム例外として実装
- エラーメッセージは明確で、ユーザーが解決方法を理解できるよう設計
- ヒントメッセージを表示（--skip-dependency-check, --ignore-dependencies の使用方法）

### 4. ログ出力
- `[INFO]`, `[WARNING]`, `[ERROR]` プレフィックスで統一
- 依存関係チェック成功時は `[INFO]` レベルで記録
- 依存関係違反時は `[WARNING]` または `[ERROR]` で記録

### 5. 将来拡張への配慮
- メタデータへのフラグ記録は将来拡張用としてコメントで明記
- ユーティリティ関数（`get_phase_dependencies()`, `get_all_phase_dependencies()`）を提供

---

## 品質ゲート確認

### ✅ Phase 2の設計に沿った実装である
- 設計書7.1〜7.3節に従って実装
- PHASE_DEPENDENCIES 定義、DependencyError クラス、validate_phase_dependencies() 関数を実装
- CLIオプション追加、個別フェーズ実行時の依存関係チェック統合を実装

### ✅ 既存コードの規約に準拠している
- 既存のコーディングスタイルを維持（インデント、命名規則、コメント形式）
- docstring は既存コードと同じ形式で記載
- エラーハンドリングは既存パターンに従う

### ✅ 基本的なエラーハンドリングがある
- DependencyError カスタム例外を実装
- ValueError（未知のフェーズ名）のハンドリング
- 各種例外のキャッチと適切なエラーメッセージ表示

### ✅ 明らかなバグがない
- PHASE_DEPENDENCIES 定義は要件定義書に基づく
- 依存関係チェックロジックは設計書通りに実装
- オプション排他性チェックを実装
- メタデータからのステータス取得は既存メソッドを使用

---

## 次のステップ

### Phase 5（test_implementation）
テストコードの実装を行う：
1. `tests/unit/utils/test_dependency_validator.py` の作成
2. `tests/unit/test_main.py` の拡張
3. `tests/unit/phases/test_base_phase.py` の拡張
4. `tests/integration/test_dependency_check_integration.py` の作成

### Phase 6（testing）
実装したテストコードを実行し、すべてのテストが成功することを確認する。

---

## 参考情報

### 設計書セクション
- 7.1: 新規モジュール: utils/dependency_validator.py
- 7.2: 既存モジュール修正: main.py
- 7.3: 既存モジュール修正: phases/base_phase.py

### 要件定義書セクション
- 付録A: フェーズ依存関係図
- FR-1: フェーズ依存関係の明示化
- FR-2: 依存関係チェック機能
- FR-3: CLIオプション - 依存関係チェックのスキップ
- FR-4: CLIオプション - 依存関係警告モード
- FR-6: プリセット実行モード

### コーディング規約
- @CONTRIBUTION.md: プロジェクト全体の開発ガイドライン
- @CLAUDE.md: Claude Code向けガイド

---

## 変更履歴

| バージョン | 日付 | 変更内容 | 作成者 |
|----------|------|---------|--------|
| 1.0 | 2025-10-12 | 初版作成 | Claude (AI Workflow) |
