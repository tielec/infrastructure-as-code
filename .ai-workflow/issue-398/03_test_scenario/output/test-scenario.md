# テストシナリオ - Issue #398

**Issue番号**: #398
**タイトル**: [FOLLOW-UP] Issue #396 - 残タスク
**作成日**: 2025-01-16
**作成者**: AI Test Scenario Designer (Phase 3)

---

## 0. Planning Documentの確認

Planning Document (@.ai-workflow/issue-398/00_planning/output/planning.md) を確認し、以下のテスト戦略を踏まえてテストシナリオを作成します。

### テスト戦略（Phase 2で決定）
**INTEGRATION_ONLY**

**判断根拠**:
- `buildOptionalContext`メソッドのユニットテストは既に存在（Issue #396で実装済み）
- 各Phaseクラスは既存メソッドを呼び出すだけで、新規ロジックの追加がない
- エンドツーエンドの動作確認が必要（実際のプリセット実行、Agent実行時の挙動確認）
- BDDは不要（開発者向けの内部機能拡張であり、エンドユーザー向けのストーリーではない）

---

## 1. テスト戦略サマリー

### 1.1 選択されたテスト戦略

**INTEGRATION_ONLY（インテグレーションテストのみ）**

### 1.2 テスト対象の範囲

本Issue #398では、以下のコンポーネントを修正します：

**Phaseクラス（4ファイル）**:
1. `test-implementation.ts`
2. `testing.ts`
3. `documentation.ts`
4. `report.ts`

**プロンプトファイル（5ファイル）**:
5. `implementation/execute.txt`
6. `test_implementation/execute.txt`
7. `testing/execute.txt`
8. `documentation/execute.txt`
9. `report/execute.txt`

### 1.3 テストの目的

1. **オプショナルコンテキスト構築の動作確認**: 修正した4つのPhaseクラスで、`buildOptionalContext`メソッドが正常に動作することを確認
2. **プリセット実行の動作確認**: quick-fixプリセット、implementationプリセット等が正常に動作することを確認
3. **Agent実行時の挙動確認**: 実際のClaude Agent実行時に、プロンプトのオプショナル参照が正常に機能することを確認
4. **既存テストの継続動作**: Issue #396で作成された42個のテストケースが引き続き成功することを確認

---

## 2. Integrationテストシナリオ

### 2.1 手動E2Eテスト（4シナリオ）

#### シナリオ1: quick-fixプリセット実行（依存関係無視）

**目的**: quick-fixプリセットが`--ignore-dependencies`オプション付きで正常に動作し、前段Phaseの成果物が存在しない場合でもフォールバックメッセージで動作することを確認

**前提条件**:
- ai-workflow-v2が実行可能な環境である
- 新規Issueを作成済み（または既存のIssueを使用）
- 前段Phase（requirements、design等）の成果物が存在しない状態

**テスト手順**:
1. 新規Issueを作成（例: Issue #399）
2. 以下のコマンドを実行:
   ```bash
   cd scripts/ai-workflow-v2
   npm run start -- execute --issue 399 --preset quick-fix --ignore-dependencies
   ```
3. 実行ログを確認
4. 各Phaseの成果物（implementation.md、documentation-update-log.md、evaluation_report.md）を確認
5. 各Phase実行時のプロンプトにフォールバックメッセージが含まれていることを確認

**期待結果**:
- quick-fixプリセットが正常に実行される（implementation、documentation、reportの3 Phase）
- 前段Phaseの成果物が存在しない場合、フォールバックメッセージがプロンプトに含まれる
- 例（implementation Phase）:
  - `requirements_context`: "要件定義書は利用できません。Planning情報とIssue情報から要件を推測してください。"
  - `design_context`: "設計書は利用できません。Issue情報とPlanning情報に基づいて適切な設計判断を行ってください。"
- 各Phaseが正常に完了し、成果物が生成される
- エラーが発生しない

**確認項目**:
- [ ] quick-fixプリセットが正常に実行される
- [ ] implementation Phaseが実行される
- [ ] documentation Phaseが実行される
- [ ] report Phaseが実行される
- [ ] 各Phaseでフォールバックメッセージが使用される
- [ ] 成果物（implementation.md、documentation-update-log.md、evaluation_report.md）が生成される
- [ ] エラーやwarningが発生しない

