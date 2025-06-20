package jp.co.tielec.git

import jp.co.tielec.utils.DateUtils

/**
 * GitHub Pull Request操作に関するクラス
 */
class GitHubPullRequest implements Serializable {
    private static final long serialVersionUID = 1L
    
    protected def script
    protected GitHubApiClient apiClient
    
    /**
     * コンストラクタ
     * @param script Pipelineスクリプトコンテキスト
     */
    GitHubPullRequest(def script) {
        this.script = script
        this.apiClient = new GitHubApiClient(script)
    }
    
    /**
     * PRの情報を取得する
     * @param prNumber PR番号
     * @param config 設定（オプション）
     * @return PRの情報
     * @throws GitOperationException API呼び出しに失敗した場合
     */
    def getPullRequestInfo(int prNumber, Map config = [:]) {
        try {
            def (repoOwner, repoName) = apiClient.getRepositoryInfo(config)
            
            return apiClient.callGitHubApi(
                "https://api.github.com/repos/${repoOwner}/${repoName}/pulls/${prNumber}",
                'GET',
                null,
                config
            )
        } catch (Exception e) {
            throw new GitOperationException("PR情報の取得に失敗しました: ${e.message}", e)
        }
    }
    
    /**
     * 最新のPull Requestを取得する
     * @param config 設定（オプション）
     * @return 最新のPR情報
     * @throws GitOperationException API呼び出しに失敗した場合
     */
    def getLatestPullRequest(Map config = [:]) {
        def (repoOwner, repoName) = apiClient.getRepositoryInfo(config)
        
        def defaultConfig = [
            state: 'open',
            per_page: 1,
            sort: 'created',
            direction: 'desc'
        ]
        config = defaultConfig + config
        
        try {
            def response = apiClient.callGitHubApi(
                "https://api.github.com/repos/${repoOwner}/${repoName}/pulls?" +
                "state=${config.state}&sort=${config.sort}&direction=${config.direction}&per_page=${config.per_page}",
                'GET',
                null,
                config
            )
            
            // オープンなPRが存在しないケースを明示的に処理
            if (!response || response.size() == 0) {
                return null
            }
            
            return response[0]
        } catch (Exception e) {
            throw new GitOperationException("最新PRの取得に失敗しました: ${e.message}", e)
        }
    }
    
    /**
     * 最新のプルリクエスト情報を安全に取得する（例外をスローしない）
     * @param repoOwner リポジトリのオーナー
     * @param repoName リポジトリ名
     * @return 成功/失敗のステータスとデータを含むマップ
     */
    def safeGetLatestPullRequest(String repoOwner, String repoName) {
        def result = [
            success: true,
            data: null,
            message: ""
        ]
        
        try {
            def pullRequests = null
            try {
                pullRequests = apiClient.callGitHubApi(
                    "https://api.github.com/repos/${repoOwner}/${repoName}/pulls?" +
                    "state=open&sort=created&direction=desc&per_page=1",
                    'GET'
                )
            } catch (Exception e) {
                result.success = false
                result.message = "API呼び出しに失敗しました: ${e.message}"
                return result
            }
            
            if (pullRequests && pullRequests.size() > 0) {
                result.data = pullRequests[0]
            }
        } catch (Exception e) {
            result.success = false
            result.message = "最新PR取得中にエラーが発生: ${e.message}"
        }
        
        return result
    }
    
