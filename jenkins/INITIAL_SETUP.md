# Jenkins初期作業マニュアル

## 概要
本マニュアルは、Jenkins環境構築後の初期手順を記載しています。

## EC2 Fleet Agentの動作確認
1. **Admin_Jobs/Test_EC2_Fleet_Agent** ジョブを実行
2. ジョブが「SUCCESS」となることを確認
3. 成功すれば、EC2 Fleet Agentが正常に利用可能

### 注意事項

- EC2 Fleetは事前にAWS側で作成し、activeな状態にしておく必要があります
- SSH秘密鍵は適切に管理し、外部に漏洩しないよう注意してください
- Maximum Cluster Sizeは初期構築時は1に設定していますが、本番運用時は必要に応じて調整してください
- WorkterminalノードのパブリックIPは、インスタンスの再起動等で変更される可能性があるため、定期的に確認が必要です

# Jenkins と GitHub Apps 連携設定マニュアル

## 概要
本マニュアルは、Jenkins と GitHub Apps を連携させ、GitHub リポジトリの自動ビルド・デプロイを実現するための設定手順を記載しています。

## 環境情報
- **Jenkins バージョン**: 2.504.2
- **GitHub**: GitHub.com（Organization: tielec）
- **Jenkins URL**: `<JENKINS_URL>` （例: http://jenkins.example.com/）
- **アクセス**: 外部からアクセス可能

## 前提条件
- Jenkins に必要なプラグインがインストール済みであること
- GitHub Organization の管理者権限を持っていること
- Jenkins の管理者権限を持っていること

## 設定手順

### 1. GitHub Apps の作成

#### 1.1 GitHub Apps ページへのアクセス
1. GitHub.com にログイン
2. tielec Organization のページへ移動
3. **Settings** → **Developer settings** → **GitHub Apps** → **New GitHub App** をクリック

#### 1.2 基本情報の設定
| 項目 | 設定値 |
|------|--------|
| **GitHub App name** | tielec-jenkins-integration |
| **Homepage URL** | `<JENKINS_URL>` |
| **Webhook URL** | `<JENKINS_URL>/github-webhook/` |
| **Webhook secret** | （推奨：強力なパスワードを設定） |

#### 1.3 権限（Permissions）の設定

**Repository permissions:**
- Contents: `Read & Write`
- Metadata: `Read`
- Pull requests: `Read & Write`
- Commit statuses: `Read & Write`
- Checks: `Read & Write`
- Issues: `Read & Write`
- Administration: `Read & Write`
- Webhooks: `Read & Write`

**Organization permissions:**
- Members: `Read`

#### 1.4 イベント購読（Subscribe to events）
以下のイベントにチェック：
- Pull request
- Push
- Repository

#### 1.5 インストール範囲
- **Where can this GitHub App be installed?**: `Only on this account` を選択

#### 1.6 App の作成
**Create GitHub App** をクリックして作成を完了

### 2. GitHub Apps の設定完了後の作業

#### 2.1 必要な情報の取得
作成した GitHub App のページから以下の情報を取得：
- **App ID**: Apps ページで確認
- **Private Key**: 
  1. Private keys セクションで **Generate a private key** をクリック
  2. `.pem` ファイルをダウンロード（安全に保管）
- **Installation ID**: 
  1. **Install App** をクリック
  2. tielec organization を選択
  3. 対象リポジトリを選択（All repositories または Selected repositories）

### 3. Jenkins 側の設定

#### 3.1 Private Key の形式変換
GitHub から取得した Private Key は PKCS#1 形式のため、PKCS#8 形式に変換が必要：

1. 以下のジョブにアクセス：
   ```
   <JENKINS_URL>/job/Admin_Jobs/job/Convert_GitHub_App_Key/
   ```
2. ジョブを実行して鍵を変換

#### 3.2 認証情報の登録
1. **Manage Jenkins** → **Manage Credentials** へ移動
2. 適切なドメイン（Global）を選択し、**Add Credentials** をクリック
3. 以下を設定：
   - **Kind**: `GitHub App`
   - **ID**: `github-app-credentials`
   - **Description**: `GitHub App for tielec organization`
   - **App ID**: 取得した App ID を入力
   - **API endpoint**: `https://api.github.com`
   - **Private Key**: `Enter directly` を選択し、変換後の鍵を貼り付け
4. **Test Connection** で接続確認
5. **Create** をクリック

### 4. 動作確認

#### 4.1 テストジョブの実行
以下のテストジョブを順番に実行して動作を確認：

1. **基本操作テスト**
   ```
   <JENKINS_URL>/job/Shared_Library/job/Git_Utils/job/GitHub_Apps_Basic_Operation_Test/
   ```

2. **Webhook 操作テスト**
   ```
   <JENKINS_URL>/job/Shared_Library/job/Git_Utils/job/Webhook_Operation_Test/
   ```

3. **設定のバックアップ**
   ```
   <JENKINS_URL>/job/Admin_Jobs/job/Backup_Config/
   ```

## 運用上の注意事項

### セキュリティに関する推奨事項
1. **Webhook Secret の設定**
   - 本番環境では必ず Webhook Secret を設定し、リクエストの正当性を検証すること

2. **HTTPS の使用**
   - 将来的には HTTPS への移行を検討すること
   - GitHub は HTTPS の使用を推奨しており、HTTP は将来制限される可能性がある

### 権限管理
- 必要最小限の権限のみを付与する
- 定期的に権限の見直しを行う
- Private Key は安全に管理し、定期的に更新する

### トラブルシューティング
1. **接続エラーが発生した場合**
   - App ID が正しいか確認
   - Private Key が PKCS#8 形式に変換されているか確認
   - API endpoint が正しいか確認

2. **Webhook が動作しない場合**
   - Webhook URL が正しいか確認
   - Jenkins が外部からアクセス可能か確認
   - GitHub Apps の Event 購読設定を確認

## 付録：設定した権限の用途

| 権限 | 用途 |
|------|------|
| Contents (R&W) | リポジトリのコード読み書き、コミット操作 |
| Metadata (R) | リポジトリの基本情報取得 |
| Pull requests (R&W) | PR の作成・更新・マージ操作 |
| Commit statuses (R&W) | ビルドステータスの更新 |
| Checks (R&W) | PR 時のチェック結果表示 |
| Issues (R&W) | Issue へのコメント投稿 |
| Administration (R&W) | デプロイキーの作成・管理 |
| Webhooks (R&W) | Webhook の動的な設定・管理 |
| Members (R) | Organization メンバー情報の取得 |


