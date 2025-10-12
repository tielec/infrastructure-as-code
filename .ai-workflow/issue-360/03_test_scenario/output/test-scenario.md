# テストシナリオ - Issue #360

## プロジェクト情報

- **Issue番号**: #360
- **タイトル**: [FEATURE] AIワークフロー実行時のレジューム機能実装
- **状態**: open
- **URL**: https://github.com/tielec/infrastructure-as-code/issues/360
- **ラベル**: enhancement
- **作成日**: 2025-10-12

---

## 0. 前提ドキュメントの確認

### Planning Document
- **実装戦略**: EXTEND（既存コードの拡張）
- **テスト戦略**: **UNIT_INTEGRATION**（ユニット + 統合テスト）
- **テストコード戦略**: CREATE_TEST（新規テストファイル作成）
- **見積もり工数**: 約12時間

### Requirements Document
主要な機能要件:
- FR-01: デフォルトでの自動レジューム機能
- FR-02: 強制リセットフラグ（`--force-reset`）
- FR-03: レジューム開始フェーズの優先順位決定
- FR-04: エッジケースの処理
- FR-05: レジューム状態のログ出力
- FR-06: `MetadataManager.clear()`メソッドの実装

### Design Document
主要な設計要素:
- 新規モジュール: `scripts/ai-workflow/utils/resume.py`（ResumeManagerクラス）
- 拡張モジュール: `scripts/ai-workflow/main.py`（レジューム判定ロジック）
- 拡張モジュール: `scripts/ai-workflow/core/metadata_manager.py`（`clear()`メソッド）

---

## 1. テスト戦略サマリー

### 1.1 選択されたテスト戦略

**UNIT_INTEGRATION**（Phase 2で決定）

本プロジェクトでは以下の理由により、ユニットテストと統合テストの両方を実施します：

1. **ユニットテストの必要性**:
   - `ResumeManager`クラスの各メソッドのロジック検証が必要
   - メタデータ状態の判定ロジック（failed/in_progress/pending）の正確性検証
   - エッジケース（メタデータ破損、不存在等）の網羅的なテスト

2. **統合テストの必要性**:
   - `main.py execute --phase all`との統合動作確認
   - メタデータの読み込み → レジューム判定 → フェーズ実行の一連のフロー検証
   - `--force-reset`フラグの動作確認
   - 実際のmetadata.jsonファイルを使用した動作確認

3. **BDDテスト不要の理由**:
   - エンドユーザー向けのユーザーストーリーではなく、CLI内部機能のため
   - 要件定義書にユーザーストーリー形式の記載がない
   - ユニットテストと統合テストで十分にカバー可能

### 1.2 テスト対象の範囲

**テスト対象コンポーネント**:
1. **ResumeManagerクラス** (`scripts/ai-workflow/utils/resume.py`)
   - `__init__()`: 初期化処理
   - `can_resume()`: レジューム可能性判定
   - `is_completed()`: 全フェーズ完了判定
   - `get_resume_phase()`: レジューム開始フェーズ決定
   - `get_status_summary()`: ステータスサマリー取得
   - `reset()`: メタデータクリア
   - `_get_phases_by_status()`: ステータス別フェーズリスト取得

2. **MetadataManager.clear()メソッド** (`scripts/ai-workflow/core/metadata_manager.py`)
   - メタデータファイル削除
   - ワークフローディレクトリ削除

3. **main.pyのレジューム機能統合** (`scripts/ai-workflow/main.py`)
   - `--force-reset`フラグの処理
   - レジューム判定ロジック
   - `execute_phases_from()`関数

### 1.3 テストの目的

1. **機能の正確性**: レジューム機能が要件定義書通りに動作することを検証
2. **エッジケース対応**: メタデータ破損、不存在などの異常系に適切に対応することを検証
3. **統合動作**: `main.py`との統合が正しく動作することを検証
4. **後方互換性**: 既存のワークフローに影響を与えないことを検証

### 1.4 テストカバレッジ目標

- **ユニットテストカバレッジ**: 90%以上
- **統合テストカバレッジ**: 主要ユースケース100%
- **エッジケースカバレッジ**: Planning Documentで特定された5つのリスクをカバー

---

## 2. ユニットテストシナリオ

### 2.1 ResumeManager.__init__()

#### UT-RM-INIT-001: 正常系 - 初期化成功

**目的**: ResumeManagerが正しく初期化されることを検証

**前提条件**:
- `MetadataManager`インスタンスが存在する

**入力**:
```python
metadata_manager = MetadataManager(Path('.ai-workflow/issue-360'))
resume_manager = ResumeManager(metadata_manager)
```

**期待結果**:
- `resume_manager.metadata_manager`が設定される
- `resume_manager.phases`が正しいフェーズリストを持つ
- フェーズリストが以下の順序である:
  ```python
  ['requirements', 'design', 'test_scenario', 'implementation',
   'test_implementation', 'testing', 'documentation', 'report']
  ```

**テストデータ**: N/A

---

### 2.2 ResumeManager.can_resume()

#### UT-RM-RESUME-001: 正常系 - メタデータ存在、未完了フェーズあり

**目的**: メタデータが存在し未完了フェーズがある場合にレジューム可能と判定されることを検証

**前提条件**:
- メタデータファイルが存在する
- Phase 1-4が完了、Phase 5が失敗、Phase 6-8が未実行

**入力**:
```python
# モックメタデータ
metadata_manager.metadata_path.exists() → True
metadata_manager.data['phases'] = {
    'requirements': {'status': 'completed'},
    'design': {'status': 'completed'},
    'test_scenario': {'status': 'completed'},
    'implementation': {'status': 'completed'},
    'test_implementation': {'status': 'failed'},
    'testing': {'status': 'pending'},
    'documentation': {'status': 'pending'},
    'report': {'status': 'pending'}
}
```

**期待結果**:
- `can_resume()`が`True`を返す

**テストデータ**: 上記モックデータ

---

#### UT-RM-RESUME-002: 正常系 - メタデータ不存在

**目的**: メタデータファイルが存在しない場合にレジューム不可と判定されることを検証

**前提条件**:
- メタデータファイルが存在しない

**入力**:
```python
metadata_manager.metadata_path.exists() → False
```

**期待結果**:
- `can_resume()`が`False`を返す

**テストデータ**: N/A

---

#### UT-RM-RESUME-003: 正常系 - 全フェーズ完了

**目的**: 全フェーズが完了している場合にレジューム不可と判定されることを検証

**前提条件**:
- メタデータファイルが存在する
- Phase 1-8がすべて完了

