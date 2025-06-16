import jp.co.tielec.aws.AwsGeneralUtils
import jp.co.tielec.aws.AwsSqsUtils

/**
 * AWSユーティリティのファクトリクラス
 */
class AwsUtils implements Serializable {
    private def script
    private AwsGeneralUtils generalUtils
    private AwsSqsUtils sqsUtils

    /**
     * コンストラクタ
     * @param script Pipelineスクリプトのコンテキスト
     */
    AwsUtils(def script) {
        this.script = script
        this.generalUtils = new AwsGeneralUtils(script)
        this.sqsUtils = new AwsSqsUtils(script)
    }

    /**
     * AWS一般ユーティリティを取得
     */
    def getGeneral() {
        return generalUtils
    }

    /**
     * SQSユーティリティを取得
     */
    def getSqs() {
        return sqsUtils
    }
}

/**
 * シングルトンインスタンスを生成
 */
def call() {
    return new AwsUtils(this)
}