---

#### シナリオ2: implementationプリセット実行（通常実行）

**目的**: implementationプリセットが正常に動作し、前段Phaseの成果物が存在する場合は`@filepath`参照が使用されることを確認

**前提条件**:
- ai-workflow-v2が実行可能な環境である
- Issue #398が存在し、planning、requirements、design、test_scenarioが完了している

**テスト手順**:
1. 以下のコマンドを実行:
   ```bash
   cd scripts/ai-workflow-v2
   npm run start -- execute --issue 398 --preset implementation
   ```
2. 実行ログを確認
3. 各Phaseの成果物を確認
4. 各Phase実行時のプロンプトに`@filepath`参照が含まれていることを確認

**期待結果**:
- implementationプリセットが正常に実行される（implementation、test_implementation、testing、documentation、reportの5 Phase）
- 前段Phaseの成果物が存在する場合、`@filepath`参照がプロンプトに含まれる
- 例（implementation Phase）:
  - `requirements_context`: `@.ai-workflow/issue-398/01_requirements/output/requirements.md`
  - `design_context`: `@.ai-workflow/issue-398/02_design/output/design.md`
- 各Phaseが順次実行され、成果物が生成される
- 依存関係チェックが正常に動作する

**確認項目**:
- [ ] implementationプリセットが正常に実行される
- [ ] implementation Phaseが実行される
- [ ] test_implementation Phaseが実行される
- [ ] testing Phaseが実行される
- [ ] documentation Phaseが実行される
- [ ] report Phaseが実行される
- [ ] 各Phaseで`@filepath`参照が使用される（前段Phase完了時）
- [ ] 成果物が順次生成される
- [ ] 依存関係チェックが正常に動作する

---

#### シナリオ3: 非推奨プリセット名での実行（警告確認）

**目的**: 非推奨プリセット名で実行した場合、警告メッセージが表示され、新しいプリセット名が実行されることを確認

**前提条件**:
- ai-workflow-v2が実行可能な環境である
- Issue #398が存在する

**テスト手順**:
1. 以下のコマンドを実行（非推奨プリセット名を使用）:
   ```bash
   cd scripts/ai-workflow-v2
   npm run start -- execute --issue 398 --preset requirements-only
   ```
2. 実行ログを確認
3. 警告メッセージが表示されることを確認
4. 新しいプリセット名（review-requirements）が実行されることを確認

**期待結果**:
- 警告メッセージが表示される:
  - "警告: プリセット名 'requirements-only' は非推奨です。代わりに 'review-requirements' を使用してください。"
- 新しいプリセット名（review-requirements）が実行される
- 正常にPhaseが実行される

**確認項目**:
- [ ] 警告メッセージが表示される
- [ ] 警告メッセージに新しいプリセット名が記載されている
- [ ] 新しいプリセット名（review-requirements）が実行される
- [ ] Phaseが正常に実行される

---

#### シナリオ4: --list-presetsコマンド実行

**目的**: `--list-presets`コマンドが正常に動作し、プリセット一覧と説明が表示されることを確認

**前提条件**:
- ai-workflow-v2が実行可能な環境である

**テスト手順**:
1. 以下のコマンドを実行:
   ```bash
   cd scripts/ai-workflow-v2
   npm run start -- --list-presets
   ```
2. 出力を確認
3. プリセット一覧と説明が表示されることを確認

**期待結果**:
- プリセット一覧が表示される
- 各プリセットの説明が表示される
- 以下のプリセットが含まれる:
  - `full-workflow`: 全フェーズ実行
  - `planning-only`: Planning Phase のみ実行
  - `review-requirements`: Planning + Requirements Phase のみ実行
  - `review-design`: Planning + Requirements + Design Phase のみ実行
  - `quick-fix`: 軽微な修正用（implementation + documentation + report）
  - `implementation`: 実装フェーズ以降を実行
  - `testing-only`: テスト実行のみ
- 非推奨プリセット名は表示されない（または非推奨の注記がある）

**確認項目**:
- [ ] プリセット一覧が表示される
- [ ] 各プリセットに説明が表示される
- [ ] 7個のプリセットが表示される
- [ ] 非推奨プリセット名が適切に処理されている

