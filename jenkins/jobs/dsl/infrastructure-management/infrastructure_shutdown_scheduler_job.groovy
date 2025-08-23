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
        |- 毎日実行（土日祝日含む）
        |
        |実行内容:
        |- Infrastructure_Management/Shutdown_Jenkins_Environment ジョブをトリガー
        |- 環境: dev
        |- モード: graceful（実行中ジョブの完了を待つ）
        |
        |注意事項:
        |- 本番環境は対象外（dev環境のみ）
        |- 土日祝日も含めて毎日自動停止します
    '''.stripMargin())

    // トリガー設定
    triggers {
        // 日本時間午前0時に実行（UTC 15:00）
        // H: Hash（負荷分散のため0-59分の間でランダムに実行）
        // 毎日実行: *（全曜日）
        cron('H 15 * * *')  // UTC 15:00 = JST 00:00、毎日
    }

    // 並行実行を無効化
    concurrentBuild(false)

    // ビルド履歴の保持設定
    logRotator {
        daysToKeep(30)      // 30日間保持
        numToKeep(90)       // 最大90ビルド保持
    }

    // ビルドステップは空（ポストビルドで実行するため）
    steps {
        shell('echo "環境停止ジョブをトリガーします..."')
    }
    
    // ポストビルドアクション - 非同期でジョブをトリガー
    publishers {
        // 他のジョブをトリガー（待機なし）
        downstreamParameterized {
            trigger('Infrastructure_Management/Shutdown_Jenkins_Environment') {
                // 条件: 常に実行
                condition('ALWAYS')
                
                // 固定パラメータを設定
                parameters {
                    predefinedProp('ENVIRONMENT', 'dev')
                    predefinedProp('AWS_REGION', 'ap-northeast-1')
                    predefinedProp('SHUTDOWN_MODE', 'graceful')
                    predefinedProp('WAIT_TIMEOUT_MINUTES', '30')
                    booleanParam('CONFIRM_SHUTDOWN', true)
                    booleanParam('DRY_RUN', false)
                }
                
                // 結果を待たない（非同期実行）
                triggerWithNoParameters(false)
            }
        }
    }

    // ビルドラッパー
    wrappers {
        timestamps()
        
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
}