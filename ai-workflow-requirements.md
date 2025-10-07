# AI駆動開発自動化ワークフロー 要件定義書

## 1. プロジェクト概要

### 1.1 プロジェクト名
AI駆動開発自動化ワークフロー（AI-Driven Development Workflow）

### 1.2 目的
GitHub IssueからClaude APIを活用して、要件定義～実装～テスト～ドキュメント作成まで、AIが主導する開発プロセスを自動化し、最終的なマージ判断のみ人間が行うシステムを構築する。

### 1.3 背景
- 開発プロセスの標準化と効率化が必要
- AIの能力を活用した開発の自動化・高速化を実現
- 品質を保ちながら開発サイクルを短縮
- Jenkins既存インフラを活用したCI/CD基盤の拡張

### 1.4 スコープ
- **対象**: 新機能開発、バグ修正、リファクタリング等、GitHub Issueベースの開発タスク
- **範囲**: 要件定義作成から実装、テスト、ドキュメント作成まで
- **境界**: 最終的なコードマージ判断は人間が実施

## 2. ステークホルダー

| 役割 | 名前/システム | 責任 |
|------|--------------|------|
| 開発者 | 人間 | Issue作成、最終マージ判断、エスカレーション対応 |
| AI開発エージェント | Claude (Sonnet 4.5) | 各フェーズの成果物作成 |
| AIレビュアー | Claude (Sonnet 4.5) | クリティカルシンキングによる成果物レビュー |
| オーケストレーター | Jenkins | ワークフロー実行管理、フェーズ制御 |
| バージョン管理 | Git/GitHub | 成果物の保存、履歴管理 |

## 3. 機能要件

### 3.1 ワークフローフェーズ定義

システムは以下の6フェーズを順次実行する：

| フェーズ | 入力 | 出力 | 成果物 |
|---------|------|------|--------|
| Phase 1: 要件定義 | GitHub Issue | 要件定義書 | `01-requirements.md` |
| Phase 2: 詳細設計 | 要件定義書 + Issue + 既存コードベース分析 | 設計書 + 実装戦略判断 | `02-design.md` |
| Phase 3: テストシナリオ | 要件定義書 + 設計書 + 既存テスト分析 | テストシナリオ | `03-test-scenario.md` |
| Phase 4: 実装 | 設計書 + テストシナリオ + 既存コード | ソースコード + 実装ログ | `04-implementation.md` + コード変更 |
| Phase 5: テスト実行 | 実装コード + テストシナリオ | テスト結果 | `05-test-result.md` |
| Phase 6: ドキュメント作成 | 全フェーズ成果物 | 最終ドキュメント | `06-documentation.md` |

#### 3.1.1 Phase 1: 要件定義
GitHub Issueの内容を分析し、明確な要件定義書を作成する。

**成果物内容**：
- 機能要件の整理
- 非機能要件の洗い出し
- 制約事項の明確化
- 受け入れ基準の定義

#### 3.1.2 Phase 2: 詳細設計（重要な判断フェーズ）
要件定義を基に詳細設計を行う。**このフェーズで以下の重要な判断を行う**：

**判断事項**：
1. **実装戦略**：
   - 既存コードの拡張（EXTEND）
   - 新規コード作成（CREATE）
   - リファクタリング（REFACTOR）

2. **テスト戦略**：
   - Unitテストのみ（UNIT_ONLY）
   - Integrationテストのみ（INTEGRATION_ONLY）
   - BDDテストのみ（BDD_ONLY）
   - Unit + Integration（UNIT_INTEGRATION）
   - Unit + BDD（UNIT_BDD）
   - Integration + BDD（INTEGRATION_BDD）
   - すべて（ALL）

3. **テストコード戦略**：
   - 既存テストの拡張（EXTEND_TEST）
   - 新規テスト作成（CREATE_TEST）
   - 両方（BOTH_TEST）

**成果物内容**：
- アーキテクチャ設計
- 既存コードベースの影響範囲分析
- 変更・追加が必要なファイルのリスト
- インターフェース設計
- データ構造設計
- 上記判断事項の明記と根拠

