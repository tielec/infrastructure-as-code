# 要件定義書: Issue #396

## 0. Planning Documentの確認

Planning Document (@.ai-workflow/issue-396/00_planning/output/planning.md) の内容を確認し、以下の戦略を踏まえて要件定義を実施します：

### 開発計画の全体像
- **実装戦略**: EXTEND（既存のPHASE_PRESTESオブジェクトを拡張）
- **テスト戦略**: UNIT_INTEGRATION（ユニットテストとインテグレーションテストの組み合わせ）
- **テストコード戦略**: BOTH_TEST（既存テストの拡張と新規テスト作成）
- **見積もり工数**: 15~21時間
- **リスクレベル**: 中

### 主要な技術的判断
1. プリセットは複数Phaseの組み合わせのみ（単一Phaseは`--phase <name>`で対応）
2. 依存関係チェック機能の確認と強化が必要
3. プロンプトのオプショナル参照対応が重要
4. 後方互換性の維持（deprecation warning付き）

## 1. 概要

### 背景
ai-workflow-v2には既にプリセット機能（`--preset`オプション）が実装されていますが、以下の問題点があります：
1. **命名規則の不一致**: `-only`, `-phase`, `-workflow`といった異なるサフィックスが混在
2. **実際の開発パターンの未カバー**: 軽微な修正、テスト追加、ドキュメント更新などの頻繁なシナリオに対応していない
3. **依存関係の不考慮**: `planning`フェーズが含まれていないプリセットが存在
4. **プロンプトの依存関係問題**: 前段Phaseの成果物が存在しない場合、プロンプトが不完全になる

### 目的
実際の開発ワークフローを分析し、プリセット機能を拡充することで以下を実現します：
- 開発効率の大幅向上（軽微な修正で6-9時間の削減）
- チーム内の開発フロー標準化
- 柔軟性の確保（プリセットでカバーされないパターンは`--phase`で対応）
- プロンプトの堅牢性向上（前段Phaseの成果物が存在しなくても動作）

### ビジネス価値
- **開発効率**: 軽微な修正で現在8-12時間かかる処理を2-3時間に短縮
- **標準化**: ベストプラクティスがプリセットに組み込まれ、新メンバーのオンボーディングが容易
- **柔軟性**: 段階的な拡張が可能

### 技術的価値
- **コードの保守性**: 統一された命名規則により可読性向上
- **堅牢性**: 依存関係チェックとオプショナル参照により、エッジケースに強い
- **拡張性**: 新しいプリセットの追加が容易

## 2. 機能要件

### 2.1 既存プリセットの整理【優先度: 高】

#### 2.1.1 命名規則の統一
- **要件**: 既存プリセット名を新しい命名規則に変更する
  - `requirements-only` → `review-requirements`
  - `design-phase` → `review-design`
  - `implementation-phase` → `implementation`
  - `full-workflow` → **削除**（`--phase all`で代替）
- **検証**: 新プリセット名で実行し、期待されるPhaseリストが実行されること

#### 2.1.2 依存関係の修正
- **要件**: 依存関係を考慮したPhaseリストに修正する
  - `review-requirements`: `['planning', 'requirements']` (planningを追加)
  - `review-design`: `['planning', 'requirements', 'design']` (planningを追加)
- **検証**: 依存関係チェックが成功し、エラーが発生しないこと

#### 2.1.3 後方互換性の維持
- **要件**: 古いプリセット名をエイリアスとして6ヶ月間サポート（deprecation warning付き）
  - `requirements-only`, `design-phase`, `implementation-phase`: 新プリセット名への移行を促す警告を表示
  - `full-workflow`: 「`--phase all`を使用してください」という明示的なメッセージを表示
- **検証**: 古いプリセット名で実行時、警告が表示され、かつ新プリセットと同じ動作をすること

### 2.2 新規プリセットの追加【優先度: 高】

#### 2.2.1 レビュー駆動パターン
- **要件**: 以下のプリセットを追加する
  - `review-requirements`: `['planning', 'requirements']`
  - `review-design`: `['planning', 'requirements', 'design']`
  - `review-test-scenario`: `['planning', 'requirements', 'design', 'test_scenario']`
- **用途**: 各フェーズでPRレビューを受けながら進める
- **検証**: 各プリセット実行時、指定されたPhaseが順番に実行されること

