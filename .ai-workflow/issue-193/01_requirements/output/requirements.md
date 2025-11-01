# 要件定義書 - Issue #193

**Issue**: [TASK] Lambda Teardown Pipeline用のforce_destroyパラメータのドキュメント化
**Issue URL**: https://github.com/tielec/infrastructure-as-code/issues/193
**作成日**: 2025年度
**Planning Document**: @planning.md を参照

---

## 0. Planning Documentの確認

### 開発計画の概要

Planning Documentで策定された主要な方針：

- **実装戦略**: EXTEND（既存ファイルへの追記）
  - 新規ファイル作成は不要
  - 既存ドキュメントとJob DSLファイルへの追記のみ

- **テスト戦略**: UNIT_ONLY（ドキュメント検証のみ）
  - 実際のコード実行テストは不要
  - ドキュメントの正確性と可読性のレビュー

- **複雑度**: 簡単
  - 見積もり工数: 2~3時間
  - リスク: 低（ドキュメントのみの更新）

- **影響範囲**:
  1. `jenkins/jobs/dsl/infrastructure/infrastructure_ansible_playbook_executor_job.groovy` - パラメータコメント追加
  2. `jenkins/README.md` - Lambda Teardown Pipelineジョブの使用方法追記
  3. `ansible/README.md` - 実行例と注意事項の追記

Planning Documentで特定された実装済みロジック（`ansible/playbooks/lambda/lambda_teardown_pipeline.yml` 66-69行目）:
- 非対話モード（CI/Jenkins）では `force_destroy=true` が必須
- 設定されていない場合は安全のため処理を停止
- 誤操作による本番環境削除を防ぐセーフガード機能

---

## 1. 概要

### 背景

現在、Lambda Teardown Pipeline（`ansible/playbooks/lambda/lambda_teardown_pipeline.yml`）は、Jenkins（非対話モード）から実行する場合、`force_destroy=true` パラメータの明示的な設定を必須としている。これは、誤操作による本番環境リソースの削除を防ぐためのセーフガード機能として実装されている（プレイブック66-69行目）。

しかし、この重要なパラメータ要件が、JenkinsジョブのパラメータドキュメントやREADMEに明記されていないため、ユーザーが実行時にエラーで停止し、混乱する可能性がある。

### 目的

Jenkins Job DSLファイルおよび関連ドキュメント（`jenkins/README.md`、`ansible/README.md`）に `force_destroy` パラメータの要件を明記し、ユーザーが迷わず安全に Lambda リソースの削除を実行できるようにする。

### ビジネス価値・技術的価値

- **ビジネス価値**:
  - ユーザーエクスペリエンスの向上（エラーによる試行錯誤の削減）
  - 誤操作リスクの低減（本番環境の誤削除防止）
  - 運用効率の向上（ドキュメント参照で自己解決可能）

- **技術的価値**:
  - ドキュメントの完全性向上（既存機能の網羅的な説明）
  - 保守性の向上（後続開発者が仕様を理解しやすい）
  - セーフガード機能の可視化（セキュリティ意識の向上）

---

## 2. 機能要件

### FR-001: Job DSLファイルへのパラメータコメント追加【高】

- **要件**: `jenkins/jobs/dsl/infrastructure/infrastructure_ansible_playbook_executor_job.groovy` の `ANSIBLE_EXTRA_VARS` パラメータ定義箇所にコメントを追加
- **詳細**:
  - Lambda Teardown Pipeline実行時には `force_destroy=true` が必要であることを明記
  - コメント内に具体的な実行例を記載
  - 既存のパラメータ説明と整合性のある記述スタイルを維持
- **受け入れ基準**:
  - Given: Job DSLファイルを開いたとき
  - When: ANSIBLE_EXTRA_VARSパラメータ定義を確認する
  - Then: force_destroyパラメータに関するコメントが存在し、実行例が記載されている

### FR-002: jenkins/README.mdへのジョブ使用方法追記【高】

- **要件**: `jenkins/README.md` に Lambda Teardown Pipeline ジョブの使用方法を追記
- **詳細**:
  - 「重要なジョブの詳細」セクションに新規サブセクション「Lambda Teardown Pipeline」を追加
  - パラメータ一覧に `force_destroy` の説明を追記
  - 実行例（`force_destroy=true` を含む）を記載
  - 削除実行時の確認プロンプトについて記載
  - 既存のジョブドキュメントと同じフォーマットを踏襲
- **受け入れ基準**:
  - Given: jenkins/README.mdを開いたとき
  - When: Lambda Teardown Pipelineセクションを確認する
  - Then: 目的、パラメータ、実行例、注意事項が明確に記載されている

### FR-003: ansible/README.mdへの実行例追記【高】

