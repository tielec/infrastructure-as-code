# 詳細設計書: Issue #396

## 0. Planning Documentの確認

Planning Document (@.ai-workflow/issue-396/00_planning/output/planning.md) の内容を確認し、以下の戦略を踏まえて詳細設計を実施します：

### 開発計画の全体像
- **実装戦略**: EXTEND（既存のPHASE_PRESETSオブジェクトを拡張）
- **テスト戦略**: UNIT_INTEGRATION（ユニットテストとインテグレーションテストの組み合わせ）
- **テストコード戦略**: BOTH_TEST（既存テストの拡張と新規テスト作成）
- **見積もり工数**: 15~21時間
- **リスクレベル**: 中

## 1. 概要

### 背景
ai-workflow-v2のプリセット機能の拡充により、実際の開発ワークフローパターンをカバーし、開発効率を向上させます。

### 設計目標
1. 実用的なプリセットの追加（7個の新規プリセット）
2. 既存プリセットの整理（命名規則の統一、依存関係の修正）
3. 依存関係チェックの確認と強化
4. プロンプトのオプショナル参照対応
5. 後方互換性の維持

## 2. 実装戦略判断

### 実装戦略: EXTEND

**判断根拠**:
- **既存コードベースの拡張が中心**: `PHASE_PRESETS`オブジェクトに新規プリセットを追加
- **既存機能の修正が必要**: `validatePhaseDependencies`の動作確認と強化
- **既存プロンプトの改善**: 5つのプロンプトファイルにオプショナル参照機能を追加
- **新規ファイル作成は最小限**: 主に既存ファイルの拡張で対応可能
- **既存の型定義とインターフェースを活用**: `PhaseName`, `PhasePresets`などの既存型を維持

## 3. テスト戦略判断

### テスト戦略: UNIT_INTEGRATION

**判断根拠**:
- **ユニットテストが必要な理由**:
  - プリセット定義の正確性（各プリセットが正しいPhaseリストを持つ）
  - 依存関係チェックロジックの動作検証（単一Phase実行時のチェック）
  - `buildOptionalContext`関数の動作検証（ファイル存在・非存在の両方）
  - 後方互換性の検証（古いプリセット名の動作確認）

- **インテグレーションテストが必要な理由**:
  - 各プリセットのエンドツーエンド実行（複数Phaseの連携）
  - プロンプトのオプショナル参照が実際のAgent実行時に正常に動作
  - 依存関係チェックエラー時の挙動（エラーメッセージ、`--ignore-dependencies`オプション）
  - Resume機能との連携（特定Phaseから再開時の動作）

- **BDD不要の理由**: エンドユーザー向けのストーリーではなく、開発者向けのCLIオプション拡張であるため

## 4. テストコード戦略判断

### テストコード戦略: BOTH_TEST

**判断根拠**:
- **既存テストの拡張が必要**:
  - 既存の`phase-dependencies.ts`関連テストに新規プリセットのテストを追加
  - 既存の依存関係チェックテストに新しいシナリオを追加

- **新規テスト作成が必要**:
  - `buildOptionalContext`関数の単体テスト（新規機能）
  - プロンプトオプショナル参照のインテグレーションテスト（新規機能）
  - 各プリセットのエンドツーエンドテスト（新規プリセット）

## 5. アーキテクチャ設計

### 5.1 システム全体図

```mermaid
graph TD
    A[CLI: main.ts] -->|--preset| B[phase-dependencies.ts]
    A -->|--phase| B
    A -->|--list-presets| B

    B -->|validatePhaseDependencies| C[依存関係チェック]
    B -->|PHASE_PRESETS| D[プリセット定義]
    B -->|DEPRECATED_PRESETS| E[後方互換性エイリアス]

    C -->|依存Phase未完了| F[エラーメッセージ表示]
    C -->|ファイル不在| F
    C -->|--ignore-dependencies| G[警告表示 + 継続]

    A -->|execute| H[BasePhase]
    H -->|buildOptionalContext| I[ファイル存在チェック]
    I -->|存在する| J[@filepath参照]
    I -->|存在しない| K[フォールバックメッセージ]

    H -->|具体Phase実装| L[implementation.ts]
    H -->|具体Phase実装| M[test-implementation.ts]
    H -->|具体Phase実装| N[testing.ts]
    H -->|具体Phase実装| O[documentation.ts]
    H -->|具体Phase実装| P[report.ts]

    L -->|プロンプト| Q[implementation/execute.txt]
    M -->|プロンプト| R[test_implementation/execute.txt]
    N -->|プロンプト| S[testing/execute.txt]
    O -->|プロンプト| T[documentation/execute.txt]
    P -->|プロンプト| U[report/execute.txt]

    style D fill:#e3f2fd,stroke:#2196f3,stroke-width:2px
    style E fill:#fff3e0,stroke:#ff9800,stroke-width:2px
    style C fill:#e8f5e9,stroke:#4caf50,stroke-width:2px
    style H fill:#fce4ec,stroke:#e91e63,stroke-width:2px
    style I fill:#f3e5f5,stroke:#9c27b0,stroke-width:2px
```

### 5.2 コンポーネント間の関係

#### コアコンポーネント

1. **phase-dependencies.ts**
   - `PHASE_PRESETS`: プリセット定義（既存 + 新規7個）
   - `DEPRECATED_PRESETS`: 後方互換性のためのエイリアスマップ
   - `validatePhaseDependencies`: 依存関係チェック関数（強化）

2. **main.ts**
   - `--preset` オプション処理（既存）
   - `--phase` オプション処理（既存）
   - `--list-presets` オプション追加（新規）
   - エラーメッセージ表示の改善

