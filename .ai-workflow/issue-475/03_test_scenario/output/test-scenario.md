# テストシナリオ: Issue #475

**Issue番号**: #475
**タイトル**: [BugFix] dot_processor.py インポートエラーの修正
**作成日**: 2025-01-17
**優先度**: Critical

---

## ⚠️ Phase 3 スキップ通知

**このPhaseはスキップされます。**

### スキップ理由

Planning Phase（Phase 0）および設計フェーズ（Phase 2）の決定に基づき、Phase 3（テストシナリオ作成）は**スキップ**されます。

**根拠**:

1. **既存テストが十分**:
   - `tests/test_dot_processor.py` - 既存
   - `tests/test_urn_processor.py` - 既存
   - `tests/test_node_label_generator.py` - 既存
   - `tests/test_resource_dependency_builder.py` - 既存
   - `tests/conftest.py` - フィクスチャ定義

2. **機能追加なし**:
   - 新規機能の追加ではなく、既存機能の修復のみ
   - `src/__init__.py`（空ファイル）の作成によるPythonパッケージ認識の修正

3. **テスト戦略: UNIT_ONLY**:
   - 既存ユニットテストの実行確認のみで十分
   - 新規テストシナリオの作成は不要

4. **テストコード戦略: EXTEND_TEST**:
   - 既存テストコードで十分
   - 追加のテストケースは不要

5. **修正内容の性質**:
   - 空の`__init__.py`ファイルを1つ作成するだけの単純な修正
   - Jenkinsfileに1行追加するのみ
   - 既存コードの変更なし

---

## Phase 6での検証内容

Phase 3（テストシナリオ作成）はスキップしますが、**Phase 6（テスト実行）**では以下の検証を実施します：

### 1. インポートエラー解消の確認

**目的**: `__init__.py`の作成により、インポートエラーが解消されていることを確認

**検証コマンド**:

```bash
cd jenkins/jobs/pipeline/infrastructure/pulumi-stack-action

# 各モジュールのインポートテスト
python3 -c "from src.dot_processor import DotFileGenerator; print('✅ dot_processor インポート成功')"
python3 -c "from src.urn_processor import UrnProcessor; print('✅ urn_processor インポート成功')"
python3 -c "from src.node_label_generator import NodeLabelGenerator; print('✅ node_label_generator インポート成功')"
python3 -c "from src.resource_dependency_builder import ResourceDependencyBuilder; print('✅ resource_dependency_builder インポート成功')"
```

**期待結果**:
- すべてのインポートが成功すること
- `ModuleNotFoundError`が発生しないこと

---

### 2. 既存ユニットテストの実行

**目的**: 既存のユニットテストが正常に実行できることを確認

**検証コマンド**:

```bash
cd jenkins/jobs/pipeline/infrastructure/pulumi-stack-action

# pytestがインストールされている場合
python3 -m pytest tests/ -v

# または個別実行
python3 -m pytest tests/test_dot_processor.py -v
python3 -m pytest tests/test_urn_processor.py -v
python3 -m pytest tests/test_node_label_generator.py -v
python3 -m pytest tests/test_resource_dependency_builder.py -v
```

**期待結果**:
- すべてのテストケースが成功すること
- インポートエラーが発生しないこと
- テストカバレッジが維持されていること

---

### 3. Jenkinsジョブの動作確認

**目的**: Jenkins環境でレポート生成が正常に動作することを確認

**検証手順**:

1. **development環境でのジョブ実行**:
   - Jenkins UIにアクセス
   - `delivery-management-jobs/development/pulumi-deployments`のいずれかのジョブを選択
   - ビルドを実行

2. **コンソールログの確認**:
   - `__init__.py`がコピーされていることを確認
   - `ModuleNotFoundError`が発生しないことを確認
   - レポート生成処理が成功することを確認

3. **HTMLレポートの確認**:
   - ビルド成果物にHTMLレポートが生成されていることを確認
   - レポート内容が正しく表示されることを確認

**期待結果**:
- ビルドステータスが`SUCCESS`または`UNSTABLE`であること（`UNSTABLE`はPulumiアクションのエラーのみ）
- レポート生成処理が完了すること
- HTMLレポートが正常に生成されること
- `ModuleNotFoundError`が発生しないこと

---

## 受け入れ基準の対応

要件定義書で定義された5つの受け入れ基準を、Phase 6で検証します：

