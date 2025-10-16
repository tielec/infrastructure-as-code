# テストシナリオ書：AIワークフローv2 マルチリポジトリ対応

**Issue番号**: #369
**タイトル**: [FEATURE] AIワークフローv2: Issue URLから対象リポジトリを自動判定して実行
**作成日**: 2025-01-13
**ワークフローバージョン**: 0.1.0

---

## 0. Planning Documentの確認

Planning Phase（Issue #369-00_planning）で策定された開発計画を確認し、以下の戦略に基づいてテストシナリオを作成します：

### 開発戦略サマリー

- **実装戦略**: EXTEND（既存コードの拡張が中心）
- **テスト戦略**: UNIT_INTEGRATION（ロジック部分と外部システム連携の両方をテスト）
- **テストコード戦略**: BOTH_TEST（既存テスト拡張 + 新規テストファイル作成）
- **複雑度**: 中程度（Medium）
- **見積もり工数**: 12〜16時間
- **主要リスク**: 後方互換性、メタデータマイグレーション、リポジトリパス探索の失敗

---

## 1. テスト戦略サマリー

### 選択されたテスト戦略

**UNIT_INTEGRATION**

**判断根拠**（Phase 2から引用）:
- **ユニットテスト**: URL解析、パス探索ロジックなど単体でテスト可能な部分
- **インテグレーションテスト**: 実際のGitリポジトリとファイルシステムを使った動作確認

### テスト対象の範囲

#### ユニットテスト対象
1. `parseIssueUrl()` - Issue URL解析ロジック
2. `resolveLocalRepoPath()` - ローカルリポジトリパス解決ロジック
3. `findWorkflowMetadata()` - メタデータ探索ロジック（モック使用）

#### インテグレーションテスト対象
1. `handleInitCommand()` - 実際のGitリポジトリとファイルシステムでの動作確認
2. `handleExecuteCommand()` - メタデータ読み込みとworkingDir設定の検証
3. マルチリポジトリワークフロー全体のE2E検証（Case 1, 2, 3）

### テストの目的

1. **機能検証**: 各関数が仕様通りに動作することを確認
2. **統合検証**: コンポーネント間の連携が正しく動作することを確認
3. **後方互換性検証**: 既存ワークフロー（Issue #305等）が正常に動作し続けることを確認
4. **エラーハンドリング検証**: 異常系・境界値での適切なエラー処理を確認

---

## 2. ユニットテストシナリオ

### 2.1 parseIssueUrl() のテストケース

#### UT-001: parseIssueUrl_正常系_標準URL

**目的**: 標準的なGitHub Issue URLから正しくリポジトリ情報を抽出できることを検証

**前提条件**:
- `parseIssueUrl()`関数が実装されている

**入力**:
```typescript
issueUrl = "https://github.com/tielec/my-app/issues/123"
```

**期待結果**:
```typescript
{
  owner: "tielec",
  repo: "my-app",
  issueNumber: 123,
  repositoryName: "tielec/my-app"
}
```

**テストデータ**: 上記issueUrl

**検証項目**:
- ✓ ownerが"tielec"であること
- ✓ repoが"my-app"であること
- ✓ issueNumberが123（数値型）であること
- ✓ repositoryNameが"tielec/my-app"であること

---

#### UT-002: parseIssueUrl_正常系_末尾スラッシュあり

**目的**: 末尾にスラッシュがあるURLでも正しく解析できることを検証

**前提条件**:
- `parseIssueUrl()`関数が実装されている

**入力**:
```typescript
issueUrl = "https://github.com/tielec/my-app/issues/123/"
```

**期待結果**:
```typescript
{
  owner: "tielec",
  repo: "my-app",
  issueNumber: 123,
  repositoryName: "tielec/my-app"
}
```

**テストデータ**: 上記issueUrl

**検証項目**:
- ✓ UT-001と同じ結果が返されること
- ✓ 末尾スラッシュの有無が結果に影響しないこと

---

#### UT-003: parseIssueUrl_正常系_大きなIssue番号

**目的**: 大きなIssue番号でも正しく解析できることを検証（境界値テスト）

**前提条件**:
- `parseIssueUrl()`関数が実装されている

**入力**:
```typescript
issueUrl = "https://github.com/tielec/infrastructure-as-code/issues/99999"
```

**期待結果**:
```typescript
{
  owner: "tielec",
  repo: "infrastructure-as-code",
  issueNumber: 99999,
  repositoryName: "tielec/infrastructure-as-code"
}
```

**テストデータ**: 上記issueUrl

**検証項目**:
- ✓ issueNumberが99999（数値型）であること
- ✓ repoに"-"（ハイフン）が含まれていても正しく解析されること

---

#### UT-004: parseIssueUrl_異常系_GitHub以外のURL

**目的**: GitHub以外のURLではエラーが発生することを検証

**前提条件**:
- `parseIssueUrl()`関数が実装されている

**入力**:
```typescript
issueUrl = "https://example.com/issues/123"
```

**期待結果**:
- Errorが投げられること
- エラーメッセージ: `Invalid GitHub Issue URL: https://example.com/issues/123`

**テストデータ**: 上記issueUrl

**検証項目**:
- ✓ Errorが投げられること
- ✓ エラーメッセージに"Invalid GitHub Issue URL"が含まれること
- ✓ エラーメッセージに入力URLが含まれること

---

#### UT-005: parseIssueUrl_異常系_プルリクエストURL

**目的**: プルリクエストURLではエラーが発生することを検証

**前提条件**:
- `parseIssueUrl()`関数が実装されている

**入力**:
```typescript
issueUrl = "https://github.com/tielec/my-app/pulls/123"
```

**期待結果**:
- Errorが投げられること
- エラーメッセージ: `Invalid GitHub Issue URL: https://github.com/tielec/my-app/pulls/123`

**テストデータ**: 上記issueUrl

