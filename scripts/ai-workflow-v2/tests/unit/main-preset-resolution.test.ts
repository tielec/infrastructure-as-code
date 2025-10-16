/**
 * ユニットテスト: main.ts - プリセット名解決機能
 *
 * テスト対象:
 * - resolvePresetName関数（後方互換性対応）
 * - listPresets関数（プリセット一覧表示）
 *
 * 注意: resolvePresetNameはmain.ts内のプライベート関数のため、
 * 実際のテストではCLI経由での動作確認が必要です。
 * このテストでは、同等のロジックを再現してテストします。
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  PHASE_PRESETS,
  DEPRECATED_PRESETS,
  PRESET_DESCRIPTIONS,
} from '../../src/core/phase-dependencies.js';

/**
 * main.tsのresolvePresetName関数と同等のロジック
 * （テスト用に再現）
 */
function resolvePresetName(presetName: string): {
  resolvedName: string;
  warning?: string;
} {
  // 現行プリセット名の場合
  if (PHASE_PRESETS[presetName]) {
    return { resolvedName: presetName };
  }

  // 非推奨プリセット名の場合
  if (DEPRECATED_PRESETS[presetName]) {
    const newName = DEPRECATED_PRESETS[presetName];

    // full-workflowの特殊ケース
    if (presetName === 'full-workflow') {
      return {
        resolvedName: '',
        warning: `[WARNING] Preset "${presetName}" is deprecated. Please use "--phase all" instead.`,
      };
    }

    // 通常の非推奨プリセット
    return {
      resolvedName: newName,
      warning: `[WARNING] Preset "${presetName}" is deprecated. Please use "${newName}" instead. This alias will be removed in 6 months.`,
    };
  }

  // 存在しないプリセット名
  throw new Error(`[ERROR] Unknown preset: ${presetName}. Use 'list-presets' command to see available presets.`);
}

describe('resolvePresetName関数テスト', () => {
  it('1.2.1: 現行プリセット名の解決（正常系）', () => {
    // Given: 現行プリセット名
    const presetName = 'quick-fix';

    // When: プリセット名を解決
    const result = resolvePresetName(presetName);

    // Then: 警告なしで解決される
    assert.equal(result.resolvedName, 'quick-fix');
    assert.equal(result.warning, undefined);
  });

  it('1.2.2: 非推奨プリセット名の解決（警告付き）', () => {
    // Given: 非推奨プリセット名
    const presetName = 'requirements-only';

    // When: プリセット名を解決
    const result = resolvePresetName(presetName);

    // Then: 新プリセット名に解決され、警告が表示される
    assert.equal(result.resolvedName, 'review-requirements');
    assert.ok(result.warning);
    assert.ok(result.warning.includes('deprecated'));
    assert.ok(result.warning.includes('review-requirements'));
    assert.ok(result.warning.includes('6 months'));
  });

  it('1.2.2-2: 非推奨プリセット名（design-phase）の解決', () => {
    // Given: 非推奨プリセット名
    const presetName = 'design-phase';

    // When: プリセット名を解決
    const result = resolvePresetName(presetName);

    // Then: 新プリセット名に解決され、警告が表示される
    assert.equal(result.resolvedName, 'review-design');
    assert.ok(result.warning);
    assert.ok(result.warning.includes('deprecated'));
  });

  it('1.2.2-3: 非推奨プリセット名（implementation-phase）の解決', () => {
    // Given: 非推奨プリセット名
    const presetName = 'implementation-phase';

    // When: プリセット名を解決
    const result = resolvePresetName(presetName);

    // Then: 新プリセット名に解決され、警告が表示される
    assert.equal(result.resolvedName, 'implementation');
    assert.ok(result.warning);
    assert.ok(result.warning.includes('deprecated'));
  });

  it('1.2.3: full-workflowプリセットの特殊処理', () => {
    // Given: full-workflowプリセット名
    const presetName = 'full-workflow';

    // When: プリセット名を解決
    const result = resolvePresetName(presetName);

    // Then: 空文字列に解決され、--phase allへの移行メッセージが表示される
    assert.equal(result.resolvedName, '');
    assert.ok(result.warning);
    assert.ok(result.warning.includes('--phase all'));
    assert.ok(result.warning.includes('deprecated'));
  });

  it('1.2.4: 存在しないプリセット名のエラー', () => {
    // Given: 存在しないプリセット名
    const presetName = 'unknown-preset';

    // When/Then: エラーが投げられる
    assert.throws(() => {
      resolvePresetName(presetName);
    }, /Unknown preset/);
  });

  it('1.2.4-2: 空文字列プリセット名のエラー', () => {
    // Given: 空文字列
    const presetName = '';

    // When/Then: エラーが投げられる
    assert.throws(() => {
      resolvePresetName(presetName);
    }, /Unknown preset/);
  });
});