#### 2.2.2 実装中心パターン
- **要件**: 以下のプリセットを追加する
  - `quick-fix`: `['implementation', 'documentation', 'report']`
  - `implementation`: `['implementation', 'test_implementation', 'testing', 'documentation', 'report']`
- **用途**:
  - `quick-fix`: タイポ修正、小さなバグ修正（2-3時間）
  - `implementation`: 通常の実装フロー（実装+テスト+ドキュメント）
- **検証**:
  - `quick-fix`実行時、所要時間が3時間以内であること
  - `implementation`実行時、全ての実装関連Phaseが実行されること

#### 2.2.3 テスト中心パターン
- **要件**: 以下のプリセットを追加する
  - `testing`: `['test_implementation', 'testing']`
- **用途**: 既存実装にテストを追加
- **検証**: テストコード作成とテスト実行のみが実行されること

#### 2.2.4 ドキュメント・レポートパターン
- **要件**: 以下のプリセットを追加する
  - `finalize`: `['documentation', 'report', 'evaluation']`
- **用途**: 実装完了後の最終化（ドキュメント+レポート+評価）
- **検証**: ドキュメント作成、レポート作成、評価のみが実行されること

#### 2.2.5 プリセット一覧表示機能
- **要件**: `--list-presets`オプションを追加する
- **出力形式**:
```
Available Presets:
  review-requirements     - Planning + Requirements
  review-design           - Planning + Requirements + Design
  review-test-scenario    - Planning + Requirements + Design + TestScenario
  quick-fix               - Implementation + Documentation + Report
  implementation          - Implementation + TestImplementation + Testing + Documentation + Report
  testing                 - TestImplementation + Testing
  finalize                - Documentation + Report + Evaluation

Deprecated Presets (will be removed in 6 months):
  requirements-only       → Use 'review-requirements' instead
  design-phase            → Use 'review-design' instead
  implementation-phase    → Use 'implementation' instead
  full-workflow           → Use '--phase all' instead
```
- **検証**: `--list-presets`実行時、上記のフォーマットで出力されること

### 2.3 依存関係チェックの確認と強化【優先度: 高】

#### 2.3.1 現在の実装確認
- **要件**: 以下の動作を確認する
  1. `--phase implementation`実行時、依存Phase未完了でエラーになるか
  2. `validatePhaseDependencies`の呼び出しタイミング
  3. `skipDependencyCheck`, `ignoreDependencies`オプションの動作
- **検証**: 単体テストで各シナリオの動作を確認

#### 2.3.2 依存関係チェックの強化
- **要件**: 以下の機能を実装する
  1. **単一Phase実行時**: 依存関係チェックを必ず実行（デフォルトは厳格モード）
  2. **ファイル存在チェック**: metadata.jsonで`completed`でも、実ファイルが存在しない場合はエラー
  3. **`--ignore-dependencies`オプション**: 警告のみで実行継続（非推奨）
- **検証**:
  - 依存Phase未完了時、エラーで停止すること
  - ファイル不在時、エラーメッセージが表示されること
  - `--ignore-dependencies`使用時、警告のみで実行されること

#### 2.3.3 エラーメッセージの改善
- **要件**: 依存関係エラー時、以下の情報を表示する
```
[ERROR] Phase "implementation" requires the following phases to be completed:
  ✗ planning - .ai-workflow/issue-123/00_planning/output/planning.md NOT FOUND
  ✗ requirements - .ai-workflow/issue-123/01_requirements/output/requirements.md NOT FOUND

Options:
  1. Complete the missing phases first
  2. Use --phase all to run all phases
  3. Use --ignore-dependencies to proceed anyway (not recommended)
```
- **検証**: 依存関係エラー時、上記のフォーマットで表示されること

### 2.4 プロンプトのオプショナル参照対応【優先度: 高】

#### 2.4.1 `buildOptionalContext`ヘルパー関数の実装
- **要件**: `BasePhase`クラスに以下のヘルパー関数を追加する
```typescript
protected buildOptionalContext(
  filename: string,
  issueNumber: number,
  fallbackMessage: string
): string {
  const filePath = this.getPhaseOutputFile(<対応するPhase>, filename, issueNumber);
  if (filePath && fs.existsSync(filePath)) {
    return `@${filePath}`;
  } else {
    return fallbackMessage;
  }
}
```
- **検証**: ユニットテストで、ファイル存在時と不在時の動作を確認

