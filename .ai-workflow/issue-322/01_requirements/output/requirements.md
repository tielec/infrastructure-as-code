# 要件定義書 - Issue #322

**プロジェクト**: AIワークフローのGitコミット時のユーザー名とメールアドレスを設定可能に
**Issue番号**: #322
**作成日**: 2025-10-12
**バージョン**: 1.0.0

---

## 0. Planning Documentの確認

### 開発計画の全体像

Planning Phase (Phase 0) の成果物を確認しました。以下の開発戦略を踏まえて要件定義を実施します：

- **複雑度**: 簡単
- **見積もり工数**: 3時間
- **実装戦略**: EXTEND（既存コードの拡張）
- **テスト戦略**: UNIT_ONLY（ユニットテストのみ）
- **テストコード戦略**: EXTEND_TEST（既存テストファイルに追加）
- **リスク評価**: 低

**主要な変更箇所** (Planning Documentより引用):
1. `scripts/ai-workflow/core/git_manager.py` - `_ensure_git_config()`メソッド拡張
2. `jenkins/jobs/dsl/ai-workflow/ai_workflow_orchestrator.groovy` - パラメータ追加
3. `jenkins/jobs/pipeline/ai-workflow/ai-workflow-orchestrator/Jenkinsfile` - environment設定追加
4. `scripts/ai-workflow/main.py` - CLIオプション追加（オプション）

**実装上の重要な制約**:
- 後方互換性の保証（環境変数未設定時は従来通り動作）
- グローバルGit設定は変更しない（ローカルリポジトリのみ）
- 既存の `_ensure_git_config()` メソッドが既に存在するため、拡張のみで対応

---

## 1. 概要

### 背景

AIワークフローシステムは、GitHub IssueからPR作成まで自動的に開発プロセスを実行します。現在、Gitコミット時のユーザー名とメールアドレスはシステムのデフォルト設定またはグローバル設定が使用されていますが、CI/CD環境では明示的にコミット者情報を指定したいケースがあります。

**現在の実装状況**:
- `git_manager.py` の `_ensure_git_config()` メソッドが環境変数 `GIT_AUTHOR_NAME` と `GIT_AUTHOR_EMAIL` から設定を読み取る実装が既に存在
- Jenkinsパラメータでの設定機能はまだ実装されていない

### 目的

環境変数やJenkinsパラメータを通じて、AIワークフローのGitコミット時のユーザー名とメールアドレスを柔軟に設定できるようにする。

### ビジネス価値

- **運用の柔軟性向上**: プロジェクトやチームごとに異なるコミット者情報を設定可能
- **トレーサビリティ向上**: AI Botによるコミットを明確に識別できる（例: `AI Workflow Bot <ai-workflow@example.com>`）
- **コンプライアンス対応**: 組織のGitコミットポリシーに準拠したコミット者情報を設定

### 技術的価値

- **設定の一元管理**: Jenkinsパラメータで環境変数を集約管理
- **デバッグ容易性**: ログ出力により使用中のGit設定を確認可能
- **後方互換性**: 既存のワークフローに影響を与えない

---

## 2. 機能要件

### FR-001: 環境変数でのGit設定【高】

**説明**: 環境変数を通じてGitコミット時のユーザー名とメールアドレスを設定できる。

**環境変数仕様**:
- `GIT_COMMIT_USER_NAME`: コミット時のユーザー名
- `GIT_COMMIT_USER_EMAIL`: コミット時のメールアドレス

**既存実装との整合性**:
現在、`_ensure_git_config()` は以下の環境変数を使用しています：
- `GIT_AUTHOR_NAME` (既存)
- `GIT_AUTHOR_EMAIL` (既存)

Issue #322で提案されている新しい環境変数との統合方法：
- **優先順位**: `GIT_COMMIT_USER_NAME` → `GIT_AUTHOR_NAME` → デフォルト値
- **優先順位**: `GIT_COMMIT_USER_EMAIL` → `GIT_AUTHOR_EMAIL` → デフォルト値

**デフォルト値**:
- ユーザー名: `AI Workflow` (既存実装)
- メールアドレス: `ai-workflow@tielec.local` (既存実装)

**動作**:
- 環境変数が設定されている場合: その値を使用
- 環境変数が未設定の場合: デフォルト値を使用

**受け入れ基準**:
- Given: 環境変数 `GIT_COMMIT_USER_NAME` と `GIT_COMMIT_USER_EMAIL` が設定されている
- When: `python main.py execute --phase requirements --issue 123` を実行
- Then: コミットのAuthorが環境変数の値になる

