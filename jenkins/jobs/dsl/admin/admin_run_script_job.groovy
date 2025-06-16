// 共通設定を取得
def jenkinsPipelineRepo = commonSettings['jenkins-pipeline-repo']

// ジョブ設定を取得
def jobKey = 'admin_run_script_job'
def jobConfig = jenkinsJobsConfig[jobKey]

// フォルダとジョブ名を組み合わせる
def fullJobName = "Admin_Jobs/${jobConfig.name}"

// ジョブの作成
job(fullJobName) {
    displayName(jobConfig.displayName)
    description('''
        |シェルスクリプトを安全に実行するための管理者用ジョブです。
        |
        |### 注意事項
        |* built-inノードでのみ実行可能です
        |* 同時実行はできません
        '''.stripMargin())

    // ノード制限
    label('built-in')
    
    // 同時実行の制限
    concurrentBuild(false)
    
    // プロパティの設定
    properties {
        rebuild {
            autoRebuild(false)
            rebuildDisabled(false)
        }
        
        rateLimitBuilds {
            throttle {
                durationName('second')
                count(1)
                userBoost(false)
            }
        }
    }
    
    // パラメータの定義
    parameters {
        stringParam('JENKINS_ADMIN_USER', 'admin', 'Jenkins admin user name')
        nonStoredPasswordParam('JENKINS_API_TOKEN', 'Jenkins admin user api token')
        textParam('ADDITIONAL_ENV_VARS', 'Additional environment variables in KEY=VALUE format (one per line)', '')
        fileParam('script.sh', 'Upload shell script to execute')
    }
    
    // ビルドステップ
    steps {
        shell('''\
            |# 実行権限を付与
            |chmod +x ${WORKSPACE}/script.sh
            |# sedでCRLFを修正
            |sed -i 's/\r$//' ${WORKSPACE}/script.sh
            |# 追加の環境変数を設定
            |if [ ! -z "$ADDITIONAL_ENV_VARS" ]; then
            |    echo "Setting additional environment variables..."
            |    while IFS='=' read -r key value; do
            |        if [ ! -z "$key" ]; then
            |            export "$key=$value"
            |            echo "Set $key=$value"
            |        fi
            |    done <<< "$ADDITIONAL_ENV_VARS"
            |fi
            |
            |# アップロードされたシェルスクリプトを実行
            |${WORKSPACE}/script.sh
            '''.stripMargin())
    }
    
    // アーティファクトの保存
    publishers {
        archiveArtifacts {
            pattern('**/*')
            allowEmpty(true)
            onlyIfSuccessful(false)
            fingerprint(true)
            defaultExcludes(true)
            caseSensitive(true)
            followSymlinks(true)
        }
    }
}
