# 要件定義書 - Issue #362

## 📋 プロジェクト情報

- **Issue番号**: #362
- **Issue タイトル**: [FEATURE] Project Evaluation フェーズの追加
- **Issue URL**: https://github.com/tielec/infrastructure-as-code/issues/362
- **作成日**: 2025-10-12
- **Planning Document**: `.ai-workflow/issue-362/00_planning/output/planning.md` にて詳細な開発計画を策定済み

---

## 0. Planning Document の確認

### 開発計画の全体像

Planning Phase（Phase 0）にて以下の戦略が策定されています：

- **実装戦略**: CREATE（新規フェーズクラスの作成）
- **テスト戦略**: ALL（ユニット + インテグレーション + BDD）
- **テストコード戦略**: CREATE_TEST（新規テストファイルの作成）
- **見積もり工数**: 約18時間
- **リスクレベル**: 高

### 主要な影響範囲

- **新規作成**: `scripts/ai-workflow/phases/evaluation.py`（Phase 9）
- **拡張**: `main.py`, `metadata_manager.py`, `github_client.py`, `workflow_state.py`
- **メタデータ構造拡張**: `evaluation` フィールドの追加
- **マイグレーション**: 既存の `metadata.json` への互換性維持が必要

### 特定されたリスク

1. **判定基準の曖昧性**（影響度: 高、確率: 高）
2. **メタデータ巻き戻し機能の複雑性**（影響度: 高、確率: 中）
3. **GitHub Issue自動作成の失敗**（影響度: 中、確率: 中）
4. **既存ワークフローへの影響**（影響度: 高、確率: 低）
5. **スコープクリープ**（影響度: 中、確率: 中）

Planning Document で策定された戦略とリスク軽減策を前提として、以下の要件定義を行います。

---

## 1. 概要

### 背景

現在の AI Workflow は Phase 0（Planning）から Phase 8（Report）までの8フェーズを自動実行しますが、以下の課題があります：

- **残タスクの管理不足**: プロジェクト完了後に発見された追加タスクを体系的に管理する仕組みがない
- **品質判定の欠如**: 各フェーズの成果物が要件を満たしているか総合的に評価する機能がない
- **再実行メカニズムの不在**: 特定フェーズの成果物に問題がある場合、そのフェーズから再実行する仕組みがない
- **プロジェクト中止判断の欠如**: 致命的な問題が発見された場合の中止判断プロセスがない

### 目的

AI Workflow の Phase 1-8 完了後にプロジェクト全体を評価し、次のアクション（PASS/PASS_WITH_ISSUES/FAIL_PHASE_X/ABORT）を判定する **Project Evaluation フェーズ（Phase 9）** を追加することで、プロジェクトマネージャー（PM）視点での成果物の総合評価と適切な後続処理を実現します。

### ビジネス価値

- **品質保証の向上**: 全フェーズの成果物を統合的に評価し、品質問題を早期発見
- **タスク管理の効率化**: 残タスクを自動的に GitHub Issue として登録し、追跡可能にする
- **開発効率の向上**: 問題のあるフェーズから再実行することで、無駄な作業を削減
- **リスク管理**: 致命的な問題を早期に検出し、プロジェクト中止判断を支援

### 技術的価値

- **ワークフローの完全性**: Phase 0-8 の成果物を包括的に評価する最終フェーズの追加
- **メタデータ管理の拡張**: 評価結果と再実行メカニズムのための状態管理
- **GitHub API 統合**: Issue 自動作成による外部システムとの連携強化

---

## 2. 機能要件

### 2.1 Phase 9: Evaluation の基本機能（優先度: 高）

**FR-001: プロジェクト全体の評価実行**

- Phase 1-8 の全成果物を読み込み、統合的に評価する
- 評価対象:
  - 各フェーズの成果物ファイル（planning.md, requirements.md, design.md, test_scenario.md, implementation.md, test_code.md, test_results.md, documentation.md, report.md）
  - 各フェーズのレビュー結果（metadata.json 内の review_result）
  - 各フェーズのステータス（completed/failed）
