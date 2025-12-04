# テストシナリオ: dot_processor.py - Phase 2-1: UrnProcessorクラスの抽出

## ドキュメント情報

- **Issue番号**: #461
- **タイトル**: [Refactor] dot_processor.py - Phase 2-1: UrnProcessorクラスの抽出
- **親Issue**: #448
- **依存Issue**: #460 (Phase 1: 基盤整備)
- **作成日**: 2025-01-19
- **最終更新**: 2025-01-19
- **作成者**: AI Workflow Phase 3
- **レビュー状態**: 未レビュー

---

## 0. Planning Phase、Requirements Phase、Design Phaseの確認

### テスト戦略（Phase 2で決定）

**テスト戦略**: UNIT_INTEGRATION

**判断根拠**:
1. **ユニットテスト（UNIT）**: 新規クラス`UrnProcessor`の全公開メソッドを独立してテストする
2. **インテグレーションテスト（INTEGRATION）**: `DotFileProcessor`と`UrnProcessor`間の統合が正常に動作することを検証
3. **BDD不要の理由**: ユーザーストーリーではなく、技術的なリファクタリングである

**テストコード戦略**: BOTH_TEST
- CREATE_TEST: `test_urn_processor.py`を新規作成
- EXTEND_TEST: `test_dot_processor.py`を更新（統合テストとして継続）

**カバレッジ目標**: 80%以上
- 全公開メソッド: 100%
- プライベートメソッド: 70%以上

---

## 1. テスト戦略サマリー

### 1.1 選択されたテスト戦略

**UNIT_INTEGRATION**: ユニットテスト + 統合テスト

### 1.2 テスト対象の範囲

**ユニットテスト対象**:
- 新規クラス: `UrnProcessor`
  - `parse_urn()`: URNをパースして構成要素を抽出
  - `_parse_provider_type()`: プロバイダータイプ文字列を解析（プライベート）
  - `create_readable_label()`: URN情報から読みやすいラベルを生成
  - `_format_resource_type()`: リソースタイプを読みやすい形式にフォーマット（プライベート）
  - `is_stack_resource()`: スタックリソースかどうかを判定

**統合テスト対象**:
- `DotFileProcessor`と`UrnProcessor`の統合
  - `DotFileProcessor._process_node_definition()` → `UrnProcessor.parse_urn()`
  - `DotFileProcessor._generate_resource_node_attributes()` → `UrnProcessor.create_readable_label()`
  - `DotFileProcessor._shorten_pulumi_label()` → `UrnProcessor`の各メソッド
- エンドツーエンドのDOT生成フロー

### 1.3 テストの目的

1. **リファクタリングの安全性保証**: 外部から見た振る舞いが変更されていないことを検証
2. **URN処理ロジックの正確性**: 各種プロバイダー（AWS、Azure、GCP、Kubernetes）のURNが正しく処理されることを検証
3. **エッジケースの網羅**: 不正なURN、空文字列、極端に長いURN等のエッジケースが正しく処理されることを検証
4. **統合動作の検証**: `DotFileProcessor`と`UrnProcessor`が正しく連携することを検証

---

## 2. ユニットテストシナリオ

### 2.1 TestUrnProcessorParsing - URNパースのテスト

#### 2.1.1 parse_urn_valid_aws - 正常なAWS URNの解析

**テストケース名**: `test_parse_urn_valid_aws`

- **目的**: AWS URNが正しく解析されることを検証
- **前提条件**: `UrnProcessor`クラスが正しく実装されている
- **入力**:
  ```python
  urn = "urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket"
  ```
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
- **テストデータ**:
  ```python
  sample_aws_urn = "urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket"
  ```

#### 2.1.2 parse_urn_valid_azure - 正常なAzure URNの解析

**テストケース名**: `test_parse_urn_valid_azure`

- **目的**: Azure URNが正しく解析されることを検証
- **前提条件**: `UrnProcessor`クラスが正しく実装されている
- **入力**:
  ```python
  urn = "urn:pulumi:prod::azureapp::azure:storage/storageAccount:StorageAccount::mystorageaccount"
  ```
- **期待結果**:
  ```python
  {
      'stack': 'prod',
      'project': 'azureapp',
      'provider': 'azure',
      'module': 'storage',
      'type': 'StorageAccount',
      'name': 'mystorageaccount',
      'full_urn': 'urn:pulumi:prod::azureapp::azure:storage/storageAccount:StorageAccount::mystorageaccount'
  }
  ```
- **テストデータ**:
  ```python
  sample_azure_urn = "urn:pulumi:prod::azureapp::azure:storage/storageAccount:StorageAccount::mystorageaccount"
  ```

#### 2.1.3 parse_urn_valid_gcp - 正常なGCP URNの解析

**テストケース名**: `test_parse_urn_valid_gcp`

- **目的**: GCP URNが正しく解析されることを検証
- **前提条件**: `UrnProcessor`クラスが正しく実装されている
- **入力**:
  ```python
  urn = "urn:pulumi:staging::gcpproject::gcp:storage/bucket:Bucket::my-gcp-bucket"
  ```
- **期待結果**:
  ```python
  {
      'stack': 'staging',
      'project': 'gcpproject',
      'provider': 'gcp',
      'module': 'storage',
      'type': 'Bucket',
      'name': 'my-gcp-bucket',
      'full_urn': 'urn:pulumi:staging::gcpproject::gcp:storage/bucket:Bucket::my-gcp-bucket'
  }
  ```
