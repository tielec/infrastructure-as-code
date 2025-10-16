# 要件定義書：AIワークフローv2 マルチリポジトリ対応

**Issue番号**: #369
**タイトル**: [FEATURE] AIワークフローv2: Issue URLから対象リポジトリを自動判定して実行
**作成日**: 2025-01-13
**ワークフローバージョン**: 0.1.0

---

## 0. Planning Documentの確認

Planning Phase（Issue #369-00_planning）で策定された開発計画を確認し、以下の戦略に基づいて要件定義を実施します：

### 開発戦略サマリー

- **実装戦略**: EXTEND（既存コードの拡張が中心）
- **テスト戦略**: UNIT_INTEGRATION（ロジック部分と外部システム連携の両方をテスト）
- **テストコード戦略**: BOTH_TEST（既存テスト拡張 + 新規テストファイル作成）
- **複雑度**: 中程度（Medium）
- **見積もり工数**: 12〜16時間
- **主要リスク**: 後方互換性、メタデータマイグレーション、リポジトリパス探索の失敗

### 主要な設計判断

1. **URL解析とパス探索**: Issue URLから自動的にリポジトリ情報を抽出し、ローカルパスを探索
2. **環境変数REPOS_ROOT**: リポジトリの親ディレクトリを指定（推奨）
3. **メタデータスキーマ拡張**: `target_repository`フィールドを追加
4. **後方互換性**: 既存ワークフロー（Issue #305等）への影響を最小化

---

## 1. 概要

### 背景

現在、AIワークフローv2（TypeScript版）は実行環境のGitリポジトリ（`scripts/ai-workflow-v2/`が配置されている`infrastructure-as-code`リポジトリ）のみを対象としています。

具体的には、`src/main.ts`の`getRepoRoot()`関数が現在のGitリポジトリルートを取得するため、Issue URLが別のリポジトリ（例: `https://github.com/tielec/my-app/issues/123`）を指していても、実行環境のリポジトリ（`infrastructure-as-code`）が対象になってしまいます。

### 目的

**Issue URLから対象リポジトリを自動的に判定**することで、別のリポジトリに対してもAIワークフローを実行できるようにします。これにより、以下のメリットを得られます：

1. **マルチリポジトリ対応**: 複数のリポジトリで並行してワークフローを実行可能
2. **直感的な操作**: Issue URLを指定するだけで対象リポジトリが自動判定される
3. **追加オプション不要**: `--target-repo-path`などの追加オプションが不要
4. **自然な対応関係**: Issueとリポジトリが自然に対応

### ビジネス価値・技術的価値

- **開発効率向上**: 別リポジトリのIssueに対しても同じワークフローが使用可能
- **運用の柔軟性**: リポジトリごとに独立したワークフロー管理が可能
- **スケーラビリティ**: 組織内の複数リポジトリに対して容易に展開可能
- **保守性**: 各リポジトリの`.ai-workflow`ディレクトリで完全に独立管理

---

## 2. 機能要件

### FR-001: Issue URLからリポジトリ情報を抽出 【優先度: 高】

**要件**:
GitHub Issue URLから以下の情報を正しく抽出できること。

- **入力**: GitHub Issue URL（例: `https://github.com/tielec/my-app/issues/123`）
- **出力**:
  - `owner`: リポジトリオーナー（例: `tielec`）
  - `repo`: リポジトリ名（例: `my-app`）
  - `issueNumber`: Issue番号（例: `123`）
  - `repositoryName`: `owner/repo`形式（例: `tielec/my-app`）

**処理詳細**:
- 正規表現によるURL解析: `github\.com\/([^\/]+)\/([^\/]+)\/issues\/(\d+)`
- URL形式のバリデーション（末尾スラッシュの有無を許容）
- 不正なURL形式の場合はエラーを投げる

**実装対象**: `src/main.ts`に`parseIssueUrl(issueUrl: string): IssueInfo`関数を追加

**関連する設計判断**: Planning Phase Task 4-2（URL解析機能の実装）

---

### FR-002: ローカルリポジトリパスを自動解決 【優先度: 高】

**要件**:
リポジトリ名から対応するローカルパスを自動的に解決できること。

