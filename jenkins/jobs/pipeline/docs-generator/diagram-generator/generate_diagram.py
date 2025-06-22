#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import os
import subprocess
from typing import List, Dict, Any

from openai import OpenAI

# ------------------------------------------------------------------------------
# 共通で利用する文章・テンプレートを定義
# ------------------------------------------------------------------------------

COMMON_CONDITIONS = """\
# 条件:
- show=False にして、画像生成のみ行う
- 出力ファイル名は 'architecture_diagram.png'
- 'diagrams==0.24.4' で動作すること
- 「```python」や「```」などのMarkdown記法は含めずに、Pythonコードのみを返してください。
- 必ず使用する全ての要素（AWSやonprem等）は正しいパスから適切にimportしてください。
"""

IMPORT_EXAMPLES = """\
# import例:
```
from diagrams.onprem.aggregator import Fluentd, Vector
from diagrams.onprem.analytics import Hadoop, Hive, Spark, Presto
from diagrams.onprem.auth import Oauth2Proxy
from diagrams.onprem.cd import Tekton
from diagrams.onprem.certificates import CertManager, LetsEncrypt
from diagrams.onprem.ci import Jenkins, GithubActions, Gitlabci
from diagrams.onprem.client import User
from diagrams.onprem.compute import Server
from diagrams.onprem.container import Docker, K3S
from diagrams.onprem.database import Postgresql, Mysql, Cassandra, Mongodb
from diagrams.onprem.iac import Ansible, Terraform
from diagrams.onprem.inmemory import Redis
from diagrams.onprem.logging import Fluentbit, Loki
from diagrams.onprem.monitoring import Grafana, Prometheus
from diagrams.onprem.network import Apache, Envoy, Nginx
from diagrams.onprem.queue import Kafka, Rabbitmq
from diagrams.onprem.security import Vault
from diagrams.aws.analytics import Athena, EMR, Glue, Kinesis, Quicksight, Redshift
from diagrams.aws.compute import (
    Batch,
    EC2,
    EC2AutoScaling,
    EC2ContainerRegistry,
    ElasticContainerService,
    ElasticKubernetesService,
    ElasticBeanstalk,
    Fargate,
    Lambda,
)
from diagrams.aws.database import Aurora, Dynamodb, Elasticache, RDS
from diagrams.aws.devtools import Codebuild, Codecommit, Codepipeline
from diagrams.aws.integration import Eventbridge, SNS, SQS, StepFunctions
from diagrams.aws.management import Cloudformation, Cloudtrail, Cloudwatch, SystemsManager
from diagrams.aws.ml import Comprehend, Lex, Polly, Rekognition, Sagemaker, Transcribe, Translate
from diagrams.aws.network import (
    APIGateway,
    CloudFront,
    DirectConnect,
    ElbApplicationLoadBalancer,
    ElbNetworkLoadBalancer,
    NATGateway,
    Route53,
    VPC,
)
from diagrams.aws.security import IAM, KMS, SecretsManager, Shield, WAF
from diagrams.aws.storage import Backup, EBS, EFS, S3
from diagrams.programming.flowchart import Action, Database, Decision, Document, ManualInput, StartEnd
from diagrams.programming.framework import (
    Angular,
    Django,
    Dotnet,
    Fastapi,
    Flask,
    Flutter,
    Graphql,
    Laravel,
    Nextjs,
    Rails,
    React,
    Spring,
    Svelte,
    Vue,
)
from diagrams.programming.language import (
    Bash,
    C,
    Cpp,
    Csharp,
    Dart,
    Go,
    Java,
    Javascript,
    Kotlin,
    Nodejs,
    Php,
    Python,
    R,
    Ruby,
    Rust,
    Swift,
    Typescript,
)
from diagrams.programming.runtime import Dapr
```
"""

# 新規作成時のプロンプトテンプレート
NEW_CREATION_PROMPT = """\
以下の要望を満たすPythonコードを出力してください:
ユーザーの要望: {requirement}

{common_conditions}

{import_examples}
"""

# 既存コードアップデート時のプロンプトテンプレート
UPDATE_PROMPT = """\
以下の既存Python(diagrams)コードをアップデートし、ユーザーの要望を満たすよう修正してください。

既存コード:
```
{existing_code}
```

ユーザーの要望:
{requirement}

{common_conditions}
"""

# エラー修正用の追加入力テンプレート
ERROR_FIX_PROMPT = """\
実行したコード:
```
{current_code}
```

実行したところ、以下のエラーが発生しました:
```
{error_output}
```

このエラーを修正し、正しいPython(diagrams)コードを再度出力してください。

{common_conditions}
- ImportErrorが発生している場合は、該当のimportを `diagrams.programming.flowchart.Action` に変更してください。
- もし不足しているimport文があれば、以下を参考に追加してください。

{import_examples}
"""

# システムメッセージ
SYSTEM_MESSAGE = {
    "role": "system",
    "content": (
        "あなたはPythonのDiagramsライブラリを使ってアーキテクチャ図を生成・修正するアシスタントです。"
        "ユーザーの要望に応じて、図を描画するPythonコード（diagram.py）を新規に作成または既存コードをアップデートしてください。"
    )
}

