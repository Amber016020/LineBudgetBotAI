# AI-Line-Bot 💬🤖

AI-Line-Bot 是一個結合 LINE Messaging API 與 PostgreSQL 的智慧型記帳機器人。使用者可透過對話輸入記帳訊息（例如：「早餐 60」），系統會自動解析、儲存並建立個人化記帳紀錄。

這是一個使用 LINE Messaging API 與 Flask 開發的記帳聊天機器人，支援：

💡 自動分類 & 使用者自訂分類

🌏 多語言支援（中/英文）

🤖 AI 問答（整合 ChatGPT）

🗃️ 記帳查詢、刪除與本週總結

☁️ 部署於 Vercel + 資料儲存於 PostgreSQL

 分類訊息處理邏輯（message_handler.py）

 加入 NLP 模組協助情境分析

 增加查詢與報表功能（如統計圖表、花費分析）

---

## 📦 專案結構

AI-LineBot/
├── app.py                        # 主入口，啟動 Flask 應用與 LINE webhook 註冊
├── .env                          # 儲存 LINE channel 的機密金鑰（CHANNEL_SECRET、ACCESS_TOKEN）
├── .gitignore                    # Git 忽略項目設定
├── requirements.txt              # 專案所需 Python 套件列表
├── README.md                     # 專案說明文件
├── vercel.json                   # Vercel 部署設定
│
├── apps/                         # 專案核心模組目錄
│   ├── common/                   # 共用工具與資料庫層
│   │   ├── database.py           # 與 MySQL 資料庫的 CRUD 操作
│   │   ├── i18n.py               # 多語系字典與國際化工具函式
│   │   └── lang_utils.py         # 語言偵測工具，例如自動判斷中英文
│   │
│   ├── handlers/                 # LINE webhook 對應事件處理器
│   │   ├── chart_handler.py      # 支出圖表產生邏輯（如週/月/年圖）
│   │   ├── command_utils.py      # 指令比對與分類（record、summary 等）
│   │   ├── follow_handler.py     # 處理 FollowEvent（使用者加好友）
│   │   ├── message_handler.py    # 處理文字訊息事件（MessageEvent）
│   │   ├── postback_handler.py   # 處理按鈕點擊事件（PostbackEvent）
│   │   └── reply_service.py      # 包含 FlexMessage 的封裝邏輯
│   │
│   └── services/                 # 核心商業邏輯或 AI 外部服務封裝
│       ├── ai_financial_advisor.py   # 分析訊息是否為 AI 詢問，並回應建議
│       ├── call_openai_chatgpt.py    # 呼叫 OpenAI ChatGPT 的封裝邏輯
│       ├── category_classifier.py    # 關鍵字分類器，含使用者自訂類別
│       └── reply_service.py          # 快速回覆（QuickReply）封裝邏輯
│
├── .vscode/                     # VS Code 本地開發設定（可忽略）
└── __pycache__/                # Python 編譯快取（應被 Git 忽略）


---

## 💡 功能介紹：分類與記帳
✅ 自動分類記帳
使用者只需輸入如 晚餐 120、uber 300 等簡單格式，即可自動記錄支出/收入。

系統會根據關鍵字自動分類為：

food（餐飲）

transport（交通）

entertainment（娛樂）

shopping（購物）

medical（醫療）

others（其他）

✅ 使用者自訂分類（中英皆可）
使用者可自行定義分類規則，例如：

新增分類：股票=investment

add category: coffee=food

一旦定義成功，未來輸入「股票 5000」就會自動分類為 investment。

支援多語指令格式，並提供格式錯誤提示。

✅ 語言自動切換
系統會根據使用者輸入文字自動判斷語言（中或英），並回覆對應語系的訊息與選單文字。

所有文字內容均支援 i18n 設計，便於擴展多語版本。