#### 3.1.3 Phase 3: テストシナリオ
Phase 2の設計と判断に基づき、適切なテストシナリオを作成する。

**動作**：
- Phase 2の「テスト戦略」判断に基づき、必要なテスト種別を作成
- Phase 2の「テストコード戦略」判断に基づき、既存テストの分析・拡張または新規作成
- BDDを含む場合は、ユーザー視点の振る舞い記述を優先

**成果物内容**（テスト戦略による）：
- **UNIT_ONLY**: Unitテストケースのみ
- **INTEGRATION_ONLY**: Integrationテストケースのみ
- **BDD_ONLY**: BDDシナリオのみ（Given-When-Then形式）
- **UNIT_INTEGRATION**: UnitテストとIntegrationテスト
- **UNIT_BDD**: UnitテストとBDDシナリオ
- **INTEGRATION_BDD**: IntegrationテストとBDDシナリオ
- **ALL**: Unit、Integration、BDDすべて
- 既存テストケースの拡張計画（EXTEND_TESTの場合）
- テストデータ設計
- 期待結果の定義

**BDDシナリオの特徴**：
- Gherkin形式（Given-When-Then）で記述
- ユーザー視点の振る舞いを記述
- ビジネス要件との対応が明確
- 非技術者でも理解可能な記述

#### 3.1.4 Phase 4: 実装
Phase 2の設計と判断に基づき、実装を行う。

**動作**：
- Phase 2の「実装戦略」判断に基づき、既存コード拡張または新規作成
- 既存コードの影響範囲を考慮した変更
- テストコードの実装（Phase 3のシナリオに基づく）

**成果物内容**：
- ソースコードの変更・追加
- テストコードの変更・追加
- 実装ログ（変更理由、技術的判断）

#### 3.1.5 Phase 5: テスト実行
Phase 3で作成したテストシナリオに基づき、テストを実行する。

**動作**：
- Unitテストの実行（必要な場合）
- Integrationテストの実行（必要な場合）
- 既存テストへの影響確認（リグレッションテスト）

**成果物内容**：
- テスト実行結果
- カバレッジレポート
- 失敗時のデバッグ情報

#### 3.1.6 Phase 6: ドキュメント作成
全フェーズの成果物を統合し、最終ドキュメントを作成する。

**成果物内容**：
- 変更内容のサマリー
- 技術的意思決定の記録
- 使用方法・動作確認手順
- マージ判断用チェックリスト

### 3.2 レビュー機能

各フェーズの成果物に対して、以下の機能を持つレビューを実施する：

#### 3.2.1 レビュー観点（共通）
1. **前提条件の妥当性**: 記載されている前提は本当に正しいか？
2. **ロジックの整合性**: 論理的な飛躍や矛盾はないか？
3. **エッジケースの考慮**: 想定外のケースは考慮されているか？
4. **実現可能性**: 提案内容は現実的に実装可能か？
5. **セキュリティとパフォーマンス**: リスクや問題はないか？

#### 3.2.1.1 Phase 2（詳細設計）の追加レビュー観点
Phase 2では上記に加えて、以下の判断の妥当性をレビューする：

1. **実装戦略の妥当性**:
   - 既存コードの分析は適切か？
   - EXTEND/CREATE/REFACTORの選択は合理的か？
   - 既存コードへの影響範囲は正しく評価されているか？

2. **テスト戦略の妥当性**:
   - UNIT/INTEGRATION/BOTHの選択は適切か？
   - テスト範囲は十分か？
   - テストの優先順位は妥当か？

3. **テストコード戦略の妥当性**:
   - 既存テストの分析は適切か？
   - EXTEND_TEST/CREATE_TEST/BOTH_TESTの選択は合理的か？
   - テストの重複や欠落はないか？

#### 3.2.2 レビュー姿勢（クリティカルシンキング）
シニアエンジニアのようなバランス感覚を持ってレビューする：

**基本姿勢**：
- すべてを疑うのではなく、重要な点に焦点を当てる
- 批判だけでなく、具体的な改善案を提示する
- **完璧ではなく「十分」を目指す**（最重要）
- 前提を鵜呑みにせず、疑問を持つべき点は指摘する

