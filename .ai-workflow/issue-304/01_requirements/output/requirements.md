# AI駆動開発自動化ワークフロー MVP v1.0.0 要件定義書

**Issue番号**: #304
**Issue URL**: https://github.com/tielec/infrastructure-as-code/issues/304
**文書バージョン**: 1.0.0
**作成日**: 2025-10-08

---

## 1. 概要

### 1.1 背景

本プロジェクトは、Jenkins CI/CDインフラ自動化プロジェクト（infrastructure-as-code）の一部として、AI駆動による開発プロセスの自動化を実現するワークフローシステムの最小実装版（MVP v1.0.0）を構築する。

**現在の課題**:
- 開発プロセスの標準化と効率化が求められている
- GitHub Issueから実装、テスト、ドキュメント作成まで手作業で実施している
- 開発者のリソースをより創造的なタスクに集中させたい

### 1.2 目的

GitHub IssueからPR作成まで、Claude AI（Agent SDK）が自律的に開発プロセスを実行するワークフローシステムのMVPを実装する。

**ビジネス価値**:
- 開発サイクルの短縮（Issue作成から実装完了まで）
- 品質の一貫性確保（AIレビューによる標準化）
- 開発者の生産性向上（定型作業の自動化）

**技術的価値**:
- Claude Agent SDKの実践的活用事例の確立
- AIとCI/CD統合のベストプラクティス構築
- 既存Jenkins基盤との連携強化

### 1.3 スコープ

**対象範囲（MVP v1.0.0）**:
- ワークフロー初期化機能（Issue URLからmetadata.json生成）
- 6フェーズ構造の定義と状態管理
- Click CLIフレームワークによるコマンドライン操作
- BDD（behave）テストによる品質保証
- Jenkins統合（Job DSL + Jenkinsfile）
- Docker環境での実行基盤

**スコープ外（将来対応）**:
- Phase 1-6の実際の実行機能（Phase 1のみv1.1.0で対応済み）
- PR自動作成機能
- GitHub Webhook統合
- 複数Issue同時実行
- リアルタイムモニタリングUI

---

## 2. 機能要件

### FR-01: ワークフロー初期化機能（優先度: 高）

**要件**: GitHub Issue URLを受け取り、ワークフロー実行環境を初期化する。

**詳細**:
- Issue URLからIssue番号を抽出
- `.ai-workflow/issue-{number}/` ディレクトリを作成
- `metadata.json` を初期状態で生成
- 6フェーズ（requirements, design, test_scenario, implementation, testing, documentation）を`pending`状態で初期化
- ISO 8601形式のタイムスタンプ（UTC）で作成・更新日時を記録

**受け入れ基準**:
- **Given**: GitHub Issue URL `https://github.com/tielec/infrastructure-as-code/issues/304`
- **When**: `python main.py init --issue-url <URL>` を実行
- **Then**: `.ai-workflow/issue-304/metadata.json` が作成され、以下を含む
  - `issue_number`: "304"
  - `workflow_version`: "1.0.0"
  - `current_phase`: "requirements"
  - 6フェーズすべてが`status: pending`

### FR-02: ワークフロー状態管理（優先度: 高）

**要件**: metadata.jsonを通じてワークフロー全体の状態を管理する。

**詳細**:
- フェーズステータス管理（Enum: `pending`, `in_progress`, `completed`, `failed`）
- リトライカウント管理（最大3回）
- タイムスタンプ管理（開始時刻、完了時刻）
- コスト追跡（トークン使用量、API利用料金）
- 設計判断の保存（Phase 2での戦略判断）

**受け入れ基準**:
- **Given**: ワークフロー初期化が完了している
- **When**: フェーズステータスを`in_progress`に更新
- **Then**: `metadata.json`の該当フェーズが更新され、`started_at`がISO 8601形式で記録される
- **And**: `updated_at`が最新のタイムスタンプに更新される

### FR-03: CLI操作インターフェース（優先度: 高）

**要件**: Clickフレームワークを使用したCLIコマンドを提供する。

**詳細**:
- `init`: ワークフロー初期化
- `execute`: フェーズ実行（将来実装）
- `status`: 現在の状態確認（将来実装）
- `cleanup`: ワークフローのクリーンアップ（将来実装）

