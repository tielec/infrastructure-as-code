# 要件定義書 - Issue #355

## 0. Planning Documentの確認

### 開発計画の概要

**Planning Document**: [.ai-workflow/issue-355/00_planning/output/planning.md](.ai-workflow/issue-355/00_planning/output/planning.md)

#### 実装戦略
- **戦略**: EXTEND（既存コードの拡張）
- **根拠**: `main.py`の`init`コマンドを拡張し、既存のGitManager、GitHubClientを活用
- **変更ファイル**: main.py、github_client.py（git_manager.pyは既存機能活用のみ）

#### テスト戦略
- **戦略**: UNIT_INTEGRATION（ユニットテスト + 統合テスト）
- **ユニットテスト**: GitHubClient.create_pull_request()、エラーハンドリング
- **統合テスト**: initコマンド全体（ブランチ作成 → commit → push → PR作成）

#### テストコード戦略
- **戦略**: BOTH_TEST（既存テスト拡張 + 新規テスト作成）
- **拡張対象**: tests/unit/core/test_github_client.py、tests/integration/test_workflow_init.py
- **新規作成**: tests/unit/test_main_init_pr.py、tests/integration/test_init_pr_workflow.py

#### 主要リスク
1. **gh CLI依存**: Docker環境にgh CLIがインストールされていない可能性
   - 軽減策: PyGithubのPR作成APIを使用（gh CLI依存を排除）
2. **GitHub Token権限**: repo スコープが必要（PRの作成権限）
   - 軽減策: initコマンド実行前にトークン権限をチェック
3. **既存PR重複**: 同じブランチで既にPRが存在する場合の処理
   - 軽減策: `check_existing_pr()`で事前チェック、既存PR存在時はスキップ

#### 見積もり工数
- **総工数**: 約12時間
- **Phase 4（実装）**: 3時間
- **Phase 5（テスト実装）**: 2時間

---

## 1. 概要

### 背景
現在、AI Workflowの初期化コマンド（`python main.py init --issue-url <URL>`）は、以下の処理を実行します：

1. `.ai-workflow/issue-XXX/metadata.json`を作成
2. ローカルブランチ`ai-workflow/issue-XXX`を作成

しかし、この時点でブランチはローカルにのみ存在し、リモートにpushされません。また、Pull Request（PR）は手動で作成する必要があります。

### 問題点
- **作業の可視性が低い**: GitHub上でワークフローの進捗を追跡できない
- **手動操作が必要**: PR作成を毎回手動で行う必要がある
- **チーム協業の障壁**: 他の開発者がワークフローの状態を把握しづらい

### 目的
`init`コマンド実行時に、以下を自動化する：

1. **Git commit & push**: metadata.jsonをコミットし、リモートブランチにpush
2. **ドラフトPR作成**: ワークフロー進捗を追跡可能なドラフトPRを自動作成

### ビジネス価値
- **開発効率向上**: PR作成の手動作業を削減（1回あたり2-3分の削減）
- **可視性向上**: GitHub上でワークフロー進捗をリアルタイムで追跡可能
- **レビューの早期化**: ドラフトPRにより、作業中でもレビュアーがコードを確認可能

### 技術的価値
- **既存機能の活用**: GitManager、GitHubClientの既存メソッドを最大限活用
- **拡張性**: 将来的なPR本文の動的更新、`--no-pr`オプション追加が容易
- **保守性**: 既存のアーキテクチャを維持しつつ、最小限の変更で実現

---

## 2. 機能要件

### FR-1: Git Commit機能（優先度: 高）

**説明**: metadata.json作成後、自動的にGitコミットを作成する。

**詳細仕様**:
- コミット対象ファイル: `.ai-workflow/issue-XXX/metadata.json`
- コミットメッセージ形式:
  ```
  [ai-workflow] Phase 0 (init) - metadata初期化

  Issue #XXX のAIワークフローを開始しました。
  ```
- コミット実行条件:
  - metadata.jsonが正常に作成されている
  - Gitリポジトリが存在する
  - Git設定（user.name、user.email）が有効

**既存機能の活用**:
- `GitManager.commit_phase_output(phase_name='init', status='completed', review_result='PASS')`メソッドを使用
- 既存のコミットメッセージ生成ロジックを活用（scripts/ai-workflow/core/git_manager.py:237-298）