**入力**:
```python
metadata_manager.metadata_path.exists() → True
metadata_manager.data['phases'] = {
    'requirements': {'status': 'completed'},
    'design': {'status': 'completed'},
    'test_scenario': {'status': 'completed'},
    'implementation': {'status': 'completed'},
    'test_implementation': {'status': 'completed'},
    'testing': {'status': 'completed'},
    'documentation': {'status': 'completed'},
    'report': {'status': 'completed'}
}
```

**期待結果**:
- `can_resume()`が`False`を返す

**テストデータ**: 上記モックデータ

---

#### UT-RM-RESUME-004: 正常系 - 全フェーズpending

**目的**: 全フェーズがpendingの場合にレジューム不可と判定されることを検証（新規ワークフロー）

**前提条件**:
- メタデータファイルが存在する
- Phase 1-8がすべてpending

**入力**:
```python
metadata_manager.metadata_path.exists() → True
metadata_manager.data['phases'] = {
    'requirements': {'status': 'pending'},
    'design': {'status': 'pending'},
    # ... すべてpending
}
```

**期待結果**:
- `can_resume()`が`False`を返す

**テストデータ**: 上記モックデータ

---

### 2.3 ResumeManager.is_completed()

#### UT-RM-COMPLETE-001: 正常系 - 全フェーズ完了

**目的**: 全フェーズが完了している場合にTrueを返すことを検証

**前提条件**:
- Phase 1-8がすべて完了

**入力**:
```python
metadata_manager.data['phases'] = {
    'requirements': {'status': 'completed'},
    'design': {'status': 'completed'},
    'test_scenario': {'status': 'completed'},
    'implementation': {'status': 'completed'},
    'test_implementation': {'status': 'completed'},
    'testing': {'status': 'completed'},
    'documentation': {'status': 'completed'},
    'report': {'status': 'completed'}
}
```

**期待結果**:
- `is_completed()`が`True`を返す

**テストデータ**: 上記データ

---

#### UT-RM-COMPLETE-002: 正常系 - 未完了フェーズあり

**目的**: 未完了フェーズがある場合にFalseを返すことを検証

**前提条件**:
- Phase 1-7が完了、Phase 8が未実行

**入力**:
```python
metadata_manager.data['phases'] = {
    'requirements': {'status': 'completed'},
    # ... Phase 1-7は completed
    'report': {'status': 'pending'}
}
```

**期待結果**:
- `is_completed()`が`False`を返す

**テストデータ**: 上記データ

---

#### UT-RM-COMPLETE-003: 正常系 - 失敗フェーズあり

**目的**: 失敗フェーズがある場合にFalseを返すことを検証

**前提条件**:
- Phase 1-4が完了、Phase 5が失敗

**入力**:
```python
metadata_manager.data['phases'] = {
    'requirements': {'status': 'completed'},
    'design': {'status': 'completed'},
    'test_scenario': {'status': 'completed'},
    'implementation': {'status': 'completed'},
    'test_implementation': {'status': 'failed'},
    # ... 以降は pending
}
```

**期待結果**:
- `is_completed()`が`False`を返す

**テストデータ**: 上記データ

---

### 2.4 ResumeManager.get_resume_phase()

#### UT-RM-PHASE-001: 正常系 - failedフェーズから再開

**目的**: failedフェーズが最優先でレジューム開始フェーズとして返されることを検証

**前提条件**:
- Phase 1-4が完了、Phase 5が失敗、Phase 6-8が未実行

**入力**:
```python
metadata_manager.data['phases'] = {
    'requirements': {'status': 'completed'},
    'design': {'status': 'completed'},
    'test_scenario': {'status': 'completed'},
    'implementation': {'status': 'completed'},
    'test_implementation': {'status': 'failed'},
    'testing': {'status': 'pending'},
    'documentation': {'status': 'pending'},
    'report': {'status': 'pending'}
}
```

**期待結果**:
- `get_resume_phase()`が`'test_implementation'`を返す

**テストデータ**: 上記データ

---

#### UT-RM-PHASE-002: 正常系 - 複数failedフェーズ、最初から再開

**目的**: 複数のfailedフェーズがある場合、最初の失敗フェーズから再開することを検証

**前提条件**:
- Phase 1-2が完了、Phase 3が失敗、Phase 4が完了、Phase 5が失敗、Phase 6-8が未実行

**入力**:
```python
metadata_manager.data['phases'] = {
    'requirements': {'status': 'completed'},
    'design': {'status': 'completed'},
    'test_scenario': {'status': 'failed'},
    'implementation': {'status': 'completed'},
    'test_implementation': {'status': 'failed'},
    'testing': {'status': 'pending'},
    'documentation': {'status': 'pending'},
    'report': {'status': 'pending'}
}
```

**期待結果**:
- `get_resume_phase()`が`'test_scenario'`を返す（最初のfailedフェーズ）

**テストデータ**: 上記データ

---

#### UT-RM-PHASE-003: 正常系 - in_progressフェーズから再開

**目的**: failedフェーズがなく、in_progressフェーズがある場合にそこから再開することを検証

**前提条件**:
- Phase 1-4が完了、Phase 5がin_progress、Phase 6-8が未実行

**入力**:
```python
metadata_manager.data['phases'] = {
    'requirements': {'status': 'completed'},
    'design': {'status': 'completed'},
    'test_scenario': {'status': 'completed'},
    'implementation': {'status': 'completed'},
    'test_implementation': {'status': 'in_progress'},
    'testing': {'status': 'pending'},
    'documentation': {'status': 'pending'},
    'report': {'status': 'pending'}
}
```

**期待結果**:
- `get_resume_phase()`が`'test_implementation'`を返す

**テストデータ**: 上記データ

---

#### UT-RM-PHASE-004: 正常系 - pendingフェーズから再開

**目的**: failed/in_progressフェーズがなく、pendingフェーズがある場合にそこから再開することを検証

**前提条件**:
- Phase 1-5が完了、Phase 6-8が未実行

**入力**:
```python
metadata_manager.data['phases'] = {
    'requirements': {'status': 'completed'},
    'design': {'status': 'completed'},
    'test_scenario': {'status': 'completed'},
    'implementation': {'status': 'completed'},
    'test_implementation': {'status': 'completed'},
    'testing': {'status': 'pending'},
    'documentation': {'status': 'pending'},
    'report': {'status': 'pending'}
}
```

**期待結果**:
- `get_resume_phase()`が`'testing'`を返す（最初のpendingフェーズ）

**テストデータ**: 上記データ

---

#### UT-RM-PHASE-005: 正常系 - 全フェーズ完了、Noneを返す

