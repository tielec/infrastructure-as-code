#!/usr/bin/env groovy
/**
 * Jenkins CLIユーザーを作成し、APIトークンを生成してSSMに保存するスクリプト
 * init.groovy.dディレクトリに配置して、Jenkins起動時に実行される
 */
import jenkins.model.*
import hudson.model.*
import hudson.security.*
import jenkins.security.*
import jenkins.security.apitoken.*

def instance = Jenkins.getInstance()
def hudsonRealm = instance.getSecurityRealm()

// CLIユーザーの設定
def CLI_USERNAME = "cli-user"
def CLI_FULLNAME = "Jenkins CLI User"
def CLI_EMAIL = "cli-user@jenkins.local"

println("=== Starting CLI User Setup ===")

// HudsonPrivateSecurityRealmでない場合はスキップ
if (!(hudsonRealm instanceof HudsonPrivateSecurityRealm)) {
    println("Security realm is not HudsonPrivateSecurityRealm. Skipping CLI user creation.")
    return
}

// ユーザーが既に存在するかチェック
def existingUser = hudsonRealm.getUser(CLI_USERNAME)
if (existingUser != null) {
    println("CLI user '${CLI_USERNAME}' already exists. Checking token...")
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
}

// ユーザーを取得（作成済みまたは既存）
def cliUser = User.get(CLI_USERNAME, false, null)
if (cliUser == null) {
    println("ERROR: Failed to get CLI user")
    return
}

// APIトークンの生成または取得
def tokenProperty = cliUser.getProperty(ApiTokenProperty.class)
if (tokenProperty == null) {
    println("ERROR: Failed to get API token property")
    return
}

// 既存のトークンをチェック
def tokenStore = tokenProperty.getTokenStore()
def existingTokens = tokenStore.getTokenListSortedByName()
def tokenName = "cli-automation-token"
def apiToken = null

// 既存のトークンを探す
def existingToken = existingTokens.find { it.name == tokenName }
if (existingToken != null) {
    println("Token '${tokenName}' already exists. Skipping token generation.")
    // 既存トークンの値は取得できないので、SSMから取得することを前提とする
} else {
    println("Generating new API token: ${tokenName}")
    
    try {
        // 新しいトークンを生成
        def tokenResult = tokenProperty.tokenStore.generateNewToken(tokenName)
        apiToken = tokenResult.plainValue
        println("API token generated successfully")
        
        // SSMパラメータに保存
        saveTokenToSSM(apiToken)
        
    } catch (Exception e) {
        println("ERROR: Failed to generate API token: ${e.message}")
        e.printStackTrace()
    }
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

println("=== CLI User Setup Completed ===")

/**
 * APIトークンをSSMパラメータストアに保存
 */
def saveTokenToSSM(String token) {
    println("Attempting to save API token to SSM Parameter Store")
    
    try {
        // 環境変数から設定を取得（Jenkinsプロセスから継承）
        def projectName = System.getenv("PROJECT_NAME") ?: "jenkins-infra"
        def environment = System.getenv("ENVIRONMENT") ?: "dev"
        def region = System.getenv("AWS_REGION") ?: System.getenv("AWS_DEFAULT_REGION") ?: "ap-northeast-1"
        
        println("SSM Parameter configuration:")
        println("  PROJECT_NAME: ${projectName}")
        println("  ENVIRONMENT: ${environment}")
        println("  AWS_REGION: ${region}")
        
        def parameterName = "/${projectName}/${environment}/jenkins/cli-user-token"
        println("  Parameter path: ${parameterName}")
        
        // AWS CLIを使用してSSMパラメータを作成/更新
        def command = [
            "bash", "-c",
            "aws ssm put-parameter " +
            "--name '${parameterName}' " +
            "--value '${token}' " +
            "--type SecureString " +
            "--description 'Jenkins CLI user API token' " +
            "--overwrite " +
            "--region ${region}"
        ]
        
        println("Executing AWS CLI command...")
        
        def process = command.execute()
        def output = process.text
        def error = process.err.text
        process.waitFor()
        
        if (process.exitValue() == 0) {
            println("API token successfully saved to SSM parameter: ${parameterName}")
            println("Command output: ${output}")
        } else {
            println("ERROR: Failed to save token to SSM")
            println("Exit code: ${process.exitValue()}")
            println("Error output: ${error}")
            println("Standard output: ${output}")
        }
        
    } catch (Exception e) {
        println("ERROR: Exception while saving token to SSM: ${e.message}")
        e.printStackTrace()
    }
}
