import fs from 'fs-extra';
import path from 'node:path';
import { BasePhase, type PhaseInitializationParams } from './base-phase.js';
import { PhaseExecutionResult, RemainingTask, PhaseName } from '../types.js';

type PhaseOutputInfo = {
  path: string;
  exists: boolean;
};

type PhaseOutputMap = Record<string, PhaseOutputInfo>;

export class EvaluationPhase extends BasePhase {
  constructor(params: PhaseInitializationParams) {
    super({ ...params, phaseName: 'evaluation' });
  }

  protected async execute(): Promise<PhaseExecutionResult> {
    const issueNumber = parseInt(this.metadata.data.issue_number, 10);
    const outputs = this.getAllPhaseOutputs(issueNumber);

    const requiredPhases: PhaseName[] = [
      'planning',
      'requirements',
      'design',
      'test_scenario',
      'implementation',
      'test_implementation',
      'testing',
      'documentation',
      'report',
    ];

    for (const phase of requiredPhases) {
      if (!outputs[phase]?.exists) {
        return {
          success: false,
          output: null,
          decision: null,
          error: `${phase} の成果物が見つかりません: ${outputs[phase]?.path ?? 'N/A'}`,
        };
      }
    }

    const planningReference = this.getPlanningDocumentReference(issueNumber);
    const issueTitle = this.metadata.data.issue_title ?? `Issue #${issueNumber}`;
    const repoName = this.metadata.data.repository ?? 'unknown';
    const branchName =
      this.metadata.data.branch_name ?? `ai-workflow/issue-${this.metadata.data.issue_number}`;
    const workflowDir = this.metadata.workflowDir;
    const agentWorkingDir = this.getAgentWorkingDirectory();

    const relPaths: Record<string, string> = {};
    for (const [phase, info] of Object.entries(outputs)) {
      const relative = this.getAgentFileReference(info.path);
      relPaths[phase] = relative ?? info.path;
    }

    const phaseOutputsList = Object.entries(relPaths)
      .map(([phase, ref]) => `- **${this.formatPhaseName(phase)}**: ${ref}`)
      .join('\n');

    const executePrompt = this.loadPrompt('execute')
      .replace('{issue_number}', String(issueNumber))
      .replace('{issue_title}', issueTitle)
      .replace('{repo_name}', repoName)
      .replace('{branch_name}', branchName)
      .replace('{workflow_dir}', workflowDir)
      .replace('{phase_outputs}', phaseOutputsList)
      .replace('{planning_document_path}', planningReference)
      .replace('{requirements_document_path}', relPaths.requirements)
      .replace('{design_document_path}', relPaths.design)
      .replace('{test_scenario_document_path}', relPaths.test_scenario)
      .replace('{implementation_document_path}', relPaths.implementation)
      .replace('{test_implementation_document_path}', relPaths.test_implementation)
      .replace('{test_result_document_path}', relPaths.testing)
      .replace('{documentation_update_log_path}', relPaths.documentation)
      .replace('{report_document_path}', relPaths.report);

    await this.executeWithAgent(executePrompt, { maxTurns: 50 });

    const evaluationFile = path.join(this.outputDir, 'evaluation_report.md');
    if (!fs.existsSync(evaluationFile)) {
      return {
        success: false,
        output: null,
        decision: null,
        error: `evaluation_report.md が見つかりません: ${evaluationFile}`,
      };
    }

    try {
      const content = fs.readFileSync(evaluationFile, 'utf-8');

      // Phase outputはPRに含まれるため、Issue投稿は不要（Review resultのみ投稿）
      // await this.postOutput(content, 'プロジェクト評価レポート');

      const decisionResult = await this.contentParser.parseEvaluationDecision(content);

      console.info(`[DEBUG] Decision extraction result: ${JSON.stringify(decisionResult)}`);

      if (!decisionResult.success || !decisionResult.decision) {
        console.error(`[ERROR] Failed to determine decision: ${decisionResult.error}`);
        console.error(`[ERROR] Content snippet: ${content.substring(0, 500)}`);
        return {
          success: false,
          output: evaluationFile,
          decision: decisionResult.decision ?? null,
          error: decisionResult.error ?? '判定タイプの解析に失敗しました',
        };
      }

      const decision = decisionResult.decision;
      console.info(`[INFO] 評価判定: ${decision}`);

      if (decision === 'PASS') {
        this.metadata.setEvaluationDecision({ decision: 'PASS' });
        return {
          success: true,
          output: evaluationFile,
          decision,
        };
      }

      if (decision === 'PASS_WITH_ISSUES') {
        const remainingTasks = decisionResult.remainingTasks ?? [];
        const passResult = await this.handlePassWithIssues(remainingTasks, issueNumber, evaluationFile);

        if (!passResult.success) {
          this.metadata.setEvaluationDecision({
            decision: 'PASS_WITH_ISSUES',
            remainingTasks,
            createdIssueUrl: null,
          });
          return {
            success: false,
            output: evaluationFile,
            decision,
            error: passResult.error ?? '残タスク Issue の作成に失敗しました',
          };
        }

        this.metadata.setEvaluationDecision({
          decision: 'PASS_WITH_ISSUES',
          remainingTasks,
          createdIssueUrl: passResult.createdIssueUrl ?? null,
        });

        return {
          success: true,
          output: evaluationFile,
          decision,
        };
      }

      if (decision.startsWith('FAIL_PHASE_')) {
        const failedPhase = decisionResult.failedPhase;
        if (!failedPhase) {
          return {
            success: false,
            output: evaluationFile,
            decision,
            error: '失敗フェーズの特定に失敗しました',
          };
        }

        const failResult = this.metadata.rollbackToPhase(failedPhase);
        if (!failResult.success) {
          return {
            success: false,
            output: evaluationFile,
            decision,
            error: failResult.error ?? 'メタデータの巻き戻しに失敗しました',
          };
        }

        this.metadata.setEvaluationDecision({
          decision,
          failedPhase,
        });

        return {
          success: true,
          output: evaluationFile,
          decision,
        };
      }

      if (decision === 'ABORT') {
        const abortReason =
          decisionResult.abortReason ?? 'プロジェクトを継続できない重大な問題が検出されました。';
        const abortResult = await this.handleAbort(abortReason, issueNumber);

        this.metadata.setEvaluationDecision({
          decision: 'ABORT',
          abortReason,
        });

        if (!abortResult.success) {
          return {
            success: false,
            output: evaluationFile,
            decision,
            error: abortResult.error ?? 'ワークフロー中止処理に失敗しました',
          };
        }

        return {
          success: true,
          output: evaluationFile,
          decision,
        };
      }

      console.error(`[ERROR] Invalid decision type: ${decision}`);
      console.error(`[ERROR] Valid decisions: PASS, PASS_WITH_ISSUES, FAIL_PHASE_*, ABORT`);
      console.error(`[ERROR] Content snippet for debugging: ${content.substring(0, 1000)}`);
      return {
        success: false,
        output: evaluationFile,
        decision,
        error: `不正な判定タイプ: ${decision}. 有効な判定: PASS, PASS_WITH_ISSUES, FAIL_PHASE_*, ABORT`,
      };
    } catch (error) {
      const message = (error as Error).message ?? String(error);
      return {
        success: false,
        output: evaluationFile,
        decision: null,
        error: message,
      };
    }
  }

