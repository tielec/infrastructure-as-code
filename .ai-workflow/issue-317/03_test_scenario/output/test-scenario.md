# テストシナリオ: リトライ時のログファイル連番管理

**Issue番号**: #317
**作成日**: 2025-10-10
**対象システム**: AI Workflow Orchestrator
**実装対象**: BasePhase クラス
**テスト戦略**: UNIT_INTEGRATION

---

## 1. テスト戦略サマリー

### 1.1 選択されたテスト戦略

**UNIT_INTEGRATION**

Phase 2の設計書で決定された通り、以下の理由でUNIT_INTEGRATIONテスト戦略を採用します：

1. **Unitテストが必須**:
   - `_get_next_sequence_number()` メソッドの単体動作確認が必要
   - 連番決定ロジックの境界値テストが必要
   - 正規表現パターンマッチングの正確性確認が必要

2. **Integrationテストも必要**:
   - `execute_with_claude()` → `_save_execution_logs()` → `_get_next_sequence_number()` の一連の流れを確認
   - 実際のディレクトリ構造でのファイル生成を確認
   - リトライシナリオでの連番インクリメント動作を確認

### 1.2 テスト対象の範囲

**対象コンポーネント**:
- `BasePhase._get_next_sequence_number()` メソッド（新規）
- `BasePhase._save_execution_logs()` メソッド（修正）
- `BasePhase.execute_with_claude()` メソッド（間接的）

**対象ファイル**:
- `scripts/ai-workflow/phases/base_phase.py`

**テスト対象の動作**:
1. ログファイル名への連番付与（`agent_log_N.md`, `agent_log_raw_N.txt`, `prompt_N.txt`）
2. 既存ログファイルの検出と次の連番決定
3. リトライ時の連番インクリメント
4. 成果物ファイルの上書き動作維持（`output/` 配下）

### 1.3 テストの目的

1. **機能の正確性**: 連番決定ロジックが正しく動作することを保証
2. **統合の正確性**: execute → review → revise の各フェーズで連番管理が正しく動作することを保証
3. **後方互換性**: 既存のログファイル（連番なし）が存在する環境でも正常動作することを保証
4. **堅牢性**: 異常系（欠番、ファイルなし、大量ファイル）でも正しく動作することを保証

---

## 2. Unitテストシナリオ

### 2.1 `_get_next_sequence_number()` メソッドのテスト

#### TC-U001: 既存ファイルが存在しない場合（正常系）

**目的**: ファイルが存在しないディレクトリで、連番=1が返されることを検証

**前提条件**:
- 対象ディレクトリが存在する
- `agent_log_*.md` パターンのファイルが存在しない

**入力**:
```python
target_dir = Path('/tmp/test_dir')  # 空ディレクトリ
```

**期待結果**:
```python
assert _get_next_sequence_number(target_dir) == 1
```

**テストデータ**: なし（空ディレクトリ）

---

#### TC-U002: 既存ファイルが1件存在する場合（正常系）

**目的**: 既存ファイルが1件の場合、連番=2が返されることを検証

**前提条件**:
- 対象ディレクトリに `agent_log_1.md` が存在する

**入力**:
```python
target_dir = Path('/tmp/test_dir')
# 事前に agent_log_1.md を作成
(target_dir / 'agent_log_1.md').touch()
```

**期待結果**:
```python
assert _get_next_sequence_number(target_dir) == 2
```

**テストデータ**: `agent_log_1.md`（空ファイル）

---

#### TC-U003: 既存ファイルが複数存在する場合（正常系）

**目的**: 既存ファイルが複数の場合、最大値+1が返されることを検証

**前提条件**:
- 対象ディレクトリに以下のファイルが存在する:
  - `agent_log_1.md`
  - `agent_log_2.md`
  - `agent_log_3.md`
  - `agent_log_4.md`
  - `agent_log_5.md`

**入力**:
```python
target_dir = Path('/tmp/test_dir')
# 事前に agent_log_1.md ~ agent_log_5.md を作成
for i in range(1, 6):
    (target_dir / f'agent_log_{i}.md').touch()
```

**期待結果**:
```python
assert _get_next_sequence_number(target_dir) == 6
```

**テストデータ**: `agent_log_1.md` ~ `agent_log_5.md`（空ファイル）

---

#### TC-U004: 欠番がある場合（境界値）

**目的**: ファイル連番に欠番がある場合、最大値+1が返されることを検証（欠番は埋めない）

**前提条件**:
- 対象ディレクトリに以下のファイルが存在する:
  - `agent_log_1.md`
  - `agent_log_3.md`（2が欠番）
  - `agent_log_5.md`（4が欠番）

**入力**:
```python
target_dir = Path('/tmp/test_dir')
# 1, 3, 5 のみ作成（2, 4 は欠番）
for i in [1, 3, 5]:
    (target_dir / f'agent_log_{i}.md').touch()
```

**期待結果**:
```python
assert _get_next_sequence_number(target_dir) == 6
# 欠番（2, 4）は埋められず、最大値5の次の6が返される
```

**テストデータ**: `agent_log_1.md`, `agent_log_3.md`, `agent_log_5.md`

---

#### TC-U005: 大きな連番が存在する場合（境界値）

**目的**: 大きな連番（999）が存在する場合、1000が返されることを検証

**前提条件**:
- 対象ディレクトリに `agent_log_999.md` が存在する

**入力**:
```python
target_dir = Path('/tmp/test_dir')
(target_dir / 'agent_log_999.md').touch()
```

**期待結果**:
```python
assert _get_next_sequence_number(target_dir) == 1000
```

**テストデータ**: `agent_log_999.md`

---

#### TC-U006: 無効なファイル名が混在する場合（異常系）

**目的**: 正規表現にマッチしないファイルが混在しても、正しく連番を取得できることを検証

**前提条件**:
- 対象ディレクトリに以下のファイルが存在する:
  - `agent_log_1.md`（有効）
  - `agent_log_2.md`（有効）
  - `agent_log.md`（無効: 連番なし）
  - `agent_log_abc.md`（無効: 非数値）
  - `agent_log_3.txt`（無効: 拡張子違い）
  - `other_file.md`（無効: パターン不一致）

