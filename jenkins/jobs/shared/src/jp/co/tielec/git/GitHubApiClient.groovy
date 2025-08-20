package jp.co.tielec.git

import groovy.json.JsonOutput
import groovy.json.JsonSlurper
import java.text.SimpleDateFormat
import java.util.TimeZone

/**
 * GitHub API操作のためのクライアントクラス
 */
class GitHubApiClient implements Serializable {
    private static final long serialVersionUID = 1L;
    
    // 認証方式の列挙型
    enum AuthType {
        PAT,        // Personal Access Token認証
        GITHUB_APP  // GitHub App認証
    }
    
    protected def script
    protected Map defaultConfig
    protected GitClientBase gitClient
    
    /**
     * コンストラクタ
     * @param script Pipelineスクリプトコンテキスト
     */
    GitHubApiClient(def script) {
        this.script = script
        // 環境変数から取得、未定義の場合はデフォルト値を使用
        def defaultCredentialsId = script.env.GITHUB_APP_CREDENTIALS_ID ?: 'github-app-credentials'
        this.defaultConfig = [
            credentialsId: defaultCredentialsId,
            acceptType: 'application/vnd.github.v3+json',
            authType: AuthType.GITHUB_APP // デフォルトはGitHub App認証
        ]
        this.gitClient = new GitClientBase(script)
    }
    
    /**
     * GitHub API呼び出しの共通処理
     * @param url APIのエンドポイントURL
     * @param method HTTPメソッド（デフォルト: 'GET'）
     * @param body リクエストボディ（オプション）
     * @param config 設定（オプション）
     * @return APIレスポンス
     * @throws GitOperationException API呼び出しに失敗した場合
     */
    def callGitHubApi(String url, String method = 'GET', def body = null, Map config = [:]) {
        try {
            // パラメータのバリデーション
            if (!url?.trim()) {
                throw new IllegalArgumentException("URLは必須です")
            }
            
            // デフォルト設定とマージ
            def effectiveConfig = defaultConfig + config
            
            // 認証タイプに応じてAPIを呼び出す
            if (effectiveConfig.authType == AuthType.GITHUB_APP) {
                return callGitHubApiWithGithubApp(url, method, body, effectiveConfig)
            } else {
                // デフォルトのPAT認証
                return callGitHubApiWithPAT(url, method, body, effectiveConfig)
            }
        } catch (IllegalArgumentException e) {
            throw e  // バリデーションエラーはそのまま再スロー
        } catch (Exception e) {
            def errorMessage = "GitHub API呼び出しエラー: ${e.message}"
            if (e.hasProperty('response') && e.response != null && e.response.hasProperty('content')) {
                errorMessage += "\nResponse: ${e.response.content}"
            }
            script.echo "API Call Error: ${errorMessage}"
            throw new GitOperationException(errorMessage, e)
        }
    }
    
    /**
     * PAT認証を使用したGitHub API呼び出し
     * @param url APIのエンドポイントURL
     * @param method HTTPメソッド
     * @param body リクエストボディ
     * @param config 設定
     * @return APIレスポンス
     */
    private def callGitHubApiWithPAT(String url, String method, def body, Map config) {
        script.withCredentials([script.usernamePassword(
            credentialsId: config.credentialsId,
            usernameVariable: 'GIT_USERNAME', // PATの場合は通常パスワードのみ使用
            passwordVariable: 'GIT_PASSWORD'  // PATを格納
        )]) {
            // リクエスト設定の構築
            def requestConfig = [
                url: url,
                httpMode: method.toUpperCase(),
                customHeaders: [
                    [name: 'Authorization', value: "token ${script.env.GIT_PASSWORD}"],
                    [name: 'Accept', value: config.acceptType],
                    [name: 'X-GitHub-Api-Version', value: '2022-11-28'] // APIバージョン指定を推奨
                ],
                ignoreSslErrors: false, // 必要に応じてtrueに変更
                timeout: 30 // タイムアウト設定（秒）
            ]

            // ボディがある場合の追加設定
            if (body) {
                requestConfig.contentType = 'APPLICATION_JSON'
                requestConfig.requestBody = JsonOutput.toJson(body)
            }

            script.echo "Requesting to ${url} with PAT auth"
            def response = script.httpRequest(requestConfig)
            script.echo "Response Status: ${response.status}"
            // script.echo "Response Content: ${response.content}" // デバッグ用に必要であれば有効化

            // レスポンスの検証 (204 No Content も成功とみなす場合がある)
            if (!(response.status in [200, 201, 202, 204])) {
                throw new GitOperationException(
                    "GitHub API呼び出しに失敗しました。URL: ${url}, メソッド: ${method}, ステータス: ${response.status}, Response: ${response.content}"
                )
            }
            
            // レスポンスが空でない場合のみJSONとしてパース
            if (response.content && response.content.trim()) {
                return script.readJSON(text: response.content)
            } else {
                return null // または適切な空のレスポンス
            }
        }
    }
    
