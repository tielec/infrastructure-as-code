"""!
Mermaid図表検証・修正モジュール

生成されたMermaidダイアグラムの構文をチェックし、エラーがある場合は
OpenAI APIを使用して自動的に修正します。
"""

import os
import re
import subprocess
import json
from typing import List, Dict, Optional
import tempfile

from utils.logger import logger
from api.openai_client import OpenAIClient


class MermaidHelper:
    """!
    Mermaidダイアグラムの検証と修正を行うヘルパークラス
    
    mmdc コマンドを使用してMermaidコードをレンダリングし、
    エラーがある場合はOpenAI APIを使用して修正します。
    """
    
    # プロンプトの共通部分
    PROMPT_PREFIX = "あなたはMermaid図表の専門家です。Mermaidのコードを修正してください。\nエラーの原因を特定し、修正したコードを返してください。"
    PROMPT_SUFFIX = "修正したコードのみを返し、説明は含めないでください。Mermaidの基本構文を尊重し、エラーが発生しない有効なコードを提供してください。"
    
    # フローチャート用プロンプト
    FLOWCHART_PROMPT = """
1. **テキストの引用符処理**: 
   - 日本語テキストや括弧、空白を含むノード名は、必ず二重引用符(")で囲む
   - 例: `A[プラグインインストール (install-plugins.sh)]` → `A["プラグインインストール (install-plugins.sh)"]`

2. **コメントの処理**:
   - `%%` コメントはノード定義やエッジ定義の中や直後には配置しない
   - コメントは別の行に移動するか、完全に削除する

3. **矢印と関係の定義**:
   - 矢印ラベルにテキストを含める場合は `|` で囲み、必要に応じて引用符も使用
   - 例: `A --> B 説明テキスト` → `A --> |"説明テキスト"| B`

4. **サブグラフの定義と接続**:
   - サブグラフ名に空白や特殊文字を含む場合は引用符で囲む: `subgraph "システム A" ... end`
   - サブグラフには必ずIDを割り当てる: `subgraph subgraphID ["サブグラフ表示名"] ... end`
   - サブグラフへの接続は直接文字列ではなくIDを使用: `subgraphID --> otherNode`（○）、`"サブグラフ表示名" --> otherNode`（×）
   - サブグラフ内部のノードへの外部からの接続は: `externalNode --> subgraphID.internalNode`
   - 例:
     ```
     subgraph sg1 ["システム1"]
       A[ノード1]
       B[ノード2]
     end
     sg1 --> C[外部ノード]  // サブグラフ全体を接続
     D[別の外部ノード] --> A  // サブグラフ内のノードに直接接続
     ```

5. **フローチャートの方向指定**:
   - 方向指定は図の最初に記述（TB, LR, RL, BT）
   - サブグラフ内の方向指定は `direction` キーワードを使用

6. **注釈の追加方法**:
   - flowchart/graph では `note` 構文は使用できない（エラーになる）
   - 代わりに、通常のノードとして注釈を作成し、適切にスタイル設定する
   - 例: 
     ```
     Note1["これは注釈です"]
     A --> Note1
     style Note1 fill:#ffffcc,stroke:#ffcc00
     ```
   - または注釈をノードの説明として含める:
     ```
     A["コンポーネント\n(説明をここに記述)"]
     ```

7. **クラス定義とスタイリング**:
   - クラス定義は図の最後に配置: `classDef className fill:#f9f,stroke:#333;`
   - クラスの適用: `class nodeID1,nodeID2 className;`
   - スタイル直接適用: `style nodeID fill:#bbf,stroke:#33f;`
"""
    
    # シーケンス図用プロンプト
    SEQUENCE_DIAGRAM_PROMPT = """
1. **参加者の定義**: 
   - 空白や特殊文字を含む参加者名には二重引用符を使用
   - 例: `participant ユーザー` → `participant "ユーザー"`

2. **アクティベーションと非アクティベーション**:
   - 活性化/非活性化の矢印の対応を確認
   - 例: `A->>+B: メッセージ` と対応する `B-->>-A: 応答`

3. **ループとエリア構造**:
   - loop/end, alt/else/end, opt/end などの構造は正しく閉じる

4. **注釈の配置**:
   - 注釈は `Note left of`, `Note right of`, `Note over` などを使用
   - 複数参加者の範囲指定は `Note over A,B`
   - 注釈のテキストには改行を含められる: `Note right of A: 複数行の</br>注釈も可能`
"""
    
    # 状態図用プロンプト
    STATE_DIAGRAM_PROMPT = """
1. **状態名の定義**:
   - 空白や特殊文字を含む状態名は二重引用符で囲む
   - 例: `状態 A` → `"状態 A"`

2. **状態遷移の記法**:
   - 基本的な遷移: `State1 --> State2`
   - 説明付き遷移: `State1 --> State2: "アクション"` 
   - 条件付き遷移では特殊な書式が必要:
     - `A --> B: 処理 (条件: 値)` ← このような書き方はエラーになります
     - 正しくは: `A --> B: "処理"` または `A --> B: "処理 [条件]"`

3. **注意点**:
   - 状態図では括弧を含む説明文は避け、シンプルにする
   - 複雑な条件や説明は省略するか単純化する
   - 状態名と遷移の説明はすべて引用符で囲む

4. **入れ子状態と複合状態**:
   - 複合状態は `state "状態名" as X { ... }` で定義
   - 状態名の省略形 `state X as "長い状態名"` を使うことも可能

5. **開始・終了状態**:
   - 開始状態は `[*] --> "最初の状態"`
   - 終了状態は `"最後の状態" --> [*]`

6. **注釈の追加**:
   - 注釈は `note right of` または `note left of` 構文を使用
   - 例: `note right of "状態A": これは注釈です`
   - 注釈のテキストにはマークダウン記法は使用できない
"""
    
    # 不明なダイアグラム用プロンプト
    UNKNOWN_DIAGRAM_PROMPT = """
一般的なエラー修正のガイドライン:

1. **テキストの引用符処理**: 
   - 日本語テキストや括弧、空白を含む識別子やラベルは、必ず二重引用符(")で囲む

2. **コメントの処理**:
   - `%%` コメントは単独の行に配置し、定義の中や直後には入れない

3. **構文チェック**:
   - 開始宣言が正しいか確認（flowchart, sequenceDiagram, stateDiagram-v2 など）
   - 閉じタグが必要な構造（サブグラフ、ループなど）が正しく閉じられているか
   - 矢印や関係の定義が正しいシンタックスで記述されているか

4. **ダイアグラム種類別の注釈方法**:
   - flowchart/graph: `note` 構文は使用不可。代わりにスタイル付きのノードを使用
   - sequenceDiagram: `Note left of`, `Note right of`, `Note over` を使用
   - stateDiagram-v2: `note left of`, `note right of` を使用
"""
    
    def __init__(self, openai_client: OpenAIClient):
        """!
        MermaidHelperを初期化します
        
        Args:
            openai_client: OpenAI APIクライアント
        """
        self.openai_client = openai_client
        self.temp_dir = tempfile.gettempdir()
        
        # puppeteer-config.jsonを作成
        self.puppeteer_config = os.path.join(self.temp_dir, "puppeteer-config.json")
        with open(self.puppeteer_config, "w", encoding="utf-8") as f:
            f.write('{"args":["--no-sandbox","--disable-setuid-sandbox"]}')
        
        logger.info(f"MermaidHelper initialized")
    
    def validate_mermaid_in_file(self, markdown_file: str) -> bool:
        """!
        Markdownファイル内のすべてのMermaidダイアグラムを検証します
        
        Args:
            markdown_file: Markdownファイルのパス
            
        Returns:
            bool: すべてのダイアグラムが有効な場合はTrue
        """
        logger.info(f"Validating Mermaid diagrams in {markdown_file}")
        
        # ファイルを読み込む
        try:
            with open(markdown_file, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Failed to read file {markdown_file}: {str(e)}")
            return False
        
        # Mermaidコードブロックを抽出
        mermaid_blocks = self._extract_mermaid_blocks(content)
        
        if not mermaid_blocks:
            logger.info(f"No Mermaid diagrams found in {markdown_file}")
            return True
        
        logger.info(f"Found {len(mermaid_blocks)} Mermaid diagrams in {markdown_file}")
        
        # 各ブロックを検証
        all_valid = True
        for i, code in enumerate(mermaid_blocks):
            logger.debug(f"Validating diagram {i+1}/{len(mermaid_blocks)}")
            if not self._validate_mermaid_code(code, i):
                all_valid = False
        
        return all_valid
    
    def fix_mermaid_in_file(self, markdown_file: str, max_retry: int = 3) -> bool:
        """!
        Markdownファイル内のMermaidダイアグラムを検証し、必要に応じて修正します
        
        Args:
            markdown_file: Markdownファイルのパス
            max_retry: 各ダイアグラムの最大再試行回数
            
        Returns:
            bool: 修正が成功したかどうか
        """
        logger.start_group(f"Fixing Mermaid diagrams in {markdown_file}")
        
        try:
            # ファイルを読み込む
            with open(markdown_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Mermaidコードブロックを抽出
            mermaid_blocks = self._extract_mermaid_blocks(content)
            
            if not mermaid_blocks:
                logger.info(f"No Mermaid diagrams found in {markdown_file}")
                logger.end_group()
                return True
            
            logger.info(f"Found {len(mermaid_blocks)} Mermaid diagrams")
            
            # 各ブロックを検証し、必要に応じて修正
            for i, code in enumerate(mermaid_blocks):
                logger.step(f"Processing diagram {i+1}/{len(mermaid_blocks)}")
                
                # 一時ファイルにコードを書き込む
                temp_file = os.path.join(self.temp_dir, f"diagram_{i}.mmd")
                with open(temp_file, "w", encoding="utf-8") as f:
                    f.write(code)
                
                # 検証して必要に応じて修正
                fixed_code = self._fix_mermaid_code_if_needed(temp_file, max_retry)
                
                if fixed_code and fixed_code != code:
                    logger.info(f"Diagram {i+1} was fixed")
                    # ファイル内のMermaidブロックを置換
                    # 正確に置換するためにコードをエスケープしてから正規表現で置換
                    escaped_code = re.escape(code)
                    content = re.sub(
                        f"```mermaid\n{escaped_code}\n```",
                        f"```mermaid\n{fixed_code}\n```",
                        content
                    )
            
            # 修正された内容をファイルに書き戻す
            with open(markdown_file, "w", encoding="utf-8") as f:
                f.write(content)
            
            logger.info(f"Mermaid diagrams fixed successfully in {markdown_file}")
            logger.end_group()
            return True
            
        except Exception as e:
            logger.error(f"Failed to fix Mermaid diagrams: {str(e)}")
            logger.end_group()
            return False
    
    def _extract_mermaid_blocks(self, content: str) -> List[str]:
        """
        Markdownコンテンツから```mermaidブロックを抽出します
        
        Args:
            content: Markdownコンテンツ
            
        Returns:
            List[str]: 抽出されたMermaidコードブロックのリスト
        """
        pattern = r"```mermaid\n([\s\S]*?)\n```"
        matches = re.findall(pattern, content)
        return matches
    
    def _validate_mermaid_code(self, code: str, index: int = 0) -> bool:
        """
        Mermaidコードを検証します
        
        Args:
            code: Mermaidコード
            index: ダイアグラムのインデックス（ログ用）
            
        Returns:
            bool: コードが有効な場合はTrue
        """
        # 一時ファイルにコードを書き込む
        temp_file = os.path.join(self.temp_dir, f"validate_{index}.mmd")
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(code)
        
        # mmdcで検証
        output_file = os.path.join(self.temp_dir, f"validate_{index}.png")
        cmd = [
            "mmdc",
            "-i", temp_file,
            "-o", output_file,
            "-p", self.puppeteer_config
        ]
        
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True)
            
            if proc.returncode == 0:
                logger.debug(f"Diagram {index} is valid")
                return True
            else:
                error_output = (proc.stderr or proc.stdout).strip()
                logger.warning(f"Diagram {index} has errors: {error_output}")
                return False
        except Exception as e:
            logger.error(f"Error validating diagram {index}: {str(e)}")
            return False
        finally:
            # 一時ファイルをクリーンアップ
            if os.path.exists(temp_file):
                os.remove(temp_file)
            if os.path.exists(output_file):
                os.remove(output_file)
    
    def _fix_mermaid_code_if_needed(self, mmd_filename: str, max_retry: int) -> Optional[str]:
        """
        mmdcを実行し、エラーが出た場合はOpenAI APIで修正します
        
        Args:
            mmd_filename: Mermaidコードファイルのパス
            max_retry: 最大再試行回数
            
        Returns:
            Optional[str]: 修正されたコード（エラーがなければNone）
        """
        for i in range(max_retry):
            logger.debug(f"Attempt {i+1}/{max_retry} to render {mmd_filename}")
            
            # 出力ファイルパス
            output_file = os.path.join(self.temp_dir, f"output_{os.path.basename(mmd_filename)}.png")
            
            # mmdcコマンドを実行
            cmd = [
                "mmdc",
                "-i", mmd_filename,
                "-o", output_file,
                "-p", self.puppeteer_config
            ]
            
            proc = subprocess.run(cmd, capture_output=True, text=True)
            
            if proc.returncode == 0:
                logger.debug(f"Mermaid diagram generation succeeded")
                # 正常終了した場合はファイルを読み込んで返す
                with open(mmd_filename, "r", encoding="utf-8") as f:
                    return f.read()
            else:
                error_output = (proc.stderr or proc.stdout).strip()
                logger.warning(f"mmdc failed. Output: {error_output}")
                
                # 現在のコードを読み込む
                try:
                    with open(mmd_filename, "r", encoding="utf-8") as f:
                        current_code = f.read()
                except FileNotFoundError:
                    logger.error(f"File {mmd_filename} not found")
                    return None
                
                # OpenAI APIを使用してコードを修正
                fixed_code = self._fix_with_openai(current_code, error_output)
                
                if fixed_code:
                    # 修正されたコードを書き込む
                    with open(mmd_filename, "w", encoding="utf-8") as f:
                        f.write(fixed_code)
                    
                    logger.info(f"Code fixed and saved to {mmd_filename}")
                else:
                    logger.error("Failed to fix code with OpenAI")
                    return None
        
        logger.error(f"Failed to fix Mermaid code after {max_retry} attempts")
        return None
    
    def _detect_diagram_type(self, code: str) -> str:
        """
        Mermaidコードからダイアグラムの種類を検出します
        
        Args:
            code: Mermaidコード
            
        Returns:
            str: ダイアグラムの種類（"flowchart", "sequenceDiagram", "stateDiagram-v2", "unknown"）
        """
        # 先頭行からダイアグラム種類を抽出
        first_line = code.strip().split('\n')[0].strip().lower()
        
        # 3つの主要なダイアグラム種類を検出
        if first_line.startswith(("flowchart", "graph")):
            return "flowchart"
        elif first_line.startswith(("sequencediagram", "sequence")):
            return "sequenceDiagram"
        elif first_line.startswith(("statediagram", "statediagram-v2")):
            return "stateDiagram-v2"
        
        return "unknown"

    def _get_system_prompt_for_diagram(self, diagram_type: str) -> str:
        """
        ダイアグラム種類に応じたシステムプロンプトを生成します
        
        Args:
            diagram_type: ダイアグラムの種類
            
        Returns:
            str: ダイアグラム種類に適したシステムプロンプト
        """
        # ダイアグラム種類別のプロンプトを選択
        if diagram_type == "flowchart":
            specific_prompt = self.FLOWCHART_PROMPT
        elif diagram_type == "sequenceDiagram":
            specific_prompt = self.SEQUENCE_DIAGRAM_PROMPT
        elif diagram_type == "stateDiagram-v2":
            specific_prompt = self.STATE_DIAGRAM_PROMPT
        else:  # unknown
            specific_prompt = self.UNKNOWN_DIAGRAM_PROMPT
        
        return f"{self.PROMPT_PREFIX}\n\n{specific_prompt}\n\n{self.PROMPT_SUFFIX}"
    
    def _fix_with_openai(self, code: str, error_output: str) -> Optional[str]:
        """
        OpenAI APIを使用してMermaidコードを修正します
        
        Args:
            code: 修正するMermaidコード
            error_output: エラー出力
            
        Returns:
            Optional[str]: 修正されたコード（失敗した場合はNone）
        """
        try:
            # ダイアグラム種類を検出
            diagram_type = self._detect_diagram_type(code)
            logger.info(f"Detected diagram type: {diagram_type}")
            
            # ダイアグラム種類に応じたシステムプロンプトを取得
            system_prompt = self._get_system_prompt_for_diagram(diagram_type)
            
            # ユーザープロンプト
            user_prompt = f"""以下のMermaidコードにエラーがあります:

```mermaid
{code}
```

エラーメッセージ:
{error_output}

修正したコードのみを返してください。Mermaidのコード以外は含めないでください。```mermaid```のタグも含めないでください。
"""
            
            # OpenAI APIを呼び出す
            response = self.openai_client.generate_content(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                operation_type="fix_mermaid"
            )
            
            if response:
                # コードのみを抽出（```mermaidタグを除去）
                fixed_code = self._extract_code_only(response)
                logger.info("OpenAI successfully fixed the Mermaid code")
                return fixed_code
            
            return None
            
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {str(e)}")
            return None
    
    def _extract_code_only(self, response: str) -> str:
        """
        OpenAI APIのレスポンスからコードのみを抽出します
        
        Args:
            response: OpenAI APIレスポンス
            
        Returns:
            str: 抽出されたコード
        """
        # コードブロックを抽出
        code_pattern = r"```(?:mermaid)?\n([\s\S]*?)```"
        code_match = re.search(code_pattern, response)
        
        if code_match:
            return code_match.group(1).strip()
        
        # コードブロックがない場合はレスポンス全体を返す
        return response.strip()
    
    def process_section_file(self, section_file: str, max_retry: int = 3) -> bool:
        """!
        セクションファイル内のMermaidダイアグラムを処理します
        
        Args:
            section_file: セクションファイルのパス
            max_retry: 最大再試行回数
            
        Returns:
            bool: 処理が成功したかどうか
        """
        logger.info(f"Processing Mermaid diagrams in section file: {section_file}")
        
        # ファイルが存在するか確認
        if not os.path.exists(section_file):
            logger.warning(f"Section file {section_file} does not exist")
            return False
        
        # mmdc コマンドが利用可能か確認
        if not self._check_mmdc_available():
            logger.error("mmdc command is not available. Please install mermaid-cli")
            return False
        
        # Mermaidダイアグラムを修正
        return self.fix_mermaid_in_file(section_file, max_retry)
    
    def _check_mmdc_available(self) -> bool:
        """
        mmdc コマンドが利用可能かチェックします
        
        Returns:
            bool: コマンドが利用可能な場合はTrue
        """
        try:
            subprocess.run(["mmdc", "--version"], capture_output=True, text=True)
            return True
        except Exception:
            return False


# メイン関数（直接実行時のサンプル使用法）
def main():
    """
    このモジュールを直接実行した場合のサンプル使用法
    """
    from api.openai_client import OpenAIClient
    
    # 引数解析
    import argparse
    parser = argparse.ArgumentParser(description='Validate and fix Mermaid diagrams in markdown files')
    parser.add_argument('--file', required=True, help='Markdown file containing Mermaid diagrams')
    parser.add_argument('--api-key', help='OpenAI API Key')
    parser.add_argument('--api-endpoint', help='OpenAI API Endpoint')
    parser.add_argument('--model', default='gpt-4o-mini', help='OpenAI model name')
    args = parser.parse_args()
    
    # OpenAI クライアントを初期化
    api_key = args.api_key or os.environ.get('OPENAI_API_KEY')
    api_endpoint = args.api_endpoint or os.environ.get('OPENAI_API_ENDPOINT')
    
    if not api_key or not api_endpoint:
        print("Error: API key and endpoint must be provided")
        return 1
    
    openai_client = OpenAIClient(
        endpoint=api_endpoint,
        api_key=api_key,
        deployment_name=args.model
    )
    
    # MermaidHelperを初期化して実行
    helper = MermaidHelper(openai_client)
    result = helper.process_section_file(args.file)
    
    if result:
        print(f"Successfully processed Mermaid diagrams in {args.file}")
        return 0
    else:
        print(f"Failed to process Mermaid diagrams in {args.file}")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