# ------------------------------------------------------------------------------
# メッセージ生成関数
# ------------------------------------------------------------------------------

def build_initial_user_message(existing_code: str, requirement: str) -> Dict[str, str]:
    """
    新規作成または既存コードアップデートの指示を行うためのユーザーメッセージを生成する。
    """
    if existing_code:
        print("[INFO] Update mode (existing diagram code provided).")
        content = UPDATE_PROMPT.format(
            existing_code=existing_code,
            requirement=requirement,
            common_conditions=COMMON_CONDITIONS,
        )
    else:
        print("[INFO] Creation mode (no existing diagram code provided).")
        content = NEW_CREATION_PROMPT.format(
            requirement=requirement,
            common_conditions=COMMON_CONDITIONS,
            import_examples=IMPORT_EXAMPLES,
        )
    return {"role": "user", "content": content}


def build_error_fix_message(current_code: str, error_output: str) -> Dict[str, str]:
    """
    diagram.py 実行時に発生したエラーを元に修正を依頼するメッセージを生成する。
    """
    content = ERROR_FIX_PROMPT.format(
        current_code=current_code,
        error_output=error_output,
        common_conditions=COMMON_CONDITIONS,
        import_examples=IMPORT_EXAMPLES,
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
        help='Path to a file containing existing diagram.py code (if empty, will create new)'
    )
    parser.add_argument('--output-dir', default='reports/images', help='Directory to store the generated diagram')
    parser.add_argument('--model-name', default='gpt-4.1', help='OpenAI model name')
    return parser.parse_args()


def load_existing_diagram_code(filepath: str) -> str:
    """
    既存の diagram.py ファイルがあれば読み込み、その内容を文字列として返す。
    """
    if filepath and os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read().strip()
    return ""


def generate_diagram_code(
    client: OpenAI,
    messages: List[Dict[str, Any]],
    model: str,
) -> str:
    """
    OpenAI に会話メッセージを送り、生成されたコードを取得して返す。
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

    generated_code = (
        response.choices[0]
        .message
        .content
        .strip('`\n ')
        .replace('```python', '')
        .replace('```', '')
    )
    print("===== Response Content (Generated Code) =====")
    print(generated_code)
    print("=============================================")
    return generated_code


def write_code_to_file(filename: str, code: str) -> None:
    """
    文字列として受け取ったコードを指定ファイルに書き込む。
    """
    with open(filename, "w", encoding="utf-8") as f:
        f.write(code)


def run_diagram_code_and_fix_if_needed(
    max_retry: int,
    diagram_filename: str,
    chat_history: List[Dict[str, str]],
    client: OpenAI,
    model: str
) -> None:
    """
    diagram.py を実行し、エラーが出た場合は修正を依頼して再実行する。
    成功もしくはリトライ上限に達すると処理終了。
    """
    for i in range(max_retry):
        print(f"[INFO] Attempt {i+1}/{max_retry} to run {diagram_filename}")
        proc = subprocess.run(["python", diagram_filename], capture_output=True, text=True)

        if proc.returncode == 0:
            print("[INFO] Diagram generation succeeded.")
            return
        else:
            error_output = proc.stderr.strip()
            print("[WARN] diagram.py failed. stderr:")
            print(error_output)
            print("[WARN] Requesting GPT fix...")

            # 実行失敗したコードを再読み込み
            try:
                with open(diagram_filename, "r", encoding="utf-8") as diag_file:
                    current_code = diag_file.read()
            except FileNotFoundError:
                current_code = "[diagram.py not found]"

            # エラー修正を依頼するメッセージを生成
            error_message = build_error_fix_message(current_code, error_output)
            chat_history.append(error_message)

            # GPTから修正版を生成
            fixed_code = generate_diagram_code(client, chat_history, model)
            write_code_to_file(diagram_filename, fixed_code)

    raise SystemExit("[ERROR] Failed to generate diagram after max retries.")


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

    # 既存コードを読み込み
    existing_diagram_code = load_existing_diagram_code(args.diagram_code_file)

    # システムメッセージとユーザーメッセージを作成
    chat_history = [SYSTEM_MESSAGE]
    chat_history.append(
        build_initial_user_message(existing_diagram_code, args.requirement)
    )

    # 1. コードを生成して書き込み
    code = generate_diagram_code(client, chat_history, args.model_name)
    write_code_to_file("diagram.py", code)

    # 2. diagram.py を実行 & エラー修正リトライ
    run_diagram_code_and_fix_if_needed(
        max_retry=5,
        diagram_filename="diagram.py",
        chat_history=chat_history,
        client=client,
        model=args.model_name
    )

    # 3. 出力された画像を指定ディレクトリへ移動
    check_and_move_diagram_image(args.output_dir, "architecture_diagram.png")

    print("[INFO] Done successfully.")


if __name__ == "__main__":
    main()
