from typing import Dict, Optional, Tuple, List
import os
import base64
from github import Github, GithubException, GithubIntegration
import difflib
import jwt
import time
import requests

class GitHubClientError(Exception):
    """GitHub APIに関連するエラーを表すカスタム例外"""
    pass

class GitHubClient:
    """GitHub APIとのインタラクションを管理するクラス"""

    def __init__(self, auth_method="pat", app_id=None, private_key_path=None, installation_id=None, token=None):
        """
        GitHubクライアントを初期化
        
        Args:
            auth_method (str): 認証方法 ("pat" または "app")
            app_id (int): GitHub Appのアプリケーション ID (auth_method="app"の場合)
            private_key_path (str): GitHub Appの秘密鍵のパス (auth_method="app"の場合)
            installation_id (int): GitHub AppのインストールID (auth_method="app"の場合)
            token (str): 直接提供されたアクセストークン (Jenkinsなどの外部システムから提供された場合)
        
        Raises:
            GitHubClientError: 初期化に失敗した場合
        """
        self.auth_method = auth_method
        
        # 直接トークンが提供された場合
        if token:
            self.token = token
            self.client = Github(self.token)
        elif auth_method == "pat":
            self._init_with_pat()
        elif auth_method == "app":
            self._init_with_app(app_id, private_key_path, installation_id)
        else:
            raise GitHubClientError(f"Invalid authentication method: {auth_method}")
        
        self._rate_limit_check()

    def _init_with_pat(self):
        """個人アクセストークン(PAT)を使用して初期化"""
        self.token = os.getenv('GITHUB_PAT')
        if not self.token:
            raise GitHubClientError("GITHUB_PAT environment variable is not set")
        
        self.client = Github(self.token)

    def _init_with_app(self, app_id, private_key_path, installation_id):
        """GitHub Appを使用して初期化"""
        # 直接アクセストークンが環境変数で提供されている場合はそれを使用
        self.token = os.getenv('GITHUB_ACCESS_TOKEN')
        if self.token:
            self.client = Github(self.token)
            return
            
        # 必要なパラメータのチェック
        if not app_id:
            app_id = os.getenv('GITHUB_APP_ID')
            if not app_id:
                raise GitHubClientError("app_id is required for GitHub App authentication")
        
        if not private_key_path:
            private_key_path = os.getenv('GITHUB_PRIVATE_KEY_PATH')
            if not private_key_path:
                raise GitHubClientError("private_key_path is required for GitHub App authentication")
        
        if not installation_id:
            installation_id = os.getenv('GITHUB_INSTALLATION_ID')
            if not installation_id:
                raise GitHubClientError("installation_id is required for GitHub App authentication")
        
        try:
            # 数値に変換
            self.app_id = int(app_id)
            self.installation_id = int(installation_id)
            
            # 秘密鍵を読み込む
            with open(private_key_path, 'r') as key_file:
                self.private_key = key_file.read()
            
            # GitHub Integrationオブジェクトを作成
            self.integration = GithubIntegration(self.app_id, self.private_key)
            
            # インストールのアクセストークンを取得
            self.token = self.integration.get_access_token(self.installation_id).token
            
            # Githubクライアントを初期化
            self.client = Github(self.token)
        except Exception as e:
            raise GitHubClientError(f"Failed to initialize GitHub App: {str(e)}")

    def _refresh_token_if_needed(self):
        """
        GitHub Appのトークンを必要に応じてリフレッシュ
        """
        if self.auth_method != "app" or os.getenv('GITHUB_ACCESS_TOKEN'):
            # 環境変数からトークンが直接提供されている場合はリフレッシュ不要
            return
            
        try:
            # GitHub Appのトークンは有効期限が1時間なので、必要に応じて更新
            self.token = self.integration.get_access_token(self.installation_id).token
            self.client = Github(self.token)
        except Exception as e:
            raise GitHubClientError(f"Failed to refresh GitHub App token: {str(e)}")

    def get_file_content(self, owner: str, repo: str, path: str, 
                        base_sha: str, head_sha: str) -> Tuple[str, str]:
        """
        指定されたファイルの変更前後の内容を取得
        
        Args:
            owner (str): リポジトリオーナー
            repo (str): リポジトリ名
            path (str): ファイルパス
            base_sha (str): ベースコミットのSHA
            head_sha (str): ヘッドコミットのSHA
        
        Returns:
            Tuple[str, str]: (変更前の内容, 変更後の内容)
        
        Raises:
            GitHubClientError: API呼び出しに失敗した場合
        """
        # GitHub Appを使用している場合はトークンをリフレッシュ
        if self.auth_method == "app":
            self._refresh_token_if_needed()
            
        try:
            repository = self.client.get_repo(f"{owner}/{repo}")
            
            # 変更前のファイル内容を取得
            try:
                base_content = self._get_file_at_commit(repository, path, base_sha)
            except GithubException:
                base_content = ""  # 新規ファイルの場合は空文字
            
            # 変更後のファイル内容を取得
            try:
                head_content = self._get_file_at_commit(repository, path, head_sha)
            except GithubException:
                head_content = ""  # 削除されたファイルの場合は空文字
            
            return base_content, head_content
            
        except GithubException as e:
            self._handle_github_exception(e)
        except Exception as e:
            raise GitHubClientError(f"Failed to get file content: {str(e)}")

    def get_change_context(self, before_content: str, after_content: str, 
                          patch: Optional[str], context_lines: int = 3) -> Dict[str, List[str]]:
        """
        変更箇所の前後のコンテキストを取得
        
        Args:
            before_content (str): 変更前のファイル内容
            after_content (str): 変更後のファイル内容
            patch (str): GitHub APIから取得した差分パッチ
            context_lines (int): 変更箇所の前後何行を含めるか
        
        Returns:
            Dict[str, List[str]]: 
                {
                    'before': [変更前の該当箇所の前後n行],
                    'after': [変更後の該当箇所の前後n行],
                    'changes': [{'type': 'add|remove|modify', 'content': '行の内容'}]
                }
        """
        if not patch:
            return {
                'before': before_content.splitlines() if before_content else [],
                'after': after_content.splitlines() if after_content else [],
                'changes': []
            }

        # 変更前後のファイルを行に分割
        before_lines = before_content.splitlines()
        after_lines = after_content.splitlines()

        # パッチから変更された行番号を抽出
        changed_lines = self._parse_patch(patch)
        
        # コンテキスト情報を収集
        context = {
            'before': [],
            'after': [],
            'changes': []
        }

        # 変更前のコンテキスト
        for line_info in changed_lines.get('before', []):
            line_num = line_info['line'] - 1  # 0-based indexing
            start = max(0, line_num - context_lines)
            end = min(len(before_lines), line_num + context_lines + 1)
            context['before'].extend(before_lines[start:end])
            context['changes'].append({
                'type': 'remove',
                'content': before_lines[line_num] if line_num < len(before_lines) else ''
            })

        # 変更後のコンテキスト
        for line_info in changed_lines.get('after', []):
            line_num = line_info['line'] - 1  # 0-based indexing
            start = max(0, line_num - context_lines)
            end = min(len(after_lines), line_num + context_lines + 1)
            context['after'].extend(after_lines[start:end])
            context['changes'].append({
                'type': 'add',
                'content': after_lines[line_num] if line_num < len(after_lines) else ''
            })

        # 重複を除去
        context['before'] = list(dict.fromkeys(context['before']))
        context['after'] = list(dict.fromkeys(context['after']))

        return context

    def _get_file_at_commit(self, repository, path: str, sha: str) -> str:
        """特定のコミットでのファイル内容を取得"""
        self._rate_limit_check()
        content = repository.get_contents(path, ref=sha)
        if isinstance(content, list):
            raise GitHubClientError(f"Path {path} is a directory")
        
        return base64.b64decode(content.content).decode('utf-8')

    def _parse_patch(self, patch: str) -> Dict[str, List[Dict[str, int]]]:
        """
        パッチから変更された行の情報を抽出
        
        Returns:
            Dict[str, List[Dict[str, int]]]: 
                {
                    'before': [{'line': 行番号}],
                    'after': [{'line': 行番号}]
                }
        """
        result = {
            'before': [],
            'after': []
        }
        
        if not patch:
            return result

        current_line_before = 0
        current_line_after = 0

        for line in patch.splitlines():
            if line.startswith('@@'):
                # パッチのヘッダーから開始行番号を取得
                try:
                    changes = line.split('@@')[1].strip()
                    before, after = changes.split(' ')
                    current_line_before = abs(int(before.split(',')[0]))
                    current_line_after = int(after.split(',')[0])
                except (IndexError, ValueError):
                    continue
            elif line.startswith('-'):
                result['before'].append({'line': current_line_before})
                current_line_before += 1
            elif line.startswith('+'):
                result['after'].append({'line': current_line_after})
                current_line_after += 1
            else:
                current_line_before += 1
                current_line_after += 1

        return result

    def _rate_limit_check(self):
        """
        レート制限をチェックし、制限に近づいている場合は警告を出す
        
        Raises:
            GitHubClientError: レート制限に達している場合
        """
        try:
            rate_limit = self.client.get_rate_limit()
            remaining = rate_limit.core.remaining
            
            if remaining < 100:
                print(f"Warning: GitHub API rate limit is low. {remaining} requests remaining.")
            if remaining <= 0:
                reset_time = rate_limit.core.reset.strftime('%Y-%m-%d %H:%M:%S')
                raise GitHubClientError(
                    f"GitHub API rate limit exceeded. Resets at {reset_time}"
                )
        except GithubException as e:
            self._handle_github_exception(e)

    def _handle_github_exception(self, e: GithubException):
        """GitHub APIの例外を適切にハンドリング"""
        if e.status == 403 and 'rate limit exceeded' in str(e.data):
            raise GitHubClientError(
                f"GitHub API rate limit exceeded. Reset time: {e.headers.get('X-RateLimit-Reset')}"
            )
        elif e.status == 404:
            raise GitHubClientError("Requested resource not found")
        else:
            raise GitHubClientError(f"GitHub API error: {str(e)}")
