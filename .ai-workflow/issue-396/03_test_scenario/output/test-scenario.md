# テストシナリオ: Issue #396

## 0. テスト戦略サマリー

### 選択されたテスト戦略
**UNIT_INTEGRATION**

Phase 2（設計フェーズ）で決定されたテスト戦略に基づき、以下の2種類のテストシナリオを作成します：

1. **ユニットテスト**: 個別の関数・メソッド単位のテスト
2. **インテグレーションテスト**: コンポーネント間の連携テスト

### テスト対象の範囲

#### コア機能
- `phase-dependencies.ts`: プリセット定義、依存関係チェック
- `main.ts`: CLIオプション処理、エラーメッセージ表示
- `base-phase.ts`: オプショナルコンテキスト構築ヘルパー

#### Phase実装
- `implementation.ts`, `test-implementation.ts`, `testing.ts`, `documentation.ts`, `report.ts`

#### プロンプトファイル
- 5つのプロンプトファイルのオプショナル参照動作

### テストの目的

1. **機能の正確性**: 7個の新規プリセットが正しく動作する
2. **後方互換性**: 既存プリセット名のエイリアスが正常に動作する
3. **依存関係チェック**: 単一Phase実行時の依存関係チェックが正常に動作する
4. **堅牢性**: ファイル不在時のフォールバック動作が正常に動作する
5. **エラーハンドリング**: 適切なエラーメッセージが表示される

---

## 1. ユニットテストシナリオ

### 1.1 プリセット定義テスト

#### 1.1.1 新規プリセット定義の正確性

**テストケース名**: `PHASE_PRESETS_新規プリセット_正常系`

- **目的**: 7個の新規プリセットが正しいPhaseリストを持つことを検証
- **前提条件**: `phase-dependencies.ts`が実装されている
- **入力**: なし（定数の検証）
- **期待結果**:
  ```typescript
  PHASE_PRESETS['review-requirements'] === ['planning', 'requirements']
  PHASE_PRESETS['review-design'] === ['planning', 'requirements', 'design']
  PHASE_PRESETS['review-test-scenario'] === ['planning', 'requirements', 'design', 'test_scenario']
  PHASE_PRESETS['quick-fix'] === ['implementation', 'documentation', 'report']
  PHASE_PRESETS['implementation'] === ['implementation', 'test_implementation', 'testing', 'documentation', 'report']
  PHASE_PRESETS['testing'] === ['test_implementation', 'testing']
  PHASE_PRESETS['finalize'] === ['documentation', 'report', 'evaluation']
  ```
- **テストデータ**: PHASE_PRESETS定数

---

#### 1.1.2 プリセット説明マップの存在確認

**テストケース名**: `PRESET_DESCRIPTIONS_存在確認_正常系`

- **目的**: 全てのプリセットに説明が定義されていることを検証
- **前提条件**: `PRESET_DESCRIPTIONS`が実装されている
- **入力**: PHASE_PRESETSの全キー
- **期待結果**: 各プリセット名に対応する説明文字列が存在する
- **テストデータ**:
  ```typescript
  Object.keys(PHASE_PRESETS).forEach(presetName => {
    expect(PRESET_DESCRIPTIONS[presetName]).toBeDefined();
    expect(PRESET_DESCRIPTIONS[presetName].length).toBeGreaterThan(0);
  });
  ```

---

### 1.2 後方互換性テスト

#### 1.2.1 既存プリセット名の解決（正常系）

**テストケース名**: `resolvePresetName_現行プリセット名_正常系`

- **目的**: 現行のプリセット名が正常に解決されることを検証
- **前提条件**: `resolvePresetName`関数が実装されている
- **入力**: `'quick-fix'`
- **期待結果**:
  ```typescript
  {
    resolvedName: 'quick-fix',
    warning: undefined
  }
  ```
- **テストデータ**: 現行プリセット名 (`'review-requirements'`, `'review-design'`, `'quick-fix'`, etc.)

---

#### 1.2.2 非推奨プリセット名の解決（警告付き）

**テストケース名**: `resolvePresetName_非推奨プリセット名_警告表示`

- **目的**: 非推奨プリセット名が新プリセット名に解決され、警告が表示されることを検証
- **前提条件**: `DEPRECATED_PRESETS`マップが実装されている
- **入力**: `'requirements-only'`
- **期待結果**:
  ```typescript
  {
    resolvedName: 'review-requirements',
    warning: '[WARNING] Preset "requirements-only" is deprecated. Please use "review-requirements" instead. This alias will be removed in 6 months.'
  }
  ```
- **テストデータ**:
  - `'requirements-only'` → `'review-requirements'`
  - `'design-phase'` → `'review-design'`
  - `'implementation-phase'` → `'implementation'`

---

#### 1.2.3 full-workflowプリセットの特殊処理

**テストケース名**: `resolvePresetName_full-workflow_特殊メッセージ`

- **目的**: `full-workflow`プリセットが削除され、`--phase all`への移行メッセージが表示されることを検証
- **前提条件**: `resolvePresetName`関数が実装されている
- **入力**: `'full-workflow'`
- **期待結果**:
  ```typescript
  {
    resolvedName: '',
    warning: '[WARNING] Preset "full-workflow" is deprecated. Please use "--phase all" instead.'
  }
  ```
