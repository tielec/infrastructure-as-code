#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import os
import subprocess
import re
from typing import List, Dict, Any

from openai import OpenAI

# ------------------------------------------------------------------------------
# Mermaid 用の共通メッセージ・テンプレートを定義
# ------------------------------------------------------------------------------

COMMON_CONDITIONS = """\
# 条件:
- Mermaid のコード（```mermaid は不要）をテキストとして出力してください。
- 出力ファイル名は 'diagram.mmd'
- 画像生成は mmdc (Mermaid CLI) を使用し、最終的に 'architecture_diagram.png' を出力する形としてください。
- 不要なMarkdownの記法 (```mermaid や ```python など) は含めないでください。
- 可能な場合はサブグラフやクラス定義、アイコンなどを活用し、可読性を向上させてください。
- 多数の要素があっても破綻しないよう、複数レイヤー（サブグラフなど）や視認性を考慮してください。
- 相互依存関係や多対多関係がある場合は、ER図やクラス図を検討してください。
"""

# Mermaid コード生成時のプロンプトテンプレート (新規作成)
NEW_CREATION_PROMPT = """\
あなたはMermaidの専門家です。以下の要望に沿って、最適なMermaidダイアグラム（{diagram_type}）を生成してください。

ユーザーの要望:
{requirement}

追加で満たしてほしい点:
- テーマやスタイルを適宜設定し、視認性や一貫性を高めてください。
- 必要に応じて classDef を用い、ノードの色分けや強調を行ってください。
- 大きな図の場合は subgraph を用いたグルーピングにより階層構造を明示してください。

{common_conditions}
"""

# Mermaid コード修正時のプロンプトテンプレート (既存コードアップデート)
UPDATE_PROMPT = """\
あなたはMermaidの専門家です。以下の既存Mermaidコードを元に、ユーザーの追加要望を満たすようアップデートしてください。

既存コード:
```
{existing_code}
```

ユーザーの要望:
{requirement}

追加で満たしてほしい点:
- テーマやスタイルを適宜設定し、視認性や一貫性を高めてください。
- 必要に応じて classDef を用い、ノードの色分けや強調を行ってください。
- 大きな図の場合は subgraph を用いたグルーピングにより階層構造を明示してください。

{common_conditions}
"""

# エラー修正用の追加入力テンプレート (修正版)
ERROR_FIX_PROMPT = """\
以下のMermaidコードを mmdc コマンドで実行したところエラーが発生しました。コードの不備を修正し、再度正しいMermaidコードを出力してください。

実行したMermaidコード:
```
{current_code}
```

mmdcコマンド実行時に発生したエラー:
```
{error_output}
```

{common_conditions}

# 注意点:
- ノードのラベルに半角括弧 ( ) が混在するとパースエラーが出る場合があります。
- 行末に余計な文字が残っていないかチェックしてください。
- サブグラフは `subgraph ... end` を正しくペアで書いてください。
- classDef / class などの構文は正しく書いてください。
"""

# システムメッセージ
SYSTEM_MESSAGE = {
    "role": "system",
    "content": (
        "あなたはMermaid記法を使ってアーキテクチャ図などを生成・修正するアシスタントです。"
        "ユーザーの要望に応じて、Mermaidコード（diagram.mmd）を新規に作成または既存コードをアップデートしてください。"
        "複雑な依存関係や階層構造、視覚的にわかりやすいアイコンやスタイルを活用したMermaidダイアグラムの生成が求められます。"
    )
}

# ------------------------------------------------------------------------------
# ダイアグラム種別を自動推定する簡易関数 (例示)
# ------------------------------------------------------------------------------

def detect_diagram_type(requirement: str) -> str:
    """
    ユーザー要求文字列からキーワードに応じて簡易的にダイアグラム種別を推定する。
    必要に応じてロジックを拡張可能。
    """
    req_lower = requirement.lower()
    # 例: ER図・クラス図を優先的に判定
    if "er" in req_lower or "entity" in req_lower:
        return "erDiagram"
    if "class" in req_lower or "継承" in req_lower:
        return "classDiagram"
    if "状態" in req_lower or "state" in req_lower:
        return "stateDiagram"
    if "シーケンス" in req_lower or "sequence" in req_lower:
        return "sequenceDiagram"
    # キーワードが無ければフローチャート扱い (適宜調整可能)
    return "flowchart"

# ------------------------------------------------------------------------------
# メッセージ生成関数
# ------------------------------------------------------------------------------

def build_initial_user_message(
    existing_code: str,
    requirement: str,
    diagram_type: str
) -> Dict[str, str]:
    """
    新規作成または既存コードアップデートの指示を行うためのユーザーメッセージを生成する。
    """
    if existing_code:
        print("[INFO] Update mode (existing Mermaid code provided).")
        content = UPDATE_PROMPT.format(
            existing_code=existing_code,
            requirement=requirement,
            common_conditions=COMMON_CONDITIONS,
        )
    else:
        print("[INFO] Creation mode (no existing Mermaid code provided).")
        content = NEW_CREATION_PROMPT.format(
            requirement=requirement,
            diagram_type=diagram_type,
            common_conditions=COMMON_CONDITIONS,
        )
    return {"role": "user", "content": content}