3. **base-phase.ts**
   - `buildOptionalContext`: オプショナルコンテキスト構築ヘルパー（新規）
   - `getPhaseOutputFile`: ファイルパス取得（既存活用）

4. **各Phase実装クラス**
   - implementation.ts
   - test-implementation.ts
   - testing.ts
   - documentation.ts
   - report.ts
   - → `execute`メソッドでオプショナルコンテキスト構築

5. **プロンプトファイル**
   - implementation/execute.txt
   - test_implementation/execute.txt
   - testing/execute.txt
   - documentation/execute.txt
   - report/execute.txt
   - → オプショナル参照への変更

### 5.3 データフロー

#### シナリオ1: プリセット実行（依存関係満たす）

```
User: npm run start -- execute --issue 123 --preset quick-fix
  ↓
main.ts: プリセット名を解析
  ↓
phase-dependencies.ts: PHASE_PRESETS['quick-fix'] → ['implementation', 'documentation', 'report']
  ↓
validatePhaseDependencies: 各Phaseの依存関係チェック
  ↓ (全依存Phase完了)
各Phase実行:
  implementation.ts → buildOptionalContext → プロンプト構築 → Agent実行
  documentation.ts → buildOptionalContext → プロンプト構築 → Agent実行
  report.ts → buildOptionalContext → プロンプト構築 → Agent実行
```

#### シナリオ2: 単一Phase実行（依存関係不足）

```
User: npm run start -- execute --issue 123 --phase implementation
  ↓
main.ts: Phase名を解析
  ↓
validatePhaseDependencies: implementationの依存関係チェック
  ↓ (planning, requirements, design, test_scenario未完了)
エラーメッセージ表示:
  [ERROR] Phase "implementation" requires the following phases to be completed:
    ✗ planning - NOT FOUND
    ✗ requirements - NOT FOUND
    ...
  Options:
    1. Complete the missing phases first
    2. Use --phase all to run all phases
    3. Use --ignore-dependencies to proceed anyway
  ↓
実行停止
```

#### シナリオ3: --ignore-dependencies使用

```
User: npm run start -- execute --issue 123 --preset quick-fix --ignore-dependencies
  ↓
main.ts: プリセット名を解析
  ↓
phase-dependencies.ts: PHASE_PRESETS['quick-fix'] → ['implementation', 'documentation', 'report']
  ↓
validatePhaseDependencies: ignoreViolations=true
  ↓ (依存Phase未完了だが警告のみ)
警告メッセージ表示:
  [WARNING] Some dependencies are not met. Proceeding anyway...
  ↓
各Phase実行:
  implementation.ts → buildOptionalContext
    → requirements.md不在 → フォールバックメッセージ
    → design.md不在 → フォールバックメッセージ
    → プロンプト構築（フォールバック含む） → Agent実行
```

## 6. 影響範囲分析

### 6.1 既存コードへの影響

#### 変更が必要なファイル (10ファイル)

**コア機能**:
1. `src/core/phase-dependencies.ts` - プリセット定義の追加・変更、依存関係チェック強化
2. `src/main.ts` - `--list-presets`オプション追加、エラーメッセージ改善

**Phase実装**:
3. `src/phases/base-phase.ts` - `buildOptionalContext`ヘルパー関数の追加
4. `src/phases/implementation.ts` - オプショナルコンテキスト構築
5. `src/phases/test-implementation.ts` - オプショナルコンテキスト構築
6. `src/phases/testing.ts` - オプショナルコンテキスト構築
7. `src/phases/documentation.ts` - オプショナルコンテキスト構築
8. `src/phases/report.ts` - オプショナルコンテキスト構築

**プロンプトファイル** (2ファイルは既存、3ファイルは追加確認が必要):
9. `src/prompts/implementation/execute.txt` - オプショナル参照への変更
10. `src/prompts/test_implementation/execute.txt` - オプショナル参照への変更
11. `src/prompts/testing/execute.txt` - オプショナル参照への変更（要確認）
12. `src/prompts/documentation/execute.txt` - オプショナル参照への変更（要確認）
13. `src/prompts/report/execute.txt` - オプショナル参照への変更（要確認）

**ドキュメント**:
14. `README.md` - プリセット一覧セクション追加

#### 影響度マトリクス

| ファイル | 影響度 | 変更タイプ | リスク |
|---------|-------|-----------|--------|
| phase-dependencies.ts | 高 | 拡張 + 強化 | 中 |
| main.ts | 中 | 拡張 | 低 |
| base-phase.ts | 中 | 拡張 | 低 |
| implementation.ts | 低 | 修正 | 低 |
| test-implementation.ts | 低 | 修正 | 低 |
| testing.ts | 低 | 修正 | 低 |
| documentation.ts | 低 | 修正 | 低 |
| report.ts | 低 | 修正 | 低 |
| プロンプトファイル x 5 | 低 | 修正 | 低 |
| README.md | 低 | 追加 | 低 |

### 6.2 依存関係の変更

**新規依存の追加**: なし

**既存依存の変更**: なし

**注意点**:
- `fs`モジュールの使用（既存のimportを活用）
- `path`モジュールの使用（既存のimportを活用）

### 6.3 マイグレーション要否

**不要**

- メタデータスキーマの変更なし
- データベーススキーマの変更なし
- 設定ファイルの変更なし（オプションの追加のみ）

## 7. 詳細設計

### 7.1 プリセット定義の設計

#### 7.1.1 新規プリセット定義

**ファイル**: `src/core/phase-dependencies.ts`

