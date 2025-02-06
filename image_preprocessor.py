import json
import cv2
import pytesseract
import os
from difflib import get_close_matches
import subprocess
from playwright.async_api import async_playwright
import asyncio
import time
import http
import http.client
import urllib.parse
import urllib
import numpy as np
from config import DUBCLUB_PHONE_NUMBER, PUSHOVER_API_TOKEN, GROUP_KEY


def send_pushover_notification(title, message):
    conn = http.client.HTTPSConnection("api.pushover.net:443")
    try:
        conn.request("POST", "/1/messages.json",
        urllib.parse.urlencode({
            "token": PUSHOVER_API_TOKEN,
            "user": GROUP_KEY,
            "message": message,
            "title": title,
        }), { "Content-type": "application/x-www-form-urlencoded" })
        conn.getresponse()
    except:
        print("Failed")

def generate_request(results_dict, x_csrf_token, body_token):
    picks = ",".join([
        f'{{\\"line_score\\":{line_score[0]},\\"wager_type\\":\\"{line_score[1]}\\",\\"projection_id\\":\\"{projection_id}\\",\\"prediction_source\\":\\"board\\",\\"source_data\\":\\"\\"}}'
        for projection_id, line_score in results_dict.items()
    ])

    fetch_request = f"""
fetch("https://api.prizepicks.com/wagers", {{
  "headers": {{
    "accept": "application/json",
    "accept-language": "en-US,en;q=0.9",
    "content-type": "application/json",
    "priority": "u=1, i",
    "sec-ch-ua": "\\"Not/A)Brand\\";v=\\"8\\", \\"Chromium\\";v=\\"126\\", \\"Google Chrome\\";v=\\"126\\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\\"macOS\\"",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "x-csrf-token": "{x_csrf_token}",
    "x-device-id": "f70bf701-3e76-4f83-ac17-e15ab607a805",
    "x-device-info": "name=,os=mac,osVersion=10.15.7,isSimulator=false,platform=web,appVersion=web"
  }},
  "referrer": "https://app.prizepicks.com/",
  "referrerPolicy": "strict-origin-when-cross-origin",
  "body": "{{\\"game_mode\\":\\"pickem\\",\\"new_wager\\":{{\\"amount_bet_cents\\":500,\\"picks\\":[{picks}],\\"pick_protection\\":false,\\"device_library\\":\\"js\\",\\"device_platform\\":\\"web\\",\\"tailed_entry_id\\":\\"\\",\\"is_exact\\":false}},\\"lat\\":null,\\"lng\\":null,\\"token\\":\\"{body_token}\\"}}",
  "method": "POST",
  "mode": "cors",
  "credentials": "include"
}});
"""
    return fetch_request.strip()

def generate_share_link_request(wager_id, results_dict):
    projections = []
    
    for projection_id, line_score in results_dict.items():
        projection_str = f'\\"{projection_id}-{line_score[1][0]}-{line_score[0]}\\"'
        projections.append(projection_str)

    # Join the projections into a single string
    projections_str = ','.join(projections)
    
    # Construct the fetch request
    share_link_request = f"""
fetch("https://api.prizepicks.com/payload_hashes", {{
  "headers": {{
    "accept": "application/json",
    "accept-language": "en-US,en;q=0.9",
    "content-type": "application/json",
    "priority": "u=1, i",
    "sec-ch-ua": "\\"Not/A)Brand\\";v=\\"8\\", \\"Chromium\\";v=\\"126\\", \\"Google Chrome\\";v=\\"126\\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\\"macOS\\"",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site"
  }},
  "referrer": "https://app.prizepicks.com/",
  "referrerPolicy": "strict-origin-when-cross-origin",
  "body": "{{\\"payload\\":{{\\"projections\\":[{projections_str}],\\"invite_code\\":\\"PR-2YJ29QH\\",\\"wager_id\\":\\"{wager_id}\\"}}}}",
  "method": "POST",
  "mode": "cors",
  "credentials": "include"
}});
    """
    return share_link_request.strip()

def get_projection_id(player_name, stat_type, lookup_dict):
    player_name = player_name.lower()
    idx = 0
    for char in stat_type:
        if char.isdigit() or char == '.' or char == ' ':
            idx += 1
        else:
            break
    stat_type = stat_type[idx:]

    # Find the closest match for the player name
    player_names = list(lookup_dict.keys())
    closest_player_match = get_close_matches(player_name, player_names, n=1)
    
    if closest_player_match:
        closest_player_name = closest_player_match[0]
        possible_stat_types = list(lookup_dict[closest_player_name].keys())
        
        # Find the closest match for the stat type
        closest_stat_match = get_close_matches(stat_type, possible_stat_types, n=1)
        
        if closest_stat_match:
            matched_stat = closest_stat_match[0]
            return lookup_dict[closest_player_name][matched_stat]["projection_id"]
    
    return None

