package jp.co.tielec.git

/**
 * Git操作の基本機能を提供するクラス
 */
class GitClientBase implements Serializable {
    private static final long serialVersionUID = 1L

    // 認証方式の列挙型
    enum AuthMethod {
        PAT,        // Personal Access Token認証
        DEPLOY_KEY  // Deploy Key (SSH)認証
    }

    // 定数定義
    private static final String DEFAULT_GIT_EMAIL = 'tielec-dev-jenkins@tielec.net'
    private static final String DEFAULT_GIT_USERNAME = 'TIELEC Dev Jenkins'
    private static final String DEFAULT_PAT_CREDENTIALS_ID = 'github-pat'
    private static final int DEFAULT_CHECKOUT_TIMEOUT = 60
    private static final int DEFAULT_CLONE_DEPTH = 1
    private static final String DEFAULT_BASE_BRANCH = 'main'
    
    protected def script
    protected Map defaultConfig
    
    /**
     * コンストラクタ
     * @param script Pipelineスクリプトコンテキスト
     */
    GitClientBase(def script) {
        this.script = script
        this.defaultConfig = [
            email: DEFAULT_GIT_EMAIL,
            username: DEFAULT_GIT_USERNAME,
            credentialsId: DEFAULT_PAT_CREDENTIALS_ID,
            checkoutTimeout: DEFAULT_CHECKOUT_TIMEOUT,
            shallowClone: true,
            cloneDepth: DEFAULT_CLONE_DEPTH,
            wipeWorkspace: true,
            createNewBranch: true,
            baseBranch: DEFAULT_BASE_BRANCH
        ]
    }
    
    /**
     * Gitの基本設定を行う
     * @param config 設定（オプション）
     */
    def setupGit(Map config = [:]) {
        def effectiveConfig = defaultConfig + config
        
        script.sh """
            git config user.email "${effectiveConfig.email}"
            git config user.name "${effectiveConfig.username}"
        """
    }
    
    // ==========================================
    // リポジトリチェックアウト関連メソッド
    // ==========================================
    
    /**
     * リポジトリをチェックアウトする（認証情報IDを明示的に指定）
     * @param url リポジトリURL
     * @param branch ブランチ名
     * @param credentialsId 認証情報ID
     * @param config 設定（オプション）
     */
    def checkoutRepository(String url, String branch, String credentialsId, Map config = [:]) {
        // URLからAuthMethodを判断し、認証情報IDをconfigに追加
        AuthMethod authMethod = detectAuthMethod(url)
        
        Map updatedConfig = new HashMap(config)
        updatedConfig.put('credentialsId', credentialsId)
        
        checkoutRepositoryWithAuth(url, branch, authMethod, updatedConfig)
    }
    
    /**
     * 統合されたリポジトリチェックアウトメソッド
     * @param repoUrl リポジトリURL
     * @param branch ブランチ名
     * @param authMethod 認証方式
     * @param config 設定（オプション）
     * @throws IllegalArgumentException 必須パラメータが不足している場合
     * @throws GitOperationException チェックアウトに失敗した場合
     */
    private def checkoutRepositoryWithAuth(String repoUrl, String branch, AuthMethod authMethod, Map config = [:]) {
        def effectiveConfig = defaultConfig + config
        
        // パラメータのバリデーション
        validateRepositoryParams(repoUrl, branch, authMethod, effectiveConfig)
        
        // 認証方式に応じたログメッセージを表示
        logCheckoutInfo(repoUrl, branch, authMethod, effectiveConfig)
        
        try {
            // ワークスペースをクリーンアップ（強化版）
            script.echo "ワークスペースをクリーンアップ中..."
            cleanupWorkspace()
            
            // ディレクトリの権限を確保
            script.sh """
                # カレントディレクトリの権限を確保
                chmod 777 . 2>/dev/null || {
                    echo "Warning: Could not change directory permissions"
                    # 親ディレクトリの情報を表示
                    echo "Parent directory info:"
                    ls -la ../ || true
                }
            """
            
            // Gitセキュリティ設定
            setupGitSecurity()
            
            if (authMethod == AuthMethod.DEPLOY_KEY) {
                checkoutWithDirectSSHKey(repoUrl, branch, effectiveConfig.credentialsId)
            } else {
                // PAT認証の場合は通常のチェックアウト
                def checkoutExtensions = getCheckoutExtensions(effectiveConfig)
                executePATCheckout(repoUrl, branch, effectiveConfig.credentialsId, checkoutExtensions)
            }
            
            script.echo "リポジトリ '${repoUrl}' (ブランチ: '${branch}') が正常にチェックアウトされました"
        } catch (Exception e) {
            script.echo "チェックアウトエラー: ${e.message}"
            
            // エラー時の追加診断情報
            script.sh """
                echo "=== Error Diagnostics ==="
                echo "Current directory: \$(pwd)"
                echo "Directory permissions: \$(ls -la . 2>/dev/null || echo 'Cannot list directory')"
                echo "User info: \$(id)"
                echo "Git config:"
                git config --list | grep safe.directory || echo "No safe.directory config"
                echo "======================"
            """ 
            
            throw new GitOperationException("リポジトリ '${repoUrl}' (ブランチ: '${branch}') をチェックアウトできませんでした。エラー: ${e.message}", e)
        }
    }
    
