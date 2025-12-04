# テストシナリオ: Issue #463

## Issue情報

- **Issue番号**: #463
- **タイトル**: [Refactor] dot_processor.py - Phase 2-3: ResourceDependencyBuilderクラスの抽出
- **URL**: https://github.com/tielec/infrastructure-as-code/issues/463
- **親Issue**: #448
- **依存Issue**: #460 (Phase 1: 基盤整備), #461 (Phase 2-1: UrnProcessor)

---

## 0. Planning Documentの確認

Planning Phaseで策定された以下のテスト戦略を確認しました：

### テスト戦略
- **戦略**: UNIT_INTEGRATION
- **UNIT（必須）**: ResourceDependencyBuilderクラス単独での動作を検証（カバレッジ80%以上）
- **INTEGRATION（必須）**: DotFileProcessorとの統合を検証（既存テストが全てパス）

### テストコード戦略
- **戦略**: BOTH_TEST
- **CREATE_TEST**: `test_resource_dependency_builder.py` を新規作成
- **EXTEND_TEST**: 既存の `test_dot_processor.py` を更新（既存テストの動作確認）

---

## 1. テスト戦略サマリー

### 選択されたテスト戦略
**UNIT_INTEGRATION**

### テスト対象の範囲
1. **UNIT（単体テスト）**: ResourceDependencyBuilderクラス
   - URNマッピング作成
   - 直接依存関係追加
   - 親依存関係追加
   - プロパティ依存関係追加
   - 複合シナリオ（複数の依存関係タイプが混在）

2. **INTEGRATION（統合テスト）**: DotFileGeneratorとの統合
   - 既存の`test_dot_processor.py`の全テストがパス
   - DotFileGenerator経由でResourceDependencyBuilderが正しく呼び出される
   - end-to-endでDOTファイル生成が正常に動作

### テストの目的
1. **リファクタリングの正確性保証**: 既存機能を完全に維持
2. **単体動作の検証**: ResourceDependencyBuilderが独立して動作
3. **カバレッジ達成**: 80%以上のカバレッジ
4. **リグレッション防止**: 既存テストが全てパス

---

## 2. Unitテストシナリオ

### 2.1 URNマッピング作成テスト（TestURNMapping）

#### テストケース 2.1.1: create_urn_to_node_mapping_正常系_3リソース

- **目的**: 3個のリソースからURNマッピングが正しく作成されることを検証
- **前提条件**: 有効なURNを持つ3個のリソースリストが存在する
- **入力**:
  ```python
  resources = [
      {'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-a', ...},
      {'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-b', ...},
      {'urn': 'urn:pulumi:dev::myproject::aws:ec2/vpc:Vpc::my-vpc', ...}
  ]
  ```
- **期待結果**:
  - 3エントリのマッピング辞書が返される
  - キー: URN文字列（完全なPulumi URN）
  - 値: `resource_0`, `resource_1`, `resource_2`
  - 辞書サイズ: 3
- **テストデータ**: 上記リソースリスト

#### テストケース 2.1.2: create_urn_to_node_mapping_空リスト

- **目的**: 空リストを渡した場合に空の辞書が返されることを検証
- **前提条件**: 空のリソースリスト
- **入力**: `resources = []`
- **期待結果**: 空の辞書 `{}` が返される
- **テストデータ**: 空リスト

#### テストケース 2.1.3: create_urn_to_node_mapping_1リソース

- **目的**: 1個のリソースで1エントリのマッピングが作成されることを検証
- **前提条件**: 有効なURNを持つ1個のリソースリスト
- **入力**: `resources = [{'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket'}]`
- **期待結果**:
  - 1エントリのマッピング辞書
  - 値: `resource_0`
- **テストデータ**: 1個のリソースリスト

#### テストケース 2.1.4: create_urn_to_node_mapping_重複URN

- **目的**: 重複URNが含まれる場合、最後のリソースのノードIDが使用されることを検証
- **前提条件**: 同じURNを持つ2個のリソースリスト
- **入力**:
  ```python
  resources = [
      {'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket'},
      {'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket'}
  ]
  ```
- **期待結果**:
  - マッピング辞書のエントリ数: 1
  - 値: `resource_1`（最後のインデックス）
- **テストデータ**: 重複URNを持つリソースリスト

#### テストケース 2.1.5: create_urn_to_node_mapping_urnキーなし

- **目的**: 'urn'キーが存在しないリソースを安全に処理できることを検証
- **前提条件**: 'urn'キーを持たないリソースを含むリスト
- **入力**:
  ```python
  resources = [
      {'type': 'aws:s3/bucket:Bucket'},  # urnキーなし
      {'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-b'}
  ]
  ```
- **期待結果**:
  - 2エントリのマッピング辞書
  - 1つ目のキー: `''`（空文字列）
  - 2つ目のキー: `'urn:pulumi:...'`
  - エラーが発生しない
- **テストデータ**: urnキーなしのリソースを含むリスト

#### テストケース 2.1.6: create_urn_to_node_mapping_最大20リソース

- **目的**: 最大20リソースのマッピングが正しく作成されることを検証
- **前提条件**: ちょうど20個のリソースリスト
- **入力**: 20個のリソース（`bucket-0`から`bucket-19`まで）
- **期待結果**:
  - 20エントリのマッピング辞書
  - 値: `resource_0`から`resource_19`まで
- **テストデータ**: 20個のリソースリスト

---

### 2.2 直接依存関係追加テスト（TestDirectDependencies）

