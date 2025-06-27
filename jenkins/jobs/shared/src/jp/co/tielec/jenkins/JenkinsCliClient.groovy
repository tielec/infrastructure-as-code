package jp.co.tielec.jenkins

/**
 * Jenkins CLI操作の内部実装クラス
 */
class JenkinsCliClient {
    
    private def steps
    private def env
    
    /**
     * コンストラクタ
     * @param steps Jenkinsパイプラインのstepsオブジェクト
     * @param env Jenkins環境変数
     */
    JenkinsCliClient(def steps, def env) {
        this.steps = steps
        this.env = env
    }
    
    /**
     * Jenkins CLIをセットアップする
     * @param jenkinsUrl JenkinsのURL
     * @return CLIのパス
     */
    String setupCli(String jenkinsUrl) {
        if (!jenkinsUrl?.trim()) {
            throw new IllegalArgumentException("Jenkins URL is required")
        }

        // URLの末尾のスラッシュを除去
        jenkinsUrl = jenkinsUrl.replaceAll('/+$', '')

        steps.sh """
            curl -O '${jenkinsUrl}/jnlpJars/jenkins-cli.jar'
            chmod +x jenkins-cli.jar
        """
        return 'jenkins-cli.jar'
    }
    
    /**
     * Jenkins CLIコマンドを実行する
     * @param command 実行するコマンド
     * @param config 設定オプション
     *        - jenkinsUrl: JenkinsのURL
     *        - credentialsId: 認証情報ID
     *        - inputFile: 入力ファイルのパス
     *        - outputFile: 出力ファイルのパス
     *        - timeout: タイムアウト時間（分）
     *        - useHttp: HTTP接続を使用するか（デフォルト: true）
     *        - authMethod: 認証方式 ('auto', 'token', 'password')（デフォルト: 'auto'）
     *        - username: APIトークン使用時のユーザー名
     */
    def executeCommand(String command, Map config = [:]) {
        if (!command?.trim()) {
            throw new IllegalArgumentException("Command is required")
        }

        def defaultConfig = [
            jenkinsUrl: env.JENKINS_URL,
            credentialsId: 'cli-user-token',
            timeout: 5,
            useHttp: true,  // デフォルトでHTTP接続を使用
            authMethod: 'auto'  // デフォルトで自動判定
        ]
        config = defaultConfig + config

        validateConfig(config)
        
        // Jenkins CLIがセットアップされているか確認
        if (!steps.fileExists('jenkins-cli.jar')) {
            steps.echo "Jenkins CLI not found. Setting up..."
            setupCli(config.jenkinsUrl)
        }

        // authMethod が 'auto' の場合、Credentialの型を自動判定
        if (config.authMethod == 'auto') {
            try {
                // まずUsernamePasswordとして試す
                return steps.withCredentials([steps.usernamePassword(
                    credentialsId: config.credentialsId,
                    usernameVariable: 'USER',
                    passwordVariable: 'PASS'
                )]) {
                    steps.echo "Using UsernamePassword credential type"
                    config.authMethod = 'password'
                    steps.timeout(time: config.timeout, unit: 'MINUTES') {
                        executeCliCommand(command, config)
                    }
                }
            } catch (Exception e) {
                // UsernamePasswordで失敗したら、Secret textとして試す
                steps.echo "UsernamePassword failed, trying Secret text: ${e.message}"
                return steps.withCredentials([steps.string(
                    credentialsId: config.credentialsId,
                    variable: 'JENKINS_API_TOKEN'
                )]) {
                    steps.echo "Using Secret text credential type"
                    config.authMethod = 'token'
                    def username = config.username ?: 'cli-user'
                    steps.withEnv(["JENKINS_USER=${username}"]) {
                        steps.timeout(time: config.timeout, unit: 'MINUTES') {
                            executeCliCommand(command, config)
                        }
                    }
                }
            }
        } else if (config.authMethod == 'token') {
            // 明示的にAPIトークンの場合
            return steps.withCredentials([steps.string(
                credentialsId: config.credentialsId,
                variable: 'JENKINS_API_TOKEN'
            )]) {
                def username = config.username ?: 'cli-user'
                steps.withEnv(["JENKINS_USER=${username}"]) {
                    steps.timeout(time: config.timeout, unit: 'MINUTES') {
                        executeCliCommand(command, config)
                    }
                }
            }
        } else {
            // 明示的にユーザー名/パスワードの場合
            return steps.withCredentials([steps.usernamePassword(
                credentialsId: config.credentialsId,
                usernameVariable: 'USER',
                passwordVariable: 'PASS'
            )]) {
                steps.timeout(time: config.timeout, unit: 'MINUTES') {
                    executeCliCommand(command, config)
                }
            }
        }
    }
    
