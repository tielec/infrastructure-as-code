# テストシナリオ: Phase execute()失敗時のリトライ機能修正

## 1. テスト戦略サマリー

### 1.1 選択されたテスト戦略

**UNIT_INTEGRATION** (Phase 2設計書より)

### 1.2 テスト対象の範囲

- **主要対象**: `scripts/ai-workflow/phases/base_phase.py`の`run()`メソッド
- **統合対象**:
  - `execute()` → `review()` → `revise()` → `review()`のフロー
  - MetadataManager、GitHubClient、GitManager、ClaudeAgentClientとの連携
  - 全Phaseサブクラス（requirements, design, test_scenario, implementation, testing, documentation, report, planning）

### 1.3 テストの目的

本テストの目的は、以下を検証することです：

1. **execute()失敗時のリトライ動作**: execute()が失敗した場合でも、リトライループに入り、revise()による修正が実行されること
2. **統一リトライループの動作**: execute()とrevise()が同一のリトライループ内で正しく動作すること
3. **最大リトライ回数の制御**: MAX_RETRIES=3が正しく機能し、無限ループが発生しないこと
4. **レビューとリトライの連携**: review()の結果に基づいてrevise()が適切に実行されること
5. **メタデータ・GitHub・Git連携**: リトライ処理中のメタデータ更新、GitHub通知、Git commit & pushが正しく動作すること

---

## 2. Unitテストシナリオ

### 2.1 リトライループの基本動作

#### UT-001: execute()成功時の正常終了

- **目的**: 初回execute()が成功した場合、リトライせずに正常終了することを検証
- **前提条件**:
  - BasePhaseのサブクラス（ConcretePhase）が定義されている
  - execute()が`{'success': True, 'output': 'test_output'}`を返すようにモック化
- **入力**: なし（run()メソッドを呼び出し）
- **期待結果**:
  - execute()が1回だけ呼ばれる
  - review()が呼ばれる（最終レビュー）
  - revise()は呼ばれない
  - run()がTrueを返す
  - final_status='completed'
- **テストデータ**: execute()の戻り値 = `{'success': True, 'output': 'test_output'}`

#### UT-002: execute()失敗時のリトライ実行

- **目的**: execute()が失敗した場合、リトライループに入り、review() → revise()が実行されることを検証
- **前提条件**:
  - execute()が初回実行で`{'success': False, 'error': 'Test error'}`を返す
  - review()が`{'result': 'FAIL', 'feedback': 'Test feedback'}`を返す
  - revise()が`{'success': True, 'output': 'revised_output'}`を返す
- **入力**: なし
- **期待結果**:
  - execute()が1回呼ばれる（attempt=1）
  - review()が2回呼ばれる（attempt=2の前と最終レビュー）
  - revise()が1回呼ばれる（attempt=2）
  - `[ATTEMPT 1/3]`と`[ATTEMPT 2/3]`のログが出力される
  - run()がTrueを返す
  - final_status='completed'
- **テストデータ**:
  - execute()の戻り値 = `{'success': False, 'error': 'Test error'}`
  - review()の戻り値 = `{'result': 'FAIL', 'feedback': 'Test feedback'}`
  - revise()の戻り値 = `{'success': True, 'output': 'revised_output'}`

#### UT-003: execute()失敗後の最大リトライ到達

- **目的**: execute()失敗後、最大リトライ回数（3回）に到達した場合、失敗終了することを検証
- **前提条件**:
  - execute()が`{'success': False, 'error': 'Test error'}`を返す
  - review()が常に`{'result': 'FAIL', 'feedback': 'Test feedback'}`を返す
  - revise()が常に`{'success': False, 'error': 'Revise failed'}`を返す
- **入力**: なし
- **期待結果**:
  - execute()が1回呼ばれる（attempt=1）
  - review()が2回呼ばれる（attempt=2, attempt=3の前）
  - revise()が2回呼ばれる（attempt=2, attempt=3）
  - `[ATTEMPT 1/3]`, `[ATTEMPT 2/3]`, `[ATTEMPT 3/3]`のログが出力される
  - `[WARNING] Attempt 1 failed: Test error`のログが出力される
  - `[WARNING] Attempt 2 failed: Revise failed`のログが出力される
  - `[WARNING] Attempt 3 failed: Revise failed`のログが出力される
  - GitHub Issueに「最大リトライ回数(3)に到達しました」が投稿される
  - run()がFalseを返す
  - final_status='failed'
- **テストデータ**:
  - execute()の戻り値 = `{'success': False, 'error': 'Test error'}`
  - review()の戻り値 = `{'result': 'FAIL', 'feedback': 'Test feedback'}`
  - revise()の戻り値 = `{'success': False, 'error': 'Revise failed'}`

#### UT-004: execute()失敗後、revise()成功→review()合格

- **目的**: execute()失敗後、revise()が成功し、その後のreview()が合格する正常フローを検証
- **前提条件**:
  - execute()が`{'success': False, 'error': 'Initial error'}`を返す
  - 1回目のreview()（attempt=2の前）が`{'result': 'FAIL', 'feedback': 'Need revision'}`を返す
  - revise()が`{'success': True, 'output': 'revised_output'}`を返す
  - 2回目のreview()（最終レビュー）が`{'result': 'PASS', 'feedback': ''}`を返す
- **入力**: なし
- **期待結果**:
  - execute()が1回呼ばれる
  - review()が2回呼ばれる
  - revise()が1回呼ばれる
  - 最終的にrun()がTrueを返す
  - final_status='completed'
  - review_result='PASS'
- **テストデータ**:
  - execute()の戻り値 = `{'success': False, 'error': 'Initial error'}`
  - 1回目review()の戻り値 = `{'result': 'FAIL', 'feedback': 'Need revision'}`
  - revise()の戻り値 = `{'success': True, 'output': 'revised_output'}`
  - 2回目review()の戻り値 = `{'result': 'PASS', 'feedback': ''}`

#### UT-005: attempt>=2でreview()がPASSの場合の早期終了

