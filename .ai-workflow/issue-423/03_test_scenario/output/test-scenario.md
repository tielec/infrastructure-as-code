# テストシナリオ - Issue #423

## 0. Planning Documentの確認

本テストシナリオは、以下のドキュメントで策定された戦略に基づいて作成します：

- **Planning Document**: `.ai-workflow/issue-423/00_planning/output/planning.md`
- **Requirements Document**: `.ai-workflow/issue-423/01_requirements/output/requirements.md`
- **Design Document**: `.ai-workflow/issue-423/02_design/output/design.md`

**テスト戦略**: INTEGRATION_ONLY（Jenkins環境での統合テストのみ）

---

## 1. テスト戦略サマリー

### 1.1 選択されたテスト戦略

**INTEGRATION_ONLY**

### 1.2 テスト対象の範囲

| コンポーネント | テスト対象 | 理由 |
|--------------|----------|------|
| `setJenkinsQuietMode()` | Jenkins Controller QuietDown制御 | Jenkins API統合 |
| `getRunningAgentExecutors()` | エージェントExecutor監視 | Jenkins API統合 |
| `waitForAgentJobsCompletion()` | ジョブ完了待機ロジック | エージェント統合 |
| `scaleDownEC2Fleet()` | gracefulモードのフロー全体 | SpotFleet統合 |

### 1.3 テストの目的

1. **Jenkins QuietDown機能との統合検証**
   - QuietDownモードが正常に有効化/無効化されること
   - 新規ジョブキューが停止されること

2. **エージェント監視機能の統合検証**
   - エージェント上のExecutor状態が正確に取得されること
   - built-inエージェントが除外されること

3. **gracefulシャットダウンフローの統合検証**
   - 実行中ジョブの完了を待機してからスケールダウンすること
   - タイムアウト時でもジョブが失敗しないこと

4. **既存動作（immediateモード）の互換性検証**
   - 既存の動作が変更されていないこと

### 1.4 テスト環境

- **環境**: dev環境のJenkins Controller
- **エージェント**: SpotFleet Agents（dev環境）
- **実行方法**: 手動実行（Jenkins UIから）

---

## 2. Integrationテストシナリオ

### カテゴリ1: Jenkins QuietDownモード制御（FR-001）

#### TC-QD-01: QuietDown有効化の正常動作

**目的**: Jenkins QuietDownモードが正常に有効化されることを検証

**前提条件**:
- dev環境のJenkins Controllerが起動中
- Jenkins UIにアクセス可能
- Script Security承認が完了している（必要な場合）

**テスト手順**:
1. shutdown-environmentジョブを開く
2. パラメータを設定:
   - `ENVIRONMENT`: `dev`
   - `AWS_REGION`: `ap-northeast-1`
   - `CONFIRM_SHUTDOWN`: `true`
   - `SHUTDOWN_MODE`: `graceful`
   - `WAIT_TIMEOUT_MINUTES`: `5`（テスト用に短縮）
   - `DRY_RUN`: `false`
3. ジョブを実行
4. ジョブログを確認
5. Jenkins UIのトップページを確認

**期待結果**:
- ✓ ジョブログに「Jenkins QuietDownモードを有効化しました」が表示される
- ✓ ジョブログに「新規ジョブのキューは停止されました」が表示される
- ✓ Jenkins UIのトップページに「Prepare for shutdown」メッセージが表示される
- ✓ 新規ジョブがキューに追加されない（手動で確認）

**確認項目**:
- [ ] ログに成功メッセージが表示されているか
- [ ] Jenkins UIにQuietDownメッセージが表示されているか
- [ ] 新規ジョブをキューに追加しようとしても拒否されるか

---

#### TC-QD-02: QuietDownキャンセルの正常動作

**目的**: QuietDownモードが正常にキャンセルされ、新規ジョブが受付可能になることを検証

**前提条件**:
- TC-QD-01が完了し、QuietDownモードが有効
- または、事前にScript Consoleで`Jenkins.instance.doQuietDown()`を実行

**テスト手順**:
1. Jenkins Script Consoleで以下を実行して状態を確認:
   ```groovy
   Jenkins.instance.isQuietingDown()
   ```
2. shutdown-environmentジョブのログを確認し、処理が完了するまで待機
3. ジョブ完了後、再度Script Consoleで状態を確認:
   ```groovy
   Jenkins.instance.isQuietingDown()
   ```
4. テスト用ジョブを新規にキューに追加

**期待結果**:
- ✓ ジョブログに「Jenkins QuietDownモードをキャンセルしました」が表示される
- ✓ ジョブ完了後、`isQuietingDown()`が`false`を返す
- ✓ 新規ジョブがキューに正常に追加される

**確認項目**:
- [ ] QuietDownキャンセルログが表示されているか
- [ ] Jenkins UIから「Prepare for shutdown」メッセージが消えているか
- [ ] 新規ジョブが正常にキューに追加されるか

---

#### TC-QD-03: Script Security承認エラー時のハンドリング

**目的**: Script Security承認が必要な場合、エラーメッセージが表示され処理が続行されることを検証

**前提条件**:
- Script Security承認が未完了の状態
- または、Script Consoleで承認を一時的に削除

