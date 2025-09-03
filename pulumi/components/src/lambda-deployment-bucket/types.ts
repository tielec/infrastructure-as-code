import * as pulumi from "@pulumi/pulumi";

export interface LambdaDeploymentBucketArgs {
  bucketName?: pulumi.Input<string>;
  lifecycleDays?: pulumi.Input<number>;
  versioning?: pulumi.Input<boolean>;
  tags?: pulumi.Input<{ [key: string]: string }>;
  /**
   * If true, references an existing bucket instead of creating a new one
   */
  useExisting?: boolean;
}