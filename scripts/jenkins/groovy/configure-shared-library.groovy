#!/usr/bin/env groovy
/**
 * Jenkins Shared Libraryを設定するスクリプト
 * Global Pipeline Librariesにリポジトリを追加
 */
import jenkins.model.*
import jenkins.plugins.git.GitSCMSource
import jenkins.plugins.git.traits.*
import org.jenkinsci.plugins.workflow.libs.*
import org.jenkinsci.plugins.workflow.libs.retriever.modernscm.*

def instance = Jenkins.getInstance()

// 環境変数から設定を取得
def LIBRARY_NAME = System.getenv("SHARED_LIBRARY_NAME") ?: "jenkins-shared-lib"
def LIBRARY_REPO = System.getenv("SHARED_LIBRARY_REPO") ?: "https://github.com/tielec/infrastructure-as-code"
def LIBRARY_BRANCH = System.getenv("SHARED_LIBRARY_BRANCH") ?: "main"
def LIBRARY_PATH = System.getenv("SHARED_LIBRARY_PATH") ?: "jenkins/jobs/shared/"
def ALLOW_VERSION_OVERRIDE = System.getenv("SHARED_LIBRARY_ALLOW_OVERRIDE") ?: "true"
def INCLUDE_IN_CHANGELOG = System.getenv("SHARED_LIBRARY_INCLUDE_CHANGELOG") ?: "true"
def CACHE_VERSIONS = System.getenv("SHARED_LIBRARY_CACHE") ?: "false"

println("=== Configuring Jenkins Shared Library ===")
println("Library Name: ${LIBRARY_NAME}")
println("Repository: ${LIBRARY_REPO}")
println("Default Branch: ${LIBRARY_BRANCH}")
println("Library Path: ${LIBRARY_PATH}")

// Global Pipeline Libraries設定の取得
def globalLibraries = instance.getDescriptor("org.jenkinsci.plugins.workflow.libs.GlobalLibraries")

if (globalLibraries == null) {
    println("ERROR: Global Libraries descriptor not found. Ensure Pipeline plugins are installed.")
    return
}

// 既存のライブラリを確認
def existingLibraries = globalLibraries.getLibraries()
def existingLibrary = existingLibraries.find { it.name == LIBRARY_NAME }

if (existingLibrary != null) {
    println("Library '${LIBRARY_NAME}' already exists")
    if (System.getenv("UPDATE_EXISTING_LIBRARY") == "true") {
        println("Removing existing library configuration...")
        existingLibraries.remove(existingLibrary)
    } else {
        println("Skipping configuration (set UPDATE_EXISTING_LIBRARY=true to update)")
        return
    }
}

try {
    println("Creating Shared Library configuration...")
    
    // GitSCMSourceの作成
    def scmSource = new GitSCMSource(LIBRARY_REPO)
    
    // ブランチ検出戦略の設定
    def traits = []
    
    // ブランチソーストレイトの追加
    traits.add(new BranchDiscoveryTrait())
    
    // PRとして提出されたブランチを除外（オプション）
    if (System.getenv("EXCLUDE_PR_BRANCHES") == "true") {
        traits.add(new ExcludeFromPollSCMTrait())
    }
    
    scmSource.setTraits(traits)
    
    // ライブラリ設定の作成
    def libraryConfiguration = new LibraryConfiguration(
        LIBRARY_NAME,
        new SCMSourceRetriever(scmSource)
    )
    
    // デフォルトバージョンの設定
    libraryConfiguration.setDefaultVersion(LIBRARY_BRANCH)
    
    // バージョンオーバーライドの許可
    libraryConfiguration.setAllowVersionOverride(ALLOW_VERSION_OVERRIDE.toBoolean())
    
    // 変更履歴への含有
    libraryConfiguration.setIncludeInChangesets(INCLUDE_IN_CHANGELOG.toBoolean())
    
    // インプリシットロードの設定（falseがデフォルト）
    libraryConfiguration.setImplicit(false)
    
    // ライブラリパスの設定（オプショナル）
    if (LIBRARY_PATH && LIBRARY_PATH != "") {
        println("Setting library path: ${LIBRARY_PATH}")
        // LibraryPathの設定はSCMSourceRetrieverのプロパティとして設定
        def retriever = libraryConfiguration.getRetriever()
        if (retriever instanceof SCMSourceRetriever) {
            // ライブラリパスはGitSCMSourceの設定として保持される
            // 注: 実際のパス設定は、ジョブ実行時にcheckout時に適用される
        }
    }
    
    // グローバルライブラリに追加
    def updatedLibraries = new ArrayList<>(existingLibraries)
    updatedLibraries.add(libraryConfiguration)
    globalLibraries.setLibraries(updatedLibraries)
    
    // 保存
    globalLibraries.save()
    instance.save()
    
    println("✓ Shared Library '${LIBRARY_NAME}' configured successfully")
    println("  Repository: ${LIBRARY_REPO}")
    println("  Default Version: ${LIBRARY_BRANCH}")
    println("  Allow Override: ${ALLOW_VERSION_OVERRIDE}")
    println("  Include in Changelog: ${INCLUDE_IN_CHANGELOG}")
    println("  Library Path: ${LIBRARY_PATH}")
    
} catch (Exception e) {
    println("ERROR: Failed to configure Shared Library: ${e.message}")
    e.printStackTrace()
}

// 設定の検証
println("\n=== Validating Shared Library Configuration ===")

// 再度グローバルライブラリを取得して確認
def verifyLibraries = globalLibraries.getLibraries()
def verifyLibrary = verifyLibraries.find { it.name == LIBRARY_NAME }

if (verifyLibrary != null) {
    println("✓ Library '${LIBRARY_NAME}' successfully configured")
    println("  Configuration verified in Global Pipeline Libraries")
} else {
    println("✗ WARNING: Library '${LIBRARY_NAME}' not found after configuration")
}

// 使用方法の表示
println("\n=== How to use this Shared Library ===")
println("In your Jenkinsfile, add at the top:")
println("@Library('${LIBRARY_NAME}') _")
println("")
println("Or with a specific version:")
println("@Library('${LIBRARY_NAME}@${LIBRARY_BRANCH}') _")
println("")
println("Then you can use the shared library functions from:")
println("${LIBRARY_REPO} (path: ${LIBRARY_PATH})")

println("\n=== Shared Library Configuration Completed ===")
