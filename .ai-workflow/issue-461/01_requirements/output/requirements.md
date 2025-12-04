# 要件定義書: dot_processor.py - Phase 2-1: UrnProcessorクラスの抽出

## ドキュメント情報

- **Issue番号**: #461
- **タイトル**: [Refactor] dot_processor.py - Phase 2-1: UrnProcessorクラスの抽出
- **親Issue**: #448
- **依存Issue**: #460 (Phase 1: 基盤整備)
- **作成日**: 2025-01-19
- **最終更新**: 2025-01-19
- **作成者**: AI Workflow Phase 1
- **レビュー状態**: 未レビュー

---

## 0. Planning Documentの確認

### 開発計画の全体像

Planning Document（`.ai-workflow/issue-461/00_planning/output/planning.md`）で策定された開発計画を踏まえて、本要件定義書を作成しています。

**主要な戦略的決定事項**:

1. **実装戦略**: REFACTOR（クラス抽出型リファクタリング）
   - 既存の`DotFileProcessor`からURN処理の責務を新規クラス`UrnProcessor`に分離
   - 単一責務の原則（SRP）に基づくクラス分割
   - 機能追加なし（外部から見た振る舞いは変更されない）

2. **テスト戦略**: UNIT_INTEGRATION
   - ユニットテスト: `UrnProcessor`単独での動作検証（新規作成）
   - インテグレーションテスト: 既存の`test_dot_processor.py`を活用して統合動作を検証

3. **テストコード戦略**: BOTH_TEST
   - CREATE_TEST: `test_urn_processor.py`を新規作成
   - EXTEND_TEST: `test_dot_processor.py`を更新（統合テストとして継続）

4. **リスク評価**: 中程度
   - 既存コードへの影響範囲が中程度（複数メソッドの呼び出し変更）
   - Phase 1で構築されたテストインフラによりリスク軽減可能

5. **見積もり工数**: 10~14時間
   - 要件定義: 1.5~2時間
   - 設計: 2~3時間
   - テストシナリオ: 1.5~2時間
   - 実装: 2.5~3.5時間
   - テストコード実装: 1.5~2時間
   - テスト実行: 0.5~1時間
   - ドキュメント: 0.5~1時間
   - レポート: 0.5時間

---

## 1. 概要

### 背景

`DotFileProcessor`クラスは、DOTファイル（Graphviz形式）の処理を担当していますが、URN（Uniform Resource Name）の解析、正規化、コンポーネント抽出など、URN処理に関する複数の責務を併せ持っています。これは単一責務の原則（SRP）に反しており、以下の問題を引き起こしています：

- **可読性の低下**: クラスのサイズが大きく、URN処理とDOT処理のロジックが混在
- **テスタビリティの低下**: URN処理のみを独立してテストすることが困難
- **再利用性の低下**: URN処理ロジックを他のコンポーネントから利用できない
- **保守性の低下**: URN処理の変更がDOT処理に影響を与える可能性

Phase 1（Issue #460）では、既存コードの振る舞いを記録する特性テスト（Characterization Test）を構築し、リファクタリングの安全網を整備しました。この基盤の上に、Phase 2-1ではURN処理の責務を分離します。

### 目的

1. **単一責務の原則（SRP）の適用**: URN処理の責務を`UrnProcessor`クラスに分離し、`DotFileProcessor`はDOT処理に専念させる
2. **テスタビリティの向上**: `UrnProcessor`単独でのユニットテストを可能にする
3. **再利用性の向上**: URN処理ロジックを他のコンポーネントから利用可能にする
4. **保守性の向上**: URN処理の変更をDOT処理から独立させる
5. **外部インターフェースの維持**: `DotFileProcessor`の公開APIは変更せず、振る舞いを完全に保持する

### ビジネス価値・技術的価値

**ビジネス価値**:
- コードの保守性向上により、将来的な機能追加・バグ修正のコストを削減
- テストカバレッジ向上により、品質リスクを低減

**技術的価値**:
- クリーンアーキテクチャの実現（単一責務の原則の適用）
- コードの可読性向上による開発効率の向上
- テスタビリティ向上によるテスト実行時間の短縮（ユニットテストの独立実行）
- 再利用性向上による将来的な横展開の可能性

