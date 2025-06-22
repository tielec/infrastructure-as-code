"""!
OpenAI API クライアントモジュール

OpenAI APIとの通信を管理し、エラー処理とフォールバック処理を提供します。
"""

import os
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from openai import OpenAI

from utils.logger import logger
from config import SectionType


class OpenAIClient:
    """!
    OpenAI APIとのインタラクションを管理するクラス

    APIへの接続、プロンプト送信、レスポンス処理を担当します。
    エラー発生時のフォールバック処理も実装しています。
    """

    def __init__(self, api_key: str, model_name: Optional[str] = None,
                save_reflection: bool = False,
                template_manager = None):  # template_manager パラメータを追加
        """!
        OpenAIClientを初期化します

        Args:
            api_key: OpenAI APIキー
            model_name: 使用するモデル名（デフォルト: gpt-4.1）
            save_reflection: 省察プロセスを保存するかどうか
            template_manager: テンプレート管理クラスのインスタンス（オプション）
        """
        self.client = OpenAI(
            api_key=api_key
        )
        self.model_name = model_name or "gpt-4.1"
        self.fallback_model_name = "gpt-4o"  # フォールバック用のモデル
        self.usage_stats = {'prompt_tokens': 0, 'completion_tokens': 0}
        self.save_reflection = save_reflection
        self.template_manager = template_manager  # template_manager をインスタンス変数として保存
        
        # プロンプト履歴を保存するリスト
        self.prompt_history = []

        logger.info(f"OpenAIClient initialized with model: {self.model_name}")

    def generate_content(self, system_prompt: str, user_prompt: str,
                    temperature: float = 0.1, max_tokens: int = 10000,
                    operation_type: str = None, section_type: str = None) -> str:
        """!
        OpenAI APIを使用してコンテンツを生成します

        Args:
            system_prompt: システムプロンプト
            user_prompt: ユーザープロンプト
            temperature: 生成の温度（低いほど決定的な応答）
            max_tokens: 生成する最大トークン数
            operation_type: 操作タイプ（"new", "update", "analysis" など）
            section_type: セクションタイプ（"dataflow", "architecture" など）
            
        Returns:
            str: 生成されたテキスト
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        current_model = self.model_name
        max_retries = 1  # リトライ回数（フォールバックモデルを1回だけ試す）
        retry_count = 0
        
        logger.start_group(f"GENERATING CONTENT WITH {current_model}")
        
        # プロンプト情報を記録
        prompt_info = {
            "timestamp": datetime.now().isoformat(),
            "model": current_model,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "category": self._determine_prompt_category(user_prompt, operation_type, section_type)
        }
        
        while retry_count <= max_retries:
            try:
                logger.step(f"Sending request to OpenAI API using model: {current_model}")
                
                response = self._call_api(current_model, messages, temperature, max_tokens)
                self._update_usage_stats(response.usage)
                
                # プロンプト情報にレスポンスを追加
                prompt_info["response"] = response.choices[0].message.content.strip()
                prompt_info["completion_tokens"] = response.usage.completion_tokens
                prompt_info["prompt_tokens"] = response.usage.prompt_tokens
                prompt_info["total_tokens"] = response.usage.total_tokens
                prompt_info["is_fallback"] = current_model != self.model_name
                
                # プロンプト履歴に追加
                self.prompt_history.append(prompt_info)
                
                logger.token_usage(
                    response.usage.prompt_tokens, 
                    response.usage.completion_tokens, 
                    response.usage.total_tokens
                )
                logger.api_call(current_model, "SUCCESS")
                logger.end_group()
                
                return response.choices[0].message.content.strip()
                
            except Exception as e:
                # エラー情報をプロンプト情報に追加
                prompt_info["error"] = str(e)
                prompt_info["error_type"] = e.__class__.__name__ if hasattr(e, '__class__') else "Unknown"
                prompt_info["is_fallback"] = current_model != self.model_name
                
                # プロンプト履歴に追加（エラーでも記録）
                self.prompt_history.append(prompt_info)
                
                if self._should_retry_with_fallback(e, retry_count, max_retries):
                    logger.warning(f"Error with model {current_model}: {str(e)}. Retrying with {self.fallback_model_name}...")
                    current_model = self.fallback_model_name
                    retry_count += 1
                    # フォールバックの情報を次のプロンプト情報に設定
                    prompt_info = prompt_info.copy()
                    prompt_info["model"] = current_model
                    prompt_info["timestamp"] = datetime.now().isoformat()
                else:
                    logger.error(self._get_error_message(e, retry_count))
                    logger.end_group()
                    raise
        
        # このコードには到達しないはずだが、念のため
        logger.end_group()
        return ""

    def generate_content_with_reflection(self, system_prompt: str, user_prompt: str,
                                temperature: float = 0.1, max_tokens: int = 10000,
                                operation_type: str = None, section_type: str = None,
                                variables: Dict[str, Any] = None) -> str:
        """!
        自己対話プロセスを通じてコンテンツを生成します。
        3つのステップ（計画立案、自己対話、最終生成）を経て高品質なコンテンツを作成します。

        Args:
            system_prompt: システムプロンプト
            user_prompt: ユーザープロンプト
            temperature: 生成の温度（低いほど決定的な応答）
            max_tokens: 生成する最大トークン数
            operation_type: 操作タイプ（"new", "update", "analysis" など）
            section_type: セクションタイプ（"dataflow", "architecture" など）
            variables: テンプレート変数の辞書（オプション）
            
        Returns:
            str: 生成されたテキスト
        """
        
        logger.start_group(f"REFLECTION PROCESS - {section_type if section_type else 'document'}")
        
        # セクションタイプをSectionType列挙型に変換
        section_enum = None
        if section_type:
            try:
                section_enum = SectionType.from_string(section_type)
            except ValueError:
                logger.warning(f"Unknown section type: {section_type}")
                
        # 操作タイプの決定（デフォルトは "new"）
        if not operation_type or operation_type not in ["new", "update"]:
            op_type = "new"
        else:
            op_type = operation_type
                
        # テンプレートマネージャーが利用可能かチェック
        has_template_manager = hasattr(self, 'template_manager') and self.template_manager is not None
        
        # 変数が提供されていない場合、ユーザープロンプトから抽出
        if not variables:
            variables = self._extract_variables_from_prompt(user_prompt)
        
        # ステップ1: 計画立案
        logger.step("Phase 1: Planning phase")
        
        planning_prompt = f"{user_prompt}\n\n# まず、この情報を分析し、ドキュメント作成計画を立ててください。\n1. 情報の過不足を分析\n2. 不明点や推測が必要な部分を特定\n3. 取るべきアプローチを決定"
        planning_system_prompt = system_prompt
        
        # テンプレートマネージャーが利用可能で、セクションタイプが有効な場合は段階別テンプレートを使用
        if has_template_manager and section_enum:
            try:
                # 抽出した変数を渡す
                planning_template = self.template_manager.get_reflection_stage_template(
                    section_enum, "planning", op_type, variables)
                
                if planning_template.get("system_prompt"):
                    planning_system_prompt = planning_template["system_prompt"]
                    logger.debug("Using specialized system prompt for planning phase")
                
                # ユーザープロンプトが取得できれば、それを使用
                if planning_template.get("user_prompt") and planning_template["user_prompt"].strip():
                    planning_prompt = planning_template["user_prompt"]
                    logger.debug("Using specialized user prompt for planning phase")
            except Exception as e:
                logger.warning(f"Error getting planning template: {str(e)}")
        
        planning_result = self.generate_content(
            planning_system_prompt,
            planning_prompt,
            temperature,
            max_tokens,
            operation_type="planning",
            section_type=section_type
        )
        
        # 計画結果を変数に追加
        variables["planning_result"] = planning_result
        
        # ステップ2: 自己対話
        logger.step("Phase 2: Self-dialogue phase")
        
        dialog_prompt = f"{user_prompt}\n\n# 計画を基に自己対話を行い、情報の不足を補ってください\n{planning_result}\n\n以上の計画を踏まえ、自己対話形式で考えを整理してください。不明点については複数の可能性を検討し、最も妥当な仮説を採用するプロセスを示してください。"
        dialog_system_prompt = system_prompt
        
        # テンプレートマネージャーが利用可能で、セクションタイプが有効な場合は段階別テンプレートを使用
        if has_template_manager and section_enum:
            try:
                # 更新された変数を渡す
                dialog_template = self.template_manager.get_reflection_stage_template(
                    section_enum, "dialog", op_type, variables)
                
                if dialog_template.get("system_prompt"):
                    dialog_system_prompt = dialog_template["system_prompt"]
                    logger.debug("Using specialized system prompt for dialog phase")
                
                # ユーザープロンプトが取得できれば、それを使用
                if dialog_template.get("user_prompt") and dialog_template["user_prompt"].strip():
                    dialog_prompt = f"{dialog_template['user_prompt']}\n\n{planning_result}"
                    logger.debug("Using specialized user prompt for dialog phase")
            except Exception as e:
                logger.warning(f"Error getting dialog template: {str(e)}")
        
        dialog_result = self.generate_content(
            dialog_system_prompt,
            dialog_prompt,
            temperature,
            max_tokens,
            operation_type="reflection",
            section_type=section_type
        )
        
        # 自己対話結果を変数に追加
        variables["dialog_result"] = dialog_result
        
        # ステップ3: 最終生成
        logger.step("Phase 3: Final document generation")
        
        final_prompt = f"{user_prompt}\n\n# 分析と自己対話を踏まえて最終ドキュメントを作成してください\n{planning_result}\n\n{dialog_result}\n\n以上の分析と考察を踏まえ、最終的なドキュメントを作成してください。推測に基づく部分は「（推測）」などと明記してください。"
        final_system_prompt = system_prompt
        
        # テンプレートマネージャーが利用可能で、セクションタイプが有効な場合は段階別テンプレートを使用
        if has_template_manager and section_enum:
            try:
                # 全ての結果を含む変数を渡す
                final_template = self.template_manager.get_reflection_stage_template(
                    section_enum, "final", op_type, variables)
                
                if final_template.get("system_prompt"):
                    final_system_prompt = final_template["system_prompt"]
                    logger.debug("Using specialized system prompt for final phase")
                
                # ユーザープロンプトが取得できれば、それを使用
                if final_template.get("user_prompt") and final_template["user_prompt"].strip():
                    final_prompt = f"{final_template['user_prompt']}\n\n{planning_result}\n\n{dialog_result}"
                    logger.debug("Using specialized user prompt for final phase")
            except Exception as e:
                logger.warning(f"Error getting final template: {str(e)}")
        
        final_content = self.generate_content(
            final_system_prompt,
            final_prompt,
            temperature,
            max_tokens,
            operation_type=operation_type,
            section_type=section_type
        )
        
        # 省察プロセスの保存（オプション）
        if self.save_reflection:
            self._save_reflection_process(section_type, planning_result, dialog_result, final_content)
        
        logger.info("Reflection process completed successfully")
        logger.end_group()
        
        return final_content

    def _extract_variables_from_prompt(self, prompt: str) -> Dict[str, Any]:
        """
        ユーザープロンプトから変数を抽出する
        
        Args:
            prompt: ユーザープロンプト
            
        Returns:
            Dict[str, Any]: 抽出された変数の辞書
        """
        import re
        
        variables = {}
        
        # プレースホルダーの値を探す (例: ```{structured_info}\n...\n``` など)
        pattern = r'```\{([a-zA-Z_]+)\}\n([\s\S]*?)\n```'
        matches = re.finditer(pattern, prompt)
        
        for match in matches:
            var_name = match.group(1)
            var_value = match.group(2)
            variables[var_name] = var_value
            
        # その他の重要な情報を探す（必要に応じて追加）
        
        return variables
    
    def _load_reflection_prompt(self, stage: str, original_prompt: str, section_type: str = None) -> str:
        """
        段階に応じた適切な省察プロンプトを読み込みます。
        
        Args:
            stage: 省察の段階 ("planning", "dialog", "final")
            original_prompt: 元のシステムプロンプト
            section_type: セクションタイプ（"dataflow", "architecture" など）
            
        Returns:
            str: 適切なシステムプロンプト
        """
        # テンプレートマネージャーがない場合は元のプロンプトを使用
        if not hasattr(self, 'template_manager') or not self.template_manager:
            return original_prompt
        
        # セクション名を取得（データフロー図、アーキテクチャ図など）
        section_name = section_type.replace('_', ' ').title() if section_type else "ドキュメント"
        
        # ステージに応じたプロンプトファイル名
        prompt_files = {
            "planning": "reflection_planning_prompt.txt",
            "dialog": "reflection_dialog_prompt.txt",
            "final": "reflection_final_prompt.txt"
        }
        
        try:
            # 共通ガイドラインを読み込む
            common_guidelines = self.template_manager.get_common_template("reflection_common_guidelines.txt") or ""
            
            # 段階別プロンプトを読み込む
            stage_prompt_file = prompt_files.get(stage, "reflection_system_prompt.txt")
            stage_prompt = self.template_manager.get_common_template(stage_prompt_file) or ""
            
            # プロンプトを組み合わせて変数を置換
            if stage_prompt:
                combined_prompt = f"{stage_prompt}\n\n{common_guidelines}"
                prompt = self.template_manager.render_template(
                    combined_prompt,
                    {"SECTION_TYPE": section_type or "document", "SECTION_NAME": section_name}
                )
                return prompt
        except Exception as e:
            logger.warning(f"Failed to load reflection prompt for stage {stage}: {str(e)}")
        
        # エラー時は元のプロンプトを使用
        return original_prompt

    def _save_reflection_process(self, section_type: str, planning: str, reflection: str, final: str) -> None:
        """
        省察プロセスの内容を保存します。
        
        Args:
            section_type: セクションタイプ
            planning: 計画立案の結果
            reflection: 自己対話の結果
            final: 最終生成された内容
        """
        try:
            # 保存先ディレクトリ
            reflection_dir = os.path.join("reflection_logs", section_type if section_type else "document")
            os.makedirs(reflection_dir, exist_ok=True)
            
            # タイムスタンプ
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 各ステップの内容を保存
            with open(os.path.join(reflection_dir, f"{timestamp}_planning.md"), "w", encoding="utf-8") as f:
                f.write("# 計画立案\n\n")
                f.write(planning)
                
            with open(os.path.join(reflection_dir, f"{timestamp}_reflection.md"), "w", encoding="utf-8") as f:
                f.write("# 自己対話による省察\n\n")
                f.write(reflection)
                
            # 統合ファイルも作成
            with open(os.path.join(reflection_dir, f"{timestamp}_full_process.md"), "w", encoding="utf-8") as f:
                f.write("# 省察プロセス - 詳細記録\n\n")
                f.write("## 1. 計画立案\n\n")
                f.write(planning)
                f.write("\n\n## 2. 自己対話による省察\n\n")
                f.write(reflection)
                f.write("\n\n## 3. 最終生成結果\n\n")
                f.write(final)
                
            logger.info(f"Saved reflection process to {reflection_dir}")
            
        except Exception as e:
            logger.error(f"Failed to save reflection process: {str(e)}")

    def _call_api(self, model: str, messages: list, temperature: float, max_tokens: int) -> Any:
        """
        APIを呼び出し、レスポンスを返します
        
        Args:
            model: 使用するモデル名
            messages: メッセージリスト
            temperature: 生成の温度
            max_tokens: 最大トークン数
            
        Returns:
            API応答オブジェクト
        """
        return self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=0.9,                # より確実な選択肢に集中させる
            frequency_penalty=0.1,    # 若干の多様性を促進
            presence_penalty=0.0,     # 同じままでOK
            stream=False              # 長い応答でも一度に取得するため
        )

    def _update_usage_stats(self, usage) -> None:
        """
        トークン使用量の統計を更新します
        
        Args:
            usage: 使用量オブジェクト
        """
        self.usage_stats['prompt_tokens'] += usage.prompt_tokens
        self.usage_stats['completion_tokens'] += usage.completion_tokens

    def _should_retry_with_fallback(self, error: Exception, retry_count: int, max_retries: int) -> bool:
        """
        フォールバックでリトライすべきかを判断します
        
        Args:
            error: 発生したエラー
            retry_count: 現在のリトライ回数
            max_retries: 最大リトライ回数
            
        Returns:
            bool: リトライすべき場合はTrue
        """
        error_message = str(error).lower()
        # レート制限エラーまたはモデルが利用できないエラーの場合
        is_rate_limit = "rate_limit_exceeded" in error_message or "429" in error_message
        is_model_error = "model_not_found" in error_message or "model not available" in error_message
        return (is_rate_limit or is_model_error) and retry_count < max_retries

    def _get_error_message(self, error: Exception, retry_count: int) -> str:
        """
        エラーメッセージを取得します
        
        Args:
            error: 発生したエラー
            retry_count: 現在のリトライ回数
            
        Returns:
            str: エラーメッセージ
        """
        error_message = str(error).lower()
        if "rate_limit_exceeded" in error_message or "429" in error_message:
            return "Rate limit exceeded with fallback model too. Giving up."
        elif "model_not_found" in error_message:
            return "Model not found with fallback model too. Giving up."
        return f"Error calling OpenAI API: {str(error)}"

    def get_usage_stats(self) -> Dict[str, int]:
        """!
        APIの使用統計を取得します

        Returns:
            Dict[str, int]: トークン使用量の統計辞書
        """
        return {
            'prompt_tokens': self.usage_stats['prompt_tokens'],
            'completion_tokens': self.usage_stats['completion_tokens'],
            'total_tokens': sum(self.usage_stats.values())
        }
    
    def get_prompt_history(self) -> List[Dict[str, Any]]:
        """!
        プロンプト履歴を取得します
        
        Returns:
            List[Dict[str, Any]]: プロンプト履歴のリスト
        """
        return self.prompt_history
    
    def save_prompt_history(self, output_file: str) -> bool:
        """!
        プロンプト履歴をマークダウンファイルに保存します
        
        Args:
            output_file: 出力ファイルパス
            
        Returns:
            bool: 成功した場合はTrue
        """
        logger.info(f"Saving prompt history to {output_file}")
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                # マークダウンのヘッダーを書き込む
                f.write("# プロンプト履歴\n\n")
                f.write("このファイルには、ドキュメント生成中に使用されたすべてのプロンプトが含まれています。\n\n")
                
                # 各プロンプトを順番に書き込む
                for i, prompt in enumerate(self.prompt_history, 1):
                    # プロンプトの基本情報
                    f.write(f"## プロンプト {i}: {prompt['category']}\n\n")
                    f.write(f"- **モデル**: {prompt['model']}\n")
                    f.write(f"- **日時**: {prompt['timestamp']}\n")
                    if prompt.get('is_fallback'):
                        f.write(f"- **フォールバック**: はい\n")
                    
                    # トークン情報（もし存在すれば）
                    if 'prompt_tokens' in prompt:
                        f.write(f"- **プロンプトトークン**: {prompt['prompt_tokens']}\n")
                        f.write(f"- **レスポンストークン**: {prompt['completion_tokens']}\n")
                        f.write(f"- **合計トークン**: {prompt['total_tokens']}\n")
                    
                    # エラー情報（もし存在すれば）
                    if 'error' in prompt:
                        f.write(f"- **エラー**: {prompt['error']}\n")
                        f.write(f"- **エラータイプ**: {prompt['error_type']}\n")
                    
                    # システムプロンプト
                    f.write("\n### システムプロンプト\n\n")
                    f.write("```\n")
                    f.write(prompt['system_prompt'])
                    f.write("\n```\n\n")
                    
                    # ユーザープロンプト
                    f.write("### ユーザープロンプト\n\n")
                    f.write("```\n")
                    f.write(prompt['user_prompt'])
                    f.write("\n```\n\n")
                    
                    # レスポンス（もし存在すれば）
                    if 'response' in prompt:
                        f.write("### レスポンス\n\n")
                        f.write("```\n")
                        f.write(prompt['response'])
                        f.write("\n```\n\n")
                    
                    # プロンプト間の区切り
                    if i < len(self.prompt_history):
                        f.write("---\n\n")
                    
                logger.info(f"Successfully saved {len(self.prompt_history)} prompts to {output_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save prompt history: {str(e)}")
            return False
    
    def _determine_prompt_category(self, user_prompt: str, operation_type: str = None, section_type: str = None) -> str:
        """
        プロンプトの種類を判断します
        
        Args:
            user_prompt: ユーザープロンプト
            operation_type: 操作タイプ ("new"、"update"、"analysis" など)
            section_type: セクションタイプ ("overview", "directory_structure" など)
            
        Returns:
            str: プロンプトカテゴリ
        """
        # 1. 操作タイプとセクションタイプが両方指定されている場合
        if operation_type and section_type:
            # "analysis", "merge", "planning", "reflection" などの特殊な操作タイプはそのまま返す
            if operation_type in ["analysis", "merge", "planning", "reflection"]:
                return operation_type
            
            # それ以外は"{operation_type}_{section_type}"形式で返す
            return f"{operation_type}_{section_type}"
            
        # 2. 操作タイプのみが指定されている場合
        if operation_type:
            # "analysis", "merge", "planning", "reflection" などの特殊な操作タイプはそのまま返す
            if operation_type in ["analysis", "merge", "planning", "reflection"]:
                return operation_type
                
            # セクションタイプをプロンプトから検出
            detected_section = self._detect_section_type(user_prompt)
            if detected_section:
                return f"{operation_type}_{detected_section}"
            
            # 検出できなかった場合
            return f"{operation_type}_unknown"
        
        # 3. セクションタイプのみが指定されている場合
        if section_type:
            # 操作タイプをプロンプトから検出
            if "新規作成" in user_prompt or "新規" in user_prompt or "create" in user_prompt.lower():
                return f"new_{section_type}"
            elif "更新" in user_prompt or "update" in user_prompt.lower():
                return f"update_{section_type}"
            else:
                # デフォルトは "new" とする
                return f"new_{section_type}"
        
        # 4. どちらも指定されていない場合 (後方互換性のため)
        # 各セクションタイプに関連するキーワード
        keywords = {
            "overview": ["概要", "overview", "全体像"],
            "directory_structure": ["ディレクトリ", "フォルダ", "構造", "directory", "folder", "structure"],
            "architecture": ["アーキテクチャ", "architecture", "構成図", "コンポーネント"],
            "dataflow": ["データフロー", "data flow", "フロー図", "データの流れ"],
            "glossary": ["用語", "glossary", "terminology", "語彙"],
            "changelog": ["変更履歴", "changelog", "history", "変更点"]
        }
        
        # セクションタイプを検出
        detected_section = None
        for section, words in keywords.items():
            for word in words:
                if word in user_prompt:
                    detected_section = section
                    break
            if detected_section:
                break
        
        # 操作タイプを検出
        detected_operation = None
        if "新規作成" in user_prompt or "新規" in user_prompt or "create" in user_prompt.lower():
            detected_operation = "new"
        elif "更新" in user_prompt or "update" in user_prompt.lower():
            detected_operation = "update"
        
        # 分析か統合かを判断
        if "分析" in user_prompt or "analysis" in user_prompt.lower():
            return "analysis"
        elif "統合" in user_prompt or "merge" in user_prompt.lower():
            return "merge"
        elif "計画" in user_prompt or "planning" in user_prompt.lower():
            return "planning"
        elif "省察" in user_prompt or "reflection" in user_prompt.lower() or "自己対話" in user_prompt:
            return "reflection"
        
        # セクションと操作タイプの組み合わせがある場合
        if detected_section and detected_operation:
            return f"{detected_operation}_{detected_section}"
            
        # セクションのみが検出された場合
        if detected_section:
            # デフォルトは "new" とする
            return f"new_{detected_section}"
        
        # 操作タイプのみが検出された場合
        if detected_operation:
            return f"{detected_operation}_unknown"
        
        # 何も検出できなかった場合
        return "other"

    def _detect_section_type(self, user_prompt: str) -> str:
        """
        ユーザープロンプトからセクションタイプを検出します
        
        Args:
            user_prompt: ユーザープロンプト
            
        Returns:
            str: 検出されたセクションタイプ、検出できない場合は None
        """
        # 各セクションタイプに関連するキーワード
        keywords = {
            "overview": ["概要", "overview", "全体像"],
            "directory_structure": ["ディレクトリ", "フォルダ", "構造", "directory", "folder", "structure"],
            "architecture": ["アーキテクチャ", "architecture", "構成図", "コンポーネント"],
            "dataflow": ["データフロー", "data flow", "フロー図", "データの流れ"],
            "glossary": ["用語", "glossary", "terminology", "語彙"],
            "changelog": ["変更履歴", "changelog", "history", "変更点"]
        }
        
        for section, words in keywords.items():
            for word in words:
                if word in user_prompt:
                    return section
        
        return None
