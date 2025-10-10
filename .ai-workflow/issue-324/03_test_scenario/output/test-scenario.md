# テストシナリオ - Issue #324

## Issue情報

- **Issue番号**: #324
- **タイトル**: [FEATURE] 実装フェーズとテストコード実装フェーズの分離
- **URL**: https://github.com/tielec/infrastructure-as-code/issues/324
- **優先度**: High
- **ラベル**: enhancement, ai-workflow, refactoring

## 1. テスト戦略サマリー

### 選択されたテスト戦略
**UNIT_INTEGRATION** (Phase 2で決定)

### テスト対象の範囲

#### Unit Test対象
- `WorkflowState.create_new()`: 新規ワークフロー作成時のフェーズ構造生成
- `WorkflowState.update_phase_status()`: test_implementationフェーズのステータス更新
- `WorkflowState.get_phase_status()`: test_implementationフェーズのステータス取得
- フェーズ順序の検証（implementation → test_implementation → testing）
- 存在しないフェーズへのアクセス時のエラーハンドリング

#### Integration Test対象
- 新規ワークフロー作成から全フェーズ実行までの一連の流れ
- 既存ワークフロー（Phase 1-7構成）の後方互換性
- Phase 4とPhase 5の責務分離（プロンプト内容検証）
- クリティカルシンキングレビューの動作確認
- Git auto-commit & push動作確認

### テストの目的

1. **機能正確性の検証**: test_implementationフェーズが正しく追加され、期待通りに動作すること
2. **後方互換性の検証**: 既存のワークフロー（Phase 1-7）が引き続き動作すること
3. **責務分離の検証**: Phase 4（実コード）とPhase 5（テストコード）の責務が明確に分離されていること
4. **統合動作の検証**: 新しいフェーズ構造でワークフロー全体が正しく機能すること

## 2. Unitテストシナリオ

### 2.1 WorkflowState.create_new() - test_implementationフェーズ追加

#### テストケース: test_create_new_includes_test_implementation_phase

**目的**: 新規ワークフロー作成時にtest_implementationフェーズが含まれることを検証

**前提条件**:
- 空のmetadata.jsonパス（新規作成）
- 有効なIssue情報（issue_number, issue_url, issue_title）

**入力**:
```python
metadata_path = Path('/tmp/test_metadata.json')
issue_number = '324'
issue_url = 'https://github.com/tielec/infrastructure-as-code/issues/324'
issue_title = '[FEATURE] 実装フェーズとテストコード実装フェーズの分離'
```

**期待結果**:
- metadata.jsonが作成される
- `phases`辞書に`test_implementation`キーが存在する
- `test_implementation`の初期状態:
  - `status`: "pending"
  - `retry_count`: 0
  - `started_at`: None
  - `completed_at`: None
  - `review_result`: None

**テストデータ**: 上記入力パラメータ

---

#### テストケース: test_create_new_test_implementation_phase_order

**目的**: test_implementationフェーズが正しい位置（implementationとtestingの間）に配置されることを検証

**前提条件**:
- 空のmetadata.jsonパス（新規作成）

**入力**:
```python
metadata_path = Path('/tmp/test_metadata.json')
issue_number = '324'
issue_url = 'https://github.com/tielec/infrastructure-as-code/issues/324'
issue_title = 'Test Phase Order'
```

**期待結果**:
- phases辞書のキー順序が以下の通り:
  1. planning
  2. requirements
  3. design
  4. test_scenario
  5. implementation
  6. **test_implementation** ← ここに配置
  7. testing
  8. documentation
  9. report

**検証方法**:
```python
phases_list = list(state.data['phases'].keys())
impl_index = phases_list.index('implementation')
test_impl_index = phases_list.index('test_implementation')
testing_index = phases_list.index('testing')
assert impl_index < test_impl_index < testing_index
```

**テストデータ**: 上記入力パラメータ

---

### 2.2 WorkflowState.update_phase_status() - test_implementationフェーズ対応

#### テストケース: test_update_phase_status_test_implementation_to_in_progress

**目的**: test_implementationフェーズのステータスを"in_progress"に更新できることを検証

