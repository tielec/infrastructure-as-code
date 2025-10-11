# テストシナリオ - Issue #324

## 0. Planning Documentの確認

Planning Phase（Phase 0）で作成された計画書を確認しました。以下の重要事項を踏まえてテストシナリオを作成します：

### 開発戦略の概要（Planning Documentより）
- **複雑度**: 中程度
- **見積もり工数**: 8時間
- **リスクレベル**: 低
- **実装戦略**: CREATE（新規ファイル作成）
- **テスト戦略**: UNIT_INTEGRATION（ユニット + 統合テスト）
- **テストコード戦略**: CREATE_TEST（新規テストファイル作成）

### 主要な実装箇所（Planning & Design Documentより）
- **新規作成**: `scripts/ai-workflow/phases/test_implementation.py`（約300行）
- **修正**: `scripts/ai-workflow/main.py`（phase選択肢追加）
- **修正**: `scripts/ai-workflow/phases/__init__.py`（エクスポート追加）
- **修正**: `scripts/ai-workflow/phases/report.py`（Phase番号更新）

---

## 1. テスト戦略サマリー

### 選択されたテスト戦略
**UNIT_INTEGRATION**（Phase 2で決定済み）

### テスト対象の範囲

**1. ユニットテスト対象**:
- TestImplementationPhaseクラスの各メソッド
  - `__init__()`: 初期化処理
  - `execute()`: テストコード実装処理
  - `review()`: テストコードレビュー処理
  - `revise()`: テストコード修正処理
- main.pyのphase_classes辞書更新
- phases/__init__.pyのエクスポート

**2. 統合テスト対象**:
- Phase 4（implementation）→ Phase 5（test_implementation）→ Phase 6（testing）の連携
- metadata.jsonの更新フロー
- Git auto-commit & push動作
- 8フェーズワークフロー全体（Phase 0〜8）

### テストの目的

1. **ユニットテスト**:
   - TestImplementationPhaseクラスが正しく動作することを検証
   - 各メソッドが期待通りの結果を返すことを確認
   - エラーハンドリングが適切に機能することを確認

2. **統合テスト**:
   - 8フェーズワークフローが正常に実行されることを検証
   - Phase間の依存関係が正しく機能することを確認
   - 既存の7フェーズワークフローとの後方互換性を確認

---

## 2. Unitテストシナリオ

### 2.1 TestImplementationPhase.__init__()

#### テストケース: test_init_正常系

- **目的**: TestImplementationPhaseクラスが正しく初期化されることを検証
- **前提条件**:
  - BasePhaseが正常にインポート可能
  - ClaudeAgentClient、MetadataManagerが正常に動作
- **入力**:
  - `issue_number=324`
  - `working_dir=/tmp/jenkins-386ec346/workspace/AI_Workflow/ai_workflow_orchestrator`
- **期待結果**:
  - `phase_name='test_implementation'`が設定される
  - `output_dir=.ai-workflow/issue-324/05_test_implementation/output/`が設定される
  - `execute_dir=.ai-workflow/issue-324/05_test_implementation/execute/`が設定される
  - `review_dir=.ai-workflow/issue-324/05_test_implementation/review/`が設定される
  - 例外が発生しない
- **テストデータ**: 上記入力パラメータ

---

### 2.2 TestImplementationPhase.execute()

#### テストケース: test_execute_正常系

- **目的**: テストコード実装が正常に実行されることを検証
- **前提条件**:
  - Phase 0〜4が正常に完了している
  - 以下のファイルが存在する:
    - `.ai-workflow/issue-324/00_planning/output/planning.md`
    - `.ai-workflow/issue-324/01_requirements/output/requirements.md`
    - `.ai-workflow/issue-324/02_design/output/design.md`
    - `.ai-workflow/issue-324/03_test_scenario/output/test-scenario.md`
    - `.ai-workflow/issue-324/04_implementation/output/implementation.md`
  - metadata.jsonにtest_strategy='UNIT_INTEGRATION'が設定されている
  - metadata.jsonにtest_code_strategy='CREATE_TEST'が設定されている