**受け入れ基準**:
- **Given**: CLIスクリプトがインストールされている
- **When**: `python main.py --help` を実行
- **Then**: 利用可能なコマンド一覧が表示される
- **And**: 各コマンドの説明とオプションが表示される

### FR-04: BDDテスト基盤（優先度: 中）

**要件**: behaveフレームワークを使用したBDDテストを提供する。

**詳細**:
- Gherkin形式（Given-When-Then）でテストシナリオを記述
- ワークフロー初期化シナリオのテスト実装
- 将来の6フェーズ実装時のテスト拡張可能性を確保

**受け入れ基準**:
- **Given**: BDDテストシナリオが定義されている
- **When**: `behave tests/features/` を実行
- **Then**: ワークフロー初期化のシナリオが成功する
- **And**: テスト結果が明確に表示される

### FR-05: Jenkins統合（優先度: 高）

**要件**: JenkinsからワークフローをトリガーできるJob DSLとJenkinsfileを提供する。

**詳細**:
- Job DSL定義: `jenkins/jobs/dsl/ai-workflow/ai-workflow-orchestrator.groovy`
- Jenkinsfile定義: `jenkins/jobs/pipeline/ai-workflow/ai-workflow-orchestrator/Jenkinsfile`
- パラメータ: `ISSUE_URL` (String, 必須)
- 将来のフェーズステージ追加に対応可能な構造

**受け入れ基準**:
- **Given**: JenkinsにJob DSLがデプロイされている
- **When**: Job DSL Seed Jobを実行
- **Then**: `AI-Workflow/ai-workflow-orchestrator` Jobが作成される
- **And**: Job実行時にISSUE_URLパラメータを入力できる

### FR-06: Docker実行環境（優先度: 高）

**要件**: Docker環境でワークフローを実行できる基盤を提供する。

**詳細**:
- Dockerfile定義: Python 3.11ベース
- 依存パッケージ管理: requirements.txt
- Claude Agent SDK統合（v0.9.1）
- 環境変数による認証管理（`CLAUDE_CODE_OAUTH_TOKEN`, `GITHUB_TOKEN`）

**受け入れ基準**:
- **Given**: Dockerfileが定義されている
- **When**: `docker build -t ai-workflow:v1.1.0 .` を実行
- **Then**: イメージが正常にビルドされる
- **And**: コンテナ内で`python main.py init`が実行できる

---

## 3. 非機能要件

### NFR-01: パフォーマンス

| 項目 | 要件 | 測定方法 |
|------|------|---------|
| ワークフロー初期化時間 | 1秒以内 | 実行時間計測 |
| metadata.json読み込み時間 | 100ms以内 | 実行時間計測 |
| Docker イメージビルド時間 | 5分以内 | ビルドログ確認 |

### NFR-02: セキュリティ

| 項目 | 要件 |
|------|------|
| 認証情報管理 | Claude API Key、GitHub Tokenは環境変数で管理、ハードコーディング禁止 |
| ログ出力 | 認証情報をログに出力しない |
| ファイルアクセス | `.ai-workflow/`ディレクトリ配下のみ書き込み許可 |

### NFR-03: 可用性・信頼性

| 項目 | 要件 |
|------|------|
| エラーハンドリング | すべての例外を適切にキャッチし、明確なエラーメッセージを出力 |
| 状態の永続化 | metadata.jsonは常に最新状態を反映 |
| 冪等性 | 同じコマンドを複数回実行しても安全 |

### NFR-04: 保守性・拡張性

| 項目 | 要件 |
|------|------|
| コード品質 | Python PEP 8準拠、型ヒント付与 |
| モジュール構造 | core/、phases/、reviewers/に明確に分離 |
| 拡張性 | 新しいフェーズの追加が容易な設計 |
| ドキュメント | README.md、ARCHITECTURE.mdで設計思想を明記 |

### NFR-05: テスト容易性

| 項目 | 要件 |
|------|------|
| ユニットテスト | 各モジュールが独立してテスト可能 |
| 統合テスト | BDDテストによるエンドツーエンド検証 |
| ローカル実行 | Jenkins環境以外でもPythonスクリプトを実行可能 |