**前提条件**:
- test_implementationフェーズを含むmetadata.jsonが存在
- test_implementationの初期status: "pending"

**入力**:
```python
state.update_phase_status('test_implementation', 'in_progress')
```

**期待結果**:
- metadata.json内のtest_implementation.statusが"in_progress"に更新される
- started_atにタイムスタンプが記録される
- 他のフィールド（retry_count等）は変更されない

**テストデータ**: 既存のWorkflowStateオブジェクト

---

#### テストケース: test_update_phase_status_test_implementation_to_completed

**目的**: test_implementationフェーズのステータスを"completed"に更新できることを検証

**前提条件**:
- test_implementationの現在のstatus: "in_progress"

**入力**:
```python
state.update_phase_status('test_implementation', 'completed')
```

**期待結果**:
- metadata.json内のtest_implementation.statusが"completed"に更新される
- completed_atにタイムスタンプが記録される
- started_atは保持される

**テストデータ**: 既存のWorkflowStateオブジェクト

---

#### テストケース: test_update_phase_status_invalid_phase_name

**目的**: 存在しないフェーズ名を指定した場合にエラーが発生することを検証

**前提条件**:
- 正常なWorkflowStateオブジェクト

**入力**:
```python
state.update_phase_status('test_implemantation', 'in_progress')  # typo
```

**期待結果**:
- KeyErrorまたは適切なカスタム例外が発生
- エラーメッセージに存在しないフェーズ名が含まれる
- metadata.jsonは変更されない

**テストデータ**: 既存のWorkflowStateオブジェクト

---

### 2.3 WorkflowState.get_phase_status() - test_implementationフェーズ対応

#### テストケース: test_get_phase_status_test_implementation

**目的**: test_implementationフェーズのステータスを取得できることを検証

**前提条件**:
- test_implementationフェーズのstatus: "pending"

**入力**:
```python
status = state.get_phase_status('test_implementation')
```

**期待結果**:
- status == "pending"
- 例外が発生しない

**テストデータ**: 既存のWorkflowStateオブジェクト

---

#### テストケース: test_get_phase_status_nonexistent_phase

**目的**: 存在しないフェーズのステータス取得時にエラーが発生することを検証

**前提条件**:
- 正常なWorkflowStateオブジェクト

**入力**:
```python
status = state.get_phase_status('nonexistent_phase')
```

**期待結果**:
- KeyErrorまたは適切なカスタム例外が発生
- エラーメッセージに存在しないフェーズ名が含まれる

**テストデータ**: 既存のWorkflowStateオブジェクト

---

### 2.4 フェーズ番号シフトの検証

#### テストケース: test_phase_indices_after_test_implementation_addition

**目的**: 各フェーズのインデックスが期待通りであることを検証

**前提条件**:
- 新規作成されたWorkflowState

**入力**:
```python
state = WorkflowState.create_new(...)
phases_list = list(state.data['phases'].keys())
```

**期待結果**:
- planning: index 0
- requirements: index 1
- design: index 2
- test_scenario: index 3
- implementation: index 4
- test_implementation: index 5 ← 新規
- testing: index 6 (旧: index 5)
- documentation: index 7 (旧: index 6)
- report: index 8 (旧: index 7)

**検証方法**:
```python
assert phases_list[5] == 'test_implementation'
assert phases_list[6] == 'testing'
assert phases_list[7] == 'documentation'
assert phases_list[8] == 'report'
```

**テストデータ**: 新規WorkflowStateオブジェクト

---

## 3. Integrationテストシナリオ

### 3.1 新規ワークフロー作成と実行

#### シナリオ: test_new_workflow_with_test_implementation_phase

**目的**: 新しいフェーズ構成（Phase 1-8）でワークフローが最後まで実行できることを検証

**前提条件**:
- クリーンな環境（既存のmetadata.jsonなし）
- Git リポジトリが初期化されている

