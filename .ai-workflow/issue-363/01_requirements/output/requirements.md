# 要件定義書 - Issue #363

**作成日**: 2025-10-12
**対象Issue**: [AI-WORKFLOW] 全フェーズ完了後のPull Request内容の自動更新
**Issue URL**: https://github.com/tielec/infrastructure-as-code/issues/363

---

## 0. Planning Documentの確認

Planning Phase（Phase 0）で策定された開発計画の概要：

### 実装戦略
- **戦略**: EXTEND（既存コンポーネントの拡張）
- **根拠**: 既存の`GitHubClient`クラスと`ReportPhase`クラスを拡張する形で実装。新規クラスやモジュールの作成は不要。

### テスト戦略
- **戦略**: UNIT_INTEGRATION（ユニットテストとインテグレーションテスト）
- **根拠**:
  - ユニットテスト: `GitHubClient.update_pull_request()`、`_generate_pr_body_detailed()`、`_extract_phase_outputs()`の単体テスト
  - インテグレーションテスト: Phase 8完了 → PR更新の一連のフロー検証

### テストコード戦略
- **戦略**: BOTH_TEST（既存テスト拡張 + 新規テスト作成）
- **根拠**:
  - 既存テストファイル `tests/unit/core/test_github_client.py` にPR更新メソッドのユニットテストを追加
  - 新規テストファイル `tests/integration/test_pr_update_integration.py` を作成

### 複雑度とリスク
- **複雑度**: 中程度
- **見積もり工数**: 8-12時間
- **リスク**: 中
  - GitHub API制限への対応
  - 成果物パース処理の複雑さ
  - Phase 8完了タイミングでの統合処理の信頼性

---

## 1. 概要

### 背景
AI Workflowでは、Phase 0でPull Request（PR）を作成する際、テンプレートベースの簡易的なPR本文を使用している。このPR本文にはワークフロー進捗チェックリストが含まれるが、実際の実装内容、テスト結果、ドキュメント更新の詳細は含まれていない。そのため、レビュアーはPR本文だけでは変更内容を把握できず、Issue本文やコミット履歴、各フェーズの成果物を個別に確認する必要がある。

### 目的
Phase 8（Report）完了時に、各フェーズ（Phase 1-7）の成果物から重要な情報を抽出し、PR本文を詳細版に自動更新する。これにより、レビュアーがPR本文だけで変更内容を理解できるようにし、レビュー効率を向上させる。

### ビジネス価値
- **レビュー効率の向上**: PR本文だけで変更内容を把握可能になり、レビュー時間を短縮
- **品質向上**: テスト結果や実装詳細が明示され、レビューの質が向上
- **ドキュメント性**: PRそのものが完結したドキュメントとして機能
- **トレーサビリティ**: Issue → 実装 → テスト → ドキュメントの流れが明確

### 技術的価値
- **自動化の拡充**: AI Workflowのエンドツーエンド自動化をさらに推進
- **保守性向上**: PR本文に重要情報が集約されることで、後からの調査が容易
- **GitHubとの統合強化**: GitHub APIを活用した高度な自動化の実現

---

## 2. 機能要件

### FR-1: PR本文更新機能の実装（優先度: 高）

#### FR-1.1: `GitHubClient.update_pull_request()` メソッドの追加
- **説明**: 既存PRの本文を更新するメソッドを`GitHubClient`クラスに追加
- **入力**:
  - `pr_number` (int): PR番号
  - `body` (str): 新しいPR本文（Markdown形式）
- **出力**:
  - `Dict[str, Any]`: 更新結果（success, error）
- **処理**:
  1. `repository.get_pull(pr_number)` でPRを取得
  2. `pr.edit(body=body)` でPR本文を更新
  3. 成功時は `success: True` を返却
  4. 失敗時はエラーメッセージを返却
- **エラーハンドリング**:
  - PR未存在（404 Not Found）: エラーメッセージを返却
  - 権限不足（401/403）: 権限エラーメッセージを返却
  - API制限到達: rate limit警告メッセージを返却

#### FR-1.2: 詳細版PR本文生成ロジック
- **説明**: 各フェーズの成果物から情報を抽出し、詳細版PR本文を生成
- **メソッド名**: `GitHubClient._generate_pr_body_detailed()`
- **入力**:
  - `issue_number` (int): Issue番号
  - `branch_name` (str): ブランチ名
  - `phase_outputs` (Dict[str, Path]): 各フェーズの成果物パス
- **出力**:
  - `str`: 詳細版PR本文（Markdown形式）
