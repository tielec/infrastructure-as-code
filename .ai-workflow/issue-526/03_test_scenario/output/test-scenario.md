# テストシナリオ - Issue #526

## 環境停止スケジューラージョブの無効化

---

## 0. Planning Document 確認

本テストシナリオは Planning Phase（`.ai-workflow/issue-526/00_planning/output/planning.md`）で策定された開発計画に基づいて作成されています。

### Planning Phase で確認された戦略
- **実装戦略**: EXTEND（既存ファイルの機能拡張）
- **テスト戦略**: INTEGRATION_ONLY（Jenkins環境での統合テスト）
- **テストコード戦略**: CREATE_TEST（新規テストシナリオ作成）
- **複雑度**: 簡単（単一ファイルの1行修正）
- **工数見積**: 2-3時間
- **リスク評価**: 低

---

## 1. テスト戦略サマリー

### 1.1 選択されたテスト戦略: INTEGRATION_ONLY

**判断根拠**:
- Jenkins DSL の変更であり、単体テストよりもJenkins環境での統合テストが重要
- シードジョブ実行→ジョブ作成→スケジュール無効化確認という一連の流れを検証する必要がある
- ビジネスロジックがなく、BDD は不要（インフラ設定変更のみ）
- Jenkins の Job DSL Plugin、Cron Trigger、UI表示の統合的な動作確認が必要

### 1.2 テスト対象の範囲

#### 統合対象コンポーネント
1. **Git Repository** ↔ **Jenkins DSL ファイル**
2. **Jenkins DSL Plugin** ↔ **シードジョブ（job-creator）**
3. **シードジョブ** ↔ **Shutdown-Environment-Scheduler ジョブ**
4. **Jenkins UI** ↔ **ジョブ設定・表示**
5. **Cron Trigger** ↔ **スケジュール実行**

#### テストフォーカス
- DSL ファイル変更からジョブ無効化までの一連の統合フロー
- Jenkins 内部コンポーネント間の連携
- 手動実行機能の維持確認
- 他ジョブへの非影響確認

### 1.3 テストの目的

1. **機能統合確認**: DSL 変更が正しく Jenkins ジョブ設定に反映されること
2. **スケジュール統合確認**: Cron Trigger が正しく無効化されること
3. **UI統合確認**: Jenkins UI で無効化状態が正しく表示されること
4. **回帰確認**: 他のジョブに影響がないこと
5. **運用継続性確認**: 手動実行機能が維持されること

---

## 2. 統合テストシナリオ

### 2.1 テストケース1: DSL修正からジョブ無効化までの統合フロー

**シナリオ名**: End-to-End Job Disable Integration

**目的**:
DSL ファイル変更からシードジョブ実行、ジョブ無効化までの一連の統合プロセスが正常に動作することを検証

**前提条件**:
- Jenkins 環境が稼働している
- `infrastructure_shutdown_scheduler_job.groovy` が存在する
- `Admin_Jobs/job-creator` シードジョブが正常動作する
- Jenkins 管理者権限でアクセス可能

**テスト手順**:

#### Step 1: 現在の状態確認
```bash
# 1-1. 現在のジョブ状態確認
jenkins-cli get-job "Infrastructure_Management/Shutdown-Environment-Scheduler" | grep -i disabled
# 期待: disabled要素がない、またはdisabled=false

# 1-2. 現在のスケジュール確認
jenkins-cli get-job "Infrastructure_Management/Shutdown-Environment-Scheduler" | grep -o '<spec>H 15 \* \* \*</spec>'
# 期待: スケジュール設定が存在

# 1-3. 現在のビルド番号記録
BEFORE_BUILD=$(jenkins-cli get-job "Infrastructure_Management/Shutdown-Environment-Scheduler" | grep -o '<nextBuildNumber>[0-9]*</nextBuildNumber>' | grep -o '[0-9]*')
echo "変更前ビルド番号: $BEFORE_BUILD"
```

#### Step 2: DSL ファイル修正と Git 操作
```bash
# 2-1. DSL ファイルに disabled(true) を追加
echo "    disabled(true)" >> jenkins/jobs/dsl/infrastructure-management/infrastructure_shutdown_scheduler_job.groovy

# 2-2. 構文確認（基本チェック）
grep -n "disabled(true)" jenkins/jobs/dsl/infrastructure-management/infrastructure_shutdown_scheduler_job.groovy
# 期待: 追加した行が表示される

# 2-3. Git コミット
git add jenkins/jobs/dsl/infrastructure-management/infrastructure_shutdown_scheduler_job.groovy
git commit -m "[jenkins] update: スケジューラージョブを無効化 (disabled=true) - Issue #526"
```

