#!/usr/bin/env node
/**
 * 广州回南天监测脚本
 * 每天早上8点检测，根据湿度、露点温度判断回南天
 */

const fs = require('fs');
const path = require('path');

const DATA_FILE = '/root/.openclaw/workspace/memory/huinan-history.json';
const QWEATHER_KEY = 'a51c6a4dedb2458fb500637c9747ecc7'; // 和风天气 API Key - 测试同步 2026-02-18 20:27
const API_HOST = 'mg5khw3dm5.re.qweatherapi.com';
const LOCATION = '101280101'; // 广州

// 加载历史数据
function loadData() {
    try {
        return JSON.parse(fs.readFileSync(DATA_FILE, 'utf8'));
    } catch {
        return {
            records: [],
            lastAlert: null,
            alertActive: false,
            alertLevel: null
        };
    }
}

// 保存数据
function saveData(data) {
    fs.writeFileSync(DATA_FILE, JSON.stringify(data, null, 2));
    
    // 同时生成可视化用的数据文件
    const vizData = {
        humidity: data.records[data.records.length - 1]?.humidity || 0,
        dew: data.records[data.records.length - 1]?.dew || 0,
        temp: data.records[data.records.length - 1]?.temp || 0,
        isNanhui: data.alertActive,
        level: data.alertLevel,
        updatedAt: new Date().toISOString()
    };
    fs.writeFileSync('/root/.openclaw/workspace/data/huinan-data.json', JSON.stringify(vizData, null, 2));
}

// 获取天气数据
async function getWeather() {
    try {
        const response = await fetch(
            `https://${API_HOST}/v7/weather/now?location=${LOCATION}&key=${QWEATHER_KEY}`
        );
        const data = await response.json();
        
        if (data.code !== '200') {
            throw new Error(`API错误: ${data.code}`);
        }
        
        return {
            humidity: parseInt(data.now.humidity),
            dew: parseInt(data.now.dew),
            temp: parseInt(data.now.temp),
            time: new Date().toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false }).replace(/\//g, '-').replace(', ', 'T')
        };
    } catch (e) {
        console.error('获取天气失败:', e.message);
        return null;
    }
}

// 判断回南天条件
function checkNanhui(weather) {
    const { humidity, dew, temp } = weather;
    
    // 条件1: 湿度 >= 85%
    const condition1 = humidity >= 85;
    
    // 条件2: 露点 >= 空气温度 - 3°C
    const condition2 = dew >= (temp - 3);
    
    // 条件3: 温度 15-28°C
    const condition3 = temp >= 15 && temp <= 28;
    
    return condition1 && condition2 && condition3;
}

// 判断预警等级
function getAlertLevel(humidity) {
    if (humidity > 95) return 'severe';      // 重度
    if (humidity >= 90) return 'moderate';   // 中度
    return 'mild';                            // 轻度
}

// 检查是否需要发送警告
function shouldSendAlert(data) {
    if (!data.lastAlert) return true;
    
    const lastAlert = new Date(data.lastAlert);
    const now = new Date();
    const hoursSinceLastAlert = (now - lastAlert) / (1000 * 60 * 60);
    
    // 24小时内不重复发送
    return hoursSinceLastAlert >= 24;
}

// 检查结束条件
function checkEndCondition(records) {
    // 需要最近6小时的记录
    if (records.length < 6) return false;
    
    const recent = records.slice(-6);
    return recent.every(r => r.humidity < 80);
}

// 生成警告消息
function generateAlertMessage(weather, level) {
    const levelText = {
        'mild': '🟡 轻度',
        'moderate': '🟠 中度', 
        'severe': '🔴 重度'
    };
    
    const advice = {
        'mild': '注意防潮，建议关闭门窗',
        'moderate': '使用除湿设备，地面湿滑请小心',
        'severe': '严重回南天，尽量减少外出，注意电器防潮'
    };
    
    return {
        subject: `🌫️ 回南天警报（${levelText[level]}）- 湿度${weather.humidity}%`,
        message: `${levelText[level]} 回南天警报

📊 当前气象:
• 湿度: ${weather.humidity}%
• 露点温度: ${weather.dew}°C
• 空气温度: ${weather.temp}°C

⚠️ 防护建议:
${advice[level]}
• 关闭门窗，防止湿气进入
• 地面湿滑，小心行走
• 衣物注意防潮

📍 广州 | ${new Date().toLocaleString('zh-CN')}

---
此提醒由 OpenClaw 自动生成`
    };
}

