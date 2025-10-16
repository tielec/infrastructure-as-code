# 要件定義書 - Issue #398

**Issue番号**: #398
**タイトル**: [FOLLOW-UP] Issue #396 - 残タスク
**作成日**: 2025-01-16
**作成者**: AI Requirements Analyst (Phase 1)

---

## 0. Planning Documentの確認

Planning Document (@.ai-workflow/issue-398/00_planning/output/planning.md) を確認し、以下の開発計画を踏まえて要件定義を実施します：

### 開発計画の全体像
- **実装戦略**: EXTEND（既存パターンの拡張適用）
- **テスト戦略**: INTEGRATION_ONLY（手動E2E + 既存自動テストの実行）
- **テストコード戦略**: EXTEND_TEST（既存42ケースを再利用）
- **複雑度**: 中程度
- **見積もり工数**: 6~10時間
- **リスクレベル**: 低

### 戦略の要点
1. **既存パターンの適用が中心**: implementation.tsで実装されたオプショナルコンテキスト構築パターンを、4つのPhaseクラスに適用
2. **既存ヘルパー関数の活用**: `BasePhase.buildOptionalContext`メソッドは既に実装済み
3. **プロンプトファイルの修正**: 置換キーの変更とコメント追加による使用方法の明示
4. **新規ファイル作成は不要**: すべて既存ファイルの修正のみ

---

## 1. 概要

### 1.1 背景

Issue #396において、ai-workflow-v2のプリセット機能拡充と依存関係チェック強化が実装されました。このプロジェクトでは、オプショナルコンテキスト構築機能（`buildOptionalContext`ヘルパー関数）が導入され、implementation.tsで実装されました。

しかし、時間的制約により以下の項目が未完了でした：
- 残りの4つのPhaseクラス（test-implementation.ts、testing.ts、documentation.ts、report.ts）へのオプショナルコンテキスト構築の適用
- 5つのプロンプトファイルの置換キー変更
- 手動E2Eテストの実施
- 既存テストの自動実行

### 1.2 目的

Issue #396で残された作業を完了させ、ai-workflow-v2のオプショナルコンテキスト構築機能を全Phaseクラスに適用することで、以下を実現します：

1. **一貫性の確保**: すべてのPhaseクラスで統一されたオプショナルコンテキスト構築パターンを使用
2. **quick-fixプリセットの完全動作**: 依存関係を無視した実行（`--ignore-dependencies`）が全Phaseで正常に動作
3. **保守性の向上**: 各Phaseクラスでエラーハンドリングを削減し、コードの保守性を向上
4. **品質の保証**: 手動E2Eテストと既存自動テストの実行により、実装の正当性を検証

### 1.3 ビジネス価値・技術的価値

**ビジネス価値**:
- **開発効率の向上**: quick-fixプリセットが完全に動作することで、軽微な修正時のワークフロー時間を短縮（推定: 30-50%削減）
- **ユーザー体験の改善**: 全Phaseでオプショナルコンテキストが使用できるため、柔軟なワークフローが可能

**技術的価値**:
- **コードの統一性**: 全Phaseクラスで同じパターンを使用し、コードの可読性と保守性が向上
- **エラーハンドリングの削減**: オプショナルコンテキストにより、従来の複雑なエラーハンドリングが不要
- **テストカバレッジの完成**: 既存の42個のテストケースが全Phaseで機能することを確認

---

## 2. 機能要件

### FR-1: Phaseクラスへのオプショナルコンテキスト構築の実装（優先度: 高）

**説明**: 4つのPhaseクラス（test-implementation.ts、testing.ts、documentation.ts、report.ts）の`execute`メソッドで、`buildOptionalContext`ヘルパー関数を使用してオプショナルコンテキストを構築する。

**詳細**:
- **対象ファイル**:
  1. `src/phases/test-implementation.ts`
  2. `src/phases/testing.ts`
  3. `src/phases/documentation.ts`
  4. `src/phases/report.ts`

- **修正内容**（各ファイル共通）:
  1. 従来のエラーハンドリング付きファイル読み込みを削除
  2. `buildOptionalContext`ヘルパー関数を使用したコンテキスト構築に置き換え
  3. プロンプト置換キーを`{filename_context}`形式に変更（例: `{requirements_document_path}` → `{requirements_context}`）

- **参照実装**: `src/phases/implementation.ts`（Issue #396で実装済み）

**受け入れ基準**（FR-1）:
- Given: test-implementation.ts、testing.ts、documentation.ts、report.tsが存在する
- When: 各Phaseクラスの`execute`メソッドを実行する
- Then: `buildOptionalContext`を使用してオプショナルコンテキストが構築される
- And: 前段Phaseのファイルが存在する場合、`@filepath`形式でファイル参照が行われる
- And: 前段Phaseのファイルが存在しない場合、フォールバックメッセージが使用される
- And: エラーハンドリング処理（try-catch等）が削除されている

