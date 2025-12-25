# 要件定義書 - Issue #526

## 環境停止スケジューラージョブの無効化

---

## 0. Planning Document確認

本要件定義はPlanning Phase（`.ai-workflow/issue-526/00_planning/output/planning.md`）で策定された開発計画を基に作成されています。

### Planning Phaseで確認された戦略
- **実装戦略**: EXTEND（既存ファイルの機能拡張）
- **テスト戦略**: INTEGRATION_ONLY（Jenkins環境での統合テスト）
- **テストコード戦略**: CREATE_TEST（新規テストシナリオ作成）
- **複雑度**: 簡単（単一ファイルの1行修正）
- **工数見積**: 2-3時間
- **リスク評価**: 低

---

## 1. 概要

### 1.1 背景と目的

**背景**:
- 現在、dev環境が毎日JST午前0時（UTC 15:00）に自動停止される設定になっている
- 運用方針の変更により、常時稼働の運用に切り替える必要がある
- `Infrastructure_Management/Shutdown-Environment-Scheduler`ジョブの無効化が求められている

**目的**:
- スケジュール実行による自動停止を無効化
- 手動停止機能は維持（必要時に使用可能）
- 運用コスト管理の責任を自動化から手動運用に移行

### 1.2 ビジネス価値・技術的価値

**ビジネス価値**:
- 常時稼働による開発効率の向上
- 予期しないシステム停止の回避
- チーム間の運用方針統一

**技術的価値**:
- Infrastructure as Codeの原則に従った設定変更
- 可逆的な変更（将来的な再有効化が容易）
- Jenkins Job DSLによる宣言的な管理

---

## 2. 機能要件

### 2.1 主要機能要件

| ID | 要件名 | 説明 | 優先度 |
|----|--------|------|--------|
| FR-001 | DSLファイル修正 | `infrastructure_shutdown_scheduler_job.groovy`に`disabled(true)`を追加 | 最高 |
| FR-002 | シードジョブ実行 | `Admin_Jobs/job-creator`を実行してジョブ設定を反映 | 最高 |
| FR-003 | ジョブ無効化確認 | Jenkins UIでジョブが「無効」状態になっていることを確認 | 高 |
| FR-004 | スケジュール停止確認 | Cronスケジュール（`H 15 * * *`）が実行されないことを確認 | 高 |
| FR-005 | ドキュメント更新 | 必要に応じてjenkins/README.mdを更新 | 中 |

### 2.2 詳細仕様

#### FR-001: DSLファイル修正
- **ファイル**: `jenkins/jobs/dsl/infrastructure-management/infrastructure_shutdown_scheduler_job.groovy`
- **変更内容**:
  ```groovy
  // 修正前
  disabled(false)  // または設定なし

  // 修正後
  disabled(true)   // ジョブを無効化
  ```
- **構文エラー**: 発生させない
- **Git管理**: 変更内容をコミット

#### FR-002: シードジョブ実行
- **実行対象**: `Admin_Jobs/job-creator`
- **実行方法**: Jenkins UI経由での手動実行
- **実行時間**: 5分以内で完了
- **実行結果**: SUCCESS状態

#### FR-003: ジョブ無効化確認
- **確認対象**: `Infrastructure_Management/Shutdown-Environment-Scheduler`
- **確認方法**:
  - Jenkins UI: ジョブ画面でdisabledアイコンの表示
  - Jenkins CLI: `java -jar jenkins-cli.jar get-job`コマンド
- **期待値**: ジョブが無効状態

#### FR-004: スケジュール停止確認
- **確認対象**: Cronトリガー（`H 15 * * *`）
- **確認方法**: Jenkins UIのスケジュール表示
- **確認タイミング**: 次回予定時刻での非実行
- **期待値**: スケジュール実行が発生しない

#### FR-005: ドキュメント更新
- **対象ファイル**: `jenkins/README.md`（必要に応じて）
- **更新内容**:
  - 自動停止機能の無効化について記載
  - 手動停止の手順を明記
  - 将来的な再有効化手順を記載

---

## 3. 非機能要件

### 3.1 パフォーマンス要件
- **NFR-001**: シードジョブ実行時間は5分以内で完了すること
- **NFR-002**: DSL構文エラーにより他のジョブ作成に影響を与えないこと

### 3.2 セキュリティ要件
- **NFR-003**: Jenkins管理者権限を持つユーザーのみが作業を実行すること
- **NFR-004**: 変更作業はGit履歴として記録されること

### 3.3 可用性・信頼性要件
- **NFR-005**: ロールバック可能であること（`disabled(false)`への復旧）
- **NFR-006**: 他のインフラ管理ジョブに影響を与えないこと

### 3.4 保守性・拡張性要件
- **NFR-007**: Infrastructure as Codeの原則に従うこと
- **NFR-008**: 将来的なスケジュール時刻変更にも対応可能であること

---

## 4. 制約事項

### 4.1 技術的制約
- **TC-001**: Jenkins Job DSL構文に厳密に準拠すること
- **TC-002**: 既存の`infrastructure_shutdown_scheduler_job.groovy`ファイルを使用すること
- **TC-003**: シードジョブ（job-creator）の実行が必要であること