**テスト手順**:
1. Jenkins管理 > In-process Script Approval で、`doQuietDown`の承認を削除（可能な場合）
2. shutdown-environmentジョブを実行（パラメータは TC-QD-01 と同じ）
3. ジョブログを確認

**期待結果**:
- ✓ ジョブログに「警告: Jenkins QuietDownモードの有効化に失敗」が表示される
- ✓ ジョブログに「Script Security承認が必要な可能性があります」が表示される
- ✓ ジョブログに承認方法（In-process Script Approval）が表示される
- ✓ ジョブログに「処理を続行します」が表示される
- ✓ ジョブがエラーで失敗しない（SUCCESSステータス）

**確認項目**:
- [ ] エラーメッセージが表示されているか
- [ ] ヘルプメッセージ（承認方法）が表示されているか
- [ ] ジョブが失敗せずに続行されているか

---

#### TC-QD-04: DRY_RUNモードでのスキップ

**目的**: DRY_RUNモード時、QuietDown処理がスキップされることを検証

**前提条件**:
- dev環境のJenkins Controllerが起動中

**テスト手順**:
1. shutdown-environmentジョブを開く
2. パラメータを設定:
   - `ENVIRONMENT`: `dev`
   - `SHUTDOWN_MODE`: `graceful`
   - `DRY_RUN`: `true`
3. ジョブを実行
4. ジョブログを確認

**期待結果**:
- ✓ ジョブログに「DRY_RUN: Jenkins QuietDownモードを有効化します（スキップ）」が表示される
- ✓ Jenkins UIに「Prepare for shutdown」メッセージが表示されない
- ✓ 実際にQuietDownモードが有効化されていない

**確認項目**:
- [ ] DRY_RUNスキップログが表示されているか
- [ ] Jenkins UIの状態が変更されていないか

---

### カテゴリ2: エージェント実行中ジョブ監視（FR-002）

#### TC-EX-01: エージェントジョブなしの場合

**目的**: エージェント上にジョブが実行されていない場合、0が返されることを検証

**前提条件**:
- dev環境のSpotFleet Agentsが稼働中（キャパシティ1以上）
- エージェント上でジョブが実行されていない（全エージェントがアイドル）

**テスト手順**:
1. Jenkins > ノード管理 で、全エージェントがアイドル状態であることを確認
2. shutdown-environmentジョブを実行（パラメータ: `SHUTDOWN_MODE=graceful`、`DRY_RUN=false`）
3. ジョブログで「残りのエージェント実行中ジョブ」メッセージを確認

**期待結果**:
- ✓ ジョブログに「残りのエージェント実行中ジョブ: 0」が表示される
- ✓ ジョブログに「✓ 全エージェントジョブが完了しました」が即座に表示される
- ✓ 待機時間がほぼゼロ（15秒未満）

**確認項目**:
- [ ] 実行中ジョブ数が0とカウントされているか
- [ ] 待機がスキップされているか

---

#### TC-EX-02: エージェントジョブ実行中の場合

**目的**: エージェント上でジョブが実行中の場合、正確な数が返されることを検証

**前提条件**:
- dev環境のSpotFleet Agentsが稼働中
- テスト用の長時間ジョブ（5分程度のsleepジョブ）を準備

**テスト手順**:
1. テスト用長時間ジョブをエージェント上で実行開始
   ```groovy
   // テスト用Pipelineジョブ
   node('agent-label') {
       sleep(time: 5, unit: 'MINUTES')
   }
   ```
2. Jenkins > ノード管理 で、エージェントがビジー状態であることを確認
3. shutdown-environmentジョブを実行（パラメータ: `SHUTDOWN_MODE=graceful`、`WAIT_TIMEOUT_MINUTES=10`）
4. ジョブログを確認

**期待結果**:
- ✓ ジョブログに「残りのエージェント実行中ジョブ: 1」が表示される
- ✓ ジョブログに実行中ジョブの詳細（ジョブ名、ノード名）が表示される
   - 例: 「実行中ジョブ: test-long-job #1 (ノード: agent-i-0123456789abcdef)」
- ✓ テスト用ジョブが完了すると、「残りのエージェント実行中ジョブ: 0」に変化
- ✓ その後、「✓ 全エージェントジョブが完了しました」が表示される

**確認項目**:
- [ ] 実行中ジョブ数が正確にカウントされているか
- [ ] ジョブ名とノード名が正しく表示されているか
- [ ] ジョブ完了後、カウントが0に変化しているか

---

#### TC-EX-03: built-inエージェントの除外

**目的**: built-inエージェント（Controller）が監視対象から除外されることを検証

**前提条件**:
- dev環境のJenkins Controllerが起動中
- built-inエージェント上でジョブが実行中（shutdown-environmentジョブ自体）

**テスト手順**:
1. shutdown-environmentジョブを実行（パラメータ: `SHUTDOWN_MODE=graceful`）
2. ジョブログで「実行中ジョブ」メッセージを確認
3. built-inエージェント上で実行中のジョブがカウントされていないことを確認

**期待結果**:
- ✓ shutdown-environmentジョブ自体（built-inで実行中）がカウントされない
- ✓ ジョブログに built-in ノード上のジョブが表示されない
- ✓ エージェント（SpotFleet）上のジョブのみがカウントされる