- **要件**: `ansible/README.md` の Lambda関連セクションに実行例と注意事項を追記
- **詳細**:
  - Lambda Teardown Pipeline の実行例に `force_destroy=true` を明記
  - 非対話モードでの必須パラメータであることを注記
  - `destroy_ssm=true` との組み合わせ例も追記
  - 既存のAnsibleプレイブック実行例と同じフォーマットを維持
- **受け入れ基準**:
  - Given: ansible/README.mdを開いたとき
  - When: Lambda Teardown Pipelineの実行例を確認する
  - Then: force_destroy=trueを含む実行例が記載され、非対話モードでの必須要件が明記されている

### FR-004: ドキュメント間の整合性確保【中】

- **要件**: 3つのファイル（Job DSL、jenkins/README.md、ansible/README.md）間で、force_destroyパラメータの説明が一貫している
- **詳細**:
  - 同一のパラメータ名、デフォルト値、実行例を使用
  - 説明文の内容が矛盾しない
  - 実行例の環境名（dev/prod）が適切
- **受け入れ基準**:
  - Given: 3つのファイルを並べて比較したとき
  - When: force_destroyパラメータの説明を確認する
  - Then: パラメータ名、実行例、説明文が一貫している

---

## 3. 非機能要件

### NFR-001: 可読性

