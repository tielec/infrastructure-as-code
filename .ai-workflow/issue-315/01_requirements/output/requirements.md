# 要件定義書: AI WorkflowでIssue番号に連動したブランチを自動作成

## ドキュメントメタデータ

- **Issue番号**: #315
- **Issue URL**: https://github.com/tielec/infrastructure-as-code/issues/315
- **作成日**: 2025-10-10
- **バージョン**: 1.0.0
- **ステータス**: Draft

---

## 1. 概要

### 1.1 背景

現在のAI Workflowシステムは、GitHub Issueに基づいた開発タスクを自動化していますが、各Issueの作業は同一ブランチ（feature/ai-workflow-mvpなど）で実施されています。これにより、以下の課題が発生しています：

- **並行作業の困難性**: 複数のIssueを同時に処理する際、ブランチが競合する
- **変更追跡の複雑性**: 異なるIssueの変更が混在し、コードレビューやロールバックが困難
- **Pull Request作成の手動運用**: ブランチが手動管理のため、PR作成も手動で実施が必要

### 1.2 目的

本機能により、以下を実現します：

1. **Issue単位のブランチ管理**: 各Issueに対して独立したブランチを自動作成
2. **変更追跡の容易化**: Issue番号とブランチの1:1対応により、コードレビューとロールバックを簡素化
3. **自動化の基盤構築**: Pull Request自動作成機能の前提条件を整備

### 1.3 ビジネス価値

- **開発効率の向上**: 並行作業が可能になり、複数のIssueを同時進行できる
- **品質向上**: 各Issueの変更が分離され、コードレビューの精度が向上
- **運用コスト削減**: ブランチ管理の自動化により、手動オペレーションが不要

### 1.4 技術的価値

- **Gitワークフローの標準化**: Issue番号ベースのブランチ命名規則により、チーム全体で一貫した運用が可能
- **拡張性の確保**: Pull Request自動作成、マージ戦略の自動化など、将来的な拡張の基盤を確立
- **トレーサビリティの向上**: Issue → Branch → Commit → PRの一貫した追跡が可能

---

## 2. 機能要件

### 2.1 ブランチ命名規則の定義

**優先度**: 高

**要件ID**: FR-001

**説明**: Issue番号に基づいた一意のブランチ名を自動生成する

**仕様**:
- ブランチ名フォーマット: `ai-workflow/issue-{issue_number}`
- 例: `ai-workflow/issue-315`
- Issue番号は必ず数値（整数）であること
- ブランチ名は英数字とハイフン、スラッシュのみを含む

**受け入れ基準**:
- Given: Issue番号が"315"である
- When: ブランチ名を生成する
- Then: `ai-workflow/issue-315`が生成される

---

### 2.2 init コマンド実行時のブランチ自動作成

**優先度**: 高

**要件ID**: FR-002

**説明**: `main.py init --issue-url <URL>` 実行時に、Issue番号に対応するブランチを自動作成し、チェックアウトする

**仕様**:
- Issue URLからIssue番号を抽出
- ブランチ名を生成（`ai-workflow/issue-{issue_number}`）
- ブランチが既に存在する場合は、以下の動作を選択可能にする:
  - デフォルト: エラーを表示して終了
  - オプション `--force`: 既存ブランチをチェックアウト（警告を表示）
- ブランチ作成後、自動的にチェックアウト
- ブランチ作成元はデフォルトで現在のブランチ（通常はmainまたはdevelop）

**受け入れ基準**:
- Given: Issue URL `https://github.com/tielec/infrastructure-as-code/issues/315` が指定される
- And: ブランチ `ai-workflow/issue-315` が存在しない
- When: `python main.py init --issue-url https://github.com/tielec/infrastructure-as-code/issues/315` を実行
- Then: ブランチ `ai-workflow/issue-315` が作成される
- And: 作業ブランチが `ai-workflow/issue-315` に切り替わる
- And: 成功メッセージが表示される

---

### 2.3 init コマンド実行時のブランチ存在チェック

**優先度**: 高

**要件ID**: FR-003

**説明**: ブランチが既に存在する場合のエラーハンドリング

**仕様**:
- ブランチ存在チェックを実施
- 既存の場合はエラーメッセージを表示
- `--force` オプション指定時は警告を表示してチェックアウト

