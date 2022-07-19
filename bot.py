import os, boto3, datetime
import discord
from discord.ext import commands
import aiosqlite
from functions import *

client = commands.Bot(command_prefix='.')
ec2 = boto3.resource('ec2')
guildid = str(466315445905915915)
instances = list(ec2.instances.filter(Filters=[{'Name':'tag:guild', 'Values': [guildid]}]))

async def totalup():
    current_date = datetime.datetime.now().strftime('%Y-%m-%d')
    uptime = []
    async with aiosqlite.connect('/home/ec2bot/ec2bot.db') as db:
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
    async with aiosqlite.connect('ec2bot.db') as db:
        async with db.cursor() as cursor:
            await cursor.execute('CREATE TABLE IF NOT EXISTS uptime (date TEXT, uptime TEXT)')
        await db.commit()
    print('database ready')
    print('-------------------------')

@client.command()
async def info(ctx):
    async with ctx.typing():
        if instanceState(instances[0]) == 'running':
            embed = discord.Embed(title='EC2 Bot Info', description='Server and Instance display', color=0x03fcca)
            embed.add_field(name='instance status', value = instanceState(instances[0]), inline=False)
            embed.add_field(name='instance IP', value = get_instance_ip(instances[0]), inline=True)
            embed.add_field(name='instance uptime', value = await totalup(), inline=True)
            embed.add_field(name='server status', value = f'```\n{getServerState(server_data)}\n```', inline=False)
            embed.set_footer(text= 'Commands: .info, .ping, .state, .start, .stop, .uptime, .totaluptime, .servers, .lrs')
        else:
            server_data = serverState(generateResourcesURL())
            embed = discord.Embed(title='EC2 Bot Info', description='Server and Instance display', color=0x03fcca)
            embed.add_field(name='instance status', value = instanceState(instances[0]), inline=False)
            embed.add_field(name='instance IP', value = get_instance_ip(instances[0]), inline=True)
            embed.add_field(name='instance uptime', value = await totalup(), inline=True)
            embed.set_footer(text= 'Commands: .info, .ping, .start, .stop, .lrs')
    await ctx.send( embed=embed)

@client.command()
async def ping(ctx):
    await ctx.send(f'Pong! latency: {round(client.latency * 1000)}ms')

@client.command()
async def start(ctx):
    try:
        turnOnInstance(instances[0])
        await ctx.send('Starting EC2 instance...')
    except Exception as e:
        print(e)
        await ctx.send('Error starting EC2 instance...')

@client.command()
async def stop(ctx):
    if (instanceState(instances[0]) == 'running'):
        if turnOffInstance(instances[0]):
            await ctx.send('Stopping EC2 instance... Session Time: ' + str(up(instances[0])))
            turnOffInstance(instances[0])
            async with aiosqlite.connect('ec2bot.db') as db:
                async with db.cursor() as cursor:
                    await cursor.execute('INSERT INTO uptime VALUES (?, ?)', (datetime.datetime.now().strftime('%Y-%m-%d'), up(instances[0])))
                    await db.commit()
        else:
            await ctx.send('AWS Instance stopping failed')
    else:
        await ctx.send('AWS Instance state is: ' + instanceState(instances[0]))

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