import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";
import simpleGit from "simple-git";
import * as fs from "fs";
import * as path from "path";
import * as crypto from "crypto";

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

export class GitHubRepoCheckout extends pulumi.ComponentResource {
  public readonly localPath: pulumi.Output<string>;
  public readonly outputPath: pulumi.Output<string>;
  public readonly commitHash: pulumi.Output<string>;

  constructor(
    name: string,
    args: GitHubRepoCheckoutArgs,
    opts?: pulumi.ComponentResourceOptions
  ) {
    super("tielec:components:GitHubRepoCheckout", name, {}, opts);

    // Build repository URL
    const repositoryUrl = args.repositoryUrl || 
      (args.owner && args.repo ? `https://github.com/${args.owner}/${args.repo}.git` : null);
    
    if (!repositoryUrl) {
      throw new Error("Either repositoryUrl or owner/repo must be provided");
    }

    const repoHash = crypto
      .createHash("sha256")
      .update(repositoryUrl)
      .digest("hex")
      .substring(0, 8);

    const defaultOutputPath = path.join(
      process.cwd(),
      ".pulumi",
      "repos",
      `${name}-${repoHash}`
    );

    const outputPath = args.outputPath || defaultOutputPath;

    // Get GitHub token from SSM Parameter Store if not provided
    const useParameterStore = args.useParameterStore !== false; // default true
    let githubTokenOutput: pulumi.Output<string | undefined>;
    
    if (args.githubToken) {
      githubTokenOutput = pulumi.output(args.githubToken);
    } else if (useParameterStore) {
      const parameterNameInput = args.githubTokenParameterName || `/tielec-iac/GITHUB_TOKEN`;
      
      githubTokenOutput = pulumi.output(parameterNameInput).apply(async (paramName) => {
        try {
          const parameter = await aws.ssm.getParameter({
            name: paramName,
            withDecryption: true,
          }, { parent: this });
          return parameter.value;
        } catch (error) {
          pulumi.log.warn(`Failed to get GitHub token from SSM Parameter Store: ${error}`);
          return undefined;
        }
      });
    } else {
      githubTokenOutput = pulumi.output(undefined);
    }

    const checkoutPromise = pulumi.all([
      args.branch || "main",
      args.tag,
      args.commit,
      githubTokenOutput
    ]).apply(async ([branch, tag, commit, githubToken]) => {
      if (!fs.existsSync(outputPath)) {
        fs.mkdirSync(outputPath, { recursive: true });
      }

      const git = simpleGit();

      let repoUrl = repositoryUrl;
      if (githubToken && repoUrl.startsWith("https://github.com/")) {
        repoUrl = repoUrl.replace(
          "https://github.com/",
          `https://${githubToken}@github.com/`
        );
      }

      const isRepoCloned = fs.existsSync(path.join(outputPath, ".git"));

      if (!isRepoCloned) {
        // ブランチを指定してクローン
        await git.clone(repoUrl, outputPath, ["--branch", branch, "--depth", "1"]);
      }

      const repoGit = simpleGit(outputPath);

      if (isRepoCloned) {
        // 既存のリポジトリの場合、指定ブランチをフェッチ
        await repoGit.fetch(["origin", `${branch}:${branch}`, "--depth", "1"]);
      }

      let targetRef = branch;
      if (tag) {
        targetRef = tag;
        await repoGit.fetch(["--tags", "--depth", "1"]);
      } else if (commit) {
        targetRef = commit;
        await repoGit.fetch(["--depth", "1", "origin", commit]);
      }

      await repoGit.checkout(targetRef);

      if (!tag && !commit && branch) {
        try {
          await repoGit.pull("origin", branch);
        } catch (e) {
          pulumi.log.warn(`Failed to pull latest changes: ${e}`);
        }
      }

      const currentCommit = await repoGit.revparse("HEAD");

      return {
        localPath: outputPath,
        commitHash: currentCommit,
      };
    });

    this.localPath = pulumi.Output.create(checkoutPromise).apply(
      (result) => result.localPath
    );
    this.outputPath = this.localPath; // alias for backward compatibility
    this.commitHash = pulumi.Output.create(checkoutPromise).apply(
      (result) => result.commitHash
    );

    this.registerOutputs({
      localPath: this.localPath,
      outputPath: this.outputPath,
      commitHash: this.commitHash,
    });
  }
}