#### Step 3: シードジョブ実行
```bash
# 3-1. シードジョブ実行
jenkins-cli build "Admin_Jobs/job-creator" -s

# 3-2. 実行結果確認
SEED_BUILD_NUMBER=$(jenkins-cli get-job "Admin_Jobs/job-creator" | grep -o '<nextBuildNumber>[0-9]*</nextBuildNumber>' | grep -o '[0-9]*')
SEED_BUILD_NUMBER=$((SEED_BUILD_NUMBER - 1))
jenkins-cli console "Admin_Jobs/job-creator" $SEED_BUILD_NUMBER | tail -20
# 期待: SUCCESS と表示される
```

#### Step 4: ジョブ無効化確認
```bash
# 4-1. Jenkins CLI でのジョブ状態確認
jenkins-cli get-job "Infrastructure_Management/Shutdown-Environment-Scheduler" | grep "<disabled>true</disabled>"
# 期待: disabled=true が検出される

# 4-2. Jenkins UI での確認（手動）
# ブラウザで Jenkins にアクセス
# Infrastructure_Management フォルダ → Shutdown-Environment-Scheduler ジョブ
# 期待: ジョブ名の横に無効化アイコン（グレーアウト）が表示
```

#### Step 5: スケジュール無効化確認
```bash
# 5-1. Trigger 設定は維持されているが無効化されていることを確認
jenkins-cli get-job "Infrastructure_Management/Shutdown-Environment-Scheduler" | grep -A5 -B5 "TimerTrigger"
# 期待: TimerTrigger設定は存在するが、disabled=trueにより実行されない

# 5-2. 次回スケジュール時刻での非実行確認（テスト日によって調整）
# 注意: 実際のスケジュール時刻（JST 00:00）まで待つか、時刻を進めてテスト
```

**期待結果**:
- シードジョブが SUCCESS で完了する
- `Infrastructure_Management/Shutdown-Environment-Scheduler` ジョブが無効状態になる
- Jenkins UI で無効化アイコンが表示される
- スケジュール実行が停止する
- DSL 構文エラーが発生しない

**確認項目チェックリスト**:
- [ ] シードジョブ実行が 5分以内に SUCCESS で完了
- [ ] CLI で `<disabled>true</disabled>` が確認できる
- [ ] Jenkins UI でジョブが無効化アイコンで表示される
- [ ] Cron Trigger 設定は維持されているが実行されない
- [ ] Git コミットが正常に記録されている

---

### 2.2 テストケース2: 手動実行機能の統合確認

**シナリオ名**: Manual Execution Integration Test

**目的**:
ジョブが無効化されても手動実行機能は正常に動作することを確認

**前提条件**:
- テストケース1 が正常完了している
- `Shutdown-Environment-Scheduler` ジョブが無効化されている
- `DRY_RUN` パラメータが利用可能

**テスト手順**:

#### Step 1: 手動実行の実行
```bash
# 1-1. DRY_RUN=true で安全に手動実行
jenkins-cli build "Infrastructure_Management/Shutdown-Environment-Scheduler" -s -p DRY_RUN=true

# 1-2. 実行完了まで待機
sleep 30
```

#### Step 2: 手動実行結果確認
```bash
# 2-1. ビルド結果確認
MANUAL_BUILD_NUMBER=$(jenkins-cli get-job "Infrastructure_Management/Shutdown-Environment-Scheduler" | grep -o '<nextBuildNumber>[0-9]*</nextBuildNumber>' | grep -o '[0-9]*')
MANUAL_BUILD_NUMBER=$((MANUAL_BUILD_NUMBER - 1))
jenkins-cli console "Infrastructure_Management/Shutdown-Environment-Scheduler" $MANUAL_BUILD_NUMBER

# 2-2. ビルド状況確認
jenkins-cli get-job "Infrastructure_Management/Shutdown-Environment-Scheduler" | grep -o '<result>[A-Z]*</result>'
# 期待: SUCCESS
```

