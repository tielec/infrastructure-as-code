#!/usr/bin/env groovy
/**
 * Jenkins EC2 Fleet Cloudを設定するスクリプト
 * AWS EC2 Fleetプラグインを使用してスポットインスタンスベースのエージェントを管理
 */
import jenkins.model.*
import hudson.model.*
import hudson.plugins.ec2.fleet.*
import com.amazonaws.services.ec2.model.*

def instance = Jenkins.getInstance()

// 環境変数から設定を取得
def PROJECT_NAME = System.getenv("PROJECT_NAME") ?: "jenkins-infra"
def ENVIRONMENT = System.getenv("ENVIRONMENT") ?: "dev"
def AWS_REGION = System.getenv("AWS_REGION") ?: "ap-northeast-1"

// EC2 Fleet設定のデフォルト値
def CLOUD_NAME = System.getenv("EC2_FLEET_CLOUD_NAME") ?: "ec2-fleet"
def FLEET_REGION = System.getenv("EC2_FLEET_REGION") ?: AWS_REGION
def SSH_CREDENTIAL_ID = System.getenv("EC2_FLEET_SSH_CREDENTIAL") ?: "ec2-agent-keypair"
def NUM_EXECUTORS = Integer.parseInt(System.getenv("EC2_FLEET_NUM_EXECUTORS") ?: "3")
def MAX_IDLE_MINUTES = Integer.parseInt(System.getenv("EC2_FLEET_MAX_IDLE_MINUTES") ?: "15")
def MIN_SIZE = Integer.parseInt(System.getenv("EC2_FLEET_MIN_SIZE") ?: "0")
def MAX_SIZE = Integer.parseInt(System.getenv("EC2_FLEET_MAX_SIZE") ?: "1")
def MAX_INIT_TIMEOUT = Integer.parseInt(System.getenv("EC2_FLEET_MAX_INIT_TIMEOUT") ?: "900")
def STATUS_INTERVAL = Integer.parseInt(System.getenv("EC2_FLEET_STATUS_INTERVAL") ?: "30")

println("=== Starting EC2 Fleet Cloud Configuration ===")
println("Cloud Name: ${CLOUD_NAME}")
println("Region: ${FLEET_REGION}")
println("SSH Credential: ${SSH_CREDENTIAL_ID}")

// 既存のクラウド設定を確認
def existingCloud = instance.clouds.find { it.name == CLOUD_NAME }

if (existingCloud != null) {
    println("Cloud '${CLOUD_NAME}' already exists")
    if (System.getenv("UPDATE_EXISTING_CLOUD") == "true") {
        println("Removing existing cloud configuration...")
        instance.clouds.remove(existingCloud)
    } else {
        println("Skipping configuration (set UPDATE_EXISTING_CLOUD=true to update)")
        return
    }
}

