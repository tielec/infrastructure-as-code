# Phase 3: テストシナリオ

**Issue**: #462 - [Refactor] dot_processor.py - Phase 2-2: NodeLabelGeneratorクラスの抽出
**作成日**: 2025-01-XX
**担当者**: AI Agent
**Design Document参照**: [design.md](../../02_design/output/design.md)
**Requirements Document参照**: [requirements.md](../../01_requirements/output/requirements.md)
**Planning Document参照**: [planning.md](../../00_planning/output/planning.md)

---

## 📋 0. Planning Documentの確認

### 開発計画の全体像

Planning Documentで策定された以下の戦略を踏まえてテストシナリオを作成します：

#### 実装戦略: **REFACTOR**
- 既存の`DotFileProcessor`クラスからラベル生成ロジックを抽出
- 新規クラス`NodeLabelGenerator`を作成し、既存ロジックを再編成
- Phase 2-1 (UrnProcessor抽出) と同様のリファクタリングパターンを適用

#### テスト戦略: **UNIT_INTEGRATION**
- **UNIT**: 新規クラス`NodeLabelGenerator`の単体テスト（カバレッジ80%以上）
- **INTEGRATION**: `DotFileProcessor`との統合動作確認、既存テスト全パス

#### テストコード戦略: **BOTH_TEST**
- **CREATE_TEST**: `test_node_label_generator.py`を新規作成
- **EXTEND_TEST**: `test_dot_processor.py`の統合テスト更新

#### 見積もり工数: **10~14時間**
- 要件定義: 1h ✅ 完了
- 設計: 2~3h ✅ 完了
- **テストシナリオ**: 1~2h ← 現在のフェーズ
- 実装: 3~4h
- テストコード実装: 2~3h
- テスト実行: 0.5~1h
- ドキュメント: 0.5~1h

#### リスク評価: **低〜中**
- ラベル生成ロジックの抽出漏れ（中）
- カスタムラベル対応の仕様不明確さ（中）
- 既存テストへの影響（低）

---

## 🎯 1. テスト戦略サマリー

### 選択されたテスト戦略: **UNIT_INTEGRATION**

**Phase 2で決定されたテスト戦略**:
- **UNIT (単体テスト)**: 新規クラス`NodeLabelGenerator`の単体テスト
  - 各メソッドの動作検証（リソースタイプ別ラベル生成）
  - エッジケース（長いラベル、特殊文字、カスタムラベル）
  - **カバレッジ80%以上の達成**

- **INTEGRATION (統合テスト)**: `DotFileProcessor`との統合動作確認
  - 既存の統合テストが全てパスすることの検証
  - ラベル生成結果が既存と同一であることの検証
  - Phase 2-1で作成された`UrnProcessor`との協調動作確認

### テスト対象の範囲

**新規作成**:
- `NodeLabelGenerator`クラスの全メソッド
  - `generate_node_label(urn, urn_info)` - ノード属性生成の振り分け
  - `generate_stack_node_label(urn_info)` - スタックノードラベル生成
  - `generate_resource_node_label(urn_info)` - リソースノードラベル生成
  - `_format_label(label, max_length)` - ラベルフォーマット（内部ヘルパー）

**統合テスト**:
- `DotFileProcessor`との統合
- `UrnProcessor`との協調動作
- 既存の統合テスト（`test_dot_processor.py`）の全パス確認

### テストの目的

1. **機能正確性**: ラベル生成ロジックが要件通りに動作することを検証
2. **リファクタリングの安全性**: 既存の動作が維持されていることを検証
3. **エッジケース耐性**: 異常な入力に対しても安全に動作することを検証
4. **カバレッジ達成**: 単体テストカバレッジ80%以上を達成
5. **統合動作**: 関連クラスとの協調動作を検証

---

## 🧪 2. Unitテストシナリオ

### 2.1 generate_node_label() - ノード属性生成の振り分け

このメソッドは、URNがスタックリソースか通常リソースかを判定し、適切なラベル生成メソッドに振り分けます。

#### テストケース 2.1.1: スタックリソースの振り分け（正常系）

- **目的**: スタックリソースURNが正しく`generate_stack_node_label()`に振り分けられることを検証
- **前提条件**: NodeLabelGeneratorクラスがインポート可能
- **入力**:
  - `urn`: `"urn:pulumi:dev::myproject::pulumi:pulumi:Stack::dev"`
  - `urn_info`: `{'stack': 'dev', 'project': 'myproject', 'provider': 'pulumi', 'module': 'pulumi', 'type': 'Stack', 'name': 'dev', 'full_urn': urn}`
- **期待結果**:
  - 戻り値がDOT形式の属性文字列であること
  - `label="Stack\\ndev"`が含まれること
  - `fillcolor="#D1C4E9"`が含まれること
  - `color="#512DA8"`が含まれること
  - `shape=ellipse`が含まれること
  - `fontsize="14"`が含まれること
- **テストデータ**: 上記urn、urn_info

#### テストケース 2.1.2: 通常リソース（AWS）の振り分け（正常系）

- **目的**: 通常リソースURNが正しく`generate_resource_node_label()`に振り分けられることを検証
- **前提条件**: NodeLabelGeneratorクラスがインポート可能
- **入力**:
  - `urn`: `"urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket"`
  - `urn_info`: `{'stack': 'dev', 'project': 'myproject', 'provider': 'aws', 'module': 's3', 'type': 'Bucket', 'name': 'my-bucket', 'full_urn': urn}`