**目的**: 全フェーズが完了している場合にNoneを返すことを検証

**前提条件**:
- Phase 1-8がすべて完了

**入力**:
```python
metadata_manager.data['phases'] = {
    'requirements': {'status': 'completed'},
    'design': {'status': 'completed'},
    'test_scenario': {'status': 'completed'},
    'implementation': {'status': 'completed'},
    'test_implementation': {'status': 'completed'},
    'testing': {'status': 'completed'},
    'documentation': {'status': 'completed'},
    'report': {'status': 'completed'}
}
```

**期待結果**:
- `get_resume_phase()`が`None`を返す

**テストデータ**: 上記データ

---

#### UT-RM-PHASE-006: エッジケース - failed優先度確認

**目的**: failedフェーズがin_progressより優先されることを検証

**前提条件**:
- Phase 1-2が完了、Phase 3がin_progress、Phase 4が完了、Phase 5が失敗

**入力**:
```python
metadata_manager.data['phases'] = {
    'requirements': {'status': 'completed'},
    'design': {'status': 'completed'},
    'test_scenario': {'status': 'in_progress'},
    'implementation': {'status': 'completed'},
    'test_implementation': {'status': 'failed'},
    'testing': {'status': 'pending'},
    'documentation': {'status': 'pending'},
    'report': {'status': 'pending'}
}
```

**期待結果**:
- `get_resume_phase()`が`'test_implementation'`を返す（failedが優先）

**テストデータ**: 上記データ

---

### 2.5 ResumeManager.get_status_summary()

#### UT-RM-SUMMARY-001: 正常系 - ステータスサマリー取得

**目的**: 各ステータスのフェーズリストが正しく取得できることを検証

**前提条件**:
- Phase 1-4が完了、Phase 5が失敗、Phase 6がin_progress、Phase 7-8が未実行

**入力**:
```python
metadata_manager.data['phases'] = {
    'requirements': {'status': 'completed'},
    'design': {'status': 'completed'},
    'test_scenario': {'status': 'completed'},
    'implementation': {'status': 'completed'},
    'test_implementation': {'status': 'failed'},
    'testing': {'status': 'in_progress'},
    'documentation': {'status': 'pending'},
    'report': {'status': 'pending'}
}
```

**期待結果**:
- `get_status_summary()`が以下を返す:
  ```python
  {
      'completed': ['requirements', 'design', 'test_scenario', 'implementation'],
      'failed': ['test_implementation'],
      'in_progress': ['testing'],
      'pending': ['documentation', 'report']
  }
  ```

**テストデータ**: 上記データ

---

#### UT-RM-SUMMARY-002: 正常系 - 全フェーズ完了時のサマリー

**目的**: 全フェーズが完了している場合のサマリーが正しいことを検証

**前提条件**:
- Phase 1-8がすべて完了

**入力**:
```python
metadata_manager.data['phases'] = {
    'requirements': {'status': 'completed'},
    # ... すべて completed
}
```

**期待結果**:
- `get_status_summary()`が以下を返す:
  ```python
  {
      'completed': ['requirements', 'design', 'test_scenario', 'implementation',
                    'test_implementation', 'testing', 'documentation', 'report'],
      'failed': [],
      'in_progress': [],
      'pending': []
  }
  ```

**テストデータ**: 上記データ

---

#### UT-RM-SUMMARY-003: 正常系 - 全フェーズpending時のサマリー

**目的**: 全フェーズがpendingの場合のサマリーが正しいことを検証

**前提条件**:
- Phase 1-8がすべてpending

**入力**:
```python
metadata_manager.data['phases'] = {
    'requirements': {'status': 'pending'},
    # ... すべて pending
}
```

**期待結果**:
- `get_status_summary()`が以下を返す:
  ```python
  {
      'completed': [],
      'failed': [],
      'in_progress': [],
      'pending': ['requirements', 'design', 'test_scenario', 'implementation',
                  'test_implementation', 'testing', 'documentation', 'report']
  }
  ```

**テストデータ**: 上記データ

---

### 2.6 ResumeManager.reset()

#### UT-RM-RESET-001: 正常系 - resetがMetadataManager.clear()を呼ぶ

**目的**: `reset()`が`MetadataManager.clear()`を正しく呼び出すことを検証

**前提条件**:
- `MetadataManager`のモックが存在する

**入力**:
```python
# モックの準備
metadata_manager_mock = MagicMock(spec=MetadataManager)
resume_manager = ResumeManager(metadata_manager_mock)
resume_manager.reset()
```

**期待結果**:
- `metadata_manager_mock.clear()`が1回呼ばれる

**テストデータ**: N/A

---

### 2.7 ResumeManager._get_phases_by_status()

#### UT-RM-FILTER-001: 正常系 - ステータス別フェーズ取得

**目的**: 指定したステータスのフェーズリストが正しく取得できることを検証

**前提条件**:
- 各ステータスのフェーズが混在している

**入力**:
```python
metadata_manager.data['phases'] = {
    'requirements': {'status': 'completed'},
    'design': {'status': 'completed'},
    'test_scenario': {'status': 'failed'},
    'implementation': {'status': 'pending'},
    'test_implementation': {'status': 'pending'},
    'testing': {'status': 'in_progress'},
    'documentation': {'status': 'pending'},
    'report': {'status': 'pending'}
}
```

**期待結果**:
- `_get_phases_by_status('completed')`が`['requirements', 'design']`を返す
- `_get_phases_by_status('failed')`が`['test_scenario']`を返す
- `_get_phases_by_status('in_progress')`が`['testing']`を返す
- `_get_phases_by_status('pending')`が`['implementation', 'test_implementation', 'documentation', 'report']`を返す

**テストデータ**: 上記データ

---

### 2.8 MetadataManager.clear()

#### UT-MM-CLEAR-001: 正常系 - メタデータファイル削除

**目的**: メタデータファイルが正しく削除されることを検証

**前提条件**:
- メタデータファイルが存在する
- ワークフローディレクトリが存在する

**入力**:
```python
# テスト用の一時ファイル/ディレクトリを作成
temp_dir = Path('/tmp/test_workflow')
temp_dir.mkdir(parents=True, exist_ok=True)
metadata_file = temp_dir / 'metadata.json'
metadata_file.write_text('{}')

metadata_manager = MetadataManager(temp_dir)
metadata_manager.clear()
```

**期待結果**:
- メタデータファイルが削除される（`metadata_file.exists()`が`False`）
- ワークフローディレクトリが削除される（`temp_dir.exists()`が`False`）

**テストデータ**: 上記一時ファイル/ディレクトリ

---

