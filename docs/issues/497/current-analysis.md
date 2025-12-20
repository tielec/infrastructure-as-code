# Issue #497 現状分析：ECS Fargate Agent WebSocket切断問題

**最終更新**: 2025-12-20
**Jenkinsバージョン**: 2.528.3

---

## 📋 問題の症状

### 現象
ECS Fargate AgentがJenkinsに接続後、約14分でWebSocket接続が切断され、ビルドが中断される。

### エラーメッセージ
```
WARNING: Failed to send back a reply to the request UserRequest:hudson.FilePath$IsDirectory@...
java.io.IOException: java.lang.InterruptedException
    at hudson.remoting.Engine$1AgentEndpoint$Transport.write(Engine.java:681)
    ...
Caused by: java.lang.InterruptedException

INFO: Ping failed. Terminating the channel ecs-fargate-ecs-fargate-15c26.
java.util.concurrent.TimeoutException: Ping started at 1766192701897 hasn't completed by 1766193026599
```

### タイムライン（最新ログより）
```
00:58:26 - WebSocket接続確立、Connected
01:05:01 - Controller→Agent Ping開始（接続から約6分35秒後）
01:12:23 - Agent→Controllerへの応答送信が繰り返し失敗
01:12:27 - Pingタイムアウト、接続終了
```

**接続持続時間**: 約13分57秒（837秒）

---

## ✅ 実装済みの対策

### 1. Route 53プライベートホストゾーン（Issue #497対応）
**目的**: NAT Instance経由のループバック通信を回避し、VPC内部でALBに直接接続

**実装内容**:
```typescript
// pulumi/jenkins-loadbalancer/index.ts
const privateZone = new aws.route53.Zone(`jenkins-private-zone`, {
    name: `jenkins.internal`,
    vpcs: [{ vpcId: vpcId }],
});

const albPrivateRecord = new aws.route53.Record(`alb-private-record`, {
    zoneId: privateZone.zoneId,
    name: `jenkins.internal`,
    type: "A",
    aliases: [{ name: alb.dnsName, zoneId: alb.zoneId }],
});
```

**確認済み**:
- ✅ Route 53プライベートホストゾーン `jenkins.internal` 作成済み
- ✅ ECSタスクは `http://jenkins.internal/` を使用している

### 2. WebSocket Keep-Alive設定（PR #501）

#### Controller側（scripts/jenkins/shell/controller-install.sh:145）
```bash
Environment="JAVA_OPTS=-Djava.awt.headless=true \
  -Djenkins.install.runSetupWizard=false \
  -Dhudson.model.DownloadService.noSignatureCheck=true \
  -Djenkins.security.canSetSecurityRealm=true \
  -Djenkins.websocket.pingInterval=15 \
  -Djenkins.websocket.idleTimeout=600"
```

**確認済み**:
- ✅ systemdサービスファイルに設定されている
- ✅ `systemctl cat jenkins | grep JAVA_OPTS` で確認済み

#### Agent側（docker/jenkins-agent-ecs/entrypoint.sh:38,51）
```bash
exec java \
    -Dhudson.remoting.Launcher.pingIntervalSec=10 \
    -jar "${JENKINS_AGENT_HOME}/agent.jar" \
    -url "${JENKINS_URL}" \
    -secret "${SECRET}" \
    -name "${AGENT_NAME}" \
    -workDir "${WORKDIR}" \
    -webSocket
```

**確認済み**:
- ✅ entrypoint.shに設定されている
- ✅ Dockerイメージ: 2025-12-19ビルド版（最新）

### 3. ALBアイドルタイムアウト設定
```typescript
// pulumi/jenkins-loadbalancer/index.ts:61
idleTimeout: 3600,  // WebSocket接続用に1時間に延長
```

**確認済み**: ✅ 3600秒（1時間）に設定済み

---

## 📊 効果の検証

### 対策前後の比較

| 項目 | 対策前 | 対策後（現在） | 改善率 |
|------|--------|---------------|--------|
| 接続持続時間 | 約6分（360秒） | 約14分（837秒） | **+133%** |
| DNS経路 | NAT Instance経由 | VPC内部直接 | ✅ |
| 設定反映 | なし | 設定ファイルに記述 | ⚠️ |

**結論**: Route 53プライベートホストゾーンの効果は出ているが、まだ不十分

