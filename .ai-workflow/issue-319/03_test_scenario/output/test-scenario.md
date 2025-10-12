# テストシナリオ: Issue #319

## 📋 プロジェクト情報

- **Issue番号**: #319
- **タイトル**: [FEATURE] AIワークフロー: フェーズ依存関係の柔軟化と選択的実行機能
- **URL**: https://github.com/tielec/infrastructure-as-code/issues/319
- **作成日**: 2025-10-12

---

## 0. Planning Document・Requirements・Designの確認

### Planning Phase (Phase 0)

- **実装戦略**: EXTEND - 既存ワークフローエンジンの拡張
- **テスト戦略**: **UNIT_INTEGRATION**
- **見積もり工数**: 10~14時間

### Requirements Phase (Phase 1)

要件定義書において、以下の7つの機能要件が定義されています：

1. **FR-001**: フェーズ依存関係の定義
2. **FR-002**: 依存関係チェック機能
3. **FR-003**: 依存関係チェックのスキップ機能
4. **FR-004**: 依存関係違反の警告表示
5. **FR-005**: 外部ドキュメント指定機能
6. **FR-006**: プリセット実行モード
7. **FR-007**: base_phase.py への統合

### Design Phase (Phase 2)

設計書において、以下の実装方針が定義されています：

- 新規モジュール: `phase_dependencies.py`
- 既存モジュール拡張: `main.py`, `base_phase.py`
- データ構造: `PHASE_DEPENDENCIES`, `PHASE_PRESETS`
- 主要関数: `validate_phase_dependencies()`, `detect_circular_dependencies()`, `validate_external_document()`

---

## 1. テスト戦略サマリー

### 選択されたテスト戦略

**UNIT_INTEGRATION**

### テスト対象の範囲

#### ユニットテスト対象
- `phase_dependencies.py` の各関数
  - `validate_phase_dependencies()`
  - `detect_circular_dependencies()`
  - `validate_external_document()`
- `main.py` の新規関数
  - `_get_preset_phases()`
  - `_load_external_documents()`

#### インテグレーションテスト対象
- フェーズ実行時の依存関係チェック統合
- CLIオプションとフェーズ実行の統合
- プリセット機能とフェーズ選択の統合
- 外部ドキュメント指定と依存関係チェックの統合

### テストの目的

1. **機能正確性**: すべての機能要件が正しく実装されていることを検証
2. **後方互換性**: 既存ワークフローが正常に動作することを確認
3. **エラーハンドリング**: 異常系のエラーメッセージが明確であることを確認
4. **統合動作**: 各コンポーネントが正しく連携することを確認

---

## 2. ユニットテストシナリオ

### 2.1 validate_phase_dependencies() のテスト

#### UT-001: 依存関係チェック - 正常系（すべて完了）

**目的**: すべての依存フェーズが完了している場合、バリデーションが成功すること

**前提条件**:
- モックの `MetadataManager` を作成
- `get_all_phases_status()` が以下を返すように設定:
  ```python
  {
      'planning': 'completed',
      'requirements': 'completed',
      'design': 'completed',
      'test_scenario': 'completed'
  }
  ```

**入力**:
```python
phase_name = 'implementation'
metadata_manager = MockMetadataManager()
skip_check = False
ignore_violations = False
```

**期待結果**:
```python
result = {
    'valid': True
}
```

**検証項目**:
- `result['valid']` が `True` であること
- エラーメッセージが含まれていないこと

---

#### UT-002: 依存関係チェック - 異常系（依存フェーズ未完了）

**目的**: 依存フェーズが未完了の場合、バリデーションが失敗し、適切なエラーメッセージが返されること

**前提条件**:
- モックの `MetadataManager` を作成
- `get_all_phases_status()` が以下を返すように設定:
  ```python
  {
      'planning': 'completed',
      'requirements': 'pending',
      'design': 'in_progress',
      'test_scenario': 'pending'
  }
  ```

**入力**:
```python
phase_name = 'implementation'
metadata_manager = MockMetadataManager()
skip_check = False
ignore_violations = False
```

**期待結果**:
```python
result = {
    'valid': False,
    'error': "Phase 'requirements' must be completed before 'implementation'",
    'missing_phases': ['requirements']
}
```

**検証項目**:
- `result['valid']` が `False` であること
- `result['error']` に未完了フェーズ名が含まれていること
- `result['missing_phases']` に `'requirements'` が含まれていること

---

#### UT-003: 依存関係チェック - skip_check フラグ

**目的**: `skip_check=True` の場合、依存関係チェックがスキップされ、常に成功すること

**前提条件**:
- モックの `MetadataManager` を作成
- 依存フェーズがすべて未完了でも問題ない設定

**入力**:
```python
phase_name = 'implementation'
metadata_manager = MockMetadataManager()
skip_check = True
ignore_violations = False
```

