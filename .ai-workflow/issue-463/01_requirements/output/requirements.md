# 要件定義書: Issue #463

## Issue情報

- **Issue番号**: #463
- **タイトル**: [Refactor] dot_processor.py - Phase 2-3: ResourceDependencyBuilderクラスの抽出
- **URL**: https://github.com/tielec/infrastructure-as-code/issues/463
- **親Issue**: #448
- **依存Issue**: #460 (Phase 1: 基盤整備), #461 (Phase 2-1: UrnProcessor)

---

## 0. Planning Documentの確認

Planning Phaseで策定された以下の開発計画を確認しました：

### 実装戦略
- **戦略**: REFACTOR
- **根拠**: 既存のDotFileProcessorから依存関係処理ロジックを抽出して新規クラスに分離
- **目的**: 既存機能を維持しながら、コードの構造を改善

### テスト戦略
- **戦略**: UNIT_INTEGRATION
- **UNIT（必須）**: ResourceDependencyBuilderクラス単独での動作を検証（カバレッジ80%以上）
- **INTEGRATION（必須）**: DotFileProcessorとの統合を検証（既存テストが全てパス）

### リスク評価
- **技術的リスク（中）**: 依存関係グラフの複雑なロジックを正しく抽出できるか
- **品質リスク（中）**: カバレッジ80%達成と既存テストの維持
- **統合リスク（低）**: 既存のDotFileProcessorとの連携

### 見積もり工数
- **合計**: 8~12時間
- **内訳**: 要件定義(1~1.5h)、設計(1.5~2h)、テストシナリオ(1~1.5h)、実装(3~4h)、テストコード実装(2~3h)、テスト実行(0.5~1h)、ドキュメント(0.5~1h)、レポート(0.5~1h)

---

## 1. 概要

### 背景
dot_processor.pyの段階的リファクタリング計画（Issue #448）のPhase 2-3として、依存関係グラフの構築と検証を担当する`ResourceDependencyBuilder`クラスを新規作成します。

現在、`DotFileGenerator`クラス内に依存関係処理ロジックが含まれており、以下のような単一責任原則の違反が発生しています：
- DOT形式の文字列生成（本来の責務）
- 依存関係グラフの構築（抽出対象）
- URNマッピングの管理（抽出対象）

### 目的
依存関係処理ロジックを`ResourceDependencyBuilder`クラスとして分離し、以下を実現します：
1. **単一責任原則の適用**: 各クラスが明確な責務を持つ
2. **テスト容易性の向上**: 依存関係処理を独立してテスト可能
3. **保守性の向上**: 変更影響範囲の局所化
4. **拡張性の向上**: 新しい依存関係タイプの追加が容易

### ビジネス価値・技術的価値
- **保守性**: コードベースが理解しやすくなり、バグ修正が迅速化
- **品質**: 単体テストカバレッジ80%以上により、リグレッションリスクを低減
- **拡張性**: 将来的な依存関係処理の拡張（例: 循環依存検出、最適化）が容易
- **開発効率**: 責務が明確になることで、並行開発が可能になる

---

## 2. 機能要件

### FR-1: ResourceDependencyBuilderクラスの新規作成（高）
- **ID**: FR-1
- **優先度**: 高
- **説明**: 依存関係グラフ構築を担当する新規クラスを作成する
- **詳細**:
  - ファイル名: `resource_dependency_builder.py`
  - クラス名: `ResourceDependencyBuilder`
  - すべてのメソッドは静的メソッド（ステートレス設計）
  - DotFileGeneratorから以下のメソッドを抽出:
    - `_create_urn_to_node_mapping()`
    - `_add_dependencies_for_resource()`
    - `_add_direct_dependencies()`
    - `_add_parent_dependency()`
    - `_add_property_dependencies()`

### FR-2: URNマッピング作成機能（高）
- **ID**: FR-2
- **優先度**: 高
- **説明**: リソースのURNからノードIDへのマッピングを作成する
- **詳細**:
  - メソッド名: `create_urn_to_node_mapping(resources: List[Dict]) -> Dict[str, str]`
  - 入力: リソースリスト（最大20個）
  - 出力: URN文字列をキー、ノードID（`resource_{i}`形式）を値とする辞書
  - エッジケース:
    - 空リスト: 空の辞書を返す
    - 重複URN: 最初のリソースのノードIDを使用
    - 不正なURN: スキップ（ログ出力なし、サイレントに処理）

