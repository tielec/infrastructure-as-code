# 要件定義書 - Issue #456

**作成日**: 2025年1月17日
**Issue番号**: #456
**タイトル**: [jenkins] AI Workflow用の汎用フォルダを追加
**Issue URL**: https://github.com/tielec/infrastructure-as-code/issues/456

---

## 0. Planning Documentの確認

本要件定義は、Planning Phase（`.ai-workflow/issue-456/00_planning/output/planning.md`）で策定された以下の戦略に基づいて実施されます。

### Planning Phase成果物の要約

- **実装戦略**: EXTEND（既存の`folder-config.yaml`に定義を追加）
- **テスト戦略**: INTEGRATION_ONLY（シードジョブ実行による実環境確認）
- **テストコード戦略**: なし（YAML定義のため自動テスト不要）
- **複雑度**: 簡単
- **総工数**: 3〜4時間
- **リスクレベル**: 低

### Planning Documentで策定された重要な方針

1. **既存の動的フォルダ生成パターンは使用しない**
   動的フォルダ生成（`dynamic_folders`）はリポジトリごとに自動生成する機能であり、汎用フォルダの性質に合わないため、静的フォルダ定義（`folders`セクション）に追加する。

2. **フォルダ命名の一貫性**
   既存フォルダの命名規則を確認し、一貫性のある命名を採用する（例：`develop-generic`、`main-generic-1`等）。

3. **テストコード不要**
   YAML定義のみであり、Job DSLが自動処理するため、テストコードは不要。シードジョブ実行による手動確認で十分。

---

## 1. 概要

### 背景

現在、AI Workflowフォルダ配下には、**リポジトリごとに動的生成されるフォルダ**が存在します（`dynamic_folders`機能を使用）。しかし、以下のニーズが発生しました：

- **特定リポジトリに依存しない汎用的なワークフロー実行環境が必要**
  個別リポジトリのフォルダではなく、複数リポジトリで共通利用できるワークフロー実行環境を提供したい。

- **ブランチ別の実行環境分離が必要**
  - **develop**ブランチ: ai-workflow-agentの最新バージョン（新機能のテストや実験的利用）
  - **main**ブランチ: ai-workflow-agentの安定バージョン（本番環境や安定した動作が求められる場合）

### 目的

`AI_Workflow`フォルダ配下に、**特定リポジトリに依存しない汎用的なフォルダを3つ追加**し、以下を実現する：

1. **developブランチ用フォルダ（1つ）** - 最新機能のテスト・検証環境
2. **mainブランチ用フォルダ（2つ）** - 安定バージョンの本番利用環境（並行利用可能）

### ビジネス価値

- **柔軟性の向上**: リポジトリに縛られない汎用的なワークフロー実行が可能になる
- **環境分離**: developとmainで異なるバージョンを安全に使い分けられる
- **並行実行**: main用フォルダが2つあることで、複数のワークフローを同時実行可能

### 技術的価値

- **既存の動的フォルダ生成パターンを再利用しない**: 汎用フォルダは静的定義で管理し、リポジトリ依存の動的フォルダと明確に分離
- **スケーラビリティ**: 将来的に汎用フォルダを追加する際の雛形となる
- **保守性**: 静的定義により、フォルダの存在が明示的で管理しやすい

---

## 2. 機能要件

### FR-1: develop用汎用フォルダの追加（優先度：高）

- **要件ID**: FR-1
- **説明**: `AI_Workflow`フォルダ配下に、developブランチ用の汎用フォルダを1つ追加する
- **詳細**:
  - フォルダパス: `AI_Workflow/develop-generic`（最終決定はPhase 2設計で確定）
  - displayName: わかりやすい表示名（例：「汎用 - Develop」）
  - description: 用途説明（developブランチ用、最新機能のテスト環境）
  - ai-workflow-agentの**developブランチ**を使用する設定