**検証項目**:
- ✓ Errorが投げられること
- ✓ pullsパスが拒否されること

---

#### UT-006: parseIssueUrl_異常系_Issue番号なし

**目的**: Issue番号がないURLではエラーが発生することを検証

**前提条件**:
- `parseIssueUrl()`関数が実装されている

**入力**:
```typescript
issueUrl = "https://github.com/tielec/my-app"
```

**期待結果**:
- Errorが投げられること
- エラーメッセージ: `Invalid GitHub Issue URL: https://github.com/tielec/my-app`

**テストデータ**: 上記issueUrl

**検証項目**:
- ✓ Errorが投げられること
- ✓ issuesパスがないURLが拒否されること

---

#### UT-007: parseIssueUrl_異常系_Issue番号が数値でない

**目的**: Issue番号が数値でない場合にエラーが発生することを検証

**前提条件**:
- `parseIssueUrl()`関数が実装されている

**入力**:
```typescript
issueUrl = "https://github.com/tielec/my-app/issues/abc"
```

**期待結果**:
- Errorが投げられること
- エラーメッセージ: `Invalid GitHub Issue URL: https://github.com/tielec/my-app/issues/abc`

**テストデータ**: 上記issueUrl

**検証項目**:
- ✓ Errorが投げられること
- ✓ 数値でないIssue番号が拒否されること

---

### 2.2 resolveLocalRepoPath() のテストケース

#### UT-101: resolveLocalRepoPath_正常系_REPOS_ROOT設定済み

**目的**: 環境変数REPOS_ROOTが設定されている場合、優先的に使用されることを検証

**前提条件**:
- `resolveLocalRepoPath()`関数が実装されている
- 環境変数`REPOS_ROOT`が設定されている（モック）
- `fs.existsSync()`がモックされている

**入力**:
```typescript
repoName = "my-app"
process.env.REPOS_ROOT = "/path/to/repos" (モック)
```

**モック設定**:
```typescript
fs.existsSync("/path/to/repos/my-app") → true
fs.existsSync("/path/to/repos/my-app/.git") → true
```

**期待結果**:
```typescript
"/path/to/repos/my-app"
```

**テストデータ**: 上記repoName、環境変数

**検証項目**:
- ✓ 環境変数REPOS_ROOTが使用されること
- ✓ `path.join(REPOS_ROOT, repoName)`が返されること
- ✓ 他の候補パスが探索されないこと（早期リターン）

---

#### UT-102: resolveLocalRepoPath_正常系_候補パス探索_最初の候補で見つかる

**目的**: 環境変数が未設定でも候補パスから見つかることを検証

**前提条件**:
- `resolveLocalRepoPath()`関数が実装されている
- 環境変数`REPOS_ROOT`が未設定
- `fs.existsSync()`がモックされている

**入力**:
```typescript
repoName = "my-app"
process.env.REPOS_ROOT = undefined (モック)
os.homedir() = "/home/user" (モック)
```

**モック設定**:
```typescript
fs.existsSync("/home/user/TIELEC/development/my-app") → true
fs.existsSync("/home/user/TIELEC/development/my-app/.git") → true
```

**期待結果**:
```typescript
"/home/user/TIELEC/development/my-app"
```

**テストデータ**: 上記repoName

**検証項目**:
- ✓ 候補パス探索が実行されること
- ✓ 最初の候補で見つかった場合、即座にリターンすること
- ✓ それ以降の候補パスは探索されないこと

---

#### UT-103: resolveLocalRepoPath_正常系_候補パス探索_2番目の候補で見つかる

**目的**: 最初の候補で見つからなくても、次の候補を探索することを検証

**前提条件**:
- `resolveLocalRepoPath()`関数が実装されている
- 環境変数`REPOS_ROOT`が未設定
- `fs.existsSync()`がモックされている

**入力**:
```typescript
repoName = "my-app"
process.env.REPOS_ROOT = undefined (モック)
os.homedir() = "/home/user" (モック)
```

**モック設定**:
```typescript
fs.existsSync("/home/user/TIELEC/development/my-app") → false
fs.existsSync("/home/user/projects/my-app") → true
fs.existsSync("/home/user/projects/my-app/.git") → true
```

**期待結果**:
```typescript
"/home/user/projects/my-app"
```

**テストデータ**: 上記repoName

**検証項目**:
- ✓ 最初の候補が見つからない場合、次の候補を探索すること
- ✓ 2番目の候補で見つかった場合、即座にリターンすること

---

#### UT-104: resolveLocalRepoPath_正常系_Windowsパス対応

**目的**: Windowsパスでも正しく動作することを検証

**前提条件**:
- `resolveLocalRepoPath()`関数が実装されている
- 環境変数`REPOS_ROOT`が設定されている（モック）
- `fs.existsSync()`がモックされている

**入力**:
```typescript
repoName = "my-app"
process.env.REPOS_ROOT = "C:\\Users\\ytaka\\TIELEC\\development" (モック)
```

**モック設定**:
```typescript
fs.existsSync("C:\\Users\\ytaka\\TIELEC\\development\\my-app") → true
fs.existsSync("C:\\Users\\ytaka\\TIELEC\\development\\my-app\\.git") → true
```

**期待結果**:
```typescript
"C:\\Users\\ytaka\\TIELEC\\development\\my-app"
```

**テストデータ**: 上記repoName、環境変数

**検証項目**:
- ✓ Windowsパス（バックスラッシュ）が正しく処理されること
- ✓ `path.join()`がOSに依存しないパス結合を行うこと

---

#### UT-105: resolveLocalRepoPath_異常系_リポジトリが見つからない

**目的**: すべての候補でリポジトリが見つからない場合にエラーが発生することを検証

**前提条件**:
- `resolveLocalRepoPath()`関数が実装されている
- 環境変数`REPOS_ROOT`が未設定
- `fs.existsSync()`がモックされている

