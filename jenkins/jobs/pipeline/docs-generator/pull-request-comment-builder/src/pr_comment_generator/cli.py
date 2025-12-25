"""CLIエントリポイントを提供するモジュール。"""
import argparse
import json
import logging
import os
import traceback

from .generator import PRCommentGenerator


def create_argument_parser() -> argparse.ArgumentParser:
    """コマンドライン引数パーサーを生成"""
    parser = argparse.ArgumentParser(description='Generate PR comments using OpenAI API')
    parser.add_argument('--pr-diff', required=True, help='PR diff JSON file path')
    parser.add_argument('--pr-info', required=True, help='PR info JSON file path')
    parser.add_argument('--output', required=True, help='Output JSON file path')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level')
    parser.add_argument('--parallel', action='store_true', help='Use parallel processing for file fetching')
    parser.add_argument('--save-prompts', action='store_true', help='Save prompts and results to files')
    parser.add_argument('--prompt-output-dir', default='/prompts', help='Directory to save prompts and results')
    return parser


def setup_environment_from_args(args: argparse.Namespace) -> None:
    """引数に基づき環境変数を設定し、CLIの動作を制御"""
    if args.parallel:
        os.environ['PARALLEL_PROCESSING'] = 'true'

    if args.save_prompts:
        os.environ['SAVE_PROMPTS'] = 'true'
        os.environ['PROMPT_OUTPUT_DIR'] = args.prompt_output_dir

        if not os.path.exists(args.prompt_output_dir):
            os.makedirs(args.prompt_output_dir, exist_ok=True)
            print(f"Created prompt output directory: {args.prompt_output_dir}")


def main() -> None:
    """CLIエントリポイント"""
    parser = create_argument_parser()
    args = parser.parse_args()
    setup_environment_from_args(args)

    log_level = getattr(logging, args.log_level)

    try:
        generator = PRCommentGenerator(log_level=log_level)
        result = generator.generate_comment(args.pr_info, args.pr_diff)

        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        if 'error' in result:
            print(f"\nWarning: Comment generation completed with errors: {result['error']}")
            if 'usage' in result and result['usage']:
                print(f"Partial tokens used: {result['usage'].get('total_tokens', 0)}")
            raise SystemExit(1)

        print("\nComment generation completed successfully!")
        print(f"Total tokens used: {result['usage']['total_tokens']}")
        print(f"Files analyzed: {result['file_count']}")
        print(f"Total changes: {result['total_changes']}")
        print(f"Execution time: {result.get('execution_time_seconds', 0)} seconds")

        if args.save_prompts:
            print(f"Prompts and results saved to: {args.prompt_output_dir}")

    except Exception as exc:  # noqa: BLE001 既存の例外処理方針に合わせる
        print(f"Critical error: {exc}")
        traceback.print_exc()

        try:
            error_result = {
                'error': str(exc),
                'traceback': traceback.format_exc(),
                'comment': f"Critical error occurred: {exc}",
                'suggested_title': 'Error: PR Analysis Failed'
            }
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(error_result, f, indent=2, ensure_ascii=False)
        except Exception:
            print('Failed to write error information to output file')

        raise SystemExit(1)


if __name__ == '__main__':
    main()
