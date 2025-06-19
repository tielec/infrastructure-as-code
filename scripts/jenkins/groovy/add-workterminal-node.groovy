#!/usr/bin/env groovy
/**
 * Jenkins Workterminalノードを追加するスクリプト
 * Bootstrap環境用の永続的なSSHエージェントを設定
 */
import jenkins.model.*
import hudson.model.*
import hudson.slaves.*
import hudson.plugins.sshslaves.*
import hudson.plugins.sshslaves.verifiers.*
import com.cloudbees.plugins.credentials.*
import com.cloudbees.plugins.credentials.domains.*

def instance = Jenkins.getInstance()

// 環境変数から設定を取得
def NODE_NAME = System.getenv("WORKTERMINAL_NODE_NAME") ?: "bootstrap-workterminal"
def NODE_DESCRIPTION = System.getenv("WORKTERMINAL_NODE_DESCRIPTION") ?: "Bootstrap Workterminal Node"
def NODE_HOST = System.getenv("WORKTERMINAL_HOST") ?: ""
def NODE_PORT = Integer.parseInt(System.getenv("WORKTERMINAL_PORT") ?: "22")
def NODE_USER = System.getenv("WORKTERMINAL_USER") ?: "ec2-user"
def NODE_CREDENTIAL_ID = System.getenv("WORKTERMINAL_CREDENTIAL_ID") ?: "ec2-bootstrap-workterminal-keypair"
def NODE_REMOTE_FS = System.getenv("WORKTERMINAL_REMOTE_FS") ?: "/home/ec2-user/jenkins-agent"
def NODE_LABELS = System.getenv("WORKTERMINAL_LABELS") ?: "bootstrap-workterminal"
def NODE_EXECUTORS = Integer.parseInt(System.getenv("WORKTERMINAL_EXECUTORS") ?: "1")

println("=== Adding Workterminal Node ===")
println("Node Name: ${NODE_NAME}")
println("Host: ${NODE_HOST}")
println("Credential ID: ${NODE_CREDENTIAL_ID}")

// ホストが指定されていない場合はBootstrap-InstanceのPublic IPを取得
if (!NODE_HOST || NODE_HOST.isEmpty()) {
    println("Host not provided, attempting to retrieve Bootstrap-Instance Public IP...")
    
    def PROJECT_NAME = System.getenv("PROJECT_NAME") ?: "jenkins-infra"
    def ENVIRONMENT = System.getenv("ENVIRONMENT") ?: "dev"
    def AWS_REGION = System.getenv("AWS_REGION") ?: "ap-northeast-1"
    
    try {
        // Bootstrap-Instanceを検索
        def command = [
            "aws", "ec2", "describe-instances",
            "--region", AWS_REGION,
            "--filters", 
            "Name=tag:Name,Values=Bootstrap-Instance",
            "Name=instance-state-name,Values=running",
            "--query", "Reservations[0].Instances[0].PublicIpAddress",
            "--output", "text"
        ]
        
        def process = command.execute()
        def output = new StringBuilder()
        def error = new StringBuilder()
        process.consumeProcessOutput(output, error)
        process.waitForOrKill(30000)
        
        if (process.exitValue() == 0 && output.toString().trim() != "None" && output.toString().trim() != "null") {
            NODE_HOST = output.toString().trim()
            println("Retrieved Bootstrap-Instance Public IP: ${NODE_HOST}")
        } else {
            println("Bootstrap-Instance not found or has no public IP")
            println("Error output: ${error.toString()}")
            
            // フォールバック: SSMパラメータから取得を試みる
            println("Falling back to SSM Parameter Store...")
            def parameterPath = "/bootstrap/workterminal/public-ip"
            
            command = [
                "aws", "ssm", "get-parameter",
                "--name", parameterPath,
                "--region", AWS_REGION,
                "--query", "Parameter.Value",
                "--output", "text"
            ]
            
            process = command.execute()
            output = new StringBuilder()
            process.consumeProcessOutput(output, new StringBuilder())
            process.waitForOrKill(30000)
            
            if (process.exitValue() == 0) {
                NODE_HOST = output.toString().trim()
                println("Retrieved Workterminal host from SSM: ${NODE_HOST}")
            }
        }
    } catch (Exception e) {
        println("WARNING: Failed to retrieve Bootstrap-Instance IP: ${e.message}")
    }
}

