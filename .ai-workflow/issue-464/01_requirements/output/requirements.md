# 要件定義書 - Issue #464

## 0. Planning Documentの確認

### 開発計画の全体像

**プロジェクト計画書**: `.ai-workflow/issue-464/00_planning/output/planning.md` を確認済み。

**実装戦略**: REFACTOR（既存コードの構造改善）
**テスト戦略**: UNIT_INTEGRATION（単体テスト + 統合テスト）
**テストコード戦略**: EXTEND_TEST（既存テストファイルの拡張）

**見積もり工数**: 8〜12時間
**複雑度**: 中程度
**リスク評価**: 中

### 戦略を踏まえた要件定義のポイント

1. **リファクタリングの性質を考慮**
   - 既存機能の完全な維持が最優先
   - 既存のCharacterization Test（特性テスト）を活用
   - 振る舞いの変化を許容しない

2. **Phase 2（Issue #461〜#463）の成果物を前提**
   - `UrnProcessor`クラス（URN解析）
   - `NodeLabelGenerator`クラス（ノードラベル生成）
   - `ResourceDependencyBuilder`クラス（依存関係構築）
   - これらのクラスは既にテスト済みで動作保証されている

3. **品質目標**
   - Cyclomatic Complexity < 10（全メソッド）
   - ネストレベル ≤ 3（深いネスト構造の平坦化）
   - 循環参照の回避（`NodeLabelGenerator` → `DotFileProcessor.PROVIDER_COLORS`は遅延インポートで既に解決済み）

---

## 1. 概要

### 背景

Issue #448（親Issue）の一環として、`dot_processor.py`のリファクタリングを段階的に実施している。Phase 2（Issue #461〜#463）で以下の3つの新規クラスが作成された：