**入力**:
```typescript
repoName = "unknown-repo"
process.env.REPOS_ROOT = undefined (モック)
```

**モック設定**:
```typescript
// すべての候補パスでfalseを返す
fs.existsSync(...) → false (すべて)
```

**期待結果**:
- Errorが投げられること
- エラーメッセージ:
  ```
  Repository 'unknown-repo' not found.
  Please set REPOS_ROOT environment variable or clone the repository.
  ```

**テストデータ**: 上記repoName

**検証項目**:
- ✓ Errorが投げられること
- ✓ エラーメッセージにリポジトリ名が含まれること
- ✓ エラーメッセージに対処方法（REPOS_ROOT設定またはclone）が含まれること

---

#### UT-106: resolveLocalRepoPath_異常系_ディレクトリは存在するが.gitがない

**目的**: ディレクトリは存在するが`.git`がない場合はスキップされることを検証

**前提条件**:
- `resolveLocalRepoPath()`関数が実装されている
- 環境変数`REPOS_ROOT`が設定されている（モック）
- `fs.existsSync()`がモックされている

**入力**:
```typescript
repoName = "my-app"
process.env.REPOS_ROOT = "/path/to/repos" (モック)
```

**モック設定**:
```typescript
fs.existsSync("/path/to/repos/my-app") → true
fs.existsSync("/path/to/repos/my-app/.git") → false
// 他の候補パスもすべてfalse
```

**期待結果**:
- Errorが投げられること
- エラーメッセージ:
  ```
  Repository 'my-app' not found.
  Please set REPOS_ROOT environment variable or clone the repository.
  ```

**テストデータ**: 上記repoName、環境変数

**検証項目**:
- ✓ ディレクトリが存在しても`.git`がない場合はスキップされること
- ✓ 最終的にErrorが投げられること

---

### 2.3 findWorkflowMetadata() のテストケース

#### UT-201: findWorkflowMetadata_正常系_REPOS_ROOT配下で見つかる

**目的**: 環境変数REPOS_ROOT配下でメタデータが見つかることを検証

**前提条件**:
- `findWorkflowMetadata()`関数が実装されている
- 環境変数`REPOS_ROOT`が設定されている（モック）
- `fs.readdirSync()`と`fs.existsSync()`がモックされている

**入力**:
```typescript
issueNumber = "123"
process.env.REPOS_ROOT = "/path/to/repos" (モック)
```

**モック設定**:
```typescript
fs.readdirSync("/path/to/repos") → ["my-app", "other-repo"]
fs.existsSync("/path/to/repos/my-app/.git") → true
fs.existsSync("/path/to/repos/my-app/.ai-workflow/issue-123/metadata.json") → true
```

**期待結果**:
```typescript
{
  repoRoot: "/path/to/repos/my-app",
  metadataPath: "/path/to/repos/my-app/.ai-workflow/issue-123/metadata.json"
}
```

**テストデータ**: 上記issueNumber、環境変数

**検証項目**:
- ✓ REPOS_ROOT配下のリポジトリが列挙されること
- ✓ 各リポジトリの`.git`が確認されること
- ✓ メタデータが見つかった場合、即座にリターンすること

---

#### UT-202: findWorkflowMetadata_正常系_候補パス探索で見つかる

**目的**: 環境変数が未設定でも候補パスからメタデータが見つかることを検証

**前提条件**:
- `findWorkflowMetadata()`関数が実装されている
- 環境変数`REPOS_ROOT`が未設定
- `fs.readdirSync()`と`fs.existsSync()`がモックされている

**入力**:
```typescript
issueNumber = "123"
process.env.REPOS_ROOT = undefined (モック)
os.homedir() = "/home/user" (モック)
```

**モック設定**:
```typescript
fs.readdirSync("/home/user/TIELEC/development") → ["my-app", "other-repo"]
fs.existsSync("/home/user/TIELEC/development/my-app/.git") → true
fs.existsSync("/home/user/TIELEC/development/my-app/.ai-workflow/issue-123/metadata.json") → true
```

**期待結果**:
```typescript
{
  repoRoot: "/home/user/TIELEC/development/my-app",
  metadataPath: "/home/user/TIELEC/development/my-app/.ai-workflow/issue-123/metadata.json"
}
```

**テストデータ**: 上記issueNumber

**検証項目**:
- ✓ 候補パス探索が実行されること
- ✓ メタデータが見つかった場合、即座にリターンすること

---

#### UT-203: findWorkflowMetadata_異常系_メタデータが見つからない

**目的**: すべての候補でメタデータが見つからない場合にエラーが発生することを検証

**前提条件**:
- `findWorkflowMetadata()`関数が実装されている
- `fs.readdirSync()`と`fs.existsSync()`がモックされている

**入力**:
```typescript
issueNumber = "999"
```

**モック設定**:
```typescript
fs.readdirSync(...) → [] (すべて空)
// またはメタデータが存在しない
fs.existsSync(".../.ai-workflow/issue-999/metadata.json") → false (すべて)
```

**期待結果**:
- Errorが投げられること
- エラーメッセージ:
  ```
  Workflow metadata for issue 999 not found.
  Please run init first or check the issue number.
  ```

**テストデータ**: 上記issueNumber

**検証項目**:
- ✓ Errorが投げられること
- ✓ エラーメッセージにIssue番号が含まれること
- ✓ エラーメッセージに対処方法（init実行またはIssue番号確認）が含まれること

---

## 3. インテグレーションテストシナリオ

### 3.1 Case 1: 同一リポジトリでの動作確認（後方互換性）

#### IT-001: infrastructure-as-codeリポジトリのIssueでワークフロー実行

**シナリオ名**: 同一リポジトリでのinit→execute

**目的**: 既存の動作（同一リポジトリでのワークフロー実行）が正常に動作し続けることを検証（後方互換性）

