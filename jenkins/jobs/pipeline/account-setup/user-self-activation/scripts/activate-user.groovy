/**
 * ユーザー権限アクティベーションスクリプト
 * 
 * 指定されたユーザーにadminロールを付与します
 * @tielec.netドメインのユーザーのみ対象
 */

import jenkins.model.*
import hudson.model.*

def targetUserId = ''  // Jenkinsfileから動的に設定される

println "=== ユーザー権限アクティベーション ==="
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

// メールアドレスを取得して@tielec.netドメインかチェック
def email = null
try {
    def mailProp = user.getProperty(hudson.tasks.Mailer.UserProperty.class)
    if (mailProp != null) {
        email = mailProp.getAddress()
    }
} catch (Exception e) {
    println "メールアドレスの取得中にエラー: ${e.message}"
}

if (!email) {
    println "エラー: メールアドレスが設定されていません"
    return "メールアドレス未設定"
}

if (!email.endsWith("@tielec.net")) {
    println "エラー: @tielec.netドメインのユーザーではありません"
    println "メールアドレス: ${email}"
    return "ドメインエラー"
}

println "\n【ユーザー情報】"
println "ユーザーID: ${targetUserId}"
println "フルネーム: ${user.getFullName() ?: '未設定'}"
println "メールアドレス: ${email}"
println "✓ @tielec.netドメインを確認"

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
    def adminRole = roles.find { it.getName() == "admin" }
    
    if (!adminRole) {
        println "\nエラー: 'admin'ロールが存在しません"
        println "管理者に連絡してadminロールを作成してもらってください"
        return "ロール不在"
    }
    
    // grantedRolesマップを取得
    def grantedRolesField = globalRoleMap.getClass().getDeclaredField("grantedRoles")
    grantedRolesField.setAccessible(true)
    def grantedRoles = grantedRolesField.get(globalRoleMap)
    
    // 現在のadminロール保持者を取得
    def currentAdminSids = grantedRoles.get(adminRole) ?: new HashSet()
    
    // すでにadminロールを持っているかチェック
    def alreadyHasAdmin = false
    currentAdminSids.each { entry ->
        def entryStr = entry.toString()
        if (entryStr.contains("type=USER") && entryStr.contains("sid='${targetUserId}'")) {
            alreadyHasAdmin = true
        }
    }
    
    if (alreadyHasAdmin) {
        println "\n【結果】"
        println "すでにadminロールを持っています"
        println "再度アクティベートする必要はありません"
        return "既にアクティベート済み"
    }
    
    println "\n【権限付与処理】"
    println "adminロールを付与します..."
    
    // PermissionEntryクラスを取得
    def permissionEntryClass = null
    if (currentAdminSids.size() > 0) {
        permissionEntryClass = currentAdminSids.iterator().next().getClass()
    } else {
        // 既存のエントリがない場合は、別のロールから取得
        for (role in roles) {
            def sids = grantedRoles.get(role)
            if (sids && sids.size() > 0) {
                permissionEntryClass = sids.iterator().next().getClass()
                break
            }
        }
    }
    
    if (!permissionEntryClass) {
        println "エラー: PermissionEntryクラスを取得できません"
        return "技術的エラー"
    }
    
    // staticメソッド user(String) を取得
    def userMethod = permissionEntryClass.getMethod("user", String.class)
    
    // 新しいPermissionEntryセットを作成（既存のものをコピー）
    def newAdminSids = new HashSet(currentAdminSids)
    
    // 対象ユーザーを追加
    def newEntry = userMethod.invoke(null, targetUserId)
    newAdminSids.add(newEntry)
    
    // grantedRolesマップを更新
    grantedRoles.put(adminRole, newAdminSids)
    
    // 設定を保存
    jenkins.save()
    
    println "\n【アクティベーション完了】"
    println "✓ ${targetUserId} にadminロールを付与しました"
    println "✓ Jenkinsの全機能が利用可能になりました"
    
    // 付与後の確認
    println "\n【付与後の確認】"
    println "adminロール保持者総数: ${newAdminSids.size()}"
    
    return "アクティベーション完了"
    
} catch (Exception e) {
    println "\n重大なエラーが発生しました: ${e.message}"
    e.printStackTrace()
    return "エラー"
}
