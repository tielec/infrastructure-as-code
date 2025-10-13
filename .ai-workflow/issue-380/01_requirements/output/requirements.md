# 要件定義書 - Issue #380

## 📋 Issue情報

- **Issue番号**: #380
- **タイトル**: [TASK] Issue #376の続き - Application/CLI層の実装
- **状態**: open
- **URL**: https://github.com/tielec/infrastructure-as-code/issues/380
- **親Issue**: #376
- **作成日**: 2025-10-13

---

## 0. Planning Documentの確認

Issue #380のPlanning Document（`.ai-workflow/issue-380/00_planning/output/planning.md`）を確認し、以下の重要な開発戦略を把握しました：

### 実装戦略
- **戦略**: EXTEND（拡張）
- **複雑度**: 中程度（Medium）
- **見積もり工数**: 72~140時間（平均106時間、約13日）
- **判断根拠**: Issue #376で作成された基盤レイヤーと既存コードの統合が中心

### テスト戦略
- **テストレベル**: UNIT_INTEGRATION（ユニット + インテグレーション）
- **テストコード戦略**: BOTH_TEST（既存拡張 + 新規作成）
- **BDD_TEST**: 不要（Issue #376で既に実施済み）

### リスク評価
- **リスクレベル**: 中（Medium）
- **主要リスク**:
  - 116件のテスト失敗の修正が必要
  - 10個のフェーズファイルすべてのインポートパス修正
  - 後方互換性の維持が必須

### 成功基準
1. すべての既存機能が正常動作（テストカバレッジ80%以上）
2. 基盤レイヤーと既存コードの完全統合
3. 後方互換性の維持（CLIコマンド、メタデータフォーマット、設定ファイル構造）
4. main.pyのサイズ50行以下

---

## 1. 概要

### 1.1 背景

Issue #376の大規模リファクタリングにおいて、Phase 4（実装フェーズ）で以下の基盤レイヤーが完了しました：

- **Infrastructure層**（5ファイル）: 共通ユーティリティ（logger, error_handler, file_handler, retry）
- **Domain層 - Git Operations**（4ファイル）: GitRepository, GitBranch, GitCommit
- **Domain層 - GitHub Operations**（4ファイル）: IssueClient, PRClient, CommentClient
- **Domain層 - Phases**（5ファイル）: AbstractPhase, PhaseExecutor, PhaseValidator, PhaseReporter

しかし、上位レイヤー（Application層、CLI層）および既存ファイルの修正が未完了のままIssue #376が終了しました。Phase 9（評価フェーズ）では116件のテスト失敗が報告されており、これらの修正も必要です。

### 1.2 目的

Issue #380では、Issue #376で完了した基盤レイヤーと既存コードを統合し、リファクタリングを完全に完了させることを目的とします。

具体的には：
1. **Application層の実装**: WorkflowController、ConfigManagerの新規作成
2. **CLI層の実装**: cli/commands.pyの新規作成とmain.pyの簡素化
3. **既存コードの統合**: 10個のフェーズファイルのインポートパス修正
4. **テストの修正**: 116件の失敗テストの修正
5. **旧ファイルの削除**: 新しいアーキテクチャに完全移行後、旧ファイルを削除

### 1.3 ビジネス価値・技術的価値

#### ビジネス価値
- **保守性向上**: コードベースが整理され、バグ修正や機能追加が容易になる
- **開発速度向上**: 明確なレイヤー構造により、新規開発者のオンボーディング時間が短縮される
- **品質向上**: ユニットテストが容易になり、バグの早期発見が可能になる

#### 技術的価値
- **コードの可読性向上**: main.pyが1,080行から50行以下に削減され、責務が明確になる
- **疎結合アーキテクチャ**: 依存性注入パターンにより、コンポーネント間の結合度が低下
- **再利用性向上**: 小さなクラス単位でのコンポーネント化により、他プロジェクトでの再利用が可能
- **テスタビリティ向上**: モックが容易になり、ユニットテストの実装が簡単になる

---

## 2. 機能要件

