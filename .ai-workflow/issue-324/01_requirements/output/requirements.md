# 要件定義書 - Issue #324

## 0. Planning Documentの確認

Planning Phase（Phase 0）で策定された開発計画を確認しました。

### 主要な戦略と方針

- **実装戦略**: EXTEND（既存実装を拡張・補完）
- **テスト戦略**: INTEGRATION_BDD（統合テストとBDDテスト）
- **テストコード戦略**: CREATE_TEST（新規BDD & Integrationテスト作成）
- **複雑度**: 中程度
- **見積もり工数**: 12時間

### 現状認識

Planning Documentによると、`test_implementation`フェーズのコア機能は既に実装済みです：

- ✅ `scripts/ai-workflow/phases/test_implementation.py`
- ✅ `scripts/ai-workflow/prompts/test_implementation/` 配下のプロンプトファイル
- ✅ `scripts/ai-workflow/main.py`でのフェーズ統合
- ✅ metadata.jsonスキーマへの`test_implementation`フェーズ追加

### 本要件定義の目的

既に実装されているコア機能が、Issue #324の受け入れ基準を完全に満たしているかを検証し、不足している部分を明確化します。

## 1. 概要

### 背景

現在のAIワークフローでは、Phase 4（implementation）で実コードとテストコードを同時に実装しています。これには以下の課題があります：

- **責務の混在**: 実装とテストという異なる性質の作業が同一フェーズに混在
- **レビューの焦点分散**: 実装コードとテストコードを同時にレビューするため、各観点での精査が不十分になる可能性
- **並行作業の困難**: 実装とテストを別々のエンジニアが担当する場合、フェーズが分離されていないと作業しにくい
- **クリティカルシンキングレビューの精度低下**: 1つのフェーズで2つの異なる観点（実装品質とテスト品質）をレビューする必要がある

### 目的

実装フェーズとテストコード実装フェーズを分離することで、以下を実現します：

- **段階的な開発**: 実コードの実装 → テストコードの実装という明確な流れ
- **レビューの焦点化**: 各フェーズで異なる観点でレビュー可能
- **並行作業の可能性**: 実装とテスト実装を別々に進められる（将来的に）
- **クリティカルシンキングレビューの精度向上**: 各フェーズで異なるレビュー基準を適用

### ビジネス価値

- **開発品質の向上**: 実装とテストが明確に分離され、各フェーズの品質が向上
- **開発効率の向上**: フェーズごとの責務が明確化され、作業の見通しが良くなる
- **レビュー精度の向上**: 各フェーズに適したレビュー基準を適用できる

### 技術的価値

- **保守性の向上**: フェーズ分離により、ワークフローの構造がより明確になる
- **拡張性の向上**: 将来的なフェーズ追加のモデルケースとなる
- **トレーサビリティの向上**: 実装とテストの各成果物が明確に分離され、追跡が容易になる

## 2. 機能要件

### FR-001: Phase 5の新設（test_implementation）

**優先度**: 高

**詳細**:
- テストコード実装に特化した新しいフェーズを追加する
- Phase 3（test_scenario）で作成されたテストシナリオを基に実装
- Phase 4（implementation）で実装された実コードに対するテストを作成

**検証可能な基準**:
- `scripts/ai-workflow/phases/test_implementation.py`が存在する ✅（既存実装確認済み）
- Phase 5が実行された際に`test-implementation.md`が生成される
- 実際のテストファイル（test_*.py、*.test.js等）が作成される

**現状**: ✅ **実装済み**（`scripts/ai-workflow/phases/test_implementation.py:1-434`）

### FR-002: 既存フェーズの番号変更

**優先度**: 高

**詳細**:
Phase 5以降のフェーズ番号を1つずつ繰り下げる：
- Phase 5（testing）→ Phase 6（testing）
- Phase 6（documentation）→ Phase 7（documentation）
- Phase 7（report）→ Phase 8（report）

