# Phase 1: 要件定義書

**Issue**: #462 - [Refactor] dot_processor.py - Phase 2-2: NodeLabelGeneratorクラスの抽出
**作成日**: 2025-01-XX
**担当者**: AI Agent
**Planning Document参照**: [planning.md](../../00_planning/output/planning.md)

---

## 📋 0. Planning Documentの確認

### 開発計画の全体像

Planning Documentで策定された以下の戦略を踏まえて要件定義を実施します：

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
- 要件定義: 1h
- 設計: 2~3h
- テストシナリオ: 1~2h
- 実装: 3~4h
- テストコード実装: 2~3h
- テスト実行: 0.5~1h
- ドキュメント: 0.5~1h

#### リスク評価: **低〜中**
- ラベル生成ロジックの抽出漏れ（中）
- カスタムラベル対応の仕様不明確さ（中）
- 既存テストへの影響（低）

---

## 📌 1. 概要

### 背景

Phase 2-2リファクタリングの一環として、`DotFileProcessor`クラスの肥大化を解消するため、ラベル生成ロジックを専門クラスに分離する必要があります。Phase 2-1で`UrnProcessor`の抽出が完了しており、次のステップとして`NodeLabelGenerator`クラスの抽出を実施します。

### 目的

リソースタイプに応じたノードラベル生成ロジックを担当する`NodeLabelGenerator`クラスを新規作成し、Single Responsibility Principle（単一責任の原則）に基づいた責務の明確な分離を実現します。

### ビジネス価値

- **保守性の向上**: クラスの責務が明確になり、コードの理解と変更が容易になる
- **テスト容易性の向上**: ラベル生成ロジックを独立してテスト可能
- **拡張性の向上**: カスタムラベルフォーマットの追加が容易になる

### 技術的価値

- **Single Responsibility Principle遵守**: 1クラス1責務の原則に基づいた設計
- **コード再利用性**: ラベル生成ロジックを他のモジュールから利用可能
- **リファクタリングの継続性**: Phase 2-1の成功パターンを踏襲し、Phase 2-3への準備を整える

---

## 🎯 2. 機能要件

### FR-1: NodeLabelGeneratorクラスの新規作成【高】

**要件**: リソースタイプに応じたラベル生成を担当する`NodeLabelGenerator`クラスを新規作成する。

**詳細**:
- ファイルパス: `src/node_label_generator.py`
- クラス名: `NodeLabelGenerator`
- 設計方針: 静的メソッド（ステートレス設計）
- 依存関係: `UrnProcessor`クラスを利用

**受け入れ基準**:
```gherkin
Given NodeLabelGeneratorクラスが作成されている
When インポートして利用する
Then エラーなく読み込まれること
And すべてのメソッドが静的メソッドであること
```

---

### FR-2: スタックノードラベル生成機能【高】

**要件**: Pulumiスタックリソース用のラベルを生成する機能を実装する。

**詳細**:
- メソッド名: `generate_stack_node_label(urn_info: Dict[str, str]) -> str`
- 入力: URN情報辞書（UrnProcessor.parse_urn()の戻り値）
- 出力: スタック用のDOT形式ノード属性文字列
- フォーマット: `label="Stack\n{stack_name}", fillcolor="#D1C4E9", color="#512DA8", shape=ellipse, fontsize="14"`

**受け入れ基準**:
```gherkin
Given スタックリソースのURN情報が与えられた
When generate_stack_node_label()を呼び出す
Then スタック名を含むラベル文字列が返されること
And 固定色（#D1C4E9, #512DA8）が設定されていること
And 楕円形（ellipse）のshapeが指定されていること
And フォントサイズが14であること
```

---

### FR-3: リソースノードラベル生成機能【高】

**要件**: AWS、Azure、GCPなどのクラウドリソース用のラベルを生成する機能を実装する。

**詳細**:
- メソッド名: `generate_resource_node_label(urn_info: Dict[str, str]) -> str`
- 入力: URN情報辞書
- 出力: リソース用のDOT形式ノード属性文字列
- プロバイダー別色設定: `DotFileGenerator.PROVIDER_COLORS`から取得
- フォーマット: `label="{module}\n{type}\n{name}", fillcolor="{fillcolor}", color="{color}", shape=box, fontsize="11"`

