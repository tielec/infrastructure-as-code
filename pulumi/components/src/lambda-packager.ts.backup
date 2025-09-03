import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";
import * as archiver from "archiver";
import * as fs from "fs";
import * as path from "path";
import * as crypto from "crypto";
import { promisify } from "util";
import { exec } from "child_process";
import { LambdaDeploymentBucket } from "./lambda-deployment-bucket";

const execAsync = promisify(exec);

export interface LambdaPackageArgs {
  sourcePath: pulumi.Input<string>;
  runtime?: pulumi.Input<string>;
  installDependencies?: pulumi.Input<boolean>;
  excludePatterns?: pulumi.Input<string[]>;
  includePatterns?: pulumi.Input<string[]>;
  outputPath?: string;
  extraFiles?: pulumi.Input<{ [key: string]: string }>;
}

interface PackageResult {
  zipPath: string;
  zipHash: string;
  sizeBytes: number;
}

export class LambdaPackage extends pulumi.ComponentResource {
  public readonly zipPath: pulumi.Output<string>;
  public readonly zipHash: pulumi.Output<string>;
  public readonly sizeBytes: pulumi.Output<number>;
  private readonly name: string;
  private readonly runtime: pulumi.Output<string>;

  constructor(
    name: string,
    args: LambdaPackageArgs,
    opts?: pulumi.ComponentResourceOptions
  ) {
    super("tielec:components:LambdaPackage", name, {}, opts);
    this.name = name;
    this.runtime = pulumi.output(args.runtime || "nodejs18.x");

    const packageOutput = this.createPackage(name, args);

    this.zipPath = packageOutput.apply(
      (result) => result.zipPath
    );
    this.zipHash = packageOutput.apply(
      (result) => result.zipHash
    );
    this.sizeBytes = packageOutput.apply(
      (result) => result.sizeBytes
    );

    this.registerOutputs({
      zipPath: this.zipPath,
      zipHash: this.zipHash,
      sizeBytes: this.sizeBytes,
    });
  }

  /**
   * パッケージを作成するメイン処理
   */
  private createPackage(
    name: string,
    args: LambdaPackageArgs
  ): pulumi.Output<PackageResult> {
    return pulumi.all([
      args.sourcePath,
      args.runtime || "nodejs18.x",
      args.installDependencies !== false,
      args.excludePatterns || [],
      args.includePatterns || ["**"],
      args.extraFiles || {},
    ]).apply(async ([
      sourcePath,
      runtime,
      installDependencies,
      excludePatterns,
      includePatterns,
      extraFiles
    ]) => {
      const outputPath = this.getOutputPath(name, args.outputPath, sourcePath);
      
      // 出力ディレクトリを作成
      this.ensureOutputDirectory(outputPath);
      
      // 依存関係のインストールとビルド
      await this.installDependenciesAndBuild(
        sourcePath,
        runtime,
        installDependencies,
        name
      );
      
      // ZIPファイルを作成
      return await this.createZipArchive(
        outputPath,
        sourcePath,
        includePatterns,
        excludePatterns,
        extraFiles
      );
    });
  }


  /**
   * 出力パスを生成
   */
  private getOutputPath(
    name: string,
    outputPath: string | undefined,
    sourcePath: string
  ): string {
    if (outputPath) {
      return outputPath;
    }

    const sourceHash = crypto
      .createHash("sha256")
      .update(sourcePath)
      .digest("hex")
      .substring(0, 8);

    return path.join(
      process.cwd(),
      ".pulumi",
      "lambdas",
      `${name}-${sourceHash}.zip`
    );
  }