**テスト手順**:
1. WorkflowState.create_new()で新規ワークフローを作成
2. metadata.jsonにtest_implementationフェーズが含まれることを確認
3. Phase 0（planning）を実行
4. Phase 1（requirements）を実行
5. Phase 2（design）を実行
6. Phase 3（test_scenario）を実行
7. Phase 4（implementation）を実行 → 実コードのみ実装されることを確認
8. Phase 5（test_implementation）を実行 → テストコードのみ実装されることを確認
9. Phase 6（testing）を実行
10. Phase 7（documentation）を実行
11. Phase 8（report）を実行

**期待結果**:
- すべてのフェーズが正常に完了する（status: "completed"）
- 各フェーズの成果物が作成される:
  - `.ai-workflow/issue-324/00_planning/output/planning.md`
  - `.ai-workflow/issue-324/01_requirements/output/requirements.md`
  - `.ai-workflow/issue-324/02_design/output/design.md`
  - `.ai-workflow/issue-324/03_test_scenario/output/test-scenario.md`
  - `.ai-workflow/issue-324/04_implementation/output/implementation.md`
  - `.ai-workflow/issue-324/05_test_implementation/output/test_implementation.md` ← 新規
  - `.ai-workflow/issue-324/06_testing/output/test-result.md`
  - `.ai-workflow/issue-324/07_documentation/output/documentation-update-log.md`
  - `.ai-workflow/issue-324/08_report/output/report.md`
- エラーや警告が発生しない

**確認項目**:
- [ ] metadata.jsonにすべてのフェーズが"completed"ステータスで記録されている
- [ ] 各フェーズの成果物ファイルが存在する
- [ ] Phase 4の成果物に実コードのみが含まれる（テストコードなし）
- [ ] Phase 5の成果物にテストコードのみが含まれる（実コードなし）
- [ ] Git commitが各フェーズで実行されている

---

### 3.2 既存ワークフローの後方互換性

#### シナリオ: test_existing_workflow_backward_compatibility

**目的**: 既存のワークフロー（Phase 1-7構成）が引き続き動作することを検証

**前提条件**:
- 既存のmetadata.json（Phase 1-7構成）が存在
  - phases: planning, requirements, design, test_scenario, implementation, testing, documentation, report
  - test_implementationフェーズは含まれない

**テスト手順**:
1. 既存のmetadata.jsonを読み込む
2. WorkflowState.load()でワークフローを読み込む
3. 各フェーズのステータスを取得できることを確認
4. update_phase_status()で既存フェーズのステータスを更新できることを確認
5. エラーが発生しないことを確認

**期待結果**:
- metadata.jsonが正常に読み込まれる
- test_implementationフェーズが存在しなくてもエラーにならない
- 既存フェーズ（planning, requirements, ..., report）のステータス取得・更新が正常に動作する
- 警告やエラーが発生しない

**確認項目**:
- [ ] WorkflowState.load()が正常に完了する
- [ ] get_phase_status('implementation')が動作する
- [ ] get_phase_status('testing')が動作する（Phase 5として）
- [ ] update_phase_status('testing', 'in_progress')が動作する
- [ ] 例外が発生しない

---

### 3.3 Phase 4とPhase 5の責務分離

#### シナリオ: test_phase_4_and_5_responsibility_separation

**目的**: Phase 4（implementation）とPhase 5（test_implementation）の責務が明確に分離されていることを検証

**前提条件**:
- プロンプトファイルが配置されている:
  - `scripts/ai-workflow/prompts/implementation/execute.txt`
  - `scripts/ai-workflow/prompts/test_implementation/execute.txt`

**テスト手順**:
1. implementation/execute.txtの内容を読み込む
2. 「実コードのみを実装」という文言が含まれることを確認
3. 「テストコードはPhase 5で実装」という文言が含まれることを確認
4. test_implementation/execute.txtの内容を読み込む
5. 「テストコードのみを実装」という文言が含まれることを確認
6. 「Phase 4の実コードを参照」という文言が含まれることを確認
7. 「Phase 3のテストシナリオを参照」という文言が含まれることを確認

**期待結果**:
- implementation/execute.txt:
  - 「実コード」「ビジネスロジック」「API」「データモデル」などの文言が含まれる
  - 「テストコードはPhase 5」「test_implementation」などの文言が含まれる
