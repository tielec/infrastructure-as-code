# 要件定義書: AI駆動開発自動化ワークフローMVP v1.0.0

## ドキュメント情報
- **Issue番号**: #304
- **バージョン**: v1.0.0 (MVP)
- **作成日**: 2025-10-09
- **ステータス**: Phase 1 - 要件定義

---

## 1. 概要

### 1.1 背景
現在の開発プロセスでは、GitHub IssueからPR作成まで手動での作業が多く、開発者の生産性に影響を与えている。特に以下の課題が存在する：
- Issue内容の分析と要件定義の作成に時間がかかる
- 設計ドキュメント作成が手作業で属人化しやすい
- テストシナリオの作成が後回しになりがち
- 実装からドキュメント化までの一貫性が保たれにくい

### 1.2 目的
GitHub IssueからPR作成までの開発プロセスを、Claude AIが自動的に実行するワークフローシステムを構築する。MVP（Minimum Viable Product）として、まずはワークフローの基盤部分（初期化、状態管理、CLI、テストフレームワーク、Jenkins統合）を実装し、6フェーズの自動実行機能の土台を作る。

### 1.3 ビジネス価値
- **開発者の生産性向上**: 手動作業の削減により開発に集中できる
- **品質の標準化**: AIによる一貫した品質のドキュメント・コード生成
- **開発サイクルの短縮**: Issue作成からPRまでの時間を大幅に削減
- **属人化の解消**: プロセスの標準化により誰でも同じ品質を実現

### 1.4 技術的価値
- **Platform Engineeringの実践**: セルフサービス化の実現
- **Everything as Code**: ワークフロー定義もコードで管理
- **再利用可能な基盤**: 将来的な機能拡張の土台
- **テスト駆動開発**: BDDによる信頼性の高い実装

---

## 2. 機能要件

### 2.1 ワークフロー初期化機能 (優先度: 高)
**要件ID**: FR-001

GitHub Issueの情報を元に、ワークフロー用のディレクトリ構造とメタデータファイルを生成する。

**詳細**:
- Issue番号、タイトル、URL、状態、本文を受け取る
- `.ai-workflow/issue-{番号}/` ディレクトリを作成
- 6フェーズ用のサブディレクトリを作成（`01_requirements`, `02_design`, `03_test_scenario`, `04_implementation`, `05_testing`, `06_documentation`）
- 各フェーズに `output/`, `review/` ディレクトリを作成
- `metadata.json` ファイルを生成（Issue情報、フェーズ状態、タイムスタンプを含む）

**受け入れ基準**:
```gherkin
Given: GitHub Issue #304 の情報が入力される
When: ワークフロー初期化コマンドを実行する
Then: `.ai-workflow/issue-304/` ディレクトリが作成される
And: `metadata.json` に Issue情報が正しく記録される
And: 全6フェーズのディレクトリ構造が作成される
And: 各フェーズの状態が "pending" として初期化される
```

### 2.2 状態管理機能 (優先度: 高)
**要件ID**: FR-002

`metadata.json` を使用してワークフローの状態を永続化し、フェーズの進行状況を管理する。

**詳細**:
- Issue情報（番号、タイトル、URL、状態、本文）の保存
- 各フェーズの状態管理（pending/in_progress/completed/failed）
- タイムスタンプの記録（created_at, updated_at, 各フェーズの開始・完了時刻）
- 状態の読み込み・更新・保存機能
- JSONスキーマ検証

**受け入れ基準**:
```gherkin
Given: ワークフローが初期化されている
When: フェーズの状態を更新する
Then: `metadata.json` が正しく更新される
And: タイムスタンプが記録される
And: JSON形式が正しい（バリデーション成功）
```

### 2.3 CLIインターフェース (優先度: 高)
**要件ID**: FR-003

Click フレームワークを使用したコマンドラインインターフェースを提供する。

**詳細**:
- `python main.py init` - ワークフロー初期化
- `python main.py status` - 状態表示
- `python main.py phase <phase-name>` - フェーズ実行（将来拡張用）
- サブコマンド構造のサポート
- ヘルプメッセージの提供
- エラーハンドリングとユーザーフレンドリーなメッセージ

**受け入れ基準**:
```gherkin
Given: ai-workflowディレクトリに移動している
When: `python main.py --help` を実行する
Then: 使用可能なコマンド一覧が表示される

Given: Issue情報が用意されている
When: `python main.py init --issue-number 304 --title "..." --url "..." --state open --body "..."` を実行する
Then: ワークフローが初期化される
And: 成功メッセージが表示される
```

### 2.4 BDDテストフレームワーク (優先度: 高)
**要件ID**: FR-004

behave を使用したBDD（Behavior Driven Development）テストフレームワークを構築する。

**詳細**:
- Gherkin形式のシナリオ定義（`workflow.feature`）
- ステップ定義の実装（`workflow_steps.py`）
- テストフィクスチャの管理（`conftest.py`）
- テスト実行環境のセットアップ・クリーンアップ
- テストレポートの生成

