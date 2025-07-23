# এই কোডটি keep_alive.py ফাইলে থাকবে

from flask import Flask
from threading import Thread
import logging

# Flask এর নিজস্ব লগ দেখানো বন্ধ করা হচ্ছে
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask('')

@app.route('/')
def home():
    return "I'm alive"

def run():
  # এখানে host='0.0.0.0' এবং port=8080 ব্যবহার করা Render এর জন্য স্ট্যান্ডার্ড
  app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()