    /**
     * 直接SSHエージェント鍵を使用してリポジトリをクローンする
     */
    private def checkoutWithDirectSSHKey(String repoUrl, String branch, String credentialsId) {
        script.withCredentials([script.sshUserPrivateKey(credentialsId: credentialsId, keyFileVariable: 'SSH_KEY_FILE', passphraseVariable: 'SSH_PASSPHRASE')]) {
            // SSHキーにパスフレーズが設定されている場合の警告 (clone時にも影響する可能性)
            if (script.env.SSH_PASSPHRASE) {
                script.echo "[WARN] SSH key '${credentialsId}' for clone has a passphrase. This script might not handle passphrase-protected keys automatically for GIT_SSH_COMMAND. Operations could fail."
            }
            script.sh """
                # すべてのファイルを削除（隠しファイルも含む）
                rm -rf * .[!.]* ..?* || true
                
                # SSHディレクトリが確実に存在するようにする
                mkdir -p ~/.ssh
                chmod 700 ~/.ssh
                
                # github.com 以外のホストも考慮するなら、リポジトリURLからホスト名を抽出してssh-keyscanに渡す
                ssh-keyscan -t rsa,ecdsa,ed25519 github.com > ~/.ssh/known_hosts
                chmod 600 ~/.ssh/known_hosts
                
                # Gitクローンで明示的に鍵ファイルを指定する
                GIT_SSH_COMMAND="ssh -i \${SSH_KEY_FILE} -o UserKnownHostsFile=~/.ssh/known_hosts -o StrictHostKeyChecking=no" \\
                git clone --depth=1 --branch=${branch} ${repoUrl} .
            """
        }
    }
    
    /**
     * PAT認証でのチェックアウト実行
     */
    private def executePATCheckout(String url, String branch, String credentialsId, def extensions) {
        // まずディレクトリをクリーンアップ
        cleanupWorkspace()
        
        // ワークスペースの権限を確保
        script.sh """
            # 現在のディレクトリに書き込み権限があることを確認
            touch .test-write-permission 2>/dev/null && rm -f .test-write-permission || {
                echo "Warning: No write permission in current directory"
                # 親ディレクトリから権限を修正
                chmod 777 . 2>/dev/null || true
            }
        """
        
        // チェックアウト前にクリーンアップを含む拡張設定を追加
        def enhancedExtensions = extensions + [
            [$class: 'CleanBeforeCheckout', deleteUntrackedNestedRepositories: true],
            [$class: 'CheckoutOption', timeout: 60]
        ]
        
        // より詳細な設定でチェックアウト
        script.checkout([
            $class: 'GitSCM',
            branches: [[name: "*/${branch}"]],
            userRemoteConfigs: [[
                url: url,
                credentialsId: credentialsId,
                refspec: '+refs/heads/*:refs/remotes/origin/*'
            ]],
            extensions: enhancedExtensions,
            doGenerateSubmoduleConfigurations: false,
            browser: null,
            gitTool: 'Default'
        ])
    }
    