- **テストデータ**: `'full-workflow'`

---

#### 1.2.4 存在しないプリセット名のエラー

**テストケース名**: `resolvePresetName_未知のプリセット名_エラー`

- **目的**: 存在しないプリセット名でエラーが投げられることを検証
- **前提条件**: `resolvePresetName`関数が実装されている
- **入力**: `'unknown-preset'`
- **期待結果**: 例外が投げられる
  ```typescript
  Error: '[ERROR] Unknown preset: unknown-preset. Use --list-presets to see available presets.'
  ```
- **テストデータ**: `'unknown-preset'`, `'invalid-name'`, `''`

---

### 1.3 buildOptionalContextヘルパー関数テスト

#### 1.3.1 ファイル存在時の参照生成

**テストケース名**: `buildOptionalContext_ファイル存在_ファイルパス参照`

- **目的**: ファイルが存在する場合、`@filepath`形式の参照が返されることを検証
- **前提条件**:
  - `buildOptionalContext`メソッドが実装されている
  - テスト用ファイル（requirements.md）が存在する
- **入力**:
  ```typescript
  phaseName: 'requirements',
  filename: 'requirements.md',
  issueNumber: 123,
  fallbackMessage: 'Fallback message'
  ```
- **期待結果**: `'@/path/to/.ai-workflow/issue-123/01_requirements/output/requirements.md'`（パスは環境依存）
- **テストデータ**: モックファイルシステム（`fs.existsSync`が`true`を返す）

---

#### 1.3.2 ファイル不在時のフォールバック

**テストケース名**: `buildOptionalContext_ファイル不在_フォールバックメッセージ`

- **目的**: ファイルが存在しない場合、フォールバックメッセージが返されることを検証
- **前提条件**:
  - `buildOptionalContext`メソッドが実装されている
  - テスト用ファイルが存在しない
- **入力**:
  ```typescript
  phaseName: 'requirements',
  filename: 'requirements.md',
  issueNumber: 123,
  fallbackMessage: '要件定義書は利用できません。'
  ```
- **期待結果**: `'要件定義書は利用できません。'`
- **テストデータ**: モックファイルシステム（`fs.existsSync`が`false`を返す）

---

#### 1.3.3 複数ファイルのオプショナルコンテキスト構築

**テストケース名**: `buildOptionalContext_複数ファイル_混在`

- **目的**: 一部のファイルが存在し、一部が存在しない場合の動作を検証
- **前提条件**:
  - `buildOptionalContext`メソッドが実装されている
  - requirements.mdは存在、design.mdは不在
- **入力**:
  ```typescript
  // Case 1
  phaseName: 'requirements', filename: 'requirements.md', issueNumber: 123, fallbackMessage: 'Fallback'

  // Case 2
  phaseName: 'design', filename: 'design.md', issueNumber: 123, fallbackMessage: '設計書は利用できません。'
  ```
- **期待結果**:
  - Case 1: `'@/path/to/requirements.md'`
  - Case 2: `'設計書は利用できません。'`
- **テストデータ**: モックファイルシステム（`fs.existsSync`がファイルによって異なる値を返す）

---

### 1.4 依存関係チェックテスト

#### 1.4.1 全依存関係が満たされている場合

**テストケース名**: `validatePhaseDependencies_全依存完了_成功`

- **目的**: 全ての依存Phaseが完了している場合、チェックが成功することを検証
- **前提条件**: `validatePhaseDependencies`関数が実装されている
- **入力**:
  ```typescript
  phaseName: 'implementation',
  workflowState: {
    issueNumber: 123,
    phases: {
      planning: { completed: true },
      requirements: { completed: true },
      design: { completed: true },
      test_scenario: { completed: true }
    }
  },
  options: {}
  ```
- **期待結果**:
  ```typescript
  {
    isValid: true,
    missingDependencies: [],
    missingFiles: []
  }
  ```
- **テストデータ**: 上記workflowState

---

#### 1.4.2 依存関係が不足している場合

**テストケース名**: `validatePhaseDependencies_依存不足_エラー`

- **目的**: 依存Phaseが未完了の場合、エラーが返されることを検証
- **前提条件**: `validatePhaseDependencies`関数が実装されている
- **入力**:
  ```typescript
  phaseName: 'implementation',
  workflowState: {
    issueNumber: 123,
    phases: {
      planning: { completed: false },
      requirements: { completed: false }
    }
  },
  options: {}
  ```
- **期待結果**:
  ```typescript
  {
    isValid: false,
    missingDependencies: ['planning', 'requirements', 'design', 'test_scenario'],
    missingFiles: [],
    errorMessage: '[ERROR] Phase "implementation" requires the following phases to be completed:\n  ✗ planning - NOT COMPLETED\n  ✗ requirements - NOT COMPLETED\n  ✗ design - NOT COMPLETED\n  ✗ test_scenario - NOT COMPLETED\n\nOptions:\n  1. Complete the missing phases first\n  2. Use --phase all to run all phases\n  3. Use --ignore-dependencies to proceed anyway (not recommended)\n'
  }
  ```
