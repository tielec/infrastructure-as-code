import * as pulumi from "@pulumi/pulumi";

// 依存関係を正しく指定するためのヘルパー関数
export function dependsOn<T extends pulumi.Resource>(
    resource: T, 
    dependencies: pulumi.Resource[] | undefined
): T {
    if (dependencies && dependencies.length > 0) {
        // 依存関係を確立するために、Pulumi の内部的な依存グラフを使用する
        for (const dependency of dependencies) {
            resource.urn.apply(_ => {
                return dependency.urn.apply(_ => {
                    // ここでは何もしない。単に依存関係を作成するだけ
                    return undefined;
                });
            });
        }
    }
    return resource;
}
