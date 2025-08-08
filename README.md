# 🤖 AI 智慧記帳機器人：AI-Line-Bot

AI-Line-Bot 是一個結合 **LINE Messaging API** 與 **PostgreSQL** 的智慧型記帳機器人。使用者只需在 LINE 對話中輸入簡單的訊息（例如：「早餐 60」），系統就會自動解析、儲存，並為您建立個人化的記帳紀錄。

-----

## ✨ 核心功能特色

  * **自動分類與自訂分類**：系統能自動將您的支出歸類，您也可以新增自己的分類（例如：`新增分類：股票=投資`）。
  * **多語言支援**：支援中、英文，並能自動偵測語言，回覆對應的訊息與選單。
  * **AI 問答**：整合了 ChatGPT，讓您能直接在聊天中進行 AI 互動。
  * **記帳管理**：提供查詢、刪除以及本週總結等功能。
  * **雲端部署**：專案部署在 Vercel，資料則儲存於 PostgreSQL 資料庫。

-----

## 🛠️ 專案結構

```
AI-LineBot/
├── app.py                        # 應用程式入口
├── .env                          # 環境變數設定
├── .gitignore                    # Git 忽略設定
├── requirements.txt              # Python 套件列表
├── README.md                     # 專案說明文件
├── vercel.json                   # Vercel 部署設定
│
├── apps/                         # 核心模組
│   ├── common/                   # 共用工具與資料庫操作
│   │   ├── database.py           # 資料庫 CRUD
│   │   ├── i18n.py               # 多國語系字典
│   │   └── lang_utils.py         # 語言偵測
│   │
│   ├── handlers/                 # LINE Webhook 事件處理
│   │   ├── chart_handler.py      # 圖表產生
│   │   ├── command_utils.py      # 指令比對
│   │   ├── follow_handler.py     # 新增好友事件
│   │   ├── message_handler.py    # 訊息處理
│   │   ├── postback_handler.py   # 按鈕點擊事件
│   │   └── reply_service.py      # FlexMessage 封裝
│   │
│   └── services/                 # 核心商業邏輯與 AI 服務
│       ├── ai_financial_advisor.py   # AI 財務建議
│       ├── call_openai_chatgpt.py    # ChatGPT 整合
│       ├── category_classifier.py    # 分類器
│       └── reply_service.py          # QuickReply 封裝
```

-----

## 💡 功能說明

### 📝 自動分類與自訂分類

系統會根據您的輸入，自動將項目分類為以下幾種：

  * **餐飲 (food)**
  * **交通 (transport)**
  * **娛樂 (entertainment)**
  * **購物 (shopping)**
  * **醫療 (medical)**
  * **其他 (others)**

**自訂分類：** 您可以輕鬆定義自己的分類，無論是中文或英文都支援。

  * `新增分類：股票=投資`
  * `add category: coffee=food`

一旦設定完成，當您輸入「股票 5000」時，系統就會自動歸類為「投資」。

**範例輸入與結果：**

| 使用者輸入 | 自動分類結果 | 回覆語言 |
| :--- | :--- | :--- |
| `午餐 100` | `food` | 中文 |
| `uber 150` | `transport` | 中文 |
| `add category: coffee=food` | 自訂分類建立成功 | 英文 |
| `coffee 70` | `food`（來自自訂） | 英文 |

### 🌍 語言自動切換

系統會自動偵測您輸入的語言，並以對應的語系回覆，所有文字內容都支援 i18n 設計，便於未來擴充。

-----

## 🚀 快速開始

### 環境安裝

```bash
pip install -r requirements.txt
```

### 資料庫設計

本專案使用 PostgreSQL，包含 `users`、`transactions`、`categories` 三個資料表。

#### 🧑‍💼 `users` (使用者資料)

儲存 LINE 使用者的基本資訊。

  * **id**: 主鍵 ID
  * **line\_user\_id**: LINE 上的唯一 ID
  * **display\_name**: 使用者暱稱
  * **created\_at**: 帳號建立時間

#### 💰 `transactions` (記帳紀錄)

記錄每一筆支出或收入。

  * **id**: 交易主鍵 ID
  * **user\_id**: 對應 `users` 表
  * **category**: 分類名稱
  * **amount**: 金額
  * **message**: 原始輸入訊息
  * **created\_at**: 記帳時間
  * **type**: 交易類型（`expense` 或 `income`）

#### 🏷️ `categories` (自訂分類)

每位使用者可定義專屬的分類與關鍵字。

  * **id**: 分類主鍵 ID
  * **user\_id**: 對應 `users` 表
  * **category**: 分類名稱
  * **keywords**: 對應的關鍵字集合
  * **created\_at**: 建立時間

-----

## 📄 實作與開發流程建議

1.  **資料表建立**：首先建立 `categories` 和 `transactions` 資料表，並設定好關聯。
2.  **預設分類**：在 `categories` 表中預先建立一組系統預設分類，讓使用者能立即使用。
3.  **記帳流程**：當使用者輸入 `午餐 100`，系統會從 `categories` 表查詢對應的分類，並將新紀錄寫入 `transactions` 表。
4.  **新增分類流程**：引導使用者新增分類，並將其與系統預設的主分類建立階層關係，例如將 `周邊` 歸類在 `購物` 主分類下。
5.  **報表/圖表**：利用 SQL 查詢搭配 `GROUP BY` 功能，依據主分類或子分類產生統計圖表。

這種獨立分類表與父子階層的設計，能兼顧資料的統一性與使用者自訂的靈活性，是記帳應用程式中最成熟的解決方案。

-----

## 🧑‍💻 作者

佳融 Wu — [GitHub](https://www.google.com/search?q=https://github.com/your-github-profile)