**受け入れ基準**:
- Given: ブランチ `ai-workflow/issue-315` が既に存在する
- When: `python main.py init --issue-url https://github.com/tielec/infrastructure-as-code/issues/315` を実行
- Then: エラーメッセージ `[ERROR] Branch already exists: ai-workflow/issue-315` が表示される
- And: プログラムが終了コード1で終了する

---

### 2.4 execute コマンド実行時のブランチ自動切り替え

**優先度**: 高

**要件ID**: FR-004

**説明**: `main.py execute --phase <phase> --issue <番号>` 実行時に、対象ブランチに自動的に切り替える

**仕様**:
- Issue番号からブランチ名を生成
- ブランチが存在しない場合:
  - エラーメッセージを表示
  - `init` コマンドの実行を促す
- ブランチが存在する場合:
  - 現在のブランチが対象ブランチと異なる場合は自動的にチェックアウト
  - 未コミットの変更がある場合は警告を表示（チェックアウトは中止）
- Phase実行前にブランチ確認を完了

**受け入れ基準**:
- Given: ブランチ `ai-workflow/issue-315` が存在する
- And: 現在のブランチが `main` である
- When: `python main.py execute --phase requirements --issue 315` を実行
- Then: 作業ブランチが `ai-workflow/issue-315` に切り替わる
- And: Phase実行が開始される

---

### 2.5 Phase完了後の自動コミット・プッシュ

**優先度**: 高

**要件ID**: FR-005

**説明**: 各Phase完了後、変更を対象ブランチにコミットし、リモートリポジトリにプッシュする

**仕様**:
- Phase完了時に、既存の `GitManager.commit_phase_output()` を使用
- コミットメッセージは既存フォーマットを維持
- コミット後、自動的に `GitManager.push_to_remote()` を実行
- プッシュ先ブランチは現在の作業ブランチ（`ai-workflow/issue-{issue_number}`）
- プッシュ失敗時はリトライを実施（最大3回、既存実装を流用）

**受け入れ基準**:
- Given: Phase `requirements` が正常に完了した
- And: 作業ブランチが `ai-workflow/issue-315` である
- When: Phase完了処理が実行される
- Then: 変更が `ai-workflow/issue-315` ブランチにコミットされる
- And: リモートリポジトリの `ai-workflow/issue-315` ブランチにプッシュされる
- And: コミットハッシュがログに出力される

---

### 2.6 GitManagerクラスの拡張

**優先度**: 高

**要件ID**: FR-006

**説明**: GitManagerクラスに、ブランチ作成・切り替え機能を追加する

**仕様**:
- 新規メソッド `create_branch(branch_name: str, base_branch: Optional[str] = None) -> Dict[str, Any]`
  - ブランチを作成し、チェックアウト
  - 既存ブランチの場合はエラーを返却
  - 戻り値: `{'success': bool, 'branch_name': str, 'error': Optional[str]}`
- 新規メソッド `switch_branch(branch_name: str, force: bool = False) -> Dict[str, Any]`
  - 指定ブランチにチェックアウト
  - 未コミット変更がある場合は `force=False` ならエラー
  - 戻り値: `{'success': bool, 'branch_name': str, 'error': Optional[str]}`
- 新規メソッド `branch_exists(branch_name: str) -> bool`
  - ブランチの存在確認
- 新規メソッド `get_current_branch() -> str`
  - 現在のブランチ名を返却

**受け入れ基準**:
- Given: GitManagerインスタンスが初期化されている
- When: `create_branch('ai-workflow/issue-315')` を実行
- Then: ブランチが作成され、チェックアウトされる
- And: 戻り値の `success` が `True` である

---

### 2.7 main.pyの init コマンド拡張

**優先度**: 高

**要件ID**: FR-007

**説明**: `init` コマンドにブランチ作成機能を統合する

**仕様**:
- GitManagerインスタンスを生成（リポジトリルートパスを指定）
- Issue番号からブランチ名を生成
- `GitManager.create_branch()` を呼び出し
- 成功時: ブランチ作成完了メッセージを表示
- 失敗時: エラーメッセージを表示し、プログラムを終了

