# 要件定義書: Phase execute()失敗時のリトライ機能修正

## 1. 概要

### 1.1 背景

AI駆動開発自動化ワークフローにおいて、各フェーズ（requirements, design, test_scenario, implementation, testing, documentation, report）は以下の実行フローを持つ設計となっている：

1. **execute()**: フェーズの主要タスクを実行（成果物の生成）
2. **review()**: 生成された成果物の品質をレビュー
3. **revise()**: レビューで不合格の場合、フィードバックに基づいて修正

しかし、現在の実装（`scripts/ai-workflow/phases/base_phase.py:617-625`）では、**execute()が失敗した場合に即座にreturn Falseで終了し、リトライループに到達しない**という重大なバグが存在する。

このバグにより、一時的なエラー（ネットワーク障害、API制限、ファイル生成の一時的失敗など）でもワークフロー全体が停止してしまい、本来可能であったrevise()による自動回復の機会が失われている。

### 1.2 目的

execute()とrevise()を統一的なリトライループ内に統合し、execute()失敗時にもrevise()による修正とリトライが実行されるように改善する。これにより、以下のビジネス価値を提供する：

- **信頼性向上**: 一時的なエラーでも自動回復が可能になり、ワークフロー全体の成功率が向上
- **運用効率化**: 手動介入の頻度を削減し、人的リソースを解放
- **開発速度向上**: エラーハンドリングの改善により、CI/CDパイプラインの安定性向上

### 1.3 影響範囲

全てのPhaseクラスに影響：
- `scripts/ai-workflow/phases/requirements.py`
- `scripts/ai-workflow/phases/design.py`
- `scripts/ai-workflow/phases/test_scenario.py`
- `scripts/ai-workflow/phases/implementation.py`
- `scripts/ai-workflow/phases/testing.py`
- `scripts/ai-workflow/phases/documentation.py`
- `scripts/ai-workflow/phases/report.py`

ただし、修正は基底クラス（`base_phase.py`）のみで対応可能。

## 2. 機能要件

### FR-001: execute()とrevise()の統一リトライループ統合【優先度: 高】

**説明**: execute()とrevise()を同一のリトライループ内に統合し、execute()失敗時もrevise()による自動修正を可能にする。

**詳細**:
- 初回実行（attempt=1）ではexecute()を呼び出す
- 2回目以降（attempt>=2）ではrevise()を呼び出す
- 各attemptの実行結果が成功（success=True）であればループを抜ける
- 最大リトライ回数（MAX_RETRIES=3）に到達した場合はフェーズを失敗として終了

**受け入れ基準**:
- **Given**: execute()が失敗を返す（success=False）
- **When**: リトライループが実行される
- **Then**: revise()が呼び出され、最大3回までリトライが実行される

### FR-002: リトライループ内でのレビュー実行【優先度: 高】

**説明**: 2回目以降のリトライでは、revise()実行前にreview()を実行し、レビュー結果に基づいてフィードバックを生成する。

**詳細**:
- attempt>=2の場合、review()を実行
- レビュー結果がPASSまたはPASS_WITH_SUGGESTIONSの場合はループを抜けて成功
- レビュー結果がFAILの場合は、フィードバックをrevise()に渡して修正実行

**受け入れ基準**:
- **Given**: 2回目以降のリトライが実行される
- **When**: review()が実行される
- **Then**: レビュー結果がPASSの場合、revise()をスキップして成功終了する
- **And**: レビュー結果がFAILの場合、フィードバックを使用してrevise()が実行される

### FR-003: 実行試行回数の表示とロギング【優先度: 中】

**説明**: 各試行回数（attempt）をログに明示的に出力し、デバッグとトラブルシューティングを容易にする。

**詳細**:
- 各試行の開始時に`[ATTEMPT {attempt}/{MAX_RETRIES}]`形式でログ出力
- 80文字の区切り線（`=`）で視覚的に試行を区別
- フェーズ名を各試行のログに含める

**受け入れ基準**:
- **Given**: リトライループが実行される
- **When**: 各試行が開始される
- **Then**: 標準出力に試行回数とフェーズ名が明確に表示される

### FR-004: 失敗時の詳細エラーメッセージ【優先度: 中】

**説明**: 各試行が失敗した場合、詳細なエラーメッセージをログに出力し、最終失敗時にはリトライ回数到達の旨を通知する。

**詳細**:
- 各試行失敗時に`[WARNING] Attempt {attempt} failed: {error}`を出力
- 最大リトライ回数到達時に`最大リトライ回数({MAX_RETRIES})に到達しました`をGitHub Issueに投稿

**受け入れ基準**:
- **Given**: 試行が失敗する
- **When**: エラーメッセージが生成される
- **Then**: 標準出力とGitHub Issueに詳細なエラー情報が記録される

### FR-005: レビュー結果のGitHub投稿【優先度: 低】

