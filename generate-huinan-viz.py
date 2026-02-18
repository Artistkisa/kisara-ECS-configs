#!/usr/bin/env python3
"""
生成回南天监测可视化页面 - 炫酷版

数据架构:
- 主服务器: /root/.openclaw/workspace/memory/huinan-history.json (合并后数据)
- ECS 服务器: 阿里云 2C2G (47.116.201.2) - 每小时采集原始数据
- 合并流程: 生成可视化前，先调用 merge-huinan-data.py 合并 ECS 数据

ECS 托管说明:
- ECS 由主服务器通过 SSH 代管
- 私钥位置: ~/.ssh/aliyun_ecs.pem
- ECS 定时任务: 每小时采集 + 推送 GitHub
- 主服务器定时任务: 每天5次生成可视化 (08:35/12:35/16:35/20:35/00:35)

创建时间: 2026-02-18
维护者: OpenClaw
"""

import json
import subprocess
import os
from datetime import datetime
from pathlib import Path

def load_data():
    """加载回南天历史数据"""
    data_file = "/root/.openclaw/workspace/memory/huinan-history.json"
    try:
        with open(data_file, 'r') as f:
            return json.load(f)
    except:
        return {"records": [], "alertActive": False}

def generate_html(data):
    """生成可视化 HTML - 炫酷版"""
    records = data.get("records", [])
    alert_active = data.get("alertActive", False)
    
    # 计算年度统计
    current_year = datetime.now().year
    year_records = [r for r in records if r.get("time", "").startswith(str(current_year))]
    
    alert_count = 0
    prev_alert = False
    for r in year_records:
        if r.get("isNanhui") and not prev_alert:
            alert_count += 1
        prev_alert = r.get("isNanhui", False)
    
    mild_days = sum(1 for r in year_records if r.get("level") == "mild")
    moderate_days = sum(1 for r in year_records if r.get("level") == "moderate")
    severe_days = sum(1 for r in year_records if r.get("level") == "severe")
    total_days = mild_days + moderate_days + severe_days
    
    # 获取最近24小时数据
    recent_records = []
    for r in records[-30:]:  # 获取更多数据点
        try:
            dt = datetime.fromisoformat(r.get("time", "").replace('Z', '+00:00').replace('+00:00', ''))
            recent_records.append(r)
        except:
            pass
    
    # 当前状态
    current = recent_records[-1] if recent_records else {"humidity": 0, "dew": 0, "temp": 0, "isNanhui": False, "level": None}
    
    # 判断状态样式
    status_class = "normal"
    status_text = "正常"
    status_icon = "☀️"
    pulse_class = ""
    
    if current.get("isNanhui"):
        level = current.get("level")
        pulse_class = "pulse"
        if level == "severe":
            status_class = "severe"
            status_text = "重度回南天"
            status_icon = "🔴"
        elif level == "moderate":
            status_class = "moderate"
            status_text = "中度回南天"
            status_icon = "🟠"
        else:
            status_class = "mild"
            status_text = "轻度回南天"
            status_icon = "🟡"
    
    # 准备图表数据
    labels = []
    humidity_data = []
    dew_data = []
    temp_data = []
    nanhui_points = []  # 回南天标记点
    
    for i, r in enumerate(recent_records):
        try:
            dt = datetime.fromisoformat(r.get("time", "").replace('Z', '+00:00').replace('+00:00', ''))
            labels.append(f"{dt.hour:02d}:{dt.minute:02d}")
            humidity_data.append(r.get("humidity", 0))
            dew_data.append(r.get("dew", 0))
            temp_data.append(r.get("temp", 0))
            
            # 标记回南天点
            if r.get("isNanhui"):
                nanhui_points.append({
                    x: i,
                    humidity: r.get("humidity", 0),
                    dew: r.get("dew", 0),
                    temp: r.get("temp", 0)
                })
        except:
            pass
    
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>回南天监测 - 广州</title>
    <link rel="icon" type="image/svg+xml" href="../favicon.svg">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@2.1.0/dist/chartjs-plugin-annotation.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #fff;
            padding: 20px;
        }}
        .container {{ max-width: 1000px; margin: 0 auto; }}
        h1 {{
            text-align: center;
            margin-bottom: 30px;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .back-link {{
            display: inline-block;
            margin-bottom: 20px;
            color: #8892b0;
            text-decoration: none;
        }}
        .back-link:hover {{ color: #fff; }}
        
        /* 状态卡片 */
        .status-card {{
            background: rgba(255,255,255,0.05);
            border-radius: 20px;
            padding: 40px;
            text-align: center;
            border: 3px solid;
            margin-bottom: 30px;
            position: relative;
            overflow: hidden;
        }}
        .status-card.normal {{ border-color: #00c853; background: rgba(0,200,83,0.1); }}
        .status-card.mild {{ border-color: #feca57; background: rgba(254,202,87,0.1); }}
        .status-card.moderate {{ border-color: #ff9800; background: rgba(255,152,0,0.1); }}
        .status-card.severe {{ border-color: #ff1744; background: rgba(255,23,68,0.1); }}
        
        .status-card.pulse::before {{
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            width: 100%;
            height: 100%;
            border-radius: 50%;
            border: 3px solid;
            animation: pulse-ring 2s ease-out infinite;
            transform: translate(-50%, -50%);
        }}
        
        @keyframes pulse-ring {{
            0% {{ transform: translate(-50%, -50%) scale(0.8); opacity: 1; }}
            100% {{ transform: translate(-50%, -50%) scale(1.5); opacity: 0; }}
        }}
        
        .status-icon {{ font-size: 5rem; margin-bottom: 15px; animation: bounce 2s infinite; }}
        @keyframes bounce {{
            0%, 100% {{ transform: translateY(0); }}
            50% {{ transform: translateY(-10px); }}
        }}
        
        .status-text {{ font-size: 1.8rem; font-weight: bold; margin-bottom: 10px; }}
        .status-card.normal .status-text {{ color: #00c853; }}
        .status-card.mild .status-text {{ color: #feca57; }}
        .status-card.moderate .status-text {{ color: #ff9800; }}
        .status-card.severe .status-text {{ color: #ff1744; }}
        
        /* 实时数据卡片 */
        .metrics {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            margin-bottom: 30px;
        }}
        .metric {{
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            padding: 25px;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.1);
            transition: transform 0.3s;
        }}
        .metric:hover {{ transform: translateY(-5px); }}
        .metric-value {{
            font-size: 2.5rem;
            font-weight: bold;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .metric-label {{ font-size: 0.9rem; color: #8892b0; margin-top: 8px; }}
        
        /* 年度统计 */
        .year-stats {{
            background: rgba(255,255,255,0.05);
            border-radius: 20px;
            padding: 30px;
            border: 1px solid rgba(255,255,255,0.1);
            margin-bottom: 30px;
        }}
        .year-stats h2 {{
            margin-bottom: 25px;
            font-size: 1.3rem;
            text-align: center;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
        }}
        .stat-item {{
            text-align: center;
            padding: 20px;
            background: rgba(255,255,255,0.03);
            border-radius: 16px;
            border: 1px solid rgba(255,255,255,0.05);
        }}
        .stat-number {{ font-size: 2.2rem; font-weight: bold; }}
        .stat-desc {{ font-size: 0.85rem; color: #8892b0; margin-top: 8px; }}
        .stat-item.total .stat-number {{ color: #667eea; }}
        .stat-item.mild .stat-number {{ color: #feca57; }}
        .stat-item.moderate .stat-number {{ color: #ff9800; }}
        .stat-item.severe .stat-number {{ color: #ff1744; }}
        
        /* 图表区域 */
        .chart-section {{
            background: rgba(255,255,255,0.05);
            border-radius: 20px;
            padding: 30px;
            border: 1px solid rgba(255,255,255,0.1);
            margin-bottom: 30px;
        }}
        .chart-section h2 {{
            margin-bottom: 25px;
            font-size: 1.3rem;
        }}
        .chart-container {{
            height: 400px;
            position: relative;
        }}
        
        /* 图例 */
        .legend {{
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-top: 20px;
            flex-wrap: wrap;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.9rem;
            color: #8892b0;
        }}
        .legend-color {{
            width: 20px;
            height: 4px;
            border-radius: 2px;
        }}
        
        /* 说明 */
        .info-section {{
            background: rgba(255,255,255,0.05);
            border-radius: 20px;
            padding: 30px;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .info-section h2 {{
            margin-bottom: 20px;
            font-size: 1.2rem;
        }}
        .info-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
        }}
        .info-item {{
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 12px;
            background: rgba(255,255,255,0.03);
            border-radius: 10px;
        }}
        .info-badge {{
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: bold;
        }}
        .info-badge.mild {{ background: rgba(254,202,87,0.2); color: #feca57; }}
        .info-badge.moderate {{ background: rgba(255,152,0,0.2); color: #ff9800; }}
        .info-badge.severe {{ background: rgba(255,23,68,0.2); color: #ff1744; }}
        
        .update-time {{
            text-align: center;
            color: #8892b0;
            font-size: 0.9rem;
            margin-top: 30px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <a href="../" class="back-link">← 返回可视化中心</a>
        <h1>🌫️ 回南天监测</h1>
        
        <div class="status-card {status_class} {pulse_class}">
            <div class="status-icon">{status_icon}</div>
            <div class="status-text">{status_text}</div>
            <div style="color: #8892b0; font-size: 1.1rem;">
                {current.get('isNanhui', False) and '⚠️ 注意防潮除湿' or '✅ 空气湿度正常'}
            </div>
        </div>
        
        <div class="metrics">
            <div class="metric">
                <div class="metric-value">{current.get('humidity', 0)}%</div>
                <div class="metric-label">💧 相对湿度</div>
            </div>
            <div class="metric">
                <div class="metric-value">{current.get('dew', 0)}°C</div>
                <div class="metric-label">🌡️ 露点温度</div>
            </div>
            <div class="metric">
                <div class="metric-value">{current.get('temp', 0)}°C</div>
                <div class="metric-label">🌡️ 空气温度</div>
            </div>
        </div>
        
        <div class="year-stats">
            <h2>📊 {current_year}年统计</h2>
            <div class="stats-grid">
                <div class="stat-item total">
                    <div class="stat-number">{alert_count}</div>
                    <div class="stat-desc">回南天次数</div>
                </div>
                <div class="stat-item mild">
                    <div class="stat-number">{mild_days}</div>
                    <div class="stat-desc">轻度天数</div>
                </div>
                <div class="stat-item moderate">
                    <div class="stat-number">{moderate_days}</div>
                    <div class="stat-desc">中度天数</div>
                </div>
                <div class="stat-item severe">
                    <div class="stat-number">{severe_days}</div>
                    <div class="stat-desc">重度天数</div>
                </div>
            </div>
            <div style="text-align: center; margin-top: 20px; color: #8892b0; font-size: 1rem;">
                累计影响 <strong style="color: #fff;">{total_days}</strong> 天
            </div>
        </div>
        
        <div class="chart-section">
            <h2>📈 趋势分析</h2>
            <div class="chart-container">
                <canvas id="trendChart"></canvas>
            </div>
            <div class="legend">
                <div class="legend-item">
                    <div class="legend-color" style="background: #667eea;"></div>
                    <span>湿度</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #feca57;"></div>
                    <span>温度</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #00c853;"></div>
                    <span>露点</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #ff1744;"></div>
                    <span>85%基线</span>
                </div>
            </div>
        </div>
        
        <div class="info-section">
            <h2>ℹ️ 回南天判断标准</h2>
            <div class="info-grid">
                <div class="info-item">
                    <span class="info-badge mild">轻度</span>
                    <span>湿度 85-90%</span>
                </div>
                <div class="info-item">
                    <span class="info-badge moderate">中度</span>
                    <span>湿度 90-95%</span>
                </div>
                <div class="info-item">
                    <span class="info-badge severe">重度</span>
                    <span>湿度 > 95%</span>
                </div>
                <div class="info-item">
                    <span style="color: #8892b0;">露点 ≥ 温度-3°C</span>
                </div>
            </div>
        </div>
        
        <p class="update-time">最后更新: {datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S')} | 每天检测5次</p>
    </div>
    
    <script>
        const ctx = document.getElementById('trendChart').getContext('2d');
        
        // 数据
        const labels = {json.dumps(labels)};
        const humidityData = {json.dumps(humidity_data)};
        const dewData = {json.dumps(dew_data)};
        const tempData = {json.dumps(temp_data)};
        
        // 计算露点-温度差值，用于判断回南天区域
        const diffData = dewData.map((dew, i) => dew - (tempData[i] || 0) + 3);
        
        // 创建渐变背景
        const nanhuiGradient = ctx.createLinearGradient(0, 0, 0, 400);
        nanhuiGradient.addColorStop(0, 'rgba(255, 23, 68, 0.3)');
        nanhuiGradient.addColorStop(1, 'rgba(255, 23, 68, 0.05)');
        
        const chart = new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: labels,
                datasets: [
                    {{
                        label: '湿度 (%)',
                        data: humidityData,
                        borderColor: '#667eea',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        borderWidth: 3,
                        tension: 0.4,
                        fill: true,
                        pointRadius: 4,
                        pointHoverRadius: 8,
                        pointBackgroundColor: '#667eea',
                        pointBorderColor: '#fff',
                        pointBorderWidth: 2
                    }},
                    {{
                        label: '温度 (°C)',
                        data: tempData,
                        borderColor: '#feca57',
                        backgroundColor: 'rgba(254, 202, 87, 0.1)',
                        borderWidth: 3,
                        tension: 0.4,
                        fill: false,
                        pointRadius: 4,
                        pointHoverRadius: 8,
                        pointBackgroundColor: '#feca57',
                        pointBorderColor: '#fff',
                        pointBorderWidth: 2
                    }},
                    {{
                        label: '露点 (°C)',
                        data: dewData,
                        borderColor: '#00c853',
                        backgroundColor: 'rgba(0, 200, 83, 0.1)',
                        borderWidth: 3,
                        tension: 0.4,
                        fill: false,
                        pointRadius: 4,
                        pointHoverRadius: 8,
                        pointBackgroundColor: '#00c853',
                        pointBorderColor: '#fff',
                        pointBorderWidth: 2
                    }},
                    {{
                        label: '回南天区域',
                        data: humidityData.map((h, i) => (h >= 85 && dewData[i] >= tempData[i] - 3) ? h : null),
                        borderColor: 'transparent',
                        backgroundColor: nanhuiGradient,
                        borderWidth: 0,
                        fill: true,
                        pointRadius: 8,
                        pointHoverRadius: 12,
                        pointBackgroundColor: '#ff1744',
                        pointBorderColor: '#fff',
                        pointBorderWidth: 3,
                        showLine: false
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                interaction: {{
                    mode: 'index',
                    intersect: false
                }},
                plugins: {{
                    legend: {{
                        display: false
                    }},
                    tooltip: {{
                        backgroundColor: 'rgba(26, 26, 46, 0.9)',
                        titleColor: '#fff',
                        bodyColor: '#8892b0',
                        borderColor: 'rgba(255,255,255,0.1)',
                        borderWidth: 1,
                        padding: 12,
                        callbacks: {{
                            afterBody: function(context) {{
                                const idx = context[0].dataIndex;
                                const h = humidityData[idx];
                                const d = dewData[idx];
                                const t = tempData[idx];
                                if (h >= 85 && d >= t - 3) {{
                                    return '⚠️ 回南天条件满足';
                                }}
                                return '';
                            }}
                        }}
                    }},
                    annotation: {{
                        annotations: {{
                            line1: {{
                                type: 'line',
                                yMin: 85,
                                yMax: 85,
                                borderColor: '#ff1744',
                                borderWidth: 2,
                                borderDash: [10, 5],
                                label: {{
                                    content: '85% 警戒线',
                                    enabled: true,
                                    position: 'end',
                                    backgroundColor: 'rgba(255, 23, 68, 0.8)',
                                    color: '#fff',
                                    font: {{ size: 12 }}
                                }}
                            }},
                            box1: {{
                                type: 'box',
                                yMin: 15,
                                yMax: 28,
                                backgroundColor: 'rgba(136, 146, 176, 0.1)',
                                borderColor: 'transparent',
                                label: {{
                                    content: '温度范围',
                                    enabled: true,
                                    position: 'start',
                                    color: '#8892b0',
                                    font: {{ size: 10 }}
                                }}
                            }}
                        }}
                    }}
                }},
                scales: {{
                    y: {{
                        min: 0,
                        max: 100,
                        grid: {{
                            color: 'rgba(255,255,255,0.05)',
                            drawBorder: false
                        }},
                        ticks: {{
                            color: '#8892b0',
                            font: {{ size: 11 }}
                        }},
                        title: {{
                            display: true,
                            text: '数值',
                            color: '#667eea'
                        }}
                    }},
                    x: {{
                        grid: {{
                            color: 'rgba(255,255,255,0.05)',
                            drawBorder: false
                        }},
                        ticks: {{
                            color: '#8892b0',
                            font: {{ size: 10 }},
                            maxRotation: 45
                        }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>'''
    
    return html

def push_to_github(source_file, subdir=''):
    """使用新的推送脚本"""
    result = subprocess.run(
        ["python3", "/root/.openclaw/workspace/scripts/push-to-github.py", source_file, subdir],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    return result.returncode == 0

def main():
    # 第一步：合并 ECS 数据
    print("🔄 合并 ECS 数据...")
    merge_result = subprocess.run(
        ["python3", "/root/.openclaw/workspace/scripts/merge-huinan-data.py"],
        capture_output=True,
        text=True
    )
    print(merge_result.stdout)
    if merge_result.stderr:
        print(merge_result.stderr)
    
    # 第二步：加载合并后的数据
    data = load_data()
    
    # 第三步：生成 HTML
    output_file = "/tmp/huinan-visualization.html"
    print("🎨 生成回南天可视化...")
    html = generate_html(data)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    # 第四步：推送到 GitHub
    push_to_github(output_file, "huinan")
    
    # 同时推送数据文件
    data_file = "/root/.openclaw/workspace/data/huinan-data.json"
    if os.path.exists(data_file):
        print("📤 推送数据文件...")
        push_to_github(data_file, "huinan")

if __name__ == "__main__":
    main()