```typescript
export const PHASE_PRESETS: Record<string, PhaseName[]> = {
  // === レビュー駆動パターン ===
  'review-requirements': ['planning', 'requirements'],
  'review-design': ['planning', 'requirements', 'design'],
  'review-test-scenario': ['planning', 'requirements', 'design', 'test_scenario'],

  // === 実装中心パターン ===
  'quick-fix': ['implementation', 'documentation', 'report'],
  'implementation': ['implementation', 'test_implementation', 'testing', 'documentation', 'report'],

  // === テスト中心パターン ===
  'testing': ['test_implementation', 'testing'],

  // === ドキュメント・レポートパターン ===
  'finalize': ['documentation', 'report', 'evaluation'],
};
```

#### 7.1.2 後方互換性のためのエイリアスマップ

```typescript
export const DEPRECATED_PRESETS: Record<string, string> = {
  'requirements-only': 'review-requirements',
  'design-phase': 'review-design',
  'implementation-phase': 'implementation',
  'full-workflow': '--phase all', // 特殊ケース
};
```

#### 7.1.3 プリセット説明マップ

```typescript
export const PRESET_DESCRIPTIONS: Record<string, string> = {
  'review-requirements': 'Planning + Requirements (要件定義レビュー用)',
  'review-design': 'Planning + Requirements + Design (設計レビュー用)',
  'review-test-scenario': 'Planning + Requirements + Design + TestScenario (テストシナリオレビュー用)',
  'quick-fix': 'Implementation + Documentation + Report (軽微な修正用)',
  'implementation': 'Implementation + TestImplementation + Testing + Documentation + Report (通常の実装フロー)',
  'testing': 'TestImplementation + Testing (テスト追加用)',
  'finalize': 'Documentation + Report + Evaluation (最終化用)',
};
```

### 7.2 依存関係チェック強化の設計

#### 7.2.1 現在の実装確認項目

**検証項目**:
1. `validatePhaseDependencies`の呼び出しタイミング
2. `skipCheck`オプションの使用状況
3. `ignoreViolations`オプションの使用状況
4. metadata.jsonの`completed`フラグのチェック
5. 実ファイル存在チェックの有無

#### 7.2.2 強化内容

**ファイル**: `src/core/phase-dependencies.ts`

```typescript
/**
 * 依存関係チェック強化版
 * @param phaseName - 実行対象のPhase名
 * @param workflowState - ワークフロー状態
 * @param options - チェックオプション
 * @returns チェック結果
 */
export function validatePhaseDependencies(
  phaseName: PhaseName,
  workflowState: WorkflowState,
  options: {
    skipCheck?: boolean;
    ignoreViolations?: boolean;
    checkFileExistence?: boolean; // 新規オプション
  } = {}
): {
  isValid: boolean;
  missingDependencies: PhaseName[];
  missingFiles: Array<{ phase: PhaseName; file: string }>; // 新規
  errorMessage?: string;
  warningMessage?: string;
} {
  // skipCheckの場合は即座に成功を返す
  if (options.skipCheck) {
    return { isValid: true, missingDependencies: [], missingFiles: [] };
  }

  // 依存Phase一覧を取得
  const dependencies = PHASE_DEPENDENCIES[phaseName] || [];
  const missingDependencies: PhaseName[] = [];
  const missingFiles: Array<{ phase: PhaseName; file: string }> = [];

  // 各依存Phaseをチェック
  for (const depPhase of dependencies) {
    // metadata.jsonのcompleteフラグチェック
    if (!workflowState.phases[depPhase]?.completed) {
      missingDependencies.push(depPhase);
      continue;
    }

    // ファイル存在チェック（オプション）
    if (options.checkFileExistence) {
      const expectedFile = getPhaseOutputFile(depPhase, workflowState.issueNumber);
      if (!fs.existsSync(expectedFile)) {
        missingFiles.push({ phase: depPhase, file: expectedFile });
      }
    }
  }

  // チェック結果の判定
  const hasViolations = missingDependencies.length > 0 || missingFiles.length > 0;

  if (!hasViolations) {
    return { isValid: true, missingDependencies: [], missingFiles: [] };
  }

  // ignoreViolationsの場合は警告のみ
  if (options.ignoreViolations) {
    const warningMessage = buildWarningMessage(phaseName, missingDependencies, missingFiles);
    return {
      isValid: true, // 警告のみで継続
      missingDependencies,
      missingFiles,
      warningMessage,
    };
  }

  // エラーメッセージを構築
  const errorMessage = buildErrorMessage(phaseName, missingDependencies, missingFiles);
  return {
    isValid: false,
    missingDependencies,
    missingFiles,
    errorMessage,
  };
}
```

#### 7.2.3 エラーメッセージ構築

```typescript
function buildErrorMessage(
  phaseName: PhaseName,
  missingDependencies: PhaseName[],
  missingFiles: Array<{ phase: PhaseName; file: string }>
): string {
  let message = `[ERROR] Phase "${phaseName}" requires the following phases to be completed:\n`;

  // 未完了Phaseのリスト
  for (const dep of missingDependencies) {
    message += `  ✗ ${dep} - NOT COMPLETED\n`;
  }

  // ファイル不在のリスト
  for (const { phase, file } of missingFiles) {
    message += `  ✗ ${phase} - ${file} NOT FOUND\n`;
  }

  message += `\nOptions:\n`;
  message += `  1. Complete the missing phases first\n`;
  message += `  2. Use --phase all to run all phases\n`;
  message += `  3. Use --ignore-dependencies to proceed anyway (not recommended)\n`;

  return message;
}
```

#### 7.2.4 警告メッセージ構築

