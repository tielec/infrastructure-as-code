/**
 * ユーザーのアクティベーション状態を確認するスクリプト
 * 
 * 指定されたユーザーが既に権限を持っているかチェックします
 */

import jenkins.model.*
import hudson.model.*

def targetUserId = ''  // Jenkinsfileから動的に設定される

println "=== ユーザー権限状態チェック ==="
println "対象ユーザー: ${targetUserId}"
println "実行時刻: ${new Date()}"
println "=" * 50

if (!targetUserId) {
    println "エラー: ユーザーIDが指定されていません"
    return "エラー"
}

def jenkins = Jenkins.instance
def authStrategy = jenkins.getAuthorizationStrategy()

// ユーザー情報を取得
def user = User.get(targetUserId, false)
if (!user) {
    println "エラー: ユーザーが見つかりません: ${targetUserId}"
    return "ユーザー不在"
}

// メールアドレスを取得
def email = "未設定"
try {
    def mailProp = user.getProperty(hudson.tasks.Mailer.UserProperty.class)
    if (mailProp != null) {
        email = mailProp.getAddress() ?: "未設定"
    }
} catch (Exception e) {
    // エラーは無視
}

println "\n【ユーザー情報】"
println "ユーザーID: ${targetUserId}"
println "フルネーム: ${user.getFullName() ?: '未設定'}"
println "メールアドレス: ${email}"

// Role Strategy Pluginのチェック
if (!authStrategy.getClass().getName().contains("RoleBasedAuthorizationStrategy")) {
    println "\nエラー: Role Strategy Pluginが有効になっていません"
    return "設定エラー"
}

try {
    // globalRolesフィールドを取得
    def globalRoleMapField = authStrategy.getClass().getDeclaredField("globalRoles")
    globalRoleMapField.setAccessible(true)
    def globalRoleMap = globalRoleMapField.get(authStrategy)
    
    // ロールを取得
    def getRolesMethod = globalRoleMap.getClass().getMethod("getRoles")
    def roles = getRolesMethod.invoke(globalRoleMap)
    
    // grantedRolesマップを取得
    def grantedRolesField = globalRoleMap.getClass().getDeclaredField("grantedRoles")
    grantedRolesField.setAccessible(true)
    def grantedRoles = grantedRolesField.get(globalRoleMap)
    
    println "\n【現在の権限状態】"
    
    def hasAdminRole = false
    def userRoles = []
    
    // 各ロールをチェック
    roles.each { role ->
        def roleName = role.getName()
        def sids = grantedRoles.get(role)
        
        if (sids) {
            sids.each { entry ->
                def entryStr = entry.toString()
                if (entryStr.contains("type=USER") && entryStr.contains("sid='${targetUserId}'")) {
                    userRoles.add(roleName)
                    if (roleName == "admin") {
                        hasAdminRole = true
                    }
                }
            }
        }
    }
    
    if (userRoles.size() > 0) {
        println "現在のロール:"
        userRoles.each { roleName ->
            println "  - ${roleName}"
        }
    } else {
        println "現在、ロールが割り当てられていません"
    }
    
    println "\n【診断結果】"
    if (hasAdminRole) {
        println "✓ すでに必要な権限を持っています"
        println "  adminロールが付与されています"
        return "アクティベート済み"
    } else {
        println "✗ 権限のアクティベーションが必要です"
        println "  adminロールが付与されていません"
        return "アクティベーション必要"
    }
    
} catch (Exception e) {
    println "\nエラーが発生しました: ${e.message}"
    e.printStackTrace()
    return "エラー"
}