**入力**:
```python
target_dir = Path('/tmp/test_dir')
(target_dir / 'agent_log_1.md').touch()
(target_dir / 'agent_log_2.md').touch()
(target_dir / 'agent_log.md').touch()
(target_dir / 'agent_log_abc.md').touch()
(target_dir / 'agent_log_3.txt').touch()
(target_dir / 'other_file.md').touch()
```

**期待結果**:
```python
assert _get_next_sequence_number(target_dir) == 3
# 有効なファイルは agent_log_1.md, agent_log_2.md のみ
# 最大値2の次の3が返される
```

**テストデータ**: 上記6ファイル

---

#### TC-U007: 連番が順不同の場合（境界値）

**目的**: ファイル連番が順不同でも、正しく最大値を取得できることを検証

**前提条件**:
- 対象ディレクトリに以下のファイルが存在する（作成順序は逆順）:
  - `agent_log_5.md`
  - `agent_log_2.md`
  - `agent_log_8.md`
  - `agent_log_1.md`
  - `agent_log_3.md`

**入力**:
```python
target_dir = Path('/tmp/test_dir')
# 順不同で作成
for i in [5, 2, 8, 1, 3]:
    (target_dir / f'agent_log_{i}.md').touch()
```

**期待結果**:
```python
assert _get_next_sequence_number(target_dir) == 9
# 最大値8の次の9が返される
```

**テストデータ**: `agent_log_1.md`, `agent_log_2.md`, `agent_log_3.md`, `agent_log_5.md`, `agent_log_8.md`

---

### 2.2 `_save_execution_logs()` メソッドのテスト

#### TC-U101: 初回実行時の連番付きファイル保存（正常系）

**目的**: 初回実行時に連番=1でログファイルが保存されることを検証

**前提条件**:
- 対象ディレクトリが空（ログファイルなし）

**入力**:
```python
prompt = "テストプロンプト"
messages = ["レスポンス1", "レスポンス2"]
log_prefix = "execute"
```

**期待結果**:
```python
# 以下のファイルが作成される
assert (target_dir / 'prompt_1.txt').exists()
assert (target_dir / 'agent_log_1.md').exists()
assert (target_dir / 'agent_log_raw_1.txt').exists()

# ファイル内容の確認
assert (target_dir / 'prompt_1.txt').read_text() == "テストプロンプト"
assert "レスポンス1" in (target_dir / 'agent_log_raw_1.txt').read_text()
assert "レスポンス2" in (target_dir / 'agent_log_raw_1.txt').read_text()
```

**テストデータ**: 上記prompt, messages

---

#### TC-U102: リトライ実行時の連番インクリメント（正常系）

**目的**: リトライ実行時に連番がインクリメントされ、既存ファイルが上書きされないことを検証

**前提条件**:
- 対象ディレクトリに以下のファイルが存在:
  - `prompt_1.txt`
  - `agent_log_1.md`
  - `agent_log_raw_1.txt`

**入力**:
```python
prompt = "リトライプロンプト"
messages = ["リトライレスポンス1"]
log_prefix = "execute"
```

**期待結果**:
```python
# 新しいファイルが作成される
assert (target_dir / 'prompt_2.txt').exists()
assert (target_dir / 'agent_log_2.md').exists()
assert (target_dir / 'agent_log_raw_2.txt').exists()

# 既存ファイルが保持される
assert (target_dir / 'prompt_1.txt').exists()
assert (target_dir / 'agent_log_1.md').exists()
assert (target_dir / 'agent_log_raw_1.txt').exists()

# 新ファイルの内容確認
assert (target_dir / 'prompt_2.txt').read_text() == "リトライプロンプト"
assert "リトライレスポンス1" in (target_dir / 'agent_log_raw_2.txt').read_text()

# 既存ファイルが変更されていないことを確認
assert (target_dir / 'prompt_1.txt').read_text() == "テストプロンプト"
```

**テストデータ**: 上記prompt, messages

---

#### TC-U103: 異なるlog_prefixでの独立した連番管理（正常系）

**目的**: execute, review, revise ディレクトリでそれぞれ独立した連番が付与されることを検証

**前提条件**:
- executeディレクトリに `agent_log_1.md`, `agent_log_2.md` が存在
- reviewディレクトリは空
- reviseディレクトリは空

**入力**:
```python
# review ディレクトリへの保存
prompt = "レビュープロンプト"
messages = ["レビューレスポンス"]
log_prefix = "review"
```

**期待結果**:
```python
# reviewディレクトリに連番=1で保存される（executeの連番に影響されない）
assert (review_dir / 'prompt_1.txt').exists()
assert (review_dir / 'agent_log_1.md').exists()
assert (review_dir / 'agent_log_raw_1.txt').exists()

# executeディレクトリのファイルは影響を受けない
assert (execute_dir / 'agent_log_1.md').exists()
assert (execute_dir / 'agent_log_2.md').exists()
```

**テストデータ**: 上記prompt, messages

---

#### TC-U104: 日本語を含むログファイルの保存（正常系）

**目的**: 日本語を含むプロンプトとレスポンスが正しくUTF-8で保存されることを検証

**前提条件**:
- 対象ディレクトリが空

**入力**:
```python
prompt = "日本語プロンプト：要件定義書を作成してください"
messages = ["了解しました。要件定義書を作成します。"]
log_prefix = "execute"
```

**期待結果**:
```python
# ファイルが作成される
assert (target_dir / 'prompt_1.txt').exists()
assert (target_dir / 'agent_log_1.md').exists()
assert (target_dir / 'agent_log_raw_1.txt').exists()

# UTF-8で正しく保存されている
prompt_content = (target_dir / 'prompt_1.txt').read_text(encoding='utf-8')
assert prompt_content == "日本語プロンプト：要件定義書を作成してください"

log_content = (target_dir / 'agent_log_raw_1.txt').read_text(encoding='utf-8')
assert "了解しました。要件定義書を作成します。" in log_content
```

**テストデータ**: 上記prompt, messages

---

### 2.3 エラーハンドリングのテスト

#### TC-U201: ディレクトリが存在しない場合（異常系）

**目的**: 対象ディレクトリが存在しない場合の動作を検証

