# テストシナリオ - Issue #320

**Issue**: [FEATURE] AIワークフロー: 全フェーズ一括実行機能（--phase all）
**作成日**: 2025-10-12
**Phase**: Test Scenario (Phase 3)

---

## 0. テスト戦略サマリー

### Phase 2で決定されたテスト戦略

**テスト戦略**: UNIT_INTEGRATION

**判断根拠**（Phase 2設計書より）:
1. **ユニットテストの必要性**:
   - `execute_all_phases()`関数のロジック（フェーズ順次実行、エラーハンドリング、サマリー生成）を独立してテスト
   - モックを使用して、実際のフェーズ実行なしでロジックを検証
   - テスト実行時間を短縮（約1分以内）

2. **インテグレーションテストの必要性**:
   - 実際に全フェーズを実行し、エンドツーエンドの動作を確認
   - Claude API連携、GitHub API連携、Git操作等の統合を検証
   - 実行サマリーの正確性を確認

3. **BDDテスト不要の理由**:
   - エンドユーザー向けUIではなく、CLI開発者向け機能
   - ユーザーストーリーよりも技術的な正確性が重要

### テスト対象の範囲

#### 新規作成関数
- `execute_all_phases()`: 全フェーズ順次実行のメイン関数
- `_execute_single_phase()`: 個別フェーズ実行ヘルパー関数
- `_generate_success_summary()`: 成功サマリー生成関数
- `_generate_failure_summary()`: 失敗サマリー生成関数

#### 修正箇所
- `main.py`の`execute`コマンド: `--phase all`オプションの追加と分岐処理

#### 既存機能（リグレッションテスト対象）
- 個別フェーズ実行（`--phase requirements`等）
- 各フェーズクラスの`run()`メソッド
- メタデータ管理（`metadata.json`の更新）

### テストの目的

1. **機能的正確性**: 全フェーズが正しい順序で実行されること
2. **エラーハンドリング**: フェーズ失敗時に適切に停止し、エラー情報を返すこと
3. **進捗表示**: リアルタイムで進捗が表示されること
4. **サマリー生成**: 実行結果が正しく集計されること
5. **リグレッション防止**: 既存の個別フェーズ実行機能が引き続き動作すること
6. **統合動作**: Claude API、GitHub API、Git操作が正しく統合されること

---

## 1. ユニットテストシナリオ

### 1.1 `execute_all_phases()` 関数のテスト

#### TC-U-001: 全フェーズ成功時の正常系

**目的**: 全フェーズが成功した場合、正しい結果が返されることを検証

**前提条件**:
- Issue #320のワークフローが初期化されている
- `_execute_single_phase()`がモックされており、常に成功を返す

**入力**:
```python
issue = "320"
repo_root = Path("/tmp/test-repo")
metadata_manager = Mock(data={
    'issue_number': '320',
    'cost_tracking': {'total_cost_usd': 2.45},
    'phases': {
        'requirements': {'review_result': 'PASS'},
        'design': {'review_result': 'PASS_WITH_SUGGESTIONS'},
        'test_scenario': {'review_result': 'PASS'},
        'implementation': {'review_result': 'PASS'},
        'test_implementation': {'review_result': 'PASS'},
        'testing': {'review_result': 'PASS'},
        'documentation': {'review_result': 'PASS'},
        'report': {'review_result': 'PASS'}
    }
})
claude_client = Mock()
github_client = Mock()
```

**モック設定**:
```python
mock_execute_single_phase.return_value = {
    'success': True,
    'review_result': 'PASS',
    'error': None
}
```

**期待結果**:
```python
{
    'success': True,
    'completed_phases': [
        'requirements', 'design', 'test_scenario', 'implementation',
        'test_implementation', 'testing', 'documentation', 'report'
    ],
    'failed_phase': None,
    'error': None,
    'results': {
        'requirements': {'success': True, 'review_result': 'PASS', 'error': None},
        'design': {'success': True, 'review_result': 'PASS', 'error': None},
        # ... 他のフェーズ
    },
    'total_duration': <float>,  # 0-5秒程度
    'total_cost': 2.45
}
```

**検証項目**:
- [ ] `result['success']`が`True`
- [ ] `result['completed_phases']`に8つのフェーズが含まれる
- [ ] `result['failed_phase']`が`None`
- [ ] `result['error']`が`None`
- [ ] `result['total_cost']`が`2.45`
- [ ] `_execute_single_phase()`が8回呼ばれる

---

#### TC-U-002: 途中フェーズ失敗時の異常系

**目的**: 途中のフェーズが失敗した場合、それ以降のフェーズが実行されず、失敗情報が正しく返されることを検証

