#!groovy
import jenkins.model.*
import hudson.security.*
import jenkins.install.InstallState

println "=== Configuring basic security ==="
def instance = Jenkins.getInstance()

// Clear any existing security realm and authorization strategy
instance.setSecurityRealm(null)
instance.setAuthorizationStrategy(null)
instance.save()

def hudsonRealm = new HudsonPrivateSecurityRealm(false)
if (hudsonRealm.getAllUsers().isEmpty()) {
    println "=== Creating admin user ==="
    hudsonRealm.createAccount("admin", "admin")
}

instance.setSecurityRealm(hudsonRealm)

def strategy = new FullControlOnceLoggedInAuthorizationStrategy()
strategy.setAllowAnonymousRead(false)
instance.setAuthorizationStrategy(strategy)

if(!instance.getInstallState().isSetupComplete()) {
    println "=== Marking install as complete ==="
    instance.setInstallState(InstallState.INITIAL_SETUP_COMPLETED)
}

instance.save()
println "=== Basic security configuration completed ==="
