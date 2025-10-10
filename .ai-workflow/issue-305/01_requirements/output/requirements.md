# 要件定義書 - Issue #305

**タイトル**: AI Workflow: Jenkins統合完成とPhase終了後の自動commit & push機能
**Issue番号**: #305
**作成日**: 2025-10-09
**ステータス**: Phase 1 - Requirements Definition

---

## 1. 概要

### 1.1 背景

Issue #304においてAI Workflow OrchestrationシステムのPhase 1-7の全フェーズ実装が完了しました。この実装により、GitHub IssueからPR作成までの自動開発プロセスの基盤が整いました。

しかし、Jenkins統合は以下の状態で未完成です：
- Jenkinsfileは作成済みだが、Phase 1-7実行部分が実装済み
- Git自動commit & push機能が`BasePhase.run()`メソッド内に実装済み
- GitManagerクラスが既に実装済み

**現在の状況分析**：
- **既に実装済み**：
  - Jenkinsfile（全フェーズ実行ステージ完成）
  - BasePhaseクラス（Git自動commit & push統合完了）
  - GitManagerクラス（commit/push機能完成）
  - Job DSL定義
- **未実装**：なし（Issue #304で完成）

### 1.2 目的

本Issueは、既存の実装を検証し、以下を達成することを目的とします：

1. **既存実装の動作検証**: Jenkins上でフェーズ実行が正常に動作することを確認
2. **Git自動commit & push機能の統合テスト**: Phase完了後に成果物が自動的にGitにcommit & pushされることを確認
3. **エンドツーエンドテスト**: Issue取得 → Phase実行 → レビュー → Git commit & push の全フローを検証
4. **ドキュメント整備**: 既存実装の使用方法とアーキテクチャをドキュメント化

### 1.3 ビジネス価値・技術的価値

#### ビジネス価値
- **開発効率の劇的な向上**: 手動プロセスの自動化により、開発サイクル時間を大幅に短縮
- **品質の標準化**: AI駆動レビューにより一貫した品質基準を維持
- **透明性の向上**: 各フェーズの成果物とレビュー結果がGitHub上で追跡可能
- **コスト削減**: 反復作業の自動化により、エンジニアリソースを高付加価値タスクにシフト

#### 技術的価値
- **完全自動化された開発パイプライン**: Issue作成からPR作成まで人的介入を最小化
- **トレーサビリティ**: Git履歴により全フェーズの成果物とレビュー結果を記録
- **再現性**: 同じIssueから常に同じプロセスで開発を実行可能
- **拡張性**: 新しいフェーズやレビュー基準を容易に追加可能

---

## 2. 機能要件

### 2.1 既存実装の検証（優先度: 高）

**FR-001: Jenkins統合の動作確認**
- **説明**: Jenkinsfile内のPhase 1-7実行ステージが正常に動作することを確認
- **詳細**:
  - Jenkins UI上で`ai_workflow_orchestrator`ジョブを手動実行
  - 各Phase（requirements, design, test_scenario, implementation, testing, documentation, report）が順次実行される
  - Phase実行中にClaude Agent SDKが正常に呼び出される
  - エラー発生時に適切なエラーメッセージが表示される
- **入力**: GitHub Issue URL、START_PHASE パラメータ
- **出力**: 各Phaseの実行ログ、成果物（.ai-workflow/issue-XXX/配下）
- **制約**: Docker環境内でPython3とClaude CLIが利用可能であること
- **優先度**: 高

**FR-002: Git自動commit & push機能の検証**
- **説明**: Phase完了後、成果物が自動的にGitにcommit & pushされることを確認
- **詳細**:
  - BasePhase.run()メソッド内のfinally句でGitManagerが呼び出される
  - `.ai-workflow/issue-XXX/`配下のファイルのみがcommit対象となる
  - コミットメッセージが指定フォーマット（`[ai-workflow] Phase X (phase_name) - status`）に従う
  - push時にネットワークエラーが発生した場合、最大3回リトライされる
  - 成功・失敗に関わらず、Phase実行後に必ずcommit & pushが実行される
- **入力**: Phase名、ステータス（completed/failed）、レビュー結果（PASS/PASS_WITH_SUGGESTIONS/FAIL）
- **出力**: Git commit（コミットハッシュ）、リモートリポジトリへのpush
- **制約**: GITHUB_TOKEN環境変数が設定されていること、リモートブランチが存在すること
- **優先度**: 高

