# 要件定義書: Planning PhaseのJenkins統合とプロンプト修正

**Issue番号**: #332
**タイトル**: [FEATURE] Planning PhaseのJenkins統合とプロンプト修正
**作成日**: 2025-10-10
**バージョン**: 1.0.0

---

## 1. 概要

### 1.1 背景

AI WorkflowのPlanning Phase（Phase 0）は、プロジェクトマネージャ役として実装戦略・テスト戦略を事前決定し、Issue複雑度分析・タスク分割・依存関係特定・リスク評価を行う重要なフェーズです。Phase 0の成果物（`planning.md`）は、後続の全Phase（requirements, design, test_scenario, implementation, testing, documentation, report）で参照されることで、一貫性のある開発プロセスが実現されるべきです。

しかし、現在の実装には以下の2つの課題があります：

1. **Jenkins統合の不在**: Planning PhaseのPythonクラス（`phases/planning.py`）は実装済みだが、Jenkinsジョブから実行できない
2. **成果物参照の未実装**: 各Phase（Phase 1-7）のプロンプトとPythonクラスがPlanning Phaseの成果物を参照していない

### 1.2 目的

本機能追加により、以下を達成します：

- **Jenkinsからの実行可能化**: ai_workflow_orchestratorジョブでPlanning Phaseを開始フェーズとして選択可能にする
- **全Phase統合**: 各PhaseがPlanning Phaseの成果物を参照し、開発計画に基づいた一貫性のある作業を実現
- **トレーサビリティ向上**: 計画書 → 要件定義 → 設計 → 実装の流れを明確にし、各フェーズの判断根拠を記録

### 1.3 ビジネス価値・技術的価値

**ビジネス価値**:
- **開発効率の向上**: Planning Phaseで事前に実装戦略とテスト戦略を決定することで、後続Phaseでの判断コストを削減
- **一貫性の確保**: 全Phaseが同じ計画書を参照することで、方針のブレを防止
- **リスク管理の強化**: Planning Phaseで特定されたリスクと軽減策を全Phaseで共有

**技術的価値**:
- **Phase 0の活用**: 既存のPlanning Phase実装（Issue #313で追加）の完全な統合
- **自動化の完成**: Jenkinsジョブで全Phase（0-7）を自動実行可能に
- **保守性の向上**: 共通ヘルパーメソッド（`_get_planning_document_path`）により、重複コードを削減

---

## 2. 機能要件

### FR-1: JenkinsジョブへのPlanning Phase統合（優先度: 高）

**説明**: ai_workflow_orchestratorジョブでPlanning Phaseを開始フェーズとして選択可能にする

**詳細要件**:
- FR-1.1: Job DSLファイル（`jenkins/jobs/dsl/ai-workflow/ai_workflow_orchestrator.groovy`）のSTART_PHASEパラメータに`planning`を追加
  - 現在の選択肢: `['requirements', 'design', 'test_scenario', 'implementation', 'testing', 'documentation', 'report']`
  - 変更後: `['planning', 'requirements', 'design', 'test_scenario', 'implementation', 'testing', 'documentation', 'report']`
  - デフォルト値を`requirements`から`planning`に変更
- FR-1.2: Jenkinsfile（`jenkins/jobs/pipeline/ai-workflow/ai-workflow-orchestrator/Jenkinsfile`）に`Planning Phase`ステージを追加
  - Phase 0実行コマンド: `python main.py execute --phase planning --issue ${ISSUE_NUMBER}`
  - Requirements Phaseステージの前に配置
  - 既存のPhaseステージと同様のエラーハンドリング（try-catch、ステータス更新）を実装

**受け入れ基準**:
- **Given**: Jenkinsでai_workflow_orchestratorジョブを開く
- **When**: START_PHASEパラメータのドロップダウンを確認
- **Then**: `planning`が選択肢に含まれており、デフォルトで選択されている

- **Given**: ISSUE_URLとSTART_PHASE=planningを指定してジョブを実行
- **When**: Jenkinsfileが実行される
- **Then**: Planning Phaseステージが実行され、`planning.md`が生成される