- test_implementation/execute.txt:
  - 「テストコード」「unit test」「integration test」などの文言が含まれる
  - 「Phase 4」「implementation」などの参照が含まれる
  - 「Phase 3」「test_scenario」などの参照が含まれる

**確認項目**:
- [ ] implementation/execute.txtに責務明確化の記述がある
- [ ] test_implementation/execute.txtにテスト実装専用の記述がある
- [ ] 両プロンプトで責務の境界が明確である

---

### 3.4 プロンプトファイルの存在確認

#### シナリオ: test_test_implementation_prompt_files_exist

**目的**: test_implementationフェーズのプロンプトファイルがすべて存在することを検証

**前提条件**:
- プロジェクトルートから相対パスでアクセス可能

**テスト手順**:
1. `scripts/ai-workflow/prompts/test_implementation/`ディレクトリが存在することを確認
2. `execute.txt`が存在することを確認
3. `review.txt`が存在することを確認
4. `revise.txt`が存在することを確認
5. 各ファイルが空でないことを確認（最低1文字以上）

**期待結果**:
- すべてのプロンプトファイルが存在する
- 各ファイルのサイズが0バイトでない
- UTF-8エンコーディングで読み込める

**確認項目**:
- [ ] `prompts/test_implementation/execute.txt`が存在する
- [ ] `prompts/test_implementation/review.txt`が存在する
- [ ] `prompts/test_implementation/revise.txt`が存在する
- [ ] 各ファイルが空でない

---

### 3.5 Phase番号シフトの検証

#### シナリオ: test_phase_number_shift_in_prompts

**目的**: testing、documentation、reportプロンプトのPhase番号が正しくシフトされていることを検証

**前提条件**:
- 更新されたプロンプトファイルが配置されている

**テスト手順**:
1. `prompts/testing/execute.txt`を読み込む
2. "Phase 6"という文言が含まれることを確認（旧: Phase 5）
3. `prompts/documentation/execute.txt`を読み込む
4. "Phase 7"という文言が含まれることを確認（旧: Phase 6）
5. `prompts/report/execute.txt`を読み込む
6. "Phase 8"という文言が含まれることを確認（旧: Phase 7）
7. 旧Phase番号（"Phase 5"が誤った箇所に残っていないか）を確認

**期待結果**:
- testing/execute.txt: "Phase 6"が含まれる、"Phase 5"は含まれない（またはtest_implementationの文脈でのみ）
- documentation/execute.txt: "Phase 7"が含まれる、"Phase 6"は含まれない（またはtestingの文脈でのみ）
- report/execute.txt: "Phase 8"が含まれる、"Phase 7"は含まれない（またはdocumentationの文脈でのみ）

**確認項目**:
- [ ] testing/execute.txtが"Phase 6"を参照している
- [ ] documentation/execute.txtが"Phase 7"を参照している
- [ ] report/execute.txtが"Phase 8"を参照している
- [ ] 旧Phase番号が誤った箇所に残っていない

---

### 3.6 クリティカルシンキングレビューの動作確認

#### シナリオ: test_critical_thinking_review_for_test_implementation

**目的**: test_implementationフェーズでクリティカルシンキングレビューが正しく機能することを検証

**前提条件**:
- test_implementation/review.txtが存在
- Phase 5（test_implementation）が"completed"ステータス

**テスト手順**:
1. Phase 5（test_implementation）を完了させる（テストコードを実装）
2. クリティカルシンキングレビューを実行
3. review.txtが読み込まれることを確認
4. レビュー結果がmetadata.jsonに記録されることを確認
5. ブロッカーが検出された場合、retryが要求されることを確認（意図的にブロッカーを混入）

**期待結果**:
- test_implementation/review.txtが読み込まれる
- レビュー観点が評価される:
  - テストカバレッジの確認
  - テストシナリオとの対応確認
  - エッジケースのテスト確認
  - テストの独立性確認
- metadata.jsonのtest_implementation.review_resultにレビュー結果が記録される
- ブロッカーがある場合、retry_countが増加する