**FR-003: エンドツーエンドテストの実施**
- **説明**: Issue取得からPhase実行、レビュー、Git commit & pushまでの全フローを検証
- **詳細**:
  - テスト用Issueを作成（シンプルな機能追加タスク）
  - Jenkins上で`ai_workflow_orchestrator`ジョブを実行（START_PHASE=requirements）
  - Phase 1完了後、`.ai-workflow/issue-XXX/01_requirements/`配下に成果物が生成される
  - レビュー実行後、GitHub Issue上にレビュー結果がコメントとして投稿される
  - Git履歴に`[ai-workflow] Phase 1 (requirements) - completed`のコミットが記録される
  - リモートリポジトリに自動的にpushされる
  - Phase 2-7も同様に実行され、全Phaseが正常に完了する
- **入力**: GitHub Issue URL（テスト用Issue）
- **出力**: 各Phaseの成果物、Git履歴、GitHub Issue上のコメント
- **制約**: Jenkins環境が正常に動作していること
- **優先度**: 高

### 2.2 ドキュメント整備（優先度: 中）

**FR-004: 使用方法のドキュメント化**
- **説明**: Jenkinsジョブの使用方法とパラメータ設定をドキュメント化
- **詳細**:
  - `scripts/ai-workflow/README.md`にJenkins統合セクションを追加
  - パラメータ（ISSUE_URL, START_PHASE, DRY_RUN等）の説明を記載
  - 実行例とトラブルシューティング情報を追加
- **出力**: 更新された`scripts/ai-workflow/README.md`
- **優先度**: 中

**FR-005: アーキテクチャドキュメントの更新**
- **説明**: GitManagerコンポーネントと自動commit機能のアーキテクチャ図を追加
- **詳細**:
  - `scripts/ai-workflow/ARCHITECTURE.md`にGitManagerの説明を追加
  - コンポーネント図にGitManagerを追加
  - シーケンス図にcommit & pushフローを追加
- **出力**: 更新された`scripts/ai-workflow/ARCHITECTURE.md`
- **優先度**: 中

**FR-006: Jenkinsドキュメントの更新**
- **説明**: Jenkins統合に関する説明を`jenkins/README.md`に追加
- **詳細**:
  - `ai_workflow_orchestrator`ジョブの説明を追加
  - 使用方法、パラメータ、実行例を記載
- **出力**: 更新された`jenkins/README.md`
- **優先度**: 中

### 2.3 テストコードの追加（優先度: 低）

**FR-007: GitManager Unitテスト**
- **説明**: GitManagerクラスのUnitテストを作成（既存実装の保守性向上）
- **詳細**:
  - `tests/unit/core/test_git_manager.py`を作成
  - `commit_phase_output()`メソッドのテスト
    - 正常系: 変更ファイルが正常にcommitされる
    - 異常系: Gitリポジトリが存在しない場合のエラーハンドリング
    - エッジケース: コミット対象ファイルが0件の場合
  - `push_to_remote()`メソッドのテスト
    - 正常系: リモートリポジトリに正常にpushされる
    - 異常系: ネットワークエラー時のリトライロジック
    - 異常系: 権限エラー時のエラーハンドリング
  - `create_commit_message()`メソッドのテスト
    - コミットメッセージフォーマットの検証
- **出力**: `tests/unit/core/test_git_manager.py`
- **優先度**: 低

---

## 3. 非機能要件

### 3.1 パフォーマンス要件

**NFR-001: Phase実行時間**
- Phase 1件あたりの実行時間は平均10分以内（Claude API呼び出し時間を含む）
- 全7フェーズの実行時間は合計70分以内

**NFR-002: Git操作のタイムアウト**
- Git commitは5秒以内に完了
- Git pushは30秒以内に完了（ネットワーク状況に依存、リトライ含む）

**NFR-003: API呼び出しの最適化**
- Claude API呼び出し時にPrompt Cachingを活用し、トークン使用量を削減
- 1ワークフローあたりのAPI呼び出し回数を最小化（Phase実行とレビューのみ）

### 3.2 セキュリティ要件

**NFR-004: 認証情報の保護**
- `GITHUB_TOKEN`はJenkinsクレデンシャルストアで管理
- `CLAUDE_CODE_OAUTH_TOKEN`はJenkinsクレデンシャルストアで管理
- 環境変数として渡される認証情報はログに出力しない