**確認項目**:
- [ ] built-inエージェントが除外されているか
- [ ] ログに built-in 上のジョブが表示されていないか

---

#### TC-EX-04: オフラインノードのスキップ

**目的**: オフライン状態のノードがスキップされることを検証

**前提条件**:
- dev環境のSpotFleet Agentsが稼働中
- 1台のエージェントを手動でオフラインに設定

**テスト手順**:
1. Jenkins > ノード管理 で、1台のエージェントを「Temporarily offline」に設定
2. shutdown-environmentジョブを実行（パラメータ: `SHUTDOWN_MODE=graceful`）
3. ジョブログを確認

**期待結果**:
- ✓ オフラインノードがカウント対象外
- ✓ オンライン状態のエージェントのみが監視対象
- ✓ エラーが発生しない

**確認項目**:
- [ ] オフラインノードがスキップされているか
- [ ] オンラインノードのみがカウントされているか

---

#### TC-EX-05: Script Security承認エラー時のハンドリング

**目的**: Script Security承認が必要な場合、エラーメッセージが表示され0を返すことを検証

**前提条件**:
- Script Security承認が未完了の状態

**テスト手順**:
1. Jenkins管理 > In-process Script Approval で、Jenkins API関連の承認を削除（可能な場合）
2. shutdown-environmentジョブを実行（パラメータ: `SHUTDOWN_MODE=graceful`）
3. ジョブログを確認

**期待結果**:
- ✓ ジョブログに「エージェントExecutor監視でエラー」が表示される
- ✓ ジョブログに「Script Security承認が必要な可能性があります」が表示される
- ✓ 承認が必要なメソッド一覧が表示される
- ✓ 0を返して処理が続行される（安全側に倒す）
- ✓ ジョブがエラーで失敗しない

**確認項目**:
- [ ] エラーメッセージが表示されているか
- [ ] ヘルプメッセージ（承認方法とメソッド一覧）が表示されているか
- [ ] 0を返して処理が続行されているか

---

### カテゴリ3: エージェントジョブ完了待機（FR-003）

#### TC-WAIT-01: ジョブ完了後の正常終了

**目的**: エージェントジョブが完了した後、待機が正常に終了することを検証

**前提条件**:
- dev環境のSpotFleet Agentsが稼働中
- テスト用の短時間ジョブ（1分程度のsleepジョブ）を準備

**テスト手順**:
1. テスト用短時間ジョブをエージェント上で実行開始
   ```groovy
   node('agent-label') {
       sleep(time: 1, unit: 'MINUTES')
   }
   ```
2. 即座にshutdown-environmentジョブを実行（パラメータ: `SHUTDOWN_MODE=graceful`、`WAIT_TIMEOUT_MINUTES=10`）
3. ジョブログを確認
4. 待機時間を測定

**期待結果**:
- ✓ ジョブログに「=== エージェントジョブの完了を待機 ===」が表示される
- ✓ ジョブログに「タイムアウト: 10分」が表示される
- ✓ 15秒間隔で「残りのエージェント実行中ジョブ: X」が表示される
- ✓ 経過時間が定期的にログ出力される（例: 「経過時間: 0.3分」）
- ✓ テスト用ジョブ完了後、「✓ 全エージェントジョブが完了しました」が表示される
- ✓ 待機時間がテスト用ジョブの実行時間とほぼ一致（約1分）

**確認項目**:
- [ ] 待機開始メッセージが表示されているか
- [ ] 15秒間隔でポーリングログが表示されているか
- [ ] 経過時間が正しく表示されているか
- [ ] ジョブ完了後、正常に待機が終了しているか

---

#### TC-WAIT-02: タイムアウト時のハンドリング

**目的**: タイムアウトに達した場合、警告ログが表示されジョブが成功ステータスになることを検証

**前提条件**:
- dev環境のSpotFleet Agentsが稼働中
- テスト用の長時間ジョブ（10分以上のsleepジョブ）を準備

**テスト手順**:
1. テスト用長時間ジョブをエージェント上で実行開始
   ```groovy
   node('agent-label') {
       sleep(time: 15, unit: 'MINUTES')
   }
   ```
2. shutdown-environmentジョブを実行（パラメータ: `SHUTDOWN_MODE=graceful`、`WAIT_TIMEOUT_MINUTES=2`）
3. 2分間待機
4. ジョブログとジョブステータスを確認

**期待結果**:
- ✓ 2分後、ジョブログに「警告: エージェントジョブのタイムアウト（2分）に達しました」が表示される
- ✓ ジョブログに「SpotFleetのスケールダウンを続行します」が表示される
- ✓ ジョブログに「実行中のジョブは強制終了される可能性があります」が表示される
- ✓ タイムアウト時の実行中ジョブ数が表示される（例: 「タイムアウト時の実行中ジョブ数: 1」）
- ✓ ジョブログに「処理を続行します」が表示される
- ✓ ジョブステータスが`SUCCESS`（失敗しない）
- ✓ 次のステップ（SpotFleetスケールダウン）が実行される

**確認項目**:
- [ ] タイムアウト警告メッセージが表示されているか
- [ ] タイムアウト時の実行中ジョブ数が表示されているか
- [ ] ジョブステータスがSUCCESSか
- [ ] 次のステップが実行されているか

---