- **入力**: なし（execute()は引数なし）
- **期待結果**:
  - 戻り値: `{'success': True, 'output': '<test-implementation.mdのパス>', 'error': None}`
  - `.ai-workflow/issue-324/05_test_implementation/output/test-implementation.md`が生成される
  - `.ai-workflow/issue-324/05_test_implementation/execute/`配下にログが保存される
  - metadata.jsonのtest_implementationステータスが'completed'に更新される
- **テストデータ**: モックファイル（requirements.md、design.md等）

---

#### テストケース: test_execute_必須ファイル不在エラー

- **目的**: 必須ファイルが存在しない場合にエラーが返されることを検証
- **前提条件**:
  - `requirements.md`が存在しない
- **入力**: なし
- **期待結果**:
  - 戻り値: `{'success': False, 'output': None, 'error': '必要なファイルが見つかりません: <パス>'}`
  - test-implementation.mdが生成されない
  - metadata.jsonのstatusが'failed'に更新される
- **テストデータ**: なし

---

#### テストケース: test_execute_テスト戦略未定義エラー

- **目的**: テスト戦略が設計フェーズで決定されていない場合にエラーが返されることを検証
- **前提条件**:
  - 必須ファイルは存在する
  - metadata.jsonにtest_strategyが含まれていない
- **入力**: なし
- **期待結果**:
  - 戻り値: `{'success': False, 'output': None, 'error': 'テスト戦略が設計フェーズで決定されていません。Phase 2を先に実行してください。'}`
  - test-implementation.mdが生成されない
  - metadata.jsonのstatusが'failed'に更新される
- **テストデータ**: metadata.json（test_strategy未定義）

---

#### テストケース: test_execute_出力ファイル生成失敗エラー

- **目的**: Claude Agent SDK実行後に出力ファイルが生成されない場合のエラー処理を検証
- **前提条件**:
  - 必須ファイルは存在する
  - test_strategyは定義されている
  - Claude Agent SDKが実行されるが、test-implementation.mdが生成されない
- **入力**: なし
- **期待結果**:
  - 戻り値: `{'success': False, 'output': None, 'error': 'test-implementation.mdが生成されませんでした: <パス>'}`
  - metadata.jsonのstatusが'failed'に更新される
- **テストデータ**: モックClaudeAgentClient（出力ファイル生成なし）

---

### 2.3 TestImplementationPhase.review()

#### テストケース: test_review_正常系_PASS

- **目的**: テストコードレビューが正常に実行され、PASSが返されることを検証
- **前提条件**:
  - execute()が正常に完了している
  - `test-implementation.md`が存在する
  - 設計書、テストシナリオ、実装ログが存在する
- **入力**: なし
- **期待結果**:
  - 戻り値: `{'result': 'PASS', 'feedback': '<フィードバック内容>', 'suggestions': []}`
  - `.ai-workflow/issue-324/05_test_implementation/review/result.md`が生成される
  - レビューログが保存される
- **テストデータ**: モックtest-implementation.md（品質良好）

---

#### テストケース: test_review_正常系_PASS_WITH_SUGGESTIONS

- **目的**: テストコードレビューでPASS_WITH_SUGGESTIONSが返されることを検証
- **前提条件**:
  - execute()が正常に完了している
  - test-implementation.mdに軽微な改善提案がある
- **入力**: なし
- **期待結果**:
  - 戻り値: `{'result': 'PASS_WITH_SUGGESTIONS', 'feedback': '<フィードバック>', 'suggestions': ['<提案1>', '<提案2>']}`
  - result.mdが生成される
- **テストデータ**: モックtest-implementation.md（軽微な問題あり）

---

#### テストケース: test_review_正常系_FAIL

