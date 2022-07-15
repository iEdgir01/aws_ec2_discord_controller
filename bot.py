import os, boto3, datetime
from discord.ext import commands
import aiosqlite
from functions import *

client = commands.Bot(command_prefix='.')
ec2 = boto3.resource('ec2')
guild = client.get_guild()
memberlist = guild.members
instances = list(ec2.instances.filter(Filters=[{'Name':'tag:guild', 'Values': [str(guild.id)]}]))

async def totaluptime(instance):
    current_date = datetime.datetime.now().strftime('%Y-%m-%d')
    uptime = []
    async with aiosqlite.connect('ec2bot.db') as db:
        async with db.cursor() as cursor:
            await cursor.execute('SELECT uptime FROM uptime WHERE date = ?', (current_date))
            uptime = await cursor.fetchall()
    totalUptime = datetime.timedelta()
    for i in uptime:
        (h, m, s) = i.split(':')
        d = datetime.timedelta(hours=int(h), minutes=int(m), seconds=int(float(s)))
        totalUptime += d
    return str(totalUptime)

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    if (client.user.id in memberlist and len(instances[0]) > 0):
        async with aiosqlite.connect('ec2bot.db') as db:
            async with db.cursor() as cursor:
                await cursor.execute('CREATE TABLE IF NOT EXISTS uptime (date TEXT, uptime TEXT)')
            await db.commit()
        print('database ready')
    else:
        print('Attempt to start bot by unrecognised guild ' + str(guild.id))
    print('------------')

@client.command()
async def ping(ctx):
    await ctx.send(f'Pong! latency:{round(client.latency * 1000)}ms')

@client.command()
async def start(ctx):
    if turnOnInstance(instances[0]):
        await ctx.send('Starting EC2 instance...')
    else:
        await ctx.send('Error starting EC2 instance')

@client.command()
async def stop(ctx):
    if (instanceState(instances[0]) == 'running'):
        if turnOffInstance(instances[0]):
            await ctx.send('Stopping EC2 instance... Session Time: ' + uptime(instances[0]))
            await turnOffInstance(instances[0])
            async with aiosqlite.connect('ec2bot.db') as db:
                async with db.cursor() as cursor:
                    await cursor.execute('INSERT INTO uptime VALUES (?, ?)', (datetime.datetime.now().strftime('%Y-%m-%d'), uptime(instances[0])))
                    await db.commit()
        else:
            await ctx.send('AWS Instance stopping failed')
    else:
        await ctx.send('AWS Instance state is: ' + instanceState(instances[0]))

@client.command()
async def reboot(ctx):
    if rebootInstance(instances[0]):
        await ctx.send('Rebooting EC2 instance...')
    else:
        await ctx.send('Error rebooting EC2 instance')

@client.command()
async def state(ctx):
    await ctx.send(f'AWS Instance state is: {instanceState(instances[0])}' )

@client.command()
async def uptime(ctx):
    await ctx.send(f'AWS Instance uptime is: {uptime(instances[0])}')

@client.command()
async def totaluptime(ctx):
    await ctx.send(f'AWS Instance total uptime is: {totaluptime(instances[0])}')

@client.command()
async def lrs(ctx):
    if isinstance(server_data, dict):
        if list_running_servers(server_data):
            await ctx.send(list_running_servers(server_data))
        else:
            await ctx.send('There are no running servers')
    else:
        await ctx.send(server_data)
        await ctx.send('AWS Instance state is: ' + instanceState(instances[0]))

@client.command()
async def list_servers(ctx):
    if isinstance(server_data, dict):
        await ctx.send(f'```\n{getServerState(server_data)}\n```')
    else:
        await ctx.send(server_data)
        await ctx.send('AWS Instance state is: ' + instanceState(instances[0]))

@client.command()
async def info(ctx):
    await ctx.send('commands: .ping, .stop, .start, .state, .reboot, .uptime, .totaluptime', '.lrs')

client.run(os.environ['AWSDISCORDTOKEN'])