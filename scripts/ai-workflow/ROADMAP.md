# AI駆動開発自動化ワークフロー 開発ロードマップ

**バージョン**: 1.0.0
**最終更新**: 2025-10-07

---

## 現在の状況（v1.2.0）

**完了した機能**:
- ✅ ワークフロー基盤（main.py, workflow_state.py）
- ✅ メタデータ管理（metadata.json CRUD）
- ✅ BDDテスト基盤（1シナリオ）
- ✅ 設定管理（config.yaml）
- ✅ ドキュメント（README, ARCHITECTURE, TROUBLESHOOTING）
- ✅ Claude Agent SDK統合（Docker環境）
- ✅ GitHub API統合（PyGithub）
- ✅ Phase 1: 要件定義フェーズ（requirements.py）
- ✅ Phase 2: 詳細設計フェーズ（design.py）
- ✅ 設計判断機能（実装戦略・テスト戦略・テストコード戦略）
- ✅ Phase 2 E2Eテスト（test_phase2.py）

---

## 開発フェーズ

### Phase 1: MVP基盤（完了）✅

**目標**: ワークフロー初期化とメタデータ管理の実装

**完了項目**:
- ✅ CLIフレームワーク（Click）
- ✅ WorkflowState クラス
- ✅ metadata.json 管理
- ✅ PhaseStatus Enum
- ✅ BDDテスト1シナリオ
- ✅ ドキュメント

**成果物**:
- scripts/ai-workflow/main.py
- scripts/ai-workflow/core/workflow_state.py
- scripts/ai-workflow/tests/features/workflow.feature
- scripts/ai-workflow/tests/features/steps/workflow_steps.py
- README.md, ARCHITECTURE.md, TROUBLESHOOTING.md

---

### Phase 2: Claude API統合とPhase 1実装（完了）✅

**目標**: 要件定義フェーズの自動実行を実現

**完了日**: 2025-10-08

**実装項目**:

#### 2.1 Claude Agent SDK統合
- [x] `core/claude_agent_client.py` 実装
  - Anthropic Python SDK統合
  - messages.create() メソッド
  - コスト追跡（input/output tokens）
  - 指数バックオフリトライ（1秒, 2秒, 4秒）
  - タイムアウト処理（120秒）

**実装例**:
```python
class ClaudeClient:
    def chat(self, messages: List[Dict], max_tokens: int = 4096) -> str:
        """Claude APIでテキスト生成"""
        for attempt in range(3):
            try:
                response = self.client.messages.create(
                    model="claude-sonnet-4-5-20250929",
                    max_tokens=max_tokens,
                    messages=messages
                )
                self.track_cost(response.usage)
                return response.content[0].text
            except Exception as e:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                else:
                    raise
```

#### 2.2 GitHub API統合
- [x] `core/github_client.py` 実装
  - PyGithub使用
  - Issue取得（タイトル、本文、コメント）
  - コメント投稿

#### 2.3 プロンプト管理
- [x] `prompts/requirements/execute.txt` 作成
  - 要件定義生成プロンプト

- [x] `prompts/requirements/review.txt` 作成
  - 要件定義レビュープロンプト

- [x] `prompts/requirements/revise.txt` 作成
  - 要件定義修正プロンプト

#### 2.4 Phase 1実装
- [x] `phases/base_phase.py` 基底クラス
  - execute() 抽象メソッド
  - review() 抽象メソッド
  - revise() 抽象メソッド

- [x] `phases/requirements.py` 要件定義フェーズ
  - GitHub Issueからコンテンツ取得
  - Claude Agent SDKで要件定義生成
  - requirements.md 保存

#### 2.5 E2Eテスト
- [x] Phase 1 E2Eテスト（test_phase1.py）

**期待される成果物**:
```
.ai-workflow/issue-304/
├── metadata.json
└── 01_requirements/
    ├── output/requirements.md
    ├── execute/
    ├── review/
    └── revise/
```

**マイルストーン条件**:
- ✅ `python main.py execute --phase requirements --issue 304` が動作
- ✅ Claude Agent SDKで要件定義が自動生成される
- ✅ AIレビューが実行される
- ✅ metadata.jsonに実行状況が記録される

---

### Phase 3: Phase 2実装（完了）✅

**目標**: 詳細設計フェーズの自動生成

**完了日**: 2025-10-09

**実装項目**:

#### 3.1 Phase 2実装（詳細設計）
- [x] `phases/design.py` 実装
  - requirements.md を読み込み
  - Claude Agent SDKで詳細設計生成
  - 設計判断の記録（implementation_strategy, test_strategy, test_code_strategy）
  - design.md 保存