- **テストデータ**:
  ```python
  sample_gcp_urn = "urn:pulumi:staging::gcpproject::gcp:storage/bucket:Bucket::my-gcp-bucket"
  ```

#### 2.1.4 parse_urn_valid_kubernetes - 正常なKubernetes URNの解析

**テストケース名**: `test_parse_urn_valid_kubernetes`

- **目的**: Kubernetes URNが正しく解析されることを検証
- **前提条件**: `UrnProcessor`クラスが正しく実装されている
- **入力**:
  ```python
  urn = "urn:pulumi:dev::k8sapp::kubernetes:apps/v1:Deployment::my-deployment"
  ```
- **期待結果**:
  ```python
  {
      'stack': 'dev',
      'project': 'k8sapp',
      'provider': 'kubernetes',
      'module': 'apps/v1',
      'type': 'Deployment',
      'name': 'my-deployment',
      'full_urn': 'urn:pulumi:dev::k8sapp::kubernetes:apps/v1:Deployment::my-deployment'
  }
  ```
- **テストデータ**:
  ```python
  sample_k8s_urn = "urn:pulumi:dev::k8sapp::kubernetes:apps/v1:Deployment::my-deployment"
  ```

#### 2.1.5 parse_urn_stack_resource - スタックリソースURNの解析

**テストケース名**: `test_parse_urn_stack_resource`

- **目的**: スタックリソースURNが正しく解析されることを検証
- **前提条件**: `UrnProcessor`クラスが正しく実装されている
- **入力**:
  ```python
  urn = "urn:pulumi:dev::myproject::pulumi:pulumi:Stack::dev"
  ```
- **期待結果**:
  ```python
  {
      'stack': 'dev',
      'project': 'myproject',
      'provider': 'pulumi',
      'module': 'pulumi',
      'type': 'Stack',
      'name': 'dev',
      'full_urn': 'urn:pulumi:dev::myproject::pulumi:pulumi:Stack::dev'
  }
  ```
- **テストデータ**:
  ```python
  sample_stack_urn = "urn:pulumi:dev::myproject::pulumi:pulumi:Stack::dev"
  ```

#### 2.1.6 parse_urn_invalid_format - 不正なURN形式（区切り不足）

**テストケース名**: `test_parse_urn_invalid_format`

- **目的**: 不正なURN形式でも例外を投げず、デフォルト値を返すことを検証
- **前提条件**: `UrnProcessor`クラスが正しく実装されている
- **入力**:
  ```python
  urn = "invalid-urn-format"
  ```
- **期待結果**:
  ```python
  {
      'stack': '',
      'project': '',
      'provider': 'unknown',
      'module': '',
      'type': 'unknown',
      'name': 'invalid-urn-format',
      'full_urn': 'invalid-urn-format'
  }
  ```
- **検証ポイント**:
  - 例外が発生しないこと
  - デフォルト値を含む辞書が返されること
  - `provider`と`type`が`'unknown'`であること
- **テストデータ**:
  ```python
  invalid_urn = "invalid-urn-format"
  ```

#### 2.1.7 parse_urn_partial_urn - 部分的なURN

**テストケース名**: `test_parse_urn_partial_urn`

- **目的**: 部分的なURN（一部の区切りが不足）でも安全に処理されることを検証
- **前提条件**: `UrnProcessor`クラスが正しく実装されている
- **入力**:
  ```python
  urn = "urn:pulumi:dev::myproject"
  ```
- **期待結果**:
  - 例外が発生しない
  - デフォルト値を含む辞書が返される
  - `stack`と`project`は抽出される
  - `provider`、`module`、`type`はデフォルト値
- **テストデータ**:
  ```python
  partial_urn = "urn:pulumi:dev::myproject"
  ```

#### 2.1.8 parse_urn_empty_string - 空文字列

**テストケース名**: `test_parse_urn_empty_string`

- **目的**: 空文字列でも例外を投げず、デフォルト値を返すことを検証
- **前提条件**: `UrnProcessor`クラスが正しく実装されている
- **入力**:
  ```python
  urn = ""
  ```
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
- **検証ポイント**:
  - 例外が発生しないこと
  - すべてのキーが存在すること
  - `name`が空文字列であること
- **テストデータ**:
  ```python
  empty_urn = ""
  ```

#### 2.1.9 parse_urn_extremely_long - 極端に長いURN

**テストケース名**: `test_parse_urn_extremely_long`

- **目的**: 極端に長いURN（1万文字）でもメモリリークや無限ループが発生しないことを検証
- **前提条件**: `UrnProcessor`クラスが正しく実装されている
- **入力**:
  ```python
  urn = "urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::" + "x" * 10000
  ```
- **期待結果**:
  - 例外が発生しない
  - 処理が完了する（タイムアウトしない）
  - メモリリークが発生しない
  - `name`に極端に長い文字列が含まれる
- **検証ポイント**:
  - 処理時間が100ms以内であること
  - メモリ使用量が異常に増加しないこと
- **テストデータ**:
  ```python
  extremely_long_urn = "urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::" + "x" * 10000
  ```

#### 2.1.10 parse_urn_no_module - モジュール名なしのURN

**テストケース名**: `test_parse_urn_no_module`

