from flask import Flask
from threading import Thread
import logging

# Flask এর নিজস্ব লগিং নিষ্ক্রিয় করার জন্য এই লাইনগুলো যোগ করা হয়েছে
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask('')

# Render এর Health Check Path অনুযায়ী এটি পরিবর্তন করা হয়েছে
@app.route('/ping')
def home():
    return "I'm alive"

def run():
  # Dockerfile এখন পোর্ট নিয়ন্ত্রণ করবে, তাই এখানে পোর্ট নির্দিষ্ট করার প্রয়োজন নেই
  app.run(host='0.0.0.0')

def keep_alive():
    t = Thread(target=run)
    t.start()```