---

## 4. 制約事項

### 4.1 技術的制約

| 制約 | 理由 |
|------|------|
| Python 3.11以上 | Claude Agent SDK v0.9.1の要件 |
| Docker Desktop必須 | Linux環境での安定動作のため |
| Claude Pro/Max契約 | OAuth認証によるAgent SDK利用のため |
| GitHub Personal Access Token | Issue情報取得、コメント投稿のため |
| Windows開発環境 | 開発者PCがWindows（WSL2使用） |

### 4.2 リソース制約

| 項目 | 制約 |
|------|------|
| 開発期間 | MVP v1.0.0は2週間で完了（実績） |
| API利用料金 | Claude API利用料は1ワークフローあたり$5以下を目標 |
| ストレージ | `.ai-workflow/`ディレクトリはリポジトリサイズに影響 |

### 4.3 ポリシー制約

| 項目 | 制約 |
|------|------|
| コーディング規約 | `CLAUDE.md`、`scripts/CONTRIBUTION.md`に準拠 |
| コミットメッセージ | `[scripts] action: 説明` 形式 |
| ドキュメント言語 | 日本語（コメント、README） |
| AI安全性 | 防御的セキュリティタスクのみ、悪意のあるコード生成禁止 |

---

## 5. 前提条件

### 5.1 システム環境

| 項目 | 要件 |
|------|------|
| OS | Windows 10/11 (WSL2) またはLinux |
| Docker | Docker Desktop 20.10以上 |
| Git | Git 2.0以上 |
| Python | 3.11以上（ローカル開発時） |
| Node.js | 20以上（Claude Code CLI用） |

### 5.2 依存コンポーネント

| コンポーネント | バージョン | 用途 |
|--------------|----------|------|
| Click | 8.1.7 | CLIフレームワーク |
| behave | 最新 | BDDテスト |
| claude-code-sdk | 0.9.1 | Claude Agent SDK |
| PyGithub | 最新 | GitHub API統合 |

### 5.3 外部システム連携

| システム | 連携内容 |
|---------|---------|
| Claude API | Agent SDK経由でAI実行（OAuth認証） |
| GitHub API | Issue情報取得、コメント投稿、PR作成（PAT認証） |
| Jenkins | ワークフローのトリガーと実行管理 |

---

## 6. 受け入れ基準

### AC-01: ワークフロー初期化

**シナリオ**: ワークフロー初期化とメタデータ作成

```gherkin
Given GitHub Issue "https://github.com/tielec/infrastructure-as-code/issues/304" が存在する
When ワークフロー初期化コマンドを実行する
Then .ai-workflow/issue-304/metadata.json が作成される
And metadata.jsonにIssue番号 "304" が記録される
And metadata.jsonにワークフローバージョン "1.0.0" が記録される
And metadata.jsonに6つのフェーズ定義が含まれる
And すべてのフェーズステータスが "pending" である
```

### AC-02: フェーズステータス更新

**シナリオ**: Phase 1をin_progressに更新

```gherkin
Given ワークフロー初期化が完了している
When Phase 1のステータスを "in_progress" に更新する
Then metadata.jsonのrequirementsフェーズが "in_progress" になる
And started_atにISO 8601形式のタイムスタンプが記録される
And updated_atが最新のタイムスタンプに更新される
```

### AC-03: BDDテスト実行

**シナリオ**: BDDテストが成功する

```gherkin
Given BDDテストシナリオが定義されている
When behaveコマンドを実行する
Then ワークフロー初期化シナリオが成功する
And テスト結果が "1 scenario passed" を含む
```

### AC-04: Docker環境での実行

**シナリオ**: Docker環境でワークフロー初期化

```gherkin
Given Dockerイメージがビルドされている
And 環境変数CLAUDE_CODE_OAUTH_TOKENが設定されている
And 環境変数GITHUB_TOKENが設定されている
When Dockerコンテナ内でinitコマンドを実行する
Then ワークフロー初期化が成功する
And metadata.jsonがホスト側に永続化される
```

### AC-05: Jenkins Job作成

**シナリオ**: Jenkins Job DSLからJob作成

