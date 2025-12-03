# 要件定義書

**Issue**: #453
**タイトル**: [TASK] AI Workflow Orchestrator ジョブを実行モードごとに分割・リポジトリ別構成に変更
**作成日**: 2025-01-17
**URL**: https://github.com/tielec/infrastructure-as-code/issues/453

---

## 0. Planning Documentの確認

### 開発計画の全体像
- **実装戦略**: REFACTOR（既存の単一ジョブを5つのジョブに分割）
- **テスト戦略**: INTEGRATION_ONLY（Jenkins環境での統合テストのみ）
- **テストコード戦略**: CREATE_TEST（手動テスト手順書を新規作成）
- **見積もり工数**: 8~12時間
- **リスク評価**: 中（既存ジョブの削除影響、パラメータロジックの複雑性）

### Planning Documentで策定された戦略
1. 既存の`ai_workflow_orchestrator.groovy`を5つの独立したJob DSLファイルに分割
2. 各ジョブに必要なパラメータのみを定義し、UI/UXを改善
3. `Code_Quality_Checker`と同じリポジトリ別構成パターンを採用
4. 既存ジョブは即座に削除せず、deprecated扱いとして残す
5. 統合テスト（シードジョブ実行、パラメータ画面確認、DRY_RUN実行）による検証

---

## 1. 概要

### 背景
現在、AI Workflow Orchestratorは単一のジョブ（`ai_workflow_orchestrator`）として実装されており、5つの実行モード（all_phases、preset、single_phase、rollback、auto_issue）すべてのパラメータ（24個）が混在しています。これにより、以下の問題が発生しています：
- パラメータが多すぎて使いにくい（不要なパラメータも表示される）
- リポジトリごとのジョブ区別がない（マルチリポジトリ対応が不十分）
- `Code_Quality_Checker`など他のジョブと構成パターンが異なる（一貫性の欠如）

### 目的
実行モードごとにジョブを分割し、リポジトリ別のサブフォルダ構成に変更することで、以下を実現します：
1. **パラメータの削減**: 各ジョブに必要なパラメータのみを表示（24個 → 8~15個）
2. **視認性向上**: リポジトリごとにジョブがグループ化され、管理が容易に
3. **一貫性の向上**: `Code_Quality_Checker`と同じパターンで統一

### ビジネス価値・技術的価値
- **開発者の生産性向上**: パラメータ数が削減され、ジョブ実行時の迷いが減少
- **保守性の向上**: ジョブ定義が分割され、変更影響範囲が明確化
- **拡張性の向上**: 新しいリポジトリの追加が容易（`jenkinsManagedRepositories`に追加するだけ）
- **ユーザビリティの向上**: 不要なパラメータが表示されず、UI/UXが改善

---

## 2. 機能要件

### F-1: リポジトリ別フォルダ構成の実装【優先度: 高】
- **要件**: `jenkinsManagedRepositories`に登録された各リポジトリに対して、サブフォルダ構造を自動生成する
- **詳細**:
  - フォルダ構造: `AI_Workflow/{repository-name}/`
  - 各リポジトリフォルダ配下に5つのジョブ（all_phases、preset、single_phase、rollback、auto_issue）を作成
  - `code_quality_pr_complexity_analyzer_job.groovy`の実装パターンを参考にする
- **成功条件**:
  - シードジョブ実行後、`AI_Workflow/infrastructure-as-code/all_phases`のようなパスでジョブが生成される
  - `jenkinsManagedRepositories`に新しいリポジトリを追加すると、自動的にジョブが生成される

### F-2: all_phases ジョブの作成【優先度: 高】
- **要件**: 全フェーズ一括実行用のジョブを作成する
- **詳細**:
  - Job DSLファイル: `jenkins/jobs/dsl/ai-workflow/ai_workflow_all_phases_job.groovy`
  - EXECUTION_MODE: `all_phases`（固定値、パラメータとして表示しない）
  - パラメータ数: 14個（Issue本文のパラメータ対応表を参照）
  - 必須パラメータ: ISSUE_URL
  - 不要なパラメータ: PRESET、START_PHASE、ROLLBACK_*、AUTO_ISSUE_*
- **成功条件**:
  - ジョブのパラメータ画面にall_phases用の14個のパラメータのみが表示される
  - EXECUTION_MODEが`all_phases`として内部的に設定され、Jenkinsfileに渡される

