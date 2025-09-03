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

    const packagePromise = pulumi.all([
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
      const sourceHash = crypto
        .createHash("sha256")
        .update(sourcePath)
        .digest("hex")
        .substring(0, 8);

      const defaultOutputPath = path.join(
        process.cwd(),
        ".pulumi",
        "lambdas",
        `${name}-${sourceHash}.zip`
      );

      const outputPath = args.outputPath || defaultOutputPath;
      const outputDir = path.dirname(outputPath);

      if (!fs.existsSync(outputDir)) {
        fs.mkdirSync(outputDir, { recursive: true });
      }

      if (installDependencies && runtime.startsWith("nodejs")) {
        const packageJsonPath = path.join(sourcePath, "package.json");
        if (fs.existsSync(packageJsonPath)) {
          pulumi.log.info(`Installing dependencies for ${name}`);
          try {
            await execAsync("npm ci --production", { cwd: sourcePath });
          } catch (e) {
            pulumi.log.warn(`npm ci failed, trying npm install: ${e}`);
            await execAsync("npm install --production", { cwd: sourcePath });
          }
        }
      } else if (installDependencies && runtime.startsWith("python")) {
        const requirementsPath = path.join(sourcePath, "requirements.txt");
        if (fs.existsSync(requirementsPath)) {
          pulumi.log.info(`Installing Python dependencies for ${name}`);
          await execAsync(
            `pip install -r requirements.txt -t .`,
            { cwd: sourcePath }
          );
        }
      }

      return new Promise<{
        zipPath: string;
        zipHash: string;
        sizeBytes: number;
      }>((resolve, reject) => {
        const output = fs.createWriteStream(outputPath);
        const archive = archiver.create("zip", {
          zlib: { level: 9 },
        });

        output.on("close", () => {
          const stats = fs.statSync(outputPath);
          const fileBuffer = fs.readFileSync(outputPath);
          const hashSum = crypto.createHash("sha256");
          hashSum.update(fileBuffer);
          const hex = hashSum.digest("hex");

          resolve({
            zipPath: outputPath,
            zipHash: hex,
            sizeBytes: stats.size,
          });
        });

        archive.on("error", (err: Error) => {
          reject(err);
        });

        archive.pipe(output);

        const defaultExcludes = [
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
        ];

        const allExcludes = [...defaultExcludes, ...excludePatterns];

        archive.glob(includePatterns.join(","), {
          cwd: sourcePath,
          ignore: allExcludes,
          dot: true,
        });

        for (const [destPath, content] of Object.entries(extraFiles)) {
          archive.append(content, { name: destPath });
        }

        archive.finalize();
      });
    });

    this.zipPath = pulumi.Output.create(packagePromise).apply(
      (result) => result.zipPath
    );
    this.zipHash = pulumi.Output.create(packagePromise).apply(
      (result) => result.zipHash
    );
    this.sizeBytes = pulumi.Output.create(packagePromise).apply(
      (result) => result.sizeBytes
    );

    this.registerOutputs({
      zipPath: this.zipPath,
      zipHash: this.zipHash,
      sizeBytes: this.sizeBytes,
    });
  }

  public createAsset(): pulumi.Output<pulumi.asset.FileArchive> {
    return this.zipPath.apply(p => new pulumi.asset.FileArchive(p));
  }

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