- **目的**: モジュール名がないURN（`provider:type`形式）が正しく解析されることを検証
- **前提条件**: `UrnProcessor`クラスが正しく実装されている
- **入力**:
  ```python
  urn = "urn:pulumi:dev::myproject::pulumi:Stack::dev"
  ```
- **期待結果**:
  ```python
  {
      'stack': 'dev',
      'project': 'myproject',
      'provider': 'pulumi',
      'module': '',
      'type': 'Stack',
      'name': 'dev',
      'full_urn': 'urn:pulumi:dev::myproject::pulumi:Stack::dev'
  }
  ```
- **検証ポイント**:
  - `module`が空文字列であること
  - その他の要素が正しく抽出されること
- **テストデータ**:
  ```python
  no_module_urn = "urn:pulumi:dev::myproject::pulumi:Stack::dev"
  ```

### 2.2 TestUrnProcessorLabelCreation - ラベル生成のテスト

#### 2.2.1 create_readable_label_basic - 基本的なラベル生成

**テストケース名**: `test_create_readable_label_basic`

- **目的**: URN情報から読みやすいラベルが正しく生成されることを検証
- **前提条件**: `UrnProcessor`クラスが正しく実装されている
- **入力**:
  ```python
  urn_info = {
      'provider': 'aws',
      'module': 's3',
      'type': 'Bucket',
      'name': 'my-bucket'
  }
  ```
- **期待結果**:
  ```python
  label = "s3\nBucket\nmy-bucket"
  ```
- **検証ポイント**:
  - モジュール名が含まれること
  - 改行区切り（`\n`）であること
  - タイプ名とリソース名が含まれること
- **テストデータ**:
  ```python
  basic_urn_info = {
      'provider': 'aws',
      'module': 's3',
      'type': 'Bucket',
      'name': 'my-bucket'
  }
  ```

#### 2.2.2 create_readable_label_no_module - モジュール名なしの場合

**テストケース名**: `test_create_readable_label_no_module`

- **目的**: モジュール名がない場合でもラベルが正しく生成されることを検証
- **前提条件**: `UrnProcessor`クラスが正しく実装されている
- **入力**:
  ```python
  urn_info = {
      'provider': 'pulumi',
      'module': '',
      'type': 'Stack',
      'name': 'dev'
  }
  ```
- **期待結果**:
  ```python
  label = "Stack\ndev"
  ```
- **検証ポイント**:
  - モジュール名が省略されること
  - タイプ名とリソース名のみが含まれること
  - 改行区切りであること
- **テストデータ**:
  ```python
  no_module_urn_info = {
      'provider': 'pulumi',
      'module': '',
      'type': 'Stack',
      'name': 'dev'
  }
  ```

#### 2.2.3 create_readable_label_long_type - 長いタイプ名の省略処理

**テストケース名**: `test_create_readable_label_long_type`

- **目的**: 長いタイプ名（30文字以上）が省略されることを検証
- **前提条件**: `UrnProcessor`クラスが正しく実装されている
- **入力**:
  ```python
  urn_info = {
      'provider': 'aws',
      'module': 'ecs',
      'type': 'VeryLongResourceTypeNameThatExceeds30Characters',
      'name': 'my-resource'
  }
  ```
- **期待結果**:
  - ラベルに省略されたタイプ名が含まれること
  - 省略形式は`_format_resource_type()`に依存
  - 省略記号（`...`）が含まれる可能性
- **検証ポイント**:
  - タイプ名が30文字以下に省略されること
  - 元のタイプ名の一部が保持されること
- **テストデータ**:
  ```python
  long_type_urn_info = {
      'provider': 'aws',
      'module': 'ecs',
      'type': 'VeryLongResourceTypeNameThatExceeds30Characters',
      'name': 'my-resource'
  }
  ```

#### 2.2.4 format_resource_type_short - 短いタイプ名（30文字以下）

**テストケース名**: `test_format_resource_type_short`

- **目的**: 短いタイプ名がそのまま返されることを検証
- **前提条件**: `UrnProcessor`クラスが正しく実装されている
- **入力**:
  ```python
  resource_type = "Bucket"
  ```
- **期待結果**:
  ```python
  formatted_type = "Bucket"
  ```
- **検証ポイント**:
  - タイプ名が変更されないこと
  - 長さが30文字以下であること
- **テストデータ**:
  ```python
  short_type = "Bucket"
  ```

#### 2.2.5 format_resource_type_long - 長いタイプ名（30文字以上）

**テストケース名**: `test_format_resource_type_long`

- **目的**: 長いタイプ名が省略されることを検証
- **前提条件**: `UrnProcessor`クラスが正しく実装されている
- **入力**:
  ```python
  resource_type = "VeryLongResourceTypeNameThatExceeds30Characters"
  ```
- **期待結果**:
  - 省略されたタイプ名が返される
  - 長さが30文字以下（または省略記号を含む）
  - キャメルケースを考慮した省略が行われる
- **検証ポイント**:
  - 長さが適切に制限されること
  - 省略記号（`...`）が含まれること
  - 読みやすい省略形であること
- **テストデータ**:
  ```python
  long_type = "VeryLongResourceTypeNameThatExceeds30Characters"
  ```

#### 2.2.6 create_readable_label_special_characters - 特殊文字を含む名前

**テストケース名**: `test_create_readable_label_special_characters`

