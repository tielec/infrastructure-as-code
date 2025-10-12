# 要件定義書 - Issue #360

## プロジェクト情報

- **Issue番号**: #360
- **タイトル**: [FEATURE] AIワークフロー実行時のレジューム機能実装
- **状態**: open
- **URL**: https://github.com/tielec/infrastructure-as-code/issues/360
- **ラベル**: enhancement
- **作成日**: 2025-10-12

---

## 0. Planning Documentの確認

### 開発計画の全体像

**実装戦略**: **EXTEND**
- 新規モジュール `scripts/ai-workflow/utils/resume.py` の作成
- 既存ファイル `main.py`, `metadata.py` の拡張
- 既存アーキテクチャの維持、後方互換性の保持

**テスト戦略**: **UNIT_INTEGRATION**
- ユニットテスト: `ResumeManager`クラスの各メソッドのロジック検証
- インテグレーションテスト: `main.py execute --phase all` との統合動作確認

**テストコード戦略**: **CREATE_TEST**
- 新規テストファイル作成: `test_resume.py`, `test_resume_integration.py`

**見積もり総工数**: 約12時間

**主要なリスク**:
1. メタデータ状態の複雑性（影響度: 中、確率: 中）
2. 既存ワークフローへの影響（影響度: 低、確率: 低）
3. `clear()`メソッドの破壊的操作（影響度: 高、確率: 低）
4. Phase 0（planning）フェーズとの混同（影響度: 中、確率: 中）
5. パフォーマンス低下（影響度: 低、確率: 低）

---

## 1. 概要

### 背景

現在のAIワークフローシステムでは、`--phase all`で全フェーズ（Phase 1-8）を実行中に途中のフェーズ（例: Phase 5）で失敗した場合、再度`--phase all`を実行すると最初（Phase 1）から実行し直す必要がある。

この問題により以下の課題が発生している：

1. **時間の無駄**: 既に完了したPhase 1-4を再実行する必要があり、数十分〜数時間の時間が無駄になる
2. **リソースの無駄**: Claude API呼び出しが重複し、APIクォータとコストが増加する
3. **作業効率の低下**: 開発者が手動で`--phase N`を指定して途中フェーズから実行する必要がある
4. **ユーザー体験の悪化**: エラーが発生するたびに最初からやり直す必要があり、ストレスが増加する

### 目的

メタデータJSON (`.ai-workflow/issue-XXX/metadata.json`) に記録されている各フェーズのステータス情報を活用し、**失敗したフェーズから自動的に再開するレジューム機能**を実装する。

### ビジネス価値

- **開発効率の向上**: 既に完了したフェーズの再実行が不要になり、開発者の時間を節約
- **コスト削減**: Claude API呼び出しの重複を削減し、APIコストを最小化
- **ユーザー体験の改善**: 自動レジュームによりストレスフリーなワークフロー実行を実現

### 技術的価値

- **既存資産の活用**: メタデータJSONの状態管理機能を有効活用
- **拡張性の向上**: レジューム機能により長時間実行ワークフローの信頼性が向上
- **保守性の向上**: `ResumeManager`クラスによる関心の分離

---

## 2. 機能要件

### FR-01: デフォルトでの自動レジューム機能（優先度: 高）

**要件**:
`--phase all`実行時、既存のメタデータが存在する場合、デフォルトで自動的にレジューム処理を行う。

**詳細**:
- メタデータJSONが存在し、かつ全フェーズが完了していない場合、自動レジュームを実行
- 完了済みフェーズ、失敗フェーズ、進行中フェーズ、未実行フェーズをログに表示
- レジューム開始フェーズをユーザーに明示

**受け入れ基準**:
- **Given**: メタデータJSONが存在し、Phase 1-4が完了、Phase 5が失敗
- **When**: `python scripts/ai-workflow/main.py --issue 360 --phase all`を実行
- **Then**:
  - ログに「既存ワークフローを検出しました」と表示される
  - ログに「Phase 1-4: completed」と表示される
  - ログに「Phase 5: failed」と表示される
  - ログに「Phase 5から自動的に再開します...」と表示される
  - Phase 5から実行が開始される
  - Phase 1-4は実行されない