**前提条件**:
- Issue #320のワークフローが初期化されている
- `_execute_single_phase()`がモックされており、4回目（implementation）で失敗を返す

**入力**: TC-U-001と同じ

**モック設定**:
```python
def mock_execute_side_effect(phase, *args, **kwargs):
    if phase == 'implementation':
        return {'success': False, 'review_result': 'FAIL', 'error': 'Phase execution failed'}
    return {'success': True, 'review_result': 'PASS', 'error': None}

mock_execute_single_phase.side_effect = mock_execute_side_effect
```

**期待結果**:
```python
{
    'success': False,
    'completed_phases': ['requirements', 'design', 'test_scenario', 'implementation'],
    'failed_phase': 'implementation',
    'error': 'Phase execution failed',
    'results': {
        'requirements': {'success': True, 'review_result': 'PASS', 'error': None},
        'design': {'success': True, 'review_result': 'PASS', 'error': None},
        'test_scenario': {'success': True, 'review_result': 'PASS', 'error': None},
        'implementation': {'success': False, 'review_result': 'FAIL', 'error': 'Phase execution failed'}
    },
    'total_duration': <float>
}
```

**検証項目**:
- [ ] `result['success']`が`False`
- [ ] `result['completed_phases']`に4つのフェーズが含まれる
- [ ] `result['failed_phase']`が`'implementation'`
- [ ] `result['error']`が`'Phase execution failed'`
- [ ] `_execute_single_phase()`が4回のみ呼ばれる（5回目以降は実行されない）

---

#### TC-U-003: 最初のフェーズ失敗時の異常系

**目的**: 最初のフェーズ（requirements）が失敗した場合、即座に停止することを検証

**前提条件**: TC-U-002と同じ

**入力**: TC-U-001と同じ

**モック設定**:
```python
def mock_execute_side_effect(phase, *args, **kwargs):
    if phase == 'requirements':
        return {'success': False, 'review_result': 'FAIL', 'error': 'Requirements phase failed'}
    return {'success': True, 'review_result': 'PASS', 'error': None}

mock_execute_single_phase.side_effect = mock_execute_side_effect
```

**期待結果**:
```python
{
    'success': False,
    'completed_phases': ['requirements'],
    'failed_phase': 'requirements',
    'error': 'Requirements phase failed',
    'results': {
        'requirements': {'success': False, 'review_result': 'FAIL', 'error': 'Requirements phase failed'}
    },
    'total_duration': <float>
}
```

**検証項目**:
- [ ] `result['success']`が`False`
- [ ] `result['completed_phases']`に1つのフェーズのみが含まれる
- [ ] `result['failed_phase']`が`'requirements'`
- [ ] `_execute_single_phase()`が1回のみ呼ばれる

---

#### TC-U-004: 例外発生時の異常系

**目的**: フェーズ実行中に予期しない例外が発生した場合、適切にキャッチされることを検証

**前提条件**: TC-U-002と同じ

**入力**: TC-U-001と同じ

**モック設定**:
```python
def mock_execute_side_effect(phase, *args, **kwargs):
    if phase == 'design':
        raise RuntimeError("Unexpected error in design phase")
    return {'success': True, 'review_result': 'PASS', 'error': None}

mock_execute_single_phase.side_effect = mock_execute_side_effect
```

**期待結果**:
```python
{
    'success': False,
    'completed_phases': ['requirements', 'design'],
    'failed_phase': 'design',
    'error': 'Unexpected error in design phase',
    'results': {
        'requirements': {'success': True, 'review_result': 'PASS', 'error': None},
        'design': {'success': False, 'error': 'Unexpected error in design phase'}
    },
    'total_duration': <float>
}
```

**検証項目**:
- [ ] `result['success']`が`False`
- [ ] `result['failed_phase']`が`'design'`
- [ ] `result['error']`に例外メッセージが含まれる
- [ ] 例外がキャッチされ、プログラムがクラッシュしない

---

#### TC-U-005: 空のフェーズリストの境界値テスト

**目的**: フェーズリストが空の場合の動作を検証（実装上は発生しないが、堅牢性確認）

**前提条件**: フェーズリストを空に設定

**入力**: TC-U-001と同じ

**実装修正**:
```python
# テスト用にフェーズリストを空にする
phases = []
```

**期待結果**:
```python
{
    'success': True,
    'completed_phases': [],
    'failed_phase': None,
    'error': None,
    'results': {},
    'total_duration': <float>,
    'total_cost': 2.45
}
```

**検証項目**:
- [ ] `result['success']`が`True`
- [ ] `result['completed_phases']`が空リスト
- [ ] `_execute_single_phase()`が呼ばれない

---

### 1.2 `_execute_single_phase()` 関数のテスト