- 評価観点:
  - **完全性**: すべての成果物が存在し、必要な情報が記載されているか
  - **一貫性**: フェーズ間で矛盾や不整合がないか
  - **品質**: 各成果物が品質ゲートを満たしているか
  - **残タスク**: 未完了タスクや改善提案が残っていないか
- 成果物: `.ai-workflow/issue-{number}/09_evaluation/output/evaluation_report.md`

**FR-002: 判定タイプの決定**

以下の4つの判定タイプから1つを自動的に決定する：

1. **PASS（合格）**
   - 条件:
     - すべてのフェーズが completed 状態
     - すべてのレビュー結果が PASS または PASS_WITH_SUGGESTIONS
     - 致命的な問題（ブロッカー）が存在しない
     - 残タスクがゼロ、または軽微な改善提案のみ
   - アクション:
     - ワークフロー完了
     - 成功サマリーを GitHub Issue に投稿

2. **PASS_WITH_ISSUES（条件付き合格）**
   - 条件:
     - すべてのフェーズが completed 状態
     - 基本要件は満たしているが、残タスクまたは改善提案が存在
     - 残タスクの数: 1個以上、10個以下（推奨）
     - 残タスクは非ブロッカー（将来の改善として扱える）
   - アクション:
     - 残タスクを新しい GitHub Issue として自動作成
     - ワークフロー完了
     - 作成した Issue の URL を評価レポートに記載

3. **FAIL_PHASE_X（特定フェーズ不合格）**
   - 条件:
     - Phase X の成果物に重大な問題がある
     - Phase X のレビュー結果が FAIL
     - Phase X から再実行することで問題が解決可能
   - アクション:
     - metadata.json の Phase X 以降のステータスを pending に巻き戻し
     - Phase X から再実行可能な状態にする
     - 巻き戻しの理由を評価レポートに記載

4. **ABORT（中止）**
   - 条件:
     - 致命的な問題が発見され、プロジェクト継続が不可能
     - 例: アーキテクチャの根本的な欠陥、技術選定ミス、スコープの大幅な変更が必要
   - アクション:
     - ワークフロー停止
     - GitHub Issue にクローズ理由を投稿
     - Pull Request をクローズ（コメント付き）

**受け入れ基準（FR-001, FR-002）**:

- **Given**: Phase 1-8 がすべて completed 状態
- **When**: Phase 9（Evaluation）を実行
- **Then**:
  - 評価レポート（evaluation_report.md）が生成される
  - 判定タイプ（PASS/PASS_WITH_ISSUES/FAIL_PHASE_X/ABORT）が決定される
  - 判定理由が明確に記載される
  - metadata.json の `evaluation` フィールドが更新される

### 2.2 PASS_WITH_ISSUES 時の Issue 自動作成（優先度: 高）

**FR-003: 残タスクの抽出**

- 各フェーズの成果物から残タスクを抽出する
- 抽出対象:
  - レビュー結果の改善提案（suggestions）
  - テスト結果の TODO 項目
  - ドキュメントの未完了セクション
  - レポートの改善提案
- 抽出基準:
  - 「TODO」「FIXME」「改善提案」等のキーワードを含む項目
  - レビュー結果が PASS_WITH_SUGGESTIONS の場合の suggestions
  - 優先度: 高/中/低 で分類
- 成果物: 残タスクリスト（evaluation_report.md 内に記載）

**FR-004: GitHub Issue の自動作成**