```gherkin
Given Job DSLファイルが配置されている
When Jenkins Seed Jobを実行する
Then AI-Workflow/ai-workflow-orchestrator Jobが作成される
And Jobパラメータに "ISSUE_URL" が含まれる
```

---

## 7. スコープ外

以下の機能は将来バージョンで対応予定：

| 機能 | 理由 | 対応予定 |
|------|------|---------|
| Phase 1-6の実行機能 | MVP v1.0.0はフレームワーク構築のみ | v1.1.0以降で段階的実装 |
| PR自動作成機能 | Gitワークフロー統合が必要 | v1.3.0以降 |
| リアルタイムモニタリングUI | フロントエンド開発が必要 | v2.0.0以降 |
| 複数Issue同時実行 | 並行処理制御が複雑 | v2.0.0以降 |
| GitHub Webhook統合 | Issueトリガー自動化 | v2.0.0以降 |
| マルチリポジトリ対応 | 設定管理が複雑 | v3.0.0以降 |

---

## 8. データ構造定義

### 8.1 metadata.json スキーマ（MVP v1.0.0）

```json
{
  "issue_number": "304",
  "issue_url": "https://github.com/tielec/infrastructure-as-code/issues/304",
  "issue_title": "Issue #304",
  "workflow_version": "1.0.0",
  "current_phase": "requirements",
  "design_decisions": {
    "implementation_strategy": null,
    "test_strategy": null,
    "test_code_strategy": null
  },
  "cost_tracking": {
    "total_input_tokens": 0,
    "total_output_tokens": 0,
    "total_cost_usd": 0.0
  },
  "phases": {
    "requirements": {
      "status": "pending",
      "retry_count": 0,
      "started_at": null,
      "completed_at": null,
      "review_result": null
    },
    "design": {
      "status": "pending",
      "retry_count": 0,
      "started_at": null,
      "completed_at": null,
      "review_result": null
    },
    "test_scenario": {
      "status": "pending",
      "retry_count": 0,
      "started_at": null,
      "completed_at": null,
      "review_result": null
    },
    "implementation": {
      "status": "pending",
      "retry_count": 0,
      "started_at": null,
      "completed_at": null,
      "review_result": null
    },
    "testing": {
      "status": "pending",
      "retry_count": 0,
      "started_at": null,
      "completed_at": null,
      "review_result": null
    },
    "documentation": {
      "status": "pending",
      "retry_count": 0,
      "started_at": null,
      "completed_at": null,
      "review_result": null
    }
  },
  "created_at": "2025-10-08T01:07:54.281813Z",
  "updated_at": "2025-10-08T01:07:54.281813Z"
}
```

### 8.2 フィールド定義

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|-----|------|
| issue_number | String | ✓ | GitHub Issue番号 |
| issue_url | String | ✓ | GitHub Issue URL |
| issue_title | String | ✓ | Issue タイトル |
| workflow_version | String | ✓ | ワークフローバージョン（"1.0.0"） |
| current_phase | String | ✓ | 現在のフェーズ（requirements～documentation） |
| design_decisions | Object | ✓ | Phase 2での設計判断（将来実装） |
| cost_tracking | Object | ✓ | API利用コスト追跡 |
| phases | Object | ✓ | 6フェーズの状態管理 |
| phases.{phase}.status | Enum | ✓ | pending, in_progress, completed, failed |
| phases.{phase}.retry_count | Integer | ✓ | リトライ回数（0-3） |
| phases.{phase}.started_at | String | - | 開始時刻（ISO 8601） |
| phases.{phase}.completed_at | String | - | 完了時刻（ISO 8601） |
| phases.{phase}.review_result | String | - | PASS, PASS_WITH_SUGGESTIONS, FAIL（将来実装） |
| created_at | String | ✓ | 作成時刻（ISO 8601） |
| updated_at | String | ✓ | 更新時刻（ISO 8601） |

---

## 9. 成功基準

### 9.1 機能面

