# テストシナリオ: Planning PhaseのJenkins統合とプロンプト修正

**Issue番号**: #332
**タイトル**: [FEATURE] Planning PhaseのJenkins統合とプロンプト修正
**作成日**: 2025-10-10
**バージョン**: 1.0.0

---

## 1. テスト戦略サマリー

### 1.1 選択されたテスト戦略

**INTEGRATION_ONLY**

Phase 2の設計書で決定されたテスト戦略に基づき、統合テストのみを実施します。

### 1.2 テスト戦略の判断根拠（Phase 2から引用）

- **複数コンポーネント間の統合**: Jenkins → Python → Claude Agent SDK → Planning Document参照という複数コンポーネント間の連携
- **E2Eワークフローの検証**: Planning Phase → Requirements Phase → Design Phaseという一連のワークフローの動作確認が必要
- **ファイル生成とパス参照の検証**: Planning Documentが正しく生成され、後続Phaseで正しく参照されることの確認
- **Unitテストの必要性は低い**: `_get_planning_document_path()` は単純なファイルパス構築とチェックのみ（Unitテストで得られる価値は限定的）
- **BDDは不要**: ユーザーストーリーよりもシステム間の統合動作確認が主目的

### 1.3 テスト対象の範囲

本テストシナリオでは、以下の統合ポイントをカバーします：

1. **Jenkins統合**: Job DSL → Jenkinsfile → Planning Phase実行
2. **Phase間連携**: Planning Phase → Requirements Phase → Design Phase
3. **Planning Document参照**: BasePhaseヘルパーメソッド → 各Phase → Claude Agent SDK
4. **エラーハンドリング**: Planning Document不在時の各Phaseの動作
5. **E2Eワークフロー**: Planning Phase → Report Phase（全Phase）

### 1.4 テストの目的

- Jenkins環境からPlanning Phaseが正常に実行できることを確認
- 各PhaseがPlanning Documentを正しく参照できることを確認
- Planning Documentが存在しない場合でも後続Phaseが正常動作することを確認
- 全Phase（Phase 0-7）が連携して動作することを確認

---

## 2. 統合テストシナリオ

### 2.1 Jenkins統合テスト

#### テストシナリオ 1-1: Planning Phaseの単独実行

**シナリオ名**: Jenkins Job DSL → Jenkinsfile → Planning Phase実行

**目的**: JenkinsからPlanning Phaseを単独で実行できることを確認

**前提条件**:
- Jenkins dev環境が稼働している
- ai_workflow_orchestratorジョブがシードジョブで生成済み
- テスト用Issue（例: #332）が存在する
- GITHUB_TOKENが設定されている
- Claude Agent SDK（Docker環境）が利用可能

**テスト手順**:
1. Jenkinsのai_workflow_orchestratorジョブを開く
2. パラメータを設定:
   - `START_PHASE`: `planning`
   - `ISSUE_URL`: `https://github.com/tielec/infrastructure-as-code/issues/332`
   - `DRY_RUN`: `false`
3. "ビルド実行"をクリック
4. ビルドログを確認
5. Planning Phaseステージが実行されることを確認
6. ファイルシステムで `.ai-workflow/issue-332/00_planning/output/planning.md` の存在を確認
7. `metadata.json` の内容を確認

**期待結果**:
- Planning Phaseステージが成功ステータスで完了する
- ビルドログに `[INFO] Phase: planning` が出力される
- ビルドログに `python main.py execute --phase planning --issue 332` の実行ログが出力される
- `.ai-workflow/issue-332/00_planning/output/planning.md` が生成される
- planning.mdに以下のセクションが含まれる:
  - Issue複雑度分析
  - 実装タスクの洗い出しと分割
  - タスク間依存関係
  - 実装戦略・テスト戦略の判断
  - リスク評価とリスク軽減策
- `metadata.json` に Planning Phase のステータスが記録される:
  ```json
  {
    "design_decisions": {
      "implementation_strategy": "EXTEND",
      "test_strategy": "INTEGRATION_ONLY",
      "test_code_strategy": "CREATE_TEST"
    }
  }
  ```

**確認項目**:
- [ ] START_PHASEパラメータで `planning` が選択可能
- [ ] Planning Phaseステージが実行される
- [ ] planning.mdが生成される
- [ ] planning.mdの内容が要件を満たしている
- [ ] metadata.jsonに戦略判断が保存される
- [ ] GitHub Issueにコメントが投稿される（成果物リンク）

---

#### テストシナリオ 1-2: START_PHASEパラメータの確認

**シナリオ名**: Job DSLパラメータ設定の検証

**目的**: START_PHASEパラメータに `planning` が追加され、デフォルト値になっていることを確認

**前提条件**:
- Jenkins dev環境が稼働している
- シードジョブが実行され、Job DSLが最新化されている

**テスト手順**:
1. Jenkinsのai_workflow_orchestratorジョブを開く
2. "Build with Parameters"ボタンをクリック
3. START_PHASEドロップダウンを確認

**期待結果**:
- START_PHASEドロップダウンに以下の選択肢が表示される:
  - `planning` (デフォルト)
  - `requirements`
  - `design`
  - `test_scenario`
  - `implementation`
  - `testing`
  - `documentation`
  - `report`
