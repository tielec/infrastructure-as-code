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

  constructor(options: { workingDir?: string; model?: string; credentialsPath?: string } = {}) {
    this.workingDir = options.workingDir ?? process.cwd();
    this.model = options.model;

    this.ensureAuthToken(options.credentialsPath);
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

  private ensureAuthToken(credentialsPath?: string): void {
    const resolvedPath = credentialsPath ?? process.env.CLAUDE_CODE_CREDENTIALS_PATH ?? null;

    if (resolvedPath) {
      const token = this.readTokenFromCredentials(resolvedPath);
      process.env.CLAUDE_CODE_OAUTH_TOKEN = token;
      return;
    }

    const token = process.env.CLAUDE_CODE_OAUTH_TOKEN;
    if (!token || !token.trim()) {
      throw new Error(
        [
          'Claude Code credentials are not configured.',
          'Provide a valid credentials file via CLAUDE_CODE_CREDENTIALS_PATH or set CLAUDE_CODE_OAUTH_TOKEN.',
        ].join('\n'),
      );
    }
  }

  private readTokenFromCredentials(credentialsPath: string): string {
    if (!fs.existsSync(credentialsPath)) {
      throw new Error(`Claude Code credentials file not found: ${credentialsPath}`);
    }

    const raw = fs.readFileSync(credentialsPath, 'utf-8').trim();
    if (!raw) {
      throw new Error(`Claude Code credentials file is empty: ${credentialsPath}`);
    }

    let token = raw;
    try {
      const parsed = JSON.parse(raw);
      if (typeof parsed === 'string' && parsed.trim()) {
        token = parsed.trim();
      } else if (parsed && typeof parsed === 'object') {
        const obj = parsed as Record<string, unknown>;
        if (typeof obj.token === 'string') {
          token = (obj.token as string).trim();
        } else if (typeof obj.access_token === 'string') {
          token = (obj.access_token as string).trim();
        } else if (obj.credentials && typeof obj.credentials === 'object') {
          const credObj = obj.credentials as Record<string, unknown>;
          if (typeof credObj.token === 'string') {
            token = (credObj.token as string).trim();
          }
        }
      }
    } catch {
      // Not JSON – treat as raw token string.
    }

    if (!token) {
      throw new Error(`Unable to extract Claude Code token from credentials file: ${credentialsPath}`);
    }

    return token;
  }
}