**検証可能な基準**:
- `scripts/ai-workflow/main.py`でフェーズ番号が正しく定義されている
- metadata.jsonのphasesフィールドでPhase 0-8が定義されている
- 各フェーズの実装ファイルが正しいディレクトリ構造に配置されている

**現状**: ✅ **実装済み**（`scripts/ai-workflow/main.py:108-110、182-192`）

### FR-003: Phase 4（implementation）の責務明確化

**優先度**: 高

**詳細**:
- Phase 4では実コード（ビジネスロジック、API、データモデル等）のみを実装対象とする
- テストコードはPhase 5（test_implementation）に委譲
- プロンプトを更新して責務を明確化

**検証可能な基準**:
- `prompts/implementation/execute.txt`にテストコード実装を行わない旨が明記されている
- Phase 4実行後の`implementation.md`にテストコード実装の記録がない
- Phase 5実行後の`test-implementation.md`にテストコード実装の記録がある

**現状**: ✅ **実装済み**（`scripts/ai-workflow/prompts/implementation/execute.txt:72-76、130`で明記）

### FR-004: Phase 5（test_implementation）のプロンプト作成

**優先度**: 高

**詳細**:
以下の3つのプロンプトファイルを作成：
- `prompts/test_implementation/execute.txt`: テストコード実装プロンプト
- `prompts/test_implementation/review.txt`: テストコードレビュープロンプト
- `prompts/test_implementation/revise.txt`: テストコード修正プロンプト

**検証可能な基準**:
- 各プロンプトファイルが存在する
- プロンプト内容が適切である（テスト戦略、Given-When-Then形式等）
- Phase 5実行時にプロンプトが正しく読み込まれる

**現状**: ✅ **実装済み**（`scripts/ai-workflow/prompts/test_implementation/`配下に3ファイル存在）

### FR-005: metadata.jsonの拡張

**優先度**: 高

**詳細**:
- metadata.jsonのphasesフィールドに`test_implementation`フェーズを追加
- 既存のメタデータ構造との互換性を維持
- マイグレーション機能で既存ワークフローのmetadata.jsonを自動更新

**検証可能な基準**:
- 新規作成されたmetadata.jsonに`test_implementation`フェーズが含まれている
- 既存のmetadata.jsonに対してマイグレーションが実行される
- マイグレーション後もワークフローが正常に動作する

**現状**: ❓ **要確認**（Planning Documentでは実装済みとされているが、WorkflowState.migrate()の詳細動作を検証する必要がある）

### FR-006: 依存関係の明確化

**優先度**: 中

**詳細**:
- Phase 5（test_implementation）はPhase 4（implementation）の完了が前提
- Phase 6（testing）はPhase 5（test_implementation）の完了が前提
- 依存関係をコード上で明確にする

**検証可能な基準**:
- Phase 5実行時にPhase 4が完了していない場合、エラーメッセージが表示される
- Phase 6実行時にPhase 5が完了していない場合、エラーメッセージが表示される
- 依存関係の検証ロジックが実装されている

**現状**: ❓ **要確認**（`test_implementation.py:36-59`でファイル存在確認はあるが、フェーズステータスによる依存関係チェックは未確認）

## 3. 非機能要件

### NFR-001: 後方互換性

**優先度**: 高

**詳細**:
- 既存のワークフロー（Phase 1-7構成）は引き続き動作する
- 新しいフェーズ構成（Phase 0-8）に自動マイグレーションされる
- ユーザーが明示的に操作しなくても、既存ワークフローが自動的に新構成に対応する

**検証可能な基準**:
- Phase 1-7構成の既存metadata.jsonを読み込んでも、エラーが発生しない
- マイグレーション機能が自動的に実行される
- マイグレーション後も、既存のフェーズ成果物が保持されている

**測定指標**:
- マイグレーション成功率: 100%
- マイグレーション実行時間: 1秒未満

**現状**: ❓ **要確認**（`scripts/ai-workflow/main.py:54-62`でマイグレーション処理はあるが、動作を検証する必要がある）