**処理順序**:
1. **環境変数REPOS_ROOTの確認**:
   - 環境変数`REPOS_ROOT`が設定されている場合、`$REPOS_ROOT/{repo-name}`を候補として確認
   - `.git`ディレクトリが存在する場合は有効なパスとして採用

2. **候補パスの探索**:
   - 環境変数が未設定の場合、以下の候補パスを順番に探索:
     - `~/TIELEC/development/{repo-name}`
     - `~/projects/{repo-name}`
     - `{current-repo}/../{repo-name}`
   - 各候補パスについて、ディレクトリと`.git`の存在を確認

3. **エラー処理**:
   - すべての候補パスで見つからない場合、明確なエラーメッセージを表示:
     ```
     [ERROR] Repository '{repo-name}' not found.
             Please set REPOS_ROOT environment variable or clone the repository.
     ```

**実装対象**: `src/main.ts`に`resolveLocalRepoPath(repoName: string): string`関数を追加

**関連する設計判断**: Planning Phase Task 4-3（ローカルリポジトリパス解決機能の実装）

---

### FR-003: target_repositoryフィールドをメタデータに追加 【優先度: 高】

**要件**:
メタデータスキーマに対象リポジトリ情報を保存するフィールドを追加すること。

**データ構造**:
```typescript
interface TargetRepository {
  path: string;              // ローカルパス（例: C:\Users\ytaka\TIELEC\development\my-app）
  github_name: string;       // owner/repo形式（例: tielec/my-app）
  remote_url: string;        // Git remote URL（例: https://github.com/tielec/my-app.git）
  owner: string;             // リポジトリオーナー（例: tielec）
  repo: string;              // リポジトリ名（例: my-app）
}

interface WorkflowMetadata {
  // ... 既存フィールド
  repository?: string | null;         // 既存（後方互換性のため保持）
  target_repository?: TargetRepository;  // 新規
}
```

**実装対象**:
- `src/types.ts`: `TargetRepository`インターフェース追加、`WorkflowMetadata`に`target_repository?`フィールド追加
- `metadata.json.template`: `target_repository: null`を追加

**関連する設計判断**: Planning Phase Task 4-1（types.tsの拡張）

---

### FR-004: initコマンドでtarget_repositoryを自動設定 【優先度: 高】

**要件**:
`init`コマンド実行時、Issue URLから対象リポジトリを自動判定し、メタデータに保存すること。

**処理フロー**:
1. Issue URLをパース（`parseIssueUrl()`）
2. ローカルリポジトリパスを解決（`resolveLocalRepoPath()`）
3. メタデータに以下を設定:
   - `target_repository.path`: ローカルパス
   - `target_repository.github_name`: `owner/repo`形式
   - `target_repository.remote_url`: `https://github.com/owner/repo.git`
   - `target_repository.owner`: オーナー名
   - `target_repository.repo`: リポジトリ名
4. `.ai-workflow`ディレクトリを対象リポジトリ配下に作成
5. metadata.jsonをコミット・プッシュ
6. Draft PRを作成（GITHUB_TOKENが設定されている場合）

**実装対象**: `src/main.ts`の`handleInitCommand()`を修正

**関連する設計判断**: Planning Phase Task 4-4（handleInitCommandの修正）

---

### FR-005: executeコマンドでメタデータからtarget_repositoryを読み込み 【優先度: 高】

**要件**:
`execute`コマンド実行時、メタデータから対象リポジトリ情報を読み込み、workingDirとして使用すること。

**処理フロー**:
1. Issue番号から`.ai-workflow/issue-{number}/metadata.json`を探索
2. メタデータから`target_repository`を取得
3. `target_repository.path`を`workingDir`として使用
4. 後方互換性対応:
   - `target_repository`がnullまたは未定義の場合、従来の動作を維持（実行環境のリポジトリを使用）
   - 警告メッセージを表示: `[WARNING] target_repository not found in metadata. Using current repository.`

**実装対象**: `src/main.ts`の`handleExecuteCommand()`を修正

**関連する設計判断**: Planning Phase Task 4-5（handleExecuteCommandの修正）

