import os
import asyncio
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
from datetime import datetime, timedelta
import random
import json
import plotly.graph_objects as go
import plotly.io as pio
import plotly.express as px

load_dotenv()

#program constants
BOT_TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_TOKEN = os.getenv('DISCORD_GUILD')
STATS_CHANNEL = 1309194360042160138

#runtime constants
GROUP_STATS_EMBED = None

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='$', intents=intents)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    # if not send_scheduled_messages.is_running():
    #     send_scheduled_messages.start()
    scheduler.start()

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

scheduler = AsyncIOScheduler()

def extract_repo_stats(data):
    repo_stats = []
    for repo in data['repo_array']:
        stats = repo['file_stats']['repo_stats']
        repo_stats.append({
            'user': repo['discord_user'],
            'total_lines': stats['total_lines'],
            'total_files': stats['total_files'],
            'total_size': stats['total_size'],
            "hackathon": 1
        })
    return repo_stats

@bot.command(name='collectivestats')
async def send_message(ctx):

    folder = 'thermometer_responses'

    data = []

    filename = "global-stats-example.json"
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            data = json.load(f)

    repo_stats = extract_repo_stats(data)
    total_lines = sum(repo['total_lines'] for repo in repo_stats)
    total_files = sum(repo['total_files'] for repo in repo_stats)
    total_size = sum(repo['total_size'] for repo in repo_stats)


    fig = px.bar(repo_stats, x="hackathon", y="total_files", color="user", title="Hackathon Collective Progress")

    #write figure out to file system
    if not os.path.exists("images"):
        os.mkdir("images")

    fig.write_image("images/checkins.png")

    #create file attachment for discord
    file = discord.File("images/checkins.png", filename="checkins.png")
    
    #generate an embed
    embed = discord.Embed(title = "Our Collective Progress", description="Lets go team!", color=discord.Color.green() )
    embed.set_image(url="attachment://image.png")

    #send embed to the stats channel
    channel = bot.get_channel(STATS_CHANNEL)
    #TODO - refactor into a class
    #global GROUP_STATS_EMBED
    #if GROUP_STATS_EMBED:
        #edit prexisting message
    #    await GROUP_STATS_EMBED.edit(embed=embed)
    #else:
          #make new embed if there is not one
    GROUP_STATS_EMBED = await channel.send(file=file,embed=embed)


@bot.command(name='schedule-test')
@commands.has_permissions(administrator=True)
async def schedule_command(ctx):
    """
    Schedule a message to a user or all members of a role, either one-time or recurring.
    """
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    await ctx.send("Type `1` for a one-time message or `2` for a recurring message:")

    try:
        response = await bot.wait_for('message', check=check, timeout=60.0)

        if response.content == '1':  # One-time schedule
            await ctx.send("You chose one-time. Please provide the target (user or role):")
            target_response = await bot.wait_for('message', check=check, timeout=60.0)
            target, target_type = get_user_or_role(ctx, target_response.content)

            if not target:
                await ctx.send(f"Couldn't find user or role with the name: {target_response.content}")
                return

            await ctx.send("Please provide the date and time in the format: `YYYY-MM-DD HH:MM`")
            time_response = await bot.wait_for('message', check=check, timeout=60.0)
            try:
                date_time = datetime.strptime(time_response.content, "%Y-%m-%d %H:%M")
            except ValueError:
                await ctx.send("Invalid date-time format. Please use `2024-11-21 14:40`.")
                return

            await ctx.send("Please provide the message to be sent:")
            message_response = await bot.wait_for('message', check=check, timeout=60.0)
            message = message_response.content

            async def send_message():
                await send_message_to_target(target, target_type, message, ctx)

            scheduler.add_job(send_message, 'date', run_date=date_time)
            await ctx.send(f"One-time message scheduled for {date_time}.")

        elif response.content == '2':  # Recurring schedule
            await ctx.send("You chose recurring. Please provide the target (user or role):")
            target_response = await bot.wait_for('message', check=check, timeout=60.0)
            target, target_type = get_user_or_role(ctx, target_response.content)

            if not target:
                await ctx.send(f"Couldn't find user or role with the name: {target_response.content}")
                return

            await ctx.send(
                "Please provide the start date, interval, and end date in the format: "
                "`2024-11-24 14:30 hours=24 2024-11-27 14:30`"
            )
            interval_response = await bot.wait_for('message', check=check, timeout=60.0)

            try:
                parts = interval_response.content.split()
                start_date_time = datetime.strptime(parts[0] + ' ' + parts[1], "%Y-%m-%d %H:%M")
                interval = parts[2]
                end_date_time = datetime.strptime(parts[3] + ' ' + parts[4], "%Y-%m-%d %H:%M")
                

                if "hours" in interval:
                    interval_kwargs = {"hours": int(interval.split('=')[1])}
                elif "minutes" in interval:
                    interval_kwargs = {"minutes": int(interval.split('=')[1])}
                else:
                    await ctx.send("Invalid interval format. Use `hours=24` or `minutes=60`.")
                    return

            except (ValueError, IndexError):
                await ctx.send("Invalid input format. Please follow the provided example.")
                return

            await ctx.send("Please provide the message to be sent:")
            message_response = await bot.wait_for('message', check=check, timeout=60.0)
            message = message_response.content

            async def send_message():
                await send_message_to_target(target, target_type, message, ctx)

            scheduler.add_job(
                send_message,
                'interval',
                start_date=start_date_time,
                end_date=end_date_time,
                **interval_kwargs
            )
            await ctx.send(
                f"Recurring message scheduled starting from {start_date_time} every {interval} until {end_date_time}."
            )
        else:
            await ctx.send("Invalid choice. Please type `1` or `2`.")
    except asyncio.TimeoutError:
        await ctx.send("You took too long to respond. Please try again.")