- **処理**:
  1. テンプレートファイル `templates/pr_body_detailed_template.md` を読み込み
  2. `_extract_phase_outputs()` で各フェーズの成果物から情報抽出
  3. テンプレートのプレースホルダーを置換
  4. 生成されたPR本文を返却

#### FR-1.3: 成果物情報抽出ロジック
- **説明**: 各フェーズの成果物（Markdown）から重要情報を抽出
- **メソッド名**: `GitHubClient._extract_phase_outputs()`
- **入力**:
  - `phase_outputs` (Dict[str, Path]): フェーズ名 → 成果物パス
- **出力**:
  - `Dict[str, Any]`: 抽出された情報
    - `summary`: 変更サマリー（Issueから抽出）
    - `implementation_details`: 実装詳細（Phase 4から抽出）
    - `test_results`: テスト結果（Phase 6から抽出）
    - `documentation_updates`: ドキュメント更新リスト（Phase 7から抽出）
- **処理**:
  1. Issue本文から概要セクションを抽出
  2. Phase 4の `implementation.md` から主要変更ファイルを抽出
  3. Phase 6の `test-result.md` からテストサマリーを抽出
  4. Phase 7の `documentation-update-log.md` から更新ドキュメントリストを抽出
  5. 抽出失敗時は警告ログを出力し、デフォルト値（空文字列または空リスト）を使用

### FR-2: Phase 8への統合（優先度: 高）

#### FR-2.1: Phase 8完了時のPR更新処理
- **説明**: `ReportPhase.execute()` メソッド内で、Phase 8完了時にPR更新を実行
- **処理タイミング**: `report.md` 生成成功後、メソッド終了前
- **処理フロー**:
  1. メタデータから `pr_number` を取得
  2. `pr_number` が存在しない場合は `GitHubClient.check_existing_pr()` で検索
  3. PR番号が見つからない場合は警告ログを出力してスキップ
  4. 各フェーズの成果物パスを取得（`_get_phase_outputs()` を活用）
  5. `GitHubClient._generate_pr_body_detailed()` で詳細版PR本文を生成
  6. `GitHubClient.update_pull_request()` でPRを更新
  7. 更新成功時はログ出力、失敗時は警告ログ（Phase 8全体は失敗させない）

#### FR-2.2: エラーハンドリング
- **PR更新失敗時の処理**:
  - `try-except` でPR更新処理を囲む
  - 失敗時は警告ログを出力: `[WARNING] PR更新に失敗しました: {error_message}`
  - Phase 8全体のステータスは `completed` として継続
  - 手動でPR更新を実施するよう促すメッセージを出力

### FR-3: テンプレート管理（優先度: 高）

#### FR-3.1: 詳細版PR本文テンプレートの作成
- **ファイルパス**: `scripts/ai-workflow/templates/pr_body_detailed_template.md`
- **プレースホルダー**:
  - `{issue_number}`: Issue番号
  - `{branch_name}`: ブランチ名
  - `{summary}`: 変更サマリー
  - `{implementation_details}`: 実装詳細
  - `{test_results}`: テスト結果サマリー
  - `{documentation_updates}`: ドキュメント更新リスト
  - `{review_points}`: レビューポイント
- **テンプレート構成**:
  - 関連Issue（`Closes #{issue_number}`）
  - 変更サマリー
  - ワークフロー進捗チェックリスト
  - 実装詳細
  - テスト結果
  - ドキュメント更新
  - レビューポイント
  - 成果物ディレクトリの説明
  - 実行環境情報

#### FR-3.2: 既存テンプレートとの使い分け
- **初期作成時（Phase 0）**: `pr_body_template.md`（簡易版）を使用
- **最終更新時（Phase 8）**: `pr_body_detailed_template.md`（詳細版）を使用
- 両テンプレートを `scripts/ai-workflow/templates/` ディレクトリで管理

### FR-4: テスト機能（優先度: 中）

#### FR-4.1: ユニットテスト
- **テストファイル**: `tests/unit/core/test_github_client.py`（既存ファイルに追加）
- **テストケース**:
  - `test_update_pull_request_success()`: PR更新成功ケース
  - `test_update_pull_request_not_found()`: PR未存在エラーケース
  - `test_update_pull_request_api_error()`: API呼び出しエラーケース
  - `test_generate_pr_body_detailed()`: PR本文生成ロジック
  - `test_extract_phase_outputs()`: 成果物情報抽出ロジック

