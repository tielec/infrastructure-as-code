import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

type RegionalResources = {
    region: string;
    bucket: aws.s3.Bucket;
    publicAccessBlock: aws.s3.BucketPublicAccessBlock;
    bucketPolicy: aws.s3.BucketPolicy;
    ssmParameter: aws.ssm.Parameter;
};

const config = new pulumi.Config();
const projectName = config.require("projectName");
const environment = config.require("environment");
const configuredRegions = config.requireObject<string[]>("regions");
const defaultRegion = config.require("defaultRegion");
const ssmHomeRegion = config.get("ssmHomeRegion") || defaultRegion;

const regions = Array.from(new Set(configuredRegions));
if (regions.length === 0) {
    throw new Error("No regions configured. Please set 'regions' in Pulumi config.");
}

if (!regions.includes(defaultRegion)) {
    throw new Error("defaultRegion must be included in regions.");
}

const callerIdentity = pulumi.output(aws.getCallerIdentity({}));
const accountId = callerIdentity.apply(identity => identity.accountId);

const ssmProvider = createRegionProvider("ssm-home", ssmHomeRegion);

const regionalResources: Record<string, RegionalResources> = {};
for (const region of regions) {
    const provider = createRegionProvider(`region-${region}`, region);
    regionalResources[region] = createRegionalResources({
        region,
        accountId,
        environment,
        projectName,
        provider,
        ssmProvider,
    });
}

const defaultRegionResources = regionalResources[defaultRegion];
if (!defaultRegionResources) {
    throw new Error(`Failed to locate resources for default region '${defaultRegion}'.`);
}

const legacyParameter = emitLegacyParameter({
    environment,
    bucketName: defaultRegionResources.bucket.bucket,
    provider: ssmProvider,
});

emitRegionMetadata({
    regions,
    defaultRegion,
    environment,
    provider: ssmProvider,
});

export const bucketMap = pulumi
    .all(
        Object.values(regionalResources).map(res =>
            res.bucket.bucket.apply(bucketName => ({
                region: res.region,
                bucketName,
            })),
        ),
    )
    .apply(entries =>
        entries.reduce<Record<string, string>>((acc, entry) => {
            acc[entry.region] = entry.bucketName;
            return acc;
        }, {}),
    );

export const bucketNameOutput = defaultRegionResources.bucket.bucket;
export const bucketArn = defaultRegionResources.bucket.arn;
export const ssmBackupBucketParameter = legacyParameter.name;

interface RegionalResourceArgs {
    region: string;
    accountId: pulumi.Output<string>;
    environment: string;
    projectName: string;
    provider: aws.Provider;
    ssmProvider: aws.Provider | undefined;
}

