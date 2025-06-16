package jp.co.tielec.aws

/**
 * AWS操作に関する汎用的なユーティリティクラス
 */
class AwsGeneralUtils implements Serializable {
    private def script

    /**
     * コンストラクタ
     * @param script Pipelineスクリプトのコンテキスト
     */
    AwsGeneralUtils(def script) {
        this.script = script
    }

    static class AWSOperationException extends Exception {
        AWSOperationException(String message) {
            super(message)
        }
    }

    /**
     * ARNを構築する
     */
    String buildArn(String service, String resourceId, Map config = [:]) {
        if (!service?.trim()) throw new IllegalArgumentException("Service name is required")
        if (!resourceId?.trim()) throw new IllegalArgumentException("Resource ID is required")

        def arnParts = ["arn:aws:${service}"]
        
        if (service == 'iam') {
            arnParts << ''  // IAMはグローバルサービス
        } else if (config.region) {
            arnParts << config.region
        } else {
            arnParts << "*"
        }
        
        if (config.accountId) {
            arnParts << config.accountId
        } else {
            arnParts << "*"
        }
        
        arnParts << resourceId
        
        return arnParts.join(":")
    }

    /**
     * AWSロールを引き受ける
     * @param roleArn 引き受けるロールのARN
     * @param serviceName サービス名（セッション名の生成に使用）
     * @param config 追加設定
     *        - externalId: 外部ID
     *        - durationSeconds: セッション時間（デフォルト: 3600）
     *        - environment: 環境名（デフォルト: prd）
     * @return AWS認証情報
     */
    def assumeRole(String roleArn, String serviceName, Map config = [:]) {
        if (!roleArn?.trim()) throw new IllegalArgumentException("Role ARN is required")
        if (!serviceName?.trim()) throw new IllegalArgumentException("Service name is required")

        // デフォルト値の設定
        def defaultConfig = [
            durationSeconds: 3600,
            environment: 'prd'
        ]
        config = defaultConfig + config

        def sessionName = "${serviceName}SQSCheck-${script.BUILD_NUMBER}"
        def accountId = roleArn.split(':')[4]  // ARNからアカウントIDを抽出
        def externalId = "${accountId}-${config.environment}"

        try {
            def assumeRoleCmd = """
                aws sts assume-role \
                    --role-arn ${roleArn} \
                    --role-session-name ${sessionName} \
                    --external-id ${externalId} \
                    --duration-seconds ${config.durationSeconds} \
                    --output json
            """
            
            def result = script.sh(script: assumeRoleCmd, returnStdout: true).trim()
            return script.readJSON(text: result)
        } catch (Exception e) {
            throw new AWSOperationException("Failed to assume role: ${e.message}")
        }
    }

    /**
     * AWS認証情報を使用して処理を実行
     */
    def withAWSCredentials(Map credentials, String region, Closure body) {
        if (!credentials?.Credentials) throw new IllegalArgumentException("Invalid AWS credentials")
        if (!region?.trim()) throw new IllegalArgumentException("AWS region is required")

        script.withEnv([
            "AWS_ACCESS_KEY_ID=${credentials.Credentials.AccessKeyId}",
            "AWS_SECRET_ACCESS_KEY=${credentials.Credentials.SecretAccessKey}",
            "AWS_SESSION_TOKEN=${credentials.Credentials.SessionToken}",
            "AWS_DEFAULT_REGION=${region}"
        ]) {
            body()
        }
    }

    /**
     * AWS CLIコマンドを実行
     */
    def executeAwsCommand(String command, Map config = [:]) {
        if (!command?.trim()) throw new IllegalArgumentException("Command is required")

        try {
            def result = script.sh(
                script: command,
                returnStdout: true
            ).trim()
            return result
        } catch (Exception e) {
            throw new AWSOperationException("Failed to execute AWS command: ${e.message}")
        }
    }
}