    /**
     * マージ済みのPRを取得する
     * @param config 設定（オプション）
     * @return マージ済みPRのリスト
     * @throws IllegalArgumentException 必須パラメータが不足している場合
     * @throws GitOperationException API呼び出しに失敗した場合
     */
    def getMergedPullRequests(Map config = [:]) {
        try {
            // リポジトリ情報の検証
            if (!config.repoOwner?.trim() || !config.repoName?.trim()) {
                throw new IllegalArgumentException("リポジトリオーナーとリポジトリ名は必須です")
            }
            
            // デフォルト設定
            def defaultConfig = [
                credentialsId: 'github-app-credentials',
                base: 'main',
                maxResults: 10,
                sort: 'merged',
                direction: 'asc',
                perPage: 30 // 1ページあたりの取得数
            ]
            config = defaultConfig + config
            
            def mergedPRs = []
            def page = 1
            
            // 最大件数に達するまでAPIを呼び出す
            while (mergedPRs.size() < config.maxResults) {
                def apiUrl = "https://api.github.com/repos/${config.repoOwner}/${config.repoName}/pulls?" +
                    "state=closed&base=${config.base}&sort=${config.sort}&direction=${config.direction}" +
                    "&per_page=${config.perPage}&page=${page}"
                
                def response = apiClient.callGitHubApi(
                    apiUrl,
                    'GET',
                    null,
                    config
                )
                
                // レスポンスが空の場合は終了
                if (!response || response.size() == 0) {
                    break
                }
                
                // マージ済みPRのみをフィルタリング
                def filteredPRs = response.findAll { pr -> pr.merged_at != null }
                
                // フィルタリング後に結果がない場合は終了
                if (filteredPRs.isEmpty()) {
                    break
                }
                
                // 結果を追加
                mergedPRs.addAll(filteredPRs)
                
                // 最大件数に達した場合は切り詰める
                if (mergedPRs.size() > config.maxResults) {
                    mergedPRs = mergedPRs.take(config.maxResults).toList()
                    break
                }
                
                // 次のページへ
                page++
            }
            
            return mergedPRs
        } catch (IllegalArgumentException e) {
            throw e  // バリデーションエラーはそのまま再スロー
        } catch (Exception e) {
            throw new GitOperationException("マージ済みPRの取得に失敗しました: ${e.message}", e)
        }
    }
    
