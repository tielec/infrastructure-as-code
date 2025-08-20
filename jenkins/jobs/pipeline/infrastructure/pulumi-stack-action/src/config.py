"""
Configuration management for Pulumi Report Generator
"""

import matplotlib
matplotlib.use('Agg')  # Jenkins環境でのGUI問題を回避
import matplotlib.pyplot as plt


class MatplotlibConfig:
    """Matplotlib設定の管理"""
    
    @staticmethod
    def setup():
        """Matplotlibの初期設定"""
        # 日本語フォントの問題を回避するため、フォントファミリーを設定しない
        plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
        plt.rcParams.update({
            'figure.dpi': 100,
            'savefig.dpi': 100,
            'savefig.bbox': 'tight',
            'font.size': 9,
            'axes.titlesize': 12,
            'axes.labelsize': 10,
            'xtick.labelsize': 8,
            'ytick.labelsize': 8,
            'legend.fontsize': 9,
            # 日本語表示を無効化（英語のみ表示）
            'axes.unicode_minus': False
        })
