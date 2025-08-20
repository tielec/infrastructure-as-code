#!/usr/bin/env groovy
/**
 * Jenkins ユーザー（Admin、CLI）を作成するスクリプト
 * AWS Systems Manager Parameter Storeからパスワードを取得
 */
import jenkins.model.*
import hudson.model.*
import hudson.security.*
import jenkins.security.*
import jenkins.security.apitoken.*

def instance = Jenkins.getInstance()
def hudsonRealm = instance.getSecurityRealm()

// 環境変数から設定を取得
def PROJECT_NAME = System.getenv("PROJECT_NAME") ?: "jenkins-infra"
def ENVIRONMENT = System.getenv("ENVIRONMENT") ?: "dev"
def AWS_REGION = System.getenv("AWS_REGION") ?: "ap-northeast-1"

println("=== Starting Jenkins Users Setup ===")
println("Project: ${PROJECT_NAME}")
println("Environment: ${ENVIRONMENT}")
println("Region: ${AWS_REGION}")

// HudsonPrivateSecurityRealmでない場合はスキップ
if (!(hudsonRealm instanceof HudsonPrivateSecurityRealm)) {
    println("Security realm is not HudsonPrivateSecurityRealm. Skipping user creation.")
    return
}

// AWS CLIを使用してパラメータストアから値を取得する関数
def getParameterFromSSM = { parameterPath ->
    try {
        def command = [
            "aws", "ssm", "get-parameter",
            "--name", parameterPath,
            "--with-decryption",
            "--region", AWS_REGION,
            "--query", "Parameter.Value",
            "--output", "text"
        ]
        
        println("Fetching parameter: ${parameterPath}")
        def process = command.execute()
        def output = new StringBuilder()
        def error = new StringBuilder()
        
        process.consumeProcessOutput(output, error)
        process.waitForOrKill(30000) // 30秒のタイムアウト
        
        if (process.exitValue() != 0) {
            println("WARNING: Failed to get parameter ${parameterPath}")
            println("Error output: ${error.toString()}")
            return null
        }
        
        def value = output.toString().trim()
        if (value.isEmpty()) {
            println("WARNING: Parameter ${parameterPath} is empty")
            return null
        }
        
        println("✓ Successfully retrieved parameter")
        return value
    } catch (Exception e) {
        println("WARNING: Exception while getting parameter ${parameterPath}: ${e.message}")
        return null
    }
}

// ユーザー設定のマッピング
def userConfigs = [
    [
        username: "admin",
        fullname: "Jenkins Administrator",
        email: "admin@jenkins.local",
        passwordParam: "/${PROJECT_NAME}/${ENVIRONMENT}/jenkins/admin-password",
        isAdmin: true
    ],
    [
        username: "cli-user",
        fullname: "Jenkins CLI User",
        email: "cli-user@jenkins.local",
        passwordParam: "/${PROJECT_NAME}/${ENVIRONMENT}/jenkins/cli-password",
        isAdmin: false
    ]
]

// 作成されたユーザー情報を保存
def createdUsers = []