**受け入れ基準**:
- Given: `init` コマンドが実装されている
- When: `python main.py init --issue-url https://github.com/tielec/infrastructure-as-code/issues/315` を実行
- Then: ブランチ `ai-workflow/issue-315` が作成される
- And: メッセージ `[OK] Branch created and checked out: ai-workflow/issue-315` が表示される

---

### 2.8 main.pyの execute コマンド拡張

**優先度**: 高

**要件ID**: FR-008

**説明**: `execute` コマンドにブランチ切り替え機能を統合する

**仕様**:
- GitManagerインスタンスを生成
- Issue番号からブランチ名を生成
- `GitManager.branch_exists()` で存在確認
- 存在しない場合: エラーメッセージを表示し、`init` コマンドの実行を促す
- 存在する場合: `GitManager.switch_branch()` を呼び出し
- 切り替え成功後、Phase実行を継続

**受け入れ基準**:
- Given: ブランチ `ai-workflow/issue-315` が存在する
- When: `python main.py execute --phase requirements --issue 315` を実行
- Then: 作業ブランチが `ai-workflow/issue-315` に切り替わる
- And: メッセージ `[INFO] Switched to branch: ai-workflow/issue-315` が表示される
- And: Phase実行が開始される

---

### 2.9 エラーハンドリングとロギング

**優先度**: 中

**要件ID**: FR-009

**説明**: ブランチ操作に関する適切なエラーハンドリングとロギングを実装する

**仕様**:
- すべてのGit操作でエラーをキャッチ
- エラー発生時は詳細なエラーメッセージをユーザーに表示
- 成功時は成功メッセージを表示
- ログレベル:
  - `[INFO]`: 通常の処理フロー
  - `[WARN]`: 警告（処理は継続）
  - `[ERROR]`: エラー（処理は中止）
  - `[OK]`: 成功

**受け入れ基準**:
- Given: ブランチ作成中にネットワークエラーが発生した
- When: GitManagerが例外をキャッチする
- Then: エラーメッセージ `[ERROR] Failed to create branch: {error_message}` が表示される
- And: 戻り値の `success` が `False` である

---

### 2.10 リモートブランチの自動作成

**優先度**: 中

**要件ID**: FR-010

**説明**: Phase完了時のプッシュで、リモートに存在しないブランチを自動作成する

**仕様**:
- `git push -u origin {branch_name}` を実行
- リモートブランチが存在しない場合は自動的に作成
- プッシュ成功後、アップストリームブランチを設定

**受け入れ基準**:
- Given: ローカルブランチ `ai-workflow/issue-315` が存在する
- And: リモートブランチ `ai-workflow/issue-315` が存在しない
- When: `GitManager.push_to_remote()` を実行
- Then: リモートブランチ `ai-workflow/issue-315` が作成される
- And: ローカルブランチのアップストリームが設定される

---

## 3. 非機能要件

### 3.1 パフォーマンス要件

**要件ID**: NFR-001

- ブランチ作成・切り替え処理は3秒以内に完了すること
- リモートプッシュは、ネットワーク状況により変動するが、タイムアウトは30秒とする
- Gitコマンド実行時のオーバーヘッドは最小化すること

### 3.2 信頼性要件

**要件ID**: NFR-002

- ブランチ作成・切り替え失敗時は、プログラムを適切に終了し、ユーザーに明確なエラーメッセージを表示すること
- リモートプッシュ失敗時は、最大3回までリトライすること（既存実装を流用）
- 未コミットの変更がある状態でのブランチ切り替えは禁止すること

### 3.3 可用性要件

**要件ID**: NFR-003

- Gitリポジトリが存在しない場合は、明確なエラーメッセージを表示すること
- ネットワーク障害時は、ローカル操作（ブランチ作成・切り替え・コミット）は継続可能とすること
- リモートプッシュはネットワーク復旧後に手動で実行可能であること

### 3.4 保守性・拡張性要件

**要件ID**: NFR-004

- GitManagerクラスのメソッドは、単一責任原則に従い、テスタブルな設計とすること
- ブランチ命名規則は将来的に変更可能な設計とすること（設定ファイルでの管理を推奨）
- Pull Request自動作成機能の追加を見据えた拡張性を確保すること

### 3.5 セキュリティ要件

**要件ID**: NFR-005