    /**
    * GitHub App認証を使用したGitHub API呼び出し
    * @param url APIのエンドポイントURL
    * @param method HTTPメソッド
    * @param body リクエストボディ
    * @param config 設定 (credentialsId を含む)
    * @return APIレスポンス
    */
    private def callGitHubApiWithGithubApp(String url, String method, def body, Map config) {
        script.withCredentials([script.usernamePassword(
            credentialsId: config.credentialsId,      // Github Appの認証情報ID
            usernameVariable: 'GITHUB_APP',           // App ID
            passwordVariable: 'GITHUB_ACCESS_TOKEN'   // トークンを直接使用
        )]) {
            // リクエスト設定の構築
            def requestConfig = [
                url: url,
                httpMode: method.toUpperCase(),
                quiet: false,
                customHeaders: [
                    [name: 'Authorization', value: "Bearer ${script.env.GITHUB_ACCESS_TOKEN}"], // トークンをそのまま使用
                    [name: 'Accept', value: config.acceptType ?: 'application/vnd.github+json'],
                    [name: 'X-GitHub-Api-Version', value: '2022-11-28']
                ],
                ignoreSslErrors: false, // 必要に応じてtrueに変更
                timeout: 30 // タイムアウト設定（秒）
            ]

            // ボディがある場合の追加設定
            if (body) {
                requestConfig.contentType = 'APPLICATION_JSON'
                requestConfig.requestBody = JsonOutput.toJson(body)
            }
            
            script.echo "Requesting to ${url} with GitHub App auth"
            def response = script.httpRequest(requestConfig)
            script.echo "Response Status: ${response.status}"
            
            // レスポンスの検証
            if (!(response.status in [200, 201, 202, 204])) {
                throw new GitOperationException(
                    "GitHub API呼び出しに失敗しました。URL: ${url}, メソッド: ${method}, ステータス: ${response.status}, Response: ${response.content}"
                )
            }

            // レスポンスが空でない場合のみJSONとしてパース
            if (response.content && response.content.trim()) {
                return script.readJSON(text: response.content)
            } else {
                return null // または適切な空のレスポンス
            }
        }
    }
    
    /**
     * GitHub認証ユーザーの情報を取得する (PAT認証用)
     * @param config 設定（オプション, credentialsIdを指定可能）
     * @return 認証ユーザーの情報（login, id, name等）
     * @throws GitOperationException API呼び出しに失敗した場合
     */
    def getAuthenticatedUser(Map config = [:]) {
        try {
            // このメソッドは通常PAT認証を想定
            def effectiveConfig = [:] + config
            effectiveConfig.authType = AuthType.PAT // 明示的にPATを指定

            return callGitHubApi(
                "https://api.github.com/user",
                'GET',
                null,
                effectiveConfig
            )
        } catch (Exception e) {
            throw new GitOperationException("認証ユーザー情報の取得に失敗しました: ${e.message}", e)
        }
    }
    
