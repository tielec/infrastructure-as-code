# テストシナリオ: AI Workflow用シードジョブの設定ファイル分離

## Issue情報

- **Issue番号**: #479
- **タイトル**: [Feature] AI Workflow用シードジョブの設定ファイル分離
- **URL**: https://github.com/tielec/infrastructure-as-code/issues/479
- **関連Issue**: #477 ([Feature] AI Workflow用のシードジョブを分離)
- **作成日**: 2025年1月19日

---

## 0. Planning Documentの確認

### テスト戦略

Planning Document（planning.md）より、以下のテスト戦略が策定されています：

- **テスト戦略**: INTEGRATION_ONLY（設定ファイル中心のため単体テスト不要）
- **テストコード戦略**: 該当なし（Job DSLプラグインによる自動検証を活用）

### テスト戦略の判断根拠

**INTEGRATION_ONLYが適切な理由**:
- **設定ファイル中心**: YAMLファイルとJenkinsfileの修正のみ
- **ロジックなし**: 複雑なビジネスロジックや計算処理が存在しない
- **統合確認が重要**: 2つのシードジョブが正しく独立して動作するかの確認が主要な検証ポイント
- **Jenkins環境での実行確認**: 設定ファイルの文法チェックだけでなく、実際のジョブ作成が成功するかの確認が必須

### 品質ゲート（Phase 3）

Planning Documentで定義された以下の品質ゲートを満たすことを確認します：

- [ ] **Phase 2の戦略に沿ったテストシナリオである**（INTEGRATION_ONLY）
- [ ] **主要な正常系がカバーされている**
- [ ] **主要な異常系がカバーされている**
- [ ] **期待結果が明確である**

---

## 1. テスト戦略サマリー

### 選択されたテスト戦略
**INTEGRATION_ONLY** - 統合テストのみ

### テスト対象の範囲

#### 新規作成ファイル
1. `jenkins/jobs/pipeline/_seed/ai-workflow-job-creator/job-config.yaml`
2. `jenkins/jobs/pipeline/_seed/ai-workflow-job-creator/folder-config.yaml`

#### 修正ファイル
1. `jenkins/jobs/pipeline/_seed/ai-workflow-job-creator/Jenkinsfile`
2. `jenkins/jobs/pipeline/_seed/job-creator/job-config.yaml`
3. `jenkins/jobs/pipeline/_seed/job-creator/folder-config.yaml`
4. `jenkins/jobs/pipeline/_seed/job-creator/Jenkinsfile`

### テストの目的

1. **設定ファイル分離の検証**: AI Workflow専用設定ファイルが正しく作成され、参照されることを確認
2. **独立動作の検証**: 両シードジョブが独立して正常に動作することを確認
3. **除外ロジック削除の検証**: job-creatorからAI Workflow除外処理が削除され、コードが簡素化されていることを確認
4. **並行実行の検証**: 両シードジョブが並行実行しても競合しないことを確認

---

## 2. Integrationテストシナリオ

### シナリオ1: ai-workflow-job-creator の独立動作確認（正常系）

#### 目的
AI Workflow専用設定ファイルを使用して、ai-workflow-job-creatorが独立して正常に動作することを検証する。

#### 前提条件
- 新規作成ファイルが存在する
  - `jenkins/jobs/pipeline/_seed/ai-workflow-job-creator/job-config.yaml`
  - `jenkins/jobs/pipeline/_seed/ai-workflow-job-creator/folder-config.yaml`
- `ai-workflow-job-creator/Jenkinsfile` のパス参照が更新されている
- Jenkins環境が稼働している
- GitHub認証情報が設定されている（`github-app-credentials`）

#### テスト手順

**Step 1: 設定ファイルの検証**
1. `ai-workflow-job-creator/job-config.yaml` が存在することを確認
2. AI Workflow関連の5ジョブ定義が含まれることを確認
   - `ai_workflow_all_phases_job`
   - `ai_workflow_preset_job`
   - `ai_workflow_single_phase_job`
   - `ai_workflow_rollback_job`
   - `ai_workflow_auto_issue_job`