#### TC-U-101: 個別フェーズ実行の正常系

**目的**: 個別フェーズが正常に実行され、正しい結果が返されることを検証

**前提条件**:
- Issue #320のワークフローが初期化されている
- `BasePhase.run()`がモックされており、成功を返す

**入力**:
```python
phase = "requirements"
issue = "320"
repo_root = Path("/tmp/test-repo")
metadata_manager = Mock(data={
    'phases': {
        'requirements': {'review_result': 'PASS'}
    }
})
claude_client = Mock()
github_client = Mock()
```

**モック設定**:
```python
mock_phase_instance = Mock()
mock_phase_instance.run.return_value = True
mock_phase_class.return_value = mock_phase_instance
```

**期待結果**:
```python
{
    'success': True,
    'review_result': 'PASS',
    'error': None
}
```

**検証項目**:
- [ ] `result['success']`が`True`
- [ ] `result['review_result']`が`'PASS'`
- [ ] フェーズインスタンスが正しく生成される
- [ ] `phase_instance.run()`が1回呼ばれる

---

#### TC-U-102: 個別フェーズ実行の異常系（run()がFalseを返す）

**目的**: フェーズの`run()`メソッドが`False`を返した場合、失敗として扱われることを検証

**前提条件**: TC-U-101と同じ

**入力**: TC-U-101と同じ

**モック設定**:
```python
mock_phase_instance = Mock()
mock_phase_instance.run.return_value = False
mock_phase_class.return_value = mock_phase_instance
```

**期待結果**:
```python
{
    'success': False,
    'review_result': None,
    'error': 'Phase execution failed'
}
```

**検証項目**:
- [ ] `result['success']`が`False`
- [ ] `result['error']`が`'Phase execution failed'`

---

#### TC-U-103: 不正なフェーズ名の異常系

**目的**: 存在しないフェーズ名が指定された場合、エラーが返されることを検証

**前提条件**: TC-U-101と同じ

**入力**:
```python
phase = "invalid_phase"
# 他の引数はTC-U-101と同じ
```

**期待結果**:
```python
{
    'success': False,
    'error': 'Unknown phase: invalid_phase'
}
```

**検証項目**:
- [ ] `result['success']`が`False`
- [ ] `result['error']`に`'Unknown phase'`が含まれる
- [ ] フェーズインスタンスが生成されない

---

### 1.3 `_generate_success_summary()` 関数のテスト

#### TC-U-201: 成功サマリー生成の正常系

**目的**: 全フェーズ成功時のサマリーが正しく生成されることを検証

**前提条件**: 全フェーズが成功している

**入力**:
```python
phases = ['requirements', 'design', 'test_scenario', 'implementation',
          'test_implementation', 'testing', 'documentation', 'report']
results = {
    'requirements': {'success': True, 'review_result': 'PASS'},
    'design': {'success': True, 'review_result': 'PASS_WITH_SUGGESTIONS'},
    'test_scenario': {'success': True, 'review_result': 'PASS'},
    'implementation': {'success': True, 'review_result': 'PASS'},
    'test_implementation': {'success': True, 'review_result': 'PASS'},
    'testing': {'success': True, 'review_result': 'PASS'},
    'documentation': {'success': True, 'review_result': 'PASS'},
    'report': {'success': True, 'review_result': 'PASS'}
}
start_time = time.time() - 2732.5  # 45分32秒前
metadata_manager = Mock(data={
    'issue_number': '320',
    'cost_tracking': {'total_cost_usd': 2.45}
})
```

**期待結果**:
```python
{
    'success': True,
    'completed_phases': ['requirements', 'design', 'test_scenario', 'implementation',
                         'test_implementation', 'testing', 'documentation', 'report'],
    'failed_phase': None,
    'error': None,
    'results': results,
    'total_duration': 2732.5,  # 約45分32秒
    'total_cost': 2.45
}
```

**検証項目**:
- [ ] `result['success']`が`True`
- [ ] `result['completed_phases']`に8つのフェーズが含まれる
- [ ] `result['total_duration']`が約2732.5秒
- [ ] `result['total_cost']`が`2.45`
- [ ] 標準出力にサマリーが表示される（モックで確認）

---

#### TC-U-202: サマリー生成時の総実行時間計算

**目的**: 総実行時間が正しく計算されることを検証

**前提条件**: TC-U-201と同じ

**入力**:
```python
# 異なる実行時間でテスト
start_time_cases = [
    (time.time() - 60, 60),        # 1分
    (time.time() - 3600, 3600),    # 1時間
    (time.time() - 300, 300),      # 5分
]
```

**期待結果**: 各ケースで正しい実行時間が計算される

