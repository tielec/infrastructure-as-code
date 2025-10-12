# 実装ログ - Issue #370

**Issue番号**: #370
**タイトル**: [IMPROVEMENT] AIワークフロー: GitHub Issue進捗コメント最適化（ページ重量化対策）
**実装日**: 2025-01-15
**実装者**: AI Workflow - Implementation Phase

---

## 実装サマリー

- **実装戦略**: EXTEND（既存コード拡張）
- **変更ファイル数**: 3個
- **新規作成ファイル数**: 0個（テストコードはPhase 5で実装）

## 変更ファイル一覧

### 修正

1. **scripts/ai-workflow/core/github_client.py**: 新規メソッド `create_or_update_progress_comment()` を追加
2. **scripts/ai-workflow/core/metadata_manager.py**: 新規メソッド `save_progress_comment_id()` と `get_progress_comment_id()` を追加
3. **scripts/ai-workflow/phases/base_phase.py**: `post_progress()` メソッドを修正、新規メソッド `_format_progress_content()` を追加

## 実装詳細

### ファイル1: scripts/ai-workflow/core/github_client.py

**変更内容**: 新規メソッド `create_or_update_progress_comment()` を実装

**実装内容**:
- メタデータから既存コメントIDを取得
- コメントIDが存在する場合:
  - `repository.get_issue_comment(comment_id)` でコメント取得
  - `comment.edit(content)` でコメント編集
- コメントIDが存在しない場合:
  - `issue.create_comment(content)` で新規コメント作成
  - `metadata_manager.save_progress_comment_id()` でコメントIDを保存
- エラーハンドリング:
  - Edit Comment API失敗時: ログ出力してから新規コメント作成にフォールバック
  - GithubException発生時: エラーメッセージを出力して RuntimeError を raise

**理由**:
- 設計書（design.md）のセクション7.1.1「GitHubClient（既存クラスの拡張）」に従って実装
- PyGithub の `repository.get_issue_comment()` と `comment.edit()` を使用
- フォールバック処理により、コメントIDが無効な場合でも新規コメント作成として動作可能

**注意点**:
- `metadata_manager` パラメータは型ヒントなし（循環参照を避けるため）
- GithubException のキャッチにより、GitHub API障害時のエラーハンドリングが実装されている

---

### ファイル2: scripts/ai-workflow/core/metadata_manager.py

**変更内容**: 新規メソッド `save_progress_comment_id()` と `get_progress_comment_id()` を実装

**実装内容**:

#### `save_progress_comment_id(comment_id: int, comment_url: str) -> None`
- `self._state.data` に `github_integration` セクションを追加（存在しない場合）
- `progress_comment_id` と `progress_comment_url` を保存
- `self._state.save()` でメタデータファイルに永続化

#### `get_progress_comment_id() -> Optional[int]`
- `self._state.data['github_integration']` の存在確認
- 存在する場合: `progress_comment_id` を返却
- 存在しない場合: `None` を返却

**理由**:
- 設計書（design.md）のセクション7.1.2「MetadataManager（既存クラスの拡張）」に従って実装
- 後方互換性を保つため、`github_integration` セクションが存在しない場合は `None` を返却
- メタデータスキーマ拡張:
  ```json
  {
    "github_integration": {
      "progress_comment_id": 123456789,
      "progress_comment_url": "https://github.com/.../issues/370#issuecomment-123456789"
    }
  }
  ```

**注意点**:
- 既存のメタデータフィールドには影響を与えない設計
- `get_progress_comment_id()` は KeyError を発生させず、存在しない場合は `None` を返す安全な実装

---

### ファイル3: scripts/ai-workflow/phases/base_phase.py

**変更内容**:
1. `post_progress()` メソッドを修正（内部実装変更）
2. 新規メソッド `_format_progress_content()` を実装

**実装内容**:

#### `post_progress(status: str, details: Optional[str] = None)`
- 既存の `github.post_workflow_progress()` 呼び出しを削除
- `_format_progress_content()` を呼び出して統合コメント形式のMarkdownを生成
- `github.create_or_update_progress_comment()` を呼び出してコメント作成/更新
- 既存のシグネチャを維持（既存の呼び出し元には影響なし）