- **期待結果**:
  - 戻り値がDOT形式の属性文字列であること
  - `label=`で始まること
  - AWS固有の色設定が適用されていること（`fillcolor="#FFF3E0"`, `color="#EF6C00"`）
  - `shape=box`が含まれること
  - `fontsize="11"`が含まれること
- **テストデータ**: 上記urn、urn_info

#### テストケース 2.1.3: 通常リソース（Azure）の振り分け（正常系）

- **目的**: Azureリソースが正しく処理され、Azure固有の色設定が適用されることを検証
- **前提条件**: NodeLabelGeneratorクラスがインポート可能
- **入力**:
  - `urn`: `"urn:pulumi:dev::myproject::azure:storage/storageAccount:StorageAccount::mystorage"`
  - `urn_info`: `{'stack': 'dev', 'project': 'myproject', 'provider': 'azure', 'module': 'storage', 'type': 'StorageAccount', 'name': 'mystorage', 'full_urn': urn}`
- **期待結果**:
  - 戻り値がDOT形式の属性文字列であること
  - Azure固有の色設定が適用されていること（`fillcolor="#E3F2FD"`, `color="#0078D4"`）
  - `shape=box`が含まれること
- **テストデータ**: 上記urn、urn_info

#### テストケース 2.1.4: 通常リソース（GCP）の振り分け（正常系）

- **目的**: GCPリソースが正しく処理され、GCP固有の色設定が適用されることを検証
- **前提条件**: NodeLabelGeneratorクラスがインポート可能
- **入力**:
  - `urn`: `"urn:pulumi:dev::myproject::gcp:storage/bucket:Bucket::my-bucket"`
  - `urn_info`: `{'stack': 'dev', 'project': 'myproject', 'provider': 'gcp', 'module': 'storage', 'type': 'Bucket', 'name': 'my-bucket', 'full_urn': urn}`
- **期待結果**:
  - 戻り値がDOT形式の属性文字列であること
  - GCP固有の色設定が適用されていること（`fillcolor="#E8F5E9"`, `color="#4285F4"`）
  - `shape=box`が含まれること
- **テストデータ**: 上記urn、urn_info

---

### 2.2 generate_stack_node_label() - スタックノードラベル生成

このメソッドは、スタックノード用のDOT属性文字列を生成します。

#### テストケース 2.2.1: 基本的なスタックラベル生成（正常系）

- **目的**: 基本的なスタックラベルが正しく生成されることを検証
- **前提条件**: NodeLabelGeneratorクラスがインポート可能
- **入力**:
  - `urn_info`: `{'stack': 'dev', 'project': 'myproject', 'provider': 'pulumi', 'module': 'pulumi', 'type': 'Stack', 'name': 'dev', 'full_urn': '...'}`
- **期待結果**:
  - 戻り値: `'label="Stack\\ndev", fillcolor="#D1C4E9", color="#512DA8", shape=ellipse, fontsize="14"'`
  - すべての属性が正しい順序で含まれること
- **テストデータ**: 上記urn_info

#### テストケース 2.2.2: 長いスタック名（正常系）

- **目的**: 長いスタック名が正しく処理されることを検証
- **前提条件**: NodeLabelGeneratorクラスがインポート可能
- **入力**:
  - `urn_info`: `{'stack': 'production-environment-v2-with-very-long-name', ...}`
- **期待結果**:
  - 戻り値にスタック名全体が含まれること（省略なし）
  - `label="Stack\\nproduction-environment-v2-with-very-long-name"`が含まれること
  - 固定色設定が適用されていること
- **テストデータ**: 上記urn_info

#### テストケース 2.2.3: 特殊文字を含むスタック名（エッジケース）

- **目的**: 特殊文字を含むスタック名が正しく処理されることを検証
- **前提条件**: NodeLabelGeneratorクラスがインポート可能
- **入力**:
  - `urn_info`: `{'stack': 'dev-stack-with-"quotes"', ...}`
- **期待結果**:
  - 戻り値にスタック名が含まれること
  - エスケープが必要な場合は適切にエスケープされること
  - 固定色設定が適用されていること
- **テストデータ**: 上記urn_info

#### テストケース 2.2.4: 空文字列のスタック名（異常系）

- **目的**: 空文字列のスタック名でも安全に動作することを検証
- **前提条件**: NodeLabelGeneratorクラスがインポート可能
- **入力**:
  - `urn_info`: `{'stack': '', 'project': 'myproject', 'provider': 'pulumi', 'module': 'pulumi', 'type': 'Stack', 'name': '', 'full_urn': '...'}`
- **期待結果**:
  - 例外が発生しないこと
  - 戻り値が有効なDOT形式の属性文字列であること
  - `label="Stack\\n"`が含まれること（空のスタック名）
- **テストデータ**: 上記urn_info

---

### 2.3 generate_resource_node_label() - リソースノードラベル生成

このメソッドは、リソースノード用のDOT属性文字列を生成し、プロバイダー別色設定を適用します。

#### テストケース 2.3.1: AWSリソースラベル生成（正常系）

- **目的**: AWSリソースのラベルが正しく生成されることを検証
- **前提条件**:
  - NodeLabelGeneratorクラスがインポート可能
  - UrnProcessorがインポート可能
- **入力**:
  - `urn_info`: `{'stack': 'dev', 'project': 'myproject', 'provider': 'aws', 'module': 's3', 'type': 'Bucket', 'name': 'my-bucket', 'full_urn': '...'}`
