/**
 * Jenkins adminロール自動付与スクリプト
 * 
 * @tielec.netのメールアドレスを持つユーザーに自動的にadminロールを付与します。
 * 
 * 使用方法:
 * - dryRun = true: 変更をプレビューのみ（デフォルト）
 * - dryRun = false: 実際に変更を適用
 */

import jenkins.model.*
import hudson.model.*
import java.lang.reflect.*

def dryRun = true  // Jenkinsfileから動的に変更される

println "=== Jenkins adminロール付与スクリプト ==="
println "モード: ${dryRun ? 'ドライラン（確認のみ）' : '実行モード'}"
println "実行時刻: ${new Date()}"
println "=" * 50

def jenkins = Jenkins.instance
def authStrategy = jenkins.getAuthorizationStrategy()

if (!authStrategy.getClass().getName().contains("RoleBasedAuthorizationStrategy")) {
    println "エラー: Role Strategy Pluginが有効になっていません。"
    println "Manage Jenkins > Configure Global Security > Authorization で"
    println "「Role-Based Strategy」を選択してください。"
    return
}

try {
    // globalRolesフィールドを取得
    def globalRoleMapField = authStrategy.getClass().getDeclaredField("globalRoles")
    globalRoleMapField.setAccessible(true)
    def globalRoleMap = globalRoleMapField.get(authStrategy)

    // ロールを取得
    def getRolesMethod = globalRoleMap.getClass().getMethod("getRoles")
    def roles = getRolesMethod.invoke(globalRoleMap)
    def adminRole = roles.find { it.getName() == "admin" }

    if (!adminRole) {
        println "エラー: 'admin'ロールが見つかりません。"
        println "Manage Jenkins > Manage and Assign Roles > Manage Roles で"
        println "'admin'ロールを作成してください。"
        return
    }

    // grantedRolesマップを取得
    def grantedRolesField = globalRoleMap.getClass().getDeclaredField("grantedRoles")
    grantedRolesField.setAccessible(true)
    def grantedRoles = grantedRolesField.get(globalRoleMap)

    // 現在のadminロール保持者を取得
    def currentAdminSids = grantedRoles.get(adminRole) ?: new HashSet()

    println "\n【現在のadminロール保持者】"
    def currentAdminUserIds = new HashSet()
    currentAdminSids.each { permissionEntry ->
        println "  - ${permissionEntry}"
        try {
            def sidField = permissionEntry.getClass().getDeclaredField("sid")
            sidField.setAccessible(true)
            def sid = sidField.get(permissionEntry)
            currentAdminUserIds.add(sid)
        } catch (Exception e) {
            currentAdminUserIds.add(permissionEntry.toString())
        }
    }

    // @tielec.netのユーザーを収集
    def targetUsers = []
    def alreadyAdmins = []

    User.getAll().each { user ->
        def userId = user.getId()
        def email = "未設定"
        
        try {
            def mailProp = user.getProperty(hudson.tasks.Mailer.UserProperty.class)
            if (mailProp != null) {
                email = mailProp.getAddress() ?: "未設定"
            }
        } catch (Exception e) {
            // エラーは無視
        }
        
        if (email.endsWith("@tielec.net")) {
            if (currentAdminUserIds.contains(userId)) {
                alreadyAdmins.add([userId: userId, email: email])
            } else {
                targetUsers.add([userId: userId, email: email])
            }
        }
    }

    println "\n【既にadminロールを持つ@tielec.netユーザー】"
    if (alreadyAdmins.size() > 0) {
        println String.format("%-25s %-35s", "ユーザーID", "メールアドレス")
        println "-" * 60
        alreadyAdmins.each { user ->
            println String.format("%-25s %-35s", user.userId, user.email)
        }
    } else {
        println "  なし"
    }

    println "\n【adminロール付与が必要な@tielec.netユーザー】"
    if (targetUsers.size() > 0) {
        println String.format("%-25s %-35s", "ユーザーID", "メールアドレス")
        println "-" * 60
        targetUsers.each { user ->
            println String.format("%-25s %-35s", user.userId, user.email)
        }
    } else {
        println "  なし"
    }

    if (!dryRun && targetUsers.size() > 0) {
        println "\nadminロールを付与中..."
        
        // PermissionEntryクラスを取得
        def permissionEntryClass = currentAdminSids.iterator().next().getClass()
        
        // staticメソッド user(String) を取得
        def userMethod = permissionEntryClass.getMethod("user", String.class)
        
        // 新しいPermissionEntryセットを作成（既存のものをコピー）
        def newAdminSids = new HashSet(currentAdminSids)
        
        // 対象ユーザーを追加
        def addedCount = 0
        targetUsers.each { user ->
            try {
                def newEntry = userMethod.invoke(null, user.userId)
                newAdminSids.add(newEntry)
                println "  追加成功: ${user.userId}"
                addedCount++
            } catch (Exception e) {
                println "  追加失敗: ${user.userId} - ${e.message}"
            }
        }
        
        // grantedRolesマップを更新
        grantedRoles.put(adminRole, newAdminSids)
        
        // 設定を保存
        jenkins.save()
        
        println "\n付与完了！"
        println "追加したユーザー数: ${addedCount}/${targetUsers.size()}"
        println "adminロール保持者総数: ${newAdminSids.size()}"
    } else if (dryRun && targetUsers.size() > 0) {
        println "\n"
        println "**********************************************************************"
        println "* これはドライランモードです。実際にはロール付与されていません。"
        println "**********************************************************************"
    } else if (targetUsers.size() == 0) {
        println "\nすべての@tielec.netユーザーは既にadminロールを持っています。"
    }

    println "\n=== 実行完了 ==="
    return "成功"

} catch (Exception e) {
    println "\n重大なエラーが発生しました: ${e.message}"
    e.printStackTrace()
    return "失敗"
}