#### テストケース 2.2.1: add_direct_dependencies_正常系_1依存

- **目的**: 1個の直接依存関係が正しく追加されることを検証
- **前提条件**: 1個の依存URNを持つリソースとURNマッピングが存在する
- **入力**:
  ```python
  node_id = 'resource_1'
  resource = {
      'dependencies': ['urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-a']
  }
  urn_to_node_id = {
      'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-a': 'resource_0'
  }
  dot_lines = []
  ```
- **期待結果**:
  - `dot_lines`に1行追加される
  - 追加された行: `'    "resource_1" -> "resource_0" [style=solid, color="#9C27B0", fontsize="10"];'`
  - スタイル: `solid`
  - 色: `#9C27B0`（紫色）
- **テストデータ**: 上記入力データ

#### テストケース 2.2.2: add_direct_dependencies_複数依存_3個

- **目的**: 複数（3個）の直接依存関係が正しく追加されることを検証
- **前提条件**: 3個の依存URNを持つリソース
- **入力**:
  ```python
  node_id = 'resource_3'
  resource = {
      'dependencies': [
          'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-a',
          'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-b',
          'urn:pulumi:dev::myproject::aws:ec2/vpc:Vpc::my-vpc'
      ]
  }
  urn_to_node_id = {
      'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-a': 'resource_0',
      'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-b': 'resource_1',
      'urn:pulumi:dev::myproject::aws:ec2/vpc:Vpc::my-vpc': 'resource_2'
  }
  dot_lines = []
  ```
- **期待結果**:
  - `dot_lines`に3行追加される
  - すべて`resource_3`から各ノードへのエッジ
  - すべて`style=solid`
- **テストデータ**: 上記入力データ

#### テストケース 2.2.3: add_direct_dependencies_空依存リスト

- **目的**: 空の依存リストの場合、何も追加されないことを検証
- **前提条件**: 空の依存リストを持つリソース
- **入力**:
  ```python
  node_id = 'resource_1'
  resource = {'dependencies': []}
  urn_to_node_id = {}
  dot_lines = []
  ```
- **期待結果**:
  - `dot_lines`に何も追加されない（空のまま）
  - エラーが発生しない
- **テストデータ**: 空依存リストを持つリソース

#### テストケース 2.2.4: add_direct_dependencies_存在しないURN

- **目的**: URNマッピングに存在しないURNへの依存が安全にスキップされることを検証
- **前提条件**: 存在しないURNへの依存を持つリソース
- **入力**:
  ```python
  node_id = 'resource_1'
  resource = {
      'dependencies': [
          'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-a',  # 存在する
          'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::nonexistent'  # 存在しない
      ]
  }
  urn_to_node_id = {
      'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-a': 'resource_0'
  }
  dot_lines = []
  ```
- **期待結果**:
  - `dot_lines`に1行のみ追加される（存在するURNのみ）
  - 存在しないURNはスキップされる
  - エラーが発生しない
- **テストデータ**: 存在しないURNを含む依存リスト

#### テストケース 2.2.5: add_direct_dependencies_dependenciesキーなし

- **目的**: 'dependencies'キーが存在しないリソースを安全に処理できることを検証
- **前提条件**: 'dependencies'キーを持たないリソース
- **入力**:
  ```python
  node_id = 'resource_1'
  resource = {'type': 'aws:s3/bucket:Bucket'}  # dependenciesキーなし
  urn_to_node_id = {}
  dot_lines = []
  ```
- **期待結果**:
  - `dot_lines`に何も追加されない
  - エラーが発生しない
- **テストデータ**: dependenciesキーなしのリソース

---

### 2.3 親依存関係追加テスト（TestParentDependencies）

#### テストケース 2.3.1: add_parent_dependency_正常系

- **目的**: 親依存関係が正しく追加されることを検証
- **前提条件**: 有効な親URNを持つリソースとURNマッピングが存在する
- **入力**:
  ```python
  node_id = 'resource_1'
  resource = {
      'parent': 'urn:pulumi:dev::myproject::aws:ec2/vpc:Vpc::my-vpc'
  }
  urn_to_node_id = {
      'urn:pulumi:dev::myproject::aws:ec2/vpc:Vpc::my-vpc': 'resource_0'
  }
  dot_lines = []
  ```
- **期待結果**:
  - `dot_lines`に1行追加される
  - 追加された行: `'    "resource_1" -> "resource_0" [style=dashed, color="#2196F3", label="parent", fontsize="10"];'`
  - スタイル: `dashed`（破線）
  - 色: `#2196F3`（青色）
  - ラベル: `parent`
- **テストデータ**: 上記入力データ

#### テストケース 2.3.2: add_parent_dependency_parentなし

- **目的**: parent=Noneの場合、何も追加されないことを検証
- **前提条件**: parent=Noneのリソース
- **入力**:
  ```python
  node_id = 'resource_1'
  resource = {'parent': None}
  urn_to_node_id = {}
  dot_lines = []
  ```
- **期待結果**:
  - `dot_lines`に何も追加されない
  - エラーが発生しない
- **テストデータ**: parent=Noneのリソース

#### テストケース 2.3.3: add_parent_dependency_parent空文字列

- **目的**: parent=空文字列の場合、何も追加されないことを検証
- **前提条件**: parent=空文字列のリソース
- **入力**:
  ```python
  node_id = 'resource_1'
  resource = {'parent': ''}
  urn_to_node_id = {}
  dot_lines = []
  ```