**完璧主義の回避**：
- ❌ 「もっと良い方法があるかもしれない」で不合格にしない
- ✅ 「この方法で要件を満たせている」なら合格
- ❌ 「すべての可能性を検証すべき」で不合格にしない
- ✅ 「主要なケースは考慮されている」なら合格
- ❌ 「完璧なドキュメントではない」で不合格にしない
- ✅ 「次フェーズに進むのに十分な情報がある」なら合格

**実用的なバランス**：
- 80点の解決策を今すぐ進めるか、100点を目指して時間をかけるか
- シニアエンジニアなら「80点で十分、残り20点は後で改善」と判断する
- プロジェクトを前に進めることが最優先

#### 3.2.3 レビュー判定基準

各レビューは以下の3つの判定を返す：

| 判定 | 条件 | 次アクション |
|------|------|-------------|
| **PASS** | クオリティゲートを満たしている | 次フェーズへ進む |
| **PASS_WITH_SUGGESTIONS** | クオリティゲートを満たしているが改善余地あり | 次フェーズへ進む（改善提案は記録） |
| **FAIL** | ブロッカーが存在する | 指摘事項を反映して再実行 |

#### 3.2.4 ブロッカーと改善提案の区別

レビューでは、指摘事項を以下の2カテゴリに明確に分類する：

**ブロッカー（BLOCKER）**：
- 要件を満たしていない
- 論理的な矛盾がある
- 実装不可能な設計
- 重大なセキュリティリスク
- 既存システムを破壊する変更
- 必須情報が欠落している

**改善提案（SUGGESTION）**：
- より良い代替案がある
- パフォーマンス最適化の余地
- コードの可読性向上
- ドキュメントの充実
- エッジケースの追加考慮
- テストケースの追加

**判定ルール**：
- ブロッカーが1つでもある → **FAIL**
- ブロッカーなし、改善提案あり → **PASS_WITH_SUGGESTIONS**
- ブロッカーなし、改善提案なし → **PASS**

#### 3.2.5 クオリティゲート定義

各フェーズで最低限満たすべき品質基準：

**Phase 1（要件定義）のクオリティゲート**：
- [ ] 機能要件が明確に記載されている
- [ ] 受け入れ基準が定義されている
- [ ] スコープが明確である
- [ ] 論理的な矛盾がない

**Phase 2（詳細設計）のクオリティゲート**：
- [ ] 実装戦略の判断根拠が明記されている
- [ ] テスト戦略の判断根拠が明記されている
- [ ] 既存コードへの影響範囲が分析されている
- [ ] 変更が必要なファイルがリストアップされている
- [ ] 設計が実装可能である

**Phase 3（テストシナリオ）のクオリティゲート**：
- [ ] Phase 2の戦略に沿ったテストシナリオである
- [ ] 主要な正常系がカバーされている
- [ ] 主要な異常系がカバーされている
- [ ] 期待結果が明確である

**Phase 4（実装）のクオリティゲート**：
- [ ] Phase 2の設計に沿った実装である
- [ ] 既存コードの規約に準拠している
- [ ] 基本的なエラーハンドリングがある
- [ ] テストコードが実装されている
- [ ] 明らかなバグがない

**Phase 5（テスト実行）のクオリティゲート**：
- [ ] テストが実行されている
- [ ] 主要なテストケースが成功している
- [ ] 失敗したテストは分析されている

**Phase 6（ドキュメント）のクオリティゲート**：
- [ ] 変更内容が要約されている
- [ ] マージ判断に必要な情報が揃っている
- [ ] 動作確認手順が記載されている

**重要な原則**：
- これらのゲートを満たせば**合格**
- 完璧である必要はない
- 追加の改善提案は歓迎だが、合格/不合格には影響しない

### 3.3 リトライ機能

**基本ルール**：
- 各フェーズは最大**3回**まで再実行可能
- レビューが**FAIL**の場合のみリトライ
- **PASS**または**PASS_WITH_SUGGESTIONS**は次フェーズへ進む（リトライ不要）
- 3回連続でFAILの場合、人間へエスカレーション