**検証項目**:
- [ ] `result['total_duration']`が期待値と一致（±1秒の誤差許容）

---

### 1.4 `_generate_failure_summary()` 関数のテスト

#### TC-U-301: 失敗サマリー生成の正常系

**目的**: フェーズ失敗時のサマリーが正しく生成されることを検証

**前提条件**: implementationフェーズで失敗している

**入力**:
```python
completed_phases = ['requirements', 'design', 'test_scenario', 'implementation']
failed_phase = 'implementation'
error = 'Phase execution failed'
results = {
    'requirements': {'success': True, 'review_result': 'PASS'},
    'design': {'success': True, 'review_result': 'PASS'},
    'test_scenario': {'success': True, 'review_result': 'PASS'},
    'implementation': {'success': False, 'review_result': 'FAIL', 'error': 'Phase execution failed'}
}
start_time = time.time() - 1823.2  # 約30分前
```

**期待結果**:
```python
{
    'success': False,
    'completed_phases': ['requirements', 'design', 'test_scenario', 'implementation'],
    'failed_phase': 'implementation',
    'error': 'Phase execution failed',
    'results': results,
    'total_duration': 1823.2
}
```

**検証項目**:
- [ ] `result['success']`が`False`
- [ ] `result['failed_phase']`が`'implementation'`
- [ ] `result['error']`が`'Phase execution failed'`
- [ ] 標準出力に失敗サマリーが表示される

---

#### TC-U-302: スキップされたフェーズの表示

**目的**: 失敗後にスキップされたフェーズが正しく表示されることを検証

**前提条件**: TC-U-301と同じ

**入力**: TC-U-301と同じ

**期待される標準出力**:
```
=============================================================
Execution Summary - FAILED
=============================================================

Total Phases: 4
✓ Completed: 3
✗ Failed: 1
⊘ Skipped: 4

Phase Results:
  1. requirements          ✓ PASS
  2. design                ✓ PASS
  3. test_scenario         ✓ PASS
  4. implementation        ✗ FAIL
  5. test_implementation   ⊘ SKIPPED
  6. testing               ⊘ SKIPPED
  7. documentation         ⊘ SKIPPED
  8. report                ⊘ SKIPPED

Failed Phase: implementation
Error: Phase execution failed
...
```

**検証項目**:
- [ ] 完了したフェーズ数が正しい（3つ）
- [ ] 失敗したフェーズ数が正しい（1つ）
- [ ] スキップされたフェーズ数が正しい（4つ）
- [ ] 各フェーズのステータス（✓/✗/⊘）が正しい

---

### 1.5 `main.py`の`execute`コマンドのテスト

#### TC-U-401: `--phase all`オプションの分岐処理

**目的**: `--phase all`が指定された場合、`execute_all_phases()`が呼ばれることを検証

**前提条件**:
- Issue #320のワークフローが初期化されている
- 環境変数が設定されている

**入力**:
```python
# CLIコマンドとして実行
phase = "all"
issue = "320"
```

**モック設定**:
```python
mock_execute_all_phases = Mock(return_value={
    'success': True,
    'completed_phases': ['requirements', 'design', 'test_scenario', 'implementation',
                         'test_implementation', 'testing', 'documentation', 'report']
})
```

**期待結果**:
- `execute_all_phases()`が1回呼ばれる
- 終了コードが0（成功）

**検証項目**:
- [ ] `execute_all_phases()`が正しい引数で呼ばれる
- [ ] `sys.exit(0)`が呼ばれる

---

#### TC-U-402: `--phase all`失敗時の終了コード

**目的**: 全フェーズ実行が失敗した場合、終了コードが1になることを検証

**前提条件**: TC-U-401と同じ

**入力**: TC-U-401と同じ

**モック設定**:
```python
mock_execute_all_phases = Mock(return_value={
    'success': False,
    'failed_phase': 'implementation',
    'error': 'Phase execution failed'
})
```

**期待結果**:
- 終了コードが1（失敗）
- エラーメッセージが標準出力に表示される

**検証項目**:
- [ ] `sys.exit(1)`が呼ばれる
- [ ] エラーメッセージに失敗したフェーズ名が含まれる

---

#### TC-U-403: 個別フェーズ実行のリグレッションテスト

**目的**: 既存の個別フェーズ実行機能が引き続き動作することを検証

**前提条件**: Issue #320のワークフローが初期化されている

**入力**:
```python
phase = "requirements"
issue = "320"
```

**期待結果**:
- `execute_all_phases()`が呼ばれない
- 既存のフェーズ実行ロジックが実行される

**検証項目**:
- [ ] `execute_all_phases()`が呼ばれない
- [ ] フェーズインスタンスが生成される
- [ ] `phase_instance.run()`が呼ばれる

