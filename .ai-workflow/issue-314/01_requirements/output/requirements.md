# 要件定義書 - Issue #314

## ドキュメント情報

| 項目 | 内容 |
|------|------|
| Issue番号 | #314 |
| タイトル | [CI/CD] pytestコマンドを承認不要で実行できるようにする |
| 作成日 | 2025-10-10 |
| ステータス | Draft |
| 対象システム | AI Workflow Orchestrator (Jenkins Docker環境) |

---

## 1. 概要

### 1.1 背景

現在、JenkinsのDockerコンテナ内でAI Workflowを実行する際、以下のコマンドの実行に手動承認が必要となっている：

- `pytest` コマンド（Pythonテストフレームワーク）
- Bashスクリプトの実行

この手動承認プロセスにより、AI Agentが自律的にテストフェーズを完了できず、以下の問題が発生している：

1. **Phase 5（Testing）の自動化が不完全**：テストコード実装は完了しているが、実行には人間の介入が必須
2. **CI/CDパイプラインの中断**：手動承認待ちでワークフローが停止
3. **開発効率の低下**：テスト実行のたびに承認作業が必要

参照：[Issue #310のコメント](https://github.com/tielec/infrastructure-as-code/issues/310#issuecomment-3388025496)では、Phase 5（Testing）においてpytestコマンドの手動承認が必要であることが報告されている。

### 1.2 目的

Jenkins環境におけるスクリプト承認設定を適切に調整し、pytestコマンドとBashスクリプトの自動実行を可能にすることで、AI Workflowの完全自動化を実現する。

### 1.3 ビジネス価値

- **開発生産性の向上**：手動承認のボトルネック解消により、AI Workflowの実行時間を短縮
- **CI/CD自動化の完全性**：人間の介入なしで要件定義からテスト・レポート作成まで一貫して実行可能
- **運用コストの削減**：承認作業の削減により、開発者がコア業務に集中可能

### 1.4 技術的価値

- **Jenkins Script Approvalの理解深化**：セキュリティとユーザビリティのバランスを取る適切な設定方法の確立
- **Dockerコンテナセキュリティの最適化**：必要最小限の権限でスクリプト実行を許可
- **再利用可能な知見の獲得**：同様の問題に対する標準的な解決パターンを確立

---

## 2. 機能要件

### FR-1: Jenkins Script Approval設定の調整（優先度：高）

**要件**：Jenkinsの「In-process Script Approval」設定を調整し、pytest関連コマンドとBashスクリプトを承認不要で実行可能にする。

**詳細**：
- Jenkins管理画面（Manage Jenkins → In-process Script Approval）で以下のメソッド・コマンドを承認リストに追加：
  - `method hudson.model.Run getEnvironment`（環境変数アクセス）
  - `staticMethod org.codehaus.groovy.runtime.DefaultGroovyMethods execute java.lang.String`（Bashスクリプト実行）
  - pytest実行に必要なPython関連メソッド
- 承認リストの設定をコード化（JCasC: Jenkins Configuration as Code）

**受け入れ基準**：
- **Given**：JenkinsのDockerコンテナ環境が起動している
- **When**：Jenkinsfileから`sh 'pytest tests/'`コマンドを実行する
- **Then**：手動承認なしでpytestが実行され、テスト結果が返される

### FR-2: Dockerfileのセキュリティ設定の見直し（優先度：高）

**要件**：Dockerfile内のユーザー権限設定を見直し、コンテナ内でのスクリプト実行を適切に許可する。

**詳細**：
- 現在のDockerfile（`scripts/ai-workflow/Dockerfile`）のユーザー権限設定を確認
- 必要に応じてUSERディレクティブを追加（非rootユーザーでの実行を維持しつつ、必要な権限を付与）
- `chmod +x`によるスクリプト実行権限の明示的な設定

**受け入れ基準**：
- **Given**：Dockerイメージがビルドされている
- **When**：コンテナ内で`python main.py execute --phase testing --issue 310`を実行する
- **Then**：Dockerfileに起因する権限エラーが発生せず、pytestが実行される

### FR-3: Jenkins Groovyスクリプトによる承認リスト自動設定（優先度：中）

**要件**：Jenkins起動時にGroovy初期化スクリプトを実行し、Script Approval設定を自動的に構成する。

**詳細**：
- `scripts/jenkins/groovy/`配下にスクリプト承認を設定するGroovyスクリプトを作成
- スクリプトはJenkins起動時に自動実行される（init.groovy.d/経由）
- 承認が必要なメソッドシグネチャを事前定義リストとして管理

**受け入れ基準**：
- **Given**：Jenkinsコンテナが再起動された
- **When**：Jenkins管理画面のScript Approvalページを確認する
- **Then**：pytest関連のメソッドが事前承認済みとして表示される

### FR-4: JCasC（Jenkins Configuration as Code）による設定管理（優先度：中）

**要件**：Script Approval設定をJCasC YAMLファイルで管理し、インフラストラクチャコード化する。

**詳細**：
- `jenkins/config/jcasc/`配下にScript Approval設定用のYAMLファイルを作成
- 既存のJCasC設定と統合
- Git管理により、設定変更履歴を追跡可能にする

**受け入れ基準**：
- **Given**：JCasC YAMLファイルが作成・配置されている
- **When**：Jenkinsを再起動またはConfiguration Reloadを実行する
- **Then**：YAMLファイルに定義されたScript Approval設定が自動的に適用される

### FR-5: 検証用テストケースの実装（優先度：低）

**要件**：修正後の動作を検証するための統合テストケースを作成する。

**詳細**：
- `tests/integration/test_script_approval.py`として実装
- Jenkins APIを使用してScript Approval設定を確認
- 実際にpytestコマンドを実行し、承認なしで成功することを検証

**受け入れ基準**：
- **Given**：統合テストが実装されている
- **When**：`pytest tests/integration/test_script_approval.py -v`を実行する
- **Then**：すべてのテストケースがPASSする（承認なしでのpytest実行が成功）

---

## 3. 非機能要件

### 3.1 パフォーマンス要件

- **NFR-1**：Script Approval設定の適用時間は5秒以内（Jenkins起動時）
- **NFR-2**：設定変更によるJenkinsの再起動時間は増加させない（現状維持）
- **NFR-3**：pytest実行のオーバーヘッドは1秒以内（承認プロセス排除による高速化）

### 3.2 セキュリティ要件

- **NFR-4**：承認リストに追加するメソッドは最小限に限定（必要なもののみ）
- **NFR-5**：任意のコード実行を許可しない（ホワイトリスト方式の維持）
- **NFR-6**：Dockerコンテナの非rootユーザー実行を維持（セキュリティベストプラクティス）
- **NFR-7**：Jenkins管理画面へのアクセス制御を維持（未承認ユーザーによる設定変更を防止）

### 3.3 可用性・信頼性要件

- **NFR-8**：設定変更による既存Jenkinsジョブへの影響はゼロ
- **NFR-9**：Jenkins再起動後も設定が永続化される（JCasCまたはGroovyスクリプトによる自動復元）
- **NFR-10**：設定ミスによるJenkins起動失敗を防止（YAML構文検証、Groovyスクリプトのエラーハンドリング）

### 3.4 保守性・拡張性要件

- **NFR-11**：Script Approval設定はGit管理され、変更履歴が追跡可能
- **NFR-12**：新しいコマンド・メソッドの承認追加が容易（設定ファイルへの追記のみ）
- **NFR-13**：ドキュメント（README.md、CONTRIBUTION.md）に設定方法を明記
- **NFR-14**：他のJenkinsプロジェクトへの設定移植が容易（JCasC YAMLのコピーで対応可能）

---

## 4. 制約事項

### 4.1 技術的制約

- **TC-1**：Jenkinsのセキュリティポリシーに準拠（In-process Script Approvalの有効化は維持）
- **TC-2**：Dockerコンテナのセキュリティベストプラクティスを遵守（非rootユーザー、最小権限の原則）
- **TC-3**：既存のJenkins設定（JCasC、Groovyスクリプト）との互換性を維持
- **TC-4**：Python 3.11、pytest 8.x環境での動作を保証
- **TC-5**：Jenkins LTS（Long Term Support）バージョンとの互換性を確保

### 4.2 リソース制約

- **RC-1**：作業期間：1週間以内
- **RC-2**：Jenkinsの停止時間：最小限（設定適用のための再起動のみ）
- **RC-3**：追加のインフラリソース不要（既存Jenkins環境で対応）

### 4.3 ポリシー制約

- **PC-1**：プロジェクトのコーディング規約（CLAUDE.md、CONTRIBUTION.md）を遵守
- **PC-2**：日本語でのドキュメント作成（コメント、README）
- **PC-3**：Git管理：コミットメッセージは `[jenkins] fix: pytestコマンド承認不要化` 形式
- **PC-4**：セキュリティ監査：承認リスト追加は必ずレビューを経る

---

## 5. 前提条件

### 5.1 システム環境

- **Jenkins環境**：
  - Jenkins LTS 2.4xx以上
  - Docker Plugin導入済み
  - JCasC Plugin導入済み
  - Script Security Plugin導入済み
- **Dockerコンテナ**：
  - Python 3.11-slim-bullseye
  - Claude Code CLI（@anthropic-ai/claude-code）インストール済み
  - pytest、その他Python依存パッケージインストール済み
- **オペレーティングシステム**：
  - ホスト：Amazon Linux 2023
  - コンテナ：Debian Bullseye

### 5.2 依存コンポーネント

- **Jenkins Plugins**：
  - Script Security Plugin
  - Configuration as Code Plugin（JCasC）
  - Pipeline Plugin
  - Docker Plugin
- **Python Packages**：
  - pytest 8.x
  - pytest-cov
  - その他（requirements.txt定義）
- **外部ツール**：
  - Docker Engine 20.x以上
  - Git 2.x以上

### 5.3 外部システム連携

- **GitHub**：Issue #314、PR作成・管理
- **AWS Systems Manager Parameter Store**：Jenkins設定パラメータ管理（SSM経由）
- **Claude Agent SDK**：AI Workflowの実行エンジン

---

## 6. 受け入れ基準

### AC-1: pytest実行の自動化（最重要）

- **Given**：AI WorkflowのPhase 5（Testing）が実行される
- **When**：`python main.py execute --phase testing --issue 310`コマンドを実行する
- **Then**：
  - [ ] 手動承認なしでpytestが実行される
  - [ ] テスト結果（成功/失敗）が`.ai-workflow/issue-310/05_testing/output/test-result.md`に記録される
  - [ ] `HUMAN_INTERVENTION_REQUIRED.md`ファイルが生成されない

### AC-2: Bashスクリプト実行の自動化

- **Given**：JenkinsfileでBashスクリプトを実行する
- **When**：`sh 'bash scripts/test.sh'`ステートメントを実行する
- **Then**：
  - [ ] 手動承認なしでスクリプトが実行される
  - [ ] スクリプトの標準出力・エラー出力がJenkinsコンソールに表示される
  - [ ] スクリプトの終了コードが正しく返される

### AC-3: 設定の永続性

- **Given**：Script Approval設定が適用されている
- **When**：Jenkinsを再起動する
- **Then**：
  - [ ] 再起動後も承認リストが維持される
  - [ ] pytestコマンドが引き続き承認不要で実行可能

### AC-4: セキュリティの担保

- **Given**：Script Approval設定が適用されている
- **When**：未承認の危険なコマンド（例：`rm -rf /`）を実行しようとする
- **Then**：
  - [ ] 手動承認が要求される
  - [ ] 未承認のまま実行されない

### AC-5: 既存機能への影響なし

- **Given**：Script Approval設定が変更された
- **When**：既存のJenkinsジョブを実行する
- **Then**：
  - [ ] 既存ジョブが正常に動作する
  - [ ] エラーや警告が発生しない

### AC-6: ドキュメント整備

- **Given**：実装が完了している
- **When**：`jenkins/README.md`と`jenkins/CONTRIBUTION.md`を確認する
- **Then**：
  - [ ] Script Approval設定の手順が記載されている
  - [ ] トラブルシューティング情報が追加されている
  - [ ] 新しいコマンド追加方法が説明されている

---

## 7. スコープ外

### 7.1 明確にスコープ外とする事項

以下の項目は本要件の対象外とし、将来的な検討課題とする：

1. **Jenkins Script Approvalの完全無効化**
   - 理由：セキュリティリスクが高すぎる
   - 代替案：ホワイトリスト方式で必要なコマンドのみ承認

2. **Dockerコンテナのroot実行**
   - 理由：セキュリティベストプラクティスに反する
   - 代替案：非rootユーザーで必要な権限のみ付与

3. **pytest以外のテストフレームワーク（unittest、nose等）の対応**
   - 理由：現在のプロジェクトではpytestのみ使用
   - 将来対応：必要に応じて個別に承認追加

4. **Windows環境でのJenkins実行**
   - 理由：プロジェクトはLinux環境（Amazon Linux 2023）を前提
   - 将来対応：別のIssueで検討

5. **Jenkins Plugin自体の開発・カスタマイズ**
   - 理由：既存のScript Security Pluginで対応可能
   - 将来対応：プラグインの機能拡張が必要になった場合のみ検討

### 7.2 将来的な拡張候補

以下の項目は将来的に検討する価値がある：

1. **動的Script Approval管理**：
   - AI AgentがScript Approval設定を自動的に提案・適用
   - Jenkins APIを使用した承認リストの自動更新

2. **承認ポリシーのテンプレート化**：
   - Python開発用、Node.js開発用など、プロジェクトタイプ別のテンプレート
   - 新規プロジェクト作成時に適切なポリシーを自動選択

3. **Script Approvalのログ監視・アラート**：
   - 承認待ちコマンドをSlack/メールで通知
   - 承認履歴の可視化ダッシュボード

4. **セキュリティスキャンの自動化**：
   - 承認リストに追加するコマンドの自動セキュリティスキャン
   - 危険なメソッドシグネチャのブラックリストチェック

---

## 8. 補足情報

### 8.1 参考Issue・ドキュメント

- **Issue #310**：AI Workflow実行時のpytest承認問題の初期報告
  - [コメント](https://github.com/tielec/infrastructure-as-code/issues/310#issuecomment-3388025496)：Phase 5でのブロッカー詳細
- **CLAUDE.md**：プロジェクト全体のコーディング規約・開発ガイドライン
- **jenkins/CONTRIBUTION.md**：Jenkins開発の詳細ガイド（パラメータ定義ルール、DSL規約等）
- **DOCKER_AUTH_SETUP.md**：Docker環境でのClaude Agent SDK認証設定

### 8.2 関連する技術資料

- [Jenkins Script Security Plugin](https://plugins.jenkins.io/script-security/)
- [Jenkins Configuration as Code (JCasC)](https://plugins.jenkins.io/configuration-as-code/)
- [Docker Security Best Practices](https://docs.docker.com/engine/security/)
- [pytest Documentation](https://docs.pytest.org/)

### 8.3 既知の問題・リスク

| 項目 | 説明 | 対策 |
|------|------|------|
| **リスク-1** | Script Approval設定ミスによるセキュリティホール | 承認リストは最小限に限定、レビュー必須 |
| **リスク-2** | JCasC設定の構文エラーによるJenkins起動失敗 | YAML検証ツールの使用、ステージング環境での事前検証 |
| **リスク-3** | Groovyスクリプトの実行エラー | try-catchブロックでエラーハンドリング、詳細ログ出力 |
| **リスク-4** | Docker環境固有の権限問題 | Dockerfileの権限設定を段階的にテスト |

### 8.4 成功指標（KPI）

| 指標 | 目標値 | 測定方法 |
|------|--------|----------|
| **AI Workflow自動化率** | 100%（Phase 1-7すべて人間介入なし） | Phase 5実行時に`HUMAN_INTERVENTION_REQUIRED.md`が生成されないこと |
| **pytest実行時間短縮** | 手動承認待ち時間ゼロ（即座に実行） | Phase 5実行ログのタイムスタンプ分析 |
| **設定変更作業時間** | 新規コマンド承認追加が5分以内 | JCasC YAML編集〜適用までの時間計測 |
| **セキュリティインシデント** | ゼロ件 | 運用開始後1ヶ月間の監視 |

---

## 9. 品質ゲート確認

本要件定義書が満たすべき品質ゲート（Phase 1必須要件）：

- [x] **機能要件が明確に記載されている**：FR-1〜FR-5で明確に定義
- [x] **受け入れ基準が定義されている**：AC-1〜AC-6でGiven-When-Then形式で記述
- [x] **スコープが明確である**：スコープ外（7章）で対象外を明示
- [x] **論理的な矛盾がない**：各セクション間で整合性を確認済み

---

## 10. 次フェーズへの引き継ぎ事項

Phase 2（設計）で検討すべき事項：

1. **Script Approval設定の具体的なメソッドシグネチャリスト**：
   - pytest実行に必要な正確なメソッド名の特定
   - Jenkinsログからの未承認メソッド抽出方法

2. **JCasC YAML構造の設計**：
   - 既存JCasC設定への統合方法
   - Script Approval設定の記述フォーマット

3. **Groovy初期化スクリプトの設計**：
   - `ScriptApproval` APIの使用方法
   - エラーハンドリング・ログ出力の詳細設計

4. **テスト戦略**：
   - 統合テストの具体的なテストケース設計
   - モック化の必要性検討（Jenkins API）

5. **ドキュメント更新計画**：
   - `jenkins/README.md`への追記内容
   - `jenkins/CONTRIBUTION.md`のトラブルシューティング拡充

---

**レビュー日時**: 2025-10-10
**レビュアー**: AI Workflow Orchestrator
**承認状態**: クリティカルシンキングレビュー待ち
