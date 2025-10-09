# AI駆動開発自動化ワークフロー テストシナリオ（BDD）

**文書バージョン**: 2.0.0
**作成日**: 2025-10-07
**前フェーズ**: 詳細設計書 v1.0.0（更新版）

---

## 1. テスト戦略（Phase 2の判断より）

- **テスト戦略**: INTEGRATION_BDD（IntegrationテストとBDDテスト）
- **テストコード戦略**: CREATE_TEST（新規作成）
- **テストフレームワーク**:
  - BDD: behave（Gherkin/Python）
  - Integration: pytest
- **優先順位**: BDD（ユーザー視点）> Integration（技術的検証）

---

## 2. BDDテストシナリオ（Gherkin形式）

### 2.1 機能概要

```gherkin
# language: ja
フィーチャー: AI駆動開発自動化ワークフロー

  開発者として
  GitHub Issueを作成したら
  AIが自動的に要件定義～実装～テストまで行い、レビュー準備ができた状態にしてほしい

  背景:
    前提 Jenkinsが起動している
    かつ Claude API キーが設定されている
    かつ GitHub リポジトリにアクセスできる
```

---

### 2.2 シナリオ1: 正常系 - 新機能追加Issue から PR作成まで

**目的**: 開発者がIssueを作成してから、AIが全フェーズを完了してPR準備ができるまでの基本フロー

```gherkin
シナリオ: 新機能追加Issueから自動的にPR準備まで完了する

  前提 GitHubに以下のIssueが作成されている:
    """
    タイトル: ユーザーダッシュボードに統計グラフを追加

    本文:
    ユーザーダッシュボードに以下の統計グラフを追加してください：
    - 月別アクティビティグラフ
    - カテゴリ別利用状況

    技術要件:
    - Chart.jsを使用
    - データはREST APIから取得
    - レスポンシブ対応
    """

  もし 開発者がJenkinsで「AI Workflow Orchestrator」ジョブを実行する
  かつ パラメータ「ISSUE_URL」に上記IssueのURLを指定する

  ならば ジョブが成功する
  かつ 以下のフェーズが順次完了する:
    | フェーズ | 成果物 |
    | Phase 1: 要件定義 | 01-requirements.md |
    | Phase 2: 詳細設計 | 02-design.md |
    | Phase 3: テストシナリオ | 03-test-scenario.md |
    | Phase 4: 実装 | 04-implementation.md + ソースコード |
    | Phase 5: テスト実行 | 05-test-result.md |
    | Phase 6: ドキュメント | 06-documentation.md |

  かつ Gitブランチ「feature/issue-123-add-dashboard-stats」が作成されている
  かつ すべての成果物がコミットされている
  かつ マージ準備チェックリスト「merge-checklist.md」が作成されている

  かつ 開発者は以下を確認できる:
    """
    - 要件定義書で機能要件とスコープが明確になっている
    - 設計書でChart.jsの利用方針が記載されている
    - テストシナリオで正常系・異常系がカバーされている
    - 実装コードが追加されている
    - テスト結果が全て合格になっている
    - ドキュメントで使用方法が記載されている
    """

  かつ 開発者は成果物をレビューして、問題なければマージできる
```

**期待される価値**:
- 開発者は要件を書くだけで、AIが設計・実装・テストを自動生成
- レビューに集中でき、実装時間を大幅に削減
- 品質ゲートが自動的に適用される

---

### 2.3 シナリオ2: レビュー不合格 - 要件定義が不十分で再作成

**目的**: AIレビュワーが要件定義の不備を指摘し、自動的にリトライされることを検証

```gherkin
シナリオ: 要件定義が不十分な場合、AIレビュワーが指摘して再作成される

  前提 GitHubに以下の曖昧なIssueが作成されている:
    """
    タイトル: ダッシュボードを改善

    本文:
    ダッシュボードをもっと使いやすくしてください。
    """

  もし 開発者がJenkinsでワークフローを実行する

  ならば Phase 1（要件定義）で成果物が作成される
  かつ AIレビュワーが以下の指摘をする:
    """
    判定: FAIL

    ブロッカー:
    - 機能要件が抽象的すぎて実装できない（「使いやすく」が不明確）
    - スコープが未定義
    - 受け入れ基準が欠落

    改善提案:
    - 具体的な改善内容を箇条書きで記載
    - 対象画面・機能を明記
    """

  かつ Phase 1が自動的に再実行される（リトライ1回目）
  かつ AIが指摘事項を反映して、より具体的な要件定義を作成する:
    """
    ## 機能要件
    - ダッシュボードにクイックアクションボタンを追加
    - 最近使用した項目を表示
    - 通知件数をバッジ表示

    ## スコープ
    対象: トップページのダッシュボード
    対象外: 設定画面、管理画面

    ## 受け入れ基準
    - [ ] クイックアクションボタンが表示される
    - [ ] 最近5件の項目が表示される
    """

  かつ AIレビュワーが「判定: PASS_WITH_SUGGESTIONS」と判定する
  かつ Phase 2（詳細設計）に進む

  かつ 開発者は metadata.json で以下を確認できる:
    """
    phases.requirements.retry_count: 1
    phases.requirements.review_result: "PASS_WITH_SUGGESTIONS"
    """
```