- **目的**: テストコードレビューでFAILが返されることを検証
- **前提条件**:
  - execute()が正常に完了している
  - test-implementation.mdに致命的な問題がある（例: 実コードが変更されている）
- **入力**: なし
- **期待結果**:
  - 戻り値: `{'result': 'FAIL', 'feedback': '<フィードバック>', 'suggestions': ['<修正提案1>', '<修正提案2>']}`
  - result.mdが生成される
  - metadata.jsonのstatusが'failed'に更新される
- **テストデータ**: モックtest-implementation.md（実コード変更を含む）

---

#### テストケース: test_review_出力ファイル不在エラー

- **目的**: test-implementation.mdが存在しない場合にエラーが返されることを検証
- **前提条件**:
  - test-implementation.mdが存在しない
- **入力**: なし
- **期待結果**:
  - 戻り値: `{'result': 'FAIL', 'feedback': 'test-implementation.mdが存在しません。', 'suggestions': ['execute()を実行してtest-implementation.mdを生成してください。']}`
- **テストデータ**: なし

---

### 2.4 TestImplementationPhase.revise()

#### テストケース: test_revise_正常系

- **目的**: レビューフィードバックに基づいてテストコードが修正されることを検証
- **前提条件**:
  - review()が実行され、FAILが返されている
  - review_feedbackが提供されている
- **入力**:
  - `review_feedback="実コードの変更を削除してください。テストコードのみを実装してください。"`
- **期待結果**:
  - 戻り値: `{'success': True, 'output': '<test-implementation.mdのパス>', 'error': None}`
  - test-implementation.mdが更新される
  - `.ai-workflow/issue-324/05_test_implementation/revise/`配下にログが保存される
- **テストデータ**: モックreview_feedback

---

#### テストケース: test_revise_出力ファイル不在エラー

- **目的**: 元のtest-implementation.mdが存在しない場合にエラーが返されることを検証
- **前提条件**:
  - test-implementation.mdが存在しない
- **入力**:
  - `review_feedback="修正してください"`
- **期待結果**:
  - 戻り値: `{'success': False, 'output': None, 'error': 'test-implementation.mdが存在しません。'}`
- **テストデータ**: なし

---

#### テストケース: test_revise_修正後ファイル生成失敗エラー

- **目的**: Claude Agent SDK実行後に修正されたファイルが生成されない場合のエラー処理を検証
- **前提条件**:
  - 元のtest-implementation.mdは存在する
  - Claude Agent SDKが実行されるが、修正後のファイルが生成されない
- **入力**:
  - `review_feedback="修正してください"`
- **期待結果**:
  - 戻り値: `{'success': False, 'output': None, 'error': '修正されたtest-implementation.mdが生成されませんでした。'}`
- **テストデータ**: モックClaudeAgentClient（出力ファイル生成なし）

---

### 2.5 main.pyの修正

#### テストケース: test_main_phase_classes_にtest_implementationが追加されている

- **目的**: main.pyのphase_classes辞書にTestImplementationPhaseが追加されることを検証
- **前提条件**:
  - main.pyが修正されている
- **入力**: なし（コードレビュー）
- **期待結果**:
  - `phase_classes`辞書に`'test_implementation': TestImplementationPhase`が含まれる
  - 順序が正しい（implementation → test_implementation → testing）
- **テストデータ**: なし（静的検証）

---

#### テストケース: test_main_CLI選択肢にtest_implementationが追加されている

- **目的**: CLIでtest_implementationが選択可能であることを検証
- **前提条件**:
  - main.pyが修正されている
- **入力**: なし
- **期待結果**:
  - `@click.option('--phase')`の選択肢に`'test_implementation'`が含まれる
  - 順序が正しい（implementation → test_implementation → testing）
- **テストデータ**: なし（静的検証）

---

#### テストケース: test_main_TestImplementationPhaseがインポートされている

