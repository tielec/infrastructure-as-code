# テストシナリオ: dot_processor.py - Phase 1: 基盤整備

## Issue情報

- **Issue番号**: #460
- **タイトル**: [Refactor] dot_processor.py - Phase 1: 基盤整備
- **親Issue**: #448
- **状態**: open
- **URL**: https://github.com/tielec/infrastructure-as-code/issues/460
- **作成日**: 2025-01-19

---

## 0. Planning Documentと設計書の確認

### テスト戦略（Phase 2から引用）

**テスト戦略: UNIT_ONLY**

- **理由**: `dot_processor.py`は単一モジュールで、外部依存が限定的
- **カバレッジ目標**: 80%以上
- **テスト種別**: 特性テスト（Characterization Test）+ ユニットテスト

### テスト対象の範囲

**対象ファイル**: `jenkins/jobs/pipeline/infrastructure/pulumi-stack-action/src/dot_processor.py`

**対象クラス**:
1. `DotFileGenerator` - DOTファイル生成の責務
2. `DotFileProcessor` - DOTファイル処理の責務

### テストの目的

1. **既存の振る舞いを記録**: 現在の`dot_processor.py`の振る舞いを正確に記録
2. **リファクタリングの安全網構築**: Phase 2以降のリファクタリング時に振る舞いが維持されていることを検証
3. **カバレッジ80%以上達成**: 主要な振る舞いを保証

---

## 1. テスト戦略サマリー

### 1.1 採用するテスト戦略

**UNIT_ONLY（ユニットテストのみ）**

### 1.2 テスト種別

- **特性テスト（Characterization Test）**: 既存の振る舞いを記録するテスト
- **ユニットテスト**: 各メソッドの入出力を検証するテスト

### 1.3 テスト対象メソッド

#### DotFileGeneratorクラス

**公開メソッド**:
- `escape_dot_string(s: str) -> str` - DOT形式の文字列エスケープ
- `create_dot_file(stack_name, resources, resource_providers) -> List[str]` - DOTファイル生成

**プライベートメソッド（公開メソッド経由でテスト）**:
- `_add_stack_node(stack_name)` - スタックノード生成
- `_add_provider_nodes(resource_providers, dot_lines)` - プロバイダーノード生成
- `_add_stack_to_provider_connections(provider_nodes, dot_lines)` - スタック-プロバイダー接続
- `_add_resources(resources, provider_nodes, dot_lines)` - リソースノード生成
- `_add_resource_dependencies(resources, dot_lines)` - リソース間依存関係

#### DotFileProcessorクラス

**公開メソッド**:
- `is_empty_graph(dot_content: str) -> bool` - 空グラフ判定
- `parse_urn(urn: str) -> Dict[str, str]` - URN解析
- `create_readable_label(urn_info: Dict) -> str` - 読みやすいラベル生成
- `is_stack_resource(urn: str) -> bool` - スタックリソース判定
- `apply_graph_styling(dot_content: str) -> str` - グラフスタイル適用

**プライベートメソッド（公開メソッド経由でテスト）**:
- `_parse_provider_type(provider_type)` - プロバイダータイプ解析
- `_format_resource_type(resource_type)` - リソースタイプのフォーマット
- `_enhance_pulumi_graph(dot_content)` - Pulumiグラフの拡張

---

## 2. Unitテストシナリオ

### 2.1 DotFileGenerator - エスケープ処理のテスト

#### テストケース 2.1.1: escape_dot_string - ダブルクォートのエスケープ

**テストケース名**: `test_escape_dot_string_with_double_quotes`

- **目的**: ダブルクォートが正しくエスケープされることを検証
- **前提条件**: なし
- **入力**: `'test "value" here'`
- **期待結果**: `'test \\"value\\" here'`（ダブルクォートがエスケープされる）
- **テストデータ**:
  ```python
  input_str = 'test "value" here'
  expected = 'test \\"value\\" here'
  ```

#### テストケース 2.1.2: escape_dot_string - バックスラッシュのエスケープ

**テストケース名**: `test_escape_dot_string_with_backslash`

- **目的**: バックスラッシュが正しくエスケープされることを検証
- **前提条件**: なし
- **入力**: `'test\\path'`
- **期待結果**: `'test\\\\path'`（バックスラッシュがエスケープされる）
- **テストデータ**:
  ```python
  input_str = 'test\\path'
  expected = 'test\\\\path'
  ```

#### テストケース 2.1.3: escape_dot_string - 改行のエスケープ

**テストケース名**: `test_escape_dot_string_with_newline`

- **目的**: 改行が`\\n`に変換されることを検証
- **前提条件**: なし
- **入力**: `'line1\nline2'`
- **期待結果**: `'line1\\nline2'`（改行がエスケープされる）
- **テストデータ**:
  ```python
  input_str = 'line1\nline2'
  expected = 'line1\\nline2'
  ```

#### テストケース 2.1.4: escape_dot_string - タブのエスケープ

**テストケース名**: `test_escape_dot_string_with_tab`

- **目的**: タブが`\\t`に変換されることを検証
- **前提条件**: なし
- **入力**: `'col1\tcol2'`
- **期待結果**: `'col1\\tcol2'`（タブがエスケープされる）
- **テストデータ**:
  ```python
  input_str = 'col1\tcol2'
  expected = 'col1\\tcol2'
  ```