#### TC-WAIT-03: 経過時間ログの定期出力

**目的**: 経過時間が15秒ごとに正しくログ出力されることを検証

**前提条件**:
- dev環境のSpotFleet Agentsが稼働中
- テスト用の中時間ジョブ（2分程度のsleepジョブ）を準備

**テスト手順**:
1. テスト用中時間ジョブをエージェント上で実行開始
   ```groovy
   node('agent-label') {
       sleep(time: 2, unit: 'MINUTES')
   }
   ```
2. shutdown-environmentジョブを実行（パラメータ: `SHUTDOWN_MODE=graceful`、`WAIT_TIMEOUT_MINUTES=10`）
3. ジョブログで経過時間の表示を確認

**期待結果**:
- ✓ 約15秒間隔で経過時間が表示される
- ✓ 経過時間が正しく増加している（例: 0.3分 → 0.5分 → 0.8分 → ...）
- ✓ 経過時間が小数点第1位まで表示される
- ✓ ジョブ完了後、最終的な待機時間が表示される

**確認項目**:
- [ ] 15秒間隔で経過時間が表示されているか
- [ ] 経過時間が正しく増加しているか
- [ ] 表示形式が正しいか（小数点第1位まで）

---

#### TC-WAIT-04: ユーザー手動中断時のハンドリング

**目的**: ユーザーがジョブを手動で中断した場合、エラーメッセージが表示され処理が続行されることを検証

**前提条件**:
- dev環境のSpotFleet Agentsが稼働中
- テスト用の長時間ジョブ（5分程度のsleepジョブ）を準備

**テスト手順**:
1. テスト用長時間ジョブをエージェント上で実行開始
2. shutdown-environmentジョブを実行（パラメータ: `SHUTDOWN_MODE=graceful`、`WAIT_TIMEOUT_MINUTES=10`）
3. 待機中（1分後程度）、Jenkins UIでジョブの「Abort」ボタンをクリック
4. ジョブログを確認

**期待結果**:
- ✓ ジョブログに「警告: ジョブ待機が中断されました」が表示される
- ✓ ジョブログに「処理を続行します」が表示される
- ✓ ジョブステータスが`ABORTED`（または`SUCCESS`）
- ✓ エラーで失敗しない

**確認項目**:
- [ ] 中断メッセージが表示されているか
- [ ] 処理続行メッセージが表示されているか
- [ ] ジョブが失敗していないか

---

### カテゴリ4: スケールダウンフロー全体（FR-004）

#### TC-SCALE-01: gracefulモードの5ステップ実行

**目的**: gracefulモード時、5つのステップが順番に実行されることを検証

**前提条件**:
- dev環境のJenkins Controllerが起動中
- dev環境のSpotFleet Agentsが稼働中（キャパシティ1以上）
- エージェント上にジョブが実行されていない（全アイドル）

**テスト手順**:
1. shutdown-environmentジョブを実行
2. パラメータを設定:
   - `ENVIRONMENT`: `dev`
   - `AWS_REGION`: `ap-northeast-1`
   - `CONFIRM_SHUTDOWN`: `true`
   - `SHUTDOWN_MODE`: `graceful`
   - `WAIT_TIMEOUT_MINUTES`: `5`
   - `DRY_RUN`: `false`
3. ジョブログを確認
4. 各ステップの実行順序を検証

**期待結果**:
- ✓ ジョブログに「--- Gracefulモードでスケールダウン ---」が表示される
- ✓ ステップ1: 「Jenkins QuietDownモードを有効化」が表示される
- ✓ ステップ2: 「エージェントジョブの完了を待機」が表示される
- ✓ ステップ3: 「SpotFleetのキャパシティを0に設定」が表示される
- ✓ ステップ4: 「インスタンスの終了を待機」が表示される
- ✓ ステップ5: 「Jenkins QuietDownモードをキャンセル」が表示される
- ✓ 各ステップが順番に実行される（並行実行されない）
- ✓ ジョブが成功ステータスで完了

**確認項目**:
- [ ] 5つのステップが全て表示されているか
- [ ] ステップが順番に実行されているか（1→2→3→4→5）
- [ ] 各ステップの完了メッセージが表示されているか
- [ ] ジョブが成功しているか

---

#### TC-SCALE-02: immediateモードの既存動作維持

**目的**: immediateモード時、既存の動作が維持されることを検証

**前提条件**:
- dev環境のJenkins Controllerが起動中
- dev環境のSpotFleet Agentsが稼働中（キャパシティ1以上）

**テスト手順**:
1. shutdown-environmentジョブを実行
2. パラメータを設定:
   - `ENVIRONMENT`: `dev`
   - `SHUTDOWN_MODE`: `immediate`
   - `DRY_RUN`: `false`
3. ジョブログを確認

**期待結果**:
- ✓ ジョブログに「--- Immediateモードでスケールダウン ---」が表示される
- ✓ QuietDown処理がスキップされる（ログに表示されない）
- ✓ エージェントジョブ完了待機がスキップされる（ログに表示されない）
- ✓ SpotFleetスケールダウンが即座に実行される
- ✓ ジョブログに「Immediateモードのため、インスタンス終了待機をスキップします」が表示される
- ✓ 処理時間が短い（1分未満）