📦 範例輸入與結果
使用者輸入	自動分類結果	回覆語言
午餐 100	food	中文
uber 150	transport	中文
add category: coffee=food	自訂分類建立成功	英文
coffee 70	food（來自自訂）	英文

## 🚀 快速開始

### 安裝依賴

```bash
pip install -r requirements.txt
```

🧠 功能說明
📥 使用者進入聊天室時自動記錄基本資料

🧾 輸入類似「午餐 100」即可自動寫入記帳系統

🧠 （開發中）加入 AI 模組，如「幫我看哪天花最多」等功能

🔐 使用 Supabase PostgreSQL 資料庫作為儲存後端

📚 資料庫設計說明
本系統的資料庫設計包含三張主要資料表：users、transactions、categories，分別用於儲存使用者資料、記帳紀錄，以及自訂分類關鍵字。

🧑‍💼 users（使用者資料）
儲存每位 LINE 使用者的基本資料。
包含欄位如下：

id：使用者的主鍵 ID，為自動遞增的整數。

line_user_id：使用者在 LINE 上的唯一 ID。

display_name：使用者的暱稱，透過 LINE API 取得。

created_at：使用者加入時間，會自動紀錄時間戳記。

每位使用者可以擁有多筆記帳紀錄與自訂分類。

💰 transactions（記帳紀錄）
用來記錄使用者每一筆記帳的資料，可為支出或收入。
包含欄位如下：

id：交易紀錄主鍵 ID。

user_id：對應 users 表的使用者 ID，表示這筆紀錄屬於哪位使用者。

category：分類名稱，例如「午餐」、「交通」等。

amount：金額，為整數型態。

message：使用者輸入的原始文字訊息，可用於 NLP 分析。

created_at：記帳時間，自動填入時間戳記。

type：交易類型，分為 expense（支出）或 income（收入）。

🏷️ categories（自訂分類關鍵字）
每位使用者可定義自己的分類與對應的關鍵字，讓系統在自動分類時更加準確。
包含欄位如下：

id：分類主鍵 ID。

user_id：對應 users 表的使用者 ID。

category：分類名稱（例如 food、娛樂、交通等）。

keywords：與該分類對應的關鍵字集合（例如「吃」、「晚餐」、「便當」等）。

created_at：建立時間，系統自動填入。

🔗 資料表關聯
每位使用者（users）可以有多筆記帳紀錄（transactions）。


# 總結與實作流程建議
建立 Categories 和 Transactions 資料表，並定義好它們之間的關聯。

提供一組優質的系統預設分類：在 Categories 表中預先建立好一些常見的主分類 (如餐飲、購物、交通、娛樂、醫療) 和子分類 (如早餐、午餐、晚餐、捷運、公車)，並將 is_system_default 設為 true，user_id 設為 0。

設計記帳流程：

使用者輸入「午餐 100」。

系統在 Categories 表中查詢 name = "午餐" 且 user_id 為該使用者或 0 的紀錄。

找到對應的 category_id (例如 101)。

在 Transactions 表中新增一筆紀錄，category_id 填入 101。

設計新增分類流程：

使用者想新增「周邊」分類。

系統詢問：「『周邊』要歸類在哪個主分類下呢？」並提供「購物」、「娛樂」等選項。

使用者選擇「購物」(其 id 為 2)。

系統在 Categories 表中新增一筆紀錄：name="周邊", parent_id=2, user_id=123。

設計報表/圖表：

提供切換按鈕，讓使用者選擇要依據「主分類」還是「子分類」來檢視圖表。

背後的 SQL 查詢根據選項，決定要 GROUP BY 子分類的 ID 還是父分類的 ID。

採用這個 「獨立分類表 + 父子階層」 的設計，可以完美兼顧資料的統一性與使用者自訂的靈活性，是目前記帳軟體中最成熟、也最具擴充性的解決方案。

每位使用者也可以設定多組自訂分類（categories）。

# 📤 部署步驟 todo

# 🧑‍💻 作者
佳融 Wu — GitHub