# 変更履歴

> 📖 **親ドキュメント**: [README.md](../README.md)

## 2025-10-16: AI Workflow V1 (Python版) の削除完了

AI Workflow V2 (TypeScript版) への移行が完了し、V1 (Python版) を削除しました。

- **削除対象**: `scripts/ai-workflow/` ディレクトリ全体（127ファイル）
- **削除実行日**: 2025年10月17日
- **削除コミット**: `0dce7388f878bca303457ca3707dbb78b39929c9`
- **バックアップ**: `archive/ai-workflow-v1-python` ブランチに保存
- **復元時間**: 1秒未満（Issue #411で検証済み）
- **V2の場所**: `scripts/ai-workflow-v2/`
- **V2のドキュメント**: [scripts/ai-workflow-v2/README.md](scripts/ai-workflow-v2/README.md)
- **関連Issue**: [#411](https://github.com/tielec/infrastructure-as-code/issues/411), [#415](https://github.com/tielec/infrastructure-as-code/issues/415)

必要に応じて、以下のコマンドでV1を復元できます（1秒未満）：

```bash
git checkout archive/ai-workflow-v1-python -- scripts/ai-workflow/
```

## 関連ドキュメント

- [README.md](../README.md)