- GitHub Tokenは環境変数から取得し、ハードコーディングしないこと
- リモートURLには認証情報を含めること（既存のGitManager実装を流用）
- ブランチ作成・切り替え時は、権限エラーを適切にハンドリングすること

---

## 4. 制約事項

### 4.1 技術的制約

- **Git**: Git 2.20以上が必要（ブランチ作成・切り替え機能を利用）
- **Python**: Python 3.8以上が必要（既存のAI Workflowシステムと同様）
- **GitPython**: GitPython 3.1以上が必要（既存の依存関係を維持）
- **既存実装との整合性**: 既存の `GitManager` クラスのメソッドシグネチャを変更しないこと
- **コミットメッセージフォーマット**: 既存のフォーマットを維持すること（Phase番号、Issue番号を含む）

### 4.2 リソース制約

- **開発期間**: 1週間以内に実装を完了すること
- **テスト**: ユニットテスト、統合テストを実施すること
- **ドキュメント**: 実装完了後、README.mdに使用方法を追記すること

### 4.3 ポリシー制約

- **コーディング規約**: CLAUDE.mdに記載されたコーディングガイドラインに従うこと
  - コメントは日本語で記述
  - 変数名・関数名は英語（スネークケース）
  - ドキュメントは日本語
- **Git戦略**: ブランチ命名規則は `ai-workflow/issue-{issue_number}` に統一すること
- **コミット規約**: コミットメッセージは既存フォーマットを維持すること

---

## 5. 前提条件

### 5.1 システム環境

- **OS**: Linux（推奨）、macOS、Windows（WSL2）
- **Python**: 3.8以上
- **Git**: 2.20以上
- **GitHub**: GitHubリポジトリへのプッシュ権限があること

### 5.2 依存コンポーネント

- **GitPython**: 既にインストール済み（既存のAI Workflowシステムで使用）
- **Click**: CLIフレームワーク（既存のmain.pyで使用）
- **MetadataManager**: 既存のメタデータ管理クラス

### 5.3 外部システム連携

- **GitHub**: リモートリポジトリとしてGitHubを使用
- **GitHub Token**: 環境変数 `GITHUB_TOKEN` が設定されていること
- **GitHub Repository**: 環境変数 `GITHUB_REPOSITORY` が設定されていること（例: `tielec/infrastructure-as-code`）

---

## 6. 受け入れ基準

### 6.1 機能受け入れ基準

#### TC-001: ブランチ自動作成（init コマンド）

- **Given**: Issue URL `https://github.com/tielec/infrastructure-as-code/issues/315` が指定される
- **And**: ブランチ `ai-workflow/issue-315` が存在しない
- **When**: `python main.py init --issue-url https://github.com/tielec/infrastructure-as-code/issues/315` を実行
- **Then**: ブランチ `ai-workflow/issue-315` が作成される
- **And**: 作業ブランチが `ai-workflow/issue-315` に切り替わる
- **And**: メッセージ `[OK] Branch created and checked out: ai-workflow/issue-315` が表示される
- **And**: メタデータファイル `metadata.json` が作成される

#### TC-002: ブランチ存在チェック（init コマンド）

- **Given**: ブランチ `ai-workflow/issue-315` が既に存在する
- **When**: `python main.py init --issue-url https://github.com/tielec/infrastructure-as-code/issues/315` を実行
- **Then**: エラーメッセージ `[ERROR] Branch already exists: ai-workflow/issue-315` が表示される
- **And**: プログラムが終了コード1で終了する
- **And**: 新しいメタデータファイルは作成されない

#### TC-003: ブランチ自動切り替え（execute コマンド）

- **Given**: ブランチ `ai-workflow/issue-315` が存在する
- **And**: 現在のブランチが `main` である
- **And**: 未コミットの変更がない
- **When**: `python main.py execute --phase requirements --issue 315` を実行
- **Then**: 作業ブランチが `ai-workflow/issue-315` に切り替わる
- **And**: メッセージ `[INFO] Switched to branch: ai-workflow/issue-315` が表示される
- **And**: Phase `requirements` が実行される

#### TC-004: ブランチ未存在エラー（execute コマンド）

