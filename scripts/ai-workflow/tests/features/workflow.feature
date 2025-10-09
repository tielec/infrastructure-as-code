# language: ja
機能: AI駆動開発自動化ワークフロー

  シナリオ: ワークフロー初期化とメタデータ作成
    前提 作業ディレクトリがリポジトリルートである
    もし 開発者がワークフローを初期化する
      """
      python scripts/ai-workflow/main.py init --issue-url https://github.com/tielec/infrastructure-as-code/issues/999
      """
    ならば ワークフローディレクトリ ".ai-workflow/issue-999" が作成される
    かつ "metadata.json" ファイルが存在する
    かつ metadata.json に以下の情報が含まれる:
      | フィールド        | 値                |
      | issue_number     | 999               |
      | current_phase    | requirements      |
      | workflow_version | 1.0.0             |
    かつ すべてのフェーズのステータスが "pending" である

  シナリオ: 既存ワークフローが存在する場合はエラーを表示する
    前提 作業ディレクトリがリポジトリルートである
    かつ ワークフローが既に初期化されている
    もし 開発者が同じIssue番号でワークフローを初期化しようとする
      """
      python scripts/ai-workflow/main.py init --issue-url https://github.com/tielec/infrastructure-as-code/issues/999
      """
    ならば コマンドが失敗する
    かつ エラーメッセージ "Workflow already exists" が表示される

  シナリオ: CLIヘルプメッセージを表示する
    前提 作業ディレクトリがリポジトリルートである
    もし 開発者がヘルプコマンドを実行する
      """
      python scripts/ai-workflow/main.py --help
      """
    ならば 利用可能なコマンドのリストが表示される