---

### FR-2: プロンプトファイルの置換キー変更（優先度: 高）

**説明**: 5つのプロンプトファイルの置換キーを`{filename_context}`形式に変更し、オプショナル参照の説明コメントを追加する。

**詳細**:
- **対象ファイル**:
  1. `src/prompts/implementation/execute.txt`
  2. `src/prompts/test_implementation/execute.txt`
  3. `src/prompts/testing/execute.txt`
  4. `src/prompts/documentation/execute.txt`
  5. `src/prompts/report/execute.txt`

- **修正内容**（各ファイル共通）:
  1. 置換キーを`{filename_path}` → `{filename_context}`に変更
  2. 各セクションに「（利用可能な場合）」を追加
  3. HTMLコメントでオプショナル参照の動作を説明

- **参照例**: Issue #396 設計書 7.4.1節（implementation/execute.txtの例）

**受け入れ基準**（FR-2）:
- Given: 5つのプロンプトファイルが存在する
- When: プロンプトファイルを確認する
- Then: 置換キーが`{filename_context}`形式に変更されている
- And: 各セクションに「（利用可能な場合）」が記載されている
- And: HTMLコメントでオプショナル参照の動作が説明されている
- And: フォールバックメッセージの内容が明記されている

---

### FR-3: 手動E2Eテストの実施（優先度: 高）

**説明**: Issue #396の評価レポートで特定された4つのシナリオを手動で実行し、実際のAgent実行を含むエンドツーエンドの動作を検証する。

**詳細**:
- **テストシナリオ**:
  1. **quick-fixプリセット実行**: `npm run start -- execute --issue <番号> --preset quick-fix --ignore-dependencies`
     - 期待結果: implementation、documentation、reportが実行され、前段Phase不在でもフォールバックメッセージで動作する
  2. **implementationプリセット実行**: `npm run start -- execute --issue <番号> --preset implementation`
     - 期待結果: implementation、test_implementation、testing、documentation、reportが順次実行される
  3. **非推奨プリセット名での実行**: `npm run start -- execute --issue <番号> --preset requirements-only`
     - 期待結果: 警告メッセージが表示され、review-requirementsプリセットが実行される
  4. **--list-presetsコマンド実行**: `npm run start -- --list-presets`
     - 期待結果: プリセット一覧と説明が表示される

**受け入れ基準**（FR-3）:
- Given: ai-workflow-v2が実行可能な環境である
- When: 4つのテストシナリオを手動で実行する
- Then: すべてのシナリオが期待通りに動作する
- And: エラーが発生しない
- And: フォールバックメッセージが適切に表示される（シナリオ1）
- And: 警告メッセージが適切に表示される（シナリオ3）

---

### FR-4: 既存自動テストの実行（優先度: 高）

**説明**: Issue #396で作成された42個のテストケースを実行し、すべてが成功することを確認する。

**詳細**:
- **対象テストファイル**:
  1. `tests/unit/phase-dependencies.test.ts` - 10ケース
  2. `tests/unit/main-preset-resolution.test.ts` - 11ケース
  3. `tests/unit/base-phase-optional-context.test.ts` - 7ケース
  4. `tests/integration/preset-execution.test.ts` - 14ケース

- **実行方法**: `tests/run-tests.sh`スクリプトを使用

**受け入れ基準**（FR-4）:
- Given: 42個のテストケースが存在する
- When: テストスクリプトを実行する
- Then: 42個すべてのテストケースが成功する
- And: テスト実行時にエラーやwarningが発生しない

---

## 3. 非機能要件

### NFR-1: パフォーマンス要件

- **P-1**: 各Phaseクラスの`execute`メソッド内の`buildOptionalContext`呼び出しは、1ファイルあたり0.01秒以内に完了すること
- **P-2**: report.tsの`execute`メソッド（5個のオプショナルコンテキスト構築）は、合計0.05秒以内に完了すること
- **P-3**: 既存のPhase実行時間に対して、オプショナルコンテキスト構築による遅延が5%未満であること

### NFR-2: 保守性要件

- **M-1**: すべてのPhaseクラスで同じ`buildOptionalContext`パターンを使用し、コードの一貫性を確保すること
- **M-2**: 各Phaseクラスのフォールバックメッセージは、そのPhaseの目的に即した内容であること
- **M-3**: プロンプトファイルのHTMLコメントは、将来のメンテナーが理解しやすい形式であること

### NFR-3: 互換性要件