- **期待結果**:
  - `dot_lines`に何も追加されない
  - エラーが発生しない
- **テストデータ**: parent=空文字列のリソース

#### テストケース 2.3.4: add_parent_dependency_存在しないURN

- **目的**: URNマッピングに存在しない親URNが安全にスキップされることを検証
- **前提条件**: 存在しない親URNを持つリソース
- **入力**:
  ```python
  node_id = 'resource_1'
  resource = {
      'parent': 'urn:pulumi:dev::myproject::aws:ec2/vpc:Vpc::nonexistent'
  }
  urn_to_node_id = {
      'urn:pulumi:dev::myproject::aws:ec2/vpc:Vpc::my-vpc': 'resource_0'
  }
  dot_lines = []
  ```
- **期待結果**:
  - `dot_lines`に何も追加されない
  - エラーが発生しない
- **テストデータ**: 存在しない親URNを持つリソース

#### テストケース 2.3.5: add_parent_dependency_parentキーなし

- **目的**: 'parent'キーが存在しないリソースを安全に処理できることを検証
- **前提条件**: 'parent'キーを持たないリソース
- **入力**:
  ```python
  node_id = 'resource_1'
  resource = {'type': 'aws:s3/bucket:Bucket'}  # parentキーなし
  urn_to_node_id = {}
  dot_lines = []
  ```
- **期待結果**:
  - `dot_lines`に何も追加されない
  - エラーが発生しない
- **テストデータ**: parentキーなしのリソース

---

### 2.4 プロパティ依存関係追加テスト（TestPropertyDependencies）

#### テストケース 2.4.1: add_property_dependencies_正常系_1プロパティ

- **目的**: 1個のプロパティ依存関係が正しく追加されることを検証
- **前提条件**: 1個のプロパティ依存を持つリソースとURNマッピングが存在する
- **入力**:
  ```python
  node_id = 'resource_1'
  resource = {
      'propertyDependencies': {
          'bucket': ['urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket']
      }
  }
  urn_to_node_id = {
      'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket': 'resource_0'
  }
  dot_lines = []
  ```
- **期待結果**:
  - `dot_lines`に1行追加される
  - 追加された行: `'    "resource_1" -> "resource_0" [style=dotted, color="#FF5722", label="bucket", fontsize="9"];'`
  - スタイル: `dotted`（点線）
  - 色: `#FF5722`（オレンジ色）
  - ラベル: `bucket`（プロパティ名）
- **テストデータ**: 上記入力データ

#### テストケース 2.4.2: add_property_dependencies_複数プロパティ_3個

- **目的**: 複数（3個）のプロパティ依存関係が正しく追加されることを検証
- **前提条件**: 3個のプロパティ依存を持つリソース
- **入力**:
  ```python
  node_id = 'resource_3'
  resource = {
      'propertyDependencies': {
          'vpcId': ['urn:pulumi:dev::myproject::aws:ec2/vpc:Vpc::my-vpc'],
          'securityGroupIds': [
              'urn:pulumi:dev::myproject::aws:ec2/securityGroup:SecurityGroup::sg-a',
              'urn:pulumi:dev::myproject::aws:ec2/securityGroup:SecurityGroup::sg-b'
          ]
      }
  }
  urn_to_node_id = {
      'urn:pulumi:dev::myproject::aws:ec2/vpc:Vpc::my-vpc': 'resource_0',
      'urn:pulumi:dev::myproject::aws:ec2/securityGroup:SecurityGroup::sg-a': 'resource_1',
      'urn:pulumi:dev::myproject::aws:ec2/securityGroup:SecurityGroup::sg-b': 'resource_2'
  }
  dot_lines = []
  ```
- **期待結果**:
  - `dot_lines`に3行追加される
  - 1つ目: `label="vpcId"`
  - 2つ目: `label="securityGroupIds"`
  - 3つ目: `label="securityGroupIds"`
  - すべて`style=dotted`
- **テストデータ**: 上記入力データ

#### テストケース 2.4.3: add_property_dependencies_長いプロパティ名

- **目的**: 長いプロパティ名が末尾のみに省略されることを検証
- **前提条件**: ドット区切りの長いプロパティ名を持つリソース
- **入力**:
  ```python
  node_id = 'resource_1'
  resource = {
      'propertyDependencies': {
          'vpc.subnet.id': ['urn:pulumi:dev::myproject::aws:ec2/subnet:Subnet::my-subnet']
      }
  }
  urn_to_node_id = {
      'urn:pulumi:dev::myproject::aws:ec2/subnet:Subnet::my-subnet': 'resource_0'
  }
  dot_lines = []
  ```
- **期待結果**:
  - `dot_lines`に1行追加される
  - ラベル: `id`（`vpc.subnet.id`の末尾のみ）
  - 追加された行に`label="id"`が含まれる
- **テストデータ**: 長いプロパティ名を持つリソース

#### テストケース 2.4.4: add_property_dependencies_空辞書

- **目的**: 空のpropertyDependencies辞書の場合、何も追加されないことを検証
- **前提条件**: 空のpropertyDependencies辞書を持つリソース
- **入力**:
  ```python
  node_id = 'resource_1'
  resource = {'propertyDependencies': {}}
  urn_to_node_id = {}
  dot_lines = []
  ```
- **期待結果**:
  - `dot_lines`に何も追加されない
  - エラーが発生しない
- **テストデータ**: 空辞書を持つリソース

#### テストケース 2.4.5: add_property_dependencies_存在しないURN

