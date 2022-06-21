from os.path import join, dirname
import json
import requests
from dotenv import dotenv_values

#.env configuration
dotenv_path = join(dirname(__file__), '.env')
config = dotenv_values(dotenv_path)

#api configuration
url = config['panel_url']
api = config['api']
accept_type = config['accept_type']
content_type = config['content_type']

#authorisation cofiguration
auth = {
    'Authorization': f'Bearer {api}',
    'Accept': accept_type,
    'content-type': content_type, 
}

#global actions
panel_url = config['get_server_url']

def statusCodeCheck(endpoint, headers):
    response = requests.get(endpoint, headers=headers)
    try:
        if response.status_code == 200:
            return True
    except:
        print(response.status_code)
        return False

if statusCodeCheck(url, auth):
    print('Connection Successful.')
    print('----------------------')
else:
   print('Connection Error.')

def serverList(endpoint, headers): 
    response = requests.request('GET', endpoint, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        return str(response.status_code)

server_list = serverList(panel_url, auth)

def serverData():
    server_data = {}
    if server_list:
        for server in server_list['data']:
            attributes = server['attributes']
            name = attributes['name']
            identifier = attributes['identifier']
            port = server['attributes']['relationships']['allocations']['data'][0]['attributes']['port']
            server_data[f'{name}'] = {'identifier': f'{identifier}', 'port': f'{port}'}
        return server_data
    else:
        return []

server_data = serverData()

def generateResourcesURL():
    ws_urls = []
    for k, v in server_data.items():
        id = v['identifier']
        ws_urls.append(f'{panel_url}/servers/{id}/resources')
    return ws_urls

def getServerStats(endpoint, headers):
    response = requests.request('GET', endpoint, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        return str(response.status_code)
    
def serverState(urls):
    for url in urls:
        id = url.split('/')[6]
        response = getServerStats(url, auth)
        state = response['attributes']['current_state']
        for k, v in server_data.items():
            guid = v['identifier']
            if id == guid:
                data = {'state': f'{state}'}
                server_data[f'{k}'].update(data)
    return server_data

server_data = serverState(generateResourcesURL())

def getRunningPort():
    for k, v in server_data.items():
        if v['state'] == 'running':
            port = v['port']
            name = k
            state = v['state']
            return port 

print(getRunningPort())    
# next steps are as follows, may not be in order
# a) get server status - done
# b) if server on take port and pass it to the bot to work with checking the server state.
# c) create functionality to post node and server states in discord.
# d) create flags to handle starting the Instance and the server flagged
# e) stop function to stop server then the instance
# f) notifications every 2 hours on node uptime
# g) server uptime & node uptime calculations - impliment with a database
# h) investigate discord bot gui to do these actions without needing to type commands in dc chat