#!/usr/bin/env groovy
/**
 * Jenkinsプラグインをインストールするためのスクリプト
 * init.groovy.dディレクトリに配置することで、Jenkins起動時に実行される
 * インストール済みプラグインの更新も行います
 */
import jenkins.model.*
import hudson.model.*
import jenkins.install.*
import hudson.util.*
import hudson.PluginWrapper
import hudson.model.UpdateSite
import jenkins.security.s2m.*

def instance = Jenkins.getInstance()
def pm = instance.getPluginManager()
def uc = instance.getUpdateCenter()

// 更新サイトを更新
println("Updating update center...")
uc.updateAllSites()

// インストールするプラグインのリスト
def plugins = [
    // 基本的なUI/UXプラグイン
    "cloudbees-folder",
    "antisamy-markup-formatter",
    "dark-theme",
    "ansicolor",
    
    // ビルド管理プラグイン
    "build-name-setter",
    "build-timeout",
    "build-user-vars-plugin",
    "generic-webhook-trigger",
    "parameterized-trigger",
    "throttle-concurrents",
    "timestamper",
    "ws-cleanup",
    "rebuild",
    "schedule-build",
    
    // 認証と権限管理プラグイン
    "credentials-binding",
    "matrix-auth",
    "role-strategy",
    "mask-passwords",

    // 設定管理プラグイン
    "configuration-as-code",
    "jobConfigHistory",
    
    // クラウドと仮想化プラグイン
    "ec2",
    "ec2-fleet",
    "docker-plugin",
    
    // パイプラインとワークフロープラグイン
    "workflow-aggregator",
    "pipeline-build-step", 
    "pipeline-model-definition",
    "pipeline-github-lib",
    "pipeline-graph-analysis",
    "pipeline-graph-view",
    "pipeline-stage-view",
    "pipeline-utility-steps",
    "ssh-steps",
    "docker-workflow",
    
    // ソース管理とGitプラグイン
    "git",
    "git-parameter",
    "github-branch-source",
    "github-oauth",
    
    // ジョブ管理プラグイン
    "job-dsl",
    
    // 通知プラグイン
    "email-ext",
    "mailer",
    "Office-365-Connector",
    
    // その他のユーティリティプラグイン
    "copyartifact",
    "envinject",
    "htmlpublisher",
    "http_request",
    "ssh-agent",
    "markdown-formatter"
]

// アップデートセンターの初期化を待機
int attempts = 0
int maxAttempts = 10  // 試行回数を増やす
boolean updateCenterInitialized = false

// 初回起動時の場合、Update Centerの初期化に時間がかかる
println("Waiting for Update Center to initialize...")
Thread.sleep(10000) // 初期待機時間を設ける

while (!updateCenterInitialized && attempts < maxAttempts) {
    try {
        println("Checking update center... (attempt ${attempts + 1}/${maxAttempts})")
        
        // Update Centerを更新
        uc.updateAllSites()
        
        // 少し待機してからチェック
        Thread.sleep(5000)
        
        def updateCenter = uc.getById("default")
        def available = updateCenter.getAvailables()
        
        // プラグインの利用可能リストを取得できるかチェック
        if (updateCenter.getUpdates().size() > 0 || available.size() > 0) {
            updateCenterInitialized = true
            println("Update center initialized successfully. Available plugins: ${available.size()}")
        } else {
            // まだ初期化されていない場合は、updateSiteのURLから直接チェック
            def site = updateCenter.getSite()
            if (site != null && site.getDataTimestamp() > 0) {
                updateCenterInitialized = true
                println("Update center initialized (data timestamp: ${new Date(site.getDataTimestamp())})")
            } else {
                println("Update center not initialized yet. Waiting...")
                Thread.sleep(10000) // 10秒待機
            }
        }
    } catch (Exception e) {
        println("Error checking update center: ${e.message}")
        Thread.sleep(5000)
    }
    attempts++
}

if (!updateCenterInitialized) {
    println("Warning: Update center could not be fully initialized after ${maxAttempts} attempts.")
    println("Attempting to proceed anyway...")
}

// プラグインをインストールまたは更新する関数
def installOrUpdatePlugin = { pluginId ->
    def plugin = pm.getPlugin(pluginId)
    
    if (!plugin) {
        // プラグインがインストールされていない場合、新規インストール
        println("Installing plugin: ${pluginId}")
        try {
            def pluginToInstall = uc.getPlugin(pluginId)
            if (pluginToInstall == null) {
                println("Plugin ${pluginId} not found in update center. Skipping...")
                return false
            }
            
            // 依存関係も含めてインストール
            def installFuture = pluginToInstall.deploy(true)  // true = dynamicLoad
            
            // インストール完了を待つ
            int waitCount = 0
            while(!installFuture.isDone() && waitCount < 60) {  // 最大30秒待機
                Thread.sleep(500)
                waitCount++
            }
            
            if (installFuture.isDone()) {
                println("Successfully installed plugin: ${pluginId}")
                return true
            } else {
                println("Plugin ${pluginId} installation timed out")
                return false
            }
        } catch (Exception e) {
            println("Failed to install plugin ${pluginId}: ${e.message}")
            return false
        }
    } else {
        // プラグインが既にインストールされている場合、更新が必要かチェック
        def updateSite = uc.getById("default")
        def available = updateSite.getAvailables()
        def updateInfo = available.find { it.name == pluginId }
        
        if (updateInfo) {
            def currentVersion = plugin.getVersionNumber()
            def availableVersion = updateInfo.version
            
            if (availableVersion > currentVersion) {
                println("Updating plugin ${pluginId} from ${currentVersion} to ${availableVersion}")
                try {
                    def installFuture = updateInfo.deploy()
                    while(!installFuture.isDone()) {
                        Thread.sleep(500)
                    }
                    println("Successfully updated plugin: ${pluginId}")
                    return true
                } catch (Exception e) {
                    println("Failed to update plugin ${pluginId}: ${e.message}")
                    return false
                }
            } else {
                println("Plugin ${pluginId} is already up to date (${currentVersion})")
                return false
            }
        } else {
            println("Plugin ${pluginId} is installed but no update information is available")
            return false
        }
    }
}

// すべてのプラグインをインストールまたは更新
println("Starting plugin installation/update process")
boolean restartRequired = false

plugins.each { plugin ->
    try {
        boolean modified = installOrUpdatePlugin(plugin)
        restartRequired = restartRequired || modified
    } catch (Exception e) {
        println("Error processing plugin ${plugin}: ${e.message}")
        e.printStackTrace()
    }
}

// 保存して反映
println("Saving Jenkins configuration")
instance.save()

// 再起動が必要かどうかを出力
if (restartRequired) {
    println("Some plugins were installed or updated. A restart of Jenkins is required.")
    
    // 自動再起動を有効にする場合はここにコードを追加
    // 注意: 実運用環境では計画的な再起動が望ましい
    // instance.restart()
} else {
    println("No plugins were installed or updated. No restart required.")
}

println("Plugin installation/update process completed")