**前提条件**:
- 対象ディレクトリが存在しない

**入力**:
```python
target_dir = Path('/tmp/non_existent_dir')
```

**期待結果**:
```python
# ディレクトリが存在しない場合、glob()は空リストを返し、連番=1が返される
# 設計書での決定: エラーを発生させず、1を返す（ディレクトリは事前に作成される想定）
result = _get_next_sequence_number(target_dir)
assert result == 1
```

**補足**:
- 設計書での実装方針: ディレクトリが存在しない場合も`glob()`は空リストを返すため、連番=1を返す
- BasePhaseクラスの`__init__()`でディレクトリは事前に作成されるため、通常は発生しないケース
- このテストは`_get_next_sequence_number()`の単体テストとして、ディレクトリ不在時の動作を検証

**テストデータ**: なし

---

#### TC-U202: ディレクトリへの書き込み権限がない場合（異常系）

**目的**: ディレクトリへの書き込み権限がない場合、適切なエラーが発生することを検証

**前提条件**:
- 対象ディレクトリが読み取り専用

**入力**:
```python
target_dir = Path('/tmp/readonly_dir')
target_dir.mkdir(mode=0o555)  # 読み取り専用
prompt = "テストプロンプト"
messages = ["レスポンス"]
log_prefix = "execute"
```

**期待結果**:
```python
# PermissionErrorが発生する
with pytest.raises(PermissionError):
    _save_execution_logs(prompt, messages, log_prefix)

# 既存ファイルは破損しない
```

**テストデータ**: 上記prompt, messages

---

## 3. Integrationテストシナリオ

### 3.1 execute → review → revise のリトライシナリオ

#### TC-I001: 全フェーズでの連番管理（正常系）

**シナリオ名**: 全フェーズ（execute → review → revise）での独立した連番管理

**目的**: 各フェーズで独立した連番管理が行われることを検証

**前提条件**:
- `.ai-workflow/issue-XXX/` ディレクトリ構造が存在
- 各フェーズのディレクトリ（execute, review, revise）が作成済み

**テスト手順**:

1. **executeフェーズ実行（初回）**
   ```python
   phase = ExecutePhase(issue_number="XXX", phase_name="01_requirements")
   phase.execute_with_claude(prompt="要件定義を作成", log_prefix="execute")
   ```

2. **executeフェーズの確認**
   ```python
   assert (phase.execute_dir / 'agent_log_1.md').exists()
   assert (phase.execute_dir / 'agent_log_raw_1.txt').exists()
   assert (phase.execute_dir / 'prompt_1.txt').exists()
   ```

3. **reviewフェーズ実行（初回）**
   ```python
   phase.execute_with_claude(prompt="要件をレビュー", log_prefix="review")
   ```

4. **reviewフェーズの確認**
   ```python
   # reviewディレクトリで連番=1から開始（executeの連番に影響されない）
   assert (phase.review_dir / 'agent_log_1.md').exists()
   assert (phase.review_dir / 'agent_log_raw_1.txt').exists()
   assert (phase.review_dir / 'prompt_1.txt').exists()
   ```

5. **reviseフェーズ実行（初回）**
   ```python
   phase.execute_with_claude(prompt="要件を修正", log_prefix="revise")
   ```

6. **reviseフェーズの確認**
   ```python
   # reviseディレクトリで連番=1から開始
   assert (phase.revise_dir / 'agent_log_1.md').exists()
   assert (phase.revise_dir / 'agent_log_raw_1.txt').exists()
   assert (phase.revise_dir / 'prompt_1.txt').exists()
   ```

**期待結果**:
- 各フェーズで独立した連番管理（すべて1から開始）
- executeディレクトリ: `agent_log_1.md`
- reviewディレクトリ: `agent_log_1.md`
- reviseディレクトリ: `agent_log_1.md`

**確認項目**:
- [ ] executeディレクトリに `agent_log_1.md`, `agent_log_raw_1.txt`, `prompt_1.txt` が存在
- [ ] reviewディレクトリに `agent_log_1.md`, `agent_log_raw_1.txt`, `prompt_1.txt` が存在
- [ ] reviseディレクトリに `agent_log_1.md`, `agent_log_raw_1.txt`, `prompt_1.txt` が存在
- [ ] 各ディレクトリで独立した連番管理（executeの連番がreviewに影響しない）

---

#### TC-I002: reviseフェーズのリトライシナリオ（正常系）

**シナリオ名**: reviseフェーズでのリトライ実行と連番インクリメント

**目的**: リトライ実行時に連番が正しくインクリメントされ、過去のログが保持されることを検証

**前提条件**:
- `.ai-workflow/issue-XXX/01_requirements/` ディレクトリ構造が存在
- executeフェーズ、reviewフェーズが完了済み
- reviseディレクトリに `agent_log_1.md` が存在（初回実行済み）

**テスト手順**:

1. **reviseフェーズリトライ1回目**
   ```python
   phase = ExecutePhase(issue_number="XXX", phase_name="01_requirements")
   phase.execute_with_claude(prompt="要件を再修正（リトライ1）", log_prefix="revise")
   ```

2. **ファイル確認**
   ```python
   # 新規ファイル作成
   assert (phase.revise_dir / 'agent_log_2.md').exists()
   assert (phase.revise_dir / 'agent_log_raw_2.txt').exists()
   assert (phase.revise_dir / 'prompt_2.txt').exists()

   # 既存ファイル保持
   assert (phase.revise_dir / 'agent_log_1.md').exists()
   assert (phase.revise_dir / 'agent_log_raw_1.txt').exists()
   assert (phase.revise_dir / 'prompt_1.txt').exists()
   ```

3. **reviseフェーズリトライ2回目**
   ```python
   phase.execute_with_claude(prompt="要件を再修正（リトライ2）", log_prefix="revise")
   ```

4. **ファイル確認**
   ```python
   # 新規ファイル作成
   assert (phase.revise_dir / 'agent_log_3.md').exists()
   assert (phase.revise_dir / 'agent_log_raw_3.txt').exists()
   assert (phase.revise_dir / 'prompt_3.txt').exists()

   # 既存ファイル保持（1, 2）
   assert (phase.revise_dir / 'agent_log_1.md').exists()
   assert (phase.revise_dir / 'agent_log_2.md').exists()
   ```

