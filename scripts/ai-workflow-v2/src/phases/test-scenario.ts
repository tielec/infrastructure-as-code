import fs from 'fs-extra';
import path from 'node:path';
import { BasePhase, type PhaseInitializationParams } from './base-phase.js';
import { PhaseExecutionResult } from '../types.js';

type IssueInfo = {
  number: number;
  title: string;
  state: string;
  url: string;
  labels: string[];
  body: string;
};

export class TestScenarioPhase extends BasePhase {
  constructor(params: PhaseInitializationParams) {
    super({ ...params, phaseName: 'test_scenario' });
  }

  protected async execute(): Promise<PhaseExecutionResult> {
    const issueInfo = (await this.getIssueInfo()) as IssueInfo;
    const planningReference = this.getPlanningDocumentReference(issueInfo.number);

    const requirementsFile = this.getPhaseOutputFile('requirements', 'requirements.md', issueInfo.number);
    const designFile = this.getPhaseOutputFile('design', 'design.md', issueInfo.number);

    if (!requirementsFile) {
      return {
        success: false,
        error: '要件定義書が見つかりません。Phase 1 を実行してください。',
      };
    }

    if (!designFile) {
      return {
        success: false,
        error: '設計ドキュメントが見つかりません。Phase 2 を実行してください。',
      };
    }

    const requirementsReference = this.getClaudeFileReference(requirementsFile);
    const designReference = this.getClaudeFileReference(designFile);

    if (!requirementsReference || !designReference) {
      return {
        success: false,
        error: 'Claude Agent が参照できないドキュメントがあります。',
      };
    }

    const testStrategy = this.metadata.data.design_decisions.test_strategy;
    if (!testStrategy) {
      return {
        success: false,
        error: 'テスト戦略が設定されていません。Phase 2 で設計を完了してください。',
      };
    }

    const executePrompt = this.loadPrompt('execute')
      .replace('{planning_document_path}', planningReference)
      .replace('{requirements_document_path}', requirementsReference)
      .replace('{design_document_path}', designReference)
      .replace('{test_strategy}', testStrategy)
      .replace('{issue_info}', this.formatIssueInfo(issueInfo))
      .replace('{issue_number}', String(issueInfo.number));

    await this.executeWithClaude(executePrompt, { maxTurns: 40 });

    const scenarioFile = path.join(this.outputDir, 'test-scenario.md');
    if (!fs.existsSync(scenarioFile)) {
      return {
        success: false,
        error: `test-scenario.md が見つかりません: ${scenarioFile}`,
      };
    }

    try {
      const content = fs.readFileSync(scenarioFile, 'utf-8');
      await this.postOutput(content, 'テストシナリオ');
    } catch (error) {
      const message = (error as Error).message ?? String(error);
      console.warn(`[WARNING] GitHub へのテストシナリオ投稿に失敗しました: ${message}`);
    }

    return {
      success: true,
      output: scenarioFile,
    };
  }

  protected async review(): Promise<PhaseExecutionResult> {
    const issueInfo = (await this.getIssueInfo()) as IssueInfo;
    const scenarioFile = path.join(this.outputDir, 'test-scenario.md');

    if (!fs.existsSync(scenarioFile)) {
      return {
        success: false,
        error: 'test-scenario.md が存在しません。execute() を先に実行してください。',
      };
    }

    const requirementsFile = this.getPhaseOutputFile('requirements', 'requirements.md', issueInfo.number);
    const designFile = this.getPhaseOutputFile('design', 'design.md', issueInfo.number);

    if (!requirementsFile || !designFile) {
      return {
        success: false,
        error: '要件または設計ドキュメントが見つかりません。',
      };
    }

    const scenarioReference = this.getClaudeFileReference(scenarioFile);
    const requirementsReference = this.getClaudeFileReference(requirementsFile);
    const designReference = this.getClaudeFileReference(designFile);

    if (!scenarioReference || !requirementsReference || !designReference) {
      return {
        success: false,
        error: 'Claude Agent が参照できないドキュメントがあります。',
      };
    }

    const testStrategy = this.metadata.data.design_decisions.test_strategy ?? 'UNKNOWN';

    const reviewPrompt = this.loadPrompt('review')
      .replace('{test_scenario_document_path}', scenarioReference)
      .replace('{design_document_path}', designReference)
      .replace('{requirements_document_path}', requirementsReference)
      .replace('{test_strategy}', testStrategy);

    const messages = await this.executeWithClaude(reviewPrompt, { maxTurns: 30, logDir: this.reviewDir });
    const reviewResult = await this.contentParser.parseReviewResult(messages);

    const reviewFile = path.join(this.reviewDir, 'result.md');
    fs.writeFileSync(reviewFile, reviewResult.feedback, 'utf-8');

    await this.github.postReviewResult(
      issueInfo.number,
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
    const issueInfo = (await this.getIssueInfo()) as IssueInfo;
    const scenarioFile = path.join(this.outputDir, 'test-scenario.md');

    if (!fs.existsSync(scenarioFile)) {
      return {
        success: false,
        error: 'test-scenario.md が存在しません。execute() を先に実行してください。',
      };
    }

    const requirementsFile = this.getPhaseOutputFile('requirements', 'requirements.md', issueInfo.number);
    const designFile = this.getPhaseOutputFile('design', 'design.md', issueInfo.number);

    if (!requirementsFile || !designFile) {
      return {
        success: false,
        error: '要件または設計ドキュメントが見つかりません。',
      };
    }

    const scenarioReference = this.getClaudeFileReference(scenarioFile);
    const requirementsReference = this.getClaudeFileReference(requirementsFile);
    const designReference = this.getClaudeFileReference(designFile);

    if (!scenarioReference || !requirementsReference || !designReference) {
      return {
        success: false,
        error: 'Claude Agent が参照できないドキュメントがあります。',
      };
    }

    const testStrategy = this.metadata.data.design_decisions.test_strategy ?? 'UNKNOWN';

    const revisePrompt = this.loadPrompt('revise')
      .replace('{test_scenario_document_path}', scenarioReference)
      .replace('{design_document_path}', designReference)
      .replace('{requirements_document_path}', requirementsReference)
      .replace('{test_strategy}', testStrategy)
      .replace('{review_feedback}', reviewFeedback)
      .replace('{issue_number}', String(issueInfo.number));

    await this.executeWithClaude(revisePrompt, { maxTurns: 40, logDir: this.reviseDir });

    if (!fs.existsSync(scenarioFile)) {
      return {
        success: false,
        error: '改訂後の test-scenario.md を確認できませんでした。',
      };
    }

    return {
      success: true,
      output: scenarioFile,
    };
  }
}