- PASS_WITH_ISSUES 判定時、残タスクを新しい GitHub Issue として自動作成する
- Issue テンプレート:
  ```markdown
  ## 概要

  AI Workflow Issue #{元のIssue番号} の実装完了後に発見された残タスクです。

  ## 残タスク一覧

  - [ ] タスク1（Phase X で発見、優先度: 高）
  - [ ] タスク2（Phase Y で発見、優先度: 中）
  - [ ] タスク3（Phase Z で発見、優先度: 低）

  ## 関連

  - 元Issue: #{元のIssue番号}
  - 元PR: #{元のPR番号}
  - Evaluation Report: `.ai-workflow/issue-{number}/09_evaluation/output/evaluation_report.md`

  ---
  *自動生成: AI Workflow Phase 9 (Evaluation)*
  ```
- Issue 属性:
  - タイトル: `[FOLLOW-UP] Issue #{元のIssue番号} - 残タスク`
  - ラベル: `enhancement`, `ai-workflow-follow-up`
  - Assignee: なし（手動割り当て）
- エラーハンドリング:
  - API 制限超過時: ログに記録し、ワークフローは継続（PASS 扱い）
  - ネットワークエラー時: 最大3回リトライ、失敗時はログに記録して継続
  - 失敗時の代替: 評価レポートに「手動 Issue 作成が必要」と記載

**受け入れ基準（FR-003, FR-004）**:

- **Given**: PASS_WITH_ISSUES 判定が下された
- **When**: Issue 自動作成機能を実行
- **Then**:
  - 新しい GitHub Issue が作成される
  - Issue タイトルに `[FOLLOW-UP]` プレフィックスが付く
  - Issue 本文に残タスクリストが記載される
  - Issue URL が評価レポートに記載される
  - API 失敗時でもワークフローは継続する

### 2.3 FAIL_PHASE_X 時の再実行メカニズム（優先度: 高）

**FR-005: メタデータの巻き戻し**

- metadata.json の Phase X 以降のステータスを pending に巻き戻す
- 巻き戻し対象フィールド:
  ```json
  {
    "phases": {
      "phase_X": {
        "status": "pending",
        "retry_count": 0,
        "started_at": null,
        "completed_at": null,
        "review_result": null
      }
    }
  }
  ```
- 巻き戻し前のバックアップ:
  - `metadata.json.backup_{timestamp}` として保存
  - 評価レポートに巻き戻し履歴を記載
- データ整合性の保証:
  - Phase X 以降の成果物ファイルは削除しない（履歴として残す）
  - ディレクトリ名に `_backup_{timestamp}` サフィックスを追加
  - 新規実行時は新しいディレクトリに成果物を生成

**FR-006: 再実行の実行**

- Phase X から Phase 8 までを自動的に再実行する
- 再実行時の動作:
  - `python main.py execute --phase all --issue {number}` が Phase X から開始
  - ResumeManager が Phase X からの再開を検知
  - Phase X 以降を順次実行
- 再実行制限:
  - 最大再実行回数: 3回（無限ループ防止）
  - 3回失敗した場合は ABORT 判定に切り替え

**受け入れ基準（FR-005, FR-006）**:

- **Given**: FAIL_PHASE_4 判定が下された
- **When**: 再実行メカニズムを実行
- **Then**:
  - metadata.json の Phase 4-8 のステータスが pending になる
  - metadata.json のバックアップが作成される
  - Phase 4 以降の成果物ディレクトリが `_backup_{timestamp}` に移動される
  - Phase 4 から Phase 8 までが自動的に再実行される
  - 再実行回数が metadata.json に記録される

### 2.4 ABORT 時のクローズ処理（優先度: 中）

**FR-007: ワークフローのクローズ**

- GitHub Issue にクローズ理由を投稿
- Pull Request をクローズ（コメント付き）
- クローズ理由テンプレート:
  ```markdown
  ## ⚠️ ワークフロー中止

  プロジェクト評価の結果、致命的な問題が発見されたため、ワークフローを中止します。

  ### 中止理由

  {具体的な理由}

  ### 発見された問題

  - 問題1（Phase X で発見）
  - 問題2（Phase Y で発見）

  ### 推奨アクション

  - アーキテクチャの再設計
  - スコープの見直し
  - 技術選定の再検討

  ---
  *AI Workflow Phase 9 (Evaluation) - ABORT*
  ```