### FR-1: WorkflowController実装（優先度: 高）

#### FR-1.1 ワークフロー初期化機能
**要件**: `initialize()` メソッドを実装し、Issue情報に基づいてワークフローを初期化する。

**詳細**:
- Issue番号からGitHub Issue情報を取得
- メタデータファイル（metadata.json）の作成
- 作業ブランチの作成
- 初期状態の記録

**依存コンポーネント**:
- IssueClient（GitHub Issue取得）
- MetadataManager（メタデータ管理）
- GitRepository, GitBranch（Git操作）

**見積もり**: 8~12時間

---

#### FR-1.2 単一フェーズ実行機能
**要件**: `execute_phase(phase_name: str)` メソッドを実装し、指定されたフェーズを実行する。

**詳細**:
- フェーズ名からフェーズクラスを動的にロード
- PhaseExecutorを使用してフェーズを実行
- 実行結果をメタデータに記録
- エラー発生時は適切にハンドリング

**依存コンポーネント**:
- PhaseExecutor（フェーズ実行制御）
- MetadataManager（実行結果記録）

**見積もり**: 6~10時間

---

#### FR-1.3 全フェーズ実行機能
**要件**: `execute_all_phases()` メソッドを実装し、Phase 1からPhase 9まで順番に実行する。

**詳細**:
- フェーズ実行順序の定義（planning → requirements → design → ... → evaluation）
- 各フェーズの依存関係チェック
- フェーズ失敗時のエラーハンドリング
- 進捗状況のリアルタイム表示

**依存コンポーネント**:
- PhaseExecutor
- MetadataManager

**見積もり**: 6~10時間

---

#### FR-1.4 エラーハンドリング機能
**要件**: ワークフロー実行中のエラーを適切にハンドリングする。

**詳細**:
- MetadataError、GitError、GitHubAPIError、ClaudeAPIErrorの適切なキャッチ
- エラー発生時のロールバック処理
- エラーログの記録
- ユーザーへの分かりやすいエラーメッセージ表示

**見積もり**: 4~8時間

---

### FR-2: ConfigManager実装（優先度: 高）

#### FR-2.1 設定ファイル読み込み機能
**要件**: `config.yaml` の読み込み機能を実装する。

**詳細**:
- YAMLファイルのパース処理
- 設定項目のバリデーション
- 必須項目の存在確認
- 型チェック（文字列、整数、真偽値）

**見積もり**: 2~4時間

---

#### FR-2.2 環境変数読み込み機能
**要件**: 環境変数からの設定読み込み機能を実装する。

**詳細**:
- 以下の環境変数をサポート:
  - GITHUB_TOKEN（必須）
  - GITHUB_REPOSITORY（必須）
  - CLAUDE_API_KEY（必須）
  - WORKING_DIR（オプション、デフォルト: カレントディレクトリ）
  - LOG_LEVEL（オプション、デフォルト: INFO）
- 環境変数がconfig.yamlより優先される

**見積もり**: 2~4時間

---

#### FR-2.3 設定バリデーション機能
**要件**: 読み込んだ設定のバリデーション機能を実装する。

**詳細**:
- 必須項目の存在確認
- 値の型チェック
- 値の範囲チェック（例: LOG_LEVELは"DEBUG", "INFO", "WARNING", "ERROR"のいずれか）
- バリデーションエラー時は ConfigValidationError を発生

**見積もり**: 2~4時間

---

#### FR-2.4 デフォルト値管理機能
**要件**: 設定項目のデフォルト値を管理する機能を実装する。

**詳細**:
- デフォルト値の定義（クラス変数または定数ファイル）
- 未設定項目へのデフォルト値適用
- デフォルト値のドキュメント化

**見積もり**: 2~4時間

---

### FR-3: CLI層実装（優先度: 高）

#### FR-3.1 CLIグループ定義
**要件**: `@click.group()` を使用してCLIコマンドグループを定義する。

**詳細**:
- `cli` グループの作成
- グローバルオプション（`--verbose`, `--config`）の定義
- ヘルプメッセージの設定

