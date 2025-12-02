# 要件定義書: Issue #448

## 基本情報

- **Issue番号**: #448
- **タイトル**: [Refactor] 複雑度の削減: dot_processor.py
- **作成日**: 2025-01-14
- **ステータス**: Requirements Phase
- **実装戦略**: REFACTOR（リファクタリング）
- **テスト戦略**: UNIT_INTEGRATION（ユニット＋統合テスト）
- **テストコード戦略**: CREATE_TEST（新規テスト作成）

---

## 0. Planning Documentの確認

### 開発計画の全体像

**Planning Phase成果物**: [planning.md](../../00_planning/output/planning.md)

#### スコープと実装戦略
- **実装戦略**: REFACTOR
  - 既存の公開APIは維持し、内部実装のみをリファクタリング
  - Extract Classパターン、Guard Clauseパターンを適用
  - 振る舞いは変えず、コードの保守性・可読性を向上

#### テスト戦略
- **UNIT_INTEGRATION**: 新規クラスのユニットテストと、統合後の動作確認テスト
- **CREATE_TEST**: 現在テストファイルが存在しないため、新規作成が必須

#### 主要なリスク
1. **テストカバレッジの欠如によるリグレッション**（影響度: 高、確率: 中）
   - 軽減策: Phase 3で特性テストを優先的に作成
2. **外部依存による予期しない破壊的変更**（影響度: 中、確率: 中）
   - 軽減策: Phase 1で`graph_processor.py`等の依存関係を徹底調査
3. **URNパースロジックのエッジケース対応漏れ**（影響度: 中、確率: 高）
   - 軽減策: Phase 3でエッジケースのテストシナリオを網羅的に作成

#### スケジュール
- **見積もり工数**: 20〜28時間
  - Phase 1: 要件定義（2〜3h）
  - Phase 2: 設計（3〜4h）
  - Phase 3: テストシナリオ（2〜3h）
  - Phase 4: 実装（6〜8h）
  - Phase 5: テストコード実装（4〜6h）
  - Phase 6: テスト実行（1〜2h）
  - Phase 7: ドキュメント（1〜2h）
  - Phase 8: レポート（1h）

---

## 1. 概要

### 背景

`DotFileProcessor`クラスは、Pulumiが生成したDOTファイル（依存関係グラフ）を処理し、視覚的に改善された形式で出力する責務を担っています。しかし、現在のコードは以下の問題を抱えています：

- **深いネスト構造**: `_enhance_pulumi_graph`および`_process_node_definition`メソッドにおいて5レベル以上のネストが存在（397〜473行目）
- **責務の混在**: URIパース、ノードラベル生成、依存関係処理などの異なる責務が単一クラスに混在
- **メソッドの分散**: 40以上のメソッドに処理が分散しており、全体像の把握が困難
- **複雑な状態追跡**: 複雑な状態追跡ロジックが各所に散在し、バグの温床となっている
- **テストの欠如**: テストファイルが存在せず、振る舞いの保証がない

### 目的

本リファクタリングの目的は、**責務の分離と構造の簡素化により、保守性と可読性を大幅に向上させる**ことです。具体的には：

1. **Extract Classパターン**の適用により、3つの新規クラスを抽出
   - `UrnProcessor`: URN/URIのパース、正規化、コンポーネント抽出
   - `NodeLabelGenerator`: リソースタイプに応じたラベル生成ロジック
   - `ResourceDependencyBuilder`: 依存関係グラフの構築と検証

2. **Guard Clauseパターン**の適用により、ネストレベルを3以下に削減

3. **特性テストの作成**により、リファクタリング前後の振る舞い同一性を保証

### ビジネス価値・技術的価値

#### ビジネス価値
- **開発速度の向上**: コードの理解に要する時間が短縮され、新機能追加が容易に
- **品質の向上**: バグの発生リスクが低減し、安定したサービス提供が可能に
- **保守コストの削減**: 技術的負債の解消により、長期的な保守コストが大幅に削減

#### 技術的価値
- **可読性の向上**: 各クラスの責務が明確化され、単一責任の原則に準拠
- **テスタビリティの向上**: クラスごとのユニットテストが容易になり、カバレッジが向上
- **拡張性の向上**: コードの再利用性が高まり、将来的な機能拡張が容易に
- **認知的複雑度の削減**: ネストレベルの削減により、コードの理解が容易に