    // ==========================================
    // コミット・プッシュ関連メソッド
    // ==========================================
    
    /**
     * 変更を新しいブランチにコミットしてプッシュする
     * URLの形式から認証方式を自動的に判断します
     * @param branchName 作成するブランチ名
     * @param commitMessage コミットメッセージ
     * @param files コミット対象のファイルまたはディレクトリのリスト
     * @param config 追加設定（repoUrlを含む必要があります）
     */
    def commitAndPushChanges(String branchName, String commitMessage, def files, Map config = [:]) {
        def repoUrl = config.repoUrl ?: script.env.REPO_URL
        if (!repoUrl) {
            throw new IllegalArgumentException("リポジトリURLが指定されていません。configにrepoUrlを指定するか、REPO_URL環境変数を設定してください")
        }
        
        // URLからAuthMethodを判断
        AuthMethod authMethod = detectAuthMethod(repoUrl)
        Map updatedConfig = new HashMap(config) // defaultConfig とマージする前の config
        updatedConfig.put('authMethod', authMethod) // authMethod をここで追加
        commitAndPushChangesWithAuth(branchName, commitMessage, files, authMethod, updatedConfig)
    }

    /**
     * 変更を新しいブランチにコミットしてプッシュする（認証情報ID指定）
     * @param branchName 作成するブランチ名
     * @param commitMessage コミットメッセージ
     * @param files コミット対象のファイルまたはディレクトリのリスト
     * @param credentialsId 認証情報ID
     * @param config 追加設定（repoUrlを含む必要があります）
     */    
    def commitAndPushChanges(String branchName, String commitMessage, def files, String credentialsId, Map config = [:]) {
        def repoUrl = config.repoUrl ?: script.env.REPO_URL
        if (!repoUrl) {
            throw new IllegalArgumentException("リポジトリURLが指定されていません。configにrepoUrlを指定するか、REPO_URL環境変数を設定してください")
        }
        
        // URLからAuthMethodを判断
        AuthMethod authMethod = detectAuthMethod(repoUrl)
        Map updatedConfig = new HashMap(config)
        updatedConfig.put('credentialsId', credentialsId)
        updatedConfig.put('authMethod', authMethod) // authMethod をここで追加
        commitAndPushChangesWithAuth(branchName, commitMessage, files, authMethod, updatedConfig)
    }
    
    /**
     * 統合されたコミット＆プッシュメソッド
     * @param branchName 作成するブランチ名
     * @param commitMessage コミットメッセージ
     * @param files コミット対象のファイルまたはディレクトリのリスト
     * @param authMethod 認証方式
     * @param config 追加設定
     * @throws IllegalArgumentException 必須パラメータが不足している場合
     * @throws GitOperationException Git操作に失敗した場合
     */
    private def commitAndPushChangesWithAuth(String branchName, String commitMessage, def files, AuthMethod authMethod, Map configParams = [:]) {
        // effectiveConfig の前に configParams に authMethod を入れておく
        Map tempConfig = new HashMap(configParams)
        if (!tempConfig.containsKey('authMethod')) {
            tempConfig.put('authMethod', authMethod)
        }

        def effectiveConfig = defaultConfig + tempConfig
        validateCommitParams(branchName, commitMessage, files, authMethod, effectiveConfig)
        
        List<Map> normalizedFiles = normalizeFiles(files)
        if (normalizedFiles.isEmpty()) {
            script.echo "ブランチ '${branchName}' にコミットするファイルが指定されていないか、正規化後に空になりました。コミットとプッシュをスキップします"
            return
        }
        
        // Gitユーザー情報を設定
        setupGit([email: effectiveConfig.gitUserEmail ?: effectiveConfig.email, 
                 username: effectiveConfig.gitUserName ?: effectiveConfig.username])
        
        // リポジトリのディレクトリを安全として登録
        setupGitSecurity()
        
        try {
            // 認証方式に応じてコミットとプッシュを実行
            if (authMethod == AuthMethod.PAT) {
                executePATCommitAndPush(branchName, commitMessage, normalizedFiles, effectiveConfig)
            } else { // DEPLOY_KEY
                executeDeployKeyCommitAndPush(branchName, commitMessage, normalizedFiles, effectiveConfig)
            }
        } catch (Exception e) {
            script.echo "コミットとプッシュに失敗しました: ${e.message}"
            throw e
        }
    }
    