- **C-1**: 既存機能（`--phase`オプション、Resume機能等）への影響がないこと
- **C-2**: 従来通りの動作（前段Phase完了時の`@filepath`参照）が維持されること
- **C-3**: オプショナルコンテキスト未使用のPhaseクラス（planning、requirements等）の動作に影響がないこと

### NFR-4: テスト要件

- **T-1**: Issue #396で作成された既存の42個のテストケースがすべて成功すること
- **T-2**: 手動E2Eテストの4シナリオがすべて成功すること
- **T-3**: テストの実行時間が合計10分以内であること（自動テスト + 手動E2Eテスト）

---

## 4. 制約事項

### 4.1 技術的制約

1. **既存実装の活用**:
   - `BasePhase.buildOptionalContext`メソッドは既に実装済み（Issue #396）
   - このメソッドを変更せず、そのまま活用すること

2. **実装パターンの遵守**:
   - implementation.tsで実装されたパターンを厳密に踏襲すること
   - 新規のロジックやヘルパー関数を追加しないこと

3. **TypeScript型安全性**:
   - 既存の型定義（`PhaseName`、`PhaseExecutionResult`等）を変更しないこと
   - 型安全性を損なわないこと

### 4.2 リソース制約

1. **時間的制約**:
   - 見積もり工数: 6~10時間（Planning Documentより）
   - 各タスクの実行時間を厳守すること

2. **人員制約**:
   - 単独作業者で完結可能な作業であること
   - 外部依存やレビュー待ちを最小限に抑えること

### 4.3 ポリシー制約

1. **コーディング規約**:
   - 既存のコーディングスタイルに合致すること
   - JSDocコメントを適切に記載すること

2. **後方互換性**:
   - 既存のプリセット動作に影響を与えないこと
   - 従来通りのPhase実行（依存関係を満たす場合）の動作を維持すること

---

## 5. 前提条件

### 5.1 システム環境

- **実行環境**: Node.js 18以上
- **TypeScriptバージョン**: 既存プロジェクトで使用されているバージョンと同一
- **テストフレームワーク**: Node.js built-in test runner

### 5.2 依存コンポーネント

1. **Issue #396の成果物**:
   - `BasePhase.buildOptionalContext`メソッド（実装済み）
   - `PHASE_PRESETS`定義（プリセット定義）
   - `validatePhaseDependencies`関数（依存関係チェック）
   - 42個のテストケース

2. **既存Phaseクラス**:
   - implementation.ts（参照実装として使用）
   - test-implementation.ts、testing.ts、documentation.ts、report.ts（修正対象）

3. **プロンプトファイル**:
   - 5つのプロンプトファイル（修正対象）

### 5.3 外部システム連携

- **なし**: 外部システムとの連携は不要

---

## 6. 受け入れ基準

### 6.1 FR-1の受け入れ基準（Phaseクラス修正）

**Given**: test-implementation.ts、testing.ts、documentation.ts、report.tsが存在する
**When**: 各Phaseクラスの`execute`メソッドを実行する
**Then**:
- `buildOptionalContext`を使用してオプショナルコンテキストが構築される
- 前段Phaseのファイルが存在する場合、`@filepath`形式でファイル参照が行われる
- 前段Phaseのファイルが存在しない場合、フォールバックメッセージが使用される
- エラーハンドリング処理（try-catch等）が削除されている

**検証方法**:
- コードレビューで`buildOptionalContext`の使用を確認
- 手動E2Eテスト（quick-fixプリセット）で動作確認

### 6.2 FR-2の受け入れ基準（プロンプトファイル修正）

**Given**: 5つのプロンプトファイルが存在する
**When**: プロンプトファイルを確認する
**Then**:
- 置換キーが`{filename_context}`形式に変更されている
- 各セクションに「（利用可能な場合）」が記載されている
- HTMLコメントでオプショナル参照の動作が説明されている
- フォールバックメッセージの内容が明記されている

**検証方法**:
- コードレビューで置換キーとコメントを確認
- 手動E2Eテストでプロンプトの動作を確認

### 6.3 FR-3の受け入れ基準（手動E2Eテスト）

**Given**: ai-workflow-v2が実行可能な環境である
**When**: 4つのテストシナリオを手動で実行する
**Then**:
- すべてのシナリオが期待通りに動作する
- エラーが発生しない
- フォールバックメッセージが適切に表示される（シナリオ1）
- 警告メッセージが適切に表示される（シナリオ3）

**検証方法**:
- 各シナリオの実行結果をスクリーンショットまたはログで記録
- 結果をドキュメント（implementation.md）に記載

### 6.4 FR-4の受け入れ基準（自動テスト実行）

