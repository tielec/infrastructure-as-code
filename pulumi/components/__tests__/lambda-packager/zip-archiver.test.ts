import { EventEmitter } from "events";
import * as archiver from "archiver";
import * as fs from "fs";
import { ZipArchiver } from "../../src/lambda-packager/zip-archiver";
import { calculateFileHash } from "../../src/lambda-packager/utils";

class MockWriteStream extends EventEmitter {}

type MockArchiver = EventEmitter & {
  pipe: jest.Mock;
  glob: jest.Mock;
  append: jest.Mock;
  finalize: jest.Mock;
  destroy: jest.Mock;
};

type PulumiLogMock = {
  info: jest.Mock;
  warn: jest.Mock;
  error: jest.Mock;
};

jest.mock("fs", () => {
  const { EventEmitter } = require("events");

  class LocalMockWriteStream extends EventEmitter {}

  return {
    createWriteStream: jest.fn(() => new LocalMockWriteStream()),
    statSync: jest.fn(() => ({ size: 1234 }))
  };
});

jest.mock("archiver", () => {
  const { EventEmitter } = require("events");

  class LocalMockArchiver extends EventEmitter {
    pipe = jest.fn().mockReturnThis();
    glob = jest.fn().mockReturnThis();
    append = jest.fn().mockReturnThis();
    finalize = jest.fn().mockReturnThis();
    destroy = jest.fn();
  }

  return {
    create: jest.fn(() => new LocalMockArchiver())
  };
});

jest.mock("@pulumi/pulumi", () => {
  const pulumiLogMocks: PulumiLogMock = {
    info: jest.fn(),
    warn: jest.fn(),
    error: jest.fn()
  };

  return {
    __esModule: true,
    log: pulumiLogMocks
  };
});

jest.mock("../../src/lambda-packager/utils", () => ({
  calculateFileHash: jest.fn().mockReturnValue("mockedhash123")
}));

const mockCreateWriteStream = fs.createWriteStream as jest.MockedFunction<typeof fs.createWriteStream>;
const mockStatSync = fs.statSync as jest.MockedFunction<typeof fs.statSync>;
const mockArchiverCreate = archiver.create as jest.MockedFunction<typeof archiver.create>;
const mockCalculateFileHash = calculateFileHash as jest.MockedFunction<typeof calculateFileHash>;
const mockPulumiLog = (jest.requireMock("@pulumi/pulumi") as { log: PulumiLogMock }).log;

const defaultArgs = {
  outputPath: "/tmp/test-output.zip",
  sourcePath: "/app/source",
  includePatterns: ["**"],
  excludePatterns: [".git/**"],
  extraFiles: {
    "config.json": '{"key":"value"}',
    "meta.txt": "metadata"
  }
};