**期待結果**:
```python
result = {
    'valid': True
}
```

**検証項目**:
- `result['valid']` が `True` であること
- 依存関係の状態に関わらず成功すること
- 即座にリターンすること（パフォーマンス確認）

---

#### UT-004: 依存関係チェック - ignore_violations フラグ

**目的**: `ignore_violations=True` の場合、依存関係違反があっても警告のみで成功すること

**前提条件**:
- モックの `MetadataManager` を作成
- `get_all_phases_status()` が以下を返すように設定:
  ```python
  {
      'planning': 'completed',
      'requirements': 'pending',
      'design': 'pending',
      'test_scenario': 'pending'
  }
  ```

**入力**:
```python
phase_name = 'implementation'
metadata_manager = MockMetadataManager()
skip_check = False
ignore_violations = True
```

**期待結果**:
```python
result = {
    'valid': False,
    'ignored': True,
    'warning': "Dependency violations ignored: requirements, design, test_scenario",
    'missing_phases': ['requirements', 'design', 'test_scenario']
}
```

**検証項目**:
- `result['valid']` が `False` であること
- `result['ignored']` が `True` であること
- `result['warning']` に未完了フェーズ名が含まれていること

---

#### UT-005: 依存関係チェック - 依存なしフェーズ

**目的**: 依存関係のないフェーズ（planning）は常にチェックが成功すること

**前提条件**:
- モックの `MetadataManager` を作成

**入力**:
```python
phase_name = 'planning'
metadata_manager = MockMetadataManager()
skip_check = False
ignore_violations = False
```

**期待結果**:
```python
result = {
    'valid': True
}
```

**検証項目**:
- `result['valid']` が `True` であること
- 依存関係チェックがスキップされること

---

#### UT-006: 依存関係チェック - 不正なフェーズ名

**目的**: 存在しないフェーズ名が指定された場合、適切なエラーが発生すること

**前提条件**:
- モックの `MetadataManager` を作成

**入力**:
```python
phase_name = 'invalid_phase'
metadata_manager = MockMetadataManager()
skip_check = False
ignore_violations = False
```

**期待結果**:
- `ValueError` が発生すること
- エラーメッセージに「Invalid phase name」が含まれること

**検証項目**:
- 例外が発生すること
- 例外メッセージが明確であること

---

### 2.2 detect_circular_dependencies() のテスト

#### UT-007: 循環参照検出 - 正常系（循環なし）

**目的**: `PHASE_DEPENDENCIES` に循環参照が存在しない場合、空リストが返されること

**前提条件**:
- 現在の `PHASE_DEPENDENCIES` 定義を使用

**入力**:
```python
# パラメータなし（PHASE_DEPENDENCIES を参照）
```

**期待結果**:
```python
cycles = []
```

**検証項目**:
- `cycles` が空リストであること
- 処理が正常に完了すること

---

#### UT-008: 循環参照検出 - 異常系（循環あり）

**目的**: 循環参照が存在する場合、循環パスが検出されること

**前提条件**:
- テスト用の循環参照を含む依存関係定義を作成:
  ```python
  TEST_DEPENDENCIES = {
      'A': ['B'],
      'B': ['C'],
      'C': ['A']  # 循環
  }
  ```

**入力**:
```python
# テスト用の依存関係定義を使用
```

**期待結果**:
```python
cycles = [['A', 'B', 'C', 'A']]
```

**検証項目**:
- `cycles` に循環パスが含まれていること
- 循環パスが正しく検出されること

---

### 2.3 validate_external_document() のテスト

#### UT-009: 外部ドキュメント検証 - 正常系

**目的**: 正常なMarkdownファイルが指定された場合、バリデーションが成功すること

**前提条件**:
- テスト用のMarkdownファイルを作成（10MB以下）
- ファイルがリポジトリ内に存在

**入力**:
```python
file_path = 'test_data/valid_requirements.md'
```

**期待結果**:
```python
result = {
    'valid': True,
    'absolute_path': '/path/to/repo/test_data/valid_requirements.md'
}
```

**検証項目**:
- `result['valid']` が `True` であること
- `result['absolute_path']` が正しいパスであること

---

#### UT-010: 外部ドキュメント検証 - ファイル存在しない

**目的**: 存在しないファイルが指定された場合、バリデーションが失敗すること

**前提条件**:
- なし

**入力**:
```python
file_path = 'non_existent_file.md'
```

**期待結果**:
```python
result = {
    'valid': False,
    'error': 'File not found: non_existent_file.md'
}
```

**検証項目**:
- `result['valid']` が `False` であること
- `result['error']` に「not found」が含まれていること

---

#### UT-011: 外部ドキュメント検証 - 不正なファイル形式

**目的**: 許可されていないファイル形式（.sh, .exe等）が指定された場合、バリデーションが失敗すること