**説明**: 2回目以降のリトライでreview()を実行した場合、レビュー結果をGitHub Issueに投稿する。

**詳細**:
- review()実行後、post_review()を呼び出し
- レビュー結果（result）、フィードバック（feedback）、改善提案（suggestions）を投稿

**受け入れ基準**:
- **Given**: 2回目以降のリトライでreview()が実行される
- **When**: レビュー結果が生成される
- **Then**: GitHub Issueにレビュー結果がコメントとして投稿される

## 3. 非機能要件

### NFR-001: パフォーマンス要件

- リトライ処理によるオーバーヘッドは許容範囲内（各試行あたり10秒以内）
- GitHub API呼び出しのレート制限を考慮した実装（1分あたり最大60リクエスト）

### NFR-002: 信頼性要件

- リトライループの無限ループを防止（MAX_RETRIES=3で上限設定）
- 例外発生時でも適切にfinallyブロックでGit commit & pushを実行
- 各試行の成功・失敗状態を正確にメタデータに記録

### NFR-003: 可用性要件

- ネットワーク障害などの一時的なエラーでも自動回復を試みる
- Claude Agent SDK APIの一時的な障害でもリトライで対応

### NFR-004: 保守性要件

- コードの可読性を維持（適切なコメントとログ出力）
- 既存のreview()、revise()メソッドのインターフェースを変更しない
- 各Phaseサブクラスでの追加実装を不要にする（基底クラスのみで対応）

### NFR-005: 拡張性要件

- 将来的なリトライ戦略の変更が容易（例: 指数バックオフ、条件付きリトライ）
- リトライ回数の設定変更が容易（環境変数やメタデータでの制御）

## 4. 制約事項

### 4.1 技術的制約

- **Python 3.8+**: 既存のコードベースとの互換性を維持
- **Claude Agent SDK**: 既存のexecute_with_claude()メソッドのインターフェースを変更しない
- **GitHub API**: REST APIのレート制限（認証済みリクエストで5000/時間）
- **既存のメタデータ構造**: metadata.jsonの構造を変更しない（後方互換性）

### 4.2 リソース制約

- **リトライ回数**: 最大3回（MAX_RETRIES=3）
- **タイムアウト**: 各試行は独立したタイムアウトを持つ（Claude Agent SDKのデフォルト設定）
- **ストレージ**: 各試行のログを個別に保存（連番付き）

### 4.3 ポリシー制約

- **コーディング規約**: CLAUDE.mdで定義されたガイドラインに従う
  - コメントは日本語で記述
  - ドキュメントは日本語で記述
  - 変数名・関数名は英語
- **Git運用**: コミットメッセージは `[Component] Action: 詳細な説明` 形式
- **エラーハンドリング**: 予期しない例外は上位に伝播させる（適切なログを残した上で）

## 5. 前提条件

### 5.1 システム環境

- Python 3.8以上がインストール済み
- Claude Agent SDK (`claude_agent_client.py`) が正常に動作
- GitHub API (`github_client.py`) が正常に動作
- MetadataManager (`metadata_manager.py`) が正常に動作

### 5.2 依存コンポーネント

- **base_phase.py**: 全Phaseクラスの基底クラス
- **execute()メソッド**: 各Phaseサブクラスで実装済み（abstractmethod）
- **review()メソッド**: 各Phaseサブクラスで実装済み（abstractmethod）
- **revise()メソッド**: 各Phaseサブクラスで実装（オプション、実装がない場合はエラー）

### 5.3 外部システム連携

- **GitHub API**: Issue #331への進捗投稿とレビュー結果投稿
- **Claude API**: Claude Agent SDK経由でのタスク実行

## 6. 受け入れ基準

### AC-001: execute()失敗時のリトライ実行

- **Given**: execute()が初回実行で失敗を返す（success=False）
- **When**: リトライループが実行される
- **Then**:
  - 2回目の試行でreview()が実行される
  - review()の結果がFAILの場合、revise()が実行される
  - 最大3回まで試行が繰り返される
  - 3回失敗した場合、フェーズがfailedとして終了する

### AC-002: execute()成功時の正常終了

- **Given**: execute()が初回実行で成功を返す（success=True）
- **When**: review()が実行される
- **Then**:
  - review()の結果がPASSの場合、リトライせずに成功終了する
  - final_status='completed'となる
  - GitHub Issueに完了報告が投稿される

### AC-003: revise()による修正成功

- **Given**: 初回execute()が失敗し、2回目の試行でrevise()が実行される
- **When**: revise()が成功を返す（success=True）
- **Then**:
  - 再度review()が実行される
  - review()の結果がPASSの場合、成功終了する
  - final_status='completed'となる

### AC-004: revise()実装なしのエラーハンドリング

