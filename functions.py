from api import *
import pandas as pd
import datetime

headers = ['Server Name', 'UUID', 'Port', 'State']

server_data = serverState(generateResourcesURL())

#ec2 functions
def turnOffInstance(instance):
        instance.stop()
        return True

def turnOnInstance(instance):
        instance.start()
        return True

def rebootInstance(instance):
        instance.reboot()
        return True

def instanceState(instance):
    aws_state = instance.state
    return aws_state['Name']

def get_instance_ip(instance):
    public_ip = instance.public_ip_address
    return public_ip

def uptime(instance):
    launch_time = instance.launch_time
    current_time = datetime.datetime.now(launch_time.tzinfo)
    launch_time_difference = current_time - launch_time
    return str(launch_time_difference)

def dataframe(data):
    try:
        df = pd.DataFrame.from_dict(data).T
        return df
    except Exception as e:
        return str(e)

# panel functions
def get_server_statuses(data):
    try:
        server_status = []
        for k, v in data.items():
            if v['state'] == 'running':
                server_status.append(True)
            elif v['state'] == 'offline':
                server_status.append(False)
        serverstate = set(server_status)
        return serverstate
    except Exception as e:
        return str(e)

server_s = get_server_statuses(server_data)

def list_running_servers(data):
    running_servers = []
    for k, v in data.items():
        if v['state'] == 'running':
            running_servers.append(k)
    return running_servers

def server_details(dataframe):
    pretty_data = dataframe.to_markdown(headers=headers, tablefmt='psql')
    return pretty_data

def getServerState(status):
    if True in status:
        return server_details(dataframe(server_data))
    else:
        return f"There are no running servers"