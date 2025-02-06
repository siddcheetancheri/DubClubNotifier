import requests
import subprocess
import time
import http.client
import urllib.parse
import logging
import socket
import json
import asyncio
import random
import threading
import signal
import sys
import matplotlib.pyplot as plt
import uuid
import os
from globals import busy
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from threading import Thread, Event
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

from config import DUBCLUB_PHONE_NUMBER, PUSHOVER_API_TOKEN, GROUP_KEY

# Setup logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s:%(message)s',
                    handlers=[
                        logging.FileHandler('dubclub_notifier.log'),
                        logging.StreamHandler()
                    ])

# Global flags and metrics
exit_flag = False
total_data_sent = 0
total_data_received = 0
data_usage_timestamps = []

# Define headers once
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    'Accept': 'application/json',
    'Referer': 'https://dubclub.win/t/prd-ck8aj/',
    'Sec-Ch-Ua': '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"macOS"',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
}

# Custom HTTP Adapter to measure data usage
class DataUsageAdapter(requests.adapters.HTTPAdapter):
    def send(self, request, *args, **kwargs):
        global total_data_sent, total_data_received, data_usage_timestamps
        request_size = len(request.body) if request.body else 0
        total_data_sent += request_size
        response = super().send(request, *args, **kwargs)
        response_size = len(response.content)
        total_data_received += response_size
        data_usage_timestamps.append((datetime.now(), total_data_sent + total_data_received))
        return response

# Function to send a Pushover notification
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

# Function to login and retrieve cookies
def login_and_get_cookies(driver):
    try:
        driver.get("https://dubclub.win/r/subscriber-signin/")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "phone_input-0")))

        # Enter phone number and submit the form
        phone_input = driver.find_element(By.NAME, "phone_input-0")
        phone_input.send_keys(DUBCLUB_PHONE_NUMBER)
        phone_input.send_keys(Keys.RETURN)

        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "security_code")))

        # send_pushover_notification("DubClub Notifier", "Please login to DubClub manually.")

        # Enter the verification code
        verification_code = input("Enter the verification code sent to your phone: ")
        code_input = driver.find_element(By.NAME, "security_code")
        code_input.send_keys(verification_code)
        code_input.send_keys(Keys.RETURN)

        logging.info("Login successful.")
        cookies = driver.get_cookies()
        return cookies

    except (TimeoutException, WebDriverException) as e:
        logging.error(f"Error during login: {e}")

        # Check for internet connection
        try:
            socket.gethostbyname("www.google.com")
            # If we get here, the internet connection is fine, so retry login
            logging.info("Retrying login due to non-network error.")
            return login_and_get_cookies(driver)
        except socket.gaierror:
            # No internet connection
            logging.error("No internet connection. Unable to login.")
            send_pushover_notification("DubClub Notifier Error", "No internet connection. Unable to login.")
            return None
    except Exception as e:
        logging.error(f"Unexpected error during login: {e}")
        send_pushover_notification("DubClub Notifier Error", f"Unexpected error during login: {e}")
        return None

# Function to check for new posts
def check_for_new_posts(session, last_post_url):
    response = session.get("https://dubclub.win/api/prd-ck8aj/textpicks/?page=1", headers=headers)
    response.raise_for_status()
    posts = response.json()['results']

    if not posts:
        return None, last_post_url

    latest_post = posts[0]
    latest_post_url = latest_post['url']

    if last_post_url is None:
        return None, latest_post_url

    if latest_post_url != last_post_url:
        post_title = latest_post['sms_title']
        post_content = latest_post['message']

        return (post_title, post_content, latest_post_url), latest_post_url
    return None, last_post_url

# Function to handle clean exit
def signal_handler(sig, frame):
    global exit_flag
    print("\n")
    logging.info("Signal received, preparing to exit gracefully...")
    exit_flag = True

# Function to calculate and log data rate
def log_data_rate():
    global total_data_sent, total_data_received, data_usage_timestamps
    if len(data_usage_timestamps) > 1:
        start_time = data_usage_timestamps[0][0]
        end_time = data_usage_timestamps[-1][0]
        duration = (end_time - start_time).total_seconds() / 3600  # in hours
        total_data = total_data_sent + total_data_received
        data_rate = total_data / (1024 ** 3) / duration  # GB/hour
        sys.stdout.write(f"\rData rate: {data_rate:.2f} GB/hour")
        sys.stdout.flush()

# Function to generate data usage graph
def generate_data_usage_graph():
    global data_usage_timestamps
    times, data_usage = zip(*data_usage_timestamps)
    data_usage_gb = [d / (1024 ** 3) for d in data_usage]  # Convert bytes to GB

    plt.figure(figsize=(10, 5))
    plt.plot(times, data_usage_gb, label='Data Usage (GB)')
    plt.xlabel('Time')
    plt.ylabel('Data Usage (GB)')
    plt.title('Data Usage Over Time')
    plt.legend()
    plt.grid(True)
    plt.savefig('data_usage_graph.png')
    plt.show()

# Function to update data rate display
def update_data_rate_display(stop_event):
    while not stop_event.is_set():
        log_data_rate()
        time.sleep(5)

def clear_directory(folder_path):
    for root, dirs, files in os.walk(folder_path, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))