- **テストデータ**: 上記workflowState

---

#### 1.4.3 ignoreViolationsオプション使用時

**テストケース名**: `validatePhaseDependencies_ignoreViolations_警告のみ`

- **目的**: `ignoreViolations`オプション使用時、警告のみで継続することを検証
- **前提条件**: `validatePhaseDependencies`関数が実装されている
- **入力**:
  ```typescript
  phaseName: 'implementation',
  workflowState: {
    issueNumber: 123,
    phases: {}
  },
  options: { ignoreViolations: true }
  ```
- **期待結果**:
  ```typescript
  {
    isValid: true,  // 警告のみで継続
    missingDependencies: ['planning', 'requirements', 'design', 'test_scenario'],
    missingFiles: [],
    warningMessage: '[WARNING] Phase "implementation" has unmet dependencies, but proceeding anyway...\n  ⚠ planning - NOT COMPLETED\n  ⚠ requirements - NOT COMPLETED\n  ⚠ design - NOT COMPLETED\n  ⚠ test_scenario - NOT COMPLETED\n'
  }
  ```
- **テストデータ**: 上記workflowState

---

#### 1.4.4 ファイル存在チェック（metadata完了だがファイル不在）

**テストケース名**: `validatePhaseDependencies_ファイル不在_エラー`

- **目的**: metadata.jsonで`completed`だが実ファイルが存在しない場合、エラーが返されることを検証
- **前提条件**:
  - `validatePhaseDependencies`関数が実装されている
  - `checkFileExistence`オプションが実装されている
- **入力**:
  ```typescript
  phaseName: 'implementation',
  workflowState: {
    issueNumber: 123,
    phases: {
      planning: { completed: true },
      requirements: { completed: true }  // ファイルは不在
    }
  },
  options: { checkFileExistence: true }
  ```
- **期待結果**:
  ```typescript
  {
    isValid: false,
    missingDependencies: ['design', 'test_scenario'],
    missingFiles: [
      { phase: 'requirements', file: '/path/to/requirements.md' }
    ],
    errorMessage: '[ERROR] Phase "implementation" requires the following phases to be completed:\n  ✗ design - NOT COMPLETED\n  ✗ test_scenario - NOT COMPLETED\n  ✗ requirements - /path/to/requirements.md NOT FOUND\n\nOptions:\n  1. Complete the missing phases first\n  2. Use --phase all to run all phases\n  3. Use --ignore-dependencies to proceed anyway (not recommended)\n'
  }
  ```
- **テストデータ**: モックファイルシステム（requirements.mdが不在）

---

#### 1.4.5 skipCheckオプション使用時

**テストケース名**: `validatePhaseDependencies_skipCheck_即座に成功`

- **目的**: `skipCheck`オプション使用時、チェックがスキップされることを検証
- **前提条件**: `validatePhaseDependencies`関数が実装されている
- **入力**:
  ```typescript
  phaseName: 'implementation',
  workflowState: {
    issueNumber: 123,
    phases: {}  // 全依存が未完了
  },
  options: { skipCheck: true }
  ```
- **期待結果**:
  ```typescript
  {
    isValid: true,
    missingDependencies: [],
    missingFiles: []
  }
  ```
- **テストデータ**: 上記workflowState

---

### 1.5 エラーメッセージ構築テスト

#### 1.5.1 エラーメッセージの形式

**テストケース名**: `buildErrorMessage_形式検証_正常系`

- **目的**: エラーメッセージが期待される形式で生成されることを検証
- **前提条件**: `buildErrorMessage`関数が実装されている
- **入力**:
  ```typescript
  phaseName: 'implementation',
  missingDependencies: ['planning', 'requirements'],
  missingFiles: [
    { phase: 'design', file: '/path/to/design.md' }
  ]
  ```
- **期待結果**:
  ```
  [ERROR] Phase "implementation" requires the following phases to be completed:
    ✗ planning - NOT COMPLETED
    ✗ requirements - NOT COMPLETED
    ✗ design - /path/to/design.md NOT FOUND

  Options:
    1. Complete the missing phases first
    2. Use --phase all to run all phases
    3. Use --ignore-dependencies to proceed anyway (not recommended)
  ```
- **テストデータ**: 上記パラメータ

---

#### 1.5.2 警告メッセージの形式

**テストケース名**: `buildWarningMessage_形式検証_正常系`

- **目的**: 警告メッセージが期待される形式で生成されることを検証
- **前提条件**: `buildWarningMessage`関数が実装されている
- **入力**:
  ```typescript
  phaseName: 'implementation',
  missingDependencies: ['planning'],
  missingFiles: []
  ```
- **期待結果**:
  ```
  [WARNING] Phase "implementation" has unmet dependencies, but proceeding anyway...
    ⚠ planning - NOT COMPLETED
  ```
- **テストデータ**: 上記パラメータ

---

### 1.6 プリセット一覧表示テスト

#### 1.6.1 listPresets関数の出力形式

**テストケース名**: `listPresets_出力形式_正常系`