**期待結果**:
- reviseディレクトリに `agent_log_1.md`, `agent_log_2.md`, `agent_log_3.md` が存在
- すべてのログファイルが保持され、上書きされない
- 連番が正しくインクリメント（1 → 2 → 3）

**確認項目**:
- [ ] リトライ1回目で `agent_log_2.md` が作成される
- [ ] リトライ2回目で `agent_log_3.md` が作成される
- [ ] 既存ファイル（1, 2）が上書きされずに保持される
- [ ] 各ファイルの内容が正しい（プロンプトとレスポンスの対応）

---

#### TC-I003: 成果物ファイルの上書き動作（正常系）

**シナリオ名**: リトライ時の成果物ファイル上書き動作

**目的**: `output/` ディレクトリ配下の成果物ファイルは連番が付与されず、上書きされることを検証

**前提条件**:
- `.ai-workflow/issue-XXX/01_requirements/` ディレクトリ構造が存在
- `output/requirements.md` が存在（初回実行済み）

**テスト手順**:

1. **初回実行後の確認**
   ```python
   output_file = phase.output_dir / 'requirements.md'
   assert output_file.exists()
   initial_content = output_file.read_text()
   assert "初回要件定義" in initial_content
   ```

2. **リトライ実行**
   ```python
   phase.execute_with_claude(prompt="要件を修正", log_prefix="revise")
   # この実行により output/requirements.md が更新される想定
   ```

3. **成果物ファイルの確認**
   ```python
   # 成果物ファイルは上書きされる（連番なし）
   assert output_file.exists()
   updated_content = output_file.read_text()
   assert "修正後要件定義" in updated_content

   # 連番付きファイルは存在しない
   assert not (phase.output_dir / 'requirements_1.md').exists()
   assert not (phase.output_dir / 'requirements_2.md').exists()
   ```

4. **ログファイルの確認**
   ```python
   # ログファイルは連番付きで保存される
   assert (phase.revise_dir / 'agent_log_1.md').exists()
   assert (phase.revise_dir / 'agent_log_2.md').exists()
   ```

**期待結果**:
- 成果物ファイル（`output/requirements.md`）は上書きされる（連番なし）
- ログファイルは連番付きで保存される

**確認項目**:
- [ ] `output/requirements.md` が上書きされる
- [ ] `output/requirements_1.md` などの連番付きファイルは作成されない
- [ ] ログファイル（`agent_log_1.md`, `agent_log_2.md`）は連番付きで保存される
- [ ] 成果物は常に最新版のみが存在する

---

### 3.2 複数フェーズでの動作確認

#### TC-I101: 複数フェーズ（requirements → design → execute）での連番管理

**シナリオ名**: 複数フェーズでの独立した連番管理

**目的**: 異なるフェーズ（requirements, design, execute）でそれぞれ独立した連番管理が行われることを検証

**前提条件**:
- `.ai-workflow/issue-XXX/` ディレクトリ構造が存在
- 各フェーズのディレクトリが作成済み

**テスト手順**:

1. **requirementsフェーズ（executeサブフェーズ）実行**
   ```python
   req_phase = RequirementsPhase(issue_number="XXX")
   req_phase.execute_with_claude(prompt="要件定義", log_prefix="execute")
   ```

2. **requirementsフェーズ確認**
   ```python
   assert (req_phase.execute_dir / 'agent_log_1.md').exists()
   ```

3. **designフェーズ（executeサブフェーズ）実行**
   ```python
   design_phase = DesignPhase(issue_number="XXX")
   design_phase.execute_with_claude(prompt="設計書作成", log_prefix="execute")
   ```

4. **designフェーズ確認**
   ```python
   # designフェーズも連番=1から開始（requirementsフェーズの連番に影響されない）
   assert (design_phase.execute_dir / 'agent_log_1.md').exists()
   ```

5. **executeフェーズ（実装フェーズ）実行**
   ```python
   exec_phase = ExecutePhase(issue_number="XXX")
   exec_phase.execute_with_claude(prompt="実装", log_prefix="execute")
   ```

6. **executeフェーズ確認**
   ```python
   # executeフェーズも連番=1から開始
   assert (exec_phase.execute_dir / 'agent_log_1.md').exists()
   ```

**期待結果**:
- 各フェーズで独立した連番管理
- `.ai-workflow/issue-XXX/01_requirements/execute/agent_log_1.md`
- `.ai-workflow/issue-XXX/02_design/execute/agent_log_1.md`
- `.ai-workflow/issue-XXX/03_execute/execute/agent_log_1.md`

**確認項目**:
- [ ] requirementsフェーズのexecuteディレクトリに `agent_log_1.md` が存在
- [ ] designフェーズのexecuteディレクトリに `agent_log_1.md` が存在
- [ ] executeフェーズのexecuteディレクトリに `agent_log_1.md` が存在
- [ ] 各フェーズで独立した連番管理（他フェーズの連番に影響されない）

---

### 3.3 後方互換性テスト

#### TC-I201: 既存の連番なしログファイルが存在する場合（互換性）

**シナリオ名**: 既存の連番なしログファイルとの共存

**目的**: 既存の連番なしログファイル（`agent_log.md`）が存在する環境でも、新しいロジックが正常動作することを検証

**前提条件**:
- 対象ディレクトリに旧形式のログファイルが存在:
  - `agent_log.md`（連番なし）
  - `agent_log_raw.txt`（連番なし）
  - `prompt.txt`（連番なし）

**テスト手順**:

1. **既存ファイルの確認**
   ```python
   assert (target_dir / 'agent_log.md').exists()
   assert (target_dir / 'agent_log_raw.txt').exists()
   assert (target_dir / 'prompt.txt').exists()
   ```

2. **新しいロジックで実行**
   ```python
   phase.execute_with_claude(prompt="新規実行", log_prefix="execute")
   ```

3. **新規ファイルの確認**
   ```python
   # 新しい連番付きファイルが作成される
   assert (target_dir / 'agent_log_1.md').exists()
   assert (target_dir / 'agent_log_raw_1.txt').exists()
   assert (target_dir / 'prompt_1.txt').exists()
   ```