- [x] `prompts/design/execute.txt` 作成
- [x] `prompts/design/review.txt` 作成
- [x] `prompts/design/revise.txt` 作成

#### 3.2 E2Eテスト
- [x] Phase 2 E2Eテスト（test_phase2.py）

**期待される成果物**:
```
.ai-workflow/issue-304/
├── metadata.json
└── 02_design/
    ├── output/design.md
    ├── execute/
    ├── review/
    └── revise/
```

**マイルストーン条件**:
- ✅ `python main.py execute --phase design --issue 304` が動作
- ✅ Claude Agent SDKで詳細設計が自動生成される
- ✅ 設計判断がmetadata.jsonに記録される（implementation_strategy, test_strategy, test_code_strategy）
- ✅ AIレビューが実行される

---

### Phase 4: Phase 3実装とGit操作（次のマイルストーン）

**目標**: テストシナリオの自動生成とGitコミット

**予定期間**: 2-3週間

**実装項目**:

#### 4.1 Git操作
- [ ] `core/git_operations.py` 実装
  - ブランチ作成（feature/issue-{number}）
  - コミット作成
  - ブランチプッシュ
  - GitPython使用

#### 4.2 Phase 3実装（テストシナリオ）
- [ ] `phases/test_scenario.py` 実装
  - requirements.md, design.md を読み込み
  - テスト戦略に基づいたテストシナリオ生成
  - test-scenario.md 保存

- [ ] `prompts/test_scenario/execute.txt` 作成
- [ ] `prompts/test_scenario/review.txt` 作成
- [ ] `prompts/test_scenario/revise.txt` 作成

#### 4.3 E2Eテスト
- [ ] Phase 3 E2Eテスト（test_phase3.py）

**マイルストーン条件**:
- ✅ Phase 1-3が連続実行される
- ✅ Gitコミットが自動作成される
- ✅ テスト戦略に基づいたテストシナリオが生成される

---

### Phase 5: Phase 4-6実装（実装・テスト・ドキュメント）

**目標**: 完全なワークフロー実現

**予定期間**: 3-4週間

**実装項目**:

#### 4.1 コードベース分析
- [ ] `core/codebase_analyzer.py` 実装
  - Grep/Globでファイル検索
  - 関連ファイルの抽出（最大20ファイル）
  - トークン数制限（50,000トークン）

#### 4.2 Phase 4実装（実装フェーズ）
- [ ] `phases/implementation.py` 実装
  - コードベース分析
  - Claude APIによるコード生成
  - ファイル書き込み（CREATE/EXTEND/REFACTOR）
  - 04-implementation.md 保存

- [ ] `prompts/implementation/execute.txt` 作成
  - 実装戦略別のプロンプト

#### 4.3 Phase 5実装（テスト実行）
- [ ] `phases/testing.py` 実装
  - pytest/behave実行
  - テスト結果の解析
  - 失敗時のリトライ（最大3回）
  - 05-testing.md 保存

#### 4.4 Phase 6実装（ドキュメント作成）
- [ ] `phases/documentation.py` 実装
  - README.md更新
  - API仕様書生成
  - 06-documentation.md 保存

**マイルストーン条件**:
- ✅ Phase 1-6が完全に自動実行される
- ✅ 実装コードが生成される
- ✅ テストが自動実行される
- ✅ ドキュメントが自動生成される

---

### Phase 6: Jenkins統合

**目標**: JenkinsからAIワークフローを実行

**予定期間**: 1-2週間

**実装項目**:

#### 5.1 Jenkinsfile作成
- [ ] `jenkins/jobs/pipeline/ai-workflow/Jenkinsfile` 作成
  - パラメータ: ISSUE_URL
  - Stage 1: ワークフロー初期化
  - Stage 2-7: Phase 1-6実行
  - Stage 8: レビュー結果判定
  - Stage 9: PR作成

**Jenkinsfile例**:
```groovy
pipeline {
    agent any

    parameters {
        string(name: 'ISSUE_URL', description: 'GitHub Issue URL')
    }

    stages {
        stage('Initialize') {
            steps {
                sh 'python scripts/ai-workflow/main.py init --issue-url ${ISSUE_URL}'
            }
        }

        stage('Phase 1: Requirements') {
            steps {
                sh 'python scripts/ai-workflow/main.py execute --phase requirements --issue ${ISSUE_NUMBER}'
                sh 'python scripts/ai-workflow/main.py review --phase requirements --issue ${ISSUE_NUMBER}'
            }
        }

        // Phase 2-6...
    }
}
```

#### 5.2 Job DSL作成
- [ ] `jenkins/jobs/dsl/ai-workflow/ai-workflow-orchestrator.groovy`
  - ジョブ定義
  - パラメータ定義

