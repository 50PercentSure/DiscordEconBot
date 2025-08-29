import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import config
from database import init_db, get_db_connection
from economy import EconomySystem
import commands as bot_commands

# Initialize bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=config.BOT_PREFIX, intents=intents)

# Initialize database
init_db()

# Setup economy system
economy = EconomySystem()


# Background task to record stock values periodically
async def record_daily_values():
    """Background task to record stock values periodically"""
    await bot.wait_until_ready()
    from database import record_stock_history

    while not bot.is_closed():
        try:
            # Record values for all users every hour
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT user_id, stock_value, message_count FROM users')
                users = cursor.fetchall()

                for user in users:
                    user_id = user['user_id']
                    stock_value = user['stock_value']
                    message_count = user['message_count']

                    # Record history
                    record_stock_history(user_id, stock_value, message_count)

            # Wait for an hour before recording again
            await asyncio.sleep(3600)
        except Exception as e:
            print(f"Error in record_daily_values: {e}")
            await asyncio.sleep(300)  # Wait 5 minutes on error


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
    bot.loop.create_task(record_daily_values())


# Event: Message handler
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Update user activity in economy system
    economy.update_user_activity(message.author.id)

    # Process commands (for any remaining prefix commands)
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
@bot.tree.command(name="balance", description="Check your cash balance and stock value")
async def balance(interaction: discord.Interaction):
    await bot_commands.balance(interaction)


@bot.tree.command(name="buy", description="Buy stocks of another user")
@app_commands.describe(member="The user to invest in", amount="Number of shares to buy")
async def buy(interaction: discord.Interaction, member: discord.Member, amount: float):
    await bot_commands.buy(interaction, member, amount)


@bot.tree.command(name="sell", description="Sell stocks of another user")
@app_commands.describe(member="The user you invested in", amount="Number of shares to sell")
async def sell(interaction: discord.Interaction, member: discord.Member, amount: float):
    await bot_commands.sell(interaction, member, amount)


@bot.tree.command(name="portfolio", description="View your investment portfolio")
async def portfolio(interaction: discord.Interaction):
    await bot_commands.portfolio(interaction)


@bot.tree.command(name="market", description="View top users by stock value")
@app_commands.describe(limit="Number of users to show (default: 10)")
async def market(interaction: discord.Interaction, limit: int = 10):
    await bot_commands.market(interaction, limit)


@bot.tree.command(name="profile", description="View a user's profile")
@app_commands.describe(member="The user to view (default: yourself)")
async def profile(interaction: discord.Interaction, member: discord.Member = None):
    await bot_commands.profile(interaction, member)


@bot.tree.command(name="chart", description="View stock performance chart for a user")
@app_commands.describe(member="The user to view (default: yourself)", days="Number of days to show (1-30)")
async def chart(interaction: discord.Interaction, member: discord.Member = None, days: int = 7):
    await bot_commands.chart(interaction, member, days)


# Run the bot
if __name__ == "__main__":
    bot.run(config.DISCORD_TOKEN)