package jp.co.tielec.aws

/**
 * SSM Parameter Store ユーティリティクラス
 *
 * AWS Systems Manager Parameter Storeからパラメータを取得するための
 * 汎用ユーティリティクラス。
 *
 * @author infrastructure-team
 * @since 2025-01-16
 */
class SsmParameterStore implements Serializable {
    private def script
    private String region
    private Map<String, String> cache = [:]
    private boolean useCache

    /**
     * コンストラクタ
     *
     * @param script Jenkinsパイプラインスクリプト
     * @param region AWSリージョン（デフォルト: ap-northeast-1）
     * @param useCache キャッシュを使用するか（デフォルト: true）
     */
    SsmParameterStore(def script, String region = 'ap-northeast-1', boolean useCache = true) {
        this.script = script
        this.region = region
        this.useCache = useCache
    }

    /**
     * 単一のパラメータを取得
     *
     * @param parameterName パラメータ名
     * @param withDecryption SecureStringの復号化（デフォルト: true）
     * @return パラメータ値
     */
    String getParameter(String parameterName, boolean withDecryption = true) {
        if (!parameterName) {
            script.error "パラメータ名が指定されていません"
        }

        // キャッシュチェック
        if (useCache && cache.containsKey(parameterName)) {
            script.echo "[SSM] キャッシュからパラメータを取得: ${parameterName}"
            return cache[parameterName]
        }

        script.echo "[SSM] パラメータを取得中: ${parameterName}"

        try {
            def decryptFlag = withDecryption ? '--with-decryption' : ''
            def result = script.sh(
                script: """
                    aws ssm get-parameter \
                        --name '${parameterName}' \
                        --region ${region} \
                        ${decryptFlag} \
                        --query 'Parameter.Value' \
                        --output text
                """,
                returnStdout: true
            ).trim()

            // キャッシュに保存
            if (useCache) {
                cache[parameterName] = result
            }

            return result
        } catch (Exception e) {
            script.error "SSMパラメータの取得に失敗しました: ${parameterName}\nエラー: ${e.message}"
        }
    }

    /**
     * 複数のパラメータを一括取得
     *
     * @param parameterNames パラメータ名のリスト
     * @param withDecryption SecureStringの復号化（デフォルト: true）
     * @return パラメータ名と値のマップ
     */
    Map<String, String> getParameters(List<String> parameterNames, boolean withDecryption = true) {
        if (!parameterNames || parameterNames.isEmpty()) {
            script.error "パラメータ名のリストが空です"
        }

        Map<String, String> results = [:]
        List<String> uncachedParams = []

        // キャッシュチェック
        if (useCache) {
            parameterNames.each { name ->
                if (cache.containsKey(name)) {
                    script.echo "[SSM] キャッシュからパラメータを取得: ${name}"
                    results[name] = cache[name]
                } else {
                    uncachedParams << name
                }
            }
        } else {
            uncachedParams = parameterNames
        }

        // キャッシュにないパラメータを取得
        if (!uncachedParams.isEmpty()) {
            script.echo "[SSM] ${uncachedParams.size()}個のパラメータを取得中..."

            try {
                def namesParam = uncachedParams.collect { "'${it}'" }.join(' ')
                def decryptFlag = withDecryption ? '--with-decryption' : ''

                def jsonResult = script.sh(
                    script: """
                        aws ssm get-parameters \
                            --names ${namesParam} \
                            --region ${region} \
                            ${decryptFlag} \
                            --query 'Parameters[*].[Name,Value]' \
                            --output json
                    """,
                    returnStdout: true
                ).trim()

                // JSON結果をパース
                def parsedResult = script.readJSON(text: jsonResult)
                parsedResult.each { param ->
                    def name = param[0]
                    def value = param[1]
                    results[name] = value

                    // キャッシュに保存
                    if (useCache) {
                        cache[name] = value
                    }
                }
            } catch (Exception e) {
                script.error "SSMパラメータの一括取得に失敗しました\nエラー: ${e.message}"
            }
        }

        return results
    }

    /**
     * パスによるパラメータの取得（階層構造）
     *
     * @param path パラメータのパス（例: /jenkins/config/）
     * @param recursive 再帰的に取得（デフォルト: true）
     * @param withDecryption SecureStringの復号化（デフォルト: true）
     * @return パラメータ名と値のマップ
     */
    Map<String, String> getParametersByPath(String path, boolean recursive = true, boolean withDecryption = true) {
        if (!path) {
            script.error "パスが指定されていません"
        }

        script.echo "[SSM] パス配下のパラメータを取得中: ${path}"

        try {
            def recursiveFlag = recursive ? '--recursive' : ''
            def decryptFlag = withDecryption ? '--with-decryption' : ''

            def jsonResult = script.sh(
                script: """
                    aws ssm get-parameters-by-path \
                        --path '${path}' \
                        --region ${region} \
                        ${recursiveFlag} \
                        ${decryptFlag} \
                        --query 'Parameters[*].[Name,Value]' \
                        --output json
                """,
                returnStdout: true
            ).trim()

            Map<String, String> results = [:]
            def parsedResult = script.readJSON(text: jsonResult)

            parsedResult.each { param ->
                def name = param[0]
                def value = param[1]
                results[name] = value

                // キャッシュに保存
                if (useCache) {
                    cache[name] = value
                }
            }

            script.echo "[SSM] ${results.size()}個のパラメータを取得しました"
            return results

        } catch (Exception e) {
            script.error "パス配下のパラメータ取得に失敗しました: ${path}\nエラー: ${e.message}"
        }
    }

    /**
     * パラメータが存在するかチェック
     *
     * @param parameterName パラメータ名
     * @return 存在する場合true
     */
    boolean parameterExists(String parameterName) {
        try {
            script.sh(
                script: """
                    aws ssm get-parameter \
                        --name '${parameterName}' \
                        --region ${region} \
                        --query 'Parameter.Name' \
                        --output text
                """,
                returnStatus: true
            ) == 0
        } catch (Exception e) {
            return false
        }
    }

    /**
     * キャッシュをクリア
     */
    void clearCache() {
        cache.clear()
        script.echo "[SSM] キャッシュをクリアしました"
    }

    /**
     * 現在のキャッシュサイズを取得
     *
     * @return キャッシュに保存されているパラメータ数
     */
    int getCacheSize() {
        return cache.size()
    }
}