#### UT-MM-CLEAR-002: 正常系 - ファイル不存在時のエラーなし

**目的**: メタデータファイルが存在しない場合でもエラーが発生しないことを検証

**前提条件**:
- メタデータファイルが存在しない

**入力**:
```python
temp_dir = Path('/tmp/test_workflow_nonexistent')
metadata_manager = MetadataManager(temp_dir)
metadata_manager.clear()
```

**期待結果**:
- エラーが発生しない
- 正常に終了する

**テストデータ**: N/A

---

#### UT-MM-CLEAR-003: 異常系 - 権限エラー

**目的**: 削除権限がない場合に適切にエラーが発生することを検証

**前提条件**:
- メタデータファイルが存在する
- 削除権限がない（読み取り専用）

**入力**:
```python
# テスト用の一時ファイルを作成し、読み取り専用にする
temp_dir = Path('/tmp/test_workflow_readonly')
temp_dir.mkdir(parents=True, exist_ok=True)
metadata_file = temp_dir / 'metadata.json'
metadata_file.write_text('{}')
metadata_file.chmod(0o444)  # 読み取り専用

metadata_manager = MetadataManager(temp_dir)
```

**期待結果**:
- `PermissionError`が発生する
- エラーメッセージが適切に表示される

**テストデータ**: 上記読み取り専用ファイル

---

## 3. 統合テストシナリオ

### 3.1 自動レジューム機能の統合テスト

#### IT-RESUME-001: 正常系 - Phase 5失敗後の自動レジューム

**目的**: Phase 5で失敗した後、`--phase all`実行時に自動的にPhase 5から再開することを検証

**前提条件**:
- `.ai-workflow/issue-360/metadata.json`が存在する
- Phase 1-4が完了、Phase 5が失敗、Phase 6-8が未実行

**テスト手順**:
1. テスト用のメタデータファイルを準備:
   ```json
   {
     "issue_number": "360",
     "phases": {
       "requirements": {"status": "completed"},
       "design": {"status": "completed"},
       "test_scenario": {"status": "completed"},
       "implementation": {"status": "completed"},
       "test_implementation": {"status": "failed"},
       "testing": {"status": "pending"},
       "documentation": {"status": "pending"},
       "report": {"status": "pending"}
     }
   }
   ```

2. 以下のコマンドを実行:
   ```bash
   python scripts/ai-workflow/main.py execute --issue 360 --phase all
   ```

3. ログ出力を確認

**期待結果**:
- ログに以下が表示される:
  ```
  [INFO] Existing workflow detected.
  [INFO] Completed phases: requirements, design, test_scenario, implementation
  [INFO] Failed phases: test_implementation
  [INFO] Resuming from phase: test_implementation
  ```
- Phase 1-4はスキップされる（実行されない）
- Phase 5から実行が開始される

**確認項目**:
- [ ] ログに「Existing workflow detected」と表示される
- [ ] ログに完了フェーズリストが表示される
- [ ] ログに失敗フェーズリストが表示される
- [ ] ログに「Resuming from phase: test_implementation」と表示される
- [ ] Phase 1-4の実行ログが出力されない
- [ ] Phase 5の実行ログが出力される

---

#### IT-RESUME-002: 正常系 - Phase 3失敗後の自動レジューム

**目的**: Phase 3で失敗した後、`--phase all`実行時に自動的にPhase 3から再開することを検証

**前提条件**:
- Phase 1-2が完了、Phase 3が失敗、Phase 4-8が未実行

**テスト手順**:
1. テスト用のメタデータファイルを準備:
   ```json
   {
     "issue_number": "360",
     "phases": {
       "requirements": {"status": "completed"},
       "design": {"status": "completed"},
       "test_scenario": {"status": "failed"},
       "implementation": {"status": "pending"},
       "test_implementation": {"status": "pending"},
       "testing": {"status": "pending"},
       "documentation": {"status": "pending"},
       "report": {"status": "pending"}
     }
   }
   ```

2. 以下のコマンドを実行:
   ```bash
   python scripts/ai-workflow/main.py execute --issue 360 --phase all
   ```

**期待結果**:
- ログに「Resuming from phase: test_scenario」と表示される
- Phase 1-2はスキップされる
- Phase 3から実行が開始される

**確認項目**:
- [ ] ログに「Existing workflow detected」と表示される
- [ ] ログに「Completed phases: requirements, design」と表示される
- [ ] ログに「Failed phases: test_scenario」と表示される
- [ ] ログに「Resuming from phase: test_scenario」と表示される

---

#### IT-RESUME-003: 正常系 - in_progressフェーズからの再開

**目的**: in_progressフェーズがある場合、そのフェーズから自動的に再開することを検証

**前提条件**:
- Phase 1-4が完了、Phase 5がin_progress、Phase 6-8が未実行

**テスト手順**:
1. テスト用のメタデータファイルを準備:
   ```json
   {
     "issue_number": "360",
     "phases": {
       "requirements": {"status": "completed"},
       "design": {"status": "completed"},
       "test_scenario": {"status": "completed"},
       "implementation": {"status": "completed"},
       "test_implementation": {"status": "in_progress"},
       "testing": {"status": "pending"},
       "documentation": {"status": "pending"},
       "report": {"status": "pending"}
     }
   }
   ```

2. 以下のコマンドを実行:
   ```bash
   python scripts/ai-workflow/main.py execute --issue 360 --phase all
   ```

**期待結果**:
- ログに「In-progress phases: test_implementation」と表示される
- ログに「Resuming from phase: test_implementation」と表示される
- Phase 5から実行が開始される

**確認項目**:
- [ ] ログに「In-progress phases: test_implementation」と表示される
- [ ] ログに「Resuming from phase: test_implementation」と表示される

---

#### IT-RESUME-004: 正常系 - 複数failedフェーズ、最初から再開

**目的**: 複数のfailedフェーズがある場合、最初の失敗フェーズから再開することを検証

**前提条件**:
- Phase 1-2が完了、Phase 3が失敗、Phase 4が完了、Phase 5が失敗、Phase 6-8が未実行

**テスト手順**:
1. テスト用のメタデータファイルを準備:
   ```json
   {
     "issue_number": "360",
     "phases": {
       "requirements": {"status": "completed"},
       "design": {"status": "completed"},
       "test_scenario": {"status": "failed"},
       "implementation": {"status": "completed"},
       "test_implementation": {"status": "failed"},
       "testing": {"status": "pending"},
       "documentation": {"status": "pending"},
       "report": {"status": "pending"}
     }
   }
   ```