---

## 2. 機能要件

### FR-001: UrnProcessorクラスの抽出（優先度: 高）

**概要**: URN/URIのパース、正規化、コンポーネント抽出の責務を独立したクラスに分離する。

**詳細仕様**:
- **移行対象メソッド**:
  - `DotFileProcessor.parse_urn()` → `UrnProcessor.parse_urn()`
  - `DotFileProcessor._parse_provider_type()` → `UrnProcessor._parse_provider_type()`

- **公開メソッド**:
  - `parse_urn(urn: str) -> Dict[str, str]`: URNを解析し、構成要素を辞書形式で返す
    - 戻り値: `{'stack': str, 'project': str, 'provider': str, 'module': str, 'type': str, 'name': str, 'full_urn': str}`

- **プライベートメソッド**:
  - `_parse_provider_type(provider_type: str) -> Dict[str, str]`: プロバイダータイプ文字列を解析

**受け入れ基準**:
- Given: 有効なURN文字列 `urn:pulumi:dev::myproject::aws:ec2/instance:Instance::webserver`
- When: `parse_urn()`を呼び出す
- Then: 各構成要素が正しく抽出され、辞書形式で返される

- Given: 不正なURN形式（`::`が不足、空文字列、None等）
- When: `parse_urn()`を呼び出す
- Then: 例外をスローせず、デフォルト値を含む辞書を返す

### FR-002: NodeLabelGeneratorクラスの抽出（優先度: 高）

**概要**: リソースタイプに応じたラベル生成ロジックを独立したクラスに分離する。

**詳細仕様**:
- **移行対象メソッド**:
  - `DotFileProcessor.create_readable_label()` → `NodeLabelGenerator.create_readable_label()`
  - `DotFileProcessor._format_resource_type()` → `NodeLabelGenerator._format_resource_type()`

- **公開メソッド**:
  - `create_readable_label(urn_info: Dict[str, str]) -> str`: URN情報から読みやすいラベルを生成
    - 入力: `parse_urn()`の戻り値形式の辞書
    - 戻り値: 改行区切りのラベル文字列（`モジュール名\nリソースタイプ\nリソース名`）

- **プライベートメソッド**:
  - `_format_resource_type(resource_type: str) -> str`: リソースタイプを読みやすい形式にフォーマット

**受け入れ基準**:
- Given: 標準的なURN情報（モジュール名あり）
- When: `create_readable_label()`を呼び出す
- Then: `モジュール名\nリソースタイプ\nリソース名`の形式でラベルが生成される

- Given: 30文字を超える長いリソースタイプ名
- When: `create_readable_label()`を呼び出す
- Then: リソースタイプが適切に省略される（例: `FirstSecond...Last`）

- Given: 特殊文字を含むリソース名
- When: `create_readable_label()`を呼び出す
- Then: DOT形式向けに適切にエスケープされる

### FR-003: ResourceDependencyBuilderクラスの抽出（優先度: 高）

**概要**: 依存関係グラフの構築と検証の責務を独立したクラスに分離する。

**詳細仕様**:
- **移行対象メソッド**:
  - `DotFileProcessor._process_graph_line()` → 部分的に移行
  - `DotFileProcessor._process_node_definition()` → 部分的に移行
  - `DotFileProcessor._process_edge_definition()` → 部分的に移行

- **公開メソッド**:
  - `build_dependency_graph(resources: List[Dict]) -> List[str]`: リソースリストから依存関係グラフを構築
    - 入力: リソース情報のリスト
    - 戻り値: DOT形式のエッジ定義のリスト

- **内部機能**:
  - ノードIDマッピングの管理（URN → ノードID）
  - 通常の依存関係、親リソース依存、プロパティ依存の処理
  - エッジ属性の管理（style, color, label）

**受け入れ基準**:
- Given: 単純な依存関係を持つリソースリスト
- When: `build_dependency_graph()`を呼び出す
- Then: 正しいDOT形式のエッジ定義が生成される

- Given: 循環依存を含むリソースリスト
- When: `build_dependency_graph()`を呼び出す
- Then: 循環依存が検出され、警告が出力される（またはエラー）

