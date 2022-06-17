import os
import json
import requests
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
    'content-type': content_type, 
}

#global actions
server_url = config['get_server_url']