- **目的**: 2回目以降のattemptでreview()がPASSを返した場合、revise()をスキップして成功終了することを検証
- **前提条件**:
  - execute()が`{'success': False, 'error': 'Initial error'}`を返す
  - 1回目のreview()（attempt=2の前）が`{'result': 'PASS', 'feedback': ''}`を返す
- **入力**: なし
- **期待結果**:
  - execute()が1回呼ばれる
  - review()が1回呼ばれる（attempt=2の前）
  - revise()は呼ばれない
  - `[ATTEMPT 1/3]`と`[ATTEMPT 2/3]`のログが出力される
  - run()がTrueを返す
  - final_status='completed'
- **テストデータ**:
  - execute()の戻り値 = `{'success': False, 'error': 'Initial error'}`
  - review()の戻り値 = `{'result': 'PASS', 'feedback': ''}`

### 2.2 エラーハンドリング

#### UT-006: revise()メソッドが実装されていない場合

- **目的**: revise()が実装されていないPhaseサブクラスで、execute()失敗時に適切なエラーメッセージが出力されることを検証
- **前提条件**:
  - BasePhaseのサブクラス（NoRevisePhase）が定義されており、revise()メソッドが実装されていない
  - execute()が`{'success': False, 'error': 'Test error'}`を返す
  - review()が`{'result': 'FAIL', 'feedback': 'Test feedback'}`を返す
- **入力**: なし
- **期待結果**:
  - execute()が1回呼ばれる
  - review()が1回呼ばれる（attempt=2の前）
  - `[ERROR] NoRevisePhase.revise()メソッドが実装されていません。`のログが出力される
  - GitHub Issueに「revise()メソッドが未実装のため、修正できません。」が投稿される
  - run()がFalseを返す
  - final_status='failed'
- **テストデータ**:
  - execute()の戻り値 = `{'success': False, 'error': 'Test error'}`
  - review()の戻り値 = `{'result': 'FAIL', 'feedback': 'Test feedback'}`

#### UT-007: execute()が例外をスローした場合

- **目的**: execute()実行中に例外が発生した場合、適切にハンドリングされることを検証
- **前提条件**:
  - execute()がRuntimeError('Unexpected error')をスローする
- **入力**: なし
- **期待結果**:
  - execute()が1回呼ばれる
  - 例外がキャッチされる
  - final_status='failed'
  - GitHub Issueにエラーメッセージが投稿される
  - finally句でGit commit & pushが実行される
- **テストデータ**: execute()がRuntimeError('Unexpected error')をスロー

#### UT-008: revise()が例外をスローした場合

- **目的**: revise()実行中に例外が発生した場合、適切にハンドリングされることを検証
- **前提条件**:
  - execute()が`{'success': False, 'error': 'Initial error'}`を返す
  - review()が`{'result': 'FAIL', 'feedback': 'Test feedback'}`を返す
  - revise()がRuntimeError('Revise error')をスローする
- **入力**: なし
- **期待結果**:
  - execute()が1回呼ばれる
  - review()が1回呼ばれる（attempt=2の前）
  - revise()が1回呼ばれる
  - 例外がキャッチされる
  - final_status='failed'
  - GitHub Issueにエラーメッセージが投稿される
  - finally句でGit commit & pushが実行される
- **テストデータ**:
  - execute()の戻り値 = `{'success': False, 'error': 'Initial error'}`
  - review()の戻り値 = `{'result': 'FAIL', 'feedback': 'Test feedback'}`
  - revise()がRuntimeError('Revise error')をスロー

### 2.3 ログ出力とメタデータ更新

#### UT-009: 試行回数ログの出力

- **目的**: 各試行の開始時に`[ATTEMPT N/3]`形式でログが出力されることを検証
- **前提条件**:
  - execute()が`{'success': False, 'error': 'Test error'}`を返す
  - review()が`{'result': 'FAIL', 'feedback': 'Test feedback'}`を返す
  - revise()が`{'success': True, 'output': 'revised_output'}`を返す（2回目のreview()で合格）
- **入力**: なし
- **期待結果**:
  - 標準出力に以下が含まれる:
    ```
    ================================================================================
    [ATTEMPT 1/3] Phase: test_phase
    ================================================================================
    ```
    ```
    ================================================================================
    [ATTEMPT 2/3] Phase: test_phase
    ================================================================================
    ```
  - 80文字の区切り線（`=`）が各試行の前に出力される
- **テストデータ**:
  - execute()の戻り値 = `{'success': False, 'error': 'Test error'}`
  - review()の戻り値 = `{'result': 'FAIL', 'feedback': 'Test feedback'}` → `{'result': 'PASS'}`
  - revise()の戻り値 = `{'success': True, 'output': 'revised_output'}`

#### UT-010: 失敗時の警告ログ出力

- **目的**: 各試行が失敗した場合、`[WARNING]`ログが出力されることを検証
- **前提条件**:
  - execute()が`{'success': False, 'error': 'Execute failed'}`を返す
  - review()が`{'result': 'FAIL', 'feedback': 'Test feedback'}`を返す
  - revise()が`{'success': False, 'error': 'Revise failed'}`を返す（2回）
- **入力**: なし
- **期待結果**:
  - 標準出力に以下が含まれる:
    - `[WARNING] Attempt 1 failed: Execute failed`
    - `[WARNING] Attempt 2 failed: Revise failed`
    - `[WARNING] Attempt 3 failed: Revise failed`
- **テストデータ**:
  - execute()の戻り値 = `{'success': False, 'error': 'Execute failed'}`
  - review()の戻り値 = `{'result': 'FAIL', 'feedback': 'Test feedback'}`
  - revise()の戻り値 = `{'success': False, 'error': 'Revise failed'}`

#### UT-011: メタデータのretry_count更新

- **目的**: revise()実行時にメタデータのretry_countが正しくインクリメントされることを検証
- **前提条件**:
  - execute()が`{'success': False, 'error': 'Test error'}`を返す
  - review()が`{'result': 'FAIL', 'feedback': 'Test feedback'}`を返す
  - revise()が`{'success': True, 'output': 'revised_output'}`を返す
  - MetadataManagerがモック化されている
