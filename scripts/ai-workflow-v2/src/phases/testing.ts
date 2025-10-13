import fs from 'fs-extra';
import path from 'node:path';
import { BasePhase, type PhaseInitializationParams } from './base-phase.js';
import { PhaseExecutionResult } from '../types.js';

export class TestingPhase extends BasePhase {
  constructor(params: PhaseInitializationParams) {
    super({ ...params, phaseName: 'testing' });
  }

  protected async execute(): Promise<PhaseExecutionResult> {
    const issueNumber = parseInt(this.metadata.data.issue_number, 10);
    const planningReference = this.getPlanningDocumentReference(issueNumber);

    const testImplementationFile = this.getPhaseOutputFile(
      'test_implementation',
      'test-implementation.md',
      issueNumber,
    );
    const implementationFile = this.getPhaseOutputFile('implementation', 'implementation.md', issueNumber);
    const scenarioFile = this.getPhaseOutputFile('test_scenario', 'test-scenario.md', issueNumber);

    if (!testImplementationFile || !implementationFile || !scenarioFile) {
      return {
        success: false,
        error: 'テスト実装・実装・テストシナリオのいずれかが欠けています。',
      };
    }

    const testImplementationRef = this.getClaudeFileReference(testImplementationFile);
    const implementationRef = this.getClaudeFileReference(implementationFile);
    const scenarioRef = this.getClaudeFileReference(scenarioFile);

    if (!testImplementationRef || !implementationRef || !scenarioRef) {
      return {
        success: false,
        error: 'Claude Agent から参照できないドキュメントがあります。',
      };
    }

    const testResultFile = path.join(this.outputDir, 'test-result.md');
    const oldMtime = fs.existsSync(testResultFile) ? fs.statSync(testResultFile).mtimeMs : null;

    const executePrompt = this.loadPrompt('execute')
      .replace('{planning_document_path}', planningReference)
      .replace('{test_implementation_document_path}', testImplementationRef)
      .replace('{implementation_document_path}', implementationRef)
      .replace('{test_scenario_document_path}', scenarioRef)
      .replace('{issue_number}', String(issueNumber));

    await this.executeWithClaude(executePrompt, { maxTurns: 30 });

    if (!fs.existsSync(testResultFile)) {
      return {
        success: false,
        error: `test-result.md が見つかりません: ${testResultFile}`,
      };
    }

    const newMtime = fs.statSync(testResultFile).mtimeMs;
    if (oldMtime !== null && newMtime === oldMtime) {
      return {
        success: false,
        error: 'test-result.md が更新されていません。出力内容を確認してください。',
      };
    }

    return {
      success: true,
      output: testResultFile,
    };
  }

  protected async review(): Promise<PhaseExecutionResult> {
    const issueNumber = parseInt(this.metadata.data.issue_number, 10);
    const testResultFile = path.join(this.outputDir, 'test-result.md');

    if (!fs.existsSync(testResultFile)) {
      return {
        success: false,
        error: 'test-result.md が存在しません。execute() を先に実行してください。',
      };
    }

    const testImplementationFile = this.getPhaseOutputFile(
      'test_implementation',
      'test-implementation.md',
      issueNumber,
    );
    const implementationFile = this.getPhaseOutputFile('implementation', 'implementation.md', issueNumber);
    const scenarioFile = this.getPhaseOutputFile('test_scenario', 'test-scenario.md', issueNumber);

    if (!testImplementationFile || !implementationFile || !scenarioFile) {
      return {
        success: false,
        error: '前段フェーズの成果物が不足しています。',
      };
    }

    const testResultRef = this.getClaudeFileReference(testResultFile);
    const testImplementationRef = this.getClaudeFileReference(testImplementationFile);
    const implementationRef = this.getClaudeFileReference(implementationFile);
    const scenarioRef = this.getClaudeFileReference(scenarioFile);

    if (!testResultRef || !testImplementationRef || !implementationRef || !scenarioRef) {
      return {
        success: false,
        error: 'Claude Agent から参照できないドキュメントがあります。',
      };
    }

    const reviewPrompt = this.loadPrompt('review')
      .replace('{test_result_document_path}', testResultRef)
      .replace('{test_implementation_document_path}', testImplementationRef)
      .replace('{implementation_document_path}', implementationRef)
      .replace('{test_scenario_document_path}', scenarioRef);

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
    const testResultFile = path.join(this.outputDir, 'test-result.md');

    if (!fs.existsSync(testResultFile)) {
      return {
        success: false,
        error: 'test-result.md が存在しません。execute() を先に実行してください。',
      };
    }

    const testImplementationFile = this.getPhaseOutputFile(
      'test_implementation',
      'test-implementation.md',
      issueNumber,
    );
    const implementationFile = this.getPhaseOutputFile('implementation', 'implementation.md', issueNumber);
    const scenarioFile = this.getPhaseOutputFile('test_scenario', 'test-scenario.md', issueNumber);

    if (!testImplementationFile || !implementationFile || !scenarioFile) {
      return {
        success: false,
        error: '前段フェーズの成果物が不足しています。',
      };
    }

    const testResultRef = this.getClaudeFileReference(testResultFile);
    const testImplementationRef = this.getClaudeFileReference(testImplementationFile);
    const implementationRef = this.getClaudeFileReference(implementationFile);
    const scenarioRef = this.getClaudeFileReference(scenarioFile);

    if (!testResultRef || !testImplementationRef || !implementationRef || !scenarioRef) {
      return {
        success: false,
        error: 'Claude Agent から参照できないドキュメントがあります。',
      };
    }

    const revisePrompt = this.loadPrompt('revise')
      .replace('{test_result_document_path}', testResultRef)
      .replace('{test_implementation_document_path}', testImplementationRef)
      .replace('{implementation_document_path}', implementationRef)
      .replace('{test_scenario_document_path}', scenarioRef)
      .replace('{review_feedback}', reviewFeedback)
      .replace('{issue_number}', String(issueNumber));

    const oldMtime = fs.existsSync(testResultFile) ? fs.statSync(testResultFile).mtimeMs : null;

    await this.executeWithClaude(revisePrompt, { maxTurns: 30 });

    if (!fs.existsSync(testResultFile)) {
      return {
        success: false,
        error: '改訂後の test-result.md を確認できませんでした。',
      };
    }

    const newMtime = fs.statSync(testResultFile).mtimeMs;
    if (oldMtime !== null && newMtime === oldMtime) {
      return {
        success: false,
        error: 'test-result.md が更新されていません。再度実行内容を確認してください。',
      };
    }

    return {
      success: true,
      output: testResultFile,
    };
  }
}