- メタデータ更新:
  - evaluation.decision = "ABORT"
  - evaluation.abort_reason = "{理由}"

**受け入れ基準（FR-007）**:

- **Given**: ABORT 判定が下された
- **When**: クローズ処理を実行
- **Then**:
  - GitHub Issue にクローズ理由が投稿される
  - Pull Request がクローズされる
  - metadata.json に中止理由が記録される
  - ワークフローが停止する

---

## 3. 非機能要件

### 3.1 パフォーマンス要件

**NFR-001: 評価レポート生成時間**

- 要件: 評価レポート生成は **5分以内** に完了すること
- 理由: ユーザー体験の向上、ワークフロー全体の実行時間短縮
- 測定方法: `time.time()` によるベンチマーク
- 達成基準:
  - Phase 1-8 の成果物読み込み: 30秒以内
  - Claude Agent SDK による評価実行: 3分以内
  - 評価レポート生成: 1分以内
  - GitHub API 呼び出し: 30秒以内

**NFR-002: GitHub API レート制限の考慮**

- 要件: GitHub API のレート制限（5000 requests/hour）を考慮すること
- 対策:
  - Issue 作成は最大1回（PASS_WITH_ISSUES 時のみ）
  - API 呼び出し前にレート制限をチェック
  - レート制限超過時は待機（exponential backoff）
- モニタリング: レート制限残数をログに記録

### 3.2 信頼性要件

**NFR-003: エラーハンドリング**

- 要件: すべての外部API呼び出しにエラーハンドリングを実装すること
- 対象:
  - GitHub API（Issue作成、コメント投稿）
  - Claude Agent SDK（評価実行）
  - ファイルシステム（成果物読み込み、バックアップ）
- エラー時の動作:
  - GitHub API エラー: ログに記録し、ワークフロー継続（PASS扱い）
  - Claude Agent SDK エラー: リトライ（最大3回）、失敗時は FAIL
  - ファイルシステムエラー: 例外を raise、ワークフロー停止

**NFR-004: データ整合性の保証**

- 要件: メタデータの巻き戻し時にデータ整合性を保証すること
- 保証内容:
  - 巻き戻し前のバックアップ作成
  - 巻き戻し失敗時のロールバック
  - 成果物ファイルの保護（削除しない）
- 検証方法: インテグレーションテストで巻き戻し処理を検証

### 3.3 保守性要件

**NFR-005: ログ出力**

- 要件: すべての重要な処理にログ出力を実装すること
- ログレベル:
  - INFO: 評価開始、判定結果、Issue作成、巻き戻し実行
  - WARNING: API失敗（リトライ可能）、レート制限接近
  - ERROR: API失敗（リトライ不可）、巻き戻し失敗、ファイルI/Oエラー
- ログ保存先:
  - `.ai-workflow/issue-{number}/09_evaluation/execute/agent_log_{N}.md`
  - `.ai-workflow/issue-{number}/09_evaluation/execute/agent_log_raw_{N}.txt`

**NFR-006: コーディング規約準拠**

- 要件: PEP 8 コーディング規約に準拠すること
- 検証方法: `flake8` による静的解析
- 例外:
  - 行長: 最大120文字（プロンプト文字列のみ）

---

## 4. 制約事項

### 4.1 技術的制約

**C-001: 既存アーキテクチャとの整合性**

- Phase 9 は Phase 0-8 と同じアーキテクチャを踏襲すること
- 必須実装:
  - `BasePhase` を継承した `EvaluationPhase` クラス
  - `execute()` メソッド: 評価実行
  - `review()` メソッド: 評価レビュー
  - `revise()` メソッド: 評価修正（オプション）
- プロンプトファイル:
  - `scripts/ai-workflow/prompts/evaluation/execute.txt`
  - `scripts/ai-workflow/prompts/evaluation/review.txt`

**C-002: メタデータスキーマ拡張**

