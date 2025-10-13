import fs from 'fs-extra';
import path from 'node:path';
import { BasePhase, type PhaseInitializationParams } from './base-phase.js';
import { PhaseExecutionResult } from '../types.js';

export class TestImplementationPhase extends BasePhase {
  constructor(params: PhaseInitializationParams) {
    super({ ...params, phaseName: 'test_implementation' });
  }

  protected async execute(): Promise<PhaseExecutionResult> {
    const issueNumber = parseInt(this.metadata.data.issue_number, 10);
    const planningReference = this.getPlanningDocumentReference(issueNumber);

    const requirementsFile = this.getPhaseOutputFile('requirements', 'requirements.md', issueNumber);
    const designFile = this.getPhaseOutputFile('design', 'design.md', issueNumber);
    const scenarioFile = this.getPhaseOutputFile('test_scenario', 'test-scenario.md', issueNumber);
    const implementationFile = this.getPhaseOutputFile('implementation', 'implementation.md', issueNumber);

    if (!requirementsFile || !designFile || !scenarioFile || !implementationFile) {
      return {
        success: false,
        error: '要件・設計・テストシナリオ・実装のいずれかが欠けています。',
      };
    }

    const requirementsReference = this.getClaudeFileReference(requirementsFile);
    const designReference = this.getClaudeFileReference(designFile);
    const scenarioReference = this.getClaudeFileReference(scenarioFile);
    const implementationReference = this.getClaudeFileReference(implementationFile);

    if (
      !requirementsReference ||
      !designReference ||
      !scenarioReference ||
      !implementationReference
    ) {
      return {
        success: false,
        error: 'Claude Agent から参照できないドキュメントがあります。',
      };
    }

    const testStrategy = this.metadata.data.design_decisions.test_strategy;
    const testCodeStrategy = this.metadata.data.design_decisions.test_code_strategy;

    if (!testStrategy || !testCodeStrategy) {
      return {
        success: false,
        error: 'テスト戦略・テストコード方針が未設定です。Phase 2 (design) を確認してください。',
      };
    }

    const executePrompt = this.loadPrompt('execute')
      .replace('{planning_document_path}', planningReference)
      .replace('{requirements_document_path}', requirementsReference)
      .replace('{design_document_path}', designReference)
      .replace('{test_scenario_document_path}', scenarioReference)
      .replace('{implementation_document_path}', implementationReference)
      .replace('{test_strategy}', testStrategy)
      .replace('{test_code_strategy}', testCodeStrategy)
      .replace('{issue_number}', String(issueNumber));

    await this.executeWithClaude(executePrompt, { maxTurns: 40 });

    const testImplementationFile = path.join(this.outputDir, 'test-implementation.md');
    if (!fs.existsSync(testImplementationFile)) {
      return {
        success: false,
        error: `test-implementation.md が見つかりません: ${testImplementationFile}`,
      };
    }

    try {
      const content = fs.readFileSync(testImplementationFile, 'utf-8');
      await this.postOutput(content, 'テストコード実装方針');
    } catch (error) {
      const message = (error as Error).message ?? String(error);
      console.warn(`[WARNING] GitHub へのテストコード実装出力に失敗しました: ${message}`);
    }

    return {
      success: true,
      output: testImplementationFile,
    };
  }

  protected async review(): Promise<PhaseExecutionResult> {
    const issueNumber = parseInt(this.metadata.data.issue_number, 10);
    const testImplementationFile = path.join(this.outputDir, 'test-implementation.md');

    if (!fs.existsSync(testImplementationFile)) {
      return {
        success: false,
        error: 'test-implementation.md が存在しません。execute() を先に実行してください。',
      };
    }

    const designFile = this.getPhaseOutputFile('design', 'design.md', issueNumber);
    const scenarioFile = this.getPhaseOutputFile('test_scenario', 'test-scenario.md', issueNumber);
    const implementationFile = this.getPhaseOutputFile('implementation', 'implementation.md', issueNumber);

    if (!designFile || !scenarioFile || !implementationFile) {
      return {
        success: false,
        error: '設計・テストシナリオ・実装のいずれかが見つかりません。',
      };
    }

    const testImplementationReference = this.getClaudeFileReference(testImplementationFile);
    const designReference = this.getClaudeFileReference(designFile);
    const scenarioReference = this.getClaudeFileReference(scenarioFile);
    const implementationReference = this.getClaudeFileReference(implementationFile);

    if (
      !testImplementationReference ||
      !designReference ||
      !scenarioReference ||
      !implementationReference
    ) {
      return {
        success: false,
        error: 'Claude Agent から参照できないドキュメントがあります。',
      };
    }

    const testStrategy = this.metadata.data.design_decisions.test_strategy ?? 'UNKNOWN';
    const testCodeStrategy = this.metadata.data.design_decisions.test_code_strategy ?? 'UNKNOWN';

    const reviewPrompt = this.loadPrompt('review')
      .replace('{test_implementation_document_path}', testImplementationReference)
      .replace('{design_document_path}', designReference)
      .replace('{test_scenario_document_path}', scenarioReference)
      .replace('{implementation_document_path}', implementationReference)
      .replace('{test_strategy}', testStrategy)
      .replace('{test_code_strategy}', testCodeStrategy);

    const messages = await this.executeWithClaude(reviewPrompt, { maxTurns: 30 });
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
    const testImplementationFile = path.join(this.outputDir, 'test-implementation.md');

    if (!fs.existsSync(testImplementationFile)) {
      return {
        success: false,
        error: 'test-implementation.md が存在しません。execute() を先に実行してください。',
      };
    }

    const designFile = this.getPhaseOutputFile('design', 'design.md', issueNumber);
    const scenarioFile = this.getPhaseOutputFile('test_scenario', 'test-scenario.md', issueNumber);
    const implementationFile = this.getPhaseOutputFile('implementation', 'implementation.md', issueNumber);

    if (!designFile || !scenarioFile || !implementationFile) {
      return {
        success: false,
        error: '設計・テストシナリオ・実装のいずれかが見つかりません。',
      };
    }

    const testImplementationReference = this.getClaudeFileReference(testImplementationFile);
    const designReference = this.getClaudeFileReference(designFile);
    const scenarioReference = this.getClaudeFileReference(scenarioFile);
    const implementationReference = this.getClaudeFileReference(implementationFile);

    if (
      !testImplementationReference ||
      !designReference ||
      !scenarioReference ||
      !implementationReference
    ) {
      return {
        success: false,
        error: 'Claude Agent から参照できないドキュメントがあります。',
      };
    }

    const testStrategy = this.metadata.data.design_decisions.test_strategy ?? 'UNKNOWN';
    const testCodeStrategy = this.metadata.data.design_decisions.test_code_strategy ?? 'UNKNOWN';

    const revisePrompt = this.loadPrompt('revise')
      .replace('{test_implementation_document_path}', testImplementationReference)
      .replace('{design_document_path}', designReference)
      .replace('{test_scenario_document_path}', scenarioReference)
      .replace('{implementation_document_path}', implementationReference)
      .replace('{test_strategy}', testStrategy)
      .replace('{test_code_strategy}', testCodeStrategy)
      .replace('{review_feedback}', reviewFeedback)
      .replace('{issue_number}', String(issueNumber));

    await this.executeWithClaude(revisePrompt, { maxTurns: 50 });

    if (!fs.existsSync(testImplementationFile)) {
      return {
        success: false,
        error: '改訂後の test-implementation.md を確認できませんでした。',
      };
    }

    return {
      success: true,
      output: testImplementationFile,
    };
  }
}