- デフォルト値が `planning` である

**確認項目**:
- [ ] `planning` が選択肢に含まれる
- [ ] `planning` がリストの先頭に配置される
- [ ] デフォルト値が `planning` である

---

### 2.2 Phase間連携テスト

#### テストシナリオ 2-1: Planning Phase → Requirements Phase連携

**シナリオ名**: Planning Documentの参照（Requirements Phase）

**目的**: Requirements PhaseがPlanning Documentを正しく参照できることを確認

**前提条件**:
- Planning Phaseが完了し、`.ai-workflow/issue-332/00_planning/output/planning.md` が存在する
- Jenkins dev環境が稼働している

**テスト手順**:
1. Jenkinsのai_workflow_orchestratorジョブを実行:
   - `START_PHASE`: `planning`
   - `ISSUE_URL`: `https://github.com/tielec/infrastructure-as-code/issues/332`
2. Planning Phaseステージの完了を待つ
3. Requirements Phaseステージが自動実行されることを確認
4. Requirements Phaseのビルドログを確認
5. Requirements Phaseの成果物 `requirements.md` を確認

**期待結果**:
- Requirements Phaseのビルドログに以下のログが出力される:
  ```
  [INFO] Planning Document参照: @.ai-workflow/issue-332/00_planning/output/planning.md
  ```
- Requirements Phaseが正常に完了する
- `requirements.md` が生成される
- `requirements.md` にPlanning Documentの内容が反映されている:
  - 実装戦略（EXTEND）が考慮されている
  - テスト戦略（INTEGRATION_ONLY）が反映されている
  - Planning Documentで特定されたリスクが考慮されている

**確認項目**:
- [ ] Requirements PhaseでPlanning Documentのパスが正しく取得される
- [ ] ビルドログに `[INFO] Planning Document参照` が出力される
- [ ] requirements.mdが生成される
- [ ] requirements.mdにPlanning Documentの戦略が反映される
- [ ] エラーが発生しない

---

#### テストシナリオ 2-2: Planning Phase → Design Phase連携

**シナリオ名**: Planning Documentの参照（Design Phase）

**目的**: Design PhaseがPlanning Documentを正しく参照できることを確認

**前提条件**:
- Planning Phaseが完了し、planning.mdが存在する
- Requirements Phaseが完了し、requirements.mdが存在する

**テスト手順**:
1. Jenkinsのai_workflow_orchestratorジョブを実行:
   - `START_PHASE`: `planning`
   - `ISSUE_URL`: `https://github.com/tielec/infrastructure-as-code/issues/332`
2. Planning Phase → Requirements Phase → Design Phaseの順に実行される
3. Design Phaseのビルドログを確認
4. Design Phaseの成果物 `design.md` を確認

**期待結果**:
- Design Phaseのビルドログに以下のログが出力される:
  ```
  [INFO] Planning Document参照: @.ai-workflow/issue-332/00_planning/output/planning.md
  ```
- Design Phaseが正常に完了する
- `design.md` が生成される
- `design.md` にPlanning Documentの内容が反映されている:
  - 実装戦略（EXTEND）に基づいた設計
  - テスト戦略（INTEGRATION_ONLY）に基づいたテスト計画
  - Planning Documentのリスク軽減策が設計に組み込まれている

**確認項目**:
- [ ] Design PhaseでPlanning Documentのパスが正しく取得される
- [ ] ビルドログに `[INFO] Planning Document参照` が出力される
- [ ] design.mdが生成される
- [ ] design.mdにPlanning Documentの戦略が反映される
- [ ] requirements.mdとの整合性が保たれる

---

#### テストシナリオ 2-3: 全Phase（Phase 0-7）のE2E連携

**シナリオ名**: Planning Phase → Report Phase（全Phase統合）

**目的**: 全Phase（Phase 0-7）が連携して動作することを確認

**前提条件**:
- Jenkins dev環境が稼働している
- テスト用Issue（例: #332）が存在する

**テスト手順**:
1. Jenkinsのai_workflow_orchestratorジョブを実行:
   - `START_PHASE`: `planning`
   - `ISSUE_URL`: `https://github.com/tielec/infrastructure-as-code/issues/332`
   - `DRY_RUN`: `false`
2. 全Phaseが順次実行されることを確認:
   - Phase 0: Planning
   - Phase 1: Requirements
   - Phase 2: Design
   - Phase 3: Test Scenario
   - Phase 4: Implementation
   - Phase 5: Testing
   - Phase 6: Documentation
   - Phase 7: Report
3. 各Phaseのビルドログを確認
4. 各Phaseの成果物を確認

**期待結果**:
- 全8つのPhaseステージが成功ステータスで完了する
- 各Phase（Phase 1-7）のビルドログに Planning Document参照ログが出力される:
  ```
  [INFO] Planning Document参照: @.ai-workflow/issue-332/00_planning/output/planning.md
  ```