- Given: 依存先が存在しないリソース
- When: `build_dependency_graph()`を呼び出す
- Then: エラーをスローせず、該当する依存関係をスキップする

### FR-004: DotFileProcessorの統合（優先度: 高）

**概要**: 新規クラスを統合し、既存の公開APIを維持しつつ内部実装をリファクタリングする。

**詳細仕様**:
- **依存性注入**: 新規クラスのインスタンスをコンストラクタで受け取る（または内部で生成）
  ```python
  class DotFileProcessor:
      def __init__(self):
          self.urn_processor = UrnProcessor()
          self.label_generator = NodeLabelGenerator()
          self.dependency_builder = ResourceDependencyBuilder()
  ```

- **既存メソッドの委譲**:
  - `parse_urn()` → `self.urn_processor.parse_urn()`に委譲
  - `create_readable_label()` → `self.label_generator.create_readable_label()`に委譲

- **公開APIの維持**: 既存の公開メソッドのシグネチャは一切変更しない

**受け入れ基準**:
- Given: リファクタリング後の`DotFileProcessor`
- When: 既存の公開メソッド（`parse_urn()`, `create_readable_label()`等）を呼び出す
- Then: リファクタリング前と同じ結果が返される（特性テストで確認）

### FR-005: 制御フローの簡素化（優先度: 高）

**概要**: Guard Clauseパターンを適用し、5レベル以上のネストを3レベル以下に削減する。

**詳細仕様**:
- **対象メソッド**:
  - `_enhance_pulumi_graph()`: ネスト構造を早期リターンで平坦化
  - `_process_node_definition()`: 条件分岐を早期リターンで簡素化
  - その他、ネストレベルが4以上のメソッド

- **パターン適用例**:
  ```python
  # Before: 深いネスト
  if condition1:
      if condition2:
          if condition3:
              process()

  # After: 早期リターン
  if not condition1:
      return default_value
  if not condition2:
      return default_value
  if not condition3:
      return default_value
  process()
  ```

**受け入れ基準**:
- Given: リファクタリング後の全メソッド
- When: 静的解析ツールでCyclomatic Complexityを測定
- Then: すべてのメソッドでCyclomatic Complexity < 10を達成

- Given: リファクタリング後の全メソッド
- When: ネストレベルを測定
- Then: すべてのメソッドで最大ネストレベル ≤ 3を達成

---

## 3. 非機能要件

### NFR-001: パフォーマンス要件

- **処理時間**: リファクタリング後の処理時間が、リファクタリング前の±10%以内であること
- **メモリ使用量**: リファクタリング前後でメモリ使用量に大きな差がないこと（±20%以内）
- **測定方法**: Phase 6でパフォーマンステストを実施し、結果を記録

### NFR-002: セキュリティ要件

- **入力検証**: URNパース時に不正な入力（極端に長い文字列、制御文字等）を安全に処理すること
- **エスケープ処理**: DOT形式への出力時に、特殊文字を適切にエスケープすること
- **例外処理**: 想定外の入力でも例外がスローされず、デフォルト値を返すこと

### NFR-003: 可用性・信頼性要件

- **後方互換性**: 既存の公開APIを変更せず、外部からの利用に影響を与えないこと
- **エラーハンドリング**: エラー発生時も処理を中断せず、適切なフォールバック処理を実行すること
- **冪等性**: 同じ入力に対して常に同じ出力を返すこと

### NFR-004: 保守性・拡張性要件

- **単一責任の原則**: 各クラスは1つの責務のみを持つこと
- **疎結合**: クラス間の依存関係を最小限に抑え、依存性注入パターンを活用すること
- **テストカバレッジ**: ユニットテストで90%以上のカバレッジを達成すること
- **ドキュメント**: 各クラス・メソッドにdocstringを記載し、使用方法を明確にすること

---

## 4. 制約事項

### 技術的制約

- **使用技術**: Python 3.8以上（既存環境に準拠）
- **標準ライブラリのみ**: 新規の外部依存を追加しない（`re`, `typing`のみ使用）
- **既存システムとの整合性**: `graph_processor.py`からのインポート構造を維持

### リソース制約

