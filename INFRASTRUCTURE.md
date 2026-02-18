# 关键基础设施清单

## 必须知道的服务器

### 1. ECS 托管服务器（重要！）
- **IP**: 47.116.201.2
- **SSH 密钥**: `~/.ssh/aliyun_ecs.pem`
- **连接命令**: `ssh -i ~/.ssh/aliyun_ecs.pem root@47.116.201.2`
- **配置**: 阿里云 ECS 2C2G
- **系统**: Ubuntu 22.04 LTS
- **用途**: 数据采集节点，分担 API 压力
- **位置**: 阿里云上海
- **状态**: 每小时运行回南天监测，推送到 GitHub

**配置同步机制（重要！）**
```
主服务器修改配置
    ↓ 每10分钟检测变更
GitHub (kisara-ECS-configs 仓库)
    ↓ 每10分钟拉取
ECS 自动应用配置
```
- 主服务器脚本: `scripts/sync-configs-to-github.py`
- ECS 脚本: `/opt/monitor/scripts/sync-configs-from-github.sh`
- 同步文件: 回南天脚本、推送脚本、心跳脚本、文档等
- 变更检测: MD5 哈希值比对

**为什么重要：**
- 分担了 720 次/月的 API 调用
- 如果忘记它，会以为所有数据都来自主服务器
- 可视化数据可能不完整

**检查方式：**
```bash
ssh -i ~/.ssh/aliyun_ecs.pem root@47.116.201.2 "crontab -l"
```

### 2. 主服务器（当前）
- **位置**: OpenClaw Workspace
- **用途**: 数据汇总、可视化、通知
- **关键脚本**: 
  - `scripts/merge-huinan-data.py` - 必须合并 ECS 数据
  - `scripts/generate-huinan-viz.py` - 生成可视化

## 数据流向（必须理解）

```
ECS (47.116.201.2) 
    ↓ 每小时采集
GitHub (ecs-data/huinan-data.json)
    ↓ 生成可视化前拉取
主服务器 (merge)
    ↓ 合并后生成
可视化页面
```

## 每次生成可视化前必须做的

1. 运行 `scripts/merge-huinan-data.py` 合并 ECS 数据
2. 检查 ECS 数据是否成功拉取
3. 生成可视化

## 如果 ECS 挂了

- 可视化还能生成（用本地数据）
- 但数据会缺失 ECS 的部分
- 需要修复 ECS 或临时增加主服务器采集频率

---
**警告**: 忘记 ECS 会导致数据不完整！