4. **既存ファイルの保持確認**
   ```python
   # 既存の連番なしファイルは削除されず、そのまま残る
   assert (target_dir / 'agent_log.md').exists()
   assert (target_dir / 'agent_log_raw.txt').exists()
   assert (target_dir / 'prompt.txt').exists()
   ```

**期待結果**:
- 既存の連番なしファイルは保持される
- 新規実行分から連番付きファイルで保存される
- エラーが発生しない

**確認項目**:
- [ ] 既存の連番なしファイル（`agent_log.md` など）が保持される
- [ ] 新規ファイルは連番付き（`agent_log_1.md` など）で作成される
- [ ] エラーが発生しない
- [ ] 次回実行時は `agent_log_2.md` が作成される

---

### 3.4 パフォーマンステスト

#### TC-I301: 1000ファイル存在時の連番決定時間（性能）

**シナリオ名**: 大量ファイル存在時のパフォーマンス

**目的**: 1000ファイル存在時でも、連番決定が1秒以内に完了することを検証

**前提条件**:
- 対象ディレクトリに `agent_log_1.md` ~ `agent_log_1000.md` が存在

**テスト手順**:

1. **1000ファイルの作成**
   ```python
   import time
   target_dir = Path('/tmp/perf_test_dir')
   target_dir.mkdir(exist_ok=True)
   for i in range(1, 1001):
       (target_dir / f'agent_log_{i}.md').touch()
   ```

2. **連番決定時間の計測（3回実行して平均を取る）**
   ```python
   import statistics

   execution_times = []
   for _ in range(3):
       start_time = time.time()
       next_seq = _get_next_sequence_number(target_dir)
       elapsed_time = time.time() - start_time
       execution_times.append(elapsed_time)
       assert next_seq == 1001

   avg_time = statistics.mean(execution_times)
   max_time = max(execution_times)
   ```

3. **結果確認**
   ```python
   # 平均実行時間が1秒以内
   assert avg_time < 1.0
   # 最大実行時間も許容範囲内（1.2秒、±20%の許容誤差）
   assert max_time < 1.2
   # 正しい連番が返される
   assert next_seq == 1001
   ```

**期待結果**:
- 連番決定の平均実行時間が1秒以内
- 最大実行時間も1.2秒以内（環境差の許容誤差±20%）
- 正しい連番（1001）が返される

**測定基準**:
- **測定回数**: 3回実行して平均を算出
- **許容誤差**: ±20%（環境差を考慮）
- **基準時間**: 平均1秒以内、最大1.2秒以内

**確認項目**:
- [ ] 1000ファイル存在時の平均連番決定時間が1秒以内
- [ ] 最大実行時間が1.2秒以内（環境差を考慮）
- [ ] 正しい連番（1001）が返される
- [ ] メモリ使用量が適切（大量のファイル情報を保持しない）

---

## 4. テストデータ

### 4.1 正常系テストデータ

#### TD-001: 基本的なログデータ

```python
# プロンプト
prompt_basic = "要件定義書を作成してください"

# レスポンスメッセージ
messages_basic = [
    "了解しました。要件定義書を作成します。",
    "以下の要件を含めます：\n1. 機能要件\n2. 非機能要件"
]

# 期待されるファイル
expected_files_basic = [
    'prompt_1.txt',
    'agent_log_1.md',
    'agent_log_raw_1.txt'
]
```

#### TD-002: 日本語を含むログデータ

```python
# 日本語プロンプト
prompt_japanese = "日本語の要件定義書を作成してください。\n以下の項目を含めること：\n- 概要\n- 機能要件\n- 非機能要件"

# 日本語レスポンス
messages_japanese = [
    "承知しました。日本語で要件定義書を作成します。",
    "# 要件定義書\n\n## 概要\n本システムは...",
    "## 機能要件\nFR-001: ユーザー登録機能"
]

# 期待される文字コード
expected_encoding = 'utf-8'
```

#### TD-003: 長文ログデータ

```python
# 長文プロンプト（1000文字以上）
prompt_long = "要件定義書を作成してください。" + "詳細な説明。" * 200

# 長文レスポンス
messages_long = [
    "要件定義書を作成します。" + "詳細内容。" * 500
]
```

### 4.2 異常系テストデータ

#### TD-101: 特殊文字を含むログデータ

```python
# 特殊文字を含むプロンプト
prompt_special = "要件定義書を作成 <tag> & 'quote' \"double\" \n改行 \t タブ"

# 特殊文字を含むレスポンス
messages_special = [
    "了解: <response> & 'value' \"text\"",
    "改行\nタブ\t含む"
]
```

#### TD-102: 空データ

```python
# 空プロンプト
prompt_empty = ""

# 空レスポンス
messages_empty = []

# 期待される動作: エラーまたは空ファイル作成
```

### 4.3 境界値テストデータ

#### TD-201: 連番境界値

```python
# 大きな連番
large_sequence_files = [
    f'agent_log_{i}.md' for i in [999, 1000, 9999, 10000]
]

# 連番0（無効）
invalid_sequence_files = [
    'agent_log_0.md',  # 0は無効（1始まり）
    'agent_log_-1.md'  # 負数は無効
]
```

#### TD-202: ファイル名パターン境界値

```python
# 有効なパターン
valid_patterns = [
    'agent_log_1.md',
    'agent_log_999.md',
    'agent_log_123456789.md'
]

# 無効なパターン
invalid_patterns = [
    'agent_log.md',           # 連番なし
    'agent_log_abc.md',       # 非数値
    'agent_log_1.txt',        # 拡張子違い
    'agent_log_1_extra.md',   # 余分な文字
    'prefix_agent_log_1.md',  # プレフィックス追加
    'agent_log_1.md.bak'      # 追加拡張子
]
```

### 4.4 統合テスト用ディレクトリ構造

#### TD-301: 標準ディレクトリ構造