---

## 🔍 根本原因の分析

### 🚨 重大な問題：設定が効いていない

#### 期待される動作
- **Controller → Agent Ping**: 15秒間隔
- **Agent → Controller Ping**: 10秒間隔
- **アイドルタイムアウト**: 600秒（10分）

#### 実際の動作（ログ分析）
```
接続確立: 00:58:26
Ping開始: 01:05:01
差分: 約6分35秒（395秒）
```

**設定では15秒間隔のはずが、実際には約6分半後に最初のPingが送信されている！**

### 原因の仮説（検証状況）

#### ✅ コントローラーのSystem Propertiesは反映済み
- Script Console結果より `jenkins.websocket.pingInterval=15 / idleTimeout=600` に加え、`hudson.slaves.ChannelPinger.pingIntervalSeconds=15 / timeoutSeconds=60` もJVMオプションとして読み込まれている。
- `JAVA_OPTS` に `-Djenkins.websocket.enforceKeepAlive=true` を追加し、Jetty側でもKeep-Alive強制中。

#### ❌ WebSocket ChannelにChannelPingerが付与されていない
- `Jenkins.instance.computers` からリモートエージェントのChannelを列挙し、`channel.getProperty(hudson.slaves.ChannelPinger.class)` を確認したが常に `null`。
- つまり Controller → Agent のPingThread（ChannelPinger）がWebSocket接続で動作しておらず、プロパティを設定しても効果がない。

#### ❌ Jetty Keep-Alive強制でも改善せず
- `-Djenkins.websocket.enforceKeepAlive=true` 追加後もCloudWatchログ上では接続から約6分後に初回Ping→応答不能→切断という挙動が継続。
- ALBのアイドルタイムアウト（3600秒）やAgent側の `pingIntervalSec=10` には変化なし。

