import psycopg2
import os
from datetime import datetime, timedelta

POSTGRES_URL = os.getenv("POSTGRES_URL")

if not POSTGRES_URL:
    raise ValueError("POSTGRES_URL is not set in the environment variables.")

# Establish the connection and enable autocommit
conn = psycopg2.connect(POSTGRES_URL)
conn.autocommit = True  # Recommended to avoid manual commit

# Ensure the user exists in the database
def ensure_user_exists(user_id, display_name=None):
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM users WHERE line_user_id = %s", (user_id,))
        if cur.fetchone() is None:
            cur.execute(
                "INSERT INTO users (line_user_id, display_name, preferred_lang) VALUES (%s, %s, %s)",
                (user_id, display_name, "zh-TW")
            )
            
# Create the 7 default system categories for the given user if they do not exist.
def ensure_default_categories(user_id: str):
    user_uuid = get_user_uuid(user_id)
    if not user_uuid:
        return

    #base_names = ["food", "investment", "transport", "entertainment", "shopping", "medical", "others"]
    # todo 抽到config
    base_names = [
            "餐飲", "投資", "交通",
            "娛樂", "購物", "醫療", "其他"
        ]
    with conn.cursor() as cur:
        for name in base_names:
            # Check if category exists for this user
            cur.execute("""
                SELECT id, parent_id
                FROM categories
                WHERE user_id = %s AND name = %s
                LIMIT 1
            """, (user_uuid, name))
            row = cur.fetchone()

            if row:
                cat_id, parent_id = row[0], row[1]
                # Only ensure self-referencing parent_id when missing
                if parent_id is None:
                    cur.execute("""
                        UPDATE categories
                        SET parent_id = %s
                        WHERE id = %s
                    """, (cat_id, cat_id))
                continue

            # Insert new base category (mark system default on creation)
            cur.execute("""
                INSERT INTO categories (user_id, name, is_system_default)
                VALUES (%s, %s, TRUE)
                RETURNING id
            """, (user_uuid, name))
            new_id = cur.fetchone()[0]

            # Set parent_id to self
            cur.execute("""
                UPDATE categories
                SET parent_id = %s
                WHERE id = %s
            """, (new_id, new_id))

# Add or update a user-defined subcategory under a specified root category.
def add_user_category(user_id: str, keyword: str, category: str):
    """
    在指定的大類(category)底下，新增一個使用者自訂子類別(keyword)。
    若同一使用者已存在同名子類別(不分大小寫)則不新增。
    """
    ensure_user_exists(user_id)
    user_uuid = get_user_uuid(user_id)
    if not user_uuid:
        return

    keyword = (keyword or "").strip()
    category = (category or "").strip().lower()
    if not keyword or not category:
        return

    with conn.cursor() as cur:
        # 1) 找到 root category id（先找系統預設，再找使用者自訂的大類）
        cur.execute(
            """
            SELECT id
            FROM categories
            WHERE name = %s
              AND (is_system_default = TRUE OR user_id = %s)
            ORDER BY is_system_default DESC
            LIMIT 1
            """,
            (category, user_uuid)
        )
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Root category '{category}' not found")
        root_id = row[0]

        # 2) 檢查同 user 是否已有同名子類別（不分大小寫）
        cur.execute(
            """
            SELECT id
            FROM categories
            WHERE user_id = %s
              AND LOWER(name) = LOWER(%s)
            LIMIT 1
            """,
            (user_uuid, keyword)
        )
        exists = cur.fetchone()

        # 3) 沒有才插入
        if not exists:
            cur.execute(
                """
                INSERT INTO categories (user_id, name, parent_id, is_system_default, created_at)
                VALUES (%s, %s, %s, FALSE, NOW())
                """,
                (user_uuid, keyword, root_id)
            )

# Retrieve the internal UUID of the user from LINE user ID
def get_user_uuid(user_id):
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM users WHERE line_user_id = %s", (user_id,))
        result = cur.fetchone()
        return result[0] if result else None
    
# Retrieve the preferred language of the user
def get_user_language(user_id):
    with conn.cursor() as cur:
        cur.execute("SELECT preferred_lang FROM users WHERE line_user_id = %s", (user_id,))
        result = cur.fetchone()
        return result[0] if result else None
    
