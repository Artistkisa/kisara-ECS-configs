# ECS 托管服务器记录

## 服务器信息

| 项目 | 详情 |
|------|------|
| IP 地址 | 47.116.201.2 |
| 配置 | 2C2G (阿里云 ECS) |
| 系统 | Ubuntu 22.04 LTS |
| 用途 | 数据采集节点，分担主服务器压力 |
| 托管方式 | 主服务器通过 SSH 密钥代管 |

## 连接方式

```bash
# 私钥位置
~/.ssh/aliyun_ecs.pem

# SSH 连接
ssh -i ~/.ssh/aliyun_ecs.pem root@47.116.201.2
```

## 部署的服务

### 1. 回南天监测
- **脚本**: `/opt/monitor/scripts/guangzhou-huinan.js`
- **频率**: 每小时
- **数据推送**: GitHub (ecs-data/huinan-data.json)
- **Token 消耗**: 每月 720 次

### 2. 数据同步
- **脚本**: `/opt/monitor/scripts/push-data-to-github.sh`
- **频率**: 每小时（采集后立即推送）

## 数据流向

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│  ECS 采集    │ ───→ │   GitHub    │ ←─── │  主服务器    │
│ (每小时)     │ 推送  │ 数据文件     │ 拉取  │ (合并展示)   │
└─────────────┘      └─────────────┘      └─────────────┘
     47.116.201.2        ecs-data/         OpenClaw
                                          Workspace
```

## 维护记录

| 日期 | 操作 | 说明 |
|------|------|------|
| 2026-02-18 | 初始化部署 | 安装 Node.js, Python, PM2, 配置定时任务 |
| 2026-02-18 | 部署回南天监测 | 每小时采集，推送到 GitHub |

## 故障处理

### ECS 无法连接
1. 检查安全组：确保 22 端口开放
2. 检查私钥：`~/.ssh/aliyun_ecs.pem` 是否存在
3. 阿里云控制台：检查实例状态

### 数据未同步
1. 检查 ECS 日志：`/opt/monitor/logs/huinan.log`
2. 检查推送日志：`/opt/monitor/logs/push.log`
3. 手动测试：`ssh -i ~/.ssh/aliyun_ecs.pem root@47.116.201.2 "cd /opt/monitor && node scripts/guangzhou-huinan.js"`

## Token 配额监控

| 来源 | 每月调用 | 占比 |
|------|---------|------|
| ECS | 720 次 | 7% |
| 主服务器 | ~9,810 次 | 93% |
| **总计** | **~10,530 次** | **35%** (配额 30,000) |

## 扩展计划

- [ ] 部署更多监控脚本到 ECS
- [ ] 配置数据备份到 ECS
- [ ] 设置 ECS 监控告警

---
*最后更新: 2026-02-18*