- **目的**: TestImplementationPhaseが正しくインポートされることを検証
- **前提条件**:
  - main.pyが修正されている
- **入力**: なし
- **期待結果**:
  - `from phases.test_implementation import TestImplementationPhase`が含まれる
  - インポートエラーが発生しない
- **テストデータ**: なし（静的検証）

---

### 2.6 phases/__init__.pyの修正

#### テストケース: test_phases_init_TestImplementationPhaseがエクスポートされている

- **目的**: phases/__init__.pyでTestImplementationPhaseがエクスポートされることを検証
- **前提条件**:
  - phases/__init__.pyが修正されている
- **入力**: なし
- **期待結果**:
  - `from .test_implementation import TestImplementationPhase`が含まれる
  - `__all__`に`'TestImplementationPhase'`が含まれる
- **テストデータ**: なし（静的検証）

---

### 2.7 report.pyの修正

#### テストケース: test_report_Phase番号が7から8に更新されている

- **目的**: report.pyのPhase番号が正しく更新されることを検証
- **前提条件**:
  - report.pyが修正されている
- **入力**: なし
- **期待結果**:
  - コメント内の「Phase 7」が「Phase 8」に更新されている
  - ログ出力の「Phase 7」が「Phase 8」に更新されている
  - ロジックに変更がない
- **テストデータ**: なし（静的検証）

---

## 3. Integrationテストシナリオ

### 3.1 Phase 4→5→6の連携テスト

#### シナリオ名: 8フェーズワークフロー_Phase4から6までの連携

- **目的**: Phase 4（implementation）→ Phase 5（test_implementation）→ Phase 6（testing）の連携が正常に動作することを検証
- **前提条件**:
  - Phase 0〜3が正常に完了している
  - metadata.jsonが正しく初期化されている
  - Git repositoryが初期化されている
- **テスト手順**:
  1. Phase 4（implementation）を実行
     - `python scripts/ai-workflow/main.py --issue-number 324 --phase implementation`
  2. Phase 4完了を確認
     - metadata.jsonのimplementationステータスが'completed'であることを確認
  3. Phase 5（test_implementation）を実行
     - `python scripts/ai-workflow/main.py --issue-number 324 --phase test_implementation`
  4. Phase 5完了を確認
     - metadata.jsonのtest_implementationステータスが'completed'であることを確認
  5. Phase 6（testing）を実行
     - `python scripts/ai-workflow/main.py --issue-number 324 --phase testing`
  6. Phase 6完了を確認
     - metadata.jsonのtestingステータスが'completed'であることを確認
- **期待結果**:
  - 全フェーズが正常に完了する（statusが'completed'）
  - Phase 4で実コードが実装される（テストコードは含まれない）
  - Phase 5でテストコードが実装される（実コードは変更されない）
  - Phase 6でテストが実行される（Phase 5のテストコードを使用）
  - 各フェーズの成果物が適切なディレクトリに保存される
- **確認項目**:
  - [ ] Phase 4の成果物に`test_*.py`ファイルが含まれていない
  - [ ] Phase 5の成果物に`test_*.py`ファイルが含まれている
  - [ ] Phase 5で実コード（`test_*.py`以外）が変更されていない
  - [ ] metadata.jsonに全フェーズの実行履歴が記録されている
  - [ ] Git commitが3回行われている（各フェーズで1回ずつ）
  - [ ] Git commitメッセージが正しい（`[ai-workflow] Phase X (phase_name) - completed`）

---

### 3.2 8フェーズワークフロー全体テスト

#### シナリオ名: 8フェーズワークフロー_完全実行

- **目的**: Phase 0〜8の全フェーズが正常に実行されることを検証
- **前提条件**:
  - Issue #324が作成されている
  - Git repositoryが初期化されている
  - Claude API keyが設定されている