### FR-02: 強制リセットフラグ（--force-reset）（優先度: 高）

**要件**:
`--force-reset`フラグを使用することで、既存のメタデータをクリアし、最初から全フェーズを実行できる。

**詳細**:
- `--force-reset`フラグはboolean型（指定なし=False、指定あり=True）
- フラグ指定時、メタデータJSONファイルを削除
- フラグ指定時、ワークフローディレクトリ全体を削除（オプション）
- 削除後、Phase 1から新規ワークフローとして実行

**受け入れ基準**:
- **Given**: メタデータJSONが存在し、Phase 1-4が完了
- **When**: `python scripts/ai-workflow/main.py --issue 360 --phase all --force-reset`を実行
- **Then**:
  - ログに「--force-reset指定により、ワークフローを最初から実行します」と表示される
  - ログに「既存のメタデータをクリアしました」と表示される
  - メタデータJSONファイルが削除される
  - Phase 1から実行が開始される

### FR-03: レジューム開始フェーズの優先順位決定（優先度: 高）

**要件**:
メタデータJSONの状態に基づき、以下の優先順位でレジューム開始フェーズを決定する。

**優先順位**:
1. **failedフェーズ**: 最初に失敗したフェーズから再開
2. **in_progressフェーズ**: 異常終了したフェーズから再開
3. **pendingフェーズ**: 最初の未実行フェーズから再開
4. **全フェーズcompleted**: 既に完了済みメッセージを表示して終了

**受け入れ基準**:
- **Given**: Phase 3: failed, Phase 5: failed, Phase 7: pending
- **When**: レジューム機能を実行
- **Then**: Phase 3から再開される（最初のfailedフェーズ）

- **Given**: Phase 3: in_progress, Phase 5: pending
- **When**: レジューム機能を実行
- **Then**: Phase 3から再開される（in_progressフェーズ）

- **Given**: Phase 1-5: completed, Phase 6-8: pending
- **When**: レジューム機能を実行
- **Then**: Phase 6から再開される（最初のpendingフェーズ）

- **Given**: Phase 1-8: completed
- **When**: レジューム機能を実行
- **Then**:
  - ログに「ワークフローは既に完了しています」と表示される
  - ログに「再実行する場合は --force-reset を使用してください」と表示される
  - 実行は終了する（Phase実行なし）

### FR-04: エッジケースの処理（優先度: 中）

**要件**:
メタデータ不存在、メタデータ破損など、エッジケースに適切に対応する。

**ケース1: メタデータJSON不存在**
- **Given**: `.ai-workflow/issue-360/metadata.json`が存在しない
- **When**: `--phase all`を実行
- **Then**: 新規ワークフローとしてPhase 1から実行

**ケース2: メタデータJSON破損**
- **Given**: メタデータJSONが破損しており、JSONパースエラーが発生
- **When**: `--phase all`を実行
- **Then**:
  - ログに警告「メタデータファイルが破損しています。新規ワークフローとして実行します。」を表示
  - 新規ワークフローとしてPhase 1から実行

**ケース3: Phase 0（planning）フェーズの扱い**
- **Given**: `execute_all_phases()`関数がPlanningフェーズを含むか不明確
- **When**: レジューム機能を実装
- **Then**:
  - README.mdの記述に従い、`--phase all`は「Phase 1-8」を指すものとする
  - Planningフェーズ（Phase 0）はレジューム対象外とする
  - ドキュメントとコードの一貫性を確保

### FR-05: レジューム状態のログ出力（優先度: 中）

**要件**:
レジューム処理の状態を明確にログ出力し、ユーザーが現在の状況を把握できるようにする。

