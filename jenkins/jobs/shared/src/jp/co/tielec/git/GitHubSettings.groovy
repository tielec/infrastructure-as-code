package jp.co.tielec.git

/**
 * GitHub Settings操作に関するクラス
 */
class GitHubSettings implements Serializable {
    private static final long serialVersionUID = 1L
    
    protected def script
    protected GitHubApiClient apiClient
    
    /**
     * コンストラクタ
     * @param script Pipelineスクリプトコンテキスト
     */
    GitHubSettings(def script) {
        this.script = script
        this.apiClient = new GitHubApiClient(script)
    }
    
    // ==================== Webhook操作 ====================
    
    /**
     * Webhookの一覧を取得する
     * @param config 設定（オプション）
     * @return Webhookの一覧
     * @throws GitOperationException API呼び出しに失敗した場合
     */
    def listWebhooks(Map config = [:]) {
        try {
            def (repoOwner, repoName) = apiClient.getRepositoryInfo(config)
            
            return apiClient.callGitHubApi(
                "https://api.github.com/repos/${repoOwner}/${repoName}/hooks",
                'GET',
                null,
                config
            )
        } catch (Exception e) {
            throw new GitOperationException("Webhook一覧の取得に失敗しました: ${e.message}", e)
        }
    }
    
    /**
     * 特定のWebhookを取得する
     * @param hookId Webhook ID
     * @param config 設定（オプション）
     * @return Webhookの情報
     * @throws GitOperationException API呼び出しに失敗した場合
     */
    def getWebhook(def hookId, Map config = [:]) {
        try {
            def (repoOwner, repoName) = apiClient.getRepositoryInfo(config)
            
            return apiClient.callGitHubApi(
                "https://api.github.com/repos/${repoOwner}/${repoName}/hooks/${hookId}",
                'GET',
                null,
                config
            )
        } catch (Exception e) {
            throw new GitOperationException("Webhook情報の取得に失敗しました: ${e.message}", e)
        }
    }
    
    /**
     * Webhookを作成する
     * @param url Webhook送信先URL
     * @param events 受信するイベントのリスト
     * @param config 設定（オプション）
     * @return 作成されたWebhookの情報
     * @throws IllegalArgumentException 必須パラメータが不足している場合
     * @throws GitOperationException API呼び出しに失敗した場合
     */
    def createWebhook(String url, List<String> events, Map config = [:]) {
        try {
            // URLのバリデーション
            if (!url?.trim()) {
                throw new IllegalArgumentException("Webhook URLは必須です")
            }
            
            // URLフォーマットの検証
            if (!isValidUrl(url)) {
                throw new IllegalArgumentException("無効なURL形式です: ${url}")
            }
            
            // イベントリストのバリデーション
            if (!events || events.isEmpty()) {
                throw new IllegalArgumentException("イベントリストは必須です")
            }
            
            def (repoOwner, repoName) = apiClient.getRepositoryInfo(config)
            
            // デフォルト設定
            def defaultConfig = [
                active: true,
                contentType: 'json',
                sslVerify: true
            ]
            config = defaultConfig + config
            
            // Webhook設定の構築
            def webhookConfig = [
                url: url,
                content_type: config.contentType,
                insecure_ssl: config.sslVerify ? "0" : "1"
            ]
            
            // シークレットが指定されている場合は追加
            if (config.secret?.trim()) {
                webhookConfig.secret = config.secret
            }
            
            def payload = [
                name: 'web',
                active: config.active,
                events: events,
                config: webhookConfig
            ]
            
            return apiClient.callGitHubApi(
                "https://api.github.com/repos/${repoOwner}/${repoName}/hooks",
                'POST',
                payload,
                config
            )
        } catch (IllegalArgumentException e) {
            throw e  // バリデーションエラーはそのまま再スロー
        } catch (Exception e) {
            throw new GitOperationException("Webhookの作成に失敗しました: ${e.message}", e)
        }
    }
    
