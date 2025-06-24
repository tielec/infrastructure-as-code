/**
 * Rust Code Analysis Report - Interactive Charts
 * Chart.jsを使用したインタラクティブなチャート表示
 */

// グローバル設定
Chart.defaults.font.family = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
Chart.defaults.color = '#333';

/**
 * 複雑度分布のヒストグラムを作成
 */
function createComplexityDistribution(canvasId, data, threshold, type = 'Cyclomatic') {
    const ctx = document.getElementById(canvasId);
    if (!ctx || !data || data.length === 0) return;

    // データをビンに分割
    const bins = createHistogramBins(data, 30);
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: bins.labels,
            datasets: [{
                label: `${type} Complexity`,
                data: bins.counts,
                backgroundColor: type === 'Cyclomatic' ? 
                    'rgba(54, 162, 235, 0.6)' : 'rgba(255, 159, 64, 0.6)',
                borderColor: type === 'Cyclomatic' ? 
                    'rgba(54, 162, 235, 1)' : 'rgba(255, 159, 64, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: `${type} Complexity Distribution`,
                    font: { size: 16 }
                },
                annotation: {
                    annotations: {
                        threshold: {
                            type: 'line',
                            xMin: threshold,
                            xMax: threshold,
                            borderColor: 'rgb(255, 99, 132)',
                            borderWidth: 2,
                            borderDash: [5, 5],
                            label: {
                                display: true,
                                content: `Threshold: ${threshold}`,
                                position: 'start'
                            }
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Complexity Value'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Number of Functions'
                    },
                    beginAtZero: true
                }
            }
        }
    });
}

/**
 * 言語別関数数のグラフを作成
 */
function createLanguageBreakdown(canvasId, languageData) {
    const ctx = document.getElementById(canvasId);
    if (!ctx || !languageData) return;

    const languages = Object.keys(languageData);
    const totalCounts = languages.map(lang => languageData[lang].count);
    const complexCounts = languages.map(lang => languageData[lang].complex);

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: languages.map(lang => lang.charAt(0).toUpperCase() + lang.slice(1)),
            datasets: [
                {
                    label: 'Total Functions',
                    data: totalCounts,
                    backgroundColor: 'rgba(75, 192, 192, 0.6)',
                    borderColor: 'rgba(75, 192, 192, 1)',
                    borderWidth: 1
                },
                {
                    label: 'Complex Functions',
                    data: complexCounts,
                    backgroundColor: 'rgba(255, 99, 132, 0.6)',
                    borderColor: 'rgba(255, 99, 132, 1)',
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Functions by Programming Language',
                    font: { size: 16 }
                },
                tooltip: {
                    callbacks: {
                        afterLabel: function(context) {
                            if (context.datasetIndex === 1 && totalCounts[context.dataIndex] > 0) {
                                const percentage = (complexCounts[context.dataIndex] / totalCounts[context.dataIndex] * 100).toFixed(1);
                                return `${percentage}% of total`;
                            }
                            return '';
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Programming Language'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Number of Functions'
                    },
                    beginAtZero: true
                }
            }
        }
    });
}

/**
 * 複雑度の相関図（Cyclomatic vs Cognitive）
 */
function createComplexityCorrelation(canvasId, data) {
    const ctx = document.getElementById(canvasId);
    if (!ctx || !data || data.length === 0) return;

    const scatterData = data.map(item => ({
        x: item.cyclomatic,
        y: item.cognitive,
        label: item.function
    }));

    new Chart(ctx, {
        type: 'scatter',
        data: {
            datasets: [{
                label: 'Functions',
                data: scatterData,
                backgroundColor: function(context) {
                    const value = context.raw;
                    if (value.x > 15 || value.y > 20) {
                        return 'rgba(255, 99, 132, 0.6)';
                    } else if (value.x > 10 || value.y > 15) {
                        return 'rgba(255, 206, 86, 0.6)';
                    }
                    return 'rgba(75, 192, 192, 0.6)';
                },
                pointRadius: 4,
                pointHoverRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Cyclomatic vs Cognitive Complexity',
                    font: { size: 16 }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return [
                                context.raw.label,
                                `Cyclomatic: ${context.raw.x}`,
                                `Cognitive: ${context.raw.y}`
                            ];
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Cyclomatic Complexity'
                    },
                    beginAtZero: true
                },
                y: {
                    title: {
                        display: true,
                        text: 'Cognitive Complexity'
                    },
                    beginAtZero: true
                }
            }
        }
    });
}

/**
 * メンテナビリティインデックスのゲージチャート
 */