def build_error_fix_message(current_code: str, error_output: str) -> Dict[str, str]:
    """
    mmdc 実行時に発生したエラーを元に修正を依頼するメッセージを生成する。
    """
    content = ERROR_FIX_PROMPT.format(
        current_code=current_code,
        error_output=error_output,
        common_conditions=COMMON_CONDITIONS,
    )
    return {"role": "user", "content": content}

# ------------------------------------------------------------------------------
# メイン処理
# ------------------------------------------------------------------------------

def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument('--requirement', required=True, help='User requirement for the diagram')
    parser.add_argument(
        '--diagram-code-file', default='',
        help='Path to a file containing existing diagram.mmd code (if empty, will create new)'
    )
    parser.add_argument('--output-dir', default='reports/images', help='Directory to store the generated diagram')
    parser.add_argument('--model-name', default='gpt-4.1', help='OpenAI model name')
    parser.add_argument('--diagram-type', default='', help='If specified, override the auto-detected diagram type')
    return parser.parse_args()


def load_existing_diagram_code(filepath: str) -> str:
    """
    既存の diagram.mmd ファイルがあれば読み込み、その内容を文字列として返す。
    """
    if filepath and os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read().strip()
    return ""


def generate_mermaid_code(
    client: OpenAI,
    messages: List[Dict[str, Any]],
    model: str
) -> str:
    """
    OpenAI に会話メッセージを送り、生成されたMermaidコードを取得して返す。
    """
    # デバッグ用にメッセージ内容を出力
    print("===== Prompt to OpenAI =====")
    for i, msg in enumerate(messages, start=1):
        print(f"\nMessage {i} - Role: {msg['role']}")
        print("Content:")
        print(msg["content"])
    print("===================================")

    print("[INFO] Sending request to OpenAI...")
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.3,
        max_tokens=10000,
        top_p=0.8,
        frequency_penalty=0.0,
        presence_penalty=0.0,
    )
    print("[INFO] Received response from OpenAI.")

    # Mermaidコードだけを抜き出す（不要な ``` などを取り除く）
    generated_code = (
        response.choices[0]
        .message
        .content
        .strip('`\n ')
        .replace('```mermaid', '')
        .replace('```', '')
    )

    # 先頭にテーマや初期化コードなどを挿入 (例: forestテーマを使用)
    # 必要に応じてユーザー側で変更可能
    # 例: custom CSSクラスを定義しておく
    style_injection = """%%{init: {'theme': 'forest', 'themeVariables': { 'primaryColor': '#8FBC8F'}}}%%
%%{init: {'logLevel': 'fatal'}}%%
"""
    # すでにinitディレクティブが入っていない場合のみ注入する例
    # (すでにユーザーが独自テーマを使っている可能性があるため簡易チェック)
    if "%%{init:" not in generated_code:
        generated_code = style_injection + generated_code

    print("===== Response Content (Generated Mermaid Code) =====")
    print(generated_code)
    print("=====================================================")
    return generated_code


def sanitize_code(code: str) -> str:
    """
    Mermaid記法の不備を軽減し、余分な解説文や行を削除する。
    - ノード名に含まれる ( ) を - に置換（エスケープ代わり）
    - graph / flowchart / classDiagram 等が現れるまでの行はすべて削除
    - コード末尾に余計な解説文行があれば削除
    """
    # 1) 行単位に分割
    lines = code.splitlines()

    # 2) Mermaid本体の開始行を探す
    #    例えば "graph TD", "flowchart LR", "erDiagram", "classDiagram", "sequenceDiagram" など
    mermaid_start_pattern = re.compile(r'^\s*(graph|flowchart|classDiagram|erDiagram|stateDiagram|sequenceDiagram|journey|gantt|mindmap)\b', re.IGNORECASE)

    start_index = None
    for i, line in enumerate(lines):
        if mermaid_start_pattern.search(line):
            start_index = i
            break

    # Mermaidの定義が見つからなければ、そのまま返す（あるいは空文字返す）
    if start_index is None:
        return ""

    # 不要な先頭行を捨て、以降だけを処理
    lines = lines[start_index:]

    # 3) Mermaid本体終了後に解説文が出てくる場合に備え、"```" や "このコードを" などが始まる行で終了する
    #    例: 不要そうな日本語文章やMarkdownブロック終了行などを検出して切り落とす
    end_index = None
    invalid_line_pattern = re.compile(r'(```|このコード|^以下は|^#)', re.IGNORECASE)
    for i, line in enumerate(lines):
        # "```" や "このコード" などが始まったらそこから先をカット
        if invalid_line_pattern.search(line):
            end_index = i
            break

    if end_index is not None:
        lines = lines[:end_index]

    # 4) ノードラベルに含まれる "(" / ")" を一旦 "-" に置換してパースエラーを抑制する(必要に応じて)
    sanitized_lines = []
    for line in lines:
        # ただし classDef などを壊したくないので、ALB(...) のようなノードだけ対象にする
        # 簡易的には単純置換:
        line = line.replace("(", "_").replace(")", "_")
        sanitized_lines.append(line)

    # 5) 仕上げで join
    sanitized_code = "\n".join(sanitized_lines).strip()

    return sanitized_code