---

### FR-2: BasePhaseヘルパーメソッドの追加（優先度: 高）

**説明**: 全Phaseで共通利用できるPlanning Document参照ヘルパーメソッドを実装

**詳細要件**:
- FR-2.1: `scripts/ai-workflow/phases/base_phase.py`に`_get_planning_document_path()`メソッドを追加
  - 引数: `issue_number: int`
  - 戻り値: `str` - Planning Documentのパス（`@{relative_path}`形式）または警告メッセージ
  - 処理フロー:
    1. Planning Document パスを構築: `.ai-workflow/issue-{number}/00_planning/output/planning.md`
    2. ファイル存在確認
    3. 存在する場合: `working_dir`からの相対パスを取得し、`@{rel_path}`形式で返す
    4. 存在しない場合: `"Planning Phaseは実行されていません"`を返す
- FR-2.2: メソッドのdocstringを記載（引数、戻り値、動作説明）

**受け入れ基準**:
- **Given**: Planning Documentが存在する状態（`.ai-workflow/issue-123/00_planning/output/planning.md`）
- **When**: `_get_planning_document_path(123)`を呼び出す
- **Then**: `@.ai-workflow/issue-123/00_planning/output/planning.md`形式の文字列が返される

- **Given**: Planning Documentが存在しない状態
- **When**: `_get_planning_document_path(123)`を呼び出す
- **Then**: `"Planning Phaseは実行されていません"`が返される

---

### FR-3: 各Phaseプロンプトの修正（優先度: 高）

**説明**: 全Phase（Phase 1-7）のexecute.txtプロンプトにPlanning Document参照セクションを追加

**詳細要件**:
- FR-3.1: 以下7ファイルの`execute.txt`を修正
  - `scripts/ai-workflow/prompts/requirements/execute.txt`
  - `scripts/ai-workflow/prompts/design/execute.txt`
  - `scripts/ai-workflow/prompts/test_scenario/execute.txt`
  - `scripts/ai-workflow/prompts/implementation/execute.txt`
  - `scripts/ai-workflow/prompts/testing/execute.txt`
  - `scripts/ai-workflow/prompts/documentation/execute.txt`
  - `scripts/ai-workflow/prompts/report/execute.txt`
- FR-3.2: 各プロンプトに以下のセクションを追加（GitHub Issue情報セクションの前に配置）
  ```markdown
  ## 入力情報

  ### Planning Phase成果物
  - Planning Document: {planning_document_path}

  **注意**: Planning Phaseが実行されている場合、開発計画（実装戦略、テスト戦略、リスク、スケジュール）を必ず確認してください。

  ### GitHub Issue情報
  - Issue URL: {issue_url}
  - Issue Title: {issue_title}
  - Issue Body: {issue_body}
  ```
- FR-3.3: プロンプト本文に「Planning Documentの確認」タスクを追加
  - 要件定義の例: "Planning Documentで策定された開発計画を踏まえて、以下の要件定義を実施してください"
  - 設計の例: "Planning Documentの実装戦略とテスト戦略を参照し、詳細設計を行ってください"

**受け入れ基準**:
- **Given**: 修正されたプロンプトファイルを確認
- **When**: プロンプトテンプレートを読み込む
- **Then**: `{planning_document_path}`プレースホルダーが存在し、Planning Document確認の指示が含まれている

---

### FR-4: 各PhaseクラスのPlanning Document参照ロジック追加（優先度: 高）

**説明**: 全Phase（Phase 1-7）のPythonクラスで、Planning Documentのパスを取得しプロンプトに埋め込むロジックを実装

**詳細要件**:
- FR-4.1: 以下7ファイルの`execute()`メソッドを修正
  - `scripts/ai-workflow/phases/requirements.py`
  - `scripts/ai-workflow/phases/design.py`
  - `scripts/ai-workflow/phases/test_scenario.py`
  - `scripts/ai-workflow/phases/implementation.py`
  - `scripts/ai-workflow/phases/testing.py`
  - `scripts/ai-workflow/phases/documentation.py`
  - `scripts/ai-workflow/phases/report.py`
