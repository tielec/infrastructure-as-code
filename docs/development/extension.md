# 拡張方法

> 📖 **親ドキュメント**: [README.md](../../README.md)

## 概要

PulumiスタックやAnsibleプレイブックを追加してインフラを拡張するためのサンプル構造を示します。

リポジトリ構造は以下のように拡張可能です：

1. 新しいコンポーネントの追加:
```
pulumi/
  ├─jenkins-network/          # 既存のネットワークスタック
  ├─jenkins-security/         # 既存のセキュリティスタック
  ├─jenkins-application/      # 既存のアプリケーション設定スタック
  ├─monitoring/               # 新しいモニタリングスタック
  └─database/                 # 新しいデータベーススタック
```

2. 新しいAnsibleプレイブックの追加:
```
ansible/playbooks/jenkins/
  ├─jenkins_setup_pipeline.yml      # 既存のメインパイプライン
  ├─jenkins_teardown_pipeline.yml   # 既存の削除パイプライン
  ├─deploy/
  │  ├─deploy_jenkins_network.yml      # 既存のネットワークデプロイ
  │  ├─deploy_jenkins_application.yml  # 既存のアプリケーション設定
  │  └─deploy_monitoring.yml           # 新しいモニタリングデプロイ
  └─remove/
     ├─remove_jenkins_network.yml      # ネットワーク削除
     └─remove_monitoring.yml           # モニタリング削除
```

3. 新しいロールの追加時は、必ず`deploy.yml`と`destroy.yml`の両方を実装してください

## 関連ドキュメント

- [インフラ構成](../architecture/infrastructure.md)
- [README.md](../../README.md)
