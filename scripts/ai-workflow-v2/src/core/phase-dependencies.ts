import fs from 'fs-extra';
import { resolve as resolvePath } from 'node:path';
import { MetadataManager } from './metadata-manager.js';
import { PhaseName, PhaseStatus } from '../types.js';

export const PHASE_DEPENDENCIES: Record<PhaseName, PhaseName[]> = {
  planning: [],
  requirements: ['planning'],
  design: ['requirements'],
  test_scenario: ['requirements', 'design'],
  implementation: ['requirements', 'design', 'test_scenario'],
  test_implementation: ['implementation'],
  testing: ['test_implementation'],
  documentation: ['implementation'],
  report: ['requirements', 'design', 'implementation', 'testing', 'documentation'],
  evaluation: ['report'],
};

export const PHASE_PRESETS: Record<string, PhaseName[]> = {
  'requirements-only': ['requirements'],
  'design-phase': ['requirements', 'design'],
  'implementation-phase': ['requirements', 'design', 'test_scenario', 'implementation'],
  'full-workflow': [
    'planning',
    'requirements',
    'design',
    'test_scenario',
    'implementation',
    'test_implementation',
    'testing',
    'documentation',
    'report',
    'evaluation',
  ],
};

export interface DependencyValidationOptions {
  skipCheck?: boolean;
  ignoreViolations?: boolean;
}

export interface DependencyValidationResult {
  valid: boolean;
  error?: string;
  warning?: string;
  ignored?: boolean;
  missing_phases?: PhaseName[];
}

export const validatePhaseDependencies = (
  phaseName: PhaseName,
  metadataManager: MetadataManager,
  options: DependencyValidationOptions = {},
): DependencyValidationResult => {
  const { skipCheck = false, ignoreViolations = false } = options;

  if (!(phaseName in PHASE_DEPENDENCIES)) {
    throw new Error(`Invalid phase name: ${phaseName}`);
  }

  if (skipCheck) {
    return { valid: true };
  }

  const required = PHASE_DEPENDENCIES[phaseName] ?? [];
  if (required.length === 0) {
    return { valid: true };
  }

  const missing = required.filter((phase) => {
    let status: PhaseStatus;
    try {
      status = metadataManager.getPhaseStatus(phase);
    } catch {
      return true;
    }
    return status !== 'completed';
  });

  if (missing.length === 0) {
    return { valid: true };
  }

  const message = `Phase '${phaseName}' requires ${missing
    .map((p) => `'${p}'`)
    .join(', ')} to be completed first.`;

  if (ignoreViolations) {
    return {
      valid: true,
      warning: message,
      ignored: true,
      missing_phases: missing,
    };
  }

  return {
    valid: false,
    error: message,
    missing_phases: missing,
  };
};

export const detectCircularDependencies = (): PhaseName[][] => {
  const visited = new Set<PhaseName>();
  const stack: PhaseName[] = [];
  const cycles: PhaseName[][] = [];

  const dfs = (phase: PhaseName) => {
    visited.add(phase);
    stack.push(phase);

    for (const dependency of PHASE_DEPENDENCIES[phase] ?? []) {
      if (!visited.has(dependency)) {
        dfs(dependency);
      } else if (stack.includes(dependency)) {
        const cycleStart = stack.indexOf(dependency);
        cycles.push([...stack.slice(cycleStart), dependency]);
      }
    }

    stack.pop();
  };

  (Object.keys(PHASE_DEPENDENCIES) as PhaseName[]).forEach((phase) => {
    if (!visited.has(phase)) {
      dfs(phase);
    }
  });

  return cycles;
};

export interface ExternalDocumentValidation {
  valid: boolean;
  absolute_path?: string;
  error?: string;
}

export const validateExternalDocument = (
  filePath: string,
  repoRoot?: string,
): ExternalDocumentValidation => {
  try {
    const absolutePath = resolvePath(filePath);

    if (!fs.existsSync(absolutePath)) {
      return { valid: false, error: `File not found: ${filePath}` };
    }

    const extension = absolutePath.split('.').pop()?.toLowerCase();
    if (!extension || !['md', 'txt'].includes(extension)) {
      return {
        valid: false,
        error: `Invalid file format: .${extension ?? 'unknown'}. Only .md and .txt are allowed`,
      };
    }

    const stats = fs.statSync(absolutePath);
    if (stats.size > 10 * 1024 * 1024) {
      return {
        valid: false,
        error: `File size exceeds 10MB limit (actual: ${(stats.size / (1024 * 1024)).toFixed(1)}MB)`,
      };
    }

    if (repoRoot) {
      const normalizedRoot = resolvePath(repoRoot);
      if (!resolvePath(absolutePath).startsWith(normalizedRoot)) {
        return {
          valid: false,
          error: 'File must be within the repository',
        };
      }
    }

    return {
      valid: true,
      absolute_path: absolutePath,
    };
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === 'EACCES') {
      return { valid: false, error: `Permission denied: ${filePath}` };
    }
    return { valid: false, error: `Unexpected error: ${(error as Error).message}` };
  }
};
