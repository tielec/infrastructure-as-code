// YAMLから渡されたjenkinsManagedRepositoriesを使用してリポジトリ情報を構築
def repositories = jenkinsManagedRepositories.collect { name, repo ->
    [
        name: name,
        url: repo.httpsUrl,
        branch: repo.mainBranch,
        credentialsId: repo.credentialsId
    ]
}

// 共通設定を定義するメソッド
def createRustCodeAnalysisJob(repoConfig) {
    // 共通設定を取得
    def jenkinsPipelineRepo = commonSettings['jenkins-pipeline-repo']
    
    // ジョブ設定を取得（このDSLファイル自体の設定）
    def jobKey = 'code_quality_rust_code_analysis_check_job'
    def jobConfig = jenkinsJobsConfig[jobKey]
    
    // ジョブ名を新しい構造に合わせて調整
    def jobName = "Code_Quality_Checker/${repoConfig.name}/${jobConfig.name}"
    
    pipelineJob(jobName) {
        displayName(jobConfig.displayName)
        description("""\
            |# 概要
            |Rust Code Analysisツールを使用してコードメトリクスを分析するジョブ
            |リポジトリ: ${repoConfig.name}
            |
            |## 処理内容
            |1. リポジトリからソースコードを取得
            |2. rust-code-analysis-cliを使用してメトリクスを分析
            |3. 循環的複雑度（Cyclomatic Complexity）の計算
            |4. 認知的複雑度（Cognitive Complexity）の計算
            |5. 行数の計算
            |6. HTMLレポートの生成
            |
            |## 対応言語
            |- Rust, Python, JavaScript, TypeScript, C/C++, Java, Go
            |- PHP, Ruby, C#, Kotlin, Swift, Scala
            |
            |## メトリクス
            |- **Cyclomatic Complexity**: コードの分岐の数に基づく複雑度
            |- **Cognitive Complexity**: 人間にとっての理解しやすさを表す複雑度
            |- **Line Count**: コードの行数
            |""".stripMargin())

        // 依存関係の保持設定
        keepDependencies(false)

        // ログローテーション設定
        logRotator {
            numToKeep(30)
            artifactNumToKeep(30)
        }

        // 同時実行の無効化
        throttleConcurrentBuilds {
            maxTotal(1)
            throttleDisabled(false)
        }

        // プロパティ設定
        properties {
            rebuild {
                autoRebuild(false)
                rebuildDisabled(false)
            }
        }

        // パラメータ設定
        parameters {
            // AGENT_LABELパラメータ
            choiceParam('AGENT_LABEL', ['ec2-fleet-small', 'ec2-fleet-medium', 'ec2-fleet-micro'],
                'Jenkins エージェントのラベル（small: 2並列/2GB, medium: 3並列/4GB, micro: 1並列/1GB）')

            // リポジトリ情報（読み取り専用として表示）
            stringParam('GIT_SOURCE_REPO_URL', repoConfig.url, 'ソースコードリポジトリURL')
            stringParam('GIT_SOURCE_REPO_BRANCH', repoConfig.branch, '分析対象ブランチ')
            stringParam('GIT_SOURCE_REPO_CREDENTIALS_ID', repoConfig.credentialsId, 'Git認証情報ID')
            
            // 複雑度の閾値設定
            stringParam('COMPLEXITY_THRESHOLD', '15', 
                       '循環的複雑度の閾値（これを超えると警告）')
            stringParam('COGNITIVE_THRESHOLD', '20', 
                       '認知的複雑度の閾値（これを超えると警告）')
            stringParam('MIN_CODE_LENGTH', '100', 
                       '分析対象とする最小コード行数')
            
            // 除外パターン
            stringParam('EXCLUDE_PATTERNS', 
                       '*/test/*,*/tests/*,*/node_modules/*,*/target/*,*/vendor/*,*/.git/*', 
                       'カンマ区切りの除外パターン（テストファイルやビルド成果物を除外）')
            
            // メトリクスオプション(将来の拡張性を考慮)
            booleanParam('INCLUDE_HALSTEAD', true, 
                        'Halsteadメトリクス（語彙の多様性、プログラムの長さなど）を分析に含めるか')
            booleanParam('INCLUDE_MI', true, 
                        '保守性指標（Maintainability Index）を分析に含めるか')
            
            // Rustバージョン選択
            choiceParam('RUST_VERSION', ['1.76', '1.77', '1.78', 'latest'], 
                       'Rustのバージョン（最小要件: 1.76）')
            
            // Jenkinsfileブランチ
            stringParam('JENKINSFILE_BRANCH', 'main', 'Jenkinsfileが格納されているブランチ')
        }

        // パイプライン定義
        definition {
            cpsScm {
                scm {
                    git {
                        remote {
                            url(jenkinsPipelineRepo.url)
                            credentials(jenkinsPipelineRepo.credentials)
                        }
                        branch('${JENKINSFILE_BRANCH}')
                    }
                }
                scriptPath(jobConfig.jenkinsfile)
                lightweight(true)
            }
        }

        // ジョブの無効化状態
        disabled(false)
    }
}

// 各リポジトリのジョブを作成
repositories.each { repo ->
    createRustCodeAnalysisJob(repo)
}
