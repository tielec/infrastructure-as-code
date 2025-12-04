# テストシナリオ: Issue #465

## メタデータ

- **Issue番号**: #465
- **タイトル**: [Refactor] dot_processor.py - Phase 4: レビューと最適化
- **親Issue**: #448
- **依存Issue**: #464 (Phase 3: 統合とネスト解消)
- **作成日**: 2025年10月17日
- **ステータス**: テストシナリオ作成完了
- **URL**: https://github.com/tielec/infrastructure-as-code/issues/465

---

## 1. テスト戦略サマリー

### 1.1 選択されたテスト戦略

**INTEGRATION_BDD** (Phase 2で決定)

### 1.2 テスト対象の範囲

Phase 4は、Phase 1~3のリファクタリング成果を検証・補強するフェーズです。以下の範囲をテスト対象とします：

#### テスト対象コンポーネント

1. **DotFileGenerator** (生成層)
   - DOTファイル生成のエントリーポイント
   - Pulumiリソースデータの処理

2. **DotFileProcessor** (処理層)
   - DOTファイルのスタイル適用
   - グラフの拡張処理

3. **UrnProcessor** (ユーティリティ層)
   - URN解析処理
   - Phase 1で分離

4. **NodeLabelGenerator** (ユーティリティ層)
   - ノードラベル生成
   - Phase 2で分離

5. **ResourceDependencyBuilder** (ユーティリティ層)
   - リソース依存関係構築
   - Phase 3で分離

#### 統合テストの焦点

- **4つのクラスの協調動作**: Phase 1~3で分離されたクラス間の連携
- **エンドツーエンドのデータフロー**: Pulumi生成データ → DOT出力までの一連の流れ
- **エラーハンドリング**: 不正データに対する適切な処理
- **境界値**: リソース数の境界での動作

### 1.3 テストの目的

Phase 4のテスト目的は以下の通りです：

1. **品質保証**: リファクタリング後のコードが正しく動作することを検証
2. **統合検証**: 分離されたクラスが協調して動作することを確認
3. **性能検証**: リファクタリング前後で性能劣化がないこと（±10%以内）を確認
4. **回帰防止**: 既存機能が維持されていることを確認

### 1.4 テスト種別と件数

| テスト種別 | テストケース数 | 説明 |
|-----------|---------------|------|
| **統合テスト - エンドツーエンド** | 5ケース | Pulumiデータ → DOT出力の正常系 |
| **統合テスト - エラーハンドリング** | 3ケース | 異常データ処理の検証 |
| **統合テスト - 境界値** | 3ケース | リソース数の境界値検証 |
| **パフォーマンステスト** | 5ケース | リファクタリング前後の性能比較 |
| **合計** | **16ケース** | Phase 4で追加する新規テスト |

**既存テスト**: 114ケース（Phase 1~3で作成済み）

**全体**: 130ケース（114 + 16）

---

## 2. 統合テストシナリオ

### 2.1 エンドツーエンド統合テスト（5ケース）

Phase 1~3で分離された4つのクラスの協調動作を検証します。

---

#### TC-E-01: 基本的なPulumiグラフ処理（AWS）

**Feature**: Pulumi生成データからDOTファイル生成

**Scenario**: 基本的なAWSリソースのグラフを正しく生成できる

**目的**:
- 最も基本的なエンドツーエンドのデータフローを検証
- DotFileGenerator → UrnProcessor → NodeLabelGenerator → ResourceDependencyBuilderの連携を確認

**Given** (前提条件):
- Pulumiで生成されたAWSリソースデータが存在する
- リソース数: 3個（S3バケット、Lambda関数、IAMロール）
- スタック名: "dev-stack"

**When** (操作):
- DotFileGenerator.create_dot_file()を呼び出す
- 生成されたDOT文字列にDotFileProcessor.apply_graph_styling()を適用する

**Then** (期待結果):
- DOTファイルが正しく生成される
- 以下のノードが含まれている:
  - スタックノード: "dev-stack"
  - プロバイダーノード: "aws"
  - リソースノード: 3個（S3、Lambda、IAM）
- AWSプロバイダーの色設定が適用されている（オレンジ系）
- リソース間の依存関係エッジが生成されている（Lambda → IAMロール）
- ノードラベルが省略記号なしで表示されている（短いリソース名）

**テストデータ**:
```python
stack_name = "dev-stack"
resources = [
    {
        "urn": "urn:pulumi:dev::myapp::aws:s3/bucket:Bucket::my-bucket",
        "type": "aws:s3/bucket:Bucket",
        "dependencies": []
    },
    {
        "urn": "urn:pulumi:dev::myapp::aws:iam/role:Role::lambda-role",
        "type": "aws:iam/role:Role",
        "dependencies": []
    },
    {
        "urn": "urn:pulumi:dev::myapp::aws:lambda/function:Function::my-function",
        "type": "aws:lambda/function:Function",
        "dependencies": ["urn:pulumi:dev::myapp::aws:iam/role:Role::lambda-role"]
    }
]
resource_providers = {"aws": 3}
```

**検証項目**:
- [ ] DOT文字列が`digraph`で始まる
- [ ] スタックノード`dev-stack`が存在する
- [ ] プロバイダーノード`aws`が存在する
- [ ] 3つのリソースノードが存在する
- [ ] Lambda → IAMロールのエッジが存在する
- [ ] AWSの色設定（fillcolor, color）が適用されている
- [ ] エスケープ処理が正しく適用されている（特殊文字なし）

---

#### TC-E-02: 複数プロバイダー（AWS + Azure）

**Feature**: マルチクラウドリソースのグラフ生成

**Scenario**: AWS and Azureの両方のリソースを含むグラフを正しく生成できる

**目的**:
- 複数プロバイダーの処理を検証
- プロバイダー別の色設定が正しく適用されることを確認