describe('プリセット一覧表示機能テスト', () => {
  it('1.6.1: listPresets関数のロジック検証', () => {
    // Given: PHASE_PRESETSとDEPRECATED_PRESETSが定義されている
    // When: プリセット一覧を生成
    const presetList: string[] = [];
    for (const [name, phases] of Object.entries(PHASE_PRESETS)) {
      const description = PRESET_DESCRIPTIONS[name] || '';
      const phaseList = phases.join(' → ');
      presetList.push(`${name}: ${description} (${phaseList})`);
    }

    const deprecatedList: string[] = [];
    for (const [oldName, newName] of Object.entries(DEPRECATED_PRESETS)) {
      deprecatedList.push(`${oldName} → ${newName}`);
    }

    // Then: プリセット一覧が正しく生成される
    assert.ok(presetList.length > 0, 'プリセット一覧が空です');
    assert.ok(deprecatedList.length > 0, '非推奨プリセット一覧が空です');

    // 各プリセットに説明が含まれていることを確認
    for (const item of presetList) {
      assert.ok(item.includes(':'), `プリセット項目にコロンが含まれていません: ${item}`);
      assert.ok(item.includes('→'), `プリセット項目に→が含まれていません: ${item}`);
    }

    // 非推奨プリセットに移行先が含まれていることを確認
    for (const item of deprecatedList) {
      assert.ok(item.includes('→'), `非推奨プリセット項目に→が含まれていません: ${item}`);
    }
  });

  it('全プリセットに説明が存在する', () => {
    // Given: PHASE_PRESETSが定義されている
    // When: 各プリセットの説明を確認
    // Then: 全てのプリセットに説明が存在する
    for (const presetName of Object.keys(PHASE_PRESETS)) {
      assert.ok(
        PRESET_DESCRIPTIONS[presetName],
        `プリセット "${presetName}" の説明がPRESET_DESCRIPTIONSに存在しません`
      );
    }
  });
});

describe('プリセット名の境界値テスト', () => {
  it('全ての現行プリセット名が解決できる', () => {
    // Given: PHASE_PRESETSの全キー
    // When: 各プリセット名を解決
    // Then: 全て警告なしで解決される
    for (const presetName of Object.keys(PHASE_PRESETS)) {
      const result = resolvePresetName(presetName);
      assert.equal(result.resolvedName, presetName);
      assert.equal(result.warning, undefined);
    }
  });

  it('全ての非推奨プリセット名が解決できる', () => {
    // Given: DEPRECATED_PRESETSの全キー
    // When: 各非推奨プリセット名を解決
    // Then: 全て新プリセット名に解決され、警告が表示される
    for (const oldName of Object.keys(DEPRECATED_PRESETS)) {
      const result = resolvePresetName(oldName);

      if (oldName === 'full-workflow') {
        // 特殊ケース
        assert.equal(result.resolvedName, '');
        assert.ok(result.warning);
        assert.ok(result.warning.includes('--phase all'));
      } else {
        // 通常ケース
        assert.ok(result.resolvedName);
        assert.ok(result.warning);
        assert.ok(result.warning.includes('deprecated'));
      }
    }
  });
});
