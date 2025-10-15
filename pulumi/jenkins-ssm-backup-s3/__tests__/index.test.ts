import * as fs from "fs";
import * as path from "path";
import * as pulumi from "@pulumi/pulumi";
import type { ConfigValue } from "@pulumi/pulumi/config";
import type { MockResourceArgs } from "@pulumi/pulumi/runtime";
import { mockCallerIdentity } from "./fixtures/mock_account";

type ConfigFixture = {
    projectName?: string;
    environment?: string;
    regions?: string[];
    defaultRegion?: string;
    ssmHomeRegion?: string;
};

type RecordedResource = {
    name: string;
    type: string;
    inputs: Record<string, any>;
    state: Record<string, any>;
};

const FIXTURE_DIR = path.resolve(__dirname, "fixtures");
const PROJECT_KEY = "jenkins-ssm-backup-s3";
const MOCK_ACCOUNT_ID = mockCallerIdentity.accountId;

let recordedResources: RecordedResource[] = [];

const loadFixture = (fileName: string): ConfigFixture => {
    const content = fs.readFileSync(path.join(FIXTURE_DIR, fileName), "utf-8");
    return JSON.parse(content) as ConfigFixture;
};

const toConfigMap = (fixture: ConfigFixture): Record<string, ConfigValue> => {
    const config: Record<string, ConfigValue> = {};
    if (fixture.projectName !== undefined) {
        config[`${PROJECT_KEY}:projectName`] = { value: fixture.projectName };
    }
    if (fixture.environment !== undefined) {
        config[`${PROJECT_KEY}:environment`] = { value: fixture.environment };
    }
    if (fixture.regions !== undefined) {
        config[`${PROJECT_KEY}:regions`] = { value: JSON.stringify(fixture.regions) };
    }
    if (fixture.defaultRegion !== undefined) {
        config[`${PROJECT_KEY}:defaultRegion`] = { value: fixture.defaultRegion };
    }
    if (fixture.ssmHomeRegion !== undefined) {
        config[`${PROJECT_KEY}:ssmHomeRegion`] = { value: fixture.ssmHomeRegion };
    }
    return config;
};

const bucketNameFor = (fixture: ConfigFixture, region: string): string => {
    return `${fixture.projectName}-ssm-backup-${fixture.environment}-${MOCK_ACCOUNT_ID}-${region}`;
};

const registerMocks = (fixture: ConfigFixture) => {
    recordedResources = [];
    const pulumiConfig = toConfigMap(fixture);
    const resolvedDefaultRegion = fixture.defaultRegion ?? fixture.regions?.[0] ?? "ap-northeast-1";

    pulumi.runtime.setMocks(
        {
            newResource: (args: MockResourceArgs) => {
                const state: Record<string, any> = { ...args.inputs };

                if (args.type === "pulumi:providers:aws") {
                    recordedResources.push({
                        name: args.name,
                        type: args.type,
                        inputs: args.inputs,
                        state,
                    });
                    return {
                        id: `${args.name}_id`,
                        state,
                    };
                }

                if (args.type === "aws:s3/bucket:Bucket") {
                    const regionTag =
                        (args.inputs?.tags && (args.inputs.tags.Region as string | undefined)) ?? resolvedDefaultRegion;
                    const bucketName = bucketNameFor(fixture, regionTag);
                    state.bucket = bucketName;
                    state.arn = `arn:aws:s3:::${bucketName}`;
                    state.region = regionTag;
                    state.versioning = args.inputs.versioning;
                    state.serverSideEncryptionConfiguration = args.inputs.serverSideEncryptionConfiguration;
                }

                if (args.type === "aws:s3/bucketPolicy:BucketPolicy") {
                    const regionTag =
                        (args.inputs?.tags && (args.inputs.tags.Region as string | undefined)) ?? resolvedDefaultRegion;
                    const bucketName = bucketNameFor(fixture, regionTag);
                    const bucketArn = `arn:aws:s3:::${bucketName}`;
                    state.bucket = args.inputs.bucket;
                    state.policy = JSON.stringify({
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
                    });
                }

                if (args.type === "aws:ssm/parameter:Parameter") {
                    const name = args.inputs.name as string;
                    state.name = name;

                    if (typeof args.inputs.value === "string") {
                        state.value = args.inputs.value;
                    } else if (name.endsWith("/s3-bucket-name")) {
                        const match = name.match(/backup\/([^/]+)\/s3-bucket-name$/);
                        const region = match ? match[1] : resolvedDefaultRegion;
                        state.value = bucketNameFor(fixture, region);
                    } else if (name.endsWith("/default-region")) {
                        state.value = resolvedDefaultRegion;
                    } else if (name.endsWith("/region-list")) {
                        state.value = JSON.stringify(fixture.regions ?? []);
                    } else {
                        state.value = "";
                    }
                }

                recordedResources.push({
                    name: args.name,
                    type: args.type,
                    inputs: args.inputs,
                    state,
                });

                return {
                    id: `${args.name}_id`,
                    state,
                };
            },
            call: (args) => {
                if (args.token === "aws:getCallerIdentity") {
                    return mockCallerIdentity;
                }
                return args.inputs;
            },
        },
        PROJECT_KEY,
        "test",
        false,
        pulumiConfig,
    );
};

const importStack = async <T>(fixture: ConfigFixture): Promise<T> => {
    registerMocks(fixture);
    jest.resetModules();
    return await import("../index") as T;
};

afterEach(() => {
    jest.resetModules();
});