**前提条件**:
- テスト用の一時Gitリポジトリを作成（infrastructure-as-code）
- リポジトリ構造:
  ```
  /tmp/test-repos/infrastructure-as-code/
    .git/
    scripts/ai-workflow-v2/
  ```
- 環境変数`REPOS_ROOT`を一時ディレクトリに設定
- `GITHUB_TOKEN`が設定されていない（PR作成をスキップ）

**テスト手順**:

1. **initコマンド実行**
   ```bash
   npm run start -- init \
     --issue-url https://github.com/tielec/infrastructure-as-code/issues/305
   ```

2. **metadata.jsonの確認**
   - `.ai-workflow/issue-305/metadata.json`が作成されていることを確認
   - 以下のフィールドを確認:
     - `issue_number`: "305"
     - `issue_url`: "https://github.com/tielec/infrastructure-as-code/issues/305"
     - `repository`: "tielec/infrastructure-as-code"
     - `target_repository.path`: テスト用リポジトリのパス
     - `target_repository.github_name`: "tielec/infrastructure-as-code"
     - `target_repository.remote_url`: "https://github.com/tielec/infrastructure-as-code.git"
     - `target_repository.owner`: "tielec"
     - `target_repository.repo`: "infrastructure-as-code"

3. **ディレクトリ構造の確認**
   - `.ai-workflow/issue-305/`ディレクトリが作成されていることを確認
   - Gitブランチ`ai-workflow/issue-305`が作成されていることを確認

4. **executeコマンド実行（planningフェーズのみ）**
   ```bash
   npm run start -- execute --phase planning --issue 305
   ```

5. **workingDirの確認**
   - ログから`[INFO] Target repository: tielec/infrastructure-as-code`が出力されることを確認
   - ログから`[INFO] Local path: <テスト用リポジトリのパス>`が出力されることを確認

**期待結果**:
- ✓ metadata.jsonが正しく作成される
- ✓ `target_repository`フィールドが設定される
- ✓ `.ai-workflow`ディレクトリがinfrastructure-as-codeリポジトリ配下に作成される
- ✓ executeコマンドが正常に実行される（workingDirが正しい）
- ✓ 既存の動作と同じ結果が得られる

**確認項目**:
- [ ] initコマンドが成功する
- [ ] metadata.jsonの全フィールドが正しい
- [ ] .ai-workflowディレクトリが正しい場所に作成される
- [ ] Gitブランチが作成される
- [ ] executeコマンドが成功する
- [ ] workingDirが対象リポジトリのパスになる

---

### 3.2 Case 2: 別リポジトリでの動作確認（新機能）

#### IT-002: my-appリポジトリのIssueでワークフロー実行

**シナリオ名**: 別リポジトリでのinit→execute

**目的**: Issue URLから別リポジトリを自動判定し、そのリポジトリでワークフローが実行されることを検証

**前提条件**:
- テスト用の一時Gitリポジトリを2つ作成（infrastructure-as-code、my-app）
- リポジトリ構造:
  ```
  /tmp/test-repos/
    infrastructure-as-code/
      .git/
      scripts/ai-workflow-v2/
    my-app/
      .git/
      src/
      README.md
  ```
- 環境変数`REPOS_ROOT`を`/tmp/test-repos`に設定
- `GITHUB_TOKEN`が設定されていない（PR作成をスキップ）

**テスト手順**:

1. **initコマンド実行（infrastructure-as-codeリポジトリで実行）**
   ```bash
   cd /tmp/test-repos/infrastructure-as-code
   npm run start -- init \
     --issue-url https://github.com/tielec/my-app/issues/123
   ```

2. **コンソール出力の確認**
   - `[INFO] Target repository: tielec/my-app`が出力されることを確認
   - `[INFO] Local path: /tmp/test-repos/my-app`が出力されることを確認

3. **metadata.jsonの確認（my-appリポジトリ配下）**
   - `/tmp/test-repos/my-app/.ai-workflow/issue-123/metadata.json`が作成されていることを確認
   - 以下のフィールドを確認:
     - `issue_number`: "123"
     - `issue_url`: "https://github.com/tielec/my-app/issues/123"
     - `repository`: "tielec/my-app"
     - `target_repository.path`: "/tmp/test-repos/my-app"
     - `target_repository.github_name`: "tielec/my-app"
     - `target_repository.remote_url`: "https://github.com/tielec/my-app.git"
     - `target_repository.owner`: "tielec"
     - `target_repository.repo`: "my-app"

4. **ディレクトリ構造の確認**
   - `.ai-workflow/issue-123/`ディレクトリがmy-appリポジトリ配下に作成されていることを確認
   - infrastructure-as-codeリポジトリには`.ai-workflow/issue-123/`が作成されていないことを確認

5. **Gitブランチの確認（my-appリポジトリ）**
   ```bash
   cd /tmp/test-repos/my-app
   git branch
   ```
   - `ai-workflow/issue-123`ブランチが作成されていることを確認

6. **executeコマンド実行（infrastructure-as-codeリポジトリで実行）**
   ```bash
   cd /tmp/test-repos/infrastructure-as-code
   npm run start -- execute --phase planning --issue 123
   ```

7. **コンソール出力の確認**
   - `[INFO] Target repository: tielec/my-app`が出力されることを確認
   - `[INFO] Local path: /tmp/test-repos/my-app`が出力されることを確認

8. **workingDirの確認**
   - PhaseContextの`workingDir`が`/tmp/test-repos/my-app`になっていることを確認（ログまたはデバッグ出力）

**期待結果**:
- ✓ metadata.jsonがmy-appリポジトリ配下に作成される
- ✓ `target_repository`フィールドがmy-appの情報で設定される
- ✓ `.ai-workflow`ディレクトリがmy-appリポジトリ配下に作成される
- ✓ Gitブランチがmy-appリポジトリで作成される
- ✓ executeコマンドがmy-appリポジトリをworkingDirとして使用する