- **Given**: Phaseサブクラスでrevise()が実装されていない
- **When**: 2回目の試行でrevise()を呼び出そうとする
- **Then**:
  - `hasattr(self, 'revise')`チェックが動作する
  - エラーメッセージが標準出力とGitHub Issueに投稿される
  - フェーズがfailedとして終了する

### AC-005: 最大リトライ回数到達時の処理

- **Given**: 3回の試行がすべて失敗する
- **When**: MAX_RETRIESに到達する
- **Then**:
  - `最大リトライ回数(3)に到達しました`というメッセージがGitHub Issueに投稿される
  - final_status='failed'となる
  - メタデータのphase statusがfailedに更新される
  - finallyブロックでGit commit & pushが実行される

### AC-006: ログ出力の可視性

- **Given**: リトライループが実行される
- **When**: 各試行が開始される
- **Then**:
  - `[ATTEMPT 1/3] Phase: requirements`のような形式でログ出力される
  - 80文字の区切り線（`=`）で視覚的に区別される
  - 失敗時には`[WARNING] Attempt 1 failed: {error}`が出力される

### AC-007: 既存Phaseクラスへの影響なし

- **Given**: 既存のPhaseサブクラス（requirements.py, design.py等）が存在する
- **When**: base_phase.pyのrun()メソッドを修正する
- **Then**:
  - 既存のexecute()、review()、revise()メソッドのインターフェースは変更不要
  - 各Phaseサブクラスでの追加実装は不要
  - 既存のテストが引き続きパスする（存在する場合）

## 7. スコープ外

以下の項目は本要件の対象外とする：

### 7.1 指数バックオフの実装

- リトライ間隔の段階的増加（例: 1秒、2秒、4秒）
- 将来的な拡張候補として検討

### 7.2 リトライ回数の動的変更

- フェーズごとや環境変数によるMAX_RETRIESの動的設定
- 現時点では固定値（3回）で対応

### 7.3 条件付きリトライ

- エラーの種類に応じたリトライ戦略の変更（例: ネットワークエラーのみリトライ）
- すべてのエラーを均等に扱う

### 7.4 並列リトライ

- 複数のフェーズを並列にリトライする機能
- 各フェーズは独立して直列にリトライ

### 7.5 レビュー基準の動的調整

- リトライ回数に応じてレビュー基準を緩和する機能
- レビュー基準は常に一定

### 7.6 コスト最適化

- リトライによるAPI呼び出し増加に対するコスト最適化
- 現時点ではコスト増加を許容

### 7.7 マニュアルインターベンション

- リトライ途中での手動介入・承認機能
- 完全自動でリトライを実行

### 7.8 リトライ統計の可視化

- リトライ回数の分析やダッシュボード表示
- メタデータには記録されるが、可視化は将来対応

## 8. 参考情報

### 8.1 現在の問題コード

**ファイル**: `scripts/ai-workflow/phases/base_phase.py`
**行数**: 617-625

```python
if not execute_result.get('success', False):
    # 実行失敗
    final_status = 'failed'
    self.update_phase_status(status='failed')
    self.post_progress(
        status='failed',
        details=f"実行エラー: {execute_result.get('error', 'Unknown error')}"
    )
    return False  # ← ★ここで即座に終了！リトライしない！
```

### 8.2 期待される修正後のロジック

```python
# ━━━ リトライループ ━━━
for attempt in range(1, self.MAX_RETRIES + 1):
    print(f"\n{'='*80}")
    print(f"[ATTEMPT {attempt}/{self.MAX_RETRIES}] Phase: {self.phase_name}")
    print(f"{'='*80}\n")

    # 初回はexecute()、2回目以降はrevise()
    if attempt == 1:
        result = self.execute()
    else:
        # レビュー結果に基づいてrevise()
        review_result = self.review()
        if review_result['result'] == 'PASS':
            # レビューが成功した場合は終了
            final_status = 'completed'
            break

        # revise()を実行
        feedback = review_result.get('feedback', '')
        result = self.revise(review_feedback=feedback)

    # 結果チェック
    if result.get('success', False):
        final_status = 'completed'
        break
    else:
        print(f"[WARNING] Attempt {attempt} failed: {result.get('error', 'Unknown')}")
        if attempt == self.MAX_RETRIES:
            final_status = 'failed'
            self.update_phase_status(status='failed')
            self.post_progress(
                status='failed',
                details=f"最大リトライ回数({self.MAX_RETRIES})に到達しました"
            )
            return False
```

### 8.3 関連ドキュメント

- **CLAUDE.md**: プロジェクト全体の開発ガイドライン
- **ARCHITECTURE.md**: アーキテクチャ設計思想
- **scripts/ai-workflow/README.md**: AI Workflowの使用方法
- **Issue #331**: https://github.com/tielec/infrastructure-as-code/issues/331

---

**文書履歴**:
- 2025-10-10: 初版作成（Phase 1: Requirements）