**受け入れ基準**:
```gherkin
Given リソースのURN情報が与えられた
When generate_resource_node_label()を呼び出す
Then UrnProcessor.create_readable_label()で生成されたラベルが含まれること
And プロバイダーに応じた色設定が適用されていること
And box形状のshapeが指定されていること
And フォントサイズが11であること
```

---

### FR-4: プロバイダー別色設定管理【高】

**要件**: プロバイダー（AWS、Azure、GCP等）に応じた色設定を管理する。

**詳細**:
- 色設定の参照元: `DotFileGenerator.PROVIDER_COLORS`
- サポートするプロバイダー: aws, azure, azuread, gcp, google, kubernetes, docker, pulumi, random, tls, github, cloudflare, datadog, postgresql, mysql, vault
- デフォルト色: `#E3F2FD`（fillcolor）、`#1565C0`（color）

**受け入れ基準**:
```gherkin
Given 定義済みプロバイダー（例: aws）のURN情報が与えられた
When generate_resource_node_label()を呼び出す
Then プロバイダー固有の色設定が適用されること

Given 未定義プロバイダーのURN情報が与えられた
When generate_resource_node_label()を呼び出す
Then デフォルト色設定が適用されること
```

---

### FR-5: ラベルエスケープ処理【高】

**要件**: DOT形式で特殊な意味を持つ文字を適切にエスケープする。

**詳細**:
- エスケープ対象: ダブルクォート（`"`）、バックスラッシュ（`\`）、改行（`\n`）、タブ（`\t`）
- エスケープ方法: `DotFileGenerator.escape_dot_string()`を利用

**受け入れ基準**:
```gherkin
Given 特殊文字を含むリソース名が与えられた
When ラベル生成を行う
Then すべての特殊文字が正しくエスケープされていること
And DOT形式として有効な文字列が生成されること
```

---

### FR-6: 長いラベルの省略処理【中】

**要件**: 過度に長いラベルを省略記号（...）で短縮する。

**詳細**:
- 省略基準: ラベル全体が40文字を超える場合
- 省略方法: リソース名を30文字まで切り詰め、`...`を追加
- UrnProcessorの処理結果を尊重: タイプ名の省略は`UrnProcessor._format_resource_type()`で処理済み

**受け入れ基準**:
```gherkin
Given 40文字を超えるラベルが生成される場合
When ラベル生成を行う
Then ラベルが適切に省略されること
And 省略記号（...）が含まれること

Given 40文字以下のラベルの場合
When ラベル生成を行う
Then 省略されずに全体が表示されること
```

---

### FR-7: DotFileProcessorからの呼び出し更新【高】

**要件**: `DotFileProcessor`クラスから`NodeLabelGenerator`を利用するように変更する。

**詳細**:
- 抽出対象メソッド:
  - `_generate_node_attributes()` → `NodeLabelGenerator.generate_node_label()`に移行
  - `_generate_stack_node_attributes()` → `NodeLabelGenerator.generate_stack_node_label()`に移行
  - `_generate_resource_node_attributes()` → `NodeLabelGenerator.generate_resource_node_label()`に移行
- 更新が必要な呼び出し箇所:
  - `_process_node_definition()`メソッド

**受け入れ基準**:
```gherkin
Given DotFileProcessorからラベル生成が必要な場合
When _process_node_definition()が呼び出される
Then NodeLabelGeneratorのメソッドが呼び出されること
And 既存の動作が維持されていること
```

---

### FR-8: カスタムラベル対応【低】

**要件**: リソースタイプごとにカスタムラベルフォーマットを適用できる拡張可能な設計を行う。

**詳細**:
- 設計方針: 将来の拡張を見据えた基本実装
- 初期実装: 基本的なラベルフォーマットのみ実装
- 拡張ポイント: メソッドのオーバーライドまたは設定辞書の追加で対応可能

**受け入れ基準**:
```gherkin
Given 将来的にカスタムラベルフォーマットを追加する必要がある場合
When コードを確認する
Then 拡張ポイントが明確にドキュメント化されていること
And 既存コードの大幅な変更なしに拡張可能であること
```

---

## 🔒 3. 非機能要件

### NFR-1: パフォーマンス要件

- **応答時間**: ラベル生成は1リソースあたり10ミリ秒以内
- **スケーラビリティ**: 1000リソースのラベル生成を10秒以内に完了
- **メモリ使用量**: ラベル生成処理で追加のメモリ使用量は100MB以下

**検証方法**:
```python
# パフォーマンステスト例
import time
start = time.time()
for i in range(1000):
    NodeLabelGenerator.generate_resource_node_label(urn_info)
