import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

// 設定値の取得
const config = new pulumi.Config();
const projectName = config.require("projectName");
const environment = config.require("environment");

// S3バケット名の生成
const bucketName = `${projectName}-ssm-backup-${environment}`;

// SSMパラメータバックアップ用S3バケット
const backupBucket = new aws.s3.Bucket("ssm-backup-bucket", {
    bucket: bucketName,
    versioning: {
        enabled: true,
    },
    serverSideEncryptionConfiguration: {
        rule: {
            applyServerSideEncryptionByDefault: {
                sseAlgorithm: "AES256",
            },
        },
    },
    lifecycleRules: [{
        id: "delete-old-backups",
        enabled: true,
        expiration: {
            days: 30,  // 30日間保持
        },
        noncurrentVersionExpiration: {
            days: 7,  // 非現行バージョンは7日間保持
        },
    }],
    tags: {
        Name: bucketName,
        Environment: environment,
        Purpose: "SSM Parameter Store Backup Storage",
        ManagedBy: "Pulumi",
    },
});

// バケットのパブリックアクセスブロック設定
const bucketPublicAccessBlock = new aws.s3.BucketPublicAccessBlock("ssm-backup-bucket-pab", {
    bucket: backupBucket.id,
    blockPublicAcls: true,
    blockPublicPolicy: true,
    ignorePublicAcls: true,
    restrictPublicBuckets: true,
});

// SSMパラメータストアにバケット名を保存
const ssmBackupBucketName = new aws.ssm.Parameter("ssm-backup-bucket-name", {
    name: `/jenkins/${environment}/backup/s3-bucket-name`,
    type: "String",
    value: backupBucket.bucket,
    description: "SSM Parameter Store backup S3 bucket name",
    tags: {
        Environment: environment,
        ManagedBy: "Pulumi",
    },
});

// エクスポート
export const bucketNameOutput = backupBucket.bucket;
export const bucketArn = backupBucket.arn;
export const ssmBackupBucketParameter = ssmBackupBucketName.name;