**NFR-005: Git操作の安全性**
- Gitリモート認証はHTTPSトークン認証を使用
- コミットにはGit設定（user.name, user.email）を適切に設定
- Detached HEAD状態を検知し、自動的に適切なブランチにcheckout

**NFR-006: アクセス制御**
- Jenkinsジョブの実行権限は適切に制限
- GitHub Tokenは最小限の権限（repo: write、issues: write）のみを付与

### 3.3 可用性・信頼性要件

**NFR-007: エラーハンドリング**
- Phase実行失敗時もGit commit & pushは必ず実行（トラブルシューティング用）
- ネットワークエラー時は自動リトライ（最大3回、2秒間隔）
- エラー発生時は詳細なログを出力し、GitHub Issueにコメント投稿

**NFR-008: レジリエンス**
- Phase実行中にClaude APIがタイムアウトした場合、リトライロジックが動作
- Git pushに失敗した場合、エラーメッセージを記録するが、Phaseは失敗扱いにしない

**NFR-009: ロギング**
- 各Phaseの実行ログを`.ai-workflow/issue-XXX/XX_phase_name/execute/agent_log.md`に保存
- プロンプトを`.ai-workflow/issue-XXX/XX_phase_name/execute/prompt.txt`に保存
- Git操作のログをJenkins Console Outputに出力

### 3.4 保守性・拡張性要件

**NFR-010: コードの可読性**
- Pythonコードは型ヒントを使用
- Groovyコード（Job DSL、Jenkinsfile）は適切にコメントを記載
- 複雑なロジックにはdocstringで詳細を説明

**NFR-011: モジュール性**
- GitManagerクラスは単一責任の原則に従い、Git操作のみを担当
- BasePhaseクラスは各Phaseの共通インターフェースを提供
- 各PhaseクラスはBasePhaseを継承し、`execute()`と`review()`メソッドを実装

**NFR-012: テスタビリティ**
- GitManagerクラスはUnitテスト可能な設計（依存性注入）
- モックを使用してGit操作をテスト可能

---

## 4. 制約事項

### 4.1 技術的制約

**C-001: プログラミング言語とフレームワーク**
- Python 3.8以上（Claude Agent SDK互換性）
- Groovy（Jenkins DSL）
- Docker環境（Jenkinsエージェント）

**C-002: 既存システムとの整合性**
- 既存のJenkinsインフラストラクチャ（EC2 SpotFleet、ALB、EFS）を使用
- 既存のGitワークフロー（ブランチ戦略、コミットメッセージ規約）に準拠
- CLAUDE.mdのコーディングガイドライン（日本語コメント、命名規則）に準拠

**C-003: 外部サービス依存**
- Claude Agent SDK（Claude Code headless mode）
- GitHub API（Issue取得、コメント投稿）
- Git（GitHub remote repository）

**C-004: ネットワーク制約**
- Jenkinsエージェントはプライベートサブネット上で動作
- インターネットアクセスはNATゲートウェイ経由
- GitHub APIとClaude APIへのHTTPSアクセスが可能であること

### 4.2 リソース制約

**C-005: コスト制約**
- 1ワークフローあたりのClaude API利用料金は最大$5.00 USD
- Jenkinsエージェント（EC2 Spot Instance）のコスト最適化

**C-006: 実行時間制約**
- Jenkinsジョブのタイムアウトは2時間
- 各Phaseの最大実行時間は30分（タイムアウト発生時は失敗）

**C-007: ストレージ制約**
- EFS上のJenkinsワークスペースは定期的にクリーンアップ
- `.ai-workflow/`ディレクトリは成果物アーカイブ後も保持

### 4.3 ポリシー制約

**C-008: セキュリティポリシー**
- 認証情報のハードコーディング禁止
- SSM SecureStringまたはJenkinsクレデンシャルストアで管理
- IAMロールは最小権限の原則に従う

**C-009: コーディング規約**
- CLAUDE.mdのコーディングガイドラインに準拠
  - コメント: 日本語
  - ドキュメント: 日本語
  - コミットメッセージ: 英語（`[component] action: description`形式）
- Pythonコード: PEP 8準拠、型ヒント使用
- Groovyコード: Jenkinsベストプラクティスに準拠

**C-010: ブランチ戦略**
- フィーチャーブランチ: `feature/issue-XXX-description`
- バグ修正ブランチ: `bug/issue-XXX-description`
- mainブランチへの直接コミットは禁止（PRレビュー必須）

