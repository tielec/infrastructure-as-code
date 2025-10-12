# テストシナリオ - Issue #362

## 📋 プロジェクト情報

- **Issue番号**: #362
- **Issue タイトル**: [FEATURE] Project Evaluation フェーズの追加
- **Issue URL**: https://github.com/tielec/infrastructure-as-code/issues/362
- **作成日**: 2025-10-12
- **Planning Document**: `.ai-workflow/issue-362/00_planning/output/planning.md`
- **Requirements Document**: `.ai-workflow/issue-362/01_requirements/output/requirements.md`
- **Design Document**: `.ai-workflow/issue-362/02_design/output/design.md`

---

## 0. Planning & Requirements & Design Document の確認

### 開発計画の確認（Planning Phase）

- **実装戦略**: CREATE（新規フェーズクラスの作成）
- **テスト戦略**: **ALL**（ユニット + インテグレーション + BDD）
- **テストコード戦略**: CREATE_TEST（新規テストファイルの作成）
- **見積もり工数**: 約18時間
- **リスクレベル**: 高

### 要件定義の確認（Requirements Phase）

主要な機能要件：

- **FR-001**: プロジェクト全体の評価実行
- **FR-002**: 判定タイプの決定（PASS/PASS_WITH_ISSUES/FAIL_PHASE_X/ABORT）
- **FR-003**: 残タスクの抽出
- **FR-004**: GitHub Issue の自動作成
- **FR-005**: メタデータの巻き戻し
- **FR-006**: 再実行の実行
- **FR-007**: ワークフローのクローズ

### 設計の確認（Design Phase）

主要なコンポーネント：

- **EvaluationPhase クラス**: Phase 9 の実装（`BasePhase` を継承）
- **MetadataManager 拡張**: `rollback_to_phase()` など4つの新規メソッド
- **GitHubClient 拡張**: `create_issue_from_evaluation()` など4つの新規メソッド
- **メタデータ構造拡張**: `evaluation` フィールドの追加

---

## 1. テスト戦略サマリー

### 選択されたテスト戦略

**ALL**（Unit + Integration + BDD）

Planning Phase（Phase 0）にて決定されたテスト戦略に基づき、以下の3つのテストレベルを実施します：

1. **ユニットテスト**: 各クラス・メソッドの単体テスト
2. **インテグレーションテスト**: コンポーネント間の連携テスト
3. **BDDテスト**: ユーザーストーリーベースのシナリオテスト

### テスト対象の範囲

**新規作成コンポーネント**:
- `EvaluationPhase` クラス（すべてのメソッド）

**拡張コンポーネント**:
- `MetadataManager`（新規メソッド4つ）
- `GitHubClient`（新規メソッド4つ）
- `WorkflowState`（migrate()メソッドの拡張）

**統合ポイント**:
- EvaluationPhase と MetadataManager の連携
- EvaluationPhase と GitHubClient の連携
- EvaluationPhase と ClaudeAgentClient の連携
- Phase 0-8 成果物の読み込みと評価フロー

### テストの目的

1. **機能正確性**: 4つの判定タイプ（PASS/PASS_WITH_ISSUES/FAIL_PHASE_X/ABORT）が正しく決定されること
2. **データ整合性**: メタデータの巻き戻し処理が正しく動作し、データ整合性が保たれること
3. **外部連携**: GitHub API（Issue作成、クローズ処理）が正しく動作すること
4. **エラーハンドリング**: API失敗、ファイルI/Oエラーなどが適切に処理されること
5. **ユーザーストーリー**: プロジェクトマネージャー視点でのワークフロー全体が正しく動作すること

---

## 2. ユニットテストシナリオ

### 2.1 EvaluationPhase クラス

#### 2.1.1 execute() メソッド

**テストケース名**: `test_execute_pass_decision`

- **目的**: PASS 判定時に evaluation_report.md が正しく生成されることを検証
- **前提条件**:
  - Phase 1-8 がすべて completed 状態
  - すべてのレビュー結果が PASS または PASS_WITH_SUGGESTIONS
  - 残タスクがゼロ
- **入力**: なし（metadata.json から状態を読み込み）
- **期待結果**:
  - `evaluation_report.md` が生成される
  - 返り値: `{'success': True, 'output': '...', 'decision': 'PASS', 'error': None}`
  - metadata.json の `evaluation.decision` が 'PASS' になる
- **テストデータ**: モックの Phase 1-8 成果物（すべて正常）

---

**テストケース名**: `test_execute_pass_with_issues_decision`

- **目的**: PASS_WITH_ISSUES 判定時に残タスクが抽出され、Issue が作成されることを検証
- **前提条件**:
  - Phase 1-8 がすべて completed 状態
  - 残タスクが2個存在（「パフォーマンス最適化」「追加テストケース」）
  - 残タスクはすべて非ブロッカー
- **入力**: なし
- **期待結果**:
  - `evaluation_report.md` に残タスクリストが記載される
  - `GitHubClient.create_issue_from_evaluation()` が呼び出される
  - 返り値: `{'success': True, 'output': '...', 'decision': 'PASS_WITH_ISSUES', 'error': None}`
  - metadata.json の `evaluation.remaining_tasks` に2個のタスクが記録される
  - metadata.json の `evaluation.created_issue_url` が設定される
- **テストデータ**: モックの Phase 1-8 成果物（残タスクあり）

---

**テストケース名**: `test_execute_fail_phase_implementation_decision`

- **目的**: FAIL_PHASE_4 判定時にメタデータが Phase 4 に巻き戻されることを検証
- **前提条件**:
  - Phase 1-8 がすべて completed 状態
  - Phase 4（Implementation）のレビュー結果が FAIL
  - または Phase 4 の成果物に重大な欠陥がある
- **入力**: なし
- **期待結果**:
  - `evaluation_report.md` に FAIL_PHASE_4 判定と理由が記載される
  - `MetadataManager.rollback_to_phase('implementation')` が呼び出される
  - 返り値: `{'success': True, 'output': '...', 'decision': 'FAIL_PHASE_IMPLEMENTATION', 'error': None}`
  - metadata.json の `evaluation.decision` が 'FAIL_PHASE_IMPLEMENTATION' になる
  - metadata.json の `evaluation.failed_phase` が 'implementation' になる
- **テストデータ**: モックの Phase 1-8 成果物（Phase 4 に問題あり）

---

**テストケース名**: `test_execute_abort_decision`

- **目的**: ABORT 判定時に Issue と PR がクローズされることを検証
- **前提条件**:
  - Phase 1-8 の実行完了
  - アーキテクチャの根本的な欠陥が発見された（例: 設計の致命的な矛盾）
- **入力**: なし
- **期待結果**:
  - `evaluation_report.md` に ABORT 判定と中止理由が記載される
  - `GitHubClient.close_issue_with_reason()` が呼び出される
  - `GitHubClient.close_pull_request()` が呼び出される
  - 返り値: `{'success': True, 'output': '...', 'decision': 'ABORT', 'error': None}`
  - metadata.json の `evaluation.decision` が 'ABORT' になる
  - metadata.json の `evaluation.abort_reason` が設定される
- **テストデータ**: モックの Phase 1-8 成果物（致命的な問題あり）

---

**テストケース名**: `test_execute_claude_agent_error`

- **目的**: Claude Agent SDK エラー時にリトライ処理が動作することを検証
- **前提条件**:
  - Phase 1-8 がすべて completed 状態
  - Claude Agent SDK が一時的にエラーを返す（1回目失敗、2回目成功）
- **入力**: なし
- **期待結果**:
  - 1回目の呼び出しが失敗し、2回目の呼び出しが成功する
  - ログに WARNING レベルのメッセージが記録される
  - 最終的に成功を返す
- **テストデータ**: モックの Claude Agent SDK（エラーをシミュレート）

---

**テストケース名**: `test_execute_phase_1_to_8_not_completed`

- **異常系**
- **目的**: Phase 1-8 が完了していない場合にエラーが返されることを検証
- **前提条件**:
  - Phase 7（Documentation）が in_progress 状態
  - Phase 8（Report）が pending 状態
- **入力**: なし
- **期待結果**:
  - 返り値: `{'success': False, 'error': 'Phase 1-8 are not all completed', ...}`
  - evaluation_report.md は生成されない
  - ログに ERROR レベルのメッセージが記録される
- **テストデータ**: metadata.json（Phase 7-8 が未完了）

---

#### 2.1.2 review() メソッド

**テストケース名**: `test_review_pass`

- **目的**: 評価レポートが品質ゲートを満たしている場合に PASS が返されることを検証
- **前提条件**:
  - `evaluation_report.md` が存在し、すべての必須セクションが記載されている
  - 判定タイプが明記されている
  - 判定理由が200文字以上
- **入力**: なし
- **期待結果**:
  - 返り値: `{'result': 'PASS', 'feedback': '...', 'suggestions': []}`
  - metadata.json の `evaluation.review_result` が 'PASS' になる
- **テストデータ**: モックの evaluation_report.md（品質ゲート満たす）

---

**テストケース名**: `test_review_pass_with_suggestions`

- **目的**: 評価レポートに軽微な改善点がある場合に PASS_WITH_SUGGESTIONS が返されることを検証
- **前提条件**:
  - `evaluation_report.md` が存在し、基本要件は満たしている
  - 判定理由が150文字（200文字未満）
