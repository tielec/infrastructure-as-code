# jenkins/jobs/pipeline/docs-generator/pull-request-comment-builder/src/pr_comment_generator/prompt_manager.py
"""
プロンプトテンプレート管理

このモジュールは、OpenAI APIに送信するプロンプトのテンプレートを
管理し、PR情報に基づいてプロンプトを生成する機能を提供します。

主要なクラス:
- PromptTemplateManager: プロンプトテンプレートの読み込みとフォーマット
"""

import os
from typing import Dict

from .models import PRInfo


class PromptTemplateManager:
    """プロンプトテンプレートを管理するクラス"""

    def __init__(self, template_dir: str = "templates"):
        """初期化

        Args:
            template_dir: テンプレートファイルのディレクトリパス
        """
        self.template_dir = template_dir
        self._load_templates()

    def _load_templates(self):
        """テンプレートファイルを読み込む"""
        template_files = {
            'base': 'base_template.md',
            'chunk': 'chunk_analysis_extension.md',
            'summary': 'summary_extension.md'
        }

        self.templates = {}
        for key, filename in template_files.items():
            path = os.path.join(self.template_dir, filename)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    self.templates[key] = f.read().strip()
            except FileNotFoundError:
                print(f"Warning: Template file {filename} not found")
                self.templates[key] = ""

    def get_base_prompt(self) -> str:
        """ベースプロンプトを取得する

        Returns:
            str: ベースプロンプトテキスト
        """
        return self.templates.get('base', '')

    def get_chunk_analysis_prompt(self, pr_info_format: str = None) -> str:
        """チャンク分析プロンプトを取得する

        Args:
            pr_info_format: PR情報のフォーマット済みテキスト

        Returns:
            str: チャンク分析用プロンプト
        """
        # テンプレートの内容を確認
        if not self.templates['base'] or not self.templates['chunk']:
            print("Warning: Template content is empty!")

        if pr_info_format:
            formatted_prompt = self.templates['base'].format(
                input_format=pr_info_format,
                additional_instructions=self.templates['chunk']
            )
        else:
            formatted_prompt = self.templates['base'] + "\n\n" + self.templates['chunk']

        return formatted_prompt

    def get_summary_prompt(self, pr_info: PRInfo = None, analyses_text: str = "") -> str:
        """サマリー生成用のプロンプトを生成

        Args:
            pr_info: PR情報オブジェクト
            analyses_text: 分析結果テキスト

        Returns:
            str: サマリー生成用プロンプト
        """
        if pr_info:
            pr_info_format = (
                "### PR情報\n"
                f"- PR番号: {pr_info.number}\n"
                f"- タイトル: {pr_info.title}\n"
                f"- 作成者: {pr_info.author}\n"
                f"- ブランチ: {pr_info.base_branch} → {pr_info.head_branch}\n\n"
                "### 分析結果\n"
                f"{analyses_text}"
            )

            return self.templates['base'].format(
                input_format=pr_info_format,
                additional_instructions=self.templates['summary']
            )
        else:
            return self.templates['base'] + "\n\n" + self.templates['summary']

    def format_prompt(self, template_key: str, **kwargs) -> str:
        """プロンプトをフォーマットする

        Args:
            template_key: テンプレートのキー（'base', 'chunk', 'summary'）
            **kwargs: フォーマット用の変数

        Returns:
            str: フォーマットされたプロンプト
        """
        template = self.templates.get(template_key, '')
        try:
            return template.format(**kwargs)
        except KeyError as e:
            print(f"Warning: Missing format variable: {e}")
            return template