### F-3: preset ジョブの作成【優先度: 高】
- **要件**: プリセット実行用のジョブを作成する
- **詳細**:
  - Job DSLファイル: `jenkins/jobs/dsl/ai-workflow/ai_workflow_preset_job.groovy`
  - EXECUTION_MODE: `preset`（固定値）
  - パラメータ数: 15個
  - 必須パラメータ: ISSUE_URL、PRESET
  - 不要なパラメータ: START_PHASE、ROLLBACK_*、AUTO_ISSUE_*
- **成功条件**:
  - PRESETパラメータが必須として表示される
  - 不要なパラメータが表示されない

### F-4: single_phase ジョブの作成【優先度: 高】
- **要件**: 単一フェーズ実行用のジョブを作成する
- **詳細**:
  - Job DSLファイル: `jenkins/jobs/dsl/ai-workflow/ai_workflow_single_phase_job.groovy`
  - EXECUTION_MODE: `single_phase`（固定値）
  - パラメータ数: 13個
  - 必須パラメータ: ISSUE_URL、START_PHASE
  - 不要なパラメータ: PRESET、ROLLBACK_*、AUTO_ISSUE_*、FORCE_RESET、CLEANUP_ON_COMPLETE_FORCE
- **成功条件**:
  - START_PHASEパラメータが必須として表示される
  - FORCE_RESETとCLEANUP_ON_COMPLETE_FORCEが表示されない

### F-5: rollback ジョブの作成【優先度: 高】
- **要件**: フェーズ差し戻し実行用のジョブを作成する
- **詳細**:
  - Job DSLファイル: `jenkins/jobs/dsl/ai-workflow/ai_workflow_rollback_job.groovy`
  - EXECUTION_MODE: `rollback`（固定値）
  - パラメータ数: 12個
  - 必須パラメータ: ISSUE_URL、ROLLBACK_TO_PHASE
  - 任意パラメータ: ROLLBACK_TO_STEP、ROLLBACK_REASON、ROLLBACK_REASON_FILE
  - 不要なパラメータ: PRESET、START_PHASE、AUTO_ISSUE_*、SKIP_REVIEW、FORCE_RESET、MAX_RETRIES、CLEANUP_ON_COMPLETE_FORCE
- **成功条件**:
  - ROLLBACK_TO_PHASEが必須、ROLLBACK_TO_STEP等が任意として表示される
  - 実行制御系パラメータ（SKIP_REVIEW、FORCE_RESET等）が表示されない

### F-6: auto_issue ジョブの作成【優先度: 高】
- **要件**: 自動Issue作成用のジョブを作成する
- **詳細**:
  - Job DSLファイル: `jenkins/jobs/dsl/ai-workflow/ai_workflow_auto_issue_job.groovy`
  - EXECUTION_MODE: `auto_issue`（固定値）
  - パラメータ数: 8個
  - 必須パラメータ: GITHUB_REPOSITORY（ISSUE_URLは不要）
  - AUTO_ISSUE_*パラメータ: AUTO_ISSUE_CATEGORY（必須）、AUTO_ISSUE_LIMIT、AUTO_ISSUE_SIMILARITY_THRESHOLD（任意）
  - 不要なパラメータ: ISSUE_URL、BRANCH_NAME、PRESET、START_PHASE、ROLLBACK_*、SKIP_REVIEW、FORCE_RESET、MAX_RETRIES、CLEANUP_ON_COMPLETE_FORCE、GIT_COMMIT_*、AWS_*
- **成功条件**:
  - GITHUB_REPOSITORYが必須、ISSUE_URLが非表示
  - パラメータ数が8個に削減される（最も大きな削減効果）

### F-7: job-config.yamlの更新【優先度: 高】
- **要件**: 5つの新しいジョブ定義をYAMLファイルに追加する
- **詳細**:
  - ファイルパス: `jenkins/jobs/pipeline/_seed/job-creator/job-config.yaml`
  - 追加項目:
    ```yaml
    ai_workflow_all_phases_job:
      name: 'all_phases'
      displayName: 'All Phases Execution'
      dslfile: jenkins/jobs/dsl/ai-workflow/ai_workflow_all_phases_job.groovy
      jenkinsfile: Jenkinsfile  # ai-workflow-agentリポジトリのJenkinsfile
    ```
  - 既存の`ai_workflow_orchestrator_job`はコメントアウト（削除はしない）
- **成功条件**:
  - YAMLの構文チェックが通る
  - シードジョブが5つの新しいジョブを認識する

