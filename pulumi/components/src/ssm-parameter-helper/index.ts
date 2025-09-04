/**
 * SSM Parameter Helper Component
 * 
 * SSMパラメータの作成を統一的に管理するヘルパーコンポーネント
 * パラメータタイプに応じて適切な設定（ignoreChanges, protect）を自動適用
 */

import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";
import { SSMParameterType, SSMParameterHelperArgs } from "./types";

/**
 * SSMパラメータヘルパークラス
 * 
 * 使用例:
 * ```typescript
 * const helper = new SSMParameterHelper('/my-app/dev', {
 *   Environment: 'dev',
 *   ManagedBy: 'pulumi',
 * });
 * 
 * const param = helper.createParameter('/database/password', {
 *   paramType: 'init-only',
 *   value: 'secret-value',
 *   type: 'SecureString',
 * });
 * ```
 */
export class SSMParameterHelper {
    private readonly paramPrefix: string;
    private readonly commonTags: Record<string, string>;
    private parameters: aws.ssm.Parameter[] = [];

    /**
     * @param paramPrefix パラメータ名のプレフィックス（例: /my-app/dev）
     * @param commonTags 全パラメータに適用する共通タグ
     */
    constructor(paramPrefix: string, commonTags: Record<string, string>) {
        this.paramPrefix = paramPrefix;
        this.commonTags = commonTags;
    }

    /**
     * SSMパラメータを作成
     * 
     * @param name パラメータ名（prefixからの相対パス）
     * @param args パラメータ設定
     * @returns 作成されたSSMパラメータ
     */
    createParameter(name: string, args: SSMParameterHelperArgs): aws.ssm.Parameter {
        // リソース名を生成（スラッシュを除去）
        const resourceName = name.replace(/\//g, "-").replace(/^-/, "");
        const fullName = `${this.paramPrefix}${name}`;
        
        // パラメータタイプに応じた設定
        let resourceOptions: pulumi.ResourceOptions = {};
        
        switch (args.paramType) {
            case 'init-only':
                // 初期設定のみ - 値の変更を完全に無視
                resourceOptions = {
                    ignoreChanges: ["value"],
                    protect: true,  // 削除保護
                };
                break;
                
            case 'managed':
                // Pulumiで管理 - 常に上書き
                resourceOptions = {};
                break;
        }
        
        // SSMパラメータ作成用の引数を構築
        const ssmArgs: aws.ssm.ParameterArgs = {
            name: fullName,
            value: args.value,
            type: args.type || 'String',
            description: args.description,
            tags: this.commonTags,
            // managedパラメータは常に最新値で上書き
            // init-onlyパラメータは初回作成のみ（既存があればエラー）
            overwrite: args.paramType === 'managed' ? true : undefined,
        };
        
        const param = new aws.ssm.Parameter(resourceName, ssmArgs, resourceOptions);
        
        this.parameters.push(param);
        return param;
    }

    /**
     * 作成された全パラメータを取得
     * 
     * @returns パラメータの配列
     */
    getParameters(): aws.ssm.Parameter[] {
        return this.parameters;
    }

    /**
     * 作成されたパラメータ数を取得
     * 
     * @returns パラメータ数
     */
    getParameterCount(): number {
        return this.parameters.length;
    }
}

/**
 * 単一のSSMパラメータを作成する関数
 * （SSMParameterHelperを使わない簡易版）
 * 
 * @param fullName パラメータのフルパス
 * @param args パラメータ設定
 * @param commonTags 共通タグ
 * @returns 作成されたSSMパラメータ
 */
export function createSSMParameter(
    fullName: string,
    args: SSMParameterHelperArgs,
    commonTags?: Record<string, string>
): aws.ssm.Parameter {
    // リソース名を生成（スラッシュを除去）
    const resourceName = fullName.replace(/\//g, "-").replace(/^-/, "");
    
    // パラメータタイプに応じた設定
    let resourceOptions: pulumi.ResourceOptions = {};
    
    switch (args.paramType) {
        case 'init-only':
            resourceOptions = {
                ignoreChanges: ["value"],
                protect: true,
            };
            break;
            
        case 'managed':
            resourceOptions = {};
            break;
    }
    
    // SSMパラメータ作成用の引数を構築
    const ssmArgs: aws.ssm.ParameterArgs = {
        name: fullName,
        value: args.value,
        type: args.type || 'String',
        description: args.description,
        tags: commonTags || {},
        // managedパラメータは常に最新値で上書き
        // init-onlyパラメータは初回作成のみ（既存があればエラー）
        overwrite: args.paramType === 'managed' ? true : undefined,
    };
    
    return new aws.ssm.Parameter(resourceName, ssmArgs, resourceOptions);
}

// 型エクスポート
export type { SSMParameterType, SSMParameterHelperArgs } from "./types";