    /**
     * 指定された日付範囲内でマージされたPRから自動生成コメントを抽出する
     * @param config 設定（オプション）
     * @return PR情報とコメントの配列
     * @throws IllegalArgumentException 必須パラメータが不足している場合
     * @throws GitOperationException API呼び出しに失敗した場合
     */
    def extractCommentsFromMergedPRsByDate(Map config = [:]) {
        try {
            // リポジトリ情報の検証
            if (!config.repoOwner?.trim() || !config.repoName?.trim()) {
                throw new IllegalArgumentException("リポジトリオーナーとリポジトリ名は必須です")
            }
            
            // 日付範囲の検証
            if (!config.startDate?.trim() || !config.endDate?.trim()) {
                throw new IllegalArgumentException("開始日と終了日は必須です")
            }
            
            // 日付フォーマットの検証
            DateUtils.validateDateFormat(config.startDate)
            DateUtils.validateDateFormat(config.endDate)
            
            // 終了日に23:59:59を追加して日付範囲を完全にカバー
            def startDateFormatted = DateUtils.formatDateToIso(config.startDate, true)
            def endDateFormatted = DateUtils.formatDateToIso(config.endDate, false)
            
            // デフォルト設定
            def defaultConfig = [
                credentialsId: 'github-app-credentials',
                base: 'main',
                sort: 'updated',  // 'merged' から 'updated' に変更
                direction: 'desc', // 新しいものから取得するようにdescに変更
                commentTag: 'auto-generated-comment',
                perPage: 100 // ページサイズを増やして効率化
            ]
            config = defaultConfig + config
            
            // 日付範囲内のマージ済みPRを取得
            def mergedPRs = []
            def page = 1
            def hasMore = true
            def maxPages = 20 // 無限ループ防止
            
            script.echo "期間内のマージ済みPRを取得しています: ${config.startDate} 〜 ${config.endDate}"
            script.echo "検索対象期間（ISO形式）: ${startDateFormatted} 〜 ${endDateFormatted}"
            
            while (hasMore && page <= maxPages) {
                def apiUrl = "https://api.github.com/repos/${config.repoOwner}/${config.repoName}/pulls?" +
                    "state=closed&base=${config.base}&sort=${config.sort}&direction=${config.direction}" +
                    "&per_page=${config.perPage}&page=${page}"
                
                script.echo "API URL: ${apiUrl}"
                
                def response = apiClient.callGitHubApi(
                    apiUrl,
                    'GET',
                    null,
                    config
                )
                
                // レスポンスが空の場合は終了
                if (!response || response.size() == 0) {
                    script.echo "APIレスポンスが空です。ページネーション終了。"
                    hasMore = false
                    break
                }
                
                script.echo "ページ ${page}: ${response.size()}件のクローズされたPRを取得"
                
                // デバッグ: 最初の数件のPR情報を出力
                if (page == 1 && response.size() > 0) {
                    script.echo "=== デバッグ情報: 最初の3件のPR ==="
                    response.take(3).eachWithIndex { pr, index ->
                        script.echo "PR #${pr.number}: merged_at=${pr.merged_at}, closed_at=${pr.closed_at}, state=${pr.state}"
                    }
                    script.echo "================================="
                }
                
                // マージ済みPRのみをフィルタリング
                def pageFilteredPRs = response.findAll { pr -> 
                    def mergedAtStr = pr.merged_at
                    if (mergedAtStr == null || 
                        mergedAtStr.toString() == "null" || 
                        mergedAtStr.toString().isEmpty()) {
                        return false
                    }
                    
                    // 日付範囲内かどうかを確認
                    try {
                        def mergedDate = DateUtils.parseIsoDateTime(mergedAtStr.toString())
                        def startDate = DateUtils.parseIsoDateTime(startDateFormatted)
                        def endDate = DateUtils.parseIsoDateTime(endDateFormatted)
                        
                        def isInRange = DateUtils.isDateInRange(mergedDate, startDate, endDate)
                        if (isInRange) {
                            script.echo "期間内PR発見: #${pr.number} (merged: ${mergedAtStr})"
                        }
                        return isInRange
                    } catch (Exception e) {
                        script.echo "日付の比較に失敗しました (PR #${pr.number}): ${e.message}"
                        return false
                    }
                }
                
                script.echo "ページ ${page}: ${pageFilteredPRs.size()}件が期間内でマージ済み"
                
                // フィルタリング後の結果を追加
                if (pageFilteredPRs.size() > 0) {
                    mergedPRs.addAll(pageFilteredPRs)
                }
                
                // 早期終了の条件をチェック
                def shouldContinue = true
                
                // direction=descの場合、古いPRに到達したら終了
                if (config.direction == 'desc') {
                    def oldestPRInPage = response.min { pr -> 
                        pr.updated_at ?: pr.closed_at ?: "1970-01-01T00:00:00Z" 
                    }
                    if (oldestPRInPage) {
                        try {
                            def oldestDate = DateUtils.parseIsoDateTime(oldestPRInPage.updated_at ?: oldestPRInPage.closed_at)
                            def startDate = DateUtils.parseIsoDateTime(startDateFormatted)
                            if (oldestDate.before(startDate)) {
                                script.echo "検索期間より古いPRに到達しました。検索終了。"
                                shouldContinue = false
                            }
                        } catch (Exception e) {
                            script.echo "日付比較エラー: ${e.message}"
                        }
                    }
                }
                
                // 応答数がperPageより少ない場合は終了
                if (response.size() < config.perPage) {
                    script.echo "最終ページに到達しました。"
                    hasMore = false
                    break
                }
                
                if (!shouldContinue) {
                    hasMore = false
                    break
                }
                
                // 次のページへ
                page++
            }
            
            if (page > maxPages) {
                script.echo "警告: 最大ページ数(${maxPages})に到達しました。すべてのPRを取得できていない可能性があります。"
            }
            
            script.echo "期間内でマージされたPRの件数: ${mergedPRs.size()}"
            
            def results = []
            
            // 各PRのコメントを抽出
            mergedPRs.each { pr ->
                script.echo "PR #${pr.number} のコメントを抽出中..."
                def comments = extractAutoGeneratedComments(pr.number, config)
                
                if (comments && comments.size() > 0) {
                    def prData = [
                        pr_info: new LinkedHashMap(pr),
                        comments: new ArrayList(comments)
                    ]
                    
                    results.add(prData)
                    script.echo "PR #${pr.number}: ${comments.size()}件の自動生成コメントを発見"
                } else {
                    script.echo "PR #${pr.number}: 自動生成コメントなし"
                }
            }
            
            script.echo "自動生成コメントを含むPRの件数: ${results.size()}"
            
            return results
        } catch (IllegalArgumentException e) {
            throw e  // バリデーションエラーはそのまま再スロー
        } catch (Exception e) {
            script.echo "エラー詳細: ${e.message}"
            script.echo "スタックトレース: ${e.getStackTrace()}"
            throw new GitOperationException("日付範囲でのマージ済みPRからのコメント抽出に失敗しました: ${e.message}", e)
        }
    }
        
