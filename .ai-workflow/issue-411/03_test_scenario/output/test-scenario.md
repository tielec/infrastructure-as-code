# テストシナリオ - Issue #411

## ドキュメント情報

- **Issue番号**: #411
- **タイトル**: [TASK] AI Workflow V1 (Python版) の安全な削除計画
- **URL**: https://github.com/tielec/infrastructure-as-code/issues/411
- **作成日**: 2025年
- **対象環境**: infrastructure-as-code リポジトリ

---

## 0. 前提ドキュメントの確認

本テストシナリオは、以下のドキュメントに基づいて作成されています：

### Planning Phase成果物
- **Planning Document**: `.ai-workflow/issue-411/00_planning/output/planning.md`
- **実装戦略**: REFACTOR
- **テスト戦略**: **INTEGRATION_ONLY**
- **複雑度**: 中程度
- **見積もり工数**: 8~12時間

### 要件定義書
- **Requirements Document**: `.ai-workflow/issue-411/01_requirements/output/requirements.md`
- **機能要件**: FR-1～FR-9（9つの機能要件）
- **受け入れ基準**: AC-1～AC-9（Given-When-Then形式）
- **非機能要件**: NFR-1～NFR-5（安全性、信頼性、保守性、完全性、透明性）

### 設計書
- **Design Document**: `.ai-workflow/issue-411/02_design/output/design.md`
- **段階的削除戦略**: Phase 1～4（4フェーズ）
- **バックアップ戦略**: Gitブランチ（`archive/ai-workflow-v1-python`）
- **ロールバック手順**: 明確に定義済み

---

## 1. テスト戦略サマリー

### 1.1 選択されたテスト戦略

**INTEGRATION_ONLY**

### 1.2 テスト戦略の判断根拠（Phase 2より）

1. **ユニットテスト不要**
   - 削除作業であり、新規ロジックの追加がない
   - テスト対象となるコード実装が存在しない

2. **インテグレーションテスト必須**
   - Jenkins環境での動作確認が必要（V2を使用するジョブの正常動作）
   - ドキュメントのリンク切れチェックが必要
   - CI/CDパイプラインの正常動作確認が必要
   - V2ワークフローの全機能動作確認が必要

3. **BDDテスト不要**
   - エンドユーザー向けの新機能追加ではない
   - ユーザーストーリーが存在しない

### 1.3 テスト対象の範囲

- **削除対象**: `scripts/ai-workflow/` ディレクトリ全体
- **更新対象**: `jenkins/README.md`、その他V1を参照するドキュメント
- **動作確認対象**: Jenkins環境（V2ジョブ）、ドキュメント、CI/CDパイプライン

### 1.4 テストの目的

1. **安全性の確保**: V1削除後もJenkins環境が正常に動作することを確認
2. **完全性の確保**: V1への参照が完全に削除されていることを確認
3. **復元可能性の確保**: バックアップから復元できることを確認
4. **リンク切れ防止**: ドキュメントのリンクが有効であることを確認

---

## 2. Integrationテストシナリオ

### 2.1 バックアップと復元の統合テスト

#### INT-001: Gitブランチバックアップの作成と検証

**目的**: バックアップブランチが正常に作成され、リモートにプッシュされることを確認

**前提条件**:
- mainブランチにV1ディレクトリ（`scripts/ai-workflow/`）が存在する
- Gitリポジトリへの書き込み権限がある
- リモートリポジトリ（GitHub）への接続が可能

**テスト手順**:
1. 現在のブランチを確認
   ```bash
   git branch --show-current
   ```
2. アーカイブブランチを作成
   ```bash
   git checkout -b archive/ai-workflow-v1-python
   ```
3. ブランチが作成されたことを確認
   ```bash
   git branch | grep archive/ai-workflow-v1-python
   ```
4. リモートにプッシュ
   ```bash
   git push origin archive/ai-workflow-v1-python
   ```
5. GitHubでブランチが存在することを確認
   ```bash
   git ls-remote --heads origin | grep archive/ai-workflow-v1-python
   ```
6. mainブランチに戻る
   ```bash
   git checkout main
   ```