---

## 2. インテグレーション/E2Eテストシナリオ

### 2.1 全フェーズ実行のE2Eテスト

#### TC-E-001: 全フェーズ実行の正常系（完全統合テスト）

**目的**: 実際に全フェーズを実行し、エンドツーエンドで正常に動作することを検証

**前提条件**:
- テスト用Issueが存在する（例: Issue #999）
- 環境変数が設定されている（`GITHUB_TOKEN`, `CLAUDE_CODE_OAUTH_TOKEN`）
- リポジトリがクリーンな状態
- テスト用ブランチが作成されている

**テスト手順**:

1. **ワークフロー初期化**:
   ```bash
   python main.py init --issue-url https://github.com/tielec/infrastructure-as-code/issues/999
   ```
   - 確認: `.ai-workflow/issue-999/metadata.json`が作成される

2. **全フェーズ実行**:
   ```bash
   python main.py execute --phase all --issue 999
   ```
   - 確認: 各フェーズが順番に実行される
   - 確認: 進捗表示が正しく表示される

3. **実行結果確認**:
   - 標準出力に実行サマリーが表示される
   - 終了コードが0

4. **メタデータ確認**:
   ```bash
   cat .ai-workflow/issue-999/metadata.json
   ```
   - 確認: 全フェーズのステータスが`completed`
   - 確認: 各フェーズの`review_result`が記録されている

5. **出力ファイル確認**:
   ```bash
   ls -la .ai-workflow/issue-999/
   ```
   - 確認: 各フェーズのディレクトリが存在する
   - 確認: 各フェーズの出力ファイルが生成されている

6. **GitHub確認**:
   - 確認: Issue #999に進捗コメントが投稿されている
   - 確認: 各フェーズのレビュー結果が投稿されている

7. **Git確認**:
   ```bash
   git log --oneline | head -n 10
   ```
   - 確認: 各フェーズのコミットが作成されている
   - 確認: コミットメッセージに`[ai-workflow]`プレフィックスが含まれる

**期待結果**:
- 全フェーズが成功（requirements → design → test_scenario → implementation → test_implementation → testing → documentation → report）
- 実行サマリーに以下が表示される:
  - Total Phases: 8
  - ✓ Completed: 8
  - ✗ Failed: 0
  - 各フェーズの`review_result`（PASS/PASS_WITH_SUGGESTIONS）
  - Total Execution Time: 30-60分
  - Total Cost: $2-5 USD

**検証項目**:
- [ ] 全フェーズが正しい順序で実行される
- [ ] 各フェーズの出力ファイルが生成される
- [ ] メタデータが正しく更新される
- [ ] GitHub Issueに進捗コメントが投稿される
- [ ] Gitコミットが各フェーズで作成される
- [ ] 実行サマリーが表示される
- [ ] 終了コードが0

**実行時間**: 30-60分

**備考**: このテストは時間がかかるため、CI環境では`@pytest.mark.slow`でマークし、必要な場合のみ実行する。

---

#### TC-E-002: 途中フェーズ失敗時のE2Eテスト

**目的**: 途中のフェーズが失敗した場合、それ以降のフェーズが実行されず、適切にエラーハンドリングされることを検証

**前提条件**: TC-E-001と同じ

**テスト手順**:

1. **ワークフロー初期化**: TC-E-001と同じ

2. **意図的にフェーズを失敗させる**:
   - 方法1: テスト用の不正なIssueを使用（実装が困難な要件）
   - 方法2: モックを使用して特定フェーズで失敗させる（推奨）

3. **全フェーズ実行**:
   ```bash
   python main.py execute --phase all --issue 999
   ```

4. **実行結果確認**: 失敗時のサマリーが表示される

5. **メタデータ確認**: 失敗したフェーズまでのステータスが記録されている

6. **GitHub確認**: 失敗情報がIssueに投稿されている

**期待結果**:
- 失敗したフェーズで停止
- それ以降のフェーズは実行されない
- 実行サマリーに以下が表示される:
  - Total Phases: N（失敗したフェーズまでの数）
  - ✓ Completed: N-1
  - ✗ Failed: 1
  - ⊘ Skipped: 8-N
  - Failed Phase: {phase_name}
  - Error: {error_message}

**検証項目**:
- [ ] 失敗したフェーズで停止する
- [ ] それ以降のフェーズが実行されない
- [ ] 失敗サマリーが表示される
- [ ] 終了コードが1
- [ ] GitHub Issueに失敗情報が投稿される
- [ ] メタデータに失敗情報が記録される

**実行時間**: 15-30分

---

### 2.2 統合テスト（コンポーネント間連携）

#### TC-I-001: Claude API連携テスト