---

## 2. 機能要件

本セクションでは、Issue #461の「## TODO」セクションから抽出した機能要件を記載します。

### 2.1 新規ファイル作成: `urn_processor.py` 【優先度: 高】

**要件**: URN処理に特化した新規モジュール`urn_processor.py`を作成する

**詳細**:
- ファイルパス: `jenkins/jobs/pipeline/infrastructure/pulumi-stack-action/src/urn_processor.py`
- モジュールドキュメント文字列を記載（目的、主要機能、使用例）
- `UrnProcessor`クラスを定義
- 全メソッドに型ヒント（Type Hints）を付与
- 全メソッドにドキュメント文字列を記載

**受け入れ基準**:
- Given: 新規ファイル作成が必要な場合
- When: `urn_processor.py`を作成する
- Then: ファイルが適切な場所に配置され、PEP 8に準拠している

### 2.2 URNパースロジックの抽出 【優先度: 高】

**要件**: `DotFileProcessor.parse_urn()`メソッドを`UrnProcessor`クラスに移行する

**詳細**:
- `parse_urn(urn: str) -> Dict[str, str]`メソッドを抽出
  - URNをパースして構成要素を抽出
  - 抽出する要素: `stack`, `project`, `provider`, `module`, `type`, `name`, `full_urn`
  - エラーハンドリング: 不正なURNの場合はデフォルト値を返す（例外を投げない）
- `_parse_provider_type(provider_type: str) -> Dict[str, str]`メソッドを抽出
  - プロバイダータイプ文字列を解析
  - 抽出する要素: `provider`, `module`, `type`
- 既存の実装を維持（振る舞い変更なし）

**受け入れ基準**:
- Given: 正常なURN形式の文字列（例: `urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket`）
- When: `UrnProcessor.parse_urn()`を呼び出す
- Then: 辞書形式で構成要素が正しく抽出される
- Given: 不正なURN形式の文字列
- When: `UrnProcessor.parse_urn()`を呼び出す
- Then: デフォルト値を含む辞書が返される（例外が発生しない）

### 2.3 URI正規化ロジックの移行 【優先度: 高】

**要件**: `DotFileProcessor.create_readable_label()`および`_format_resource_type()`メソッドを`UrnProcessor`クラスに移行する

**詳細**:
- `create_readable_label(urn_info: Dict[str, str]) -> str`メソッドを抽出
  - URN情報から読みやすいラベルを生成
  - 改行区切り（`\n`）のラベル文字列を返す
  - モジュール名の有無に対応
- `_format_resource_type(resource_type: str) -> str`メソッドを抽出
  - リソースタイプを読みやすい形式にフォーマット
  - 長いタイプ名の省略処理（30文字以上の場合）
  - キャメルケースの単語分割

**受け入れ基準**:
- Given: URN情報辞書（`provider`, `module`, `type`, `name`を含む）
- When: `UrnProcessor.create_readable_label()`を呼び出す
- Then: 改行区切りの読みやすいラベル文字列が返される
- Given: 30文字以上のリソースタイプ名
- When: `UrnProcessor._format_resource_type()`を呼び出す
- Then: 省略されたタイプ名が返される（例: `VeryLongType...Name`）

### 2.4 コンポーネント抽出メソッドの実装 【優先度: 高】

**要件**: `DotFileProcessor.is_stack_resource()`メソッドを`UrnProcessor`クラスに移行する

**詳細**:
- `is_stack_resource(urn: str) -> bool`メソッドを抽出
  - スタックリソースかどうかを判定
  - 判定条件: URNに`pulumi:pulumi:Stack`を含む

**受け入れ基準**:
- Given: スタックリソースURN（例: `urn:pulumi:dev::myproject::pulumi:pulumi:Stack::dev`）
- When: `UrnProcessor.is_stack_resource()`を呼び出す
- Then: `True`が返される
- Given: 通常のリソースURN（例: AWS S3バケット）
- When: `UrnProcessor.is_stack_resource()`を呼び出す
- Then: `False`が返される

### 2.5 単体テストの作成: `test_urn_processor.py` 【優先度: 高】