    /**
     * PAT認証でのコミットとプッシュを実行
     */
    private def executePATCommitAndPush(String branchName, String commitMessage, List<Map> normalizedFiles, Map config) {
        def repoUrl = config.repoUrl ?: script.env.REPO_URL // このrepoUrlはHTTPS形式のはず
        
        script.withCredentials([script.usernamePassword(
            credentialsId: config.credentialsId,
            usernameVariable: 'GIT_USERNAME',
            passwordVariable: 'GIT_PASSWORD'
        )]) {
            def authUrl = getAuthenticatedUrl(repoUrl, script.env.GIT_USERNAME, script.env.GIT_PASSWORD)
            
          Map operationConfig = new HashMap(config)
          operationConfig.put('authMethod', AuthMethod.PAT)
            executeGitOperationsForCommit(authUrl, branchName, commitMessage, normalizedFiles, operationConfig)
            
            script.sh "git remote set-url origin ${repoUrl}" // 認証情報をリセット
        }
    }
    
    /**
     * Deploy Key認証でのコミットとプッシュを実行
     */
    private def executeDeployKeyCommitAndPush(String branchName, String commitMessage, List<Map> normalizedFiles, Map config) {
        def repoUrlSsh = config.repoUrl // このrepoUrlはSSH形式 (git@...) のはず
        script.echo "ブランチ '${branchName}' にSSH Deploy Key (認証情報: '${config.credentialsId}') を使用してコミットとプッシュを行います"
        
        script.withCredentials([script.sshUserPrivateKey(credentialsId: config.credentialsId, keyFileVariable: 'SSH_KEY_FILE', passphraseVariable: 'SSH_PASSPHRASE')]) {
            setupSshEnvironment() // ~/.ssh ディレクトリと known_hosts を準備

            // SSHキーにパスフレーズが設定されている場合の警告
            if (script.env.SSH_PASSPHRASE) {
                script.echo "[WARN] The SSH key '${config.credentialsId}' has a passphrase. This script does not directly support passphrase-protected keys for GIT_SSH_COMMAND. Operations might fail if the key requires interactive passphrase input. Consider using a key without a passphrase or Jenkins ssh-agent wrapper."
            }
            
            // GIT_SSH_COMMAND を Groovy 内で構築 (script.env.SSH_KEY_FILE で鍵ファイルのパスを取得)
            def sshKeyFilePath = script.env.SSH_KEY_FILE 
            def gitSshCommand = "ssh -i ${sshKeyFilePath} -o UserKnownHostsFile=~/.ssh/known_hosts -o StrictHostKeyChecking=no"
            
            script.withEnv(["GIT_SSH_COMMAND=${gitSshCommand}"]) {
                try {
                  Map operationConfig = new HashMap(config)
                  operationConfig.put('authMethod', AuthMethod.DEPLOY_KEY)
                    executeGitOperationsForCommit(repoUrlSsh, branchName, commitMessage, normalizedFiles, operationConfig)
                } finally {
                    // GIT_SSH_COMMAND は withEnv のスコープを抜ければ元に戻る (unsetは不要)
                }
            }
        }
    }