#### 2.4.2 各Phaseでのオプショナルコンテキスト構築
- **要件**: 以下のPhaseで`buildOptionalContext`を使用する
  - `implementation.ts`
  - `test-implementation.ts`
  - `testing.ts`
  - `documentation.ts`
  - `report.ts`
- **例** (implementation.ts):
```typescript
const context = {
  issue_info: this.getIssueInfo(),
  planning_document_path: this.getPlanningDocumentReference(issueNumber),

  requirements_context: this.buildOptionalContext(
    'requirements.md',
    issueNumber,
    '要件定義書は利用できません。Planning情報とIssue情報から要件を推測してください。'
  ),

  design_context: this.buildOptionalContext(
    'design.md',
    issueNumber,
    '設計書は利用できません。Issue情報とPlanning情報に基づいて適切な設計判断を行ってください。'
  ),

  test_scenario_context: this.buildOptionalContext(
    'test-scenario.md',
    issueNumber,
    'テストシナリオは利用できません。実装時に適切なテスト考慮を行ってください。'
  ),
};
```
- **検証**: プロンプト構築時、ファイル不在時にフォールバックメッセージが設定されること

#### 2.4.3 プロンプトファイルの修正
- **要件**: 以下のプロンプトファイルを修正する
  - `src/prompts/implementation/execute.txt`
  - `src/prompts/test_implementation/execute.txt`
  - `src/prompts/testing/execute.txt`
  - `src/prompts/documentation/execute.txt`
  - `src/prompts/report/execute.txt`
- **修正内容** (implementation/execute.txt):
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
  存在しない場合: "要件定義書は利用できません。..."
-->

### 設計書（利用可能な場合）
{design_context}