    /**
     * Webhookを更新する
     * @param hookId Webhook ID
     * @param updates 更新内容
     * @param config 設定（オプション）
     * @return 更新されたWebhookの情報
     * @throws IllegalArgumentException 必須パラメータが不足している場合
     * @throws GitOperationException API呼び出しに失敗した場合
     */
    def updateWebhook(def hookId, Map updates, Map config = [:]) {
        try {
            // Hook IDのバリデーション
            if (!hookId) {
                throw new IllegalArgumentException("Webhook IDは必須です")
            }
            
            // 更新内容のバリデーション
            if (!updates || updates.isEmpty()) {
                throw new IllegalArgumentException("更新内容は必須です")
            }
            
            def (repoOwner, repoName) = apiClient.getRepositoryInfo(config)
            
            // 更新用ペイロードの構築
            def payload = [:]
            
            if (updates.active != null) {
                payload.active = updates.active
            }
            
            if (updates.events) {
                payload.events = updates.events
            }
            
            // config の更新
            if (updates.url || updates.contentType || updates.secret || updates.sslVerify != null) {
                payload.config = [:]
                
                if (updates.url?.trim()) {
                    if (!isValidUrl(updates.url)) {
                        throw new IllegalArgumentException("無効なURL形式です: ${updates.url}")
                    }
                    payload.config.url = updates.url
                }
                
                if (updates.contentType) {
                    payload.config.content_type = updates.contentType
                }
                
                if (updates.secret?.trim()) {
                    payload.config.secret = updates.secret
                }
                
                if (updates.sslVerify != null) {
                    payload.config.insecure_ssl = updates.sslVerify ? "0" : "1"
                }
            }
            
            return apiClient.callGitHubApi(
                "https://api.github.com/repos/${repoOwner}/${repoName}/hooks/${hookId}",
                'PATCH',
                payload,
                config
            )
        } catch (IllegalArgumentException e) {
            throw e  // バリデーションエラーはそのまま再スロー
        } catch (Exception e) {
            throw new GitOperationException("Webhookの更新に失敗しました: ${e.message}", e)
        }
    }
    
    /**
     * Webhookを削除する
     * @param hookId Webhook ID
     * @param config 設定（オプション）
     * @return 削除結果
     * @throws IllegalArgumentException 必須パラメータが不足している場合
     * @throws GitOperationException API呼び出しに失敗した場合
     */
    def deleteWebhook(def hookId, Map config = [:]) {
        try {
            // Hook IDのバリデーション
            if (!hookId) {
                throw new IllegalArgumentException("Webhook IDは必須です")
            }
            
            def (repoOwner, repoName) = apiClient.getRepositoryInfo(config)
            
            return apiClient.callGitHubApi(
                "https://api.github.com/repos/${repoOwner}/${repoName}/hooks/${hookId}",
                'DELETE',
                null,
                config
            )
        } catch (IllegalArgumentException e) {
            throw e  // バリデーションエラーはそのまま再スロー
        } catch (Exception e) {
            throw new GitOperationException("Webhookの削除に失敗しました: ${e.message}", e)
        }
    }
    
    /**
     * Webhookをテストする（ping送信）
     * @param hookId Webhook ID
     * @param config 設定（オプション）
     * @return テスト結果
     * @throws IllegalArgumentException 必須パラメータが不足している場合
     * @throws GitOperationException API呼び出しに失敗した場合
     */
    def pingWebhook(def hookId, Map config = [:]) {
        try {
            // Hook IDのバリデーション
            if (!hookId) {
                throw new IllegalArgumentException("Webhook IDは必須です")
            }
            
            def (repoOwner, repoName) = apiClient.getRepositoryInfo(config)
            
            return apiClient.callGitHubApi(
                "https://api.github.com/repos/${repoOwner}/${repoName}/hooks/${hookId}/pings",
                'POST',
                null,
                config
            )
        } catch (IllegalArgumentException e) {
            throw e  // バリデーションエラーはそのまま再スロー
        } catch (Exception e) {
            throw new GitOperationException("Webhookのテストに失敗しました: ${e.message}", e)
        }
    }
    
    /**
     * 複数のWebhookを一括作成する
     * @param webhookConfigs Webhook設定のリスト
     * @param config 設定（オプション）
     * @return 作成結果のリスト
     */
    def batchCreateWebhooks(List<Map> webhookConfigs, Map config = [:]) {
        def results = []
        
        if (!webhookConfigs || webhookConfigs.isEmpty()) {
            script.echo "作成するWebhookが指定されていません"
            return results
        }
        
        script.echo "Webhookを一括作成しています: ${webhookConfigs.size()}件"
        
        webhookConfigs.each { webhookConfig ->
            try {
                def result = createWebhook(
                    webhookConfig.url,
                    webhookConfig.events,
                    config + (webhookConfig.config ?: [:])
                )
                
                results << [
                    success: true,
                    config: webhookConfig,
                    result: result
                ]
                
                script.echo "Webhook作成成功: ${webhookConfig.url}"
            } catch (Exception e) {
                results << [
                    success: false,
                    config: webhookConfig,
                    error: e.message
                ]
                
                script.echo "Webhook作成失敗: ${webhookConfig.url} - ${e.message}"
            }
        }
        
        def successCount = results.count { it.success }
        script.echo "Webhook一括作成完了: 成功 ${successCount}件 / 全体 ${webhookConfigs.size()}件"
        
        return results
    }
    
    // ==================== Deploy Key操作 ====================
    