**詳細**:
- 完了済みフェーズのリスト
- 失敗フェーズのリスト
- 進行中フェーズのリスト
- 未実行フェーズのリスト
- レジューム開始フェーズの明示

**受け入れ基準**:
- **Given**: Phase 1-4: completed, Phase 5: failed, Phase 6-8: pending
- **When**: レジューム機能を実行
- **Then**: ログに以下が表示される
  ```
  [INFO] 既存ワークフローを検出しました
  [INFO] 完了: requirements, design, test_scenario, implementation
  [INFO] 失敗: test_implementation
  [INFO] test_implementationから自動的に再開します...
  ```

### FR-06: MetadataManager.clear()メソッドの実装（優先度: 高）

**要件**:
`MetadataManager`クラスに`clear()`メソッドを追加し、メタデータとワークフローディレクトリを削除する機能を実装する。

**詳細**:
- メタデータJSONファイルを削除
- ワークフローディレクトリ全体を削除（オプション、デフォルトは削除する）
- 削除実行前にログで警告を表示
- 削除対象ファイル/ディレクトリが存在しない場合はスキップ（エラーなし）

**受け入れ基準**:
- **Given**: `.ai-workflow/issue-360/metadata.json`が存在
- **When**: `metadata.clear()`を実行
- **Then**:
  - ログに「メタデータをクリアしました: .ai-workflow/issue-360/metadata.json」と表示される
  - メタデータJSONファイルが削除される
  - ワークフローディレクトリ全体が削除される
  - 削除後、ディレクトリが存在しないことが確認できる

---

## 3. 非機能要件

### NFR-01: パフォーマンス要件

**要件**:
レジューム判定処理は`--phase all`の起動時間に大きな影響を与えないこと。

**詳細**:
- レジューム判定処理の追加オーバーヘッドは1秒未満であること
- メタデータ読み込みは既存処理で実施済みのため、追加コストは最小限
- レジューム判定ロジックはシンプルなループ処理のみ（複雑な計算なし）

**計測方法**:
- Phase 6（テスト実行）でパフォーマンス測定を実施
- `--phase all`の起動時間を計測（レジューム判定を含む）
- レジューム機能なしの場合と比較し、差分が1秒未満であることを確認

### NFR-02: 信頼性要件

**要件**:
メタデータ読み込みエラーやファイルシステムエラーが発生しても、システムが適切に動作すること。

**詳細**:
- メタデータJSON破損時も新規ワークフローとして継続実行
- ファイルI/Oエラー時は適切なエラーメッセージを表示
- 例外処理により予期しない終了を防止

**受け入れ基準**:
- メタデータ破損時にシステムがクラッシュしない
- エラーメッセージが明確でユーザーが対処方法を理解できる

### NFR-03: 保守性要件

**要件**:
レジューム機能は`ResumeManager`クラスとして独立して実装され、既存コードへの影響を最小限にすること。

**詳細**:
- `ResumeManager`クラスは`scripts/ai-workflow/utils/resume.py`に配置
- 既存の`WorkflowMetadata`クラスを活用し、重複実装を避ける
- `main.py`の変更は最小限（レジューム判定ロジックの呼び出しのみ）
- コードコメントを適切に記載（各メソッドの目的、引数、戻り値）

**受け入れ基準**:
- `ResumeManager`クラスが単体でテスト可能
- 既存の`WorkflowMetadata`クラスのインターフェースを変更しない（`clear()`メソッド追加のみ）
- コードレビューで保守性が承認される

### NFR-04: 後方互換性要件

**要件**:
既存のワークフローに影響を与えず、既存の`metadata.json`ファイルと互換性を維持すること。

**詳細**:
- メタデータJSON構造の変更なし
- 既存の`metadata.json`ファイルをそのまま読み込み可能
- `--phase all`のデフォルト動作が変わることをREADME.mdで明記

**受け入れ基準**:
- 既存の`metadata.json`ファイルでレジューム機能が正常に動作
- 既存ワークフローとの互換性テストがパス

