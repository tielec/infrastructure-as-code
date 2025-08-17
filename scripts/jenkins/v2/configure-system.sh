#!/bin/bash
# JCasC システム設定を適用するスクリプト（セキュリティ以外）

set -e

JENKINS_HOME="${JENKINS_HOME:-/mnt/efs/jenkins}"
PROJECT_NAME="${PROJECT_NAME:-jenkins-infra}"
ENVIRONMENT="${ENVIRONMENT:-dev}"

echo "===== Configuring Jenkins System Settings ====="

# AWS メタデータとSSMパラメータから必要な情報を取得
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
AWS_REGION=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/placement/region)

# SSMから設定値を取得
EC2_FLEET_ID=$(aws ssm get-parameter \
    --name "/jenkins-infra/${ENVIRONMENT}/agent/spotFleetRequestId" \
    --region "$AWS_REGION" \
    --query "Parameter.Value" \
    --output text 2>/dev/null || echo "")

WORKTERMINAL_HOST=$(aws ssm get-parameter \
    --name "/bootstrap/workterminal/public-ip" \
    --region "$AWS_REGION" \
    --query "Parameter.Value" \
    --output text 2>/dev/null || echo "")

JENKINS_URL=$(aws ssm get-parameter \
    --name "/jenkins-infra/${ENVIRONMENT}/application/jenkins-url" \
    --region "$AWS_REGION" \
    --query "Parameter.Value" \
    --output text 2>/dev/null || echo "http://localhost:8080/")

# 環境変数をエクスポート
export EC2_FLEET_ID
export WORKTERMINAL_HOST
export AWS_REGION
export JENKINS_URL
export SHARED_LIBRARY_REPO="${SHARED_LIBRARY_REPO:-https://github.com/tielec/infrastructure-as-code}"
export SHARED_LIBRARY_BRANCH="${SHARED_LIBRARY_BRANCH:-main}"
export SHARED_LIBRARY_PATH="${SHARED_LIBRARY_PATH:-jenkins/jobs/shared/}"
export EC2_IDLE_MINUTES="${EC2_IDLE_MINUTES:-15}"
export EC2_MIN_SIZE="${EC2_MIN_SIZE:-0}"
export EC2_MAX_SIZE="${EC2_MAX_SIZE:-1}"
export EC2_NUM_EXECUTORS="${EC2_NUM_EXECUTORS:-3}"

echo "Configuration parameters:"
echo "  Jenkins URL: $JENKINS_URL"
echo "  EC2 Fleet ID: $EC2_FLEET_ID"
echo "  Workterminal Host: $WORKTERMINAL_HOST"
echo "  AWS Region: $AWS_REGION"

# 現在の設定のハッシュを計算
CURRENT_HASH=""
if [ -f "${JENKINS_HOME}/jenkins.yaml" ]; then
    CURRENT_HASH=$(md5sum "${JENKINS_HOME}/jenkins.yaml" | cut -d' ' -f1)
fi

# JCasC設定ファイルを生成（セキュリティは無効のまま）
cat > "${JENKINS_HOME}/jenkins.yaml" << EOF
jenkins:
  systemMessage: "Jenkins Configured via JCasC (Setup in Progress)"
  numExecutors: 1
  mode: NORMAL
  authorizationStrategy:
    unsecured: {}
  securityRealm:
    local:
      allowsSignup: false
      enableCaptcha: false
  crumbIssuer:
    standard:
      excludeClientIPFromCrumb: true
  markupFormatter:
    markdownFormatter:
      disableSyntaxHighlighting: false
  disableRememberMe: false
  globalNodeProperties:
  - envVars:
      env:
      - key: "GIT_JENKINS_CREDENTIALS_ID"
        value: "github-app-credentials"
      - key: "GIT_JENKINS_REPO_BRANCH"
        value: "main"
      - key: "GIT_JENKINS_REPO_URL"
        value: "https://github.com/tielec/infrastructure-as-code.git"
EOF