elapsed = time.time() - start
assert elapsed < 10  # 10秒以内
```

---

### NFR-2: セキュリティ要件

- **入力検証**: URN情報辞書の必須キー（type, name）の存在確認
- **エスケープ処理**: DOTインジェクション攻撃への対策（ダブルクォート、バックスラッシュのエスケープ）
- **エラーハンドリング**: 不正な入力に対してもクラッシュせず、デフォルト値を返す

---

### NFR-3: 可用性・信頼性要件

- **エラー耐性**: 不正なURN情報が与えられてもエラーを投げず、安全なデフォルト値を返す
- **冪等性**: 同じ入力に対して常に同じ出力を返す
- **副作用なし**: 静的メソッド設計により、グローバル状態への依存や変更がない

---

### NFR-4: 保守性・拡張性要件

- **コード可読性**: PEP 8に準拠し、すべてのメソッドにdocstringを記載
- **テスト容易性**: 単体テストカバレッジ80%以上
- **拡張性**: 新規プロバイダーの色設定追加が容易（PROVIDER_COLORSに1行追加するだけ）
- **疎結合**: UrnProcessorへの依存のみ、他のクラスへの直接依存なし

---

## ⚙️ 4. 制約事項

### 技術的制約

1. **Python 3.8以上**: 型ヒント（typing）を活用
2. **既存コードとの整合性**: `DotFileProcessor`、`UrnProcessor`との統合が必要
3. **DOT形式準拠**: Graphviz DOT言語の仕様に準拠したラベル生成
4. **既存のPROVIDER_COLORS利用**: `DotFileGenerator.PROVIDER_COLORS`を参照（2重管理を避ける）

### リソース制約

1. **時間制約**: 実装期間は10~14時間（Planning Documentの見積もり）
2. **人員制約**: 単独開発（AI Agent）
3. **依存関係**: Phase 2-1 (UrnProcessor) が完了済みであること

### ポリシー制約

1. **コーディング規約**: プロジェクトの[CLAUDE.md](../../../../CLAUDE.md)に準拠
2. **テスト要件**: 単体テストカバレッジ80%以上が必須
3. **ドキュメント**: すべてのパブリックメソッドにdocstringを記載（Google Style推奨）

---

## 📦 5. 前提条件

### システム環境

- **Python**: 3.8以上
- **テストフレームワーク**: pytest 7.0以上
- **依存パッケージ**: なし（標準ライブラリのみ使用）

### 依存コンポーネント

1. **UrnProcessor** (Phase 2-1で完成): URN解析、ラベル生成補助
2. **DotFileGenerator**: PROVIDER_COLORS定義の参照
3. **DotFileProcessor**: NodeLabelGeneratorを呼び出す

### 外部システム連携

- なし（内部モジュール間の連携のみ）

---

## ✅ 6. 受け入れ基準

### AC-1: NodeLabelGeneratorクラスの動作確認

```gherkin
Given NodeLabelGeneratorクラスが実装されている
When 以下のメソッドを呼び出す
  - generate_stack_node_label(urn_info)
  - generate_resource_node_label(urn_info)
Then すべてのメソッドがエラーなく実行されること
And 各メソッドがDOT形式の属性文字列を返すこと
```

---

### AC-2: 単体テストのカバレッジ

```gherkin
Given test_node_label_generator.pyが実装されている
When pytest --cov=node_label_generator --cov-report=termを実行する
Then カバレッジが80%以上であること
And すべてのテストがパスすること
```

---

### AC-3: 既存の統合テストの互換性

```gherkin
Given 既存のtest_dot_processor.pyが存在する
When pytest tests/test_dot_processor.pyを実行する
Then すべてのテストがパスすること
And ラベル生成結果が既存実装と一致すること
```

---

### AC-4: DotFileProcessorとの統合

```gherkin
Given DotFileProcessorがNodeLabelGeneratorを利用するように更新されている
When DotFileProcessor._process_node_definition()を呼び出す
Then NodeLabelGeneratorのメソッドが正しく呼び出されること
And 既存のDOT形式出力が維持されていること
```

---

### AC-5: プロバイダー別色設定の動作確認

```gherkin
Given 各プロバイダー（aws, azure, gcp）のURN情報が与えられた
When generate_resource_node_label()を呼び出す
Then プロバイダー固有の色設定が適用されること