- **入力**: なし
- **期待結果**:
  - execute()失敗後、review()実行前にretry_countがインクリメントされない
  - revise()実行前にmetadata.increment_retry_count()が1回呼ばれる
  - メタデータのretry_countが1増加する
- **テストデータ**:
  - execute()の戻り値 = `{'success': False, 'error': 'Test error'}`
  - review()の戻り値 = `{'result': 'FAIL', 'feedback': 'Test feedback'}`
  - revise()の戻り値 = `{'success': True, 'output': 'revised_output'}`

#### UT-012: phase statusの更新

- **目的**: 各ステージでphase statusが正しく更新されることを検証
- **前提条件**:
  - execute()が成功を返す
  - review()が合格を返す
  - MetadataManagerがモック化されている
- **入力**: なし
- **期待結果**:
  - run()開始時に`update_phase_status(status='in_progress')`が呼ばれる
  - run()成功終了時に`update_phase_status(status='completed', review_result='PASS')`が呼ばれる
- **テストデータ**:
  - execute()の戻り値 = `{'success': True, 'output': 'test_output'}`
  - review()の戻り値 = `{'result': 'PASS', 'feedback': ''}`

### 2.4 GitHub連携

#### UT-013: レビュー結果のGitHub投稿（attempt>=2）

- **目的**: 2回目以降のattemptでreview()実行後、レビュー結果がGitHub Issueに投稿されることを検証
- **前提条件**:
  - execute()が`{'success': False, 'error': 'Test error'}`を返す
  - review()が`{'result': 'FAIL', 'feedback': 'Test feedback', 'suggestions': ['Suggestion 1']}`を返す
  - GitHubClientがモック化されている
- **入力**: なし
- **期待結果**:
  - attempt=2の前にreview()が実行される
  - post_review()が以下の引数で呼ばれる:
    - result='FAIL'
    - feedback='Test feedback'
    - suggestions=['Suggestion 1']
- **テストデータ**:
  - execute()の戻り値 = `{'success': False, 'error': 'Test error'}`
  - review()の戻り値 = `{'result': 'FAIL', 'feedback': 'Test feedback', 'suggestions': ['Suggestion 1']}`

#### UT-014: 最大リトライ到達時のGitHub投稿

- **目的**: 最大リトライ回数に到達した場合、適切なメッセージがGitHub Issueに投稿されることを検証
- **前提条件**:
  - execute()が`{'success': False, 'error': 'Test error'}`を返す
  - review()が常に`{'result': 'FAIL', 'feedback': 'Test feedback'}`を返す
  - revise()が常に`{'success': False, 'error': 'Revise failed'}`を返す
  - GitHubClientがモック化されている
- **入力**: なし
- **期待結果**:
  - post_progress()が以下の引数で呼ばれる:
    - status='failed'
    - details='最大リトライ回数(3)に到達しました'
- **テストデータ**:
  - execute()の戻り値 = `{'success': False, 'error': 'Test error'}`
  - review()の戻り値 = `{'result': 'FAIL', 'feedback': 'Test feedback'}`
  - revise()の戻り値 = `{'success': False, 'error': 'Revise failed'}`

### 2.5 Git連携

#### UT-015: finally句でのGit commit & push

- **目的**: run()実行後、成功・失敗に関わらずfinally句でGit commit & pushが実行されることを検証
- **前提条件**:
  - execute()が成功を返す
  - GitManagerがモック化されている
- **入力**: なし
- **期待結果**:
  - finally句で_auto_commit_and_push()が呼ばれる
  - 引数:
    - git_manager: GitManagerインスタンス
    - final_status: 'completed'
    - review_result: 'PASS'
- **テストデータ**:
  - execute()の戻り値 = `{'success': True, 'output': 'test_output'}`
  - review()の戻り値 = `{'result': 'PASS', 'feedback': ''}`

#### UT-016: 例外発生時もfinally句でGit commit & push

- **目的**: 例外発生時でもfinally句でGit commit & pushが実行されることを検証
- **前提条件**:
  - execute()がRuntimeError('Unexpected error')をスローする
  - GitManagerがモック化されている
- **入力**: なし
- **期待結果**:
  - 例外がスローされる
  - finally句で_auto_commit_and_push()が呼ばれる
  - 引数:
    - git_manager: GitManagerインスタンス
    - final_status: 'failed'
    - review_result: None
- **テストデータ**: execute()がRuntimeError('Unexpected error')をスロー

---

## 3. Integrationテストシナリオ

### 3.1 実際のPhaseクラスとの統合

#### IT-001: RequirementsPhaseでのexecute()失敗→revise()成功フロー

- **目的**: 実際のRequirementsPhaseでexecute()が失敗した場合、revise()によるリトライが実行され、最終的に成功することを検証
- **前提条件**:
  - テスト用のGitHubリポジトリが存在する
  - テスト用のIssue（例: #999）が存在する
  - メタデータファイル（`.ai-workflow/issue-999/metadata.json`）が存在する
  - ClaudeAgentClientが正常に動作する（または適切にモック化）
- **テスト手順**:
  1. RequirementsPhaseのインスタンスを作成
  2. execute()が失敗するようにClaudeAgentClientをモック化（初回のみ失敗、2回目は成功）
  3. run()を実行
  4. リトライループの動作を観察
- **期待結果**:
  - execute()が1回実行され、失敗を返す
  - `[ATTEMPT 1/3]`のログが出力される
  - `[ATTEMPT 2/3]`のログが出力される
  - review()が実行される（attempt=2の前）
  - review()が'FAIL'を返す
  - revise()が実行される
  - revise()が成功を返す
  - 最終的にrun()がTrueを返す
  - requirements.mdファイルが正しく生成される
  - メタデータのretry_countが1になる
  - GitHub Issueにレビュー結果が投稿される
  - Git commit & pushが実行される
- **確認項目**:
  - [ ] execute()が1回実行されたか
  - [ ] revise()が1回実行されたか
  - [ ] 最終的にrun()がTrueを返したか
  - [ ] requirements.mdが生成されたか
  - [ ] metadata.jsonのretry_countが1か
  - [ ] GitHub Issueにレビュー結果が投稿されたか
  - [ ] Gitにcommit & pushされたか

