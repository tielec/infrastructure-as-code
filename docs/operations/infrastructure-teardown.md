# インフラストラクチャ削除

> 📖 **親ドキュメント**: [README.md](../../README.md)

## 概要

構築済みのJenkinsインフラを安全に削除するためのプレイブックと注意事項をまとめています。

## インフラストラクチャの削除

構築したJenkinsインフラストラクチャを削除する場合は、以下のコマンドを使用します：

### 全体の削除

```bash
# 削除の確認（ドライラン）
ansible-playbook playbooks/jenkins/jenkins_teardown_pipeline.yml -e "env=dev"

# 実際に削除を実行
ansible-playbook playbooks/jenkins/jenkins_teardown_pipeline.yml -e "env=dev confirm=true"

# Pulumiスタックも含めて完全に削除
ansible-playbook playbooks/jenkins/jenkins_teardown_pipeline.yml -e "env=dev confirm=true remove_stacks=true"
```

### 特定コンポーネントの削除

個別のコンポーネントを削除する場合は、専用のremoveプレイブックを使用します：

```bash
# 例: Jenkinsアプリケーション設定のみ削除
ansible-playbook playbooks/jenkins/remove/remove_jenkins_application.yml -e "env=dev confirm=true"

# 例: エージェントのみ削除
ansible-playbook playbooks/jenkins/remove/remove_jenkins_agent.yml -e "env=dev confirm=true"

# 例: コントローラーのみ削除
ansible-playbook playbooks/jenkins/remove/remove_jenkins_controller.yml -e "env=dev confirm=true"

# 例: 設定リソースのみ削除
ansible-playbook playbooks/jenkins/remove/remove_jenkins_config.yml -e "env=dev confirm=true"
```

**削除順序の注意事項**:
- 依存関係の逆順で削除する必要があります
- 例: applicationを削除してからagent、その後controller
- ネットワークやセキュリティグループは最後に削除

**注意**: 削除操作は破壊的な操作です。以下の点に注意してください：
- 必ず `confirm=true` の指定が必要です
- 環境名 (`env`) を正しく指定してください
- EFSに保存されているJenkinsデータも削除されます
- 削除前に重要なデータのバックアップを取ることを推奨します

## 関連ドキュメント

- [Jenkinsインフラデプロイ](jenkins-deploy.md)
- [Jenkins環境運用管理](jenkins-management.md)
- [README.md](../../README.md)
