import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot configuration
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
BOT_PREFIX = '!'
INITIAL_BALANCE = 1000
INITIAL_STOCK_VALUE = 10.0
ACTIVITY_REWARD = 0.1
VALUE_INCREASE = 0.01

# Enhanced price calculation parameters
SMOOTHING_FACTOR = 0.7
BUY_PRESSURE_EFFECT = 0.002
VOLATILITY_FACTOR = 0.03
TREND_DAYS = 7

# Anti-spam configuration
MESSAGE_COOLDOWN = 15
SPAM_WINDOW = 10
SPAM_THRESHOLD = 5
SPAM_PENALTY_FACTOR = 0.5
MIN_MESSAGE_LENGTH = 5

# Company configuration
COMPANY_CREATION_COST = 5000
EMPLOYEE_SALARY_INTERVAL = 86400  # Daily salary payments
COMPANY_DEAL_COOLDOWN = 3600  # 1 hour between deals
TASK_COMPLETION_REWARD = 50  # Base reward for completing tasks

# Company role permissions
ROLE_PERMISSIONS = {
    "CEO": ["hire", "fire", "promote", "demote", "create_deal", "assign_task", "manage_funds"],
    "Upper Management": ["hire", "fire", "assign_task", "create_deal"],
    "Management": ["assign_task"],
    "Employee": ["complete_task"]
}

# Data storage configuration
DATA_DIR = 'data'
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
INVESTMENTS_FILE = os.path.join(DATA_DIR, 'investments.json')
TRANSACTIONS_FILE = os.path.join(DATA_DIR, 'transactions.json')
HISTORY_FILE = os.path.join(DATA_DIR, 'history.json')
SPAM_TRACKER_FILE = os.path.join(DATA_DIR, 'spam_tracker.json')
COMPANIES_FILE = os.path.join(DATA_DIR, 'companies.json')
EMPLOYEES_FILE = os.path.join(DATA_DIR, 'employees.json')
TASKS_FILE = os.path.join(DATA_DIR, 'tasks.json')
DEALS_FILE = os.path.join(DATA_DIR, 'deals.json')

# Chart configuration
CHART_DAYS_LIMIT = 30

# Cache configuration
CACHE_SYNC_INTERVAL = 300
HISTORY_RECORD_INTERVAL = 3600

# Channel restrictions (optional)
RESTRICTED_CHANNELS = []
