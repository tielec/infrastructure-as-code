import jenkins.model.*
import com.cloudbees.plugins.credentials.*
import com.cloudbees.plugins.credentials.impl.*
import com.cloudbees.plugins.credentials.domains.*
import org.jenkinsci.plugins.plaincredentials.impl.*
import hudson.util.Secret

def jenkins = Jenkins.getInstance()

// OpenAI APIキーの取得（SSMパラメータから環境変数として渡される）
def openaiApiKey = System.getenv("OPENAI_API_KEY")
if (!openaiApiKey) {
    println "Error: OPENAI_API_KEY environment variable not set"
    return
}

// クレデンシャルストアの取得
def domain = Domain.global()
def store = SystemCredentialsProvider.getInstance().getStore()

// 既存のクレデンシャルを確認
def credentialId = "openai-api-key"
def existingCredentials = store.getCredentials(domain)
def existingCredential = existingCredentials.find { it.id == credentialId }

if (existingCredential) {
    println "Updating existing OpenAI API key credential: ${credentialId}"
    store.removeCredentials(domain, existingCredential)
} else {
    println "Creating new OpenAI API key credential: ${credentialId}"
}

// 新しいSecretTextクレデンシャルを作成
def newCredential = new StringCredentialsImpl(
    CredentialsScope.GLOBAL,
    credentialId,
    "OpenAI API Key",
    Secret.fromString(openaiApiKey)
)

// クレデンシャルを追加
store.addCredentials(domain, newCredential)

println "✓ OpenAI API key credential '${credentialId}' has been successfully configured"

// 保存
jenkins.save()