  protected async review(): Promise<PhaseExecutionResult> {
    // Evaluation phase does not require review
    // But we save a placeholder result.md for consistency
    const reviewFile = path.join(this.reviewDir, 'result.md');
    const content = '# 評価フェーズレビュー\n\n評価フェーズにはレビューは不要です。\n\n**判定**: PASS\n';
    fs.writeFileSync(reviewFile, content, 'utf-8');

    return {
      success: true,
      output: null,
    };
  }

  private getAllPhaseOutputs(issueNumber: number): PhaseOutputMap {
    const baseDir = path.resolve(this.metadata.workflowDir, '..', `issue-${issueNumber}`);

    const entries: Record<string, string> = {
      planning: path.join(baseDir, '00_planning', 'output', 'planning.md'),
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
      testing: path.join(baseDir, '06_testing', 'output', 'test-result.md'),
      documentation: path.join(
        baseDir,
        '07_documentation',
        'output',
        'documentation-update-log.md',
      ),
      report: path.join(baseDir, '08_report', 'output', 'report.md'),
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

  private async handlePassWithIssues(
    remainingTasks: RemainingTask[],
    issueNumber: number,
    evaluationFile: string,
  ): Promise<{ success: boolean; createdIssueUrl?: string | null; error?: string }> {
    if (!remainingTasks.length) {
      return { success: true, createdIssueUrl: null };
    }

    try {
      const agentWorkingDir = this.getAgentWorkingDirectory();
      const repoRoot = path.resolve(agentWorkingDir, '..', '..');
      const relativeReportPath = path.relative(repoRoot, evaluationFile);

      const result = await this.github.createIssueFromEvaluation(
        issueNumber,
        remainingTasks,
        relativeReportPath,
      );

      if (result.success) {
        return { success: true, createdIssueUrl: result.issue_url ?? null };
      }

      return { success: false, error: result.error ?? 'Issue 作成に失敗しました' };
    } catch (error) {
      const message = (error as Error).message ?? String(error);
      return { success: false, error: message };
    }
  }

  private async handleAbort(
    abortReason: string,
    issueNumber: number,
  ): Promise<{ success: boolean; error?: string }> {
    try {
      const issueResult = await this.github.closeIssueWithReason(issueNumber, abortReason);
      if (!issueResult.success) {
        console.warn(`[WARNING] Issue クローズに失敗: ${issueResult.error ?? '不明なエラー'}`);
      }

      const prNumber = await this.github.getPullRequestNumber(issueNumber);
      if (prNumber) {
        const prResult = await this.github.closePullRequest(prNumber, abortReason);
        if (!prResult.success) {
          console.warn(`[WARNING] PR クローズに失敗: ${prResult.error ?? '不明なエラー'}`);
        }
      }

      return { success: true };
    } catch (error) {
      const message = (error as Error).message ?? String(error);
      return { success: false, error: message };
    }
  }

  private formatPhaseName(phase: string): string {
    return phase
      .split('_')
      .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
      .join(' ');
  }
}