    /**
     * Deploy Keyの一覧を取得する
     * @param config 設定（オプション）
     * @return Deploy Keyの一覧
     * @throws GitOperationException API呼び出しに失敗した場合
     */
    def listDeployKeys(Map config = [:]) {
        try {
            def (repoOwner, repoName) = apiClient.getRepositoryInfo(config)
            
            return apiClient.callGitHubApi(
                "https://api.github.com/repos/${repoOwner}/${repoName}/keys",
                'GET',
                null,
                config
            )
        } catch (Exception e) {
            throw new GitOperationException("Deploy Key一覧の取得に失敗しました: ${e.message}", e)
        }
    }
    
    /**
     * 特定のDeploy Keyを取得する
     * @param keyId Deploy Key ID
     * @param config 設定（オプション）
     * @return Deploy Keyの情報
     * @throws GitOperationException API呼び出しに失敗した場合
     */
    def getDeployKey(def keyId, Map config = [:]) {
        try {
            def (repoOwner, repoName) = apiClient.getRepositoryInfo(config)
            
            return apiClient.callGitHubApi(
                "https://api.github.com/repos/${repoOwner}/${repoName}/keys/${keyId}",
                'GET',
                null,
                config
            )
        } catch (Exception e) {
            throw new GitOperationException("Deploy Key情報の取得に失敗しました: ${e.message}", e)
        }
    }
    
    /**
     * Deploy Keyを作成する
     * @param title Deploy Keyのタイトル
     * @param key SSH公開鍵
     * @param readOnly 読み取り専用かどうか（デフォルト: true）
     * @param config 設定（オプション）
     * @return 作成されたDeploy Keyの情報
     * @throws IllegalArgumentException 必須パラメータが不足している場合
     * @throws GitOperationException API呼び出しに失敗した場合
     */
    def createDeployKey(String title, String key, boolean readOnly = true, Map config = [:]) {
        try {
            // タイトルのバリデーション
            if (!title?.trim()) {
                throw new IllegalArgumentException("Deploy Keyのタイトルは必須です")
            }
            
            // SSH鍵のバリデーション
            if (!key?.trim()) {
                throw new IllegalArgumentException("SSH公開鍵は必須です")
            }
            
            // SSH鍵フォーマットの検証と正規化
            def validatedKey = validateAndNormalizeDeployKey(key)
            
            def (repoOwner, repoName) = apiClient.getRepositoryInfo(config)
            
            def payload = [
                title: title.trim(),
                key: validatedKey,
                read_only: readOnly
            ]
            
            return apiClient.callGitHubApi(
                "https://api.github.com/repos/${repoOwner}/${repoName}/keys",
                'POST',
                payload,
                config
            )
        } catch (IllegalArgumentException e) {
            throw e  // バリデーションエラーはそのまま再スロー
        } catch (Exception e) {
            throw new GitOperationException("Deploy Keyの作成に失敗しました: ${e.message}", e)
        }
    }
    
    /**
     * Deploy Keyを削除する
     * @param keyId Deploy Key ID
     * @param config 設定（オプション）
     * @return 削除結果
     * @throws IllegalArgumentException 必須パラメータが不足している場合
     * @throws GitOperationException API呼び出しに失敗した場合
     */
    def deleteDeployKey(def keyId, Map config = [:]) {
        try {
            // Key IDのバリデーション
            if (!keyId) {
                throw new IllegalArgumentException("Deploy Key IDは必須です")
            }
            
            def (repoOwner, repoName) = apiClient.getRepositoryInfo(config)
            
            return apiClient.callGitHubApi(
                "https://api.github.com/repos/${repoOwner}/${repoName}/keys/${keyId}",
                'DELETE',
                null,
                config
            )
        } catch (IllegalArgumentException e) {
            throw e  // バリデーションエラーはそのまま再スロー
        } catch (Exception e) {
            throw new GitOperationException("Deploy Keyの削除に失敗しました: ${e.message}", e)
        }
    }
    
    /**
     * 複数のDeploy Keyを一括作成する
     * @param keyConfigs Deploy Key設定のリスト
     * @param config 設定（オプション）
     * @return 作成結果のリスト
     */
    def batchCreateDeployKeys(List<Map> keyConfigs, Map config = [:]) {
        def results = []
        
        if (!keyConfigs || keyConfigs.isEmpty()) {
            script.echo "作成するDeploy Keyが指定されていません"
            return results
        }
        
        script.echo "Deploy Keyを一括作成しています: ${keyConfigs.size()}件"
        
        keyConfigs.each { keyConfig ->
            try {
                def result = createDeployKey(
                    keyConfig.title,
                    keyConfig.key,
                    keyConfig.readOnly != null ? keyConfig.readOnly : true,
                    config
                )
                
                results << [
                    success: true,
                    config: keyConfig,
                    result: result
                ]
                
                script.echo "Deploy Key作成成功: ${keyConfig.title}"
            } catch (Exception e) {
                results << [
                    success: false,
                    config: keyConfig,
                    error: e.message
                ]
                
                script.echo "Deploy Key作成失敗: ${keyConfig.title} - ${e.message}"
            }
        }
        
        def successCount = results.count { it.success }
        script.echo "Deploy Key一括作成完了: 成功 ${successCount}件 / 全体 ${keyConfigs.size()}件"
        
        return results
    }
    