- 追加するドキュメントは、技術的な知識が中程度のユーザー（Ansible初心者～中級者）でも理解できる平易な日本語で記述する
- コードブロック（```）を使用してコマンド例を視覚的に明確に示す

### NFR-002: 保守性

- 既存のドキュメント構造を維持し、後続の開発者が容易に更新できるようにする
- Markdownの見出しレベル（#, ##, ###）を既存のスタイルに合わせる

### NFR-003: 正確性

- プレイブックの実装（66-69行目）と完全に一致する説明を記載する
- 誤った情報により、ユーザーが誤操作を行わないようにする

### NFR-004: 一貫性

- プロジェクト内の他のドキュメント（jenkins/README.md、ansible/README.md）のスタイルと統一する
- 用語（例：「非対話モード」「CI/Jenkins」）を統一して使用する

---

## 4. 制約事項

### 技術的制約

- **既存コードの変更禁止**: Ansibleプレイブック（`lambda_teardown_pipeline.yml`）の実装は既に正しく動作しているため、変更してはならない
- **Job DSLの構造維持**: Job DSLファイルの既存パラメータ定義構造を変更してはならない
- **Markdownフォーマット**: README.mdファイルはMarkdown形式を維持し、既存のレンダリング環境（GitHub、Jenkins等）で正しく表示される必要がある

### リソース制約

- **作業時間**: 2~3時間以内に完了させる（Planning Documentの見積もり）
- **影響範囲**: 3ファイルのみの変更に限定（新規ファイル作成は行わない）

### ポリシー制約

- **コーディング規約**: CLAUDE.mdで定義されたコーディング規約（日本語コメント、コミットメッセージ形式）に従う
- **ドキュメント規約**:
  - README.md: エンドユーザー向け（使い方、実行方法）
  - CONTRIBUTION.md: 開発者向け（実装方法、ベストプラクティス）
  - 今回はREADME.mdのみを更新（CONTRIBUTION.mdは不要）

---

## 5. 前提条件

### システム環境

- Ansible 2.9以上がインストールされている
- Jenkins 2.426.1以上が動作している
- `lambda_teardown_pipeline.yml` プレイブックが正しく実装されている（66-69行目のチェックロジック）

### 依存コンポーネント

- **Job DSLプラグイン**: Jenkins上でJob DSLが動作している
- **GitHub連携**: ドキュメントがGitHubリポジトリで管理されている
- **SSM Parameter Store**: Ansibleプレイブックが AWS SSM Parameter Storeと連携している

### 外部システム連携

- なし（ドキュメント更新のみのため）

---

## 6. 受け入れ基準

### AC-001: Job DSLファイルのコメント追加

- **Given**: `infrastructure_ansible_playbook_executor_job.groovy` ファイルを開く
- **When**: `ANSIBLE_EXTRA_VARS` パラメータ定義（115行目付近）を確認する
- **Then**: 以下の内容が記載されている
  - Lambda Teardown Pipeline実行時に `force_destroy=true` が必須であること
  - 具体的な実行例（`env=dev force_destroy=true`）
  - 既存のパラメータ説明文と矛盾しない

### AC-002: jenkins/README.mdへのセクション追加

- **Given**: `jenkins/README.md` ファイルを開く
- **When**: 「重要なジョブの詳細」セクションを確認する
- **Then**: 以下の内容が記載されている
  - 新規サブセクション「Lambda Teardown Pipeline」が存在する
  - 目的、パラメータ一覧、実行例、注意事項が記載されている
  - 実行例に `force_destroy=true` が含まれている
  - 削除実行時の確認プロンプトについて記載されている

### AC-003: ansible/README.mdへの実行例追記

- **Given**: `ansible/README.md` ファイルを開く
- **When**: Lambda Teardown Pipelineの実行例（124行目付近）を確認する
- **Then**: 以下の内容が記載されている
  - `force_destroy=true` を含む実行例が記載されている
  - 非対話モード（CI/Jenkins）での必須要件が明記されている
  - `destroy_ssm=true` との組み合わせ例も記載されている

### AC-004: ドキュメントの一貫性確認

- **Given**: 3つのファイル（Job DSL、jenkins/README.md、ansible/README.md）を並べて確認する
- **When**: `force_destroy` パラメータの説明と実行例を比較する
- **Then**: パラメータ名、実行例、説明文に矛盾がなく、一貫している

### AC-005: 誤字脱字のチェック

- **Given**: 更新した3つのファイルを確認する
- **When**: テキスト全体を読む
- **Then**: 誤字脱字がなく、日本語として自然な文章である

### AC-006: Markdownレンダリング確認

- **Given**: GitHub上で README.md ファイルを表示する
- **When**: 追加したセクションを確認する
- **Then**: 見出し、コードブロック、箇条書きが正しくレンダリングされている

---

## 7. スコープ外

以下の項目は今回のIssueのスコープ外とし、将来的な拡張候補として記録する：

### スコープ外項目

1. **Ansibleプレイブックの実装変更**
   - プレイブックの66-69行目のロジックは既に正しく実装されているため、変更しない
   - `force_destroy` パラメータのデフォルト値の変更も行わない

2. **Jenkinsfileの変更**
   - パラメータ定義はJob DSLで行うため、Jenkinsfile（`ansible-playbook-executor/Jenkinsfile`）の変更は不要

3. **実装テストの実施**
   - ドキュメント更新のみのため、実際のプレイブック実行テストは不要
   - Planning Documentのテスト戦略（UNIT_ONLY）に従う

4. **他のプレイブックへの同様のドキュメント追加**
   - Jenkins Teardown Pipelineなど、他のteardownプレイブックへの同様のドキュメント追加は別Issueで対応

5. **CONTRIBUTION.mdの更新**
   - 開発者向けガイドラインの追加は今回は不要（ユーザー向けREADMEのみ更新）

6. **自動化スクリプトの作成**
   - ドキュメント整合性チェックスクリプトなどの自動化ツールは今回は作成しない

### 将来的な拡張候補

- Jenkins UIから `force_destroy` パラメータをチェックボックス化（`booleanParam`）
- 他のteardownプレイブック（jenkins_teardown_pipeline.ymlなど）への同様のドキュメント追加
- ドキュメント整合性を自動チェックするCI/CDパイプラインの構築

---

## 品質ゲート（Phase 1）チェックリスト

以下の品質ゲートは**必須要件**です：

- [x] **機能要件が明確に記載されている**: FR-001～FR-004で具体的に定義
- [x] **受け入れ基準が定義されている**: AC-001～AC-006で検証可能な形式（Given-When-Then）で記述
- [x] **スコープが明確である**: スコープ外項目を明記し、将来拡張候補も記載
- [x] **論理的な矛盾がない**: Planning Documentの戦略（EXTEND、UNIT_ONLY）と整合性あり

---

## 参考情報

### 関連ファイル

- **Ansibleプレイブック**: `ansible/playbooks/lambda/lambda_teardown_pipeline.yml` (66-69行目)
- **Job DSL**: `jenkins/jobs/dsl/infrastructure/infrastructure_ansible_playbook_executor_job.groovy`
- **ドキュメント**:
  - `jenkins/README.md`
  - `ansible/README.md`

### 実装済みの動作（確認事項）

プレイブック（66-69行目）では、以下のチェックが既に実装されています：

```yaml
- name: Check force_destroy in non-interactive mode
  ansible.builtin.fail:
    msg: |
      Running in non-interactive mode (CI/Jenkins).
      To destroy resources, you must explicitly set 'force_destroy=true'
      Example: ansible-playbook lambda_teardown_pipeline.yml -e "env=dev force_destroy=true"
  when:
    - not is_interactive | bool
    - force_destroy is not defined or not force_destroy | bool
```

このロジックにより、Jenkinsから実行する場合は `force_destroy=true` が必須となっています。

### 追記する実行例（設計案）

**Jenkinsから実行する場合**:
```
ANSIBLE_EXTRA_VARS: "env=dev force_destroy=true"
```

**SSMパラメータも削除する場合**:
```
ANSIBLE_EXTRA_VARS: "env=dev force_destroy=true destroy_ssm=true"
```

---

**レビュー時の確認ポイント**:
- [ ] Planning Documentの戦略（EXTEND、UNIT_ONLY）に沿っているか
- [ ] 機能要件が検証可能な形で記述されているか
- [ ] 受け入れ基準がGiven-When-Then形式で明確か
- [ ] スコープ外項目が明確に定義されているか
- [ ] ブロッカー（次フェーズに進めない問題）が存在しないか
