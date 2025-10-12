# language: ja
フィーチャ: 実装フェーズとテストコード実装フェーズの分離

  Issue #324の要件として、Phase 4（implementation）とPhase 5（test_implementation）を分離し、
  各フェーズの責務を明確化する。

  背景:
    前提 AIワークフローが初期化されている
    かつ metadata.jsonが存在する

  シナリオ: AC-001 - Phase 5（test_implementation）が新設されている
    もし "ai-workflow execute --phase test_implementation --issue 324" を実行する
    ならば Phase 5（test_implementation）が正常に実行される
    かつ ".ai-workflow/issue-324/05_test_implementation/output/test-implementation.md" が生成される
    かつ metadata.jsonのphases['test_implementation']['status']が 'completed' になる

  シナリオ: AC-002 - Phase 5でテストコードのみが実装される
    前提 Phase 4（implementation）が完了している
    かつ 実コードが実装されている
    もし Phase 5（test_implementation）を実行する
    ならば テストファイル（test_*.py、*.test.js等）が作成される
    かつ 実コード（src/配下のビジネスロジック等）は変更されない
    かつ test-implementation.mdにテストコード実装のログが記録される

  シナリオ: AC-003 - Phase 4では実コードのみが実装される
    前提 Phase 3（test_scenario）が完了している
    もし Phase 4（implementation）を実行する
    ならば 実コード（src/配下のビジネスロジック等）が作成される
    かつ テストファイル（test_*.py等）は作成されない
    かつ implementation.mdに実コード実装のログが記録される

  シナリオ: AC-004 - 既存のワークフロー（Phase 1-7）は引き続き動作する
    前提 Phase 1-7構成の既存metadata.jsonが存在する
    もし WorkflowState(metadata_path)でロードする
    ならば マイグレーション処理が自動実行される
    かつ metadata.jsonがPhase 0-8構成に更新される
    かつ エラーが発生しない
    かつ 既存フェーズのデータが保持される

  シナリオ: AC-005 - Jenkinsでの自動実行が可能
    前提 JenkinsパイプラインでAIワークフローを実行する環境
    もし 全フェーズ（Phase 0-8）を順次実行する
    ならば 各フェーズが正常に完了する
    かつ 各フェーズの成果物が ".ai-workflow/issue-324/" 配下に保存される
    かつ metadata.jsonが各フェーズ完了時に更新される

  シナリオ: AC-006 - クリティカルシンキングレビューが正しく機能する
    前提 Phase 5（test_implementation）が完了している
    もし Phase 5のreview()メソッドを実行する
    ならば レビュー結果が 'PASS'、'PASS_WITH_SUGGESTIONS'、'FAIL' のいずれかで返される
    かつ レビュー結果が ".ai-workflow/issue-324/05_test_implementation/review/result.md" に保存される
    かつ レビュー結果がGitHub Issueにコメント投稿される

  シナリオ: AC-007 - metadata.jsonにtest_implementationフェーズが記録される
    前提 ワークフローが初期化されている
    もし metadata.jsonを読み込む
    ならば "phases" 辞書に "test_implementation" が含まれている
    かつ "test_implementation" フェーズの "status" フィールドが存在する
    かつ フェーズの順序が正しい（planning, requirements, design, test_scenario, implementation, test_implementation, testing, documentation, report）

  シナリオ: AC-008 - 全フェーズのGit auto-commit & pushが正しく動作する
    前提 各フェーズが完了している
    もし 各フェーズのrun()メソッドが実行される
    ならば 成果物がGitにコミットされる
    かつ コミットメッセージが "[ai-workflow] Phase X (phase_name) - status" 形式である
    かつ リモートリポジトリにプッシュされる

  シナリオ: Phase 5はテストコード実装のみを担当する
    前提 Phase 4で実コードが実装されている
    かつ Phase 3でテストシナリオが作成されている
    もし Phase 5を実行する
    ならば Phase 3のテストシナリオが参照される
    かつ Phase 4の実装ログが参照される
    かつ テストコードが作成される
    かつ 実コードは変更されない

  シナリオ: Phase 5はPhase 4の完了が前提である
    前提 Phase 4が未完了の状態
    もし Phase 5を実行しようとする
    ならば エラーメッセージが表示される
    かつ "Phase 4 (implementation) must be completed before Phase 5" と表示される
    かつ Phase 5は実行されない

  シナリオ: Phase 6はPhase 5の完了が前提である
    前提 Phase 5が未完了の状態
    もし Phase 6を実行しようとする
    ならば エラーメッセージが表示される
    かつ "Phase 5 (test_implementation) must be completed before Phase 6" と表示される
    かつ Phase 6は実行されない

  シナリオ: 古いmetadata.jsonが自動的にマイグレーションされる
    前提 Phase 1-7構成のmetadata.jsonが存在する
    かつ "planning" フェーズが存在しない
    かつ "test_implementation" フェーズが存在しない
    もし WorkflowState(metadata_path)でロードする
    ならば "[INFO] Migrating metadata.json: Adding planning phase" と表示される
    かつ "[INFO] Migrating metadata.json: Adding test_implementation phase" と表示される
    かつ metadata.jsonに "planning" フェーズが追加される
    かつ metadata.jsonに "test_implementation" フェーズが追加される
    かつ 既存の "requirements" フェーズのデータが保持される
    かつ 既存の "design" フェーズのデータが保持される

  シナリオ: Phase 5のプロンプトファイルが存在する
    前提 AIワークフローが初期化されている
    もし プロンプトディレクトリを確認する
    ならば "scripts/ai-workflow/prompts/test_implementation/execute.txt" が存在する
    かつ "scripts/ai-workflow/prompts/test_implementation/review.txt" が存在する
    かつ "scripts/ai-workflow/prompts/test_implementation/revise.txt" が存在する
    かつ 各プロンプトファイルの内容が適切である

  シナリオ: フェーズ番号が正しく定義されている
    前提 BasePhase.PHASE_NUMBERSが定義されている
    もし PHASE_NUMBERSを確認する
    ならば 'planning'が'00'にマッピングされている
    かつ 'requirements'が'01'にマッピングされている
    かつ 'design'が'02'にマッピングされている
    かつ 'test_scenario'が'03'にマッピングされている
    かつ 'implementation'が'04'にマッピングされている
    かつ 'test_implementation'が'05'にマッピングされている
    かつ 'testing'が'06'にマッピングされている
    かつ 'documentation'が'07'にマッピングされている
    かつ 'report'が'08'にマッピングされている

  シナリオ: Phase 5のクラスがmain.pyに統合されている
    前提 main.pyが存在する
    もし main.pyを確認する
    ならば TestImplementationPhaseがimportされている
    かつ phase_classes辞書に'test_implementation'が含まれている
    かつ executeコマンドのphase選択肢に'test_implementation'が含まれている