- 以下の成果物が生成される:
  - `.ai-workflow/issue-332/00_planning/output/planning.md`
  - `.ai-workflow/issue-332/01_requirements/output/requirements.md`
  - `.ai-workflow/issue-332/02_design/output/design.md`
  - `.ai-workflow/issue-332/03_test_scenario/output/test-scenario.md`
  - `.ai-workflow/issue-332/04_implementation/output/` （実装ファイル）
  - `.ai-workflow/issue-332/05_testing/output/test-results.md`
  - `.ai-workflow/issue-332/06_documentation/output/documentation.md`
  - `.ai-workflow/issue-332/07_report/output/report.md`
- 各成果物にPlanning Documentの内容が反映されている
- metadata.jsonに全Phaseのステータスが記録される
- GitHub Issueに各Phaseの成果物コメントが投稿される

**確認項目**:
- [ ] 全8Phaseが成功する
- [ ] 各PhaseでPlanning Documentが参照される
- [ ] 全成果物が生成される
- [ ] 成果物間の整合性が保たれる
- [ ] metadata.jsonが正しく更新される
- [ ] GitHub Issueコメントが投稿される

---

### 2.3 Planning Document参照機能の統合テスト

#### テストシナリオ 3-1: BasePhaseヘルパーメソッドの統合

**シナリオ名**: `_get_planning_document_path()` メソッドの動作確認

**目的**: BasePhaseヘルパーメソッドが正しく動作し、各Phaseで利用できることを確認

**前提条件**:
- Planning Phaseが完了し、planning.mdが存在する

**テスト手順**:
1. Jenkinsのai_workflow_orchestratorジョブを実行:
   - `START_PHASE`: `requirements`
   - `ISSUE_URL`: `https://github.com/tielec/infrastructure-as-code/issues/332`
2. Requirements Phaseのビルドログを確認
3. `_get_planning_document_path()` の実行結果を確認

**期待結果**:
- ビルドログに以下のログが出力される:
  ```
  [INFO] Planning Document参照: @.ai-workflow/issue-332/00_planning/output/planning.md
  ```
- `_get_planning_document_path(332)` が正しいパスを返す
- パスが `@{relative_path}` 形式である
- Requirements Phaseが正常に完了する

**確認項目**:
- [ ] ヘルパーメソッドが正しく呼び出される
- [ ] 相対パスが正しく取得される
- [ ] `@` 記法が正しく適用される
- [ ] エラーが発生しない

---

#### テストシナリオ 3-2: Claude Agent SDKとの統合

**シナリオ名**: `@{path}` 記法によるファイル参照

**目的**: Claude Agent SDKが `@{path}` 記法でPlanning Documentを正しく読み込むことを確認

**前提条件**:
- Planning Phaseが完了し、planning.mdが存在する
- Claude Agent SDK（Docker環境）が利用可能

**テスト手順**:
1. Jenkinsのai_workflow_orchestratorジョブを実行:
   - `START_PHASE`: `requirements`
   - `ISSUE_URL`: `https://github.com/tielec/infrastructure-as-code/issues/332`
2. Requirements Phaseの実行中、Claude Agent SDKのログを確認
3. Requirements Phaseの成果物を確認

**期待結果**:
- Claude Agent SDKがPlanning Documentを正しく読み込む
- プロンプトにPlanning Documentの内容が含まれる
- Requirements Phaseの成果物にPlanning Documentの内容が反映される
- エラーが発生しない

**確認項目**:
- [ ] `@` 記法が正しく機能する
- [ ] Planning Documentが読み込まれる
- [ ] プロンプトに内容が含まれる
- [ ] 成果物に反映される

---

### 2.4 エラーハンドリング統合テスト

#### テストシナリオ 4-1: Planning Document不在時の動作

**シナリオ名**: Planning Documentが存在しない場合の各Phaseの挙動

**目的**: Planning Documentが存在しない場合でも、各Phaseが正常に実行されることを確認

**前提条件**:
- Planning Phaseが実行されていない（planning.mdが存在しない）
- テスト用Issue（例: #333）が存在する

**テスト手順**:
1. Jenkinsのai_workflow_orchestratorジョブを実行:
   - `START_PHASE`: `requirements` （Planning Phaseをスキップ）
   - `ISSUE_URL`: `https://github.com/tielec/infrastructure-as-code/issues/333`
2. Requirements Phaseのビルドログを確認
3. Requirements Phaseの成果物を確認

**期待結果**:
- Requirements Phaseのビルドログに警告ログが出力される:
  ```
  [WARNING] Planning Phase成果物が見つかりません: .ai-workflow/issue-333/00_planning/output/planning.md
  ```
- プロンプトに以下のメッセージが埋め込まれる:
  ```
  Planning Document: Planning Phaseは実行されていません
  ```
- Requirements Phaseが正常に完了する（エラー終了しない）
- `requirements.md` が生成される
- requirements.mdは、Planning Documentなしで要件定義が行われる

**確認項目**:
- [ ] 警告ログが出力される
- [ ] エラー終了しない
- [ ] プロンプトに警告メッセージが埋め込まれる
- [ ] requirements.mdが生成される
- [ ] 後続Phaseも正常実行できる

---

#### テストシナリオ 4-2: Planning Document不在時の全Phase実行

