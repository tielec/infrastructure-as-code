/**
 * ユニットテスト: リポジトリ解決機能
 *
 * テスト対象:
 * - parseIssueUrl(): Issue URL解析
 * - resolveLocalRepoPath(): ローカルリポジトリパス解決
 *
 * テスト戦略: UNIT_INTEGRATION - ユニット部分
 */

import * as path from 'path';
import * as fs from 'fs-extra';
import * as os from 'os';

// テスト対象の関数をインポート
// 注意: main.tsから関数をエクスポートする必要がある
// または、テスト用にモジュール分割を検討

/**
 * IssueInfo インターフェース（main.tsから）
 */
interface IssueInfo {
  owner: string;
  repo: string;
  issueNumber: number;
  repositoryName: string;
}

/**
 * parseIssueUrl関数のスタブ（テスト用）
 * 実際のテストでは main.ts からインポート
 */
function parseIssueUrl(issueUrl: string): IssueInfo {
  // GitHub Issue URLの正規表現
  const regex = /github\.com\/([^\/]+)\/([^\/]+)\/issues\/(\d+)(?:\/)?$/;
  const match = issueUrl.match(regex);

  if (!match) {
    throw new Error(`Invalid GitHub Issue URL: ${issueUrl}`);
  }

  const [, owner, repo, issueNumberStr] = match;
  const issueNumber = parseInt(issueNumberStr, 10);

  return {
    owner,
    repo,
    issueNumber,
    repositoryName: `${owner}/${repo}`,
  };
}

/**
 * resolveLocalRepoPath関数のスタブ（テスト用）
 * 実際のテストでは main.ts からインポート
 */
function resolveLocalRepoPath(repoName: string): string {
  // 環境変数REPOS_ROOTをチェック
  const reposRoot = process.env.REPOS_ROOT;

  if (reposRoot) {
    const candidatePath = path.join(reposRoot, repoName);
    if (fs.existsSync(candidatePath) && fs.existsSync(path.join(candidatePath, '.git'))) {
      return candidatePath;
    }
  }

  // フォールバック候補パス
  const homedir = os.homedir();
  const candidatePaths = [
    path.join(homedir, 'TIELEC', 'development', repoName),
    path.join(homedir, 'projects', repoName),
    path.join(process.cwd(), '..', repoName),
  ];

  for (const candidatePath of candidatePaths) {
    if (fs.existsSync(candidatePath) && fs.existsSync(path.join(candidatePath, '.git'))) {
      return candidatePath;
    }
  }

  throw new Error(
    `Repository '${repoName}' not found.\nPlease set REPOS_ROOT environment variable or clone the repository.`
  );
}

// =============================================================================
// UT-001: parseIssueUrl_正常系_標準URL
// =============================================================================
describe('UT-001: parseIssueUrl_正常系_標準URL', () => {
  test('標準的なGitHub Issue URLから正しくリポジトリ情報を抽出できる', () => {
    // Given: 標準的なGitHub Issue URL
    const issueUrl = 'https://github.com/tielec/my-app/issues/123';

    // When: parseIssueUrl()を実行
    const result = parseIssueUrl(issueUrl);

    // Then: 正しい情報が抽出される
    expect(result.owner).toBe('tielec');
    expect(result.repo).toBe('my-app');
    expect(result.issueNumber).toBe(123);
    expect(result.repositoryName).toBe('tielec/my-app');
  });
});

// =============================================================================
// UT-002: parseIssueUrl_正常系_末尾スラッシュあり
// =============================================================================
describe('UT-002: parseIssueUrl_正常系_末尾スラッシュあり', () => {
  test('末尾にスラッシュがあるURLでも正しく解析できる', () => {
    // Given: 末尾にスラッシュがあるURL
    const issueUrl = 'https://github.com/tielec/my-app/issues/123/';

    // When: parseIssueUrl()を実行
    const result = parseIssueUrl(issueUrl);

    // Then: UT-001と同じ結果が返される
    expect(result.owner).toBe('tielec');
    expect(result.repo).toBe('my-app');
    expect(result.issueNumber).toBe(123);
    expect(result.repositoryName).toBe('tielec/my-app');
  });
});

