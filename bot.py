import discord, asyncio, os, boto3, socket, traceback
import subprocess
import datetime
from api import serverState
from os import popen
from os import path
from dateutil.parser import *


client = discord.Client()

ec2 = boto3.resource('ec2')

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------------')

@client.event
async def on_message(message):
    memberIDs = (member.id for member in message.mentions)
    instances = list(ec2.instances.filter(Filters=[{'Name':'tag:guild', 'Values': [str(message.channel.guild.id)]}]))
    print('Acting on ' + str(instances[0]) + ' (' + str(len(instances)) + ' matching instances)')
    # assume that there will never be more than one matching instance
    if (client.user.id in memberIDs and len(instances) > 0):
        if 'stop' in message.content:
            if turnOffInstance(instances[0]):
                await message.channel.send('AWS Instance stopping, Session Time: ' + uptime(instances[0]))
                current_date = datetime.datetime.now().strftime('%Y-%m-%d')
                uptimeAtStop = uptime(instances[0])
                with open(path.join("/home",  "ec2bot", "uptime.txt"), "a+") as f:
                    f.write(current_date + ", " + uptimeAtStop + "\n")
                    f.close()
            else:
                await message.channel.send('Error stopping AWS Instance')
        elif 'start' in message.content:
            if turnOnInstance(instances[0]):
                await message.channel.send('AWS Instance starting')
            else:
                await message.channel.send('Error starting AWS Instance')
        elif 'state' in message.content:
            await message.channel.send('AWS Instance state is: ' + getInstanceState(instances[0]))
        elif 'reboot' in message.content:
            if rebootInstance(instances[0]):
                await message.channel.send('AWS Instance rebooting')
            else:
                await message.channel.send('Error rebooting AWS Instance')
        elif 'info' in message.content:
            await message.channel.send('Server start/stop bot. Commands are `start`, `stop`, `state`, `reboot`, `uptime` and `info`')
        elif 'current uptime' in message.content:
            if (instanceState(instances[0]) == 'running'):
                await message.channel.send('AWS Instance uptime for the current session is: ' + uptime(instances[0]))
            else:
                await message.channel.send('AWS Instance state is: ' + getInstanceState(instances[0]))
        elif 'uptime' in message.content:
            await message.channel.send('AWS Instance uptime for the current day is: ' + totalUptime())
    else:
        print('Attempt to start bot by unrecognised guild ' + str(message.channel.guild.id))

def turnOffInstance(instance):
    try:
        instance.stop()
        return True
    except: 
        print(traceback.format_exc())
        return False

def turnOnInstance(instance):
    try:
        instance.start()
        return True
    except:
        print(traceback.format_exc())
        return False

def instanceState(instance):
    aws_state = instance.state
    return aws_state['Name']

def getInstanceState(instance):
    aws_state = instance.state
    if (aws_state['Name'] == 'running'):
        return getPortState(instance.public_ip_address, 25565)
    else:
        return aws_state['Name']

def getPortState(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3.0)
    ready = sock.connect_ex((ip, port))
    if ready == 0:
        return 'ready at ' + ip 
    else:
        return 'Startup in progress, Please wait.'

def rebootInstance(instance):
    try:
        instance.reboot()
        return True
    except:
        print(traceback.format_exc())
        return False

def uptime(instance):
    launch_time = instance.launch_time
    current_time = datetime.datetime.now(launch_time.tzinfo)
    launch_time_difference = current_time - launch_time
    return str(launch_time_difference)

def totalUptime():
    current_date = datetime.datetime.now().strftime('%Y-%m-%d')
    uptime = []
    with open(path.join("/home",  "ec2bot", "uptime.txt"), "rt") as text:
        for line in text.readlines():
            line = line.rstrip()
            if current_date in line.split(', ')[0]:
                uptime.append(line.split(', ')[1])
    text.close()
    totalUptime = datetime.timedelta()
    for i in uptime:
        (h, m, s) = i.split(':')
        d = datetime.timedelta(hours=int(h), minutes=int(m), seconds=int(float(s)))
        totalUptime += d    
    return str(totalUptime)

def getRunningPort():
    
    

client.run(os.environ['AWSDISCORDTOKEN'])