#### IT-002: DesignPhaseでのexecute()失敗→最大リトライ到達

- **目的**: 実際のDesignPhaseでexecute()が失敗し、リトライが最大回数に到達した場合、失敗終了することを検証
- **前提条件**:
  - テスト用のGitHubリポジトリが存在する
  - テスト用のIssue（例: #999）が存在する
  - メタデータファイルが存在する
  - ClaudeAgentClientが正常に動作する（または適切にモック化）
- **テスト手順**:
  1. DesignPhaseのインスタンスを作成
  2. execute()が常に失敗するようにモック化
  3. review()が常に'FAIL'を返すようにモック化
  4. revise()が常に失敗するようにモック化
  5. run()を実行
  6. 最大リトライ回数に到達することを確認
- **期待結果**:
  - execute()が1回実行され、失敗を返す
  - `[ATTEMPT 1/3]`, `[ATTEMPT 2/3]`, `[ATTEMPT 3/3]`のログが出力される
  - review()が2回実行される（attempt=2, 3の前）
  - revise()が2回実行される
  - すべての試行が失敗する
  - `[WARNING] Attempt 1 failed: ...`のログが出力される
  - `[WARNING] Attempt 2 failed: ...`のログが出力される
  - `[WARNING] Attempt 3 failed: ...`のログが出力される
  - GitHub Issueに「最大リトライ回数(3)に到達しました」が投稿される
  - run()がFalseを返す
  - メタデータのphase statusが'failed'になる
  - メタデータのretry_countが2になる（revise()が2回実行されたため）
  - Git commit & pushが実行される（失敗時も実行）
- **確認項目**:
  - [ ] execute()が1回実行されたか
  - [ ] revise()が2回実行されたか
  - [ ] 最大リトライ回数（3回）に到達したか
  - [ ] run()がFalseを返したか
  - [ ] metadata.jsonのphase statusが'failed'か
  - [ ] metadata.jsonのretry_countが2か
  - [ ] GitHub Issueに「最大リトライ回数(3)に到達しました」が投稿されたか
  - [ ] Gitにcommit & pushされたか（失敗時も実行）

#### IT-003: TestScenarioPhaseでのexecute()成功→review()合格

- **目的**: 実際のTestScenarioPhaseでexecute()が成功し、review()が合格する正常フローを検証
- **前提条件**:
  - テスト用のGitHubリポジトリが存在する
  - テスト用のIssue（例: #999）が存在する
  - メタデータファイルが存在する
  - 要件定義書（requirements.md）と設計書（design.md）が存在する
  - ClaudeAgentClientが正常に動作する（または適切にモック化）
- **テスト手順**:
  1. TestScenarioPhaseのインスタンスを作成
  2. execute()が成功するようにモック化
  3. review()が'PASS'を返すようにモック化
  4. run()を実行
  5. リトライが発生しないことを確認
- **期待結果**:
  - execute()が1回実行され、成功を返す
  - `[ATTEMPT 1/3]`のログが出力される
  - review()が1回実行される（最終レビュー）
  - review()が'PASS'を返す
  - revise()は実行されない
  - run()がTrueを返す
  - test-scenario.mdファイルが正しく生成される
  - メタデータのphase statusが'completed'になる
  - メタデータのreview_resultが'PASS'になる
  - メタデータのretry_countが0のまま（リトライしていないため）
  - GitHub Issueにレビュー結果が投稿される
  - Git commit & pushが実行される
- **確認項目**:
  - [ ] execute()が1回だけ実行されたか
  - [ ] revise()が実行されなかったか
  - [ ] run()がTrueを返したか
  - [ ] test-scenario.mdが生成されたか
  - [ ] metadata.jsonのphase statusが'completed'か
  - [ ] metadata.jsonのreview_resultが'PASS'か
  - [ ] metadata.jsonのretry_countが0か
  - [ ] GitHub Issueにレビュー結果が投稿されたか
  - [ ] Gitにcommit & pushされたか

### 3.2 メタデータ連携

#### IT-004: リトライ回数のメタデータへの記録

- **目的**: リトライ実行時にメタデータのretry_countが正しく更新されることを検証
- **前提条件**:
  - テスト用のメタデータファイルが存在する
  - MetadataManagerが正常に動作する
  - BasePhaseのサブクラス（ConcretePhase）が定義されている
- **テスト手順**:
  1. 初期状態のメタデータファイルを作成（retry_count=0）
  2. execute()が失敗するように設定
  3. review()が'FAIL'を返すように設定
  4. revise()を2回実行する（1回目は失敗、2回目は成功）
  5. run()を実行
  6. メタデータファイルを読み込み、retry_countを確認
- **期待結果**:
  - 初期状態: retry_count=0
  - 1回目のrevise()実行前: retry_count=1にインクリメント
  - 2回目のrevise()実行前: retry_count=2にインクリメント
  - 最終的なretry_count=2
  - メタデータファイルに正しく保存される
- **確認項目**:
  - [ ] revise()実行前にretry_countがインクリメントされたか
  - [ ] 最終的なretry_countが2か
  - [ ] metadata.jsonファイルに正しく保存されたか

#### IT-005: phase statusの遷移（成功ケース）

- **目的**: run()実行中のphase statusの遷移が正しく記録されることを検証（成功ケース）
- **前提条件**:
  - テスト用のメタデータファイルが存在する
  - MetadataManagerが正常に動作する
  - BasePhaseのサブクラス（ConcretePhase）が定義されている
- **テスト手順**:
  1. 初期状態のメタデータファイルを作成（status=null）
  2. execute()が成功するように設定
  3. review()が'PASS'を返すように設定
  4. run()を実行
  5. 各ステージでメタデータファイルを確認
- **期待結果**:
  - run()開始時: status='in_progress'
  - execute()成功後: status='in_progress'（まだレビュー前）
  - review()合格後: status='completed', review_result='PASS'
  - 最終的なstatus='completed', review_result='PASS'