---

### 2.2 自動テスト実行（既存42ケース）

#### シナリオ5: 既存テストスイートの実行

**目的**: Issue #396で作成された42個のテストケースが、今回の修正後も引き続き成功することを確認

**前提条件**:
- ai-workflow-v2が実行可能な環境である
- テストスクリプト（`tests/run-tests.sh`）が存在する
- 今回の修正（Phaseクラス4個、プロンプトファイル5個）が完了している

**テスト手順**:
1. 以下のコマンドを実行:
   ```bash
   cd scripts/ai-workflow-v2
   ./tests/run-tests.sh
   ```
2. テスト実行ログを確認
3. テスト結果を確認（42ケース全て成功することを期待）

**期待結果**:
- 42個のテストケースすべてが成功する
- テスト実行時にエラーやwarningが発生しない
- テストカバレッジが維持される

**テストファイル一覧**:
1. `tests/unit/phase-dependencies.test.ts` - 10ケース
2. `tests/unit/main-preset-resolution.test.ts` - 11ケース
3. `tests/unit/base-phase-optional-context.test.ts` - 7ケース
4. `tests/integration/preset-execution.test.ts` - 14ケース

**確認項目**:
- [ ] 42個のテストケースすべてが成功する
- [ ] phase-dependencies.test.ts（10ケース）が成功する
- [ ] main-preset-resolution.test.ts（11ケース）が成功する
- [ ] base-phase-optional-context.test.ts（7ケース）が成功する
- [ ] preset-execution.test.ts（14ケース）が成功する
- [ ] テスト実行時にエラーやwarningが発生しない
- [ ] テストカバレッジが維持される（または向上する）

---

### 2.3 コンポーネント統合テスト

#### シナリオ6: Phaseクラスとプロンプトファイルの統合

**目的**: 修正したPhaseクラスとプロンプトファイルの置換キーが一致しており、正常にプロンプトが構築されることを確認

**前提条件**:
- 4つのPhaseクラスが修正済み
- 5つのプロンプトファイルが修正済み

**テスト手順**:
1. test-implementation Phaseを実行
2. プロンプト構築時にエラーが発生しないことを確認
3. 置換キーがすべて置換されていることを確認（`{...}`が残っていないこと）
4. 同様の確認を、testing、documentation、report Phaseでも実施

**期待結果**:
- 各Phaseでプロンプトが正常に構築される
- 置換キー（`{requirements_context}`、`{design_context}`等）がすべて置換される
- 未置換のキー（`{...}`形式）が残っていない
- プロンプト構築時にエラーが発生しない

**確認項目**（各Phaseごと）:
- [ ] test-implementation Phase: プロンプトが正常に構築される
  - [ ] `{requirements_context}` が置換される
  - [ ] `{design_context}` が置換される
  - [ ] `{test_scenario_context}` が置換される
  - [ ] `{implementation_context}` が置換される
- [ ] testing Phase: プロンプトが正常に構築される
  - [ ] `{test_implementation_context}` が置換される
  - [ ] `{implementation_context}` が置換される
  - [ ] `{test_scenario_context}` が置換される
- [ ] documentation Phase: プロンプトが正常に構築される
  - [ ] `{implementation_context}` が置換される
  - [ ] `{testing_context}` が置換される
  - [ ] 参考情報の各contextが置換される
- [ ] report Phase: プロンプトが正常に構築される
  - [ ] `{requirements_context}` が置換される
  - [ ] `{design_context}` が置換される
  - [ ] `{implementation_context}` が置換される
  - [ ] `{testing_context}` が置換される
  - [ ] `{documentation_context}` が置換される

---

#### シナリオ7: buildOptionalContextメソッドとPhaseクラスの統合

**目的**: `BasePhase.buildOptionalContext`メソッドが各Phaseクラスから正常に呼び出され、期待通りの動作をすることを確認

**前提条件**:
- `BasePhase.buildOptionalContext`メソッドが実装済み（Issue #396）
- 4つのPhaseクラスが`buildOptionalContext`を使用するように修正済み

