# テストシナリオ - Issue #319

## 0. ドキュメントメタデータ

| 項目 | 内容 |
|------|------|
| Issue番号 | #319 |
| タイトル | [FEATURE] AIワークフロー: フェーズ依存関係の柔軟化と選択的実行機能 |
| 作成日 | 2025-10-12 |
| バージョン | 1.0 |
| ステータス | Draft |
| テスト戦略 | UNIT_INTEGRATION |

---

## 1. テスト戦略サマリー

### 1.1 選択されたテスト戦略

**UNIT_INTEGRATION**

Phase 2（設計フェーズ）で決定されたテスト戦略に基づき、以下の2種類のテストを実施します：

1. **Unitテスト**: 各関数・メソッド単位の詳細なテスト
2. **Integrationテスト**: コンポーネント間の連携および実際のCLI実行フロー全体のテスト

### 1.2 テスト対象の範囲

#### 新規作成モジュール
- `utils/dependency_validator.py`
  - `PHASE_DEPENDENCIES` 定数
  - `DependencyError` カスタム例外
  - `validate_phase_dependencies()` 関数
  - ユーティリティ関数（`get_phase_dependencies()`, `get_all_phase_dependencies()`）

#### 既存モジュール修正箇所
- `main.py`
  - CLIオプション追加（`--skip-dependency-check`, `--ignore-dependencies`, `--preset`）
  - 個別フェーズ実行時の依存関係チェック統合
  - オプション排他性チェック

- `phases/base_phase.py`
  - `run()` メソッドへの依存関係チェック統合

### 1.3 テストの目的

1. **依存関係定義の正確性検証**: `PHASE_DEPENDENCIES`が要件通りに定義されているか
2. **依存関係チェックロジックの検証**: 未完了フェーズを正しく検出できるか
3. **CLIオプションの動作検証**: スキップ・無視・プリセット機能が正しく動作するか
4. **エラーハンドリング検証**: 依存関係違反時に適切なエラー処理が行われるか
5. **統合動作の検証**: 実際のワークフロー実行における依存関係チェックの動作確認

### 1.4 テストカバレッジ目標

- **ラインカバレッジ**: 90%以上
- **ブランチカバレッジ**: 85%以上
- **クリティカルパスカバレッジ**: 100%

---

## 2. Unitテストシナリオ

### 2.1 `utils/dependency_validator.py` - PHASE_DEPENDENCIES 定義

#### TC-U-001: PHASE_DEPENDENCIES 構造検証

**目的**: 依存関係定義が正しいデータ構造を持つことを検証

**前提条件**: なし

**入力**: `PHASE_DEPENDENCIES` 定数

**期待結果**:
- `dict` 型である
- 全フェーズ名（planning, requirements, design, test_scenario, implementation, test_implementation, testing, documentation, report, evaluation）がキーとして存在する
- 各値が `list` 型である

**テストデータ**: `PHASE_DEPENDENCIES` 定数そのもの

---

#### TC-U-002: requirements フェーズの依存関係検証

**目的**: requirements フェーズが依存関係を持たないことを検証

**前提条件**: なし

**入力**: `PHASE_DEPENDENCIES['requirements']`

**期待結果**: 空リスト `[]`

**テストデータ**: なし

---

#### TC-U-003: design フェーズの依存関係検証

**目的**: design フェーズが requirements フェーズに依存することを検証

**前提条件**: なし

**入力**: `PHASE_DEPENDENCIES['design']`

**期待結果**: `['requirements']`

**テストデータ**: なし

---

#### TC-U-004: implementation フェーズの依存関係検証

**目的**: implementation フェーズが requirements, design, test_scenario に依存することを検証

**前提条件**: なし

**入力**: `PHASE_DEPENDENCIES['implementation']`

**期待結果**: リストに `'requirements'`, `'design'`, `'test_scenario'` が含まれる（順不同）

**テストデータ**: なし

---

#### TC-U-005: report フェーズの依存関係検証

**目的**: report フェーズが複数フェーズに依存することを検証

**前提条件**: なし

**入力**: `PHASE_DEPENDENCIES['report']`

**期待結果**: リストに `'requirements'`, `'design'`, `'implementation'`, `'testing'`, `'documentation'` が含まれる

**テストデータ**: なし

---

### 2.2 `utils/dependency_validator.py` - DependencyError クラス

#### TC-U-006: DependencyError - 単一フェーズ未完了

**目的**: 単一フェーズの依存関係違反時に適切なエラーメッセージが生成されることを検証

**前提条件**: なし

**入力**:
```python
error = DependencyError(
    phase_name='design',
    missing_phases=['requirements']
)
```

**期待結果**:
- `error.phase_name` が `'design'`
- `error.missing_phases` が `['requirements']`
- `error.message` に `"Phase 'requirements' must be completed before 'design'"` が含まれる
- `str(error)` でメッセージが表示される

**テストデータ**: 上記入力パラメータ

---

#### TC-U-007: DependencyError - 複数フェーズ未完了

**目的**: 複数フェーズの依存関係違反時に適切なエラーメッセージが生成されることを検証

**前提条件**: なし

**入力**:
```python
error = DependencyError(
    phase_name='implementation',
    missing_phases=['requirements', 'design']
)
```

**期待結果**:
- `error.phase_name` が `'implementation'`
- `error.missing_phases` が `['requirements', 'design']`
- `error.message` に `"Phases 'requirements', 'design' must be completed before 'implementation'"` が含まれる

**テストデータ**: 上記入力パラメータ

---

#### TC-U-008: DependencyError - カスタムメッセージ

**目的**: カスタムエラーメッセージが正しく設定されることを検証

**前提条件**: なし

**入力**:
```python
error = DependencyError(
    phase_name='design',
    missing_phases=['requirements'],
    message='Custom error message'
)
```

**期待結果**:
- `error.message` が `'Custom error message'`

**テストデータ**: 上記入力パラメータ

