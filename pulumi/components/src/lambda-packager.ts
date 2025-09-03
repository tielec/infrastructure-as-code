/**
 * Lambda Packagerの再エクスポート
 * 
 * このファイルは後方互換性のために維持されています。
 * 実際の実装は lambda-packager/ ディレクトリ内にモジュール化されています。
 */
export { 
  LambdaPackage,
  LambdaPackageArgs,
  PackageResult,
  DEFAULT_RUNTIME,
  DEFAULT_EXCLUDE_PATTERNS
} from "./lambda-packager/index";