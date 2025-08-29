import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot configuration
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
BOT_PREFIX = '!'  # Keep for fallback, but primarily using slash commands now
INITIAL_BALANCE = 1000
INITIAL_STOCK_VALUE = 10.0
ACTIVITY_REWARD = 0.1  # Cash reward per message
VALUE_INCREASE = 0.01  # Stock value increase per message

# Database configuration
DATABASE_PATH = 'data/stock_bot.db'

# Chart configuration
CHART_DAYS_LIMIT = 30  # Maximum days for chart history

# Channel restrictions (optional)
RESTRICTED_CHANNELS = []  # Add channel IDs to restrict bot functionality