**リトライ時の動作**：
- ブロッカー指摘事項を入力に加えて再実行
- 前回の成果物も参照可能
- リトライ回数はmetadata.jsonに記録

**エスカレーション条件**：
- 3回連続FAIL → 人間介入が必要
- エスカレーション時には全履歴（成果物、レビュー結果）を提示
- 人間が判断：強制PASS / 要件変更 / プロジェクト中止

### 3.4 コンテキスト管理

#### 3.4.1 作業ブランチ戦略
```
main
  └─ feature/issue-{issue_number}-{title}
       └─ .ai-workflow/
            └─ issue-{issue_number}/
                 ├─ metadata.json
                 ├─ 01-requirements.md
                 ├─ 01-requirements-review.md
                 ├─ 02-design.md
                 ├─ 02-design-review.md
                 ├─ 03-test-scenario.md
                 ├─ 03-test-scenario-review.md
                 ├─ 04-implementation.md
                 ├─ 04-implementation-review.md
                 ├─ 05-test-result.md
                 ├─ 05-test-result-review.md
                 ├─ 06-documentation.md
                 ├─ 06-documentation-review.md
                 └─ merge-checklist.md
```

#### 3.4.2 metadata.json 構造
```json
{
  "issue_number": "123",
  "issue_url": "https://github.com/org/repo/issues/123",
  "issue_title": "機能追加タイトル",
  "workflow_version": "1.0.0",
  "current_phase": "requirements",
  "design_decisions": {
    "implementation_strategy": null,
    "test_strategy": null,
    "test_code_strategy": null
  },
  "phases": {
    "requirements": {
      "status": "in_progress",
      "retry_count": 0,
      "started_at": "2025-10-07T10:00:00Z",
      "completed_at": null,
      "review_result": null
    },
    "design": {
      "status": "pending",
      "retry_count": 0,
      "started_at": null,
      "completed_at": null,
      "review_result": null,
      "decisions": {
        "implementation_strategy": null,
        "test_strategy": null,
        "test_code_strategy": null
      }
    },
    "test_scenario": {
      "status": "pending",
      "retry_count": 0,
      "started_at": null,
      "completed_at": null,
      "review_result": null,
      "applied_test_strategy": null
    },
    "implementation": {
      "status": "pending",
      "retry_count": 0,
      "started_at": null,
      "completed_at": null,
      "review_result": null,
      "applied_implementation_strategy": null
    },
    "testing": {
      "status": "pending",
      "retry_count": 0,
      "started_at": null,
      "completed_at": null,
      "review_result": null
    },
    "documentation": {
      "status": "pending",
      "retry_count": 0,
      "started_at": null,
      "completed_at": null,
      "review_result": null
    }
  },
  "created_at": "2025-10-07T10:00:00Z",
  "updated_at": "2025-10-07T10:30:00Z"
}
```

**design_decisions フィールド説明**：
- `implementation_strategy`: `EXTEND` | `CREATE` | `REFACTOR`
- `test_strategy`: `UNIT_ONLY` | `INTEGRATION_ONLY` | `BOTH`
- `test_code_strategy`: `EXTEND_TEST` | `CREATE_TEST` | `BOTH_TEST`

これらの判断はPhase 2で決定され、Phase 3以降で参照される。

#### 3.4.3 成果物管理
- 各フェーズの成果物はGitにコミット
- コミットメッセージ形式: `[AI-Workflow][Phase {N}] {phase_name}: {status}`
- 例: `[AI-Workflow][Phase 1] requirements: completed`

### 3.5 Jenkins Job要件

#### 3.5.1 Job構成
- **Job数**: 1つ（`AI-Workflow/orchestrator`）
- **実装方式**: Jenkinsfile（パイプライン） + Pythonスクリプト