#### テストケース 2.1.5: escape_dot_string - キャリッジリターンの除去

**テストケース名**: `test_escape_dot_string_with_carriage_return`

- **目的**: キャリッジリターンが削除されることを検証
- **前提条件**: なし
- **入力**: `'line1\r\nline2'`
- **期待結果**: `'line1\\nline2'`（`\r`が削除され、`\n`がエスケープされる）
- **テストデータ**:
  ```python
  input_str = 'line1\r\nline2'
  expected = 'line1\\nline2'
  ```

#### テストケース 2.1.6: escape_dot_string - 空文字列の処理

**テストケース名**: `test_escape_dot_string_with_empty_string`

- **目的**: 空文字列が正しく処理されることを検証（エラーが発生しない）
- **前提条件**: なし
- **入力**: `''`
- **期待結果**: `''`（空文字列がそのまま返される）
- **テストデータ**:
  ```python
  input_str = ''
  expected = ''
  ```

#### テストケース 2.1.7: escape_dot_string - Noneの処理

**テストケース名**: `test_escape_dot_string_with_none`

- **目的**: None値が正しく処理されることを検証
- **前提条件**: なし
- **入力**: `None`
- **期待結果**: `None`（Noneがそのまま返される）
- **テストデータ**:
  ```python
  input_str = None
  expected = None
  ```

#### テストケース 2.1.8: escape_dot_string - Unicode文字の処理

**テストケース名**: `test_escape_dot_string_with_unicode`

- **目的**: Unicode文字がそのまま出力されることを検証
- **前提条件**: なし
- **入力**: `'テスト🚀データ'`
- **期待結果**: `'テスト🚀データ'`（エスケープされずにそのまま）
- **テストデータ**:
  ```python
  input_str = 'テスト🚀データ'
  expected = 'テスト🚀データ'
  ```

#### テストケース 2.1.9: escape_dot_string - 複合エスケープ

**テストケース名**: `test_escape_dot_string_with_multiple_escapes`

- **目的**: 複数の特殊文字が同時に正しくエスケープされることを検証
- **前提条件**: なし
- **入力**: `'test "value"\nwith\\backslash\tand\ttabs'`
- **期待結果**: `'test \\"value\\"\\nwith\\\\backslash\\tand\\ttabs'`
- **テストデータ**:
  ```python
  input_str = 'test "value"\nwith\\backslash\tand\ttabs'
  expected = 'test \\"value\\"\\nwith\\\\backslash\\tand\\ttabs'
  ```

---

### 2.2 DotFileGenerator - DOTファイル生成のテスト

#### テストケース 2.2.1: create_dot_file - 基本的なDOT生成

**テストケース名**: `test_create_dot_file_basic`

- **目的**: 基本的なDOTファイルが正しく生成されることを検証
- **前提条件**: サンプルリソースとプロバイダー情報が存在する
- **入力**:
  ```python
  stack_name = 'dev'
  resources = [
      {
          'type': 'aws:s3/bucket:Bucket',
          'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket',
          'dependencies': [],
          'parent': None,
          'propertyDependencies': {}
      }
  ]
  resource_providers = {'aws': 1}
  ```
- **期待結果**:
  - `digraph G {`で開始される
  - `Stack`ノードが含まれる
  - `provider_aws`ノードが含まれる
  - リソースノード`resource_0`が含まれる
  - `}`で終了する
- **確認項目**:
  - [ ] DOT形式として有効である
  - [ ] スタックノードが存在する
  - [ ] プロバイダーノードが存在する
  - [ ] リソースノードが存在する
  - [ ] 依存関係のエッジが存在する

#### テストケース 2.2.2: create_dot_file - 空リソースの処理

**テストケース名**: `test_create_dot_file_with_empty_resources`

- **目的**: リソースが空の場合でもDOTファイルが生成されることを検証
- **前提条件**: なし
- **入力**:
  ```python
  stack_name = 'dev'
  resources = []
  resource_providers = {}
  ```
- **期待結果**:
  - `digraph G {`で開始される
  - `Stack`ノードが含まれる
  - プロバイダーノードは含まれない
  - リソースノードは含まれない
  - `}`で終了する

#### テストケース 2.2.3: create_dot_file - 最大20リソースの処理

**テストケース名**: `test_create_dot_file_with_20_resources`

- **目的**: ちょうど20リソースが全て処理されることを検証
- **前提条件**: 20個のリソースを準備
- **入力**:
  ```python
  stack_name = 'dev'
  resources = [リソース20個のリスト]  # resource_0 ~ resource_19
  resource_providers = {'aws': 20}
  ```
- **期待結果**:
  - 20個全てのリソースノードが生成される（`resource_0` ~ `resource_19`）
  - 省略メッセージは表示されない

#### テストケース 2.2.4: create_dot_file - 21リソース以上の制限

**テストケース名**: `test_create_dot_file_with_21_resources`

- **目的**: 21リソース以上の場合、最初の20個のみ処理されることを検証
- **前提条件**: 21個以上のリソースを準備
- **入力**:
  ```python
  stack_name = 'dev'
  resources = [リソース25個のリスト]
  resource_providers = {'aws': 25}
  ```
- **期待結果**:
  - 最初の20個のリソースノードのみ生成される（`resource_0` ~ `resource_19`）
  - 21個目以降は生成されない

