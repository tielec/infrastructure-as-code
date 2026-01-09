# トラブルシューティング

> 📖 **親ドキュメント**: [README.md](../README.md)

## 概要

セットアップから運用までで遭遇しやすい問題と確認ポイントを整理しています。

- **EC2インスタンス起動後の初期化エラー**: 
  - `sudo less +F /var/log/cloud-init-output.log`でuser data実行ログを確認
  - `Bootstrap setup complete!`が表示されていない場合は、エラー内容を確認
  - よくあるエラー：インターネット接続不可、IAMロール権限不足
- **Pulumiデプロイエラー**:
  - `pulumi logs`でエラー詳細を確認
  - Lambda パッケージ作成時のハング: zip出力ストリームエラー（権限不足・ディスク枯渇等）が適切にログ出力されるようになりました（Issue #549で修正済み）
- **Ansibleエラー**: `-vvv`オプションを追加して詳細なログを確認（例: `ansible-playbook -vvv playbooks/jenkins_setup_pipeline.yml`）
- **AWS認証エラー**: `source scripts/aws/setup-aws-credentials.sh`を実行して認証情報を更新
- **Pulumiバックエンドエラー**: 
  - S3バックエンド使用時: 環境変数`PULUMI_CONFIG_PASSPHRASE`が設定されているか確認
    ```bash
    # パスフレーズが設定されているか確認
    echo $PULUMI_CONFIG_PASSPHRASE
    
    # 再設定が必要な場合
    export PULUMI_CONFIG_PASSPHRASE="your-secure-passphrase"
    
    # S3バケットの存在確認
    aws s3 ls | grep pulumi-state
    ```
- **Jenkinsへのアクセス問題**: セキュリティグループの設定を確認
- **EFSマウント問題**: マウントターゲットの可用性を確認
- **削除時のリソース依存関係エラー**: 削除順序が正しいか確認（ネットワークは最後に削除）
- **Jenkinsバージョン更新失敗**: `/var/log/jenkins-update-version.log`を確認
- **プラグインインストール失敗**: Jenkins管理画面のシステムログを確認
- **CLIユーザー作成失敗**: `/var/log/jenkins/jenkins.log`でGroovyスクリプトの実行ログを確認
- **シードジョブ作成失敗**: 
  - Pipeline pluginがインストールされているか確認
  - `/var/log/jenkins/jenkins.log`でエラーを確認
  - Gitリポジトリへのアクセス権限を確認

## 関連ドキュメント

- [Jenkins環境運用管理](operations/jenkins-management.md)
- [README.md](../README.md)
