// 共通設定を取得
def jenkinsPipelineRepo = commonSettings['jenkins-pipeline-repo']

// ジョブ設定を取得
def jobKey = 'admin_test_ec2_fleet_job'
def jobConfig = jenkinsJobsConfig[jobKey]

// フォルダとジョブ名を組み合わせる
def fullJobName = "Admin_Jobs/${jobConfig.name}"

job(fullJobName) {
    displayName(jobConfig.displayName)
    description('''\
        |EC2 Fleet プラグインで作成された Jenkins エージェントの動作確認用ジョブです。
        |
        |### 収集する情報
        |* システム情報
        |    * ホスト名
        |    * OS・カーネル
        |    * CPU・メモリ
        |    * ディスク使用量
        |* ネットワーク情報（IPアドレス）
        |* インストール済みソフトウェア
        |    * Java
        |    * Git
        |    * Docker
        |    * AWS CLI
        |* 環境変数
        |
        |### 注意事項
        |* EC2 Fleet エージェント上でのみ実行可能です
        |* 実行結果はビルドログに出力されます
        |'''.stripMargin())

    // EC2 Fleet エージェントでのみ実行
    label('ec2-fleet')

    // ログローテーション設定
    logRotator {
        numToKeep(10)
    }

    // 同時実行を許可しない
    concurrentBuild(false)

    steps {
        shell('''\
            |#!/bin/bash
            |echo "EC2 Fleet Agent 情報:"
            |echo "------------------------"
            |
            |# システム情報
            |echo "ホスト名: $(hostname)"
            |echo "OS: $(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)"
            |echo "カーネル: $(uname -r)"
            |echo "CPU: $(lscpu | grep 'Model name' | cut -d':' -f2 | xargs)"
            |echo "メモリ: $(free -h | awk '/^Mem:/ {print $2}')"
            |# ディスク情報（詳細表示）
            |echo "ディスク情報:"
            |echo ""
            |echo "■ マウントポイント別使用状況:"
            |df -h | awk 'NR==1 {print "  " $0} NR>1 {print "  " $0}'
            |echo ""
            |echo "■ ディレクトリ別使用量 (上位10):"
            |du -h / 2>/dev/null | sort -rh | head -10 | awk '{print "  " $0}'
            |echo ""
            |echo "■ /var ディレクトリの詳細:"
            |du -h /var 2>/dev/null | sort -rh | head -10 | awk '{print "  " $0}'
            |echo ""
            |echo "■ /tmp ディレクトリの詳細:"
            |du -h /tmp 2>/dev/null | sort -rh | head -10 | awk '{print "  " $0}'
            |echo ""
            |echo "■ Jenkinsワークスペースの使用量:"
            |if [ -d "${WORKSPACE}" ]; then
            |    du -sh "${WORKSPACE}" 2>/dev/null | awk '{print "  " $0}'
            |else
            |    echo "  ワークスペースが存在しません"
            |fi
            |echo ""
            |echo "■ iノード使用状況:"
            |df -i | awk 'NR==1 {print "  " $0} /\\/$/ {print "  " $0}'
            |
            |# ネットワーク情報
            |echo "IPアドレス: $(hostname -I | awk '{print $1}')"
            |
            |# Java情報
            |if command -v java &> /dev/null; then
            |    echo "Java バージョン: $(java -version 2>&1 | awk -F '"' '/version/ {print $2}')"
            |else
            |    echo "Java がインストールされていません"
            |fi
            |
            |# Git情報
            |if command -v git &> /dev/null; then
            |    echo "Git バージョン: $(git --version | awk '{print $3}')"
            |else
            |    echo "Git がインストールされていません"
            |fi
            |
            |# Docker情報
            |if command -v docker &> /dev/null; then
            |    echo "Docker バージョン: $(docker --version | awk '{print $3}')"
            |else
            |    echo "Docker がインストールされていません"
            |fi
            |
            |# AWS CLI情報
            |if command -v aws &> /dev/null; then
            |    echo "AWS CLI バージョン: $(aws --version 2>&1 | awk '{print $1}' | cut -d'/' -f2)"
            |else
            |    echo "AWS CLI がインストールされていません"
            |fi
            |
            |# 環境変数
            |echo "環境変数:"
            |env | sort
            |
            |echo "------------------------"
            |echo "EC2 Fleet Agent チェック完了"
            |'''.stripMargin())
    }

    // ビルド後の処理
    publishers {
        // ビルドログの保存
        archiveArtifacts {
            pattern('*.log')
            allowEmpty(true)
            onlyIfSuccessful(false)
        }
    }
}