#### テストケース 2.2.5: create_dot_file - AWSプロバイダーの色設定

**テストケース名**: `test_create_dot_file_provider_colors_aws`

- **目的**: AWSプロバイダーに正しい色設定が適用されることを検証
- **前提条件**: AWSリソースを準備
- **入力**:
  ```python
  stack_name = 'dev'
  resources = [
      {
          'type': 'aws:s3/bucket:Bucket',
          'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket'
      }
  ]
  resource_providers = {'aws': 1}
  ```
- **期待結果**:
  - プロバイダーノードに`fillcolor="#FFF3E0"`が設定される
  - プロバイダーノードに`color="#EF6C00"`が設定される

#### テストケース 2.2.6: create_dot_file - Azureプロバイダーの色設定

**テストケース名**: `test_create_dot_file_provider_colors_azure`

- **目的**: Azureプロバイダーに正しい色設定が適用されることを検証
- **前提条件**: Azureリソースを準備
- **入力**:
  ```python
  stack_name = 'dev'
  resources = [
      {
          'type': 'azure:storage/storageAccount:StorageAccount',
          'urn': 'urn:pulumi:dev::myproject::azure:storage/storageAccount:StorageAccount::mystorage'
      }
  ]
  resource_providers = {'azure': 1}
  ```
- **期待結果**:
  - プロバイダーノードに`fillcolor="#E3F2FD"`が設定される
  - プロバイダーノードに`color="#0078D4"`が設定される

#### テストケース 2.2.7: create_dot_file - 未定義プロバイダーのデフォルト色

**テストケース名**: `test_create_dot_file_provider_colors_unknown`

- **目的**: 未定義プロバイダーにデフォルト色が適用されることを検証
- **前提条件**: 未定義プロバイダーのリソースを準備
- **入力**:
  ```python
  stack_name = 'dev'
  resources = [
      {
          'type': 'custom:resource:CustomResource',
          'urn': 'urn:pulumi:dev::myproject::custom:resource:CustomResource::my-resource'
      }
  ]
  resource_providers = {'custom': 1}
  ```
- **期待結果**:
  - プロバイダーノードに`fillcolor="#E3F2FD"`（デフォルト）が設定される
  - プロバイダーノードに`color="#1565C0"`（デフォルト）が設定される

#### テストケース 2.2.8: create_dot_file - 複数プロバイダーの処理

**テストケース名**: `test_create_dot_file_multiple_providers`

- **目的**: 複数のプロバイダーが正しく処理されることを検証
- **前提条件**: 複数プロバイダーのリソースを準備
- **入力**:
  ```python
  stack_name = 'dev'
  resources = [
      {
          'type': 'aws:s3/bucket:Bucket',
          'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket'
      },
      {
          'type': 'gcp:storage/bucket:Bucket',
          'urn': 'urn:pulumi:dev::myproject::gcp:storage/bucket:Bucket::my-bucket'
      }
  ]
  resource_providers = {'aws': 1, 'gcp': 1}
  ```
- **期待結果**:
  - `provider_aws`ノードが存在する
  - `provider_gcp`ノードが存在する
  - 各プロバイダーに対応する色設定が適用される

#### テストケース 2.2.9: create_dot_file - リソース依存関係の生成

**テストケース名**: `test_create_dot_file_resource_dependencies`

- **目的**: リソース間の依存関係が正しく生成されることを検証
- **前提条件**: 依存関係を持つリソースを準備
- **入力**:
  ```python
  stack_name = 'dev'
  resources = [
      {
          'type': 'aws:s3/bucket:Bucket',
          'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket',
          'dependencies': []
      },
      {
          'type': 'aws:s3/bucketObject:BucketObject',
          'urn': 'urn:pulumi:dev::myproject::aws:s3/bucketObject:BucketObject::my-object',
          'dependencies': ['urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket']
      }
  ]
  resource_providers = {'aws': 2}
  ```
- **期待結果**:
  - 依存関係のエッジが生成される（`resource_1` -> `resource_0`）
  - エッジに`style=solid, color="#9C27B0"`が設定される

#### テストケース 2.2.10: create_dot_file - 親リソースへの依存

**テストケース名**: `test_create_dot_file_parent_dependency`

- **目的**: 親リソースへの依存関係が正しく生成されることを検証
- **前提条件**: 親子関係を持つリソースを準備
- **入力**:
  ```python
  stack_name = 'dev'
  resources = [
      {
          'type': 'aws:s3/bucket:Bucket',
          'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket',
          'parent': None
      },
      {
          'type': 'aws:s3/bucketObject:BucketObject',
          'urn': 'urn:pulumi:dev::myproject::aws:s3/bucketObject:BucketObject::my-object',
          'parent': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket'
      }
  ]
  resource_providers = {'aws': 2}
  ```
- **期待結果**:
  - 親依存のエッジが生成される（`resource_1` -> `resource_0`）
  - エッジに`style=dashed, color="#2196F3", label="parent"`が設定される

#### テストケース 2.2.11: create_dot_file - プロパティ依存の生成

**テストケース名**: `test_create_dot_file_property_dependencies`

