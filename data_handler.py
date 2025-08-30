import json
import os
import time
import threading
from datetime import datetime
import config

class JSONDataHandler:
    def __init__(self):
        self.data_dir = config.DATA_DIR
        # Existing files
        self.users_file = config.USERS_FILE
        self.investments_file = config.INVESTMENTS_FILE
        self.transactions_file = config.TRANSACTIONS_FILE
        self.history_file = config.HISTORY_FILE
        self.spam_tracker_file = config.SPAM_TRACKER_FILE
        
        # New company system files
        self.companies_file = config.COMPANIES_FILE
        self.employees_file = config.EMPLOYEES_FILE
        self.tasks_file = config.TASKS_FILE
        self.deals_file = config.DEALS_FILE
        
        self.lock = threading.RLock()
        
        # Initialize data directory
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Initialize data files if they don't exist
        self._init_data_files()
    
    def _init_data_files(self):
        """Initialize data files with empty structures if they don't exist"""
        with self.lock:
            # Existing files
            if not os.path.exists(self.users_file):
                self._save_data({}, self.users_file)
            
            if not os.path.exists(self.investments_file):
                self._save_data([], self.investments_file)
            
            if not os.path.exists(self.transactions_file):
                self._save_data([], self.transactions_file)
            
            if not os.path.exists(self.history_file):
                self._save_data([], self.history_file)
            
            if not os.path.exists(self.spam_tracker_file):
                self._save_data({}, self.spam_tracker_file)
            
            # New company system files
            if not os.path.exists(self.companies_file):
                self._save_data({}, self.companies_file)
            
            if not os.path.exists(self.employees_file):
                self._save_data({}, self.employees_file)
            
            if not os.path.exists(self.tasks_file):
                self._save_data({}, self.tasks_file)
            
            if not os.path.exists(self.deals_file):
                self._save_data({}, self.deals_file)
    
    def _load_data(self, file_path):
        """Load data from a JSON file"""
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Return appropriate empty data structure based on file
            if file_path in [self.users_file, self.companies_file, self.employees_file, 
                           self.tasks_file, self.deals_file, self.spam_tracker_file]:
                return {}
            return []
    
    def _save_data(self, data, file_path):
        """Save data to a JSON file with pretty formatting"""
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2, default=self._json_serializer)
            return True
        except Exception as e:
            print(f"Error saving data to {file_path}: {e}")
            return False
    
    def _json_serializer(self, obj):
        """Custom JSON serializer for non-serializable objects"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    # User operations (existing)
    def get_all_users(self):
        with self.lock:
            return self._load_data(self.users_file)
    
    def get_user(self, user_id):
        users = self.get_all_users()
        return users.get(str(user_id))
    
    def save_user(self, user_data):
        with self.lock:
            users = self.get_all_users()
            users[str(user_data['user_id'])] = user_data
            return self._save_data(users, self.users_file)
    
    def save_all_users(self, users_data):
        with self.lock:
            return self._save_data(users_data, self.users_file)
    
    # Investment operations (existing)
    def get_all_investments(self):
        with self.lock:
            return self._load_data(self.investments_file)
    
    def save_investment(self, investment_data):
        with self.lock:
            investments = self.get_all_investments()
            if 'id' not in investment_data:
                investment_data['id'] = max([inv.get('id', 0) for inv in investments] + [0]) + 1
            investments.append(investment_data)
            return self._save_data(investments, self.investments_file)
    
    def update_investment(self, investment_id, updates):
        with self.lock:
            investments = self.get_all_investments()
            for investment in investments:
                if investment.get('id') == investment_id:
                    investment.update(updates)
                    return self._save_data(investments, self.investments_file)
            return False
    
    def remove_investment(self, investment_id):
        with self.lock:
            investments = self.get_all_investments()
            investments = [inv for inv in investments if inv.get('id') != investment_id]
            return self._save_data(investments, self.investments_file)
    
    # Transaction operations (existing)
    def get_all_transactions(self):
        with self.lock:
            return self._load_data(self.transactions_file)
    
    def save_transaction(self, transaction_data):
        with self.lock:
            transactions = self.get_all_transactions()
            if 'id' not in transaction_data:
                transaction_data['id'] = max([t.get('id', 0) for t in transactions] + [0]) + 1
            transaction_data['created_at'] = datetime.now().isoformat()
            transactions.append(transaction_data)
            return self._save_data(transactions, self.transactions_file)
    
    # History operations (existing)
    def get_all_history(self):
        with self.lock:
            return self._load_data(self.history_file)
    
    def save_history(self, history_data):
        with self.lock:
            history = self.get_all_history()
            if 'id' not in history_data:
                history_data['id'] = max([h.get('id', 0) for h in history] + [0]) + 1
            history_data['recorded_at'] = datetime.now().isoformat()
            history.append(history_data)
            return self._save_data(history, self.history_file)
    
    def get_user_history(self, user_id, days=7):
        history = self.get_all_history()
        cutoff = time.time() - (days * 24 * 3600)
        
        return [record for record in history 
                if record.get('user_id') == user_id and 
                self._parse_timestamp(record.get('recorded_at', 0)) > cutoff]
    
    # Spam tracker operations (existing)
    def get_spam_data(self):
        with self.lock:
            return self._load_data(self.spam_tracker_file)
    
    def save_spam_data(self, spam_data):
        with self.lock:
            return self._save_data(spam_data, self.spam_tracker_file)
    
    def update_user_spam_data(self, user_id, spam_data):
        with self.lock:
            all_spam_data = self.get_spam_data()
            all_spam_data[str(user_id)] = spam_data
            return self.save_spam_data(all_spam_data)
    
    # Company operations (new)
    def get_all_companies(self):
        with self.lock:
            return self._load_data(self.companies_file)
    
    def get_company(self, company_id):
        companies = self.get_all_companies()
        return companies.get(str(company_id))
    
    def save_company(self, company_data):
        with self.lock:
            companies = self.get_all_companies()
            companies[str(company_data['id'])] = company_data
            return self._save_data(companies, self.companies_file)
    
    def update_company(self, company_id, updates):
        with self.lock:
            companies = self.get_all_companies()
            if str(company_id) in companies:
                companies[str(company_id)].update(updates)
                return self._save_data(companies, self.companies_file)
            return False
    
    def remove_company(self, company_id):
        with self.lock:
            companies = self.get_all_companies()
            if str(company_id) in companies:
                del companies[str(company_id)]
                return self._save_data(companies, self.companies_file)
            return False
    
    # Employee operations (new)
    def get_all_employees(self):
        with self.lock:
            return self._load_data(self.employees_file)
    
    def get_employee(self, user_id):
        employees = self.get_all_employees()
        return employees.get(str(user_id))
    
    def save_employee(self, employee_data):
        with self.lock:
            employees = self.get_all_employees()
            employees[str(employee_data['user_id'])] = employee_data
            return self._save_data(employees, self.employees_file)
    
    def update_employee(self, user_id, updates):
        with self.lock:
            employees = self.get_all_employees()
            if str(user_id) in employees:
                employees[str(user_id)].update(updates)
                return self._save_data(employees, self.employees_file)
            return False
    
    def remove_employee(self, user_id):
        with self.lock:
            employees = self.get_all_employees()
            if str(user_id) in employees:
                del employees[str(user_id)]
                return self._save_data(employees, self.employees_file)
            return False
    
    # Task operations (new)
    def get_all_tasks(self):
        with self.lock:
            return self._load_data(self.tasks_file)
    
    def get_company_tasks(self, company_id):
        tasks = self.get_all_tasks()
        return tasks.get(str(company_id), [])
    
    def save_company_tasks(self, company_id, tasks):
        with self.lock:
            all_tasks = self.get_all_tasks()
            all_tasks[str(company_id)] = tasks
            return self._save_data(all_tasks, self.tasks_file)
    
    def add_company_task(self, company_id, task_data):
        with self.lock:
            tasks = self.get_company_tasks(company_id)
            task_id = max([task.get('id', 0) for task in tasks] + [0]) + 1
            task_data['id'] = task_id
            task_data['created_at'] = datetime.now().isoformat()
            tasks.append(task_data)
            return self.save_company_tasks(company_id, tasks)
    
    def update_company_task(self, company_id, task_id, updates):
        with self.lock:
            tasks = self.get_company_tasks(company_id)
            for task in tasks:
                if task.get('id') == task_id:
                    task.update(updates)
                    return self.save_company_tasks(company_id, tasks)
            return False
    
    def remove_company_task(self, company_id, task_id):
        with self.lock:
            tasks = self.get_company_tasks(company_id)
            tasks = [task for task in tasks if task.get('id') != task_id]
            return self.save_company_tasks(company_id, tasks)
    
    # Deal operations (new)
    def get_all_deals(self):
        with self.lock:
            return self._load_data(self.deals_file)
    
    def get_company_deals(self, company_id):
        deals = self.get_all_deals()
        return deals.get(str(company_id), [])
    
    def save_company_deals(self, company_id, deals):
        with self.lock:
            all_deals = self.get_all_deals()
            all_deals[str(company_id)] = deals
            return self._save_data(all_deals, self.deals_file)
    
    def add_company_deal(self, company_id, deal_data):
        with self.lock:
            deals = self.get_company_deals(company_id)
            deal_id = max([deal.get('id', 0) for deal in deals] + [0]) + 1
            deal_data['id'] = deal_id
            deal_data['created_at'] = datetime.now().isoformat()
            deals.append(deal_data)
            return self.save_company_deals(company_id, deals)
    
    def update_company_deal(self, company_id, deal_id, updates):
        with self.lock:
            deals = self.get_company_deals(company_id)
            for deal in deals:
                if deal.get('id') == deal_id:
                    deal.update(updates)
                    return self.save_company_deals(company_id, deals)
            return False
    
    def remove_company_deal(self, company_id, deal_id):
        with self.lock:
            deals = self.get_company_deals(company_id)
            deals = [deal for deal in deals if deal.get('id') != deal_id]
            return self.save_company_deals(company_id, deals)
    
    def _parse_timestamp(self, timestamp):
        if isinstance(timestamp, (int, float)):
            return timestamp
        try:
            dt = datetime.fromisoformat(timestamp)
            return dt.timestamp()
        except (ValueError, TypeError):
            return 0