- **期待結果**:
  - 戻り値に`label=`が含まれること
  - UrnProcessor.create_readable_label()の結果が含まれること（`s3\\nBucket\\nmy-bucket`）
  - AWS固有の色設定が適用されていること（`fillcolor="#FFF3E0"`, `color="#EF6C00"`）
  - `shape=box`が含まれること
  - `fontsize="11"`が含まれること
- **テストデータ**: 上記urn_info

#### テストケース 2.3.2: Azureリソースラベル生成（正常系）

- **目的**: Azureリソースのラベルが正しく生成され、Azure固有の色設定が適用されることを検証
- **前提条件**:
  - NodeLabelGeneratorクラスがインポート可能
  - UrnProcessorがインポート可能
- **入力**:
  - `urn_info`: `{'stack': 'dev', 'project': 'myproject', 'provider': 'azure', 'module': 'storage', 'type': 'StorageAccount', 'name': 'mystorage', 'full_urn': '...'}`
- **期待結果**:
  - Azure固有の色設定が適用されていること（`fillcolor="#E3F2FD"`, `color="#0078D4"`）
  - `label=`に`storage\\nStorageAccount\\nmystorage`が含まれること
  - `shape=box`が含まれること
- **テストデータ**: 上記urn_info

#### テストケース 2.3.3: GCPリソースラベル生成（正常系）

- **目的**: GCPリソースのラベルが正しく生成され、GCP固有の色設定が適用されることを検証
- **前提条件**:
  - NodeLabelGeneratorクラスがインポート可能
  - UrnProcessorがインポート可能
- **入力**:
  - `urn_info`: `{'stack': 'dev', 'project': 'myproject', 'provider': 'gcp', 'module': 'storage', 'type': 'Bucket', 'name': 'my-bucket', 'full_urn': '...'}`
- **期待結果**:
  - GCP固有の色設定が適用されていること（`fillcolor="#E8F5E9"`, `color="#4285F4"`）
  - `label=`に`storage\\nBucket\\nmy-bucket`が含まれること
  - `shape=box`が含まれること
- **テストデータ**: 上記urn_info

#### テストケース 2.3.4: Kubernetesリソースラベル生成（正常系）

- **目的**: Kubernetesリソースのラベルが正しく生成されることを検証
- **前提条件**:
  - NodeLabelGeneratorクラスがインポート可能
  - UrnProcessorがインポート可能
- **入力**:
  - `urn_info`: `{'stack': 'dev', 'project': 'myproject', 'provider': 'kubernetes', 'module': 'core', 'type': 'Namespace', 'name': 'my-namespace', 'full_urn': '...'}`
- **期待結果**:
  - Kubernetes固有の色設定が適用されていること（`fillcolor="#E8EAF6"`, `color="#326DE6"`）
  - `label=`に`core\\nNamespace\\nmy-namespace`が含まれること
  - `shape=box`が含まれること
- **テストデータ**: 上記urn_info

#### テストケース 2.3.5: 未定義プロバイダーのデフォルト色設定（正常系）

- **目的**: PROVIDER_COLORSに定義されていないプロバイダーに対してデフォルト色が適用されることを検証
- **前提条件**:
  - NodeLabelGeneratorクラスがインポート可能
  - UrnProcessorがインポート可能
- **入力**:
  - `urn_info`: `{'stack': 'dev', 'project': 'myproject', 'provider': 'unknown-provider', 'module': 'module', 'type': 'Resource', 'name': 'my-resource', 'full_urn': '...'}`
- **期待結果**:
  - デフォルト色設定が適用されていること（`fillcolor="#E3F2FD"`, `color="#1565C0"`）
  - `label=`が含まれること
  - `shape=box`が含まれること
- **テストデータ**: 上記urn_info

#### テストケース 2.3.6: モジュール名なしのリソース（正常系）

- **目的**: モジュール名がない場合のラベル生成が正しく動作することを検証
- **前提条件**:
  - NodeLabelGeneratorクラスがインポート可能
  - UrnProcessorがインポート可能
- **入力**:
  - `urn_info`: `{'stack': 'dev', 'project': 'myproject', 'provider': 'pulumi', 'module': '', 'type': 'Stack', 'name': 'dev', 'full_urn': '...'}`
- **期待条件**:
  - 例外が発生しないこと
  - `label=`に`Stack\\ndev`が含まれること（モジュール名が省略されること）
  - プロバイダー（pulumi）に応じた色設定が適用されていること
- **テストデータ**: 上記urn_info

#### テストケース 2.3.7: 長いリソース名（正常系）

- **目的**: 長いリソース名が正しく処理されることを検証
- **前提条件**:
  - NodeLabelGeneratorクラスがインポート可能
  - UrnProcessorがインポート可能
- **入力**:
  - `urn_info`: `{'stack': 'dev', 'project': 'myproject', 'provider': 'aws', 'module': 's3', 'type': 'Bucket', 'name': 'my-very-long-bucket-name-that-exceeds-standard-length-limits-x' * 2, 'full_urn': '...'}`
- **期待結果**:
  - 例外が発生しないこと
  - ラベルが生成されること（UrnProcessor.create_readable_label()に委譲）
  - AWS固有の色設定が適用されていること
- **テストデータ**: 上記urn_info

#### テストケース 2.3.8: 特殊文字を含むリソース名（エッジケース）