- **Given**: ブランチ `ai-workflow/issue-999` が存在しない
- **When**: `python main.py execute --phase requirements --issue 999` を実行
- **Then**: エラーメッセージ `[ERROR] Branch not found: ai-workflow/issue-999. Please run 'init' first.` が表示される
- **And**: プログラムが終了コード1で終了する

#### TC-005: Phase完了後の自動コミット・プッシュ

- **Given**: Phase `requirements` が正常に完了した
- **And**: 作業ブランチが `ai-workflow/issue-315` である
- **When**: Phase完了処理が実行される
- **Then**: 変更が `.ai-workflow/issue-315/` 配下にコミットされる
- **And**: コミットメッセージに `[ai-workflow] Phase 1 (requirements) - completed` が含まれる
- **And**: リモートブランチ `ai-workflow/issue-315` にプッシュされる
- **And**: コミットハッシュがログに出力される

#### TC-006: 未コミット変更がある場合の警告

- **Given**: 未コミットの変更がある
- **And**: 現在のブランチが `main` である
- **When**: `python main.py execute --phase requirements --issue 315` を実行
- **Then**: 警告メッセージ `[WARN] You have uncommitted changes. Please commit or stash them before switching branches.` が表示される
- **And**: ブランチ切り替えは実行されない
- **And**: プログラムが終了コード1で終了する

### 6.2 非機能受け入れ基準

#### TC-NFR-001: パフォーマンス

- **Given**: Gitリポジトリが正常に動作している
- **When**: `python main.py init --issue-url {URL}` を実行
- **Then**: 3秒以内にブランチが作成される

#### TC-NFR-002: 信頼性（リトライ）

- **Given**: ネットワーク一時障害によりプッシュが1回失敗する
- **When**: `GitManager.push_to_remote()` が実行される
- **Then**: 自動的にリトライされる
- **And**: 2回目のプッシュが成功する
- **And**: ログに `[INFO] Git push failed. Retrying (1/3)...` が表示される

#### TC-NFR-003: セキュリティ

- **Given**: 環境変数 `GITHUB_TOKEN` が設定されている
- **When**: リモートプッシュが実行される
- **Then**: 認証情報付きのHTTPS URLが使用される
- **And**: コンソール出力やログにトークンが表示されない

---

## 7. スコープ外

以下の項目は、本要件のスコープ外とします：

### 7.1 Pull Request自動作成機能

- Pull Requestの自動作成・更新は、本機能では実装しない
- 将来的な拡張として、Issue #XXX（別Issue）で実装予定

### 7.2 ブランチマージ機能

- ブランチのマージ（mainへのマージ等）は手動で実施
- 自動マージは将来的な拡張として検討

### 7.3 ブランチ削除機能

- ブランチの自動削除（Issue完了後のクリーンアップ）は本機能では実装しない
- 将来的な拡張として検討

### 7.4 複数ブランチ間の切り替え履歴管理

- ブランチ切り替え履歴の記録・可視化は実装しない
- 必要に応じて `git reflog` を使用

### 7.5 ブランチ保護ルールの設定

- GitHubのブランチ保護ルール設定は、リポジトリ管理者が手動で実施
- AI Workflowからの自動設定は実装しない

### 7.6 コンフリクト解決の自動化

- ブランチ切り替え時やマージ時のコンフリクト解決は手動で実施
- AI Workflowによる自動解決は実装しない

---

## 8. 実装アプローチ（参考情報）

### 8.1 実装順序（推奨）

1. **GitManagerクラスの拡張**
   - `create_branch()` メソッド実装
   - `switch_branch()` メソッド実装
   - `branch_exists()` メソッド実装
   - `get_current_branch()` メソッド実装
   - ユニットテスト作成

2. **main.pyの init コマンド拡張**
   - GitManagerインスタンス生成
   - ブランチ作成処理の統合
   - エラーハンドリング
   - 統合テスト作成

3. **main.pyの execute コマンド拡張**
   - ブランチ切り替え処理の統合
   - エラーハンドリング
   - 統合テスト作成

4. **Phase完了後のプッシュ処理統合**
   - `BasePhase` クラスでの `GitManager.push_to_remote()` 呼び出し
   - 統合テスト作成

5. **E2Eテスト作成**
   - init → execute → commit → push の一連のフローをテスト