- **目的**: URNマッピングに存在しないURNへのプロパティ依存が安全にスキップされることを検証
- **前提条件**: 存在しないURNへのプロパティ依存を持つリソース
- **入力**:
  ```python
  node_id = 'resource_1'
  resource = {
      'propertyDependencies': {
          'vpcId': [
              'urn:pulumi:dev::myproject::aws:ec2/vpc:Vpc::my-vpc',  # 存在する
              'urn:pulumi:dev::myproject::aws:ec2/vpc:Vpc::nonexistent'  # 存在しない
          ]
      }
  }
  urn_to_node_id = {
      'urn:pulumi:dev::myproject::aws:ec2/vpc:Vpc::my-vpc': 'resource_0'
  }
  dot_lines = []
  ```
- **期待結果**:
  - `dot_lines`に1行のみ追加される（存在するURNのみ）
  - 存在しないURNはスキップされる
  - エラーが発生しない
- **テストデータ**: 存在しないURNを含むプロパティ依存

#### テストケース 2.4.6: add_property_dependencies_propertyDependenciesキーなし

- **目的**: 'propertyDependencies'キーが存在しないリソースを安全に処理できることを検証
- **前提条件**: 'propertyDependencies'キーを持たないリソース
- **入力**:
  ```python
  node_id = 'resource_1'
  resource = {'type': 'aws:s3/bucket:Bucket'}  # propertyDependenciesキーなし
  urn_to_node_id = {}
  dot_lines = []
  ```
- **期待結果**:
  - `dot_lines`に何も追加されない
  - エラーが発生しない
- **テストデータ**: propertyDependenciesキーなしのリソース

---

### 2.5 リソース依存関係追加テスト（TestResourceDependencies）

#### テストケース 2.5.1: add_resource_dependencies_正常系_2リソース

- **目的**: 2個のリソースで依存関係が正しく追加されることを検証
- **前提条件**: 2個のリソース（1つは依存関係を持つ）
- **入力**:
  ```python
  resources = [
      {
          'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-a',
          'dependencies': [],
          'parent': None,
          'propertyDependencies': {}
      },
      {
          'urn': 'urn:pulumi:dev::myproject::aws:s3/bucketObject:BucketObject::my-object',
          'dependencies': ['urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-a'],
          'parent': None,
          'propertyDependencies': {}
      }
  ]
  dot_lines = []
  ```
- **期待結果**:
  - `dot_lines`に3行以上追加される
  - 1行目: 空行 `''`
  - 2行目: コメント `'    // リソース間の依存関係'`
  - 3行目以降: 依存関係エッジ
  - `resource_1 -> resource_0`のエッジが含まれる
- **テストデータ**: 上記リソースリスト

#### テストケース 2.5.2: add_resource_dependencies_空リスト

- **目的**: 空リストを渡した場合、何も追加されないことを検証
- **前提条件**: 空のリソースリスト
- **入力**: `resources = []`, `dot_lines = []`
- **期待結果**:
  - `dot_lines`に何も追加されない（空のまま）
  - エラーが発生しない
- **テストデータ**: 空リスト

#### テストケース 2.5.3: add_resource_dependencies_1リソース

- **目的**: 1個のリソースの場合、何も追加されないことを検証
- **前提条件**: 1個のリソースリスト
- **入力**:
  ```python
  resources = [
      {
          'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket',
          'dependencies': [],
          'parent': None,
          'propertyDependencies': {}
      }
  ]
  dot_lines = []
  ```
- **期待結果**:
  - `dot_lines`に何も追加されない（依存関係がないため）
  - エラーが発生しない
- **テストデータ**: 1個のリソースリスト

#### テストケース 2.5.4: add_resource_dependencies_20リソース

- **目的**: 最大20リソースの依存関係が正しく処理されることを検証
- **前提条件**: ちょうど20個のリソースリスト
- **入力**: 20個のリソース（各リソースは前のリソースに依存）
- **期待結果**:
  - `dot_lines`に複数行追加される
  - コメント行 `'    // リソース間の依存関係'`が含まれる
  - 19個の依存関係エッジが含まれる（resource_1 -> resource_0, resource_2 -> resource_1, ...）
- **テストデータ**: 20個のリソースリスト

#### テストケース 2.5.5: add_resource_dependencies_複合シナリオ

- **目的**: 直接+親+プロパティ依存が混在する複合シナリオが正しく処理されることを検証
- **前提条件**: 3種類の依存関係を持つリソースリスト
- **入力**:
  ```python
  resources = [
      {
          'urn': 'urn:pulumi:dev::myproject::aws:ec2/vpc:Vpc::my-vpc',
          'dependencies': [],
          'parent': None,
          'propertyDependencies': {}
      },
      {
          'urn': 'urn:pulumi:dev::myproject::aws:ec2/subnet:Subnet::my-subnet',
          'dependencies': ['urn:pulumi:dev::myproject::aws:ec2/vpc:Vpc::my-vpc'],
          'parent': 'urn:pulumi:dev::myproject::aws:ec2/vpc:Vpc::my-vpc',
          'propertyDependencies': {
              'vpcId': ['urn:pulumi:dev::myproject::aws:ec2/vpc:Vpc::my-vpc']
          }
      }
  ]
  dot_lines = []
  ```