3. `ai-workflow-job-creator/folder-config.yaml` が存在することを確認
4. AI_Workflowフォルダ定義（11個）が含まれることを確認
   - `AI_Workflow`（親フォルダ）
   - `AI_Workflow/develop`
   - `AI_Workflow/stable-1` ～ `AI_Workflow/stable-9`

**Step 2: Jenkinsfileパス参照の確認**
1. `ai-workflow-job-creator/Jenkinsfile` を確認
2. `JOB_CONFIG_PATH` が `jenkins/jobs/pipeline/_seed/ai-workflow-job-creator/job-config.yaml` を指していることを確認
3. `FOLDER_CONFIG_PATH` が `jenkins/jobs/pipeline/_seed/ai-workflow-job-creator/folder-config.yaml` を指していることを確認

**Step 3: シードジョブの実行**
1. Jenkins UIで `Admin_Jobs/ai-workflow-job-creator` を開く
2. "Build Now" をクリックしてジョブを実行
3. ビルドログを確認

**Step 4: ジョブ作成結果の確認**
1. `AI_Workflow` フォルダが作成されていることを確認
2. 以下のサブフォルダが作成されていることを確認
   - `AI_Workflow/develop`
   - `AI_Workflow/stable-1` ～ `AI_Workflow/stable-9`
3. 各フォルダ内に5つのジョブが作成されていることを確認
   - `all_phases`
   - `preset`
   - `single_phase`
   - `rollback`
   - `auto_issue`

**Step 5: ジョブ設定の確認**
1. いずれか1つのジョブ（例: `AI_Workflow/develop/all_phases`）を開く
2. ジョブのパラメータ定義が正しいことを確認
3. Jenkinsfileパスが `Jenkinsfile` になっていることを確認（ai-workflow-agentリポジトリのJenkinsfile）

#### 期待結果

**設定ファイル**:
- ✅ `ai-workflow-job-creator/job-config.yaml` に5ジョブ定義が含まれる
- ✅ `ai-workflow-job-creator/folder-config.yaml` に11フォルダ定義が含まれる
- ✅ YAML構文エラーがない

**Jenkinsfile**:
- ✅ パス参照が専用設定ファイルを指している
- ✅ Groovy構文エラーがない

**シードジョブ実行**:
- ✅ ビルドが成功（緑色）
- ✅ エラーログがない
- ✅ 実行時間が1分以内

**作成されたリソース**:
- ✅ AI_Workflowフォルダ（11個）が作成される
- ✅ AI Workflow関連ジョブ（5ジョブ × 11フォルダ = 55ジョブ）が作成される
- ✅ ジョブパラメータが正しく設定される

#### 確認項目チェックリスト

- [ ] 設定ファイルにYAML構文エラーがない
- [ ] JenkinsfileにGroovy構文エラーがない
- [ ] シードジョブが正常に実行される
- [ ] AI_Workflowフォルダ（11個）が作成される
- [ ] AI Workflowジョブ（5種類）が各フォルダに作成される
- [ ] ジョブパラメータが正しく設定される
- [ ] ビルドログにエラーがない

---

### シナリオ2: job-creator の除外ロジック削除確認（正常系）

#### 目的
job-creatorからAI Workflow関連の除外ロジックが削除され、一般ジョブのみが正常に作成されることを検証する。

#### 前提条件
- `job-creator/job-config.yaml` からAI Workflow定義が削除されている
- `job-creator/folder-config.yaml` からAI_Workflowフォルダ定義が削除されている
- `job-creator/Jenkinsfile` からAI Workflow除外ロジック（行127-133）が削除されている
- Jenkins環境が稼働している

#### テスト手順

**Step 1: 設定ファイルの検証**
1. `job-creator/job-config.yaml` を確認
2. AI Workflow関連ジョブ定義が存在しないことを確認
   - `ai_workflow_all_phases_job`
   - `ai_workflow_preset_job`
   - `ai_workflow_single_phase_job`
   - `ai_workflow_rollback_job`
   - `ai_workflow_auto_issue_job`
3. 一般ジョブ定義は残っていることを確認（例: `account_self_activation_job`, `admin_backup_config_job` 等）
4. `job-creator/folder-config.yaml` を確認
5. AI_Workflowフォルダ定義が存在しないことを確認
6. 一般フォルダ定義は残っていることを確認（例: `Admin_Jobs`, `Code_Quality_Checker` 等）