**期待される価値**:
- AIが自己修正して品質を保つ
- 開発者の手戻りが発生しない
- レビュープロセスが自動化される

---

### 2.4 シナリオ3: 既存コード拡張 - バグ修正Issue

**目的**: 新規作成ではなく既存コード修正のケースを検証

```gherkin
シナリオ: 既存機能のバグ修正で、既存コードを拡張して修正する

  前提 GitHubに以下のバグ報告Issueが作成されている:
    """
    タイトル: ログイン画面でエラーメッセージが表示されない

    本文:
    ## 再現手順
    1. ログイン画面で誤ったパスワードを入力
    2. ログインボタンをクリック

    ## 期待動作
    「パスワードが正しくありません」とエラーメッセージが表示される

    ## 実際の動作
    何も表示されず、無反応

    ## 環境
    ブラウザ: Chrome 120
    """

  もし 開発者がワークフローを実行する

  ならば Phase 2（詳細設計）で以下の戦略判断がされる:
    | 判断項目 | 判断結果 | 根拠 |
    | 実装戦略 | EXTEND | 既存のログイン機能を修正 |
    | テスト戦略 | INTEGRATION_BDD | 既存機能への影響確認とE2E検証 |
    | テストコード戦略 | EXTEND_TEST | 既存テストにエラーケース追加 |

  かつ Phase 4（実装）で以下のファイルが修正される:
    """
    - src/components/LoginForm.tsx（エラー表示ロジック追加）
    - src/components/LoginForm.test.tsx（エラーケース追加）
    """

  かつ Phase 5（テスト実行）で既存テストとの整合性が検証される:
    """
    - 既存テスト: すべて合格
    - 新規テスト: エラーメッセージ表示テスト合格
    """

  かつ 開発者はバグ修正内容を確認してマージできる
```

**期待される価値**:
- バグ修正でも自動化の恩恵を受けられる
- 既存コードへの影響が自動チェックされる
- リグレッションテストが自動実行される

---

### 2.5 シナリオ4: テスト失敗フィードバック - 実装バグの自動修正

**目的**: Phase 5でテスト失敗した際、Phase 4に戻って修正されることを検証

```gherkin
シナリオ: テストが失敗した場合、AIが自動的にコードを修正する

  前提 ワークフローがPhase 5（テスト実行）まで進んでいる

  もし Phase 5でテストが失敗する:
    """
    テスト結果:
    - test_calculation: FAILED
      Expected: 100
      Actual: 99

    原因: calculation関数で切り捨てエラー
    """

  ならば AIが失敗原因を分析する
  かつ ワークフローが自動的にPhase 4（実装）に戻る
  かつ metadata.json が以下のように更新される:
    """
    phases.testing.test_failure_count: 1
    phases.implementation.retry_count: 1
    """

  かつ Phase 4（実装）で以下の修正が行われる:
    """
    修正内容:
    - calculation関数の丸め処理をMath.round()に変更
    - 境界値テストケースを追加
    """

  かつ Phase 5（テスト実行）が再実行される
  かつ すべてのテストが合格する
  かつ Phase 6（ドキュメント）に進む

  かつ 開発者は実装ログで修正履歴を確認できる:
    """
    04-implementation.md:

    ## リトライ履歴
    ### 1回目（失敗）
    - 実装内容: Math.floor()で切り捨て
    - テスト結果: 境界値で失敗

    ### 2回目（成功）
    - 修正内容: Math.round()で四捨五入に変更
    - テスト結果: すべて合格
    """
```

**期待される価値**:
- テスト駆動開発（TDD）のような自動フィードバックループ
- バグが自動的に修正される
- 開発者の手動デバッグ時間が削減される

---

### 2.6 シナリオ5: コスト上限超過 - 処理の自動停止

**目的**: Claude APIのコスト上限に達した際、処理が安全に停止することを検証

