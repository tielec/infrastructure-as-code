// pulumi/test-s3/index.ts
/**
 * Minimal Pulumi project for testing
 * Creates a simple S3 bucket with basic configuration
 */
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

// Get configuration
const config = new pulumi.Config();
const projectName = config.get("projectName") || "test";
const environment = pulumi.getStack();

// Create a simple S3 bucket
const bucket = new aws.s3.Bucket(`${projectName}-bucket`, {
    bucket: `${projectName}-${environment}-${Date.now()}`, // Unique bucket name
    acl: "private",
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
    tags: {
        Name: `${projectName}-bucket-${environment}`,
        Environment: environment,
        ManagedBy: "pulumi",
        Purpose: "testing",
    },
});

// Block public access
const bucketPublicAccessBlock = new aws.s3.BucketPublicAccessBlock(`${projectName}-bucket-pab`, {
    bucket: bucket.id,
    blockPublicAcls: true,
    blockPublicPolicy: true,
    ignorePublicAcls: true,
    restrictPublicBuckets: true,
});

// Create a test object in the bucket
const testObject = new aws.s3.BucketObject(`${projectName}-test-object`, {
    bucket: bucket.id,
    key: "test/hello.txt",
    content: `Hello from Pulumi! Environment: ${environment}`,
    contentType: "text/plain",
    tags: {
        Environment: environment,
        CreatedAt: new Date().toISOString(),
    },
});

// Export the bucket name and ARN
export const bucketName = bucket.bucket;
export const bucketArn = bucket.arn;
export const bucketDomainName = bucket.bucketDomainName;
export const testObjectKey = testObject.key;