- **目的**: 特殊文字を含むリソース名が正しく処理されることを検証
- **前提条件**:
  - NodeLabelGeneratorクラスがインポート可能
  - UrnProcessorがインポート可能
- **入力**:
  - `urn_info`: `{'stack': 'dev', 'project': 'myproject', 'provider': 'aws', 'module': 's3', 'type': 'Bucket', 'name': 'my-bucket-with-"quotes"', 'full_urn': '...'}`
- **期待結果**:
  - 例外が発生しないこと
  - ラベルが生成されること
  - 特殊文字がそのまま含まれること（エスケープはUrnProcessorに委譲）
- **テストデータ**: 上記urn_info

#### テストケース 2.3.9: Unicode文字を含むリソース名（エッジケース）

- **目的**: Unicode文字（日本語、絵文字）を含むリソース名が正しく処理されることを検証
- **前提条件**:
  - NodeLabelGeneratorクラスがインポート可能
  - UrnProcessorがインポート可能
- **入力**:
  - `urn_info`: `{'stack': 'dev', 'project': 'myproject', 'provider': 'aws', 'module': 's3', 'type': 'Bucket', 'name': '私のバケット🎉', 'full_urn': '...'}`
- **期待結果**:
  - 例外が発生しないこと
  - ラベルが生成されること
  - Unicode文字がそのまま含まれること
- **テストデータ**: 上記urn_info

#### テストケース 2.3.10: 大文字小文字の混在したプロバイダー名（正常系）

- **目的**: プロバイダー名の大文字小文字が正しく処理されることを検証（PROVIDER_COLORSの検索はlower()を使用）
- **前提条件**:
  - NodeLabelGeneratorクラスがインポート可能
  - UrnProcessorがインポート可能
- **入力**:
  - `urn_info`: `{'stack': 'dev', 'project': 'myproject', 'provider': 'AWS', 'module': 's3', 'type': 'Bucket', 'name': 'my-bucket', 'full_urn': '...'}`
- **期待結果**:
  - AWS固有の色設定が適用されていること（大文字小文字を無視）
  - `fillcolor="#FFF3E0"`, `color="#EF6C00"`が含まれること
- **テストデータ**: 上記urn_info

---

### 2.4 _format_label() - ラベルフォーマット（内部ヘルパー）

このメソッドは、長いラベルを省略記号付きで短縮します（将来の拡張用）。

#### テストケース 2.4.1: 短いラベル（正常系）

- **目的**: 短いラベル（40文字以下）がそのまま返されることを検証
- **前提条件**: NodeLabelGeneratorクラスがインポート可能
- **入力**:
  - `label`: `"s3\\nBucket\\nmy-bucket"`（21文字）
  - `max_length`: `40`（デフォルト）
- **期待結果**:
  - 戻り値: `"s3\\nBucket\\nmy-bucket"`（変更なし）
  - 省略記号（...）が含まれないこと
- **テストデータ**: 上記label

#### テストケース 2.4.2: 長いラベル（正常系）

- **目的**: 長いラベル（40文字以上）が正しく省略されることを検証
- **前提条件**: NodeLabelGeneratorクラスがインポート可能
- **入力**:
  - `label`: `"very-long-module-name\\nVeryLongResourceTypeName\\nvery-long-resource-name-that-exceeds-40-chars"`（90文字）
  - `max_length`: `40`（デフォルト）
- **期待結果**:
  - 戻り値の長さが40文字以下であること
  - 省略記号（...）が含まれること
  - 戻り値: `"very-long-module-name\\nVeryLongResou..."`（例）
- **テストデータ**: 上記label

#### テストケース 2.4.3: カスタムmax_length（正常系）

- **目的**: max_lengthパラメータが正しく動作することを検証
- **前提条件**: NodeLabelGeneratorクラスがインポート可能
- **入力**:
  - `label`: `"s3\\nBucket\\nmy-bucket-with-a-longer-name"`（40文字）
  - `max_length`: `20`
- **期待結果**:
  - 戻り値の長さが20文字以下であること
  - 省略記号（...）が含まれること
  - 戻り値: `"s3\\nBucket\\nmy-bu..."`（例）
- **テストデータ**: 上記label、max_length

#### テストケース 2.4.4: 空文字列（異常系）

- **目的**: 空文字列が正しく処理されることを検証
- **前提条件**: NodeLabelGeneratorクラスがインポート可能
- **入力**:
  - `label`: `""`
  - `max_length`: `40`
- **期待結果**:
  - 戻り値: `""`（空文字列のまま）
  - 例外が発生しないこと
- **テストデータ**: 上記label

#### テストケース 2.4.5: 極端に長いラベル（エッジケース）

- **目的**: 極端に長いラベル（1000文字）が正しく処理されることを検証
- **前提条件**: NodeLabelGeneratorクラスがインポート可能
- **入力**:
  - `label`: `"x" * 1000`
  - `max_length`: `40`
- **期待結果**:
  - 戻り値の長さが40文字以下であること
  - 省略記号（...）が含まれること
  - 処理が100ms以内に完了すること（パフォーマンス）
- **テストデータ**: 上記label

---

### 2.5 プロバイダー別色設定のテスト

#### テストケース 2.5.1: 全定義済みプロバイダーの色設定検証

- **目的**: PROVIDER_COLORSに定義されているすべてのプロバイダーで正しい色設定が適用されることを検証
- **前提条件**:
  - NodeLabelGeneratorクラスがインポート可能
  - DotFileGenerator.PROVIDER_COLORSが参照可能