- **期待結果**:
  - `dot_lines`に5行追加される
  - 1行目: 空行
  - 2行目: コメント
  - 3行目: 直接依存（`style=solid`）
  - 4行目: 親依存（`style=dashed`, `label="parent"`）
  - 5行目: プロパティ依存（`style=dotted`, `label="vpcId"`）
- **テストデータ**: 上記リソースリスト

---

### 2.6 エッジケーステスト（TestEdgeCases）

#### テストケース 2.6.1: 循環依存の処理

- **目的**: 循環依存が含まれる場合でも両方のエッジが生成されることを検証
- **前提条件**: resource_0がresource_1に依存し、resource_1がresource_0に依存
- **入力**:
  ```python
  resources = [
      {
          'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-a',
          'dependencies': ['urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-b'],
          'parent': None,
          'propertyDependencies': {}
      },
      {
          'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-b',
          'dependencies': ['urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-a'],
          'parent': None,
          'propertyDependencies': {}
      }
  ]
  dot_lines = []
  ```
- **期待結果**:
  - `dot_lines`に4行追加される（空行、コメント、エッジ2本）
  - `resource_0 -> resource_1`のエッジが含まれる
  - `resource_1 -> resource_0`のエッジが含まれる
  - 無限ループが発生しない
  - エラーが発生しない
- **テストデータ**: 循環依存を持つリソースリスト

#### テストケース 2.6.2: 自己参照依存

- **目的**: 自分自身への依存が安全に処理されることを検証
- **前提条件**: resource_0がresource_0自身に依存
- **入力**:
  ```python
  resources = [
      {
          'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-a',
          'dependencies': ['urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-a'],
          'parent': None,
          'propertyDependencies': {}
      }
  ]
  dot_lines = []
  ```
- **期待結果**:
  - `dot_lines`に何も追加されない（リソースが1個のみのため）
  - エラーが発生しない
- **テストデータ**: 自己参照依存を持つリソース

#### テストケース 2.6.3: 極端に長いURN

- **目的**: 極端に長いURN（300文字以上）が正常に処理されることを検証
- **前提条件**: 極端に長いURNを持つリソース
- **入力**:
  ```python
  long_name = 'a' * 300
  resources = [
      {
          'urn': f'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::{long_name}',
          'dependencies': [],
          'parent': None,
          'propertyDependencies': {}
      }
  ]
  dot_lines = []
  ```
- **期待結果**:
  - URNマッピングに長いURNが正しく登録される
  - エラーが発生しない
- **テストデータ**: 極端に長いURNを持つリソース

#### テストケース 2.6.4: すべてのフィールドがNoneのリソース

- **目的**: すべてのフィールドがNoneのリソースを安全に処理できることを検証
- **前提条件**: dependencies, parent, propertyDependenciesがすべてNoneのリソース
- **入力**:
  ```python
  resources = [
      {
          'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-a',
          'dependencies': None,
          'parent': None,
          'propertyDependencies': None
      },
      {
          'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-b',
          'dependencies': None,
          'parent': None,
          'propertyDependencies': None
      }
  ]
  dot_lines = []
  ```
- **期待結果**:
  - `dot_lines`に2行追加される（空行、コメント）
  - 依存関係エッジは追加されない
  - エラーが発生しない
- **テストデータ**: すべてNoneのリソースリスト

---

### 2.7 エラーハンドリングテスト（TestErrorHandling）

#### テストケース 2.7.1: 不正なリソース辞書_urnキーなし

- **目的**: 'urn'キーが存在しないリソース辞書を安全に処理できることを検証
- **前提条件**: 'urn'キーを持たないリソース辞書
- **入力**:
  ```python
  resources = [
      {'type': 'aws:s3/bucket:Bucket'},  # urnキーなし
      {'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-b'}
  ]
  dot_lines = []
  ```
- **期待結果**:
  - URNマッピングに空文字列がキーとして追加される
  - エラーが発生しない
- **テストデータ**: urnキーなしのリソース

#### テストケース 2.7.2: Noneリソース

- **目的**: Noneリソースが含まれる場合の動作を検証
- **前提条件**: Noneを含むリソースリスト
- **入力**:
  ```python
  resources = [
      None,
      {'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-b'}
  ]
  dot_lines = []
  ```
- **期待結果**:
  - AttributeErrorが発生する可能性がある（設計上の想定外）
  - または、Noneリソースがスキップされる
- **テストデータ**: Noneを含むリソースリスト

**注**: このテストケースは、実装が想定外の入力に対してどのように動作するかを確認するためのものです。

#### テストケース 2.7.3: 不正なpropertyDependencies形式

- **目的**: propertyDependenciesがリスト形式でない場合の動作を検証
- **前提条件**: propertyDependenciesの値が文字列（リストではない）
- **入力**:
  ```python
  resources = [
      {
          'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-a',
          'dependencies': [],
          'parent': None,
          'propertyDependencies': {
              'bucket': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket'  # リストではない
          }
      },
      {
          'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-b',
          'dependencies': [],
          'parent': None,
          'propertyDependencies': {}
      }
  ]
  dot_lines = []
  ```
- **期待結果**:
  - TypeErrorが発生する可能性がある
  - または、文字列がイテレーション可能として処理される（各文字が依存URNとして扱われる）
- **テストデータ**: 不正なpropertyDependencies形式のリソース

**注**: このテストケースも、実装が想定外の入力に対してどのように動作するかを確認するためのものです。

---

### 2.8 定数スタイル設定テスト（TestStyleConstants）

#### テストケース 2.8.1: DIRECT_DEPENDENCY_STYLE定数