### FR-3: リソース依存関係追加機能（高）
- **ID**: FR-3
- **優先度**: 高
- **説明**: リソース間の依存関係をDOT形式の行として追加する
- **詳細**:
  - メソッド名: `add_resource_dependencies(resources: List[Dict], dot_lines: List[str]) -> None`
  - 入力:
    - `resources`: リソースリスト（最大20個）
    - `dot_lines`: DOT形式の行リスト（破壊的更新）
  - 処理:
    1. リソースが1個以下の場合は何もしない
    2. コメント行を追加: `// リソース間の依存関係`
    3. URNマッピングを作成
    4. 各リソースの依存関係を処理（FR-4）
  - エッジケース:
    - 空リスト: 何もしない
    - 1個のリソース: 何もしない
    - 2個以上: 依存関係処理を実行

### FR-4: 単一リソースの依存関係処理（高）
- **ID**: FR-4
- **優先度**: 高
- **説明**: 単一リソースの全依存関係（直接、親、プロパティ）を処理する
- **詳細**:
  - メソッド名: `add_dependencies_for_resource(resource_index: int, resource: Dict, urn_to_node_id: Dict[str, str], dot_lines: List[str]) -> None`
  - 処理順序:
    1. 直接依存関係を追加（FR-5）
    2. 親依存関係を追加（FR-6）
    3. プロパティ依存関係を追加（FR-7）

### FR-5: 直接依存関係の追加（高）
- **ID**: FR-5
- **優先度**: 高
- **説明**: リソースの直接的な依存関係をDOT形式で追加する
- **詳細**:
  - メソッド名: `_add_direct_dependencies(node_id: str, resource: Dict, urn_to_node_id: Dict[str, str], dot_lines: List[str]) -> None`
  - 入力: `resource.get('dependencies', [])`（URNリスト）
  - 出力: `"{node_id}" -> "{dep_node_id}" [style=solid, color="#9C27B0", fontsize="10"];`
  - エッジケース:
    - 空の依存リスト: 何もしない
    - 存在しないURN: スキップ（URNマッピングに存在しない場合）

### FR-6: 親依存関係の追加（高）
- **ID**: FR-6
- **優先度**: 高
- **説明**: リソースの親への依存関係をDOT形式で追加する
- **詳細**:
  - メソッド名: `_add_parent_dependency(node_id: str, resource: Dict, urn_to_node_id: Dict[str, str], dot_lines: List[str]) -> None`
  - 入力: `resource.get('parent')`（単一URN文字列またはNone）
  - 出力: `"{node_id}" -> "{parent_node_id}" [style=dashed, color="#2196F3", label="parent", fontsize="10"];`
  - エッジケース:
    - parent=None: 何もしない
    - parent=空文字列: 何もしない
    - 存在しないURN: スキップ

### FR-7: プロパティ依存関係の追加（高）
- **ID**: FR-7
- **優先度**: 高
- **説明**: リソースのプロパティ依存関係をDOT形式で追加する
- **詳細**:
  - メソッド名: `_add_property_dependencies(node_id: str, resource: Dict, urn_to_node_id: Dict[str, str], dot_lines: List[str]) -> None`
  - 入力: `resource.get('propertyDependencies', {})`（プロパティ名をキー、URNリストを値とする辞書）
  - 処理:
    - 各プロパティの各URNに対してエッジを生成
    - プロパティ名が長い場合は末尾のみを使用（`prop.split('.')[-1]`）
  - 出力: `"{node_id}" -> "{dep_node_id}" [style=dotted, color="#FF5722", label="{short_prop}", fontsize="9"];`
  - エッジケース:
    - 空の辞書: 何もしない
    - 存在しないURN: スキップ