- FR-4.2: 各`execute()`メソッドに以下の処理を追加（Issue情報取得の直後）
  ```python
  # Planning Phase成果物のパス取得
  issue_number = int(self.metadata.data['issue_number'])
  planning_path_str = self._get_planning_document_path(issue_number)

  # 実行プロンプトを読み込み
  execute_prompt_template = self.load_prompt('execute')

  # プロンプトに情報を埋め込み
  execute_prompt = execute_prompt_template.replace(
      '{planning_document_path}',
      planning_path_str
  ).replace(
      '{issue_url}',
      self.metadata.data['issue_url']
  )
  # ... 以降の処理
  ```
- FR-4.3: 同様に`revise()`メソッドにもPlanning Document参照ロジックを追加（該当するPhaseのみ）

**受け入れ基準**:
- **Given**: Planning Documentが存在する状態で各Phaseを実行
- **When**: execute()メソッド内でプロンプトが生成される
- **Then**: `{planning_document_path}`が`@.ai-workflow/issue-{number}/00_planning/output/planning.md`に置換されている

- **Given**: Planning Documentが存在しない状態で各Phaseを実行
- **When**: execute()メソッド内でプロンプトが生成される
- **Then**: `{planning_document_path}`が`"Planning Phaseは実行されていません"`に置換されており、警告ログが出力される

---

### FR-5: ドキュメント更新（優先度: 中）

**説明**: Planning Phaseの使用方法と各Phaseでの参照方法を記載

**詳細要件**:
- FR-5.1: `jenkins/README.md`を更新
  - ai_workflow_orchestratorジョブのパラメータ説明にSTART_PHASE=planningを追加
  - Planning Phaseの実行例を追加
  - ワークフローの全体図にPhase 0を追加
- FR-5.2: `scripts/ai-workflow/README.md`を更新
  - Phase 0（Planning）の位置づけと重要性を説明
  - 各PhaseでのPlanning Document参照方法を記載
  - Jenkins統合セクションでPlanning Phaseジョブの説明を追加

**受け入れ基準**:
- **Given**: 更新されたREADME.mdを確認
- **When**: ai_workflow_orchestratorジョブのセクションを読む
- **Then**: Planning Phaseの実行方法とパラメータ説明が記載されている

---

## 3. 非機能要件

### NFR-1: パフォーマンス要件

- **NFR-1.1**: Planning Phase追加によるJenkinsジョブ実行時間の増加は5分以内であること
- **NFR-1.2**: `_get_planning_document_path()`メソッドの実行時間は100ms以内であること（ファイル存在確認のみ）
- **NFR-1.3**: 各Phaseのexecute()メソッドでのプロンプト生成時間の増加は無視できる範囲（10ms以内）であること

### NFR-2: 可用性・信頼性要件

- **NFR-2.1**: Planning Documentが存在しない場合でも、各Phaseは正常に実行を継続すること（警告ログ出力のみ）
- **NFR-2.2**: Planning Phase実行失敗時、Jenkinsジョブは適切にエラーステータスを返し、後続Phaseは実行されないこと
- **NFR-2.3**: Planning Documentのパス取得エラー時、明確なエラーメッセージを出力すること

### NFR-3: 保守性・拡張性要件

- **NFR-3.1**: 新しいPhaseを追加する際、BasePhaseの`_get_planning_document_path()`メソッドを再利用できること
- **NFR-3.2**: Planning Documentのパス形式を変更する場合、BasePhaseのメソッドのみ修正すればよいこと（DRY原則）
- **NFR-3.3**: プロンプトテンプレートのPlanning Document参照セクションは、全Phaseで統一されたフォーマットであること

### NFR-4: セキュリティ要件

- **NFR-4.1**: Planning Documentのパス構築時、ディレクトリトラバーサル攻撃を防ぐため、Issue番号をバリデーションすること（整数型のみ許可）
- **NFR-4.2**: Planning Documentへのファイルアクセスは読み取り専用であること

---

## 4. 制約事項

### 4.1 技術的制約