- **テスト手順**:
  1. Phase 0（planning）を実行
  2. Phase 1（requirements）を実行
  3. Phase 2（design）を実行
  4. Phase 3（test_scenario）を実行
  5. Phase 4（implementation）を実行
  6. Phase 5（test_implementation）を実行
  7. Phase 6（testing）を実行
  8. Phase 7（documentation）を実行
  9. Phase 8（report）を実行
- **期待結果**:
  - 全フェーズが正常に完了する（statusが'completed'）
  - 各フェーズの成果物が適切なディレクトリに保存される
  - metadata.jsonに全フェーズの実行履歴が記録される
  - Git commitが8回行われている
- **確認項目**:
  - [ ] `.ai-workflow/issue-324/`配下に00〜08のディレクトリが作成されている
  - [ ] 各ディレクトリに`output/`フォルダが存在し、成果物が保存されている
  - [ ] metadata.jsonの全フェーズのstatusが'completed'になっている
  - [ ] Git logに8つのcommitが記録されている
  - [ ] 各commitメッセージが正しいフォーマットである
  - [ ] Phase 5のディレクトリ名が`05_test_implementation`である
  - [ ] Phase 6〜8のディレクトリ名が正しく繰り下げられている（06_testing、07_documentation、08_report）

---

### 3.3 後方互換性テスト

#### シナリオ名: 7フェーズワークフロー_test_implementationスキップ

- **目的**: 既存の7フェーズワークフロー（test_implementationをスキップ）が引き続き動作することを検証
- **前提条件**:
  - 既存のIssue（例: #305、#310）が存在する
  - 既存のmetadata.json構造（7フェーズ）が使用されている
- **テスト手順**:
  1. Phase 0（planning）を実行
  2. Phase 1（requirements）を実行
  3. Phase 2（design）を実行
  4. Phase 3（test_scenario）を実行
  5. Phase 4（implementation）を実行
  6. Phase 5をスキップ（test_implementationを実行しない）
  7. Phase 6（testing）を実行（旧Phase 5）
  8. Phase 7（documentation）を実行（旧Phase 6）
  9. Phase 8（report）を実行（旧Phase 7）
- **期待結果**:
  - 全フェーズが正常に完了する（statusが'completed'）
  - test_implementationフェーズはスキップされる（実行されない）
  - 既存のmetadata.json構造で動作する
  - Phase 4でテストコードも実装される（従来の動作）
- **確認項目**:
  - [ ] Phase 0→1→2→3→4→6→7→8の順序で実行される
  - [ ] `.ai-workflow/issue-XXX/05_test_implementation/`ディレクトリが作成されない
  - [ ] Phase 4でテストコードが実装される
  - [ ] metadata.jsonにtest_implementationフェーズが含まれていても既存フェーズが動作する
  - [ ] Git commitが7回行われている（test_implementation分を除く）

---

### 3.4 metadata.json更新フローテスト

#### シナリオ名: metadata.json_test_implementation記録

- **目的**: metadata.jsonにtest_implementationフェーズが正しく記録されることを検証
- **前提条件**:
  - 新規ワークフローが開始される
  - WorkflowState.create_new()が実行される
- **テスト手順**:
  1. 新規Issueでワークフローを初期化
  2. metadata.jsonを確認
  3. Phase 5（test_implementation）を実行
  4. metadata.jsonを再確認
- **期待結果**:
  - 初期化時: metadata.jsonにtest_implementationフェーズが含まれる
    ```json
    {
      "phases": {
        "test_implementation": {
          "status": "pending",
          "retry_count": 0,
          "started_at": null,
          "completed_at": null,
          "review_result": null
        }
      }
    }
    ```
  - 実行後: metadata.jsonのtest_implementationが更新される
    ```json
    {
      "phases": {
        "test_implementation": {
          "status": "completed",
          "retry_count": 0,
          "started_at": "2025-10-11T10:00:00",
          "completed_at": "2025-10-11T10:30:00",
          "review_result": "PASS"
        }
      }
    }
    ```