**テスト手順**:
1. 前段Phaseの成果物が**存在する**場合のテスト:
   - requirements、design、test_scenarioが完了している状態
   - implementation Phaseを実行
   - `buildOptionalContext`が`@filepath`参照を返すことを確認
2. 前段Phaseの成果物が**存在しない**場合のテスト:
   - 前段Phaseが完了していない状態
   - quick-fixプリセットを`--ignore-dependencies`付きで実行
   - `buildOptionalContext`がフォールバックメッセージを返すことを確認

**期待結果**:
- **ファイル存在時**: `@filepath`形式の参照が返される
  - 例: `@.ai-workflow/issue-398/01_requirements/output/requirements.md`
- **ファイル不存在時**: フォールバックメッセージが返される
  - 例: "要件定義書は利用できません。Planning情報とIssue情報から要件を推測してください。"
- エラーが発生しない
- 例外がスローされない

**確認項目**:
- [ ] ファイル存在時、`@filepath`参照が返される
- [ ] ファイル不存在時、フォールバックメッセージが返される
- [ ] test-implementation Phaseで正常に動作する
- [ ] testing Phaseで正常に動作する
- [ ] documentation Phaseで正常に動作する
- [ ] report Phaseで正常に動作する
- [ ] エラーや例外が発生しない

---

#### シナリオ8: プリセット実行と依存関係チェックの統合

**目的**: プリセット実行時に、依存関係チェック機能が正常に動作し、オプショナルコンテキスト構築と矛盾なく統合されていることを確認

**前提条件**:
- `validatePhaseDependencies`関数が実装済み（Issue #396）
- quick-fixプリセット定義で`ignoreDependencies: true`が設定されている

**テスト手順**:
1. 通常のプリセット実行（implementation）:
   - 前段Phaseが未完了の状態
   - implementationプリセットを実行
   - 依存関係チェックでエラーが発生することを確認
2. 依存関係無視のプリセット実行（quick-fix）:
   - 前段Phaseが未完了の状態
   - quick-fixプリセットを`--ignore-dependencies`付きで実行
   - 依存関係チェックがスキップされ、正常に実行されることを確認

**期待結果**:
- **通常のプリセット（依存関係チェック有効）**:
  - 前段Phaseが未完了の場合、エラーが発生する
  - エラーメッセージに不足しているPhaseが記載される
- **quick-fixプリセット（依存関係チェック無効）**:
  - 前段Phaseが未完了でも実行される
  - オプショナルコンテキストでフォールバックメッセージが使用される
  - 正常に完了する

**確認項目**:
- [ ] 通常のプリセット実行で依存関係チェックが動作する
- [ ] 依存関係が不足している場合、エラーが発生する
- [ ] quick-fixプリセットで依存関係チェックがスキップされる
- [ ] quick-fixプリセットで前段Phase不在でも実行される
- [ ] オプショナルコンテキストと依存関係チェックが矛盾なく動作する

---

## 3. テストデータ

### 3.1 テスト用Issue

**Issue #398（本Issue）**:
- 用途: シナリオ2（implementationプリセット実行）で使用
- 前提条件: planning、requirements、design、test_scenarioが完了している

**Issue #399（新規作成）**:
- 用途: シナリオ1（quick-fixプリセット実行）で使用
- 前提条件: 前段Phaseが存在しない（または最小限）

### 3.2 テストコマンド一覧

| シナリオ | コマンド | 期待される動作 |
|---------|---------|--------------|
| シナリオ1 | `npm run start -- execute --issue 399 --preset quick-fix --ignore-dependencies` | quick-fixプリセット実行、フォールバックメッセージ使用 |
| シナリオ2 | `npm run start -- execute --issue 398 --preset implementation` | implementationプリセット実行、@filepath参照使用 |
| シナリオ3 | `npm run start -- execute --issue 398 --preset requirements-only` | 警告メッセージ表示、review-requirements実行 |
| シナリオ4 | `npm run start -- --list-presets` | プリセット一覧表示 |
| シナリオ5 | `./tests/run-tests.sh` | 42ケース全て成功 |

### 3.3 検証ポイント