**確認項目**:
- [ ] review.txtが読み込まれる
- [ ] レビュー結果がmetadata.jsonに記録される
- [ ] ブロッカー検出時にretryが要求される

---

### 3.7 Git auto-commit & push動作確認

#### シナリオ: test_git_auto_commit_push_all_phases

**目的**: すべてのフェーズでGit auto-commit & pushが正しく動作することを検証

**前提条件**:
- Gitリポジトリが初期化されている
- リモートリポジトリへのプッシュ権限がある

**テスト手順**:
1. 各フェーズ（Phase 0-8）を順次実行
2. 各フェーズ完了後にGit commitが実行されることを確認
3. コミットメッセージにPhase名が含まれることを確認
4. リモートリポジトリにpushされることを確認

**期待結果**:
- 各フェーズの成果物がGitにコミットされる
- コミットメッセージの形式:
  - `[ai-workflow] Phase 0 (planning) - completed`
  - `[ai-workflow] Phase 1 (requirements) - completed`
  - ...
  - `[ai-workflow] Phase 5 (test_implementation) - completed` ← 新規
  - ...
  - `[ai-workflow] Phase 8 (report) - completed`
- リモートリポジトリにpushされる

**確認項目**:
- [ ] Phase 5のコミットが存在する
- [ ] コミットメッセージに"test_implementation"が含まれる
- [ ] リモートリポジトリに全コミットがpushされている

---

## 4. テストデータ

### 4.1 正常データ

#### 新規ワークフロー用メタデータ
```json
{
  "issue_number": "324",
  "issue_url": "https://github.com/tielec/infrastructure-as-code/issues/324",
  "issue_title": "[FEATURE] 実装フェーズとテストコード実装フェーズの分離",
  "phases": {
    "planning": {"status": "pending", "retry_count": 0, ...},
    "requirements": {"status": "pending", "retry_count": 0, ...},
    "design": {"status": "pending", "retry_count": 0, ...},
    "test_scenario": {"status": "pending", "retry_count": 0, ...},
    "implementation": {"status": "pending", "retry_count": 0, ...},
    "test_implementation": {"status": "pending", "retry_count": 0, ...},
    "testing": {"status": "pending", "retry_count": 0, ...},
    "documentation": {"status": "pending", "retry_count": 0, ...},
    "report": {"status": "pending", "retry_count": 0, ...}
  }
}
```

#### 既存ワークフロー用メタデータ（後方互換性テスト用）
```json
{
  "issue_number": "305",
  "issue_url": "https://github.com/tielec/infrastructure-as-code/issues/305",
  "issue_title": "全フェーズ完成 v1.3.0",
  "phases": {
    "planning": {"status": "completed", "retry_count": 0, ...},
    "requirements": {"status": "completed", "retry_count": 0, ...},
    "design": {"status": "completed", "retry_count": 0, ...},
    "test_scenario": {"status": "completed", "retry_count": 0, ...},
    "implementation": {"status": "completed", "retry_count": 0, ...},
    "testing": {"status": "completed", "retry_count": 0, ...},
    "documentation": {"status": "completed", "retry_count": 0, ...},
    "report": {"status": "completed", "retry_count": 0, ...}
  }
}
```

### 4.2 異常データ

#### 無効なフェーズ名
```python
invalid_phase_names = [
    'test_implemantation',  # typo
    'testimplementation',   # アンダースコアなし
    'test-implementation',  # ハイフン
    'TestImplementation',   # キャメルケース
    'TEST_IMPLEMENTATION',  # 大文字
    'nonexistent_phase',    # 存在しないフェーズ
    '',                      # 空文字列
    None,                   # None
]
```

#### 無効なステータス値
```python
invalid_status_values = [
    'invalid_status',
    'COMPLETED',  # 大文字
    'Complete',   # 異なるスペル
    '',           # 空文字列
    None,         # None
]
```

### 4.3 境界値データ

#### フェーズ名の長さ
```python
boundary_phase_names = [
    'a' * 1,      # 最小長（1文字）
    'a' * 50,     # 通常の長さ
    'a' * 255,    # 最大長（仮定）
]
```

