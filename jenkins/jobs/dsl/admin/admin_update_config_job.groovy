// 共通設定を取得
def jenkinsPipelineRepo = commonSettings['jenkins-pipeline-repo']

// ジョブ設定を取得
def jobKey = 'admin_update_config_job'
def jobConfig = jenkinsJobsConfig[jobKey]

// フォルダとジョブ名を組み合わせる
def fullJobName = "Admin_Jobs/${jobConfig.name}"

job(fullJobName) {
    displayName(jobConfig.displayName)
    description('''\
        |Jenkins Configuration as Code を使用して Jenkins の設定を更新します。
        |
        |### 主な機能
        |1. ユーザーがアップロードした jenkins.yaml ファイルを使用して Jenkins の設定を更新します。
        |2. 設定ファイルを Jenkins の適切なディレクトリにコピーします。
        |3. Jenkins Configuration as Code プラグインを使用して設定をリロードします。
        |
        |### 注意
        |* このジョブを実行するには管理者権限が必要です。
        |* 設定更新後、一部の変更を適用するために Jenkins の再起動が必要な場合があります。
        |* アップロードする設定ファイルが正しいフォーマットであることを確認してください。
        |
        |### 使用方法
        |1. jenkins.yaml ファイルをアップロードします。
        |2. Jenkins 管理者のユーザー名とAPI_TOKENを入力します。
        |3. ジョブを実行します。
        |'''.stripMargin())

    parameters {
        stringParam('JENKINS_ADMIN_USER', 'admin', 'Jenkins admin user name')
        nonStoredPasswordParam('JENKINS_API_TOKEN', 'Jenkins admin user api token')
        fileParam('JENKINS_YAML', 'アップロードする jenkins.yaml ファイル')
    }
    keepDependencies(false)

    scm {
        none()
    }

    label('built-in')

    disabled(false)
    
    logRotator {
        numToKeep(10)
    }

    triggers()
    
    concurrentBuild(false)

    steps {
        shell('''\
            |#!/bin/bash
            |set -e
            |
            |handle_error() {
            |    echo "エラーが発生しました: $1"
            |    exit 1
            |}
            |
            |echo "現在のディレクトリの内容:"
            |ls -la
            |
            |if [ ! -f "JENKINS_YAML" ]; then
            |    handle_error "設定ファイル JENKINS_YAML が見つかりません"
            |fi
            |
            |JENKINS_URL="http://localhost:8080"
            |JENKINS_HOME="${JENKINS_HOME:-/mnt/efs/jenkins}"
            |
            |echo "jenkins-cli.jar をダウンロードします"
            |wget ${JENKINS_URL}/jnlpJars/jenkins-cli.jar || handle_error "jenkins-cli.jar のダウンロードに失敗しました"
            |
            |echo "設定ファイルを Jenkins の設定ディレクトリにコピーします"
            |cp JENKINS_YAML "${JENKINS_HOME}/jenkins.yaml" || handle_error "設定ファイルのコピーに失敗しました"
            |
            |echo "CASC_JENKINS_CONFIG 環境変数を設定します"
            |export CASC_JENKINS_CONFIG="${JENKINS_HOME}/jenkins.yaml"
            |
            |echo "Jenkins の設定を更新しています..."
            |if ! java -jar jenkins-cli.jar -s ${JENKINS_URL} -auth ${JENKINS_ADMIN_USER}:${JENKINS_API_TOKEN} reload-jcasc-configuration; then
            |    echo "設定の更新中にエラーが発生しました。Jenkins ログを確認します。"
            |    tail -n 50 ${JENKINS_HOME}/logs/jenkins.log
            |    handle_error "設定の更新に失敗しました"
            |fi
            |
            |echo "Jenkins の設定が更新されました。変更を完全に適用するには Jenkins の再起動が必要な場合があります。"
            |'''.stripMargin())
    }
}
