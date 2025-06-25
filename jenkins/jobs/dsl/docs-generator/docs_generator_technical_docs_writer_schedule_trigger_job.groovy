// YAMLから渡されたjenkinsManagedRepositoriesを使用してリポジトリ情報を構築
def repositories = jenkinsManagedRepositories.collect { name, repo ->
    [
        name: name,
        url: repo.httpsUrl,  // HTTPSのURLを使用
        branch: repo.mainBranch
    ]
}

// 共通設定を定義するメソッド
def createTechnicalDocsWriterTriggerJob(repoConfig) {
    // 共通設定を取得
    def jenkinsPipelineRepo = commonSettings['jenkins-pipeline-repo']
    
    // ジョブ設定を取得（このDSLファイル自体の設定）
    def jobKey = 'docs_generator_technical_docs_writer_schedule_trigger_job'
    def jobConfig = jenkinsJobsConfig[jobKey]
    
    // ジョブ名を新しい構造に合わせて調整
    def jobName = "Document_Generator/${repoConfig.name}/${jobConfig.name}"
    def downstreamJob = "Document_Generator/${repoConfig.name}/${jobConfig.downstreamJob}"
    
    job(jobName) {
        // ジョブの説明
        description("""\
            |# 技術ドキュメント生成トリガージョブ
            |
            |## 概要
            |毎週月曜日の朝6時（日本時間）に technical-docs-writer ジョブを自動実行します。
            |
            |## 対象リポジトリ
            |* リポジトリ: [${repoConfig.name}](${repoConfig.url})
            |* ブランチ: ${repoConfig.branch}
            |
            |## トリガー実行タイミング
            |* 毎週月曜日朝6時（日本時間）
            |
            |## トリガー対象
            |* ジョブ: ${downstreamJob}
            |* パラメータ: 
            |  - GIT_TARGET_BRANCH: ${repoConfig.branch}
            |  - START_DATE: 実行時の1週間前の日付（自動計算）
            |
            |## 関連リソース
            |* 技術ドキュメント生成ジョブ: ${downstreamJob}
            |""".stripMargin())
        
        // 依存関係の保持設定
        keepDependencies(false)
        disabled(true) // 初期状態では無効化

        
        // ログローテーション設定
        logRotator {
            daysToKeep(30)
            numToKeep(50)
        }
        
        // 同時実行制御
        throttleConcurrentBuilds {
            maxTotal(1)
            throttleDisabled(false)
        }
        
        // プロパティ設定
        properties {
            // GitHub Project設定
            githubProjectUrl("${repoConfig.url}/")
            
            // リビルド設定
            rebuild {
                autoRebuild(false)
                rebuildDisabled(false)
            }
        }
        
        // 日本時間での設定を考慮
        triggers {
            // 毎週月曜日朝6時（日本時間）に実行
            // JSTはUTC+9なので、UTC時間で日曜日21時に設定
            cron('H 21 * * 0')
        }
        
        // ビルドステップ
        steps {
            // 1週間前の日付を計算してパラメータを設定
            shell("""#!/bin/bash
                |# 1週間前の日付を計算（YYYY-MM-DD形式）
                |START_DATE=\$(date -d "7 days ago" +"%Y-%m-%d")
                |
                |# パラメータをファイルに出力
                |cat > env.properties <<EOF
                |START_DATE=\${START_DATE}
                |REPOSITORY_NAME=${repoConfig.name}
                |REPOSITORY_URL=${repoConfig.url}
                |GIT_TARGET_BRANCH=${repoConfig.branch}
                |EOF
                |
                |echo "=========================================="
                |echo "技術ドキュメント生成パラメータ:"
                |echo "リポジトリ: ${repoConfig.name}"
                |echo "ブランチ: ${repoConfig.branch}"
                |echo "開始日: \${START_DATE}"
                |echo "=========================================="
                |""".stripMargin())
            
            // 環境変数を読み込む
            environmentVariables {
                propertiesFile('env.properties')
            }
            
            // technical-docs-writerジョブをトリガー
            downstreamParameterized {
                trigger(downstreamJob) {
                    parameters {
                        predefinedProp('GIT_TARGET_BRANCH', '${GIT_TARGET_BRANCH}')
                        predefinedProp('START_DATE', '${START_DATE}')
                    }
                    block {
                        buildStepFailure('FAILURE')
                        failure('FAILURE')
                        unstable('UNSTABLE')
                    }
                }
            }
        }
        
        // ジョブの無効化状態
        disabled(true)
    }
}

// 各リポジトリのジョブを作成
repositories.each { repo ->
    createTechnicalDocsWriterTriggerJob(repo)
}