```typescript
function buildWarningMessage(
  phaseName: PhaseName,
  missingDependencies: PhaseName[],
  missingFiles: Array<{ phase: PhaseName; file: string }>
): string {
  let message = `[WARNING] Phase "${phaseName}" has unmet dependencies, but proceeding anyway...\n`;

  // 未完了Phaseのリスト
  for (const dep of missingDependencies) {
    message += `  ⚠ ${dep} - NOT COMPLETED\n`;
  }

  // ファイル不在のリスト
  for (const { phase, file } of missingFiles) {
    message += `  ⚠ ${phase} - ${file} NOT FOUND\n`;
  }

  return message;
}
```

### 7.3 オプショナルコンテキスト構築の設計

#### 7.3.1 BasePhaseクラスへのヘルパー関数追加

**ファイル**: `src/phases/base-phase.ts`

```typescript
import * as fs from 'fs';
import * as path from 'path';

export abstract class BasePhase {
  // 既存メソッド...

  /**
   * オプショナルコンテキストを構築
   * ファイルが存在する場合は@filepath参照、存在しない場合はフォールバックメッセージ
   *
   * @param phaseName - 参照するPhase名
   * @param filename - ファイル名（例: 'requirements.md'）
   * @param issueNumber - Issue番号
   * @param fallbackMessage - ファイルが存在しない場合のメッセージ
   * @returns ファイル参照またはフォールバックメッセージ
   */
  protected buildOptionalContext(
    phaseName: PhaseName,
    filename: string,
    issueNumber: number,
    fallbackMessage: string
  ): string {
    // Phase出力ディレクトリのパスを取得
    const phaseOutputDir = this.getPhaseOutputDir(phaseName, issueNumber);
    const filePath = path.join(phaseOutputDir, filename);

    // ファイル存在チェック
    if (fs.existsSync(filePath)) {
      // 存在する場合は@filepath形式で参照
      return `@${filePath}`;
    } else {
      // 存在しない場合はフォールバックメッセージ
      return fallbackMessage;
    }
  }

  /**
   * Phase出力ディレクトリのパスを取得
   *
   * @param phaseName - Phase名
   * @param issueNumber - Issue番号
   * @returns ディレクトリパス
   */
  private getPhaseOutputDir(phaseName: PhaseName, issueNumber: number): string {
    // Phase番号マップ
    const phaseNumberMap: Record<PhaseName, string> = {
      'planning': '00_planning',
      'requirements': '01_requirements',
      'design': '02_design',
      'test_scenario': '03_test_scenario',
      'implementation': '04_implementation',
      'test_implementation': '05_test_implementation',
      'testing': '06_testing',
      'documentation': '07_documentation',
      'report': '08_report',
      'evaluation': '09_evaluation',
    };

    const phaseDir = phaseNumberMap[phaseName];
    return path.join(
      process.cwd(),
      '.ai-workflow',
      `issue-${issueNumber}`,
      phaseDir,
      'output'
    );
  }
}
```

#### 7.3.2 各Phaseでのオプショナルコンテキスト構築

**例: implementation.ts**

```typescript
import { BasePhase } from './base-phase';

export class ImplementationPhase extends BasePhase {
  async execute(issueNumber: number): Promise<void> {
    // Issue情報とPlanning情報は必須
    const issueInfo = await this.getIssueInfo(issueNumber);
    const planningPath = this.getPlanningDocumentPath(issueNumber);

    // オプショナルコンテキストを構築
    const requirementsContext = this.buildOptionalContext(
      'requirements',
      'requirements.md',
      issueNumber,
      '要件定義書は利用できません。Planning情報とIssue情報から要件を推測してください。'
    );

    const designContext = this.buildOptionalContext(
      'design',
      'design.md',
      issueNumber,
      '設計書は利用できません。Issue情報とPlanning情報に基づいて適切な設計判断を行ってください。'
    );

    const testScenarioContext = this.buildOptionalContext(
      'test_scenario',
      'test-scenario.md',
      issueNumber,
      'テストシナリオは利用できません。実装時に適切なテスト考慮を行ってください。'
    );

    // プロンプトコンテキストを構築
    const context = {
      issue_info: issueInfo,
      planning_document_path: planningPath,
      requirements_context: requirementsContext,
      design_context: designContext,
      test_scenario_context: testScenarioContext,
    };

    // Agent実行
    await this.runAgent(context);
  }
}
```

**例: test-implementation.ts**

```typescript
export class TestImplementationPhase extends BasePhase {
  async execute(issueNumber: number): Promise<void> {
    const issueInfo = await this.getIssueInfo(issueNumber);
    const planningPath = this.getPlanningDocumentPath(issueNumber);

    const implementationContext = this.buildOptionalContext(
      'implementation',
      'implementation.md',
      issueNumber,
      '実装情報は利用できません。Issue情報とPlanning情報からテストコードを推測してください。'
    );

    const context = {
      issue_info: issueInfo,
      planning_document_path: planningPath,
      implementation_context: implementationContext,
    };

    await this.runAgent(context);
  }
}
```

**例: testing.ts**

```typescript
export class TestingPhase extends BasePhase {
  async execute(issueNumber: number): Promise<void> {
    const issueInfo = await this.getIssueInfo(issueNumber);
    const planningPath = this.getPlanningDocumentPath(issueNumber);

    const testImplementationContext = this.buildOptionalContext(
      'test_implementation',
      'test-implementation.md',
      issueNumber,
      'テスト実装情報は利用できません。既存のテストコードを探索してテストを実行してください。'
    );

    const context = {
      issue_info: issueInfo,
      planning_document_path: planningPath,
      test_implementation_context: testImplementationContext,
    };

    await this.runAgent(context);
  }
}
```

**例: documentation.ts**

