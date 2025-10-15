import fs from 'fs-extra';
import path from 'node:path';
import { BasePhase, type PhaseInitializationParams } from './base-phase.js';
import { PhaseExecutionResult } from '../types.js';

type PhaseOutputInfo = {
  path: string;
  exists: boolean;
};

type PhaseOutputMap = Record<string, PhaseOutputInfo>;

export class DocumentationPhase extends BasePhase {
  constructor(params: PhaseInitializationParams) {
    super({ ...params, phaseName: 'documentation' });
  }

  protected async execute(): Promise<PhaseExecutionResult> {
    const issueNumber = parseInt(this.metadata.data.issue_number, 10);
    const outputs = this.getPhaseOutputs(issueNumber);

    const requiredPhases = ['requirements', 'design', 'test_scenario', 'implementation', 'test_result'];
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
      test_result_document_path: this.requireReference(outputs, 'test_result'),
      test_implementation_document_path: this.optionalReference(outputs, 'test_implementation'),
    };

    const executePrompt = Object.entries(replacements).reduce(
      (acc, [key, value]) => acc.replace(`{${key}}`, value),
      this.loadPrompt('execute')
        .replace('{planning_document_path}', planningReference)
        .replace('{issue_number}', String(issueNumber)),
    );

    await this.executeWithAgent(executePrompt, { maxTurns: 30 });

    const documentationFile = path.join(this.outputDir, 'documentation-update-log.md');
    if (!fs.existsSync(documentationFile)) {
      return {
        success: false,
        error: `documentation-update-log.md が見つかりません: ${documentationFile}`,
      };
    }

    try {
      const content = fs.readFileSync(documentationFile, 'utf-8');
      await this.postOutput(content, 'ドキュメント更新ログ');
    } catch (error) {
      const message = (error as Error).message ?? String(error);
      console.warn(`[WARNING] GitHub へのドキュメント更新ログ投稿に失敗しました: ${message}`);
    }

    return {
      success: true,
      output: documentationFile,
    };
  }

  protected async review(): Promise<PhaseExecutionResult> {
    const issueNumber = parseInt(this.metadata.data.issue_number, 10);
    const documentationFile = path.join(this.outputDir, 'documentation-update-log.md');

    if (!fs.existsSync(documentationFile)) {
      return {
        success: false,
        error: 'documentation-update-log.md が存在しません。execute() を先に実行してください。',
      };
    }

    const outputs = this.getPhaseOutputs(issueNumber);
    const reviewPrompt = this.buildPrompt('review', issueNumber, documentationFile, outputs);

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
    const documentationFile = path.join(this.outputDir, 'documentation-update-log.md');

    if (!fs.existsSync(documentationFile)) {
      return {
        success: false,
        error: 'documentation-update-log.md が存在しません。execute() を先に実行してください。',
      };
    }

    const outputs = this.getPhaseOutputs(issueNumber);
    const revisePrompt = this.buildPrompt('revise', issueNumber, documentationFile, outputs).replace(
      '{review_feedback}',
      reviewFeedback,
    );

    await this.executeWithAgent(revisePrompt, { maxTurns: 30, logDir: this.reviseDir });

    if (!fs.existsSync(documentationFile)) {
      return {
        success: false,
        error: '改訂後の documentation-update-log.md を確認できませんでした。',
      };
    }

    return {
      success: true,
      output: documentationFile,
    };
  }

  private buildPrompt(
    promptType: 'review' | 'revise',
    issueNumber: number,
    documentationPath: string,
    outputs: PhaseOutputMap,
  ): string {
    const basePrompt = this.loadPrompt(promptType)
      .replace('{documentation_update_log_path}', this.requireReferencePath(documentationPath))
      .replace('{issue_number}', String(issueNumber));

    const replacements: Record<string, string> = {
      requirements_document_path: this.optionalReference(outputs, 'requirements'),
      design_document_path: this.optionalReference(outputs, 'design'),
      test_scenario_document_path: this.optionalReference(outputs, 'test_scenario'),
      implementation_document_path: this.optionalReference(outputs, 'implementation'),
      test_result_document_path: this.optionalReference(outputs, 'test_result'),
      test_implementation_document_path: this.optionalReference(outputs, 'test_implementation'),
    };

    return Object.entries(replacements).reduce(
      (acc, [key, value]) => acc.replace(`{${key}}`, value),
      basePrompt,
    );
  }

  private requireReference(outputs: PhaseOutputMap, key: string): string {
    const info = outputs[key];
    if (!info?.exists) {
      throw new Error(`Required phase output missing: ${key}`);
    }

    const reference = this.getAgentFileReference(info.path);
    if (!reference) {
      throw new Error(`Failed to compute reference path for ${info.path}`);
    }
    return reference;
  }

  private optionalReference(outputs: PhaseOutputMap, key: string): string {
    const info = outputs[key];
    if (!info?.exists) {
      return '';
    }
    const reference = this.getAgentFileReference(info.path);
    return reference ?? '';
  }

  private requireReferencePath(filePath: string): string {
    const reference = this.getAgentFileReference(filePath);
    if (!reference) {
      throw new Error(`Failed to compute reference path for ${filePath}`);
    }
    return reference;
  }

  private getPhaseOutputs(issueNumber: number): PhaseOutputMap {
    const baseDir = path.resolve(this.metadata.workflowDir, '..', `issue-${issueNumber}`);

    const newPaths: Record<string, string> = {
      requirements: path.join(baseDir, '01_requirements', 'output', 'requirements.md'),
      design: path.join(baseDir, '02_design', 'output', 'design.md'),
      test_scenario: path.join(baseDir, '03_test_scenario', 'output', 'test-scenario.md'),
      implementation: path.join(baseDir, '04_implementation', 'output', 'implementation.md'),
      test_implementation: path.join(baseDir, '05_test_implementation', 'output', 'test-implementation.md'),
      test_result: path.join(baseDir, '06_testing', 'output', 'test-result.md'),
    };

    const legacyPaths: Record<string, string> = {
      test_result: path.join(baseDir, '05_testing', 'output', 'test-result.md'),
    };

    const outputs: PhaseOutputMap = {};

    for (const [phase, newPath] of Object.entries(newPaths)) {
      let finalPath = newPath;
      if (!fs.existsSync(newPath) && legacyPaths[phase] && fs.existsSync(legacyPaths[phase])) {
        finalPath = legacyPaths[phase];
        console.info(`[INFO] Using legacy documentation path for ${phase}: ${finalPath}`);
      }
      outputs[phase] = {
        path: finalPath,
        exists: fs.existsSync(finalPath),
      };
    }

    return outputs;
  }
}
