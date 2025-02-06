'''
<div id="uAYilcnqPlxmNhF" class="UcjTWZDVAJARQAH" tabindex="0" aria-describedby="dfhuAxPRjWXlnZg qGQeZOIbfnuepMJ" role="button" aria-label="Press &amp; Hold" style="display: block; margin: auto;"><div id="oMxNswdgnHlAyCD"></div><div id="jKMueAZQXzoyKPK"><div id="AuygvFSiklTNoxi" style="width: 0px;"></div><div id="DlyASOaUEXuwCKQ"><p id="BxCzrXOrMSriLck" class="OvUFtNeJxEurILR" style="animation: 1489.83ms ease 0s 1 normal none running textColorIReverse;">Press &amp; Hold</p><span id="dfhuAxPRjWXlnZg" class="yihOKYdugGUGXea">Human Challenge requires verification. Please press and hold the button until verified</span> <span id="DosuopiFHdRWGZO" class="yihOKYdugGUGXea" aria-live="assertive"></span></div><div class="fetching-volume"><span>•</span><span>•</span><span>•</span></div><div id="checkmark"></div><div id="ripple"></div></div></div>
'''

import subprocess
import time
import random
import threading
from globals import busy


def restart_chrome_window():
    while True:
        # Open a new Chrome window with the specified command
        chrome_process = subprocess.Popen([
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "--remote-debugging-port=9222",
            '--user-data-dir="/tmp/chrome_dev"',
            "https://app.prizepicks.com/board"
        ])
        
        print("Chrome window restarted.")

        # Calculate the next restart time with random delay
        time.sleep(20 * 60 + random.randint(-120, 120))
        
        # Check if busy is False
        while busy.value:
            print("busy")
            time.sleep(120)  # Wait for 2 minutes before checking again
        
        # Close the existing Chrome window
        chrome_process.terminate()
        
        time.sleep(0.1)
        


def start_background_task():
    # Start the background task in a separate thread
    chrome_thread = threading.Thread(target=restart_chrome_window, daemon=True)
    chrome_thread.start()

if __name__ == "__main__":
    start_background_task()
    
    while True:
        time.sleep(10)