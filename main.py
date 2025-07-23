# এই সম্পূর্ণ কোডটি main.py ফাইলে পেস্ট করুন (১ জন কর্মী সহ স্থিতিশীল আর্কিটেকচার)

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

# --- কনফিগারেশন (Configuration) ---
NUM_COLLECTOR_WORKERS = 1 # Render ফ্রি প্ল্যানে ২৪/৭ স্থিতিশীলভাবে চালানোর জন্য ১ জন কর্মী সেরা।
NUM_SENDER_WORKERS = 5    # ৫ জন প্রেরক OTP পাঠানোর জন্য প্রস্তুত থাকবে।

# --- ব্যক্তিগত তথ্য ---
IVASMS_EMAIL = "niloyg822@gmail.com"
IVASMS_PASSWORD = "N81234567"
TELEGRAM_TOKEN = "7549134101:AAFtBzB1gJ1hXj18zHLVTXQvtM3gZlkOvpw"
TELEGRAM_CHAT_ID = "-1002819267399"
ADMIN_USER_ID = 7052442701

# --- লগিং কনফিগারেশন ---
log_level = os.environ.get('LOG_LEVEL', 'WARNING').upper()
logging.basicConfig(level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# --- শেয়ারড রিসোর্স (সব থ্রেড এগুলো ব্যবহার করবে) ---
otp_queue = Queue()
sent_messages = set() # সব কর্মীর জন্য একটিই "স্মৃতি"

def send_to_telegram(message, chat_id):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML", "disable_web_page_preview": True}
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            logging.error(f"টেলিগ্রামে বার্তা পাঠাতে ব্যর্থ (স্ট্যাটাস কোড: {response.status_code}): {response.text}")
    except Exception as e:
        logging.error(f"টেলিগ্রামে বার্তা পাঠাতে গিয়ে নেটওয়ার্ক সমস্যা: {e}")

def create_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def otp_collector(worker_id):
    logger = logging.getLogger(f"Collector-{worker_id}")
    logger.warning("কর্মী চালু হচ্ছে...")
    driver = None
    try:
        driver = create_driver()
        driver.get("https://www.ivasms.com/login")
        driver.find_element(By.NAME, "email").send_keys(IVASMS_EMAIL)
        driver.find_element(By.NAME, "password").send_keys(IVASMS_PASSWORD)
        driver.find_element(By.TAG_NAME, "button").click()
        time.sleep(5) 

        if "login" in driver.current_url:
            raise Exception("লগইন ব্যর্থ।")
        
        logger.warning("কর্মী সফলভাবে লগইন করেছে।")
        driver.get("https://www.ivasms.com/portal/live/my_sms")

        while True:
            all_rows = driver.find_elements(By.CSS_SELECTOR, "tbody > tr")
            for row in reversed(all_rows):
                try:
                    message_content = row.find_elements(By.TAG_NAME, "td")[4].text.strip()
                    if message_content and message_content not in sent_messages:
                        sent_messages.add(message_content)
                        number_details = row.find_elements(By.TAG_NAME, "td")[0].text.strip().split('\n')
                        number = number_details[1] if len(number_details) > 1 else "N/A"
                        service_name = row.find_elements(By.TAG_NAME, "td")[1].text.strip()
                        otp_queue.put({"number": number, "service": service_name, "message": message_content})
                except Exception:
                    continue
            time.sleep(0.05)

    except Exception as e:
        logger.critical(f"কর্মী একটি মারাত্মক ত্রুটির কারণে বন্ধ হয়ে গেছে: {e}", exc_info=True)
        send_to_telegram(f"🐞 <b>একজন কালেক্টর কর্মী ({worker_id}) ক্র্যাশ করেছে!</b>\n\n<b>কারণ:</b>\n<code>{e}</code>", ADMIN_USER_ID)
    finally:
        if driver:
            driver.quit()
        logger.warning("কর্মী বন্ধ হয়ে গেছে।")

def telegram_sender():
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
        except Exception as e:
            logging.error(f"টেলিগ্রামে মেসেজ পাঠাতে গিয়ে সমস্যা: {e}")
        finally:
            otp_queue.task_done()

def start_bot():
    logging.warning("মূল বট সিস্টেম চালু হচ্ছে...")
    send_to_telegram("✅ <b>বট সিস্টেম চালু হচ্ছে এবং কর্মীরা প্রস্তুত হচ্ছে...</b>", ADMIN_USER_ID)

    for i in range(NUM_SENDER_WORKERS):
        sender_thread = Thread(target=telegram_sender, daemon=True)
        sender_thread.start()
    
    collector_thread = Thread(target=otp_collector, args=(1,), daemon=True)
    collector_thread.start()
    
    send_to_telegram(f"✅ <b>সিস্টেম সম্পূর্ণ অনলাইন! {NUM_COLLECTOR_WORKERS} জন কর্মী OTP সংগ্রহ করছে।</b>", ADMIN_USER_ID)

    collector_thread.join()

if __name__ == "__main__":
    keep_alive()
    main_bot_thread = Thread(target=start_bot)
    main_bot_thread.start()