    /**
     * すべてのPRが終了日以降かを確認
     * @param prs PRのリスト
     * @param endDateFormatted フォーマット済みの終了日
     * @return すべてのPRが終了日以降の場合はtrue
     */
    private boolean isAllPRsPastEndDate(def prs, String endDateFormatted) {
        def allPastEndDate = true
        for (pr in prs) {
            def mergedAtStr = pr.merged_at
            if (mergedAtStr == null || 
                mergedAtStr.toString() == "null" || 
                mergedAtStr.toString().isEmpty()) {
                continue
            }
            
            try {
                def mergedDate = DateUtils.parseIsoDateTime(mergedAtStr.toString())
                def endDate = DateUtils.parseIsoDateTime(endDateFormatted)
                
                if (!mergedDate.after(endDate)) {
                    allPastEndDate = false
                    break
                }
            } catch (Exception e) {
                allPastEndDate = false
                script.echo "日付の比較に失敗しました (終了日チェック): ${e.message}"
                break
            }
        }
        
        return allPastEndDate
    }
    
    /**
     * すべてのPRが開始日より前かを確認
     * @param prs PRのリスト
     * @param startDateFormatted フォーマット済みの開始日
     * @return すべてのPRが開始日より前の場合はtrue
     */
    private boolean isAllPRsBeforeStartDate(def prs, String startDateFormatted) {
        def allBeforeStartDate = true
        for (pr in prs) {
            def mergedAtStr = pr.merged_at
            if (mergedAtStr == null || 
                mergedAtStr.toString() == "null" || 
                mergedAtStr.toString().isEmpty()) {
                continue
            }
            
            try {
                def mergedDate = DateUtils.parseIsoDateTime(mergedAtStr.toString())
                def startDate = DateUtils.parseIsoDateTime(startDateFormatted)
                
                if (!mergedDate.before(startDate)) {
                    allBeforeStartDate = false
                    break
                }
            } catch (Exception e) {
                allBeforeStartDate = false
                script.echo "日付の比較に失敗しました (開始日チェック): ${e.message}"
                break
            }
        }
        
        return allBeforeStartDate
    }
    
    /**
     * PR内の自動生成コメントを抽出する
     * @param prNumber PR番号
     * @param config 設定（オプション）
     * @return 自動生成コメントのリスト
     * @throws IllegalArgumentException 必須パラメータが不足している場合
     * @throws GitOperationException API呼び出しに失敗した場合
     */
    def extractAutoGeneratedComments(int prNumber, Map config = [:]) {
        try {
            // リポジトリ情報の検証
            if (!config.repoOwner?.trim() || !config.repoName?.trim()) {
                throw new IllegalArgumentException("リポジトリオーナーとリポジトリ名は必須です")
            }
            
            // デフォルト設定
            def defaultConfig = [
                credentialsId: 'github-app-credentials',
                commentTag: 'auto-generated-comment'
            ]
            config = defaultConfig + config
            
            // PRのコメント一覧を取得
            def comments = getPullRequestComments(prNumber, config)
            
            def autoGenComments = []
            
            // コメントタグが含まれるコメントをフィルタリング
            comments.each { comment ->
                if (comment.body?.contains("<!-- ${config.commentTag}")) {
                    // 新しいマップに必要なプロパティをコピー
                    def newComment = new LinkedHashMap(comment)
                    
                    // メタデータを抽出して追加
                    newComment.metadata = extractCommentMetadata(comment.body, config.commentTag)
                    
                    autoGenComments.add(newComment)
                }
            }
            
            return autoGenComments
        } catch (IllegalArgumentException e) {
            throw e  // バリデーションエラーはそのまま再スロー
        } catch (Exception e) {
            throw new GitOperationException("自動生成コメントの抽出に失敗しました: ${e.message}", e)
        }
    }
    
    /**
     * コメント本文からメタデータを抽出する
     * @param commentBody コメント本文
     * @param commentTag コメントタグ（デフォルト: 'auto-generated-comment'）
     * @return メタデータのマップ
     */
    private def extractCommentMetadata(String commentBody, String commentTag = 'auto-generated-comment') {
        def metadata = [:]
        
        if (!commentBody) {
            return metadata
        }
        
        // タグのブロックを抽出
        def tagStart = commentBody.indexOf("<!-- ${commentTag}")
        def tagEnd = commentBody.indexOf("-->", tagStart)
        
        if (tagStart == -1 || tagEnd == -1) {
            return metadata
        }
        
        def tagContent = commentBody.substring(tagStart, tagEnd)
        
        // メタデータを行ごとに処理
        def lines = tagContent.split('\n')
        for (line in lines) {
            line = line.trim()
            if (line.contains(':')) {
                def parts = line.split(':', 2)
                def key = parts[0].trim()
                def value = parts[1].trim()
                
                // タグ行自体は除外
                if (key && !key.startsWith("<!--")) {
                    metadata[key] = value
                }
            }
        }
        
        return metadata
    }
    
