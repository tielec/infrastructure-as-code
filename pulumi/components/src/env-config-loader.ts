import * as fs from "fs";
import * as path from "path";
import * as yaml from "js-yaml";
import * as pulumi from "@pulumi/pulumi";

export interface EnvConfig {
  [key: string]: any;
}

/**
 * SharePointからダウンロードしたYAML設定ファイルを読み込むためのローダー
 */
export class EnvConfigLoader {
  private config: EnvConfig = {};
  private environment: string;

  constructor(environment: string) {
    this.environment = environment;
  }

  /**
   * YAMLファイルを読み込む
   * @param filePath YAMLファイルのパス（相対パスまたは絶対パス）
   */
  loadYamlFile(filePath: string): EnvConfigLoader {
    try {
      const resolvedPath = path.resolve(filePath);
      
      if (!fs.existsSync(resolvedPath)) {
        throw new Error(`Configuration file not found: ${resolvedPath}`);
      }

      const fileContents = fs.readFileSync(resolvedPath, "utf8");
      const yamlConfig = yaml.load(fileContents) as EnvConfig;
      
      // マージ（後から読み込んだファイルが優先される）
      this.config = { ...this.config, ...yamlConfig };
      
      pulumi.log.info(`Loaded configuration from: ${resolvedPath}`);
      
      return this;
    } catch (error) {
      throw new Error(`Failed to load YAML configuration from ${filePath}: ${error}`);
    }
  }

  /**
   * 複数のYAMLファイルを順番に読み込む
   * @param filePaths YAMLファイルのパスの配列
   */
  loadYamlFiles(filePaths: string[]): EnvConfigLoader {
    for (const filePath of filePaths) {
      this.loadYamlFile(filePath);
    }
    return this;
  }

  /**
   * 設定値を取得
   * @param key ドット記法によるキー（例: "vpc.subnetIds"）
   * @param defaultValue デフォルト値
   */
  get(key: string, defaultValue?: any): any {
    const keys = key.split(".");
    let value: any = this.config;

    for (const k of keys) {
      if (value && typeof value === "object" && k in value) {
        value = value[k];
      } else {
        return defaultValue;
      }
    }

    return value;
  }

  /**
   * 設定値を文字列として取得
   */
  getString(key: string, defaultValue?: string): string {
    const value = this.get(key, defaultValue);
    return value != null ? String(value) : (defaultValue ?? "");
  }

  /**
   * 設定値を数値として取得
   */
  getNumber(key: string, defaultValue?: number): number {
    const value = this.get(key, defaultValue);
    return typeof value === "number" ? value : Number(value);
  }

  /**
   * 設定値をブール値として取得
   */
  getBoolean(key: string, defaultValue?: boolean): boolean {
    const value = this.get(key, defaultValue);
    return typeof value === "boolean" ? value : value === "true";
  }

  /**
   * 設定値を配列として取得（カンマ区切り文字列にも対応）
   */
  getArray(key: string, defaultValue?: string[]): string[] {
    const value = this.get(key, defaultValue);
    
    if (Array.isArray(value)) {
      return value;
    }
    
    if (typeof value === "string") {
      // カンマ区切り文字列を配列に変換
      return value.split(",").map(s => s.trim());
    }
    
    return defaultValue ?? [];
  }

  /**
   * 設定値をPulumi Secretとして取得
   */
  getSecret(key: string, defaultValue?: string): pulumi.Output<string> {
    const value = this.getString(key, defaultValue);
    return pulumi.secret(value);
  }

  /**
   * すべての設定を取得
   */
  getAll(): EnvConfig {
    return this.config;
  }

  /**
   * 現在の環境を取得
   */
  getEnvironment(): string {
    return this.environment;
  }
}

/**
 * 標準的な環境設定ファイルパスから設定を読み込むヘルパー関数
 * @param environment 環境名（dev, staging, prod など）
 * @param baseDir 設定ファイルのベースディレクトリ（デフォルト: env/）
 */
export function loadEnvConfig(
  environment: string,
  baseDir: string = "env"
): EnvConfigLoader {
  const loader = new EnvConfigLoader(environment);
  
  // 標準的なファイル名パターンで読み込みを試みる
  const possibleFiles = [
    path.join(baseDir, `${environment}.yml`),
    path.join(baseDir, `${environment}.yaml`),
    path.join(baseDir, `${environment}.json`),
  ];

  for (const file of possibleFiles) {
    if (fs.existsSync(file)) {
      loader.loadYamlFile(file);
      break;
    }
  }

  return loader;
}