---
name: jenkins-deploy-app
description: Jenkinsアプリケーション設定のみを再デプロイする（JCasC、プラグイン、クレデンシャル等）
user-invocable: true
---

# Jenkinsアプリケーション設定デプロイ

Jenkinsコントローラー上のアプリケーション設定を再デプロイしてください。
このplaybookは以下を順番に実行します：

1. プラグインのインストール・更新 → Jenkins再起動
2. ユーザー設定（admin、CLI）
3. クレデンシャル設定（SSH鍵、APIトークン等） → Jenkins再起動
4. JCasC設定ファイルの生成・配置（EC2 Fleet、ECS Fargate、共有ライブラリ等）
5. シードジョブの作成 → Jenkins最終再起動
6. 全設定の検証

## 前提
- 作業ディレクトリ: `/home/ec2-user/infrastructure-as-code/ansible`
- 環境: ユーザーが指定しない場合は `dev` をデフォルトとする

## 手順

```bash
ansible-playbook playbooks/jenkins/deploy/deploy_jenkins_application.yml -e "env=${ENV}"
```

- 実行時間は5〜10分程度（Jenkins再起動の待機含む）
- 出力の末尾 `PLAY RECAP` の `failed=0` を確認する

## エラー時の対応
- `failed` が発生した場合、エラー内容を表示してユーザーに報告する
- JCasC関連のエラー（`ConfigurationAsCodeBootFailure`、`UnknownAttributesException`等）の場合：
  - `scripts/jenkins/casc/jenkins.yaml.template` の設定項目がJenkinsバージョンと互換性があるか確認する
  - EFS上の古いJCasC設定ファイルが原因の可能性がある場合、SSM経由でJenkinsコントローラー上の `/mnt/efs/jenkins/jenkins.yaml` を削除してリトライする
- Jenkins再起動タイムアウトの場合：
  - Jenkinsコントローラーの `service jenkins status` で状態を確認する