- **制約1**: Planning Phaseクラス（`phases/planning.py`）は既存実装を使用し、変更しない
  - **理由**: Issue #313で実装済み、安定動作しているため
- **制約2**: Job DSLファイルとJenkinsfileの修正は、既存のJob DSL構造とJenkinsパイプライン構造を踏襲する
  - **理由**: 他のPhaseとの一貫性、保守性の確保
- **制約3**: Claude Agent SDKの`@{path}`記法を使用してPlanning Documentを参照する
  - **理由**: Claude Codeがファイル内容を自動的に読み取る標準的な方法
- **制約4**: Planning Documentのファイル名は`planning.md`に固定
  - **理由**: PlanningPhaseクラスの出力仕様

### 4.2 リソース制約

- **制約5**: 実装期間は最大5営業日
- **制約6**: テスト環境はJenkins dev環境のみ使用（本番環境テストは別Issue）

### 4.3 ポリシー制約

- **制約7**: コーディング規約はプロジェクトのCLAUDE.md、CONTRIBUTION.mdに準拠
- **制約8**: Jenkinsパラメータ定義ルールに従う（Jenkinsfileでのパラメータ定義禁止、Job DSLファイルで定義）

---

## 5. 前提条件

### 5.1 システム環境

- **前提1**: Python 3.11以上がインストールされている
- **前提2**: Jenkins環境（dev）が稼働している
- **前提3**: Claude Agent SDK（Docker環境）が利用可能である
- **前提4**: GitHub Personal Access Token（GITHUB_TOKEN）が設定されている

### 5.2 依存コンポーネント

- **前提5**: Planning Phaseクラス（`phases/planning.py`）が実装済みである（Issue #313で追加）
- **前提6**: BasePhaseクラス（`phases/base_phase.py`）が存在し、全Phaseで継承されている
- **前提7**: MetadataManagerが`metadata.json`を正常に管理している
- **前提8**: ai_workflow_orchestratorジョブが既に存在し、Phase 1-7が実行可能である

### 5.3 外部システム連携

- **前提9**: GitHub APIが利用可能である（Issue情報取得、コメント投稿）
- **前提10**: Claude API（Sonnet 4.5）が利用可能である

---

## 6. 受け入れ基準

### AC-1: Jenkinsジョブの統合（FR-1関連）

- **Given**: Jenkinsでai_workflow_orchestratorジョブを開く
- **When**: パラメータ設定画面を確認する
- **Then**: START_PHASEパラメータで`planning`が選択可能であり、デフォルト値である

- **Given**: ISSUE_URL=https://github.com/tielec/infrastructure-as-code/issues/332、START_PHASE=planningを指定
- **When**: ジョブを実行する
- **Then**:
  - Planning Phaseステージが実行される
  - `.ai-workflow/issue-332/00_planning/output/planning.md`が生成される
  - metadata.jsonにPlanning Phaseのステータスが記録される（status: completed）

### AC-2: BasePhaseヘルパーメソッドの動作（FR-2関連）

- **Given**: Planning Documentが存在する状態（`.ai-workflow/issue-123/00_planning/output/planning.md`）
- **When**: `_get_planning_document_path(123)`を呼び出す
- **Then**: `@.ai-workflow/issue-123/00_planning/output/planning.md`が返される

- **Given**: Planning Documentが存在しない状態
- **When**: `_get_planning_document_path(123)`を呼び出す
- **Then**: `"Planning Phaseは実行されていません"`が返される

### AC-3: Phaseプロンプトの修正（FR-3関連）

- **Given**: 修正された`prompts/requirements/execute.txt`を確認
- **When**: ファイル内容を読む
- **Then**:
  - `{planning_document_path}`プレースホルダーが存在する
  - Planning Document確認の指示文が含まれている
  - 既存のIssue情報セクションが保持されている

- **Given**: 全7Phaseのexecute.txtを確認
- **When**: Planning Document参照セクションを比較
- **Then**: すべて統一されたフォーマットである

### AC-4: Phaseクラスのロジック追加（FR-4関連）