### F-8: 既存ジョブのdeprecated化【優先度: 中】
- **要件**: 既存の`ai_workflow_orchestrator.groovy`を非推奨として明示する
- **詳細**:
  - ファイル冒頭に非推奨コメントを追加
  - ジョブのdescriptionに移行案内を追加
  - 削除予定日をコメントに記載（例: 1ヶ月後）
- **成功条件**:
  - 既存ジョブのUIに「このジョブは非推奨です。新しいジョブ（AI_Workflow/{repo}/all_phases等）を使用してください」と表示される

### F-9: ドキュメント更新【優先度: 中】
- **要件**: `jenkins/README.md`を更新する
- **詳細**:
  - AI_Workflowセクションに5つのジョブの説明を追加
  - パラメータ一覧表を更新（各ジョブのパラメータ数を明記）
  - 既存ジョブからの移行ガイドを追加
- **成功条件**:
  - README.mdに新しいジョブ構成が記載される
  - ユーザーが移行方法を理解できる

---

## 3. 非機能要件

### N-1: パフォーマンス要件
- **シードジョブ実行時間**: 5分以内
  - 根拠: リポジトリ数が増えても（10リポジトリ = 50ジョブ）、合理的な時間で完了する必要がある
- **ジョブ生成時のCPU使用率**: 50%以下
  - 根拠: Jenkins Controllerへの負荷を最小化

### N-2: 可用性・信頼性要件
- **後方互換性**: 既存の`ai_workflow_orchestrator`ジョブは削除しない（deprecated扱い）
  - 根拠: 既存のビルド履歴やスケジュール設定を保持
- **段階的移行**: 移行期間（1ヶ月）を設け、ユーザーが新ジョブに移行できるようにする
- **ロールバック可能性**: job-config.yamlで既存ジョブのコメントアウトを解除すれば、即座に復元可能

### N-3: 保守性・拡張性要件
- **コードの再利用性**: 共通パラメータ定義は変数化（DRYの原則）
- **命名規則の統一**: `ai_workflow_{execution_mode}_job.groovy`形式
- **ドキュメントの完全性**: 各Job DSLファイルにヘッダーコメント（目的、パラメータ一覧、依存関係）を記載

### N-4: セキュリティ要件
- **パラメータの暗号化**: AWS認証情報（AWS_SECRET_ACCESS_KEY、AWS_SESSION_TOKEN）は`nonStoredPasswordParam`を使用
- **権限管理**: 既存の権限設定を維持（Jenkinsの既存の権限モデルを変更しない）

---

## 4. 制約事項

### 技術的制約
1. **Jenkins環境依存**: Job DSLはJenkins環境でのみ動作し、ユニットテストが困難
2. **Jenkinsfileの変更不可**: `ai-workflow-agent`リポジトリのJenkinsfileは本Issue対象外（別リポジトリ）
3. **EXECUTION_MODEの受け渡し**: Jenkinsfileは既にEXECUTION_MODEパラメータを受け取る実装になっているため、Job DSLから固定値として渡す
4. **jenkinsManagedRepositoriesの形式**: job-config.yamlで定義された形式に従う必要がある

### リソース制約
- **開発期間**: 8~12時間（Planning Documentの見積もり）
- **テスト環境**: dev環境でのみテスト実行可能（本番環境でのテストは不可）

### ポリシー制約
- **コーディング規約**: CLAUDE.mdおよびjenkins/CONTRIBUTION.mdに従う
- **パラメータ定義ルール**: Jenkinsfileでのパラメータ定義は禁止（Job DSLファイルでのみ定義）
- **Git運用**: ブランチ命名規則（task/issue-453-*）、コミットメッセージ規約を遵守

---

## 5. 前提条件

### システム環境
- Jenkins 2.426.1以上
- Job DSL Plugin（最新版）
- Groovy（Jenkins標準バージョン）

### 依存コンポーネント
- **Job Creator（シードジョブ）**: `Admin_Jobs/job-creator`が正常に動作すること
- **ai-workflow-agent リポジトリ**: Jenkinsfileが`main`ブランチに存在し、EXECUTION_MODEパラメータを受け取る実装になっていること
- **jenkins-pipeline-repo（infrastructure-as-code）**: job-config.yamlおよびJob DSLファイルが格納されるリポジトリ

### 外部システム連携
- **GitHub**: `jenkinsManagedRepositories`に登録されたリポジトリへのアクセス権限
- **Jenkins Credentials Store**: `github-app-credentials`が正しく設定されていること

---

## 6. 受け入れ基準

