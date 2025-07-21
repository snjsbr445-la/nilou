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

# --- আপনার ব্যক্তিগত তথ্য ---
IVASMS_EMAIL = "niloyg822@gmail.com"
IVASMS_PASSWORD = "N81234567"
TELEGRAM_TOKEN = "7549134101:AAFtBzB1gJ1hXj18zHLVTXQvtM3gZlkOvpw"
TELEGRAM_CHAT_ID = "-1002819267399"
BOT_NAME = "NILOY OTP"
ADMIN_USER_ID = 7052442701

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
otp_queue = Queue()

def send_to_telegram(message, chat_id):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML", "disable_web_page_preview": True}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logging.error(f"টেলিগ্রামে বার্তা পাঠাতে ব্যর্থ: {e}")

def create_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def otp_collector(driver, sent_messages):
    logging.info("✅ OTP সংগ্রহকারী চালু হয়েছে।")
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
            time.sleep(2)
        time.sleep(0.1)

def telegram_sender():
    logging.info("✅ টেলিগ্রাম প্রেরক চালু হয়েছে।")
    while True:
        item = otp_queue.get()
        try:
            message_content = item["message"]
            otp_code_match = re.search(r'\b\d{4,8}\b', message_content)
            otp_code = otp_code_match.group(0) if otp_code_match else "N/A"
            tz = pytz.timezone('Asia/Dhaka')
            current_time = datetime.now(tz).strftime('%d/%m/%Y, %I:%M:%S %p')
            escaped_message = html.escape(message_content)
            formatted_msg = (f"<b>{BOT_NAME}</b>\n✨ <b>OTP Received</b> ✨\n\n⏰ <b>Time:</b> {current_time}\n📞 <b>Number:</b> <code>{item['number']}</code>\n🔧 <b>Service:</b> {item['service']}\n🔑 <b>OTP Code:</b> <code>{otp_code}</code>\n\n<blockquote>{escaped_message}</blockquote>")
            send_to_telegram(formatted_msg, TELEGRAM_CHAT_ID)
        except Exception as e:
            logging.error(f"টেলিগ্রামে মেসেজ পাঠাতে গিয়ে সমস্যা: {e}")
        finally:
            otp_queue.task_done()

def start_bot():
    driver = None
    try:
        logging.info("বট চালু হচ্ছে...")
        driver = create_driver()
        driver.get("https://www.ivasms.com/login")
        time.sleep(3)
        driver.find_element(By.NAME, "email").send_keys(IVASMS_EMAIL)
        driver.find_element(By.NAME, "password").send_keys(IVASMS_PASSWORD)
        driver.find_element(By.TAG_NAME, "button").click()
        time.sleep(5)
        if "login" in driver.current_url:
            raise Exception("iVASMS-এ লগইন ব্যর্থ।")
        logging.info("✅ iVASMS-এ সফলভাবে লগইন করা হয়েছে।")
        send_to_telegram(f"<b>{BOT_NAME} BOT</b>\n🚀 <i>বট সফলভাবে চালু হয়েছে...</i>", ADMIN_USER_ID)
        driver.get("https://www.ivasms.com/portal/live/my_sms")
        logging.info("👀 OTP পেজ পর্যবেক্ষণ শুরু হচ্ছে...")
        sent_messages = set()
        collector_thread = Thread(target=otp_collector, args=(driver, sent_messages), daemon=True)
        collector_thread.start()
        sender_thread = Thread(target=telegram_sender, daemon=True)
        sender_thread.start()
        collector_thread.join()
        sender_thread.join()
    except Exception as e:
        error_details = traceback.format_exc()
        logging.critical(f"বট একটি মারাত্মক ত্রুটির কারণে বন্ধ হয়ে গেছে: {e}\n{error_details}")
        send_to_telegram(f"<b>{BOT_NAME} BOT</b>\n🐞 **বট ক্র্যাশ করেছে!**\n\n**কারণ:**\n`{e}`", ADMIN_USER_ID)
    finally:
        if driver:
            driver.quit()
        logging.info("বট সম্পূর্ণভাবে বন্ধ।")

if __name__ == "__main__":
    keep_alive()
    main_bot_thread = Thread(target=start_bot)
    main_bot_thread.start()