**確認項目**:
- [ ] Immediateモードのログが表示されているか
- [ ] QuietDown処理がスキップされているか
- [ ] ジョブ完了待機がスキップされているか
- [ ] 既存の動作と同じか

---

#### TC-SCALE-03: gracefulモードのエラー時QuietDownキャンセル

**目的**: gracefulモードでエラーが発生した場合、QuietDownがキャンセルされることを検証

**前提条件**:
- dev環境のJenkins Controllerが起動中
- SpotFleet Request IDが無効な状態（または、AWS認証情報が無効）

**テスト手順**:
1. SSMパラメータストアのSpotFleet Request IDを一時的に無効な値に変更（または、IAMロールを一時的に削除）
2. shutdown-environmentジョブを実行（パラメータ: `SHUTDOWN_MODE=graceful`）
3. ジョブログを確認

**期待結果**:
- ✓ QuietDownが有効化される
- ✓ SpotFleetスケールダウンでエラーが発生
- ✓ ジョブログに「SpotFleetのスケールダウンでエラー」が表示される
- ✓ ジョブログに「エラー発生のため、QuietDownモードをキャンセルします」が表示される
- ✓ QuietDownがキャンセルされる
- ✓ ジョブログに「警告: SpotFleetのスケールダウンでエラーが発生しましたが、処理を続行します」が表示される
- ✓ ジョブが成功ステータス（失敗しない）

**確認項目**:
- [ ] エラーが発生しているか
- [ ] QuietDownキャンセルのログが表示されているか
- [ ] 警告メッセージが表示されているか
- [ ] ジョブが失敗していないか

---

#### TC-SCALE-04: キャパシティが既に0の場合のスキップ

**目的**: SpotFleetキャパシティが既に0の場合、処理がスキップされることを検証

**前提条件**:
- dev環境のJenkins Controllerが起動中
- dev環境のSpotFleet Agentsが既にスケールダウン済み（キャパシティ0）

**テスト手順**:
1. 事前にshutdown-environmentジョブを実行してキャパシティを0にする
2. 再度shutdown-environmentジョブを実行（パラメータ: `SHUTDOWN_MODE=graceful`）
3. ジョブログを確認

**期待結果**:
- ✓ ジョブログに「現在のキャパシティ: 0」が表示される
- ✓ ジョブログに「SpotFleetのキャパシティは既に0です」が表示される
- ✓ QuietDown処理がスキップされる
- ✓ スケールダウン処理がスキップされる
- ✓ ジョブが成功ステータス

**確認項目**:
- [ ] キャパシティ0のメッセージが表示されているか
- [ ] スケールダウン処理がスキップされているか
- [ ] ジョブが成功しているか

---

### カテゴリ5: エラーハンドリング（FR-005）

#### TC-ERR-01: タイムアウト時のジョブ成功

**目的**: タイムアウトが発生した場合でも、ジョブがSUCCESSステータスになることを検証

**前提条件**:
- TC-WAIT-02と同様

**テスト手順**:
- TC-WAIT-02の手順を実行

**期待結果**:
- ✓ タイムアウト警告が表示される
- ✓ ジョブステータスが`SUCCESS`
- ✓ ジョブステータスが`FAILURE`にならない

**確認項目**:
- [ ] ジョブステータスがSUCCESSか
- [ ] Jenkins UIでジョブが緑色（成功）で表示されるか

---

#### TC-ERR-02: Jenkins API失敗時のログ出力

**目的**: Jenkins API呼び出しが失敗した場合、エラーログが出力されることを検証

**前提条件**:
- TC-QD-03またはTC-EX-05と同様

**テスト手順**:
- TC-QD-03またはTC-EX-05の手順を実行

**期待結果**:
- ✓ エラーログが表示される
- ✓ エラーメッセージが明確（何が失敗したか）
- ✓ 処理が続行される

**確認項目**:
- [ ] エラーログが表示されているか
- [ ] エラーメッセージが明確か
- [ ] 処理が続行されているか

---

#### TC-ERR-03: Script Security承認時のヘルプメッセージ

**目的**: Script Security承認が必要な場合、承認方法がログに表示されることを検証

**前提条件**:
- TC-QD-03またはTC-EX-05と同様

**テスト手順**:
- TC-QD-03またはTC-EX-05の手順を実行

**期待結果**:
- ✓ ヘルプメッセージが表示される
- ✓ Jenkins管理 > In-process Script Approval の場所が記載されている
- ✓ 承認が必要なメソッド一覧が表示される
- ✓ 承認方法が明確

**確認項目**:
- [ ] ヘルプメッセージが表示されているか
- [ ] 承認方法が明確か
- [ ] 承認が必要なメソッド一覧が表示されているか

---

### カテゴリ6: ログ出力の強化（FR-006）

#### TC-LOG-01: 処理進捗ログの出力

**目的**: 処理の進捗状況が明確にログ出力されることを検証

**前提条件**:
- dev環境のJenkins Controllerが起動中
- dev環境のSpotFleet Agentsが稼働中

**テスト手順**:
1. shutdown-environmentジョブを実行（パラメータ: `SHUTDOWN_MODE=graceful`）
2. ジョブログを確認
3. 各ステップの開始・完了ログを検証