  /**
   * 出力ディレクトリを確保
   */
  private ensureOutputDirectory(outputPath: string): void {
    const outputDir = path.dirname(outputPath);
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }
  }

  /**
   * 依存関係のインストールとビルドを実行
   */
  private async installDependenciesAndBuild(
    sourcePath: string,
    runtime: string,
    installDependencies: boolean,
    name: string
  ): Promise<void> {
    if (!installDependencies) {
      return;
    }

    if (runtime.startsWith("nodejs")) {
      await this.handleNodejsProject(sourcePath, name);
    } else if (runtime.startsWith("python")) {
      await this.handlePythonProject(sourcePath, name);
    }
  }

  /**
   * Node.jsプロジェクトの処理
   */
  private async handleNodejsProject(
    sourcePath: string,
    name: string
  ): Promise<void> {
    const packageJsonPath = path.join(sourcePath, "package.json");
    if (!fs.existsSync(packageJsonPath)) {
      return;
    }

    // 依存関係をインストール
    await this.installNodeDependencies(sourcePath, name);
    
    // TypeScriptプロジェクトの場合はビルド
    await this.buildTypeScriptProject(sourcePath, name);
  }

  /**
   * Node.jsの依存関係をインストール
   */
  private async installNodeDependencies(
    sourcePath: string,
    name: string
  ): Promise<void> {
    pulumi.log.info(`Installing dependencies for ${name}`);
    
    // package-lock.jsonの存在を確認
    const packageLockPath = path.join(sourcePath, "package-lock.json");
    const hasPackageLock = fs.existsSync(packageLockPath);
    
    try {
      if (hasPackageLock) {
        // package-lock.jsonがある場合はnpm ciを使用
        pulumi.log.info(`Running npm ci --omit=dev in ${sourcePath}`);
        const result = await execAsync("npm ci --omit=dev", { cwd: sourcePath });
        if (result.stderr) {
          pulumi.log.warn(`npm ci stderr: ${result.stderr}`);
        }
      } else {
        // package-lock.jsonがない場合はnpm installを使用
        pulumi.log.info(`No package-lock.json found, running npm install --omit=dev in ${sourcePath}`);
        const result = await execAsync("npm install --omit=dev", { cwd: sourcePath });
        if (result.stderr) {
          pulumi.log.warn(`npm install stderr: ${result.stderr}`);
        }
      }
    } catch (e: any) {
      pulumi.log.error(`Failed to install dependencies: ${e.message || e}`);
      if (e.stdout) {
        pulumi.log.error(`Install stdout: ${e.stdout}`);
      }
      if (e.stderr) {
        pulumi.log.error(`Install stderr: ${e.stderr}`);
      }
      throw new Error(`Failed to install dependencies: ${e.message || e}`);
    }
  }

  /**
   * TypeScriptプロジェクトをビルド
   */
  private async buildTypeScriptProject(
    sourcePath: string,
    name: string
  ): Promise<void> {
    const tsConfigPath = path.join(sourcePath, "tsconfig.json");
    if (!fs.existsSync(tsConfigPath)) {
      return;
    }

    pulumi.log.info(`Building TypeScript project for ${name}`);
    
    try {
      // まず開発依存関係をインストール（TypeScriptコンパイラが必要）
      pulumi.log.info(`Installing dependencies in ${sourcePath}`);
      const installResult = await execAsync("npm install", { cwd: sourcePath });
      if (installResult.stderr) {
        pulumi.log.warn(`npm install stderr: ${installResult.stderr}`);
      }
      
      // package.jsonのスクリプトを確認
      const packageJsonPath = path.join(sourcePath, "package.json");
      if (fs.existsSync(packageJsonPath)) {
        const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, "utf-8"));
        pulumi.log.info(`Available scripts: ${JSON.stringify(packageJson.scripts)}`);
        
        // buildスクリプトが存在しない場合はスキップ
        if (!packageJson.scripts || !packageJson.scripts.build) {
          pulumi.log.warn(`No build script found in package.json, skipping TypeScript build`);
          return;
        }
      } else {
        pulumi.log.warn(`No package.json found in ${sourcePath}, skipping TypeScript build`);
        return;
      }
      
      // ビルドを実行
      pulumi.log.info(`Running npm run build in ${sourcePath}`);
      const buildResult = await execAsync("npm run build", { cwd: sourcePath });
      if (buildResult.stderr) {
        pulumi.log.warn(`npm run build stderr: ${buildResult.stderr}`);
      }
      if (buildResult.stdout) {
        pulumi.log.info(`npm run build stdout: ${buildResult.stdout}`);
      }
      pulumi.log.info(`TypeScript build completed for ${name}`);
      
      // ビルド結果を確認
      const distPath = path.join(sourcePath, "dist");
      if (fs.existsSync(distPath)) {
        const files = fs.readdirSync(distPath);
        pulumi.log.info(`Built files in dist/: ${files.join(", ")}`);
      } else {
        pulumi.log.warn(`No dist directory found after build`);
      }
    } catch (e: any) {
      // エラーの詳細情報をログ出力
      pulumi.log.error(`TypeScript build failed: ${e.message || e}`);
      if (e.stdout) {
        pulumi.log.error(`Build stdout: ${e.stdout}`);
      }
      if (e.stderr) {
        pulumi.log.error(`Build stderr: ${e.stderr}`);
      }
      if (e.code) {
        pulumi.log.error(`Build exit code: ${e.code}`);
      }
      throw new Error(`Failed to build TypeScript project: ${e.message || e}`);
    }
  }

  /**
   * Pythonプロジェクトの処理
   */
  private async handlePythonProject(
    sourcePath: string,
    name: string
  ): Promise<void> {
    const requirementsPath = path.join(sourcePath, "requirements.txt");
    if (!fs.existsSync(requirementsPath)) {
      return;
    }

    pulumi.log.info(`Installing Python dependencies for ${name}`);
    await execAsync(
      `pip install -r requirements.txt -t .`,
      { cwd: sourcePath }
    );
  }

  /**
   * ZIPアーカイブを作成
   */
  private async createZipArchive(
    outputPath: string,
    sourcePath: string,
    includePatterns: string[],
    excludePatterns: string[],
    extraFiles: { [key: string]: string }
  ): Promise<PackageResult> {
    return new Promise<PackageResult>((resolve, reject) => {
      const output = fs.createWriteStream(outputPath);
      const archive = archiver.create("zip", {
        zlib: { level: 9 },
      });

      output.on("close", () => {
        const result = this.getArchiveResult(outputPath);
        resolve(result);
      });

      archive.on("error", (err: Error) => {
        reject(err);
      });

      archive.pipe(output);

      // ファイルを追加
      this.addFilesToArchive(
        archive,
        sourcePath,
        includePatterns,
        excludePatterns,
        extraFiles
      );

      archive.finalize();
    });
  }

  /**
   * アーカイブにファイルを追加
   */
  private addFilesToArchive(
    archive: archiver.Archiver,
    sourcePath: string,
    includePatterns: string[],
    excludePatterns: string[],
    extraFiles: { [key: string]: string }
  ): void {
    // デフォルトの除外パターン
    const defaultExcludes = this.getDefaultExcludes();
    const allExcludes = [...defaultExcludes, ...excludePatterns];

    pulumi.log.info(`Adding files from ${sourcePath} with patterns: ${includePatterns.join(", ")}`);
    pulumi.log.info(`Exclude patterns: ${allExcludes.join(", ")}`);

    // ソースファイルを追加
    archive.glob(includePatterns.join(","), {
      cwd: sourcePath,
      ignore: allExcludes,
      dot: true,
    });

    // 追加ファイルを含める
    for (const [destPath, content] of Object.entries(extraFiles)) {
      pulumi.log.info(`Adding extra file: ${destPath}`);
      archive.append(content, { name: destPath });
    }
  }

  /**
   * デフォルトの除外パターンを取得
   */
  private getDefaultExcludes(): string[] {
    return [
      "*.zip",
      ".git/**",
      ".gitignore",
      ".env*",
      "*.test.js",
      "*.test.ts",
      "*.spec.js",
      "*.spec.ts",
      "__tests__/**",
      "test/**",
      "tests/**",
      "coverage/**",
      ".nyc_output/**",
      ".vscode/**",
      ".idea/**",
      "*.map",
      "tsconfig.json",
      "package-lock.json",
      "yarn.lock",
      // TypeScript関連の除外
      "src/**",       // srcディレクトリ全体を除外（TypeScriptソースコード）
      ".claude/**",   // Claudeの設定ディレクトリ
    ];
  }

  /**
   * アーカイブの結果を取得
   */
  private getArchiveResult(outputPath: string): PackageResult {
    const stats = fs.statSync(outputPath);
    const fileBuffer = fs.readFileSync(outputPath);
    const hashSum = crypto.createHash("sha256");
    hashSum.update(fileBuffer);
    const hex = hashSum.digest("hex");

    return {
      zipPath: outputPath,
      zipHash: hex,
      sizeBytes: stats.size,
    };
  }

  /**
   * Pulumiアセットとして作成
   */
  public createAsset(): pulumi.Output<pulumi.asset.FileArchive> {
    return this.zipPath.apply(p => new pulumi.asset.FileArchive(p));
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