**シナリオ名**: Planning PhaseをスキップしたE2Eワークフロー

**目的**: Planning PhaseをスキップしてもE2Eワークフローが正常動作することを確認

**前提条件**:
- テスト用Issue（例: #334）が存在する

**テスト手順**:
1. Jenkinsのai_workflow_orchestratorジョブを実行:
   - `START_PHASE`: `requirements` （Planning Phaseをスキップ）
   - `ISSUE_URL`: `https://github.com/tielec/infrastructure-as-code/issues/334`
2. 全Phaseが順次実行されることを確認
3. 各Phaseのビルドログを確認
4. 各Phaseの成果物を確認

**期待結果**:
- 全Phase（Phase 1-7）が成功ステータスで完了する
- 各Phaseのビルドログに警告ログが出力される:
  ```
  [WARNING] Planning Phase成果物が見つかりません
  ```
- 全Phaseの成果物が生成される
- 成果物はPlanning Documentなしで作成される
- エラーが発生しない

**確認項目**:
- [ ] 全Phase（Phase 1-7）が成功する
- [ ] 各Phaseで警告ログが出力される
- [ ] 全成果物が生成される
- [ ] エラー終了しない
- [ ] 後方互換性が保たれる

---

#### テストシナリオ 4-3: 相対パス取得エラーのハンドリング

**シナリオ名**: 相対パスが取得できない場合の挙動

**目的**: working_dirからの相対パスが取得できない場合でも、エラー終了しないことを確認

**前提条件**:
- 異常な環境条件（異なるドライブ、シンボリックリンクなど）

**テスト手順**:
1. 異常な環境条件を設定（テスト環境依存）
2. Jenkinsのai_workflow_orchestratorジョブを実行
3. Requirements Phaseのビルドログを確認

**期待結果**:
- Requirements Phaseのビルドログに警告ログが出力される:
  ```
  [WARNING] Planning Documentの相対パスが取得できません
  ```
- プロンプトに以下のメッセージが埋め込まれる:
  ```
  Planning Document: Planning Phaseは実行されていません
  ```
- Requirements Phaseが正常に完了する（エラー終了しない）

**確認項目**:
- [ ] 警告ログが出力される
- [ ] エラー終了しない
- [ ] プロンプトに警告メッセージが埋め込まれる
- [ ] Phaseは正常完了する

---

### 2.5 プロンプトとクラスの統合テスト

#### テストシナリオ 5-1: プロンプトテンプレートのプレースホルダー置換

**シナリオ名**: `{planning_document_path}` プレースホルダーの置換

**目的**: 各Phaseのプロンプトテンプレートで `{planning_document_path}` プレースホルダーが正しく置換されることを確認

**前提条件**:
- Planning Phaseが完了し、planning.mdが存在する

**テスト手順**:
1. Jenkinsのai_workflow_orchestratorジョブを実行:
   - `START_PHASE`: `requirements`
   - `ISSUE_URL`: `https://github.com/tielec/infrastructure-as-code/issues/332`
2. Requirements Phaseのビルドログを確認
3. Claude Agent SDKに渡されるプロンプトを確認（ログから）

**期待結果**:
- プロンプトテンプレートの `{planning_document_path}` が以下に置換される:
  ```
  @.ai-workflow/issue-332/00_planning/output/planning.md
  ```
- 置換後のプロンプトにPlanning Documentのパスが含まれる
- 他のプレースホルダー（`{issue_info}`, `{issue_number}` など）も正しく置換される
- Requirements Phaseが正常に完了する

**確認項目**:
- [ ] `{planning_document_path}` が置換される
- [ ] 置換後のパスが正しい
- [ ] 他のプレースホルダーも置換される
- [ ] プロンプトが正しく生成される

---

#### テストシナリオ 5-2: 全Phaseのプロンプト統一フォーマット確認

**シナリオ名**: 全Phaseのプロンプトで統一されたPlanning Document参照フォーマット

**目的**: 全Phase（Phase 1-7）のプロンプトで、Planning Document参照セクションが統一されていることを確認

**前提条件**:
- Planning Phaseが完了し、planning.mdが存在する

**テスト手順**:
1. Jenkinsのai_workflow_orchestratorジョブを実行:
   - `START_PHASE`: `planning`
   - `ISSUE_URL`: `https://github.com/tielec/infrastructure-as-code/issues/332`
2. 全Phaseが順次実行されることを確認
3. 各Phaseのビルドログを確認し、プロンプトフォーマットを比較

**期待結果**:
- 全Phase（Phase 1-7）のプロンプトに以下のセクションが含まれる:
  ```markdown
  ## 入力情報

  ### Planning Phase成果物
  - Planning Document: @.ai-workflow/issue-332/00_planning/output/planning.md

  **注意**: Planning Phaseが実行されている場合、開発計画（実装戦略、テスト戦略、リスク、スケジュール）を必ず確認してください。
  ```
- フォーマットが全Phaseで統一されている
- 全Phaseが正常に完了する