- **目的**: 直接依存関係のスタイル定数が正しく定義されていることを検証
- **前提条件**: ResourceDependencyBuilderクラスが読み込まれている
- **入力**: なし
- **期待結果**:
  - `ResourceDependencyBuilder.DIRECT_DEPENDENCY_STYLE == 'style=solid, color="#9C27B0", fontsize="10"'`
- **テストデータ**: なし

#### テストケース 2.8.2: PARENT_DEPENDENCY_STYLE定数

- **目的**: 親依存関係のスタイル定数が正しく定義されていることを検証
- **前提条件**: ResourceDependencyBuilderクラスが読み込まれている
- **入力**: なし
- **期待結果**:
  - `ResourceDependencyBuilder.PARENT_DEPENDENCY_STYLE == 'style=dashed, color="#2196F3", label="parent", fontsize="10"'`
- **テストデータ**: なし

#### テストケース 2.8.3: PROPERTY_DEPENDENCY_STYLE定数

- **目的**: プロパティ依存関係のスタイル定数が正しく定義されていることを検証
- **前提条件**: ResourceDependencyBuilderクラスが読み込まれている
- **入力**: なし
- **期待結果**:
  - `ResourceDependencyBuilder.PROPERTY_DEPENDENCY_STYLE == 'style=dotted, color="#FF5722", fontsize="9"'`
- **テストデータ**: なし

---

## 3. Integrationテストシナリオ

### 3.1 DotFileGeneratorとの統合テスト

#### 統合シナリオ 3.1.1: DotFileGenerator経由での依存関係追加

- **目的**: DotFileGeneratorからResourceDependencyBuilderへの委譲が正しく機能することを検証
- **前提条件**:
  - DotFileGeneratorクラスが存在する
  - ResourceDependencyBuilderクラスがimportされている
  - DotFileGenerator._add_resource_dependencies()がResourceDependencyBuilder.add_resource_dependencies()を呼び出す
- **テスト手順**:
  1. 2個のリソース（1つは依存関係を持つ）を準備
  2. `DotFileGenerator.create_dot_file()`を呼び出す
  3. 返されたDOT文字列リストを確認
- **期待結果**:
  - DOT文字列リストに`// リソース間の依存関係`のコメント行が含まれる
  - DOT文字列リストに依存関係エッジ（`resource_1 -> resource_0`）が含まれる
  - 外部インターフェース（`create_dot_file()`のシグネチャ）に変更がない
- **確認項目**:
  - [ ] `create_dot_file()`が正常に完了する
  - [ ] 依存関係コメント行が含まれる
  - [ ] 依存関係エッジが含まれる
  - [ ] 既存の動作と一致する

#### 統合シナリオ 3.1.2: 既存のtest_dot_processor.pyの全テストパス

- **目的**: 既存の統合テスト（特性テスト）が全てパスすることを検証
- **前提条件**:
  - `test_dot_processor.py`の既存テストスイートが存在する（841行）
  - ResourceDependencyBuilderクラスが実装されている
  - DotFileGeneratorがResourceDependencyBuilderを呼び出している
- **テスト手順**:
  1. `pytest tests/test_dot_processor.py`を実行
  2. すべてのテストがパスすることを確認
  3. カバレッジレポートを生成
- **期待結果**:
  - すべてのテストがパス（841行のテストすべて）
  - リグレッションが発生していない
  - 特性テスト（Characterization Test）が維持される
- **確認項目**:
  - [ ] TestDotFileGeneratorEscapingクラスの全テストがパス
  - [ ] TestDotFileGeneratorCreationクラスの全テストがパス
  - [ ] TestDotFileProcessorUrnParsingクラスの全テストがパス
  - [ ] TestDotFileProcessorGraphStylingクラスの全テストがパス
  - [ ] TestDotFileProcessorGraphValidationクラスの全テストがパス
  - [ ] TestDotFileProcessorLabelCreationクラスの全テストがパス
  - [ ] TestDotFileProcessorResourceIdentificationクラスの全テストがパス
  - [ ] TestEdgeCasesクラスの全テストがパス

#### 統合シナリオ 3.1.3: end-to-endのDOTファイル生成

- **目的**: end-to-endで実際のDOTファイル生成プロセスが正常に動作することを検証
- **前提条件**: 実際のPulumiリソースデータに近いサンプルデータが存在する
- **テスト手順**:
  1. サンプルスタック名、リソースリスト、プロバイダー辞書を準備
  2. `DotFileGenerator.create_dot_file()`を呼び出す
  3. 返されたDOT文字列リストを結合してDOT文字列を生成
  4. DOT文字列の構造を検証
- **期待結果**:
  - 有効なDOT形式の文字列が生成される
  - `digraph G {`で開始し`}`で終了する
  - スタックノードが含まれる
  - プロバイダーノードが含まれる
  - リソースノードが含まれる
  - 依存関係エッジが含まれる
- **確認項目**:
  - [ ] DOT形式の構文が正しい
  - [ ] すべてのノードが含まれる
  - [ ] すべてのエッジが含まれる
  - [ ] スタイル設定が適用されている

---

### 3.2 既存テストとの互換性テスト

#### 統合シナリオ 3.2.1: test_create_dot_file_resource_dependenciesとの互換性

- **目的**: 既存の`test_create_dot_file_resource_dependencies`テストが引き続き動作することを検証
- **前提条件**:
  - test_dot_processor.py:L309-L328のテストが存在する
  - ResourceDependencyBuilderが実装されている
