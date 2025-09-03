import * as pulumi from "@pulumi/pulumi";

export interface GitHubRepoCheckoutArgs {
  // Either provide repositoryUrl or owner/repo
  repositoryUrl?: string;
  owner?: string;
  repo?: string;
  branch?: pulumi.Input<string>;
  tag?: pulumi.Input<string>;
  commit?: pulumi.Input<string>;
  outputPath?: string;
  githubToken?: pulumi.Input<string>;
  // SSM Parameter Store path for GitHub token (default: /tielec-iac/GITHUB_TOKEN)
  githubTokenParameterName?: pulumi.Input<string>;
  useParameterStore?: boolean; // default: true
}