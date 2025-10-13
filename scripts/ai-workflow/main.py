"""AI Workflow - CLIエントリーポイント

このファイルは、AI駆動ワークフローのエントリーポイントです。
CLIコマンドの定義は cli/commands.py に分離されています。

使用例:
    $ python main.py init --issue-url https://github.com/owner/repo/issues/380
    $ python main.py execute --issue 380 --phase planning
    $ python main.py status --issue 380
    $ python main.py resume --issue 380
"""

from cli.commands import cli


if __name__ == '__main__':
    cli()