---

### FR-002: Jenkinsパラメータでの設定【高】

**説明**: Jenkinsジョブのパラメータを通じてGitコミット者情報を指定できる。

**追加パラメータ**:
1. **`GIT_COMMIT_USER_NAME`** (stringParam)
   - デフォルト値: `AI Workflow Bot`
   - 説明: Gitコミット時のユーザー名

2. **`GIT_COMMIT_USER_EMAIL`** (stringParam)
   - デフォルト値: `ai-workflow@example.com`
   - 説明: Gitコミット時のメールアドレス

**実装箇所**:
1. Job DSL (`jenkins/jobs/dsl/ai-workflow/ai_workflow_orchestrator.groovy`)
   - `parameters` ブロックに2つのパラメータを追加

2. Jenkinsfile (`jenkins/jobs/pipeline/ai-workflow/ai-workflow-orchestrator/Jenkinsfile`)
   - `environment` ブロックで環境変数に設定
   - `GIT_COMMIT_USER_NAME = "${params.GIT_COMMIT_USER_NAME}"`
   - `GIT_COMMIT_USER_EMAIL = "${params.GIT_COMMIT_USER_EMAIL}"`

**受け入れ基準**:
- Given: Jenkinsジョブで `GIT_COMMIT_USER_NAME="Custom User"`, `GIT_COMMIT_USER_EMAIL="custom@example.com"` を指定
- When: `ai_workflow_orchestrator` ジョブを実行
- Then: コミットのAuthorが `Custom User <custom@example.com>` になる

---

### FR-003: GitManagerでの環境変数読み取り【高】

**説明**: `GitManager._ensure_git_config()` メソッドで環境変数を読み取り、Gitローカル設定を行う。

**実装詳細**:
1. 環境変数の優先順位を実装
   - `GIT_COMMIT_USER_NAME` > `GIT_AUTHOR_NAME` > デフォルト値
   - `GIT_COMMIT_USER_EMAIL` > `GIT_AUTHOR_EMAIL` > デフォルト値

2. Git設定の範囲
   - **ローカルリポジトリのみ**: `git config --local user.name`, `git config --local user.email`
   - **グローバル設定は変更しない**: `git config --global` は使用禁止

3. ログ出力
   - 設定された値を `[INFO]` レベルで出力
   - 例: `[INFO] Git設定完了: user.name=AI Workflow Bot, user.email=ai-workflow@example.com`

**受け入れ基準**:
- Given: 環境変数 `GIT_COMMIT_USER_NAME="Test User"` が設定されている
- When: `commit_phase_output()` が呼ばれる
- Then: `git config user.name` の値が `Test User` になる（ローカルリポジトリのみ）
- And: グローバル設定 (`git config --global user.name`) は変更されない

---

### FR-004: Python CLIでの設定（オプション）【中】

**説明**: `main.py execute` コマンドに `--git-user` と `--git-email` オプションを追加し、コマンドライン引数からもGit設定を行えるようにする。

**CLIオプション仕様**:
- `--git-user <username>`: Gitコミット時のユーザー名
- `--git-email <email>`: Gitコミット時のメールアドレス

**優先順位**:
1. CLIオプション（`--git-user`, `--git-email`）
2. 環境変数（`GIT_COMMIT_USER_NAME`, `GIT_COMMIT_USER_EMAIL`）
3. 環境変数（`GIT_AUTHOR_NAME`, `GIT_AUTHOR_EMAIL`）- 既存実装との互換性
4. デフォルト値（`AI Workflow`, `ai-workflow@tielec.local`）

**実装方法**:
```python
@click.command()
@click.option('--phase', required=True, help='Phase name')
@click.option('--issue', required=True, type=int, help='GitHub Issue number')
@click.option('--git-user', help='Git commit user name')
@click.option('--git-email', help='Git commit user email')
def execute(phase: str, issue: int, git_user: str = None, git_email: str = None):
    # CLIオプションが指定されている場合、環境変数に設定（最優先）
    if git_user:
        os.environ['GIT_COMMIT_USER_NAME'] = git_user
    if git_email:
        os.environ['GIT_COMMIT_USER_EMAIL'] = git_email

    # 既存の処理...
```

**受け入れ基準**:
- Given: コマンドラインオプション `--git-user "CLI User"` が指定されている
- And: 環境変数 `GIT_COMMIT_USER_NAME="Env User"` も設定されている
- When: `python main.py execute --phase requirements --issue 123 --git-user "CLI User"` を実行
- Then: コミットのAuthorが `CLI User` になる（CLIオプションが優先）