```
.ai-workflow/issue-317/
├── 01_requirements/
│   ├── execute/
│   │   ├── agent_log_1.md
│   │   ├── agent_log_raw_1.txt
│   │   └── prompt_1.txt
│   ├── review/
│   │   ├── agent_log_1.md
│   │   ├── agent_log_raw_1.txt
│   │   └── prompt_1.txt
│   ├── revise/
│   │   ├── agent_log_1.md
│   │   ├── agent_log_raw_1.txt
│   │   └── prompt_1.txt
│   └── output/
│       └── requirements.md
├── 02_design/
│   ├── execute/
│   ├── review/
│   ├── revise/
│   └── output/
│       └── design.md
└── metadata.json
```

#### TD-302: リトライ後のディレクトリ構造

```
.ai-workflow/issue-317/01_requirements/revise/
├── agent_log_1.md         # 初回実行
├── agent_log_raw_1.txt
├── prompt_1.txt
├── agent_log_2.md         # リトライ1回目
├── agent_log_raw_2.txt
├── prompt_2.txt
├── agent_log_3.md         # リトライ2回目
├── agent_log_raw_3.txt
└── prompt_3.txt
```

---

## 5. テスト環境要件

### 5.1 ハードウェア要件

| 項目 | 要件 |
|------|------|
| CPU | 特になし（通常のCI/CD環境で十分） |
| メモリ | 最低1GB（1000ファイル作成時） |
| ディスク | 最低500MB（ログファイル保存用） |

### 5.2 ソフトウェア要件

| 項目 | 要件 |
|------|------|
| Python | 3.8以上 |
| pytest | 最新版（7.0以上推奨） |
| OS | Linux, macOS, Windows（クロスプラットフォーム対応） |
| ファイルシステム | POSIX互換またはNTFS |

### 5.3 テスト実行環境

#### ローカル環境

- **用途**: Unitテスト、Integration テストの開発・デバッグ
- **要件**:
  - Python 3.8以上
  - pytest インストール済み
  - `.ai-workflow/` ディレクトリへの書き込み権限

#### CI/CD環境（GitHub Actions）

- **用途**: 自動テスト実行、リグレッションテスト
- **要件**:
  - Python 3.8, 3.9, 3.10, 3.11 のマトリックステスト
  - Linux, macOS, Windows のマトリックステスト
  - pytest, pytest-cov インストール

#### テンポラリディレクトリ

- **用途**: テスト実行時の一時ファイル作成
- **要件**:
  - `/tmp/` または `tempfile.mkdtemp()` を使用
  - テスト終了後にクリーンアップ（`pytest` の `tmp_path` fixture使用推奨）

### 5.4 モック/スタブの必要性

#### モック不要なテスト

- `_get_next_sequence_number()`: 実ファイルシステムでテスト可能
- `_save_execution_logs()`: 実ファイルシステムでテスト可能

#### モックが必要なテスト（Integrationテストの場合）

- **Claude API呼び出し**: `execute_with_claude()` 内のClaude API呼び出しをモック

**モック実装例1: AgentSessionのモック**
```python
from unittest.mock import patch, MagicMock
from pathlib import Path

@patch('ai_workflow_orchestrator.phases.base_phase.AgentSession')
def test_execute_with_claude_logging(mock_agent_session_class, tmp_path):
    """
    execute_with_claude()のログ保存機能をテスト（Claude APIをモック）
    """
    # モックの設定
    mock_session = MagicMock()
    mock_session.run.return_value = [
        "レスポンス1: 要件定義書を作成します",
        "レスポンス2: 以下の要件を含めます"
    ]
    mock_agent_session_class.return_value = mock_session

    # テスト対象のPhaseインスタンス作成
    from ai_workflow_orchestrator.phases.base_phase import BasePhase
    phase = BasePhase(issue_number="TEST", phase_name="test_phase")
    phase.phase_dir = tmp_path
    phase.execute_dir = tmp_path / "execute"
    phase.execute_dir.mkdir()

    # execute_with_claude()を実行
    prompt = "要件定義書を作成してください"
    result = phase.execute_with_claude(
        prompt=prompt,
        log_prefix="execute",
        save_logs=True
    )

    # ログファイルが正しく保存されたか確認
    assert (phase.execute_dir / 'agent_log_1.md').exists()
    assert (phase.execute_dir / 'agent_log_raw_1.txt').exists()
    assert (phase.execute_dir / 'prompt_1.txt').exists()

    # ファイル内容の確認
    assert (phase.execute_dir / 'prompt_1.txt').read_text() == prompt
    raw_log = (phase.execute_dir / 'agent_log_raw_1.txt').read_text()
    assert "レスポンス1: 要件定義書を作成します" in raw_log
    assert "レスポンス2: 以下の要件を含めます" in raw_log
```

**モック実装例2: リトライシナリオのモック**
```python
@patch('ai_workflow_orchestrator.phases.base_phase.AgentSession')
def test_execute_with_claude_retry_sequencing(mock_agent_session_class, tmp_path):
    """
    リトライ時の連番インクリメントをテスト（Claude APIをモック）
    """
    # モックの設定
    mock_session = MagicMock()
    mock_agent_session_class.return_value = mock_session

    # テスト対象のPhaseインスタンス作成
    phase = BasePhase(issue_number="TEST", phase_name="test_phase")
    phase.execute_dir = tmp_path / "execute"
    phase.execute_dir.mkdir(parents=True)

    # 初回実行
    mock_session.run.return_value = ["初回レスポンス"]
    phase.execute_with_claude(prompt="初回プロンプト", log_prefix="execute")
    assert (phase.execute_dir / 'agent_log_1.md').exists()

    # リトライ1回目
    mock_session.run.return_value = ["リトライ1レスポンス"]
    phase.execute_with_claude(prompt="リトライ1プロンプト", log_prefix="execute")
    assert (phase.execute_dir / 'agent_log_2.md').exists()
    # 既存ファイルが保持されることを確認
    assert (phase.execute_dir / 'agent_log_1.md').exists()

    # リトライ2回目
    mock_session.run.return_value = ["リトライ2レスポンス"]
    phase.execute_with_claude(prompt="リトライ2プロンプト", log_prefix="execute")
    assert (phase.execute_dir / 'agent_log_3.md').exists()
    # 既存ファイルが保持されることを確認
    assert (phase.execute_dir / 'agent_log_1.md').exists()
    assert (phase.execute_dir / 'agent_log_2.md').exists()
```

