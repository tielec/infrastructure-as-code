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

    const requirementsFile = this.getPhaseOutputFile('requirements', 'requirements.md', issueNumber);
    const designFile = this.getPhaseOutputFile('design', 'design.md', issueNumber);
    const scenarioFile = this.getPhaseOutputFile('test_scenario', 'test-scenario.md', issueNumber);

    if (!requirementsFile || !designFile || !scenarioFile) {
      return {
        success: false,
        error: '要件・設計・テストシナリオのいずれかが欠けています。前段フェーズを完了してください。',
      };
    }

    const requirementsReference = this.getClaudeFileReference(requirementsFile);
    const designReference = this.getClaudeFileReference(designFile);
    const scenarioReference = this.getClaudeFileReference(scenarioFile);

    if (!requirementsReference || !designReference || !scenarioReference) {
      return {
        success: false,
        error: 'Claude Agent から参照できないドキュメントがあります。',
      };
    }

    const implementationStrategy = this.metadata.data.design_decisions.implementation_strategy;
    if (!implementationStrategy) {
      return {
        success: false,
        error: '実装方針が未設定です。Phase 2 (design) を完了してください。',
      };
    }

    const executePrompt = this.loadPrompt('execute')
      .replace('{planning_document_path}', planningReference)
      .replace('{requirements_document_path}', requirementsReference)
      .replace('{design_document_path}', designReference)
      .replace('{test_scenario_document_path}', scenarioReference)
      .replace('{implementation_strategy}', implementationStrategy)
      .replace('{issue_number}', String(issueNumber));

    await this.executeWithClaude(executePrompt, { maxTurns: 50 });

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

    const designFile = this.getPhaseOutputFile('design', 'design.md', issueNumber);
    const scenarioFile = this.getPhaseOutputFile('test_scenario', 'test-scenario.md', issueNumber);

    if (!designFile || !scenarioFile) {
      return {
        success: false,
        error: '設計またはテストシナリオが見つかりません。',
      };
    }

    const implementationReference = this.getClaudeFileReference(implementationFile);
    const designReference = this.getClaudeFileReference(designFile);
    const scenarioReference = this.getClaudeFileReference(scenarioFile);
    const implementationStrategy = this.metadata.data.design_decisions.implementation_strategy ?? 'UNKNOWN';

    if (!implementationReference || !designReference || !scenarioReference) {
      return {
        success: false,
        error: 'Claude Agent から参照できないドキュメントがあります。',
      };
    }

    const reviewPrompt = this.loadPrompt('review')
      .replace('{implementation_document_path}', implementationReference)
      .replace('{design_document_path}', designReference)
      .replace('{test_scenario_document_path}', scenarioReference)
      .replace('{implementation_strategy}', implementationStrategy);

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

    const implementationReference = this.getClaudeFileReference(implementationFile);
    const designReference = this.getClaudeFileReference(designFile);
    const scenarioReference = this.getClaudeFileReference(scenarioFile);
    const implementationStrategy = this.metadata.data.design_decisions.implementation_strategy ?? 'UNKNOWN';

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

    await this.executeWithClaude(revisePrompt, { maxTurns: 50, logDir: this.reviseDir });

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