### FR-8: DotFileProcessorの更新（高）
- **ID**: FR-8
- **優先度**: 高
- **説明**: `DotFileGenerator._add_resource_dependencies()`を`ResourceDependencyBuilder`の呼び出しに置き換える
- **詳細**:
  - 修正対象: `dot_processor.py`の`DotFileGenerator`クラス
  - 修正内容:
    1. `ResourceDependencyBuilder`をimport
    2. `_add_resource_dependencies()`メソッドを以下に変更:
       ```python
       @staticmethod
       def _add_resource_dependencies(resources: List[Dict], dot_lines: List[str]):
           """リソース間の依存関係を追加（ResourceDependencyBuilderに委譲）"""
           ResourceDependencyBuilder.add_resource_dependencies(resources, dot_lines)
       ```
  - 削除対象メソッド（ResourceDependencyBuilderに移動）:
    - `_create_urn_to_node_mapping()`
    - `_add_dependencies_for_resource()`
    - `_add_direct_dependencies()`
    - `_add_parent_dependency()`
    - `_add_property_dependencies()`

### FR-9: 単体テストの作成（高）
- **ID**: FR-9
- **優先度**: 高
- **説明**: `ResourceDependencyBuilder`専用の単体テストを作成する
- **詳細**:
  - ファイル名: `test_resource_dependency_builder.py`
  - カバレッジ目標: 80%以上
  - テストカテゴリ:
    - URNマッピング作成（正常系、エッジケース）
    - 直接依存関係追加（正常系、エッジケース）
    - 親依存関係追加（正常系、エッジケース）
    - プロパティ依存関係追加（正常系、エッジケース）
    - 複合シナリオ（複数の依存関係タイプが混在）

### FR-10: 統合テストの確認（高）
- **ID**: FR-10
- **優先度**: 高
- **説明**: 既存の`test_dot_processor.py`の全テストがパスすることを確認する
- **詳細**:
  - 修正不要: 外部インターフェースは変更しないため
  - 確認項目:
    - 既存の依存関係テストが全てパス
    - エッジケーステストが全てパス
    - 統合テストが全てパス
  - 失敗時の対応:
    - リグレッション調査
    - ResourceDependencyBuilderまたはDotFileProcessorの修正

---

## 3. 非機能要件

### NFR-1: パフォーマンス要件
- **最大リソース数**: 20個（既存仕様を維持）
- **処理時間**: 20リソースの依存関係処理を100ms以内（既存と同等）
- **メモリ使用量**: URNマッピング辞書のメモリ使用量は最大10KB以内

### NFR-2: 信頼性要件
- **エラーハンドリング**: 不正なURN、存在しないURN、Noneなどに対して例外を投げずに処理
- **データ整合性**: URNマッピングと実際のリソースリストの整合性を保証
- **冪等性**: 同じ入力に対して常に同じ出力を生成

### NFR-3: 保守性要件
- **コードカバレッジ**: 単体テストカバレッジ80%以上（必須）
- **ドキュメント**: 各メソッドにdocstring（Args, Returns, Examples）を記述
- **命名規則**: PEP 8準拠、意図が明確な変数名・メソッド名
- **複雑度**: 各メソッドのサイクロマティック複雑度は10以下

### NFR-4: 拡張性要件
- **ステートレス設計**: すべてのメソッドを静的メソッドとして実装
- **疎結合**: ResourceDependencyBuilderは他のクラスに依存しない（typingとreのみ）
- **拡張ポイント**: 新しい依存関係タイプの追加が容易な設計

### NFR-5: セキュリティ要件
- **入力検証**: 不正なURN形式に対してセキュアに処理（例外を投げない）
- **ログ出力**: 機密情報（URN、リソース名）をログに出力しない（本Issue範囲外）

---

## 4. 制約事項

### 技術的制約
- **Python標準ライブラリのみ**: 新規依存パッケージの追加は禁止（typing, reのみ使用）
- **既存インターフェースの維持**: `DotFileGenerator._add_resource_dependencies()`のシグネチャは変更しない
- **最大20リソース**: `create_dot_file()`の仕様により、最大20リソースまで処理
- **DOT形式準拠**: 生成するDOT形式は既存の形式と完全に一致