**確認項目**:
- [ ] 全Phaseで同じフォーマットが使用される
- [ ] Planning Document参照セクションが含まれる
- [ ] 注意書きが含まれる
- [ ] フォーマットに一貫性がある

---

#### テストシナリオ 5-3: revise()メソッドでのPlanning Document参照

**シナリオ名**: revise()メソッドでのPlanning Document参照ロジック

**目的**: revise()メソッドでもPlanning Documentが正しく参照されることを確認

**前提条件**:
- Planning Phaseが完了し、planning.mdが存在する
- Requirements Phaseが完了し、requirements.mdが存在する
- Requirements Phaseのreview処理が失敗し、reviseが必要な状態（シミュレート）

**テスト手順**:
1. Requirements Phaseのrevise()メソッドが呼び出される状況を作る（テスト環境依存）
2. revise()メソッドのビルドログを確認
3. revise()で生成されたプロンプトを確認

**期待結果**:
- revise()メソッドのビルドログに Planning Document参照ログが出力される:
  ```
  [INFO] Planning Document参照: @.ai-workflow/issue-332/00_planning/output/planning.md
  ```
- revise()で生成されるプロンプトに Planning Documentのパスが含まれる
- revise()が正常に完了する
- 修正された requirements.mdが生成される

**確認項目**:
- [ ] revise()でもPlanning Documentが参照される
- [ ] ビルドログに参照ログが出力される
- [ ] プロンプトにパスが含まれる
- [ ] revise()が正常完了する

---

### 2.6 Jenkinsパイプライン統合テスト

#### テストシナリオ 6-1: Jenkinsfileのステージ順序確認

**シナリオ名**: Planning Phaseステージの配置確認

**目的**: Planning PhaseステージがRequirements Phaseステージの前に配置されていることを確認

**前提条件**:
- Jenkins dev環境が稼働している
- Jenkinsfileが最新化されている

**テスト手順**:
1. Jenkinsのai_workflow_orchestratorジョブを実行:
   - `START_PHASE`: `planning`
   - `ISSUE_URL`: `https://github.com/tielec/infrastructure-as-code/issues/332`
2. ビルドログでステージの実行順序を確認

**期待結果**:
- ステージが以下の順序で実行される:
  1. Initialization
  2. Phase 0: Planning
  3. Phase 1: Requirements
  4. Phase 2: Design
  5. Phase 3: Test Scenario
  6. Phase 4: Implementation
  7. Phase 5: Testing
  8. Phase 6: Documentation
  9. Phase 7: Report
  10. Finalization
- 各ステージが順次実行される
- エラーが発生しない

**確認項目**:
- [ ] Planning Phaseステージが最初のPhaseである
- [ ] ステージ順序が正しい
- [ ] 各ステージが順次実行される
- [ ] エラーが発生しない

---

#### テストシナリオ 6-2: START_PHASEパラメータによるステージスキップ

**シナリオ名**: START_PHASE=requirementsでPlanning Phaseをスキップ

**目的**: START_PHASEパラメータでPlanning Phaseをスキップできることを確認

**前提条件**:
- Jenkins dev環境が稼働している

**テスト手順**:
1. Jenkinsのai_workflow_orchestratorジョブを実行:
   - `START_PHASE`: `requirements`
   - `ISSUE_URL`: `https://github.com/tielec/infrastructure-as-code/issues/332`
2. ビルドログでステージの実行状況を確認

**期待結果**:
- Planning Phaseステージがスキップされる（実行されない）
- Requirements Phaseステージから実行が開始される
- ビルドログに Planning Phaseステージのスキップログが出力される
- Requirements Phase以降は正常に実行される

**確認項目**:
- [ ] Planning Phaseがスキップされる
- [ ] Requirements Phaseから開始される
- [ ] スキップログが出力される
- [ ] 後続Phaseが正常実行される

---

#### テストシナリオ 6-3: DRY_RUNモードの動作確認

**シナリオ名**: DRY_RUNモードでPlanning Phaseをスキップ

**目的**: DRY_RUNモードでPlanning Phaseがスキップされることを確認

**前提条件**:
- Jenkins dev環境が稼働している

**テスト手順**:
1. Jenkinsのai_workflow_orchestratorジョブを実行:
   - `START_PHASE`: `planning`
   - `ISSUE_URL`: `https://github.com/tielec/infrastructure-as-code/issues/332`
   - `DRY_RUN`: `true`
2. ビルドログを確認

**期待結果**:
- Planning Phaseステージが実行されるが、実際の処理はスキップされる
- ビルドログに `[DRY RUN] Phase 0実行をスキップ` が出力される
- planning.mdは生成されない
- ジョブは成功ステータスで完了する

**確認項目**:
- [ ] DRY RUNログが出力される
- [ ] 実際の処理がスキップされる
- [ ] planning.mdが生成されない
- [ ] ジョブが成功する

---

## 3. テストデータ

### 3.1 テスト用Issue

**Issue #332**:
- **タイトル**: [FEATURE] Planning PhaseのJenkins統合とプロンプト修正
- **URL**: https://github.com/tielec/infrastructure-as-code/issues/332
- **状態**: open
- **用途**: 本Issue自体をテスト対象として使用