---

### 2.3 `utils/dependency_validator.py` - validate_phase_dependencies() 関数

#### TC-U-009: 依存関係なしのフェーズ（正常系）

**目的**: 依存関係のないフェーズは常に検証成功することを確認

**前提条件**: メタデータが初期化されている

**入力**:
```python
phase_name = 'requirements'
metadata = MetadataManager(metadata_path)
```

**期待結果**:
- 戻り値が `True`
- 標準出力に `"[INFO] Phase 'requirements' has no dependencies. Proceeding."` が表示される
- 例外が発生しない

**テストデータ**:
```json
{
  "phases": {
    "requirements": {"status": "pending"}
  }
}
```

---

#### TC-U-010: 依存関係満たされている（正常系）

**目的**: 依存フェーズが completed の場合、検証成功することを確認

**前提条件**: requirements フェーズが completed

**入力**:
```python
phase_name = 'design'
metadata = MetadataManager(metadata_path)
metadata.update_phase_status('requirements', 'completed')
```

**期待結果**:
- 戻り値が `True`
- 標準出力に `"[INFO] Dependency check passed for phase 'design'."` が表示される
- 例外が発生しない

**テストデータ**:
```json
{
  "phases": {
    "requirements": {"status": "completed"},
    "design": {"status": "pending"}
  }
}
```

---

#### TC-U-011: 依存関係違反（異常系）

**目的**: 依存フェーズが未完了の場合、DependencyError が発生することを確認

**前提条件**: requirements フェーズが pending

**入力**:
```python
phase_name = 'design'
metadata = MetadataManager(metadata_path)
# requirements は pending のまま
```

**期待結果**:
- `DependencyError` 例外が発生
- 例外メッセージに `'requirements'` と `'design'` が含まれる
- 例外の `missing_phases` が `['requirements']`

**テストデータ**:
```json
{
  "phases": {
    "requirements": {"status": "pending"},
    "design": {"status": "pending"}
  }
}
```

---

#### TC-U-012: 複数依存関係の一部未完了（異常系）

**目的**: 複数の依存フェーズのうち一部が未完了の場合、DependencyError が発生することを確認

**前提条件**: requirements は completed、design は pending

**入力**:
```python
phase_name = 'test_scenario'
metadata = MetadataManager(metadata_path)
metadata.update_phase_status('requirements', 'completed')
# design は pending のまま
```

**期待結果**:
- `DependencyError` 例外が発生
- 例外の `missing_phases` が `['design']`

**テストデータ**:
```json
{
  "phases": {
    "requirements": {"status": "completed"},
    "design": {"status": "pending"},
    "test_scenario": {"status": "pending"}
  }
}
```

---

#### TC-U-013: skip_check フラグ有効（正常系）

**目的**: skip_check=True の場合、依存関係チェックがスキップされることを確認

**前提条件**: requirements フェーズが pending

**入力**:
```python
phase_name = 'design'
metadata = MetadataManager(metadata_path)
skip_check = True
```

**期待結果**:
- 戻り値が `True`
- 標準出力に `"[WARNING] Dependency check skipped. Proceeding without validation."` が表示される
- 例外が発生しない（依存関係未満足でも）

**テストデータ**:
```json
{
  "phases": {
    "requirements": {"status": "pending"},
    "design": {"status": "pending"}
  }
}
```

---

#### TC-U-014: ignore_violations フラグ有効（警告モード）

**目的**: ignore_violations=True の場合、警告のみ表示して実行継続することを確認

**前提条件**: requirements フェーズが pending

**入力**:
```python
phase_name = 'design'
metadata = MetadataManager(metadata_path)
ignore_violations = True
```

**期待結果**:
- 戻り値が `True`
- 標準出力に `"[WARNING] Dependency violation: Phase 'requirements' is not completed. Continuing anyway."` が表示される
- 例外が発生しない

**テストデータ**:
```json
{
  "phases": {
    "requirements": {"status": "pending"},
    "design": {"status": "pending"}
  }
}
```

---

#### TC-U-015: 未知のフェーズ名（異常系）

**目的**: 存在しないフェーズ名を指定した場合、ValueError が発生することを確認

**前提条件**: メタデータが初期化されている

**入力**:
```python
phase_name = 'unknown_phase'
metadata = MetadataManager(metadata_path)
```

**期待結果**:
- `ValueError` 例外が発生
- 例外メッセージに `"Unknown phase: 'unknown_phase'"` が含まれる

**テストデータ**: なし

---

#### TC-U-016: 複数依存関係すべて未完了（異常系）

**目的**: すべての依存フェーズが未完了の場合、正しくエラーが発生することを確認

**前提条件**: requirements, design, test_scenario すべてが pending

**入力**:
```python
phase_name = 'implementation'
metadata = MetadataManager(metadata_path)
```

**期待結果**:
- `DependencyError` 例外が発生
- 例外の `missing_phases` に `'requirements'`, `'design'`, `'test_scenario'` が含まれる

**テストデータ**:
```json
{
  "phases": {
    "requirements": {"status": "pending"},
    "design": {"status": "pending"},
    "test_scenario": {"status": "pending"},
    "implementation": {"status": "pending"}
  }
}
```

---

### 2.4 `utils/dependency_validator.py` - ユーティリティ関数

#### TC-U-017: get_phase_dependencies() - 正常系

**目的**: 指定フェーズの依存関係リストが正しく取得できることを確認

**前提条件**: なし

**入力**:
```python
phase_name = 'design'
```

**期待結果**:
- 戻り値が `['requirements']`
- コピーされたリストである（元のリストと異なるオブジェクト）

**テストデータ**: なし

---

#### TC-U-018: get_phase_dependencies() - 未知のフェーズ

**目的**: 存在しないフェーズ名を指定した場合、ValueError が発生することを確認

**前提条件**: なし

**入力**:
```python
phase_name = 'unknown_phase'
```