- **受け入れ基準**:
  - Given: `folder-config.yaml`のfoldersセクションにdevelop用フォルダ定義が追加されている
  - When: シードジョブ（`Admin_Jobs/job-creator`）を実行する
  - Then: Jenkins UIに`AI_Workflow/develop-generic`フォルダが表示される
  - Then: フォルダのdisplayNameとdescriptionが正しく設定されている

### FR-2: main用汎用フォルダの追加（1つ目）（優先度：高）

- **要件ID**: FR-2
- **説明**: `AI_Workflow`フォルダ配下に、mainブランチ用の汎用フォルダ（1つ目）を追加する
- **詳細**:
  - フォルダパス: `AI_Workflow/main-generic-1`（最終決定はPhase 2設計で確定）
  - displayName: わかりやすい表示名（例：「汎用 - Main #1」）
  - description: 用途説明（mainブランチ用、安定バージョンの本番利用）
  - ai-workflow-agentの**mainブランチ**を使用する設定
- **受け入れ基準**:
  - Given: `folder-config.yaml`のfoldersセクションにmain用フォルダ定義（1つ目）が追加されている
  - When: シードジョブ（`Admin_Jobs/job-creator`）を実行する
  - Then: Jenkins UIに`AI_Workflow/main-generic-1`フォルダが表示される
  - Then: フォルダのdisplayNameとdescriptionが正しく設定されている

### FR-3: main用汎用フォルダの追加（2つ目）（優先度：高）

- **要件ID**: FR-3
- **説明**: `AI_Workflow`フォルダ配下に、mainブランチ用の汎用フォルダ（2つ目）を追加する
- **詳細**:
  - フォルダパス: `AI_Workflow/main-generic-2`（最終決定はPhase 2設計で確定）
  - displayName: わかりやすい表示名（例：「汎用 - Main #2」）
  - description: 用途説明（mainブランチ用、安定バージョンの本番利用）
  - ai-workflow-agentの**mainブランチ**を使用する設定
- **受け入れ基準**:
  - Given: `folder-config.yaml`のfoldersセクションにmain用フォルダ定義（2つ目）が追加されている
  - When: シードジョブ（`Admin_Jobs/job-creator`）を実行する
  - Then: Jenkins UIに`AI_Workflow/main-generic-2`フォルダが表示される
  - Then: フォルダのdisplayNameとdescriptionが正しく設定されている

### FR-4: 既存フォルダとの命名規則の一貫性（優先度：高）

- **要件ID**: FR-4
- **説明**: 追加する3つのフォルダは、既存フォルダの命名規則に一貫性を保つ
- **詳細**:
  - 既存フォルダの命名パターン（`Admin_Jobs`、`Code_Quality_Checker`等）を参考にする
  - アンダースコアまたはハイフン、大文字・小文字の使い分けを統一する
  - Phase 2設計で最終決定する
- **受け入れ基準**:
  - Given: 既存フォルダの命名規則を調査済み
  - When: 新しいフォルダ名を決定する
  - Then: 命名規則が既存フォルダと一貫している

### FR-5: フォルダdescriptionの明確化（優先度：中）

- **要件ID**: FR-5
- **説明**: 各フォルダのdescriptionに、用途と対象ブランチを明記する
- **詳細**:
  - developフォルダ: 「developブランチ用、最新機能のテスト環境」
  - mainフォルダ: 「mainブランチ用、安定バージョンの本番利用」
  - main用が2つある理由を説明（並行利用可能）
- **受け入れ基準**:
  - Given: フォルダがJenkins UIに表示されている
  - When: フォルダページにアクセスする
  - Then: descriptionに用途と対象ブランチが明記されている

### FR-6: コメントによる追加理由の記録（優先度：中）

- **要件ID**: FR-6
- **説明**: `folder-config.yaml`に追加する3つのフォルダ定義の上部に、Issue番号と追加理由をコメントで記載する
- **詳細**:
  - コメント例: `# Issue #456: AI Workflow用の汎用フォルダを追加`
  - 追加日とIssue URLも記載することを推奨