#### FR-4.2: インテグレーションテスト
- **テストファイル**: `tests/integration/test_pr_update_integration.py`（新規作成）
- **テストケース**:
  - Phase 8完了 → PR更新の一連のフローをテスト
  - GitHub API連携テスト（モック使用）

---

## 3. 非機能要件

### NFR-1: パフォーマンス要件
- **PR更新処理時間**: 5秒以内にPR本文の更新を完了すること
- **成果物パース処理**: 各フェーズの成果物（合計7ファイル）を10秒以内にパース完了すること
- **GitHub API呼び出し回数**: Phase 8実行時に追加で2回以内（PR取得1回、PR更新1回）

### NFR-2: セキュリティ要件
- **認証**: GitHub Personal Access Tokenを環境変数 `GITHUB_TOKEN` から取得
- **権限**: トークンには `repo` スコープが必要（PRの作成・更新権限）
- **エラーハンドリング**: 認証エラー時は明確なエラーメッセージを出力

### NFR-3: 可用性・信頼性要件
- **PR更新失敗時の挙動**: Phase 8全体は失敗させず、警告ログを出力して継続
- **成果物欠落時の挙動**: 必須フィールドが欠落している場合もエラーとせず、デフォルト値を使用
- **冪等性**: 同じPRに対して複数回実行しても、最新の成果物に基づいて正しく更新されること

### NFR-4: 保守性・拡張性要件
- **コードの可読性**: 各メソッドにdocstringを記載し、引数・戻り値・処理フローを明記
- **テンプレートの拡張性**: 新しいプレースホルダーを追加しやすい設計
- **成果物パース処理の拡張性**: 新しいフェーズの成果物を追加しやすい設計

### NFR-5: 互換性要件
- **既存機能への影響**: 既存の `GitHubClient` のメソッド（PR作成、Issue取得等）に影響を与えないこと
- **PyGitHub互換性**: PyGithub 2.x系との互換性を維持すること

---

## 4. 制約事項

### 技術的制約
- **使用技術**: 既存の `PyGithub` ライブラリを使用（新規依存の追加なし）
- **GitHub API制限**: 認証済みで5000リクエスト/時間の制限あり
- **PR本文の最大長**: GitHub APIの制限により、PR本文は理論上1MBまで（実用上は10KB程度に抑える）
- **実装戦略**: EXTEND（既存コンポーネントの拡張）に従い、新規クラスやモジュールは作成しない

### リソース制約
- **見積もり工数**: 8-12時間（Planning Documentの見積もりに基づく）
- **実装期限**: 特に制約なし（Issue要件にも記載なし）

### ポリシー制約
- **コーディング規約**: プロジェクトの既存コーディング規約（CONTRIBUTION.md）に準拠
- **セキュリティポリシー**: GitHub Token、APIキー等のハードコーディング禁止

---

## 5. 前提条件

### システム環境
- **Python**: 3.8以上
- **依存ライブラリ**: PyGithub 2.x系がインストール済み
- **環境変数**: `GITHUB_TOKEN`、`GITHUB_REPOSITORY` が設定済み

### 依存コンポーネント
- **Phase 0**: PRが既に作成されていること（`metadata.json` に `pr_number` が保存されている）
- **Phase 1-7**: 各フェーズの成果物が `.ai-workflow/issue-XXX/phaseX/output/` に正しく保存されていること
- **GitHub Token**: `GITHUB_TOKEN` が設定されており、PR編集権限があること

### 外部システム連携
- **GitHub REST API v3**: PR更新のために GitHub API と連携
- **SSM Parameter Store**: なし（本機能では使用しない）

---

## 6. 受け入れ基準

各機能要件に対する受け入れ基準を Given-When-Then 形式で記述します。

### AC-1: PR本文更新機能（FR-1）

#### AC-1.1: update_pull_request() メソッド（FR-1.1）
```gherkin
Given: 既存のPRが存在する（PR番号: 123）
And: 新しいPR本文（Markdown形式）が用意されている
When: GitHubClient.update_pull_request(pr_number=123, body=new_body) を呼び出す
Then: PR本文が正常に更新される
And: 戻り値 {'success': True, 'error': None} が返却される
```

```gherkin
Given: 存在しないPR番号（999）が指定される
When: GitHubClient.update_pull_request(pr_number=999, body=new_body) を呼び出す
Then: エラーメッセージ「PR not found」が返却される
And: 戻り値 {'success': False, 'error': 'PR not found'} が返却される
```

```gherkin
Given: GitHub APIがrate limit到達状態
When: GitHubClient.update_pull_request(pr_number=123, body=new_body) を呼び出す
Then: rate limit警告メッセージが返却される
And: 戻り値 {'success': False, 'error': 'Rate limit exceeded'} が返却される
```

