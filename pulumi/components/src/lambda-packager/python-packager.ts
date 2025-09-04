import * as pulumi from "@pulumi/pulumi";
import * as fs from "fs";
import * as path from "path";
import { executeCommand } from "./utils";

/**
 * Pythonプロジェクト用パッケージャー
 * requirements.txtから依存関係をインストール
 */
export class PythonPackager {
  /**
   * Pythonプロジェクトを処理
   */
  async processProject(sourcePath: string, name: string): Promise<void> {
    const requirementsPath = path.join(sourcePath, "requirements.txt");
    
    // requirements.txtがない場合は処理不要
    if (!fs.existsSync(requirementsPath)) {
      pulumi.log.info(`No requirements.txt found, skipping Python processing for ${name}`);
      return;
    }

    await this.installDependencies(sourcePath, name);
  }

  /**
   * Python依存関係をインストール
   * Lambdaレイヤーと同じディレクトリ構造でインストール
   */
  private async installDependencies(
    sourcePath: string,
    name: string
  ): Promise<void> {
    pulumi.log.info(`Installing Python dependencies for ${name}`);
    
    // Lambda実行環境と同じディレクトリ構造でインストール
    // -t . オプションで現在のディレクトリに直接インストール
    await executeCommand(
      "pip install -r requirements.txt -t .",
      sourcePath,
      "Installing Python dependencies"
    );
    
    // インストール結果の確認
    this.verifyInstallation(sourcePath);
  }

  /**
   * インストール結果を確認
   */
  private verifyInstallation(sourcePath: string): void {
    // Pythonパッケージの一般的なマーカーファイルをチェック
    const markers = [
      "*.dist-info",
      "*.egg-info"
    ];
    
    const files = fs.readdirSync(sourcePath);
    const installedPackages = files.filter(file => 
      markers.some(marker => file.endsWith(marker.replace("*", "")))
    );
    
    if (installedPackages.length > 0) {
      pulumi.log.info(`Installed Python packages: ${installedPackages.length} packages found`);
    } else {
      pulumi.log.warn("No Python packages installation markers found");
    }
  }
}