- **受け入れ基準**:
  - Given: `folder-config.yaml`を開く
  - When: 追加したフォルダ定義を確認する
  - Then: Issue番号と追加理由がコメントとして記載されている

---

## 3. 非機能要件

### NFR-1: パフォーマンス要件

- **要件**: シードジョブ実行時のフォルダ作成時間は、既存のフォルダ作成と同等であること（追加で5秒以上かからない）
- **理由**: 3つのフォルダ追加が全体のシードジョブ実行時間に大きな影響を与えないようにする
- **測定方法**: シードジョブのビルド時間を実行前後で比較

### NFR-2: セキュリティ要件

- **要件**: 追加するフォルダには、既存の`AI_Workflow`フォルダと同等のアクセス権限が適用されること
- **理由**: 汎用フォルダであっても、不正なアクセスを防ぐため
- **実装**: JenkinsのJob DSLが自動的に親フォルダの権限を継承する仕組みを利用

### NFR-3: 可用性・信頼性要件

- **要件**: YAML構文エラーがないこと（シードジョブが失敗しない）
- **理由**: シードジョブの失敗は全ジョブ管理に影響を与えるため
- **実装**: YAMLバリデータで事前検証（Phase 4実装で実施）

### NFR-4: 保守性・拡張性要件

- **要件**: 将来的に汎用フォルダを追加する際、同じパターンで追加できること
- **理由**: スケーラビリティを確保し、保守コストを削減
- **実装**: 静的フォルダ定義（`folders`セクション）に追加することで、拡張が容易になる

---

## 4. 制約事項

### 技術的制約

1. **既存のJob DSLスクリプトは変更しない**
   `folders.groovy`は既存のロジックで対応可能であり、変更不要。

2. **動的フォルダ生成機能は使用しない**
   汎用フォルダはリポジトリに紐付かないため、`dynamic_folders`ではなく`folders`セクションに定義する。

3. **YAML構文の制約**
   インデント（スペース2つ）、特殊文字のエスケープに注意する。

4. **Jenkins Job DSLの制約**
   フォルダパスに使用できる文字は、英数字、アンダースコア、ハイフンのみ（スラッシュは階層区切り）。

### リソース制約

1. **時間**: 総工数3〜4時間（Planning Document参照）
2. **人員**: 1名で実装可能（Issueの複雑度：簡単）
3. **環境**: Jenkins環境が稼働していること（シードジョブ実行のため）

### ポリシー制約

1. **コーディング規約**（CLAUDE.md参照）:
   - コメントは日本語で記述
   - YAML変数名はsnake_case
   - コミットメッセージ: `[jenkins] add: AI Workflow用の汎用フォルダを追加 (#456)`

2. **Git管理**:
   - すべての変更はGitで管理
   - コミット前に差分確認（意図しない変更がないか）

---

## 5. 前提条件

### システム環境

- **Jenkins環境**: 稼働中であり、シードジョブ（`Admin_Jobs/job-creator`）が実行可能な状態
- **Job DSL Plugin**: インストール済み
- **Git環境**: `infrastructure-as-code`リポジトリがクローン済み

### 依存コンポーネント

- **`folder-config.yaml`**: 既存ファイルが存在し、正しいYAML構文であること
- **`folders.groovy`**: 既存のJob DSLスクリプトが動作していること
- **シードジョブ**: `Admin_Jobs/job-creator`が正常に動作していること

### 外部システム連携

- **Git連携**: Jenkins Webhookやポーリングが設定されている場合、変更がトリガーされる可能性がある（手動実行を推奨）

---

## 6. 受け入れ基準

### AC-1: develop用フォルダが正しく作成される

