import time
import json
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import random

# Function to fetch and store data with retry logic
def fetch_and_store_data(url, filename, cookies, headers, retries=5, delay=0.1):
    session = requests.Session()

    for cookie in cookies:
        session.cookies.set(cookie['name'], cookie['value'])

    for attempt in range(1, retries + 1):
        try:
            response = session.get(url, headers=headers)
            response.raise_for_status()

            data = response.json()
            with open(filename, 'w') as f:
                json.dump(data, f, indent=4)
            # print(f"Data fetched and stored in {filename}")
            break  # Break the loop if the request is successful

        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err} (Attempt {attempt}/{retries})")
        except requests.exceptions.RequestException as err:
            print(f"Request error occurred: {err} (Attempt {attempt}/{retries})")
        except json.JSONDecodeError as json_err:
            print(f"JSON decode error: {json_err} (Attempt {attempt}/{retries})")

        if attempt < retries:
            print(f"Retrying in {delay} seconds...")
            time.sleep(delay)
        else:
            print("Max retries reached. Failed to fetch the data.")

# Function to preprocess data and create lookup dictionary
def preprocess_data(projection_filename):
    with open(projection_filename, 'r') as f:
        data = json.load(f)

    lookup_dict = {}
    players = {player['id']: player['attributes']['display_name'] for player in data['included'] if player['type'] == 'new_player'}

    for item in data['data']:
        player_id = item['relationships']['new_player']['data']['id']
        stat_type = item['attributes']['stat_type'].lower()
        projection_id = item['id']
        line_score = item['attributes']['line_score']

        player_name = players[player_id].lower()
        
        if player_name not in lookup_dict:
            lookup_dict[player_name] = {}
        lookup_dict[player_name][stat_type] = {
            "projection_id": projection_id,
            "line_score": line_score
        }

    return lookup_dict

# Function to get projection ID and line score
def get_projection_details(player_name, stat_type, lookup_dict):
    player_name = player_name.lower()
    stat_type = stat_type.lower()

    if player_name in lookup_dict and stat_type in lookup_dict[player_name]:
        return lookup_dict[player_name][stat_type]
    
    return None

