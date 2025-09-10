/**
 * pulumi/lambda-nat/index.ts
 * 
 * Lambda APIインフラのNATリソースを構築するPulumiスクリプト
 * ハイアベイラビリティモード: NAT Gateway（2つ）
 * ノーマルモード: NAT Instance（1つ）- Amazon Linux 2023 + nftables使用
 * SSMパラメータストアから設定を取得し、条件に応じて適切なNATリソースを作成
 */
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";
import { createNatGateway, NatGatewayOutputs } from "./components/nat-gateway";
import { createNatInstance, NatInstanceOutputs } from "./components/nat-instance";

// ========================================
// 環境変数取得
// ========================================
const environment = pulumi.getStack();

// ========================================
// SSMパラメータ参照（Single Source of Truth）
// ========================================
// プロジェクト名を取得
const projectNameParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/common/project-name`,
});
const projectName = pulumi.output(projectNameParam).apply(p => p.value);

// NAT設定を取得
const natHighAvailabilityParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/nat/high-availability`,
});
const highAvailabilityMode = pulumi.output(natHighAvailabilityParam).apply(p => p.value === "true");

const natInstanceTypeParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/nat/instance-type`,
});
const natInstanceType = pulumi.output(natInstanceTypeParam).apply(p => p.value || "t4g.nano");

// ネットワーク情報を取得
const vpcIdParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/network/vpc-id`,
});
const vpcCidrParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/network/vpc-cidr`,
});
const publicSubnetAIdParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/network/subnets/public-a-id`,
});
const publicSubnetBIdParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/network/subnets/public-b-id`,
});
const privateRouteTableAIdParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/network/route-tables/private-a-id`,
});
const privateRouteTableBIdParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/network/route-tables/private-b-id`,
});

const vpcId = pulumi.output(vpcIdParam).apply(p => p.value);
const vpcCidr = pulumi.output(vpcCidrParam).apply(p => p.value);
const publicSubnetAId = pulumi.output(publicSubnetAIdParam).apply(p => p.value);
const publicSubnetBId = pulumi.output(publicSubnetBIdParam).apply(p => p.value);
const privateRouteTableAId = pulumi.output(privateRouteTableAIdParam).apply(p => p.value);
const privateRouteTableBId = pulumi.output(privateRouteTableBIdParam).apply(p => p.value);

// セキュリティ情報を取得（NAT Instance用）
const natInstanceSecurityGroupIdParam = aws.ssm.getParameter({
    name: `/lambda-api/${environment}/security/nat-instance-sg-id`,
});
const natInstanceSecurityGroupId = pulumi.output(natInstanceSecurityGroupIdParam).apply(p => p.value);

// ========================================
// 共通タグ定義
// ========================================
const commonTags = {
    Environment: environment,
    ManagedBy: "pulumi",
    Project: "lambda-api",
    Stack: pulumi.getProject(),
};

// ========================================
// NATリソースの条件付き作成
// ========================================
// 高可用性モードに応じてNATリソースを作成
// Pulumiの条件付きリソース作成パターンを使用
let natInstanceAutoStopSchedule: pulumi.Output<string> | undefined;

highAvailabilityMode.apply(isHA => {
    if (isHA) {
        // ========================================
        // 高可用性モード: NAT Gateway（2つ）
        // ========================================
        pulumi.log.info("Creating NAT Gateway resources for high-availability mode");
        
        createNatGateway({
            projectName,
            environment,
            publicSubnetAId,
            publicSubnetBId,
            privateRouteTableAId,
            privateRouteTableBId,
            commonTags,
        });
    } else {
        // ========================================
        // 通常モード: NAT Instance（1つ）
        // ========================================
        pulumi.log.info("Creating NAT Instance resources for normal mode");
        
        const natInstanceOutputs = createNatInstance({
            projectName,
            environment,
            vpcCidr,
            natInstanceType,
            publicSubnetAId,
            privateRouteTableAId,
            privateRouteTableBId,
            natInstanceSecurityGroupId,
            commonTags,
        });
        
        // 自動停止スケジュール情報を保存（dev環境のみ）
        natInstanceAutoStopSchedule = natInstanceOutputs.autoStopSchedule;
    }
});


// ========================================
// エクスポート（表示用のみ）
// ========================================
// エクスポートは表示・確認用のみ
// 他のスタックはSSMパラメータから値を取得すること
export const outputs = {
    stack: "lambda-nat",
    environment: environment,
    natType: highAvailabilityMode.apply(ha => ha ? "gateway-ha" : "instance"),
    ssmParameterPrefix: pulumi.interpolate`/${projectName}/${environment}/nat`,
    autoStopSchedule: natInstanceAutoStopSchedule || pulumi.output("N/A - Auto-stop only available for NAT Instance in dev environment"),
};

// デバッグ情報をログに出力
pulumi.log.info("NAT configuration deployment starting...");
highAvailabilityMode.apply(isHA => {
    pulumi.log.info(`Mode: ${isHA ? "High Availability (NAT Gateway)" : "Normal (NAT Instance)"}`);
    if (!isHA) {
        natInstanceType.apply(type => {
            pulumi.log.info(`NAT Instance Type: ${type}`);
        });
    }
});