- [x] GitHub Issue URLからワークフロー初期化が可能（v1.0.0で実装済み）
- [x] metadata.jsonが正しく生成され、6フェーズが定義される（v1.0.0で実装済み）
- [x] CLIコマンド（init）が動作する（v1.0.0で実装済み）
- [x] BDDテストが成功する（v1.0.0で実装済み）
- [x] Jenkins Job DSLとJenkinsfileが定義される（v1.0.0で実装済み）
- [x] Docker環境で実行可能（v1.1.0で実装済み）
- [x] Phase 1（要件定義）が実行可能（v1.1.0で実装済み）
- [ ] Phase 2-6の実装（将来対応）
- [ ] PR自動作成機能（将来対応）

### 9.2 品質面

- [x] Pythonコードがクリーンで可読性が高い
- [x] エラーハンドリングが適切に実装されている
- [x] ドキュメント（README.md、ARCHITECTURE.md）が充実している
- [x] BDDテストでワークフロー動作が検証できる
- [ ] ユニットテストが実装される（将来対応）

### 9.3 運用面

- [x] Dockerイメージが正常にビルドできる
- [x] 環境変数による認証設定が可能
- [x] ローカル環境でのデバッグが容易
- [x] Jenkinsからの実行が可能（Job DSL定義済み）
- [ ] エラー時の適切な通知（将来対応）

---

## 10. リスク管理

| リスク | 影響度 | 発生確率 | 対策 | 担当 |
|--------|--------|---------|------|------|
| Claude API認証エラー | 高 | 中 | OAuth Token取得手順をDOCKER_AUTH_SETUP.mdに明記 | 開発者 |
| Docker環境での権限エラー | 中 | 中 | ボリュームマウントパスの検証、troubleshooting追加 | 開発者 |
| metadata.json破損 | 高 | 低 | バックアップ機能、バリデーション強化 | 将来対応 |
| GitHub Token期限切れ | 中 | 低 | エラーメッセージで明確に通知 | 開発者 |
| BDDテストの不安定性 | 低 | 低 | テストシナリオの冪等性確保 | 開発者 |

---

## 11. 参考資料

| ドキュメント | パス | 用途 |
|------------|------|------|
| プロジェクト全体ガイド | `/CLAUDE.md` | 開発方針、コーディング規約 |
| スクリプト開発ガイド | `/scripts/CONTRIBUTION.md` | Python開発ベストプラクティス |
| Jenkins開発ガイド | `/jenkins/CONTRIBUTION.md` | Job DSL、Jenkinsfile作成方法 |
| AI Workflow README | `/scripts/ai-workflow/README.md` | 使用方法、トラブルシューティング |
| AI Workflow Architecture | `/scripts/ai-workflow/ARCHITECTURE.md` | アーキテクチャ設計思想 |
| 要件定義書（参考） | `/ai-workflow-requirements.md` | 全体要件定義 |
| 設計書（参考） | `/ai-workflow-design.md` | 詳細設計 |

---

## 12. 用語集

| 用語 | 定義 |
|------|------|
| MVP | Minimum Viable Product（最小実用製品） |
| Agent SDK | Claude Code Agent SDK（AI実行基盤） |
| BDD | Behavior-Driven Development（振る舞い駆動開発） |
| Gherkin | BDDシナリオ記述言語（Given-When-Then形式） |
| metadata.json | ワークフロー状態を管理するJSONファイル |
| フェーズ | ワークフローの1ステップ（requirements, design等） |
| Job DSL | JenkinsでJobを定義するGroovyスクリプト |
| Jenkinsfile | Jenkinsパイプラインを定義するGroovyスクリプト |
| OAuth Token | Claude API認証トークン（`CLAUDE_CODE_OAUTH_TOKEN`） |
| PAT | Personal Access Token（GitHub認証トークン） |

---

## 13. 変更履歴

| バージョン | 日付 | 変更内容 | 作成者 |
|-----------|------|---------|--------|
| 1.0.0 | 2025-10-08 | 初版作成（Issue #304ベース、MVP v1.0.0スコープ） | Claude Code |

---

**承認**:
- [ ] 開発者レビュー
- [ ] ステークホルダー承認

**次フェーズ**: Phase 2（詳細設計）へ移行

---

**文書バージョン**: 1.0.0
**最終更新**: 2025-10-08
**ステータス**: レビュー待ち
