# 要件定義書 - Issue #536

## 0. Planning Documentの確認

Planning Phaseで以下が明確化されました：

- **実装戦略**: REFACTOR（新機能追加ではなく、既存のTokenEstimatorクラスの正しい使用方法への修正）
- **テスト戦略**: UNIT_INTEGRATION（ユニットテストと統合テストの両方が必要）
- **テストコード戦略**: EXTEND_TEST（既存のテストファイルにエッジケースのテストを追加）
- **複雑度**: 簡単（単一の実装パターンエラー）
- **見積もり工数**: 3~4時間
- **リスク評価**: 低

この要件定義はPlanning Documentの戦略に基づいて策定します。

## 1. 概要

### 背景
pr_comment_generator.pyでPRのコメント生成処理において、TokenEstimatorクラスの使用方法が間違っているため、`TokenEstimator.estimate_tokens() missing 1 required positional argument: 'text'`エラーが発生しています。

### 目的
TokenEstimatorクラスを正しいインスタンスベースの使用方法に修正し、PRコメント生成機能を正常に動作させる。

### ビジネス価値・技術的価値
- **ビジネス価値**: PRコメント生成機能の復旧により、開発チームの生産性向上とコードレビュー効率化を実現
- **技術的価値**: 設計意図通りのインスタンスベース使用によるコードの一貫性向上、保守性の改善

## 2. 機能要件

| ID | 要件名 | 説明 | 優先度 |
|----|-------|------|--------|
| FR001 | TokenEstimatorインスタンス化の修正 | openai_client.pyクラスでTokenEstimatorのインスタンスを作成・保持する | 高 |
| FR002 | メソッド呼び出しパターンの修正 | 11箇所のクラスメソッド呼び出しをインスタンスメソッド呼び出しに変更 | 高 |
| FR003 | メソッド名の修正 | truncate_to_token_limit → truncate_textメソッド名変更 | 高 |
| FR004 | エラーハンドリング強化 | TokenEstimator関連のエラーハンドリングを追加 | 中 |
| FR005 | ログ出力改善 | TokenEstimator関連のログ出力を明確化 | 低 |

## 3. 非機能要件

### 3.1 パフォーマンス要件
- TokenEstimatorインスタンス化によるメモリ使用量増加は軽微である（TokenEstimatorクラス自体が軽量）
- 既存の処理性能を維持する（遅延初期化パターンも検討可能）

### 3.2 信頼性要件
- 修正後も既存のトークン推定精度を維持する
- エラー発生時は適切なエラーメッセージを出力する

### 3.3 保守性要件
- 設計意図通りのインスタンスベース使用により、将来の拡張性を確保する
- 既存のユニットテストパターンと整合性を保つ

### 3.4 互換性要件
- 後方互換性への影響なし（internal APIの修正のため）
- 既存の統合テストが引き続き動作する

## 4. 制約事項

### 4.1 技術的制約
- TokenEstimatorクラス自体の設計変更は不可（インスタンスメソッドとして設計されている）
- token_estimator.pyモジュールの修正は不要（既存実装が正しい）
- 既存のインポート文は変更不要

### 4.2 時間的制約
- 見積もり工数: 3~4時間以内
- 緊急性: 中（PRコメント生成機能の不具合）

### 4.3 テスト制約
- 既存のtest_token_estimator.pyは正しい使用パターンを示しているため変更不要
- 新規テストファイル作成は不要（既存テストの拡張で対応）

## 5. 前提条件

### 5.1 システム環境
- Python環境でのpr_comment_generator実行環境
- OpenAI APIキーが適切に設定されている
- Jenkins CI/CD環境での実行可能性

### 5.2 依存コンポーネント
- pr_comment_generator.token_estimator: 既存実装（修正不要）
- 既存のテストスイート（test_token_estimator.py）

### 5.3 外部システム連携
- 外部システム連携への影響なし（internal APIの修正）

## 6. 受け入れ基準