- **目的**: `--list-presets`の出力が期待される形式であることを検証
- **前提条件**: `listPresets`関数が実装されている
- **入力**: なし
- **期待結果**: 出力に以下が含まれる
  - "Available Presets:"
  - 各プリセット名と説明
  - "Deprecated Presets (will be removed in 6 months):"
  - 非推奨プリセット名と移行先
  - "Usage:"セクション
- **テストデータ**: なし（console.logのモック）

---

## 2. インテグレーションテストシナリオ

### 2.1 プリセット実行の統合テスト

#### 2.1.1 quick-fixプリセットのエンドツーエンド実行

**シナリオ名**: `quick-fix_プリセット実行_E2E`

- **目的**: `quick-fix`プリセットが正常に動作し、想定されるPhaseが実行されることを検証
- **前提条件**:
  - ai-workflow-v2がビルドされている
  - Issue #123が存在する
  - Planning Phaseが完了している
- **テスト手順**:
  1. `npm run start -- execute --issue 123 --preset quick-fix --ignore-dependencies`を実行
  2. 実行ログを確認
  3. 各Phase完了後のメタデータを確認
  4. 出力ファイルを確認
- **期待結果**:
  - Phase 4（Implementation）が実行される
  - Phase 7（Documentation）が実行される
  - Phase 8（Report）が実行される
  - 他のPhaseは実行されない
  - 各Phaseの出力ファイルが生成される
  - metadata.jsonが更新される
- **確認項目**:
  - [ ] `implementation.md`が生成される
  - [ ] `documentation.md`が生成される
  - [ ] `report.md`が生成される
  - [ ] metadata.jsonの`phases.implementation.completed`が`true`
  - [ ] metadata.jsonの`phases.documentation.completed`が`true`
  - [ ] metadata.jsonの`phases.report.completed`が`true`
  - [ ] 実行時間が3時間以内（非機能要件）

---

#### 2.1.2 review-requirementsプリセットの実行

**シナリオ名**: `review-requirements_プリセット実行_E2E`

- **目的**: `review-requirements`プリセットが正常に動作することを検証
- **前提条件**:
  - ai-workflow-v2がビルドされている
  - Issue #124が存在する（新規Issue）
- **テスト手順**:
  1. `npm run start -- execute --issue 124 --preset review-requirements`を実行
  2. 実行ログを確認
  3. 出力ファイルを確認
- **期待結果**:
  - Phase 0（Planning）が実行される
  - Phase 1（Requirements）が実行される
  - 他のPhaseは実行されない
  - `planning.md`と`requirements.md`が生成される
- **確認項目**:
  - [ ] `planning.md`が生成される
  - [ ] `requirements.md`が生成される
  - [ ] metadata.jsonが正しく更新される
  - [ ] Planningに依存関係が考慮されている

---

#### 2.1.3 implementationプリセットの実行

**シナリオ名**: `implementation_プリセット実行_E2E`

- **目的**: `implementation`プリセットが正常に動作し、5つのPhaseが連続実行されることを検証
- **前提条件**:
  - ai-workflow-v2がビルドされている
  - Issue #125が存在する
  - Planning, Requirements, Design, TestScenarioが完了している
- **テスト手順**:
  1. `npm run start -- execute --issue 125 --preset implementation`を実行
  2. 各Phaseの実行を監視
  3. 出力ファイルを確認
- **期待結果**:
  - Phase 4（Implementation）が実行される
  - Phase 5（TestImplementation）が実行される
  - Phase 6（Testing）が実行される
  - Phase 7（Documentation）が実行される
  - Phase 8（Report）が実行される
  - 各Phaseの出力ファイルが生成される
- **確認項目**:
  - [ ] 5つのPhaseが順番に実行される
  - [ ] 各Phase間の依存関係が正しく処理される
  - [ ] 全ての出力ファイルが生成される
  - [ ] エラーが発生しない

---

#### 2.1.4 testingプリセットの実行

**シナリオ名**: `testing_プリセット実行_E2E`

- **目的**: `testing`プリセットが正常に動作することを検証
- **前提条件**:
  - ai-workflow-v2がビルドされている
  - Issue #126が存在する
  - Implementationが完了している
- **テスト手順**:
  1. `npm run start -- execute --issue 126 --preset testing`を実行
  2. テストコード作成とテスト実行を監視
  3. 出力ファイルを確認
- **期待結果**:
  - Phase 5（TestImplementation）が実行される
  - Phase 6（Testing）が実行される
  - テストコードが生成される
  - テストが実行される
- **確認項目**:
  - [ ] `test-implementation.md`が生成される
  - [ ] `testing.md`が生成される
  - [ ] テスト実行結果が記録される

---

#### 2.1.5 finalizeプリセットの実行

**シナリオ名**: `finalize_プリセット実行_E2E`

- **目的**: `finalize`プリセットが正常に動作することを検証
- **前提条件**:
  - ai-workflow-v2がビルドされている
  - Issue #127が存在する
  - Implementation, Testing が完了している
- **テスト手順**:
  1. `npm run start -- execute --issue 127 --preset finalize`を実行
  2. ドキュメント、レポート、評価の生成を監視
  3. 出力ファイルを確認