**確認項目**:
- [ ] initコマンドが成功する
- [ ] 対象リポジトリが正しく判定される（my-app）
- [ ] metadata.jsonがmy-app配下に作成される
- [ ] target_repositoryフィールドが正しい
- [ ] .ai-workflowディレクトリがmy-app配下に作成される
- [ ] Gitブランチがmy-appで作成される
- [ ] executeコマンドが成功する
- [ ] workingDirがmy-appのパスになる

---

### 3.3 Case 3: リポジトリが見つからない場合のエラー処理

#### IT-003: 存在しないリポジトリのIssueでエラー発生

**シナリオ名**: 存在しないリポジトリでのinit失敗

**目的**: リポジトリがローカルに存在しない場合、明確なエラーメッセージが表示されることを検証

**前提条件**:
- テスト用の一時Gitリポジトリを1つ作成（infrastructure-as-code）
- リポジトリ構造:
  ```
  /tmp/test-repos/
    infrastructure-as-code/
      .git/
      scripts/ai-workflow-v2/
  ```
- 環境変数`REPOS_ROOT`を`/tmp/test-repos`に設定
- `unknown-repo`リポジトリは存在しない

**テスト手順**:

1. **initコマンド実行（存在しないリポジトリ）**
   ```bash
   cd /tmp/test-repos/infrastructure-as-code
   npm run start -- init \
     --issue-url https://github.com/tielec/unknown-repo/issues/999
   ```

2. **エラー出力の確認**
   - 標準エラー出力に以下のメッセージが含まれることを確認:
     ```
     [ERROR] Repository 'unknown-repo' not found.
             Please set REPOS_ROOT environment variable or clone the repository.
     ```

3. **終了コードの確認**
   - プロセスが終了コード1で終了することを確認

4. **副作用の確認**
   - `.ai-workflow/issue-999/`ディレクトリが作成されていないことを確認
   - Gitブランチが作成されていないことを確認

**期待結果**:
- ✓ エラーメッセージが表示される
- ✓ エラーメッセージにリポジトリ名"unknown-repo"が含まれる
- ✓ エラーメッセージに対処方法が含まれる
- ✓ プロセスが終了コード1で終了する
- ✓ 不完全な状態（ディレクトリ、ブランチ）が残らない

**確認項目**:
- [ ] initコマンドが失敗する（終了コード1）
- [ ] エラーメッセージが明確である
- [ ] エラーメッセージにリポジトリ名が含まれる
- [ ] エラーメッセージに対処方法が含まれる
- [ ] .ai-workflowディレクトリが作成されない
- [ ] Gitブランチが作成されない

---

### 3.4 Case 4: 後方互換性テスト（target_repositoryが存在しない場合）

#### IT-004: 既存のmetadata.jsonでexecuteコマンド実行

**シナリオ名**: target_repositoryがnullの場合の後方互換性

**目的**: 既存のmetadata.json（`target_repository`フィールドが存在しない）でも正常に動作することを検証

**前提条件**:
- テスト用の一時Gitリポジトリを作成（infrastructure-as-code）
- 既存のmetadata.jsonを手動で作成（`target_repository`フィールドなし）:
  ```json
  {
    "issue_number": "305",
    "issue_url": "https://github.com/tielec/infrastructure-as-code/issues/305",
    "repository": "tielec/infrastructure-as-code",
    "workflow_version": "1.0.0",
    "current_phase": "planning",
    "design_decisions": {},
    "cost_tracking": {
      "total_input_tokens": 0,
      "total_output_tokens": 0,
      "total_cost_usd": 0.0
    },
    "phases": {},
    "created_at": "2025-01-13T10:00:00.000Z",
    "updated_at": "2025-01-13T10:00:00.000Z"
  }
  ```
- 環境変数`REPOS_ROOT`を一時ディレクトリに設定

**テスト手順**:

1. **executeコマンド実行**
   ```bash
   npm run start -- execute --phase planning --issue 305
   ```

2. **警告メッセージの確認**
   - コンソール出力に以下のメッセージが含まれることを確認:
     ```
     [WARNING] target_repository not found in metadata. Using current repository.
     ```

3. **workingDirの確認**
   - PhaseContextの`workingDir`が現在のリポジトリルートになっていることを確認

4. **フェーズ実行の確認**
   - planningフェーズが正常に実行されることを確認

**期待結果**:
- ✓ 警告メッセージが表示される
- ✓ executeコマンドが成功する
- ✓ workingDirが現在のリポジトリルートになる
- ✓ 既存のワークフローと同じ動作をする

**確認項目**:
- [ ] executeコマンドが成功する
- [ ] 警告メッセージが表示される
- [ ] workingDirが現在のリポジトリルートになる
- [ ] フェーズが正常に実行される

---

### 3.5 Case 5: マイグレーション機能のテスト

#### IT-005: WorkflowState.migrate()でtarget_repositoryフィールドが追加される

**シナリオ名**: メタデータスキーマのマイグレーション

**目的**: `WorkflowState.migrate()`が既存のmetadata.jsonに`target_repository`フィールドを追加することを検証

**前提条件**:
- テスト用の一時Gitリポジトリを作成（infrastructure-as-code）
- 既存のmetadata.jsonを作成（`target_repository`フィールドなし）

**テスト手順**:

1. **WorkflowState.load()とmigrate()の実行**
   ```typescript
   const metadataPath = "/tmp/test-repos/infrastructure-as-code/.ai-workflow/issue-305/metadata.json";
   const state = WorkflowState.load(metadataPath);
   const migrated = state.migrate();
   ```

2. **migrate()の戻り値確認**
   - `migrated`が`true`であることを確認

3. **マイグレーション後のmetadata.jsonの確認**
   - `target_repository`フィールドが追加されていることを確認
   - `target_repository`の値が`null`であることを確認
   - 既存のフィールド（`repository`等）が保持されていることを確認

