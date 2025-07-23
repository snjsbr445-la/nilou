# এটি main.py ফাইলে থাকবে

from keep_alive import keep_alive
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from threading import Thread
from queue import Queue
import time
import logging
import traceback
import requests
import html
import re
from datetime import datetime
import pytz
import os

# --- ব্যক্তিগত তথ্য (পরিবেশগত ভেরিয়েবল থেকে নেওয়া হবে) ---
# এটি অনেক বেশি নিরাপদ এবং সেরা অভ্যাস
IVASMS_EMAIL = os.environ.get('IVASMS_EMAIL')
IVASMS_PASSWORD = os.environ.get('IVASMS_PASSWORD')
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
ADMIN_USER_ID = os.environ.get('ADMIN_USER_ID')

# --- লগিং কনফিগারেশন (সঠিক পদ্ধতি) ---
# Render-এর পরিবেশগত ভেরিয়েবল থেকে লগ লেভেল নেওয়া হবে। ডিফল্ট WARNING থাকবে।
log_level = os.environ.get('LOG_LEVEL', 'WARNING').upper()
logging.basicConfig(level=log_level, format="%(asctime)s - %(levelname)s - %(message)s")

otp_queue = Queue()

def send_to_telegram(message, chat_id):
    if not chat_id:
        logging.error("Telegram chat_id পাওয়া যায়নি। বার্তা পাঠানো সম্ভব নয়।")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML", "disable_web_page_preview": True}
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            logging.error(f"টেলিগ্রামে বার্তা পাঠাতে ব্যর্থ (Status Code: {response.status_code}): {response.text}")
    except Exception as e:
        logging.error(f"টেলিগ্রামে বার্তা পাঠাতে গিয়ে নেটওয়ার্ক সমস্যা: {e}")

def create_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def otp_collector(driver, sent_messages):
    logging.info("✅ OTP সংগ্রহকারী চালু হয়েছে।") # এটি আর লগে দেখাবে না
    while True:
        try:
            all_rows = driver.find_elements(By.CSS_SELECTOR, "tbody > tr")
            for row in reversed(all_rows):
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 5:
                        message_content = cells[4].text.strip()
                        if message_content and message_content not in sent_messages:
                            sent_messages.add(message_content)
                            logging.warning(f"নতুন OTP পাওয়া গেছে: {message_content}") # এটি WARNING হিসেবে দেখাবে
                            number_details = cells[0].text.strip().split('\n')
                            number = number_details[1] if len(number_details) > 1 else "N/A"
                            service_name = cells[1].text.strip()
                            otp_queue.put({"number": number, "service": service_name, "message": message_content})
                except Exception:
                    continue
        except Exception as e:
            logging.error(f"OTP সংগ্রহ করতে গিয়ে সমস্যা: {e}")
            try:
                if "login" in driver.current_url:
                    logging.critical("iVASMS সেশন শেষ। বট বন্ধ হচ্ছে।")
                    os._exit(1)
            except Exception:
                os._exit(1)
        time.sleep(2) # ওয়েবসাইটকে অতিরিক্ত চাপ না দেওয়ার জন্য সময় ২ সেকেন্ড করা হলো

def telegram_sender():
    logging.info("✅ টেলিগ্রাম প্রেরক চালু হয়েছে।") # এটিও আর দেখাবে না
    while True:
        item = otp_queue.get()
        try:
            message_content = item["message"]
            otp_code_match = re.search(r'\b\d{4,8}\b', message_content)
            otp_code = otp_code_match.group(0) if otp_code_match else "N/A"
            tz = pytz.timezone('Asia/Dhaka')
            current_time = datetime.now(tz).strftime('%d/%m/%Y, %I:%M:%S %p')
            escaped_message = html.escape(message_content)
            formatted_msg = (
                f"✨ <b>OTP Received</b> ✨\n\n"
                f"⏰ <b>Time:</b> {current_time}\n"
                f"📞 <b>Number:</b> <code>{item['number']}</code>\n"
                f"🔧 <b>Service:</b> <code>{item['service']}</code>\n"
                f"🔑 <b>OTP Code:</b> <code>{otp_code}</code>\n\n"
                f"<blockquote>{escaped_message}</blockquote>"
            )
            send_to_telegram(formatted_msg, TELEGRAM_CHAT_ID)
            logging.warning(f"{item['number']}-এ একটি OTP সফলভাবে টেলিগ্রামে পাঠানো হয়েছে।")
        except Exception as e:
            logging.error(f"টেলিগ্রামে মেসেজ পাঠাতে গিয়ে সমস্যা: {e}")
        finally:
            otp_queue.task_done()

def start_bot():
    driver = None
    try:
        logging.warning("বট চালু হচ্ছে...") # এটি WARNING, তাই লগে দেখা যাবে
        if not all([IVASMS_EMAIL, IVASMS_PASSWORD, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, ADMIN_USER_ID]):
             logging.critical("গুরুত্বপূর্ণ তথ্য (Password/Token) পাওয়া যায়নি। Environment Variables চেক করুন।")
             return

        driver = create_driver()
        driver.get("https://www.ivasms.com/login")
        time.sleep(3)
        driver.find_element(By.NAME, "email").send_keys(IVASMS_EMAIL)
        driver.find_element(By.NAME, "password").send_keys(IVASMS_PASSWORD)
        driver.find_element(By.TAG_NAME, "button").click()
        time.sleep(5)
        if "login" in driver.current_url:
            raise Exception("iVASMS-এ লগইন ব্যর্থ। ইমেল/পাসওয়ার্ড অথবা সাইট পরিবর্তন হয়েছে কিনা চেক করুন।")
        logging.warning("✅ iVASMS-এ সফলভাবে লগইন করা হয়েছে।") # এটিও WARNING হিসেবে দেখাবে

        driver.get("https://www.ivasms.com/portal/live/my_sms")
        logging.warning("👀 OTP পেজ পর্যবেক্ষণ শুরু হচ্ছে...")
        sent_messages = set()
        collector_thread = Thread(target=otp_collector, args=(driver, sent_messages), daemon=True)
        collector_thread.start()

        for _ in range(5):
            sender_thread = Thread(target=telegram_sender, daemon=True)
            sender_thread.start()

        collector_thread.join()
    except Exception as e:
        error_details = traceback.format_exc()
        # এই দুটি লাইন নিশ্চিত করবে যে ক্র্যাশ হলে আপনি জানতে পারবেন
        logging.critical(f"বট একটি মারাত্মক ত্রুটির কারণে বন্ধ হয়ে গেছে: {e}\n{error_details}")
        send_to_telegram(f"🐞 <b>বট ক্র্যাশ করেছে!</b>\n\n<b>কারণ:</b>\n<code>{html.escape(str(e))}</code>\n\n<b>সম্পূর্ণ লগ চেক করুন।</b>", ADMIN_USER_ID)
    finally:
        if driver:
            driver.quit()
        logging.warning("বট সম্পূর্ণভাবে বন্ধ।")

if __name__ == "__main__":
    keep_alive()
    main_bot_thread = Thread(target=start_bot)
    main_bot_thread.start()
