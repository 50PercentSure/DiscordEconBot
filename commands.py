import discord
from discord import app_commands
from database import get_user_data, get_stock_history
from economy import EconomySystem
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import io
from datetime import datetime

# Initialize economy system
economy = EconomySystem()


async def balance(interaction: discord.Interaction):
    """Check your cash balance and stock value"""
    user_data = get_user_data(interaction.user.id)
    if not user_data:
        await interaction.response.send_message(
            "You're not registered in the system yet. Send a message to get started!", ephemeral=True)
        return

    embed = discord.Embed(
        title=f"{interaction.user.display_name}'s Balance",
        color=discord.Color.blue()
    )
    embed.add_field(name="Cash Balance", value=f"${user_data['cash_balance']:.2f}", inline=True)
    embed.add_field(name="Stock Value", value=f"${user_data['stock_value']:.2f}", inline=True)
    embed.add_field(name="Message Count", value=user_data['message_count'], inline=True)
    await interaction.response.send_message(embed=embed)


async def buy(interaction: discord.Interaction, member: discord.Member, amount: float):
    """Buy stocks of another user"""
    if member.id == interaction.user.id:
        await interaction.response.send_message("You cannot buy your own stocks!", ephemeral=True)
        return

    if amount <= 0:
        await interaction.response.send_message("Amount must be positive!", ephemeral=True)
        return

    success, message = economy.buy_stocks(interaction.user.id, member.id, amount)
    if success:
        embed = discord.Embed(
            title="Stock Purchase",
            description=message,
            color=discord.Color.green()
        )
    else:
        embed = discord.Embed(
            title="Purchase Failed",
            description=message,
            color=discord.Color.red()
        )
    await interaction.response.send_message(embed=embed)


async def sell(interaction: discord.Interaction, member: discord.Member, amount: float):
    """Sell stocks of another user"""
    if amount <= 0:
        await interaction.response.send_message("Amount must be positive!", ephemeral=True)
        return

    success, message = economy.sell_stocks(interaction.user.id, member.id, amount)
    if success:
        embed = discord.Embed(
            title="Stock Sale",
            description=message,
            color=discord.Color.green()
        )
    else:
        embed = discord.Embed(
            title="Sale Failed",
            description=message,
            color=discord.Color.red()
        )
    await interaction.response.send_message(embed=embed)


async def portfolio(interaction: discord.Interaction):
    """View your investment portfolio"""
    portfolio = economy.get_portfolio(interaction.user.id)

    if not portfolio['investments']:
        await interaction.response.send_message("Your portfolio is empty. Use `/buy` to invest in other users!",
                                                ephemeral=True)
        return

    embed = discord.Embed(
        title=f"{interaction.user.display_name}'s Portfolio",
        color=discord.Color.gold()
    )

    for investment in portfolio['investments']:
        user = await interaction.client.fetch_user(investment['subject_id'])
        embed.add_field(
            name=user.display_name,
            value=f"Shares: {investment['shares']:.2f}\n" +
                  f"Current Value: ${investment['current_value']:.2f}\n" +
                  f"P/L: ${investment['profit_loss']:+.2f} ({investment['profit_loss_percent']:+.2f}%)",
            inline=True
        )

    embed.add_field(
        name="Summary",
        value=f"Cash: ${portfolio['cash_balance']:.2f}\n" +
              f"Investments: ${portfolio['total_investment_value']:.2f}\n" +
              f"Total: ${portfolio['total_portfolio_value']:.2f}\n" +
              f"Total P/L: ${portfolio['total_profit_loss']:+.2f} ({portfolio['total_profit_loss_percent']:+.2f}%)",
        inline=False
    )

    await interaction.response.send_message(embed=embed)


async def market(interaction: discord.Interaction, limit: int):
    """View top users by stock value"""
    from database import get_db_connection

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
                       SELECT user_id, username, stock_value, message_count
                       FROM users
                       ORDER BY stock_value DESC LIMIT ?
                       ''', (limit,))

        top_users = cursor.fetchall()

    embed = discord.Emembed(
        title="Stock Market Leaders",
        color=discord.Color.purple()
    )

    for i, user in enumerate(top_users, 1):
        discord_user = await interaction.client.fetch_user(user['user_id'])
        embed.add_field(
            name=f"{i}. {discord_user.display_name}",
            value=f"Value: ${user['stock_value']:.2f}\nMessages: {user['message_count']}",
            inline=False
        )

    await interaction.response.send_message(embed=embed)


async def profile(interaction: discord.Interaction, member: discord.Member):
    """View a user's profile"""
    target = member or interaction.user
    user_data = get_user_data(target.id)

    if not user_data:
        await interaction.response.send_message("User not found in the system!", ephemeral=True)
        return

    # Get number of investors
    from database import get_db_connection
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
                       SELECT COUNT(*) as investor_count
                       FROM investments
                       WHERE subject_id = ?
                       ''', (target.id,))
        investor_count = cursor.fetchone()['investor_count']

    embed = discord.Embed(
        title=f"{target.display_name}'s Profile",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=target.avatar.url if target.avatar else None)
    embed.add_field(name="Stock Value", value=f"${user_data['stock_value']:.2f}", inline=True)
    embed.add_field(name="Message Count", value=user_data['message_count'], inline=True)
    embed.add_field(name="Investors", value=investor_count, inline=True)
    embed.add_field(name="Account Created", value=target.created_at.strftime("%Y-%m-%d"), inline=True)

    await interaction.response.send_message(embed=embed)


async def chart(interaction: discord.Interaction, member: discord.Member, days: int):
    """View stock performance chart for a user"""
    target = member or interaction.user

    # Validate days parameter
    if days < 1 or days > 30:
        await interaction.response.send_message("Please specify a number of days between 1 and 30.", ephemeral=True)
        return

    # Get historical data
    history = get_stock_history(target.id, days)

    if not history:
        await interaction.response.send_message("No historical data available for this user.", ephemeral=True)
        return

    # Extract data for plotting
    dates = [datetime.strptime(row['recorded_at'], '%Y-%m-%d %H:%M:%S') for row in history]
    values = [row['stock_value'] for row in history]

    # Create the plot
    plt.figure(figsize=(10, 6))
    plt.plot(dates, values, marker='o', linestyle='-', linewidth=2, markersize=4)

    # Format the plot
    plt.title(f"{target.display_name}'s Stock Performance (Last {days} Days)")
    plt.xlabel("Date")
    plt.ylabel("Stock Value ($)")
    plt.grid(True, alpha=0.3)

    # Format x-axis to show dates nicely
    plt.gcf().autofmt_xdate()
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=max(1, days // 7)))

    # Add value labels to some points to make it more readable
    if len(values) > 5:
        # Label first, last, and max/min points
        indices_to_label = [0, len(values) - 1]
        indices_to_label.append(values.index(max(values)))
        indices_to_label.append(values.index(min(values)))

        for i in set(indices_to_label):
            if i < len(values):
                plt.annotate(f"${values[i]:.2f}",
                             (dates[i], values[i]),
                             textcoords="offset points",
                             xytext=(0, 10),
                             ha='center')

    # Save to bytes buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    plt.close()

    # Get current stock value for context
    current_value = economy.get_stock_price(target.id)

    # Create embed with chart
    embed = discord.Embed(
        title=f"{target.display_name}'s Stock Performance",
        description=f"Current value: ${current_value:.2f} (Last {days} days)",
        color=discord.Color.blue()
    )

    # Send the chart as a file
    file = discord.File(buf, filename="stock_chart.png")
    embed.set_image(url="attachment://stock_chart.png")
    await interaction.response.send_message(embed=embed, file=file)