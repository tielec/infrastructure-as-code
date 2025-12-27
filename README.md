# Jenkins CI/CD インフラストラクチャ構築

AWS上にJenkinsベースのCI/CD環境を段階的に構築・運用するためのリポジトリです。ブルーグリーンデプロイ、カスタムAMIによる高速エージェント、SSMを用いた設定管理など、運用効率を高める仕組みを揃えています。

## 📚 重要なドキュメント

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Platform Engineeringのアーキテクチャ設計思想
- **[CLAUDE.md](CLAUDE.md)** - Claude Code向けガイダンス
- **[CONTRIBUTION.md](CONTRIBUTION.md)** - 開発者向けコントリビューションガイド

## 📋 クイックナビゲーション

### セットアップ（初回構築）
- [前提条件](docs/setup/prerequisites.md)
- [ブートストラップ構築](docs/setup/bootstrap.md)
- [Pulumiバックエンド設定](docs/setup/pulumi-backend.md)

### 運用
- [Jenkinsインフラデプロイ](docs/operations/jenkins-deploy.md)
- [Jenkins環境運用管理](docs/operations/jenkins-management.md)
- [ブートストラップ管理](docs/operations/bootstrap-management.md)
- [インフラ削除](docs/operations/infrastructure-teardown.md)
- [共有パラメータ・注意事項](docs/operations/parameters.md)

### リファレンス
- [インフラ構成](docs/architecture/infrastructure.md)
- [拡張方法](docs/development/extension.md)
- [トラブルシューティング](docs/troubleshooting.md)
- [変更履歴](docs/changelog.md)

## 🧭 このREADMEについて

- 以前READMEに含まれていた詳細な手順・構成情報は、役割別に`docs/`配下へ整理しました。
- 目的に応じて上記クイックナビゲーションから該当ドキュメントを参照してください。
- 追加のFAQやリンクを見つけた場合は、対応する分割ドキュメントを更新してください。

## 🧪 まず試すこと

- ブートストラップを新規構築する場合は、[前提条件](docs/setup/prerequisites.md)と[ブートストラップ構築](docs/setup/bootstrap.md)の順に実施してください。
- 既存環境の更新やトラブル時は、[Jenkins環境運用管理](docs/operations/jenkins-management.md)および[トラブルシューティング](docs/troubleshooting.md)を参照してください。