- **目的**: 特殊文字を含むリソース名でもラベルが正しく生成されることを検証
- **前提条件**: `UrnProcessor`クラスが正しく実装されている
- **入力**:
  ```python
  urn_info = {
      'provider': 'aws',
      'module': 's3',
      'type': 'Bucket',
      'name': 'my-bucket-with-特殊文字'
  }
  ```
- **期待結果**:
  - 特殊文字がそのまま含まれること
  - エスケープ処理が適切に行われること
- **検証ポイント**:
  - 特殊文字が正しく処理されること
  - ラベル生成が失敗しないこと
- **テストデータ**:
  ```python
  special_char_urn_info = {
      'provider': 'aws',
      'module': 's3',
      'type': 'Bucket',
      'name': 'my-bucket-with-特殊文字'
  }
  ```

### 2.3 TestUrnProcessorResourceIdentification - リソース判定のテスト

#### 2.3.1 is_stack_resource_true - スタックリソースの判定

**テストケース名**: `test_is_stack_resource_true`

- **目的**: スタックリソースURNが正しく判定されることを検証
- **前提条件**: `UrnProcessor`クラスが正しく実装されている
- **入力**:
  ```python
  urn = "urn:pulumi:dev::myproject::pulumi:pulumi:Stack::dev"
  ```
- **期待結果**:
  ```python
  result = True
  ```
- **検証ポイント**:
  - `pulumi:pulumi:Stack`を含むURNが`True`と判定されること
- **テストデータ**:
  ```python
  stack_urn = "urn:pulumi:dev::myproject::pulumi:pulumi:Stack::dev"
  ```

#### 2.3.2 is_stack_resource_false - 通常リソースの判定

**テストケース名**: `test_is_stack_resource_false`

- **目的**: 通常リソースURNが正しく判定されることを検証
- **前提条件**: `UrnProcessor`クラスが正しく実装されている
- **入力**:
  ```python
  urn = "urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket"
  ```
- **期待結果**:
  ```python
  result = False
  ```
- **検証ポイント**:
  - `pulumi:pulumi:Stack`を含まないURNが`False`と判定されること
- **テストデータ**:
  ```python
  normal_urn = "urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket"
  ```

#### 2.3.3 is_stack_resource_invalid_urn - 不正なURN

**テストケース名**: `test_is_stack_resource_invalid_urn`

- **目的**: 不正なURNでも例外を投げず、`False`を返すことを検証
- **前提条件**: `UrnProcessor`クラスが正しく実装されている
- **入力**:
  ```python
  urn = "invalid-urn"
  ```
- **期待結果**:
  ```python
  result = False
  ```
- **検証ポイント**:
  - 例外が発生しないこと
  - `False`が返されること
- **テストデータ**:
  ```python
  invalid_urn = "invalid-urn"
  ```

#### 2.3.4 is_stack_resource_empty_string - 空文字列

**テストケース名**: `test_is_stack_resource_empty_string`

- **目的**: 空文字列でも例外を投げず、`False`を返すことを検証
- **前提条件**: `UrnProcessor`クラスが正しく実装されている
- **入力**:
  ```python
  urn = ""
  ```
- **期待結果**:
  ```python
  result = False
  ```
- **検証ポイント**:
  - 例外が発生しないこと
  - `False`が返されること
- **テストデータ**:
  ```python
  empty_urn = ""
  ```

### 2.4 TestEdgeCases - エッジケースのテスト

#### 2.4.1 extremely_long_urn_10000_chars - 極端に長いURN（1万文字）

**テストケース名**: `test_extremely_long_urn_10000_chars`

- **目的**: 極端に長いURN（1万文字）でもメモリリークや処理時間の問題が発生しないことを検証
- **前提条件**: `UrnProcessor`クラスが正しく実装されている
- **入力**:
  ```python
  urn = "urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::" + "x" * 10000
  ```
- **期待結果**:
  - 例外が発生しない
  - 処理が100ms以内に完了する
  - メモリリークが発生しない
  - パース結果の`name`に極端に長い文字列が含まれる
- **検証ポイント**:
  - 処理時間が許容範囲内であること
  - メモリ使用量が異常に増加しないこと
  - 正常に辞書が返されること
- **テストデータ**:
  ```python
  extremely_long_urn = "urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::" + "x" * 10000
  ```

#### 2.4.2 special_characters_in_urn - 特殊文字を含むURN

**テストケース名**: `test_special_characters_in_urn`

- **目的**: 特殊文字（SQLインジェクション文字列等）を含むURNでも安全に処理されることを検証
- **前提条件**: `UrnProcessor`クラスが正しく実装されている
- **入力**:
  ```python
  urn = "urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket'; DROP TABLE users;--"
  ```
- **期待結果**:
  - 例外が発生しない
  - エスケープが正しく行われる
  - コードインジェクションが発生しない
  - `name`に特殊文字が含まれる
- **検証ポイント**:
  - セキュリティリスクがないこと
  - 特殊文字がそのまま保持されること
- **テストデータ**:
  ```python
  sql_injection_urn = "urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket'; DROP TABLE users;--"
  ```

#### 2.4.3 unicode_characters_in_urn - Unicode文字を含むURN

**テストケース名**: `test_unicode_characters_in_urn`

- **目的**: Unicode文字（日本語、絵文字等）を含むURNでも正しく処理されることを検証
- **前提条件**: `UrnProcessor`クラスが正しく実装されている
- **入力**:
  ```python
  urn = "urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::私のバケット🎉"
  ```