#### 📌 Jenkins 2.528.x固有のリグレッション疑い
- Jenkinsコミュニティ [Agent suddenly disconnected](https://community.jenkins.io/t/agent-suddenly-disconnected/35667) でも2.528.1以降で同症状が報告されている。
- Jenkins JIRAを `text ~ "websocket" AND text ~ "2.528"` 等で検索したが該当issueはゼロ。現時点では未報告または未解決のバグと考えられる。

### エラーの詳細分析

#### 片方向通信の失敗
```
Controller → Agent: リクエスト送信 ✅ 成功
Agent → Controller: 応答送信 ❌ 失敗
```

**エラー内容**:
```java
Failed to send back a reply to the request UserRequest:hudson.FilePath$IsDirectory
java.io.IOException: java.lang.InterruptedException
    at hudson.remoting.Engine$1AgentEndpoint$Transport.write(Engine.java:681)
Caused by: java.lang.InterruptedException
    at java.base/java.util.concurrent.CompletableFuture.reportGet
    at io.jenkins.remoting.shaded.org.glassfish.tyrus.core.TyrusRemoteEndpoint$Async$1.get
```

**解釈**:
- ControllerからのFilePath操作リクエストは届いている
- Agentが応答を返そうとしたが、WebSocket送信でブロック/タイムアウト
- CompletableFutureがInterruptされた = WebSocket接続が既に閉じられている

#### Pingタイムアウトの詳細
```
Ping started at: 1766192701897 (01:05:01)
Timeout at:      1766193026599 (01:10:26)
差分: 324,702ms = 約324秒（5分24秒）
```

**解釈**:
- ControllerがAgentにPingを送信
- 約5分24秒待っても応答がない
- タイムアウトして接続を切断

---

## 🎯 次のアクションプラン

### 優先度1: リグレッションとしての証跡固め・情報共有

- **Action 1-1: 設定反映結果のドキュメント化（完了）**  
  System Properties 出力、Channel property が `null` だったログ、CloudWatchでの切断タイムラインを保存済み。
- **Action 1-2: 公式Issue調査（完了）**  
  Jenkins JIRAを `text ~ "websocket" AND text ~ "2.528"` で検索したが該当無し。コミュニティ投稿（qlik-okl氏）を参考リンクとして記録。
- **Action 1-3: Jenkins JIRAへの起票（予定）**  
  再現条件: Jenkins 2.528.3 + WebSocket inbound agent（ECS/EKS問わず）でChannelPingerがattachされず6分程度で切断される。添付資料: CloudWatchログ・Script Console結果・コミュニティURL。

### 優先度2: 運用継続のための暫定対策

- **Option 2-1: WebSocketを停止しHTTP(JNLP)へ戻す**  
  Amazon ECSプラグインのテンプレートまたはImage entrypointから `-webSocket` を外し、JNLP接続に切り替える。ControllerのChannelPingerが機能するため切断リスクが大幅に下がる。
- **Option 2-2: Jenkinsバージョンのロールバック**  
  2.462.xなどChannelPingerが正常に動いていたLTSへ一時的に戻す。ただし最新セキュリティFixが失われるリスクあり。
- **Option 2-3: 旧来のEC2/Spotエージェントを併用**  
  ECS WebSocketエージェントが安定するまで、重要ジョブはEC2 Fleet側で実行して影響を最小化。

### 優先度3: 追加ログ収集（Issue報告向け）

- `Manage Jenkins → System Log` で `org.jenkinsci.remoting.websocket`, `hudson.remoting`, `jenkins.agents.WebSocketAgents` をFINE以上に設定し、問題再現時のログを取得する。
- ALB/NLBレベルの接続ログと突き合わせ、AWS経路ではタイムアウトが発生していないことを証明する。

---

## 📚 関連リソース

### 実装済みの変更
- [PR #501: Add websocket options to JAVA_OPTS](https://github.com/tielec/infrastructure-as-code/pull/501)
- [PR #500: Route 53 Private Hosted Zone implementation](https://github.com/tielec/infrastructure-as-code/pull/500)

### Issue #497関連ドキュメント
- [Issue #497本文](https://github.com/tielec/infrastructure-as-code/issues/497)
- [issue-497-research.md](./issue-497-research.md) - 調査結果まとめ

### Jenkins公式リソース
- [JENKINS-66172: Unexplained websocket idle timeout disconnects](https://issues.jenkins.io/browse/JENKINS-66172)
- [JENKINS-69955: Make websocket connection idleTimeout configurable](https://github.com/jenkinsci/jenkins/pull/7670)
- [Agent suddenly disconnected (Jenkins Community Forum, 2.528.1報告)](https://community.jenkins.io/t/agent-suddenly-disconnected/35667)

### AWS ALB + WebSocket関連
- [CloudBees KB: WebSocket Inbound Agents disconnect intermittently](https://docs.cloudbees.com/docs/cloudbees-ci-kb/latest/client-and-managed-controllers/websocket-inbound-agents-disconnect-intermittenly-due-to-websockettimeoutexception-connection-idle-timeout)
- [AWS re:Post: Can't check websocket message in ALB idle timeout](https://repost.aws/questions/QUj--eltTjSV2pedcb_rwPpQ/can-t-check-websocket-message-in-alb-idle-timeout)

---

## 🔄 ステータス

### 現在の状態
- ⚠️ **問題継続中**: WebSocket接続が約14分で切断
- ✅ **設定反映確認済み**: System Properties / JVM引数には全てのオプションが渡っている
- ❌ **ChannelPinger未添付**: WebSocketチャネルに ChannelPinger がセットされず、PingThreadが発火していない

### 次のマイルストーン
1. ✅ ログ分析・System Info確認完了
2. ✅ Channel property 調査で `ChannelPinger` 未添付を特定
3. 🔄 Jenkins Issue（2.528.x WebSocketリグレッション）起票
4. ⏳ 暫定回避策（HTTP接続 or ダウングレード）を選択・実装
5. ⏳ 修正版リリース後の再検証

---

## 💡 暫定回避策

現時点で根本解決まで時間がかかる場合、以下の暫定策を検討：

### 回避策1: ビルドジョブを短時間に分割
- 14分以内で完了するようにジョブを分割
- ただし、運用負荷が増加

### 回避策2: EC2 Fleetエージェントを使用
- ECS Fargateの代わりにEC2 Fleetエージェントを一時的に使用
- WebSocket問題を回避できるが、コストが増加

### 回避策3: ビルド完了まで手動監視
- 切断が発生したら手動で再実行
- 一時的な対処として

---

**調査継続中**: Jenkins 2.528.x のWebSocketチャネルにChannelPingerがattachされないリグレッションを切り分け中（公式Issue起票予定）