**要件**: `UrnProcessor`クラスの単体テストを新規作成する

**詳細**:
- ファイルパス: `jenkins/jobs/pipeline/infrastructure/pulumi-stack-action/tests/test_urn_processor.py`
- テストクラス構成:
  - `TestUrnProcessorParsing`: URNパースのテスト
  - `TestUrnProcessorLabelCreation`: ラベル生成のテスト
  - `TestUrnProcessorResourceIdentification`: リソース判定のテスト
- カバレッジ目標: 80%以上
- Phase 1で構築された`conftest.py`のフィクスチャ（`sample_urns`等）を活用

**受け入れ基準**:
- Given: `UrnProcessor`クラスのすべての公開メソッド
- When: テストスイートを実行する
- Then: すべてのテストがパスし、カバレッジが80%以上である
- Given: エッジケース（不正なURN、空文字列、極端に長いURN等）
- When: テストを実行する
- Then: すべてのエッジケースが正しく処理されることが検証される

### 2.6 `DotFileProcessor`からの呼び出し部分の更新 【優先度: 高】

**要件**: `DotFileProcessor`内のURN処理メソッド呼び出しを`UrnProcessor`の呼び出しに置き換える

**詳細**:
- インポート追加: `from urn_processor import UrnProcessor`
- URN関連メソッドの削除:
  - `parse_urn()`
  - `_parse_provider_type()`
  - `create_readable_label()`
  - `_format_resource_type()`
  - `is_stack_resource()`
- メソッド呼び出しの置き換え:
  - `self.parse_urn()` → `UrnProcessor.parse_urn()`
  - `self.create_readable_label()` → `UrnProcessor.create_readable_label()`
  - `self.is_stack_resource()` → `UrnProcessor.is_stack_resource()`
- 影響を受けるメソッド:
  - `_process_node_definition()`
  - `_generate_resource_node_attributes()`
  - `_shorten_pulumi_label()`

**受け入れ基準**:
- Given: 既存の`test_dot_processor.py`のテストスイート
- When: `DotFileProcessor`の修正後にテストを実行する
- Then: すべての既存テストがパスする（統合テストとして機能）
- Given: `DotFileProcessor`の公開API
- When: 外部から`DotFileProcessor`を使用する
- Then: 外部から見た振る舞いが変更前と完全に一致する

---

## 3. 非機能要件

### 3.1 パフォーマンス要件 【優先度: 中】

**要件3.1.1**: URNパース処理は既存実装と同等のパフォーマンスを維持する

**詳細**:
- 単一URNのパース処理時間: 1ms未満（既存実装と同等）
- 100件のURNの一括パース処理時間: 100ms未満

**根拠**: リファクタリングによるパフォーマンス劣化を防ぐため

**受け入れ基準**:
- Given: 100件のURNを含むリスト
- When: `UrnProcessor.parse_urn()`を各URNに対して実行する
- Then: 合計処理時間が100ms未満である

### 3.2 セキュリティ要件 【優先度: 低】

**要件3.2.1**: URN処理において悪意のある入力を安全に処理する

**詳細**:
- 極端に長いURN（1万文字以上）を処理してもメモリリークや無限ループが発生しない
- 特殊文字を含むURNを処理してもコードインジェクションが発生しない

**根拠**: セキュリティリスクを最小化するため

**受け入れ基準**:
- Given: 1万文字のURN文字列
- When: `UrnProcessor.parse_urn()`を呼び出す
- Then: 処理が正常に完了し、メモリリークが発生しない
- Given: SQLインジェクション文字列を含むURN
- When: `UrnProcessor.parse_urn()`を呼び出す
- Then: 安全に処理され、エスケープが正しく行われる

### 3.3 可用性・信頼性要件 【優先度: 高】

**要件3.3.1**: 不正なURN入力に対して例外を投げず、デフォルト値を返す

**詳細**:
- 空文字列、`None`、不正なフォーマットのURNを受け取った場合でも例外を投げない
- デフォルト値を含む辞書を返す（`provider='unknown'`, `type='unknown'`等）

**根拠**: Pulumi生成データに不正なURNが含まれる可能性があるため、処理を継続する必要がある

