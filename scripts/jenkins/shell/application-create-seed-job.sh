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

# SSM実行時のGitリポジトリパスを取得
if [ -n "$REPO_PATH" ]; then
    # SSMドキュメントから渡されたパス
    GIT_REPO_PATH="$REPO_PATH"
else
    # デフォルトパス
    GIT_REPO_PATH="${GIT_REPO_PATH:-/mnt/efs/jenkins/git-repo}"
fi

# スクリプトディレクトリの設定
if [ -d "$GIT_REPO_PATH/scripts" ]; then
    SCRIPTS_DIR="$GIT_REPO_PATH/scripts"
else
    SCRIPTS_DIR="${SCRIPTS_DIR:-/mnt/efs/jenkins/scripts}"
fi

export SCRIPTS_DIR
export GIT_REPO_PATH

log "Environment:"
log "  JENKINS_HOME: $JENKINS_HOME"
log "  GIT_REPO_PATH: $GIT_REPO_PATH"
log "  SCRIPTS_DIR: $SCRIPTS_DIR"
log "  Current directory: $(pwd)"

# プロジェクト情報を取得（環境変数またはSSMパラメータから）
PROJECT_NAME="${PROJECT_NAME:-jenkins-infra}"
ENVIRONMENT="${ENVIRONMENT:-dev}"

# デフォルト値の設定（環境変数が設定されていない場合）
SEED_JOB_NAME="${SEED_JOB_NAME:-seed-job}"

# SSMパラメータから設定を取得（オプション）
if command -v aws &> /dev/null; then
    # Gitリポジトリ設定
    if [ -z "$JENKINS_JOBS_REPO" ]; then
        JENKINS_JOBS_REPO=$(aws ssm get-parameter --name "/${PROJECT_NAME}/${ENVIRONMENT}/jenkins/jobs-repo" --query "Parameter.Value" --output text 2>/dev/null || echo "https://github.com/your-org/jenkins-job-definitions.git")
    fi
    
    if [ -z "$JENKINS_JOBS_BRANCH" ]; then
        JENKINS_JOBS_BRANCH=$(aws ssm get-parameter --name "/${PROJECT_NAME}/${ENVIRONMENT}/jenkins/jobs-branch" --query "Parameter.Value" --output text 2>/dev/null || echo "main")
    fi
else
    # SSMが使えない場合のデフォルト値
    JENKINS_JOBS_REPO="${JENKINS_JOBS_REPO:-https://github.com/your-org/jenkins-job-definitions.git}"
    JENKINS_JOBS_BRANCH="${JENKINS_JOBS_BRANCH:-main}"
fi

# その他のデフォルト値
JOB_DSL_SCRIPTS_PATH="${JOB_DSL_SCRIPTS_PATH:-jenkins/jobs/seed-job/Jenkinsfile}"
UPDATE_EXISTING_JOB="${UPDATE_EXISTING_JOB:-true}"
RUN_INITIAL_BUILD="${RUN_INITIAL_BUILD:-false}"

# 環境変数をエクスポート
export SEED_JOB_NAME
export JENKINS_JOBS_REPO
export JENKINS_JOBS_BRANCH
export JOB_DSL_SCRIPTS_PATH
export UPDATE_EXISTING_JOB
export RUN_INITIAL_BUILD

log "Configuration:"
log "  JENKINS_HOME: $JENKINS_HOME"
log "  SEED_JOB_NAME: $SEED_JOB_NAME"
log "  JENKINS_JOBS_REPO: $JENKINS_JOBS_REPO"
log "  JENKINS_JOBS_BRANCH: $JENKINS_JOBS_BRANCH"
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
# SSM実行時は現在のディレクトリがGitリポジトリのルート
CURRENT_DIR="$(pwd)"
log "Current working directory: $CURRENT_DIR"

# 相対パスでスクリプトを探す（SSMドキュメントのデフォルト動作）
if [ -f "scripts/jenkins/groovy/create-seed-job.groovy" ]; then
    GROOVY_SCRIPT="$CURRENT_DIR/scripts/jenkins/groovy/create-seed-job.groovy"
    XML_FILE="$CURRENT_DIR/scripts/jenkins/jobs/seed-job.xml"
    SCRIPTS_DIR="$CURRENT_DIR/scripts"
    log "Found scripts in Git repository at: $CURRENT_DIR"
else
    # フォールバック: 絶対パスで探す
    GIT_REPO_PATH="${GIT_REPO_PATH:-/mnt/efs/jenkins/git-repo}"
    if [ -d "$GIT_REPO_PATH" ]; then
        GROOVY_SCRIPT="$GIT_REPO_PATH/scripts/jenkins/groovy/create-seed-job.groovy"
        XML_FILE="$GIT_REPO_PATH/scripts/jenkins/jobs/seed-job.xml"
        SCRIPTS_DIR="$GIT_REPO_PATH/scripts"
    else
        # 最終フォールバック
        GROOVY_SCRIPT="/mnt/efs/jenkins/scripts/jenkins/groovy/create-seed-job.groovy"
        XML_FILE="/mnt/efs/jenkins/scripts/jenkins/jobs/seed-job.xml"
        SCRIPTS_DIR="/mnt/efs/jenkins/scripts"
    fi
fi

export SCRIPTS_DIR

log "Using Groovy script at: $GROOVY_SCRIPT"
log "Using XML file at: $XML_FILE"

if [ ! -f "$GROOVY_SCRIPT" ]; then
    log "ERROR: Groovy script not found at any of the expected locations:"
    log "  - $GIT_REPO_PATH/scripts/jenkins/groovy/create-seed-job.groovy"
    log "  - ${SCRIPTS_DIR}/jenkins/groovy/create-seed-job.groovy"
    log "  - $(pwd)/scripts/jenkins/groovy/create-seed-job.groovy"
    
    # ディレクトリ構造を確認
    log "Checking directory structure..."
    if [ -d "/mnt/efs/jenkins" ]; then
        log "Contents of /mnt/efs/jenkins:"
        ls -la /mnt/efs/jenkins/ | head -20
    fi
    
    if [ -d "$GIT_REPO_PATH" ]; then
        log "Contents of $GIT_REPO_PATH:"
        ls -la "$GIT_REPO_PATH/" | head -20
        
        if [ -d "$GIT_REPO_PATH/scripts" ]; then
            log "Contents of $GIT_REPO_PATH/scripts:"
            find "$GIT_REPO_PATH/scripts" -type f -name "*.groovy" | head -20
        fi
    fi
    
    error_exit "Groovy script not found: create-seed-job.groovy"
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

# Groovyスクリプトの実行ログを確認
log "Checking Groovy script execution logs..."
if [ -f "/var/log/jenkins/jenkins.log" ]; then
    log "Recent Jenkins logs related to seed job:"
    grep -i "seed" /var/log/jenkins/jenkins.log | tail -20 || true
    grep -i "groovy" /var/log/jenkins/jenkins.log | tail -20 || true
fi

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
