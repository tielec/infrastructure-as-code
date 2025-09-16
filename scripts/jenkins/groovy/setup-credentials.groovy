#!/usr/bin/env groovy
/**
 * Jenkinsクレデンシャルを一括設定するスクリプト
 * AWS Systems Manager Parameter Storeから各種認証情報を取得して登録
 */
import jenkins.model.*
import com.cloudbees.plugins.credentials.*
import com.cloudbees.plugins.credentials.domains.*
import com.cloudbees.plugins.credentials.impl.*
import com.cloudbees.jenkins.plugins.sshcredentials.impl.*
import org.jenkinsci.plugins.plaincredentials.impl.*
import hudson.util.Secret

def instance = Jenkins.getInstance()

// 環境変数から設定を取得
def PROJECT_NAME = System.getenv("PROJECT_NAME") ?: "jenkins-infra"
def ENVIRONMENT = System.getenv("ENVIRONMENT") ?: "dev"
def AWS_REGION = System.getenv("AWS_REGION") ?: "ap-northeast-1"

println("=== Starting Jenkins Credentials Setup ===")
println("Project: ${PROJECT_NAME}")
println("Environment: ${ENVIRONMENT}")
println("Region: ${AWS_REGION}")

// クレデンシャルストアの取得
def credentialsStore = SystemCredentialsProvider.getInstance().getStore()
def globalDomain = Domain.global()

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
        
        println("  Fetching: ${parameterPath}")
        def process = command.execute()
        def output = new StringBuilder()
        def error = new StringBuilder()
        
        process.consumeProcessOutput(output, error)
        process.waitForOrKill(30000) // 30秒のタイムアウト
        
        if (process.exitValue() != 0) {
            println("  ✗ Failed to get parameter")
            return null
        }
        
        def value = output.toString().trim()
        if (value.isEmpty()) {
            println("  ✗ Parameter is empty")
            return null
        }
        
        println("  ✓ Successfully retrieved")
        return value
    } catch (Exception e) {
        println("  ✗ Exception: ${e.message}")
        return null
    }
}

// 既存のクレデンシャルを更新または作成する関数
def upsertCredential = { credentialId, credential ->
    try {
        def existingCredentials = credentialsStore.getCredentials(globalDomain)
        def existingCredential = existingCredentials.find { it.id == credentialId }
        
        if (existingCredential != null) {
            println("  Updating existing credential: ${credentialId}")
            // 既存のクレデンシャルを更新する
            def removed = credentialsStore.updateCredentials(globalDomain, existingCredential, credential)
            if (!removed) {
                // updateCredentialsが失敗した場合、削除して再作成
                println("    Update failed, trying remove and add...")
                credentialsStore.removeCredentials(globalDomain, existingCredential)
                credentialsStore.addCredentials(globalDomain, credential)
            }
        } else {
            println("  Creating new credential: ${credentialId}")
            credentialsStore.addCredentials(globalDomain, credential)
        }
        
        println("  ✓ Successfully saved credential: ${credentialId}")
        return true
    } catch (Exception e) {
        println("  ✗ Failed to save credential: ${e.message}")
        return false
    }
}

// 処理結果のカウンター
def successCount = 0
def failureCount = 0
def skippedCount = 0

println("\n--- SSH Credentials ---")

// SSH秘密鍵クレデンシャルの設定
def sshCredentialMappings = [
    [
        parameterPath: "/jenkins-infra/${ENVIRONMENT}/agent/private-key",
        credentialId: "ec2-agent-keypair",
        description: "Spot Fleet で起動する EC2 Agent のSSH 秘密鍵",
        username: "ec2-user"
    ],
    [
        parameterPath: "/bootstrap/workterminal/private-key",
        credentialId: "ec2-bootstrap-workterminal-keypair",
        description: "Bootstrap環境のSSH 秘密鍵",
        username: "ec2-user"
    ]
]

sshCredentialMappings.each { mapping ->
    println("\nProcessing SSH credential: ${mapping.credentialId}")
    println("  Description: ${mapping.description}")
    
    def privateKey = getParameterFromSSM(mapping.parameterPath)
    if (!privateKey) {
        println("  ✗ Skipping - no private key available")
        skippedCount++
        return
    }
    
    // 秘密鍵の形式を検証
    if (!privateKey.contains("BEGIN") || !privateKey.contains("PRIVATE KEY")) {
        println("  ✗ Invalid private key format")
        failureCount++
        return
    }
    
    try {
        def privateKeySource = new BasicSSHUserPrivateKey.DirectEntryPrivateKeySource(privateKey)
        def credential = new BasicSSHUserPrivateKey(
            CredentialsScope.GLOBAL,
            mapping.credentialId,
            mapping.username,
            privateKeySource,
            null, // パスフレーズ
            mapping.description
        )
        
        if (upsertCredential(mapping.credentialId, credential)) {
            successCount++
        } else {
            failureCount++
        }
    } catch (Exception e) {
        println("  ✗ Exception: ${e.message}")
        failureCount++
    }
}

println("\n--- Secret Text Credentials ---")

