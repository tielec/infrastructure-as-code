# 共有パラメータ・注意事項

> 📖 **親ドキュメント**: [README.md](../../README.md)

## 概要

Ansible共通パラメータの確認と修正手順、変更時のチェックポイントをまとめています。

## 共有パラメータの確認と修正

共有パラメータファイル（`all.yml`）が適切に設定されていることを確認してください。パラメータを変更する場合は以下の手順で行います：

```bash
# パラメータファイルを編集
vi ansible/inventory/group_vars/all.yml

# エディタで必要な変更を行った後、構文をチェック
ansible-playbook playbooks/jenkins/jenkins_setup_pipeline.yml -e "env=dev" --syntax-check

# 変更を適用（コミットする前にチェックモードで実行）
ansible-playbook playbooks/jenkins/jenkins_setup_pipeline.yml -e "env=dev" --check
```

## 注意事項

- 本番環境では適切なセキュリティ設定を行ってください
- AdministratorAccess権限は開発段階のみに使用し、本番環境では最小権限原則に従ってください
- バックアップ戦略の実装を忘れずに行ってください
- AWS認証情報は定期的に更新が必要です。セッションが切れた場合は`source scripts/aws/setup-aws-credentials.sh`を実行してください
- Pulumiパスフレーズは安全に管理してください。SSMパラメータストアから取得した値は他のユーザーに見えないように注意してください
- **削除操作は取り消せません**。本番環境での削除操作は特に注意して実行してください
- Jenkinsバージョン更新前には必ずバックアップを取得してください
- シードジョブで管理されるジョブは、手動で変更しても次回シードジョブ実行時に上書きされます

## 関連ドキュメント

- [Jenkins環境運用管理](jenkins-management.md)
- [インフラストラクチャ削除](infrastructure-teardown.md)
- [README.md](../../README.md)