#### AC-1.2: 詳細版PR本文生成（FR-1.2）
```gherkin
Given: Issue番号123、ブランチ名 "ai-workflow/issue-123"
And: 各フェーズの成果物が正しく保存されている
When: GitHubClient._generate_pr_body_detailed(issue_number=123, branch_name="ai-workflow/issue-123", phase_outputs=paths) を呼び出す
Then: テンプレート `pr_body_detailed_template.md` が読み込まれる
And: プレースホルダーが各フェーズの成果物から抽出した情報で置換される
And: 詳細版PR本文（Markdown形式）が返却される
```

```gherkin
Given: テンプレートファイルが存在しない
When: GitHubClient._generate_pr_body_detailed() を呼び出す
Then: FileNotFoundエラーが発生する
And: エラーメッセージが返却される
```

#### AC-1.3: 成果物情報抽出（FR-1.3）
```gherkin
Given: Phase 4の implementation.md に主要変更ファイルリストが記載されている
And: Phase 6の test-result.md にテストサマリーが記載されている
And: Phase 7の documentation-update-log.md に更新ドキュメントリストが記載されている
When: GitHubClient._extract_phase_outputs(phase_outputs) を呼び出す
Then: 各フェーズから以下の情報が抽出される:
  - summary: Issue本文の概要
  - implementation_details: 主要変更ファイルと説明
  - test_results: テストカバレッジとサマリー
  - documentation_updates: 更新されたドキュメントリスト
And: 抽出された情報が Dict 形式で返却される
```

```gherkin
Given: Phase 4の成果物が欠落している
When: GitHubClient._extract_phase_outputs(phase_outputs) を呼び出す
Then: 警告ログ "[WARNING] Phase 4の成果物が見つかりません" が出力される
And: implementation_details にデフォルト値（空文字列）が設定される
And: 他のフェーズの情報は正常に抽出される
```

### AC-2: Phase 8への統合（FR-2）

#### AC-2.1: Phase 8完了時のPR更新（FR-2.1）
```gherkin
Given: Phase 1-7の成果物が正常に生成されている
And: metadata.json に pr_number=123 が保存されている
When: ReportPhase.execute() を実行する
Then: report.md が正常に生成される
And: GitHubClient.update_pull_request(pr_number=123, body=detailed_body) が呼び出される
And: PR本文が詳細版に更新される
And: Phase 8のステータスが "completed" に更新される
```

```gherkin
Given: metadata.json に pr_number が保存されていない
When: ReportPhase.execute() を実行する
Then: GitHubClient.check_existing_pr(head="ai-workflow/issue-123") が呼び出される
And: PRが見つかった場合、PR番号を取得してPR更新を実行
And: PRが見つからない場合、警告ログを出力してスキップ
And: Phase 8のステータスは "completed" に更新される
```

#### AC-2.2: エラーハンドリング（FR-2.2）
```gherkin
Given: Phase 1-7の成果物が正常に生成されている
And: PR更新処理がGitHub APIエラーで失敗する
When: ReportPhase.execute() を実行する
Then: 警告ログ "[WARNING] PR更新に失敗しました: {error_message}" が出力される
And: Phase 8のステータスは "completed" に更新される（失敗扱いにしない）
And: 手動でPR更新を実施するよう促すメッセージが出力される
```

### AC-3: テンプレート管理（FR-3）

#### AC-3.1: 詳細版テンプレートの作成（FR-3.1）
```gherkin
Given: テンプレートファイル `templates/pr_body_detailed_template.md` が存在する
When: ファイルを読み込む
Then: 以下のプレースホルダーが含まれている:
  - {issue_number}
  - {branch_name}
  - {summary}
  - {implementation_details}
  - {test_results}
  - {documentation_updates}
  - {review_points}
And: テンプレートの構成は以下の通り:
  - 関連Issue
  - 変更サマリー
  - ワークフロー進捗チェックリスト
  - 実装詳細
  - テスト結果
  - ドキュメント更新
  - レビューポイント
  - 成果物ディレクトリの説明
  - 実行環境情報
```

#### AC-3.2: 既存テンプレートとの使い分け（FR-3.2）
```gherkin
Given: Phase 0でPRを作成する
When: GitHubClient.create_pull_request() を呼び出す
Then: _generate_pr_body_template() が呼び出される
And: pr_body_template.md（簡易版）が使用される
```