#### Step 3: 下流ジョブとの統合確認
```bash
# 3-1. Shutdown_Jenkins_Environment ジョブがトリガーされることを確認
# 注意: DRY_RUN=trueのため実際の停止は行われない
jenkins-cli console "Infrastructure_Management/Shutdown-Environment-Scheduler" $MANUAL_BUILD_NUMBER | grep -i "shutdown"
# 期待: 停止処理のログが表示される（DRY_RUNモード）
```

**期待結果**:
- 手動実行が正常に完了する
- DRY_RUN モードで安全に実行される
- 下流の停止ジョブがトリガーされる（DRY_RUN で実際停止なし）

**確認項目チェックリスト**:
- [ ] 無効化されたジョブでも手動実行が可能
- [ ] 手動実行が SUCCESS で完了する
- [ ] DRY_RUN パラメータが正常に機能する
- [ ] 下流ジョブとの連携が維持されている

---

### 2.3 テストケース3: 他ジョブへの非影響確認（回帰テスト）

**シナリオ名**: Regression Test for Other Jobs

**目的**:
シードジョブ実行により他の Infrastructure_Management ジョブに意図しない影響がないことを確認

**前提条件**:
- シードジョブが正常実行されている
- 他の Infrastructure_Management ジョブが存在する

**テスト手順**:

#### Step 1: 関連ジョブの一覧確認
```bash
# 1-1. Infrastructure_Management フォルダ内のジョブ一覧
jenkins-cli list-jobs Infrastructure_Management/
# 期待: 複数のジョブが表示される（Shutdown-Environment-Scheduler, Shutdown_Jenkins_Environment等）
```

#### Step 2: 手動停止ジョブの状態確認
```bash
# 2-1. Shutdown_Jenkins_Environment ジョブが有効状態を維持していることを確認
jenkins-cli get-job "Infrastructure_Management/Shutdown_Jenkins_Environment" | grep -i disabled
# 期待: disabled要素が見つからない、またはdisabled=false

# 2-2. 手動停止ジョブの設定確認
jenkins-cli get-job "Infrastructure_Management/Shutdown_Jenkins_Environment" | grep -o '<displayName>.*</displayName>'
# 期待: 正常な表示名が確認できる
```

#### Step 3: 各ジョブの設定整合性確認
```bash
# 3-1. 各ジョブの XML 設定が正常であることを確認
for job in $(jenkins-cli list-jobs Infrastructure_Management/); do
  echo "チェック中: $job"
  jenkins-cli get-job "$job" > /dev/null 2>&1
  if [ $? -eq 0 ]; then
    echo "OK: $job"
  else
    echo "ERROR: $job"
  fi
done
```

#### Step 4: 他のスケジュールジョブの確認
```bash
# 4-1. 他にスケジュールされたジョブがある場合の影響確認
jenkins-cli list-jobs | xargs -I {} sh -c 'jenkins-cli get-job "{}" 2>/dev/null | grep -l "TimerTrigger" && echo "スケジュールジョブ: {}"'
# 各スケジュールジョブが正常に設定されていることを確認
```

**期待結果**:
- 他の Infrastructure_Management ジョブが正常状態を維持
- `Shutdown_Jenkins_Environment` ジョブが有効状態を保持
- 他のスケジュールジョブに影響なし
- すべてのジョブ設定が構文的に正常

**確認項目チェックリスト**:
- [ ] `Shutdown_Jenkins_Environment` ジョブが有効状態
- [ ] 他の Infrastructure_Management ジョブに設定変更なし
- [ ] 他のスケジュールジョブが正常動作
- [ ] ジョブ設定に構文エラーなし

---

### 2.4 テストケース4: スケジュール実行停止の時系列確認

**シナリオ名**: Schedule Execution Stop Verification

**目的**:
実際のスケジュール時刻にジョブが実行されないことを時系列で確認

**前提条件**:
- ジョブが無効化されている
- 次回スケジュール時刻（JST 00:00、UTC 15:00）が特定できる

**テスト手順**:

#### Step 1: スケジュール実行前の状態記録
```bash
# 1-1. 現在のビルド履歴確認
jenkins-cli get-job "Infrastructure_Management/Shutdown-Environment-Scheduler" | grep -o '<nextBuildNumber>[0-9]*</nextBuildNumber>' | grep -o '[0-9]*'
# 現在のビルド番号を記録

# 1-2. 最新ビルドの実行時刻確認
jenkins-cli console "Infrastructure_Management/Shutdown-Environment-Scheduler" -1 | head -5
# 最後の実行時刻を記録
```