**エラーハンドリング**:
- コミット失敗時は警告メッセージを表示し、PR作成をスキップ
- エラーメッセージ例: `[WARNING] Commit失敗。PRは作成されません: {error_message}`

---

### FR-2: Git Push機能（優先度: 高）

**説明**: コミット成功後、リモートブランチにpushする。

**詳細仕様**:
- Push対象ブランチ: `ai-workflow/issue-XXX`
- Push先: `origin/{branch_name}`
- リトライ機能:
  - 最大3回リトライ
  - リトライ間隔: 2秒（exponential backoffなし）
- Push実行条件:
  - コミットが成功している
  - リモート`origin`が設定されている
  - GitHub Tokenが環境変数`GITHUB_TOKEN`に設定されている

**既存機能の活用**:
- `GitManager.push_to_remote(max_retries=3, retry_delay=2.0)`メソッドを使用
- 既存のリトライロジックを活用（scripts/ai-workflow/core/git_manager.py:122-235）

**エラーハンドリング**:
- Push失敗時は警告メッセージを表示し、PR作成をスキップ
- エラーメッセージ例: `[WARNING] Push失敗。PRは作成されません: {error_message}`
- リトライ可能なエラー（ネットワークエラー等）は自動リトライ
- リトライ不可能なエラー（認証エラー等）は即座に失敗

---

### FR-3: ドラフトPR作成機能（優先度: 高）

**説明**: Push成功後、ドラフトPull Requestを自動作成する。

**詳細仕様**:
- PR作成方法: PyGithubのPR作成API（`repository.create_pull()`）を使用（gh CLI依存を排除）
- PRタイトル: `[AI-Workflow] Issue #{issue_number}`
- PR本文: 以下のテンプレートを使用
  ```markdown
  ## AI Workflow自動生成PR

  ### 📋 関連Issue
  Closes #{issue_number}

  ### 🔄 ワークフロー進捗

  - [x] Phase 0: Planning
  - [ ] Phase 1: Requirements
  - [ ] Phase 2: Design
  - [ ] Phase 3: Test Scenario
  - [ ] Phase 4: Implementation
  - [ ] Phase 5: Test Implementation
  - [ ] Phase 6: Testing
  - [ ] Phase 7: Documentation
  - [ ] Phase 8: Report

  ### 📁 成果物

  `.ai-workflow/issue-{issue_number}/` ディレクトリに各フェーズの成果物が格納されています。

  ### ⚙️ 実行環境

  - **モデル**: Claude Code Pro Max (Sonnet 4.5)
  - **ContentParser**: OpenAI GPT-4o mini
  - **ブランチ**: {branch_name}
  ```
- PR作成オプション:
  - `draft=True`（ドラフトPRとして作成）
  - `base="main"`（マージ先ブランチ）
  - `head="ai-workflow/issue-XXX"`（作成元ブランチ）
- PR作成条件:
  - Pushが成功している
  - GitHub Tokenが`repo`スコープを持つ
  - 既存PRが同じブランチに存在しない（後述のFR-4で事前チェック）

**新規実装が必要**:
- `GitHubClient.create_pull_request()`メソッドの追加（scripts/ai-workflow/core/github_client.py）
- 実装詳細:
  ```python
  def create_pull_request(
      self,
      title: str,
      body: str,
      head: str,
      base: str = "main",
      draft: bool = True
  ) -> Dict[str, Any]:
      """
      Pull Requestを作成

      Args:
          title: PRタイトル
          body: PR本文（Markdown形式）
          head: 作成元ブランチ名
          base: マージ先ブランチ名（デフォルト: main）
          draft: ドラフトPRとして作成（デフォルト: True）

      Returns:
          Dict[str, Any]:
              - success: bool - 成功/失敗
              - pr_url: str - 作成されたPRのURL
              - pr_number: int - PR番号
              - error: Optional[str] - エラーメッセージ
      """
      # 実装は設計フェーズで詳細化
  ```