def download_images_from_url(session, url):
    try:
        clear_directory("images")
        response = session.get(url, allow_redirects=True)  # Follow redirects
        response.raise_for_status()

        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find the specified container
        container = soup.find('div', class_='text-start text-wrap text-break text-black markdown-container')
        if container:
            # Find all images within the container
            img_tags = container.find_all('img')
            if img_tags:
                for img_tag in img_tags:
                    if img_tag['src']:
                        img_url = img_tag['src']

                        # Ensure the image URL is complete
                        if not img_url.startswith('http'):
                            img_url = urljoin(url, img_url)

                        # Ensure the images directory exists
                        images_dir = 'images'
                        if not os.path.exists(images_dir):
                            os.makedirs(images_dir)

                        # Extract the image name from the URL, or generate a unique name
                        img_name = os.path.basename(img_url)
                        if not img_name:
                            img_name = f'image_{uuid.uuid4()}.jpg'  # Generate a unique filename

                        file_path = os.path.join(images_dir, img_name)

                        logging.info(f"Downloading image from: {img_url} to: {file_path}")

                        # Download and save the image
                        img_response = session.get(img_url)
                        img_response.raise_for_status()

                        # Ensure that the file_path points to a file, not a directory
                        if os.path.isdir(file_path):
                            raise Exception(f"File path is a directory, not a file: {file_path}")

                        with open(file_path, 'wb') as f:
                            f.write(img_response.content)

                        logging.info(f"Image saved: {file_path}")
            else:
                logging.info("No images found in the specified container.")
        else:
            logging.info("No container found with the specified class.")
    except Exception as e:
        logging.error(f"Failed to download images: {e}")
        print(f"Exception details: {e}")


# Main function
def main():
    global exit_flag

    # Set up signal handlers for clean exit
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Set up the Selenium WebDriver with Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")

    driver_path = ChromeDriverManager().install()
    print("Driver path returned by ChromeDriverManager:", driver_path)

    # Manually adjust the path to point to the chromedriver executable
    driver_directory = os.path.dirname(driver_path)
    executable_name = "chromedriver"  # or "chromedriver.exe" on Windows
    executable_path = os.path.join(driver_directory, executable_name)
    print("Executable path being used:", executable_path)

    # Ensure the executable has execute permissions
    os.chmod(executable_path, 0o755)

    # Initialize the driver
    service = ChromeService(executable_path=executable_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    last_post_url = None
    cookies = login_and_get_cookies(driver)

    driver.quit()
    if not cookies:
        logging.error("Failed to login and retrieve cookies. Exiting...")
        return

    session = requests.Session()
    session.mount('https://', DataUsageAdapter())
    for cookie in cookies:
        session.cookies.set(cookie['name'], cookie['value'])

    stop_event = Event()
    data_rate_thread = Thread(target=update_data_rate_display, args=(stop_event,))
    data_rate_thread.start()

    logging.info("Listening for new posts...")

    keywords = ["prizepicks", "pp"]

    while not exit_flag:
        try:
            new_post, last_post_url = check_for_new_posts(session, last_post_url)

            if new_post:
                sys.stdout.write("\n")  # Move to a new line before printing the new post log
                logging.info(f"New post detected: {new_post[0]}")
                send_pushover_notification(new_post[0], f"{new_post[1]}\n\nURL: https://dubclub.win{new_post[2]}")
                with busy.get_lock():
                    busy.value = True

                if any(keyword in new_post[0].lower() for keyword in keywords):
                    logging.info("Keyword detected in post title. Attempting to download the image...")
                    download_images_from_url(session, f"https://dubclub.win{new_post[2]}")
                    logging.info("Running image_preprocessor.py to place the slip and intercept tokens.")

                    subprocess.run(["python3", "image_preprocessor.py"], check=True)
                with busy.get_lock():
                    busy.value = False
            time.sleep(1)  # Adjust the interval as needed
        except Exception as e:
            logging.error(f"An error occurred: {e}")
            time.sleep(1)  # Wait before retrying

    # Stop the data rate thread and generate data usage graph upon exit
    stop_event.set()
    data_rate_thread.join()
    generate_data_usage_graph()

# Test function for downloading images with login
def test_main():
    # Set up signal handlers for clean exit
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Set up the Selenium WebDriver with Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)

    # Perform login and get cookies
    cookies = login_and_get_cookies(driver)
    driver.quit()

    if not cookies:
        logging.error("Failed to login and retrieve cookies. Exiting...")
        return

    # Set up a session and attach cookies
    session = requests.Session()
    session.mount('https://', DataUsageAdapter())
    for cookie in cookies:
        session.cookies.set(cookie['name'], cookie['value'])

    # Ask for the post URL to test
    post_url = input("Enter the post URL to test: ")
    
    # Mock the new_post data
    new_post = {
        'title': 'Test post for PrizePicks',
        'url': post_url
    }

    # Check if the post title contains any of the keywords
    keywords = ["prizepicks", "pp"]

    if any(keyword in new_post['title'].lower() for keyword in keywords):
        logging.info("Keyword detected in post title. Attempting to download the image...")
        download_images_from_url(session, post_url)
        logging.info("Running dummy_slip_placer.py to place the slip and intercept tokens.")

        # Run the combined dummy slip placer script with token interception
        subprocess.run(["python3", "dummy_slip_placer.py"], check=True)

    logging.info("Test completed. Exiting...")



if __name__ == "__main__":
    main()