- **期待結果**:
  - Phase 7（Documentation）が実行される
  - Phase 8（Report）が実行される
  - Phase 9（Evaluation）が実行される
  - 全ての出力ファイルが生成される
- **確認項目**:
  - [ ] `documentation.md`が生成される
  - [ ] `report.md`が生成される
  - [ ] `evaluation.md`が生成される
  - [ ] 最終化が完了する

---

### 2.2 依存関係チェックの統合テスト

#### 2.2.1 単一Phase実行時の依存関係エラー

**シナリオ名**: `単一Phase実行_依存関係不足_エラー表示`

- **目的**: 単一Phase実行時に依存関係チェックが動作し、適切なエラーメッセージが表示されることを検証
- **前提条件**:
  - ai-workflow-v2がビルドされている
  - Issue #128が存在する
  - 依存Phaseが未完了
- **テスト手順**:
  1. `npm run start -- execute --issue 128 --phase implementation`を実行
  2. エラーメッセージを確認
  3. 実行が停止することを確認
- **期待結果**:
  - 依存関係エラーが表示される
  - エラーメッセージに未完了Phaseのリストが表示される
  - 解決策（3つのオプション）が表示される
  - 実行が停止する
- **確認項目**:
  - [ ] エラーメッセージに"[ERROR] Phase \"implementation\" requires the following phases to be completed:"が含まれる
  - [ ] 未完了Phaseが"✗"マークで表示される
  - [ ] "Options:"セクションが表示される
  - [ ] 実行が停止し、implementationが実行されない

---

#### 2.2.2 --ignore-dependenciesオプション使用時の警告

**シナリオ名**: `単一Phase実行_ignore-dependencies_警告のみ`

- **目的**: `--ignore-dependencies`オプション使用時、警告のみで実行が継続されることを検証
- **前提条件**:
  - ai-workflow-v2がビルドされている
  - Issue #129が存在する
  - 依存Phaseが未完了
- **テスト手順**:
  1. `npm run start -- execute --issue 129 --phase implementation --ignore-dependencies`を実行
  2. 警告メッセージを確認
  3. 実行が継続されることを確認
  4. Phaseが完了することを確認
- **期待結果**:
  - 警告メッセージが表示される
  - 実行が継続される
  - implementationが実行される
  - プロンプトのオプショナル参照が動作する
- **確認項目**:
  - [ ] "[WARNING]"で始まる警告メッセージが表示される
  - [ ] 未完了Phaseが"⚠"マークで表示される
  - [ ] implementationが実行される
  - [ ] `implementation.md`が生成される

---

#### 2.2.3 metadata完了だがファイル不在の検出

**シナリオ名**: `ファイル存在チェック_metadata完了_ファイル不在_エラー`

- **目的**: metadata.jsonで`completed`だが実ファイルが存在しない場合、エラーが検出されることを検証
- **前提条件**:
  - ai-workflow-v2がビルドされている
  - Issue #130が存在する
  - metadata.jsonでrequirementsが`completed: true`
  - requirements.mdファイルが削除されている
- **テスト手順**:
  1. metadata.jsonを手動で編集し、requirementsを`completed: true`に設定
  2. requirements.mdファイルを削除
  3. `npm run start -- execute --issue 130 --phase implementation`を実行
  4. エラーメッセージを確認
- **期待結果**:
  - ファイル不在エラーが表示される
  - エラーメッセージにファイルパスが表示される
  - 実行が停止する
- **確認項目**:
  - [ ] エラーメッセージに"NOT FOUND"が含まれる
  - [ ] ファイルパスが表示される
  - [ ] 実行が停止する

---

### 2.3 プロンプトのオプショナル参照の統合テスト

#### 2.3.1 implementation Phase: ファイル存在時の参照

**シナリオ名**: `implementation_Phase_ファイル存在_参照動作`

- **目的**: requirements.md, design.md, test-scenario.mdが存在する場合、プロンプト内で正しく参照されることを検証
- **前提条件**:
  - ai-workflow-v2がビルドされている
  - Issue #131が存在する
  - requirements.md, design.md, test-scenario.mdが存在する
- **テスト手順**:
  1. Planning, Requirements, Design, TestScenarioを実行し、ファイルを生成
  2. `npm run start -- execute --issue 131 --phase implementation`を実行
  3. Agent実行時のプロンプトをログで確認
  4. implementationが正常に完了することを確認
- **期待結果**:
  - プロンプトに`@requirements.md`への参照が含まれる
  - プロンプトに`@design.md`への参照が含まれる
  - プロンプトに`@test-scenario.md`への参照が含まれる
  - Agentがこれらのファイルを参照して実装を行う
  - implementationが正常に完了する
- **確認項目**:
  - [ ] プロンプトに`@`プレフィックス付きファイルパスが含まれる
  - [ ] フォールバックメッセージが含まれない
  - [ ] `implementation.md`が生成される

---

#### 2.3.2 implementation Phase: ファイル不在時のフォールバック

**シナリオ名**: `implementation_Phase_ファイル不在_フォールバック動作`

