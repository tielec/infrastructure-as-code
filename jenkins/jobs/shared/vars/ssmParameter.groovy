import jp.co.tielec.aws.SsmParameterStore

/**
 * SSM Parameter Store ヘルパー関数
 *
 * パイプラインから簡単にSSMパラメータを取得するためのグローバル関数。
 *
 * 使用例:
 * ```groovy
 * // 単一パラメータ取得
 * def dbPassword = ssmParameter.get('/jenkins/db/password', 'ap-northeast-1')
 *
 * // 複数パラメータ取得
 * def params = ssmParameter.getMultiple(['/jenkins/api/key', '/jenkins/api/secret'], 'ap-northeast-1')
 *
 * // パス配下の全パラメータ取得
 * def configs = ssmParameter.getByPath('/jenkins/config/', 'ap-northeast-1')
 * ```
 */

/**
 * 単一のSSMパラメータを取得
 *
 * @param parameterName パラメータ名
 * @param region AWSリージョン
 * @param withDecryption SecureStringの復号化（デフォルト: true）
 * @return パラメータ値
 */
def get(String parameterName, String region, boolean withDecryption = true) {
    def ssmStore = new SsmParameterStore(this, region, true)
    return ssmStore.getParameter(parameterName, withDecryption)
}

/**
 * 複数のSSMパラメータを一括取得
 *
 * @param parameterNames パラメータ名のリスト
 * @param region AWSリージョン
 * @param withDecryption SecureStringの復号化（デフォルト: true）
 * @return パラメータ名と値のマップ
 */
def getMultiple(List<String> parameterNames, String region, boolean withDecryption = true) {
    def ssmStore = new SsmParameterStore(this, region, true)
    return ssmStore.getParameters(parameterNames, withDecryption)
}

/**
 * パス配下のSSMパラメータを取得
 *
 * @param path パラメータのパス（例: /jenkins/config/）
 * @param region AWSリージョン
 * @param recursive 再帰的に取得（デフォルト: true）
 * @param withDecryption SecureStringの復号化（デフォルト: true）
 * @return パラメータ名と値のマップ
 */
def getByPath(String path, String region, boolean recursive = true, boolean withDecryption = true) {
    def ssmStore = new SsmParameterStore(this, region, true)
    return ssmStore.getParametersByPath(path, recursive, withDecryption)
}

/**
 * SSMパラメータが存在するかチェック
 *
 * @param parameterName パラメータ名
 * @param region AWSリージョン
 * @return 存在する場合true
 */
def exists(String parameterName, String region) {
    def ssmStore = new SsmParameterStore(this, region, false)
    return ssmStore.parameterExists(parameterName)
}

/**
 * withSSMParametersブロック
 * 指定したパラメータを環境変数として設定してブロックを実行
 *
 * @param parameterMapping パラメータ名と環境変数名のマッピング
 * @param region AWSリージョン
 * @param body 実行するクロージャ
 */
def withParameters(Map parameterMapping, String region, Closure body) {
    def ssmStore = new SsmParameterStore(this, region, true)

    // パラメータを取得
    def parameterNames = parameterMapping.keySet().toList()
    def values = ssmStore.getParameters(parameterNames, true)

    // 環境変数を設定
    def envVars = []
    parameterMapping.each { paramName, envName ->
        if (values.containsKey(paramName)) {
            envVars << "${envName}=${values[paramName]}"
        } else {
            error "SSMパラメータが見つかりません: ${paramName}"
        }
    }

    // withEnvブロックで実行
    withEnv(envVars) {
        body()
    }
}