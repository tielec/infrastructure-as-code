---
name: jenkins-update-repo
description: mainブランチを最新に更新する
user-invocable: true
---

# リポジトリ更新

mainブランチを最新の状態に更新してください。

## 手順

```bash
/home/ec2-user/infrastructure-as-code/scripts/workterminal/update-repo-branch.sh main --ci
```

## 完了後
- 更新されたファイル一覧を報告する
- 変更がJenkins関連の場合、影響を簡潔に説明する