**期待結果**:
- `ValueError` 例外が発生
- 例外メッセージに `"Unknown phase"` が含まれる

**テストデータ**: なし

---

#### TC-U-019: get_all_phase_dependencies() - 正常系

**目的**: すべてのフェーズ依存関係定義が取得できることを確認

**前提条件**: なし

**入力**: なし

**期待結果**:
- 戻り値が `dict` 型
- すべてのフェーズ名がキーとして含まれる
- コピーされた辞書である（元の辞書と異なるオブジェクト）

**テストデータ**: なし

---

### 2.5 `main.py` - CLIオプションパース

#### TC-U-020: --skip-dependency-check フラグのパース

**目的**: --skip-dependency-check フラグが正しくパースされることを確認

**前提条件**: なし

**入力**:
```bash
python main.py execute --phase design --issue 319 --skip-dependency-check
```

**期待結果**:
- `skip_dependency_check` パラメータが `True`
- 他のパラメータは正常に設定される

**テストデータ**: 上記コマンドライン引数

---

#### TC-U-021: --ignore-dependencies フラグのパース

**目的**: --ignore-dependencies フラグが正しくパースされることを確認

**前提条件**: なし

**入力**:
```bash
python main.py execute --phase design --issue 319 --ignore-dependencies
```

**期待結果**:
- `ignore_dependencies` パラメータが `True`
- 他のパラメータは正常に設定される

**テストデータ**: 上記コマンドライン引数

---

#### TC-U-022: --preset オプションのパース

**目的**: --preset オプションが正しくパースされることを確認

**前提条件**: なし

**入力**:
```bash
python main.py execute --preset design-phase --issue 319
```

**期待結果**:
- `preset` パラメータが `'design-phase'`
- プリセットに応じて実行フェーズが決定される

**テストデータ**: 上記コマンドライン引数

---

#### TC-U-023: --preset と --phase の同時指定（異常系）

**目的**: --preset と --phase を同時指定した場合、エラーが発生することを確認

**前提条件**: なし

**入力**:
```bash
python main.py execute --preset design-phase --phase implementation --issue 319
```

**期待結果**:
- エラーメッセージ `"--preset and --phase cannot be used together"` が表示される
- 終了コード 1 で終了

**テストデータ**: 上記コマンドライン引数

---

#### TC-U-024: --skip-dependency-check と --ignore-dependencies の同時指定（異常系）

**目的**: 相互排他的なフラグを同時指定した場合、エラーが発生することを確認

**前提条件**: なし

**入力**:
```bash
python main.py execute --phase design --issue 319 --skip-dependency-check --ignore-dependencies
```

**期待結果**:
- エラーメッセージ `"--skip-dependency-check and --ignore-dependencies are mutually exclusive"` が表示される
- 終了コード 1 で終了

**テストデータ**: 上記コマンドライン引数

---

#### TC-U-025: プリセットマッピング - requirements-only

**目的**: requirements-only プリセットが正しく解釈されることを確認

**前提条件**: なし

**入力**:
```python
preset = 'requirements-only'
```

**期待結果**:
- 実行フェーズが `'requirements'` に設定される

**テストデータ**: 上記プリセット値

---

#### TC-U-026: プリセットマッピング - design-phase

**目的**: design-phase プリセットが正しく解釈されることを確認

**前提条件**: なし

**入力**:
```python
preset = 'design-phase'
```

**期待結果**:
- 実行フェーズが `'design'` に設定される（Phase 1-2を実行）

**テストデータ**: 上記プリセット値

---

#### TC-U-027: プリセットマッピング - implementation-phase

**目的**: implementation-phase プリセットが正しく解釈されることを確認

**前提条件**: なし

**入力**:
```python
preset = 'implementation-phase'
```

**期待結果**:
- 実行フェーズが `'implementation'` に設定される（Phase 1-4を実行）

**テストデータ**: 上記プリセット値

---

#### TC-U-028: プリセットマッピング - full-workflow

**目的**: full-workflow プリセットが正しく解釈されることを確認

**前提条件**: なし

**入力**:
```python
preset = 'full-workflow'
```

**期待結果**:
- 実行フェーズが `'all'` に設定される

**テストデータ**: 上記プリセット値

---

### 2.6 `main.py` - 依存関係チェック統合

#### TC-U-029: 個別フェーズ実行時の依存関係チェック呼び出し

**目的**: phase != 'all' の場合、依存関係チェックが呼び出されることを確認

**前提条件**: メタデータが初期化されている

**入力**:
```python
phase = 'design'
skip_dependency_check = False
ignore_dependencies = False
```

**期待結果**:
- `validate_phase_dependencies()` が呼び出される
- 依存関係が満たされていない場合、エラーメッセージとヒントが表示される

**テストデータ**: モックされたメタデータ

---

#### TC-U-030: phase='all' の場合、依存関係チェックをスキップ

**目的**: phase='all' の場合、個別の依存関係チェックが実行されないことを確認

**前提条件**: メタデータが初期化されている

**入力**:
```python
phase = 'all'
```

**期待結果**:
- `validate_phase_dependencies()` が呼び出されない
- 全フェーズが順次実行される

**テストデータ**: モックされたメタデータ

---

#### TC-U-031: DependencyError 発生時のエラーハンドリング

**目的**: DependencyError 発生時に適切なエラーメッセージとヒントが表示されることを確認

**前提条件**: 依存関係が満たされていない

**入力**:
```python
phase = 'design'
# requirements が未完了
```

**期待結果**:
- エラーメッセージ `"[ERROR] Dependency check failed: Phase 'requirements' must be completed before 'design'"` が表示される
- ヒント1: `"[INFO] Hint: Use --skip-dependency-check to bypass this check."` が表示される
- ヒント2: `"[INFO] Hint: Use --ignore-dependencies to show warnings only."` が表示される
- 終了コード 1 で終了

**テストデータ**: モックされたメタデータ

---