**期待結果**:
- ✓ `archive/ai-workflow-v1-python` ブランチが作成される
- ✓ ブランチがリモートリポジトリにプッシュされる
- ✓ mainブランチに戻れる

**確認項目**:
- [ ] ブランチ名が正しい（`archive/ai-workflow-v1-python`）
- [ ] リモートにブランチが存在する
- [ ] `scripts/ai-workflow/` ディレクトリが含まれている
- [ ] mainブランチに影響がない

---

#### INT-002: バックアップブランチからの復元テスト

**目的**: バックアップブランチから5分以内に復元できることを確認（NFR-1の検証）

**前提条件**:
- `archive/ai-workflow-v1-python` ブランチが存在する
- mainブランチで `scripts/ai-workflow/` が削除されている（シミュレーション）

**テスト手順**:
1. 開始時刻を記録
2. バックアップブランチからファイルを復元
   ```bash
   git checkout archive/ai-workflow-v1-python -- scripts/ai-workflow/
   ```
3. 復元されたことを確認
   ```bash
   ls -la scripts/ai-workflow/
   ```
4. 主要ファイルが存在することを確認
   ```bash
   test -f scripts/ai-workflow/README.md && echo "OK"
   test -f scripts/ai-workflow/main.py && echo "OK"
   ```
5. 終了時刻を記録し、所要時間を計算

**期待結果**:
- ✓ 5分以内に復元が完了する
- ✓ `scripts/ai-workflow/` ディレクトリが復元される
- ✓ 主要ファイル（README.md, main.py等）が存在する
- ✓ 復元されたファイルが削除前の状態と一致する

**確認項目**:
- [ ] 復元コマンドが正常に完了する
- [ ] 所要時間が5分以内である
- [ ] ファイル構造が元の状態と一致する
- [ ] ファイル内容が元の状態と一致する（サンプリング確認）

---

### 2.2 V1参照箇所の調査と削除の統合テスト

#### INT-003: V1参照箇所の全数調査

**目的**: リポジトリ内のV1への参照がすべて特定されることを確認

**前提条件**:
- リポジトリのルートディレクトリにいる
- `grep`、`find` コマンドが使用可能

**テスト手順**:
1. 全markdownファイルからV1への参照を検索
   ```bash
   grep -rn "scripts/ai-workflow" --include="*.md" . | grep -v "scripts/ai-workflow-v2" > /tmp/v1-refs-md.txt
   ```
2. Jenkinsジョブ定義からV1への参照を検索
   ```bash
   grep -rn "scripts/ai-workflow" jenkins/ --include="*.groovy" --include="Jenkinsfile" --include="*.yaml" | grep -v "scripts/ai-workflow-v2" > /tmp/v1-refs-jenkins.txt
   ```
3. スクリプトファイルからV1への参照を検索
   ```bash
   grep -rn "scripts/ai-workflow" --include="*.sh" --include="*.py" --include="*.ts" . | grep -v "scripts/ai-workflow-v2" | grep -v ".ai-workflow" > /tmp/v1-refs-scripts.txt
   ```
4. 検索結果を確認
   ```bash
   cat /tmp/v1-refs-md.txt
   cat /tmp/v1-refs-jenkins.txt
   cat /tmp/v1-refs-scripts.txt
   ```
5. 検索結果をリスト化し、各参照箇所を分類（更新/削除/影響なし）

**期待結果**:
- ✓ V1への参照がすべて検出される
- ✓ 検索結果が一覧化される
- ✓ 各参照箇所に判定（更新/削除/影響なし）が記載される

**確認項目**:
- [ ] `jenkins/README.md` (line 547) が検出される
- [ ] Jenkinsジョブ定義にV1への参照がないことが確認される
- [ ] その他のドキュメントにV1への参照があれば検出される
- [ ] 検索結果に漏れがない（V2への参照は除外されている）

---

#### INT-004: ドキュメントからのV1参照削除とリンク切れチェック

**目的**: ドキュメントからV1への参照が削除され、リンク切れがないことを確認