- **入力**: なし
- **期待結果**:
  - 返り値: `{'result': 'PASS_WITH_SUGGESTIONS', 'feedback': '...', 'suggestions': ['判定理由をもう少し詳しく記載してください']}`
  - metadata.json の `evaluation.review_result` が 'PASS_WITH_SUGGESTIONS' になる
- **テストデータ**: モックの evaluation_report.md（軽微な問題あり）

---

**テストケース名**: `test_review_fail`

- **目的**: 評価レポートが品質ゲートを満たしていない場合に FAIL が返されることを検証
- **前提条件**:
  - `evaluation_report.md` が存在するが、判定タイプが明記されていない
  - または必須セクションが欠落している
- **入力**: なし
- **期待結果**:
  - 返り値: `{'result': 'FAIL', 'feedback': '判定タイプが明記されていません', 'suggestions': [...]}`
  - metadata.json の `evaluation.review_result` が 'FAIL' になる
- **テストデータ**: モックの evaluation_report.md（品質ゲート満たさない）

---

#### 2.1.3 _get_all_phase_outputs() メソッド

**テストケース名**: `test_get_all_phase_outputs_success`

- **目的**: Phase 0-8 の全成果物パスが正しく取得されることを検証
- **前提条件**:
  - `.ai-workflow/issue-362/` ディレクトリが存在
  - Phase 0-8 の output ディレクトリにそれぞれの成果物ファイルが存在
- **入力**: `issue_number=362`
- **期待結果**:
  - 返り値: `{'planning': Path('...planning.md'), 'requirements': Path('...requirements.md'), ..., 'report': Path('...report.md')}`
  - すべてのファイルパスが存在することを確認
- **テストデータ**: 実際のファイル構造（モック）

---

**テストケース名**: `test_get_all_phase_outputs_missing_file`

- **異常系**
- **目的**: Phase X の成果物ファイルが存在しない場合にエラーが返されることを検証
- **前提条件**:
  - Phase 4（Implementation）の成果物ファイル（implementation.md）が存在しない
- **入力**: `issue_number=362`
- **期待結果**:
  - 例外が発生: `FileNotFoundError: Phase 4 output file not found: ...`
- **テストデータ**: 不完全なファイル構造（Phase 4 ファイル欠落）

---

#### 2.1.4 _determine_decision() メソッド

**テストケース名**: `test_determine_decision_pass`

- **目的**: evaluation_report.md の内容から PASS 判定が正しく抽出されることを検証
- **前提条件**: なし
- **入力**:
  ```
  evaluation_content = \"\"\"
  ## 判定結果
  **PASS**

  ## 判定理由
  すべてのフェーズが completed 状態であり...
  \"\"\"
  ```
- **期待結果**:
  - 返り値: `{'decision': 'PASS', 'failed_phase': None, 'abort_reason': None}`
- **テストデータ**: 上記 evaluation_content

---

**テストケース名**: `test_determine_decision_pass_with_issues`

- **目的**: PASS_WITH_ISSUES 判定が正しく抽出されることを検証
- **前提条件**: なし
- **入力**:
  ```
  evaluation_content = \"\"\"
  ## 判定結果
  **PASS_WITH_ISSUES**

  ## 残タスク一覧
  - [ ] パフォーマンス最適化（Phase 4、優先度: 中）
  - [ ] 追加テストケース（Phase 6、優先度: 低）
  \"\"\"
  ```
- **期待結果**:
  - 返り値: `{'decision': 'PASS_WITH_ISSUES', 'failed_phase': None, 'abort_reason': None}`
- **テストデータ**: 上記 evaluation_content

---

**テストケース名**: `test_determine_decision_fail_phase_implementation`

- **目的**: FAIL_PHASE_4 判定が正しく抽出され、failed_phase が設定されることを検証
- **前提条件**: なし
- **入力**:
  ```
  evaluation_content = \"\"\"
  ## 判定結果
  **FAIL_PHASE_IMPLEMENTATION**

  ## 失敗フェーズ
  Phase 4（Implementation）の成果物に重大な欠陥があります...
  \"\"\"
  ```
- **期待結果**:
  - 返り値: `{'decision': 'FAIL_PHASE_IMPLEMENTATION', 'failed_phase': 'implementation', 'abort_reason': None}`
- **テストデータ**: 上記 evaluation_content

---

**テストケース名**: `test_determine_decision_abort`

- **目的**: ABORT 判定が正しく抽出され、abort_reason が設定されることを検証
- **前提条件**: なし
- **入力**:
  ```
  evaluation_content = \"\"\"
  ## 判定結果
  **ABORT**

  ## 中止理由
  アーキテクチャの根本的な欠陥が発見されたため、プロジェクトを中止します...
  \"\"\"
  ```
- **期待結果**:
  - 返り値: `{'decision': 'ABORT', 'failed_phase': None, 'abort_reason': 'アーキテクチャの根本的な欠陥が発見されたため...'}`
- **テストデータ**: 上記 evaluation_content

---

**テストケース名**: `test_determine_decision_invalid_format`

- **異常系**
- **目的**: evaluation_report.md のフォーマットが不正な場合にデフォルト判定が返されることを検証
- **前提条件**: なし
- **入力**:
  ```
  evaluation_content = \"\"\"
  ## 評価結果
  （判定タイプが記載されていない）
  \"\"\"
  ```
- **期待結果**:
  - 返り値: `{'decision': 'PASS', 'failed_phase': None, 'abort_reason': None}`（デフォルト: PASS）
  - ログに WARNING メッセージが記録される
- **テストデータ**: 上記 evaluation_content

---

#### 2.1.5 _extract_remaining_tasks() メソッド

**テストケース名**: `test_extract_remaining_tasks_success`

- **目的**: 残タスクが正しく抽出されることを検証
- **前提条件**: なし
- **入力**:
  ```
  evaluation_content = \"\"\"
  ## 残タスク一覧

  - [ ] パフォーマンス最適化（Phase 4 で発見、優先度: 中）
  - [ ] 追加テストケース作成（Phase 6 で発見、優先度: 低）
  - [ ] ドキュメント改善（Phase 7 で発見、優先度: 低）
  \"\"\"
  ```
- **期待結果**:
  - 返り値:
    ```python
    [
      {'task': 'パフォーマンス最適化', 'phase': 'implementation', 'priority': '中'},
      {'task': '追加テストケース作成', 'phase': 'testing', 'priority': '低'},
      {'task': 'ドキュメント改善', 'phase': 'documentation', 'priority': '低'}
    ]
    ```
- **テストデータ**: 上記 evaluation_content

---

**テストケース名**: `test_extract_remaining_tasks_empty`

- **目的**: 残タスクがゼロの場合に空リストが返されることを検証
- **前提条件**: なし
- **入力**:
  ```
  evaluation_content = \"\"\"
  ## 残タスク一覧

  残タスクはありません。
  \"\"\"
  ```
- **期待結果**:
  - 返り値: `[]`
- **テストデータ**: 上記 evaluation_content

---

**テストケース名**: `test_extract_remaining_tasks_missing_priority`

- **異常系**
- **目的**: 優先度が記載されていないタスクに対してデフォルト優先度が設定されることを検証
- **前提条件**: なし
- **入力**:
  ```
  evaluation_content = \"\"\"
  ## 残タスク一覧

  - [ ] パフォーマンス最適化（Phase 4 で発見）
  \"\"\"
  ```
- **期待結果**:
  - 返り値: `[{'task': 'パフォーマンス最適化', 'phase': 'implementation', 'priority': '中'}]`（デフォルト: 中）
- **テストデータ**: 上記 evaluation_content

---

#### 2.1.6 _handle_pass_with_issues() メソッド

**テストケース名**: `test_handle_pass_with_issues_success`

- **目的**: 残タスクから Issue が正しく作成されることを検証
- **前提条件**:
  - GitHub API が正常に動作する
  - 残タスクが2個存在
- **入力**:
  ```python
  remaining_tasks = [
    {'task': 'パフォーマンス最適化', 'phase': 'implementation', 'priority': '中'},
    {'task': '追加テストケース', 'phase': 'testing', 'priority': '低'}
  ]
  ```
- **期待結果**:
  - `GitHubClient.create_issue_from_evaluation()` が呼び出される
  - 返り値: `{'success': True, 'created_issue_url': 'https://github.com/.../issues/363', 'error': None}`
  - metadata.json の `evaluation.created_issue_url` が設定される
- **テストデータ**: 上記 remaining_tasks、モックの GitHubClient

---

**テストケース名**: `test_handle_pass_with_issues_api_error`

- **異常系**
- **目的**: GitHub API エラー時にログ記録されるが、ワークフローは継続されることを検証
- **前提条件**:
  - GitHub API が Rate Limit エラーを返す
  - 残タスクが1個存在
- **入力**: `remaining_tasks = [{'task': '...', 'phase': '...', 'priority': '...'}]`
- **期待結果**:
  - `GitHubClient.create_issue_from_evaluation()` が呼び出されるが失敗
  - 返り値: `{'success': True, 'created_issue_url': None, 'error': 'GitHub API rate limit exceeded'}`
  - ログに ERROR メッセージが記録される
  - ワークフローは PASS として継続
