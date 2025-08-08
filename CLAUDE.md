# CLAUDE.md

このファイルは、このリポジトリでコードを扱う際のClaude Code (claude.ai/code) へのガイダンスを提供します。

## プロジェクト概要

これは包括的なJenkins CI/CDインフラ自動化プロジェクトで、ブートストラップにCloudFormation、インフラプロビジョニングにPulumi (TypeScript)、オーケストレーションにAnsibleを使用しています。本プロジェクトは、ブルーグリーンデプロイメント機能、自動スケーリングエージェント、高可用性機能を備えた本番環境対応のJenkins環境をAWS上にデプロイします。

## 必須コマンド

### Jenkins完全デプロイメント
```bash
cd ansible
ansible-playbook playbooks/jenkins_setup_pipeline.yml -e "env=dev"
```

### 個別コンポーネントデプロイメント
```bash
cd ansible
ansible-playbook playbooks/deploy_jenkins_network.yml -e "env=dev"
ansible-playbook playbooks/deploy_jenkins_security.yml -e "env=dev"
ansible-playbook playbooks/deploy_jenkins_nat.yml -e "env=dev"
ansible-playbook playbooks/deploy_jenkins_storage.yml -e "env=dev"
ansible-playbook playbooks/deploy_jenkins_loadbalancer.yml -e "env=dev"
ansible-playbook playbooks/deploy_jenkins_controller.yml -e "env=dev"
ansible-playbook playbooks/deploy_jenkins_agent.yml -e "env=dev"
ansible-playbook playbooks/deploy_jenkins_config.yml -e "env=dev"
ansible-playbook playbooks/deploy_jenkins_application.yml -e "env=dev"
```

### インフラストラクチャ削除
```bash
cd ansible
ansible-playbook playbooks/jenkins_teardown_pipeline.yml -e "env=dev confirm=true"
```

### Pulumiスタックコマンド (各pulumi/{component}ディレクトリから実行)
```bash
npm run build      # TypeScriptをコンパイル
npm run preview    # 変更をプレビュー
npm run deploy     # スタックをデプロイ
npm run destroy    # スタックを削除
```

## アーキテクチャ概要

本プロジェクトは明確な関心の分離を持つモジュラーアーキテクチャに従います：

1. **ブートストラップレイヤー** (`/bootstrap/`): CloudFormationテンプレートが必要なツールを備えた初期EC2踏み台ホストを作成
2. **インフラストラクチャレイヤー** (`/pulumi/`): 各コンポーネントはTypeScriptによる個別のPulumiスタック
3. **オーケストレーションレイヤー** (`/ansible/`): Ansibleプレイブックがデプロイメントと設定を調整

### 主要インフラストラクチャコンポーネント

- **jenkins-network**: VPC、サブネット、インターネットゲートウェイ (10.0.0.0/16)
- **jenkins-security**: セキュリティグループとIAMロール
- **jenkins-nat**: プライベートサブネットアクセス用のNATゲートウェイ/インスタンス
- **jenkins-storage**: Jenkinsデータ永続化用のEFSファイルシステム
- **jenkins-loadbalancer**: ブルーグリーンデプロイメントをサポートするALB
- **jenkins-controller**: Jenkinsコントローラーを実行するEC2インスタンス
- **jenkins-agent**: コスト効率的なエージェント用のSpotFleet設定
- **jenkins-config**: 設定管理リソース
- **jenkins-application**: SSMパラメータ経由のアプリケーションレベル設定

### セカンダリシステム

- **Lambda APIインフラストラクチャ** (`/pulumi/lambda-*`): API Gateway、Lambda、WAF、WebSocketサポートを備えた完全なサーバーレスAPI
- **Lambda関数** (`/lambda/`): PythonベースのLambda関数実装

## 開発上の考慮事項

1. **デプロイメント順序が重要**: コンポーネントには依存関係があり、正しい順序でデプロイする必要があります（パイプラインプレイブックで処理）

2. **環境設定**: 主要設定は `/ansible/inventory/group_vars/all.yml` にあり、環境固有の設定を制御します

3. **コスト最適化**: 開発環境ではコスト削減のためNATゲートウェイの代わりにNATインスタンス（t4g.nano）を使用

4. **ブルーグリーンデプロイメント**: JenkinsコントローラーはALBターゲットグループの切り替えによりゼロダウンタイム更新をサポート

5. **リカバリーモード**: ロックアウトシナリオに対応するJenkins設定に組み込まれた緊急管理者アクセスメカニズム

6. **シードジョブ**: Jenkinsジョブはシードジョブシステムを通じてコードとして管理 - Jenkins UIではなくジョブDSLファイルを修正

7. **AWSリージョン**: デフォルトリージョンはap-northeast-1（東京） - 他の場所にデプロイする場合は設定ファイルを更新

8. **CI/CDパイプラインなし**: プロジェクトはAnsible経由の手動デプロイメントを使用 - GitHub Actionsや自動パイプラインは未使用

9. **日本語ドキュメント**: READMEと多くのコメントは日本語 - Jenkinsセットアップと管理のコア機能ドキュメント