- **確認項目**:
  - [ ] run()開始時にstatus='in_progress'になったか
  - [ ] review()合格後にstatus='completed'になったか
  - [ ] review_result='PASS'が記録されたか
  - [ ] metadata.jsonファイルに正しく保存されたか

#### IT-006: phase statusの遷移（失敗ケース）

- **目的**: run()実行中のphase statusの遷移が正しく記録されることを検証（失敗ケース）
- **前提条件**:
  - テスト用のメタデータファイルが存在する
  - MetadataManagerが正常に動作する
  - BasePhaseのサブクラス（ConcretePhase）が定義されている
- **テスト手順**:
  1. 初期状態のメタデータファイルを作成（status=null）
  2. execute()が失敗するように設定
  3. review()が常に'FAIL'を返すように設定
  4. revise()が常に失敗するように設定
  5. run()を実行
  6. 各ステージでメタデータファイルを確認
- **期待結果**:
  - run()開始時: status='in_progress'
  - execute()失敗後: status='in_progress'（リトライ中）
  - 最大リトライ到達後: status='failed'
  - 最終的なstatus='failed'
- **確認項目**:
  - [ ] run()開始時にstatus='in_progress'になったか
  - [ ] 最大リトライ到達後にstatus='failed'になったか
  - [ ] metadata.jsonファイルに正しく保存されたか

### 3.3 GitHub連携

#### IT-007: GitHub Issue投稿の統合テスト（成功ケース）

- **目的**: run()実行中のGitHub Issue投稿が正しく動作することを検証（成功ケース）
- **前提条件**:
  - テスト用のGitHubリポジトリが存在する
  - テスト用のIssue（例: #999）が存在する
  - GitHubClientが正常に動作する（または適切にモック化）
  - BasePhaseのサブクラス（ConcretePhase）が定義されている
- **テスト手順**:
  1. execute()が成功するように設定
  2. review()が'PASS'を返すように設定
  3. run()を実行
  4. GitHub Issueのコメントを確認
- **期待結果**:
  - フェーズ開始時に進捗投稿される（status='in_progress'）
  - review()実行後にレビュー結果が投稿される（result='PASS'）
  - フェーズ完了時に完了投稿される（status='completed'）
  - 合計3回のGitHub Issue投稿が実行される
- **確認項目**:
  - [ ] フェーズ開始時に進捗投稿されたか
  - [ ] レビュー結果が投稿されたか（result='PASS'）
  - [ ] フェーズ完了時に完了投稿されたか
  - [ ] GitHub Issueに正しいコメントが追加されたか

#### IT-008: GitHub Issue投稿の統合テスト（リトライケース）

- **目的**: リトライ実行時のGitHub Issue投稿が正しく動作することを検証
- **前提条件**:
  - テスト用のGitHubリポジトリが存在する
  - テスト用のIssue（例: #999）が存在する
  - GitHubClientが正常に動作する（または適切にモック化）
  - BasePhaseのサブクラス（ConcretePhase）が定義されている
- **テスト手順**:
  1. execute()が失敗するように設定
  2. 1回目のreview()が'FAIL'を返すように設定
  3. revise()が成功するように設定
  4. 2回目のreview()が'PASS'を返すように設定
  5. run()を実行
  6. GitHub Issueのコメントを確認
- **期待結果**:
  - フェーズ開始時に進捗投稿される（status='in_progress'）
  - attempt=2の前にreview()実行後、レビュー結果が投稿される（result='FAIL'）
  - revise()実行前に進捗投稿される（status='in_progress', details='レビュー不合格のため修正を実施します（1/2回目）。'）
  - 最終レビュー後にレビュー結果が投稿される（result='PASS'）
  - フェーズ完了時に完了投稿される（status='completed'）
  - 合計5回のGitHub Issue投稿が実行される
- **確認項目**:
  - [ ] フェーズ開始時に進捗投稿されたか
  - [ ] 1回目のレビュー結果が投稿されたか（result='FAIL'）
  - [ ] revise()実行前に進捗投稿されたか
  - [ ] 最終レビュー結果が投稿されたか（result='PASS'）
  - [ ] フェーズ完了時に完了投稿されたか
  - [ ] GitHub Issueに正しいコメントが追加されたか

#### IT-009: GitHub Issue投稿の統合テスト（最大リトライ到達）

- **目的**: 最大リトライ到達時のGitHub Issue投稿が正しく動作することを検証
- **前提条件**:
  - テスト用のGitHubリポジトリが存在する
  - テスト用のIssue（例: #999）が存在する
  - GitHubClientが正常に動作する（または適切にモック化）
  - BasePhaseのサブクラス（ConcretePhase）が定義されている
- **テスト手順**:
  1. execute()が失敗するように設定
  2. review()が常に'FAIL'を返すように設定
  3. revise()が常に失敗するように設定
  4. run()を実行
  5. GitHub Issueのコメントを確認
- **期待結果**:
  - フェーズ開始時に進捗投稿される（status='in_progress'）
  - attempt=2の前にreview()実行後、レビュー結果が投稿される（result='FAIL'）
  - revise()実行前に進捗投稿される（1回目）
  - attempt=3の前にreview()実行後、レビュー結果が投稿される（result='FAIL'）
  - revise()実行前に進捗投稿される（2回目）
  - 最大リトライ到達後に失敗投稿される（status='failed', details='最大リトライ回数(3)に到達しました'）
  - 合計6回のGitHub Issue投稿が実行される
- **確認項目**:
  - [ ] フェーズ開始時に進捗投稿されたか
  - [ ] 各attempt前にレビュー結果が投稿されたか
  - [ ] 各revise()実行前に進捗投稿されたか
  - [ ] 最大リトライ到達後に「最大リトライ回数(3)に到達しました」が投稿されたか
  - [ ] GitHub Issueに正しいコメントが追加されたか

### 3.4 Git連携

#### IT-010: Git commit & pushの統合テスト（成功ケース）

- **目的**: run()実行後のGit commit & pushが正しく動作することを検証（成功ケース）
- **前提条件**:
  - テスト用のGitリポジトリが存在する
  - GitManagerが正常に動作する
  - BasePhaseのサブクラス（ConcretePhase）が定義されている