#### 3.5.2 Jenkinsパラメータ
| パラメータ名 | 型 | 必須 | 説明 |
|-------------|-----|------|------|
| ISSUE_URL | String | ✓ | GitHub Issue URL |
| START_PHASE | Choice | - | 開始フェーズ（デフォルト: requirements） |
| DRY_RUN | Boolean | - | ドライラン実行（デフォルト: false） |

#### 3.5.3 Jenkins Stage構成
1. **Initialize**: ワークフロー初期化、ブランチ作成
2. **Phase 1: Requirements**: 要件定義作成
3. **Phase 1: Review**: 要件定義レビュー
4. **Phase 2: Design**: 詳細設計作成
5. **Phase 2: Review**: 詳細設計レビュー
6. **Phase 3: Test Scenario**: テストシナリオ作成
7. **Phase 3: Review**: テストシナリオレビュー
8. **Phase 4: Implementation**: 実装
9. **Phase 4: Review**: 実装レビュー
10. **Phase 5: Testing**: テスト実行
11. **Phase 5: Review**: テスト結果レビュー
12. **Phase 6: Documentation**: ドキュメント作成
13. **Phase 6: Review**: ドキュメントレビュー
14. **Finalize**: マージチェックリスト作成、PR作成

### 3.6 Pythonスクリプト要件

#### 3.6.1 ディレクトリ構造
```
scripts/ai-workflow/
├── main.py                    # CLIエントリーポイント
├── requirements.txt           # 依存パッケージ
├── config.yaml                # 設定ファイル
├── core/
│   ├── claude_client.py       # Claude API クライアント
│   ├── git_operations.py      # Git操作
│   ├── context_manager.py     # コンテキスト管理
│   └── workflow_state.py      # ワークフロー状態管理
├── phases/
│   ├── base_phase.py          # フェーズ基底クラス
│   ├── requirements.py
│   ├── design.py
│   ├── test_scenario.py
│   ├── implementation.py
│   ├── testing.py
│   └── documentation.py
├── reviewers/
│   ├── base_reviewer.py
│   └── critical_thinking.py
├── prompts/
│   ├── requirements.txt
│   ├── design.txt
│   └── ...
└── tests/
    └── ...
```

#### 3.6.2 CLIコマンド定義
```bash
# 初期化
python main.py init --issue-url <URL>

# フェーズ実行
python main.py execute --phase <phase_name>

# レビュー実行
python main.py review --phase <phase_name>

# 状態確認
python main.py status

# クリーンアップ
python main.py cleanup
```

#### 3.6.3 依存ライブラリ
- `anthropic`: Claude API クライアント
- `click`: CLIフレームワーク
- `gitpython`: Git操作
- `pyyaml`: 設定ファイル読み込み
- `requests`: GitHub API呼び出し
- `pytest`: テストフレームワーク

## 4. 非機能要件

### 4.1 パフォーマンス要件

| 項目 | 要件 |
|------|------|
| 1フェーズ実行時間 | 10分以内（実装フェーズは除く） |
| 実装フェーズ実行時間 | 30分以内 |
| 全ワークフロー実行時間 | 2時間以内（リトライなしの場合） |
| Claude APIタイムアウト | 120秒 |

### 4.2 可用性要件

| 項目 | 要件 |
|------|------|
| Claude APIエラー時リトライ | 指数バックオフで最大3回 |
| Git操作エラー | 即座に失敗、人間介入 |
| ワークフロー中断時の再開 | START_PHASEパラメータで任意フェーズから再開可能 |

### 4.3 保守性要件

- Pythonコードは`black`、`pylint`、`mypy`でリント済み
- 各フェーズは独立してテスト可能
- ローカル環境でのデバッグが容易
- ログは構造化され、トレース可能

### 4.4 セキュリティ要件

| 項目 | 要件 |
|------|------|
| Claude APIキー | Jenkins Credentials Pluginで管理 |
| GitHub Token | Jenkins Credentials Pluginで管理 |
| 認証情報のログ出力 | 禁止（マスキング必須） |
| 生成コードのセキュリティチェック | レビューフェーズで実施 |

### 4.5 拡張性要件