**Given** (前提条件):
- AWS and Azureのリソースが混在するPulumiデータが存在する
- リソース数: 5個（AWS: 3個、Azure: 2個）
- スタック名: "multi-cloud-stack"

**When** (操作):
- DotFileGenerator.create_dot_file()を呼び出す
- 生成されたDOT文字列にDotFileProcessor.apply_graph_styling()を適用する

**Then** (期待結果):
- DOTファイルが正しく生成される
- 以下のノードが含まれている:
  - スタックノード: "multi-cloud-stack"
  - プロバイダーノード: "aws" and "azure"
  - リソースノード: 5個（AWS: 3個、Azure: 2個）
- AWSリソースにはオレンジ系の色設定
- Azureリソースには青系の色設定
- スタック → 各プロバイダーのエッジが存在する
- プロバイダー → リソースのエッジが存在する

**テストデータ**:
```python
stack_name = "multi-cloud-stack"
resources = [
    # AWS Resources
    {
        "urn": "urn:pulumi:dev::app::aws:s3/bucket:Bucket::bucket1",
        "type": "aws:s3/bucket:Bucket",
        "dependencies": []
    },
    {
        "urn": "urn:pulumi:dev::app::aws:ec2/instance:Instance::instance1",
        "type": "aws:ec2/instance:Instance",
        "dependencies": []
    },
    {
        "urn": "urn:pulumi:dev::app::aws:rds/instance:Instance::db1",
        "type": "aws:rds/instance:Instance",
        "dependencies": []
    },
    # Azure Resources
    {
        "urn": "urn:pulumi:dev::app::azure:storage/account:Account::storage1",
        "type": "azure:storage/account:Account",
        "dependencies": []
    },
    {
        "urn": "urn:pulumi:dev::app::azure:compute/virtualMachine:VirtualMachine::vm1",
        "type": "azure:compute/virtualMachine:VirtualMachine",
        "dependencies": []
    }
]
resource_providers = {"aws": 3, "azure": 2}
```

**検証項目**:
- [ ] 2つのプロバイダーノード（aws, azure）が存在する
- [ ] AWSリソースにオレンジ系の色設定が適用されている
- [ ] Azureリソースに青系の色設定が適用されている
- [ ] スタック → aws、スタック → azureのエッジが存在する
- [ ] 各プロバイダー → リソースのエッジが存在する
- [ ] 5つのリソースノードがすべて存在する

---

#### TC-E-03: 複雑な依存関係

**Feature**: 複雑な依存関係を持つリソースのグラフ生成

**Scenario**: 多段階の依存関係（A→B→C）と複数依存（D→A, D→B）を正しく表現できる

**目的**:
- ResourceDependencyBuilderの依存関係構築ロジックを検証
- 複雑な依存関係グラフが正しく生成されることを確認

**Given** (前提条件):
- 複雑な依存関係を持つPulumiリソースデータが存在する
- リソース数: 5個
- 依存関係:
  - Lambda → IAMロール（単純依存）
  - API Gateway → Lambda（単純依存）
  - CloudWatch → Lambda（単純依存）
  - CloudWatch → API Gateway（複数依存）

**When** (操作):
- DotFileGenerator.create_dot_file()を呼び出す
- 生成されたDOT文字列にDotFileProcessor.apply_graph_styling()を適用する

**Then** (期待結果):
- DOTファイルが正しく生成される
- 以下の依存関係エッジが存在する:
  - Lambda → IAMロール
  - API Gateway → Lambda
  - CloudWatch → Lambda
  - CloudWatch → API Gateway
- エッジのスタイルが適用されている（directDependencies: 実線、propertyDependencies: 点線等）
- 循環依存がない（DAG構造）
- すべてのリソースが到達可能

**テストデータ**:
```python
stack_name = "complex-stack"
resources = [
    {
        "urn": "urn:pulumi:dev::app::aws:iam/role:Role::lambda-role",
        "type": "aws:iam/role:Role",
        "dependencies": []
    },
    {
        "urn": "urn:pulumi:dev::app::aws:lambda/function:Function::my-function",
        "type": "aws:lambda/function:Function",
        "dependencies": ["urn:pulumi:dev::app::aws:iam/role:Role::lambda-role"]
    },
    {
        "urn": "urn:pulumi:dev::app::aws:apigateway/restApi:RestApi::my-api",
        "type": "aws:apigateway/restApi:RestApi",
        "dependencies": ["urn:pulumi:dev::app::aws:lambda/function:Function::my-function"]
    },
    {
        "urn": "urn:pulumi:dev::app::aws:s3/bucket:Bucket::log-bucket",
        "type": "aws:s3/bucket:Bucket",
        "dependencies": []
    },
    {
        "urn": "urn:pulumi:dev::app::aws:cloudwatch/logGroup:LogGroup::logs",
        "type": "aws:cloudwatch/logGroup:LogGroup",
        "dependencies": [
            "urn:pulumi:dev::app::aws:lambda/function:Function::my-function",
            "urn:pulumi:dev::app::aws:apigateway/restApi:RestApi::my-api"
        ]
    }
]
resource_providers = {"aws": 5}
```

**検証項目**:
- [ ] 5つのリソースノードが存在する
- [ ] 5本の依存関係エッジが存在する（Lambda→IAM、API→Lambda、CloudWatch→Lambda、CloudWatch→API、独立したS3）
- [ ] エッジのスタイルが適用されている
- [ ] 循環依存がない
- [ ] 依存関係の方向が正しい（被依存リソース → 依存元リソース）

---

#### TC-E-04: 長いリソース名の処理

**Feature**: 長いリソース名の省略表示

**Scenario**: 長いリソース名が省略記号付きで処理される

**目的**:
- NodeLabelGeneratorの省略処理を検証
- 長いリソース名でもグラフが読みやすいことを確認