    /**
     * SSH環境の基本的なセットアップ (known_hosts)
     * このメソッドは withCredentials ブロックの外側、または鍵ファイルが不要な場合に使用できます。
     * 今回は withCredentials の中で SSH_KEY_FILE を使うので、known_hosts の設定だけを行う。
     */
    private def setupSshEnvironment() {
        script.sh """
            set -e
            mkdir -p ~/.ssh
            chmod 700 ~/.ssh
            # github.com 以外のホストも考慮するなら、リポジトリURLからホスト名を動的に取得してssh-keyscanに渡す
            # ここでは github.com にハードコード
            if ! grep -q "github.com" ~/.ssh/known_hosts 2>/dev/null; then
                echo "Adding github.com to known_hosts"
                ssh-keyscan -t rsa,ecdsa,ed25519 github.com >> ~/.ssh/known_hosts
            else
                echo "github.com already in known_hosts"
            fi
            chmod 600 ~/.ssh/known_hosts
        """
    }

    // setupSshWithPrivateKey メソッドは削除 (機能は上記に統合・変更)
    
    /**
    * コミットとプッシュの共通Git操作実行
    */
    private def executeGitOperationsForCommit(String repoUrl, String branchName, String commitMessage, 
                                        List<Map> normalizedFiles, Map config) {
        try {
            def baseBranchEsc = config.baseBranch.replace("'", "'\\''")
            def branchNameEsc = branchName.replace("'", "'\\''")
            def commitMessageEsc = commitMessage.replace("'", "'\\''")
            
            // AuthMethod を config から取得。なければ repoUrl から推測 (フォールバック)
            AuthMethod authMethod = config.authMethod ?: detectAuthMethod(repoUrl)
            // リモートURLの設定
            if (authMethod == AuthMethod.PAT) {
                // PATの場合、渡された repoUrl は認証情報付きURLのはず
                script.echo "Setting remote origin URL for PAT: ${repoUrl.replaceAll('https://[^@]+@', 'https://<REDACTED>@')}"
                script.sh "git remote set-url origin \"${repoUrl}\""
            } else if (authMethod == AuthMethod.DEPLOY_KEY) {
                // SSHの場合、渡された repoUrl は SSH形式のURL (例: git@github.com:user/repo.git)
                // GIT_SSH_COMMAND が認証を処理する
                script.echo "Setting remote origin URL for SSH: ${repoUrl}"
                script.sh "git remote set-url origin \"${repoUrl}\""
            }
            
            stashChangesAndUpdateBaseBranch(baseBranchEsc) // ★ここでgit fetchが実行される
            
            handleBranchCreation(branchNameEsc, baseBranchEsc, config.createNewBranch)
            
            script.sh """
                set -xe pipefail
                echo "退避した変更を復元しています..."
                git stash pop || echo "退避した変更の復元に失敗したか退避が存在しません (続行します)"
            """
            
            addFilesToCommit(normalizedFiles)
            commitChanges(commitMessageEsc)
            
            script.sh """
                set -xe pipefail
                echo "変更をorigin/${branchNameEsc}にプッシュします..."
                git push --set-upstream origin '${branchNameEsc}'
            """
            script.echo "ブランチ '${branchNameEsc}' への変更を正常にコミットしてプッシュしました"
            
        } catch (Exception e) {
            script.echo "Git操作中にエラーが発生しました: ${e.message}"
            throw new GitOperationException("ブランチ '${branchName}' のgit操作中にエラーが発生しました: ${e.message}", e)
        }
    }
    
    /**
     * 変更を退避してベースブランチを更新
     * このメソッドは、呼び出し元のコンテキストでgit fetchが正しく認証されるように、
     * GIT_SSH_COMMAND (SSHの場合) や remote.origin.url (PATの場合) が
     * 適切に設定されていることを前提とします。
     */
    private def stashChangesAndUpdateBaseBranch(String baseBranchEsc) {
        script.sh """
            set -xe pipefail
            # 変更を退避
            echo "ローカルの変更を退避中..."
            git stash push -u || echo "退避する変更がないか退避操作に失敗しました (続行します)"
            
            # ベースブランチを最新に更新
            echo "originからフェッチし、ベースブランチ '${baseBranchEsc}' を最新の状態にします..."
            git fetch origin --prune
            git checkout '${baseBranchEsc}'
            git reset --hard origin/'${baseBranchEsc}'
        """
    }