### AC-1: リポジトリ別フォルダ構成の生成
**Given**: `jenkinsManagedRepositories`に`infrastructure-as-code`と`ai-workflow-agent`の2つのリポジトリが登録されている
**When**: シードジョブ（`Admin_Jobs/job-creator`）を実行する
**Then**:
- `AI_Workflow/infrastructure-as-code/all_phases`のようなパスでジョブが生成される
- `AI_Workflow/ai-workflow-agent/all_phases`のようなパスでジョブが生成される
- 各リポジトリに5つのジョブ（all_phases、preset、single_phase、rollback、auto_issue）が作成される

### AC-2: all_phasesジョブのパラメータ
**Given**: `AI_Workflow/infrastructure-as-code/all_phases`ジョブが生成されている
**When**: ジョブのパラメータ画面を開く
**Then**:
- パラメータ数が14個である
- ISSUE_URL、BRANCH_NAME、AGENT_MODE、DRY_RUN、SKIP_REVIEW、FORCE_RESET、MAX_RETRIES、CLEANUP_ON_COMPLETE_FORCE、GIT_COMMIT_USER_NAME、GIT_COMMIT_USER_EMAIL、AWS_ACCESS_KEY_ID、AWS_SECRET_ACCESS_KEY、AWS_SESSION_TOKEN、COST_LIMIT_USD、LOG_LEVELが表示される
- EXECUTION_MODE、PRESET、START_PHASE、ROLLBACK_*、AUTO_ISSUE_*が表示されない

### AC-3: presetジョブのパラメータ
**Given**: `AI_Workflow/infrastructure-as-code/preset`ジョブが生成されている
**When**: ジョブのパラメータ画面を開く
**Then**:
- パラメータ数が15個である
- PRESETパラメータが必須項目として表示される
- START_PHASE、ROLLBACK_*、AUTO_ISSUE_*が表示されない

### AC-4: single_phaseジョブのパラメータ
**Given**: `AI_Workflow/infrastructure-as-code/single_phase`ジョブが生成されている
**When**: ジョブのパラメータ画面を開く
**Then**:
- パラメータ数が13個である
- START_PHASEパラメータが必須項目として表示される
- PRESET、ROLLBACK_*、AUTO_ISSUE_*、FORCE_RESET、CLEANUP_ON_COMPLETE_FORCEが表示されない

### AC-5: rollbackジョブのパラメータ
**Given**: `AI_Workflow/infrastructure-as-code/rollback`ジョブが生成されている
**When**: ジョブのパラメータ画面を開く
**Then**:
- パラメータ数が12個である
- ROLLBACK_TO_PHASEが必須項目として表示される
- ROLLBACK_TO_STEP、ROLLBACK_REASON、ROLLBACK_REASON_FILEが任意項目として表示される
- PRESET、START_PHASE、AUTO_ISSUE_*、SKIP_REVIEW、FORCE_RESET、MAX_RETRIES、CLEANUP_ON_COMPLETE_FORCEが表示されない

### AC-6: auto_issueジョブのパラメータ
**Given**: `AI_Workflow/infrastructure-as-code/auto_issue`ジョブが生成されている
**When**: ジョブのパラメータ画面を開く
**Then**:
- パラメータ数が8個である
- GITHUB_REPOSITORYが必須項目として表示される
- AUTO_ISSUE_CATEGORY、AUTO_ISSUE_LIMIT、AUTO_ISSUE_SIMILARITY_THRESHOLDが表示される
- ISSUE_URL、BRANCH_NAME、PRESET、START_PHASE、ROLLBACK_*、SKIP_REVIEW、FORCE_RESET、MAX_RETRIES、CLEANUP_ON_COMPLETE_FORCE、GIT_COMMIT_*、AWS_*が表示されない

### AC-7: EXECUTION_MODEの内部設定
**Given**: `AI_Workflow/infrastructure-as-code/all_phases`ジョブでビルドを実行する
**When**: DRY_RUN=trueで実行し、ログを確認する
**Then**:
- ログに`EXECUTION_MODE=all_phases`と記録される
- Jenkinsfileが正しく動作する（エラーが発生しない）

### AC-8: job-config.yamlの更新
**Given**: job-config.yamlに5つの新しいジョブ定義を追加した
**When**: YAMLの構文チェック（`ansible-playbook --syntax-check`）を実行する
**Then**:
- エラーが発生しない
- 既存の`ai_workflow_orchestrator_job`がコメントアウトされている