def get_line_score(player_name, stat_type, lookup_dict):
    player_name = player_name.lower()
    idx = 0
    for char in stat_type:
        if char.isdigit() or char == '.' or char == ' ':
            idx += 1
        else:
            break
    stat_type = stat_type[idx:]

    # Find the closest match for the player name
    player_names = list(lookup_dict.keys())
    closest_player_match = get_close_matches(player_name, player_names, n=1)

    if closest_player_match:
        closest_player_name = closest_player_match[0]
        possible_stat_types = list(lookup_dict[closest_player_name].keys())

        # Find the closest match for the stat type
        closest_stat_match = get_close_matches(stat_type, possible_stat_types, n=1)

        if closest_stat_match:
            matched_stat = closest_stat_match[0]
            return lookup_dict[closest_player_name][matched_stat]["line_score"]

    return None


def preprocess_data(projection_filename):
    with open(projection_filename, 'r') as f:
        data = json.load(f)

    lookup_dict = {}
    players = {player['id']: (player['attributes']['display_name'] + player['attributes']['league'])for player in data['included'] if player['type'] == 'new_player'}

    for item in data['data']:
        if item['attributes']['adjusted_odds']:
            continue
        player_id = item['relationships']['new_player']['data']['id']
        stat_type = item['attributes']['stat_type'].lower()
        projection_id = item['id']
        line_score = item['attributes']['line_score']

        player_name = players[player_id].lower()
        stat_type = stat_type.replace(' ', '')
        
        if player_name not in lookup_dict:
            lookup_dict[player_name] = {}
        lookup_dict[player_name][stat_type] = {
            "projection_id": projection_id,
            "line_score": line_score
        }

    return lookup_dict

def extract_text_from_image(final_projection_path, results_dict):
    image = cv2.imread(final_projection_path)
    height, width, _ = image.shape
    
    player_name_roi = image[int(height * 0.0685):int(height * 0.2083), int(width * 0.27):int(width * 0.76)]
    stat_type_roi = image[int(height * 0.71):height, int(width * 0.27):int(width * 0.76)]
    league_roi = image[int(height * 0.25):int(height * 0.4), int(width * 0.27):int(width * 0.6)]
    more_button_roi = image[int(height * 0.375):int(height * 0.67), int(width * 0.76):int(width * 0.95)]
    less_button_roi = image[int(height * 0.67):int(height * 0.94), int(width * 0.76):int(width * 0.95)]
    more = np.mean(more_button_roi) > np.mean(less_button_roi)
    
    player_name = pytesseract.image_to_string(player_name_roi, config='--psm 7').strip()
    stat_type_unprocessed = pytesseract.image_to_string(stat_type_roi, config='--psm 7').strip()
    league_unprocessed = pytesseract.image_to_string(league_roi, config='--psm 7').strip()

    
    stat_type = ''
    stat_type_unprocessed = stat_type_unprocessed.replace(' ', '')
    i = len(stat_type_unprocessed) - 1
    while i > 0 and (stat_type_unprocessed[i - 1] != '.'):
        stat_type = stat_type_unprocessed[i] + stat_type
        i -= 1
    
    stat_type = stat_type.strip()
    league_unprocessed = league_unprocessed.split(' ')[0]
    league = ''
    for char in league_unprocessed:
        if char.isalpha() or char.isdigit():
            league += char
    player_name = player_name + league
    projection_id = get_projection_id(player_name, stat_type, lookup_dict)
    line_score = get_line_score(player_name, stat_type, lookup_dict)
    
    print(f"Player Name: {player_name}, Stat Type: {stat_type}, Line Score: {line_score}, Projection ID: {projection_id}")

    if projection_id is not None:
        if more:
            results_dict[projection_id] = [line_score, 'over']
        else:
            results_dict[projection_id] = [line_score, 'under']