- **時間**: 20〜28時間（Phase 1〜8の合計）
- **人員**: 1名（必要に応じてレビュアー2名）
- **予算**: なし（既存リソース内で実施）

### ポリシー制約

- **セキュリティポリシー**: 入力検証とエスケープ処理を徹底
- **コーディング規約**: PEP 8に準拠
- **型ヒント**: すべての公開メソッドに型ヒントを付与

---

## 5. 前提条件

### システム環境

- **Python**: 3.8以上
- **実行環境**: Jenkins Pipeline内での実行
- **依存ライブラリ**: 標準ライブラリのみ

### 依存コンポーネント

- **graph_processor.py**: `DotFileProcessor`を利用（インポート構造の変更なし）
- **main.py**: 間接的に`DotFileProcessor`を利用（影響範囲の調査が必要）
- **report_generator.py**: 間接的に影響を受ける可能性（Phase 1で確認）

### 外部システム連携

- **Graphviz**: DOTファイルのレンダリングに使用（既存の依存関係を維持）

---

## 6. 受け入れ基準

### AC-001: UrnProcessorクラスの受け入れ基準

- **Given**: 有効なURN文字列 `urn:pulumi:dev::myproject::aws:ec2/instance:Instance::webserver`
- **When**: `UrnProcessor.parse_urn()`を呼び出す
- **Then**:
  - `stack` = `dev`
  - `project` = `myproject`
  - `provider` = `aws`
  - `module` = `ec2`
  - `type` = `Instance`
  - `name` = `webserver`

### AC-002: NodeLabelGeneratorクラスの受け入れ基準

- **Given**: URN情報 `{'provider': 'aws', 'module': 'ec2', 'type': 'Instance', 'name': 'webserver'}`
- **When**: `NodeLabelGenerator.create_readable_label()`を呼び出す
- **Then**: ラベルが `ec2\nInstance\nwebserver` の形式で返される

### AC-003: ResourceDependencyBuilderクラスの受け入れ基準

- **Given**: 2つのリソースを含むリスト（リソースAがリソースBに依存）
- **When**: `ResourceDependencyBuilder.build_dependency_graph()`を呼び出す
- **Then**: `resource_0 -> resource_1` の形式でエッジ定義が返される

### AC-004: DotFileProcessorの統合の受け入れ基準

- **Given**: リファクタリング前後の`DotFileProcessor`
- **When**: 同一の入力（URN、リソースリスト等）で各メソッドを呼び出す
- **Then**: 出力が完全に一致する（特性テストで確認）

### AC-005: 制御フローの簡素化の受け入れ基準

- **Given**: リファクタリング後のすべてのメソッド
- **When**: 静的解析ツール（radon等）でCyclomatic Complexityを測定
- **Then**: すべてのメソッドでCyclomatic Complexity < 10

### AC-006: テストカバレッジの受け入れ基準

- **Given**: 新規作成されたユニットテスト
- **When**: pytest-covを使用してカバレッジを測定
- **Then**: Statement Coverage ≥ 90%

### AC-007: パフォーマンスの受け入れ基準

- **Given**: リファクタリング前後の実装
- **When**: 同一の入力で100回実行し、平均処理時間を測定
- **Then**: リファクタリング後の処理時間が、リファクタリング前の±10%以内

### AC-008: ドキュメントの受け入れ基準

- **Given**: 新規作成されたすべてのクラス・メソッド
- **When**: docstringの存在を確認
- **Then**: すべての公開クラス・メソッドにdocstringが記載されている

---

## 7. スコープ外

### 明確にスコープ外とする事項

1. **DotFileGeneratorクラスのリファクタリング**: 今回は`DotFileProcessor`クラスのみが対象
2. **graph_processor.pyのリファクタリング**: 依存関係の調査は実施するが、リファクタリングは実施しない
3. **新規機能の追加**: リファクタリングのみを実施し、機能追加は行わない
4. **外部ライブラリの導入**: 標準ライブラリのみを使用し、新規依存は追加しない

### 将来的な拡張候補

1. **Strategy パターンの適用**: ノードタイプごとの処理を戦略クラスとして分離（必要に応じて）
2. **Factoryパターンの導入**: プロバイダー別の処理を動的に切り替え可能にする
3. **キャッシュ機構の追加**: URNパース結果をキャッシュし、パフォーマンスを向上
4. **プラグイン機構**: カスタムプロバイダーのサポートを容易にする