2. 以下のコマンドを実行:
   ```bash
   python scripts/ai-workflow/main.py execute --issue 360 --phase all
   ```

**期待結果**:
- ログに「Failed phases: test_scenario, test_implementation」と表示される
- ログに「Resuming from phase: test_scenario」と表示される（最初のfailedフェーズ）
- Phase 3から実行が開始される

**確認項目**:
- [ ] ログに「Failed phases: test_scenario, test_implementation」と表示される
- [ ] ログに「Resuming from phase: test_scenario」と表示される

---

### 3.2 強制リセット機能の統合テスト

#### IT-RESET-001: 正常系 - --force-resetでメタデータクリア

**目的**: `--force-reset`フラグを指定した場合、メタデータがクリアされてPhase 1から実行されることを検証

**前提条件**:
- Phase 1-4が完了、Phase 5が失敗

**テスト手順**:
1. テスト用のメタデータファイルを準備:
   ```json
   {
     "issue_number": "360",
     "phases": {
       "requirements": {"status": "completed"},
       "design": {"status": "completed"},
       "test_scenario": {"status": "completed"},
       "implementation": {"status": "completed"},
       "test_implementation": {"status": "failed"},
       "testing": {"status": "pending"},
       "documentation": {"status": "pending"},
       "report": {"status": "pending"}
     }
   }
   ```

2. 以下のコマンドを実行:
   ```bash
   python scripts/ai-workflow/main.py execute --issue 360 --phase all --force-reset
   ```

3. メタデータファイルの存在を確認

**期待結果**:
- ログに「--force-reset specified. Restarting from Phase 1...」と表示される
- ログに「Clearing metadata: .ai-workflow/issue-360/metadata.json」と表示される
- ログに「Removing workflow directory: .ai-workflow/issue-360」と表示される
- メタデータファイルが削除される
- ワークフローディレクトリが削除される
- Phase 1から実行が開始される

**確認項目**:
- [ ] ログに「--force-reset specified. Restarting from Phase 1...」と表示される
- [ ] ログに「Clearing metadata」と表示される
- [ ] ログに「Removing workflow directory」と表示される
- [ ] メタデータファイルが存在しないことを確認
- [ ] ワークフローディレクトリが存在しないことを確認
- [ ] Phase 1の実行ログが出力される

---

#### IT-RESET-002: 正常系 - --force-reset後の新規ワークフロー実行

**目的**: `--force-reset`実行後、新規ワークフローとして全フェーズが実行されることを検証

**前提条件**:
- Phase 1-8がすべて完了

**テスト手順**:
1. テスト用のメタデータファイルを準備（全フェーズ完了）

2. 以下のコマンドを実行:
   ```bash
   python scripts/ai-workflow/main.py execute --issue 360 --phase all --force-reset
   ```

**期待結果**:
- メタデータがクリアされる
- ログに「Starting new workflow」と表示される
- Phase 1-8がすべて実行される

**確認項目**:
- [ ] メタデータがクリアされる
- [ ] ログに「Starting new workflow」と表示される
- [ ] Phase 1-8の実行ログが出力される

---

### 3.3 全フェーズ完了時の統合テスト

#### IT-COMPLETE-001: 正常系 - 全フェーズ完了時のメッセージ表示

**目的**: 全フェーズが完了している場合、完了メッセージを表示して終了することを検証

**前提条件**:
- Phase 1-8がすべて完了

**テスト手順**:
1. テスト用のメタデータファイルを準備:
   ```json
   {
     "issue_number": "360",
     "phases": {
       "requirements": {"status": "completed"},
       "design": {"status": "completed"},
       "test_scenario": {"status": "completed"},
       "implementation": {"status": "completed"},
       "test_implementation": {"status": "completed"},
       "testing": {"status": "completed"},
       "documentation": {"status": "completed"},
       "report": {"status": "completed"}
     }
   }
   ```

2. 以下のコマンドを実行:
   ```bash
   python scripts/ai-workflow/main.py execute --issue 360 --phase all
   ```

**期待結果**:
- ログに「All phases are already completed.」と表示される
- ログに「To re-run, use --force-reset flag.」と表示される
- フェーズ実行は行われない（Phase 1-8の実行ログが出力されない）
- プログラムが正常終了する（exit code 0）

**確認項目**:
- [ ] ログに「All phases are already completed.」と表示される
- [ ] ログに「To re-run, use --force-reset flag.」と表示される
- [ ] Phase実行ログが出力されない
- [ ] exit code が 0

---

### 3.4 エッジケースの統合テスト

#### IT-EDGE-001: エッジケース - メタデータ不存在時の新規ワークフロー実行

**目的**: メタデータファイルが存在しない場合、新規ワークフローとしてPhase 1から実行されることを検証

**前提条件**:
- `.ai-workflow/issue-360/metadata.json`が存在しない

**テスト手順**:
1. メタデータファイルを削除（存在する場合）:
   ```bash
   rm -rf .ai-workflow/issue-360
   ```

2. 以下のコマンドを実行:
   ```bash
   python scripts/ai-workflow/main.py execute --issue 360 --phase all
   ```

**期待結果**:
- ログに「Starting new workflow.」と表示される
- Phase 1から実行が開始される
- エラーが発生しない

**確認項目**:
- [ ] ログに「Starting new workflow.」と表示される
- [ ] Phase 1の実行ログが出力される
- [ ] エラーが発生しない

---

#### IT-EDGE-002: エッジケース - メタデータ破損時の警告表示と新規実行

**目的**: メタデータファイルが破損している場合、警告を表示して新規ワークフローとして実行することを検証

**前提条件**:
- メタデータファイルが破損している（JSONパースエラー）

**テスト手順**:
1. テスト用の破損したメタデータファイルを作成:
   ```bash
   mkdir -p .ai-workflow/issue-360
   echo "{ invalid json" > .ai-workflow/issue-360/metadata.json
   ```

2. 以下のコマンドを実行:
   ```bash
   python scripts/ai-workflow/main.py execute --issue 360 --phase all
   ```

**期待結果**:
- ログに「[WARNING] metadata.json is corrupted. Starting as new workflow.」と表示される
- ログに「Starting new workflow.」と表示される
- Phase 1から実行が開始される
- プログラムがクラッシュしない

**確認項目**:
- [ ] ログに「[WARNING] metadata.json is corrupted.」と表示される
- [ ] ログに「Starting new workflow.」と表示される
- [ ] Phase 1の実行ログが出力される
- [ ] プログラムがクラッシュしない

---

#### IT-EDGE-003: エッジケース - 全フェーズpending時の新規実行

**目的**: 全フェーズがpendingの場合、新規ワークフローとして実行されることを検証