**Step 2: Jenkinsfileの検証**
1. `job-creator/Jenkinsfile` を確認
2. 以下のコードブロックが削除されていることを確認
   ```groovy
   // AI Workflow関連ジョブを除外
   def excludedJobPrefixes = ['ai_workflow_']
   def jobsToProcess = jobConfig['jenkins-jobs'].findAll { jobKey, jobDef ->
       !excludedJobPrefixes.any { prefix -> jobKey.startsWith(prefix) }
   }
   echo "AI Workflow jobs excluded: ${jobConfig['jenkins-jobs'].size() - jobsToProcess.size()}"
   ```
3. 代わりに、シンプルな処理になっていることを確認
   ```groovy
   // 各ジョブのDSLファイルを追加
   jobConfig['jenkins-jobs'].each { jobKey, jobDef ->
       if (jobDef.dslfile) {
           dslFiles.add(jobDef.dslfile)
       }
   }
   ```

**Step 3: シードジョブの実行**
1. Jenkins UIで `Admin_Jobs/job-creator` を開く
2. "Build Now" をクリックしてジョブを実行
3. ビルドログを確認

**Step 4: ジョブ作成結果の確認**
1. 一般ジョブが正常に作成されることを確認（例: `Admin_Jobs/Backup_Config`）
2. AI Workflowジョブが作成されないことを確認
   - `AI_Workflow/develop/all_phases` が存在しない（または以前のバージョンのまま）
3. ビルドログに「AI Workflow jobs excluded」メッセージが出力されないことを確認

**Step 5: コードの簡素化確認**
1. Jenkinsfileの行数が削減されていることを確認
2. 除外ロジック関連のコメントが削除されていることを確認

#### 期待結果

**設定ファイル**:
- ✅ `job-creator/job-config.yaml` にAI Workflow定義が存在しない
- ✅ `job-creator/folder-config.yaml` にAI_Workflowフォルダ定義が存在しない
- ✅ 一般ジョブ・フォルダ定義は残っている
- ✅ YAML構文エラーがない

**Jenkinsfile**:
- ✅ AI Workflow除外ロジックが削除されている
- ✅ コードが簡素化されている
- ✅ Groovy構文エラーがない

**シードジョブ実行**:
- ✅ ビルドが成功（緑色）
- ✅ エラーログがない
- ✅ 一般ジョブが正常に作成される
- ✅ AI Workflowジョブが作成されない

**ビルドログ**:
- ✅ 「AI Workflow jobs excluded」メッセージが出力されない
- ✅ ジョブカウントが正確（除外なし）

#### 確認項目チェックリスト

- [ ] job-config.yaml にAI Workflow定義が存在しない
- [ ] folder-config.yaml にAI_Workflowフォルダ定義が存在しない
- [ ] Jenkinsfileから除外ロジックが削除されている
- [ ] コードが簡素化されている
- [ ] シードジョブが正常に実行される
- [ ] 一般ジョブが正常に作成される
- [ ] AI Workflowジョブが作成されない
- [ ] ビルドログにエラーがない

---

### シナリオ3: 両シードジョブの並行実行確認（正常系）

#### 目的
job-creatorとai-workflow-job-creatorを並行実行しても競合せず、両方のジョブが正常に完了することを検証する。

#### 前提条件
- シナリオ1とシナリオ2が成功している
- 両方のシードジョブが独立して動作することが確認済み
- Jenkins環境が稼働している

#### テスト手順

**Step 1: 並行実行の開始**
1. Jenkins UIで2つのブラウザタブを開く
2. タブ1で `Admin_Jobs/job-creator` を開く
3. タブ2で `Admin_Jobs/ai-workflow-job-creator` を開く
4. ほぼ同時に両方のジョブで "Build Now" をクリック

**Step 2: 実行状態の監視**
1. 両方のジョブが同時に実行されることを確認
2. 各ジョブのビルドログをリアルタイムで確認
3. エラーや警告が出力されないことを確認

