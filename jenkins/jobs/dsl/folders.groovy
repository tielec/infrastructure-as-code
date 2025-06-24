// Admin Jobsフォルダの作成
folder('Admin_Jobs') {
    displayName('Admin Jobs')
    description('''\
            |このフォルダーには、管理者用のジョブが含まれています。
            |
            |### 概要
            |Jenkins環境の管理・保守に必要な各種ジョブを集約しています。
            |設定のバックアップ/リストア、GitHub連携の設定、ユーザー管理、
            |システムテストなどの管理タスクを実行できます。
            |
            |### 注意事項
            |* 一部のジョブはmasterノードでの実行が必要です
            |* 管理者権限が必要なジョブが含まれています
            |* 実行前に各ジョブの説明を確認してください
            |'''.stripMargin())
}

// Account_Setupフォルダの作成
folder('Account_Setup') {
    displayName('Account Setup Jobs')
    description('''\
        |このフォルダーには、アカウントセットアップを行うジョブが含まれています。
        |
        |### 概要
        |* 新規ユーザーのアカウントセットアップを自動化するジョブを管理
        |'''.stripMargin())
}

// Playgroundsフォルダの作成
folder('Playgrounds') {
    displayName('Playgrounds for Job Creation and Testing')
    description('''\
        |このフォルダーは、ユーザーが自由にジョブの作成と検証を行うための場所です。
        |
        |### 目的
        |* 各ユーザーが独自のジョブを作成し、安全に検証できる環境を提供
        |* CI/CDパイプラインの実験や新機能のテストに活用
        |
        |### 使用方法
        |1. このフォルダ内に自分の名前でサブフォルダを作成してください  
        |   例: Playgrounds/yamada/
        |2. 作成したフォルダ内で自由にジョブを作成・検証できます
        |
        |### 注意事項
        |* 他のユーザーのフォルダには変更を加えないでください
        |* リソースの過剰な使用は避けてください
        |* 本番環境に影響を与える可能性のある操作は行わないでください
        |* 定期的に不要なジョブやフォルダの清掃を行ってください
        |
        |不明点がある場合は管理者に確認してください。
        |'''.stripMargin())
}

// Code_Quality_Checkerフォルダの作成
folder('Code_Quality_Checker') {
    displayName('Code Quality Checker Jobs')
    description('''\
        |このフォルダーには、コード品質チェックを行うジョブが含まれています。
        |
        |### 概要
        |各プロジェクトのソースコードの品質を自動的に分析・評価します。
        |循環的複雑度（Cyclomatic Complexity）の測定など、コード品質の向上と技術的負債の
        |管理に必要なジョブを集約しています。
        |
        |### 主な機能
        |* **循環的複雑度分析** - 関数の複雑さを数値化し、リファクタリング対象を特定
        |
        |### メトリクスの解釈
        |* **複雑度 1-10**: シンプルで理解しやすい（推奨）
        |* **複雑度 11-15**: やや複雑（要注意）
        |* **複雑度 16以上**: 複雑でリスクが高い（リファクタリング推奨）
        |
        |### 実行方法
        |* 定期実行: 毎週月曜日の朝9時に自動実行
        |* 手動実行: 各ジョブの「Build with Parameters」から実行
        |'''.stripMargin())
}

// 各リポジトリ用のCode Quality Checkerフォルダを作成
jenkinsManagedRepositories.each { name, repo ->
    folder("Code_Quality_Checker/${name}") {
        displayName("Code Quality - ${name}")
        description("""\
            |${name}リポジトリのコード品質チェックジョブ
            |
            |### 提供機能
            |* **循環的複雑度分析** - 複雑度の測定とレポート生成
            |* **閾値チェック** - 設定した閾値を超える関数の自動検出
            |* **HTMLレポート** - 視覚的に分かりやすい分析結果の表示
            |
            |### レポート内容
            |* 全関数の複雑度一覧（上位300件）
            |* 統計情報（総関数数、平均複雑度、最大複雑度など）
            |* 問題のある関数のハイライト（色分け表示）
            |
            |### カスタマイズ可能な閾値
            |* **複雑度閾値**: デフォルト15（変更可能）
            |* **最小コード行数**: デフォルト100行
            |
            |### 除外設定
            |テストコード、ビルド成果物、外部ライブラリなどを自動的に除外
            |""".stripMargin())
    }
}