// 生成持续提醒消息
function generateContinueMessage(weather, level) {
    const levelText = {
        'mild': '🟡 轻度',
        'moderate': '🟠 中度',
        'severe': '🔴 重度'
    };
    
    return {
        subject: `🌫️ 回南天持续中（${levelText[level]}）- 湿度${weather.humidity}%`,
        message: `回南天持续中

📊 当前气象:
• 湿度: ${weather.humidity}%
• 露点温度: ${weather.dew}°C
• 空气温度: ${weather.temp}°C

⏰ 回南天已持续一段时间，请继续保持防护措施

📍 广州 | ${new Date().toLocaleString('zh-CN')}

---
此提醒由 OpenClaw 自动生成`
    };
}

// 生成结束消息
function generateEndMessage() {
    return {
        subject: `☀️ 回南天结束 - 湿度已恢复正常`,
        message: `☀️ 回南天结束

好消息！回南天已经结束。

湿度已降至80%以下，可以开窗通风了。

📍 广州 | ${new Date().toLocaleString('zh-CN')}

---
此提醒由 OpenClaw 自动生成`
    };
}

async function main() {
    // 获取天气
    const weather = await getWeather();
    if (!weather) {
        console.log('---RESULT---');
        console.log(JSON.stringify({ error: '获取天气失败' }, null, 2));
        process.exit(1);
    }
    
    // 加载数据
    const data = loadData();
    
    // 记录当前状态
    const isNanhui = checkNanhui(weather);
    const level = isNanhui ? getAlertLevel(weather.humidity) : null;
    
    data.records.push({
        ...weather,
        isNanhui,
        level
    });
    
    // 只保留最近48小时记录
    const cutoff = new Date(Date.now() - 48 * 60 * 60 * 1000);
    data.records = data.records.filter(r => new Date(r.time) > cutoff);
    
    let result = {
        shouldAlert: false,
        alertType: null,
        subject: null,
        message: null,
        weather,
        isNanhui,
        level
    };
    
    // 判断逻辑
    if (isNanhui) {
        // 当前是回南天
        if (!data.alertActive) {
            // 首次进入回南天
            if (shouldSendAlert(data)) {
                const alert = generateAlertMessage(weather, level);
                result.shouldAlert = true;
                result.alertType = 'start';
                result.subject = alert.subject;
                result.message = alert.message;
                
                data.lastAlert = new Date().toISOString();
                data.alertActive = true;
                data.alertLevel = level;
            }
        } else {
            // 持续中的回南天，每24小时提醒一次
            if (shouldSendAlert(data)) {
                const alert = generateContinueMessage(weather, level);
                result.shouldAlert = true;
                result.alertType = 'continue';
                result.subject = alert.subject;
                result.message = alert.message;
                
                data.lastAlert = new Date().toISOString();
            }
        }
    } else {
        // 当前不是回南天
        if (data.alertActive) {
            // 检查是否满足结束条件
            if (checkEndCondition(data.records)) {
                const alert = generateEndMessage();
                result.shouldAlert = true;
                result.alertType = 'end';
                result.subject = alert.subject;
                result.message = alert.message;
                
                data.alertActive = false;
                data.alertLevel = null;
            }
        }
    }
    
    // 保存数据
    saveData(data);
    
    // 输出结果
    console.log('---RESULT---');
    console.log(JSON.stringify(result, null, 2));
}

main().catch(e => {
    console.error('脚本错误:', e);
    process.exit(1);
});
