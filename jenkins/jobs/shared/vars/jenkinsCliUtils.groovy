import jp.co.tielec.jenkins.JenkinsCliClient

/**
 * Jenkins CLI操作のファサード
 * 内部実装はJenkinsCliClientクラスに委譲
 */

/**
 * クライアントインスタンスを作成する
 */
private JenkinsCliClient createClient() {
    return new JenkinsCliClient(this, env)
}

/**
 * Jenkins CLIをセットアップする
 * @param jenkinsUrl JenkinsのURL
 * @return CLIのパス
 */
def setupCli(String jenkinsUrl) {
    return createClient().setupCli(jenkinsUrl)
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
 */
def executeCommand(String command, Map config = [:]) {
    return createClient().executeCommand(command, config)
}

/**
 * 設定をエクスポートする
 * @param outputFile 出力ファイルパス
 * @param config 設定オプション
 */
def exportConfiguration(String outputFile, Map config = [:]) {
    return createClient().exportConfiguration(outputFile, config)
}

/**
 * 設定を検証する
 * @param configFile 設定ファイルパス
 * @param config 設定オプション
 */
def checkConfiguration(String configFile, Map config = [:]) {
    return createClient().checkConfiguration(configFile, config)
}

/**
 * JCasCの設定をリロードする
 * @param config 設定オプション
 */
def reloadJCasCConfiguration(Map config = [:]) {
    return createClient().reloadJCasCConfiguration(config)
}

/**
 * Jenkinsを安全に再起動する
 * @param config 設定オプション
 */
def safeRestart(Map config = [:]) {
    return createClient().safeRestart(config)
}

// Credentials関連メソッド

/**
 * Credentialsをリスト表示
 * @param store Store ID (例: system::system::jenkins)
 * @param config 設定オプション
 * @return コマンドの出力
 */
def listCredentials(String store, Map config = [:]) {
    return createClient().listCredentials(store, config)
}

/**
 * CredentialsをXML形式でリスト表示
 * @param store Store ID
 * @param domain Domain名（オプション）
 * @param config 設定オプション
 * @return XML形式の出力
 */
def listCredentialsAsXml(String store, String domain = null, Map config = [:]) {
    return createClient().listCredentialsAsXml(store, domain, config)
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
    return createClient().getCredentialAsXml(store, domain, credentialId, config)
}

/**
 * XMLからCredentialを作成
 * @param store Store ID
 * @param domain Domain名
 * @param xmlFile XMLファイルパス
 * @param config 設定オプション
 */
def createCredentialByXml(String store, String domain, String xmlFile, Map config = [:]) {
    return createClient().createCredentialByXml(store, domain, xmlFile, config)
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
    return createClient().updateCredentialByXml(store, domain, credentialId, xmlFile, config)
}

/**
 * Credentialを削除
 * @param store Store ID
 * @param domain Domain名
 * @param credentialId Credential ID
 * @param config 設定オプション
 */
def deleteCredential(String store, String domain, String credentialId, Map config = [:]) {
    return createClient().deleteCredential(store, domain, credentialId, config)
}

/**
 * CredentialsをXML形式でインポート
 * @param store Store ID
 * @param xmlFile XMLファイルパス
 * @param domain Domain名（オプション）
 * @param config 設定オプション
 */
def importCredentialsAsXml(String store, String xmlFile, String domain = null, Map config = [:]) {
    return createClient().importCredentialsAsXml(store, xmlFile, domain, config)
}

/**
 * Credentials Domainを作成
 * @param store Store ID
 * @param xmlFile Domain定義のXMLファイルパス
 * @param config 設定オプション
 */
def createCredentialsDomainByXml(String store, String xmlFile, Map config = [:]) {
    return createClient().createCredentialsDomainByXml(store, xmlFile, config)
}

/**
 * Credentials DomainをXML形式で取得
 * @param store Store ID
 * @param domain Domain名
 * @param config 設定オプション
 * @return XML形式の出力
 */
def getCredentialsDomainAsXml(String store, String domain, Map config = [:]) {
    return createClient().getCredentialsDomainAsXml(store, domain, config)
}

/**
 * Credentials Domainを更新
 * @param store Store ID
 * @param domain Domain名
 * @param xmlFile Domain定義のXMLファイルパス
 * @param config 設定オプション
 */
def updateCredentialsDomainByXml(String store, String domain, String xmlFile, Map config = [:]) {
    return createClient().updateCredentialsDomainByXml(store, domain, xmlFile, config)
}

/**
 * Credentials Domainを削除
 * @param store Store ID
 * @param domain Domain名
 * @param config 設定オプション
 */
def deleteCredentialsDomain(String store, String domain, Map config = [:]) {
    return createClient().deleteCredentialsDomain(store, domain, config)
}

/**
 * Credentials Providersをリスト表示
 * @param config 設定オプション
 * @return プロバイダーリスト
 */
def listCredentialsProviders(Map config = [:]) {
    return createClient().listCredentialsProviders(config)
}

/**
 * Credentials Context Resolversをリスト表示
 * @param config 設定オプション
 * @return リゾルバーリスト
 */
def listCredentialsContextResolvers(Map config = [:]) {
    return createClient().listCredentialsContextResolvers(config)
}

/**
 * プログラマティックにCredentialを作成するヘルパーメソッド
 * @param store Store ID
 * @param domain Domain名
 * @param credentialData Credential情報のMap
 * @param config 設定オプション
 */
def createCredential(String store, String domain, Map credentialData, Map config = [:]) {
    return createClient().createCredential(store, domain, credentialData, config)
}
