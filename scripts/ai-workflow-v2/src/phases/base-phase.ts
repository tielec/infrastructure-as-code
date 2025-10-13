import fs from 'fs-extra';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { MetadataManager } from '../core/metadata-manager.js';
import { ClaudeAgentClient } from '../core/claude-agent-client.js';
import { GitHubClient } from '../core/github-client.js';
import { ContentParser } from '../core/content-parser.js';
import { GitManager } from '../core/git-manager.js';
import { validatePhaseDependencies } from '../core/phase-dependencies.js';
import { PhaseExecutionResult, PhaseName, PhaseStatus } from '../types.js';

const moduleDir = path.dirname(fileURLToPath(import.meta.url));
const promptsRoot = path.resolve(moduleDir, '..', 'prompts');

export interface PhaseRunOptions {
  gitManager?: GitManager | null;
  skipReview?: boolean;
}

export type BasePhaseConstructorParams = {
  phaseName: PhaseName;
  workingDir: string;
  metadataManager: MetadataManager;
  claudeClient: ClaudeAgentClient;
  githubClient: GitHubClient;
  skipDependencyCheck?: boolean;
  ignoreDependencies?: boolean;
};

export type PhaseInitializationParams = Omit<BasePhaseConstructorParams, 'phaseName'>;

export abstract class BasePhase {
  protected readonly phaseName: PhaseName;
  protected readonly workingDir: string;
  protected readonly metadata: MetadataManager;
  protected readonly claude: ClaudeAgentClient;
  protected readonly github: GitHubClient;
  protected readonly skipDependencyCheck: boolean;
  protected readonly ignoreDependencies: boolean;
  protected readonly contentParser: ContentParser;

  protected readonly phaseDir: string;
  protected readonly outputDir: string;
  protected readonly executeDir: string;
  protected readonly reviewDir: string;
  protected readonly reviseDir: string;

  constructor(params: BasePhaseConstructorParams) {
    this.phaseName = params.phaseName;
    this.workingDir = params.workingDir;
    this.metadata = params.metadataManager;
    this.claude = params.claudeClient;
    this.github = params.githubClient;
    this.skipDependencyCheck = params.skipDependencyCheck ?? false;
    this.ignoreDependencies = params.ignoreDependencies ?? false;
    this.contentParser = new ContentParser();

    const phaseNumber = this.getPhaseNumber(this.phaseName);
    this.phaseDir = path.join(this.metadata.workflowDir, `${phaseNumber}_${this.phaseName}`);
    this.outputDir = path.join(this.phaseDir, 'output');
    this.executeDir = path.join(this.phaseDir, 'execute');
    this.reviewDir = path.join(this.phaseDir, 'review');
    this.reviseDir = path.join(this.phaseDir, 'revise');

    this.ensureDirectories();
  }

  protected abstract execute(): Promise<PhaseExecutionResult>;

  protected abstract review(): Promise<PhaseExecutionResult>;

  protected async shouldRunReview(): Promise<boolean> {
    return true;
  }

  public async run(options: PhaseRunOptions = {}): Promise<boolean> {
    const gitManager = options.gitManager ?? null;
    const issueNumber = parseInt(this.metadata.data.issue_number, 10);

    const dependencyResult = validatePhaseDependencies(this.phaseName, this.metadata, {
      skipCheck: this.skipDependencyCheck,
      ignoreViolations: this.ignoreDependencies,
    });

    if (!dependencyResult.valid) {
      const error =
        dependencyResult.error ??
        'Dependency validation failed. Use --skip-dependency-check to bypass.';
      console.error(`[ERROR] ${error}`);
      return false;
    }

    if (dependencyResult.warning) {
      console.warn(`[WARNING] ${dependencyResult.warning}`);
    }

    this.updatePhaseStatus('in_progress');
    await this.postProgress('in_progress', `${this.phaseName} フェーズを開始します。`);

    try {
      const executeResult = await this.execute();
      if (!executeResult.success) {
        await this.handleFailure(executeResult.error ?? 'Unknown execute error');
        return false;
      }

      let reviewResult: PhaseExecutionResult | null = null;
      if (!options.skipReview && (await this.shouldRunReview())) {
        reviewResult = await this.review();
        if (!reviewResult.success) {
          await this.handleFailure(reviewResult.error ?? 'Review failed');
          return false;
        }
      }

      this.updatePhaseStatus('completed');
      await this.postProgress('completed', `${this.phaseName} フェーズが完了しました。`);

      if (gitManager) {
        await this.autoCommitAndPush(gitManager, reviewResult?.output ?? null);
      }

      return true;
    } catch (error) {
      const message = (error as Error).message ?? String(error);
      await this.handleFailure(message);
      return false;
    }
  }

  protected loadPrompt(promptType: 'execute' | 'review' | 'revise'): string {
    const promptPath = path.join(promptsRoot, this.phaseName, `${promptType}.txt`);
    if (!fs.existsSync(promptPath)) {
      throw new Error(`Prompt file not found: ${promptPath}`);
    }
    return fs.readFileSync(promptPath, 'utf-8');
  }

  protected async executeWithClaude(prompt: string, options?: { maxTurns?: number; verbose?: boolean }) {
    return this.claude.executeTask({
      prompt,
      maxTurns: options?.maxTurns ?? 50,
      workingDirectory: this.workingDir,
      verbose: options?.verbose,
    });
  }