**エラーハンドリング**:
- PR作成失敗時は警告メッセージを表示（initコマンド全体は成功として扱う）
- エラーメッセージ例: `[WARNING] PR作成失敗: {error_message}`
- 失敗ケース:
  - GitHub Token権限不足（`repo`スコープなし）
  - 既存PRが存在する（スキップ処理、FR-4参照）
  - ネットワークエラー

---

### FR-4: 既存PRチェック機能（優先度: 中）

**説明**: PR作成前に、同じブランチで既存PRが存在するかチェックする。

**詳細仕様**:
- チェック対象: `origin/ai-workflow/issue-XXX`ブランチ
- チェック方法: PyGithubの`repository.get_pulls(state='open', head='{owner}:{branch_name}')`を使用
- 既存PR存在時の動作:
  - PR作成をスキップ
  - 既存PR URLを表示
  - 成功として扱う（エラーではない）

**新規実装が必要**:
- `GitHubClient.check_existing_pr()`メソッドの追加（scripts/ai-workflow/core/github_client.py）
- 実装詳細:
  ```python
  def check_existing_pr(self, branch_name: str) -> Dict[str, Any]:
      """
      既存PRの存在確認

      Args:
          branch_name: ブランチ名

      Returns:
          Dict[str, Any]:
              - exists: bool - 既存PRが存在するか
              - pr_url: Optional[str] - 既存PRのURL
              - pr_number: Optional[int] - 既存PR番号
              - error: Optional[str] - エラーメッセージ
      """
      # 実装は設計フェーズで詳細化
  ```

**エラーハンドリング**:
- チェック失敗時は警告メッセージを表示し、PR作成を試行
- エラーメッセージ例: `[WARNING] 既存PRチェック失敗: {error_message}`

---

### FR-5: PR URL記録機能（優先度: 低）

**説明**: 作成されたPR URLをmetadata.jsonに記録する（オプション）。

**詳細仕様**:
- 記録先: `.ai-workflow/issue-XXX/metadata.json`
- 記録フィールド: `pr_url`（新規追加）
- スキーマ例:
  ```json
  {
    "issue_number": 355,
    "issue_url": "https://github.com/tielec/infrastructure-as-code/issues/355",
    "pr_url": "https://github.com/tielec/infrastructure-as-code/pull/XXX",
    "phases": {...}
  }
  ```

**実装方針**:
- Phase 4（実装）で実装を検討（必須ではない）
- 後方互換性: `pr_url`フィールドは省略可能

---

### FR-6: PR本文テンプレート動的生成（優先度: 低、将来実装）

**説明**: PR本文のワークフロー進捗チェックリストを動的に生成する。

**詳細仕様**:
- Planning Phase（Phase 0）が完了している場合、チェックボックスを`[x]`に更新
- 各フェーズ完了時にPR本文を更新（`gh pr edit`またはPyGithub APIを使用）

**実装時期**: Phase 4（実装）では実装せず、Issue #355完了後の拡張機能として検討

---

## 3. 非機能要件

### NFR-1: パフォーマンス要件

**応答時間**:
- `init`コマンド全体の実行時間: 15秒以内
  - metadata.json作成: 1秒以内
  - ブランチ作成: 1秒以内
  - Git commit: 2秒以内
  - Git push: 5秒以内（ネットワーク状況による）
  - PR作成: 5秒以内（GitHub API応答時間による）

**スループット**:
- 同時実行: 想定されない（1ユーザーが1回のみ実行）

**リトライ戦略**:
- Git push: 最大3回リトライ、リトライ間隔2秒
- PR作成: リトライなし（エラー時は警告表示のみ）

---

### NFR-2: セキュリティ要件

**認証情報管理**:
- GitHub Token: 環境変数`GITHUB_TOKEN`から取得
- トークンの最小権限: `repo`スコープ（PRの作成・編集権限）
- トークンのログ出力禁止: エラーメッセージに認証情報を含めない

**権限確認**:
- `init`コマンド実行前に`GITHUB_TOKEN`の存在を確認
- トークン権限不足時は明確なエラーメッセージを表示
  - 例: `[ERROR] GitHub Tokenに 'repo' スコープが必要です。トークンを再発行してください。`

**監査ログ**:
- PR作成時の操作ログをGitHub Audit Logに記録（GitHub API標準機能）

---

