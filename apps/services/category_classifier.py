import apps.common.database as db

CATEGORY_KEYWORDS = {
    "food": [
        "早餐", "午餐", "晚餐", "早午餐", "消夜", "宵夜", "便當", "吃", "餐", "飯", "飲料", "喝",
        "咖啡", "奶茶", "星巴克", "麥當勞", "肯德基", "subway", "burger", "food", "drink", "早點",
        "滷味", "火鍋", "拉麵", "餐廳", "外送", "ubereats", "foodpanda", "炸雞", "鹹酥雞", "早餐店"
    ],

    "transport": [
        "捷運", "公車", "交通", "uber", "計程車", "高鐵", "台鐵", "客運", "小黃", "油", "停車", "車票",
        "租車", "機車", "開車", "搭車", "taxi", "train", "bus", "bike", "油錢", "過路費", "加油"
    ],

    "entertainment": [
        "電影", "戲院", "看劇", "netflix", "youtube", "娛樂", "演唱會", "遊戲", "手遊", "ps5", "switch",
        "game", "音樂", "spotify", "追劇", "動漫", "漫畫", "streaming", "直播", "卡拉OK", "唱歌", "表演"
    ],

    "shopping": [
        "買", "購物", "momo", "蝦皮", "shopee", "pchome", "7-11", "全聯", "家樂福", "網購", "百貨", "超商",
        "超市", "衣服", "鞋子", "包包", "飾品", "化妝品", "美妝", "保養", "電器", "家電", "3c", "手機殼", 
        "耳機", "鍵盤", "衣物", "購買", "淘寶", "京東", "便利商店", "購"
    ],

    "medical": [
        "醫生", "藥", "藥局", "診所", "醫院", "掛號", "看病", "牙醫", "健保", "自費", "檢查", "打針", "流感",
        "covid", "處方", "生病", "保健", "醫療", "眼科", "皮膚科", "醫藥", "診療", "medical", "hospital"
    ],

    "others": [
        # fallback 類別，如果都沒命中
    ]
}

def classify_category(text: str, user_id: str = "") -> str:
    text = text.lower()

    if user_id:
        user_keywords = db.get_user_categories(user_id)
        for kw, cat in user_keywords.items():
            if kw in text:
                return cat

    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return category

    return "others"