- **目的**: プロパティ依存が正しく生成されることを検証
- **前提条件**: プロパティ依存を持つリソースを準備
- **入力**:
  ```python
  stack_name = 'dev'
  resources = [
      {
          'type': 'aws:s3/bucket:Bucket',
          'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket',
          'propertyDependencies': {}
      },
      {
          'type': 'aws:s3/bucketObject:BucketObject',
          'urn': 'urn:pulumi:dev::myproject::aws:s3/bucketObject:BucketObject::my-object',
          'propertyDependencies': {
              'bucket': ['urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket']
          }
      }
  ]
  resource_providers = {'aws': 2}
  ```
- **期待結果**:
  - プロパティ依存のエッジが生成される（`resource_1` -> `resource_0`）
  - エッジに`style=dotted, color="#FF5722", label="bucket"`が設定される

#### テストケース 2.2.12: create_dot_file - 長いリソース名の省略

**テストケース名**: `test_create_dot_file_long_resource_name`

- **目的**: 長いリソース名が省略されることを検証
- **前提条件**: 長いリソース名を持つリソースを準備
- **入力**:
  ```python
  stack_name = 'dev'
  resources = [
      {
          'type': 'aws:s3/bucket:Bucket',
          'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::' + 'a' * 50
      }
  ]
  resource_providers = {'aws': 1}
  ```
- **期待結果**:
  - リソース名が30文字 + `...`で省略される

---

### 2.3 DotFileProcessor - URN解析のテスト

#### テストケース 2.3.1: parse_urn - 正常なAWS URNの解析

**テストケース名**: `test_parse_urn_valid_aws`

- **目的**: 正常なAWS URNが正しく解析されることを検証
- **前提条件**: なし
- **入力**: `'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket'`
- **期待結果**:
  ```python
  {
      'stack': 'dev',
      'project': 'myproject',
      'provider': 'aws',
      'module': 's3',
      'type': 'Bucket',
      'name': 'my-bucket',
      'full_urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket'
  }
  ```

#### テストケース 2.3.2: parse_urn - 正常なAzure URNの解析

**テストケース名**: `test_parse_urn_valid_azure`

- **目的**: 正常なAzure URNが正しく解析されることを検証
- **前提条件**: なし
- **入力**: `'urn:pulumi:dev::myproject::azure:storage/storageAccount:StorageAccount::mystorage'`
- **期待結果**:
  ```python
  {
      'stack': 'dev',
      'project': 'myproject',
      'provider': 'azure',
      'module': 'storage',
      'type': 'StorageAccount',
      'name': 'mystorage',
      'full_urn': 'urn:pulumi:dev::myproject::azure:storage/storageAccount:StorageAccount::mystorage'
  }
  ```

#### テストケース 2.3.3: parse_urn - 正常なGCP URNの解析

**テストケース名**: `test_parse_urn_valid_gcp`

- **目的**: 正常なGCP URNが正しく解析されることを検証
- **前提条件**: なし
- **入力**: `'urn:pulumi:dev::myproject::gcp:storage/bucket:Bucket::my-bucket'`
- **期待結果**:
  ```python
  {
      'stack': 'dev',
      'project': 'myproject',
      'provider': 'gcp',
      'module': 'storage',
      'type': 'Bucket',
      'name': 'my-bucket',
      'full_urn': 'urn:pulumi:dev::myproject::gcp:storage/bucket:Bucket::my-bucket'
  }
  ```

#### テストケース 2.3.4: parse_urn - 正常なKubernetes URNの解析

**テストケース名**: `test_parse_urn_valid_kubernetes`

- **目的**: 正常なKubernetes URNが正しく解析されることを検証
- **前提条件**: なし
- **入力**: `'urn:pulumi:dev::myproject::kubernetes:core/v1:Namespace::my-namespace'`
- **期待結果**:
  ```python
  {
      'stack': 'dev',
      'project': 'myproject',
      'provider': 'kubernetes',
      'module': 'core',
      'type': 'Namespace',
      'name': 'my-namespace',
      'full_urn': 'urn:pulumi:dev::myproject::kubernetes:core/v1:Namespace::my-namespace'
  }
  ```

#### テストケース 2.3.5: parse_urn - スタックリソースURNの解析

**テストケース名**: `test_parse_urn_stack_resource`

- **目的**: スタックリソースURNが正しく解析されることを検証
- **前提条件**: なし
- **入力**: `'urn:pulumi:dev::myproject::pulumi:pulumi:Stack::dev'`
- **期待結果**:
  ```python
  {
      'stack': 'dev',
      'project': 'myproject',
      'provider': 'pulumi',
      'module': '',
      'type': 'Stack',
      'name': 'dev',
      'full_urn': 'urn:pulumi:dev::myproject::pulumi:pulumi:Stack::dev'
  }
  ```

#### テストケース 2.3.6: parse_urn - 不正なURN形式（区切り不足）

**テストケース名**: `test_parse_urn_invalid_format`

- **目的**: 不正なURN形式でもエラーが発生せず、デフォルト値が返されることを検証
- **前提条件**: なし
- **入力**: `'invalid-urn'`
- **期待結果**:
  ```python
  {
      'stack': '',
      'project': '',
      'provider': 'unknown',
      'module': '',
      'type': 'unknown',
      'name': 'invalid-urn',
      'full_urn': 'invalid-urn'
  }
  ```

#### テストケース 2.3.7: parse_urn - 部分的なURN