### NFR-3: 可用性要件

**エラー許容性**:
- Commit失敗時: PR作成をスキップし、警告メッセージを表示（initコマンド全体は成功）
- Push失敗時: PR作成をスキップし、警告メッセージを表示（initコマンド全体は成功）
- PR作成失敗時: 警告メッセージを表示（initコマンド全体は成功）

**フォールバック戦略**:
- PR作成失敗時: 手動PR作成の案内メッセージを表示
  - 例: `[WARNING] PR作成失敗。手動でPRを作成してください: gh pr create --draft --title "[AI-Workflow] Issue #355" --base main`

**依存サービスの障害対応**:
- GitHub API障害時: リトライせず、警告メッセージを表示

---

### NFR-4: 保守性要件

**コードの可読性**:
- PEP 8準拠（Pythonコーディング規約）
- 関数ごとにdocstringを記述（Args、Returns、Raisesを明記）

**テストカバレッジ**:
- 目標カバレッジ: 80%以上
- テスト対象:
  - ユニットテスト: GitHubClient.create_pull_request()、check_existing_pr()
  - 統合テスト: initコマンド全体（commit → push → PR作成）

**ログ出力**:
- 各処理ステップで進捗ログを出力
  - `[INFO] metadata.jsonを作成しました: {path}`
  - `[INFO] ブランチを作成しました: {branch_name}`
  - `[INFO] コミットを作成しました: {commit_hash}`
  - `[INFO] ブランチをリモートにpushしました: {branch_name}`
  - `[INFO] ドラフトPRを作成しました: {pr_url}`

**エラーメッセージ**:
- ユーザーにとって理解しやすいメッセージ
- エラー原因と対処方法を明記

---

### NFR-5: 拡張性要件

**将来的な拡張機能**:
- `--no-pr`オプション: PR作成をスキップするオプション
  - 実装例: `python main.py init --issue-url <URL> --no-pr`
- PR本文の動的更新: 各フェーズ完了時にPR本文のチェックリストを自動更新
- PR作成リトライ: ネットワークエラー時の自動リトライ（exponential backoff）

**アーキテクチャの柔軟性**:
- GitHubClient.create_pull_request()メソッドは独立しており、他のコマンドからも呼び出し可能
- PR本文テンプレートは外部ファイル化可能（現時点ではコード内に埋め込み）

---

### NFR-6: 互換性要件

**後方互換性**:
- 既存のinitコマンドの動作を変更しない
  - metadata.json作成
  - ブランチ作成
- 新機能（commit、push、PR作成）はすべて追加機能

**環境依存性**:
- Python 3.11以上
- PyGithub 2.0以上（PR作成APIを使用）
- GitPython 3.1以上（Git操作）
- Docker環境での動作保証

---

## 4. 制約事項

### 技術的制約

**CT-1: GitHub API制約**
- APIレート制限: 認証済みユーザーは5000リクエスト/時間
- 影響: init1回あたり2-3リクエスト（既存PRチェック、PR作成）のため、実質的な制限なし
- 対策: エラー時に明確なメッセージを表示

**CT-2: Git操作制約**
- リモートブランチが存在しない場合のpush: `-u`オプションを使用して新規ブランチを作成
- 既存実装: GitManager.push_to_remote()は`git push origin HEAD:{branch_name}`を使用（自動的に新規ブランチ作成）

**CT-3: PyGithub制約**
- PR作成API: `repository.create_pull(title, body, head, base, draft)`
- draft引数: PyGithub 2.0以降でサポート
- 対策: requirements.txtに`PyGithub>=2.0.0`を明記

**CT-4: Docker環境制約**
- gh CLI依存の排除: PyGithubのPR作成APIを使用することで、gh CLIのインストールが不要
- メリット: Dockerイメージのサイズ削減、依存関係の簡素化

---

### リソース制約

**RC-1: 時間制約**
- 見積もり工数: 12時間（Planning Documentより）
- 実装期間: 2-3日（1日4時間作業として）

**RC-2: 人員制約**
- 開発者: 1名（AIエージェント）
- レビュアー: 人間の開発者（クリティカルシンキングレビュー）

---

### ポリシー制約