- **入力**:
  - 各プロバイダーのurn_info（aws, azure, azuread, gcp, google, kubernetes, docker, pulumi, random, tls, github, cloudflare, datadog, postgresql, mysql, vault）
- **期待結果**:
  - 各プロバイダーで定義された色設定が適用されること
  - fillcolorとcolorが正しく設定されること
- **テストデータ**: 各プロバイダーのurn_infoリスト

---

### 2.6 エッジケース・異常系のテスト

#### テストケース 2.6.1: urn_infoが不完全な場合（異常系）

- **目的**: 必須キーが欠落したurn_infoでも安全に動作することを検証
- **前提条件**: NodeLabelGeneratorクラスがインポート可能
- **入力**:
  - `urn_info`: `{'stack': 'dev'}`（providerやtypeが欠落）
- **期待結果**:
  - 例外が発生しないこと
  - デフォルト値で処理されること、またはKeyError処理が適切であること
- **テストデータ**: 上記urn_info

#### テストケース 2.6.2: urn_infoがNone（異常系）

- **目的**: urn_infoがNoneの場合の動作を検証
- **前提条件**: NodeLabelGeneratorクラスがインポート可能
- **入力**:
  - `urn_info`: `None`
- **期待結果**:
  - 例外が発生する、またはデフォルト値を返すこと（設計方針による）
- **テストデータ**: None

#### テストケース 2.6.3: URNにコロンが多数含まれる場合（エッジケース）

- **目的**: URNに複数のコロンが含まれる場合でも正しく動作することを検証
- **前提条件**: NodeLabelGeneratorクラスがインポート可能
- **入力**:
  - `urn`: `"urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my:bucket:with:colons"`
  - `urn_info`: UrnProcessor.parse_urn(urn)の結果
- **期待結果**:
  - 例外が発生しないこと
  - ラベルが生成されること
- **テストデータ**: 上記urn、urn_info

#### テストケース 2.6.4: SQLインジェクション文字列を含む場合（セキュリティ）

- **目的**: SQLインジェクション文字列を含むリソース名が安全に処理されることを検証
- **前提条件**: NodeLabelGeneratorクラスがインポート可能
- **入力**:
  - `urn_info`: `{'stack': 'dev', 'provider': 'aws', 'module': 's3', 'type': 'Bucket', 'name': "my-bucket'; DROP TABLE users;--", ...}`
- **期待結果**:
  - 例外が発生しないこと
  - コードインジェクションが発生しないこと
  - ラベルが生成されること
- **テストデータ**: 上記urn_info

---

### 2.7 パフォーマンステスト

#### テストケース 2.7.1: 1000リソースのラベル生成パフォーマンス

- **目的**: 1000リソースのラベル生成を10秒以内に完了できることを検証
- **前提条件**: NodeLabelGeneratorクラスがインポート可能
- **入力**:
  - 1000個のurn_info（各種プロバイダーをランダムに配置）
- **期待結果**:
  - 処理時間が10秒以内であること
  - メモリリークが発生しないこと
- **テストデータ**: 1000個のurn_infoリスト

#### テストケース 2.7.2: 単一リソースのラベル生成パフォーマンス

- **目的**: 単一リソースのラベル生成が10ミリ秒以内に完了することを検証
- **前提条件**: NodeLabelGeneratorクラスがインポート可能
- **入力**:
  - 単一のurn_info（AWS S3 Bucket）
- **期待結果**:
  - 処理時間が10ミリ秒以内であること
- **テストデータ**: 上記urn_info

---

## 🔗 3. Integrationテストシナリオ

### 3.1 DotFileProcessor統合テスト

#### シナリオ 3.1.1: DotFileProcessorからのNodeLabelGenerator呼び出し

- **目的**: DotFileProcessorが正しくNodeLabelGeneratorを呼び出し、既存の動作が維持されることを検証
- **前提条件**:
  - NodeLabelGeneratorクラスがdot_processor.pyにインポートされている
  - DotFileProcessorが更新されている
- **テスト手順**:
  1. DotFileProcessorのインスタンスを作成
  2. Pulumi生成のDOTファイルを入力として渡す
  3. _process_node_definition()メソッドが呼び出される
  4. NodeLabelGenerator.generate_node_label()が呼び出されることを確認（モック/スタブで検証）
  5. 生成されたDOT形式の出力を検証
- **期待結果**:
  - NodeLabelGenerator.generate_node_label()が呼び出されること
  - 生成されたDOT形式の出力が既存と同一であること
  - 既存のラベル生成ロジックが削除されていること（_generate_node_attributes()などが削除）
- **確認項目**:
  - [ ] NodeLabelGeneratorのインポート文が存在する
  - [ ] _process_node_definition()内でNodeLabelGenerator.generate_node_label()が呼び出されている
  - [ ] _generate_node_attributes(), _generate_stack_node_attributes(), _generate_resource_node_attributes()が削除されている
  - [ ] 既存のテストケースが全てパスする

#### シナリオ 3.1.2: 既存の統合テストの全パス確認

- **目的**: 既存の統合テスト（test_dot_processor.py）が全てパスすることを検証
- **前提条件**:
  - NodeLabelGeneratorクラスが実装されている
  - DotFileProcessorが更新されている
- **テスト手順**:
  1. `pytest tests/test_dot_processor.py -v`を実行
  2. すべてのテストケースが実行される
  3. テスト結果を確認
