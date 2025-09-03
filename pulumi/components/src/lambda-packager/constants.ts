/**
 * Lambda Packager用の定数定義
 */

/**
 * デフォルトのランタイム
 */
export const DEFAULT_RUNTIME = "nodejs18.x";

/**
 * Lambda ZIPパッケージから除外するファイルパターン
 * 実行環境に不要なファイルを除外してパッケージサイズを最小化
 */
export const DEFAULT_EXCLUDE_PATTERNS = [
  // アーカイブファイル
  "*.zip",
  
  // バージョン管理
  ".git/**",
  ".gitignore",
  
  // 環境設定
  ".env*",
  
  // テストファイル
  "*.test.js",
  "*.test.ts", 
  "*.spec.js",
  "*.spec.ts",
  "__tests__/**",
  "test/**",
  "tests/**",
  
  // カバレッジ
  "coverage/**",
  ".nyc_output/**",
  
  // IDE設定
  ".vscode/**",
  ".idea/**",
  
  // ソースマップ
  "*.map",
  
  // 設定ファイル
  "tsconfig.json",
  "package-lock.json",
  "yarn.lock",
  
  // TypeScriptソースコード（ビルド後のdist/を使用）
  "src/**",
  
  // Claude設定
  ".claude/**",
];

/**
 * デフォルトのインクルードパターン
 */
export const DEFAULT_INCLUDE_PATTERNS = ["**"];

/**
 * 各言語のビルド出力ディレクトリ
 */
export const BUILD_OUTPUT_DIRS = {
  typescript: "dist",
  javascript: ".",
  python: ".",
} as const;

/**
 * 各言語の設定ファイル
 */
export const LANGUAGE_CONFIG_FILES = {
  typescript: "tsconfig.json",
  javascript: "package.json",
  python: "requirements.txt",
} as const;

/**
 * ZIPアーカイブの圧縮レベル（最大圧縮）
 */
export const ZIP_COMPRESSION_LEVEL = 9;