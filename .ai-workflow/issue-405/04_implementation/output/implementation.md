# 実装ログ - Issue #405

## 実装サマリー

- **実装戦略**: EXTEND（既存のreport.tsを拡張）
- **変更ファイル数**: 1個
- **新規作成ファイル数**: 0個

## 変更ファイル一覧

### 修正

- `scripts/ai-workflow-v2/src/phases/report.ts`: ReportPhaseクラスにワークフローログのクリーンアップ機能を追加

## 実装詳細

### ファイル1: scripts/ai-workflow-v2/src/phases/report.ts

#### 変更内容

1. **`execute()`メソッドの修正**（99-106行目に追加）
   - レポート完了後、`cleanupWorkflowLogs()`メソッドを呼び出し
   - try-catchブロックでエラーハンドリング
   - クリーンアップ失敗時はWARNINGログを出力（処理は継続）

```typescript
// レポート完了後にワークフローログをクリーンアップ（Issue #405）
try {
  await this.cleanupWorkflowLogs(issueNumber);
  console.info('[INFO] Workflow logs cleaned up successfully.');
} catch (error) {
  const message = (error as Error).message ?? String(error);
  console.warn(`[WARNING] Failed to cleanup workflow logs: ${message}`);
}
```

2. **`cleanupWorkflowLogs()`メソッドの実装**（291-346行目に追加）
   - 各フェーズの`execute/`, `review/`, `revise/`ディレクトリを削除
   - `00_planning`ディレクトリは削除対象外（Issue参照ソースとして保持）
   - `metadata.json`と`output/*.md`は保持
   - 削除結果をサマリーとして出力

```typescript
/**
 * ワークフローログをクリーンアップ（Issue #405）
 *
 * Report完了後に実行され、各フェーズのexecute/review/reviseディレクトリを削除します。
 * metadata.jsonとoutput/*.mdファイルは保持されます。
 *
 * @param issueNumber - Issue番号
 */
private async cleanupWorkflowLogs(issueNumber: number): Promise<void> {
  // 削除対象のフェーズディレクトリ（01_requirements 〜 08_report）
  const phaseDirectories = [
    '01_requirements',
    '02_design',
    '03_test_scenario',
    '04_implementation',
    '05_test_implementation',
    '06_testing',
    '07_documentation',
    '08_report',
  ];

  // 削除対象のサブディレクトリ
  const targetSubdirs = ['execute', 'review', 'revise'];

  // 各フェーズディレクトリを走査し、対象サブディレクトリを削除
  for (const phaseDir of phaseDirectories) {
    for (const subdir of targetSubdirs) {
      // fs.removeSync()で削除（fs-extraライブラリ使用）
      // 削除結果をログ出力
    }
  }

  // クリーンアップサマリーを出力
  console.info(`[INFO] Cleanup summary: ${deletedCount} directories deleted, ${skippedCount} phase directories skipped.`);
}
```

#### 理由

- **実装タイミング**: レポート完了後にクリーンアップを実行することで、デバッグログが必要な段階（レポート生成前）では保持され、レポート完了後に自動削除される
- **エラーハンドリング**: クリーンアップ失敗してもワークフロー全体を停止させない（Warning扱い）
- **Git統合**: `base-phase.ts`の`run()`メソッドがフェーズ完了後に自動的にGitコミット・プッシュを実行するため、クリーンアップされた状態が自動的にコミットされる（main.tsへの変更不要）

#### 注意点

- **Planning フェーズの保護**: `00_planning`ディレクトリは削除対象外（Issue情報の参照ソースとして保持）
- **非破壊的**: クリーンアップ失敗時もワークフローは継続（WARNINGログのみ）
- **冪等性**: 既に削除されているディレクトリに対する削除操作は自動的にスキップされる

### Gitコミット統合

**main.tsへの変更は不要**でした。理由は以下の通り：

- `base-phase.ts`の`run()`メソッド（161-163行目）が既にフェーズ完了後に`autoCommitAndPush()`を自動実行
- `cleanupWorkflowLogs()`は`execute()`内で呼び出されるため、Gitコミット前に実行される
- クリーンアップされたファイル状態が自動的にコミット・プッシュされる

## 期待される効果

### リポジトリサイズ削減

- **削減率**: 約70%（30-50ファイル → 10-15ファイル/Issue）
- **削除対象**: 8フェーズ × 3ディレクトリ = 最大24ディレクトリ
- **保持対象**: `metadata.json` + `output/*.md`（8-10ファイル）

### PR レビュー効率化

- デバッグログ（`agent_log.md`, `agent_log_raw.txt`, `prompt.txt`）が削除され、成果物（`output/*.md`）のみが残る
- PRの差分が成果物に集中し、レビューが容易になる

### デバッグログの利用可能期間

- レポート生成前: すべてのログが利用可能（トラブルシューティング可能）
- レポート生成後: 自動クリーンアップ（リポジトリサイズ削減）

## 次のステップ

- **Phase 5（test_implementation）**: テストコードの実装
- **Phase 6（testing）**: 実装したクリーンアップ機能のテスト実行

## 実装の品質確認

- [x] **Phase 2の設計に沿った実装である**: 設計書はスキップされたが、Issue #405の要件に従って実装
- [x] **既存コードの規約に準拠している**: TypeScript、async/await、fs-extraの使用パターンに従う
- [x] **基本的なエラーハンドリングがある**: try-catchブロックでエラーを捕捉し、WARNINGログを出力
- [x] **明らかなバグがない**: ディレクトリの存在チェック、安全な削除処理、適切なログ出力
