import requests
import json
from config import PUSHOVER_API_TOKEN, GROUP_KEY

BASE_URL = "https://api.pushover.net/1/groups"

def create_group(name):
    url = f"{BASE_URL}.json"
    payload = {
        'token': PUSHOVER_API_TOKEN,
        'name': name
    }
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        data = response.json()
        if data['status'] == 1:
            print(f"Group '{name}' created successfully with key: {data['group']}")
            return data['group']
    print(f"Failed to create group: {response.text}")
    return None

def retrieve_groups():
    url = f"{BASE_URL}.json"
    params = {
        'token': PUSHOVER_API_TOKEN
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        if data['status'] == 1:
            return data['groups']
    print(f"Failed to retrieve groups: {response.text}")
    return None

def get_group_info(group_key):
    url = f"{BASE_URL}/{group_key}.json"
    params = {
        'token': PUSHOVER_API_TOKEN
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    print(f"Failed to get group info: {response.text}")
    return None

def add_user_to_group(group_key, user_key, device=None, memo=None):
    url = f"{BASE_URL}/{group_key}/add_user.json"
    payload = {
        'token': PUSHOVER_API_TOKEN,
        'user': user_key,
        'device': device,
        'memo': memo
    }
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        data = response.json()
        if data['status'] == 1:
            print(f"User '{user_key}' added successfully to group '{group_key}'")
            return True
    print(f"Failed to add user to group: {response.text}")
    return False

def remove_user_from_group(group_key, user_key, device=None):
    url = f"{BASE_URL}/{group_key}/remove_user.json"
    payload = {
        'token': PUSHOVER_API_TOKEN,
        'user': user_key,
        'device': device
    }
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        data = response.json()
        if data['status'] == 1:
            print(f"User '{user_key}' removed successfully from group '{group_key}'")
            return True
    print(f"Failed to remove user from group: {response.text}")
    return False

def save_group_key(group_key):
    with open('config.py', 'r') as file:
        lines = file.readlines()

    with open('config.py', 'w') as file:
        for line in lines:
            if line.startswith("GROUP_KEY"):
                file.write(f"GROUP_KEY = '{group_key}'\n")
            else:
                file.write(line)

if __name__ == "__main__":
    add_user_to_group(GROUP_KEY, 'ucddx7o6w8hdfzaieepmuakw8k4q7z')

    # for user_info in get_group_info(GROUP_KEY)['users']:
    #     user = user_info['user']
    #     remove_user_from_group(GROUP_KEY, user)

    print(get_group_info(GROUP_KEY))