/**
 * Infrastructure Shutdown Scheduler Job DSL
 * 
 * 日本時間午前0時に環境停止ジョブを自動実行するスケジューラージョブ
 * 既存の停止ジョブをトリガーするfreestyleジョブ
 */

def folderPath = 'Infrastructure_Management'
def jobName = 'Shutdown-Environment-Scheduler'
def fullJobName = "${folderPath}/${jobName}"

freeStyleJob(fullJobName) {
    displayName('環境自動停止スケジューラー')
    description('''
        |開発環境を毎日定時に自動停止するスケジューラージョブです。
        |
        |実行タイミング:
        |- 日本時間（JST）午前0時
        |- 平日のみ実行（月曜日〜金曜日）
        |
        |実行内容:
        |- Infrastructure_Management/Shutdown-Environment ジョブをトリガー
        |- 環境: dev
        |- モード: graceful（実行中ジョブの完了を待つ）
        |
        |注意事項:
        |- 本番環境は対象外（dev環境のみ）
        |- 週末は自動停止しません
    '''.stripMargin())

    // トリガー設定
    triggers {
        // 日本時間午前0時に実行（UTC 15:00）
        // H: Hash（負荷分散のため0-59分の間でランダムに実行）
        // 平日のみ: 1-5（月-金）
        cron('H 15 * * 1-5')  // UTC 15:00 = JST 00:00、月-金のみ
    }

    // 並行実行を無効化
    concurrentBuild(false)

    // ビルド履歴の保持設定
    logRotator {
        daysToKeep(30)      // 30日間保持
        numToKeep(90)       // 最大90ビルド保持
    }

    // ビルドステップ - 既存ジョブをトリガー
    steps {
        // Shutdown-Environment ジョブを実行
        downstreamParameterized {
            trigger('Infrastructure_Management/Shutdown-Environment') {
                // 固定パラメータを設定
                parameters {
                    predefinedProp('ENVIRONMENT', 'dev')
                    predefinedProp('AWS_REGION', 'ap-northeast-1')
                    predefinedProp('SHUTDOWN_MODE', 'graceful')
                    predefinedProp('WAIT_TIMEOUT_MINUTES', '30')
                    predefinedProp('CONFIRM_SHUTDOWN', 'true')
                    predefinedProp('DRY_RUN', 'false')
                }
                
                // ビルド結果の扱い
                block {
                    buildStepFailure('FAILURE')
                    failure('FAILURE')
                    unstable('UNSTABLE')
                }
            }
        }
    }

    // ビルドラッパー
    wrappers {
        timestamps()
        ansiColorBuildWrapper()
        
        // タイムアウト設定（停止ジョブが長引いた場合の保険）
        timeout {
            absolute(60)  // 最大60分
            failBuild()
        }
        
        // ビルド名の設定
        buildName('#${BUILD_NUMBER} - Scheduled Shutdown [dev]')
    }

    // 環境変数
    environmentVariables {
        env('TZ', 'Asia/Tokyo')
    }

    // ポストビルドアクション
    publishers {
        // ビルド結果に応じた説明を追加
        buildDescription('', '''
            |環境: dev
            |実行時刻: ${BUILD_TIMESTAMP}
            |結果: ${BUILD_STATUS}
        '''.stripMargin())
        
        // 必要に応じてメール通知を追加
        /*
        mailer('devops-team@example.com', false, true)
        */
    }
}