async def send_message_to_target(target, target_type, message, ctx):
    """
    Sends a message to a target. If the target is a role, sends the message to all members of the role.
    """
    if target_type == 'role':
        for member in target.members:
            if not member.bot:  # Skip bot accounts
                try:
                    await member.send(message)
                except discord.Forbidden:
                    await ctx.send(f"Could not send message to {member.name} (DMs might be closed).")
                except discord.HTTPException as e:
                    await ctx.send(f"Failed to send message to {member.name} due to an error: {e}")
    else:
        try:
            await target.send(message)
            await ctx.send(f"Message sent to {target.name}.")
        except discord.Forbidden:
            await ctx.send(f"Could not send message to {target.name} (DMs might be closed).")
        except discord.HTTPException as e:
            await ctx.send(f"Failed to send message to {target.name} due to an error: {e}")




# @bot.command(name='send')
# @commands.has_permissions(administrator=True)
# async def send_message(ctx, identifier: str, *, message: str):
#     """Send an immediate message to a user or all members with a specific role."""
#     target, target_type = get_user_or_role(ctx, identifier)
#     if not target:
#         await ctx.send(f"Couldn't find user or role with the name: {identifier}")
#         return

#     if target_type == 'role':
#         for member in target.members:
#             try:
#                 await member.send(message)
#             except discord.Forbidden:
#                 await ctx.send(f'Could not send message to {member.name}.')
#     else:
#         try:
#             await target.send(message)
#             await ctx.send(f'Message sent to {target.name}.')
#         except discord.Forbidden:
#             await ctx.send(f'Could not send message to {target.name}.')

# @tasks.loop(seconds=30)
# async def send_scheduled_messages():
#     now = datetime.now()
#     for i, (target_id, is_role, message, next_send_time, interval) in enumerate(scheduled_messages):
#         print(f"Checking scheduled message for target ID {target_id} (is_role: {is_role}) at {now}")

#         if now >= next_send_time:
#             if is_role:
#                 role = discord.utils.get(bot.get_guild(GUILD_TOKEN).roles, id=target_id)
#                 if role:
#                     print(f"Sending message to role: {role.name}")

#                     for member in role.members:
#                         try:
#                             await member.send(message)
#                             print(f"Sent message to {member.name}")
#                         except discord.Forbidden:
#                             print(f"Could not send message to {member.name}.")
#             else:
#                 user = bot.get_user(target_id)
#                 if user:
#                     try:
#                         await user.send(message)
#                         print(f"Sent message to {user.name}")
#                     except discord.Forbidden:
#                         print(f"Could not send message to {user.name}.")
#                 else:
#                     print(f"User with ID {target_id} not found.")

#             # Update the next_send_time for the scheduled message
#             scheduled_messages[i] = (target_id, is_role, message, now + timedelta(minutes=interval), interval)
#             print(f"Rescheduled message for target ID {target_id} to send at {now + timedelta(minutes=interval)}")

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
        while True:
            await user.send(question)
            def check(m):
                return m.author == user and isinstance(m.channel, discord.DMChannel)
            response = await bot.wait_for('message', check=check)
            try:
                value = int(response.content)
                if 1 <= value <= 10:
                    user_responses[user.id].append((question, response.content))
                    break
                else:
                    await user.send("Please enter a valid integer between 1 and 10.")
            except ValueError:
                await user.send("Please enter a valid integer between 1 and 10.")

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
    folder = 'thermometer_responses'
    os.makedirs(folder, exist_ok=True)
    filename = os.path.join(folder, f'{user_id}.json')
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

@bot.command(name='my_temps')
async def get_responses(ctx):
    folder = 'thermometer_responses'
    user_id = ctx.author.id
    filename = os.path.join(folder, f'{user_id}.json')
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            data = json.load(f)

        # Extract responses for plotting
        response_numbers = []
        function_scores = []
        elegance_scores = []
        effort_scores = []
        resources_list = []

        for entry in data:
            response_numbers.append(entry["response_number"])
            for question, response in entry["responses"]:
                if "Function" in question:
                    function_scores.append(int(response))
                elif "Elegance" in question:
                    elegance_scores.append(int(response))
                elif "Effort" in question:
                    effort_scores.append(int(response))
                elif "Resources" in question:
                    resources_list.append(response)

        # Create the plot
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=response_numbers, y=function_scores, mode='lines+markers', name='Function'))
        fig.add_trace(go.Scatter(x=response_numbers, y=elegance_scores, mode='lines+markers', name='Elegance'))
        fig.add_trace(go.Scatter(x=response_numbers, y=effort_scores, mode='lines+markers', name='Effort'))

        fig.update_layout(title='Thermometer Responses',
                          xaxis_title='Response Number',
                          yaxis_title='Score',
                          legend_title='Questions')

        # Save the plot as an image
        image_path = os.path.join(folder, f'{user_id}_plot.png')
        pio.write_image(fig, image_path)

        # Prepare resources text
        resources_text = "\n\n".join([f"Response {i+1}:\n" + "\n".join(resources) for i, resources in enumerate(resources_list)])

        # Send the plot as an embed
        file = discord.File(image_path, filename=f'{user_id}_plot.png')
        embed = discord.Embed(title="Your Thermometer Data")
        embed.set_image(url=f'attachment://{user_id}_plot.png')
        embed.add_field(name="Resources", value=resources_text if resources_text else "No resources provided", inline=False)
        await ctx.author.send(embed=embed, file=file)
    else:
        await ctx.author.send("You have no recorded responses.")


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