**PC-1: コーディング規約**
- PEP 8準拠（Pythonコーディング規約）
- プロジェクト固有の規約: CLAUDE.md、CONTRIBUTION.mdに従う
- docstring形式: Google Style

**PC-2: コミットメッセージ規約**
- フォーマット: `[Component] Action: 詳細な説明`
- 例: `[ai-workflow] add: Init時にドラフトPRを自動作成する機能を追加`

**PC-3: テスト必須**
- ユニットテスト: 新規メソッドは必ずテストを作成
- 統合テスト: initコマンド全体のワークフローをテスト
- カバレッジ目標: 80%以上

---

## 5. 前提条件

### システム環境

**ENV-1: Python環境**
- Python 3.11以上
- pip 23.0以上

**ENV-2: 依存ライブラリ**
- PyGithub 2.0以上（PR作成API）
- GitPython 3.1以上（Git操作）
- click 8.0以上（CLIフレームワーク）

**ENV-3: Docker環境**
- Dockerイメージ: `ai-workflow:latest`
- ベースイメージ: Python 3.11-slim
- プリインストール: git、python3、pip3

---

### 依存コンポーネント

**DEP-1: Gitリポジトリ**
- リポジトリが存在する（`.git`ディレクトリが存在）
- リモート`origin`が設定されている
- Git設定（user.name、user.email）が有効（未設定の場合は環境変数から自動設定）

**DEP-2: GitHub Repository**
- リポジトリがGitHub上に存在する
- リモートURLがGitHub（`https://github.com/{owner}/{repo}.git`）

**DEP-3: 環境変数**
- `GITHUB_TOKEN`: GitHub Personal Access Token（`repo`スコープ）
- `GITHUB_REPOSITORY`: リポジトリ名（例: `tielec/infrastructure-as-code`）
- `GIT_COMMIT_USER_NAME`（オプション）: Git commit user name
- `GIT_COMMIT_USER_EMAIL`（オプション）: Git commit user email

---

### 外部システム連携

**EXT-1: GitHub API**
- GitHub REST API v3
- 認証: Personal Access Token（Bearer Token）
- 必要スコープ: `repo`（PRの作成・編集権限）

**EXT-2: Git Remote（GitHub）**
- HTTPS認証: `https://{token}@github.com/{owner}/{repo}.git`
- 既存実装: GitManager._setup_github_credentials()で自動設定（scripts/ai-workflow/core/git_manager.py:853-890）

---

## 6. 受け入れ基準

### AC-1: Git Commit機能

**Given**: metadata.jsonが正常に作成されている
**When**: initコマンドを実行する
**Then**:
- `.ai-workflow/issue-XXX/metadata.json`がコミットされる
- コミットメッセージが`[ai-workflow] Phase 0 (init) - completed`形式である
- コミットハッシュが取得できる

**検証方法**:
```bash
python main.py init --issue-url https://github.com/tielec/infrastructure-as-code/issues/355
git log -1 --oneline | grep "[ai-workflow] Phase 0 (init) - completed"
```

---

### AC-2: Git Push機能

**Given**: コミットが成功している
**When**: initコマンドを実行する
**Then**:
- リモートブランチ`origin/ai-workflow/issue-XXX`が作成される
- pushが成功し、成功メッセージが表示される
- リトライ機能がネットワークエラー時に動作する（最大3回）

**検証方法**:
```bash
python main.py init --issue-url https://github.com/tielec/infrastructure-as-code/issues/355
git ls-remote origin | grep "refs/heads/ai-workflow/issue-355"
```

---

### AC-3: ドラフトPR作成機能

**Given**: pushが成功している
**When**: initコマンドを実行する
**Then**:
- ドラフトPRが作成される
- PRタイトルが`[AI-Workflow] Issue #355`である
- PR本文にワークフロー進捗チェックリストが含まれる
- PR URLが表示される

**検証方法**:
```bash
python main.py init --issue-url https://github.com/tielec/infrastructure-as-code/issues/355
gh pr list --head ai-workflow/issue-355 --json number,title,isDraft
```

---

### AC-4: 既存PRチェック機能

**Given**: 同じブランチで既存PRが存在する
**When**: initコマンドを実行する
**Then**:
- PR作成がスキップされる
- 既存PR URLが表示される
- initコマンド全体は成功として扱われる

