import discord
from discord import app_commands
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import io
from datetime import datetime
import numpy as np

# Existing commands (balance, buy, sell, portfolio, market, profile, chart) remain unchanged
async def balance(interaction: discord.Interaction, economy):
    """Check your cash balance and stock value with trend"""
    user_data = economy.get_user_data(interaction.user.id)
    if not user_data:
        await interaction.response.send_message("You're not registered in the system yet. Send a message to get started!", ephemeral=True)
        return
        
    # Calculate trend
    trend = economy.calculate_trend(interaction.user.id)
    trend_icon = "📈" if trend > 0 else "📉" if trend < 0 else "➡️"
    
    # Predict tomorrow's price
    predicted_price = economy.predict_future_price(interaction.user.id, 1)
    prediction_change = predicted_price - user_data['stock_value']
    prediction_icon = "🔮"
    
    embed = discord.Embed(
        title=f"{interaction.user.display_name}'s Balance",
        color=discord.Color.blue()
    )
    embed.add_field(name="Cash Balance", value=f"${user_data['cash_balance']:.2f}", inline=True)
    embed.add_field(name="Stock Value", value=f"${user_data['stock_value']:.2f}", inline=True)
    embed.add_field(name="Message Count", value=user_data['message_count'], inline=True)
    embed.add_field(name="7-Day Trend", value=f"{trend_icon} {trend:+.2f}%", inline=True)
    embed.add_field(name="Tomorrow's Prediction", value=f"{prediction_icon} ${predicted_price:.2f} ({prediction_change:+.2f})", inline=True)
    
    await interaction.response.send_message(embed=embed)

async def buy(interaction: discord.Interaction, economy, member: discord.Member, amount: float):
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

async def sell(interaction: discord.Interaction, economy, member: discord.Member, amount: float):
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