#### Step 2: スケジュール時刻の監視
```bash
# 2-1. 次回スケジュール時刻の計算
# H 15 * * * = UTC 15:00頃 (Jenkins Hash値により数分前後)
# 実際のテストでは次の日の該当時刻まで監視

# 2-2. スケジュール時刻後の確認（翌日実行）
# 注意: 実際の運用では翌日確認が必要
```

#### Step 3: スケジュール時刻後の確認
```bash
# 3-1. ビルド番号の確認
AFTER_SCHEDULE=$(jenkins-cli get-job "Infrastructure_Management/Shutdown-Environment-Scheduler" | grep -o '<nextBuildNumber>[0-9]*</nextBuildNumber>' | grep -o '[0-9]*')
echo "スケジュール後ビルド番号: $AFTER_SCHEDULE"

# 3-2. ビルド履歴の確認
jenkins-cli console "Infrastructure_Management/Shutdown-Environment-Scheduler" -1 | head -10
# 期待: スケジュール時刻での新しい実行がない
```

**期待結果**:
- スケジュール時刻になってもジョブが実行されない
- ビルド番号が増加しない
- ビルド履歴に新しい実行記録がない

**確認項目チェックリスト**:
- [ ] 予定されたスケジュール時刻にジョブが実行されない
- [ ] ビルド番号が変化しない
- [ ] Jenkins ログにスケジュール実行の記録がない
- [ ] 無効化状態が継続している

---

### 2.5 テストケース5: ロールバック統合テスト

**シナリオ名**: Rollback Integration Test

**目的**:
Git revert による設定ロールバック機能が正常に動作することを確認

**前提条件**:
- ジョブが無効化されている
- Git 履歴に変更コミットが存在する

**テスト手順**:

#### Step 1: ロールバック実行
```bash
# 1-1. 変更コミットのハッシュ確認
COMMIT_HASH=$(git log --oneline -1 --grep="disabled.*true" | cut -d' ' -f1)
echo "ロールバック対象コミット: $COMMIT_HASH"

# 1-2. Git revert 実行
git revert $COMMIT_HASH --no-edit

# 1-3. ロールバックコミットの確認
git log --oneline -2
```

#### Step 2: シードジョブ再実行
```bash
# 2-1. シードジョブ実行
jenkins-cli build "Admin_Jobs/job-creator" -s

# 2-2. 実行結果確認
ROLLBACK_SEED_BUILD=$(jenkins-cli get-job "Admin_Jobs/job-creator" | grep -o '<nextBuildNumber>[0-9]*</nextBuildNumber>' | grep -o '[0-9]*')
ROLLBACK_SEED_BUILD=$((ROLLBACK_SEED_BUILD - 1))
jenkins-cli console "Admin_Jobs/job-creator" $ROLLBACK_SEED_BUILD | tail -10
```

#### Step 3: ジョブ有効化確認
```bash
# 3-1. ジョブが有効状態に戻ったことを確認
jenkins-cli get-job "Infrastructure_Management/Shutdown-Environment-Scheduler" | grep -i disabled
# 期待: disabled要素が見つからない、またはdisabled=false

# 3-2. Jenkins UI での確認
# ブラウザで確認: 無効化アイコンが消えていることを確認
```

#### Step 4: スケジュール再開確認
```bash
# 4-1. Trigger 設定の確認
jenkins-cli get-job "Infrastructure_Management/Shutdown-Environment-Scheduler" | grep -A5 -B5 "TimerTrigger"
# 期待: TimerTrigger が有効状態で設定されている
```

**期待結果**:
- Git revert が正常に実行される
- シードジョブ再実行により設定が元に戻る
- ジョブが有効状態に復旧する
- スケジュール実行が再開される

**確認項目チェックリスト**:
- [ ] Git revert が正常実行
- [ ] シードジョブ再実行が SUCCESS 完了
- [ ] ジョブが有効状態に復旧
- [ ] スケジュール設定が有効状態に戻る
- [ ] Jenkins UI でアイコンが正常表示

---

## 3. テストデータ

### 3.1 テスト用設定データ

#### 3.1.1 DSL ファイル修正内容
```groovy
// テスト対象の追加行
disabled(true)  // ジョブを無効化

// ロールバックテスト用の誤った設定例
disabled('invalid')  // 構文エラーテスト用（文字列は不正）
```

