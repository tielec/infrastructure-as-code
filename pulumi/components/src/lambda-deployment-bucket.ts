import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

export interface LambdaDeploymentBucketArgs {
  bucketName?: pulumi.Input<string>;
  lifecycleDays?: pulumi.Input<number>;
  versioning?: pulumi.Input<boolean>;
  tags?: pulumi.Input<{ [key: string]: string }>;
  /**
   * If true, references an existing bucket instead of creating a new one
   */
  useExisting?: boolean;
}

export class LambdaDeploymentBucket extends pulumi.ComponentResource {
  public readonly bucket?: aws.s3.Bucket;
  public readonly bucketName: pulumi.Output<string>;
  public readonly bucketArn: pulumi.Output<string>;

  constructor(
    name: string,
    args?: LambdaDeploymentBucketArgs,
    opts?: pulumi.ComponentResourceOptions
  ) {
    super("tielec:components:LambdaDeploymentBucket", name, {}, opts);

    const useExisting = args?.useExisting !== false; // Default to true

    if (useExisting) {
      // Reference existing bucket
      if (!args?.bucketName) {
        throw new Error("bucketName is required when useExisting is true (default)");
      }
      
      this.bucketName = pulumi.output(args.bucketName);
      this.bucketArn = this.bucketName.apply(name => `arn:aws:s3:::${name}`);
    } else {
      // Create new bucket
      const defaultTags = {
        Purpose: "Lambda-Deployment",
        ManagedBy: "Pulumi",
      };

      const tags = {
        ...defaultTags,
        ...(args?.tags || {}),
      };

      const bucketName = args?.bucketName || `tielec-lambda-shipment-${name}`;

      this.bucket = new aws.s3.Bucket(
        `${name}-bucket`,
        {
          bucket: bucketName,
          acl: "private",
          versioning: {
            enabled: args?.versioning !== false,
          },
          serverSideEncryptionConfiguration: {
            rule: {
              applyServerSideEncryptionByDefault: {
                sseAlgorithm: "AES256",
              },
            },
          },
          lifecycleRules: [
            {
              enabled: true,
              id: "delete-old-versions",
              noncurrentVersionExpiration: {
                days: args?.lifecycleDays || 7,
              },
            },
            {
              enabled: true,
              id: "delete-incomplete-uploads",
              abortIncompleteMultipartUploadDays: 7,
            },
          ],
          tags,
        },
        { parent: this }
      );

      const bucketPublicAccessBlock = new aws.s3.BucketPublicAccessBlock(
        `${name}-public-access-block`,
        {
          bucket: this.bucket.id,
          blockPublicAcls: true,
          blockPublicPolicy: true,
          ignorePublicAcls: true,
          restrictPublicBuckets: true,
        },
        { parent: this }
      );

      this.bucketName = this.bucket.bucket;
      this.bucketArn = this.bucket.arn;
    }

    this.registerOutputs({
      bucketName: this.bucketName,
      bucketArn: this.bucketArn,
    });
  }

  public uploadLambdaPackage(
    name: string,
    zipPath: pulumi.Input<string>,
    zipHash: pulumi.Input<string>,
    metadata?: pulumi.Input<{ [key: string]: pulumi.Input<string> }>,
    options?: {
      retainOnDelete?: boolean;  // デフォルトはtrue（古いファイルを保持）
    }
  ): aws.s3.BucketObject {
    // 簡潔なタイムスタンプ形式（YYYYMMDD-HHmmss）
    const now = new Date();
    const timestamp = now.toISOString()
      .replace(/[T:]/g, '-')
      .replace(/\.\d{3}Z$/, '')
      .replace(/-/g, '')
      .slice(0, 8) + '-' + 
      now.toISOString()
      .replace(/[T:]/g, '')
      .replace(/\.\d{3}Z$/, '')
      .slice(9, 15);
    
    // ハッシュの最初の8文字のみ使用（衝突は実質的に問題なし）
    const shortHash = pulumi.output(zipHash).apply(h => h.substring(0, 8));
    
    const key = pulumi.interpolate`lambda-packages/${name}/${timestamp}-${shortHash}.zip`;

    // デフォルトで古いファイルを保持
    const retainOnDelete = options?.retainOnDelete ?? true;

    // retainOnDeleteがtrueの場合は動的な名前、falseの場合は固定名
    if (retainOnDelete) {
      // ハッシュが確定してから動的な名前でリソースを作成
      return pulumi.output(zipHash).apply(hash => {
        const shortHashStr = hash.substring(0, 8);
        return new aws.s3.BucketObject(
          `${name}-package-${shortHashStr}`,
          {
            bucket: this.bucketName,
            key,
            source: pulumi.output(zipPath).apply(p => new pulumi.asset.FileAsset(p)),
            contentType: "application/zip",
            metadata: pulumi
              .all([metadata, zipHash])
              .apply(([meta, fullHash]) => ({
                ...meta,
                "package-hash": fullHash,
                "upload-time": timestamp,
              })),
          },
          { parent: this, retainOnDelete: retainOnDelete }
        );
      }) as any as aws.s3.BucketObject;
    } else {
      // 固定名でリソースを作成（削除時に置き換える）
      return new aws.s3.BucketObject(
        `${name}-package`,
        {
          bucket: this.bucketName,
          key,
          source: pulumi.output(zipPath).apply(p => new pulumi.asset.FileAsset(p)),
          contentType: "application/zip",
          metadata: pulumi
            .all([metadata, zipHash])
            .apply(([meta, hash]) => ({
              ...meta,
              "package-hash": hash,
              "upload-time": timestamp,
            })),
        },
        { parent: this, retainOnDelete: retainOnDelete }
      );
    }
  }
}