- **UrnProcessor** (Issue #461): URN解析、正規化、コンポーネント抽出
- **NodeLabelGenerator** (Issue #462): DOTグラフのノードラベル生成
- **ResourceDependencyBuilder** (Issue #463): リソース依存関係グラフ構築

これらの新規クラスは既に単体テスト済みで動作保証されている。

Phase 3（本Issue）では、これらの新規クラスを既存の`DotFileProcessor`クラスに統合し、深いネスト構造を早期リターンパターンで平坦化する。

### 目的

1. **コードの保守性向上**: 新規クラスの統合により、責務を明確に分離し、コードの読みやすさを向上
2. **複雑度削減**: 深いネスト構造（ネストレベル ≥ 3）を早期リターンパターンで平坦化し、Cyclomatic Complexity < 10を達成
3. **既存機能の維持**: リファクタリングによる振る舞いの変化を一切許容しない（Characterization Testで検証）

### ビジネス価値・技術的価値

**ビジネス価値**:
- 今後の機能追加・変更時の開発速度向上（保守性の向上）
- バグ発生リスクの低減（複雑度削減）

**技術的価値**:
- コードの可読性・保守性の大幅向上
- テスタビリティの向上（単体テスト可能な小さなメソッドへの分割）
- SOLID原則の遵守（Single Responsibility Principle、依存性注入）

---

## 2. 機能要件

以下の要件は、すべて**既存機能の振る舞いを維持**することが前提である。

### FR-1: 新規クラスの統合（依存性注入パターンの適用）

**優先度**: 高

**要件説明**:
`DotFileProcessor`クラスおよび`DotFileGenerator`クラスに、Phase 2で作成した3つの新規クラス（`UrnProcessor`、`NodeLabelGenerator`、`ResourceDependencyBuilder`）を統合する。

**詳細**:
- `DotFileProcessor._process_node_definition()`メソッドは、既に`UrnProcessor.parse_urn()`と`NodeLabelGenerator.generate_node_label()`を呼び出しているため、統合作業は完了している（確認のみ）
- `DotFileGenerator._add_resource_dependencies()`メソッドは、既に`ResourceDependencyBuilder.add_resource_dependencies()`を呼び出しているため、統合作業は完了している（確認のみ）
- 既存の静的メソッド呼び出しを維持する（互換性確保）
- 循環参照が発生しないことを確認（`NodeLabelGenerator`は遅延インポートで既に回避済み）

**受け入れ基準**:
- Given: `dot_processor.py`にPhase 2の3つの新規クラスがインポートされている
- When: 既存のテストケース（Characterization Test）を実行
- Then: 全テストがパスし、振る舞いに変化がない

---

### FR-2: `_enhance_pulumi_graph`メソッドのネスト解消

**優先度**: 高

**要件説明**:
`DotFileProcessor._enhance_pulumi_graph()`メソッドの深いネスト構造（現在のネストレベル: 推定3以上）を早期リターンパターンで平坦化する。

**詳細**:
- 現在のネストレベルを測定（手動レビューまたはlintツール）
- 早期リターンパターン（ガード節）を適用
- ネストレベルを3以下に削減
- 可読性を向上させる

**対象コード**（現状分析）:
```python
@staticmethod
def _enhance_pulumi_graph(dot_content: str) -> str:
    """Pulumi生成グラフを拡張"""
    lines = dot_content.split('\n')
    new_lines = []

    # URN情報をキャッシュ
    node_urn_map = {}
    stack_node_id = None

    # 各行を処理
    for i, line in enumerate(lines):
        if i == 0 and 'strict digraph' in line:
            new_lines.extend(DotFileProcessor._add_graph_header(line))
        else:
            processed_line, node_info = DotFileProcessor._process_graph_line(
                line, node_urn_map, stack_node_id
            )

            if node_info:
                node_urn_map.update(node_info.get('node_urn_map', {}))
                if node_info.get('stack_node_id'):
                    stack_node_id = node_info['stack_node_id']

            if processed_line:
                new_lines.append(processed_line)

    return '\n'.join(new_lines)
```

**現状のネストレベル**: 3（for → if → else → if）

**改善案**:
- 早期リターンパターンを適用（ガード節の追加）
- ネスト内の`if node_info:`ブロックを関数抽出して平坦化

**受け入れ基準**:
- Given: リファクタリング前の`_enhance_pulumi_graph`メソッド
- When: 早期リターンパターンを適用してリファクタリング
- Then: ネストレベルが3以下に削減され、全Characterization Testがパス

---

### FR-3: `_process_node_definition`メソッドのネスト解消

**優先度**: 高

**要件説明**:
`DotFileProcessor._process_node_definition()`メソッドの深いネスト構造を早期リターンパターンで平坦化する。

**詳細**:
- 現在のネストレベルを測定
- 早期リターンパターンを適用
- ネストレベルを3以下に削減
- 可読性を向上させる

**対象コード**（現状分析）:
```python
@staticmethod
def _process_node_definition(line: str) -> Tuple[str, Dict]:
    """ノード定義を処理"""
    # ノードIDを抽出
    node_id = line.strip().split('[')[0].strip()

    # URNを抽出
    urn_match = re.search(r'label="([^"]+)"', line)
    if not urn_match:
        return line, None

    urn = urn_match.group(1)
    urn_info = UrnProcessor.parse_urn(urn)

    # NodeLabelGeneratorでノード属性を生成
    node_attrs = NodeLabelGenerator.generate_node_label(urn, urn_info)

    # 新しいノード定義
    new_line = f'    {node_id} [{node_attrs}];'

    # メタデータを返す
    result_info = {'node_urn_map': {node_id: urn_info}}
    if UrnProcessor.is_stack_resource(urn):
        result_info['stack_node_id'] = node_id

    return new_line, result_info
```

**現状のネストレベル**: 2（if → 処理）

**改善案**:
- 既に早期リターン（`if not urn_match: return line, None`）が適用されているため、追加の改善は不要
- ただし、`result_info`の構築ロジックが長い場合は、ヘルパーメソッドに抽出することを検討

**受け入れ基準**:
- Given: リファクタリング前の`_process_node_definition`メソッド
- When: ネスト解消またはメソッド抽出を適用（必要な場合）
- Then: ネストレベルが3以下であることを確認し、全Characterization Testがパス

---

### FR-4: その他の深いネスト構造の平坦化

**優先度**: 中

**要件説明**:
`dot_processor.py`内の他のメソッドで、ネストレベルが3以上の箇所を特定し、早期リターンパターンで平坦化する。

**詳細**:
- `_process_graph_line()`メソッドを調査（ネストレベル確認）
- `_process_edge_definition()`メソッドを調査
- `_process_single_node()`メソッドを調査
- ネストレベルが3以上のメソッドをリストアップ
- 早期リターンパターンまたはメソッド抽出で平坦化

**受け入れ基準**:
- Given: `dot_processor.py`のすべてのメソッド
- When: ネストレベルを測定し、3以上の箇所を特定
- Then: 全メソッドのネストレベルが3以下に削減され、全Characterization Testがパス

---

### FR-5: 統合テストの実施と回帰確認

**優先度**: 高

**要件説明**:
新規クラス統合後、既存のCharacterization Testを実行し、振る舞いに変化がないことを確認する。さらに、新規統合箇所をカバーする統合テストを追加する。

**詳細**:
- 既存のCharacterization Testマーカー（`@pytest.mark.characterization`）を持つテストを全実行
- リファクタリング前後の振る舞い比較テスト
- 新規統合箇所（`UrnProcessor`、`NodeLabelGenerator`、`ResourceDependencyBuilder`との協調動作）をカバーする統合テストを`tests/test_dot_processor.py`に追加

**受け入れ基準**:
- Given: リファクタリング完了後のコード
- When: 全Characterization Testを実行
- Then: 全テストがパスし、リファクタリング前と振る舞いが一致

---

### FR-6: Cyclomatic Complexityの確認と削減

**優先度**: 高

**要件説明**:
リファクタリング後、全メソッドのCyclomatic Complexityを測定し、目標値（< 10）を達成していることを確認する。

**詳細**:
- radonツール（`pip install radon`）を使用してCyclomatic Complexityを測定
  ```bash
  radon cc jenkins/jobs/pipeline/infrastructure/pulumi-stack-action/src/dot_processor.py -s
  ```
- 目標値（< 10）を超えるメソッドを特定
- 早期リターンパターン、メソッド分割で改善
- 再測定して目標達成を確認

**受け入れ基準**:
- Given: リファクタリング完了後のコード
- When: radonツールでCyclomatic Complexityを測定
- Then: 全メソッドのCyclomatic Complexityが10未満

---

## 3. 非機能要件

### NFR-1: パフォーマンス要件

**要件**: リファクタリング前後で処理時間に顕著な劣化がないこと

**詳細**:
- 20リソース処理時の実行時間を計測
- リファクタリング前後で実行時間の差が±10%以内であること
- パフォーマンステストを`tests/test_dot_processor.py`に追加

**測定方法**:
```python
import time
start = time.time()
# 20リソース処理
elapsed = time.time() - start
assert elapsed < 1.0  # 1秒以内
```

---

### NFR-2: 保守性要件

**要件**: コードの可読性が向上し、今後の変更が容易になること

**詳細**:
- ネストレベルが3以下に削減されている
- メソッドの責務が明確（Single Responsibility Principle）
- docstringが適切に記述されている
- 変数名、メソッド名が意図を明確に表現している

**検証方法**:
- コードレビューで可読性を評価
- 新規開発者がコードを理解するまでの時間を計測（主観的評価）

---

### NFR-3: テスタビリティ要件

**要件**: 単体テストが容易に記述できる構造であること

**詳細**:
- メソッドが小さく、単一の責務を持つ
- 依存性注入により、モックやスタブを容易に利用可能
- 既存のCharacterization Testが全パス

**検証方法**:
- 統合テストの追加が容易であることを確認
- テストカバレッジツール（`pytest-cov`）でカバレッジを測定（目標: 80%以上）

---

## 4. 制約事項

### 技術的制約

1. **使用技術**:
   - Python 3.8以上
   - 既存ライブラリ（re, typing）のみ使用（新規依存の追加なし）
   - Pulumiが生成するDOT形式に準拠

2. **既存システムとの整合性**:
   - `DotFileProcessor`と`DotFileGenerator`の公開インターフェース（静的メソッド）を変更しない
   - 既存の呼び出し元コードに影響を与えない

3. **循環参照の回避**:
   - `NodeLabelGenerator` → `DotFileProcessor.PROVIDER_COLORS`は遅延インポートで既に回避済み
   - 新規統合時に新たな循環参照を発生させない

### リソース制約

1. **時間**: 見積もり工数8〜12時間
2. **人員**: 1名のエンジニア
3. **予算**: なし（既存リソース内で実施）

### ポリシー制約

1. **セキュリティポリシー**:
   - クレデンシャルのハードコーディング禁止
   - 機密情報のログ出力禁止

2. **コーディング規約**:
   - [CLAUDE.md](../../CLAUDE.md)、[CONTRIBUTION.md](../../CONTRIBUTION.md)に準拠
   - PEP 8準拠（Pythonコーディング規約）
   - docstringはGoogle Style

---

## 5. 前提条件

### システム環境

1. **開発環境**:
   - Python 3.8以上
   - pytest 6.0以上
   - radon 5.0以上（Cyclomatic Complexity測定）

2. **実行環境**:
   - Jenkins Job（Pulumi Stack Action）内で動作
   - `dot_processor.py`はJenkins Pipelineから呼び出される

### 依存コンポーネント

1. **Phase 2の成果物（Issue #461〜#463）**:
   - `UrnProcessor`クラス（`src/urn_processor.py`）
   - `NodeLabelGenerator`クラス（`src/node_label_generator.py`）
   - `ResourceDependencyBuilder`クラス（`src/resource_dependency_builder.py`）
   - これらのクラスは既にテスト済みで動作保証されている

2. **既存テストファイル**:
   - `tests/test_dot_processor.py`（Characterization Test）

### 外部システム連携

- **なし**: `dot_processor.py`は外部システムに依存しない（Pulumiが生成したJSONデータを処理するのみ）

---

## 6. 受け入れ基準

以下の受け入れ基準は、**すべて達成すること**が必須である。

### AC-1: 機能要件の達成

- [ ] **AC-1.1**: 新規クラス（`UrnProcessor`、`NodeLabelGenerator`、`ResourceDependencyBuilder`）が正しく統合されている
- [ ] **AC-1.2**: `_enhance_pulumi_graph`メソッドのネストレベルが3以下に削減されている
- [ ] **AC-1.3**: `_process_node_definition`メソッドのネストレベルが3以下に削減されている
- [ ] **AC-1.4**: その他の深いネスト構造（ネストレベル ≥ 3）が平坦化されている
- [ ] **AC-1.5**: 全Characterization Testがパス（回帰なし）
- [ ] **AC-1.6**: 全メソッドのCyclomatic Complexityが10未満

### AC-2: 非機能要件の達成

- [ ] **AC-2.1**: 20リソース処理時の実行時間がリファクタリング前後で±10%以内
- [ ] **AC-2.2**: コードレビューで可読性が向上していることが確認されている
- [ ] **AC-2.3**: 統合テストが追加され、新規統合箇所がカバーされている

### AC-3: 制約事項の遵守

- [ ] **AC-3.1**: 既存の公開インターフェース（静的メソッド）が変更されていない
- [ ] **AC-3.2**: 循環参照が発生していない
- [ ] **AC-3.3**: 新規依存ライブラリが追加されていない
- [ ] **AC-3.4**: PEP 8に準拠している（`flake8`でチェック）

### AC-4: ドキュメントの更新

- [ ] **AC-4.1**: コード内docstringが更新されている（依存性注入、早期リターンの説明）
- [ ] **AC-4.2**: アーキテクチャ図（クラス図、シーケンス図）が更新されている（必要な場合）
- [ ] **AC-4.3**: リファクタリング理由と結果がIssue完了レポートに記録されている

---

## 7. スコープ外

以下の項目は、本Issue（Phase 3）のスコープ外とする。

### 明確にスコープ外とする事項

1. **新機能の追加**:
   - DOTグラフの新しいレンダリング機能
   - 新しいプロバイダーの色設定追加
   - リソースフィルタリング機能

2. **既存機能の拡張**:
   - 20リソースを超える処理のサポート拡張
   - DOT形式以外のグラフフォーマット対応

3. **パフォーマンス最適化**:
   - アルゴリズムの根本的な変更
   - キャッシュ機構の追加

4. **テストインフラの変更**:
   - テストフレームワークの変更
   - CI/CDパイプラインの変更

### 将来的な拡張候補

以下の項目は、Phase 4以降で検討する可能性がある：

1. **さらなるクラス分割**:
   - `DotFileGenerator`のメソッドを別クラスに抽出
   - スタイル設定を専用の設定クラスに分離

2. **設定の外部化**:
   - `PROVIDER_COLORS`をYAML/JSON設定ファイルに移動
   - カスタム色設定の動的読み込み

3. **プラグイン機構**:
   - カスタムラベルジェネレーターのプラグイン対応
   - カスタム依存関係ビルダーのプラグイン対応

---

## 8. リスク分析

以下のリスクは、プロジェクト計画書（`.ai-workflow/issue-464/00_planning/output/planning.md`）のリスクセクションから抽出したものである。

### リスク1: Characterization Testの失敗（振る舞いの変化）

**影響度**: 高
**確率**: 中

**軽減策**:
- 小さな変更ごとにテスト実行（インクリメンタルリファクタリング）
- リファクタリング前に全テストがパスすることを確認
- 失敗時は即座にロールバックして原因調査

### リスク2: Cyclomatic Complexity目標未達成（< 10）

**影響度**: 中
**確率**: 低

**軽減策**:
- radonツールによる測定を実施
- 未達成の場合は追加リファクタリング時間を確保（バッファ0.5h）
- 早期リターンパターンの徹底適用

### リスク3: 循環参照の発生

**影響度**: 中
**確率**: 低

**軽減策**:
- 既存の循環参照（`NodeLabelGenerator` → `DotFileProcessor.PROVIDER_COLORS`）は遅延インポートで回避済み
- 新規統合時は依存方向を明確にする（`DotFileProcessor` → 新規クラス、逆方向の依存は作らない）

### リスク4: 実装時間の超過

**影響度**: 低
**確率**: 中

**軽減策**:
- タスク単位で細分化（Task 4-1〜4-5）
- 各タスク完了時にテストを実行（早期問題検出）
- 見積もり工数に20%のバッファを含める（8〜12h = 10h ± 20%）

---

## 9. 付録

### 9.1. 関連ファイル

**対象ファイル**:
- `jenkins/jobs/pipeline/infrastructure/pulumi-stack-action/src/dot_processor.py`

**テストファイル**:
- `jenkins/jobs/pipeline/infrastructure/pulumi-stack-action/tests/test_dot_processor.py`

**Phase 2の成果物**:
- `jenkins/jobs/pipeline/infrastructure/pulumi-stack-action/src/urn_processor.py`（Issue #461）
- `jenkins/jobs/pipeline/infrastructure/pulumi-stack-action/src/node_label_generator.py`（Issue #462）
- `jenkins/jobs/pipeline/infrastructure/pulumi-stack-action/src/resource_dependency_builder.py`（Issue #463）

### 9.2. 関連Issue

**親Issue**: #448（dot_processor.pyの全体リファクタリング計画）

**Phase 2の依存Issue**:
- #461（Phase 2-1: UrnProcessor作成 - 完了）
- #462（Phase 2-2: NodeLabelGenerator作成 - 完了）
- #463（Phase 2-3: ResourceDependencyBuilder作成 - 完了）

### 9.3. 測定ツール

**Cyclomatic Complexity測定**:
```bash
pip install radon
radon cc jenkins/jobs/pipeline/infrastructure/pulumi-stack-action/src/dot_processor.py -s
```

**ネストレベル測定**:
- 手動レビュー
- lintツール（flake8, pylint）の`max-nested-blocks`チェック

**テストカバレッジ測定**:
```bash
pip install pytest-cov
pytest tests/test_dot_processor.py --cov=src.dot_processor --cov-report=term-missing
```

### 9.4. プロジェクト参考ドキュメント

- [CLAUDE.md](../../CLAUDE.md) - プロジェクト全体の方針とコーディングガイドライン
- [ARCHITECTURE.md](../../ARCHITECTURE.md) - アーキテクチャ設計思想
- [CONTRIBUTION.md](../../CONTRIBUTION.md) - 開発ガイドライン
- [README.md](../../README.md) - プロジェクト概要と使用方法

---

## 10. 改訂履歴

| 日付 | バージョン | 変更内容 | 作成者 |
|------|-----------|---------|--------|
| 2025-01-XX | 1.0 | 初版作成 | Claude Code |

---

**作成日**: 2025年01月
**最終更新**: 2025年01月