---

## 8. 影響範囲

### 主要対象ファイル

1. **jenkins/jobs/pipeline/infrastructure/pulumi-stack-action/src/dot_processor.py** (618行)
   - `DotFileProcessor`クラスを3つの新規クラスに分離
   - 既存メソッドの内部実装を変更（公開APIは維持）

### 新規作成ファイル

1. **jenkins/jobs/pipeline/infrastructure/pulumi-stack-action/src/urn_processor.py**
   - 責務: URN/URIのパース、正規化、コンポーネント抽出
   - 移行元: `DotFileProcessor.parse_urn()`, `_parse_provider_type()`

2. **jenkins/jobs/pipeline/infrastructure/pulumi-stack-action/src/node_label_generator.py**
   - 責務: リソースタイプに応じたラベル生成ロジック
   - 移行元: `DotFileProcessor.create_readable_label()`, `_format_resource_type()`

3. **jenkins/jobs/pipeline/infrastructure/pulumi-stack-action/src/resource_dependency_builder.py**
   - 責務: 依存関係グラフの構築と検証
   - 移行元: `DotFileProcessor._process_graph_line()`, `_process_node_definition()`, `_process_edge_definition()`の一部

4. **tests/unit/test_urn_processor.py**
   - `UrnProcessor`のユニットテスト

5. **tests/unit/test_node_label_generator.py**
   - `NodeLabelGenerator`のユニットテスト

6. **tests/unit/test_resource_dependency_builder.py**
   - `ResourceDependencyBuilder`のユニットテスト

7. **tests/integration/test_dot_processor.py**
   - `DotFileProcessor`の統合テスト（特性テストを含む）

8. **tests/fixtures/sample_urns.json**
   - テストデータ（サンプルURN）

9. **tests/conftest.py**
   - pytest設定とフィクスチャ定義

### 間接的に影響を受けるファイル

1. **graph_processor.py** (175行)
   - インポート文: `from dot_processor import DotFileGenerator, DotFileProcessor`
   - 影響: なし（公開APIは維持されるため）
   - 調査事項: Phase 1で詳細な使用箇所を確認

2. **main.py** (31行)
   - 間接的な依存関係の可能性
   - 調査事項: Phase 1で`dot_processor`の使用を確認

3. **report_generator.py** (150行)
   - 間接的な依存関係の可能性
   - 調査事項: Phase 1で`dot_processor`の使用を確認

### パッケージ構造の変更

```
jenkins/jobs/pipeline/infrastructure/pulumi-stack-action/src/
├── dot_processor.py (既存: リファクタリング対象)
├── urn_processor.py (新規: URN処理を分離)
├── node_label_generator.py (新規: ラベル生成を分離)
├── resource_dependency_builder.py (新規: 依存関係処理を分離)
├── graph_processor.py (既存: 影響確認が必要)
├── main.py (既存: 影響確認が必要)
└── ...

jenkins/jobs/pipeline/infrastructure/pulumi-stack-action/tests/ (新規作成)
├── unit/
│   ├── test_urn_processor.py
│   ├── test_node_label_generator.py
│   └── test_resource_dependency_builder.py
├── integration/
│   └── test_dot_processor.py
├── fixtures/
│   ├── sample_urns.json
│   └── sample_dot_files/
└── conftest.py (pytest設定)
```

---

## 9. 技術的詳細

### 9.1 現状の問題箇所の詳細

#### 深いネスト構造（dot_processor.py: 397〜473行目）

**_enhance_pulumi_graph メソッド**:
```python
def _enhance_pulumi_graph(dot_content: str) -> str:
    lines = dot_content.split('\n')
    new_lines = []
    node_urn_map = {}
    stack_node_id = None

    for i, line in enumerate(lines):  # レベル1
        if i == 0 and 'strict digraph' in line:  # レベル2
            new_lines.extend(DotFileProcessor._add_graph_header(line))
        else:
            processed_line, node_info = DotFileProcessor._process_graph_line(
                line, node_urn_map, stack_node_id
            )

            if node_info:  # レベル2
                node_urn_map.update(node_info.get('node_urn_map', {}))
                if node_info.get('stack_node_id'):  # レベル3
                    stack_node_id = node_info['stack_node_id']

            if processed_line:  # レベル2
                new_lines.append(processed_line)

    return '\n'.join(new_lines)
```

