# dot_processor.py 振る舞い記録ドキュメント

## 概要

このドキュメントは、`dot_processor.py`の既存の振る舞いを記録したものです。リファクタリング時にこの振る舞いが維持されていることを確認するために使用します。

## DotFileGenerator クラス

### `escape_dot_string(s: str) -> str`

**目的**: DOT形式用の特殊文字エスケープ

**期待動作**:
- ダブルクォート (`"`) → `\"`
- バックスラッシュ (`\`) → `\\`
- 改行 (`\n`) → `\n` (エスケープ)
- タブ (`\t`) → `\t` (エスケープ)
- キャリッジリターン (`\r`) → 削除
- 空文字列 → 空文字列（エラーなし）
- None値 → None（エラーなし）
- Unicode文字 → そのまま出力（エラーなし）

**エッジケース**:
- None値: そのまま返される
- 極端に長い文字列（10000文字以上）: エスケープ処理が正常に動作

### `create_dot_file(stack_name, resources, resource_providers) -> List[str]`

**目的**: DOTファイル生成

**期待動作**:
- ヘッダー: `digraph G {`で開始
- スタックノード: 中央に配置、楕円形
- プロバイダーノード: フォルダー形状、色設定適用
- リソース: 最大20個まで処理
- 依存関係: エッジとして表現（通常依存、親依存、プロパティ依存）
- フッター: `}`で終了

**エッジケース**:
- 空リソース: スタックノードのみ生成
- 21個以上のリソース: 最初の20個のみ処理
- 未定義プロバイダー: デフォルト色を適用（`#E3F2FD`, `#1565C0`）

### プロバイダー色設定

**定義済みプロバイダー**:
- AWS: `#FFF3E0` (fill), `#EF6C00` (border)
- Azure: `#E3F2FD` (fill), `#0078D4` (border)
- GCP: `#E8F5E9` (fill), `#4285F4` (border)
- Kubernetes: `#E8EAF6` (fill), `#326DE6` (border)
- Pulumi: `#F3E5F5` (fill), `#6A1B9A` (border)

**デフォルト色**: `#E3F2FD` (fill), `#1565C0` (border)

## UrnProcessor クラス

**概要**: Phase 2-1リファクタリング（Issue #461）により、URN処理の責務を`DotFileProcessor`から分離しました。URN/URI処理に特化した独立クラスです。

### `parse_urn(urn: str) -> Dict[str, str]`

**目的**: Pulumi URN形式の解析

**URN形式**: `urn:pulumi:STACK::PROJECT::PROVIDER:MODULE/TYPE:TYPE::NAME`

**期待動作**:
- 正常なURN: 辞書形式で構成要素を返す
  - キー: `stack`, `project`, `provider`, `module`, `type`, `name`, `full_urn`
- 不正なURN: デフォルト値を含む辞書を返す（エラーなし）
  - `provider`: `'unknown'`
  - `type`: `'unknown'`
- 空文字列: デフォルト値を含む辞書を返す（エラーなし）

**エッジケース**:
- 部分的なURN: デフォルト値で補完
- 極端に長いURN: 正常に解析（パフォーマンスは低下する可能性）
- プロバイダー情報なし: `provider='unknown'`

### `create_readable_label(urn_info: Dict) -> str`

**目的**: 読みやすいラベル生成

**期待動作**:
- 改行区切りで`module`, `type`, `name`を表示
- モジュール名が空の場合: `type`, `name`のみ表示
- 長いタイプ名: 省略処理（30文字以内）

**エッジケース**:
- モジュール名が空: `type\nname`の形式
- 長いタイプ名: キャメルケースを分割して主要部分のみ表示

### `is_stack_resource(urn: str) -> bool`

**目的**: スタックリソース判定

**期待動作**:
- スタックURN（`pulumi:pulumi:Stack`を含む）: `True`
- 通常リソースURN: `False`

**エッジケース**:
- 不正なURN: `False`
- 空文字列: `False`

## DotFileProcessor クラス

**概要**: Phase 2-1リファクタリング（Issue #461）により、URN処理を`UrnProcessor`に委譲しました。DOT処理に専念します。

### `apply_graph_styling(dot_content: str) -> str`

**目的**: グラフスタイル適用

**期待動作**:
- Pulumi生成グラフ（`strict digraph`で始まる）: グラフ拡張処理を適用
  - グラフ属性、ノード属性、エッジ属性を追加
  - URNラベルを読みやすい形式に変換
  - スタックノードに特別なスタイル適用
- 自前生成グラフ（`digraph G {`で始まる）: スタイル設定を置換
  - `STYLE_SETTINGS`に置換
  - ノードラベルを処理

**エッジケース**:
- 空グラフ: そのまま返される（または最小限の変更）
- 不正なDOT形式: エラーが発生する可能性

### `is_empty_graph(dot_content: str) -> bool`

**目的**: 空グラフ判定

**期待動作**:
- `digraph G {}`: `True`
- 30文字未満の文字列: `True`
- それ以外: `False`

**エッジケース**:
- ちょうど30文字: `False`（30文字以上なので空でない）

**注意**: URN処理関連のメソッド（`parse_urn`, `create_readable_label`, `is_stack_resource`）は、Phase 2-1リファクタリングにより`UrnProcessor`クラスに移動しました。`DotFileProcessor`は内部で`UrnProcessor`を呼び出しますが、外部から見た振る舞いは変更ありません。

## ResourceDependencyBuilder クラス

**概要**: Phase 2-3リファクタリング（Issue #463）により、依存関係処理の責務を`DotFileProcessor`から分離しました。依存関係グラフ構築に特化した独立クラスです。

### `add_resource_dependencies(resources: List[Dict], dot_lines: List[str]) -> None`

**目的**: リソース間の依存関係をDOT形式で追加

**期待動作**:
- リソースが1個以下の場合: 何もしない（早期リターン）
- リソースが2個以上の場合: コメント行追加と依存関係処理を実行
- URNマッピングを作成後、各リソースの依存関係を順次処理
- 破壊的更新: `dot_lines`リストに直接追加

**エッジケース**:
- 空リスト: 何もしない
- 1個のリソース: 何もしない
- 不正なURNが含まれていても処理を継続

### `create_urn_to_node_mapping(resources: List[Dict]) -> Dict[str, str]`

**目的**: URNからノードIDへのマッピング作成

**期待動作**:
- 各リソースのURNを`resource_{i}`形式のノードIDにマッピング
- 空リスト: 空の辞書を返す
- 重複URN: 最後のリソースのノードIDで上書き
- 'urn'キーなし: 空文字列をキーとして扱う

### 依存関係の種類

### 通常依存（dependencies）
- **スタイル**: `solid`
- **色**: `#9C27B0`（紫）
- **説明**: リソース間の直接的な依存関係
- **処理**: `_add_direct_dependencies()`メソッド

### 親依存（parent）
- **スタイル**: `dashed`
- **色**: `#2196F3`（青）
- **ラベル**: `"parent"`
- **説明**: 親子関係による依存
- **処理**: `_add_parent_dependency()`メソッド

### プロパティ依存（propertyDependencies）
- **スタイル**: `dotted`
- **色**: `#FF5722`（オレンジ）
- **ラベル**: プロパティ名（短縮形）
- **説明**: プロパティ値による依存
- **処理**: `_add_property_dependencies()`メソッド
- **プロパティ名短縮**: `vpc.subnet.id` → `id`（ドット区切りの末尾のみ使用）

## テスト実行時の注意事項

1. **既存の振る舞いを記録する**: 現在のコードがどのように動作するかを記録し、将来のリファクタリング時に比較できるようにする
2. **正解を決めつけない**: 既存コードの出力が「正解」である。もし期待と異なる動作があっても、まずは記録する
3. **Golden Masterパターン**: 初回実行時の出力を「Golden Master」として保存し、以降のテストで比較

## 更新履歴

| 日付 | バージョン | 変更者 | 変更内容 |
|------|-----------|--------|----------|
| 2025-01-19 | 1.0 | Claude Code | 初版作成（テスト実装前の設計版） |
| 2025-01-19 | 2.0 | Claude Code | Phase 2-1リファクタリング（Issue #461）反映：UrnProcessorクラスの分離 |

---

**注意**: このドキュメントは、テスト実装後に実際の振る舞いを記録して完成させます。Phase 5（テストコード実装）およびPhase 6（テスト実行）で更新されます。

## リファクタリング記録

### Phase 2-1: Issue #461 - UrnProcessorクラスの抽出

**実施日**: 2025-01-19

2025-01-19に実施されたPhase 2-1リファクタリングにより、URN処理の責務を`DotFileProcessor`から分離し、新規クラス`UrnProcessor`を作成しました。

**目的**: 単一責務の原則（SRP）の適用

**変更内容**:
- 新規作成: `src/urn_processor.py`（`UrnProcessor`クラス）
- 修正: `src/dot_processor.py`（URN関連メソッドの削除、`UrnProcessor`の呼び出しに置き換え）
- 新規作成: `tests/test_urn_processor.py`（ユニットテスト）

**影響**:
- 外部から見た`DotFileProcessor`の振る舞いは完全に維持されています
- 内部実装のみ変更（URN処理を`UrnProcessor`に委譲）

**関連ドキュメント**:
- 要件定義: `.ai-workflow/issue-461/01_requirements/output/requirements.md`
- 設計書: `.ai-workflow/issue-461/02_design/output/design.md`
- 実装ログ: `.ai-workflow/issue-461/04_implementation/output/implementation.md`

### Phase 2-3: Issue #463 - ResourceDependencyBuilderクラスの抽出

**実施日**: 2025-01-XX

Phase 2-3リファクタリングにより、依存関係処理の責務を`DotFileProcessor`から分離し、新規クラス`ResourceDependencyBuilder`を作成しました。

**目的**: 単一責務の原則（SRP）の適用、テスト容易性の向上

**変更内容**:
- 新規作成: `src/resource_dependency_builder.py`（`ResourceDependencyBuilder`クラス）
- 修正: `src/dot_processor.py`（依存関係処理メソッドの削除、`ResourceDependencyBuilder`の呼び出しに置き換え）
- 新規作成: `tests/test_resource_dependency_builder.py`（ユニットテスト、37ケース）

**影響**:
- 外部から見た`DotFileProcessor`の振る舞いは完全に維持されています
- 内部実装のみ変更（依存関係処理を`ResourceDependencyBuilder`に委譲）
- カバレッジ目標: 80%以上（推定90%以上）

**関連ドキュメント**:
- 要件定義: `.ai-workflow/issue-463/01_requirements/output/requirements.md`
- 設計書: `.ai-workflow/issue-463/02_design/output/design.md`
- 実装ログ: `.ai-workflow/issue-463/04_implementation/output/implementation.md`