**前提条件**:
- V1参照箇所の調査が完了している（INT-003）
- 更新対象ドキュメントが特定されている

**テスト手順**:
1. `jenkins/README.md` からV1への参照を削除
   - line 547の削除、またはV2への参照に変更
2. その他のドキュメントからV1への参照を削除
3. 変更をコミット
   ```bash
   git add jenkins/README.md [その他の変更ファイル]
   git commit -m "[docs] update: AI Workflow V1への参照を削除"
   ```
4. 削除後、V1への参照が残っていないことを確認
   ```bash
   grep -rn "scripts/ai-workflow" --include="*.md" . | grep -v "scripts/ai-workflow-v2" | grep -v "archive/ai-workflow-v1-python" | grep -v ".ai-workflow"
   ```
5. ドキュメント内のリンクを手動で確認（サンプリング）
   - `jenkins/README.md` の主要リンク
   - `CLAUDE.md` の主要リンク
   - `ARCHITECTURE.md` の主要リンク

**期待結果**:
- ✓ V1への参照が削除される
- ✓ V2への参照は維持される
- ✓ リンク切れが存在しない
- ✓ ドキュメントの可読性が維持される

**確認項目**:
- [ ] `jenkins/README.md` からV1への参照が削除されている
- [ ] その他のドキュメントからV1への参照が削除されている
- [ ] V2への参照は正しく維持されている
- [ ] リンク切れが存在しない（手動確認）
- [ ] Markdown構文が正しい

---

### 2.3 Jenkins環境の統合テスト

#### INT-005: Jenkinsジョブの動作確認（削除前）

**目的**: 削除前にJenkinsジョブが正常に動作することを確認（ベースライン）

**前提条件**:
- Jenkins環境へのアクセス権限がある
- `AI_Workflow/ai_workflow_orchestrator` ジョブが存在する

**テスト手順**:
1. Jenkins UIにログイン
2. `AI_Workflow/ai_workflow_orchestrator` ジョブにアクセス
3. ジョブの設定を確認
   - `WORKFLOW_DIR` が `scripts/ai-workflow-v2` であることを確認
4. ジョブを手動実行
5. 実行結果を確認
   - ビルド成功（SUCCESS）
   - ログにエラーがない
   - 期待される成果物が生成される

**期待結果**:
- ✓ ジョブが正常に実行される（SUCCESS）
- ✓ V2（`scripts/ai-workflow-v2`）を使用している
- ✓ ログにエラーがない
- ✓ 期待される成果物が生成される

**確認項目**:
- [ ] ジョブがSUCCESS状態で完了する
- [ ] `WORKFLOW_DIR = 'scripts/ai-workflow-v2'` が設定されている
- [ ] V1への参照がログに含まれていない
- [ ] 実行時間が通常範囲内である

---

#### INT-006: Jenkinsジョブの動作確認（削除後）

**目的**: V1削除後もJenkinsジョブが正常に動作することを確認（NFR-2の検証）

**前提条件**:
- `scripts/ai-workflow/` ディレクトリが削除されている
- Jenkins環境へのアクセス権限がある

**テスト手順**:
1. Jenkins UIにログイン
2. `AI_Workflow/ai_workflow_orchestrator` ジョブにアクセス
3. ジョブを手動実行
4. 実行結果を確認
   - ビルド成功（SUCCESS）
   - ログにエラーがない
   - V1への参照によるエラーがない
5. INT-005の結果と比較
   - 実行時間が同程度
   - 成果物が同等

**期待結果**:
- ✓ ジョブが正常に実行される（SUCCESS）
- ✓ V1削除による影響がない
- ✓ ログにエラーがない
- ✓ INT-005と同等の結果が得られる

**確認項目**:
- [ ] ジョブがSUCCESS状態で完了する
- [ ] V1削除によるエラーが発生していない
- [ ] ログに `scripts/ai-workflow/` への参照がない
- [ ] 実行時間がINT-005と同程度である
- [ ] 成果物がINT-005と同等である

---

#### INT-007: Jenkins DSLファイルの検証

**目的**: Jenkins DSLファイルにV1への参照がないことを確認