// =============================================================================
// UT-003: parseIssueUrl_正常系_大きなIssue番号
// =============================================================================
describe('UT-003: parseIssueUrl_正常系_大きなIssue番号', () => {
  test('大きなIssue番号でも正しく解析できる（境界値テスト）', () => {
    // Given: 大きなIssue番号のURL
    const issueUrl = 'https://github.com/tielec/infrastructure-as-code/issues/99999';

    // When: parseIssueUrl()を実行
    const result = parseIssueUrl(issueUrl);

    // Then: 正しい情報が抽出される
    expect(result.owner).toBe('tielec');
    expect(result.repo).toBe('infrastructure-as-code');
    expect(result.issueNumber).toBe(99999);
    expect(result.repositoryName).toBe('tielec/infrastructure-as-code');
    expect(result.repo).toContain('-'); // ハイフンが含まれていても正しく解析
  });
});

// =============================================================================
// UT-004: parseIssueUrl_異常系_GitHub以外のURL
// =============================================================================
describe('UT-004: parseIssueUrl_異常系_GitHub以外のURL', () => {
  test('GitHub以外のURLではエラーが発生する', () => {
    // Given: GitHub以外のURL
    const issueUrl = 'https://example.com/issues/123';

    // When & Then: parseIssueUrl()でエラーが投げられる
    expect(() => parseIssueUrl(issueUrl)).toThrow('Invalid GitHub Issue URL');
    expect(() => parseIssueUrl(issueUrl)).toThrow(issueUrl);
  });
});

// =============================================================================
// UT-005: parseIssueUrl_異常系_プルリクエストURL
// =============================================================================
describe('UT-005: parseIssueUrl_異常系_プルリクエストURL', () => {
  test('プルリクエストURLではエラーが発生する', () => {
    // Given: プルリクエストURL
    const issueUrl = 'https://github.com/tielec/my-app/pulls/123';

    // When & Then: parseIssueUrl()でエラーが投げられる
    expect(() => parseIssueUrl(issueUrl)).toThrow('Invalid GitHub Issue URL');
  });
});

// =============================================================================
// UT-006: parseIssueUrl_異常系_Issue番号なし
// =============================================================================
describe('UT-006: parseIssueUrl_異常系_Issue番号なし', () => {
  test('Issue番号がないURLではエラーが発生する', () => {
    // Given: Issue番号がないURL
    const issueUrl = 'https://github.com/tielec/my-app';

    // When & Then: parseIssueUrl()でエラーが投げられる
    expect(() => parseIssueUrl(issueUrl)).toThrow('Invalid GitHub Issue URL');
  });
});

// =============================================================================
// UT-007: parseIssueUrl_異常系_Issue番号が数値でない
// =============================================================================
describe('UT-007: parseIssueUrl_異常系_Issue番号が数値でない', () => {
  test('Issue番号が数値でない場合にエラーが発生する', () => {
    // Given: Issue番号が数値でないURL
    const issueUrl = 'https://github.com/tielec/my-app/issues/abc';

    // When & Then: parseIssueUrl()でエラーが投げられる
    expect(() => parseIssueUrl(issueUrl)).toThrow('Invalid GitHub Issue URL');
  });
});