**受け入れ基準**:
- Given: 空文字列のURN
- When: `UrnProcessor.parse_urn('')`を呼び出す
- Then: 例外が発生せず、デフォルト値を含む辞書が返される

### 3.4 保守性・拡張性要件 【優先度: 高】

**要件3.4.1**: 全メソッドに型ヒントとドキュメント文字列を記載する

**詳細**:
- 型ヒント: すべてのメソッドの引数と戻り値に型ヒントを付与
- ドキュメント文字列: 各メソッドの目的、引数、戻り値、エラーハンドリングを記載

**根拠**: コードの可読性と保守性を向上させるため

**受け入れ基準**:
- Given: `urn_processor.py`のすべてのメソッド
- When: コードレビューを実施する
- Then: すべてのメソッドに型ヒントとドキュメント文字列が記載されている

**要件3.4.2**: 静的メソッド中心の設計により、ステートレスな処理を実現する

**詳細**:
- `UrnProcessor`クラスはインスタンス変数を持たない
- 全メソッドを`@staticmethod`として実装する（必要に応じてクラスメソッドも検討）

**根拠**: ステートレスな設計により、並行処理時の競合を回避し、テストを簡略化するため

**受け入れ基準**:
- Given: `UrnProcessor`クラス
- When: クラス設計をレビューする
- Then: インスタンス変数が存在せず、すべてのメソッドが静的メソッドである

---

## 4. 制約事項

### 4.1 技術的制約

**制約4.1.1**: 既存の`DotFileProcessor`の公開APIを変更してはならない

**詳細**:
- 外部から`DotFileProcessor`のメソッドを呼び出しているコードが存在する可能性があるため、公開APIを維持する必要がある
- 内部実装（プライベートメソッド）の変更は許容される

**影響**:
- `DotFileProcessor`の公開メソッドのシグネチャは変更不可
- 内部で`UrnProcessor`を呼び出す形で実装を変更

**制約4.1.2**: Phase 1で構築されたテストインフラを活用する

**詳細**:
- `conftest.py`で定義されたフィクスチャ（`sample_urns`, `sample_resources`等）を再利用する
- 既存のテストスイート（`test_dot_processor.py`）を統合テストとして継続使用する

**影響**:
- 新規テストファイル（`test_urn_processor.py`）は既存フィクスチャを活用
- テストコードの重複を最小化

**制約4.1.3**: Python 3.8以上に対応する

**詳細**:
- 型ヒントは Python 3.8 の標準ライブラリ（`typing`モジュール）を使用
- Python 3.10以降の新機能（Union演算子`|`等）は使用しない

**影響**:
- `Dict[str, str]`を使用（`dict[str, str]`は使用不可）
- `Optional[str]`を使用（`str | None`は使用不可）

### 4.2 リソース制約

**制約4.2.1**: 実装工数は10~14時間以内とする

**詳細**:
- Planning Documentで見積もられた工数範囲内で完了する必要がある
- 各フェーズの工数見積もりを超過する場合はエスカレーション

**影響**:
- タスクの優先順位付けが必要
- ドキュメント整備等の優先度が低いタスクは後回し可能

**制約4.2.2**: カバレッジ測定はPhase 6で実施する

**詳細**:
- テストコード実装後、全体のカバレッジを測定する
- 80%未満の場合は追加テストを作成

**影響**:
- カバレッジ測定結果によっては、追加工数が発生する可能性

### 4.3 ポリシー制約

**制約4.3.1**: PEP 8コーディング規約に準拠する

**詳細**:
- インデント: 4スペース
- 命名規則: クラス名はPascalCase、メソッド名はsnake_case
- 行の長さ: 最大88文字（Black準拠）

**影響**:
- コードレビュー時にPEP 8準拠を確認
- リンター（`flake8`、`black`等）の実行を推奨

**制約4.3.2**: Phase 1で記録された振る舞いを変更してはならない

**詳細**:
- 特性テスト（Characterization Test）で記録された既存の振る舞いを完全に維持する
- テスト実行結果が変更前と完全に一致する必要がある

**影響**:
- リファクタリング後、既存のテストスイートが全てパスする必要がある
- 振る舞い変更が必要な場合は、別途Issue化して対応

