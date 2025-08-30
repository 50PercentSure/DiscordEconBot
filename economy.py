import random
import time
import threading
import math
from datetime import datetime, timedelta
from data_handler import JSONDataHandler

class EconomySystem:
    def __init__(self):
        self.data_handler = JSONDataHandler()
        self.users_cache = {}
        self.pending_history = []
        self.cache_lock = threading.RLock()
        self.last_sync_time = 0
        self.price_history = {}
        self.spam_tracker = {}
        self.companies_cache = {}
        self.last_salary_payment = time.time()
        
        # Load initial data
        self.load_from_storage()
    
    def _load_price_history(self):
        """Load and process price history for trend analysis"""
        history = self.data_handler.get_all_history()
        self.price_history = {}
        
        for record in history:
            user_id = record.get('user_id')
            if user_id not in self.price_history:
                self.price_history[user_id] = []
            
            # Convert timestamp to datetime if it's a string
            timestamp = record.get('recorded_at')
            if isinstance(timestamp, str):
                try:
                    timestamp = datetime.fromisoformat(timestamp).timestamp()
                except ValueError:
                    timestamp = time.time()
            
            self.price_history[user_id].append({
                'timestamp': timestamp,
                'price': record.get('stock_value', 10.0),
                'message_count': record.get('message_count', 0)
            })
        
        # Sort all history by timestamp
        for user_id in self.price_history:
            self.price_history[user_id].sort(key=lambda x: x['timestamp'])
    
    def load_from_storage(self):
        """Load all user data from storage into cache"""
        with self.cache_lock:
            users_data = self.data_handler.get_all_users()
            self.users_cache = {int(user_id): user_data for user_id, user_data in users_data.items()}
            self.last_sync_time = time.time()
            
            # Load spam tracking data
            spam_data = self.data_handler.get_spam_data()
            self.spam_tracker = {int(user_id): data for user_id, data in spam_data.items()}
            
            # Load companies data
            companies_data = self.data_handler.get_all_companies()
            self.companies_cache = {int(company_id): company_data for company_id, company_data in companies_data.items()}
            
            # Initialize price history
            self._load_price_history()
    
    def sync_to_storage(self):
        """Synchronize cache to storage"""
        with self.cache_lock:
            if not self.users_cache:
                return
                
            # Update users in storage
            users_to_update = {}
            current_time = time.time()
            
            for user_id, user_data in self.users_cache.items():
                if user_data.get('last_updated', 0) > self.last_sync_time:
                    users_to_update[str(user_id)] = user_data
            
            if users_to_update:
                all_users = self.data_handler.get_all_users()
                all_users.update(users_to_update)
                self.data_handler.save_all_users(all_users)
            
            # Record history if needed
            if self.pending_history:
                for history_record in self.pending_history:
                    self.data_handler.save_history(history_record)
                self.pending_history = []
            
            # Update companies if needed
            if self.companies_cache:
                self.data_handler.save_all_companies(self.companies_cache)
            
            # Process salary payments
            if current_time - self.last_salary_payment >= 86400:  # Using constant instead of config
                self.process_salary_payments()
                self.last_salary_payment = current_time
            
            self.last_sync_time = current_time
    
    def process_salary_payments(self):
        """Process salary payments for all employees"""
        employees = self.data_handler.get_all_employees()
        
        for user_id_str, employee_data in employees.items():
            user_id = int(user_id_str)
            company_id = employee_data.get('company_id')
            
            if company_id and company_id in self.companies_cache:
                company = self.companies_cache[company_id]
                salary = employee_data.get('salary', 0)
                
                # Check if company has enough funds
                if company.get('funds', 0) >= salary:
                    # Pay employee
                    if user_id in self.users_cache:
                        self.users_cache[user_id]['cash_balance'] += salary
                        self.users_cache[user_id]['last_updated'] = time.time()
                    
                    # Deduct from company funds
                    company['funds'] -= salary
                    
                    # Record transaction
                    self.data_handler.save_transaction({
                        'user_id': user_id,
                        'type': 'salary',
                        'amount': salary,
                        'details': f"Salary from {company.get('name', 'Unknown Company')}"
                    })
    
    def is_spamming(self, user_id, message_content):
        """Check if a user is spamming messages"""
        current_time = time.time()
        
        # Initialize spam tracking for new users
        if user_id not in self.spam_tracker:
            self.spam_tracker[user_id] = {
                'message_times': [],
                'last_penalty': 0,
                'spam_count': 0
            }
        
        user_tracker = self.spam_tracker[user_id]
        
        # Check message length
        if len(message_content.strip()) < 5:  # Using constant instead of config
            return True, "Message too short"
        
        # Check message cooldown
        if user_tracker['message_times']:
            last_message_time = user_tracker['message_times'][-1]
            if current_time - last_message_time < 15:  # Using constant instead of config
                return True, "Message cooldown"
        
        # Update message tracking
        user_tracker['message_times'].append(current_time)
        
        # Keep only the last N messages (sliding window)
        window_size = 10  # Using constant instead of config
        if len(user_tracker['message_times']) > window_size:
            user_tracker['message_times'] = user_tracker['message_times'][-window_size:]
        
        # Check if user is spamming (too many messages in short time)
        if len(user_tracker['message_times']) >= window_size:
            time_span = user_tracker['message_times'][-1] - user_tracker['message_times'][0]
            if time_span < 60:  # 10 messages in less than 60 seconds is spamming
                user_tracker['spam_count'] += 1
                user_tracker['last_penalty'] = current_time
                return True, "Spam detected"
        
        # Save updated spam data
        self.data_handler.update_user_spam_data(user_id, user_tracker)
        
        return False, "OK"
    
    def calculate_spam_penalty(self, user_id):
        """Calculate penalty factor for spamming users"""
        if user_id not in self.spam_tracker:
            return 1.0  # No penalty
        
        user_tracker = self.spam_tracker[user_id]
        current_time = time.time()
        
        # Reduce penalty over time (1 hour half-life)
        time_since_penalty = current_time - user_tracker.get('last_penalty', 0)
        if time_since_penalty > 0:
            decay_factor = math.exp(-time_since_penalty / 3600)  # 1 hour half-life
        else:
            decay_factor = 1.0
        
        # Base penalty based on spam count
        spam_count = user_tracker.get('spam_count', 0)
        base_penalty = max(0.1, 1.0 - (spam_count * 0.1))  # Minimum 10% effectiveness
        
        return max(0.1, base_penalty * decay_factor)  # Ensure at least 10% effectiveness
    
    def calculate_smoothed_price(self, user_data, new_base_value):
        """Calculate smoothed price with reduced volatility"""
        current_price = user_data['stock_value']
        smoothing_factor = 0.7
        
        # Apply exponential smoothing
        smoothed_price = (smoothing_factor * current_price) + ((1 - smoothing_factor) * new_base_value)
        
        # Add controlled volatility
        volatility = 0.03
        fluctuation = random.uniform(-volatility, volatility)
        final_price = smoothed_price * (1 + fluctuation)
        
        # Ensure minimum price
        return max(0.5, final_price)
    
    def calculate_trend(self, user_id, days=7):
        """Calculate price trend for a user"""
        if user_id not in self.price_history or not self.price_history[user_id]:
            return 0
        
        cutoff = time.time() - (days * 24 * 3600)
        recent_history = [point for point in self.price_history[user_id] 
                         if point['timestamp'] >= cutoff]
        
        if len(recent_history) < 2:
            return 0
        
        first_price = recent_history[0]['price']
        last_price = recent_history[-1]['price']
        
        if first_price == 0:
            return 0
        
        trend_percent = ((last_price - first_price) / first_price) * 100
        
        recent_messages = recent_history[-1]['message_count'] - recent_history[0]['message_count']
        message_momentum = min(1.0, recent_messages / 100)
        
        adjusted_trend = trend_percent + (message_momentum * 1.0)
        
        return adjusted_trend
    
    def predict_future_price(self, user_id, days_ahead=1):
        """Predict future price based on trend"""
        trend = self.calculate_trend(user_id)
        current_price = self.get_stock_price(user_id)
        
        daily_trend = trend / 7
        predicted_change = (daily_trend / 100) * current_price * days_ahead
        
        return current_price + predicted_change
    
    def apply_buy_pressure(self, user_id, shares_bought):
        """Increase stock price when shares are bought"""
        buy_pressure = 0.002
        price_increase = self.get_stock_price(user_id) * buy_pressure * shares_bought
        
        with self.cache_lock:
            if user_id in self.users_cache:
                self.users_cache[user_id]['stock_value'] += price_increase
                self.users_cache[user_id]['last_updated'] = time.time()
        
        return price_increase
    
    def update_user_activity(self, user_id, message_content):
        """Update user stats with anti-spam checks"""
        # Check for spam
        is_spam, reason = self.is_spamming(user_id, message_content)
        spam_penalty = self.calculate_spam_penalty(user_id)
        
        with self.cache_lock:
            current_time = time.time()
            
            # Get or create user in cache
            if user_id not in self.users_cache:
                self.users_cache[user_id] = {
                    'user_id': user_id,
                    'username': f"User_{user_id}",
                    'cash_balance': 1000,
                    'message_count': 0,
                    'stock_value': 10.0,
                    'last_updated': current_time,
                    'spam_penalty': 1.0
                }
            
            user_data = self.users_cache[user_id]
            
            # Update spam penalty
            user_data['spam_penalty'] = spam_penalty
            
            # Only update if not spamming
            if not is_spam:
                # Update message count and cash balance (with penalty)
                user_data['message_count'] += 1
                user_data['cash_balance'] += 0.1 * spam_penalty
                
                # Calculate new base value (with penalty)
                new_base_value = 10.0 + (user_data['message_count'] * 0.01 * spam_penalty)
                
                # Apply smoothing and controlled volatility
                new_stock_value = self.calculate_smoothed_price(user_data, new_base_value)
                
                user_data['stock_value'] = new_stock_value
                user_data['last_updated'] = current_time
                
                # Add to pending history
                self.pending_history.append({
                    'user_id': user_id,
                    'stock_value': new_stock_value,
                    'message_count': user_data['message_count'],
                    'spam_penalty': spam_penalty
                })
                
                # Update price history
                if user_id not in self.price_history:
                    self.price_history[user_id] = []
                
                self.price_history[user_id].append({
                    'timestamp': current_time,
                    'price': new_stock_value,
                    'message_count': user_data['message_count']
                })
            else:
                # Still update last_updated but don't increase value
                user_data['last_updated'] = current_time
                
                # Log spam event
                if is_spam and reason != "Message cooldown":
                    print(f"Spam detected for user {user_id}: {reason}")
    
    def get_stock_price(self, user_id):
        """Get current stock price from cache"""
        with self.cache_lock:
            if user_id in self.users_cache:
                return self.users_cache[user_id]['stock_value']
            return 10.0
    
    def get_user_data(self, user_id):
        """Get user data from cache"""
        with self.cache_lock:
            if user_id in self.users_cache:
                return self.users_cache[user_id].copy()
            return None
    
    def buy_stocks(self, investor_id, subject_id, amount):
        """Buy stocks of another user"""
        # Get investor data
        investor_data = self.get_user_data(investor_id)
        if not investor_data:
            return False, "Investor not found"
            
        # Get subject stock price
        stock_price = self.get_stock_price(subject_id)
        total_cost = stock_price * amount
        
        # Check if investor has enough funds
        if investor_data['cash_balance'] < total_cost:
            return False, "Insufficient funds"
        
        # Update investor's balance
        with self.cache_lock:
            self.users_cache[investor_id]['cash_balance'] -= total_cost
            self.users_cache[investor_id]['last_updated'] = time.time()
        
        # Check if investment already exists
        investments = self.data_handler.get_all_investments()
        existing_investment = None
        
        for investment in investments:
            if (investment.get('investor_id') == investor_id and 
                investment.get('subject_id') == subject_id):
                existing_investment = investment
                break
        
        if existing_investment:
            # Update existing investment
            new_shares = existing_investment['shares_owned'] + amount
            self.data_handler.update_investment(
                existing_investment['id'],
                {'shares_owned': new_shares, 'purchase_price': stock_price}
            )
        else:
            # Create new investment
            self.data_handler.save_investment({
                'investor_id': investor_id,
                'subject_id': subject_id,
                'shares_owned': amount,
                'purchase_price': stock_price,
                'invested_at': time.time()
            })
        
        # Record transaction
        self.data_handler.save_transaction({
            'user_id': investor_id,
            'type': 'buy',
            'amount': total_cost,
            'details': f"Bought {amount} shares of {subject_id} at ${stock_price:.2f}"
        })
        
        return True, f"Successfully bought {amount} shares at ${stock_price:.2f} each"
    
    def sell_stocks(self, investor_id, subject_id, amount):
        """Sell stocks of another user"""
        # Check if investment exists
        investments = self.data_handler.get_all_investments()
        investment = None
        
        for inv in investments:
            if (inv.get('investor_id') == investor_id and 
                inv.get('subject_id') == subject_id):
                investment = inv
                break
        
        if not investment or investment['shares_owned'] < amount:
            return False, "Not enough shares to sell"
            
        # Get current stock price
        stock_price = self.get_stock_price(subject_id)
        total_value = stock_price * amount
        
        # Update investment
        new_shares = investment['shares_owned'] - amount
        if new_shares <= 0:
            self.data_handler.remove_investment(investment['id'])
        else:
            self.data_handler.update_investment(
                investment['id'],
                {'shares_owned': new_shares}
            )
        
        # Update investor's balance
        with self.cache_lock:
            if investor_id in self.users_cache:
                self.users_cache[investor_id]['cash_balance'] += total_value
                self.users_cache[investor_id]['last_updated'] = time.time()
        
        # Record transaction
        self.data_handler.save_transaction({
            'user_id': investor_id,
            'type': 'sell',
            'amount': total_value,
            'details': f"Sold {amount} shares of {subject_id} at ${stock_price:.2f}"
        })
        
        # Calculate profit/loss
        purchase_value = investment['purchase_price'] * amount
        profit_loss = total_value - purchase_value
        profit_loss_percent = (profit_loss / purchase_value) * 100 if purchase_value > 0 else 0
        
        return True, f"Sold {amount} shares for ${total_value:.2f} " \
                     f"(P/L: ${profit_loss:+.2f}, {profit_loss_percent:+.2f}%)"
    
    def get_portfolio(self, investor_id):
        """Get user's investment portfolio"""
        investments = self.data_handler.get_all_investments()
        user_investments = [inv for inv in investments if inv.get('investor_id') == investor_id]
        
        portfolio = []
        total_value = 0
        total_invested = 0
        
        for investment in user_investments:
            subject_id = investment['subject_id']
            current_price = self.get_stock_price(subject_id)
            shares = investment['shares_owned']
            purchase_price = investment['purchase_price']
            
            current_val = current_price * shares
            invested_val = purchase_price * shares
            profit_loss = current_val - invested_val
            profit_loss_percent = (profit_loss / invested_val) * 100 if invested_val > 0 else 0
            
            portfolio.append({
                'subject_id': subject_id,
                'shares': shares,
                'purchase_price': purchase_price,
                'current_price': current_price,
                'current_value': current_val,
                'profit_loss': profit_loss,
                'profit_loss_percent': profit_loss_percent
            })
            
            total_value += current_val
            total_invested += invested_val
        
        # Get user's cash balance
        user_data = self.get_user_data(investor_id)
        cash_balance = user_data['cash_balance'] if user_data else 0
        
        return {
            'investments': portfolio,
            'cash_balance': cash_balance,
            'total_investment_value': total_value,
            'total_portfolio_value': cash_balance + total_value,
            'total_invested': total_invested,
            'total_profit_loss': total_value - total_invested,
            'total_profit_loss_percent': ((total_value - total_invested) / total_invested * 100) if total_invested > 0 else 0
        }
    
    def create_company(self, user_id, name, description, initial_funds):
        """Create a new company"""
        with self.cache_lock:
            # Check if user has enough funds
            if user_id not in self.users_cache or self.users_cache[user_id]['cash_balance'] < initial_funds:
                return False, "Insufficient funds"
            
            # Check if user is already in a company
            employee_data = self.data_handler.get_employee(user_id)
            if employee_data and employee_data.get('company_id'):
                return False, "You are already part of a company"
            
            # Create company
            company_id = max([c_id for c_id in self.companies_cache.keys()] + [0]) + 1
            company_data = {
                'id': company_id,
                'name': name,
                'description': description,
                'funds': initial_funds,
                'ceo_id': user_id,
                'founded_at': time.time(),
                'employees': [],
                'stock_value': 100.0  # Initial company value
            }
            
            # Add to cache
            self.companies_cache[company_id] = company_data
            
            # Deduct funds from user
            self.users_cache[user_id]['cash_balance'] -= initial_funds
            
            # Create employee record for CEO
            employee_data = {
                'user_id': user_id,
                'company_id': company_id,
                'role': 'CEO',
                'salary': 0,  # CEO doesn't take a salary initially
                'joined_at': time.time()
            }
            self.data_handler.save_employee(employee_data)
            
            # Add to company employees list
            company_data['employees'].append({
                'user_id': user_id,
                'role': 'CEO',
                'salary': 0
            })
            
            # Record transaction
            self.data_handler.save_transaction({
                'user_id': user_id,
                'type': 'company_creation',
                'amount': initial_funds,
                'details': f"Created company: {name}"
            })
            
            return True, f"Successfully created company '{name}' with ${initial_funds:,.2f} initial funds"
    
    def hire_employee(self, company_id, hirer_id, user_id, role, salary):
        """Hire an employee to a company"""
        with self.cache_lock:
            # Check if company exists
            if company_id not in self.companies_cache:
                return False, "Company not found"
            
            company = self.companies_cache[company_id]
            
            # Check if hirer has permission
            hirer_employee = self.data_handler.get_employee(hirer_id)
            if not hirer_employee or hirer_employee.get('company_id') != company_id:
                return False, "You are not part of this company"
            
            hirer_role = hirer_employee.get('role', '')
            if hirer_role not in ['CEO', 'Upper Management']:
                return False, "You don't have permission to hire employees"
            
            # Check if user is already employed
            existing_employee = self.data_handler.get_employee(user_id)
            if existing_employee and existing_employee.get('company_id'):
                return False, "This user is already employed"
            
            # Check if company has enough funds for salary
            if company.get('funds', 0) < salary:
                return False, "Company doesn't have enough funds for this salary"
            
            # Create employee record
            employee_data = {
                'user_id': user_id,
                'company_id': company_id,
                'role': role,
                'salary': salary,
                'joined_at': time.time()
            }
            self.data_handler.save_employee(employee_data)
            
            # Add to company employees list
            company['employees'].append({
                'user_id': user_id,
                'role': role,
                'salary': salary
            })
            
            # Update user cache if user is online
            if user_id in self.users_cache:
                user_data = self.users_cache[user_id]
                if 'companies' not in user_data:
                    user_data['companies'] = []
                user_data['companies'].append({
                    'id': company_id,
                    'name': company.get('name', 'Unknown Company'),
                    'role': role
                })
            
            return True, f"Successfully hired user as {role} with ${salary:,.2f} salary"
    
    def fire_employee(self, company_id, firer_id, user_id):
        """Fire an employee from a company"""
        with self.cache_lock:
            # Check if company exists
            if company_id not in self.companies_cache:
                return False, "Company not found"
            
            company = self.companies_cache[company_id]
            
            # Check if firer has permission
            firer_employee = self.data_handler.get_employee(firer_id)
            if not firer_employee or firer_employee.get('company_id') != company_id:
                return False, "You are not part of this company"
            
            firer_role = firer_employee.get('role', '')
            if firer_role not in ['CEO', 'Upper Management']:
                return False, "You don't have permission to fire employees"
            
            # Check if user is employed by the company
            employee_data = self.data_handler.get_employee(user_id)
            if not employee_data or employee_data.get('company_id') != company_id:
                return False, "This user is not employed by this company"
            
            # Cannot fire yourself if you're CEO
            if user_id == firer_id and firer_role == 'CEO':
                return False, "CEOs cannot fire themselves"
            
            # Remove employee record
            self.data_handler.remove_employee(user_id)
            
            # Remove from company employees list
            company['employees'] = [emp for emp in company['employees'] if emp.get('user_id') != user_id]
            
            # Update user cache if user is online
            if user_id in self.users_cache:
                user_data = self.users_cache[user_id]
                if 'companies' in user_data:
                    user_data['companies'] = [comp for comp in user_data['companies'] if comp.get('id') != company_id]
            
            return True, "Successfully fired employee"
    
    def create_task(self, company_id, creator_id, title, description, assignee_id, reward):
        """Create a task for an employee"""
        with self.cache_lock:
            # Check if company exists
            if company_id not in self.companies_cache:
                return False, "Company not found"
            
            company = self.companies_cache[company_id]
            
            # Check if creator has permission
            creator_employee = self.data_handler.get_employee(creator_id)
            if not creator_employee or creator_employee.get('company_id') != company_id:
                return False, "You are not part of this company"
            
            creator_role = creator_employee.get('role', '')
            if creator_role not in ['CEO', 'Upper Management', 'Management']:
                return False, "You don't have permission to create tasks"
            
            # Check if assignee is part of the company
            assignee_employee = self.data_handler.get_employee(assignee_id)
            if not assignee_employee or assignee_employee.get('company_id') != company_id:
                return False, "Assignee is not part of this company"
            
            # Check if company has enough funds for reward
            if company.get('funds', 0) < reward:
                return False, "Company doesn't have enough funds for this task reward"
            
            # Create task
            task_data = {
                'title': title,
                'description': description,
                'assignee_id': assignee_id,
                'creator_id': creator_id,
                'reward': reward,
                'status': 'assigned',
                'created_at': time.time()
            }
            
            self.data_handler.add_company_task(company_id, task_data)
            
            return True, f"Task '{title}' created with ${reward:,.2f} reward"
    
    def complete_task(self, company_id, user_id, task_id):
        """Complete a task and receive reward"""
        with self.cache_lock:
            # Check if company exists
            if company_id not in self.companies_cache:
                return False, "Company not found"
            
            company = self.companies_cache[company_id]
            
            # Check if user is part of the company
            employee_data = self.data_handler.get_employee(user_id)
            if not employee_data or employee_data.get('company_id') != company_id:
                return False, "You are not part of this company"
            
            # Get task
            tasks = self.data_handler.get_company_tasks(company_id)
            task = next((t for t in tasks if t.get('id') == task_id), None)
            
            if not task:
                return False, "Task not found"
            
            if task.get('assignee_id') != user_id:
                return False, "This task is not assigned to you"
            
            if task.get('status') != 'assigned':
                return False, "This task is not in progress"
            
            # Check if company has enough funds for reward
            reward = task.get('reward', 0)
            if company.get('funds', 0) < reward:
                return False, "Company doesn't have enough funds to pay the reward"
            
            # Update task status
            task['status'] = 'completed'
            task['completed_at'] = time.time()
            self.data_handler.update_company_task(company_id, task_id, task)
            
            # Pay reward to employee
            if user_id in self.users_cache:
                self.users_cache[user_id]['cash_balance'] += reward
                self.users_cache[user_id]['last_updated'] = time.time()
            
            # Deduct from company funds
            company['funds'] -= reward
            
            # Record transaction
            self.data_handler.save_transaction({
                'user_id': user_id,
                'type': 'task_reward',
                'amount': reward,
                'details': f"Completed task: {task.get('title', 'Unknown Task')}"
            })
            
            return True, f"Task completed! You received ${reward:,.2f}"
    
    def create_deal(self, company_id, creator_id, target_company_id, description, amount):
        """Create a deal between companies"""
        with self.cache_lock:
            # Check if both companies exist
            if company_id not in self.companies_cache:
                return False, "Your company not found"
            
            if target_company_id not in self.companies_cache:
                return False, "Target company not found"
            
            company = self.companies_cache[company_id]
            target_company = self.companies_cache[target_company_id]
            
            # Check if creator has permission
            creator_employee = self.data_handler.get_employee(creator_id)
            if not creator_employee or creator_employee.get('company_id') != company_id:
                return False, "You are not part of this company"
            
            creator_role = creator_employee.get('role', '')
            if creator_role not in ['CEO', 'Upper Management']:
                return False, "You don't have permission to create deals"
            
            # Check if company has enough funds for deal
            if company.get('funds', 0) < amount:
                return False, "Your company doesn't have enough funds for this deal"
            
            # Create deal
            deal_data = {
                'from_company_id': company_id,
                'to_company_id': target_company_id,
                'description': description,
                'amount': amount,
                'status': 'proposed',
                'created_at': time.time()
            }
            
            self.data_handler.add_company_deal(company_id, deal_data)
            self.data_handler.add_company_deal(target_company_id, {
                **deal_data,
                'status': 'pending'
            })
            
            return True, f"Deal proposed to {target_company.get('name', 'Unknown Company')} for ${amount:,.2f}"
    
    def accept_deal(self, company_id, user_id, deal_id):
        """Accept a proposed deal"""
        with self.cache_lock:
            # Check if company exists
            if company_id not in self.companies_cache:
                return False, "Company not found"
            
            company = self.companies_cache[company_id]
            
            # Check if user has permission
            employee_data = self.data_handler.get_employee(user_id)
            if not employee_data or employee_data.get('company_id') != company_id:
                return False, "You are not part of this company"
            
            employee_role = employee_data.get('role', '')
            if employee_role not in ['CEO', 'Upper Management']:
                return False, "You don't have permission to accept deals"
            
            # Get deal
            deals = self.data_handler.get_company_deals(company_id)
            deal = next((d for d in deals if d.get('id') == deal_id), None)
            
            if not deal:
                return False, "Deal not found"
            
            if deal.get('status') != 'pending':
                return False, "This deal is not pending"
            
            from_company_id = deal.get('from_company_id')
            if from_company_id not in self.companies_cache:
                return False, "Deal origin company not found"
            
            from_company = self.companies_cache[from_company_id]
            amount = deal.get('amount', 0)
            
            # Check if origin company still has funds
            if from_company.get('funds', 0) < amount:
                return False, "Origin company doesn't have enough funds for this deal"
            
            # Transfer funds
            from_company['funds'] -= amount
            company['funds'] += amount
            
            # Update deal status
            deal['status'] = 'accepted'
            deal['accepted_at'] = time.time()
            deal['accepted_by'] = user_id
            self.data_handler.update_company_deal(company_id, deal_id, deal)
            
            # Update deal in origin company
            from_deals = self.data_handler.get_company_deals(from_company_id)
            from_deal = next((d for d in from_deals if d.get('id') == deal_id), None)
            if from_deal:
                from_deal['status'] = 'accepted'
                from_deal['accepted_at'] = time.time()
                self.data_handler.update_company_deal(from_company_id, deal_id, from_deal)
            
            # Record transactions
            self.data_handler.save_transaction({
                'user_id': user_id,
                'type': 'deal_accept',
                'amount': amount,
                'details': f"Accepted deal: {deal.get('description', 'Unknown Deal')}"
            })
            
            return True, f"Deal accepted! ${amount:,.2f} transferred to your company"
    
    def get_company_info(self, company_id):
        """Get information about a company"""
        if company_id not in self.companies_cache:
            return None
        
        company = self.companies_cache[company_id].copy()
        
        # Add employee details
        employees = self.data_handler.get_all_employees()
        company['employee_details'] = []
        
        for emp in company.get('employees', []):
            user_id = emp.get('user_id')
            if str(user_id) in employees:
                emp_data = employees[str(user_id)]
                company['employee_details'].append({
                    'user_id': user_id,
                    'role': emp_data.get('role', 'Unknown'),
                    'salary': emp_data.get('salary', 0),
                    'joined_at': emp_data.get('joined_at', 0)
                })
        
        # Add tasks
        company['tasks'] = self.data_handler.get_company_tasks(company_id)
        
        # Add deals
        company['deals'] = self.data_handler.get_company_deals(company_id)
        
        return company