- **目的**: requirements.md, design.md, test-scenario.mdが存在しない場合、フォールバックメッセージが使用されることを検証
- **前提条件**:
  - ai-workflow-v2がビルドされている
  - Issue #132が存在する
  - Planning Phaseのみ完了
  - requirements.md, design.md, test-scenario.mdが存在しない
- **テスト手順**:
  1. Planning Phaseのみ実行
  2. `npm run start -- execute --issue 132 --phase implementation --ignore-dependencies`を実行
  3. Agent実行時のプロンプトをログで確認
  4. implementationが正常に完了することを確認
- **期待結果**:
  - プロンプトに"要件定義書は利用できません。Planning情報とIssue情報から要件を推測してください。"が含まれる
  - プロンプトに"設計書は利用できません。Issue情報とPlanning情報に基づいて適切な設計判断を行ってください。"が含まれる
  - プロンプトに"テストシナリオは利用できません。実装時に適切なテスト考慮を行ってください。"が含まれる
  - Agentがエラーにならず、適切に動作する
  - implementationが正常に完了する
- **確認項目**:
  - [ ] プロンプトに`@`プレフィックスが含まれない
  - [ ] フォールバックメッセージが3つ含まれる
  - [ ] Agentがエラーにならない
  - [ ] `implementation.md`が生成される

---

#### 2.3.3 report Phase: 複数ファイルのオプショナル参照

**シナリオ名**: `report_Phase_複数ファイル_混在`

- **目的**: report Phaseで複数のファイルが混在（一部存在、一部不在）する場合の動作を検証
- **前提条件**:
  - ai-workflow-v2がビルドされている
  - Issue #133が存在する
  - implementation.mdのみ存在
  - requirements.md, design.md, testing.md, documentation.mdは不在
- **テスト手順**:
  1. implementation Phaseのみ実行
  2. `npm run start -- execute --issue 133 --phase report --ignore-dependencies`を実行
  3. Agent実行時のプロンプトをログで確認
  4. reportが正常に完了することを確認
- **期待結果**:
  - プロンプトに`@implementation.md`への参照が含まれる
  - プロンプトに他のファイルのフォールバックメッセージが含まれる
  - Agentが利用可能な情報のみでレポートを作成する
  - reportが正常に完了する
- **確認項目**:
  - [ ] プロンプトに`@implementation.md`が含まれる
  - [ ] プロンプトに"利用できません"のメッセージが4つ含まれる
  - [ ] `report.md`が生成される
  - [ ] レポート内容が利用可能な情報のみで作成されている

---

#### 2.3.4 test-implementation Phase: オプショナル参照

**シナリオ名**: `test-implementation_Phase_implementation不在_フォールバック`

- **目的**: test-implementation Phaseでimplementation.mdが不在の場合、フォールバックが動作することを検証
- **前提条件**:
  - ai-workflow-v2がビルドされている
  - Issue #134が存在する
  - Planning Phaseのみ完了
  - implementation.mdが不在
- **テスト手順**:
  1. Planning Phaseのみ実行
  2. `npm run start -- execute --issue 134 --phase test_implementation --ignore-dependencies`を実行
  3. Agent実行時のプロンプトをログで確認
  4. test_implementationが正常に完了することを確認
- **期待結果**:
  - プロンプトに"実装情報は利用できません。Issue情報とPlanning情報からテストコードを推測してください。"が含まれる
  - Agentが既存のコードベースを探索してテストを作成する
  - test_implementationが正常に完了する
- **確認項目**:
  - [ ] フォールバックメッセージが含まれる
  - [ ] Agentがコードベースを探索する
  - [ ] `test-implementation.md`が生成される

---

### 2.4 後方互換性の統合テスト

#### 2.4.1 非推奨プリセット名での実行

**シナリオ名**: `非推奨プリセット名_requirements-only_警告付き実行`

- **目的**: 非推奨プリセット名（`requirements-only`）で実行時、警告が表示され、新プリセットと同じ動作をすることを検証
- **前提条件**:
  - ai-workflow-v2がビルドされている
  - Issue #135が存在する
- **テスト手順**:
  1. `npm run start -- execute --issue 135 --preset requirements-only`を実行
  2. 警告メッセージを確認
  3. 実行されるPhaseを確認
  4. 出力ファイルを確認
- **期待結果**:
  - 警告メッセージ"[WARNING] Preset \"requirements-only\" is deprecated..."が表示される
  - `review-requirements`と同じPhase（Planning, Requirements）が実行される
  - 出力ファイルが正常に生成される
- **確認項目**:
  - [ ] 警告メッセージが表示される
  - [ ] "review-requirements"への移行が案内される
  - [ ] Planning, Requirementsが実行される
  - [ ] `planning.md`, `requirements.md`が生成される

---

#### 2.4.2 full-workflowプリセットの実行試行

**シナリオ名**: `非推奨プリセット名_full-workflow_エラーメッセージ`

- **目的**: `full-workflow`プリセット実行時、`--phase all`への移行メッセージが表示されることを検証
- **前提条件**:
  - ai-workflow-v2がビルドされている
  - Issue #136が存在する
- **テスト手順**:
  1. `npm run start -- execute --issue 136 --preset full-workflow`を実行
  2. エラー/警告メッセージを確認
  3. 実行が停止することを確認