#### 3.1.2 Git コミットメッセージテンプレート
```bash
# 正常な変更コミット
git commit -m "[jenkins] update: スケジューラージョブを無効化 (disabled=true) - Issue #526"

# ロールバックコミット
git commit -m "[jenkins] revert: スケジューラージョブの無効化をロールバック - Issue #526"
```

#### 3.1.3 Jenkins CLI コマンドテンプレート
```bash
# ジョブ状態確認
jenkins-cli get-job "Infrastructure_Management/Shutdown-Environment-Scheduler"

# シードジョブ実行
jenkins-cli build "Admin_Jobs/job-creator" -s

# 手動実行（DRY_RUN）
jenkins-cli build "Infrastructure_Management/Shutdown-Environment-Scheduler" -s -p DRY_RUN=true

# コンソール出力確認
jenkins-cli console "JOB_NAME" BUILD_NUMBER
```

### 3.2 テスト環境固有データ

#### 3.2.1 Jenkins 環境情報
- **Jenkins URL**: dev 環境の Jenkins インスタンス
- **認証方式**: API Token または SSH Key
- **対象フォルダ**: `Infrastructure_Management/`
- **シードジョブ**: `Admin_Jobs/job-creator`

#### 3.2.2 時刻関連データ
- **スケジュール設定**: `H 15 * * *` (UTC 15:00、JST 00:00)
- **Jenkins Hash値**: 環境固有（実際の実行時刻に影響）
- **タイムゾーン**: JST (UTC+9)

---

## 4. テスト環境要件

### 4.1 必要なテスト環境

#### 4.1.1 Jenkins 環境
- **Jenkins インスタンス**: dev 環境の稼働中 Jenkins
- **必要プラグイン**:
  - Job DSL Plugin
  - Build Pipeline Plugin（必要に応じて）
- **権限**:
  - Jenkins 管理者権限または適切なジョブ実行権限
  - シードジョブ実行権限

#### 4.1.2 Git 環境
- **リポジトリ**: infrastructure-as-code リポジトリへの読み書きアクセス
- **ブランチ**: 作業用ブランチまたは main ブランチ（運用ポリシーに従う）
- **権限**: コミット・プッシュ権限

#### 4.1.3 ローカル環境
```bash
# 必要なツール
- Git クライアント
- Jenkins CLI (jenkins-cli.jar)
- curl または wget
- bash シェル環境

# Jenkins CLI セットアップ
wget http://jenkins-dev-url/jnlpJars/jenkins-cli.jar
export JENKINS_USER_ID="your-username"
export JENKINS_API_TOKEN="your-api-token"
```

### 4.2 テスト実行の前提条件

#### 4.2.1 システム稼働条件
- [ ] Jenkins dev 環境が稼働中
- [ ] `Admin_Jobs/job-creator` シードジョブが存在し実行可能
- [ ] `Infrastructure_Management/Shutdown-Environment-Scheduler` ジョブが存在
- [ ] `Infrastructure_Management/Shutdown_Jenkins_Environment` ジョブが存在

#### 4.2.2 アクセス権限
- [ ] Jenkins 管理者権限または適切な実行権限
- [ ] Git リポジトリへの読み書きアクセス権限
- [ ] Jenkins CLI 実行のための API Token

#### 4.2.3 安全性確認
- [ ] テスト環境での実行（本番環境では実行しない）
- [ ] `DRY_RUN=true` パラメータの活用
- [ ] バックアップとしての Git 履歴の確認

### 4.3 モック/スタブの必要性

#### 4.3.1 統合テストのため実モック不要
- Jenkins 実環境を使用するため、モック・スタブは基本的に不要
- DRY_RUN パラメータによる安全な実行を活用

#### 4.3.2 テスト用の安全措置
```bash
# DRY_RUN モード確認
if ! jenkins-cli get-job "Infrastructure_Management/Shutdown_Jenkins_Environment" | grep -q "DRY_RUN"; then
  echo "警告: DRY_RUN パラメータが利用できません"
  exit 1
fi
```

---

## 5. テスト実行手順書

### 5.1 事前準備チェックリスト

#### 5.1.1 環境確認
```bash
# Jenkins 接続確認
jenkins-cli who-am-i

# 対象ジョブの存在確認
jenkins-cli get-job "Infrastructure_Management/Shutdown-Environment-Scheduler" > /dev/null
jenkins-cli get-job "Admin_Jobs/job-creator" > /dev/null

# Git リポジトリ状態確認
git status
git log --oneline -5
```