```gherkin
シナリオ: APIコストが上限に達した場合、処理が停止して開発者に通知される

  前提 config.yamlでコスト上限が「$1.00」に設定されている
  かつ 非常に大規模なIssueが作成されている（10,000行の仕様書）

  もし 開発者がワークフローを実行する

  ならば Phase 2（詳細設計）まで正常に進む
  かつ 累積コストが「$0.95」に達する

  もし Phase 3（テストシナリオ）を実行しようとする

  ならば ワークフローが以下のエラーで停止する:
    """
    Error: Cost limit exceeded

    累積コスト: $1.03
    上限: $1.00

    Phase 2までの成果物は保存されています。
    コスト上限を引き上げるか、Issueを分割してください。
    """

  かつ Jenkins ジョブが失敗ステータスになる
  かつ metadata.json が以下の状態で保存される:
    """
    cost_tracking.total_cost_usd: 1.03
    current_phase: "test_scenario"
    phases.test_scenario.status: "failed"
    error_message: "Cost limit exceeded"
    """

  かつ 開発者はSlack通知を受け取る:
    """
    AI Workflow失敗通知

    Issue: #123
    原因: コスト上限超過（$1.03 / $1.00）

    対応方法:
    1. config.yamlの上限を引き上げる
    2. Issueを小さく分割する
    3. START_PHASEパラメータで中断箇所から再開
    """

  かつ 開発者はコスト上限を「$2.00」に引き上げて再実行できる
```

**期待される価値**:
- 予期しない高額請求を防止
- 処理が途中で停止しても、成果物は保存される
- 再開が容易

---

### 2.7 シナリオ6: 複数Issue並行実行 - 競合の防止

**目的**: 複数の開発者が同時にワークフローを実行しても、競合しないことを検証

```gherkin
シナリオ: 複数のIssueが同時に処理されても、相互に影響しない

  前提 開発者Aが Issue #100 でワークフローを実行している
  かつ Phase 3（テストシナリオ）まで進んでいる

  もし 開発者Bが Issue #101 で新たにワークフローを実行する

  ならば 2つのワークフローが独立して動作する:
    | Issue | ブランチ | ワークフローディレクトリ |
    | #100 | feature/issue-100-feature-a | .ai-workflow/issue-100/ |
    | #101 | feature/issue-101-feature-b | .ai-workflow/issue-101/ |

  かつ Issue #100 のワークフローが完了する
  かつ Issue #101 のワークフローも正常に進行する

  かつ 開発者Aは Issue #100 のPRを作成できる
  かつ 開発者Bは Issue #101 のPRを作成できる

  かつ 2つのブランチに競合がない
```

**期待される価値**:
- チームでの並行作業が可能
- ワークフロー同士が干渉しない
- スケーラビリティ

---

### 2.8 シナリオ7: 中断と再開 - 途中から再開可能

**目的**: ワークフローを途中で中断しても、任意のフェーズから再開できることを検証

```gherkin
シナリオ: ワークフローを途中で中断しても、後から再開できる

  前提 開発者がワークフローを実行している
  かつ Phase 3（テストシナリオ）まで完了している

  もし Jenkinsジョブを手動でキャンセルする

  ならば Phase 3までの成果物は保存されている
  かつ metadata.jsonが以下の状態:
    """
    current_phase: "test_scenario"
    phases.test_scenario.status: "completed"
    phases.implementation.status: "pending"
    """

  もし 翌日、開発者がワークフローを再実行する
  かつ パラメータ「START_PHASE」を「implementation」に指定する

  ならば ワークフローがPhase 4（実装）から再開する
  かつ Phase 3までの成果物が読み込まれる
  かつ Phase 4以降が正常に実行される

  かつ 開発者は作業を中断しても、後から継続できる
```

**期待される価値**:
- 長時間実行でも安心して中断できる
- 失敗したフェーズだけ再実行できる
- リソースの無駄を削減

---

## 3. Integrationテストシナリオ（技術的詳細）

BDDシナリオを実装するための技術的な統合テストです。

### 3.1 Phase連携テスト

```python
# tests/integration/test_phase_flow.py
import pytest
from main import WorkflowOrchestrator

def test_phase_1_to_2_context_handoff(setup_workflow):
    """Phase 1の成果物がPhase 2に正しく引き継がれる"""
    orchestrator = WorkflowOrchestrator(issue_url="...")

    # Phase 1実行
    orchestrator.run_phase("requirements")
    req_artifact = orchestrator.get_artifact("requirements")

    # Phase 2実行
    orchestrator.run_phase("design")
    design_artifact = orchestrator.get_artifact("design")

    # 検証: Phase 2が要件定義を参照している
    assert "機能要件" in design_artifact
    assert req_artifact['summary'] in design_artifact
```

### 3.2 レビューフロー統合テスト

```python
def test_review_fail_retry_integration(setup_workflow, mock_claude):
    """レビュー不合格時の自動リトライ"""
    # 初回: 不合格
    mock_claude.review.return_value = {
        'judgment': 'FAIL',
        'blockers': ['受け入れ基準が欠落']
    }

    orchestrator = WorkflowOrchestrator(issue_url="...")
    orchestrator.run_phase("requirements")

    # リトライが発生する
    state = orchestrator.get_state()
    assert state['phases']['requirements']['retry_count'] == 1

    # 2回目: 合格
    mock_claude.review.return_value = {
        'judgment': 'PASS',
        'blockers': []
    }

    orchestrator.run_phase("requirements")
    assert state['phases']['requirements']['status'] == 'completed'
```