**期待結果**:
- ✓ ジョブログに以下が表示される:
  - 「=== EC2 Fleet (SpotFleet) のスケールダウン ===」
  - 「現在のキャパシティ: X」
  - 「--- Gracefulモードでスケールダウン ---」
  - 「ステップ1: Jenkins QuietDownモードを有効化」
  - 「✓ Jenkins QuietDownモードを有効化しました」
  - 「新規ジョブのキューは停止されました」
  - 「ステップ2: エージェントジョブの完了を待機」
  - 「=== エージェントジョブの完了を待機 ===」
  - 「タイムアウト: X分」
  - 「残りのエージェント実行中ジョブ: X」（15秒間隔）
  - 「経過時間: X分」
  - 「✓ 全エージェントジョブが完了しました」
  - 「ステップ3: SpotFleetのキャパシティを0に設定」
  - 「ステップ4: インスタンスの終了を待機」
  - 「ステップ5: Jenkins QuietDownモードをキャンセル」
  - 「✓ Jenkins QuietDownモードをキャンセルしました」

**確認項目**:
- [ ] 全ステップの開始ログが表示されているか
- [ ] 全ステップの完了ログが表示されているか
- [ ] 進捗状況が追跡可能か

---

#### TC-LOG-02: タイムアウト時の警告メッセージ

**目的**: タイムアウト時に明確な警告メッセージが表示されることを検証

**前提条件**:
- TC-WAIT-02と同様

**テスト手順**:
- TC-WAIT-02の手順を実行

**期待結果**:
- ✓ ジョブログに以下が表示される:
  - 「警告: エージェントジョブのタイムアウト（X分）に達しました」
  - 「SpotFleetのスケールダウンを続行します」
  - 「実行中のジョブは強制終了される可能性があります」
  - 「タイムアウト時の実行中ジョブ数: X」
  - 「処理を続行します」

**確認項目**:
- [ ] 警告メッセージが明確か
- [ ] ユーザーが状況を理解できるか
- [ ] 次のアクション（スケールダウン続行）が明記されているか

---

## 3. テストデータ

### 3.1 ジョブパラメータのテストデータ

#### 正常系データセット

| データセット名 | ENVIRONMENT | SHUTDOWN_MODE | WAIT_TIMEOUT_MINUTES | DRY_RUN | 用途 |
|-------------|------------|--------------|---------------------|---------|------|
| DS-01 | dev | graceful | 5 | false | graceful短時間テスト |
| DS-02 | dev | graceful | 30 | false | gracefulデフォルト |
| DS-03 | dev | immediate | 30 | false | immediateモード |
| DS-04 | dev | graceful | 30 | true | DRY_RUNモード |

#### 異常系データセット

| データセット名 | ENVIRONMENT | SHUTDOWN_MODE | WAIT_TIMEOUT_MINUTES | DRY_RUN | 用途 |
|-------------|------------|--------------|---------------------|---------|------|
| DS-ERR-01 | dev | graceful | 2 | false | タイムアウトテスト |
| DS-ERR-02 | dev | graceful | 30 | false | Script Security未承認 |

### 3.2 テスト用ダミージョブ

#### 短時間ジョブ（1分）

```groovy
pipeline {
    agent { label 'agent-label' }
    stages {
        stage('Test') {
            steps {
                echo 'Test job started'
                sleep(time: 1, unit: 'MINUTES')
                echo 'Test job completed'
            }
        }
    }
}
```

#### 中時間ジョブ（2分）

```groovy
pipeline {
    agent { label 'agent-label' }
    stages {
        stage('Test') {
            steps {
                echo 'Test job started'
                sleep(time: 2, unit: 'MINUTES')
                echo 'Test job completed'
            }
        }
    }
}
```

#### 長時間ジョブ（10分）

```groovy
pipeline {
    agent { label 'agent-label' }
    stages {
        stage('Test') {
            steps {
                echo 'Test job started'
                sleep(time: 10, unit: 'MINUTES')
                echo 'Test job completed'
            }
        }
    }
}
```

### 3.3 環境設定データ

#### dev環境の前提条件

| 項目 | 設定値 | 確認方法 |
|-----|-------|---------|
| SpotFleet Request ID | SSMパラメータストアから取得 | `aws ssm get-parameter --name /jenkins-infra/dev/agent/spotFleetRequestId` |
| 初期キャパシティ | 1以上 | Jenkins > ノード管理 |
| エージェントラベル | 環境に応じた値 | ジョブDSL設定を確認 |

---

## 4. テスト環境要件

### 4.1 必要なテスト環境

| 環境 | 必須/オプション | 用途 |
|-----|--------------|------|
| dev環境のJenkins Controller | 必須 | 全テストケース |
| dev環境のSpotFleet Agents | 必須 | エージェント監視テスト |
| Script Console | 必須 | 状態確認・Script Security承認テスト |
| Jenkins管理画面へのアクセス権限 | 必須 | Script Security承認、ノード管理 |

### 4.2 必要な外部サービス

| サービス | 必須/オプション | 用途 |
|---------|--------------|------|
| AWS CLI v2 | 必須 | SpotFleet操作 |
| AWS SSM Parameter Store | 必須 | リソースID取得 |
| AWS EC2 SpotFleet | 必須 | スケールダウンテスト |
| IAMロール権限 | 必須 | AWS API呼び出し |

