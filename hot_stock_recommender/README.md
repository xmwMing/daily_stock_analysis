# 🔥 热门股票推荐系统

## 📋 目录

- [功能介绍](#功能介绍)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [GitHub Actions 部署](#github-actions-部署)
- [使用方式](#使用方式)
- [系统架构](#系统架构)
- [常见问题](#常见问题)

---

## 功能介绍

热门股票推荐系统能够自动从市场中发现热门股票，基于趋势分析和交易理念进行智能筛选，并在每日分析报告中推荐最值得关注的股票。

### 核心特性

- ✅ **自动发现**：从涨幅榜、成交额榜、换手率榜自动发现热门股票
- ✅ **智能过滤**：过滤ST股票、价格异常、市值过小、新股等
- ✅ **趋势分析**：基于MA5>MA10>MA20多头排列判断
- ✅ **评分系统**：综合趋势评分和市场热度评分
- ✅ **分类标签**：强势股、回调股、突破股、价值股、潜力股
- ✅ **风险评估**：基于换手率、涨幅和波动率判断风险等级
- ✅ **报告生成**：生成详细的 Markdown 格式推荐报告
- ✅ **系统集成**：自动集成到每日分析流程

### 推荐流程

```
1. 发现热门股票（默认每个榜单30只）
   ├─ 涨幅榜前30只
   ├─ 成交额榜前30只
   └─ 换手率榜前30只
   
2. 过滤筛选
   ├─ 排除ST股票
   ├─ 排除价格异常（<3元 或 >300元）
   ├─ 排除小市值（<50亿）
   └─ 排除新股（上市<90天）
   
3. 深度分析（约30-60只）
   ├─ 获取60天历史数据
   ├─ 趋势分析（MA5>MA10>MA20）
   ├─ 计算综合评分（趋势×0.6 + 热度×0.4）
   ├─ 股票分类
   └─ 风险评估
   
4. 生成推荐（前5只）
   ├─ 按评分排序
   ├─ 生成推荐报告
   └─ 推送通知
```

---

## 快速开始

### 本地测试

```bash
# 1. 进入项目目录
cd daily_stock_analysis

# 2. 测试热门股票发现器
python test_finder.py

# 3. 测试完整推荐系统
python test_hot_recommender.py

# 4. 运行完整分析（包含热门推荐）
python main.py
```

### GitHub Actions 部署

**✅ 可以直接部署！无需额外配置！**

```bash
# 1. 提交代码
git add .
git commit -m "feat: 添加热门股票推荐功能"
git push origin main

# 2. 手动触发测试
# 进入 GitHub 仓库 > Actions > 每日股票分析 > Run workflow > 选择 full 模式

# 3. 查看结果
# 在 Actions 页面查看日志，下载 Artifacts 查看报告
```

---

## 配置说明

### 配置文件位置

`daily_stock_analysis/config.py` 中的 `HOT_STOCK_CONFIG` 字典。

### 核心配置项

```python
HOT_STOCK_CONFIG = {
    # === 获取数量配置 ===
    'fetch_count': 30,           # 从每个榜单获取的股票数量
                                 # 推荐：20-30（快速）| 50（全面）
    
    # === 推荐配置 ===
    'top_n': 5,                  # 最终推荐的股票数量
    'min_score': 60,             # 最低推荐评分阈值
    
    # === 性能配置 ===
    'cache_ttl': 1800,           # 缓存有效期（秒），30分钟
    'max_concurrent': 10,        # 最大并发分析线程数
    'history_days': 60,          # 获取历史数据的天数
    'min_history_days': 30,      # 最少需要的历史数据天数
    
    # === 过滤条件 ===
    'filter': {
        'min_price': 3.0,        # 最低价格（元）
        'max_price': 300.0,      # 最高价格（元）
        'min_market_cap': 5e9,   # 最小市值（50亿元）
        'min_list_days': 90,     # 最少上市天数
    },
    
    # === 评分权重 ===
    'score_weights': {
        'trend': 0.6,            # 趋势评分权重
        'market_heat': 0.4,      # 市场热度权重
    },
}
```

### 常见配置场景

#### 场景1：快速分析（推荐）

```python
'fetch_count': 30,  # 每个榜单30只
'top_n': 5,         # 推荐5只
```
- 预计时间：1-2分钟
- 候选股票：30-60只
- 适合：日常使用、GitHub Actions

#### 场景2：全面覆盖

```python
'fetch_count': 50,  # 每个榜单50只
'top_n': 10,        # 推荐10只
```
- 预计时间：3-5分钟
- 候选股票：50-100只
- 适合：周末深度分析

#### 场景3：精选模式

```python
'fetch_count': 20,  # 每个榜单20只
'top_n': 3,         # 推荐3只
'min_score': 70,    # 提高评分阈值
```
- 预计时间：1分钟以内
- 候选股票：20-40只
- 适合：快速筛选高质量股票

### 性能对比

| fetch_count | 候选股票数 | 预计时间 | 推荐场景 |
|------------|----------|---------|---------|
| 20 | 20-40只 | 1分钟 | 快速精选 |
| 30 | 30-60只 | 1-2分钟 | **推荐配置** |
| 50 | 50-100只 | 3-5分钟 | 全面覆盖 |
| 100 | 100-200只 | 5-10分钟 | 不推荐 |

---

## GitHub Actions 部署

### 部署前检查

✅ 所有代码已实现并集成  
✅ 所有依赖已包含在 requirements.txt  
✅ GitHub Actions 配置已支持  
✅ 默认配置已优化  

### 部署步骤

#### 1. 提交代码

```bash
cd daily_stock_analysis
git add .
git commit -m "feat: 添加热门股票推荐功能"
git push origin main
```

#### 2. 配置 Secrets（如果还没配置）

在 GitHub 仓库的 Settings > Secrets and variables > Actions 中配置：

**必需**：
- `GEMINI_API_KEY` - Gemini API 密钥

**可选**：
- `STOCK_LIST` - 自选股列表
- `WECHAT_WEBHOOK_URL` - 企业微信推送
- `FEISHU_WEBHOOK_URL` - 飞书推送
- `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` - Telegram 推送

#### 3. 手动测试

1. 进入 GitHub 仓库
2. 点击 **Actions** 标签
3. 选择 **每日股票分析** 工作流
4. 点击 **Run workflow**
5. 选择 `full` 模式（完整分析）
6. 点击 **Run workflow** 开始

#### 4. 查看结果

- 在 Actions 页面查看运行日志
- 下载 Artifacts 查看生成的报告
- 检查通知渠道是否收到推送

### 自动运行

部署后，系统会在每个交易日（周一到周五）北京时间 18:00 自动运行：

1. ✅ 分析你的自选股
2. ✅ 大盘复盘分析
3. ✅ **热门股票推荐**（新增）
4. ✅ 生成报告并推送

### GitHub Actions 优化建议

对于 GitHub Actions 环境，建议调整配置以加快速度：

```python
HOT_STOCK_CONFIG = {
    'fetch_count': 20,        # 减少到 20
    'max_concurrent': 5,      # 减少到 5
    # ... 其他保持默认
}
```

**原因**：
- GitHub Actions 有运行时间限制
- 避免触发 API 频率限制
- 20只已足够覆盖主要热门股票

---

## 使用方式

### 独立使用

```python
from hot_stock_recommender import HotStockRecommender

# 创建推荐系统
recommender = HotStockRecommender()

# 执行推荐流程，获取报告
report = recommender.run()
print(report)

# 或者只获取推荐列表
recommendations = recommender.get_recommendations()
for rec in recommendations:
    print(f"{rec.stock_info.name}: {rec.score}分 - {rec.category}")
```

### 集成在每日分析中

热门股票推荐已自动集成到每日分析流程中，运行 `python main.py` 时会自动执行。

### 输出文件

运行后会生成以下文件：

```
reports/
├── report_20260126.md                      # 个股分析报告
├── market_review_20260126.md               # 大盘复盘报告
└── hot_stock_recommendations_20260126.md   # 🔥 热门股票推荐报告

logs/
└── stock_analysis_20260126.log             # 运行日志
```

### 推荐报告示例

```markdown
# 🔥 2026-01-26 热门股票推荐

> 共推荐 **5** 只热门股票

---

## 1. 🚀 贵州茅台 (600519)

**综合评分**: 85.3分 | **分类**: 强势股 | **风险**: 🟡 中

### 💡 推荐理由

多头排列强势，成交活跃，趋势向上明确。

### 📊 基本信息

| 指标 | 数值 |
|------|------|
| 当前价 | 1650.00 元 |
| 涨跌幅 | +3.50% |
| 成交量 | 120.50 万手 |
| 成交额 | 198.83 亿元 |
| 换手率 | 1.25% |
| 市值 | 20720.00 亿元 |

### 📈 趋势分析

**趋势状态**: 多头排列
**均线排列**: MA5 > MA10 > MA20
**买入信号**: 强烈买入 (评分: 85分)

**信号原因**:
- 多头排列，趋势向上
- 价格位于均线上方，支撑强劲
- 成交量温和放大，资金流入

### ⚠️ 风险提示

短期涨幅较大，注意回调风险。建议分批建仓，设置止损位。

---
```

---

## 系统架构

### 模块组成

```
HotStockRecommender (主入口)
├── HotStockFinder (热门股票发现)
│   ├── 获取涨幅榜
│   ├── 获取成交额榜
│   ├── 获取换手率榜
│   ├── 去重合并
│   └── 过滤筛选
│
├── StockRecommender (股票推荐)
│   ├── 并发获取历史数据
│   ├── 趋势分析（复用 StockTrendAnalyzer）
│   ├── 评分算法
│   ├── 股票分类
│   ├── 风险评估
│   └── 生成推荐列表
│
└── RecommendationReport (报告生成)
    ├── 格式化推荐卡片
    ├── 生成 Markdown 报告
    └── 处理空推荐列表
```

### 文件结构

```
hot_stock_recommender/
├── __init__.py          # 主入口类 HotStockRecommender
├── models.py            # 数据模型（StockInfo, Recommendation）
├── finder.py            # 热门股票发现器
├── recommender.py       # 股票推荐器
├── report.py            # 报告生成器
└── README.md            # 本文档
```

### 性能优化

1. **缓存机制**：热门股票列表缓存30分钟
2. **并发处理**：使用线程池并发分析，默认10个线程
3. **数据复用**：复用主程序的 DataFetcherManager 和 StockTrendAnalyzer

---

## 常见问题

### Q1: 如何调整获取的股票数量？

**A**: 编辑 `config.py` 中的 `fetch_count`：

```python
HOT_STOCK_CONFIG = {
    'fetch_count': 20,  # 改为你想要的数量（推荐 20-50）
    # ...
}
```

### Q2: 为什么没有生成推荐报告？

**A**: 可能的原因：
- 市场整体调整，无符合条件的股票（正常情况）
- 过滤条件过严
- API 调用失败

查看日志确认具体原因。如果是无符合条件的股票，系统会生成空报告说明。

### Q3: 分析时间太长怎么办？

**A**: 减少获取数量：

```python
'fetch_count': 20,        # 减少到 20
'max_concurrent': 5,      # 减少并发数
```

### Q4: 如何调整推荐数量？

**A**: 修改 `top_n` 配置：

```python
'top_n': 3,  # 改为你想要的数量（推荐 3-10）
```

### Q5: 遇到 API 频率限制怎么办？

**A**: 系统已自动配置：
- 30分钟缓存
- 3秒请求延时（GitHub Actions）
- 通常不会遇到此问题

如果仍然遇到，可以：
- 减少 `fetch_count`
- 减少 `max_concurrent`
- 增加 `GEMINI_REQUEST_DELAY`

### Q6: 如何提高推荐质量？

**A**: 调整评分阈值：

```python
'min_score': 70,  # 提高到 70（默认 60）
```

这样只会推荐高质量股票，但可能导致推荐数量减少。

### Q7: 支持哪些通知渠道？

**A**: 支持多种渠道，可同时配置：
- 企业微信
- 飞书
- Telegram
- 邮件
- 自定义 Webhook
- Discord

配置方法见 [GitHub Actions 部署](#github-actions-部署) 章节。

### Q8: 本地运行和 GitHub Actions 有什么区别？

**A**: 
- **本地运行**：可以使用更大的 `fetch_count`（如 50-100）
- **GitHub Actions**：建议使用较小的 `fetch_count`（如 20-30）以加快速度

### Q9: 如何查看详细的运行日志？

**A**: 
- **本地**：查看 `logs/stock_analysis_YYYYMMDD.log`
- **GitHub Actions**：在 Actions 页面查看运行日志，或下载 Artifacts

### Q10: 推荐的股票可靠吗？

**A**: 
- 推荐基于技术分析和市场数据
- 仅供参考，不构成投资建议
- 建议结合自己的判断和风险承受能力
- 注意风险提示和止损设置

---

## 技术支持

如遇到问题，请检查：

1. **运行日志**：查看详细的错误信息
2. **配置文件**：确认配置是否正确
3. **API 密钥**：确认 API 密钥是否有效
4. **网络连接**：确认网络是否正常

---

**版本**: 1.0.0  
**最后更新**: 2026-01-26  
**作者**: Kiro AI Assistant