### NFR-002: パフォーマンス

**優先度**: 中

**詳細**:
- フェーズ追加によるオーバーヘッドは最小限
- 各フェーズの実行時間は、従来のPhase 4（実装+テスト）の時間を実装とテストで分割した程度
- メタデータ処理の追加コストは無視できる範囲

**検証可能な基準**:
- Phase 4とPhase 5の合計実行時間が、従来のPhase 4（実装+テスト）の実行時間と同等
- metadata.jsonの読み書き処理が100ms未満

**測定指標**:
- Phase 4実行時間: 従来の50%程度（テストコード実装を含まないため）
- Phase 5実行時間: 従来のPhase 4の50%程度（テストコードのみ）
- 合計実行時間: 従来のPhase 4と同等または若干改善

**現状**: ❓ **要確認**（実測が必要）

### NFR-003: ログとトレーサビリティ

**優先度**: 中

**詳細**:
- 各フェーズの実行ログを明確に分離
- Phase間の依存関係をログで追跡可能
- 成果物の生成場所が明確

**検証可能な基準**:
- Phase 4の成果物: `.ai-workflow/issue-XXX/04_implementation/output/implementation.md`
- Phase 5の成果物: `.ai-workflow/issue-XXX/05_test_implementation/output/test-implementation.md`
- 各フェーズのログファイルが独立して保存される

**測定指標**:
- ログの可読性: レビュアーが5分以内にフェーズの成果を理解できる
- トレーサビリティ: Issue番号から各フェーズの成果物を10秒以内に特定できる

**現状**: ✅ **実装済み**（`test_implementation.py:120、175-183`でoutput/test-implementation.mdが生成され、GitHub Issueにも投稿される）

## 4. 制約事項

### 技術的制約

1. **既存アーキテクチャの維持**
   - 既存のBasePhaseクラスの設計を変更しない
   - ClaudeAgentClient、GitHubClient、MetadataManagerの既存インターフェースを維持

2. **Python 3.11互換性**
   - Python 3.11で動作すること
   - 追加の外部依存ライブラリを最小限に

3. **ファイルシステム構造**
   - `.ai-workflow/issue-XXX/`配下のディレクトリ構造を維持
   - 各フェーズは独立したディレクトリに成果物を保存

4. **Git統合**
   - 各フェーズの成果物は自動的にGitコミット・プッシュされる
   - ブランチ名: `ai-workflow/issue-XXX`

### リソース制約

1. **時間制約**
   - 見積もり工数: 12時間（Planning Documentに基づく）
   - Phase 1（要件定義）: 2時間
   - 全体リリースまで: 12時間

2. **人員制約**
   - AIエージェントによる自動実装
   - レビューは人間が実施

### ポリシー制約

1. **コーディング規約**
   - CLAUDE.mdに記載された規約に準拠
   - 日本語コメント、日本語ドキュメント

2. **セキュリティポリシー**
   - GitHub TokenやAPI Keyはハードコーディング禁止
   - 環境変数経由で取得

3. **テスト戦略**
   - Phase 2（design）で決定されたテスト戦略に従う
   - 本Issue #324では、INTEGRATION_BDD戦略を採用

## 5. 前提条件

### システム環境

1. **Python環境**
   - Python 3.11以上
   - pip経由で必要なライブラリがインストール済み
   - pathlib、typing等の標準ライブラリが利用可能

2. **Git環境**
   - Gitリポジトリ内で実行
   - リモートリポジトリへのpush権限

3. **AWS環境（Jenkinsで実行する場合）**
   - EC2インスタンス（踏み台サーバー）
   - GitHub TokenとGitHub Repository環境変数が設定済み

### 依存コンポーネント

1. **BasePhaseクラス**
   - `scripts/ai-workflow/phases/base_phase.py`
   - execute()、review()、revise()、run()メソッドを提供

2. **ClaudeAgentClient**
   - `scripts/ai-workflow/core/claude_agent_client.py`
   - Claude Agent SDKとの通信を担当

