#!/usr/bin/env python3
"""
合并主服务器和 ECS 的回南天数据

架构说明:
- ECS 服务器: 阿里云 2C2G (47.116.201.2) - 每小时采集数据
- 主服务器: OpenClaw Workspace - 负责合并和可视化
- 数据流向: ECS → GitHub (ecs-data/) → 主服务器 (merge) → 可视化

ECS 托管说明:
- 由主服务器代管，通过 SSH 密钥连接
- ECS 独立运行，故障不影响主服务器
- Token 消耗: ECS 每月 720 次，主服务器 ~9810 次，总计 ~35% 配额

创建时间: 2026-02-18
维护者: OpenClaw
"""

import json
import urllib.request
from datetime import datetime

# 数据文件路径
LOCAL_DATA_FILE = "/root/.openclaw/workspace/memory/huinan-history.json"
ECS_DATA_URL = "https://raw.githubusercontent.com/Artistkisa/kisara-viz-center/main/ecs-data/huinan-data.json"

def load_local_data():
    """加载主服务器本地数据"""
    try:
        with open(LOCAL_DATA_FILE, 'r') as f:
            return json.load(f)
    except:
        return {"records": [], "lastAlert": None, "alertActive": False, "alertLevel": None}

def fetch_ecs_data():
    """从 GitHub 获取 ECS 数据"""
    try:
        req = urllib.request.Request(ECS_DATA_URL)
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read())
    except Exception as e:
        print(f"获取 ECS 数据失败: {e}")
        return None

def merge_data(local_data, ecs_data):
    """合并两组数据"""
    if not ecs_data:
        return local_data
    
    local_records = local_data.get("records", [])
    
    # 构建 ECS 记录
    ecs_record = {
        "humidity": ecs_data.get("humidity", 0),
        "dew": ecs_data.get("dew", 0),
        "temp": ecs_data.get("temp", 0),
        "time": ecs_data.get("updatedAt", datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
        "isNanhui": ecs_data.get("isNanhui", False),
        "level": ecs_data.get("level"),
        "source": "ecs"
    }
    
    # 检查是否已存在
    exists = any(r.get("time") == ecs_record["time"] for r in local_records)
    
    if not exists:
        local_records.append(ecs_record)
        print(f"✅ 添加 ECS 数据: {ecs_record['time']}")
    else:
        print("⏭️ ECS 数据已存在，跳过")
    
    # 按时间排序
    local_records.sort(key=lambda x: x.get("time", ""))
    
    # 只保留最近 72 小时
    try:
        cutoff = datetime.now().timestamp() - 72 * 3600
        local_records = [
            r for r in local_records 
            if datetime.fromisoformat(r.get("time", "2024-01-01").replace('Z', '+00:00').replace('+00:00', '')).timestamp() > cutoff
        ]
    except:
        pass
    
    local_data["records"] = local_records
    
    # 更新状态（优先使用 ECS 的最新状态）
    if ecs_data.get("isNanhui"):
        local_data["alertActive"] = True
        local_data["alertLevel"] = ecs_data.get("level")
    
    return local_data

def save_data(data):
    """保存合并后的数据"""
    with open(LOCAL_DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"💾 数据已保存: {LOCAL_DATA_FILE}")

def main():
    print("=" * 60)
    print("🔄 合并回南天数据")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)
    print("📋 数据来源:")
    print("   - 主服务器: /root/.openclaw/workspace/memory/huinan-history.json")
    print("   - ECS 服务器: 47.116.201.2 (每小时采集)")
    print("   - ECS 数据 URL: https://raw.githubusercontent.com/Artistkisa/kisara-viz-center/main/ecs-data/huinan-data.json")
    print("-" * 60)
    
    local_data = load_local_data()
    print(f"📊 本地记录: {len(local_data.get('records', []))} 条")
    
    ecs_data = fetch_ecs_data()
    if ecs_data:
        print(f"✅ ECS 数据获取成功: 湿度{ecs_data.get('humidity')}%, 温度{ecs_data.get('temp')}°C")
    else:
        print("⚠️ 警告: 无法获取 ECS 数据！可视化将只显示主服务器数据。")
        print("   请检查:")
        print("   1. ECS 服务器是否运行 (47.116.201.2)")
        print("   2. GitHub 上是否有 ecs-data/huinan-data.json")
    
    merged_data = merge_data(local_data, ecs_data)
    print(f"📈 合并后: {len(merged_data.get('records', []))} 条")
    
    save_data(merged_data)
    print("✅ 完成!")
    print("=" * 60)

if __name__ == "__main__":
    main()