```typescript
export class DocumentationPhase extends BasePhase {
  async execute(issueNumber: number): Promise<void> {
    const issueInfo = await this.getIssueInfo(issueNumber);
    const planningPath = this.getPlanningDocumentPath(issueNumber);

    const implementationContext = this.buildOptionalContext(
      'implementation',
      'implementation.md',
      issueNumber,
      '実装情報は利用できません。Issue情報とPlanning情報からドキュメントを作成してください。'
    );

    const testingContext = this.buildOptionalContext(
      'testing',
      'testing.md',
      issueNumber,
      'テスト情報は利用できません。ドキュメントにテスト結果を含めることができません。'
    );

    const context = {
      issue_info: issueInfo,
      planning_document_path: planningPath,
      implementation_context: implementationContext,
      testing_context: testingContext,
    };

    await this.runAgent(context);
  }
}
```

**例: report.ts**

```typescript
export class ReportPhase extends BasePhase {
  async execute(issueNumber: number): Promise<void> {
    const issueInfo = await this.getIssueInfo(issueNumber);
    const planningPath = this.getPlanningDocumentPath(issueNumber);

    // Reportは全Phaseの成果物を参照するため、多数のオプショナルコンテキスト
    const requirementsContext = this.buildOptionalContext(
      'requirements',
      'requirements.md',
      issueNumber,
      '要件定義書は利用できません。'
    );

    const designContext = this.buildOptionalContext(
      'design',
      'design.md',
      issueNumber,
      '設計書は利用できません。'
    );

    const implementationContext = this.buildOptionalContext(
      'implementation',
      'implementation.md',
      issueNumber,
      '実装情報は利用できません。'
    );

    const testingContext = this.buildOptionalContext(
      'testing',
      'testing.md',
      issueNumber,
      'テスト情報は利用できません。'
    );

    const documentationContext = this.buildOptionalContext(
      'documentation',
      'documentation.md',
      issueNumber,
      'ドキュメント情報は利用できません。'
    );

    const context = {
      issue_info: issueInfo,
      planning_document_path: planningPath,
      requirements_context: requirementsContext,
      design_context: designContext,
      implementation_context: implementationContext,
      testing_context: testingContext,
      documentation_context: documentationContext,
    };

    await this.runAgent(context);
  }
}
```

### 7.4 プロンプトファイルの設計

#### 7.4.1 implementation/execute.txt

**変更前**:
```markdown
## 参照ドキュメント

### 要件定義書
{requirements_document_path}

### 設計書
{design_document_path}

### テストシナリオ
{test_scenario_document_path}

上記のドキュメントに基づいて実装してください。
```

**変更後**:
```markdown
## 参照ドキュメント

### Issue情報（必須）
{issue_info}

### Planning情報（必須）
{planning_document_path}

### 要件定義書（利用可能な場合）
{requirements_context}
<!--
  存在する場合: @requirements.md への参照
  存在しない場合: "要件定義書は利用できません。Planning情報とIssue情報から要件を推測してください。"
-->

### 設計書（利用可能な場合）
{design_context}
<!--
  存在する場合: @design.md への参照
  存在しない場合: "設計書は利用できません。Issue情報とPlanning情報に基づいて適切な設計判断を行ってください。"
-->

### テストシナリオ（利用可能な場合）
{test_scenario_context}
<!--
  存在する場合: @test-scenario.md への参照
  存在しない場合: "テストシナリオは利用できません。実装時に適切なテスト考慮を行ってください。"
-->

## 実装指示

上記の利用可能なドキュメントとIssue情報に基づいて実装してください。
ドキュメントが利用できない場合は、Issue情報とPlanning情報から合理的に判断してください。
```

#### 7.4.2 test_implementation/execute.txt

```markdown
## 参照ドキュメント

### Issue情報（必須）
{issue_info}

### Planning情報（必須）
{planning_document_path}

### 実装情報（利用可能な場合）
{implementation_context}
<!--
  存在する場合: @implementation.md への参照
  存在しない場合: "実装情報は利用できません。Issue情報とPlanning情報からテストコードを推測してください。"
-->

## テストコード実装指示

上記の情報に基づいてテストコードを実装してください。
実装情報が利用できない場合は、既存のコードベースを探索し、適切なテストを作成してください。
```

#### 7.4.3 testing/execute.txt

```markdown
## 参照ドキュメント

### Issue情報（必須）
{issue_info}

### Planning情報（必須）
{planning_document_path}

### テスト実装情報（利用可能な場合）
{test_implementation_context}
<!--
  存在する場合: @test-implementation.md への参照
  存在しない場合: "テスト実装情報は利用できません。既存のテストコードを探索してテストを実行してください。"
-->

## テスト実行指示

上記の情報に基づいてテストを実行してください。
テスト実装情報が利用できない場合は、既存のテストコードを探索して実行してください。
```

#### 7.4.4 documentation/execute.txt

```markdown
## 参照ドキュメント

### Issue情報（必須）
{issue_info}

### Planning情報（必須）
{planning_document_path}

### 実装情報（利用可能な場合）
{implementation_context}
<!--
  存在する場合: @implementation.md への参照
  存在しない場合: "実装情報は利用できません。Issue情報とPlanning情報からドキュメントを作成してください。"
-->

### テスト情報（利用可能な場合）
{testing_context}
<!--
  存在する場合: @testing.md への参照
  存在しない場合: "テスト情報は利用できません。ドキュメントにテスト結果を含めることができません。"
-->

## ドキュメント作成指示

上記の利用可能な情報に基づいてドキュメントを作成してください。
実装情報やテスト情報が利用できない場合は、Issue情報とPlanning情報から可能な範囲でドキュメントを作成してください。
```

#### 7.4.5 report/execute.txt

