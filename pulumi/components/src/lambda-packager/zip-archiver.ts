import * as pulumi from "@pulumi/pulumi";
import * as fs from "fs";
import * as archiver from "archiver";
import { PackageResult } from "./types";
import { DEFAULT_EXCLUDE_PATTERNS, ZIP_COMPRESSION_LEVEL } from "./constants";
import { calculateFileHash } from "./utils";

/**
 * ZIPアーカイブ作成を担当するクラス
 * ファイルの収集、除外パターンの適用、ZIP圧縮を処理
 */
export class ZipArchiver {
  /**
   * ZIPアーカイブを作成
   */
  async createArchive(
    outputPath: string,
    sourcePath: string,
    includePatterns: string[],
    excludePatterns: string[],
    extraFiles: { [key: string]: string }
  ): Promise<PackageResult> {
    return new Promise<PackageResult>((resolve, reject) => {
      const output = fs.createWriteStream(outputPath);
      const archive = this.setupArchive();

      // イベントハンドラの設定
      output.on("close", () => {
        const result = this.createPackageResult(outputPath);
        resolve(result);
      });

      archive.on("error", (err: Error) => {
        pulumi.log.error(`Archive creation failed: ${err.message}`);
        reject(err);
      });

      archive.on("warning", (warning: Error) => {
        pulumi.log.warn(`Archive warning: ${warning.message}`);
      });

      // アーカイブ処理の実行
      archive.pipe(output);
      this.addFiles(archive, sourcePath, includePatterns, excludePatterns);
      this.addExtraFiles(archive, extraFiles);
      archive.finalize();
    });
  }

  /**
   * アーカイブの設定
   */
  private setupArchive(): archiver.Archiver {
    return archiver.create("zip", {
      zlib: { level: ZIP_COMPRESSION_LEVEL }
    });
  }

  /**
   * ソースディレクトリからファイルを追加
   */
  private addFiles(
    archive: archiver.Archiver,
    sourcePath: string,
    includePatterns: string[],
    excludePatterns: string[]
  ): void {
    const allExcludes = this.mergeExcludePatterns(excludePatterns);
    
    pulumi.log.info(`Adding files from ${sourcePath}`);
    pulumi.log.info(`Include patterns: ${includePatterns.join(", ")}`);
    pulumi.log.info(`Exclude patterns: ${allExcludes.join(", ")}`);

    // globパターンを使用してファイルを追加
    archive.glob(includePatterns.join(","), {
      cwd: sourcePath,
      ignore: allExcludes,
      dot: true,  // ドットファイルも含める
    });
  }

  /**
   * 追加ファイルをアーカイブに含める
   */
  private addExtraFiles(
    archive: archiver.Archiver,
    extraFiles: { [key: string]: string }
  ): void {
    for (const [destPath, content] of Object.entries(extraFiles)) {
      pulumi.log.info(`Adding extra file: ${destPath}`);
      archive.append(content, { name: destPath });
    }
  }

  /**
   * デフォルトとユーザー指定の除外パターンをマージ
   */
  private mergeExcludePatterns(userPatterns: string[]): string[] {
    return [...DEFAULT_EXCLUDE_PATTERNS, ...userPatterns];
  }

  /**
   * パッケージ結果を作成
   */
  private createPackageResult(zipPath: string): PackageResult {
    const stats = fs.statSync(zipPath);
    const hash = calculateFileHash(zipPath);

    pulumi.log.info(`Archive created: ${zipPath} (${stats.size} bytes, hash: ${hash})`);

    return {
      zipPath,
      zipHash: hash,
      sizeBytes: stats.size,
    };
  }
}