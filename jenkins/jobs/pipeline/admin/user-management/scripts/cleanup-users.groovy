/**
 * Jenkins ユーザー削除スクリプト
 * 
 * 使用方法:
 * - dryRun = true: 削除対象を表示のみ（デフォルト）
 * - dryRun = false: 実際に削除を実行
 * - deleteNonDomainUsers = true: @tielec.net以外のユーザーを削除
 * - specificUsersToDelete: 特定のユーザーのみ削除
 */

import jenkins.model.*
import hudson.model.*

def dryRun = true  // Jenkinsfileから動的に変更される
def deleteNonDomainUsers = false  // @tielec.net以外のユーザーを削除するか
def specificUsersToDelete = []  // 特定のユーザーのみ削除する場合はここに指定

println "=== Jenkins ユーザー削除スクリプト ==="
println "モード: ${dryRun ? 'ドライラン（確認のみ）' : '実行モード'}"
println "削除オプション:"
if (deleteNonDomainUsers) {
    println "  - @tielec.net以外のユーザーを削除"
}
if (specificUsersToDelete) {
    println "  - 特定ユーザーを削除: ${specificUsersToDelete.join(', ')}"
}
if (!deleteNonDomainUsers && !specificUsersToDelete) {
    println "  - 削除対象なし"
}
println "実行時刻: ${new Date()}"
println "=" * 50

def jenkins = Jenkins.instance

// 保護するユーザー
def protectedUsers = ['admin','noreply','SYSTEM']

// 削除対象と保持対象のリスト
def usersToDelete = []
def usersToKeep = []

// すべてのユーザーを確認
User.getAll().each { user ->
    def userId = user.getId()
    def fullName = user.getFullName() ?: "未設定"
    def email = "未設定"
    
    // メールアドレスを取得
    try {
        def mailProp = user.getProperty(hudson.tasks.Mailer.UserProperty.class)
        if (mailProp != null) {
            email = mailProp.getAddress() ?: "未設定"
        }
    } catch (Exception e) {
        // エラーは無視
    }
    
    // 削除条件の判定
    if (protectedUsers.contains(userId)) {
        // 保護されたユーザー
        usersToKeep.add([userId: userId, fullName: fullName, email: email, reason: "保護ユーザー"])
    } else if (specificUsersToDelete && specificUsersToDelete.contains(userId)) {
        // 特定ユーザー削除対象
        usersToDelete.add([userId: userId, fullName: fullName, email: email, reason: "指定削除"])
    } else if (deleteNonDomainUsers && !email.endsWith("@tielec.net")) {
        // ドメイン外削除対象（特定ユーザーとして既に削除対象でない場合）
        if (!usersToDelete.any { it.userId == userId }) {
            usersToDelete.add([userId: userId, fullName: fullName, email: email, reason: "ドメイン外"])
        }
    } else {
        // それ以外は保持
        def reason = email.endsWith("@tielec.net") ? "@tielec.net" : "削除対象外"
        usersToKeep.add([userId: userId, fullName: fullName, email: email, reason: reason])
    }
}

// 保持するユーザーの表示
println "\n【保持するユーザー】"
println String.format("%-20s %-30s %-30s %-15s", "ユーザーID", "フルネーム", "メールアドレス", "理由")
println "-" * 95
usersToKeep.each { user ->
    println String.format("%-20s %-30s %-30s %-15s", 
        user.userId, user.fullName, user.email, user.reason)
}
println "保持ユーザー数: ${usersToKeep.size()}"

// 削除対象ユーザーの表示
println "\n【削除対象ユーザー】"
if (usersToDelete.size() > 0) {
    println String.format("%-20s %-30s %-30s %-15s", "ユーザーID", "フルネーム", "メールアドレス", "理由")
    println "-" * 95
    
    // 理由別に集計
    def byReason = usersToDelete.groupBy { it.reason }
    
    byReason.each { reason, users ->
        println "\n◆ ${reason} (${users.size()}件)"
        users.each { user ->
            println String.format("%-20s %-30s %-30s", 
                user.userId, user.fullName, user.email)
        }
    }
    
    println "\n削除対象ユーザー合計: ${usersToDelete.size()}"
    byReason.each { reason, users ->
        println "  - ${reason}: ${users.size()}件"
    }
} else {
    println "なし"
}

// 実際の削除処理
if (!dryRun && usersToDelete.size() > 0) {
    println "\n削除を実行中..."
    def deletedCount = 0
    def failedUsers = []
    
    usersToDelete.each { userInfo ->
        try {
            def user = User.get(userInfo.userId, false)
            if (user != null) {
                user.delete()
                deletedCount++
                println "削除完了: ${userInfo.userId}"
            }
        } catch (Exception e) {
            failedUsers.add(userInfo.userId)
            println "削除エラー: ${userInfo.userId} - ${e.message}"
        }
    }
    
    println "\n削除完了: ${deletedCount}/${usersToDelete.size()} ユーザー"
    
    if (failedUsers.size() > 0) {
        println "\n削除に失敗したユーザー:"
        failedUsers.each { userId ->
            println "  - ${userId}"
        }
    }
    
    return "成功"
} else if (dryRun && usersToDelete.size() > 0) {
    println "\n"
    println "**********************************************************************"
    println "* これはドライランモードです。実際には削除されていません。"
    println "**********************************************************************"
    return "ドライラン完了"
} else {
    println "\n削除対象のユーザーはありません。"
    return "対象なし"
}
