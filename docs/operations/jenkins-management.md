# Jenkins環境運用管理

> 📖 **親ドキュメント**: [README.md](../../README.md)

## 概要

構築済みのJenkins環境を運用するための設定更新、シードジョブ管理、実行頻度の目安をまとめています。

### 6. Jenkins環境の運用管理

#### Jenkinsアプリケーション設定の更新

構築済みのJenkins環境に対して、以下の管理タスクを実行できます：

```bash
# すべての設定を更新（バージョン更新、プラグイン、ユーザー、ジョブ）
ansible-playbook playbooks/jenkins/deploy/deploy_jenkins_application.yml -e "env=dev"

# Jenkinsバージョンのみ更新
ansible-playbook playbooks/jenkins/deploy/deploy_jenkins_application.yml \
  -e "env=dev version=2.555.1 plugins=false setup_cli_user=false setup_seed_job=false"

# プラグインのみ更新
ansible-playbook playbooks/jenkins/deploy/deploy_jenkins_application.yml \
  -e "env=dev jenkins_version=latest setup_cli_user=false setup_seed_job=false"

# シードジョブのみ更新
ansible-playbook playbooks/jenkins/deploy/deploy_jenkins_application.yml \
  -e "env=dev jenkins_version=latest install_plugins=false setup_cli_user=false"
```

詳細な段階的更新手順は [Jenkins アップグレード Runbook](../jenkins-upgrade-runbook.md) を参照してください。

#### シードジョブによるジョブ管理

シードジョブはGitリポジトリからJob DSL/Jenkinsfileを読み込み、Jenkinsジョブを自動管理します：

```bash
# デフォルトのシードジョブ作成
ansible-playbook playbooks/jenkins/deploy/deploy_jenkins_application.yml \
  -e "env=dev" \
  -e "jenkins_version=latest install_plugins=false setup_cli_user=false"

# カスタムリポジトリを使用
ansible-playbook playbooks/jenkins/deploy/deploy_jenkins_application.yml \
  -e "env=dev" \
  -e "jenkins_jobs_repo=https://github.com/myorg/jenkins-jobs.git" \
  -e "jenkins_jobs_branch=main" \
  -e "jenkins_jobs_jenkinsfile=seed-job/Jenkinsfile"
```

#### 管理タスクの実行頻度

| タスク | 推奨頻度 | 実行時間 |
|--------|----------|----------|
| Jenkinsバージョン更新 | 月1回（詳細手順は [Runbook](../jenkins-upgrade-runbook.md) を参照） | 5-10分 |
| プラグイン更新 | 週1回 | 3-5分 |
| シードジョブ実行 | ジョブ定義変更時 | 1-3分 |
| 全体再デプロイ | 大規模変更時のみ | 1-2時間 |

詳細な更新手順、段階的な検証、ロールバック条件は [Jenkins アップグレード Runbook](../jenkins-upgrade-runbook.md) を参照してください。

## 関連ドキュメント

- [Jenkinsインフラデプロイ](jenkins-deploy.md)
- [インフラ削除](infrastructure-teardown.md)
- [README.md](../../README.md)
