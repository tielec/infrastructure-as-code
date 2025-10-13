# テストシナリオ - Issue #380

## プロジェクト情報

- **Issue番号**: #380
- **タイトル**: [TASK] Issue #376の続き - Application/CLI層の実装
- **状態**: open
- **作成日**: 2025-10-13
- **Planning Document**: `.ai-workflow/issue-380/00_planning/output/planning.md`
- **Requirements Document**: `.ai-workflow/issue-380/01_requirements/output/requirements.md`
- **Design Document**: `.ai-workflow/issue-380/02_design/output/design.md`

---

## 📋 目次

1. [テスト戦略サマリー](#1-テスト戦略サマリー)
2. [Unitテストシナリオ](#2-unitテストシナリオ)
3. [Integrationテストシナリオ](#3-integrationテストシナリオ)
4. [テストデータ](#4-テストデータ)
5. [テスト環境要件](#5-テスト環境要件)
6. [テスト実行計画](#6-テスト実行計画)
7. [品質ゲートチェックリスト](#7-品質ゲートチェックリスト)

---

## 1. テスト戦略サマリー

### 1.1 選択されたテスト戦略

**テスト戦略**: **UNIT_INTEGRATION（ユニット + インテグレーション）**

**判断根拠**（Design Document セクション3より引用）:

#### UNIT_TEST（必須）
- **理由**: 新規作成するクラス（WorkflowController、ConfigManager、CLI層）の正常動作を保証
- **対象**:
  - WorkflowController: ワークフロー制御ロジックの正常動作を検証
  - ConfigManager: 設定読み込みとバリデーションを検証
  - CLI層（cli/commands.py）: CLIコマンドのパース処理を検証

#### INTEGRATION_TEST（必須）
- **理由**: Issue #376で作成された基盤レイヤーと既存コードの統合が正しく動作することを保証
- **対象**:
  - WorkflowController + PhaseExecutor + 各フェーズクラスの連携
  - ConfigManager + 環境変数 + config.yamlの統合
  - CLI層 → Application層 → Domain層の全体フロー
  - 既存テストの修正（Issue #376で失敗した116件のテスト）

#### BDD_TEST（不要）
- **理由**: エンドユーザー視点での機能追加はない（内部構造の改善のみ）
- **補足**: Issue #376で既にBDDテストが作成されており、既存機能の動作保証のため維持するが、新規作成は不要

### 1.2 テスト対象の範囲

#### 新規実装コンポーネント（4ファイル）
- `scripts/ai-workflow/core/workflow_controller.py` - ワークフロー制御クラス
- `scripts/ai-workflow/core/config_manager.py` - 設定管理クラス
- `scripts/ai-workflow/cli/__init__.py` - CLIモジュール初期化
- `scripts/ai-workflow/cli/commands.py` - CLIコマンド定義

#### 修正対象コンポーネント（13ファイル）
- `scripts/ai-workflow/main.py` - エントリーポイント
- `scripts/ai-workflow/phases/*.py` - 各フェーズクラス（10ファイル）
- `scripts/ai-workflow/core/metadata_manager.py` - メタデータ管理
- `scripts/ai-workflow/core/claude_agent_client.py` - Claude API クライアント

### 1.3 テストの目的

1. **新規コンポーネントの動作保証**: WorkflowController、ConfigManager、CLI層が設計通りに動作すること
2. **統合の正常性**: Issue #376で作成された基盤レイヤーと既存コードが正しく統合されること
3. **後方互換性の維持**: CLIコマンド、メタデータフォーマット、設定ファイル構造が維持されること
4. **既存機能の維持**: すべての既存機能が正常動作すること
5. **テストカバレッジ80%以上**: コード品質の担保

---

## 2. Unitテストシナリオ

### 2.1 ConfigManager（core/config_manager.py）

#### 2.1.1 ConfigManager初期化

**テストケース名**: `test_config_manager_init_正常系`

- **目的**: ConfigManagerが正しく初期化されることを検証
- **前提条件**: なし
- **入力**: `config_path = Path('config.yaml')`
- **期待結果**:
  - ConfigManagerインスタンスが作成される
  - `config_path`が正しく設定される
  - `_config`が空の辞書として初期化される
- **テストデータ**: なし

---

#### 2.1.2 config.yamlからの設定読み込み（正常系）

**テストケース名**: `test_load_config_from_yaml_正常系`

- **目的**: config.yamlから設定が正しく読み込まれることを検証
- **前提条件**:
  - config.yamlが存在する
  - 有効なYAML形式である
- **入力**:
  ```yaml
  github_token: "test-token-123"
  github_repository: "test-owner/test-repo"
  claude_api_key: "sk-test-key-456"
  working_dir: "/tmp/test"
  log_level: "INFO"
  ```
- **期待結果**:
  - `_config`に上記の設定が格納される
  - `load_config()`が成功する（例外が発生しない）
- **テストデータ**: 上記YAML内容のテストファイル

---

#### 2.1.3 環境変数からの設定読み込み（正常系）

**テストケース名**: `test_load_config_from_environment_正常系`

- **目的**: 環境変数から設定が正しく読み込まれ、config.yamlより優先されることを検証
- **前提条件**:
  - config.yamlに `github_token: "yaml-token"`
  - 環境変数 `GITHUB_TOKEN="env-token"`
- **入力**: 上記の設定とモック環境変数
- **期待結果**:
  - `_config['github_token']`が `"env-token"`である（環境変数が優先）
  - その他の設定はconfig.yamlから読み込まれる
- **テストデータ**: config.yamlファイル + モック環境変数

---

#### 2.1.4 必須項目の欠落（異常系）

**テストケース名**: `test_load_config_missing_required_key_異常系`

- **目的**: 必須項目が欠落している場合にConfigValidationErrorが発生することを検証
- **前提条件**:
  - config.yamlに `github_token`が存在しない
  - 環境変数も設定されていない
- **入力**: 不完全なconfig.yaml
- **期待結果**:
  - `ConfigValidationError`が発生する
  - エラーメッセージに "github_token" が含まれる
- **テストデータ**:
  ```yaml
  github_repository: "test-owner/test-repo"
  claude_api_key: "sk-test-key-456"
  # github_token が欠落
  ```

---

#### 2.1.5 無効なLOG_LEVEL（異常系）

**テストケース名**: `test_load_config_invalid_log_level_異常系`

- **目的**: 無効なLOG_LEVELが指定された場合にConfigValidationErrorが発生することを検証
- **前提条件**: config.yamlに `log_level: "INVALID"`
- **入力**:
  ```yaml
  github_token: "test-token"
  github_repository: "test-owner/test-repo"
  claude_api_key: "sk-test-key"
  log_level: "INVALID"
  ```
- **期待結果**:
  - `ConfigValidationError`が発生する
  - エラーメッセージに "Invalid log_level" が含まれる
- **テストデータ**: 上記YAML内容

---

#### 2.1.6 config.yamlが存在しない（正常系）

**テストケース名**: `test_load_config_yaml_not_found_正常系`

- **目的**: config.yamlが存在しない場合、デフォルト値が使用され、環境変数から読み込まれることを検証
- **前提条件**:
  - config.yamlが存在しない
  - 環境変数に必須項目が設定されている
- **入力**: 環境変数（GITHUB_TOKEN, GITHUB_REPOSITORY, CLAUDE_API_KEY）
- **期待結果**:
  - デフォルト値 + 環境変数の設定が使用される
  - `load_config()`が成功する
  - WARNINGログに "Config file not found" が含まれる
- **テストデータ**: モック環境変数のみ

---

#### 2.1.7 get()メソッド（正常系）

**テストケース名**: `test_config_get_method_正常系`

- **目的**: get()メソッドで設定値が正しく取得できることを検証
- **前提条件**: `_config`に設定が読み込まれている
- **入力**:
  - `get('github_token')`
  - `get('non_existent_key', 'default_value')`
- **期待結果**:
  - `get('github_token')`が正しい値を返す
  - `get('non_existent_key', 'default_value')`が `'default_value'` を返す
- **テストデータ**: 事前に読み込まれた設定

---

### 2.2 WorkflowController（core/workflow_controller.py）

#### 2.2.1 WorkflowController初期化

**テストケース名**: `test_workflow_controller_init_正常系`

- **目的**: WorkflowControllerが正しく初期化されることを検証
- **前提条件**: 必要な依存オブジェクトがモックされている
- **入力**:
  - `repo_root = Path('/tmp/test-repo')`
  - `config_manager` (モック)
  - `metadata_manager` (モック)
  - その他依存オブジェクト（モック）
- **期待結果**:
  - WorkflowControllerインスタンスが作成される
  - すべての依存オブジェクトが正しく設定される
  - `PHASE_ORDER`が定義されている
- **テストデータ**: モックオブジェクト

---

#### 2.2.2 ワークフロー初期化（正常系）

**テストケース名**: `test_initialize_workflow_正常系`

- **目的**: ワークフロー初期化が正常に完了することを検証
- **前提条件**:
  - GitHub Issue #380が存在する
  - issue_client.get_issue_info()がIssue情報を返す
- **入力**:
  - `issue_number = 380`
  - `issue_url = "https://github.com/tielec/infrastructure-as-code/issues/380"`
- **期待結果**:
  - `result['success']`が`True`
  - `result['branch_name']`が`'ai-workflow/issue-380'`
  - metadata.create_new()が呼ばれる
  - git_branch.create_and_checkout()が呼ばれる
  - metadata.save()が呼ばれる
- **テストデータ**:
  ```python
  issue_info_mock = {
      'title': '[TASK] Issue #376の続き - Application/CLI層の実装',
      'state': 'open'
  }
  ```

---

#### 2.2.3 ワークフロー初期化（GitHub APIエラー）

**テストケース名**: `test_initialize_workflow_github_api_error_異常系`

- **目的**: GitHub API呼び出し失敗時に適切にエラーハンドリングされることを検証
- **前提条件**: issue_client.get_issue_info()が`GitHubAPIError`を発生させる
- **入力**:
  - `issue_number = 999`
  - `issue_url = "https://github.com/tielec/infrastructure-as-code/issues/999"`
- **期待結果**:
  - `result['success']`が`False`
  - `result['error']`にエラーメッセージが含まれる
  - エラーログが出力される
- **テストデータ**: `GitHubAPIError('Issue not found')`

---

#### 2.2.4 単一フェーズ実行（正常系）

**テストケース名**: `test_execute_phase_正常系`

- **目的**: 単一フェーズが正常に実行されることを検証
- **前提条件**:
  - ワークフローが初期化されている
  - phase_executor.execute()が成功結果を返す
- **入力**: `phase_name = 'planning'`
- **期待結果**:
  - `result['success']`が`True`
  - `result['phase']`が`'planning'`
  - `result['review_result']`が`'PASS'`または`'PASS_WITH_SUGGESTIONS'`
  - metadata.update_phase_status()が呼ばれる
  - metadata.save()が呼ばれる
- **テストデータ**:
  ```python
  phase_executor_result_mock = {
      'success': True,
      'review_result': 'PASS',
      'output_file': '.ai-workflow/issue-380/00_planning/output/planning.md'
  }
  ```

---

#### 2.2.5 単一フェーズ実行（未知のフェーズ名）

**テストケース名**: `test_execute_phase_unknown_phase_異常系`

- **目的**: 未知のフェーズ名が指定された場合にWorkflowErrorが発生することを検証
- **前提条件**: なし
- **入力**: `phase_name = 'unknown_phase'`
- **期待結果**:
  - `result['success']`が`False`
  - `result['error']`に "Unknown phase" が含まれる
  - WorkflowErrorが発生する
- **テストデータ**: なし

---

#### 2.2.6 全フェーズ実行（正常系）

**テストケース名**: `test_execute_all_phases_正常系`

- **目的**: 全フェーズが順次実行されることを検証
- **前提条件**:
  - ワークフローが初期化されている
  - すべてのフェーズが成功する
- **入力**: なし
- **期待結果**:
  - `result['success']`が`True`
  - `result['completed_phases']`が10個のフェーズ名を含む
  - `result['failed_phase']`が`None`
  - execute_phase()が10回呼ばれる
- **テストデータ**: 各フェーズの成功結果モック

---

#### 2.2.7 全フェーズ実行（途中で失敗）

**テストケース名**: `test_execute_all_phases_failure_異常系`

- **目的**: フェーズ実行中にエラーが発生した場合、適切に停止することを検証
- **前提条件**:
  - planningフェーズは成功
  - requirementsフェーズが失敗
- **入力**: なし
- **期待結果**:
  - `result['success']`が`False`
  - `result['completed_phases']`が`['planning']`
  - `result['failed_phase']`が`'requirements'`
  - `result['error']`にエラーメッセージが含まれる
- **テストデータ**:
  ```python
  # planningは成功、requirementsは失敗
  phase_results = {
      'planning': {'success': True, 'review_result': 'PASS'},
      'requirements': {'success': False, 'error': 'Test error'}
  }
  ```

---

### 2.3 CLI層（cli/commands.py）

#### 2.3.1 initコマンド（正常系）

**テストケース名**: `test_cli_init_command_正常系`

- **目的**: initコマンドが正常に実行されることを検証
- **前提条件**: WorkflowController.initialize()が成功する
- **入力**:
  - コマンド: `init --issue-url https://github.com/tielec/infrastructure-as-code/issues/380`
- **期待結果**:
  - exit codeが0
  - 出力に "[OK] Workflow initialized for Issue #380" が含まれる
  - WorkflowController.initialize()が呼ばれる
- **テストデータ**: モックWorkflowController

---

#### 2.3.2 initコマンド（無効なURL）

**テストケース名**: `test_cli_init_command_invalid_url_異常系`

- **目的**: 無効なIssue URLが指定された場合にエラーメッセージが表示されることを検証
- **前提条件**: なし
- **入力**:
  - コマンド: `init --issue-url invalid-url`
- **期待結果**:
  - exit codeが1
  - 出力に "[ERROR] Invalid Issue URL format" が含まれる
  - WorkflowController.initialize()が呼ばれない
- **テストデータ**: なし

---

#### 2.3.3 executeコマンド（単一フェーズ・正常系）

**テストケース名**: `test_cli_execute_command_single_phase_正常系`

- **目的**: executeコマンドで単一フェーズが実行されることを検証
- **前提条件**: WorkflowController.execute_phase()が成功する
- **入力**:
  - コマンド: `execute --issue 380 --phase planning`
- **期待結果**:
  - exit codeが0
  - 出力に "[OK] Phase planning completed successfully" が含まれる
  - WorkflowController.execute_phase('planning')が呼ばれる
- **テストデータ**: モックWorkflowController

---

#### 2.3.4 executeコマンド（全フェーズ・正常系）

**テストケース名**: `test_cli_execute_command_all_phases_正常系`

- **目的**: executeコマンドで全フェーズが実行されることを検証
- **前提条件**: WorkflowController.execute_all_phases()が成功する
- **入力**:
  - コマンド: `execute --issue 380 --phase all`
- **期待結果**:
  - exit codeが0
  - 出力に "[OK] Phase all completed successfully" が含まれる
  - WorkflowController.execute_all_phases()が呼ばれる
- **テストデータ**: モックWorkflowController

---

#### 2.3.5 executeコマンド（失敗）

**テストケース名**: `test_cli_execute_command_failure_異常系`

- **目的**: フェーズ実行失敗時に適切なエラーメッセージが表示されることを検証
- **前提条件**: WorkflowController.execute_phase()が失敗する
- **入力**:
  - コマンド: `execute --issue 380 --phase planning`
- **期待結果**:
  - exit codeが1
  - 出力に "[ERROR] Phase planning failed:" が含まれる
- **テストデータ**:
  ```python
  result_mock = {
      'success': False,
      'error': 'Test error message'
  }
  ```

---

#### 2.3.6 statusコマンド（正常系）

**テストケース名**: `test_cli_status_command_正常系`

- **目的**: statusコマンドでワークフロー状態が表示されることを検証
- **前提条件**: メタデータにワークフロー状態が記録されている
- **入力**:
  - コマンド: `status --issue 380`
- **期待結果**:
  - exit codeが0
  - 出力に "Workflow Status - Issue #380" が含まれる
  - 出力に "Branch: ai-workflow/issue-380" が含まれる
  - 各フェーズのステータスが表示される
- **テストデータ**:
  ```python
  metadata_mock = {
      'branch_name': 'ai-workflow/issue-380',
      'phases': {
          'planning': {'status': 'completed'},
          'requirements': {'status': 'in_progress'}
      }
  }
  ```

---

#### 2.3.7 resumeコマンド（正常系）

**テストケース名**: `test_cli_resume_command_正常系`

- **目的**: resumeコマンドで中断したワークフローが再開されることを検証
- **前提条件**:
  - メタデータに最後に実行したフェーズが記録されている
  - WorkflowController.execute_all_phases()が成功する
- **入力**:
  - コマンド: `resume --issue 380`
- **期待結果**:
  - exit codeが0
  - 出力に "[OK] Workflow resumed from phase:" が含まれる
  - 最後のフェーズの次から実行される
- **テストデータ**:
  ```python
  metadata_mock = {
      'last_completed_phase': 'planning'
  }
  ```

---

### 2.4 main.py

#### 2.4.1 main.pyエントリーポイント

**テストケース名**: `test_main_entry_point_正常系`

- **目的**: main.pyがCLIコマンドを正しく呼び出すことを検証
- **前提条件**: cli.commands.cli()が正しく動作する
- **入力**: `python main.py --help`
- **期待結果**:
  - exit codeが0
  - ヘルプメッセージが表示される
  - cli.commands.cli()が呼ばれる
- **テストデータ**: なし

---

### 2.5 既存ファイル修正

#### 2.5.1 phases/planning.py インポートパス修正

**テストケース名**: `test_planning_phase_import_paths_正常系`

- **目的**: PlanningPhaseが新しいインポートパスで動作することを検証
- **前提条件**:
  - `from phases.base.abstract_phase import AbstractPhase`
  - `from core.git.repository import GitRepository`
- **入力**: PlanningPhaseインスタンス化
- **期待結果**:
  - PlanningPhaseインスタンスが作成される
  - AbstractPhaseを継承している
  - execute()メソッドが動作する
- **テストデータ**: モック依存オブジェクト

---

#### 2.5.2 core/metadata_manager.py エラーハンドリング統一

**テストケース名**: `test_metadata_manager_error_handling_正常系`

- **目的**: MetadataManagerが新しい例外クラスを使用することを検証
- **前提条件**: `from common.error_handler import MetadataError`
- **入力**: 不正なメタデータファイルを読み込み
- **期待結果**:
  - `MetadataError`が発生する
  - エラーメッセージが適切に設定される
- **テストデータ**: 不正なJSON形式のファイル

---

#### 2.5.3 core/claude_agent_client.py エラーハンドリング統一

**テストケース名**: `test_claude_agent_client_error_handling_正常系`

- **目的**: ClaudeAgentClientが新しい例外クラスを使用することを検証
- **前提条件**: `from common.error_handler import ClaudeAPIError`
- **入力**: Claude API呼び出しでエラー発生
- **期待結果**:
  - `ClaudeAPIError`が発生する
  - エラーメッセージが適切に設定される
- **テストデータ**: モックClaude APIレスポンス（エラー）

---

## 3. Integrationテストシナリオ

### 3.1 ワークフロー全体統合テスト

#### 3.1.1 ワークフロー初期化 → 単一フェーズ実行

**シナリオ名**: `Integration_WorkflowInit_to_PhaseExecution`

- **目的**: ワークフロー初期化から単一フェーズ実行までの全体フローが正しく動作することを検証
- **前提条件**:
  - GitHub Issue #380が存在する
  - config.yamlまたは環境変数に必須設定が存在する
  - リポジトリがクリーンな状態
- **テスト手順**:
  1. ConfigManagerで設定を読み込み
  2. WorkflowControllerを初期化
  3. `initialize(issue_number=380)`を実行
  4. メタデータファイルが作成されることを確認
  5. 作業ブランチ`ai-workflow/issue-380`が作成されることを確認
  6. `execute_phase('planning')`を実行
  7. planningフェーズが正常完了することを確認
  8. メタデータにフェーズステータスが記録されることを確認
- **期待結果**:
  - すべての手順が成功する
  - メタデータファイルが存在し、正しい内容が記録されている
  - 作業ブランチが存在する
  - planningフェーズの出力ファイルが生成されている
- **確認項目**:
  - [ ] metadata.jsonが存在する
  - [ ] metadata.jsonに`issue_number: 380`が記録されている
  - [ ] `ai-workflow/issue-380`ブランチが存在する
  - [ ] `.ai-workflow/issue-380/00_planning/output/planning.md`が存在する
  - [ ] metadata.jsonに`phases.planning.status: completed`が記録されている

---

#### 3.1.2 CLI → Application → Domain層の統合

**シナリオ名**: `Integration_CLI_to_Domain_Layer`

- **目的**: CLI層からDomain層までの全体フローが正しく動作することを検証
- **前提条件**:
  - すべてのコンポーネントが実装されている
  - config.yamlに必須設定が存在する
- **テスト手順**:
  1. コマンド実行: `python main.py init --issue-url https://github.com/tielec/infrastructure-as-code/issues/380`
  2. CLI層がWorkflowController.initialize()を呼び出すことを確認
  3. WorkflowControllerがGitRepository、IssueClientを使用することを確認
  4. コマンド実行: `python main.py execute --issue 380 --phase planning`
  5. CLI層がWorkflowController.execute_phase()を呼び出すことを確認
  6. WorkflowControllerがPhaseExecutorを使用することを確認
  7. PhaseExecutorがPlanningPhaseを実行することを確認
- **期待結果**:
  - すべてのレイヤーが正しく連携する
  - CLI → Application → Domain → Infrastructureの依存関係が正しい
  - エラーが発生しない
- **確認項目**:
  - [ ] CLIコマンドが正常終了する（exit code 0）
  - [ ] WorkflowController.initialize()が呼ばれる
  - [ ] IssueClient.get_issue_info()が呼ばれる
  - [ ] GitBranch.create_and_checkout()が呼ばれる
  - [ ] PhaseExecutor.execute()が呼ばれる
  - [ ] PlanningPhase.execute()が呼ばれる

---

#### 3.1.3 ConfigManager + 環境変数 + config.yamlの統合

**シナリオ名**: `Integration_ConfigManager_MultiSource`

- **目的**: ConfigManagerが環境変数、config.yaml、デフォルト値を正しく統合することを検証
- **前提条件**:
  - config.yamlに`github_token: "yaml-token"`
  - 環境変数`GITHUB_TOKEN="env-token"`
  - 環境変数`WORKING_DIR`が未設定（デフォルト値を使用）
- **テスト手順**:
  1. ConfigManagerを初期化
  2. `load_config()`を実行
  3. `github_token`の値が環境変数の値であることを確認
  4. `working_dir`の値がデフォルト値であることを確認
  5. その他の設定がconfig.yamlから読み込まれていることを確認
- **期待結果**:
  - 設定の優先順位が正しい（環境変数 > config.yaml > デフォルト値）
  - すべての必須項目が設定されている
  - バリデーションが通過する
- **確認項目**:
  - [ ] `config['github_token'] == "env-token"`
  - [ ] `config['working_dir'] == "."`（デフォルト値）
  - [ ] `config['github_repository']`がconfig.yamlから読み込まれている
  - [ ] `ConfigValidationError`が発生しない

---

### 3.2 エラーハンドリング統合テスト

#### 3.2.1 GitHub API障害時のエラーハンドリング

**シナリオ名**: `Integration_GitHubAPI_Error_Handling`

- **目的**: GitHub API障害時に適切にエラーハンドリングされることを検証
- **前提条件**: GitHub APIがエラーを返す状況をモック
- **テスト手順**:
  1. IssueClient.get_issue_info()が`GitHubAPIError`を発生させるようにモック
  2. `WorkflowController.initialize(issue_number=999)`を実行
  3. エラーが適切にキャッチされることを確認
  4. エラーログが出力されることを確認
  5. ユーザーにエラーメッセージが表示されることを確認
- **期待結果**:
  - `GitHubAPIError`が適切にキャッチされる
  - ワークフローが異常終了せず、エラー情報を返す
  - エラーログが出力される
- **確認項目**:
  - [ ] `result['success'] == False`
  - [ ] `result['error']`にエラーメッセージが含まれる
  - [ ] エラーログに "GitHub API error" が含まれる
  - [ ] プログラムがクラッシュしない

---

#### 3.2.2 メタデータ破損時のエラーハンドリング

**シナリオ名**: `Integration_Metadata_Corruption_Handling`

- **目的**: メタデータファイルが破損している場合に適切にエラーハンドリングされることを検証
- **前提条件**: 不正なJSON形式のmetadata.jsonが存在する
- **テスト手順**:
  1. 不正なJSON形式のmetadata.jsonを作成
  2. `MetadataManager.load()`を実行
  3. `MetadataError`が発生することを確認
  4. エラーログが出力されることを確認
- **期待結果**:
  - `MetadataError`が発生する
  - エラーメッセージに破損の詳細が含まれる
  - エラーログが出力される
- **確認項目**:
  - [ ] `MetadataError`が発生する
  - [ ] エラーメッセージに "Failed to load metadata" が含まれる
  - [ ] エラーログに詳細なエラー情報が含まれる

---

### 3.3 既存テスト修正の検証

#### 3.3.1 116件の失敗テスト修正確認

**シナリオ名**: `Integration_FixedTests_Verification`

- **目的**: Issue #376で失敗した116件のテストが修正されていることを検証
- **前提条件**:
  - すべてのインポートパス修正が完了している
  - モックの差し替えが完了している
- **テスト手順**:
  1. 全テストスイートを実行: `pytest tests/`
  2. テスト結果を確認
  3. 失敗テストが0件であることを確認
  4. テストカバレッジレポートを生成
  5. カバレッジが80%以上であることを確認
- **期待結果**:
  - すべてのテストが通過する（116件の失敗が0件になる）
  - テストカバレッジが80%以上
  - 新規テストが正常に動作する
- **確認項目**:
  - [ ] `pytest tests/ --tb=short`がすべて成功する
  - [ ] `pytest --cov=scripts/ai-workflow --cov-report=term`でカバレッジ80%以上
  - [ ] 新規作成したユニットテスト（4ファイル）が通過する
  - [ ] 既存修正したテスト（70+ファイル）が通過する

---

### 3.4 後方互換性の検証

#### 3.4.1 既存CLIコマンドの動作確認

**シナリオ名**: `Integration_Backward_Compatibility_CLI`

- **目的**: リファクタリング後も既存CLIコマンドが変更なく動作することを検証
- **前提条件**: リファクタリングが完了している
- **テスト手順**:
  1. コマンド実行: `python main.py init --issue-url <URL>`
  2. コマンド実行: `python main.py execute --issue 380 --phase planning`
  3. コマンド実行: `python main.py resume --issue 380`
  4. コマンド実行: `python main.py status --issue 380`
  5. すべてのコマンドが正常終了することを確認
- **期待結果**:
  - すべてのCLIコマンドが動作する
  - コマンドのインターフェースが変更されていない
  - 出力フォーマットが維持されている
- **確認項目**:
  - [ ] `init`コマンドが動作する
  - [ ] `execute`コマンドが動作する
  - [ ] `resume`コマンドが動作する
  - [ ] `status`コマンドが動作する
  - [ ] ヘルプメッセージが表示される

---

#### 3.4.2 メタデータフォーマットの互換性

**シナリオ名**: `Integration_Metadata_Format_Compatibility`

- **目的**: 既存のmetadata.jsonファイルが新しい実装で正しく読み込まれることを検証
- **前提条件**: Issue #376で作成されたmetadata.jsonが存在する
- **テスト手順**:
  1. Issue #376のmetadata.jsonを読み込み
  2. `MetadataManager.load()`を実行
  3. すべてのフィールドが正しく読み込まれることを確認
  4. 新しいフェーズステータスを更新
  5. `MetadataManager.save()`を実行
  6. 保存されたmetadata.jsonが正しい形式であることを確認
- **期待結果**:
  - 既存metadata.jsonが正常に読み込まれる
  - フィールド名・構造が変更されていない
  - 新しいデータが正しく保存される
- **確認項目**:
  - [ ] 既存metadata.jsonが読み込める
  - [ ] `issue_number`フィールドが存在する
  - [ ] `phases`フィールドが存在する
  - [ ] 新しいフェーズステータスが保存される

---

### 3.5 パフォーマンステスト

#### 3.5.1 ワークフロー初期化時間

**シナリオ名**: `Integration_Performance_Initialize`

- **目的**: ワークフロー初期化が10秒以内に完了することを検証
- **前提条件**: すべてのコンポーネントが実装されている
- **テスト手順**:
  1. 開始時刻を記録
  2. `WorkflowController.initialize(issue_number=380)`を実行
  3. 終了時刻を記録
  4. 実行時間を計算
  5. 実行時間が10秒以内であることを確認
- **期待結果**:
  - 初期化が10秒以内に完了する
  - GitHub API呼び出しが最小限である
- **確認項目**:
  - [ ] 実行時間 < 10秒
  - [ ] GitHub API呼び出し回数が1回
  - [ ] メタデータ書き込みが1秒以内

---

#### 3.5.2 メタデータ読み書き速度

**シナリオ名**: `Integration_Performance_Metadata`

- **目的**: メタデータの読み込み/書き込みが1秒以内に完了することを検証
- **前提条件**: metadata.jsonが存在する（サイズ10KB以下）
- **テスト手順**:
  1. 開始時刻を記録
  2. `MetadataManager.load()`を実行
  3. 終了時刻を記録
  4. 読み込み時間を計算
  5. 開始時刻を記録
  6. `MetadataManager.save()`を実行
  7. 終了時刻を記録
  8. 書き込み時間を計算
- **期待結果**:
  - 読み込みが1秒以内に完了する
  - 書き込みが1秒以内に完了する
- **確認項目**:
  - [ ] 読み込み時間 < 1秒
  - [ ] 書き込み時間 < 1秒
  - [ ] metadata.jsonサイズ < 10KB

---

## 4. テストデータ

### 4.1 config.yaml（正常系）

```yaml
# テスト用config.yaml（正常系）
github_token: "ghp_test1234567890abcdefghijklmnopqrstuvwxyz"
github_repository: "tielec/infrastructure-as-code"
claude_api_key: "sk-test-key-1234567890abcdefghijklmnopqrstuvwxyz"
working_dir: "/tmp/ai-workflow-test"
log_level: "INFO"
max_turns: 30
timeout: 300
```

### 4.2 config.yaml（異常系 - 必須項目欠落）

```yaml
# テスト用config.yaml（異常系 - github_token欠落）
github_repository: "tielec/infrastructure-as-code"
claude_api_key: "sk-test-key-1234567890abcdefghijklmnopqrstuvwxyz"
working_dir: "/tmp/ai-workflow-test"
log_level: "INFO"
```

### 4.3 config.yaml（異常系 - 無効なLOG_LEVEL）

```yaml
# テスト用config.yaml（異常系 - 無効なLOG_LEVEL）
github_token: "ghp_test1234567890abcdefghijklmnopqrstuvwxyz"
github_repository: "tielec/infrastructure-as-code"
claude_api_key: "sk-test-key-1234567890abcdefghijklmnopqrstuvwxyz"
log_level: "INVALID_LEVEL"
```

### 4.4 環境変数（正常系）

```bash
# テスト用環境変数（正常系）
export GITHUB_TOKEN="ghp_env_token_1234567890"
export GITHUB_REPOSITORY="tielec/infrastructure-as-code"
export CLAUDE_API_KEY="sk-env-key-1234567890"
export WORKING_DIR="/tmp/ai-workflow-test"
export LOG_LEVEL="DEBUG"
```

### 4.5 metadata.json（正常系）

```json
{
  "issue_number": 380,
  "issue_url": "https://github.com/tielec/infrastructure-as-code/issues/380",
  "issue_title": "[TASK] Issue #376の続き - Application/CLI層の実装",
  "branch_name": "ai-workflow/issue-380",
  "created_at": "2025-10-13T10:00:00Z",
  "phases": {
    "planning": {
      "status": "completed",
      "started_at": "2025-10-13T10:05:00Z",
      "completed_at": "2025-10-13T10:30:00Z",
      "output_file": ".ai-workflow/issue-380/00_planning/output/planning.md",
      "review_result": "PASS"
    },
    "requirements": {
      "status": "in_progress",
      "started_at": "2025-10-13T10:35:00Z"
    }
  }
}
```

### 4.6 metadata.json（異常系 - 破損）

```json
{
  "issue_number": 380,
  "issue_url": "https://github.com/tielec/infrastructure-as-code/issues/380",
  "issue_title": "[TASK] Issue #376の続き - Application/CLI層の実装",
  "branch_name": "ai-workflow/issue-380",
  "created_at": "2025-10-13T10:00:00Z",
  "phases": {
    "planning": {
      "status": "completed",
      // 不正なコメント
```

### 4.7 GitHub Issue情報（モック）

```python
# テスト用GitHub Issue情報（モック）
issue_info_mock = {
    "number": 380,
    "title": "[TASK] Issue #376の続き - Application/CLI層の実装",
    "state": "open",
    "body": "## 概要\n\nIssue #376の大規模リファクタリングにて...",
    "labels": [],
    "created_at": "2025-10-13T09:00:00Z",
    "updated_at": "2025-10-13T09:00:00Z"
}
```

### 4.8 PhaseExecutor結果（モック）

```python
# テスト用PhaseExecutor結果（正常系）
phase_executor_result_success = {
    "success": True,
    "phase": "planning",
    "review_result": "PASS",
    "output_file": ".ai-workflow/issue-380/00_planning/output/planning.md",
    "started_at": "2025-10-13T10:05:00Z",
    "completed_at": "2025-10-13T10:30:00Z"
}

# テスト用PhaseExecutor結果（失敗）
phase_executor_result_failure = {
    "success": False,
    "phase": "requirements",
    "error": "Requirements validation failed",
    "started_at": "2025-10-13T10:35:00Z",
    "failed_at": "2025-10-13T10:40:00Z"
}
```

---

## 5. テスト環境要件

### 5.1 ローカルテスト環境

#### 必須環境
- **Python**: 3.10以上
- **Git**: 2.30以上
- **pip**: 最新版
- **virtualenv**: 最新版

#### 必須ライブラリ
```
click==8.1.3
GitPython==3.1.31
PyGithub==1.58.0
openai==1.0.0
anthropic==0.21.3
pytest==7.4.0
pytest-cov==4.1.0
pytest-mock==3.11.1
pytest-benchmark==4.0.0
```

### 5.2 モック/スタブの必要性

#### モックが必要なコンポーネント
1. **GitHub API**:
   - `IssueClient.get_issue_info()`: GitHub Issue情報取得
   - `PRClient.create_pr()`: PR作成
   - `CommentClient.post_comment()`: コメント投稿

2. **Git操作**:
   - `GitRepository.clone()`: リポジトリクローン
   - `GitBranch.create_and_checkout()`: ブランチ作成
   - `GitCommit.commit()`: コミット作成

3. **Claude API**:
   - `ClaudeAgentClient.execute()`: Claude Agent SDK実行

4. **ファイルI/O**:
   - `FileHandler.read()`: ファイル読み込み
   - `FileHandler.write()`: ファイル書き込み

#### モック実装方法
- `pytest-mock`の`mocker.patch()`を使用
- `unittest.mock.Mock`オブジェクトを使用
- フィクスチャとして共通モックを定義

### 5.3 テストディレクトリ構成

```
tests/
├─ unit/
│  ├─ core/
│  │  ├─ test_workflow_controller.py  # 新規作成
│  │  ├─ test_config_manager.py       # 新規作成
│  │  ├─ test_metadata_manager.py     # 既存修正
│  │  └─ test_claude_agent_client.py  # 既存修正
│  ├─ cli/
│  │  └─ test_commands.py              # 新規作成
│  └─ phases/
│     ├─ test_planning.py              # 既存修正
│     └─ ...（10ファイル）
├─ integration/
│  ├─ test_workflow_integration.py     # 新規作成
│  └─ ...（30ファイル - 既存修正）
└─ conftest.py                         # 共通フィクスチャ
```

### 5.4 CI/CD環境

#### GitHub Actions
- **トリガー**: Pull Request作成/更新時
- **実行内容**:
  1. 環境セットアップ（Python 3.10）
  2. 依存ライブラリインストール
  3. ユニットテスト実行
  4. インテグレーションテスト実行
  5. カバレッジレポート生成
  6. テスト結果の通知

#### 環境変数（CI/CD）
```yaml
GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
GITHUB_REPOSITORY: ${{ github.repository }}
CLAUDE_API_KEY: ${{ secrets.CLAUDE_API_KEY }}
```

---

## 6. テスト実行計画

### 6.1 テスト実行順序

#### Phase 5: テスト実装（見積もり: 16~32時間）

1. **新規クラスのユニットテスト作成**（8~16h）
   - ConfigManagerのユニットテスト
   - WorkflowControllerのユニットテスト
   - CLI層のユニットテスト

2. **既存テストの修正**（8~16h）
   - インポートパス修正（70+ファイル）
   - モック差し替え
   - 116件の失敗テストの修正

#### Phase 6: テスト実行（見積もり: 2~4時間）

1. **ユニットテスト実行**
   ```bash
   pytest tests/unit/ -v --tb=short
   ```

2. **インテグレーションテスト実行**
   ```bash
   pytest tests/integration/ -v --tb=short
   ```

3. **カバレッジレポート生成**
   ```bash
   pytest --cov=scripts/ai-workflow --cov-report=html --cov-report=term
   ```

4. **パフォーマンスベンチマーク実行**
   ```bash
   pytest tests/integration/test_performance.py --benchmark-only
   ```

### 6.2 カバレッジ目標

#### 全体目標
- **総合カバレッジ**: 80%以上

#### コンポーネント別目標
- **WorkflowController**: 85%以上
- **ConfigManager**: 90%以上
- **CLI層**: 80%以上
- **既存コンポーネント**: 現状維持（低下させない）

### 6.3 テスト失敗時の対応

#### 失敗カテゴリー別対応

1. **インポートパスエラー**:
   - 修正方法: インポート文を新しいモジュール構造に修正
   - 優先度: 高

2. **モック差し替えエラー**:
   - 修正方法: モックオブジェクトを新しいクラスに対応
   - 優先度: 高

3. **アサーション失敗**:
   - 修正方法: 期待値を新しいインターフェースに対応
   - 優先度: 中

4. **統合テスト失敗**:
   - 修正方法: コンポーネント間の連携を再確認
   - 優先度: 高

### 6.4 成功基準

#### Phase 6（テスト実行）の品質ゲート

- [ ] **すべてのユニットテストが通過する**
- [ ] **すべてのインテグレーションテストが通過する**
- [ ] **テストカバレッジが80%以上**
- [ ] **パフォーマンスが劣化していない**（ワークフロー初期化10秒以内）

---

## 7. 品質ゲートチェックリスト

### Phase 3（テストシナリオ）の品質ゲート

- [x] **Phase 2の戦略に沿ったテストシナリオである**
  - テスト戦略: UNIT_INTEGRATION
  - Unitテストシナリオ作成済み（2.1〜2.5）
  - Integrationテストシナリオ作成済み（3.1〜3.5）
  - BDDテストシナリオは不要（Phase 2の判断通り）

- [x] **主要な正常系がカバーされている**
  - ConfigManager: 設定読み込み（YAML、環境変数、デフォルト値）
  - WorkflowController: ワークフロー初期化、単一フェーズ実行、全フェーズ実行
  - CLI層: すべてのコマンド（init, execute, resume, status）
  - 統合テスト: ワークフロー全体フロー、CLI→Application→Domain層

- [x] **主要な異常系がカバーされている**
  - ConfigManager: 必須項目欠落、無効なLOG_LEVEL
  - WorkflowController: GitHub APIエラー、未知のフェーズ名、フェーズ実行失敗
  - CLI層: 無効なIssue URL、フェーズ実行失敗
  - 統合テスト: GitHub API障害、メタデータ破損

- [x] **期待結果が明確である**
  - すべてのテストケースに「期待結果」セクションを記載
  - 具体的な値・状態を明示（例: `exit code == 0`, `result['success'] == True`）
  - 確認項目チェックリストを記載

### 追加の品質確認

- [x] **Requirements DocumentのFR-1〜FR-9がすべてカバーされている**
  - FR-1: WorkflowController実装 → 2.2, 3.1.1
  - FR-2: ConfigManager実装 → 2.1, 3.1.3
  - FR-3: CLI層実装 → 2.3, 3.1.2
  - FR-4: main.py修正 → 2.4
  - FR-5: phases/*.py修正 → 2.5.1
  - FR-6: metadata_manager.py修正 → 2.5.2
  - FR-7: claude_agent_client.py修正 → 2.5.3
  - FR-8: 既存テストの修正 → 3.3.1
  - FR-9: 旧ファイルの削除 → （Phase 9で実施）

- [x] **受け入れ基準（AC-1.1〜AC-9.1）がテストシナリオに反映されている**
  - AC-1.1〜1.3: WorkflowControllerのテスト（2.2.2〜2.2.7）
  - AC-2.1〜2.3: ConfigManagerのテスト（2.1.2〜2.1.5）
  - AC-3.1〜3.3: CLI層のテスト（2.3.1〜2.3.6）
  - AC-4.1: main.pyのテスト（2.4.1）
  - AC-5.1〜5.2: phases/*.pyのテスト（2.5.1）
  - AC-8.1: 既存テスト修正の検証（3.3.1）

- [x] **テストデータが具体的である**
  - config.yaml（正常系・異常系）を記載
  - 環境変数のサンプルを記載
  - metadata.json（正常系・異常系）を記載
  - モックデータの構造を記載

- [x] **テスト環境要件が明確である**
  - ローカルテスト環境の要件を記載
  - モック/スタブの必要性を記載
  - CI/CD環境の要件を記載

---

## まとめ

### テストシナリオのポイント

1. **テスト戦略: UNIT_INTEGRATION**
   - Unitテスト: 新規クラス（ConfigManager, WorkflowController, CLI層）の動作保証
   - Integrationテスト: 基盤レイヤーと既存コードの統合検証
   - BDDテスト: 不要（Phase 2の判断通り）

2. **テスト対象**
   - 新規実装: 4ファイル（WorkflowController, ConfigManager, CLI層）
   - 修正対象: 13ファイル（main.py, phases/*.py, metadata_manager.py, claude_agent_client.py）
   - 既存テスト修正: 70+ファイル（116件の失敗テスト修正含む）

3. **品質ゲート**
   - Phase 2の戦略に沿ったテストシナリオ: ✅
   - 主要な正常系がカバーされている: ✅
   - 主要な異常系がカバーされている: ✅
   - 期待結果が明確である: ✅

4. **次のステップ**
   - Phase 4: 実装（見積もり: 66~124時間）
   - Phase 5: テスト実装（見積もり: 16~32時間）
   - Phase 6: テスト実行（見積もり: 2~4時間）

---

**作成日**: 2025-10-13
**作成者**: Claude (AI Workflow - Phase 3)
**ステータス**: Test Scenario Phase Completed