**Issue #333（予備）**:
- **タイトル**: [TEST] Planning Document不在時のテスト
- **URL**: https://github.com/tielec/infrastructure-as-code/issues/333
- **状態**: open
- **用途**: Planning Phaseをスキップしたテスト用

**Issue #334（予備）**:
- **タイトル**: [TEST] E2Eワークフローテスト（Planning Phaseなし）
- **URL**: https://github.com/tielec/infrastructure-as-code/issues/334
- **状態**: open
- **用途**: Planning PhaseをスキップしたE2Eテスト用

### 3.2 テスト用データファイル

**Planning Document（正常データ）**:
- パス: `.ai-workflow/issue-332/00_planning/output/planning.md`
- 内容: Planning Phaseで生成される標準的な開発計画書
- サイズ: 約10-20KB（Markdownテキスト）

**Planning Document（不在データ）**:
- パス: `.ai-workflow/issue-333/00_planning/output/planning.md`
- 状態: ファイルが存在しない
- 用途: エラーハンドリングテスト

### 3.3 Jenkinsパラメータ組み合わせ

| テストケース | START_PHASE | ISSUE_URL | DRY_RUN | 期待動作 |
|------------|------------|-----------|---------|---------|
| 正常系1 | planning | Issue #332 | false | Planning Phase実行 |
| 正常系2 | requirements | Issue #332 | false | Planning Phaseスキップ |
| 正常系3 | planning | Issue #333 | false | Planning Phase実行（新Issue） |
| DRY_RUN1 | planning | Issue #332 | true | 実行スキップ |
| DRY_RUN2 | requirements | Issue #332 | true | Planning Phaseスキップ |

---

## 4. テスト環境要件

### 4.1 必要なテスト環境

**Jenkins環境**:
- **環境**: Jenkins dev環境
- **バージョン**: Jenkins 2.x以上
- **プラグイン**:
  - Job DSL Plugin
  - Pipeline Plugin
  - Git Plugin
  - GitHub Plugin

**Claude Agent SDK環境**:
- **環境**: Docker環境
- **イメージ**: Claude Agent SDK（最新版）
- **マウント**: ワークスペースディレクトリ

**Git環境**:
- **ブランチ**: `ai-workflow/issue-332`
- **リポジトリ**: infrastructure-as-code

### 4.2 必要な外部サービス

**GitHub API**:
- **認証**: GITHUB_TOKEN環境変数
- **権限**: Issue読み取り・コメント投稿
- **エンドポイント**: https://api.github.com

**Claude API**:
- **モデル**: Claude Sonnet 4.5
- **認証**: APIキー（環境変数）
- **用途**: Planning Phaseとその他Phase実行

### 4.3 必要なファイルシステム構造

```
/tmp/jenkins-a2d2d2b4/workspace/AI_Workflow/ai_workflow_orchestrator/
├── .ai-workflow/
│   └── issue-332/
│       ├── 00_planning/
│       │   └── output/
│       │       └── planning.md
│       ├── 01_requirements/
│       │   └── output/
│       │       └── requirements.md
│       ├── 02_design/
│       │   └── output/
│       │       └── design.md
│       ├── 03_test_scenario/
│       │   └── output/
│       │       └── test-scenario.md
│       ├── 04_implementation/
│       │   └── output/
│       ├── 05_testing/
│       │   └── output/
│       ├── 06_documentation/
│       │   └── output/
│       ├── 07_report/
│       │   └── output/
│       └── metadata.json
├── scripts/
│   └── ai-workflow/
│       ├── phases/
│       ├── prompts/
│       └── main.py
└── jenkins/
    └── jobs/
```

### 4.4 環境変数

| 変数名 | 用途 | 必須 |
|-------|------|------|
| GITHUB_TOKEN | GitHub API認証 | ✅ |
| WORKSPACE | Jenkinsワークスペースパス | ✅ |
| ISSUE_NUMBER | Issue番号（抽出） | ✅ |
| ISSUE_URL | Issue URL | ✅ |

### 4.5 モック/スタブの必要性

**不要**: 本テストは統合テストであり、実際のコンポーネント間の統合を検証するため、モック/スタブは使用しません。

---

## 5. 非機能要件テスト

### 5.1 パフォーマンステスト

#### テストシナリオ P-1: Planning Phase実行時間測定

**目的**: Planning Phaseの実行時間が5分以内であることを確認

**テスト手順**:
1. Jenkinsのai_workflow_orchestratorジョブを実行
2. Planning Phaseステージの実行時間を測定

**期待結果**:
- Planning Phase実行時間: 3-5分以内

#### テストシナリオ P-2: `_get_planning_document_path()` 実行時間測定

**目的**: ヘルパーメソッドの実行時間が100ms以内であることを確認

**テスト手順**:
1. Requirements Phaseを実行
2. `_get_planning_document_path()` の実行時間をログから測定

**期待結果**:
- 実行時間: 10ms以下（目標）、100ms以内（必須）

### 5.2 信頼性テスト

#### テストシナリオ R-1: Planning Document不在時の継続性

**目的**: Planning Documentが存在しない場合でも、各Phaseが正常に実行されることを確認

