import fs from 'fs-extra';
import path from 'node:path';
import { BasePhase, type PhaseInitializationParams } from './base-phase.js';
import { PhaseExecutionResult, PhaseName } from '../types.js';

type PhaseOutputInfo = {
  path: string;
  exists: boolean;
};

type PhaseOutputMap = Record<string, PhaseOutputInfo>;

type DecisionResult = {
  success: boolean;
  decision?: string;
  failedPhase?: PhaseName;
  abortReason?: string;
  error?: string;
};

type RemainingTask = {
  task: string;
  phase: string;
  priority: string;
};

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
    const claudeWorkingDir = this.claude.getWorkingDirectory();

    const relPaths: Record<string, string> = {};
    for (const [phase, info] of Object.entries(outputs)) {
      const relative = this.getClaudeFileReference(info.path);
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

    await this.executeWithClaude(executePrompt, { maxTurns: 50 });

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
      await this.postOutput(content, 'プロジェクト評価レポート');

      const decisionResult = this.determineDecision(content);
      if (!decisionResult.success || !decisionResult.decision) {
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
        const remainingTasks = this.extractRemainingTasks(content);
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

      return {
        success: false,
        output: evaluationFile,
        decision,
        error: `不正な判定タイプ: ${decision}`,
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

  private determineDecision(content: string): DecisionResult {
    try {
      const decisionPattern1 = /##\s*決定.*?\n.*?(?:判定|決定|結果)[:：]\s*\**([A-Z_]+)\**/is;
      const decisionPattern2 = /\*\*(?:判定|決定|結果)\*\*[:：]\s*\**([A-Z_]+)\**/i;

      let match = content.match(decisionPattern1) ?? content.match(decisionPattern2);

      if (!match) {
        return {
          success: false,
          decision: undefined,
          error: '判定セクションを特定できませんでした',
        };
      }

      const decision = match[1].trim();
      const validDecisions = ['PASS', 'PASS_WITH_ISSUES', 'ABORT'];

      if (decision.startsWith('FAIL_PHASE_')) {
        const phaseKey = decision.replace('FAIL_PHASE_', '').toLowerCase();
        const mapping: Record<string, PhaseName> = {
          planning: 'planning',
          '0': 'planning',
          requirements: 'requirements',
          '1': 'requirements',
          design: 'design',
          '2': 'design',
          test_scenario: 'test_scenario',
          testscenario: 'test_scenario',
          '3': 'test_scenario',
          implementation: 'implementation',
          '4': 'implementation',
          test_implementation: 'test_implementation',
          testimplementation: 'test_implementation',
          '5': 'test_implementation',
          testing: 'testing',
          '6': 'testing',
          documentation: 'documentation',
          '7': 'documentation',
          report: 'report',
          '8': 'report',
        };

        const failedPhase = mapping[phaseKey];
        if (!failedPhase) {
          return {
            success: false,
            decision,
            error: `無効なフェーズ名: ${phaseKey}`,
          };
        }

        return {
          success: true,
          decision,
          failedPhase,
        };
      }

      if (validDecisions.includes(decision)) {
        let abortReason: string | undefined;
        if (decision === 'ABORT') {
          const reasonMatch = content.match(
            /(?:中止|ABORT)理由[:：]\s*(.+?)(?:\n\n|\n##|$)/is,
          );
          abortReason = reasonMatch ? reasonMatch[1].trim() : 'プロジェクトを継続できません。';
        }

        return {
          success: true,
          decision,
          abortReason,
        };
      }

      return {
        success: false,
        decision,
        error: `無効な判定タイプ: ${decision}`,
      };
    } catch (error) {
      const message = (error as Error).message ?? String(error);
      return {
        success: false,
        decision: undefined,
        error: `判定解析中にエラー: ${message}`,
      };
    }
  }

  private extractRemainingTasks(content: string): RemainingTask[] {
    const tasks: RemainingTask[] = [];

    try {
      const sectionMatch = content.match(/##\s*残タスク(?:一覧)?\s*\n([\s\S]*?)(?:\n##|$)/i);
      if (!sectionMatch) {
        return tasks;
      }

      const sectionText = sectionMatch[1];
      const taskMatches = sectionText.match(/- \[ \]\s*.+/g) ?? [];

      for (const taskLine of taskMatches) {
        const phaseMatch = taskLine.match(/(?:Phase|phase)[:：]\s*([^、,\n]+)/);
        const priorityMatch = taskLine.match(/優先度[:：]\s*([高中低])/);

        const cleanTask = taskLine
          .replace(/- \[ \]\s*/, '')
          .replace(/（.*?）/g, '')
          .replace(/\(.*?\)/g, '')
          .trim();

        tasks.push({
          task: cleanTask,
          phase: phaseMatch ? phaseMatch[1].trim() : 'unknown',
          priority: priorityMatch ? priorityMatch[1] : '中',
        });
      }
    } catch (error) {
      const message = (error as Error).message ?? String(error);
      console.warn(`[WARNING] 残タスクの抽出に失敗しました: ${message}`);
    }

    return tasks;
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
      const claudeDir = this.claude.getWorkingDirectory();
      const repoRoot = path.resolve(claudeDir, '..', '..');
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