### 2.7 `phases/base_phase.py` - run() メソッド統合

#### TC-U-032: run() メソッド開始時の依存関係チェック

**目的**: run() メソッド開始時に依存関係チェックが実行されることを確認

**前提条件**: フェーズインスタンスが作成されている

**入力**:
```python
phase = DesignPhase(...)
phase.run()
```

**期待結果**:
- `validate_phase_dependencies()` が呼び出される
- 依存関係が満たされている場合、フェーズ実行が継続される

**テストデータ**: モックされたメタデータ

---

#### TC-U-033: run() メソッドでの DependencyError ハンドリング

**目的**: run() メソッド内で DependencyError が発生した場合、適切に処理されることを確認

**前提条件**: 依存関係が満たされていない

**入力**:
```python
phase = DesignPhase(...)
phase.run()
```

**期待結果**:
- エラーメッセージが表示される
- フェーズステータスが `'failed'` に更新される
- GitHub Issue にエラーメッセージが投稿される（モック確認）
- 戻り値が `False`

**テストデータ**: モックされたメタデータ

---

#### TC-U-034: run() メソッドでの skip_check フラグ確認

**目的**: メタデータから skip_dependency_check フラグが正しく読み取られることを確認

**前提条件**: メタデータに skip_dependency_check が設定されている

**入力**:
```python
metadata.data['skip_dependency_check'] = True
phase = DesignPhase(...)
phase.run()
```

**期待結果**:
- `validate_phase_dependencies()` に `skip_check=True` が渡される
- 依存関係チェックがスキップされる

**テストデータ**: skip_dependency_check=True のメタデータ

---

#### TC-U-035: run() メソッドでの ignore_violations フラグ確認

**目的**: メタデータから ignore_dependencies フラグが正しく読み取られることを確認

**前提条件**: メタデータに ignore_dependencies が設定されている

**入力**:
```python
metadata.data['ignore_dependencies'] = True
phase = DesignPhase(...)
phase.run()
```

**期待結果**:
- `validate_phase_dependencies()` に `ignore_violations=True` が渡される
- 依存関係違反時も警告のみ表示して実行継続

**テストデータ**: ignore_dependencies=True のメタデータ

---

## 3. Integrationテストシナリオ

### 3.1 CLI実行フロー全体テスト

#### TC-I-001: 正常フロー - 依存関係満たされた状態でのフェーズ実行

**目的**: 依存関係が満たされている場合、フェーズが正常に実行されることを確認

**前提条件**:
- ワークフローが初期化されている
- requirements フェーズが completed

**テスト手順**:
1. `python main.py init --issue-url https://github.com/test/test/issues/319` を実行
2. metadata.json を編集し、requirements フェーズを completed に設定
3. `python main.py execute --phase design --issue 319` を実行

**期待結果**:
- 終了コード 0
- design フェーズが正常に実行される
- 依存関係チェック成功のメッセージが表示される
- フェーズステータスが completed に更新される

**確認項目**:
- [ ] 終了コード確認
- [ ] 標準出力に `"[INFO] Dependency check passed"` が含まれる
- [ ] metadata.json の design フェーズステータスが completed
- [ ] 成果物ファイルが作成されている

---

#### TC-I-002: 異常フロー - 依存関係未満足でのフェーズ実行エラー

**目的**: 依存関係が満たされていない場合、エラーで実行が停止することを確認

**前提条件**:
- ワークフローが初期化されている
- requirements フェーズが pending

**テスト手順**:
1. `python main.py init --issue-url https://github.com/test/test/issues/319` を実行
2. `python main.py execute --phase design --issue 319` を実行（requirements は pending のまま）

**期待結果**:
- 終了コード 1
- エラーメッセージ `"[ERROR] Dependency check failed: Phase 'requirements' must be completed before 'design'"` が表示される
- ヒントメッセージが表示される
- design フェーズが実行されない

**確認項目**:
- [ ] 終了コード確認
- [ ] エラーメッセージ確認
- [ ] ヒントメッセージ確認
- [ ] design フェーズの成果物が作成されていない
- [ ] metadata.json の design フェーズステータスが pending のまま

---

#### TC-I-003: --skip-dependency-check フラグ使用時の動作

**目的**: --skip-dependency-check フラグを使用した場合、依存関係チェックがスキップされることを確認

**前提条件**:
- ワークフローが初期化されている
- requirements フェーズが pending

**テスト手順**:
1. `python main.py init --issue-url https://github.com/test/test/issues/319` を実行
2. `python main.py execute --phase design --issue 319 --skip-dependency-check` を実行

**期待結果**:
- 警告メッセージ `"[WARNING] Dependency check skipped. Proceeding without validation."` が表示される
- design フェーズの実行が試行される（ファイル不在等で失敗する可能性はある）
- 依存関係チェックによるエラーは発生しない

**確認項目**:
- [ ] 警告メッセージ確認
- [ ] 依存関係チェックエラーが発生しない
- [ ] フェーズ実行が試行される

---

#### TC-I-004: --ignore-dependencies フラグ使用時の動作

**目的**: --ignore-dependencies フラグを使用した場合、警告のみ表示して実行継続することを確認

**前提条件**:
- ワークフローが初期化されている
- requirements フェーズが pending

**テスト手順**:
1. `python main.py init --issue-url https://github.com/test/test/issues/319` を実行
2. `python main.py execute --phase design --issue 319 --ignore-dependencies` を実行

**期待結果**:
- 警告メッセージ `"[WARNING] Dependency violation: Phase 'requirements' is not completed. Continuing anyway."` が表示される
- design フェーズの実行が試行される
- エラーで終了しない

**確認項目**:
- [ ] 警告メッセージ確認
- [ ] 依存関係違反エラーで終了しない
- [ ] フェーズ実行が試行される

---

#### TC-I-005: プリセット実行 - requirements-only

**目的**: requirements-only プリセットで requirements フェーズのみが実行されることを確認