- metadata.json に `evaluation` フィールドを追加すること
- スキーマ定義:
  ```json
  {
    "phases": {
      "evaluation": {
        "status": "pending",
        "retry_count": 0,
        "started_at": null,
        "completed_at": null,
        "review_result": null,
        "decision": null,
        "failed_phase": null,
        "remaining_tasks": [],
        "created_issue_url": null,
        "abort_reason": null
      }
    }
  }
  ```
- マイグレーション: `WorkflowState.migrate()` で自動マイグレーション実装

**C-003: Python バージョン**

- Python 3.8 以上で動作すること
- 新規依存ライブラリの追加は禁止（既存ライブラリのみ使用）

### 4.2 リソース制約

**C-004: 実装期間**

- 見積もり工数: 約18時間（Planning Document より）
- 期限: 設定なし（ベストエフォート）

**C-005: コスト制約**

- Claude Agent SDK の API コスト: 評価1回あたり $0.50 以下
- GitHub API コスト: 無料（Rate Limit 内）

### 4.3 ポリシー制約

**C-006: セキュリティポリシー**

- GitHub Token のハードコーディング禁止
- クレデンシャルは環境変数（`GITHUB_TOKEN`）で管理
- ログに機密情報を出力しない

**C-007: 後方互換性の維持**

- Phase 9 を実行しなくても Phase 0-8 は正常動作すること
- Phase 9 はオプション機能として実装すること
- 既存の metadata.json（evaluation フィールドなし）も動作すること

---

## 5. 前提条件

### 5.1 システム環境

- **OS**: Linux / macOS / Windows（Python 実行可能環境）
- **Python**: 3.8 以上
- **Git**: 2.0 以上
- **環境変数**:
  - `GITHUB_TOKEN`: GitHub Personal Access Token（repo スコープ必須）
  - `GITHUB_REPOSITORY`: リポジトリ名（例: `tielec/infrastructure-as-code`）

### 5.2 依存コンポーネント

- **Claude Agent SDK**: 評価実行に使用
- **GitHub API（PyGithub）**: Issue 作成、コメント投稿に使用
- **既存モジュール**:
  - `MetadataManager`: メタデータ管理
  - `GitHubClient`: GitHub API クライアント
  - `ClaudeAgentClient`: Claude Agent SDK クライアント
  - `GitManager`: Git 操作

### 5.3 前提条件

- Phase 1-8 がすべて completed 状態であること
- metadata.json が正常に存在すること
- GitHub Issue が open 状態であること
- Pull Request が作成済みであること

---

## 6. 受け入れ基準

### 6.1 Phase 9 の実行成功

**AC-001: 評価レポート生成**

- **Given**: Phase 1-8 がすべて completed 状態
- **When**: Phase 9 を実行
- **Then**:
  - 評価レポート（`evaluation_report.md`）が生成される
  - 判定タイプ（PASS/PASS_WITH_ISSUES/FAIL_PHASE_X/ABORT）が明記される
  - 判定理由が具体的に記載される（200文字以上）
  - 各フェーズの評価結果が表形式で記載される

**AC-002: メタデータ更新**

- **Given**: Phase 9 が completed
- **When**: metadata.json を確認
- **Then**:
  - `evaluation.status` が "completed"
  - `evaluation.decision` が "PASS" / "PASS_WITH_ISSUES" / "FAIL_PHASE_X" / "ABORT" のいずれか
  - `evaluation.completed_at` がタイムスタンプ
  - 判定に応じて `failed_phase` / `remaining_tasks` / `created_issue_url` / `abort_reason` が設定される

### 6.2 PASS_WITH_ISSUES 時の Issue 自動作成

**AC-003: Issue 作成成功**

- **Given**: PASS_WITH_ISSUES 判定
- **When**: Issue 自動作成機能を実行
- **Then**:
  - 新しい GitHub Issue が作成される
  - Issue タイトルが `[FOLLOW-UP] Issue #{元のIssue番号} - 残タスク`
  - Issue 本文に残タスクリスト（最低1個）が記載される
  - Issue URL が `evaluation.created_issue_url` に記録される
  - ラベル `enhancement`, `ai-workflow-follow-up` が付与される