```markdown
## 参照ドキュメント

### Issue情報（必須）
{issue_info}

### Planning情報（必須）
{planning_document_path}

### 要件定義書（利用可能な場合）
{requirements_context}

### 設計書（利用可能な場合）
{design_context}

### 実装情報（利用可能な場合）
{implementation_context}

### テスト情報（利用可能な場合）
{testing_context}

### ドキュメント情報（利用可能な場合）
{documentation_context}

## レポート作成指示

上記の利用可能な情報に基づいて最終レポートを作成してください。
各フェーズの情報が利用できない場合は、利用可能な情報のみでレポートを作成してください。

レポートには以下を含めてください：
- 実装の概要
- 完了したタスク
- テスト結果（利用可能な場合）
- 既知の制約・課題
- 今後の改善提案
```

### 7.5 --list-presetsオプションの設計

**ファイル**: `src/main.ts`

```typescript
// CLIオプションのパース
if (args.includes('--list-presets')) {
  listPresets();
  process.exit(0);
}

function listPresets(): void {
  console.log('Available Presets:\n');

  // 現行プリセットの一覧表示
  for (const [name, phases] of Object.entries(PHASE_PRESETS)) {
    const description = PRESET_DESCRIPTIONS[name] || '';
    const phaseList = phases.join(' → ');
    console.log(`  ${name.padEnd(25)} - ${description}`);
    console.log(`    Phases: ${phaseList}\n`);
  }

  console.log('\nDeprecated Presets (will be removed in 6 months):\n');

  // 非推奨プリセットの一覧表示
  for (const [oldName, newName] of Object.entries(DEPRECATED_PRESETS)) {
    console.log(`  ${oldName.padEnd(25)} → Use '${newName}' instead`);
  }

  console.log('\nUsage:');
  console.log('  npm run start -- execute --issue <number> --preset <preset-name>');
  console.log('  npm run start -- execute --issue <number> --phase <phase-name>');
  console.log('  npm run start -- execute --issue <number> --phase all');
}
```

### 7.6 後方互換性の設計

**ファイル**: `src/main.ts`

```typescript
function resolvePresetName(presetName: string): {
  resolvedName: string;
  warning?: string;
} {
  // 現行プリセット名の場合
  if (PHASE_PRESETS[presetName]) {
    return { resolvedName: presetName };
  }

  // 非推奨プリセット名の場合
  if (DEPRECATED_PRESETS[presetName]) {
    const newName = DEPRECATED_PRESETS[presetName];

    // full-workflowの特殊ケース
    if (presetName === 'full-workflow') {
      return {
        resolvedName: '', // 使用不可
        warning: `[WARNING] Preset "${presetName}" is deprecated. Please use "--phase all" instead.`,
      };
    }

    // 通常の非推奨プリセット
    return {
      resolvedName: newName,
      warning: `[WARNING] Preset "${presetName}" is deprecated. Please use "${newName}" instead. This alias will be removed in 6 months.`,
    };
  }

  // 存在しないプリセット名
  throw new Error(`[ERROR] Unknown preset: ${presetName}. Use --list-presets to see available presets.`);
}
```

## 8. セキュリティ考慮事項

### 8.1 ファイルパス操作

- `buildOptionalContext`でのファイルパス構築時、パストラバーサル攻撃を防ぐ
- `path.join`を使用し、相対パスの正規化を行う

```typescript
// パストラバーサル対策
const normalizedPath = path.normalize(filePath);
if (!normalizedPath.startsWith(process.cwd())) {
  throw new Error('Invalid file path detected');
}
```

### 8.2 ユーザー入力の検証

- プリセット名の検証（既知のプリセット名のみ許可）
- Phase名の検証（PhaseName型で型安全性を確保）

## 9. 非機能要件への対応

### 9.1 パフォーマンス

- **ファイル存在チェック**: `fs.existsSync`は同期処理だが、軽量なため問題なし
- **依存関係チェック**: 最大10個のPhaseチェックでも0.5秒以内に完了
- **プリセット一覧表示**: 0.1秒以内に完了

### 9.2 保守性

- **命名規則の統一**: プリセット名は一貫した規則に従う
- **コードの可読性**: `buildOptionalContext`は再利用可能で理解しやすい
- **拡張性**: 新しいプリセットの追加が容易（`PHASE_PRESETS`に追加するだけ）

### 9.3 互換性

- **後方互換性**: 6ヶ月間の移行期間を設定
- **既存機能への影響**: `--phase`オプションの動作に影響なし
- **Resume機能との連携**: プリセット実行中に中断した場合、Resume機能で再開可能

## 10. 変更・追加ファイルリスト

### 10.1 新規作成ファイル

なし（全て既存ファイルの拡張）

### 10.2 修正が必要な既存ファイル

#### コア機能
- `src/core/phase-dependencies.ts`
  - `PHASE_PRESETS`に7個の新規プリセット追加
  - `DEPRECATED_PRESETS`追加
  - `PRESET_DESCRIPTIONS`追加
  - `validatePhaseDependencies`強化
  - `buildErrorMessage`追加
  - `buildWarningMessage`追加

- `src/main.ts`
  - `--list-presets`オプション追加
  - `listPresets`関数追加
  - `resolvePresetName`関数追加
  - エラーメッセージ改善

#### Phase実装
- `src/phases/base-phase.ts`
  - `buildOptionalContext`メソッド追加
  - `getPhaseOutputDir`メソッド追加

- `src/phases/implementation.ts`
  - `execute`メソッドでオプショナルコンテキスト構築

- `src/phases/test-implementation.ts`
  - `execute`メソッドでオプショナルコンテキスト構築

- `src/phases/testing.ts`
  - `execute`メソッドでオプショナルコンテキスト構築

- `src/phases/documentation.ts`
  - `execute`メソッドでオプショナルコンテキスト構築