**前提条件**:
- ワークフローが初期化されている

**テスト手順**:
1. `python main.py init --issue-url https://github.com/test/test/issues/319` を実行
2. `python main.py execute --preset requirements-only --issue 319` を実行

**期待結果**:
- requirements フェーズのみが実行される
- 他のフェーズは実行されない
- 終了コード 0

**確認項目**:
- [ ] requirements フェーズの成果物が作成されている
- [ ] metadata.json の requirements ステータスが completed
- [ ] 他のフェーズのステータスが pending のまま

---

#### TC-I-006: プリセット実行 - design-phase

**目的**: design-phase プリセットで Phase 1-2 が実行されることを確認

**前提条件**:
- ワークフローが初期化されている

**テスト手順**:
1. `python main.py init --issue-url https://github.com/test/test/issues/319` を実行
2. `python main.py execute --preset design-phase --issue 319` を実行

**期待結果**:
- requirements と design フェーズが順次実行される
- 依存関係チェックが自動的に有効
- 終了コード 0

**確認項目**:
- [ ] requirements と design の成果物が作成されている
- [ ] metadata.json で両フェーズが completed
- [ ] 他のフェーズは実行されていない

---

#### TC-I-007: プリセット実行 - implementation-phase

**目的**: implementation-phase プリセットで Phase 1-4 が実行されることを確認

**前提条件**:
- ワークフローが初期化されている

**テスト手順**:
1. `python main.py init --issue-url https://github.com/test/test/issues/319` を実行
2. `python main.py execute --preset implementation-phase --issue 319` を実行

**期待結果**:
- requirements, design, test_scenario, implementation フェーズが順次実行される
- 依存関係が自動的に満たされる
- 終了コード 0

**確認項目**:
- [ ] 4つのフェーズすべての成果物が作成されている
- [ ] metadata.json で4つのフェーズが completed
- [ ] Phase 5以降は実行されていない

---

#### TC-I-008: プリセットとphaseの同時指定エラー

**目的**: --preset と --phase を同時指定した場合、エラーで終了することを確認

**前提条件**:
- ワークフローが初期化されている

**テスト手順**:
1. `python main.py execute --preset design-phase --phase implementation --issue 319` を実行

**期待結果**:
- エラーメッセージ `"[ERROR] --preset and --phase cannot be used together"` が表示される
- 終了コード 1
- フェーズが実行されない

**確認項目**:
- [ ] エラーメッセージ確認
- [ ] 終了コード確認
- [ ] フェーズが実行されていない

---

### 3.2 複数依存関係のテスト

#### TC-I-009: 複数依存関係 - すべて満たされている場合

**目的**: implementation フェーズの複数依存関係がすべて満たされている場合、正常実行されることを確認

**前提条件**:
- requirements, design, test_scenario が completed

**テスト手順**:
1. ワークフロー初期化
2. metadata.json を編集し、requirements, design, test_scenario を completed に設定
3. `python main.py execute --phase implementation --issue 319` を実行

**期待結果**:
- 依存関係チェック成功
- implementation フェーズが実行される
- 終了コード 0

**確認項目**:
- [ ] 依存関係チェック成功メッセージ確認
- [ ] implementation フェーズの成果物が作成される
- [ ] metadata.json の implementation ステータスが completed

---

#### TC-I-010: 複数依存関係 - 一部未満足の場合

**目的**: implementation フェーズの依存関係のうち一部が未満足の場合、エラーで停止することを確認

**前提条件**:
- requirements と design は completed、test_scenario は pending

**テスト手順**:
1. ワークフロー初期化
2. metadata.json を編集し、requirements と design を completed に設定（test_scenario は pending のまま）
3. `python main.py execute --phase implementation --issue 319` を実行

**期待結果**:
- エラーメッセージに test_scenario が未完了であることが表示される
- 終了コード 1
- implementation フェーズが実行されない

**確認項目**:
- [ ] エラーメッセージに 'test_scenario' が含まれる
- [ ] 終了コード確認
- [ ] implementation フェーズが実行されていない

---

#### TC-I-011: report フェーズの複雑な依存関係

**目的**: report フェーズの複数依存関係（requirements, design, implementation, testing, documentation）が正しくチェックされることを確認

**前提条件**:
- requirements, design, implementation, testing は completed、documentation は pending

**テスト手順**:
1. ワークフロー初期化
2. metadata.json を編集（上記前提条件に設定）
3. `python main.py execute --phase report --issue 319` を実行

**期待結果**:
- エラーメッセージに documentation が未完了であることが表示される
- 終了コード 1

**確認項目**:
- [ ] エラーメッセージに 'documentation' が含まれる
- [ ] 他の未完了フェーズがある場合、それらも表示される
- [ ] 終了コード確認

---

### 3.3 BasePhase.run() 統合テスト

#### TC-I-012: BasePhase.run() 経由での依存関係チェック

**目的**: BasePhase.run() メソッドを直接呼び出した場合、依存関係チェックが実行されることを確認

**前提条件**:
- requirements フェーズが pending

**テスト手順**:
1. ワークフロー初期化
2. Python コードから DesignPhase インスタンスを作成
3. `phase.run()` を直接呼び出し

**期待結果**:
- 依存関係チェックが実行される
- DependencyError が発生
- フェーズステータスが failed に更新される
- 戻り値が False

**確認項目**:
- [ ] DependencyError 発生確認
- [ ] フェーズステータスが failed
- [ ] GitHub Issue にエラーコメントが投稿される（モック確認）
- [ ] run() の戻り値が False

---

#### TC-I-013: BasePhase.run() でのスキップフラグ動作

**目的**: BasePhase.run() 呼び出し時、メタデータの skip_dependency_check フラグが考慮されることを確認

**前提条件**:
- requirements フェーズが pending
- metadata に skip_dependency_check=True が設定されている