---

## 5. 前提条件

### 5.1 システム環境

**前提5.1.1**: Python 3.8以上がインストールされている

**詳細**:
- 開発環境、テスト環境ともにPython 3.8以上を使用
- 型ヒント、`typing`モジュール等の標準ライブラリを使用

**前提5.1.2**: pytestがインストールされている

**詳細**:
- テスト実行にpytestを使用
- `conftest.py`で定義されたフィクスチャを利用

### 5.2 依存コンポーネント

**前提5.2.1**: Phase 1（Issue #460）が完了している

**詳細**:
- 特性テストが構築され、既存コードの振る舞いが記録されている
- `conftest.py`にフィクスチャ（`sample_urns`, `sample_resources`等）が定義されている
- カバレッジ測定環境が整備されている

**前提5.2.2**: `dot_processor.py`が現在の形で存在している

**詳細**:
- `DotFileProcessor`クラスが実装されている
- URN処理に関するメソッド（`parse_urn()`, `create_readable_label()`, `is_stack_resource()`等）が実装されている

### 5.3 外部システム連携

**前提5.3.1**: 外部システムとの連携は存在しない

**詳細**:
- `UrnProcessor`は純粋な計算処理のみを行う
- データベースアクセス、API呼び出し等の外部連携は行わない

---

## 6. 受け入れ基準

本セクションでは、各機能要件の受け入れ基準をGiven-When-Then形式で記載します。

### 6.1 新規ファイル作成: `urn_processor.py`

**シナリオ6.1.1**: 新規ファイルが適切な場所に配置される

- **Given**: 新規ファイル作成が必要な場合
- **When**: `urn_processor.py`を作成する
- **Then**: ファイルパスが`jenkins/jobs/pipeline/infrastructure/pulumi-stack-action/src/urn_processor.py`である
- **And**: ファイルがPEP 8に準拠している
- **And**: モジュールドキュメント文字列が記載されている

**シナリオ6.1.2**: `UrnProcessor`クラスが定義される

- **Given**: `urn_processor.py`が作成されている
- **When**: ファイルをインポートする
- **Then**: `UrnProcessor`クラスが定義されている
- **And**: すべてのメソッドに型ヒントが付与されている
- **And**: すべてのメソッドにドキュメント文字列が記載されている

### 6.2 URNパースロジックの抽出

**シナリオ6.2.1**: 正常なAWS URNが正しく解析される

- **Given**: 正常なAWS URN文字列 `urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket`
- **When**: `UrnProcessor.parse_urn(urn)`を呼び出す
- **Then**: 辞書が返される
- **And**: `result['stack'] == 'dev'`
- **And**: `result['project'] == 'myproject'`
- **And**: `result['provider'] == 'aws'`
- **And**: `result['module'] == 's3'`
- **And**: `result['type'] == 'Bucket'`
- **And**: `result['name'] == 'my-bucket'`
- **And**: `result['full_urn'] == urn`

**シナリオ6.2.2**: 不正なURNが安全に処理される

- **Given**: 不正なURN形式の文字列 `invalid-urn`
- **When**: `UrnProcessor.parse_urn(urn)`を呼び出す
- **Then**: 例外が発生しない
- **And**: デフォルト値を含む辞書が返される
- **And**: `result['provider'] == 'unknown'`
- **And**: `result['type'] == 'unknown'`

**シナリオ6.2.3**: 空文字列が安全に処理される

- **Given**: 空文字列 `''`
- **When**: `UrnProcessor.parse_urn('')`を呼び出す
- **Then**: 例外が発生しない
- **And**: デフォルト値を含む辞書が返される
- **And**: `result['name'] == ''`

### 6.3 URI正規化ロジックの移行

**シナリオ6.3.1**: 基本的なラベルが正しく生成される

- **Given**: URN情報辞書
  ```python
  urn_info = {
      'provider': 'aws',
      'module': 's3',
      'type': 'Bucket',
      'name': 'my-bucket'
  }
  ```