**Given** (前提条件):
- 非常に長いリソース名を含むPulumiデータが存在する
- リソース名の長さ: 100文字以上
- リソース数: 3個

**When** (操作):
- DotFileGenerator.create_dot_file()を呼び出す
- 生成されたDOT文字列にDotFileProcessor.apply_graph_styling()を適用する

**Then** (期待結果):
- DOTファイルが正しく生成される
- 長いリソース名が省略記号（...）付きで表示されている
- ノードラベルの最大長が制限されている（例: 50文字）
- 省略されても、リソースを識別できる情報が残っている
- エスケープ処理が正しく適用されている

**テストデータ**:
```python
stack_name = "long-name-stack"
resources = [
    {
        "urn": "urn:pulumi:dev::app::aws:s3/bucket:Bucket::this-is-a-very-long-bucket-name-that-exceeds-the-normal-length-limit-for-display-purposes-in-graph-visualization-tools-like-graphviz",
        "type": "aws:s3/bucket:Bucket",
        "dependencies": []
    },
    {
        "urn": "urn:pulumi:dev::app::aws:lambda/function:Function::another-extremely-long-lambda-function-name-that-should-be-truncated-to-ensure-readability-in-the-generated-dot-file",
        "type": "aws:lambda/function:Function",
        "dependencies": []
    },
    {
        "urn": "urn:pulumi:dev::app::aws:iam/role:Role::iam-role-with-a-moderately-long-name",
        "type": "aws:iam/role:Role",
        "dependencies": []
    }
]
resource_providers = {"aws": 3}
```

**検証項目**:
- [ ] 3つのリソースノードが存在する
- [ ] 長いリソース名が省略記号付きで表示されている
- [ ] ノードラベルが50文字程度に制限されている
- [ ] 省略されたラベルでもリソースタイプが識別可能
- [ ] DOT構文が正しい（エスケープ処理）

---

#### TC-E-05: 特殊文字を含むリソース名

**Feature**: 特殊文字のエスケープ処理

**Scenario**: DOT構文の特殊文字（`"`、`\`、改行等）を含むリソース名が正しくエスケープされる

**目的**:
- DotFileGenerator.escape_dot_string()の機能を検証
- 特殊文字を含むリソース名でもDOTファイルが正しく生成されることを確認

**Given** (前提条件):
- 特殊文字を含むリソース名のPulumiデータが存在する
- 特殊文字: `"`、`\`、改行（`\n`）、タブ（`\t`）
- リソース数: 4個

**When** (操作):
- DotFileGenerator.create_dot_file()を呼び出す
- 生成されたDOT文字列にDotFileProcessor.apply_graph_styling()を適用する

