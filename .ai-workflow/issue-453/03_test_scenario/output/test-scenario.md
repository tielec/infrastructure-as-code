# テストシナリオ書

**Issue**: #453
**タイトル**: [TASK] AI Workflow Orchestrator ジョブを実行モードごとに分割・リポジトリ別構成に変更
**作成日**: 2025-01-17
**URL**: https://github.com/tielec/infrastructure-as-code/issues/453

---

## 0. Planning/Requirements/Design Documentの確認

### Phase 2で決定されたテスト戦略

- **テスト戦略**: INTEGRATION_ONLY（Jenkins環境での統合テストのみ）
- **テストコード戦略**: CREATE_TEST（手動テスト手順書を新規作成）
- **判断根拠**:
  - Job DSLはGroovyコードだが、Jenkins環境依存のため単独でのユニットテストが困難
  - 実際にJenkinsでジョブを生成し、パラメータが正しく表示されるかを確認する統合テストが必要
  - ユーザーストーリーベースの機能追加ではなく、内部リファクタリングのためBDDは不要

### テスト実施方法

1. **シードジョブ実行テスト**: `Admin_Jobs/job-creator`を実行してジョブが正しく生成されることを確認
2. **パラメータ画面確認テスト**: 各ジョブのパラメータ画面を確認（パラメータ数と内容が要件通りか）
3. **DRY_RUN実行テスト**: 各ジョブを`DRY_RUN=true`で実行して動作確認

---

## 1. テスト戦略サマリー

### 選択されたテスト戦略

**INTEGRATION_ONLY**: Jenkins統合テストのみ

### テスト対象の範囲

本テストシナリオは、以下の範囲をカバーします：

1. **Job DSL生成テスト**: 5つの新しいJob DSLファイルが正しくJenkinsジョブを生成できるか
2. **フォルダ構造テスト**: リポジトリ別のフォルダ構造が正しく生成されるか
3. **パラメータ定義テスト**: 各ジョブのパラメータが要件通りに表示されるか（数、種類、必須/任意）
4. **EXECUTION_MODE設定テスト**: 各ジョブがEXECUTION_MODEを固定値として正しく渡すか
5. **Jenkinsfile連携テスト**: 生成されたジョブがJenkinsfileと正しく連携して動作するか
6. **Deprecated化テスト**: 既存ジョブが非推奨として正しく表示されるか

### テストの目的

- 既存の`ai_workflow_orchestrator`ジョブを5つの独立したジョブに分割できることを検証
- リポジトリ別フォルダ構成が正しく動作することを検証
- パラメータが各実行モードに応じて適切に削減されることを検証（24個 → 8〜15個）
- 既存の機能が損なわれず、後方互換性が維持されることを検証

---

## 2. 統合テストシナリオ

### 2.1 シードジョブ実行テスト

#### テストシナリオ: TS-INT-001 - シードジョブによるジョブ生成

**目的**: シードジョブ（`Admin_Jobs/job-creator`）を実行し、5つの新しいジョブが正しく生成されることを検証

**前提条件**:
- Jenkins環境が正常に動作している
- `job-config.yaml`に5つの新しいジョブ定義が追加されている
- `folder-config.yaml`にAI_Workflowの動的フォルダルールが追加されている
- 5つのJob DSLファイルが`jenkins/jobs/dsl/ai-workflow/`に配置されている
- `jenkinsManagedRepositories`に最低1つのリポジトリ（例: `infrastructure-as-code`）が登録されている

**テスト手順**:

1. Jenkinsにログイン
2. `Admin_Jobs/job-creator`ジョブに移動
3. 「Build Now」をクリックしてシードジョブを実行
4. ビルドログを確認し、エラーがないことを確認
5. ビルドが成功（緑色）で完了することを確認
6. Jenkins Top画面に戻り、`AI_Workflow`フォルダを開く

**期待結果**:

- [ ] シードジョブが成功（SUCCESS）で完了する
- [ ] ビルドログに「ERROR」「FAILED」の文字列が含まれない
- [ ] `AI_Workflow`フォルダが存在する
- [ ] `AI_Workflow/{repository-name}`フォルダが各リポジトリに対して生成される
- [ ] 各リポジトリフォルダ配下に以下の5つのジョブが生成される:
  - `all_phases`
  - `preset`
  - `single_phase`
  - `rollback`
  - `auto_issue`

**確認項目**:

- [ ] シードジョブのビルド時間が5分以内である（非機能要件）
- [ ] 生成されたジョブのdisplayNameが正しい（例: "All Phases Execution"）
- [ ] フォルダ構造が期待通り（`AI_Workflow/infrastructure-as-code/all_phases`等）

**異常系テスト**:

- [ ] DSLファイルに構文エラーがある場合、シードジョブがFAILEDとなり、適切なエラーメッセージが表示される
- [ ] `jenkinsManagedRepositories`が空の場合、ジョブが生成されない（エラーにはならない）

---

#### テストシナリオ: TS-INT-002 - リポジトリ別フォルダ構成の検証

**目的**: 複数のリポジトリに対して、それぞれ独立したフォルダとジョブが生成されることを検証

**前提条件**:
- `jenkinsManagedRepositories`に複数のリポジトリ（例: `infrastructure-as-code`, `ai-workflow-agent`）が登録されている
- シードジョブが実行済み