describe("ZipArchiver#createArchive", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockStatSync.mockReturnValue({ size: 2048 } as any);
    mockCalculateFileHash.mockReturnValue("mockedhash123");
  });

  test("正常系: アーカイブ作成に成功し、結果が返却される", async () => {
    // 正常完了パスが維持されていることを確認
    const archiverInstance = new ZipArchiver();
    const promise = archiverInstance.createArchive(
      defaultArgs.outputPath,
      defaultArgs.sourcePath,
      defaultArgs.includePatterns,
      defaultArgs.excludePatterns,
      defaultArgs.extraFiles
    );

    const outputStream = latestWriteStream();
    const archive = latestArchiver();

    expect(archive.pipe).toHaveBeenCalledWith(outputStream);
    expect(archive.glob).toHaveBeenCalledWith(
      defaultArgs.includePatterns.join(","),
      expect.objectContaining({
        cwd: defaultArgs.sourcePath,
        ignore: expect.arrayContaining(defaultArgs.excludePatterns),
        dot: true
      })
    );
    expect(archive.append).toHaveBeenCalledTimes(Object.keys(defaultArgs.extraFiles).length);
    expect(archive.finalize).toHaveBeenCalled();

    outputStream.emit("close");

    const result = await promise;

    expect(result).toEqual({
      zipPath: defaultArgs.outputPath,
      zipHash: "mockedhash123",
      sizeBytes: 2048
    });
    expect(mockPulumiLog.info).toHaveBeenCalledWith(
      expect.stringContaining("Archive created")
    );
  });

  test("異常系: 出力ストリームのerrorイベントでPromiseがrejectされる", async () => {
    // 出力エラー時にハングせず即座にrejectされることを確認
    const archiverInstance = new ZipArchiver();
    const promise = archiverInstance.createArchive(
      defaultArgs.outputPath,
      defaultArgs.sourcePath,
      defaultArgs.includePatterns,
      defaultArgs.excludePatterns,
      defaultArgs.extraFiles
    );

    const outputStream = latestWriteStream();
    const archive = latestArchiver();
    const error = new Error("EACCES: permission denied");

    outputStream.emit("error", error);

    await expect(promise).rejects.toBe(error);
    expect(archive.destroy).toHaveBeenCalledTimes(1);
  });

  test("異常系: 出力ストリームエラー時にarchive.destroy()がrejectより先に呼ばれる", async () => {
    // リソース解放が先行して呼ばれる順序を検証
    const archiverInstance = new ZipArchiver();
    const promise = archiverInstance.createArchive(
      defaultArgs.outputPath,
      defaultArgs.sourcePath,
      defaultArgs.includePatterns,
      defaultArgs.excludePatterns,
      defaultArgs.extraFiles
    );

    const outputStream = latestWriteStream();
    const archive = latestArchiver();
    const sequence: string[] = [];
    (archive.destroy as jest.Mock).mockImplementation(() => sequence.push("destroy"));

    const rejection = promise.catch(() => sequence.push("reject"));
    outputStream.emit("error", new Error("ENOSPC: no space left on device"));
    await rejection;

    expect(sequence).toEqual(["destroy", "reject"]);
  });

  test("異常系: 出力ストリームエラー時に適切なログが出力される", async () => {
    // ログメッセージにエラー内容が含まれることを確認
    const archiverInstance = new ZipArchiver();
    const promise = archiverInstance.createArchive(
      defaultArgs.outputPath,
      defaultArgs.sourcePath,
      defaultArgs.includePatterns,
      defaultArgs.excludePatterns,
      defaultArgs.extraFiles
    );

    const outputStream = latestWriteStream();
    const error = new Error("EROFS: read-only file system");

    outputStream.emit("error", error);

    await expect(promise).rejects.toBe(error);
    expect(mockPulumiLog.error).toHaveBeenCalledWith(
      `Output stream error: ${error.message}`
    );
  });

  test("既存動作: archiveエラー発生時にPromiseがrejectされる", async () => {
    // 既存のarchiveエラーハンドリングが維持されていることを確認
    const archiverInstance = new ZipArchiver();
    const promise = archiverInstance.createArchive(
      defaultArgs.outputPath,
      defaultArgs.sourcePath,
      defaultArgs.includePatterns,
      defaultArgs.excludePatterns,
      defaultArgs.extraFiles
    );

    const archive = latestArchiver();
    const archiveError = new Error("Archive entry error");

    archive.emit("error", archiveError);

    await expect(promise).rejects.toBe(archiveError);
    expect(mockPulumiLog.error).toHaveBeenCalledWith(
      `Archive creation failed: ${archiveError.message}`
    );
  });

  test("エッジケース: 出力とarchiveの両方でエラーが発生しても最初のエラーでrejectされる", async () => {
    // 複数エラー時でも二重rejectしないことを確認
    const archiverInstance = new ZipArchiver();
    const promise = archiverInstance.createArchive(
      defaultArgs.outputPath,
      defaultArgs.sourcePath,
      defaultArgs.includePatterns,
      defaultArgs.excludePatterns,
      defaultArgs.extraFiles
    );

    const outputStream = latestWriteStream();
    const archive = latestArchiver();

    const outputError = new Error("EPIPE: broken pipe");
    const archiveError = new Error("Archive corruption detected");

    outputStream.emit("error", outputError);
    archive.emit("error", archiveError);

    await expect(promise).rejects.toBe(outputError);
    expect(mockPulumiLog.error).toHaveBeenCalledWith(
      `Output stream error: ${outputError.message}`
    );
    expect(mockPulumiLog.error).toHaveBeenCalledWith(
      `Archive creation failed: ${archiveError.message}`
    );
  });

  test("エッジケース: エラーメッセージが空でもログとrejectが行われる", async () => {
    // メッセージが空文字でも処理が継続することを確認
    const archiverInstance = new ZipArchiver();
    const promise = archiverInstance.createArchive(
      defaultArgs.outputPath,
      defaultArgs.sourcePath,
      defaultArgs.includePatterns,
      defaultArgs.excludePatterns,
      defaultArgs.extraFiles
    );

    const outputStream = latestWriteStream();
    const emptyMessageError = new Error("");

    outputStream.emit("error", emptyMessageError);

    await expect(promise).rejects.toBe(emptyMessageError);
    expect(mockPulumiLog.error).toHaveBeenCalledWith("Output stream error: ");
  });

  test("既存動作: warningイベントではrejectせずログ出力後に正常完了する", async () => {
    // warningがrejectを引き起こさないことを確認
    const archiverInstance = new ZipArchiver();
    const promise = archiverInstance.createArchive(
      defaultArgs.outputPath,
      defaultArgs.sourcePath,
      defaultArgs.includePatterns,
      defaultArgs.excludePatterns,
      defaultArgs.extraFiles
    );

    const outputStream = latestWriteStream();
    const archive = latestArchiver();
    const warning = new Error("stat failure on file");

    archive.emit("warning", warning);
    outputStream.emit("close");

    const result = await promise;

    expect(mockPulumiLog.warn).toHaveBeenCalledWith(
      `Archive warning: ${warning.message}`
    );
    expect(result.zipPath).toBe(defaultArgs.outputPath);
  });
});

function latestWriteStream(): MockWriteStream {
  const value = mockCreateWriteStream.mock.results.at(-1)?.value as MockWriteStream | undefined;
  if (!value) {
    throw new Error("WriteStream mock was not created");
  }
  return value;
}

function latestArchiver(): MockArchiver {
  const value = mockArchiverCreate.mock.results.at(-1)?.value as MockArchiver | undefined;
  if (!value) {
    throw new Error("Archiver mock was not created");
  }
  return value;
}