- **確認項目**:
  - [ ] metadata.jsonにtest_implementationキーが存在する
  - [ ] statusが'pending'→'completed'に更新される
  - [ ] started_atとcompleted_atが記録される
  - [ ] review_resultが記録される
  - [ ] 既存のmetadata.json構造と互換性がある

---

### 3.5 Git auto-commit & push動作テスト

#### シナリオ名: Git_auto_commit_test_implementation

- **目的**: Phase 5完了時にGit auto-commitが正常に実行されることを検証
- **前提条件**:
  - Git repositoryが初期化されている
  - Git remoteが設定されている
  - Phase 5（test_implementation）が正常に完了している
- **テスト手順**:
  1. Phase 5を実行
  2. Git logを確認
  3. Git statusを確認
- **期待結果**:
  - テストコードがGitにコミットされる
  - commitメッセージに「[ai-workflow] Phase 5 (test_implementation) - completed」が含まれる
  - リモートリポジトリにpushされる（設定による）
  - metadata.jsonのgit_commitフィールドにcommit hashが記録される
- **確認項目**:
  - [ ] `git log --oneline --grep="Phase 5 (test_implementation)"`でcommitが見つかる
  - [ ] commitメッセージが正しいフォーマットである
  - [ ] テストコードファイル（`test_*.py`）がcommitに含まれている
  - [ ] metadata.jsonのgit_commitフィールドにcommit hashが記録されている
  - [ ] `git status`で未コミットファイルがない

---

### 3.6 Jenkinsパイプライン統合テスト

#### シナリオ名: Jenkins_test_implementation実行

- **目的**: JenkinsパイプラインでPhase 5が正常に実行されることを検証
- **前提条件**:
  - Jenkins DSLが設定されている
  - ai-workflow-orchestratorジョブが存在する
- **テスト手順**:
  1. Jenkins UIでai-workflow-orchestratorジョブを開く
  2. START_PHASEパラメータで'test_implementation'を選択
  3. ビルドを実行
  4. ビルドログを確認
- **期待結果**:
  - START_PHASEパラメータで'test_implementation'が選択可能
  - Jenkinsパイプラインが正常に実行される
  - ログがJenkins UIで確認可能
  - 実行結果がmetadata.jsonに記録される
  - ビルドが成功する（緑色）
- **確認項目**:
  - [ ] Jenkins UIのパラメータドロップダウンに'test_implementation'が表示される
  - [ ] ビルドが成功する（緑色のチェックマーク）
  - [ ] ビルドログに「Phase 5 (test_implementation)」が記録されている
  - [ ] metadata.jsonがJenkins workspace内で更新されている
  - [ ] Git commitがJenkins経由で実行されている

---

### 3.7 クリティカルシンキングレビュー機能テスト

#### シナリオ名: クリティカルシンキングレビュー_Phase5

- **目的**: Phase 5でクリティカルシンキングレビューが正常に機能することを検証
- **前提条件**:
  - Phase 5（test_implementation）が実行され、テストコードが生成されている
- **テスト手順**:
  1. review()メソッドを実行
  2. レビュー結果を確認
  3. ブロッカーがある場合、revise()メソッドを実行
- **期待結果**:
  - Phase 5に特化したレビュー基準が適用される
  - テストコードの品質がチェックされる（カバレッジ、エッジケース、命名規則）
  - 実コードが変更されていないかチェックされる
  - レビュー結果が`.ai-workflow/issue-XXX/05_test_implementation/review/result.md`に保存される
  - ブロッカーがある場合、Phase 5は'failed'ステータスになる
- **確認項目**:
  - [ ] review.mdにレビュー結果が記載されている
  - [ ] レビュー観点が明確である（テストコード品質、実コード変更なし等）
  - [ ] ブロッカーがある場合、metadata.jsonのstatusが'failed'になる
  - [ ] PASS_WITH_SUGGESTIONSの場合、suggestionsが記録される
  - [ ] FAILの場合、revise()メソッドが実行可能である