#### retry_countの境界値
```python
boundary_retry_counts = [
    0,    # 最小値
    1,    # 初回リトライ
    2,    # 2回目リトライ
    3,    # 最大リトライ回数（仮定）
]
```

---

## 5. テスト環境要件

### 5.1 必要なテスト環境

#### ローカル開発環境
- **OS**: Amazon Linux 2023（または互換環境）
- **Python**: 3.11以上
- **Git**: 2.40以上
- **pytest**: 最新版

#### CI/CD環境（Jenkins）
- **Jenkins**: 最新LTSバージョン
- **Jenkinsプラグイン**: Git、Pipeline、Workspace Cleanup
- **実行環境**: 上記ローカル開発環境と同等

### 5.2 必要な外部サービス

#### Git リポジトリ
- **GitHub**: リモートリポジトリ
- **認証**: SSHキーまたはPersonal Access Token
- **権限**: push権限

#### AWS SSM Parameter Store（オプション）
- **用途**: 設定情報の取得（必要に応じて）
- **認証**: AWS認証情報

### 5.3 モック/スタブの必要性

#### ユニットテストでモックが必要なもの
- **Gitコマンド**: commit、push（ユニットテストでは実際に実行しない）
- **ファイルI/O**: 一部のテストではtempディレクトリを使用

#### インテグレーションテストで実環境を使用するもの
- **Git リポジトリ**: 実際のGit操作を実行
- **ファイルシステム**: 実際のファイル読み書き

---

## 6. エッジケースシナリオ

### 6.1 フェーズ名のtypo

#### エッジケース: 存在しないフェーズ名でupdate_phase_status()を呼ぶ

**入力**:
```python
state.update_phase_status('test_implemantation', 'in_progress')  # 'test_implementation'のtypo
```

**期待結果**:
- KeyErrorまたは適切なカスタム例外が発生
- エラーメッセージ: "Phase 'test_implemantation' does not exist. Available phases: ..."
- metadata.jsonは変更されない

---

### 6.2 フェーズの順序を無視した実行

#### エッジケース: Phase 5を実行する前にPhase 6を実行しようとする

**前提条件**:
- Phase 4（implementation）が完了
- Phase 5（test_implementation）が未実行

**操作**:
- Phase 6（testing）を実行しようとする

**期待結果**:
- エラーまたは警告が表示される（「Phase 5が未完了です」等）
- または、Phase 5のテストコードがない状態でPhase 6が失敗する

**注意**: 現在の実装ではフェーズ順序の強制はないため、この挙動は実装次第

---

### 6.3 metadata.jsonが破損している場合

#### エッジケース: metadata.jsonのphasesが空

**入力**:
```json
{
  "issue_number": "324",
  "phases": {}
}
```

**操作**:
- WorkflowState.load()で読み込む

**期待結果**:
- エラーが発生する（"phases is empty"等）
- または、デフォルトのphasesで初期化される

---

### 6.4 同じフェーズのステータスを複数回更新

#### エッジケース: test_implementationを"in_progress"→"completed"→"in_progress"と更新

**操作**:
```python
state.update_phase_status('test_implementation', 'in_progress')
state.update_phase_status('test_implementation', 'completed')
state.update_phase_status('test_implementation', 'in_progress')  # 再度in_progress
```

**期待結果**:
- すべての更新が成功する
- started_atは最初の"in_progress"時のタイムスタンプが保持される
- completed_atはクリアされる（またはNoneになる）

---

## 7. テスト実行順序

テストは以下の順序で実行することを推奨します：

### Phase 1: Unitテスト
1. `test_create_new_includes_test_implementation_phase`
2. `test_create_new_test_implementation_phase_order`
3. `test_update_phase_status_test_implementation_to_in_progress`
4. `test_update_phase_status_test_implementation_to_completed`
5. `test_update_phase_status_invalid_phase_name`
6. `test_get_phase_status_test_implementation`
7. `test_get_phase_status_nonexistent_phase`
8. `test_phase_indices_after_test_implementation_addition`

