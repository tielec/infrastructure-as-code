# Jenkins設定作業マニュアル

## 概要
本マニュアルは、Jenkins環境構築後の初期設定手順を記載しています。

## 設定手順

### 1. Credentials（認証情報）の設定

#### 1.1 EC2 Agent用SSH秘密鍵の登録
1. **Jenkinsの管理 > 認証情報 > System > グローバルドメイン** に移動
2. **認証情報を追加** をクリック
3. 以下の内容で設定：
   - **種類**: SSH ユーザー名と秘密鍵
   - **ID**: `ec2-agent-keypair`
   - **説明**: Spot Fleet で起動する EC2 Agent のSSH 秘密鍵
   - **ユーザー名**: `ec2-user`
   - **秘密鍵**: 実際の秘密鍵を入力（-----BEGIN RSA PRIVATE KEY-----から始まる内容）

#### 1.2 Bootstrap環境用SSH秘密鍵の登録
1. **Jenkinsの管理 > 認証情報 > System > グローバルドメイン** に移動
2. **認証情報を追加** をクリック
3. 以下の内容で設定：
   - **種類**: SSH ユーザー名と秘密鍵
   - **ID**: `ec2-bootstrap-workterminal-keypair`
   - **説明**: Bootstrap環境のSSH 秘密鍵
   - **ユーザー名**: `ec2-user`
   - **秘密鍵**: 実際の秘密鍵を入力（-----BEGIN RSA PRIVATE KEY-----から始まる内容）

### 2. Agent（EC2 Fleet）の設定

1. **Jenkinsの管理 > Clouds > New cloud** に移動
2. 以下の内容で設定：
   - **Cloud name**: `ec2-fleet`
   - **Type**: Amazon EC2 Fleet を選択
3. **Create** ボタンをクリック

4. 詳細設定：
   - **Region**: `ap-northeast-1`
   - **EC2 Fleet**: activeになっているものを選択
   - **Launcher**: SSH経由でUnixマシンのスレーブエージェントを起動
   - **認証情報**: 手順1.1で登録した`ec2-agent-keypair`を選択
   - **Private IP**: チェックする
   - **Host Key Verification Strategy**: Non verifying Verification Strategy
   - **Number of Executors**: `3`
   - **Max Idle Minutes Before Scaledown**: `15`
   - **Minimum Cluster Size**: `0`
   - **Maximum Cluster Size**: `1` （初期構築時の場合）
   - **Maximum Init Connection Timeout in sec**: `900`
   - **Cloud Status Interval in sec**: `30`

5. **Save** をクリック

### 3. Shared Libraryの設定

1. **Jenkinsの管理 > System** に移動
2. **Global Trusted Pipeline Libraries** セクションで以下を設定：
   - **Name**: `jenkins-shared-lib`
   - **Default version**: `main`
   - **Allow default version to be overridden**: チェックする
   - **Include @Library changes in job recent changes**: チェックする
   - **Cache fetched versions on controller for quick retrieval**: チェックしない
   - **Retrieval method**: Modern SCM
   - **Source Code Management**: GitHub
   - **Repository HTTPS URL**: `https://github.com/tielec/infrastructure-as-code`
   - **Discover branches**:
     - **Strategy**: Exclude branches that are also filed as PRs
   - **Library Path (optional)**: `jenkins/jobs/shared/`

### 4. セキュリティの設定

1. **Jenkinsの管理 > Security** に移動
2. 以下を設定：
   - **マークアップ記法**: Markdown Formatter

### 5. Workterminalノードの追加

1. **Jenkinsの管理 > ノード** に移動
2. **新規ノード作成** をクリック
3. 以下の内容で設定：
   - **ノード名**: `bootstrap-workterminal`
   - **Permanent Agent**: チェックを入れる
4. **OK** をクリック後、詳細設定：
   - **リモートFSルート**: `/home/ec2-user/jenkins-agent`
   - **ラベル**: `bootstrap-workterminal`
   - **用途**: このマシーンを特定ジョブ専用にする
   - **起動方法**: SSH経由でUnixマシンのスレーブエージェントを起動
   - **ホスト**: インスタンスのパブリックIPを記載
   - **認証情報**: 手順1.2で登録した`ec2-bootstrap-workterminal-keypair`を選択
   - **Host Key Verification Strategy**: Non verifying Verification Strategy

### 6. 動作確認

#### 6.1 EC2 Fleet Agentの動作確認
1. **Admin_Jobs/Test_EC2_Fleet_Agent** ジョブを実行
2. ジョブが「SUCCESS」となることを確認
3. 成功すれば、EC2 Fleet Agentが正常に利用可能

## 注意事項

- EC2 Fleetは事前にAWS側で作成し、activeな状態にしておく必要があります
- SSH秘密鍵は適切に管理し、外部に漏洩しないよう注意してください
- Maximum Cluster Sizeは初期構築時は1に設定していますが、本番運用時は必要に応じて調整してください
- WorkterminalノードのパブリックIPは、インスタンスの再起動等で変更される可能性があるため、定期的に確認が必要です