function createRegionalResources(args: RegionalResourceArgs): RegionalResources {
    const { region, accountId, environment, projectName, provider, ssmProvider } = args;

    const bucketName = pulumi.interpolate`${projectName}-ssm-backup-${environment}-${accountId}-${region}`;

    const bucket = new aws.s3.Bucket(
        `ssm-backup-bucket-${region}`,
        {
            bucket: bucketName,
            versioning: {
                enabled: true,
            },
            serverSideEncryptionConfiguration: {
                rule: {
                    applyServerSideEncryptionByDefault: {
                        sseAlgorithm: "AES256",
                    },
                    bucketKeyEnabled: true,
                },
            },
            lifecycleRules: [
                {
                    id: "delete-old-backups",
                    enabled: true,
                    expiration: {
                        days: 30,
                    },
                    noncurrentVersionExpiration: {
                        days: 7,
                    },
                },
            ],
            objectLockEnabled: false,
            tags: {
                Name: bucketName,
                Environment: environment,
                ManagedBy: "Pulumi",
                Purpose: "SSM Parameter Store Backup Storage",
                DataClassification: "Confidential",
                Region: region,
            },
        },
        {
            provider,
        },
    );

    const publicAccessBlock = new aws.s3.BucketPublicAccessBlock(
        `ssm-backup-bucket-pab-${region}`,
        {
            bucket: bucket.id,
            blockPublicAcls: true,
            blockPublicPolicy: true,
            ignorePublicAcls: true,
            restrictPublicBuckets: true,
        },
        {
            provider,
        },
    );

    const bucketPolicy = new aws.s3.BucketPolicy(
        `ssm-backup-bucket-policy-${region}`,
        {
            bucket: bucket.id,
            policy: pulumi
                .all([bucket.arn])
                .apply(([bucketArn]) =>
                    JSON.stringify({
                        Version: "2012-10-17",
                        Statement: [
                            {
                                Sid: "DenyInsecureConnections",
                                Effect: "Deny",
                                Principal: "*",
                                Action: "s3:*",
                                Resource: [bucketArn, `${bucketArn}/*`],
                                Condition: {
                                    Bool: {
                                        "aws:SecureTransport": "false",
                                    },
                                },
                            },
                            {
                                Sid: "DenyUnencryptedObjectUploads",
                                Effect: "Deny",
                                Principal: "*",
                                Action: "s3:PutObject",
                                Resource: `${bucketArn}/*`,
                                Condition: {
                                    StringNotEquals: {
                                        "s3:x-amz-server-side-encryption": "AES256",
                                    },
                                },
                            },
                        ],
                    }),
                ),
        },
        {
            provider,
        },
    );

    const parameter = new aws.ssm.Parameter(
        `ssm-backup-bucket-name-${region}`,
        {
            name: `/jenkins/${environment}/backup/${region}/s3-bucket-name`,
            type: "String",
            value: bucket.bucket,
            description: `SSM Parameter Store backup S3 bucket for ${region}`,
            tags: {
                Environment: environment,
                ManagedBy: "Pulumi",
                Region: region,
            },
        },
        ssmProvider ? { provider: ssmProvider } : undefined,
    );

    return {
        region,
        bucket,
        publicAccessBlock,
        bucketPolicy,
        ssmParameter: parameter,
    };
}

interface EmitLegacyParameterArgs {
    environment: string;
    bucketName: pulumi.Output<string>;
    provider: aws.Provider | undefined;
}

function emitLegacyParameter(args: EmitLegacyParameterArgs): aws.ssm.Parameter {
    const { environment, bucketName, provider } = args;

    return new aws.ssm.Parameter(
        "ssm-backup-bucket-name-legacy",
        {
            name: `/jenkins/${environment}/backup/s3-bucket-name`,
            type: "String",
            value: bucketName,
            description: "Legacy default region SSM backup bucket name",
            tags: {
                Environment: environment,
                ManagedBy: "Pulumi",
                Region: "legacy",
            },
        },
        provider ? { provider } : undefined,
    );
}

interface EmitRegionMetadataArgs {
    regions: string[];
    defaultRegion: string;
    environment: string;
    provider: aws.Provider | undefined;
}

function emitRegionMetadata(args: EmitRegionMetadataArgs): void {
    const { regions, defaultRegion, environment, provider } = args;
    const providerOptions = provider ? { provider } : undefined;

    new aws.ssm.Parameter(
        "ssm-backup-region-list",
        {
            name: `/jenkins/${environment}/backup/region-list`,
            type: "String",
            value: JSON.stringify(regions),
            description: "JSON encoded list of backup target regions",
            tags: {
                Environment: environment,
                ManagedBy: "Pulumi",
            },
        },
        providerOptions,
    );

    new aws.ssm.Parameter(
        "ssm-backup-default-region",
        {
            name: `/jenkins/${environment}/backup/default-region`,
            type: "String",
            value: defaultRegion,
            description: "Default region for legacy integrations",
            tags: {
                Environment: environment,
                ManagedBy: "Pulumi",
            },
        },
        providerOptions,
    );
}

function createRegionProvider(name: string, region: string): aws.Provider {
    return new aws.Provider(name, { region });
}