**フォールバックメッセージの検証**:
- requirements: "要件定義書は利用できません。Planning情報とIssue情報から要件を推測してください。"
- design: "設計書は利用できません。Issue情報とPlanning情報に基づいて適切な設計判断を行ってください。"
- test_scenario: "テストシナリオは利用できません。実装時に適切なテスト考慮を行ってください。"
- implementation: "実装ログは利用できません。リポジトリの実装コードを直接確認してください。"
- test_implementation: "テストコード実装ログは利用できません。実装コードを直接確認してテストを実行してください。"
- testing: "テスト結果は利用できません。実装内容に基づいて適切に判断してください。"
- documentation: "ドキュメント更新ログは利用できません。"

**@filepath参照の検証**:
- requirements: `@.ai-workflow/issue-398/01_requirements/output/requirements.md`
- design: `@.ai-workflow/issue-398/02_design/output/design.md`
- test_scenario: `@.ai-workflow/issue-398/03_test_scenario/output/test-scenario.md`
- implementation: `@.ai-workflow/issue-398/04_implementation/output/implementation.md`
- test_implementation: `@.ai-workflow/issue-398/05_test_implementation/output/test-implementation.md`
- testing: `@.ai-workflow/issue-398/06_testing/output/test-result.md`
- documentation: `@.ai-workflow/issue-398/07_documentation/output/documentation-update-log.md`

---

## 4. テスト環境要件

### 4.1 実行環境

- **Node.js**: 18以上
- **npm**: 最新版
- **OS**: Linux、macOS、またはWindows（WSL推奨）
- **ワークスペース**: `AI_Workflow/ai_workflow_orchestrator`ディレクトリ

### 4.2 必要なファイル・ディレクトリ

- `scripts/ai-workflow-v2/`: ai-workflow-v2のソースコード
- `tests/`: テストコード（42ケース）
- `tests/run-tests.sh`: テスト実行スクリプト

### 4.3 外部依存

- **GitHub**: Issue情報の取得に使用
- **Claude API**: Agent実行に使用（手動E2Eテストのみ）
- **ファイルシステム**: Phase成果物の読み書き

### 4.4 モック/スタブの必要性

**不要**:
- 今回のテストはインテグレーションテストのため、実際のコンポーネントを使用
- ユニットテスト（Issue #396で実装済み）では、モック/スタブを使用済み

---

## 5. テスト実行スケジュール

### 5.1 実行順序

1. **Phase 4（実装）完了後**:
   - シナリオ5（自動テスト実行）を実施
   - 42ケースすべて成功することを確認
   - 失敗した場合は実装を修正

2. **Phase 6（テスト実行）**:
   - シナリオ1~4（手動E2Eテスト）を実施
   - シナリオ6~8（コンポーネント統合テスト）を実施
   - すべてのシナリオが成功することを確認

### 5.2 見積もり時間

| テストシナリオ | 見積もり時間 |
|--------------|------------|
| シナリオ1: quick-fixプリセット実行 | 15~20分 |
| シナリオ2: implementationプリセット実行 | 20~30分 |
| シナリオ3: 非推奨プリセット警告 | 5~10分 |
| シナリオ4: --list-presetsコマンド | 5分 |
| シナリオ5: 自動テスト実行 | 10~15分 |
| シナリオ6: Phaseとプロンプト統合 | 15~20分 |
| シナリオ7: buildOptionalContext統合 | 15~20分 |
| シナリオ8: プリセットと依存関係統合 | 10~15分 |
| **合計** | **1.5~2.5時間** |

---

## 6. 成功基準

### 6.1 機能要件の達成

- [ ] **手動E2Eテスト（4シナリオ）がすべて成功する**
  - シナリオ1: quick-fixプリセット実行
  - シナリオ2: implementationプリセット実行
  - シナリオ3: 非推奨プリセット警告
  - シナリオ4: --list-presetsコマンド

- [ ] **自動テスト（42ケース）がすべて成功する**
  - phase-dependencies.test.ts（10ケース）
  - main-preset-resolution.test.ts（11ケース）
  - base-phase-optional-context.test.ts（7ケース）
  - preset-execution.test.ts（14ケース）

- [ ] **コンポーネント統合テスト（3シナリオ）がすべて成功する**
  - シナリオ6: Phaseクラスとプロンプトファイルの統合
  - シナリオ7: buildOptionalContextメソッドとPhaseクラスの統合
  - シナリオ8: プリセット実行と依存関係チェックの統合