### リソース制約
- **工数**: 8~12時間（Planning Documentに従う）
- **スコープ**: Phase 2-3のみ（Phase 2-1のUrnProcessorは完了済み）

### ポリシー制約
- **コーディング規約**: PEP 8準拠
- **テスト戦略**: UNIT_INTEGRATION（pytest使用）
- **品質ゲート**: カバレッジ80%以上、既存テストが全てパス

---

## 5. 前提条件

### システム環境
- **Python**: 3.8以上
- **テストフレームワーク**: pytest
- **カバレッジツール**: pytest-cov

### 依存コンポーネント
- **Phase 2-1完了**: `UrnProcessor`クラスが既に抽出済み（Issue #461）
- **Phase 1完了**: 基盤整備が完了（Issue #460）
- **既存ファイル**:
  - `src/dot_processor.py` - 既存コード
  - `tests/test_dot_processor.py` - 既存テスト
  - `tests/conftest.py` - テストfixture

### 外部システム連携
- なし（依存なし）

---

## 6. 受け入れ基準

### AC-1: ResourceDependencyBuilderクラスが単独で動作すること
**Given**: 有効なリソースリストとDOT行リストがある
**When**: `ResourceDependencyBuilder.add_resource_dependencies()`を呼び出す
**Then**:
- 依存関係のDOT行が正しく生成される
- 既存のdot_linesに破壊的に追加される
- 不正なURNが含まれていてもエラーが発生しない

### AC-2: URNマッピングが正しく作成されること
**Given**: 3個のリソースリスト（各リソースは有効なURNを持つ）
**When**: `create_urn_to_node_mapping()`を呼び出す
**Then**:
- 3個のURNとノードIDのマッピングが返される
- ノードIDは`resource_0`, `resource_1`, `resource_2`の形式
- 辞書のキーはURN文字列

### AC-3: 直接依存関係が正しく追加されること
**Given**: resource_0がresource_1に依存している（`dependencies`フィールドに含まれる）
**When**: `add_resource_dependencies()`を呼び出す
**Then**:
- `"resource_0" -> "resource_1" [style=solid, color="#9C27B0", fontsize="10"];`が生成される
- 既存のdot_linesに追加される

### AC-4: 親依存関係が正しく追加されること
**Given**: resource_0の親がresource_1である（`parent`フィールドに含まれる）
**When**: `add_resource_dependencies()`を呼び出す
**Then**:
- `"resource_0" -> "resource_1" [style=dashed, color="#2196F3", label="parent", fontsize="10"];`が生成される
- `style=dashed`が使用される

### AC-5: プロパティ依存関係が正しく追加されること
**Given**: resource_0の`propertyDependencies`に`vpc.id: [resource_1_urn]`が含まれる
**When**: `add_resource_dependencies()`を呼び出す
**Then**:
- `"resource_0" -> "resource_1" [style=dotted, color="#FF5722", label="id", fontsize="9"];`が生成される
- プロパティ名は末尾のみ（`vpc.id` → `id`）

### AC-6: 空リソースリストを処理できること
**Given**: 空のリソースリスト
**When**: `add_resource_dependencies()`を呼び出す
**Then**:
- 何も追加されない
- エラーが発生しない

### AC-7: 1個のリソースリストを処理できること
**Given**: 1個のリソースリスト
**When**: `add_resource_dependencies()`を呼び出す
**Then**:
- 何も追加されない（依存関係がないため）
- エラーが発生しない

### AC-8: 存在しないURNへの依存を安全に処理できること
**Given**: resource_0が存在しないURNに依存している
**When**: `add_resource_dependencies()`を呼び出す
**Then**:
- その依存関係はスキップされる
- エラーが発生しない
- 他の有効な依存関係は正しく処理される

### AC-9: 循環依存を処理できること
**Given**: resource_0がresource_1に依存し、resource_1がresource_0に依存している
**When**: `add_resource_dependencies()`を呼び出す
**Then**:
- 両方の依存関係エッジが生成される
- 無限ループが発生しない

### AC-10: 単体テストのカバレッジが80%以上であること
**Given**: `test_resource_dependency_builder.py`が実装されている
**When**: `pytest --cov=src/resource_dependency_builder`を実行
**Then**:
- カバレッジが80%以上
- すべてのテストがパス