**前提条件**:
- リポジトリのルートディレクトリにいる
- Jenkins DSLファイルへのアクセス権限がある

**テスト手順**:
1. DSLファイル（`ai_workflow_orchestrator.groovy`）を確認
   ```bash
   cat jenkins/jobs/dsl/ai-workflow/ai_workflow_orchestrator.groovy
   ```
2. V1への参照を検索
   ```bash
   grep "scripts/ai-workflow" jenkins/jobs/dsl/ai-workflow/ai_workflow_orchestrator.groovy | grep -v "scripts/ai-workflow-v2"
   ```
3. Jenkinsfile を確認
   ```bash
   cat jenkins/jobs/pipeline/ai-workflow/ai-workflow-orchestrator/Jenkinsfile
   ```
4. V1への参照を検索
   ```bash
   grep "scripts/ai-workflow" jenkins/jobs/pipeline/ai-workflow/ai-workflow-orchestrator/Jenkinsfile | grep -v "scripts/ai-workflow-v2"
   ```
5. folder-config.yaml を確認
   ```bash
   cat jenkins/jobs/pipeline/_seed/job-creator/folder-config.yaml
   ```
6. V1への参照を検索
   ```bash
   grep "scripts/ai-workflow" jenkins/jobs/pipeline/_seed/job-creator/folder-config.yaml | grep -v "scripts/ai-workflow-v2"
   ```

**期待結果**:
- ✓ DSLファイルにV1への参照がない
- ✓ JenkinsfileにV1への参照がない
- ✓ folder-config.yamlにV1への参照がない
- ✓ すべてのファイルがV2を参照している

**確認項目**:
- [ ] `ai_workflow_orchestrator.groovy` にV1への参照がない
- [ ] `Jenkinsfile` で `WORKFLOW_DIR = 'scripts/ai-workflow-v2'` が設定されている
- [ ] `folder-config.yaml` にV1への参照がない
- [ ] すべてのファイルがV2のみを参照している

---

### 2.4 Git操作の統合テスト

#### INT-008: V1ディレクトリの削除とコミット作成

**目的**: V1ディレクトリが正常に削除され、規約に従ったコミットが作成されることを確認

**前提条件**:
- バックアップブランチ（`archive/ai-workflow-v1-python`）が作成されている
- mainブランチにいる
- V1ディレクトリ（`scripts/ai-workflow/`）が存在する

**テスト手順**:
1. 現在のブランチを確認
   ```bash
   git branch --show-current
   ```
2. V1ディレクトリを削除
   ```bash
   git rm -rf scripts/ai-workflow/
   ```
3. 削除されたことを確認
   ```bash
   ls scripts/ | grep -v ai-workflow-v2
   ```
4. 削除内容をステージングエリアで確認
   ```bash
   git status
   ```
5. コミットを作成
   ```bash
   git commit -m "[scripts] remove: AI Workflow V1 (Python版) を削除

V2 (TypeScript版) への移行完了に伴い、V1を削除しました。

- 削除対象: scripts/ai-workflow/ ディレクトリ全体
- バックアップ: archive/ai-workflow-v1-python ブランチに保存
- 関連Issue: #411"
   ```
6. コミットメッセージを確認
   ```bash
   git log -1 --format="%s%n%n%b"
   ```
7. Co-Authorクレジットが含まれていないことを確認
   ```bash
   git log -1 --format="%b" | grep -i "co-authored-by" || echo "OK: Co-Authorなし"
   ```

**期待結果**:
- ✓ `scripts/ai-workflow/` ディレクトリが削除される
- ✓ コミットメッセージが規約に従っている
- ✓ Co-Authorクレジットが含まれていない
- ✓ 削除以外の意図しない変更が含まれていない

**確認項目**:
- [ ] `scripts/ai-workflow/` ディレクトリが存在しない
- [ ] コミットメッセージが `[scripts] remove: ...` で始まる
- [ ] コミットメッセージが日本語である
- [ ] Co-Authorクレジットが含まれていない（CLAUDE.md line 364）
- [ ] 削除以外の変更が含まれていない（`git show` で確認）