// Secret Text クレデンシャルの設定
def secretTextMappings = [
    [
        parameterPath: "/bootstrap/openai/api-key",
        credentialId: "openai-api-key",
        description: "OpenAI API Key"
    ],
    [
        parameterPath: "/${PROJECT_NAME}/${ENVIRONMENT}/jenkins/cli-token",
        credentialId: "cli-user-token",
        description: "API token for Jenkins CLI user"
    ]
]

secretTextMappings.each { mapping ->
    println("\nProcessing secret text credential: ${mapping.credentialId}")
    println("  Description: ${mapping.description}")
    
    def secretValue = getParameterFromSSM(mapping.parameterPath)
    if (!secretValue) {
        println("  ✗ Skipping - no value available")
        skippedCount++
        return
    }
    
    try {
        def credential = new StringCredentialsImpl(
            CredentialsScope.GLOBAL,
            mapping.credentialId,
            mapping.description,
            Secret.fromString(secretValue)
        )
        
        if (upsertCredential(mapping.credentialId, credential)) {
            successCount++
        } else {
            failureCount++
        }
    } catch (Exception e) {
        println("  ✗ Exception: ${e.message}")
        failureCount++
    }
}

println("\n--- GitHub App Credentials ---")

// GitHub App クレデンシャルの設定
// GitHub App プラグインがインストールされている場合のみ処理
try {
    // GitHub App クレデンシャルクラスの存在確認
    def githubAppClass = Class.forName("org.jenkinsci.plugins.github_branch_source.GitHubAppCredentials")
    
    println("\nProcessing GitHub App credential: github-app-credentials")
    println("  Description: GitHub App for repository access")
    
    // GitHub App情報をSSMから取得
    def appId = getParameterFromSSM("/bootstrap/github/app-id")
    def privateKey = getParameterFromSSM("/bootstrap/github/app-private-key")
    def owner = getParameterFromSSM("/bootstrap/github/app-owner")
    
    if (!appId || !privateKey) {
        println("  ✗ Skipping - GitHub App ID or private key not available")
        skippedCount++
    } else {
        try {
            // GitHub App クレデンシャルの作成
            def credential = githubAppClass.newInstance(
                CredentialsScope.GLOBAL,
                "github-app-credentials",
                "GitHub App for repository access",
                appId,
                Secret.fromString(privateKey)
            )
            
            // ownerが指定されている場合は設定
            if (owner && !owner.isEmpty()) {
                credential.setOwner(owner)
            }
            
            if (upsertCredential("github-app-credentials", credential)) {
                successCount++
            } else {
                failureCount++
            }
        } catch (Exception e) {
            println("  ✗ Failed to create GitHub App credential: ${e.message}")
            failureCount++
        }
    }
} catch (ClassNotFoundException e) {
    println("\nGitHub App plugin not installed - skipping GitHub App credential")
    println("  To enable GitHub App authentication, install the 'GitHub Branch Source' plugin")
}

println("\n--- Username/Password Credentials ---")

// Username/Password クレデンシャルの設定
def usernamePasswordMappings = [
    [
        usernameParam: "/${PROJECT_NAME}/${ENVIRONMENT}/jenkins/cli-username",
        passwordParam: "/${PROJECT_NAME}/${ENVIRONMENT}/jenkins/cli-password",
        credentialId: "cli-user-credentials",
        description: "Jenkins CLI user credentials"
    ]
]

usernamePasswordMappings.each { mapping ->
    println("\nProcessing username/password credential: ${mapping.credentialId}")
    println("  Description: ${mapping.description}")
    
    def username = getParameterFromSSM(mapping.usernameParam)
    def password = getParameterFromSSM(mapping.passwordParam)
    
    if (!username || !password) {
        println("  ✗ Skipping - username or password not available")
        skippedCount++
        return
    }
    
    try {
        def credential = new UsernamePasswordCredentialsImpl(
            CredentialsScope.GLOBAL,
            mapping.credentialId,
            mapping.description,
            username,
            password
        )
        
        if (upsertCredential(mapping.credentialId, credential)) {
            successCount++
        } else {
            failureCount++
        }
    } catch (Exception e) {
        println("  ✗ Exception: ${e.message}")
        failureCount++
    }
}

// 処理結果のサマリー
println("\n=== Credentials Setup Summary ===")
println("Total credentials processed: ${successCount + failureCount + skippedCount}")
println("Successfully created/updated: ${successCount}")
println("Failed: ${failureCount}")
println("Skipped (no data): ${skippedCount}")

// 登録されたクレデンシャルの一覧を表示
if (System.getenv("LIST_CREDENTIALS") == "true") {
    println("\n=== Current Credentials ===")
    def allCredentials = credentialsStore.getCredentials(globalDomain)
    allCredentials.each { cred ->
        def type = cred.class.simpleName
        println("  - ID: ${cred.id}")
        println("    Type: ${type}")
        println("    Description: ${cred.description}")
    }
}

println("\n=== Jenkins Credentials Setup Completed ===")

if (failureCount > 0) {
    println("\nWARNING: Some credentials failed to create. Please check the logs above.")
}