**テスト手順**:

1. `AI_Workflow`フォルダを開く
2. 各リポジトリ名のサブフォルダが存在することを確認
3. 各サブフォルダを開き、5つのジョブが存在することを確認

**期待結果**:

- [ ] `AI_Workflow/infrastructure-as-code/`フォルダが存在する
- [ ] `AI_Workflow/ai-workflow-agent/`フォルダが存在する
- [ ] 各リポジトリフォルダに5つのジョブ（all_phases, preset, single_phase, rollback, auto_issue）が存在する
- [ ] 合計ジョブ数 = リポジトリ数 × 5

**確認項目**:

- [ ] フォルダのdescriptionにリポジトリ名が正しく埋め込まれている
- [ ] ジョブ名が一意である（重複がない）

---

### 2.2 パラメータ定義テスト

#### テストシナリオ: TS-INT-003 - all_phasesジョブのパラメータ検証

**目的**: `all_phases`ジョブのパラメータが要件通りに定義されていることを検証

**前提条件**:
- `AI_Workflow/infrastructure-as-code/all_phases`ジョブが生成されている

**テスト手順**:

1. `AI_Workflow/infrastructure-as-code/all_phases`ジョブを開く
2. 「Build with Parameters」をクリック
3. パラメータ一覧を確認

**期待結果**:

| パラメータ名 | 表示 | 型 | 必須/任意 | デフォルト値 |
|------------|------|-----|-----------|------------|
| ISSUE_URL | ✅ | String | 必須（空欄） | （空文字） |
| BRANCH_NAME | ✅ | String | 任意 | （空文字） |
| AGENT_MODE | ✅ | Choice | 必須 | `auto` |
| DRY_RUN | ✅ | Boolean | 必須 | `false` |
| SKIP_REVIEW | ✅ | Boolean | 必須 | `false` |
| FORCE_RESET | ✅ | Boolean | 必須 | `false` |
| MAX_RETRIES | ✅ | Choice | 必須 | `3` |
| CLEANUP_ON_COMPLETE_FORCE | ✅ | Boolean | 必須 | `false` |
| GIT_COMMIT_USER_NAME | ✅ | String | 必須 | `AI Workflow Bot` |
| GIT_COMMIT_USER_EMAIL | ✅ | String | 必須 | `ai-workflow@example.com` |
| AWS_ACCESS_KEY_ID | ✅ | String | 任意 | （空文字） |
| AWS_SECRET_ACCESS_KEY | ✅ | NonStoredPassword | 任意 | - |
| AWS_SESSION_TOKEN | ✅ | NonStoredPassword | 任意 | - |
| COST_LIMIT_USD | ✅ | String | 必須 | `5.0` |
| LOG_LEVEL | ✅ | Choice | 必須 | `INFO` |
| **表示されないパラメータ** | | | | |
| EXECUTION_MODE | ❌ | - | - | - |
| PRESET | ❌ | - | - | - |
| START_PHASE | ❌ | - | - | - |
| ROLLBACK_TO_PHASE | ❌ | - | - | - |
| ROLLBACK_TO_STEP | ❌ | - | - | - |
| ROLLBACK_REASON | ❌ | - | - | - |
| ROLLBACK_REASON_FILE | ❌ | - | - | - |
| AUTO_ISSUE_CATEGORY | ❌ | - | - | - |
| AUTO_ISSUE_LIMIT | ❌ | - | - | - |
| AUTO_ISSUE_SIMILARITY_THRESHOLD | ❌ | - | - | - |
| GITHUB_REPOSITORY | ❌ | - | - | - |

**確認項目**:

- [ ] パラメータの総数が**14個**である
- [ ] 各パラメータの説明文が適切に表示されている
- [ ] 必須パラメータが明確に示されている
- [ ] Choiceパラメータの選択肢が正しい（例: AGENT_MODEは`auto`, `codex`, `claude`）
- [ ] NonStoredPasswordパラメータがマスクされている

**異常系テスト**:

- [ ] 不要なパラメータ（PRESET、START_PHASE等）が表示されていないことを確認

---

#### テストシナリオ: TS-INT-004 - presetジョブのパラメータ検証

**目的**: `preset`ジョブのパラメータが要件通りに定義されていることを検証

**前提条件**:
- `AI_Workflow/infrastructure-as-code/preset`ジョブが生成されている

**テスト手順**:

1. `AI_Workflow/infrastructure-as-code/preset`ジョブを開く
2. 「Build with Parameters」をクリック
3. パラメータ一覧を確認

**期待結果**:

- [ ] パラメータの総数が**15個**である（all_phasesの14個 + PRESET）
- [ ] **PRESETパラメータ**が表示される（Choiceタイプ、必須）
- [ ] PRESETの選択肢が以下の通り:
  - `quick-fix`
  - `implementation`
  - `testing`
  - `review-requirements`
  - `review-design`
  - `review-test-scenario`
  - `finalize`
- [ ] 他のパラメータはall_phasesと同じ
- [ ] START_PHASE、ROLLBACK_*、AUTO_ISSUE_*が表示されない

**確認項目**:

- [ ] PRESETパラメータの説明文が各プリセットの内容を説明している

---

#### テストシナリオ: TS-INT-005 - single_phaseジョブのパラメータ検証

