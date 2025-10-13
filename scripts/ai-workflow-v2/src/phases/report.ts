import fs from 'fs-extra';
import path from 'node:path';
import { BasePhase, type PhaseInitializationParams } from './base-phase.js';
import { PhaseExecutionResult } from '../types.js';

type PhaseOutputInfo = {
  path: string;
  exists: boolean;
};

type PhaseOutputMap = Record<string, PhaseOutputInfo>;

export class ReportPhase extends BasePhase {
  constructor(params: PhaseInitializationParams) {
    super({ ...params, phaseName: 'report' });
  }

  protected async execute(): Promise<PhaseExecutionResult> {
    const issueNumber = parseInt(this.metadata.data.issue_number, 10);
    const outputs = this.getPhaseOutputs(issueNumber);

    const requiredPhases = [
      'requirements',
      'design',
      'test_scenario',
      'implementation',
      'test_result',
      'documentation',
    ];

    for (const phase of requiredPhases) {
      if (!outputs[phase]?.exists) {
        return {
          success: false,
          error: `${phase} の成果物が見つかりません: ${outputs[phase]?.path ?? 'N/A'}`,
        };
      }
    }

    const planningReference = this.getPlanningDocumentReference(issueNumber);
    const replacements: Record<string, string> = {
      requirements_document_path: this.requireReference(outputs, 'requirements'),
      design_document_path: this.requireReference(outputs, 'design'),
      test_scenario_document_path: this.requireReference(outputs, 'test_scenario'),
      implementation_document_path: this.requireReference(outputs, 'implementation'),
      test_implementation_document_path: this.optionalReference(outputs, 'test_implementation'),
      test_result_document_path: this.requireReference(outputs, 'test_result'),
      documentation_update_log_path: this.requireReference(outputs, 'documentation'),
    };

    const executePrompt = Object.entries(replacements).reduce(
      (acc, [key, value]) => acc.replace(`{${key}}`, value),
      this.loadPrompt('execute')
        .replace('{planning_document_path}', planningReference)
        .replace('{issue_number}', String(issueNumber)),
    );

    await this.executeWithClaude(executePrompt, { maxTurns: 30 });

    const reportFile = path.join(this.outputDir, 'report.md');
    if (!fs.existsSync(reportFile)) {
      return {
        success: false,
        error: `report.md が見つかりません: ${reportFile}`,
      };
    }

    try {
      const content = fs.readFileSync(reportFile, 'utf-8');
      await this.postOutput(content, '最終レポート');
    } catch (error) {
      const message = (error as Error).message ?? String(error);
      console.warn(`[WARNING] GitHub へのレポート投稿に失敗しました: ${message}`);
    }

    await this.updatePullRequestSummary(issueNumber, outputs);

    return {
      success: true,
      output: reportFile,
    };
  }

  protected async review(): Promise<PhaseExecutionResult> {
    const issueNumber = parseInt(this.metadata.data.issue_number, 10);
    const reportFile = path.join(this.outputDir, 'report.md');

    if (!fs.existsSync(reportFile)) {
      return {
        success: false,
        error: 'report.md が存在しません。execute() を先に実行してください。',
      };
    }

    const outputs = this.getPhaseOutputs(issueNumber);
    const reviewPrompt = this.buildPrompt('review', issueNumber, reportFile, outputs);

    const messages = await this.executeWithClaude(reviewPrompt, { maxTurns: 30, logDir: this.reviewDir });
    const reviewResult = await this.contentParser.parseReviewResult(messages);

    const reviewFile = path.join(this.reviewDir, 'result.md');
    fs.writeFileSync(reviewFile, reviewResult.feedback, 'utf-8');

    await this.github.postReviewResult(
      issueNumber,
      this.phaseName,
      reviewResult.result,
      reviewResult.feedback,
      reviewResult.suggestions,
    );

    return {
      success: reviewResult.result !== 'FAIL',
      output: reviewResult.result,
      error: reviewResult.result === 'FAIL' ? reviewResult.feedback : undefined,
    };
  }

  public async revise(reviewFeedback: string): Promise<PhaseExecutionResult> {
    const issueNumber = parseInt(this.metadata.data.issue_number, 10);
    const reportFile = path.join(this.outputDir, 'report.md');

    if (!fs.existsSync(reportFile)) {
      return {
        success: false,
        error: 'report.md が存在しません。execute() を先に実行してください。',
      };
    }

    const outputs = this.getPhaseOutputs(issueNumber);
    const revisePrompt = this.buildPrompt('revise', issueNumber, reportFile, outputs).replace(
      '{review_feedback}',
      reviewFeedback,
    );

    await this.executeWithClaude(revisePrompt, { maxTurns: 30, logDir: this.reviseDir });

    if (!fs.existsSync(reportFile)) {
      return {
        success: false,
        error: '改訂後の report.md を確認できませんでした。',
      };
    }

    return {
      success: true,
      output: reportFile,
    };
  }