    /**
     * GitHub Appのインストール情報を取得する
     * @param config 設定（オプション, credentialsIdを指定可能。例: [credentialsId: 'github-app-key-pem']）
     * @return アプリのインストール情報
     * @throws GitOperationException API呼び出しに失敗した場合
     */
    def getGitHubAppInstallations(Map config = [:]) {
        try {
            // 認証タイプをGitHub Appに設定
            def updatedConfig = [:] + config
            updatedConfig.authType = AuthType.GITHUB_APP

            return callGitHubApi(
                "https://api.github.com/app/installations",
                'GET',
                null,
                updatedConfig
            )
        } catch (Exception e) {
            throw new GitOperationException("GitHub Appインストール情報の取得に失敗しました: ${e.message}", e)
        }
    }
    
    /**
     * GitHub APIのレート制限情報を取得する
     * @param config 設定（オプション）
     * @return レート制限情報
     * @throws GitOperationException API呼び出しに失敗した場合
     */
    def getRateLimit(Map config = [:]) {
        try {
            return callGitHubApi(
                "https://api.github.com/rate_limit",
                'GET',
                null,
                config
            )
        } catch (Exception e) {
            throw new GitOperationException("レート制限情報の取得に失敗しました: ${e.message}", e)
        }
    }
    
    /**
     * リポジトリ情報を取得するヘルパーメソッド
     * @param config 設定
     * @return [リポジトリオーナー, リポジトリ名] の配列
     */
    protected def getRepositoryInfo(Map config) {
        if (config.repoOwner && config.repoName) {
            return [config.repoOwner, config.repoName]
        } else if (config.repoUrl) {
            return gitClient.getCurrentRepoInfo(config.repoUrl)
        } else {
            return gitClient.getCurrentRepoInfo()
        }
    }
    
    /**
     * Check Runを作成する
     * @param repoOwner リポジトリオーナー
     * @param repoName リポジトリ名
     * @param headSha コミットのSHA
     * @param checkName チェック名
     * @param status ステータス (queued, in_progress, completed)
     * @param conclusion 結論 (success, failure, neutral, cancelled, skipped, timed_out, or action_required)
     * @param config 設定（オプション）
     * @return 作成されたCheck Runの情報
     * @throws GitOperationException API呼び出しに失敗した場合
     */
    def createCheckRun(String repoOwner, String repoName, String headSha, String checkName, 
                      String status, String conclusion = null, Map config = [:]) {
        try {
            // パラメータのバリデーション
            if (!repoOwner?.trim() || !repoName?.trim()) {
                throw new IllegalArgumentException("リポジトリオーナーとリポジトリ名は必須です")
            }
            if (!headSha?.trim()) {
                throw new IllegalArgumentException("コミットのSHAは必須です")
            }
            if (!checkName?.trim()) {
                throw new IllegalArgumentException("チェック名は必須です")
            }
            
            // 現在のUTC時刻を取得（ISO 8601フォーマット）
            def now = new Date()
            def timestamp = now.format("yyyy-MM-dd'T'HH:mm:ss'Z'", TimeZone.getTimeZone('UTC'))
            
            // リクエストボディの作成
            def body = [
                name: checkName,
                head_sha: headSha,
                status: status
            ]
            
            // statusがcompletedの場合はconclusionが必須
            if (status == 'completed') {
                if (!conclusion) {
                    throw new IllegalArgumentException("ステータスがcompletedの場合、conclusionは必須です")
                }
                body.conclusion = conclusion
                body.completed_at = timestamp
            }
            
            // 開始時刻を設定
            body.started_at = timestamp
            
            // 出力情報があれば追加
            if (config.title || config.summary) {
                body.output = [
                    title: config.title ?: checkName,
                    summary: config.summary ?: "${checkName} completed with ${conclusion ?: 'no conclusion'}"
                ]
                
                if (config.text) {
                    body.output.text = config.text
                }
            }
            
            // 認証タイプをGitHub Appに設定（GitHub App認証で必要）
            def updatedConfig = [:] + config
            updatedConfig.authType = AuthType.GITHUB_APP
            
            return callGitHubApi(
                "https://api.github.com/repos/${repoOwner}/${repoName}/check-runs",
                'POST',
                body,
                updatedConfig
            )
        } catch (IllegalArgumentException e) {
            throw e  // バリデーションエラーはそのまま再スロー
        } catch (Exception e) {
            throw new GitOperationException("Check Runの作成に失敗しました: ${e.message}", e)
        }
    }
    