### NFR-05: セキュリティ要件

**要件**:
`clear()`メソッドの破壊的操作によるデータ損失を防止すること。

**詳細**:
- `--force-reset`フラグを明示的に指定した場合のみ`clear()`を実行
- 削除実行前にログで警告メッセージを表示
- 削除対象が意図しないディレクトリでないことを検証（パス検証）

**受け入れ基準**:
- `--force-reset`フラグなしで`clear()`が実行されない
- 削除前にログで警告が表示される
- Phase 5（テストコード実装）で`clear()`の動作が十分にテストされる

---

## 4. 制約事項

### 技術的制約

1. **Python標準ライブラリの使用**: 新規依存パッケージの追加は不可
   - 既存の`pathlib`, `json`, `typing`モジュールのみ使用
   - 外部ライブラリ依存を避ける

2. **既存アーキテクチャの維持**: メタデータJSON構造の変更は不可
   - `WorkflowMetadata`クラスの既存インターフェースを維持
   - 新規フィールド追加は避ける

3. **Phase 0（planning）フェーズの扱い**:
   - README.mdの記述に従い、`--phase all`は「Phase 1-8」を指す
   - Planningフェーズはレジューム対象外

### リソース制約

1. **開発期間**: 約12時間（見積もり）
2. **開発者**: 1名（AI支援）
3. **テスト環境**: 開発者ローカル環境のみ

### ポリシー制約

1. **コーディング規約**: CLAUDE.mdのガイドラインに準拠
   - コメントは日本語
   - ドキュメントは日本語
   - 変数名、関数名は英語（camelCase/snake_case）

2. **テスト要件**:
   - ユニットテストカバレッジ90%以上
   - 統合テストで主要ユースケースをカバー

---

## 5. 前提条件

### システム環境

1. **Python環境**: Python 3.8以上
2. **ファイルシステム**: POSIX準拠（Linux, macOS）またはWindows
3. **パーミッション**: ワークフローディレクトリへの読み書き権限

### 依存コンポーネント

1. **既存モジュール**:
   - `scripts/ai-workflow/utils/metadata.py` - `WorkflowMetadata`クラス
   - `scripts/ai-workflow/core/workflow_state.py` - フェーズ定義
   - `scripts/ai-workflow/main.py` - エントリーポイント

2. **メタデータJSON**: `.ai-workflow/issue-XXX/metadata.json`
   - 各フェーズのステータス（pending/in_progress/completed/failed）
   - 出力ファイルパス
   - エラーメッセージ（失敗時）

### 外部システム連携

- なし（スタンドアロン機能）

---

## 6. 受け入れ基準

### AC-01: 自動レジューム機能の動作確認

- **Given**: Phase 1-4が完了、Phase 5が失敗、Phase 6-8が未実行
- **When**: `python scripts/ai-workflow/main.py --issue 360 --phase all`を実行
- **Then**:
  - Phase 5から実行が開始される
  - Phase 1-4は実行されない
  - ログに完了フェーズ、失敗フェーズ、レジューム開始フェーズが表示される

### AC-02: 強制リセット機能の動作確認

- **Given**: Phase 1-4が完了、Phase 5が失敗
- **When**: `python scripts/ai-workflow/main.py --issue 360 --phase all --force-reset`を実行
- **Then**:
  - メタデータJSONが削除される
  - ワークフローディレクトリが削除される
  - Phase 1から実行が開始される

### AC-03: 全フェーズ完了時の動作確認

- **Given**: Phase 1-8がすべて完了
- **When**: `python scripts/ai-workflow/main.py --issue 360 --phase all`を実行
- **Then**:
  - ログに「ワークフローは既に完了しています」と表示される
  - ログに「再実行する場合は --force-reset を使用してください」と表示される
  - Phase実行は行われない

### AC-04: メタデータ不存在時の動作確認