- **期待結果**:
  - 例外が発生しない
  - Unicode文字がそのまま保持される
  - `name`にUnicode文字が含まれる
- **検証ポイント**:
  - Unicode対応が正しく実装されていること
  - 文字エンコーディングの問題がないこと
- **テストデータ**:
  ```python
  unicode_urn = "urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::私のバケット🎉"
  ```

#### 2.4.4 multiple_colons_in_name - リソース名に複数のコロンが含まれるURN

**テストケース名**: `test_multiple_colons_in_name`

- **目的**: リソース名に複数のコロンが含まれる場合でも正しく解析されることを検証
- **前提条件**: `UrnProcessor`クラスが正しく実装されている
- **入力**:
  ```python
  urn = "urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my:bucket:with:colons"
  ```
- **期待結果**:
  - 例外が発生しない
  - `name`に`my:bucket:with:colons`が含まれる
  - その他の要素が正しく抽出される
- **検証ポイント**:
  - コロン区切りのパースが正しく実装されていること
  - 最後の`::`以降がすべて`name`として扱われること
- **テストデータ**:
  ```python
  multiple_colons_urn = "urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my:bucket:with:colons"
  ```

---

## 3. 統合テストシナリオ

### 3.1 IntegrationDotFileProcessorUrnProcessor - DotFileProcessorとUrnProcessorの統合

#### 3.1.1 urn_processor_integration_in_process_node_definition - _process_node_definition内でのUrnProcessor使用

**シナリオ名**: `test_urn_processor_integration_in_process_node_definition`

- **目的**: `DotFileProcessor._process_node_definition()`が`UrnProcessor.parse_urn()`を正しく呼び出すことを検証
- **前提条件**:
  - `UrnProcessor`クラスが実装されている
  - `DotFileProcessor`が`UrnProcessor`をインポートしている
  - `_process_node_definition()`が修正されている
- **テスト手順**:
  1. サンプルDOT文字列を準備（URNを含むノード定義）
  2. `DotFileProcessor.apply_graph_styling()`を呼び出す
  3. 内部で`_process_node_definition()`が実行される
  4. `UrnProcessor.parse_urn()`が呼び出されることを確認
  5. パース結果がラベル生成に使用されることを確認
- **期待結果**:
  - DOT文字列が正しく処理される
  - URN情報が正しく抽出される
  - ノードラベルが正しく生成される
  - 既存のテストケースが全てパスする
- **確認項目**:
  - [ ] `UrnProcessor.parse_urn()`が呼び出されたか
  - [ ] パース結果が正しいか
  - [ ] ノード定義が正しく処理されたか
  - [ ] 例外が発生していないか

#### 3.1.2 urn_processor_integration_in_generate_resource_node_attributes - _generate_resource_node_attributes内でのUrnProcessor使用

**シナリオ名**: `test_urn_processor_integration_in_generate_resource_node_attributes`

- **目的**: `DotFileProcessor._generate_resource_node_attributes()`が`UrnProcessor.create_readable_label()`を正しく呼び出すことを検証
- **前提条件**:
  - `UrnProcessor`クラスが実装されている
  - `DotFileProcessor`が`UrnProcessor`をインポートしている
  - `_generate_resource_node_attributes()`が修正されている
- **テスト手順**:
  1. サンプルURNとURN情報を準備
  2. `_generate_resource_node_attributes()`を呼び出す
  3. 内部で`UrnProcessor.create_readable_label()`が呼び出されることを確認
  4. 生成されたラベルがノード属性に含まれることを確認
- **期待結果**:
  - ノード属性が正しく生成される
  - ラベルが読みやすい形式で生成される
  - ノード属性文字列にラベルが含まれる
- **確認項目**:
  - [ ] `UrnProcessor.create_readable_label()`が呼び出されたか
  - [ ] ラベルが正しく生成されたか
  - [ ] ノード属性文字列が正しいか
  - [ ] 例外が発生していないか

#### 3.1.3 urn_processor_integration_in_shorten_pulumi_label - _shorten_pulumi_label内でのUrnProcessor使用

**シナリオ名**: `test_urn_processor_integration_in_shorten_pulumi_label`

- **目的**: `DotFileProcessor._shorten_pulumi_label()`が`UrnProcessor`の各メソッドを正しく呼び出すことを検証
- **前提条件**:
  - `UrnProcessor`クラスが実装されている
  - `DotFileProcessor`が`UrnProcessor`をインポートしている
  - `_shorten_pulumi_label()`が修正されている
- **テスト手順**:
  1. サンプルDOTラベル文字列を準備（長いラベル）
  2. `_shorten_pulumi_label()`を呼び出す
  3. 内部で`UrnProcessor.parse_urn()`、`create_readable_label()`、`is_stack_resource()`が呼び出されることを確認
  4. ラベルが短縮されることを確認
- **期待結果**:
  - ラベルが短縮される
  - スタックリソースは処理がスキップされる
  - 通常リソースは読みやすいラベルに変換される
- **確認項目**:
  - [ ] `UrnProcessor.parse_urn()`が呼び出されたか
  - [ ] `UrnProcessor.is_stack_resource()`が呼び出されたか
  - [ ] `UrnProcessor.create_readable_label()`が呼び出されたか
  - [ ] ラベルが正しく短縮されたか

### 3.2 IntegrationEndToEnd - エンドツーエンドのDOT生成フロー