**テストケース名**: `test_parse_urn_partial_urn`

- **目的**: 部分的なURNでもエラーが発生しないことを検証
- **前提条件**: なし
- **入力**: `'urn:pulumi:dev'`
- **期待結果**:
  ```python
  {
      'stack': '',
      'project': '',
      'provider': 'unknown',
      'module': '',
      'type': 'unknown',
      'name': 'urn:pulumi:dev',
      'full_urn': 'urn:pulumi:dev'
  }
  ```

#### テストケース 2.3.8: parse_urn - 空文字列

**テストケース名**: `test_parse_urn_empty_string`

- **目的**: 空文字列でもエラーが発生しないことを検証
- **前提条件**: なし
- **入力**: `''`
- **期待結果**:
  ```python
  {
      'stack': '',
      'project': '',
      'provider': 'unknown',
      'module': '',
      'type': 'unknown',
      'name': '',
      'full_urn': ''
  }
  ```

#### テストケース 2.3.9: parse_urn - プロバイダー情報なしURN

**テストケース名**: `test_parse_urn_no_provider`

- **目的**: プロバイダー情報がないURNでもデフォルト値が返されることを検証
- **前提条件**: なし
- **入力**: `'urn:pulumi:dev::myproject::::my-resource'`
- **期待結果**:
  ```python
  {
      'stack': 'dev',
      'project': 'myproject',
      'provider': 'unknown',
      'module': '',
      'type': 'unknown',
      'name': 'my-resource',
      'full_urn': 'urn:pulumi:dev::myproject::::my-resource'
  }
  ```

#### テストケース 2.3.10: parse_urn - 極端に長いURN

**テストケース名**: `test_parse_urn_extremely_long`

- **目的**: 極端に長いURNでもパースできることを検証
- **前提条件**: なし
- **入力**: `'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::' + 'a' * 1000`
- **期待結果**:
  - パース処理が正常に完了する
  - `name`に1000文字の文字列が含まれる

---

### 2.4 DotFileProcessor - グラフスタイル適用のテスト

#### テストケース 2.4.1: apply_graph_styling - Pulumi生成グラフの処理

**テストケース名**: `test_apply_graph_styling_pulumi_generated`

- **目的**: Pulumi生成グラフ（`strict digraph`）が正しく拡張されることを検証
- **前提条件**: Pulumi生成のDOT文字列を準備
- **入力**:
  ```
  strict digraph {
    "node1" [label="urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket"];
    "node2" [label="urn:pulumi:dev::myproject::aws:s3/bucketObject:BucketObject::my-object"];
    "node2" -> "node1";
  }
  ```
- **期待結果**:
  - グラフ属性が追加される（`graph [rankdir=TB, ...]`）
  - ノード属性が追加される（`node [...]`）
  - エッジ属性が追加される（`edge [...]`）
  - ノードラベルが読みやすい形式に変換される

#### テストケース 2.4.2: apply_graph_styling - 自前生成グラフの処理

**テストケース名**: `test_apply_graph_styling_custom_generated`

- **目的**: 自前生成グラフ（`digraph G {`）が正しく処理されることを検証
- **前提条件**: 自前生成のDOT文字列を準備
- **入力**:
  ```
  digraph G {
    "node1" [label="Resource1"];
    "node2" [label="Resource2"];
    "node1" -> "node2";
  }
  ```
- **期待結果**:
  - `digraph G {`が`DotFileProcessor.STYLE_SETTINGS`に置換される
  - ノードラベルが処理される

#### テストケース 2.4.3: apply_graph_styling - 空グラフの処理

**テストケース名**: `test_apply_graph_styling_empty_graph`

- **目的**: 空グラフが正しく処理されることを検証
- **前提条件**: 空グラフを準備
- **入力**: `'digraph G {}'`
- **期待結果**:
  - 元のDOT文字列がそのまま返される（または最小限の変更）

#### テストケース 2.4.4: apply_graph_styling - スタックノードの色設定

**テストケース名**: `test_apply_graph_styling_stack_node`

- **目的**: スタックノードに正しい色設定が適用されることを検証
- **前提条件**: スタックノードを含むPulumiグラフを準備
- **入力**:
  ```
  strict digraph {
    "stack_node" [label="urn:pulumi:dev::myproject::pulumi:pulumi:Stack::dev"];
  }
  ```
- **期待結果**:
  - スタックノードに`fillcolor="#D1C4E9"`が設定される
  - スタックノードに`color="#512DA8"`が設定される
  - ラベルが`Stack\ndev`に変換される

---

### 2.5 DotFileProcessor - グラフ検証のテスト

#### テストケース 2.5.1: is_empty_graph - 空グラフの判定

**テストケース名**: `test_is_empty_graph_empty`

- **目的**: 空グラフが正しく判定されることを検証
- **前提条件**: なし
- **入力**: `'digraph G {}'`
- **期待結果**: `True`

#### テストケース 2.5.2: is_empty_graph - 最小グラフ（30文字未満）の判定

**テストケース名**: `test_is_empty_graph_minimal`

- **目的**: 30文字未満のグラフが空と判定されることを検証
- **前提条件**: なし
- **入力**: `'digraph G { a; }'`（17文字）
- **期待結果**: `True`

#### テストケース 2.5.3: is_empty_graph - 非空グラフの判定

