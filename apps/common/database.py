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
            cur.execute("INSERT INTO users (line_user_id, display_name) VALUES (%s, %s)", (user_id, display_name))

# Retrieve the internal UUID of the user from LINE user ID
def get_user_uuid(user_id):
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM users WHERE line_user_id = %s", (user_id,))
        result = cur.fetchone()
        return result[0] if result else None

# Insert a new transaction (income or expense)
def insert_transactions(user_id, category, amount, message, display_name=None, record_type='expense'):
    ensure_user_exists(user_id, display_name)
    user_uuid = get_user_uuid(user_id)
    if user_uuid:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO transactions (user_id, category, amount, message, type, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (user_uuid, category, amount, message or category, record_type, datetime.now()))

# Retrieve the most recent transaction records
def get_last_records(user_id, limit=5):
    user_uuid = get_user_uuid(user_id)  # Convert LINE user ID to internal database ID
    if not user_uuid:
        return []
    with conn.cursor() as cur:
        cur.execute("""
            SELECT category, amount, created_at 
            FROM transactions 
            WHERE user_id = %s 
            ORDER BY created_at DESC 
            LIMIT %s
        """, (user_uuid, limit))
        rows = cur.fetchall()
        return [
            {"category": row[0], "amount": row[1], "created_at": row[2]}
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

# Retrieve transactions within a specific time range or past N days
def get_user_transactions(user_id, start_time=None, end_time=None, days=None):
    user_uuid = get_user_uuid(user_id)
    if not user_uuid:
        return []

    query = "SELECT type, category, amount, created_at, message FROM transactions WHERE user_id = %s"
    params = [user_uuid]

    # Prioritize the 'days' parameter if provided
    if days is not None:
        since = datetime.utcnow() - timedelta(days=days)
        query += " AND created_at >= %s"
        params.append(since)
    else:
        if start_time:
            query += " AND created_at >= %s"
            params.append(start_time)
        if end_time:
            query += " AND created_at <= %s"
            params.append(end_time)

    query += " ORDER BY created_at DESC"

    with conn.cursor() as cur:
        cur.execute(query, params)
        return [
            {
                'type': r[0],
                'category': r[1],
                'amount': r[2],
                'date': r[3],
                'message': r[4]
            }
            for r in cur.fetchall()
        ]

# Add or update a keyword-category mapping for the user
def add_user_category(user_id: str, keyword: str, category: str):
    user_uuid = get_user_uuid(user_id)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO categories (user_id, keywords, category)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id, keywords)
            DO UPDATE SET category = EXCLUDED.category
            """,
            (user_uuid, keyword.lower(), category)
        )

# Retrieve all keyword-category mappings for the user
def get_user_categories(user_id: str) -> dict:
    user_uuid = get_user_uuid(user_id)
    with conn.cursor(dictionary=True) as cur:
        cur.execute("SELECT keyword, category FROM categories WHERE user_id = %s", (user_uuid,))
        return {row['keyword']: row['category'] for row in cur.fetchall()}

# Delete a specific keyword-category mapping
def delete_user_category(user_id: str, keyword: str):
    user_uuid = get_user_uuid(user_id)
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM categories WHERE user_id = %s AND keywords = %s",
            (user_uuid, keyword.lower())
        )

# Check if a keyword-category mapping exists
def category_exists(user_id: str, keyword: str) -> bool:
    user_uuid = get_user_uuid(user_id)
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM categories WHERE user_id = %s AND keywords = %s LIMIT 1", (user_uuid, keyword.lower()))
        return cur.fetchone() is not None

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