    /**
     * ブランチの作成またはチェックアウト
     */
    private def handleBranchCreation(String branchNameEsc, String baseBranchEsc, boolean createNewBranch) {
        if (createNewBranch) {
            script.sh """
                set -xe pipefail
                echo "ブランチ '${baseBranchEsc}' から新しいブランチ '${branchNameEsc}' を作成してチェックアウトします..."
                if git rev-parse --verify --quiet '${branchNameEsc}'; then
                    echo "ローカルブランチ '${branchNameEsc}' はすでに存在します。チェックアウトします"
                    git checkout '${branchNameEsc}'
                else
                    git checkout -b '${branchNameEsc}'
                fi
            """
        } else {
            script.sh """
                set -xe pipefail
                echo "既存のブランチ '${branchNameEsc}' をチェックアウトします..."
                if git show-ref --quiet refs/heads/'${branchNameEsc}'; then
                    git checkout '${branchNameEsc}'
                else
                    echo "ローカルブランチ '${branchNameEsc}' が見つかりません。リモートブランチ 'origin/${branchNameEsc}' からチェックアウトを試みます"
                    git checkout -b '${branchNameEsc}' origin/'${branchNameEsc}' 2>/dev/null || {
                        echo "リモートブランチ 'origin/${branchNameEsc}' が見つかりません。'${baseBranchEsc}' をベースに新しいローカルブランチ '${branchNameEsc}' を作成します"
                        git checkout -b '${branchNameEsc}' '${baseBranchEsc}'
                    }
                fi
                echo "ブランチ '${branchNameEsc}' の最新の変更を取得中..."
                git pull origin '${branchNameEsc}' || echo "ブランチ '${branchNameEsc}' のpullに失敗したか適用できませんでした (続行します)"
            """
        }
    }
    
    /**
    * ファイルをコミットに追加
    */
    private def addFilesToCommit(List<Map> normalizedFiles) {
        script.echo "指定されたファイルをコミットに追加します..."
        
        // 各ファイルを個別に追加
        normalizedFiles.each { fileInfo ->
            try {
                // ファイルパスの前後の空白を取り除く
                def filePath = fileInfo.path.trim()
                
                // エスケープ
                def escapedPath = filePath.replace("'", "'\\''").replace("\"", "\\\"")
                
                script.sh "git add \"${escapedPath}\""
            } catch (Exception e) {
                script.echo "警告: ファイル '${fileInfo.path}' の追加に失敗しました: ${e.message}"
                // 続行するためにエラーをスローしない
            }
        }
    }
    
    /**
    * 変更をコミット
    */
    private def commitChanges(String commitMessageEsc) {
        try {
            script.sh """
                set -xe pipefail
                echo "変更をコミットしています..."
                git commit -m '${commitMessageEsc}' || echo "コミットする変更がないか、コミットに失敗しました (続行します)"
            """
        } catch (Exception e) {
            script.echo "警告: 変更のコミットに失敗しました: ${e.message}"
            // 続行するためにエラーをスローしない
        }
    }

    // ==========================================
    // ユーティリティメソッド
    // ==========================================
    
    /**
     * URLから認証方式を検出する
     * @param url リポジトリURL
     * @return 認証方式
     */
    protected AuthMethod detectAuthMethod(String url) {
        if (url.startsWith("git@") || url.startsWith("ssh://")) {
            return AuthMethod.DEPLOY_KEY
        } else {
            return AuthMethod.PAT
        }
    }

    /**
     * リポジトリURLからオーナーとリポジトリ名を抽出する
     * @param repoUrl リポジトリURL
     * @return [リポジトリオーナー, リポジトリ名] の配列
     * @throws GitOperationException 抽出に失敗した場合
     */
    def extractRepoInfo(String repoUrl) {
        def matcher = repoUrl =~ /github\.com[\/:]([^\/]+)\/([^\/\.]+)(\.git)?$/
        if (!matcher.find()) {
            throw new GitOperationException("不正なGitHubリポジトリURL: ${repoUrl}")
        }
        return [matcher.group(1), matcher.group(2)]
    }
    
