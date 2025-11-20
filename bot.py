import os, boto3, datetime
import discord
import asyncio
import aiosqlite
from discord.ext import commands
from os.path import join, dirname
from dotenv import dotenv_values
from functions import *

# .env configuration
dotenv_path = join(dirname(__file__), '.env')
config = dotenv_values(dotenv_path)

#bot configuration
client = commands.Bot(command_prefix='.')
ec2 = boto3.resource('ec2')
guildid = config['guild_id']
db_path = config.get('DB_PATH', '/data/ec2bot.db')
instances = list(ec2.instances.filter(Filters=[{'Name':'tag:guild', 'Values': [guildid]}]))

if not instances:
    raise ValueError(f'No EC2 instances found with guild tag: {guildid}')

status = False

async def countdown(num_of_secs): 
        while num_of_secs > 0:
            if status == True:
                    break
            else:
                await asyncio.sleep(1)
                num_of_secs -= 1
        return True

async def totalup():
    current_date = datetime.datetime.now().strftime('%Y-%m-%d')
    uptime = []
    async with aiosqlite.connect(db_path) as db:
        async with db.cursor() as cursor:
            await cursor.execute('SELECT uptime FROM uptime WHERE date = ?', (current_date,))
            uptime = await cursor.fetchall()
            print(uptime)
    totalUptime = datetime.timedelta()
    for i in uptime:
        (h, m, s) = i[0].split(':')
        d = datetime.timedelta(hours=int(h), minutes=int(m), seconds=int(float(s)))
        totalUptime += d
    return str(totalUptime)

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('Acting on ' + str(instances[0]) + ' (' + str(len(instances)) + ' matching instances)')
    async with aiosqlite.connect(db_path) as db:
        async with db.cursor() as cursor:
            await cursor.execute('CREATE TABLE IF NOT EXISTS uptime (date TEXT, uptime TEXT)')
        await db.commit()
    print('database ready')
    print('-------------------------')

@client.command()
async def info(ctx):
    async with ctx.typing():
        server_data = serverState(generateResourcesURL())
        if instanceState(instances[0]) == 'running':
            embed = discord.Embed(title='EC2 Bot Info', description='Server and Instance display', color=0x03fcca)
            embed.add_field(name='instance status', value = instanceState(instances[0]), inline=False)
            embed.add_field(name='instance IP', value = get_instance_ip(instances[0]), inline=True)
            embed.add_field(name='instance uptime', value = await totalup(), inline=True)
            embed.add_field(name='server status', value = f'```\n{getServerState(server_data)}\n```', inline=False)
            embed.set_footer(text= 'Commands: .info, .ping, .start, .stop, .state, .lrs')
        else:
            embed = discord.Embed(title='EC2 Bot Info', description='Server and Instance display', color=0x03fcca)
            embed.add_field(name='instance status', value = instanceState(instances[0]), inline=False)
            embed.add_field(name='instance IP', value = get_instance_ip(instances[0]), inline=True)
            embed.add_field(name='instance uptime', value = await totalup(), inline=True)
            embed.set_footer(text= 'Commands: .info, .ping, .start, .stop, .state, .lrs')
    await ctx.send( embed=embed)

@client.command()
async def ping(ctx):
    await ctx.send(f'Pong! latency: {round(client.latency * 1000)}ms')

@client.command()
async def start(ctx):
    global status
    if (instanceState(instances[0]) != 'running'):
        try:
            turnOnInstance(instances[0])
            await ctx.send('Starting EC2 instance...')
            status = False
            count = 1
            countdowntime = 3600
            while countdowntime > 0:
                if await countdown(countdowntime):
                    if instanceState(instances[0]) == 'running':
                        await ctx.send(f'EC2 instance is on and {count}{" hours" if count != 1 else " hour"} has passed.')
                        count += 1
                        countdowntime = 3600
                    else:
                        break
        except Exception as e:
            print(f'Error starting instance: {e}')
            await ctx.send(f'Error starting EC2 instance: {str(e)}')
    else:
        await ctx.send('AWS Instance state is: ' + instanceState(instances[0]))

@client.command()
async def stop(ctx):
    global status
    if (instanceState(instances[0]) == 'running'):
        try:
            turnOffInstance(instances[0])
            status = True
            await ctx.send('Stopping EC2 instance... Session Time: ' + str(up(instances[0])))
            async with aiosqlite.connect(db_path) as db:
                async with db.cursor() as cursor:
                    await cursor.execute('INSERT INTO uptime VALUES (?, ?)', (datetime.datetime.now().strftime('%Y-%m-%d'), up(instances[0])))
                    await db.commit()
        except Exception as e:
            print(f'Error stopping instance: {e}')
            await ctx.send(f'AWS Instance stopping failed: {str(e)}')
    else:
        await ctx.send('AWS Instance state is: ' + instanceState(instances[0]))

@client.command()
async def state(ctx):
    await ctx.send(f'AWS Instance state is: {instanceState(instances[0])}')

@client.command()
async def totaluptime(ctx):
    uptime = await totalup()
    await ctx.send(f'AWS Instance total uptime is: {str(uptime)}')

@client.command()
async def lrs(ctx):
    async with ctx.typing():
        server_data = serverState(generateResourcesURL())
    if instanceState(instances[0]) == 'running':
        if list_running_servers(server_data):
            await ctx.send(list_running_servers(server_data))
        else:
            await ctx.send('There are no running servers')
    else:
        print(server_data)
        await ctx.send('AWS Instance state is: ' + instanceState(instances[0]))
        
client.run(os.environ['AWSDISCORDTOKEN'])