**見積もり**: 2~4時間

---

#### FR-3.2 initコマンド実装
**要件**: `init` コマンドを実装し、ワークフローを初期化する。

**詳細**:
- コマンド形式: `python main.py init --issue <issue_number>`
- WorkflowController.initialize() を呼び出し
- 初期化成功時のメッセージ表示
- エラー時の適切なエラーメッセージとexit code

**見積もり**: 2~4時間

---

#### FR-3.3 executeコマンド実装
**要件**: `execute` コマンドを実装し、指定されたフェーズを実行する。

**詳細**:
- コマンド形式: `python main.py execute --phase <phase_name>`
- WorkflowController.execute_phase() を呼び出し
- 実行結果の表示
- エラー時の適切なエラーメッセージとexit code

**見積もり**: 2~4時間

---

#### FR-3.4 resumeコマンド実装
**要件**: `resume` コマンドを実装し、中断したワークフローを再開する。

**詳細**:
- コマンド形式: `python main.py resume`
- メタデータから最後に実行したフェーズを取得
- WorkflowController.execute_all_phases() を呼び出し（最後のフェーズの次から）
- 実行結果の表示

**見積もり**: 2~4時間

---

#### FR-3.5 statusコマンド実装
**要件**: `status` コマンドを実装し、ワークフローの現在の状態を表示する。

**詳細**:
- コマンド形式: `python main.py status`
- メタデータからワークフロー状態を取得
- 各フェーズの実行状態（未実行/実行中/完了/失敗）を表示
- 現在のブランチ、Issue番号を表示

**見積もり**: 2~4時間

---

### FR-4: main.py修正（優先度: 中）

#### FR-4.1 CLI層の分離
**要件**: main.pyからCLI処理を `cli/commands.py` に分離する。

**詳細**:
- main.pyは cli.commands.cli() を呼び出すのみ
- エントリーポイントとしての責務のみに限定
- 50行以下に削減

**見積もり**: 2~4時間

---

#### FR-4.2 インポートパスの修正
**要件**: 新しいモジュール構造に対応したインポートパスに修正する。

**詳細**:
- `from cli.commands import cli` をインポート
- 旧インポートパスの削除

**見積もり**: 1~2時間

---

#### FR-4.3 WorkflowController呼び出し
**要件**: CLI層から WorkflowController を呼び出すように変更する。

**詳細**:
- cli/commands.py内で WorkflowController のインスタンス化
- ConfigManager を使用した設定読み込み
- WorkflowController のメソッド呼び出し

**見積もり**: 1~2時間

---

### FR-5: phases/*.py修正（優先度: 中）

#### FR-5.1 継承元の変更（10ファイル）
**要件**: 各フェーズクラスの継承元を `BasePhase` から `AbstractPhase` に変更する。

**対象ファイル**:
- phases/planning.py
- phases/requirements.py
- phases/design.py
- phases/test_scenario.py
- phases/implementation.py
- phases/test_implementation.py
- phases/testing.py
- phases/documentation.py
- phases/report.py
- phases/evaluation.py

**変更内容**:
```python
# Before
from phases.base_phase import BasePhase
class PlanningPhase(BasePhase):
    ...

# After
from phases.base.abstract_phase import AbstractPhase
class PlanningPhase(AbstractPhase):
    ...
```

**見積もり**: 4~8時間

---

#### FR-5.2 インポートパスの修正（10ファイル）
**要件**: Git/GitHub関連のインポートパスを新しいモジュール構造に変更する。

**変更内容**:
```python
# Before
from core.git_manager import GitManager
from core.github_client import GitHubClient

# After
from core.git.repository import GitRepository
from core.git.branch import GitBranch
from core.git.commit import GitCommit
from core.github.issue_client import IssueClient
from core.github.pr_client import PRClient
from core.github.comment_client import CommentClient
```

**見積もり**: 4~8時間

---

### FR-6: core/metadata_manager.py修正（優先度: 中）

#### FR-6.1 例外クラスのインポート修正
**要件**: 新しい例外クラス（MetadataError）をインポートする。