if (!NODE_HOST || NODE_HOST.isEmpty()) {
    println("ERROR: No host specified for Workterminal node")
    println("Please ensure one of the following:")
    println("  - Bootstrap-Instance is running with tag Name=Bootstrap-Instance")
    println("  - WORKTERMINAL_HOST environment variable is set")
    println("  - SSM parameter exists at /bootstrap/workterminal/public-ip")
    return
}

// 既存のノードを確認
def existingNode = instance.getNode(NODE_NAME)

if (existingNode != null) {
    println("Node '${NODE_NAME}' already exists")
    if (System.getenv("UPDATE_EXISTING_NODE") == "true") {
        println("Removing existing node configuration...")
        instance.removeNode(existingNode)
    } else {
        println("Skipping configuration (set UPDATE_EXISTING_NODE=true to update)")
        // 既存ノードのホストが変更されているかチェック
        if (existingNode.getLauncher() instanceof SSHLauncher) {
            def launcher = existingNode.getLauncher()
            if (launcher.getHost() != NODE_HOST) {
                println("WARNING: Host has changed from ${launcher.getHost()} to ${NODE_HOST}")
                println("Consider updating the node configuration")
            }
        }
        return
    }
}

// SSHクレデンシャルの存在確認
def credentialsStore = SystemCredentialsProvider.getInstance().getStore()
def globalDomain = Domain.global()
def sshCredential = credentialsStore.getCredentials(globalDomain).find { it.id == NODE_CREDENTIAL_ID }

if (sshCredential == null) {
    println("ERROR: SSH credential '${NODE_CREDENTIAL_ID}' not found")
    println("Please ensure the credential is created before adding the node")
    return
}

try {
    println("Creating Workterminal node configuration...")
    
    // SSH接続の設定
    def sshLauncher = new SSHLauncher(
        NODE_HOST,                                          // host
        NODE_PORT,                                          // port
        NODE_CREDENTIAL_ID,                                 // credentialsId
        null,                                               // jvmOptions
        null,                                               // javaPath
        null,                                               // prefixStartSlaveCmd
        null,                                               // suffixStartSlaveCmd
        60,                                                 // launchTimeoutSeconds
        10,                                                 // maxNumRetries
        5,                                                  // retryWaitTime
        new NonVerifyingKeyVerificationStrategy()           // sshHostKeyVerificationStrategy
    )
    
    // Permanent Agentの作成
    def workterminalNode = new DumbSlave(
        NODE_NAME,                                          // name
        NODE_DESCRIPTION,                                   // description
        NODE_REMOTE_FS,                                     // remoteFS
        Integer.toString(NODE_EXECUTORS),                   // numExecutors
        Node.Mode.EXCLUSIVE,                                // mode (このノード専用)
        NODE_LABELS,                                        // labels
        sshLauncher,                                        // launcher
        RetentionStrategy.INSTANCE,                         // retentionStrategy (常時接続)
        new ArrayList()                                     // nodeProperties
    )
    
    // ノードを追加
    instance.addNode(workterminalNode)
    instance.save()
    
    println("✓ Workterminal node '${NODE_NAME}' configured successfully")
    println("  Host: ${NODE_HOST}:${NODE_PORT}")
    println("  Remote FS: ${NODE_REMOTE_FS}")
    println("  Labels: ${NODE_LABELS}")
    println("  Executors: ${NODE_EXECUTORS}")
    println("  Mode: Exclusive (dedicated for specific jobs)")
    
    // ノードの接続を試みる
    println("\nAttempting to connect to the node...")
    def computer = workterminalNode.toComputer()
    if (computer != null) {
        computer.connect(false)
        println("Connection initiated. Check node status in Jenkins UI.")
    }
    
} catch (Exception e) {
    println("ERROR: Failed to add Workterminal node: ${e.message}")
    e.printStackTrace()
}

// 設定の検証
println("\n=== Validating Workterminal Node Configuration ===")

// ノードの一覧を確認
def allNodes = instance.getNodes()
def addedNode = allNodes.find { it.name == NODE_NAME }

if (addedNode != null) {
    println("✓ Node '${NODE_NAME}' successfully added to Jenkins")
    
    // コンピューターの状態を確認
    def computer = addedNode.toComputer()
    if (computer != null) {
        println("  Online: ${computer.isOnline()}")
        println("  Connecting: ${computer.isConnecting()}")
        if (!computer.isOnline() && !computer.isConnecting()) {
            println("  Offline Reason: ${computer.getOfflineCauseReason()}")
        }
    }
} else {
    println("✗ WARNING: Node '${NODE_NAME}' not found after configuration")
}

println("\n=== Workterminal Node Configuration Completed ===")