**前提条件**:
- テスト用の実行可能ファイル（.sh）を作成

**入力**:
```python
file_path = 'test_data/script.sh'
```

**期待結果**:
```python
result = {
    'valid': False,
    'error': 'Invalid file format: .sh. Only .md and .txt are allowed'
}
```

**検証項目**:
- `result['valid']` が `False` であること
- `result['error']` に「Invalid file format」が含まれていること

---

#### UT-012: 外部ドキュメント検証 - ファイルサイズ超過

**目的**: ファイルサイズが10MBを超える場合、バリデーションが失敗すること

**前提条件**:
- テスト用の大きなファイル（10MB超）を作成

**入力**:
```python
file_path = 'test_data/large_file.md'
```

**期待結果**:
```python
result = {
    'valid': False,
    'error': 'File size exceeds 10MB limit (actual: 15.2MB)'
}
```

**検証項目**:
- `result['valid']` が `False` であること
- `result['error']` に「size exceeds」が含まれていること

---

#### UT-013: 外部ドキュメント検証 - リポジトリ外のファイル

**目的**: リポジトリ外のファイル（パストラバーサル攻撃）が指定された場合、バリデーションが失敗すること

**前提条件**:
- なし

**入力**:
```python
file_path = '/etc/passwd'
```

**期待結果**:
```python
result = {
    'valid': False,
    'error': 'File must be within the repository'
}
```

**検証項目**:
- `result['valid']` が `False` であること
- `result['error']` に「within the repository」が含まれていること

---

### 2.4 _get_preset_phases() のテスト

#### UT-014: プリセット取得 - requirements-only

**目的**: `requirements-only` プリセットが正しいフェーズリストを返すこと

**前提条件**:
- `PHASE_PRESETS` が定義されている

**入力**:
```python
preset_name = 'requirements-only'
```

**期待結果**:
```python
phases = ['requirements']
```

**検証項目**:
- `phases` が `['requirements']` であること

---

#### UT-015: プリセット取得 - design-phase

**目的**: `design-phase` プリセットが正しいフェーズリストを返すこと

**前提条件**:
- `PHASE_PRESETS` が定義されている

**入力**:
```python
preset_name = 'design-phase'
```

**期待結果**:
```python
phases = ['requirements', 'design']
```

**検証項目**:
- `phases` が `['requirements', 'design']` であること

---

#### UT-016: プリセット取得 - implementation-phase

**目的**: `implementation-phase` プリセットが正しいフェーズリストを返すこと

**前提条件**:
- `PHASE_PRESETS` が定義されている

**入力**:
```python
preset_name = 'implementation-phase'
```

**期待結果**:
```python
phases = ['requirements', 'design', 'test_scenario', 'implementation']
```

**検証項目**:
- `phases` が正しい順序で返されること

---

#### UT-017: プリセット取得 - 不正なプリセット名

**目的**: 存在しないプリセット名が指定された場合、適切なエラーが発生すること

**前提条件**:
- `PHASE_PRESETS` が定義されている

**入力**:
```python
preset_name = 'invalid-preset'
```

**期待結果**:
- `ValueError` が発生すること
- エラーメッセージに「Invalid preset」が含まれること

**検証項目**:
- 例外が発生すること
- 例外メッセージが明確であること

---

### 2.5 PHASE_DEPENDENCIES 定義のテスト

#### UT-018: フェーズ依存関係定義の完全性

**目的**: すべてのフェーズが `PHASE_DEPENDENCIES` に定義されていること

**前提条件**:
- `PHASE_DEPENDENCIES` が定義されている

**入力**:
```python
expected_phases = [
    'planning', 'requirements', 'design', 'test_scenario',
    'implementation', 'test_implementation', 'testing',
    'documentation', 'report', 'evaluation'
]
```

**期待結果**:
- すべての `expected_phases` が `PHASE_DEPENDENCIES` のキーに存在すること

**検証項目**:
- キーの完全性
- 値が空リストまたはフェーズ名のリストであること

---

#### UT-019: フェーズ依存関係の前方依存性

**目的**: すべての依存関係が前方依存（Phase N → Phase N-1以前）であること

**前提条件**:
- `PHASE_DEPENDENCIES` が定義されている
- フェーズ順序が定義されている

**入力**:
```python
phase_order = [
    'planning', 'requirements', 'design', 'test_scenario',
    'implementation', 'test_implementation', 'testing',
    'documentation', 'report', 'evaluation'
]
```

**期待結果**:
- すべての依存関係が前方依存であること
- 後方依存（Phase N → Phase N+1）が存在しないこと

**検証項目**:
- 各フェーズの依存関係がフェーズ順序に従っていること

---

### 2.6 パフォーマンステスト

#### UT-020: 依存関係チェックのオーバーヘッド

**目的**: 依存関係チェックのオーバーヘッドが0.1秒以下であること