- **テストデータ**: モックの GitHubClient（エラーを返す）

---

#### 2.1.7 _handle_fail_phase_x() メソッド

**テストケース名**: `test_handle_fail_phase_implementation_success`

- **目的**: Phase 4 から巻き戻しが正しく実行されることを検証
- **前提条件**:
  - Phase 1-8 がすべて completed 状態
  - Phase 4 に問題が発見された
- **入力**: `failed_phase='implementation'`
- **期待結果**:
  - `MetadataManager.rollback_to_phase('implementation')` が呼び出される
  - 返り値: `{'success': True, 'error': None}`
  - metadata.json の `evaluation.failed_phase` が 'implementation' になる
- **テストデータ**: モックの MetadataManager

---

**テストケース名**: `test_handle_fail_phase_requirements_success`

- **目的**: Phase 1 から巻き戻しが正しく実行されることを検証
- **前提条件**:
  - Phase 1-8 がすべて completed 状態
  - Phase 1（Requirements）に根本的な問題が発見された
- **入力**: `failed_phase='requirements'`
- **期待結果**:
  - `MetadataManager.rollback_to_phase('requirements')` が呼び出される
  - 返り値: `{'success': True, 'error': None}`
  - metadata.json の Phase 1-8 のステータスが pending になる
- **テストデータ**: モックの MetadataManager

---

#### 2.1.8 _handle_abort() メソッド

**テストケース名**: `test_handle_abort_success`

- **目的**: Issue と PR が正しくクローズされることを検証
- **前提条件**:
  - GitHub Issue #362 が open 状態
  - Pull Request #123 が open 状態
- **入力**: `abort_reason='アーキテクチャの根本的な欠陥'`
- **期待結果**:
  - `GitHubClient.close_issue_with_reason(362, '...')` が呼び出される
  - `GitHubClient.close_pull_request(123, '...')` が呼び出される
  - 返り値: `{'success': True, 'error': None}`
  - metadata.json の `evaluation.abort_reason` が設定される
- **テストデータ**: モックの GitHubClient

---

**テストケース名**: `test_handle_abort_pr_not_found`

- **異常系**
- **目的**: PR が見つからない場合でも Issue はクローズされることを検証
- **前提条件**:
  - GitHub Issue #362 が open 状態
  - Pull Request が存在しない（`get_pull_request_number()` が None を返す）
- **入力**: `abort_reason='...'`
- **期待結果**:
  - `GitHubClient.close_issue_with_reason()` が呼び出される
  - `GitHubClient.close_pull_request()` は呼び出されない
  - 返り値: `{'success': True, 'error': None}`
  - ログに WARNING メッセージが記録される
- **テストデータ**: モックの GitHubClient（PR なし）

---

### 2.2 MetadataManager 拡張

#### 2.2.1 rollback_to_phase() メソッド

**テストケース名**: `test_rollback_to_phase_implementation_success`

- **目的**: Phase 4 から Phase 8 までのステータスが pending に巻き戻されることを検証
- **前提条件**:
  - Phase 1-8 がすべて completed 状態
  - metadata.json が正常に存在する
- **入力**: `phase_name='implementation'`
- **期待結果**:
  - metadata.json のバックアップファイル `metadata.json.backup_20251012_143022` が作成される
  - Phase 4-8 の `status` が 'pending' になる
  - Phase 4-8 の `started_at`, `completed_at`, `review_result` が null になる
  - Phase 4-8 の `retry_count` が 0 になる
  - 返り値: `{'success': True, 'backup_path': '...', 'rolled_back_phases': ['implementation', 'test_implementation', 'testing', 'documentation', 'report']}`
- **テストデータ**: metadata.json（全フェーズ completed）

---

**テストケース名**: `test_rollback_to_phase_requirements_success`

- **目的**: Phase 1 から Phase 8 までのすべてのフェーズが巻き戻されることを検証
- **前提条件**:
  - Phase 1-8 がすべて completed 状態
- **入力**: `phase_name='requirements'`
- **期待結果**:
  - Phase 1-8 の `status` が 'pending' になる
  - 返り値: `{'success': True, 'backup_path': '...', 'rolled_back_phases': ['requirements', 'design', 'test_scenario', 'implementation', 'test_implementation', 'testing', 'documentation', 'report']}`
- **テストデータ**: metadata.json（全フェーズ completed）

---

**テストケース名**: `test_rollback_to_phase_invalid_phase`

- **異常系**
- **目的**: 不正なフェーズ名が指定された場合にエラーが返されることを検証
- **前提条件**: なし
- **入力**: `phase_name='invalid_phase'`
- **期待結果**:
  - 例外が発生: `ValueError: Invalid phase name: invalid_phase`
  - metadata.json は変更されない
- **テストデータ**: metadata.json

---

**テストケース名**: `test_rollback_to_phase_backup_creation_failure`

- **異常系**
- **目的**: バックアップ作成失敗時にロールバックされることを検証
- **前提条件**:
  - ディスク容量不足などでバックアップファイルが作成できない
- **入力**: `phase_name='implementation'`
- **期待結果**:
  - 例外が発生: `IOError: Failed to create backup: ...`
  - metadata.json は変更されない（ロールバック）
  - 返り値: `{'success': False, 'error': 'Failed to create backup: ...'}`
- **テストデータ**: ファイルシステムエラーをシミュレート

---

#### 2.2.2 get_all_phases_status() メソッド

**テストケース名**: `test_get_all_phases_status_success`

- **目的**: 全フェーズのステータスが正しく取得されることを検証
- **前提条件**:
  - Phase 1-7 が completed 状態
  - Phase 8 が in_progress 状態
  - Phase 9（evaluation）が pending 状態
- **入力**: なし
- **期待結果**:
  - 返り値:
    ```python
    {
      'planning': 'completed',
      'requirements': 'completed',
      'design': 'completed',
      'test_scenario': 'completed',
      'implementation': 'completed',
      'test_implementation': 'completed',
      'testing': 'completed',
      'documentation': 'in_progress',
      'report': 'pending',
      'evaluation': 'pending'
    }
    ```
- **テストデータ**: metadata.json

---

#### 2.2.3 backup_metadata() メソッド

**テストケース名**: `test_backup_metadata_success`

- **目的**: metadata.json のバックアップが正しく作成されることを検証
- **前提条件**:
  - metadata.json が正常に存在する
- **入力**: なし
- **期待結果**:
  - バックアップファイル `metadata.json.backup_20251012_143022` が作成される
  - バックアップファイルの内容が元のファイルと同一である
  - 返り値: バックアップファイルパス（文字列）
- **テストデータ**: metadata.json

---

**テストケース名**: `test_backup_metadata_timestamp_format`

- **目的**: バックアップファイル名のタイムスタンプが正しいフォーマットであることを検証
- **前提条件**: metadata.json が存在する
- **入力**: なし
- **期待結果**:
  - バックアップファイル名が `metadata.json.backup_YYYYMMDD_HHMMSS` 形式である
  - 例: `metadata.json.backup_20251012_143022`
- **テストデータ**: metadata.json

---

#### 2.2.4 set_evaluation_decision() メソッド

**テストケース名**: `test_set_evaluation_decision_pass`

- **目的**: PASS 判定が metadata.json に正しく記録されることを検証
- **前提条件**: metadata.json が存在する
- **入力**:
  ```python
  decision='PASS',
  failed_phase=None,
  remaining_tasks=None,
  created_issue_url=None,
  abort_reason=None
  ```
- **期待結果**:
  - metadata.json の `evaluation.decision` が 'PASS' になる
  - その他のフィールド（failed_phase、remaining_tasks 等）が null になる
- **テストデータ**: metadata.json

---

**テストケース名**: `test_set_evaluation_decision_pass_with_issues`

- **目的**: PASS_WITH_ISSUES 判定が metadata.json に正しく記録されることを検証
- **前提条件**: metadata.json が存在する
- **入力**:
  ```python
  decision='PASS_WITH_ISSUES',
  failed_phase=None,
  remaining_tasks=[
    {'task': 'パフォーマンス最適化', 'phase': 'implementation', 'priority': '中'},
    {'task': '追加テストケース', 'phase': 'testing', 'priority': '低'}
  ],
  created_issue_url='https://github.com/.../issues/363',
  abort_reason=None
  ```
- **期待結果**:
  - metadata.json の `evaluation.decision` が 'PASS_WITH_ISSUES' になる
  - metadata.json の `evaluation.remaining_tasks` に2個のタスクが記録される
  - metadata.json の `evaluation.created_issue_url` が設定される
- **テストデータ**: metadata.json

---

**テストケース名**: `test_set_evaluation_decision_fail_phase_implementation`

- **目的**: FAIL_PHASE_IMPLEMENTATION 判定が metadata.json に正しく記録されることを検証
- **前提条件**: metadata.json が存在する
- **入力**:
  ```python
  decision='FAIL_PHASE_IMPLEMENTATION',
  failed_phase='implementation',
  remaining_tasks=None,
  created_issue_url=None,
  abort_reason=None
  ```
- **期待結果**:
  - metadata.json の `evaluation.decision` が 'FAIL_PHASE_IMPLEMENTATION' になる
  - metadata.json の `evaluation.failed_phase` が 'implementation' になる
- **テストデータ**: metadata.json

---