---

#### INT-009: ロールバックの実行と検証

**目的**: ロールバック手順が正常に動作することを確認（NFR-1の検証）

**前提条件**:
- `archive/ai-workflow-v1-python` ブランチが存在する
- mainブランチで `scripts/ai-workflow/` が削除されている

**テスト手順**:
1. 開始時刻を記録
2. バックアップブランチからファイルを復元
   ```bash
   git checkout archive/ai-workflow-v1-python -- scripts/ai-workflow/
   ```
3. 復元されたことを確認
   ```bash
   ls -la scripts/ai-workflow/
   ```
4. 復元をコミット
   ```bash
   git commit -m "[rollback] restore: AI Workflow V1 (Python版) を復元"
   ```
5. Jenkinsジョブの動作確認
   - Jenkins UIで `AI_Workflow/ai_workflow_orchestrator` を実行
   - 実行結果を確認（SUCCESS）
6. 終了時刻を記録し、所要時間を計算

**期待結果**:
- ✓ 5分以内にロールバックが完了する
- ✓ `scripts/ai-workflow/` ディレクトリが復元される
- ✓ 復元後にJenkinsが正常に動作する
- ✓ 復元されたファイルが削除前の状態と一致する

**確認項目**:
- [ ] 復元が5分以内に完了する
- [ ] `scripts/ai-workflow/` ディレクトリが存在する
- [ ] 主要ファイル（README.md, main.py等）が存在する
- [ ] Jenkinsジョブが正常に実行される（SUCCESS）
- [ ] ファイル内容が元の状態と一致する

---

### 2.5 CI/CDパイプラインの統合テスト

#### INT-010: CI/CDパイプラインの動作確認（削除後）

**目的**: V1削除後もCI/CDパイプラインが正常に動作することを確認

**前提条件**:
- `scripts/ai-workflow/` ディレクトリが削除されている
- CI/CD環境へのアクセス権限がある

**テスト手順**:
1. CI/CDパイプラインをトリガー
   - mainブランチへのプッシュ、または手動実行
2. パイプラインの実行を監視
3. 各ステージの実行結果を確認
   - ビルドステージ: SUCCESS
   - テストステージ: SUCCESS
   - デプロイステージ（該当する場合）: SUCCESS
4. ログを確認
   - V1への参照によるエラーがない
   - 警告が発生していない
5. 実行時間を記録（ベースラインとの比較）

**期待結果**:
- ✓ CI/CDパイプラインがエラーなく完了する
- ✓ V1削除による影響がない
- ✓ ログにエラー・警告がない
- ✓ 実行時間がベースラインと同程度である

**確認項目**:
- [ ] 全ステージがSUCCESS状態で完了する
- [ ] ログに `scripts/ai-workflow/` への参照がない
- [ ] エラー・警告が発生していない
- [ ] 実行時間が通常範囲内である
- [ ] 成果物が正常に生成される

---

### 2.6 V2ワークフローの統合テスト

#### INT-011: V2ワークフローの全機能動作確認

**目的**: V1削除後もV2ワークフローがすべての機能で正常に動作することを確認

**前提条件**:
- `scripts/ai-workflow/` ディレクトリが削除されている
- V2ワークフロー（`scripts/ai-workflow-v2/`）が存在する
- テストリポジトリまたは本番リポジトリへのアクセス権限がある

**テスト手順**:
1. V2ワークフローの存在を確認
   ```bash
   ls -la scripts/ai-workflow-v2/
   ```
2. V2の主要機能をテスト（簡易テスト）
   - Phase 0（Planning）の実行
   - Phase 1（Requirements）の実行
   - Phase 2（Design）の実行
   - （時間的制約がある場合は、Phase 0のみ実行）
3. 実行結果を確認
   - 各フェーズが正常に完了する
   - 成果物が生成される
   - エラーが発生しない
4. V1への依存がないことを確認
   - ログに `scripts/ai-workflow/` への参照がない
   - エラーメッセージにV1関連の記述がない

