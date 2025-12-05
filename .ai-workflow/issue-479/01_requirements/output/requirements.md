# 要件定義書: AI Workflow用シードジョブの設定ファイル分離

## Issue情報

- **Issue番号**: #479
- **タイトル**: [Feature] AI Workflow用シードジョブの設定ファイル分離
- **URL**: https://github.com/tielec/infrastructure-as-code/issues/479
- **関連Issue**: #477 ([Feature] AI Workflow用のシードジョブを分離)
- **作成日**: 2025年1月19日

---

## 0. Planning Documentの確認

### 開発計画の概要

Planning Document（planning.md）より、以下の開発方針が策定されています：

- **実装戦略**: CREATE（新規ファイル作成が中心、既存ファイルは削除とパス変更のみ）
- **テスト戦略**: INTEGRATION_ONLY（設定ファイル中心のため単体テスト不要）
- **テストコード戦略**: 該当なし（Job DSLプラグインによる自動検証を活用）
- **複雑度**: 簡単
- **見積もり工数**: 3~5時間
- **リスク評価**: 低（影響範囲が明確、ロールバック容易）

### 主要な成果物

1. **新規作成ファイル**:
   - `jenkins/jobs/pipeline/_seed/ai-workflow-job-creator/job-config.yaml`
   - `jenkins/jobs/pipeline/_seed/ai-workflow-job-creator/folder-config.yaml`

2. **修正ファイル**:
   - `jenkins/jobs/pipeline/_seed/ai-workflow-job-creator/Jenkinsfile`（パス参照更新）
   - `jenkins/jobs/pipeline/_seed/job-creator/job-config.yaml`（AI Workflow定義削除）
   - `jenkins/jobs/pipeline/_seed/job-creator/folder-config.yaml`（AI Workflowフォルダ削除）
   - `jenkins/jobs/pipeline/_seed/job-creator/Jenkinsfile`（除外ロジック削除）

### 品質ゲート（Phase 1）

Planning Documentで定義された以下の品質ゲートを満たすことを確認しました：

- [x] AI Workflow関連の5ジョブがリストアップされている
- [x] AI_Workflowフォルダ定義（11個）がリストアップされている
- [x] 既存設定ファイルとの差分が明確になっている

---

## 1. 概要

### 背景

Issue #477でAI Workflow専用のシードジョブ（ai-workflow-job-creator）を作成しましたが、現状では以下の問題があります：

- **設定ファイルの共有**: ai-workflow-job-creatorが依然として共通の設定ファイル（job-creator/job-config.yaml、job-creator/folder-config.yaml）を参照している
- **冗長な除外ロジック**: job-creator/JenkinsfileにAI Workflowを除外するロジックが含まれており、コードが複雑化している

この状態では、シードジョブの分離が不完全であり、以下のリスクがあります：

- 一方の設定変更が他方に影響する可能性
- 除外ロジックのメンテナンスコスト
- 設定ファイルの肥大化による可読性低下

### 目的

AI Workflow専用の設定ファイルを作成し、以下を実現します：

1. **完全な分離**: AI Workflowと一般ジョブの設定を完全に独立させる
2. **コードの簡素化**: 除外ロジックを削除し、job-creatorのコードを簡潔にする
3. **保守性の向上**: 各シードジョブの責務を明確化し、変更影響範囲を限定する

### ビジネス価値

- **保守性向上**: 各シードジョブが独立して動作するため、変更時の影響範囲が明確
- **可読性向上**: 設定ファイルが整理され、ジョブ定義の見通しが良くなる
- **開発効率向上**: 除外ロジックが不要になり、コードがシンプルに

### 技術的価値

- **疎結合化**: シードジョブ間の依存関係を排除
- **単一責任の原則**: 各シードジョブが特定のジョブセットのみを管理
- **拡張性**: 将来的に他のジョブカテゴリを分離する際のテンプレートとなる

---

## 2. 機能要件

### FR-1: AI Workflow専用設定ファイルの作成（優先度: 高）

**説明**: AI Workflow関連のジョブとフォルダを定義する専用のYAML設定ファイルを作成する。

**詳細**:

- **FR-1.1**: `jenkins/jobs/pipeline/_seed/ai-workflow-job-creator/job-config.yaml` を作成
  - AI Workflow関連の5ジョブのみを定義
    1. ai_workflow_all_phases_job
    2. ai_workflow_preset_job
    3. ai_workflow_single_phase_job
    4. ai_workflow_rollback_job
    5. ai_workflow_auto_issue_job
  - 既存の `job-creator/job-config.yaml` から対象ジョブ定義をコピー

- **FR-1.2**: `jenkins/jobs/pipeline/_seed/ai-workflow-job-creator/folder-config.yaml` を作成
  - AI_Workflowフォルダ定義（11個）のみを定義
    1. AI_Workflow（親フォルダ）
    2. AI_Workflow/develop
    3. AI_Workflow/stable-1 ～ stable-9（9個）
  - 既存の `job-creator/folder-config.yaml` から対象フォルダ定義をコピー

**受け入れ基準**:
```gherkin
Given: AI Workflow関連ジョブとフォルダの定義が既存設定ファイルに存在する
When: 新規YAML設定ファイルを作成する
Then: AI Workflow関連の5ジョブ定義が job-config.yaml に含まれる
And: AI_Workflowフォルダ定義（11個）が folder-config.yaml に含まれる
And: YAML構文エラーがない
And: 既存定義と内容が一致する（定義の重複なし）
```

---

### FR-2: ai-workflow-job-creator/Jenkinsfile のパス参照更新（優先度: 高）

**説明**: ai-workflow-job-creatorのJenkinsfileを修正し、新規作成した設定ファイルを参照するように変更する。

**詳細**:

- **FR-2.1**: `JOB_CONFIG_PATH` の値を変更
  - Before: `jenkins/jobs/pipeline/_seed/job-creator/job-config.yaml`
  - After: `jenkins/jobs/pipeline/_seed/ai-workflow-job-creator/job-config.yaml`

- **FR-2.2**: `FOLDER_CONFIG_PATH` の値を変更
  - Before: `jenkins/jobs/pipeline/_seed/job-creator/folder-config.yaml`
  - After: `jenkins/jobs/pipeline/_seed/ai-workflow-job-creator/folder-config.yaml`

**受け入れ基準**:
```gherkin
Given: ai-workflow-job-creator/Jenkinsfile が存在する
When: パス定義を新規設定ファイルに変更する
Then: JOB_CONFIG_PATH が "jenkins/jobs/pipeline/_seed/ai-workflow-job-creator/job-config.yaml" を指す
And: FOLDER_CONFIG_PATH が "jenkins/jobs/pipeline/_seed/ai-workflow-job-creator/folder-config.yaml" を指す
And: Groovy構文エラーがない
```

---

### FR-3: 共通設定ファイルからAI Workflow定義の削除（優先度: 高）

**説明**: 共通設定ファイル（job-creator配下）からAI Workflow関連の定義を削除する。

**詳細**:

- **FR-3.1**: `job-creator/job-config.yaml` からAI Workflow関連ジョブ定義を削除
  - 削除対象: ai_workflow_all_phases_job、ai_workflow_preset_job、ai_workflow_single_phase_job、ai_workflow_rollback_job、ai_workflow_auto_issue_job の5ジョブ定義

- **FR-3.2**: `job-creator/folder-config.yaml` からAI_Workflowフォルダ定義を削除
  - 削除対象: AI_Workflow（親）+ develop + stable-1～9（全11フォルダ定義）

**受け入れ基準**:
```gherkin
Given: job-creator/job-config.yaml にAI Workflow関連ジョブ定義が含まれる
And: job-creator/folder-config.yaml にAI_Workflowフォルダ定義が含まれる
When: AI Workflow関連の定義を削除する
Then: job-creator/job-config.yaml にAI Workflow関連ジョブ定義が存在しない
And: job-creator/folder-config.yaml にAI_Workflowフォルダ定義が存在しない
And: YAML構文エラーがない
And: 一般ジョブの定義は残っている
```

---

### FR-4: job-creator/Jenkinsfile からAI Workflow除外ロジックの削除（優先度: 高）