**テストケース名**: `test_is_empty_graph_non_empty`

- **目的**: 十分な内容を持つグラフが空でないと判定されることを検証
- **前提条件**: なし
- **入力**:
  ```
  digraph G {
    "node1" [label="Resource1"];
    "node2" [label="Resource2"];
    "node1" -> "node2";
  }
  ```
- **期待結果**: `False`

#### テストケース 2.5.4: is_empty_graph - ちょうど30文字のグラフ

**テストケース名**: `test_is_empty_graph_boundary_30`

- **目的**: 境界値（30文字）のグラフが正しく判定されることを検証
- **前提条件**: なし
- **入力**: ちょうど30文字のグラフ文字列
- **期待結果**: `False`（30文字以上なので空でない）

---

### 2.6 DotFileProcessor - ラベル生成のテスト

#### テストケース 2.6.1: create_readable_label - 基本的なラベル生成

**テストケース名**: `test_create_readable_label_basic`

- **目的**: 基本的なラベルが正しく生成されることを検証
- **前提条件**: なし
- **入力**:
  ```python
  urn_info = {
      'provider': 'aws',
      'module': 's3',
      'type': 'Bucket',
      'name': 'my-bucket'
  }
  ```
- **期待結果**: `'s3\\nBucket\\nmy-bucket'`（改行区切り）

#### テストケース 2.6.2: create_readable_label - モジュール名なしの場合

**テストケース名**: `test_create_readable_label_no_module`

- **目的**: モジュール名がない場合のラベル生成を検証
- **前提条件**: なし
- **入力**:
  ```python
  urn_info = {
      'provider': 'pulumi',
      'module': '',
      'type': 'Stack',
      'name': 'dev'
  }
  ```
- **期待結果**: `'Stack\\ndev'`（モジュール名が省略される）

#### テストケース 2.6.3: create_readable_label - 長いタイプ名の省略

**テストケース名**: `test_create_readable_label_long_type`

- **目的**: 長いタイプ名が省略されることを検証
- **前提条件**: なし
- **入力**:
  ```python
  urn_info = {
      'provider': 'aws',
      'module': 'ec2',
      'type': 'VeryLongResourceTypeNameThatExceeds30Characters',
      'name': 'my-resource'
  }
  ```
- **期待結果**: タイプ名が30文字以内に省略される

#### テストケース 2.6.4: create_readable_label - キャメルケースの処理

**テストケース名**: `test_create_readable_label_camelcase`

- **目的**: キャメルケースのタイプ名が正しく処理されることを検証
- **前提条件**: なし
- **入力**:
  ```python
  urn_info = {
      'provider': 'aws',
      'module': 'ec2',
      'type': 'SecurityGroup',
      'name': 'my-sg'
  }
  ```
- **期待結果**: `'ec2\\nSecurityGroup\\nmy-sg'`

---

### 2.7 DotFileProcessor - リソース識別のテスト

#### テストケース 2.7.1: is_stack_resource - スタックリソースの判定

**テストケース名**: `test_is_stack_resource_true`

- **目的**: スタックリソースURNが正しく判定されることを検証
- **前提条件**: なし
- **入力**: `'urn:pulumi:dev::myproject::pulumi:pulumi:Stack::dev'`
- **期待結果**: `True`

#### テストケース 2.7.2: is_stack_resource - 通常リソースの判定

**テストケース名**: `test_is_stack_resource_false`

- **目的**: 通常リソースURNがスタックでないと判定されることを検証
- **前提条件**: なし
- **入力**: `'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket'`
- **期待結果**: `False`

#### テストケース 2.7.3: is_stack_resource - 不正なURN

**テストケース名**: `test_is_stack_resource_invalid_urn`

- **目的**: 不正なURNでも正しく判定されることを検証
- **前提条件**: なし
- **入力**: `'invalid-urn'`
- **期待結果**: `False`

---

### 2.8 エッジケースのテスト

#### テストケース 2.8.1: 極端に長いリソース名

**テストケース名**: `test_extreme_long_resource_name`

- **目的**: 極端に長いリソース名でも処理できることを検証
- **前提条件**: なし
- **入力**:
  ```python
  stack_name = 'dev'
  resources = [
      {
          'type': 'aws:s3/bucket:Bucket',
          'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::' + 'a' * 1000
      }
  ]
  resource_providers = {'aws': 1}
  ```
- **期待結果**:
  - エラーが発生しない
  - リソース名が適切に省略される

#### テストケース 2.8.2: 特殊文字を含むリソース名

**テストケース名**: `test_special_characters_in_resource_name`

- **目的**: 特殊文字を含むリソース名が正しくエスケープされることを検証
- **前提条件**: なし
- **入力**:
  ```python
  stack_name = 'dev'
  resources = [
      {
          'type': 'aws:s3/bucket:Bucket',
          'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-"special"-bucket'
      }
  ]
  resource_providers = {'aws': 1}
  ```
- **期待結果**:
  - ダブルクォートが正しくエスケープされる
  - DOT形式として有効

#### テストケース 2.8.3: プロバイダー名の大文字小文字

**テストケース名**: `test_provider_name_case_sensitivity`