**前提条件**:
- モックの `MetadataManager` を作成
- 100回の連続実行

**入力**:
```python
phase_name = 'implementation'
metadata_manager = MockMetadataManager()
iterations = 100
```

**期待結果**:
- 100回の平均実行時間が0.1秒以下であること

**検証項目**:
- パフォーマンス要件（NFR-001）が満たされること
- 早期リターン最適化が機能していること

---

## 3. インテグレーションテストシナリオ

### 3.1 依存関係チェック統合テスト

#### IT-001: フェーズ実行時の依存関係チェック - 正常系

**目的**: 依存関係チェックが有効な場合、すべての依存フェーズが完了していれば実行が成功すること

**前提条件**:
- テスト用のリポジトリ環境を作成
- `metadata.json` を作成し、以下の状態に設定:
  ```json
  {
    "phases": {
      "planning": {"status": "completed"},
      "requirements": {"status": "completed"},
      "design": {"status": "completed"},
      "test_scenario": {"status": "completed"}
    }
  }
  ```

**テスト手順**:
1. `python main.py execute --phase implementation --issue test-issue` を実行
2. 標準出力を確認
3. `metadata.json` のステータスを確認

**期待結果**:
- 終了コード: 0（成功）
- 標準出力に「Phase 'implementation' started」が表示される
- `metadata.json` の `implementation` フェーズステータスが更新される

**確認項目**:
- [ ] 依存関係チェックが実行された
- [ ] エラーメッセージが表示されなかった
- [ ] フェーズが正常に実行された
- [ ] メタデータが正しく更新された

---

#### IT-002: フェーズ実行時の依存関係チェック - 異常系（依存フェーズ未完了）

**目的**: 依存関係チェックが有効な場合、未完了の依存フェーズがあるとエラーで停止すること

**前提条件**:
- テスト用のリポジトリ環境を作成
- `metadata.json` を作成し、以下の状態に設定:
  ```json
  {
    "phases": {
      "planning": {"status": "completed"},
      "requirements": {"status": "pending"},
      "design": {"status": "pending"},
      "test_scenario": {"status": "pending"}
    }
  }
  ```

**テスト手順**:
1. `python main.py execute --phase implementation --issue test-issue` を実行
2. 標準エラー出力を確認
3. `metadata.json` のステータスを確認

**期待結果**:
- 終了コード: 1（エラー）
- 標準エラー出力に以下が表示される:
  ```
  [ERROR] Dependency check failed for phase 'implementation'
  [ERROR] The following phases must be completed first:
  [ERROR]   - requirements: pending
  ```
- `metadata.json` の `implementation` フェーズステータスが `failed` になる

**確認項目**:
- [ ] 依存関係チェックでエラーが発生した
- [ ] エラーメッセージに未完了フェーズ名が含まれる
- [ ] フェーズ実行が開始されなかった
- [ ] メタデータに失敗が記録された

---

#### IT-003: --skip-dependency-check フラグの動作確認

**目的**: `--skip-dependency-check` フラグ指定時、依存関係チェックがスキップされ、強制実行されること

**前提条件**:
- テスト用のリポジトリ環境を作成
- `metadata.json` を作成し、依存フェーズが未完了の状態に設定

**テスト手順**:
1. `python main.py execute --phase implementation --issue test-issue --skip-dependency-check` を実行
2. 標準出力を確認
3. フェーズが実行されることを確認

**期待結果**:
- 終了コード: 0（成功）
- 標準出力に以下の警告が表示される:
  ```
  [WARNING] Dependency check has been skipped!
  [WARNING] This may result in inconsistent workflow execution.
  ```
- フェーズが正常に実行される

**確認項目**:
- [ ] 警告メッセージが表示された
- [ ] 依存関係チェックがスキップされた
- [ ] フェーズが実行された
- [ ] メタデータが更新された

---

#### IT-004: --ignore-dependencies フラグの動作確認

**目的**: `--ignore-dependencies` フラグ指定時、依存関係違反があっても警告のみで実行が継続されること

**前提条件**:
- テスト用のリポジトリ環境を作成
- `metadata.json` を作成し、依存フェーズが未完了の状態に設定

**テスト手順**:
1. `python main.py execute --phase implementation --issue test-issue --ignore-dependencies` を実行
2. 標準出力を確認
3. フェーズが実行されることを確認

**期待結果**:
- 終了コード: 0（成功）
- 標準出力に以下の警告が表示される:
  ```
  [WARNING] Dependency violations ignored: requirements, design, test_scenario
  ```
- フェーズが正常に実行される

**確認項目**:
- [ ] 警告メッセージが表示された
- [ ] 未完了の依存フェーズ名が表示された
- [ ] フェーズが実行された
- [ ] エラーにはならなかった

---

### 3.2 プリセット機能統合テスト

#### IT-005: プリセット実行 - requirements-only