# EC2 Fleet設定を追加（Fleet IDがある場合）
if [ -n "$EC2_FLEET_ID" ]; then
    cat >> "${JENKINS_HOME}/jenkins.yaml" << EOF
  clouds:
    - eC2Fleet:
        name: "ec2-fleet"
        fleet: "$EC2_FLEET_ID"
        region: "$AWS_REGION"
        idleMinutes: $EC2_IDLE_MINUTES
        minSize: $EC2_MIN_SIZE
        maxSize: $EC2_MAX_SIZE
        numExecutors: $EC2_NUM_EXECUTORS
        computerConnector:
          sSHConnector:
            credentialsId: "ec2-agent-keypair"
            port: 22
            launchTimeoutSeconds: 60
            maxNumRetries: 10
            retryWaitTime: 15
            sshHostKeyVerificationStrategy: "nonVerifyingKeyVerificationStrategy"
        labelString: "ec2-fleet"
        privateIpUsed: true
        addNodeOnlyIfRunning: false
        alwaysReconnect: false
        cloudStatusIntervalSec: 30
        disableTaskResubmit: false
        executorScaler: "noScaler"
        initOnlineCheckIntervalSec: 15
        initOnlineTimeoutSec: 900
        maxTotalUses: -1
        minSpareSize: 0
        noDelayProvision: false
        restrictUsage: false
        scaleExecutorsByWeight: false
EOF
fi

# Workterminalノード設定を追加（ホストがある場合）
if [ -n "$WORKTERMINAL_HOST" ] && [ "$WORKTERMINAL_HOST" != "None" ]; then
    cat >> "${JENKINS_HOME}/jenkins.yaml" << EOF
  nodes:
    - permanent:
        name: "bootstrap-workterminal"
        nodeDescription: "Bootstrap Workterminal Node"
        numExecutors: 1
        remoteFS: "/home/ec2-user/jenkins-agent"
        labelString: "bootstrap-workterminal"
        mode: EXCLUSIVE
        launcher:
          ssh:
            host: "$WORKTERMINAL_HOST"
            port: 22
            credentialsId: "ec2-bootstrap-workterminal-keypair"
            retryWaitTime: 5
            sshHostKeyVerificationStrategy: "nonVerifyingKeyVerificationStrategy"
        retentionStrategy: "always"
EOF
fi

# unclassified設定を追加
cat >> "${JENKINS_HOME}/jenkins.yaml" << EOF

unclassified:
  location:
    adminAddress: "jenkins-admin@example.com"
    url: "$JENKINS_URL"
  globalLibraries:
    libraries:
      - name: "jenkins-shared-lib"
        defaultVersion: "$SHARED_LIBRARY_BRANCH"
        retriever:
          modernSCM:
            clone: true
            libraryPath: "$SHARED_LIBRARY_PATH"
            scm:
              git:
                remote: "$SHARED_LIBRARY_REPO"
                traits:
                  - "gitBranchDiscovery"
  scmGit:
    addGitTagAction: false
    allowSecondFetch: false
    createAccountBasedOnEmail: false
    disableGitToolChooser: false
    hideCredentials: false
    showEntireCommitSummaryInChanges: false
    useExistingAccountWithSameEmail: false
  gitHubPluginConfig:
    hookUrl: "${JENKINS_URL}github-webhook/"
  pollSCM:
    pollingThreadCount: 10
  timestamper:
    allPipelines: false
    elapsedTimeFormat: "'<b>'HH:mm:ss.S'</b> '"
    systemTimeFormat: "'<b>'HH:mm:ss'</b> '"

tool:
  git:
    installations:
      - name: "Default"
        home: "git"
EOF

# 権限設定
chown jenkins:jenkins "${JENKINS_HOME}/jenkins.yaml"
chmod 600 "${JENKINS_HOME}/jenkins.yaml"

# 新しいハッシュを計算
NEW_HASH=$(md5sum "${JENKINS_HOME}/jenkins.yaml" | cut -d' ' -f1)

# 設定が変更されたか確認
if [ "$CURRENT_HASH" != "$NEW_HASH" ]; then
    echo "CONFIG_CHANGED"
    echo "Configuration has been updated"
else
    echo "NO_CONFIG_CHANGE"
    echo "Configuration is already up to date"
fi

echo "===== System Configuration Complete ====="
exit 0