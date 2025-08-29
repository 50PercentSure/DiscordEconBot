import sqlite3
import config
from database import get_db_connection, get_user_data, update_user_data, record_stock_history
import random
import asyncio


class EconomySystem:
    def __init__(self):
        self.connection = get_db_connection

    def update_user_activity(self, user_id):
        """Update user stats when they send a message"""
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Get current user data
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            user = cursor.fetchone()

            if not user:
                # Create new user if doesn't exist
                cursor.execute(
                    'INSERT INTO users (user_id, username) VALUES (?, ?)',
                    (user_id, f"User_{user_id}")
                )
                conn.commit()
                return

            # Update message count and cash balance
            new_message_count = user['message_count'] + 1
            new_balance = user['cash_balance'] + config.ACTIVITY_REWARD

            # Calculate new stock value (base + incremental based on activity)
            new_stock_value = config.INITIAL_STOCK_VALUE + (new_message_count * config.VALUE_INCREASE)

            # Add some randomness to simulate market fluctuations
            fluctuation = random.uniform(-0.05, 0.1)
            new_stock_value *= (1 + fluctuation)

            # Ensure stock value doesn't go below a minimum
            new_stock_value = max(0.5, new_stock_value)

            # Update user record
            cursor.execute('''
                           UPDATE users
                           SET message_count = ?,
                               cash_balance  = ?,
                               stock_value   = ?
                           WHERE user_id = ?
                           ''', (new_message_count, new_balance, new_stock_value, user_id))

            # Record history
            record_stock_history(user_id, new_stock_value, new_message_count)

            conn.commit()

    def get_stock_price(self, user_id):
        """Get current stock price for a user"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT stock_value FROM users WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            return result['stock_value'] if result else config.INITIAL_STOCK_VALUE

    def buy_stocks(self, investor_id, subject_id, amount):
        """Buy stocks of another user"""
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Get investor balance
            cursor.execute('SELECT cash_balance FROM users WHERE user_id = ?', (investor_id,))
            investor = cursor.fetchone()
            if not investor:
                return False, "Investor not found"

            # Get subject stock price
            stock_price = self.get_stock_price(subject_id)
            total_cost = stock_price * amount

            # Check if investor has enough funds
            if investor['cash_balance'] < total_cost:
                return False, "Insufficient funds"

            # Check if investment already exists
            cursor.execute('''
                           SELECT *
                           FROM investments
                           WHERE investor_id = ?
                             AND subject_id = ?
                           ''', (investor_id, subject_id))
            existing_investment = cursor.fetchone()

            if existing_investment:
                # Update existing investment
                new_shares = existing_investment['shares_owned'] + amount
                cursor.execute('''
                               UPDATE investments
                               SET shares_owned   = ?,
                                   purchase_price = ?
                               WHERE investor_id = ?
                                 AND subject_id = ?
                               ''', (new_shares, stock_price, investor_id, subject_id))
            else:
                # Create new investment
                cursor.execute('''
                               INSERT INTO investments (investor_id, subject_id, shares_owned, purchase_price)
                               VALUES (?, ?, ?, ?)
                               ''', (investor_id, subject_id, amount, stock_price))

            # Deduct cost from investor's balance
            cursor.execute('''
                           UPDATE users
                           SET cash_balance = cash_balance - ?
                           WHERE user_id = ?
                           ''', (total_cost, investor_id))

            # Record transaction
            cursor.execute('''
                           INSERT INTO transactions (user_id, type, amount, details)
                           VALUES (?, 'buy', ?, ?)
                           ''',
                           (investor_id, total_cost, f"Bought {amount} shares of {subject_id} at ${stock_price:.2f}"))

            conn.commit()
            return True, f"Successfully bought {amount} shares at ${stock_price:.2f} each"

    def sell_stocks(self, investor_id, subject_id, amount):
        """Sell stocks of another user"""
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Check if investment exists
            cursor.execute('''
                           SELECT *
                           FROM investments
                           WHERE investor_id = ?
                             AND subject_id = ?
                           ''', (investor_id, subject_id))
            investment = cursor.fetchone()

            if not investment or investment['shares_owned'] < amount:
                return False, "Not enough shares to sell"

            # Get current stock price
            stock_price = self.get_stock_price(subject_id)
            total_value = stock_price * amount

            # Update investment
            new_shares = investment['shares_owned'] - amount
            if new_shares <= 0:
                # Remove investment if no shares left
                cursor.execute('''
                               DELETE
                               FROM investments
                               WHERE investor_id = ?
                                 AND subject_id = ?
                               ''', (investor_id, subject_id))
            else:
                # Update shares count
                cursor.execute('''
                               UPDATE investments
                               SET shares_owned = ?
                               WHERE investor_id = ?
                                 AND subject_id = ?
                               ''', (new_shares, investor_id, subject_id))

            # Add proceeds to investor's balance
            cursor.execute('''
                           UPDATE users
                           SET cash_balance = cash_balance + ?
                           WHERE user_id = ?
                           ''', (total_value, investor_id))

            # Record transaction
            cursor.execute('''
                           INSERT INTO transactions (user_id, type, amount, details)
                           VALUES (?, 'sell', ?, ?)
                           ''',
                           (investor_id, total_value, f"Sold {amount} shares of {subject_id} at ${stock_price:.2f}"))

            conn.commit()

            # Calculate profit/loss
            purchase_value = investment['purchase_price'] * amount
            profit_loss = total_value - purchase_value
            profit_loss_percent = (profit_loss / purchase_value) * 100 if purchase_value > 0 else 0

            return True, f"Sold {amount} shares for ${total_value:.2f} " \
                         f"(P/L: ${profit_loss:+.2f}, {profit_loss_percent:+.2f}%)"

    def get_portfolio(self, investor_id):
        """Get user's investment portfolio"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                           SELECT i.subject_id, i.shares_owned, i.purchase_price, u.stock_value as current_price
                           FROM investments i
                                    JOIN users u ON i.subject_id = u.user_id
                           WHERE i.investor_id = ?
                           ''', (investor_id,))

            investments = cursor.fetchall()
            portfolio = []
            total_value = 0
            total_invested = 0

            for investment in investments:
                current_value = investment['shares_owned'] * investment['current_price']
                invested_value = investment['shares_owned'] * investment['purchase_price']
                profit_loss = current_value - invested_value
                profit_loss_percent = (profit_loss / invested_value) * 100 if invested_value > 0 else 0

                portfolio.append({
                    'subject_id': investment['subject_id'],
                    'shares': investment['shares_owned'],
                    'purchase_price': investment['purchase_price'],
                    'current_price': investment['current_price'],
                    'current_value': current_value,
                    'profit_loss': profit_loss,
                    'profit_loss_percent': profit_loss_percent
                })

                total_value += current_value
                total_invested += invested_value

            # Get user's cash balance
            cursor.execute('SELECT cash_balance FROM users WHERE user_id = ?', (investor_id,))
            cash_balance = cursor.fetchone()['cash_balance']

            return {
                'investments': portfolio,
                'cash_balance': cash_balance,
                'total_investment_value': total_value,
                'total_portfolio_value': cash_balance + total_value,
                'total_invested': total_invested,
                'total_profit_loss': total_value - total_invested,
                'total_profit_loss_percent': (
                            (total_value - total_invested) / total_invested * 100) if total_invested > 0 else 0
            }