**目的**: `single_phase`ジョブのパラメータが要件通りに定義されていることを検証

**前提条件**:
- `AI_Workflow/infrastructure-as-code/single_phase`ジョブが生成されている

**テスト手順**:

1. `AI_Workflow/infrastructure-as-code/single_phase`ジョブを開く
2. 「Build with Parameters」をクリック
3. パラメータ一覧を確認

**期待結果**:

- [ ] パラメータの総数が**13個**である
- [ ] **START_PHASEパラメータ**が表示される（Choiceタイプ、必須）
- [ ] START_PHASEの選択肢が以下の通り:
  - `planning`
  - `requirements`
  - `design`
  - `test_scenario`
  - `implementation`
  - `test_implementation`
  - `testing`
  - `documentation`
  - `report`
  - `evaluation`
- [ ] FORCE_RESETが表示されない
- [ ] CLEANUP_ON_COMPLETE_FORCEが表示されない
- [ ] PRESET、ROLLBACK_*、AUTO_ISSUE_*が表示されない

**確認項目**:

- [ ] パラメータ数が14個（all_phases）から13個に削減されている
- [ ] START_PHASEパラメータの説明文が適切

---

#### テストシナリオ: TS-INT-006 - rollbackジョブのパラメータ検証

**目的**: `rollback`ジョブのパラメータが要件通りに定義されていることを検証

**前提条件**:
- `AI_Workflow/infrastructure-as-code/rollback`ジョブが生成されている

**テスト手順**:

1. `AI_Workflow/infrastructure-as-code/rollback`ジョブを開く
2. 「Build with Parameters」をクリック
3. パラメータ一覧を確認

**期待結果**:

- [ ] パラメータの総数が**12個**である
- [ ] **ROLLBACK_TO_PHASEパラメータ**が表示される（Choiceタイプ、必須）
- [ ] ROLLBACK_TO_PHASEの選択肢が以下の通り（evaluationは含まれない）:
  - `implementation`
  - `planning`
  - `requirements`
  - `design`
  - `test_scenario`
  - `test_implementation`
  - `testing`
  - `documentation`
  - `report`
- [ ] **ROLLBACK_TO_STEPパラメータ**が表示される（Choiceタイプ、任意）
- [ ] ROLLBACK_TO_STEPの選択肢: `revise`, `execute`, `review`
- [ ] **ROLLBACK_REASONパラメータ**が表示される（Textタイプ、任意）
- [ ] **ROLLBACK_REASON_FILEパラメータ**が表示される（Stringタイプ、任意）
- [ ] 以下が表示されない: PRESET、START_PHASE、AUTO_ISSUE_*、SKIP_REVIEW、FORCE_RESET、MAX_RETRIES、CLEANUP_ON_COMPLETE_FORCE

**確認項目**:

- [ ] Rollback専用パラメータの説明文が適切（差し戻し理由の注入方法等）
- [ ] パラメータ数が最も大きく削減されている（24個 → 12個）

---

#### テストシナリオ: TS-INT-007 - auto_issueジョブのパラメータ検証

**目的**: `auto_issue`ジョブのパラメータが要件通りに定義されていることを検証

**前提条件**:
- `AI_Workflow/infrastructure-as-code/auto_issue`ジョブが生成されている

**テスト手順**:

1. `AI_Workflow/infrastructure-as-code/auto_issue`ジョブを開く
2. 「Build with Parameters」をクリック
3. パラメータ一覧を確認

**期待結果**:

- [ ] パラメータの総数が**8個**である（最大の削減効果）
- [ ] **GITHUB_REPOSITORYパラメータ**が表示される（Stringタイプ、必須）
- [ ] **AUTO_ISSUE_CATEGORYパラメータ**が表示される（Choiceタイプ、必須）
- [ ] AUTO_ISSUE_CATEGORYの選択肢: `bug`, `refactor`, `enhancement`, `all`
- [ ] **AUTO_ISSUE_LIMITパラメータ**が表示される（Stringタイプ、任意、デフォルト`5`）
- [ ] **AUTO_ISSUE_SIMILARITY_THRESHOLDパラメータ**が表示される（Stringタイプ、任意、デフォルト`0.8`）
- [ ] AGENT_MODE、DRY_RUN、COST_LIMIT_USD、LOG_LEVELが表示される
- [ ] 以下が表示されない: ISSUE_URL、BRANCH_NAME、PRESET、START_PHASE、ROLLBACK_*、SKIP_REVIEW、FORCE_RESET、MAX_RETRIES、CLEANUP_ON_COMPLETE_FORCE、GIT_COMMIT_*、AWS_*

**確認項目**:

- [ ] ISSUE_URLが表示されない（auto_issueでは不要）
- [ ] GITHUB_REPOSITORYが必須として表示される
- [ ] パラメータ数が24個から8個に削減されている（削減率66.7%）

---

### 2.3 EXECUTION_MODE固定値設定テスト

#### テストシナリオ: TS-INT-008 - all_phasesジョブのEXECUTION_MODE検証

**目的**: `all_phases`ジョブがEXECUTION_MODEを`all_phases`として内部的に設定し、Jenkinsfileに渡すことを検証