- **Given**: `folder-config.yaml`にdevelop用フォルダ定義を追加した
- **When**: シードジョブ（`Admin_Jobs/job-creator`）を実行する
- **Then**:
  - Jenkins UIに`AI_Workflow/develop-generic`（またはPhase 2で決定した名前）フォルダが表示される
  - displayNameが「汎用 - Develop」（またはPhase 2で決定した表示名）である
  - descriptionに「developブランチ用、最新機能のテスト環境」が含まれる

### AC-2: main用フォルダ（1つ目）が正しく作成される

- **Given**: `folder-config.yaml`にmain用フォルダ定義（1つ目）を追加した
- **When**: シードジョブ（`Admin_Jobs/job-creator`）を実行する
- **Then**:
  - Jenkins UIに`AI_Workflow/main-generic-1`（またはPhase 2で決定した名前）フォルダが表示される
  - displayNameが「汎用 - Main #1」（またはPhase 2で決定した表示名）である
  - descriptionに「mainブランチ用、安定バージョンの本番利用」が含まれる

### AC-3: main用フォルダ（2つ目）が正しく作成される

- **Given**: `folder-config.yaml`にmain用フォルダ定義（2つ目）を追加した
- **When**: シードジョブ（`Admin_Jobs/job-creator`）を実行する
- **Then**:
  - Jenkins UIに`AI_Workflow/main-generic-2`（またはPhase 2で決定した名前）フォルダが表示される
  - displayNameが「汎用 - Main #2」（またはPhase 2で決定した表示名）である
  - descriptionに「mainブランチ用、安定バージョンの本番利用」が含まれる

### AC-4: シードジョブが成功する

- **Given**: `folder-config.yaml`に3つのフォルダ定義を追加した
- **When**: シードジョブ（`Admin_Jobs/job-creator`）を実行する
- **Then**:
  - ビルドステータスが**SUCCESS**である
  - ビルドログに3つのフォルダ作成メッセージが表示される
  - YAML構文エラーやJob DSLエラーが発生しない

### AC-5: 既存フォルダに影響がない

- **Given**: `folder-config.yaml`に3つのフォルダ定義を追加した
- **When**: シードジョブ（`Admin_Jobs/job-creator`）を実行する
- **Then**:
  - 既存の`AI_Workflow`配下の動的フォルダ（リポジトリ別）が削除されない
  - 既存のフォルダ（`Admin_Jobs`、`Code_Quality_Checker`等）に変更がない
  - フォルダの階層構造が壊れていない

### AC-6: YAML構文が正しい

- **Given**: `folder-config.yaml`を編集した
- **When**: YAMLバリデータでパースする（オンラインツールまたはyamllint）
- **Then**:
  - 構文エラーが0件である
  - インデントが正しい（スペース2つ）
  - 特殊文字が適切にエスケープされている

### AC-7: Git差分が正しい

- **Given**: `folder-config.yaml`を編集した
- **When**: `git diff`で差分を確認する
- **Then**:
  - 意図した3つのフォルダ定義のみが追加されている
  - 既存のフォルダ定義に意図しない変更がない
  - コメント行（Issue番号、追加理由）が追加されている

### AC-8: ドキュメントが更新されている（オプション）

- **Given**: フォルダ追加が完了した
- **When**: `jenkins/README.md`を確認する
- **Then**:
  - 必要に応じてフォルダ一覧表が更新されている
  - または、更新不要の理由がPhase 7ドキュメントで記録されている

---

## 7. スコープ外

本Issueでは、以下は**スコープ外**とします：

### 7.1. ジョブの作成・配置

- **理由**: 本Issueは「フォルダ構造の追加」のみを対象とし、ジョブ定義は別Issueで対応する。
- **将来的な拡張候補**: AI Workflowジョブ（all_phases、preset等）を汎用フォルダ内に配置するIssueを別途作成する。

### 7.2. 動的フォルダ生成ルールの変更

- **理由**: 汎用フォルダは静的定義で管理するため、`dynamic_folders`セクションは変更しない。
- **現状維持**: リポジトリ別の動的フォルダは従来通り`dynamic_folders`で管理する。