**目的**: 全フェーズ実行中にClaude APIが正しく呼び出されることを検証

**前提条件**: TC-E-001と同じ

**テスト手順**:
1. Claude APIクライアントをモニタリング（ログ出力等）
2. 全フェーズを実行
3. API呼び出しログを確認

**期待結果**:
- 各フェーズで少なくとも1回Claude APIが呼び出される
- API呼び出しがタイムアウトしない
- レート制限エラーが発生しない

**検証項目**:
- [ ] Claude APIが正常に呼び出される
- [ ] トークン使用量が記録される
- [ ] コストが正しく計算される

---

#### TC-I-002: GitHub API連携テスト

**目的**: 全フェーズ実行中にGitHub APIが正しく呼び出され、進捗コメントが投稿されることを検証

**前提条件**: TC-E-001と同じ

**テスト手順**:
1. 全フェーズを実行
2. GitHub Issue画面を確認

**期待結果**:
- 各フェーズの開始・完了時にコメントが投稿される
- レビュー結果がコメントに含まれる

**検証項目**:
- [ ] 進捗コメントが投稿される
- [ ] レビュー結果が投稿される
- [ ] GitHub API認証が正常に動作する

---

#### TC-I-003: Git操作統合テスト

**目的**: 全フェーズ実行中にGit操作（commit, push）が正しく実行されることを検証

**前提条件**: TC-E-001と同じ

**テスト手順**:
1. 全フェーズを実行
2. Gitログを確認

**期待結果**:
- 各フェーズでコミットが作成される
- コミットがリモートにプッシュされる

**検証項目**:
- [ ] 各フェーズでコミットが作成される
- [ ] コミットメッセージに`[ai-workflow]`プレフィックスが含まれる
- [ ] リモートリポジトリにプッシュされる

---

#### TC-I-004: メタデータ管理統合テスト

**目的**: 全フェーズ実行中にメタデータが正しく更新されることを検証

**前提条件**: TC-E-001と同じ

**テスト手順**:
1. 全フェーズを実行
2. 各フェーズ完了後に`metadata.json`を確認

**期待結果**:
- 各フェーズのステータスが逐次更新される
- トークン使用量・コストが累積される

**検証項目**:
- [ ] フェーズステータスが正しく更新される
- [ ] レビュー結果が記録される
- [ ] トークン使用量が累積される
- [ ] コストが累積される

---

### 2.3 パフォーマンステスト

#### TC-P-001: 実行時間オーバーヘッドテスト

**目的**: 全フェーズ一括実行のオーバーヘッドが5%以内であることを検証（NFR-01）

**前提条件**: TC-E-001と同じ

**テスト手順**:

1. **個別フェーズ実行の総実行時間測定**:
   ```bash
   time python main.py execute --phase requirements --issue 999
   time python main.py execute --phase design --issue 999
   # ... 全フェーズを個別に実行
   ```
   - 各フェーズの実行時間を記録
   - 総実行時間を計算

2. **全フェーズ一括実行の実行時間測定**:
   ```bash
   time python main.py execute --phase all --issue 1000
   ```
   - 総実行時間を記録

3. **オーバーヘッド計算**:
   ```
   オーバーヘッド = (一括実行時間 - 個別実行の総時間) / 個別実行の総時間 × 100
   ```

**期待結果**:
- オーバーヘッドが5%以内

**検証項目**:
- [ ] オーバーヘッドが5%以内
- [ ] 実行時間が個別実行と比較して大幅に増加していない

---

## 3. テストデータ

### 3.1 モック用テストデータ

#### メタデータ（metadata.json）

```json
{
  "issue_number": "320",
  "issue_title": "[FEATURE] AIワークフロー: 全フェーズ一括実行機能（--phase all）",
  "issue_url": "https://github.com/tielec/infrastructure-as-code/issues/320",
  "branch_name": "ai-workflow/issue-320",
  "status": "in_progress",
  "phases": {
    "requirements": {
      "status": "completed",
      "review_result": "PASS",
      "started_at": "2025-10-12T10:00:00Z",
      "completed_at": "2025-10-12T10:15:00Z"
    },
    "design": {
      "status": "completed",
      "review_result": "PASS_WITH_SUGGESTIONS",
      "started_at": "2025-10-12T10:15:00Z",
      "completed_at": "2025-10-12T10:35:00Z"
    },
    "test_scenario": {
      "status": "completed",
      "review_result": "PASS",
      "started_at": "2025-10-12T10:35:00Z",
      "completed_at": "2025-10-12T10:50:00Z"
    },
    "implementation": {
      "status": "completed",
      "review_result": "PASS",
      "started_at": "2025-10-12T10:50:00Z",
      "completed_at": "2025-10-12T11:30:00Z"
    },
    "test_implementation": {
      "status": "completed",
      "review_result": "PASS",
      "started_at": "2025-10-12T11:30:00Z",
      "completed_at": "2025-10-12T12:00:00Z"
    },
    "testing": {
      "status": "completed",
      "review_result": "PASS",
      "started_at": "2025-10-12T12:00:00Z",
      "completed_at": "2025-10-12T12:15:00Z"
    },
    "documentation": {
      "status": "completed",
      "review_result": "PASS",
      "started_at": "2025-10-12T12:15:00Z",
      "completed_at": "2025-10-12T12:30:00Z"
    },
    "report": {
      "status": "completed",
      "review_result": "PASS",
      "started_at": "2025-10-12T12:30:00Z",
      "completed_at": "2025-10-12T12:45:00Z"
    }
  },
  "cost_tracking": {
    "total_tokens": 150000,
    "total_cost_usd": 2.45
  }
}
```