    /**
     * 現在のリポジトリからオーナーとリポジトリ名を取得する
     * @return [リポジトリオーナー, リポジトリ名] の配列
     * @throws GitOperationException 取得に失敗した場合
     */
    def getCurrentRepoInfo( repoUrl = null) {
        try {
            if (repoUrl) {
                return extractRepoInfo(repoUrl)
            } else {
                repoUrl = script.sh(script: 'git config --get remote.origin.url', returnStdout: true).trim()
                return extractRepoInfo(repoUrl)
            }
        } catch (Exception e) {
            throw new GitOperationException("リポジトリ情報の抽出に失敗しました: ${e.message}", e)
        }
    }
    
    // ==========================================
    // ヘルパーメソッド
    // ==========================================
    
    /**
     * ワークスペースのクリーンアップ
     */
    private def cleanupWorkspace() {
        script.sh '''
            # 現在のディレクトリの情報を出力（デバッグ用）
            echo "Current directory: $(pwd)"
            echo "Current user: $(whoami) (UID: $(id -u), GID: $(id -g))"
            
            # .gitディレクトリを含むすべてのファイルを強制削除
            # 権限エラーを回避するため、まず権限を変更してから削除
            if [ -d .git ]; then
                chmod -R 777 .git 2>/dev/null || true
            fi
            
            # すべてのファイルを削除（隠しファイルも含む）
            rm -rf * .[!.]* ..?* 2>/dev/null || true
            
            # 削除できなかったファイルがある場合は、権限を変更して再試行
            if [ "$(ls -A 2>/dev/null)" ]; then
                echo "Some files remain, attempting forced cleanup..."
                find . -type d -exec chmod 777 {} + 2>/dev/null || true
                find . -type f -exec chmod 666 {} + 2>/dev/null || true
                rm -rf * .[!.]* ..?* 2>/dev/null || true
            fi
        '''
    }
    
    /**
     * リポジトリチェックアウト情報のログ出力
     */
    private def logCheckoutInfo(String repoUrl, String branch, AuthMethod authMethod, Map config) {
        def authTypeMsg = (authMethod == AuthMethod.PAT) ? 
            "PAT認証（認証情報: '${config.credentialsId}'）" : 
            "SSH Deploy Key認証（認証情報: '${config.credentialsId}'）"
        
        script.echo "リポジトリ ${repoUrl.replaceAll('https://[^@]+@', 'https://<REDACTED>@')} のブランチ '${branch}' を${authTypeMsg}を使用してチェックアウトします"
    }
    
    /**
     * Gitのセキュリティ設定（ディレクトリの安全設定）
     */
    private def setupGitSecurity() {
        script.sh """
            # Git 2.35.2以降の所有権チェックに対応
            git config --global --unset-all safe.directory 2>/dev/null || true
            git config --global --add safe.directory '*'
            
            # 作業ディレクトリも明示的に追加
            git config --global --add safe.directory \$(pwd)
            git config --global --add safe.directory ${script.env.WORKSPACE ?: '/workspace'}
            
            # 現在のGitバージョンを確認
            echo "Git version: \$(git --version)"
        """
    }
    
    /**
     * リポジトリパラメータのバリデーション
     */
    private void validateRepositoryParams(String repoUrl, String branch, AuthMethod authMethod, Map config) {
        if (!repoUrl?.trim()) {
            throw new IllegalArgumentException("リポジトリURLは必須です")
        }
        if (!branch?.trim()) {
            throw new IllegalArgumentException("ブランチ名は必須です")
        }
        
        if (authMethod == AuthMethod.PAT) {
            if (!config.credentialsId?.trim()) {
                throw new IllegalArgumentException("PAT認証では認証情報ID (credentialsId) は必須です")
            }
        } else {
            if (!repoUrl.startsWith("git@") && !repoUrl.startsWith("ssh://")) {
                throw new IllegalArgumentException("SSH形式のリポジトリURL (repoUrl) は 'git@' または 'ssh://' で始まる必要があります。指定値: '${repoUrl}'")
            }
            if (!config.credentialsId?.trim()) {
                throw new IllegalArgumentException("SSH認証では認証情報ID (credentialsId) は必須です")
            }
        }
    }
    