**受け入れ基準**:
```gherkin
Given: テストスイートが用意されている
When: `behave tests/features/` を実行する
Then: すべてのシナリオが成功する
And: テストレポートが生成される
And: カバレッジが80%以上である
```

### 2.5 Jenkins統合 (優先度: 中)
**要件ID**: FR-005

Jenkins Job DSL と Jenkinsfile を使用したCI/CD統合を実装する。

**詳細**:
- Job DSL定義（`ai-workflow-orchestrator.groovy`）
- Jenkinsfileによるパイプライン定義
- GitHub Webhook連携（将来拡張用のプレースホルダー）
- パイプラインパラメータ（Issue番号、環境変数）
- ビルド成功/失敗の通知

**受け入れ基準**:
```gherkin
Given: Jenkinsサーバーが稼働している
When: シードジョブを実行する
Then: AI Workflow Orchestratorジョブが作成される

Given: AI Workflow Orchestratorジョブが存在する
When: ジョブを手動実行する（Issue番号をパラメータ指定）
Then: ワークフロー初期化が実行される
And: Jenkinsコンソールに実行ログが表示される
And: 成功/失敗ステータスが正しく報告される
```

### 2.6 ロギング機能 (優先度: 中)
**要件ID**: FR-006

実行プロセスのロギングとトレーサビリティを提供する。

**詳細**:
- 標準出力へのログ出力（INFO, WARNING, ERROR レベル）
- ログファイルへの永続化（`.ai-workflow/issue-{番号}/logs/`）
- タイムスタンプ付きログ
- 構造化ログ（JSON形式でのメタデータ記録）

**受け入れ基準**:
```gherkin
Given: ワークフローが実行されている
When: 各処理ステップが実行される
Then: ログファイルに実行内容が記録される
And: エラー発生時にスタックトレースが記録される
```

---

## 3. 非機能要件

### 3.1 パフォーマンス要件
- **NFR-001**: ワークフロー初期化は5秒以内に完了すること
- **NFR-002**: metadata.json の読み書きは1秒以内に完了すること
- **NFR-003**: BDDテストスイート全体の実行時間は5分以内であること

### 3.2 セキュリティ要件
- **NFR-004**: API キー等の機密情報は環境変数またはSSM Parameter Storeで管理すること
- **NFR-005**: `metadata.json` に機密情報を含めないこと
- **NFR-006**: Jenkinsクレデンシャルストアを使用してAPI認証情報を管理すること

### 3.3 可用性・信頼性要件
- **NFR-007**: ワークフロー実行中の中断に対する再開機能を提供すること
- **NFR-008**: エラー発生時に適切なエラーメッセージとリカバリー手順を提示すること
- **NFR-009**: metadata.json の破損時にバックアップから復元できること

### 3.4 保守性・拡張性要件
- **NFR-010**: Phase 1-6 の実装を容易に追加できるモジュラー設計とすること
- **NFR-011**: 新しいフェーズの追加が既存コードへの影響を最小化すること
- **NFR-012**: コーディング規約（CLAUDE.md）に準拠すること
- **NFR-013**: PEP 8 準拠のPythonコードとすること
- **NFR-014**: 日本語コメントとドキュメントを使用すること（CLAUDE.md要件）

### 3.5 ユーザビリティ要件
- **NFR-015**: CLIコマンドは直感的で覚えやすいものとすること
- **NFR-016**: エラーメッセージは原因と対処方法を明示すること
- **NFR-017**: `--help` オプションで詳細な使用方法を表示すること

---

## 4. 制約事項

### 4.1 技術的制約
- **C-001**: Python 3.8以上を使用すること
- **C-002**: Click, behave を使用すること（requirements.txt で管理）
- **C-003**: Jenkins Job DSL と Jenkinsfile を使用すること
- **C-004**: Groovy によるJob DSL定義を使用すること
- **C-005**: 既存のPlatform Engineering設計思想（ARCHITECTURE.md）に準拠すること
- **C-006**: 日本語でのコメント・ドキュメント記述（CLAUDE.md 要件）

### 4.2 リソース制約
- **C-007**: MVP実装のため、Phase 1-6 の自動実行は将来対応とする
- **C-008**: PR自動作成機能は将来対応とする
- **C-009**: GitHub Webhook連携は将来対応とする（Jenkinsfileにプレースホルダーのみ）

### 4.3 ポリシー制約
- **C-010**: すべてのコードはGit管理すること
- **C-011**: コミットメッセージは `[scripts] action: 説明` 形式とすること（CONTRIBUTION.md）
- **C-012**: 機密情報のハードコーディング禁止
- **C-013**: CLAUDE.md に記載されたJenkinsパラメータ定義ルールを遵守すること（Job DSLで定義、Jenkinsfileでは禁止）

---

## 5. 前提条件