**テスト手順**:
1. ワークフロー初期化
2. metadata.json に `"skip_dependency_check": true` を追加
3. DesignPhase.run() を呼び出し

**期待結果**:
- 依存関係チェックがスキップされる
- フェーズ実行が試行される
- DependencyError が発生しない

**確認項目**:
- [ ] 警告メッセージ `"Dependency check skipped"` 確認
- [ ] DependencyError が発生しない
- [ ] フェーズ実行が試行される

---

### 3.4 エラーハンドリングとリカバリ

#### TC-I-014: 依存関係エラー後のリカバリ

**目的**: 依存関係エラー発生後、依存フェーズを完了させれば次回実行できることを確認

**前提条件**:
- ワークフローが初期化されている

**テスト手順**:
1. `python main.py execute --phase design --issue 319` を実行（エラー発生）
2. `python main.py execute --phase requirements --issue 319` を実行
3. 再度 `python main.py execute --phase design --issue 319` を実行

**期待結果**:
- 1回目はエラーで終了
- 2回目で requirements が completed
- 3回目で design が正常実行される

**確認項目**:
- [ ] 1回目の終了コードが 1
- [ ] 2回目の終了コードが 0
- [ ] 3回目の終了コードが 0
- [ ] metadata.json で両フェーズが completed

---

#### TC-I-015: 相互排他フラグ指定時のエラー

**目的**: --skip-dependency-check と --ignore-dependencies を同時指定した場合、エラーで終了することを確認

**前提条件**:
- ワークフローが初期化されている

**テスト手順**:
1. `python main.py execute --phase design --issue 319 --skip-dependency-check --ignore-dependencies` を実行

**期待結果**:
- エラーメッセージ `"[ERROR] --skip-dependency-check and --ignore-dependencies are mutually exclusive"` が表示される
- 終了コード 1
- フェーズが実行されない

**確認項目**:
- [ ] エラーメッセージ確認
- [ ] 終了コード確認
- [ ] フェーズが実行されていない

---

### 3.5 Phase 0-9 全体の依存関係フロー

#### TC-I-016: 全フェーズ順次実行時の依存関係チェック

**目的**: 全フェーズを順次実行する場合、依存関係チェックが各フェーズで正しく機能することを確認

**前提条件**:
- ワークフローが初期化されている

**テスト手順**:
1. `python main.py execute --preset full-workflow --issue 319` を実行

**期待結果**:
- Phase 0-9 が順次実行される
- 各フェーズ実行前に依存関係チェックが成功する
- すべてのフェーズが completed になる
- 終了コード 0

**確認項目**:
- [ ] すべてのフェーズが順次実行される
- [ ] 各フェーズで依存関係チェック成功メッセージが表示される
- [ ] metadata.json ですべてのフェーズが completed
- [ ] 終了コード 0

---

#### TC-I-017: 途中フェーズからの実行（中断・再開シナリオ）

**目的**: Phase 3 まで実行後、Phase 4 から再開する場合、依存関係が正しく認識されることを確認

**前提条件**:
- requirements, design, test_scenario が completed

**テスト手順**:
1. metadata.json を編集し、Phase 1-3 を completed に設定
2. `python main.py execute --phase implementation --issue 319` を実行

**期待結果**:
- 依存関係チェックが成功
- implementation フェーズが実行される
- 終了コード 0

**確認項目**:
- [ ] 依存関係チェック成功メッセージ確認
- [ ] implementation フェーズが実行される
- [ ] 前フェーズの成果物が読み込まれる

---

### 3.6 パフォーマンステスト

#### TC-I-018: 依存関係チェックの実行時間

**目的**: 依存関係チェックが NFR-1.1（100ms以内）を満たすことを確認

**前提条件**:
- メタデータが初期化されている

**テスト手順**:
1. 各フェーズに対して `validate_phase_dependencies()` を100回実行
2. 実行時間を計測

**期待結果**:
- 平均実行時間が 100ms 以内
- 最大実行時間が 150ms 以内

**確認項目**:
- [ ] 平均実行時間測定
- [ ] 最大実行時間測定
- [ ] メモリ使用量が増加しない

---

## 4. テストデータ

### 4.1 メタデータテストデータ

#### データセット1: 初期状態（すべて pending）

```json
{
  "workflow_version": "1.0.0",
  "issue_number": "319",
  "issue_url": "https://github.com/tielec/infrastructure-as-code/issues/319",
  "issue_title": "[FEATURE] AIワークフロー: フェーズ依存関係の柔軟化と選択的実行機能",
  "phases": {
    "planning": {"status": "pending"},
    "requirements": {"status": "pending"},
    "design": {"status": "pending"},
    "test_scenario": {"status": "pending"},
    "implementation": {"status": "pending"},
    "test_implementation": {"status": "pending"},
    "testing": {"status": "pending"},
    "documentation": {"status": "pending"},
    "report": {"status": "pending"},
    "evaluation": {"status": "pending"}
  }
}
```

#### データセット2: Phase 1 完了状態

```json
{
  "workflow_version": "1.0.0",
  "issue_number": "319",
  "issue_url": "https://github.com/tielec/infrastructure-as-code/issues/319",
  "issue_title": "[FEATURE] AIワークフロー: フェーズ依存関係の柔軟化と選択的実行機能",
  "phases": {
    "planning": {"status": "completed"},
    "requirements": {"status": "completed"},
    "design": {"status": "pending"},
    "test_scenario": {"status": "pending"},
    "implementation": {"status": "pending"},
    "test_implementation": {"status": "pending"},
    "testing": {"status": "pending"},
    "documentation": {"status": "pending"},
    "report": {"status": "pending"},
    "evaluation": {"status": "pending"}
  }
}
```

#### データセット3: Phase 1-3 完了状態