**変更内容**:
```python
# Before
class MetadataError(Exception):
    pass

# After
from common.error_handler import MetadataError
```

**見積もり**: 1~2時間

---

#### FR-6.2 エラーハンドリングの統一
**要件**: エラーハンドリングを新しい例外クラスに統一する。

**詳細**:
- MetadataError を使用してメタデータ関連のエラーを表現
- ログ出力を common.logger.Logger を使用して統一

**見積もり**: 1~2時間

---

### FR-7: core/claude_agent_client.py修正（優先度: 中）

#### FR-7.1 例外クラスのインポート修正
**要件**: 新しい例外クラス（ClaudeAPIError）をインポートする。

**変更内容**:
```python
# Before
class ClaudeAPIError(Exception):
    pass

# After
from common.error_handler import ClaudeAPIError
```

**見積もり**: 1~2時間

---

#### FR-7.2 エラーハンドリングの統一
**要件**: エラーハンドリングを新しい例外クラスに統一する。

**詳細**:
- ClaudeAPIError を使用してClaude API関連のエラーを表現
- ログ出力を common.logger.Logger を使用して統一

**見積もり**: 1~2時間

---

### FR-8: 既存テストの修正（優先度: 高）

#### FR-8.1 116件の失敗テストの修正
**要件**: Issue #376 Phase 9で報告された116件の失敗テストを修正する。

**詳細**:
- インポートパスの修正
- モックの差し替え（新しいクラスに対応）
- アサーションの修正
- テスト失敗原因の分析と修正

**見積もり**: 12~24時間

---

#### FR-8.2 新規クラス用のユニットテスト作成
**要件**: WorkflowController、ConfigManager、cli/commands.py用のユニットテストを作成する。

**詳細**:
- tests/unit/core/test_workflow_controller.py
- tests/unit/core/test_config_manager.py
- tests/unit/cli/test_commands.py
- テストカバレッジ80%以上

**見積もり**: 8~16時間

---

#### FR-8.3 統合テストの作成
**要件**: ワークフロー全体の統合テストを作成する。

**詳細**:
- tests/integration/test_workflow_integration.py
- CLI → Application → Domain層の全体フロー確認
- エラー発生時のリカバリー確認

**見積もり**: 4~8時間

---

### FR-9: 旧ファイルの削除（優先度: 低）

#### FR-9.1 phases/base_phase.py削除
**要件**: 4ファイル（AbstractPhase、PhaseExecutor、PhaseValidator、PhaseReporter）に分割後、削除する。