**モック実装例3: 複数フェーズでの独立連番管理のモック**
```python
@patch('ai_workflow_orchestrator.phases.base_phase.AgentSession')
def test_independent_sequencing_across_phases(mock_agent_session_class, tmp_path):
    """
    execute, review, reviseの各フェーズで独立した連番管理をテスト
    """
    mock_session = MagicMock()
    mock_session.run.return_value = ["レスポンス"]
    mock_agent_session_class.return_value = mock_session

    # テスト対象のPhaseインスタンス作成
    phase = BasePhase(issue_number="TEST", phase_name="test_phase")
    phase.execute_dir = tmp_path / "execute"
    phase.review_dir = tmp_path / "review"
    phase.revise_dir = tmp_path / "revise"
    phase.execute_dir.mkdir(parents=True)
    phase.review_dir.mkdir(parents=True)
    phase.revise_dir.mkdir(parents=True)

    # executeフェーズで2回実行
    phase.execute_with_claude(prompt="execute1", log_prefix="execute")
    phase.execute_with_claude(prompt="execute2", log_prefix="execute")
    assert (phase.execute_dir / 'agent_log_1.md').exists()
    assert (phase.execute_dir / 'agent_log_2.md').exists()

    # reviewフェーズで1回実行（連番は1から開始）
    phase.execute_with_claude(prompt="review1", log_prefix="review")
    assert (phase.review_dir / 'agent_log_1.md').exists()

    # reviseフェーズで1回実行（連番は1から開始）
    phase.execute_with_claude(prompt="revise1", log_prefix="revise")
    assert (phase.revise_dir / 'agent_log_1.md').exists()

    # 各フェーズで独立した連番管理が行われることを確認
    # executeは2まで、reviewとreviseは1のみ
    assert not (phase.review_dir / 'agent_log_2.md').exists()
    assert not (phase.revise_dir / 'agent_log_2.md').exists()
```

### 5.5 テストデータの準備

#### 事前準備が必要なデータ

1. **ディレクトリ構造**:
   - `pytest` の `tmp_path` fixture で動的に作成
   - または `setup_method()` で作成

2. **既存ログファイル**:
   - テストケースごとに動的に作成
   - `Path.touch()` で空ファイル作成

3. **テストフィクスチャ**:
   ```python
   @pytest.fixture
   def test_phase(tmp_path):
       phase = BasePhase(issue_number="TEST", phase_name="test_phase")
       phase.phase_dir = tmp_path
       phase.execute_dir = tmp_path / "execute"
       phase.execute_dir.mkdir()
       return phase
   ```

### 5.6 テスト実行コマンド

#### Unitテスト実行

```bash
# すべてのUnitテスト実行
pytest tests/unit/phases/test_base_phase.py -v

# 特定のテストケース実行
pytest tests/unit/phases/test_base_phase.py::test_get_next_sequence_number_no_files -v

# カバレッジ計測
pytest tests/unit/phases/test_base_phase.py --cov=ai_workflow_orchestrator.phases.base_phase --cov-report=html
```

#### Integrationテスト実行

```bash
# すべてのIntegrationテスト実行
pytest tests/integration/test_log_file_sequencing.py -v

# 特定のシナリオ実行
pytest tests/integration/test_log_file_sequencing.py::test_log_sequencing_execute_review_revise -v
```

#### 全テスト実行

```bash
# すべてのテスト実行
pytest tests/ -v

# 並列実行（高速化）
pytest tests/ -n auto
```

#### カバレッジ目標の確認

```bash
# カバレッジレポート生成（HTML形式）
pytest tests/ --cov=ai_workflow_orchestrator.phases.base_phase --cov-report=html --cov-report=term

# カバレッジレポート生成（XML形式、CI/CD用）
pytest tests/ --cov=ai_workflow_orchestrator.phases.base_phase --cov-report=xml
```

### 5.7 テストカバレッジ目標

本テストシナリオでは、以下のカバレッジ目標を設定します:

#### カバレッジ目標値

| カバレッジ種別 | 目標値 | 測定対象 |
|--------------|-------|---------|
| **ライン（Line）カバレッジ** | **90%以上** | `BasePhase._get_next_sequence_number()`<br>`BasePhase._save_execution_logs()` |
| **ブランチ（Branch）カバレッジ** | **80%以上** | 条件分岐（if文、for文など） |
| **関数（Function）カバレッジ** | **100%** | 新規追加メソッドおよび修正メソッド |

#### 測定範囲

**対象ファイル**:
- `ai_workflow_orchestrator/phases/base_phase.py`

**対象メソッド**:
- `_get_next_sequence_number()` (新規)
- `_save_execution_logs()` (修正)
- `execute_with_claude()` (間接的)

**カバレッジ除外**:
- エラーメッセージ出力のみの行（`print()`文など）
- デバッグ用ログ出力

#### カバレッジ達成基準

**ライン90%以上を達成するために必要なテスト**:
- TC-U001〜TC-U007: `_get_next_sequence_number()`の全パスをカバー
- TC-U101〜TC-U104: `_save_execution_logs()`の全パスをカバー
- TC-U201〜TC-U202: エラーハンドリングパスをカバー

**ブランチ80%以上を達成するために必要なテスト**:
- `if not log_files:` (TC-U001でカバー)
- `if not sequence_numbers:` (TC-U006でカバー)
- `if log_prefix == 'execute':` (TC-U101でカバー)
- `elif log_prefix == 'review':` (TC-U103でカバー)
- `elif log_prefix == 'revise':` (TC-I002でカバー)

**関数100%を達成するために必要なテスト**:
- `_get_next_sequence_number()`: TC-U001でカバー
- `_save_execution_logs()`: TC-U101でカバー

#### カバレッジ未達成時の対応

カバレッジ目標未達成の場合、以下の優先順位で対応:

1. **優先度: 高** - ライン90%未達成
   - 追加テストケースを作成し、未カバーのコード行を網羅
   - 主要な正常系・異常系が不足している可能性を調査

2. **優先度: 中** - ブランチ80%未達成
   - 条件分岐の境界値テストケースを追加
   - エッジケースの追加テストを検討

3. **優先度: 低** - 関数100%未達成
   - 未テストの関数を特定し、テストケースを追加