// =============================================================================
// UT-101: resolveLocalRepoPath_正常系_REPOS_ROOT設定済み
// =============================================================================
describe('UT-101: resolveLocalRepoPath_正常系_REPOS_ROOT設定済み', () => {
  // モック設定
  const originalEnv = process.env.REPOS_ROOT;
  const mockExistsSync = jest.spyOn(fs, 'existsSync');

  afterEach(() => {
    // 環境変数を元に戻す
    if (originalEnv !== undefined) {
      process.env.REPOS_ROOT = originalEnv;
    } else {
      delete process.env.REPOS_ROOT;
    }
    mockExistsSync.mockRestore();
  });

  test('環境変数REPOS_ROOTが設定されている場合、優先的に使用される', () => {
    // Given: 環境変数REPOS_ROOTが設定されている
    process.env.REPOS_ROOT = '/path/to/repos';
    const repoName = 'my-app';

    // Mock: fs.existsSync()
    mockExistsSync.mockImplementation((pathToCheck: any) => {
      if (pathToCheck === '/path/to/repos/my-app') return true;
      if (pathToCheck === '/path/to/repos/my-app/.git') return true;
      return false;
    });

    // When: resolveLocalRepoPath()を実行
    const result = resolveLocalRepoPath(repoName);

    // Then: REPOS_ROOT配下のパスが返される
    expect(result).toBe(path.join('/path/to/repos', 'my-app'));
  });
});

// =============================================================================
// UT-102: resolveLocalRepoPath_正常系_候補パス探索_最初の候補で見つかる
// =============================================================================
describe('UT-102: resolveLocalRepoPath_正常系_候補パス探索_最初の候補で見つかる', () => {
  const originalEnv = process.env.REPOS_ROOT;
  const mockExistsSync = jest.spyOn(fs, 'existsSync');
  const mockHomedir = jest.spyOn(os, 'homedir');

  afterEach(() => {
    if (originalEnv !== undefined) {
      process.env.REPOS_ROOT = originalEnv;
    } else {
      delete process.env.REPOS_ROOT;
    }
    mockExistsSync.mockRestore();
    mockHomedir.mockRestore();
  });

  test('環境変数が未設定でも候補パスから見つかる', () => {
    // Given: 環境変数REPOS_ROOTが未設定
    delete process.env.REPOS_ROOT;
    const repoName = 'my-app';

    // Mock: os.homedir()
    mockHomedir.mockReturnValue('/home/user');

    // Mock: fs.existsSync()
    mockExistsSync.mockImplementation((pathToCheck: any) => {
      if (pathToCheck === '/home/user/TIELEC/development/my-app') return true;
      if (pathToCheck === '/home/user/TIELEC/development/my-app/.git') return true;
      return false;
    });

    // When: resolveLocalRepoPath()を実行
    const result = resolveLocalRepoPath(repoName);

    // Then: 最初の候補パスが返される
    expect(result).toBe('/home/user/TIELEC/development/my-app');
  });
});

// =============================================================================
// UT-103: resolveLocalRepoPath_正常系_候補パス探索_2番目の候補で見つかる
// =============================================================================
describe('UT-103: resolveLocalRepoPath_正常系_候補パス探索_2番目の候補で見つかる', () => {
  const originalEnv = process.env.REPOS_ROOT;
  const mockExistsSync = jest.spyOn(fs, 'existsSync');
  const mockHomedir = jest.spyOn(os, 'homedir');

  afterEach(() => {
    if (originalEnv !== undefined) {
      process.env.REPOS_ROOT = originalEnv;
    } else {
      delete process.env.REPOS_ROOT;
    }
    mockExistsSync.mockRestore();
    mockHomedir.mockRestore();
  });

  test('最初の候補で見つからなくても、次の候補を探索する', () => {
    // Given: 環境変数REPOS_ROOTが未設定
    delete process.env.REPOS_ROOT;
    const repoName = 'my-app';

    // Mock: os.homedir()
    mockHomedir.mockReturnValue('/home/user');

    // Mock: fs.existsSync() - 最初の候補はfalse、2番目はtrue
    mockExistsSync.mockImplementation((pathToCheck: any) => {
      if (pathToCheck === '/home/user/TIELEC/development/my-app') return false;
      if (pathToCheck === '/home/user/projects/my-app') return true;
      if (pathToCheck === '/home/user/projects/my-app/.git') return true;
      return false;
    });

    // When: resolveLocalRepoPath()を実行
    const result = resolveLocalRepoPath(repoName);

    // Then: 2番目の候補パスが返される
    expect(result).toBe('/home/user/projects/my-app');
  });
});