**説明**: job-creator/JenkinsfileからAI Workflowを除外する冗長なロジックを削除し、コードを簡素化する。

**詳細**:

- **FR-4.1**: AI Workflow除外ロジックの削除
  - Planning Documentによると行127-133が対象
  - 除外処理に関連するコードブロックを削除

- **FR-4.2**: ジョブカウントログ出力の修正
  - AI Workflow除外後のジョブ数を正しく表示するログを削除または修正

**受け入れ基準**:
```gherkin
Given: job-creator/Jenkinsfile にAI Workflow除外ロジックが含まれる
When: 除外ロジックを削除する
Then: AI Workflow除外に関するコードが存在しない
And: Groovy構文エラーがない
And: 一般ジョブの作成ロジックは正常に動作する
And: コードが簡潔になっている
```

---

### FR-5: 動作確認（優先度: 高）

**説明**: 両方のシードジョブが独立して正常に動作することを確認する。

**詳細**:

- **FR-5.1**: job-creator シードジョブの実行確認
  - AI Workflow関連ジョブが作成されないこと
  - 一般ジョブが正常に作成されること

- **FR-5.2**: ai-workflow-job-creator シードジョブの実行確認
  - AI Workflow関連の5ジョブのみが作成されること
  - AI_Workflowフォルダ構造（親 + develop + stable 1-9）が正しく作成されること

- **FR-5.3**: 並行実行テスト
  - 両シードジョブを並行実行して競合が発生しないことを確認

**受け入れ基準**:
```gherkin
Given: 両方のシードジョブが設定済み
When: job-creator を実行する
Then: AI Workflow関連ジョブが作成されない
And: 一般ジョブが正常に作成される
And: 実行ログにエラーがない

Given: 両方のシードジョブが設定済み
When: ai-workflow-job-creator を実行する
Then: AI Workflow関連の5ジョブのみが作成される
And: AI_Workflowフォルダ構造（11個）が正しく作成される
And: 実行ログにエラーがない

Given: 両方のシードジョブが設定済み
When: 両シードジョブを並行実行する
Then: どちらのジョブもエラーなく完了する
And: ジョブ・フォルダの重複や欠落がない
```

---

## 3. 非機能要件

### NFR-1: パフォーマンス要件

- **NFR-1.1**: シードジョブの実行時間は各1分以内で完了すること
- **NFR-1.2**: 設定ファイルの読み込み処理は3秒以内で完了すること

### NFR-2: セキュリティ要件

- **NFR-2.1**: 設定ファイルにクレデンシャル情報を含めないこと
- **NFR-2.2**: ジョブ作成権限は適切に制御されること（Jenkinsの権限管理に準拠）

### NFR-3: 可用性・信頼性要件

- **NFR-3.1**: 一方のシードジョブが失敗しても他方に影響しないこと
- **NFR-3.2**: 設定ファイルのYAML構文エラーは実行前に検出されること（Job DSLプラグインによる検証）

### NFR-4: 保守性・拡張性要件

- **NFR-4.1**: 設定ファイルはDRY原則に従い、重複定義がないこと
- **NFR-4.2**: 新規ジョブの追加は該当する設定ファイルのみの変更で完了すること
- **NFR-4.3**: コードコメントにより、各ファイルの責務が明確に記載されていること
- **NFR-4.4**: 将来的に他のジョブカテゴリを分離する際のテンプレートとして機能すること

---

## 4. 制約事項

### 技術的制約

- **TC-1**: Jenkins Job DSLプラグインの仕様に準拠すること
- **TC-2**: YAML 1.1または1.2の仕様に準拠すること
- **TC-3**: Groovy構文の制約に従うこと
- **TC-4**: 既存のJob DSL処理ロジック（seedジョブの実装）を変更しないこと

### リソース制約

- **RC-1**: 実装工数は3~5時間以内とする（Planning Documentの見積もり）
- **RC-2**: 新規リソースの追加は不要（既存の設定ファイル再編成のみ）

### ポリシー制約

- **PC-1**: CLAUDE.mdのコーディングガイドラインに準拠すること
  - コメントは日本語で記述
  - ファイル先頭にヘッダーコメント（ファイルパス、目的、依存関係）を記載