#### フェーズ実行結果（正常系）

```python
{
    'success': True,
    'review_result': 'PASS',
    'error': None
}
```

#### フェーズ実行結果（異常系）

```python
{
    'success': False,
    'review_result': 'FAIL',
    'error': 'Phase execution failed due to API timeout'
}
```

### 3.2 E2E用テストデータ

#### テスト用Issue

- **Issue番号**: #999
- **タイトル**: [TEST] テスト用Issue
- **本文**: 簡単な機能実装のテスト（Hello Worldレベル）

#### 環境変数

```bash
export GITHUB_TOKEN="ghp_test_token_xxx"
export CLAUDE_CODE_OAUTH_TOKEN="test_oauth_token_xxx"
export GITHUB_REPOSITORY="tielec/infrastructure-as-code"
```

---

## 4. テスト環境要件

### 4.1 ユニットテスト環境

- **OS**: Linux（Amazon Linux 2023）
- **Python**: 3.11以上
- **必要なライブラリ**:
  - `pytest`: 7.0以上
  - `pytest-mock`: 3.10以上
  - `unittest.mock`: 標準ライブラリ
- **実行場所**: ローカル環境、CI環境
- **実行時間**: 約1分以内

### 4.2 E2E/統合テスト環境

- **OS**: Linux（Amazon Linux 2023）
- **Python**: 3.11以上
- **必要な環境変数**:
  - `GITHUB_TOKEN`: GitHub API認証トークン
  - `CLAUDE_CODE_OAUTH_TOKEN`: Claude API認証トークン
  - `GITHUB_REPOSITORY`: テスト用リポジトリ
- **必要な外部サービス**:
  - GitHub API（Issue作成・コメント投稿権限）
  - Claude API（claude-sonnet-4-5-20250929モデルへのアクセス）
  - Gitリポジトリ（push権限）
- **実行場所**: CI環境（Jenkins等）
- **実行時間**: 30-60分
- **実行頻度**: リリース前のみ（`@pytest.mark.slow`でマーク）

### 4.3 モック/スタブ要件

#### ユニットテストでモックする対象

- `_execute_single_phase()`: フェーズ実行をモック
- `BasePhase.run()`: フェーズの`run()`メソッドをモック
- `ClaudeAgentClient`: Claude API呼び出しをモック
- `GitHubClient`: GitHub API呼び出しをモック
- `time.time()`: 実行時間計算のため固定値を返す
- `click.echo()`: 標準出力をキャプチャ

#### E2E/統合テストでモックしない対象

- Claude API: 実際に呼び出す
- GitHub API: 実際に呼び出す
- Git操作: 実際に実行する
- ファイルシステム: 実際に読み書きする

---

## 5. テスト実行手順

### 5.1 ユニットテストの実行

```bash
# すべてのユニットテストを実行
cd /tmp/jenkins-26e41fa0/workspace/AI_Workflow/ai_workflow_orchestrator
pytest scripts/ai-workflow/tests/unit/test_main.py -v

# 特定のテストケースのみ実行
pytest scripts/ai-workflow/tests/unit/test_main.py::test_execute_all_phases_success -v

# カバレッジ測定付き実行
pytest scripts/ai-workflow/tests/unit/test_main.py --cov=scripts/ai-workflow/main --cov-report=html
```

### 5.2 E2E/統合テストの実行

```bash
# E2Eテストを実行（時間がかかる）
pytest scripts/ai-workflow/tests/e2e/test_phase_all.py -v -s

# スローテストのみ実行
pytest -m slow -v

# E2Eテストをスキップ
pytest -m "not slow" -v
```

### 5.3 すべてのテストを実行