### 3.3 テスト失敗フィードバックループ

```python
def test_phase5_failure_to_phase4_loop(setup_workflow):
    """Phase 5失敗時、Phase 4に戻る"""
    orchestrator = WorkflowOrchestrator(issue_url="...")

    # Phase 4まで実行（バグあり実装）
    orchestrator.run_until_phase("implementation")

    # Phase 5実行（テスト失敗）
    result = orchestrator.run_phase("testing")
    assert result['test_passed'] == False

    # Phase 4に自動的に戻る
    state = orchestrator.get_state()
    assert state['current_phase'] == 'implementation'
    assert state['phases']['implementation']['retry_count'] == 1
    assert state['phases']['testing']['test_failure_count'] == 1

    # Phase 4再実行（修正）→ Phase 5成功
    orchestrator.run_phase("implementation")
    result = orchestrator.run_phase("testing")
    assert result['test_passed'] == True
```

---

## 4. テスト実行方法

### 4.1 BDDテスト実行

```bash
# BDDシナリオ全実行
behave tests/features/

# 特定シナリオのみ
behave tests/features/workflow.feature:15  # 行番号指定

# タグ指定
behave --tags=@smoke  # スモークテストのみ
behave --tags=@regression  # リグレッションテストのみ

# 日本語レポート生成
behave --format=html --outfile=report.html
```

### 4.2 Integrationテスト実行

```bash
# 統合テスト全実行
pytest tests/integration/ -v

# カバレッジ付き
pytest tests/integration/ --cov=core --cov=phases

# 並列実行
pytest tests/integration/ -n auto
```

### 4.3 ローカルテスト（モック使用）

```bash
# Claude APIをモック化してテスト
export USE_MOCK_CLAUDE=true
behave tests/features/

# 実際のAPIを使用（コスト注意）
export USE_MOCK_CLAUDE=false
behave tests/features/ --tags=@smoke
```

---

## 5. テストデータ管理

### 5.1 Gherkinフィクスチャ

```python
# tests/features/steps/fixtures.py
from behave import fixture

@fixture
def sample_issue(context):
    """サンプルIssue"""
    return {
        "number": 123,
        "title": "新機能追加",
        "body": "この機能を実装してください",
        "url": "https://github.com/org/repo/issues/123"
    }

@fixture
def mock_claude_responses(context):
    """Claudeレスポンスのモック"""
    return {
        "requirements": "# 要件定義\n\n...",
        "design": "# 設計書\n\n...",
        # ...
    }
```

### 5.2 ステップ定義

```python
# tests/features/steps/workflow_steps.py
from behave import given, when, then

@given('GitHubに以下のIssueが作成されている')
def step_given_github_issue(context):
    issue_text = context.text
    context.issue = parse_issue(issue_text)
    context.github_mock.create_issue(context.issue)

@when('開発者がJenkinsで「AI Workflow Orchestrator」ジョブを実行する')
def step_when_run_jenkins_job(context):
    context.job_result = context.jenkins_client.run_job(
        job_name="AI-Workflow/orchestrator",
        parameters={"ISSUE_URL": context.issue['url']}
    )

@then('ジョブが成功する')
def step_then_job_succeeds(context):
    assert context.job_result.is_success()

@then('以下のフェーズが順次完了する')
def step_then_phases_complete(context):
    for row in context.table:
        phase = row['フェーズ']
        artifact = row['成果物']
        assert context.workflow.get_artifact(artifact).exists()
```

---

## 6. 成功基準（Phase 3固有）

- [x] Phase 2の戦略（INTEGRATION_BDD）に沿ったテストシナリオである
- [x] ユーザー視点の振る舞いが記述されている（Gherkin形式7シナリオ）
- [x] ビジネス要件との対応が明確である
- [x] 非技術者でも理解可能な記述になっている
- [x] 主要な正常系がカバーされている（シナリオ1, 3）
- [x] 主要な異常系がカバーされている（シナリオ2, 4, 5）
- [x] エッジケースが考慮されている（シナリオ6, 7）
- [x] 期待結果が明確である（各シナリオに「期待される価値」記載）
- [x] 技術的な統合テストも補完されている（セクション3）

---

**次フェーズ**: Phase 4（実装）

**補足**:
- BDDシナリオ: 7ケース（ユーザーストーリー網羅）
- Integrationテスト: 3ケース（技術的検証）
- テストフレームワーク: behave + pytest
- レポート形式: HTML（日本語対応）