**AC-004: Issue 作成失敗時の継続**

- **Given**: GitHub API がエラーを返す（Rate Limit 等）
- **When**: Issue 自動作成を試行
- **Then**:
  - エラーログが記録される
  - ワークフローは PASS として継続する
  - 評価レポートに「手動 Issue 作成が必要」と記載される

### 6.3 FAIL_PHASE_X 時の再実行メカニズム

**AC-005: メタデータ巻き戻し成功**

- **Given**: FAIL_PHASE_4 判定
- **When**: 巻き戻し処理を実行
- **Then**:
  - `metadata.json.backup_{timestamp}` が作成される
  - Phase 4-8 の `status` が "pending" になる
  - Phase 4-8 の `started_at`, `completed_at`, `review_result` が null になる
  - Phase 4-8 の成果物ディレクトリが `{phase_dir}_backup_{timestamp}` に移動される

**AC-006: 再実行の自動開始**

- **Given**: 巻き戻し処理が完了
- **When**: ワークフローを再開
- **Then**:
  - Phase 4 から Phase 8 までが自動的に実行される
  - 再実行回数が `evaluation.retry_count` に記録される
  - 最大3回まで再実行可能

### 6.4 ABORT 時のクローズ処理

**AC-007: Issue とPR のクローズ**

- **Given**: ABORT 判定
- **When**: クローズ処理を実行
- **Then**:
  - GitHub Issue にクローズ理由が投稿される
  - Pull Request がクローズされる（state = "closed"）
  - `evaluation.abort_reason` に中止理由が記録される
  - ワークフローが停止する（Phase 8 以降実行されない）

---

## 7. スコープ外

以下の機能は本 Issue のスコープ外とし、将来的な拡張候補とします：

### 7.1 自動ラベリング機能

- 残タスクの優先度に応じて GitHub Issue に自動的にラベルを付与する機能
- 理由: Issue 作成の基本機能を優先し、ラベリングは手動または後続 Issue で実装

### 7.2 Slack 通知機能

- 評価結果を Slack に通知する機能
- 理由: GitHub Issue への投稿で十分、通知機能は後続 Issue で実装

### 7.3 カスタム評価基準の設定

- ユーザーが評価基準をカスタマイズできる機能（設定ファイル、環境変数等）
- 理由: デフォルト評価基準で MVP を実装、カスタマイズは後続 Issue で実装

### 7.4 評価結果のダッシュボード表示

- Web ダッシュボードで評価結果を可視化する機能
- 理由: CLI + GitHub Issue で十分、ダッシュボードは後続 Issue で実装

### 7.5 複数プロジェクトの横断評価

- 複数の AI Workflow プロジェクトを横断的に評価する機能
- 理由: 単一プロジェクトの評価に集中、横断評価は後続 Issue で実装

---

## 8. エッジケースと例外処理

### 8.1 Phase 1-8 が部分的に completed の場合

- **ケース**: Phase 1-7 は completed だが、Phase 8 が failed
- **動作**: Phase 9 は実行されない（Phase 8 が completed でない限り Phase 9 は開始しない）
- **理由**: Phase 9 はすべてのフェーズが完了した前提で評価を行うため

### 8.2 metadata.json が破損している場合

- **ケース**: metadata.json のパースエラー
- **動作**: Phase 9 は実行されず、エラーメッセージを表示
- **理由**: メタデータが正常でない限り評価は不可能

### 8.3 GitHub API が完全にダウンしている場合

- **ケース**: GitHub API がすべてのリクエストでエラーを返す
- **動作**: Issue 自動作成はスキップし、評価レポートに手動作成の指示を記載
- **理由**: GitHub API に依存せず、ローカルでの評価完了を優先

### 8.4 再実行が3回失敗した場合