**テストケース名**: `test_set_evaluation_decision_abort`

- **目的**: ABORT 判定が metadata.json に正しく記録されることを検証
- **前提条件**: metadata.json が存在する
- **入力**:
  ```python
  decision='ABORT',
  failed_phase=None,
  remaining_tasks=None,
  created_issue_url=None,
  abort_reason='アーキテクチャの根本的な欠陥が発見されたため、プロジェクトを中止します'
  ```
- **期待結果**:
  - metadata.json の `evaluation.decision` が 'ABORT' になる
  - metadata.json の `evaluation.abort_reason` が設定される
- **テストデータ**: metadata.json

---

### 2.3 GitHubClient 拡張

#### 2.3.1 create_issue_from_evaluation() メソッド

**テストケース名**: `test_create_issue_from_evaluation_success`

- **目的**: 残タスクから Issue が正しく作成されることを検証
- **前提条件**:
  - GitHub API が正常に動作する
  - 残タスクが2個存在
- **入力**:
  ```python
  issue_number=362,
  remaining_tasks=[
    {'task': 'パフォーマンス最適化', 'phase': 'implementation', 'priority': '中'},
    {'task': '追加テストケース', 'phase': 'testing', 'priority': '低'}
  ],
  evaluation_report_path='.ai-workflow/issue-362/09_evaluation/output/evaluation_report.md'
  ```
- **期待結果**:
  - 新しい Issue が作成される
  - Issue タイトル: `[FOLLOW-UP] Issue #362 - 残タスク`
  - Issue 本文に残タスクリスト（チェックボックス形式）が記載される
  - ラベル: `enhancement`, `ai-workflow-follow-up`
  - 返り値: `{'success': True, 'issue_url': 'https://github.com/.../issues/363', 'issue_number': 363, 'error': None}`
- **テストデータ**: 上記 remaining_tasks、モックの GitHub API

---

**テストケース名**: `test_create_issue_from_evaluation_rate_limit_error`

- **異常系**
- **目的**: GitHub API Rate Limit エラー時にリトライ処理が動作することを検証
- **前提条件**:
  - GitHub API が Rate Limit エラーを返す（1回目）
  - 2回目のリトライで成功
- **入力**: 上記と同じ
- **期待結果**:
  - 1回目の API 呼び出しが失敗し、WARNING ログが記録される
  - 待機時間後に2回目の API 呼び出しが成功する
  - 返り値: `{'success': True, 'issue_url': '...', 'issue_number': 363, 'error': None}`
- **テストデータ**: モックの GitHub API（1回目エラー、2回目成功）

---

**テストケース名**: `test_create_issue_from_evaluation_max_retry_exceeded`

- **異常系**
- **目的**: 最大リトライ回数を超えた場合にエラーが返されることを検証
- **前提条件**:
  - GitHub API がすべてのリトライでエラーを返す（3回）
- **入力**: 上記と同じ
- **期待結果**:
  - 3回リトライ後にエラーが返される
  - 返り値: `{'success': False, 'issue_url': None, 'issue_number': None, 'error': 'GitHub API rate limit exceeded after 3 retries'}`
  - ログに ERROR メッセージが記録される
- **テストデータ**: モックの GitHub API（すべてエラー）

---

**テストケース名**: `test_create_issue_from_evaluation_empty_tasks`

- **境界値**
- **目的**: 残タスクが空の場合に Issue が作成されないことを検証
- **前提条件**: なし
- **入力**:
  ```python
  issue_number=362,
  remaining_tasks=[],
  evaluation_report_path='...'
  ```
- **期待結果**:
  - Issue は作成されない
  - 返り値: `{'success': True, 'issue_url': None, 'issue_number': None, 'error': 'No remaining tasks to create issue'}`
  - ログに INFO メッセージが記録される
- **テストデータ**: 空の remaining_tasks

---

#### 2.3.2 close_issue_with_reason() メソッド

**テストケース名**: `test_close_issue_with_reason_success`

- **目的**: Issue がクローズ理由付きでクローズされることを検証
- **前提条件**:
  - GitHub Issue #362 が open 状態
- **入力**:
  ```python
  issue_number=362,
  reason='アーキテクチャの根本的な欠陥が発見されたため、プロジェクトを中止します'
  ```
- **期待結果**:
  - Issue #362 にクローズ理由のコメントが投稿される
  - Issue #362 が closed 状態になる
  - 返り値: `{'success': True, 'error': None}`
- **テストデータ**: モックの GitHub API

---

**テストケース名**: `test_close_issue_with_reason_not_found`

- **異常系**
- **目的**: Issue が存在しない場合にエラーが返されることを検証
- **前提条件**:
  - GitHub Issue #999 が存在しない
- **入力**: `issue_number=999, reason='...'`
- **期待結果**:
  - 例外が発生: `GithubException: 404 Not Found`
  - 返り値: `{'success': False, 'error': '404 Not Found'}`
- **テストデータ**: モックの GitHub API（404エラー）

---

#### 2.3.3 close_pull_request() メソッド

**テストケース名**: `test_close_pull_request_success`

- **目的**: Pull Request がクローズされることを検証
- **前提条件**:
  - Pull Request #123 が open 状態
- **入力**:
  ```python
  pr_number=123,
  comment='プロジェクト評価の結果、ワークフローを中止します'
  ```
- **期待結果**:
  - PR #123 にコメントが投稿される
  - PR #123 が closed 状態になる
  - 返り値: `{'success': True, 'error': None}`
- **テストデータ**: モックの GitHub API

---

#### 2.3.4 get_pull_request_number() メソッド

**テストケース名**: `test_get_pull_request_number_success`

- **目的**: Issue番号から PR番号が正しく取得されることを検証
- **前提条件**:
  - Issue #362 に関連する PR #123 が存在する
  - PR のブランチ名が `ai-workflow/issue-362`
- **入力**: `issue_number=362`
- **期待結果**:
  - 返り値: `123`
- **テストデータ**: モックの GitHub API

---

**テストケース名**: `test_get_pull_request_number_not_found`

- **異常系**
- **目的**: 関連する PR が見つからない場合に None が返されることを検証
- **前提条件**:
  - Issue #362 に関連する PR が存在しない
- **入力**: `issue_number=362`
- **期待結果**:
  - 返り値: `None`
  - ログに WARNING メッセージが記録される
- **テストデータ**: モックの GitHub API（PR なし）

---

### 2.4 WorkflowState マイグレーション

#### 2.4.1 migrate() メソッド（evaluation フィールド追加）

**テストケース名**: `test_migrate_add_evaluation_field`

- **目的**: 既存の metadata.json に evaluation フィールドが追加されることを検証
- **前提条件**:
  - metadata.json に evaluation フィールドが存在しない（古いバージョン）
- **入力**: なし
- **期待結果**:
  - metadata.json に `evaluation` フィールドが追加される
  - evaluation フィールドの内容:
    ```json
    {
      "status": "pending",
      "retry_count": 0,
      "started_at": null,
      "completed_at": null,
      "review_result": null,
      "decision": null,
      "failed_phase": null,
      "remaining_tasks": [],
      "created_issue_url": null,
      "abort_reason": null
    }
    ```
  - ログに INFO メッセージが記録される: `[INFO] Migrating metadata.json: Adding evaluation phase`
- **テストデータ**: metadata.json（evaluation フィールドなし）

---

**テストケース名**: `test_migrate_evaluation_already_exists`

- **目的**: evaluation フィールドが既に存在する場合にマイグレーションがスキップされることを検証
- **前提条件**:
  - metadata.json に evaluation フィールドが既に存在する（最新バージョン）
- **入力**: なし
- **期待結果**:
  - metadata.json は変更されない
  - マイグレーションログが記録されない
- **テストデータ**: metadata.json（evaluation フィールドあり）

---

## 3. インテグレーションテストシナリオ

### 3.1 Phase 0-8 → Phase 9 評価フロー

**シナリオ名**: Phase 0-8 完了後の評価フロー（PASS判定）

- **目的**: Phase 1-8 の成果物を読み込み、評価し、PASS 判定が下されるまでの統合フローを検証
- **前提条件**:
  - Phase 1-8 がすべて completed 状態
  - すべてのレビュー結果が PASS または PASS_WITH_SUGGESTIONS
  - 残タスクがゼロ
  - metadata.json が正常に存在する
- **テスト手順**:
  1. `python main.py execute --phase evaluation --issue 362` を実行
  2. EvaluationPhase.execute() が Phase 1-8 の成果物を読み込む
  3. Claude Agent SDK でプロジェクト全体を評価
  4. evaluation_report.md が生成される
  5. 判定タイプが PASS と決定される
  6. metadata.json が更新される（evaluation.decision = 'PASS'）
  7. ワークフロー完了
- **期待結果**:
  - `.ai-workflow/issue-362/09_evaluation/output/evaluation_report.md` が生成される
  - evaluation_report.md に「判定結果: PASS」が記載される
  - metadata.json の `evaluation.status` が 'completed' になる
  - metadata.json の `evaluation.decision` が 'PASS' になる
  - ログに INFO メッセージが記録される: `[INFO] Evaluation completed: PASS`
- **確認項目**:
  - [ ] evaluation_report.md が存在する
  - [ ] 判定結果が PASS である
  - [ ] metadata.json が正しく更新されている
  - [ ] Phase 1-8 の成果物が変更されていない
  - [ ] ワークフローが正常終了している