**目的**: `--preset requirements-only` で requirements フェーズのみが実行されること

**前提条件**:
- テスト用のリポジトリ環境を作成
- Issue #test-issue が存在する

**テスト手順**:
1. `python main.py execute --preset requirements-only --issue test-issue` を実行
2. 実行されたフェーズを確認
3. `metadata.json` を確認

**期待結果**:
- 終了コード: 0（成功）
- requirements フェーズのみが実行される
- 他のフェーズはスキップされる
- `metadata.json` に requirements のステータスのみ記録される

**確認項目**:
- [ ] requirements フェーズが実行された
- [ ] design フェーズが実行されなかった
- [ ] 他のフェーズがスキップされた
- [ ] メタデータが正しく更新された

---

#### IT-006: プリセット実行 - design-phase

**目的**: `--preset design-phase` で requirements と design フェーズが実行されること

**前提条件**:
- テスト用のリポジトリ環境を作成
- Issue #test-issue が存在する

**テスト手順**:
1. `python main.py execute --preset design-phase --issue test-issue` を実行
2. 実行されたフェーズを確認
3. `metadata.json` を確認

**期待結果**:
- 終了コード: 0（成功）
- requirements と design フェーズが順次実行される
- 他のフェーズはスキップされる

**確認項目**:
- [ ] requirements フェーズが実行された
- [ ] design フェーズが実行された
- [ ] test_scenario フェーズが実行されなかった
- [ ] メタデータが正しく更新された

---

#### IT-007: プリセット実行 - implementation-phase

**目的**: `--preset implementation-phase` で requirements, design, test_scenario, implementation フェーズが実行されること

**前提条件**:
- テスト用のリポジトリ環境を作成
- Issue #test-issue が存在する

**テスト手順**:
1. `python main.py execute --preset implementation-phase --issue test-issue` を実行
2. 実行されたフェーズを確認
3. `metadata.json` を確認

**期待結果**:
- 終了コード: 0（成功）
- requirements, design, test_scenario, implementation フェーズが順次実行される
- test_implementation フェーズ以降はスキップされる

**確認項目**:
- [ ] 4つのフェーズが順次実行された
- [ ] test_implementation フェーズが実行されなかった
- [ ] メタデータが正しく更新された

---

#### IT-008: プリセットとフェーズオプションの排他性

**目的**: `--preset` と `--phase` オプションが同時に指定された場合、エラーになること

**前提条件**:
- テスト用のリポジトリ環境を作成

**テスト手順**:
1. `python main.py execute --preset design-phase --phase implementation --issue test-issue` を実行
2. エラーメッセージを確認

**期待結果**:
- 終了コード: 1（エラー）
- 標準エラー出力に以下が表示される:
  ```
  [ERROR] Options '--preset' and '--phase' are mutually exclusive
  [ERROR] Please specify only one of them
  ```

**確認項目**:
- [ ] エラーメッセージが表示された
- [ ] フェーズが実行されなかった

---

### 3.3 外部ドキュメント指定機能統合テスト

#### IT-009: 外部ドキュメント指定 - requirements-doc

**目的**: `--requirements-doc` オプションで外部ドキュメントを指定した場合、requirements フェーズがスキップされること

**前提条件**:
- テスト用のリポジトリ環境を作成
- 外部要件定義書 `external_requirements.md` を作成

**テスト手順**:
1. `python main.py execute --phase implementation --issue test-issue --requirements-doc external_requirements.md --skip-dependency-check` を実行
2. 実行されたフェーズを確認
3. `metadata.json` の `external_documents` フィールドを確認

**期待結果**:
- 終了コード: 0（成功）
- requirements フェーズがスキップされる
- `metadata.json` に以下が記録される:
  ```json
  {
    "external_documents": {
      "requirements": "external_requirements.md"
    }
  }
  ```

**確認項目**:
- [ ] 外部ドキュメントが読み込まれた
- [ ] requirements フェーズがスキップされた
- [ ] メタデータに外部ドキュメント情報が記録された

---

#### IT-010: 外部ドキュメント指定 - 複数ドキュメント

**目的**: 複数の外部ドキュメント（`--requirements-doc`, `--design-doc`）を同時に指定できること

**前提条件**:
- テスト用のリポジトリ環境を作成
- 外部要件定義書 `external_requirements.md` を作成
- 外部設計書 `external_design.md` を作成

**テスト手順**:
1. `python main.py execute --phase implementation --issue test-issue --requirements-doc external_requirements.md --design-doc external_design.md --skip-dependency-check` を実行
2. `metadata.json` を確認

**期待結果**:
- 終了コード: 0（成功）
- `metadata.json` に以下が記録される:
  ```json
  {
    "external_documents": {
      "requirements": "external_requirements.md",
      "design": "external_design.md"
    }
  }
  ```