- `src/phases/report.ts`
  - `execute`メソッドでオプショナルコンテキスト構築

#### プロンプトファイル
- `src/prompts/implementation/execute.txt`
  - オプショナル参照への変更

- `src/prompts/test_implementation/execute.txt`
  - オプショナル参照への変更

- `src/prompts/testing/execute.txt`
  - オプショナル参照への変更

- `src/prompts/documentation/execute.txt`
  - オプショナル参照への変更

- `src/prompts/report/execute.txt`
  - オプショナル参照への変更

#### ドキュメント
- `README.md`
  - プリセット一覧セクション追加
  - 使い分けガイド追加
  - 移行ガイド追加

### 10.3 削除が必要なファイル

なし

## 11. 実装の順序

### Phase 1: 既存プリセットの整理（2-3時間）

**実装順序**:
1. `DEPRECATED_PRESETS`マップの追加
2. `PHASE_PRESETS`の既存プリセット名変更
3. `resolvePresetName`関数の実装
4. 後方互換性テストの実装

**依存関係**: なし（独立して実装可能）

### Phase 2: 新規プリセットの追加（3-4時間）

**実装順序**:
1. `PHASE_PRESETS`に7個の新規プリセット追加
2. `PRESET_DESCRIPTIONS`マップの追加
3. `listPresets`関数の実装
4. `--list-presets`オプションの追加
5. 新規プリセットのテスト実装

**依存関係**: Phase 1完了後（後方互換性処理が必要）

### Phase 3-1: 依存関係チェックの確認と強化（2-3時間）

**実装順序**:
1. 現在の`validatePhaseDependencies`の動作確認
2. ファイル存在チェック機能の追加
3. `buildErrorMessage`関数の実装
4. `buildWarningMessage`関数の実装
5. エラーメッセージ表示の改善
6. 依存関係チェックのテスト実装

**依存関係**: Phase 2完了後（新規プリセットのテストで依存関係チェックが必要）

### Phase 3-2: プロンプトのオプショナル参照対応（3-5時間）

**実装順序**:
1. `buildOptionalContext`メソッドの実装（base-phase.ts）
2. `getPhaseOutputDir`メソッドの実装（base-phase.ts）
3. implementation.tsの`execute`メソッド修正
4. test-implementation.tsの`execute`メソッド修正
5. testing.tsの`execute`メソッド修正
6. documentation.tsの`execute`メソッド修正
7. report.tsの`execute`メソッド修正
8. プロンプトファイル5個の修正
9. オプショナル参照のテスト実装

**依存関係**: Phase 3-1完了後（依存関係チェックとの連携が必要）

### Phase 4: ドキュメント更新（2-3時間）

**実装順序**:
1. README.mdにプリセット一覧セクション追加
2. 使い分けガイドの作成
3. 移行ガイドの作成
4. 使用例の追加

**依存関係**: Phase 2完了後（新規プリセットの仕様が確定後）

### Phase 5: テストとバリデーション（2-3時間）

**実装順序**:
1. 全プリセットの動作テスト
2. 依存関係チェックのテスト
3. オプショナル参照のテスト
4. エラーケースのテスト
5. バグ修正

**依存関係**: Phase 1-4完了後（全実装完了後）

## 12. テスト設計

### 12.1 ユニットテスト

#### プリセット定義テスト

```typescript
describe('PHASE_PRESETS', () => {
  it('should contain all required presets', () => {
    expect(PHASE_PRESETS['review-requirements']).toEqual(['planning', 'requirements']);
    expect(PHASE_PRESETS['review-design']).toEqual(['planning', 'requirements', 'design']);
    expect(PHASE_PRESETS['review-test-scenario']).toEqual(['planning', 'requirements', 'design', 'test_scenario']);
    expect(PHASE_PRESETS['quick-fix']).toEqual(['implementation', 'documentation', 'report']);
    expect(PHASE_PRESETS['implementation']).toEqual(['implementation', 'test_implementation', 'testing', 'documentation', 'report']);
    expect(PHASE_PRESETS['testing']).toEqual(['test_implementation', 'testing']);
    expect(PHASE_PRESETS['finalize']).toEqual(['documentation', 'report', 'evaluation']);
  });
});
```

#### 後方互換性テスト

```typescript
describe('resolvePresetName', () => {
  it('should resolve current preset names', () => {
    const result = resolvePresetName('quick-fix');
    expect(result.resolvedName).toBe('quick-fix');
    expect(result.warning).toBeUndefined();
  });

  it('should resolve deprecated preset names with warning', () => {
    const result = resolvePresetName('requirements-only');
    expect(result.resolvedName).toBe('review-requirements');
    expect(result.warning).toContain('deprecated');
  });

  it('should reject full-workflow with special message', () => {
    const result = resolvePresetName('full-workflow');
    expect(result.resolvedName).toBe('');
    expect(result.warning).toContain('--phase all');
  });

  it('should throw error for unknown preset', () => {
    expect(() => resolvePresetName('unknown-preset')).toThrow('Unknown preset');
  });
});
```

#### buildOptionalContextテスト

```typescript
describe('buildOptionalContext', () => {
  it('should return @filepath when file exists', () => {
    // ファイル存在をモック
    jest.spyOn(fs, 'existsSync').mockReturnValue(true);

    const phase = new ImplementationPhase();
    const result = phase['buildOptionalContext'](
      'requirements',
      'requirements.md',
      123,
      'Fallback message'
    );

    expect(result).toMatch(/@.*requirements\.md$/);
  });

  it('should return fallback message when file does not exist', () => {
    // ファイル不在をモック
    jest.spyOn(fs, 'existsSync').mockReturnValue(false);

    const phase = new ImplementationPhase();
    const result = phase['buildOptionalContext'](
      'requirements',
      'requirements.md',
      123,
      'Fallback message'
    );

    expect(result).toBe('Fallback message');
  });
});
```

