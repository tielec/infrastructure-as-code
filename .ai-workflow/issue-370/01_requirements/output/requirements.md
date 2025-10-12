# 要件定義書 - Issue #370

**Issue番号**: #370
**タイトル**: [IMPROVEMENT] AIワークフロー: GitHub Issue進捗コメント最適化（ページ重量化対策）
**作成日**: 2025-01-15
**要件定義者**: AI Workflow - Requirements Phase
**Planning Document参照**: `.ai-workflow/issue-370/00_planning/output/planning.md`

---

## 0. Planning Documentの確認

### 策定された戦略の概要

Planning Phaseで以下の戦略が決定されました：

- **実装戦略**: EXTEND（既存コード拡張）
- **テスト戦略**: INTEGRATION_ONLY
- **テストコード戦略**: CREATE_TEST
- **推奨オプション**: オプション1（進捗を1つのコメントに統合、GitHub API Edit Comment使用）
- **見積もり工数**: 8-12時間
- **複雑度**: 中程度

### 採用理由

オプション1を採用する理由：
- コメント数が1つのみ（最もシンプル）
- リアルタイム性が高い（常に最新状態が反映）
- 実装がシンプル（GitHub API Edit Comment機能を使用）
- 履歴は折りたたみ可能
- ユーザビリティが最も優れている

### 成功基準

- **定量的**: コメント数を最大90コメント → **1コメント**に削減（98.9%削減）
- **定量的**: Issueページ読み込み時間を3秒 → **1秒以下**に短縮
- **定性的**: 進捗が一目で把握できる
- **定性的**: 既存ワークフローへの影響を最小限に抑える

---

## 1. 概要

### 背景

AIワークフローは現在、GitHub Issueに進捗状況を逐次コメントとして投稿する仕組みを採用しています。しかし、1つのワークフローで最大90コメント以上が投稿されるため、以下の問題が発生しています：

- Issueページの読み込みが遅い（現在3秒以上）
- スクロールが重く、操作性が悪い
- 重要なコメントが大量の進捗コメントに埋もれる
- モバイル環境では特に閲覧困難

### 目的

GitHub Issueのコメント数を最小化し、ページの軽量化と操作性の向上を実現することで、開発者のユーザビリティを大幅に改善します。

### ビジネス価値

- **開発者体験の向上**: Issue閲覧時のストレス軽減
- **生産性向上**: 重要な情報への素早いアクセス
- **保守性向上**: 進捗履歴の見やすさ改善

### 技術的価値

- **スケーラビリティ**: 長期稼働するワークフローにも対応可能
- **保守性**: 1つのコメントで進捗を管理する明確な設計
- **拡張性**: 将来的なフォーマット変更が容易

---

## 2. 機能要件

### FR-001: 進捗コメントの統合管理（優先度：高）

**説明**:
GitHub Issueに投稿される進捗コメントを1つに統合し、更新時には既存コメントをEdit Comment APIで編集する。

**詳細要件**:
- 初回投稿時に進捗コメントを作成し、コメントIDをメタデータに保存
- 2回目以降はコメントIDを使用して既存コメントを編集
- 既存の`post_progress()`メソッドから呼び出し可能な形で実装

**該当コンポーネント**:
- `scripts/ai-workflow/core/github_client.py`
- `scripts/ai-workflow/phases/base_phase.py`

---

### FR-002: GitHubClient新規メソッド追加（優先度：高）

**説明**:
`GitHubClient`クラスに`create_or_update_progress_comment()`メソッドを追加する。

**メソッドシグネチャ**:
```python
def create_or_update_progress_comment(
    self,
    issue_number: int,
    content: str
) -> Dict[str, Any]:
    """
    進捗コメントを作成または更新

    Args:
        issue_number: Issue番号
        content: コメント本文（Markdown形式）

    Returns:
        Dict[str, Any]:
            - comment_id (int): コメントID
            - comment_url (str): コメントURL

    Raises:
        GithubException: GitHub API呼び出しエラー
    """
```

**処理フロー**:
1. MetadataManagerから既存コメントIDを取得
2. コメントIDが存在する場合:
   - `repository.get_issue_comment(comment_id)`でコメント取得
   - `comment.edit(content)`でコメント編集
3. コメントIDが存在しない場合:
   - `issue.create_comment(content)`で新規コメント作成
   - コメントIDをMetadataManagerに保存