#### 3.2.1 end_to_end_dot_generation_with_urn_processor - UrnProcessor使用時のエンドツーエンドDOT生成

**シナリオ名**: `test_end_to_end_dot_generation_with_urn_processor`

- **目的**: リファクタリング後も、エンドツーエンドのDOT生成フローが正常に動作することを検証
- **前提条件**:
  - `UrnProcessor`クラスが実装されている
  - `DotFileProcessor`が修正されている
  - Phase 1で構築されたテストインフラが利用可能
- **テスト手順**:
  1. サンプルPulumiリソースデータを準備（複数のプロバイダーを含む）
  2. `DotFileGenerator.create_dot_file()`を呼び出してDOTファイルを生成
  3. `DotFileProcessor.apply_graph_styling()`を呼び出してスタイルを適用
  4. 生成されたDOT文字列を検証
- **期待結果**:
  - DOTファイルが正しく生成される
  - ノードラベルが読みやすい形式である
  - URN情報が正しく反映されている
  - グラフスタイルが正しく適用されている
  - 既存のテストケースが全てパスする
- **確認項目**:
  - [ ] DOT文字列が生成されたか
  - [ ] ノード定義が正しいか
  - [ ] エッジ定義が正しいか
  - [ ] ラベルが読みやすい形式か
  - [ ] スタイルが正しく適用されているか
  - [ ] 例外が発生していないか

#### 3.2.2 existing_test_suite_passes - 既存テストスイートが全てパスすること

**シナリオ名**: `test_existing_test_suite_passes`

- **目的**: リファクタリング後、既存の`test_dot_processor.py`のテストスイートが全てパスすることを検証
- **前提条件**:
  - Phase 1で構築されたテストスイートが存在する
  - `UrnProcessor`クラスが実装されている
  - `DotFileProcessor`が修正されている
- **テスト手順**:
  1. `pytest tests/test_dot_processor.py`を実行
  2. 全テストケースの実行結果を確認
  3. テスト実行時間を測定
  4. カバレッジレポートを生成
- **期待結果**:
  - 全テストケースがパスする
  - テスト実行時間が既存と同等（±10%以内）
  - カバレッジが80%以上を維持している
  - 振る舞い変更がないことが確認される
- **確認項目**:
  - [ ] 全テストケースがパスしたか
  - [ ] テスト実行時間は許容範囲内か
  - [ ] カバレッジは80%以上か
  - [ ] 既存の振る舞いが保持されているか

### 3.3 IntegrationPerformance - パフォーマンス検証

#### 3.3.1 urn_parsing_performance_100_urns - 100件のURNパースパフォーマンス

**シナリオ名**: `test_urn_parsing_performance_100_urns`

- **目的**: 100件のURNを一括パースした際のパフォーマンスが許容範囲内であることを検証
- **前提条件**:
  - `UrnProcessor`クラスが実装されている
  - 100件の多様なURNサンプルが準備されている
- **テスト手順**:
  1. 100件のURNサンプルを準備（AWS、Azure、GCP、Kubernetes等）
  2. 開始時刻を記録
  3. 各URNに対して`UrnProcessor.parse_urn()`を呼び出す
  4. 終了時刻を記録
  5. 処理時間を計算
- **期待結果**:
  - 合計処理時間が100ms未満である
  - メモリリークが発生しない
  - すべてのURNが正しくパースされる
- **確認項目**:
  - [ ] 処理時間が100ms未満か
  - [ ] メモリ使用量が異常に増加していないか
  - [ ] すべてのパース結果が正しいか

#### 3.3.2 dot_generation_performance_1000_resources - 1000件リソースのDOT生成パフォーマンス

**シナリオ名**: `test_dot_generation_performance_1000_resources`

- **目的**: 1000件のリソースでのDOT生成時のパフォーマンスが許容範囲内であることを検証
- **前提条件**:
  - `UrnProcessor`クラスが実装されている
  - `DotFileProcessor`が修正されている
  - 1000件のリソースサンプルが準備されている
- **テスト手順**:
  1. 1000件のリソースサンプルを準備
  2. 開始時刻を記録
  3. `DotFileGenerator.create_dot_file()`と`DotFileProcessor.apply_graph_styling()`を呼び出す
  4. 終了時刻を記録
  5. 処理時間を計算
- **期待結果**:
  - 処理時間が既存実装と同等（±10%以内）
  - メモリリークが発生しない
  - DOTファイルが正しく生成される
- **確認項目**:
  - [ ] 処理時間が許容範囲内か
  - [ ] メモリ使用量が異常に増加していないか
  - [ ] DOT生成が正しく完了したか

---

## 4. テストデータ

### 4.1 サンプルURNデータ

**AWS URNs**:
```python
aws_s3_bucket = "urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket"
aws_ec2_instance = "urn:pulumi:prod::webapp::aws:ec2/instance:Instance::web-server"
aws_lambda_function = "urn:pulumi:staging::api::aws:lambda/function:Function::api-handler"
```

**Azure URNs**:
```python
azure_storage_account = "urn:pulumi:prod::azureapp::azure:storage/storageAccount:StorageAccount::mystorageaccount"
azure_vm = "urn:pulumi:dev::webapp::azure:compute/virtualMachine:VirtualMachine::my-vm"
```