**Then** (期待結果):
- DOTファイルが正しく生成される
- 特殊文字がエスケープされている:
  - `"` → `\"`
  - `\` → `\\`
  - `\n` → `\\n`
  - `\t` → `\\t`
- DOT構文が有効である（Graphvizでパース可能）
- リソース名が正しく表示される

**テストデータ**:
```python
stack_name = "special-char-stack"
resources = [
    {
        "urn": 'urn:pulumi:dev::app::aws:s3/bucket:Bucket::bucket-with-"quotes"',
        "type": "aws:s3/bucket:Bucket",
        "dependencies": []
    },
    {
        "urn": "urn:pulumi:dev::app::aws:lambda/function:Function::function\\with\\backslash",
        "type": "aws:lambda/function:Function",
        "dependencies": []
    },
    {
        "urn": "urn:pulumi:dev::app::aws:iam/role:Role::role\nwith\nnewline",
        "type": "aws:iam/role:Role",
        "dependencies": []
    },
    {
        "urn": "urn:pulumi:dev::app::aws:rds/instance:Instance::db\twith\ttab",
        "type": "aws:rds/instance:Instance",
        "dependencies": []
    }
]
resource_providers = {"aws": 4}
```

**検証項目**:
- [ ] 4つのリソースノードが存在する
- [ ] `"`が`\"`にエスケープされている
- [ ] `\`が`\\`にエスケープされている
- [ ] `\n`が`\\n`にエスケープされている
- [ ] `\t`が`\\t`にエスケープされている
- [ ] 生成されたDOT文字列が有効なDOT構文である
- [ ] 特殊文字を含むリソース名が正しく表示される

---

### 2.2 エラーハンドリング統合テスト（3ケース）

異常データに対する適切なエラーハンドリングを検証します。

---

#### TC-EH-01: 不正なURN形式

**Feature**: 不正なURN形式の処理

**Scenario**: 不正なURN形式のリソースを含むデータを処理しても、エラーを投げずにデフォルト値で処理される

**目的**:
- UrnProcessor.parse_urn()のエラーハンドリングを検証
- 不正なURN形式でもシステムが停止しないことを確認

**Given** (前提条件):
- 不正なURN形式を含むPulumiデータが存在する
- 不正なURNの例:
  - "invalid-urn-format"（区切り文字`::`がない）
  - ""（空文字列）
  - "urn:pulumi"（不完全なURN）

**When** (操作):
- DotFileGenerator.create_dot_file()を呼び出す
- 不正なURNを含むリソースデータを渡す

**Then** (期待結果):
- エラーを投げない（例外が発生しない）
- DOTファイルが生成される
- 不正なURNはデフォルト値で処理される:
  - プロバイダー: "unknown"
  - リソースタイプ: "unknown"
  - リソース名: URN文字列そのまま
- 正常なURNのリソースは正しく処理される
- デフォルト色設定（グレー系）が適用される

**テストデータ**:
```python
stack_name = "invalid-urn-stack"
resources = [
    {
        "urn": "invalid-urn-format",
        "type": "unknown:type",
        "dependencies": []
    },
    {
        "urn": "",
        "type": "unknown:type",
        "dependencies": []
    },
    {
        "urn": "urn:pulumi",
        "type": "incomplete:type",
        "dependencies": []
    },
    {
        "urn": "urn:pulumi:dev::app::aws:s3/bucket:Bucket::valid-bucket",
        "type": "aws:s3/bucket:Bucket",
        "dependencies": []
    }
]
resource_providers = {"unknown": 3, "aws": 1}
```

**検証項目**:
- [ ] エラーを投げない（例外が発生しない）
- [ ] DOTファイルが生成される
- [ ] 不正なURNのリソースがデフォルト色設定で表示される
- [ ] 正常なURNのリソースは正しく処理される
- [ ] スタックノードが存在する
- [ ] プロバイダーノード（unknown, aws）が存在する

---

#### TC-EH-02: 空データ

**Feature**: 空データの処理

**Scenario**: リソースリストが空の場合、空のDOT出力を生成してエラーを投げない

**目的**:
- 空リソースリストのハンドリングを検証
- エッジケースでもシステムが安定していることを確認

**Given** (前提条件):
- リソースリストが空（`[]`）のPulumiデータが存在する
- スタック名: "empty-stack"

**When** (操作):
- DotFileGenerator.create_dot_file()を呼び出す
- 空のリソースリストを渡す

**Then** (期待結果):
- エラーを投げない（例外が発生しない）
- DOTファイルが生成される
- スタックノードのみが存在する
- プロバイダーノードは存在しない
- リソースノードは存在しない
- DOT構文が有効である

**テストデータ**:
```python
stack_name = "empty-stack"
resources = []
resource_providers = {}
```

**検証項目**:
- [ ] エラーを投げない（例外が発生しない）
- [ ] DOTファイルが生成される
- [ ] スタックノード"empty-stack"が存在する
- [ ] プロバイダーノードが存在しない
- [ ] リソースノードが存在しない
- [ ] DOT文字列が`digraph`で始まる
- [ ] DOT文字列が`}`で終わる

---

#### TC-EH-03: Noneデータ

**Feature**: Noneデータの処理

**Scenario**: Noneデータを含むリソースを処理しても、デフォルト値で処理されエラーを投げない

**目的**:
- Noneデータのハンドリングを検証
- 各メソッドのNoneチェックが機能していることを確認

**Given** (前提条件):
- Noneデータを含むPulumiデータが存在する
- リソースのURNがNone
- リソースのtypeがNone
- リソースのdependenciesがNone

**When** (操作):
- DotFileGenerator.create_dot_file()を呼び出す
- Noneデータを含むリソースリストを渡す

**Then** (期待結果):
- エラーを投げない（例外が発生しない）
- DOTファイルが生成される
- Noneデータはデフォルト値で処理される:
  - URN: "unknown" or 空文字列
  - type: "unknown"
  - dependencies: 空リスト
- 正常なリソースは正しく処理される

**テストデータ**:
```python
stack_name = "none-data-stack"
resources = [
    {
        "urn": None,
        "type": None,
        "dependencies": None
    },
    {
        "urn": "urn:pulumi:dev::app::aws:s3/bucket:Bucket::valid-bucket",
        "type": "aws:s3/bucket:Bucket",
        "dependencies": []
    }
]
resource_providers = {"unknown": 1, "aws": 1}
```

**検証項目**:
- [ ] エラーを投げない（例外が発生しない）
- [ ] DOTファイルが生成される
- [ ] Noneデータのリソースがデフォルト値で処理される
- [ ] 正常なリソースは正しく処理される
- [ ] スタックノードが存在する
- [ ] 2つのプロバイダーノード（unknown, aws）が存在する

---

### 2.3 境界値統合テスト（3ケース）

リソース数の境界値での動作を検証します。

---

#### TC-BV-01: 0リソース（空リソース）

**Feature**: 0リソースの処理

**Scenario**: リソース数が0の場合、スタックノードのみのDOT出力を生成する

**目的**:
- 最小境界値（0リソース）のハンドリングを検証
- TC-EH-02（空データ）と同じだが、境界値テストとして明示的に実施

**Given** (前提条件):
- リソース数が0のPulumiデータが存在する
- スタック名: "zero-resource-stack"

**When** (操作):
- DotFileGenerator.create_dot_file()を呼び出す
- 空のリソースリスト（`[]`）を渡す

**Then** (期待結果):
- エラーを投げない（例外が発生しない）
- DOTファイルが生成される
- スタックノードのみが存在する
- プロバイダーノードは存在しない
- リソースノードは存在しない

**テストデータ**:
```python
stack_name = "zero-resource-stack"
resources = []
resource_providers = {}
```

**検証項目**:
- [ ] エラーを投げない
- [ ] DOTファイルが生成される
- [ ] スタックノード"zero-resource-stack"が存在する
- [ ] プロバイダーノードが0個
- [ ] リソースノードが0個
- [ ] DOT構文が有効である

---

#### TC-BV-02: 20リソース（最大値）

**Feature**: 最大リソース数の処理

**Scenario**: リソース数が20（最大値）の場合、全20リソースが正しく処理される

**目的**:
- 最大境界値（20リソース）のハンドリングを検証
- パフォーマンスが許容範囲内であることを確認

**Given** (前提条件):
- リソース数が20のPulumiデータが存在する
- スタック名: "max-resource-stack"

**When** (操作):
- DotFileGenerator.create_dot_file()を呼び出す
- 20個のリソースを含むリストを渡す

**Then** (期待結果):
- エラーを投げない（例外が発生しない）
- DOTファイルが生成される
- 全20リソースが処理される
- スタックノード、プロバイダーノード、20個のリソースノードが存在する
- 処理時間が許容範囲内（< 2秒）

**テストデータ**:
```python
stack_name = "max-resource-stack"
resources = [
    {
        "urn": f"urn:pulumi:dev::app::aws:s3/bucket:Bucket::bucket-{i}",
        "type": "aws:s3/bucket:Bucket",
        "dependencies": []
    }
    for i in range(20)
]
resource_providers = {"aws": 20}
```

**検証項目**:
- [ ] エラーを投げない
- [ ] DOTファイルが生成される
- [ ] スタックノードが存在する
- [ ] プロバイダーノード"aws"が存在する
- [ ] 20個のリソースノードが存在する
- [ ] 処理時間 < 2秒

---

#### TC-BV-03: 21リソース（最大値超過）

**Feature**: 最大リソース数超過の処理

**Scenario**: リソース数が21（最大値超過）の場合、最初の20リソースのみ処理される

**目的**:
- 最大値超過時の制限処理を検証
- `resources[:20]`のスライス処理が機能していることを確認

**Given** (前提条件):
- リソース数が21のPulumiデータが存在する
- スタック名: "overflow-stack"

**When** (操作):
- DotFileGenerator.create_dot_file()を呼び出す
- 21個のリソースを含むリストを渡す

**Then** (期待結果):
- エラーを投げない（例外が発生しない）
- DOTファイルが生成される
- 最初の20リソースのみが処理される
- 21番目のリソースは処理されない
- スタックノード、プロバイダーノード、20個のリソースノードが存在する
- 警告メッセージが出力される（オプション）

**テストデータ**:
```python
stack_name = "overflow-stack"
resources = [
    {
        "urn": f"urn:pulumi:dev::app::aws:s3/bucket:Bucket::bucket-{i}",
        "type": "aws:s3/bucket:Bucket",
        "dependencies": []
    }
    for i in range(21)
]
resource_providers = {"aws": 21}
```

**検証項目**:
- [ ] エラーを投げない
- [ ] DOTファイルが生成される
- [ ] スタックノードが存在する
- [ ] プロバイダーノード"aws"が存在する
- [ ] 20個のリソースノードが存在する（21個ではない）
- [ ] 21番目のリソース（bucket-20）が存在しない
- [ ] 処理時間 < 2秒

---

## 3. パフォーマンステストシナリオ

リファクタリング前後のパフォーマンス比較を実施します。

### 3.1 パフォーマンステストの測定方法

**測定ツール**: `timeit`モジュール

**測定手順**:
1. ウォームアップ実行（10回）: キャッシュを効かせる
2. 本測定（100回実行）: 平均実行時間を測定
3. 標準偏差を計算: 測定のばらつきを評価

**ベースライン**:
- Phase 1実施前のコード（可能であれば別ブランチから取得）
- ベースラインが取得できない場合は、現在のパフォーマンスを記録して将来の基準とする

**許容範囲**: ±10%以内

**結果の記録**:
- CSV形式で保存: `テストメソッド名, リソース数, 平均実行時間(秒), 標準偏差(秒), ベースライン比較(%)`

---

#### TC-P-01: 1リソース処理時間

**Feature**: DotFileGenerator.create_dot_file()のパフォーマンス

**Scenario**: 1リソース処理時間が許容範囲内である

**目的**:
- 最小リソース数でのパフォーマンスを測定
- ベースラインとの比較

**Given** (前提条件):
- リソース数: 1個
- スタック名: "perf-test-stack"

**When** (操作):
- DotFileGenerator.create_dot_file()を100回実行
- 平均実行時間を測定

**Then** (期待結果):
- 平均実行時間 < 0.1秒
- ベースラインとの差が±10%以内
- 標準偏差が小さい（安定した実行時間）

**テストデータ**:
```python
stack_name = "perf-test-stack"
resources = [
    {
        "urn": "urn:pulumi:dev::app::aws:s3/bucket:Bucket::bucket-1",
        "type": "aws:s3/bucket:Bucket",
        "dependencies": []
    }
]
resource_providers = {"aws": 1}
```

**検証項目**:
- [ ] 平均実行時間 < 0.1秒
- [ ] ベースライン比較: -10% ≤ 差 ≤ +10%
- [ ] 標準偏差 < 平均の10%

---

#### TC-P-02: 5リソース処理時間

**Feature**: DotFileGenerator.create_dot_file()のパフォーマンス

**Scenario**: 5リソース処理時間が許容範囲内である

**目的**:
- 中規模リソース数でのパフォーマンスを測定

**Given** (前提条件):
- リソース数: 5個
- スタック名: "perf-test-stack"

**When** (操作):
- DotFileGenerator.create_dot_file()を100回実行
- 平均実行時間を測定

**Then** (期待結果):
- 平均実行時間 < 0.5秒
- ベースラインとの差が±10%以内

**テストデータ**:
```python
stack_name = "perf-test-stack"
resources = [
    {
        "urn": f"urn:pulumi:dev::app::aws:s3/bucket:Bucket::bucket-{i}",
        "type": "aws:s3/bucket:Bucket",
        "dependencies": []
    }
    for i in range(5)
]
resource_providers = {"aws": 5}
```

**検証項目**:
- [ ] 平均実行時間 < 0.5秒
- [ ] ベースライン比較: -10% ≤ 差 ≤ +10%
- [ ] 標準偏差 < 平均の10%

---

#### TC-P-03: 10リソース処理時間

**Feature**: DotFileGenerator.create_dot_file()のパフォーマンス

**Scenario**: 10リソース処理時間が許容範囲内である

**目的**:
- 大規模リソース数でのパフォーマンスを測定

**Given** (前提条件):
- リソース数: 10個
- スタック名: "perf-test-stack"

**When** (操作):
- DotFileGenerator.create_dot_file()を100回実行
- 平均実行時間を測定

**Then** (期待結果):
- 平均実行時間 < 1.0秒
- ベースラインとの差が±10%以内

**テストデータ**:
```python
stack_name = "perf-test-stack"
resources = [
    {
        "urn": f"urn:pulumi:dev::app::aws:s3/bucket:Bucket::bucket-{i}",
        "type": "aws:s3/bucket:Bucket",
        "dependencies": []
    }
    for i in range(10)
]
resource_providers = {"aws": 10}
```

**検証項目**:
- [ ] 平均実行時間 < 1.0秒
- [ ] ベースライン比較: -10% ≤ 差 ≤ +10%
- [ ] 標準偏差 < 平均の10%

---

#### TC-P-04: 20リソース処理時間（境界値）

**Feature**: DotFileGenerator.create_dot_file()のパフォーマンス

**Scenario**: 20リソース（最大値）処理時間が許容範囲内である

**目的**:
- 最大リソース数でのパフォーマンスを測定
- スケーラビリティの限界を確認

**Given** (前提条件):
- リソース数: 20個
- スタック名: "perf-test-stack"

**When** (操作):
- DotFileGenerator.create_dot_file()を100回実行
- 平均実行時間を測定

**Then** (期待結果):
- 平均実行時間 < 2.0秒
- ベースラインとの差が±10%以内

**テストデータ**:
```python
stack_name = "perf-test-stack"
resources = [
    {
        "urn": f"urn:pulumi:dev::app::aws:s3/bucket:Bucket::bucket-{i}",
        "type": "aws:s3/bucket:Bucket",
        "dependencies": []
    }
    for i in range(20)
]
resource_providers = {"aws": 20}
```

**検証項目**:
- [ ] 平均実行時間 < 2.0秒
- [ ] ベースライン比較: -10% ≤ 差 ≤ +10%
- [ ] 標準偏差 < 平均の10%

---

#### TC-P-05: グラフスタイル適用処理時間

**Feature**: DotFileProcessor.apply_graph_styling()のパフォーマンス

**Scenario**: グラフスタイル適用処理時間が許容範囲内である

**目的**:
- DotFileProcessorのパフォーマンスを測定
- ノードラベル生成、色設定適用の処理時間を確認

**Given** (前提条件):
- 10リソースのDOT文字列が存在する
- スタイル未適用の状態

**When** (操作):
- DotFileProcessor.apply_graph_styling()を100回実行
- 平均実行時間を測定

**Then** (期待結果):
- 平均実行時間 < 0.1秒
- ベースラインとの差が±10%以内

**テストデータ**:
```python
# DotFileGenerator.create_dot_file()で生成された10リソースのDOT文字列
dot_content = """digraph G {
    "stack:dev-stack" [label="dev-stack"];
    "provider:aws" [label="aws"];
    "stack:dev-stack" -> "provider:aws";
    # ... 10 resources ...
}"""
```

**検証項目**:
- [ ] 平均実行時間 < 0.1秒
- [ ] ベースライン比較: -10% ≤ 差 ≤ +10%
- [ ] 標準偏差 < 平均の10%

---

## 4. BDDシナリオ

ユーザーストーリーベースのBDDシナリオを記載します。

### 4.1 Feature: Pulumi Stack Visualization

**ユーザーストーリー**:
As a DevOps engineer,
I want to visualize Pulumi stack resources as a graph,
So that I can understand resource dependencies and architecture at a glance.

---

#### Scenario: Visualize a basic AWS stack

**Given** ユーザーがPulumiスタック "dev-stack" をデプロイしている
**And** スタックには以下のリソースが含まれている:
  - S3バケット "my-bucket"
  - Lambda関数 "my-function"
  - IAMロール "lambda-role"
**And** Lambda関数はIAMロールに依存している

**When** ユーザーがDOTファイル生成を実行する

**Then** DOTファイルが生成される
**And** DOTファイルには以下が含まれている:
  - スタックノード "dev-stack"
  - AWSプロバイダーノード
  - 3つのリソースノード（S3、Lambda、IAM）
  - Lambda → IAMロールの依存関係エッジ
**And** AWSリソースにオレンジ系の色が適用されている
**And** ユーザーがGraphvizでグラフを可視化できる

---

#### Scenario: Visualize a multi-cloud stack

**Given** ユーザーがPulumiスタック "multi-cloud-stack" をデプロイしている
**And** スタックにはAWS and Azureのリソースが混在している
**And** AWSリソース: 3個（S3、EC2、RDS）
**And** Azureリソース: 2個（Storage、VM）

**When** ユーザーがDOTファイル生成を実行する

**Then** DOTファイルが生成される
**And** DOTファイルには以下が含まれている:
  - スタックノード "multi-cloud-stack"
  - AWSプロバイダーノード（オレンジ系）
  - Azureプロバイダーノード（青系）
  - 5つのリソースノード
**And** AWSリソースにオレンジ系の色が適用されている
**And** Azureリソースに青系の色が適用されている
**And** ユーザーが各プロバイダーのリソースを視覚的に区別できる

---

#### Scenario: Handle empty stack gracefully

**Given** ユーザーがPulumiスタック "empty-stack" をデプロイしている
**And** スタックにはリソースが1つも含まれていない

**When** ユーザーがDOTファイル生成を実行する

**Then** エラーが発生しない
**And** DOTファイルが生成される
**And** DOTファイルにはスタックノード "empty-stack" のみが含まれている
**And** ユーザーにエラーメッセージが表示されない

---

#### Scenario: Handle invalid URN gracefully

**Given** ユーザーがPulumiスタック "invalid-urn-stack" をデプロイしている
**And** スタックに不正なURN形式のリソースが含まれている
**And** 一部のリソースは正常なURN形式である

**When** ユーザーがDOTファイル生成を実行する

**Then** エラーが発生しない
**And** DOTファイルが生成される
**And** 不正なURNのリソースはデフォルト色（グレー系）で表示される
**And** 正常なURNのリソースは正しい色で表示される
**And** ユーザーが不正なURNのリソースを視覚的に識別できる

---

#### Scenario: Visualize complex dependencies

**Given** ユーザーがPulumiスタック "complex-stack" をデプロイしている
**And** スタックには以下の依存関係がある:
  - Lambda → IAMロール（単純依存）
  - API Gateway → Lambda（単純依存）
  - CloudWatch → Lambda（単純依存）
  - CloudWatch → API Gateway（複数依存）

**When** ユーザーがDOTファイル生成を実行する

**Then** DOTファイルが生成される
**And** すべての依存関係エッジが正しく表示される
**And** 依存関係の方向が正しい（被依存 → 依存元）
**And** ユーザーがリソース間の依存関係を理解できる

---

## 5. テストデータ

### 5.1 テストデータの種類

| データ種別 | 説明 | 使用テストケース |
|----------|------|-----------------|
| **正常データ** | 標準的なPulumiリソースデータ | TC-E-01, TC-E-02, TC-E-03 |
| **長いリソース名** | 100文字以上のリソース名 | TC-E-04 |
| **特殊文字データ** | DOT特殊文字を含むリソース名 | TC-E-05 |
| **不正URN** | URN形式が不正なデータ | TC-EH-01 |
| **空データ** | リソースリストが空 | TC-EH-02, TC-BV-01 |
| **Noneデータ** | Noneを含むリソースデータ | TC-EH-03 |
| **境界値データ** | 0, 20, 21リソース | TC-BV-01, TC-BV-02, TC-BV-03 |
| **パフォーマンステストデータ** | 1, 5, 10, 20リソース | TC-P-01~TC-P-04 |

### 5.2 テストデータの配置

テストデータは以下のディレクトリ構造で管理します：

```
jenkins/jobs/pipeline/infrastructure/pulumi-stack-action/tests/fixtures/test_data/
├── e2e/
│   ├── basic_aws.json           # TC-E-01
│   ├── multi_cloud.json         # TC-E-02
│   ├── complex_dependencies.json # TC-E-03
│   ├── long_resource_names.json # TC-E-04
│   └── special_characters.json  # TC-E-05
├── error_handling/
│   ├── invalid_urn.json         # TC-EH-01
│   ├── empty_data.json          # TC-EH-02
│   └── none_data.json           # TC-EH-03
├── boundary/
│   ├── zero_resources.json      # TC-BV-01
│   ├── max_resources.json       # TC-BV-02
│   └── overflow_resources.json  # TC-BV-03
└── performance/
    ├── 1_resource.json          # TC-P-01
    ├── 5_resources.json         # TC-P-02
    ├── 10_resources.json        # TC-P-03
    └── 20_resources.json        # TC-P-04
