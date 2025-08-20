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

    static class AWSAuthenticationException extends Exception {
        AWSAuthenticationException(String message) {
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

    // ================================================================================
    // 認証関連の新機能
    // ================================================================================

    /**
     * AWS CLIがインストールされているかチェック
     * @return CLIバージョン情報またはnull
     */
    def checkAwsCli() {
        def cliCheck = script.sh(
            script: 'command -v aws || echo "not found"',
            returnStdout: true
        ).trim()
        
        if (cliCheck == "not found") {
            return null
        }
        
        return script.sh(script: 'aws --version', returnStdout: true).trim()
    }

    /**
     * AWS認証情報を検証
     * @param config 設定
     *        - accessKeyId: AWSアクセスキーID
     *        - secretAccessKey: AWSシークレットアクセスキー
     *        - sessionToken: AWSセッショントークン（オプション）
     *        - region: AWSリージョン
     *        - allowedAccountIds: 許可されたアカウントIDのリスト（オプション）
     *        - environment: 環境名（dev/prod等、ログ表示用）
     *        - requireUserConfirmation: ホワイトリスト外の場合にユーザー確認を求めるか（デフォルト: true）
     * @return 認証情報の詳細（accountId, arn, userId等を含むマップ）
     */
    def verifyAwsCredentials(Map config = [:]) {
        // 必須パラメータのチェック
        if (!config.accessKeyId || !config.secretAccessKey) {
            throw new AWSAuthenticationException("AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are required")
        }
        
        if (!config.region) {
            throw new IllegalArgumentException("AWS region is required")
        }

        // デフォルト値の設定
        def defaultConfig = [
            requireUserConfirmation: true,
            environment: 'development'
        ]
        config = defaultConfig + config

        script.echo "ℹ️ AWS認証情報が設定されています"
        script.echo "ℹ️ リージョン: ${config.region}"
        
        if (config.sessionToken) {
            script.echo "ℹ️ 一時認証情報を使用します"
        }

        // AWS CLIのチェック
        def cliVersion = checkAwsCli()
        if (!cliVersion) {
            script.echo "⚠️ AWS CLIがインストールされていません。基本的な認証チェックのみ実行します"
            return [
                verified: false,
                reason: "AWS CLI not installed"
            ]
        }
        script.echo "ℹ️ AWS CLI version: ${cliVersion}"

        // 認証情報の有効性チェック
        def callerIdentity = null
        script.withEnv([
            "AWS_ACCESS_KEY_ID=${config.accessKeyId}",
            "AWS_SECRET_ACCESS_KEY=${config.secretAccessKey}",
            "AWS_SESSION_TOKEN=${config.sessionToken ?: ''}",
            "AWS_DEFAULT_REGION=${config.region}"
        ]) {
            try {
                def identityJson = script.sh(
                    script: 'aws sts get-caller-identity --output json',
                    returnStdout: true
                ).trim()
                callerIdentity = script.readJSON(text: identityJson)
            } catch (Exception e) {
                throw new AWSAuthenticationException("""
                    AWS認証情報が無効または期限切れです
                    以下を確認してください:
                      - アクセスキーが有効であること
                      - シークレットアクセスキーが正しいこと
                      - セッショントークン（使用している場合）が期限切れでないこと
                    
                    エラー詳細: ${e.message}
                """.stripIndent())
            }
        }

        script.echo "✅ AWS認証情報の有効性確認OK"
        script.echo "ℹ️ アカウントID: ${callerIdentity.Account}"
        script.echo "ℹ️ プリンシパルARN: ${callerIdentity.Arn}"

        // アカウントIDのホワイトリストチェック
        if (config.allowedAccountIds) {
            def accountCheckResult = checkAccountWhitelist(
                callerIdentity.Account,
                config.allowedAccountIds,
                callerIdentity.Arn,
                config.environment,
                config.requireUserConfirmation
            )
            
            if (!accountCheckResult.allowed) {
                throw new AWSAuthenticationException(accountCheckResult.message)
            }
        }

        // 長期認証情報の追加情報取得（オプション）
        def keyAge = null
        if (!config.sessionToken) {
            keyAge = getAccessKeyAge(callerIdentity.Arn, config)
            if (keyAge) {
                script.echo "ℹ️ ${keyAge}"
            }
        }

        return [
            verified: true,
            accountId: callerIdentity.Account,
            arn: callerIdentity.Arn,
            userId: callerIdentity.UserId,
            keyAge: keyAge
        ]
    }

    /**
     * アカウントIDがホワイトリストに含まれているかチェック
     * @param accountId チェック対象のアカウントID
     * @param allowedAccountIds 許可されたアカウントIDのリスト
     * @param arn プリンシパルARN
     * @param environment 環境名
     * @param requireUserConfirmation ユーザー確認を求めるか
     * @return チェック結果（allowed: boolean, message: String）
     */
    private def checkAccountWhitelist(String accountId, List allowedAccountIds, String arn, 
                                    String environment, boolean requireUserConfirmation) {
        script.echo "ℹ️ ${environment}環境の確認中..."
        
        if (allowedAccountIds.contains(accountId)) {
            script.echo "✅ ${environment}環境（アカウントID: ${accountId}）であることを確認しました"
            return [allowed: true, message: "Account verified"]
        }
        
        script.echo "❌ このアカウントは${environment}環境として登録されていません"
        script.echo "❌ アカウントID: ${accountId}"
        script.echo "❌ 許可されているアカウント: ${allowedAccountIds.join(', ')}"
        
        if (requireUserConfirmation) {
            def proceed = script.input(
                message: """
                ⚠️ 警告: ${environment}環境として登録されていないアカウントです
                
                現在のアカウントID: ${accountId}
                プリンシパル: ${arn}
                許可されているアカウント: ${allowedAccountIds.join(', ')}
                
                処理を続行しますか？
                """,
                parameters: [
                    script.booleanParam(
                        name: 'PROCEED',
                        defaultValue: false,
                        description: '自己責任で続行する（推奨されません）'
                    )
                ]
            )
            
            if (proceed) {
                script.echo "⚠️ ユーザーの確認により処理を続行します"
                script.echo "⚠️ このアカウントを${environment}環境として使用する場合は、許可リストに追加してください"
                return [allowed: true, message: "User confirmed to proceed"]
            }
        }
        
        return [
            allowed: false, 
            message: "${environment}環境ではないため、処理を中止しました"
        ]
    }

    /**
     * アクセスキーの作成日時を取得
     * @param arn プリンシパルARN
     * @param config 認証設定
     * @return アクセスキーの作成日時情報（取得できない場合はnull）
     */
    private def getAccessKeyAge(String arn, Map config) {
        script.echo "ℹ️ 長期認証情報の情報を確認中..."
        
        try {
            def userName = arn.tokenize(':').last().tokenize('/').last()
            
            if (!userName) {
                return null
            }
            
            script.withEnv([
                "AWS_ACCESS_KEY_ID=${config.accessKeyId}",
                "AWS_SECRET_ACCESS_KEY=${config.secretAccessKey}",
                "AWS_DEFAULT_REGION=${config.region}"
            ]) {
                def keyInfo = script.sh(
                    script: """
                        aws iam list-access-keys --user-name "${userName}" --output json 2>/dev/null || echo "{}"
                    """,
                    returnStdout: true
                ).trim()
                
                if (keyInfo && keyInfo != "{}") {
                    def keyData = script.readJSON(text: keyInfo)
                    def accessKey = keyData.AccessKeyMetadata?.find { 
                        it.AccessKeyId == config.accessKeyId 
                    }
                    
                    if (accessKey?.CreateDate) {
                        return "Key created: ${accessKey.CreateDate}"
                    }
                }
            }
        } catch (Exception e) {
            // エラーは無視（権限がない場合など）
            script.echo "ℹ️ アクセスキー情報の取得をスキップしました: ${e.message}"
        }
        
        return null
    }

    /**
     * 開発環境のAWS認証情報を検証する便利メソッド
     * @param accessKeyId AWSアクセスキーID
     * @param secretAccessKey AWSシークレットアクセスキー
     * @param sessionToken AWSセッショントークン（オプション）
     * @param region AWSリージョン
     * @param devAccountIds 開発環境のアカウントIDリスト（オプション、指定しない場合は環境変数から取得）
     * @return 認証情報の詳細
     */
    def verifyDevAwsCredentials(String accessKeyId, String secretAccessKey, 
                               String sessionToken = null, String region = 'us-west-2',
                               List devAccountIds = null) {
        // Jenkins System環境変数から開発環境アカウントIDを取得
        if (!devAccountIds) {
            def envAccountIds = script.env.AWS_DEV_ACCOUNT_IDS
            if (!envAccountIds) {
                throw new AWSAuthenticationException(
                    "AWS_DEV_ACCOUNT_IDS environment variable is not set. " +
                    "Please configure it in Jenkins System Configuration."
                )
            }
            devAccountIds = envAccountIds.split(',').collect { it.trim() }
            
            if (devAccountIds.isEmpty()) {
                throw new AWSAuthenticationException(
                    "AWS_DEV_ACCOUNT_IDS is empty. Please provide valid account IDs."
                )
            }
        }
        
        return verifyAwsCredentials([
            accessKeyId: accessKeyId,
            secretAccessKey: secretAccessKey,
            sessionToken: sessionToken,
            region: region,
            allowedAccountIds: devAccountIds,
            environment: 'development',
            requireUserConfirmation: true
        ])
    }

    /**
     * 本番環境のAWS認証情報を検証する便利メソッド
     * @param accessKeyId AWSアクセスキーID
     * @param secretAccessKey AWSシークレットアクセスキー
     * @param sessionToken AWSセッショントークン（オプション）
     * @param region AWSリージョン
     * @param prodAccountIds 本番環境のアカウントIDリスト（オプション、指定しない場合は環境変数から取得）
     * @return 認証情報の詳細
     */
    def verifyProdAwsCredentials(String accessKeyId, String secretAccessKey,
                                String sessionToken = null, String region = 'us-west-2',
                                List prodAccountIds = null) {
        // Jenkins System環境変数から本番環境アカウントIDを取得
        if (!prodAccountIds) {
            def envAccountIds = script.env.AWS_PROD_ACCOUNT_IDS
            if (!envAccountIds) {
                throw new AWSAuthenticationException(
                    "AWS_PROD_ACCOUNT_IDS environment variable is not set. " +
                    "Please configure it in Jenkins System Configuration."
                )
            }
            prodAccountIds = envAccountIds.split(',').collect { it.trim() }
            
            if (prodAccountIds.isEmpty()) {
                throw new AWSAuthenticationException(
                    "AWS_PROD_ACCOUNT_IDS is empty. Please provide valid account IDs."
                )
            }
        }
        
        return verifyAwsCredentials([
            accessKeyId: accessKeyId,
            secretAccessKey: secretAccessKey,
            sessionToken: sessionToken,
            region: region,
            allowedAccountIds: prodAccountIds,
            environment: 'production',
            requireUserConfirmation: true
        ])
    }
    
    /**
     * カスタム環境のAWS認証情報を検証する便利メソッド
     * @param accessKeyId AWSアクセスキーID
     * @param secretAccessKey AWSシークレットアクセスキー
     * @param sessionToken AWSセッショントークン（オプション）
     * @param region AWSリージョン
     * @param environment 環境名（staging, qa等）
     * @param accountIds アカウントIDリスト（オプション、指定しない場合は環境変数から取得）
     * @return 認証情報の詳細
     */
    def verifyEnvAwsCredentials(String accessKeyId, String secretAccessKey,
                               String sessionToken = null, String region = 'us-west-2',
                               String environment, List accountIds = null) {
        // Jenkins System環境変数からアカウントIDを取得
        if (!accountIds) {
            def envVarName = "AWS_${environment.toUpperCase()}_ACCOUNT_IDS"
            def envAccountIds = script.env[envVarName]
            
            if (!envAccountIds) {
                throw new AWSAuthenticationException(
                    "${envVarName} environment variable is not set. " +
                    "Please configure it in Jenkins System Configuration."
                )
            }
            accountIds = envAccountIds.split(',').collect { it.trim() }
            
            if (accountIds.isEmpty()) {
                throw new AWSAuthenticationException(
                    "${envVarName} is empty. Please provide valid account IDs."
                )
            }
        }
        
        return verifyAwsCredentials([
            accessKeyId: accessKeyId,
            secretAccessKey: secretAccessKey,
            sessionToken: sessionToken,
            region: region,
            allowedAccountIds: accountIds,
            environment: environment,
            requireUserConfirmation: true
        ])
    }
}