    /**
     * マージ済みPRから自動生成コメントをまとめて抽出する
     * @param config 設定（オプション）
     * @return PR情報とコメントの配列
     * @throws IllegalArgumentException 必須パラメータが不足している場合
     * @throws GitOperationException API呼び出しに失敗した場合
     */
    def extractCommentsFromMergedPRs(Map config = [:]) {
        try {
            // リポジトリ情報の検証
            if (!config.repoOwner?.trim() || !config.repoName?.trim()) {
                throw new IllegalArgumentException("リポジトリオーナーとリポジトリ名は必須です")
            }
            
            // マージ済みPRを取得
            def mergedPRs = getMergedPullRequests(config)
            
            def results = []
            
            // 各PRのコメントを抽出
            mergedPRs.each { pr ->
                def comments = extractAutoGeneratedComments(pr.number, config)
                
                if (comments) {
                    def prData = [
                        pr_info: new LinkedHashMap(pr),
                        comments: new ArrayList(comments)
                    ]
                    
                    results.add(prData)
                }
            }
            
            return results
        } catch (IllegalArgumentException e) {
            throw e  // バリデーションエラーはそのまま再スロー
        } catch (Exception e) {
            throw new GitOperationException("マージ済みPRからのコメント抽出に失敗しました: ${e.message}", e)
        }
    }
    
    /**
     * PRの差分情報を取得する
     * @param prNumber PR番号
     * @param config 設定（オプション）
     * @return 差分情報のリスト
     * @throws GitOperationException API呼び出しに失敗した場合
     */
    def getPullRequestDiff(int prNumber, Map config = [:]) {
        try {
            def (repoOwner, repoName) = apiClient.getRepositoryInfo(config)
            
            return apiClient.callGitHubApi(
                "https://api.github.com/repos/${repoOwner}/${repoName}/pulls/${prNumber}/files",
                'GET',
                null,
                config
            )
        } catch (Exception e) {
            throw new GitOperationException("PR差分の取得に失敗しました: ${e.message}", e)
        }
    }
    