### テストシナリオ（利用可能な場合）
{test_scenario_context}
```
- **検証**: Agent実行時、ファイル不在でもエラーにならず、適切なフォールバック動作をすること

### 2.5 ドキュメント更新【優先度: 中】

#### 2.5.1 README.mdにプリセット一覧セクション追加
- **要件**: README.mdに以下のセクションを追加する
  1. プリセット一覧テーブル（名前、含まれるPhase、用途）
  2. 使用例（各プリセットの実行コマンド）
  3. プリセット vs `--phase`の使い分けガイド
  4. 移行ガイド（古いプリセット名 → 新プリセット名）
- **検証**: ドキュメントが分かりやすく、実際に使用できること

## 3. 非機能要件

### 3.1 パフォーマンス要件
- **実行時間**: `quick-fix`プリセット実行時、2-3時間以内に完了すること
- **依存関係チェック**: 0.5秒以内に完了すること
- **レスポンス**: `--list-presets`実行時、0.1秒以内に出力されること

### 3.2 互換性要件
- **後方互換性**: 既存の古いプリセット名で6ヶ月間動作すること（deprecation warning付き）
- **既存機能への影響**: 既存の`--phase`オプションの動作に影響を与えないこと
- **Resume機能との連携**: プリセット実行中に中断した場合、Resume機能で再開できること

### 3.3 可用性・信頼性要件
- **依存関係チェック**: 依存Phase未完了時、明確なエラーメッセージで停止すること
- **エラーハンドリング**: ファイル不在時、適切なフォールバックメッセージを表示すること
- **ログ出力**: 実行中のPhase、エラー内容が明確にログに記録されること

### 3.4 保守性・拡張性要件
- **命名規則の統一**: プリセット名は一貫した規則に従うこと（カテゴリごとにサフィックス統一）
- **コードの可読性**: `buildOptionalContext`関数は再利用可能で、理解しやすいこと
- **拡張性**: 新しいプリセットの追加が容易であること（`PHASE_PRESETS`に追加するだけ）

## 4. 制約事項

### 4.1 技術的制約
- **既存コードへの影響最小化**: `EXTEND`戦略により、既存のコードベースを最大限活用
- **TypeScript型安全性**: 既存の型定義（`PhaseName`, `PhasePresets`）を維持
- **ファイルパス形式**: `@`プレフィックスを使用したAgent向けファイル参照形式を維持

### 4.2 リソース制約
- **開発工数**: 15~21時間（Phase 1-3は11-15時間で主要機能を実装）
- **テスト工数**: ユニットテストとインテグレーションテストを含む
- **ドキュメント更新**: README.mdの更新を含む

### 4.3 ポリシー制約
- **後方互換性**: 6ヶ月間の移行期間を設定
- **エラーメッセージ**: ユーザーフレンドリーで、具体的な解決策を提示
- **ログレベル**: `[INFO]`, `[WARNING]`, `[ERROR]`の統一した形式

## 5. 前提条件

### 5.1 システム環境
- **Node.js**: v18以上
- **TypeScript**: 既存のai-workflow-v2プロジェクト環境
- **Git**: バージョン管理に使用

### 5.2 依存コンポーネント
- **既存Phase実装**: `BasePhase`, 各Phase実装クラス（Planning, Requirements, etc.）
- **メタデータ管理**: `MetadataManager`, `WorkflowState`
- **依存関係管理**: `phase-dependencies.ts`の`PHASE_DEPENDENCIES`, `validatePhaseDependencies`

### 5.3 外部システム連携
- **GitHub**: Issue情報取得、コメント投稿
- **Agent（Codex/Claude）**: プロンプト実行

## 6. 受け入れ基準

### 6.1 既存プリセットの整理

**Given**: 既存のプリセット名（`requirements-only`, `design-phase`, `implementation-phase`, `full-workflow`）が存在する
**When**: 新しいプリセット名（`review-requirements`, `review-design`, `implementation`）で実行する
**Then**:
- 期待されるPhaseリストが実行される
- 依存関係チェックが成功する
- 古いプリセット名で実行時、deprecation warningが表示される

### 6.2 新規プリセットの追加

**Given**: 新規プリセット（`quick-fix`, `testing`, `finalize`, `review-test-scenario`）が定義されている
**When**: 各プリセットを実行する
**Then**:
- 指定されたPhaseが順番に実行される
- 所要時間が想定範囲内である（`quick-fix`: 2-3時間）
- エラーなく完了する

### 6.3 プリセット一覧表示

**Given**: `--list-presets`オプションが実装されている
**When**: `npm run start -- execute --list-presets`を実行する
**Then**:
- 利用可能なプリセット一覧が表示される
- 各プリセットの含まれるPhaseと用途が表示される
- 非推奨プリセットが別セクションに表示される

### 6.4 依存関係チェックの強化

**Given**: 依存Phase（planning, requirements, design）が未完了の状態
**When**: `--phase implementation`を実行する
**Then**:
- 依存関係エラーが表示される
- エラーメッセージに未完了Phaseのリストと解決策が表示される
- 実行が停止する

**Given**: 依存Phase未完了で`--ignore-dependencies`オプションを使用
**When**: `--phase implementation --ignore-dependencies`を実行する
**Then**:
- 警告メッセージが表示される
- 実行が継続される

### 6.5 ファイル存在チェック

**Given**: metadata.jsonで`completed`だが、実ファイル（requirements.md）が存在しない
**When**: `--phase implementation`を実行する
**Then**:
- ファイル不在エラーが表示される
- エラーメッセージにファイルパスが表示される
- 実行が停止する

### 6.6 プロンプトのオプショナル参照

**Given**: requirements.md, design.mdが存在しない状態
**When**: `--preset quick-fix --ignore-dependencies`を実行する
**Then**:
- プロンプト内でフォールバックメッセージが使用される
- Agentがエラーにならず、適切に動作する
- 実装Phaseが正常に完了する

### 6.7 後方互換性

**Given**: 古いプリセット名（`requirements-only`, `design-phase`, `implementation-phase`）を使用
**When**: 各プリセットを実行する
**Then**:
- deprecation warningが表示される
- 新プリセット名への移行を促すメッセージが表示される
- 新プリセットと同じPhaseが実行される

**Given**: `full-workflow`プリセットを使用
**When**: 実行する
**Then**:
- 「`--phase all`を使用してください」というメッセージが表示される

### 6.8 ドキュメント更新

**Given**: README.mdが更新されている
**When**: プリセット一覧セクションを確認する
**Then**:
- プリセット一覧テーブルが存在する
- 各プリセットの用途と使用例が記載されている
- プリセット vs `--phase`の使い分けガイドが記載されている
- 移行ガイドが記載されている

## 7. スコープ外

### 7.1 本Issue範囲外の機能
- **新しいPhaseの追加**: 既存の10個のPhase（planning ~ evaluation）以外の追加は対象外
- **Agent機能の拡張**: Codex/Claude Agentの機能拡張は対象外
- **UI/UX改善**: CLI以外のインターフェース（Web UI等）は対象外
- **並列実行**: 複数Phaseの並列実行機能は対象外

### 7.2 将来的な拡張候補
- **カスタムプリセット定義**: ユーザーが独自のプリセットを定義できる機能
- **プリセットの動的生成**: Issue内容に基づいて最適なプリセットを提案
- **Phase実行時間の最適化**: 各Phaseの実行時間を短縮する最適化
- **プリセット間の移行**: 実行中のプリセットから別のプリセットへの切り替え

### 7.3 既知の制限
- **Planning Phase必須**: 全てのプリセットでPlanning Phaseの実行を前提とする（一部プリセットを除く）
- **Resume機能との完全統合**: プリセット実行中の中断・再開は既存のResume機能に依存
- **エラーリカバリ**: Phase実行失敗時の自動リトライは既存機能に依存

## 8. 補足情報

### 8.1 プリセット設計の原則
1. **命名規則の統一**: 用途を表す名詞を使用、カテゴリごとにサフィックスを統一
2. **依存関係の明示**: 各プリセットは依存関係を考慮したPhaseリスト
3. **実用性重視**: 実際の開発パターンから逆算してプリセットを定義
4. **拡張性**: カテゴリごとに整理し、将来的な追加が容易

### 8.2 プリセット vs `--phase`の使い分け
- **プリセット**: 頻繁に使用する複数Phaseの組み合わせ（推奨）
- **`--phase all`**: 全Phaseを実行（新規Issue、初回実行）
- **`--phase <name>`**: 単一Phase実行、またはプリセットでカバーされないパターン

### 8.3 依存関係チェックのロジック

**現在の実装**:
- `validatePhaseDependencies`関数が`PHASE_DEPENDENCIES`を参照
- `skipCheck`オプション: チェックをスキップ
- `ignoreViolations`オプション: 警告のみで実行継続

**強化内容**:
- ファイル存在チェックの追加
- エラーメッセージの改善（具体的なファイルパス、解決策の提示）

### 8.4 プロンプト修正対象ファイル

| ファイルパス | 参照する前段Phase | オプショナル化対象 |
|------------|-----------------|------------------|
| `src/prompts/implementation/execute.txt` | requirements, design, test_scenario | requirements_context, design_context, test_scenario_context |
| `src/prompts/test_implementation/execute.txt` | implementation | implementation_context |
| `src/prompts/testing/execute.txt` | test_implementation | test_implementation_context |
| `src/prompts/documentation/execute.txt` | implementation, testing | implementation_context, testing_context |
| `src/prompts/report/execute.txt` | requirements, design, implementation, testing, documentation | 全ての前段Phase成果物 |

### 8.5 見積もり詳細（Planning Documentより）

| Phase | 見積もり | 内容 |
|-------|---------|------|
| Phase 1: 既存プリセット整理 | 2-3h | 命名変更、依存関係修正、後方互換性 |
| Phase 2: 新規プリセット追加 | 3-4h | 7個のプリセット追加、一覧表示機能 |
| Phase 3: 依存関係チェック + プロンプト改善 | 6-8h | 依存関係確認・強化、オプショナル参照 |
| Phase 4: ドキュメント更新 | 2-3h | README更新、使い分けガイド |
| Phase 5: テスト・検証 | 2-3h | 全プリセット、依存関係、プロンプトテスト |
| **合計** | **15-21h** | |

**最小実装（Phase 1-3）**: 11-15時間で主要な効果が得られます。

### 8.6 リスクと軽減策（Planning Documentより）

**リスク1: 依存関係チェックの現在の動作が不明確**
- **軽減策**: Phase 1で現在の実装を詳細に確認、テストケース作成

**リスク2: プロンプト変更による予期しない動作**
- **軽減策**: オプショナル参照のフォールバックメッセージを明確に記述、インテグレーションテスト実施

**リスク3: 後方互換性の維持不足**
- **軽減策**: Deprecation warningを明確に表示、エイリアスを確実に実装

**リスク4: テスト工数の増加**
- **軽減策**: テストの優先順位付け、自動テストの活用

---

**作成日**: 2025-01-XX
**Issue番号**: #396
**関連ドキュメント**:
- Planning Document: @.ai-workflow/issue-396/00_planning/output/planning.md
- CLAUDE.md: プロジェクト全体方針
- ARCHITECTURE.md: アーキテクチャ設計思想
- CONTRIBUTION.md: 開発ガイドライン