    /**
     * 設定をエクスポートする
     * @param outputFile 出力ファイルパス
     * @param config 設定オプション
     */
    def exportConfiguration(String outputFile, Map config = [:]) {
        if (!outputFile?.trim()) {
            throw new IllegalArgumentException("Output file path is required")
        }

        config.outputFile = outputFile
        executeCommand('export-configuration', config)
    }
    
    /**
     * 設定を検証する
     * @param configFile 設定ファイルパス
     * @param config 設定オプション
     */
    def checkConfiguration(String configFile, Map config = [:]) {
        if (!steps.fileExists(configFile)) {
            throw new JenkinsCliException("Configuration file not found: ${configFile}")
        }

        config.inputFile = configFile
        executeCommand('check-configuration', config)
    }
    
    /**
     * JCasCの設定をリロードする
     * @param config 設定オプション
     */
    def reloadJCasCConfiguration(Map config = [:]) {
        executeCommand('reload-jcasc-configuration', config)
    }
    
    /**
     * Jenkinsを安全に再起動する
     * @param config 設定オプション
     */
    def safeRestart(Map config = [:]) {
        config.timeout = config.timeout ?: 10  // 再起動は長めのタイムアウトを設定
        executeCommand('safe-restart', config)
    }
    
    // Credentials関連メソッド
    
    /**
     * Credentialsをリスト表示
     * @param store Store ID (例: system::system::jenkins)
     * @param config 設定オプション
     * @return コマンドの出力
     */
    def listCredentials(String store, Map config = [:]) {
        if (!store?.trim()) {
            throw new IllegalArgumentException("Store ID is required")
        }
        return executeCommand("list-credentials '${store}'", config)
    }
    
    /**
     * CredentialsをXML形式でリスト表示
     * @param store Store ID
     * @param domain Domain名（オプション）
     * @param config 設定オプション
     * @return XML形式の出力
     */
    def listCredentialsAsXml(String store, String domain = null, Map config = [:]) {
        if (!store?.trim()) {
            throw new IllegalArgumentException("Store ID is required")
        }
        def command = "list-credentials-as-xml '${store}'"
        if (domain?.trim()) {
            command += " '${domain}'"
        }
        return executeCommand(command, config)
    }
    
    /**
     * 特定のCredentialをXML形式で取得
     * @param store Store ID
     * @param domain Domain名
     * @param credentialId Credential ID
     * @param config 設定オプション
     * @return XML形式の出力
     */
    def getCredentialAsXml(String store, String domain, String credentialId, Map config = [:]) {
        if (!store?.trim() || !domain?.trim() || !credentialId?.trim()) {
            throw new IllegalArgumentException("Store ID, domain and credential ID are required")
        }
        return executeCommand("get-credentials-as-xml '${store}' '${domain}' '${credentialId}'", config)
    }
    
    /**
     * XMLからCredentialを作成
     * @param store Store ID
     * @param domain Domain名
     * @param xmlFile XMLファイルパス
     * @param config 設定オプション
     */
    def createCredentialByXml(String store, String domain, String xmlFile, Map config = [:]) {
        if (!store?.trim() || !domain?.trim()) {
            throw new IllegalArgumentException("Store ID and domain are required")
        }
        if (!steps.fileExists(xmlFile)) {
            throw new JenkinsCliException("XML file not found: ${xmlFile}")
        }
        config.inputFile = xmlFile
        executeCommand("create-credentials-by-xml '${store}' '${domain}'", config)
    }
    
    /**
     * XMLからCredentialを更新
     * @param store Store ID
     * @param domain Domain名
     * @param credentialId Credential ID
     * @param xmlFile XMLファイルパス
     * @param config 設定オプション
     */
    def updateCredentialByXml(String store, String domain, String credentialId, String xmlFile, Map config = [:]) {
        if (!store?.trim() || !domain?.trim() || !credentialId?.trim()) {
            throw new IllegalArgumentException("Store ID, domain and credential ID are required")
        }
        if (!steps.fileExists(xmlFile)) {
            throw new JenkinsCliException("XML file not found: ${xmlFile}")
        }
        config.inputFile = xmlFile
        executeCommand("update-credentials-by-xml '${store}' '${domain}' '${credentialId}'", config)
    }
    