- **テスト手順**:
  1. `pytest tests/test_dot_processor.py::TestDotFileGeneratorCreation::test_create_dot_file_resource_dependencies`を実行
  2. テストがパスすることを確認
- **期待結果**:
  - テストがパスする
  - `resource_1 -> resource_0`のエッジが生成される
  - 依存関係のエッジが正しく含まれる
- **確認項目**:
  - [ ] テストがパスする
  - [ ] アサーションが全て成功する

#### 統合シナリオ 3.2.2: test_circular_dependenciesとの互換性

- **目的**: 既存の`test_circular_dependencies`テストが引き続き動作することを検証
- **前提条件**:
  - test_dot_processor.py:L794-L825のテストが存在する
  - ResourceDependencyBuilderが実装されている
- **テスト手順**:
  1. `pytest tests/test_dot_processor.py::TestEdgeCases::test_circular_dependencies`を実行
  2. テストがパスすることを確認
- **期待結果**:
  - テストがパスする
  - エラーが発生しない
  - 両方の依存関係エッジが生成される
- **確認項目**:
  - [ ] テストがパスする
  - [ ] 循環依存が正しく処理される

---

## 4. テストデータ

### 4.1 基本的なリソースデータ

以下のfixtureを`conftest.py`に追加します：

```python
@pytest.fixture
def sample_dependency_resources():
    """依存関係テスト用のサンプルリソース"""
    return [
        {
            'type': 'aws:ec2/vpc:Vpc',
            'urn': 'urn:pulumi:dev::myproject::aws:ec2/vpc:Vpc::my-vpc',
            'dependencies': [],
            'parent': None,
            'propertyDependencies': {}
        },
        {
            'type': 'aws:ec2/subnet:Subnet',
            'urn': 'urn:pulumi:dev::myproject::aws:ec2/subnet:Subnet::my-subnet',
            'dependencies': ['urn:pulumi:dev::myproject::aws:ec2/vpc:Vpc::my-vpc'],
            'parent': 'urn:pulumi:dev::myproject::aws:ec2/vpc:Vpc::my-vpc',
            'propertyDependencies': {
                'vpcId': ['urn:pulumi:dev::myproject::aws:ec2/vpc:Vpc::my-vpc']
            }
        },
        {
            'type': 'aws:s3/bucket:Bucket',
            'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket',
            'dependencies': [],
            'parent': None,
            'propertyDependencies': {}
        }
    ]


@pytest.fixture
def circular_dependency_resources():
    """循環依存テスト用のリソース"""
    return [
        {
            'type': 'aws:s3/bucket:Bucket',
            'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-a',
            'dependencies': ['urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-b'],
            'parent': None,
            'propertyDependencies': {}
        },
        {
            'type': 'aws:s3/bucket:Bucket',
            'urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-b',
            'dependencies': ['urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-a'],
            'parent': None,
            'propertyDependencies': {}
        }
    ]


@pytest.fixture
def resource_dependency_builder():
    """ResourceDependencyBuilderインスタンス（静的メソッドのためクラスを返す）"""
    from resource_dependency_builder import ResourceDependencyBuilder
    return ResourceDependencyBuilder
```

### 4.2 正常データ

- **3リソース**: 上記`sample_dependency_resources`
- **2リソース（依存あり）**: `sample_dependency_resources[:2]`
- **20リソース**: ループで生成（bucket-0からbucket-19まで）

### 4.3 異常データ

- **空リスト**: `[]`
- **1リソース**: `[{'urn': '...', 'dependencies': [], 'parent': None, 'propertyDependencies': {}}]`
- **urnキーなし**: `[{'type': 'aws:s3/bucket:Bucket'}]`
- **dependencies=None**: `[{'urn': '...', 'dependencies': None, 'parent': None, 'propertyDependencies': None}]`

### 4.4 境界値データ

- **循環依存**: 上記`circular_dependency_resources`
- **極端に長いURN**: `'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::' + 'a' * 300`
- **最大20リソース**: ループで生成
- **21リソース以上**: 25個のリソースリスト（最初の20個のみ処理される）

---

## 5. テスト環境要件

### 5.1 必要なテスト環境
- **ローカル環境**: 開発者のローカルマシン
- **CI/CD環境**: GitHub Actions（既存のワークフローを使用）

### 5.2 必要な外部サービス・データベース
- **なし**: 外部サービスへの依存なし
- **データベース**: 不要

### 5.3 モック/スタブの必要性
- **不要**: ResourceDependencyBuilderは外部依存がないため、モック不要
- **DotFileGenerator**: 統合テストでは実際のDotFileGeneratorを使用

### 5.4 必要なPythonパッケージ
- **pytest**: テスト実行
- **pytest-cov**: カバレッジ測定
- **既存の依存**: typing（標準ライブラリ）

### 5.5 テスト実行コマンド

#### 単体テストのみ実行:
```bash
pytest tests/test_resource_dependency_builder.py -v
```

#### 単体テストとカバレッジ測定:
```bash
pytest tests/test_resource_dependency_builder.py --cov=src/resource_dependency_builder --cov-report=term-missing --cov-report=html
```

#### 統合テストのみ実行:
```bash
pytest tests/test_dot_processor.py -v
```

#### 全テスト実行:
```bash
pytest tests/ -v
```

#### カバレッジ目標確認:
```bash
pytest tests/test_resource_dependency_builder.py --cov=src/resource_dependency_builder --cov-fail-under=80
```

---