---

**シナリオ名**: Phase 0-8 完了後の評価フロー（PASS_WITH_ISSUES判定）

- **目的**: PASS_WITH_ISSUES 判定時に残タスクが抽出され、Issue が自動作成されることを検証
- **前提条件**:
  - Phase 1-8 がすべて completed 状態
  - 残タスクが2個存在（Phase 4 と Phase 6 で発見）
  - GitHub API が正常に動作する
- **テスト手順**:
  1. `python main.py execute --phase evaluation --issue 362` を実行
  2. EvaluationPhase.execute() が Phase 1-8 の成果物を読み込む
  3. Claude Agent SDK で評価実行、PASS_WITH_ISSUES 判定
  4. _extract_remaining_tasks() で残タスクを抽出（2個）
  5. _handle_pass_with_issues() で GitHub Issue を作成
  6. metadata.json が更新される
  7. ワークフロー完了
- **期待結果**:
  - evaluation_report.md に「判定結果: PASS_WITH_ISSUES」が記載される
  - 新しい GitHub Issue #363 が作成される
  - Issue タイトル: `[FOLLOW-UP] Issue #362 - 残タスク`
  - Issue 本文に残タスクリスト（2個）が記載される
  - metadata.json の `evaluation.decision` が 'PASS_WITH_ISSUES' になる
  - metadata.json の `evaluation.remaining_tasks` に2個のタスクが記録される
  - metadata.json の `evaluation.created_issue_url` が設定される
- **確認項目**:
  - [ ] evaluation_report.md に残タスクリストが記載されている
  - [ ] GitHub Issue #363 が作成されている
  - [ ] Issue に正しいラベル（enhancement, ai-workflow-follow-up）が付与されている
  - [ ] metadata.json が正しく更新されている
  - [ ] ワークフローが正常終了している

---

**シナリオ名**: Phase 0-8 完了後の評価フロー（FAIL_PHASE_4判定）

- **目的**: FAIL_PHASE_4 判定時にメタデータが巻き戻され、Phase 4 から再実行可能になることを検証
- **前提条件**:
  - Phase 1-8 がすべて completed 状態
  - Phase 4（Implementation）の成果物に重大な問題がある
- **テスト手順**:
  1. `python main.py execute --phase evaluation --issue 362` を実行
  2. EvaluationPhase.execute() が Phase 1-8 の成果物を読み込む
  3. Claude Agent SDK で評価実行、FAIL_PHASE_4 判定
  4. _handle_fail_phase_x('implementation') でメタデータを巻き戻し
  5. MetadataManager.rollback_to_phase('implementation') が実行される
  6. metadata.json のバックアップが作成される
  7. Phase 4-8 のステータスが pending に変更される
  8. ワークフロー完了（Phase 4 から再実行可能）
- **期待結果**:
  - evaluation_report.md に「判定結果: FAIL_PHASE_IMPLEMENTATION」が記載される
  - metadata.json のバックアップファイル `metadata.json.backup_20251012_143022` が作成される
  - metadata.json の Phase 4-8 の `status` が 'pending' になる
  - metadata.json の `evaluation.decision` が 'FAIL_PHASE_IMPLEMENTATION' になる
  - metadata.json の `evaluation.failed_phase` が 'implementation' になる
  - ログに INFO メッセージが記録される: `[INFO] Rolled back to phase: implementation`
- **確認項目**:
  - [ ] バックアップファイルが作成されている
  - [ ] Phase 4-8 のステータスが pending になっている
  - [ ] Phase 1-3 のステータスは completed のまま
  - [ ] `python main.py execute --phase all --issue 362` で Phase 4 から再実行可能
  - [ ] データ整合性が保たれている

---

**シナリオ名**: Phase 0-8 完了後の評価フロー（ABORT判定）

- **目的**: ABORT 判定時に Issue と PR がクローズされ、ワークフローが停止することを検証
- **前提条件**:
  - Phase 1-8 がすべて completed 状態
  - アーキテクチャの根本的な欠陥が発見された
  - GitHub Issue #362 が open 状態
  - Pull Request #123 が open 状態
- **テスト手順**:
  1. `python main.py execute --phase evaluation --issue 362` を実行
  2. EvaluationPhase.execute() が Phase 1-8 の成果物を読み込む
  3. Claude Agent SDK で評価実行、ABORT 判定
  4. _handle_abort('アーキテクチャの根本的な欠陥') が実行される
  5. GitHubClient.close_issue_with_reason(362, '...') が実行される
  6. GitHubClient.close_pull_request(123, '...') が実行される
  7. metadata.json が更新される
  8. ワークフロー停止
- **期待結果**:
  - evaluation_report.md に「判定結果: ABORT」が記載される
  - GitHub Issue #362 にクローズ理由のコメントが投稿される
  - GitHub Issue #362 が closed 状態になる
  - Pull Request #123 にコメントが投稿される
  - Pull Request #123 が closed 状態になる
  - metadata.json の `evaluation.decision` が 'ABORT' になる
  - metadata.json の `evaluation.abort_reason` が設定される
  - ログに INFO メッセージが記録される: `[INFO] Workflow aborted: ...`
- **確認項目**:
  - [ ] Issue #362 がクローズされている
  - [ ] PR #123 がクローズされている
  - [ ] クローズコメントが適切に投稿されている
  - [ ] metadata.json に中止理由が記録されている
  - [ ] ワークフローが停止している

---

### 3.2 GitHub API 連携テスト

**シナリオ名**: Issue 自動作成の統合テスト

- **目的**: 残タスクから GitHub Issue が正しく作成されることを検証（実際の GitHub API を使用）
- **前提条件**:
  - GitHub API Token が設定されている（`GITHUB_TOKEN` 環境変数）
  - リポジトリへのアクセス権限がある
  - 残タスクが3個存在
- **テスト手順**:
  1. `GitHubClient.create_issue_from_evaluation()` を呼び出す
  2. 残タスクリストを Issue 本文に整形
  3. GitHub API で Issue を作成（POST /repos/{owner}/{repo}/issues）
  4. ラベルを付与（enhancement, ai-workflow-follow-up）
  5. 作成された Issue の URL を取得
- **期待結果**:
  - 新しい Issue が GitHub リポジトリに作成される
  - Issue タイトル: `[FOLLOW-UP] Issue #362 - 残タスク`
  - Issue 本文に残タスクリスト（チェックボックス形式）が記載される
  - ラベル: `enhancement`, `ai-workflow-follow-up`
  - Issue URL が返される
- **確認項目**:
  - [ ] GitHub UI で Issue を確認できる
  - [ ] Issue 本文が正しくフォーマットされている
  - [ ] ラベルが正しく付与されている
  - [ ] Issue URL が有効である

---

**シナリオ名**: Issue/PR クローズの統合テスト

- **目的**: Issue と PR が正しくクローズされることを検証（実際の GitHub API を使用）
- **前提条件**:
  - GitHub API Token が設定されている
  - テスト用の Issue #362 と PR #123 が open 状態
- **テスト手順**:
  1. `GitHubClient.close_issue_with_reason(362, 'テスト中止理由')` を呼び出す
  2. Issue #362 にクローズコメントを投稿
  3. Issue #362 を closed 状態に変更
  4. `GitHubClient.close_pull_request(123, 'テスト中止理由')` を呼び出す
  5. PR #123 にコメントを投稿
  6. PR #123 を closed 状態に変更
- **期待結果**:
  - Issue #362 が closed 状態になる
  - Issue #362 にクローズコメントが投稿されている
  - PR #123 が closed 状態になる
  - PR #123 にコメントが投稿されている
- **確認項目**:
  - [ ] GitHub UI で Issue がクローズされていることを確認
  - [ ] GitHub UI で PR がクローズされていることを確認
  - [ ] クローズコメントが適切に投稿されている

---

### 3.3 メタデータ巻き戻しの統合テスト

**シナリオ名**: Phase 4 から Phase 8 への巻き戻しとデータ整合性

- **目的**: メタデータ巻き戻し処理が正しく動作し、データ整合性が保たれることを検証
- **前提条件**:
  - Phase 1-8 がすべて completed 状態
  - metadata.json が正常に存在する
- **テスト手順**:
  1. `MetadataManager.rollback_to_phase('implementation')` を呼び出す
  2. metadata.json のバックアップを作成
  3. Phase 4-8 のステータスを pending に変更
  4. Phase 4-8 の started_at, completed_at, review_result を null に設定
  5. metadata.json を保存
  6. バックアップファイルと現在のファイルを比較
- **期待結果**:
  - バックアップファイル `metadata.json.backup_20251012_143022` が作成される
  - Phase 4-8 の `status` が 'pending' になる
  - Phase 1-3 の `status` は 'completed' のまま
  - Phase 4-8 の `started_at`, `completed_at`, `review_result` が null になる
  - バックアップファイルには元の Phase 4-8 の状態が保存されている
- **確認項目**:
  - [ ] バックアップファイルが存在する
  - [ ] バックアップファイルの内容が元の metadata.json と同一
  - [ ] Phase 4-8 のステータスが正しく変更されている
  - [ ] Phase 1-3 のステータスが変更されていない
  - [ ] JSON フォーマットが正しい