    /**
     * コミットパラメータのバリデーション
     */
    private void validateCommitParams(String branchName, String commitMessage, def files, AuthMethod authMethod, Map config) {
        if (!branchName?.trim()) {
            throw new IllegalArgumentException("ブランチ名は必須です")
        }
        if (!commitMessage?.trim()) {
            throw new IllegalArgumentException("コミットメッセージは必須です")
        }
        if (files == null) {
            throw new IllegalArgumentException("コミット対象ファイルは必須です")
        }
        
        if (authMethod == AuthMethod.PAT) {
            if (!config.credentialsId?.trim() && !defaultConfig.credentialsId?.trim()) {
                throw new IllegalArgumentException("PAT認証では認証情報ID (credentialsId) は必須です")
            }
            if (!config.repoUrl && !script.env.REPO_URL) {
                throw new IllegalArgumentException("リポジトリURLが指定されていません")
            }
        } else {
            if (!config.repoUrl?.trim()) {
                throw new IllegalArgumentException("SSH形式のリポジトリURL (repoUrl) は必須です")
            }
            if (!config.repoUrl.startsWith("git@") && !config.repoUrl.startsWith("ssh://")) {
                throw new IllegalArgumentException("SSH形式のリポジトリURL (repoUrl) は 'git@' または 'ssh://' で始まる必要があります。指定値: '${config.repoUrl}'")
            }
            if (!config.credentialsId?.trim()) {
                throw new IllegalArgumentException("SSH認証では認証情報ID (credentialsId) は必須です")
            }
        }
    }
    
    /**
     * ファイルパラメータを正規化する
     * @return List<Map> 正規化されたファイルリスト
     */
    protected List<Map> normalizeFiles(def files) {
        def normalized = []
        
        if (files instanceof String) {
            // 単一ファイル
            normalized << [path: files, status: 'add']
        } else if (files instanceof List) {
            // ファイルパスのリスト
            files.each { file ->
                if (file instanceof String) {
                    normalized << [path: file, status: 'add']
                } else if (file instanceof Map && file.path) {
                    normalized << [path: file.path, status: (file.status?.toLowerCase() == 'remove' ? 'remove' : 'add')]
                } else {
                    throw new IllegalArgumentException("不正なファイル指定: ${file}")
                }
            }
        } else if (files instanceof Map) {
            // ファイルパスとステータスのマップ
            files.each { path, status ->
                normalized << [path: path, status: status ?: 'add']
            }
        } else {
            throw new IllegalArgumentException("不正なファイルパラメータ型: ${files.class}")
        }
        
        return normalized
    }
    
    /**
     * 認証情報付きのURLを生成する
     */
    private String getAuthenticatedUrl(String repoUrl, String username, String password) {
        def url = repoUrl.replaceFirst("https://", "")
        return "https://${username}:${password}@${url}"
    }
    
    /**
     * チェックアウト拡張設定を取得する
     */
    private List getCheckoutExtensions(Map config) {
        def extensions = []
        
        // 常にクリーンアップを含める
        extensions.add([$class: 'CleanBeforeCheckout', deleteUntrackedNestedRepositories: true])
        
        if (config.wipeWorkspace) {
            extensions.add([$class: 'WipeWorkspace'])
        }
        
        if (config.shallowClone) {
            extensions.add([$class: 'CloneOption', noTags: true, shallow: true, depth: config.cloneDepth, timeout: config.checkoutTimeout])
        } else {
            extensions.add([$class: 'CloneOption', noTags: true, shallow: false, timeout: config.checkoutTimeout])
        }
        
        // タイムアウト設定を追加
        extensions.add([$class: 'CheckoutOption', timeout: config.checkoutTimeout])
        
        return extensions
    }
}