**確認項目**:
- [ ] 複数の外部ドキュメントが読み込まれた
- [ ] メタデータに両方のドキュメント情報が記録された

---

#### IT-011: 外部ドキュメント指定 - バリデーションエラー

**目的**: 不正な外部ドキュメントパスが指定された場合、エラーになること

**前提条件**:
- テスト用のリポジトリ環境を作成

**テスト手順**:
1. `python main.py execute --phase implementation --issue test-issue --requirements-doc /etc/passwd` を実行
2. エラーメッセージを確認

**期待結果**:
- 終了コード: 1（エラー）
- 標準エラー出力に以下が表示される:
  ```
  [ERROR] Invalid external document: /etc/passwd
  [ERROR] Reason: File must be within the repository
  ```

**確認項目**:
- [ ] エラーメッセージが表示された
- [ ] フェーズが実行されなかった
- [ ] セキュリティチェックが機能した

---

### 3.4 後方互換性テスト

#### IT-012: 既存ワークフロー - --phase all

**目的**: 既存の `--phase all` モードが正常に動作すること（後方互換性の確認）

**前提条件**:
- テスト用のリポジトリ環境を作成
- Issue #test-issue が存在する

**テスト手順**:
1. `python main.py execute --phase all --issue test-issue` を実行
2. すべてのフェーズが順次実行されることを確認

**期待結果**:
- 終了コード: 0（成功）
- すべてのフェーズ（planning → evaluation）が順次実行される
- 既存の動作と同じ

**確認項目**:
- [ ] すべてのフェーズが実行された
- [ ] 既存の動作と変わりがない
- [ ] 依存関係チェックが機能している

---

#### IT-013: 既存ワークフロー - 単一フェーズ実行

**目的**: 既存の単一フェーズ実行が正常に動作すること

**前提条件**:
- テスト用のリポジトリ環境を作成
- 依存フェーズがすべて完了している状態

**テスト手順**:
1. `python main.py execute --phase implementation --issue test-issue` を実行
2. implementation フェーズのみが実行されることを確認

**期待結果**:
- 終了コード: 0（成功）
- implementation フェーズのみが実行される
- 依存関係チェックが機能している

**確認項目**:
- [ ] 指定したフェーズが実行された
- [ ] 他のフェーズが実行されなかった
- [ ] 既存の動作と変わりがない

---

### 3.5 エラーハンドリング統合テスト

#### IT-014: エラーメッセージの明確性 - 依存関係違反

**目的**: 依存関係違反時のエラーメッセージが明確で、解決方法が提示されること

**前提条件**:
- テスト用のリポジトリ環境を作成
- 依存フェーズが未完了の状態

**テスト手順**:
1. `python main.py execute --phase implementation --issue test-issue` を実行
2. エラーメッセージを確認

**期待結果**:
- 標準エラー出力に以下が表示される:
  ```
  [ERROR] Dependency check failed for phase 'implementation'
  [ERROR] The following phases must be completed first:
  [ERROR]   - requirements: pending
  [ERROR]   - design: pending
  [ERROR]   - test_scenario: pending
  [ERROR]
  [ERROR] To bypass this check, use one of the following options:
  [ERROR]   --skip-dependency-check    (skip all dependency checks)
  [ERROR]   --ignore-dependencies      (show warnings but continue)
  ```

**確認項目**:
- [ ] エラーメッセージが明確である
- [ ] 未完了のフェーズ名が表示される
- [ ] 解決方法が提示される（AC-007）

---

#### IT-015: フラグの排他性チェック - skip vs ignore

**目的**: `--skip-dependency-check` と `--ignore-dependencies` が同時に指定された場合、エラーになること

**前提条件**:
- テスト用のリポジトリ環境を作成

**テスト手順**:
1. `python main.py execute --phase implementation --issue test-issue --skip-dependency-check --ignore-dependencies` を実行
2. エラーメッセージを確認

**期待結果**:
- 終了コード: 1（エラー）
- 標準エラー出力に以下が表示される:
  ```
  [ERROR] Options '--skip-dependency-check' and '--ignore-dependencies' are mutually exclusive
  [ERROR] Please specify only one of them
  ```

**確認項目**:
- [ ] エラーメッセージが表示された
- [ ] フェーズが実行されなかった

---

### 3.6 パフォーマンス統合テスト

#### IT-016: 依存関係チェックのオーバーヘッド測定

**目的**: 依存関係チェックを含めたフェーズ実行のオーバーヘッドが要件（0.1秒以下）を満たすこと

**前提条件**:
- テスト用のリポジトリ環境を作成
- すべての依存フェーズが完了している状態

**テスト手順**:
1. `python main.py execute --phase implementation --issue test-issue` を10回実行
2. 各実行の依存関係チェック時間を測定
3. 平均時間を計算

**期待結果**:
- 依存関係チェックの平均時間が0.1秒以下
- パフォーマンス要件（NFR-001）が満たされる