**検証方法**:
```bash
# 既存PR作成
gh pr create --draft --title "[AI-Workflow] Issue #355" --base main --head ai-workflow/issue-355

# initコマンド実行（既存PR存在時）
python main.py init --issue-url https://github.com/tielec/infrastructure-as-code/issues/355

# 出力に既存PR URLが含まれることを確認
# 例: [INFO] 既存PRが存在します: https://github.com/tielec/infrastructure-as-code/pull/XXX
```

---

### AC-5: エラーハンドリング

**Given**: GitHub Tokenが未設定
**When**: initコマンドを実行する
**Then**:
- エラーメッセージが表示される
- 例: `[ERROR] GITHUB_TOKEN environment variable is required`

**検証方法**:
```bash
unset GITHUB_TOKEN
python main.py init --issue-url https://github.com/tielec/infrastructure-as-code/issues/355
# エラーメッセージが表示され、exit code 1で終了
```

---

**Given**: Commit失敗（Gitリポジトリが存在しない）
**When**: initコマンドを実行する
**Then**:
- 警告メッセージが表示される
- 例: `[WARNING] Commit失敗。PRは作成されません: {error_message}`
- initコマンド全体は成功として扱われる（exit code 0）

**検証方法**:
```bash
# Gitリポジトリ外で実行
cd /tmp
python main.py init --issue-url https://github.com/tielec/infrastructure-as-code/issues/355
# 警告メッセージが表示されるが、exit code 0で終了
```

---

**Given**: Push失敗（ネットワークエラー）
**When**: initコマンドを実行する
**Then**:
- 最大3回リトライが実行される
- リトライ後も失敗する場合、警告メッセージが表示される
- 例: `[WARNING] Push失敗。PRは作成されません: {error_message}`

**検証方法**:
```bash
# ネットワークを一時的に無効化
# 統合テストでモック化してテスト
```

---

### AC-6: パフォーマンス

**Given**: 正常な環境
**When**: initコマンドを実行する
**Then**:
- 全体の実行時間が15秒以内である
- 各処理ステップが以下の時間内に完了する:
  - metadata.json作成: 1秒以内
  - ブランチ作成: 1秒以内
  - Git commit: 2秒以内
  - Git push: 5秒以内
  - PR作成: 5秒以内

**検証方法**:
```bash
time python main.py init --issue-url https://github.com/tielec/infrastructure-as-code/issues/355
# 実行時間を確認
```

---

### AC-7: 後方互換性

**Given**: 既存のワークフロー（init → execute）が存在する
**When**: 新機能を追加する
**Then**:
- 既存のワークフローが正常に動作する
- metadata.jsonのスキーマが後方互換性を保つ
- `pr_url`フィールドは省略可能

**検証方法**:
```bash
# 既存のワークフローを実行
python main.py init --issue-url https://github.com/tielec/infrastructure-as-code/issues/355
python main.py execute --phase requirements --issue 355
# 正常に実行されることを確認
```

---

## 7. スコープ外

### 明確にスコープ外とする事項

**OUT-1: `--no-pr`オプション**
- PR作成をスキップするCLIオプション
- 理由: Phase 4（実装）では基本機能の実装を優先
- 将来実装: Issue #355完了後の拡張機能として検討

**OUT-2: PR本文の動的更新**
- 各フェーズ完了時にPR本文のチェックリストを自動更新する機能
- 理由: Phase 4（実装）では基本機能の実装を優先
- 将来実装: Phase 7（ドキュメント）完了後の拡張機能として検討

**OUT-3: gh CLI依存**
- gh CLIを使用したPR作成
- 理由: Docker環境へのgh CLIインストールが必要（依存関係の増加）
- 代替: PyGithubのPR作成APIを使用（Planning Documentで決定済み）

**OUT-4: PR作成のリトライ機能**
- PR作成失敗時の自動リトライ（exponential backoff）
- 理由: PR作成は冪等性が保証されず、リトライによる重複PR作成のリスクがある
- 代替: 失敗時は警告メッセージを表示し、手動PR作成を案内