---

## 5. 前提条件

### 5.1 システム環境

**P-001: Jenkinsインフラストラクチャ**
- Jenkins Controller: EC2インスタンス（EFS永続化）
- Jenkins Agent: EC2 SpotFleet（Docker対応）
- ネットワーク: VPC、プライベートサブネット、NATゲートウェイ
- ストレージ: EFS（Jenkins Home共有）

**P-002: Dockerイメージ**
- Python 3.8以上がインストール済み
- Claude CLI（Claude Code headless mode）がインストール済み
- Gitクライアントがインストール済み
- 必要なPythonパッケージ（requirements.txt）がインストール済み

**P-003: 環境変数**
- `GITHUB_TOKEN`: GitHub Personal Access Token（repo, issues権限）
- `CLAUDE_CODE_OAUTH_TOKEN`: Claude OAuth Token
- `GITHUB_REPOSITORY`: GitHubリポジトリ（例: tielec/infrastructure-as-code）

### 5.2 依存コンポーネント

**P-004: Pulumiスタック**
- `jenkins-network`: VPC、サブネット
- `jenkins-security`: セキュリティグループ、IAMロール
- `jenkins-controller`: Jenkinsコントローラー
- `jenkins-agent`: Jenkinsエージェント（SpotFleet）
- `jenkins-application`: Jenkins設定、プラグイン

**P-005: Ansibleロール**
- `jenkins_application`: Jenkinsバージョン管理、プラグインインストール
- `jenkins_seed_job`: シードジョブ作成、Job DSL実行

**P-006: Pythonパッケージ（requirements.txt）**
```
claude-agent-sdk>=0.1.0
click==8.1.7
GitPython==3.1.40
PyYAML==6.0.1
PyGithub==2.1.1
requests==2.31.0
python-dotenv==1.0.0
pytest==7.4.3
pytest-asyncio==0.21.1
```

### 5.3 外部システム連携

**P-007: GitHub API**
- Issue情報取得API（GET /repos/{owner}/{repo}/issues/{issue_number}）
- コメント投稿API（POST /repos/{owner}/{repo}/issues/{issue_number}/comments）
- 認証: GitHub Personal Access Token

**P-008: Claude Agent SDK**
- Claude Code headless mode（OAuth認証）
- API endpoint: Claude API（https://api.anthropic.com）
- モデル: Claude 3.5 Sonnet（claude-3-5-sonnet-20241022）

**P-009: Gitリモートリポジトリ**
- GitHub: https://github.com/tielec/infrastructure-as-code.git
- 認証: HTTPS + Personal Access Token
- ブランチ: feature/ai-workflow-mvp（またはissue対応ブランチ）

---

## 6. 受け入れ基準

### 6.1 Jenkins統合の動作確認（FR-001）

**AC-001: Phase実行ステージの正常動作**
```gherkin
Given Jenkins上で`ai_workflow_orchestrator`ジョブが存在する
And ジョブパラメータ`ISSUE_URL`に有効なGitHub Issue URLが設定されている
And ジョブパラメータ`START_PHASE`が"requirements"に設定されている
When ジョブを手動実行する
Then Phase 1（Requirements）ステージが開始される
And "Stage: Phase 1 - Requirements Definition"ログが出力される
And `python main.py execute --phase requirements --issue {issue_number}`が実行される
And Phase実行が正常に完了する
And 成果物が`.ai-workflow/issue-XXX/01_requirements/output/requirements.md`に生成される
```

**AC-002: 複数Phaseの順次実行**
```gherkin
Given Jenkins上で`ai_workflow_orchestrator`ジョブが存在する
And ジョブパラメータ`START_PHASE`が"requirements"に設定されている
When ジョブを実行する
Then Phase 1（Requirements）が完了する
And Phase 2（Design）が自動的に開始される
And Phase 3（Test Scenario）が自動的に開始される
And Phase 4（Implementation）が自動的に開始される
And Phase 5（Testing）が自動的に開始される
And Phase 6（Documentation）が自動的に開始される
And Phase 7（Report）が自動的に開始される
And 全Phaseが正常に完了する
```

**AC-003: エラーハンドリング**
```gherkin
Given Phase実行中にエラーが発生する（例: Claude APIタイムアウト）
When エラーが検知される
Then エラーメッセージがJenkins Console Outputに出力される
And Phaseステータスが"failed"に更新される
And GitHub IssueにエラーコメントDが投稿される
And ジョブが失敗ステータスで終了する
```