**Step 3: 実行完了の確認**
1. 両方のジョブが正常に完了することを確認（緑色）
2. 実行時間を記録

**Step 4: ジョブ・フォルダの整合性確認**
1. 全ジョブが正常に作成されていることを確認
   - 一般ジョブ（job-creatorが作成）
   - AI Workflowジョブ（ai-workflow-job-creatorが作成）
2. フォルダ構造が正しいことを確認
   - 一般フォルダ（job-creatorが作成）
   - AI_Workflowフォルダ（ai-workflow-job-creatorが作成）
3. ジョブやフォルダの重複がないことを確認
4. ジョブやフォルダの欠落がないことを確認

**Step 5: ビルドログの確認**
1. job-creatorのビルドログに競合エラーがないことを確認
2. ai-workflow-job-creatorのビルドログに競合エラーがないことを確認

#### 期待結果

**並行実行**:
- ✅ 両シードジョブが同時に実行される
- ✅ 実行中に競合エラーが発生しない
- ✅ 両方のジョブが正常に完了（緑色）

**ジョブ・フォルダの整合性**:
- ✅ 一般ジョブが正常に作成される（job-creator）
- ✅ AI Workflowジョブが正常に作成される（ai-workflow-job-creator）
- ✅ ジョブの重複がない
- ✅ ジョブの欠落がない
- ✅ フォルダ構造が正しい

**パフォーマンス**:
- ✅ 各ジョブの実行時間が1分以内
- ✅ 並行実行による遅延が発生しない

#### 確認項目チェックリスト

- [ ] 両シードジョブが同時に実行される
- [ ] job-creatorが正常に完了する
- [ ] ai-workflow-job-creatorが正常に完了する
- [ ] 競合エラーが発生しない
- [ ] 一般ジョブが正常に作成される
- [ ] AI Workflowジョブが正常に作成される
- [ ] ジョブ・フォルダの重複がない
- [ ] ジョブ・フォルダの欠落がない

---

### シナリオ4: 設定ファイル構文エラーの検出（異常系）

#### 目的
設定ファイルにYAML構文エラーがある場合、シードジョブが適切にエラーを検出し、失敗することを検証する。

#### 前提条件
- 正常な設定ファイルが存在する
- Jenkins環境が稼働している

#### テスト手順

**Step 1: YAML構文エラーの挿入**
1. `ai-workflow-job-creator/job-config.yaml` のバックアップを作成
2. 意図的にYAML構文エラーを挿入（例: インデント不正、クォート不一致）
   ```yaml
   # 誤った構文例
   ai_workflow_all_phases_job:
     name: 'all_phases'
       displayName: 'All Phases Execution'  # インデントエラー
   ```

**Step 2: シードジョブの実行**
1. Jenkins UIで `Admin_Jobs/ai-workflow-job-creator` を実行
2. ビルドログを確認

**Step 3: エラーメッセージの確認**
1. ジョブが失敗（赤色）することを確認
2. ビルドログにYAML構文エラーのメッセージが出力されることを確認
3. エラーメッセージが明確であることを確認

**Step 4: 修正と再実行**
1. バックアップから正常な設定ファイルを復元
2. シードジョブを再実行
3. 正常に完了することを確認

#### 期待結果

**エラー検出**:
- ✅ シードジョブが失敗（赤色）
- ✅ YAML構文エラーのメッセージが出力される
- ✅ エラー箇所が特定できる

**復旧**:
- ✅ 正常な設定ファイルに戻すと成功する
- ✅ ジョブが正常に作成される

#### 確認項目チェックリスト

- [ ] YAML構文エラーが検出される
- [ ] シードジョブが失敗する
- [ ] エラーメッセージが明確
- [ ] 正常な設定ファイルで復旧できる

---

### シナリオ5: 設定ファイル不在の検出（異常系）

#### 目的
設定ファイルが存在しない場合、シードジョブが適切にエラーを検出し、失敗することを検証する。

#### 前提条件
- 正常な設定ファイルが存在する
- Jenkins環境が稼働している

#### テスト手順

**Step 1: 設定ファイルの一時移動**
1. `ai-workflow-job-creator/job-config.yaml` を一時的にリネーム
   - 例: `job-config.yaml.backup`