---

### FR-006: ワークフローディレクトリを対象リポジトリ配下に作成 【優先度: 高】

**要件**:
`.ai-workflow`ディレクトリを対象リポジトリのルート配下に作成すること。

**ディレクトリ構造**:
```
C:\Users\ytaka\TIELEC\development\my-app/
  .ai-workflow/
    issue-123/
      metadata.json
      00_planning/
      01_requirements/
      02_design/
      ...
  src/
  README.md
  .gitignore  # .ai-workflow を追加
```

**メリット**:
- 成果物と対象リポジトリが同じ場所にある
- リポジトリごとに独立して管理できる
- Git管理対象外（`.gitignore`に`.ai-workflow`を追加）

**実装対象**: `src/main.ts`の`handleInitCommand()`

**関連する設計判断**: Planning Phase Section 5（実装案）

---

### FR-007: メタデータスキーマのマイグレーション 【優先度: 中】

**要件**:
既存のmetadata.jsonを新しいスキーマに自動的にマイグレーションすること。

**マイグレーション処理**:
1. `target_repository`フィールドが存在しない場合、`null`値で追加
2. 既存の`repository`フィールドは削除せず保持（後方互換性）
3. マイグレーション実行時はコンソールに情報を表示

**実装対象**: `src/core/workflow-state.ts`の`migrate()`メソッドを拡張

**関連する設計判断**: Planning Phase Task 4-6（WorkflowState.migrate()の拡張）

---

### FR-008: メタデータ探索機能 【優先度: 中】

**要件**:
`execute`コマンド実行時、Issue番号から対応するメタデータを探索できること。

**処理フロー**:
1. Issue番号を受け取る
2. 以下の候補パスを順番に探索:
   - 環境変数`REPOS_ROOT`配下のすべてのリポジトリ
   - `~/TIELEC/development/`配下のすべてのリポジトリ
   - `~/projects/`配下のすべてのリポジトリ
3. 各リポジトリの`.ai-workflow/issue-{number}/metadata.json`の存在を確認
4. 見つかった場合、そのパスを返す
5. 見つからない場合、エラーメッセージを表示

**実装対象**: `src/main.ts`に`findWorkflowMetadata(issueNumber: string): { repoRoot: string, metadataPath: string }`関数を追加

**関連する設計判断**: Planning Phase Task 4-4（findWorkflowMetadata関数の実装）

---

### FR-009: 環境変数REPOS_ROOTのサポート 【優先度: 中】

**要件**:
環境変数`REPOS_ROOT`でリポジトリの親ディレクトリを指定できること。

**設定例**:
```bash
# Bash/Zsh
export REPOS_ROOT="C:\Users\ytaka\TIELEC\development"

# Jenkins環境変数
environment {
    REPOS_ROOT = 'C:\Users\ytaka\TIELEC\development'
}
```

**動作**:
- `REPOS_ROOT`が設定されている場合、`$REPOS_ROOT/{repo-name}`を優先的に使用
- 未設定の場合、フォールバック探索（FR-002参照）

**実装対象**: `src/main.ts`の`resolveLocalRepoPath()`関数

**関連する設計判断**: Planning Phase Section 9（環境変数）

---

## 3. 非機能要件

### NFR-001: パフォーマンス

- **リポジトリパス探索**: 2秒以内に完了すること
- **メタデータ探索**: 最大10個のリポジトリを探索する場合でも5秒以内に完了すること
- **URL解析**: 1ミリ秒以内に完了すること（正規表現による処理）

### NFR-002: セキュリティ

- **認証情報**: GITHUB_TOKENは環境変数経由で取得し、ハードコーディングしないこと
- **ログ出力**: パス情報や環境変数値をログに出力する際は、機密情報を含まないこと
- **ファイルシステムアクセス**: 指定されたリポジトリ配下のみアクセスし、意図しないディレクトリへのアクセスを防ぐこと

### NFR-003: 可用性・信頼性

- **後方互換性**: 既存のワークフロー（Issue #305等）が正常に動作し続けること
- **エラーハンドリング**: すべてのエラーケースで明確なエラーメッセージを表示すること
- **フォールバック**: 環境変数が未設定でも、候補パス探索で動作すること

