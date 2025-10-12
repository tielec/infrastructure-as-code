"""content_parser.pyのテストコード

外部ファイル化されたプロンプトが正しく読み込まれ、
OpenAI APIが正常に動作することを検証します。

環境変数の要件:
- OPENAI_API_KEY: OpenAI API用のAPIキー（必須）

OpenAI API Key は https://platform.openai.com/api-keys で取得できます。
"""
import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.content_parser import ContentParser


def test_extract_design_decisions():
    """設計書から戦略判断を抽出するテスト"""
    print("\n" + "="*60)
    print("TEST 1: extract_design_decisions()")
    print("="*60)

    # テスト用の計画書コンテンツ
    planning_content = """
# Issue #332 実装計画書

## 実装戦略: CREATE

新規機能として`ContentParser`クラスを作成します。
正規表現ベースの脆弱な判定を、OpenAI APIによる自然言語理解に置き換えます。

## テスト戦略: UNIT_INTEGRATION

- ユニットテスト: `extract_design_decisions()`メソッドの単体テスト
- 統合テスト: 実際の計画書を使用したEnd-to-Endテスト

## テストコード戦略: CREATE_TEST

新規にテストコードを作成します。
    """

    try:
        # ContentParserインスタンス作成
        parser = ContentParser()
        print(f"[OK] ContentParser初期化成功")

        # 戦略判断を抽出
        print(f"\n[INFO] 戦略判断の抽出を開始...")
        decisions = parser.extract_design_decisions(planning_content)

        # 結果検証
        print(f"\n[RESULT] 抽出された戦略判断:")
        for key, value in decisions.items():
            print(f"  - {key}: {value}")

        # 期待値チェック
        expected = {
            'implementation_strategy': 'CREATE',
            'test_strategy': 'UNIT_INTEGRATION',
            'test_code_strategy': 'CREATE_TEST'
        }

        success = True
        for key, expected_value in expected.items():
            if key not in decisions:
                print(f"[FAIL] {key}が抽出されませんでした")
                success = False
            elif decisions[key] != expected_value:
                print(f"[FAIL] {key}の値が期待値と異なります: {decisions[key]} != {expected_value}")
                success = False

        if success:
            print(f"\n[OK] TEST 1 PASSED - 全ての戦略判断が正しく抽出されました")
            return True
        else:
            print(f"\n[FAIL] TEST 1 FAILED - 期待値と一致しませんでした")
            return False

    except Exception as e:
        print(f"[ERROR] TEST 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_parse_review_result():
    """レビュー結果の解析テスト"""
    print("\n" + "="*60)
    print("TEST 2: parse_review_result()")
    print("="*60)

    # テスト用のレビューメッセージ（Claude Agent SDKのレスポンス形式）
    test_messages = [
        "AssistantMessage(content=[TextBlock(text='## レビュー結果\\n\\n**判定: PASS**\\n\\n素晴らしい実装です。プロンプトが外部ファイルに適切に分離されており、保守性が向上しています。')], model='claude-sonnet-4-20250514', ...)"
    ]

    try:
        # ContentParserインスタンス作成
        parser = ContentParser()
        print(f"[OK] ContentParser初期化成功")

        # レビュー結果を解析
        print(f"\n[INFO] レビュー結果の解析を開始...")
        result = parser.parse_review_result(test_messages)

        # 結果検証
        print(f"\n[RESULT] 解析されたレビュー結果:")
        print(f"  - result: {result['result']}")
        print(f"  - feedback: {result['feedback'][:100]}..." if len(result['feedback']) > 100 else f"  - feedback: {result['feedback']}")

        # 期待値チェック
        if result['result'] == 'PASS':
            print(f"\n[OK] TEST 2 PASSED - レビュー結果が正しく解析されました")
            return True
        else:
            print(f"\n[FAIL] TEST 2 FAILED - 期待値: PASS, 実際: {result['result']}")
            return False

    except Exception as e:
        print(f"[ERROR] TEST 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_prompt_file_loading():
    """プロンプトファイルの読み込みテスト"""
    print("\n" + "="*60)
    print("TEST 3: Prompt File Loading")
    print("="*60)

    try:
        parser = ContentParser()

        # プロンプトファイルのパスを確認
        prompt_dir = parser.prompt_dir
        print(f"[INFO] プロンプトディレクトリ: {prompt_dir}")

        # extract_design_decisionsプロンプトファイルの存在確認
        extract_prompt_file = prompt_dir / 'extract_design_decisions.txt'
        if extract_prompt_file.exists():
            print(f"[OK] extract_design_decisions.txt が存在します")
            content = extract_prompt_file.read_text(encoding='utf-8')
            print(f"[INFO] ファイルサイズ: {len(content)} 文字")
            if '{document_content}' in content:
                print(f"[OK] プレースホルダー {{document_content}} が含まれています")
            else:
                print(f"[FAIL] プレースホルダー {{document_content}} が見つかりません")
                return False
        else:
            print(f"[FAIL] extract_design_decisions.txt が存在しません")
            return False

        # parse_review_resultプロンプトファイルの存在確認
        parse_prompt_file = prompt_dir / 'parse_review_result.txt'
        if parse_prompt_file.exists():
            print(f"[OK] parse_review_result.txt が存在します")
            content = parse_prompt_file.read_text(encoding='utf-8')
            print(f"[INFO] ファイルサイズ: {len(content)} 文字")
            if '{full_text}' in content:
                print(f"[OK] プレースホルダー {{full_text}} が含まれています")
            else:
                print(f"[FAIL] プレースホルダー {{full_text}} が見つかりません")
                return False
        else:
            print(f"[FAIL] parse_review_result.txt が存在しません")
            return False

        print(f"\n[OK] TEST 3 PASSED - プロンプトファイルが正しく配置されています")
        return True

    except Exception as e:
        print(f"[ERROR] TEST 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """全テストを実行"""
    print("\n" + "="*60)
    print("ContentParser テストスイート")
    print("="*60)

    # 環境変数の確認
    api_key = os.environ.get("OPENAI_API_KEY")

    print("\n[INFO] 環境変数の確認:")
    if api_key:
        print(f"  ✓ OPENAI_API_KEY: 設定済み (先頭10文字: {api_key[:10]}...)")
    else:
        print(f"  ✗ OPENAI_API_KEY: 未設定")

    if not api_key:
        print("\n[ERROR] 環境変数 OPENAI_API_KEY が設定されていません！")
        print("OpenAI API Key は https://platform.openai.com/api-keys で取得できます。")
        sys.exit(1)

    print(f"\n[INFO] OPENAI_API_KEY が使用されます")

    results = []

    # TEST 1: プロンプトファイルの読み込み確認（最初に実行）
    results.append(("Prompt File Loading", test_prompt_file_loading()))

    # TEST 2: 戦略判断の抽出
    results.append(("Extract Design Decisions", test_extract_design_decisions()))

    # TEST 3: レビュー結果の解析
    results.append(("Parse Review Result", test_parse_review_result()))

    # 結果サマリー
    print("\n" + "="*60)
    print("テスト結果サマリー")
    print("="*60)

    passed = 0
    failed = 0
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
        else:
            failed += 1

    print(f"\n合計: {passed} passed, {failed} failed")

    if failed == 0:
        print("\n[SUCCESS] 全てのテストが成功しました！")
        sys.exit(0)
    else:
        print(f"\n[FAILURE] {failed}件のテストが失敗しました")
        sys.exit(1)


if __name__ == '__main__':
    main()