def write_code_to_file(filename: str, code: str) -> None:
    """
    文字列として受け取ったコードを指定ファイルに書き込む。
    """
    with open(filename, "w", encoding="utf-8") as f:
        f.write(code)


def run_mermaid_and_fix_if_needed(
    max_retry: int,
    mmd_filename: str,
    chat_history: List[Dict[str, str]],
    client: OpenAI,
    model: str
) -> None:
    """
    mmdc を実行し、エラーが出た場合は修正を依頼して再実行する。
    成功もしくはリトライ上限に達すると処理終了。
    
    --no-sandbox オプションを付けるために puppeteer-config.json を用いたり
    -p オプションで直接指定したりしている。
    """
    puppeteer_config = "puppeteer-config.json"
    with open(puppeteer_config, "w", encoding="utf-8") as f:
        f.write('{"args":["--no-sandbox","--disable-setuid-sandbox"]}')

    for i in range(max_retry):
        print(f"[INFO] Attempt {i+1}/{max_retry} to run mmdc on {mmd_filename}")
        cmd = [
            "mmdc",
            "-i", mmd_filename,
            "-o", "architecture_diagram.png",
            "-p", puppeteer_config
        ]
        print(f"[INFO] Running command: {' '.join(cmd)}")

        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0:
            print("[INFO] Mermaid diagram generation succeeded.")
            return
        else:
            error_output = (proc.stderr or proc.stdout).strip()
            print("[WARN] mmdc failed. Output:")
            print(error_output)
            print("[WARN] Requesting GPT fix...")

            try:
                with open(mmd_filename, "r", encoding="utf-8") as f:
                    current_code = f.read()
            except FileNotFoundError:
                current_code = "[diagram.mmd not found]"

            # GPT にエラー修正を依頼
            error_message = build_error_fix_message(current_code, error_output)
            chat_history.append(error_message)
            fixed_code = generate_mermaid_code(client, chat_history, model)
            fixed_code = sanitize_code(fixed_code)
            write_code_to_file(mmd_filename, fixed_code)

    raise SystemExit("[ERROR] Failed to generate mermaid diagram after max retries.")


def check_and_move_diagram_image(output_dir: str, diagram_image: str) -> None:
    """
    出力先に architecture_diagram.png を移動する。ファイルが存在しない場合はエラーを報告。
    """
    if not os.path.exists(diagram_image):
        raise SystemExit(f"[ERROR] No '{diagram_image}' found despite successful run.")

    os.makedirs(output_dir, exist_ok=True)
    destination = os.path.join(output_dir, diagram_image)
    os.replace(diagram_image, destination)
    print(f"[INFO] Moved {diagram_image} to: {destination}")


def main() -> None:
    """
    メイン処理のエントリーポイント
    """
    args = parse_arguments()

    openai_key = os.environ.get("OPENAI_API_KEY", "")

    if not openai_key:
        raise SystemExit("[ERROR] OPENAI_API_KEY is not set.")

    client = OpenAI(
        api_key=openai_key
    )

    # 既存の Mermaid コードを読み込み
    existing_mermaid_code = load_existing_diagram_code(args.diagram_code_file)

    # ダイアグラム種別を推定または指定されたものを使用
    if args.diagram_type:
        diagram_type = args.diagram_type
        print(f"[INFO] Diagram type overridden by user: {diagram_type}")
    else:
        diagram_type = detect_diagram_type(args.requirement)
        print(f"[INFO] Auto-detected diagram type: {diagram_type}")

    # システムメッセージとユーザーメッセージを作成
    chat_history = [SYSTEM_MESSAGE]
    initial_message = build_initial_user_message(
        existing_mermaid_code,
        args.requirement,
        diagram_type
    )
    chat_history.append(initial_message)

    # 1. コードを生成して書き込み (初回)
    code = generate_mermaid_code(client, chat_history, args.model_name)
    code = sanitize_code(code)
    write_code_to_file("diagram.mmd", code)

    # 2. mmdc を実行 & エラー修正リトライ
    run_mermaid_and_fix_if_needed(
        max_retry=5,
        mmd_filename="diagram.mmd",
        chat_history=chat_history,
        client=client,
        model=args.model_name
    )

    # 3. 出力された画像を指定ディレクトリへ移動
    check_and_move_diagram_image(args.output_dir, "architecture_diagram.png")

    print("[INFO] Done successfully.")


if __name__ == "__main__":
    main()
