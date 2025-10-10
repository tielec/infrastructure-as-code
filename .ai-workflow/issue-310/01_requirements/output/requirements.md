# 要件定義書

**Issue**: #310
**タイトル**: [ai-workflow] feat: 全フェーズの成果物をGitHub Issueコメントに投稿する機能を追加
**作成日**: 2025-10-10

---

## 1. 概要

### 1.1 背景

現在のAI駆動開発自動化ワークフローでは、Phase 6（documentation）のみが`post_output()`メソッドを使用して成果物をGitHub Issueコメントに投稿している。他のフェーズ（requirements, design, test_scenario, implementation, testing, report）では、成果物がファイルシステムにのみ保存され、GitHubコメントには投稿されていない。

このため、GitHub Issue上でワークフロー全体の進捗と成果物を一元的に確認することが難しく、レビュープロセスの効率が低下している。

### 1.2 目的

全フェーズで成果物をGitHub Issueコメントに投稿することで、以下を実現する：

- **可視性の向上**: GitHub Issue上でワークフロー全体の進捗と成果物を即座に確認可能
- **レビュー効率化**: 成果物のレビューがGitHub上で容易に実施可能
- **一貫性の向上**: 全フェーズで統一された成果物投稿フロー
- **トレーサビリティ**: 各フェーズの成果物履歴をGitHub Issue上で追跡可能

### 1.3 ビジネス価値

- **開発効率の向上**: レビュアーがファイルシステムを探す必要がなくなり、GitHub UIで完結
- **コラボレーション強化**: チーム全体が同じプラットフォームで成果物を確認・議論可能
- **品質向上**: 成果物が可視化されることで、早期フィードバックが促進される

---

## 2. 機能要件

### FR-01: Phase 1（requirements）の成果物投稿機能

**優先度**: 高

**要件**:
- `scripts/ai-workflow/phases/requirements.py`の`execute()`メソッドに成果物投稿処理を追加する
- 成果物ファイル: `requirements.md`
- 投稿タイトル: "要件定義書"
- `post_output()`メソッドを使用してGitHub Issueコメントに投稿する
- 投稿失敗時でもワークフローは継続する（WARNING表示）

**受け入れ基準**:
- Given: Phase 1が正常に完了した
- When: `requirements.md`が生成された後
- Then: GitHub Issueに"要件定義書"というタイトルで成果物がコメント投稿される

### FR-02: Phase 2（design）の成果物投稿機能

**優先度**: 高

**要件**:
- `scripts/ai-workflow/phases/design.py`の`execute()`メソッドに成果物投稿処理を追加する
- 成果物ファイル: `design.md`
- 投稿タイトル: "詳細設計書"
- `post_output()`メソッドを使用してGitHub Issueコメントに投稿する
- 投稿失敗時でもワークフローは継続する（WARNING表示）

**受け入れ基準**:
- Given: Phase 2が正常に完了した
- When: `design.md`が生成された後
- Then: GitHub Issueに"詳細設計書"というタイトルで成果物がコメント投稿される

### FR-03: Phase 3（test_scenario）の成果物投稿機能

**優先度**: 高

**要件**:
- `scripts/ai-workflow/phases/test_scenario.py`の`execute()`メソッドに成果物投稿処理を追加する
- 成果物ファイル: `test-scenario.md`
- 投稿タイトル: "テストシナリオ"
- `post_output()`メソッドを使用してGitHub Issueコメントに投稿する
- 投稿失敗時でもワークフローは継続する（WARNING表示）

**受け入れ基準**:
- Given: Phase 3が正常に完了した
- When: `test-scenario.md`が生成された後
- Then: GitHub Issueに"テストシナリオ"というタイトルで成果物がコメント投稿される

### FR-04: Phase 4（implementation）の成果物投稿機能

**優先度**: 高

**要件**:
- `scripts/ai-workflow/phases/implementation.py`の`execute()`メソッドに成果物投稿処理を追加する
- 成果物ファイル: `implementation.md`
- 投稿タイトル: "実装ログ"
- `post_output()`メソッドを使用してGitHub Issueコメントに投稿する
- 投稿失敗時でもワークフローは継続する（WARNING表示）

**受け入れ基準**:
- Given: Phase 4が正常に完了した
- When: `implementation.md`が生成された後
- Then: GitHub Issueに"実装ログ"というタイトルで成果物がコメント投稿される

### FR-05: Phase 5（testing）の成果物投稿機能

**優先度**: 高

**要件**:
- `scripts/ai-workflow/phases/testing.py`の`execute()`メソッドに成果物投稿処理を追加する
- 成果物ファイル: `test-result.md`
- 投稿タイトル: "テスト結果"
- `post_output()`メソッドを使用してGitHub Issueコメントに投稿する
- 投稿失敗時でもワークフローは継続する（WARNING表示）