**前提条件**:
- `AI_Workflow/infrastructure-as-code/all_phases`ジョブが生成されている
- Jenkinsfileが`EXECUTION_MODE`パラメータを受け取る実装になっている

**テスト手順**:

1. `AI_Workflow/infrastructure-as-code/all_phases`ジョブを開く
2. 「Build with Parameters」をクリック
3. 必須パラメータのみ入力:
   - `ISSUE_URL`: `https://github.com/tielec/infrastructure-as-code/issues/999`（ダミーIssue）
   - `DRY_RUN`: `true`（ドライランモード）
4. 「Build」をクリック
5. ビルドログを確認

**期待結果**:

- [ ] ビルドが開始される
- [ ] ビルドログに`EXECUTION_MODE=all_phases`と記録される
- [ ] Jenkinsfileが正常に動作する（エラーが発生しない）
- [ ] DRY_RUNモードのため、実際のAPI呼び出しは行わない
- [ ] ビルドが成功（SUCCESS）で完了する

**確認項目**:

- [ ] パラメータ画面にEXECUTION_MODEが表示されていないこと（内部的に設定）
- [ ] 環境変数としてEXECUTION_MODEがJenkinsfileに渡されていること

**ログ例**（期待される出力）:
```
[Pipeline] {
[Pipeline] echo
EXECUTION_MODE: all_phases
ISSUE_URL: https://github.com/tielec/infrastructure-as-code/issues/999
DRY_RUN: true
```

---

#### テストシナリオ: TS-INT-009 - 全ジョブのEXECUTION_MODE一斉検証

**目的**: 5つのジョブそれぞれが、正しいEXECUTION_MODEを設定していることを検証

**前提条件**:
- 5つのジョブすべてが生成されている

**テスト手順**:

各ジョブについて以下を実行:

1. ジョブを開く
2. 「Build with Parameters」をクリック
3. 最小限のパラメータを入力（DRY_RUN=true）
4. ビルドを実行
5. ビルドログで`EXECUTION_MODE`の値を確認

**期待結果**:

| ジョブ名 | EXECUTION_MODE | ビルド結果 |
|---------|----------------|-----------|
| all_phases | `all_phases` | SUCCESS |
| preset | `preset` | SUCCESS |
| single_phase | `single_phase` | SUCCESS |
| rollback | `rollback` | SUCCESS |
| auto_issue | `auto_issue` | SUCCESS |

**確認項目**:

- [ ] 各ジョブのEXECUTION_MODEが固定値として正しく設定されている
- [ ] Jenkinsfileがすべての実行モードで正常に動作する
- [ ] DRY_RUNモードで実際のAPI呼び出しが行われない

---

### 2.4 Jenkinsfile連携テスト

#### テストシナリオ: TS-INT-010 - Jenkinsfile参照設定の検証

**目的**: 各ジョブが正しいJenkinsfile（ai-workflow-agentリポジトリ）を参照していることを検証

**前提条件**:
- 5つのジョブすべてが生成されている

**テスト手順**:

1. 各ジョブの設定画面（Configure）を開く
2. 「Pipeline」セクションを確認
3. 「Pipeline script from SCM」が選択されていることを確認
4. SCM設定を確認

**期待結果**:

- [ ] 「Pipeline script from SCM」が選択されている
- [ ] SCM: Git
- [ ] Repository URL: `https://github.com/tielec/ai-workflow-agent.git`
- [ ] Credentials: `github-token`
- [ ] Branch: `*/main`
- [ ] Script Path: `Jenkinsfile`

**確認項目**:

- [ ] すべてのジョブが同じJenkinsfileを参照している
- [ ] クレデンシャルが正しく設定されている

---

### 2.5 Deprecated化テスト

#### テストシナリオ: TS-INT-011 - 既存ジョブのDeprecated表示検証

**目的**: 既存の`ai_workflow_orchestrator`ジョブが非推奨として正しく表示されることを検証

**前提条件**:
- 既存の`ai_workflow_orchestrator.groovy`が修正されている（Deprecatedコメント追加）
- シードジョブが実行済み

**テスト手順**:

1. `AI_Workflow/ai_workflow_orchestrator`ジョブを開く（存在する場合）
2. ジョブのdescription（説明文）を確認
3. パラメータ画面を確認

**期待結果**:

- [ ] descriptionの冒頭に「⚠️ このジョブは非推奨です」と表示される
- [ ] 新しいジョブへの移行案内が表示される
- [ ] 5つの新しいジョブのパスが記載されている:
  - `AI_Workflow/{repository-name}/all_phases`
  - `AI_Workflow/{repository-name}/preset`
  - `AI_Workflow/{repository-name}/single_phase`
  - `AI_Workflow/{repository-name}/rollback`
  - `AI_Workflow/{repository-name}/auto_issue`
- [ ] 削除予定日が明記されている（例: 2025年2月17日）
- [ ] 移行方法へのリンク（jenkins/README.md）が記載されている

**確認項目**:

- [ ] 既存ジョブが削除されておらず、実行可能な状態である（後方互換性）
- [ ] パラメータは既存のまま（24個すべて表示される）

---

### 2.6 統合テスト - エンドツーエンド

#### テストシナリオ: TS-INT-012 - 実際のIssue URLでの動作確認（all_phases）

**目的**: 実際のGitHub Issue URLを使用して、all_phasesジョブが正常に動作することを検証