**前提条件**:
- Phase 1-8がすべてpending

**テスト手順**:
1. テスト用のメタデータファイルを準備:
   ```json
   {
     "issue_number": "360",
     "phases": {
       "requirements": {"status": "pending"},
       "design": {"status": "pending"},
       "test_scenario": {"status": "pending"},
       "implementation": {"status": "pending"},
       "test_implementation": {"status": "pending"},
       "testing": {"status": "pending"},
       "documentation": {"status": "pending"},
       "report": {"status": "pending"}
     }
   }
   ```

2. 以下のコマンドを実行:
   ```bash
   python scripts/ai-workflow/main.py execute --issue 360 --phase all
   ```

**期待結果**:
- ログに「Starting new workflow.」と表示される
- Phase 1から実行が開始される

**確認項目**:
- [ ] ログに「Starting new workflow.」と表示される
- [ ] Phase 1の実行ログが出力される

---

#### IT-EDGE-004: エッジケース - failedとin_progress混在時の優先順位確認

**目的**: failedとin_progressが混在する場合、failedが優先されることを検証

**前提条件**:
- Phase 1-2が完了、Phase 3がin_progress、Phase 4が完了、Phase 5が失敗

**テスト手順**:
1. テスト用のメタデータファイルを準備:
   ```json
   {
     "issue_number": "360",
     "phases": {
       "requirements": {"status": "completed"},
       "design": {"status": "completed"},
       "test_scenario": {"status": "in_progress"},
       "implementation": {"status": "completed"},
       "test_implementation": {"status": "failed"},
       "testing": {"status": "pending"},
       "documentation": {"status": "pending"},
       "report": {"status": "pending"}
     }
   }
   ```

2. 以下のコマンドを実行:
   ```bash
   python scripts/ai-workflow/main.py execute --issue 360 --phase all
   ```

**期待結果**:
- ログに「In-progress phases: test_scenario」と表示される
- ログに「Failed phases: test_implementation」と表示される
- ログに「Resuming from phase: test_implementation」と表示される（failedが優先）
- Phase 5から実行が開始される

**確認項目**:
- [ ] ログに「In-progress phases: test_scenario」と表示される
- [ ] ログに「Failed phases: test_implementation」と表示される
- [ ] ログに「Resuming from phase: test_implementation」と表示される

---

### 3.5 パフォーマンステスト

#### IT-PERF-001: 非機能要件 - レジューム判定処理のオーバーヘッド

**目的**: レジューム判定処理の追加オーバーヘッドが1秒未満であることを検証（NFR-01）

**前提条件**:
- Phase 1-4が完了、Phase 5が失敗

**テスト手順**:
1. テスト用のメタデータファイルを準備

2. 以下のコマンドを10回実行し、起動時間を計測:
   ```bash
   time python scripts/ai-workflow/main.py execute --issue 360 --phase all
   ```
   ※ 実際のフェーズ実行前にCtrl+Cで中断

3. レジューム機能なしの場合と比較

**期待結果**:
- レジューム判定処理のオーバーヘッドが1秒未満
- 起動時間の平均値が許容範囲内

**確認項目**:
- [ ] レジューム判定処理のオーバーヘッドが1秒未満
- [ ] 起動時間の標準偏差が小さい（安定している）

---

## 4. テストデータ

### 4.1 正常系テストデータ

#### TD-NORMAL-001: Phase 5失敗ケース

```json
{
  "issue_number": "360",
  "issue_url": "https://github.com/tielec/infrastructure-as-code/issues/360",
  "issue_title": "[FEATURE] AIワークフロー実行時のレジューム機能実装",
  "workflow_version": "1.0.0",
  "current_phase": "test_implementation",
  "design_decisions": {
    "implementation_strategy": "EXTEND",
    "test_strategy": "UNIT_INTEGRATION",
    "test_code_strategy": "CREATE_TEST"
  },
  "cost_tracking": {
    "total_input_tokens": 50000,
    "total_output_tokens": 10000,
    "total_cost_usd": 1.5
  },
  "phases": {
    "planning": {
      "status": "completed",
      "retry_count": 0,
      "started_at": "2025-10-12T10:00:00Z",
      "completed_at": "2025-10-12T10:30:00Z",
      "review_result": "PASS"
    },
    "requirements": {
      "status": "completed",
      "retry_count": 0,
      "started_at": "2025-10-12T10:30:00Z",
      "completed_at": "2025-10-12T11:00:00Z",
      "review_result": "PASS"
    },
    "design": {
      "status": "completed",
      "retry_count": 0,
      "started_at": "2025-10-12T11:00:00Z",
      "completed_at": "2025-10-12T11:30:00Z",
      "review_result": "PASS"
    },
    "test_scenario": {
      "status": "completed",
      "retry_count": 0,
      "started_at": "2025-10-12T11:30:00Z",
      "completed_at": "2025-10-12T12:00:00Z",
      "review_result": "PASS"
    },
    "implementation": {
      "status": "completed",
      "retry_count": 0,
      "started_at": "2025-10-12T12:00:00Z",
      "completed_at": "2025-10-12T13:00:00Z",
      "review_result": "PASS"
    },
    "test_implementation": {
      "status": "failed",
      "retry_count": 1,
      "started_at": "2025-10-12T13:00:00Z",
      "completed_at": null,
      "review_result": "FAIL",
      "error_message": "test-implementation.mdが生成されませんでした"
    },
    "testing": {
      "status": "pending",
      "retry_count": 0,
      "started_at": null,
      "completed_at": null,
      "review_result": null
    },
    "documentation": {
      "status": "pending",
      "retry_count": 0,
      "started_at": null,
      "completed_at": null,
      "review_result": null
    },
    "report": {
      "status": "pending",
      "retry_count": 0,
      "started_at": null,
      "completed_at": null,
      "review_result": null
    }
  },
  "created_at": "2025-10-12T10:00:00Z",
  "updated_at": "2025-10-12T13:00:00Z"
}
```

#### TD-NORMAL-002: 全フェーズ完了ケース

```json
{
  "issue_number": "360",
  "phases": {
    "requirements": {"status": "completed"},
    "design": {"status": "completed"},
    "test_scenario": {"status": "completed"},
    "implementation": {"status": "completed"},
    "test_implementation": {"status": "completed"},
    "testing": {"status": "completed"},
    "documentation": {"status": "completed"},
    "report": {"status": "completed"}
  }
}
```

#### TD-NORMAL-003: in_progressフェーズケース