function createMaintainabilityGauge(canvasId, avgMI) {
    const ctx = document.getElementById(canvasId);
    if (!ctx || avgMI === undefined) return;

    // ゲージの色を決定
    let color;
    if (avgMI >= 65) {
        color = 'rgba(75, 192, 192, 0.8)';
    } else if (avgMI >= 20) {
        color = 'rgba(255, 206, 86, 0.8)';
    } else {
        color = 'rgba(255, 99, 132, 0.8)';
    }

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            datasets: [{
                data: [avgMI, 100 - avgMI],
                backgroundColor: [color, 'rgba(200, 200, 200, 0.3)'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            rotation: -90,
            circumference: 180,
            plugins: {
                title: {
                    display: true,
                    text: 'Average Maintainability Index',
                    font: { size: 16 }
                },
                tooltip: {
                    enabled: false
                }
            }
        },
        plugins: [{
            id: 'text',
            beforeDraw: function(chart) {
                const width = chart.width;
                const height = chart.height;
                const ctx = chart.ctx;
                
                ctx.restore();
                const fontSize = (height / 100).toFixed(2);
                ctx.font = fontSize + "em sans-serif";
                ctx.textBaseline = "middle";
                
                const text = avgMI.toFixed(1);
                const textX = Math.round((width - ctx.measureText(text).width) / 2);
                const textY = height / 2 + height / 4;
                
                ctx.fillText(text, textX, textY);
                ctx.save();
            }
        }]
    });
}

/**
 * ヒストグラムのビンを作成
 */
function createHistogramBins(data, binCount) {
    const min = Math.min(...data);
    const max = Math.max(...data);
    const binSize = (max - min) / binCount;
    
    const bins = {
        labels: [],
        counts: new Array(binCount).fill(0)
    };
    
    // ビンのラベルを作成
    for (let i = 0; i < binCount; i++) {
        const binStart = min + (i * binSize);
        const binEnd = binStart + binSize;
        bins.labels.push(`${binStart.toFixed(0)}-${binEnd.toFixed(0)}`);
    }
    
    // データをビンに分類
    data.forEach(value => {
        const binIndex = Math.min(
            Math.floor((value - min) / binSize),
            binCount - 1
        );
        bins.counts[binIndex]++;
    });
    
    return bins;
}

/**
 * ページ読み込み時の初期化
 */
document.addEventListener('DOMContentLoaded', function() {
    // データ属性から値を取得
    const reportData = window.reportData || {};
    
    // 複雑度分布チャート
    if (reportData.cyclomaticData) {
        createComplexityDistribution(
            'cyclomaticChart',
            reportData.cyclomaticData,
            reportData.cyclomaticThreshold,
            'Cyclomatic'
        );
    }
    
    if (reportData.cognitiveData) {
        createComplexityDistribution(
            'cognitiveChart',
            reportData.cognitiveData,
            reportData.cognitiveThreshold,
            'Cognitive'
        );
    }
    
    // 言語別チャート
    if (reportData.languageStats) {
        createLanguageBreakdown('languageChart', reportData.languageStats);
    }
    
    // 相関図
    if (reportData.complexityData) {
        createComplexityCorrelation('correlationChart', reportData.complexityData);
    }
    
    // メンテナビリティゲージ
    if (reportData.averageMI !== undefined) {
        createMaintainabilityGauge('miGauge', reportData.averageMI);
    }
    
    // テーブルのソート機能
    initTableSort();
});

/**
 * テーブルのソート機能を初期化
 */
function initTableSort() {
    const table = document.querySelector('.complexity-table');
    if (!table) return;
    
    const headers = table.querySelectorAll('th');
    headers.forEach((header, index) => {
        if (index >= 2) { // 数値カラムのみソート可能
            header.style.cursor = 'pointer';
            header.addEventListener('click', () => sortTable(index));
        }
    });
}

/**
 * テーブルをソート
 */
function sortTable(columnIndex) {
    const table = document.querySelector('.complexity-table');
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    // 現在のソート状態を確認
    const isAscending = table.dataset.sortColumn == columnIndex && 
                       table.dataset.sortOrder === 'asc';
    
    // ソート
    rows.sort((a, b) => {
        const aValue = parseFloat(a.cells[columnIndex].textContent);
        const bValue = parseFloat(b.cells[columnIndex].textContent);
        
        if (isAscending) {
            return aValue - bValue;
        } else {
            return bValue - aValue;
        }
    });
    
    // テーブルを更新
    tbody.innerHTML = '';
    rows.forEach(row => tbody.appendChild(row));
    
    // ソート状態を保存
    table.dataset.sortColumn = columnIndex;
    table.dataset.sortOrder = isAscending ? 'desc' : 'asc';
}