describe("pulumi jenkins-ssm-backup-s3 stack", () => {
    // 異常系: リージョン未設定時は明示的な例外を投げること
    test("throws when regions are not configured", async () => {
        const fixture = loadFixture("config_no_regions.json");
        registerMocks(fixture);
        jest.resetModules();
        await expect(import("../index")).rejects.toThrow("No regions configured");
    });

    // 異常系: defaultRegion が regions に含まれない場合は失敗させること
    test("throws when defaultRegion is not part of regions", async () => {
        const fixture = loadFixture("config_invalid_default.json");
        registerMocks(fixture);
        jest.resetModules();
        await expect(import("../index")).rejects.toThrow("defaultRegion must be included in regions.");
    });

    // 正常系: 各リージョンで暗号化・公開遮断設定付きのバケットが生成されること
    test("creates regional S3 buckets with encryption and public access block", async () => {
        const fixture = loadFixture("regions_dual.json");
        await importStack<typeof import("../index")>(fixture);

        const buckets = recordedResources.filter(r => r.type === "aws:s3/bucket:Bucket");
        expect(buckets).toHaveLength(fixture.regions?.length ?? 0);

        for (const bucket of buckets) {
            expect(bucket.state.bucket).toMatch(
                new RegExp(`^${fixture.projectName}-ssm-backup-${fixture.environment}-${MOCK_ACCOUNT_ID}-[a-z0-9-]+$`),
            );

            expect(bucket.state.serverSideEncryptionConfiguration?.rule?.applyServerSideEncryptionByDefault?.sseAlgorithm).toBe(
                "AES256",
            );
            expect(bucket.state.versioning?.enabled).toBe(true);
        }

        const accessBlocks = recordedResources.filter(r => r.type === "aws:s3/bucketPublicAccessBlock:BucketPublicAccessBlock");
        expect(accessBlocks).toHaveLength(fixture.regions?.length ?? 0);
        accessBlocks.forEach(block => {
            expect(block.inputs.blockPublicAcls).toBe(true);
            expect(block.inputs.blockPublicPolicy).toBe(true);
            expect(block.inputs.ignorePublicAcls).toBe(true);
            expect(block.inputs.restrictPublicBuckets).toBe(true);
        });
    });

    // 正常系: リージョン別パラメータとレガシー互換パラメータが出力されること
    test("emits region-specific SSM parameters and legacy parameter for default region", async () => {
        const fixture = loadFixture("regions_dual.json");
        const stack = await importStack<typeof import("../index")>(fixture);
        const bucketMap = await stack.bucketMap;
        const defaultBucket = bucketMap[fixture.defaultRegion as string];

        const ssmParameters = recordedResources.filter(r => r.type === "aws:ssm/parameter:Parameter");

        const regionParameters = ssmParameters.filter(r =>
            String(r.state.name).includes(`/jenkins/${fixture.environment}/backup/`) &&
            String(r.state.name).endsWith("/s3-bucket-name"),
        );
        expect(regionParameters).toHaveLength(fixture.regions?.length ?? 0);
        regionParameters.forEach(param => {
            const regionMatch = String(param.state.name).match(/backup\/([^/]+)\/s3-bucket-name$/);
            const region = regionMatch ? regionMatch[1] : undefined;
            expect(region).toBeDefined();
            if (region) {
                expect(param.state.value).toBe(bucketMap[region]);
            }
        });

        const legacyParam = ssmParameters.find(r => r.state.name === `/jenkins/${fixture.environment}/backup/s3-bucket-name`);
        expect(legacyParam).toBeDefined();
        expect(legacyParam?.state.value).toBe(defaultBucket);
    });

    // 正常系: リージョン一覧とデフォルトリージョンのメタデータが SSM に登録されること
    test("publishes region metadata list and default region parameters", async () => {
        const fixture = loadFixture("regions_dual.json");
        await importStack<typeof import("../index")>(fixture);

        const ssmParameters = recordedResources.filter(r => r.type === "aws:ssm/parameter:Parameter");
        const regionListParam = ssmParameters.find(r => r.state.name === `/jenkins/${fixture.environment}/backup/region-list`);
        const defaultRegionParam = ssmParameters.find(
            r => r.state.name === `/jenkins/${fixture.environment}/backup/default-region`,
        );

        expect(regionListParam).toBeDefined();
        expect(defaultRegionParam).toBeDefined();

        const regionListValue = JSON.parse(regionListParam?.state.value ?? "[]");
        expect(regionListValue).toEqual(fixture.regions);
        expect(defaultRegionParam?.state.value).toBe(fixture.defaultRegion);
    });

    // 正常系: bucketMap エクスポートが全リージョンのバケット名を返すこと
    test("exports bucketMap containing all configured regions", async () => {
        const fixture = loadFixture("regions_triple.json");
        const stack = await importStack<typeof import("../index")>(fixture);
        const bucketMap = await stack.bucketMap;

        expect(Object.keys(bucketMap)).toEqual(fixture.regions);
        fixture.regions?.forEach(region => {
            expect(bucketMap[region]).toBe(bucketNameFor(fixture, region));
        });

        expect(await stack.bucketNameOutput).toBe(bucketNameFor(fixture, fixture.defaultRegion as string));
        expect(typeof (await stack.bucketArn)).toBe("string");
        expect((await stack.bucketArn)).toContain(bucketMap[fixture.defaultRegion as string]);
        expect(await stack.ssmBackupBucketParameter).toBeDefined();
    });
});
