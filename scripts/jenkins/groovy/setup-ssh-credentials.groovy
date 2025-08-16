#!/usr/bin/env groovy
/**
 * AWS Systems Manager Parameter StoreからSSH秘密鍵を取得してJenkinsクレデンシャルに登録するスクリプト
 * 複数のパラメータストアパスから秘密鍵を読み込み、対応するクレデンシャルを作成します
 */
import jenkins.model.*
import hudson.model.*
import com.cloudbees.plugins.credentials.*
import com.cloudbees.plugins.credentials.domains.*
import com.cloudbees.plugins.credentials.impl.*
import com.cloudbees.jenkins.plugins.sshcredentials.impl.*
import hudson.util.Secret
import groovy.json.JsonSlurper

def instance = Jenkins.getInstance()

// 環境変数から設定を取得
def PROJECT_NAME = System.getenv("PROJECT_NAME") ?: "jenkins-infra"
def ENVIRONMENT = System.getenv("ENVIRONMENT") ?: "dev"
def AWS_REGION = System.getenv("AWS_REGION") ?: "ap-northeast-1"

println("=== Starting SSH Credentials Setup from Parameter Store ===")
println("Project: ${PROJECT_NAME}")
println("Environment: ${ENVIRONMENT}")
println("Region: ${AWS_REGION}")

// SSH秘密鍵の設定マッピング
// パラメータストアのパス -> クレデンシャル設定のマッピング
def credentialMappings = [
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

// 追加のマッピングを環境変数から読み込む（カスタマイズ用）
def additionalMappings = System.getenv("ADDITIONAL_SSH_CREDENTIALS")
if (additionalMappings) {
    println("Loading additional credential mappings from environment variable")
    try {
        def jsonSlurper = new JsonSlurper()
        def mappings = jsonSlurper.parseText(additionalMappings)
        credentialMappings.addAll(mappings)
    } catch (Exception e) {
        println("WARNING: Failed to parse ADDITIONAL_SSH_CREDENTIALS: ${e.message}")
    }
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
            println("ERROR: Failed to get parameter ${parameterPath}")
            println("Error output: ${error.toString()}")
            return null
        }
        
        def value = output.toString().trim()
        if (value.isEmpty()) {
            println("ERROR: Parameter ${parameterPath} is empty")
            return null
        }
        
        println("✓ Successfully retrieved parameter")
        return value
    } catch (Exception e) {
        println("ERROR: Exception while getting parameter ${parameterPath}: ${e.message}")
        e.printStackTrace()
        return null
    }
}

// クレデンシャルストアの取得
def credentialsStore = SystemCredentialsProvider.getInstance().getStore()
def globalDomain = Domain.global()

// 既存のクレデンシャルを取得
def existingCredentials = credentialsStore.getCredentials(globalDomain)

// 各マッピングを処理
def successCount = 0
def failureCount = 0
def skippedCount = 0

credentialMappings.each { mapping ->
    println("\nProcessing credential: ${mapping.credentialId}")
    println("  Parameter path: ${mapping.parameterPath}")
    println("  Description: ${mapping.description}")
    println("  Username: ${mapping.username}")
    
    // 既存のクレデンシャルをチェック
    def existingCredential = existingCredentials.find { it.id == mapping.credentialId }
    
    if (existingCredential != null) {
        println("  ✓ Credential '${mapping.credentialId}' already exists")
        
        // 更新オプションがある場合
        if (System.getenv("UPDATE_EXISTING_CREDENTIALS") == "true") {
            println("  Updating existing credential...")
            try {
                // 既存のクレデンシャルを削除
                credentialsStore.removeCredentials(globalDomain, existingCredential)
                println("  Removed existing credential")
            } catch (Exception e) {
                println("  ERROR: Failed to remove existing credential: ${e.message}")
                failureCount++
                return // continue to next mapping
            }
        } else {
            println("  Skipping (set UPDATE_EXISTING_CREDENTIALS=true to update)")
            skippedCount++
            return // continue to next mapping
        }
    }
    
    // パラメータストアから秘密鍵を取得
    def privateKey = getParameterFromSSM(mapping.parameterPath)
    if (privateKey == null) {
        println("  ✗ Failed to retrieve private key from Parameter Store")
        failureCount++
        return // continue to next mapping
    }
    
    // 秘密鍵の形式を検証
    if (!privateKey.contains("BEGIN") || !privateKey.contains("PRIVATE KEY")) {
        println("  ✗ ERROR: Retrieved value does not appear to be a valid private key")
        failureCount++
        return // continue to next mapping
    }
    
    // SSH秘密鍵クレデンシャルを作成
    try {
        def privateKeySource = new BasicSSHUserPrivateKey.DirectEntryPrivateKeySource(privateKey)
        def credential = new BasicSSHUserPrivateKey(
            CredentialsScope.GLOBAL,
            mapping.credentialId,
            mapping.username,
            privateKeySource,
            null, // パスフレーズ（必要に応じて設定）
            mapping.description
        )
        
        // クレデンシャルを保存
        credentialsStore.addCredentials(globalDomain, credential)
        println("  ✓ Successfully created SSH credential '${mapping.credentialId}'")
        successCount++
        
    } catch (Exception e) {
        println("  ✗ ERROR: Failed to create credential: ${e.message}")
        e.printStackTrace()
        failureCount++
    }
}

// 処理結果のサマリー
println("\n=== SSH Credentials Setup Summary ===")
println("Total credentials processed: ${credentialMappings.size()}")
println("Successfully created/updated: ${successCount}")
println("Failed: ${failureCount}")
println("Skipped (already exist): ${skippedCount}")

// オプション: 登録されたクレデンシャルの一覧を表示
if (System.getenv("LIST_CREDENTIALS") == "true") {
    println("\n=== Current SSH Credentials ===")
    def allCredentials = credentialsStore.getCredentials(globalDomain)
    allCredentials.findAll { it instanceof BasicSSHUserPrivateKey }.each { cred ->
        println("  - ID: ${cred.id}")
        println("    Username: ${cred.username}")
        println("    Description: ${cred.description}")
    }
}

println("\n=== SSH Credentials Setup Completed ===")

// エラーがある場合は警告を表示
if (failureCount > 0) {
    println("\nWARNING: Some credentials failed to create. Please check the logs above.")
}
