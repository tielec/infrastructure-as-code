---
name: jenkins-deploy-app
description: Jenkinsアプリケーション設定のみを再デプロイする（JCasC、プラグイン、クレデンシャル等）
user-invocable: true
---

# Jenkinsアプリケーション設定デプロイ

Step 3（アプリケーション設定）のみを実行してください。

## 前提
- 作業ディレクトリ: `/home/ec2-user/infrastructure-as-code/ansible`
- 環境: ユーザーが指定しない場合は `dev` をデフォルトとする

## 手順

```bash
ansible-playbook playbooks/jenkins/deploy/deploy_jenkins_application.yml -e "env=${ENV}"
```

## 完了後
- 結果（ok数、changed数、failed数）を報告する

## エラー時の対応
- `failed` が発生した場合、エラー内容を表示してユーザーに報告する
- JCasC関連のエラーの場合、`scripts/jenkins/casc/jenkins.yaml.template` の内容と実際のJenkinsバージョンの互換性を確認する
- EFS上の古いJCasC設定ファイルが原因の可能性がある場合、Jenkinsコントローラー上の `/mnt/efs/jenkins/jenkins.yaml` を削除してリトライする