---

## 3. 非機能要件

### NFR-001: 後方互換性【必須】

**説明**: 環境変数が未設定の場合、既存の動作を維持する。

**検証方法**:
- 環境変数を設定せずにワークフローを実行
- デフォルト値（`AI Workflow <ai-workflow@tielec.local>`）が使用されることを確認

**受け入れ基準**:
- Given: すべてのGit関連環境変数が未設定
- When: ワークフローを実行
- Then: デフォルト値でコミットが作成される
- And: 既存のワークフローに影響がない

---

### NFR-002: セキュリティ【必須】

**説明**: 入力値のバリデーションを実施し、不正な値を防ぐ。

**バリデーションルール**:

1. **メールアドレス**:
   - 基本的な形式チェック（`@` の存在確認）
   - RFC 5322準拠の厳密なチェックは不要
   - 不正な形式の場合: 警告ログを出力するが処理は継続
   - 例: `user@example.com` (OK), `invalid-email` (NG)

2. **ユーザー名**:
   - 長さ制限: 1文字以上100文字以下
   - 空文字列は許可しない
   - 不正な長さの場合: デフォルト値にフォールバック

**実装方針**:
- バリデーションエラーは警告レベルでログ出力
- 致命的エラーではないため、処理は継続
- 不正な値の場合はデフォルト値を使用

**受け入れ基準**:
- Given: 環境変数 `GIT_COMMIT_USER_EMAIL="invalid-email"` （`@` なし）
- When: ワークフローを実行
- Then: 警告ログ `[WARN] Invalid email format: invalid-email` が出力される
- And: デフォルトメールアドレスが使用される

---

### NFR-003: ログ出力【必須】

**説明**: 使用されているGit設定をログに出力し、デバッグを容易にする。

**ログ出力内容**:
1. Git設定完了メッセージ
   - `[INFO] Git設定完了: user.name=AI Workflow Bot, user.email=ai-workflow@example.com`

2. 環境変数の読み取り状況（DEBUGレベル）
   - `[DEBUG] GIT_COMMIT_USER_NAME: AI Workflow Bot`
   - `[DEBUG] GIT_COMMIT_USER_EMAIL: ai-workflow@example.com`

3. バリデーションエラー（WARNレベル）
   - `[WARN] Invalid email format: invalid-email, using default`
   - `[WARN] User name too long (150 chars), using default`

**受け入れ基準**:
- Given: 環境変数 `GIT_COMMIT_USER_NAME="Test User"` が設定されている
- When: ワークフローを実行
- Then: コンソールログに `[INFO] Git設定完了: user.name=Test User, user.email=...` が出力される

---

### NFR-004: パフォーマンス【推奨】

**説明**: Git設定処理がワークフロー全体のパフォーマンスに影響を与えないようにする。

**要求事項**:
- Git設定処理時間: 100ms以内
- 環境変数読み取り処理: 10ms以内

**受け入れ基準**:
- Given: 通常のワークフロー実行
- When: `_ensure_git_config()` が呼ばれる
- Then: 処理時間が100ms以内に完了する

---

## 4. 制約事項

### 技術的制約

1. **Git設定スコープ**:
   - ローカルリポジトリのみ設定可能（`git config --local`）
   - グローバル設定（`git config --global`）の変更は禁止
   - システム設定（`git config --system`）の変更は禁止

2. **環境変数の命名規則**:
   - 既存実装との互換性を保つため、新旧両方の環境変数をサポート
   - 優先順位: `GIT_COMMIT_USER_NAME` > `GIT_AUTHOR_NAME`

3. **Jenkinsパラメータ定義のルール** (CLAUDE.md, jenkins/CONTRIBUTION.md):
   - パラメータ定義はJob DSLファイルで実施（必須）
   - Jenkinsfileでのパラメータ定義は禁止

4. **既存実装の活用**:
   - `_ensure_git_config()` メソッドは既に実装済み
   - 拡張のみで対応（メソッドの全面的な書き換えは不要）

### リソース制約

1. **開発時間**: 3時間（Planning Documentより）
2. **テスト時間**: ユニットテストのみ（0.5時間）
3. **レビュー時間**: クリティカルシンキングレビュー含む

### ポリシー制約

1. **コーディング規約** (CLAUDE.md):
   - コメントは日本語で記述
   - ドキュメントは日本語で記述
   - ログメッセージは英語または日本語