```json
{
  "workflow_version": "1.0.0",
  "issue_number": "319",
  "issue_url": "https://github.com/tielec/infrastructure-as-code/issues/319",
  "issue_title": "[FEATURE] AIワークフロー: フェーズ依存関係の柔軟化と選択的実行機能",
  "phases": {
    "planning": {"status": "completed"},
    "requirements": {"status": "completed"},
    "design": {"status": "completed"},
    "test_scenario": {"status": "completed"},
    "implementation": {"status": "pending"},
    "test_implementation": {"status": "pending"},
    "testing": {"status": "pending"},
    "documentation": {"status": "pending"},
    "report": {"status": "pending"},
    "evaluation": {"status": "pending"}
  }
}
```

#### データセット4: 部分的完了（design 未完了）

```json
{
  "workflow_version": "1.0.0",
  "issue_number": "319",
  "issue_url": "https://github.com/tielec/infrastructure-as-code/issues/319",
  "issue_title": "[FEATURE] AIワークフロー: フェーズ依存関係の柔軟化と選択的実行機能",
  "phases": {
    "planning": {"status": "completed"},
    "requirements": {"status": "completed"},
    "design": {"status": "pending"},
    "test_scenario": {"status": "completed"},
    "implementation": {"status": "pending"},
    "test_implementation": {"status": "pending"},
    "testing": {"status": "pending"},
    "documentation": {"status": "pending"},
    "report": {"status": "pending"},
    "evaluation": {"status": "pending"}
  }
}
```

### 4.2 CLIコマンドテストデータ

#### 正常系コマンド

```bash
# 基本実行
python main.py execute --phase requirements --issue 319

# スキップフラグ
python main.py execute --phase design --issue 319 --skip-dependency-check

# 無視フラグ
python main.py execute --phase design --issue 319 --ignore-dependencies

# プリセット
python main.py execute --preset requirements-only --issue 319
python main.py execute --preset design-phase --issue 319
python main.py execute --preset implementation-phase --issue 319
python main.py execute --preset full-workflow --issue 319
```

#### 異常系コマンド

```bash
# 相互排他フラグ
python main.py execute --phase design --issue 319 --skip-dependency-check --ignore-dependencies

# プリセットとphase同時指定
python main.py execute --preset design-phase --phase implementation --issue 319

# 未知のフェーズ
python main.py execute --phase unknown --issue 319

# 未知のプリセット
python main.py execute --preset unknown-preset --issue 319
```

### 4.3 境界値テストデータ

#### フェーズ名の境界値

- 最短フェーズ名: なし（すべて実在するフェーズ名）
- 最長フェーズ名: `test_implementation` (19文字)
- 空文字列: `""` （エラー期待）
- None: `None` （エラー期待）

#### 依存関係の境界値

- 依存なし: `requirements` (空リスト)
- 単一依存: `design` (1要素)
- 複数依存: `implementation` (3要素), `report` (5要素)

---

## 5. テスト環境要件

### 5.1 ローカル開発環境

#### 必須コンポーネント
- Python 3.8以上
- pytest 6.0以上
- pytest-mock
- pytest-timeout
- click（CLIテスト用）

#### 環境変数
- `GITHUB_TOKEN`: GitHub API アクセス用（Integration テストで必要）

#### ディレクトリ構造
```
scripts/ai-workflow/
├── utils/
│   └── dependency_validator.py
├── phases/
│   └── base_phase.py
├── main.py
├── tests/
│   ├── unit/
│   │   ├── utils/
│   │   │   └── test_dependency_validator.py
│   │   ├── test_main.py
│   │   └── phases/
│   │       └── test_base_phase.py
│   └── integration/
│       └── test_dependency_check_integration.py
└── .ai-workflow/
    └── issue-319/
        └── metadata.json
```

### 5.2 CI/CD環境（Jenkins）

#### 必須要件
- Python 3.8ランタイム
- pytest実行環境
- Gitリポジトリアクセス
- GitHub API アクセス権限

#### テスト実行コマンド
```bash
# Unitテスト
pytest tests/unit/ -v --tb=short

# Integrationテスト
pytest tests/integration/ -v --tb=short

# すべてのテスト
pytest tests/ -v --tb=short --cov=scripts/ai-workflow
```

### 5.3 モック/スタブ要件

#### モックが必要なコンポーネント

1. **MetadataManager**:
   - `get_phase_status()`: フェーズステータスの取得
   - `update_phase_status()`: フェーズステータスの更新
   - `data`: メタデータ辞書のアクセス

2. **GitManager**:
   - Gitコミット・プッシュ操作（Integration テストでは実際の Git 操作はスキップ）

3. **GitHub API**:
   - Issue コメント投稿（モックで代替）
   - 進捗報告（モックで代替）

4. **Claude API**:
   - フェーズ実行時の AI 呼び出し（Integration テストでは必要に応じてモック）

#### スタブが必要なコンポーネント

1. **ファイルシステム**:
   - 一時ディレクトリ（`pytest` の `tmp_path` フィクスチャ使用）
   - メタデータファイル（テンポラリに作成）

2. **成果物ファイル**:
   - Unitテストではファイル存在チェックのみスタブ
   - Integrationテストでは実際のファイル作成を確認

---

## 6. テスト実行計画

### 6.1 テスト実行順序

#### Phase 1: Unitテスト（優先度: 高）
1. `test_dependency_validator.py` 実行
2. `test_main.py` 拡張テスト実行
3. `test_base_phase.py` 拡張テスト実行

**完了条件**: すべての Unit テストが成功し、カバレッジ目標達成

#### Phase 2: Integrationテスト（優先度: 高）
1. `test_dependency_check_integration.py` 実行
2. 既存 E2E テスト修正後の実行

**完了条件**: すべての Integration テストが成功

#### Phase 3: 回帰テスト（優先度: 中）
1. 既存の全 Unit テスト実行
2. 既存の全 Integration テスト実行
3. 既存の全 E2E テスト実行

**完了条件**: すべての既存テストが引き続き成功

### 6.2 テストスケジュール

