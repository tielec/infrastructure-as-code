import fs from 'fs-extra';
import path from 'node:path';
import { BasePhase, type PhaseInitializationParams } from './base-phase.js';
import { PhaseExecutionResult } from '../types.js';

export class ImplementationPhase extends BasePhase {
  constructor(params: PhaseInitializationParams) {
    super({ ...params, phaseName: 'implementation' });
  }

  protected async execute(): Promise<PhaseExecutionResult> {
    const issueNumber = parseInt(this.metadata.data.issue_number, 10);
    const planningReference = this.getPlanningDocumentReference(issueNumber);

    // オプショナルコンテキストを構築（Issue #396）
    const requirementsContext = this.buildOptionalContext(
      'requirements',
      'requirements.md',
      '要件定義書は利用できません。Planning情報とIssue情報から要件を推測してください。',
      issueNumber,
    );

    const designContext = this.buildOptionalContext(
      'design',
      'design.md',
      '設計書は利用できません。Issue情報とPlanning情報に基づいて適切な設計判断を行ってください。',
      issueNumber,
    );

    const testScenarioContext = this.buildOptionalContext(
      'test_scenario',
      'test-scenario.md',
      'テストシナリオは利用できません。実装時に適切なテスト考慮を行ってください。',
      issueNumber,
    );

    const implementationStrategy =
      this.metadata.data.design_decisions.implementation_strategy ??
      '実装方針は利用できません。Issue情報とPlanning情報に基づいて適切な実装アプローチを決定してください。';

    const executePrompt = this.loadPrompt('execute')
      .replace('{planning_document_path}', planningReference)
      .replace('{requirements_context}', requirementsContext)
      .replace('{design_context}', designContext)
      .replace('{test_scenario_context}', testScenarioContext)
      .replace('{implementation_strategy}', implementationStrategy)
      .replace('{issue_number}', String(issueNumber));

    await this.executeWithAgent(executePrompt, { maxTurns: 50 });

    const implementationFile = path.join(this.outputDir, 'implementation.md');
    if (!fs.existsSync(implementationFile)) {
      return {
        success: false,
        error: `implementation.md が見つかりません: ${implementationFile}`,
      };
    }

    try {
      const content = fs.readFileSync(implementationFile, 'utf-8');
      await this.postOutput(content, '実装内容');
    } catch (error) {
      const message = (error as Error).message ?? String(error);
      console.warn(`[WARNING] GitHub への実装結果投稿に失敗しました: ${message}`);
    }

    return {
      success: true,
      output: implementationFile,
    };
  }

  protected async review(): Promise<PhaseExecutionResult> {
    const issueNumber = parseInt(this.metadata.data.issue_number, 10);
    const implementationFile = path.join(this.outputDir, 'implementation.md');

    if (!fs.existsSync(implementationFile)) {
      return {
        success: false,
        error: 'implementation.md が存在しません。execute() を先に実行してください。',
      };
    }

    const planningReference = this.getPlanningDocumentReference(issueNumber);
    const designFile = this.getPhaseOutputFile('design', 'design.md', issueNumber);
    const scenarioFile = this.getPhaseOutputFile('test_scenario', 'test-scenario.md', issueNumber);

    if (!designFile || !scenarioFile) {
      return {
        success: false,
        error: '設計またはテストシナリオが見つかりません。',
      };
    }

    const implementationReference = this.getAgentFileReference(implementationFile);
    const designReference = this.getAgentFileReference(designFile);
    const scenarioReference = this.getAgentFileReference(scenarioFile);
    const implementationStrategy =
      this.metadata.data.design_decisions.implementation_strategy ??
      '実装方針は利用できません。実装内容とPlanning情報から推測してください。';

    if (!implementationReference || !designReference || !scenarioReference) {
      return {
        success: false,
        error: 'Claude Agent から参照できないドキュメントがあります。',
      };
    }

    const reviewPrompt = this.loadPrompt('review')
      .replace('{planning_document_path}', planningReference)
      .replace('{implementation_document_path}', implementationReference)
      .replace('{design_document_path}', designReference)
      .replace('{test_scenario_document_path}', scenarioReference)
      .replace('{implementation_strategy}', implementationStrategy);

    const messages = await this.executeWithAgent(reviewPrompt, { maxTurns: 30, logDir: this.reviewDir });
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
    const implementationFile = path.join(this.outputDir, 'implementation.md');

    if (!fs.existsSync(implementationFile)) {
      return {
        success: false,
        error: 'implementation.md が存在しません。execute() を先に実行してください。',
      };
    }

    const designFile = this.getPhaseOutputFile('design', 'design.md', issueNumber);
    const scenarioFile = this.getPhaseOutputFile('test_scenario', 'test-scenario.md', issueNumber);

    if (!designFile || !scenarioFile) {
      return {
        success: false,
        error: '設計またはテストシナリオが見つかりません。',
      };
    }

    const implementationReference = this.getAgentFileReference(implementationFile);
    const designReference = this.getAgentFileReference(designFile);
    const scenarioReference = this.getAgentFileReference(scenarioFile);
    const implementationStrategy =
      this.metadata.data.design_decisions.implementation_strategy ??
      '実装方針は利用できません。実装内容とPlanning情報から推測してください。';

    if (!implementationReference || !designReference || !scenarioReference) {
      return {
        success: false,
        error: 'Claude Agent から参照できないドキュメントがあります。',
      };
    }

    const revisePrompt = this.loadPrompt('revise')
      .replace('{implementation_document_path}', implementationReference)
      .replace('{design_document_path}', designReference)
      .replace('{test_scenario_document_path}', scenarioReference)
      .replace('{implementation_strategy}', implementationStrategy)
      .replace('{review_feedback}', reviewFeedback)
      .replace('{issue_number}', String(issueNumber));

    await this.executeWithAgent(revisePrompt, { maxTurns: 50, logDir: this.reviseDir });

    if (!fs.existsSync(implementationFile)) {
      return {
        success: false,
        error: '改訂後の implementation.md を確認できませんでした。',
      };
    }

    return {
      success: true,
      output: implementationFile,
    };
  }
}