**受け入れ基準**:
- Given: Phase 5が正常に完了した
- When: `test-result.md`が生成された後
- Then: GitHub Issueに"テスト結果"というタイトルで成果物がコメント投稿される

### FR-06: Phase 7（report）の成果物投稿機能

**優先度**: 高

**要件**:
- `scripts/ai-workflow/phases/report.py`の`execute()`メソッドに成果物投稿処理を追加する
- 成果物ファイル: `report.md`（注: Issue本文では`final-report.md`だが、実装コードでは`report.md`）
- 投稿タイトル: "最終レポート"
- `post_output()`メソッドを使用してGitHub Issueコメントに投稿する
- 投稿失敗時でもワークフローは継続する（WARNING表示）

**受け入れ基準**:
- Given: Phase 7が正常に完了した
- When: `report.md`が生成された後
- Then: GitHub Issueに"最終レポート"というタイトルで成果物がコメント投稿される

**注記**: Phase 7（report.py）は既に98-106行目で`post_output()`を実装済みだが、タイトルは"最終レポート"を使用している。

### FR-07: エラーハンドリング

**優先度**: 高

**要件**:
- GitHub API投稿失敗時は`try-except`ブロックでキャッチする
- 失敗時は`[WARNING]`レベルのログを出力する
- 失敗してもPhaseの`execute()`メソッドは成功を返す（ワークフロー継続）

**受け入れ基準**:
- Given: GitHub API投稿処理で例外が発生した
- When: `post_output()`メソッドが呼ばれた
- Then: WARNINGログが出力され、`execute()`メソッドは正常終了する

### FR-08: UTF-8エンコーディング対応

**優先度**: 高

**要件**:
- 成果物ファイルは`UTF-8`エンコーディングで読み込む
- `file.read_text(encoding='utf-8')`を使用する

**受け入れ基準**:
- Given: 成果物ファイルにマルチバイト文字（日本語等）が含まれる
- When: `post_output()`メソッドが呼ばれた
- Then: 文字化けせずにGitHub Issueコメントに投稿される

---

## 3. 非機能要件

### NFR-01: パフォーマンス要件

- GitHub API呼び出しは各フェーズの`execute()`完了後に1回のみ実行する
- API呼び出しによるフェーズ実行時間の増加は2秒以内とする
- 大きなファイル（10MB以上）の場合は投稿をスキップし、WARNING表示する（将来対応）

### NFR-02: 信頼性要件

- GitHub API投稿失敗時でも、フェーズ実行は正常に完了する
- リトライ処理は`BasePhase.post_output()`内で実施される（現状は実装なし）
- ネットワーク障害時でもワークフロー全体は継続する

### NFR-03: 保守性要件

- 各フェーズクラスに同じパターンで実装する（DRY原則の範囲内）
- `post_output()`メソッドは`BasePhase`で提供される共通機能を使用する
- 投稿タイトルは各フェーズで定義し、将来の変更に柔軟に対応できる

### NFR-04: セキュリティ要件

- GitHub APIトークンは環境変数またはクレデンシャルストアから取得する（`GitHubClient`が担保）
- 成果物に機密情報が含まれる場合は投稿しない（レビュー時に確認）

---

## 4. 制約事項

### 4.1 技術的制約

- **既存アーキテクチャへの準拠**: `BasePhase.post_output()`メソッドを使用する（独自実装は不可）
- **GitHub API制限**: GitHub APIのレート制限（5000リクエスト/時）を考慮する
- **ファイルサイズ制限**: GitHub Issueコメントは最大65,536文字までのため、大きな成果物は投稿できない
- **Python 3.8+**: 既存のPythonバージョンに準拠する

### 4.2 リソース制約

- **開発工数**: 既存のPhase 6実装パターンを踏襲するため、最小限の工数で実装可能
- **テスト工数**: 各フェーズで手動テストが必要（自動テストは今回スコープ外）

### 4.3 ポリシー制約

- **コーディング規約**: CLAUDE.mdに記載された規約に準拠（日本語コメント、エラーハンドリング等）
- **Git運用**: featureブランチで開発し、PRレビューを経てマージする

---

## 5. 前提条件

### 5.1 システム環境

- Python 3.8以上がインストールされている
- GitHub APIアクセス用のトークンが設定されている（`GitHubClient`経由）
- `scripts/ai-workflow/`ディレクトリ構造が既存のまま維持されている

### 5.2 依存コンポーネント

- **BasePhase**: `post_output()`メソッドが正しく実装されている
- **GitHubClient**: `post_comment()`メソッドが正常に動作している
- **MetadataManager**: Issue番号の取得が可能である

### 5.3 外部システム連携