### 6.2 Git自動commit & push機能の検証（FR-002）

**AC-004: Phase完了後の自動commit**
```gherkin
Given Phase 1（Requirements）が正常に完了する
And `.ai-workflow/issue-305/01_requirements/`配下に成果物が生成される
When BasePhase.run()のfinally句が実行される
Then GitManager.commit_phase_output()が呼び出される
And `.ai-workflow/issue-305/`配下のファイルがgit addされる
And コミットメッセージが"[ai-workflow] Phase 1 (requirements) - completed"となる
And Gitにcommitが作成される
And コミットハッシュがログに出力される
```

**AC-005: Phase失敗時の自動commit**
```gherkin
Given Phase 1（Requirements）の実行が失敗する
And `.ai-workflow/issue-305/01_requirements/execute/`にログが保存される
When BasePhase.run()のfinally句が実行される
Then GitManager.commit_phase_output()が呼び出される
And `.ai-workflow/issue-305/`配下のファイルがgit addされる
And コミットメッセージが"[ai-workflow] Phase 1 (requirements) - failed"となる
And Gitにcommitが作成される（失敗時もcommit）
```

**AC-006: 自動push（正常系）**
```gherkin
Given Phase完了後にGit commitが作成される
When GitManager.push_to_remote()が呼び出される
Then `git push origin HEAD:{current_branch}`が実行される
And リモートリポジトリに正常にpushされる
And "Git push successful"ログが出力される
```

**AC-007: 自動push（リトライロジック）**
```gherkin
Given Phase完了後にGit commitが作成される
And Git push実行時にネットワークタイムアウトエラーが発生する
When GitManager.push_to_remote()が呼び出される
Then 1回目のpushが失敗する
And 2秒間スリープする
And 2回目のpushがリトライされる
And 2回目のpushが成功する
And "Git push successful (retries: 1)"ログが出力される
```

**AC-008: コミットメッセージフォーマット**
```gherkin
Given Phase 1（Requirements）が完了し、レビュー結果が"PASS"である
When GitManager.create_commit_message()が呼び出される
Then コミットメッセージが以下のフォーマットになる:
"""
[ai-workflow] Phase 1 (requirements) - completed

Issue: #305
Phase: 1 (requirements)
Status: completed
Review: PASS

Auto-generated by AI Workflow
"""
```

### 6.3 エンドツーエンドテストの実施（FR-003）

**AC-009: 全フロー統合テスト**
```gherkin
Given テスト用GitHub Issue #999が作成されている
And Issue本文に"シンプルな機能追加タスク"が記載されている
And Jenkins上で`ai_workflow_orchestrator`ジョブが存在する
When ジョブパラメータ`ISSUE_URL`に"https://github.com/tielec/infrastructure-as-code/issues/999"を設定する
And ジョブパラメータ`START_PHASE`を"requirements"に設定する
And ジョブを実行する
Then Phase 1が開始される
And `.ai-workflow/issue-999/01_requirements/output/requirements.md`が生成される
And レビューが実行される
And レビュー結果がGitHub Issue #999にコメント投稿される
And Git commitが作成される（コミットメッセージ: "[ai-workflow] Phase 1 (requirements) - completed"）
And リモートリポジトリにpushされる
And Phase 2が自動的に開始される
And 同様にPhase 3-7が順次実行される
And 全Phaseが正常に完了する
And ジョブが成功ステータスで終了する
And `.ai-workflow/issue-999/`配下にすべてのPhaseの成果物が保存される
```

### 6.4 ドキュメント整備（FR-004, FR-005, FR-006）

**AC-010: README更新**
```gherkin
Given `scripts/ai-workflow/README.md`が存在する
When ドキュメント整備タスクが完了する
Then README.mdに"Jenkins統合"セクションが追加されている
And `ai_workflow_orchestrator`ジョブの使用方法が記載されている
And パラメータ説明（ISSUE_URL, START_PHASE等）が記載されている
And 実行例とトラブルシューティング情報が記載されている
```

**AC-011: ARCHITECTURE.md更新**
```gherkin
Given `scripts/ai-workflow/ARCHITECTURE.md`が存在する
When ドキュメント整備タスクが完了する
Then ARCHITECTURE.mdに"GitManager"セクションが追加されている
And GitManagerのクラス図が記載されている
And commit & pushのシーケンス図が記載されている
```