if __name__ == "__main__":
    url = 'https://api.prizepicks.com/projections'
    headers = {
    'Accept': 'application/json',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Accept-Language': 'en-US,en;q=0.9',
    'Content-Type': 'application/json',
    'Origin': 'https://app.prizepicks.com',
    'Referer': 'https://app.prizepicks.com/',
    'Sec-Ch-Ua': '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"macOS"',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-site',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    'X-Device-Id': 'f70bf701-3e76-4f83-ac17-e15ab607a805',
    'X-Device-Info': 'name=,os=mac,osVersion=10.15.7,isSimulator=false,platform=web,appVersion=web'
}

    cookies = [
    {'name': 'rl_anonymous_id', 'value': '10f232a5-424c-4cf4-bc77-b22fe7b44ed9'},
    {'name': 'rl_page_init_referrer', 'value': '$direct'},
    {'name': '_pxvid', 'value': 'faa54dea-3b41-11ef-b0a4-d0a88b86ae97'},
    {'name': '__pxvid', 'value': 'ff23ca10-3b41-11ef-a1d4-0242ac120003'},
    {'name': 'intercom-device-id-qmdeaj0t', 'value': '62ca9b2d-45b7-495f-8ee8-c6ca37f77270'},
    {'name': 'ajs_anonymous_id', 'value': '10f232a5-424c-4cf4-bc77-b22fe7b44ed9'},
    {'name': 'ajs_user_id', 'value': '74327ff3-8bd6-49ac-a0e1-9ccbe06e193b'},
    {'name': 'cf_clearance', 'value': 'yzUIs7RTIJXPOYpaQOV.IVqdGcjaerRQtp4uXESBrpg-1723141720-1.0.1.1-w6sf03_Sd9qXbuHoXYTHOUYXJNUCCNifvwAlQbbFmpwVwPz8TPs50fOsqNy38vp3o6bh3ANI34azctpaWUWnJA'},
    {'name': 'intercom-id-qmdeaj0t', 'value': 'ce92c075-ee5d-4313-bf2d-ec8e29384182'},
    {'name': 'intercom-session-qmdeaj0t', 'value': ''},
    {'name': 'remember_user_token', 'value': 'eyJfcmFpbHMiOnsibWVzc2FnZSI6Ilcxc3hNVFEzT0RBNU9WMHNJaVF5WVNReE1TUlZNWGhVU2xWRlkyeFRNVlZyWTB0VWJUWnpiMVV1TURreFptSXdaak5rTW1GaVl6bGxOV001WW1Zd05HRmxPR0kzT0RrM1l6RWlMQ0l4TnpJek1UUXlNRGcwTGpJd01EZzNOalVpWFE9PSIsImV4cCI6IjIwMjQtMDgtMjJUMTg6MzQ6NDQuMjAwWiIsInB1ciI6ImNvb2tpZS5yZW1lbWJlcl91c2VyX3Rva2VuIn19--98240370df29b605fce6e200cf9cd4373cff4b7e'},
    {'name': 'rl_user_id', 'value': '74327ff3-8bd6-49ac-a0e1-9ccbe06e193b'},
    {'name': 'rl_trait', 'value': '{"id":"74327ff3-8bd6-49ac-a0e1-9ccbe06e193b","address":"41447 Carmen St","amount_won":547.5,"bonus":null,"city":"Fremont","confirmed_at":"2024-07-22T20:27:42-04:00","country_code":"US","created_at":"2024-07-22T20:24:16-04:00","credit":1342.5,"date_of_birth":"2005-07-20T00:00:00-04:00","default_entry_amount":null,"default_entry_type":null,"deposited_amount":1000,"device_vibration":true,"email":"danielgongprizepicks@gmail.com","entries_won":4,"first_name":"Daniel","ftd_promo_type":"DepositMatch","full_name":"Daniel Gong","has_confirmed_phone_number":null,"idology_validation_state":"pending","internal_validation_state":"pending","invite_code":"BESTOFFER","is_rotogrinders":null,"last_agreed_to_terms_at":"2024-07-22T20:24:16-04:00","last_entry_created_at":"2024-08-08T12:25:11Z","last_name":"Gong","notifications":false,"number_of_entries":6,"otp_status":"withdrawal_only","payment_service":"nuvei","phone_number":null,"postal_code":"94539","promo":5,"push_notification_token":null,"referral_code":"PR-2YJ29QH","require_kyc_selfie":false,"role":null,"show_balance":true,"sms_opt_in":false,"socure_validation_state":"passed","state":"CA","terms_accepted":true,"updated_at":"2024-08-08T14:34:44-04:00","validation_provider":"socure","validation_state":"passed","verification_image":null,"verification_image_reviewed":false,"verified":true,"withdrawable_credit":0,"bonus_offer":null,"free_entries":[],"customerDashLink":"https://api.prizepicks.com/admin/users/74327ff3-8bd6-49ac-a0e1-9ccbe06e193b","prize_points":1000,"weekly_prize_points":1000}'},
    {'name': '__cf_bm', 'value': 'gZi_7HavLDe.zPuH5.zhx5ne2NBTs8KXRccA5QKMqso-1723142604-1.0.1.1-th.1nFVOtp1sDdDsDVeBVdHPo40bWhS6Un6Ca81dqiNVgK6VBkRdw5KLH3btCJK0XGgIrafokZ3JsWgrFrNj2A'},
    {'name': '_cfuvid', 'value': 'cWY1ymTOoFS_ZZqacNvSyUHHVxOxDK2hGS61TuYv88E-1723142604109-0.0.1.1-604800000'},
    {'name': 'pxcts', 'value': '182bdb3a-55b6-11ef-8041-dbeb24a1095b'},
    {'name': 'CSRF-TOKEN', 'value': 'sEUAMFRR2B0ItVElMbM2MIqx50qLWWWG_Ulii9ZscF_4qtyaNx94PyTNOOFzR-pQ-Aski4oC3XwbhORg0Pk9yg'}
    ]

    fetch_and_store_data(url, 'fetched_props.json', cookies, headers)

    # Preprocess the data
    projection_filename = 'fetched_props.json'
    lookup_dict = preprocess_data(projection_filename)
    
    # Save the preprocessed data to a file
    with open('lookup_dict.json', 'w') as f:
        json.dump(lookup_dict, f)

    # Load the preprocessed data
    with open('lookup_dict.json', 'r') as f:
        lookup_dict = json.load(f)