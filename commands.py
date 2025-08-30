import discord
from discord import app_commands
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import io
from datetime import datetime
import numpy as np

# Existing commands (balance, buy, sell, portfolio, market, profile, chart) remain unchanged

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