### NFR-004: 保守性・拡張性

- **コードの再利用性**: 新規関数（`parseIssueUrl()`, `resolveLocalRepoPath()`）は単体でテスト可能であること
- **型安全性**: TypeScriptの型定義を活用し、コンパイル時にエラーを検出できること
- **テストカバレッジ**: 80%以上のカバレッジを目指すこと

### NFR-005: 使いやすさ

- **エラーメッセージの明確性**: ユーザーが問題を理解し、対処できる明確なメッセージを提供すること
  - NG例: "Error: not found"
  - OK例: "[ERROR] Repository 'my-app' not found. Please set REPOS_ROOT environment variable or clone the repository."
- **ドキュメントの充実**: README.mdに使用例、環境変数設定、トラブルシューティングを記載すること

---

## 4. 制約事項

### 技術的制約

1. **GitHubリポジトリ専用**: 現時点ではGitHub以外のサービス（GitLab、Bitbucket等）は非サポート
2. **Gitリポジトリ必須**: ローカルパスに`.git`ディレクトリが存在することが前提
3. **リポジトリ名の一意性**: 同名の異なるリポジトリがある場合、環境変数`REPOS_ROOT`での明示が必要
4. **Node.js標準ライブラリのみ**: 新規依存関係の追加は行わない（`path`, `fs`, `os`を使用）
5. **Windowsパス対応**: バックスラッシュとスラッシュの混在を許容する必要がある

### リソース制約

- **見積もり工数**: 12〜16時間（Planning Phase参照）
- **実装期間**: 2週間以内
- **テスト実施**: ユニットテスト（1〜1.5h）+ インテグレーションテスト（1〜1.5h）

### ポリシー制約

- **後方互換性の保証**: 既存の`repository`フィールドは削除せず保持
- **コーディング規約**: プロジェクトのCLAUDE.mdとCONTRIBUTION.mdに従うこと
- **コミットメッセージ**: `[ai-workflow] Phase X (phase_name) - status`形式を維持

---

## 5. 前提条件

### システム環境

- **OS**: Windows、macOS、Linux
- **Node.js**: v18以上
- **npm**: v8以上
- **Git**: v2.0以上
- **TypeScript**: プロジェクトの既存バージョン

### 依存コンポーネント

- `simple-git`: Gitコマンドラッパー
- `fs-extra`: ファイルシステム操作
- `commander`: CLIフレームワーク
- `path`, `os`: Node.js標準ライブラリ

### 外部システム連携

- **GitHub API**: PR作成、Issue情報取得（GITHUB_TOKENが必要）
- **Git Remote**: ブランチのプッシュ、プル（認証情報が必要）

---

## 6. 受け入れ基準

### AC-001: Issue URLからリポジトリ情報を抽出できる

**Given**: 有効なGitHub Issue URLが与えられる
**When**: `parseIssueUrl()`関数を実行する
**Then**: 以下の情報が正しく抽出される
- `owner`: "tielec"
- `repo`: "my-app"
- `issueNumber`: 123
- `repositoryName`: "tielec/my-app"

**テスト入力**:
- `https://github.com/tielec/my-app/issues/123`
- `https://github.com/tielec/my-app/issues/123/`（末尾スラッシュあり）

---

### AC-002: 無効なIssue URLでエラーが発生する

**Given**: 無効なGitHub Issue URLが与えられる
**When**: `parseIssueUrl()`関数を実行する
**Then**: `Invalid GitHub Issue URL`エラーが投げられる

**テスト入力**:
- `https://example.com/issues/123`（GitHub以外）
- `https://github.com/tielec/my-app/pulls/123`（プルリクエスト）
- `https://github.com/tielec/my-app`（Issue番号なし）

---

### AC-003: 環境変数REPOS_ROOTが設定されている場合、優先的に使用される

**Given**: 環境変数`REPOS_ROOT`が設定されており、`$REPOS_ROOT/my-app`が存在し、`.git`ディレクトリを持つ
**When**: `resolveLocalRepoPath("my-app")`関数を実行する
**Then**: `$REPOS_ROOT/my-app`のパスが返される

