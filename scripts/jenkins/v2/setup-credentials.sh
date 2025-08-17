#!/bin/bash
# Jenkins クレデンシャルを設定するスクリプト（冪等）

set -e

JENKINS_HOME="${JENKINS_HOME:-/mnt/efs/jenkins}"
PROJECT_NAME="${PROJECT_NAME:-jenkins-infra}"
ENVIRONMENT="${ENVIRONMENT:-dev}"

echo "===== Setting up Jenkins Credentials ====="

# AWS メタデータを取得
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
AWS_REGION=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/placement/region)

# Groovyスクリプトディレクトリ
GROOVY_DIR="${JENKINS_HOME}/init.groovy.d"
mkdir -p "$GROOVY_DIR"

# クレデンシャル設定用Groovyスクリプトを作成
cat > "$GROOVY_DIR/setup-credentials.groovy" << 'EOF'
#!groovy
import jenkins.model.*
import com.cloudbees.plugins.credentials.*
import com.cloudbees.plugins.credentials.common.*
import com.cloudbees.plugins.credentials.domains.*
import com.cloudbees.plugins.credentials.impl.*
import com.cloudbees.jenkins.plugins.sshcredentials.impl.*
import hudson.plugins.sshslaves.*
import java.util.logging.Logger

def logger = Logger.getLogger("")
def jenkins = Jenkins.getInstance()
def credentialsStore = jenkins.getExtensionList(SystemCredentialsProvider.class)[0].getStore()
def domain = Domain.global()
def credentialsChanged = false

logger.info("==== Setting up Jenkins Credentials ====")

// エージェント用SSHキーペアのクレデンシャル作成
def agentKeyId = "ec2-agent-keypair"
def existingAgentKey = credentialsStore.getCredentials(domain).find { it.id == agentKeyId }

if (!existingAgentKey) {
    logger.info("Creating EC2 agent keypair credential")
    
    // SSMから秘密鍵を取得（実際の環境では適切に設定）
    def privateKey = """-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEAplaceholder...
-----END RSA PRIVATE KEY-----"""
    
    def agentCredential = new BasicSSHUserPrivateKey(
        CredentialsScope.GLOBAL,
        agentKeyId,
        "ec2-user",
        new BasicSSHUserPrivateKey.DirectEntryPrivateKeySource(privateKey),
        "",
        "EC2 Agent SSH Key"
    )
    
    credentialsStore.addCredentials(domain, agentCredential)
    credentialsChanged = true
    logger.info("EC2 agent keypair credential created")
} else {
    logger.info("EC2 agent keypair credential already exists")
}

// Workterminal用SSHキーペアのクレデンシャル作成
def workterminalKeyId = "ec2-bootstrap-workterminal-keypair"
def existingWorkterminalKey = credentialsStore.getCredentials(domain).find { it.id == workterminalKeyId }

if (!existingWorkterminalKey) {
    logger.info("Creating Workterminal keypair credential")
    
    // SSMから秘密鍵を取得（実際の環境では適切に設定）
    def workterminalPrivateKey = """-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEAplaceholder2...
-----END RSA PRIVATE KEY-----"""
    
    def workterminalCredential = new BasicSSHUserPrivateKey(
        CredentialsScope.GLOBAL,
        workterminalKeyId,
        "ec2-user",
        new BasicSSHUserPrivateKey.DirectEntryPrivateKeySource(workterminalPrivateKey),
        "",
        "Bootstrap Workterminal SSH Key"
    )
    
    credentialsStore.addCredentials(domain, workterminalCredential)
    credentialsChanged = true
    logger.info("Workterminal keypair credential created")
} else {
    logger.info("Workterminal keypair credential already exists")
}

// GitHub用クレデンシャル（必要に応じて）
def githubTokenId = "github-token"
def existingGithubToken = credentialsStore.getCredentials(domain).find { it.id == githubTokenId }

if (!existingGithubToken) {
    logger.info("Creating GitHub token credential")
    
    def githubToken = new StringCredentialsImpl(
        CredentialsScope.GLOBAL,
        githubTokenId,
        "GitHub Personal Access Token",
        Secret.fromString("ghp_placeholder_token")
    )
    
    credentialsStore.addCredentials(domain, githubToken)
    credentialsChanged = true
    logger.info("GitHub token credential created")
} else {
    logger.info("GitHub token credential already exists")
}

if (credentialsChanged) {
    jenkins.save()
    logger.info("Credentials have been saved")
    println("CREDENTIALS_CHANGED")
} else {
    logger.info("No credential changes needed")
    println("NO_CREDENTIALS_CHANGE")
}
EOF

# SSMから実際の秘密鍵を取得してGroovyスクリプトを更新する処理を追加
# （実際の実装では、SSMパラメータから秘密鍵を取得してスクリプトに埋め込む）

# エージェント秘密鍵を取得
AGENT_PRIVATE_KEY=$(aws ssm get-parameter \
    --name "/jenkins-infra/${ENVIRONMENT}/agent/private-key" \
    --with-decryption \
    --region "$AWS_REGION" \
    --query "Parameter.Value" \
    --output text 2>/dev/null || echo "")

if [ -n "$AGENT_PRIVATE_KEY" ]; then
    # Groovyスクリプト内のプレースホルダーを実際の鍵で置換
    # （sedコマンドで適切に置換する処理を実装）
    echo "Agent private key found in SSM"
fi

# 権限設定
chown jenkins:jenkins "$GROOVY_DIR/setup-credentials.groovy"
chmod 644 "$GROOVY_DIR/setup-credentials.groovy"

echo "Credentials setup script created"
echo "CREDENTIALS_SETUP_COMPLETE"

# スクリプトは次回のJenkins再起動時に実行される
exit 0