---

## 4. テストデータ

### 4.1 ユニットテスト用テストデータ

#### モックファイル: requirements.md
```markdown
# 要件定義書 - Issue #324
## 機能要件
FR-001: Phase 5の新設
...
```

#### モックファイル: design.md
```markdown
# 詳細設計書 - Issue #324
## TestImplementationPhaseクラス設計
...
```

#### モックファイル: test-scenario.md
```markdown
# テストシナリオ - Issue #324
## ユニットテスト
...
```

#### モックファイル: implementation.md
```markdown
# 実装ログ - Issue #324
## 実装内容
- TestImplementationPhaseクラスを作成
...
```

#### モックmetadata.json（テスト戦略定義済み）
```json
{
  "issue_number": "324",
  "design_decisions": {
    "implementation_strategy": "CREATE",
    "test_strategy": "UNIT_INTEGRATION",
    "test_code_strategy": "CREATE_TEST"
  },
  "phases": {
    "test_implementation": {
      "status": "pending",
      "retry_count": 0,
      "started_at": null,
      "completed_at": null,
      "review_result": null
    }
  }
}
```

#### モックmetadata.json（テスト戦略未定義）
```json
{
  "issue_number": "324",
  "design_decisions": {},
  "phases": {
    "test_implementation": {
      "status": "pending"
    }
  }
}
```

### 4.2 統合テスト用テストデータ

#### テスト用Issue番号
- Issue #324（新規Issue、8フェーズワークフロー）
- Issue #305（既存Issue、7フェーズワークフロー）

#### テスト用Git repository
- ローカルリポジトリ: `/tmp/test-ai-workflow/`
- リモートリポジトリ: モック（実際のpushは行わない）

---

## 5. テスト環境要件

### 5.1 必要なテスト環境

**ローカル開発環境**:
- Python 3.8以上
- pytest 6.0以上
- Git 2.x以上
- Claude API key（環境変数またはSSM）

**CI/CD環境**:
- Jenkins 2.426.1以上
- AWS SSM Parameter Storeへのアクセス
- Git repository（GitHub）

### 5.2 必要な外部サービス

**Claude API**:
- Claude Agent SDK（sonnet-4-5モデル）
- APIキー: AWS SSM Parameter Storeから取得

**GitHub API**:
- GitHubトークン（Issue投稿用）
- リポジトリ: tielec/infrastructure-as-code

**Git**:
- Git repository初期化済み
- Git remote設定済み（origin）

### 5.3 モック/スタブの必要性

**ユニットテストでモック対象**:
- `ClaudeAgentClient.execute_task_sync()`: Claude API呼び出し
- `GitHubClient.post_comment()`: GitHub Issue投稿
- `MetadataManager.update_phase_status()`: metadata.json更新
- `Path.exists()`: ファイル存在確認
- `Path.read_text()`: ファイル読み込み
- `Path.write_text()`: ファイル書き込み

**統合テストでモック対象**:
- Git push（リモートリポジトリへのpushはモック）
- GitHub Issue投稿（実際のIssueには投稿しない）

---

## 6. 品質ゲート確認

テストシナリオが以下の品質ゲートを満たしているか確認します：

- [x] **Phase 2の戦略に沿ったテストシナリオである**
  - UNIT_INTEGRATION戦略に基づき、ユニットテスト（2.1〜2.7）と統合テスト（3.1〜3.7）を作成

- [x] **主要な正常系がカバーされている**
  - execute()正常系（2.2）
  - review()正常系_PASS（2.3）
  - revise()正常系（2.4）
  - 8フェーズワークフロー完全実行（3.2）
  - Phase 4→5→6連携（3.1）

