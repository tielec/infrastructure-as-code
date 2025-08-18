#!/usr/bin/env groovy
/**
 * Jenkins adminユーザーを作成するスクリプト
 * init.groovy.dディレクトリに配置して、Jenkins起動時に実行される
 */
import jenkins.model.*
import hudson.model.*
import hudson.security.*

def instance = Jenkins.getInstance()
def hudsonRealm = instance.getSecurityRealm()

def ADMIN_USERNAME = "admin"
def ADMIN_FULLNAME = "Jenkins Administrator"
def ADMIN_EMAIL = "admin@jenkins.local"

// パスワードはスクリプト実行時にプレースホルダーから置換される
def adminPassword = "##JENKINS_ADMIN_PASSWORD_PLACEHOLDER##"

println("=== Starting Admin User Setup ===")

if (!(hudsonRealm instanceof HudsonPrivateSecurityRealm)) {
    println("Security realm is not HudsonPrivateSecurityRealm. Skipping admin user creation.")
    return
}

if (adminPassword == null || adminPassword.isEmpty()) {
    println("ERROR: JENKINS_ADMIN_PASSWORD environment variable not set. Skipping admin user creation.")
    return
}

def existingUser = hudsonRealm.getUser(ADMIN_USERNAME)
if (existingUser != null) {
    println("Admin user '${ADMIN_USERNAME}' already exists. Setting password.")
    existingUser.setPassword(adminPassword)
    existingUser.save()
    println("Admin user password updated.")
} else {
    println("Creating new admin user: ${ADMIN_USERNAME}")
    def user = hudsonRealm.createAccount(ADMIN_USERNAME, adminPassword)
    user.setFullName(ADMIN_FULLNAME)
    def mailProperty = new hudson.tasks.Mailer.UserProperty(ADMIN_EMAIL)
    user.addProperty(mailProperty)
    user.save()
    println("Admin user created successfully.")
}

// Admin権限を付与 (Matrixベースの認証戦略を想定)
println("Granting admin permissions to admin user")
def authStrategy = instance.getAuthorizationStrategy()

// loggedInUsersCanDoAnything の場合は、ログインさえすればadminなので特別な権限付与は不要
if (authStrategy instanceof hudson.security.FullControlOnceLoggedInAuthorizationStrategy) {
    println("Authorization strategy is FullControlOnceLoggedIn. Admin user will have full control.")
} else if (authStrategy instanceof hudson.security.GlobalMatrixAuthorizationStrategy) {
    authStrategy.add(Jenkins.ADMINISTER, ADMIN_USERNAME)
    instance.save()
    println("Admin permissions granted via GlobalMatrixAuthorizationStrategy.")
} else {
    println("WARNING: Authorization strategy is not FullControlOnceLoggedIn or GlobalMatrixAuthorizationStrategy. Could not grant specific permissions.")
}

println("=== Admin User Setup Completed ===")