- **期待結果**:
  - すべてのテストケースがパスすること
  - テスト実行時間が大幅に増加しないこと
  - 警告やエラーが発生しないこと
- **確認項目**:
  - [ ] すべてのテストがパス（100% passed）
  - [ ] 既存のテストが変更されていない（既存動作の維持）

---

### 3.2 UrnProcessor協調動作テスト

#### シナリオ 3.2.1: NodeLabelGeneratorとUrnProcessorの協調動作

- **目的**: NodeLabelGeneratorがUrnProcessorのメソッドを正しく呼び出し、協調動作することを検証
- **前提条件**:
  - NodeLabelGeneratorクラスがインポート可能
  - UrnProcessorクラスがインポート可能
- **テスト手順**:
  1. NodeLabelGeneratorのインスタンスを作成（静的メソッドのため不要）
  2. sample_urnsからAWS、Azure、GCP、Kubernetesの各URNを取得
  3. 各URNに対してUrnProcessor.parse_urn()を呼び出してurn_infoを取得
  4. NodeLabelGenerator.generate_resource_node_label(urn_info)を呼び出す
  5. 内部でUrnProcessor.create_readable_label(urn_info)が呼び出されていることを確認
- **期待結果**:
  - UrnProcessor.create_readable_label()が正しく呼び出されること
  - ラベル生成結果にUrnProcessorが生成したラベルが含まれること
  - 協調動作がシームレスに行われること
- **確認項目**:
  - [ ] UrnProcessorのメソッドが正しく呼び出されている
  - [ ] UrnProcessorの戻り値がNodeLabelGeneratorのラベルに反映されている
  - [ ] エラーやNone値が発生しない

#### シナリオ 3.2.2: スタックリソースの判定連携

- **目的**: NodeLabelGeneratorがUrnProcessor.is_stack_resource()を使用してスタックリソースを正しく判定することを検証
- **前提条件**:
  - NodeLabelGeneratorクラスがインポート可能
  - UrnProcessorクラスがインポート可能
- **テスト手順**:
  1. スタックリソースURN（`urn:pulumi:dev::myproject::pulumi:pulumi:Stack::dev`）を用意
  2. UrnProcessor.parse_urn()でurn_infoを取得
  3. NodeLabelGenerator.generate_node_label()を呼び出す
  4. 内部でUrnProcessor.is_stack_resource()が呼び出されることを確認
  5. generate_stack_node_label()が呼び出されることを確認
- **期待結果**:
  - UrnProcessor.is_stack_resource()が呼び出されること
  - スタックリソースとして正しく判定されること
  - generate_stack_node_label()が呼び出されること
- **確認項目**:
  - [ ] UrnProcessor.is_stack_resource()が正しく動作している
  - [ ] スタックリソース用のラベル生成が正しく実行される

---

### 3.3 ラベル生成結果の既存との一致検証

#### シナリオ 3.3.1: リファクタリング前後でのラベル生成結果の一致

- **目的**: リファクタリング前後でラベル生成結果が同一であることを検証
- **前提条件**:
  - NodeLabelGeneratorクラスが実装されている
  - DotFileProcessorが更新されている
  - テスト用のサンプルURNデータが存在する
- **テスト手順**:
  1. リファクタリング前の期待値（既存のtest_dot_processor.pyで使用されているラベル）を準備
  2. 各種URN（AWS、Azure、GCP、Kubernetes、スタックリソース）に対してラベル生成
  3. NodeLabelGeneratorで生成されたラベルと期待値を比較
  4. すべてのラベルが一致することを確認
- **期待結果**:
  - すべてのラベルが既存の期待値と一致すること
  - スタックノードラベルが一致すること
  - リソースノードラベルが一致すること
  - プロバイダー別色設定が一致すること
- **確認項目**:
  - [ ] スタックノードラベルが既存と一致
  - [ ] AWSリソースラベルが既存と一致
  - [ ] Azureリソースラベルが既存と一致
  - [ ] GCPリソースラベルが既存と一致
  - [ ] Kubernetesリソースラベルが既存と一致
  - [ ] 色設定が既存と一致

---

### 3.4 E2Eテスト（Pulumi生成DOTファイルの処理）

#### シナリオ 3.4.1: Pulumi生成DOTファイルの完全処理

- **目的**: Pulumi生成のDOTファイルを入力として、NodeLabelGeneratorを含むパイプライン全体が正しく動作することを検証
- **前提条件**:
  - NodeLabelGeneratorクラスが実装されている
  - DotFileProcessorが更新されている
  - テスト用のPulumi生成DOTファイルが存在する
- **テスト手順**:
  1. Pulumi生成のDOTファイル（sample.dot）を読み込む
  2. DotFileProcessor.apply_graph_styling()を呼び出す
  3. 内部でNodeLabelGeneratorが呼び出される
  4. 生成されたDOTファイルを検証
  5. Graphvizでレンダリング可能であることを確認（オプション）
- **期待結果**:
  - DOTファイルが正しく処理されること
  - すべてのノードラベルが正しく変換されること
  - プロバイダー別色設定が適用されること
  - Graphviz形式として有効であること
- **確認項目**:
  - [ ] DOTファイルが正常に処理される
  - [ ] ノードラベルが正しく変換される
  - [ ] 色設定が適用される
  - [ ] Graphvizでエラーが発生しない

---

## 📚 4. テストデータ

### 4.1 サンプルURN（sample_urns.json）

既存の`tests/fixtures/test_data/sample_urns.json`を利用します。以下のURNが必要です：