**Step 2: シードジョブの実行**
1. Jenkins UIで `Admin_Jobs/ai-workflow-job-creator` を実行
2. ビルドログを確認

**Step 3: エラーメッセージの確認**
1. ジョブが失敗（赤色）することを確認
2. ビルドログに「Job configuration file not found」エラーが出力されることを確認
3. ファイルパスが正確に表示されることを確認

**Step 4: 修正と再実行**
1. ファイルを元の名前に戻す
   - `job-config.yaml.backup` → `job-config.yaml`
2. シードジョブを再実行
3. 正常に完了することを確認

#### 期待結果

**エラー検出**:
- ✅ シードジョブが失敗（赤色）
- ✅ 「Job configuration file not found」エラーが出力される
- ✅ 不在ファイルのパスが表示される

**復旧**:
- ✅ ファイルを戻すと成功する
- ✅ ジョブが正常に作成される

#### 確認項目チェックリスト

- [ ] 設定ファイル不在が検出される
- [ ] シードジョブが失敗する
- [ ] エラーメッセージが明確
- [ ] ファイルパスが表示される
- [ ] ファイルを戻すと復旧できる

---

### シナリオ6: Jenkinsfileパス参照エラーの検出（異常系）

#### 目的
Jenkinsfileのパス参照が誤っている場合、シードジョブが適切にエラーを検出することを検証する。

#### 前提条件
- 正常な設定ファイルが存在する
- Jenkins環境が稼働している

#### テスト手順

**Step 1: パス参照の一時変更**
1. `ai-workflow-job-creator/Jenkinsfile` のバックアップを作成
2. `JOB_CONFIG_PATH` を存在しないパスに変更
   ```groovy
   environment {
       JOB_CONFIG_PATH = 'jenkins/jobs/pipeline/_seed/ai-workflow-job-creator/INVALID_PATH.yaml'
       FOLDER_CONFIG_PATH = 'jenkins/jobs/pipeline/_seed/ai-workflow-job-creator/folder-config.yaml'
       FOLDERS_DSL_PATH = 'jenkins/jobs/dsl/folders.groovy'
   }
   ```

**Step 2: シードジョブの実行**
1. Jenkins UIで `Admin_Jobs/ai-workflow-job-creator` を実行
2. ビルドログを確認

**Step 3: エラーメッセージの確認**
1. ジョブが失敗（赤色）することを確認
2. ビルドログに「Job configuration file not found」エラーが出力されることを確認
3. 誤ったパスが表示されることを確認

**Step 4: 修正と再実行**
1. バックアップから正常なJenkinsfileを復元
2. シードジョブを再実行
3. 正常に完了することを確認

#### 期待結果

**エラー検出**:
- ✅ シードジョブが失敗（赤色）
- ✅ 「Job configuration file not found」エラーが出力される
- ✅ 誤ったパスが表示される

**復旧**:
- ✅ 正常なパスに戻すと成功する
- ✅ ジョブが正常に作成される

#### 確認項目チェックリスト

- [ ] パス参照エラーが検出される
- [ ] シードジョブが失敗する
- [ ] エラーメッセージが明確
- [ ] 誤ったパスが表示される
- [ ] 正常なパスで復旧できる

---

## 3. テストデータ

### AI Workflow関連ジョブ定義（5個）

```yaml
ai_workflow_all_phases_job:
  name: 'all_phases'
  displayName: 'All Phases Execution'
  dslfile: jenkins/jobs/dsl/ai-workflow/ai_workflow_all_phases_job.groovy
  jenkinsfile: Jenkinsfile
  skipJenkinsfileValidation: true

ai_workflow_preset_job:
  name: 'preset'
  displayName: 'Preset Execution'
  dslfile: jenkins/jobs/dsl/ai-workflow/ai_workflow_preset_job.groovy
  jenkinsfile: Jenkinsfile
  skipJenkinsfileValidation: true

ai_workflow_single_phase_job:
  name: 'single_phase'
  displayName: 'Single Phase Execution'
  dslfile: jenkins/jobs/dsl/ai-workflow/ai_workflow_single_phase_job.groovy
  jenkinsfile: Jenkinsfile
  skipJenkinsfileValidation: true

ai_workflow_rollback_job:
  name: 'rollback'
  displayName: 'Rollback Execution'
  dslfile: jenkins/jobs/dsl/ai-workflow/ai_workflow_rollback_job.groovy
  jenkinsfile: Jenkinsfile
  skipJenkinsfileValidation: true

ai_workflow_auto_issue_job:
  name: 'auto_issue'
  displayName: 'Auto Issue Creation'
  dslfile: jenkins/jobs/dsl/ai-workflow/ai_workflow_auto_issue_job.groovy
  jenkinsfile: Jenkinsfile
  skipJenkinsfileValidation: true
```