- **期待結果**:
  - "[WARNING] Preset \"full-workflow\" is deprecated. Please use \"--phase all\" instead."が表示される
  - 実行が停止する（または代替案の提示）
- **確認項目**:
  - [ ] 警告メッセージが表示される
  - [ ] `--phase all`への移行が明示される
  - [ ] 実行が適切に処理される

---

### 2.5 CLIオプションの統合テスト

#### 2.5.1 --list-presetsオプションの実行

**シナリオ名**: `--list-presets_オプション実行_一覧表示`

- **目的**: `--list-presets`オプションが正常に動作し、プリセット一覧が表示されることを検証
- **前提条件**:
  - ai-workflow-v2がビルドされている
- **テスト手順**:
  1. `npm run start -- execute --list-presets`を実行
  2. 出力内容を確認
  3. 実行時間を測定
- **期待結果**:
  - "Available Presets:"セクションが表示される
  - 7個の現行プリセットとその説明が表示される
  - "Deprecated Presets (will be removed in 6 months):"セクションが表示される
  - 4個の非推奨プリセットと移行先が表示される
  - "Usage:"セクションが表示される
  - 実行時間が0.1秒以内（非機能要件）
- **確認項目**:
  - [ ] 出力が期待されるフォーマットである
  - [ ] 全てのプリセットが表示される
  - [ ] 説明文が分かりやすい
  - [ ] 実行時間が0.1秒以内

---

### 2.6 Resume機能との連携テスト

#### 2.6.1 プリセット実行中の中断と再開

**シナリオ名**: `プリセット実行_中断_Resume機能で再開`

- **目的**: プリセット実行中に中断した場合、Resume機能で再開できることを検証
- **前提条件**:
  - ai-workflow-v2がビルドされている
  - Issue #137が存在する
- **テスト手順**:
  1. `npm run start -- execute --issue 137 --preset implementation`を実行
  2. implementation Phase実行中に中断（Ctrl+C）
  3. metadata.jsonを確認
  4. Resume機能で再開
  5. 残りのPhaseが実行されることを確認
- **期待結果**:
  - 中断されたPhaseがmetadata.jsonに記録される
  - Resume機能が中断されたPhaseを検出する
  - 残りのPhase（test_implementation, testing, documentation, report）が実行される
  - 全てのPhaseが完了する
- **確認項目**:
  - [ ] 中断時のメタデータが正しく保存される
  - [ ] Resume機能が動作する
  - [ ] 残りのPhaseが実行される
  - [ ] 全ての出力ファイルが生成される

---

## 3. テストデータ

### 3.1 正常データ

#### プリセット名
- `'review-requirements'`
- `'review-design'`
- `'review-test-scenario'`
- `'quick-fix'`
- `'implementation'`
- `'testing'`
- `'finalize'`

#### Phase名
- `'planning'`, `'requirements'`, `'design'`, `'test_scenario'`
- `'implementation'`, `'test_implementation'`, `'testing'`
- `'documentation'`, `'report'`, `'evaluation'`

#### Issue番号
- `123`, `124`, `125`, `126`, `127`, `128`, `129`, `130`, `131`, `132`, `133`, `134`, `135`, `136`, `137`

#### WorkflowState
```typescript
{
  issueNumber: 123,
  phases: {
    planning: { completed: true },
    requirements: { completed: true },
    design: { completed: true },
    test_scenario: { completed: true }
  }
}
```

---

### 3.2 異常データ

#### 存在しないプリセット名
- `'unknown-preset'`
- `'invalid-name'`
- `''`（空文字列）
- `null`
- `undefined`

#### 存在しないPhase名
- `'invalid-phase'`
- `'unknown'`

#### 不正なIssue番号
- `-1`
- `0`
- `'abc'`（文字列）
- `null`

#### 不完全なWorkflowState
```typescript
{
  issueNumber: 123,
  phases: {}  // 全依存が未完了
}
```

---

### 3.3 境界値データ

#### 非推奨プリセット名
- `'requirements-only'`
- `'design-phase'`
- `'implementation-phase'`
- `'full-workflow'`

#### メタデータ完了だがファイル不在
```typescript
{
  issueNumber: 130,
  phases: {
    requirements: { completed: true }  // ファイルは削除済み
  }
}
```

---

## 4. テスト環境要件

### 4.1 必要なテスト環境

#### ローカル環境
- **Node.js**: v18以上
- **TypeScript**: ai-workflow-v2プロジェクトのバージョン
- **npm**: 最新版

#### CI/CD環境（将来的）
- GitHub Actions
- 自動テスト実行パイプライン

---

### 4.2 必要な外部サービス

#### GitHub
- Issue情報取得（GitHub API）
- テスト用Issueの作成

#### Agent（Codex/Claude）
- プロンプト実行
- テスト用のAgent実行環境

---

### 4.3 モック/スタブの必要性

#### ユニットテスト
- **fs.existsSync**: ファイル存在チェックのモック
- **console.log**: `listPresets`の出力検証用モック
- **Agent実行**: Agent呼び出しのスタブ（実際のAgent実行を避ける）

