package jp.co.tielec.git

/**
 * Git操作中に発生する例外を表すクラス
 */
class GitOperationException extends Exception {
    /**
     * エラーメッセージのみを指定するコンストラクタ
     * @param message エラーメッセージ
     */
    GitOperationException(String message) {
        super(message)
    }
    
    /**
     * エラーメッセージと原因となる例外を指定するコンストラクタ
     * @param message エラーメッセージ
     * @param cause 原因となる例外
     */
    GitOperationException(String message, Throwable cause) {
        super(message, cause)
    }
}