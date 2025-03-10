import * as pulumi from "@pulumi/pulumi";

// 依存関係を正しく指定するためのヘルパー関数
export function dependsOn<T extends pulumi.Resource>(
    resource: T, 
    dependencies: pulumi.Resource[] | undefined
): T {
    if (dependencies && dependencies.length > 0) {
        (<any>resource).__logicalName = resource.__logicalName;
        resource.urn.apply(urn => { /* 空の適用で依存関係を確立 */ });
        
        // それぞれの依存リソースについて明示的な依存関係を追加
        for (const dependency of dependencies) {
            resource.urn.apply(_ => dependency.urn.apply(_ => { /* 依存性を確立 */ }));
        }
    }
    return resource;
}