### AC-11: 既存の統合テストが全てパスすること
**Given**: `test_dot_processor.py`の既存テストスイート
**When**: `pytest tests/test_dot_processor.py`を実行
**Then**:
- すべてのテストがパス
- リグレッションが発生していない
- 既存の依存関係テストが正常に動作

### AC-12: DotFileProcessorからResourceDependencyBuilderへの委譲が動作すること
**Given**: `DotFileGenerator._add_resource_dependencies()`が呼び出される
**When**: リソースリストを渡す
**Then**:
- 内部的に`ResourceDependencyBuilder.add_resource_dependencies()`が呼び出される
- 出力結果は既存実装と完全に一致
- 外部インターフェースに変更がない

---

## 7. スコープ外

### 明確にスコープ外とする事項
1. **循環依存の検出**: 循環依存の検出と警告は本Issueの範囲外（将来的な拡張候補）
2. **依存関係の最適化**: 冗長な依存関係の削除や最適化は範囲外
3. **新しい依存関係タイプの追加**: 既存の3種類（直接、親、プロパティ）以外の依存関係タイプは範囲外
4. **エラーログの出力**: 不正なURNや存在しないURNに対するエラーログ出力は範囲外
5. **依存関係の検証**: 依存関係の妥当性検証（例: 型チェック）は範囲外
6. **パフォーマンスの最適化**: 既存実装と同等のパフォーマンスであれば十分（高速化は範囲外）
7. **リソース数の上限変更**: 最大20リソースの制限は変更しない
8. **DOT形式の拡張**: 新しいDOT属性の追加や形式変更は範囲外
9. **他のプロセッサとの統合**: NodeLabelGeneratorやUrnProcessor以外との統合は範囲外
10. **ドキュメントの大規模更新**: README更新は最小限（リファクタリング内容の記録のみ）

### 将来的な拡張候補
1. **Phase 3以降のリファクタリング**: 他のコンポーネント抽出（Issue #448参照）
2. **依存関係グラフの可視化拡張**: インタラクティブなグラフ表示
3. **依存関係分析機能**: 影響範囲分析、クリティカルパス検出
4. **マルチプロバイダー対応の拡張**: プロバイダー固有の依存関係処理

---

## 8. 関連ドキュメント

### Planning Document
- `.ai-workflow/issue-463/00_planning/output/planning.md` - 開発計画全体

### 既存コード
- `src/dot_processor.py` - リファクタリング対象
- `src/urn_processor.py` - Phase 2-1で抽出済み
- `src/node_label_generator.py` - Phase 2-2で抽出済み

### 既存テスト
- `tests/test_dot_processor.py` - 既存の統合テスト
- `tests/conftest.py` - テストfixture

### プロジェクトドキュメント
- `CLAUDE.md` - プロジェクト全体方針とコーディングガイドライン
- `CONTRIBUTION.md` - 開発ガイドライン

---

## 9. 変更履歴

| 日付 | バージョン | 変更内容 | 作成者 |
|------|-----------|---------|--------|
| 2025-01-XX | 1.0 | 初版作成 | AI Requirements Agent (Phase 1) |

---

## 10. レビュー・承認

### 品質ゲート確認

- [x] **機能要件が明確に記載されている**: FR-1からFR-10まで10個の機能要件を定義
- [x] **受け入れ基準が定義されている**: AC-1からAC-12まで12個の受け入れ基準を定義（Given-When-Then形式）
- [x] **スコープが明確である**: スコープ外10項目を明確に記載
- [x] **論理的な矛盾がない**: 機能要件、非機能要件、受け入れ基準の整合性を確認

### レビューチェックリスト

- [ ] 機能要件の優先度は適切か
- [ ] 受け入れ基準は検証可能か
- [ ] 非機能要件は測定可能か
- [ ] スコープ外は明確か
- [ ] Planning Documentとの整合性はあるか
- [ ] 既存コードとの互換性は保たれるか

---

**要件定義書作成日**: 2025-01-XX
**要件定義書バージョン**: 1.0
**作成者**: AI Requirements Agent (Phase 1)