// 各ユーザーを処理
userConfigs.each { config ->
    println("\nProcessing user: ${config.username}")
    
    // パスワードを取得
    def password = getParameterFromSSM(config.passwordParam)
    
    if (!password) {
        // パスワードが取得できない場合はランダム生成（CLIユーザー用）
        if (config.username == "cli-user") {
            password = UUID.randomUUID().toString()
            println("Generated random password for CLI user")
        } else {
            println("WARNING: No password available for ${config.username}. Skipping.")
            return // continue to next user
        }
    }
    
    // 既存ユーザーをチェック
    def existingUser = null
    try {
        existingUser = hudsonRealm.getUser(config.username)
    } catch (Exception e) {
        // ユーザーが存在しない
    }
    
    if (existingUser != null) {
        println("User '${config.username}' already exists. Updating password.")
        // HudsonPrivateSecurityRealm.Details.fromPlainPasswordを使用してパスワードを更新
        def user = User.get(config.username)
        def passwordProperty = HudsonPrivateSecurityRealm.Details.fromPlainPassword(password)
        user.addProperty(passwordProperty)
        user.setFullName(config.fullname)
        def mailProperty = new hudson.tasks.Mailer.UserProperty(config.email)
        user.addProperty(mailProperty)
        user.save()
        createdUsers.add([username: config.username, existed: true])
    } else {
        println("Creating new user: ${config.username}")
        def user = hudsonRealm.createAccount(config.username, password)
        user.setFullName(config.fullname)
        def mailProperty = new hudson.tasks.Mailer.UserProperty(config.email)
        user.addProperty(mailProperty)
        user.save()
        createdUsers.add([username: config.username, existed: false])
    }
    
    // Admin権限を付与
    if (config.isAdmin) {
        println("Granting admin permissions to ${config.username}")
        def authStrategy = instance.getAuthorizationStrategy()
        
        if (authStrategy instanceof hudson.security.FullControlOnceLoggedInAuthorizationStrategy) {
            println("Authorization strategy is FullControlOnceLoggedIn. User will have full control.")
        } else if (authStrategy instanceof hudson.security.GlobalMatrixAuthorizationStrategy) {
            authStrategy.add(Jenkins.ADMINISTER, config.username)
            instance.save()
            println("Admin permissions granted via GlobalMatrixAuthorizationStrategy.")
        } else {
            println("WARNING: Could not grant specific permissions for current authorization strategy.")
        }
    }
    
    // CLIユーザーの場合、APIトークンを生成してSSMに保存
    if (config.username == "cli-user") {
        println("Generating API token for CLI user...")
        
        try {
            // ユーザーが作成されたばかりなので、Userオブジェクトを取得
            def cliUser = User.getById(config.username, false)
            if (cliUser == null) {
                println("WARNING: Failed to get CLI user object")
                return
            }
            def apiTokenProperty = cliUser.getProperty(ApiTokenProperty.class)
            
            // 既存のトークンをクリア（すべて削除）
            try {
                apiTokenProperty.deleteApiToken()
            } catch (Exception e) {
                println("  Note: No existing tokens to delete or deletion failed: ${e.message}")
            }
            
            // 新しいAPIトークンを生成
            def tokenName = "cli-automation-token"
            def result = apiTokenProperty.generateNewToken(tokenName)
            def apiToken = result.plainValue
            cliUser.save()
            
            println("✓ API token generated for CLI user")
            
            // SSMにユーザー名とトークンを保存
            def saveToSSM = { name, value ->
                try {
                    def paramPath = "/${PROJECT_NAME}/${ENVIRONMENT}/jenkins/${name}"
                    println("  Saving to SSM: ${paramPath}")
                    
                    def command = [
                        "aws", "ssm", "put-parameter",
                        "--name", paramPath,
                        "--value", value,
                        "--type", "SecureString",
                        "--overwrite",
                        "--region", AWS_REGION
                    ]
                    
                    def process = command.execute()
                    def output = new StringBuilder()
                    def error = new StringBuilder()
                    
                    process.consumeProcessOutput(output, error)
                    process.waitForOrKill(30000)
                    
                    if (process.exitValue() == 0) {
                        println("  ✓ Successfully saved ${name} to SSM")
                        return true
                    } else {
                        println("  ✗ Failed to save ${name} to SSM")
                        if (error.toString()) {
                            println("  Error: ${error.toString()}")
                        }
                        return false
                    }
                } catch (Exception e) {
                    println("  ✗ Exception while saving ${name} to SSM: ${e.message}")
                    e.printStackTrace()
                    return false
                }
            }
            
            saveToSSM("cli-username", config.username)
            saveToSSM("cli-password", password)
            saveToSSM("cli-token", apiToken)
            
        } catch (Exception e) {
            println("ERROR: Failed to generate API token for CLI user: ${e.message}")
            e.printStackTrace()
        }
    }
}

// 処理結果のサマリー
println("\n=== Users Setup Summary ===")
createdUsers.each { user ->
    def status = user.existed ? "Updated" : "Created"
    println("  - ${user.username}: ${status}")
}

println("\n=== Jenkins Users Setup Completed ===")