- **テスト手順**:
  1. execute()が成功するように設定
  2. review()が'PASS'を返すように設定
  3. run()を実行
  4. Gitリポジトリの履歴を確認
- **期待結果**:
  - finally句で_auto_commit_and_push()が実行される
  - 引数:
    - final_status='completed'
    - review_result='PASS'
  - 成果物（output/）とログファイルがcommitされる
  - リモートリポジトリにpushされる
  - コミットメッセージに適切な情報が含まれる
- **確認項目**:
  - [ ] _auto_commit_and_push()が実行されたか
  - [ ] 成果物がcommitされたか
  - [ ] ログファイルがcommitされたか
  - [ ] リモートリポジトリにpushされたか
  - [ ] コミットメッセージが適切か

#### IT-011: Git commit & pushの統合テスト（失敗ケース）

- **目的**: run()失敗時でもGit commit & pushが実行されることを検証
- **前提条件**:
  - テスト用のGitリポジトリが存在する
  - GitManagerが正常に動作する
  - BasePhaseのサブクラス（ConcretePhase）が定義されている
- **テスト手順**:
  1. execute()が失敗するように設定
  2. review()が常に'FAIL'を返すように設定
  3. revise()が常に失敗するように設定
  4. run()を実行
  5. Gitリポジトリの履歴を確認
- **期待結果**:
  - finally句で_auto_commit_and_push()が実行される
  - 引数:
    - final_status='failed'
    - review_result=None（またはレビュー結果）
  - ログファイルがcommitされる（失敗時も記録）
  - リモートリポジトリにpushされる
  - コミットメッセージに失敗の旨が含まれる
- **確認項目**:
  - [ ] _auto_commit_and_push()が実行されたか（失敗時も）
  - [ ] ログファイルがcommitされたか
  - [ ] リモートリポジトリにpushされたか
  - [ ] コミットメッセージに失敗の旨が含まれるか

#### IT-012: Git commit & pushの統合テスト（例外発生時）

- **目的**: 例外発生時でもfinally句でGit commit & pushが実行されることを検証
- **前提条件**:
  - テスト用のGitリポジトリが存在する
  - GitManagerが正常に動作する
  - BasePhaseのサブクラス（ConcretePhase）が定義されている
- **テスト手順**:
  1. execute()がRuntimeErrorをスローするように設定
  2. run()を実行（例外をキャッチ）
  3. Gitリポジトリの履歴を確認
- **期待結果**:
  - 例外がスローされる
  - finally句で_auto_commit_and_push()が実行される
  - 引数:
    - final_status='failed'
    - review_result=None
  - ログファイルがcommitされる（エラーログ含む）
  - リモートリポジトリにpushされる
  - コミットメッセージに例外発生の旨が含まれる
- **確認項目**:
  - [ ] 例外がスローされたか
  - [ ] finally句で_auto_commit_and_push()が実行されたか
  - [ ] エラーログがcommitされたか
  - [ ] リモートリポジトリにpushされたか
  - [ ] コミットメッセージに例外発生の旨が含まれるか

### 3.5 全体フロー統合テスト

#### IT-013: エンドツーエンド統合テスト（正常フロー）

- **目的**: execute()成功→review()合格の正常フローがエンドツーエンドで動作することを検証
- **前提条件**:
  - テスト用のGitHubリポジトリが存在する
  - テスト用のIssue（例: #999）が存在する
  - テスト用のGitリポジトリが存在する
  - 全ての依存コンポーネントが正常に動作する
  - BasePhaseのサブクラス（ConcretePhase）が定義されている
- **テスト手順**:
  1. execute()が成功するように設定
  2. review()が'PASS'を返すように設定
  3. run()を実行
  4. 全ての統合ポイントを確認
- **期待結果**:
  - execute()が1回実行され、成功する
  - review()が1回実行され、'PASS'を返す
  - revise()は実行されない
  - run()がTrueを返す
  - 成果物が生成される
  - metadata.jsonが正しく更新される（status='completed', review_result='PASS', retry_count=0）
  - GitHub Issueに進捗とレビュー結果が投稿される
  - Gitにcommit & pushされる
  - ログファイルが生成される
- **確認項目**:
  - [ ] execute()が1回だけ実行されたか
  - [ ] review()が1回だけ実行されたか
  - [ ] revise()が実行されなかったか
  - [ ] run()がTrueを返したか
  - [ ] 成果物が生成されたか
  - [ ] metadata.jsonが正しく更新されたか
  - [ ] GitHub Issueに投稿されたか
  - [ ] Gitにcommit & pushされたか
  - [ ] ログファイルが生成されたか

#### IT-014: エンドツーエンド統合テスト（リトライ成功フロー）

- **目的**: execute()失敗→revise()成功→review()合格のリトライ成功フローがエンドツーエンドで動作することを検証
- **前提条件**:
  - テスト用のGitHubリポジトリが存在する
  - テスト用のIssue（例: #999）が存在する
  - テスト用のGitリポジトリが存在する
  - 全ての依存コンポーネントが正常に動作する
  - BasePhaseのサブクラス（ConcretePhase）が定義されている
- **テスト手順**:
  1. execute()が失敗するように設定
  2. 1回目のreview()が'FAIL'を返すように設定
  3. revise()が成功するように設定
  4. 2回目のreview()が'PASS'を返すように設定
  5. run()を実行
  6. 全ての統合ポイントを確認
- **期待結果**:
  - execute()が1回実行され、失敗する
  - `[ATTEMPT 1/3]`と`[ATTEMPT 2/3]`のログが出力される
  - 1回目のreview()が実行され、'FAIL'を返す
  - revise()が1回実行され、成功する
  - 2回目のreview()が実行され、'PASS'を返す
  - run()がTrueを返す
  - 成果物が生成される（revise()によって修正されたもの）
  - metadata.jsonが正しく更新される（status='completed', review_result='PASS', retry_count=1）
  - GitHub Issueに進捗、レビュー結果（2回）が投稿される
  - Gitにcommit & pushされる
  - ログファイルが生成される（連番付き: 001.log, 002.log）