**前提条件**:
- テスト用のGitHub Issueが存在する（例: #999 - テスト用Issue）
- 必要なクレデンシャル（GitHub Token、Claude API Key）が設定されている

**テスト手順**:

1. `AI_Workflow/infrastructure-as-code/all_phases`ジョブを開く
2. 「Build with Parameters」をクリック
3. パラメータを入力:
   - `ISSUE_URL`: `https://github.com/tielec/infrastructure-as-code/issues/999`
   - `DRY_RUN`: `true`
   - その他はデフォルト
4. ビルドを実行
5. ビルドログを確認

**期待結果**:

- [ ] ビルドが開始される
- [ ] Jenkinsfileがチェックアウトされる
- [ ] `EXECUTION_MODE=all_phases`が設定される
- [ ] Issue URLからリポジトリ情報が正しく取得される
- [ ] DRY_RUNモードのため、実際の処理は行わないが、各フェーズのステップが表示される
- [ ] ビルドが成功（SUCCESS）で完了する

**確認項目**:

- [ ] ビルド時間が合理的な範囲内（DRY_RUNで数分以内）
- [ ] エラーログが出力されない
- [ ] EXECUTION_MODEが正しく認識されている

---

#### テストシナリオ: TS-INT-013 - presetジョブの動作確認

**目的**: presetジョブが正常に動作することを検証

**前提条件**:
- 同上

**テスト手順**:

1. `AI_Workflow/infrastructure-as-code/preset`ジョブを開く
2. 「Build with Parameters」をクリック
3. パラメータを入力:
   - `ISSUE_URL`: `https://github.com/tielec/infrastructure-as-code/issues/999`
   - `PRESET`: `quick-fix`
   - `DRY_RUN`: `true`
4. ビルドを実行

**期待結果**:

- [ ] ビルドが成功（SUCCESS）で完了する
- [ ] `EXECUTION_MODE=preset`が設定される
- [ ] `PRESET=quick-fix`が設定される
- [ ] quick-fixプリセットに対応するフェーズ（Implementation → Documentation → Report）のみが実行予定として表示される

---

#### テストシナリオ: TS-INT-014 - single_phaseジョブの動作確認

**目的**: single_phaseジョブが正常に動作することを検証

**前提条件**:
- 同上

**テスト手順**:

1. `AI_Workflow/infrastructure-as-code/single_phase`ジョブを開く
2. 「Build with Parameters」をクリック
3. パラメータを入力:
   - `ISSUE_URL`: `https://github.com/tielec/infrastructure-as-code/issues/999`
   - `START_PHASE`: `implementation`
   - `DRY_RUN`: `true`
4. ビルドを実行

**期待結果**:

- [ ] ビルドが成功（SUCCESS）で完了する
- [ ] `EXECUTION_MODE=single_phase`が設定される
- [ ] `START_PHASE=implementation`が設定される
- [ ] implementationフェーズのみが実行予定として表示される

---

#### テストシナリオ: TS-INT-015 - rollbackジョブの動作確認

**目的**: rollbackジョブが正常に動作することを検証

**前提条件**:
- 同上

**テスト手順**:

1. `AI_Workflow/infrastructure-as-code/rollback`ジョブを開く
2. 「Build with Parameters」をクリック
3. パラメータを入力:
   - `ISSUE_URL`: `https://github.com/tielec/infrastructure-as-code/issues/999`
   - `ROLLBACK_TO_PHASE`: `implementation`
   - `ROLLBACK_TO_STEP`: `revise`
   - `ROLLBACK_REASON`: `テストのための差し戻し`
   - `DRY_RUN`: `true`
4. ビルドを実行

**期待結果**:

- [ ] ビルドが成功（SUCCESS）で完了する
- [ ] `EXECUTION_MODE=rollback`が設定される
- [ ] `ROLLBACK_TO_PHASE=implementation`が設定される
- [ ] `ROLLBACK_TO_STEP=revise`が設定される
- [ ] `ROLLBACK_REASON`が正しく渡される
- [ ] 差し戻し処理が実行予定として表示される

---

#### テストシナリオ: TS-INT-016 - auto_issueジョブの動作確認

**目的**: auto_issueジョブが正常に動作することを検証

**前提条件**:
- 同上

**テスト手順**:

1. `AI_Workflow/infrastructure-as-code/auto_issue`ジョブを開く
2. 「Build with Parameters」をクリック
3. パラメータを入力:
   - `GITHUB_REPOSITORY`: `tielec/infrastructure-as-code`
   - `AUTO_ISSUE_CATEGORY`: `bug`
   - `AUTO_ISSUE_LIMIT`: `5`
   - `AUTO_ISSUE_SIMILARITY_THRESHOLD`: `0.8`
   - `DRY_RUN`: `true`
4. ビルドを実行

**期待結果**:

- [ ] ビルドが成功（SUCCESS）で完了する
- [ ] `EXECUTION_MODE=auto_issue`が設定される
- [ ] `GITHUB_REPOSITORY=tielec/infrastructure-as-code`が設定される
- [ ] `AUTO_ISSUE_CATEGORY=bug`が設定される
- [ ] ISSUE_URLが設定されていない（auto_issueでは不要）
- [ ] 自動Issue作成処理が実行予定として表示される

