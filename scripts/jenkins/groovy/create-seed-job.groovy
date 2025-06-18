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
def SEED_JOB_NAME = System.getenv("SEED_JOB_NAME") ?: "seed-job"
def GIT_REPO_URL = System.getenv("JENKINS_JOBS_REPO") ?: "https://github.com/tielec/infrastructure-as-code.git"
def GIT_BRANCH = System.getenv("JENKINS_JOBS_BRANCH") ?: "main"
def GIT_CREDENTIALS_ID = System.getenv("GIT_CREDENTIALS_ID") ?: "github-credentials"
def JOB_DSL_SCRIPTS_PATH = System.getenv("JOB_DSL_SCRIPTS_PATH") ?: "jenkins/jobs/pipeline/_seed/job-creator/Jenkinsfile"

println("=== Starting Seed Job Setup ===")
println("Job Name: ${SEED_JOB_NAME}")
println("Git Repository: ${GIT_REPO_URL}")
println("Git Branch: ${GIT_BRANCH}")
println("Jenkinsfile Path: ${JOB_DSL_SCRIPTS_PATH}")

// Job DSLプラグインの確認は不要（パイプラインジョブなので）
println("Creating pipeline job for seed job management")

// 既存のジョブをチェック
def existingJob = instance.getItem(SEED_JOB_NAME)
if (existingJob != null) {
    println("Job '${SEED_JOB_NAME}' already exists.")
    
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
                jobXml = jobXml.replaceAll('https://github.com/tielec/infrastructure-as-code.git', GIT_REPO_URL)
                jobXml = jobXml.replaceAll('\\*/main', "*/${GIT_BRANCH}")
                jobXml = jobXml.replaceAll('jenkins/jobs/pipeline/_seed/job-creator/Jenkinsfile', JOB_DSL_SCRIPTS_PATH)
                
                // ジョブを更新
                def xmlStream = new ByteArrayInputStream(jobXml.getBytes("UTF-8"))
                existingJob.updateByXml(new StreamSource(xmlStream))
                existingJob.save()
                println("Job '${SEED_JOB_NAME}' updated successfully")
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
println("Creating new seed job: ${SEED_JOB_NAME}")

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
    jobXml = jobXml.replaceAll('https://github.com/tielec/infrastructure-as-code.git', GIT_REPO_URL)
    jobXml = jobXml.replaceAll('\\*/main', "*/${GIT_BRANCH}")
    jobXml = jobXml.replaceAll('jenkins/jobs/pipeline/_seed/job-creator/Jenkinsfile', JOB_DSL_SCRIPTS_PATH)
    
    // 説明文内の変数も置換
    jobXml = jobXml.replaceAll('\\$\\{JENKINS_JOBS_REPO\\}', GIT_REPO_URL)
    jobXml = jobXml.replaceAll('\\$\\{JENKINS_JOBS_BRANCH\\}', GIT_BRANCH)
    jobXml = jobXml.replaceAll('\\$\\{JENKINSFILE_PATH\\}', JOB_DSL_SCRIPTS_PATH)
    
    // ジョブを作成
    def xmlStream = new ByteArrayInputStream(jobXml.getBytes("UTF-8"))
    
    // パイプラインジョブの場合は、createProjectFromXMLではなく、
    // 適切なジョブタイプを指定して作成する必要がある
    try {
        // Jenkins.instanceのcreateProjectFromXMLメソッドを使用
        def job = instance.createProjectFromXML(SEED_JOB_NAME, xmlStream)
        println("Seed job '${SEED_JOB_NAME}' created successfully")
        println("\nJob Configuration:")
        println("  - Repository: ${GIT_REPO_URL}")
        println("  - Branch: ${GIT_BRANCH}")
        println("  - Jenkinsfile: ${JOB_DSL_SCRIPTS_PATH}")
        println("\nNext step: Run this job to create all other Jenkins jobs from your repository")
    } catch (Exception e) {
        // エラーが発生した場合は、別の方法を試す
        println("First attempt failed, trying alternative method: ${e.message}")
        
        // XMLを再度読み込み
        xmlStream = new ByteArrayInputStream(jobXml.getBytes("UTF-8"))
        
        try {
            // ItemLoaderを使用して作成
            def loader = new hudson.model.Items()
            def job = loader.load(instance, new File("/tmp/"), SEED_JOB_NAME, xmlStream)
            instance.putItem(job)
            println("Seed job '${SEED_JOB_NAME}' created successfully using alternative method")
        } catch (Exception e2) {
            println("ERROR: Both methods failed to create job")
            println("Error 1: ${e.message}")
            println("Error 2: ${e2.message}")
            e2.printStackTrace()
            return
        }
    }
    
    println("Seed job '${SEED_JOB_NAME}' created successfully")
    
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
def gitCredential = credentials.find { it.id == GIT_CREDENTIALS_ID }

if (gitCredential != null) {
    println("✓ Git credential '${GIT_CREDENTIALS_ID}' found")
} else {
    println("✗ WARNING: Git credential '${GIT_CREDENTIALS_ID}' not found")
    println("  The seed job will fail to checkout from Git without proper credentials")
    println("  Please create credentials with ID: ${GIT_CREDENTIALS_ID}")
}

println("\n=== Seed Job Setup Completed ===")

// サンプルJenkinsfileの情報を表示
println("\nNext steps:")
println("1. Create a Jenkinsfile in your Git repository at: ${JOB_DSL_SCRIPTS_PATH}")
println("2. The Jenkinsfile should use Job DSL to create other jobs")
println("\nExample Jenkinsfile content:")
println("""
pipeline {
    agent any
    
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