- GitHub APIが正常にアクセス可能である
- ネットワーク接続が確立されている

---

## 6. 受け入れ基準

### 6.1 機能受け入れ基準

| Phase | 成果物ファイル | 投稿タイトル | 検証方法 |
|-------|---------------|-------------|---------|
| Phase 1 | requirements.md | 要件定義書 | GitHub Issueコメントに投稿されることを確認 |
| Phase 2 | design.md | 詳細設計書 | GitHub Issueコメントに投稿されることを確認 |
| Phase 3 | test-scenario.md | テストシナリオ | GitHub Issueコメントに投稿されることを確認 |
| Phase 4 | implementation.md | 実装ログ | GitHub Issueコメントに投稿されることを確認 |
| Phase 5 | test-result.md | テスト結果 | GitHub Issueコメントに投稿されることを確認 |
| Phase 7 | report.md | 最終レポート | GitHub Issueコメントに投稿されることを確認（既存実装の確認） |

### 6.2 非機能受け入れ基準

- **エラーハンドリング**: GitHub API投稿失敗時にWARNINGログが出力され、ワークフローが継続することを確認
- **UTF-8エンコーディング**: 日本語を含む成果物が文字化けせずに投稿されることを確認
- **パフォーマンス**: 各フェーズの実行時間が投稿処理により2秒以上増加しないことを確認

### 6.3 品質ゲート（Phase 1）

- [ ] **機能要件が明確に記載されている**: 全6フェーズの投稿機能が具体的に定義されている
- [ ] **受け入れ基準が定義されている**: Given-When-Then形式で各フェーズの受け入れ基準が記述されている
- [ ] **スコープが明確である**: 実装対象フェーズ（1, 2, 3, 4, 5, 7）が明示されている
- [ ] **論理的な矛盾がない**: エラーハンドリング要件と実装パターンが一貫している

---

## 7. スコープ外

以下の項目は今回の実装範囲外とする：

### 7.1 将来的な拡張候補

- **Phase 6の再実装**: Phase 6（documentation）は既に実装済みのため、今回は対象外
- **リトライ機能**: GitHub API投稿失敗時の自動リトライ機能（将来`GitHubClient`側で実装予定）
- **大容量ファイル対応**: 65,536文字を超える成果物の分割投稿機能
- **投稿内容のプレビュー機能**: 投稿前に内容を確認する機能
- **自動テストの追加**: 各フェーズの投稿機能をカバーするユニットテスト・統合テスト

### 7.2 明確にスコープ外とする事項

- **既存のPhase 6実装の変更**: 既に動作しているため、今回は触らない
- **`BasePhase.post_output()`の修正**: 既存メソッドの仕様変更は行わない
- **GitHub API以外の通知先**: Slack、Email等への通知は対象外
- **成果物のフォーマット変更**: Markdown形式以外の出力形式（HTML、PDF等）は対象外

---

## 8. リスクと対策

### 8.1 技術的リスク

| リスク | 影響度 | 対策 |
|--------|--------|------|
| GitHub APIレート制限超過 | 中 | `GitHubClient`でレート制限を監視し、必要に応じて待機処理を追加（将来対応） |
| 大容量ファイルの投稿失敗 | 低 | 65,536文字を超える場合はWARNINGを表示してスキップ（将来対応） |
| ネットワーク障害 | 低 | try-exceptでキャッチし、ワークフローを継続 |

### 8.2 運用リスク

| リスク | 影響度 | 対策 |
|--------|--------|------|
| GitHub Issueが大量のコメントで埋まる | 低 | 1フェーズ1コメントのため、最大7コメント追加（許容範囲） |
| 機密情報の誤投稿 | 高 | レビュープロセスで成果物の内容を確認し、機密情報が含まれないことを検証 |

---

## 9. 参照ドキュメント

- **既存実装**: `scripts/ai-workflow/phases/documentation.py` (Phase 6)
- **基底クラス**: `scripts/ai-workflow/phases/base_phase.py`
- **GitHubクライアント**: `scripts/ai-workflow/core/github_client.py`
- **プロジェクトガイドライン**: `CLAUDE.md`
- **Issue**: https://github.com/tielec/infrastructure-as-code/issues/310

---

## 10. 用語集

| 用語 | 定義 |
|------|------|
| Phase | AI駆動開発自動化ワークフローの各段階（requirements, design, test_scenario, implementation, testing, documentation, report） |
| 成果物 | 各Phaseが生成するMarkdown形式のドキュメント（*.md） |
| `post_output()` | `BasePhase`で提供される、成果物をGitHub Issueコメントに投稿するメソッド |
| GitHub Issue | タスク管理プラットフォームとしてのGitHub Issues |
| WARNING | ログレベルの一種。エラーではないが注意が必要な事象 |

---

**以上**