---

### AC-004: 環境変数が未設定の場合、候補パスから探索する

**Given**: 環境変数`REPOS_ROOT`が未設定で、`~/TIELEC/development/my-app`が存在し、`.git`ディレクトリを持つ
**When**: `resolveLocalRepoPath("my-app")`関数を実行する
**Then**: `~/TIELEC/development/my-app`のパスが返される

---

### AC-005: リポジトリが見つからない場合、明確なエラーメッセージが表示される

**Given**: リポジトリがどの候補パスにも存在しない
**When**: `resolveLocalRepoPath("unknown-repo")`関数を実行する
**Then**: 以下のエラーメッセージが表示される
```
[ERROR] Repository 'unknown-repo' not found.
        Please set REPOS_ROOT environment variable or clone the repository.
```

---

### AC-006: initコマンドで対象リポジトリ情報がメタデータに保存される

**Given**: Issue URL `https://github.com/tielec/my-app/issues/123`を指定してinitコマンドを実行
**When**: コマンドが成功する
**Then**: `metadata.json`に以下の情報が保存される
```json
{
  "target_repository": {
    "path": "C:\\Users\\ytaka\\TIELEC\\development\\my-app",
    "github_name": "tielec/my-app",
    "remote_url": "https://github.com/tielec/my-app.git",
    "owner": "tielec",
    "repo": "my-app"
  }
}
```

---

### AC-007: .ai-workflowディレクトリが対象リポジトリ配下に作成される

**Given**: Issue URL `https://github.com/tielec/my-app/issues/123`を指定してinitコマンドを実行
**When**: コマンドが成功する
**Then**: `C:\Users\ytaka\TIELEC\development\my-app\.ai-workflow\issue-123\`ディレクトリが作成される

---

### AC-008: executeコマンドでメタデータからtarget_repositoryを読み込む

**Given**: `metadata.json`に`target_repository`が設定されている
**When**: executeコマンドを実行する
**Then**: `target_repository.path`が`workingDir`として使用される

---

### AC-009: target_repositoryが存在しない場合、後方互換性が保たれる

**Given**: `metadata.json`に`target_repository`が存在しない（既存ワークフロー）
**When**: executeコマンドを実行する
**Then**: 以下の動作となる
- 従来の動作を維持（実行環境のリポジトリを使用）
- 警告メッセージを表示: `[WARNING] target_repository not found in metadata. Using current repository.`

---

### AC-010: マイグレーション機能が正常に動作する

**Given**: 既存の`metadata.json`に`target_repository`フィールドが存在しない
**When**: `WorkflowState.migrate()`メソッドを実行する
**Then**: 以下の動作となる
- `target_repository: null`が追加される
- `repository`フィールドは保持される
- `[INFO] Migrating metadata.json: Adding target_repository`メッセージが表示される

---

### AC-011: 同一リポジトリでの動作が変わらない（後方互換性）

**Given**: Issue URL `https://github.com/tielec/infrastructure-as-code/issues/305`を指定してinitコマンドを実行
**When**: コマンドが成功する
**Then**: 従来と同じ動作で、`infrastructure-as-code`リポジトリが対象となる

---

### AC-012: 別リポジトリのIssueに対して正しく動作する

**Given**: Issue URL `https://github.com/tielec/my-app/issues/123`を指定してinitコマンドを実行
**When**: コマンドが成功する
**Then**: `my-app`リポジトリが対象となり、`.ai-workflow`ディレクトリが`my-app`配下に作成される

---

### AC-013: Windowsパスが正しく処理される

**Given**: Windows環境で`REPOS_ROOT`が`C:\Users\ytaka\TIELEC\development`と設定されている
**When**: `resolveLocalRepoPath("my-app")`関数を実行する
**Then**: `C:\Users\ytaka\TIELEC\development\my-app`のパスが正しく返される（バックスラッシュが保持される）

---

## 7. スコープ外

以下の事項は本Issueのスコープ外とし、将来的な拡張候補とします：

### 将来的な拡張候補