    /**
     * タイトルでDeploy Keyを検索する
     * @param title 検索するタイトル
     * @param config 設定（オプション）
     * @return マッチするDeploy Keyのリスト
     */
    def findDeployKeysByTitle(String title, Map config = [:]) {
        try {
            if (!title?.trim()) {
                throw new IllegalArgumentException("検索タイトルは必須です")
            }
            
            def deployKeys = listDeployKeys(config)
            
            return deployKeys.findAll { key ->
                key.title?.toLowerCase()?.contains(title.toLowerCase())
            }
        } catch (IllegalArgumentException e) {
            throw e
        } catch (Exception e) {
            throw new GitOperationException("Deploy Keyの検索に失敗しました: ${e.message}", e)
        }
    }
    
    // ==================== ヘルパーメソッド ====================
    
    /**
     * URLの形式を検証する
     * @param url 検証するURL
     * @return 有効な場合はtrue
     */
    private boolean isValidUrl(String url) {
        if (!url?.trim()) {
            return false
        }
        
        try {
            def urlObj = new URL(url)
            def protocol = urlObj.protocol?.toLowerCase()
            
            // HTTPSを推奨するが、HTTPも許可
            if (!(protocol == 'https' || protocol == 'http')) {
                return false
            }
            
            // ホスト名が存在することを確認
            if (!urlObj.host?.trim()) {
                return false
            }
            
            return true
        } catch (MalformedURLException e) {
            return false
        }
    }
    
    /**
     * SSH公開鍵を検証し、正規化する
     * @param key SSH公開鍵
     * @return 正規化されたSSH公開鍵
     * @throws IllegalArgumentException 無効な鍵の場合
     */
    private String validateAndNormalizeDeployKey(String key) {
        if (!key?.trim()) {
            throw new IllegalArgumentException("SSH公開鍵が空です")
        }
        
        def cleanKey = key.trim()
        def parts = cleanKey.split(/\s+/)
        
        if (parts.length < 2) {
            throw new IllegalArgumentException("SSH公開鍵の形式が無効です。'type key [comment]' の形式である必要があります")
        }
        
        def keyType = parts[0]
        def keyData = parts[1]
        
        // サポートされている鍵タイプの確認
        def supportedKeyTypes = [
            'ssh-rsa',
            'ssh-ed25519',
            'ecdsa-sha2-nistp256',
            'ecdsa-sha2-nistp384', 
            'ecdsa-sha2-nistp521'
        ]
        
        if (!supportedKeyTypes.contains(keyType)) {
            throw new IllegalArgumentException("サポートされていないSSH鍵タイプです: ${keyType}")
        }
        
        // 鍵データの基本的な長さチェック
        if (keyData.length() < 50) {
            throw new IllegalArgumentException("SSH鍵データが短すぎます")
        }
        
        // Base64形式の基本チェック
        if (!keyData.matches(/^[A-Za-z0-9+\/]+=*$/)) {
            throw new IllegalArgumentException("SSH鍵データのBase64形式が無効です")
        }
        
        // RSA鍵の場合は最小長チェック
        if (keyType == 'ssh-rsa' && keyData.length() < 300) {
            script.echo "警告: RSA鍵が短い可能性があります。2048bit以上を推奨します。"
        }
        
        // 正規化: タイプと鍵データのみを返す（コメント部分は除く）
        return "${keyType} ${keyData}"
    }
    
    /**
     * 設定情報をサニタイズして表示用文字列に変換する
     * @param config 設定情報
     * @return サニタイズされた設定情報
     */
    private String sanitizeConfigForDisplay(Map config) {
        def sanitized = [:]
        
        config.each { key, value ->
            if (key.toLowerCase().contains('secret') || 
                key.toLowerCase().contains('token') ||
                key.toLowerCase().contains('password')) {
                sanitized[key] = '***'
            } else if (key == 'key' && value?.toString()?.startsWith('ssh-')) {
                // SSH鍵の場合は最初の部分のみ表示
                def keyParts = value.toString().split(' ')
                if (keyParts.length >= 2) {
                    sanitized[key] = "${keyParts[0]} ${keyParts[1].take(20)}..."
                } else {
                    sanitized[key] = value.toString().take(50) + '...'
                }
            } else {
                sanitized[key] = value
            }
        }
        
        return sanitized.toString()
    }
}