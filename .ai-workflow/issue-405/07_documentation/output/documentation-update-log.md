# プロジェクトドキュメント更新ログ

## 調査したドキュメント

以下のドキュメントファイルを調査しました（.ai-workflowディレクトリとnode_modules、テンプレートファイルは除外）：

### プロジェクトルート
- `README.md`
- `ARCHITECTURE.md`
- `CLAUDE.md`
- `CONTRIBUTION.md`

### scripts/ai-workflow-v2/（メイン対象）
- `scripts/ai-workflow-v2/README.md`
- `scripts/ai-workflow-v2/ARCHITECTURE.md`
- `scripts/ai-workflow-v2/DOCKER_AUTH_SETUP.md`
- `scripts/ai-workflow-v2/PROGRESS.md`
- `scripts/ai-workflow-v2/ROADMAP.md`
- `scripts/ai-workflow-v2/SETUP_TYPESCRIPT.md`
- `scripts/ai-workflow-v2/TROUBLESHOOTING.md`

### その他のサブディレクトリ
- `ansible/README.md`
- `ansible/CONTRIBUTION.md`
- `jenkins/README.md`
- `jenkins/INITIAL_SETUP.md`
- `jenkins/CONTRIBUTION.md`
- `pulumi/README.md`
- `pulumi/CONTRIBUTION.md`
- `scripts/README.md`
- `scripts/CONTRIBUTION.md`
- `scripts/ai-workflow/README.md`
- `scripts/ai-workflow/ARCHITECTURE.md`
- `scripts/ai-workflow/DOCKER_AUTH_SETUP.md`
- `scripts/ai-workflow/ROADMAP.md`
- `scripts/ai-workflow/SETUP_PYTHON.md`
- `scripts/ai-workflow/TROUBLESHOOTING.md`

## 更新したドキュメント

### `scripts/ai-workflow-v2/README.md`
**更新理由**: Report Phaseの機能説明にワークフローログクリーンアップ機能を追加する必要があるため

**主な変更内容**:
- フェーズ概要表のPhase 8（report.ts）の説明に「ワークフローログクリーンアップ」を追加
- 「ワークフローログの自動クリーンアップ」セクションを新規追加
  - 削除対象（execute/, review/, revise/ディレクトリ）
  - 保持対象（metadata.json, output/*.md）
  - 保護対象（00_planningディレクトリ）
  - 効果（リポジトリサイズ約70%削減、PRレビュー効率化）
  - 非破壊的動作の説明

### `scripts/ai-workflow-v2/ARCHITECTURE.md`
**更新理由**: ワークフローメタデータの構造説明にクリーンアップ機能の詳細を追加する必要があるため

**主な変更内容**:
- 「ワークフローログクリーンアップ（Issue #405）」サブセクションを新規追加
  - 削除対象の詳細（フェーズ範囲とディレクトリ名、内容）
  - 保持対象の詳細（metadata.json, output/*.md, 00_planning全体）
  - 実行タイミングの説明（Report Phaseのexecute()完了後、Gitコミット前）
  - エラーハンドリングの動作（WARNINGログのみ、ワークフロー継続）

### `scripts/ai-workflow-v2/TROUBLESHOOTING.md`
**更新理由**: ユーザーがクリーンアップ機能により直面する可能性のある問題と対処法を追加する必要があるため

**主な変更内容**:
- 「8. ワークフローログクリーンアップ関連」セクションを新規追加
  - 「デバッグログが見つからない」トラブルシューティング
    - Report Phase後の自動削除の説明
    - バックアップ方法の推奨
    - 保持されるファイル（metadata.json, output/*.md, 00_planning）の案内
  - 「クリーンアップ失敗時の対処」
    - WARNING ログの例
    - 手動クリーンアップコマンドの提供
  - 「クリーンアップをスキップしたい場合」
    - 現在スキップ不可の説明
    - バックアップ推奨
- 「デバッグのヒント」セクションを「9.」に番号変更
  - agent_log_raw.txtの利用可能期間の注記を追加（Report Phase前のみ）

## 更新不要と判断したドキュメント

- `README.md`（プロジェクトルート）: Jenkins CI/CD環境構築の全体ドキュメント。ai-workflow-v2の内部実装詳細は対象外
- `ARCHITECTURE.md`（プロジェクトルート）: Platform Engineeringの全体アーキテクチャ。ai-workflow-v2の詳細は対象外
- `CLAUDE.md`: Claude Code向けガイダンス。ワークフロー実装の内部詳細は含まない
- `CONTRIBUTION.md`（プロジェクトルート）: 開発者向けコントリビューションガイド。実装機能の詳細は対象外
- `scripts/ai-workflow-v2/DOCKER_AUTH_SETUP.md`: Docker認証設定のみ。ワークフロー機能とは無関係
- `scripts/ai-workflow-v2/PROGRESS.md`: 進捗サマリー。Phase 8が完了済みと記載されており、内部実装詳細は対象外
- `scripts/ai-workflow-v2/ROADMAP.md`: 今後の改善計画。既実装機能（Issue #405）は対象外
- `scripts/ai-workflow-v2/SETUP_TYPESCRIPT.md`: ローカル開発環境構築手順のみ。ワークフロー機能とは無関係
- `ansible/*`: Ansible関連ドキュメント。ai-workflowの機能とは無関係
- `jenkins/*`: Jenkins関連ドキュメント。ai-workflowの内部実装とは無関係
- `pulumi/*`: Pulumi関連ドキュメント。ai-workflowの機能とは無関係
- `scripts/README.md`, `scripts/CONTRIBUTION.md`: scriptsディレクトリ全体の概要。個別機能の詳細は対象外
- `scripts/ai-workflow/*`: Python版ai-workflowのドキュメント。TypeScript版（ai-workflow-v2）とは別実装

## 更新判断の基準

### 更新対象とした理由

1. **ユーザーへの直接的な影響**: Report Phase実行後にデバッグログが削除されるため、ユーザーが知らないと困る
2. **動作の可視性**: 自動的にファイルが削除される動作のため、明示的なドキュメント記載が必要
3. **トラブルシューティング**: デバッグログが見つからない場合の対処法が必要

### 更新対象外とした理由

1. **スコープ外**: プロジェクト全体のドキュメント（ルートのREADME.md等）はai-workflow-v2の内部実装詳細を含まない
2. **無関係なサブシステム**: Ansible、Jenkins、Pulumiは独立したコンポーネントで、ai-workflowの機能とは無関係
3. **Python版との分離**: scripts/ai-workflow（Python版）とscripts/ai-workflow-v2（TypeScript版）は別実装

## 品質確認

- [x] **影響を受けるドキュメントが特定されている**: README.md、ARCHITECTURE.md、TROUBLESHOOTING.mdの3ファイルを特定
- [x] **必要なドキュメントが更新されている**: 上記3ファイルすべてに適切な説明を追加
- [x] **更新内容が記録されている**: 本ログに更新理由、変更内容、判断基準を記録