#### カバレッジレポートの確認方法

```bash
# テスト実行後、HTMLレポートを確認
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows

# ターミナルで簡易レポートを確認
pytest tests/ --cov=ai_workflow_orchestrator.phases.base_phase --cov-report=term-missing
```

#### CI/CDでのカバレッジチェック

GitHub ActionsなどのCI/CDで、カバレッジ目標未達成時にビルドを失敗させる設定:

```yaml
# .github/workflows/test.yml（例）
- name: Run tests with coverage
  run: |
    pytest tests/ \
      --cov=ai_workflow_orchestrator.phases.base_phase \
      --cov-report=xml \
      --cov-fail-under=90
```

**カバレッジ判定基準**:
- ライン90%未満: ビルド失敗
- ブランチ80%未満: 警告表示（失敗はさせない）
- 関数100%未満: 警告表示（失敗はさせない）

---

## 6. 品質ゲート確認

- [x] **Phase 2の戦略に沿ったテストシナリオである**
  - UNIT_INTEGRATION戦略に基づき、Unitテスト（TC-U001〜TC-U202）とIntegrationテスト（TC-I001〜TC-I301）を作成

- [x] **主要な正常系がカバーされている**
  - TC-U001, TC-U002, TC-U003: 連番決定の正常系
  - TC-U101, TC-U102: ログ保存の正常系
  - TC-I001, TC-I002, TC-I003: 統合シナリオの正常系

- [x] **主要な異常系がカバーされている**
  - TC-U006: 無効なファイル名混在
  - TC-U201, TC-U202: エラーハンドリング
  - TC-I201: 後方互換性

- [x] **期待結果が明確である**
  - すべてのテストケースで具体的な期待結果を記載
  - アサーション文を含む検証コード例を記載
  - 確認項目チェックリストを記載

---

## 7. 補足情報

### 7.1 テスト実装時の注意事項

1. **ファイルクリーンアップ**: 各テスト後に一時ファイルを削除
   ```python
   @pytest.fixture
   def cleanup_files(tmp_path):
       yield tmp_path
       shutil.rmtree(tmp_path, ignore_errors=True)
   ```

2. **並行実行の考慮**: 同一ディレクトリへの並行書き込みは想定外（テストでは考慮不要）

3. **クロスプラットフォーム**: Path オブジェクトを使用してOS依存性を排除

### 7.2 テスト優先順位

| 優先度 | テストケース | 理由 |
|--------|-------------|------|
| 高 | TC-U001, TC-U002, TC-U003 | 連番決定の基本動作 |
| 高 | TC-U101, TC-U102 | ログ保存の基本動作 |
| 高 | TC-I001, TC-I002 | 統合シナリオの基本動作 |
| 中 | TC-U004, TC-U005, TC-U007 | 境界値テスト |
| 中 | TC-I003, TC-I101, TC-I201 | 特殊シナリオ |
| 低 | TC-U006, TC-U201, TC-U202 | 異常系・エラーハンドリング |
| 低 | TC-I301 | パフォーマンステスト |

### 7.3 テスト実装の順序

1. **Phase 1**: Unitテスト実装（TC-U001〜TC-U104）
2. **Phase 2**: Unitテスト異常系（TC-U201〜TC-U202）
3. **Phase 3**: Integrationテスト基本シナリオ（TC-I001〜TC-I003）
4. **Phase 4**: Integrationテスト拡張シナリオ（TC-I101〜TC-I301）

---

## 8. 改善履歴

### 8.1 レビュー指摘事項の反映（2025-10-10）

Phase 3のクリティカルシンキングレビューで指摘された以下の改善提案を反映しました：

#### 改善1: TC-U201の期待結果の明確化

**指摘内容**:
- 期待結果が「連番=1が返される または FileNotFoundErrorが発生する（実装依存）」と曖昧

**対応内容**:
- 設計書での実装方針を明確化し、「ディレクトリが存在しない場合も連番=1を返す」と決定
- テストケースに補足説明を追加し、実装依存の曖昧さを排除

**修正箇所**: TC-U201（セクション2.3）

#### 改善2: パフォーマンステスト基準の明確化

**指摘内容**:
- TC-I301で「1秒以内」という基準はあるが、測定方法や許容誤差が不明確

**対応内容**:
- 測定回数を3回に設定し、平均値と最大値を算出する方法を追加
- 許容誤差±20%を明記（平均1秒以内、最大1.2秒以内）
- 測定基準セクションを追加し、環境差を考慮した判定基準を明示

**修正箇所**: TC-I301（セクション3.4）

#### 改善3: モック実装例の追加

**指摘内容**:
- モックの必要性は記載されているが、具体的なモック実装例が少ない

**対応内容**:
- 3つの具体的なモック実装例を追加:
  1. AgentSessionの基本的なモック方法
  2. リトライシナリオでのモック方法
  3. 複数フェーズでの独立連番管理のモック方法
- 各例に詳細なコメントと検証ロジックを含む

**修正箇所**: セクション5.4

#### 改善4: テストカバレッジ目標の明示

**指摘内容**:
- テストケースは網羅的だが、カバレッジ目標（80%など）が明記されていない

**対応内容**:
- 新規セクション5.7「テストカバレッジ目標」を追加
- カバレッジ種別ごとの目標値を設定:
  - ライン90%以上
  - ブランチ80%以上
  - 関数100%
- カバレッジ達成基準、未達成時の対応、CI/CDでのチェック方法を詳細に記載

**修正箇所**: セクション5.7（新規追加）

### 8.2 レビュー総合評価

**判定**: PASS_WITH_SUGGESTIONS

**レビューコメント抜粋**:
> このテストシナリオは、Phase 2で決定されたUNIT_INTEGRATION戦略に完全に準拠し、要件定義書の受け入れ基準をすべてカバーした高品質なドキュメントです。テストシナリオは「80点で十分」の基準を大きく超えており、次フェーズ（実装）に進むのに十分な品質を備えています。改善提案はすべてオプションであり、実装フェーズで補完可能です。

---

**テストシナリオ作成完了**: 本テストシナリオは、レビュー指摘事項を反映し、実装フェーズに進むための準備が整いました。
