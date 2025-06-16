package jp.co.tielec.aws

/**
 * SQS操作に関するユーティリティクラス
 */
class AwsSqsUtils implements Serializable {
    private def script
    private AwsGeneralUtils awsGeneralUtils

    /**
     * コンストラクタ
     * @param script Pipelineスクリプトのコンテキスト
     */
    AwsSqsUtils(def script) {
        this.script = script
        this.awsGeneralUtils = new AwsGeneralUtils(script)
    }

    /**
     * SQS操作に関する例外クラス
     */
    static class SQSOperationException extends Exception {
        SQSOperationException(String message) {
            super(message)
        }
    }

    /**
     * SQSキューのURLを取得する
     * @param queueName キュー名
     * @param region AWSリージョン
     * @return キューのURL
     */
    String getQueueUrl(String queueName, String region) {
        if (!queueName?.trim()) throw new IllegalArgumentException("Queue name is required")
        if (!region?.trim()) throw new IllegalArgumentException("Region is required")

        try {
            def result = awsGeneralUtils.executeAwsCommand("""
                aws sqs get-queue-url \
                --queue-name ${queueName} \
                --region ${region} \
                --output json
            """)
            return script.readJSON(text: result).QueueUrl
        } catch (Exception e) {
            script.echo "Failed to get queue URL for ${queueName}: ${e.message}"
            return null
        }
    }

    /**
     * プレフィックスに一致するSQSキューの一覧を取得する
     * @param prefix キュー名のプレフィックス
     * @param region AWSリージョン
     * @return キューURLのリスト
     */
    List<String> listQueuesByPrefix(String prefix, String region) {
        if (!prefix?.trim()) throw new IllegalArgumentException("Prefix is required")
        if (!region?.trim()) throw new IllegalArgumentException("Region is required")

        try {
            def result = awsGeneralUtils.executeAwsCommand("""
                aws sqs list-queues \
                --queue-name-prefix ${prefix} \
                --region ${region} \
                --output json
            """)
            return script.readJSON(text: result).QueueUrls ?: []
        } catch (Exception e) {
            throw new SQSOperationException("Failed to list queues: ${e.message}")
        }
    }

    /**
     * SQSキューの属性を取得する
     * @param queueUrl キューのURL
     * @param attributes 取得する属性のリスト
     * @return キューの属性
     */
    Map getQueueAttributes(String queueUrl, List attributes = ['All']) {
        if (!queueUrl?.trim()) throw new IllegalArgumentException("Queue URL is required")

        try {
            def attrList = attributes.join(' ')
            def result = awsGeneralUtils.executeAwsCommand("""
                aws sqs get-queue-attributes \
                --queue-url ${queueUrl} \
                --attribute-names ${attrList} \
                --output json
            """)
            return script.readJSON(text: result).Attributes
        } catch (Exception e) {
            throw new SQSOperationException("Failed to get queue attributes: ${e.message}")
        }
    }

    /**
     * SQSキューのメッセージ数を取得する
     * @param queueUrl キューのURL
     * @return メッセージ数の情報
     */
    Map getQueueMessageCounts(String queueUrl) {
        if (!queueUrl?.trim()) throw new IllegalArgumentException("Queue URL is required")

        try {
            def attrs = getQueueAttributes(
                queueUrl, 
                ['ApproximateNumberOfMessages', 'ApproximateNumberOfMessagesNotVisible']
            )
            
            def availableCount = attrs.ApproximateNumberOfMessages as Integer
            def processingCount = attrs.ApproximateNumberOfMessagesNotVisible as Integer
            
            return [
                availableCount: availableCount,
                processingCount: processingCount,
                totalCount: availableCount + processingCount
            ]
        } catch (Exception e) {
            throw new SQSOperationException("Failed to get message counts: ${e.message}")
        }
    }

    /**
     * DLQかどうかを判定する
     * @param queueName キュー名
     * @return DLQの場合はtrue
     */
    boolean isDLQ(String queueName) {
        if (!queueName?.trim()) return false
        def lowerName = queueName.toLowerCase()
        return lowerName.contains('dlq') || lowerName.contains('deadletter')
    }

    /**
     * SQSキューの完全なステータスを取得する
     * @param queueUrl キューのURL
     * @param config 追加設定（includeMessageAttributes, includeTags）
     * @return キューの詳細情報
     */
    Map getQueueStatus(String queueUrl, Map config = [:]) {
        if (!queueUrl?.trim()) throw new IllegalArgumentException("Queue URL is required")

        def defaultConfig = [
            includeMessageAttributes: false,
            includeTags: false
        ]
        config = defaultConfig + config

        def status = [:]
        
        // 基本的なメッセージ数を取得
        status += getQueueMessageCounts(queueUrl)
        
        // キューの基本属性を取得
        def attributes = getQueueAttributes(queueUrl)
        status.createdTimestamp = attributes.CreatedTimestamp
        status.lastModifiedTimestamp = attributes.LastModifiedTimestamp
        status.visibilityTimeout = attributes.VisibilityTimeout
        
        // メッセージ属性を取得（オプション）
        if (config.includeMessageAttributes) {
            status.messageAttributes = getQueueAttributes(
                queueUrl, 
                ['MessageRetentionPeriod', 'MaximumMessageSize']
            )
        }
        
        // タグを取得（オプション）
        if (config.includeTags) {
            try {
                def tagsResult = awsGeneralUtils.executeAwsCommand("""
                    aws sqs list-queue-tags \
                    --queue-url ${queueUrl} \
                    --output json
                """)
                status.tags = script.readJSON(text: tagsResult).Tags ?: [:]
            } catch (Exception e) {
                script.echo "Warning: Failed to get queue tags: ${e.message}"
                status.tags = [:]
            }
        }
        
        return status
    }
}