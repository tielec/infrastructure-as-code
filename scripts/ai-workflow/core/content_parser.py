"""Claude APIベースのコンテンツ解析モジュール

正規表現による脆弱な判定を、Claude Messages APIによる
自然言語理解ベースの高精度な抽出に置き換える。

使用例:
    >>> from core.content_parser import ClaudeContentParser
    >>> parser = ClaudeContentParser()
    >>> decisions = parser.extract_design_decisions(planning_content)
    >>> print(decisions)
    {'implementation_strategy': 'CREATE', 'test_strategy': 'UNIT_INTEGRATION', ...}
"""
import os
import json
import anthropic
from pathlib import Path
from typing import Dict, Any, List, Optional


class ClaudeContentParser:
    """Claude Messages APIを使用したコンテンツ解析"""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514"):
        """
        初期化

        Args:
            api_key: Anthropic API Key（省略時は環境変数から取得）
            model: 使用するClaudeモデル（デフォルト: claude-sonnet-4-20250514）

        Raises:
            ValueError: API キーが指定されず、環境変数も設定されていない場合
        """
        # API キーの優先順位:
        # 1. 引数で明示的に指定されたキー
        # 2. ANTHROPIC_API_KEY 環境変数
        #
        # 注意: CLAUDE_CODE_OAUTH_TOKEN (OAuth トークン) は使用できません。
        # ClaudeContentParser は anthropic.Anthropic() クライアントを使用しており、
        # これは Anthropic API Key (sk-ant-api03-...) を必要とします。
        resolved_api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")

        if not resolved_api_key:
            raise ValueError(
                "Anthropic API キーが設定されていません。以下のいずれかの方法で設定してください:\n"
                "1. ClaudeContentParser(api_key='your-key') で明示的に指定\n"
                "2. 環境変数 ANTHROPIC_API_KEY を設定\n"
                "\n"
                "注意: CLAUDE_CODE_OAUTH_TOKEN (OAuth トークン) は使用できません。\n"
                "Anthropic API Key は https://console.anthropic.com/settings/keys で取得できます。"
            )

        self.client = anthropic.Anthropic(api_key=resolved_api_key)
        self.model = model

        # プロンプトディレクトリのパスを設定
        self.prompt_dir = Path(__file__).parent.parent / 'prompts' / 'content_parser'

    def _load_prompt(self, prompt_name: str) -> str:
        """
        プロンプトファイルを読み込み

        Args:
            prompt_name: プロンプトファイル名（拡張子なし）

        Returns:
            str: プロンプトの内容
        """
        prompt_file = self.prompt_dir / f'{prompt_name}.txt'
        return prompt_file.read_text(encoding='utf-8')

    def extract_design_decisions(self, document_content: str) -> Dict[str, str]:
        """
        設計書/計画書から戦略判断を抽出

        Args:
            document_content: 設計書または計画書の内容（Markdown形式）

        Returns:
            Dict[str, str]: 戦略判断
                - implementation_strategy: CREATE/EXTEND/REFACTOR
                - test_strategy: UNIT_ONLY/INTEGRATION_ONLY/BDD_ONLY/UNIT_INTEGRATION/UNIT_BDD/INTEGRATION_BDD/ALL
                - test_code_strategy: EXTEND_TEST/CREATE_TEST/BOTH_TEST

        Example:
            >>> parser = ClaudeContentParser()
            >>> doc = '''
            ... ## 実装戦略: CREATE
            ... 新規機能として実装します。
            ... ## テスト戦略: UNIT_INTEGRATION
            ... ユニットテストと統合テストを実施します。
            ... ## テストコード戦略: CREATE_TEST
            ... 新規テストコードを作成します。
            ... '''
            >>> decisions = parser.extract_design_decisions(doc)
            >>> decisions['implementation_strategy']
            'CREATE'
        """
        # プロンプトファイルを読み込み
        prompt_template = self._load_prompt('extract_design_decisions')
        prompt = prompt_template.replace('{document_content}', document_content)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # レスポンスからテキストを取得
            response_text = response.content[0].text.strip()

            # JSONをパース
            decisions = json.loads(response_text)

            # null値を除外
            return {k: v for k, v in decisions.items() if v is not None}

        except json.JSONDecodeError as e:
            print(f"[WARNING] 戦略判断の抽出に失敗しました（JSONパースエラー）: {e}")
            print(f"[DEBUG] Response: {response_text}")
            return {}
        except Exception as e:
            print(f"[WARNING] 戦略判断の抽出に失敗しました: {e}")
            return {}

    def parse_review_result(self, messages: List[str]) -> Dict[str, Any]:
        """
        Claude Agent SDKのレスポンスメッセージからレビュー結果を抽出

        Args:
            messages: Claude Agent SDKからのレスポンスメッセージ

        Returns:
            Dict[str, Any]: レビュー結果
                - result: str - PASS/PASS_WITH_SUGGESTIONS/FAIL
                - feedback: str - フィードバック全文
                - suggestions: List[str] - 改善提案一覧

        Example:
            >>> parser = ClaudeContentParser()
            >>> messages = ["AssistantMessage(TextBlock(text='**判定: PASS**\\n\\n素晴らしい実装です。'))"]
            >>> result = parser.parse_review_result(messages)
            >>> result['result']
            'PASS'
        """
        # AssistantMessageのTextBlockとResultMessageのresultを抽出
        text_blocks = []
        import re

        for message in messages:
            # ResultMessageのresultフィールドを優先的に抽出
            if 'ResultMessage' in message and 'result="' in message:
                result_start = message.find('result="') + 8
                # 最後の"を見つける（エスケープされた\"は除外）
                result_end = -1
                i = result_start
                while i < len(message):
                    if message[i] == '"' and (i == result_start or message[i-1] != '\\'):
                        result_end = i
                        break
                    i += 1

                if result_end != -1:
                    result_content = message[result_start:result_end]
                    # エスケープシーケンスを置換
                    result_content = result_content.replace('\\n', '\n')
                    result_content = result_content.replace('\\t', '\t')
                    result_content = result_content.replace('\\r', '\r')
                    result_content = result_content.replace('\\"', '"')
                    result_content = result_content.replace("\\'", "'")
                    result_content = result_content.replace('\\\\', '\\')

                    # ResultMessageのresultは完全なレビュー結果なので、そのまま使用
                    text_blocks.append(result_content)
                    continue

            # AssistantMessageのTextBlockを抽出（従来の処理）
            if 'AssistantMessage' in message and 'TextBlock(text=' in message:
                text_start = message.find('TextBlock(text=') + 16
                text_end = message.find('\')', text_start)
                if text_end == -1:
                    continue

                text_content = message[text_start:text_end]

                # エスケープシーケンスを置換
                text_content = text_content.replace('\\n', '\n')
                text_content = text_content.replace('\\t', '\t')
                text_content = text_content.replace('\\r', '\r')
                text_content = text_content.replace("\\'", "'")
                text_content = text_content.replace('\\\\', '\\')

                # デバッグメッセージや前置きを除外
                skip_patterns = [
                    r"^\s*'\s+in\s+message:",
                    r"^\s*\d+→",
                    r"^I'll\s+conduct",
                    r"^Let me\s+",
                    r"^Now\s+let\s+me",
                    r"^Based on\s+my\s+.*review.*,\s*let me\s+provide",
                ]

                should_skip = False
                for skip_pattern in skip_patterns:
                    if re.match(skip_pattern, text_content.strip(), re.IGNORECASE):
                        should_skip = True
                        break

                # 短すぎるメッセージも除外（ただし判定キーワードが含まれている場合は除外しない）
                if len(text_content.strip()) < 50 and '**判定:' not in text_content:
                    should_skip = True

                if not should_skip:
                    text_blocks.append(text_content)

        # テキストブロックを結合
        full_text = "\n".join(text_blocks)

        if not full_text.strip():
            return {
                'result': 'FAIL',
                'feedback': 'レビュー結果が空でした。',
                'suggestions': ['レビュープロンプトを確認してください。']
            }

        # プロンプトファイルを読み込み
        prompt_template = self._load_prompt('parse_review_result')
        prompt = prompt_template.replace('{full_text}', full_text)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=256,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # レスポンスからテキストを取得
            response_text = response.content[0].text.strip()

            # JSONをパース
            parsed = json.loads(response_text)
            result_value = parsed.get('result', 'FAIL').upper()

            return {
                'result': result_value,
                'feedback': full_text.strip(),
                'suggestions': []
            }

        except json.JSONDecodeError as e:
            print(f"[WARNING] レビュー結果の抽出に失敗しました（JSONパースエラー）: {e}")
            print(f"[DEBUG] Response: {response_text}")
            # フォールバック: テキストに'PASS'が含まれているか確認
            if 'PASS' in full_text.upper():
                if 'PASS_WITH_SUGGESTIONS' in full_text.upper():
                    result_value = 'PASS_WITH_SUGGESTIONS'
                else:
                    result_value = 'PASS'
            else:
                result_value = 'FAIL'

            return {
                'result': result_value,
                'feedback': full_text.strip(),
                'suggestions': []
            }
        except Exception as e:
            print(f"[WARNING] レビュー結果の抽出に失敗しました: {e}")
            return {
                'result': 'FAIL',
                'feedback': f'レビュー結果の抽出中にエラーが発生しました: {str(e)}\n\n{full_text[:500]}',
                'suggestions': ['エラーログを確認してください。']
            }