```json
{
  "valid_aws_urn": "urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket",
  "valid_azure_urn": "urn:pulumi:dev::myproject::azure:storage/storageAccount:StorageAccount::mystorage",
  "valid_gcp_urn": "urn:pulumi:dev::myproject::gcp:storage/bucket:Bucket::my-bucket",
  "valid_kubernetes_urn": "urn:pulumi:dev::myproject::kubernetes:core/v1:Namespace::my-namespace",
  "stack_urn": "urn:pulumi:dev::myproject::pulumi:pulumi:Stack::dev",
  "invalid_urn_no_separator": "invalid-urn",
  "invalid_urn_partial": "urn:pulumi:dev",
  "empty_urn": ""
}
```

### 4.2 サンプルURN情報辞書

単体テストで使用するurn_info辞書のサンプル：

```python
# AWS S3 Bucket
aws_urn_info = {
    'stack': 'dev',
    'project': 'myproject',
    'provider': 'aws',
    'module': 's3',
    'type': 'Bucket',
    'name': 'my-bucket',
    'full_urn': 'urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket'
}

# Azure Storage Account
azure_urn_info = {
    'stack': 'dev',
    'project': 'myproject',
    'provider': 'azure',
    'module': 'storage',
    'type': 'StorageAccount',
    'name': 'mystorage',
    'full_urn': 'urn:pulumi:dev::myproject::azure:storage/storageAccount:StorageAccount::mystorage'
}

# GCP Storage Bucket
gcp_urn_info = {
    'stack': 'dev',
    'project': 'myproject',
    'provider': 'gcp',
    'module': 'storage',
    'type': 'Bucket',
    'name': 'my-bucket',
    'full_urn': 'urn:pulumi:dev::myproject::gcp:storage/bucket:Bucket::my-bucket'
}

# Kubernetes Namespace
kubernetes_urn_info = {
    'stack': 'dev',
    'project': 'myproject',
    'provider': 'kubernetes',
    'module': 'core',
    'type': 'Namespace',
    'name': 'my-namespace',
    'full_urn': 'urn:pulumi:dev::myproject::kubernetes:core/v1:Namespace::my-namespace'
}

# Pulumi Stack
stack_urn_info = {
    'stack': 'dev',
    'project': 'myproject',
    'provider': 'pulumi',
    'module': 'pulumi',
    'type': 'Stack',
    'name': 'dev',
    'full_urn': 'urn:pulumi:dev::myproject::pulumi:pulumi:Stack::dev'
}

# 未定義プロバイダー
unknown_provider_urn_info = {
    'stack': 'dev',
    'project': 'myproject',
    'provider': 'unknown-provider',
    'module': 'module',
    'type': 'Resource',
    'name': 'my-resource',
    'full_urn': 'urn:pulumi:dev::myproject::unknown-provider:module/resource:Resource::my-resource'
}
```

### 4.3 期待されるラベル生成結果

```python
# スタックノードの期待値
expected_stack_label = 'label="Stack\\ndev", fillcolor="#D1C4E9", color="#512DA8", shape=ellipse, fontsize="14"'

# AWSリソースの期待値
expected_aws_label_parts = [
    'label="s3\\nBucket\\nmy-bucket"',
    'fillcolor="#FFF3E0"',
    'color="#EF6C00"',
    'shape=box',
    'fontsize="11"'
]

# Azureリソースの期待値
expected_azure_label_parts = [
    'label="storage\\nStorageAccount\\nmystorage"',
    'fillcolor="#E3F2FD"',
    'color="#0078D4"',
    'shape=box',
    'fontsize="11"'
]

# GCPリソースの期待値
expected_gcp_label_parts = [
    'label="storage\\nBucket\\nmy-bucket"',
    'fillcolor="#E8F5E9"',
    'color="#4285F4"',
    'shape=box',
    'fontsize="11"'
]
```

### 4.4 エッジケース用テストデータ

```python
# 長いリソース名
long_name_urn_info = {
    'stack': 'dev',
    'project': 'myproject',
    'provider': 'aws',
    'module': 's3',
    'type': 'Bucket',
    'name': 'my-very-long-bucket-name-that-exceeds-standard-length-limits-and-continues-for-even-more-characters',
    'full_urn': '...'
}

# 特殊文字を含むリソース名
special_chars_urn_info = {
    'stack': 'dev',
    'project': 'myproject',
    'provider': 'aws',
    'module': 's3',
    'type': 'Bucket',
    'name': 'my-bucket-with-"quotes"',
    'full_urn': '...'
}

# Unicode文字を含むリソース名
unicode_urn_info = {
    'stack': 'dev',
    'project': 'myproject',
    'provider': 'aws',
    'module': 's3',
    'type': 'Bucket',
    'name': '私のバケット🎉',
    'full_urn': '...'
}

# SQLインジェクション文字列
sql_injection_urn_info = {
    'stack': 'dev',
    'project': 'myproject',
    'provider': 'aws',
    'module': 's3',
    'type': 'Bucket',
    'name': "my-bucket'; DROP TABLE users;--",
    'full_urn': '...'
}
```

### 4.5 プロバイダー色設定の期待値