**_process_node_definition メソッド**:
```python
def _process_node_definition(line: str) -> Tuple[str, Dict]:
    node_id = line.strip().split('[')[0].strip()

    urn_match = re.search(r'label="([^"]+)"', line)
    if not urn_match:  # レベル1
        return line, None

    urn = urn_match.group(1)
    urn_info = DotFileProcessor.parse_urn(urn)

    # ノード属性を生成
    node_attrs = DotFileProcessor._generate_node_attributes(urn, urn_info)

    # 新しいノード定義
    new_line = f'    {node_id} [{node_attrs}];'

    # メタデータを返す
    result_info = {'node_urn_map': {node_id: urn_info}}
    if DotFileProcessor.is_stack_resource(urn):  # レベル1
        result_info['stack_node_id'] = node_id

    return new_line, result_info
```

### 9.2 リファクタリング後の構造

#### UrnProcessor クラス

```python
class UrnProcessor:
    """URN/URI のパース、正規化、コンポーネント抽出を担当"""

    @staticmethod
    def parse_urn(urn: str) -> Dict[str, str]:
        """URNをパースして構成要素を抽出

        Args:
            urn: Pulumi URN文字列（例: urn:pulumi:STACK::PROJECT::PROVIDER:MODULE/TYPE:TYPE::NAME）

        Returns:
            URN構成要素の辞書
            {
                'stack': str,
                'project': str,
                'provider': str,
                'module': str,
                'type': str,
                'name': str,
                'full_urn': str
            }
        """
        # 実装内容は既存の parse_urn() から移行
        pass

    @staticmethod
    def _parse_provider_type(provider_type: str) -> Dict[str, str]:
        """プロバイダータイプ文字列を解析

        Args:
            provider_type: プロバイダータイプ文字列（例: aws:ec2/instance:Instance）

        Returns:
            プロバイダー情報の辞書 {'provider': str, 'module': str, 'type': str}
        """
        # 実装内容は既存の _parse_provider_type() から移行
        pass
```

#### NodeLabelGenerator クラス

```python
class NodeLabelGenerator:
    """リソースタイプに応じたラベル生成を担当"""

    @staticmethod
    def create_readable_label(urn_info: Dict[str, str]) -> str:
        """URN情報から読みやすいラベルを生成

        Args:
            urn_info: parse_urn() の戻り値

        Returns:
            改行区切りのラベル文字列（モジュール名\\nリソースタイプ\\nリソース名）
        """
        # 実装内容は既存の create_readable_label() から移行
        pass

    @staticmethod
    def _format_resource_type(resource_type: str) -> str:
        """リソースタイプを読みやすい形式にフォーマット

        Args:
            resource_type: リソースタイプ文字列

        Returns:
            フォーマット済みのリソースタイプ
        """
        # 実装内容は既存の _format_resource_type() から移行
        pass
```

#### ResourceDependencyBuilder クラス

```python
class ResourceDependencyBuilder:
    """依存関係グラフの構築と検証を担当"""

    def __init__(self):
        self.node_urn_map: Dict[str, Dict[str, str]] = {}

    def build_dependency_graph(self, resources: List[Dict]) -> List[str]:
        """リソースリストから依存関係グラフを構築

        Args:
            resources: リソース情報のリスト

        Returns:
            DOT形式のエッジ定義のリスト
        """
        # 新規実装（既存の _process_graph_line() 等から抽出）
        pass

    def _create_urn_to_node_mapping(self, resources: List[Dict]) -> Dict[str, str]:
        """URNからノードIDへのマッピングを作成"""
        pass
```

#### リファクタリング後の DotFileProcessor