---

### 2.7 スケーラビリティテスト

#### テストシナリオ: TS-INT-017 - 複数リポジトリでのジョブ生成

**目的**: リポジトリ数が増加した場合、シードジョブが正常に動作し、すべてのジョブが生成されることを検証

**前提条件**:
- `jenkinsManagedRepositories`に10個のリポジトリが登録されている（想定）

**テスト手順**:

1. シードジョブを実行
2. ビルド完了時間を記録
3. 生成されたジョブ数を確認

**期待結果**:

- [ ] シードジョブが成功（SUCCESS）で完了する
- [ ] ビルド時間が5分以内である（非機能要件）
- [ ] 生成されたジョブ数 = リポジトリ数 × 5（例: 10リポジトリ × 5ジョブ = 50ジョブ）
- [ ] すべてのジョブが正常に生成される

**確認項目**:

- [ ] Jenkins CPUが50%以下である（非機能要件）
- [ ] メモリ使用量が異常に増加しない

---

## 3. テストデータ

### 3.1 テスト用GitHub Issue

**Issue #999** (テスト用ダミーIssue):
- URL: `https://github.com/tielec/infrastructure-as-code/issues/999`
- タイトル: `[TEST] テストシナリオ検証用Issue`
- 内容: テスト用の簡単な説明

### 3.2 テスト用リポジトリ

**jenkinsManagedRepositories**に登録されるテスト用リポジトリ:

```yaml
jenkins-managed-repositories:
  infrastructure-as-code:
    httpsUrl: "https://github.com/tielec/infrastructure-as-code.git"
    credentialsId: "github-token"
  ai-workflow-agent:
    httpsUrl: "https://github.com/tielec/ai-workflow-agent.git"
    credentialsId: "github-token"
```

### 3.3 パラメータ入力例

#### all_phases ジョブ

```
ISSUE_URL: https://github.com/tielec/infrastructure-as-code/issues/999
BRANCH_NAME: （空欄）
AGENT_MODE: auto
DRY_RUN: true
SKIP_REVIEW: false
FORCE_RESET: false
MAX_RETRIES: 3
CLEANUP_ON_COMPLETE_FORCE: false
GIT_COMMIT_USER_NAME: AI Workflow Bot
GIT_COMMIT_USER_EMAIL: ai-workflow@example.com
AWS_ACCESS_KEY_ID: （空欄）
AWS_SECRET_ACCESS_KEY: （空欄）
AWS_SESSION_TOKEN: （空欄）
COST_LIMIT_USD: 5.0
LOG_LEVEL: INFO
```

#### preset ジョブ

```
ISSUE_URL: https://github.com/tielec/infrastructure-as-code/issues/999
PRESET: quick-fix
DRY_RUN: true
（他のパラメータはall_phasesと同じ）
```

#### single_phase ジョブ

```
ISSUE_URL: https://github.com/tielec/infrastructure-as-code/issues/999
START_PHASE: implementation
DRY_RUN: true
（他のパラメータはall_phasesと同じ、ただしFORCE_RESETとCLEANUP_ON_COMPLETE_FORCEは除外）
```

#### rollback ジョブ

```
ISSUE_URL: https://github.com/tielec/infrastructure-as-code/issues/999
ROLLBACK_TO_PHASE: implementation
ROLLBACK_TO_STEP: revise
ROLLBACK_REASON: テストのための差し戻し
ROLLBACK_REASON_FILE: （空欄）
DRY_RUN: true
（SKIP_REVIEW、FORCE_RESET、MAX_RETRIES、CLEANUP_ON_COMPLETE_FORCEは除外）
```

#### auto_issue ジョブ

```
GITHUB_REPOSITORY: tielec/infrastructure-as-code
AUTO_ISSUE_CATEGORY: bug
AUTO_ISSUE_LIMIT: 5
AUTO_ISSUE_SIMILARITY_THRESHOLD: 0.8
AGENT_MODE: auto
DRY_RUN: true
COST_LIMIT_USD: 5.0
LOG_LEVEL: INFO
（ISSUE_URL、BRANCH_NAME、Git設定、AWS認証情報は除外）
```

---

## 4. テスト環境要件

### 4.1 Jenkins環境

- **Jenkins Version**: 2.426.1以上
- **必須プラグイン**:
  - Job DSL Plugin（最新版）
  - Pipeline Plugin
  - Git Plugin
  - Credentials Plugin

### 4.2 外部サービス

- **GitHub**:
  - テスト用リポジトリへのアクセス権限
  - GitHub Token（`github-token`クレデンシャル）

- **ai-workflow-agent リポジトリ**:
  - `main`ブランチにJenkinsfileが存在すること
  - JenkinsfileがEXECUTION_MODEパラメータを受け取る実装になっていること

### 4.3 テスト実行環境

- **推奨**: 開発環境（dev）でのテスト実行
- **本番環境**: 開発環境でのテスト完了後に実施
- **テスト実行者**: Jenkins管理者権限を持つユーザー

### 4.4 モック/スタブ

**不要**: 実際のJenkins環境で統合テストを実施するため、モック/スタブは使用しない

**DRY_RUNモード**: 実際のAPI呼び出しを行わずに動作確認を行うため、外部サービスへの影響を最小化

---