    /**
     * Credentialを削除
     * @param store Store ID
     * @param domain Domain名
     * @param credentialId Credential ID
     * @param config 設定オプション
     */
    def deleteCredential(String store, String domain, String credentialId, Map config = [:]) {
        if (!store?.trim() || !domain?.trim() || !credentialId?.trim()) {
            throw new IllegalArgumentException("Store ID, domain and credential ID are required")
        }
        executeCommand("delete-credentials '${store}' '${domain}' '${credentialId}'", config)
    }
    
    /**
     * CredentialsをXML形式でインポート
     * @param store Store ID
     * @param xmlFile XMLファイルパス
     * @param domain Domain名（オプション）
     * @param config 設定オプション
     */
    def importCredentialsAsXml(String store, String xmlFile, String domain = null, Map config = [:]) {
        if (!store?.trim()) {
            throw new IllegalArgumentException("Store ID is required")
        }
        if (!steps.fileExists(xmlFile)) {
            throw new JenkinsCliException("XML file not found: ${xmlFile}")
        }
        config.inputFile = xmlFile
        def command = "import-credentials-as-xml '${store}'"
        if (domain?.trim()) {
            command += " '${domain}'"
        }
        executeCommand(command, config)
    }
    
    /**
     * Credentials Domainを作成
     * @param store Store ID
     * @param xmlFile Domain定義のXMLファイルパス
     * @param config 設定オプション
     */
    def createCredentialsDomainByXml(String store, String xmlFile, Map config = [:]) {
        if (!store?.trim()) {
            throw new IllegalArgumentException("Store ID is required")
        }
        if (!steps.fileExists(xmlFile)) {
            throw new JenkinsCliException("XML file not found: ${xmlFile}")
        }
        config.inputFile = xmlFile
        executeCommand("create-credentials-domain-by-xml '${store}'", config)
    }
    
    /**
     * Credentials DomainをXML形式で取得
     * @param store Store ID
     * @param domain Domain名
     * @param config 設定オプション
     * @return XML形式の出力
     */
    def getCredentialsDomainAsXml(String store, String domain, Map config = [:]) {
        if (!store?.trim() || !domain?.trim()) {
            throw new IllegalArgumentException("Store ID and domain are required")
        }
        return executeCommand("get-credentials-domain-as-xml '${store}' '${domain}'", config)
    }
    
    /**
     * Credentials Domainを更新
     * @param store Store ID
     * @param domain Domain名
     * @param xmlFile Domain定義のXMLファイルパス
     * @param config 設定オプション
     */
    def updateCredentialsDomainByXml(String store, String domain, String xmlFile, Map config = [:]) {
        if (!store?.trim() || !domain?.trim()) {
            throw new IllegalArgumentException("Store ID and domain are required")
        }
        if (!steps.fileExists(xmlFile)) {
            throw new JenkinsCliException("XML file not found: ${xmlFile}")
        }
        config.inputFile = xmlFile
        executeCommand("update-credentials-domain-by-xml '${store}' '${domain}'", config)
    }
    
    /**
     * Credentials Domainを削除
     * @param store Store ID
     * @param domain Domain名
     * @param config 設定オプション
     */
    def deleteCredentialsDomain(String store, String domain, Map config = [:]) {
        if (!store?.trim() || !domain?.trim()) {
            throw new IllegalArgumentException("Store ID and domain are required")
        }
        executeCommand("delete-credentials-domain '${store}' '${domain}'", config)
    }
    
    /**
     * Credentials Providersをリスト表示
     * @param config 設定オプション
     * @return プロバイダーリスト
     */
    def listCredentialsProviders(Map config = [:]) {
        return executeCommand("list-credentials-providers", config)
    }
    
    /**
     * Credentials Context Resolversをリスト表示
     * @param config 設定オプション
     * @return リゾルバーリスト
     */
    def listCredentialsContextResolvers(Map config = [:]) {
        return executeCommand("list-credentials-context-resolvers", config)
    }
    