- **Given**: Planning Documentが存在する状態で`requirements.py`の`execute()`を実行
- **When**: プロンプト生成ロジックが実行される
- **Then**:
  - `_get_planning_document_path()`が呼び出される
  - `{planning_document_path}`が`@.ai-workflow/issue-{number}/00_planning/output/planning.md`に置換される
  - Claude Agent SDKに渡されるプロンプトにPlanning Documentパスが含まれる

- **Given**: Planning Documentが存在しない状態で`design.py`の`execute()`を実行
- **When**: プロンプト生成ロジックが実行される
- **Then**:
  - `{planning_document_path}`が`"Planning Phaseは実行されていません"`に置換される
  - 警告ログ`[WARNING] Planning Phase成果物が見つかりません。`が出力される
  - Phaseは正常に継続される（エラー終了しない）

### AC-5: ドキュメントの更新（FR-5関連）

- **Given**: 更新された`jenkins/README.md`を確認
- **When**: ai_workflow_orchestratorジョブのセクションを読む
- **Then**:
  - START_PHASE=planningの説明が記載されている
  - Planning Phaseの実行例が記載されている
  - ワークフローの図にPhase 0が含まれている

- **Given**: 更新された`scripts/ai-workflow/README.md`を確認
- **When**: Phase 0のセクションを読む
- **Then**:
  - Planning Phaseの位置づけと重要性が説明されている
  - 各PhaseでのPlanning Document参照方法が記載されている

### AC-6: E2Eテスト（統合受け入れ基準）

- **Given**: 新しいIssue（例: #333）を作成
- **When**: 以下の順序でai_workflow_orchestratorジョブを実行
  1. START_PHASE=planningで実行
  2. START_PHASE=requirementsで実行
  3. START_PHASE=designで実行
- **Then**:
  - Planning Phase完了後、`planning.md`が生成される
  - Requirements Phase実行時、プロンプトにPlanning Documentパスが含まれる
  - Design Phase実行時、プロンプトにPlanning Documentパスが含まれる
  - 各PhaseのGitHub Issueコメントに成果物が投稿される
  - metadata.jsonに全Phaseのステータスが記録される

---

## 7. スコープ外

以下の項目は本Issue（#332）のスコープ外とし、将来的な拡張候補とします：

### 7.1 明確にスコープ外とする事項

- **スコープ外1**: Planning Phaseクラス（`phases/planning.py`）の機能追加・修正
  - **理由**: Issue #313で実装済み、安定動作している。別Issueで対応すべき
- **スコープ外2**: `review.txt`および`revise.txt`プロンプトへのPlanning Document参照追加
  - **理由**: 優先度が低い。`execute.txt`のみで十分な効果が得られる
- **スコープ外3**: metadata.jsonへのPlanning Document情報の追加保存
  - **理由**: 現在のdesign_decisions機能で十分。追加のメタデータ管理は複雑化を招く
- **スコープ外4**: Planning Phaseのスキップ判定ロジック
  - **理由**: 現在は手動でSTART_PHASEを選択するため不要。自動判定は将来的な拡張
- **スコープ外5**: 本番環境（production）へのデプロイ
  - **理由**: dev環境での動作確認後、別Issueで本番デプロイを実施

### 7.2 将来的な拡張候補

- **拡張候補1**: Phase 0の自動実行判定
  - Planning Phaseが未実行の場合、自動的に先頭で実行する機能
- **拡張候補2**: Planning Documentの差分検出
  - Planning Documentが更新された場合、後続Phaseに通知する機能
- **拡張候補3**: Phase間の依存関係管理
  - Planning Phaseが完了していない場合、Requirements Phaseを実行不可にする制約
- **拡張候補4**: Planning Documentのバージョン管理
  - Planning Documentの履歴を管理し、各Phaseがどのバージョンを参照したか記録

---

## 8. 品質ゲート（Phase 1）

本要件定義書は、以下の品質ゲートを満たしています：

- ✅ **機能要件が明確に記載されている**: FR-1〜FR-5に機能要件を明確に定義
- ✅ **受け入れ基準が定義されている**: 各機能要件に対してGiven-When-Then形式の受け入れ基準を記載
- ✅ **スコープが明確である**: スコープ外の項目を明示し、将来的な拡張候補を整理
- ✅ **論理的な矛盾がない**: 機能要件、非機能要件、制約事項、前提条件に矛盾なし