# Update the preferred language of the user
def set_user_language(user_id, lang_code):
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE users SET preferred_lang = %s WHERE line_user_id = %s",
            (lang_code, user_id)
        )

# Insert a new transaction (income or expense)
def insert_transactions(user_id, category_id, item, amount, message, display_name=None, record_type='expense'):
    ensure_user_exists(user_id, display_name)
    user_uuid = get_user_uuid(user_id)
    if user_uuid:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO transactions (user_id, category_id, item, amount, message, type, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (user_uuid, category_id, item, amount, message, record_type, datetime.now()))

# Retrieve the most recent transaction records
def get_last_records(user_id, limit=5):
    user_uuid = get_user_uuid(user_id)  # Convert LINE user ID to internal database ID
    if not user_uuid:
        return []
    with conn.cursor() as cur:
        cur.execute("""
             SELECT 
                COALESCE(c.name, '') AS category_name,
                t.item,
                t.amount,
                t.created_at            
            FROM transactions AS t
            LEFT JOIN categories AS c
              ON c.id = t.category_id
            WHERE t.user_id = %s
            ORDER BY t.created_at DESC
            LIMIT %s
        """, (user_uuid, limit))
        rows = cur.fetchall() or []
        return [
            {
                "category_name": row[0],
                "item": row[1],
                "amount": row[2],
                "created_at": row[3]
            }
            for row in rows
        ]

# Delete a specific transaction by index (latest = 1)
def delete_record(user_id, index):
    user_uuid = get_user_uuid(user_id)
    if not user_uuid:
        return False

    with conn.cursor() as cur:
        # Find the N-th latest transaction record
        cur.execute("""
            SELECT id FROM transactions 
            WHERE user_id = %s 
            ORDER BY created_at DESC 
            LIMIT 1 OFFSET %s
        """, (user_uuid, index - 1))  # Index starts from 1

        result = cur.fetchone()
        if not result:
            return False  # No record found

        expense_id = result[0]

        # Delete the specified record
        cur.execute("DELETE FROM transactions WHERE id = %s", (expense_id,))
        return True
    
def get_user_category_id(user_id, category_name):
    """Retrieve category ID for a user by category name."""
    user_uuid = get_user_uuid(user_id)
    if not user_uuid:
        return None

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id
            FROM categories
            WHERE user_id = %s
              AND LOWER(name) = LOWER(%s)
            LIMIT 1
            """,
            (user_uuid, category_name)
        )
        row = cur.fetchone()
        return row[0] if row else None


# Retrieve transactions within a specific time range or past N days
def get_user_transactions(user_id, start_time=None, end_time=None, days=None):
    user_uuid = get_user_uuid(user_id)
    if not user_uuid:
        return []
    
    query = """
        SELECT
            t.type,
            COALESCE(c.name, '') AS category,
            t.item,
            t.amount,
            t.created_at,
            t.message
        FROM transactions AS t
        LEFT JOIN categories AS c
          ON c.id = t.category_id
        WHERE t.user_id = %s
    """
    params = [user_uuid]

    # Prioritize the 'days' parameter if provided
    if days is not None:
        since = datetime.utcnow() - timedelta(days=days)
        query += " AND t.created_at >= %s"
        params.append(since)
    else:
        if start_time:
            query += " AND t.created_at >= %s"
            params.append(start_time)
        if end_time:
            query += " AND t.created_at <= %s"
            params.append(end_time)

    query += " ORDER BY t.created_at DESC"

    with conn.cursor() as cur:
        cur.execute(query, params)
        return [
            {
                'type': r[0],
                'category': r[1],
                'item': r[2],
                'amount': r[3],
                'date': r[4],
                'message': r[5]
            }
            for r in cur.fetchall()
        ]

# Search transaction messages containing the keyword
def find_transactions_by_keyword(user_id: str, keyword: str):
    """Search past records matching the keyword"""
    user_uuid = get_user_uuid(user_id)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, message FROM transactions
            WHERE user_id = %s AND message ILIKE %s
        """, (user_uuid, f"%{keyword}%"))
        return [{"id": row[0], "message": row[1]} for row in cur.fetchall()]

# Update the category of a specific transaction
def update_transaction_category(transaction_id: int, category: str):
    """Update category of a specific transaction"""
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE transactions
            SET category = %s
            WHERE id = %s
        """, (category, transaction_id))
