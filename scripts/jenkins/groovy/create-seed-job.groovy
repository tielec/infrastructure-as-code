#!/usr/bin/env groovy
/**
 * Jenkins シードジョブを作成するスクリプト
 * Job DSLプラグインを使用して他のジョブを管理する
 */
import jenkins.model.*
import hudson.model.*
import com.cloudbees.plugins.credentials.*
import com.cloudbees.plugins.credentials.domains.*
import javax.xml.transform.stream.StreamSource
import org.jenkinsci.plugins.workflow.job.WorkflowJob
import hudson.plugins.git.*

def instance = Jenkins.getInstance()

// 設定
def seedJobNmae = System.getenv("SEED_JOB_NAME") ?: "seed-job"
def gitRepoUrl = System.getenv("GIT_INFRASTRUCTURE_REPO_URL") ?: "https://github.com/tielec/infrastructure-as-code.git"
def gitBranch = System.getenv("GIT_INFRASTRUCTURE_REPO_BRANCH") ?: "main"
def gitCredentialsId = System.getenv("GITHUB_APP_CREDENTIALS_ID") ?: "github-app-credentials"
def jobDslScriptsPath = System.getenv("JOB_DSL_SCRIPTS_PATH") ?: "jenkins/jobs/pipeline/_seed/job-creator/Jenkinsfile"

println("=== Starting Seed Job Setup ===")
println("Job Name: ${seedJobNmae}")
println("Git Repository: ${gitRepoUrl}")
println("Git Branch: ${gitBranch}")
println("Jenkinsfile Path: ${jobDslScriptsPath}")

// Job DSLプラグインの確認は不要（パイプラインジョブなので）
println("Creating pipeline job for seed job management")

// 既存のジョブをチェック
def existingJob = instance.getItem(seedJobNmae)
if (existingJob != null) {
    println("Job '${seedJobNmae}' already exists.")
    
    // 既存ジョブの更新オプション
    if (System.getenv("UPDATE_EXISTING_JOB") == "true") {
        println("Updating existing job configuration...")
        try {
            // XMLファイルから設定を読み込む
            def jobXmlFile = new File("/tmp/seed-job.xml")
            if (!jobXmlFile.exists()) {
                // スクリプトディレクトリから読み込む
                def scriptDir = System.getenv("SCRIPTS_DIR") ?: "/mnt/efs/jenkins/scripts"
                jobXmlFile = new File("${scriptDir}/jenkins/jobs/seed-job.xml")
            }
            
            if (jobXmlFile.exists()) {
                def jobXml = jobXmlFile.text
                // Git URLとブランチを置換
                jobXml = jobXml.replaceAll('https://github.com/tielec/infrastructure-as-code.git', gitRepoUrl)
                jobXml = jobXml.replaceAll('\\*/main', "*/${gitBranch}")
                jobXml = jobXml.replaceAll('jenkins/jobs/pipeline/_seed/job-creator/Jenkinsfile', jobDslScriptsPath)
                
                // ジョブを更新
                def xmlStream = new ByteArrayInputStream(jobXml.getBytes("UTF-8"))
                existingJob.updateByXml(new StreamSource(xmlStream))
                existingJob.save()
                println("Job '${seedJobNmae}' updated successfully")
            } else {
                println("WARNING: seed-job.xml not found, skipping update")
            }
        } catch (Exception e) {
            println("ERROR: Failed to update existing job: ${e.message}")
            e.printStackTrace()
        }
    } else {
        println("Skipping update of existing job (set UPDATE_EXISTING_JOB=true to update)")
    }
    return
}

// 新規ジョブの作成
println("Creating new seed job: ${seedJobNmae}")