    /**
    * GitHub App接続をテストする（レート制限情報のみ取得）
    * @param config 設定（オプション）
    *        - credentialsId: GitHub App認証情報ID (デフォルト: 'github-app-credentials')
    * @return テスト結果 (success: true/false, rate_limit: レート制限情報)
    */
    def testGitHubAppConnection(Map config = [:]) {
        try {
            // 認証タイプをGitHub Appに設定
            def updatedConfig = [:] + config
            updatedConfig.authType = AuthType.GITHUB_APP
            
            // レート制限情報を取得して接続テスト
            def rateLimit = getRateLimit(updatedConfig)
            
            return [
                success: true,
                rate_limit: rateLimit,
                message: "GitHub App接続テストが成功しました"
            ]
        } catch (Exception e) {
            script.echo "GitHub App接続テストに失敗: ${e.message}"
            return [
                success: false,
                message: e.message
            ]
        }
    }

    /**
    * PAT認証で接続をテストする
    * @param config 設定（オプション）
    *        - credentialsId: PAT認証情報ID (デフォルト: 'github-pat')
    * @return テスト結果 (success: true/false, rate_limit: レート制限情報)
    */
    def testPATConnection(Map config = [:]) {
        try {
            // 認証タイプをPATに設定
            def updatedConfig = [:] + config
            updatedConfig.authType = AuthType.PAT
            
            // レート制限情報を取得して接続テスト
            def rateLimit = getRateLimit(updatedConfig)
            
            // ユーザー情報も取得してみる（追加のテスト）
            def userInfo = getAuthenticatedUser(updatedConfig)
            
            return [
                success: true,
                rate_limit: rateLimit,
                user_info: userInfo,
                message: "PAT認証接続テストが成功しました"
            ]
        } catch (Exception e) {
            script.echo "PAT認証接続テストに失敗: ${e.message}"
            return [
                success: false,
                message: e.message
            ]
        }
    }

    /**
    * 指定した認証方式でGitHub接続をテストする
    * @param authType 認証タイプ (AuthType.PAT または AuthType.GITHUB_APP)
    * @param config 設定（オプション）
    *        - credentialsId: 認証情報ID
    * @return テスト結果 (success: true/false, rate_limit: レート制限情報)
    */
    def testGitHubConnection(AuthType authType, Map config = [:]) {
        try {
            // 認証タイプを設定
            def updatedConfig = [:] + config
            updatedConfig.authType = authType
            
            // デフォルトの認証情報IDを設定（環境変数から取得）
            if (!updatedConfig.credentialsId) {
                def githubAppCredentialsId = script.env.GITHUB_APP_CREDENTIALS_ID ?: 'github-app-credentials'
                def githubPatCredentialsId = script.env.GITHUB_PAT_CREDENTIALS_ID ?: 'github-pat'
                updatedConfig.credentialsId = (authType == AuthType.GITHUB_APP) ? githubAppCredentialsId : githubPatCredentialsId
            }
            
            // レート制限情報を取得して接続テスト
            def rateLimit = getRateLimit(updatedConfig)
            
            def result = [
                success: true,
                auth_type: authType.toString(),
                rate_limit: rateLimit,
                message: "${authType.toString()}認証接続テストが成功しました"
            ]
            
            // PATの場合はユーザー情報も取得
            if (authType == AuthType.PAT) {
                try {
                    def userInfo = getAuthenticatedUser(updatedConfig)
                    result.user_info = userInfo
                } catch (Exception ignored) {
                    // ユーザー情報取得に失敗しても全体のテストは成功とみなす
                    result.user_info_error = "ユーザー情報の取得に失敗: ${ignored.message}"
                }
            }
            
            return result
        } catch (Exception e) {
            script.echo "${authType.toString()}認証接続テストに失敗: ${e.message}"
            return [
                success: false,
                auth_type: authType.toString(),
                message: e.message
            ]
        }
    }
}