```python
class DotFileProcessor:
    """DOTファイル処理の責務を分離"""

    def __init__(self):
        self.urn_processor = UrnProcessor()
        self.label_generator = NodeLabelGenerator()
        self.dependency_builder = ResourceDependencyBuilder()

    @staticmethod
    def parse_urn(urn: str) -> Dict[str, str]:
        """既存の公開API（後方互換性のため維持）"""
        processor = UrnProcessor()
        return processor.parse_urn(urn)

    @staticmethod
    def create_readable_label(urn_info: Dict[str, str]) -> str:
        """既存の公開API（後方互換性のため維持）"""
        generator = NodeLabelGenerator()
        return generator.create_readable_label(urn_info)

    # その他のメソッドは新規クラスに委譲
```

---

## 10. リスクと軽減策

### リスク1: テストカバレッジの欠如によるリグレッション

- **影響度**: 高
- **確率**: 中
- **軽減策**:
  1. Phase 3で特性テスト（リファクタリング前の振る舞いを固定）を優先的に作成
  2. Phase 4で段階的リファクタリング（1クラスずつ抽出し、都度テスト実行）
  3. Phase 6で統合テストと回帰テストを徹底実施
  4. カバレッジ目標を90%以上に設定し、未カバー箇所を最小化

### リスク2: 外部依存による予期しない破壊的変更

- **影響度**: 中
- **確率**: 中
- **軽減策**:
  1. Phase 1で`graph_processor.py`, `main.py`, `report_generator.py`の依存関係を徹底調査
  2. 公開API（外部から呼び出されているメソッド）を明確化し、変更禁止リストを作成
  3. Phase 4で既存の公開APIは変更せず、内部実装のみをリファクタリング
  4. Phase 6で統合テストにより外部モジュールとの連携を確認

### リスク3: URNパースロジックのエッジケース対応漏れ

- **影響度**: 中
- **確率**: 高
- **軽減策**:
  1. Phase 1で既存コードから実際のURN形式のサンプルを収集
  2. Phase 3でエッジケース（特殊文字、長いURN、不正形式）のテストシナリオを網羅的に作成
  3. Phase 5でパラメタライズドテストを活用し、多様なURN形式をテスト
  4. Phase 6でPulumi実環境から取得したDOTファイルでE2Eテストを実施

### リスク4: リファクタリング工数の見積もり超過

- **影響度**: 低
- **確率**: 中
- **軽減策**:
  1. Phase 4を4つのサブタスクに分割し、各タスクの進捗を細かく管理
  2. Phase 5のテスト実装を優先度付け（クリティカルなテストから実装）
  3. Phase 4-1完了後、すぐにPhase 5-2（UrnProcessorのテスト）を実装し、早期にフィードバックを得る
  4. 工数超過の兆候があれば、Phase 7のドキュメント作成をスコープ縮小

---

## 11. 成功基準

### 定量的指標

1. **Cyclomatic Complexity（循環的複雑度）の削減**
   - リファクタリング前: 推定15〜25（複雑なメソッド）
   - リファクタリング後: 各メソッドで10未満（目標）

2. **ネストレベルの削減**
   - リファクタリング前: 5レベル以上のネストが複数存在
   - リファクタリング後: 最大3レベル以下（目標）

3. **テストカバレッジ**
   - 目標: 90%以上（Statement Coverage）
   - 新規クラスは100%を目指す

4. **パフォーマンス**
   - リファクタリング後の処理時間が、リファクタリング前の±10%以内

### 定性的指標

1. **コードの可読性**
   - コードレビューで「理解しやすい」と評価される
   - 新規開発者がコードを理解するまでの時間が短縮される

2. **保守性**
   - 新機能追加時の変更箇所が明確（単一責任の原則）
   - クラスごとの独立性が高く、影響範囲が限定的

3. **テスタビリティ**
   - 各クラスのユニットテストが容易に作成できる
   - モック・スタブを使用したテストが不要（依存性が低い）

---

## 12. 次のステップ

### Phase 1の開始

1. **外部依存の調査** (Task 1-1)
   - `graph_processor.py`, `main.py`, `report_generator.py`での`dot_processor.py`の使用箇所を特定
   - インポート文とメソッド呼び出しをリストアップ
   - 公開API（変更してはいけないインターフェース）を明確化

2. **現状のコード複雑度の定量的測定** (Task 1-2)
   - Cyclomatic Complexity（循環的複雑度）の測定
   - ネストレベルの詳細確認（5レベル以上の箇所をすべて特定）
   - メソッド数と平均行数の計算
   - 測定結果を`requirements.md`に記録