- **PC-2**: jenkins/CONTRIBUTION.mdのベストプラクティスに準拠すること
  - パラメータ定義はJob DSLファイルで行い、Jenkinsfileには記載しない
- **PC-3**: コミットメッセージ規約に従うこと
  - 形式: `[jenkins] action: 詳細な説明`

---

## 5. 前提条件

### システム環境

- **ENV-1**: Jenkins環境が構築済みであること
- **ENV-2**: Job DSLプラグインがインストール済みであること
- **ENV-3**: Git連携が設定済みであること

### 依存コンポーネント

- **DEP-1**: Issue #477で作成したai-workflow-job-creatorが存在すること
- **DEP-2**: 既存のjob-creatorが正常に動作していること
- **DEP-3**: 以下の設定ファイルが存在すること
  - `jenkins/jobs/pipeline/_seed/job-creator/job-config.yaml`
  - `jenkins/jobs/pipeline/_seed/job-creator/folder-config.yaml`
  - `jenkins/jobs/pipeline/_seed/job-creator/Jenkinsfile`
  - `jenkins/jobs/pipeline/_seed/ai-workflow-job-creator/Jenkinsfile`

### 外部システム連携

- **EXT-1**: Gitリポジトリへのアクセス権限があること
- **EXT-2**: Jenkinsサーバーからの設定ファイル読み込みが可能であること

---

## 6. 受け入れ基準

### AC-1: 設定ファイルの分離完了

```gherkin
Given: AI Workflow専用の設定ファイルが存在しない
When: 要件FR-1に従って設定ファイルを作成する
Then: ai-workflow-job-creator/job-config.yaml が存在する
And: AI Workflow関連の5ジョブ定義が含まれる
And: ai-workflow-job-creator/folder-config.yaml が存在する
And: AI_Workflowフォルダ定義（11個）が含まれる
And: YAML構文エラーがない
```

### AC-2: パス参照の更新完了

```gherkin
Given: ai-workflow-job-creator/Jenkinsfile が共通設定ファイルを参照している
When: 要件FR-2に従ってパス参照を更新する
Then: JOB_CONFIG_PATH が専用設定ファイルを指す
And: FOLDER_CONFIG_PATH が専用設定ファイルを指す
And: Jenkinsfileが正常に実行できる
```

### AC-3: 共通設定からの削除完了

```gherkin
Given: job-creator配下の設定ファイルにAI Workflow定義が含まれる
When: 要件FR-3に従ってAI Workflow定義を削除する
Then: job-creator/job-config.yaml にAI Workflowジョブ定義が存在しない
And: job-creator/folder-config.yaml にAI_Workflowフォルダ定義が存在しない
And: 一般ジョブの定義は保持されている
```

### AC-4: 除外ロジックの削除完了

```gherkin
Given: job-creator/Jenkinsfile にAI Workflow除外ロジックが含まれる
When: 要件FR-4に従って除外ロジックを削除する
Then: AI Workflow除外に関するコードが存在しない
And: コードが簡素化されている
And: 一般ジョブ作成機能は正常に動作する
```

### AC-5: 独立動作の確認完了

```gherkin
Given: すべての設定変更が完了している
When: job-creator シードジョブを実行する
Then: AI Workflow関連ジョブが作成されない
And: 一般ジョブが正常に作成される
And: 実行ログにエラーがない

Given: すべての設定変更が完了している
When: ai-workflow-job-creator シードジョブを実行する
Then: AI Workflow関連の5ジョブのみが作成される
And: AI_Workflowフォルダ構造（11個）が正しく作成される
And: 実行ログにエラーがない

Given: すべての設定変更が完了している
When: 両シードジョブを並行実行する
Then: どちらのジョブもエラーなく完了する
And: ジョブ・フォルダの重複や欠落がない
```

---

## 7. スコープ外

### 現時点でスコープ外とする事項

1. **他のジョブカテゴリの分離**
   - 本Issueではai-workflow-job-creatorの設定ファイル分離のみを実施
   - 他のジョブカテゴリ（Lambda、Pulumi等）の分離は別Issueで対応