#### インテグレーションテスト
- **Agent実行**: 一部のテストでは実際のAgent実行が必要
- **GitHub API**: テスト用Issueの作成/取得

---

## 5. テスト実行計画

### 5.1 ユニットテストの実行

**実行コマンド**:
```bash
cd scripts/ai-workflow-v2
npm run test:unit
```

**実行タイミング**: 実装完了後、各関数・メソッドの動作を検証

**目標カバレッジ**: 80%以上

---

### 5.2 インテグレーションテストの実行

**実行コマンド**:
```bash
cd scripts/ai-workflow-v2
npm run test:integration
```

**実行タイミング**: ユニットテスト成功後、コンポーネント間の連携を検証

**目標成功率**: 100%

---

### 5.3 テスト実行の優先順位

#### 高優先度（クリティカルパス）
1. プリセット定義テスト（1.1）
2. 依存関係チェックテスト（1.4）
3. buildOptionalContextテスト（1.3）
4. quick-fixプリセットE2E（2.1.1）
5. 単一Phase実行時の依存関係エラー（2.2.1）
6. プロンプトのオプショナル参照（2.3）

#### 中優先度
1. 後方互換性テスト（1.2）
2. エラーメッセージ構築テスト（1.5）
3. 他のプリセットE2E（2.1.2-2.1.5）
4. CLIオプションテスト（2.5）

#### 低優先度
1. プリセット一覧表示テスト（1.6）
2. Resume機能との連携テスト（2.6）

---

## 6. 品質ゲート

### ✅ Phase 2の戦略に沿ったテストシナリオである
- UNIT_INTEGRATIONテスト戦略に基づき、ユニットテストとインテグレーションテストの両方を作成
- BDDテストは含まれていない（テスト戦略に含まれていないため）

### ✅ 主要な正常系がカバーされている
- プリセット定義の正確性（1.1）
- プリセット実行のE2E（2.1）
- オプショナル参照の正常動作（2.3.1）
- 依存関係チェックの正常動作（1.4.1）

### ✅ 主要な異常系がカバーされている
- 存在しないプリセット名のエラー（1.2.4）
- 依存関係不足時のエラー（1.4.2, 2.2.1）
- ファイル不在時のエラー（1.4.4, 2.2.3）
- オプショナル参照のフォールバック（2.3.2）

### ✅ 期待結果が明確である
- 全てのテストケースに具体的な期待結果を記載
- 確認項目チェックリストを用意
- 入力と出力が明確に定義されている

---

## 7. リスクと制約

### 7.1 テスト実行時のリスク

#### Agent実行時間
- **リスク**: インテグレーションテストでAgent実行が必要な場合、テスト時間が長くなる
- **軽減策**:
  - ユニットテストではAgentをモック
  - インテグレーションテストは最小限のシナリオに絞る
  - CI/CDでは並列実行

#### 外部サービス依存
- **リスク**: GitHub APIの制限、Agent実行環境の不安定性
- **軽減策**:
  - ローカルテスト用のモックデータ準備
  - CI/CDでのリトライ機能

---

### 7.2 テストデータの制約

#### テスト用Issue作成
- **制約**: GitHub上に実際のテスト用Issueを作成する必要がある
- **対応**: テスト実行前にセットアップスクリプトでIssue作成

#### ファイルシステム依存
- **制約**: テスト実行時にファイルシステムに依存する
- **対応**: テスト前後でクリーンアップ処理を実行

---

## 8. テスト完了基準

### 8.1 ユニットテスト

- [ ] 全てのユニットテストが成功する
- [ ] テストカバレッジが80%以上である
- [ ] 全ての正常系テストが成功する
- [ ] 全ての異常系テストが成功する
- [ ] 境界値テストが成功する

---

### 8.2 インテグレーションテスト

- [ ] 全てのインテグレーションテストが成功する
- [ ] 各プリセットのE2E実行が成功する
- [ ] 依存関係チェックが正常に動作する
- [ ] プロンプトのオプショナル参照が正常に動作する
- [ ] 後方互換性が維持されている

---

### 8.3 非機能要件

- [ ] `quick-fix`プリセット実行時間が3時間以内
- [ ] 依存関係チェックが0.5秒以内
- [ ] `--list-presets`実行が0.1秒以内
- [ ] 既存機能への影響がない（既存テストが全て成功）

---

## 9. 次フェーズへの引き継ぎ事項

### 9.1 実装フェーズへ

- 本テストシナリオを参照し、TDD（テスト駆動開発）で実装を進める
- ユニットテストを先に実装し、実装を進める
- インテグレーションテストは実装完了後に実行

### 9.2 テストコード実装フェーズへ

- 本テストシナリオをベースにテストコードを実装
- Jest/Mochaなどのテストフレームワークを使用
- 各テストケースを忠実に実装

---

**作成日**: 2025-01-XX
**Issue番号**: #396
**テスト戦略**: UNIT_INTEGRATION
**関連ドキュメント**:
- Planning Document: @.ai-workflow/issue-396/00_planning/output/planning.md
- Requirements Document: @.ai-workflow/issue-396/01_requirements/output/requirements.md
- Design Document: @.ai-workflow/issue-396/02_design/output/design.md