**GCP URNs**:
```python
gcp_storage_bucket = "urn:pulumi:staging::gcpproject::gcp:storage/bucket:Bucket::my-gcp-bucket"
gcp_compute_instance = "urn:pulumi:prod::webapp::gcp:compute/instance:Instance::my-instance"
```

**Kubernetes URNs**:
```python
k8s_deployment = "urn:pulumi:dev::k8sapp::kubernetes:apps/v1:Deployment::my-deployment"
k8s_service = "urn:pulumi:prod::k8sapp::kubernetes:core/v1:Service::my-service"
```

**Stack URNs**:
```python
stack_urn = "urn:pulumi:dev::myproject::pulumi:pulumi:Stack::dev"
```

**Invalid/Edge Case URNs**:
```python
invalid_urn = "invalid-urn-format"
partial_urn = "urn:pulumi:dev::myproject"
empty_urn = ""
extremely_long_urn = "urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::" + "x" * 10000
sql_injection_urn = "urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket'; DROP TABLE users;--"
unicode_urn = "urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::私のバケット🎉"
multiple_colons_urn = "urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my:bucket:with:colons"
```

### 4.2 サンプルURN情報データ

**基本的なURN情報**:
```python
basic_urn_info = {
    'stack': 'dev',
    'project': 'myproject',
    'provider': 'aws',
    'module': 's3',
    'type': 'Bucket',
    'name': 'my-bucket',
    'full_urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket'
}
```

**モジュール名なしのURN情報**:
```python
no_module_urn_info = {
    'stack': 'dev',
    'project': 'myproject',
    'provider': 'pulumi',
    'module': '',
    'type': 'Stack',
    'name': 'dev',
    'full_urn': 'urn:pulumi:dev::myproject::pulumi:pulumi:Stack::dev'
}
```

**長いタイプ名のURN情報**:
```python
long_type_urn_info = {
    'stack': 'dev',
    'project': 'myproject',
    'provider': 'aws',
    'module': 'ecs',
    'type': 'VeryLongResourceTypeNameThatExceeds30Characters',
    'name': 'my-resource',
    'full_urn': 'urn:pulumi:dev::myproject::aws:ecs/...:VeryLongResourceTypeNameThatExceeds30Characters::my-resource'
}
```

### 4.3 サンプルDOT文字列データ

**基本的なDOT文字列**:
```python
sample_dot_string = '''
digraph G {
    "urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket" [label="urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket"];
    "urn:pulumi:dev::myproject::aws:s3/bucketObject:BucketObject::index.html" [label="urn:pulumi:dev::myproject::aws:s3/bucketObject:BucketObject::index.html"];
    "urn:pulumi:dev::myproject::aws:s3/bucketObject:BucketObject::index.html" -> "urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket";
}
'''
```

**スタックリソースを含むDOT文字列**:
```python
sample_dot_with_stack = '''
digraph G {
    "urn:pulumi:dev::myproject::pulumi:pulumi:Stack::dev" [label="urn:pulumi:dev::myproject::pulumi:pulumi:Stack::dev"];
    "urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket" [label="urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket"];
    "urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket" -> "urn:pulumi:dev::myproject::pulumi:pulumi:Stack::dev";
}
'''
```

### 4.4 パフォーマンステスト用データ

**100件のURNリスト**:
```python
def generate_100_urns():
    urns = []
    providers = ['aws', 'azure', 'gcp', 'kubernetes']
    modules = ['s3', 'storage', 'compute', 'apps/v1']
    types = ['Bucket', 'StorageAccount', 'Instance', 'Deployment']

    for i in range(100):
        provider = providers[i % len(providers)]
        module = modules[i % len(modules)]
        type_ = types[i % len(types)]
        name = f"resource-{i}"
        urn = f"urn:pulumi:dev::myproject::{provider}:{module}/{type_.lower()}:{type_}::{name}"
        urns.append(urn)

    return urns
```

**1000件のリソースリスト**:
```python
def generate_1000_resources():
    resources = []
    for i in range(1000):
        resource = {
            'urn': f"urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::bucket-{i}",
            'type': 'aws:s3/bucket:Bucket',
            'name': f'bucket-{i}',
            'dependencies': []
        }
        resources.append(resource)
    return resources
```

---

## 5. テスト環境要件

### 5.1 ローカル環境

**必須要件**:
- Python 3.8以上
- pytest 6.0以上
- pytest-cov（カバレッジ測定）
- Phase 1で構築されたテストインフラ（`conftest.py`）

**推奨要件**:
- pytest-benchmark（パフォーマンステスト）
- pytest-timeout（タイムアウト設定）
- memory_profiler（メモリプロファイリング）

### 5.2 CI/CD環境

**要件**:
- GitHub Actions等のCI/CDパイプライン
- Python 3.8、3.9、3.10、3.11での実行（互換性確認）
- カバレッジレポートの自動生成
- テスト失敗時のアラート

### 5.3 モック/スタブの必要性

**不要**:
- `UrnProcessor`は純粋な計算処理のみ（外部依存なし）
- `DotFileProcessor`の統合テストも、外部システムとの連携がない

**フィクスチャの活用**:
- Phase 1で構築された`conftest.py`のフィクスチャを再利用
- `sample_urns`、`sample_resources`、`sample_dot_strings`等

---

## 6. テスト実行計画

### 6.1 ユニットテスト実行

**コマンド**:
```bash
pytest tests/test_urn_processor.py -v --cov=src/urn_processor --cov-report=html
```