#### 5.1.2 バックアップ作成
```bash
# 現在の設定バックアップ
jenkins-cli get-job "Infrastructure_Management/Shutdown-Environment-Scheduler" > backup-original-config.xml

# Git 状態記録
git log --oneline -1 jenkins/jobs/dsl/infrastructure-management/infrastructure_shutdown_scheduler_job.groovy
```

### 5.2 テスト実行順序

#### 推奨実行順序
1. **テストケース1**: DSL修正からジョブ無効化までの統合フロー
2. **テストケース2**: 手動実行機能の統合確認
3. **テストケース3**: 他ジョブへの非影響確認（回帰テスト）
4. **テストケース4**: スケジュール実行停止の時系列確認（翌日確認）
5. **テストケース5**: ロールバック統合テスト

#### 並行実行の注意
- テストケース1-3は連続して実行可能
- テストケース4は時間依存のため独立実行
- テストケース5はロールバックのため最後に実行

### 5.3 テスト結果記録テンプレート

```markdown
# テスト実行結果 - Issue #526

## テスト環境
- 実行日時: YYYY-MM-DD HH:MM:SS
- Jenkins環境: dev
- 実行者: [name]

## テストケース1: DSL修正からジョブ無効化までの統合フロー
- [ ] 実行完了
- [ ] 期待結果一致
- 備考:

## テストケース2: 手動実行機能の統合確認
- [ ] 実行完了
- [ ] 期待結果一致
- 備考:

## テストケース3: 他ジョブへの非影響確認
- [ ] 実行完了
- [ ] 期待結果一致
- 備考:

## テストケース4: スケジュール実行停止の時系列確認
- [ ] 実行完了
- [ ] 期待結果一致
- 備考:

## テストケース5: ロールバック統合テスト
- [ ] 実行完了
- [ ] 期待結果一致
- 備考:

## 総合評価
- [ ] すべてのテストケースが成功
- [ ] Issue #526 の要件を満たしている
```

---

## 6. エラーケース・例外処理テスト

### 6.1 DSL 構文エラーテスト

**目的**: 不正な DSL 構文がエラーとして適切に検出されることを確認

```bash
# 意図的に構文エラーを作成
echo "disabled('invalid')" >> jenkins/jobs/dsl/infrastructure-management/infrastructure_shutdown_scheduler_job.groovy

# シードジョブ実行
jenkins-cli build "Admin_Jobs/job-creator" -s

# エラー確認
jenkins-cli console "Admin_Jobs/job-creator" -1 | grep -i error
# 期待: エラーメッセージが出力される

# 修正
git checkout -- jenkins/jobs/dsl/infrastructure-management/infrastructure_shutdown_scheduler_job.groovy
```

### 6.2 権限不足エラーテスト

**目的**: 権限不足時の適切なエラーハンドリングを確認

```bash
# 権限を制限した状態でのアクセステスト
# 注意: 実際のテストでは権限制限の方法は環境依存
jenkins-cli -auth limited-user:token get-job "Infrastructure_Management/Shutdown-Environment-Scheduler"
# 期待: 権限エラーが返される
```

### 6.3 Git 操作失敗テスト

**目的**: Git 操作失敗時のロールバック手順を確認

```bash
# ファイルロック状態の模擬
chmod 444 jenkins/jobs/dsl/infrastructure-management/infrastructure_shutdown_scheduler_job.groovy

# 修正試行
echo "disabled(true)" >> jenkins/jobs/dsl/infrastructure-management/infrastructure_shutdown_scheduler_job.groovy
# 期待: Permission denied エラー

# 復旧
chmod 644 jenkins/jobs/dsl/infrastructure-management/infrastructure_shutdown_scheduler_job.groovy
```

---

## 7. 品質ゲート確認

### ✅ Phase 2の戦略に沿ったテストシナリオである

**確認事項**:
- [x] **INTEGRATION_ONLY 戦略**: Jenkins DSL Plugin、シードジョブ、UI、Cron Trigger の統合テストに特化
- [x] **Unit テストは含まない**: ビジネスロジックがないため Unit テスト不要
- [x] **BDD テストは含まない**: インフラ設定変更のみでビジネス要件のBDD不要
- [x] **新規テストシナリオ**: 既存テストの拡張ではなく、この変更に特化した独立テストを作成

### ✅ 主要な正常系がカバーされている