Given 未定義プロバイダーのURN情報が与えられた
When generate_resource_node_label()を呼び出す
Then デフォルト色設定が適用されること
```

---

### AC-6: エッジケースの処理

```gherkin
Given 以下のエッジケースが与えられた
  - 空文字列のリソース名
  - 特殊文字（"、\、改行、タブ）を含むリソース名
  - 極端に長いリソース名（1000文字）
  - 不正なURN情報（必須キーの欠落）
When ラベル生成を行う
Then エラーが発生せず、安全な出力が返されること
```

---

### AC-7: ドキュメントの完全性

```gherkin
Given node_label_generator.pyが実装されている
When ファイルを確認する
Then 以下のドキュメントが存在すること
  - ファイルレベルのdocstring（モジュールの目的、主要機能）
  - クラスレベルのdocstring（責務、設計方針）
  - すべてのパブリックメソッドのdocstring（引数、戻り値、使用例）
```

---

## 🚫 7. スコープ外

### 明確にスコープ外とする事項

1. **DOT形式の解析**: 入力として受け取るのはURN情報のみ（DOT文字列の解析はしない）
2. **グラフ構造の生成**: ノードラベルのみを担当（エッジ、依存関係は対象外）
3. **色設定の動的変更**: 実行時の色設定変更機能は対象外（PROVIDER_COLORSは静的定義）
4. **ラベルの国際化（i18n）**: 英語のみサポート
5. **画像やアイコンの埋め込み**: テキストベースのラベルのみ
6. **ラベルの動的生成**: メタデータ（作成日時、タグなど）に基づくラベル生成は対象外

### 将来的な拡張候補

1. **高度なカスタムラベルフォーマット**: リソースタイプごとの詳細なカスタマイズ（FR-8の拡張）
2. **ラベルテンプレートエンジン**: Jinja2などのテンプレートエンジンの統合
3. **プロバイダー色設定の外部ファイル化**: YAML/JSONによる色設定の外部管理
4. **ラベル長の自動調整**: グラフ全体のレイアウトに応じたラベル長の動的調整

---

## 📊 8. 補足情報

### 参考実装

- **UrnProcessor** (Phase 2-1): 静的メソッド設計、詳細なdocstring、エッジケース処理のベストプラクティス
- **DotFileGenerator**: PROVIDER_COLORS定義、DOT形式生成ロジック

### 関連ドキュメント

- [CLAUDE.md](../../../../CLAUDE.md): プロジェクトのコーディングガイドライン
- [ARCHITECTURE.md](../../../../ARCHITECTURE.md): アーキテクチャ設計思想
- [Planning Document](../../00_planning/output/planning.md): Phase 2-2の開発計画

### 実装順序の推奨

1. **Phase 1 (本ドキュメント)**: 要件定義の完了とレビュー
2. **Phase 2**: 設計書の作成（クラス図、メソッドシグネチャ、責務の明確化）
3. **Phase 3**: テストシナリオの作成（単体テスト、統合テスト）
4. **Phase 4**: 実装（NodeLabelGenerator新規作成、DotFileProcessor更新）
5. **Phase 5**: テストコード実装（test_node_label_generator.py新規作成）
6. **Phase 6**: テスト実行（カバレッジ80%以上の確認）
7. **Phase 7**: ドキュメント作成（docstring完全性の確認）
8. **Phase 8**: 完了レポート作成

---

## ✅ 品質ゲート（Phase 1）

本要件定義書は、以下の品質ゲートを満たしています：

- [x] **機能要件が明確に記載されている**: FR-1〜FR-8で具体的な機能要件を定義
- [x] **受け入れ基準が定義されている**: AC-1〜AC-7でGiven-When-Then形式の受け入れ基準を記載
- [x] **スコープが明確である**: スコープ外の項目を明示的にリストアップ
- [x] **論理的な矛盾がない**: Planning Documentの戦略と整合性を確認済み

---

**次のフェーズ**: Phase 2（設計）に進んでください。

**クリティカルシンキングレビュー**: 本要件定義書は、Planning Documentで定義された品質ゲートを満たしており、Phase 2への移行準備が整っています。