```gherkin
Given: Phase 8でPR本文を更新する
When: ReportPhase.execute() を実行する
Then: _generate_pr_body_detailed() が呼び出される
And: pr_body_detailed_template.md（詳細版）が使用される
```

### AC-4: テスト機能（FR-4）

#### AC-4.1: ユニットテスト（FR-4.1）
```gherkin
Given: tests/unit/core/test_github_client.py が存在する
When: pytest tests/unit/core/test_github_client.py を実行する
Then: 以下のテストケースが全てPASSする:
  - test_update_pull_request_success
  - test_update_pull_request_not_found
  - test_update_pull_request_api_error
  - test_generate_pr_body_detailed
  - test_extract_phase_outputs
And: テストカバレッジが80%以上である
```

#### AC-4.2: インテグレーションテスト（FR-4.2）
```gherkin
Given: tests/integration/test_pr_update_integration.py が存在する
When: pytest tests/integration/test_pr_update_integration.py を実行する
Then: Phase 8完了 → PR更新の一連のフローが正常に動作する
And: GitHub API連携テスト（モック使用）が全てPASSする
```

---

## 7. スコープ外

本機能では以下の事項はスコープ外とします：

### 将来的な拡張候補
1. **PR本文の差分更新**: 現在は全体を上書きする方式。将来的には差分更新（特定セクションのみ更新）を検討。
2. **PR本文のバージョン管理**: PR本文の更新履歴を保存する機能。
3. **カスタマイズ可能なテンプレート**: ユーザーが独自のテンプレートを定義できる機能。
4. **他のGitホスティングサービス対応**: GitLab、Bitbucket等への対応。
5. **PR本文のフォーマットバリデーション**: 生成されたPR本文のMarkdownフォーマットが正しいかを検証する機能。

### 明確にスコープ外とする事項
1. **Phase 0-7での中間更新**: Phase 8完了時のみPR更新を実施。各フェーズ完了時の中間更新は実施しない。
2. **PR以外の更新**: IssueコメントやIssue本文の更新は実施しない。
3. **GitHub App認証**: 現在のPersonal Access Token方式を維持。GitHub App認証への移行は検討しない。
4. **PR本文の国際化**: 日本語のみサポート。英語等の多言語対応は実施しない。

---

## 8. 補足情報

### 参考資料
- **Planning Document**: `.ai-workflow/issue-363/00_planning/output/planning.md`
- **Issue本文**: https://github.com/tielec/infrastructure-as-code/issues/363
- **既存実装**:
  - `scripts/ai-workflow/core/github_client.py`: GitHub API wrapper（lines 336-512: PR作成機能）
  - `scripts/ai-workflow/phases/report.py`: Phase 8実装（lines 22-137: execute()メソッド）
  - `scripts/ai-workflow/templates/pr_body_template.md`: 簡易版テンプレート

### 外部リソース
- [PyGithub Documentation](https://pygithub.readthedocs.io/)
- [GitHub REST API - Pull Requests](https://docs.github.com/en/rest/pulls/pulls)
- [GitHub API Rate Limiting](https://docs.github.com/en/rest/overview/resources-in-the-rest-api#rate-limiting)

### 期待される効果の定量評価
- **レビュー時間短縮**: 平均20-30分のレビュー時間を10-15分に短縮（約50%削減）
- **Issue/コミット履歴確認の削減**: レビュアーの80%がPR本文のみで変更内容を把握可能
- **PRドキュメント性向上**: 後からの調査時間を60%削減

---

## 9. 品質ゲート確認

本要件定義書は、以下の品質ゲート（Phase 1の必須要件）を満たしています：

- ✅ **機能要件が明確に記載されている**: FR-1からFR-4まで、全ての機能要件を具体的かつ測定可能な形で記述。各機能要件には入力・出力・処理フローを明記。
- ✅ **受け入れ基準が定義されている**: AC-1からAC-4まで、全ての機能要件に対してGiven-When-Then形式で受け入れ基準を定義。
- ✅ **スコープが明確である**: 機能要件（FR-1〜FR-4）とスコープ外（将来的な拡張候補、明確にスコープ外とする事項）を明確に区別。
- ✅ **論理的な矛盾がない**: 機能要件、非機能要件、制約事項、前提条件の間で矛盾がないことを確認。Planning Documentの戦略（EXTEND、UNIT_INTEGRATION、BOTH_TEST）と整合。

---

## 変更履歴

| 日付 | 変更者 | 変更内容 |
|------|--------|----------|
| 2025-10-12 | Claude Code | 初版作成 |