**カバー済み正常系**:
- [x] **DSL修正→シードジョブ実行→ジョブ無効化**: End-to-Endの主要フロー
- [x] **手動実行機能**: 無効化後も手動実行は維持される
- [x] **スケジュール停止**: Cron Trigger の無効化
- [x] **UI表示更新**: Jenkins UI での無効化表示
- [x] **ロールバック**: Git revert による復旧機能

### ✅ 主要な異常系がカバーされている

**カバー済み異常系**:
- [x] **DSL構文エラー**: 不正な disabled 設定値
- [x] **権限不足**: Jenkins アクセス権限不足
- [x] **Git操作失敗**: ファイル権限問題
- [x] **シードジョブ失敗**: DSL 評価エラー時の確認

### ✅ 期待結果が明確である

**明確な期待結果**:
- [x] **具体的な CLI コマンドと期待出力**: `<disabled>true</disabled>` の検出等
- [x] **チェックリスト形式**: 各テストケースで確認項目を明記
- [x] **数値的な基準**: 実行時間（5分以内）、SUCCESS ステータス等
- [x] **検証可能な条件**: Jenkins UI の視覚的確認と CLI の両方を併用

---

## 8. 実行タイミングと注意事項

### 8.1 推奨実行タイミング

#### テストケース1-3, 5 (即座実行可能)
- **推奨時間帯**: 平日営業時間内（09:00-17:00）
- **所要時間**: 約30-45分
- **必要リソース**: Jenkins 管理者権限、Git リポジトリアクセス

#### テストケース4 (時系列確認)
- **実行タイミング**: スケジュール時刻（JST 00:00）前後
- **確認タイミング**: 翌日の業務開始時
- **注意事項**: 実際の自動停止が発生しないことの確認

### 8.2 テスト実行の制約事項

#### 環境制約
- **dev環境限定**: 本番・ステージング環境での実行は禁止
- **営業時間**: Jenkins システムへの負荷を考慮した時間帯選択
- **権限管理**: 最小権限の原則に従った実行

#### 安全措置
- **DRY_RUN 必須**: 手動実行テストではDRY_RUN=true を指定
- **バックアップ確認**: Git 履歴によるロールバック準備
- **段階的実行**: 一度に全テストを実行せず、段階的に確認

---

## 9. 成功基準とテスト完了条件

### 9.1 個別テストケースの成功基準

各テストケースは以下の条件をすべて満たした場合に成功とみなします：

#### テストケース1: 統合フロー
- [ ] シードジョブが SUCCESS で完了
- [ ] ジョブが無効状態になる
- [ ] CLI と UI で無効化が確認できる
- [ ] Git コミットが記録される

#### テストケース2: 手動実行
- [ ] 無効化後も手動実行が成功
- [ ] DRY_RUN モードが正常動作
- [ ] 下流ジョブとの連携が維持される

#### テストケース3: 回帰テスト
- [ ] 他のジョブに変更がない
- [ ] Shutdown_Jenkins_Environment が有効状態維持
- [ ] 構文エラーが発生しない

#### テストケース4: スケジュール停止
- [ ] 予定時刻にジョブが実行されない
- [ ] ビルド番号が増加しない

#### テストケース5: ロールバック
- [ ] Git revert が成功
- [ ] ジョブが有効状態に復旧する

### 9.2 全体の成功基準

**テストシナリオ全体の成功条件**:
1. **すべてのテストケース（1-5）が成功する**
2. **要件定義書の受け入れ基準（AC-001〜AC-006）がすべて満たされる**
3. **品質ゲートの4つの必須要件がすべて通過する**
4. **エラーケーステストで適切なエラーハンドリングが確認される**

### 9.3 テスト完了の判定

以下の条件をすべて満たした時点でテストシナリオフェーズ完了とします：

- [ ] **機能統合**: DSL変更がJenkinsに正しく反映される
- [ ] **スケジュール統合**: 自動実行が停止し、手動実行が維持される
- [ ] **UI統合**: Jenkins UI で正しく状態表示される
- [ ] **回帰なし**: 他のジョブに影響がない
- [ ] **可逆性**: ロールバック手順が正常動作する
- [ ] **ドキュメント**: テスト結果が適切に記録される

---

**作成日**: 2025年1月17日
**作成者**: Claude Code
**バージョン**: 1.0
**関連Issue**: #526
**テスト戦略**: INTEGRATION_ONLY
**対象フェーズ**: Phase 3 - Test Scenario