## 6. カバレッジ目標

### 6.1 カバレッジ測定方法
- **ツール**: pytest-cov
- **コマンド**: `pytest --cov=src/resource_dependency_builder --cov-report=term-missing`
- **レポート形式**: ターミナル出力 + HTMLレポート

### 6.2 カバレッジ目標
- **全体目標**: 80%以上（必須）
- **各メソッド目標**:
  - `create_urn_to_node_mapping()`: 100%
  - `add_resource_dependencies()`: 100%
  - `_add_dependencies_for_resource()`: 100%
  - `_add_direct_dependencies()`: 100%
  - `_add_parent_dependency()`: 100%
  - `_add_property_dependencies()`: 100%

### 6.3 カバレッジ測定タイミング
- **Phase 5（テストコード実装）**: 継続的にカバレッジを測定
- **Phase 6（テスト実行）**: 最終的なカバレッジ確認

### 6.4 未カバー箇所の特定方法
- `--cov-report=term-missing`オプションでカバーされていない行番号を表示
- HTMLレポート（`--cov-report=html`）で視覚的に確認

---

## 7. テスト実装の優先順位

以下の優先順位でテストを実装します：

### 優先度1（最優先）: 基本的な正常系
1. `create_urn_to_node_mapping_正常系_3リソース` (2.1.1)
2. `add_direct_dependencies_正常系_1依存` (2.2.1)
3. `add_parent_dependency_正常系` (2.3.1)
4. `add_property_dependencies_正常系_1プロパティ` (2.4.1)
5. `add_resource_dependencies_正常系_2リソース` (2.5.1)

### 優先度2（高）: エッジケースと空/None処理
1. `create_urn_to_node_mapping_空リスト` (2.1.2)
2. `add_resource_dependencies_空リスト` (2.5.2)
3. `add_resource_dependencies_1リソース` (2.5.3)
4. `add_direct_dependencies_空依存リスト` (2.2.3)
5. `add_parent_dependency_parentなし` (2.3.2)
6. `add_property_dependencies_空辞書` (2.4.4)

### 優先度3（中）: 複合シナリオと境界値
1. `add_resource_dependencies_複合シナリオ` (2.5.5)
2. `add_resource_dependencies_20リソース` (2.5.4)
3. `循環依存の処理` (2.6.1)
4. `add_direct_dependencies_複数依存_3個` (2.2.2)
5. `add_property_dependencies_複数プロパティ_3個` (2.4.2)

### 優先度4（低）: エラーハンドリングと特殊ケース
1. `add_direct_dependencies_存在しないURN` (2.2.4)
2. `add_parent_dependency_存在しないURN` (2.3.4)
3. `add_property_dependencies_存在しないURN` (2.4.5)
4. `add_property_dependencies_長いプロパティ名` (2.4.3)
5. `極端に長いURN` (2.6.3)

### 優先度5（統合テスト）: 統合テストの確認
1. `DotFileGenerator経由での依存関係追加` (3.1.1)
2. `既存のtest_dot_processor.pyの全テストパス` (3.1.2)
3. `end-to-endのDOTファイル生成` (3.1.3)

---

## 8. 品質ゲート確認

テストシナリオは以下の品質ゲートを満たしています：

- [x] **Phase 2の戦略に沿ったテストシナリオである**
  - UNIT_INTEGRATION戦略に基づき、単体テストと統合テストの両方を定義
  - CREATE_TESTとEXTEND_TESTの両方に対応

- [x] **主要な正常系がカバーされている**
  - 優先度1でURNマッピング作成、3種類の依存関係追加、全体のオーケストレーションをカバー
  - 合計5個の正常系テストケース

- [x] **主要な異常系がカバーされている**
  - 優先度2で空リスト、None、キーなし等の異常系をカバー
  - 優先度4で存在しないURN等のエラーハンドリングをカバー
  - 合計10個以上の異常系テストケース

- [x] **期待結果が明確である**
  - すべてのテストケースでGiven-When-Then形式に近い構造を採用
  - 入力、前提条件、期待結果を明確に記載
  - 検証可能な具体的な値（文字列、数値）を記載

---

## 9. 次フェーズへの引き継ぎ事項

### Phase 4（実装）への引き継ぎ:

1. **テストファーストアプローチ**:
   - テストシナリオを参照しながら実装を進める
   - 優先度1のテストケースから順に実装と検証を行う

2. **カバレッジの継続的測定**:
   - 各メソッド実装後、対応するテストを実行してカバレッジを確認
   - 80%未達の場合は、テストケースを追加

3. **既存テストの動作確認タイミング**:
   - Phase 4-2（dot_processor.pyの更新）完了後、すぐに既存テストを実行
   - リグレッションが発生した場合は即座に修正

### Phase 5（テストコード実装）への引き継ぎ:

1. **テストコードの実装順序**:
   - セクション7（優先順位）に従って実装
   - 優先度1から順に実装し、都度カバレッジを測定

2. **fixtureの準備**:
   - セクション4.1の`sample_dependency_resources`等のfixtureを`conftest.py`に追加
   - 既存のfixtureを再利用（`sample_resources`, `sample_urns`）

3. **テストデータの準備**:
   - JSON形式のテストデータファイルは不要（Pythonコード内で定義）
   - 複雑なテストデータはfixtureとして定義

---

**テストシナリオ作成日**: 2025-01-XX
**テストシナリオバージョン**: 1.0
**作成者**: AI Test Scenario Agent (Phase 3)