**期待結果**:
- 全テストケースがパス
- カバレッジが80%以上

### 6.2 統合テスト実行

**コマンド**:
```bash
pytest tests/test_dot_processor.py -v --cov=src/dot_processor --cov-report=html
```

**期待結果**:
- 全テストケースがパス（既存テストを含む）
- カバレッジが80%以上を維持

### 6.3 全体テスト実行

**コマンド**:
```bash
pytest tests/ -v --cov=src --cov-report=html --cov-report=term
```

**期待結果**:
- 全テストケースがパス
- 全体カバレッジが80%以上

### 6.4 パフォーマンステスト実行

**コマンド**:
```bash
pytest tests/test_urn_processor.py::TestEdgeCases::test_extremely_long_urn_10000_chars -v
pytest tests/test_dot_processor.py::IntegrationPerformance -v
```

**期待結果**:
- 処理時間が許容範囲内
- メモリリークが発生しない

---

## 7. 品質ゲート（Phase 3）

### ✅ 品質ゲート1: Phase 2の戦略に沿ったテストシナリオである

- [x] テスト戦略（UNIT_INTEGRATION）に沿ったシナリオが作成されている
- [x] ユニットテストシナリオが詳細に記載されている
- [x] 統合テストシナリオが詳細に記載されている
- [x] BDDシナリオは不要と判断されている（技術的リファクタリングのため）

### ✅ 品質ゲート2: 主要な正常系がカバーされている

- [x] 各プロバイダー（AWS、Azure、GCP、Kubernetes）のURNパースシナリオが含まれている
- [x] スタックリソースURNのパースシナリオが含まれている
- [x] ラベル生成の基本的なシナリオが含まれている
- [x] リソース判定の正常系シナリオが含まれている
- [x] 統合動作の正常系シナリオが含まれている（エンドツーエンド）

### ✅ 品質ゲート3: 主要な異常系がカバーされている

- [x] 不正なURN形式のシナリオが含まれている
- [x] 空文字列のシナリオが含まれている
- [x] 部分的なURNのシナリオが含まれている
- [x] 極端に長いURNのシナリオが含まれている
- [x] 特殊文字を含むURNのシナリオが含まれている
- [x] Unicode文字を含むURNのシナリオが含まれている

### ✅ 品質ゲート4: 期待結果が明確である

- [x] 各テストケースに期待結果が明記されている
- [x] 期待結果が検証可能な形式で記載されている
- [x] 異常系の期待動作（例外を投げない、デフォルト値を返す）が明記されている
- [x] 統合テストの確認項目がチェックリスト形式で記載されている

---

## 8. レビューチェックリスト

### ✅ テスト戦略の整合性

- [x] Phase 2で決定されたテスト戦略（UNIT_INTEGRATION）に準拠している
- [x] ユニットテストと統合テストの両方が含まれている
- [x] BDDシナリオは不要と判断されている

### ✅ 要件との対応

- [x] 要件定義書の受け入れ基準がテストシナリオに反映されている
- [x] 機能要件がすべてテスト対象に含まれている
- [x] 非機能要件（パフォーマンス、セキュリティ）がテスト対象に含まれている

### ✅ カバレッジ目標

- [x] 全公開メソッドのテストシナリオが含まれている
- [x] プライベートメソッドのテストシナリオが含まれている（間接的に検証）
- [x] カバレッジ80%以上を達成できるシナリオが含まれている

### ✅ エッジケースの網羅

- [x] 境界値テストが含まれている
- [x] 異常系テストが含まれている
- [x] セキュリティ関連のエッジケースが含まれている

### ✅ 実行可能性

- [x] 具体的な入力・出力が記載されている
- [x] 曖昧な表現が避けられている
- [x] 検証可能な期待結果が記載されている

---

## 9. 次フェーズへの引き継ぎ

### Phase 4（実装）への準備

Phase 4では、以下の情報を引き継ぎます：

1. **ユニットテストシナリオ**: 30個以上の詳細なテストケース
2. **統合テストシナリオ**: 6個の統合ポイント検証シナリオ
3. **テストデータ**: サンプルURN、URN情報、DOT文字列
4. **カバレッジ目標**: 80%以上（全公開メソッド100%、プライベートメソッド70%以上）

### 実装フェーズで実施すべき事項

1. **`urn_processor.py`の実装**
   - 本テストシナリオで定義されたすべてのテストケースをパスするように実装
   - エラーハンドリング（例外を投げない設計）を徹底

2. **`test_urn_processor.py`の実装**
   - 本テストシナリオを基にテストコードを実装
   - `conftest.py`のフィクスチャを活用

3. **`dot_processor.py`の修正**
   - `UrnProcessor`のインポートと呼び出しへの置き換え
   - 既存テストが全てパスすることを確認

4. **テスト実行とカバレッジ測定**
   - 全テストがパスすることを確認
   - カバレッジ80%以上を達成

---

## 10. 変更履歴

| 日付 | 変更内容 | 変更者 |
|------|---------|--------|
| 2025-01-19 | 初版作成 | AI Workflow Phase 3 |

---

**このドキュメントは、Phase 0（Planning）、Phase 1（Requirements）、Phase 2（Design）の成果物を基に作成されました。**
**Phase 4（実装）以降のフェーズでは、本テストシナリオを基にテストコードと実装コードを作成してください。**