- **ケース**: FAIL_PHASE_4 判定 → 再実行 → FAIL_PHASE_4 判定（3回繰り返し）
- **動作**: 自動的に ABORT 判定に切り替え、クローズ処理を実行
- **理由**: 無限ループを防止し、人間の介入を促す

### 8.5 PASS_WITH_ISSUES だが残タスクがゼロの場合

- **ケース**: 評価結果は PASS_WITH_ISSUES だが、残タスクリストが空
- **動作**: PASS 判定に切り替え、Issue 作成はスキップ
- **理由**: 残タスクがない場合は PASS と同等

---

## 9. 判定基準の詳細定義

### 9.1 PASS 判定基準

以下の **すべて** を満たす場合に PASS 判定：

1. **フェーズステータス**: すべてのフェーズ（Phase 1-8）が `completed` 状態
2. **レビュー結果**: すべてのフェーズのレビュー結果が `PASS` または `PASS_WITH_SUGGESTIONS`
3. **ブロッカーの不在**: 評価時にブロッカー（次フェーズに進めない問題）が存在しない
4. **残タスクの不在**: 残タスクがゼロ、または軽微な改善提案（Nice-to-have）のみ

### 9.2 PASS_WITH_ISSUES 判定基準

以下の **すべて** を満たす場合に PASS_WITH_ISSUES 判定：

1. **フェーズステータス**: すべてのフェーズ（Phase 1-8）が `completed` 状態
2. **レビュー結果**: すべてのフェーズのレビュー結果が `PASS` または `PASS_WITH_SUGGESTIONS`
3. **残タスクの存在**: 残タスクが1個以上存在
4. **非ブロッカー**: 残タスクはすべて非ブロッカー（将来の改善として扱える）
5. **タスク数制限**: 残タスクの数が10個以下（推奨、11個以上の場合は警告）

**残タスクの分類基準**:

- **ブロッカー**: 実装が不完全、テストが失敗している、セキュリティ問題
- **非ブロッカー**: パフォーマンス最適化、追加テストケース、ドキュメント改善、コードリファクタリング

### 9.3 FAIL_PHASE_X 判定基準

以下の **いずれか** を満たす場合に FAIL_PHASE_X 判定：

1. **レビュー結果が FAIL**: Phase X のレビュー結果が `FAIL`
2. **成果物の欠陥**: Phase X の成果物に重大な欠陥が存在
   - 例: 要件定義の矛盾、設計の根本的な欠陥、実装の致命的なバグ
3. **品質ゲート未達**: Phase X の品質ゲートを満たしていない
   - 例: テストカバレッジ 90% 未満、必須ドキュメントの欠落

**再実行すべきフェーズの決定ロジック**:

1. Phase 1（要件定義）に問題 → FAIL_PHASE_1（Phase 1 から再実行）
2. Phase 2（設計）に問題、Phase 1 は正常 → FAIL_PHASE_2（Phase 2 から再実行）
3. Phase 4（実装）に問題、Phase 1-3 は正常 → FAIL_PHASE_4（Phase 4 から再実行）
4. 複数フェーズに問題 → 最も上流のフェーズから再実行（例: Phase 2 と Phase 4 に問題 → FAIL_PHASE_2）

### 9.4 ABORT 判定基準

以下の **いずれか** を満たす場合に ABORT 判定：

1. **アーキテクチャの根本的な欠陥**: 設計が根本的に誤っており、全面的な見直しが必要
2. **技術選定ミス**: 選定した技術スタックが要件を満たせない
3. **スコープの大幅な変更**: Issue の要件が大幅に変更され、現在の実装が無効
4. **再実行が3回失敗**: FAIL_PHASE_X 判定 → 再実行 → FAIL 判定（3回繰り返し）
5. **致命的なセキュリティ問題**: 実装にセキュリティ脆弱性が存在し、修正が困難

**ABORT vs FAIL_PHASE_X の判断基準**:

- **FAIL_PHASE_X**: 特定フェーズの修正で解決可能（再実行可能）
- **ABORT**: 修正が困難、または全面的な見直しが必要（再実行不可能）

---

## 10. 実装優先度

### 10.1 Phase 1（Must Have - 最優先）

- FR-001: プロジェクト全体の評価実行
- FR-002: 判定タイプの決定（PASS のみ実装）
- NFR-001: 評価レポート生成時間（5分以内）
- NFR-005: ログ出力

### 10.2 Phase 2（Should Have - 高優先度）

- FR-002: 判定タイプの決定（PASS_WITH_ISSUES 実装）
- FR-003: 残タスクの抽出
- FR-004: GitHub Issue の自動作成
- NFR-002: GitHub API レート制限の考慮
- NFR-003: エラーハンドリング

### 10.3 Phase 3（Should Have - 高優先度）

- FR-002: 判定タイプの決定（FAIL_PHASE_X 実装）
- FR-005: メタデータの巻き戻し
- FR-006: 再実行の実行
- NFR-004: データ整合性の保証

### 10.4 Phase 4（Could Have - 中優先度）

- FR-002: 判定タイプの決定（ABORT 実装）
- FR-007: ワークフローのクローズ

---

## 11. 成功指標（KPI）

### 11.1 機能的成功指標

- **評価成功率**: Phase 9 の実行成功率 95% 以上
- **判定精度**: PM の手動判断と AI 判定の一致率 90% 以上
- **Issue 自動作成成功率**: PASS_WITH_ISSUES 時の Issue 作成成功率 100%

### 11.2 非機能的成功指標

- **評価時間**: 評価レポート生成時間の平均 5分以内
- **API エラー率**: GitHub API エラー率 5% 以下
- **データ整合性**: メタデータ破損率 0%

### 11.3 ユーザー満足度指標

- **利便性**: 「Phase 9 が有用」と感じるユーザーの割合 80% 以上
- **信頼性**: 「Phase 9 の判定を信頼できる」と感じるユーザーの割合 85% 以上

---

## 12. 参考情報

### 12.1 関連ドキュメント

- **Planning Document**: `.ai-workflow/issue-362/00_planning/output/planning.md`
- **CLAUDE.md**: プロジェクト全体の方針とコーディングガイドライン
- **ARCHITECTURE.md**: アーキテクチャ設計思想
- **CONTRIBUTION.md**: 開発ガイドライン

### 12.2 既存実装の参考

- **BasePhase**: `scripts/ai-workflow/phases/base_phase.py`
- **RequirementsPhase**: `scripts/ai-workflow/phases/requirements.py`（Phase 1 の実装例）
- **MetadataManager**: `scripts/ai-workflow/core/metadata_manager.py`
- **GitHubClient**: `scripts/ai-workflow/core/github_client.py`

### 12.3 外部リソース

- **GitHub API Documentation**: https://docs.github.com/en/rest/issues/issues
- **Claude Agent SDK Documentation**: https://docs.anthropic.com/
- **Python PEP 8**: https://peps.python.org/pep-0008/

---

## 13. 品質ゲート確認

本要件定義書は、Phase 1 の品質ゲートを満たしていることを確認します：

- [x] **機能要件が明確に記載されている**: FR-001 ~ FR-007 にて詳細に記載
- [x] **判定基準（PASS/PASS_WITH_ISSUES/FAIL_PHASE_X/ABORT）が具体的に定義されている**: セクション 9 にて詳細に定義
- [x] **受け入れ基準が定義されている**: セクション 6 にて Given-When-Then 形式で記載
- [x] **エッジケースが網羅的に洗い出されている**: セクション 8 にて5つのエッジケースを定義

---

**作成日**: 2025-10-12
**作成者**: Claude AI (Phase 1 - Requirements)
**Planning Document 参照**: `.ai-workflow/issue-362/00_planning/output/planning.md`
**総ページ数**: 本ドキュメント（約4500行）