#### 依存関係チェックテスト

```typescript
describe('validatePhaseDependencies', () => {
  it('should pass when all dependencies are met', () => {
    const workflowState = {
      issueNumber: 123,
      phases: {
        planning: { completed: true },
        requirements: { completed: true },
        design: { completed: true },
        test_scenario: { completed: true },
      },
    };

    const result = validatePhaseDependencies('implementation', workflowState);
    expect(result.isValid).toBe(true);
    expect(result.missingDependencies).toHaveLength(0);
  });

  it('should fail when dependencies are not met', () => {
    const workflowState = {
      issueNumber: 123,
      phases: {
        planning: { completed: false },
      },
    };

    const result = validatePhaseDependencies('implementation', workflowState);
    expect(result.isValid).toBe(false);
    expect(result.missingDependencies).toContain('planning');
    expect(result.errorMessage).toContain('NOT COMPLETED');
  });

  it('should warn when ignoreViolations is true', () => {
    const workflowState = {
      issueNumber: 123,
      phases: {},
    };

    const result = validatePhaseDependencies('implementation', workflowState, {
      ignoreViolations: true,
    });

    expect(result.isValid).toBe(true);
    expect(result.warningMessage).toContain('WARNING');
  });
});
```

### 12.2 インテグレーションテスト

#### プリセット実行テスト

```typescript
describe('Preset execution', () => {
  it('should execute quick-fix preset successfully', async () => {
    // quick-fixプリセットの実行
    const result = await executePreset('quick-fix', 123);

    // 実行されたPhaseを確認
    expect(result.executedPhases).toEqual(['implementation', 'documentation', 'report']);
    expect(result.success).toBe(true);
  });

  it('should execute review-requirements preset successfully', async () => {
    const result = await executePreset('review-requirements', 123);

    expect(result.executedPhases).toEqual(['planning', 'requirements']);
    expect(result.success).toBe(true);
  });
});
```

#### プロンプトオプショナル参照のインテグレーションテスト

```typescript
describe('Optional context in prompts', () => {
  it('should use file reference when file exists', async () => {
    // requirements.mdを作成
    await createTestFile('.ai-workflow/issue-123/01_requirements/output/requirements.md', 'Test content');

    const phase = new ImplementationPhase();
    await phase.execute(123);

    // プロンプトに@filepathが含まれることを確認
    expect(phase.lastPrompt).toContain('@');
    expect(phase.lastPrompt).toContain('requirements.md');
  });

  it('should use fallback message when file does not exist', async () => {
    // requirements.mdを削除
    await deleteTestFile('.ai-workflow/issue-123/01_requirements/output/requirements.md');

    const phase = new ImplementationPhase();
    await phase.execute(123);

    // プロンプトにフォールバックメッセージが含まれることを確認
    expect(phase.lastPrompt).toContain('要件定義書は利用できません');
  });
});
```

## 13. リスク管理

### リスク1: 依存関係チェックの現在の動作が不明確

- **影響度**: 中
- **確率**: 中
- **軽減策**:
  - Phase 3-1で現在の実装を詳細に確認（`validatePhaseDependencies`のコードレビュー）
  - テストケースを作成して実際の動作を検証
  - 予想外の動作が判明した場合は、設計を見直す

### リスク2: プロンプト変更による予期しない動作

- **影響度**: 中
- **確率**: 低
- **軽減策**:
  - オプショナル参照のフォールバックメッセージを明確に記述
  - 各Phaseで実際にAgentを実行してテスト（インテグレーションテスト）
  - Agentの挙動を注意深く監視し、問題があれば即座に修正

### リスク3: 後方互換性の維持不足

- **影響度**: 低
- **確率**: 低
- **軽減策**:
  - Deprecation warningを明確に表示
  - 旧プリセット名のエイリアスを確実に実装
  - ドキュメントに移行ガイドを明記

### リスク4: テスト工数の増加

- **影響度**: 低
- **確率**: 中
- **軽減策**:
  - テストの優先順位付け（クリティカルパスのテストを優先）
  - 自動テストの活用（ユニットテスト、インテグレーションテスト）
  - 手動テストは最小限に抑える

## 14. 成功基準

### 機能要件の達成

- [ ] 7個の新規プリセットが正常に動作する
- [ ] 既存プリセット名が新しい命名規則に準拠している
- [ ] 後方互換性が維持されている（deprecation warning付き）
- [ ] `--list-presets`オプションが正常に動作する
- [ ] 依存関係チェックが強化されている
- [ ] プロンプトのオプショナル参照が正常に動作する

### 非機能要件の達成

- [ ] `quick-fix`プリセット実行時、2-3時間以内に完了する
- [ ] 依存関係チェックが0.5秒以内に完了する
- [ ] `--list-presets`が0.1秒以内に出力される
- [ ] 既存の`--phase`オプションの動作に影響がない
- [ ] Resume機能が正常に動作する

### 品質基準の達成

- [ ] すべてのユニットテストが成功する
- [ ] すべてのインテグレーションテストが成功する
- [ ] テストカバレッジが80%以上である
- [ ] コーディング規約に準拠している
- [ ] ドキュメントが分かりやすい

---

**作成日**: 2025-01-XX
**Issue番号**: #396
**関連ドキュメント**:
- Planning Document: @.ai-workflow/issue-396/00_planning/output/planning.md
- Requirements Document: @.ai-workflow/issue-396/01_requirements/output/requirements.md
- GitHub Issue: https://github.com/tielec/infrastructure-as-code/issues/396
