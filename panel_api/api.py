import os
import requests
import json
from os.path import join, dirname
from dotenv import dotenv_values
from requests.structures import CaseInsensitiveDict

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
server_url = config['get_server_url']

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

server_list = serverList(server_url, auth)

#if server_list:
#     print(server_list)                                   #print this line to view as dict
#    print(json.dumps(server_list, indent=4))             #print this line for json formatting
#else:
#    print('Connection Error, Status Code: ' + server_list)

def serverData():
    server_data = {}
    if server_list:
        for server in server_list['data']:
            attributes = server['attributes']
            name = attributes['name']
            uuid = attributes['uuid']
            identifier = attributes['identifier']
            port = server['attributes']['relationships']['allocations']['data'][0]['attributes']['port']
            server_data[f'{name}'] = {'identifier': f'{identifier}', 'uuid': f'{uuid}', 'port': f'{port}'}
        return server_data
    else:
        return []

server_data = serverData()

def generateWsUrl():
    ws_urls = []
    for k, v in server_data.items():
        id = v['identifier']
        ws_urls.append(f'{server_url}/servers/{id}/websocket')
    return ws_urls

def generateToken(endpoint, headers):
    response = requests.request('GET', endpoint, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        return str(response.status_code)

print("Token's Generated.")
print('----------------------')

def tokenData():
    token_data = []
    my_data = []
    for urls in generateWsUrl():
        token_data.append(generateToken(urls, auth))
    for dict in token_data:
        for k, v in dict.items():
            data = {}
            url = v['socket']
            guid = url.split('/')[5]
            token = v['token']
            data[f'{guid}'] = token
            my_data.append(data)
    return my_data

def find_key(d, value):
    for k,v in d.items():
        if isinstance(v, dict):
            p = find_key(v, value)
            if p:
                return k
        elif v == value:
            return k


def getServerNameFromId():
    uuid = []
    for k, v in server_data.items():    
            uuid.append(v['uuid'])      
    for dict in tokenData():
        for k, v in dict.items():
            if k in uuid:
                token ={'token': v}
                x = uuid.index(k)
                y = uuid[x]
                name = find_key(server_data, y)
                data = {'token': f'{token}'}
                for name in server_data:
                        server_data[f'{name}'].update(token)
    return server_data

# next steps are as follows, may not be in order
# a) create a websocket call and determine if server is on or off. - update server details with status
# b) if server on take port and pass it to the bot to work with checking the server state.
# c) create functionality to post node and server states in discord.
# d) create flags to handle starting the Instance and the server flagged
# e) stop function to stop server then the instance
# f) notifications every 2 hours on node uptime
# g) server uptime & node uptime calculations
# h) investigate discord bot gui to do these actions without needing to type commands in dc chat.. 

print(getServerNameFromId())
            
        