### 6.2 非機能要件の達成

- [ ] パフォーマンス: オプショナルコンテキスト構築が1ファイルあたり0.01秒以内
- [ ] 互換性: 既存機能（`--phase`、Resume等）への影響がない
- [ ] 保守性: すべてのPhaseクラスで同じパターンが使用されている

### 6.3 品質ゲート（Phase 3）

- [x] **Phase 2の戦略に沿ったテストシナリオである**
  - テスト戦略: INTEGRATION_ONLY
  - 手動E2Eテスト（4シナリオ）を定義
  - 自動テスト実行（42ケース）を定義
  - コンポーネント統合テスト（3シナリオ）を定義

- [x] **主要な正常系がカバーされている**
  - quick-fixプリセット実行（正常系）
  - implementationプリセット実行（正常系）
  - --list-presetsコマンド実行（正常系）
  - Phaseとプロンプト統合（正常系）
  - buildOptionalContext統合（正常系）

- [x] **主要な異常系がカバーされている**
  - 非推奨プリセット名での実行（警告確認）
  - 前段Phase不在時の動作（フォールバックメッセージ）
  - 依存関係チェック不足時の動作（エラー確認）

- [x] **期待結果が明確である**
  - 各シナリオで具体的な期待結果を記載
  - 確認項目をチェックリスト形式で記載
  - テストデータとコマンドを明記

---

## 7. テスト結果記録フォーマット

テスト実行時は、以下のフォーマットで結果を記録してください：

### 7.1 手動E2Eテスト結果

```markdown
### シナリオ[番号]: [シナリオ名]

**実行日時**: YYYY-MM-DD HH:MM:SS
**実行者**: [実行者名]
**結果**: ✅ 成功 / ❌ 失敗

**実行ログ**:
[コマンド実行時のログ（抜粋）]

**スクリーンショット**:
[必要に応じてスクリーンショットを添付]

**確認項目**:
- [x] 項目1
- [x] 項目2
- [ ] 項目3（失敗した場合）

**備考**:
[気づいた点、問題点など]
```

### 7.2 自動テスト結果

```markdown
### シナリオ5: 自動テスト実行

**実行日時**: YYYY-MM-DD HH:MM:SS
**実行者**: [実行者名]
**結果**: ✅ 42/42ケース成功 / ❌ [失敗数]/42ケース失敗

**テスト実行ログ**:
[./tests/run-tests.sh の出力]

**失敗したテストケース**（該当する場合）:
- [テストケース名]: [失敗理由]

**テストカバレッジ**:
[カバレッジレポート（利用可能な場合）]
```

---

## 8. 参考情報

### 8.1 関連ドキュメント

- **Planning Document**: @.ai-workflow/issue-398/00_planning/output/planning.md
- **要件定義書**: @.ai-workflow/issue-398/01_requirements/output/requirements.md
- **設計書**: @.ai-workflow/issue-398/02_design/output/design.md
- **Issue #396評価レポート**: `.ai-workflow/issue-396/09_evaluation/output/evaluation_report.md`
- **Issue #396設計書**: `.ai-workflow/issue-396/02_design/output/design.md`

### 8.2 テスト実行コマンド集

```bash
# シナリオ1: quick-fixプリセット実行
cd scripts/ai-workflow-v2
npm run start -- execute --issue 399 --preset quick-fix --ignore-dependencies

# シナリオ2: implementationプリセット実行
npm run start -- execute --issue 398 --preset implementation

# シナリオ3: 非推奨プリセット名での実行
npm run start -- execute --issue 398 --preset requirements-only

# シナリオ4: --list-presetsコマンド
npm run start -- --list-presets

# シナリオ5: 自動テスト実行
./tests/run-tests.sh
```

---

**作成日**: 2025-01-16
**Issue番号**: #398
**関連Issue**: #396
**Planning Document**: @.ai-workflow/issue-398/00_planning/output/planning.md
**Requirements Document**: @.ai-workflow/issue-398/01_requirements/output/requirements.md
**Design Document**: @.ai-workflow/issue-398/02_design/output/design.md