### 7.3. Job DSLスクリプトの変更

- **理由**: 既存の`folders.groovy`は変更不要であり、追加のロジックは不要。
- **既存ロジック再利用**: YAML定義を追加するだけで、Job DSLが自動的にフォルダを作成する。

### 7.4. パラメータ化・自動化

- **理由**: 本Issueはフォルダ追加のみであり、パラメータ化やWebhook連携は含まない。
- **将来的な拡張候補**: フォルダ作成を自動化するスクリプトやAPIを別Issueで検討する。

### 7.5. ブランチ戦略の変更

- **理由**: ai-workflow-agentのブランチ戦略（developとmainの使い分け）は既存の方針に従う。
- **現状維持**: 各フォルダで使用するブランチは、Phase 2設計で明示的に定義する。

---

## 8. 追加情報

### 8.1. 既存のフォルダ構造分析

現在の`folder-config.yaml`には以下のパターンが存在します：

1. **静的フォルダ**（`folders`セクション）:
   - `Admin_Jobs`, `Account_Setup`, `Playgrounds`等
   - パス、displayName、descriptionを明示的に定義

2. **動的フォルダ**（`dynamic_folders`セクション）:
   - `AI_Workflow`配下のリポジトリ別フォルダ
   - `Code_Quality_Checker`配下のリポジトリ別フォルダ
   - `Document_Generator`配下のリポジトリ別フォルダ

本Issueで追加する汎用フォルダは、**パターン1（静的フォルダ）**に該当します。

### 8.2. Planning Documentとの整合性

本要件定義は、Planning Documentで策定された以下の方針と整合しています：

- **実装戦略（EXTEND）**: `folder-config.yaml`に定義を追加するのみ
- **テスト戦略（INTEGRATION_ONLY）**: シードジョブ実行による実環境確認のみ
- **テストコード不要**: YAML定義のため、自動テストは不要

### 8.3. リスク軽減策

Planning Documentで特定されたリスクと軽減策：

1. **YAML構文エラー**: YAMLバリデータでパース確認（Phase 4実装で実施）
2. **シードジョブ実行失敗**: 事前にシードジョブのログを確認、エラー時は即座にロールバック
3. **命名規則の不統一**: Phase 2設計で既存フォルダの命名規則を確認
4. **既存フォルダとの競合**: `folder-config.yaml`の既存定義を確認し、重複パスがないことを確認

---

## 9. 成功基準（Definition of Success）

本要件定義が成功とみなされる条件：

1. **機能要件がすべて明確に記載されている**
   ✅ FR-1〜FR-6が具体的かつ測定可能な形で記述されている

2. **受け入れ基準が定義されている**
   ✅ AC-1〜AC-8がGiven-When-Then形式で記述されている

3. **スコープが明確である**
   ✅ スコープ外の項目（7.1〜7.5）が明示されている

4. **論理的な矛盾がない**
   ✅ 各セクション間で矛盾がない（機能要件と受け入れ基準が対応、非機能要件と制約事項が整合）

---

## 10. 次のフェーズへの引き継ぎ事項

Phase 2（設計）で決定すべき事項：

1. **フォルダ命名の最終決定**
   - develop用: `develop-generic`、`develop-common`、`generic-develop`のいずれか
   - main用: `main-generic-1`/`main-generic-2`、`main-common-1`/`main-common-2`のいずれか

2. **displayNameの最終決定**
   - 日本語または英語、表記方法の統一

3. **descriptionの詳細記述**
   - 用途、対象ブランチ、使用例を含む説明文の作成

4. **コメントの記載内容**
   - Issue番号、追加日、追加理由の記載形式

5. **README.md更新要否の判断**
   - フォルダ一覧表の更新が必要かどうかを判断

---

**要件定義書作成者**: Claude (AI Assistant)
**レビュー待ち**: Phase 1品質ゲート確認
**次のフェーズ**: Phase 2（設計）