## 5. テスト実行チェックリスト

### 5.1 事前準備

- [ ] Jenkins環境が正常に動作している
- [ ] 5つのJob DSLファイルが作成され、`jenkins/jobs/dsl/ai-workflow/`に配置されている
- [ ] `job-config.yaml`に5つの新しいジョブ定義が追加されている
- [ ] `folder-config.yaml`に動的フォルダルールが追加されている
- [ ] 既存の`ai_workflow_orchestrator.groovy`にDeprecatedコメントが追加されている
- [ ] `jenkinsManagedRepositories`に最低1つのリポジトリが登録されている
- [ ] GitHub Token（`github-token`）が設定されている

### 5.2 シードジョブ実行テスト

- [ ] TS-INT-001: シードジョブによるジョブ生成
- [ ] TS-INT-002: リポジトリ別フォルダ構成の検証

### 5.3 パラメータ定義テスト

- [ ] TS-INT-003: all_phasesジョブのパラメータ検証
- [ ] TS-INT-004: presetジョブのパラメータ検証
- [ ] TS-INT-005: single_phaseジョブのパラメータ検証
- [ ] TS-INT-006: rollbackジョブのパラメータ検証
- [ ] TS-INT-007: auto_issueジョブのパラメータ検証

### 5.4 EXECUTION_MODE設定テスト

- [ ] TS-INT-008: all_phasesジョブのEXECUTION_MODE検証
- [ ] TS-INT-009: 全ジョブのEXECUTION_MODE一斉検証

### 5.5 Jenkinsfile連携テスト

- [ ] TS-INT-010: Jenkinsfile参照設定の検証

### 5.6 Deprecated化テスト

- [ ] TS-INT-011: 既存ジョブのDeprecated表示検証

### 5.7 エンドツーエンドテスト

- [ ] TS-INT-012: 実際のIssue URLでの動作確認（all_phases）
- [ ] TS-INT-013: presetジョブの動作確認
- [ ] TS-INT-014: single_phaseジョブの動作確認
- [ ] TS-INT-015: rollbackジョブの動作確認
- [ ] TS-INT-016: auto_issueジョブの動作確認

### 5.8 スケーラビリティテスト

- [ ] TS-INT-017: 複数リポジトリでのジョブ生成

---

## 6. 品質ゲートチェック

### Phase 3品質ゲート（必須要件）

- [x] **Phase 2の戦略に沿ったテストシナリオである**: INTEGRATION_ONLYに基づく統合テストシナリオのみを作成
- [x] **主要な正常系がカバーされている**: 5つのジョブそれぞれの生成、パラメータ表示、EXECUTION_MODE設定、DRY_RUN実行をカバー
- [x] **主要な異常系がカバーされている**: DSLファイルの構文エラー、jenkinsManagedRepositoriesの空配列、不要なパラメータの非表示検証を含む
- [x] **期待結果が明確である**: 各テストシナリオで具体的な期待結果（チェックリスト形式）を記載

**判定**: ✅ 全ての品質ゲートをクリア

---

## 7. テスト結果記録テンプレート

### テスト実行記録

| テストID | テストシナリオ名 | 実行日 | 実行者 | 結果 | 備考 |
|---------|--------------|--------|--------|------|------|
| TS-INT-001 | シードジョブによるジョブ生成 | YYYY-MM-DD | 担当者名 | ✅/❌ | |
| TS-INT-002 | リポジトリ別フォルダ構成の検証 | YYYY-MM-DD | 担当者名 | ✅/❌ | |
| TS-INT-003 | all_phasesジョブのパラメータ検証 | YYYY-MM-DD | 担当者名 | ✅/❌ | |
| TS-INT-004 | presetジョブのパラメータ検証 | YYYY-MM-DD | 担当者名 | ✅/❌ | |
| TS-INT-005 | single_phaseジョブのパラメータ検証 | YYYY-MM-DD | 担当者名 | ✅/❌ | |
| TS-INT-006 | rollbackジョブのパラメータ検証 | YYYY-MM-DD | 担当者名 | ✅/❌ | |
| TS-INT-007 | auto_issueジョブのパラメータ検証 | YYYY-MM-DD | 担当者名 | ✅/❌ | |
| TS-INT-008 | all_phasesジョブのEXECUTION_MODE検証 | YYYY-MM-DD | 担当者名 | ✅/❌ | |
| TS-INT-009 | 全ジョブのEXECUTION_MODE一斉検証 | YYYY-MM-DD | 担当者名 | ✅/❌ | |
| TS-INT-010 | Jenkinsfile参照設定の検証 | YYYY-MM-DD | 担当者名 | ✅/❌ | |
| TS-INT-011 | 既存ジョブのDeprecated表示検証 | YYYY-MM-DD | 担当者名 | ✅/❌ | |
| TS-INT-012 | all_phasesジョブの動作確認 | YYYY-MM-DD | 担当者名 | ✅/❌ | |
| TS-INT-013 | presetジョブの動作確認 | YYYY-MM-DD | 担当者名 | ✅/❌ | |
| TS-INT-014 | single_phaseジョブの動作確認 | YYYY-MM-DD | 担当者名 | ✅/❌ | |
| TS-INT-015 | rollbackジョブの動作確認 | YYYY-MM-DD | 担当者名 | ✅/❌ | |
| TS-INT-016 | auto_issueジョブの動作確認 | YYYY-MM-DD | 担当者名 | ✅/❌ | |
| TS-INT-017 | 複数リポジトリでのジョブ生成 | YYYY-MM-DD | 担当者名 | ✅/❌ | |

