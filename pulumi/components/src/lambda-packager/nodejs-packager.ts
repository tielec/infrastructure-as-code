import * as pulumi from "@pulumi/pulumi";
import * as fs from "fs";
import * as path from "path";
import { executeCommand, readPackageJson } from "./utils";
import { BuildConfig } from "./types";

/**
 * Node.js/TypeScriptプロジェクト用パッケージャー
 * 依存関係のインストールとTypeScriptのビルドを担当
 */
export class NodejsPackager {
  /**
   * Node.jsプロジェクトを処理
   */
  async processProject(sourcePath: string, name: string): Promise<void> {
    const packageJsonPath = path.join(sourcePath, "package.json");
    
    // package.jsonがない場合は処理不要（単純なJavaScriptファイル）
    if (!fs.existsSync(packageJsonPath)) {
      pulumi.log.info(`No package.json found, skipping Node.js processing for ${name}`);
      return;
    }

    // 1. 依存関係をインストール
    await this.installProductionDependencies(sourcePath, name);
    
    // 2. TypeScriptプロジェクトの場合はビルド
    const buildConfig = this.detectBuildConfig(sourcePath);
    if (buildConfig.needsBuild) {
      await this.buildProject(sourcePath, name, buildConfig);
    }
  }

  /**
   * 本番用の依存関係をインストール
   */
  private async installProductionDependencies(
    sourcePath: string,
    name: string
  ): Promise<void> {
    pulumi.log.info(`Installing production dependencies for ${name}`);
    
    const hasPackageLock = fs.existsSync(path.join(sourcePath, "package-lock.json"));
    
    if (hasPackageLock) {
      // package-lock.jsonがある場合は高速で確実なnpm ciを使用
      await executeCommand(
        "npm ci --omit=dev",
        sourcePath,
        "Installing dependencies with npm ci"
      );
    } else {
      // package-lock.jsonがない場合は通常のインストール
      await executeCommand(
        "npm install --omit=dev",
        sourcePath,
        "Installing dependencies with npm install"
      );
    }
  }

  /**
   * ビルド設定を検出
   */
  private detectBuildConfig(sourcePath: string): BuildConfig {
    // TypeScriptプロジェクトかチェック
    const hasTsConfig = fs.existsSync(path.join(sourcePath, "tsconfig.json"));
    if (!hasTsConfig) {
      return { needsBuild: false };
    }

    // package.jsonのbuildスクリプトをチェック
    const packageJson = readPackageJson(path.join(sourcePath, "package.json"));
    const hasBuildScript = packageJson?.scripts?.build !== undefined;
    
    if (!hasBuildScript) {
      pulumi.log.warn("TypeScript project detected but no build script found");
      return { needsBuild: false };
    }

    return {
      needsBuild: true,
      buildCommand: "npm run build",
      outputDirectory: "dist",
      needsDevDependencies: true
    };
  }

  /**
   * TypeScriptプロジェクトをビルド
   */
  private async buildProject(
    sourcePath: string,
    name: string,
    buildConfig: BuildConfig
  ): Promise<void> {
    pulumi.log.info(`Building TypeScript project for ${name}`);

    // ビルドには開発依存関係（TypeScriptコンパイラ等）が必要
    if (buildConfig.needsDevDependencies) {
      await executeCommand(
        "npm install",
        sourcePath,
        "Installing all dependencies including devDependencies"
      );
    }

    // ビルド実行
    if (buildConfig.buildCommand) {
      await executeCommand(
        buildConfig.buildCommand,
        sourcePath,
        "Building TypeScript project"
      );
    }

    // ビルド結果を確認
    if (buildConfig.outputDirectory) {
      this.verifyBuildOutput(sourcePath, buildConfig.outputDirectory);
    }
  }

  /**
   * ビルド出力を確認
   */
  private verifyBuildOutput(sourcePath: string, outputDir: string): void {
    const outputPath = path.join(sourcePath, outputDir);
    
    if (fs.existsSync(outputPath)) {
      const files = fs.readdirSync(outputPath);
      pulumi.log.info(`Build output found in ${outputDir}/: ${files.join(", ")}`);
    } else {
      pulumi.log.warn(`Expected build output directory ${outputDir}/ not found`);
    }
  }
}