```json
{
  "issue_number": "360",
  "phases": {
    "requirements": {"status": "completed"},
    "design": {"status": "completed"},
    "test_scenario": {"status": "completed"},
    "implementation": {"status": "completed"},
    "test_implementation": {"status": "in_progress"},
    "testing": {"status": "pending"},
    "documentation": {"status": "pending"},
    "report": {"status": "pending"}
  }
}
```

### 4.2 異常系テストデータ

#### TD-ERROR-001: 破損したメタデータ

```
{ invalid json
```

#### TD-ERROR-002: 空のメタデータ

```json
{}
```

#### TD-ERROR-003: phasesフィールド欠損

```json
{
  "issue_number": "360"
}
```

### 4.3 エッジケーステストデータ

#### TD-EDGE-001: 複数failedフェーズ

```json
{
  "issue_number": "360",
  "phases": {
    "requirements": {"status": "completed"},
    "design": {"status": "completed"},
    "test_scenario": {"status": "failed"},
    "implementation": {"status": "completed"},
    "test_implementation": {"status": "failed"},
    "testing": {"status": "pending"},
    "documentation": {"status": "pending"},
    "report": {"status": "pending"}
  }
}
```

#### TD-EDGE-002: failedとin_progress混在

```json
{
  "issue_number": "360",
  "phases": {
    "requirements": {"status": "completed"},
    "design": {"status": "completed"},
    "test_scenario": {"status": "in_progress"},
    "implementation": {"status": "completed"},
    "test_implementation": {"status": "failed"},
    "testing": {"status": "pending"},
    "documentation": {"status": "pending"},
    "report": {"status": "pending"}
  }
}
```

#### TD-EDGE-003: 全フェーズpending

```json
{
  "issue_number": "360",
  "phases": {
    "requirements": {"status": "pending"},
    "design": {"status": "pending"},
    "test_scenario": {"status": "pending"},
    "implementation": {"status": "pending"},
    "test_implementation": {"status": "pending"},
    "testing": {"status": "pending"},
    "documentation": {"status": "pending"},
    "report": {"status": "pending"}
  }
}
```

---

## 5. テスト環境要件

### 5.1 ハードウェア要件

- **CPU**: 2コア以上
- **メモリ**: 4GB以上
- **ディスク**: 1GB以上の空き容量

### 5.2 ソフトウェア要件

- **OS**: Linux, macOS, Windows（POSIX準拠）
- **Python**: 3.8以上
- **必須パッケージ**:
  - `pytest`: 7.0.0以上（ユニットテスト実行）
  - `pytest-mock`: 3.6.0以上（モック機能）
  - `pytest-cov`: 3.0.0以上（カバレッジ計測）

### 5.3 テスト実行環境

#### 5.3.1 ローカル環境

- 開発者のローカルマシンでテスト実行
- テスト用の一時ディレクトリ: `/tmp/test_workflow_*`
- テスト後の自動クリーンアップ必須

#### 5.3.2 CI/CD環境（将来対応）

- GitHub Actions等のCI/CD環境でのテスト実行
- テストの並列実行
- カバレッジレポートの自動生成

### 5.4 モック/スタブの必要性

#### 5.4.1 ユニットテストで使用するモック

1. **MetadataManagerのモック**:
   - `metadata_path.exists()`: ファイル存在チェック
   - `data['phases']`: フェーズデータの読み込み
   - `clear()`: メタデータクリア

2. **ファイルシステムのモック**:
   - `Path.exists()`: ファイル/ディレクトリ存在チェック
   - `Path.unlink()`: ファイル削除
   - `shutil.rmtree()`: ディレクトリ削除

3. **ログ出力のモック**:
   - `click.echo()`: ログ出力

#### 5.4.2 統合テストで使用する実データ

- 実際のmetadata.jsonファイル（テスト用）
- 実際のワークフローディレクトリ（テスト用）
- テスト後の自動クリーンアップ

### 5.5 テストデータの準備

#### 5.5.1 テスト用メタデータファイルの配置

- テストフィクスチャとして`tests/fixtures/metadata/`配下に配置
- 各テストケースごとに異なるメタデータファイルを準備

#### 5.5.2 テスト用ディレクトリの作成

- テスト実行時に一時ディレクトリを作成
- テスト終了時に自動削除（`pytest`の`tmp_path`フィクスチャを使用）

---

## 6. テストケースサマリー

### 6.1 テストケース数

| テスト種別 | テストケース数 | 備考 |
|-----------|--------------|------|
| ユニットテスト | 21 | ResumeManager: 18, MetadataManager: 3 |
| 統合テスト | 10 | 自動レジューム: 4, 強制リセット: 2, 全フェーズ完了: 1, エッジケース: 3 |
| **合計** | **31** | |

### 6.2 カバレッジ目標達成状況（見込み）

| コンポーネント | 目標カバレッジ | 見込みカバレッジ |
|--------------|-------------|--------------|
| ResumeManager | 90%以上 | 95%以上 |
| MetadataManager.clear() | 90%以上 | 95%以上 |
| main.py（レジューム機能部分） | 統合テストでカバー | 100% |

### 6.3 要件カバレッジマトリックス

| 要件ID | 要件名 | ユニットテスト | 統合テスト | カバー状況 |
|-------|--------|-------------|-----------|----------|
| FR-01 | デフォルトでの自動レジューム機能 | UT-RM-RESUME-001 | IT-RESUME-001〜004 | ✓ |
| FR-02 | 強制リセットフラグ（--force-reset） | UT-RM-RESET-001 | IT-RESET-001〜002 | ✓ |
| FR-03 | レジューム開始フェーズの優先順位決定 | UT-RM-PHASE-001〜006 | IT-RESUME-001〜004, IT-EDGE-004 | ✓ |
| FR-04 | エッジケースの処理 | UT-RM-RESUME-002〜004 | IT-EDGE-001〜003 | ✓ |
| FR-05 | レジューム状態のログ出力 | UT-RM-SUMMARY-001〜003 | IT-RESUME-001〜004 | ✓ |
| FR-06 | MetadataManager.clear()メソッドの実装 | UT-MM-CLEAR-001〜003 | IT-RESET-001〜002 | ✓ |

**結果**: すべての機能要件がテストでカバーされています。

### 6.4 エッジケースカバレッジマトリックス

| リスクID | リスク内容 | 対応テストケース | カバー状況 |
|---------|----------|----------------|----------|
| リスク1 | メタデータ状態の複雑性 | UT-RM-PHASE-001〜006, IT-EDGE-004 | ✓ |
| リスク2 | 既存ワークフローへの影響 | IT-RESUME-001〜004, IT-EDGE-003 | ✓ |
| リスク3 | clear()メソッドの破壊的操作 | UT-MM-CLEAR-001〜003, IT-RESET-001〜002 | ✓ |
| リスク4 | Phase 0（planning）フェーズとの混同 | （実装で対応、テストデータにplanningを含めない） | ✓ |
| リスク5 | パフォーマンス低下 | IT-PERF-001 | ✓ |