2. **シードジョブの実行自動化**
   - 設定ファイル変更時のシードジョブ自動実行は別途検討
   - 現時点では手動実行を前提

3. **設定ファイルのバリデーション自動化**
   - YAML構文チェックの自動化は別途検討
   - 現時点ではJob DSLプラグインによる実行時検証に依存

4. **ドキュメントの大幅な更新**
   - jenkins/README.mdの更新要否は確認するが、大幅な変更は不要
   - 必要に応じて軽微な更新のみ実施

### 将来的な拡張候補

1. **設定ファイルのテンプレート化**
   - 他のジョブカテゴリ分離時のテンプレートとして活用
   - ベストプラクティスの文書化

2. **CI/CDパイプラインへの統合**
   - 設定ファイル変更のPR作成時に自動検証
   - シードジョブの自動実行とテスト

3. **モニタリング機能の追加**
   - シードジョブ実行結果の通知
   - 設定ファイルの変更履歴追跡

---

## 8. 補足情報

### AI Workflow関連ジョブ一覧（5個）

1. **ai_workflow_all_phases_job** - 全フェーズ実行ジョブ
2. **ai_workflow_preset_job** - プリセット実行ジョブ
3. **ai_workflow_single_phase_job** - 単一フェーズ実行ジョブ
4. **ai_workflow_rollback_job** - ロールバックジョブ
5. **ai_workflow_auto_issue_job** - 自動Issue作成ジョブ

### AI_Workflowフォルダ定義一覧（11個）

1. **AI_Workflow** - 親フォルダ
2. **AI_Workflow/develop** - 開発環境用フォルダ
3. **AI_Workflow/stable-1** - 安定版1フォルダ
4. **AI_Workflow/stable-2** - 安定版2フォルダ
5. **AI_Workflow/stable-3** - 安定版3フォルダ
6. **AI_Workflow/stable-4** - 安定版4フォルダ
7. **AI_Workflow/stable-5** - 安定版5フォルダ
8. **AI_Workflow/stable-6** - 安定版6フォルダ
9. **AI_Workflow/stable-7** - 安定版7フォルダ
10. **AI_Workflow/stable-8** - 安定版8フォルダ
11. **AI_Workflow/stable-9** - 安定版9フォルダ

### ファイル構造（変更後）

```
jenkins/jobs/pipeline/_seed/
├── job-creator/
│   ├── Jenkinsfile                 # 修正: 除外ロジック削除
│   ├── job-config.yaml             # 修正: AI Workflow定義削除
│   └── folder-config.yaml          # 修正: AI_Workflowフォルダ削除
└── ai-workflow-job-creator/
    ├── Jenkinsfile                 # 修正: パス参照更新
    ├── job-config.yaml             # 新規作成: AI Workflowジョブ定義
    └── folder-config.yaml          # 新規作成: AI_Workflowフォルダ定義
```

### 変更ファイル一覧

| No | ファイルパス | 変更種別 | 変更内容 |
|----|-------------|----------|----------|
| 1 | jenkins/jobs/pipeline/_seed/ai-workflow-job-creator/job-config.yaml | 新規作成 | AI Workflow関連5ジョブ定義 |
| 2 | jenkins/jobs/pipeline/_seed/ai-workflow-job-creator/folder-config.yaml | 新規作成 | AI_Workflowフォルダ定義（11個） |
| 3 | jenkins/jobs/pipeline/_seed/ai-workflow-job-creator/Jenkinsfile | 修正 | パス参照を専用設定ファイルに変更 |
| 4 | jenkins/jobs/pipeline/_seed/job-creator/job-config.yaml | 修正 | AI Workflow関連ジョブ定義を削除 |
| 5 | jenkins/jobs/pipeline/_seed/job-creator/folder-config.yaml | 修正 | AI_Workflowフォルダ定義を削除 |
| 6 | jenkins/jobs/pipeline/_seed/job-creator/Jenkinsfile | 修正 | AI Workflow除外ロジックを削除 |

---

**作成日**: 2025年1月19日
**ステータス**: Draft
**次フェーズ**: Phase 2（設計）
