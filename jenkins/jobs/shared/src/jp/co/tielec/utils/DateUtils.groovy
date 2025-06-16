package jp.co.tielec.utils

/**
 * 日付操作に関するユーティリティクラス
 */
class DateUtils implements Serializable {
    private static final long serialVersionUID = 1L

    /**
     * 日付フォーマットを検証する (YYYY-MM-DD)
     * @param dateStr 検証対象の日付文字列
     * @throws IllegalArgumentException 日付フォーマットが不正な場合
     */
    static void validateDateFormat(String dateStr) {
        if (!dateStr?.trim()) {
            throw new IllegalArgumentException("日付文字列が指定されていません")
        }
        
        def datePattern = ~/^\d{4}-\d{2}-\d{2}$/
        if (!(dateStr =~ datePattern)) {
            throw new IllegalArgumentException("日付フォーマットが不正です: ${dateStr}。YYYY-MM-DD形式で指定してください")
        }
        
        try {
            // 日付としての妥当性を検証
            def sdf = new java.text.SimpleDateFormat("yyyy-MM-dd")
            sdf.setLenient(false)
            sdf.parse(dateStr)
        } catch (java.text.ParseException e) {
            throw new IllegalArgumentException("不正な日付: ${dateStr}。${e.message}")
        }
    }
    
    /**
     * ISO 8601形式の日付文字列をパースする
     * @param dateTimeStr ISO 8601形式の日付文字列 (例: "2023-01-01T12:00:00Z")
     * @return パースされた日付オブジェクト
     */
    static java.util.Date parseIsoDateTime(String dateTimeStr) {
        if (!dateTimeStr?.trim()) {
            return null
        }
        
        def sdf = new java.text.SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'")
        sdf.setTimeZone(java.util.TimeZone.getTimeZone("UTC"))
        return sdf.parse(dateTimeStr)
    }
    
    /**
     * 日付の範囲内かどうかを確認する
     * @param dateToCheck 確認対象の日付
     * @param startDate 開始日
     * @param endDate 終了日
     * @return 範囲内の場合はtrue、それ以外はfalse
     */
    static boolean isDateInRange(java.util.Date dateToCheck, java.util.Date startDate, java.util.Date endDate) {
        return !dateToCheck.before(startDate) && !dateToCheck.after(endDate)
    }
    
    /**
     * 日付文字列をISO 8601形式でフォーマットする
     * @param dateStr YYYY-MM-DD形式の日付文字列
     * @param startOfDay 日の開始時刻の場合はtrue、終了時刻の場合はfalse
     * @return ISO 8601形式の日付文字列
     */
    static String formatDateToIso(String dateStr, boolean startOfDay = true) {
        validateDateFormat(dateStr)
        return startOfDay ? "${dateStr}T00:00:00Z" : "${dateStr}T23:59:59Z"
    }
}