3. **リファクタリング要件の詳細化** (Task 1-3)
   - 各新規クラス（UrnProcessor、NodeLabelGenerator、ResourceDependencyBuilder）の責務を明確に定義
   - クラス間のインターフェース設計（メソッドシグネチャ、戻り値、例外処理）
   - Extract Classパターンの適用方針を文書化
   - Guard Clauseパターンの適用対象メソッドをリストアップ

### クリティカルシンキングレビューの実施

要件定義書作成後、クリティカルシンキングレビューを実施します。レビューでは以下の品質ゲートが確認されます：

- [ ] **機能要件が明確に記載されている**
- [ ] **受け入れ基準が定義されている**
- [ ] **スコープが明確である**
- [ ] **論理的な矛盾がない**

ブロッカーが指摘された場合は、Phase 2への移行前に修正が必要です。

---

## 付録

### A. 参考ドキュメント

- **プロジェクト全体方針**: [CLAUDE.md](../../CLAUDE.md)
- **アーキテクチャ設計**: [ARCHITECTURE.md](../../ARCHITECTURE.md)
- **開発ガイドライン**: [CONTRIBUTION.md](../../CONTRIBUTION.md)
- **プロジェクト概要**: [README.md](../../README.md)
- **Planning Document**: [planning.md](../../00_planning/output/planning.md)

### B. 用語集

- **Cyclomatic Complexity（循環的複雑度）**: プログラムの制御フローの複雑さを表す指標。値が大きいほど複雑。
- **Extract Class パターン**: 責務の多いクラスから、特定の責務を持つ新しいクラスを抽出するリファクタリング手法。
- **Guard Clause パターン**: メソッドの先頭で事前条件をチェックし、不正な場合は早期リターンすることで、ネストを削減する手法。
- **URN（Uniform Resource Name）**: Pulumiがリソースを識別するために使用する一意の識別子。
- **特性テスト（Characterization Test）**: 既存コードの振る舞いを固定するために作成するテスト。リファクタリング時に有用。
- **依存性注入（Dependency Injection）**: オブジェクトの依存関係を外部から注入することで、疎結合を実現する設計パターン。

### C. リファクタリングパターンの例

#### Extract Class パターン

```python
# Before
class DotFileProcessor:
    def parse_urn(self, urn: str) -> Dict[str, str]:
        # URN解析ロジック
        pass

    def create_readable_label(self, urn_info: Dict) -> str:
        # ラベル生成ロジック
        pass

# After
class UrnProcessor:
    def parse_urn(self, urn: str) -> Dict[str, str]:
        # URN解析ロジック
        pass

class NodeLabelGenerator:
    def create_readable_label(self, urn_info: Dict) -> str:
        # ラベル生成ロジック
        pass

class DotFileProcessor:
    def __init__(self):
        self.urn_processor = UrnProcessor()
        self.label_generator = NodeLabelGenerator()

    def parse_urn(self, urn: str) -> Dict[str, str]:
        return self.urn_processor.parse_urn(urn)

    def create_readable_label(self, urn_info: Dict) -> str:
        return self.label_generator.create_readable_label(urn_info)
```

#### Guard Clause パターン

```python
# Before: 深いネスト
def process(data):
    if data is not None:
        if len(data) > 0:
            if data['type'] == 'valid':
                if data['status'] == 'active':
                    # 実際の処理
                    return process_data(data)
    return None

# After: 早期リターン
def process(data):
    if data is None:
        return None
    if len(data) == 0:
        return None
    if data['type'] != 'valid':
        return None
    if data['status'] != 'active':
        return None

    # 実際の処理（ネストなし）
    return process_data(data)
```

---

## 変更履歴

| 日付 | バージョン | 変更内容 | 担当者 |
|------|-----------|---------|--------|
| 2025-01-14 | v1.0 | 初版作成 | AI Workflow System |

---

**要件定義書の作成完了**

この要件定義書は、Issue #448のリファクタリング作業を詳細に定義したものです。Planning Documentで策定された戦略を踏まえ、機能要件・非機能要件・受け入れ基準を明確化しました。次のステップとして、Phase 2（設計フェーズ）へ移行します。