- [x] **主要な異常系がカバーされている**
  - 必須ファイル不在エラー（2.2）
  - テスト戦略未定義エラー（2.2）
  - 出力ファイル生成失敗エラー（2.2、2.4）
  - review()出力ファイル不在エラー（2.3）
  - review()FAIL（2.3）

- [x] **期待結果が明確である**
  - 全テストケースで期待結果を具体的に記載
  - 戻り値の形式を明記
  - 確認項目をチェックリスト形式で列挙

**結論**: 全ての品質ゲートを満たしています。

---

## 7. テスト実行計画

### 7.1 ユニットテスト実行

**実行コマンド**:
```bash
pytest tests/unit/phases/test_test_implementation.py -v
```

**実行順序**:
1. test_init_正常系
2. test_execute_正常系
3. test_execute_必須ファイル不在エラー
4. test_execute_テスト戦略未定義エラー
5. test_execute_出力ファイル生成失敗エラー
6. test_review_正常系_PASS
7. test_review_正常系_PASS_WITH_SUGGESTIONS
8. test_review_正常系_FAIL
9. test_review_出力ファイル不在エラー
10. test_revise_正常系
11. test_revise_出力ファイル不在エラー
12. test_revise_修正後ファイル生成失敗エラー

**期待結果**: 全テストがPASS

### 7.2 統合テスト実行

**実行方法**: 手動実行（開発初期段階）

**実行順序**:
1. Phase 4→5→6連携テスト
2. 8フェーズワークフロー完全実行テスト
3. 後方互換性テスト（7フェーズワークフロー）
4. metadata.json更新フローテスト
5. Git auto-commit & push動作テスト
6. Jenkinsパイプライン統合テスト（オプション）
7. クリティカルシンキングレビュー機能テスト

**期待結果**: 全テストが正常に完了

---

## 8. テストシナリオのメンテナンス

### 8.1 テストシナリオの更新タイミング

- 要件変更時: 要件定義書の変更に伴い、テストシナリオを更新
- 設計変更時: 設計書の変更に伴い、テストシナリオを更新
- バグ発見時: バグに対応するテストケースを追加
- リファクタリング時: テストシナリオの可読性向上

### 8.2 テストカバレッジ目標

- **ユニットテスト**: 80%以上のカバレッジ
- **統合テスト**: 主要なフローをカバー（100%）

---

## 9. 付録

### 9.1 用語集

| 用語 | 説明 |
|------|------|
| TestImplementationPhase | Phase 5のテストコード実装を担当するクラス |
| test-implementation.md | Phase 5の成果物（テストコード実装ログ） |
| metadata.json | ワークフローの状態管理ファイル |
| クリティカルシンキングレビュー | 各フェーズのreview()メソッドで実施される品質レビュー |
| ブロッカー | 次フェーズに進めない致命的な問題 |
| モック | テストで使用する偽のオブジェクト |

### 9.2 参考ドキュメント

- **Planning Document**: `.ai-workflow/issue-324/00_planning/output/planning.md`
- **Requirements Document**: `.ai-workflow/issue-324/01_requirements/output/requirements.md`
- **Design Document**: `.ai-workflow/issue-324/02_design/output/design.md`
- **CLAUDE.md**: プロジェクトの全体方針とコーディングガイドライン
- **README.md**: プロジェクト概要と使用方法

---

**作成日**: 2025-10-11
**Issue番号**: #324
**Phase**: Phase 3 (test_scenario)
**バージョン**: 1.3
**改訂履歴**:
- v1.0: 初版作成
- v1.1: レビュー実施（ブロッカーなし） - 品質ゲート全項目クリア確認済み
- v1.2: 修正フェーズ完了 - レビュー結果確認、全品質ゲートクリア、次フェーズ準備完了
- v1.3: 再レビュー対応完了 - レビューフィードバックが空のため変更なし、既存の高品質なテストシナリオを維持、全品質ゲート継続クリア