```

### 5.3 テストデータのフォーマット

すべてのテストデータはJSON形式で保存します：

```json
{
  "stack_name": "dev-stack",
  "resources": [
    {
      "urn": "urn:pulumi:dev::app::aws:s3/bucket:Bucket::my-bucket",
      "type": "aws:s3/bucket:Bucket",
      "dependencies": []
    }
  ],
  "resource_providers": {
    "aws": 1
  }
}
```

---

## 6. テスト環境要件

### 6.1 テスト実行環境

| 項目 | 要件 | 説明 |
|------|------|------|
| **OS** | Amazon Linux 2023 | ブートストラップ環境 |
| **Python** | 3.8以上 | 言語バージョン |
| **pytest** | 7.4.3 | テストフレームワーク |
| **pytest-cov** | 4.1.0 | カバレッジ測定ツール |
| **pytest-benchmark** | 4.0.0 (オプション) | パフォーマンステスト支援 |

### 6.2 必要な外部サービス

**なし**

Phase 4のテストは既存コードのレビューとテストが中心のため、外部サービス連携は発生しません。

### 6.3 モック/スタブの必要性

**不要**

Phase 4のテストは以下の理由でモック/スタブを使用しません：

1. **静的メソッド設計**: すべてのメソッドが静的メソッドであり、外部依存がない
2. **ステートレス設計**: 状態を持たない設計のため、モックが不要
3. **純粋関数**: 入力 → 処理 → 出力の純粋関数として実装されている

### 6.4 テストデータの準備

テストデータは以下の手順で準備します：

1. **フィクスチャの作成**: `conftest.py`に共通フィクスチャを定義
2. **テストデータファイルの配置**: `tests/fixtures/test_data/`にJSONファイルを配置
3. **テストコードでの読み込み**: `json.load()`でテストデータを読み込み

---

## 7. テスト実行手順

### 7.1 全テスト実行

```bash
# カレントディレクトリをテストディレクトリに移動
cd jenkins/jobs/pipeline/infrastructure/pulumi-stack-action/tests