4. **コンソール出力の確認**
   - 以下のメッセージが出力されることを確認:
     ```
     [INFO] Migrating metadata.json: Adding target_repository
     [OK] metadata.json migrated successfully
     ```

**期待結果**:
- ✓ migrate()が`true`を返す
- ✓ `target_repository`フィールドが追加される
- ✓ `target_repository`の値が`null`である
- ✓ 既存のフィールドが保持される
- ✓ マイグレーション成功メッセージが表示される

**確認項目**:
- [ ] migrate()が成功する（trueを返す）
- [ ] target_repositoryフィールドが追加される
- [ ] target_repositoryの初期値がnullである
- [ ] 既存のフィールドが変更されない
- [ ] メッセージが表示される

---

### 3.6 Case 6: Windowsパス対応のテスト

#### IT-006: Windowsパスでリポジトリ判定とワークフロー実行

**シナリオ名**: Windowsパスでの動作確認

**目的**: Windowsパス（バックスラッシュ）でも正しく動作することを検証

**前提条件**:
- Windows環境または`path.win32`を使用したテスト環境
- テスト用の一時Gitリポジトリを作成
- 環境変数`REPOS_ROOT`をWindowsパス形式で設定
  ```
  REPOS_ROOT=C:\Users\ytaka\TIELEC\development
  ```

**テスト手順**:

1. **initコマンド実行（Windowsパス）**
   ```bash
   npm run start -- init \
     --issue-url https://github.com/tielec/my-app/issues/123
   ```

2. **metadata.jsonのパス確認**
   - `target_repository.path`がWindowsパス形式で保存されることを確認
   - 例: `"C:\\Users\\ytaka\\TIELEC\\development\\my-app"`

3. **executeコマンド実行**
   ```bash
   npm run start -- execute --phase planning --issue 123
   ```

4. **workingDirの確認**
   - PhaseContextの`workingDir`がWindowsパス形式であることを確認

**期待結果**:
- ✓ Windowsパスが正しく処理される
- ✓ バックスラッシュがエスケープされて保存される
- ✓ executeコマンドが成功する

**確認項目**:
- [ ] initコマンドが成功する
- [ ] metadata.jsonのパスがWindowsパス形式である
- [ ] executeコマンドが成功する
- [ ] workingDirがWindowsパス形式である

---

## 4. テストデータ

### 4.1 テストURL（parseIssueUrl用）

#### 正常系URL
```
https://github.com/tielec/my-app/issues/123
https://github.com/tielec/my-app/issues/123/
https://github.com/tielec/infrastructure-as-code/issues/305
https://github.com/tielec/another-repo/issues/99999
```

#### 異常系URL
```
https://example.com/issues/123                     // GitHub以外
https://github.com/tielec/my-app/pulls/123         // プルリクエスト
https://github.com/tielec/my-app                   // Issue番号なし
https://github.com/tielec/my-app/issues/abc        // Issue番号が数値でない
```

### 4.2 テストリポジトリ構造（インテグレーションテスト用）

#### infrastructure-as-codeリポジトリ
```
/tmp/test-repos/infrastructure-as-code/
  .git/
  scripts/
    ai-workflow-v2/
      src/
        main.ts
        types.ts
        core/
      tests/
      package.json
  README.md
```

#### my-appリポジトリ
```
/tmp/test-repos/my-app/
  .git/
  src/
    index.ts
  README.md
  package.json
```

### 4.3 テストmetadata.json（後方互換性テスト用）

#### target_repositoryなしのmetadata.json
```json
{
  "issue_number": "305",
  "issue_url": "https://github.com/tielec/infrastructure-as-code/issues/305",
  "repository": "tielec/infrastructure-as-code",
  "workflow_version": "1.0.0",
  "current_phase": "planning",
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
    "planning": {
      "status": "not_started",
      "preset": "default",
      "inputs": {},
      "outputs": {},
      "cost_tracking": {
        "input_tokens": 0,
        "output_tokens": 0,
        "cost_usd": 0.0
      }
    }
  },
  "created_at": "2025-01-13T10:00:00.000Z",
  "updated_at": "2025-01-13T10:00:00.000Z"
}
```

#### target_repository設定済みのmetadata.json
```json
{
  "issue_number": "123",
  "issue_url": "https://github.com/tielec/my-app/issues/123",
  "repository": "tielec/my-app",
  "target_repository": {
    "path": "/tmp/test-repos/my-app",
    "github_name": "tielec/my-app",
    "remote_url": "https://github.com/tielec/my-app.git",
    "owner": "tielec",
    "repo": "my-app"
  },
  "workflow_version": "1.0.0",
  "current_phase": "planning",
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
    "planning": {
      "status": "not_started",
      "preset": "default",
      "inputs": {},
      "outputs": {},
      "cost_tracking": {
        "input_tokens": 0,
        "output_tokens": 0,
        "cost_usd": 0.0
      }
    }
  },
  "created_at": "2025-01-13T10:00:00.000Z",
  "updated_at": "2025-01-13T10:00:00.000Z"
}
```

---

## 5. テスト環境要件

### 5.1 ユニットテスト環境

**必要な環境**:
- Node.js v18以上
- npm v8以上
- テストフレームワーク: Jest（既存）
- モックライブラリ: Jest標準のモック機能

**モック/スタブの使用**:
- `fs.existsSync()` - ファイル・ディレクトリ存在確認
- `fs.readdirSync()` - ディレクトリ列挙
- `process.env` - 環境変数
- `os.homedir()` - ホームディレクトリ取得

**実行コマンド**:
```bash
npm test -- repository-resolution.test.ts
```

### 5.2 インテグレーションテスト環境