---

**シナリオ名**: 巻き戻し失敗時のロールバック

- **目的**: 巻き戻し処理が失敗した場合にロールバックされることを検証
- **前提条件**:
  - Phase 1-8 がすべて completed 状態
  - ディスク容量不足などで保存に失敗する状況をシミュレート
- **テスト手順**:
  1. `MetadataManager.rollback_to_phase('implementation')` を呼び出す
  2. バックアップ作成は成功
  3. metadata.json の更新時にエラーが発生（IOError）
  4. ロールバック処理が実行される（バックアップから復元）
  5. エラーが返される
- **期待結果**:
  - metadata.json が元の状態に戻る（Phase 4-8 が completed のまま）
  - 返り値: `{'success': False, 'error': 'Failed to save metadata: ...'}`
  - ログに ERROR メッセージが記録される
  - ログに INFO メッセージが記録される: `[INFO] Rolled back to backup: ...`
- **確認項目**:
  - [ ] metadata.json が元の状態に戻っている
  - [ ] バックアップファイルが残っている
  - [ ] エラーメッセージが適切に記録されている

---

### 3.4 エンドツーエンド評価フロー

**シナリオ名**: Phase 0 から Phase 9 までの完全な実行フロー

- **目的**: Phase 0（Planning）から Phase 9（Evaluation）までの完全なワークフローが正しく動作することを検証
- **前提条件**:
  - GitHub Issue #999 が新規作成されている（テスト用）
  - metadata.json が存在しない（新規ワークフロー）
- **テスト手順**:
  1. `python main.py execute --phase all --issue 999` を実行
  2. Phase 0（Planning）が実行される
  3. Phase 1（Requirements）が実行される
  4. Phase 2（Design）が実行される
  5. Phase 3（Test Scenario）が実行される
  6. Phase 4（Implementation）が実行される
  7. Phase 5（Test Implementation）が実行される
  8. Phase 6（Testing）が実行される
  9. Phase 7（Documentation）が実行される
  10. Phase 8（Report）が実行される
  11. Phase 9（Evaluation）が実行される
  12. 評価結果に応じた後続処理が実行される
- **期待結果**:
  - すべてのフェーズが completed 状態になる（または Phase X から再実行）
  - evaluation_report.md が生成される
  - 判定タイプに応じた処理が実行される（PASS/PASS_WITH_ISSUES/FAIL_PHASE_X/ABORT）
  - metadata.json にすべてのフェーズの情報が記録される
  - ワークフローが正常終了する（または Phase X から再実行可能な状態になる）
- **確認項目**:
  - [ ] Phase 0-9 の成果物がすべて生成されている
  - [ ] metadata.json が正しく更新されている
  - [ ] evaluation_report.md に判定結果が記載されている
  - [ ] 判定に応じた後続処理が実行されている
  - [ ] ワークフロー全体が正常終了している

---

## 4. BDDテストシナリオ

### 4.1 Feature: プロジェクト評価機能

```gherkin
Feature: プロジェクト評価機能
  As a プロジェクトマネージャー
  I want Phase 1-8 の成果物を総合的に評価し、次のアクションを判定する
  So that プロジェクトの品質を保証し、適切な後続処理を実行できる

  Background:
    Given AI Workflow が正常にセットアップされている
    And GitHub API Token が設定されている
    And Issue #362 が open 状態である

  Scenario: プロジェクトが合格と判定される（PASS）
    Given Phase 1-8 がすべて completed 状態である
    And すべてのレビュー結果が PASS または PASS_WITH_SUGGESTIONS である
    And 残タスクがゼロである
    When Phase 9（Evaluation）を実行する
    Then evaluation_report.md が生成される
    And 判定結果が "PASS" である
    And metadata.json の evaluation.decision が "PASS" になる
    And ワークフローが完了する

  Scenario: 残タスクが新Issueとして作成される（PASS_WITH_ISSUES）
    Given Phase 1-8 がすべて completed 状態である
    And 残タスクが2個存在する
      | タスク                   | フェーズ          | 優先度 |
      | パフォーマンス最適化     | implementation    | 中     |
      | 追加テストケース作成     | testing           | 低     |
    And 残タスクはすべて非ブロッカーである
    When Phase 9（Evaluation）を実行する
    Then evaluation_report.md が生成される
    And 判定結果が "PASS_WITH_ISSUES" である
    And 残タスクリストが evaluation_report.md に記載される
    And 新しい GitHub Issue #363 が作成される
    And Issue タイトルが "[FOLLOW-UP] Issue #362 - 残タスク" である
    And Issue 本文に残タスクリスト（2個）が記載される
    And metadata.json の evaluation.created_issue_url が設定される
    And ワークフローが完了する

  Scenario: 特定フェーズから再実行される（FAIL_PHASE_IMPLEMENTATION）
    Given Phase 1-8 がすべて completed 状態である
    And Phase 4（Implementation）の成果物に重大な問題がある
    And Phase 4 のレビュー結果が FAIL である
    When Phase 9（Evaluation）を実行する
    Then evaluation_report.md が生成される
    And 判定結果が "FAIL_PHASE_IMPLEMENTATION" である
    And metadata.json のバックアップファイルが作成される
    And Phase 4-8 のステータスが "pending" になる
    And Phase 1-3 のステータスは "completed" のままである
    And metadata.json の evaluation.failed_phase が "implementation" になる
    And ログに "Rolled back to phase: implementation" が記録される
    And Phase 4 から再実行可能な状態になる

  Scenario: プロジェクトが中止される（ABORT）
    Given Phase 1-8 がすべて completed 状態である
    And アーキテクチャの根本的な欠陥が発見された
    And Pull Request #123 が open 状態である
    When Phase 9（Evaluation）を実行する
    Then evaluation_report.md が生成される
    And 判定結果が "ABORT" である
    And GitHub Issue #362 にクローズ理由が投稿される
    And GitHub Issue #362 が closed 状態になる
    And Pull Request #123 にコメントが投稿される
    And Pull Request #123 が closed 状態になる
    And metadata.json の evaluation.abort_reason が設定される
    And ワークフローが停止する

  Scenario: GitHub API エラー時にワークフローが継続される
    Given Phase 1-8 がすべて completed 状態である
    And 残タスクが1個存在する
    And GitHub API が Rate Limit エラーを返す
    When Phase 9（Evaluation）を実行する
    Then evaluation_report.md が生成される
    And 判定結果が "PASS_WITH_ISSUES" である
    And Issue 作成が失敗する
    And ログに ERROR メッセージが記録される
    And ワークフローは PASS として継続する
    And evaluation_report.md に "手動 Issue 作成が必要" と記載される

  Scenario: Claude Agent SDK エラー時にリトライされる
    Given Phase 1-8 がすべて completed 状態である
    And Claude Agent SDK が一時的にエラーを返す
    When Phase 9（Evaluation）を実行する
    Then 1回目の評価が失敗する
    And ログに WARNING メッセージが記録される
    And 2回目の評価が自動的にリトライされる
    And 2回目の評価が成功する
    And evaluation_report.md が生成される
    And ワークフローが完了する
```

---

### 4.2 Feature: メタデータ巻き戻し機能

```gherkin
Feature: メタデータ巻き戻し機能
  As a プロジェクトマネージャー
  I want 特定フェーズの成果物に問題がある場合、そのフェーズから再実行する
  So that 問題を修正し、プロジェクトを正常に完了できる

  Background:
    Given AI Workflow が正常にセットアップされている
    And Phase 1-8 がすべて completed 状態である
    And metadata.json が正常に存在する

  Scenario: Phase 4 から Phase 8 までが巻き戻される
    Given Phase 4（Implementation）に問題が発見された
    When MetadataManager.rollback_to_phase("implementation") を実行する
    Then metadata.json のバックアップファイルが作成される
    And バックアップファイル名が "metadata.json.backup_YYYYMMDD_HHMMSS" 形式である
    And Phase 4-8 のステータスが "pending" になる
    And Phase 4-8 の started_at, completed_at, review_result が null になる
    And Phase 1-3 のステータスは "completed" のままである
    And Phase 4 から再実行可能な状態になる

  Scenario: Phase 1 からすべてのフェーズが巻き戻される
    Given Phase 1（Requirements）に根本的な問題が発見された
    When MetadataManager.rollback_to_phase("requirements") を実行する
    Then metadata.json のバックアップファイルが作成される
    And Phase 1-8 のステータスが "pending" になる
    And Phase 0（Planning）のステータスは "completed" のままである
    And Phase 1 から再実行可能な状態になる

  Scenario: 巻き戻し後に再実行が成功する
    Given Phase 4 から Phase 8 までが巻き戻された状態である
    When python main.py execute --phase all --issue 362 を実行する
    Then Phase 4（Implementation）から実行が開始される
    And Phase 5-8 が順次実行される
    And Phase 9（Evaluation）が実行される
    And すべてのフェーズが completed 状態になる

  Scenario: 巻き戻し失敗時にロールバックされる
    Given ディスク容量不足で保存に失敗する状況である
    When MetadataManager.rollback_to_phase("implementation") を実行する
    Then バックアップ作成は成功する
    And metadata.json の更新時にエラーが発生する
    And ロールバック処理が実行される
    And metadata.json が元の状態に戻る
    And エラーメッセージが返される
    And ログに ERROR メッセージが記録される
```

