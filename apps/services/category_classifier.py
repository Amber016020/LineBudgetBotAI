import os
import threading
import numpy as np
from openai import OpenAI

# Minimal comments, English only.
_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
_LOCK = threading.Lock()

CORE_CATEGORIES = {
    "food": (
        "餐飲美食, 吃飯, 吃東西, 喝東西, 飲料, 咖啡, 早餐, 午餐, 晚餐, 宵夜, "
        "便當, 小吃, 零食, 速食, 麥當勞, 肯德基, 漢堡王, 炸雞, 披薩, 義大利麵, 拉麵, 火鍋, "
        "燒肉, 燒烤, 自助餐, 鹽酥雞, 手搖飲, 奶茶, 果汁, 冰淇淋, 甜點, 蛋糕, 麵包, 餅乾"
    ),
    "transport": (
        "交通, 搭車, 捷運, 公車, 高鐵, 台鐵, 計程車, 小黃, Uber, uber, 汽車, 機車, 油錢, 停車費, "
        "高速公路, 收費站, 共享單車, YouBike, 飛機, 機票, 船票"
    ),
    "shopping": (
        "購物, 買東西, 買衣服, 衣服, 褲子, 鞋子, 包包, 配件, 手機, 3C, 電腦, 平板, 耳機, 相機, "
        "生活用品, 衛生紙, 洗髮精, 清潔用品, 廚房用品, 家具, 家電, momo, 蝦皮, shopee, "
        "全聯, 家樂福, 大潤發, 好市多, costco"
    ),
    "entertainment": (
        "娛樂, 看電影, 電影票, 遊戲, 電動, 手遊, 桌遊, 唱歌, KTV, 演唱會, 展覽, 表演, 演劇, 演出, "
        "運動, 健身, 健身房, 游泳, 球類, 旅遊, 旅行, 觀光, 住宿, 飯店, 民宿, 門票, 遊樂園"
    ),
    "medical": (
        "醫療, 看醫生, 診所, 掛號, 藥品, 藥局, 西藥, 中藥, 感冒, 打針, 牙醫, 洗牙, 健檢, 體檢, "
        "物理治療, 復健, 醫院, 手術, 保健品, 維他命"
    ),
    "investment": (
        "投資, 股票, 基金, ETF, 債券, 虛擬貨幣, 加密貨幣, 比特幣, Ethereum, 幣安, 期貨, 外匯, "
        "定存, 儲蓄, 保險, 股票手續費, 匯款, 匯率"
    ),
    "others": (
        "其他, 雜項, 雜費, 捐款, 禮物, 紅包, 婚禮, 喪禮, 慶生, 稅金, 手續費, 罰款, "
        "寵物, 寵物飼料, 寵物用品, 寵物醫療"
    ),
}

_category_vectors = None
_EMBED_MODEL = "text-embedding-3-small"
_FALLBACK_CATEGORY = "others"
_SIM_THRESHOLD = 0.30


def _embed(texts: list[str]) -> list[list[float]]:
    resp = _client.embeddings.create(input=texts, model=_EMBED_MODEL)
    return [d.embedding for d in resp.data]


def _ensure_category_vectors():
    global _category_vectors
    with _LOCK:
        if _category_vectors is not None:
            return
        try:
            vecs = _embed(list(CORE_CATEGORIES.values()))
            _category_vectors = {
                name: vecs[i] for i, name in enumerate(CORE_CATEGORIES.keys())
            }
            # print("Category vectors initialized.")
        except Exception:
            _category_vectors = {k: np.zeros(1536).tolist() for k in CORE_CATEGORIES}  # safe fallback


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    return float(np.dot(a, b) / denom) if denom else 0.0


def classify_category_by_embedding(text: str) -> str:
    """Return best-matched category using embeddings."""
    if not text:
        return _FALLBACK_CATEGORY
    _ensure_category_vectors()
    try:
        v = np.array(_embed([text])[0], dtype=np.float32)
    except Exception:
        return _FALLBACK_CATEGORY

    best_cat, best_sim = _FALLBACK_CATEGORY, -1.0
    for name, vec in _category_vectors.items():
        sim = _cosine(v, np.array(vec, dtype=np.float32))
        if sim > best_sim:
            best_cat, best_sim = name, sim

    return best_cat if best_sim >= _SIM_THRESHOLD else _FALLBACK_CATEGORY