### ✅ 受け入れ基準1: `__init__.py`の作成

**検証方法** (Phase 4実施後):
```bash
ls -la jenkins/jobs/pipeline/infrastructure/pulumi-stack-action/src/__init__.py
stat -c "%a" jenkins/jobs/pipeline/infrastructure/pulumi-stack-action/src/__init__.py
```

**期待結果**:
- ファイルが存在すること
- ファイル権限が644であること
- ファイル内容が空（0バイト）であること

---

### ✅ 受け入れ基準2: インポートエラーの解消

**検証方法** (Phase 6実施):
```bash
python3 -c "from src.dot_processor import DotFileGenerator"
python3 -c "from src.urn_processor import UrnProcessor"
```

**期待結果**:
- インポートが成功すること
- `ModuleNotFoundError`が発生しないこと

---

### ✅ 受け入れ基準3: 既存ユニットテストの成功

**検証方法** (Phase 6実施):
```bash
python3 -m pytest tests/ -v
```

**期待結果**:
- すべてのテストケースが成功すること
- インポートエラーが発生しないこと

---

### ✅ 受け入れ基準4: Jenkinsfileの更新

**検証方法** (Phase 4実施後):
```bash
grep "__init__.py" jenkins/jobs/pipeline/infrastructure/pulumi-stack-action/Jenkinsfile
```

**期待結果**:
- `cp ${JENKINS_REPO_DIR}/${SCRIPT_PATH}/__init__.py . || true`が追加されていること
- 既存のファイルコピー処理が影響を受けないこと

---

### ✅ 受け入れ基準5: Jenkinsジョブの成功

**検証方法** (Phase 6実施):
- development環境でのJenkinsジョブ実行

**期待結果**:
- レポート生成処理が成功すること
- HTMLレポートが生成されること
- `ModuleNotFoundError`が発生しないこと
- ビルドステータスが`SUCCESS`または`UNSTABLE`であること

---

## オプション: インポート回帰テストの追加

Phase 5（テストコード実装）で、必要に応じて以下のインポート回帰テストを追加することも可能です（優先度: 低）：

```python
# tests/test_imports.py（オプション）
"""
インポートエラー回帰テスト
Issue #475の修正を検証
"""

def test_urn_processor_import():
    """urn_processorがインポート可能であることを確認"""
    from urn_processor import UrnProcessor
    assert UrnProcessor is not None

def test_node_label_generator_import():
    """node_label_generatorがインポート可能であることを確認"""
    from node_label_generator import NodeLabelGenerator
    assert NodeLabelGenerator is not None

def test_resource_dependency_builder_import():
    """resource_dependency_builderがインポート可能であることを確認"""
    from resource_dependency_builder import ResourceDependencyBuilder
    assert ResourceDependencyBuilder is not None

def test_dot_processor_import():
    """dot_processorがインポート可能であることを確認"""
    from dot_processor import DotFileGenerator, DotFileProcessor
    assert DotFileGenerator is not None
    assert DotFileProcessor is not None
```

**注**: このテストの追加は**オプション**であり、必須ではありません。既存のテストで十分にカバーされています。

---

## 品質ゲート（Phase 3）- スキップ

Phase 3の品質ゲートは、**スキップ**されるため評価されません。

代わりに、Phase 6（テスト実行）で以下を確認します：

- ✅ **既存ユニットテストが正常に実行できる**
- ✅ **インポートエラーが解消されている**
- ✅ **すべてのテストケースが成功している**
- ✅ **Jenkinsジョブが正常に実行できる**

---

## 次のステップ

**Phase 4（実装）**に直接進みます：

1. `src/__init__.py`を作成
2. Jenkinsfileを修正
3. Gitコミット

**Phase 5（テストコード実装）**: スキップ（既存テストで十分）

**Phase 6（テスト実行）**:
1. ローカル環境でインポートテスト実施
2. 既存ユニットテストを実行
3. Jenkins環境で動作確認

---

## 参照ドキュメント

- Planning Document: `.ai-workflow/issue-475/00_planning/output/planning.md`
- 要件定義書: `.ai-workflow/issue-475/01_requirements/output/requirements.md`
- 設計書: `.ai-workflow/issue-475/02_design/output/design.md`

---

**Phase 3スキップの承認**: Planning Phase（Phase 0）の決定に基づく

**次のPhase**: Phase 4（実装フェーズ）