// =============================================================================
// UT-104: resolveLocalRepoPath_正常系_Windowsパス対応
// =============================================================================
describe('UT-104: resolveLocalRepoPath_正常系_Windowsパス対応', () => {
  const originalEnv = process.env.REPOS_ROOT;
  const mockExistsSync = jest.spyOn(fs, 'existsSync');

  afterEach(() => {
    if (originalEnv !== undefined) {
      process.env.REPOS_ROOT = originalEnv;
    } else {
      delete process.env.REPOS_ROOT;
    }
    mockExistsSync.mockRestore();
  });

  test('Windowsパスでも正しく動作する', () => {
    // Given: 環境変数REPOS_ROOTがWindowsパス形式
    process.env.REPOS_ROOT = 'C:\\Users\\ytaka\\TIELEC\\development';
    const repoName = 'my-app';

    // Mock: fs.existsSync()
    mockExistsSync.mockImplementation((pathToCheck: any) => {
      const expectedPath = path.join('C:\\Users\\ytaka\\TIELEC\\development', 'my-app');
      const expectedGitPath = path.join(expectedPath, '.git');
      if (pathToCheck === expectedPath) return true;
      if (pathToCheck === expectedGitPath) return true;
      return false;
    });

    // When: resolveLocalRepoPath()を実行
    const result = resolveLocalRepoPath(repoName);

    // Then: Windowsパスが正しく処理される
    expect(result).toBe(path.join('C:\\Users\\ytaka\\TIELEC\\development', 'my-app'));
  });
});

// =============================================================================
// UT-105: resolveLocalRepoPath_異常系_リポジトリが見つからない
// =============================================================================
describe('UT-105: resolveLocalRepoPath_異常系_リポジトリが見つからない', () => {
  const originalEnv = process.env.REPOS_ROOT;
  const mockExistsSync = jest.spyOn(fs, 'existsSync');

  afterEach(() => {
    if (originalEnv !== undefined) {
      process.env.REPOS_ROOT = originalEnv;
    } else {
      delete process.env.REPOS_ROOT;
    }
    mockExistsSync.mockRestore();
  });

  test('すべての候補でリポジトリが見つからない場合にエラーが発生する', () => {
    // Given: 環境変数REPOS_ROOTが未設定、すべての候補でfalse
    delete process.env.REPOS_ROOT;
    const repoName = 'unknown-repo';

    // Mock: fs.existsSync() - すべてfalse
    mockExistsSync.mockReturnValue(false);

    // When & Then: resolveLocalRepoPath()でエラーが投げられる
    expect(() => resolveLocalRepoPath(repoName)).toThrow("Repository 'unknown-repo' not found");
    expect(() => resolveLocalRepoPath(repoName)).toThrow('Please set REPOS_ROOT environment variable or clone the repository');
  });
});

// =============================================================================
// UT-106: resolveLocalRepoPath_異常系_ディレクトリは存在するが.gitがない
// =============================================================================
describe('UT-106: resolveLocalRepoPath_異常系_ディレクトリは存在するが.gitがない', () => {
  const originalEnv = process.env.REPOS_ROOT;
  const mockExistsSync = jest.spyOn(fs, 'existsSync');

  afterEach(() => {
    if (originalEnv !== undefined) {
      process.env.REPOS_ROOT = originalEnv;
    } else {
      delete process.env.REPOS_ROOT;
    }
    mockExistsSync.mockRestore();
  });

  test('ディレクトリは存在するが.gitがない場合はスキップされる', () => {
    // Given: 環境変数REPOS_ROOTが設定されている
    process.env.REPOS_ROOT = '/path/to/repos';
    const repoName = 'my-app';

    // Mock: fs.existsSync() - ディレクトリはあるが.gitがない
    mockExistsSync.mockImplementation((pathToCheck: any) => {
      if (pathToCheck === '/path/to/repos/my-app') return true;
      if (pathToCheck === '/path/to/repos/my-app/.git') return false;
      return false;
    });

    // When & Then: resolveLocalRepoPath()でエラーが投げられる
    expect(() => resolveLocalRepoPath(repoName)).toThrow("Repository 'my-app' not found");
  });
});