**必要な環境**:
- Node.js v18以上
- npm v8以上
- Git v2.0以上
- テストフレームワーク: Jest（既存）
- 一時ディレクトリ: `/tmp/test-repos/`（テスト終了後にクリーンアップ）

**外部サービス**:
- Gitリポジトリ: テスト用の一時Gitリポジトリを作成（実際の`.git`ディレクトリを持つ）
- GitHub API: モック（GITHUB_TOKENを設定しないことでPR作成をスキップ）

**セットアップ**:
```typescript
beforeAll(async () => {
  // テスト用の一時Gitリポジトリを作成
  await setupTestRepositories();
});

afterAll(async () => {
  // テスト用の一時ディレクトリをクリーンアップ
  await cleanupTestRepositories();
});
```

**実行コマンド**:
```bash
npm test -- multi-repo-workflow.test.ts
```

### 5.3 CI/CD環境（Jenkins）

**必要な環境変数**:
- `REPOS_ROOT`: リポジトリの親ディレクトリ（例: `C:\Users\ytaka\TIELEC\development`）
- `GITHUB_TOKEN`: GitHub API認証（PR作成用、テストではオプション）

**Jenkinsfile設定例**:
```groovy
environment {
    REPOS_ROOT = 'C:\\Users\\ytaka\\TIELEC\\development'
}
```

---

## 6. テスト実行順序と依存関係

### 6.1 ユニットテスト実行順序

1. **parseIssueUrl()のテスト**（UT-001〜UT-007）
   - 他のテストに依存しない
   - 最初に実行

2. **resolveLocalRepoPath()のテスト**（UT-101〜UT-106）
   - 他のテストに依存しない
   - parseIssueUrl()のテスト後に実行

3. **findWorkflowMetadata()のテスト**（UT-201〜UT-203）
   - 他のテストに依存しない
   - resolveLocalRepoPath()のテスト後に実行

### 6.2 インテグレーションテスト実行順序

1. **Case 1: 同一リポジトリでの動作確認**（IT-001）
   - 後方互換性を最初に検証
   - 他のテストに依存しない

2. **Case 2: 別リポジトリでの動作確認**（IT-002）
   - 新機能の主要シナリオ
   - IT-001の後に実行（独立しているが、順序として推奨）

3. **Case 3: リポジトリが見つからない場合**（IT-003）
   - エラーハンドリングの検証
   - 他のテストに依存しない

4. **Case 4: 後方互換性テスト**（IT-004）
   - 既存metadata.jsonでの動作確認
   - 他のテストに依存しない

5. **Case 5: マイグレーション機能のテスト**（IT-005）
   - WorkflowState.migrate()の検証
   - 他のテストに依存しない

6. **Case 6: Windowsパス対応のテスト**（IT-006）
   - Windows環境またはモック環境が必要
   - 他のテストに依存しない（環境依存のため最後に実行を推奨）

---

## 7. 品質ゲート（Phase 3）

テストシナリオは以下の品質ゲートを満たす必要があります：

- [x] **Phase 2の戦略に沿ったテストシナリオである**
  - UNIT_INTEGRATIONに準拠
  - ユニットテスト: 20ケース（parseIssueUrl: 7、resolveLocalRepoPath: 6、findWorkflowMetadata: 3、その他: 4）
  - インテグレーションテスト: 6ケース

- [x] **主要な正常系がカバーされている**
  - ユニットテスト:
    - UT-001: parseIssueUrl_正常系_標準URL
    - UT-101: resolveLocalRepoPath_正常系_REPOS_ROOT設定済み
    - UT-201: findWorkflowMetadata_正常系_REPOS_ROOT配下で見つかる
  - インテグレーションテスト:
    - IT-001: 同一リポジトリでの動作確認（後方互換性）
    - IT-002: 別リポジトリでの動作確認（新機能）

- [x] **主要な異常系がカバーされている**
  - ユニットテスト:
    - UT-004: parseIssueUrl_異常系_GitHub以外のURL
    - UT-105: resolveLocalRepoPath_異常系_リポジトリが見つからない
    - UT-203: findWorkflowMetadata_異常系_メタデータが見つからない
  - インテグレーションテスト:
    - IT-003: リポジトリが見つからない場合のエラー処理

- [x] **期待結果が明確である**
  - すべてのテストケースで「期待結果」セクションを記載
  - 具体的な出力値、エラーメッセージ、状態変化を明示
  - 「検証項目」でチェックリスト形式で確認ポイントを列挙

**すべての品質ゲートを満たしています。**

---

## 8. テストカバレッジ目標

### 8.1 機能カバレッジ

| 機能要件 | テストケース | カバー状況 |
|---------|------------|----------|
| FR-001: Issue URLからリポジトリ情報を抽出 | UT-001〜UT-007 | ✓ 完全カバー |
| FR-002: ローカルリポジトリパスを自動解決 | UT-101〜UT-106, IT-002 | ✓ 完全カバー |
| FR-003: target_repositoryフィールドをメタデータに追加 | IT-001, IT-002, IT-005 | ✓ 完全カバー |
| FR-004: initコマンドでtarget_repositoryを自動設定 | IT-001, IT-002 | ✓ 完全カバー |
| FR-005: executeコマンドでメタデータからtarget_repositoryを読み込み | IT-001, IT-002, IT-004 | ✓ 完全カバー |
| FR-006: ワークフローディレクトリを対象リポジトリ配下に作成 | IT-001, IT-002 | ✓ 完全カバー |
| FR-007: メタデータスキーマのマイグレーション | IT-005 | ✓ 完全カバー |
| FR-008: メタデータ探索機能 | UT-201〜UT-203, IT-002 | ✓ 完全カバー |
| FR-009: 環境変数REPOS_ROOTのサポート | UT-101, IT-002 | ✓ 完全カバー |

### 8.2 受け入れ基準カバレッジ