**Given**: 42個のテストケースが存在する
**When**: テストスクリプトを実行する
**Then**:
- 42個すべてのテストケースが成功する
- テスト実行時にエラーやwarningが発生しない

**検証方法**:
- テスト実行ログを確認
- テスト結果をドキュメント（report.md）に記載

---

## 7. スコープ外

以下の項目は、本Issue（#398）のスコープ外とします：

### 7.1 明確にスコープ外とする事項

1. **新規プリセットの追加**: Issue #396で既に7個のプリセットを追加済みであり、本Issueでは追加しない
2. **依存関係チェックの強化**: Issue #396で既に強化済みであり、本Issueでは変更しない
3. **buildOptionalContextメソッドの修正**: Issue #396で実装済みであり、本Issueでは変更しない
4. **新規テストケースの作成**: Issue #396で42個のテストケースを作成済みであり、本Issueでは追加しない
5. **ドキュメントの大幅な更新**: README.md等のドキュメントはIssue #396で更新済みであり、本Issueでは軽微な更新のみ
6. **CI/CD統合**: 将来的な拡張候補であり、本Issueでは実施しない

### 7.2 将来的な拡張候補

1. **プリセット実行履歴の記録**: 各プリセットの実行履歴をメタデータに記録し、統計情報を提供
2. **カスタムプリセット定義機能**: ユーザーが独自のプリセットを定義できる機能
3. **プリセットの動的生成**: Issue内容に基づいて最適なプリセットを提案
4. **Phase実行の並列化**: 依存関係のないPhaseを並列実行し、実行時間を短縮

---

## 8. 成功基準のチェックリスト

### 8.1 機能要件の達成

- [ ] test-implementation.ts、testing.ts、documentation.ts、report.tsが`buildOptionalContext`を使用している
- [ ] 5つのプロンプトファイルの置換キーが`{filename_context}`形式に変更されている
- [ ] プロンプトファイルにオプショナル参照の説明コメントが追加されている
- [ ] 手動E2Eテストの4シナリオがすべて成功する
- [ ] 既存自動テストの42ケースがすべて成功する

### 8.2 非機能要件の達成

- [ ] オプショナルコンテキスト構築が1ファイルあたり0.01秒以内に完了する
- [ ] 既存のPhase実行時間への影響が5%未満である
- [ ] すべてのPhaseクラスで同じパターンが使用されている
- [ ] 既存機能（`--phase`、Resume等）への影響がない

### 8.3 品質基準の達成

- [ ] コードレビューで問題が指摘されない
- [ ] コーディング規約に準拠している
- [ ] TypeScriptの型安全性が維持されている
- [ ] 実装ログが正確に記録されている

---

## 9. 参考情報

### 9.1 関連ドキュメント

- **Issue #396評価レポート**: `.ai-workflow/issue-396/09_evaluation/output/evaluation_report.md`
- **Issue #396設計書**: `.ai-workflow/issue-396/02_design/output/design.md`（特に7.3節を参照）
- **Issue #396実装ログ**: `.ai-workflow/issue-396/04_implementation/output/implementation.md`
- **参照実装**: `scripts/ai-workflow-v2/src/phases/implementation.ts`

### 9.2 実装パターン例

**implementation.tsからの抜粋**（参照実装）:
```typescript
// オプショナルコンテキストを構築（Issue #396）
const requirementsContext = this.buildOptionalContext(
  'requirements',
  'requirements.md',
  '要件定義書は利用できません。Planning情報とIssue情報から要件を推測してください。',
  issueNumber,
);

const designContext = this.buildOptionalContext(
  'design',
  'design.md',
  '設計書は利用できません。Issue情報とPlanning情報に基づいて適切な設計判断を行ってください。',
  issueNumber,
);

// プロンプトで使用
const executePrompt = this.loadPrompt('execute')
  .replace('{planning_document_path}', planningReference)
  .replace('{requirements_context}', requirementsContext)
  .replace('{design_context}', designContext)
  .replace('{test_scenario_context}', testScenarioContext)
  .replace('{implementation_strategy}', implementationStrategy)
  .replace('{issue_number}', String(issueNumber));
```

### 9.3 プロンプトファイルのフォーマット例

**設計書7.4.1節より**:
```markdown
### 要件定義書（利用可能な場合）
{requirements_context}
<!--
  存在する場合: @requirements.md への参照
  存在しない場合: "要件定義書は利用できません。Planning情報とIssue情報から要件を推測してください。"
-->
```

---

**作成日**: 2025-01-16
**Issue番号**: #398
**関連Issue**: #396
**Planning Document**: @.ai-workflow/issue-398/00_planning/output/planning.md
**GitHub Issue**: https://github.com/tielec/infrastructure-as-code/issues/398