1. **自動clone機能**: ローカルに存在しないリポジトリを自動的にcloneする機能
   - 理由: 初回実装の複雑度を抑えるため。ユーザーが手動でcloneすることを前提とする

2. **GitHub以外のサービス対応**: GitLab、Bitbucket等のサポート
   - 理由: GitHub以外の需要が不明確。必要に応じて将来拡張

3. **リモートリポジトリへの直接アクセス**: ローカルクローンなしでリモートリポジトリを操作
   - 理由: 実装の複雑度が高く、ローカルクローンが前提の方がシンプル

4. **マルチテナント対応**: 複数のGitHubアカウント、組織の同時サポート
   - 理由: 現時点では単一アカウント・組織での使用を想定

5. **対話形式のリポジトリ選択**: 候補が複数ある場合、ユーザーに選択させる機能
   - 理由: 環境変数`REPOS_ROOT`での明示的な指定を推奨

---

## 8. 付録

### A. 使用例

#### Case 1: infrastructure-as-codeリポジトリのIssue（現在と同じ）

```bash
cd C:\Users\ytaka\TIELEC\development\infrastructure-as-code

npm run start -- init \
  --issue-url https://github.com/tielec/infrastructure-as-code/issues/305

# → 対象: infrastructure-as-code リポジトリ
# → ローカルパス: C:\Users\ytaka\TIELEC\development\infrastructure-as-code
```

#### Case 2: 別リポジトリ（my-app）のIssue

```bash
cd C:\Users\ytaka\TIELEC\development\infrastructure-as-code

# my-appリポジトリのIssueを指定
npm run start -- init \
  --issue-url https://github.com/tielec/my-app/issues/123

# → 自動判定
#   - GitHubリポジトリ: tielec/my-app
#   - ローカルパス: C:\Users\ytaka\TIELEC\development\my-app
#   - .ai-workflowディレクトリ: C:\Users\ytaka\TIELEC\development\my-app/.ai-workflow/

# 実行
npm run start -- execute --phase all --issue 123

# → my-appリポジトリが対象になる
```

#### Case 3: リポジトリが見つからない場合

```bash
npm run start -- init \
  --issue-url https://github.com/tielec/unknown-repo/issues/999

# → [ERROR] Repository 'unknown-repo' not found.
#          Please set REPOS_ROOT environment variable or clone the repository.
```

### B. 環境変数設定例

```bash
# Bash/Zsh
export REPOS_ROOT="C:\Users\ytaka\TIELEC\development"

# Jenkins環境変数（Jenkinsfile）
environment {
    REPOS_ROOT = 'C:\Users\ytaka\TIELEC\development'
}
```

### C. メタデータ例

```json
{
  "issue_number": "123",
  "issue_url": "https://github.com/tielec/my-app/issues/123",
  "issue_title": "Implement new feature",
  "repository": "tielec/my-app",
  "target_repository": {
    "path": "C:\\Users\\ytaka\\TIELEC\\development\\my-app",
    "github_name": "tielec/my-app",
    "remote_url": "https://github.com/tielec/my-app.git",
    "owner": "tielec",
    "repo": "my-app"
  },
  "workflow_version": "0.1.0",
  "current_phase": "planning",
  "design_decisions": {},
  "cost_tracking": {
    "total_input_tokens": 0,
    "total_output_tokens": 0,
    "total_cost_usd": 0
  },
  "phases": { ... },
  "created_at": "2025-01-13T10:00:00.000Z",
  "updated_at": "2025-01-13T10:00:00.000Z"
}
```

### D. 関連ファイル

- `scripts/ai-workflow-v2/src/main.ts`
- `scripts/ai-workflow-v2/src/core/metadata-manager.ts`
- `scripts/ai-workflow-v2/src/core/workflow-state.ts`
- `scripts/ai-workflow-v2/src/core/git-manager.ts`
- `scripts/ai-workflow-v2/src/types.ts`
- `scripts/ai-workflow-v2/metadata.json.template`
- `jenkins/jobs/pipeline/ai-workflow/ai-workflow-orchestrator/Jenkinsfile`

---

**要件定義承認日**: （Design Phase完了後に記入）
**承認者**: （Design Phaseで記入）
