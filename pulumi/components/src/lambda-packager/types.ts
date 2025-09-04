import * as pulumi from "@pulumi/pulumi";

/**
 * Lambda Packagerの引数型定義
 */
export interface LambdaPackageArgs {
  /** Lambda関数のソースコードがあるディレクトリパス */
  sourcePath: pulumi.Input<string>;
  
  /** Lambdaランタイム (例: nodejs18.x, python3.9) */
  runtime?: pulumi.Input<string>;
  
  /** 依存関係を自動インストールするか (デフォルト: true) */
  installDependencies?: pulumi.Input<boolean>;
  
  /** ZIPから除外するファイルパターン */
  excludePatterns?: pulumi.Input<string[]>;
  
  /** ZIPに含めるファイルパターン */
  includePatterns?: pulumi.Input<string[]>;
  
  /** ZIP出力先パス（未指定時は自動生成） */
  outputPath?: string;
  
  /** 追加で含めるファイル（キー: ZIPパス内のパス、値: ファイル内容） */
  extraFiles?: pulumi.Input<{ [key: string]: string }>;
}

/**
 * パッケージング結果
 */
export interface PackageResult {
  /** 生成されたZIPファイルのパス */
  zipPath: string;
  
  /** ZIPファイルのSHA256ハッシュ値 */
  zipHash: string;
  
  /** ZIPファイルのサイズ（バイト） */
  sizeBytes: number;
}

/**
 * ランタイム種別
 */
export type RuntimeType = "nodejs" | "python" | "unknown";

/**
 * Node.jsプロジェクトのpackage.json型
 */
export interface PackageJson {
  name?: string;
  version?: string;
  scripts?: {
    [key: string]: string;
  };
  dependencies?: {
    [key: string]: string;
  };
  devDependencies?: {
    [key: string]: string;
  };
}

/**
 * ビルド設定
 */
export interface BuildConfig {
  /** ビルドが必要か */
  needsBuild: boolean;
  
  /** ビルドコマンド */
  buildCommand?: string;
  
  /** ビルド出力ディレクトリ */
  outputDirectory?: string;
  
  /** 開発依存関係のインストールが必要か */
  needsDevDependencies?: boolean;
}