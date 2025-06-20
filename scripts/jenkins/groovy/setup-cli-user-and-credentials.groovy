#!/usr/bin/env groovy
/**
 * Jenkins CLIユーザーを作成し、APIトークンをJenkinsクレデンシャルストアに保存するスクリプト
 * init.groovy.dディレクトリに配置して、Jenkins起動時に実行される
 */
import jenkins.model.*
import hudson.model.*
import hudson.security.*
import jenkins.security.*
import jenkins.security.apitoken.*
import com.cloudbees.plugins.credentials.*
import com.cloudbees.plugins.credentials.domains.*
import com.cloudbees.plugins.credentials.impl.*
import hudson.util.Secret

def instance = Jenkins.getInstance()
def hudsonRealm = instance.getSecurityRealm()

// CLIユーザーの設定
def CLI_USERNAME = "cli-user"
def CLI_FULLNAME = "Jenkins CLI User"
def CLI_EMAIL = "cli-user@jenkins.local"
def CREDENTIAL_ID = "cli-user-token"
def CREDENTIAL_DESCRIPTION = "API token for Jenkins CLI user"

println("=== Starting CLI User Setup ===")

// HudsonPrivateSecurityRealmでない場合はスキップ
if (!(hudsonRealm instanceof HudsonPrivateSecurityRealm)) {
    println("Security realm is not HudsonPrivateSecurityRealm. Skipping CLI user creation.")
    return
}

// ユーザーが既に存在するかチェック
def existingUser = hudsonRealm.getUser(CLI_USERNAME)
def cliUser = null
def needsNewToken = false

if (existingUser != null) {
    println("CLI user '${CLI_USERNAME}' already exists.")
    cliUser = User.get(CLI_USERNAME, false, null)
} else {
    println("Creating new CLI user: ${CLI_USERNAME}")
    
    // ランダムパスワードを生成（直接ログインは想定しない）
    def password = UUID.randomUUID().toString()
    
    // ユーザーを作成
    def user = hudsonRealm.createAccount(CLI_USERNAME, password)
    user.setFullName(CLI_FULLNAME)
    
    // メールアドレスを設定
    def mailProperty = new hudson.tasks.Mailer.UserProperty(CLI_EMAIL)
    user.addProperty(mailProperty)
    
    user.save()
    println("CLI user created successfully")
    
    cliUser = User.get(CLI_USERNAME, false, null)
    needsNewToken = true
}

if (cliUser == null) {
    println("ERROR: Failed to get CLI user")
    return
}

// Admin権限を付与
println("Granting admin permissions to CLI user")
def authStrategy = instance.getAuthorizationStrategy()

if (authStrategy instanceof GlobalMatrixAuthorizationStrategy) {
    // すべての権限を付与
    authStrategy.add(Jenkins.ADMINISTER, CLI_USERNAME)
    instance.save()
    println("Admin permissions granted to CLI user")
} else if (authStrategy instanceof FullControlOnceLoggedInAuthorizationStrategy) {
    println("Authorization strategy is FullControlOnceLoggedIn. CLI user will have full control when logged in.")
} else {
    println("WARNING: Unknown authorization strategy. Could not grant specific permissions.")
}

// クレデンシャルストアをチェック
def credentialsStore = SystemCredentialsProvider.getInstance().getStore()
def globalDomain = Domain.global()
def existingCredentials = credentialsStore.getCredentials(globalDomain)

// 既存のクレデンシャルをチェック
def existingCredential = existingCredentials.find { it.id == CREDENTIAL_ID }

if (existingCredential != null) {
    println("Credential '${CREDENTIAL_ID}' already exists in Jenkins credentials store.")
    // 既存のクレデンシャルを削除して再作成するオプション
    println("Removing existing credential to recreate with new token...")
    credentialsStore.removeCredentials(globalDomain, existingCredential)
}

println("Creating API token and storing in Jenkins credentials...")

// APIトークンの生成
def tokenProperty = cliUser.getProperty(ApiTokenProperty.class)
if (tokenProperty == null) {
    // APIトークンプロパティを追加
    tokenProperty = new ApiTokenProperty()
    cliUser.addProperty(tokenProperty)
    cliUser.save()
}

try {
    // 既存のトークンをすべてクリア
    tokenProperty.tokenStore.getTokenListSortedByName().each { token ->
        tokenProperty.tokenStore.revokeToken(token.getUuid())
    }
    
    // 新しいトークンを生成
    def tokenName = "cli-automation-token-" + System.currentTimeMillis()
    def tokenResult = tokenProperty.tokenStore.generateNewToken(tokenName)
    def apiToken = tokenResult.plainValue
    
    // トークンが正しく生成されたか確認
    if (apiToken == null || apiToken.isEmpty()) {
        throw new Exception("Generated token is null or empty")
    }
    
    println("API token generated successfully")
    println("  Token name: ${tokenName}")
    println("  Token length: ${apiToken.length()}")
    println("  Token UUID: ${tokenResult.tokenUuid}")
    
    // ユーザーを保存してトークンを永続化
    cliUser.save()
    
    // Jenkinsのクレデンシャルストアに保存
    def credentials = new UsernamePasswordCredentialsImpl(
        CredentialsScope.GLOBAL,
        CREDENTIAL_ID,
        CREDENTIAL_DESCRIPTION,
        CLI_USERNAME,
        apiToken
    )
    
    credentialsStore.addCredentials(globalDomain, credentials)
    println("API token stored in Jenkins credentials as '${CREDENTIAL_ID}'")
    
    // Jenkins全体を保存
    instance.save()
    
} catch (Exception e) {
    println("ERROR: Failed to generate or store API token: ${e.message}")
    e.printStackTrace()
}

// 保存されたクレデンシャルの確認
println("\n=== Verifying stored credentials ===")
def verifyCredentials = credentialsStore.getCredentials(globalDomain)
def savedCredential = verifyCredentials.find { it.id == CREDENTIAL_ID }
if (savedCredential != null) {
    println("✓ Credential '${CREDENTIAL_ID}' found in store")
    println("  Type: ${savedCredential.getClass().getSimpleName()}")
    println("  Description: ${savedCredential.description}")
    if (savedCredential instanceof UsernamePasswordCredentialsImpl) {
        println("  Username: ${savedCredential.username}")
        println("  Password stored: ${savedCredential.password != null ? 'Yes' : 'No'}")
    }
} else {
    println("✗ Credential '${CREDENTIAL_ID}' NOT found in store")
}

// トークンの一覧を表示（デバッグ用）
println("\n=== API Tokens for user ${CLI_USERNAME} ===")
def tokenProp = cliUser.getProperty(ApiTokenProperty.class)
if (tokenProp != null) {
    def tokens = tokenProp.tokenStore.getTokenListSortedByName()
    tokens.each { token ->
        println("  - ${token.name} (created: ${token.creationDate})")
    }
} else {
    println("  No API token property found")
}

println("\n=== CLI User Setup Completed ===")