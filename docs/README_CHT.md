<div align="center">

# 📈 股票智能分析系統

[![GitHub stars](https://img.shields.io/github/stars/ZhuLinsen/daily_stock_analysis?style=social)](https://github.com/ZhuLinsen/daily_stock_analysis/stargazers)
[![CI](https://github.com/ZhuLinsen/daily_stock_analysis/actions/workflows/ci.yml/badge.svg)](https://github.com/ZhuLinsen/daily_stock_analysis/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-Ready-2088FF?logo=github-actions&logoColor=white)](https://github.com/features/actions)

> 🤖 基于 AI 大模型的 A股/港股/美股自選股智能分析系統，每日自動分析並推送「決策儀表盤」到企業微信/飛書/Telegram/郵箱

[**功能特性**](#-功能特性) • [**部署指南**](DEPLOY.md) • [**推送效果**](#-推送效果) • [**使用指南**](full-guide.md) • [**更新日誌**](CHANGELOG.md)

[English](../README_EN.md) | [简体中文](../README.md) | 繁體中文

</div>

## 💖 贊助商 (Sponsors)

<div align="center">
  <a href="https://serpapi.com/baidu-search-api?utm_source=github_daily_stock_analysis" target="_blank">
    <img src="../sources/serpapi_banner_zh.png" alt="輕鬆抓取搜尋引擎上的即時金融新聞數據 - SerpApi" height="160">
  </a>
</div>
<br>

## ✨ 功能特性

### 🎯 核心功能
- **AI 決策儀表盤** - 一句話核心結論 + 精確買賣點位 + 檢查清單
- **多維度分析** - 技術面 + 籌碼分布 + 輿情情報 + 實時行情
- **大盤復盤** - 每日市場概覽、板塊漲跌、北向資金
- **多渠道推送** - 支持企業微信、飛書、Telegram、郵件（自動識別）
- **零成本部署** - GitHub Actions 免費運行，無需服務器
- **💰 白嫖 Gemini API** - Google AI Studio 提供免費額度，個人使用完全夠用
- **🔄 多模型支持** - 支持 OpenAI 兼容 API（DeepSeek、通義千問等）作為備選

### 📊 數據來源
- **行情數據**: AkShare（免費）、Tushare、Baostock、YFinance
- **新聞搜索**: Tavily、SerpAPI、Bocha
- **AI 分析**: 
  - 主力：Google Gemini（gemini-3-flash-preview）—— [免費獲取](https://aistudio.google.com/)
  - 備選：應大家要求，也支持了OpenAI 兼容 API（DeepSeek、通義千問、Moonshot 等）

### 🛡️ 交易理念內置
- ❌ **嚴禁追高** - 乖離率 > 5% 自動標記「危險」
- ✅ **趨勢交易** - MA5 > MA10 > MA20 多頭排列
- 📍 **精確點位** - 買入價、止損價、目標價
- 📋 **檢查清單** - 每項條件用 ✅⚠️❌ 標記

## 🚀 快速開始

### 方式一：GitHub Actions（推薦，零成本）

**無需服務器，每天自動運行！**

#### 1. Fork 本倉庫(順便點下⭐呀)

點擊右上角 `Fork` 按鈕

#### 2. 配置 Secrets

進入你 Fork 的倉庫 → `Settings` → `Secrets and variables` → `Actions` → `New repository secret`

**AI 模型配置（二選一）**

| Secret 名稱 | 說明 | 必填 |
|------------|------|:----:|
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/) 獲取免費 Key | ✅* |
| `OPENAI_API_KEY` | OpenAI 兼容 API Key（支持 DeepSeek、通義千問等） | 可選 |
| `OPENAI_BASE_URL` | OpenAI 兼容 API 地址（如 `https://api.deepseek.com/v1`） | 可選 |
| `OPENAI_MODEL` | 模型名稱（如 `deepseek-chat`） | 可選 |

> *注：`GEMINI_API_KEY` 和 `OPENAI_API_KEY` 至少配置一個

**通知渠道配置（可同時配置多個，全部推送）**

| Secret 名稱 | 說明 | 必填 |
|------------|------|:----:|
| `WECHAT_WEBHOOK_URL` | 企業微信 Webhook URL | 可選 |
| `FEISHU_WEBHOOK_URL` | 飛書 Webhook URL | 可選 |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token（@BotFather 獲取） | 可選 |
| `TELEGRAM_CHAT_ID` | Telegram Chat ID | 可選 |
| `EMAIL_SENDER` | 發件人郵箱（如 `xxx@qq.com`） | 可選 |
| `EMAIL_PASSWORD` | 郵箱授權碼（非登錄密碼） | 可選 |
| `EMAIL_RECEIVERS` | 收件人郵箱（多個用逗號分隔，留空則發給自己） | 可選 |
| `PUSHPLUS_TOKEN` | PushPlus Token（[獲取地址](https://www.pushplus.plus)，國內推送服務） | 可選 |
| `CUSTOM_WEBHOOK_URLS` | 自定義 Webhook（支持釘釘等，多個用逗號分隔） | 可選 |
| `CUSTOM_WEBHOOK_BEARER_TOKEN` | 自定義 Webhook 的 Bearer Token（用於需要認證的 Webhook） | 可選 |
| `SINGLE_STOCK_NOTIFY` | 單股推送模式：設為 `true` 則每分析完一隻股票立即推送 | 可選 |
| `REPORT_TYPE` | 報告類型：`simple`(精簡) 或 `full`(完整)，Docker環境推薦設為 `full` | 可選 |
| `ANALYSIS_DELAY` | 個股分析和大盤分析之間的延遲（秒），避免API限流，如 `10` | 可選 |

> *注：至少配置一個渠道，配置多個則同時推送
>
> 📖 更多配置（Pushover 手機推送、飛書雲文檔等）請參考 [完整配置指南](full-guide.md)

**其他配置**

| Secret 名稱 | 說明 | 必填 |
|------------|------|:----:|
| `STOCK_LIST` | 自選股代碼，如 `600519,hk00700,AAPL,TSLA` | ✅ |
| `TAVILY_API_KEYS` | [Tavily](https://tavily.com/) 搜索 API（新聞搜索） | 推薦 |
| `BOCHA_API_KEYS` | [博查搜索](https://open.bocha.cn/) Web Search API（中文搜索優化，支持AI摘要，多個key用逗號分隔） | 可選 |
| `SERPAPI_API_KEYS` | [SerpAPI](https://serpapi.com/baidu-search-api?utm_source=github_daily_stock_analysis) 備用搜索 | 可選 |
| `TUSHARE_TOKEN` | [Tushare Pro](https://tushare.pro/) Token | 可選 |

#### 3. 啟用 Actions

進入 `Actions` 標籤 → 點擊 `I understand my workflows, go ahead and enable them`

#### 4. 手動測試

`Actions` → `每日股票分析` → `Run workflow` → 選擇模式 → `Run workflow`

#### 5. 完成！

默認每個工作日 **18:00（北京時間）** 自動執行

### 方式二：本地運行 / Docker 部署

> 📖 本地運行、Docker 部署詳細步驟請參考 [完整配置指南](full-guide.md)

## 📱 推送效果

![運行效果演示](../sources/all_2026-01-13_221547.gif)

### 決策儀表盤
```
📊 2026-01-10 決策儀表盤
3隻股票 | 🟢買入:1 🟡觀望:2 🔴賣出:0

🟢 買入 | 貴州茅台(600519)
📌 縮量回踩MA5支撐，乖離率1.2%處於最佳買點
💰 狙擊: 買入1800 | 止損1750 | 目標1900
✅多頭排列 ✅乖離安全 ✅量能配合

🟡 觀望 | 寧德時代(300750)
📌 乖離率7.8%超過5%警戒線，嚴禁追高
⚠️ 等待回調至MA5附近再考慮

---
生成時間: 18:00
```

### 大盤復盤

![大盤復盤推送效果](../sources/dapan_2026-01-13_22-14-52.png)

```
🎯 2026-01-10 大盤復盤

📊 主要指數
- 上證指數: 3250.12 (🟢+0.85%)
- 深證成指: 10521.36 (🟢+1.02%)
- 創業板指: 2156.78 (🟢+1.35%)

📈 市場概況
上漲: 3920 | 下跌: 1349 | 漲停: 155 | 跌停: 3

🔥 板塊表現
領漲: 互聯網服務、文化傳媒、小金屬
領跌: 保險、航空機場、光伏設備
```

## ⚙️ 配置說明

> 📖 完整環境變量、定時任務配置請參考 [完整配置指南](full-guide.md)

## 🖥️ 本地 WebUI（可選）

本地運行時，可啟用 WebUI 來管理配置和觸發分析。

### 啟動方式

| 命令 | 說明 |
|------|------|
| `python main.py --webui` | 啟動 WebUI + 執行一次完整分析 |
| `python main.py --webui-only` | 僅啟動 WebUI，手動觸發分析 |

- 訪問地址：`http://127.0.0.1:8000`
- 詳細說明請參考 [配置指南 - WebUI](full-guide.md#本地-webui-管理界面)

### 功能特性

- 📝 **配置管理** - 查看/修改 `.env` 里的自選股列表
- 🚀 **快速分析** - 頁面輸入股票代碼，一鍵觸發分析
- 📊 **實時進度** - 分析任務狀態實時更新，支持多任務並行

### API 接口

| 接口 | 方法 | 說明 |
|------|------|------|
| `/` | GET | 配置管理頁面 |
| `/health` | GET | 健康檢查 |
| `/analysis?code=xxx` | GET | 觸發單隻股票異步分析 |
| `/tasks` | GET | 查詢所有任務狀態 |
| `/task?id=xxx` | GET | 查詢單個任務狀態 |

## 📁 項目結構

```
daily_stock_analysis/
├── main.py              # 主程序入口
├── webui.py             # WebUI 入口
├── src/                 # 核心業務代碼
│   ├── analyzer.py      # AI 分析器（Gemini）
│   ├── config.py        # 配置管理
│   ├── notification.py  # 消息推送
│   ├── storage.py       # 數據存儲
│   └── ...
├── bot/                 # 機器人模塊
├── web/                 # WebUI 模塊
├── data_provider/       # 數據源適配器
├── docker/              # Docker 配置
│   ├── Dockerfile
│   └── docker-compose.yml
├── docs/                # 項目文檔
│   ├── full-guide.md    # 完整配置指南
│   └── ...
└── .github/workflows/   # GitHub Actions
```

## 🗺️ Roadmap

> 📢 以下功能將視後續情況逐步完成，如果你有好的想法或建議，歡迎 [提交 Issue](https://github.com/ZhuLinsen/daily_stock_analysis/issues) 討論！

### 🔔 通知渠道擴展
- [x] 企業微信機器人
- [x] 飛書機器人
- [x] Telegram Bot
- [x] 郵件通知（SMTP）
- [x] 自定義 Webhook（支持釘釘、Discord、Slack、Bark 等）
- [x] iOS/Android 推送（Pushover）
- [x] 釘釘機器人 （已支持命令交互 >> [相關配置](bot/dingding-bot-config.md)）
### 🤖 AI 模型支持
- [x] Google Gemini（主力，免費額度）
- [x] OpenAI 兼容 API（支持 GPT-4/DeepSeek/通義千問/Claude/文心一言 等）
- [x] 本地模型（Ollama）

### 📊 數據源擴展
- [x] AkShare（免費）
- [x] Tushare Pro
- [x] Baostock
- [x] YFinance

### 🎯 功能增強
- [x] 決策儀表盤
- [x] 大盤復盤
- [x] 定時推送
- [x] GitHub Actions
- [x] 港股支持
- [x] Web 管理界面 (簡易版)
- [x] 美股支持
- [ ] 歷史分析回測

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request！

詳見 [貢獻指南](CONTRIBUTING.md)

## 📄 License
[MIT License](../LICENSE) © 2026 ZhuLinsen

如果你在項目中使用或基於本项目进行二次开发，
非常歡迎在 README 或文檔中註明來源並附上本倉庫鏈接。
這將有助於項目的持續維護和社區發展。

## 📬 聯繫與合作
- GitHub Issues：[提交 Issue](https://github.com/ZhuLinsen/daily_stock_analysis/issues)

## ⭐ Star History

<a href="https://star-history.com/#ZhuLinsen/daily_stock_analysis&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=ZhuLinsen/daily_stock_analysis&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=ZhuLinsen/daily_stock_analysis&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=ZhuLinsen/daily_stock_analysis&type=Date" />
 </picture>
</a>

## ⚠️ 免責聲明

本項目僅供學習和研究使用，不構成任何投資建議。股市有風險，投資需謹慎。作者不對使用本項目產生的任何損失負責。

---

**如果覺得有用，請給個 ⭐ Star 支持一下！**

<!-- 贊賞錨點 -->
<a id="sponsor"></a>
###### ☕ 請我喝杯咖啡
- 如果覺得本項目對你有幫助且行有餘力，可以請我喝杯咖啡，支持項目的持續維護與迭代；不贊賞也完全不影響使用。   
<small>（贊賞時可備註聯繫方式，方便私信致謝與後續交流反饋）</small>
- 感謝支持, 祝您股市長虹，拿主力當提款機。

<div align="center">
  <img src="../sources/wechatpay.jpg" alt="WeChat Pay" width="200" style="margin-right: 20px;">
  <img src="../sources/alipay.jpg" alt="Alipay" width="200">
</div>