4. コメントIDとURLを返却

**エラーハンドリング**:
- GitHub API呼び出し失敗時: 既存の`post_workflow_progress()`にフォールバック（新規コメント作成）
- コメントIDが無効な場合: 新規コメントを作成し、メタデータを更新

---

### FR-003: MetadataManager拡張（優先度：高）

**説明**:
`MetadataManager`クラスに進捗コメントIDの保存・取得メソッドを追加する。

**新規メソッド**:

```python
def save_progress_comment_id(self, comment_id: int) -> None:
    """進捗コメントIDをメタデータに保存"""

def get_progress_comment_id(self) -> Optional[int]:
    """進捗コメントIDをメタデータから取得"""
```

**メタデータスキーマ拡張**:
```json
{
  "github_integration": {
    "progress_comment_id": 123456789,
    "progress_comment_url": "https://github.com/.../issues/370#issuecomment-123456789"
  }
}
```

**後方互換性**:
- `github_integration`セクションが存在しない場合は`None`を返す
- 既存の`metadata.json`には影響を与えない

---

### FR-004: BasePhaseの進捗投稿ロジック変更（優先度：高）

**説明**:
`BasePhase.post_progress()`メソッドを修正し、`create_or_update_progress_comment()`を使用する。

**変更前**:
```python
def post_progress(self, status: str, details: Optional[str] = None):
    # 毎回新規コメント作成
    self.github.post_comment(issue_number, body)
```

**変更後**:
```python
def post_progress(self, status: str, details: Optional[str] = None):
    # 統合コメント形式に変換
    content = self._format_progress_content(status, details)

    # コメント作成または更新
    result = self.github.create_or_update_progress_comment(
        issue_number, content
    )

    print(f"[INFO] 進捗コメント更新: {result['comment_url']}")
```

**影響範囲**:
- `BasePhase.post_progress()`の内部実装のみ変更
- 既存の呼び出し元（各フェーズ）は変更不要

---

### FR-005: 進捗コメントのMarkdownフォーマット設計（優先度：高）

**説明**:
進捗コメントを視覚的に分かりやすく、情報を階層的に表示するMarkdownフォーマットを設計する。

**フォーマット要件**:

1. **全体進捗セクション**:
   - 全フェーズ（Phase 0-8）のステータス一覧を表示
   - 各フェーズの状態をアイコンで表現（✅ 完了、🔄 実行中、⏸️ 待機中、❌ 失敗）
   - 完了時刻を併記

2. **現在フェーズの詳細セクション**:
   - フェーズ名、ステータス、開始時刻、試行回数
   - 実行ログ（タイムスタンプ付き）

3. **完了フェーズの折りたたみセクション**:
   - `<details>`タグで折りたたみ可能
   - 各フェーズのステータス、レビュー結果、実行時間、コストを記載

4. **メタ情報**:
   - 最終更新日時
   - ワークフローの署名（AI駆動開発自動化ワークフロー）

**サンプル**:
```markdown
## 🤖 AI Workflow - 進捗状況

### 全体進捗

- ✅ Phase 0: Planning - **COMPLETED** (2025-01-15 10:30)
- ✅ Phase 1: Requirements - **COMPLETED** (2025-01-15 11:00)
- 🔄 Phase 2: Design - **IN PROGRESS** (開始: 2025-01-15 11:30)
- ⏸️ Phase 3-8: **PENDING**

### 現在のフェーズ: Phase 2 (Design)

**ステータス**: IN PROGRESS
**開始時刻**: 2025-01-15 11:30:45
**試行回数**: 1/3

#### 実行ログ

- `11:30:45` - Phase 2開始
- `11:32:10` - Execute実行中
- `11:35:20` - Execute完了

<details>
<summary>完了したフェーズの詳細</summary>

### Phase 0: Planning

**ステータス**: COMPLETED
**レビュー結果**: PASS
**実行時間**: 5分30秒
**コスト**: $0.15

### Phase 1: Requirements

**ステータス**: COMPLETED
**レビュー結果**: PASS_WITH_SUGGESTIONS
**実行時間**: 8分20秒
**コスト**: $0.23

</details>

---
*最終更新: 2025-01-15 11:35:30*
*AI駆動開発自動化ワークフロー (Claude Agent SDK)*
```

---

