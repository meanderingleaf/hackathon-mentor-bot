import os
import asyncio
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
from datetime import datetime, timedelta
import random

load_dotenv()
BOT_TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_TOKEN = os.getenv('DISCORD_GUILD')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='$', intents=intents)

scheduled_messages = [
    ("genly_ai", "Don't forget to check your email!", datetime.now() + timedelta(seconds=30), 30),
]

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

@bot.command(name='send')
@commands.has_permissions(administrator=True)
async def send_message(ctx, user: discord.User, *, message: str):
    """Send an immediate message to the user."""
    print(f'Sending message to {user.name}: {message}')
    try:
        await user.send(message)
        await ctx.send(f'Message sent to {user.name}.')
    except discord.Forbidden:
        await ctx.send(f'Could not send message to {user.name}.')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.content.startswith('$hello'):
        await message.channel.send('Hello!')

bot.run(BOT_TOKEN)