- **目的**: プロバイダー名の大文字小文字が正しく処理されることを検証
- **前提条件**: なし
- **入力**:
  ```python
  stack_name = 'dev'
  resources = [
      {
          'type': 'AWS:s3/bucket:Bucket',  # 大文字のAWS
          'urn': 'urn:pulumi:dev::myproject::AWS:s3/bucket:Bucket::my-bucket'
      }
  ]
  resource_providers = {'AWS': 1}
  ```
- **期待結果**:
  - プロバイダー名が小文字に変換される（`PROVIDER_COLORS`は小文字キー）
  - 正しい色設定が適用される

#### テストケース 2.8.4: 循環依存の処理

**テストケース名**: `test_circular_dependencies`

- **目的**: 循環依存でもエラーが発生しないことを検証
- **前提条件**: なし
- **入力**:
  ```python
  stack_name = 'dev'
  resources = [
      {
          'type': 'aws:s3/bucket:Bucket',
          'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-a',
          'dependencies': ['urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-b']
      },
      {
          'type': 'aws:s3/bucket:Bucket',
          'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-b',
          'dependencies': ['urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-a']
      }
  ]
  resource_providers = {'aws': 2}
  ```
- **期待結果**:
  - エラーが発生しない
  - 両方の依存関係エッジが生成される

#### テストケース 2.8.5: 空のプロバイダー辞書

**テストケース名**: `test_empty_provider_dict`

- **目的**: プロバイダー辞書が空の場合でもエラーが発生しないことを検証
- **前提条件**: なし
- **入力**:
  ```python
  stack_name = 'dev'
  resources = []
  resource_providers = {}
  ```
- **期待結果**:
  - エラーが発生しない
  - スタックノードのみのDOTファイルが生成される

---

## 3. テストデータ

### 3.1 サンプルURNデータ（`fixtures/test_data/sample_urns.json`）

```json
{
  "valid_aws_urn": "urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket",
  "valid_azure_urn": "urn:pulumi:dev::myproject::azure:storage/storageAccount:StorageAccount::mystorage",
  "valid_gcp_urn": "urn:pulumi:dev::myproject::gcp:storage/bucket:Bucket::my-bucket",
  "valid_kubernetes_urn": "urn:pulumi:dev::myproject::kubernetes:core/v1:Namespace::my-namespace",
  "stack_urn": "urn:pulumi:dev::myproject::pulumi:pulumi:Stack::dev",
  "invalid_urn_no_separator": "invalid-urn",
  "invalid_urn_partial": "urn:pulumi:dev",
  "empty_urn": "",
  "long_urn": "urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
}
```

### 3.2 サンプルリソースデータ（`fixtures/test_data/sample_resources.json`）

```json
{
  "basic_resource": {
    "type": "aws:s3/bucket:Bucket",
    "urn": "urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket",
    "dependencies": [],
    "parent": null,
    "propertyDependencies": {}
  },
  "resource_with_dependencies": {
    "type": "aws:s3/bucketObject:BucketObject",
    "urn": "urn:pulumi:dev::myproject::aws:s3/bucketObject:BucketObject::my-object",
    "dependencies": ["urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket"],
    "parent": null,
    "propertyDependencies": {
      "bucket": ["urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket"]
    }
  },
  "minimal_resource": {
    "type": "aws:s3/bucket:Bucket",
    "urn": "urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::minimal"
  },
  "azure_resource": {
    "type": "azure:storage/storageAccount:StorageAccount",
    "urn": "urn:pulumi:dev::myproject::azure:storage/storageAccount:StorageAccount::mystorage",
    "dependencies": [],
    "parent": null,
    "propertyDependencies": {}
  },
  "gcp_resource": {
    "type": "gcp:storage/bucket:Bucket",
    "urn": "urn:pulumi:dev::myproject::gcp:storage/bucket:Bucket::my-bucket",
    "dependencies": [],
    "parent": null,
    "propertyDependencies": {}
  }
}
```

### 3.3 サンプルDOT文字列（`fixtures/test_data/sample_dot_strings.json`）

```json
{
  "pulumi_generated_graph": "strict digraph {\n  \"node1\" [label=\"urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket\"];\n  \"node2\" [label=\"urn:pulumi:dev::myproject::aws:s3/bucketObject:BucketObject::my-object\"];\n  \"node2\" -> \"node1\";\n}",
  "custom_generated_graph": "digraph G {\n  \"node1\" [label=\"Resource1\"];\n  \"node2\" [label=\"Resource2\"];\n  \"node1\" -> \"node2\";\n}",
  "empty_graph": "digraph G {}",
  "minimal_graph": "digraph G { a; }",
  "stack_graph": "strict digraph {\n  \"stack_node\" [label=\"urn:pulumi:dev::myproject::pulumi:pulumi:Stack::dev\"];\n  \"resource_node\" [label=\"urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket\"];\n  \"resource_node\" -> \"stack_node\";\n}"
}
```

### 3.4 20リソースのサンプルデータ生成

テストコード内で動的に生成：

```python
def generate_resources_list(count: int) -> List[Dict]:
    """指定した数のリソースリストを生成"""
    resources = []
    for i in range(count):
        resources.append({
            'type': 'aws:s3/bucket:Bucket',
            'urn': f'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-{i}',
            'dependencies': [],
            'parent': None,
            'propertyDependencies': {}
        })
    return resources
```

---

## 4. テスト環境要件

### 4.1 必要な環境