2. **セキュリティポリシー**:
   - クレデンシャルのハードコーディング禁止
   - ログに機密情報を出力しない（メールアドレスは出力可）

---

## 5. 前提条件

### システム環境

1. **Python実行環境**:
   - Python 3.8以上
   - GitPython ライブラリ（既存依存）

2. **Git環境**:
   - Git 2.0以上
   - リポジトリがGitで初期化されている

3. **Jenkins環境**:
   - Jenkins 2.426.1以上
   - Job DSL Plugin（既存プラグイン）
   - Pipeline Plugin（既存プラグイン）

### 依存コンポーネント

1. **GitManager** (`scripts/ai-workflow/core/git_manager.py`):
   - 既存の `_ensure_git_config()` メソッド
   - `commit_phase_output()` メソッド

2. **MetadataManager** (`scripts/ai-workflow/core/metadata_manager.py`):
   - Issue番号の取得に使用

3. **Jenkinsジョブ**:
   - `AI_Workflow/ai_workflow_orchestrator` ジョブ
   - Job DSL定義ファイル
   - Jenkinsfileパイプライン

### 外部システム連携

1. **GitHub**:
   - Git push操作（認証情報: `GITHUB_TOKEN`）

2. **Jenkins Credentials**:
   - `github-token`: GitHub API用トークン（既存）

---

## 6. 受け入れ基準

### AC-001: 環境変数による設定

**Given**: 環境変数 `GIT_COMMIT_USER_NAME="Test User"` と `GIT_COMMIT_USER_EMAIL="test@example.com"` が設定されている
**When**: `python main.py execute --phase requirements --issue 123` を実行
**Then**:
- コミットのAuthorが `Test User <test@example.com>` になる
- ログに `[INFO] Git設定完了: user.name=Test User, user.email=test@example.com` が出力される
- グローバル設定は変更されない

---

### AC-002: Jenkinsパラメータによる設定

**Given**: Jenkinsジョブで以下のパラメータを指定
- `GIT_COMMIT_USER_NAME="Jenkins Bot"`
- `GIT_COMMIT_USER_EMAIL="jenkins@example.com"`

**When**: `ai_workflow_orchestrator` ジョブを実行
**Then**:
- すべてのPhaseのコミットで `Jenkins Bot <jenkins@example.com>` がAuthorとして使用される
- Jenkinsコンソールログに設定値が出力される

---

### AC-003: 環境変数未設定時のデフォルト動作

**Given**: すべてのGit関連環境変数が未設定
**When**: ワークフローを実行
**Then**:
- コミットのAuthorが `AI Workflow <ai-workflow@tielec.local>` になる（既存のデフォルト値）
- 既存のワークフローに影響がない

---

### AC-004: 環境変数の優先順位

**Given**:
- 環境変数 `GIT_COMMIT_USER_NAME="Primary Name"` が設定されている
- 環境変数 `GIT_AUTHOR_NAME="Secondary Name"` も設定されている

**When**: ワークフローを実行
**Then**:
- `Primary Name` が使用される（`GIT_COMMIT_USER_NAME` が優先）

---

### AC-005: バリデーション（メールアドレス）

**Given**: 環境変数 `GIT_COMMIT_USER_EMAIL="invalid-email"` （`@` なし）
**When**: ワークフローを実行
**Then**:
- 警告ログ `[WARN] Invalid email format: invalid-email` が出力される
- デフォルトメールアドレス `ai-workflow@tielec.local` が使用される
- 処理は継続される（エラーで停止しない）

---

### AC-006: バリデーション（ユーザー名長さ）

**Given**: 環境変数 `GIT_COMMIT_USER_NAME` に101文字以上の文字列を設定
**When**: ワークフローを実行
**Then**:
- 警告ログ `[WARN] User name too long (xxx chars), using default` が出力される
- デフォルトユーザー名 `AI Workflow` が使用される

---

### AC-007: CLIオプションの優先順位（オプション機能）

**Given**:
- CLIオプション `--git-user "CLI User"` を指定
- 環境変数 `GIT_COMMIT_USER_NAME="Env User"` も設定

**When**: `python main.py execute --phase requirements --issue 123 --git-user "CLI User"` を実行
**Then**:
- `CLI User` が使用される（CLIオプションが最優先）

---

### AC-008: グローバル設定の非変更

**Given**: グローバル設定で `git config --global user.name "Global User"` が設定されている
**When**: ワークフローで環境変数 `GIT_COMMIT_USER_NAME="Local User"` を使用
**Then**:
- ワークフロー内のコミットは `Local User` を使用
- グローバル設定 `Global User` は変更されない
- ワークフロー終了後、グローバル設定が保持されている