- **When**: `UrnProcessor.create_readable_label(urn_info)`を呼び出す
- **Then**: 改行区切りのラベル文字列が返される
- **And**: `'s3' in result`
- **And**: `'Bucket' in result`
- **And**: `'my-bucket' in result`
- **And**: `'\\n' in result`

**シナリオ6.3.2**: モジュール名がない場合のラベルが正しく生成される

- **Given**: モジュール名がないURN情報辞書
  ```python
  urn_info = {
      'provider': 'pulumi',
      'module': '',
      'type': 'Stack',
      'name': 'dev'
  }
  ```
- **When**: `UrnProcessor.create_readable_label(urn_info)`を呼び出す
- **Then**: モジュール名が省略されたラベルが返される
- **And**: `'Stack' in result`
- **And**: `'dev' in result`

**シナリオ6.3.3**: 長いタイプ名が省略される

- **Given**: 30文字以上のリソースタイプ名 `VeryLongResourceTypeNameThatExceeds30Characters`
- **When**: `UrnProcessor._format_resource_type(resource_type)`を呼び出す
- **Then**: 省略されたタイプ名が返される
- **And**: `len(result) <= 30`（または省略記号`...`を含む）

### 6.4 コンポーネント抽出メソッドの実装

**シナリオ6.4.1**: スタックリソースが正しく判定される

- **Given**: スタックリソースURN `urn:pulumi:dev::myproject::pulumi:pulumi:Stack::dev`
- **When**: `UrnProcessor.is_stack_resource(urn)`を呼び出す
- **Then**: `True`が返される

**シナリオ6.4.2**: 通常リソースが正しく判定される

- **Given**: 通常リソースURN `urn:pulumi:dev::myproject::aws:s3/bucket:Bucket::my-bucket`
- **When**: `UrnProcessor.is_stack_resource(urn)`を呼び出す
- **Then**: `False`が返される

### 6.5 単体テストの作成: `test_urn_processor.py`

**シナリオ6.5.1**: すべての公開メソッドのテストが存在する

- **Given**: `UrnProcessor`クラスのすべての公開メソッド
- **When**: `test_urn_processor.py`をレビューする
- **Then**: 各公開メソッドに対応するテストクラスが存在する
- **And**: 正常系、異常系、エッジケースのテストが含まれる

**シナリオ6.5.2**: カバレッジが80%以上である

- **Given**: `test_urn_processor.py`のテストスイート
- **When**: カバレッジ測定を実行する
- **Then**: `urn_processor.py`のカバレッジが80%以上である
- **And**: カバレッジレポート（HTML）が生成される

**シナリオ6.5.3**: すべてのテストがパスする

- **Given**: `test_urn_processor.py`のテストスイート
- **When**: `pytest tests/test_urn_processor.py`を実行する
- **Then**: すべてのテストがパスする
- **And**: テストが安定している（複数回実行で同じ結果）

### 6.6 `DotFileProcessor`からの呼び出し部分の更新

**シナリオ6.6.1**: 既存の統合テストがすべてパスする

- **Given**: 既存の`test_dot_processor.py`のテストスイート
- **When**: `DotFileProcessor`の修正後に`pytest tests/test_dot_processor.py`を実行する
- **Then**: すべての既存テストがパスする
- **And**: テスト実行時間が既存と同等である

**シナリオ6.6.2**: 外部から見た振る舞いが変更されていない

- **Given**: `DotFileProcessor`の公開API
- **When**: 外部から`DotFileProcessor`のメソッドを呼び出す
- **Then**: 戻り値が変更前と完全に一致する
- **And**: 例外の発生条件が変更されていない

---

## 7. スコープ外

本セクションでは、Issue #461のスコープ外として明確にする事項を記載します。

### 7.1 Phase 2-1でのスコープ外

**スコープ外7.1.1**: `DotFileGenerator`クラスのリファクタリング

**理由**: `DotFileGenerator`クラスはDOTファイル生成の責務を持ち、URN処理とは独立しているため、Phase 2-1のスコープ外とする。将来的なフェーズで検討する可能性がある。

**スコープ外7.1.2**: グラフスタイル適用ロジックの改善

**理由**: `apply_graph_styling()`, `_enhance_pulumi_graph()`等のグラフスタイル適用ロジックは、URN処理とは独立しており、Phase 2-1のスコープ外とする。