#### 5.3 PR自動作成
- [ ] GitHub API統合
  - PRタイトル、本文の自動生成
  - レビュワー自動アサイン

**マイルストーン条件**:
- ✅ JenkinsからGitHub Issueを指定して実行
- ✅ Phase 1-6が自動実行される
- ✅ PRが自動作成される
- ✅ 人間が最終レビュー＆マージ

---

### Phase 7: 高度な機能

**目標**: 実用性の向上

**予定期間**: 継続的

**実装項目**:

#### 6.1 並行実行制御
- [ ] ファイルロック実装（同一Issue内の並行実行防止）
- [ ] 複数Issue並行実行のテスト

#### 6.2 コスト最適化
- [ ] プロンプトキャッシング（Anthropic Prompt Caching API）
- [ ] トークン数の動的調整

#### 6.3 UI/UXの改善
- [ ] プログレスバー表示
- [ ] カラフルなログ出力（rich ライブラリ）
- [ ] Webダッシュボード（Flask/FastAPI）

#### 6.4 品質向上
- [ ] Unit Test追加（pytest）
- [ ] カバレッジ80%以上
- [ ] 静的解析（mypy, pylint）

#### 6.5 監視・ロギング
- [ ] CloudWatch連携
- [ ] Slack通知
- [ ] メトリクス収集（成功率、平均実行時間、コスト）

---

## マイルストーン一覧

| マイルストーン | 完了予定 | ステータス | 主要機能 |
|---------------|---------|-----------|---------|
| **MVP v1.0.0** | 2025-10-07 | ✅ 完了 | ワークフロー基盤、metadata管理 |
| **v1.1.0** | 2025-10-08 | ✅ 完了 | Phase 1（要件定義）実装 |
| **v1.2.0** | 2025-10-09 | ✅ 完了 | Phase 2（詳細設計）実装 |
| **v1.3.0** | 2025-10-末 | 🔄 計画中 | Phase 3（テストシナリオ）、Git操作 |
| **v2.0.0** | 2025-11-末 | 📅 予定 | Phase 4-6（実装・テスト・ドキュメント） |
| **v2.1.0** | 2025-12-中旬 | 📅 予定 | Jenkins統合 |
| **v3.0.0** | 2026-Q1 | 📅 予定 | 高度な機能（並行実行、UI、監視） |

---

## 技術的負債

現在の技術的負債と解消計画：

| 負債項目 | 影響度 | 解消予定 | 備考 |
|---------|-------|---------|------|
| 実行確認未実施 | 中 | v1.1.0 | Python環境セットアップ後に実施 |
| エラーハンドリング最小限 | 低 | v1.1.0 | Phase 1実装時に強化 |
| ロギング機能なし | 低 | v1.2.0 | logging モジュール追加 |
| Unit Test未実装 | 中 | v2.0.0 | pytest追加 |
| 並行実行未対応 | 低 | v3.0.0 | ファイルロック実装 |

---

## 貢献方法

### 開発参加

以下の分野で貢献を募集しています：

1. **Claude API統合**: Anthropic API経験者
2. **Jenkins統合**: Jenkinsfile、Job DSL経験者
3. **BDDテスト**: behave、Gherkin経験者
4. **ドキュメント**: 技術文書作成経験者
5. **UI/UX**: Flask/FastAPI、フロントエンド経験者

### 開発環境セットアップ

```powershell
# 1. リポジトリクローン
git clone https://github.com/tielec/infrastructure-as-code.git
cd infrastructure-as-code/scripts/ai-workflow

# 2. 仮想環境作成
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. 依存パッケージインストール
pip install -r requirements.txt
pip install -r requirements-test.txt

# 4. 開発ブランチ作成
git checkout -b feature/your-feature-name

# 5. 実装

# 6. テスト実行
behave tests/features/
pytest tests/

# 7. PR作成
```

### コーディング規約

- **Python**: PEP 8準拠、black でフォーマット
- **型ヒント**: 必須（mypy でチェック）
- **Docstring**: 日本語で記載
- **テスト**: 新機能には必ずテストを追加
- **コミットメッセージ**: `[Component] Action: 詳細` 形式

---

## 参考資料

- **要件定義書**: [ai-workflow-requirements.md](../../ai-workflow-requirements.md)
- **詳細設計書**: [ai-workflow-design.md](../../ai-workflow-design.md)
- **テストシナリオ**: [ai-workflow-test-scenario.md](../../ai-workflow-test-scenario.md)
- **アーキテクチャ**: [ARCHITECTURE.md](ARCHITECTURE.md)

---

**バージョン**: 1.2.0
**最終更新**: 2025-10-09
