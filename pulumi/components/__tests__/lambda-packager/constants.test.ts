import {
  DEFAULT_RUNTIME,
  DEFAULT_EXCLUDE_PATTERNS,
  DEFAULT_INCLUDE_PATTERNS,
  BUILD_OUTPUT_DIRS,
  LANGUAGE_CONFIG_FILES,
  ZIP_COMPRESSION_LEVEL
} from "../../src/lambda-packager/constants";

describe("lambda-packager/constants", () => {
  describe("DEFAULT_RUNTIME", () => {
    test("DEFAULT_RUNTIMEがnodejs22.xであること", () => {
      // ランタイム定数が最新LTSに更新されていることを確認
      expect(DEFAULT_RUNTIME).toBe("nodejs22.x");
    });

    test("DEFAULT_RUNTIMEが文字列型であること", () => {
      // Pulumiに渡すランタイム指定が文字列として保持されていることを確認
      expect(typeof DEFAULT_RUNTIME).toBe("string");
    });

    test("DEFAULT_RUNTIMEがAWS Lambdaの命名規則に準拠していること", () => {
      // nodejsXX.x の形式に従うことを正規表現で検証
      expect(DEFAULT_RUNTIME).toMatch(/^nodejs\d+\.x$/);
    });
  });

  describe("DEFAULT_EXCLUDE_PATTERNS", () => {
    test("DEFAULT_EXCLUDE_PATTERNSが配列であること", () => {
      // 除外パターンが配列として定義されていることを確認
      expect(Array.isArray(DEFAULT_EXCLUDE_PATTERNS)).toBe(true);
    });

    test("テストファイルが除外対象に含まれていること", () => {
      // テストコードがLambdaパッケージに含まれないことを確認
      expect(DEFAULT_EXCLUDE_PATTERNS).toContain("*.test.js");
      expect(DEFAULT_EXCLUDE_PATTERNS).toContain("*.test.ts");
    });

    test(".gitディレクトリが除外対象に含まれていること", () => {
      // バージョン管理情報をパッケージに含めないことを確認
      expect(DEFAULT_EXCLUDE_PATTERNS).toContain(".git/**");
    });
  });

  describe("DEFAULT_INCLUDE_PATTERNS", () => {
    test("すべてのファイルがデフォルトで含まれること", () => {
      // インクルードパターンの既定値が全対象であることを確認
      expect(DEFAULT_INCLUDE_PATTERNS).toEqual(["**"]);
    });
  });

  describe("BUILD_OUTPUT_DIRS", () => {
    test("TypeScriptのビルド出力がdistであること", () => {
      // TypeScriptのビルド成果物がdistに出力されることを確認
      expect(BUILD_OUTPUT_DIRS.typescript).toBe("dist");
    });

    test("JavaScriptのビルド出力がカレントディレクトリであること", () => {
      // JavaScriptはカレントディレクトリを想定
      expect(BUILD_OUTPUT_DIRS.javascript).toBe(".");
    });

    test("Pythonのビルド出力がカレントディレクトリであること", () => {
      // Pythonはカレントディレクトリを想定
      expect(BUILD_OUTPUT_DIRS.python).toBe(".");
    });
  });

  describe("LANGUAGE_CONFIG_FILES", () => {
    test("TypeScriptの設定ファイルがtsconfig.jsonであること", () => {
      // TypeScriptの設定ファイル名が固定であることを確認
      expect(LANGUAGE_CONFIG_FILES.typescript).toBe("tsconfig.json");
    });
  });

  describe("ZIP_COMPRESSION_LEVEL", () => {
    test("最大圧縮レベル（9）であること", () => {
      // ZIP圧縮レベルの既定値が最大値であることを確認
      expect(ZIP_COMPRESSION_LEVEL).toBe(9);
    });
  });
});