**スコープ外7.1.3**: DOT文字列エスケープ処理の改善

**理由**: `DotFileGenerator.escape_dot_string()`は既に独立したメソッドとして実装されており、URN処理との関連性が低いため、Phase 2-1のスコープ外とする。

**スコープ外7.1.4**: 新機能の追加

**理由**: Phase 2-1はリファクタリングのみを目的としており、新機能の追加は行わない。外部から見た振る舞いは完全に維持する。

**スコープ外7.1.5**: パフォーマンス最適化

**理由**: 既存実装と同等のパフォーマンスを維持するが、最適化は行わない。パフォーマンス改善が必要な場合は、別途Issue化して対応する。

### 7.2 将来的な拡張候補

**拡張候補7.2.1**: URN検証機能の追加

**詳細**: URNの形式を厳密に検証し、不正なURNを検出する機能を追加する可能性がある。

**拡張候補7.2.2**: URN正規化機能の拡張

**詳細**: 複数のURN形式を統一的に扱うための正規化機能を追加する可能性がある（例: GCPの`google`と`gcp`を統一）。

**拡張候補7.2.3**: URN処理のキャッシュ機能

**詳細**: 同じURNを複数回パースする際のパフォーマンス改善のため、キャッシュ機能を追加する可能性がある。

**拡張候補7.2.4**: プロバイダー情報の動的取得

**詳細**: プロバイダー色設定を外部ファイル（JSON/YAML）から読み込む機能を追加する可能性がある。

---

## 8. レビューチェックリスト（品質ゲート）

本要件定義書は、以下の品質ゲートを満たしていることを確認してください。

### ✅ 品質ゲート1: 機能要件が明確に記載されている

- [x] Issue #461の「## TODO」セクションから全機能要件を抽出
- [x] 各機能要件が明確かつ検証可能な形で記述されている
- [x] 優先度（高/中/低）が付与されている
- [x] 詳細な仕様が記載されている

### ✅ 品質ゲート2: 受け入れ基準が定義されている

- [x] 各機能要件に対応する受け入れ基準が記載されている
- [x] Given-When-Then形式で記述されている
- [x] テスト可能な形で具体的に記載されている
- [x] 成功条件・失敗条件が明確に識別可能である

### ✅ 品質ゲート3: スコープが明確である

- [x] スコープ内の機能要件が明確に定義されている
- [x] スコープ外の事項が明確にリストアップされている
- [x] 将来的な拡張候補が記載されている
- [x] 誤解の余地がない表現で記載されている

### ✅ 品質ゲート4: 論理的な矛盾がない

- [x] 機能要件と受け入れ基準が対応している
- [x] 非機能要件と制約事項が矛盾していない
- [x] 前提条件が現実的である
- [x] Planning Documentの戦略と整合性がある

---

## 9. 次フェーズへの引き継ぎ

### Phase 2: 設計への準備

Phase 2（設計フェーズ）では、以下の情報を引き継ぎます：

1. **機能要件**: セクション2で定義された全機能要件
2. **非機能要件**: セクション3で定義されたパフォーマンス、セキュリティ、保守性要件
3. **制約事項**: セクション4で定義された技術的制約、リソース制約、ポリシー制約
4. **受け入れ基準**: セクション6で定義されたGiven-When-Then形式の受け入れ基準

### 設計フェーズで実施すべき事項

1. **クラス設計**: `UrnProcessor`クラスの詳細設計（静的メソッド vs インスタンスメソッド）
2. **メソッドシグネチャ設計**: 全メソッドの引数、戻り値、型ヒントの確定
3. **エラーハンドリング設計**: 不正な入力に対する処理方針の詳細化
4. **テストアーキテクチャ設計**: テストクラス構成、フィクスチャ活用戦略の策定

---

## 10. 変更履歴

| 日付 | 変更内容 | 変更者 |
|------|---------|--------|
| 2025-01-19 | 初版作成 | AI Workflow Phase 1 |

---

**このドキュメントは、Phase 0（Planning）の成果物を基に作成されました。**
**Phase 2（設計）以降のフェーズでは、本要件定義書を基に詳細設計を進めてください。**
