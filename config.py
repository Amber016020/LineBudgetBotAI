# config.py
DEFAULT_CATEGORIES = [
    {"key": "food", "name": "餐飲"},
    {"key": "investment", "name": "投資"},
    {"key": "transport", "name": "交通"},
    {"key": "entertainment", "name": "娛樂"},
    {"key": "shopping", "name": "購物"},
    {"key": "medical", "name": "醫療"},
    {"key": "others", "name": "其他"},
]


CORE_CATEGORIES = {
    "food": {
        "zh-TW": "餐飲",
        "en": "Food",
        "keywords": (
            "餐飲美食, 吃飯, 吃東西, 喝東西, 飲料, 咖啡, 早餐, 午餐, 晚餐, 宵夜, "
            "便當, 小吃, 零食, 速食, 麥當勞, 肯德基, 漢堡王, 炸雞, 披薩, 義大利麵, 拉麵, 火鍋, "
            "燒肉, 燒烤, 自助餐, 鹽酥雞, 手搖飲, 奶茶, 果汁, 冰淇淋, 甜點, 蛋糕, 麵包, 餅乾"
        )
    },
    "investment": {
        "zh-TW": "投資",
        "en": "Investment",
        "keywords": (
            "投資, 股票, 基金, ETF, 債券, 虛擬貨幣, 加密貨幣, 比特幣, Ethereum, 幣安, 期貨, 外匯, "
            "定存, 儲蓄, 保險, 股票手續費, 匯款, 匯率"
        )
    },
    "transport": {
        "zh-TW": "交通",
        "en": "Transport",
        "keywords": (
            "交通, 搭車, 捷運, 公車, 高鐵, 台鐵, 計程車, 小黃, Uber, uber, 汽車, 機車, 油錢, 停車費, "
            "高速公路, 收費站, 共享單車, YouBike, 飛機, 機票, 船票"
        )
    },
    "entertainment": {
        "zh-TW": "娛樂",
        "en": "Entertainment",
        "keywords": (
            "娛樂, 看電影, 電影票, 遊戲, 電動, 手遊, 桌遊, 唱歌, KTV, 演唱會, 展覽, 表演, 演劇, 演出, "
            "運動, 健身, 健身房, 游泳, 球類, 旅遊, 旅行, 觀光, 住宿, 飯店, 民宿, 門票, 遊樂園"
        )
    },
    "shopping": {
        "zh-TW": "購物",
        "en": "Shopping",
        "keywords": (
            "購物, 買東西, 買衣服, 衣服, 褲子, 鞋子, 包包, 配件, 手機, 3C, 電腦, 平板, 耳機, 相機, "
            "生活用品, 衛生紙, 洗髮精, 清潔用品, 廚房用品, 家具, 家電, momo, 蝦皮, shopee, "
            "全聯, 家樂福, 大潤發, 好市多, costco"
        )
    },
    "medical": {
        "zh-TW": "醫療",
        "en": "Medical",
        "keywords": (
            "醫療, 看醫生, 診所, 掛號, 藥品, 藥局, 西藥, 中藥, 感冒, 打針, 牙醫, 洗牙, 健檢, 體檢, "
            "物理治療, 復健, 醫院, 手術, 保健品, 維他命"
        )
    },
    "others": {
        "zh-TW": "其他",
        "en": "Others",
        "keywords": (
            "其他, 雜項, 雜費, 捐款, 礼物, 紅包, 婚禮, 喪禮, 慶生, 稅金, 手續費, 罰款, "
            "寵物, 寵物飼料, 寵物用品, 寵物醫療"
        )
    },
}

INTENTS = {
    "check": (
        "list recent records and allow deletion; "
        "查詢最近記錄, 查帳, 查看明細, 看最近花了什麼, 最近消費, 最近帳目, 列出紀錄"
    ),
    "change_language": (
        "change preferred language, e.g., 'language en'; "
        "切換語言, 語言 zh-TW, 語言 en, 語系, 語言設定"
    ),
    "chart": (
        "show expense chart for week/month/year; "
        "支出圖, 圖表, 消費圖, 週支出圖, 月支出圖, 年支出圖, 趨勢圖, 長條圖, 圓餅圖"
    ),
    "summary": (
        "show income/expense/balance summary; "
        "總結, 本週總結, 本月總結, 本年總結, 收支統計, 統計, 總覽"
    ),
     "add_category_quick": (
        "quickly add a subcategory under a root; "
        "新增 子類別, 新增 XXX, <大類>類別內細分<子類別>, 在娛樂底下新增訂閱, 在others底下新增孝親費"
    ),
    "record": (
        "record an expense like '早餐 60'; "
        "記帳, 早餐 60, 午餐 120, 晚餐 200, 咖啡 80, 便當 95, 公車 30, 捷運 50, "
        "uber 150, 計程車 200, 高鐵 1500, 買書 450, 買鞋 1800, momo 999, 蝦皮 320, "
        "星巴克 150, 看電影 300, 唱歌 600, switch 遊戲 1500, 感冒看醫生 300, 藥局 200, "
        "牙醫 800, 股票 5000, 基金 10000, 投資 2000, 房租 25000, 水費 600, 電費 900"
    ),
    "ai": (
        "general chat or question to AI; "
        "我這週花最多錢的是什麼？, 這個月交通花多少？, 早餐平均花多少？, 幫我看看哪一類超支, "
        "有沒有省錢建議, 近三個月趨勢, 我是不是喝太多手搖, 最高單筆是哪一筆, "
        "把最近的娛樂支出列出來, 這週跟上週比較一下, 本月預算剩多少, "
        "幫我看看早餐平均花多少？"
        "你是誰, 你可以做什麼, 你有什麼功能, 你會什麼, 你能幹嘛, 你支援什麼, 使用說明, 幫助, 幫我介紹功能, "
        "help, what can you do, who are you, what are your features, capabilities, how to use"
    ),
    "unknown": (
        "fallback for unrecognized input; "
        "無法辨識, 不知道, 看不懂, 亂打, 其他"
    )
}

ALLOWED_LANGS = {"zh-TW", "en"}