6. **ドキュメント更新**
   - README.mdに使用方法を追記
   - CLAUDE.mdに実装ガイドラインを追記（必要に応じて）

### 8.2 既存コードの活用

- `GitManager.commit_phase_output()`: コミット処理はそのまま流用
- `GitManager.push_to_remote()`: プッシュ処理はそのまま流用（リトライ機能含む）
- `GitManager._setup_github_credentials()`: GitHub Token設定はそのまま流用

### 8.3 新規実装の範囲

- `GitManager.create_branch()`: 新規実装
- `GitManager.switch_branch()`: 新規実装
- `GitManager.branch_exists()`: 新規実装
- `GitManager.get_current_branch()`: 新規実装（既存の `get_status()` から分離）
- `main.py init` コマンド: ブランチ作成処理を追加
- `main.py execute` コマンド: ブランチ切り替え処理を追加

---

## 9. リスクと対策

### 9.1 リスク: ブランチ切り替え時の未コミット変更の損失

**影響度**: 高
**発生確率**: 中

**対策**:
- ブランチ切り替え前に `git status` で未コミット変更をチェック
- 未コミット変更がある場合はエラーを表示し、ユーザーにコミットまたはstashを促す
- `--force` オプションを追加し、強制的に切り替える場合は警告を表示

### 9.2 リスク: リモートプッシュ失敗によるデータ損失

**影響度**: 中
**発生確率**: 低

**対策**:
- ローカルコミットは必ず成功させる（ネットワーク障害に影響されない）
- プッシュ失敗時はリトライ（最大3回）
- リトライ失敗時はユーザーに手動プッシュを促すメッセージを表示
- 次回のPhase実行時に未プッシュコミットを検知し、再プッシュを試行

### 9.3 リスク: ブランチ命名規則の変更

**影響度**: 低
**発生確률**: 低

**対策**:
- ブランチ命名規則はコード内で定数化（`BRANCH_PREFIX = "ai-workflow/issue-"`）
- 将来的に設定ファイル（config.yaml）で管理可能な設計とする
- ドキュメントに命名規則を明記し、変更時は全体に影響することを周知

### 9.4 リスク: 並行実行時のブランチ競合

**影響度**: 中
**発生確率**: 低

**対策**:
- 各Issueは独立したブランチで作業するため、基本的には競合しない
- 同一Issueに対して複数のPhaseを並行実行することは禁止する（metadata.jsonでPhaseステータスを管理）
- `execute` コマンド実行前にPhaseステータスをチェックし、既に実行中の場合はエラーを表示

---

## 10. 成功指標

### 10.1 定量的指標

- **ブランチ作成成功率**: 95%以上
- **ブランチ切り替え成功率**: 95%以上
- **リモートプッシュ成功率**: 90%以上（ネットワーク障害を除く）
- **テストカバレッジ**: 80%以上（ユニットテスト + 統合テスト）

### 10.2 定性的指標

- **開発者体験の向上**: 手動ブランチ作成・切り替えが不要になり、開発効率が向上
- **コードレビューの効率化**: Issue単位でブランチが分離され、レビューが容易
- **運用の安定性**: ブランチ管理の自動化により、ヒューマンエラーが減少

---

## 11. 品質ゲート（Phase 1）

本要件定義書は、以下の品質ゲートを満たしています：

- ✅ **機能要件が明確に記載されている**: セクション2に10個の機能要件を詳細に記載
- ✅ **受け入れ基準が定義されている**: セクション6にGiven-When-Then形式で記載
- ✅ **スコープが明確である**: セクション7にスコープ外項目を明記
- ✅ **論理的な矛盾がない**: すべてのセクションで整合性を確認済み

---

## 12. 参考資料

- **CLAUDE.md**: プロジェクトの全体方針とコーディングガイドライン
- **ARCHITECTURE.md**: Platform Engineeringのアーキテクチャ設計思想
- **CONTRIBUTION.md**: 開発ガイドライン
- **ai-workflow-requirements.md**: AI Workflowの全体要件定義
- **GitPython Documentation**: https://gitpython.readthedocs.io/

---

## 13. 変更履歴

| バージョン | 日付 | 変更内容 | 作成者 |
|-----------|------|---------|--------|
| 1.0.0 | 2025-10-10 | 初版作成 | AI Workflow |

---

**以上**