- **確認項目**:
  - [ ] execute()が1回実行されたか
  - [ ] review()が2回実行されたか
  - [ ] revise()が1回実行されたか
  - [ ] run()がTrueを返したか
  - [ ] 成果物が生成されたか（修正版）
  - [ ] metadata.jsonのretry_countが1か
  - [ ] metadata.jsonのstatusが'completed'か
  - [ ] GitHub Issueに複数回投稿されたか
  - [ ] Gitにcommit & pushされたか
  - [ ] 連番付きログファイルが生成されたか

#### IT-015: エンドツーエンド統合テスト（最大リトライ到達フロー）

- **目的**: execute()失敗→revise()失敗（3回）→最大リトライ到達のフローがエンドツーエンドで動作することを検証
- **前提条件**:
  - テスト用のGitHubリポジトリが存在する
  - テスト用のIssue（例: #999）が存在する
  - テスト用のGitリポジトリが存在する
  - 全ての依存コンポーネントが正常に動作する
  - BasePhaseのサブクラス（ConcretePhase）が定義されている
- **テスト手順**:
  1. execute()が失敗するように設定
  2. review()が常に'FAIL'を返すように設定
  3. revise()が常に失敗するように設定
  4. run()を実行
  5. 最大リトライ回数に到達することを確認
  6. 全ての統合ポイントを確認
- **期待結果**:
  - execute()が1回実行され、失敗する
  - `[ATTEMPT 1/3]`, `[ATTEMPT 2/3]`, `[ATTEMPT 3/3]`のログが出力される
  - review()が2回実行され、常に'FAIL'を返す
  - revise()が2回実行され、常に失敗する
  - `[WARNING] Attempt 1 failed: ...`のログが出力される
  - `[WARNING] Attempt 2 failed: ...`のログが出力される
  - `[WARNING] Attempt 3 failed: ...`のログが出力される
  - run()がFalseを返す
  - 成果物は生成されない（またはエラー状態）
  - metadata.jsonが正しく更新される（status='failed', retry_count=2）
  - GitHub Issueに「最大リトライ回数(3)に到達しました」が投稿される
  - Gitにcommit & pushされる（失敗時も実行）
  - ログファイルが生成される（連番付き: 001.log, 002.log, 003.log）
- **確認項目**:
  - [ ] execute()が1回実行されたか
  - [ ] review()が2回実行されたか
  - [ ] revise()が2回実行されたか
  - [ ] 最大リトライ回数（3回）に到達したか
  - [ ] run()がFalseを返したか
  - [ ] metadata.jsonのstatusが'failed'か
  - [ ] metadata.jsonのretry_countが2か
  - [ ] GitHub Issueに「最大リトライ回数(3)に到達しました」が投稿されたか
  - [ ] Gitにcommit & pushされたか（失敗時も）
  - [ ] 連番付きログファイルが3つ生成されたか

---

## 4. テストデータ

### 4.1 正常系テストデータ

#### TD-001: execute()成功データ

```python
{
    'success': True,
    'output': 'test_output.md',
    'error': None
}
```

#### TD-002: review()合格データ

```python
{
    'result': 'PASS',
    'feedback': '',
    'suggestions': []
}
```

#### TD-003: review()条件付き合格データ

```python
{
    'result': 'PASS_WITH_SUGGESTIONS',
    'feedback': '全体的に良好ですが、以下の改善提案があります。',
    'suggestions': [
        'テストケースの網羅性を高める',
        'エッジケースを追加する'
    ]
}
```

### 4.2 異常系テストデータ

#### TD-004: execute()失敗データ

```python
{
    'success': False,
    'output': None,
    'error': 'Claude Agent SDK execution failed: Connection timeout'
}
```

#### TD-005: review()不合格データ

```python
{
    'result': 'FAIL',
    'feedback': '要件定義書の要件FR-001がカバーされていません。',
    'suggestions': [
        'FR-001のテストケースを追加する',
        '異常系のテストを追加する'
    ]
}
```

#### TD-006: revise()失敗データ

```python
{
    'success': False,
    'output': None,
    'error': 'Revision failed: Claude Agent SDK returned error'
}
```

### 4.3 境界値テストデータ

#### TD-007: 最大リトライ回数（MAX_RETRIES=3）

```python
MAX_RETRIES = 3
```

#### TD-008: retry_countの境界値

```python
# 初期値
retry_count = 0

# 最大値（revise()が2回実行された場合）
retry_count = 2
```

### 4.4 メタデータテストデータ

#### TD-009: 初期メタデータ

```json
{
  "issue_number": "999",
  "phases": {
    "requirements": {
      "status": null,
      "retry_count": 0,
      "review_result": null
    }
  }
}
```

#### TD-010: 成功完了後のメタデータ

```json
{
  "issue_number": "999",
  "phases": {
    "requirements": {
      "status": "completed",
      "retry_count": 0,
      "review_result": "PASS"
    }
  }
}
```

#### TD-011: リトライ成功後のメタデータ

```json
{
  "issue_number": "999",
  "phases": {
    "requirements": {
      "status": "completed",
      "retry_count": 1,
      "review_result": "PASS"
    }
  }
}
```

#### TD-012: 最大リトライ到達後のメタデータ

```json
{
  "issue_number": "999",
  "phases": {
    "requirements": {
      "status": "failed",
      "retry_count": 2,
      "review_result": "FAIL"
    }
  }
}
```

---

## 5. テスト環境要件

### 5.1 ローカル開発環境

- **OS**: Linux, macOS, Windows（WSL2推奨）
- **Python**: 3.8以上
- **必須ライブラリ**:
  - pytest: 7.0以上（テストフレームワーク）
  - pytest-mock: 3.6以上（モック機能）
  - pytest-cov: 3.0以上（カバレッジ計測）

### 5.2 CI/CD環境

- **CI/CDプラットフォーム**: GitHub Actions、Jenkins等
- **テスト実行環境**: Dockerコンテナ（Pythonイメージ）
- **並列実行**: 可能（Unitテストは並列、Integrationテストは直列推奨）