### 4.2 リソース制約
- **RC-001**: 作業時間は2-3時間以内に完了すること
- **RC-002**: Jenkins管理者権限でのアクセスが必要であること

### 4.3 ポリシー制約
- **PC-001**: Infrastructure as Codeの原則に従うこと
- **PC-002**: 変更内容はGitで管理すること
- **PC-003**: 手動でのJenkins UI変更は行わないこと

---

## 5. 前提条件

### 5.1 システム環境
- Jenkins環境が稼働状態であること
- `Admin_Jobs/job-creator`（シードジョブ）が正常に動作すること
- Git リポジトリへの書き込み権限があること

### 5.2 依存コンポーネント
- Jenkins Job DSL Plugin
- `infrastructure_shutdown_scheduler_job.groovy`ファイル
- `Admin_Jobs/job-creator`ジョブ

### 5.3 外部システム連携
- Gitリポジトリとの連携
- Jenkins UIへのアクセス

---

## 6. 受け入れ基準

### 6.1 AC-001: DSLファイル修正の確認
```gherkin
Given: infrastructure_shutdown_scheduler_job.groovyファイルが存在する
When: disabled(true)を追加してコミットする
Then: Git履歴に変更が記録される
And: 構文エラーが発生しない
```

### 6.2 AC-002: シードジョブ実行の成功確認
```gherkin
Given: DSLファイルが更新されている
When: Admin_Jobs/job-creatorを手動実行する
Then: ジョブ実行が5分以内に成功する
And: ビルド結果がSUCCESS状態になる
```

### 6.3 AC-003: ジョブ無効化状態の確認
```gherkin
Given: シードジョブが正常実行されている
When: Jenkins UIでInfrastructure_Management/Shutdown-Environment-Schedulerを確認する
Then: ジョブが「無効」状態として表示される
And: disabledアイコンが表示される
```

### 6.4 AC-004: スケジュール実行停止の確認
```gherkin
Given: ジョブが無効化されている
When: 次回スケジュール時刻（JST 0:00）に到達する
Then: 自動実行が発生しない
And: Jenkins実行履歴に新しいビルドが作成されない
```

### 6.5 AC-005: ロールバック可能性の確認
```gherkin
Given: ジョブが無効化されている
When: disabled(false)に変更してシードジョブを再実行する
Then: ジョブが有効状態に戻る
And: スケジュール実行が再開される
```

### 6.6 AC-006: 他ジョブへの影響なし確認
```gherkin
Given: シードジョブが実行されている
When: 他のインフラ管理ジョブを確認する
Then: すべてのジョブが正常状態を維持している
And: 手動停止ジョブが正常に動作する
```

---

## 7. スコープ外

### 7.1 明確にスコープ外とする事項
- **OSS-001**: 手動停止ジョブ（`Infrastructure_Management/Shutdown_Jenkins_Environment`）の変更
- **OSS-002**: スケジュール時刻の変更（無効化のみ）
- **OSS-003**: 他の環境（staging, production）への適用
- **OSS-004**: コスト管理の代替仕組みの実装
- **OSS-005**: 自動起動機能の実装

### 7.2 将来的な拡張候補
- **FEC-001**: 条件付き自動停止の実装
- **FEC-002**: コスト監視アラート機能の追加
- **FEC-003**: スケジュール時刻の動的変更機能
- **FEC-004**: 環境ごとの自動停止ポリシー設定

---

## 8. 品質ゲート確認

### ✅ 機能要件が明確に記載されている
- 5つの機能要件（FR-001〜FR-005）を具体的に定義
- 各要件に優先度を付与
- 実装可能な粒度で記述

### ✅ 受け入れ基準が定義されている
- 6つの受け入れ基準（AC-001〜AC-006）をGiven-When-Then形式で定義
- 各機能要件に対応した検証可能な基準
- 成功条件・失敗条件を明確に識別

### ✅ スコープが明確である
- スコープ内：スケジューラージョブの無効化のみ
- スコープ外：手動停止ジョブ、他環境、代替仕組み等を明記
- 将来的な拡張候補も整理

### ✅ 論理的な矛盾がない
- 機能要件と非機能要件の整合性確認
- 受け入れ基準と制約事項の矛盾なし
- Planning Documentとの戦略的一貫性確保

---

## 9. 備考

### 9.1 重要な注意事項
- 本変更は可逆的であり、将来的な再有効化が容易
- 手動停止機能は保持されるため、必要時には利用可能
- Infrastructure as Codeの原則に従い、手動設定変更は禁止

### 9.2 関連ドキュメント
- Planning Document: `.ai-workflow/issue-526/00_planning/output/planning.md`
- GitHub Issue: #526
- Jenkins CONTRIBUTION.md: `jenkins/CONTRIBUTION.md`
- Project CLAUDE.md: `CLAUDE.md`

### 9.3 レビュー・承認
本要件定義書は以下の品質ゲートを満たして作成されており、次のDesign Phaseに進む準備が完了しています。

---

**作成日**: 2025年1月17日
**作成者**: Claude Code
**バージョン**: 1.0
**関連Issue**: #526