    /**
    * PRのファイル一覧を取得する
    * @param prNumberParam PR番号または"latest"
    * @param targetBranch "latest"使用時のベースブランチ（オプション）
    * @param config 設定（オプション）
    * @return ファイル名とステータスのリスト
    * @throws GitOperationException API呼び出しに失敗した場合
    */
    def getPullRequestFiles(def prNumberParam, String targetBranch = 'main', Map config = [:]) {
        try {
            def (repoOwner, repoName) = apiClient.getRepositoryInfo(config)
            def prNumber = prNumberParam
            
            // "latest"が指定された場合は最新のマージ済みPRを検索（大文字小文字を区別しない）
            if (prNumberParam?.toString()?.toLowerCase() == "latest") {
                // GitHubのクエリパラメータを構築
                def queryParams = [
                    state: 'closed',
                    base: targetBranch,
                    sort: 'updated',
                    direction: 'desc'
                ]
                
                // URLにクエリパラメータを追加
                def queryString = queryParams.collect { key, value -> 
                    "${key}=${URLEncoder.encode(value.toString(), 'UTF-8')}" 
                }.join('&')
                
                def url = "https://api.github.com/repos/${repoOwner}/${repoName}/pulls?${queryString}"
                
                // API呼び出し
                def prList = apiClient.callGitHubApi(url, 'GET', null, config)
                
                // マージ済みのPRを検索
                def latestMergedPR = prList.find { it.merged_at != null }
                if (!latestMergedPR) {
                    script.echo "マージ済みのPRが見つかりませんでした。ターゲットブランチ: ${targetBranch}"
                    return []
                }
                
                prNumber = latestMergedPR.number
                script.echo "最新のマージ済みPR: #${prNumber} (ターゲットブランチ: ${targetBranch})"
            } else if (prNumberParam instanceof String) {
                // 文字列の場合は整数に変換
                prNumber = prNumberParam.isInteger() ? prNumberParam.toInteger() : prNumberParam
            }
            
            // PRの存在チェック
            if (!(prNumber instanceof Integer)) {
                script.echo "無効なPR番号: ${prNumberParam}"
                return []
            }
            
            // PR情報の取得
            def prInfo = null
            try {
                prInfo = apiClient.callGitHubApi(
                    "https://api.github.com/repos/${repoOwner}/${repoName}/pulls/${prNumber}",
                    'GET',
                    null,
                    config
                )
            } catch (Exception e) {
                // クローズ済みPRを再検索
                try {
                    prInfo = apiClient.callGitHubApi(
                        "https://api.github.com/repos/${repoOwner}/${repoName}/pulls/${prNumber}?state=closed",
                        'GET',
                        null, 
                        config
                    )
                } catch (Exception ex) {
                    script.echo "PR #${prNumber} が見つかりませんでした。"
                    return []
                }
            }
            
            if (!prInfo) {
                script.echo "PR #${prNumber} の情報を取得できませんでした。"
                return []
            }
            
            script.echo "PR #${prNumber} 状態: ${prInfo.state}, マージ済み: ${prInfo.merged}"
            
            // PRファイル一覧取得
            def prFiles = apiClient.callGitHubApi(
                "https://api.github.com/repos/${repoOwner}/${repoName}/pulls/${prNumber}/files",
                'GET',
                null,
                config
            )
            
            def result = []
            prFiles.each { file ->
                result << [
                    filename: file.filename,
                    status: file.status
                ]
            }
            
            script.echo "PR (#${prNumber}) から ${result.size()} 個のファイルを取得しました。" 
            return result
        } catch (Exception e) {
            throw new GitOperationException("PRファイルの取得に失敗しました: ${e.message}", e)
        }
    }
        
    /**
     * PRにコメントを投稿する
     * @param prNumber PR番号
     * @param comment コメント内容
     * @param config 設定（オプション）
     * @return コメントの投稿結果
     * @throws IllegalArgumentException コメントが空の場合
     * @throws GitOperationException API呼び出しに失敗した場合
     */
    def createPullRequestComment(int prNumber, String comment, Map config = [:]) {
        try {
            // コメント内容のバリデーション
            if (!comment?.trim()) {
                throw new IllegalArgumentException("コメントは必須です")
            }
            
            def (repoOwner, repoName) = apiClient.getRepositoryInfo(config)
            
            return apiClient.callGitHubApi(
                "https://api.github.com/repos/${repoOwner}/${repoName}/issues/${prNumber}/comments",
                'POST',
                [body: comment],
                config
            )
        } catch (IllegalArgumentException e) {
            throw e  // バリデーションエラーはそのまま再スロー
        } catch (Exception e) {
            throw new GitOperationException("PRコメントの作成に失敗しました: ${e.message}", e)
        }
    }
    
    /**
     * PRの既存コメントを更新する
     * @param commentId コメントID（数値または文字列）
     * @param comment 新しいコメント内容
     * @param config 設定（オプション）
     * @return 更新結果
     * @throws IllegalArgumentException パラメータが不正な場合
     * @throws GitOperationException API呼び出しに失敗した場合
     */
    def updatePullRequestComment(def commentId, String comment, Map config = [:]) {
        try {
            // commentIdの型チェック
            if (!(commentId instanceof Number || commentId instanceof String)) {
                throw new IllegalArgumentException("コメントIDは数値または文字列である必要があります")
            }
            
            // コメント内容のバリデーション
            if (!comment?.trim()) {
                throw new IllegalArgumentException("コメントは必須です")
            }
            
            // リポジトリ情報のバリデーション
            if (!config.repoOwner?.trim() || !config.repoName?.trim()) {
                throw new IllegalArgumentException("リポジトリオーナーとリポジトリ名は必須です")
            }
            
            return apiClient.callGitHubApi(
                "https://api.github.com/repos/${config.repoOwner}/${config.repoName}/issues/comments/${commentId}",
                'PATCH',
                [body: comment],
                config
            )
        } catch (IllegalArgumentException e) {
            throw e  // バリデーションエラーはそのまま再スロー
        } catch (Exception e) {
            throw new GitOperationException("PRコメントの更新に失敗しました: ${e.message}", e)
        }
    }
    