  private buildPrompt(
    promptType: 'review' | 'revise',
    issueNumber: number,
    reportPath: string,
    outputs: PhaseOutputMap,
  ): string {
    const basePrompt = this.loadPrompt(promptType)
      .replace('{report_document_path}', this.requireReferencePath(reportPath))
      .replace('{issue_number}', String(issueNumber));

    const replacements: Record<string, string> = {
      requirements_document_path: this.optionalReference(outputs, 'requirements'),
      design_document_path: this.optionalReference(outputs, 'design'),
      test_scenario_document_path: this.optionalReference(outputs, 'test_scenario'),
      implementation_document_path: this.optionalReference(outputs, 'implementation'),
      test_implementation_document_path: this.optionalReference(outputs, 'test_implementation'),
      test_result_document_path: this.optionalReference(outputs, 'test_result'),
      documentation_update_log_path: this.optionalReference(outputs, 'documentation'),
    };

    return Object.entries(replacements).reduce(
      (acc, [key, value]) => acc.replace(`{${key}}`, value),
      basePrompt,
    );
  }

  private getPhaseOutputs(issueNumber: number): PhaseOutputMap {
    const baseDir = path.resolve(this.metadata.workflowDir, '..', `issue-${issueNumber}`);

    const entries: Record<string, string> = {
      requirements: path.join(baseDir, '01_requirements', 'output', 'requirements.md'),
      design: path.join(baseDir, '02_design', 'output', 'design.md'),
      test_scenario: path.join(baseDir, '03_test_scenario', 'output', 'test-scenario.md'),
      implementation: path.join(baseDir, '04_implementation', 'output', 'implementation.md'),
      test_implementation: path.join(
        baseDir,
        '05_test_implementation',
        'output',
        'test-implementation.md',
      ),
      test_result: path.join(baseDir, '06_testing', 'output', 'test-result.md'),
      documentation: path.join(
        baseDir,
        '07_documentation',
        'output',
        'documentation-update-log.md',
      ),
    };

    return Object.fromEntries(
      Object.entries(entries).map(([phase, filePath]) => [
        phase,
        {
          path: filePath,
          exists: fs.existsSync(filePath),
        },
      ]),
    );
  }

  private requireReference(outputs: PhaseOutputMap, key: string): string {
    const info = outputs[key];
    if (!info?.exists) {
      throw new Error(`Required phase output missing: ${key}`);
    }

    const reference = this.getClaudeFileReference(info.path);
    if (!reference) {
      throw new Error(`Failed to compute reference for ${info.path}`);
    }
    return reference;
  }

  private optionalReference(outputs: PhaseOutputMap, key: string): string {
    const info = outputs[key];
    if (!info?.exists) {
      return '';
    }
    return this.getClaudeFileReference(info.path) ?? '';
  }

  private requireReferencePath(filePath: string): string {
    const reference = this.getClaudeFileReference(filePath);
    if (!reference) {
      throw new Error(`Failed to compute reference for ${filePath}`);
    }
    return reference;
  }

  private async updatePullRequestSummary(issueNumber: number, outputs: PhaseOutputMap): Promise<void> {
    try {
      let prNumber = this.metadata.data.pr_number ?? null;
      const branchName =
        this.metadata.data.branch_name ?? `ai-workflow/issue-${this.metadata.data.issue_number}`;

      if (!prNumber) {
        const existing = await this.github.checkExistingPr(branchName);
        if (existing) {
          prNumber = existing.pr_number;
        } else {
          console.info('[INFO] No existing PR found. Skipping PR body update.');
          return;
        }
      }

      if (!prNumber) {
        return;
      }

      const extractedInfo = await this.github.extractPhaseOutputs(
        issueNumber,
        Object.fromEntries(
          Object.entries(outputs).map(([key, value]) => [key, value.path]),
        ),
      );

      const prBody = this.github.generatePrBodyDetailed(issueNumber, branchName, extractedInfo);
      const result = await this.github.updatePullRequest(prNumber, prBody);

      if (!result.success) {
        console.warn(`[WARNING] Failed to update PR body: ${result.error ?? 'unknown error'}`);
      } else {
        console.info(`[INFO] Updated PR #${prNumber} summary.`);
      }
    } catch (error) {
      const message = (error as Error).message ?? String(error);
      console.warn(`[WARNING] Failed to update PR summary: ${message}`);
    }
  }
}