### FR-006: エラーハンドリングとフォールバック（優先度：中）

**説明**:
GitHub API呼び出しエラー時に適切にフォールバックし、ワークフローの継続性を保証する。

**要件**:
- Edit Comment API失敗時: 既存の`post_workflow_progress()`で新規コメント作成
- コメントID取得失敗時: 新規コメント作成としてリトライ
- 全てのGitHub APIエラーをログ出力
- ワークフローはGitHub投稿エラーで中断しない

**ログ出力例**:
```
[WARNING] GitHub Edit Comment APIエラー: Not Found (コメントID: 123456789)
[INFO] フォールバック: 新規コメント作成
[INFO] GitHub Issue #370 に進捗を投稿しました
```

---

### FR-007: レビュー結果投稿の扱い（優先度：低）

**説明**:
`post_review()`メソッドで投稿されるレビュー結果も統合コメントに含めるか、個別コメントとして残すかを決定する。

**推奨**:
- レビュー結果は**個別コメントとして残す**
- 理由: レビュー結果は重要な意思決定記録であり、通知も必要
- 進捗コメントには「レビュー実行中」のステータスのみ記載

---

## 3. 非機能要件

### NFR-001: パフォーマンス要件（優先度：高）

- **Issueページ読み込み時間**: 3秒 → **1秒以下**（目標値）
- **コメント数**: 最大90コメント → **1コメント**（98.9%削減）
- **API呼び出し頻度**: 各フェーズで最大10回 → **1-2回**（コメント作成/更新のみ）
- **GitHub API Rate Limit**: 5000 requests/hourの範囲内（進捗更新は1ワークフローで最大10回）

### NFR-002: セキュリティ要件（優先度：中）

- **認証**: 既存のGitHub Token認証を使用（変更なし）
- **権限**: Issue Write権限が必要（既存要件と同じ）
- **機密情報**: コメント内容にシークレット情報を含めない（既存ルールを継承）

### NFR-003: 可用性・信頼性要件（優先度：中）

- **GitHub API障害時**: フォールバックで新規コメント作成
- **コメントID不整合時**: 新規コメント作成でリカバリー
- **ワークフロー継続性**: GitHub投稿エラーでワークフローを中断しない

### NFR-004: 保守性・拡張性要件（優先度：中）

- **既存コードへの影響**: 最小限（`BasePhase.post_progress()`の内部実装変更のみ）
- **後方互換性**: 既存のメタデータ形式を保持
- **テスト容易性**: 統合テストで動作確認可能
- **ログ出力**: 全API呼び出しとエラーをログ出力
- **フォーマット変更**: Markdownフォーマットは容易に変更可能

---

## 4. 制約事項

### 技術的制約

- **使用API**: PyGithub（既存ライブラリ）のEdit Comment機能を使用
- **GitHub API制限**: Edit Comment APIのレート制限（5000 requests/hour）に準拠
- **Markdownサポート**: GitHub Flavored Markdown（GFM）の範囲内
- **コメント長制限**: GitHub APIのコメント長制限（65,536文字）に注意

### リソース制約

- **開発時間**: 8-12時間以内に完了（Planning Documentの見積もり）
- **開発者**: AI Agent（Claude Code）のみ
- **テスト環境**: 実際のGitHub Issueを使用

### ポリシー制約

- **既存ワークフローへの影響**: 最小限に抑える
- **後方互換性**: 既存のメタデータスキーマを保持
- **コーディング規約**: プロジェクトのCLAUDE.mdに従う

---

## 5. 前提条件

### システム環境

- Python 3.8以上
- PyGithub ライブラリがインストール済み
- GitHub Token（Issue Write権限）が設定済み

### 依存コンポーネント

- `scripts/ai-workflow/core/github_client.py` - GitHubクライアント
- `scripts/ai-workflow/core/metadata_manager.py` - メタデータ管理
- `scripts/ai-workflow/phases/base_phase.py` - フェーズ基底クラス

### 外部システム連携

- GitHub API（Edit Comment、Create Comment）
- GitHub Issue（進捗コメント投稿先）

---

## 6. 受け入れ基準

### AC-001: 進捗コメントが1つのみ作成される

**Given**: AIワークフローが実行される
**When**: 全フェーズ（Phase 0-8）が完了する
**Then**: GitHub Issueに進捗コメントが**1つのみ**存在する