---

### 4.3 Feature: GitHub Issue 自動作成機能

```gherkin
Feature: GitHub Issue 自動作成機能
  As a プロジェクトマネージャー
  I want 残タスクを新しい Issue として自動作成する
  So that 追加タスクを体系的に管理できる

  Background:
    Given AI Workflow が正常にセットアップされている
    And GitHub API Token が設定されている
    And Issue #362 が完了した状態である

  Scenario: 残タスクから新しい Issue が作成される
    Given 残タスクが3個存在する
      | タスク                     | フェーズ          | 優先度 |
      | パフォーマンス最適化       | implementation    | 中     |
      | 追加テストケース作成       | testing           | 低     |
      | ドキュメント改善           | documentation     | 低     |
    When GitHubClient.create_issue_from_evaluation() を実行する
    Then 新しい GitHub Issue #363 が作成される
    And Issue タイトルが "[FOLLOW-UP] Issue #362 - 残タスク" である
    And Issue 本文に以下の内容が記載される
      """
      ## 概要
      AI Workflow Issue #362 の実装完了後に発見された残タスクです。

      ## 残タスク一覧
      - [ ] パフォーマンス最適化（Phase 4 で発見、優先度: 中）
      - [ ] 追加テストケース作成（Phase 6 で発見、優先度: 低）
      - [ ] ドキュメント改善（Phase 7 で発見、優先度: 低）

      ## 関連
      - 元Issue: #362
      - 元PR: #123
      - Evaluation Report: .ai-workflow/issue-362/09_evaluation/output/evaluation_report.md
      """
    And ラベル "enhancement", "ai-workflow-follow-up" が付与される
    And Issue URL が返される

  Scenario: GitHub API Rate Limit エラー時にリトライされる
    Given 残タスクが1個存在する
    And GitHub API が Rate Limit エラーを返す（1回目）
    And GitHub API が成功を返す（2回目）
    When GitHubClient.create_issue_from_evaluation() を実行する
    Then 1回目の API 呼び出しが失敗する
    And ログに WARNING メッセージが記録される
    And 待機時間後に2回目の API 呼び出しが実行される
    And 2回目の API 呼び出しが成功する
    And 新しい Issue が作成される

  Scenario: 最大リトライ回数を超えた場合にエラーが返される
    Given 残タスクが1個存在する
    And GitHub API がすべてのリトライでエラーを返す
    When GitHubClient.create_issue_from_evaluation() を実行する
    Then 3回リトライが実行される
    And すべてのリトライが失敗する
    And エラーが返される
    And ログに ERROR メッセージが記録される
    And ワークフローは PASS として継続する

  Scenario: 残タスクがゼロの場合に Issue が作成されない
    Given 残タスクが0個である
    When GitHubClient.create_issue_from_evaluation() を実行する
    Then Issue は作成されない
    And ログに INFO メッセージが記録される
    And 返り値に "No remaining tasks to create issue" が含まれる
```

---

## 5. テストデータ

### 5.1 Phase 1-8 成果物データ（モック）

**シナリオ1: すべて正常（PASS判定用）**

- **planning.md**: 実装戦略 CREATE、テスト戦略 ALL、見積もり工数 18時間
- **requirements.md**: 機能要件 FR-001 ~ FR-007、受け入れ基準 AC-001 ~ AC-007
- **design.md**: EvaluationPhase クラス設計、メソッドシグネチャ、データ構造設計
- **test-scenario.md**: ユニット・インテグレーション・BDD シナリオ（本ドキュメント）
- **implementation.md**: すべての機能が実装完了、コード品質 PEP 8 準拠
- **test-implementation.md**: ユニット・インテグレーション・BDD テストコード実装完了
- **test-result.md**: すべてのテストが PASS、カバレッジ 95%
- **documentation-update-log.md**: README.md 更新、Phase 9 の説明追加
- **report.md**: プロジェクト完了、すべての品質ゲート満たす

**metadata.json の状態**:
- Phase 1-8: すべて `status: "completed"`, `review_result: "PASS"` または `"PASS_WITH_SUGGESTIONS"`
- 残タスク: なし

---

**シナリオ2: 残タスクあり（PASS_WITH_ISSUES判定用）**

- Phase 1-8 の成果物は基本的に正常
- **implementation.md**: 「今後のパフォーマンス最適化が望ましい」と記載
- **test-result.md**: 「追加テストケース（エッジケース）の作成を推奨」と記載
- **documentation-update-log.md**: 「ドキュメントのサンプルコード追加が望ましい」と記載

**metadata.json の状態**:
- Phase 1-8: すべて `status: "completed"`
- 残タスク: 3個（パフォーマンス最適化、追加テストケース、ドキュメント改善）

---

**シナリオ3: Phase 4 に問題あり（FAIL_PHASE_4判定用）**

- **implementation.md**: 「一部の機能が未実装」「エラーハンドリングが不十分」と記載
- **test-result.md**: 「Phase 4 の実装に関連するテストが複数失敗」と記載

**metadata.json の状態**:
- Phase 4: `review_result: "FAIL"`
- Phase 5-8: `status: "completed"`（Phase 4 の問題により後続フェーズも影響を受ける可能性）

---

**シナリオ4: 致命的な問題あり（ABORT判定用）**

- **design.md**: 「アーキテクチャに根本的な矛盾がある」「選定した技術スタックが要件を満たせない」と記載
- **implementation.md**: 「設計の問題により実装が困難」と記載

**metadata.json の状態**:
- Phase 2: `review_result: "FAIL"`
- Phase 4: `status: "failed"`（実装が困難なため）

---

### 5.2 evaluation_report.md サンプル

**PASS 判定のサンプル**:

```markdown
# プロジェクト評価レポート - Issue #362

## 評価サマリー

Phase 1-8 の全成果物を評価した結果、プロジェクトは要件を満たしており、すべての品質ゲートを通過しています。

## 判定結果

**PASS**

## 判定理由

すべてのフェーズが completed 状態であり、レビュー結果が PASS または PASS_WITH_SUGGESTIONS です。残タスクはゼロであり、ブロッカーが存在しません。プロジェクトは正常に完了しました。

## 各フェーズの評価結果

| フェーズ | ステータス | レビュー結果 | 評価 |
|---------|----------|------------|------|
| Phase 1: Requirements | completed | PASS | ✅ 正常 |
| Phase 2: Design | completed | PASS_WITH_SUGGESTIONS | ✅ 正常 |
| Phase 3: Test Scenario | completed | PASS | ✅ 正常 |
| Phase 4: Implementation | completed | PASS | ✅ 正常 |
| Phase 5: Test Implementation | completed | PASS | ✅ 正常 |
| Phase 6: Testing | completed | PASS_WITH_SUGGESTIONS | ✅ 正常 |
| Phase 7: Documentation | completed | PASS | ✅ 正常 |
| Phase 8: Report | completed | PASS | ✅ 正常 |

## 完全性チェック結果

✅ すべての成果物が存在し、必要な情報が記載されている
✅ 各フェーズの品質ゲートを満たしている

## 一貫性チェック結果

✅ フェーズ間で矛盾や不整合がない
✅ Requirements → Design → Implementation → Testing のトレーサビリティが確保されている

## 品質チェック結果

✅ すべての成果物が品質ゲートを満たしている
✅ レビュー結果が PASS または PASS_WITH_SUGGESTIONS

## 残タスク一覧

残タスクはありません。

---
**作成日**: 2025-10-12
**評価者**: Claude AI (Phase 9 - Evaluation)
```

---

**PASS_WITH_ISSUES 判定のサンプル**:

```markdown
# プロジェクト評価レポート - Issue #362

## 評価サマリー

Phase 1-8 の全成果物を評価した結果、基本要件は満たしていますが、将来的な改善タスクが存在します。

## 判定結果

**PASS_WITH_ISSUES**

## 判定理由

すべてのフェーズが completed 状態であり、基本要件は満たしています。しかし、パフォーマンス最適化、追加テストケース、ドキュメント改善といった非ブロッカーの残タスクが存在します。これらは将来の改善として新しい Issue で管理します。

## 各フェーズの評価結果

（表は省略）

## 残タスク一覧

以下のタスクが残っており、新しい Issue として作成されます：

- [ ] パフォーマンス最適化（Phase 4 で発見、優先度: 中）
  - evaluation.py の execute() メソッドの処理時間短縮
  - Phase 1-8 成果物の並列読み込み実装

- [ ] 追加テストケース作成（Phase 6 で発見、優先度: 低）
  - エッジケースのテストケース追加
  - 境界値テストの拡充

- [ ] ドキュメント改善（Phase 7 で発見、優先度: 低）
  - README.md にサンプルコード追加
  - TROUBLESHOOTING.md 作成

## 次のアクション

残タスクを新しい GitHub Issue として自動作成します。

---
**作成日**: 2025-10-12
**評価者**: Claude AI (Phase 9 - Evaluation)
```

---

### 5.3 metadata.json サンプル

**Phase 1-8 completed、evaluation 追加後**:

```json
{
  "issue_number": "362",
  "issue_url": "https://github.com/tielec/infrastructure-as-code/issues/362",
  "issue_title": "[FEATURE] Project Evaluation フェーズの追加",
  "workflow_version": "2.0",
  "created_at": "2025-10-12T10:00:00Z",
  "updated_at": "2025-10-12T18:00:00Z",
  "current_phase": "evaluation",
  "phases": {
    "planning": {
      "status": "completed",
      "retry_count": 0,
      "started_at": "2025-10-12T10:00:00Z",
      "completed_at": "2025-10-12T11:00:00Z",
      "review_result": "N/A"
    },
    "requirements": {
      "status": "completed",
      "retry_count": 0,
      "started_at": "2025-10-12T11:00:00Z",
      "completed_at": "2025-10-12T12:00:00Z",
      "review_result": "PASS"
    },
    "design": {
      "status": "completed",
      "retry_count": 0,
      "started_at": "2025-10-12T12:00:00Z",
      "completed_at": "2025-10-12T13:00:00Z",
      "review_result": "PASS_WITH_SUGGESTIONS"
    },
    "test_scenario": {
      "status": "completed",
      "retry_count": 0,
      "started_at": "2025-10-12T13:00:00Z",
      "completed_at": "2025-10-12T14:00:00Z",
      "review_result": "PASS"
    },
    "implementation": {
      "status": "completed",
      "retry_count": 1,
      "started_at": "2025-10-12T14:00:00Z",
      "completed_at": "2025-10-12T15:30:00Z",
      "review_result": "PASS"
    },
    "test_implementation": {
      "status": "completed",
      "retry_count": 0,
      "started_at": "2025-10-12T15:30:00Z",
      "completed_at": "2025-10-12T16:00:00Z",
      "review_result": "PASS"
    },
    "testing": {
      "status": "completed",
      "retry_count": 0,
      "started_at": "2025-10-12T16:00:00Z",
      "completed_at": "2025-10-12T16:30:00Z",
      "review_result": "PASS_WITH_SUGGESTIONS"
    },
    "documentation": {
      "status": "completed",
      "retry_count": 0,
      "started_at": "2025-10-12T16:30:00Z",
      "completed_at": "2025-10-12T17:00:00Z",
      "review_result": "PASS"
    },
    "report": {
      "status": "completed",
      "retry_count": 0,
      "started_at": "2025-10-12T17:00:00Z",
      "completed_at": "2025-10-12T17:30:00Z",
      "review_result": "PASS"
    },
    "evaluation": {
      "status": "completed",
      "retry_count": 0,
      "started_at": "2025-10-12T17:30:00Z",
      "completed_at": "2025-10-12T18:00:00Z",
      "review_result": "PASS",
      "decision": "PASS_WITH_ISSUES",
      "failed_phase": null,
      "remaining_tasks": [
        {
          "task": "パフォーマンス最適化",
          "phase": "implementation",
          "priority": "中"
        },
        {
          "task": "追加テストケース作成",
          "phase": "testing",
          "priority": "低"
        }
      ],
      "created_issue_url": "https://github.com/tielec/infrastructure-as-code/issues/363",
      "abort_reason": null
    }
  },
  "design_decisions": {
    "implementation_strategy": "CREATE",
    "test_strategy": "ALL",
    "test_code_strategy": "CREATE_TEST"
  },
  "cost_tracking": {
    "total_input_tokens": 150000,
    "total_output_tokens": 50000,
    "total_cost_usd": 12.5
  }
}
```

---

## 6. テスト環境要件

### 6.1 必要なテスト環境

**ローカル開発環境**:
- Python 3.8 以上
- pytest 7.0 以上
- pytest-mock（モック作成用）
- pytest-bdd（BDDテスト用）
- coverage（カバレッジ測定用）

**CI/CD 環境**:
- GitHub Actions（推奨）
- Python 3.8, 3.9, 3.10, 3.11 のマトリックステスト
- pytest による自動テスト実行
- カバレッジレポート生成（codecov 連携）

### 6.2 必要な外部サービス

**GitHub API**:
- GitHub Personal Access Token（`repo` スコープ）
- テスト用リポジトリ（または本番リポジトリの Issue/PR）
- Rate Limit: 5000 requests/hour（通常は十分）

**Claude Agent SDK**:
- Anthropic API Key
- Claude Agent SDK クライアント設定
- API コスト制限の設定（テスト時は低コストモデル使用）

### 6.3 モック/スタブの必要性

**モックが必要なコンポーネント**:
- **GitHub API**: ユニットテストではモック使用、インテグレーションテストでは実際の API 使用
- **Claude Agent SDK**: ユニットテストではモック使用、インテグレーションテストでは実際の SDK 使用
- **ファイルシステム**: 一部のテストではメモリ内ファイルシステム（`tempfile`）を使用

**モックライブラリ**:
- `pytest-mock`（pytest の fixture として使用）
- `unittest.mock`（Python 標準ライブラリ）

### 6.4 テストデータの管理

**テストデータの配置**:
- `tests/fixtures/`: テストデータファイルを配置
  - `phase_outputs/`: Phase 1-8 の成果物サンプル（4シナリオ）
  - `metadata/`: metadata.json サンプル（複数パターン）
  - `evaluation_reports/`: evaluation_report.md サンプル（4判定タイプ）

**テストデータの生成**:
- `tests/conftest.py` で pytest fixture として定義
- テスト実行時に動的に生成（`tempfile.mkdtemp()` 使用）

---

## 7. 品質ゲート確認

本テストシナリオは、Phase 3 の品質ゲートを満たしていることを確認します：

- [x] **Phase 2の戦略に沿ったテストシナリオである**: テスト戦略 ALL に基づき、ユニット・インテグレーション・BDD シナリオを作成
- [x] **主要な正常系がカバーされている**: 4つの判定タイプ（PASS/PASS_WITH_ISSUES/FAIL_PHASE_X/ABORT）の正常系シナリオを網羅
- [x] **主要な異常系がカバーされている**: GitHub API エラー、Claude Agent SDK エラー、ファイル I/O エラー、巻き戻し失敗などの異常系を網羅
- [x] **期待結果が明確である**: すべてのテストケースに具体的な期待結果（返り値、状態変化、ログ出力等）を記載

---

## 8. テストシナリオのサマリー

### 8.1 テストケース数

**ユニットテスト**: 40 テストケース
- EvaluationPhase: 15 テストケース
- MetadataManager: 11 テストケース
- GitHubClient: 9 テストケース
- WorkflowState: 2 テストケース
- その他: 3 テストケース

**インテグレーションテスト**: 10 シナリオ
- Phase 0-8 → Phase 9 評価フロー: 4 シナリオ
- GitHub API 連携: 2 シナリオ
- メタデータ巻き戻し: 2 シナリオ
- エンドツーエンド: 2 シナリオ

**BDDテスト**: 15 シナリオ
- プロジェクト評価機能: 6 シナリオ
- メタデータ巻き戻し機能: 5 シナリオ
- GitHub Issue 自動作成機能: 4 シナリオ

**合計**: 65 テストケース/シナリオ

### 8.2 カバレッジ目標

- **ユニットテスト**: 90% 以上（目標: 95%）
- **インテグレーションテスト**: 主要ユースケース 100% カバー
- **BDDテスト**: ユーザーストーリー 100% カバー

### 8.3 見積もりテスト実行時間

- **ユニットテスト**: 約5分（モック使用）
- **インテグレーションテスト**: 約15分（実際の API 使用）
- **BDDテスト**: 約10分
- **合計**: 約30分

---

## 9. まとめ

### テスト戦略の確認

本テストシナリオは、Planning Phase（Phase 0）で決定されたテスト戦略 **ALL**（Unit + Integration + BDD）に基づき、以下の3つのテストレベルを網羅的に作成しました：

1. **ユニットテスト（40ケース）**: 各メソッドの正常系・異常系・境界値をカバー
2. **インテグレーションテスト（10シナリオ）**: コンポーネント間の連携と外部システム統合をカバー
3. **BDDテスト（15シナリオ）**: プロジェクトマネージャー視点のユーザーストーリーをカバー

### 主要なテスト観点

- **機能正確性**: 4つの判定タイプ（PASS/PASS_WITH_ISSUES/FAIL_PHASE_X/ABORT）の正確性
- **データ整合性**: メタデータ巻き戻し処理の整合性
- **外部連携**: GitHub API、Claude Agent SDK の連携
- **エラーハンドリング**: API エラー、ファイル I/O エラーの適切な処理
- **ユーザーストーリー**: プロジェクトマネージャー視点でのワークフロー全体

### 期待される効果

- **品質保証**: 65個のテストケースにより、Phase 9 の品質を保証
- **回帰防止**: 将来の変更時に回帰バグを早期発見
- **ドキュメント**: テストシナリオ自体が仕様書として機能
- **信頼性**: 高カバレッジ（目標95%）により、実装の信頼性を担保

### 次のステップ

Phase 4（実装）に進み、本テストシナリオに基づいて実装を行います。実装完了後、Phase 5（テストコード実装）で本シナリオを実際のテストコードに変換します。

---

**作成日**: 2025-10-12
**作成者**: Claude AI (Phase 3 - Test Scenario)
**テスト戦略**: ALL（Unit + Integration + BDD）
**テストケース総数**: 65ケース
**カバレッジ目標**: 95%
**見積もりテスト実行時間**: 約30分