    /**
     * プログラマティックにCredentialを作成するヘルパーメソッド
     * @param store Store ID
     * @param domain Domain名
     * @param credentialData Credential情報のMap
     * @param config 設定オプション
     */
    def createCredential(String store, String domain, Map credentialData, Map config = [:]) {
        def xmlContent = buildCredentialXml(credentialData)
        def tempFile = "temp_credential_${System.currentTimeMillis()}.xml"
        
        steps.echo "Creating credential with XML content:"
        steps.echo xmlContent
        
        steps.writeFile(file: tempFile, text: xmlContent)
        
        // ファイルが正しく作成されたか確認
        if (steps.fileExists(tempFile)) {
            def fileContent = steps.readFile(file: tempFile)
            steps.echo "Temp file created successfully. Content length: ${fileContent.length()}"
        } else {
            throw new JenkinsCliException("Failed to create temporary XML file")
        }
        
        try {
            createCredentialByXml(store, domain, tempFile, config)
        } finally {
            steps.sh "rm -f ${tempFile}"
        }
    }
    
    /**
     * Credential情報からXMLを生成
     * @param credentialData Credential情報
     * @return XML文字列
     */
    private String buildCredentialXml(Map credentialData) {
        def type = credentialData.type ?: 'usernamePassword'
        def scope = credentialData.scope ?: 'GLOBAL'
        
        switch(type) {
            case 'usernamePassword':
                return """<com.cloudbees.plugins.credentials.impl.UsernamePasswordCredentialsImpl>
  <scope>${scope}</scope>
  <id>${credentialData.id}</id>
  <description>${credentialData.description ?: ''}</description>
  <username>${credentialData.username}</username>
  <password>${credentialData.password}</password>
</com.cloudbees.plugins.credentials.impl.UsernamePasswordCredentialsImpl>"""
            
            case 'secretText':
                return """<org.jenkinsci.plugins.plaincredentials.impl.StringCredentialsImpl>
  <scope>${scope}</scope>
  <id>${credentialData.id}</id>
  <description>${credentialData.description ?: ''}</description>
  <secret>${credentialData.secret}</secret>
</org.jenkinsci.plugins.plaincredentials.impl.StringCredentialsImpl>"""
            
            case 'sshKey':
                return """<com.cloudbees.jenkins.plugins.sshcredentials.impl.BasicSSHUserPrivateKey>
  <scope>${scope}</scope>
  <id>${credentialData.id}</id>
  <description>${credentialData.description ?: ''}</description>
  <username>${credentialData.username}</username>
  <privateKeySource class="com.cloudbees.jenkins.plugins.sshcredentials.impl.BasicSSHUserPrivateKey\$DirectEntryPrivateKeySource">
    <privateKey>${credentialData.privateKey}</privateKey>
  </privateKeySource>
</com.cloudbees.jenkins.plugins.sshcredentials.impl.BasicSSHUserPrivateKey>"""
            
            default:
                throw new IllegalArgumentException("Unsupported credential type: ${type}")
        }
    }
    
    // Private helpers
    
    private void validateConfig(Map config) {
        if (!config.jenkinsUrl?.trim()) {
            throw new IllegalArgumentException("Jenkins URL is required")
        }
        // URLの末尾のスラッシュを除去
        config.jenkinsUrl = config.jenkinsUrl.replaceAll('/+$', '')
    }
    