### テスト結果サマリー

- **総テストケース数**: 17
- **成功**: X件
- **失敗**: X件
- **未実施**: X件
- **成功率**: X%

### 発見された問題

| 問題ID | 問題内容 | 重要度 | 対応状況 | 担当者 |
|--------|---------|--------|---------|--------|
| BUG-001 | （問題の説明） | High/Medium/Low | Open/Fixed/Closed | 担当者名 |

---

## 8. リスクと軽減策

### リスク1: パラメータ数の不一致

**影響度**: 高
**確率**: 中

**軽減策**:
- TS-INT-003〜007で各ジョブのパラメータ数を厳密に検証
- Issue本文のパラメータ対応表と照合
- パラメータ画面のスクリーンショットを撮影して記録

### リスク2: EXECUTION_MODEが正しく渡されない

**影響度**: 高
**確率**: 低

**軽減策**:
- TS-INT-008〜009でEXECUTION_MODEの設定を検証
- ビルドログで実際の値を確認
- 全5つのジョブで一斉検証

### リスク3: リポジトリ別フォルダが生成されない

**影響度**: 高
**確率**: 低

**軽減策**:
- TS-INT-002でフォルダ構造を詳細に検証
- 複数リポジトリでのテスト（TS-INT-017）
- `jenkinsManagedRepositories`の事前確認

### リスク4: Jenkinsfileとの連携エラー

**影響度**: 高
**確率**: 低

**軽減策**:
- TS-INT-010でJenkinsfile参照設定を確認
- TS-INT-012〜016でDRY_RUNモードでの実行テスト
- ai-workflow-agentリポジトリのJenkinsfileが最新であることを確認

---

## 9. 成功基準

このテストシナリオは、以下の条件を満たした場合に成功とみなされます：

### 機能要件

- [ ] **ジョブ生成**: 5つのジョブ（all_phases、preset、single_phase、rollback、auto_issue）が正しく生成される
- [ ] **フォルダ構造**: リポジトリ別フォルダ構造（AI_Workflow/{repository-name}/各ジョブ）が実現されている
- [ ] **パラメータ定義**: 各ジョブのパラメータがIssue本文の対応表通りに実装されている
- [ ] **パラメータ数**: パラメータ数が正しい（all_phases: 14、preset: 15、single_phase: 13、rollback: 12、auto_issue: 8）
- [ ] **EXECUTION_MODE**: 各ジョブがEXECUTION_MODEを固定値として正しく渡している

### 非機能要件

- [ ] **シードジョブ実行時間**: 5分以内
- [ ] **後方互換性**: 既存の`ai_workflow_orchestrator`ジョブへの影響がない（deprecated扱い）
- [ ] **DRY_RUN動作**: すべてのジョブでDRY_RUN実行が成功している

### 品質要件

- [ ] **全テストケース**: 17個すべてのテストケースが実行され、成功している
- [ ] **品質ゲート**: Phase 3の4つの品質ゲートをすべてクリアしている
- [ ] **問題なし**: ブロッカーレベルの問題が発見されていない

---

## 10. 次のステップ

このテストシナリオが承認されたら、以下の順序でテストを実施します：

1. **事前準備**: テスト環境の構築、テストデータの準備
2. **シードジョブ実行テスト**: TS-INT-001〜002
3. **パラメータ定義テスト**: TS-INT-003〜007
4. **EXECUTION_MODE設定テスト**: TS-INT-008〜009
5. **Jenkinsfile連携テスト**: TS-INT-010
6. **Deprecated化テスト**: TS-INT-011
7. **エンドツーエンドテスト**: TS-INT-012〜016
8. **スケーラビリティテスト**: TS-INT-017
9. **テスト結果の記録と報告**

---

## 11. 参考情報

### 関連ドキュメント

- **Planning Document**: `.ai-workflow/issue-453/00_planning/output/planning.md`
- **Requirements Document**: `.ai-workflow/issue-453/01_requirements/output/requirements.md`
- **Design Document**: `.ai-workflow/issue-453/02_design/output/design.md`

### 参考ファイル

- **既存実装**: `jenkins/jobs/dsl/ai-workflow/ai_workflow_orchestrator.groovy`
- **参考実装**: `jenkins/jobs/dsl/code-quality-checker/code_quality_pr_complexity_analyzer_job.groovy`
- **設定ファイル**: `jenkins/jobs/pipeline/_seed/job-creator/job-config.yaml`
- **設定ファイル**: `jenkins/jobs/pipeline/_seed/job-creator/folder-config.yaml`

### 外部リンク

- [Jenkins Job DSL Plugin Documentation](https://plugins.jenkins.io/job-dsl/)
- [Jenkins Pipeline Documentation](https://www.jenkins.io/doc/book/pipeline/)
- [Jenkins Best Practices](https://www.jenkins.io/doc/book/using/best-practices/)

---

**テストシナリオ作成者**: AI Workflow Agent
**レビュー待ち**: Phase 3 (Test Scenario) Review
