#!groovy
import jenkins.model.*
import hudson.security.*
import jenkins.install.InstallState
import hudson.security.csrf.DefaultCrumbIssuer

def instance = Jenkins.getInstance()

// エージェントプロトコルの設定は新しいJenkinsバージョンでは不要
// Jenkins 2.516以降ではsetAgentProtocolsは使用できない

// セットアップウィザードを完了としてマーク
if(!instance.getInstallState().isSetupComplete()) {
  instance.setInstallState(InstallState.INITIAL_SETUP_COMPLETED)
}

instance.save()
