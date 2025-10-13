import fs from 'fs-extra';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { OpenAI } from 'openai';

interface ReviewParseResult {
  result: string;
  feedback: string;
  suggestions: string[];
}

export class ContentParser {
  private readonly client: OpenAI;
  private readonly model: string;
  private readonly promptDir: string;

  constructor(options: { apiKey?: string; model?: string } = {}) {
    const apiKey = options.apiKey ?? process.env.OPENAI_API_KEY;
    if (!apiKey) {
      throw new Error(
        [
          'OpenAI API key is required.',
          'Set the OPENAI_API_KEY environment variable or pass apiKey via constructor.',
          'You can create an API key from https://platform.openai.com/api-keys',
        ].join('\n'),
      );
    }

    this.client = new OpenAI({ apiKey });
    this.model = options.model ?? 'gpt-4o-mini';

    const moduleDir = path.dirname(fileURLToPath(import.meta.url));
    this.promptDir = path.resolve(moduleDir, '..', 'prompts', 'content_parser');
  }

  private loadPrompt(promptName: string): string {
    const promptPath = path.join(this.promptDir, `${promptName}.txt`);
    if (!fs.existsSync(promptPath)) {
      throw new Error(`Prompt file not found: ${promptPath}`);
    }
    return fs.readFileSync(promptPath, 'utf-8');
  }

  public async extractDesignDecisions(documentContent: string): Promise<Record<string, string>> {
    const template = this.loadPrompt('extract_design_decisions');
    const prompt = template.replace('{document_content}', documentContent);

    try {
      const response = await this.client.chat.completions.create({
        model: this.model,
        messages: [{ role: 'user', content: prompt }],
        max_tokens: 1024,
        temperature: 0,
      });

      const content = response.choices?.[0]?.message?.content ?? '{}';
      const parsed = JSON.parse(content) as Record<string, string | null | undefined>;
      const result: Record<string, string> = {};
      for (const [key, value] of Object.entries(parsed)) {
        if (typeof value === 'string' && value.trim().length > 0) {
          result[key] = value;
        }
      }
      return result;
    } catch (error) {
      const message = (error as Error).message ?? String(error);
      console.warn(`[WARNING] Failed to extract design decisions: ${message}`);
      return {};
    }
  }

  public async parseReviewResult(messages: string[]): Promise<ReviewParseResult> {
    const textBlocks: string[] = [];

    for (const rawMessage of messages) {
      try {
        const message = JSON.parse(rawMessage);

        // Extract text from assistant messages
        if (message.type === 'assistant' && message.message?.content) {
          for (const block of message.message.content) {
            if (block.type === 'text' && block.text) {
              textBlocks.push(block.text);
            }
          }
        }

        // Extract text from result messages
        if (message.type === 'result' && message.result) {
          textBlocks.push(message.result);
        }
      } catch (parseError) {
        // Not JSON, try legacy Python-style parsing
        const message = rawMessage ?? '';
        const resultRegex = /result="([^"]*)"/;

        const resultMatch = message.includes('ResultMessage')
          ? message.match(resultRegex)
          : null;
        if (resultMatch) {
          const normalized = this.normalizeEscapedText(resultMatch[1]);
          textBlocks.push(normalized);
          continue;
        }

        if (message.includes('AssistantMessage') && message.includes('TextBlock(text=')) {
          const start = message.indexOf('TextBlock(text=') + 'TextBlock(text='.length;
          const end = message.indexOf("')", start);
          if (end === -1) {
            continue;
          }

          const extracted = this.normalizeEscapedText(message.slice(start, end));
          if (this.shouldKeepAssistantText(extracted)) {
            textBlocks.push(extracted);
          }
        }
      }
    }

    const fullText = textBlocks.join('\n').trim();
    if (!fullText) {
      return {
        result: 'FAIL',
        feedback: 'レビュー結果を解析できませんでした。',
        suggestions: ['レビュー用のプロンプトや実行ログを確認してください。'],
      };
    }

    const template = this.loadPrompt('parse_review_result');
    const prompt = template.replace('{full_text}', fullText);

    try {
      const response = await this.client.chat.completions.create({
        model: this.model,
        messages: [{ role: 'user', content: prompt }],
        max_tokens: 256,
        temperature: 0,
      });

      const content = response.choices?.[0]?.message?.content ?? '{}';
      const parsed = JSON.parse(content) as { result?: string };
      const result = (parsed.result ?? 'FAIL').toUpperCase();

      return {
        result,
        feedback: fullText,
        suggestions: [],
      };
    } catch (error) {
      const message = (error as Error).message ?? String(error);
      console.warn(`[WARNING] Failed to parse review result via OpenAI: ${message}`);

      const upper = fullText.toUpperCase();
      let inferred = 'FAIL';
      if (upper.includes('PASS_WITH_SUGGESTIONS')) {
        inferred = 'PASS_WITH_SUGGESTIONS';
      } else if (upper.includes('PASS')) {
        inferred = 'PASS';
      }

      return {
        result: inferred,
        feedback: fullText,
        suggestions: [],
      };
    }
  }

  private normalizeEscapedText(text: string): string {
    return text
      .replace(/\\n/g, '\n')
      .replace(/\\t/g, '\t')
      .replace(/\\r/g, '\r')
      .replace(/\\"/g, '"')
      .replace(/\\'/g, "'")
      .replace(/\\\\/g, '\\');
  }

  private shouldKeepAssistantText(content: string): boolean {
    const trimmed = content.trim();
    if (!trimmed) {
      return false;
    }

    const skipPatterns = [
      /^\s*'\s+in\s+message:/i,
      /^\s*\d+行/,
      /^I'll\s+conduct/i,
      /^Let me\s+/i,
      /^Now\s+let\s+me/i,
      /^Based on\s+my\s+.*review.*,\s*let me\s+provide/i,
    ];

    if (skipPatterns.some((pattern) => pattern.test(trimmed))) {
      return false;
    }

    if (trimmed.length < 50 && !trimmed.includes('**結果:')) {
      return false;
    }

    return true;
  }
}