- **Python**: 3.8以上
- **pytest**: 7.4.3
- **pytest-cov**: 4.1.0
- **pytest-mock**: 3.12.0（オプション）

### 4.2 ディレクトリ構造

```
jenkins/jobs/pipeline/infrastructure/pulumi-stack-action/
├── src/
│   └── dot_processor.py                      # テスト対象
└── tests/                                     # 新規作成
    ├── __init__.py
    ├── conftest.py                            # 共通フィクスチャ
    ├── test_dot_processor.py                  # メインテストコード
    ├── fixtures/
    │   ├── __init__.py
    │   └── test_data/
    │       ├── sample_urns.json
    │       ├── sample_resources.json
    │       └── sample_dot_strings.json
    └── README.md
```

### 4.3 依存関係のインストール

```bash
pip3 install pytest==7.4.3 pytest-cov==4.1.0 pytest-mock==3.12.0
```

### 4.4 テスト実行コマンド

```bash
# すべてのテストを実行
pytest tests/

# カバレッジ測定付き
pytest --cov=src --cov-report=html --cov-report=term tests/

# 特定のテストクラスのみ実行
pytest tests/test_dot_processor.py::TestDotFileGeneratorEscaping

# 並列実行（高速化）
pytest -n auto tests/
```

---

## 5. テストの優先順位

カバレッジ80%以上を達成するため、以下の優先順位でテストを作成します：

### 優先度: 高（必須）

1. **DotFileGenerator.escape_dot_string**: 特殊文字エスケープは基本機能
2. **DotFileGenerator.create_dot_file**: DOT生成のコア機能
3. **DotFileProcessor.parse_urn**: URN解析はPulumiグラフ処理の基盤
4. **DotFileProcessor.is_empty_graph**: グラフ検証の基本
5. **DotFileProcessor.apply_graph_styling**: Pulumiグラフ拡張のコア機能

### 優先度: 中（重要）

6. **DotFileProcessor.create_readable_label**: ラベル生成
7. **DotFileProcessor.is_stack_resource**: スタックリソース判定
8. プロバイダー色設定のテスト
9. リソース依存関係生成のテスト

### 優先度: 低（補完的）

10. エッジケース（極端に長い入力、特殊文字、循環依存等）
11. プライベートメソッドの詳細テスト

---

## 6. 品質ゲート（Phase 3）

### 品質ゲート確認

- [x] **Phase 2の戦略に沿ったテストシナリオである**: UNIT_ONLY戦略に基づき、ユニットテストと特性テストのシナリオを作成
- [x] **主要な正常系がカバーされている**:
  - DotFileGenerator: `escape_dot_string`, `create_dot_file`の正常系をカバー
  - DotFileProcessor: `parse_urn`, `apply_graph_styling`, `is_empty_graph`, `create_readable_label`, `is_stack_resource`の正常系をカバー
- [x] **主要な異常系がカバーされている**:
  - 空文字列、None値、不正なURN、極端に長い入力、特殊文字等の異常系をカバー
- [x] **期待結果が明確である**: 全テストケースに具体的な入力・期待結果を記載

---

## 7. 実装時の注意事項

### 7.1 特性テストの原則

- **既存の振る舞いを記録する**: 現在のコードがどのように動作するかを記録し、将来のリファクタリング時に比較できるようにする
- **正解を決めつけない**: 既存コードの出力が「正解」である。もし期待と異なる動作があっても、まずは記録する
- **Golden Masterパターン**: 初回実行時の出力を「Golden Master」として保存し、以降のテストで比較

### 7.2 テストの独立性

- **テストケース間で状態を共有しない**: 各テストは独立して実行可能
- **フィクスチャのクリーンアップ**: テスト後に適切にクリーンアップ
- **並列実行可能**: `pytest -n auto`で並列実行できるように設計

### 7.3 カバレッジ目標の達成

- **公開メソッド**: 100%カバレッジ
- **プライベートメソッド**: 公開メソッド経由でテスト（70%以上）
- **エッジケース処理**: 100%カバレッジ

### 7.4 テストコードの品質

- **PEP 8準拠**: コーディング規約を遵守
- **ドキュメント文字列**: 各テストケースにdocstringを記載
- **Given-When-Then形式**: テストの意図を明確にするためコメントを使用

---

## 8. 次フェーズへの引き継ぎ

### Phase 5（テストコード実装）への準備

本テストシナリオをもとに、Phase 5では以下を実装します：

1. **テスト環境のセットアップ**:
   - `tests/`ディレクトリの作成
   - `conftest.py`の実装
   - `pytest.ini`、`.coveragerc`の作成

2. **テストデータの準備**:
   - `fixtures/test_data/sample_urns.json`
   - `fixtures/test_data/sample_resources.json`
   - `fixtures/test_data/sample_dot_strings.json`

3. **テストコードの実装**:
   - `test_dot_processor.py`に本シナリオのテストケースを実装
   - 各テストケースに対して、Given-When-Then形式で実装

4. **カバレッジ測定**:
   - テスト実行後、カバレッジレポートを生成
   - 80%以上の達成を確認

---

**作成日**: 2025-01-19
**最終更新**: 2025-01-19
**作成者**: Claude Code (AI Workflow Phase 3)
**レビュー状態**: 未レビュー
**次フェーズ**: Phase 5（テストコード実装）
