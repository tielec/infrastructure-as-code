/**
 * components/lambda-factory.ts
 * 
 * Lambda関数作成ファクトリー
 * Lambda関数とその関連リソースをシンプルに作成
 */
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

/**
 * Lambda関数を作成する簡単な関数
 * 
 * @param name - 関数の識別名（例: "main", "users", "products"）
 * @param projectName - プロジェクト名
 * @param environment - 環境名（dev, staging, prod）
 * @param config - Lambda関数の設定
 * @returns Lambda関数と関連リソース
 */
export function createLambdaFunction(
    name: string,
    projectName: pulumi.Output<string>,
    environment: string,
    config: {
        // 必須パラメータ
        role: aws.iam.Role;
        s3Bucket: pulumi.Output<string>;
        s3Key: pulumi.Output<string>;
        dlqArn: pulumi.Output<string>;
        vpcSubnetIds: pulumi.Output<string[]>;
        vpcSecurityGroupIds: pulumi.Output<string>[];
        
        // オプションパラメータ
        description?: string;
        handler?: string;
        runtime?: string;
        memorySize?: pulumi.Output<number>;
        timeout?: pulumi.Output<number>;
        environmentVariables?: { [key: string]: pulumi.Input<string> };
        logRetentionDays?: pulumi.Output<number>;
        tags?: { [key: string]: string };
    }
) {
    // デフォルト値
    const handler = config.handler || "dist/index.handler";
    const runtime = config.runtime || "nodejs20.x";
    const description = config.description || `${name} Lambda function`;
    
    // ========================================
    // 1. Lambda関数本体
    // ========================================
    const lambdaFunction = new aws.lambda.Function(`${name}-function`, {
        name: pulumi.interpolate`${projectName}-${name}-${environment}`,
        description: description,
        runtime: runtime,
        architectures: ["arm64"],
        handler: handler,
        role: config.role.arn,
        memorySize: config.memorySize,
        timeout: config.timeout,
        
        // S3からコードを取得
        s3Bucket: config.s3Bucket,
        s3Key: config.s3Key,
        
        // バージョン管理を有効化
        publish: true,
        
        // 環境変数
        environment: {
            variables: config.environmentVariables || {},
        },
        
        // VPC設定
        vpcConfig: {
            subnetIds: config.vpcSubnetIds,
            securityGroupIds: config.vpcSecurityGroupIds,
        },
        
        // DLQ設定
        deadLetterConfig: {
            targetArn: config.dlqArn,
        },
        
        tags: config.tags,
    });
    
    // ========================================
    // 2. エイリアス（環境別）
    // ========================================
    const alias = new aws.lambda.Alias(`${name}-alias`, {
        name: environment,
        functionName: lambdaFunction.name,
        functionVersion: lambdaFunction.version,
        description: `${name} alias for ${environment}`,
    });
    
    // ========================================
    // 3. CloudWatch Logsグループ
    // ========================================
    const logGroup = new aws.cloudwatch.LogGroup(`${name}-log-group`, {
        name: pulumi.interpolate`/aws/lambda/${lambdaFunction.name}`,
        retentionInDays: config.logRetentionDays,
        tags: config.tags,
    });
    
    // ========================================
    // 4. SSMパラメータ（他スタックから参照用）
    // ========================================
    const functionArnParam = new aws.ssm.Parameter(`${name}-function-arn-param`, {
        name: pulumi.interpolate`/${projectName}/${environment}/lambda/${name}-function-arn`,
        type: "String",
        value: lambdaFunction.arn,
        description: `${name} Lambda function ARN`,
        tags: config.tags,
    });
    
    const functionNameParam = new aws.ssm.Parameter(`${name}-function-name-param`, {
        name: pulumi.interpolate`/${projectName}/${environment}/lambda/${name}-function-name`,
        type: "String",
        value: lambdaFunction.name,
        description: `${name} Lambda function name`,
        tags: config.tags,
    });
    
    // 戻り値：必要なリソースのみを返す
    return {
        function: lambdaFunction,
        alias: alias,
        logGroup: logGroup,
        functionArnParam: functionArnParam,
        functionNameParam: functionNameParam,
    };
}