**テスト手順**:
- テストシナリオ 4-1、4-2を参照

**期待結果**:
- エラー終了しない
- 警告ログのみ出力
- 後続Phaseが正常実行される

### 5.3 保守性テスト

#### テストシナリオ M-1: 新Phase追加時の互換性

**目的**: 新しいPhaseを追加する際、BasePhaseのヘルパーメソッドを再利用できることを確認

**テスト手順**:
1. 新しいPhaseクラス（例: ReviewPhase）を仮想的に作成
2. BasePhaseを継承し、`_get_planning_document_path()` を呼び出す
3. 正常に動作することを確認

**期待結果**:
- ヘルパーメソッドが再利用可能
- 新Phaseでも同様に動作

---

## 6. テスト実行計画

### 6.1 テスト実行スケジュール

| フェーズ | テストシナリオ | 実行タイミング | 所要時間 |
|---------|-------------|------------|---------|
| **Phase 1** | Jenkins統合テスト（1-1, 1-2） | BasePhaseヘルパー実装後 | 30分 |
| **Phase 2** | Phase間連携テスト（2-1, 2-2） | Requirements Phase統合後 | 1時間 |
| **Phase 3** | Planning Document参照テスト（3-1, 3-2） | Design Phase統合後 | 30分 |
| **Phase 4** | エラーハンドリングテスト（4-1, 4-2, 4-3） | 全Phase統合後 | 1時間 |
| **Phase 5** | プロンプト統合テスト（5-1, 5-2, 5-3） | 全Phase統合後 | 1時間 |
| **Phase 6** | Jenkinsパイプラインテスト（6-1, 6-2, 6-3） | Jenkinsfile修正後 | 30分 |
| **Phase 7** | E2Eテスト（2-3） | 全実装完了後 | 2-3時間 |
| **Phase 8** | 非機能要件テスト（P-1, P-2, R-1, M-1） | E2Eテスト完了後 | 1時間 |

**合計見積もり**: 約7-8時間

### 6.2 テスト実行順序

1. **Jenkins統合テスト**（テストシナリオ 1-1, 1-2）
2. **BasePhaseヘルパーメソッドテスト**（テストシナリオ 3-1）
3. **Phase間連携テスト**（テストシナリオ 2-1, 2-2）
4. **Planning Document参照テスト**（テストシナリオ 3-2）
5. **エラーハンドリングテスト**（テストシナリオ 4-1, 4-2, 4-3）
6. **プロンプト統合テスト**（テストシナリオ 5-1, 5-2, 5-3）
7. **Jenkinsパイプラインテスト**（テストシナリオ 6-1, 6-2, 6-3）
8. **E2Eテスト**（テストシナリオ 2-3）
9. **非機能要件テスト**（テストシナリオ P-1, P-2, R-1, M-1）

### 6.3 テスト実行担当

- **実装者**: 統合テストの実行と結果確認
- **レビュアー**: テスト結果のレビューと品質ゲート確認

---

## 7. 品質ゲート確認

### 7.1 必須品質ゲート

本テストシナリオは、Phase 3の品質ゲートを満たしています：

- ✅ **Phase 2の戦略に沿ったテストシナリオである**: INTEGRATION_ONLYに準拠
- ✅ **主要な正常系がカバーされている**:
  - Jenkins統合（1-1）
  - Phase間連携（2-1, 2-2, 2-3）
  - Planning Document参照（3-1, 3-2）
- ✅ **主要な異常系がカバーされている**:
  - Planning Document不在（4-1, 4-2）
  - 相対パス取得エラー（4-3）
- ✅ **期待結果が明確である**: 全テストシナリオに具体的な期待結果を記載

### 7.2 テストシナリオカバレッジ

| 機能要件 | テストシナリオ | カバー状況 |
|---------|-------------|-----------|
| **FR-1**: JenkinsジョブへのPlanning Phase統合 | 1-1, 1-2, 6-1, 6-2, 6-3 | ✅ カバー済み |
| **FR-2**: BasePhaseヘルパーメソッドの追加 | 3-1, 4-1, 4-2, 4-3 | ✅ カバー済み |
| **FR-3**: 各Phaseプロンプトの修正 | 5-1, 5-2 | ✅ カバー済み |
| **FR-4**: 各PhaseクラスのPlanning Document参照ロジック追加 | 2-1, 2-2, 3-1, 3-2, 5-3 | ✅ カバー済み |
| **FR-5**: ドキュメント更新 | （手動確認） | 📝 手動確認 |

### 7.3 受け入れ基準カバレッジ

| 受け入れ基準 | テストシナリオ | カバー状況 |
|------------|-------------|-----------|
| **AC-1**: Jenkinsジョブの統合 | 1-1, 1-2 | ✅ カバー済み |
| **AC-2**: BasePhaseヘルパーメソッドの動作 | 3-1, 4-1 | ✅ カバー済み |
| **AC-3**: Phaseプロンプトの修正 | 5-1, 5-2 | ✅ カバー済み |
| **AC-4**: Phaseクラスのロジック追加 | 2-1, 2-2, 5-3 | ✅ カバー済み |
| **AC-5**: ドキュメントの更新 | （手動確認） | 📝 手動確認 |
| **AC-6**: E2Eテスト | 2-3 | ✅ カバー済み |