---

## 9. 実装優先順位と依存関係

### 9.1 実装順序

以下の順序で実装することを推奨します：

**Phase 1: Jenkins統合とBasePhaseヘルパー（1-2日目）**
1. FR-2: BasePhaseヘルパーメソッドの追加
2. FR-1: JenkinsジョブへのPlanning Phase統合
3. 単体テスト: `_get_planning_document_path()`のテスト
4. 統合テスト: Jenkinsジョブでの Planning Phase 実行テスト

**Phase 2: プロンプトとクラスの修正（3-4日目）**
5. FR-3: 各Phaseプロンプトの修正（requirements → design → test_scenario → implementation → testing → documentation → report）
6. FR-4: 各PhaseクラスのPlanning Document参照ロジック追加（同順）
7. 単体テスト: 各Phaseクラスのexecute()メソッドのテスト
8. 統合テスト: Phase 0 → Phase 1 → Phase 2 の連携テスト

**Phase 3: ドキュメント更新とE2Eテスト（5日目）**
9. FR-5: ドキュメント更新（jenkins/README.md、scripts/ai-workflow/README.md）
10. E2Eテスト: 全Phase（0-7）のワークフロー実行テスト
11. レビューとフィードバック対応

### 9.2 依存関係図

```
FR-2 (BasePhaseヘルパー)
  ↓
FR-1 (Jenkins統合) ← FR-3 (プロンプト修正) ← FR-4 (クラス修正)
  ↓                     ↓                       ↓
  └─────────────────────┴───────────────────────┴→ FR-5 (ドキュメント更新)
```

---

## 10. リスクと軽減策

### リスク1: Planning Documentが存在しない場合のエラーハンドリング不足

**影響度**: 中
**発生確率**: 中
**軽減策**:
- `_get_planning_document_path()`で存在チェックを実施
- 存在しない場合でもエラー終了せず、警告ログを出力して継続
- プロンプトに「Planning Phaseは実行されていません」と明示

### リスク2: プロンプト修正の漏れ（7ファイル）

**影響度**: 高
**発生確率**: 低
**軽減策**:
- チェックリストを作成し、全7Phaseのプロンプト修正を確認
- 統一されたテンプレートを使用して、コピー&ペーストで修正
- レビュー時に全ファイルを確認

### リスク3: Jenkinsジョブの既存パイプライン破壊

**影響度**: 高
**発生確率**: 低
**軽減策**:
- Job DSLファイルとJenkinsfileのバックアップを取得
- dev環境で十分にテストした後、mainブランチにマージ
- ロールバック手順を事前に準備

### リスク4: Claude Agent SDKの@記法の誤用

**影響度**: 中
**発生確率**: 低
**軽減策**:
- Planning Phaseクラス（`planning.py`）の既存実装を参考にする
- `working_dir`からの相対パスを正しく取得する
- テストでファイルが正しく読み込まれるか確認

---

## 11. 参考情報

### 11.1 関連Issue

- **Issue #313**: Planning Phase実装
- **Issue #305**: AI Workflowの全Phase E2Eテスト

### 11.2 関連ドキュメント

- `CLAUDE.md`: プロジェクトの全体方針とコーディングガイドライン
- `scripts/ai-workflow/README.md`: AI Workflowの概要と使用方法
- `scripts/ai-workflow/ARCHITECTURE.md`: AI Workflowのアーキテクチャ設計思想
- `jenkins/README.md`: Jenkinsジョブの使用方法
- `jenkins/CONTRIBUTION.md`: Jenkins開発のベストプラクティス

### 11.3 技術仕様

- **Claude Agent SDK**: `@{path}`記法でファイル参照
- **Python**: 3.11以上
- **Job DSL**: Groovy DSL
- **Jenkinsfile**: Declarative Pipeline

---

**承認者**: （レビュー後に記入）
**承認日**: （レビュー後に記入）
