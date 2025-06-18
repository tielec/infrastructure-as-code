#!/bin/bash
# Jenkins シードジョブのセットアップ
# SSM経由で実行されることを前提

# エラーハンドリング設定
set -e

# ログ関数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a /var/log/jenkins-application-setup.log
}

# エラーハンドラー
error_exit() {
    log "ERROR: $1"
    exit 1
}

log "===== Setting up Jenkins Seed Job ====="

# 環境変数の設定
JENKINS_HOME="${JENKINS_HOME:-/mnt/efs/jenkins}"
SCRIPTS_DIR="${SCRIPTS_DIR:-/mnt/efs/jenkins/scripts}"
export SCRIPTS_DIR

# デフォルト値の設定
SEED_JOB_NAME="${SEED_JOB_NAME:-seed-job}"
JENKINS_JOBS_REPO="${JENKINS_JOBS_REPO:-https://github.com/your-org/jenkins-job-definitions.git}"
JENKINS_JOBS_BRANCH="${JENKINS_JOBS_BRANCH:-main}"
GIT_CREDENTIALS_ID="${GIT_CREDENTIALS_ID:-github-credentials}"
JOB_DSL_SCRIPTS_PATH="${JOB_DSL_SCRIPTS_PATH:-jenkins/jobs/seed-job/Jenkinsfile}"
UPDATE_EXISTING_JOB="${UPDATE_EXISTING_JOB:-true}"
RUN_INITIAL_BUILD="${RUN_INITIAL_BUILD:-false}"

# 環境変数をエクスポート
export SEED_JOB_NAME
export JENKINS_JOBS_REPO
export JENKINS_JOBS_BRANCH
export GIT_CREDENTIALS_ID
export JOB_DSL_SCRIPTS_PATH
export UPDATE_EXISTING_JOB
export RUN_INITIAL_BUILD

log "Configuration:"
log "  JENKINS_HOME: $JENKINS_HOME"
log "  SEED_JOB_NAME: $SEED_JOB_NAME"
log "  JENKINS_JOBS_REPO: $JENKINS_JOBS_REPO"
log "  JENKINS_JOBS_BRANCH: $JENKINS_JOBS_BRANCH"
log "  GIT_CREDENTIALS_ID: $GIT_CREDENTIALS_ID"
log "  JENKINSFILE_PATH: $JOB_DSL_SCRIPTS_PATH"

# プラグインの確認（パイプラインジョブなのでworkflow-jobプラグインを確認）
log "Checking required plugins..."
if [ -d "${JENKINS_HOME}/plugins/workflow-job" ]; then
    log "✓ Pipeline plugin (workflow-job) directory found"
else
    log "✗ Pipeline plugin directory not found"
fi

# Groovyディレクトリの作成
GROOVY_DIR="${JENKINS_HOME}/init.groovy.d"
mkdir -p "$GROOVY_DIR"

# スクリプトファイルの確認
GROOVY_SCRIPT="${SCRIPTS_DIR}/jenkins/groovy/create-seed-job.groovy"
XML_FILE="${SCRIPTS_DIR}/jenkins/jobs/seed-job.xml"

if [ ! -f "$GROOVY_SCRIPT" ]; then
    error_exit "Groovy script not found: $GROOVY_SCRIPT"
fi

if [ ! -f "$XML_FILE" ]; then
    error_exit "Job XML file not found: $XML_FILE"
fi

# XMLファイルを一時ディレクトリにコピー（Groovyスクリプトからアクセスしやすくするため）
log "Copying seed job XML configuration..."
cp "$XML_FILE" /tmp/seed-job.xml
chmod 644 /tmp/seed-job.xml

# Groovyスクリプトをinit.groovy.dにコピー
log "Copying seed job creation script..."
cp "$GROOVY_SCRIPT" "$GROOVY_DIR/create-seed-job.groovy"
chown jenkins:jenkins "$GROOVY_DIR/create-seed-job.groovy"
chmod 644 "$GROOVY_DIR/create-seed-job.groovy"

# Jenkinsを再起動して実行
log "Restarting Jenkins to create seed job..."
systemctl restart jenkins

# 起動を待機
log "Waiting for Jenkins to start..."
TIMEOUT=300
ELAPSED=0
while [ $ELAPSED -lt $TIMEOUT ]; do
    if curl -sf http://localhost:8080/login > /dev/null 2>&1; then
        log "Jenkins is running"
        break
    fi
    sleep 5
    ELAPSED=$((ELAPSED + 5))
done

if [ $ELAPSED -ge $TIMEOUT ]; then
    error_exit "Jenkins failed to start within timeout"
fi

# セットアップの完了を待機
log "Waiting for seed job creation to complete..."
sleep 30

# スクリプトを削除
rm -f "$GROOVY_DIR/create-seed-job.groovy"
rm -f /tmp/seed-job.xml

# 結果の確認
log "Verifying seed job creation..."

# ジョブの存在確認
if [ -d "${JENKINS_HOME}/jobs/${SEED_JOB_NAME}" ]; then
    log "✓ Seed job directory found: ${JENKINS_HOME}/jobs/${SEED_JOB_NAME}"
    
    # config.xmlの確認
    if [ -f "${JENKINS_HOME}/jobs/${SEED_JOB_NAME}/config.xml" ]; then
        log "✓ Seed job config.xml exists"
        
        # Git URLの確認
        if grep -q "$JENKINS_JOBS_REPO" "${JENKINS_HOME}/jobs/${SEED_JOB_NAME}/config.xml"; then
            log "✓ Git repository URL correctly configured"
        else
            log "✗ WARNING: Git repository URL not found in config.xml"
        fi
    else
        log "✗ WARNING: Seed job config.xml not found"
    fi
else
    log "✗ WARNING: Seed job directory not found"
fi

log "===== Seed Job Setup Completed ====="