**確認項目**:
- [ ] パフォーマンス要件が満たされた
- [ ] 早期リターン最適化が機能している
- [ ] メタデータ読み込み回数が最小化されている

---

#### IT-017: 既存ワークフローのパフォーマンス劣化確認

**目的**: 依存関係チェック機能の追加により、既存ワークフローのパフォーマンスが劣化していないこと

**前提条件**:
- テスト用のリポジトリ環境を作成

**テスト手順**:
1. 依存関係チェック機能追加前後でフェーズ実行時間を測定
2. 実行時間の差分を計算

**期待結果**:
- パフォーマンス劣化が5%以内
- NFR-001（既存ワークフローのパフォーマンス劣化なし）が満たされる

**確認項目**:
- [ ] パフォーマンス劣化が許容範囲内
- [ ] 既存ワークフローが正常に動作する

---

## 4. テストデータ

### 4.1 ユニットテスト用データ

#### モック MetadataManager

```python
class MockMetadataManager:
    """ユニットテスト用のモック"""

    def __init__(self, phases_status: Dict[str, str]):
        self._phases_status = phases_status

    def get_all_phases_status(self) -> Dict[str, str]:
        return self._phases_status
```

#### テスト用フェーズステータス

**正常系（すべて完了）**:
```python
{
    'planning': 'completed',
    'requirements': 'completed',
    'design': 'completed',
    'test_scenario': 'completed'
}
```

**異常系（依存フェーズ未完了）**:
```python
{
    'planning': 'completed',
    'requirements': 'pending',
    'design': 'in_progress',
    'test_scenario': 'pending'
}
```

### 4.2 インテグレーションテスト用データ

#### テスト用 metadata.json

**正常系**:
```json
{
  "issue_number": "test-issue",
  "phases": {
    "planning": {
      "status": "completed",
      "started_at": "2025-10-12T10:00:00Z",
      "completed_at": "2025-10-12T10:30:00Z"
    },
    "requirements": {
      "status": "completed",
      "started_at": "2025-10-12T11:00:00Z",
      "completed_at": "2025-10-12T11:30:00Z"
    },
    "design": {
      "status": "completed",
      "started_at": "2025-10-12T12:00:00Z",
      "completed_at": "2025-10-12T12:30:00Z"
    },
    "test_scenario": {
      "status": "completed",
      "started_at": "2025-10-12T13:00:00Z",
      "completed_at": "2025-10-12T13:30:00Z"
    }
  }
}
```

**異常系（依存フェーズ未完了）**:
```json
{
  "issue_number": "test-issue",
  "phases": {
    "planning": {
      "status": "completed",
      "started_at": "2025-10-12T10:00:00Z",
      "completed_at": "2025-10-12T10:30:00Z"
    },
    "requirements": {
      "status": "pending"
    },
    "design": {
      "status": "pending"
    },
    "test_scenario": {
      "status": "pending"
    }
  }
}
```

#### テスト用外部ドキュメント

**external_requirements.md**:
```markdown
# 外部要件定義書

## 機能要件
- ユーザーは商品を検索できる
- ユーザーは商品をカートに追加できる

## 非機能要件
- レスポンスタイムは1秒以内
```

**external_design.md**:
```markdown
# 外部設計書

## アーキテクチャ
- MVC パターン

## データベース設計
- users テーブル
- products テーブル
```

### 4.3 境界値データ

#### ファイルサイズ境界値

- **正常値**: 9.9MB のファイル
- **境界値**: 10.0MB のファイル
- **異常値**: 10.1MB のファイル

#### フェーズ名境界値

- **正常値**: `'implementation'`
- **異常値**: `''` (空文字列)
- **異常値**: `'invalid_phase'` (存在しないフェーズ)

---

## 5. テスト環境要件

### 5.1 ユニットテスト環境

- **Python**: 3.8以上
- **テストフレームワーク**: pytest
- **モックライブラリ**: unittest.mock
- **カバレッジツール**: pytest-cov

### 5.2 インテグレーションテスト環境

- **Python**: 3.8以上
- **テストフレームワーク**: pytest
- **Git環境**: テスト用リポジトリ
- **一時ファイルシステム**: `tempfile`
- **環境変数**:
  - `GITHUB_TOKEN`: GitHub API アクセス用
  - `ANTHROPIC_API_KEY`: Claude API アクセス用

### 5.3 テストデータディレクトリ構成

```
tests/
├── unit/
│   └── core/
│       └── test_phase_dependencies.py
├── integration/
│   └── test_phase_dependencies_integration.py
└── test_data/
    ├── valid_requirements.md
    ├── large_file.md (10MB超)
    ├── script.sh (実行可能ファイル)
    └── metadata_samples/
        ├── all_completed.json
        └── dependencies_incomplete.json
```

---

## 6. テスト実行計画

