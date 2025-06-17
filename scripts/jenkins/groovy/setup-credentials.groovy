#!/usr/bin/env groovy
/**
 * Jenkins内部のクレデンシャルストアにCLIユーザーのトークンを設定するスクリプト
 * SSMパラメータストアからトークンを取得して、Jenkinsクレデンシャルとして登録
 */
import jenkins.model.*
import hudson.model.*
import com.cloudbees.plugins.credentials.*
import com.cloudbees.plugins.credentials.common.*
import com.cloudbees.plugins.credentials.domains.*
import com.cloudbees.plugins.credentials.impl.*
import org.jenkinsci.plugins.plaincredentials.*
import org.jenkinsci.plugins.plaincredentials.impl.*
import hudson.util.Secret

def instance = Jenkins.getInstance()

println("=== Starting Credentials Setup ===")

// CLIユーザーが作成されるまで待機（最大60秒）
def maxWaitTime = 60
def waitInterval = 5
def elapsed = 0
def cliUserExists = false

println("Waiting for CLI user to be created...")
while (elapsed < maxWaitTime && !cliUserExists) {
    try {
        def cliUser = User.get("cli-user", false, null)
        if (cliUser != null) {
            cliUserExists = true
            println("CLI user found!")
            break
        }
    } catch (Exception e) {
        // ユーザーが存在しない場合
    }
    
    println("CLI user not found yet. Waiting... (${elapsed}s/${maxWaitTime}s)")
    Thread.sleep(waitInterval * 1000)
    elapsed += waitInterval
}

if (!cliUserExists) {
    println("ERROR: CLI user was not created within timeout. Exiting.")
    return
}

// 環境変数から設定を取得
def projectName = System.getenv("PROJECT_NAME") ?: "jenkins-infra"
def environment = System.getenv("ENVIRONMENT") ?: "dev"
def region = System.getenv("AWS_REGION") ?: getRegionFromMetadata()

// クレデンシャルの設定
def credentialId = "cli-user-token"
def credentialDescription = "Jenkins CLI User API Token"
def credentialScope = CredentialsScope.GLOBAL

// SSMパラメータ名
def parameterName = "/${projectName}/${environment}/jenkins/cli-user-token"

println("Fetching CLI token from SSM parameter: ${parameterName}")

// SSMからトークンを取得（リトライ付き）
def cliToken = null
def maxRetries = 3
def retryDelay = 5000 // 5秒

for (int i = 0; i < maxRetries; i++) {
    cliToken = getTokenFromSSM(parameterName, region)
    if (cliToken != null && !cliToken.isEmpty()) {
        break
    }
    
    if (i < maxRetries - 1) {
        println("Retry ${i + 1}/${maxRetries - 1}: Token not found, waiting ${retryDelay/1000} seconds...")
        Thread.sleep(retryDelay)
    }
}

if (cliToken == null || cliToken.isEmpty()) {
    println("ERROR: Could not retrieve CLI token from SSM after ${maxRetries} attempts. Skipping credential setup.")
    return
}

// クレデンシャルストアを取得
def credentialsStore = SystemCredentialsProvider.getInstance().getStore()
def globalDomain = Domain.global()

// 既存のクレデンシャルをチェック
def existingCredentials = credentialsStore.getCredentials(globalDomain)
def existingCredential = existingCredentials.find { it.id == credentialId }

if (existingCredential != null) {
    println("Credential '${credentialId}' already exists. Updating...")
    
    // 既存のクレデンシャルを削除
    credentialsStore.removeCredentials(globalDomain, existingCredential)
}

// 新しいクレデンシャルを作成
println("Creating new credential: ${credentialId}")
def secretText = new StringCredentialsImpl(
    credentialScope,
    credentialId,
    credentialDescription,
    Secret.fromString(cliToken)
)

// クレデンシャルを追加
credentialsStore.addCredentials(globalDomain, secretText)
println("Credential '${credentialId}' has been successfully created/updated")

// Jenkins APIトークンとしても登録（UsernamePasswordCredentials）
def apiCredentialId = "cli-user-api-auth"
def apiCredentialDescription = "Jenkins CLI User Authentication"
def cliUsername = "cli-user"

// 既存のAPIクレデンシャルをチェック
def existingApiCredential = existingCredentials.find { it.id == apiCredentialId }
if (existingApiCredential != null) {
    println("API credential '${apiCredentialId}' already exists. Updating...")
    credentialsStore.removeCredentials(globalDomain, existingApiCredential)
}

// UsernamePasswordCredentialsとして登録（JenkinsのAPIアクセス用）
def apiCredential = new UsernamePasswordCredentialsImpl(
    credentialScope,
    apiCredentialId,
    apiCredentialDescription,
    cliUsername,
    cliToken
)

credentialsStore.addCredentials(globalDomain, apiCredential)
println("API credential '${apiCredentialId}' has been successfully created/updated")

// 保存
instance.save()

println("=== Credentials Setup Completed ===")

/**
 * SSMパラメータストアからトークンを取得
 */
def getTokenFromSSM(String parameterName, String region) {
    try {
        def command = [
            "aws", "ssm", "get-parameter",
            "--name", parameterName,
            "--with-decryption",
            "--region", region,
            "--query", "Parameter.Value",
            "--output", "text"
        ]
        
        def process = command.execute()
        process.waitFor()
        
        if (process.exitValue() == 0) {
            def token = process.text.trim()
            if (token && !token.equals("null") && !token.isEmpty()) {
                println("Successfully retrieved token from SSM")
                return token
            }
        } else {
            def error = process.err.text
            println("ERROR: Failed to get token from SSM: ${error}")
        }
        
    } catch (Exception e) {
        println("ERROR: Exception while getting token from SSM: ${e.message}")
        e.printStackTrace()
    }
    
    return null
}

/**
 * EC2メタデータからリージョンを取得
 */
def getRegionFromMetadata() {
    try {
        // IMDSv2対応
        def tokenCommand = ["curl", "-s", "-X", "PUT", 
                          "http://169.254.169.254/latest/api/token", 
                          "-H", "X-aws-ec2-metadata-token-ttl-seconds: 21600"]
        def tokenProcess = tokenCommand.execute()
        tokenProcess.waitFor()
        def token = tokenProcess.text.trim()
        
        def regionCommand = ["curl", "-s", "-H", "X-aws-ec2-metadata-token: ${token}",
                           "http://169.254.169.254/latest/meta-data/placement/region"]
        def regionProcess = regionCommand.execute()
        regionProcess.waitFor()
        
        return regionProcess.text.trim()
    } catch (Exception e) {
        println("Failed to get region from metadata: ${e.message}")
        return "ap-northeast-1" // デフォルト値
    }
}