### 5.3 外部サービス

#### 5.3.1 GitHub API

- **環境**: テスト用のGitHubリポジトリとIssue
- **認証**: Personal Access Token（環境変数: `GITHUB_TOKEN`）
- **モック化**: 推奨（過度なAPI呼び出しを防ぐため）
- **モックライブラリ**: responses, pytest-httpx等

#### 5.3.2 Claude Agent SDK

- **環境**: Claude Code OAuth Token（環境変数: `CLAUDE_CODE_OAUTH_TOKEN`）
- **モック化**: 必須（コスト削減とテスト高速化のため）
- **モック方法**: execute_with_claude()メソッドのモック化

#### 5.3.3 Gitリポジトリ

- **環境**: テスト用のローカルGitリポジトリ
- **初期化**: pytest fixtureで自動作成
- **クリーンアップ**: テスト終了後に自動削除
- **モック化**: 不要（ローカルリポジトリを使用）

### 5.4 テストデータ準備

#### 5.4.1 Unitテスト

- **モック/スタブ**: pytest-mockを使用
- **フィクスチャ**: pytest fixtureで共通データを準備
- **テストデータファイル**: 不要（モックで十分）

#### 5.4.2 Integrationテスト

- **テスト用リポジトリ**: テンポラリディレクトリに作成
- **テスト用Issue**: モック化または実際のIssueを使用
- **テスト用メタデータ**: テンポラリファイルに作成
- **テスト用成果物**: テンポラリディレクトリに作成

---

## 6. 品質ゲート確認

本テストシナリオは以下の品質ゲート（Phase 3必須要件）を満たしています：

### ✅ Phase 2の戦略に沿ったテストシナリオである

- **確認**: Phase 2で決定されたテスト戦略は「UNIT_INTEGRATION」
- **対応**:
  - Unitテストシナリオ: 16ケース（UT-001～UT-016）
  - Integrationテストシナリオ: 15ケース（IT-001～IT-015）
- **判定**: ✅ 合格

### ✅ 主要な正常系がカバーされている

以下の主要な正常系がカバーされています：

1. **execute()成功→review()合格** (UT-001, IT-003, IT-013)
2. **execute()失敗→revise()成功→review()合格** (UT-002, UT-004, IT-001, IT-014)
3. **attempt>=2でreview()がPASSの場合の早期終了** (UT-005)
4. **メタデータの正しい更新** (UT-011, UT-012, IT-004, IT-005)
5. **GitHub Issue投稿** (UT-013, IT-007, IT-008)
6. **Git commit & push** (UT-015, IT-010)

**判定**: ✅ 合格

### ✅ 主要な異常系がカバーされている

以下の主要な異常系がカバーされています：

1. **execute()失敗→最大リトライ到達** (UT-003, IT-002, IT-015)
2. **revise()メソッド未実装** (UT-006)
3. **execute()が例外をスロー** (UT-007)
4. **revise()が例外をスロー** (UT-008)
5. **失敗時のGitHub Issue投稿** (UT-014, IT-009)
6. **失敗時のGit commit & push** (UT-016, IT-011)
7. **例外発生時のfinally句実行** (IT-012)

**判定**: ✅ 合格

### ✅ 期待結果が明確である

全てのテストケースにおいて、以下が明確に記述されています：

1. **目的**: テストで検証する内容
2. **前提条件**: テスト実行前の状態
3. **入力**: 関数への入力パラメータ（Unitテスト）またはテスト手順（Integrationテスト）
4. **期待結果**: 期待される出力・状態変化（具体的な値を記載）
5. **確認項目**: チェックリスト形式で検証ポイントを列挙（Integrationテスト）

**判定**: ✅ 合格

---

## 7. テスト実行計画

### 7.1 Unitテスト実行

```bash
# 全Unitテストを実行
pytest scripts/ai-workflow/tests/unit/phases/test_base_phase.py -v

# 特定のテストケースを実行
pytest scripts/ai-workflow/tests/unit/phases/test_base_phase.py::test_run_execute_failure_with_retry -v

# カバレッジ計測
pytest scripts/ai-workflow/tests/unit/phases/test_base_phase.py --cov=scripts/ai-workflow/phases/base_phase --cov-report=html
```

### 7.2 Integrationテスト実行

```bash
# 全Integrationテストを実行
pytest scripts/ai-workflow/tests/integration/test_retry_mechanism.py -v

# 特定のテストケースを実行
pytest scripts/ai-workflow/tests/integration/test_retry_mechanism.py::test_retry_mechanism_with_real_phase -v
```

### 7.3 CI/CD統合

```yaml
# .github/workflows/test.yml（例）
name: Test Retry Mechanism

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.8'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-mock pytest-cov
      - name: Run Unit Tests
        run: pytest scripts/ai-workflow/tests/unit/phases/test_base_phase.py -v
      - name: Run Integration Tests
        run: pytest scripts/ai-workflow/tests/integration/test_retry_mechanism.py -v
      - name: Upload Coverage
        uses: codecov/codecov-action@v3
```

---

## 8. まとめ

本テストシナリオは、Phase 2で決定された「UNIT_INTEGRATION」戦略に基づき、以下を提供します：

1. **Unitテスト**: 16のテストケースでリトライループの各分岐条件を詳細に検証
2. **Integrationテスト**: 15のテストケースで実際のPhaseクラス、メタデータ、GitHub、Git連携を統合的に検証
3. **テストデータ**: 正常系、異常系、境界値の具体的なテストデータを定義
4. **テスト環境**: ローカル、CI/CD、外部サービス連携の要件を明確化
5. **品質ゲート**: Phase 3の4つの必須要件をすべて満たすことを確認

これらのテストシナリオに基づいてテストコードを実装することで、execute()失敗時のリトライ機能修正が正しく動作することを保証できます。

---

**文書履歴**:
- 2025-10-10: 初版作成（Phase 3: Test Scenario）
- テスト戦略: UNIT_INTEGRATION（Phase 2設計書より）
- 品質ゲート: 全て合格 ✅