### 5.1 システム環境
- **P-001**: Python 3.8以上がインストールされていること
- **P-002**: pip3 が使用可能であること
- **P-003**: Git がインストールされていること
- **P-004**: Jenkinsサーバーが稼働していること（Jenkins統合機能使用時）

### 5.2 依存コンポーネント
- **P-005**: Click フレームワーク（CLIインターフェース）
- **P-006**: behave フレームワーク（BDDテスト）
- **P-007**: Jenkins Job DSL Plugin
- **P-008**: Jenkins Pipeline Plugin

### 5.3 外部システム連携
- **P-009**: GitHub API アクセス（将来のPR作成機能で必要）
- **P-010**: Claude API アクセス（将来のAI実行機能で必要）
- **P-011**: AWS SSM Parameter Store（機密情報管理）

---

## 6. 受け入れ基準

### 6.1 ワークフロー初期化機能
```gherkin
Scenario: ワークフロー初期化
  Given GitHub Issue #304 の情報が用意されている
  When `python main.py init` コマンドを実行する
  Then `.ai-workflow/issue-304/` ディレクトリが作成される
  And 6フェーズのディレクトリ構造が作成される
  And `metadata.json` にIssue情報が記録される
  And すべてのフェーズの状態が "pending" である
```

### 6.2 状態管理機能
```gherkin
Scenario: 状態の永続化
  Given ワークフローが初期化されている
  When フェーズ1の状態を "in_progress" に更新する
  Then `metadata.json` のフェーズ1の状態が "in_progress" である
  And `updated_at` タイムスタンプが更新されている
  And JSON形式が正しい（バリデーション成功）
```

### 6.3 CLIインターフェース
```gherkin
Scenario: CLIヘルプ表示
  Given ai-workflowディレクトリにいる
  When `python main.py --help` を実行する
  Then 使用可能なコマンド一覧が表示される
  And 各コマンドの説明が表示される
```

### 6.4 BDDテストフレームワーク
```gherkin
Scenario: BDDテスト実行
  Given テストスイートが用意されている
  When `behave tests/features/` を実行する
  Then すべてのシナリオがパスする
  And テストカバレッジが80%以上である
```

### 6.5 Jenkins統合
```gherkin
Scenario: Jenkinsジョブ作成
  Given シードジョブが実行される
  When Job DSL定義が処理される
  Then AI Workflow Orchestratorジョブが作成される
  And パラメータ（Issue番号）が定義されている
```

```gherkin
Scenario: Jenkinsパイプライン実行
  Given AI Workflow Orchestratorジョブが存在する
  When ジョブを手動実行する（Issue番号=304）
  Then ワークフロー初期化が実行される
  And ビルドが成功する
  And コンソールログに実行内容が記録される
```

---

## 7. スコープ外

### 7.1 MVP v1.0.0 で対応しない機能
以下の機能は将来バージョンで対応する：

- **Phase 1-6 の自動実行**: ワークフローの基盤のみ実装、各フェーズの自動実行ロジックは将来対応
- **PR自動作成**: GitHub API連携によるPR自動作成は将来対応
- **GitHub Webhook連携**: Issue作成時の自動トリガーは将来対応
- **Claude API統合**: AI実行エンジンの統合は将来対応
- **マルチIssue同時実行**: 並列実行機能は将来対応
- **ロールバック機能**: フェーズ失敗時のロールバックは将来対応
- **通知機能**: Slack等への通知は将来対応

### 7.2 将来的な拡張候補
- 複数AIエージェントの並列実行
- レビューフィードバックの自動反映
- カスタムフェーズの追加
- ダッシュボードUI
- メトリクス収集と分析

---

## 8. 品質ゲート

この要件定義書は以下の品質ゲートを満たしている：

- ✅ **機能要件が明確に記載されている**: FR-001 ~ FR-006 として6つの機能要件を定義
- ✅ **受け入れ基準が定義されている**: Given-When-Then 形式で各機能の受け入れ基準を記載
- ✅ **スコープが明確である**: MVP v1.0.0 の範囲と将来対応を明確に区分
- ✅ **論理的な矛盾がない**: 機能要件、非機能要件、制約事項が整合している

---

## 9. 補足情報

### 9.1 用語定義
- **MVP (Minimum Viable Product)**: 最小限の機能で価値を提供できる製品
- **BDD (Behavior Driven Development)**: 振る舞い駆動開発、Given-When-Then形式で要件を記述
- **Job DSL**: Jenkinsジョブ定義をGroovyコードで記述する仕組み
- **Metadata**: ワークフローの状態や進行情報を保存するデータ

### 9.2 参考ドキュメント
- [CLAUDE.md](/workspace/CLAUDE.md) - プロジェクトガイドライン
- [ARCHITECTURE.md](/workspace/ARCHITECTURE.md) - Platform Engineering設計思想
- [CONTRIBUTION.md](/workspace/CONTRIBUTION.md) - 開発ガイドライン
- [scripts/ai-workflow/README.md](/workspace/scripts/ai-workflow/README.md) - AI Workflow詳細仕様

---

**End of Document**