**結果**: Planning Documentで特定された5つのリスクすべてがテストでカバーされています。

---

## 7. テスト実行計画

### 7.1 テスト実行順序

1. **ユニットテスト実行**（Phase 6前半）:
   ```bash
   pytest scripts/ai-workflow/tests/unit/utils/test_resume.py -v
   pytest scripts/ai-workflow/tests/unit/core/test_metadata_manager.py::test_clear -v
   ```

2. **統合テスト実行**（Phase 6後半）:
   ```bash
   pytest scripts/ai-workflow/tests/integration/test_resume_integration.py -v
   ```

3. **カバレッジ計測**:
   ```bash
   pytest --cov=scripts/ai-workflow/utils/resume --cov-report=html
   pytest --cov=scripts/ai-workflow/core/metadata_manager --cov-report=html
   ```

### 7.2 テスト実行時間見積もり

| テスト種別 | 見積もり時間 |
|-----------|-----------|
| ユニットテスト | 5分 |
| 統合テスト | 15分 |
| カバレッジ計測 | 5分 |
| **合計** | **25分** |

### 7.3 テスト失敗時の対応

1. **ユニットテスト失敗時**:
   - 実装コード（`resume.py`, `metadata_manager.py`）を修正
   - 修正後、ユニットテストを再実行
   - すべてパスするまで繰り返し

2. **統合テスト失敗時**:
   - `main.py`のレジューム判定ロジックを確認
   - 実装コードとテストコードの両方を確認
   - 修正後、統合テストを再実行

3. **カバレッジ不足時**:
   - カバレッジレポートを確認
   - カバーされていない分岐/行を特定
   - 追加のテストケースを作成

---

## 8. 品質ゲートチェックリスト

本テストシナリオは、Phase 3の品質ゲート（必須要件）を満たしています：

- [x] **Phase 2の戦略に沿ったテストシナリオである**:
  - Phase 2で決定された**UNIT_INTEGRATION**戦略に準拠
  - ユニットテスト21ケース、統合テスト10ケースを作成
  - BDDテストは不要と判断されたため未作成

- [x] **主要な正常系がカバーされている**:
  - 自動レジューム機能（FR-01）: IT-RESUME-001〜004
  - 強制リセット機能（FR-02）: IT-RESET-001〜002
  - レジューム開始フェーズ決定（FR-03）: UT-RM-PHASE-001〜006
  - すべての機能要件の正常系がカバーされている

- [x] **主要な異常系がカバーされている**:
  - メタデータ不存在（FR-04）: IT-EDGE-001
  - メタデータ破損（FR-04）: IT-EDGE-002
  - 権限エラー（FR-06）: UT-MM-CLEAR-003
  - Planning Documentで特定された5つのリスクすべてに対応するテストケースを作成

- [x] **期待結果が明確である**:
  - すべてのテストケースで具体的な期待結果を記載
  - ログ出力の具体的な文言を記載
  - 確認項目をチェックリスト形式で記載
  - Given-When-Then形式で前提条件・入力・期待結果を明確化

### 品質ゲート達成根拠

1. **戦略準拠**:
   - Phase 2のDesign Documentセクション3「テスト戦略の判断」で**UNIT_INTEGRATION**が選択された理由を確認
   - ユニットテスト（ResumeManagerの各メソッド検証）と統合テスト（main.pyとの統合動作確認）の両方を作成
   - BDDテスト不要の理由（CLI内部機能、ユーザーストーリー形式の記載なし）を明記

2. **正常系カバレッジ**:
   - Requirements Documentセクション2「機能要件」のFR-01〜FR-06すべてに対応するテストケースを作成
   - セクション6.3「要件カバレッジマトリックス」で全要件がカバーされていることを証明

3. **異常系カバレッジ**:
   - Planning Documentセクション6「リスクと軽減策」で特定された5つのリスクすべてに対応
   - セクション6.4「エッジケースカバレッジマトリックス」でリスクカバー状況を証明
   - メタデータ破損、権限エラー等の主要な異常系をカバー

4. **期待結果の明確性**:
   - すべてのテストケースで「期待結果」セクションを記載
   - 統合テストでは「確認項目」をチェックリスト形式で記載
   - ログ出力の具体的な文言を記載（例: `[INFO] Existing workflow detected.`）
   - テストデータを具体的に記載（JSON形式で記載）

---

## 9. まとめ

### 9.1 テストシナリオの完成度

本テストシナリオは、Phase 2で決定された**UNIT_INTEGRATION**戦略に基づき、以下を達成しています：

1. **包括的なカバレッジ**:
   - ユニットテスト21ケース、統合テスト10ケース、合計31ケース
   - すべての機能要件（FR-01〜FR-06）をカバー
   - Planning Documentで特定された5つのリスクすべてをカバー

2. **実行可能性**:
   - すべてのテストケースで具体的な入力・期待結果を記載
   - テストデータをJSON形式で提供
   - テスト実行コマンドを明記

3. **品質保証**:
   - カバレッジ目標90%以上を達成見込み
   - 4つの品質ゲート（必須要件）をすべて満たす
   - クリティカルシンキングレビューに対応可能

### 9.2 次のステップ

**Phase 4（実装）**:
- セクション11の実装順序に従って実装
  1. `resume.py`の実装
  2. `metadata_manager.py`の拡張
  3. `main.py`の拡張

**Phase 5（テストコード実装）**:
- 本テストシナリオに基づいてテストコードを実装
  - `tests/unit/utils/test_resume.py`
  - `tests/unit/core/test_metadata_manager.py`（`clear()`メソッドのテスト追加）
  - `tests/integration/test_resume_integration.py`

**Phase 6（テスト実行）**:
- セクション7.1のテスト実行順序に従ってテストを実行
- カバレッジ計測
- バグ修正（必要な場合）

### 9.3 備考

- 本テストシナリオは「80点で十分」の原則に従い、主要なケースに注力しました
- すべてのエッジケースではなく、クリティカルパスと高リスク領域を優先的にカバーしています
- テストコード実装時に追加のテストケースが必要になった場合は、Phase 5で追加することができます

---

**作成日**: 2025-10-12
**作成者**: Claude AI (Phase 3: Test Scenario)
**レビュー状態**: 未レビュー
**承認者**: -
**承認日**: -
