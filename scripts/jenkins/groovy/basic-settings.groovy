#!groovy
import jenkins.model.*
import hudson.security.*
import jenkins.install.InstallState
import hudson.security.csrf.DefaultCrumbIssuer

def instance = Jenkins.getInstance()

// Basic Settings
instance.setSystemMessage('Jenkins is ready!')
instance.setNumExecutors(0)  // マスターノードでのビルド実行を無効化
instance.save()

// セキュリティ設定
def hudsonRealm = new HudsonPrivateSecurityRealm(false)
def strategy = new FullControlOnceLoggedInAuthorizationStrategy()
strategy.setAllowAnonymousRead(false)

instance.setSecurityRealm(hudsonRealm)
instance.setAuthorizationStrategy(strategy)

// CSRF Protection
instance.setCrumbIssuer(new DefaultCrumbIssuer(true))

// 古いエージェントプロトコルを無効化
Set<String> agentProtocolsList = ['JNLP4-connect']
instance.setAgentProtocols(agentProtocolsList)

// セットアップウィザードを完了としてマーク
if(!instance.getInstallState().isSetupComplete()) {
  instance.setInstallState(InstallState.INITIAL_SETUP_COMPLETED)
}

instance.save()