    /**
     * PRのタイトルを更新する
     * @param prNumber PR番号
     * @param title 新しいタイトル
     * @param config 設定（オプション）
     * @return 更新結果
     * @throws IllegalArgumentException タイトルが空の場合
     * @throws GitOperationException API呼び出しに失敗した場合
     */
    def updatePullRequestTitle(int prNumber, String title, Map config = [:]) {
        try {
            // タイトルのバリデーション
            if (!title?.trim()) {
                throw new IllegalArgumentException("タイトルは必須です")
            }
            
            def (repoOwner, repoName) = apiClient.getRepositoryInfo(config)
            
            return apiClient.callGitHubApi(
                "https://api.github.com/repos/${repoOwner}/${repoName}/pulls/${prNumber}",
                'PATCH',
                [title: title],
                config
            )
        } catch (IllegalArgumentException e) {
            throw e  // バリデーションエラーはそのまま再スロー
        } catch (Exception e) {
            throw new GitOperationException("PRタイトルの更新に失敗しました: ${e.message}", e)
        }
    }
    
    /**
     * PRのコメント一覧を取得する
     * @param prNumber PR番号
     * @param config 設定（オプション）
     * @return コメント一覧
     * @throws GitOperationException API呼び出しに失敗した場合
     */
    def getPullRequestComments(int prNumber, Map config = [:]) {
        try {
            def (repoOwner, repoName) = apiClient.getRepositoryInfo(config)
            
            return apiClient.callGitHubApi(
                "https://api.github.com/repos/${repoOwner}/${repoName}/issues/${prNumber}/comments",
                'GET',
                null,
                config
            )
        } catch (Exception e) {
            throw new GitOperationException("PRコメントの取得に失敗しました: ${e.message}", e)
        }
    }
    
    /**
     * 特定のユーザーのPRコメントを検索する
     * @param prNumber PR番号
     * @param username 検索対象のユーザー名
     * @param config 設定（オプション）
     * @return 該当するコメントのリスト
     */
    def findUserComment(int prNumber, String username, Map config = [:]) {
        def comments = getPullRequestComments(prNumber, config)
        return comments.findAll { it.user.login == username }
    }
    
    /**
     * PRコメントを更新または新規作成する
     * @param prNumber PR番号
     * @param comment コメント内容
     * @param username 更新対象のユーザー名（既存コメント検索用）
     * @param config 設定（オプション）
     * @return 更新または作成されたコメント
     */
    def upsertPullRequestComment(int prNumber, String comment, String username, Map config = [:]) {
        def existingComment = findUserComment(prNumber, username, config)
        
        if (existingComment) {
            return updatePullRequestComment(existingComment[0].id, comment, config)
        } else {
            return createPullRequestComment(prNumber, comment, config)
        }
    }
    
    /**
     * GitHub Pull Requestを作成する
     * @param title PRのタイトル
     * @param body PRの本文
     * @param headBranch 変更を含むブランチ名
     * @param baseBranch マージ先のブランチ名
     * @param config 追加設定
     * @return 作成されたPRの情報
     * @throws IllegalArgumentException 必須パラメータが不足している場合
     * @throws GitOperationException PR作成に失敗した場合
     */
    def createPullRequest(String title, String body, String headBranch, String baseBranch, Map config = [:]) {
        try {
            // 必須パラメータのバリデーション
            if (!title?.trim()) throw new IllegalArgumentException("PRタイトルは必須です")
            if (!headBranch?.trim()) throw new IllegalArgumentException("変更元ブランチ名は必須です")
            if (!baseBranch?.trim()) throw new IllegalArgumentException("マージ先ブランチ名は必須です")
            
            def (repoOwner, repoName) = apiClient.getRepositoryInfo(config)
            
            // PR作成のためのペイロード
            def payload = [
                title: title,
                body: body,
                head: headBranch,
                base: baseBranch
            ]
            
            return apiClient.callGitHubApi(
                "https://api.github.com/repos/${repoOwner}/${repoName}/pulls",
                'POST',
                payload,
                config
            )
        } catch (IllegalArgumentException e) {
            throw e  // バリデーションエラーはそのまま再スロー
        } catch (Exception e) {
            throw new GitOperationException("プルリクエストの作成に失敗しました: ${e.message}", e)
        }
    }
}