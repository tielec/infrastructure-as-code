import * as pulumi from "@pulumi/pulumi";
import * as fs from "fs";
import * as path from "path";
import * as crypto from "crypto";
import { promisify } from "util";
import { exec } from "child_process";
import { RuntimeType, PackageJson } from "./types";

export const execAsync = promisify(exec);

/**
 * ランタイム文字列から言語種別を判定
 */
export function getRuntimeType(runtime: string): RuntimeType {
  if (runtime.startsWith("nodejs")) {
    return "nodejs";
  } else if (runtime.startsWith("python")) {
    return "python";
  }
  return "unknown";
}

/**
 * package.jsonを安全に読み込み
 */
export function readPackageJson(packageJsonPath: string): PackageJson | null {
  try {
    if (!fs.existsSync(packageJsonPath)) {
      return null;
    }
    const content = fs.readFileSync(packageJsonPath, "utf-8");
    return JSON.parse(content) as PackageJson;
  } catch (error) {
    pulumi.log.warn(`Failed to read package.json: ${error}`);
    return null;
  }
}

/**
 * ファイルのSHA256ハッシュを計算
 */
export function calculateFileHash(filePath: string): string {
  const fileBuffer = fs.readFileSync(filePath);
  const hashSum = crypto.createHash("sha256");
  hashSum.update(fileBuffer);
  return hashSum.digest("hex");
}

/**
 * ディレクトリを安全に作成（既存の場合はスキップ）
 */
export function ensureDirectory(dirPath: string): void {
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
  }
}

/**
 * コマンド実行のラッパー（詳細なログ出力付き）
 */
export async function executeCommand(
  command: string,
  cwd: string,
  description: string
): Promise<void> {
  pulumi.log.info(`${description}: ${command} in ${cwd}`);
  
  try {
    const result = await execAsync(command, { cwd });
    
    if (result.stdout) {
      pulumi.log.info(`stdout: ${result.stdout}`);
    }
    if (result.stderr) {
      pulumi.log.warn(`stderr: ${result.stderr}`);
    }
  } catch (error: any) {
    pulumi.log.error(`Command failed: ${error.message || error}`);
    
    if (error.stdout) {
      pulumi.log.error(`stdout: ${error.stdout}`);
    }
    if (error.stderr) {
      pulumi.log.error(`stderr: ${error.stderr}`);
    }
    if (error.code) {
      pulumi.log.error(`exit code: ${error.code}`);
    }
    
    throw new Error(`${description} failed: ${error.message || error}`);
  }
}

/**
 * パスからユニークなハッシュを生成（キャッシュキー用）
 */
export function generatePathHash(inputPath: string): string {
  return crypto
    .createHash("sha256")
    .update(inputPath)
    .digest("hex")
    .substring(0, 8);
}

/**
 * Lambda ZIPファイルの出力パスを生成
 */
export function generateOutputPath(
  name: string,
  outputPath: string | undefined,
  sourcePath: string
): string {
  if (outputPath) {
    return outputPath;
  }

  const sourceHash = generatePathHash(sourcePath);
  return path.join(
    process.cwd(),
    ".pulumi",
    "lambdas",
    `${name}-${sourceHash}.zip`
  );
}