```bash
# すべてのテストを実行
pytest scripts/ai-workflow/tests/ -v

# カバレッジ測定付き
pytest scripts/ai-workflow/tests/ --cov=scripts/ai-workflow --cov-report=html
```

---

## 6. テストカバレッジ目標

### 6.1 カバレッジ目標

- **ユニットテスト**: 80%以上（Phase 5の品質ゲート）
- **統合テスト**: 主要なユースケースをカバー

### 6.2 カバレッジ対象

- `execute_all_phases()`: 100%
- `_execute_single_phase()`: 100%
- `_generate_success_summary()`: 100%
- `_generate_failure_summary()`: 100%
- `execute`コマンドの分岐処理: 100%

---

## 品質ゲート（Phase 3）

本テストシナリオは、以下の品質ゲートを満たしています：

- [x] **Phase 2の戦略に沿ったテストシナリオである**: UNIT_INTEGRATIONに従い、ユニットテストと統合テストのシナリオを作成
- [x] **主要な正常系がカバーされている**:
  - TC-U-001: 全フェーズ成功時の正常系
  - TC-E-001: 全フェーズ実行のE2E正常系
- [x] **主要な異常系がカバーされている**:
  - TC-U-002: 途中フェーズ失敗時の異常系
  - TC-U-003: 最初のフェーズ失敗時の異常系
  - TC-U-004: 例外発生時の異常系
  - TC-E-002: 途中フェーズ失敗時のE2E異常系
- [x] **期待結果が明確である**: すべてのテストケースで期待結果と検証項目を明記

---

## 付録A: テストケース一覧（サマリー）

### ユニットテスト（20ケース）

| ID | テストケース名 | カテゴリ | 優先度 |
|----|------------|---------|-------|
| TC-U-001 | 全フェーズ成功時の正常系 | execute_all_phases() | 高 |
| TC-U-002 | 途中フェーズ失敗時の異常系 | execute_all_phases() | 高 |
| TC-U-003 | 最初のフェーズ失敗時の異常系 | execute_all_phases() | 高 |
| TC-U-004 | 例外発生時の異常系 | execute_all_phases() | 高 |
| TC-U-005 | 空のフェーズリストの境界値テスト | execute_all_phases() | 低 |
| TC-U-101 | 個別フェーズ実行の正常系 | _execute_single_phase() | 高 |
| TC-U-102 | 個別フェーズ実行の異常系 | _execute_single_phase() | 高 |
| TC-U-103 | 不正なフェーズ名の異常系 | _execute_single_phase() | 中 |
| TC-U-201 | 成功サマリー生成の正常系 | _generate_success_summary() | 高 |
| TC-U-202 | サマリー生成時の総実行時間計算 | _generate_success_summary() | 中 |
| TC-U-301 | 失敗サマリー生成の正常系 | _generate_failure_summary() | 高 |
| TC-U-302 | スキップされたフェーズの表示 | _generate_failure_summary() | 中 |
| TC-U-401 | `--phase all`オプションの分岐処理 | executeコマンド | 高 |
| TC-U-402 | `--phase all`失敗時の終了コード | executeコマンド | 高 |
| TC-U-403 | 個別フェーズ実行のリグレッションテスト | executeコマンド | 高 |

### E2E/統合テスト（7ケース）

| ID | テストケース名 | カテゴリ | 優先度 | 実行時間 |
|----|------------|---------|-------|---------|
| TC-E-001 | 全フェーズ実行の正常系 | E2E | 高 | 30-60分 |
| TC-E-002 | 途中フェーズ失敗時のE2E | E2E | 高 | 15-30分 |
| TC-I-001 | Claude API連携テスト | 統合 | 中 | 15分 |
| TC-I-002 | GitHub API連携テスト | 統合 | 中 | 10分 |
| TC-I-003 | Git操作統合テスト | 統合 | 中 | 10分 |
| TC-I-004 | メタデータ管理統合テスト | 統合 | 中 | 10分 |
| TC-P-001 | 実行時間オーバーヘッドテスト | パフォーマンス | 低 | 60分 |

**合計**: 22テストケース

---

## 付録B: テスト実行計画

### Phase 5（テスト実装）での実行順序

1. **Day 1**: ユニットテスト実装（TC-U-001〜TC-U-005）
2. **Day 1**: ユニットテスト実装（TC-U-101〜TC-U-103）
3. **Day 2**: ユニットテスト実装（TC-U-201〜TC-U-302）
4. **Day 2**: ユニットテスト実装（TC-U-401〜TC-U-403）
5. **Day 3**: E2E/統合テスト実装（TC-E-001〜TC-I-004）
6. **Day 3**: すべてのテスト実行とカバレッジ確認

---

**テストシナリオ作成完了**