3. **MetadataManager**
   - `scripts/ai-workflow/core/metadata_manager.py`
   - metadata.jsonの読み書きを担当

4. **GitHubClient**
   - `scripts/ai-workflow/core/github_client.py`
   - GitHub Issueへのコメント投稿を担当

### 外部システム連携

1. **Claude Agent SDK**
   - プロンプト実行とコード生成
   - 最大ターン数: 50ターン（test_implementation）

2. **GitHub API**
   - Issue情報の取得
   - 成果物のコメント投稿
   - 認証: GITHUB_TOKEN環境変数

## 6. 受け入れ基準

以下の受け入れ基準は、Issue #324の「受け入れ基準」セクションから抽出し、Given-When-Then形式で明確化したものです。

### AC-001: Phase 5（test_implementation）が新設されている

**Given**: AIワークフローが初期化されている
**When**: `ai-workflow execute --phase test_implementation --issue 324`を実行する
**Then**: Phase 5（test_implementation）が正常に実行され、`test-implementation.md`が生成される

### AC-002: Phase 5でテストコードのみが実装される

**Given**: Phase 4（implementation）が完了し、実コードが実装されている
**When**: Phase 5（test_implementation）を実行する
**Then**:
- テストファイル（test_*.py、*.test.js等）が作成される
- 実コード（src/配下のビジネスロジック等）は変更されない

### AC-003: Phase 4では実コードのみが実装される

**Given**: Phase 3（test_scenario）が完了している
**When**: Phase 4（implementation）を実行する
**Then**:
- 実コード（src/配下のビジネスロジック等）が作成される
- テストファイル（test_*.py等）は作成されない

### AC-004: 既存のワークフロー（Phase 1-7）は引き続き動作する

**Given**: Phase 1-7構成の既存metadata.jsonが存在する
**When**: `ai-workflow init --issue-url https://github.com/.../issues/XXX`を実行する
**Then**:
- マイグレーション処理が自動実行される
- metadata.jsonがPhase 0-8構成に更新される
- エラーが発生しない

### AC-005: Jenkinsでの自動実行が可能

**Given**: JenkinsパイプラインでAIワークフローを実行する
**When**: 全フェーズ（Phase 0-8）を順次実行する
**Then**:
- 各フェーズが正常に完了する
- 各フェーズの成果物が`.ai-workflow/issue-XXX/`配下に保存される

### AC-006: クリティカルシンキングレビューが正しく機能する

**Given**: Phase 5（test_implementation）が完了している
**When**: Phase 5のreview()メソッドを実行する
**Then**:
- レビュー結果が`PASS`、`PASS_WITH_SUGGESTIONS`、`FAIL`のいずれかで返される
- レビュー結果が`.ai-workflow/issue-XXX/05_test_implementation/review/result.md`に保存される
- レビュー結果がGitHub Issueにコメント投稿される

### AC-007: metadata.jsonにtest_implementationフェーズが記録される

**Given**: ワークフローが初期化されている
**When**: metadata.jsonを読み込む
**Then**:
- `phases`配列に`test_implementation`が含まれている
- `test_implementation`フェーズの`status`フィールドが存在する
- フェーズの順序が正しい（planning, requirements, design, test_scenario, implementation, test_implementation, testing, documentation, report）

### AC-008: 全フェーズのGit auto-commit & pushが正しく動作する

**Given**: 各フェーズが完了している
**When**: 各フェーズのrun()メソッドが実行される
**Then**:
- 成果物がGitにコミットされる
- コミットメッセージが`[ai-workflow] Phase X (phase_name) - status`形式である
- リモートリポジトリにプッシュされる

## 7. スコープ外

以下の項目は、Issue #324のスコープ外とし、将来的な拡張として別Issueで対応します：

1. **test_implementationフェーズの機能追加**
   - 既存実装の検証と修正のみ
   - 新機能追加は別Issue