### AC-002: 既存コメントが正しく更新される

**Given**: 進捗コメントが既に作成されている
**When**: 新しいフェーズが開始または完了する
**Then**: 既存コメントの内容が最新の進捗状態に更新される

### AC-003: コメントIDがメタデータに保存される

**Given**: 初回の進捗コメントが作成される
**When**: コメント作成が成功する
**Then**: `metadata.json`の`github_integration.progress_comment_id`にコメントIDが保存される

### AC-004: フォーマットが仕様通りである

**Given**: 進捗コメントが作成または更新される
**When**: コメント内容を確認する
**Then**:
- 全体進捗セクションが存在する
- 現在フェーズの詳細セクションが存在する
- 完了フェーズが`<details>`タグで折りたたまれている
- 最終更新日時が記載されている

### AC-005: GitHub APIエラー時にフォールバックする

**Given**: Edit Comment APIが失敗する（コメントIDが無効など）
**When**: `create_or_update_progress_comment()`が呼ばれる
**Then**: 新規コメント作成にフォールバックし、ワークフローは継続する

### AC-006: Issueページの読み込み時間が改善される

**Given**: ワークフローが完了している
**When**: GitHub Issueページを開く
**Then**: ページ読み込み時間が**1秒以下**である（目標値）

### AC-007: 既存ワークフローに影響を与えない

**Given**: 既存の`BasePhase`を継承した全フェーズ
**When**: ワークフローを実行する
**Then**:
- 既存のフェーズは変更不要
- `post_progress()`の呼び出し元は変更不要
- ワークフローの動作は変わらない

### AC-008: 後方互換性が保たれる

**Given**: `github_integration`セクションが存在しない既存のメタデータ
**When**: `get_progress_comment_id()`が呼ばれる
**Then**: `None`が返却され、新規コメント作成として動作する

---

## 7. スコープ外

### 明確にスコープ外とする事項

- **レビュー結果コメントの統合**: `post_review()`で投稿されるレビュー結果は個別コメントとして残す
- **GitHub Gist対応**: オプション2（Gist使用）は今回実装しない
- **Pull Request Description統合**: オプション3（PR Description使用）は今回実装しない
- **過去Issueへの適用**: 既に作成された過去のIssueには適用しない（新規ワークフローのみ）
- **通知設定のカスタマイズ**: GitHub通知設定の変更は対象外

### 将来的な拡張候補

- **GitHub Gist対応**: 超長時間ワークフロー（24時間以上）ではGist使用も検討
- **フォーマットのカスタマイズ**: ユーザーが進捗フォーマットを設定ファイルでカスタマイズ可能にする
- **通知最適化**: Edit Comment時の通知を抑制するオプション（GitHub API側の対応待ち）
- **進捗ダッシュボード**: Webベースの進捗ダッシュボード（将来的な大規模拡張）

---

## 8. 参考情報

### 関連ファイル

- `scripts/ai-workflow/phases/base_phase.py` (行216-239: `post_progress()`)
- `scripts/ai-workflow/core/github_client.py` (行159-211: `post_workflow_progress()`)
- `scripts/ai-workflow/core/metadata_manager.py`
- `.ai-workflow/issue-{number}/metadata.json`

### 外部リソース

- [PyGithub Documentation - Edit Comment](https://pygithub.readthedocs.io/en/latest/github_objects/IssueComment.html#github.IssueComment.IssueComment.edit)
- [GitHub API - Update Comment](https://docs.github.com/en/rest/issues/comments#update-an-issue-comment)
- [GitHub Markdown - Details/Summary](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/organizing-information-with-collapsed-sections)

---

## 9. 品質ゲート確認

本要件定義書は、Phase 1の品質ゲートを満たすように作成されています：

- [x] **機能要件が明確に記載されている**: FR-001〜FR-007で7つの機能要件を具体的に定義
- [x] **受け入れ基準が定義されている**: AC-001〜AC-008で8つの検証可能な受け入れ基準を記載
- [x] **スコープが明確である**: スコープ外の項目を明記し、将来拡張候補も記載
- [x] **論理的な矛盾がない**: Planning Documentの戦略と整合性があり、機能要件と受け入れ基準が対応

---

*この要件定義書は AI Workflow - Requirements Phase によって作成されました。*
*作成日時: 2025-01-15*