### AI_Workflowフォルダ定義（11個）

```yaml
folders:
  - path: "AI_Workflow"
    displayName: "50. [AI] AI駆動開発"
    description: "AI駆動開発自動化ワークフローのジョブを管理"

  - path: "AI_Workflow/develop"
    displayName: "AI Workflow Executor - Develop"
    description: "developブランチ用のワークフロー実行環境"

  - path: "AI_Workflow/stable-1"
    displayName: "AI Workflow Executor - Stable 1"
    description: "mainブランチ用のワークフロー実行環境（Stable 1）"

  # ... stable-2 から stable-9 まで同様
```

### 異常系テストデータ

#### YAML構文エラー例

```yaml
# インデントエラー
ai_workflow_all_phases_job:
  name: 'all_phases'
    displayName: 'All Phases Execution'  # インデント不正

# クォート不一致
ai_workflow_preset_job:
  name: 'preset"  # クォート不一致
  displayName: 'Preset Execution'
```

#### パス参照エラー例

```groovy
// 存在しないパス
environment {
    JOB_CONFIG_PATH = 'jenkins/jobs/pipeline/_seed/INVALID/job-config.yaml'
    FOLDER_CONFIG_PATH = 'jenkins/jobs/pipeline/_seed/INVALID/folder-config.yaml'
    FOLDERS_DSL_PATH = 'jenkins/jobs/dsl/folders.groovy'
}
```

---

## 4. テスト環境要件

### Jenkins環境

- **バージョン**: Jenkins LTS（最新版推奨）
- **必須プラグイン**:
  - Job DSL Plugin
  - Pipeline Plugin
  - Git Plugin
  - Credentials Plugin
  - Folders Plugin

### 認証情報

- **GitHub認証情報**: `github-app-credentials`
  - GitHub App認証情報（ai-workflow-agentリポジトリへのアクセス用）

### 実行権限

- シードジョブは管理者権限で実行される
- `Admin_Jobs` フォルダ配下に配置

### ネットワーク

- GitHubへのHTTPS接続が可能であること
- ai-workflow-agentリポジトリへのアクセスが可能であること

---

## 5. テスト実施計画

### 実施順序

1. **シナリオ1**: ai-workflow-job-creator の独立動作確認（正常系）
2. **シナリオ2**: job-creator の除外ロジック削除確認（正常系）
3. **シナリオ3**: 両シードジョブの並行実行確認（正常系）
4. **シナリオ4**: 設定ファイル構文エラーの検出（異常系）
5. **シナリオ5**: 設定ファイル不在の検出（異常系）
6. **シナリオ6**: Jenkinsfileパス参照エラーの検出（異常系）

### 見積もり時間

| シナリオ | 見積もり時間 |
|---------|------------|
| シナリオ1 | 30分 |
| シナリオ2 | 30分 |
| シナリオ3 | 20分 |
| シナリオ4 | 15分 |
| シナリオ5 | 15分 |
| シナリオ6 | 15分 |
| **合計** | **2時間5分** |

### 実施タイミング

- **Phase 6: テスト実行** で実施
- 実装完了後、すべてのシナリオを順次実行

---

## 6. 成功基準

### 正常系シナリオ

- [ ] シナリオ1: ai-workflow-job-creatorが独立して正常に動作する
- [ ] シナリオ2: job-creatorがAI Workflow除外なしで正常に動作する
- [ ] シナリオ3: 両シードジョブが並行実行で競合しない

### 異常系シナリオ

