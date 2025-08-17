#!/bin/bash
# Seed Jobの存在を確認するスクリプト

set -e

JENKINS_HOME="${JENKINS_HOME:-/mnt/efs/jenkins}"
SEED_JOB_NAME="${SEED_JOB_NAME:-seed-job}"

echo "===== Checking Seed Job ====="

# ジョブディレクトリの存在確認
if [ -d "${JENKINS_HOME}/jobs/${SEED_JOB_NAME}" ]; then
    echo "SEED_JOB_EXISTS"
    echo "Seed job '${SEED_JOB_NAME}' exists"
    
    # config.xmlの存在も確認
    if [ -f "${JENKINS_HOME}/jobs/${SEED_JOB_NAME}/config.xml" ]; then
        echo "Config file found"
    fi
else
    echo "SEED_JOB_NOT_FOUND"
    echo "Seed job '${SEED_JOB_NAME}' does not exist"
fi

exit 0