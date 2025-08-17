#!/bin/bash
# Seed Jobを作成するスクリプト

set -e

JENKINS_HOME="${JENKINS_HOME:-/mnt/efs/jenkins}"
SEED_JOB_NAME="${SEED_JOB_NAME:-seed-job}"
PROJECT_NAME="${PROJECT_NAME:-jenkins-infra}"
ENVIRONMENT="${ENVIRONMENT:-dev}"

echo "===== Creating Seed Job ====="

# AWS メタデータを取得
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
AWS_REGION=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/placement/region)

# Git設定を取得
GIT_REPO=$(aws ssm get-parameter \
    --name "/jenkins-infra/${ENVIRONMENT}/config/git-repo" \
    --region "$AWS_REGION" \
    --query "Parameter.Value" \
    --output text 2>/dev/null || echo "https://github.com/tielec/infrastructure-as-code.git")

GIT_BRANCH=$(aws ssm get-parameter \
    --name "/jenkins-infra/${ENVIRONMENT}/config/git-branch" \
    --region "$AWS_REGION" \
    --query "Parameter.Value" \
    --output text 2>/dev/null || echo "main")

# ジョブディレクトリを作成
mkdir -p "${JENKINS_HOME}/jobs/${SEED_JOB_NAME}"

# Pipeline Job のconfig.xmlを作成
cat > "${JENKINS_HOME}/jobs/${SEED_JOB_NAME}/config.xml" << EOF
<?xml version='1.1' encoding='UTF-8'?>
<flow-definition plugin="workflow-job">
  <actions/>
  <description>Seed job to create other Jenkins jobs from Job DSL</description>
  <keepDependencies>false</keepDependencies>
  <properties>
    <jenkins.model.BuildDiscarderProperty>
      <strategy class="hudson.tasks.LogRotator">
        <daysToKeep>30</daysToKeep>
        <numToKeep>10</numToKeep>
        <artifactDaysToKeep>-1</artifactDaysToKeep>
        <artifactNumToKeep>-1</artifactNumToKeep>
      </strategy>
    </jenkins.model.BuildDiscarderProperty>
    <org.jenkinsci.plugins.workflow.job.properties.PipelineTriggersJobProperty>
      <triggers/>
    </org.jenkinsci.plugins.workflow.job.properties.PipelineTriggersJobProperty>
  </properties>
  <definition class="org.jenkinsci.plugins.workflow.cps.CpsScmFlowDefinition" plugin="workflow-cps">
    <scm class="hudson.plugins.git.GitSCM" plugin="git">
      <configVersion>2</configVersion>
      <userRemoteConfigs>
        <hudson.plugins.git.UserRemoteConfig>
          <url>${GIT_REPO}</url>
        </hudson.plugins.git.UserRemoteConfig>
      </userRemoteConfigs>
      <branches>
        <hudson.plugins.git.BranchSpec>
          <name>*/${GIT_BRANCH}</name>
        </hudson.plugins.git.BranchSpec>
      </branches>
      <doGenerateSubmoduleConfigurations>false</doGenerateSubmoduleConfigurations>
      <submoduleCfg class="empty-list"/>
      <extensions/>
    </scm>
    <scriptPath>jenkins/jobs/pipeline/_seed/job-creator/Jenkinsfile</scriptPath>
    <lightweight>true</lightweight>
  </definition>
  <triggers/>
  <disabled>false</disabled>
</flow-definition>
EOF

# 権限設定
chown -R jenkins:jenkins "${JENKINS_HOME}/jobs/${SEED_JOB_NAME}"

# Jenkinsに新しいジョブを認識させる
echo "Reloading Jenkins configuration..."
curl -X POST "http://localhost:8080/reload" 2>/dev/null || true

# 少し待機してからジョブの存在を確認
sleep 5

if [ -d "${JENKINS_HOME}/jobs/${SEED_JOB_NAME}" ]; then
    echo "SEED_JOB_CREATED"
    echo "Seed job '${SEED_JOB_NAME}' created successfully"
else
    echo "Failed to create seed job"
    exit 1
fi

echo "===== Seed Job Creation Complete ====="
exit 0