**期待結果**:
- ✓ V2ワークフローが正常に動作する
- ✓ V1削除による影響がない
- ✓ すべての主要機能が動作する
- ✓ 成果物が正常に生成される

**確認項目**:
- [ ] V2ワークフローが実行できる
- [ ] Phase 0（Planning）が正常に完了する
- [ ] 成果物（planning.md等）が生成される
- [ ] ログにV1への参照がない
- [ ] エラー・警告が発生していない

---

### 2.7 完全性チェックの統合テスト

#### INT-012: V1参照の完全削除の検証

**目的**: リポジトリ内にV1への参照が完全に削除されていることを確認（NFR-4の検証）

**前提条件**:
- V1ディレクトリが削除されている
- ドキュメントが更新されている

**テスト手順**:
1. 全ファイルからV1への参照を検索
   ```bash
   grep -r "scripts/ai-workflow" --include="*" . \
     | grep -v "scripts/ai-workflow-v2" \
     | grep -v "archive/ai-workflow-v1-python" \
     | grep -v ".ai-workflow" \
     | grep -v ".git/"
   ```
2. 検索結果を確認
   - 結果がゼロ件であることを確認
   - 結果が存在する場合は、各参照を確認（許容される参照か）
3. 主要ファイルを個別確認
   ```bash
   grep "scripts/ai-workflow" jenkins/README.md | grep -v "scripts/ai-workflow-v2"
   grep "scripts/ai-workflow" CLAUDE.md | grep -v "scripts/ai-workflow-v2"
   grep "scripts/ai-workflow" ARCHITECTURE.md | grep -v "scripts/ai-workflow-v2"
   ```
4. 検索結果を文書化

**期待結果**:
- ✓ V1への参照がゼロ件である
- ✓ V2への参照は維持されている
- ✓ バックアップブランチへの参照のみ許容される
- ✓ `.ai-workflow` ディレクトリ内の参照は許容される

**確認項目**:
- [ ] 全ファイルからV1への参照がゼロ件である（許容される参照を除く）
- [ ] `jenkins/README.md` にV1への参照がない
- [ ] `CLAUDE.md` にV1への参照がない（あるいは削除記録のみ）
- [ ] `ARCHITECTURE.md` にV1への参照がない
- [ ] Jenkinsジョブ定義にV1への参照がない

---

## 3. テストデータ

### 3.1 バックアップ/復元テスト用データ

| データ項目 | 値 |
|-----------|-----|
| バックアップブランチ名 | `archive/ai-workflow-v1-python` |
| 削除対象ディレクトリ | `scripts/ai-workflow/` |
| 主要ファイル（確認用） | `scripts/ai-workflow/README.md`<br>`scripts/ai-workflow/main.py`<br>`scripts/ai-workflow/ARCHITECTURE.md` |

### 3.2 V1参照検索用パターン

| 検索パターン | 除外パターン |
|------------|-------------|
| `scripts/ai-workflow` | `scripts/ai-workflow-v2` |
| `scripts/ai-workflow` | `archive/ai-workflow-v1-python` |
| `scripts/ai-workflow` | `.ai-workflow` |
| `scripts/ai-workflow` | `.git/` |

### 3.3 Jenkins環境テスト用データ

| データ項目 | 値 |
|-----------|-----|
| ジョブ名 | `AI_Workflow/ai_workflow_orchestrator` |
| V2ディレクトリ | `scripts/ai-workflow-v2/` |
| 期待される環境変数 | `WORKFLOW_DIR = 'scripts/ai-workflow-v2'` |

### 3.4 コミットメッセージ検証用データ

| データ項目 | 値 |
|-----------|-----|
| コミットメッセージプレフィックス | `[scripts] remove:` |
| 言語 | 日本語 |
| 禁止文字列 | `Co-Authored-By: Claude` |
| 期待されるキーワード | `V1`, `削除`, `バックアップ`, `archive/ai-workflow-v1-python` |

---

## 4. テスト環境要件

### 4.1 ローカル環境

- **OS**: Linux/macOS/WSL
- **Git**: バージョン 2.x以上
- **シェル**: Bash 4.x以上
- **権限**: リポジトリへの読み書き権限
- **ネットワーク**: GitHubへのアクセス