// Docs_Generatorフォルダの作成
folder('Document_Generator') {
    displayName('Document Generator Jobs')
    description('''\
        |このフォルダーには、ドキュメント自動生成を行うジョブが含まれています。
        |
        |### 概要
        |各プロジェクトのソースコードから技術ドキュメントを自動生成します。
        |Doxygenによるコード解析、コメント自動挿入、プルリクエストへの
        |ドキュメントフィードバックなど、開発ドキュメントの品質向上と
        |保守性を高めるためのジョブを管理しています。
        |
        |### 構成
        |* プロジェクトごとにサブフォルダで管理
        |* GitHub連携による自動実行とマニュアル実行の両方に対応
        |* Doxygen、技術文書生成、PRコメント機能を提供
        |'''.stripMargin())
}


// 各リポジトリ用のフォルダを作成
jenkinsManagedRepositories.each { name, repo ->
    folder("Document_Generator/${name}") {
        displayName("Document Generator - ${name}")
        description("""\
            |${name}リポジトリのドキュメント自動生成ジョブ
            |
            |### 提供機能
            |* **Doxygenコメント自動挿入** - ソースコードにDoxygenコメントを自動追加
            |* **Doxygen HTML生成** - コードからHTML形式のAPIドキュメントを生成
            |* **PRコメント機能** - プルリクエストにドキュメント関連のフィードバックを投稿
            |* **技術文書生成** - プロジェクトの技術文書を自動作成
            |
            |### 実行方法
            |* GitHub Webhookによる自動実行（*_github_triggerジョブ）
            |* 手動実行による個別処理
            |""".stripMargin())
    }
}

folder('Shared_Library') {
    displayName('Shared Library Tests & Examples')
    description('''\
        |このフォルダーには、共有ライブラリのテストやサンプルジョブが含まれています。
        |
        |### 概要
        |* 共有ライブラリの機能をテストするためのジョブを管理
        |* 共有ライブラリの使用例を示すサンプルジョブを管理
        |'''.stripMargin())
}

folder('Shared_Library/AWS_Utils') {
    displayName('AWS Utilities Tests & Examples')
    description('''\
        |このフォルダーには、AWSユーティリティのテストジョブが含まれています。
        |
        |### 概要
        |* AWSの操作をテストするジョブを管理
        |'''.stripMargin())
}

folder('Shared_Library/Jenkins_Cli_Utils') {
    displayName('Jenkins CLI Utilities Tests & Examples')
    description('''\
        |このフォルダーには、Jenkins CLIユーティリティのテストジョブが含まれています。
        |
        |### 概要
        |* Jenkins CLIを使用した操作をテストするジョブを管理
        |* Jenkins CLIの機能を検証するためのサンプルジョブを管理
        |'''.stripMargin())
}

folder('Shared_Library/Git_Utils') {
    displayName('Git Utilities Tests & Examples')
    description('''\
        |このフォルダーには、Gitユーティリティのテストジョブが含まれています。
        |
        |### 概要
        |* Gitの操作をテストするジョブを管理
        |'''.stripMargin())
}

folder('Pipeline_Tests') {
    displayName('Pipeline Tests')
    description('''\
        |このフォルダーには、パイプラインのテストジョブが含まれています。
        |
        |### 概要
        |* パイプラインの機能をテストするためのジョブを管理
        |* パイプラインスクリプトの検証やデバッグに使用
        |'''.stripMargin())
}

folder('Pipeline_Tests/Document_Generator') {
    displayName('Document Generator Tests')
    description('''\
        |このフォルダーには、ドキュメント自動生成パイプラインのテストジョブが含まれています。
        |
        |### 概要
        |* ドキュメント自動生成パイプラインの機能をテストするためのジョブを管理
        |* パイプラインスクリプトの検証やデバッグに使用
        |'''.stripMargin())
}