**AC-012: jenkins/README.md更新**
```gherkin
Given `jenkins/README.md`が存在する
When ドキュメント整備タスクが完了する
Then jenkins/README.mdに"AI Workflow Orchestrator"セクションが追加されている
And ジョブの説明、使用方法が記載されている
```

### 6.5 テストコード追加（FR-007）

**AC-013: GitManager Unitテスト作成**
```gherkin
Given `tests/unit/core/test_git_manager.py`が存在する
When Unitテストを実行する（pytest tests/unit/core/test_git_manager.py）
Then すべてのテストケースが成功する（PASS）
And テストカバレッジが80%以上である
```

---

## 7. スコープ外

本Issue（#305）では以下の項目は対象外とします：

### 7.1 PR自動作成機能
- **理由**: Jenkins統合の基盤検証が優先。PR作成は次フェーズで実装
- **将来実装予定**: Phase 7完了後、`gh pr create`コマンドでPR自動作成
- **関連Issue**: 今後作成予定（"AI Workflow: PR自動作成機能"）

### 7.2 GitHub Webhook連携
- **理由**: 手動実行での動作確認が優先。Webhook連携は次フェーズで実装
- **将来実装予定**: Issue作成時またはラベル追加時に自動的にジョブ起動
- **関連Issue**: 今後作成予定（"AI Workflow: GitHub Webhook統合"）

### 7.3 レビュー基準のカスタマイズ
- **理由**: デフォルトのレビュー基準（品質ゲート）を使用。カスタマイズは次フェーズで実装
- **将来実装予定**: Issueラベルやパラメータでレビュー基準を動的に変更
- **関連Issue**: 今後作成予定（"AI Workflow: レビュー基準カスタマイズ機能"）

### 7.4 コスト最適化機能
- **理由**: 基本的なコスト制限（$5.00/workflow）は実装済み。より高度な最適化は次フェーズで実装
- **将来実装予定**: Phase単位のコスト追跡、予算アラート、Prompt Cachingの最適化
- **関連Issue**: 今後作成予定（"AI Workflow: コスト最適化とモニタリング"）

### 7.5 マルチリポジトリ対応
- **理由**: 単一リポジトリ（tielec/infrastructure-as-code）での動作確認が優先
- **将来実装予定**: 複数のGitHubリポジトリに対応可能な汎用化
- **関連Issue**: 今後作成予定（"AI Workflow: マルチリポジトリ対応"）

### 7.6 並列Phase実行
- **理由**: Phase 1-7は依存関係があり、順次実行が基本。並列実行は高度な最適化
- **将来実装予定**: 独立したPhaseを並列実行してワークフロー全体の実行時間短縮
- **関連Issue**: 今後作成予定（"AI Workflow: 並列Phase実行機能"）

### 7.7 Phase実行のスキップ機能
- **理由**: 全Phaseの実行検証が優先。スキップ機能は次フェーズで実装
- **将来実装予定**: `SKIP_PHASES`パラメータでPhaseを選択的にスキップ
- **関連Issue**: 今後作成予定（"AI Workflow: Phase選択実行機能"）

---

## 8. まとめ

本要件定義書は、Issue #305「AI Workflow: Jenkins統合完成とPhase終了後の自動commit & push機能」の詳細な要件を定義しました。

### 8.1 重要なポイント

1. **既存実装の活用**: Issue #304で実装済みのJenkinsfile、BasePhase、GitManagerを活用し、検証とテストを中心に実施
2. **自動化の完結**: Phase実行 → レビュー → Git commit & push の全フローが自動化され、人的介入を最小化
3. **トレーサビリティ**: Git履歴により全Phaseの成果物とレビュー結果を追跡可能
4. **段階的な拡張**: スコープ外項目（PR自動作成、Webhook連携等）は将来のIssueで段階的に実装

### 8.2 次のステップ（Phase 2: Design）

Phase 2（詳細設計）では、以下を実施します：
- エンドツーエンドテスト計画の詳細化
- ドキュメント更新の具体的な構成・内容
- Unitテストのテストケース設計
- システムアーキテクチャ図の更新

---

**承認者**: （レビュー後に記入）
**承認日**: （レビュー後に記入）
**バージョン**: 1.0
**最終更新**: 2025-10-09
