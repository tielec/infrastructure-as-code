import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";
import * as path from "path";
import { LambdaPackageArgs, PackageResult } from "./types";
import { NodejsPackager } from "./nodejs-packager";
import { PythonPackager } from "./python-packager";
import { ZipArchiver } from "./zip-archiver";
import { DEFAULT_RUNTIME, DEFAULT_INCLUDE_PATTERNS } from "./constants";
import { 
  getRuntimeType, 
  generateOutputPath, 
  ensureDirectory 
} from "./utils";
import { LambdaDeploymentBucket } from "../lambda-deployment-bucket";

/**
 * Lambda関数のコードをパッケージングするPulumiコンポーネント
 * 
 * 主な機能:
 * - Node.js/TypeScript/Pythonの依存関係管理
 * - TypeScriptの自動ビルド
 * - ZIPアーカイブの作成
 * - S3へのアップロード
 */
export class LambdaPackage extends pulumi.ComponentResource {
  public readonly zipPath: pulumi.Output<string>;
  public readonly zipHash: pulumi.Output<string>;
  public readonly sizeBytes: pulumi.Output<number>;
  
  private readonly name: string;
  private readonly runtime: pulumi.Output<string>;
  private readonly nodejsPackager: NodejsPackager;
  private readonly pythonPackager: PythonPackager;
  private readonly zipArchiver: ZipArchiver;

  constructor(
    name: string,
    args: LambdaPackageArgs,
    opts?: pulumi.ComponentResourceOptions
  ) {
    super("tielec:components:LambdaPackage", name, {}, opts);
    
    this.name = name;
    this.runtime = pulumi.output(args.runtime || DEFAULT_RUNTIME);
    
    // 各処理を担当するクラスのインスタンス化
    this.nodejsPackager = new NodejsPackager();
    this.pythonPackager = new PythonPackager();
    this.zipArchiver = new ZipArchiver();

    // パッケージ作成処理の実行
    const packageResult = this.createPackage(name, args);

    // 出力値の設定
    this.zipPath = packageResult.apply(result => result.zipPath);
    this.zipHash = packageResult.apply(result => result.zipHash);
    this.sizeBytes = packageResult.apply(result => result.sizeBytes);

    this.registerOutputs({
      zipPath: this.zipPath,
      zipHash: this.zipHash,
      sizeBytes: this.sizeBytes,
    });
  }

  /**
   * パッケージ作成のメイン処理
   */
  private createPackage(
    name: string,
    args: LambdaPackageArgs
  ): pulumi.Output<PackageResult> {
    return pulumi.all([
      args.sourcePath,
      args.runtime || DEFAULT_RUNTIME,
      args.installDependencies !== false,
      args.excludePatterns || [],
      args.includePatterns || DEFAULT_INCLUDE_PATTERNS,
      args.extraFiles || {},
    ]).apply(async ([
      sourcePath,
      runtime,
      installDependencies,
      excludePatterns,
      includePatterns,
      extraFiles
    ]) => {
      // 1. 出力パスの決定と準備
      const outputPath = generateOutputPath(name, args.outputPath, sourcePath);
      const outputDir = path.dirname(outputPath);
      ensureDirectory(outputDir);
      
      // 2. 言語固有の処理（依存関係インストール、ビルド）
      if (installDependencies) {
        await this.processLanguageSpecific(sourcePath, runtime, name);
      }
      
      // 3. ZIPアーカイブの作成
      return await this.zipArchiver.createArchive(
        outputPath,
        sourcePath,
        includePatterns,
        excludePatterns,
        extraFiles
      );
    });
  }

  /**
   * 言語固有の処理を実行
   */
  private async processLanguageSpecific(
    sourcePath: string,
    runtime: string,
    name: string
  ): Promise<void> {
    const runtimeType = getRuntimeType(runtime);
    
    switch (runtimeType) {
      case "nodejs":
        await this.nodejsPackager.processProject(sourcePath, name);
        break;
      
      case "python":
        await this.pythonPackager.processProject(sourcePath, name);
        break;
      
      case "unknown":
        pulumi.log.info(`Unknown runtime ${runtime}, skipping language-specific processing`);
        break;
    }
  }

  /**
   * Pulumiアセットとして作成
   */
  public createAsset(): pulumi.Output<pulumi.asset.FileArchive> {
    return this.zipPath.apply(path => new pulumi.asset.FileArchive(path));
  }

  /**
   * S3にアップロード
   */
  public uploadToS3(
    bucket: LambdaDeploymentBucket,
    name?: string
  ): aws.s3.BucketObject {
    const uploadName = name || this.name;
    return bucket.uploadLambdaPackage(
      uploadName,
      this.zipPath,
      this.zipHash,
      {
        "lambda-runtime": this.runtime,
        "package-size": this.sizeBytes.apply(s => s.toString()),
      }
    );
  }
}

// 型定義のエクスポート
export { LambdaPackageArgs, PackageResult } from "./types";

// 定数のエクスポート（必要に応じて）
export { DEFAULT_RUNTIME, DEFAULT_EXCLUDE_PATTERNS } from "./constants";