# 全テスト実行
pytest -v

# カバレッジ付きで実行
pytest -v --cov=../src --cov-report=html --cov-report=term
```

### 7.2 特定のテスト種別のみ実行

```bash
# 統合テストのみ実行
pytest -v -m integration

# パフォーマンステストのみ実行
pytest -v -m performance

# エンドツーエンドテストのみ実行
pytest -v -k "test_e2e"

# エラーハンドリングテストのみ実行
pytest -v -k "test_error_handling"

# 境界値テストのみ実行
pytest -v -k "test_boundary"
```

### 7.3 並列実行（高速化）

```bash
# pytest-xdistを使用して4並列で実行
pytest -v -n 4
```

### 7.4 カバレッジ確認

```bash
# カバレッジ測定
pytest --cov=../src --cov-report=html --cov-report=term

# HTMLレポートを開く
open htmlcov/index.html
```

---

## 8. テスト成功基準

### 8.1 全体的な成功基準

| 項目 | 基準 | 説明 |
|------|------|------|
| **テスト合格率** | 100% | 全テストケース（130ケース）がパスする |
| **カバレッジ** | 80%以上 | pytest-covで測定 |
| **パフォーマンス** | ±10%以内 | リファクタリング前後の性能差 |
| **テスト実行時間** | 10秒以内 | 全テスト（130ケース）の実行時間 |

### 8.2 Phase 4の品質ゲート

Phase 4のテストシナリオは以下の品質ゲートを満たしています：

- [x] **Phase 2の戦略に沿ったテストシナリオである**: INTEGRATION_BDD戦略に準拠
- [x] **主要な正常系がカバーされている**: エンドツーエンド5ケース（基本、マルチクラウド、複雑依存、長い名前、特殊文字）
- [x] **主要な異常系がカバーされている**: エラーハンドリング3ケース（不正URN、空データ、Noneデータ）
- [x] **期待結果が明確である**: すべてのテストケースに検証項目のチェックリストを記載

---

## 9. リスクと軽減策

### 9.1 テストシナリオ作成に関するリスク

#### リスク1: テストデータ不足

- **影響度**: 中
- **確率**: 低
- **軽減策**:
  - テストデータファイルをJSON形式で事前準備
  - フィクスチャを活用して再利用可能なテストデータを作成
  - 既存のPhase 1~3のテストデータを活用

#### リスク2: パフォーマンステストのベースライン取得困難

- **影響度**: 中
- **確率**: 中
- **軽減策**:
  - Phase 1実施前のコードをGit履歴から取得
  - ベースライン取得が不可能な場合は、現在のパフォーマンスを記録して将来の基準とする
  - 相対的な性能比較ではなく、絶対的な性能目標（< 2秒）を設定

#### リスク3: 統合テストの実行時間が長い

- **影響度**: 低
- **確率**: 低
- **軽減策**:
  - pytest-xdistで並列実行（4並列）
  - テストケース数を16ケースに絞り込み（既存114ケースと合わせて130ケース）
  - パフォーマンステストは別途実行（マーカーで分離）

---

## 10. トレーサビリティマトリックス

Issue #465の要件とテストシナリオの対応関係を示します。

### 10.1 機能要件とテストシナリオの対応

| 機能要件 | テストシナリオ | 説明 |
|---------|--------------|------|
| FR-01: コードレビュー実施 | （テスト対象外） | コードレビューは手動プロセス |
| FR-02: レビュー指摘事項の修正 | （既存テストで検証） | 修正後、既存114ケースで回帰テスト |
| FR-03: パフォーマンステスト実施 | TC-P-01~TC-P-05 | 5ケースのパフォーマンステスト |
| FR-04: 統合テストケース追加 | TC-E-01~TC-E-05, TC-EH-01~TC-EH-03, TC-BV-01~TC-BV-03 | 11ケースの統合テスト |
| FR-05: アーキテクチャ図作成 | （テスト対象外） | ドキュメント成果物 |
| FR-06: クラス図作成 | （テスト対象外） | ドキュメント成果物 |
| FR-07: README更新 | （テスト対象外） | ドキュメント成果物 |
| FR-08: レビュー報告書作成 | （テスト対象外） | レポート成果物 |
| FR-09: パフォーマンス比較レポート作成 | TC-P-01~TC-P-05 | パフォーマンステスト結果を基に作成 |
| FR-10: Phase 4完了レポート作成 | （テスト対象外） | レポート成果物 |

### 10.2 受け入れ基準とテストシナリオの対応

| 受け入れ基準 | テストシナリオ | 説明 |
|------------|--------------|------|
| AC-01: コードレビューが承認されていること | （テスト対象外） | 手動レビュープロセス |
| AC-02: パフォーマンスに大きな劣化がないこと | TC-P-01~TC-P-05 | ±10%以内を検証 |
| AC-03: 統合テストがパスすること | TC-E-01~TC-E-05, TC-EH-01~TC-EH-03, TC-BV-01~TC-BV-03 | 11ケースすべてパス |
| AC-04: アーキテクチャ図が作成されていること | （テスト対象外） | ドキュメント成果物 |
| AC-05: クラス図が作成されていること | （テスト対象外） | ドキュメント成果物 |
| AC-06: READMEが最新の状態に更新されていること | （テスト対象外） | ドキュメント成果物 |
| AC-07: Phase 4完了レポートが作成されていること | （テスト対象外） | レポート成果物 |

---

## 11. 参考情報

### 11.1 既存テストケース

Phase 1~3で作成された既存テストケース（114ケース）：

| Phase | ファイル | テストケース数 | 説明 |
|-------|---------|---------------|------|
| Phase 1 | `test_urn_processor.py` | 24ケース | URN処理のユニットテスト |
| Phase 2 | `test_node_label_generator.py` | 29ケース | ノードラベル生成のユニットテスト |
| Phase 3 | `test_resource_dependency_builder.py` | 37ケース | リソース依存関係のユニットテスト |
| Phase 3 | `test_dot_processor.py` | 24ケース | DotFileProcessorの統合テスト |

### 11.2 テストマーカー

pytestマーカーを使用してテストを分類します：

```python
@pytest.mark.integration       # 統合テスト
@pytest.mark.performance       # パフォーマンステスト
@pytest.mark.characterization  # 既存の特性記述テスト
@pytest.mark.unit              # ユニットテスト（Phase 1~3）
```

### 11.3 技術スタック

- **言語**: Python 3.8以上
- **テストフレームワーク**: pytest 7.4.3
- **カバレッジツール**: pytest-cov 4.1.0
- **パフォーマンステスト**: timeitモジュール、pytest-benchmark（オプション）
- **並列実行**: pytest-xdist

---

## 12. 変更履歴

| 日付 | バージョン | 変更内容 | 作成者 |
|------|-----------|----------|--------|
| 2025-10-17 | 1.0 | 初版作成 | Claude Code |

---

**以上、テストシナリオを完了しました。**
