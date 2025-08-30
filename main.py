import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import config
from economy import EconomySystem
import commands as bot_commands
import threading
import time

# Initialize bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=config.BOT_PREFIX, intents=intents)

# Setup economy system
economy = EconomySystem()

# Background task to sync data to storage
async def sync_data_periodically():
    """Background task to sync data to storage periodically"""
    await bot.wait_until_ready()
    
    while not bot.is_closed():
        try:
            economy.sync_to_storage()
            await asyncio.sleep(config.CACHE_SYNC_INTERVAL)
        except Exception as e:
            print(f"Error in sync_data_periodically: {e}")
            await asyncio.sleep(60)

# Event: Bot is ready
@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guilds.')
    
    # Set bot activity
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching, 
        name="the stock market"
    ))
    
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    
    # Start the background task
    bot.loop.create_task(sync_data_periodically())

# Event: Message handler with anti-spam
@bot.event
async def on_message(message):
    if message.author.bot:
        return
        
    try:
        # Update user activity with anti-spam check
        economy.update_user_activity(message.author.id, message.content)
    except Exception as e:
        print(f"Error updating user activity: {e}")
    
    # Process commands
    await bot.process_commands(message)

# Error handling for slash commands
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandNotFound):
        await interaction.response.send_message("Command not found.", ephemeral=True)
    elif isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
    else:
        await interaction.response.send_message(f"An error occurred: {str(error)}", ephemeral=True)
        print(f"Slash command error: {error}")

# Setup slash commands
# Existing commands
@bot.tree.command(name="balance", description="Check your cash balance and stock value")
async def balance(interaction: discord.Interaction):
    await bot_commands.balance(interaction, economy)

@bot.tree.command(name="buy", description="Buy stocks of another user")
@app_commands.describe(member="The user to invest in", amount="Number of shares to buy")
async def buy(interaction: discord.Interaction, member: discord.Member, amount: float):
    await bot_commands.buy(interaction, economy, member, amount)

@bot.tree.command(name="sell", description="Sell stocks of another user")
@app_commands.describe(member="The user you invested in", amount="Number of shares to sell")
async def sell(interaction: discord.Interaction, member: discord.Member, amount: float):
    await bot_commands.sell(interaction, economy, member, amount)

@bot.tree.command(name="portfolio", description="View your investment portfolio")
async def portfolio(interaction: discord.Interaction):
    await bot_commands.portfolio(interaction, economy)

@bot.tree.command(name="market", description="View top users by stock value")
@app_commands.describe(limit="Number of users to show (default: 10)")
async def market(interaction: discord.Interaction, limit: int = 10):
    await bot_commands.market(interaction, economy, limit)

@bot.tree.command(name="profile", description="View a user's profile")
@app_commands.describe(member="The user to view (default: yourself)")
async def profile(interaction: discord.Interaction, member: discord.Member = None):
    await bot_commands.profile(interaction, economy, member)

@bot.tree.command(name="chart", description="View stock performance chart for a user")
@app_commands.describe(member="The user to view (default: yourself)", days="Number of days to show (1-30)")
async def chart(interaction: discord.Interaction, member: discord.Member = None, days: int = 7):
    await bot_commands.chart(interaction, economy, member, days)

# New company commands
@bot.tree.command(name="create_company", description="Create a new company")
@app_commands.describe(name="Company name", description="Company description", initial_funds="Initial investment")
async def create_company(interaction: discord.Interaction, name: str, description: str, initial_funds: float):
    await bot_commands.create_company(interaction, economy, name, description, initial_funds)

@bot.tree.command(name="hire", description="Hire an employee to your company")
@app_commands.describe(user="User to hire", role="Employee role", salary="Monthly salary")
async def hire(interaction: discord.Interaction, user: discord.Member, role: str, salary: float):
    await bot_commands.hire_employee(interaction, economy, user, role, salary)

@bot.tree.command(name="fire", description="Fire an employee from your company")
@app_commands.describe(user="User to fire")
async def fire(interaction: discord.Interaction, user: discord.Member):
    await bot_commands.fire_employee(interaction, economy, user)

@bot.tree.command(name="create_task", description="Create a task for an employee")
@app_commands.describe(title="Task title", description="Task description", assignee="Employee to assign to", reward="Completion reward")
async def create_task(interaction: discord.Interaction, title: str, description: str, assignee: discord.Member, reward: float):
    await bot_commands.create_task(interaction, economy, title, description, assignee, reward)

@bot.tree.command(name="complete_task", description="Complete a task and receive reward")
@app_commands.describe(task_id="ID of the task to complete")
async def complete_task(interaction: discord.Interaction, task_id: int):
    await bot_commands.complete_task(interaction, economy, task_id)

@bot.tree.command(name="create_deal", description="Create a deal with another company")
@app_commands.describe(target_company="ID of the target company", description="Deal description", amount="Deal amount")
async def create_deal(interaction: discord.Interaction, target_company: str, description: str, amount: float):
    await bot_commands.create_deal(interaction, economy, target_company, description, amount)

@bot.tree.command(name="accept_deal", description="Accept a proposed deal")
@app_commands.describe(deal_id="ID of the deal to accept")
async def accept_deal(interaction: discord.Interaction, deal_id: int):
    await bot_commands.accept_deal(interaction, economy, deal_id)

@bot.tree.command(name="company_info", description="View information about a company")
@app_commands.describe(company_id="Company ID (default: your company)")
async def company_info(interaction: discord.Interaction, company_id: int = None):
    await bot_commands.company_info(interaction, economy, company_id)

# Run the bot
if __name__ == "__main__":
    bot.run(config.DISCORD_TOKEN)