- [ ] シナリオ4: YAML構文エラーが適切に検出される
- [ ] シナリオ5: 設定ファイル不在が適切に検出される
- [ ] シナリオ6: パス参照エラーが適切に検出される

### 品質ゲート（Phase 3）

- [x] **Phase 2の戦略に沿ったテストシナリオである**（INTEGRATION_ONLY）
- [x] **主要な正常系がカバーされている**（シナリオ1, 2, 3）
- [x] **主要な異常系がカバーされている**（シナリオ4, 5, 6）
- [x] **期待結果が明確である**（各シナリオに期待結果を記載）

---

## 7. テスト結果記録フォーマット

### シナリオごとの記録

各シナリオの実行結果は以下の形式で記録します：

```markdown
### シナリオX: [シナリオ名]

- **実施日時**: YYYY-MM-DD HH:MM
- **実施者**: [名前]
- **結果**: ✅ 成功 / ❌ 失敗
- **実行時間**: XX分XX秒
- **確認項目**:
  - [ ] 確認項目1
  - [ ] 確認項目2
  - ...
- **備考**: [特記事項があれば記載]
- **スクリーンショット**: [必要に応じて添付]
```

### テスト結果サマリー

```markdown
## テスト結果サマリー

- **実施日**: YYYY-MM-DD
- **実施者**: [名前]
- **総シナリオ数**: 6
- **成功**: X件
- **失敗**: X件
- **成功率**: XX%

### 失敗シナリオ詳細
[失敗したシナリオがあれば詳細を記載]

### 総評
[テスト全体の評価を記載]
```

---

## 8. リスクと軽減策

### リスク1: Jenkins環境の不安定性

- **影響度**: 中
- **確率**: 低
- **軽減策**:
  - テスト実行前にJenkins環境の安定性を確認
  - 必要に応じてJenkinsを再起動
  - テスト環境と本番環境を分離

### リスク2: GitHub認証エラー

- **影響度**: 中
- **確率**: 低
- **軽減策**:
  - テスト実行前にGitHub認証情報を確認
  - ai-workflow-agentリポジトリへのアクセス権限を確認
  - 必要に応じて認証情報を更新

### リスク3: 設定ファイルのコピーミス

- **影響度**: 高
- **確率**: 中
- **軽減策**:
  - コピー前後で差分チェック（diff）を実施
  - 不要な定義が残っていないか目視確認
  - シードジョブ実行結果で作成ジョブ数を確認

### リスク4: 並行実行時の競合

- **影響度**: 低
- **確率**: 低
- **軽減策**:
  - 並行実行テスト（シナリオ3）で競合を早期検出
  - ビルドログで競合エラーを詳細に確認
  - 必要に応じてJob DSLの実行順序を調整

---

## 9. 補足情報

### テスト実施時の注意事項

1. **バックアップの作成**: テスト前に設定ファイルとJenkinsfileのバックアップを作成
2. **ビルドログの保存**: 各シナリオのビルドログを保存して、後で参照できるようにする
3. **スクリーンショットの取得**: 重要な確認ポイント（ジョブ一覧、フォルダ構造等）のスクリーンショットを取得
4. **段階的な実施**: 正常系シナリオを先に実施し、異常系シナリオは後で実施
5. **復旧手順の確認**: 異常系テスト後、正常な状態に戻せることを確認

### トラブルシューティング

#### ジョブ作成が失敗する場合

1. ビルドログでエラーメッセージを確認
2. 設定ファイルのYAML構文を確認（オンラインYAMLバリデータを使用）
3. DSLファイルのパスが正しいことを確認
4. Job DSLプラグインのバージョンを確認

#### フォルダが作成されない場合

1. folder-config.yamlのYAML構文を確認
2. フォルダパスが正しいことを確認
3. folders.groovyが正しく実行されているか確認
4. Jenkinsの権限設定を確認

#### 並行実行で競合が発生する場合

1. 両シードジョブの実行ログを詳細に確認
2. Job DSLのlookupStrategyを確認
3. Jenkinsのシステムログを確認

---

**作成日**: 2025年1月19日
**最終更新**: 2025年1月19日
**ステータス**: Draft
**次フェーズ**: Phase 4（実装）
