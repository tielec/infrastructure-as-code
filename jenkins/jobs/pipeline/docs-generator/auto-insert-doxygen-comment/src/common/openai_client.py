"""
OpenAI API とのインタラクションを管理する共通クライアント
"""
from typing import Dict, List, Optional, Any
from openai import OpenAI

class OpenAIClient:
    """OpenAI APIとのインタラクションを管理するクラス"""
    
    def __init__(self, api_key: str, model_name: Optional[str] = None):
        """
        Args:
            api_key (str): OpenAI APIキー
            model_name (Optional[str]): 使用するモデル名（デフォルト: gpt-4.1）
        """
        self.client = OpenAI(
            api_key=api_key
        )
        self.model_name = model_name or "gpt-4.1"
        self.fallback_model_name = "gpt-4.1"  # フォールバック用のモデル
        self.usage_stats = {
            'prompt_tokens': 0,
            'completion_tokens': 0
        }

    def generate_doc(self, code: str, template: str, system_prompt: str) -> str:
        """ドキュメントを生成する

        Args:
            code (str): 対象のソースコード
            template (str): ドキュメント生成用のテンプレート
            system_prompt (str): システムプロンプト

        Returns:
            str: 生成されたドキュメント
        """
        messages = [
            {
                "role": "system", 
                "content": system_prompt
            },
            {
                "role": "user",
                "content": template.format(code=code)
            }
        ]

        # まず主要なモデルで試す
        current_model = self.model_name
        max_retries = 1  # リトライ回数（フォールバックモデルを1回だけ試す）
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                response = self.client.chat.completions.create(
                    model=current_model,
                    messages=messages,
                    temperature=0.0,
                    max_tokens=1000,
                    top_p=0.1,
                    frequency_penalty=0.0,
                    presence_penalty=0.0
                )
                
                # トークン使用量の記録と表示
                usage = response.usage
                self.usage_stats['prompt_tokens'] += usage.prompt_tokens
                self.usage_stats['completion_tokens'] += usage.completion_tokens
                print(f"\nToken usage - Prompt: {usage.prompt_tokens}, Completion: {usage.completion_tokens}, Total: {usage.total_tokens}")
                print(f"Using model: {current_model}")
                
                return response.choices[0].message.content.strip()
                
            except Exception as e:
                error_message = str(e).lower()
                
                # レート制限エラーまたはモデルが利用できないエラーの場合
                if "rate_limit_exceeded" in error_message or "429" in error_message or "model_not_found" in error_message:
                    if retry_count < max_retries:
                        # フォールバックモデルに切り替え
                        print(f"\nError with model {current_model}: {str(e)}. Falling back to {self.fallback_model_name}.")
                        current_model = self.fallback_model_name
                        retry_count += 1
                    else:
                        # リトライ回数を超えた場合はエラーを再発生
                        print(f"\nError with fallback model too. Giving up.")
                        raise
                else:
                    # その他のエラーはそのまま再発生
                    raise

    def get_usage_stats(self) -> Dict[str, int]:
        """APIの使用統計を取得する

        Returns:
            Dict[str, int]: トークン使用量の統計
        """
        return {
            'prompt_tokens': self.usage_stats['prompt_tokens'],
            'completion_tokens': self.usage_stats['completion_tokens'],
            'total_tokens': sum(self.usage_stats.values())
        }