def crop_image_based_on_x(projection_path, template_path, cropped_folder, top_offset = 20, bottom_offset = 280):
    template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
    projection = cv2.imread(projection_path, cv2.IMREAD_GRAYSCALE)
    res = cv2.matchTemplate(projection, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    
    if max_val > 0.5:  # Threshold to ensure the 'X' is found
        x, y = max_loc
        h, w = template.shape

        # Calculate cropping coordinates
        top_crop = max(0, y - top_offset)
        bottom_crop = min(projection.shape[0], y + h + bottom_offset)

        # Crop the projection
        cropped_projection = projection[top_crop:bottom_crop, :]
        cropped_projection_image_path = os.path.join(cropped_folder, f'{os.path.splitext(os.path.basename(projection_path))[0]}_cropped_.png')

        cv2.imwrite(cropped_projection_image_path, cropped_projection)
    
    else:
        cropped_projection_image_path = os.path.join(cropped_folder, f'{os.path.splitext(os.path.basename(projection_path))[0]}_cropped_.png')

        cv2.imwrite(cropped_projection_image_path, projection)
        print("X NOT FOUND")

def divide_projections(image_path, preprocessed_folder):
    image = cv2.imread(image_path)
    height, width, _ = image.shape
    num_projections = round(height // 400)
    projection_height = height // num_projections

    for i in range(num_projections):
        y_start = i * projection_height
        y_end = y_start + projection_height
        projection = image[y_start:y_end, 0:width]
        projection_image_path = os.path.join(preprocessed_folder, f'{os.path.splitext(os.path.basename(image_path))[0]}_projection_{i}.png')
        cv2.imwrite(projection_image_path, projection)

async def submit_slip_in_browser(page, request_js):
    # Intercept and log the response after submitting the request
    response = await page.evaluate(f"""
    (async () => {{
        const response = await {request_js};
        return response.json();  // Assuming the response is JSON
    }})()
    """)

    # Print out the response
    # print("Response from the request:", json.dumps(response, indent=2))
    return response['data']['id']

async def submit_share_link_request(page, request_js):
    response = await page.evaluate(f"""
    (async () => {{
        const response = await {request_js};
        return response.json();  // Assuming the response is JSON
    }})()
    """)

    # Print out the response
    # print("Response from the request:", json.dumps(response, indent=2))
    return response['data']['attributes']['uid']

def construct_share_link(entry_id):
    base_url = "https://prizepicks.onelink.me/gCQS/shareEntry"
    share_link = f"{base_url}?entryId={entry_id}"
    return share_link


async def preprocess_all_images_in_folder(folder_path, x_csrf_token, body_token):
    preprocessed_folder = os.path.join(folder_path, 'preprocessed')
    os.makedirs(preprocessed_folder, exist_ok=True)

    cropped_folder = os.path.join(folder_path, 'cropped')
    os.makedirs(cropped_folder, exist_ok=True)

    browser = await async_playwright().start()
    browser = await browser.chromium.connect_over_cdp("http://localhost:9222")
    context = browser.contexts[0]
    page = context.pages[0] if context.pages else await context.new_page()

    for filename in os.listdir(folder_path):
        try:
            clear_directory(preprocessed_folder)
            clear_directory(cropped_folder)
            if filename.endswith('.jpeg') or filename.endswith('.png') or filename.endswith('.jpg'):
                image_path = os.path.join(folder_path, filename)
                divide_projections(image_path, preprocessed_folder)
        
                template_path = 'template_x.png'
                for filename in os.listdir(preprocessed_folder):
                    if filename.endswith('.jpeg') or filename.endswith('.png') or filename.endswith('.jpg'):
                        projection_path = os.path.join(preprocessed_folder, filename)
                        crop_image_based_on_x(projection_path, template_path, cropped_folder)

                results_dict = {}
                for filename in os.listdir(cropped_folder):
                    if filename.endswith('.jpeg') or filename.endswith('.png') or filename.endswith('.jpg'):
                        final_projection_path = os.path.join(cropped_folder, filename)
                        extract_text_from_image(final_projection_path, results_dict)

                request = generate_request(results_dict, x_csrf_token, body_token)
                wager_id = await submit_slip_in_browser(page, request)
                share_link_request = generate_share_link_request(wager_id, results_dict)
                entry_id = await submit_share_link_request(page, share_link_request)
                share_link = construct_share_link(entry_id)
                send_pushover_notification("LINK", share_link)
        except Exception as e:
            print(f"Error creating link: {e}")


    await browser.close()

    clear_directory(folder_path)


def clear_directory(folder_path):
    for root, dirs, files in os.walk(folder_path, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))


subprocess.run(["python3", "prop_fetcher.py"], check=True)

# Example usage
folder_path = 'images'
projections_filename = 'fetched_props.json'
lookup_dict = preprocess_data(projections_filename)

x_csrf_token = ""
body_token = ""

# # Save the preprocessed data to a file
# with open('lookup_dict.json', 'w') as f:
#     json.dump(lookup_dict, f)

# # Load the preprocessed data
# with open('lookup_dict.json', 'r') as f:
#     lookup_dict = json.load(f)

subprocess.run(["python3", "dummy_slip_placer.py"], check=True)

# Add a short delay to ensure the file is written
time.sleep(1)

# Load the tokens from the file
try:
    with open("tokens.json", "r") as f:
        tokens = json.load(f)
        x_csrf_token = tokens["x_csrf_token"]
        body_token = tokens["body_token"]

except FileNotFoundError:
    print("tokens.json file not found. Please check if the tokens were captured correctly.")
    x_csrf_token = ""
    body_token = ""

asyncio.run(preprocess_all_images_in_folder(folder_path, x_csrf_token, body_token))
# Delete the token file after use
os.remove("tokens.json")