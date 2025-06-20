#!groovy
import jenkins.model.*
import hudson.security.*
import jenkins.install.InstallState
import hudson.security.csrf.DefaultCrumbIssuer

def instance = Jenkins.getInstance()

// 古いエージェントプロトコルを無効化
Set<String> agentProtocolsList = ['JNLP4-connect']
instance.setAgentProtocols(agentProtocolsList)

// セットアップウィザードを完了としてマーク
if(!instance.getInstallState().isSetupComplete()) {
  instance.setInstallState(InstallState.INITIAL_SETUP_COMPLETED)
}

instance.save()