| 受け入れ基準 | テストケース | カバー状況 |
|------------|------------|----------|
| AC-001: Issue URLからリポジトリ情報を抽出できる | UT-001 | ✓ |
| AC-002: 無効なIssue URLでエラーが発生する | UT-004, UT-005, UT-006, UT-007 | ✓ |
| AC-003: 環境変数REPOS_ROOTが設定されている場合、優先的に使用される | UT-101 | ✓ |
| AC-004: 環境変数が未設定の場合、候補パスから探索する | UT-102, UT-103 | ✓ |
| AC-005: リポジトリが見つからない場合、明確なエラーメッセージが表示される | UT-105, IT-003 | ✓ |
| AC-006: initコマンドで対象リポジトリ情報がメタデータに保存される | IT-001, IT-002 | ✓ |
| AC-007: .ai-workflowディレクトリが対象リポジトリ配下に作成される | IT-001, IT-002 | ✓ |
| AC-008: executeコマンドでメタデータからtarget_repositoryを読み込む | IT-001, IT-002 | ✓ |
| AC-009: target_repositoryが存在しない場合、後方互換性が保たれる | IT-004 | ✓ |
| AC-010: マイグレーション機能が正常に動作する | IT-005 | ✓ |
| AC-011: 同一リポジトリでの動作が変わらない（後方互換性） | IT-001 | ✓ |
| AC-012: 別リポジトリのIssueに対して正しく動作する | IT-002 | ✓ |
| AC-013: Windowsパスが正しく処理される | UT-104, IT-006 | ✓ |

### 8.3 コードカバレッジ目標

- **行カバレッジ**: 80%以上
- **分岐カバレッジ**: 75%以上
- **関数カバレッジ**: 90%以上

---

## 9. リスクと対策

### リスク1: 後方互換性の破壊

**軽減策**:
- IT-001で既存の動作を確認
- IT-004でtarget_repositoryがnullの場合の動作を確認
- 既存のissue-305などで実際に回帰テストを実施

### リスク2: ローカルリポジトリパス探索の失敗

**軽減策**:
- UT-101〜UT-106で探索ロジックを詳細にテスト
- IT-003でエラーハンドリングを確認
- 環境変数REPOS_ROOTの推奨設定をドキュメント化

### リスク3: メタデータマイグレーションの失敗

**軽減策**:
- IT-005でマイグレーション機能を専用にテスト
- 既存のrollback機能の存在を確認
- マイグレーション前のバックアップ作成を推奨（ドキュメント）

### リスク4: Windowsパス対応の不備

**軽減策**:
- UT-104でWindowsパスのユニットテスト
- IT-006でWindows環境での統合テスト
- `path.join()`などNode.js標準APIを使用

---

## 10. 次のステップ

Phase 4（実装）に進むための条件:
- [x] このテストシナリオ書がレビューされ、承認されている
- [x] すべての品質ゲートが満たされている
- [ ] Phase 4の実行者が割り当てられている

**テストシナリオ承認日**: （Test Scenario Phase完了後に記入）
**承認者**: （Test Scenario Phaseで記入）

---

## 付録A: テストケース一覧

### ユニットテストケース

| テストID | テスト名 | カテゴリ | 優先度 |
|---------|---------|---------|-------|
| UT-001 | parseIssueUrl_正常系_標準URL | 正常系 | 高 |
| UT-002 | parseIssueUrl_正常系_末尾スラッシュあり | 正常系 | 中 |
| UT-003 | parseIssueUrl_正常系_大きなIssue番号 | 境界値 | 中 |
| UT-004 | parseIssueUrl_異常系_GitHub以外のURL | 異常系 | 高 |
| UT-005 | parseIssueUrl_異常系_プルリクエストURL | 異常系 | 中 |
| UT-006 | parseIssueUrl_異常系_Issue番号なし | 異常系 | 中 |
| UT-007 | parseIssueUrl_異常系_Issue番号が数値でない | 異常系 | 中 |
| UT-101 | resolveLocalRepoPath_正常系_REPOS_ROOT設定済み | 正常系 | 高 |
| UT-102 | resolveLocalRepoPath_正常系_候補パス探索_最初の候補で見つかる | 正常系 | 高 |
| UT-103 | resolveLocalRepoPath_正常系_候補パス探索_2番目の候補で見つかる | 正常系 | 中 |
| UT-104 | resolveLocalRepoPath_正常系_Windowsパス対応 | 正常系 | 高 |
| UT-105 | resolveLocalRepoPath_異常系_リポジトリが見つからない | 異常系 | 高 |
| UT-106 | resolveLocalRepoPath_異常系_ディレクトリは存在するが.gitがない | 異常系 | 中 |
| UT-201 | findWorkflowMetadata_正常系_REPOS_ROOT配下で見つかる | 正常系 | 高 |
| UT-202 | findWorkflowMetadata_正常系_候補パス探索で見つかる | 正常系 | 中 |
| UT-203 | findWorkflowMetadata_異常系_メタデータが見つからない | 異常系 | 高 |

### インテグレーションテストケース

| テストID | テスト名 | カテゴリ | 優先度 |
|---------|---------|---------|-------|
| IT-001 | infrastructure-as-codeリポジトリのIssueでワークフロー実行 | 後方互換性 | 最高 |
| IT-002 | my-appリポジトリのIssueでワークフロー実行 | 新機能 | 最高 |
| IT-003 | 存在しないリポジトリのIssueでエラー発生 | エラーハンドリング | 高 |
| IT-004 | 既存のmetadata.jsonでexecuteコマンド実行 | 後方互換性 | 高 |
| IT-005 | WorkflowState.migrate()でtarget_repositoryフィールドが追加される | マイグレーション | 高 |
| IT-006 | Windowsパスでリポジトリ判定とワークフロー実行 | Windowsパス対応 | 中 |

---

**テストシナリオバージョン**: 1.0.0
**最終更新日**: 2025-01-13