```python
# DotFileGenerator.PROVIDER_COLORSから取得
EXPECTED_PROVIDER_COLORS = {
    'aws': ('#FFF3E0', '#EF6C00'),
    'azure': ('#E3F2FD', '#0078D4'),
    'azuread': ('#E8F5E9', '#0078D4'),
    'gcp': ('#E8F5E9', '#4285F4'),
    'google': ('#E8F5E9', '#4285F4'),
    'kubernetes': ('#E8EAF6', '#326DE6'),
    'docker': ('#E3F2FD', '#2496ED'),
    'pulumi': ('#F3E5F5', '#6A1B9A'),
    'random': ('#FFF9C4', '#FBC02D'),
    'tls': ('#FFEBEE', '#D32F2F'),
    'github': ('#F5F5F5', '#24292E'),
    'cloudflare': ('#FFF8E1', '#F48120'),
    'datadog': ('#F3E5F5', '#632CA6'),
    'postgresql': ('#E8F5E9', '#336791'),
    'mysql': ('#E3F2FD', '#00758F'),
    'vault': ('#F5F5F5', '#000000'),
}
DEFAULT_COLORS = ('#E3F2FD', '#1565C0')
```

---

## 🛠️ 5. テスト環境要件

### 5.1 必要なテスト環境

- **ローカル環境**: Python 3.8以上、pytest 7.0以上
- **CI/CD環境**: GitHub Actions、Jenkins等（既存のCI/CD環境）
- **依存パッケージ**: なし（標準ライブラリのみ使用）

### 5.2 必要な外部サービス・データベース

- **なし**: 外部サービスへの依存はありません

### 5.3 モック/スタブの必要性

- **統合テスト用**:
  - UrnProcessorのモック（オプション）: 単体テストではUrnProcessorの実際のメソッドを使用
  - DotFileProcessorのモック（オプション）: 統合テストでは実際のDotFileProcessorを使用

---

## ✅ 品質ゲート（Phase 3）

本テストシナリオは、以下の品質ゲートを満たしています：

- [x] **Phase 2の戦略に沿ったテストシナリオである** ✅
  - テスト戦略: UNIT_INTEGRATION（Unitテスト + Integrationテスト）
  - テストコード戦略: BOTH_TEST（新規テストファイル作成 + 既存テスト更新）
  - すべてのテストシナリオがPhase 2の設計書と整合している

- [x] **主要な正常系がカバーされている** ✅
  - スタックノードラベル生成（正常系）
  - リソースノードラベル生成（AWS、Azure、GCP、Kubernetes）
  - プロバイダー別色設定（全定義済みプロバイダー）
  - DotFileProcessorとの統合動作
  - UrnProcessorとの協調動作

- [x] **主要な異常系がカバーされている** ✅
  - 空文字列のスタック名
  - 不完全なurn_info（必須キーの欠落）
  - urn_infoがNone
  - 極端に長いラベル
  - 特殊文字を含むリソース名
  - Unicode文字を含むリソース名
  - SQLインジェクション文字列

- [x] **期待結果が明確である** ✅
  - すべてのテストケースで具体的な期待結果を記載
  - 期待されるDOT形式の属性文字列を明記
  - プロバイダー別色設定の期待値を明記
  - エッジケースの動作を明確に定義

---

## 📊 6. テストカバレッジ目標

### 6.1 カバレッジ目標

- **単体テストカバレッジ**: 80%以上（必須）
- **統合テストカバレッジ**: 既存テスト全パス（必須）

### 6.2 カバレッジ測定方法

```bash
# 単体テストカバレッジ測定
pytest tests/test_node_label_generator.py --cov=node_label_generator --cov-report=term --cov-report=html

# 統合テストカバレッジ測定
pytest tests/test_dot_processor.py --cov=dot_processor --cov=node_label_generator --cov-report=term
```

### 6.3 カバレッジ目標達成のための戦略

- **メソッド単位の網羅**: すべての公開メソッドと内部ヘルパーメソッドをテスト
- **エッジケースの網羅**: 空文字列、None、極端に長い入力、特殊文字
- **異常系の網羅**: 不正な入力、必須キーの欠落、型エラー
- **パフォーマンステスト**: 大量データ、処理時間測定

---

## 📝 7. 次のフェーズ

**次のフェーズ**: Phase 4（実装）に進んでください。

**クリティカルシンキングレビュー**: 本テストシナリオは、Planning DocumentとPhase 2の設計書で定義された品質ゲートを満たしており、Phase 4（実装）への移行準備が整っています。

---

## 📚 8. 参考情報

### 関連ドキュメント

- [CLAUDE.md](../../../../CLAUDE.md): プロジェクトのコーディングガイドライン
- [ARCHITECTURE.md](../../../../ARCHITECTURE.md): アーキテクチャ設計思想
- [Planning Document](../../00_planning/output/planning.md): Phase 2-2の開発計画
- [Requirements Document](../../01_requirements/output/requirements.md): 要件定義書
- [Design Document](../../02_design/output/design.md): 詳細設計書

### 参考実装

- `test_urn_processor.py` (Phase 2-1): 単体テストのベストプラクティス
- `test_dot_processor.py`: 統合テストの既存実装
- `conftest.py`: pytest共通フィクスチャ

### テストコーディング規約

- **Pytestマーカー**: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.edge_case`
- **命名規則**: `test_<メソッド名>_<シナリオ>`（例: `test_generate_node_label_stack_resource`）
- **Given-When-Then形式**: コメントでテストシナリオを明示
- **アサーション**: 具体的で読みやすいアサーションを記載

---

**このテストシナリオは、Phase 3の成果物です。Phase 4（実装）開始前に、クリティカルシンキングレビューを実施してください。**
