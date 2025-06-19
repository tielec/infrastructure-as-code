#!/usr/bin/env groovy
/**
 * Jenkinsのセキュリティ設定を行うスクリプト
 * Markdown Formatterの設定などを含む
 */
import jenkins.model.*
import hudson.security.csrf.DefaultCrumbIssuer
import hudson.markup.RawHtmlMarkupFormatter
import hudson.markup.MarkupFormatter

def instance = Jenkins.getInstance()

println("=== Configuring Jenkins Security Settings ===")

// Markup Formatter設定
def MARKUP_FORMATTER = System.getenv("JENKINS_MARKUP_FORMATTER") ?: "markdown"

println("Setting up Markup Formatter: ${MARKUP_FORMATTER}")

try {
    // Markdown Formatterプラグインがインストールされているか確認
    def markdownFormatterClass = null
    try {
        markdownFormatterClass = Class.forName("io.jenkins.plugins.markdown.MarkdownFormatter")
    } catch (ClassNotFoundException e) {
        println("WARNING: Markdown Formatter plugin not found")
    }
    
    if (MARKUP_FORMATTER.toLowerCase() == "markdown" && markdownFormatterClass != null) {
        // Markdown Formatterを設定
        def markdownFormatter = markdownFormatterClass.newInstance()
        instance.setMarkupFormatter(markdownFormatter)
        println("✓ Markdown Formatter configured")
    } else if (MARKUP_FORMATTER.toLowerCase() == "html") {
        // Raw HTML Formatter（セキュリティリスクあり）
        instance.setMarkupFormatter(new RawHtmlMarkupFormatter(false))
        println("✓ Raw HTML Formatter configured (Security Warning: This allows HTML content)")
    } else {
        // Plain Text Formatter（デフォルト）
        instance.setMarkupFormatter(hudson.markup.PlainTextMarkupFormatter.INSTANCE)
        println("✓ Plain Text Formatter configured (default)")
    }
} catch (Exception e) {
    println("ERROR: Failed to configure Markup Formatter: ${e.message}")
    e.printStackTrace()
}

// CSRF Protection設定の確認と強化
println("\nConfiguring CSRF Protection...")
def crumbIssuer = instance.getCrumbIssuer()
if (crumbIssuer == null) {
    println("CSRF Protection is not enabled. Enabling it now...")
    instance.setCrumbIssuer(new DefaultCrumbIssuer(true))
    println("✓ CSRF Protection enabled")
} else {
    println("✓ CSRF Protection is already enabled")
}

// エージェントプロトコルの設定
println("\nConfiguring Agent Protocols...")
def currentProtocols = instance.getAgentProtocols()
println("Current protocols: ${currentProtocols}")

// 推奨されるプロトコルのみを有効化
def recommendedProtocols = ['JNLP4-connect'] as Set
if (currentProtocols != recommendedProtocols) {
    instance.setAgentProtocols(recommendedProtocols)
    println("✓ Agent protocols updated to: ${recommendedProtocols}")
} else {
    println("✓ Agent protocols are already properly configured")
}

// セキュリティ関連の追加設定
println("\nApplying additional security settings...")

// マスターノードでのビルド実行を無効化（既に設定済みの可能性あり）
if (instance.getNumExecutors() > 0) {
    instance.setNumExecutors(0)
    println("✓ Disabled builds on master node")
} else {
    println("✓ Builds on master node already disabled")
}

// 環境変数によるセキュリティ設定のカスタマイズ
if (System.getenv("JENKINS_ENABLE_SCRIPT_SECURITY") == "true") {
    println("\nEnabling Script Security...")
    // スクリプトセキュリティの設定（プラグインが必要）
    try {
        def scriptApproval = org.jenkinsci.plugins.scriptsecurity.scripts.ScriptApproval.get()
        if (scriptApproval != null) {
            println("✓ Script Security is available")
        }
    } catch (Exception e) {
        println("✗ Script Security plugin not available")
    }
}

// 設定を保存
instance.save()

// 設定サマリーの表示
println("\n=== Security Configuration Summary ===")
println("Markup Formatter: ${instance.getMarkupFormatter().getClass().getSimpleName()}")
println("CSRF Protection: ${instance.getCrumbIssuer() != null ? 'Enabled' : 'Disabled'}")
println("Agent Protocols: ${instance.getAgentProtocols()}")
println("Master Executors: ${instance.getNumExecutors()}")

println("\n=== Security Configuration Completed ===")
