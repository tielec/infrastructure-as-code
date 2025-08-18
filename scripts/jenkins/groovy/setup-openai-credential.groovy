#!/usr/bin/env groovy
/**
 * Jenkins OpenAI APIキークレデンシャルを作成するスクリプト
 * init.groovy.dディレクトリに配置して、Jenkins起動時に実行される
 */
import jenkins.model.*
import com.cloudbees.plugins.credentials.*
import com.cloudbees.plugins.credentials.impl.*
import com.cloudbees.plugins.credentials.domains.*
import org.jenkinsci.plugins.plaincredentials.impl.*
import hudson.util.Secret

def jenkins = Jenkins.getInstance()

// APIキーはスクリプト実行時にプレースホルダーから置換される
def openaiApiKey = "##OPENAI_API_KEY_PLACEHOLDER##"

println("=== Starting OpenAI API Key Credential Setup ===")

// プレースホルダーのチェック
if (openaiApiKey == null || openaiApiKey.isEmpty() || openaiApiKey == "##OPENAI_API_KEY_PLACEHOLDER##") {
    println("WARNING: OpenAI API key not provided or placeholder not replaced. Skipping credential creation.")
    return
}

// クレデンシャルストアの取得
def domain = Domain.global()
def store = SystemCredentialsProvider.getInstance().getStore()

// 既存のクレデンシャルを確認
def credentialId = "openai-api-key"
def existingCredentials = store.getCredentials(domain)
def existingCredential = existingCredentials.find { it.id == credentialId }

if (existingCredential) {
    println("Updating existing OpenAI API key credential: ${credentialId}")
    store.removeCredentials(domain, existingCredential)
} else {
    println("Creating new OpenAI API key credential: ${credentialId}")
}

// 新しいSecretTextクレデンシャルを作成
def newCredential = new StringCredentialsImpl(
    CredentialsScope.GLOBAL,
    credentialId,
    "OpenAI API Key",
    Secret.fromString(openaiApiKey)
)

// クレデンシャルを追加
store.addCredentials(domain, newCredential)

println("✓ OpenAI API key credential '${credentialId}' has been successfully configured")

// 保存
jenkins.save()

println("=== OpenAI API Key Credential Setup Completed ===")