| フェーズ | テスト種別 | 見積工数 | 担当 |
|---------|-----------|---------|------|
| Phase 1 | Unitテスト作成・実行 | 3日 | 開発者 |
| Phase 2 | Integrationテスト作成・実行 | 2日 | 開発者 |
| Phase 3 | 回帰テスト実行 | 1日 | QA |
| **合計** | | **6日** | |

### 6.3 テスト自動化

#### CI/CDパイプライン統合

```yaml
# Jenkinsfile 例
stage('Test') {
    steps {
        sh 'pytest tests/unit/ -v --tb=short --cov=scripts/ai-workflow'
        sh 'pytest tests/integration/ -v --tb=short'
    }
}
```

#### テストレポート生成

- JUnit XML形式のレポート出力
- カバレッジレポート（HTML形式）
- 失敗時のスクリーンショット・ログ保存

---

## 7. 品質ゲート確認

### チェックリスト

- [x] **Phase 2の戦略に沿ったテストシナリオである**: UNIT_INTEGRATION 戦略に基づき、Unit テストと Integration テストのシナリオを作成
- [x] **主要な正常系がカバーされている**:
  - 依存関係満たされた状態でのフェーズ実行（TC-U-010, TC-I-001）
  - プリセット実行（TC-I-005, TC-I-006, TC-I-007）
  - 全フェーズ順次実行（TC-I-016）
- [x] **主要な異常系がカバーされている**:
  - 依存関係違反（TC-U-011, TC-I-002）
  - 複数依存関係の一部未満足（TC-U-012, TC-I-010）
  - 未知のフェーズ名（TC-U-015）
  - 相互排他フラグの同時指定（TC-U-024, TC-I-015）
- [x] **期待結果が明確である**: すべてのテストケースで具体的な期待結果を記載

---

## 8. リスクとその対策

### リスク1: テストデータ準備の複雑さ

**リスク内容**: 複数依存関係のテストケースでメタデータの準備が複雑

**対策**:
- pytest フィクスチャでテストデータセットを事前定義
- ヘルパー関数でメタデータ生成を簡略化

**影響度**: 中
**発生確率**: 中

---

### リスク2: モックの不完全性

**リスク内容**: MetadataManager のモックが実際の挙動と異なる可能性

**対策**:
- Integration テストで実際の MetadataManager を使用
- Unit テストのモックは最小限に留める

**影響度**: 中
**発生確率**: 低

---

### リスク3: 既存テストの破損

**リスク内容**: 依存関係チェック追加により既存 E2E テストが失敗する可能性

**対策**:
- 既存テスト修正方針を設計書で明記済み（Phase 0-3 完了状態の設定）
- 回帰テストフェーズで全テスト実行

**影響度**: 高
**発生確率**: 高

**緩和策**: 設計書のセクション11.3に従い、既存 E2E テストを体系的に修正

---

## 9. テスト実行基準

### 9.1 テスト開始基準

- [ ] `utils/dependency_validator.py` の実装が完了している
- [ ] `main.py` の CLI オプション追加が完了している
- [ ] `phases/base_phase.py` の修正が完了している
- [ ] テスト環境（Python 3.8、pytest）が準備されている

### 9.2 テスト完了基準

- [ ] すべての Unit テストが成功（35テストケース）
- [ ] すべての Integration テストが成功（18テストケース）
- [ ] ラインカバレッジが 90% 以上
- [ ] ブランチカバレッジが 85% 以上
- [ ] すべての既存テストが引き続き成功（回帰テスト）
- [ ] クリティカルパスのテストケースが 100% 成功

### 9.3 テスト中断基準

- [ ] 実装に重大なバグが発見され、テスト続行不可能
- [ ] テスト環境の障害
- [ ] 設計変更が必要な問題が発見された場合

---

## 10. 付録

### 10.1 テストケースサマリー

| カテゴリ | テストケース数 | 優先度 |
|---------|--------------|--------|
| Unit - PHASE_DEPENDENCIES | 5 | 高 |
| Unit - DependencyError | 3 | 高 |
| Unit - validate_phase_dependencies | 8 | 高 |
| Unit - ユーティリティ関数 | 3 | 中 |
| Unit - main.py CLI | 9 | 高 |
| Unit - main.py 依存関係統合 | 3 | 高 |
| Unit - base_phase.py | 4 | 高 |
| Integration - CLI実行フロー | 8 | 高 |
| Integration - 複数依存関係 | 3 | 高 |
| Integration - BasePhase統合 | 2 | 中 |
| Integration - エラーハンドリング | 2 | 中 |
| Integration - 全体フロー | 2 | 高 |
| Integration - パフォーマンス | 1 | 低 |
| **合計** | **53** | |

### 10.2 カバレッジマトリクス

| 要件ID | テストケース | カバレッジステータス |
|--------|------------|------------------|
| FR-1 | TC-U-001 〜 TC-U-005 | ✓ |
| FR-2 | TC-U-009 〜 TC-U-016 | ✓ |
| FR-3 | TC-U-013, TC-I-003 | ✓ |
| FR-4 | TC-U-014, TC-I-004 | ✓ |
| FR-6 | TC-I-005 〜 TC-I-008 | ✓ |
| FR-7 | TC-U-032 〜 TC-U-035, TC-I-012, TC-I-013 | ✓ |

### 10.3 用語集

| 用語 | 説明 |
|------|------|
| DependencyError | 依存関係違反時に発生するカスタム例外 |
| PHASE_DEPENDENCIES | フェーズ依存関係を定義する定数辞書 |
| skip_check | 依存関係チェックを完全にスキップするフラグ |
| ignore_violations | 依存関係違反時も警告のみ表示するフラグ |
| プリセット | よくある実行パターンの事前定義（requirements-only, design-phase等） |

---

## 変更履歴

| バージョン | 日付 | 変更内容 | 作成者 |
|----------|------|---------|--------|
| 1.0 | 2025-10-12 | 初版作成 | Claude (AI Workflow) |