**前提条件**:
- すべてのphases/*.pyがAbstractPhaseを使用している
- すべてのテストが通過している
- Grep検索で `from phases.base_phase import` の参照がないことを確認

**見積もり**: 1~2時間

---

#### FR-9.2 core/git_manager.py削除
**要件**: 3ファイル（GitRepository、GitBranch、GitCommit）に分割後、削除する。

**前提条件**:
- すべてのphases/*.pyが新しいGitクラスを使用している
- すべてのテストが通過している
- Grep検索で `from core.git_manager import` の参照がないことを確認

**見積もり**: 1~2時間

---

#### FR-9.3 core/github_client.py削除
**要件**: 3ファイル（IssueClient、PRClient、CommentClient）に分割後、削除する。

**前提条件**:
- すべてのphases/*.pyが新しいGitHubクライアントを使用している
- すべてのテストが通過している
- Grep検索で `from core.github_client import` の参照がないことを確認

**見積もり**: 1~2時間

---

## 3. 非機能要件

### NFR-1: パフォーマンス要件

#### NFR-1.1 ワークフロー初期化時間
- **要件**: `initialize()` は10秒以内に完了すること
- **測定方法**: pytest-benchmarkを使用
- **根拠**: ユーザーの待機時間を最小限にするため

#### NFR-1.2 単一フェーズ実行時間
- **要件**: フェーズ実行のオーバーヘッドは5秒以内であること（フェーズ本体の実行時間を除く）
- **測定方法**: pytest-benchmarkを使用
- **根拠**: 既存の実装と同等以上のパフォーマンスを維持するため

#### NFR-1.3 メタデータ読み書き速度
- **要件**: メタデータの読み込み/書き込みは1秒以内に完了すること
- **測定方法**: pytest-benchmarkを使用
- **根拠**: ワークフロー全体の実行速度に影響しないようにするため

---

### NFR-2: セキュリティ要件

#### NFR-2.1 API認証情報の保護
- **要件**: GITHUB_TOKEN、CLAUDE_API_KEYは環境変数またはSSMから取得し、ログに出力しないこと
- **検証方法**: ログファイルの文字列検索
- **根拠**: APIトークン漏洩の防止

#### NFR-2.2 ファイルアクセス権限
- **要件**: メタデータファイル（metadata.json）は0600（所有者のみ読み書き可能）で作成すること
- **検証方法**: `ls -l` でパーミッション確認
- **根拠**: 機密情報漏洩の防止

#### NFR-2.3 入力バリデーション
- **要件**: CLIコマンドの引数は適切にバリデーションすること（SQLインジェクション、コマンドインジェクション対策）
- **検証方法**: セキュリティテスト実施
- **根拠**: セキュリティ脆弱性の防止

---

### NFR-3: 可用性・信頼性要件

#### NFR-3.1 エラーリカバリー
- **要件**: ワークフロー実行中にエラーが発生した場合、状態を保存し、再実行可能であること
- **検証方法**: 統合テストでエラー発生→再実行を確認
- **根拠**: ユーザーの作業損失を最小限にするため

#### NFR-3.2 冪等性
- **要件**: 同じコマンドを複数回実行しても、結果が変わらないこと（`init`を除く）
- **検証方法**: 統合テストで同一コマンドを複数回実行
- **根拠**: 安全な再実行を保証するため

#### NFR-3.3 テストカバレッジ
- **要件**: ユニットテストのカバレッジは80%以上であること
- **測定方法**: pytest-cov使用
- **根拠**: コード品質の担保

---

### NFR-4: 保守性・拡張性要件

#### NFR-4.1 コードの可読性
- **要件**: main.pyは50行以下、各クラスは400行以下であること
- **測定方法**: `wc -l` でファイル行数を確認
- **根拠**: コードの可読性と保守性の向上

#### NFR-4.2 依存性注入パターン
- **要件**: すべてのクラスは依存性注入パターンを使用し、ハードコーディングされた依存を持たないこと
- **検証方法**: コードレビュー
- **根拠**: テスタビリティと拡張性の向上

#### NFR-4.3 ドキュメント
- **要件**: すべてのパブリックメソッドにdocstringがあること
- **検証方法**: pydocstyleまたはpycodestyleを使用
- **根拠**: コードの理解容易性

#### NFR-4.4 型ヒント
- **要件**: すべてのパブリックメソッドに型ヒント（Type Hints）が付与されていること
- **検証方法**: mypyで型チェック
- **根拠**: IDE補完の向上とバグの早期発見

---

## 4. 制約事項

### 4.1 技術的制約

#### 4.1.1 既存アーキテクチャとの整合性
- **制約**: Issue #376で確立された新しいアーキテクチャパターン（クリーンアーキテクチャ）に準拠すること
- **影響**: 設計の自由度が制限される
- **対応**: Issue #376の設計書（design.md）を厳密に遵守

#### 4.1.2 Python 3.10+
- **制約**: Python 3.10以上で動作すること
- **影響**: 一部の新しい構文が使用できない場合がある
- **対応**: Python 3.10の機能のみを使用

#### 4.1.3 既存ライブラリの使用
- **制約**: 新規依存ライブラリの追加は禁止（既存: click, GitPython, PyGithub, openai, anthropic, pytest）
- **影響**: 機能実装の選択肢が制限される
- **対応**: 標準ライブラリと既存ライブラリで実装

#### 4.1.4 後方互換性の維持
- **制約**: 既存のCLIコマンド、メタデータフォーマット、設定ファイル構造を維持すること
- **影響**: インターフェース設計の自由度が制限される
- **対応**: 既存フォーマットを維持し、内部実装のみ変更

---

### 4.2 リソース制約

#### 4.2.1 実装期間
- **制約**: 見積もり工数72~140時間（平均106時間、約13日）以内に完了すること
- **影響**: 実装スコープの調整が必要
- **対応**: Phase単位での進捗管理と優先度付け

#### 4.2.2 人員
- **制約**: 単独開発者による実装
- **影響**: レビューのフィードバックサイクルが遅れる可能性
- **対応**: セルフレビューとドキュメント化の徹底

---

### 4.3 ポリシー制約

#### 4.3.1 コーディング規約
- **制約**: CLAUDE.md、CONTRIBUTION.mdに記載されたコーディング規約に準拠すること
- **影響**: コーディングスタイルの自由度が制限される
- **対応**: 既存コードベースのスタイルを参考にする

#### 4.3.2 セキュリティポリシー
- **制約**: セキュリティチェックリスト（CLAUDE.md）を満たすこと
- **影響**: 実装方法が制限される
- **対応**: セキュリティレビューの実施

---

## 5. 前提条件

### 5.1 システム環境

#### 5.1.1 Python環境
- Python 3.10以上がインストールされていること
- pip、virtualenvが使用可能であること

#### 5.1.2 Git環境
- Git 2.30以上がインストールされていること
- GitHubリポジトリへのアクセス権限があること

#### 5.1.3 環境変数
- 以下の環境変数が設定されていること:
  - GITHUB_TOKEN（GitHub API認証）
  - GITHUB_REPOSITORY（リポジトリ名: `owner/repo`形式）
  - CLAUDE_API_KEY（Claude API認証）

---

### 5.2 依存コンポーネント

#### 5.2.1 Issue #376の成果物
- 以下の18ファイルが既に実装されていること:
  - Infrastructure層（5ファイル）
  - Domain層 - Git（4ファイル）
  - Domain層 - GitHub（4ファイル）
  - Domain層 - Phases（5ファイル）

#### 5.2.2 既存ファイル
- 以下の既存ファイルが存在すること:
  - main.py
  - phases/*.py（10ファイル）
  - core/metadata_manager.py
  - core/claude_agent_client.py

---

### 5.3 外部システム連携

#### 5.3.1 GitHub API
- GitHub APIへのアクセスが可能であること
- レート制限（5000リクエスト/時間）内での使用

#### 5.3.2 Claude API
- Claude APIへのアクセスが可能であること
- APIキーが有効であること

---

## 6. 受け入れ基準

### 6.1 FR-1: WorkflowController実装

#### AC-1.1 ワークフロー初期化機能
**Given**: Issue番号380が指定されている
**When**: `WorkflowController.initialize(issue_number=380)` を実行
**Then**:
- metadata.jsonが作成される
- 作業ブランチ `ai-workflow/issue-380` が作成される
- エラーが発生しない

---

#### AC-1.2 単一フェーズ実行機能
**Given**: ワークフローが初期化されている
**When**: `WorkflowController.execute_phase("planning")` を実行
**Then**:
- PlanningPhaseが実行される
- 実行結果がmetadata.jsonに記録される
- エラーが発生しない

---

#### AC-1.3 全フェーズ実行機能
**Given**: ワークフローが初期化されている
**When**: `WorkflowController.execute_all_phases()` を実行
**Then**:
- Phase 1からPhase 9まで順番に実行される
- 各フェーズの実行結果がmetadata.jsonに記録される
- 全フェーズが成功する

---

### 6.2 FR-2: ConfigManager実装

#### AC-2.1 設定ファイル読み込み機能
**Given**: `config.yaml` に以下の設定が記載されている
```yaml
github_token: "test-token"
github_repository: "test-owner/test-repo"
claude_api_key: "test-key"
```
**When**: `ConfigManager.load_config()` を実行
**Then**:
- 設定が正しく読み込まれる
- `config.github_token` が "test-token" である
- エラーが発生しない

---

#### AC-2.2 環境変数読み込み機能
**Given**: 環境変数 `GITHUB_TOKEN="env-token"` が設定されている
**When**: `ConfigManager.load_config()` を実行
**Then**:
- 環境変数がconfig.yamlより優先される
- `config.github_token` が "env-token" である

---

#### AC-2.3 設定バリデーション機能
**Given**: 必須項目 `github_token` が設定されていない
**When**: `ConfigManager.load_config()` を実行
**Then**:
- `ConfigValidationError` が発生する
- エラーメッセージに "github_token is required" が含まれる

---

### 6.3 FR-3: CLI層実装

#### AC-3.1 initコマンド実装
**Given**: Issue #380が存在する
**When**: `python main.py init --issue 380` を実行
**Then**:
- ワークフローが初期化される
- "Workflow initialized successfully" が表示される
- exit code が 0 である

---

#### AC-3.2 executeコマンド実装
**Given**: ワークフローが初期化されている
**When**: `python main.py execute --phase planning` を実行
**Then**:
- planningフェーズが実行される
- "Phase 'planning' completed successfully" が表示される
- exit code が 0 である

---

#### AC-3.3 statusコマンド実装
**Given**: planningフェーズが完了している
**When**: `python main.py status` を実行
**Then**:
- ワークフローの状態が表示される
- planningフェーズが "completed" として表示される
- exit code が 0 である

---

### 6.4 FR-4: main.py修正

#### AC-4.1 CLI層の分離
**Given**: main.pyが修正されている
**When**: `wc -l main.py` を実行
**Then**:
- main.pyの行数が50行以下である

---

### 6.5 FR-5: phases/*.py修正

#### AC-5.1 継承元の変更
**Given**: phases/planning.pyが修正されている
**When**: `grep "from phases.base.abstract_phase import AbstractPhase" phases/planning.py` を実行
**Then**:
- 該当行が見つかる

---

#### AC-5.2 インポートパスの修正
**Given**: phases/planning.pyが修正されている
**When**: `grep "from core.git_manager import" phases/planning.py` を実行
**Then**:
- 該当行が見つからない（新しいインポートパスに変更済み）

---

### 6.6 FR-8: 既存テストの修正

#### AC-8.1 テストの成功
**Given**: すべてのテストが修正されている
**When**: `pytest tests/` を実行
**Then**:
- すべてのテストが成功する（116件の失敗が0件になる）
- テストカバレッジが80%以上である

---

### 6.7 FR-9: 旧ファイルの削除

#### AC-9.1 旧ファイルの参照がないこと
**Given**: すべての実装が完了している
**When**: `grep -r "from phases.base_phase import" scripts/` を実行
**Then**:
- 該当行が見つからない（参照がない）

---

## 7. スコープ外

以下の項目は本Issue（#380）のスコープ外とします：

### 7.1 新機能の追加
- 新しいフェーズの追加
- 新しいCLIコマンドの追加（init, execute, resume, status以外）
- 新しい設定項目の追加（config.yaml）

**理由**: Issue #380はリファクタリングの完了が目的であり、新機能追加は別Issueで実施する。

---

### 7.2 パフォーマンス最適化
- 既存実装よりも大幅なパフォーマンス向上
- 並列実行の実装

**理由**: 後方互換性とコード品質を最優先とし、パフォーマンス最適化は将来の改善項目とする。

---

### 7.3 UIの改善
- プログレスバーの追加
- カラフルな出力

**理由**: 機能の完成を優先し、UX向上は将来の改善項目とする。

---

### 7.4 ドキュメントの大幅な刷新
- ARCHITECTURE.mdの全面書き直し
- チュートリアルの追加

**理由**: 既存ドキュメントの更新にとどめ、大幅な刷新は別Issueで実施する。

---

## 8. 実施順序（推奨）

Issue #380の実装は以下の順序で実施することを推奨します：

### Phase 1: 要件定義（見積もり: 2~4時間）
1. Issue #376の成果物確認
2. 残作業の詳細化

### Phase 2: 設計（見積もり: 2~4時間）
1. Application層の詳細設計
2. CLI層の詳細設計

### Phase 3: テストシナリオ（見積もり: 2~4時間）
1. ユニットテストシナリオ作成
2. インテグレーションテストシナリオ作成

### Phase 4: 実装（見積もり: 66~124時間）
1. **ConfigManagerの実装**（8~12h）
2. **WorkflowControllerの実装**（24~40h）
3. **CLI層の実装**（8~16h）
4. **main.pyの修正**（4~8h）
5. **phases/*.pyの修正**（8~16h）
6. **metadata_manager.py/claude_agent_client.pyの修正**（2~4h）

### Phase 5: テスト実装（見積もり: 16~32時間）
1. 新規クラスのユニットテスト作成
2. 既存テストの修正（116件の失敗対応）

### Phase 6: テスト実行（見積もり: 2~4時間）
1. 全テストスイート実行
2. カバレッジレポート生成

### Phase 7: ドキュメント更新（見積もり: 2~4時間）
1. ARCHITECTURE.mdの更新
2. README.mdの更新

### Phase 8: レポート作成（見積もり: 1~2時間）
1. 実装完了レポート作成

### Phase 9: 評価（見積もり: 1~2時間）
1. 品質ゲート確認
2. 旧ファイルの削除（phases/base_phase.py, core/git_manager.py, core/github_client.py）

---

## 9. 品質ゲートチェックリスト

Phase 1（要件定義）の品質ゲートは以下の通りです：

- [x] **機能要件が明確に記載されている**
  - FR-1〜FR-9まで9つの機能要件を定義
  - 各要件は具体的かつ測定可能な形で記述

- [x] **受け入れ基準が定義されている**
  - AC-1.1〜AC-9.1まで受け入れ基準を定義
  - Given-When-Then形式で記述
  - 各要件に対応する受け入れ基準を作成

- [x] **スコープが明確である**
  - スコープ内: Application層、CLI層、既存ファイル修正、テスト修正、旧ファイル削除
  - スコープ外: 新機能追加、パフォーマンス最適化、UIの改善、ドキュメントの大幅な刷新

- [x] **論理的な矛盾がない**
  - 機能要件と受け入れ基準が対応
  - 非機能要件と制約事項が矛盾しない
  - 実施順序が依存関係に基づいている

---

## 10. 総見積もり工数

| Phase | 見積もり工数 |
|-------|------------|
| Phase 1: 要件定義 | 2~4時間 |
| Phase 2: 設計 | 2~4時間 |
| Phase 3: テストシナリオ | 2~4時間 |
| Phase 4: 実装 | 66~124時間 |
| Phase 5: テスト実装 | 16~32時間 |
| Phase 6: テスト実行 | 2~4時間 |
| Phase 7: ドキュメント更新 | 2~4時間 |
| Phase 8: レポート作成 | 1~2時間 |
| Phase 9: 評価 | 1~2時間 |
| **合計** | **94~180時間** |

**平均**: 137時間（約17日）

**注意**: Planning Documentの見積もり（72~140時間）は Phase 4（実装）のみの見積もりでした。本要件定義書では全フェーズを含めた総工数を算出しています。

---

## 11. 関連ドキュメント

- **Planning Document**: `.ai-workflow/issue-380/00_planning/output/planning.md`
- **Issue #376 Design Document**: `.ai-workflow/issue-376/02_design/output/design.md`
- **Issue #376 Implementation Log**: `.ai-workflow/issue-376/04_implementation/output/implementation.md`
- **Issue #376 Evaluation Report**: `.ai-workflow/issue-376/09_evaluation/output/evaluation_report.md`
- **CLAUDE.md**: プロジェクト全体の方針とコーディングガイドライン
- **ARCHITECTURE.md**: アーキテクチャ設計思想
- **CONTRIBUTION.md**: 開発ガイドライン

---

**作成日**: 2025-10-13
**作成者**: Claude (AI Workflow - Phase 1)
**ステータス**: Requirements Phase Completed
