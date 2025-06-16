// 共通設定を取得
def jenkinsPipelineRepo = commonSettings['jenkins-pipeline-repo']

// ジョブ設定を取得
def jobKey = 'admin_convert_key_job'
def jobConfig = jenkinsJobsConfig[jobKey]

// フォルダとジョブ名を組み合わせる
def fullJobName = "Admin_Jobs/${jobConfig.name}"

job(fullJobName) {
    displayName(jobConfig.displayName)
    description('''
        |GitHub Apps で使用するプライベートキーのフォーマットを変換するジョブです。
        |
        |### 機能
        |* GitHub Apps のRSAプライベートキー（PKCS#1形式）をPKCS#8形式に変換
        |* Jenkins の GitHub App 認証用のキーフォーマットに変換
        |
        |### 使用手順
        |1. GitHub Apps からダウンロードしたプライベートキーを入力として使用
        |2. 変換されたキーを Jenkins の認証情報として設定
        |
        |### セキュリティ注意事項
        |* ジョブ実行後は実行履歴を必ず削除してください
        |* 変換されたキーは安全に保管し、不要な場合は確実に破棄してください
        '''.stripMargin())       
    parameters {
        fileParam('INPUT_KEY', 'GitHub Apps から取得したプライベートキーファイル')
    }

    // 同時実行を防止
    concurrentBuild(false)

    // ログローテーション設定
    logRotator {
        numToKeep(5)
        artifactNumToKeep(1)
    }

    steps {
        shell('''\
            |#!/bin/bash
            |set -ex
            |
            |# 現在のディレクトリの内容を表示
            |echo "Current directory contents:"
            |ls -la
            |
            |# 環境変数の表示
            |echo "Environment variables:"
            |env
            |
            |# 入力ファイルの確認
            |echo "Input file contents:"
            |cat INPUT_KEY
            |
            |# 入力ファイルを保存
            |cp INPUT_KEY input_key.pem
            |
            |# OpenSSLを使用して変換
            |openssl pkcs8 -topk8 -inform PEM -outform PEM -in input_key.pem -out output_key.pem -nocrypt
            |
            |# 結果を表示
            |echo "変換結果:"
            |cat output_key.pem
            |
            |# 結果をアーティファクトとして保存
            |mv output_key.pem "$WORKSPACE/converted_key.pem"
            |'''.stripMargin())
    }

    publishers {
        archiveArtifacts {
            pattern('converted_key.pem')
            allowEmpty(false)
            onlyIfSuccessful(true)  // 成功時のみ保存
            fingerprint(false)
            defaultExcludes(true)
        }
    }

    wrappers {
        // ビルド前にワークスペースをクリーンアップ
        preBuildCleanup {
            deleteDirectories(false)
            cleanupParameter('')
        }
    }
}