try {
    // XMLファイルから設定を読み込む
    def jobXmlFile = new File("/tmp/seed-job.xml")
    if (!jobXmlFile.exists()) {
        // スクリプトディレクトリから読み込む
        def scriptDir = System.getenv("SCRIPTS_DIR") ?: "/mnt/efs/jenkins/scripts"
        jobXmlFile = new File("${scriptDir}/jenkins/jobs/seed-job.xml")
    }
    
    if (!jobXmlFile.exists()) {
        println("ERROR: seed-job.xml not found")
        println("Expected locations:")
        println("  - /tmp/seed-job.xml (exists: ${new File('/tmp/seed-job.xml').exists()})")
        
        def scriptDir = System.getenv("SCRIPTS_DIR") ?: "/mnt/efs/jenkins/scripts"
        def altPath = "${scriptDir}/jenkins/jobs/seed-job.xml"
        println("  - ${altPath} (exists: ${new File(altPath).exists()})")
        
        // 現在のディレクトリの内容を表示
        println("\nContents of /tmp:")
        new File("/tmp").listFiles().each { file ->
            if (file.name.contains("seed") || file.name.contains("job")) {
                println("  - ${file.name}")
            }
        }
        
        return
    }
    
    println("Loading job configuration from: ${jobXmlFile.absolutePath}")
    def jobXml = jobXmlFile.text
    
    // プレースホルダーを実際の値に置換
    jobXml = jobXml.replaceAll('https://github.com/tielec/infrastructure-as-code.git', gitRepoUrl)
    jobXml = jobXml.replaceAll('\\*/main', "*/${gitBranch}")
    jobXml = jobXml.replaceAll('jenkins/jobs/pipeline/_seed/job-creator/Jenkinsfile', jobDslScriptsPath)
    
    // 説明文内の変数も置換
    jobXml = jobXml.replaceAll('\\$\\{GIT_INFRASTRUCTURE_REPO_URL\\}', gitRepoUrl)
    jobXml = jobXml.replaceAll('\\$\\{GIT_INFRASTRUCTURE_REPO_BRANCH\\}', gitBranch)
    jobXml = jobXml.replaceAll('\\$\\{JENKINSFILE_PATH\\}', jobDslScriptsPath)
    
    // ジョブを作成
    def xmlStream = new ByteArrayInputStream(jobXml.getBytes("UTF-8"))
    
    // パイプラインジョブの場合は、createProjectFromXMLではなく、
    // 適切なジョブタイプを指定して作成する必要がある
    try {
        // Jenkins.instanceのcreateProjectFromXMLメソッドを使用
        def job = instance.createProjectFromXML(seedJobNmae, xmlStream)
        println("Seed job '${seedJobNmae}' created successfully")
        println("\nJob Configuration:")
        println("  - Repository: ${gitRepoUrl}")
        println("  - Branch: ${gitBranch}")
        println("  - Jenkinsfile: ${jobDslScriptsPath}")
        println("\nNext step: Run this job to create all other Jenkins jobs from your repository")
    } catch (Exception e) {
        // エラーが発生した場合は、別の方法を試す
        println("First attempt failed, trying alternative method: ${e.message}")
        
        // XMLを再度読み込み
        xmlStream = new ByteArrayInputStream(jobXml.getBytes("UTF-8"))
        
        try {
            // ItemLoaderを使用して作成
            def loader = new hudson.model.Items()
            def job = loader.load(instance, new File("/tmp/"), seedJobNmae, xmlStream)
            instance.putItem(job)
            println("Seed job '${seedJobNmae}' created successfully using alternative method")
        } catch (Exception e2) {
            println("ERROR: Both methods failed to create job")
            println("Error 1: ${e.message}")
            println("Error 2: ${e2.message}")
            e2.printStackTrace()
            return
        }
    }
    
    println("Seed job '${seedJobNmae}' created successfully")
    
    // 初回ビルドを実行するかどうか
    if (System.getenv("RUN_INITIAL_BUILD") == "true") {
        println("Scheduling initial build...")
        job.scheduleBuild2(5, new hudson.model.Cause.UserIdCause())
        println("Initial build scheduled")
    }
    
} catch (Exception e) {
    println("ERROR: Failed to create seed job: ${e.message}")
    e.printStackTrace()
}

// Gitクレデンシャルの確認
println("\nChecking Git credentials...")
def credentialsStore = SystemCredentialsProvider.getInstance().getStore()
def globalDomain = Domain.global()
def credentials = credentialsStore.getCredentials(globalDomain)
def gitCredential = credentials.find { it.id == gitCredentialsId }

if (gitCredential != null) {
    println("✓ Git credential '${gitCredentialsId}' found")
} else {
    println("✗ WARNING: Git credential '${gitCredentialsId}' not found")
    println("  The seed job will fail to checkout from Git without proper credentials")
    println("  Please create credentials with ID: ${gitCredentialsId}")
}

println("\n=== Seed Job Setup Completed ===")

// サンプルJenkinsfileの情報を表示
println("\nNext steps:")
println("1. Create a Jenkinsfile in your Git repository at: ${jobDslScriptsPath}")
println("2. The Jenkinsfile should use Job DSL to create other jobs")
println("\nExample Jenkinsfile content:")
println("""
pipeline {
    agent { 
        label 'ec2-fleet' 
    }
    
    stages {
        stage('Create Jobs') {
            steps {
                jobDsl targets: 'jobs/**/*.groovy',
                       removedJobAction: 'DELETE',
                       removedViewAction: 'DELETE',
                       lookupStrategy: 'JENKINS_ROOT'
            }
        }
    }
}
""")