- 新しいフェーズの追加が容易
- レビューロジックのカスタマイズが可能
- 他のLLM（GPT-4等）への切り替えが可能
- Jenkins以外のCI/CD（GitHub Actions等）への移植が可能

## 5. 制約事項

### 5.1 技術的制約
- Claude API: Pro Max契約（API利用可能）
- Jenkins環境: 既存のJenkinsインフラを使用
- Git: GitHub上のリポジトリ
- Python: バージョン 3.9以上
- OS: Windows環境（開発者PC）、Linux環境（Jenkins実行環境）

### 5.2 運用制約
- 最終マージ判断は必ず人間が実施
- 3回連続レビュー不合格時は人間へエスカレーション
- 機密情報を含むIssueには使用しない（将来対応）

### 5.3 スコープ外
- リアルタイムモニタリングUI（将来対応）
- マルチリポジトリ対応（将来対応）
- 複数Issue同時実行（将来対応）
- 既存PRへの適用（将来対応）

## 6. 成功基準

### 6.1 機能面
- [ ] GitHub Issueからワークフロー起動が可能
- [ ] 6つのフェーズすべてが自動実行される
- [ ] 各フェーズでレビューが実施され、合格/不合格判定される
- [ ] レビュー不合格時、最大3回まで自動リトライされる
- [ ] すべての成果物がGitにコミットされる
- [ ] 最終的にマージ用のチェックリストが作成される

### 6.2 品質面
- [ ] AIレビュアーがクリティカルシンキングで適切に指摘する
- [ ] AIレビュアーがブロッカーと改善提案を明確に区別できる
- [ ] クオリティゲートを満たした成果物が適切にPASS判定される
- [ ] 完璧主義による無限ループが発生しない
- [ ] 生成されたコードがリポジトリのコーディング規約に準拠
- [ ] エラーハンドリングが適切に動作
- [ ] ログが十分にトレース可能

### 6.3 運用面
- [ ] 開発者がJenkinsから簡単に起動できる
- [ ] 実行中のフェーズがJenkins UIで可視化される
- [ ] エラー時に適切な通知が行われる
- [ ] Pythonスクリプトが単独でテスト可能

## 7. リスクと対策

| リスク | 影響度 | 対策 |
|--------|--------|------|
| **完璧主義による停滞** | **最高** | **PASS/PASS_WITH_SUGGESTIONS/FAILの3段階判定**<br>**ブロッカーと改善提案の明確な区別**<br>**クオリティゲート定義（最低基準の明確化）**<br>**「80点で十分」の原則を徹底** |
| Claude APIレート制限 | 高 | 指数バックオフリトライ、エラー通知 |
| 無限ループ（レビュー不合格連続） | 中 | 3回上限設定、人間エスカレーション<br>PASS_WITH_SUGGESTIONSで前進を優先 |
| レビューが甘すぎる | 中 | クオリティゲート（最低基準）の明確な定義<br>ブロッカー判定の厳格化 |
| Git競合 | 中 | フィーチャーブランチ分離、人間介入 |
| 生成コードの品質問題 | 高 | レビューフェーズでのクオリティゲートチェック、最終人間確認 |
| Jenkins環境障害 | 中 | 任意フェーズからの再開機能 |

## 8. マイルストーン

| マイルストーン | 完了条件 | 想定期間 |
|---------------|----------|---------|
| M1: 基盤実装 | Pythonスクリプト骨格、Claude APIクライアント完成 | 2週間 |
| M2: Phase 1実装 | 要件定義フェーズとレビューが動作 | 1週間 |
| M3: 全フェーズ実装 | Phase 2-6すべて実装完了 | 3週間 |
| M4: Jenkins統合 | JenkinsからPythonスクリプト呼び出し動作 | 1週間 |
| M5: テスト・調整 | エンドツーエンドテスト、バグ修正 | 2週間 |

## 9. 用語集

