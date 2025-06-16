/**
 * Jenkins ユーザー管理レポート生成スクリプト
 * 
 * 現在のユーザー状況を詳細にレポートします
 */

import jenkins.model.*
import hudson.model.*
import java.text.SimpleDateFormat

def jenkins = Jenkins.instance
def authStrategy = jenkins.getAuthorizationStrategy()
def sdf = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss")

println "=== Jenkins ユーザー管理レポート ==="
println "生成日時: ${sdf.format(new Date())}"
println "=" * 80

// ユーザー統計を収集
def allUsers = User.getAll()
def tielecUsers = []
def systemUsers = []
def otherUsers = []
def noEmailUsers = []

allUsers.each { user ->
    def userId = user.getId()
    def email = null
    
    try {
        def mailProp = user.getProperty(hudson.tasks.Mailer.UserProperty.class)
        if (mailProp != null) {
            email = mailProp.getAddress()
        }
    } catch (Exception e) {
        // エラーは無視
    }
    
    if (userId == "admin" || userId == "noreply" || userId == "SYSTEM") {
        systemUsers.add([userId: userId, email: email ?: "N/A"])
    } else if (email == null || email.isEmpty()) {
        noEmailUsers.add([userId: userId])
    } else if (email.endsWith("@tielec.net")) {
        tielecUsers.add([userId: userId, email: email])
    } else {
        otherUsers.add([userId: userId, email: email])
    }
}

// サマリー表示
println "\n【ユーザー統計サマリー】"
println "総ユーザー数: ${allUsers.size()}"
println "├─ @tielec.netユーザー: ${tielecUsers.size()}"
println "├─ その他のユーザー: ${otherUsers.size()}"
println "├─ メールアドレス未設定: ${noEmailUsers.size()}"
println "└─ システムユーザー: ${systemUsers.size()} (admin, SYSTEM)"

// @tielec.netユーザー詳細
if (tielecUsers.size() > 0) {
    println "\n【@tielec.netユーザー一覧】"
    println String.format("%-25s %-35s", "ユーザーID", "メールアドレス")
    println "-" * 60
    tielecUsers.sort { it.userId }.each { user ->
        println String.format("%-25s %-35s", user.userId, user.email)
    }
}

// その他のユーザー詳細
if (otherUsers.size() > 0) {
    println "\n【その他のユーザー一覧】"
    println String.format("%-25s %-35s", "ユーザーID", "メールアドレス")
    println "-" * 60
    otherUsers.sort { it.userId }.each { user ->
        println String.format("%-25s %-35s", user.userId, user.email)
    }
}

// メールアドレス未設定ユーザー
if (noEmailUsers.size() > 0) {
    println "\n【メールアドレス未設定ユーザー】"
    noEmailUsers.sort { it.userId }.each { user ->
        println "  - ${user.userId}"
    }
}

// Role Strategy Plugin使用時のロール情報
if (authStrategy.getClass().getName().contains("RoleBasedAuthorizationStrategy")) {
    println "\n【ロール割り当て情報】"
    
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
        
        roles.each { role ->
            def roleName = role.getName()
            def sids = grantedRoles.get(role)
            
            if (sids && sids.size() > 0) {
                println "\n${roleName}ロール (${sids.size()}人):"
                
                def userSids = []
                def groupSids = []
                
                sids.each { entry ->
                    def entryStr = entry.toString()
                    if (entryStr.contains("type=USER")) {
                        def matcher = entryStr =~ /sid='([^']+)'/
                        if (matcher.find()) {
                            userSids.add(matcher.group(1))
                        }
                    } else if (entryStr.contains("type=GROUP")) {
                        def matcher = entryStr =~ /sid='([^']+)'/
                        if (matcher.find()) {
                            groupSids.add(matcher.group(1))
                        }
                    }
                }
                
                if (userSids.size() > 0) {
                    println "  ユーザー:"
                    userSids.sort().each { sid ->
                        // ユーザーのメールアドレスを取得
                        def userEmail = "N/A"
                        try {
                            def user = User.get(sid, false)
                            if (user) {
                                def mailProp = user.getProperty(hudson.tasks.Mailer.UserProperty.class)
                                if (mailProp != null) {
                                    userEmail = mailProp.getAddress() ?: "N/A"
                                }
                            }
                        } catch (Exception e) {
                            // エラーは無視
                        }
                        println "    - ${sid} (${userEmail})"
                    }
                }
                
                if (groupSids.size() > 0) {
                    println "  グループ:"
                    groupSids.sort().each { sid ->
                        println "    - ${sid}"
                    }
                }
            }
        }
        
        // @tielec.netユーザーでadminロールを持たないユーザーを検出
        def adminRole = roles.find { it.getName() == "admin" }
        if (adminRole) {
            def adminSids = grantedRoles.get(adminRole) ?: []
            def adminUserIds = new HashSet()
            
            adminSids.each { entry ->
                def entryStr = entry.toString()
                if (entryStr.contains("type=USER")) {
                    def matcher = entryStr =~ /sid='([^']+)'/
                    if (matcher.find()) {
                        adminUserIds.add(matcher.group(1))
                    }
                }
            }
            
            def tielecUsersWithoutAdmin = tielecUsers.findAll { !adminUserIds.contains(it.userId) }
            
            if (tielecUsersWithoutAdmin.size() > 0) {
                println "\n【注意: adminロールを持たない@tielec.netユーザー】"
                tielecUsersWithoutAdmin.each { user ->
                    println "  - ${user.userId} (${user.email})"
                }
            }
        }
        
    } catch (Exception e) {
        println "ロール情報の取得中にエラーが発生しました: ${e.message}"
    }
} else {
    println "\nRole Strategy Pluginが無効です。"
}

// 最終更新情報
println "\n【システム情報】"
println "Jenkinsバージョン: ${jenkins.getVersion()}"
println "Role Strategy Plugin: ${authStrategy.getClass().getName().contains("RoleBasedAuthorizationStrategy") ? "有効" : "無効"}"

println "\n=== レポート生成完了 ==="
return "レポート生成成功"