### 4.2 Jenkins環境

- **Jenkins**: バージョン 2.x以上
- **権限**: ジョブの実行権限
- **アクセス**: Jenkins UIへのアクセス
- **ジョブ**: `AI_Workflow/ai_workflow_orchestrator` が存在する

### 4.3 CI/CD環境

- **パイプライン**: mainブランチのCI/CDパイプラインが設定されている
- **権限**: パイプラインの実行・監視権限
- **アクセス**: CI/CDプラットフォームへのアクセス

### 4.4 モック/スタブの必要性

- **該当なし**: 本テストでは実環境を使用するため、モック/スタブは不要

---

## 5. テスト実行順序

### 5.1 推奨実行順序

```
Phase 1: 削除前の準備とベースライン確認
  ├── INT-003: V1参照箇所の全数調査
  ├── INT-005: Jenkinsジョブの動作確認（削除前）
  └── INT-007: Jenkins DSLファイルの検証
       │
       ▼
Phase 2: バックアップと復元の検証
  ├── INT-001: Gitブランチバックアップの作成と検証
  ├── INT-002: バックアップブランチからの復元テスト
  └── INT-009: ロールバックの実行と検証
       │
       ▼
Phase 3: ドキュメント更新の検証
  └── INT-004: ドキュメントからのV1参照削除とリンク切れチェック
       │
       ▼
Phase 4: 削除実行と動作確認
  ├── INT-008: V1ディレクトリの削除とコミット作成
  ├── INT-006: Jenkinsジョブの動作確認（削除後）
  ├── INT-010: CI/CDパイプラインの動作確認（削除後）
  ├── INT-011: V2ワークフローの全機能動作確認
  └── INT-012: V1参照の完全削除の検証
```

### 5.2 実行時の注意事項

1. **Phase 1の完全実施**: 削除前にベースラインを確認
2. **Phase 2の事前検証**: 削除前にバックアップと復元を検証
3. **Phase 3の完了確認**: ドキュメント更新を削除前に完了
4. **Phase 4の慎重な実行**: 削除は最後のステップ

---

## 6. 受け入れ基準との対応

### 6.1 機能要件との対応

| 機能要件 | 対応するテストシナリオ |
|---------|---------------------|
| FR-1: Deprecated化の実施 | （Phase 4実装時に手動確認） |
| FR-2: V1参照箇所の全数調査 | INT-003 |
| FR-3: Jenkinsジョブの確認と更新 | INT-005, INT-006, INT-007 |
| FR-4: ドキュメント更新 | INT-004 |
| FR-5: バックアップ作成 | INT-001 |
| FR-6: 実際の削除実行 | INT-008 |
| FR-7: 削除後の動作確認 | INT-006, INT-010, INT-011 |
| FR-8: ロールバック手順の検証 | INT-002, INT-009 |
| FR-9: 変更履歴の記録 | （Phase 7実装時に手動確認） |

### 6.2 非機能要件との対応

| 非機能要件 | 対応するテストシナリオ |
|----------|---------------------|
| NFR-1: 安全性（5分以内に復元可能） | INT-002, INT-009 |
| NFR-2: 信頼性（Jenkins正常動作） | INT-005, INT-006 |
| NFR-3: 保守性（リンク切れなし） | INT-004 |
| NFR-4: 完全性（V1参照ゼロ件） | INT-003, INT-012 |
| NFR-5: 透明性（記録が残る） | INT-008 |

### 6.3 受け入れ基準との対応

| 受け入れ基準 | 対応するテストシナリオ |
|------------|---------------------|
| AC-1: Deprecated化 | （Phase 4実装時に手動確認） |
| AC-2: V1参照箇所調査 | INT-003 |
| AC-3: Jenkinsジョブ更新 | INT-007 |
| AC-4: ドキュメント更新 | INT-004 |
| AC-5: バックアップ作成 | INT-001 |
| AC-6: 削除実行 | INT-008 |
| AC-7: 削除後動作確認 | INT-006, INT-010, INT-011 |
| AC-8: ロールバック手順検証 | INT-002, INT-009 |
| AC-9: 変更履歴記録 | （Phase 7実装時に手動確認） |

