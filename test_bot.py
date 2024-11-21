import os
import asyncio
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
from datetime import datetime, timedelta
import random
import json

load_dotenv()
BOT_TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_TOKEN = os.getenv('DISCORD_GUILD')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='$', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    if not send_scheduled_messages.is_running():
        send_scheduled_messages.start()

def get_user_or_role(ctx, identifier):
    # Check if the identifier is a user
    user = discord.utils.get(ctx.guild.members, name=identifier)
    if user:
        return user, 'user'
    
    # Check if the identifier is a role
    role = discord.utils.get(ctx.guild.roles, name=identifier)
    if role:
        return role, 'role'
    
    return None, None

scheduled_messages = []

@bot.command(name='99')
async def nine_nine(ctx):
    brooklyn_99_quotes = [
        'I\'m the human form of the 💯 emoji.',
        'Bingpot!',
        (
            'Cool. Cool cool cool cool cool cool cool, '
            'no doubt no doubt no doubt no doubt.'
        ),
    ]

    response = random.choice(brooklyn_99_quotes)
    await ctx.send(response)

@bot.command(name='schedule')
@commands.has_permissions(administrator=True)
async def schedule_message(ctx, identifier: str, interval_minutes: int, *, message: str):
    """Schedule messages to send to a user or all members with a specific role at intervals."""
    target, target_type = get_user_or_role(ctx, identifier)
    if not target:
        await ctx.send(f"Couldn't find user or role with the name: {identifier}")
        return
    
    next_send_time = datetime.now() + timedelta(minutes=interval_minutes)
    is_role = (target_type == 'role')
    scheduled_messages.append((target.id, is_role, message, next_send_time, interval_minutes))
    if is_role:
        await ctx.send(f'Message scheduled to role {target.name} every {interval_minutes} minutes.')
    else:
        await ctx.send(f'Message scheduled to {target.name} every {interval_minutes} minutes.')

@bot.command(name='send')
@commands.has_permissions(administrator=True)
async def send_message(ctx, identifier: str, *, message: str):
    """Send an immediate message to a user or all members with a specific role."""
    target, target_type = get_user_or_role(ctx, identifier)
    if not target:
        await ctx.send(f"Couldn't find user or role with the name: {identifier}")
        return

    if target_type == 'role':
        for member in target.members:
            try:
                await member.send(message)
            except discord.Forbidden:
                await ctx.send(f'Could not send message to {member.name}.')
    else:
        try:
            await target.send(message)
            await ctx.send(f'Message sent to {target.name}.')
        except discord.Forbidden:
            await ctx.send(f'Could not send message to {target.name}.')

@tasks.loop(seconds=30)
async def send_scheduled_messages():
    now = datetime.now()
    for i, (target_id, is_role, message, next_send_time, interval) in enumerate(scheduled_messages):
        print(f"Checking scheduled message for target ID {target_id} (is_role: {is_role}) at {now}")

        if now >= next_send_time:
            if is_role:
                role = discord.utils.get(bot.get_guild(GUILD_TOKEN).roles, id=target_id)
                if role:
                    print(f"Sending message to role: {role.name}")

                    for member in role.members:
                        try:
                            await member.send(message)
                            print(f"Sent message to {member.name}")
                        except discord.Forbidden:
                            print(f"Could not send message to {member.name}.")
            else:
                user = bot.get_user(target_id)
                if user:
                    try:
                        await user.send(message)
                        print(f"Sent message to {user.name}")
                    except discord.Forbidden:
                        print(f"Could not send message to {user.name}.")
                else:
                    print(f"User with ID {target_id} not found.")

            # Update the next_send_time for the scheduled message
            scheduled_messages[i] = (target_id, is_role, message, now + timedelta(minutes=interval), interval)
            print(f"Rescheduled message for target ID {target_id} to send at {now + timedelta(minutes=interval)}")

user_responses = {}

async def start_survey(user):
    questions = [
        "Thermometer Testing: 1-10 + explanation\nFunction (integer) - how well solution/approach works:",
        "Elegance (integer) - the beauty of the design, thinking beauty:",
        "Effort (integer) - How hard you worked:",
        "Resources (list) - list the number, name, and kinds of resources (type 'done' when finished):"
    ]
    if user.id not in user_responses:
        user_responses[user.id] = []

    for question in questions[:-1]:
        await user.send(question)
        def check(m):
            return m.author == user and isinstance(m.channel, discord.DMChannel)
        response = await bot.wait_for('message', check=check)
        user_responses[user.id].append((question, response.content))

    # Handle the "Resources" question separately
    await user.send(questions[-1])
    resources = []
    while True:
        def check(m):
            return m.author == user and isinstance(m.channel, discord.DMChannel)
        response = await bot.wait_for('message', check=check)
        if response.content.lower() == 'done':
            break
        resources.append(response.content)
    user_responses[user.id].append((questions[-1], resources))

    await save_responses_to_file(user.id)

async def save_responses_to_file(user_id):
    filename = f'{user_id}.json'
    data = []

    if os.path.exists(filename):
        with open(filename, 'r') as f:
            data = json.load(f)

    response_number = len(data) + 1
    data.append({
        "response_number": response_number,
        "responses": user_responses[user_id]
    })

    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)


"""
This @bot.event is an override and we need to add the message processor
back to the main thread with `await bot.process_commands(message)`
"""
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Check if the message is in the specified channel
    if message.channel.id == 1309259804333572217:
        await start_survey(message.author)

    if message.content.startswith('$hello'):
        await message.channel.send('Hello!')
    
    # needed to process other `bot.commands`
    await bot.process_commands(message)

bot.run(BOT_TOKEN)