  protected getIssueInfo() {
    const issueNumber = parseInt(this.metadata.data.issue_number, 10);
    if (Number.isNaN(issueNumber)) {
      throw new Error('Invalid issue number in metadata.');
    }
    return this.github.getIssueInfo(issueNumber);
  }

  protected async postOutput(content: string, title: string) {
    const issueNumber = parseInt(this.metadata.data.issue_number, 10);
    await this.github.postComment(
      issueNumber,
      [`### ${title}`, '', '```markdown', content, '```', '', '*自動生成: AI Workflow*'].join(
        '\n',
      ),
    );
  }

  protected updatePhaseStatus(status: PhaseStatus, reviewResult?: string | null) {
    this.metadata.updatePhaseStatus(this.phaseName, status, { reviewResult: reviewResult ?? undefined });
  }

  protected getPhaseOutputFile(
    targetPhase: PhaseName,
    fileName: string,
    issueNumberOverride?: string | number,
  ): string | null {
    const workflowRoot = path.resolve(this.metadata.workflowDir, '..');
    const issueIdentifier =
      issueNumberOverride !== undefined ? String(issueNumberOverride) : this.metadata.data.issue_number;
    const phaseNumber = this.getPhaseNumber(targetPhase);
    const filePath = path.join(
      workflowRoot,
      `issue-${issueIdentifier}`,
      `${phaseNumber}_${targetPhase}`,
      'output',
      fileName,
    );

    if (!fs.existsSync(filePath)) {
      console.warn(`[WARNING] Output file not found for phase ${targetPhase}: ${filePath}`);
      return null;
    }

    return filePath;
  }

  protected formatIssueInfo(issueInfo: {
    number: number;
    title: string;
    state: string;
    url: string;
    labels: string[];
    body: string;
  }): string {
    const labels = issueInfo.labels?.length ? issueInfo.labels.join(', ') : 'なし';
    const body = issueInfo.body?.trim() ? issueInfo.body : '(本文なし)';

    return [
      '## Issue概要',
      '',
      `- **Issue番号**: #${issueInfo.number}`,
      `- **タイトル**: ${issueInfo.title}`,
      `- **状態**: ${issueInfo.state}`,
      `- **URL**: ${issueInfo.url}`,
      `- **ラベル**: ${labels}`,
      '',
      '### 本文',
      '',
      body,
    ].join('\n');
  }

  protected getPlanningDocumentReference(issueNumber: number): string {
    const planningFile = this.getPhaseOutputFile('planning', 'planning.md', issueNumber);

    if (!planningFile) {
      console.warn('[WARNING] Planning document not found.');
      return 'Planning Phaseは実行されていません';
    }

    const reference = this.getClaudeFileReference(planningFile);
    if (!reference) {
      console.warn(`[WARNING] Failed to resolve relative path for planning document: ${planningFile}`);
      return 'Planning Phaseは実行されていません';
    }

    console.info(`[INFO] Planning document reference: ${reference}`);
    return reference;
  }

  protected getClaudeFileReference(filePath: string): string | null {
    const absoluteFile = path.resolve(filePath);
    const workingDir = path.resolve(this.claude.getWorkingDirectory());
    const relative = path.relative(workingDir, absoluteFile);

    if (!relative || relative.startsWith('..') || path.isAbsolute(relative)) {
      return null;
    }

    const normalized = relative.split(path.sep).join('/');
    return `@${normalized}`;
  }

  private getPhaseNumber(phase: PhaseName): string {
    const mapping: Record<PhaseName, string> = {
      planning: '00',
      requirements: '01',
      design: '02',
      test_scenario: '03',
      implementation: '04',
      test_implementation: '05',
      testing: '06',
      documentation: '07',
      report: '08',
      evaluation: '09',
    };
    return mapping[phase];
  }

  private ensureDirectories() {
    fs.ensureDirSync(this.outputDir);
    fs.ensureDirSync(this.executeDir);
    fs.ensureDirSync(this.reviewDir);
    fs.ensureDirSync(this.reviseDir);
  }

  private async handleFailure(reason: string) {
    this.updatePhaseStatus('failed');
    await this.postProgress(
      'failed',
      `${this.phaseName} フェーズでエラーが発生しました: ${reason}`,
    );
  }

  private async postProgress(status: string, details: string) {
    const issueNumber = parseInt(this.metadata.data.issue_number, 10);
    if (Number.isNaN(issueNumber)) {
      return;
    }

    try {
      await this.github.postWorkflowProgress(issueNumber, this.phaseName, status, details);
    } catch (error) {
      const message = (error as Error).message ?? String(error);
      console.warn(`[WARNING] Failed to post workflow progress: ${message}`);
    }
  }

  private async autoCommitAndPush(gitManager: GitManager, reviewResult: string | null) {
    try {
      const commitResult = await gitManager.commitPhaseOutput(
        this.phaseName,
        'completed',
        reviewResult ?? undefined,
      );

      if (!commitResult.success) {
        console.warn(`[WARNING] Git commit failed: ${commitResult.error ?? 'unknown error'}`);
        return;
      }

      const pushResult = await gitManager.pushToRemote();
      if (!pushResult.success) {
        console.warn(`[WARNING] Git push failed: ${pushResult.error ?? 'unknown error'}`);
      }
    } catch (error) {
      const message = (error as Error).message ?? String(error);
      console.warn(`[WARNING] Auto commit & push failed: ${message}`);
    }
  }
}