| 用語 | 定義 |
|------|------|
| フェーズ | ワークフローの1ステップ（要件定義、設計など） |
| レビュー | AIによる成果物の検証プロセス |
| クリティカルシンキング | 前提を疑い、論理的整合性を検証する思考法 |
| リトライ | レビュー不合格時の再実行 |
| エスカレーション | 3回リトライ失敗時の人間への通知 |
| コンテキスト | 前フェーズからの情報引き継ぎ |
| メタデータ | ワークフロー状態を管理するJSON |
| クオリティゲート | 各フェーズで最低限満たすべき品質基準 |
| ブロッカー | 次フェーズに進めない重大な問題（FAIL判定の原因） |
| 改善提案 | あったほうが良いが必須ではない提案（PASS_WITH_SUGGESTIONSの原因） |
| PASS | レビュー合格（ブロッカーなし、改善提案なし） |
| PASS_WITH_SUGGESTIONS | レビュー合格（ブロッカーなし、改善提案あり） |
| FAIL | レビュー不合格（ブロッカーあり）|
| 実装戦略 | Phase 2で判断する実装方針（EXTEND/CREATE/REFACTOR） |
| テスト戦略 | Phase 2で判断するテスト種別（UNIT_ONLY/INTEGRATION_ONLY/BOTH） |
| テストコード戦略 | Phase 2で判断するテストコード方針（EXTEND_TEST/CREATE_TEST/BOTH_TEST） |
| EXTEND | 既存コードを拡張する実装戦略 |
| CREATE | 新規にコードを作成する実装戦略 |
| REFACTOR | 既存コードをリファクタリングする実装戦略 |
| UNIT_ONLY | Unitテストのみを実装するテスト戦略 |
| INTEGRATION_ONLY | Integrationテストのみを実装するテスト戦略 |
| BDD_ONLY | BDDテストのみを実装するテスト戦略 |
| UNIT_INTEGRATION | UnitテストとIntegrationテストを実装するテスト戦略 |
| UNIT_BDD | UnitテストとBDDテストを実装するテスト戦略 |
| INTEGRATION_BDD | IntegrationテストとBDDテストを実装するテスト戦略 |
| ALL | Unit、Integration、BDDすべてを実装するテスト戦略 |
| BDD | Behavior-Driven Development（振る舞い駆動開発） |
| Gherkin | BDDシナリオ記述言語（Given-When-Then形式） |
| EXTEND_TEST | 既存テストケースを拡張するテストコード戦略 |
| CREATE_TEST | 新規にテストケースを作成するテストコード戦略 |
| BOTH_TEST | 既存テスト拡張と新規テスト作成の両方を行うテストコード戦略 |

## 10. 付録

### 10.1 参考資料
- `CLAUDE.md`: プロジェクト全体のガイドライン
- `jenkins/CONTRIBUTION.md`: Jenkins開発ガイドライン
- `scripts/CONTRIBUTION.md`: スクリプト開発ガイドライン
- Anthropic Claude API ドキュメント

### 10.2 関連Issue
- （このワークフロー自体を管理するIssue番号をここに記載）

---

## 変更履歴

| バージョン | 日付 | 変更内容 |
|-----------|------|---------|
| 1.0.0 | 2025-10-07 | 初版作成 |
| 1.1.0 | 2025-10-07 | Phase 2の戦略判断機能を追加（実装戦略、テスト戦略、テストコード戦略）<br>各フェーズの詳細説明を追加<br>metadata.jsonにdesign_decisions追加<br>Phase 2専用のレビュー観点追加<br>用語集に戦略関連用語追加 |
| 1.2.0 | 2025-10-07 | **完璧主義回避の仕組みを追加**<br>- レビュー判定を3段階に変更（PASS/PASS_WITH_SUGGESTIONS/FAIL）<br>- ブロッカーと改善提案の明確な区別<br>- 各フェーズのクオリティゲート定義<br>- 「80点で十分」の原則を明記<br>- レビュー姿勢に完璧主義回避の具体例を追加<br>- リスクに「完璧主義による停滞」を最高影響度で追加<br>- 用語集にレビュー関連用語を追加 |

---

**文書バージョン**: 1.2.0
**作成日**: 2025-10-07
**最終更新日**: 2025-10-07
**作成者**: Claude Code
**レビュアー**: （人間のレビュー待ち）