async def portfolio(interaction: discord.Interaction, economy):
    """View your investment portfolio with trends"""
    portfolio = economy.get_portfolio(interaction.user.id)
    
    if not portfolio['investments']:
        await interaction.response.send_message("Your portfolio is empty. Use `/buy` to invest in other users!", ephemeral=True)
        return
        
    embed = discord.Embed(
        title=f"{interaction.user.display_name}'s Portfolio",
        color=discord.Color.gold()
    )
    
    for investment in portfolio['investments']:
        user = await interaction.client.fetch_user(investment['subject_id'])
        trend_icon = "📈" if investment['trend'] > 0 else "📉" if investment['trend'] < 0 else "➡️"
        
        embed.add_field(
            name=f"{user.display_name} {trend_icon}",
            value=f"Shares: {investment['shares']:.2f}\n" +
                  f"Current: ${investment['current_price']:.2f}\n" +
                  f"Value: ${investment['current_value']:.2f}\n" +
                  f"P/L: ${investment['profit_loss']:+.2f} ({investment['profit_loss_percent']:+.2f}%)\n" +
                  f"Trend: {investment['trend']:+.2f}%",
            inline=True
        )
    
    # Calculate overall portfolio trend (weighted average)
    total_investment = portfolio['total_investment_value']
    if total_investment > 0:
        weighted_trend = sum(inv['trend'] * (inv['current_value'] / total_investment) 
                           for inv in portfolio['investments'])
    else:
        weighted_trend = 0
        
    trend_icon = "📈" if weighted_trend > 0 else "📉" if weighted_trend < 0 else "➡️"
    
    embed.add_field(
        name="Summary",
        value=f"Cash: ${portfolio['cash_balance']:.2f}\n" +
              f"Investments: ${portfolio['total_investment_value']:.2f}\n" +
              f"Total: ${portfolio['total_portfolio_value']:.2f}\n" +
              f"Total P/L: ${portfolio['total_profit_loss']:+.2f} ({portfolio['total_profit_loss_percent']:+.2f}%)\n" +
              f"Portfolio Trend: {trend_icon} {weighted_trend:+.2f}%",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

async def market(interaction: discord.Interaction, economy, limit: int):
    """View top users by stock value with trends"""
    users_cache = economy.users_cache
    top_users = sorted(
        users_cache.values(), 
        key=lambda x: x['stock_value'], 
        reverse=True
    )[:limit]
    
    embed = discord.Embed(
        title="Stock Market Leaders",
        color=discord.Color.purple()
    )
    
    for i, user in enumerate(top_users, 1):
        discord_user = await interaction.client.fetch_user(user['user_id'])
        trend = economy.calculate_trend(user['user_id'])
        trend_icon = "📈" if trend > 0 else "📉" if trend < 0 else "➡️"
        
        embed.add_field(
            name=f"{i}. {discord_user.display_name} {trend_icon}",
            value=f"Value: ${user['stock_value']:.2f}\n" +
                  f"Messages: {user['message_count']}\n" +
                  f"Trend: {trend:+.2f}%",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)

async def profile(interaction: discord.Interaction, economy, member: discord.Member):
    """View a user's profile with detailed trend analysis"""
    target = member or interaction.user
    user_data = economy.get_user_data(target.id)
    
    if not user_data:
        await interaction.response.send_message("User not found in the system!", ephemeral=True)
        return
        
    # Get number of investors
    investments = economy.data_handler.get_all_investments()
    investor_count = sum(1 for inv in investments if inv.get('subject_id') == target.id)
    
    # Calculate trends
    trend_7d = economy.calculate_trend(target.id, 7)
    trend_30d = economy.calculate_trend(target.id, 30)
    
    # Predict future prices
    tomorrow = economy.predict_future_price(target.id, 1)
    next_week = economy.predict_future_price(target.id, 7)
    
    trend_icon = "📈" if trend_7d > 0 else "📉" if trend_7d < 0 else "➡️"
    
    embed = discord.Embed(
        title=f"{target.display_name}'s Profile {trend_icon}",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=target.avatar.url if target.avatar else None)
    embed.add_field(name="Stock Value", value=f"${user_data['stock_value']:.2f}", inline=True)
    embed.add_field(name="Message Count", value=user_data['message_count'], inline=True)
    embed.add_field(name="Investors", value=investor_count, inline=True)
    embed.add_field(name="7-Day Trend", value=f"{trend_7d:+.2f}%", inline=True)
    embed.add_field(name="30-Day Trend", value=f"{trend_30d:+.2f}%", inline=True)
    embed.add_field(name="Tomorrow's Prediction", value=f"${tomorrow:.2f}", inline=True)
    embed.add_field(name="Next Week Prediction", value=f"${next_week:.2f}", inline=True)
    embed.add_field(name="Account Created", value=target.created_at.strftime("%Y-%m-%d"), inline=True)
    
    await interaction.response.send_message(embed=embed)

async def chart(interaction: discord.Interaction, economy, member: discord.Member, days: int):
    """View stock performance chart for a user with trend line"""
    target = member or interaction.user
    
    # Validate days parameter
    if days < 1 or days > 30:
        await interaction.response.send_message("Please specify a number of days between 1 and 30.", ephemeral=True)
        return
    
    # Get historical data
    history = economy.data_handler.get_user_history(target.id, days)
    
    if not history:
        await interaction.response.send_message("No historical data available for this user.", ephemeral=True)
        return
    
    # Extract data for plotting
    dates = [datetime.fromisoformat(record['recorded_at']) for record in history]
    values = [record['stock_value'] for record in history]
    
    # Create the plot
    plt.figure(figsize=(12, 7))
    
    # Plot actual values
    plt.plot(dates, values, marker='o', linestyle='-', linewidth=2, markersize=4, label='Actual Price')
    
    # Add trend line (linear regression)
    if len(values) > 1:
        x = np.arange(len(values))
        z = np.polyfit(x, values, 1)
        p = np.poly1d(z)
        plt.plot(dates, p(x), "r--", alpha=0.7, linewidth=1.5, label='Trend Line')
    
    # Format the plot
    plt.title(f"{target.display_name}'s Stock Performance (Last {days} Days)")
    plt.xlabel("Date")
    plt.ylabel("Stock Value ($)")
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # Format x-axis to show dates nicely
    plt.gcf().autofmt_xdate()
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=max(1, days//7)))
    
    # Add value labels to some points
    if len(values) > 5:
        indices_to_label = [0, len(values)-1]
        indices_to_label.append(values.index(max(values)))
        indices_to_label.append(values.index(min(values)))
        
        for i in set(indices_to_label):
            if i < len(values):
                plt.annotate(f"${values[i]:.2f}", 
                            (dates[i], values[i]),
                            textcoords="offset points",
                            xytext=(0,10),
                            ha='center')
    
    # Save to bytes buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    plt.close()
    
    # Get current stock value for context
    current_value = economy.get_stock_price(target.id)
    trend = economy.calculate_trend(target.id, days)
    trend_icon = "📈" if trend > 0 else "📉" if trend < 0 else "➡️"
    
    # Create embed with chart
    embed = discord.Embed(
        title=f"{target.display_name}'s Stock Performance {trend_icon}",
        description=f"Current: ${current_value:.2f} | {days}-Day Trend: {trend:+.2f}%",
        color=discord.Color.blue()
    )
    
    # Send the chart as a file
    file = discord.File(buf, filename="stock_chart.png")
    embed.set_image(url="attachment://stock_chart.png")
    await interaction.response.send_message(embed=embed, file=file)


# Company commands (new)
async def create_company(interaction: discord.Interaction, economy, name: str, description: str, initial_funds: float):
    """Create a new company"""
    if initial_funds < 5000:  # Using constant instead of config
        await interaction.response.send_message("Initial funds must be at least $5,000", ephemeral=True)
        return
        
    success, message = economy.create_company(interaction.user.id, name, description, initial_funds)
    if success:
        embed = discord.Embed(
            title="Company Created",
            description=message,
            color=discord.Color.green()
        )
    else:
        embed = discord.Embed(
            title="Company Creation Failed",
            description=message,
            color=discord.Color.red()
        )
    await interaction.response.send_message(embed=embed)

async def hire_employee(interaction: discord.Interaction, economy, user: discord.Member, role: str, salary: float):
    """Hire an employee to your company"""
    if salary <= 0:
        await interaction.response.send_message("Salary must be positive", ephemeral=True)
        return
        
    # Get user's company
    employee_data = economy.data_handler.get_employee(interaction.user.id)
    if not employee_data or not employee_data.get('company_id'):
        await interaction.response.send_message("You are not part of a company", ephemeral=True)
        return
        
    company_id = employee_data['company_id']
    success, message = economy.hire_employee(company_id, interaction.user.id, user.id, role, salary)
    
    if success:
        embed = discord.Embed(
            title="Employee Hired",
            description=message,
            color=discord.Color.green()
        )
    else:
        embed = discord.Embed(
            title="Hiring Failed",
            description=message,
            color=discord.Color.red()
        )
    await interaction.response.send_message(embed=embed)

async def fire_employee(interaction: discord.Interaction, economy, user: discord.Member):
    """Fire an employee from your company"""
    # Get user's company
    employee_data = economy.data_handler.get_employee(interaction.user.id)
    if not employee_data or not employee_data.get('company_id'):
        await interaction.response.send_message("You are not part of a company", ephemeral=True)
        return
        
    company_id = employee_data['company_id']
    success, message = economy.fire_employee(company_id, interaction.user.id, user.id)
    
    if success:
        embed = discord.Embed(
            title="Employee Fired",
            description=message,
            color=discord.Color.green()
        )
    else:
        embed = discord.Embed(
            title="Firing Failed",
            description=message,
            color=discord.Color.red()
        )
    await interaction.response.send_message(embed=embed)

async def create_task(interaction: discord.Interaction, economy, title: str, description: str, assignee: discord.Member, reward: float):
    """Create a task for an employee"""
    if reward <= 0:
        await interaction.response.send_message("Reward must be positive", ephemeral=True)
        return
        
    # Get user's company
    employee_data = economy.data_handler.get_employee(interaction.user.id)
    if not employee_data or not employee_data.get('company_id'):
        await interaction.response.send_message("You are not part of a company", ephemeral=True)
        return
        
    company_id = employee_data['company_id']
    success, message = economy.create_task(company_id, interaction.user.id, title, description, assignee.id, reward)
    
    if success:
        embed = discord.Embed(
            title="Task Created",
            description=message,
            color=discord.Color.green()
        )
    else:
        embed = discord.Embed(
            title="Task Creation Failed",
            description=message,
            color=discord.Color.red()
        )
    await interaction.response.send_message(embed=embed)

async def complete_task(interaction: discord.Interaction, economy, task_id: int):
    """Complete a task and receive reward"""
    # Get user's company
    employee_data = economy.data_handler.get_employee(interaction.user.id)
    if not employee_data or not employee_data.get('company_id'):
        await interaction.response.send_message("You are not part of a company", ephemeral=True)
        return
        
    company_id = employee_data['company_id']
    success, message = economy.complete_task(company_id, interaction.user.id, task_id)
    
    if success:
        embed = discord.Embed(
            title="Task Completed",
            description=message,
            color=discord.Color.green()
        )
    else:
        embed = discord.Embed(
            title="Task Completion Failed",
            description=message,
            color=discord.Color.red()
        )
    await interaction.response.send_message(embed=embed)

async def create_deal(interaction: discord.Interaction, economy, target_company: str, description: str, amount: float):
    """Create a deal with another company"""
    if amount <= 0:
        await interaction.response.send_message("Amount must be positive", ephemeral=True)
        return
        
    # Get user's company
    employee_data = economy.data_handler.get_employee(interaction.user.id)
    if not employee_data or not employee_data.get('company_id'):
        await interaction.response.send_message("You are not part of a company", ephemeral=True)
        return
        
    company_id = employee_data['company_id']
    
    # Convert target_company to ID (this would need additional logic to map company names to IDs)
    # For now, we'll assume target_company is provided as an ID
    try:
        target_company_id = int(target_company)
    except ValueError:
        await interaction.response.send_message("Invalid company ID", ephemeral=True)
        return
        
    success, message = economy.create_deal(company_id, interaction.user.id, target_company_id, description, amount)
    
    if success:
        embed = discord.Embed(
            title="Deal Proposed",
            description=message,
            color=discord.Color.green()
        )
    else:
        embed = discord.Embed(
            title="Deal Creation Failed",
            description=message,
            color=discord.Color.red()
        )
    await interaction.response.send_message(embed=embed)

async def accept_deal(interaction: discord.Interaction, economy, deal_id: int):
    """Accept a proposed deal"""
    # Get user's company
    employee_data = economy.data_handler.get_employee(interaction.user.id)
    if not employee_data or not employee_data.get('company_id'):
        await interaction.response.send_message("You are not part of a company", ephemeral=True)
        return
        
    company_id = employee_data['company_id']
    success, message = economy.accept_deal(company_id, interaction.user.id, deal_id)
    
    if success:
        embed = discord.Embed(
            title="Deal Accepted",
            description=message,
            color=discord.Color.green()
        )
    else:
        embed = discord.Embed(
            title="Deal Acceptance Failed",
            description=message,
            color=discord.Color.red()
        )
    await interaction.response.send_message(embed=embed)

async def company_info(interaction: discord.Interaction, economy, company_id: int = None):
    """View information about a company"""
    # If no company ID provided, try to get user's company
    if company_id is None:
        employee_data = economy.data_handler.get_employee(interaction.user.id)
        if not employee_data or not employee_data.get('company_id'):
            await interaction.response.send_message("You are not part of a company and no company ID was provided", ephemeral=True)
            return
        company_id = employee_data['company_id']
    
    company_info = economy.get_company_info(company_id)
    if not company_info:
        await interaction.response.send_message("Company not found", ephemeral=True)
        return
        
    embed = discord.Embed(
        title=company_info.get('name', 'Unknown Company'),
        description=company_info.get('description', 'No description'),
        color=discord.Color.blue()
    )
    
    # Add company details
    embed.add_field(name="Funds", value=f"${company_info.get('funds', 0):,.2f}", inline=True)
    embed.add_field(name="CEO", value=f"<@{company_info.get('ceo_id', 0)}>", inline=True)
    embed.add_field(name="Founded", value=f"<t:{int(company_info.get('founded_at', 0))}:R>", inline=True)
    embed.add_field(name="Employees", value=str(len(company_info.get('employees', []))), inline=True)
    embed.add_field(name="Stock Value", value=f"${company_info.get('stock_value', 0):,.2f}", inline=True)
    
    # Add employees list
    employees_text = ""
    for emp in company_info.get('employee_details', []):
        employees_text += f"<@{emp['user_id']}> - {emp['role']} (${emp['salary']:,.2f})\n"
    
    if employees_text:
        embed.add_field(name="Employee Roster", value=employees_text, inline=False)
    
    # Add active tasks
    tasks = company_info.get('tasks', [])
    active_tasks = [t for t in tasks if t.get('status') == 'assigned']
    if active_tasks:
        tasks_text = ""
        for task in active_tasks[:5]:  # Show up to 5 tasks
            tasks_text += f"#{task['id']} - {task['title']} (${task.get('reward', 0):,.2f})\n"
        
        if len(active_tasks) > 5:
            tasks_text += f"... and {len(active_tasks) - 5} more tasks"
        
        embed.add_field(name="Active Tasks", value=tasks_text, inline=False)
    
    await interaction.response.send_message(embed=embed)