2. **他のフェーズの大幅な変更**
   - Phase 4とPhase 5に関連する最小限の変更のみ
   - 他のフェーズのリファクタリングは対象外

3. **パフォーマンス最適化**
   - 動作確認と基本的なパフォーマンス測定のみ
   - 大規模な最適化は別Issue

4. **UI/UX改善**
   - Jenkinsジョブやドキュメントの最小限の更新のみ
   - 新しいダッシュボードやビューの追加は対象外

5. **並行実行機能**
   - Phase 4とPhase 5の並行実行は将来的な拡張
   - 現時点では順次実行のみ

6. **Phase番号の柔軟な変更機能**
   - Phase 0-8の固定構成のみ対応
   - フェーズのスキップや順序変更は対象外

## 8. 用語集

| 用語 | 定義 |
|------|------|
| AIワークフロー | Claude Agent SDKを使用した自動開発ワークフロー |
| Phase | ワークフローの各段階（planning, requirements, design等） |
| metadata.json | ワークフローの状態を管理するJSONファイル |
| 実コード | ビジネスロジック、API、データモデル等の本体コード |
| テストコード | 実コードをテストするためのコード（test_*.py等） |
| 受け入れ基準 | 機能が完成したと判断するための基準 |
| クリティカルシンキングレビュー | AIによる自動レビュー機能 |
| マイグレーション | 既存metadata.jsonを新しいスキーマに自動変換する処理 |
| 品質ゲート | 各フェーズが満たすべき必須要件 |

## 9. リスクと対応策

### リスク1: 既存実装が受け入れ基準を完全に満たしていない

**影響度**: 高
**確率**: 中
**対応策**:
- Phase 1で詳細な調査を実施し、不足部分を特定（本ドキュメント）
- Phase 4で不足部分を追加実装
- Phase 6で受け入れ基準8項目を全て検証

### リスク2: 後方互換性の問題（既存ワークフロー Phase 1-7 が動作しない）

**影響度**: 高
**確率**: 低
**対応策**:
- `WorkflowState.migrate()`メソッドが正しく機能するか確認
- Phase 6でBDDテストにより後方互換性を検証
- 問題があればPhase 4で修正

### リスク3: Jenkinsジョブが最新のフェーズ構成に対応していない

**影響度**: 中
**確率**: 中
**対応策**:
- Phase 1でJenkinsジョブ定義を確認
- Phase 4で必要に応じてJob DSLを修正
- Phase 6でJenkins上での動作確認（可能であれば）

### リスク4: ドキュメントの不整合（README.mdなどが古い）

**影響度**: 低
**確率**: 高
**対応策**:
- Phase 1でドキュメントの現状を確認（本ドキュメント）
- Phase 4とPhase 7でドキュメントを更新
- Phase 7で最終チェックを実施

### リスク5: テスト工数の見積もりが不足

**影響度**: 低
**確率**: 中
**対応策**:
- Phase 6で想定外の問題が発生した場合、Phase 4に戻って修正
- リトライ機能を活用して柔軟に対応
- クリティカルシンキングレビューで早期に問題を検出

## 10. 次のステップ

Phase 1（要件定義）完了後、以下のフェーズに進みます：

1. **Phase 2（設計）**: 不足部分の設計、後方互換性の設計
2. **Phase 3（テストシナリオ）**: 受け入れ基準ベースのBDD & Integrationシナリオ作成
3. **Phase 4（実装）**: ドキュメント更新、Jenkinsジョブ検証、設定ファイル検証
4. **Phase 5（テスト実装）**: BDD & Integrationテストの実装
5. **Phase 6（テスト実行）**: 受け入れ基準8項目の検証
6. **Phase 7（ドキュメント）**: README.md、CONTRIBUTION.md、CHANGELOG.mdの更新
7. **Phase 8（レポート）**: 完了報告書作成、GitHub Issueクローズ

---

**作成日**: 2025-10-12
**作成者**: AI Workflow Orchestrator (Phase 1: Requirements)
**バージョン**: 1.0
**対応Issue**: #324
