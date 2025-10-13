import fs from 'fs-extra';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { MetadataManager } from '../core/metadata-manager.js';
import { ClaudeAgentClient } from '../core/claude-agent-client.js';
import { GitHubClient } from '../core/github-client.js';
import { ContentParser } from '../core/content-parser.js';
import { GitManager } from '../core/git-manager.js';
import { validatePhaseDependencies } from '../core/phase-dependencies.js';
import { PhaseExecutionResult, PhaseName, PhaseStatus, PhaseMetadata } from '../types.js';

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

  protected async executeWithClaude(
    prompt: string,
    options?: { maxTurns?: number; verbose?: boolean; logDir?: string },
  ) {
    const logDir = options?.logDir ?? this.executeDir;
    const promptFile = path.join(logDir, 'prompt.txt');
    const outputFile = path.join(logDir, 'output.json');
    const logFile = path.join(logDir, 'log.txt');

    // Save prompt
    fs.writeFileSync(promptFile, prompt, 'utf-8');
    console.info(`[INFO] Prompt saved to: ${promptFile}`);

    const startTime = Date.now();
    let messages: string[] = [];
    let error: Error | null = null;

    try {
      messages = await this.claude.executeTask({
        prompt,
        maxTurns: options?.maxTurns ?? 50,
        workingDirectory: this.workingDir,
        verbose: options?.verbose,
      });
    } catch (e) {
      error = e as Error;
    }

    const endTime = Date.now();
    const duration = endTime - startTime;

    // Save output
    fs.writeFileSync(outputFile, JSON.stringify(messages, null, 2), 'utf-8');
    console.info(`[INFO] Output saved to: ${outputFile}`);

    // Save log
    const logContent = [
      `Execution Log`,
      `=============`,
      `Start Time: ${new Date(startTime).toISOString()}`,
      `End Time: ${new Date(endTime).toISOString()}`,
      `Duration: ${duration}ms`,
      `Max Turns: ${options?.maxTurns ?? 50}`,
      `Messages Count: ${messages.length}`,
      `Status: ${error ? 'FAILED' : 'SUCCESS'}`,
      error ? `Error: ${error.message}` : '',
    ]
      .filter(Boolean)
      .join('\n');

    fs.writeFileSync(logFile, logContent, 'utf-8');
    console.info(`[INFO] Log saved to: ${logFile}`);

    if (error) {
      throw error;
    }

    return messages;
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

  private async postProgress(status: PhaseStatus, details?: string) {
    const issueNumber = parseInt(this.metadata.data.issue_number, 10);
    if (Number.isNaN(issueNumber)) {
      return;
    }

    try {
      const content = this.formatProgressComment(status, details);
      await this.github.createOrUpdateProgressComment(
        issueNumber,
        content,
        this.metadata,
      );
    } catch (error) {
      const message = (error as Error).message ?? String(error);
      console.warn(`[WARNING] Failed to post workflow progress: ${message}`);
    }
  }

  private formatProgressComment(status: PhaseStatus, details?: string): string {
    const statusEmoji: Record<string, string> = {
      pending: '⏸️',
      in_progress: '🔄',
      completed: '✅',
      failed: '❌',
    };

    const phaseDefinitions: Array<{ key: PhaseName; number: string; label: string }> = [
      { key: 'planning', number: 'Phase 0', label: 'Planning' },
      { key: 'requirements', number: 'Phase 1', label: 'Requirements' },
      { key: 'design', number: 'Phase 2', label: 'Design' },
      { key: 'test_scenario', number: 'Phase 3', label: 'Test Scenario' },
      { key: 'implementation', number: 'Phase 4', label: 'Implementation' },
      { key: 'test_implementation', number: 'Phase 5', label: 'Test Implementation' },
      { key: 'testing', number: 'Phase 6', label: 'Testing' },
      { key: 'documentation', number: 'Phase 7', label: 'Documentation' },
      { key: 'report', number: 'Phase 8', label: 'Report' },
      { key: 'evaluation', number: 'Phase 9', label: 'Evaluation' },
    ];

    const phasesStatus = this.metadata.getAllPhasesStatus();
    phasesStatus[this.phaseName] = status;
    const parts: string[] = [];

    parts.push('## 🤖 AI Workflow - 進捗状況\n\n');
    parts.push('### 全体進捗\n\n');

    const completedDetails: Array<{
      number: string;
      label: string;
      data: PhaseMetadata | undefined;
    }> = [];
    let currentPhaseInfo:
      | {
          number: string;
          label: string;
          status: PhaseStatus;
          data: PhaseMetadata | undefined;
        }
      | null = null;

    for (const definition of phaseDefinitions) {
      const phaseStatus = phasesStatus[definition.key] ?? 'pending';
      const emoji = statusEmoji[phaseStatus] ?? '📝';
      const phaseData = this.metadata.data.phases[definition.key];

      let line = `- ${emoji} ${definition.number}: ${definition.label} - **${phaseStatus.toUpperCase()}**`;
      if (phaseStatus === 'completed' && phaseData?.completed_at) {
        line += ` (${phaseData.completed_at})`;
      } else if (phaseStatus === 'in_progress' && phaseData?.started_at) {
        line += ` (開始: ${phaseData.started_at})`;
      }

      parts.push(`${line}\n`);

      if (phaseStatus === 'completed') {
        completedDetails.push({
          number: definition.number,
          label: definition.label,
          data: phaseData,
        });
      }

      if (definition.key === this.phaseName) {
        currentPhaseInfo = {
          number: definition.number,
          label: definition.label,
          status: phaseStatus,
          data: phaseData,
        };
      }
    }

    if (currentPhaseInfo) {
      parts.push(
        `\n### 現在のフェーズ: ${currentPhaseInfo.number} (${currentPhaseInfo.label})\n\n`,
      );
      parts.push(`**ステータス**: ${currentPhaseInfo.status.toUpperCase()}\n`);

      const phaseData = currentPhaseInfo.data;
      if (phaseData?.started_at) {
        parts.push(`**開始時刻**: ${phaseData.started_at}\n`);
      }

      const retryCount = phaseData?.retry_count ?? 0;
      parts.push(`**試行回数**: ${retryCount + 1}/3\n`);

      if (details) {
        parts.push(`\n${details}\n`);
      }
    }

    if (completedDetails.length) {
      parts.push('\n<details>\n');
      parts.push('<summary>完了したフェーズの詳細</summary>\n\n');

      for (const info of completedDetails) {
        parts.push(`### ${info.number}: ${info.label}\n\n`);
        parts.push('**ステータス**: COMPLETED\n');

        const data = info.data;
        if (data?.review_result) {
          parts.push(`**レビュー結果**: ${data.review_result}\n`);
        }
        if (data?.completed_at) {
          parts.push(`**完了時刻**: ${data.completed_at}\n`);
        }

        parts.push('\n');
      }

      parts.push('</details>\n');
    }

    const now = new Date();
    const pad = (value: number) => value.toString().padStart(2, '0');
    const formattedNow = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(
      now.getHours(),
    )}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;

    parts.push('\n---\n');
    parts.push(`*最終更新: ${formattedNow}*\n`);
    parts.push('*AI駆動開発自動化ワークフロー (Claude Agent SDK)*\n');

    return parts.join('');
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