### 4.3 モック/スタブの必要性

**不要** - 統合テストのため、実環境のコンポーネントをそのまま使用

### 4.4 Script Security承認

テスト実行前に、以下のメソッドをScript Approvalで承認する必要があります：

```
staticMethod jenkins.model.Jenkins getInstance
method jenkins.model.Jenkins doQuietDown
method jenkins.model.Jenkins doCancelQuietDown
method jenkins.model.Jenkins getComputers
method jenkins.model.Jenkins isQuietingDown
method hudson.model.Computer getName
method hudson.model.Computer isOffline
method hudson.model.Computer getExecutors
method hudson.model.Executor isBusy
method hudson.model.Executor getCurrentExecutable
```

**承認方法**:
1. Jenkins管理 > In-process Script Approval
2. 該当メソッドの「Approve」ボタンをクリック

---

## 5. テスト実行計画

### 5.1 テスト実行順序

#### フェーズ1: 基本機能テスト（優先度: 高）

実行順序:
1. TC-QD-01（QuietDown有効化）
2. TC-QD-02（QuietDownキャンセル）
3. TC-EX-01（エージェントジョブなし）
4. TC-EX-02（エージェントジョブ実行中）

**目的**: 基本的な機能が正常に動作することを確認

---

#### フェーズ2: エラーハンドリングテスト（優先度: 中）

実行順序:
1. TC-QD-03（Script Security承認エラー）
2. TC-EX-05（Script Security承認エラー）
3. TC-WAIT-02（タイムアウト）
4. TC-SCALE-03（gracefulモードエラー時QuietDownキャンセル）

**目的**: エラー時の動作が適切であることを確認

---

#### フェーズ3: 統合フローテスト（優先度: 高）

実行順序:
1. TC-SCALE-01（gracefulモード5ステップ実行）
2. TC-SCALE-02（immediateモード既存動作）
3. TC-WAIT-01（ジョブ完了後の正常終了）

**目的**: 全体のフローが正しく動作することを確認

---

#### フェーズ4: 補足テスト（優先度: 低）

実行順序:
1. TC-QD-04（DRY_RUNモード）
2. TC-EX-03（built-in除外）
3. TC-EX-04（オフラインノードスキップ）
4. TC-WAIT-03（経過時間ログ）
5. TC-WAIT-04（ユーザー手動中断）
6. TC-SCALE-04（キャパシティ0スキップ）
7. TC-LOG-01（処理進捗ログ）
8. TC-LOG-02（タイムアウト警告メッセージ）

**目的**: エッジケースや詳細な動作を確認

---

### 5.2 テスト実行時間見積もり

| フェーズ | テストケース数 | 見積もり時間 | 備考 |
|---------|-------------|------------|------|
| フェーズ1 | 4 | 30分 | 基本機能 |
| フェーズ2 | 4 | 40分 | タイムアウト待機を含む |
| フェーズ3 | 3 | 30分 | 統合フロー |
| フェーズ4 | 8 | 60分 | 補足テスト |
| **合計** | **19** | **2.5~3時間** | 不具合修正時間を除く |

---

### 5.3 テスト結果記録フォーマット

テスト実行後、以下のフォーマットで結果を記録してください：

#### テスト実行記録

| 項目 | 内容 |
|-----|------|
| 実行日時 | YYYY-MM-DD HH:MM:SS |
| 実行者 | 氏名 |
| 実行環境 | dev環境 |
| Jenkinsバージョン | 2.426.1以上 |

#### テストケース結果

| TC ID | テストケース名 | 結果 | 実行時刻 | 備考 |
|-------|--------------|------|---------|------|
| TC-QD-01 | QuietDown有効化 | Pass / Fail | HH:MM | エビデンス: screenshot-qd-01.png |
| TC-QD-02 | QuietDownキャンセル | Pass / Fail | HH:MM | エビデンス: screenshot-qd-02.png |
| ... | ... | ... | ... | ... |

#### 不具合記録

| 不具合ID | TC ID | 現象 | 原因 | 対応 | 対応日時 |
|---------|-------|------|------|------|---------|
| BUG-001 | TC-QD-01 | ... | ... | ... | YYYY-MM-DD HH:MM |

#### エビデンス

- ジョブログのスクリーンショット
- Jenkins UIのスクリーンショット（QuietDownメッセージ表示など）
- Script Consoleの実行結果

---

## 6. 受け入れ基準の対応

### 6.1 機能要件の受け入れ基準とテストケースの対応