### Phase 2: Integrationテスト
1. `test_test_implementation_prompt_files_exist`
2. `test_phase_4_and_5_responsibility_separation`
3. `test_phase_number_shift_in_prompts`
4. `test_existing_workflow_backward_compatibility`
5. `test_new_workflow_with_test_implementation_phase`
6. `test_critical_thinking_review_for_test_implementation`
7. `test_git_auto_commit_push_all_phases`

**理由**:
- ユニットテストを先に実行して基本機能を検証
- プロンプトファイルの存在確認を最初に実施（後続テストの前提条件）
- 後方互換性テストを新規ワークフローテストの前に実施
- 全体統合テスト（Git操作含む）を最後に実施

---

## 8. 品質ゲート確認

このテストシナリオは以下の品質ゲートを満たしています：

### ✅ Phase 2の戦略に沿ったテストシナリオである
- テスト戦略: UNIT_INTEGRATION
- ユニットテストシナリオ: 8個（セクション2）
- インテグレーションテストシナリオ: 7個（セクション3）
- BDDシナリオ: なし（UNIT_INTEGRATIONのためBDDは不要）

### ✅ 主要な正常系がカバーされている
- WorkflowState.create_new()でtest_implementationフェーズが追加される（Unit）
- 新規ワークフローが最後まで実行できる（Integration）
- Phase 4とPhase 5の責務が分離されている（Integration）

### ✅ 主要な異常系がカバーされている
- 存在しないフェーズ名でupdate_phase_status()を呼ぶ（Unit）
- 存在しないフェーズ名でget_phase_status()を呼ぶ（Unit）
- エッジケース: フェーズ名のtypo、破損したmetadata.json等（セクション6）

### ✅ 期待結果が明確である
- すべてのテストケースに「期待結果」セクションがあり、具体的な検証内容が記載されている
- 検証方法の例（assertステートメント）が記載されている箇所もある

---

## 9. テストカバレッジ目標

### 9.1 コードカバレッジ

#### 新規コード（Phase 4で実装される）
- **目標**: 80%以上
- **対象**:
  - `workflow_state.py`のcreate_new()メソッドの変更箇所
  - 新規プロンプトファイル（test_implementation/execute.txt等）

#### 既存コード
- **目標**: 既存のカバレッジを維持（低下させない）
- **対象**:
  - `workflow_state.py`の既存メソッド
  - 既存プロンプトファイル

### 9.2 要件カバレッジ

#### 機能要件
- FR-001: Phase 5の新設 → ✅ ユニットテスト、インテグレーションテストでカバー
- FR-002: 既存フェーズの番号変更 → ✅ インテグレーションテストでカバー
- FR-003: Phase 4の責務明確化 → ✅ インテグレーションテストでカバー
- FR-004: Phase 5のプロンプト作成 → ✅ インテグレーションテストでカバー
- FR-005: metadata.jsonの拡張 → ✅ ユニットテストでカバー
- FR-006: 依存関係の明確化 → ✅ インテグレーションテストでカバー

#### 非機能要件
- NFR-001: 後方互換性 → ✅ インテグレーションテストでカバー
- NFR-002: パフォーマンス → △ 手動計測（自動テストでは測定しない）
- NFR-003: ログとトレーサビリティ → ✅ インテグレーションテストで確認

---

## 10. 次のステップ

本テストシナリオの承認後、Phase 4（実装）に進みます。

Phase 4では以下を実施します：
1. workflow_state.pyの修正（create_new()にtest_implementationフェーズを追加）
2. test_implementationプロンプトファイルの作成（execute.txt、review.txt、revise.txt）
3. implementation/execute.txtの責務明確化
4. testing/execute.txt、documentation/execute.txt、report/execute.txtのPhase番号更新
5. 実装ログの作成（implementation.md）

Phase 5（テストコード実装）では本テストシナリオに基づいてテストコードを実装します。

---

**テストシナリオ作成日時**: 2025-10-10
**作成者**: AI Workflow Orchestrator
**レビュー状態**: 未レビュー（Phase 3 クリティカルシンキングレビュー待ち）
**バージョン**: 1.0
