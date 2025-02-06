import asyncio
import random
import json
import os
from playwright.async_api import async_playwright

async def intercept_request(request):
    if 'wagers' in request.url and request.method == 'POST':
        headers = request.headers
        post_data = request.post_data

        if post_data:
            x_csrf_token = headers.get('x-csrf-token')
            body_token = None

            if '"token":"' in post_data:
                body_token = post_data.split('"token":"')[1].split('"')[0]

            # Log out the tokens and ensure they're captured
            # print(f"x-csrf-token: {x_csrf_token}")
            # print(f"Body token: {body_token}")

            # Write the tokens to a file
            with open("tokens.json", "w") as f:
                json.dump({"x_csrf_token": x_csrf_token, "body_token": body_token}, f)
            # print("Tokens saved to tokens.json")

async def place_bet(page):
    max_attempts = 3
    attempt = 0
    successful_bet = False

    while attempt < max_attempts and not successful_bet:
        await page.goto("https://app.prizepicks.com/board")
        await page.wait_for_selector("#test-more", timeout=3000)

        buttons = await page.query_selector_all("#test-more")
        if len(buttons) < 2:
            attempt += 1
            continue

        if attempt == 9:
            await buttons[0].click()
            buttons = await page.query_selector_all("#test-more")  # Re-query
            await buttons[-1].click()
        else:
            random_buttons = random.sample(buttons, 2)
            await random_buttons[0].click()
            buttons = await page.query_selector_all("#test-more")  # Re-query
            random_buttons = random.sample(buttons, 2)
            await random_buttons[1].click()

        await page.fill("#entry-input", "5")
        await page.click('text="Submit Lineup"')

        # Intercept the request that places the bet
        response = await page.wait_for_event("response", lambda resp: "wagers" in resp.url and resp.request.method == "POST")

        if response.status == 200:
            successful_bet = True
            # print("Bet placed successfully!")
        else:
            # print(f"Failed to place bet. Status code: {response.status}")
            max_attempts = 1
            pass

        attempt += 1

    if not successful_bet:
        print("Failed to place a bet after multiple attempts.")

async def run(playwright):
    browser = await playwright.chromium.connect_over_cdp("http://localhost:9222")
    context = browser.contexts[0]
    page = context.pages[0] if context.pages else await context.new_page()

    page.on("request", intercept_request)
    await place_bet(page)

async def main():
    async with async_playwright() as playwright:
        await run(playwright)

asyncio.run(main())