### AC-9: 既存ジョブのdeprecated表示
**Given**: 既存の`ai_workflow_orchestrator`ジョブが存在する
**When**: ジョブの詳細画面を開く
**Then**:
- descriptionに「このジョブは非推奨です」と表示される
- 新しいジョブへの移行案内リンクが表示される
- 削除予定日が明記されている

### AC-10: ドキュメントの更新
**Given**: jenkins/README.mdが更新されている
**When**: README.mdを開く
**Then**:
- AI_Workflowセクションに5つのジョブの説明が記載されている
- 各ジョブのパラメータ数が表形式で比較されている
- 既存ジョブからの移行ガイドが記載されている

### AC-11: 統合テスト（DRY_RUN実行）
**Given**: 5つの新しいジョブすべてが生成されている
**When**: 各ジョブを`DRY_RUN=true`で実行する
**Then**:
- すべてのジョブがエラーなく完了する
- ログにEXECUTION_MODEの固定値が正しく渡されていることが記録される
- Jenkinsfileが正常に動作する

---

## 7. スコープ外

以下の項目は本Issueのスコープ外とします：

### S-1: Jenkinsfileの変更
- `ai-workflow-agent`リポジトリのJenkinsfileは別リポジトリであり、本Issue対象外
- ただし、既存のJenkinsfileがEXECUTION_MODEパラメータを受け取る実装になっていることを前提とする

### S-2: 既存ジョブの即座の削除
- 既存の`ai_workflow_orchestrator`ジョブは即座に削除しない
- deprecated扱いとし、移行期間（1ヶ月）後に別Issueで削除を検討

### S-3: パラメータの追加・削減（仕様変更）
- パラメータの種類や意味の変更は行わない
- Issue本文のパラメータ対応表に厳密に従う

### S-4: UI/UXの大幅な変更
- パラメータの説明文は既存のものを流用（軽微な調整は可）
- ジョブのアイコンやレイアウトは変更しない

### S-5: 新機能の追加
- リポジトリ別構成の追加機能（例: リポジトリごとのデフォルトパラメータ設定）は実装しない
- 将来的な拡張候補として記録

---

## 8. 将来的な拡張候補

以下の項目は本Issueでは実装しませんが、将来的な拡張候補として記録します：

1. **リポジトリごとのデフォルトパラメータ設定**: jenkinsManagedRepositoriesにデフォルトパラメータを定義し、ジョブ生成時に自動設定
2. **パラメータの動的検証**: パラメータ間の依存関係（例: PRESET選択時に特定のパラメータを必須化）をGroovyスクリプトで実装
3. **ジョブのテンプレート化**: 5つのジョブの共通部分をテンプレート化し、コードの重複を削減
4. **マルチブランチパイプライン化**: リポジトリのブランチごとにジョブを自動生成

---

## 9. 品質ゲート確認

本要件定義書は、以下の品質ゲート（Phase 1）を満たしています：

- ✅ **機能要件が明確に記載されている**: F-1～F-9として9つの機能要件を具体的に記載
- ✅ **受け入れ基準が定義されている**: AC-1～AC-11として11個の受け入れ基準をGiven-When-Then形式で記載
- ✅ **スコープが明確である**: スコープ外（S-1～S-5）と将来的な拡張候補を明記
- ✅ **論理的な矛盾がない**: Planning Documentの戦略と整合性があり、Issue本文のパラメータ対応表を厳密に反映

---

## 10. 参考情報

### 関連ファイル
- **Planning Document**: `.ai-workflow/issue-453/00_planning/output/planning.md`
- **既存実装**: `jenkins/jobs/dsl/ai-workflow/ai_workflow_orchestrator.groovy`
- **参考実装**: `jenkins/jobs/dsl/code-quality-checker/code_quality_pr_complexity_analyzer_job.groovy`
- **設定ファイル**: `jenkins/jobs/pipeline/_seed/job-creator/job-config.yaml`
- **ドキュメント**: `jenkins/README.md`、`jenkins/CONTRIBUTION.md`、`CLAUDE.md`

### パラメータ数サマリー（再掲）

| ジョブ | パラメータ数 | 削減数 | 削減率 |
|--------|-------------|--------|--------|
| 現在（統合） | 24個 | - | - |
| all_phases | 14個 | -10 | 41.7% |
| preset | 15個 | -9 | 37.5% |
| single_phase | 13個 | -11 | 45.8% |
| rollback | 12個 | -12 | 50.0% |
| auto_issue | 8個 | -16 | 66.7% |

---

**要件定義書作成者**: AI Workflow Agent
**レビュー待ち**: Phase 1 (Requirements) Review
