from os.path import join, dirname
import requests
import sys
from dotenv import dotenv_values

# .env configuration
dotenv_path = join(dirname(__file__), '.env')
config = dotenv_values(dotenv_path)

# api configuration
url = config['panel_url']
api = config['api'] 
accept_type = config['accept_type']
content_type = config['content_type']

# authorisation configuration
auth = {
    'Authorization': f'Bearer {api}',
    'Accept': accept_type,
    'content-type': content_type,
}

# global actions
panel_url = config['get_server_url']

def status_code_check(endpoint, headers):
    try:
        response = requests.get(endpoint, headers=headers)
        return response
    except requests.exceptions.RequestException as err:
        return err

if status_code_check(url, auth):
    print('Connection Successful.')
    print('-------------------------')
else:
    print(f'Panel Connection Error: {status_code_check(url, auth)}')

def serverList(endpoint, headers):
    response = requests.request('GET', endpoint, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        return str(f'Request Exception Found: {requests.status_code}')

def serverData():
    server_list = serverList(panel_url, auth)
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

def generateResourcesURL():
    server_data = serverData()
    ws_urls = []
    for v in server_data.values():
        guid = v['identifier']
        ws_urls.append(f'{panel_url}/servers/{guid}/resources')
    return ws_urls

def getServerStats(endpoint, headers):
    response = requests.request('GET', endpoint, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        err = response.json()
        sys.tracebacklimit=0
        raise Exception(f"Please check instance state, Error Code: {err['errors'][0]['code']} - {err['errors'][0]['status']}: {err['errors'][0]['detail']}")

def serverState(urls):
    server_data = serverData()
    for url in urls:
        id = url.split('/')[6]
        try:
            response = getServerStats(url, auth)
        except Exception as e:
            return str(e)
        state = response['attributes']['current_state']
        for k, v in server_data.items():
            guid = v['identifier']
            if id == guid:
                data = {'state': state}
                server_data[k].update(data)
    return server_data

print('-------------------------')
# next steps are as follows
# d) create flags to handle starting the Instance and the server flagged
# e) stop function to stop server then the instance
# h) investigate discord bot gui to do these actions without needing to type commands in dc chat