---

## 7. スコープ外

以下の項目は本Issueのスコープ外とし、将来的な拡張候補とします：

### 将来的な拡張候補

1. **SSMパラメータストアからのGit設定読み込み**:
   - AWS Systems Manager Parameter Storeから設定を取得
   - 環境ごとに異なる設定を一元管理

2. **GitHub App認証との統合**:
   - GitHub App認証を使用したコミット署名
   - Verified badgeの追加

3. **コミットメッセージテンプレートの環境変数化**:
   - `GIT_COMMIT_MESSAGE_TEMPLATE` 環境変数
   - プロジェクト固有のコミットメッセージフォーマット

4. **組織・チーム単位でのデフォルト設定管理**:
   - 組織全体のデフォルトコミット者情報
   - チーム別の設定プロファイル

5. **Git設定の永続化**:
   - ワークフローごとに設定を保存
   - 履歴確認機能

### 明確にスコープ外とする事項

1. **グローバル設定の変更**:
   - `git config --global` の操作は禁止

2. **複数ユーザーの設定管理**:
   - ユーザーごとの設定プロファイルは不要

3. **Git署名機能**:
   - GPG署名機能の実装は対象外

4. **コミット履歴の書き換え**:
   - 既存コミットのAuthor変更は不要

---

## 8. 補足情報

### 既存実装との互換性

現在の `_ensure_git_config()` 実装では以下の環境変数を使用しています：

```python
# 既存実装 (git_manager.py:562-566)
if not user_name:
    user_name = os.environ.get('GIT_AUTHOR_NAME', 'AI Workflow')

if not user_email:
    user_email = os.environ.get('GIT_AUTHOR_EMAIL', 'ai-workflow@tielec.local')
```

本Issueでは、以下の環境変数を**追加**します（既存環境変数も引き続きサポート）：

```python
# 新規追加（優先度が高い）
user_name = os.environ.get('GIT_COMMIT_USER_NAME') or os.environ.get('GIT_AUTHOR_NAME', 'AI Workflow')
user_email = os.environ.get('GIT_COMMIT_USER_EMAIL') or os.environ.get('GIT_AUTHOR_EMAIL', 'ai-workflow@tielec.local')
```

### 参考資料

- **Planning Document**: `.ai-workflow/issue-322/00_planning/output/planning.md`
- **GitManager実装**: `scripts/ai-workflow/core/git_manager.py`
- **Jenkinsfile**: `jenkins/jobs/pipeline/ai-workflow/ai-workflow-orchestrator/Jenkinsfile`
- **Job DSL**: `jenkins/jobs/dsl/ai-workflow/ai_workflow_orchestrator.groovy`
- **プロジェクトガイドライン**: `CLAUDE.md`, `CONTRIBUTION.md`

### 用語集

- **AI Workflow**: Claude AIを使用した自動開発ワークフローシステム
- **Phase**: 開発プロセスの各段階（要件定義、設計、実装など）
- **GitManager**: Git操作を管理するPythonクラス
- **Job DSL**: JenkinsのJob定義をGroovyコードで記述する仕組み
- **Jenkinsfile**: Declarative Pipeline形式のJenkinsパイプライン定義

---

## 9. レビューチェックリスト（品質ゲート）

このセクションは、クリティカルシンキングレビュー時に使用されます。

### Phase 1: 要件定義の品質ゲート

- [ ] **機能要件が明確に記載されている**
  - FR-001からFR-004まで、具体的かつ検証可能な形で記述
  - 各要件に優先度（高/中/低）を付与
  - 受け入れ基準をGiven-When-Then形式で記述

- [ ] **受け入れ基準が定義されている**
  - AC-001からAC-008まで、8つの受け入れ基準を定義
  - すべてGiven-When-Then形式で記述
  - テスト可能な形で明確化

- [ ] **スコープが明確である**
  - スコープ内: FR-001〜FR-004の機能要件
  - スコープ外: 将来的な拡張候補を明記
  - 明確に除外する事項を列挙

- [ ] **論理的な矛盾がない**
  - Planning Documentとの整合性確認
  - 既存実装との互換性確認
  - 環境変数の優先順位に矛盾なし

---

**要件定義書の完成度**: 100%
**次フェーズ**: Phase 2 - 詳細設計

---

*本要件定義書はAI Workflowシステムにより自動生成されました。*