- **Given**: メタデータJSONが存在しない
- **When**: `python scripts/ai-workflow/main.py --issue 360 --phase all`を実行
- **Then**:
  - 新規ワークフローとしてPhase 1から実行される
  - エラーが発生しない

### AC-05: メタデータ破損時の動作確認

- **Given**: メタデータJSONが破損している（JSONパースエラー）
- **When**: `python scripts/ai-workflow/main.py --issue 360 --phase all`を実行
- **Then**:
  - ログに警告「メタデータファイルが破損しています。新規ワークフローとして実行します。」が表示される
  - 新規ワークフローとしてPhase 1から実行される

### AC-06: ユニットテストと統合テストの実装

- **Given**: レジューム機能が実装されている
- **When**: `pytest tests/unit/test_resume.py`を実行
- **Then**: すべてのユニットテストがパス

- **Given**: レジューム機能が実装されている
- **When**: `pytest tests/integration/test_resume_integration.py`を実行
- **Then**: すべての統合テストがパス

### AC-07: ドキュメントの更新

- **Given**: レジューム機能が実装されている
- **When**: `scripts/ai-workflow/README.md`を確認
- **Then**:
  - レジューム機能の説明が追加されている
  - `--force-reset`フラグの使用方法が記載されている
  - 使用例が追加されている

### AC-08: パフォーマンス要件の確認

- **Given**: レジューム機能が実装されている
- **When**: `--phase all`の起動時間を計測
- **Then**: レジューム判定処理のオーバーヘッドが1秒未満

---

## 7. スコープ外

以下の項目は本Issue（#360）のスコープ外とし、将来的な拡張候補とする：

### 将来的な拡張候補

1. **フェーズ単位でのレジューム**:
   - 現在: `--phase all`のみレジューム対応
   - 将来: `--phase 5-8`など範囲指定でもレジューム対応

2. **レジューム履歴の記録**:
   - レジューム実行回数、レジューム時刻などの履歴をメタデータに記録
   - トラブルシューティングやパフォーマンス分析に活用

3. **対話形式のレジューム確認**:
   - 自動レジュームではなく、ユーザーに確認を求めるオプション
   - `--interactive`フラグで対話形式のレジューム確認を実行

4. **部分的なフェーズクリア**:
   - `--clear-phase 5`など、特定フェーズのみクリアする機能
   - 特定フェーズのみやり直したい場合に有用

5. **レジューム設定のカスタマイズ**:
   - `--resume-strategy`フラグでレジューム戦略を選択
   - 例: `--resume-strategy=from-failed`, `--resume-strategy=from-pending`

### 明確にスコープ外とする項目

1. **メタデータJSON構造の変更**: 既存の互換性を維持するため、構造変更は行わない
2. **Planningフェーズ（Phase 0）のレジューム**: README.mdの記載に従い、対象外とする
3. **並列フェーズ実行**: レジューム機能は順次実行のみ対応（並列実行は将来の拡張）
4. **リモートメタデータ同期**: 複数環境でのメタデータ同期は対象外

---

## 8. 成果物

本要件定義に基づき、以下の成果物を作成する：

### Phase 2（設計）
- [ ] `ResumeManager`クラスの詳細設計（クラス図、メソッドシグネチャ）
- [ ] `main.py`の改修設計（フロー図）
- [ ] `metadata.py`の拡張設計（`clear()`メソッド仕様）
- [ ] エラーハンドリング設計

### Phase 3（テストシナリオ）
- [ ] ユニットテストシナリオ（`ResumeManager`の全メソッド）
- [ ] インテグレーションテストシナリオ（`--phase all`, `--force-reset`）
- [ ] エッジケーステストシナリオ（メタデータ破損、不存在等）

### Phase 4（実装）
- [ ] `scripts/ai-workflow/utils/resume.py` - ResumeManager実装
- [ ] `scripts/ai-workflow/main.py` - レジューム機能統合、`--force-reset`引数追加
- [ ] `scripts/ai-workflow/utils/metadata.py` - `clear()`メソッド追加