### 6.1 エラー修正の受け入れ基準
```
Given: openai_client.pyでTokenEstimatorが使用される場合
When: pr_comment_generator.pyを実行した時
Then: "TokenEstimator.estimate_tokens() missing 1 required positional argument"エラーが発生しない
```

### 6.2 正常動作の受け入れ基準
```
Given: 修正されたTokenEstimator使用箇所において
When: estimate_tokensメソッドまたはtruncate_textメソッドが呼び出される時
Then: 正常にトークン推定およびテキスト切り詰め処理が実行される
```

### 6.3 インスタンス化の受け入れ基準
```
Given: openai_clientクラスが初期化される場合
When: TokenEstimatorインスタンスが作成される時
Then: エラーなく正常にインスタンス化され、後続処理で使用可能になる
```

### 6.4 メソッド名修正の受け入れ基準
```
Given: 修正対象箇所でtruncate_to_token_limitメソッドが呼び出されていた場合
When: truncate_textメソッドに名前変更される時
Then: 同等の機能で正常に動作し、例外が発生しない
```

### 6.5 既存機能保持の受け入れ基準
```
Given: 既存のユニットテストが存在する場合
When: 修正後にテストスイートを実行する時
Then: 全ての既存テストが成功し、新機能のテストも追加される
```

### 6.6 統合動作の受け入れ基準
```
Given: 実際のPRファイルが与えられた場合
When: pr_comment_generatorの全体処理を実行する時
Then: エラーなくPRコメントが正常に生成される
```

## 7. スコープ外

### 7.1 対象外機能
- TokenEstimatorクラス自体の機能追加・変更
- トークン推定アルゴリズムの改善
- 新しいテストファイルの作成
- OpenAI API呼び出し部分の変更
- プロンプト管理機能の変更

### 7.2 将来的な拡張候補
- TokenEstimatorの遅延初期化パターンの採用
- より詳細なトークン使用量監視機能
- トークン推定精度の向上

## 8. 品質ゲート（Phase 1）確認

- ✅ **機能要件が明確に記載されている**: FR001-005として具体的に定義
- ✅ **受け入れ基準が定義されている**: 6項目のGiven-When-Then形式で定義
- ✅ **スコープが明確である**: 対象範囲（openai_client.py修正）と対象外（TokenEstimator自体の変更）を明確化
- ✅ **論理的な矛盾がない**: Planning Documentの戦略（REFACTOR）と整合性あり

## 9. 修正対象箇所詳細

Planning Documentで特定された修正対象箇所：

### 9.1 主要修正対象ファイル
- `jenkins/jobs/pipeline/docs-generator/pull-request-comment-builder/src/pr_comment_generator/openai_client.py`

### 9.2 具体的修正箇所
1. **Line 607, 613, 618**: `truncate_to_token_limit`呼び出し修正
2. **Line 806, 815, 825, 832**: `estimate_tokens`呼び出し修正
3. **Line 1000, 1018**: `estimate_tokens`呼び出し修正
4. **Line 1134, 1157**: `truncate_to_token_limit`呼び出し修正

### 9.3 修正パターン
- **修正前**: `TokenEstimator.method_name(params)`（クラスメソッド呼び出し）
- **修正後**: `estimator.method_name(params)`（インスタンスメソッド呼び出し）
- **メソッド名**: `truncate_to_token_limit` → `truncate_text`

## 10. テスト拡張要件

Planning Documentのテスト戦略（EXTEND_TEST）に基づく拡張要件：

### 10.1 ユニットテスト拡張
- test_token_estimator.pyにエッジケースを追加
  - 空文字列処理
  - 非常に大きなテキストの処理
  - 特殊文字を含むテキストの処理

### 10.2 統合テスト追加
- openai_clientとTokenEstimatorの統合動作テスト
- テスト用モックを活用した統合テスト

この要件定義書に基づき、Phase 2（設計フェーズ）では詳細な実装設計を行います。