### 6.1 ユニットテスト実行

```bash
# すべてのユニットテストを実行
pytest tests/unit/core/test_phase_dependencies.py -v

# カバレッジ測定付き
pytest tests/unit/core/test_phase_dependencies.py --cov=core.phase_dependencies --cov-report=html
```

**実行タイミング**: Phase 5 (Test Implementation) 完了後

### 6.2 インテグレーションテスト実行

```bash
# すべてのインテグレーションテストを実行
pytest tests/integration/test_phase_dependencies_integration.py -v

# 特定のテストケースのみ実行
pytest tests/integration/test_phase_dependencies_integration.py::test_phase_execution_with_dependency_check -v
```

**実行タイミング**: Phase 5 (Test Implementation) 完了後

### 6.3 すべてのテストを実行

```bash
# すべてのテストを実行（ユニット + インテグレーション）
pytest tests/ -v --cov=scripts/ai-workflow --cov-report=html

# 並列実行（高速化）
pytest tests/ -v -n auto
```

**実行タイミング**: Phase 6 (Testing)

---

## 7. 品質ゲート確認

### 7.1 Phase 2の戦略に沿ったテストシナリオである

- [x] **UNIT_INTEGRATION 戦略に従っている**
  - ユニットテストシナリオ: 20個（UT-001 ~ UT-020）
  - インテグレーションテストシナリオ: 17個（IT-001 ~ IT-017）
  - BDDシナリオ: なし（戦略に含まれない）

### 7.2 主要な正常系がカバーされている

- [x] **すべての機能要件の正常系がカバーされている**
  - FR-001 (依存関係定義): UT-018, UT-019
  - FR-002 (依存関係チェック): UT-001, IT-001
  - FR-003 (スキップ機能): UT-003, IT-003
  - FR-004 (警告表示): UT-004, IT-004
  - FR-005 (外部ドキュメント): UT-009, IT-009, IT-010
  - FR-006 (プリセット): UT-014~016, IT-005~007
  - FR-007 (base_phase統合): IT-001

### 7.3 主要な異常系がカバーされている

- [x] **主要なエラーケースがカバーされている**
  - 依存関係違反: UT-002, IT-002
  - 不正なフェーズ名: UT-006
  - 不正なプリセット名: UT-017
  - ファイル存在しない: UT-010
  - 不正なファイル形式: UT-011
  - ファイルサイズ超過: UT-012
  - セキュリティ違反: UT-013, IT-011
  - オプション排他性: IT-008, IT-015

### 7.4 期待結果が明確である

- [x] **すべてのテストケースに明確な期待結果が記載されている**
  - 各テストケースに「期待結果」セクションがある
  - 具体的な値・状態が記載されている
  - 検証項目がチェックリスト形式で明記されている

---

## 8. テストカバレッジ目標

### 8.1 コードカバレッジ目標

- **全体カバレッジ**: 80%以上（Planning Document の品質ゲート）
- **新規コード（phase_dependencies.py）**: 90%以上
- **修正コード（main.py, base_phase.py）**: 80%以上

### 8.2 機能カバレッジ

- **機能要件カバレッジ**: 100%（FR-001 ~ FR-007）
- **受け入れ基準カバレッジ**: 100%（AC-001 ~ AC-009）
- **非機能要件カバレッジ**: 100%（NFR-001のパフォーマンステスト）

---

## 9. リスクとテスト戦略

### リスク1: 既存ワークフローへの影響

**テスト戦略**:
- IT-012, IT-013 で後方互換性を確認
- IT-017 でパフォーマンス劣化がないことを確認

### リスク2: 依存関係の循環参照

**テスト戦略**:
- UT-007, UT-008 で循環参照検出機能をテスト
- UT-019 で前方依存性を確認

### リスク3: 外部ドキュメント指定時のセキュリティ

**テスト戦略**:
- UT-013 でパストラバーサル攻撃を防御
- IT-011 でセキュリティチェックの統合を確認
- UT-011 で不正なファイル形式を拒否

### リスク4: テストカバレッジの不足

**テスト戦略**:
- 20個のユニットテストで関数レベルを網羅
- 17個のインテグレーションテストでエンドツーエンドを確認
- カバレッジ測定ツールで定量的に評価

---

## 10. 次のステップ

1. **Phase 5 (Test Implementation)** に進む
   - ユニットテスト実装: `tests/unit/core/test_phase_dependencies.py`
   - インテグレーションテスト実装: `tests/integration/test_phase_dependencies_integration.py`

2. **Phase 6 (Testing)** でテストを実行
   - すべてのテストケースを実行
   - カバレッジを測定
   - 品質ゲートを確認

3. テスト結果を **Phase 8 (Report)** に反映

---

**作成日**: 2025-10-12
**作成者**: AI Workflow Orchestrator (Claude Agent SDK)
**バージョン**: 1.0