### Phase 5（テストコード実装）
- [ ] `scripts/ai-workflow/tests/unit/test_resume.py` - ユニットテスト
- [ ] `scripts/ai-workflow/tests/integration/test_resume_integration.py` - 統合テスト

### Phase 6（テスト実行）
- [ ] すべてのテストがパス
- [ ] カバレッジ90%以上
- [ ] パフォーマンステストがパス

### Phase 7（ドキュメント）
- [ ] `scripts/ai-workflow/README.md` - レジューム機能のドキュメント追加
- [ ] コードコメントの追加・更新

---

## 9. 参考情報

### メタデータJSONの構造例

```json
{
  "issue_number": "360",
  "created_at": "2025-10-12T10:00:00Z",
  "updated_at": "2025-10-12T12:30:00Z",
  "phases": {
    "requirements": {
      "status": "completed",
      "started_at": "2025-10-12T10:00:00Z",
      "completed_at": "2025-10-12T10:15:00Z",
      "output": ".ai-workflow/issue-360/01_requirements/output/requirements.md"
    },
    "design": {
      "status": "completed",
      "started_at": "2025-10-12T10:15:00Z",
      "completed_at": "2025-10-12T10:45:00Z",
      "output": ".ai-workflow/issue-360/02_design/output/design.md"
    },
    "test_scenario": {
      "status": "completed",
      "started_at": "2025-10-12T10:45:00Z",
      "completed_at": "2025-10-12T11:15:00Z",
      "output": ".ai-workflow/issue-360/03_test_scenario/output/test-scenario.md"
    },
    "implementation": {
      "status": "completed",
      "started_at": "2025-10-12T11:15:00Z",
      "completed_at": "2025-10-12T12:00:00Z",
      "output": ".ai-workflow/issue-360/04_implementation/output/"
    },
    "test_implementation": {
      "status": "failed",
      "started_at": "2025-10-12T12:00:00Z",
      "failed_at": "2025-10-12T12:30:00Z",
      "output": null,
      "error": "test-implementation.mdが生成されませんでした"
    },
    "testing": {
      "status": "pending"
    },
    "documentation": {
      "status": "pending"
    },
    "report": {
      "status": "pending"
    }
  }
}
```

### フェーズステータスの定義

- **pending**: 未実行（初期状態）
- **in_progress**: 実行中（異常終了した場合もこの状態のまま残る）
- **completed**: 正常完了
- **failed**: 失敗（エラー発生）

### ResumeManagerの責務範囲

`ResumeManager`クラスは以下の責務を持つ：

1. **レジューム可能性の判定**: `can_resume()` - メタデータが存在し、未完了フェーズがあるか
2. **レジューム開始フェーズの決定**: `get_resume_phase()` - 優先順位に従って開始フェーズを決定
3. **完了状態の判定**: `is_completed()` - 全フェーズが完了しているか
4. **ステータスサマリーの取得**: `get_status_summary()` - 完了、失敗、進行中、未実行のフェーズリスト
5. **メタデータのクリア**: `reset()` - メタデータとワークフローディレクトリを削除

---

## 10. 品質ゲートチェックリスト

本要件定義書は、以下の品質ゲート（Phase 1必須要件）を満たしている：

- [x] **機能要件が明確に記載されている**: FR-01〜FR-06で6つの機能要件を具体的に定義
- [x] **受け入れ基準が定義されている**: AC-01〜AC-08で8つの受け入れ基準をGiven-When-Then形式で定義
- [x] **スコープが明確である**: セクション7「スコープ外」で明確に定義、将来拡張との区別も明示
- [x] **論理的な矛盾がない**:
  - 機能要件と受け入れ基準が対応
  - 非機能要件と制約事項が矛盾なし
  - Planning Documentの戦略と整合

---

**作成日**: 2025-10-12
**作成者**: Claude AI (Phase 1: Requirements)
**レビュー状態**: 未レビュー
**承認者**: -
**承認日**: -