---

## 7. テストスケジュール

### 7.1 見積もり時間

| テストシナリオ | 見積もり時間 |
|-------------|------------|
| INT-001: バックアップ作成 | 15分 |
| INT-002: 復元テスト | 15分 |
| INT-003: V1参照調査 | 30分 |
| INT-004: ドキュメント更新確認 | 30分 |
| INT-005: Jenkins確認（削除前） | 15分 |
| INT-006: Jenkins確認（削除後） | 15分 |
| INT-007: DSLファイル検証 | 15分 |
| INT-008: 削除とコミット | 15分 |
| INT-009: ロールバック検証 | 20分 |
| INT-010: CI/CD確認 | 20分 |
| INT-011: V2ワークフロー確認 | 30分 |
| INT-012: 完全性チェック | 15分 |
| **合計** | **3時間55分** |

### 7.2 実施タイミング

- **Phase 1実装前**: INT-003, INT-005, INT-007（ベースライン確認）
- **Phase 4実装前**: INT-001, INT-002, INT-009（バックアップ検証）
- **Phase 4実装中**: INT-004（ドキュメント更新確認）
- **Phase 4実装後**: INT-006, INT-008, INT-010, INT-011, INT-012（削除後確認）

---

## 8. リスクと対策

### 8.1 テスト実行時のリスク

| リスク | 影響度 | 対策 |
|--------|--------|------|
| バックアップ作成失敗 | 高 | INT-001で事前検証、リモートプッシュを必須化 |
| 復元失敗 | 高 | INT-002, INT-009で事前検証 |
| Jenkins環境でのエラー | 中 | INT-005でベースライン確認、INT-006で比較 |
| V1参照の見落とし | 中 | INT-003で徹底的な検索、INT-012で最終確認 |
| CI/CDパイプライン停止 | 高 | INT-010で削除後に即座確認 |

### 8.2 軽減策

1. **削除前の徹底的な検証**: Phase 1でベースラインを確認
2. **バックアップの必須化**: INT-001で確実にバックアップを作成
3. **段階的なテスト実行**: 推奨実行順序を厳守
4. **ロールバック準備**: INT-009でロールバック手順を検証済み

---

## 9. 品質ゲート（Phase 3）

本テストシナリオは以下の品質ゲートを満たしています：

- [x] **Phase 2の戦略に沿ったテストシナリオである**: INTEGRATION_ONLY戦略に基づき、12のインテグレーションテストシナリオを作成
- [x] **主要な正常系がカバーされている**: バックアップ作成、削除、復元、Jenkins動作確認など主要なフローをカバー
- [x] **主要な異常系がカバーされている**: ロールバックシナリオ（INT-009）で異常時の対応をカバー
- [x] **期待結果が明確である**: 各テストシナリオで期待結果と確認項目を明記

---

## 10. 関連ドキュメント

- **Planning Document**: `.ai-workflow/issue-411/00_planning/output/planning.md`
- **Requirements Document**: `.ai-workflow/issue-411/01_requirements/output/requirements.md`
- **Design Document**: `.ai-workflow/issue-411/02_design/output/design.md`
- **GitHub Issue**: https://github.com/tielec/infrastructure-as-code/issues/411
- **プロジェクトガイド**: `CLAUDE.md`, `ARCHITECTURE.md`, `CONTRIBUTION.md`, `README.md`
- **関連Issue**: #369 (AI Workflow V2 マルチリポジトリ対応), #405 (フェーズ依存関係のオプショナル化)

---

## 11. 承認

本テストシナリオは次フェーズ（Phase 4: 実装）に進むための品質ゲートを満たしています。クリティカルシンキングレビューで承認されれば、実装フェーズへ進行します。

---

## 12. 変更履歴

| 日付 | バージョン | 変更内容 | 担当 |
|------|-----------|----------|------|
| 2025年 | 1.0 | 初版作成（INTEGRATION_ONLYテスト戦略に基づく） | AI Workflow Bot |