    private def executeCliCommand(String command, Map config) {
        def cliCommand = buildCliCommand(command, config)
        
        // エラーをより詳細にキャプチャするために、returnStatus: trueを使用
        def exitCode = 0
        def output = ""
        def errorOutput = ""
        
        try {
            if (config.inputFile) {
                // ファイルの存在と内容を確認
                if (!steps.fileExists(config.inputFile)) {
                    throw new JenkinsCliException("Input file does not exist: ${config.inputFile}")
                }
                
                // ファイルサイズを確認
                def fileInfo = steps.sh(script: "ls -la ${config.inputFile}", returnStdout: true)
                steps.echo "Input file info: ${fileInfo}"
                
                // 一時ファイルを使用してエラーをキャプチャ
                def tempErrorFile = "cli_error_${System.currentTimeMillis()}.txt"
                exitCode = steps.sh(
                    script: "cat '${config.inputFile}' | ${cliCommand} 2>${tempErrorFile}",
                    returnStatus: true
                )
                output = steps.sh(script: "cat '${config.inputFile}' | ${cliCommand} 2>/dev/null || true", returnStdout: true)
                if (steps.fileExists(tempErrorFile)) {
                    errorOutput = steps.readFile(file: tempErrorFile)
                    steps.sh "rm -f ${tempErrorFile}"
                }
            } else if (config.outputFile) {
                def tempErrorFile = "cli_error_${System.currentTimeMillis()}.txt"
                exitCode = steps.sh(
                    script: "${cliCommand} > '${config.outputFile}' 2>${tempErrorFile}",
                    returnStatus: true
                )
                if (steps.fileExists(tempErrorFile)) {
                    errorOutput = steps.readFile(file: tempErrorFile)
                    steps.sh "rm -f ${tempErrorFile}"
                }
                output = "Output saved to ${config.outputFile}"
            } else {
                def tempErrorFile = "cli_error_${System.currentTimeMillis()}.txt"
                exitCode = steps.sh(
                    script: "${cliCommand} 2>${tempErrorFile}",
                    returnStatus: true
                )
                output = steps.sh(script: "${cliCommand} 2>/dev/null || true", returnStdout: true)
                if (steps.fileExists(tempErrorFile)) {
                    errorOutput = steps.readFile(file: tempErrorFile)
                    steps.sh "rm -f ${tempErrorFile}"
                }
            }
            
            // エラーチェック
            if (exitCode != 0) {
                steps.echo "CLI command failed with exit code: ${exitCode}"
                steps.echo "Error output: ${errorOutput}"
                steps.echo "Standard output: ${output}"
                
                // リトライロジック（認証エラーの場合）
                if (errorOutput.contains("401") || errorOutput.contains("Unauthorized")) {
                    steps.echo "Authentication error detected. Trying different authentication approaches..."
                    
                    // 1. まず、ユーザー名を明示的に指定して再試行
                    if (config.authMethod == 'token' && !config.retryAttempted) {
                        steps.echo "Retrying with explicit username format..."
                        config.retryAttempted = true
                        def retryCommand = buildCliCommand(command, config)
                        
                        // cURLでデバッグ情報を出力
                        steps.sh """
                            echo "=== Debug: Testing API access with curl ==="
                            curl -I -u "\$JENKINS_USER:\$JENKINS_API_TOKEN" ${config.jenkinsUrl}/cli?remoting=false || true
                            echo "=== End Debug ==="
                        """
                        
                        output = steps.sh(script: retryCommand, returnStdout: true)
                        return output
                    }
                    
                    // 2. Jenkinsの認証設定を確認
                    steps.echo """
                    Authentication failed. Please verify:
                    1. The credential ID '${config.credentialsId}' exists and is valid
                    2. The user has 'Overall/Read' permission in Jenkins
                    3. If using API token, ensure it's not expired
                    4. Jenkins security realm is properly configured
                    
                    Current Jenkins URL: ${config.jenkinsUrl}
                    """
                }
                
                throw new JenkinsCliException("CLI command failed with exit code ${exitCode}")
            }
            
            return output
            
        } catch (Exception e) {
            def errorMessage = """Failed to execute Jenkins CLI command: ${command}
Exit Code: ${exitCode}
Error: ${e.message}
Standard Output: ${output}
Error Output: ${errorOutput}"""
            
            throw new JenkinsCliException(errorMessage)
        }
    }
    
    private String buildCliCommand(String command, Map config) {
        // URLの末尾のスラッシュを確実に除去
        def jenkinsUrl = config.jenkinsUrl.replaceAll('/+$', '')
        
        // 基本的なCLIコマンドを構築
        def cliCommand = "java -jar jenkins-cli.jar"
        
        // 認証方式に応じて認証パラメータを設定
        if (config.authMethod == 'token') {
            // APIトークン認証の場合
            cliCommand += " -auth \"\$JENKINS_USER:\$JENKINS_API_TOKEN\""
        } else {
            // ユーザー名/パスワード認証の場合
            cliCommand += " -auth \"\$USER:\$PASS\""
        }
        
        // URLを追加
        cliCommand += " -s '${jenkinsUrl}'"
        
        // HTTP接続モードを使用（WebSocketの問題を回避）
        if (config.useHttp) {
            cliCommand += " -http"
        }
        
        // CSRF保護を無効化（必要に応じて）
        if (config.disableCsrf) {
            cliCommand += " -noCertificateCheck"
        }
        
        // コマンドを追加
        cliCommand += " ${command}"
        
        return cliCommand
    }
}

/**
 * Jenkins CLI操作で発生するカスタム例外クラス
 */
class JenkinsCliException extends Exception {
    JenkinsCliException(String message) {
        super(message)
    }
}
