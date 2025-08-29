import sqlite3
import config
from contextlib import contextmanager
from datetime import datetime


@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Initialize database with required tables"""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Users table
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS users
                       (
                           user_id
                           INTEGER
                           PRIMARY
                           KEY,
                           username
                           TEXT,
                           cash_balance
                           REAL
                           DEFAULT
                           ?,
                           message_count
                           INTEGER
                           DEFAULT
                           0,
                           stock_value
                           REAL
                           DEFAULT
                           ?,
                           created_at
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP
                       )
                       ''', (config.INITIAL_BALANCE, config.INITIAL_STOCK_VALUE))

        # Investments table
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS investments
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           investor_id
                           INTEGER,
                           subject_id
                           INTEGER,
                           shares_owned
                           REAL
                           DEFAULT
                           0,
                           purchase_price
                           REAL,
                           invested_at
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP,
                           FOREIGN
                           KEY
                       (
                           investor_id
                       ) REFERENCES users
                       (
                           user_id
                       ),
                           FOREIGN KEY
                       (
                           subject_id
                       ) REFERENCES users
                       (
                           user_id
                       )
                           )
                       ''')

        # Transactions history table
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS transactions
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           user_id
                           INTEGER,
                           type
                           TEXT, -- 'buy', 'sell', 'dividend', etc.
                           amount
                           REAL,
                           details
                           TEXT,
                           created_at
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP,
                           FOREIGN
                           KEY
                       (
                           user_id
                       ) REFERENCES users
                       (
                           user_id
                       )
                           )
                       ''')

        # Stock history table for tracking value over time
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS stock_history
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           user_id
                           INTEGER,
                           stock_value
                           REAL,
                           message_count
                           INTEGER,
                           recorded_at
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP,
                           FOREIGN
                           KEY
                       (
                           user_id
                       ) REFERENCES users
                       (
                           user_id
                       )
                           )
                       ''')

        # Create index for faster historical queries
        cursor.execute('CREATE INDEX IF NOT EXISTS history_user_index ON stock_history(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS history_time_index ON stock_history(recorded_at)')

        conn.commit()


def record_stock_history(user_id, stock_value, message_count):
    """Record a snapshot of user's stock value and message count"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
                       INSERT INTO stock_history (user_id, stock_value, message_count)
                       VALUES (?, ?, ?)
                       ''', (user_id, stock_value, message_count))
        conn.commit()


def get_user_data(user_id):
    """Get user data from database"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return cursor.fetchone()


def update_user_data(user_id, **kwargs):
    """Update user data in database"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        set_clause = ', '.join([f"{key} = ?" for key in kwargs.keys()])
        values = list(kwargs.values())
        values.append(user_id)
        cursor.execute(f'UPDATE users SET {set_clause} WHERE user_id = ?', values)
        conn.commit()


def get_stock_history(user_id, days=7):
    """Get stock history for a user over a specified number of days"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
                       SELECT stock_value, recorded_at
                       FROM stock_history
                       WHERE user_id = ?
                         AND recorded_at >= datetime('now', ?)
                       ORDER BY recorded_at
                       ''', (user_id, f'-{days} days'))
        return cursor.fetchall()