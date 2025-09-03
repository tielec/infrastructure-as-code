import * as pulumi from "@pulumi/pulumi";

// パラメータタイプの定義
export type SSMParameterType = 'init-only' | 'managed';

// 拡張されたParameterArgs
export interface SSMParameterHelperArgs {
    /**
     * パラメータの管理タイプ
     * - init-only: 初期設定のみ。一度設定したら変更しない（セキュア情報等）
     * - managed: Pulumiで常に管理する
     */
    paramType: SSMParameterType;
    
    /**
     * パラメータの値
     */
    value: pulumi.Input<string>;
    
    /**
     * パラメータの説明
     */
    description?: string;
    
    /**
     * パラメータのタイプ（String, SecureString, StringList）
     * デフォルト: String
     */
    type?: pulumi.Input<'String' | 'SecureString' | 'StringList'>;
}