| 受け入れ基準 | 対応するテストケース | 検証内容 |
|----------|------------------|---------|
| AC-001（QuietDownモード制御） | TC-QD-01、TC-QD-02 | QuietDown有効化/キャンセル |
| AC-002（エージェント監視） | TC-EX-01、TC-EX-02、TC-EX-03 | Executor数の正確なカウント |
| AC-003（ジョブ完了待機） | TC-WAIT-01、TC-WAIT-02 | 待機とタイムアウト処理 |
| AC-004（gracefulフロー） | TC-SCALE-01 | 5ステップの順次実行 |
| AC-005（immediateフロー） | TC-SCALE-02 | 既存動作の維持 |
| AC-006（タイムアウトエラーハンドリング） | TC-WAIT-02、TC-ERR-01 | タイムアウト時の成功ステータス |
| AC-007（API呼び出し失敗） | TC-QD-03、TC-EX-05、TC-ERR-02 | エラーハンドリング |
| AC-008（ログ出力） | TC-LOG-01、TC-LOG-02 | 進捗状況の可視化 |
| AC-009（パフォーマンス） | TC-WAIT-03 | 15秒間隔のポーリング |
| AC-010（セキュリティ） | TC-QD-03、TC-EX-05、TC-ERR-03 | Script Security承認 |
| AC-011（ジョブ実行の安全性） | TC-WAIT-01、TC-SCALE-01 | ジョブ完了待機 |
| AC-012（冪等性） | TC-SCALE-04 | キャパシティ0時のスキップ |

### 6.2 カバレッジサマリー

| カテゴリ | 要件数 | テストケース数 | カバレッジ |
|---------|-------|-------------|-----------|
| QuietDownモード制御（FR-001） | 1 | 4 | 100% |
| エージェント監視（FR-002） | 1 | 5 | 100% |
| ジョブ完了待機（FR-003） | 1 | 4 | 100% |
| スケールダウンフロー（FR-004） | 2 | 4 | 100% |
| エラーハンドリング（FR-005） | 1 | 3 | 100% |
| ログ出力（FR-006） | 1 | 2 | 100% |
| **合計** | **7** | **22** | **100%** |

---

## 7. リスクと軽減策

### 7.1 テスト実行リスク

#### リスク1: Script Security承認の遅延

- **影響度**: 中
- **確率**: 中
- **軽減策**:
  - テスト開始前に必要なメソッドを一括承認
  - 承認手順書を事前に準備
- **対応時間**: 10分程度

---

#### リスク2: dev環境のSpotFleet不安定

- **影響度**: 高
- **確率**: 低
- **軽減策**:
  - テスト前にSpotFleet状態を確認
  - エラー時は再実行
  - 最悪の場合、DRY_RUNモードでログのみ確認
- **対応時間**: 30分程度

---

#### リスク3: タイムアウトテストの長時間化

- **影響度**: 低
- **確率**: 高
- **軽減策**:
  - タイムアウト時間を短く設定（2分）
  - 長時間ジョブは必要最小限に
- **対応時間**: なし（見積もり時間に含む）

---

#### リスク4: 他ユーザーへの影響

- **影響度**: 中
- **確率**: 低
- **軽減策**:
  - テスト実行前にdev環境の使用状況を確認
  - 他ユーザーに事前通知
  - QuietDownテストは短時間で完了させる
- **対応時間**: なし（予防策のみ）

---

## 8. 品質ゲート（Phase 3）

### 8.1 品質ゲートチェックリスト

- [x] **Phase 2の戦略に沿ったテストシナリオである**
  - ✓ INTEGRATION_ONLYに準拠
  - ✓ 統合テストシナリオのみを作成
  - ✓ Unitテスト、BDDテストは含まれていない

- [x] **主要な正常系がカバーされている**
  - ✓ QuietDown有効化/キャンセル（TC-QD-01、TC-QD-02）
  - ✓ エージェント監視（TC-EX-01、TC-EX-02）
  - ✓ ジョブ完了待機（TC-WAIT-01）
  - ✓ gracefulモード5ステップ実行（TC-SCALE-01）
  - ✓ immediateモード既存動作（TC-SCALE-02）

- [x] **主要な異常系がカバーされている**
  - ✓ Script Security承認エラー（TC-QD-03、TC-EX-05）
  - ✓ タイムアウト（TC-WAIT-02）
  - ✓ gracefulモードエラー時QuietDownキャンセル（TC-SCALE-03）
  - ✓ ユーザー手動中断（TC-WAIT-04）

- [x] **期待結果が明確である**
  - ✓ 全テストケースにチェックボックス形式の確認項目を記載
  - ✓ ログ出力の具体的な内容を記載
  - ✓ ジョブステータスの期待値を明記

---

## 9. 補足情報

### 9.1 関連ドキュメント

- [Planning Document](../../00_planning/output/planning.md)
- [Requirements Document](../../01_requirements/output/requirements.md)
- [Design Document](../../02_design/output/design.md)

### 9.2 参考資料

- [Jenkins公式ドキュメント - Prepare for Shutdown](https://www.jenkins.io/doc/book/managing/prepare-for-shutdown/)
- [Jenkins Script Security Plugin](https://www.jenkins.io/doc/book/managing/script-approval/)

### 9.3 次のステップ

テストシナリオ作成後、以下の手順で進めてください：

1. **クリティカルシンキングレビューの実施**
   - 品質ゲート（4つの必須要件）を満たしているか確認
   - ブロッカー（次フェーズに進めない問題）がないか確認

2. **Script Security承認の準備**
   - 必要なメソッド一覧を管理者に共有
   - 承認手順を確認

3. **テスト環境の準備**
   - dev環境のSpotFleet状態を確認
   - テスト用ダミージョブを作成

4. **Phase 4（実装）への移行**
   - 品質ゲートを満たした後、実装フェーズに進む

---

**作成日**: 2025年1月
**作成者**: AI Workflow Phase 3 (Test Scenario)
**レビュー状態**: レビュー待ち