### 7.4 リスクカバレッジ

| リスク | テストシナリオ | 軽減状況 |
|-------|-------------|---------|
| **リスク1**: Planning Documentが存在しない場合のエラーハンドリング不足 | 4-1, 4-2, 4-3 | ✅ カバー済み |
| **リスク2**: プロンプト修正の漏れ（7ファイル） | 5-2 | ✅ カバー済み |
| **リスク3**: Jenkinsジョブの既存パイプライン破壊 | 6-1, 6-2, 6-3, 2-3 | ✅ カバー済み |
| **リスク4**: Claude Agent SDKの@記法の誤用 | 3-2 | ✅ カバー済み |

---

## 8. テスト結果記録フォーマット

### 8.1 テスト結果記録テンプレート

各テストシナリオの実行後、以下のフォーマットで結果を記録してください：

```markdown
### テストシナリオ {番号}: {シナリオ名}

**実行日時**: YYYY-MM-DD HH:MM:SS
**実行者**: {名前}
**実行環境**: Jenkins dev / Issue #{番号}

**結果**: ✅ 成功 / ❌ 失敗 / ⚠️ 警告

**確認項目**:
- [ ] 項目1: 結果
- [ ] 項目2: 結果
- [ ] 項目3: 結果

**実行ログ**:
```
（ログ抜粋）
```

**スクリーンショット**: （必要に応じて）

**備考**: （特記事項があれば記載）

**問題点**: （問題があれば記載）
```

### 8.2 テスト結果サマリー

全テスト完了後、以下のサマリーを作成してください：

```markdown
## テスト結果サマリー

**実行日**: YYYY-MM-DD
**実行者**: {名前}

**統計**:
- 総テストシナリオ数: X
- 成功: Y
- 失敗: Z
- 成功率: AA%

**品質ゲート**: ✅ 合格 / ❌ 不合格

**次ステップ**: （実装フェーズに進む / 修正が必要）
```

---

## 9. テスト自動化の可能性

### 9.1 自動化可能なテスト

以下のテストシナリオは、将来的にCI/CDパイプラインで自動化可能です：

- **テストシナリオ 1-1**: Planning Phaseの単独実行（Jenkins APIで自動実行）
- **テストシナリオ 1-2**: START_PHASEパラメータの確認（Job DSL検証スクリプト）
- **テストシナリオ 2-1, 2-2**: Phase間連携テスト（Jenkins APIで自動実行）
- **テストシナリオ 4-1**: Planning Document不在時の動作（自動テストスクリプト）
- **テストシナリオ P-1, P-2**: パフォーマンステスト（実行時間計測スクリプト）

### 9.2 自動化の優先度

1. **高優先度**: E2Eテスト（2-3）- 最も重要な統合テスト
2. **中優先度**: Phase間連携テスト（2-1, 2-2）- 頻繁に実行するテスト
3. **低優先度**: パラメータ確認（1-2）- 一度確認すれば十分

### 9.3 自動化の実装時期

- **Phase 5（実装フェーズ）完了後**: 手動統合テスト実施
- **Phase 5完了後（将来的な拡張）**: CI/CDパイプラインに自動テストを追加

---

## 10. トラブルシューティングガイド

### 10.1 よくある問題と解決策

| 問題 | 原因 | 解決策 |
|-----|------|-------|
| Planning Phaseステージが実行されない | START_PHASEが正しく設定されていない | START_PHASE=planningを確認 |
| Planning Documentが見つからない | Planning Phaseが実行されていない | Planning Phaseを先に実行 |
| 相対パスが取得できない | working_dirが正しくない | Jenkinsワークスペースパスを確認 |
| Claude Agent SDKエラー | Docker環境が起動していない | Docker環境を確認・再起動 |
| GitHub APIエラー | GITHUB_TOKENが無効 | トークンを確認・再生成 |

### 10.2 デバッグ手順

1. **Jenkinsビルドログを確認**: エラーメッセージを特定
2. **ファイルシステムを確認**: Planning Documentの存在確認
3. **環境変数を確認**: GITHUB_TOKEN、WORKSPACEなど
4. **metadata.jsonを確認**: Phase実行履歴を確認
5. **Claude Agent SDKログを確認**: プロンプト内容を確認

---

## 11. 参考情報

### 11.1 関連ドキュメント

- **要件定義書**: `.ai-workflow/issue-332/01_requirements/output/requirements.md`
- **設計書**: `.ai-workflow/issue-332/02_design/output/design.md`
- **CLAUDE.md**: プロジェクトの全体方針とコーディングガイドライン
- **scripts/ai-workflow/README.md**: AI Workflowの概要と使用方法
- **jenkins/README.md**: Jenkinsジョブの使用方法

### 11.2 関連Issue

- **Issue #313**: Planning Phase実装（既存実装）
- **Issue #305**: AI Workflowの全Phase E2Eテスト

---

**承認者**: （レビュー後に記入）
**承認日**: （レビュー後に記入）