**OUT-5: PR作成成功時のSlack通知**
- PR作成成功時にSlackに通知する機能
- 理由: Slack連携はプロジェクト全体の通知戦略として別途検討が必要
- 将来実装: 通知機能を統一的に実装する際に検討

**OUT-6: PR本文テンプレートの外部ファイル化**
- PR本文テンプレートを外部ファイル（`.github/pr_template.md`等）に分離
- 理由: 現時点ではコード内埋め込みで十分
- 将来実装: PR本文のカスタマイズ要求が増えた場合に検討

---

### 将来的な拡張候補

**FUT-1: PR作成時のラベル自動付与**
- PR作成時にラベル（例: `ai-workflow`、`draft`）を自動的に付与
- 利点: PR一覧でAI Workflowによる自動作成PRを識別しやすい
- 実装時期: Issue #355完了後の拡張機能として検討

**FUT-2: PR作成時のアサイン機能**
- PR作成時にIssueのアサイニーを自動的にPRにもアサイン
- 利点: レビュー担当者が明確になる
- 実装時期: Issue #355完了後の拡張機能として検討

**FUT-3: PR作成成功時のmetadata.json自動commit**
- PR作成後、`pr_url`を含むmetadata.jsonを自動的にcommit & push
- 利点: PR URLがワークフローの記録として残る
- 実装時期: FR-5（PR URL記録機能）実装後に検討

**FUT-4: 複数ブランチ戦略のサポート**
- mainブランチ以外（develop、staging等）をベースブランチとして指定可能
- 実装例: `python main.py init --issue-url <URL> --base-branch develop`
- 実装時期: プロジェクトでブランチ戦略が確立した後に検討

---

## 8. 補足情報

### 関連Issue
- **Issue #320**: AIワークフロー全フェーズ一括実行機能
- **Issue #352**: AI Workflow認証アーキテクチャの混乱によりHaikuモデルが使用され失敗

### 参考ドキュメント
- **CLAUDE.md**: プロジェクト全体方針とコーディングガイドライン
- **ARCHITECTURE.md**: Platform Engineeringのアーキテクチャ設計思想
- **CONTRIBUTION.md**: 開発ガイドライン
- **Planning Document**: .ai-workflow/issue-355/00_planning/output/planning.md

### 既存実装の参照箇所
- **main.py:339-405**: initコマンドの既存実装
- **core/git_manager.py:50-169**: commit_phase_output()メソッド
- **core/git_manager.py:171-284**: push_to_remote()メソッド
- **core/github_client.py**: GitHub API統合（PR作成機能は未実装）

---

## 9. 品質ゲート確認

このセクションでは、Phase 1（要件定義）の品質ゲートを満たしているか確認します。

### ✅ 機能要件が明確に記載されている
- **確認**: FR-1からFR-6まで、各機能要件が明確に記載されている
- **詳細仕様**: コミットメッセージ形式、PR本文テンプレート、エラーメッセージ等が具体的に記述されている
- **優先度**: 各要件に優先度（高/中/低）が付与されている

### ✅ 受け入れ基準が定義されている
- **確認**: AC-1からAC-7まで、Given-When-Then形式で受け入れ基準が定義されている
- **検証方法**: 各受け入れ基準に対して、具体的な検証方法（コマンド例）が記載されている
- **テスト可能性**: すべての受け入れ基準がテスト可能な形で記述されている

### ✅ スコープが明確である
- **確認**: スコープ外（OUT-1からOUT-6）が明確に定義されている
- **将来実装**: 拡張候補（FUT-1からFUT-4）が明確に分離されている
- **実装範囲**: Phase 4（実装）で実装する機能が明確に識別可能

### ✅ 論理的な矛盾がない
- **確認**: 機能要件、非機能要件、制約事項、前提条件が相互に矛盾していない
- **整合性**:
  - FR-3（PR作成）とCT-3（PyGithub制約）が整合している
  - NFR-1（パフォーマンス）とAC-6（パフォーマンス受け入れ基準）が対応している
  - DEP-3（環境変数）とNFR-2（セキュリティ要件）が整合している

---

**要件定義書作成日**: 2025-10-12
**作成者**: AI Workflow（Claude Code Pro Max - Sonnet 4.5）
**レビュー待ち**: クリティカルシンキングレビュー
