import fs from 'fs-extra';
import { query, type SDKMessage, type SDKAssistantMessage, type SDKResultMessage } from '@anthropic-ai/claude-agent-sdk';

interface ExecuteTaskOptions {
  prompt: string;
  systemPrompt?: string | null;
  maxTurns?: number;
  workingDirectory?: string;
  verbose?: boolean;
}

const DEFAULT_MAX_TURNS = 50;
const MAX_LOG_PARAM_LENGTH = 500;

export class ClaudeAgentClient {
  private readonly workingDir: string;
  private readonly model?: string;

  constructor(options: { workingDir?: string; model?: string } = {}) {
    this.workingDir = options.workingDir ?? process.cwd();
    this.model = options.model;

    if (!process.env.CLAUDE_CODE_OAUTH_TOKEN) {
      throw new Error(
        [
          'CLAUDE_CODE_OAUTH_TOKEN is not set.',
          'Please export the Claude Code OAuth token before running the workflow.',
          'See DOCKER_AUTH_SETUP.md for instructions.',
        ].join('\n'),
      );
    }
  }

  public getWorkingDirectory(): string {
    return this.workingDir;
  }

  public async executeTask(options: ExecuteTaskOptions): Promise<string[]> {
    const { prompt, systemPrompt = null, maxTurns = DEFAULT_MAX_TURNS, verbose = true } = options;
    const cwd = options.workingDirectory ?? this.workingDir;

    const stream = query({
      prompt,
      options: {
        cwd,
        permissionMode: 'acceptEdits',
        maxTurns,
        model: this.model,
        systemPrompt: systemPrompt ?? undefined,
      },
    });

    const messages: string[] = [];

    for await (const message of stream) {
      messages.push(JSON.stringify(message));
      if (verbose) {
        this.logMessage(message);
      }
    }

    return messages;
  }

  public async executeTaskFromFile(
    promptFile: string,
    templateVars?: Record<string, string>,
    systemPrompt?: string,
    maxTurns?: number,
    verbose?: boolean,
  ): Promise<string[]> {
    const template = fs.readFileSync(promptFile, 'utf-8');
    const prompt = this.fillTemplate(template, templateVars ?? {});
    return this.executeTask({ prompt, systemPrompt, maxTurns, verbose });
  }

  private fillTemplate(template: string, variables: Record<string, string>): string {
    let content = template;
    for (const [key, value] of Object.entries(variables)) {
      content = content.replace(new RegExp(`{${key}}`, 'g'), value);
    }
    return content;
  }

  private logMessage(message: SDKMessage): void {
    switch (message.type) {
      case 'assistant':
        this.logAssistantMessage(message);
        break;
      case 'result':
        this.logResultMessage(message);
        break;
      case 'system': {
        const subtype = 'subtype' in message && message.subtype ? message.subtype : 'system';
        console.log(`[AGENT SYSTEM] ${subtype}`);
        break;
      }
      case 'stream_event':
        this.logStreamEvent(message);
        break;
      default:
        break;
    }
  }

  private logAssistantMessage(message: SDKAssistantMessage): void {
    const contents = message.message.content ?? [];
    for (const block of contents) {
      if (block.type === 'text') {
        const text = block.text?.trim();
        if (text) {
          console.log(`[AGENT THINKING] ${text}`);
        }
      } else if (block.type === 'tool_use') {
        console.log(`[AGENT ACTION] Using tool: ${block.name}`);
        if (block.input && Object.keys(block.input).length > 0) {
          const raw = JSON.stringify(block.input);
          const truncated = raw.length > MAX_LOG_PARAM_LENGTH ? `${raw.slice(0, MAX_LOG_PARAM_LENGTH)}…` : raw;
          console.log(`[AGENT ACTION] Parameters: ${truncated}`);
        }
      }
    }
  }

  private logResultMessage(message: SDKResultMessage): void {
    console.log(
      `[AGENT RESULT] status=${message.subtype ?? 'success'}, turns=${message.num_turns}, duration_ms=${message.duration_ms}`,
    );
    const resultText = (message as Partial<{ result: string }>).result;
    if (typeof resultText === 'string' && resultText.trim().length > 0) {
      console.log(`[AGENT RESULT] ${resultText}`);
    }
  }

  private logStreamEvent(message: SDKMessage): void {
    if (message.type !== 'stream_event') {
      return;
    }

    const event = message.event;
    if (!event || event.type !== 'message_delta') {
      return;
    }

    const delta = event.delta;
    if (!delta || delta.type !== 'message_delta') {
      return;
    }

    for (const block of delta.delta?.content ?? []) {
      if (block.type === 'input_json_delta' && block.partial_input_json) {
        const raw = block.partial_input_json;
        const truncated = raw.length > MAX_LOG_PARAM_LENGTH ? `${raw.slice(0, MAX_LOG_PARAM_LENGTH)}…` : raw;
        console.log(`[AGENT ACTION] Partial parameters: ${truncated}`);
      } else if (block.type === 'text_delta' && block.text_delta?.trim()) {
        console.log(`[AGENT THINKING] ${block.text_delta.trim()}`);
      }
    }
  }
}