try {
    println("Creating EC2 Fleet Cloud configuration...")
    
    // Fleet IDを取得（SSMパラメータまたは環境変数から）
    def fleetId = System.getenv("EC2_FLEET_ID")
    
    if (!fleetId) {
        // SSMパラメータから取得を試みる
        println("Fleet ID not provided, attempting to retrieve from SSM Parameter Store...")
        def parameterPath = "/${PROJECT_NAME}/${ENVIRONMENT}/jenkins/agent/spotFleetRequestId"
        
        try {
            def command = [
                "aws", "ssm", "get-parameter",
                "--name", parameterPath,
                "--region", AWS_REGION,
                "--query", "Parameter.Value",
                "--output", "text"
            ]
            
            def process = command.execute()
            def output = new StringBuilder()
            process.consumeProcessOutput(output, new StringBuilder())
            process.waitForOrKill(30000)
            
            if (process.exitValue() == 0) {
                fleetId = output.toString().trim()
                println("Retrieved Fleet ID from SSM: ${fleetId}")
            }
        } catch (Exception e) {
            println("WARNING: Failed to retrieve Fleet ID from SSM: ${e.message}")
        }
    }
    
    if (!fleetId) {
        // フリートIDが取得できない場合は、アクティブなフリートを検索
        println("Fleet ID not found, searching for active fleets...")
        
        try {
            def command = [
                "aws", "ec2", "describe-fleets",
                "--region", FLEET_REGION,
                "--filters", "Name=state,Values=active",
                "--query", "Fleets[?Tags[?Key=='Project' && Value=='${PROJECT_NAME}']].FleetId",
                "--output", "text"
            ]
            
            def process = command.execute()
            def output = new StringBuilder()
            process.consumeProcessOutput(output, new StringBuilder())
            process.waitForOrKill(30000)
            
            if (process.exitValue() == 0 && output.toString().trim()) {
                fleetId = output.toString().trim().split()[0] // 最初のフリートIDを使用
                println("Found active Fleet ID: ${fleetId}")
            }
        } catch (Exception e) {
            println("WARNING: Failed to search for active fleets: ${e.message}")
        }
    }
    
    if (!fleetId) {
        println("ERROR: No Fleet ID found. Please ensure an EC2 Fleet is created and active.")
        println("You can set the Fleet ID using:")
        println("  - Environment variable: EC2_FLEET_ID")
        println("  - SSM Parameter: /${PROJECT_NAME}/${ENVIRONMENT}/jenkins/agent/spotFleetRequestId")
        return
    }
    
    // EC2 Fleet Cloud設定の作成
    def fleetCloud = new EC2FleetCloud(
        CLOUD_NAME,              // name
        null,                    // awsCredentialsId (null = use IAM role)
        null,                    // credentialsId (deprecated)
        FLEET_REGION,            // region
        null,                    // endpoint (null = default)
        fleetId,                 // fleet
        "jenkins-agent-",        // labelString (prefix for labels)
        "",                      // idleTerminationMinutes (managed by fleet)
        MIN_SIZE,                // minSize
        MAX_SIZE,                // maxSize
        NUM_EXECUTORS,           // numExecutors
        false,                   // addNodeOnlyIfRunning
        false,                   // restrictUsage
        MAX_INIT_TIMEOUT,        // initOnlineTimeoutSec
        MAX_INIT_TIMEOUT,        // cloudStatusIntervalSec (using same as init timeout)
        true,                    // disableTaskResubmit
        MAX_INIT_TIMEOUT,        // initOnlineCheckIntervalSec
        false,                   // scaleExecutorsByWeight
        MAX_IDLE_MINUTES         // maxIdleMinutesBeforeScaledown
    )
    
    // SSH接続の設定
    fleetCloud.setConnectBySSHProcess(false)
    fleetCloud.setConnectionStrategy(new StandardSSHConnectionStrategy(false)) // false = don't verify host key
    fleetCloud.setPrivateKey(SSH_CREDENTIAL_ID)
    fleetCloud.setConnect(true)
    
    // ラベルの設定
    fleetCloud.setLabelString("ec2-fleet docker linux")
    
    // クラウドを追加
    instance.clouds.add(fleetCloud)
    instance.save()
    
    println("✓ EC2 Fleet Cloud '${CLOUD_NAME}' configured successfully")
    println("  Fleet ID: ${fleetId}")
    println("  Region: ${FLEET_REGION}")
    println("  Min Size: ${MIN_SIZE}")
    println("  Max Size: ${MAX_SIZE}")
    println("  Executors per Node: ${NUM_EXECUTORS}")
    println("  Max Idle Minutes: ${MAX_IDLE_MINUTES}")
    
} catch (Exception e) {
    println("ERROR: Failed to configure EC2 Fleet Cloud: ${e.message}")
    e.printStackTrace()
}

// 設定の検証
println("\n=== Validating EC2 Fleet Configuration ===")

// SSHクレデンシャルの存在確認
def credentialsStore = com.cloudbees.plugins.credentials.SystemCredentialsProvider.getInstance().getStore()
def globalDomain = com.cloudbees.plugins.credentials.domains.Domain.global()
def sshCredential = credentialsStore.getCredentials(globalDomain).find { it.id == SSH_CREDENTIAL_ID }

if (sshCredential != null) {
    println("✓ SSH credential '${SSH_CREDENTIAL_ID}' found")
} else {
    println("✗ WARNING: SSH credential '${SSH_CREDENTIAL_ID}' not found")
    println("  EC2 Fleet will not be able to connect to agents without proper SSH credentials")
}

// 現在設定されているクラウドの一覧
println("\n=== Current Cloud Configurations ===")
instance.clouds.each { cloud ->
    println("  - ${cloud.name} (${cloud.class.simpleName})")
}

println("\n=== EC2 Fleet Cloud Configuration Completed ===")