#### `_format_progress_content(status: str, details: Optional[str] = None) -> str`
- **ヘッダーセクション**: "## 🤖 AI Workflow - 進捗状況"
- **全体進捗セクション**: Phase 0-9 のステータス一覧（アイコン付き）
  - ⏸️ pending
  - 🔄 in_progress
  - ✅ completed
  - ❌ failed
- **現在フェーズの詳細セクション**:
  - フェーズ番号、ステータス、開始時刻、試行回数
  - 詳細情報（details パラメータ）
- **完了フェーズの折りたたみセクション**: `<details>` タグでMarkdown折りたたみ
  - 各完了フェーズのステータス、レビュー結果、完了時刻
- **フッターセクション**: 最終更新日時、署名

**理由**:
- 設計書（design.md）のセクション7.1.3「BasePhase（既存クラスの修正）」とセクション7.3.2「Markdownフォーマットサンプル」に従って実装
- 要件定義書（requirements.md）のFR-004「BasePhaseの進捗投稿ロジック変更」とFR-005「進捗コメントのMarkdownフォーマット設計」に準拠
- メタデータから全フェーズのステータスを取得し、動的にMarkdownを生成
- GitHub Flavored Markdown（GFM）の `<details>` タグで折りたたみセクションを実装

**注意点**:
- `post_progress()` の呼び出し元（各フェーズ）は変更不要（シグネチャが変わっていない）
- `_format_progress_content()` は private メソッドとして実装（外部から呼び出し不可）
- エラーハンドリング: GitHub投稿失敗時は警告ログのみ出力し、ワークフローは継続

---

## 次のステップ

- **Phase 5（test_implementation）**: テストコードを実装
  - 統合テストファイル `tests/integration/test_github_progress_comment.py` を作成
  - テストシナリオ（test-scenario.md）に基づいてテストコードを実装
- **Phase 6（testing）**: テストを実行
  - 統合テストの実行
  - 実際のGitHub Issueでの動作確認

---

## 品質ゲート確認

実装は以下の品質ゲートを満たしています：

- [x] **Phase 2の設計に沿った実装である**
  - 設計書（design.md）のセクション7「詳細設計」に従って実装
  - データ構造設計、インターフェース設計、Markdownフォーマット設計に準拠
- [x] **既存コードの規約に準拠している**
  - 既存コードのインデント（4スペース）、命名規則（snake_case）を継承
  - docstring形式、型ヒント、コメント記述規約に準拠
- [x] **基本的なエラーハンドリングがある**
  - GithubException のキャッチと適切なエラーメッセージ出力
  - フォールバック処理（Edit Comment API失敗時に新規コメント作成）
  - KeyError を発生させない安全な実装（`get_progress_comment_id()`）
- [x] **明らかなバグがない**
  - 既存コードのパターンを踏襲
  - 後方互換性を保つ実装（`github_integration` セクションが存在しない場合の処理）
  - ワークフロー継続性を保証（GitHub投稿エラーでワークフローを中断しない）

---

## 実装時の判断事項

1. **型ヒントの省略**:
   - `create_or_update_progress_comment()` の `metadata_manager` パラメータは型ヒントなし
   - 理由: `MetadataManager` をインポートすると循環参照が発生する可能性があるため

2. **フォールバック処理の実装**:
   - Edit Comment API失敗時に新規コメント作成にフォールバック
   - 理由: コメントIDが無効な場合（コメントが削除された場合）でもワークフローを継続可能にするため

3. **後方互換性の保証**:
   - `get_progress_comment_id()` は `github_integration` セクションが存在しない場合に `None` を返却
   - 理由: 既存のメタデータ（`github_integration` セクションを持たない）でも動作するため

4. **エラーハンドリング方針**:
   - GitHub投稿失敗時は警告ログのみ出力し、ワークフローは継続
   - 理由: 進捗報告の失敗でワークフロー全体を停止させないため（設計書のNFR-003「可用性・信頼性要件」に準拠）

---

*この実装ログは AI Workflow - Implementation Phase によって作成されました。*
*実装日時: 2025-01-15*
